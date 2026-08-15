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


def patch_textengine_h(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    anchor = """\t\tvoid MeasureText(const TextStyle &style, const std::string &text, TextMetrics &metrics);\n\n\t\tvoid SetRenderTarget(ID3D11Texture2D *renderTarget);\n"""
    replacement = """\t\tvoid MeasureText(const TextStyle &style, const std::string &text, TextMetrics &metrics);\n\n\t\t// Hit-test the exact DirectWrite layout used by RenderText(FormattedText).\n\t\t// Coordinates are relative to the layout rectangle. Returns false when\n\t\t// the point is outside the rendered text.\n\t\tbool HitTestText(const FormattedText &formattedStr, uint32_t width, uint32_t height,\n\t\t\tfloat x, float y, uint32_t &textPosition);\n\n\t\tvoid SetRenderTarget(ID3D11Texture2D *renderTarget);\n"""
    return replace_once(text, anchor, replacement, "TextEngine HitTest declaration")


def patch_textengine_cpp(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    anchor = """\tvoid TextEngine::MeasureText(const TextStyle & style, const std::string& text, TextMetrics &metrics)\n\t{\n\t\tMeasureText(style, local_to_ucs2(text), metrics);\n\t}\n\n\tvoid TextEngine::SetRenderTarget(ID3D11Texture2D * renderTarget)\n"""
    replacement = """\tvoid TextEngine::MeasureText(const TextStyle & style, const std::string& text, TextMetrics &metrics)\n\t{\n\t\tMeasureText(style, local_to_ucs2(text), metrics);\n\t}\n\n\tbool TextEngine::HitTestText(const FormattedText &formattedStr, uint32_t width, uint32_t height,\n\t\tfloat x, float y, uint32_t &textPosition)\n\t{\n\t\tauto textLayout = mImpl->GetTextLayout(width, height, formattedStr);\n\n\t\tBOOL trailingHit = FALSE;\n\t\tBOOL isInside = FALSE;\n\t\tDWRITE_HIT_TEST_METRICS hitMetrics{};\n\t\tauto hr = textLayout->HitTestPoint(x, y, &trailingHit, &isInside, &hitMetrics);\n\t\tif (FAILED(hr) || !isInside) {\n\t\t\treturn false;\n\t\t}\n\n\t\t// Keep the leading UTF-16 position of the glyph cluster even on its\n\t\t// trailing half. The caller maps that position back to the start byte of\n\t\t// the original CP949 unit, keeping it inside D20HelpLink's byte range.\n\t\ttextPosition = hitMetrics.textPosition;\n\t\treturn true;\n\t}\n\n\tvoid TextEngine::SetRenderTarget(ID3D11Texture2D * renderTarget)\n"""
    return replace_once(text, anchor, replacement, "TextEngine HitTest implementation")


def patch_fonts_h(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    anchor = """\tvoid Measure(const TigFont &font, const TigTextStyle &style, TigFontMetrics &metrics);\n\nprivate:\n"""
    replacement = """\tvoid Measure(const TigFont &font, const TigTextStyle &style, TigFontMetrics &metrics);\n\n\t// Returns 0 for a hit, 1 when the point is outside the rendered text, and\n\t// 3 when this font/path is unsupported and the legacy caller should fall back.\n\tint HitTest(gsl::cstring_span<> text, const TigFont &font, const TigRect &extents,\n\t\tconst TigTextStyle &style, int x, int y, int &sourceBytePos);\n\nprivate:\n"""
    return replace_once(text, anchor, replacement, "TextLayouter HitTest declaration")


def patch_fonts_layout(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "KR_HELP_DWRITE_HITTEST" in text:
        raise RuntimeError("DirectWrite hit-test patch already present")

    include_anchor = "#include <gamesystems/legacy.h>\n"
    text = replace_once(text, include_anchor, include_anchor + "#include <vector>\n", "fonts_layout vector include")

    layout_anchor = "void TextLayouter::LayoutAndDraw(gsl::cstring_span<> text, const TigFont& font, TigRect& extents, TigTextStyle& style) {\n"
    hit_test_code = r'''// KR_HELP_DWRITE_HITTEST
namespace {

bool KrHitTestIsCp949TrailByte(unsigned char ch) {
	return (ch >= 0x41 && ch <= 0x5A)
		|| (ch >= 0x61 && ch <= 0x7A)
		|| (ch >= 0x81 && ch <= 0xFE);
}

size_t KrHitTestNextSourceUnit(gsl::cstring_span<> text, size_t pos) {
	auto length = static_cast<size_t>(text.size());
	if (pos >= length) {
		return length;
	}

	auto ch = static_cast<unsigned char>(text[static_cast<int>(pos)]);
	if (ch >= 0x81 && ch <= 0xFE && pos + 1 < length
		&& KrHitTestIsCp949TrailByte(static_cast<unsigned char>(text[static_cast<int>(pos + 1)]))) {
		return pos + 2;
	}
	return pos + 1;
}

bool KrBuildFormattedToSourceByteMap(gsl::cstring_span<> text,
	const gfx::FormattedText &formatted,
	std::vector<uint32_t> &sourceByteMap) {

	sourceByteMap.clear();
	sourceByteMap.reserve(formatted.text.size() + 1);

	const auto length = static_cast<size_t>(text.size());
	for (size_t pos = 0; pos < length;) {
		auto ch = static_cast<unsigned char>(text[static_cast<int>(pos)]);

		// Match ProcessString exactly: @0..@9 disappear from the DirectWrite
		// string; @t becomes one tab character.
		if (ch == '@' && pos + 1 < length) {
			auto command = text[static_cast<int>(pos + 1)];
			if (command >= '0' && command <= '9') {
				pos += 2;
				continue;
			}
			if (command == 't') {
				sourceByteMap.push_back(static_cast<uint32_t>(pos));
				pos += 2;
				continue;
			}
		}

		auto next = KrHitTestNextSourceUnit(text, pos);
		std::string sourceUnit(&text[static_cast<int>(pos)], next - pos);
		auto decoded = legacy_to_ucs2(sourceUnit);
		if (decoded.empty()) {
			return false;
		}

		for (size_t i = 0; i < decoded.size(); ++i) {
			sourceByteMap.push_back(static_cast<uint32_t>(pos));
		}
		pos = next;
	}

	// Sentinel for validation / end-of-text. A valid glyph hit must be before it.
	sourceByteMap.push_back(static_cast<uint32_t>(length));
	return sourceByteMap.size() == formatted.text.size() + 1;
}

}

int TextLayouter::HitTest(gsl::cstring_span<> text, const TigFont &font, const TigRect &extents,
	const TigTextStyle &style, int x, int y, int &sourceBytePos) {

	auto it = mMapping->find(font.name);
	if (it == mMapping->end()) {
		return 3;
	}

	auto tabPos = style.field4c - extents.x;
	auto textStyle = it->second;
	ApplyStyle(style, tabPos, textStyle);

	bool isLegacyFormattedStr = std::find(text.begin(), text.end(), '@') != text.end();
	gfx::FormattedText formatted;
	if (isLegacyFormattedStr) {
		formatted = ProcessString(textStyle, style, text);
	} else {
		formatted.text = legacy_to_ucs2(to_string(text));
		formatted.defaultStyle = textStyle;
	}

	TigRect hitExtents = extents;
	if (hitExtents.width <= 0 || hitExtents.height <= 0) {
		gfx::TextMetrics metrics;
		mTextEngine.MeasureText(formatted, metrics);
		if (hitExtents.width <= 0) {
			hitExtents.width = metrics.width;
		}
		if (hitExtents.height <= 0) {
			hitExtents.height = metrics.height;
		}
	}

	if (x < hitExtents.x || y < hitExtents.y) {
		return 1;
	}

	uint32_t utf16Pos = 0;
	if (!mTextEngine.HitTestText(formatted,
		static_cast<uint32_t>(hitExtents.width),
		static_cast<uint32_t>(hitExtents.height),
		static_cast<float>(x - hitExtents.x),
		static_cast<float>(y - hitExtents.y),
		utf16Pos)) {
		return 1;
	}

	std::vector<uint32_t> sourceByteMap;
	if (!KrBuildFormattedToSourceByteMap(text, formatted, sourceByteMap)
		|| utf16Pos >= formatted.text.size()
		|| utf16Pos >= sourceByteMap.size() - 1) {
		return 3;
	}

	sourceBytePos = static_cast<int>(sourceByteMap[utf16Pos]);
	logger->info("KR_HELP_DIAG DWRITE x={} y={} localX={} localY={} utf16={} sourceByte={} textW={} textH={}",
		x, y, x - hitExtents.x, y - hitExtents.y, utf16Pos, sourceBytePos,
		hitExtents.width, hitExtents.height);
	return 0;
}

'''
    return replace_once(text, layout_anchor, hit_test_code + layout_anchor, "TextLayouter DirectWrite HitTest")


def patch_fonts_hooks(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "KR_HELP_HITTEST_CP949" in text:
        raise RuntimeError("FontHitTest patch already present")

    addresses_end = """} addresses;\n\n// Font Rendering Replacement\n"""
    hittest_type = """} addresses;\n\nusing FontHitTestFn = int(__cdecl *)(const char*, TigRect*, TigTextStyle*, int, int, int*);\nstatic FontHitTestFn orgFontHitTest = nullptr;\n\n// Font Rendering Replacement\n"""
    text = replace_once(text, addresses_end, hittest_type, "FontHitTest typedef")

    class_anchor = """\tstatic int FontDraw(const char* text, TigRect* extents, TigTextStyle* style);\n\t\n\tstatic int FontMeasure(const TigTextStyle &style, TigFontMetrics &metrics);\n"""
    class_replacement = """\tstatic int FontDraw(const char* text, TigRect* extents, TigTextStyle* style);\n\t\n\tstatic int FontMeasure(const TigTextStyle &style, TigFontMetrics &metrics);\n\n\tstatic int FontHitTest(const char* text, TigRect* extents, TigTextStyle* style,\n\t\tint x, int y, int* textPos);\n"""
    text = replace_once(text, class_anchor, class_replacement, "FontHitTest declaration")

    apply_anchor = """void FontRenderFix::apply() {\n\treplaceFunction(0x101EAF30, FontDraw);\n\treplaceFunction(0x101EA4E0, FontMeasure);\n}\n"""
    apply_replacement = """void FontRenderFix::apply() {\n\treplaceFunction(0x101EAF30, FontDraw);\n\treplaceFunction(0x101EA4E0, FontMeasure);\n\torgFontHitTest = replaceFunction<int(__cdecl)(const char*, TigRect*, TigTextStyle*, int, int, int*)>(\n\t\t0x101EA7F0, FontHitTest);\n\tlogger->info(\"KR_HELP_HITTEST_CP949 enabled (DirectWrite)\");\n}\n"""
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

}

int FontRenderFix::FontHitTest(const char* text, TigRect* extents, TigTextStyle* style,
	int x, int y, int* textPos) {

	// ASCII help already works in the native engine. Keep that path untouched.
	if (!orgFontHitTest || !text || !extents || !style || !textPos
		|| !KrContainsDbcsBytes(text) || *addresses.stackSize < 1) {
		return orgFontHitTest ? orgFontHitTest(text, extents, style, x, y, textPos) : 3;
	}

	// Help ScrollBox uses ordinary left-aligned non-rotated text. Do not broaden
	// this compatibility hook to layouts whose legacy geometry differs.
	constexpr int UnsupportedFlags = TTSF_CENTER | TTSF_TRUNCATE
		| TTSF_ROTATE | TTSF_ROTATE_OFF_CENTER;
	if (style->flags & UnsupportedFlags) {
		return orgFontHitTest(text, extents, style, x, y, textPos);
	}

	auto font = addresses.loadedFonts[addresses.fontStack[0]];
	auto& layouter = tig->GetTextLayouter();
	int sourceBytePos = 0;
	auto result = layouter.HitTest(span(text, strlen(text)), font, *extents, *style,
		x, y, sourceBytePos);
	if (result == 3) {
		return orgFontHitTest(text, extents, style, x, y, textPos);
	}
	if (result == 0) {
		*textPos = sourceBytePos;
	}
	return result;
}
'''
    text += append_code
    return text


def patch_file(root: Path, rel: str, transform):
    path = root / rel
    text, encoding = read_source_text(path)
    patched = transform(text)
    if patched == text:
        raise RuntimeError(f"No changes made to {rel}")
    path.write_bytes(patched.encode(encoding))
    print(f"patched {rel} [{encoding}]")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_hittest_fix.py <TemplePlus source root>")

    root = Path(sys.argv[1]).resolve()
    patch_file(root, "Infrastructure/include/graphics/textengine.h", patch_textengine_h)
    patch_file(root, "Infrastructure/src/graphics/textengine.cpp", patch_textengine_cpp)
    patch_file(root, "TemplePlus/fonts/fonts.h", patch_fonts_h)
    patch_file(root, "TemplePlus/fonts/fonts_layout.cpp", patch_fonts_layout)
    patch_file(root, "TemplePlus/fonts/fonts_hooks.cpp", patch_fonts_hooks)

    checks = {
        "Infrastructure/include/graphics/textengine.h": "HitTestText",
        "Infrastructure/src/graphics/textengine.cpp": "HitTestPoint",
        "TemplePlus/fonts/fonts.h": "int HitTest(gsl::cstring_span<>",
        "TemplePlus/fonts/fonts_layout.cpp": "KR_HELP_DWRITE_HITTEST",
        "TemplePlus/fonts/fonts_hooks.cpp": "KR_HELP_HITTEST_CP949 enabled (DirectWrite)",
    }
    for rel, needle in checks.items():
        verify, _ = read_source_text(root / rel)
        if needle not in verify:
            raise RuntimeError(f"verification failed: {rel} missing {needle}")

    hooks, _ = read_source_text(root / "TemplePlus/fonts/fonts_hooks.cpp")
    if "0x1018D720" in hooks:
        raise RuntimeError("forbidden TEST4 ScrollBox hook present")

    print("HELP_DIRECTWRITE_HITTEST_PATCH_OK")


if __name__ == "__main__":
    main()
