# =============================================================================
#  methods/convert.py — PDF A4 转换 + 图片转 PDF + 临时文件管理
# =============================================================================

import os
import shutil
import tempfile

import pikepdf
from pikepdf import Pdf
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


A4_WIDTH, A4_HEIGHT = A4


# =============================================================================
#  临时文件管理
# =============================================================================

def _temp_dir() -> str:
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_tmp")
    os.makedirs(d, exist_ok=True)
    return d


def make_temp_file(suffix: str = ".pdf") -> str:
    """创建临时文件，返回路径。"""
    fd, path = tempfile.mkstemp(suffix=suffix, dir=_temp_dir())
    os.close(fd)
    return path


def cleanup_temp():
    """删除临时文件夹。"""
    d = _temp_dir()
    if os.path.exists(d):
        try:
            shutil.rmtree(d)
        except Exception as e:
            print(f"[!] 清理临时目录失败：{e}")


# =============================================================================
#  PDF → A4 转换
# =============================================================================

def _make_blank_page(pdf, w, h):
    """在 pdf 中创建空白页面。"""
    obj = pikepdf.Dictionary(
        Type=pikepdf.Name.Page,
        MediaBox=pikepdf.Array([0, 0, pikepdf.Real(round(w, 3)), pikepdf.Real(round(h, 3))]),
        Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary()),
        Contents=pdf.make_stream(b""),
    )
    pdf.pages.append(pikepdf.Page(obj))
    return pdf.pages[-1]


def _page_to_xobject(pdf, src_page_obj):
    """将源页转为 XObject，返回 (formx, vis_w, vis_h)。"""
    mb = src_page_obj.MediaBox
    w = float(mb[2]) - float(mb[0])
    h = float(mb[3]) - float(mb[1])
    rotate = int(src_page_obj.get("/Rotate", 0))
    if rotate in (90, 270):
        w, h = h, w
    pdf.pages.append(src_page_obj)
    formx = pikepdf.Page(pdf.pages[-1]).as_form_xobject()
    del pdf.pages[-1]
    return formx, w, h


def _embed_xobject(pdf, page_obj, formx, xname, pw, ph,
                   allow_shrink=True, allow_expand=True):
    """将 formx 嵌入 page_obj，返回内容流字节。"""
    page_obj["/Resources"]["/XObject"][xname] = formx
    rect = pikepdf.Rectangle(0, 0, pw, ph)
    return pikepdf.Page(page_obj).calc_form_xobject_placement(
        formx, xname, rect,
        allow_shrink=allow_shrink, allow_expand=allow_expand,
    )


def convert_pdf_to_a4(input_pdf, output_pdf):
    """将 PDF 每页转换为 A4 尺寸（等比缩放居中，无裁切）。"""
    try:
        out_dir = os.path.dirname(output_pdf)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        src = Pdf.open(input_pdf)
        out = Pdf.new()
        pages_data = []
        for src_page in src.pages:
            formx, vis_w, vis_h = _page_to_xobject(out, src_page)
            if vis_w > vis_h:
                target_w, target_h = A4_HEIGHT, A4_WIDTH
            else:
                target_w, target_h = A4_WIDTH, A4_HEIGHT
            pages_data.append((formx, target_w, target_h))
        for formx, tw, th in pages_data:
            new_obj = _make_blank_page(out, tw, th)
            content = _embed_xobject(out, new_obj, formx, pikepdf.Name("/Pg"), tw, th)
            new_obj["/Contents"] = out.make_stream(content)
        out.save(output_pdf, encryption=False)
        return True
    except Exception as e:
        print(f"[!] PDF转A4失败：{e}，直接复制文件")
        shutil.copy(input_pdf, output_pdf)
        return False


def convert_pdf_to_a4_memory(input_pdf) -> "Pdf":
    """将 PDF 每页转换为 A4 尺寸，返回 pikepdf.Pdf 对象（无需写入文件）。
    input_pdf 可以是文件路径字符串或已打开的 pikepdf.Pdf 对象。
    """
    if isinstance(input_pdf, str):
        src = Pdf.open(input_pdf)
    else:
        src = input_pdf

    out = Pdf.new()
    pages_data = []
    for src_page in src.pages:
        formx, vis_w, vis_h = _page_to_xobject(out, src_page)
        if vis_w > vis_h:
            target_w, target_h = A4_HEIGHT, A4_WIDTH
        else:
            target_w, target_h = A4_WIDTH, A4_HEIGHT
        pages_data.append((formx, target_w, target_h))
    for formx, tw, th in pages_data:
        new_obj = _make_blank_page(out, tw, th)
        content = _embed_xobject(out, new_obj, formx, pikepdf.Name("/Pg"), tw, th)
        new_obj["/Contents"] = out.make_stream(content)

    if isinstance(input_pdf, str):
        src.close()

    return out


# =============================================================================
#  图片转 PDF
# =============================================================================

def image_to_pdf(image_path: str, output_pdf: str) -> bool:
    """将单张图片转为单页 A4 PDF，图片等比居中放置。"""
    try:
        img = PILImage.open(image_path)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img_w, img_h = img.size
        # A4 内留 20pt 边距
        margin = 20
        max_w = A4_WIDTH - 2 * margin
        max_h = A4_HEIGHT - 2 * margin
        scale = min(max_w / img_w, max_h / img_h)
        draw_w = img_w * scale
        draw_h = img_h * scale
        x = (A4_WIDTH - draw_w) / 2
        y = (A4_HEIGHT - draw_h) / 2

        c = canvas.Canvas(output_pdf, pagesize=A4)
        c.drawImage(ImageReader(img), x, y, width=draw_w, height=draw_h)
        c.save()
        return True
    except Exception as e:
        print(f"[!] 图片转PDF失败：{image_path} — {e}")
        return False
