# =============================================================================
#  about_dialog.py — 「关于」弹窗（首页右下角隐蔽入口触发）
# =============================================================================

import webbrowser

import customtkinter as ctk

AUTHOR = "XinkaiSu"
GITHUB_URL = "https://github.com/XinkaiSu/PdfToolKit"

# 主要开源依赖致谢
CREDITS = [
    ("pikepdf",           "PDF 读写与 XObject 嵌入"),
    ("reportlab",         "封面 / 目录 / 页码 / 扫描件 A4 输出"),
    ("PyMuPDF (fitz)",    "PDF 渲染（预览、拼图、扫描）"),
    ("Pillow",            "图像处理"),
    ("numpy",             "拼图模式 FFT 互相关偏移检测"),
    ("customtkinter",     "GUI 框架"),
    ("look-like-scanned", "扫描效果实现"),
    ("pywin32",           "Word→PDF COM 桥接（仅 Windows）"),
]


class _AboutDialog(ctk.CTkToplevel):
    """「关于 PdfToolKit」对话框。"""

    def __init__(self, master):
        super().__init__(master)
        self.title("关于 PdfToolKit")
        self.resizable(False, False)
        self.transient(master)
        # 短暂置顶以确保浮在主窗之上，再撤销以便切窗
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        from version import __version__

        # —— 标题区 —— #
        ctk.CTkLabel(
            self,
            text="PdfToolKit",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(padx=30, pady=(20, 2))
        ctk.CTkLabel(
            self,
            text=f"v{__version__}",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).pack(padx=30, pady=(0, 14))

        # —— 作者 / 版权 —— #
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(padx=30, pady=(0, 6), fill="x")

        ctk.CTkLabel(
            info_frame,
            text=f"作者：{AUTHOR}",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w")

        link_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        link_row.pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            link_row,
            text="GitHub：",
            font=ctk.CTkFont(size=13),
        ).pack(side="left")
        link_label = ctk.CTkLabel(
            link_row,
            text=GITHUB_URL,
            text_color=("#1f6feb", "#58a6ff"),
            cursor="hand2",
            font=ctk.CTkFont(size=13, underline=True),
        )
        link_label.pack(side="left")
        link_label.bind("<Button-1>", lambda _e: webbrowser.open(GITHUB_URL))

        ctk.CTkLabel(
            info_frame,
            text="© 2026 XinkaiSu. All rights reserved.",
            text_color="gray",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", pady=(8, 0))

        # —— 依赖致谢 —— #
        ctk.CTkLabel(
            self,
            text="依赖致谢",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=30, pady=(14, 4), anchor="w")

        credits_box = ctk.CTkFrame(self, corner_radius=8)
        credits_box.pack(padx=30, pady=(0, 14), fill="x")
        for name, desc in CREDITS:
            row = ctk.CTkFrame(credits_box, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(
                row,
                text=name,
                font=ctk.CTkFont(size=12, weight="bold"),
                width=140,
                anchor="w",
            ).pack(side="left")
            ctk.CTkLabel(
                row,
                text=f"— {desc}",
                text_color="gray",
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        # —— 操作按钮 —— #
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(padx=30, pady=(0, 18), fill="x")

        ctk.CTkButton(
            btn_row,
            text="复制仓库地址",
            width=120,
            command=self._copy_github,
        ).pack(side="left")
        ctk.CTkButton(
            btn_row,
            text="访问 GitHub",
            width=120,
            command=lambda: webbrowser.open(GITHUB_URL),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btn_row,
            text="关闭",
            width=80,
            fg_color="gray35",
            hover_color="gray25",
            command=self.destroy,
        ).pack(side="right")

        # 居中到主窗口
        self.update_idletasks()
        self._center_on_master(master)

        self.grab_set()
        self.focus_set()

    # ---------------------------------------------------------------- helpers

    def _copy_github(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(GITHUB_URL)
            self.update()
        except Exception:
            pass

    def _center_on_master(self, master):
        try:
            mx = master.winfo_rootx()
            my = master.winfo_rooty()
            mw = master.winfo_width()
            mh = master.winfo_height()
            w = self.winfo_width()
            h = self.winfo_height()
            x = mx + (mw - w) // 2
            y = my + (mh - h) // 3
            self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        except Exception:
            pass


def show_about(master):
    """显示「关于」对话框（外部唯一入口）。"""
    _AboutDialog(master)
