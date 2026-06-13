# =============================================================================
#  gui/scan_path_tab.py — 扫描模式：路径面板
# =============================================================================

import os

import customtkinter as ctk
from tkinter import filedialog

from config import AppConfig


class ScanPathTab:
    """扫描模式 — 路径与文件类型选择。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._scan = config.scan
        self._app = app

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _build(self):
        self._section("输入与输出")

        self._input_var = self._add_path_entry("输入根目录", "input_root")
        self._output_var = self._add_path_entry("输出根目录", "output_root")

        self._section("文件类型")

        self._office_var = ctk.BooleanVar(value=self._scan.include_office)
        ctk.CTkCheckBox(
            self._frame, text="含 Office 文档转换 (.doc/.docx)",
            variable=self._office_var,
        ).pack(anchor="w", padx=10, pady=2)
        self._office_var.trace_add(
            "write", lambda *_: setattr(self._scan, "include_office", self._office_var.get())
        )

        self._image_var = ctk.BooleanVar(value=self._scan.include_images)
        ctk.CTkCheckBox(
            self._frame, text="含散落图片 (.jpg/.png/.tiff/.webp/.bmp)",
            variable=self._image_var,
        ).pack(anchor="w", padx=10, pady=2)
        self._image_var.trace_add(
            "write", lambda *_: setattr(self._scan, "include_images", self._image_var.get())
        )

        ctk.CTkLabel(
            self._frame,
            text="ⓘ 输出会按输入相对路径镜像写入。需要安装 Microsoft Word 才能转换 Office 文档。",
            text_color="gray", wraplength=600, justify="left",
        ).pack(anchor="w", padx=10, pady=(8, 4))

    def _add_path_entry(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=110, anchor="w").pack(side="left")
        var = ctk.StringVar(value=getattr(self._scan, attr, ""))
        ctk.CTkEntry(frame, textvariable=var, width=350).pack(
            side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(frame, text="浏览…", width=70,
                      command=lambda: self._browse(attr, var)).pack(side="right")
        var.trace_add("write", lambda *_: setattr(self._scan, attr, var.get()))
        return var

    def _browse(self, attr, var):
        initial = var.get() or os.path.expanduser("~")
        path = filedialog.askdirectory(title="选择目录", initialdir=initial)
        if path:
            var.set(path)
            setattr(self._scan, attr, path)

    def apply_to_config(self, config: AppConfig):
        config.scan = self._scan
