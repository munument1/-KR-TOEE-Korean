from pathlib import Path
import sys


def read_source_text(path: Path):
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252"), "cp1252"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def patch_fonts_hooks(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "KR_HELP_WORDWRAP_CP949" in text:
        raise RuntimeError("FontWordWrap patch already present")
    if "KR_HELP_HITTEST_CP949" not in text:
        raise RuntimeError("TEST8 CP949 hit-test patch must be applied first")

    type_anchor = """using FontHitTestFn = int(__cdecl *)(const char*, TigRect*, TigTextStyle*, int, int, int*);\nstatic FontHitTestFn orgFontHitTest = nullptr;\n"""
    type_replacement = type_anchor + """using FontWordWrapFn = int(__cdecl *)(const char*, TigRect*, TigTextStyle*);\nstatic FontWordWrapFn orgFontWordWrap = nullptr;\n"""
    text = replace_once(text, type_anchor, type_replacement, "FontWordWrap typedef")

    declaration_anchor = """\tstatic int FontHitTest(const char* text, TigRect* extents, TigTextStyle* style,\n\t\tint x, int y, int* textPos);\n"""
    declaration_replacement = declaration_anchor + """\n\tstatic int FontWordWrap(const char* text, TigRect* extents, TigTextStyle* style);\n"""
    text = replace_once(text, declaration_anchor, declaration_replacement, "FontWordWrap declaration")

    apply_anchor = """\torgFontHitTest = replaceFunction<int(__cdecl)(const char*, TigRect*, TigTextStyle*, int, int, int*)>(\n\t\t0x101EA7F0, FontHitTest);\n\tlogger->info(\"KR_HELP_HITTEST_CP949 enabled\");\n"""
    apply_replacement = apply_anchor + """\t// Verified native ABI from temple.dll 0x101E8B20:\n\t// int __cdecl(const char* text, TigRect* extents, TigTextStyle* style).\n\t// The return value is a SOURCE-BYTE count consumed by ScrollBox 0x1018D1B0.\n\torgFontWordWrap = replaceFunction<int(__cdecl)(const char*, TigRect*, TigTextStyle*)>(\n\t\t0x101E8B20, FontWordWrap);\n\tlogger->info(\"KR_HELP_WORDWRAP_CP949 enabled\");\n"""
    text = replace_once(text, apply_anchor, apply_replacement, "FontWordWrap hook")

    append_code = r'''

int FontRenderFix::FontWordWrap(const char* text, TigRect* extents, TigTextStyle* style) {
	// The original 0x101E8B20 is a byte/FNT word wrapper. It treats both bytes
	// of every CP949 Hangul syllable as unrelated glyphs. ScrollBox 0x1018D1B0
	// consumes this function's return value as a source-byte count and stops
	// creating lines entirely when that count is zero.
	//
	// Keep vanilla behavior for ASCII. Only the DBCS path below is new.
	if (!orgFontWordWrap || !text || !extents || !style || !KrContainsDbcsBytes(text)) {
		return orgFontWordWrap ? orgFontWordWrap(text, extents, style) : 0;
	}

	const auto length = strlen(text);
	if (!length) {
		return 0;
	}

	// These modes need layout semantics beyond the left-aligned line wrapping
	// used by the help/history ScrollBox. Do not alter them.
	constexpr int UnsupportedFlags = TTSF_CENTER | TTSF_TRUNCATE
		| TTSF_ROTATE | TTSF_ROTATE_OFF_CENTER;
	if ((style->flags & UnsupportedFlags) || extents->width <= 0) {
		return orgFontWordWrap(text, extents, style);
	}

	TigTextStyle measureStyle = *style;
	// LayoutAndDraw interprets field4c as an absolute tab stop and converts it
	// relative to the current rectangle. Prefix measurement must do the same.
	if (measureStyle.field4c > 0) {
		measureStyle.field4c -= extents->x;
	}

	std::string prefix;
	prefix.reserve(length);

	size_t previousVisibleBoundary = 0;
	size_t lastWhitespaceBreak = 0;
	size_t lastDbcsBreak = 0;

	for (size_t pos = 0; pos < length;) {
		const auto ch = static_cast<unsigned char>(text[pos]);
		const auto next = KrNextCp949Unit(text, length, pos);

		// The ScrollBox hands this routine one logical line including its newline.
		// Consume the newline so the next native line starts after it.
		if (ch == '\n' || ch == '\r' || ch == '\v') {
			return static_cast<int>(next);
		}

		const bool isFormat = ch == '@' && next == pos + 2
			&& ((text[pos + 1] >= '0' && text[pos + 1] <= '9') || text[pos + 1] == 't');
		const bool isTabCommand = isFormat && text[pos + 1] == 't';
		const bool isDbcs = ch >= 0x81 && ch <= 0xFE && next == pos + 2;
		const bool isWhitespace = ch == ' ' || ch == '\t' || isTabCommand;

		prefix.assign(text, next);
		TigFontMetrics metrics;
		metrics.text = prefix.c_str();
		metrics.width = 0;
		metrics.height = 0;
		if (FontMeasure(measureStyle, metrics) != 0) {
			return orgFontWordWrap(text, extents, style);
		}

		if (metrics.width > extents->width) {
			// Korean may wrap between syllables. If a DBCS character fitted after
			// the last ASCII whitespace, use that fullest Korean boundary.
			if (lastDbcsBreak > lastWhitespaceBreak) {
				return static_cast<int>(lastDbcsBreak);
			}
			// Preserve normal word wrapping for ASCII words embedded in Korean text.
			if (lastWhitespaceBreak > 0) {
				return static_cast<int>(lastWhitespaceBreak);
			}
			// Long unbroken Korean/ASCII runs still must make progress. Never split
			// a CP949 pair or an @x formatting command.
			if (previousVisibleBoundary > 0) {
				return static_cast<int>(previousVisibleBoundary);
			}
			return static_cast<int>(next);
		}

		if (isWhitespace) {
			lastWhitespaceBreak = next;
		}

		// @0..@9 are zero-width state changes. Do not choose one by itself as a
		// wrap boundary, because that could strand the color command on the prior
		// line. @t is visible spacing and is handled like whitespace above.
		if (!isFormat || isTabCommand) {
			previousVisibleBoundary = next;
			if (isDbcs) {
				lastDbcsBreak = next;
			}
		}

		pos = next;
	}

	return static_cast<int>(length);
}
'''

    text += append_code
    return text


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_wordwrap_fix.py <TemplePlus source root>")

    root = Path(sys.argv[1]).resolve()
    path = root / "TemplePlus/fonts/fonts_hooks.cpp"
    text, encoding = read_source_text(path)
    patched = patch_fonts_hooks(text)
    path.write_bytes(patched.encode(encoding))

    verify, _ = read_source_text(path)
    required = [
        "0x101E8B20",
        "KR_HELP_WORDWRAP_CP949",
        "FontWordWrapFn",
        "previousVisibleBoundary",
        "source-byte count",
    ]
    for needle in required:
        if needle not in verify:
            raise RuntimeError(f"verification failed: missing {needle}")

    forbidden = [
        "0x1018D720",
        "KrHelpCp949BytesToUtf16Units",
        "KR_HELP_POSTPARSE",
    ]
    for needle in forbidden:
        if needle in verify:
            raise RuntimeError(f"forbidden legacy experiment marker present: {needle}")

    print(f"HELP_WORDWRAP_PATCH_OK [{encoding}]")


if __name__ == "__main__":
    main()
