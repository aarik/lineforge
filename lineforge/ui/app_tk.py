import os
import tkinter as tk
from tkinter import messagebox
from pathlib import Path
from datetime import datetime

from ..settings import Settings
from ..utils import list_images
from ..deps import find_magick, find_potrace, find_inkscape
from ..stages.preprocess import preprocess_magick
from ..stages.pad import pad_square
from ..stages.trace import trace_to_svg
from ..stages.export import export_svg_to_png
from ..pipeline import run_all


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("LineForge")

        self.s = Settings()

        self._log_file_path = None
        self._log_fh = None

        top = tk.Frame(self)
        top.pack(padx=10, pady=10, fill="x")

        tk.Label(top, text="Input folder").grid(row=0, column=0, sticky="w")
        self.e_in = tk.Entry(top, width=70)
        self.e_in.insert(0, str(Path.cwd()))
        self.e_in.grid(row=0, column=1, padx=6, sticky="we")

        tk.Label(top, text="Output folder").grid(row=1, column=0, sticky="w")
        self.e_out = tk.Entry(top, width=70)
        self.e_out.insert(0, str(Path.cwd() / "output"))
        self.e_out.grid(row=1, column=1, padx=6, sticky="we")

        top.columnconfigure(1, weight=1)

        # Pad controls (most used)
        pad = tk.LabelFrame(self, text="B: Pad settings")
        pad.pack(padx=10, pady=(0, 10), fill="x")

        self.v_size = tk.IntVar(value=self.s.pad_size)
        self.v_bg = tk.StringVar(value=self.s.pad_bg)
        self.v_fmt = tk.StringVar(value=self.s.pad_out_fmt)
        self.v_q = tk.IntVar(value=self.s.jpeg_quality)

        tk.Label(pad, text="Size").grid(row=0, column=0, sticky="w")
        tk.Entry(pad, textvariable=self.v_size, width=8).grid(row=0, column=1, padx=6, sticky="w")

        tk.Label(pad, text="Background").grid(row=0, column=2, sticky="w")
        tk.OptionMenu(pad, self.v_bg, "white", "black", "transparent").grid(row=0, column=3, padx=6, sticky="w")

        tk.Label(pad, text="Out format").grid(row=0, column=4, sticky="w")
        tk.OptionMenu(pad, self.v_fmt, "jpg", "png").grid(row=0, column=5, padx=6, sticky="w")

        tk.Label(pad, text="JPEG quality").grid(row=0, column=6, sticky="w")
        tk.Entry(pad, textvariable=self.v_q, width=6).grid(row=0, column=7, padx=6, sticky="w")

        # Buttons
        btn = tk.Frame(self)
        btn.pack(padx=10, pady=(0, 10), fill="x")

        tk.Button(btn, text="Run ALL (A->D)", command=self.run_all_clicked).pack(side="left")
        tk.Button(btn, text="Run A: Preprocess", command=self.run_a).pack(side="left", padx=6)
        tk.Button(btn, text="Run B: Pad", command=self.run_b).pack(side="left", padx=6)
        tk.Button(btn, text="Run C: Trace", command=self.run_c).pack(side="left", padx=6)
        tk.Button(btn, text="Run D: Export", command=self.run_d).pack(side="left", padx=6)

        tk.Button(btn, text="Open output folder", command=self.open_output_folder).pack(side="left", padx=10)
        tk.Button(btn, text="Open last log", command=self.open_last_log).pack(side="left")

        tk.Button(btn, text="Clear log", command=self.clear).pack(side="right")

        self.log = tk.Text(self, height=20, width=110)
        self.log.pack(padx=10, pady=(0, 10), fill="both", expand=True)

        self.start_new_log_session()
        self.write(
            "Ready.\n"
            "Outputs:\n"
            "  A -> output\\01_preprocessed\n"
            "  B -> output\\02_padded\n"
            "  C -> output\\03_svg\n"
            "  D -> output\\04_export_png\n"
        )

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- logging ----------
    def start_new_log_session(self):
        self.close_log_session()

        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_file_path = logs_dir / f"lineforge_{stamp}.log"
        self._log_fh = open(self._log_file_path, "a", encoding="utf-8")

    def close_log_session(self):
        try:
            if self._log_fh:
                self._log_fh.flush()
                self._log_fh.close()
        except Exception:
            pass
        self._log_fh = None

    def write(self, msg: str):
        self.log.insert("end", msg)
        self.log.see("end")
        self.update_idletasks()

        try:
            if self._log_fh:
                self._log_fh.write(msg)
                self._log_fh.flush()
        except Exception:
            pass

    # ---------- helpers ----------
    def clear(self):
        self.log.delete("1.0", "end")

    def paths(self):
        inp = Path(self.e_in.get().strip())
        out = Path(self.e_out.get().strip())
        if not inp.exists():
            raise FileNotFoundError(f"Input path not found: {inp}")
        out.mkdir(parents=True, exist_ok=True)
        return inp, out

    def sync(self):
        self.s.pad_size = int(self.v_size.get())
        self.s.pad_bg = self.v_bg.get().strip().lower()
        self.s.pad_out_fmt = self.v_fmt.get().strip().lower()
        self.s.jpeg_quality = int(self.v_q.get())

    def open_output_folder(self):
        try:
            out = Path(self.e_out.get().strip()).resolve()
            out.mkdir(parents=True, exist_ok=True)
            os.startfile(str(out))
        except Exception as e:
            messagebox.showerror("Open output folder failed", str(e))

    def open_last_log(self):
        try:
            if self._log_file_path and self._log_file_path.exists():
                os.startfile(str(self._log_file_path.resolve()))
                return

            logs_dir = (Path.cwd() / "logs")
            if not logs_dir.exists():
                messagebox.showinfo("Open last log", "No logs folder yet.")
                return

            logs = sorted(logs_dir.glob("lineforge_*.log"))
            if not logs:
                messagebox.showinfo("Open last log", "No log files found yet.")
                return

            os.startfile(str(logs[-1].resolve()))
        except Exception as e:
            messagebox.showerror("Open last log failed", str(e))

    def on_close(self):
        self.close_log_session()
        self.destroy()

    # ---------- stage runners ----------
    def run_a(self):
        self.start_new_log_session()
        self.sync()
        inp, out = self.paths()

        files = list_images(inp)
        if not files:
            self.write("No supported images found.\n")
            return

        magick = find_magick()
        if not magick:
            messagebox.showerror("Missing dependency", "ImageMagick 'magick' not found on PATH.")
            return

        d = out / "01_preprocessed"
        d.mkdir(parents=True, exist_ok=True)
        self.write(f"\n[A] Preprocess -> {d}\n")

        for i, src in enumerate(files, 1):
            try:
                dst = d / (src.stem + ".png")
                preprocess_magick(
                    magick, src, dst,
                    self.s.grayscale, self.s.auto_level, self.s.contrast_stretch,
                    self.s.cs_black, self.s.cs_white, self.s.median, self.s.blur,
                    self.s.negate, self.s.do_threshold, self.s.threshold_pct
                )
                self.write(f"  [{i}/{len(files)}] {src.name} -> {dst.name}\n")
            except Exception as e:
                self.write(f"  FAIL: {src.name}: {e}\n")
                return

        self.write("[A] Done.\n")

    def run_b(self):
        self.start_new_log_session()
        self.sync()
        inp, out = self.paths()

        src_dir = out / "01_preprocessed"
        files = list_images(src_dir) if src_dir.exists() else list_images(inp)
        if not files:
            self.write("No supported images found.\n")
            return

        d = out / "02_padded"
        d.mkdir(parents=True, exist_ok=True)
        self.write(f"\n[B] Pad -> {d}\n")

        for i, src in enumerate(files, 1):
            try:
                out_base = d / src.stem
                dst = pad_square(
                    src, out_base,
                    self.s.pad_size, self.s.pad_bg,
                    self.s.pad_out_fmt, self.s.jpeg_quality
                )
                self.write(f"  [{i}/{len(files)}] {src.name} -> {dst.name}\n")
            except Exception as e:
                self.write(f"  FAIL: {src.name}: {e}\n")
                return

        self.write("[B] Done.\n")

    def run_c(self):
        self.start_new_log_session()
        self.sync()
        inp, out = self.paths()

        src_dir = out / "02_padded"
        files = list_images(src_dir) if src_dir.exists() else list_images(inp)
        if not files:
            self.write("No supported images found to trace. Run B first.\n")
            return

        magick = find_magick()
        if not magick:
            messagebox.showerror("Missing dependency", "ImageMagick 'magick' not found on PATH (needed for trace PBM).")
            return

        potrace = find_potrace()
        if not potrace:
            messagebox.showerror("Missing dependency", "potrace not found. Put potrace.exe in bin\\ or install potrace.")
            return

        d = out / "03_svg"
        d.mkdir(parents=True, exist_ok=True)
        self.write(f"\n[C] Trace -> {d}\n")

        for i, src in enumerate(files, 1):
            try:
                dst = d / (src.stem + ".svg")
                trace_to_svg(
                    magick, potrace, src, dst,
                    self.s.trace_cutoff_pct, self.s.trace_invert,
                    self.s.potrace_turdsize, self.s.potrace_smooth
                )
                self.write(f"  [{i}/{len(files)}] {src.name} -> {dst.name}\n")
            except Exception as e:
                self.write(f"  FAIL: {src.name}: {e}\n")
                return

        self.write("[C] Done.\n")

    def run_d(self):
        self.start_new_log_session()
        self.sync()
        _, out = self.paths()

        src_dir = out / "03_svg"
        svgs = sorted(p for p in src_dir.glob("*.svg")) if src_dir.exists() else []
        if not svgs:
            self.write("No SVGs found. Run C first.\n")
            return

        inkscape = find_inkscape()
        if not inkscape:
            messagebox.showerror("Missing dependency", "Inkscape not found on PATH (needed for export).")
            return

        d = out / "04_export_png"
        d.mkdir(parents=True, exist_ok=True)
        self.write(f"\n[D] Export -> {d}\n")

        for i, svg in enumerate(svgs, 1):
            try:
                dst = d / (svg.stem + ".png")
                export_svg_to_png(inkscape, svg, dst, self.s.export_width, self.s.export_area_drawing)
                self.write(f"  [{i}/{len(svgs)}] {svg.name} -> {dst.name}\n")
            except Exception as e:
                self.write(f"  FAIL: {svg.name}: {e}\n")
                return

        self.write("[D] Done.\n")

    def run_all_clicked(self):
        self.start_new_log_session()
        self.sync()
        inp, out = self.paths()
        try:
            self.write("\nRunning ALL stages...\n")
            run_all(inp, out, self.s, self.write)
            self.write("\nALL DONE.\n")
        except Exception as e:
            self.write(f"\nALL FAILED: {e}\n")
