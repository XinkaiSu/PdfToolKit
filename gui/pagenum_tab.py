# =============================================================================
#  pagenum_tab.py — 页码设置选项卡
# =============================================================================

import customtkinter as ctk
from tkinter import colorchooser

from config import AppConfig


class PageNumTab:
    """页码设置选项卡。"""

    def __init__(self, parent, config: AppConfig):
        self._config = config
        self._pn = config.page_num

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_checkbox(self, label, attr):
        var = ctk.BooleanVar(value=getattr(self._pn, attr, False))
        ctk.CTkCheckBox(self._frame, text=label, variable=var).pack(
            anchor="w", padx=10, pady=2)
        var.trace_add("write", lambda *_: self._set_bool(attr, var))
        return var

    def _add_font_combo(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        fonts = list(self._config.font.font_map.keys())
        var = ctk.StringVar(value=getattr(self._pn, attr, "SimHei"))
        ctk.CTkComboBox(frame, variable=var, values=fonts, width=200).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str(attr, var))

    def _add_int_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._pn, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_int(attr, var))

    def _add_float_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._pn, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_float(attr, var))

    def _add_color_button(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        color = getattr(self._pn, attr, [0, 0, 0])
        if color is None:
            color = [0, 0, 0]
        btn = ctk.CTkButton(
            frame, text="  ■  ", width=100,
            fg_color=self._rgb_to_hex(color),
            command=lambda: self._pick_color(attr, btn)
        )
        btn.pack(side="right")
        return btn

    def _add_radio_group(self, label, attr, options):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        radio_frame = ctk.CTkFrame(frame, fg_color="transparent")
        radio_frame.pack(side="right")
        var = ctk.StringVar(value=getattr(self._pn, attr, options[0]))
        for opt in options:
            ctk.CTkRadioButton(radio_frame, text=opt, variable=var,
                               value=opt).pack(side="left", padx=5)
        var.trace_add("write", lambda *_: self._set_str(attr, var))

    def _add_shape_combo(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=getattr(self._pn, attr, "rect"))
        ctk.CTkComboBox(frame, variable=var,
                        values=["rect", "roundrect", "ellipse"],
                        width=200).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str(attr, var))

    def _add_style_combo(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=getattr(self._pn, attr, "solid"))
        ctk.CTkComboBox(frame, variable=var,
                        values=["solid", "dashed", "dotted"],
                        width=200).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str(attr, var))

    def _build(self):
        self._section("基本设置")
        self._add_checkbox("启用页码", "enabled")
        self._add_font_combo("字体", "font")
        self._add_int_entry("字号", "size", "pt")
        self._add_float_entry("距底部", "margin_bottom_mm", "mm")
        self._add_radio_group("水平位置", "align", ["center", "left", "right"])
        self._add_float_entry("侧偏移", "side_offset_inch", "inch")
        self._add_color_button("文字颜色", "text_color")

        self._section("背景设置")
        # 背景色（None=透明）
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text="背景色", width=150, anchor="w").pack(side="left")
        self._bg_none_var = ctk.BooleanVar(value=(self._pn.bg_color is None))
        ctk.CTkCheckBox(frame, text="透明", variable=self._bg_none_var,
                        command=self._toggle_bg_color).pack(side="right", padx=5)
        self._bg_color_btn = ctk.CTkButton(
            frame, text="  ■  ", width=80,
            fg_color=self._rgb_to_hex(self._pn.bg_color or [1, 1, 1]),
            command=lambda: self._pick_color_bg()
        )
        self._bg_color_btn.pack(side="right")

        self._add_shape_combo("背景形状", "bg_shape")
        self._add_float_entry("背景宽度", "bg_width", "pt")
        self._add_float_entry("背景高度偏移", "bg_height_offset", "pt")
        self._add_float_entry("圆角半径", "bg_radius", "pt")

        self._section("边框设置")
        self._add_checkbox("绘制边框", "border")
        self._add_color_button("边框颜色", "border_color")
        self._add_float_entry("边框线宽", "border_width", "pt")
        self._add_style_combo("边框线型", "border_style")
        self._add_float_entry("虚线段长", "border_dash_on", "pt")
        self._add_float_entry("虚线间隔", "border_dash_off", "pt")

    def _toggle_bg_color(self):
        if self._bg_none_var.get():
            self._pn.bg_color = None
        else:
            if self._pn.bg_color is None:
                self._pn.bg_color = [1, 1, 1]

    def _pick_color(self, attr, btn):
        current = getattr(self._pn, attr, [0, 0, 0])
        if current is None:
            current = [0, 0, 0]
        initial = tuple(max(0, min(255, int(c * 255))) for c in current)
        result = colorchooser.askcolor(initialcolor=initial, title="选择颜色")
        if result[0]:
            r, g, b = [x / 255.0 for x in result[0]]
            setattr(self._pn, attr, [r, g, b])
            btn.configure(fg_color=self._rgb_to_hex([r, g, b]))

    def _pick_color_bg(self):
        current = self._pn.bg_color or [1, 1, 1]
        initial = tuple(max(0, min(255, int(c * 255))) for c in current)
        result = colorchooser.askcolor(initialcolor=initial, title="选择背景色")
        if result[0]:
            r, g, b = [x / 255.0 for x in result[0]]
            self._pn.bg_color = [r, g, b]
            self._bg_color_btn.configure(fg_color=self._rgb_to_hex([r, g, b]))

    @staticmethod
    def _rgb_to_hex(color):
        r, g, b = [max(0, min(255, int(c * 255))) for c in color]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _set_str(self, attr, var):
        try:
            setattr(self._pn, attr, var.get())
        except Exception:
            pass

    def _set_int(self, attr, var):
        try:
            setattr(self._pn, attr, int(var.get()))
        except (ValueError, TypeError):
            pass

    def _set_float(self, attr, var):
        try:
            setattr(self._pn, attr, float(var.get()))
        except (ValueError, TypeError):
            pass

    def _set_bool(self, attr, var):
        try:
            setattr(self._pn, attr, var.get())
        except Exception:
            pass

    def apply_to_config(self, config: AppConfig):
        config.page_num = self._pn

    def refresh_font_options(self):
        pass
