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


def patch_help_postparse_diag(root: Path):
    p = root / "TemplePlus/gamesystems/d20/d20_help.cpp"
    text, enc = read_source(p)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    old = '''\tlogger->info("Done Parsing Help Data Extensions.");
\treturn 1;
}
'''
    new = '''\tlogger->info("Done Parsing Help Data Extensions.");

\t// KR diagnostic: inspect help-link metadata only after all help parsing is complete.
\t// Do not touch GenerateLinks/LinkParser callbacks and never dereference a suspicious
\t// link count. This keeps the diagnostic out of the parser's construction phase.
\tauto krRoot = GetTopic(ElfHash::Hash("TAG_ROOT"));
\tif (krRoot) {
\t\tlogger->info("KR_HELP_POSTPARSE rootTopic={} numLinks={} linksPresent={} vChildren={}",
\t\t\tkrRoot->topicId, krRoot->numLinks, krRoot->links ? 1 : 0, krRoot->vChildrenSize);
\t\tif (krRoot->links && krRoot->numLinks > 0 && krRoot->numLinks <= 128) {
\t\t\tauto count = krRoot->numLinks > 64 ? 64 : krRoot->numLinks;
\t\t\tfor (int i = 0; i < count; ++i) {
\t\t\t\tauto &link = krRoot->links[i];
\t\t\t\tlogger->info("KR_HELP_POSTPARSE_LINK idx={} roll={} target={} start={} end={}",
\t\t\t\t\ti, link.isRoll, link.linkedTopicId, link.startPos, link.endPos);
\t\t\t}
\t\t} else if (krRoot->numLinks < 0 || krRoot->numLinks > 128) {
\t\t\tlogger->warn("KR_HELP_POSTPARSE suspicious root link count {}; not dereferencing", krRoot->numLinks);
\t\t}
\t} else {
\t\tlogger->warn("KR_HELP_POSTPARSE TAG_ROOT not found");
\t}
\treturn 1;
}
'''
    if old not in text:
        raise RuntimeError("HelpTabInit postparse anchor not found")
    text = text.replace(old, new, 1)
    write_source(p, text, enc)
    print("KR_HELP_POSTPARSE_DIAG_ADDED")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_postparse_diag.py <TemplePlus root>")
    root = Path(sys.argv[1]).resolve()
    patch_long_description(root)
    patch_help_postparse_diag(root)


if __name__ == "__main__":
    main()
