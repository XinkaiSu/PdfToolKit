# =============================================================================
#  main.py — 程序入口
#  启动 GUI 或 CLI 模式
# =============================================================================

import sys

__version__ = "1.1.0"


def main():
    # CLI 模式
    if "--cli" in sys.argv:
        _run_cli()
        return

    # GUI 模式
    _run_gui()


def _run_gui():
    """启动 GUI 界面。"""
    import customtkinter as ctk
    from gui.app import PdfToolKitApp

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    app = PdfToolKitApp()
    app.mainloop()


def _run_cli():
    """命令行模式（兼容旧版）。"""
    import os
    from config import AppConfig
    from core import process_folder, get_subfolders, register_fonts

    config = AppConfig.load()
    input_root = config.path.input_root
    output_root = config.path.output_root

    if not input_root or not output_root:
        print("❌ 请先在 GUI 中设置输入/输出目录，或在配置文件中填写。")
        print(f"   配置文件位置：{os.path.join(AppConfig.CONFIG_DIR, AppConfig.CONFIG_FILE)}")
        return

    os.makedirs(output_root, exist_ok=True)
    register_fonts(config)

    folders = get_subfolders(input_root, config)
    if not folders:
        print(f"⚠️ 输入目录下未找到子文件夹：{input_root}")
    else:
        for folder in folders:
            sep = "═" * 24
            print(f"\n{sep}  {folder}  {sep}")
            process_folder(
                input_folder=os.path.join(input_root, folder),
                output_file=os.path.join(output_root, f"{folder}.pdf"),
                config=config,
            )
        print(f"\n🎉 全部完成！输出目录：{output_root}")


if __name__ == "__main__":
    main()
