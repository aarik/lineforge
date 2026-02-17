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
        self.geometry("1040x780")
        self.minsize(980, 720)

        self.s = Settings()

        self._log_fh = None
        self._log_path = None

        self._build_ui()
        self.start_new_log_session()
        self.refresh_found_count()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------- UI ----------------
    def _build_ui(self):
        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        # Input
        tk.Label(top, text="Input (file or folder)").grid(row=0, column=0, sticky="w")
        self.e_in = tk.Entry(top, width=70)
        self.e_in.insert(0, str(Path.cwd()))
        self.e_in.grid(row=0, column=1, padx=6, sticky="we")
        tk.Button(top, text="Browse File", command=self.browse_input_file).grid(row=0, column=2, padx=(0, 6))
        tk.Button(top, text="Browse Folder", command=self.browse_input_folder).grid(row=0, column=3)

        # Output
        tk.Label(top, text="Output folder").grid(row=1, column=0, sticky="w")
        self.e_out = tk.Entry(top, width=70)
        self.e_out.insert(0, str(Path.cwd() / "output"))
        self.e_out.grid(row=1, column=1, padx=6, sticky="we")
        tk.Button(top, text="Browse", command=self.browse_output_folder).grid(row=1, column=2, padx=(0, 6), sticky="w")

        # Recursive + Found count
        self.v_recursive = tk.BooleanVar(value=self.s.input_recursive)
        tk.Checkbutton(top, text="Include subfolders (recursive)", variable=self.v_recursive, command=self.refresh_found_count)\
            .grid(row=2, column=1, sticky="w", padx=6, pady=(6, 0))

        self.lbl_found = tk.Label(top, text="Found: 0 images", anchor="w")
        self.lbl_found.grid(row=2, column=2, columnspan=2, sticky="w", pady=(6, 0))

        top.columnconfigure(1, weight=1)

        # Controls frame
        controls = tk.Frame(self)
        controls.pack(fill="x", padx=10)

        # A) Preprocess controls
        a = tk.LabelFrame(controls, text="A) Preprocess")
        a.grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="nsew")

        self.v_do_pre = tk.BooleanVar(value=self.s.do_preprocess)
        tk.Checkbutton(a, text="Enable", variable=self.v_do_pre).grid(row=0, column=0, sticky="w")

        self.v_gray = tk.BooleanVar(value=self.s.grayscale)
        self.v_autolvl = tk.BooleanVar(value=self.s.auto_level)
        self.v_cstretch = tk.BooleanVar(value=self.s.contrast_stretch)
        self.v_neg = tk.BooleanVar(value=self.s.negate)
        self.v_doth = tk.BooleanVar(value=self.s.do_threshold)

        tk.Checkbutton(a, text="Grayscale", variable=self.v_gray).grid(row=1, column=0, sticky="w")
        tk.Checkbutton(a, text="Auto-level", variable=self.v_autolvl).grid(row=2, column=0, sticky="w")
        tk.Checkbutton(a, text="Contrast-stretch", variable=self.v_cstretch).grid(row=3, column=0, sticky="w")
        tk.Checkbutton(a, text="Negate", variable=self.v_neg).grid(row=4, column=0, sticky="w")
        tk.Checkbutton(a, text="Threshold", variable=self.v_doth).grid(row=5, column=0, sticky="w")

        tk.Label(a, text="Threshold %").grid(row=6, column=0, sticky="w")
        self.v_th = tk.IntVar(value=self.s.threshold_pct)
        tk.Scale(a, from_=0, to=100, orient="horizontal", variable=self.v_th, length=220).grid(row=7, column=0, sticky="we")

        tk.Label(a, text="Median").grid(row=8, column=0, sticky="w")
        self.v_med = tk.IntVar(value=self.s.median)
        tk.Scale(a, from_=0, to=10, orient="horizontal", variable=self.v_med, length=220).grid(row=9, column=0, sticky="we")

        tk.Label(a, text="Blur").grid(row=10, column=0, sticky="w")
        self.v_blur = tk.DoubleVar(value=self.s.blur)
        tk.Scale(a, from_=0.0, to=10.0, resolution=0.1, orient="horizontal", variable=self.v_blur, length=220)\
            .grid(row=11, column=0, sticky="we")

        # B) Pad controls
        b = tk.LabelFrame(controls, text="B) Pad")
        b.grid(row=0, column=1, padx=(0, 8), pady=(0, 8), sticky="nsew")

        self.v_do_pad = tk.BooleanVar(value=self.s.do_pad)
        tk.Checkbutton(b, text="Enable", variable=self.v_do_pad).grid(row=0, column=0, sticky="w")

        tk.Label(b, text="Size").grid(row=1, column=0, sticky="w")
        self.v_size = tk.IntVar(value=self.s.pad_size)
        tk.Scale(b, from_=64, to=2048, resolution=64, orient="horizontal", variable=self.v_size, length=260)\
            .grid(row=2, column=0, sticky="we")

        tk.Label(b, text="Background").grid(row=3, column=0, sticky="w")
        self.v_bg = tk.StringVar(value=self.s.pad_bg)
        tk.OptionMenu(b, self.v_bg, "white", "black", "transparent").grid(row=4, column=0, sticky="w")

        tk.Label(b, text="Output format").grid(row=5, column=0, sticky="w")
        self.v_fmt = tk.StringVar(value=self.s.pad_out_fmt)
        tk.OptionMenu(b, self.v_fmt, "jpg", "png").grid(row=6, column=0, sticky="w")

        tk.Label(b, text="JPEG quality").grid(row=7, column=0, sticky="w")
        self.v_q = tk.IntVar(value=self.s.jpeg_quality)
        tk.Scale(b, from_=50, to=100, orient="horizontal", variable=self.v_q, length=260)\
            .grid(row=8, column=0, sticky="we")

        # C) Trace controls
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
        tk.Checkbutton(c, text="Smooth", variable=self.v_smooth).grid(row=6, column=0, sticky="w")

        # D) Export controls
        d = tk.LabelFrame(self, text="D) Export → PNG")
        d.pack(fill="x", padx=10, pady=(0, 8))

        self.v_do_export = tk.BooleanVar(value=self.s.do_export)
        tk.Checkbutton(d, text="Enable", variable=self.v_do_export).grid(row=0, column=0, sticky="w")

        tk.Label(d, text="Width").grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.v_w = tk.IntVar(value=self.s.export_width)
        tk.Scale(d, from_=64, to=4096, resolution=64, orient="horizontal", variable=self.v_w, length=420)\
            .grid(row=0, column=2, sticky="w", padx=6)

        self.v_area = tk.BooleanVar(value=self.s.export_area_drawing)
        tk.Checkbutton(d, text="Area: drawing", variable=self.v_area).grid(row=0, column=3, sticky="w", padx=(12, 0))

        # Buttons
        btn = tk.Frame(self)
        btn.pack(fill="x", padx=10, pady=(0, 8))

        tk.Button(btn, text="Run ALL (A→D)", command=self.run_all_clicked, width=16).pack(side="left")
        tk.Button(btn, text="Refresh Found Count", command=self.refresh_found_count, width=18).pack(side="left", padx=6)
        tk.Button(btn, text="Open output folder", command=self.open_output_folder, width=18).pack(side="left", padx=6)
        tk.Button(btn, text="Open last log", command=self.open_last_log, width=14).pack(side="left", padx=6)
        tk.Button(btn, text="Clear log", command=self.clear_log, width=12).pack(side="right")

        # Log box
        self.txt = tk.Text(self, wrap="word")
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.write(
            "Outputs:\n"
            "  A -> output\\01_preprocessed\n"
            "  B -> output\\02_padded\n"
            "  C -> output\\03_svg\n"
            "  D -> output\\04_export_png\n\n"
        )

    # ---------------- browse ----------------
    def browse_input_file(self):
        p = filedialog.askopenfilename(
            title="Select an input image file",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("All files", "*.*")],
        )
        if p:
            self.e_in.delete(0, "end")
            self.e_in.insert(0, p)
            self.refresh_found_count()

    def browse_input_folder(self):
        p = filedialog.askdirectory(title="Select an input folder")
        if p:
            self.e_in.delete(0, "end")
            self.e_in.insert(0, p)
            self.refresh_found_count()

    def browse_output_folder(self):
        p = filedialog.askdirectory(title="Select an output folder")
        if p:
            self.e_out.delete(0, "end")
            self.e_out.insert(0, p)

    # ---------------- logging ----------------
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

    # ---------------- helpers ----------------
    def sync(self):
        # input
        self.s.input_recursive = bool(self.v_recursive.get())

        # stage enables
        self.s.do_preprocess = bool(self.v_do_pre.get())
        self.s.do_pad = bool(self.v_do_pad.get())
        self.s.do_trace = bool(self.v_do_trace.get())
        self.s.do_export = bool(self.v_do_export.get())

        # preprocess
        self.s.grayscale = bool(self.v_gray.get())
        self.s.auto_level = bool(self.v_autolvl.get())
        self.s.contrast_stretch = bool(self.v_cstretch.get())
        self.s.negate = bool(self.v_neg.get())
        self.s.do_threshold = bool(self.v_doth.get())
        self.s.threshold_pct = int(self.v_th.get())
        self.s.median = int(self.v_med.get())
        self.s.blur = float(self.v_blur.get())

        # pad
        self.s.pad_size = int(self.v_size.get())
        self.s.pad_bg = self.v_bg.get().strip().lower()
        self.s.pad_out_fmt = self.v_fmt.get().strip().lower()
        self.s.jpeg_quality = int(self.v_q.get())

        # trace
        self.s.trace_cutoff_pct = int(self.v_cut.get())
        self.s.trace_invert = bool(self.v_trace_inv.get())
        self.s.potrace_turdsize = int(self.v_turd.get())
        self.s.potrace_smooth = bool(self.v_smooth.get())

        # export
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
            self.lbl_found.config(text=f"Found: {len(files)} images" + (" (recursive)" if recursive else ""))
        except Exception:
            self.lbl_found.config(text="Found: ? images")

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

    # ---------------- run ----------------
    def run_all_clicked(self):
        self.start_new_log_session()
        self.sync()

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
