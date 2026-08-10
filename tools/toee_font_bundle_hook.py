from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import toee_apply_korean_translation as core

EXPECTED_FONTS = {
    "NanumBarunGothic.ttf": "9b872773134e2e4d8c0b17021266786576db06c843ede0d0b523b214a450756c",
    "NanumBarunGothicBold.ttf": "39bba4cd9bd2986143825c8654abbb62443914ab33b346c0c929a916f5d98bf2",
    "GraceSerif-Regular.ttf": "33eb8227c4ecd0cfa4e4ec18d9f448a9530dfc36bb8034bf3b409b572aba64d1",
    "GraceSerif-Bold.ttf": "bbdc46f95144d4705c03b2b93da43464adc71ad8c3519702c7e0f04ae8b75d25",
}

REQUIRED_STATIC_FILES = [
    "fonts/mapping.json",
    "fonts/LICENSE-NanumBarunGothic.txt",
    "fonts/LICENSE-GraceSerif.txt",
    "templeplus/text_styles.json",
    "templeplus/ui/main_menu.json",
    "templeplus/ui/main_menu_cinematics.json",
    "templeplus/ui/main_menu_setpieces.json",
]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _bundle_tpdata() -> Path:
    # PyInstaller onefile extracts --add-data resources below sys._MEIPASS.
    mei = getattr(sys, "_MEIPASS", None)
    if mei:
        return Path(mei) / "resources" / "font" / "tpdata"
    # Development fallback when executed from repository checkout.
    return Path(__file__).resolve().parents[1] / "font" / "tpdata"


def _arg_value(name: str) -> str | None:
    try:
        idx = sys.argv.index(name)
    except ValueError:
        return None
    return sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None


def _validate_bundle(src: Path) -> list[str]:
    errors: list[str] = []
    if not src.is_dir():
        return [f"TemplePlus 폰트 리소스 폴더가 없습니다: {src}"]

    fonts = src / "fonts"
    for name, expected in EXPECTED_FONTS.items():
        path = fonts / name
        if not path.is_file():
            errors.append(f"필수 폰트 누락: {name}")
            continue
        actual = _sha256(path)
        if actual.lower() != expected.lower():
            errors.append(f"폰트 SHA-256 불일치: {name} expected={expected} actual={actual}")

    for rel in REQUIRED_STATIC_FILES:
        if not (src / rel).is_file():
            errors.append(f"TemplePlus 설정/라이선스 누락: {rel}")
    return errors


def _update_report(output: Path, *, ok: bool, errors: list[str] | None = None) -> None:
    report_path = output / "PATCH_REPORT.json"
    if not report_path.is_file():
        return
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return
    summary = report.setdefault("summary", {})
    summary["font_bundle_verified"] = ok
    summary["font_files"] = list(EXPECTED_FONTS)
    summary["font_bundle_errors"] = errors or []
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _stage_font_bundle(output: Path) -> tuple[bool, list[str]]:
    src = _bundle_tpdata()
    errors = _validate_bundle(src)
    if errors:
        _update_report(output, ok=False, errors=errors)
        for error in errors:
            print("[FONT ERROR]", error)
        return False, errors

    dst = output / "TemplePlus" / "tpdata"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)

    # Copy verification prevents packaging/copy corruption from being hidden.
    copied_errors = _validate_bundle(dst)
    if copied_errors:
        _update_report(output, ok=False, errors=copied_errors)
        for error in copied_errors:
            print("[FONT COPY ERROR]", error)
        return False, copied_errors

    _update_report(output, ok=True)
    print("[FONT OK] TemplePlus Korean font bundle verified and staged (4/4).")
    return True, []


_original_main = core.main


def _main_with_font_bundle() -> int:
    rc = _original_main()
    if rc != 0:
        return rc

    output_arg = _arg_value("--output")
    if not output_arg:
        print("[FONT ERROR] --output 경로를 찾을 수 없습니다.")
        return 2
    output = Path(output_arg).expanduser().resolve()

    ok, _errors = _stage_font_bundle(output)
    return 0 if ok else 2


core.main = _main_with_font_bundle
