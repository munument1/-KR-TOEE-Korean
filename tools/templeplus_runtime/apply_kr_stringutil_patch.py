#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
p = ROOT / "Infrastructure/stringutil.cpp"
if not p.is_file():
    raise SystemExit(f"[MISSING] {p}")

raw = p.read_bytes()
nl = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

old = '''std::string ucs2_to_local(const std::wstring&s) {
	
	auto slength = (int)s.length() + 1;
	auto len = WideCharToMultiByte(CP_ACP, 0, s.c_str(), slength, 0, 0, 0, 0);
	
	std::string result(len, '\\0');
	WideCharToMultiByte(CP_ACP, 0, s.c_str(), slength, &result[0], len, 0, 0);
	result.resize(strlen(result.c_str()));
	return result;

}

std::wstring local_to_ucs2(const std::string &s) {

	auto len = MultiByteToWideChar(CP_ACP, 0, s.c_str(), s.length(), nullptr, 0);

	std::wstring result(len, '\\0');
	MultiByteToWideChar(CP_ACP, 0, s.c_str(), s.length(), &result[0], len);
	result.resize(result.length());
	return result;

}
'''

new = '''std::string ucs2_to_local(const std::wstring&s) {
	// Korean runtime: keep the narrow side UTF-8 so DirectWrite/TemplePlus-native
	// text paths can preserve Hangul independent of the Windows system locale.
	if (s.empty())
		return {};

	auto len = WideCharToMultiByte(CP_UTF8, 0, s.c_str(), (int)s.length(), nullptr, 0, nullptr, nullptr);
	if (len <= 0)
		return {};

	std::string result(len, '\\0');
	WideCharToMultiByte(CP_UTF8, 0, s.c_str(), (int)s.length(), &result[0], len, nullptr, nullptr);
	return result;
}

std::wstring local_to_ucs2(const std::string &s) {
	// Korean runtime: translated TemplePlus-native resources may be UTF-8,
	// while original ToEE MES/DLG/TAB resources are commonly CP949.
	// Validate UTF-8 strictly first; only then fall back to CP949.
	if (s.empty())
		return {};

	UINT codePage = CP_UTF8;
	DWORD flags = MB_ERR_INVALID_CHARS;
	auto len = MultiByteToWideChar(codePage, flags, s.c_str(), (int)s.length(), nullptr, 0);

	if (len <= 0) {
		codePage = 949; // CP949 / Unified Hangul Code
		flags = 0;
		len = MultiByteToWideChar(codePage, flags, s.c_str(), (int)s.length(), nullptr, 0);
	}

	if (len <= 0)
		return {};

	std::wstring result(len, L'\\0');
	MultiByteToWideChar(codePage, flags, s.c_str(), (int)s.length(), &result[0], len);
	return result;
}
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f"[GUARD FAILED] Infrastructure/stringutil.cpp expected v1.0.98 block once, found {count}")
text = text.replace(old, new, 1)
if nl == "\r\n":
    text = text.replace("\n", "\r\n")
p.write_bytes(text.encode("utf-8"))
print("[OK] Korean UTF-8 strict + CP949 fallback string conversion applied")
