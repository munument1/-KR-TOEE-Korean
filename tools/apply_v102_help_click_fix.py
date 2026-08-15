from pathlib import Path
import re
import sys


def read_source(path: Path):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def write_source(path: Path, text: str, enc: str):
    path.write_bytes(text.encode(enc))


def patch_long_description(root: Path):
    p = root / "TemplePlus/ui/ui_char.cpp"
    text, enc = read_source(p)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    start_marker = "void UiCharHooks::LongDescriptionPopupCreate(objHndl item)\n{\n"
    end_marker = "\nvoid UiCharHooks::TotalWeightOutputBtnTooltip"
    start = text.find(start_marker)
    end = text.find(end_marker, start)
    if start < 0 or end < 0:
        raise RuntimeError("LongDescriptionPopupCreate anchors not found")
    replacement = '''void UiCharHooks::LongDescriptionPopupCreate(objHndl item)
{
    temple::GetRef<void(__cdecl)(objHndl)>(0x10144400)(item);
}
'''
    text = text[:start] + replacement + text[end:]
    hook_line = "\treplaceFunction(0x10144400, LongDescriptionPopupCreate);\n"
    if hook_line not in text:
        raise RuntimeError("Long-description replacement hook not found")
    text = text.replace(hook_line, "", 1)
    write_source(p, text, enc)
    print("LONG_DESCRIPTION_VANILLA_POPUP_RESTORED")


def patch_help_click(root: Path):
    p = root / "TemplePlus/gamesystems/d20/d20_help.cpp"
    text, enc = read_source(p)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    include_anchor = '#include "d20_race.h"\n'
    include_extra = '''#include "d20_race.h"
#include "ui/ui.h"
#include "tig/tig_msg.h"
#include "tig/tig_font.h"
#include <unordered_map>
#include <vector>
#include <algorithm>
#include <string>
'''
    if include_anchor not in text:
        raise RuntimeError("d20_race include anchor missing")
    text = text.replace(include_anchor, include_extra, 1)

    insert_anchor = "void D20RollHistoryEntry::CreateFromString"
    anchor_pos = text.find(insert_anchor)
    if anchor_pos < 0:
        raise RuntimeError("D20RollHistoryEntry::CreateFromString anchor missing")

    fix_code = r'''
// KR v1.0.2 help-link fix.
// Korean help text is rendered/measured through the CP949-aware TTF path,
// while the original scrollbox click hit-test still uses the legacy byte-glyph path.
// For the help window only, compute clickable link rectangles with tigFont.Measure.
namespace {

using KrHelpShowFn = void(__cdecl *)(int);
using KrScrollboxMsgFn = BOOL(__cdecl *)(int, TigMsg*);

static KrHelpShowFn krOrgHelpShow = nullptr;
static KrScrollboxMsgFn krOrgScrollboxMsg = nullptr;
static int krCurrentHelpTopic = 0;
static bool krHelpBodiesLoaded = false;
static std::unordered_map<int, std::string> krHelpBodies;

struct KrHelpLinkSpan {
    size_t start = 0;
    size_t end = 0;
    int topicId = 0;
};

struct KrVisualLine {
    size_t start = 0;
    size_t end = 0;
    bool indented = false;
};

static int __cdecl KrHelpBodyParser(const TigTabParser*, int, char** columns) {
    if (!columns || !columns[0] || !columns[5] || !*columns[0]) {
        return 0;
    }
    krHelpBodies[ElfHash::Hash(columns[0])] = columns[5];
    return 0;
}

static void KrEnsureHelpBodiesLoaded() {
    if (krHelpBodiesLoaded) return;
    krHelpBodiesLoaded = true;
    TigTabParser p;
    p.Init(KrHelpBodyParser);
    p.Open("mes\\help.tab");
    p.Process();
    p.Close();
    logger->info("KR_HELP_CLICK_FIX_ACTIVE: loaded {} help bodies", krHelpBodies.size());
}

static bool KrHasHighBytes(const std::string& s) {
    for (unsigned char ch : s) {
        if (ch >= 0x80) return true;
    }
    return false;
}

static std::string KrTrimAscii(std::string s) {
    while (!s.empty() && (s.front() == ' ' || s.front() == '\t' || s.front() == '\r')) s.erase(s.begin());
    while (!s.empty() && (s.back() == ' ' || s.back() == '\t' || s.back() == '\r')) s.pop_back();
    return s;
}

static void KrAppendTopicLink(std::string& out, std::vector<KrHelpLinkSpan>& links,
                              const std::string& label, int topicId) {
    auto start = out.size();
    out.append("@1");
    out.append(label);
    out.append("@0");
    auto end = out.size();
    if (topicId) links.push_back({ start, end, topicId });
}

static void KrAppendChildren(std::string& out, std::vector<KrHelpLinkSpan>& links,
                             D20HelpTopic* topic, bool sorted) {
    if (!topic) return;
    std::vector<D20HelpTopic*> children;
    int childId = topic->siblingId;
    int guard = 0;
    while (childId && guard++ < 4096) {
        auto child = HelpSystem::GetTopic(childId);
        if (!child) break;
        children.push_back(child);
        childId = child->nextId;
    }
    for (int i = 0; i < topic->vChildrenSize; ++i) {
        auto child = HelpSystem::GetTopic(topic->virtualChildren[i]);
        if (child && std::find(children.begin(), children.end(), child) == children.end()) {
            children.push_back(child);
        }
    }
    if (sorted) {
        std::sort(children.begin(), children.end(), [](D20HelpTopic* a, D20HelpTopic* b) {
            if (!a || !a->title) return true;
            if (!b || !b->title) return false;
            return _stricmp(a->title, b->title) < 0;
        });
    }
    for (auto child : children) {
        if (!child || !child->title) continue;
        KrAppendTopicLink(out, links, child->title, child->topicId);
        out.push_back('\n');
    }
}

static void KrBuildDisplayText(int topicId, const std::string& raw,
                               std::string& out, std::vector<KrHelpLinkSpan>& links) {
    out.clear();
    links.clear();
    out.append("\n\n");
    auto topic = HelpSystem::GetTopic(topicId);

    for (size_t i = 0; i < raw.size();) {
        if (raw.compare(i, 21, "[CMD_CHILDREN_SORTED]") == 0) {
            KrAppendChildren(out, links, topic, true);
            i += 21;
            continue;
        }
        if (raw.compare(i, 14, "[CMD_CHILDREN]") == 0) {
            KrAppendChildren(out, links, topic, false);
            i += 14;
            continue;
        }
        if (raw[i] == '~') {
            auto mid = raw.find("~[", i + 1);
            if (mid != std::string::npos) {
                auto close = raw.find(']', mid + 2);
                if (close != std::string::npos) {
                    auto label = raw.substr(i + 1, mid - i - 1);
                    auto target = KrTrimAscii(raw.substr(mid + 2, close - (mid + 2)));
                    int targetId = 0;
                    if (target.rfind("TAG_", 0) == 0) targetId = ElfHash::Hash(target.c_str());
                    KrAppendTopicLink(out, links, label, targetId);
                    i = close + 1;
                    continue;
                }
            }
        }
        char ch = raw[i++];
        if (ch == '\v') ch = '\n';
        out.push_back(ch);
    }
}

static int KrMeasureRange(const TigTextStyle& style, const std::string& text,
                          size_t start, size_t end) {
    if (end <= start) return 0;
    auto tmp = text.substr(start, end - start);
    TigFontMetrics metrics;
    metrics.text = tmp.c_str();
    metrics.width = 0;
    metrics.height = 0;
    tigFont.Measure(style, metrics);
    return metrics.width;
}

static size_t KrNextByteChar(const std::string& text, size_t pos, size_t end) {
    if (pos >= end) return end;
    unsigned char c = (unsigned char)text[pos];
    if (c == '@' && pos + 1 < end && text[pos + 1] >= '0' && text[pos + 1] <= '9') return pos + 2;
    if (c >= 0x81 && pos + 1 < end) return pos + 2;
    return pos + 1;
}

static std::vector<KrVisualLine> KrBuildVisualLines(const TigTextStyle& style,
                                                     const std::string& text, int width) {
    std::vector<KrVisualLine> result;
    size_t logicalStart = 0;
    while (logicalStart <= text.size()) {
        auto nl = text.find('\n', logicalStart);
        size_t logicalEnd = (nl == std::string::npos) ? text.size() : nl;
        if (logicalStart == logicalEnd) {
            result.push_back({ logicalStart, logicalEnd, false });
        } else {
            size_t pos = logicalStart;
            bool indented = false;
            while (pos < logicalEnd) {
                int available = width - (indented ? 15 : 0);
                size_t cur = pos;
                size_t best = pos;
                size_t lastSpace = std::string::npos;
                while (cur < logicalEnd) {
                    auto next = KrNextByteChar(text, cur, logicalEnd);
                    if (text[cur] == ' ' || text[cur] == '\t') lastSpace = next;
                    if (KrMeasureRange(style, text, pos, next) > available) {
                        if (lastSpace != std::string::npos && lastSpace > pos) best = lastSpace;
                        else if (cur > pos) best = cur;
                        else best = next;
                        break;
                    }
                    best = next;
                    cur = next;
                }
                if (best <= pos) best = KrNextByteChar(text, pos, logicalEnd);
                result.push_back({ pos, best, indented });
                pos = best;
                while (pos < logicalEnd && (text[pos] == ' ' || text[pos] == '\t')) ++pos;
                indented = true;
            }
        }
        if (nl == std::string::npos) break;
        logicalStart = nl + 1;
    }
    return result;
}

static int KrGetScrollValue(LgcyWindow* body) {
    if (!body) return 0;
    for (uint32_t i = 0; i < body->childrenCount && i < 128; ++i) {
        auto child = uiManager->GetWidget(body->children[i]);
        if (child && child->IsScrollBar()) {
            auto sb = (LgcyScrollBar*)child;
            auto value = sb->GetY();
            return value < 0 ? 0 : value;
        }
    }
    return 0;
}

static bool KrIsHelpBodyWindow(LgcyWindow* body) {
    if (!body) return false;
    if ((int)body->width != 400 || (int)body->height != 398) return false;
    if (body->parentId < 0) return false;
    auto parent = uiManager->GetWindow(body->parentId);
    return parent && (int)parent->width == 462 && (int)parent->height == 507;
}

static bool KrTryHandleHelpClick(int widId, TigMsg* msg) {
    if (!msg || msg->type != TigMsgType::WIDGET ||
        !msg->IsWidgetEvent(TigMsgWidgetEvent::MouseReleased) || !krCurrentHelpTopic) {
        return false;
    }
    auto body = uiManager->GetWindow(widId);
    if (!KrIsHelpBodyWindow(body)) return false;

    KrEnsureHelpBodiesLoaded();
    auto it = krHelpBodies.find(krCurrentHelpTopic);
    if (it == krHelpBodies.end() || !KrHasHighBytes(it->second)) return false;

    std::string display;
    std::vector<KrHelpLinkSpan> links;
    KrBuildDisplayText(krCurrentHelpTopic, it->second, display, links);
    if (links.empty()) return false;

    TigTextStyle style;
    style.flags = TTSF_DROP_SHADOW;
    style.kerning = 1;
    style.tracking = 3;
    style.field4c = 15;

    tigFont.PushFont("arial-10", 10, true);
    TigFontMetrics heightMetrics;
    heightMetrics.text = "TEST";
    tigFont.Measure(style, heightMetrics);
    int lineHeight = heightMetrics.height > 0 ? heightMetrics.height : 13;
    const int textWidth = 380;
    auto lines = KrBuildVisualLines(style, display, textWidth);

    auto wmsg = (TigMsgWidget*)msg;
    int textX = body->x;
    int textY = body->y + 16;
    int mx = (int)wmsg->x;
    int my = (int)wmsg->y;
    if (mx < textX || mx >= textX + textWidth || my < textY || my >= textY + 374) {
        tigFont.PopFont();
        return false;
    }

    int firstLine = KrGetScrollValue(body);
    int clickedLine = firstLine + (my - textY) / lineHeight;
    if (clickedLine < 0 || clickedLine >= (int)lines.size()) {
        tigFont.PopFont();
        return false;
    }

    const auto& line = lines[clickedLine];
    int indent = line.indented ? 15 : 0;
    int relX = mx - textX;
    for (const auto& link : links) {
        if (link.end <= line.start || link.start >= line.end || !link.topicId) continue;
        size_t segStart = std::max(link.start, line.start);
        size_t segEnd = std::min(link.end, line.end);
        int left = indent + KrMeasureRange(style, display, line.start, segStart);
        int right = indent + KrMeasureRange(style, display, line.start, segEnd);
        if (right < left) std::swap(left, right);
        if (relX >= left - 5 && relX <= right + 5) {
            auto targetId = link.topicId;
            tigFont.PopFont();
            logger->info("KR_HELP_CLICK_FIX: topic {} -> {}", krCurrentHelpTopic, targetId);
            helpSys.PresentWikiHelpWindow(targetId);
            return true;
        }
    }

    tigFont.PopFont();
    return false;
}

static void __cdecl KrHelpShowHook(int topicId) {
    krCurrentHelpTopic = topicId;
    krOrgHelpShow(topicId);
}

static BOOL __cdecl KrScrollboxMsgHook(int widId, TigMsg* msg) {
    if (KrTryHandleHelpClick(widId, msg)) return TRUE;
    return krOrgScrollboxMsg(widId, msg);
}

class KrHelpClickFix : TempleFix {
public:
    void apply() override {
        krOrgHelpShow = replaceFunction<void(__cdecl)(int)>(0x100E6CF0, KrHelpShowHook);
        krOrgScrollboxMsg = replaceFunction<BOOL(__cdecl)(int, TigMsg*)>(0x1018D720, KrScrollboxMsgHook);
    }
} krHelpClickFix;

} // namespace

'''

    text = text[:anchor_pos] + fix_code + text[anchor_pos:]
    write_source(p, text, enc)
    print("KR_HELP_CLICK_FIX_SOURCE_ADDED")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_click_fix.py <TemplePlus root>")
    root = Path(sys.argv[1]).resolve()
    patch_long_description(root)
    patch_help_click(root)


if __name__ == "__main__":
    main()
