# =============================================================================
#  methods/merge.py — 文件结构收集 + 内容合并
# =============================================================================

import os

from pikepdf import Pdf

from config import AppConfig
from methods.fonts import clean_text
from methods.sort import smart_sort_key
from methods.convert import convert_pdf_to_a4, convert_pdf_to_a4_memory, make_temp_file, image_to_pdf


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
        """根据 custom_order 重排条目。
        所有条目均能匹配时使用自定义顺序，否则回退默认智能排序。
        """
        if not custom_order or path not in custom_order:
            return entries
        order_list = custom_order[path]
        order_map = {name: i for i, name in enumerate(order_list)}
        matched = []
        for raw, cln in entries:
            if raw in order_map:
                matched.append((order_map[raw], raw, cln))
        # 有条目无法匹配（文件名变更/新增/删除），回退默认排序
        if len(matched) != len(entries):
            return sorted(entries, key=lambda x: smart_sort_key(x[0], config))
        matched.sort(key=lambda x: x[0])
        return [(raw, cln) for _, raw, cln in matched]

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
#  合并正文 PDF
# =============================================================================

def merge_content(items, output_path, config: AppConfig):
    """合并所有 PDF/图片文件，返回 (pagination, total_pages, source_offsets)。"""
    pagination = {}
    folder_first_page = {}
    source_offsets = {}  # 每个源PDF在合并后内容中的起始页（0-based）
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
            source_offsets[item["path"]] = current_page - 1
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

    # 流式合并：逐个 A4 转换后直接 extend，无需中间文件
    merger = Pdf.new()
    for item, pdf_path in valid_items:
        converted = convert_pdf_to_a4_memory(pdf_path)
        merger.pages.extend(converted.pages)
        converted.close()
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

    return pagination, current_page - 1, source_offsets
