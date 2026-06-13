# =============================================================================
#  test/test_scan.py — 扫描模式手动验证脚本
#  用法：python test/test_scan.py
# =============================================================================

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image

from config import ScanConfig
from methods.scan import (
    _resolve_params,
    _apply_scan_effects,
    _PRESETS,
)


def test_resolve_params_presets():
    """三档预设各能解析出 dict。"""
    for name in ("light", "medium", "heavy"):
        cfg = ScanConfig(preset=name)
        p = _resolve_params(cfg)
        assert isinstance(p, dict)
        assert "noise" in p and "jpeg_quality" in p
        assert p["noise"] == _PRESETS[name]["noise"]
    print("[OK] test_resolve_params_presets")


def test_resolve_params_custom():
    """custom 时读 scan_cfg 字段。"""
    cfg = ScanConfig(preset="custom", noise=42, jpeg_quality=60)
    p = _resolve_params(cfg)
    assert p["noise"] == 42
    assert p["jpeg_quality"] == 60
    print("[OK] test_resolve_params_custom")


def test_apply_scan_effects_returns_rgb():
    """效果函数对一张白图 → 仍是 RGB 模式，尺寸 > 0。"""
    img = Image.new("RGB", (200, 300), color=(255, 255, 255))
    cfg = ScanConfig(preset="light")
    out = _apply_scan_effects(img, cfg)
    assert out.mode == "RGB"
    assert out.size[0] > 0 and out.size[1] > 0
    print("[OK] test_apply_scan_effects_returns_rgb")


def test_collect_scan_files_filters_extensions():
    """include_office / include_images 控制返回扩展名。"""
    import shutil
    from methods.scan import collect_scan_files
    tmp = tempfile.mkdtemp(prefix="scan_test_")
    try:
        sub = os.path.join(tmp, "sub")
        os.makedirs(sub)
        # 创建空文件
        for name in ("a.pdf", "b.docx", "c.jpg", "d.txt"):
            open(os.path.join(tmp, name), "w").close()
        open(os.path.join(sub, "e.pdf"), "w").close()

        cfg = ScanConfig(input_root=tmp, include_office=False, include_images=False)
        files = [os.path.basename(p) for p in collect_scan_files(cfg)]
        assert sorted(files) == ["a.pdf", "e.pdf"], files

        cfg2 = ScanConfig(input_root=tmp, include_office=True, include_images=True)
        files2 = [os.path.basename(p) for p in collect_scan_files(cfg2)]
        assert sorted(files2) == ["a.pdf", "b.docx", "c.jpg", "e.pdf"], files2
        print("[OK] test_collect_scan_files_filters_extensions")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_images_to_pdf_a4_page_count():
    """3 张图 → 3 页 PDF。"""
    from methods.scan import images_to_pdf_a4
    import pikepdf
    imgs = [Image.new("RGB", (400, 600), color=(200, 200, 200)) for _ in range(3)]
    out = tempfile.mktemp(suffix=".pdf")
    try:
        n = images_to_pdf_a4(imgs, out, jpeg_quality=90)
        assert n == 3
        with pikepdf.Pdf.open(out) as pdf:
            assert len(pdf.pages) == 3
        print("[OK] test_images_to_pdf_a4_page_count")
    finally:
        if os.path.exists(out):
            os.remove(out)


def test_images_to_pdf_a4_jpeg_quality_affects_size():
    """高质量 PDF 应当显著大于低质量 PDF（同样的输入图片）。"""
    from methods.scan import images_to_pdf_a4
    # 用一张有细节的图（噪声）确保 JPEG 压缩有差异
    import random
    random.seed(0)
    pixels = [(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
              for _ in range(800 * 600)]
    img = Image.new("RGB", (800, 600))
    img.putdata(pixels)

    out_lo = tempfile.mktemp(suffix="_lo.pdf")
    out_hi = tempfile.mktemp(suffix="_hi.pdf")
    try:
        images_to_pdf_a4([img], out_lo, jpeg_quality=20)
        images_to_pdf_a4([img], out_hi, jpeg_quality=95)
        size_lo = os.path.getsize(out_lo)
        size_hi = os.path.getsize(out_hi)
        # 高质量至少比低质量大 20%
        assert size_hi > size_lo * 1.2, f"size_hi={size_hi} size_lo={size_lo}"
        print(f"[OK] test_images_to_pdf_a4_jpeg_quality_affects_size (lo={size_lo} hi={size_hi})")
    finally:
        for p in (out_lo, out_hi):
            if os.path.exists(p):
                os.remove(p)


if __name__ == "__main__":
    test_resolve_params_presets()
    test_resolve_params_custom()
    test_apply_scan_effects_returns_rgb()
    test_collect_scan_files_filters_extensions()
    test_images_to_pdf_a4_page_count()
    test_images_to_pdf_a4_jpeg_quality_affects_size()
    print("\nAll basic tests passed.")
