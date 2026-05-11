# =============================================================================
#  path_tab.py — 路径与高级选项卡
# =============================================================================

import os

import customtkinter as ctk
from tkinter import filedialog

from config import AppConfig


class PathTab:
    """路径与高级选项卡。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._path = config.path
        self._adv = config.advanced
        self._app = app

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_path_entry(self, label, attr):
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        var = ctk.StringVar(value=getattr(self._path, attr, ""))
        ctk.CTkEntry(frame, textvariable=var, width=350).pack(
            side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(frame, text="浏览…", width=70,
                      command=lambda: self._browse_path(attr, var)).pack(side="right")
        var.trace_add("write", lambda *_: self._set_path(attr, var))
        return var

    def _add_checkbox(self, label, attr, obj=None):
        target = obj or self._adv
        var = ctk.BooleanVar(value=getattr(target, attr, False))
        ctk.CTkCheckBox(self._frame, text=label, variable=var).pack(
            anchor="w", padx=10, pady=2)
        var.trace_add("write", lambda *_: self._set_bool_attr(attr, var, target))

    def _add_entry(self, label, attr, obj=None):
        target = obj or self._adv
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(target, attr, "")))
        ctk.CTkEntry(frame, textvariable=var, width=300).pack(side="right")
        var.trace_add("write", lambda *_: self._set_str_attr(attr, var, target))

    def _add_int_entry(self, label, attr, obj=None):
        target = obj or self._adv
        frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=120, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(target, attr, 0)))
        ctk.CTkEntry(frame, textvariable=var, width=120).pack(side="right")
        var.trace_add("write", lambda *_: self._set_int_attr(attr, var, target))

    def _build(self):
        self._section("路径配置")
        # 醒目的选择目标文件夹按钮
        pick_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        pick_frame.pack(fill="x", padx=10, pady=(4, 4))
        ctk.CTkButton(
            pick_frame, text="选择目标文件夹…", width=200,
            fg_color="#3498db", hover_color="#2980b9",
            command=self._pick_target_folder
        ).pack(side="left", padx=(0, 10))

        self._input_var = self._add_path_entry("输入目录", "input_root")
        self._input_var.trace_add("write", lambda *_: self._notify_file_list())
        self._add_path_entry("输出目录", "output_root")

        # 合并模式
        self._section("合并模式")
        mode_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(mode_frame, text="合并方式", width=120, anchor="w").pack(side="left")
        _MODE_MAP = {"per_subfolder": "按子文件夹", "single": "整体合并"}
        _MODE_REVERSE = {v: k for k, v in _MODE_MAP.items()}
        self._mode_display = _MODE_MAP
        self._mode_reverse = _MODE_REVERSE
        display_value = _MODE_MAP.get(self._adv.merge_mode, "按子文件夹")
        self._merge_mode_var = ctk.StringVar(value=display_value)
        ctk.CTkSegmentedButton(
            mode_frame,
            variable=self._merge_mode_var,
            values=list(_MODE_MAP.values()),
            command=self._on_merge_mode_change,
        ).pack(side="right", fill="x", expand=True)

        # 图片合并
        self._section("文件类型")
        self._add_checkbox("包含图片文件（PNG/JPG/BMP/TIFF/GIF）", "include_images")

        self._section("图片化模式（签名PDF兼容）")
        self._add_checkbox("启用图片化模式", "enable_image_convert")
        self._add_entry("Poppler路径", "poppler_path")
        self._add_int_entry("DPI分辨率", "image_dpi")

        self._section("其他设置")
        self._add_checkbox("过滤特殊字符", "remove_special_chars")
        self._add_checkbox("启用中文序号排序", "enable_chinese_sort")

        self._section("配置管理")
        btn_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(btn_frame, text="保存配置", width=100,
                      command=self._save_config).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="加载配置", width=100,
                      command=self._load_config).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="重置默认", width=100,
                      command=self._reset_config).pack(side="left")

    # ── 合并模式 ──

    def _on_merge_mode_change(self, value):
        self._adv.merge_mode = self._mode_reverse.get(value, "per_subfolder")

    def _notify_file_list(self):
        if self._app and hasattr(self._app, "_file_list_tab"):
            self._app._file_list_tab.refresh_file_list()

    # ── 实用方法 ──

    def _pick_target_folder(self):
        """选择目标文件夹，自动填充输入和输出目录。"""
        path = filedialog.askdirectory(title="选择目标文件夹")
        if path:
            self._path.input_root = path
            self._input_var.set(path)
            if not self._path.output_root:
                default_out = os.path.join(os.path.dirname(path), "output")
                self._path.output_root = default_out
            if self._app and hasattr(self._app, '_file_list_tab'):
                self._app._file_list_tab.refresh_file_list()
            if self._app:
                self._app.log(f"[i] 目标文件夹：{path}")

    def _browse_path(self, attr, var):
        path = filedialog.askdirectory(title="选择目录")
        if path:
            var.set(path)
            setattr(self._path, attr, path)

    def _set_path(self, attr, var):
        try:
            setattr(self._path, attr, var.get())
        except Exception:
            pass

    def _set_str_attr(self, attr, var, obj):
        try:
            setattr(obj, attr, var.get())
        except Exception:
            pass

    def _set_int_attr(self, attr, var, obj):
        try:
            setattr(obj, attr, int(var.get()))
        except (ValueError, TypeError):
            pass

    def _set_bool_attr(self, attr, var, obj):
        try:
            setattr(obj, attr, var.get())
        except Exception:
            pass

    def _save_config(self):
        try:
            self._config.save()
            if self._app:
                self._app.log("✅ 配置已保存")
        except Exception as e:
            if self._app:
                self._app.log(f"❌ 保存配置失败：{e}")

    def _load_config(self):
        try:
            new_config = AppConfig.load()
            self._config.cover = new_config.cover
            self._config.toc = new_config.toc
            self._config.page_num = new_config.page_num
            self._config.font = new_config.font
            self._config.path = new_config.path
            self._config.advanced = new_config.advanced
            self._config.numbering = new_config.numbering
            if self._app:
                self._app.log("✅ 配置已加载，重启界面后生效")
        except Exception as e:
            if self._app:
                self._app.log(f"❌ 加载配置失败：{e}")

    def _reset_config(self):
        defaults = AppConfig.get_defaults()
        self._config.cover = defaults.cover
        self._config.toc = defaults.toc
        self._config.page_num = defaults.page_num
        self._config.font = defaults.font
        self._config.path = defaults.path
        self._config.advanced = defaults.advanced
        self._config.numbering = defaults.numbering
        if self._app:
            self._app.log("ℹ️ 已重置为默认配置，重启界面后生效")

    def apply_to_config(self, config: AppConfig):
        config.path = self._path
        config.advanced = self._adv

    def refresh_font_options(self):
        pass
