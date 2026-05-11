# PDF 批量合并工具

扫描根目录下的子文件夹，将每个子文件夹中的 PDF 合并为一个文件，包含：封面、目录、页码、A4 标准化内容。GUI 界面支持所有参数实时配置，也可命令行运行。

近期项目需要多个文档的合并，感谢 AI 能快速实现一个完整的软件。

## 功能特性

- **封面生成**：纯 PDF 生成，无需 Word 模板，支持主标题/副标题/Logo/编制单位/日期/右上角密级文字/页面装饰线
- **封面实时预览**：GUI 中修改设置后自动刷新预览
- **自动目录**：多级文件夹结构自动生成目录，支持中文数字/阿拉伯数字/多级编号
- **中文智能排序**：解析"一、二、第X章、（X）"等中文序号前缀
- **页码叠加**：支持背景色/形状/边框/颜色/位置全定制
- **A4 标准化**：自动识别横纵向，等比缩放居中，无裁切
- **图片合并**：支持将 PNG/JPG/BMP/TIFF 等图片文件一并合并
- **文件列表管理**：树形浏览 + 复选框排除 + 拖拽排序
- **图片化模式**：兼容含手写签名的 PDF（需 Poppler）
- **两种合并模式**：按子文件夹分别合并 / 整体合并

## 快速开始

### 直接下载

从 [Releases](https://github.com/XinkaiSu/PdfToolKit/releases) 下载 `PdfToolKit.exe`，双击运行，无需安装 Python。

### 从源码运行

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

启动 GUI：

```bash
python main.py
```

命令行模式（需先在 GUI 中设置输入/输出目录）：

```bash
python main.py --cli
```

## GUI 说明

界面包含 6 个选项卡和底部控制区：

| 选项卡 | 内容 |
|--------|------|
| 路径与高级 | 输入/输出目录、合并模式、图片化模式、排序、配置管理 |
| 封面配置 | 主标题/副标题/装饰线/Logo/编制单位/日期/右上角文字，右侧实时预览 |
| 目录设置 | 页边距/行高/字号/各级字体/引导点/编号样式 |
| 页码设置 | 字体/位置/背景形状/边框等全部参数 |
| 字体设置 | 系统字体目录/字体映射/回退顺序 |
| 文件列表 | 树形文件浏览、复选框排除、拖拽排序 |

底部区域包含：开始/停止按钮、进度条、运行日志。

### 封面配置详解

封面布局从上到下：

```
┌──────────────────────────────────┐
│ [Logo]                [核心商密] │  ← Logo 左上角，右上角可选文字
│                                  │
│         主标题（成果名称）       │  ← 页面中心偏上，居中
│           副标题                 │
│                                  │
│       编制单位（加粗）           │  ← 页面中心下方
│       XX研究院                   │
│       2026年5月                  │  ← 留空自动填入当前年月
└──────────────────────────────────┘
  可选页面装饰线边框
```

所有元素的位置、字号、字体、颜色均可在 GUI 中设置，修改后预览区自动刷新。

## 项目结构

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
build.spec               — PyInstaller 打包配置
requirements.txt         — Python 依赖
```

## 配置持久化

GUI 中的配置自动保存到 `~/.pdftoolkit/config.json`，下次启动自动加载。也可在"路径与高级"选项卡中手动保存/加载/重置配置。

## 图片化模式

启用图片化模式后，所有 PDF 页面先光栅化再重建，兼容含手写签名的 PDF。此模式需要额外安装 [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)，并在"路径与高级"中设置 Poppler 路径。

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller build.spec --clean
```

生成的单文件 EXE 位于 `dist/PdfToolKit.exe`。

## 依赖说明

| 包 | 用途 |
|----|------|
| pikepdf | PDF 读写、XObject 嵌入、A4 转换 |
| reportlab | 封面生成、目录生成、页码叠加 |
| Pillow | 图片处理（图片化模式） |
| customtkinter | GUI 框架 |
| PyMuPDF (fitz) | 封面预览渲染 |
| pdf2image | 图片化模式（可选，需 Poppler） |

## License

MIT
