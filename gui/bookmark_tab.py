# =============================================================================
#  bookmark_tab.py — PDF书签设置选项卡
# =============================================================================

import customtkinter as ctk

from config import AppConfig


class BookmarkTab:
    """PDF书签设置选项卡。"""

    def __init__(self, parent, config: AppConfig):
        self._config = config
        self._bm = config.bookmark

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_checkbox(self, label, attr):
        var = ctk.BooleanVar(value=getattr(self._bm, attr, False))
        ctk.CTkCheckBox(self._frame, text=label, variable=var).pack(
            anchor="w", padx=10, pady=2)
        var.trace_add("write", lambda *_: self._set_bool(attr, var))
        return var

    def _add_int_entry(self, label, attr, unit=""):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=f"{label}({unit})" if unit else label,
                     width=200, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._bm, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_int(attr, var))

    def _build(self):
        self._section("基本设置")
        self._add_checkbox("启用PDF书签", "enabled")

        self._section("书签来源")
        self._add_checkbox("保留源PDF书签", "preserve_source")
        self._add_checkbox("文件夹名作为书签", "folder_as_bookmark")
        self._add_checkbox("文件名作为书签", "filename_as_bookmark")

        self._section("层级设置")
        self._add_int_entry("最大文件夹深度", "max_folder_depth", "级")

        self._section("展开状态")
        self._add_checkbox("文件夹书签默认展开", "folder_open")
        self._add_checkbox("文件书签默认展开", "file_open")

    def _set_bool(self, attr, var):
        try:
            setattr(self._bm, attr, var.get())
        except Exception:
            pass

    def _set_int(self, attr, var):
        try:
            setattr(self._bm, attr, int(var.get()))
        except (ValueError, TypeError):
            pass

    def apply_to_config(self, config: AppConfig):
        config.bookmark = self._bm

    def refresh_font_options(self):
        pass
