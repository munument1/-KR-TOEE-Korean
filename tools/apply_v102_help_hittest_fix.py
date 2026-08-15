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
    if "KR_HELP_HITTEST_CP949" in text:
        raise RuntimeError("FontHitTest patch already present")

    include_anchor = '#include "graphics/textengine.h"\n'
    text = replace_once(
        text,
        include_anchor,
        include_anchor + '#include <string>\n',
        "fonts_hooks include",
    )

    addresses_end = """} addresses;\n\n// Font Rendering Replacement\n"""
    hittest_type = """} addresses;\n\nusing FontHitTestFn = int(__cdecl *)(const char*, TigRect*, TigTextStyle*, int, int, int*);\nstatic FontHitTestFn orgFontHitTest = nullptr;\n\n// Font Rendering Replacement\n"""
    text = replace_once(text, addresses_end, hittest_type, "FontHitTest typedef")

    class_anchor = """\tstatic int FontDraw(const char* text, TigRect* extents, TigTextStyle* style);\n\t\n\tstatic int FontMeasure(const TigTextStyle &style, TigFontMetrics &metrics);\n"""
    class_replacement = """\tstatic int FontDraw(const char* text, TigRect* extents, TigTextStyle* style);\n\t\n\tstatic int FontMeasure(const TigTextStyle &style, TigFontMetrics &metrics);\n\n\tstatic int FontHitTest(const char* text, TigRect* extents, TigTextStyle* style,\n\t\tint x, int y, int* textPos);\n"""
    text = replace_once(text, class_anchor, class_replacement, "FontHitTest declaration")

    apply_anchor = """void FontRenderFix::apply() {\n\treplaceFunction(0x101EAF30, FontDraw);\n\treplaceFunction(0x101EA4E0, FontMeasure);\n}\n"""
    apply_replacement = """void FontRenderFix::apply() {\n\treplaceFunction(0x101EAF30, FontDraw);\n\treplaceFunction(0x101EA4E0, FontMeasure);\n\torgFontHitTest = replaceFunction<int(__cdecl)(const char*, TigRect*, TigTextStyle*, int, int, int*)>(\n\t\t0x101EA7F0, FontHitTest);\n\tlogger->info(\"KR_HELP_HITTEST_CP949 enabled\");\n}\n"""
    text = replace_once(text, apply_anchor, apply_replacement, "FontHitTest hook")

    append_code = r'''

namespace {

bool KrContainsDbcsBytes(const char* text) {
	if (!text) {
		return false;
	}
	for (auto p = reinterpret_cast<const unsigned char*>(text); *p; ++p) {
		if (*p >= 0x81) {
			return true;
		}
	}
	return false;
}

bool KrIsCp949TrailByte(unsigned char ch) {
	return (ch >= 0x41 && ch <= 0x5A)
		|| (ch >= 0x61 && ch <= 0x7A)
		|| (ch >= 0x81 && ch <= 0xFE);
}

size_t KrNextCp949Unit(const char* text, size_t length, size_t pos) {
	if (pos >= length) {
		return length;
	}

	auto ch = static_cast<unsigned char>(text[pos]);

	// Legacy ToEE formatting commands occupy two source bytes but either have
	// zero width (@0..@9) or render as one tab (@t). Keep them atomic so the
	// returned position remains in the same byte coordinate system as
	// D20HelpLink.startPos/length.
	if (ch == '@' && pos + 1 < length) {
		auto command = text[pos + 1];
		if ((command >= '0' && command <= '9') || command == 't') {
			return pos + 2;
		}
	}

	// Windows CP949/UHC double-byte character. This is intentionally byte based:
	// the legacy help metadata consumed by 0x100E7070 is also byte based.
	if (ch >= 0x81 && ch <= 0xFE && pos + 1 < length
		&& KrIsCp949TrailByte(static_cast<unsigned char>(text[pos + 1]))) {
		return pos + 2;
	}

	return pos + 1;
}

}

int FontRenderFix::FontHitTest(const char* text, TigRect* extents, TigTextStyle* style,
	int x, int y, int* textPos) {

	// Keep every pre-existing path byte-for-byte equivalent unless the text
	// actually contains CP949/DBCS data. ASCII help links already work in FIX3.
	if (!orgFontHitTest || !text || !extents || !style || !textPos
		|| !KrContainsDbcsBytes(text)) {
		return orgFontHitTest ? orgFontHitTest(text, extents, style, x, y, textPos) : 3;
	}

	// The help ScrollBox uses ordinary left-aligned, non-rotated text. Preserve
	// the vanilla hit tester for modes where prefix-width hit testing would not
	// exactly match the rendered origin.
	constexpr int UnsupportedFlags = TTSF_CENTER | TTSF_TRUNCATE
		| TTSF_ROTATE | TTSF_ROTATE_OFF_CENTER;
	if (style->flags & UnsupportedFlags) {
		return orgFontHitTest(text, extents, style, x, y, textPos);
	}

	TigTextStyle measureStyle = *style;
	// LayoutAndDraw converts the absolute tab stop to a position relative to the
	// current extents. Do the same here so prefix measurement matches rendering.
	if (measureStyle.field4c > 0) {
		measureStyle.field4c -= extents->x;
	}

	TigFontMetrics fullMetrics;
	fullMetrics.text = text;
	fullMetrics.width = 0;
	fullMetrics.height = 0;
	if (FontMeasure(measureStyle, fullMetrics) != 0) {
		return orgFontHitTest(text, extents, style, x, y, textPos);
	}

	if (extents->width <= 0) {
		extents->width = fullMetrics.width;
	}
	if (extents->height <= 0) {
		extents->height = fullMetrics.height;
	}

	if (y < extents->y || y >= extents->y + extents->height
		|| x < extents->x) {
		return 1;
	}

	auto relativeX = x - extents->x;
	if (relativeX >= fullMetrics.width) {
		return 1;
	}

	const auto length = strlen(text);
	std::string prefix;
	prefix.reserve(length);

	int previousWidth = 0;
	for (size_t pos = 0; pos < length;) {
		auto next = KrNextCp949Unit(text, length, pos);
		prefix.assign(text, next);

		TigFontMetrics prefixMetrics;
		prefixMetrics.text = prefix.c_str();
		prefixMetrics.width = 0;
		prefixMetrics.height = 0;
		if (FontMeasure(measureStyle, prefixMetrics) != 0) {
			return orgFontHitTest(text, extents, style, x, y, textPos);
		}

		// @0..@9 have zero width; skip them. For a visible CP949 glyph, ASCII
		// glyph, whitespace, or tab, return its source byte offset. The ScrollBox
		// then adds the line start and 0x100E7070 compares that byte position to
		// D20HelpLink.startPos/length.
		if (prefixMetrics.width > previousWidth && relativeX < prefixMetrics.width) {
			*textPos = static_cast<int>(pos);
			logger->info(\"KR_HELP_DIAG HIT x={} y={} relX={} local={} prefixW={} fullW={}\",\n				x, y, relativeX, *textPos, prefixMetrics.width, fullMetrics.width);
			return 0;
		}

		previousWidth = prefixMetrics.width;
		pos = next;
	}

	return 1;
}
'''

    text += append_code
    return text


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_hittest_fix.py <TemplePlus source root>")

    root = Path(sys.argv[1]).resolve()
    path = root / "TemplePlus/fonts/fonts_hooks.cpp"
    text, encoding = read_source_text(path)
    patched = patch_fonts_hooks(text)
    path.write_bytes(patched.encode(encoding))

    verify, _ = read_source_text(path)
    required = [
        "0x101EA7F0",
        "KR_HELP_HITTEST_CP949",
        "KR_HELP_DIAG HIT",
        "KrNextCp949Unit",
        "D20HelpLink.startPos/length",
    ]
    for needle in required:
        if needle not in verify:
            raise RuntimeError(f"verification failed: missing {needle}")

    print(f"HELP_HITTEST_DIAG_PATCH_OK [{encoding}]")


if __name__ == "__main__":
    main()
