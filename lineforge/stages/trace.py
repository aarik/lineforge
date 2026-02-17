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
    """Trace a raster image to SVG using ImageMagick -> PBM then Potrace.

    - Converts the image to a 1-bit PBM at a given threshold cutoff.
    - Optionally inverts before thresholding.
    - Runs potrace to produce an SVG.

    Args:
        magick: path to ImageMagick CLI ('magick')
        potrace: path to potrace executable
        src: source raster image
        dst: destination SVG path
        cutoff_pct: threshold cutoff percent (0..100)
        invert: invert colors before threshold
        turdsize: speck removal (potrace --turdsize)
        smooth: curve smoothing (potrace --smooth)
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

        # Build PBM (1-bit) for potrace
        args = [magick, str(src)]
        args += ["-background", "white", "-alpha", "remove", "-alpha", "off"]
        args += ["-colorspace", "Gray"]
        if invert:
            args += ["-negate"]
        args += ["-threshold", f"{cutoff}%"]
        args += [f"pbm:{pbm}"]

        run_cmd(args)

        # Potrace to SVG
        pargs = [
            potrace,
            str(pbm),
            "-s",
            "-o",
            str(dst),
            "--turdsize",
            str(int(turdsize)),
        ]
        if smooth:
            pargs.append("--smooth")
        else:
            pargs.append("--no-smooth")

        run_cmd(pargs)

    return dst
