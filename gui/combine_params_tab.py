# =============================================================================
#  combine_params_tab.py — 拼图模式参数设置面板
# =============================================================================

import os

import customtkinter as ctk
from tkinter import filedialog
import os

from config import AppConfig


class CombineParamsTab:
    """拼图模式 — 参数设置：DPI / 重叠 / 羽化 / 输出路径。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._combine = config.combine
        self._app = app

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_int_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._combine, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_int(attr, var))

    def _build(self):
        # ── 渲染设置 ──
        self._section("渲染设置")
        self._add_int_entry("DPI 分辨率", "dpi", "dpi")

        # ── 排序设置 ──
        self._section("排序设置")
        order_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        order_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(order_frame, text="排序方式", width=150, anchor="w").pack(side="left")
        _ORDER_MAP = {"auto": "自动排序", "manual": "手动顺序"}
        _ORDER_REVERSE = {v: k for k, v in _ORDER_MAP.items()}
        self._order_display = _ORDER_MAP
        self._order_reverse = _ORDER_REVERSE
        display = _ORDER_MAP.get(self._combine.order, "自动排序")
        self._order_var = ctk.StringVar(value=display)
        ctk.CTkSegmentedButton(
            order_frame,
            variable=self._order_var,
            values=list(_ORDER_MAP.values()),
            command=self._on_order_change,
        ).pack(side="right", fill="x", expand=True)

        # ── 重叠检测 ──
        self._section("重叠检测")
        overlap_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        overlap_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(overlap_frame, text="检测模式", width=150, anchor="w").pack(side="left")
        _OVERLAP_MAP = {"auto": "自动检测", "manual": "手动指定", "skip": "跳过检测"}
        _OVERLAP_REVERSE = {v: k for k, v in _OVERLAP_MAP.items()}
        self._overlap_display = _OVERLAP_MAP
        self._overlap_reverse = _OVERLAP_REVERSE
        if self._combine.no_auto:
            init_overlap = "跳过检测"
        elif self._combine.overlap is not None:
            init_overlap = "手动指定"
        else:
            init_overlap = "自动检测"
        self._overlap_var = ctk.StringVar(value=init_overlap)
        ctk.CTkSegmentedButton(
            overlap_frame,
            variable=self._overlap_var,
            values=list(_OVERLAP_MAP.values()),
            command=self._on_overlap_mode_change,
        ).pack(side="right", fill="x", expand=True)

        # 手动重叠比例（仅手动模式显示）
        self._overlap_entry_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        self._overlap_entry_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(self._overlap_entry_frame, text="重叠比例", width=150, anchor="w").pack(side="left")
        overlap_val = str(self._combine.overlap) if self._combine.overlap is not None else "0.25"
        self._overlap_val_var = ctk.StringVar(value=overlap_val)
        self._overlap_entry = ctk.CTkEntry(self._overlap_entry_frame,
                                            textvariable=self._overlap_val_var, width=120)
        self._overlap_entry.pack(side="right")
        ctk.CTkLabel(self._overlap_entry_frame, text="(0~1)", width=40, anchor="w").pack(side="right")
        self._overlap_val_var.trace_add("write", lambda *_: self._on_overlap_val_change())
        self._update_overlap_entry_visibility()

        # ── 拼接设置 ──
        self._section("拼接设置")
        self._add_int_entry("羽化像素数", "feather", "px")

        # ── 背景设置 ──
        self._section("背景设置")
        bg_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        bg_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(bg_frame, text="背景颜色", width=150, anchor="w").pack(side="left")
        self._bg_color_btn = ctk.CTkButton(
            bg_frame, text="  ", width=40, height=28,
            fg_color=self._rgb_to_hex(self._combine.bg_color),
            hover_color=self._rgb_to_hex(self._combine.bg_color),
            command=self._pick_bg_color)
        self._bg_color_btn.pack(side="right", padx=(0, 5))
        self._bg_color_label = ctk.CTkLabel(
            bg_frame, text=self._color_to_text(self._combine.bg_color))
        self._bg_color_label.pack(side="right")

        # ── 裁切设置 ──
        self._section("裁切设置")
        crop_ws_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        crop_ws_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(crop_ws_frame, text="裁切空白", width=150, anchor="w").pack(side="left")
        self._crop_ws_var = ctk.BooleanVar(value=self._combine.crop_whitespace)
        ctk.CTkSwitch(crop_ws_frame, variable=self._crop_ws_var,
                      text="自动去除周边空白",
                      command=self._on_crop_ws_change).pack(side="right")
        self._add_float_entry("边框裁切", "crop_border_mm", "mm")

        # ── 输出 ──
        self._section("输出设置")
        out_dir_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        out_dir_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(out_dir_frame, text="输出目录", width=150, anchor="w").pack(side="left")
        out_dir = os.path.dirname(self._combine.output_path) if self._combine.output_path else ""
        self._output_dir_var = ctk.StringVar(value=out_dir)
        ctk.CTkEntry(out_dir_frame, textvariable=self._output_dir_var,
                     width=250).pack(side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(out_dir_frame, text="浏览…", width=70,
                      command=self._browse_output_dir).pack(side="right")

        out_name_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        out_name_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(out_name_frame, text="文件名称", width=150, anchor="w").pack(side="left")
        out_name = os.path.basename(self._combine.output_path) if self._combine.output_path else "output.pdf"
        self._output_name_var = ctk.StringVar(value=out_name)
        ctk.CTkEntry(out_name_frame, textvariable=self._output_name_var,
                     width=250).pack(side="left", fill="x", expand=True, padx=(5, 5))
        self._output_dir_var.trace_add("write", lambda *_: self._set_output())
        self._output_name_var.trace_add("write", lambda *_: self._set_output())

    # ── 事件处理 ──

    def _on_order_change(self, value):
        self._combine.order = self._order_reverse.get(value, "auto")

    def _on_overlap_mode_change(self, value):
        mode = self._overlap_reverse.get(value, "auto")
        if mode == "skip":
            self._combine.no_auto = True
            self._combine.overlap = None
        elif mode == "manual":
            self._combine.no_auto = False
            try:
                self._combine.overlap = float(self._overlap_val_var.get())
            except (ValueError, TypeError):
                self._combine.overlap = 0.25
        else:  # auto
            self._combine.no_auto = False
            self._combine.overlap = None
        self._update_overlap_entry_visibility()

    def _update_overlap_entry_visibility(self):
        """手动模式显示重叠输入框，其他模式隐藏。"""
        mode = self._overlap_reverse.get(self._overlap_var.get(), "auto")
        if mode == "manual":
            for child in self._overlap_entry_frame.winfo_children():
                try:
                    child.configure(state="normal")
                except Exception:
                    pass
        else:
            for child in self._overlap_entry_frame.winfo_children():
                try:
                    if isinstance(child, ctk.CTkEntry):
                        child.configure(state="disabled")
                except Exception:
                    pass

    def _on_overlap_val_change(self):
        try:
            self._combine.overlap = float(self._overlap_val_var.get())
        except (ValueError, TypeError):
            pass

    def _browse_output_dir(self):
        initial = self._output_dir_var.get() or os.path.expanduser("~")
        path = filedialog.askdirectory(title="选择输出目录", initialdir=initial)
        if path:
            self._output_dir_var.set(path)

    def _set_output(self):
        d = self._output_dir_var.get().strip()
        n = self._output_name_var.get().strip()
        if d and n:
            self._combine.output_path = os.path.join(d, n)
        elif n:
            self._combine.output_path = n
        else:
            self._combine.output_path = ""

    def _set_int(self, attr, var):
        try:
            setattr(self._combine, attr, int(var.get()))
        except (ValueError, TypeError):
            pass

    def _add_float_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._combine, attr, 0.0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_float(attr, var))

    def _set_float(self, attr, var):
        try:
            setattr(self._combine, attr, float(var.get()))
        except (ValueError, TypeError):
            pass

    def _rgb_to_hex(self, rgb):
        r, g, b = [max(0, min(255, int(c))) for c in rgb]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _color_to_text(self, rgb):
        return f"RGB({int(rgb[0])}, {int(rgb[1])}, {int(rgb[2])})"

    def _on_crop_ws_change(self):
        self._combine.crop_whitespace = self._crop_ws_var.get()

    def _pick_bg_color(self):
        from tkinter import colorchooser
        color = colorchooser.askcolor(
            initialcolor=self._rgb_to_hex(self._combine.bg_color),
            title="选择背景颜色")
        if color and color[0]:
            rgb = [int(c) for c in color[0]]
            self._combine.bg_color = rgb
            hex_color = self._rgb_to_hex(rgb)
            self._bg_color_btn.configure(fg_color=hex_color, hover_color=hex_color)
            self._bg_color_label.configure(text=self._color_to_text(rgb))

    def apply_to_config(self, config: AppConfig):
        config.combine = self._combine
