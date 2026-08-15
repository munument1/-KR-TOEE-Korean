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


def patch_help_diag(root: Path):
    p = root / "TemplePlus/gamesystems/d20/d20_help.cpp"
    text, enc = read_source(p)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    old_generate = '''int HelpSystem::GenerateLinks(D20HelpTopic* d20ht)
{
\treturn orgGenerateLinks(d20ht);
}
'''
    new_generate = '''int HelpSystem::GenerateLinks(D20HelpTopic* d20ht)
{
\tauto result = orgGenerateLinks(d20ht);
\tif (d20ht) {
\t\tauto isRoot = d20ht->topicId == ElfHash::Hash("TAG_ROOT");
\t\tif (isRoot || d20ht->numLinks > 0) {
\t\t\tlogger->info("KR_HELP_META topicId={} root={} numLinks={} titleBytes={}",
\t\t\t\td20ht->topicId, isRoot ? 1 : 0, d20ht->numLinks,
\t\t\t\td20ht->title ? (int)strlen(d20ht->title) : -1);
\t\t\tif (d20ht->links && d20ht->numLinks > 0) {
\t\t\t\tauto count = d20ht->numLinks > 64 ? 64 : d20ht->numLinks;
\t\t\t\tfor (int i = 0; i < count; ++i) {
\t\t\t\t\tauto &link = d20ht->links[i];
\t\t\t\t\tlogger->info("KR_HELP_META_LINK idx={} roll={} target={} start={} end={}",
\t\t\t\t\t\ti, link.isRoll, link.linkedTopicId, link.startPos, link.endPos);
\t\t\t\t}
\t\t\t}
\t\t}
\t}
\treturn result;
}
'''
    if old_generate not in text:
        raise RuntimeError("GenerateLinks anchor not found")
    text = text.replace(old_generate, new_generate, 1)

    old_parser = '''int HelpSystem::LinkParser(D20HelpLink* d20hl, char* topicTitle, char** pos1, char** pos2, int* offsetOut)
{
\tif (strstr(topicTitle,"Disable Attacks"))
\t{
\t\tint dum = 1;
\t}
\tint result = orgLinkParser(d20hl, topicTitle, pos1, pos2, offsetOut);
\treturn result;
}
'''
    new_parser = '''int HelpSystem::LinkParser(D20HelpLink* d20hl, char* topicTitle, char** pos1, char** pos2, int* offsetOut)
{
\tint result = orgLinkParser(d20hl, topicTitle, pos1, pos2, offsetOut);
\tstatic int diagCount = 0;
\tif (d20hl && diagCount < 256 && (d20hl->linkedTopicId || d20hl->isRoll)) {
\t\tlogger->info("KR_HELP_META_PARSE result={} roll={} target={} start={} end={} offset={} sourceBytes={}",
\t\t\tresult, d20hl->isRoll, d20hl->linkedTopicId, d20hl->startPos, d20hl->endPos,
\t\t\toffsetOut ? *offsetOut : -1, topicTitle ? (int)strlen(topicTitle) : -1);
\t\tdiagCount++;
\t}
\treturn result;
}
'''
    if old_parser not in text:
        raise RuntimeError("LinkParser anchor not found")
    text = text.replace(old_parser, new_parser, 1)

    write_source(p, text, enc)
    print("KR_HELP_METADATA_DIAG_ADDED")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: apply_v102_help_metadata_diag.py <TemplePlus root>")
    root = Path(sys.argv[1]).resolve()
    patch_long_description(root)
    patch_help_diag(root)


if __name__ == "__main__":
    main()
