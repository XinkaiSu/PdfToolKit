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
    """注册配置中所有可用字体。"""
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


def get_fallback_font(config: AppConfig) -> str:
    """按回退顺序返回第一个已注册的字体名。"""
    registered = pdfmetrics.getRegisteredFontNames()
    for name in config.font.fallback_order:
        if name in registered:
            return name
    raise RuntimeError(
        "[X] 未找到任何可用字体，请检查字体目录和字体映射配置。"
    )


def resolve_font(preferred: str, config: AppConfig) -> str:
    """返回 preferred 字体（若已注册），否则返回 fallback 字体。"""
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
    """过滤无法显示的特殊字符，压缩多余空白。"""
    if not text or not config.advanced.remove_special_chars:
        return text
    text = _SPECIAL_CHAR_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


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
