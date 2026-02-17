from dataclasses import dataclass

@dataclass
class Settings:
    # Input behavior
    input_recursive: bool = False
    handle_ico: bool = False

    # A) preprocess
    do_preprocess: bool = True

    # Shared preprocess toggles
    grayscale: bool = True
    auto_level: bool = True
    contrast_stretch: bool = True
    cs_black: float = 0.5
    cs_white: float = 0.5
    median: int = 1
    blur: float = 0.0
    negate: bool = False

    # NEW: mutually exclusive preprocess modes
    # "none" | "threshold" | "quantize"
    preprocess_mode: str = "none"

    # Threshold mode (B/W)
    threshold_pct: int = 45

    # Quantize mode (grayscale levels)
    # Typical useful values: 4, 8, 16, 32, 64
    quantize_levels: int = 16

    # B) pad
    do_pad: bool = True
    pad_size: int = 512
    pad_bg: str = "white"
    pad_out_fmt: str = "png"
    jpeg_quality: int = 95

    # C) trace
    do_trace: bool = True
    trace_cutoff_pct: int = 45
    trace_invert: bool = False
    potrace_turdsize: int = 8
    potrace_smooth: bool = True  # uses default smoothing; "off" applies --flat

    # D) export
    do_export: bool = True
    export_width: int = 512
    export_area_drawing: bool = True
