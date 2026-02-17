from dataclasses import dataclass

@dataclass
class Settings:
    # Input behavior
    input_recursive: bool = False

    # A) preprocess
    do_preprocess: bool = True
    grayscale: bool = True
    auto_level: bool = True
    contrast_stretch: bool = True
    cs_black: float = 0.5
    cs_white: float = 0.5
    median: int = 1
    blur: float = 0.0
    negate: bool = False
    do_threshold: bool = False
    threshold_pct: int = 45

    # B) pad
    do_pad: bool = True
    pad_size: int = 512
    pad_bg: str = "white"          # white / black / transparent (transparent treated as white unless you add alpha path)
    pad_out_fmt: str = "jpg"       # jpg or png
    jpeg_quality: int = 95

    # C) trace
    do_trace: bool = True
    trace_cutoff_pct: int = 45
    trace_invert: bool = False
    potrace_turdsize: int = 8
    potrace_smooth: bool = True

    # D) export
    do_export: bool = True
    export_width: int = 512
    export_area_drawing: bool = True
