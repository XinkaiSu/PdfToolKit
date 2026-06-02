# methods/ — Processing Modules

All modules depend on `config.AppConfig` for settings. Pipeline is orchestrated by `core.py`.

## Module Reference

### `sort.py` — Smart Sorting

Three-tier sort key system for filenames with numeric prefixes:

- `smart_sort_key(s, config)` — entry point; dispatches to `chinese_sort_key` or `natural_sort_key` based on `config.advanced.enable_chinese_sort`
- `chinese_sort_key(s)` — parses Chinese numerals (一、第X章、（X）) and Arabic numerals (1、第1章、（1）) into a unified `(int, list)` key; both numbering styles share the same primary key space so they interleave correctly
- `natural_sort_key(s)` — standard natural sort (`2 < 10`)
- `_cn_to_int(s)` / `_int_to_cn(n)` — Chinese ↔ integer conversion (0–99)
- `_compute_numbering_prefix(level, counters, style, separator)` — generates numbering labels for TOC (`chinese` / `arabic` / `multi_level`)

### `merge.py` — File Collection + Content Merge

- `collect_file_tree(root_dir, config, custom_order)` — recursive directory scan → `(flat_items, root_name)`. Sorts with `smart_sort_key`, then applies `custom_order` (from drag-and-drop). When `file_order` entries don't match actual filenames (stale config), falls back to smart sort entirely
- `merge_content(items, output_path, config)` — merges all PDF/image files into one A4-normalized PDF; returns `(pagination, total_pages, source_offsets)` for TOC and bookmark use

### `convert.py` — A4 Conversion + Temp Files

- `convert_pdf_to_a4(path)` / `convert_pdf_to_a4_memory(path)` — pikepdf XObject embedding, proportional scaling, auto landscape/portrait
- `image_to_pdf(path, output)` — image → A4 PDF via reportlab
- `make_temp_file()` / `cleanup_temp()` — temp file lifecycle

### `cover.py` — Cover Generation

- `generate_cover_pdf(cover_config, root_name, output_path)` — reportlab canvas, fully parameterized (title/subtitle/logo/unit/date/border)
- `generate_cover_preview(cover_config, root_name)` — returns PNG bytes via PyMuPDF rendering

### `toc.py` — Table of Contents

- `generate_toc(output_path, items, pagination, root_name, config)` — reportlab TOC with per-level fonts, dot leaders, numbering prefixes

### `pagenum.py` — Page Number Overlay

- `add_page_numbers(input_path, output_path, toc_pages, config)` — XObject overlay (no reportlab merge)
- `add_page_numbers_image_mode(input_path, output_path, toc_pages, config)` — rasterize via Poppler, draw numbers, reassemble

### `bookmark.py` — PDF Bookmarks

- `add_bookmarks_to_pdf(pdf_path, items, pagination, cover_pages, toc_pages, source_offsets, config)` — writes outline via pikepdf stack algorithm
- `extract_source_bookmarks(pdf_path, page_offset, level_offset)` — preserves source PDF bookmarks
- `build_tree_bookmarks(items, pagination, page_offset, config)` — bookmarks from folder/file tree

### `combine.py` — Combine Mode (Segment Stitching)

- `process_combine(files, config)` — full pipeline: PDF→image → background removal → FFT NCC offset → feather blend → output
- `auto_sort_segments(images)` — sorts overlapping segments by vertical position
- `stitch_on_canvas(images, offsets, config)` — composites with gradient blending

### `fonts.py` — Font Management + Text Utilities

- `register_fonts(config)` — registers all fonts from `config.font.font_map`
- `resolve_font(preferred, config)` / `get_fallback_font(config)` — font fallback chain
- `clean_text(text, config)` — strips unsupported characters via `_SPECIAL_CHAR_RE`
- `wrap_text(text, font, size, max_width)` — pixel-accurate line wrapping
