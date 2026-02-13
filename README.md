# LineForge

LineForge is a plain Windows GUI for prepping monochrome / line-art datasets for ML training.

It batch-processes images to reduce intrusive artifacts (specks, halos, compression junk), standardizes them (pad/resize), optionally traces them to SVG, and optionally exports the SVGs back to PNG for consistent training inputs.

## What it does

Given an input folder (or a single image), LineForge can run this pipeline:

1) **Preprocess (ImageMagick)**
   - flatten alpha
   - optional grayscale
   - optional auto-level
   - optional contrast-stretch
   - optional median denoise
   - optional blur
   - optional invert
   - optional threshold (bilevel)

2) **Pad/Resize (Pillow)**
   - letterbox to a square canvas (ex: 512×512)
   - background: transparent / white / black

3) **Trace to SVG (Potrace)**
   - threshold-to-PBM + potrace SVG
   - speck removal (turdsize)
   - optional curve smoothing / invert / cutoff adjustments

4) **Export SVG → PNG (Inkscape CLI)**
   - export at a consistent width
   - optional crop-to-drawing-area

Outputs are written into numbered folders:
- `01_preprocessed`
- `02_padded`
- `03_svg`
- `04_png`

## Dependencies

LineForge uses:
- **Potrace** (bundled in this repo under `bin/potrace.exe`)
- **ImageMagick** (installed via winget if missing)
- **Inkscape** (installed via winget if missing)

Winget is required for the one-click dependency install feature.

## Build (developer)

From PowerShell:

```powershell
cd C:\lineforge
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
