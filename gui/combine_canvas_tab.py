# =============================================================================
#  combine_canvas_tab.py — 拼接画布：可视化预览 + 数值微调
# =============================================================================

import os
import tkinter as tk
import tkinter.ttk as ttk

import customtkinter as ctk
import numpy as np
from PIL import Image, ImageTk

from config import AppConfig


class CombineCanvasTab:
    """拼图模式 — 拼接画布：左侧预览 + 右侧数值微调面板。"""

    PREVIEW_MAX_WIDTH = 600

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._combine = config.combine
        self._app = app

        self._frame = ctk.CTkFrame(parent)

        self._segments = []
        self._positions = []
        self._canvas_items = []
        self._drag_data = {}
        self._updating = False
        self._pos_vars = []   # 每段的 (x_var, y_var) StringVar 列表

        self._build()

    def _build(self):
        # ── 顶部按钮行 ──
        btn_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=(5, 0))

        self._preprocess_btn = ctk.CTkButton(
            btn_frame, text="预处理", width=90,
            command=self._on_preprocess)
        self._preprocess_btn.pack(side="left", padx=(0, 5))

        ctk.CTkButton(
            btn_frame, text="自动排列", width=90,
            command=self._on_auto_layout).pack(side="left", padx=(0, 5))

        self._status_label = ctk.CTkLabel(btn_frame, text="请先点击「预处理」预览方位",
                                           text_color="gray")
        self._status_label.pack(side="right", padx=5)

        # ── 主区域：左画布 + 右面板 ──
        main_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # 左侧画布
        canvas_frame = ctk.CTkFrame(main_frame)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        canvas_frame.grid_columnconfigure(0, weight=1)
        canvas_frame.grid_rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(canvas_frame, bg="#d0d0d0",
                                 highlightthickness=0)
        h_scroll = ttk.Scrollbar(canvas_frame, orient="horizontal",
                                 command=self._canvas.xview)
        v_scroll = ttk.Scrollbar(canvas_frame, orient="vertical",
                                 command=self._canvas.yview)
        self._canvas.configure(xscrollcommand=h_scroll.set,
                               yscrollcommand=v_scroll.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # 保留拖拽（右侧面板为主微调方式）
        self._canvas.bind("<ButtonPress-1>", self._on_press)
        self._canvas.bind("<B1-Motion>", self._on_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_release)

        # 右侧数值面板
        right_frame = ctk.CTkFrame(main_frame, width=240)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.grid_propagate(False)

        self._right_inner = ctk.CTkScrollableFrame(right_frame, width=220)
        self._right_inner.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(self._right_inner, text="位置微调",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(5, 5))

        self._adjust_panel = ctk.CTkFrame(self._right_inner, fg_color="transparent")
        self._adjust_panel.pack(fill="both", expand=True)

        ctk.CTkLabel(self._adjust_panel, text="预处理后在此调整",
                     text_color="gray").pack(padx=5, pady=20)

    # ── 预处理 ──

    def _on_preprocess(self):
        """渲染 PDF、去背景、检测偏移、在画布上显示。"""
        if len(self._combine.input_files) < 2:
            if self._app:
                self._app.log("[X] 至少需要 2 个输入文件")
            return

        self._status_label.configure(text="预处理中…")
        self._frame.update_idletasks()

        try:
            from methods.combine import preprocess_combine, compute_positions_from_offsets
            self._segments = preprocess_combine(self._combine)
            self._positions = compute_positions_from_offsets(self._segments)
        except Exception as e:
            if self._app:
                self._app.log(f"[X] 预处理失败: {e}")
            self._status_label.configure(text="预处理失败")
            return

        self._build_adjust_panel()
        self._display_on_canvas()
        n = len(self._segments)
        self._status_label.configure(text=f"已加载 {n} 个文件，右侧面板可微调位置")

    def _on_auto_layout(self):
        """重新计算自动偏移并排列。"""
        if not self._segments:
            return
        from methods.combine import compute_positions_from_offsets
        self._positions = compute_positions_from_offsets(self._segments)
        self._sync_vars_from_positions()
        self._display_on_canvas()

    # ── 右侧数值面板构建 ──

    def _build_adjust_panel(self):
        """根据 _segments 构建数值微调面板。"""
        for w in self._adjust_panel.winfo_children():
            w.destroy()
        self._pos_vars = []

        for idx, seg in enumerate(self._segments):
            px, py = self._positions[idx]
            name = os.path.basename(seg["path"])

            # 段标题
            seg_frame = ctk.CTkFrame(self._adjust_panel)
            seg_frame.pack(fill="x", padx=2, pady=(8 if idx > 0 else 0, 2))

            ctk.CTkLabel(seg_frame, text=f"#{idx+1} {name}",
                         font=ctk.CTkFont(weight="bold", size=12),
                         anchor="w").pack(fill="x", padx=5, pady=(4, 2))

            # X 输入行
            x_var = ctk.StringVar(value=str(px))
            self._pos_vars.append((x_var, None))
            x_row = ctk.CTkFrame(seg_frame, fg_color="transparent")
            x_row.pack(fill="x", padx=5, pady=1)
            ctk.CTkLabel(x_row, text="X:", width=20, anchor="w").pack(side="left")
            x_entry = ctk.CTkEntry(x_row, textvariable=x_var, width=80)
            x_entry.pack(side="left", padx=(0, 5))
            ctk.CTkButton(x_row, text="▲", width=28, height=24,
                          command=lambda i=idx, axis='x', d=-1: self._nudge(i, axis, d)
                          ).pack(side="left", padx=1)
            ctk.CTkButton(x_row, text="▼", width=28, height=24,
                          command=lambda i=idx, axis='x', d=1: self._nudge(i, axis, d)
                          ).pack(side="left", padx=1)

            # Y 输入行
            y_var = ctk.StringVar(value=str(py))
            self._pos_vars[idx] = (x_var, y_var)
            y_row = ctk.CTkFrame(seg_frame, fg_color="transparent")
            y_row.pack(fill="x", padx=5, pady=(1, 4))
            ctk.CTkLabel(y_row, text="Y:", width=20, anchor="w").pack(side="left")
            y_entry = ctk.CTkEntry(y_row, textvariable=y_var, width=80)
            y_entry.pack(side="left", padx=(0, 5))
            ctk.CTkButton(y_row, text="▲", width=28, height=24,
                          command=lambda i=idx, axis='y', d=-1: self._nudge(i, axis, d)
                          ).pack(side="left", padx=1)
            ctk.CTkButton(y_row, text="▼", width=28, height=24,
                          command=lambda i=idx, axis='y', d=1: self._nudge(i, axis, d)
                          ).pack(side="left", padx=1)

            # 输入框变化时同步到 _positions
            x_var.trace_add("write", lambda *_, i=idx: self._on_var_change(i))
            y_var.trace_add("write", lambda *_, i=idx: self._on_var_change(i))

    def _nudge(self, idx, axis, direction):
        """按钮微调 ±1px。"""
        step = 1
        x_var, y_var = self._pos_vars[idx]
        if axis == 'x':
            try:
                cur = int(x_var.get())
                x_var.set(str(cur + direction * step))
            except (ValueError, TypeError):
                pass
        else:
            try:
                cur = int(y_var.get())
                y_var.set(str(cur + direction * step))
            except (ValueError, TypeError):
                pass

    def _on_var_change(self, idx):
        """输入框变化时同步到 _positions 并刷新画布。"""
        if self._updating:
            return
        if idx >= len(self._pos_vars):
            return
        x_var, y_var = self._pos_vars[idx]
        try:
            x = int(x_var.get())
            y = int(y_var.get())
            self._positions[idx] = (x, y)
            self._display_on_canvas()
        except (ValueError, TypeError):
            pass

    def _sync_vars_from_positions(self):
        """将 _positions 同步到输入框变量。"""
        self._updating = True
        for idx, (px, py) in enumerate(self._positions):
            if idx < len(self._pos_vars):
                x_var, y_var = self._pos_vars[idx]
                x_var.set(str(px))
                y_var.set(str(py))
        self._updating = False

    # ── 画布显示 ──

    def _display_on_canvas(self):
        """根据 _segments 和 _positions 刷新画布。"""
        self._canvas.delete("all")
        self._canvas_items = []

        if not self._segments:
            return

        max_orig_w = max(seg["orig_img"].width for seg in self._segments)
        preview_scale = min(1.0, self.PREVIEW_MAX_WIDTH / max_orig_w)

        max_x = max(pos[0] + seg["orig_img"].width
                     for pos, seg in zip(self._positions, self._segments))
        max_y = max(pos[1] + seg["orig_img"].height
                     for pos, seg in zip(self._positions, self._segments))

        self._canvas.configure(scrollregion=(0, 0, max_x * preview_scale, max_y * preview_scale))

        for idx, (seg, (px, py)) in enumerate(zip(self._segments, self._positions)):
            rgba = seg["rgba_img"]
            tw = max(1, int(rgba.width * preview_scale))
            th = max(1, int(rgba.height * preview_scale))
            thumb_rgba = rgba.resize((tw, th), Image.LANCZOS)
            bg = Image.new("RGBA", (tw, th), (200, 200, 200, 255))
            bg.paste(thumb_rgba, (0, 0), thumb_rgba)
            thumb_rgb = bg.convert("RGB")
            thumb_tk = ImageTk.PhotoImage(thumb_rgb)

            cx = px * preview_scale
            cy = py * preview_scale
            item_id = self._canvas.create_image(
                cx, cy, anchor="nw", image=thumb_tk)

            label = os.path.basename(seg["path"])
            text_id = self._canvas.create_text(
                cx + 4, cy + 4, anchor="nw", text=label,
                font=("Microsoft YaHei UI", 8), fill="blue")

            self._canvas_items.append({
                "canvas_id": item_id,
                "text_id": text_id,
                "thumb": thumb_tk,
                "seg_idx": idx,
            })

    # ── 拖拽（保留，但右侧面板为主微调方式） ──

    def _on_press(self, event):
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        items = self._canvas.find_overlapping(cx - 2, cy - 2, cx + 2, cy + 2)
        if not items:
            self._drag_data = {}
            return
        for ci in self._canvas_items:
            if ci["canvas_id"] in items:
                self._drag_data = {
                    "seg_idx": ci["seg_idx"],
                    "start_cx": cx,
                    "start_cy": cy,
                    "start_px": self._positions[ci["seg_idx"]][0],
                    "start_py": self._positions[ci["seg_idx"]][1],
                }
                return
        self._drag_data = {}

    def _on_motion(self, event):
        if not self._drag_data:
            return
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        idx = self._drag_data["seg_idx"]
        max_orig_w = max(seg["orig_img"].width for seg in self._segments) if self._segments else 1
        preview_scale = min(1.0, self.PREVIEW_MAX_WIDTH / max_orig_w)
        dx = (cx - self._drag_data["start_cx"]) / preview_scale
        dy = (cy - self._drag_data["start_cy"]) / preview_scale
        new_x = int(self._drag_data["start_px"] + dx)
        new_y = int(self._drag_data["start_py"] + dy)
        self._positions[idx] = (new_x, new_y)
        # 仅移动被拖拽项的画布坐标，不做全量重绘
        canvas_cx = new_x * preview_scale
        canvas_cy = new_y * preview_scale
        for ci in self._canvas_items:
            if ci["seg_idx"] == idx:
                self._canvas.coords(ci["canvas_id"], canvas_cx, canvas_cy)
                self._canvas.coords(ci["text_id"], canvas_cx + 4, canvas_cy + 4)
                break

    def _on_release(self, event):
        if not self._drag_data:
            return
        self._drag_data = {}
        self._sync_vars_from_positions()
        self._display_on_canvas()

    # ── 配置 ──

    def apply_to_config(self, config: AppConfig):
        config.combine = self._combine
