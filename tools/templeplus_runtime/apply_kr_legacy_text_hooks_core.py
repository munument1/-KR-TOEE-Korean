#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()

def read_source(rel):
    p = ROOT / rel
    if not p.is_file():
        raise SystemExit(f"[MISSING] {p}")
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8").replace("\r\n", "\n")
    return p, text, nl

def write_source(p, text, nl):
    text = text.replace("\r\n", "\n")
    if nl == "\r\n":
        text = text.replace("\n", "\r\n")
    p.write_bytes(text.encode("utf-8"))

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"[GUARD FAILED] {label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)

# d20stats.h
p, text, nl = read_source("TemplePlus/gamesystems/d20/d20stats.h")
text = replace_once(
    text,
    "\tconst char* GetAlignmentName(Alignment alignment);\n"
    "\tconst char* GetRaceName(Race race);\n",
    "\tconst char* GetAlignmentName(Alignment alignment);\n"
    "\tconst char* GetAlignmentShortDesc(Alignment alignment);\n"
    "\tconst char* GetRaceName(Race race);\n",
    "d20stats.h declaration"
)
write_source(p, text, nl)
print("[OK] d20stats.h")

# d20stats.cpp
p, text, nl = read_source("TemplePlus/gamesystems/d20/d20stats.cpp")
hook_anchor = (
    "\t\treplaceFunction<const char*(Stat)>(0x10073A20, [](Stat stat)->const char* {\n"
    "\t\t\treturn d20Stats.GetStatRulesString(stat);\n"
    "\t\t});\n"
)
hook_new = hook_anchor + (
    "\n"
    "\t\t// Localizable legacy stat strings still used directly by temple.dll UI.\n"
    "\t\treplaceFunction<const char*(int)>(0x10073A30, [](int genderId)->const char* {\n"
    "\t\t\treturn d20Stats.GetGenderName(genderId);\n"
    "\t\t});\n"
    "\t\treplaceFunction<const char*(Alignment)>(0x10073B40, [](Alignment alignment)->const char* {\n"
    "\t\t\treturn d20Stats.GetAlignmentShortDesc(alignment);\n"
    "\t\t});\n"
    "\t\treplaceFunction<const char*(Alignment)>(0x10073C20, [](Alignment alignment)->const char* {\n"
    "\t\t\treturn d20Stats.GetAlignmentName(alignment);\n"
    "\t\t});\n"
)
text = replace_once(text, hook_anchor, hook_new, "d20stats.cpp legacy stat hooks")

old_alignment = (
    "const char * D20StatsSystem::GetAlignmentName(Alignment alignment) {\n"
    "\treturn temple::GetRef<const char*[]>(0x10AAE89C)[alignment];\n"
    "}\n"
)
new_alignment = (
    "const char * D20StatsSystem::GetAlignmentName(Alignment alignment) {\n"
    "\tMesLine line(6000 + static_cast<int>(alignment));\n"
    "\tmesFuncs.GetLine_Safe(statMes, &line);\n"
    "\treturn line.value;\n"
    "}\n"
    "\n"
    "const char * D20StatsSystem::GetAlignmentShortDesc(Alignment alignment) {\n"
    "\tMesLine line(16000 + static_cast<int>(alignment));\n"
    "\tmesFuncs.GetLine_Safe(statMes, &line);\n"
    "\treturn line.value;\n"
    "}\n"
)
text = replace_once(text, old_alignment, new_alignment, "d20stats.cpp alignment MES lookup")

old_gender = (
    "const char * D20StatsSystem::GetGenderName(int genderId) {\n"
    "\treturn temple::GetRef<const char*[]>(0x10AAE410)[genderId];\n"
    "}\n"
)
new_gender = (
    "const char * D20StatsSystem::GetGenderName(int genderId) {\n"
    "\tMesLine line(4000 + genderId);\n"
    "\tmesFuncs.GetLine_Safe(statMes, &line);\n"
    "\treturn line.value;\n"
    "}\n"
)
text = replace_once(text, old_gender, new_gender, "d20stats.cpp gender MES lookup")
write_source(p, text, nl)
print("[OK] d20stats.cpp")

# description.cpp
p, text, nl = read_source("TemplePlus/description.cpp")
desc_hook_anchor = (
    "\tvoid apply() override {\n"
    "\n"
    "\t\t// fix for crafted items not showing long descriptions (the long description will be outdated of course)\n"
)
desc_hook_new = (
    "\tvoid apply() override {\n"
    "\n"
    "\t\t// Route legacy display names through TemplePlus' localized description lookup.\n"
    "\t\treplaceFunction<const char*(objHndl, objHndl)>(0x1001FA80, [](objHndl handle, objHndl observer) {\n"
    "\t\t\treturn description.getDisplayName(handle, observer);\n"
    "\t\t});\n"
    "\n"
    "\t\t// fix for crafted items not showing long descriptions (the long description will be outdated of course)\n"
)
text = replace_once(text, desc_hook_anchor, desc_hook_new, "description.cpp display-name hook")

old_display = (
    "const char* LegacyDescriptionSystem::getDisplayName(objHndl obj, objHndl observer)\n"
    "{\n"
    "\treturn _getDisplayName(obj, observer);\n"
    "}\n"
)
new_display = (
    "const char* LegacyDescriptionSystem::getDisplayName(objHndl obj, objHndl observer)\n"
    "{\n"
    "\tif (!obj)\n"
    "\t\treturn \"OBJ_HANDLE_NULL\";\n"
    "\n"
    "\tauto objBody = objSystem->GetObject(obj);\n"
    "\tif (!objBody)\n"
    "\t\treturn \"OBJ_HANDLE_NULL\";\n"
    "\n"
    "\tif (objBody->type == obj_t_key) {\n"
    "\t\tauto keyId = objBody->GetInt32(obj_f_key_key_id);\n"
    "\t\tif (keyId != 0)\n"
    "\t\t\treturn temple::GetRef<const char*(__cdecl)(int)>(0x100867E0)(keyId);\n"
    "\t}\n"
    "\n"
    "\tif (objBody->IsItem()) {\n"
    "\t\tint descrIdx;\n"
    "\t\tif (temple::GetRef<int>(0x10788098) || obj == observer || inventory.IsIdentified(obj))\n"
    "\t\t\tdescrIdx = objBody->GetInt32(obj_f_description);\n"
    "\t\telse\n"
    "\t\t\tdescrIdx = objBody->GetInt32(obj_f_item_description_unknown);\n"
    "\t\treturn GetDescriptionString(descrIdx);\n"
    "\t}\n"
    "\n"
    "\tif (objBody->IsPC())\n"
    "\t\treturn objBody->GetString(obj_f_pc_player_name);\n"
    "\n"
    "\tif (objBody->IsNPC()) {\n"
    "\t\tif (!observer)\n"
    "\t\t\tobserver = obj;\n"
    "\t\tauto descrId = temple::GetRef<int(__cdecl)(objHndl, objHndl)>(0x1007F670)(obj, observer);\n"
    "\t\treturn GetDescriptionString(descrId);\n"
    "\t}\n"
    "\n"
    "\treturn GetDescriptionString(objBody->GetInt32(obj_f_description));\n"
    "}\n"
)
text = replace_once(text, old_display, new_display, "description.cpp display-name implementation")
write_source(p, text, nl)
print("[OK] description.cpp")

print("CORE KR LEGACY TEXT HOOKS APPLIED")
