from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .utils import list_images
from .deps import find_magick, find_potrace, find_inkscape
from .settings import Settings
from .stages.preprocess import preprocess_magick
from .stages.pad import pad_square
from .stages.trace import trace_to_svg
from .stages.export import export_svg_to_png
from .stages.icon import split_ico_to_pngs, rebuild_ico_from_pngs


def _choose_last_raster_dir(output_root: Path, s: Settings) -> Path:
    if s.do_export and (output_root / "04_export_png").exists():
        return output_root / "04_export_png"
    if s.do_pad and (output_root / "02_padded").exists():
        return output_root / "02_padded"
    if s.do_preprocess and (output_root / "01_preprocessed").exists():
        return output_root / "01_preprocessed"
    return output_root


def run_all(input_path: Path, output_root: Path, s: Settings, log) -> None:
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    files = list_images(input_path, recursive=s.input_recursive)
    if not files:
        raise RuntimeError(
            "No supported images found.\n"
            "If your images are inside subfolders, enable: Include subfolders (recursive)."
        )

    # ICO expand (optional)
    magick_for_ico = None
    if s.handle_ico:
        magick_for_ico = find_magick()
        if not magick_for_ico:
            raise RuntimeError("ImageMagick 'magick' not found on PATH (required for ICO extract/rebuild).")

    ico_map: Dict[str, Dict[str, object]] = {}
    if s.handle_ico:
        expanded: List[Path] = []
        ico_files = [p for p in files if p.suffix.lower() == ".ico"]
        other_files = [p for p in files if p.suffix.lower() != ".ico"]

        if ico_files:
            log(f"\n[ICO] Extracting frames from {len(ico_files)} icon(s)...\n")
            ico_stage_dir = output_root / "_ico_frames"
            ico_stage_dir.mkdir(parents=True, exist_ok=True)

            for ico in ico_files:
                frame_dir = ico_stage_dir / ico.stem
                frames = split_ico_to_pngs(magick_for_ico, ico, frame_dir)
                if not frames:
                    log(f"  WARN: no frames extracted from {ico.name}\n")
                    continue
                ico_map[ico.stem] = {"src": ico, "frames": frames}
                expanded.extend(frames)
                log(f"  {ico.name}: {len(frames)} frame(s)\n")

        files = other_files + expanded

    if not files:
        raise RuntimeError("No images to process after ICO extraction. (Were the ICOs valid?)")

    # A) preprocess
    if s.do_preprocess:
        mag = find_magick()
        if not mag:
            raise RuntimeError("ImageMagick 'magick' not found on PATH.")
        d1 = output_root / "01_preprocessed"
        d1.mkdir(parents=True, exist_ok=True)

        log(f"\n[A] Preprocess -> {d1}\n")
        for i, src in enumerate(files, 1):
            dst = d1 / (src.stem + ".png")
            log(f"  [{i}/{len(files)}] {src.name}\n")
            preprocess_magick(
                mag, src, dst,
                s.grayscale, s.auto_level, s.contrast_stretch,
                s.cs_black, s.cs_white, s.median, s.blur,
                s.negate,
                s.preprocess_mode, s.threshold_pct, s.quantize_levels
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
        mag = find_magick()
        if not mag:
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
                mag, potrace, src, dst,
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

    # ICO rebuild (optional)
    if s.handle_ico and ico_map:
        mag = find_magick()
        if not mag:
            raise RuntimeError("ImageMagick 'magick' not found on PATH (required for ICO rebuild).")

        src_raster_dir = _choose_last_raster_dir(output_root, s)
        out_ico_dir = output_root / "05_ico"
        out_ico_dir.mkdir(parents=True, exist_ok=True)

        log(f"\n[ICO] Rebuilding icons -> {out_ico_dir}\n")

        for stem, info in ico_map.items():
            frames: List[Path] = info["frames"]  # type: ignore
            processed_frames = []

            for fr in frames:
                # prefer png, but allow jpg if user forced it
                cand_png = src_raster_dir / (Path(fr).stem + ".png")
                cand_jpg = src_raster_dir / (Path(fr).stem + ".jpg")
                if cand_png.exists():
                    processed_frames.append(cand_png)
                elif cand_jpg.exists():
                    processed_frames.append(cand_jpg)

            if not processed_frames:
                log(f"  WARN: No processed frames found for {stem}.ico (skipping)\n")
                continue

            dst_ico = out_ico_dir / f"{stem}.ico"
            rebuild_ico_from_pngs(mag, processed_frames, dst_ico)
            log(f"  OK: {dst_ico.name} ({len(processed_frames)} frame(s))\n")
