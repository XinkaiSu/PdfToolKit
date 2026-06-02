# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF batch merge tool for Chinese government/academic documents. Two modes: **Merge** (scan subfolders, produce one merged PDF per subfolder with cover/TOC/page numbers/A4-normalized content) and **Combine** (smart-stitch overlapping segmented PDFs via FFT-based offset detection). GUI built with customtkinter.

## Running

```bash
.venv/Scripts/activate          # Windows venv
python main.py                  # GUI mode
python main.py --cli            # CLI mode (requires GUI-configured paths)
pip install -r requirements.txt # Install deps
```

No test suite. No build step required for development.

## Building an EXE

```bash
pip install pyinstaller
pyinstaller build.spec --clean
# Output: dist/PdfToolKit.exe
```

`build.spec` reads version from `version.py` (single source of truth) and auto-generates a Windows version-info resource. When adding new modules, add them to `hiddenimports` in `build.spec`.

## Architecture

### Two modes, one app

- **Merge mode** (`core.py`): 7-tab GUI. Pipeline per folder: scan → cover → merge content → TOC → page numbers → prepend cover → bookmarks → output. `process_folder()` handles per-subfolder; `process_single_merge()` handles whole-directory merge.
- **Combine mode** (`methods/combine.py`): 3-tab GUI. Pipeline: PDF→image → background removal → FFT NCC offset detection → feather blending → output PDF. `process_combine()` is the entry point.

### Config layer

`config.py` dataclasses (`AppConfig` + sub-configs), persisted to `~/.pdftoolkit/config.json`. Key sections:

- `CoverConfig`, `TocConfig`, `PageNumConfig`, `FontConfig`, `PathConfig`, `AdvancedConfig`, `NumberingConfig`, `BookmarkConfig`, `CombineConfig`

GUI tabs hold direct references to config dataclasses; edits write through immediately. `_collect_config()` calls each tab's `apply_to_config()` before processing.

### Processing modules (`methods/` package)

| Module | Role |
|---|---|
| `fonts.py` | Font registration (reportlab), fallback resolution, text wrapping |
| `sort.py` | `smart_sort_key` — Chinese/Arabic numeral prefix parsing (一/1、第X章、（X）), natural sort fallback |
| `convert.py` | A4 XObject embedding (`_page_to_xobject`/`_embed_xobject`), image→PDF, temp file management |
| `merge.py` | File tree collection + content merging; `_apply_custom_order` falls back to smart sort when file_order is stale |
| `cover.py` | Parameterized cover generation + preview (reportlab canvas, no DOCX) |
| `toc.py` | Table of contents generation |
| `pagenum.py` | Page number overlay as separate XObject layer (not reportlab merge) |
| `bookmark.py` | PDF bookmark generation from folder structure |
| `combine.py` | Combine mode: offset detection, background removal, gradient blending |

### GUI (`gui/` package)

`PdfToolKitApp` (in `gui/app.py`) is the main window. Top mode bar switches between Home / Merge / Combine. Left nav + right content area + bottom control/log panel.

Merge panels: PathTab, CoverTab (live preview), TocTab, PageNumTab, FontTab, BookmarkTab, FileListTab (tree + drag-and-drop).
Combine panels: CombineFileListTab, CombineParamsTab, CombineCanvasTab (preview + numeric XY adjustment).

All panels are pre-created at init and shown/hidden via `pack`/`pack_forget`.

## Key Technical Details

- A4 conversion uses pikepdf XObject embedding — no cropping, proportional scaling with auto landscape/portrait detection
- Page numbers are overlaid as a separate XObject layer on each page (not merged via reportlab)
- Cover generation: reportlab canvas rendering, fully parameterized (no DOCX template dependency)
- Combine offset detection uses FFT-based Normalized Cross-Correlation (numpy) — ~0.7s vs 30+s brute-force
- Smart sort (`sort.py`): `chinese_sort_key` parses both Chinese numerals (一、第X章) and Arabic numerals (1、第1章) into a unified numeric primary key, so mixed naming sorts correctly
- `file_order` (drag-and-drop custom ordering) is stored in `AdvancedConfig`; when entries become stale (file renamed/added/deleted), `_apply_custom_order` falls back to smart sort instead of appending unmatched files at the end
- Image convert mode (`enable_image_convert=True`) rasterizes all pages via Poppler; requires separate Poppler install on Windows
- `core.py` creates temp PDFs alongside the script (`_cover_tmp.pdf`, etc.) and cleans up in `finally`
- Processing runs in a daemon thread; `stop_event` (threading.Event) enables cancellation between pipeline steps
- Log output from worker threads is redirected via a `QueueWriter` → `log_queue` → UI poll loop

## Dependencies

pikepdf (PDF read/write, XObject), reportlab (cover, TOC, page numbers), Pillow (image processing), numpy (combine NCC), customtkinter (GUI), PyMuPDF/fitz (PDF rendering for previews and combine mode), pdf2image (optional, image convert mode only).
