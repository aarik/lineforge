from pathlib import Path

from .utils import list_images
from .deps import find_magick, find_potrace, find_inkscape
from .settings import Settings
from .stages.preprocess import preprocess_magick
from .stages.pad import pad_square
from .stages.trace import trace_to_svg
from .stages.export import export_svg_to_png


def run_all(input_path: Path, output_root: Path, s: Settings, log) -> None:
    files = list_images(input_path, recursive=s.input_recursive)
    if not files:
        raise RuntimeError(
            "No supported images found.\n"
            "If your images are inside subfolders, enable: Include subfolders (recursive)."
        )

    output_root.mkdir(parents=True, exist_ok=True)

    # A) preprocess
    if s.do_preprocess:
        magick = find_magick()
        if not magick:
            raise RuntimeError("ImageMagick 'magick' not found on PATH.")
        d1 = output_root / "01_preprocessed"
        d1.mkdir(parents=True, exist_ok=True)

        log(f"\n[A] Preprocess -> {d1}\n")
        for i, src in enumerate(files, 1):
            dst = d1 / (src.stem + ".png")
            log(f"  [{i}/{len(files)}] {src.name}\n")
            preprocess_magick(
                magick, src, dst,
                s.grayscale, s.auto_level, s.contrast_stretch,
                s.cs_black, s.cs_white, s.median, s.blur,
                s.negate, s.do_threshold, s.threshold_pct
            )
        files = list_images(d1, recursive=False)

    # B) pad
    if s.do_pad:
        d2 = output_root / "02_padded"
        d2.mkdir(parents=True, exist_ok=True)
        log(f"\n[B] Pad -> {d2}\n")
        for i, src in enumerate(files, 1):
            out_base = d2 / src.stem
            log(f"  [{i}/{len(files)}] {src.name}\n")
            pad_square(src, out_base, s.pad_size, s.pad_bg, s.pad_out_fmt, s.jpeg_quality)
        files = list_images(d2, recursive=False)

    # C) trace
    if s.do_trace:
        magick = find_magick()
        if not magick:
            raise RuntimeError("ImageMagick 'magick' not found on PATH (needed for trace PBM).")
        potrace = find_potrace()
        if not potrace:
            raise RuntimeError("potrace not found. Put potrace.exe in bin\\ or install potrace.")
        d3 = output_root / "03_svg"
        d3.mkdir(parents=True, exist_ok=True)
        log(f"\n[C] Trace -> {d3}\n")
        for i, src in enumerate(files, 1):
            dst = d3 / (src.stem + ".svg")
            log(f"  [{i}/{len(files)}] {src.name}\n")
            trace_to_svg(
                magick, potrace, src, dst,
                s.trace_cutoff_pct, s.trace_invert,
                s.potrace_turdsize, s.potrace_smooth
            )
        files = sorted(d3.glob("*.svg"))

    # D) export
    if s.do_export:
        inkscape = find_inkscape()
        if not inkscape:
            raise RuntimeError("Inkscape not found on PATH (needed for export).")
        d4 = output_root / "04_export_png"
        d4.mkdir(parents=True, exist_ok=True)
        log(f"\n[D] Export -> {d4}\n")
        for i, svg in enumerate(files, 1):
            dst = d4 / (Path(svg).stem + ".png")
            log(f"  [{i}/{len(files)}] {Path(svg).name}\n")
            export_svg_to_png(inkscape, Path(svg), dst, s.export_width, s.export_area_drawing)
