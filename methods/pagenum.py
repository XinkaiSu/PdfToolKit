# =============================================================================
#  methods/pagenum.py — 页码叠加
# =============================================================================

import os
import shutil
import platform

import pikepdf
from pikepdf import Pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.pdfmetrics import stringWidth

from config import AppConfig
from methods.fonts import register_fonts, resolve_font
from methods.convert import (
    _make_blank_page, _page_to_xobject, _embed_xobject,
    make_temp_file, A4_WIDTH, A4_HEIGHT,
)


def _page_num_x(pw, config: AppConfig):
    """计算页码 X 坐标。"""
    pn = config.page_num
    if pn.align == "left":
        return pn.get_side_offset()
    if pn.align == "right":
        return pw - pn.get_side_offset()
    return pw / 2


def _draw_page_number(c, page_num, pw, config: AppConfig):
    """在 canvas 上绘制页码。"""
    pn = config.page_num
    x = _page_num_x(pw, config)
    y = pn.get_margin_bottom()

    bx = x - pn.bg_width / 2
    by = y - 2
    bw = pn.bg_width
    bh = pn.get_bg_height()

    if pn.border:
        br, bg, bb = pn.get_border_color_tuple()
        c.setStrokeColorRGB(br, bg, bb)
        c.setLineWidth(pn.border_width)
        if pn.border_style == "dashed":
            c.setDash(pn.border_dash_on, pn.border_dash_off)
        elif pn.border_style == "dotted":
            c.setDash(1, pn.border_dash_off)
        else:
            c.setDash()
        do_stroke = 1
    else:
        c.setDash()
        do_stroke = 0

    bg_color = pn.get_bg_color_tuple()
    if bg_color is not None:
        fr, fg, fb = bg_color
        c.setFillColorRGB(fr, fg, fb)
        do_fill = 1
    else:
        do_fill = 0

    if do_fill or do_stroke:
        if pn.bg_shape == "ellipse":
            c.ellipse(bx, by, bx + bw, by + bh, fill=do_fill, stroke=do_stroke)
        elif pn.bg_shape == "roundrect":
            c.roundRect(bx, by, bw, bh, pn.bg_radius, fill=do_fill, stroke=do_stroke)
        else:
            c.rect(bx, by, bw, bh, fill=do_fill, stroke=do_stroke)

    c.setDash()
    c.setLineWidth(1)

    tr, tg, tb = pn.get_text_color_tuple()
    c.setFillColorRGB(tr, tg, tb)
    font = resolve_font(pn.font, config)
    c.setFont(font, pn.size)
    text = str(page_num)

    if pn.align == "left":
        c.drawString(x, y, text)
    elif pn.align == "right":
        tw = stringWidth(text, font, pn.size)
        c.drawString(x - tw, y, text)
    else:
        c.drawCentredString(x, y, text)


def add_page_numbers(input_pdf, output_pdf, skip_pages, config: AppConfig):
    """为 PDF 添加页码，跳过前 skip_pages 页。批量处理，避免逐页临时文件。"""
    try:
        register_fonts(config)
        src = Pdf.open(input_pdf)
        out = Pdf.new()

        # 先提取源页信息（尺寸），再转 XObject
        src_page_list = list(src.pages)
        page_sizes = []
        for src_page in src_page_list:
            mb = src_page.MediaBox
            vis_w = float(mb[2]) - float(mb[0])
            vis_h = float(mb[3]) - float(mb[1])
            rotate = int(src_page.get("/Rotate", 0))
            if rotate in (90, 270):
                vis_w, vis_h = vis_h, vis_w
            page_sizes.append((vis_w, vis_h))

        total_pages = len(page_sizes)
        max_page_num = max((idx - skip_pages + 1) for idx in range(total_pages) if idx >= skip_pages) if total_pages > skip_pages else 0

        # 一次性生成所有页码叠加层
        num_xobjects = {}
        if max_page_num > 0:
            tmp = make_temp_file()
            tc = canvas.Canvas(tmp, pagesize=(A4_WIDTH, A4_HEIGHT))
            for pnum in range(1, max_page_num + 1):
                _draw_page_number(tc, pnum, A4_WIDTH, config)
                tc.showPage()
            tc.save()

            with Pdf.open(tmp) as num_pdf:
                for pnum_idx in range(len(num_pdf.pages)):
                    num_formx, _, _ = _page_to_xobject(out, num_pdf.pages[pnum_idx])
                    num_xobjects[pnum_idx + 1] = num_formx
            try:
                os.unlink(tmp)
            except Exception:
                pass

        # 处理每一页：转 XObject + 嵌入 + 可选页码叠加
        for idx, src_page in enumerate(src_page_list):
            formx, pw, ph = _page_to_xobject(out, src_page)
            new_obj = _make_blank_page(out, pw, ph)
            content = _embed_xobject(
                out, new_obj, formx, pikepdf.Name("/Pg"),
                pw, ph, allow_shrink=False, allow_expand=False
            )
            if idx >= skip_pages and (idx - skip_pages + 1) in num_xobjects:
                page_num = idx - skip_pages + 1
                num_formx = num_xobjects[page_num]
                num_content = _embed_xobject(
                    out, new_obj, num_formx, pikepdf.Name("/Num"),
                    pw, ph, allow_shrink=False, allow_expand=False
                )
                content = content + b"\n" + num_content
            new_obj["/Contents"] = out.make_stream(content)

        out.save(output_pdf, encryption=False)
        print("[OK] 页码添加完成")

    except Exception as e:
        print(f"[X] 添加页码失败：{e}")
        shutil.copy(input_pdf, output_pdf)


def add_page_numbers_image_mode(input_pdf, output_pdf, skip_pages, config: AppConfig):
    """图片化模式添加页码。"""
    try:
        from pdf2image import convert_from_path
        from PIL import Image

        adv = config.advanced
        pages = convert_from_path(
            input_pdf,
            dpi=adv.image_dpi,
            poppler_path=adv.poppler_path if platform.system() == "Windows" else None,
            thread_count=4,
        )

        register_fonts(config)
        c = canvas.Canvas(output_pdf, pagesize=A4)

        for idx, img in enumerate(pages):
            img.thumbnail((A4_WIDTH, A4_HEIGHT), Image.Resampling.LANCZOS)
            tmp_img = make_temp_file(".png")
            img.save(tmp_img, "PNG")
            c.drawImage(tmp_img, 0, 0, width=A4_WIDTH, height=A4_HEIGHT)
            if idx >= skip_pages:
                _draw_page_number(c, idx - skip_pages + 1, A4_WIDTH, config)
            try:
                os.unlink(tmp_img)
            except Exception:
                pass
            c.showPage()

        c.save()
        print("[OK] 页码添加完成（图片化模式）")

    except Exception as e:
        print(f"[X] 图片化模式添加页码失败：{e}")
        shutil.copy(input_pdf, output_pdf)
