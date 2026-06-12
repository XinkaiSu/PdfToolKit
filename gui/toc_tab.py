# =============================================================================
#  toc_tab.py — 目录设置选项卡
# =============================================================================

import customtkinter as ctk

from config import AppConfig, NumberingConfig


class TocTab:
    """目录设置选项卡。"""

    def __init__(self, parent, config: AppConfig):
        self._config = config
        self._toc = config.toc
        self._numbering = config.numbering

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_float_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._toc, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_float(attr, var))

    def _add_int_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._toc, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_int(attr, var))

    def _add_font_combo(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=150, anchor="w").pack(side="left")
        fonts = list(self._config.font.font_map.keys())
        var = ctk.StringVar(value=getattr(self._toc, attr, "SimHei"))
        ctk.CTkComboBox(frame, variable=var, values=fonts, width=200).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str(attr, var))

    def _build(self):
        self._section("页边距")
        self._add_float_entry("左边距", "margin_left_inch", "inch")
        self._add_float_entry("右边距", "margin_right_inch", "inch")
        self._add_float_entry("上边距", "margin_top_inch", "inch")
        self._add_float_entry("下边距", "margin_bottom_inch", "inch")

        self._section("条目格式")
        self._add_int_entry("行高", "line_gap", "pt")
        self._add_int_entry("字号", "font_size", "pt")
        self._add_int_entry("每级缩进", "indent_per_level", "pt")

        self._section("各级字体")
        self._add_font_combo("目录标题", "font_title")
        self._add_font_combo("一级条目", "font_level1")
        self._add_font_combo("二级条目", "font_level2")
        self._add_font_combo("三级条目", "font_level3")
        self._add_font_combo("四级及以下", "font_deeper")
        self._add_font_combo("文件条目", "font_file")

        self._section("引导点")
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text="引导点字符", width=150, anchor="w").pack(side="left")
        var = ctk.StringVar(value=self._toc.dot_char)
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str("dot_char", var))

        # ── 编号设置 ──
        self._section("编号设置")
        # 删除原有编号（置于启用编号上方）
        remove_var = ctk.BooleanVar(value=self._numbering.remove_original)
        ctk.CTkCheckBox(self._frame, text="删除原有编号", variable=remove_var).pack(
            anchor="w", padx=10, pady=2)
        remove_var.trace_add("write", lambda *_: self._set_num_bool("remove_original", remove_var))

        num_var = ctk.BooleanVar(value=self._numbering.enabled)
        ctk.CTkCheckBox(self._frame, text="启用编号", variable=num_var).pack(
            anchor="w", padx=10, pady=2)
        num_var.trace_add("write", lambda *_: self._set_num_bool("enabled", num_var))

        _NUM_STYLES = ["none", "chinese", "arabic", "multi_level"]
        _LEVEL_ATTRS = [
            ("level1_style", "一级编号"),
            ("level2_style", "二级编号"),
            ("level3_style", "三级编号"),
            ("level_deeper_style", "四级及以下编号"),
        ]
        for attr, label in _LEVEL_ATTRS:
            f = ctk.CTkFrame(self._frame, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=2)
            ctk.CTkLabel(f, text=label, width=150, anchor="w").pack(side="left")
            sv = ctk.StringVar(value=getattr(self._numbering, attr, "none"))
            ctk.CTkComboBox(
                f, variable=sv,
                values=_NUM_STYLES,
                command=lambda v, a=attr: self._set_num_str(a, v),
                width=200
            ).pack(side="right")

        sep_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        sep_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(sep_frame, text="编号分隔符", width=150, anchor="w").pack(side="left")
        sep_var = ctk.StringVar(value=self._numbering.separator)
        ctk.CTkEntry(sep_frame, textvariable=sep_var, width=120).pack(side="right")
        sep_var.trace_add("write", lambda *_: self._set_num_str("separator", sep_var))

    def _set_str(self, attr, var):
        try:
            setattr(self._toc, attr, var.get())
        except Exception:
            pass

    def _set_int(self, attr, var):
        try:
            setattr(self._toc, attr, int(var.get()))
        except (ValueError, TypeError):
            pass

    def _set_float(self, attr, var):
        try:
            setattr(self._toc, attr, float(var.get()))
        except (ValueError, TypeError):
            pass

    def _set_num_bool(self, attr, var):
        try:
            setattr(self._numbering, attr, var.get())
        except Exception:
            pass

    def _set_num_str(self, attr, value):
        try:
            if isinstance(value, str):
                setattr(self._numbering, attr, value)
        except Exception:
            pass

    def apply_to_config(self, config: AppConfig):
        config.toc = self._toc
        config.numbering = self._numbering

    def refresh_font_options(self):
        pass
