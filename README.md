# PDF 批量合并工具

PDF 批量合并工具，并制作目录与封面。扫描根目录下的子文件夹，将每个子文件夹中的 PDF 合并为一个文件，包含：封面、目录、页码、A4 标准化内容。

近期项目需要多个文档的快速合并，感谢 AI 能快速实现一个完整的软件。

## 功能特性

- **封面生成**：纯 PDF 生成，无需 Word 模板，支持主标题/副标题/Logo/编制单位/日期/右上角密级文字/页面装饰线
- **封面实时预览**：GUI 中修改设置后自动刷新预览
- **自动目录**：多级文件夹结构自动生成目录，中文序号智能排序（一、二、第X章）
- **页码叠加**：支持背景色/形状/边框/颜色/位置全定制
- **A4 标准化**：自动识别横纵向，等比缩放居中，无裁切
- **图片化模式**：兼容含手写签名的 PDF（需 Poppler）

## 快速开始

### 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

pip install -r requirements.txt
```

### 启动 GUI

```bash
python main.py
```

### 命令行模式

```bash
python main.py --cli
```

## GUI 说明

界面包含 5 个选项卡和底部控制区：

| 选项卡 | 内容 |
|--------|------|
| 封面配置 | 主标题/副标题/装饰线/Logo/编制单位/日期/右上角文字，右侧实时预览 |
| 目录设置 | 页边距/行高/字号/各级字体/引导点 |
| 页码设置 | 字体/位置/背景/边框等全部参数 |
| 字体设置 | 系统字体目录/字体映射/回退顺序 |
| 路径与高级 | 输入输出目录/图片化模式/排序/配置管理 |

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

## 打包为 EXE

```bash
pip install pyinstaller
pyinstaller build.spec --clean
```

生成的单文件 EXE 位于 `dist/PdfToolKit.exe`。

## 项目结构

```
├── main.py            # 程序入口（GUI / CLI）
├── config.py          # 配置数据模型 + JSON 持久化
├── cover.py           # 封面生成（reportlab）+ 预览渲染
├── pdf_core.py        # PDF 处理核心（A4 转换/合并/目录/页码）
├── gui_app.py         # 主窗口框架
├── gui_cover.py       # 封面配置面板 + 实时预览
├── gui_settings.py    # 目录/页码/字体/路径设置面板
├── build.spec         # PyInstaller 打包配置
├── requirements.txt   # Python 依赖
├── pdf_merge.py       # 旧版脚本（保留兼容）
└── CLAUDE.md          # Claude Code 开发指引
```

## 配置持久化

GUI 中的配置自动保存到 `~/.pdftoolkit/config.json`，下次启动自动加载。也可在"路径与高级"选项卡中手动保存/加载/重置配置。

## 图片化模式

启用图片化模式后，所有 PDF 页面先光栅化再重建，兼容含手写签名的 PDF。此模式需要额外安装 [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)，并在"路径与高级"中设置 Poppler 路径。

## 依赖说明

| 包 | 用途 |
|----|------|
| pikepdf | PDF 读写、XObject 嵌入、A4 转换 |
| reportlab | 封面生成、目录生成、页码叠加 |
| Pillow | 图片处理（图片化模式） |
| customtkinter | GUI 框架 |
| PyMuPDF (fitz) | 封面预览渲染 |
| pdf2image | 图片化模式（可选，需 Poppler） |
