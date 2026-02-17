from pathlib import Path
from .utils import list_images
from .deps import find_magick, find_potrace, find_inkscape
from .settings import Settings
from .stages.pad import pad_square

def run_pipeline(input_path:Path,output_root:Path,settings:Settings,log):
    files=list_images(input_path)
    if not files:
        raise RuntimeError("No images found.")

    d_pad=output_root/"02_padded"
    d_pad.mkdir(parents=True,exist_ok=True)

    for i,src in enumerate(files,1):
        log(f"[{i}/{len(files)}] {src.name}\n")
        if settings.do_pad:
            out=d_pad/src.stem
            pad_square(src,out,settings.pad_size,settings.pad_bg,settings.pad_out_fmt,settings.jpeg_quality)
            log(" padded\n")
