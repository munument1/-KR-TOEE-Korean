from pathlib import Path
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


def patch_help_link_offsets(root: Path):
    p = root / "TemplePlus/gamesystems/d20/d20_help.cpp"
    text, enc = read_source(p)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    include_anchor = '#include <infrastructure/elfhash.h>\n'
    include_new = '#include <infrastructure/elfhash.h>\n#include <infrastructure/stringutil.h>\n'
    if include_anchor not in text:
        raise RuntimeError("d20_help.cpp include anchor not found")
    text = text.replace(include_anchor, include_new, 1)

    old = '''int HelpSystem::LinkParser(D20HelpLink* d20hl, char* topicTitle, char** pos1, char** pos2, int* offsetOut)
{
\tif (strstr(topicTitle,"Disable Attacks"))
\t{
\t\tint dum = 1;
\t}
\tint result = orgLinkParser(d20hl, topicTitle, pos1, pos2, offsetOut);
\treturn result;
}
'''

    # IMPORTANT: this is deliberately a normal triple-quoted Python string,
    # not a raw string. The \t sequences below therefore become real tabs in
    # the generated C++ rather than literal backslash-t tokens.
    new = '''namespace {

// Vanilla help link positions are byte offsets into the legacy formatted
// string. Korean resources use CP949 while TemplePlus renders through UTF-16.
// Convert the parsed range to UTF-16 code-unit positions so the legacy help UI
// and the replacement text renderer agree on link placement.
int KrHelpCp949BytesToUtf16Units(const char* text, int byteCount)
{
\tif (!text || byteCount < 0) {
\t\treturn -1;
\t}
\tif (byteCount == 0) {
\t\treturn 0;
\t}

\tauto totalBytes = (int)strlen(text);
\tif (byteCount > totalBytes) {
\t\treturn -1;
\t}

\tauto decoded = legacy_to_ucs2(std::string(text, byteCount));
\tif (decoded.empty()) {
\t\treturn -1;
\t}
\treturn (int)decoded.size();
}

}

int HelpSystem::LinkParser(D20HelpLink* d20hl, char* topicTitle, char** pos1, char** pos2, int* offsetOut)
{
\tint result = orgLinkParser(d20hl, topicTitle, pos1, pos2, offsetOut);

\tif (!d20hl || !topicTitle) {
\t\treturn result;
\t}

\tbool validLink = false;
\tif (d20hl->isRoll == 1) {
\t\tvalidLink = true;
\t} else if (d20hl->isRoll == 0 && d20hl->linkedTopicId != 0) {
\t\tvalidLink = HelpSystem::GetTopic(d20hl->linkedTopicId) != nullptr;
\t}
\tif (!validLink || d20hl->startPos < 0 || d20hl->endPos <= 0) {
\t\treturn result;
\t}

\tauto totalBytes = (int)strlen(topicTitle);
\tif (d20hl->startPos > totalBytes || d20hl->endPos > totalBytes - d20hl->startPos) {
\t\treturn result;
\t}

\tauto utf16Start = KrHelpCp949BytesToUtf16Units(topicTitle, d20hl->startPos);
\tauto utf16End = KrHelpCp949BytesToUtf16Units(topicTitle, d20hl->startPos + d20hl->endPos);
\tif (utf16Start < 0 || utf16End < utf16Start) {
\t\treturn result;
\t}

\td20hl->startPos = utf16Start;
\td20hl->endPos = utf16End - utf16Start;
\treturn result;
}
'''

    if old not in text:
        raise RuntimeError("LinkParser anchor not found")
    text = text.replace(old, new, 1)
    write_source(p, text, enc)
    print("KR_HELP_CP949_LINK_OFFSET_FIX_ADDED")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_link_cp949_offset_fix.py <TemplePlus root>")
    root = Path(sys.argv[1]).resolve()
    patch_long_description(root)
    patch_help_link_offsets(root)


if __name__ == "__main__":
    main()
