# =============================================================================
#  home_tab.py — 首页：功能说明
# =============================================================================

import os
import sys

import customtkinter as ctk

from config import AppConfig

from .about_dialog import show_about


class HomeTab:
    """首页 — 介绍合并和拼图两大功能。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._app = app

        self._frame = ctk.CTkFrame(parent)

        self._build()

    def _build(self):
        # 居中内容
        center = ctk.CTkFrame(self._frame, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # 图标
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "gui", "icon.png")
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.png")

        if os.path.exists(icon_path):
            from PIL import Image, ImageTk
            img = Image.open(icon_path)
            img = img.resize((80, 80), Image.LANCZOS)
            self._icon_tk = ctk.CTkImage(light_image=img, dark_image=img, size=(80, 80))
            ctk.CTkLabel(center, image=self._icon_tk, text="").pack(pady=(0, 10))

        # 标题
        from main import __version__
        ctk.CTkLabel(
            center,
            text=f"PDF 批量合并工具 v{__version__}",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(0, 20))

        # 功能说明
        info_frame = ctk.CTkFrame(center, fg_color="transparent")
        info_frame.pack(padx=40, fill="x")

        # 合并说明
        merge_card = ctk.CTkFrame(info_frame, corner_radius=10)
        merge_card.pack(fill="x", pady=(0, 10), padx=10)
        ctk.CTkLabel(
            merge_card,
            text="合并模式",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            merge_card,
            text="扫描输入目录，将每个子文件夹中的 PDF 合并为一个文件。\n"
                 "支持自动生成封面、目录、页码、PDF书签等功能。\n"
                 "适用于批量整理文档（如：按项目/年份归档的文件夹结构）。",
            justify="left",
            wraplength=500,
        ).pack(anchor="w", padx=15, pady=(0, 12))

        # 拼图说明
        combine_card = ctk.CTkFrame(info_frame, corner_radius=10)
        combine_card.pack(fill="x", pady=(0, 10), padx=10)
        ctk.CTkLabel(
            combine_card,
            text="拼图模式",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(
            combine_card,
            text="将多个分段 PDF（相邻段有重叠区域）智能拼接为完整文档。\n"
                 "自动检测重叠区域和偏移量，支持画布预览和数值微调。\n"
                 "适用于长图/长文档的扫描件拼接。",
            justify="left",
            wraplength=500,
        ).pack(anchor="w", padx=15, pady=(0, 12))

        # 操作提示
        ctk.CTkLabel(
            center,
            text="请从顶部模式栏选择「合并」或「拼图」开始使用",
            text_color="gray",
            font=ctk.CTkFont(size=13),
        ).pack(pady=(15, 0))

        # 隐蔽入口：右下角低对比度小标签，点击弹出「关于」
        about_hint = ctk.CTkLabel(
            self._frame,
            text=f"ⓘ  v{__version__}",
            text_color=("#9aa0a6", "#5f6368"),
            cursor="hand2",
            font=ctk.CTkFont(size=11),
        )
        about_hint.place(relx=1.0, rely=1.0, anchor="se", x=-12, y=-10)
        about_hint.bind(
            "<Button-1>",
            lambda _e: show_about(self._frame.winfo_toplevel()),
        )

    def apply_to_config(self, config: AppConfig):
        pass
