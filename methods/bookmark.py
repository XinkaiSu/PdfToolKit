# =============================================================================
#  methods/bookmark.py — PDF 书签
# =============================================================================

import os
import shutil
import tempfile

import pikepdf
from pikepdf import Pdf

from config import AppConfig
from methods.sort import strip_original_numbering


def _resolve_bookmark_page(pdf, item):
    """解析书签目标页码，返回 0-based 页索引，无法解析则返回 -1。"""
    try:
        dest = item.destination
        if dest is not None:
            page_obj = dest[0]
            return pdf.pages.index(page_obj)
    except Exception:
        pass
    try:
        if item.dest is not None:
            dest_obj = pdf.get_destination(item.dest)
            if dest_obj is not None:
                page_obj = dest_obj[0]
                return pdf.pages.index(page_obj)
    except Exception:
        pass
    return -1


def _walk_outline(pdf, items, page_offset, level, level_offset, result):
    """递归遍历源 PDF 书签树，收集书签条目。"""
    for item in items:
        page_idx = _resolve_bookmark_page(pdf, item)
        if page_idx >= 0:
            result.append({
                "title": str(item.title),
                "page_index": page_idx + page_offset,
                "level": level + level_offset,
            })
        if item.children:
            _walk_outline(pdf, item.children, page_offset, level + 1, level_offset, result)


def extract_source_bookmarks(pdf_path, page_offset, level_offset=0):
    """从源 PDF 提取书签，页码按 page_offset 偏移，层级按 level_offset 偏移。

    Args:
        pdf_path: 源 PDF 路径
        page_offset: 该 PDF 在合并文档中的起始页（0-based）
        level_offset: 层级偏移量（源PDF书签作为文件书签的子级）

    Returns:
        书签条目列表 [{"title", "page_index", "level"}, ...]
    """
    result = []
    try:
        with Pdf.open(pdf_path) as pdf:
            with pdf.open_outline() as outline:
                if outline.root:
                    _walk_outline(pdf, outline.root, page_offset, 1, level_offset, result)
    except Exception as e:
        print(f"    [!] 提取书签失败 {os.path.basename(pdf_path)}：{e}")
    return result


def build_tree_bookmarks(items, pagination, page_offset, config):
    """从文件树结构构建书签条目。

    Args:
        items: collect_file_tree 返回的扁平条目列表
        pagination: {path: 1-based 内容页码} 来自 merge_content
        page_offset: 封面+目录总页数，用于将内容页码转为最终页索引
        config: AppConfig

    Returns:
        书签条目列表 [{"title", "page_index", "level"}, ...]
    """
    bm = config.bookmark
    result = []

    for item in items:
        if item["type"] == "folder":
            if not bm.folder_as_bookmark:
                continue
            if item["level"] == 0:
                continue  # 跳过根节点
            if item["level"] > bm.max_folder_depth:
                continue
        elif item["type"] == "file":
            if not bm.filename_as_bookmark:
                continue
        else:
            continue

        # 获取页码
        page_1based = pagination.get(item["path"])
        if page_1based is None:
            continue
        page_index = page_1based - 1 + page_offset  # 转为 0-based 最终页索引

        result.append({
            "title": (strip_original_numbering(item["name"])
                      if config.numbering.remove_original else item["name"]),
            "page_index": page_index,
            "level": item["level"],
        })

    return result


def _apply_outline_counts(item, default_open):
    """递归设置书签的 count 属性（展开/折叠状态）。"""
    n = 0
    for child in item.children:
        n += 1 + _apply_outline_counts(child, default_open)
    if n > 0:
        item.count = n if default_open else -n
    return n


def add_bookmarks_to_pdf(pdf_path, items, pagination,
                         cover_pages, toc_pages, source_offsets, config):
    """向合并后的 PDF 添加书签。

    Args:
        pdf_path: 最终输出 PDF 路径（封面+目录+正文+页码）
        items: collect_file_tree 的扁平条目列表
        pagination: {path: 1-based 内容页码}
        cover_pages: 封面页数
        toc_pages: 目录页数
        source_offsets: {pdf_path: 0-based 内容起始页偏移}
        config: AppConfig
    """
    bm = config.bookmark
    page_offset = cover_pages + toc_pages

    all_bookmarks = []

    # 构建 path → level 映射，用于源书签层级偏移
    path_level = {item["path"]: item["level"] for item in items}

    # 收集源 PDF 书签（层级调整为文件级别的下一级）
    if bm.preserve_source:
        for src_path, src_offset in source_offsets.items():
            if not src_path.lower().endswith(".pdf"):
                continue
            file_level = path_level.get(src_path, 1)
            level_offset = file_level  # 源书签第1级 → 文件level+1
            src_bookmarks = extract_source_bookmarks(
                src_path, src_offset + page_offset, level_offset,
            )
            all_bookmarks.extend(src_bookmarks)

    # 收集文件树书签
    if bm.folder_as_bookmark or bm.filename_as_bookmark:
        tree_bookmarks = build_tree_bookmarks(items, pagination, page_offset, config)
        all_bookmarks.extend(tree_bookmarks)

    if not all_bookmarks:
        print("    [i] 无书签可添加")
        return

    # 按页码和层级排序
    all_bookmarks.sort(key=lambda b: (b["page_index"], b["level"]))

    # 写入 PDF（先保存到临时文件，再替换原文件）
    bm_tmp_dir = os.path.join(os.path.expanduser("~"), ".pdftoolkit")
    os.makedirs(bm_tmp_dir, exist_ok=True)
    fd, bookmark_tmp = tempfile.mkstemp(suffix=".pdf", dir=bm_tmp_dir)
    os.close(fd)

    try:
        with Pdf.open(pdf_path) as pdf:
            with pdf.open_outline() as outline:
                stack = []  # (level, OutlineItem)

                for entry in all_bookmarks:
                    page_idx = entry["page_index"]
                    if page_idx < 0 or page_idx >= len(pdf.pages):
                        continue

                    dest = pikepdf.Array([pdf.pages[page_idx].obj, pikepdf.Name.Fit])
                    oi = pikepdf.OutlineItem(
                        title=entry["title"],
                        destination=dest,
                    )

                    # 栈算法：找到正确的父节点
                    while stack and stack[-1][0] >= entry["level"]:
                        stack.pop()

                    if not stack:
                        outline.root.append(oi)
                    else:
                        stack[-1][1].children.append(oi)

                    stack.append((entry["level"], oi))

                # 设置展开/折叠状态
                for root_item in outline.root:
                    _apply_outline_counts(root_item, bm.folder_open)

            pdf.save(bookmark_tmp, encryption=False)

        shutil.copy2(bookmark_tmp, pdf_path)
    finally:
        try:
            os.unlink(bookmark_tmp)
        except Exception:
            pass
