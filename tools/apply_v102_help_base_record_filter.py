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


def patch_d20_help(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "KR_HELP_BASE_RECORD_FILTER" in text:
        raise RuntimeError("base help record filter already present")

    anchor = """int HelpSystemReplacements::TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns)\n{\n\tauto tabEntry = (HelpTabEntry*)columns;\n\tD20HelpTopic * d20ht = new D20HelpTopic;\n"""

    replacement = """int HelpSystemReplacements::TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns)\n{\n\tauto tabEntry = (HelpTabEntry*)columns;\n\n\t// KR_HELP_BASE_RECORD_FILTER\n\t// The frozen Korean mes/help.tab contains the canonical six-column TAG_*\n\t// records plus LF-delimited carry-over/reference lines with no TAB columns.\n\t// TigTabParser still invokes this preliminary callback for those short rows\n\t// and fills the missing columns with empty strings.  Without this guard the\n\t// legacy help linker registers the carry-over text itself as a help topic,\n\t// attaches it to TAG_ROOT and pollutes prev/next sibling navigation.\n\t//\n\t// Scope this strictly to the base help file. TemplePlus extension/user help\n\t// files retain their original behavior. All canonical records in the frozen\n\t// Korean base file use TAG_* identifiers.\n\tif (tabParser && tabParser->filename\n\t\t&& _stricmp(tabParser->filename, \"mes\\\\help.tab\") == 0\n\t\t&& strncmp(tabEntry->id, \"TAG_\", 4) != 0) {\n\t\tstatic bool filterLogged = false;\n\t\tif (!filterLogged) {\n\t\t\tlogger->info(\"KR_HELP_BASE_RECORD_FILTER enabled\");\n\t\t\tfilterLogged = true;\n\t\t}\n\t\treturn 0;\n\t}\n\n\tD20HelpTopic * d20ht = new D20HelpTopic;\n"""

    return replace_once(text, anchor, replacement, "TabLineParserPriliminary filter")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_base_record_filter.py <TemplePlus source root>")

    root = Path(sys.argv[1]).resolve()
    path = root / "TemplePlus/gamesystems/d20/d20_help.cpp"
    text, encoding = read_source_text(path)
    patched = patch_d20_help(text)
    path.write_bytes(patched.encode(encoding))

    verify, _ = read_source_text(path)
    required = [
        "KR_HELP_BASE_RECORD_FILTER",
        '_stricmp(tabParser->filename, "mes\\\\help.tab")',
        'strncmp(tabEntry->id, "TAG_", 4)',
    ]
    for needle in required:
        if needle not in verify:
            raise RuntimeError(f"verification failed: missing {needle}")

    forbidden = [
        "KrHelpCp949BytesToUtf16Units",
        "KR_HELP_POSTPARSE",
        "0x1018D720",
    ]
    for needle in forbidden:
        if needle in verify:
            raise RuntimeError(f"forbidden legacy experiment marker present: {needle}")

    print(f"HELP_BASE_RECORD_FILTER_OK [{encoding}]")


if __name__ == "__main__":
    main()
