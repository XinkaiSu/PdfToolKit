# =============================================================================
#  methods/cover.py — 参数化封面生成 + 预览
#  使用 reportlab 完全生成封面，无需 DOCX 模板
# =============================================================================

import io
import os
import datetime

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth

from config import CoverConfig, AppConfig
from methods.fonts import register_fonts, resolve_font, has_bold_variant, wrap_text, clean_text


A4_WIDTH, A4_HEIGHT = A4


def _current_year_month() -> str:
    """返回当前年月字符串，如 '2026年5月'。"""
    now = datetime.date.today()
    return f"{now.year}年{now.month}月"


def _wrap_multiline(text: str, font: str, size: float, max_w: float) -> list:
    """先按用户输入的换行符切分，再按像素宽度自动换行。"""
    out = []
    for raw_line in text.split("\n"):
        if raw_line == "":
            out.append("")
            continue
        out.extend(wrap_text(raw_line, font, size, max_w))
    return out


def _draw_centered_lines(c, lines, font, size, page_w, y, line_gap_ratio=1.5):
    """以 (page_w, y) 为基准居中绘制多行文本，返回最后绘制后的 y 坐标。"""
    c.setFont(font, size)
    for line in lines:
        if line == "":
            y -= size * line_gap_ratio
            continue
        lw = stringWidth(line, font, size)
        c.drawString((page_w - lw) / 2, y, line)
        y -= size * line_gap_ratio
    return y


def _draw_cover_on_canvas(c: canvas.Canvas, config: CoverConfig, title: str,
                          page_w: float, page_h: float, app_config: AppConfig):
    """
    在 reportlab Canvas 上绘制封面。
    唯一的布局逻辑入口，供 generate_cover_pdf 和 generate_cover_preview 共享。
    """
    # 1. 页面装饰线
    if config.show_border:
        m = config.get_border_margin()
        color = config.get_border_color_tuple()
        c.setStrokeColorRGB(*color)
        c.setLineWidth(config.border_width)
        c.rect(m, m, page_w - 2 * m, page_h - 2 * m)

    # 2. Logo（左上角）
    if config.logo_path and os.path.exists(config.logo_path):
        x = config.get_logo_margin_left()
        y = page_h - config.get_logo_margin_top() - config.logo_height
        try:
            c.drawImage(
                config.logo_path, x, y,
                width=config.logo_width, height=config.logo_height,
                preserveAspectRatio=True, mask='auto'
            )
        except Exception:
            pass  # Logo 加载失败时不影响其他元素

    # 3. 右上角文字（多行，右上对齐）
    if config.corner_text:
        font = resolve_font(config.corner_text_font, app_config)
        color = config.get_corner_color_tuple()
        c.setFillColorRGB(*color)
        lines = _wrap_multiline(config.corner_text, font, config.corner_text_size,
                                 page_w - config.get_corner_margin_right() - 10)
        x = page_w - config.get_corner_margin_right()
        y = page_h - config.get_corner_margin_top() - config.corner_text_size
        for line in lines:
            if line == "":
                y -= config.corner_text_size * 1.5
                continue
            c.setFont(font, config.corner_text_size)
            tw = stringWidth(line, font, config.corner_text_size)
            c.drawString(x - tw, y, line)
            y -= config.corner_text_size * 1.5

    # 4. 主标题 + 副标题（页面中心偏上，多行）
    c.setFillColorRGB(0, 0, 0)
    text_margin = (config.get_border_margin() + 20) if config.show_border else 20
    max_w = page_w - 2 * text_margin
    center_y = page_h * config.main_title_y_ratio

    main_title = title if config.main_title_use_folder else (config.title_text or title)
    title_font = resolve_font(config.main_title_font, app_config)
    title_lines = _wrap_multiline(main_title, title_font, config.main_title_size, max_w)
    total_h = len(title_lines) * (config.main_title_size * 1.5)
    y = center_y + total_h / 2
    y = _draw_centered_lines(c, title_lines, title_font, config.main_title_size, page_w, y)

    # 副标题
    sub_text = title if config.subtitle_use_folder else config.subtitle
    if sub_text:
        y -= config.main_title_size * 0.5
        sub_font = resolve_font(config.subtitle_font, app_config)
        sub_lines = _wrap_multiline(sub_text, sub_font, config.subtitle_size, max_w)
        y = _draw_centered_lines(c, sub_lines, sub_font, config.subtitle_size, page_w, y)

    # 5. 编制单位区域（页面中心下方，多行）
    unit_y = page_h * config.unit_y_ratio
    unit_font_name = config.unit_font
    ly = unit_y

    # 标签（多行，使用粗体字体；无粗体时双重描边模拟）
    label = config.unit_label
    if label:
        label_lines = _wrap_multiline(label, unit_font_name, config.unit_label_size, max_w)
        if has_bold_variant(unit_font_name):
            bold_f = resolve_font(unit_font_name, app_config, bold=True)
            ly = _draw_centered_lines(c, label_lines, bold_f, config.unit_label_size,
                                      page_w, ly)
        else:
            for line in label_lines:
                if line == "":
                    ly -= config.unit_label_size * 1.5
                    continue
                lw = stringWidth(line, unit_font_name, config.unit_label_size)
                lx = (page_w - lw) / 2
                c.setFont(unit_font_name, config.unit_label_size)
                c.drawString(lx + 0.3, ly + 0.3, line)
                c.drawString(lx, ly, line)
                ly -= config.unit_label_size * 1.5

    # 单位名称（多行）
    if config.unit_name:
        name_lines = _wrap_multiline(config.unit_name, unit_font_name,
                                      config.unit_name_size, max_w)
        ny = ly - config.unit_label_size * 0.3
        _draw_centered_lines(c, name_lines, unit_font_name, config.unit_name_size,
                             page_w, ny)

    # 6. 日期（独立垂直位置，多行）
    date_str = config.cover_date or _current_year_month()
    date_font = resolve_font(config.date_font, app_config)
    date_lines = _wrap_multiline(date_str, date_font, config.date_size, max_w)
    total_date_h = len(date_lines) * (config.date_size * 1.5)
    dy = page_h * config.date_y_ratio + total_date_h / 2
    _draw_centered_lines(c, date_lines, date_font, config.date_size, page_w, dy)


def generate_cover_pdf(config: CoverConfig, title: str, output_path: str,
                       app_config: AppConfig = None) -> int:
    """生成封面 PDF 文件，返回页数。"""
    if app_config is None:
        app_config = AppConfig()
    register_fonts(app_config)
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setCreator("PDF Merge Tool")
    _draw_cover_on_canvas(c, config, clean_text(title, app_config),
                          A4_WIDTH, A4_HEIGHT, app_config)
    c.save()
    print(f"[OK] 封面生成完成：{title}")
    return 1


def generate_cover_preview(config: CoverConfig, title: str,
                           app_config: AppConfig = None,
                           dpi: int = 72) -> bytes:
    """生成封面预览图像数据（PNG bytes），用于 GUI 显示。"""
    import fitz  # PyMuPDF

    if app_config is None:
        app_config = AppConfig()
    register_fonts(app_config)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _draw_cover_on_canvas(c, config, clean_text(title, app_config),
                          A4_WIDTH, A4_HEIGHT, app_config)
    c.save()

    buf.seek(0)
    doc = fitz.open(stream=buf.read(), filetype="pdf")
    page = doc.load_page(0)
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")
