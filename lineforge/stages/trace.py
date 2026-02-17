from __future__ import annotations

import tempfile
from pathlib import Path

from ..utils import run_cmd


def trace_to_svg(
    magick: str,
    potrace: str,
    src: Path,
    dst: Path,
    cutoff_pct: int = 45,
    invert: bool = False,
    turdsize: int = 8,
    smooth: bool = True,
) -> Path:
    """
    Trace a raster image to SVG using ImageMagick -> PBM then Potrace.

    IMPORTANT:
    - Many potrace builds do NOT support a '--smooth' flag.
    - Smoothing/curve fitting is generally the default.
    - When smooth=False, we use '--flat' (common potrace flag) to reduce curve fitting.

    Args:
        magick: path to ImageMagick CLI ('magick')
        potrace: path to potrace executable
        src: source raster image
        dst: destination SVG path
        cutoff_pct: threshold cutoff percent (0..100)
        invert: invert colors before threshold
        turdsize: speck removal (potrace --turdsize)
        smooth: if False, pass '--flat' to reduce smoothing (no curves)
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        raise FileNotFoundError(f"Source image not found: {src}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    cutoff = max(0, min(100, int(cutoff_pct)))

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        pbm = td_path / (src.stem + ".pbm")

        # 1) Make a clean 1-bit PBM for potrace
        args = [magick, str(src)]
        args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]
        args += ["-colorspace", "Gray"]
        if invert:
            args += ["-negate"]
        args += ["-threshold", f"{cutoff}%"]
        args += [f"pbm:{pbm}"]

        run_cmd(args)

        # 2) Potrace -> SVG
        pargs = [
            potrace,
            str(pbm),
            "-s",
            "-o",
            str(dst),
            "--turdsize",
            str(int(turdsize)),
        ]

        # No '--smooth' (not standard). If user wants "less smoothing", use '--flat'.
        if not smooth:
            pargs.append("--flat")

        run_cmd(pargs)

    return dst
