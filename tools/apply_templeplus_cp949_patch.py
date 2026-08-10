from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def patch_file(path: Path, transform):
    text = path.read_text(encoding="utf-8-sig")
    new_text = transform(text)
    if new_text == text:
        raise RuntimeError(f"No changes made to {path}")
    path.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"patched {path}")


def patch_stringutil_h(text: str) -> str:
    old = """std::string ucs2_to_local(const std::wstring &);\nstd::wstring local_to_ucs2(const std::string &);\nstd::string ucs2_to_utf8(const std::wstring &);\nstd::wstring utf8_to_ucs2(const std::string &);\n"""
    new = old + """\n// Encoding used by legacy ToEE text resources (.mes/.dlg/etc.).\n// Defaults to CP_ACP to preserve the original behavior. Korean builds switch\n// this to CP949 after reading mes/language.mes.\nvoid set_legacy_text_codepage(unsigned int codePage);\nstd::string ucs2_to_legacy(const std::wstring &);\nstd::wstring legacy_to_ucs2(const std::string &);\n"""
    return replace_once(text, old, new, "stringutil.h declarations")


def patch_stringutil_cpp(text: str) -> str:
    include = '#include "infrastructure/stringutil.h"\n'
    helper = r'''
namespace {

UINT gLegacyTextCodePage = CP_ACP;

std::string ucs2_to_codepage(const std::wstring &s, UINT codePage) {
    if (s.empty()) {
        return {};
    }

    auto len = WideCharToMultiByte(
        codePage, 0,
        s.data(), (int)s.size(),
        nullptr, 0,
        nullptr, nullptr
    );
    if (len <= 0) {
        return {};
    }

    std::string result(len, '\0');
    WideCharToMultiByte(
        codePage, 0,
        s.data(), (int)s.size(),
        &result[0], len,
        nullptr, nullptr
    );
    return result;
}

std::wstring codepage_to_ucs2(const std::string &s, UINT codePage) {
    if (s.empty()) {
        return {};
    }

    auto len = MultiByteToWideChar(
        codePage, 0,
        s.data(), (int)s.size(),
        nullptr, 0
    );
    if (len <= 0) {
        return {};
    }

    std::wstring result(len, L'\0');
    MultiByteToWideChar(
        codePage, 0,
        s.data(), (int)s.size(),
        &result[0], len
    );
    return result;
}

}
'''
    text = replace_once(text, include, include + helper, "stringutil.cpp helper")

    marker = "\nstd::string ucs2_to_utf8(const std::wstring &str) {"
    additions = r'''

void set_legacy_text_codepage(unsigned int codePage) {
    gLegacyTextCodePage = codePage;
}

std::string ucs2_to_legacy(const std::wstring &s) {
    return ucs2_to_codepage(s, gLegacyTextCodePage);
}

std::wstring legacy_to_ucs2(const std::string &s) {
    return codepage_to_ucs2(s, gLegacyTextCodePage);
}
'''
    text = replace_once(text, marker, additions + marker, "stringutil.cpp public helpers")
    return text


def patch_gamesystems(text: str) -> str:
    text = replace_once(
        text,
        "#include <infrastructure/mesparser.h>\n#include <util/fixes.h>",
        "#include <infrastructure/mesparser.h>\n#include <infrastructure/stringutil.h>\n#include <util/fixes.h>",
        "gamesystems include"
    )
    old = """\tauto lang = GetLanguage();\n\tif (lang == \"en\") {\n"""
    new = """\tauto lang = GetLanguage();\n\tif (lang == \"ko\") {\n\t\t// Korean ToEE resources are emitted as Windows CP949.\n\t\t// Do not depend on the user's Windows \"language for non-Unicode\n\t\t// programs\" setting.\n\t\tset_legacy_text_codepage(949);\n\t\tlogger->info(\"Korean text mode enabled (CP949)\");\n\t}\n\tif (lang == \"en\") {\n"""
    return replace_once(text, old, new, "gamesystems Korean mode")


def patch_fonts_layout(text: str) -> str:
    start = text.index("static FormattedText ProcessString(")
    end = text.index("void TextLayouter::LayoutAndDraw", start)
    new_func = r'''static FormattedText ProcessString(const TextStyle& defaultStyle, const TigTextStyle &tigStyle, gsl::cstring_span<> text)
{
    FormattedText result;
    result.defaultStyle = defaultStyle;
    result.text.reserve(text.size());

    bool inColorRange = false;
    std::string pendingBytes;
    pendingBytes.reserve(text.size());

    // Decode ordinary text in whole CP949 byte runs. The old implementation
    // appended one byte at a time to std::wstring, corrupting double-byte Hangul.
    auto flushPending = [&]() {
        if (pendingBytes.empty()) {
            return;
        }

        auto decoded = legacy_to_ucs2(pendingBytes);
        if (inColorRange) {
            // DirectWrite formatting ranges are measured in UTF-16 code units,
            // not source bytes.
            result.formats.back().length += (uint32_t)decoded.size();
        }
        result.text.append(decoded);
        pendingBytes.clear();
    };

    for (int i = 0; i < text.size();) {
        auto ch = text[i];

        // Legacy formatting commands are ASCII and therefore unambiguous in
        // CP949. Only consume @t and @0..@9. Any other '@' remains literal.
        if (ch == '@' && i + 1 < text.size()) {
            auto command = text[i + 1];
            auto isColorCommand = command >= '0' && command <= '9';

            if (command == 't' || isColorCommand) {
                flushPending();
                i += 2;

                if (command == 't') {
                    result.text.push_back(L'\t');
                    if (inColorRange) {
                        result.formats.back().length++;
                    }
                    continue;
                }

                auto colorIdx = command - '0';
                if (colorIdx == 0 || !tigStyle.textColor) {
                    inColorRange = false;
                } else {
                    inColorRange = true;

                    ConstrainedTextStyle newStyle(defaultStyle);
                    newStyle.startChar = (uint32_t)result.text.size();
                    newStyle.style.foreground.gradient = false;
                    newStyle.style.foreground.primaryColor =
                        tigStyle.textColor[colorIdx].topLeft;

                    result.formats.emplace_back(std::move(newStyle));
                }
                continue;
            }
        }

        pendingBytes.push_back(ch);
        i++;
    }

    flushPending();
    return result;
}

'''
    text = text[:start] + new_func + text[end:]
    text = replace_once(
        text,
        "formatted.text = local_to_ucs2(to_string(text));",
        "formatted.text = legacy_to_ucs2(to_string(text));",
        "fonts_layout draw conversion"
    )
    text = replace_once(
        text,
        "mTextEngine.MeasureText(textStyle, metrics.text, textMetrics);",
        "mTextEngine.MeasureText(textStyle, legacy_to_ucs2(metrics.text), textMetrics);",
        "fonts_layout measure conversion"
    )
    return text


def patch_widget_content(text: str) -> str:
    text = replace_once(
        text,
        "mText.text = local_to_ucs2(uiAssets->ApplyTranslation(text));",
        "mText.text = legacy_to_ucs2(uiAssets->ApplyTranslation(text));",
        "WidgetText SetText"
    )
    text = replace_once(
        text,
        "auto text = ucs2_to_local(mText.text);",
        "auto text = ucs2_to_legacy(mText.text);",
        "WidgetText predefined render"
    )
    text = replace_once(
        text,
        "auto rect = UiRenderer::MeasureTextSize(ucs2_to_local(mText.text), textStyle, 0, 0);",
        "auto rect = UiRenderer::MeasureTextSize(ucs2_to_legacy(mText.text), textStyle, 0, 0);",
        "WidgetText predefined measure"
    )
    return text


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_templeplus_cp949_patch.py <TemplePlus source root>")
    root = Path(sys.argv[1]).resolve()
    patch_file(root / "Infrastructure/include/infrastructure/stringutil.h", patch_stringutil_h)
    patch_file(root / "Infrastructure/stringutil.cpp", patch_stringutil_cpp)
    patch_file(root / "TemplePlus/gamesystems/gamesystems.cpp", patch_gamesystems)
    patch_file(root / "TemplePlus/fonts/fonts_layout.cpp", patch_fonts_layout)
    patch_file(root / "TemplePlus/ui/widgets/widget_content.cpp", patch_widget_content)

    checks = {
        "Infrastructure/stringutil.cpp": "legacy_to_ucs2",
        "TemplePlus/gamesystems/gamesystems.cpp": "Korean text mode enabled (CP949)",
        "TemplePlus/fonts/fonts_layout.cpp": "pendingBytes",
        "TemplePlus/ui/widgets/widget_content.cpp": "ucs2_to_legacy",
    }
    for rel, needle in checks.items():
        if needle not in (root / rel).read_text(encoding="utf-8"):
            raise RuntimeError(f"verification failed: {rel} missing {needle}")
    print("PATCH_OK")


if __name__ == "__main__":
    main()
