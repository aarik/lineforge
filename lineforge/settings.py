from dataclasses import dataclass

@dataclass
class Settings:
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

    do_pad: bool = True
    pad_size: int = 512
    pad_bg: str = "white"
    pad_out_fmt: str = "jpg"
    jpeg_quality: int = 95

    do_trace: bool = True
    potrace_turdsize: int = 8
    potrace_smooth: bool = True

    do_export: bool = True
    export_width: int = 512
    export_area_drawing: bool = True
