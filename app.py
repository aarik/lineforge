from __future__ import annotations
import os
import sys
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

import sys, shutil
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
import subprocess
from tkinter import messagebox

def has_cmd(name: str) -> bool:
    return shutil.which(name) is not None

def winget_install(ids: list[str]) -> None:
    for pkg_id in ids:
        p = subprocess.run(
            ["winget","install","-e","--id",pkg_id,"--accept-package-agreements","--accept-source-agreements"],
            capture_output=True, text=True
        )
        if p.returncode != 0:
            raise RuntimeError(p.stderr or p.stdout or f"winget failed: {pkg_id}")

def ensure_magick_inkscape_winget() -> bool:
    if not has_cmd("winget"):
        messagebox.showerror("winget missing", "winget is not available. Install 'App Installer' from Microsoft Store.")
        return False

    missing = []
    if not has_cmd("magick"):
        missing.append("ImageMagick.ImageMagick")
    if not (has_cmd("inkscape") or has_cmd("inkscape.com") or has_cmd("inkscape.exe")):
        missing.append("Inkscape.Inkscape")

    if not missing:
        return True

    if not messagebox.askyesno("Install dependencies?", "Missing:\n\n" + "\n".join(missing) + "\n\nInstall now with winget?"):
        return False

    try:
        winget_install(missing)
    except Exception as e:
        messagebox.showerror("Install failed", str(e))
        return False

    messagebox.showinfo("Installed", "Install finished. If tools still aren't detected, restart the app (PATH refresh).")
    return True


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)

def resource_path(rel: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return str(Path(base) / rel)
    return str(Path(__file__).resolve().parent / rel)

def find_potrace() -> str | None:
    p = resource_path(r"bin\potrace.exe")
    if Path(p).exists():
        return p
    return find_potrace()


    
def run_cmd(args: List[str]) -> None:
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(args)
            + "\n\nSTDOUT:\n"
            + (p.stdout or "")
            + "\n\nSTDERR:\n"
            + (p.stderr or "")
        )


def list_images(path: Path) -> List[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in IMG_EXTS else []
    files = []
    for p in path.iterdir():
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            files.append(p)
    files.sort()
    return files


def pad_square_pillow(in_path: Path, out_path: Path, size: int, bg_mode: str) -> None:
    img = Image.open(in_path)

    # Normalize image mode based on requested background behavior
    bg_mode = (bg_mode or "").lower().strip()
    if bg_mode in ("transparent", "alpha", "none"):
        # keep alpha
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        bg = (0, 0, 0, 0)
        canvas_mode = "RGBA"
    else:
        # solid background: kill alpha
        if img.mode != "RGB":
            img = img.convert("RGB")
        if bg_mode in ("black", "0", "dark"):
            bg = (0, 0, 0)
        else:
            # default white
            bg = (255, 255, 255)
        canvas_mode = "RGB"

    w, h = img.size
    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid image size: {img.size} for {in_path}")

    # Scale to fit within the square while keeping aspect ratio
    scale = min(size / w, size / h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    resample = getattr(Image, "Resampling", Image).LANCZOS
    resized = img.resize((new_w, new_h), resample)

    # Create square canvas and paste centered
    canvas = Image.new(canvas_mode, (size, size), bg)
    x = (size - new_w) // 2
    y = (size - new_h) // 2

    if canvas_mode == "RGBA" and resized.mode == "RGBA":
        canvas.paste(resized, (x, y), resized)
    else:
        canvas.paste(resized, (x, y))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Save PNG; if RGB, it will not be transparent
    canvas.save(out_path, format="PNG")


def preprocess_magick(
    magick_exe: str,
    in_path: Path,
    out_path: Path,
    grayscale: bool,
    auto_level: bool,
    contrast_stretch: bool,
    cs_black: float,
    cs_white: float,
    median_radius: int,
    blur_sigma: float,
    negate: bool,
    do_threshold: bool,
    threshold_pct: int,
) -> None:
    """
    Preprocess an image using ImageMagick `magick` and write PNG output.
    Keeps it simple and robust for dataset prep.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    args = [magick_exe, str(in_path)]

    # Normalize alpha first so later ops behave
    args += ["-alpha", "remove", "-alpha", "off"]

    if grayscale:
        args += ["-colorspace", "Gray"]

    # Some mild “make it comfortable for tracing” helpers
    if auto_level:
        args += ["-auto-level"]

    if contrast_stretch:
        # percentages, small values like 0.5% x 0.5% are usually enough
        args += ["-contrast-stretch", f"{cs_black}%x{cs_white}%"]

    # Denoise
    if median_radius > 0:
        args += ["-median", str(median_radius)]

    if blur_sigma and blur_sigma > 0:
        args += ["-blur", f"0x{blur_sigma}"]

    if negate:
        args += ["-negate"]

    if do_threshold:
        args += ["-threshold", f"{threshold_pct}%"]

    # Keep output predictable
    args += ["-depth", "8", "-strip", str(out_path)]
    run_cmd(args)


def trace_to_svg_magick_potrace(
    magick_exe: str,
    potrace_exe: str,
    in_png: Path,
    out_svg: Path,
    cutoff_pct: int,
    invert: bool,
    turdsize: int,
    smooth: bool,
) -> None:
    """
    Convert raster -> PBM via ImageMagick threshold, then PBM -> SVG via potrace.
    """
    out_svg.parent.mkdir(parents=True, exist_ok=True)
    pbm_path = out_svg.with_suffix(".pbm")

    magick_args = [
        magick_exe,
        str(in_png),
        "-alpha", "remove", "-alpha", "off",
        "-colorspace", "Gray",
        "-depth", "8",
        "-strip",
    ]
    if invert:
        magick_args += ["-negate"]
    magick_args += ["-threshold", f"{cutoff_pct}%", str(pbm_path)]
    run_cmd(magick_args)

    potrace_args = [potrace_exe, str(pbm_path), "-s", "-o", str(out_svg)]
    if turdsize > 0:
        potrace_args += ["-t", str(turdsize)]
    if not smooth:
        # potrace smooth is on by default; disabling uses "-n" (no curve optimization)
        potrace_args += ["-n"]
    run_cmd(potrace_args)

    try:
        pbm_path.unlink(missing_ok=True)
    except Exception:
        pass


def export_svg_to_png_inkscape(
    inkscape_exe: str,
    in_svg: Path,
    out_png: Path,
    width: int,
    export_area_drawing: bool,
) -> None:
    out_png.parent.mkdir(parents=True, exist_ok=True)
    args = [
        inkscape_exe,
        str(in_svg),
        "--export-type=png",
        f"--export-filename={str(out_png)}",
        f"--export-width={width}",
    ]
    if export_area_drawing:
        args += ["--export-area-drawing"]
    run_cmd(args)


@dataclass
class Settings:
    # preprocess (magick)
    do_preprocess: bool
    grayscale: bool
    auto_level: bool
    contrast_stretch: bool
    cs_black: float
    cs_white: float
    median: int
    blur: float
    negate: bool
    do_threshold: bool
    threshold_pct: int

    # pad/resize
    do_pad: bool
    pad_size: int
    pad_bg: str

    # trace
    do_trace: bool
    potrace_turdsize: int
    potrace_smooth: bool

    # export
    do_export: bool
    export_width: int
    export_area_drawing: bool


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("LineForge")

        self.geometry("980x720")

        self.input_path: Optional[Path] = None
        self.output_root: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        io = ttk.LabelFrame(root, text="1) Select Input and Output", padding=10)
        io.pack(fill="x")

        self.input_var = tk.StringVar(value="(none)")
        self.output_var = tk.StringVar(value="(none)")

        row = ttk.Frame(io)
        row.pack(fill="x", pady=2)
        ttk.Button(row, text="Choose Folder…", command=self.pick_folder).pack(side="left")
        ttk.Button(row, text="Choose Single Image…", command=self.pick_file).pack(side="left", padx=6)
        ttk.Label(row, text="Input:").pack(side="left", padx=(12, 6))
        ttk.Label(row, textvariable=self.input_var).pack(side="left", fill="x", expand=True)

        row2 = ttk.Frame(io)
        row2.pack(fill="x", pady=2)
        ttk.Button(row2, text="Choose Output Folder…", command=self.pick_output).pack(side="left")
        ttk.Label(row2, text="Output:").pack(side="left", padx=(12, 6))
        ttk.Label(row2, textvariable=self.output_var).pack(side="left", fill="x", expand=True)

        deps = ttk.Frame(io)
        deps.pack(fill="x", pady=(8, 0))
        ttk.Button(deps, text="Check Dependencies", command=self.check_deps).pack(side="left")
        self.deps_var = tk.StringVar(value="(not checked)")
        ttk.Label(deps, textvariable=self.deps_var).pack(side="left", padx=10)

        opts = ttk.LabelFrame(root, text="2) Options (all the knobs)", padding=10)
        opts.pack(fill="both", expand=True, pady=12)

        canvas = tk.Canvas(opts, highlightthickness=0)
        scroll = ttk.Scrollbar(opts, orient="vertical", command=canvas.yview)
        self.opts_frame = ttk.Frame(canvas)

        self.opts_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.opts_frame, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)

        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Settings vars
        self.v_do_pre = tk.BooleanVar(value=True)
        self.v_gray = tk.BooleanVar(value=True)
        self.v_auto = tk.BooleanVar(value=True)
        self.v_cs = tk.BooleanVar(value=True)
        self.v_cs_black = tk.DoubleVar(value=0.5)
        self.v_cs_white = tk.DoubleVar(value=0.5)
        self.v_median = tk.IntVar(value=1)
        self.v_blur = tk.DoubleVar(value=0.0)
        self.v_negate = tk.BooleanVar(value=False)
        self.v_thresh = tk.BooleanVar(value=False)
        self.v_thresh_pct = tk.IntVar(value=45)

        self.v_do_pad = tk.BooleanVar(value=True)
        self.v_pad_size = tk.IntVar(value=512)
        self.v_pad_bg = tk.StringVar(value="transparent")

        self.v_do_trace = tk.BooleanVar(value=True)
        self.v_turd = tk.IntVar(value=8)
        self.v_smooth = tk.BooleanVar(value=True)

        self.v_do_export = tk.BooleanVar(value=True)
        self.v_export_w = tk.IntVar(value=512)
        self.v_area = tk.BooleanVar(value=True)

        self._section_preprocess(self.opts_frame)
        self._section_pad(self.opts_frame)
        self._section_trace(self.opts_frame)
        self._section_export(self.opts_frame)

        runbox = ttk.LabelFrame(root, text="3) Run", padding=10)
        runbox.pack(fill="x")

        btns = ttk.Frame(runbox)
        btns.pack(fill="x")
        ttk.Button(btns, text="Run Full Pipeline", command=self.run_pipeline).pack(side="left")
        ttk.Button(btns, text="Open Output Folder", command=self.open_output).pack(side="left", padx=8)

        self.progress = ttk.Progressbar(runbox, mode="determinate")
        self.progress.pack(fill="x", pady=(10, 6))

        self.log = tk.Text(runbox, height=10, wrap="word")
        self.log.pack(fill="both", expand=True)
        self._log("Ready.\n")

    def _section_preprocess(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="A) Preprocess (ImageMagick)", padding=10)
        box.pack(fill="x", pady=6)

        ttk.Checkbutton(box, text="Enable preprocess", variable=self.v_do_pre).grid(row=0, column=0, sticky="w")

        ttk.Checkbutton(box, text="Grayscale", variable=self.v_gray).grid(row=1, column=0, sticky="w")
        ttk.Checkbutton(box, text="Auto-level", variable=self.v_auto).grid(row=1, column=1, sticky="w")
        ttk.Checkbutton(box, text="Contrast-stretch", variable=self.v_cs).grid(row=1, column=2, sticky="w")

        ttk.Label(box, text="Contrast-stretch black%").grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(box, from_=0.0, to=5.0, variable=self.v_cs_black, orient="horizontal").grid(row=2, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(box, textvariable=self.v_cs_black).grid(row=2, column=2, sticky="w", pady=(6, 0))

        ttk.Label(box, text="Contrast-stretch white%").grid(row=3, column=0, sticky="w")
        ttk.Scale(box, from_=0.0, to=5.0, variable=self.v_cs_white, orient="horizontal").grid(row=3, column=1, sticky="ew")
        ttk.Label(box, textvariable=self.v_cs_white).grid(row=3, column=2, sticky="w")

        ttk.Label(box, text="Median radius (denoise)").grid(row=4, column=0, sticky="w", pady=(6, 0))
        ttk.Scale(box, from_=0, to=6, variable=self.v_median, orient="horizontal").grid(row=4, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(box, textvariable=self.v_median).grid(row=4, column=2, sticky="w", pady=(6, 0))

        ttk.Label(box, text="Blur sigma").grid(row=5, column=0, sticky="w")
        ttk.Scale(box, from_=0.0, to=4.0, variable=self.v_blur, orient="horizontal").grid(row=5, column=1, sticky="ew")
        ttk.Label(box, textvariable=self.v_blur).grid(row=5, column=2, sticky="w")

        ttk.Checkbutton(box, text="Negate (invert)", variable=self.v_negate).grid(row=6, column=0, sticky="w", pady=(6, 0))

        ttk.Checkbutton(box, text="Apply threshold (bilevel)", variable=self.v_thresh).grid(row=7, column=0, sticky="w", pady=(6, 0))
        ttk.Label(box, text="Threshold %").grid(row=7, column=1, sticky="e", pady=(6, 0))
        ttk.Scale(box, from_=0, to=100, variable=self.v_thresh_pct, orient="horizontal").grid(row=7, column=2, sticky="ew", pady=(6, 0))
        ttk.Label(box, textvariable=self.v_thresh_pct).grid(row=7, column=3, sticky="w", pady=(6, 0))

        for c in range(4):
            box.columnconfigure(c, weight=1)

    def _section_pad(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="B) Pad/Resize to Square (Pillow)", padding=10)
        box.pack(fill="x", pady=6)

        ttk.Checkbutton(box, text="Enable pad/resize", variable=self.v_do_pad).grid(row=0, column=0, sticky="w")
        ttk.Label(box, text="Size").grid(row=0, column=1, sticky="e")
        ttk.Spinbox(box, from_=64, to=4096, increment=64, textvariable=self.v_pad_size, width=8).grid(row=0, column=2, sticky="w")
        ttk.Label(box, text="Background").grid(row=0, column=3, sticky="e")
        ttk.Combobox(box, values=["transparent", "white", "black"], textvariable=self.v_pad_bg, width=12, state="readonly").grid(row=0, column=4, sticky="w")

        for c in range(5):
            box.columnconfigure(c, weight=1)

    def _section_trace(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="C) Trace to SVG (Potrace)", padding=10)
        box.pack(fill="x", pady=6)

        ttk.Checkbutton(box, text="Enable tracing", variable=self.v_do_trace).grid(row=0, column=0, sticky="w")
        ttk.Label(box, text="Turdsize (remove specks)").grid(row=0, column=1, sticky="e")
        ttk.Scale(box, from_=0, to=50, variable=self.v_turd, orient="horizontal").grid(row=0, column=2, sticky="ew")
        ttk.Label(box, textvariable=self.v_turd).grid(row=0, column=3, sticky="w")

        ttk.Checkbutton(box, text="Smooth curves (default)", variable=self.v_smooth).grid(row=1, column=0, sticky="w", pady=(6, 0))

        for c in range(4):
            box.columnconfigure(c, weight=1)

    def _section_export(self, parent: ttk.Frame) -> None:
        box = ttk.LabelFrame(parent, text="D) Export SVG → PNG (Inkscape CLI)", padding=10)
        box.pack(fill="x", pady=6)

        ttk.Checkbutton(box, text="Enable export to PNG", variable=self.v_do_export).grid(row=0, column=0, sticky="w")
        ttk.Label(box, text="Export width").grid(row=0, column=1, sticky="e")
        ttk.Spinbox(box, from_=64, to=4096, increment=64, textvariable=self.v_export_w, width=8).grid(row=0, column=2, sticky="w")

        ttk.Checkbutton(box, text="Crop to drawing area", variable=self.v_area).grid(row=1, column=0, sticky="w", pady=(6, 0))

        for c in range(3):
            box.columnconfigure(c, weight=1)

    def _log(self, s: str) -> None:
        self.log.insert("end", s)
        self.log.see("end")
        self.update_idletasks()

    def pick_folder(self) -> None:
        d = filedialog.askdirectory(title="Choose input folder")
        if not d:
            return
        self.input_path = Path(d)
        self.input_var.set(str(self.input_path))

    def pick_file(self) -> None:
        f = filedialog.askopenfilename(
            title="Choose input image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("All", "*.*")]
        )
        if not f:
            return
        self.input_path = Path(f)
        self.input_var.set(str(self.input_path))

    def pick_output(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder")
        if not d:
            return
        self.output_root = Path(d)
        self.output_var.set(str(self.output_root))

    def open_output(self) -> None:
        if not self.output_root:
            messagebox.showwarning("No output folder", "Choose an output folder first.")
            return
        os.startfile(str(self.output_root))

    def check_deps(self) -> None:
        magick = which("magick")
        potrace = potrace = find_potrace()

        inkscape = which("inkscape") or which("inkscape.com") or which("inkscape.exe")
        missing = []
        if not magick:
            missing.append("ImageMagick (magick)")
        if not potrace:
            missing.append("Potrace (potrace)")
        if not inkscape:
            missing.append("Inkscape (inkscape)")
        if missing:
            self.deps_var.set("Missing: " + ", ".join(missing))
        else:
            self.deps_var.set("OK: magick, potrace, inkscape found on PATH")

    def get_settings(self) -> Settings:
        return Settings(
            do_preprocess=self.v_do_pre.get(),
            grayscale=self.v_gray.get(),
            auto_level=self.v_auto.get(),
            contrast_stretch=self.v_cs.get(),
            cs_black=float(self.v_cs_black.get()),
            cs_white=float(self.v_cs_white.get()),
            median=int(self.v_median.get()),
            blur=float(self.v_blur.get()),
            negate=self.v_negate.get(),
            do_threshold=self.v_thresh.get(),
            threshold_pct=int(self.v_thresh_pct.get()),
            do_pad=self.v_do_pad.get(),
            pad_size=int(self.v_pad_size.get()),
            pad_bg=self.v_pad_bg.get(),
            do_trace=self.v_do_trace.get(),
            potrace_turdsize=int(self.v_turd.get()),
            potrace_smooth=self.v_smooth.get(),
            do_export=self.v_do_export.get(),
            export_width=int(self.v_export_w.get()),
            export_area_drawing=self.v_area.get(),
        )

    def run_pipeline(self) -> None:
        if not self.input_path:
            messagebox.showwarning("No input", "Choose an input folder or image.")
            return
        if not self.output_root:
            messagebox.showwarning("No output", "Choose an output folder.")
            return

        # Dependencies
        magick = which("magick")
        potrace = potrace = find_potrace()

        inkscape = which("inkscape") or which("inkscape.com") or which("inkscape.exe")

        if not magick or not potrace or not inkscape:
            self.check_deps()
            messagebox.showerror(
                "Missing dependencies",
                "One or more required tools are missing.\n\n"
                "Install and ensure on PATH:\n"
                "- ImageMagick (magick)\n"
                "- Potrace (potrace)\n"
                "- Inkscape (inkscape)\n"
            )
            return

        settings = self.get_settings()

        input_files = list_images(self.input_path)
        if not input_files:
            messagebox.showerror("No images", "No supported image files were found.")
            return

        # Output folders
        out_root = self.output_root
        d_pre = out_root / "01_preprocessed"
        d_pad = out_root / "02_padded"
        d_svg = out_root / "03_svg"
        d_png = out_root / "04_png"

        for d in [d_pre, d_pad, d_svg, d_png]:
            d.mkdir(parents=True, exist_ok=True)

        # Progress setup
        total_steps_per_file = 0
        if settings.do_preprocess:
            total_steps_per_file += 1
        if settings.do_pad:
            total_steps_per_file += 1
        if settings.do_trace:
            total_steps_per_file += 1
        if settings.do_export:
            total_steps_per_file += 1

        total_ops = max(1, len(input_files) * max(1, total_steps_per_file))
        done_ops = 0
        self.progress["maximum"] = total_ops
        self.progress["value"] = 0

        self._log("\n--- RUN START ---\n")
        self._log(f"Input files: {len(input_files)}\n")
        self._log(f"Output root: {out_root}\n\n")

        try:
            for idx, src in enumerate(input_files, start=1):
                stem = src.stem
                self._log(f"[{idx}/{len(input_files)}] {src.name}\n")

                # Stage A: preprocess
                cur = src
                if settings.do_preprocess:
                    out_pre = d_pre / f"{stem}.png"
                    preprocess_magick(
                        magick_exe=magick,
                        in_path=src,
                        out_path=out_pre,
                        grayscale=settings.grayscale,
                        auto_level=settings.auto_level,
                        contrast_stretch=settings.contrast_stretch,
                        cs_black=settings.cs_black,
                        cs_white=settings.cs_white,
                        median_radius=settings.median,
                        blur_sigma=settings.blur,
                        negate=settings.negate,
                        do_threshold=settings.do_threshold,
                        threshold_pct=settings.threshold_pct,
                    )
                    cur = out_pre
                    done_ops += 1
                    self.progress["value"] = done_ops
                    self._log(f"  A) preprocessed -> {out_pre.name}\n")

                # Stage B: pad/resize
                if settings.do_pad:
                    out_pad = d_pad / f"{stem}.png"
                    pad_square_pillow(cur, out_pad, size=settings.pad_size, bg_mode=settings.pad_bg)
                    cur = out_pad
                    done_ops += 1
                    self.progress["value"] = done_ops
                    self._log(f"  B) padded -> {out_pad.name}\n")

                # Stage C: trace SVG
                svg_path = d_svg / f"{stem}.svg"
                if settings.do_trace:
                    # cutoff is threshold_pct if you enabled threshold, otherwise default 45
                    cutoff = settings.threshold_pct if settings.do_threshold else 45
                    trace_to_svg_magick_potrace(
                        magick_exe=magick,
                        potrace_exe=potrace,
                        in_png=cur,
                        out_svg=svg_path,
                        cutoff_pct=cutoff,
                        invert=settings.negate,  # if user negated, tracing sees it already; but keep it consistent
                        turdsize=settings.potrace_turdsize,
                        smooth=settings.potrace_smooth,
                    )
                    done_ops += 1
                    self.progress["value"] = done_ops
                    self._log(f"  C) traced -> {svg_path.name}\n")

                # Stage D: export PNG
                if settings.do_export:
                    out_png = d_png / f"{stem}.png"
                    export_svg_to_png_inkscape(
                        inkscape_exe=inkscape,
                        in_svg=svg_path if settings.do_trace else Path(cur),
                        out_png=out_png,
                        width=settings.export_width,
                        export_area_drawing=settings.export_area_drawing,
                    )
                    done_ops += 1
                    self.progress["value"] = done_ops
                    self._log(f"  D) exported -> {out_png.name}\n")

                self._log("\n")

            self._log("--- RUN COMPLETE ---\n")
            self._log(f"01_preprocessed: {d_pre}\n")
            self._log(f"02_padded:       {d_pad}\n")
            self._log(f"03_svg:          {d_svg}\n")
            self._log(f"04_png:          {d_png}\n\n")
            messagebox.showinfo("Done", "Pipeline completed successfully.")
        except Exception as e:
            self._log(f"\n*** ERROR ***\n{e}\n")
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    App().mainloop()
