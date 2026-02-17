import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

from ..settings import Settings
from ..utils import list_images
from ..pipeline import run_all


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LineForge")
        self.geometry("1040x840")
        self.minsize(980, 720)

        self.s = Settings()

        self._log_fh = None
        self._log_path = None

        self._build_ui()
        self.start_new_log_session()
        self.refresh_found_count()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="Input (file or folder)").grid(row=0, column=0, sticky="w")
        self.e_in = tk.Entry(top, width=70)
        self.e_in.insert(0, str(Path.cwd()))
        self.e_in.grid(row=0, column=1, padx=6, sticky="we")
        tk.Button(top, text="Browse File", command=self.browse_input_file).grid(row=0, column=2, padx=(0, 6))
        tk.Button(top, text="Browse Folder", command=self.browse_input_folder).grid(row=0, column=3)

        tk.Label(top, text="Output folder").grid(row=1, column=0, sticky="w")
        self.e_out = tk.Entry(top, width=70)
        self.e_out.insert(0, str(Path.cwd() / "output"))
        self.e_out.grid(row=1, column=1, padx=6, sticky="we")
        tk.Button(top, text="Browse", command=self.browse_output_folder).grid(row=1, column=2, padx=(0, 6), sticky="w")

        self.v_recursive = tk.BooleanVar(value=self.s.input_recursive)
        tk.Checkbutton(
            top,
            text="Include subfolders (recursive)",
            variable=self.v_recursive,
            command=self.refresh_found_count
        ).grid(row=2, column=1, sticky="w", padx=6, pady=(6, 0))

        self.v_handle_ico = tk.BooleanVar(value=self.s.handle_ico)
        tk.Checkbutton(
            top,
            text="Handle .ico (extract frames + rebuild)",
            variable=self.v_handle_ico,
            command=self.refresh_found_count
        ).grid(row=3, column=1, sticky="w", padx=6, pady=(2, 0))

        self.lbl_found = tk.Label(top, text="Found: 0 inputs", anchor="w")
        self.lbl_found.grid(row=2, column=2, columnspan=2, sticky="w", pady=(6, 0))

        top.columnconfigure(1, weight=1)

        controls = tk.Frame(self)
        controls.pack(fill="x", padx=10)

        # A) Preprocess
        a = tk.LabelFrame(controls, text="A) Preprocess")
        a.grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="nsew")

        self.v_do_pre = tk.BooleanVar(value=self.s.do_preprocess)
        tk.Checkbutton(a, text="Enable", variable=self.v_do_pre).grid(row=0, column=0, sticky="w")

        self.v_gray = tk.BooleanVar(value=self.s.grayscale)
        self.v_autolvl = tk.BooleanVar(value=self.s.auto_level)
        self.v_cstretch = tk.BooleanVar(value=self.s.contrast_stretch)
        self.v_neg = tk.BooleanVar(value=self.s.negate)

        tk.Checkbutton(a, text="Grayscale", variable=self.v_gray).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(a, text="Auto-level", variable=self.v_autolvl).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(a, text="Contrast-stretch", variable=self.v_cstretch).grid(row=3, column=0, sticky="w")
        tk.Checkbutton(a, text="Negate", variable=self.v_neg).grid(row=4, column=0, sticky="w")

        tk.Label(a, text="Median").grid(row=5, column=0, sticky="w")
        self.v_med = tk.IntVar(value=self.s.median)
        tk.Scale(a, from_=0, to=10, orient="horizontal", variable=self.v_med, length=220).grid(row=6, column=0, sticky="we")

        tk.Label(a, text="Blur").grid(row=7, column=0, sticky="w")
        self.v_blur = tk.DoubleVar(value=self.s.blur)
        tk.Scale(a, from_=0.0, to=10.0, resolution=0.1, orient="horizontal", variable=self.v_blur, length=220)\
            .grid(row=8, column=0, sticky="we")

        tk.Label(a, text="Finish mode").grid(row=9, column=0, sticky="w", pady=(6, 0))
        self.v_mode = tk.StringVar(value=self.s.preprocess_mode)

        tk.Radiobutton(a, text="None", value="none", variable=self.v_mode, command=self._toggle_pre_mode_ui)\
            .grid(row=10, column=0, sticky="w")
        tk.Radiobutton(a, text="B/W Threshold", value="threshold", variable=self.v_mode, command=self._toggle_pre_mode_ui)\
            .grid(row=11, column=0, sticky="w")
        tk.Radiobutton(a, text="Grayscale Quantize", value="quantize", variable=self.v_mode, command=self._toggle_pre_mode_ui)\
            .grid(row=12, column=0, sticky="w")

        tk.Label(a, text="Threshold %").grid(row=13, column=0, sticky="w")
        self.v_th = tk.IntVar(value=self.s.threshold_pct)
        self.scale_th = tk.Scale(a, from_=0, to=100, orient="horizontal", variable=self.v_th, length=220)
        self.scale_th.grid(row=14, column=0, sticky="we")

        tk.Label(a, text="Quantize levels").grid(row=15, column=0, sticky="w")
        self.v_qlevels = tk.IntVar(value=self.s.quantize_levels)
        self.scale_q = tk.Scale(a, from_=2, to=256, resolution=1, orient="horizontal", variable=self.v_qlevels, length=220)
        self.scale_q.grid(row=16, column=0, sticky="we")

        # B) Pad
        b = tk.LabelFrame(controls, text="B) Pad")
        b.grid(row=0, column=1, padx=(0, 8), pady=(0, 8), sticky="nsew")

        self.v_do_pad = tk.BooleanVar(value=self.s.do_pad)
        tk.Checkbutton(b, text="Enable", variable=self.v_do_pad).grid(row=0, column=0, sticky="w")

        tk.Label(b, text="Size").grid(row=1, column=0, sticky="w")
        self.v_size = tk.IntVar(value=self.s.pad_size)
        tk.Scale(b, from_=16, to=2048, resolution=16, orient="horizontal", variable=self.v_size, length=260)\
            .grid(row=2, column=0, sticky="we")

        tk.Label(b, text="Background").grid(row=3, column=0, sticky="w")
        self.v_bg = tk.StringVar(value=self.s.pad_bg)
        tk.OptionMenu(b, self.v_bg, "white", "black", "transparent").grid(row=4, column=0, sticky="w")

        tk.Label(b, text="Output format").grid(row=5, column=0, sticky="w")
        self.v_fmt = tk.StringVar(value=self.s.pad_out_fmt)
        tk.OptionMenu(b, self.v_fmt, "png", "jpg").grid(row=6, column=0, sticky="w")

        tk.Label(b, text="JPEG quality").grid(row=7, column=0, sticky="w")
        self.v_q = tk.IntVar(value=self.s.jpeg_quality)
        tk.Scale(b, from_=50, to=100, orient="horizontal", variable=self.v_q, length=260)\
            .grid(row=8, column=0, sticky="we")

        # C) Trace
        c = tk.LabelFrame(controls, text="C) Trace → SVG")
        c.grid(row=0, column=2, padx=(0, 0), pady=(0, 8), sticky="nsew")

        self.v_do_trace = tk.BooleanVar(value=self.s.do_trace)
        tk.Checkbutton(c, text="Enable", variable=self.v_do_trace).grid(row=0, column=0, sticky="w")

        tk.Label(c, text="Cutoff %").grid(row=1, column=0, sticky="w")
        self.v_cut = tk.IntVar(value=self.s.trace_cutoff_pct)
        tk.Scale(c, from_=0, to=100, orient="horizontal", variable=self.v_cut, length=260)\
            .grid(row=2, column=0, sticky="we")

        self.v_trace_inv = tk.BooleanVar(value=self.s.trace_invert)
        tk.Checkbutton(c, text="Invert before threshold", variable=self.v_trace_inv).grid(row=3, column=0, sticky="w")

        tk.Label(c, text="Turdsize").grid(row=4, column=0, sticky="w")
        self.v_turd = tk.IntVar(value=self.s.potrace_turdsize)
        tk.Scale(c, from_=0, to=50, orient="horizontal", variable=self.v_turd, length=260)\
            .grid(row=5, column=0, sticky="we")

        self.v_smooth = tk.BooleanVar(value=self.s.potrace_smooth)
        tk.Checkbutton(c, text="Smooth (default)", variable=self.v_smooth).grid(row=6, column=0, sticky="w")

        # D) Export
        d = tk.LabelFrame(self, text="D) Export → PNG")
        d.pack(fill="x", padx=10, pady=(0, 8))

        self.v_do_export = tk.BooleanVar(value=self.s.do_export)
        tk.Checkbutton(d, text="Enable", variable=self.v_do_export).grid(row=0, column=0, sticky="w")

        tk.Label(d, text="Width").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.v_w = tk.IntVar(value=self.s.export_width)
        tk.Scale(d, from_=16, to=4096, resolution=16, orient="horizontal", variable=self.v_w, length=420)\
            .grid(row=0, column=2, sticky="w", padx=6)

        self.v_area = tk.BooleanVar(value=self.s.export_area_drawing)
        tk.Checkbutton(d, text="Area: drawing", variable=self.v_area).grid(row=0, column=3, sticky="w", padx=(12, 0))

        # Buttons
        btn = tk.Frame(self)
        btn.pack(fill="x", padx=10, pady=(0, 8))

        tk.Button(btn, text="Run ALL (A→D)", command=self.run_all_clicked, width=16).pack(side="left")
        tk.Button(btn, text="Icon-safe defaults", command=self.apply_icon_defaults, width=16).pack(side="left", padx=6)
        tk.Button(btn, text="Refresh Found Count", command=self.refresh_found_count, width=18).pack(side="left", padx=6)
        tk.Button(btn, text="Open output folder", command=self.open_output_folder, width=18).pack(side="left", padx=6)
        tk.Button(btn, text="Open last log", command=self.open_last_log, width=14).pack(side="left", padx=6)
        tk.Button(btn, text="Clear log", command=self.clear_log, width=12).pack(side="right")

        self.txt = tk.Text(self, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.write(
            "Outputs:\n"
            "  A -> output\\01_preprocessed\n"
            "  B -> output\\02_padded\n"
            "  C -> output\\03_svg\n"
            "  D -> output\\04_export_png\n"
            "  ICO -> output\\05_ico\n\n"
        )

        self._toggle_pre_mode_ui()

    def _toggle_pre_mode_ui(self):
        mode = (self.v_mode.get() or "none").strip().lower()
        if mode == "threshold":
            self.scale_th.configure(state="normal")
            self.scale_q.configure(state="disabled")
        elif mode == "quantize":
            self.scale_th.configure(state="disabled")
            self.scale_q.configure(state="normal")
        else:
            self.scale_th.configure(state="disabled")
            self.scale_q.configure(state="disabled")

    def apply_icon_defaults(self):
        # Core icon workflow
        self.v_handle_ico.set(True)
        self.v_do_pre.set(True)
        self.v_do_pad.set(True)
        self.v_do_trace.set(False)
        self.v_do_export.set(False)

        # Preprocess defaults for icons
        self.v_gray.set(True)
        self.v_autolvl.set(True)
        self.v_cstretch.set(True)
        self.v_neg.set(False)
        self.v_med.set(0)
        self.v_blur.set(0.0)

        # Quantize mode is usually the best "make it simpler but not destroyed"
        self.v_mode.set("quantize")
        self.v_qlevels.set(16)
        self.v_th.set(45)

        # Pad defaults for icons
        self.v_fmt.set("png")
        self.v_bg.set("transparent")
        self.v_size.set(256)
        self.v_q.set(95)

        # Export width set anyway in case they flip export on later
        self.v_w.set(256)
        self.v_area.set(True)

        self._toggle_pre_mode_ui()
        self.refresh_found_count()
        self.write("\nApplied icon-safe defaults.\n")

    # ---- browse ----
    def browse_input_file(self):
        p = filedialog.askopenfilename(
            title="Select input file",
            filetypes=[
                ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.ico"),
                ("All files", "*.*"),
            ],
        )
        if p:
            self.e_in.delete(0, "end")
            self.e_in.insert(0, p)
            self.refresh_found_count()

    def browse_input_folder(self):
        p = filedialog.askdirectory(title="Select input folder")
        if p:
            self.e_in.delete(0, "end")
            self.e_in.insert(0, p)
            self.refresh_found_count()

    def browse_output_folder(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.e_out.delete(0, "end")
            self.e_out.insert(0, p)

    # ---- logging ----
    def start_new_log_session(self):
        self.close_log_session()
        logs = Path.cwd() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._log_path = logs / f"lineforge_{stamp}.log"
        self._log_fh = open(self._log_path, "a", encoding="utf-8")
        self.write(f"--- Log: {self._log_path} ---\n")

    def close_log_session(self):
        try:
            if self._log_fh:
                self._log_fh.flush()
                self._log_fh.close()
        except Exception:
            pass
        self._log_fh = None

    def write(self, msg: str):
        self.txt.insert("end", msg)
        self.txt.see("end")
        self.update_idletasks()
        try:
            if self._log_fh:
                self._log_fh.write(msg)
                self._log_fh.flush()
        except Exception:
            pass

    def clear_log(self):
        self.txt.delete("1.0", "end")

    # ---- helpers ----
    def sync(self):
        self.s.input_recursive = bool(self.v_recursive.get())
        self.s.handle_ico = bool(self.v_handle_ico.get())

        self.s.do_preprocess = bool(self.v_do_pre.get())
        self.s.do_pad = bool(self.v_do_pad.get())
        self.s.do_trace = bool(self.v_do_trace.get())
        self.s.do_export = bool(self.v_do_export.get())

        self.s.grayscale = bool(self.v_gray.get())
        self.s.auto_level = bool(self.v_autolvl.get())
        self.s.contrast_stretch = bool(self.v_cstretch.get())
        self.s.negate = bool(self.v_neg.get())
        self.s.median = int(self.v_med.get())
        self.s.blur = float(self.v_blur.get())

        self.s.preprocess_mode = (self.v_mode.get() or "none").strip().lower()
        self.s.threshold_pct = int(self.v_th.get())
        self.s.quantize_levels = int(self.v_qlevels.get())

        self.s.pad_size = int(self.v_size.get())
        self.s.pad_bg = self.v_bg.get().strip().lower()
        self.s.pad_out_fmt = self.v_fmt.get().strip().lower()
        self.s.jpeg_quality = int(self.v_q.get())

        self.s.trace_cutoff_pct = int(self.v_cut.get())
        self.s.trace_invert = bool(self.v_trace_inv.get())
        self.s.potrace_turdsize = int(self.v_turd.get())
        self.s.potrace_smooth = bool(self.v_smooth.get())

        self.s.export_width = int(self.v_w.get())
        self.s.export_area_drawing = bool(self.v_area.get())

    def paths(self):
        inp = Path(self.e_in.get().strip())
        out = Path(self.e_out.get().strip())
        if not inp.exists():
            raise FileNotFoundError(f"Input path not found: {inp}")
        out.mkdir(parents=True, exist_ok=True)
        return inp, out

    def refresh_found_count(self):
        try:
            inp = Path(self.e_in.get().strip())
            recursive = bool(self.v_recursive.get())
            files = list_images(inp, recursive=recursive)
            self.lbl_found.config(text=f"Found: {len(files)} inputs" + (" (recursive)" if recursive else ""))
        except Exception:
            self.lbl_found.config(text="Found: ? inputs")

    def open_output_folder(self):
        try:
            out = Path(self.e_out.get().strip()).resolve()
            out.mkdir(parents=True, exist_ok=True)
            os.startfile(str(out))
        except Exception as e:
            messagebox.showerror("Open output folder failed", str(e))

    def open_last_log(self):
        try:
            if self._log_path and self._log_path.exists():
                os.startfile(str(self._log_path.resolve()))
                return
            logs = Path.cwd() / "logs"
            ls = sorted(logs.glob("lineforge_*.log"))
            if ls:
                os.startfile(str(ls[-1].resolve()))
            else:
                messagebox.showinfo("Open last log", "No log files found.")
        except Exception as e:
            messagebox.showerror("Open last log failed", str(e))

    def on_close(self):
        self.close_log_session()
        self.destroy()

    # ---- run ----
    def run_all_clicked(self):
        self.start_new_log_session()
        self.sync()
        self._toggle_pre_mode_ui()
        try:
            inp, out = self.paths()
            self.refresh_found_count()
            self.write("\nRunning ALL stages...\n")
            run_all(inp, out, self.s, self.write)
            self.write("\nDONE.\n")
            self.open_output_folder()
        except Exception as e:
            self.write(f"\nFAILED: {e}\n")
            messagebox.showerror("Run failed", str(e))
