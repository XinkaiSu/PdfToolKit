# =============================================================================
#  methods/sort.py — 中文排序 + 自然排序
# =============================================================================

import re

from config import AppConfig


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


_ARABIC_ORDER_RE = re.compile(
    r"^(?:"
    r"第(\d+)[章节条款]"
    r"|[（(](\d+)[）)]"
    r"|(\d+)[、．.\s_\-]"
    r")"
)


# 多级编号（1.2.3 / 1.2.3、 / 1.2.3 等）
_MULTI_LEVEL_RE = re.compile(
    r"^\d+(?:\.\d+){1,}[、．.\s_\-]?"
)


def strip_original_numbering(name: str) -> str:
    """递归删除文件/文件夹名开头的原有编号前缀。

    依次匹配并剥离：多级编号(1.2.3) → 阿拉伯编号(1、/第1章/(1)) → 中文编号(一、/第一章/（一）)。
    多次循环直到再无匹配，可处理嵌套场景如 "1.2 一、xxx"。
    """
    if not name:
        return name
    prev = None
    cur = name
    while prev != cur:
        prev = cur
        # 1) 多级编号
        m = _MULTI_LEVEL_RE.match(cur)
        if m:
            cur = cur[m.end():].lstrip()
            continue
        # 2) 阿拉伯编号
        m = _ARABIC_ORDER_RE.match(cur)
        if m:
            cur = cur[m.end():].lstrip()
            continue
        # 3) 中文编号
        m = _CN_ORDER_RE.match(cur)
        if m:
            cur = cur[m.end():].lstrip()
            continue
    return cur or name


def chinese_sort_key(s: str) -> tuple:
    """解析文件名开头的中文/阿拉伯序号，返回排序键。"""
    m = _CN_ORDER_RE.match(s)
    if m:
        cn_str = m.group(1) or m.group(2) or m.group(3)
        num = _cn_to_int(cn_str)
        rest = s[m.end():]
        return (num if num >= 0 else float("inf"), natural_sort_key(rest))
    # 尝试匹配阿拉伯数字前缀（与中文编号使用相同分隔符）
    m = _ARABIC_ORDER_RE.match(s)
    if m:
        num = int(m.group(1) or m.group(2) or m.group(3))
        rest = s[m.end():]
        return (num, natural_sort_key(rest))
    return (float("inf"), natural_sort_key(s))


def natural_sort_key(s: str) -> list:
    """自然排序键，使 '2' < '10'。"""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", s)]


def smart_sort_key(s: str, config: AppConfig):
    """智能排序键：优先中文序号或纯自然排序。"""
    if config.advanced.enable_chinese_sort:
        return chinese_sort_key(s)
    return (float("inf"), natural_sort_key(s))
