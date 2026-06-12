# =============================================================================
#  methods/blankpage.py — 空白页检测与删除
#  两层检测：结构检测（内容流） + 像素检测（渲染后白度）
# =============================================================================

import fitz  # PyMuPDF

# 像素白度阈值，RGB 各通道 ≥ 此值视为白色
_WHITE_THRESHOLD = 250
# 渲染 DPI，低分辨率即可判断空白
_RENDER_DPI = 72


def is_blank_page(page: fitz.Page) -> bool:
    """判断单页是否为空白页。

    第一层：结构检测 — 无 /Contents 即为空白。
    第二层：像素检测 — 渲染后检查是否几乎全白。
    """
    # 第一层：结构检测
    xref = page.xref
    if xref == 0:
        return True
    contents = page.get_contents()
    if not contents:
        return True

    # 第二层：像素检测
    pix = page.get_pixmap(dpi=_RENDER_DPI)
    samples = pix.samples  # RGB 或 RGBX 字节数组
    n_channels = pix.n  # 每像素通道数（3=RGB, 4=RGBX）

    # 逐像素检查，遇到非白像素立即返回
    for i in range(0, len(samples), n_channels):
        for c in range(min(n_channels, 3)):  # 只检查 R/G/B
            if samples[i + c] < _WHITE_THRESHOLD:
                return False
    return True


def remove_blank_pages(pdf_path: str, output_path: str) -> tuple:
    """删除 PDF 中的空白页，返回 (删除页数, 被删除页的0-based索引列表)。"""
    removed_indices = []

    with fitz.open(pdf_path) as doc:
        for i in range(len(doc)):
            if is_blank_page(doc[i]):
                removed_indices.append(i)

        if not removed_indices:
            return 0, []

        # 从后往前删除，避免索引偏移
        for i in reversed(removed_indices):
            doc.delete_page(i)
        doc.save(output_path, garbage=4, deflate=True)

    return len(removed_indices), removed_indices


def adjust_page_mapping(pagination: dict, source_offsets: dict,
                        removed_indices: list, total_pages: int) -> int:
    """根据被删除的页调整页码映射，返回新的总页数。

    pagination: {路径: 起始页号（1-based）}
    source_offsets: {路径: 起始页偏移（0-based）}
    removed_indices: 被删除页的0-based索引（已排序）
    """
    if not removed_indices:
        return total_pages

    # 为每个 0-based 页码计算它前面有多少被删除的页
    removed_set = set(removed_indices)

    def shift_before(page_0based: int) -> int:
        """计算该页前面有多少被删除页。"""
        return sum(1 for r in removed_indices if r < page_0based)

    new_total = total_pages - len(removed_indices)

    # 调整 pagination（1-based）
    for path in pagination:
        old_page = pagination[path]  # 1-based
        old_0 = old_page - 1
        if old_0 in removed_set:
            # 该条目对应的起始页被删除了，需要找下一个未被删除的页
            # 但这种情况极少发生（文件夹起始页一般是第一页），保守处理
            shift = shift_before(old_0)
        else:
            shift = shift_before(old_0)
        pagination[path] = old_page - shift

    # 调整 source_offsets（0-based）
    for path in source_offsets:
        old_0 = source_offsets[path]
        if old_0 in removed_set:
            shift = shift_before(old_0)
        else:
            shift = shift_before(old_0)
        source_offsets[path] = old_0 - shift

    return new_total
