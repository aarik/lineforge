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
    do_threshold: bool = False,
    threshold_pct: int = 45,
) -> Path:
    """Preprocess an image via ImageMagick CLI (magick) and write a PNG.

    Conservative defaults: flatten alpha, strip metadata, then apply UI toggles.
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    args: list[str] = [magick, str(src)]

    # Remove alpha by flattening against a white background (stable for datasets)
    args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]

    # Strip profiles/metadata
    args += ["-strip"]

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

    if do_threshold:
        tp = max(0, min(100, int(threshold_pct)))
        args += ["-threshold", f"{tp}%"]

    args += [f"png:{dst}"]

    run_cmd(args)
    return dst
