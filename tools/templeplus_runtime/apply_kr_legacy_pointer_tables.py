#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
p = ROOT / "TemplePlus/gamesystems/d20/d20stats.cpp"
if not p.is_file():
    raise SystemExit(f"[MISSING] {p}")

raw = p.read_bytes()
nl = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

anchor = (
    "\tmesFuncs.Open(\"mes\\\\stat.mes\", &statMes);\n"
    "\tmesFuncs.Open(\"mes\\\\stat_ext.mes\", &statMesExt);\n"
    "\n"
    "\tmesFuncs.Open(\"rules\\\\stat.mes\", &statRules);\n"
)

insert = (
    "\tmesFuncs.Open(\"mes\\\\stat.mes\", &statMes);\n"
    "\tmesFuncs.Open(\"mes\\\\stat_ext.mes\", &statMesExt);\n"
    "\n"
    "\t// Some legacy UI code reads these temple.dll pointer tables directly\n"
    "\t// instead of calling the stat accessor functions. Synchronize them\n"
    "\t// from localized stat.mes after the MES system is initialized.\n"
    "\tauto &legacyAlignmentNames = temple::GetRef<const char*[11]>(0x10AAE89C);\n"
    "\tconst int legacyAlignments[] = { 0, 1, 2, 4, 5, 6, 8, 9, 10 };\n"
    "\tfor (auto alignment : legacyAlignments) {\n"
    "\t\tMesLine line(6000 + alignment);\n"
    "\t\tmesFuncs.GetLine_Safe(statMes, &line);\n"
    "\t\tlegacyAlignmentNames[alignment] = line.value;\n"
    "\t}\n"
    "\n"
    "\tauto &legacyGenderNames = temple::GetRef<const char*[2]>(0x10AAE410);\n"
    "\tfor (auto gender = 0; gender < 2; ++gender) {\n"
    "\t\tMesLine line(4000 + gender);\n"
    "\t\tmesFuncs.GetLine_Safe(statMes, &line);\n"
    "\t\tlegacyGenderNames[gender] = line.value;\n"
    "\t}\n"
    "\n"
    "\tmesFuncs.Open(\"rules\\\\stat.mes\", &statRules);\n"
)

count = text.count(anchor)
if count != 1:
    raise SystemExit(f"[GUARD FAILED] expected one D20StatsSystem::Init anchor, found {count}")
text = text.replace(anchor, insert, 1)

if nl == "\r\n":
    text = text.replace("\n", "\r\n")
p.write_bytes(text.encode("utf-8"))
print("[OK] synchronized legacy alignment/gender pointer tables from stat.mes")
