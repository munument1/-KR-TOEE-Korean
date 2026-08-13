#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
PATH = ROOT / "TemplePlus/gamesystems/d20/d20stats.cpp"

if not PATH.is_file():
    raise SystemExit(f"[MISSING] {PATH}")

raw = PATH.read_bytes()
newline = "\r\n" if b"\r\n" in raw else "\n"
text = raw.decode("utf-8").replace("\r\n", "\n")

# This patch is intentionally narrow. It must not inherit the discarded CORE/V2
# hooks or touch any global encoding conversion logic.
for forbidden in (
    "strict UTF-8 decode + CP949 fallback",
    "synchronize temple.dll legacy alignment pointer table",
    "Route legacy display names through TemplePlus",
):
    if forbidden in text:
        raise SystemExit(f"[GUARD FAILED] discarded runtime patch marker present: {forbidden}")

if "replaceFunction<const char*(Alignment)>(0x10073C20" in text:
    raise SystemExit("[GUARD FAILED] 0x10073C20 is already hooked")

anchor = (
    "\t\treplaceFunction<const char*(Stat)>(0x10073A20, [](Stat stat)->const char* {\n"
    "\t\t\treturn d20Stats.GetStatRulesString(stat);\n"
    "\t\t});\n"
)

insert = anchor + (
    "\n"
    "\t\t// KR minimal patch: party-alignment button labels only.\n"
    "\t\t// Return the existing CP949 stat.mes bytes unchanged so the proven\n"
    "\t\t// Korean legacy renderer remains the sole encoding boundary.\n"
    "\t\treplaceFunction<const char*(Alignment)>(0x10073C20, [](Alignment alignment)->const char* {\n"
    "\t\t\tMesLine line(6000 + static_cast<int>(alignment));\n"
    "\t\t\tmesFuncs.GetLine_Safe(d20Stats.statMes, &line);\n"
    "\t\t\treturn line.value;\n"
    "\t\t});\n"
)

count = text.count(anchor)
if count != 1:
    raise SystemExit(f"[GUARD FAILED] expected one hook anchor, found {count}")

text = text.replace(anchor, insert, 1)

# Source-level scope guard: this script must not alter the existing table-backed
# accessors. They are deliberately left alone for all other call paths.
required_unchanged = (
    "const char * D20StatsSystem::GetAlignmentName(Alignment alignment) {\n"
    "\treturn temple::GetRef<const char*[]>(0x10AAE89C)[alignment];\n"
    "}\n"
)
if required_unchanged not in text:
    raise SystemExit("[GUARD FAILED] GetAlignmentName legacy-table implementation changed")

if newline == "\r\n":
    text = text.replace("\n", "\r\n")
PATH.write_bytes(text.encode("utf-8"))

print("[OK] minimal 0x10073C20 alignment-name hook applied")
print("[OK] no alignment/gender pointer-table synchronization")
print("[OK] no 0x1001FA80 display-name hook")
print("[OK] no global string conversion changes")
