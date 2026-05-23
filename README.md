# PdfToolKit

Scan subfolders under a root directory and merge PDFs in each subfolder into a single file with: cover page, table of contents, page numbers, and A4-normalized content. Also supports a Combine mode to intelligently stitch multiple segmented PDFs into a complete document. Full GUI with real-time parameter configuration, or run from the command line.

扫描根目录下的子文件夹，将每个子文件夹中的 PDF 合并为一个文件，包含：封面、目录、页码、A4 标准化内容。支持拼图模式将多个分段 PDF 智能拼接为完整文档。GUI 界面支持所有参数实时配置，也可命令行运行。

---

## Features / 功能特性

### Merge Mode / 合并模式

- **Cover Generation**: Pure PDF generation — no Word template needed. Supports main title, subtitle, logo, organization name, date, top-right classification text, and decorative page borders
- **封面生成**：纯 PDF 生成，无需 Word 模板，支持主标题/副标题/Logo/编制单位/日期/右上角密级文字/页面装饰线

- **Live Cover Preview**: Preview auto-refreshes when settings change in the GUI
- **封面实时预览**：GUI 中修改设置后自动刷新预览

- **Auto Table of Contents**: Multi-level folder structure automatically generates a TOC, supporting Chinese numerals, Arabic numerals, and multi-level numbering
- **自动目录**：多级文件夹结构自动生成目录，支持中文数字/阿拉伯数字/多级编号

- **Chinese Smart Sort**: Parses Chinese numeral prefixes like "一、二、第X章、（X）"
- **中文智能排序**：解析"一、二、第X章、（X）"等中文序号前缀

- **Page Number Overlay**: Fully customizable — background color, shape, border, text color, position
- **页码叠加**：支持背景色/形状/边框/颜色/位置全定制

- **A4 Normalization**: Auto landscape/portrait detection, proportional scaling and centering, no cropping
- **A4 标准化**：自动识别横纵向，等比缩放居中，无裁切

- **Image Merging**: Merge PNG/JPG/BMP/TIFF images alongside PDFs
- **图片合并**：支持将 PNG/JPG/BMP/TIFF 等图片文件一并合并

- **File List Management**: Tree view + checkbox exclusion + drag-and-drop reordering
- **文件列表管理**：树形浏览 + 复选框排除 + 拖拽排序

- **Image Convert Mode**: Compatible with PDFs containing handwritten signatures (requires Poppler)
- **图片化模式**：兼容含手写签名的 PDF（需 Poppler）

- **Two Merge Modes**: Merge per subfolder / merge entire folder as one
- **两种合并模式**：按子文件夹分别合并 / 整体合并

- **PDF Bookmarks**: Auto-generate PDF bookmarks from folder structure with multi-level nesting
- **PDF 书签**：根据文件夹结构自动生成 PDF 书签，支持多级嵌套

### Combine Mode / 拼图模式

- **Smart Stitching**: Auto-detect overlap regions and 2D offsets between adjacent PDF segments
- **智能拼接**：自动检测相邻分段 PDF 的重叠区域和 2D 偏移量

- **Background Removal**: White backgrounds are automatically made transparent for more reliable matching
- **背景去除**：白色背景自动透明化，提高匹配可靠性

- **FFT Acceleration**: FFT-based Normalized Cross-Correlation reduces offset detection from 30+ seconds to ~0.7 seconds
- **FFT 加速**：基于快速傅里叶变换的归一化互相关，偏移检测从 30+ 秒降至约 0.7 秒

- **Canvas Preview**: Visualize stitch positions, drag to adjust
- **画布预览**：可视化查看拼接位置，支持拖拽微调

- **Numeric Adjustment**: Right-side panel with X/Y pixel entry fields and ▲▼ buttons for precise positioning
- **数值微调**：右侧面板提供 X/Y 像素输入框和 ▲▼ 按钮，精确调整位置

- **Gradient Blending**: Overlapping regions are automatically feather-blended to eliminate seams
- **渐变融合**：重叠区域自动做渐变羽化融合，消除接缝

---

## Quick Start / 快速开始

### Download / 直接下载

Download `PdfToolKit.exe` from [Releases](https://github.com/XinkaiSu/PdfToolKit/releases) — double-click to run, no Python installation needed.

从 [Releases](https://github.com/XinkaiSu/PdfToolKit/releases) 下载 `PdfToolKit.exe`，双击运行，无需安装 Python。

### Run from Source / 从源码运行

```bash
# Create a virtual environment (recommended) / 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

Launch the GUI / 启动 GUI：

```bash
python main.py
```

Command-line mode (configure input/output directories in the GUI first) / 命令行模式（需先在 GUI 中设置输入/输出目录）：

```bash
python main.py --cli
```

---

## GUI Guide / GUI 说明

A home page is shown on startup, introducing the two main modes. Select "Merge" or "Combine" from the top mode bar to begin.

启动后显示首页，介绍两大功能模式。从顶部模式栏选择「合并」或「拼图」开始使用。

### Merge Mode / 合并模式

Contains 7 tabs and a bottom control area:

包含 7 个选项卡和底部控制区：

| Tab / 选项卡 | Content / 内容 |
|-----|---------|
| Paths & Advanced / 路径与高级 | Input/output directories, merge mode, image convert mode, sorting, config management / 输入/输出目录、合并模式、图片化模式、排序、配置管理 |
| Cover Settings / 封面配置 | Main title/subtitle/decorative lines/logo/organization/date/top-right text, with live preview / 主标题/副标题/装饰线/Logo/编制单位/日期/右上角文字，右侧实时预览 |
| TOC Settings / 目录设置 | Margins/line height/font size/per-level fonts/dot leaders/numbering styles / 页边距/行高/字号/各级字体/引导点/编号样式 |
| Page Number Settings / 页码设置 | Font/position/background shape/border and all other parameters / 字体/位置/背景形状/边框等全部参数 |
| Font Settings / 字体设置 | System font directory/font mapping/fallback order / 系统字体目录/字体映射/回退顺序 |
| PDF Bookmarks / PDF书签 | Bookmark toggle, font/color/style settings / 书签开关、字体/颜色/样式设置 |
| File List / 文件列表 | Tree view file browser, checkbox exclusion, drag-and-drop reordering / 树形文件浏览、复选框排除、拖拽排序 |

The bottom area contains: start/stop buttons, progress bar, and run log.

底部区域包含：开始/停止按钮、进度条、运行日志。

### Combine Mode / 拼图模式

Contains 3 tabs:

包含 3 个选项卡：

| Tab / 选项卡 | Content / 内容 |
|-----|---------|
| File List / 文件列表 | Add/remove/reorder PDF segments to stitch / 添加/删除/排序待拼接的 PDF 文件 |
| Parameters / 参数设置 | DPI, feather width, background threshold, output path, etc. / DPI、融合宽度、背景阈值、输出路径等 |
| Stitch Canvas / 拼接画布 | Preprocess → auto-layout → drag/numeric adjust → generate PDF / 预处理 → 自动排列 → 拖拽/数值微调 → 生成 PDF |

**Combine workflow / 拼图工作流程**：

1. Add segmented PDFs in "File List" (order from top to bottom) / 在「文件列表」添加分段 PDF（按从上到下顺序排列）
2. Configure DPI and output path in "Parameters" / 在「参数设置」配置 DPI 和输出路径
3. Click "Preprocess" in "Stitch Canvas" to auto-detect offsets and show preview / 在「拼接画布」点击「预处理」，自动检测偏移并显示预览
4. Fine-tune X/Y positions using the right-side numeric panel, or drag to adjust / 在右侧数值面板微调 X/Y 位置，或拖拽调整
5. Click "Start" to generate the stitched result / 点击「开始处理」生成拼接结果

### Cover Layout / 封面配置详解

Cover layout from top to bottom:

封面布局从上到下：

```
┌──────────────────────────────────┐
│ [Logo]              [CLASSIFIED] │  ← Logo top-left, optional text top-right / Logo 左上角，右上角可选文字
│                                  │
│         Main Title               │  ← Above page center, centered / 页面中心偏上，居中
│           Subtitle               │
│                                  │
│       Organization (bold)        │  ← Below page center / 页面中心下方
│       XX Institute               │
│       May 2026                   │  ← Leave empty for current month / 留空自动填入当前年月
└──────────────────────────────────┘
  Optional decorative page border / 可选页面装饰线边框
```

All element positions, font sizes, fonts, and colors are configurable in the GUI. The preview auto-refreshes on changes.

所有元素的位置、字号、字体、颜色均可在 GUI 中设置，修改后预览区自动刷新。

---

## Project Structure / 项目结构

```
main.py                  — Entry point (GUI / CLI mode switch) / 程序入口（GUI / CLI 模式切换）
version.py               — Version number definition (single source of truth) / 版本号定义（唯一来源）
config.py                — Configuration data models (dataclass + JSON persistence) / 配置数据模型（dataclass + JSON 持久化）
core.py                  — PDF processing pipeline (merge, TOC, page numbers, etc.) / PDF 处理流水线（合并、目录、页码等）
methods/
  __init__.py
  combine.py             — Combine mode: offset detection, background removal, gradient blending / 拼图模式：偏移检测、背景去除、渐变融合
  merge.py               — File structure collection + content merging / 文件结构收集 + 内容合并
  convert.py             — PDF A4 conversion + image-to-PDF + temp file management / PDF A4 转换 + 图片转 PDF + 临时文件管理
  pagenum.py             — Page number overlay / 页码叠加
  toc.py                 — Table of contents generation / 目录生成
  cover.py               — Parameterized cover generation + preview / 参数化封面生成 + 预览
  fonts.py               — Font registration and resolution / 字体注册与解析
  sort.py                — Smart sorting (Chinese numeral parsing) / 智能排序（中文数字解析）
  bookmark.py            — PDF bookmark generation / PDF 书签生成
gui/
  __init__.py
  app.py                 — Main window (mode bar, navigation, log panel, run control) / 主窗口框架（模式栏、导航、日志面板、运行控制）
  home_tab.py            — Home page: feature descriptions / 首页：功能说明
  cover_tab.py           — Cover settings panel + live preview / 封面配置面板 + 实时预览
  toc_tab.py             — TOC settings tab / 目录设置选项卡
  pagenum_tab.py         — Page number settings tab / 页码设置选项卡
  font_tab.py            — Font settings tab / 字体设置选项卡
  path_tab.py            — Paths & advanced tab / 路径与高级选项卡
  filelist_tab.py        — File list (tree view + drag-and-drop) / 文件列表（树形浏览 + 拖拽排序）
  bookmark_tab.py        — PDF bookmark settings tab / PDF 书签设置选项卡
  combine_filelist_tab.py — Combine file list / 拼图文件列表
  combine_params_tab.py  — Combine parameter settings / 拼图参数设置
  combine_canvas_tab.py  — Stitch canvas (preview + numeric adjustment) / 拼接画布（预览 + 数值微调）
build.spec               — PyInstaller build config / PyInstaller 打包配置
requirements.txt         — Python dependencies / Python 依赖
```

---

## Configuration Persistence / 配置持久化

GUI settings are automatically saved to `~/.pdftoolkit/config.json` and loaded on next startup. You can also manually save/load/reset configs in the "Paths & Advanced" tab.

GUI 中的配置自动保存到 `~/.pdftoolkit/config.json`，下次启动自动加载。也可在"路径与高级"选项卡中手动保存/加载/重置配置。

## Image Convert Mode / 图片化模式

When enabled, all PDF pages are rasterized and then rebuilt, making the tool compatible with PDFs containing handwritten signatures. This mode requires [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) to be installed separately, with its path configured in "Paths & Advanced".

启用图片化模式后，所有 PDF 页面先光栅化再重建，兼容含手写签名的 PDF。此模式需要额外安装 [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)，并在"路径与高级"中设置 Poppler 路径。

## Building an EXE / 打包为 EXE

```bash
pip install pyinstaller
pyinstaller build.spec --clean
```

The resulting single-file EXE is located at `dist/PdfToolKit.exe`.

生成的单文件 EXE 位于 `dist/PdfToolKit.exe`。

## Dependencies / 依赖说明

| Package / 包 | Purpose / 用途 |
|---------|------|
| pikepdf | PDF read/write, XObject embedding, A4 conversion / PDF 读写、XObject 嵌入、A4 转换 |
| reportlab | Cover generation, TOC generation, page number overlay / 封面生成、目录生成、页码叠加 |
| Pillow | Image processing (image convert mode, combine mode) / 图片处理（图片化模式、拼图模式） |
| numpy | Combine mode offset detection (NCC matching) / 拼图模式偏移检测（NCC 匹配） |
| customtkinter | GUI framework / GUI 框架 |
| PyMuPDF (fitz) | PDF rendering (cover preview, combine mode) / PDF 渲染（封面预览、拼图模式） |
| pdf2image | Image convert mode (optional, requires Poppler) / 图片化模式（可选，需 Poppler） |

## License

MIT
