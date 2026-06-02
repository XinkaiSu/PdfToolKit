# =============================================================================
#  font_tab.py — 字体设置选项卡
# =============================================================================

import os

import customtkinter as ctk
from tkinter import filedialog

from config import AppConfig


class FontTab:
    """字体设置选项卡。"""

    def __init__(self, parent, config: AppConfig):
        self._config = config
        self._font = config.font

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _build(self):
        # ── 系统字体目录 ──
        self._section("系统字体目录")
        dir_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        dir_frame.pack(fill="x", padx=10, pady=2)
        self._font_dir_var = ctk.StringVar(value=self._font.font_dir)
        ctk.CTkEntry(dir_frame, textvariable=self._font_dir_var,
                     width=350).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_frame, text="浏览…", width=70,
                      command=self._browse_font_dir).pack(side="right", padx=(5, 0))
        self._font_dir_var.trace_add("write", lambda *_: self._set_font_dir())

        # ── 字体映射 ──
        self._section("字体映射")
        self._font_map_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        self._font_map_frame.pack(fill="x", padx=10, pady=2)

        # 表头
        header = ctk.CTkFrame(self._font_map_frame, fg_color="transparent")
        header.pack(fill="x")
        ctk.CTkLabel(header, text="注册名", width=150, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="字体文件", width=150, anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkLabel(header, text="状态", width=80, anchor="center",
                     font=ctk.CTkFont(weight="bold")).pack(side="left")

        self._rebuild_font_map_list()

        btn_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="添加字体映射", width=130,
                      command=self._add_font_mapping).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="删除选中", width=100,
                      command=self._remove_font_mapping).pack(side="left")

        # ── 回退顺序 ──
        self._section("回退顺序")
        self._fallback_list_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        self._fallback_list_frame.pack(fill="x", padx=10, pady=2)
        self._rebuild_fallback_list()

        ctk.CTkButton(self._frame, text="添加回退字体", width=130,
                      command=self._add_fallback_font).pack(
            anchor="w", padx=10, pady=5)

        # ── 测试按钮 ──
        ctk.CTkButton(self._frame, text="测试注册字体", width=130,
                      command=self._test_fonts).pack(anchor="w", padx=10, pady=10)

    def _rebuild_font_map_list(self):
        """重建字体映射列表。"""
        for widget in self._font_map_frame.winfo_children():
            if widget not in [self._font_map_frame.winfo_children()[0]]:
                widget.destroy()

        font_dir = self._font.font_dir
        for name, filename in self._font.font_map.items():
            row = ctk.CTkFrame(self._font_map_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)

            # 选择标记
            select_var = ctk.BooleanVar(value=False)
            ctk.CTkCheckBox(row, text="", variable=select_var, width=20).pack(side="left")

            ctk.CTkLabel(row, text=name, width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=filename, width=140, anchor="w").pack(side="left")

            path = os.path.join(font_dir, filename)
            exists = os.path.exists(path)
            status = "✅ 已找到" if exists else "⚠️ 未找到"
            color = "green" if exists else "orange"
            ctk.CTkLabel(row, text=status, width=80, anchor="center",
                         text_color=color).pack(side="left")

            # 保存 select_var 引用
            row._select_var = select_var

    def _rebuild_fallback_list(self):
        """重建回退顺序列表。"""
        for widget in self._fallback_list_frame.winfo_children():
            widget.destroy()

        for i, name in enumerate(self._font.fallback_order):
            row = ctk.CTkFrame(self._fallback_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{i + 1}. {name}", width=200,
                         anchor="w").pack(side="left")
            ctk.CTkButton(row, text="↑", width=30,
                          command=lambda idx=i: self._move_fallback(idx, -1)).pack(
                side="right", padx=2)
            ctk.CTkButton(row, text="↓", width=30,
                          command=lambda idx=i: self._move_fallback(idx, 1)).pack(
                side="right", padx=2)
            ctk.CTkButton(row, text="×", width=30,
                          command=lambda idx=i: self._remove_fallback(idx)).pack(
                side="right", padx=2)

    def _browse_font_dir(self):
        initial = self._font_dir_var.get() or os.path.expanduser("~")
        path = filedialog.askdirectory(title="选择字体目录", initialdir=initial)
        if path:
            self._font_dir_var.set(path)
            self._font.font_dir = path
            self._rebuild_font_map_list()

    def _set_font_dir(self):
        self._font.font_dir = self._font_dir_var.get()

    def _add_font_mapping(self):
        """弹出对话框添加字体映射。"""
        dialog = ctk.CTkInputDialog(text="输入格式：注册名,字体文件名\n例：SimHei,simhei.ttf",
                                     title="添加字体映射")
        result = dialog.get_input()
        if result and "," in result:
            parts = result.split(",", 1)
            name = parts[0].strip()
            filename = parts[1].strip()
            if name and filename:
                self._font.font_map[name] = filename
                self._rebuild_font_map_list()

    def _remove_font_mapping(self):
        """删除选中的字体映射。"""
        to_remove = []
        for row in self._font_map_frame.winfo_children()[1:]:
            if hasattr(row, '_select_var') and row._select_var.get():
                name_label = row.winfo_children()[1]  # 注册名 label
                name = name_label.cget("text")
                to_remove.append(name)
        for name in to_remove:
            if name in self._font.font_map:
                del self._font.font_map[name]
        self._rebuild_font_map_list()

    def _add_fallback_font(self):
        """弹出对话框添加回退字体。"""
        fonts = list(self._font.font_map.keys())
        dialog = ctk.CTkInputDialog(
            text=f"可选字体：{', '.join(fonts)}\n请输入字体注册名：",
            title="添加回退字体"
        )
        result = dialog.get_input()
        if result and result.strip():
            self._font.fallback_order.append(result.strip())
            self._rebuild_fallback_list()

    def _remove_fallback(self, idx):
        if 0 <= idx < len(self._font.fallback_order):
            self._font.fallback_order.pop(idx)
            self._rebuild_fallback_list()

    def _move_fallback(self, idx, direction):
        new_idx = idx + direction
        order = self._font.fallback_order
        if 0 <= new_idx < len(order):
            order[idx], order[new_idx] = order[new_idx], order[idx]
            self._rebuild_fallback_list()

    def _test_fonts(self):
        """测试注册字体并刷新状态。"""
        from methods.fonts import register_fonts
        import pdfmetrics
        try:
            register_fonts(self._config)
            registered = pdfmetrics.getRegisteredFontNames()
            print(f"已注册字体：{', '.join(registered)}")
        except Exception as e:
            print(f"字体注册测试失败：{e}")
        self._rebuild_font_map_list()

    def apply_to_config(self, config: AppConfig):
        config.font = self._font

    def refresh_font_options(self):
        pass
