# PDF Batch Merge Tool

Scan subfolders under a root directory and merge PDFs in each subfolder into a single file with: cover page, table of contents, page numbers, and A4-normalized content. Also supports a Combine mode to intelligently stitch multiple segmented PDFs into a complete document. Full GUI with real-time parameter configuration, or run from the command line.

## Features

### Merge Mode

- **Cover Generation**: Pure PDF generation — no Word template needed. Supports main title, subtitle, logo, organization name, date, top-right classification text, and decorative page borders
- **Live Cover Preview**: Preview auto-refreshes when settings change in the GUI
- **Auto Table of Contents**: Multi-level folder structure automatically generates a TOC, supporting Chinese numerals, Arabic numerals, and multi-level numbering
- **Chinese Smart Sort**: Parses Chinese numeral prefixes like "一、二、第X章、（X）"
- **Page Number Overlay**: Fully customizable — background color, shape, border, text color, position
- **A4 Normalization**: Auto landscape/portrait detection, proportional scaling and centering, no cropping
- **Image Merging**: Merge PNG/JPG/BMP/TIFF images alongside PDFs
- **File List Management**: Tree view + checkbox exclusion + drag-and-drop reordering
- **Image Convert Mode**: Compatible with PDFs containing handwritten signatures (requires Poppler)
- **Two Merge Modes**: Merge per subfolder / merge entire folder as one
- **PDF Bookmarks**: Auto-generate PDF bookmarks from folder structure with multi-level nesting

### Combine Mode

- **Smart Stitching**: Auto-detect overlap regions and 2D offsets between adjacent PDF segments
- **Background Removal**: White backgrounds are automatically made transparent for more reliable matching
- **FFT Acceleration**: FFT-based Normalized Cross-Correlation reduces offset detection from 30+ seconds to ~0.7 seconds
- **Canvas Preview**: Visualize stitch positions, drag to adjust
- **Numeric Adjustment**: Right-side panel with X/Y pixel entry fields and ▲▼ buttons for precise positioning
- **Gradient Blending**: Overlapping regions are automatically feather-blended to eliminate seams

## Quick Start

### Download

Download `PdfToolKit.exe` from [Releases](https://github.com/XinkaiSu/PdfToolKit/releases) — double-click to run, no Python installation needed.

### Run from Source

```bash
# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Launch the GUI:

```bash
python main.py
```

Command-line mode (configure input/output directories in the GUI first):

```bash
python main.py --cli
```

## GUI Guide

A home page is shown on startup, introducing the two main modes. Select "Merge" or "Combine" from the top mode bar to begin.

### Merge Mode

Contains 7 tabs and a bottom control area:

| Tab | Content |
|-----|---------|
| Paths & Advanced | Input/output directories, merge mode, image convert mode, sorting, config management |
| Cover Settings | Main title/subtitle/decorative lines/logo/organization/date/top-right text, with live preview on the right |
| TOC Settings | Margins/line height/font size/per-level fonts/dot leaders/numbering styles |
| Page Number Settings | Font/position/background shape/border and all other parameters |
| Font Settings | System font directory/font mapping/fallback order |
| PDF Bookmarks | Bookmark toggle, font/color/style settings |
| File List | Tree view file browser, checkbox exclusion, drag-and-drop reordering |

The bottom area contains: start/stop buttons, progress bar, and run log.

### Combine Mode

Contains 3 tabs:

| Tab | Content |
|-----|---------|
| File List | Add/remove/reorder PDF segments to stitch |
| Parameters | DPI, feather width, background threshold, output path, etc. |
| Stitch Canvas | Preprocess → auto-layout → drag/numeric adjust → generate PDF |

**Combine workflow**:
1. Add segmented PDFs in "File List" (order from top to bottom)
2. Configure DPI and output path in "Parameters"
3. Click "Preprocess" in "Stitch Canvas" to auto-detect offsets and show preview
4. Fine-tune X/Y positions using the right-side numeric panel, or drag to adjust
5. Click "Start" to generate the stitched result

### Cover Layout

Cover layout from top to bottom:

```
┌──────────────────────────────────┐
│ [Logo]              [CLASSIFIED] │  ← Logo top-left, optional text top-right
│                                  │
│         Main Title               │  ← Above page center, centered
│           Subtitle               │
│                                  │
│       Organization (bold)        │  ← Below page center
│       XX Institute               │
│       May 2026                   │  ← Leave empty for current month
└──────────────────────────────────┘
  Optional decorative page border
```

All element positions, font sizes, fonts, and colors are configurable in the GUI. The preview auto-refreshes on changes.

## Project Structure

```
main.py                  — Entry point (GUI / CLI mode switch)
version.py               — Version number definition (single source of truth)
config.py                — Configuration data models (dataclass + JSON persistence)
core.py                  — PDF processing pipeline (merge, TOC, page numbers, etc.)
methods/
  __init__.py
  combine.py             — Combine mode: offset detection, background removal, gradient blending
  merge.py               — File structure collection + content merging
  convert.py             — PDF A4 conversion + image-to-PDF + temp file management
  pagenum.py             — Page number overlay
  toc.py                 — Table of contents generation
  cover.py               — Parameterized cover generation + preview
  fonts.py               — Font registration and resolution
  sort.py                — Smart sorting (Chinese numeral parsing)
  bookmark.py            — PDF bookmark generation
gui/
  __init__.py
  app.py                 — Main window (mode bar, navigation, log panel, run control)
  home_tab.py            — Home page: feature descriptions
  cover_tab.py           — Cover settings panel + live preview
  toc_tab.py             — TOC settings tab
  pagenum_tab.py         — Page number settings tab
  font_tab.py            — Font settings tab
  path_tab.py            — Paths & advanced tab
  filelist_tab.py        — File list (tree view + drag-and-drop)
  bookmark_tab.py        — PDF bookmark settings tab
  combine_filelist_tab.py — Combine file list
  combine_params_tab.py  — Combine parameter settings
  combine_canvas_tab.py  — Stitch canvas (preview + numeric adjustment)
build.spec               — PyInstaller build config
requirements.txt         — Python dependencies
```

## Configuration Persistence

GUI settings are automatically saved to `~/.pdftoolkit/config.json` and loaded on next startup. You can also manually save/load/reset configs in the "Paths & Advanced" tab.

## Image Convert Mode

When enabled, all PDF pages are rasterized and then rebuilt, making the tool compatible with PDFs containing handwritten signatures. This mode requires [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) to be installed separately, with its path configured in "Paths & Advanced".

## Building an EXE

```bash
pip install pyinstaller
pyinstaller build.spec --clean
```

The resulting single-file EXE is located at `dist/PdfToolKit.exe`.

## Dependencies

| Package | Purpose |
|---------|---------|
| pikepdf | PDF read/write, XObject embedding, A4 conversion |
| reportlab | Cover generation, TOC generation, page number overlay |
| Pillow | Image processing (image convert mode, combine mode) |
| numpy | Combine mode offset detection (NCC matching) |
| customtkinter | GUI framework |
| PyMuPDF (fitz) | PDF rendering (cover preview, combine mode) |
| pdf2image | Image convert mode (optional, requires Poppler) |

## License

MIT
