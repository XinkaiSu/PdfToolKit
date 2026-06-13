# =============================================================================
#  core.py — PDF 处理编排层
#  仅保留流水线入口函数，功能实现已迁移至 methods/ 包
# =============================================================================

import os
import shutil

from pikepdf import Pdf

from config import AppConfig
from methods.fonts import register_fonts
from methods.sort import smart_sort_key
from methods.merge import collect_file_tree, merge_content
from methods.convert import cleanup_temp
from methods.toc import generate_toc
from methods.pagenum import add_page_numbers, add_page_numbers_image_mode
from methods.bookmark import add_bookmarks_to_pdf
from methods.cover import generate_cover_pdf
from methods.blankpage import remove_blank_pages, adjust_page_mapping


# =============================================================================
#  主流程
# =============================================================================

def process_folder(input_folder, output_file, config: AppConfig, stop_event=None):
    """处理单个文件夹：扫描 → 封面 → 合并 → 目录 → 页码 → 插入封面 → 输出。"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cover_pdf = os.path.join(script_dir, "_cover_tmp.pdf")
    content_pdf = os.path.join(script_dir, "_content_tmp.pdf")
    toc_pdf = os.path.join(script_dir, "_toc_tmp.pdf")
    merged_pdf = os.path.join(script_dir, "_merged_tmp.pdf")
    tmp_files = [cover_pdf, content_pdf, toc_pdf, merged_pdf]

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
        pagination, content_pages, source_offsets = merge_content(items, content_pdf, config)

        # 2.5 删除空白页
        if config.advanced.remove_blank_pages:
            blank_tmp = os.path.join(script_dir, "_blank_tmp.pdf")
            tmp_files.append(blank_tmp)
            print("\n 检测并删除空白页…")
            removed_count, removed_indices = remove_blank_pages(content_pdf, blank_tmp)
            if removed_count > 0:
                content_pages = adjust_page_mapping(pagination, source_offsets, removed_indices, content_pages)
                # 用清理后的文件替换原文件
                shutil.move(blank_tmp, content_pdf)
                print(f"   已删除 {removed_count} 页空白页，剩余 {content_pages} 页")
            else:
                print("   未检测到空白页")
                if os.path.exists(blank_tmp):
                    os.remove(blank_tmp)

        if stop_event and stop_event.is_set():
            return

        # 3. 目录
        print("\n 生成目录…")
        toc_pages = generate_toc(toc_pdf, items, pagination, root_name, config)
        print(f"   目录共 {toc_pages} 页")

        if stop_event and stop_event.is_set():
            return

        # 4. 合并目录+正文 + 页码（减少一次中间 save/read）
        with Pdf.open(toc_pdf) as t, Pdf.open(content_pdf) as b:
            merged = Pdf.new()
            merged.pages.extend(t.pages)
            merged.pages.extend(b.pages)
            merged.save(merged_pdf, encryption=False)

        if stop_event and stop_event.is_set():
            return

        # 5. 页码 → 直接输出到最终文件（含封面）
        pn = config.page_num
        if pn.enabled:
            print("\n 添加页码…")
            # 先生成带页码的文件
            numbered_pdf = os.path.join(script_dir, "_numbered_tmp.pdf")
            tmp_files.append(numbered_pdf)
            if config.advanced.enable_image_convert:
                add_page_numbers_image_mode(merged_pdf, numbered_pdf, toc_pages, config)
            else:
                add_page_numbers(merged_pdf, numbered_pdf, toc_pages, config)
        else:
            numbered_pdf = merged_pdf
            print("[i]  页码已禁用，跳过")

        if stop_event and stop_event.is_set():
            return

        # 6. 插入封面 → 输出
        print("\n  插入封面…")
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with Pdf.open(cover_pdf) as cov, Pdf.open(numbered_pdf) as body:
            out = Pdf.new()
            out.pages.extend(cov.pages)
            out.pages.extend(body.pages)
            out.save(output_file, encryption=False)

        # 7. 书签
        if config.bookmark.enabled:
            print("\n 添加PDF书签…")
            try:
                add_bookmarks_to_pdf(
                    output_file, items, pagination,
                    cover_pages, toc_pages, source_offsets, config,
                )
                print("[OK] PDF书签添加完成")
            except Exception as e:
                print(f"[!] PDF书签添加失败：{e}，跳过书签")

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
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cover_pdf = os.path.join(script_dir, "_cover_tmp.pdf")
    content_pdf = os.path.join(script_dir, "_content_tmp.pdf")
    toc_pdf = os.path.join(script_dir, "_toc_tmp.pdf")
    merged_pdf = os.path.join(script_dir, "_merged_tmp.pdf")
    tmp_files = [cover_pdf, content_pdf, toc_pdf, merged_pdf]

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
        pagination, content_pages, source_offsets = merge_content(items, content_pdf, config)

        # 2.5 删除空白页
        if config.advanced.remove_blank_pages:
            blank_tmp = os.path.join(script_dir, "_blank_tmp.pdf")
            tmp_files.append(blank_tmp)
            print("\n 检测并删除空白页…")
            removed_count, removed_indices = remove_blank_pages(content_pdf, blank_tmp)
            if removed_count > 0:
                content_pages = adjust_page_mapping(pagination, source_offsets, removed_indices, content_pages)
                shutil.move(blank_tmp, content_pdf)
                print(f"   已删除 {removed_count} 页空白页，剩余 {content_pages} 页")
            else:
                print("   未检测到空白页")
                if os.path.exists(blank_tmp):
                    os.remove(blank_tmp)

        if stop_event and stop_event.is_set():
            return

        # 3. 目录
        print("\n 生成目录…")
        toc_pages = generate_toc(toc_pdf, items, pagination, root_name, config)
        print(f"   目录共 {toc_pages} 页")

        if stop_event and stop_event.is_set():
            return

        # 4. 合并目录+正文
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
            numbered_pdf = os.path.join(script_dir, "_numbered_tmp.pdf")
            tmp_files.append(numbered_pdf)
            if config.advanced.enable_image_convert:
                add_page_numbers_image_mode(merged_pdf, numbered_pdf, toc_pages, config)
            else:
                add_page_numbers(merged_pdf, numbered_pdf, toc_pages, config)
        else:
            numbered_pdf = merged_pdf
            print("[i]  页码已禁用，跳过")

        if stop_event and stop_event.is_set():
            return

        # 6. 插入封面
        print("\n  插入封面…")
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with Pdf.open(cover_pdf) as cov, Pdf.open(numbered_pdf) as body:
            out = Pdf.new()
            out.pages.extend(cov.pages)
            out.pages.extend(body.pages)
            out.save(output_file, encryption=False)

        # 7. 书签
        if config.bookmark.enabled:
            print("\n 添加PDF书签…")
            try:
                add_bookmarks_to_pdf(
                    output_file, items, pagination,
                    cover_pages, toc_pages, source_offsets, config,
                )
                print("[OK] PDF书签添加完成")
            except Exception as e:
                print(f"[!] PDF书签添加失败：{e}，跳过书签")

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


def process_scan_root(scan_cfg, stop_event=None, progress_callback=None):
    """扫描模式入口：递归处理输入根下所有 PDF/Office/图片，
    输出镜像写入输出根。

    progress_callback(done, total)：每完成（或跳过/失败）一个文件后调用，
    用于 GUI 进度条更新。可选。
    """
    from methods.scan import collect_scan_files, process_scan_file
    from methods.office import coinitialize, couninitialize

    in_root = scan_cfg.input_root
    out_root = scan_cfg.output_root

    if not in_root or not os.path.isdir(in_root):
        print(f"[X] 输入目录不存在：{in_root}")
        return
    if not out_root:
        print("[X] 未设置输出目录")
        return

    if os.path.abspath(in_root) == os.path.abspath(out_root):
        print("[!] 输入输出相同，输入根下的 .pdf 可能被覆盖")

    files = collect_scan_files(scan_cfg)
    total = len(files)
    if total == 0:
        print("[!] 未找到可处理的文件")
        return

    print(f"\n 共 {total} 个文件待处理")

    coinitialize()
    ok = fail = skip = stopped = 0
    seen_outputs = set()
    try:
        for i, src in enumerate(files):
            if stop_event and stop_event.is_set():
                stopped = total - i
                print("[STOP] 已停止")
                break

            rel = os.path.relpath(src, in_root)
            stem, _ = os.path.splitext(rel)
            dst = os.path.join(out_root, stem + ".pdf")
            dst_key = os.path.normcase(os.path.abspath(dst))

            print(f"\n [{i+1}/{total}] {rel}")

            if dst_key in seen_outputs:
                print(f"[!] 同名冲突：{stem}.pdf 已被前一个文件输出，本次跳过 {os.path.basename(src)}")
                skip += 1
                if progress_callback:
                    progress_callback(i + 1, total)
                continue
            seen_outputs.add(dst_key)

            try:
                os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
            except PermissionError:
                print(f"[X] 无权创建目录：{os.path.dirname(dst)}")
                fail += 1
                if progress_callback:
                    progress_callback(i + 1, total)
                continue

            try:
                result = process_scan_file(src, dst, scan_cfg, stop_event)
            except Exception as e:
                print(f"[X] {rel} 处理时抛出未捕获异常：{e}")
                fail += 1
                if progress_callback:
                    progress_callback(i + 1, total)
                continue

            if result == "ok":
                ok += 1
            elif result == "skip":
                skip += 1
            elif result == "stopped":
                stopped = total - i
                break
            else:
                fail += 1

            if progress_callback:
                progress_callback(i + 1, total)
    finally:
        couninitialize()

    print(f"""
╔==================================================╗
║    扫描处理完成
╠==================================================╣
║  成功：{ok}
║  失败：{fail}
║  跳过：{skip}
║  未处理（已停止）：{stopped}
║  输出：{os.path.abspath(out_root)}
╚==================================================╝
""")
