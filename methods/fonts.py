# =============================================================================
#  methods/fonts.py — 字体管理 + 文本工具
# =============================================================================

import os
import re

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

from config import AppConfig


# =============================================================================
#  字体管理
# =============================================================================

def register_fonts(config: AppConfig):
    """注册配置中所有可用字体（含粗体变体）。"""
    font_dir = config.font.font_dir
    for name, filename in config.font.font_map.items():
        path = os.path.join(font_dir, filename)
        if not os.path.exists(path):
            continue
        try:
            if filename.lower().endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(name, path, subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            print(f"[!] 字体 {name} 注册失败：{e}")

    # 注册粗体变体：注册名为 "<name>+Bold"
    bold_map = getattr(config.font, "bold_font_map", {}) or {}
    for name, bold_filename in bold_map.items():
        if not bold_filename:
            continue
        path = os.path.join(font_dir, bold_filename)
        if not os.path.exists(path):
            continue
        bold_name = bold_font_name(name)
        try:
            if bold_filename.lower().endswith(".ttc"):
                pdfmetrics.registerFont(TTFont(bold_name, path, subfontIndex=0))
            else:
                pdfmetrics.registerFont(TTFont(bold_name, path))
        except Exception as e:
            print(f"[!] 粗体字体 {bold_name} 注册失败：{e}")


def bold_font_name(name: str) -> str:
    """返回某字体对应的粗体注册名约定。"""
    return f"{name}+Bold"


def has_bold_variant(name: str) -> bool:
    """检查指定字体是否已注册粗体变体。"""
    return bold_font_name(name) in pdfmetrics.getRegisteredFontNames()


def get_fallback_font(config: AppConfig) -> str:
    """按回退顺序返回第一个已注册的字体名。"""
    registered = pdfmetrics.getRegisteredFontNames()
    for name in config.font.fallback_order:
        if name in registered:
            return name
    raise RuntimeError(
        "[X] 未找到任何可用字体，请检查字体目录和字体映射配置。"
    )


def resolve_font(preferred: str, config: AppConfig, bold: bool = False) -> str:
    """返回 preferred 字体（若已注册），否则返回 fallback 字体。
    bold=True 时优先尝试同名粗体变体。
    """
    if bold and has_bold_variant(preferred):
        return bold_font_name(preferred)
    if preferred in pdfmetrics.getRegisteredFontNames():
        return preferred
    return get_fallback_font(config)


# =============================================================================
#  文本工具
# =============================================================================

_SPECIAL_CHAR_RE = re.compile(
    r'[^a-zA-Z0-9一-鿿぀-ゟ゠-ヿ㐀-䶿豈-﫿'
    r'０-９ａ-ｚＡ-Ｚ々〆〤ヶー一-龥ぁ-んァ-ヾｱ-ﾝﾞﾟ'
    r'，。！？；：""''（）【】《》、·…—～@#￥%&*——+={}|[]<>「」『』'
    r'，．：；？！゛゜´｀¨＾￣＿ヽヾゝゞ〃仝々〆〇ー―‐／＼～∥｜…‥ ]'
)


def clean_text(text: str, config: AppConfig) -> str:
    """过滤无法显示的特殊字符，压缩多余空白（保留换行）。"""
    if not text or not config.advanced.remove_special_chars:
        return text
    # 先保护换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    parts = text.split("\n")
    cleaned = []
    for part in parts:
        p = _SPECIAL_CHAR_RE.sub("", part)
        p = re.sub(r"[ \t\f\v]+", " ", p).strip()
        cleaned.append(p)
    return "\n".join(cleaned)


def wrap_text(text: str, font: str, size: float, max_width: float) -> list:
    """按像素宽度对文本进行自动换行，返回行列表。"""
    lines, current = [], ""
    for ch in text:
        if stringWidth(current + ch, font, size) > max_width and current:
            lines.append(current)
            current = ch
        else:
            current += ch
    if current:
        lines.append(current)
    return lines
