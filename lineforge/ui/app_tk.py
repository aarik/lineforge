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


def run_all(input_path: Path, output_root: Path, s: Settings, log) -> None:
    """Run A->D in order, using the same logic as the GUI buttons."""
    files = list_images(input_path)
    if not files:
        raise RuntimeError("No supported images found.")

    # A: preprocess
    if s.do_preprocess:
        magick = find_magick()
        if not magick:
            raise RuntimeError("ImageMagick 'magick' not found on PATH.")
        d1 = output_root / "01_preprocessed"
        d1.mkdir(parents=True, exist_ok=True)
        for src in files:
            dst = d1 / (src.stem + ".png")
            preprocess_magick(
                magick, src, dst,
                s.grayscale, s.auto_level, s.contrast_stretch,
                s.cs_black, s.cs_white, s.median, s.blur,
                s.negate, s.do_threshold, s.threshold_pct
            )
        files = list_images(d1)

    # B: pad
    if s.do_pad:
        d2 = output_root / "02_padded"
        d2.mkdir(parents=True, exist_ok=True)
        for src in files:
            out_base = d2 / src.stem
            pad_square(src, out_base, s.pad_size, s.pad_bg, s.pad_out_fmt, s.jpeg_quality)
        files = list_images(d2)

    # C: trace
    if s.do_trace:
        magick = find_magick()
        if not magick:
            raise RuntimeError("ImageMagick 'magick' not found on PATH (needed for trace PBM).")
        potrace = find_potrace()
        if not potrace:
            raise RuntimeError("potrace not found. Put potrace.exe in bin\\ or install potrace.")
        d3 = output_root / "03_svg"
        d3.mkdir(parents=True, exist_ok=True)
        for src in files:
            dst = d3 / (src.stem + ".svg")
            trace_to_svg(
                magick, potrace, src, dst,
                s.trace_cutoff_pct, s.trace_invert,
                s.potrace_turdsize, s.potrace_smooth
            )
        files = sorted(d3.glob("*.svg"))

    # D: export
    if s.do_export:
        inkscape = find_inkscape()
        if not inkscape:
            raise RuntimeError("Inkscape not found on PATH (needed for export).")
        d4 = output_root / "04_export_png"
        d4.mkdir(parents=True, exist_ok=True)
        for svg in files:
            dst = d4 / (Path(svg).stem + ".png")
            export_svg_to_png(inkscape, Path(svg), dst, s.export_width, s.export_area_drawing)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LineForge")
        self.geometry("980x720")
        self.minsize(900, 650)

        self.s = Settings()

        self.var_in = tk.StringVar(value=str(Path.cwd()))
        self.var_out = tk.StringVar(value=str(Path.cwd() / "output"))

        self.log_dir = Path.cwd() / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.current_log_file = None

        self._build_ui()

    def _build_ui(self):
        frm_top = tk.Frame(self)
        frm_top.pack(fill="x", padx=10, pady=8)

        tk.Label(frm_top, text="Input folder / file:").grid(row=0, column=0, sticky="w")
        tk.Entry(frm_top, textvariable=self.var_in, width=80).grid(row=0, column=1, sticky="we", padx=6)

        tk.Label(frm_top, text="Output folder:").grid(row=1, column=0, sticky="w")
        tk.Entry(frm_top, textvariable=self.var_out, width=80).grid(row=1, column=1, sticky="we", padx=6)

        frm_top.columnconfigure(1, weight=1)

        frm_btns = tk.Frame(self)
        frm_btns.pack(fill="x", padx=10, pady=6)

        tk.Button(frm_btns, text="A) Preprocess", command=self.run_a, width=18).pack(side="left", padx=4)
        tk.Button(frm_btns, text="B) Pad", command=self.run_b, width=18).pack(side="left", padx=4)
        tk.Button(frm_btns, text="C) Trace → SVG", command=self.run_c, width=18).pack(side="left", padx=4)
        tk.Button(frm_btns, text="D) Export → PNG", command=self.run_d, width=18).pack(side="left", padx=4)
        tk.Button(frm_btns, text="Run ALL", command=self.run_all_clicked, width=18).pack(side="left", padx=8)

        frm_info = tk.Frame(self)
        frm_info.pack(fill="x", padx=10, pady=6)

        txt = (
            "Stages:\n"
            "  A -> output\\01_preprocessed\n"
            "  B -> output\\02_padded\n"
            "  C -> output\\03_svg\n"
            "  D -> output\\04_export_png\n"
        )
        tk.Label(frm_info, text=txt, justify="left").pack(anchor="w")

        frm_log = tk.Frame(self)
        frm_log.pack(fill="both", expand=True, padx=10, pady=8)

        self.txt_log = tk.Text(frm_log, wrap="word")
        self.txt_log.pack(side="left", fill="both", expand=True)

        scroll = tk.Scrollbar(frm_log, command=self.txt_log.yview)
        scroll.pack(side="right", fill="y")
        self.txt_log.configure(yscrollcommand=scroll.set)

        frm_bottom = tk.Frame(self)
        frm_bottom.pack(fill="x", padx=10, pady=8)

        tk.Button(frm_bottom, text="Quit", command=self.quit_app, width=12).pack(side="right")

    def paths(self):
        inp = Path(self.var_in.get()).expanduser()
        out = Path(self.var_out.get()).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        return inp, out

    def write(self, msg: str):
        self.txt_log.insert("end", msg)
        self.txt_log.see("end")
        self.txt_log.update_idletasks()
        if self.current_log_file:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(msg)

    def start_new_log_session(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_log_file = str(self.log_dir / f"lineforge_{ts}.log")
        self.write(f"\n--- Log session: {self.current_log_file} ---\n")

    def close_log_session(self):
        self.current_log_file = None

    def quit_app(self):
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
