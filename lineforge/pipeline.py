from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from .utils import list_images
from .deps import find_magick, find_potrace, find_inkscape
from .settings import Settings
from .stages.preprocess import preprocess_magick
from .stages.pad import pad_square
from .stages.trace import trace_to_svg
from .stages.export import export_svg_to_png
from .stages.icon import split_ico_to_pngs, rebuild_ico_from_pngs


def _choose_last_raster_dir(output_root: Path, s: Settings) -> Path:
    """
    For icon rebuild: use the last stage that definitely produced raster files.
    Priority: D export PNG -> B padded -> A preprocessed
    """
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

    # Dependencies that are needed for ICO work
    magick = None
    if s.handle_ico:
        magick = find_magick()
        if not magick:
            raise RuntimeError("ImageMagick 'magick' not found on PATH (required for ICO extract/rebuild).")

    # Expand ICO inputs into frame PNGs if requested
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
                frames = split_ico_to_pngs(magick, ico, frame_dir)
                if not frames:
                    log(f"  WARN: no frames extracted from {ico.name}\n")
                    continue

                # record mapping
                ico_map[ico.stem] = {
                    "src": ico,
                    "frames": frames,
                }
                expanded.extend(frames)
                log(f"  {ico.name}: {len(frames)} frame(s)\n")

        files = other_files + expanded

    # After ICO expansion, you might still have nothing
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

    # Rebuild ICOs if enabled
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

            # Find processed frames by stem in the chosen raster output dir
            processed_frames = []
            for fr in frames:
                candidate = src_raster_dir / (Path(fr).stem + ".png")
                if candidate.exists():
                    processed_frames.append(candidate)
                else:
                    # if pad output format is jpg, accept that too
                    candidate_j = src_raster_dir / (Path(fr).stem + ".jpg")
                    if candidate_j.exists():
                        processed_frames.append(candidate_j)

            if not processed_frames:
                log(f"  WARN: No processed frames found for {stem}.ico (skipping)\n")
                continue

            dst_ico = out_ico_dir / f"{stem}.ico"
            rebuild_ico_from_pngs(mag, processed_frames, dst_ico)
            log(f"  OK: {dst_ico.name} ({len(processed_frames)} frame(s))\n")
