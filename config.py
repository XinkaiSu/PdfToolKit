# =============================================================================
#  config.py — 配置数据模型
#  所有配置项的 dataclass 定义 + JSON 持久化
# =============================================================================

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, Tuple

from reportlab.lib.units import inch, mm


# =============================================================================
#  封面配置
# =============================================================================

@dataclass
class CoverConfig:
    # ── 主标题 ──
    main_title_font: str = "FZXiaoBiaoSong-B05S"
    main_title_size: int = 36
    main_title_y_ratio: float = 0.68       # 垂直位置（页面高度比例，0=底 1=顶）
    main_title_use_folder: bool = True     # True=使用文件夹名，False=使用 title_text

    # ── 副标题 ──
    subtitle: str = ""
    subtitle_font: str = "SimHei"
    subtitle_size: int = 24
    subtitle_use_folder: bool = False      # True=使用文件夹名，False=使用subtitle文本

    # ── 页面装饰线 ──
    show_border: bool = True
    border_margin_mm: float = 20.0         # 装饰线距页面边缘（mm）
    border_color: list = field(default_factory=lambda: [0, 0, 0])
    border_width: float = 1.5              # 磅

    # ── Logo ──
    logo_path: str = ""
    logo_width: float = 80                 # 磅
    logo_height: float = 80                # 磅
    logo_margin_left_mm: float = 30.0
    logo_margin_top_mm: float = 30.0

    # ── 编制单位 ──
    unit_label: str = "编制单位"
    unit_name: str = ""
    unit_font: str = "SimSun"
    unit_label_size: int = 16
    unit_name_size: int = 14
    unit_y_ratio: float = 0.38

    # ── 日期 ──
    cover_date: str = ""                   # 留空则自动使用当前年月
    date_font: str = "SimSun"
    date_size: int = 14
    date_y_ratio: float = 0.20             # 垂直位置（页面高度比例，0=底 1=顶）

    # ── 右上角文字 ──
    corner_text: str = ""
    corner_text_font: str = "SimHei"
    corner_text_size: int = 14
    corner_text_color: list = field(default_factory=lambda: [1, 0, 0])
    corner_text_margin_right_mm: float = 30.0
    corner_text_margin_top_mm: float = 30.0

    # 运行时填充（非持久化）
    title_text: str = ""                   # 实际运行时自动填入文件夹名

    def get_border_margin(self) -> float:
        return self.border_margin_mm * mm

    def get_logo_margin_left(self) -> float:
        return self.logo_margin_left_mm * mm

    def get_logo_margin_top(self) -> float:
        return self.logo_margin_top_mm * mm

    def get_corner_margin_right(self) -> float:
        return self.corner_text_margin_right_mm * mm

    def get_corner_margin_top(self) -> float:
        return self.corner_text_margin_top_mm * mm

    def get_border_color_tuple(self) -> tuple:
        return tuple(self.border_color)

    def get_corner_color_tuple(self) -> tuple:
        return tuple(self.corner_text_color)


# =============================================================================
#  目录配置
# =============================================================================

@dataclass
class TocConfig:
    margin_left_inch: float = 1.2
    margin_right_inch: float = 1.0
    margin_top_inch: float = 1.2
    margin_bottom_inch: float = 1.0

    line_gap: int = 28                     # 行高（磅）
    font_size: int = 16                    # 字号（磅）
    indent_per_level: int = 32             # 每级缩进（磅）

    font_level1: str = "SimHei"
    font_level2: str = "SimKai"
    font_level3: str = "SimSun"
    font_deeper: str = "SimFang"
    font_file: str = "SimFang"
    font_title: str = "SimHei"

    dot_char: str = "."

    def get_margin_left(self) -> float:
        return self.margin_left_inch * inch

    def get_margin_right(self) -> float:
        return self.margin_right_inch * inch

    def get_margin_top(self) -> float:
        return self.margin_top_inch * inch

    def get_margin_bottom(self) -> float:
        return self.margin_bottom_inch * inch


# =============================================================================
#  页码配置
# =============================================================================

@dataclass
class PageNumConfig:
    enabled: bool = True

    font: str = "SimHei"
    size: int = 12
    margin_bottom_mm: float = 10.0

    align: str = "center"                  # center / left / right
    side_offset_inch: float = 1.0          # 非居中时距页面边缘

    text_color: list = field(default_factory=lambda: [0, 0, 0])

    # 背景
    bg_color: Optional[list] = field(default_factory=lambda: [1, 1, 1])
    bg_shape: str = "rect"                 # rect / roundrect / ellipse
    bg_width: float = 40
    bg_height_offset: float = 4            # bg_height = size + offset
    bg_radius: float = 4                   # 圆角矩形

    # 边框
    border: bool = False
    border_color: list = field(default_factory=lambda: [0, 0, 0])
    border_width: float = 0.5
    border_style: str = "solid"            # solid / dashed / dotted
    border_dash_on: float = 4
    border_dash_off: float = 3

    def get_margin_bottom(self) -> float:
        return self.margin_bottom_mm * mm

    def get_side_offset(self) -> float:
        return self.side_offset_inch * inch

    def get_bg_height(self) -> float:
        return self.size + self.bg_height_offset

    def get_text_color_tuple(self) -> tuple:
        return tuple(self.text_color)

    def get_bg_color_tuple(self) -> Optional[tuple]:
        if self.bg_color is None:
            return None
        return tuple(self.bg_color)

    def get_border_color_tuple(self) -> tuple:
        return tuple(self.border_color)


# =============================================================================
#  字体配置
# =============================================================================

@dataclass
class FontConfig:
    font_dir: str = r"C:\Windows\Fonts"

    font_map: dict = field(default_factory=lambda: {
        "SimHei":               "simhei.ttf",
        "SimSun":               "simsun.ttc",
        "SimKai":               "simkai.ttf",
        "SimFang":              "simfang.ttf",
        "MicrosoftYaHei":       "msyh.ttc",
        "FZXiaoBiaoSong-B05S":  "FZXBSJW.ttf",
    })

    # 粗体字体文件映射（注册名 → 粗体 ttf/ttc 文件名）
    # 若注册名在此 dict 中且文件存在，则注册一个同名「+Bold」字体可供使用
    bold_font_map: dict = field(default_factory=lambda: {
        "SimHei":               "",
        "SimSun":               "",
        "SimKai":               "",
        "SimFang":              "",
        "MicrosoftYaHei":       "msyhbd.ttc",
        "FZXiaoBiaoSong-B05S":  "",
    })

    fallback_order: list = field(default_factory=lambda: [
        "MicrosoftYaHei", "SimHei", "SimSun"
    ])


# =============================================================================
#  路径配置
# =============================================================================

@dataclass
class PathConfig:
    input_root: str = ""
    output_root: str = ""


# =============================================================================
#  高级配置
# =============================================================================

@dataclass
class AdvancedConfig:
    # 图片化模式
    enable_image_convert: bool = False
    poppler_path: str = r"D:\Software\Poppler\Library\bin"
    image_dpi: int = 300

    # 其他
    remove_special_chars: bool = True
    enable_chinese_sort: bool = True
    remove_blank_pages: bool = False

    # 图片合并
    include_images: bool = False
    image_extensions: list = field(default_factory=lambda: [
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif"
    ])

    # 合并模式: "per_subfolder" / "single"
    merge_mode: str = "per_subfolder"

    # 自定义文件排序: {目录路径: [子项名1, 子项名2, ...]}
    file_order: dict = field(default_factory=dict)

    # 排除的文件路径列表
    excluded_files: list = field(default_factory=list)


# =============================================================================
#  编号配置
# =============================================================================

@dataclass
class NumberingConfig:
    enabled: bool = False
    # 删除原文件/文件夹名开头的原有编号（中文/阿拉伯/多级）
    remove_original: bool = False
    # 每级编号样式: "none" / "chinese" / "arabic" / "multi_level"
    level1_style: str = "none"
    level2_style: str = "none"
    level3_style: str = "none"
    level_deeper_style: str = "none"
    # 编号与名称的分隔符
    separator: str = "、"


# =============================================================================
#  书签配置
# =============================================================================

@dataclass
class BookmarkConfig:
    enabled: bool = True
    preserve_source: bool = False       # 保留源PDF书签
    folder_as_bookmark: bool = True     # 文件夹名作为书签
    filename_as_bookmark: bool = True   # 文件名作为书签
    max_folder_depth: int = 10          # 最大文件夹嵌套深度
    folder_open: bool = True            # 文件夹书签默认展开
    file_open: bool = False             # 文件书签默认展开


# =============================================================================
#  拼图配置
# =============================================================================

@dataclass
class CombineConfig:
    dpi: int = 200
    overlap: Optional[float] = None      # 手动重叠比例 0~1，None=自动检测
    feather: int = 40                    # 羽化像素数
    order: str = "auto"                  # "auto" / "manual"
    no_auto: bool = False                # 跳过重叠检测直接拼接
    output_path: str = ""                # 输出PDF路径
    input_files: list = field(default_factory=list)  # 输入文件路径列表
    bg_threshold: int = 240              # 白色背景阈值，≥此值的像素视为背景
    bg_color: list = field(default_factory=lambda: [255, 255, 255])  # 画布背景色 RGB
    crop_border_mm: float = 0.0          # 边框裁切毫米数
    crop_whitespace: bool = True         # 自动裁切周边空白区域


# =============================================================================
#  总配置
# =============================================================================

@dataclass
class AppConfig:
    cover: CoverConfig = field(default_factory=CoverConfig)
    toc: TocConfig = field(default_factory=TocConfig)
    page_num: PageNumConfig = field(default_factory=PageNumConfig)
    font: FontConfig = field(default_factory=FontConfig)
    path: PathConfig = field(default_factory=PathConfig)
    advanced: AdvancedConfig = field(default_factory=AdvancedConfig)
    numbering: NumberingConfig = field(default_factory=NumberingConfig)
    bookmark: BookmarkConfig = field(default_factory=BookmarkConfig)
    combine: CombineConfig = field(default_factory=CombineConfig)

    # ── JSON 持久化 ──

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AppConfig":
        data = json.loads(json_str)
        return cls(
            cover=CoverConfig(**data.get("cover", {})),
            toc=TocConfig(**data.get("toc", {})),
            page_num=PageNumConfig(**data.get("page_num", {})),
            font=FontConfig(**data.get("font", {})),
            path=PathConfig(**data.get("path", {})),
            advanced=AdvancedConfig(**data.get("advanced", {})),
            numbering=NumberingConfig(**data.get("numbering", {})),
            bookmark=BookmarkConfig(**data.get("bookmark", {})),
            combine=CombineConfig(**data.get("combine", {})),
        )

    # ── 文件持久化 ──

    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pdftoolkit")
    CONFIG_FILE = "config.json"

    def save(self):
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        path = os.path.join(self.CONFIG_DIR, self.CONFIG_FILE)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())

    @classmethod
    def load(cls) -> "AppConfig":
        path = os.path.join(cls.CONFIG_DIR, cls.CONFIG_FILE)
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                return cls.from_json(f.read())
        except Exception:
            return cls()

    @classmethod
    def get_defaults(cls) -> "AppConfig":
        return cls()
