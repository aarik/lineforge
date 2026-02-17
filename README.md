# LineForge

LineForge is a modular batch image processing pipeline for preparing raster artwork for tracing, icon refinement, and dataset cleanup.

It provides:

- Image preprocessing (ImageMagick)
- Square padding / resizing
- Raster → SVG tracing (Potrace)
- SVG → PNG export (Inkscape)
- ICO round-trip support (extract → process → rebuild)

---

## Supported Input

Formats:
- PNG
- JPG / JPEG
- WEBP
- BMP
- TIFF
- ICO (optional handling)

Input sources:
- Single file
- Folder
- Folder (recursive)

The UI displays:

`Found: X inputs`

If zero files are found, enable recursive mode when selecting a parent folder.

---

## Pipeline Stages

Each stage can be enabled or disabled independently.

### A) Preprocess
Uses ImageMagick.

Options:
- Grayscale
- Auto-level
- Contrast stretch
- Median filter
- Blur
- Negate
- Threshold (slider)

Output:
```
output/01_preprocessed
```

---

### B) Pad
- Square resize
- Background: white / black / transparent
- Output format: PNG or JPG
- JPEG quality control

Output:
```
output/02_padded
```

---

### C) Trace → SVG
Uses Potrace.

Options:
- Threshold cutoff
- Invert before threshold
- Turdsize
- Smooth toggle  
  (Smoothing is default; disabling applies `--flat`.)

Output:
```
output/03_svg
```

---

### D) Export → PNG
Uses Inkscape.

Options:
- Export width
- Area: drawing

Output:
```
output/04_export_png
```

---

## ICO Processing (Optional)

When enabled:

1. `.ico` files are extracted into PNG frames.
2. Frames are processed through selected stages.
3. Processed frames are rebuilt into a new `.ico`.

Final icons:
```
output/05_ico
```

Temporary extracted frames:
```
output/_ico_frames
```

Recommended icon workflow:
- Enable ICO handling
- Enable Preprocess + Pad
- Disable Trace (unless vectorizing)
- Use PNG output
- Export width 256

---

## Output Structure

```
output/
├── 01_preprocessed/
├── 02_padded/
├── 03_svg/
├── 04_export_png/
├── 05_ico/        (if enabled)
└── _ico_frames/   (temporary)
```

---

## Dependencies

Must be available on PATH:

- ImageMagick (`magick`)
- Potrace
- Inkscape

`potrace.exe` is bundled in release builds.
ImageMagick and Inkscape must be installed separately.

---

## Build (Windows Release)

```
git clone https://github.com/aarik/lineforge.git
cd lineforge
```
Then run

```
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

Output:
```
dist_release/LineForge.exe
```

---

## Logs

Each run creates a timestamped log file in:

```
logs/
```

The UI provides:
- Open output folder
- Open last log
- Clear log
