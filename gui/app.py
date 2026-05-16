# =============================================================================
#  app.py — 主窗口框架
#  customtkinter 主窗口，选项卡容器，底部运行控制区，日志面板
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


class PdfToolKitApp(ctk.CTk):
    """PDF 批量合并工具主窗口。"""

    def __init__(self):
        super().__init__()

        self._config = AppConfig.load()
        self._stop_event = threading.Event()
        self._log_queue = queue.Queue()
        self._running = False

        # 窗口设置
        from main import __version__
        self.title(f"PDF 批量合并工具 v{__version__}")
        self.geometry("1100x750")
        self.minsize(900, 600)

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

    def _build_ui(self):
        # ── 选项卡区域 ──
        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # 创建各选项卡（路径放最前）
        self._path_tab = PathTab(
            self._tabview.add("路径"), self._config, app=self
        )
        self._cover_tab = CoverTab(
            self._tabview.add("封面配置"), self._config, app=self
        )
        self._toc_tab = TocTab(
            self._tabview.add("目录设置"), self._config
        )
        self._pagenum_tab = PageNumTab(
            self._tabview.add("页码设置"), self._config
        )
        self._font_tab = FontTab(
            self._tabview.add("字体设置"), self._config
        )
        self._file_list_tab = FileListTab(
            self._tabview.add("文件列表"), self._config, app=self
        )
        self._bookmark_tab = BookmarkTab(
            self._tabview.add("PDF书签"), self._config
        )

        # ── 底部控制区 ──
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

    def _collect_config(self) -> AppConfig:
        """从所有选项卡收集当前配置。"""
        self._cover_tab.apply_to_config(self._config)
        self._toc_tab.apply_to_config(self._config)
        self._pagenum_tab.apply_to_config(self._config)
        self._font_tab.apply_to_config(self._config)
        self._path_tab.apply_to_config(self._config)
        self._file_list_tab.apply_to_config(self._config)
        self._bookmark_tab.apply_to_config(self._config)
        return self._config

    def _on_start(self):
        """点击开始处理。"""
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

        # 在子线程中执行
        thread = threading.Thread(target=self._run_process, args=(config,), daemon=True)
        thread.start()

    def _run_process(self, config: AppConfig):
        """子线程：执行 PDF 处理流程。"""
        from core import process_folder, process_single_merge, get_subfolders, register_fonts

        # 重定向 stdout 到队列
        old_stdout = sys.stdout
        log_q = self._log_queue

        class QueueWriter:
            def write(self, text):
                old_stdout.write(text)
                if text and text.strip():
                    log_q.put(text.strip())

            def flush(self):
                old_stdout.flush()

        try:
            sys.stdout = QueueWriter()
            os.makedirs(config.path.output_root, exist_ok=True)
            register_fonts(config)

            if config.advanced.merge_mode == "single":
                # 整体合并模式
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
                # 按子文件夹分别合并（默认行为）
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

    def _on_stop(self):
        """点击停止。"""
        self._stop_event.set()
        self._log("[STOP] 正在停止...")

    def _log(self, message: str):
        """向日志区域追加消息（主线程调用）。"""
        self._log_text.configure(state="normal")
        self._log_text.insert("end", message + "\n")
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _poll_log_queue(self):
        """定期从队列中取出日志消息并更新 UI。"""
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
        """窗口关闭时保存配置。"""
        self._collect_config()
        try:
            self._config.save()
        except Exception:
            pass
        self.destroy()

    def refresh_fonts(self):
        """通知所有选项卡刷新字体下拉框选项。"""
        self._cover_tab.refresh_font_options()
        self._toc_tab.refresh_font_options()
        self._pagenum_tab.refresh_font_options()
        self._bookmark_tab.refresh_font_options()

    def log(self, message: str):
        """外部调用日志接口。"""
        self._log(message)
