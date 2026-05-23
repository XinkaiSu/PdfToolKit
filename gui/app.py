# =============================================================================
#  app.py — 主窗口框架
#  顶部模式栏 + 左侧导航 + 右侧内容区 + 底部控制/日志
# =============================================================================

import os
import sys
import threading
import queue

import customtkinter as ctk

from config import AppConfig
from .cover_tab import CoverTab
from .toc_tab import TocTab
from .pagenum_tab import PageNumTab
from .font_tab import FontTab
from .path_tab import PathTab
from .filelist_tab import FileListTab
from .bookmark_tab import BookmarkTab
from .combine_filelist_tab import CombineFileListTab
from .combine_params_tab import CombineParamsTab
from .combine_canvas_tab import CombineCanvasTab
from .home_tab import HomeTab


# ── 模式定义 ──────────────────────────────────────────────────────────────────

_MERGE_ITEMS = ["路径", "封面配置", "目录设置", "页码设置", "字体设置", "PDF书签", "文件列表"]
_COMBINE_ITEMS = ["文件列表", "参数设置", "拼接画布"]
_MODE_ITEMS = {
    "合并": _MERGE_ITEMS,
    "拼图": _COMBINE_ITEMS,
}

NAV_WIDTH = 150
NAV_ITEM_HEIGHT = 36


class PdfToolKitApp(ctk.CTk):
    """PDF 批量合并工具主窗口。"""

    def __init__(self):
        super().__init__()

        self._config = AppConfig.load()
        self._stop_event = threading.Event()
        self._log_queue = queue.Queue()
        self._running = False
        self._current_mode = "首页"
        self._current_nav = ""

        # 窗口设置
        from main import __version__
        self.title(f"PDF 批量合并工具 v{__version__}")
        self.geometry("1100x750")
        self.minsize(900, 600)

        # 设置窗口图标
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "gui", "icon.ico")
        else:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # 居中显示
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{x}+{y}")

        self._build_ui()

        # 定期刷新日志
        self._poll_log_queue()

        # 关闭时保存配置
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    #  UI 构建
    # =========================================================================

    def _build_ui(self):
        # ── 顶部模式栏 ──
        mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        mode_frame.pack(fill="x", padx=10, pady=(10, 0))

        self._mode_var = ctk.StringVar(value="首页")
        self._mode_btn = ctk.CTkSegmentedButton(
            mode_frame,
            variable=self._mode_var,
            values=["首页", "合并", "拼图"],
            command=self._on_mode_change,
        )
        self._mode_btn.pack(side="left")

        # ── 中间区域：左侧导航 + 右侧内容 ──
        mid_frame = ctk.CTkFrame(self, fg_color="transparent")
        mid_frame.pack(fill="both", expand=True, padx=10, pady=(5, 0))
        mid_frame.grid_columnconfigure(1, weight=1)
        mid_frame.grid_rowconfigure(0, weight=1)

        # 左侧导航
        self._nav_frame = ctk.CTkFrame(mid_frame, width=NAV_WIDTH, corner_radius=8)
        self._nav_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self._nav_frame.grid_propagate(False)

        # 右侧内容区
        self._content_frame = ctk.CTkFrame(mid_frame, corner_radius=8)
        self._content_frame.grid(row=0, column=1, sticky="nsew")

        # 初始化面板
        self._init_panels()

        # 构建导航（首页模式时隐藏）
        self._build_nav()
        self._nav_frame.grid_remove()

        # ── 底部控制区 ──
        self._build_bottom()

    def _init_panels(self):
        """预创建所有面板实例（首页 + 合并7个 + 拼图3个）。"""
        # 首页面板
        self._home_panel = HomeTab(self._content_frame, self._config, app=self)

        # 合并模式面板
        self._merge_panels = {}
        self._merge_panels["路径"] = PathTab(self._content_frame, self._config, app=self)
        self._merge_panels["封面配置"] = CoverTab(self._content_frame, self._config, app=self)
        self._merge_panels["目录设置"] = TocTab(self._content_frame, self._config)
        self._merge_panels["页码设置"] = PageNumTab(self._content_frame, self._config)
        self._merge_panels["字体设置"] = FontTab(self._content_frame, self._config)
        self._merge_panels["PDF书签"] = BookmarkTab(self._content_frame, self._config)
        self._merge_panels["文件列表"] = FileListTab(self._content_frame, self._config, app=self)

        # 拼图模式面板
        self._combine_panels = {}
        self._combine_panels["文件列表"] = CombineFileListTab(self._content_frame, self._config, app=self)
        self._combine_panels["参数设置"] = CombineParamsTab(self._content_frame, self._config, app=self)
        self._combine_panels["拼接画布"] = CombineCanvasTab(self._content_frame, self._config, app=self)

        # 隐藏所有面板
        self._hide_all_panels()
        # 显示首页
        self._home_panel._frame.pack(in_=self._content_frame, fill="both", expand=True, padx=5, pady=5)

    def _hide_all_panels(self):
        """隐藏所有面板 widget。"""
        self._home_panel._frame.pack_forget()
        for panel in self._merge_panels.values():
            if hasattr(panel, '_main'):
                panel._main.pack_forget()
            elif hasattr(panel, '_frame'):
                panel._frame.pack_forget()
        for panel in self._combine_panels.values():
            if hasattr(panel, '_frame'):
                panel._frame.pack_forget()

    def _build_nav(self):
        """根据当前模式构建左侧导航按钮。"""
        for widget in self._nav_frame.winfo_children():
            widget.destroy()

        items = _MODE_ITEMS.get(self._current_mode, [])
        self._nav_buttons = {}

        for i, name in enumerate(items):
            is_selected = (name == self._current_nav)
            btn = ctk.CTkButton(
                self._nav_frame,
                text=name,
                width=NAV_WIDTH - 10,
                height=NAV_ITEM_HEIGHT,
                anchor="w",
                fg_color=("#3b8ed0", "#1f6aa5") if is_selected else "transparent",
                text_color=("gray10", "gray90") if is_selected else ("gray40", "gray60"),
                hover_color=("gray75", "gray30"),
                command=lambda n=name: self._on_nav_click(n),
            )
            btn.pack(padx=5, pady=(5 if i == 0 else 2, 2), fill="x")
            self._nav_buttons[name] = btn

    def _on_nav_click(self, name):
        """点击左侧导航项。"""
        self._current_nav = name
        self._show_panel(name)
        self._build_nav()

    def _show_panel(self, name):
        """显示指定面板，隐藏其他面板。"""
        # 隐藏所有
        self._home_panel._frame.pack_forget()
        for panel in self._merge_panels.values():
            if hasattr(panel, '_main'):
                panel._main.pack_forget()
            elif hasattr(panel, '_frame'):
                panel._frame.pack_forget()
        for panel in self._combine_panels.values():
            if hasattr(panel, '_frame'):
                panel._frame.pack_forget()

        # 显示目标面板
        panels = self._merge_panels if self._current_mode == "合并" else self._combine_panels
        panel = panels.get(name)
        if panel:
            if hasattr(panel, '_main'):
                panel._main.pack(in_=self._content_frame, fill="both", expand=True, padx=5, pady=5)
            elif hasattr(panel, '_frame'):
                panel._frame.pack(in_=self._content_frame, fill="both", expand=True, padx=5, pady=5)

    def _on_mode_change(self, value):
        """顶部模式栏切换。"""
        self._current_mode = value
        if value == "首页":
            # 首页模式：隐藏导航，显示首页
            self._nav_frame.grid_remove()
            self._hide_all_panels()
            self._home_panel._frame.pack(in_=self._content_frame, fill="both", expand=True, padx=5, pady=5)
        else:
            # 合并/拼图模式：隐藏首页，显示导航
            self._home_panel._frame.pack_forget()
            self._nav_frame.grid()
            items = _MODE_ITEMS[value]
            self._current_nav = items[0]
            self._build_nav()
            self._show_panel(self._current_nav)

    # =========================================================================
    #  底部控制区
    # =========================================================================

    def _build_bottom(self):
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=10, pady=10)

        # 按钮行
        btn_frame = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(10, 5))

        self._start_btn = ctk.CTkButton(
            btn_frame, text="开始处理", command=self._on_start,
            width=120, fg_color="#2ecc71", hover_color="#27ae60"
        )
        self._start_btn.pack(side="left", padx=(0, 10))

        self._stop_btn = ctk.CTkButton(
            btn_frame, text="停止", command=self._on_stop,
            width=80, fg_color="#e74c3c", hover_color="#c0392b",
            state="disabled"
        )
        self._stop_btn.pack(side="left")

        # 进度条
        self._progress = ctk.CTkProgressBar(btn_frame, width=300)
        self._progress.pack(side="right", padx=(10, 0))
        self._progress.set(0)

        self._status_label = ctk.CTkLabel(btn_frame, text="就绪")
        self._status_label.pack(side="right", padx=(10, 0))

        # 日志区域
        log_label = ctk.CTkLabel(bottom, text="运行日志", anchor="w")
        log_label.pack(fill="x", padx=10, pady=(5, 0))

        self._log_text = ctk.CTkTextbox(bottom, height=120, state="disabled")
        self._log_text.pack(fill="x", padx=10, pady=(0, 10))

    # =========================================================================
    #  配置收集
    # =========================================================================

    def _collect_config(self) -> AppConfig:
        """从所有选项卡收集当前配置。"""
        self._merge_panels["封面配置"].apply_to_config(self._config)
        self._merge_panels["目录设置"].apply_to_config(self._config)
        self._merge_panels["页码设置"].apply_to_config(self._config)
        self._merge_panels["字体设置"].apply_to_config(self._config)
        self._merge_panels["路径"].apply_to_config(self._config)
        self._merge_panels["文件列表"].apply_to_config(self._config)
        self._merge_panels["PDF书签"].apply_to_config(self._config)
        self._combine_panels["文件列表"].apply_to_config(self._config)
        self._combine_panels["参数设置"].apply_to_config(self._config)
        return self._config

    # =========================================================================
    #  处理逻辑
    # =========================================================================

    def _on_start(self):
        """点击开始处理 — 根据当前模式分发。"""
        if self._current_mode == "合并":
            self._on_start_merge()
        elif self._current_mode == "拼图":
            self._on_start_combine()

    def _on_start_merge(self):
        """合并模式开始处理。"""
        config = self._collect_config()

        if not config.path.input_root:
            self._log("[X] 请设置输入目录")
            return
        if not config.path.output_root:
            self._log("[X] 请设置输出目录")
            return

        self._running = True
        self._stop_event.clear()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.set(0)
        self._status_label.configure(text="处理中...")

        thread = threading.Thread(target=self._run_merge, args=(config,), daemon=True)
        thread.start()

    def _on_start_combine(self):
        """拼图模式开始处理。"""
        config = self._collect_config()
        combine_cfg = config.combine

        if len(combine_cfg.input_files) < 2:
            self._log("[X] 至少需要 2 个输入文件")
            return
        if not combine_cfg.output_path:
            self._log("[X] 请设置输出路径")
            return

        # 从画布标签页获取用户微调后的位置
        canvas_tab = self._combine_panels.get("拼接画布")
        canvas_positions = canvas_tab._positions if canvas_tab and canvas_tab._positions else None

        self._running = True
        self._stop_event.clear()
        self._start_btn.configure(state="disabled")
        self._stop_btn.configure(state="normal")
        self._progress.set(0)
        self._status_label.configure(text="拼图处理中...")

        thread = threading.Thread(target=self._run_combine, args=(combine_cfg, canvas_positions), daemon=True)
        thread.start()

    def _run_merge(self, config: AppConfig):
        """子线程：执行合并流程。"""
        from core import process_folder, process_single_merge, get_subfolders
        from methods.fonts import register_fonts

        old_stdout = sys.stdout
        log_q = self._log_queue

        class QueueWriter:
            def write(self, text):
                if old_stdout is not None:
                    old_stdout.write(text)
                if text and text.strip():
                    log_q.put(text.strip())

            def flush(self):
                if old_stdout is not None:
                    old_stdout.flush()

        try:
            sys.stdout = QueueWriter()
            os.makedirs(config.path.output_root, exist_ok=True)
            register_fonts(config)

            if config.advanced.merge_mode == "single":
                root_name = os.path.basename(config.path.input_root) or "output"
                output_file = os.path.join(config.path.output_root, f"{root_name}.pdf")
                process_single_merge(
                    input_folder=config.path.input_root,
                    output_file=output_file,
                    config=config,
                    stop_event=self._stop_event,
                )
                log_q.put(("progress", 1.0))
            else:
                folders = get_subfolders(config.path.input_root, config)
                total = len(folders)

                if not folders:
                    log_q.put("[!] 输入目录下未找到子文件夹")
                    return

                for i, folder in enumerate(folders):
                    if self._stop_event.is_set():
                        log_q.put("[STOP] 已停止")
                        break

                    process_folder(
                        input_folder=os.path.join(config.path.input_root, folder),
                        output_file=os.path.join(config.path.output_root, f"{folder}.pdf"),
                        config=config,
                        stop_event=self._stop_event,
                    )
                    progress = (i + 1) / total
                    log_q.put(("progress", progress))

            log_q.put(f"\n[DONE] 全部完成! 输出目录: {config.path.output_root}")

        except Exception as e:
            log_q.put(f"[X] 程序执行失败: {e}")

        finally:
            sys.stdout = old_stdout
            log_q.put("done")

    def _run_combine(self, combine_cfg, canvas_positions=None):
        """子线程：执行拼图流程。"""
        from methods.combine import process_combine

        old_stdout = sys.stdout
        log_q = self._log_queue

        class QueueWriter:
            def write(self, text):
                if old_stdout is not None:
                    old_stdout.write(text)
                if text and text.strip():
                    log_q.put(text.strip())

            def flush(self):
                if old_stdout is not None:
                    old_stdout.flush()

        try:
            sys.stdout = QueueWriter()
            process_combine(combine_cfg, stop_event=self._stop_event,
                            canvas_positions=canvas_positions)
            log_q.put(("progress", 1.0))
            log_q.put(f"\n[DONE] 拼图完成! 输出: {combine_cfg.output_path}")

        except Exception as e:
            log_q.put(f"[X] 拼图执行失败: {e}")

        finally:
            sys.stdout = old_stdout
            log_q.put("done")

    # =========================================================================
    #  停止 / 日志 / 关闭
    # =========================================================================

    def _on_stop(self):
        self._stop_event.set()
        self._log("[STOP] 正在停止...")

    def _log(self, message: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _poll_log_queue(self):
        while True:
            try:
                msg = self._log_queue.get_nowait()
            except queue.Empty:
                break

            if msg == "done":
                self._running = False
                self._start_btn.configure(state="normal")
                self._stop_btn.configure(state="disabled")
                self._status_label.configure(text="就绪")
            elif isinstance(msg, tuple) and msg[0] == "progress":
                self._progress.set(msg[1])
            else:
                self._log(msg)

        self.after(100, self._poll_log_queue)

    def _on_close(self):
        self._collect_config()
        try:
            self._config.save()
        except Exception:
            pass
        self.destroy()

    def refresh_fonts(self):
        self._merge_panels["封面配置"].refresh_font_options()
        self._merge_panels["目录设置"].refresh_font_options()
        self._merge_panels["页码设置"].refresh_font_options()
        self._merge_panels["PDF书签"].refresh_font_options()

    def log(self, message: str):
        self._log(message)
