from __future__ import annotations

from pathlib import Path

from ..utils import run_cmd


def export_svg_to_png(
    inkscape: str,
    svg: Path,
    dst: Path,
    width: int = 512,
    area_drawing: bool = True,
) -> Path:
    """Export an SVG to a PNG using Inkscape CLI."""
    svg = Path(svg)
    dst = Path(dst)

    if not svg.exists():
        raise FileNotFoundError(f"SVG not found: {svg}")

    dst.parent.mkdir(parents=True, exist_ok=True)

    w = max(1, int(width))

    args = [
        inkscape,
        str(svg),
        "--export-type=png",
        f"--export-filename={dst}",
        f"--export-width={w}",
    ]
    if area_drawing:
        args.append("--export-area-drawing")

    run_cmd(args)
    return dst
