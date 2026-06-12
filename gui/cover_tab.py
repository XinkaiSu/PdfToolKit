# =============================================================================
#  cover_tab.py — 封面配置面板 + 实时预览
#  左侧：可滚动设置控件
#  右侧：封面 PDF 预览区域
# =============================================================================

import io
import os
import threading
from tkinter import filedialog, colorchooser

import customtkinter as ctk
from PIL import Image

from config import AppConfig, CoverConfig


# 预览区宽度（像素）
PREVIEW_WIDTH = 300


class CoverTab:
    """封面配置选项卡。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._app = app
        self._cover = config.cover
        self._preview_after_id = None
        self._preview_image = None

        # ── 主容器：左右分栏 ──
        self._main = ctk.CTkFrame(parent)
        self._main.pack(fill="both", expand=True)
        self._main.grid_columnconfigure(0, weight=1)
        self._main.grid_columnconfigure(1, weight=0)
        self._main.grid_rowconfigure(0, weight=1)

        # 左栏：可滚动设置
        self._left = ctk.CTkScrollableFrame(self._main, width=420)
        self._left.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)

        # 右栏：预览区
        self._right = ctk.CTkFrame(self._main, width=PREVIEW_WIDTH + 40)
        self._right.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)

        self._build_controls()
        self._build_preview()
        self._load_from_config()

        # 初始预览
        self.after(300, self._schedule_preview_refresh)

    # =========================================================================
    #  控件构建
    # =========================================================================

    def _section(self, text):
        """添加分组标题。"""
        ctk.CTkLabel(self._left, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _add_entry(self, label, attr, width=200):
        """添加文本输入框。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._cover, attr, "")))
        entry = ctk.CTkEntry(frame, textvariable=var, width=width)
        entry.pack(side="right")
        var.trace_add("write", lambda *_: self._on_change(attr, var))
        return var

    def _add_multiline_entry(self, label, attr, width=200, height=60):
        """添加多行文本输入框（CTkTextbox）。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        textbox = ctk.CTkTextbox(frame, width=width, height=height)
        textbox.pack(side="right")
        textbox.insert("0.0", str(getattr(self._cover, attr, "")))
        textbox.bind("<KeyRelease>", lambda _: self._on_text_change(attr, textbox))
        return textbox

    def _add_font_combo(self, label, attr, width=200):
        """添加字体下拉框。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        fonts = list(self._config.font.font_map.keys())
        var = ctk.StringVar(value=getattr(self._cover, attr, "SimHei"))
        combo = ctk.CTkComboBox(frame, variable=var, values=fonts, width=width)
        combo.pack(side="right")
        var.trace_add("write", lambda *_: self._on_change(attr, var))
        return var

    def _add_int_entry(self, label, attr, width=100):
        """添加整数输入框。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._cover, attr, 0)))
        entry = ctk.CTkEntry(frame, textvariable=var, width=width)
        entry.pack(side="right")
        var.trace_add("write", lambda *_: self._on_change_int(attr, var))
        return var

    def _add_float_entry(self, label, attr, width=100):
        """添加浮点数输入框。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        var = ctk.StringVar(value=str(getattr(self._cover, attr, 0)))
        entry = ctk.CTkEntry(frame, textvariable=var, width=width)
        entry.pack(side="right")
        var.trace_add("write", lambda *_: self._on_change_float(attr, var))
        return var

    def _add_slider(self, label, attr, from_=0.0, to=1.0):
        """添加滑块。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")
        var = ctk.DoubleVar(value=getattr(self._cover, attr, 0.5))
        slider = ctk.CTkSlider(frame, from_=from_, to=to, variable=var, width=200)
        slider.pack(side="right")
        var.trace_add("write", lambda *_: self._on_change_float(attr, var))
        return var

    def _add_checkbox(self, label, attr):
        """添加复选框。"""
        var = ctk.BooleanVar(value=getattr(self._cover, attr, False))
        cb = ctk.CTkCheckBox(self._left, text=label, variable=var)
        cb.pack(anchor="w", padx=10, pady=2)
        var.trace_add("write", lambda *_: self._on_change_bool(attr, var))
        return var

    def _add_color_button(self, label, attr, width=100):
        """添加颜色选择按钮。"""
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text=label, width=100, anchor="w").pack(side="left")

        color = getattr(self._cover, attr, [0, 0, 0])
        btn = ctk.CTkButton(
            frame, text="  ■  ", width=width,
            fg_color=self._rgb_to_hex(color),
            command=lambda: self._pick_color(attr, btn)
        )
        btn.pack(side="right")
        return btn

    def _build_controls(self):
        """构建所有设置控件。"""
        # ── 预览标题 ──
        self._section("预览标题")
        # 多行主标题输入框（不使用 textvariable，CTkTextbox 不支持）
        frame = ctk.CTkFrame(self._left, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(frame, text="主标题文本", width=100, anchor="w").pack(side="left")
        self._title_textbox = ctk.CTkTextbox(frame, width=200, height=60)
        self._title_textbox.pack(side="right")
        self._title_textbox.insert("0.0", "成果佐证材料")
        self._title_textbox.bind("<KeyRelease>", lambda _: self._on_title_text_change())

        # 主标题「使用目标文件夹名」复选框
        self._main_use_folder_var = ctk.BooleanVar(value=self._cover.main_title_use_folder)
        cb1 = ctk.CTkCheckBox(
            self._left, text="使用目标文件夹名",
            variable=self._main_use_folder_var,
            command=self._on_main_use_folder_toggle
        )
        cb1.pack(anchor="w", padx=20, pady=2)
        self._on_main_use_folder_toggle()  # 初始化状态

        # ── 主标题 ──
        self._section("主标题")
        self._add_font_combo("主标题字体", "main_title_font")
        self._add_int_entry("主标题字号", "main_title_size")
        self._add_slider("垂直位置", "main_title_y_ratio", 0.1, 0.9)

        # ── 副标题 ──
        self._section("副标题")
        # 副标题多行输入框
        sub_frame = ctk.CTkFrame(self._left, fg_color="transparent")
        sub_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(sub_frame, text="副标题文本", width=100, anchor="w").pack(side="left")
        self._subtitle_textbox = ctk.CTkTextbox(sub_frame, width=200, height=60)
        self._subtitle_textbox.pack(side="right")
        self._subtitle_textbox.insert("0.0", str(getattr(self._cover, "subtitle", "")))
        self._subtitle_textbox.bind("<KeyRelease>",
                                     lambda _: self._on_text_change("subtitle", self._subtitle_textbox))

        # 「使用目标文件夹名」复选框
        self._sub_use_folder_var = ctk.BooleanVar(value=self._cover.subtitle_use_folder)
        cb2 = ctk.CTkCheckBox(
            self._left, text="使用目标文件夹名",
            variable=self._sub_use_folder_var,
            command=self._on_sub_use_folder_toggle
        )
        cb2.pack(anchor="w", padx=20, pady=2)
        self._on_sub_use_folder_toggle()  # 初始化状态
        self._add_font_combo("副标题字体", "subtitle_font")
        self._add_int_entry("副标题字号", "subtitle_size")

        # ── 装饰线 ──
        self._section("页面装饰线")
        self._add_checkbox("显示装饰线", "show_border")
        self._add_float_entry("距边距离(mm)", "border_margin_mm")
        self._add_float_entry("线宽(pt)", "border_width")
        self._border_color_btn = self._add_color_button("装饰线颜色", "border_color")

        # ── Logo ──
        self._section("Logo")
        logo_frame = ctk.CTkFrame(self._left, fg_color="transparent")
        logo_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(logo_frame, text="Logo文件", width=100, anchor="w").pack(side="left")
        self._logo_path_var = ctk.StringVar(value=self._cover.logo_path)
        ctk.CTkButton(
            logo_frame, text="选择文件…", width=100,
            command=self._pick_logo
        ).pack(side="right", padx=(5, 0))
        self._logo_label = ctk.CTkLabel(logo_frame, text="未选择", width=95, anchor="w")
        self._logo_label.pack(side="right")
        if self._cover.logo_path:
            self._logo_label.configure(text=os.path.basename(self._cover.logo_path))

        self._add_float_entry("宽度(pt)", "logo_width")
        self._add_float_entry("高度(pt)", "logo_height")
        self._add_float_entry("左边距(mm)", "logo_margin_left_mm")
        self._add_float_entry("上边距(mm)", "logo_margin_top_mm")

        # ── 编制单位 ──
        self._section("编制单位")
        self._add_multiline_entry("标签文字", "unit_label")
        self._add_multiline_entry("单位名称", "unit_name")
        self._add_font_combo("字体", "unit_font")
        self._add_int_entry("标签字号", "unit_label_size")
        self._add_int_entry("名称字号", "unit_name_size")
        self._add_slider("垂直位置", "unit_y_ratio", 0.1, 0.9)

        # ── 日期 ──
        self._section("日期")
        self._add_multiline_entry("日期(留空自动)", "cover_date")
        self._add_font_combo("日期字体", "date_font")
        self._add_int_entry("日期字号", "date_size")
        self._add_slider("垂直位置", "date_y_ratio", 0.05, 0.95)

        # ── 右上角文字 ──
        self._section("右上角文字")
        self._add_multiline_entry("文字(留空隐藏)", "corner_text")
        self._add_font_combo("字体", "corner_text_font")
        self._add_int_entry("字号", "corner_text_size")
        self._corner_color_btn = self._add_color_button("文字颜色", "corner_text_color")
        self._add_float_entry("右边距(mm)", "corner_text_margin_right_mm")
        self._add_float_entry("上边距(mm)", "corner_text_margin_top_mm")

    def _build_preview(self):
        """构建预览区域。"""
        ctk.CTkLabel(self._right, text="封面预览",
                     font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))

        # 预览图像
        self._preview_label = ctk.CTkLabel(self._right, text="加载中…")
        self._preview_label.pack(padx=10, pady=5, fill="both", expand=True)

        # 刷新按钮
        ctk.CTkButton(
            self._right, text="刷新预览", width=120,
            command=self._force_refresh_preview
        ).pack(pady=(5, 10))

    # =========================================================================
    #  事件处理
    # =========================================================================

    def _on_change(self, attr, var):
        """字符串属性变更。"""
        try:
            setattr(self._cover, attr, var.get())
        except Exception:
            pass
        self._schedule_preview_refresh()

    def _on_text_change(self, attr, textbox):
        """多行文本属性变更。"""
        try:
            val = textbox.get("0.0", "end-1c")
            setattr(self._cover, attr, val)
        except Exception:
            pass
        self._schedule_preview_refresh()

    def _on_change_int(self, attr, var):
        """整数属性变更。"""
        try:
            setattr(self._cover, attr, int(var.get()))
        except (ValueError, TypeError):
            pass
        self._schedule_preview_refresh()

    def _on_change_float(self, attr, var):
        """浮点数属性变更。"""
        try:
            setattr(self._cover, attr, float(var.get()))
        except (ValueError, TypeError):
            pass
        self._schedule_preview_refresh()

    def _on_change_bool(self, attr, var):
        """布尔属性变更。"""
        try:
            setattr(self._cover, attr, var.get())
        except Exception:
            pass
        self._schedule_preview_refresh()

    def _on_title_text_change(self):
        """主标题文本变更，同步到 config。"""
        self._cover.title_text = self._title_textbox.get("0.0", "end-1c")
        self._schedule_preview_refresh()

    def _on_main_use_folder_toggle(self):
        """主标题「使用目标文件夹名」切换。"""
        use_folder = self._main_use_folder_var.get()
        self._cover.main_title_use_folder = use_folder
        if use_folder:
            self._title_textbox.configure(state="disabled")
        else:
            self._title_textbox.configure(state="normal")
        self._schedule_preview_refresh()

    def _on_sub_use_folder_toggle(self):
        """副标题「使用目标文件夹名」切换。"""
        use_folder = self._sub_use_folder_var.get()
        self._cover.subtitle_use_folder = use_folder
        if use_folder:
            self._subtitle_textbox.configure(state="disabled")
        else:
            self._subtitle_textbox.configure(state="normal")
        self._schedule_preview_refresh()

    def _pick_logo(self):
        """选择 Logo 文件。"""
        path = filedialog.askopenfilename(
            title="选择 Logo 图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"), ("所有文件", "*.*")],
            initialdir=os.path.dirname(self._cover.logo_path) if self._cover.logo_path else os.path.expanduser("~"),
        )
        if path:
            self._cover.logo_path = path
            self._logo_path_var.set(path)
            self._logo_label.configure(text=os.path.basename(path))
            self._schedule_preview_refresh()

    def _pick_color(self, attr, btn):
        """弹出颜色选择器。"""
        current = getattr(self._cover, attr, [0, 0, 0])
        initial = self._rgb_to_hex_int(current)
        result = colorchooser.askcolor(initialcolor=initial, title="选择颜色")
        if result[0]:
            r, g, b = [x / 255.0 for x in result[0]]
            setattr(self._cover, attr, [r, g, b])
            btn.configure(fg_color=self._rgb_to_hex([r, g, b]))
            self._schedule_preview_refresh()

    # =========================================================================
    #  预览
    # =========================================================================

    def _schedule_preview_refresh(self):
        """防抖：500ms 后刷新预览。"""
        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
        self._preview_after_id = self.after(500, self._do_preview_refresh)

    def _force_refresh_preview(self):
        """强制立即刷新预览。"""
        if self._preview_after_id:
            self.after_cancel(self._preview_after_id)
            self._preview_after_id = None
        self._do_preview_refresh()

    def _do_preview_refresh(self):
        """在子线程中渲染预览。"""
        self._preview_after_id = None
        thread = threading.Thread(target=self._render_preview, daemon=True)
        thread.start()

    def _render_preview(self):
        """子线程：生成封面预览图像。"""
        try:
            from methods.cover import generate_cover_preview
            title = self._title_textbox.get("0.0", "end-1c") or "成果佐证材料"
            png_bytes = generate_cover_preview(self._cover, title, self._config, dpi=72)
            # 回到主线程更新
            self.after(0, self._update_preview_image, png_bytes)
        except Exception as e:
            self.after(0, self._update_preview_error, str(e))

    def _update_preview_image(self, png_bytes: bytes):
        """主线程：更新预览图像。"""
        try:
            img = Image.open(io.BytesIO(png_bytes))
            # 按预览区宽度等比缩放
            ratio = PREVIEW_WIDTH / img.width
            new_h = int(img.height * ratio)
            img = img.resize((PREVIEW_WIDTH, new_h), Image.Resampling.LANCZOS)
            self._preview_image = ctk.CTkImage(light_image=img, size=(PREVIEW_WIDTH, new_h))
            self._preview_label.configure(image=self._preview_image, text="")
        except Exception as e:
            self._preview_label.configure(image=None, text=f"预览失败：{e}")

    def _update_preview_error(self, error: str):
        """主线程：显示预览错误。"""
        self._preview_label.configure(image=None, text=f"预览失败：{error}")

    # =========================================================================
    #  配置读写
    # =========================================================================

    def apply_to_config(self, config: AppConfig):
        """将当前设置写回配置对象。"""
        config.cover = self._cover

    def _load_from_config(self):
        """从配置对象加载设置（初始化时已通过 _cover 绑定）。"""
        pass

    def refresh_font_options(self):
        """刷新字体下拉框选项。"""
        # 字体列表在初始化时已生成，运行时如字体映射变更需刷新
        pass

    # =========================================================================
    #  工具方法
    # =========================================================================

    def after(self, ms, func=None, *args):
        """代理到主窗口的 after 方法。"""
        if self._app:
            return self._app.after(ms, func, *args)
        return None

    def after_cancel(self, id):
        """代理到主窗口的 after_cancel 方法。"""
        if self._app and id:
            try:
                self._app.after_cancel(id)
            except Exception:
                pass

    @staticmethod
    def _rgb_to_hex(color):
        """RGB [0-1] 列表转十六进制颜色字符串。"""
        r, g, b = [max(0, min(255, int(c * 255))) for c in color]
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _rgb_to_hex_int(color):
        """RGB [0-1] 列表转 tkinter 可用的整数元组。"""
        return tuple(max(0, min(255, int(c * 255))) for c in color)
