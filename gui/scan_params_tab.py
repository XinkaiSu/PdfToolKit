# =============================================================================
#  gui/scan_params_tab.py — 扫描模式：参数面板
# =============================================================================

import customtkinter as ctk

from config import AppConfig


_PRESET_LABELS = [("light", "轻度"), ("medium", "中度"),
                  ("heavy", "重度"), ("custom", "自定义")]
_LABEL_TO_KEY = {v: k for k, v in _PRESET_LABELS}
_KEY_TO_LABEL = {k: v for k, v in _PRESET_LABELS}

_DPI_VALUES = ["100", "200", "300", "400", "500", "600"]


class ScanParamsTab:
    """扫描模式 — 渲染 DPI、强度预设、自定义参数。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._scan = config.scan
        self._app = app

        self._frame = ctk.CTkScrollableFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._custom_widgets = []
        self._build()
        self._on_preset_change(_KEY_TO_LABEL.get(self._scan.preset, "中度"))

    def _section(self, text):
        ctk.CTkLabel(self._frame, text=f"── {text} ──",
                     font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4))

    def _build(self):
        # ── 渲染 ──
        self._section("渲染")

        dpi_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        dpi_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(dpi_frame, text="渲染 DPI", width=110, anchor="w").pack(side="left")
        self._dpi_var = ctk.StringVar(value=str(self._scan.dpi))
        ctk.CTkOptionMenu(
            dpi_frame, variable=self._dpi_var, values=_DPI_VALUES,
            command=lambda v: setattr(self._scan, "dpi", int(v)),
        ).pack(side="left", padx=5)

        # ── 强度预设 ──
        self._section("扫描效果")

        preset_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        preset_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(preset_frame, text="强度预设", width=110, anchor="w").pack(side="left")
        self._preset_var = ctk.StringVar(value=_KEY_TO_LABEL.get(self._scan.preset, "中度"))
        ctk.CTkSegmentedButton(
            preset_frame, variable=self._preset_var,
            values=["轻度", "中度", "重度", "自定义"],
            command=self._on_preset_change,
        ).pack(side="left", padx=5)

        # ── 自定义参数容器 ──
        self._custom_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        self._custom_frame.pack(fill="x", padx=10, pady=(8, 4))

        # askew
        self._askew_var = ctk.BooleanVar(value=self._scan.askew)
        cb_askew = ctk.CTkCheckBox(self._custom_frame, text="倾斜 (askew)",
                                   variable=self._askew_var)
        cb_askew.pack(anchor="w", pady=2)
        self._askew_var.trace_add("write",
            lambda *_: setattr(self._scan, "askew", self._askew_var.get()))
        self._custom_widgets.append(cb_askew)

        # 滑块封装
        self._add_slider("噪点", "noise", 0, 50, int)
        self._add_slider("亮度", "brightness", 0.5, 2.0, float)
        self._add_slider("对比度", "contrast", 0.5, 2.0, float)
        self._add_slider("锐度", "sharpness", 0.5, 3.0, float)
        self._add_slider("JPEG 质量", "jpeg_quality", 50, 100, int)

        # 黑白 / 模糊 / 景深
        for label, attr in (("黑白（复印件感）", "black_and_white"),
                            ("整体模糊", "blur"),
                            ("景深模糊（半幅虚化）", "blur_variation")):
            var = ctk.BooleanVar(value=getattr(self._scan, attr))
            cb = ctk.CTkCheckBox(self._custom_frame, text=label, variable=var)
            cb.pack(anchor="w", pady=2)
            var.trace_add("write",
                lambda *_, v=var, a=attr: setattr(self._scan, a, v.get()))
            self._custom_widgets.append(cb)

    def _add_slider(self, label, attr, lo, hi, cast):
        row = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=label, width=90, anchor="w").pack(side="left")
        cur = getattr(self._scan, attr)
        var = ctk.DoubleVar(value=float(cur))
        val_label = ctk.CTkLabel(row, text=f"{cast(cur)}", width=50)
        slider_kwargs = dict(from_=lo, to=hi, variable=var, width=200)
        if cast is int:
            # 整数滑块按 1 取整，避免拖到 5.7 显示成 5、再拖一下没变化
            slider_kwargs["number_of_steps"] = int(hi - lo)
        slider = ctk.CTkSlider(row, **slider_kwargs)
        slider.pack(side="left", padx=5)
        val_label.pack(side="left", padx=5)

        def _update(*_):
            v = cast(var.get())
            setattr(self._scan, attr, v)
            val_label.configure(text=f"{v}" if cast is int else f"{v:.2f}")

        var.trace_add("write", _update)
        self._custom_widgets.append(slider)
        self._custom_widgets.append(val_label)

    def _on_preset_change(self, label):
        key = _LABEL_TO_KEY.get(label, "medium")
        self._scan.preset = key
        # 启/禁用自定义控件
        state = "normal" if key == "custom" else "disabled"
        for w in self._custom_widgets:
            try:
                w.configure(state=state)
            except Exception:
                pass

    def apply_to_config(self, config: AppConfig):
        config.scan = self._scan
