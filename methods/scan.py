# =============================================================================
#  methods/scan.py — 扫描痕迹模式
#  PDF → 渲染图片 → 应用扫描效果 → 拼回 A4 PDF
# =============================================================================

import io
import os
from typing import List

import fitz  # PyMuPDF
from PIL import Image, ImageOps
from scanner import DocumentScanner

from methods.sort import chinese_sort_key

# 支持的扩展名
PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".tif", ".bmp"}
OFFICE_EXTS = {".doc", ".docx"}


# ── 强度预设映射表 ────────────────────────────────────────────────────────────

_PRESETS = {
    "light": dict(
        askew=True, noise=0, jpeg_quality=95,
        black_and_white=False, blur=False, blur_variation=False,
        contrast=1.0, sharpness=1.0, brightness=1.0,
    ),
    "medium": dict(
        askew=True, noise=5, jpeg_quality=90,
        black_and_white=False, blur=False, blur_variation=False,
        contrast=1.05, sharpness=1.0, brightness=1.0,
    ),
    "heavy": dict(
        askew=True, noise=20, jpeg_quality=75,
        black_and_white=True, blur=False, blur_variation=True,
        contrast=1.2, sharpness=1.0, brightness=0.95,
    ),
}


def _resolve_params(scan_cfg) -> dict:
    """根据 preset 解析最终参数。custom 时读取 scan_cfg 各字段。"""
    if scan_cfg.preset == "custom":
        return dict(
            askew=scan_cfg.askew,
            noise=scan_cfg.noise,
            jpeg_quality=scan_cfg.jpeg_quality,
            black_and_white=scan_cfg.black_and_white,
            blur=scan_cfg.blur,
            blur_variation=scan_cfg.blur_variation,
            contrast=scan_cfg.contrast,
            sharpness=scan_cfg.sharpness,
            brightness=scan_cfg.brightness,
        )
    return dict(_PRESETS.get(scan_cfg.preset, _PRESETS["medium"]))


def _apply_scan_effects(img: Image.Image, scan_cfg) -> Image.Image:
    """对单张 PIL 图应用扫描效果。"""
    p = _resolve_params(scan_cfg)
    scanner = DocumentScanner(
        file_quality=p["jpeg_quality"],
        askew=p["askew"],
        black_and_white=p["black_and_white"],
        blur=p["blur"],
        variation=p["blur_variation"],
        noise=p["noise"],
        contrast=p["contrast"],
        sharpness=p["sharpness"],
        brightness=p["brightness"],
    )
    if img.mode != "RGB":
        img = img.convert("RGB")
    # 直接调用私有方法 _apply_effects：上游 DocumentScanner 没有暴露
    # "对单张已加载的 PIL 图施加效果" 的公共 API（公共入口都绑定到文件 IO）。
    # 这里我们只需效果管线，复用其实现以避免重复维护。
    return scanner._apply_effects(img)


# ── PDF → 图片 列表 ──────────────────────────────────────────────────────────

def render_pdf_to_images(pdf_path: str, dpi: int) -> List[Image.Image]:
    """用 PyMuPDF 把 PDF 每页渲染成 PIL.Image。"""
    images = []
    doc = fitz.open(pdf_path)
    try:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
            if mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
    finally:
        doc.close()
    return images


# ── 图片列表 → A4 PDF ────────────────────────────────────────────────────────

def images_to_pdf_a4(images: List[Image.Image], output_path: str,
                     jpeg_quality: int = 90) -> int:
    """把若干 PIL 图片以 A4 居中等比方式写入 PDF。返回写入页数。"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader

    if not images:
        return 0

    A4_W, A4_H = A4

    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    c = canvas.Canvas(output_path, pagesize=A4)
    for img in images:
        if img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        scale = min(A4_W / w, A4_H / h)
        draw_w = w * scale
        draw_h = h * scale
        x = (A4_W - draw_w) / 2
        y = (A4_H - draw_h) / 2
        # 显式按指定 JPEG 质量编码，避免被 reportlab 默认值吞掉
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=int(jpeg_quality), optimize=True)
        buf.seek(0)
        c.drawImage(ImageReader(buf), x, y, width=draw_w, height=draw_h,
                    preserveAspectRatio=True)
        c.showPage()
    c.save()
    return len(images)


# ── 文件收集 ─────────────────────────────────────────────────────────────────

def collect_scan_files(scan_cfg) -> List[str]:
    """递归收集输入根下所有待处理文件的绝对路径。

    返回的列表里：
    - 始终包含 .pdf
    - 当 include_office=True 时包含 .doc/.docx
    - 当 include_images=True 时包含 IMAGE_EXTS

    每层目录的兄弟节点用 chinese_sort_key 排序。
    """
    root = scan_cfg.input_root
    if not root or not os.path.isdir(root):
        return []

    wanted = set(PDF_EXTS)
    if scan_cfg.include_office:
        wanted |= OFFICE_EXTS
    if scan_cfg.include_images:
        wanted |= IMAGE_EXTS

    # 直接按中文/自然顺序排，扫描模式始终启用中文排序
    sort_key = chinese_sort_key

    results = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 排序兄弟目录与文件
        dirnames.sort(key=sort_key)
        filenames.sort(key=sort_key)
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext in wanted:
                results.append(os.path.join(dirpath, fn))
    return results


# ── 单文件处理入口 ───────────────────────────────────────────────────────────

def process_scan_file(input_path: str, output_path: str, scan_cfg,
                      stop_event=None) -> str:
    """处理单个文件 → 写到 output_path。

    返回值：
      "ok"      处理成功
      "skip"    主动跳过（如零页 PDF）
      "fail"    处理失败（已记录日志）
      "stopped" stop_event 触发
    """
    if stop_event and stop_event.is_set():
        return "stopped"

    ext = os.path.splitext(input_path)[1].lower()
    rel_label = os.path.basename(input_path)

    try:
        if ext in PDF_EXTS:
            images = render_pdf_to_images(input_path, scan_cfg.dpi)
        elif ext in IMAGE_EXTS:
            with Image.open(input_path) as raw:
                raw.load()
                img = ImageOps.exif_transpose(raw)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                images = [img.copy()]
        elif ext in OFFICE_EXTS:
            # Office 转换在 Task 4 中接入
            from methods.office import word_to_pdf_temp, OfficeError
            try:
                tmp_pdf = word_to_pdf_temp(input_path)
            except OfficeError as e:
                print(f"[X] {rel_label} 转换失败：{e}")
                return "fail"
            try:
                images = render_pdf_to_images(tmp_pdf, scan_cfg.dpi)
            finally:
                if os.path.exists(tmp_pdf):
                    try:
                        os.remove(tmp_pdf)
                    except Exception:
                        pass
        else:
            print(f"[!] {rel_label} 未知扩展名，跳过")
            return "skip"

        if not images:
            print(f"[i] {rel_label} — 0 页，跳过")
            return "skip"

        # 应用扫描效果
        processed = []
        for i, img in enumerate(images):
            if stop_event and stop_event.is_set():
                return "stopped"
            try:
                processed.append(_apply_scan_effects(img, scan_cfg))
            except Exception as e:
                print(f"[X] {rel_label} 第 {i+1} 页效果失败：{e}")
                return "fail"

        # 写出 A4 PDF
        p = _resolve_params(scan_cfg)
        try:
            images_to_pdf_a4(processed, output_path, jpeg_quality=p["jpeg_quality"])
        except PermissionError:
            print(f"[X] 无权写入 {output_path}")
            return "fail"
        return "ok"

    except Exception as e:
        print(f"[X] 文件 {rel_label} 处理失败：{e}")
        return "fail"
