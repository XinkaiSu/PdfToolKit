# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PDF batch merge tool for Chinese government/academic documents. Scans a root directory, processes each subfolder into a separate merged PDF with: cover page (parameterized via reportlab), table of contents, page numbers, and A4-normalized content. GUI built with customtkinter.

## Running

```bash
# Activate venv first
.venv/Scripts/activate

# Run GUI mode
python main.py

# Run CLI mode
python main.py --cli

# Install dependencies
pip install -r requirements.txt
```

No test suite exists. No build step required.

## Project Structure

```
main.py                  — 程序入口（GUI / CLI 模式切换）
config.py                — 配置数据模型（dataclass + JSON 持久化）
core.py                  — PDF 处理核心（合并、目录、页码、A4 转换等）
cover.py                 — 参数化封面生成 + 预览
gui/
  __init__.py
  app.py                 — 主窗口框架（选项卡容器、日志面板、运行控制）
  cover_tab.py           — 封面配置面板 + 实时预览
  toc_tab.py             — 目录设置选项卡
  pagenum_tab.py         — 页码设置选项卡
  font_tab.py            — 字体设置选项卡
  path_tab.py            — 路径与高级选项卡
  filelist_tab.py        — 文件列表（树形浏览 + 拖拽排序）
```

## Architecture

Configuration is managed via `config.py` dataclasses (`AppConfig` and sub-configs), persisted to `~/.pdftoolkit/config.json`. Key config sections:

- **CoverConfig**: fonts, layout positions, border, logo, unit info, date
- **TocConfig**: margins, fonts per hierarchy level, indent width, numbering
- **PageNumConfig**: position, background shape, border style
- **FontConfig**: font directory, font map (name→filename), fallback order
- **PathConfig**: input/output directories
- **AdvancedConfig**: image convert mode, Chinese sort, merge mode, file ordering

Processing pipeline (in `core.process_folder`): scan → generate cover → merge content PDFs → generate TOC → add page numbers → prepend cover → output.

## Key Technical Details

- A4 conversion uses pikepdf XObject embedding (`_page_to_xobject` / `_embed_xobject`) — no cropping, proportional scaling with auto landscape/portrait detection
- Page numbers are overlaid as a separate XObject layer on each page (not merged via reportlab)
- Cover generation: reportlab canvas rendering, fully parameterized (no DOCX template dependency)
- Chinese sort order: `smart_sort_key` parses Chinese numeral prefixes (一、二、第X章, （X）) before falling back to natural sort
- Image convert mode (`enable_image_convert=True`) requires Poppler installed separately on Windows (`poppler_path`)
- GUI tabs each own a reference to the corresponding config dataclass; changes are written directly, then collected via `apply_to_config()` before processing
