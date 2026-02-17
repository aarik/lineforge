# LineForge

LineForge is a plain Windows GUI for prepping monochrome / line-art datasets for ML training.

It batch-processes images to reduce intrusive artifacts (specks, halos, compression junk), standardizes them (pad/resize), optionally traces them to SVG, and optionally exports the SVGs back to PNG for consistent training inputs.

## What it does

Given an input folder (or a single image), LineForge can run this pipeline:

1) **Preprocess (ImageMagick)**
   - flattens alpha
   - optional grayscale
   - optional auto-level
   - optional contrast-stretch
   - optional median denoise
   - optional blur
   - optional invert
   - optional threshold (bilevel)

2) **Pad/Resize (Pillow)**
   - letterbox to a square canvas (ex: 512×512)
   - background: **white / black / transparent**
   - output: **JPG or PNG** (JPG recommended to avoid transparency issues)
   - JPEG quality control

3) **Trace to SVG (Potrace)**
   - threshold-to-PBM + potrace SVG
   - speck removal (turdsize)
   - optional curve smoothing
   - optional invert / cutoff adjustments

4) **Export SVG → PNG (Inkscape CLI)**
   - export at a consistent width
   - optional crop-to-drawing-area

Outputs are written into numbered folders under your chosen output directory:
- `01_preprocessed`
- `02_padded`
- `03_svg`
- `04_export_png`

## UI usage

- **Run A: Preprocess** writes to `01_preprocessed`
- **Run B: Pad** writes to `02_padded`
- **Run C: Trace** writes to `03_svg`
- **Run D: Export** writes to `04_export_png`
- **Run ALL (A→D)** runs the full pipeline in order
- **Open output folder** opens the output directory in Explorer
- **Open last log** opens the most recent run log

Logs are saved to:
- `.\logs\lineforge_YYYYMMDD_HHMMSS.log`

### Dependencies

LineForge uses:
- **Potrace** (bundled in this repo under `bin/potrace.exe`)
- **ImageMagick** (must be installed and available on PATH as `magick`)
- **Inkscape** (must be installed and available on PATH as `inkscape`)

If a dependency is missing, the UI will tell you exactly which one.


## Quick Start(Python)

pip install -r requirements.txt
python main.py


## Build (developer)

To build the release version of the app (single EXE):
powershell -ExecutionPolicy Bypass -File .\build_release.ps1

