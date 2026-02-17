from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..utils import run_cmd


def preprocess_magick(
    magick: str,
    src: Path,
    dst: Path,
    grayscale: bool = True,
    auto_level: bool = True,
    contrast_stretch: bool = True,
    cs_black: float = 0.5,
    cs_white: float = 0.5,
    median: int = 1,
    blur: float = 0.0,
    negate: bool = False,
    do_threshold: bool = False,
    threshold_pct: int = 45,
) -> Path:
    """
    Preprocess an image using ImageMagick CLI (magick).

    Goal: flatten alpha + optionally normalize/clean to prep for pad/trace.
    Always writes a PNG to dst.

    Parameters map to the UI toggles described in README. :contentReference[oaicite:2]{index=2}
    """
    if not isinstance(src, Path):
        src = Path(src)
    if not isinstance(dst, Path):
        dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Build ImageMagick command
    args: list[str] = [magick, str(src)]

    # Flatten alpha against a white background (dataset-friendly default).
    # This prevents weird halos and transparency artifacts in later steps.
    args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]

    # Strip metadata profiles (optional but helps keep outputs clean/smaller).
    args += ["-strip"]

    if grayscale:
        # Robust grayscale conversion
        args += ["-colorspace", "Gray"]

    if auto_level:
        args += ["-auto-level"]

    if contrast_stretch:
        # e.g. "0.5%x0.5%" is the common "clip both ends a bit" move
        args += ["-contrast-stretch", f"{cs_black}%x{cs_white}%"]

    if median and int(median) > 0:
        args += ["-median", str(int(median))]

    if blur and float(blur) > 0.0:
        # sigma-like behavior; radius 0 lets IM choose a good radius
        args += ["-blur", f"0x{float(blur)}"]

    if negate:
        args += ["-negate"]

    if do_threshold:
        # Threshold expects percent like "45%"
        tp = int(threshold_pct)
        tp = max(0, min(100, tp))
        args += ["-threshold", f"{tp}%"]

    # Force PNG output (stable for downstream steps)
    # Using png: prefix avoids weirdness if dst has odd suffix.
    args += [f"png:{str(dst)}"]

    run_cmd(args)
    return dst
