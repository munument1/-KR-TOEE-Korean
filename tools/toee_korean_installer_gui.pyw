from __future__ import annotations

import contextlib
import json
import os
import queue
import shutil
import sys
import tempfile
import threading
import traceback
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import toee_apply_korean_translation as core

APP_NAME = "TOEE 한국어 통합 패치 설치기"
APP_VERSION = "0.2.0"
SETTINGS_DIR = Path(os.environ.get("APPDATA", Path.home())) / "TOEE_Korean_Installer"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def normalize_tpdata(path: Path) -> Path:
    path = path.expanduser()
    if path.name.lower() == "tpdata" and path.is_dir():
        return path
    if (path / "tpdata").is_dir():
        return path / "tpdata"
    apps = [p for p in path.glob("app-*") if (p / "tpdata").is_dir()]
    if apps:
        def key(p: Path):
            out = []
            for x in p.name.removeprefix("app-").split("."):
                try:
                    out.append(int(x))
                except ValueError:
                    out.append(0)
            return tuple(out)
        return sorted(apps, key=key, reverse=True)[0] / "tpdata"
    return path


def default_tpdata() -> Path | None:
    found = core.latest_templeplus_tpdata()
    return found.resolve() if found else None


def default_output(game_root: Path | None) -> Path:
    if game_root:
        return game_root / "TOEE_Korean_Patch_Output"
    return Path.home() / "Desktop" / "TOEE_Korean_Patch_Output"


class QueueWriter:
    def __init__(self, q: queue.Queue[tuple[str, object]]):
        self.q = q

    def write(self, text: str) -> int:
        if text:
            self.q.put(("log", text))
        return len(text)

    def flush(self) -> None:
        pass


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("860x690")
        self.minsize(780, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.q: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        self.last_report: Path | None = None

        self.game_var = tk.StringVar()
        self.tp_var = tk.StringVar()
        self.xlsx_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="install")
        self.status_var = tk.StringVar(value="경로를 지정한 뒤 사전 검사를 실행하세요.")

        self._build_ui()
        self._load_settings()
        self.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(18, 14, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Temple of Elemental Evil 한국어 통합 패치", font=("Malgun Gothic", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="TOEE / Circle of Eight / TemplePlus 경로를 직접 지정합니다.").grid(row=1, column=0, sticky="w", pady=(4, 0))

        paths = ttk.LabelFrame(self, text="경로 설정", padding=12)
        paths.grid(row=1, column=0, sticky="ew", padx=18, pady=(4, 8))
        paths.columnconfigure(1, weight=1)

        self._path_row(paths, 0, "TOEE 설치 폴더", self.game_var, self.pick_game)
        self._path_row(paths, 1, "TemplePlus tpdata", self.tp_var, self.pick_tpdata, extra=("자동 찾기", self.auto_tpdata))
        self._path_row(paths, 2, "최종 번역 XLSX", self.xlsx_var, self.pick_xlsx)
        self._path_row(paths, 3, "패치 출력 폴더", self.output_var, self.pick_output)

        mode = ttk.Frame(paths)
        mode.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 2))
        ttk.Label(mode, text="실행 방식:").pack(side="left")
        ttk.Radiobutton(mode, text="통합 설치 (권장)", variable=self.mode_var, value="install").pack(side="left", padx=(12, 6))
        ttk.Radiobutton(mode, text="패치 파일만 생성", variable=self.mode_var, value="build").pack(side="left", padx=6)

        body = ttk.Frame(self, padding=(18, 0, 18, 8))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        action = ttk.Frame(body)
        action.grid(row=0, column=0, sticky="ew", pady=(4, 8))
        self.check_btn = ttk.Button(action, text="1. 사전 검사", command=lambda: self.start_job("check"))
        self.check_btn.pack(side="left")
        self.run_btn = ttk.Button(action, text="2. 통합 설치 / 생성", command=lambda: self.start_job("run"))
        self.run_btn.pack(side="left", padx=(8, 0))
        self.report_btn = ttk.Button(action, text="보고서 열기", command=self.open_report, state="disabled")
        self.report_btn.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(action, mode="indeterminate", length=190)
        self.progress.pack(side="right")

        logs = ttk.LabelFrame(body, text="검사 / 설치 로그", padding=8)
        logs.grid(row=1, column=0, sticky="nsew")
        logs.columnconfigure(0, weight=1)
        logs.rowconfigure(0, weight=1)
        self.log = scrolledtext.ScrolledText(logs, wrap="word", font=("Consolas", 9), state="disabled")
        self.log.grid(row=0, column=0, sticky="nsew")

        footer = ttk.Frame(self, padding=(18, 0, 18, 12))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(footer, text="직접 설치는 전체 검증 성공 후에만 실행되며, 날짜별 백업 폴더를 남깁니다.").grid(row=1, column=0, sticky="w", pady=(4, 0))

    def _path_row(self, parent, row, label, var, command, extra=None):
        ttk.Label(parent, text=label, width=18).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=(6, 6), pady=4)
        buttons = ttk.Frame(parent)
        buttons.grid(row=row, column=2, sticky="e")
        ttk.Button(buttons, text="찾아보기", command=command).pack(side="left")
        if extra:
            ttk.Button(buttons, text=extra[0], command=extra[1]).pack(side="left", padx=(4, 0))

    def _load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        self.game_var.set(data.get("game_root", ""))
        self.tp_var.set(data.get("templeplus_root", ""))
        self.xlsx_var.set(data.get("xlsx", ""))
        self.output_var.set(data.get("output", ""))
        self.mode_var.set(data.get("mode", "install"))
        if not self.tp_var.get():
            tp = default_tpdata()
            if tp:
                self.tp_var.set(str(tp))

    def _save_settings(self):
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "game_root": self.game_var.get().strip(),
            "templeplus_root": self.tp_var.get().strip(),
            "xlsx": self.xlsx_var.get().strip(),
            "output": self.output_var.get().strip(),
            "mode": self.mode_var.get(),
        }
        SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def pick_game(self):
        p = filedialog.askdirectory(title="TOEE 설치 폴더 선택")
        if p:
            self.game_var.set(p)
            if not self.output_var.get().strip():
                self.output_var.set(str(default_output(Path(p))))

    def pick_tpdata(self):
        p = filedialog.askdirectory(title="TemplePlus tpdata 폴더 선택")
        if p:
            self.tp_var.set(str(normalize_tpdata(Path(p))))

    def auto_tpdata(self):
        p = default_tpdata()
        if p:
            self.tp_var.set(str(p))
            self.status_var.set(f"TemplePlus 자동 감지: {p}")
        else:
            messagebox.showwarning(APP_NAME, "TemplePlus tpdata를 자동으로 찾지 못했습니다. 직접 지정해 주세요.")

    def pick_xlsx(self):
        p = filedialog.askopenfilename(title="최종 번역 XLSX 선택", filetypes=[("Excel workbook", "*.xlsx"), ("All files", "*.*")])
        if p:
            self.xlsx_var.set(p)

    def pick_output(self):
        p = filedialog.askdirectory(title="패치 출력 폴더 선택")
        if p:
            self.output_var.set(p)

    def validate_paths(self) -> tuple[Path, Path, Path, Path]:
        game = Path(self.game_var.get().strip()).expanduser().resolve()
        tp = normalize_tpdata(Path(self.tp_var.get().strip()).expanduser()).resolve()
        xlsx = Path(self.xlsx_var.get().strip()).expanduser().resolve()
        output_raw = self.output_var.get().strip()
        output = Path(output_raw).expanduser().resolve() if output_raw else default_output(game).resolve()
        self.output_var.set(str(output))

        errors = []
        if not game.is_dir() or not (game / "data").is_dir() or not (game / "modules" / "ToEE").is_dir():
            errors.append("TOEE 설치 폴더: data 및 modules\\ToEE가 있는 게임 루트를 지정하세요.")
        if not tp.is_dir() or tp.name.lower() != "tpdata":
            errors.append("TemplePlus: 실제 tpdata 폴더를 지정하세요.")
        if not xlsx.is_file() or xlsx.suffix.lower() != ".xlsx":
            errors.append("최종 번역 XLSX 파일을 지정하세요.")
        protected = [game, game / "data", game / "modules", game / "modules" / "ToEE", tp]
        if any(output == p for p in protected):
            errors.append("패치 출력 폴더는 게임/TemplePlus 원본 폴더 자체로 지정할 수 없습니다.")
        try:
            if game.is_relative_to(output) or tp.is_relative_to(output):
                errors.append("패치 출력 폴더는 게임/TemplePlus 폴더의 상위 경로로 지정할 수 없습니다.")
        except ValueError:
            pass
        if output == Path(output.anchor):
            errors.append("패치 출력 폴더로 드라이브 루트는 사용할 수 없습니다.")
        if errors:
            raise ValueError("\n".join(errors))
        return game, tp, xlsx, output

    def append_log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def set_busy(self, value: bool):
        self.busy = value
        state = "disabled" if value else "normal"
        self.check_btn.configure(state=state)
        self.run_btn.configure(state=state)
        if value:
            self.progress.start(12)
        else:
            self.progress.stop()

    def start_job(self, action: str):
        if self.busy:
            return
        try:
            paths = self.validate_paths()
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        self._save_settings()
        self.clear_log()
        self.last_report = None
        self.report_btn.configure(state="disabled")
        self.set_busy(True)
        self.status_var.set("전체 원문과 번역 시트를 대조 중입니다...")
        threading.Thread(target=self._worker, args=(action, paths, self.mode_var.get()), daemon=True).start()

    def _run_core(self, game: Path, tp: Path, xlsx: Path, output: Path) -> tuple[int, dict]:
        argv = [
            "--xlsx", str(xlsx),
            "--game-root", str(game),
            "--templeplus-root", str(tp),
            "--output", str(output),
        ]
        old_argv = sys.argv[:]
        writer = QueueWriter(self.q)
        try:
            sys.argv = ["toee_apply_korean_translation.py", *argv]
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                rc = core.main()
        finally:
            sys.argv = old_argv
        report_path = output / "PATCH_REPORT.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
        return rc, report

    def _worker(self, action: str, paths: tuple[Path, Path, Path, Path], mode: str):
        game, tp, xlsx, output = paths
        temp: Path | None = None
        try:
            temp = Path(tempfile.mkdtemp(prefix="TOEE_Korean_Preflight_"))
            self.q.put(("log", "[1/2] TOEE / Co8 / TemplePlus 전체 사전 검사 시작\n"))
            rc, report = self._run_core(game, tp, xlsx, temp)
            summary = report.get("summary", {})
            if rc != 0:
                kept = output.parent / f"TOEE_Korean_Failed_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copytree(temp, kept)
                self.q.put(("done_error", ("사전 검사 실패", f"원문 불일치/누락이 있습니다.\n검사 결과를 보존했습니다:\n{kept}", kept / "PATCH_REPORT.json")))
                return

            self.q.put(("log", "\n[검사 통과] 전체 번역 대상이 현재 설치본과 일치합니다.\n"))
            self.q.put(("log", f"적용 대상: {summary.get('rows_applied', 0):,} / {summary.get('translation_rows', 0):,}행\n"))

            if action == "check":
                report_dest = output.parent / "TOEE_Korean_Preflight_Report.json"
                shutil.copy2(temp / "PATCH_REPORT.json", report_dest)
                self.q.put(("done_ok", ("사전 검사 완료", "TOEE / Co8 / TemplePlus가 모두 적용 가능한 상태입니다.", report_dest)))
                return

            if mode == "build":
                self.q.put(("log", "\n[2/2] 패치 파일 출력 중...\n"))
                target = output
                if target.exists() and any(target.iterdir()):
                    target = target.with_name(f"{target.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                shutil.copytree(temp, target, dirs_exist_ok=True)
                self.q.put(("done_ok", ("패치 생성 완료", f"통합 패치 폴더를 생성했습니다.\n{target}", target / "PATCH_REPORT.json")))
                return

            self.q.put(("log", "\n[2/2] 전체 검증 통과. 백업 후 통합 설치를 시작합니다.\n"))
            backup = self._install_transaction(temp, game, tp)
            report_dest = game / "TOEE_Korean_Last_Install_Report.json"
            shutil.copy2(temp / "PATCH_REPORT.json", report_dest)
            self.q.put(("done_ok", ("통합 설치 완료", f"TOEE / Co8 / TemplePlus에 한국어 패치를 적용했습니다.\n백업: {backup}", report_dest)))
        except Exception as exc:
            self.q.put(("log", "\n[예외]\n" + traceback.format_exc() + "\n"))
            self.q.put(("done_error", ("실행 실패", str(exc), None)))
        finally:
            if temp:
                shutil.rmtree(temp, ignore_errors=True)

    def _install_transaction(self, staged: Path, game: Path, tp: Path) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = game / f"TOEE_Korean_Backup_{stamp}"
        backup.mkdir(parents=True, exist_ok=False)

        roots = [
            (staged / "data", game / "data", backup / "TOEE" / "data"),
            (staged / "modules" / "ToEE", game / "modules" / "ToEE", backup / "TOEE" / "modules" / "ToEE"),
            (staged / "TemplePlus" / "tpdata", tp, backup / "TemplePlus" / "tpdata"),
        ]
        plan: list[tuple[Path, Path, Path, bool]] = []
        for src_root, dst_root, bak_root in roots:
            if not src_root.exists():
                continue
            for src in src_root.rglob("*"):
                if not src.is_file() or src.name == "PATCH_REPORT.json":
                    continue
                rel = src.relative_to(src_root)
                dst = dst_root / rel
                bak = bak_root / rel
                plan.append((src, dst, bak, dst.exists()))

        # 백업을 모두 먼저 생성한다. 여기서 실패하면 원본은 아직 변경되지 않는다.
        for _src, dst, bak, existed in plan:
            if existed:
                bak.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bak)

        written: list[tuple[Path, Path, bool]] = []
        try:
            for src, dst, bak, existed in plan:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                written.append((dst, bak, existed))
        except Exception:
            # 트랜잭션 롤백
            for dst, bak, existed in reversed(written):
                try:
                    if existed and bak.exists():
                        shutil.copy2(bak, dst)
                    elif not existed and dst.exists():
                        dst.unlink()
                except Exception:
                    pass
            raise

        manifest = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "toee_root": str(game),
            "templeplus_tpdata": str(tp),
            "files_installed": len(plan),
        }
        (backup / "BACKUP_INFO.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return backup

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.append_log(str(payload))
                elif kind == "done_ok":
                    title, msg, report = payload
                    self.last_report = Path(report) if report else None
                    if self.last_report and self.last_report.exists():
                        self.report_btn.configure(state="normal")
                    self.status_var.set(str(title))
                    self.set_busy(False)
                    messagebox.showinfo(APP_NAME, str(msg))
                elif kind == "done_error":
                    title, msg, report = payload
                    self.last_report = Path(report) if report else None
                    if self.last_report and self.last_report.exists():
                        self.report_btn.configure(state="normal")
                    self.status_var.set(str(title))
                    self.set_busy(False)
                    messagebox.showerror(APP_NAME, str(msg))
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def open_report(self):
        if self.last_report and self.last_report.exists():
            try:
                os.startfile(self.last_report)  # type: ignore[attr-defined]
            except Exception:
                messagebox.showinfo(APP_NAME, str(self.last_report))

    def on_close(self):
        if self.busy and not messagebox.askyesno(APP_NAME, "작업이 진행 중입니다. 프로그램을 종료할까요?"):
            return
        try:
            self._save_settings()
        except Exception:
            pass
        self.destroy()


if __name__ == "__main__":
    InstallerApp().mainloop()
