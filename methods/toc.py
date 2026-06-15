# =============================================================================
#  methods/toc.py — 目录 PDF 生成
# =============================================================================

import os

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth

from config import AppConfig
from methods.fonts import register_fonts, resolve_font, has_bold_variant, clean_text, wrap_text
from methods.convert import convert_pdf_to_a4, make_temp_file
from methods.sort import _compute_numbering_prefix, strip_original_numbering
from pikepdf import Pdf


def generate_toc(output_path, items, pagination, title, config: AppConfig):
    """生成目录 PDF，返回目录页数。"""
    register_fonts(config)
    c = canvas.Canvas(output_path, pagesize=A4)
    c.setCreator("PDF Merge Tool")
    c.setTitle(f"目录 — {title}")

    toc = config.toc
    page_w, page_h = A4
    lm = toc.get_margin_left()
    rm = toc.get_margin_right()
    tm = toc.get_margin_top()
    bm = toc.get_margin_bottom()
    content_w = page_w - lm - rm
    y = page_h - tm

    # ── 绘制标题 ──
    t_font = resolve_font(toc.font_title, config)
    c.setFont(t_font, toc.font_size)
    title_clean = clean_text(title, config)
    title_lines = wrap_text(title_clean, t_font, toc.font_size, content_w)
    for line in title_lines:
        lw = stringWidth(line, t_font, toc.font_size)
        c.drawString(lm + (content_w - lw) / 2, y - toc.font_size, line)
        y -= toc.line_gap
    y -= toc.line_gap * 0.5

    # ── 绘制条目 ──
    _FONT_BY_LEVEL = {1: toc.font_level1, 2: toc.font_level2, 3: toc.font_level3}

    # 编号计数器（支持最多 10 级）
    _num_counters = [0] * 10
    _last_parent_at_level = [None] * 10

    def draw_entry(text, level, is_file, page_no):
        nonlocal y
        if not text or not page_no:
            return
        if is_file:
            font = resolve_font(toc.font_file, config)
            bold = False
        else:
            preferred = _FONT_BY_LEVEL.get(level, toc.font_deeper)
            want_bold = (level == 2)
            # 若该字体有粗体变体，直接用粗体注册名；否则保留双重描边的 bold 标志
            if want_bold and has_bold_variant(preferred):
                font = resolve_font(preferred, config, bold=True)
                bold = False
            else:
                font = resolve_font(preferred, config)
                bold = want_bold

        c.setFont(font, toc.font_size)
        page_str = str(page_no)
        indent = (level - 1) * toc.indent_per_level
        page_w_px = stringWidth(page_str, font, toc.font_size)
        x_page = page_w - rm - page_w_px
        max_text_w = x_page - lm - indent - 8

        lines = wrap_text(text, font, toc.font_size, max_text_w)
        if not lines:
            return

        if y - len(lines) * toc.line_gap < bm:
            c.showPage()
            y = page_h - tm
            register_fonts(config)
            c.setFont(font, toc.font_size)

        for i, line in enumerate(lines):
            x_text = lm + indent
            text_y = y - (toc.line_gap - toc.font_size) / 2 - toc.font_size
            if bold:
                c.drawString(x_text + 0.3, text_y + 0.3, line)
            c.drawString(x_text, text_y, line)
            if i == len(lines) - 1:
                dot_w = stringWidth(toc.dot_char, font, toc.font_size)
                cx = x_text + stringWidth(line, font, toc.font_size) + 2
                while cx < x_page - 2:
                    c.drawString(cx, text_y, toc.dot_char)
                    cx += dot_w + 1
                c.drawString(x_page, text_y, page_str)
            y -= toc.line_gap

    for item in items:
        if item["level"] == 0:
            continue

        # 编号前缀
        name_text = clean_text(item["name"], config)
        # 删除原有编号（在追加新编号之前）
        if config.numbering.remove_original:
            name_text = strip_original_numbering(name_text)
        if config.numbering.enabled:
            num_cfg = config.numbering
            level = item["level"]
            # 获取当前级别的编号样式
            if level == 1:
                style = num_cfg.level1_style
            elif level == 2:
                style = num_cfg.level2_style
            elif level == 3:
                style = num_cfg.level3_style
            else:
                style = num_cfg.level_deeper_style

            # 更新计数器：当父级变化时重置更深层计数器
            parent_path = item.get("path", "")
            if style != "none":
                current_parent = os.path.dirname(parent_path)
                if current_parent != _last_parent_at_level[level - 1]:
                    # 父级变化，重置当前及更深层的计数器
                    for j in range(level - 1, len(_num_counters)):
                        _num_counters[j] = 0
                    _last_parent_at_level[level - 1] = current_parent
                _num_counters[level - 1] += 1

            prefix = _compute_numbering_prefix(level, _num_counters, style, num_cfg.separator,
                                               num_cfg.num_prefix, num_cfg.num_suffix)
            if prefix:
                name_text = prefix + name_text

        draw_entry(
            name_text,
            item["level"],
            item["type"] == "file",
            pagination.get(item["path"]),
        )

    c.save()

    tmp = make_temp_file()
    convert_pdf_to_a4(output_path, tmp)
    os.replace(tmp, output_path)

    with Pdf.open(output_path) as f:
        return len(f.pages)
