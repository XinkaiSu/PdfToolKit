# =============================================================================
#  methods — 功能方法包
#  按 PDF 处理领域拆分，core.py 仅保留编排逻辑
# =============================================================================

from methods.fonts import register_fonts, get_fallback_font, resolve_font, clean_text, wrap_text
from methods.sort import smart_sort_key, chinese_sort_key, natural_sort_key
from methods.convert import convert_pdf_to_a4, image_to_pdf, make_temp_file, cleanup_temp
from methods.merge import collect_file_tree, merge_content
from methods.toc import generate_toc
from methods.pagenum import add_page_numbers, add_page_numbers_image_mode
from methods.bookmark import add_bookmarks_to_pdf, extract_source_bookmarks, build_tree_bookmarks
from methods.cover import generate_cover_pdf, generate_cover_preview
