# =============================================================================
#  core.py — PDF 处理核心
#  从 pdf_merge.py 提取，去除 DOCX 依赖，参数化配置
# =============================================================================

import os
import re
import shutil
import tempfile
import platform

import pikepdf
from pikepdf import Pdf
from PIL import Image as PILImage
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth

from config import AppConfig


# =============================================================================
#  内部常量
# =============================================================================

A4_WIDTH, A4_HEIGHT = A4


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


# =============================================================================
#  中文排序
# =============================================================================

_CN_UNIT = {"十": 10, "百": 100}
_CN_DIGIT = {
    "零": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


def _cn_to_int(s: str) -> int:
    """将中文数字字符串转换为整数（支持一~九十九）。"""
    if not s:
        return -1
    s = s.strip()
    if s[0] == "十":
        result = 10
        if len(s) > 1 and s[1] in _CN_DIGIT:
            result += _CN_DIGIT[s[1]]
        return result
    if len(s) >= 2 and s[1] == "十":
        result = _CN_DIGIT.get(s[0], -1) * 10
        if result == -1:
            return -1
        if len(s) > 2 and s[2] in _CN_DIGIT:
            result += _CN_DIGIT[s[2]]
        return result
    return _CN_DIGIT.get(s, -1)


def _int_to_cn(n: int) -> str:
    """将整数转为中文数字字符串（1→一, 10→十, 21→二十一，支持 0-99）。"""
    if n < 0 or n > 99:
        return str(n)
    digits = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]
    if n == 0:
        return digits[0]
    if n < 10:
        return digits[n]
    if n < 20:
        if n == 10:
            return "十"
        return "十" + digits[n - 10]
    tens = n // 10
    ones = n % 10
    result = digits[tens] + "十"
    if ones > 0:
        result += digits[ones]
    return result


def _compute_numbering_prefix(level: int, counters: list, style: str, separator: str) -> str:
    """根据编号样式和计数器生成编号前缀。
    counters: 各级计数器列表，1-indexed。
    """
    if style == "none":
        return ""
    if style == "chinese":
        return _int_to_cn(counters[level - 1]) + separator
    if style == "arabic":
        return str(counters[level - 1]) + separator
    if style == "multi_level":
        parts = [str(counters[i]) for i in range(level)]
        return ".".join(parts) + separator
    return ""


_CN_ORDER_RE = re.compile(
    r"^(?:"
    r"第([一二三四五六七八九十百零]+)[章节条款]"
    r"|[（(]([一二三四五六七八九十百零]+)[）)]"
    r"|([一二三四五六七八九十百零]+)[、．.]"
    r")"
)


def chinese_sort_key(s: str) -> tuple:
    """解析文件名开头的中文序号，返回排序键。"""
    m = _CN_ORDER_RE.match(s)
    if m:
        cn_str = m.group(1) or m.group(2) or m.group(3)
        num = _cn_to_int(cn_str)
        rest = s[m.end():]
        return (num if num >= 0 else float("inf"), natural_sort_key(rest))
    return (float("inf"), natural_sort_key(s))


def natural_sort_key(s: str) -> list:
    """自然排序键，使 '2' < '10'。"""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]


def smart_sort_key(s: str, config: AppConfig):
    """智能排序键：优先中文序号或纯自然排序。"""
    if config.advanced.enable_chinese_sort:
        return chinese_sort_key(s)
    return (float("inf"), natural_sort_key(s))


# =============================================================================
#  文件结构收集
# =============================================================================

def collect_file_tree(root_dir: str, config: AppConfig, custom_order: dict = None) -> tuple:
    """递归扫描 root_dir，返回 (flat_items, root_name)。
    custom_order: {目录路径: [子项名1, 子项名2, ...]}，用于覆盖默认排序。
    """
    root_name = clean_text(os.path.basename(root_dir), config)
    root_item = {
        "type": "folder", "level": 0,
        "name": root_name, "path": root_dir, "children": []
    }

    def _apply_custom_order(entries, path):
        """根据 custom_order 重排条目，未列出的条目按默认排序追加到末尾。"""
        if not custom_order or path not in custom_order:
            return entries
        order_list = custom_order[path]
        order_map = {name: i for i, name in enumerate(order_list)}
        ordered = []
        remaining = []
        for raw, cln in entries:
            key = raw  # 用原始文件名匹配
            if key in order_map:
                ordered.append((order_map[key], raw, cln))
            else:
                remaining.append((raw, cln))
        ordered.sort(key=lambda x: x[0])
        result = [(raw, cln) for _, raw, cln in ordered]
        # 未在自定义排序中的条目按默认排序追加
        remaining.sort(key=lambda x: smart_sort_key(x[0], config))
        result.extend(remaining)
        return result

    def _is_valid_file(name, path):
        """判断文件是否应被收集（PDF 或启用图片时的图片文件）。"""
        if not os.path.isfile(path):
            return False
        if path in config.advanced.excluded_files:
            return False
        if name.lower().endswith(".pdf"):
            return True
        if config.advanced.include_images:
            ext = os.path.splitext(name)[1].lower()
            return ext in [e.lower() for e in config.advanced.image_extensions]
        return False

    def _is_image_file(name):
        """判断文件是否为图片文件。"""
        ext = os.path.splitext(name)[1].lower()
        return ext in [e.lower() for e in config.advanced.image_extensions]

    def _recurse(node, path, level):
        try:
            entries = os.listdir(path)
        except (PermissionError, FileNotFoundError):
            return
        folders = sorted(
            [(e, clean_text(e, config)) for e in entries if os.path.isdir(os.path.join(path, e))],
            key=lambda x: smart_sort_key(x[0], config)
        )
        files = sorted(
            [(e, clean_text(e, config)) for e in entries
             if _is_valid_file(e, os.path.join(path, e))],
            key=lambda x: smart_sort_key(x[0], config)
        )
        # 应用自定义排序
        folders = _apply_custom_order(folders, path)
        files = _apply_custom_order(files, path)
        for raw, cln in folders:
            child = {
                "type": "folder", "level": level + 1,
                "name": cln, "path": os.path.join(path, raw), "children": []
            }
            node["children"].append(child)
            _recurse(child, child["path"], level + 1)
        for raw, cln in files:
            node["children"].append({
                "type": "file", "level": level + 1,
                "name": os.path.splitext(cln)[0],
                "raw_name": raw,
                "path": os.path.join(path, raw),
                "is_image": _is_image_file(raw),
            })

    _recurse(root_item, root_dir, 0)

    flat = []

    def _flatten(node):
        flat.append(node)
        for child in node.get("children", []):
            _flatten(child)

    _flatten(root_item)
    return flat, root_name


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


# =============================================================================
#  合并正文 PDF
# =============================================================================

def merge_content(items, output_path, config: AppConfig):
    """合并所有 PDF/图片文件，返回 (pagination, total_pages)。"""
    pagination = {}
    folder_first_page = {}
    current_page = 1
    valid_items = []
    img_temp_files = []  # 图片转PDF的临时文件，合并后清理

    for item in items:
        if item["type"] != "file":
            continue
        try:
            is_image = item.get("is_image", False)
            pdf_path = item["path"]
            if is_image:
                # 先将图片转为临时 PDF
                tmp_img_pdf = make_temp_file()
                if image_to_pdf(item["path"], tmp_img_pdf):
                    pdf_path = tmp_img_pdf
                    img_temp_files.append(tmp_img_pdf)
                else:
                    continue
            with Pdf.open(pdf_path) as f:
                page_count = len(f.pages)
            pagination[item["path"]] = current_page
            d = os.path.dirname(item["path"])
            while d not in folder_first_page and d != os.path.dirname(d):
                folder_first_page[d] = current_page
                d = os.path.dirname(d)
            current_page += page_count
            valid_items.append((item, pdf_path))
            label = item.get('raw_name', item['path'])
            prefix = "[图片] " if is_image else ""
            print(f"  [OK] {prefix}加载：{label}")
        except Exception as e:
            print(f"  [X] 跳过：{item.get('raw_name', item['path'])} — {e}")

    if not valid_items:
        raise RuntimeError("[X] 未找到任何有效 PDF/图片文件，请检查输入目录。")

    merger = Pdf.new()
    for item, pdf_path in valid_items:
        tmp = make_temp_file()
        convert_pdf_to_a4(pdf_path, tmp)
        with Pdf.open(tmp) as f:
            merger.pages.extend(f.pages)
        try:
            os.unlink(tmp)
        except Exception:
            pass
    merger.save(output_path, encryption=False)

    # 清理图片转PDF的临时文件
    for tmp in img_temp_files:
        try:
            os.unlink(tmp)
        except Exception:
            pass

    for item in items:
        if item["type"] == "folder" and item["path"] in folder_first_page:
            pagination[item["path"]] = folder_first_page[item["path"]]

    return pagination, current_page - 1


# =============================================================================
#  目录生成
# =============================================================================

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
            font = resolve_font(_FONT_BY_LEVEL.get(level, toc.font_deeper), config)
            bold = (level == 2)

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
                current_parent = os.path.dirname(parent_path) if item["type"] == "file" else parent_path
                if current_parent != _last_parent_at_level[level - 1]:
                    # 父级变化，重置当前及更深层的计数器
                    for j in range(level - 1, len(_num_counters)):
                        _num_counters[j] = 0
                    _last_parent_at_level[level - 1] = current_parent
                _num_counters[level - 1] += 1

            prefix = _compute_numbering_prefix(level, _num_counters, style, num_cfg.separator)
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


# =============================================================================
#  页码叠加
# =============================================================================

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
    """为 PDF 添加页码，跳过前 skip_pages 页。"""
    try:
        register_fonts(config)
        src = Pdf.open(input_pdf)
        out = Pdf.new()

        pages_data = []
        for idx, src_page in enumerate(src.pages):
            formx, vis_w, vis_h = _page_to_xobject(out, src_page)
            pages_data.append((formx, vis_w, vis_h, idx))

        for formx, pw, ph, idx in pages_data:
            new_obj = _make_blank_page(out, pw, ph)
            content = _embed_xobject(
                out, new_obj, formx, pikepdf.Name("/Pg"),
                pw, ph, allow_shrink=False, allow_expand=False
            )
            if idx >= skip_pages:
                page_num = idx - skip_pages + 1
                tmp = make_temp_file()
                tc = canvas.Canvas(tmp, pagesize=(pw, ph))
                _draw_page_number(tc, page_num, pw, config)
                tc.save()
                with Pdf.open(tmp) as num_pdf:
                    num_formx, _, _ = _page_to_xobject(out, num_pdf.pages[0])
                num_content = _embed_xobject(
                    out, new_obj, num_formx, pikepdf.Name("/Num"),
                    pw, ph, allow_shrink=False, allow_expand=False
                )
                content = content + b"\n" + num_content
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
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


# =============================================================================
#  主流程
# =============================================================================

def process_folder(input_folder, output_file, config: AppConfig, stop_event=None):
    """处理单个文件夹：扫描 → 封面 → 合并 → 目录 → 页码 → 插入封面 → 输出。"""
    from cover import generate_cover_pdf

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cover_pdf = os.path.join(script_dir, "_cover_tmp.pdf")
    content_pdf = os.path.join(script_dir, "_content_tmp.pdf")
    toc_pdf = os.path.join(script_dir, "_toc_tmp.pdf")
    merged_pdf = os.path.join(script_dir, "_merged_tmp.pdf")
    final_pdf = os.path.join(script_dir, "_final_tmp.pdf")
    tmp_files = [cover_pdf, content_pdf, toc_pdf, merged_pdf, final_pdf]

    # 清理残留
    for f in tmp_files:
        if os.path.exists(f):
            try:
                os.chmod(f, 0o777)
                os.remove(f)
            except Exception:
                pass

    try:
        if stop_event and stop_event.is_set():
            return

        print(f"\n 扫描目录：{input_folder}")
        custom_order = config.advanced.file_order if config.advanced.file_order else None
        items, root_name = collect_file_tree(input_folder, config, custom_order)

        if stop_event and stop_event.is_set():
            return

        # 1. 封面
        print("\n 生成封面…")
        cover_config = config.cover
        if cover_config.main_title_use_folder:
            cover_config.title_text = root_name
        cover_pages = generate_cover_pdf(cover_config, root_name, cover_pdf)

        if stop_event and stop_event.is_set():
            return

        # 2. 合并正文
        print("\n 合并正文 PDF…")
        pagination, content_pages = merge_content(items, content_pdf, config)

        if stop_event and stop_event.is_set():
            return

        # 3. 目录
        print("\n 生成目录…")
        toc_pages = generate_toc(toc_pdf, items, pagination, root_name, config)
        print(f"   目录共 {toc_pages} 页")

        if stop_event and stop_event.is_set():
            return

        # 4. 目录 + 正文合并
        with Pdf.open(toc_pdf) as t, Pdf.open(content_pdf) as b:
            merged = Pdf.new()
            merged.pages.extend(t.pages)
            merged.pages.extend(b.pages)
            merged.save(merged_pdf, encryption=False)

        if stop_event and stop_event.is_set():
            return

        # 5. 页码
        pn = config.page_num
        if pn.enabled:
            print("\n 添加页码…")
            if config.advanced.enable_image_convert:
                add_page_numbers_image_mode(merged_pdf, final_pdf, toc_pages, config)
            else:
                add_page_numbers(merged_pdf, final_pdf, toc_pages, config)
        else:
            shutil.copy(merged_pdf, final_pdf)
            print("[i]  页码已禁用，跳过")

        if stop_event and stop_event.is_set():
            return

        # 6. 插入封面
        print("\n  插入封面…")
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with Pdf.open(cover_pdf) as cov, Pdf.open(final_pdf) as body:
            out = Pdf.new()
            out.pages.extend(cov.pages)
            out.pages.extend(body.pages)
            out.save(output_file, encryption=False)

        print(f"""
╔==================================================╗
║    处理完成
╠==================================================╣
║  封面：{cover_pages} 页
║  目录：{toc_pages} 页
║  正文：{content_pages} 页
║  输出：{os.path.abspath(output_file)}
╚==================================================╝
""")

    except Exception as e:
        raise RuntimeError(f"[X] 处理失败：{e}") from e

    finally:
        for f in tmp_files:
            if os.path.exists(f):
                try:
                    os.chmod(f, 0o777)
                    os.remove(f)
                except Exception as ex:
                    print(f"[!] 清理 {f} 失败：{ex}")
        cleanup_temp()


def get_subfolders(path, config: AppConfig):
    """返回路径下所有子文件夹名称列表。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"[X] 路径不存在：{path}")
    folders = [n for n in os.listdir(path) if os.path.isdir(os.path.join(path, n))]
    return sorted(folders, key=lambda s: smart_sort_key(s, config))


def process_single_merge(input_folder, output_file, config: AppConfig, stop_event=None):
    """将整个文件夹（含所有子文件夹）合并为一个 PDF。"""
    from cover import generate_cover_pdf

    script_dir = os.path.dirname(os.path.abspath(__file__))
    cover_pdf = os.path.join(script_dir, "_cover_tmp.pdf")
    content_pdf = os.path.join(script_dir, "_content_tmp.pdf")
    toc_pdf = os.path.join(script_dir, "_toc_tmp.pdf")
    merged_pdf = os.path.join(script_dir, "_merged_tmp.pdf")
    final_pdf = os.path.join(script_dir, "_final_tmp.pdf")
    tmp_files = [cover_pdf, content_pdf, toc_pdf, merged_pdf, final_pdf]

    # 清理残留
    for f in tmp_files:
        if os.path.exists(f):
            try:
                os.chmod(f, 0o777)
                os.remove(f)
            except Exception:
                pass

    try:
        if stop_event and stop_event.is_set():
            return

        print(f"\n 扫描目录（整体合并）：{input_folder}")
        custom_order = config.advanced.file_order if config.advanced.file_order else None
        items, root_name = collect_file_tree(input_folder, config, custom_order)

        if stop_event and stop_event.is_set():
            return

        # 1. 封面
        print("\n 生成封面…")
        cover_config = config.cover
        if cover_config.main_title_use_folder:
            cover_config.title_text = root_name
        cover_pages = generate_cover_pdf(cover_config, root_name, cover_pdf)

        if stop_event and stop_event.is_set():
            return

        # 2. 合并正文
        print("\n 合并正文…")
        pagination, content_pages = merge_content(items, content_pdf, config)

        if stop_event and stop_event.is_set():
            return

        # 3. 目录
        print("\n 生成目录…")
        toc_pages = generate_toc(toc_pdf, items, pagination, root_name, config)
        print(f"   目录共 {toc_pages} 页")

        if stop_event and stop_event.is_set():
            return

        # 4. 目录 + 正文合并
        with Pdf.open(toc_pdf) as t, Pdf.open(content_pdf) as b:
            merged = Pdf.new()
            merged.pages.extend(t.pages)
            merged.pages.extend(b.pages)
            merged.save(merged_pdf, encryption=False)

        if stop_event and stop_event.is_set():
            return

        # 5. 页码
        pn = config.page_num
        if pn.enabled:
            print("\n 添加页码…")
            if config.advanced.enable_image_convert:
                add_page_numbers_image_mode(merged_pdf, final_pdf, toc_pages, config)
            else:
                add_page_numbers(merged_pdf, final_pdf, toc_pages, config)
        else:
            shutil.copy(merged_pdf, final_pdf)
            print("[i]  页码已禁用，跳过")

        if stop_event and stop_event.is_set():
            return

        # 6. 插入封面
        print("\n  插入封面…")
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with Pdf.open(cover_pdf) as cov, Pdf.open(final_pdf) as body:
            out = Pdf.new()
            out.pages.extend(cov.pages)
            out.pages.extend(body.pages)
            out.save(output_file, encryption=False)

        print(f"""
╔==================================================╗
║    整体合并完成
╠==================================================╣
║  封面：{cover_pages} 页
║  目录：{toc_pages} 页
║  正文：{content_pages} 页
║  输出：{os.path.abspath(output_file)}
╚==================================================╝
""")

    except Exception as e:
        raise RuntimeError(f"[X] 整体合并失败：{e}") from e

    finally:
        for f in tmp_files:
            if os.path.exists(f):
                try:
                    os.chmod(f, 0o777)
                    os.remove(f)
                except Exception as ex:
                    print(f"[!] 清理 {f} 失败：{ex}")
        cleanup_temp()
