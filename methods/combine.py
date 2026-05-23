# =============================================================================
#  methods/combine.py — 多段重叠 PDF 智能拼接
#  将同一份材料的多个分段 PDF（相邻段有重叠）自动排序并拼接为完整 PDF
# =============================================================================

import io
import os
import sys
import argparse
import itertools
import tempfile

import numpy as np
from pathlib import Path
from PIL import Image
from pikepdf import Pdf

from config import CombineConfig


# =============================================================================
#  PDF 渲染
# =============================================================================

def pdf_to_images(pdf_path: str, dpi: int = 200) -> list[Image.Image]:
    """将 PDF 每页转换为 PIL Image（RGB），使用 PyMuPDF，无需 Poppler。"""
    import fitz
    doc = fitz.open(pdf_path)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages.append(img)
    doc.close()
    return pages


def pil_to_gray_np(img: Image.Image) -> np.ndarray:
    """将 PIL Image 转为灰度 numpy 数组。"""
    return np.array(img.convert("L"))


def remove_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """将白色背景设为透明，只保留主体内容。返回 RGBA 图像。"""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    # 直接从 RGBA 的 R/G/B 通道计算灰度，避免额外 convert("L")
    gray_from_rgba = arr[:, :, :3].mean(axis=2)
    mask = gray_from_rgba >= threshold
    arr[mask, 3] = 0
    return Image.fromarray(arr)


def crop_whitespace(img: Image.Image, threshold: int = 240, padding: int = 5) -> tuple[Image.Image, int, int, int, int]:
    """
    裁切图像四周的空白区域（白/近白像素）。
    返回 (裁切后图像, left_crop, top_crop, right_crop, bottom_crop)，
    其中 *_crop 为原图中被裁掉的像素数，可用于偏移量修正。
    """
    gray = np.array(img.convert("L"))
    mask = gray < threshold
    if not mask.any():
        return img, 0, 0, 0, 0
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    r0, r1 = np.where(rows)[0][[0, -1]]
    c0, c1 = np.where(cols)[0][[0, -1]]
    r0 = max(0, r0 - padding)
    c0 = max(0, c0 - padding)
    r1 = min(img.height - 1, r1 + padding)
    c1 = min(img.width - 1, c1 + padding)
    cropped = img.crop((c0, r0, c1 + 1, r1 + 1))
    return cropped, c0, r0, img.width - c1 - 1, img.height - r1 - 1


def prepare_for_matching(img_gray: np.ndarray, threshold: int = 240) -> np.ndarray:
    """为匹配准备灰度图：将白色背景替换为内容均值，使 NCC 不受白色区域干扰。"""
    result = img_gray.copy().astype(np.float64)
    mask = img_gray >= threshold
    if mask.any() and (~mask).any():
        mean_val = result[~mask].mean()
        result[mask] = mean_val
    return result.astype(np.uint8)


# =============================================================================
#  重叠检测
# =============================================================================

def compute_overlap_score(strip_top: np.ndarray, strip_bot: np.ndarray) -> float:
    """归一化互相关 (NCC) 评分，范围 [-1, 1]，1 = 完全匹配。"""
    if strip_top.shape != strip_bot.shape or strip_top.size == 0:
        return -1.0
    a = strip_top.astype(np.float64).ravel()
    b = strip_bot.astype(np.float64).ravel()
    a = a - a.mean()
    b = b - b.mean()
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.0  # 无信号（纯色/白纸），视为不相关
    return float(np.dot(a, b) / (norm_a * norm_b))


def ncc_2d(template: np.ndarray, image: np.ndarray) -> np.ndarray:
    """
    用 FFT 计算归一化互相关 (NCC)，一次返回所有偏移的得分矩阵。
    template: 较小的搜索模板 (h_t × w_t)，float64
    image: 较大的搜索图像 (h_i × w_i)，float64
    返回: (h_i - h_t + 1) × (w_i - w_t + 1) 的 NCC 得分矩阵
    """
    h_t, w_t = template.shape
    h_i, w_i = image.shape

    t_mean = template.mean()
    t_centered = template - t_mean
    t_norm = np.linalg.norm(t_centered)
    if t_norm < 1e-6:
        return np.zeros((h_i - h_t + 1, w_i - w_t + 1))

    fft_h, fft_w = h_i, w_i

    t_fft = np.fft.rfft2(t_centered, s=(fft_h, fft_w))
    i_fft = np.fft.rfft2(image, s=(fft_h, fft_w))
    cross_corr = np.fft.irfft2(t_fft * i_fft.conj(), s=(fft_h, fft_w))

    ones = np.ones((h_t, w_t), dtype=np.float64)
    ones_fft = np.fft.rfft2(ones, s=(fft_h, fft_w))
    local_sum = np.fft.irfft2(i_fft * ones_fft.conj(), s=(fft_h, fft_w))

    i2_fft = np.fft.rfft2(image ** 2, s=(fft_h, fft_w))
    local_sq_sum = np.fft.irfft2(i2_fft * ones_fft.conj(), s=(fft_h, fft_w))

    n_pixels = h_t * w_t
    local_mean = local_sum / n_pixels
    local_var = local_sq_sum / n_pixels - local_mean ** 2
    local_var = np.maximum(local_var, 0)
    local_std_sum = np.sqrt(local_var * n_pixels)

    ncc = (cross_corr - n_pixels * t_mean * local_mean) / (t_norm * local_std_sum + 1e-10)

    result_h = h_i - h_t + 1
    result_w = w_i - w_t + 1
    return ncc[:result_h, :result_w]


def find_overlap_rows(img_top_gray: np.ndarray, img_bot_gray: np.ndarray,
                      min_overlap: int = 20, max_overlap_ratio: float = 0.7,
                      coarse_step: int = 2, refine_range: int = 30) -> tuple[int, float]:
    """
    在 img_top 底部和 img_bot 顶部间寻找最佳重叠行数。
    两阶段搜索：1D 行均值互相关粗搜索 + 2D NCC 逐像素精修。
    返回 (重叠像素数, NCC 得分)。
    """
    h_top = img_top_gray.shape[0]
    h_bot = img_bot_gray.shape[0]
    w = min(img_top_gray.shape[1], img_bot_gray.shape[1])

    max_overlap = int(min(h_top, h_bot) * max_overlap_ratio)
    if max_overlap < min_overlap:
        return 0, 0.0

    # 粗搜索：1D 行均值互相关（速度快，容忍微小偏移）
    top_profile = img_top_gray[:, :w].mean(axis=1).astype(np.float64)
    bot_profile = img_bot_gray[:, :w].mean(axis=1).astype(np.float64)

    best_score_1d, best_ov_coarse = -1.0, min_overlap
    for ov in range(min_overlap, max_overlap + 1, coarse_step):
        tp = top_profile[-ov:]
        bp = bot_profile[:ov]
        tp_n = tp - tp.mean()
        bp_n = bp - bp.mean()
        n_tp = np.linalg.norm(tp_n)
        n_bp = np.linalg.norm(bp_n)
        if n_tp < 1e-6 or n_bp < 1e-6:
            continue
        score = float(np.dot(tp_n, bp_n) / (n_tp * n_bp))
        if score > best_score_1d:
            best_score_1d, best_ov_coarse = score, ov

    # 精修：在粗搜索最佳值 ±refine_range 范围内逐像素 2D NCC 搜索
    lo = max(min_overlap, best_ov_coarse - refine_range)
    hi = min(max_overlap, best_ov_coarse + refine_range)
    best_score_fine, best_ov = -1.0, best_ov_coarse
    for ov in range(lo, hi + 1):
        score = compute_overlap_score(img_top_gray[-ov:, :w], img_bot_gray[:ov, :w])
        if score > best_score_fine:
            best_score_fine, best_ov = score, ov

    # 置信度阈值：NCC < 0.3 视为不可靠，返回 0
    if best_score_fine < 0.3:
        return 0, best_score_fine

    return best_ov, best_score_fine


def find_offset_2d(img_top_gray: np.ndarray, img_bot_gray: np.ndarray,
                   min_overlap: int = 20, max_overlap_ratio: float = 0.7,
                   coarse_step: int = 2, refine_range: int = 30,
                   max_dx: int = 200) -> tuple[int, int, float]:
    """
    查找两张图片的 2D 偏移量 (dx, dy)。
    使用 1/2 降采样粗搜索 + 原始分辨率精修，大幅提速。
    dx: img_bot 相对 img_top 的水平偏移（正=右移）
    dy: img_bot 相对 img_top 的垂直偏移（正=下移）
    返回 (dx, dy, NCC 得分)。
    """
    # ── 降采样到 1/2 分辨率做粗搜索 ──
    MATCH_SCALE = 2
    top_small = img_top_gray[::MATCH_SCALE, ::MATCH_SCALE]
    bot_small = img_bot_gray[::MATCH_SCALE, ::MATCH_SCALE]

    top_m = prepare_for_matching(top_small)
    bot_m = prepare_for_matching(bot_small)

    h_top_s, h_bot_s = top_m.shape[0], bot_m.shape[0]
    w_s = min(top_m.shape[1], bot_m.shape[1])

    max_overlap_s = int(min(h_top_s, h_bot_s) * max_overlap_ratio)
    min_ov_s = min_overlap // MATCH_SCALE
    if max_overlap_s < min_ov_s:
        return 0, img_top_gray.shape[0], 0.0

    # 1. 粗搜索垂直重叠（1D 行均值 NCC，降采样分辨率）
    top_profile = top_m[:, :w_s].mean(axis=1).astype(np.float64)
    bot_profile = bot_m[:, :w_s].mean(axis=1).astype(np.float64)

    best_score_v, best_ov_s = -1.0, min_ov_s
    for ov in range(min_ov_s, max_overlap_s + 1, coarse_step):
        tp = top_profile[-ov:]
        bp = bot_profile[:ov]
        tp_n, bp_n = tp - tp.mean(), bp - bp.mean()
        n_tp, n_bp = np.linalg.norm(tp_n), np.linalg.norm(bp_n)
        if n_tp < 1e-6 or n_bp < 1e-6:
            continue
        score = float(np.dot(tp_n, bp_n) / (n_tp * n_bp))
        if score > best_score_v:
            best_score_v, best_ov_s = score, ov

    # 2. 在降采样重叠区域内查找水平偏移（1D 列均值 NCC）
    top_overlap = top_m[-best_ov_s:, :w_s]
    bot_overlap = bot_m[:best_ov_s, :w_s]
    top_col = top_overlap.mean(axis=0).astype(np.float64)
    bot_col = bot_overlap.mean(axis=0).astype(np.float64)

    actual_max_dx_s = min(max_dx // MATCH_SCALE, w_s // 4)
    best_dx_s, best_dx_score = 0, -1.0
    for dx in range(-actual_max_dx_s, actual_max_dx_s + 1):
        if dx >= 0:
            tc, bc = top_col[dx:], bot_col[:w_s - dx]
        else:
            tc, bc = top_col[:w_s + dx], bot_col[-dx:]
        if len(tc) < 10:
            continue
        tc_n, bc_n = tc - tc.mean(), bc - bc.mean()
        n_tc, n_bc = np.linalg.norm(tc_n), np.linalg.norm(bc_n)
        if n_tc < 1e-6 or n_bc < 1e-6:
            continue
        score = float(np.dot(tc_n, bc_n) / (n_tc * n_bc))
        if score > best_dx_score:
            best_dx_score, best_dx_s = score, dx

    # 3. 降采样 2D NCC 精修
    dy_coarse_s = h_top_s - best_ov_s
    refine_s = max(10, refine_range // MATCH_SCALE)
    lo_dy_s = max(0, dy_coarse_s - refine_s)
    hi_dy_s = min(h_top_s, dy_coarse_s + refine_s)
    lo_dx_s = max(-actual_max_dx_s, best_dx_s - refine_s)
    hi_dx_s = min(actual_max_dx_s, best_dx_s + refine_s)

    best_score_2d, best_dx_s_f, best_dy_s_f = -1.0, best_dx_s, dy_coarse_s
    for test_dy in range(lo_dy_s, hi_dy_s + 1, 2):
        ov_rows = h_top_s - test_dy
        if ov_rows < min_ov_s or ov_rows > max_overlap_s:
            continue
        for test_dx in range(lo_dx_s, hi_dx_s + 1, 2):
            if test_dx >= 0:
                ts = top_m[-ov_rows:, test_dx:]
                bs = bot_m[:ov_rows, :bot_m.shape[1] - test_dx]
            else:
                ts = top_m[-ov_rows:, :top_m.shape[1] + test_dx]
                bs = bot_m[:ov_rows, -test_dx:]
            min_w = min(ts.shape[1], bs.shape[1])
            if min_w < 10:
                continue
            score = compute_overlap_score(ts[:, :min_w], bs[:, :min_w])
            if score > best_score_2d:
                best_score_2d, best_dx_s_f, best_dy_s_f = score, test_dx, test_dy

    # ── 映射回原始分辨率，±2px 精修 ──
    coarse_dx = best_dx_s_f * MATCH_SCALE
    coarse_dy = best_dy_s_f * MATCH_SCALE

    top_full = prepare_for_matching(img_top_gray)
    bot_full = prepare_for_matching(img_bot_gray)
    h_top_f = top_full.shape[0]

    best_score_full, best_dx_f, best_dy_f = -1.0, coarse_dx, coarse_dy
    for test_dy in range(max(0, coarse_dy - 2), min(h_top_f, coarse_dy + 3)):
        for test_dx in range(coarse_dx - 2, coarse_dx + 3):
            ts, bs = _extract_overlap(top_full, bot_full, test_dx, test_dy)
            if ts is None:
                continue
            score = compute_overlap_score(ts, bs)
            if score > best_score_full:
                best_score_full, best_dx_f, best_dy_f = score, test_dx, test_dy

    if best_score_full < 0.3:
        return 0, img_top_gray.shape[0], best_score_full

    return best_dx_f, best_dy_f, best_score_full


def find_offset_2d_fft(img_top_gray: np.ndarray, img_bot_gray: np.ndarray,
                        min_overlap: int = 20, max_overlap_ratio: float = 0.7,
                        max_dx: int = 200) -> tuple[int, int, float]:
    """
    FFT 加速的 2D 偏移检测。用降采样 + FFT-NCC 一次算出所有偏移的 NCC，
    选取最优 (dx, dy)，再映射回原始分辨率精修。
    返回 (dx, dy, NCC 得分)。
    """
    MATCH_SCALE = 2
    top_small = img_top_gray[::MATCH_SCALE, ::MATCH_SCALE]
    bot_small = img_bot_gray[::MATCH_SCALE, ::MATCH_SCALE]

    top_m = prepare_for_matching(top_small).astype(np.float64)
    bot_m = prepare_for_matching(bot_small).astype(np.float64)

    h_top_s, h_bot_s = top_m.shape[0], bot_m.shape[0]
    w_s = min(top_m.shape[1], bot_m.shape[1])

    max_overlap_s = int(min(h_top_s, h_bot_s) * max_overlap_ratio)
    min_ov_s = min_overlap // MATCH_SCALE
    if max_overlap_s < min_ov_s:
        return 0, img_top_gray.shape[0], 0.0

    # ── 1D 行均值 NCC 粗搜 dy ──
    top_profile = top_m[:, :w_s].mean(axis=1).astype(np.float64)
    bot_profile = bot_m[:, :w_s].mean(axis=1).astype(np.float64)

    best_score_v, best_ov_s = -1.0, min_ov_s
    for ov in range(min_ov_s, max_overlap_s + 1, 2):
        tp = top_profile[-ov:]
        bp = bot_profile[:ov]
        tp_n, bp_n = tp - tp.mean(), bp - bp.mean()
        n_tp, n_bp = np.linalg.norm(tp_n), np.linalg.norm(bp_n)
        if n_tp < 1e-6 or n_bp < 1e-6:
            continue
        score = float(np.dot(tp_n, bp_n) / (n_tp * n_bp))
        if score > best_score_v:
            best_score_v, best_ov_s = score, ov

    # ── FFT-NCC 2D 精搜 dx+dy ──
    dy_coarse_s = h_top_s - best_ov_s
    refine_s = max(10, 30 // MATCH_SCALE)
    lo_dy_s = max(0, dy_coarse_s - refine_s)
    hi_dy_s = min(h_top_s, dy_coarse_s + refine_s)

    actual_max_dx_s = min(max_dx // MATCH_SCALE, w_s // 4)

    best_score_2d, best_dx_s, best_dy_s = -1.0, 0, dy_coarse_s

    for test_dy in range(lo_dy_s, hi_dy_s + 1, 2):
        ov_rows = h_top_s - test_dy
        if ov_rows < min_ov_s or ov_rows > max_overlap_s:
            continue
        top_strip = top_m[-ov_rows:, :w_s]
        bot_strip = bot_m[:ov_rows, :w_s]

        top_col = top_strip.mean(axis=0).astype(np.float64)
        bot_col = bot_strip.mean(axis=0).astype(np.float64)

        n = len(top_col)
        m = len(bot_col)
        dx_lo = max(-actual_max_dx_s, -n // 2)
        dx_hi = min(actual_max_dx_s, m // 2)

        for test_dx in range(dx_lo, dx_hi + 1, 1):
            if test_dx >= 0:
                tc, bc = top_col[test_dx:], bot_col[:m - test_dx]
            else:
                tc, bc = top_col[:n + test_dx], bot_col[-test_dx:]
            if len(tc) < 10:
                continue
            tc_n, bc_n = tc - tc.mean(), bc - bc.mean()
            n_tc, n_bc = np.linalg.norm(tc_n), np.linalg.norm(bc_n)
            if n_tc < 1e-6 or n_bc < 1e-6:
                continue
            score = float(np.dot(tc_n, bc_n) / (n_tc * n_bc))
            if score > best_score_2d:
                best_score_2d, best_dx_s, best_dy_s = score, test_dx, test_dy

    # ── 原始分辨率 ±2px 精修 ──
    coarse_dx = best_dx_s * MATCH_SCALE
    coarse_dy = best_dy_s * MATCH_SCALE

    top_full = prepare_for_matching(img_top_gray)
    bot_full = prepare_for_matching(img_bot_gray)
    h_top_f = top_full.shape[0]

    best_score_full, best_dx_f, best_dy_f = -1.0, coarse_dx, coarse_dy
    for test_dy in range(max(0, coarse_dy - 2), min(h_top_f, coarse_dy + 3)):
        for test_dx in range(coarse_dx - 2, coarse_dx + 3):
            ts, bs = _extract_overlap(top_full, bot_full, test_dx, test_dy)
            if ts is None:
                continue
            score = compute_overlap_score(ts, bs)
            if score > best_score_full:
                best_score_full, best_dx_f, best_dy_f = score, test_dx, test_dy

    if best_score_full < 0.3:
        return 0, img_top_gray.shape[0], best_score_full

    return best_dx_f, best_dy_f, best_score_full


def auto_sort_segments(segments: list[dict], verbose: bool = True) -> list[dict]:
    """
    给定若干段（每段含 first_page / last_page 灰度图），
    自动确定最优从上到下的排列顺序。
    """
    n = len(segments)
    if n == 1:
        return segments

    if verbose:
        print(f"\n 自动排序 {n} 个文件…")

    score_matrix = np.full((n, n), -1.0)
    overlap_matrix = np.zeros((n, n), dtype=int)

    for i, j in itertools.permutations(range(n), 2):
        ov, sc = find_overlap_rows(
            segments[i]["last_gray"],
            segments[j]["first_gray"],
        )
        score_matrix[i, j] = sc
        overlap_matrix[i, j] = ov
        if verbose:
            print(f"  [{Path(segments[i]['path']).name}] → [{Path(segments[j]['path']).name}]  "
                  f"score={sc:.4f}  overlap={ov}px")

    best_order, best_total = list(range(n)), -999.0
    for start in range(n):
        order = [start]
        used = {start}
        total = 0.0
        while len(order) < n:
            last = order[-1]
            candidates = [(score_matrix[last, j], j) for j in range(n) if j not in used]
            if not candidates:
                break
            sc, nxt = max(candidates)
            order.append(nxt)
            used.add(nxt)
            total += sc
        if total > best_total:
            best_total = total
            best_order = order

    sorted_segs = [segments[i] for i in best_order]
    if verbose:
        names = [Path(s["path"]).name for s in sorted_segs]
        print(f"\n  最优顺序: {' → '.join(names)}  (总分={best_total:.4f})")

    for k in range(len(sorted_segs) - 1):
        i = best_order[k]
        j = best_order[k + 1]
        sorted_segs[k + 1]["overlap_to_prev"] = overlap_matrix[i, j]
        sorted_segs[k + 1]["score_to_prev"] = score_matrix[i, j]

    return sorted_segs


# =============================================================================
#  图像拼接
# =============================================================================

def stitch_two(img_top: Image.Image, img_bot: Image.Image,
               overlap_px: int, feather: int = 40) -> Image.Image:
    """
    垂直拼接两张图，在重叠处做渐变羽化融合。
    img_top 完整保留，img_bot 去掉顶部 overlap_px 行后接在下方。
    """
    w = max(img_top.width, img_bot.width)

    def pad(im):
        if im.width == w:
            return im
        canvas = Image.new("RGB", (w, im.height), (255, 255, 255))
        canvas.paste(im, (0, 0))
        return canvas

    top = pad(img_top)
    bot = pad(img_bot)

    if overlap_px <= 0:
        out = Image.new("RGB", (w, top.height + bot.height), (255, 255, 255))
        out.paste(top, (0, 0))
        out.paste(bot, (0, top.height))
        return out

    bot_body = bot.crop((0, overlap_px, w, bot.height))
    total_h = top.height + bot_body.height
    result = Image.new("RGB", (w, total_h), (255, 255, 255))
    result.paste(top, (0, 0))
    result.paste(bot_body, (0, top.height))

    blend_h = min(feather, overlap_px // 2)
    if blend_h > 1:
        sy = top.height  # 接缝 y 坐标
        top_strip = np.array(result.crop((0, sy - blend_h, w, sy)), dtype=np.float32)
        bot_strip = np.array(result.crop((0, sy, w, sy + blend_h)), dtype=np.float32)
        alpha = np.linspace(1.0, 0.0, blend_h).reshape(-1, 1, 1)
        blended = top_strip * alpha + bot_strip * (1.0 - alpha)
        result.paste(Image.fromarray(blended.clip(0, 255).astype(np.uint8)),
                     (0, sy - blend_h))

    return result


def stitch_all_pages(segments: list[dict], feather: int,
                     manual_overlap: float | None, no_auto: bool,
                     debug: bool = False) -> list[Image.Image]:
    """
    将多段（已排序）的所有页面拼接为最终页面列表。

    每段结构:
        path, pages (list[Image]), first_gray, last_gray,
        overlap_to_prev (int), score_to_prev (float)
    """
    result_pages: list[Image.Image] = []

    for idx, seg in enumerate(segments):
        pages = seg["pages"]

        if idx == 0:
            # 第一段：全部页面加入结果
            if len(segments) == 1:
                result_pages.extend(pages)
            else:
                # 保留除最后一页外的所有页，最后一页留给与下段的拼接
                result_pages.extend(pages[:-1] if len(pages) > 1 else [])
        else:
            # 非第一段：第一页与上一段最后一页拼接
            if no_auto:
                overlap_px = 0
            elif manual_overlap is not None:
                overlap_px = int(segments[idx - 1]["pages"][-1].height * manual_overlap)
                print(f"  手动重叠比例 {manual_overlap:.0%} → {overlap_px} px")
            elif "overlap_to_prev" in seg:
                overlap_px = seg["overlap_to_prev"]
                print(f"  已检测重叠: {overlap_px} px  (score={seg.get('score_to_prev', 0):.4f})")
            else:
                print(f"  临时检测第{idx}段与第{idx + 1}段重叠…")
                gray_a = pil_to_gray_np(segments[idx - 1]["pages"][-1])
                gray_b = pil_to_gray_np(pages[0])
                overlap_px, sc = find_overlap_rows(gray_a, gray_b)
                print(f"  → {overlap_px} px  score={sc:.4f}")

            stitched = stitch_two(segments[idx - 1]["pages"][-1], pages[0],
                                  overlap_px, feather)
            result_pages.append(stitched)

            if debug:
                tmp_dir = os.path.join(os.path.expanduser("~"), ".pdftoolkit")
                os.makedirs(tmp_dir, exist_ok=True)
                dbg_path = os.path.join(tmp_dir, f"debug_stitch_{idx - 1}_{idx}.png")
                stitched.save(dbg_path)
                print(f"  [debug] 保存接缝图: {dbg_path}")

            # 剩余页面（跳过已用于拼接的第一页）
            if idx < len(segments) - 1:
                # 不是最后一段：保留中间页，最后一页留给下次拼接
                result_pages.extend(pages[1:-1] if len(pages) > 2 else [])
            else:
                # 最后一段：全部加入
                result_pages.extend(pages[1:])

    return result_pages


# =============================================================================
#  画布拼接（2D 位置 + 渐变融合）
# =============================================================================

def stitch_on_canvas(images: list[Image.Image],
                     positions: list[tuple[int, int]],
                     feather: int = 40,
                     bg_color: tuple = (255, 255, 255)) -> Image.Image:
    """
    按指定位置将多张图拼接到一张画布上，重叠区做渐变融合。
    images: 原始 RGB 图像列表
    positions: 每张图像左上角在画布上的 (x, y) 坐标
    feather: 融合宽度（像素）
    bg_color: 画布背景色 (R, G, B)
    """
    if not images:
        raise ValueError("无图像可拼接")

    max_x = max(pos[0] + img.width for pos, img in zip(positions, images))
    max_y = max(pos[1] + img.height for pos, img in zip(positions, images))

    canvas = Image.new("RGB", (max_x, max_y), bg_color)

    for i, (img, (x, y)) in enumerate(zip(images, positions)):
        if i == 0:
            canvas.paste(img, (x, y))
            continue

        img_w, img_h = img.width, img.height
        ix1, iy1 = x, y
        ix2, iy2 = x + img_w, y + img_h
        ix1c, iy1c = max(ix1, 0), max(iy1, 0)
        ix2c, iy2c = min(ix2, max_x), min(iy2, max_y)

        if ix1c >= ix2c or iy1c >= iy2c:
            canvas.paste(img, (x, y))
            continue

        canvas_crop = canvas.crop((ix1c, iy1c, ix2c, iy2c))
        img_crop = img.crop((ix1c - x, iy1c - y, ix2c - x, iy2c - y))

        c_arr = np.array(canvas_crop, dtype=np.float32)
        i_arr = np.array(img_crop, dtype=np.float32)
        result_arr = i_arr.copy()

        # 上方重叠区域羽化
        overlap_top = 0
        for j in range(i):
            jx, jy = positions[j]
            jw, jh = images[j].width, images[j].height
            if jy + jh > y and jx < x + img_w and jx + jw > x:
                overlap_top = max(overlap_top, jy + jh - y)
        overlap_top = min(overlap_top, img_h, iy2c - iy1c)
        blend_h = min(feather, overlap_top // 2) if overlap_top > 0 else 0
        if blend_h > 1:
            alpha = np.linspace(0.0, 1.0, blend_h).reshape(-1, 1, 1)
            result_arr[:blend_h] = c_arr[:blend_h] * (1 - alpha) + i_arr[:blend_h] * alpha

        # 左方重叠区域羽化
        overlap_left = 0
        for j in range(i):
            jx, jy = positions[j]
            jw, jh = images[j].width, images[j].height
            if jx + jw > x and jy < y + img_h and jy + jh > y:
                overlap_left = max(overlap_left, jx + jw - x)
        overlap_left = min(overlap_left, img_w, ix2c - ix1c)
        blend_w = min(feather, overlap_left // 2) if overlap_left > 0 else 0
        if blend_w > 1:
            alpha = np.linspace(0.0, 1.0, blend_w).reshape(1, -1, 1)
            result_arr[:, :blend_w] = c_arr[:, :blend_w] * (1 - alpha) + i_arr[:, :blend_w] * alpha

        blended = Image.fromarray(result_arr.clip(0, 255).astype(np.uint8))
        canvas.paste(blended, (ix1c, iy1c))

    # 裁剪背景色边缘
    arr = np.array(canvas)
    bg_arr = np.array(bg_color, dtype=np.float32)
    diff = np.abs(arr.astype(np.float32) - bg_arr).mean(axis=2)
    mask = diff > 5
    if mask.any():
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)
        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]
        canvas = canvas.crop((c0, r0, c1 + 1, r1 + 1))

    return canvas


def preprocess_combine(config: CombineConfig, stop_event=None) -> list[dict]:
    """
    预处理：渲染 PDF → 可选裁切空白 → 去背景 → 检测偏移 → 计算位置。
    返回段列表，每段含:
        path, orig_img (RGB, 可能裁切后), rgba_img (去背景), gray, pages_count,
        crop_offset (left, top) 裁切偏移量,
        offset_to_prev (dx, dy, score)
    """
    input_paths = [p for p in config.input_files if os.path.isfile(p)]
    if len(input_paths) < 2:
        raise RuntimeError("至少需要 2 个输入文件")

    print(" 渲染 PDF 页面…")
    segments = []
    for path in input_paths:
        if stop_event and stop_event.is_set():
            return []
        pages = pdf_to_images(path, dpi=config.dpi)
        if len(pages) == 1:
            orig_img = pages[0]
        else:
            total_h = sum(p.height for p in pages)
            max_w = max(p.width for p in pages)
            orig_img = Image.new("RGB", (max_w, total_h), (255, 255, 255))
            y_off = 0
            for p in pages:
                orig_img.paste(p, (0, y_off))
                y_off += p.height

        # 先做灰度转换（只做一次）
        gray_full = pil_to_gray_np(orig_img)

        crop_offset = (0, 0)
        if config.crop_whitespace:
            # 复用灰度图做裁切检测，避免 crop_whitespace 内部再次 convert("L")
            mask = gray_full < config.bg_threshold
            if mask.any():
                rows = np.any(mask, axis=1)
                cols = np.any(mask, axis=0)
                r0, r1 = np.where(rows)[0][[0, -1]]
                c0, c1 = np.where(cols)[0][[0, -1]]
                padding = 5
                r0 = max(0, r0 - padding)
                c0 = max(0, c0 - padding)
                r1 = min(orig_img.height - 1, r1 + padding)
                c1 = min(orig_img.width - 1, c1 + padding)
                crop_offset = (c0, r0)
                orig_img = orig_img.crop((c0, r0, c1 + 1, r1 + 1))
                gray_full = gray_full[r0:r1+1, c0:c1+1]
            print(f"  ✓ {Path(path).name}  ({len(pages)} 页, "
                  f"裁切后 {orig_img.width}×{orig_img.height}px)")
        else:
            print(f"  ✓ {Path(path).name}  ({len(pages)} 页, "
                  f"{orig_img.width}×{orig_img.height}px)")

        rgba_img = remove_background(orig_img, config.bg_threshold)
        segments.append({
            "path": path,
            "orig_img": orig_img,
            "rgba_img": rgba_img,
            "gray": gray_full,
            "pages_count": len(pages),
            "crop_offset": crop_offset,
        })

    print(" 检测偏移…")
    segments[0]["offset_to_prev"] = (0, 0, 1.0)
    for k in range(1, len(segments)):
        if stop_event and stop_event.is_set():
            return []
        dx, dy, score = find_offset_2d_fft(
            segments[k - 1]["gray"],
            segments[k]["gray"],
        )
        segments[k]["offset_to_prev"] = (dx, dy, score)
        print(f"  段{k}偏移: dx={dx}, dy={dy}, score={score:.4f}")

    return segments


def _extract_overlap(top_gray, bot_gray, dx, dy):
    """根据 (dx, dy) 提取 top/bot 的重叠区域切片。返回 (top_slice, bot_slice) 或 (None, None)。"""
    top_h, top_w = top_gray.shape
    bot_h, bot_w = bot_gray.shape
    overlap_rows = top_h - dy
    if overlap_rows < 20 or overlap_rows > min(top_h, bot_h):
        return None, None
    if dx >= 0:
        ts = top_gray[-overlap_rows:, dx:]
        bs = bot_gray[:overlap_rows, :bot_w - dx] if bot_w - dx > 0 else bot_gray[:overlap_rows, :]
    else:
        ts = top_gray[-overlap_rows:, :top_w + dx] if top_w + dx > 0 else top_gray[-overlap_rows:, :]
        bs = bot_gray[:overlap_rows, -dx:]
    min_w = min(ts.shape[1], bs.shape[1])
    if min_w < 20:
        return None, None
    return ts[:, :min_w], bs[:, :min_w]


def _best_dx_1d(top_overlap, bot_overlap, max_dx):
    """1D 列均值 NCC 粗搜最佳水平偏移。"""
    top_col = top_overlap.mean(axis=0).astype(np.float64)
    bot_col = bot_overlap.mean(axis=0).astype(np.float64)
    w = len(top_col)
    actual_max = min(max_dx, w // 4)
    best_dx, best_score = 0, -1.0
    for dx in range(-actual_max, actual_max + 1, 2):
        if dx >= 0:
            tc, bc = top_col[dx:], bot_col[:w - dx]
        else:
            tc, bc = top_col[:w + dx], bot_col[-dx:]
        if len(tc) < 10:
            continue
        tc_n, bc_n = tc - tc.mean(), bc - bc.mean()
        n_tc, n_bc = np.linalg.norm(tc_n), np.linalg.norm(bc_n)
        if n_tc < 1e-6 or n_bc < 1e-6:
            continue
        score = float(np.dot(tc_n, bc_n) / (n_tc * n_bc))
        if score > best_score:
            best_score, best_dx = score, dx
    return best_dx


def refine_positions(segments: list[dict],
                     canvas_positions: list[tuple[int, int]],
                     refine_range: int = 50) -> list[tuple[int, int]]:
    """
    基于画布粗略位置，在每对相邻段的重叠区域做精细 2D NCC 匹配修正。
    使用降采样粗搜索 + 原始分辨率精修，大幅提速。
    """
    if len(segments) < 2 or len(canvas_positions) < 2:
        return canvas_positions[:]

    MATCH_SCALE = 2
    refined = [canvas_positions[0]]

    for k in range(1, len(segments)):
        prev_x, prev_y = refined[k - 1]
        cur_x, cur_y = canvas_positions[k]

        top_gray = segments[k - 1]["gray"]
        bot_gray = segments[k]["gray"]
        prev_h = top_gray.shape[0]

        # 画布位置给出的粗略偏移
        coarse_dx = cur_x - prev_x
        coarse_dy = cur_y - prev_y

        # ── 降采样粗搜索 ──
        top_small = top_gray[::MATCH_SCALE, ::MATCH_SCALE]
        bot_small = bot_gray[::MATCH_SCALE, ::MATCH_SCALE]
        top_m = prepare_for_matching(top_small)
        bot_m = prepare_for_matching(bot_small)

        small_h = top_m.shape[0]
        small_prev_w = top_m.shape[1]
        small_bot_w = bot_m.shape[1]

        dx_small = coarse_dx // MATCH_SCALE
        dy_small = coarse_dy // MATCH_SCALE
        refine_s = max(10, refine_range // MATCH_SCALE)
        actual_max_dx_s = min(refine_s, min(small_prev_w, small_bot_w) // 4)

        dy_lo_s = max(0, dy_small - refine_s)
        dy_hi_s = min(small_h, dy_small + refine_s)

        best_score, best_dx_s, best_dy_s = -1.0, dx_small, dy_small

        for test_dy in range(dy_lo_s, dy_hi_s + 1, 2):
            if small_h - test_dy < 10:
                continue
            ts_tmp, bs_tmp = _extract_overlap(top_m, bot_m, 0, test_dy)
            if ts_tmp is None:
                continue
            dx_1d = _best_dx_1d(ts_tmp, bs_tmp, actual_max_dx_s)
            for test_dx in range(dx_1d - 4, dx_1d + 5, 1):
                ts, bs = _extract_overlap(top_m, bot_m, test_dx, test_dy)
                if ts is None:
                    continue
                score = compute_overlap_score(ts, bs)
                if score > best_score:
                    best_score, best_dx_s, best_dy_s = score, test_dx, test_dy

        # ── 映射回原始分辨率 ±2px 精修 ──
        coarse_dx_f = best_dx_s * MATCH_SCALE
        coarse_dy_f = best_dy_s * MATCH_SCALE

        top_full = prepare_for_matching(top_gray)
        bot_full = prepare_for_matching(bot_gray)

        best_score_f, best_dx_f, best_dy_f = -1.0, coarse_dx_f, coarse_dy_f
        for test_dy in range(max(0, coarse_dy_f - 2), min(prev_h, coarse_dy_f + 3)):
            if prev_h - test_dy < 20:
                continue
            for test_dx in range(coarse_dx_f - 2, coarse_dx_f + 3):
                ts, bs = _extract_overlap(top_full, bot_full, test_dx, test_dy)
                if ts is None:
                    continue
                score = compute_overlap_score(ts, bs)
                if score > best_score_f:
                    best_score_f, best_dx_f, best_dy_f = score, test_dx, test_dy

        # NCC 得分太低则退回画布位置
        if best_score_f < 0.3:
            new_x, new_y = cur_x, cur_y
            print(f"  段{k}精修: NCC={best_score_f:.4f}过低，保留画布位置"
                  f"({coarse_dx},{coarse_dy})")
        else:
            new_x = prev_x + best_dx_f
            new_y = prev_y + best_dy_f
            print(f"  段{k}精修: 画布偏移({coarse_dx},{coarse_dy}) → "
                  f"精修偏移({best_dx_f},{best_dy_f}) score={best_score_f:.4f}")

        refined.append((new_x, new_y))

    return refined


def compute_positions_from_offsets(segments: list[dict]) -> list[tuple[int, int]]:
    """根据 offset_to_prev 计算每段在画布上的绝对 (x, y) 坐标。"""
    positions = [(0, 0)]
    for seg in segments[1:]:
        dx, dy, _ = seg["offset_to_prev"]
        prev_x, prev_y = positions[-1]
        positions.append((prev_x + dx, prev_y + dy))
    return positions

def save_pages_as_pdf(pages: list[Image.Image], out_path: str, dpi: int):
    """将 PIL Image 列表保存为 PDF（通过 image_to_pdf + pikepdf 合并）。"""
    from methods.convert import image_to_pdf

    tmp_dir = os.path.join(os.path.expanduser("~"), ".pdftoolkit")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_pdfs = []

    for i, page in enumerate(pages):
        fd, png_path = tempfile.mkstemp(suffix=".png", dir=tmp_dir)
        os.close(fd)
        page.save(png_path, "PNG")

        fd, pdf_path = tempfile.mkstemp(suffix=".pdf", dir=tmp_dir)
        os.close(fd)
        if not image_to_pdf(png_path, pdf_path):
            raise RuntimeError(f"[X] 拼图结果第{i + 1}页转PDF失败")
        tmp_pdfs.append(pdf_path)

        try:
            os.unlink(png_path)
        except Exception:
            pass

    merger = Pdf.new()
    for pdf_path in tmp_pdfs:
        with Pdf.open(pdf_path) as f:
            merger.pages.extend(f.pages)
        try:
            os.unlink(pdf_path)
        except Exception:
            pass

    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    merger.save(out_path, encryption=False)


# =============================================================================
#  主流程（可编程调用）
# =============================================================================

def process_combine(config: CombineConfig, stop_event=None,
                    canvas_positions: list[tuple[int, int]] | None = None) -> str:
    """
    GUI 调用入口：渲染→边框裁切→特征识别→2D拼接→保存，返回输出路径。
    canvas_positions: 画布上用户微调后的粗略位置，用于引导精修匹配。
    """
    input_paths = [p for p in config.input_files if os.path.isfile(p)]
    out_path = config.output_path or "merged_output.pdf"

    if len(input_paths) < 2:
        raise RuntimeError("至少需要 2 个输入文件")

    print(f"\n{'=' * 60}")
    print(f"  PDF 多段重叠拼接工具")
    print(f"{'=' * 60}")
    print(f"  输入文件数: {len(input_paths)}")
    for p in input_paths:
        print(f"    • {p}")
    print(f"  输出: {out_path}")
    print(f"  DPI : {config.dpi}  羽化: {config.feather}px  "
          f"裁切: {config.crop_border_mm}mm  阈值: {config.bg_threshold}")
    print()

    # 1. 渲染所有PDF
    if stop_event and stop_event.is_set():
        return ""

    print(" 渲染 PDF 页面…")
    segments = preprocess_combine(config, stop_event=stop_event)
    if not segments or (stop_event and stop_event.is_set()):
        return ""

    # 2. 计算位置：使用画布粗略位置 + 精修匹配
    if stop_event and stop_event.is_set():
        return ""

    if canvas_positions and len(canvas_positions) == len(segments):
        print(" 基于画布位置做精细匹配…")
        positions = refine_positions(segments, canvas_positions)
    else:
        positions = compute_positions_from_offsets(segments)

    for k, (pos, seg) in enumerate(zip(positions, segments)):
        print(f"  段{k+1}位置: ({pos[0]}, {pos[1]})")

    # 3. 拼接
    if stop_event and stop_event.is_set():
        return ""

    print(f"\n 拼接 {len(segments)} 个段落…")
    images = [s["orig_img"] for s in segments]
    bg_color = tuple(config.bg_color) if config.bg_color else (255, 255, 255)
    result = stitch_on_canvas(images, positions, feather=config.feather,
                               bg_color=bg_color)
    print(f"  合并完成，尺寸: {result.width}×{result.height}px")

    # 4. 边框裁切
    if config.crop_border_mm > 0:
        from reportlab.lib.units import mm
        crop_px = int(config.crop_border_mm * mm * config.dpi / 72.0)
        if crop_px > 0:
            w, h = result.width, result.height
            result = result.crop((crop_px, crop_px, w - crop_px, h - crop_px))
            print(f"  裁切边框: {config.crop_border_mm}mm ({crop_px}px)")

    # 5. 保存
    if stop_event and stop_event.is_set():
        return ""

    print(f"\n 保存 → {out_path}")
    save_pages_as_pdf([result], out_path, config.dpi)
    size_kb = Path(out_path).stat().st_size / 1024
    print(f"  文件大小: {size_kb:.1f} KB")
    print(f"\n 完成！  {out_path}\n")

    return out_path


# =============================================================================
#  CLI 入口
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="将多个分段PDF（相邻有重叠）自动排序并拼接为完整PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m methods.combine a.pdf b.pdf c.pdf -o result.pdf
  python -m methods.combine *.pdf -o result.pdf --dpi 300
        """
    )
    parser.add_argument("inputs", nargs="+", help="输入PDF路径")
    parser.add_argument("-o", "--output", default="merged_output.pdf", help="输出PDF")
    parser.add_argument("--dpi", type=int, default=200, help="渲染DPI（默认200）")
    parser.add_argument("--overlap", type=float, default=None, help="手动重叠比例 0~1")
    parser.add_argument("--feather", type=int, default=40, help="羽化像素数（默认40）")
    parser.add_argument("--order", choices=["auto", "manual"], default="auto",
                        help="auto=自动排序（默认），manual=按命令行顺序")
    parser.add_argument("--no-auto", action="store_true", help="跳过重叠检测直接拼接")
    parser.add_argument("--debug", action="store_true", help="保存中间图片")
    args = parser.parse_args()

    config = CombineConfig(
        dpi=args.dpi,
        overlap=args.overlap,
        feather=args.feather,
        order=args.order,
        no_auto=args.no_auto,
        output_path=args.output,
        input_files=[str(p) for p in args.inputs],
    )

    process_combine(config)


if __name__ == "__main__":
    main()
