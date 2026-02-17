from __future__ import annotations

from pathlib import Path
from typing import List

from ..utils import run_cmd


def split_ico_to_pngs(magick: str, ico_path: Path, out_dir: Path) -> List[Path]:
    """
    Extract all embedded icon frames from .ico into PNG files using ImageMagick.

    Produces: out_dir/<stem>_frame_000.png, etc.
    """
    ico_path = Path(ico_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not ico_path.exists():
        raise FileNotFoundError(f"ICO not found: {ico_path}")

    # ImageMagick writes one file per frame using a numbered pattern.
    pattern = out_dir / f"{ico_path.stem}_frame_%03d.png"

    args = [
        magick,
        str(ico_path),
        "-alpha", "on",
        "-strip",
        str(pattern),
    ]
    run_cmd(args)

    frames = sorted(out_dir.glob(f"{ico_path.stem}_frame_*.png"))
    return frames


def rebuild_ico_from_pngs(magick: str, png_frames: List[Path], dst_ico: Path) -> Path:
    """
    Rebuild an .ico from multiple PNG frames using ImageMagick.

    NOTE: Best results when frames are square and common icon sizes (16, 24, 32, 48, 64, 128, 256).
    """
    dst_ico = Path(dst_ico)
    dst_ico.parent.mkdir(parents=True, exist_ok=True)

    if not png_frames:
        raise RuntimeError("No PNG frames supplied to rebuild ICO.")

    args = [magick] + [str(p) for p in png_frames] + ["-colors", "256", str(dst_ico)]
    run_cmd(args)
    return dst_ico
