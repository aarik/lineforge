from __future__ import annotations

from pathlib import Path

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
    mode: str = "none",               # "none" | "threshold" | "quantize"
    threshold_pct: int = 45,          # used when mode == "threshold"
    quantize_levels: int = 16,        # used when mode == "quantize"
) -> Path:
    """
    Preprocess an image using ImageMagick CLI (magick).
    Always writes a PNG to dst.

    Modes:
      - none: no hard threshold or quantize
      - threshold: brightness cutoff (2-tone B/W)
      - quantize: grayscale tone reduction (levels)
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = [magick, str(src)]

    # Flatten alpha (avoid transparency artifacts downstream)
    args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]

    # Strip metadata
    args += ["-strip"]

    # Work in grayscale when requested (also recommended for quantization)
    if grayscale:
        args += ["-colorspace", "Gray"]

    if auto_level:
        args += ["-auto-level"]

    if contrast_stretch:
        args += ["-contrast-stretch", f"{cs_black}%x{cs_white}%"]

    if int(median) > 0:
        args += ["-median", str(int(median))]

    if float(blur) > 0.0:
        args += ["-blur", f"0x{float(blur)}"]

    if negate:
        args += ["-negate"]

    # Mutually exclusive "finish" mode
    mode = (mode or "none").strip().lower()

    if mode == "threshold":
        tp = max(0, min(100, int(threshold_pct)))
        args += ["-threshold", f"{tp}%"]

    elif mode == "quantize":
        # Quantize grayscale to N levels.
        # Use -dither None so it doesn't introduce speckled noise.
        # -colors N reduces to N palette entries.
        levels = int(quantize_levels)
        if levels < 2:
            levels = 2
        if levels > 256:
            levels = 256

        # Ensure gray colorspace for predictable output
        args += ["-colorspace", "Gray"]
        args += ["-dither", "None"]
        args += ["-colors", str(levels)]

    elif mode == "none":
        pass
    else:
        raise ValueError(f"Unknown preprocess mode: {mode!r}")

    # Force PNG output
    args += [f"png:{dst}"]

    run_cmd(args)
    return dst
