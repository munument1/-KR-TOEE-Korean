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
    if "KR_HELP_CLICK_DIAG" in text:
        raise RuntimeError("help click diagnostics already present")

    class_anchor = """class HelpSystemReplacements : TempleFix\n{\npublic:\n\tstatic int TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns);\n"""
    class_replacement = """class HelpSystemReplacements : TempleFix\n{\npublic:\n\tstatic int TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns);\n\tstatic int TabLineParserFinalFiltered(TigTabParser const* tabParser, int lineIdxx, char** columns);\n"""
    text = replace_once(text, class_anchor, class_replacement, "final-filter declaration")

    pointer_anchor = """int(__cdecl*HelpSystem::orgGenerateLinks)(D20HelpTopic * d20ht);\nint(__cdecl*HelpSystem::orgLinkParser)(D20HelpLink* d20hl, char * topicTitle, char **pos1, char **pos2, int *offsetOut);\n"""
    pointer_replacement = pointer_anchor + """\n// KR_HELP_CLICK_DIAG\n// Exact native ABI verified from temple.dll 0x100E7070. The third argument is\n// the absolute ScrollBox source-byte position after the current line-start\n// offset has been added by 0x1018CCF0. This wrapper is diagnostic only.\nusing HelpFindLinkFn = D20HelpLink*(__cdecl *)(D20HelpLink*, int, int);\nstatic HelpFindLinkFn orgHelpFindLink = nullptr;\nstatic D20HelpLink* __cdecl HelpFindLinkDiag(D20HelpLink* links, int count, int textPos);\n"""
    text = replace_once(text, pointer_anchor, pointer_replacement, "help find-link diagnostic declarations")

    apply_anchor = """void HelpSystem::apply()\n{\n\treplaceFunction(0x100E7030, GetTopic);\n\torgGenerateLinks = replaceFunction(0x100E7280, GenerateLinks);\n\torgLinkParser = replaceFunction(0x100E7670, LinkParser);\n\treplaceFunction(0x100E7E80, HelpTabInit);\n}\n"""
    apply_replacement = """void HelpSystem::apply()\n{\n\treplaceFunction(0x100E7030, GetTopic);\n\torgGenerateLinks = replaceFunction(0x100E7280, GenerateLinks);\n\torgLinkParser = replaceFunction(0x100E7670, LinkParser);\n\treplaceFunction(0x100E7E80, HelpTabInit);\n\torgHelpFindLink = replaceFunction<D20HelpLink*(__cdecl)(D20HelpLink*, int, int)>(\n\t\t0x100E7070, HelpFindLinkDiag);\n\tlogger->info(\"KR_HELP_CLICK_DIAG enabled\");\n}\n"""
    text = replace_once(text, apply_anchor, apply_replacement, "help find-link diagnostic hook")

    click_toggle_anchor = """void HelpSystem::ClickForHelpToggle() const\n{\n"""
    click_diag_definition = """D20HelpLink* __cdecl HelpFindLinkDiag(D20HelpLink* links, int count, int textPos)\n{\n\tauto result = orgHelpFindLink ? orgHelpFindLink(links, count, textPos) : nullptr;\n\tint selected = -1;\n\tif (result && links) {\n\t\tselected = static_cast<int>(result - links);\n\t}\n\n\tlogger->info(\"KR_HELP_DIAG FIND abs={} count={} selected={}\", textPos, count, selected);\n\tif (links && count > 0 && count <= 64) {\n\t\tfor (int i = 0; i < count; ++i) {\n\t\t\tauto& link = links[i];\n\t\t\tlogger->info(\"KR_HELP_DIAG RANGE idx={} roll={} topic={} start={} len={}\",\n\t\t\t\ti, link.isRoll, link.linkedTopicId, link.startPos, link.endPos);\n\t\t}\n\t}\n\tif (result) {\n\t\tlogger->info(\"KR_HELP_DIAG SELECT idx={} topic={} start={} len={}\",\n\t\t\tselected, result->linkedTopicId, result->startPos, result->endPos);\n\t}\n\treturn result;\n}\n\nvoid HelpSystem::ClickForHelpToggle() const\n{\n"""
    text = replace_once(text, click_toggle_anchor, click_diag_definition, "help find-link diagnostic definition")

    anchor = """int HelpSystemReplacements::TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns)\n{\n\tauto tabEntry = (HelpTabEntry*)columns;\n\tD20HelpTopic * d20ht = new D20HelpTopic;\n"""

    replacement = """int HelpSystemReplacements::TabLineParserPriliminary(TigTabParser const* tabParser, int lineIdxx, char** columns)\n{\n\tauto tabEntry = (HelpTabEntry*)columns;\n\n\t// KR_HELP_BASE_RECORD_FILTER\n\t// The frozen Korean mes/help.tab contains the canonical six-column TAG_*\n\t// records plus LF-delimited carry-over/reference lines with no TAB columns.\n\t// TigTabParser invokes both parsing callbacks for those short rows. Keep them\n\t// out of BOTH passes: if preliminary skips a row but final still receives it,\n\t// vanilla 0x100E7CF0 performs a failed hashtable lookup and then dereferences\n\t// the unchecked output pointer, corrupting topic/link memory.\n\t//\n\t// Scope this strictly to the frozen base help file. TemplePlus extension/user\n\t// help files retain their original behavior. Canonical base records are TAG_*.\n\tif (tabParser && tabParser->filename\n\t\t&& _stricmp(tabParser->filename, \"mes\\\\help.tab\") == 0\n\t\t&& strncmp(tabEntry->id, \"TAG_\", 4) != 0) {\n\t\tstatic bool filterLogged = false;\n\t\tif (!filterLogged) {\n\t\t\tlogger->info(\"KR_HELP_BASE_RECORD_FILTER enabled\");\n\t\t\tfilterLogged = true;\n\t\t}\n\t\treturn 0;\n\t}\n\n\tD20HelpTopic * d20ht = new D20HelpTopic;\n"""
    text = replace_once(text, anchor, replacement, "TabLineParserPriliminary filter")

    final_init_anchor = "\ttabOrg.Init(addresses.HelpSystemTabLineParserFinal);\n"
    final_init_replacement = "\ttabOrg.Init(HelpSystemReplacements::TabLineParserFinalFiltered);\n"
    text = replace_once(text, final_init_anchor, final_init_replacement, "base final parser wrapper")

    final_def_anchor = """D20HelpTopic* HelpSystem::GetTopic(int topicId)\n{\n"""
    final_def = """int HelpSystemReplacements::TabLineParserFinalFiltered(TigTabParser const* tabParser, int lineIdxx, char** columns)\n{\n\tauto tabEntry = (HelpTabEntry*)columns;\n\tif (tabParser && tabParser->filename\n\t\t&& _stricmp(tabParser->filename, \"mes\\\\help.tab\") == 0\n\t\t&& strncmp(tabEntry->id, \"TAG_\", 4) != 0) {\n\t\tstatic bool finalFilterLogged = false;\n\t\tif (!finalFilterLogged) {\n\t\t\tlogger->info(\"KR_HELP_BASE_FINAL_FILTER enabled\");\n\t\t\tfinalFilterLogged = true;\n\t\t}\n\t\treturn 0;\n\t}\n\n\treturn addresses.HelpSystemTabLineParserFinal(tabParser, lineIdxx, columns);\n}\n\nD20HelpTopic* HelpSystem::GetTopic(int topicId)\n{\n"""
    text = replace_once(text, final_def_anchor, final_def, "final-filter definition")

    return text


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
        "KR_HELP_BASE_FINAL_FILTER",
        "KR_HELP_CLICK_DIAG",
        "0x100E7070",
        "HelpFindLinkDiag",
        "KR_HELP_DIAG FIND",
        "KR_HELP_DIAG RANGE",
        "KR_HELP_DIAG SELECT",
        "TabLineParserFinalFiltered",
        'tabOrg.Init(HelpSystemReplacements::TabLineParserFinalFiltered)',
        '_stricmp(tabParser->filename, "mes\\\\help.tab")',
        'strncmp(tabEntry->id, "TAG_", 4)',
        'return addresses.HelpSystemTabLineParserFinal(tabParser, lineIdxx, columns);',
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

    print(f"HELP_BASE_FILTER_AND_CLICK_DIAG_OK [{encoding}]")


if __name__ == "__main__":
    main()
