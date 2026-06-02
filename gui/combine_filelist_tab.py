# =============================================================================
#  combine_filelist_tab.py — 拼图模式文件列表面板
#  添加/排序/排除 PDF 文件
# =============================================================================

import os
import tkinter.ttk as ttk

import customtkinter as ctk
from tkinter import filedialog

from config import AppConfig


class CombineFileListTab:
    """拼图模式 — 文件列表：添加/排序/排除 PDF 文件。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._combine = config.combine
        self._app = app
        self._press_item = None

        self._frame = ctk.CTkFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._tree_items = {}
        self._checked = set()

        self._build()

    def _build(self):
        # ── 按钮行 ──
        btn_frame = ctk.CTkFrame(self._frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=5, pady=(5, 0))

        ctk.CTkButton(btn_frame, text="添加文件", width=90,
                      command=self._add_files).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="移除选中", width=90,
                      fg_color="#e67e22", hover_color="#d35400",
                      command=self._remove_selected).pack(side="left", padx=(0, 5))
        ctk.CTkButton(btn_frame, text="清空", width=70,
                      fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._clear_all).pack(side="left")

        ctk.CTkLabel(btn_frame, text="（拖拽可调整顺序）",
                     text_color="gray").pack(side="right", padx=5)

        # ── Treeview ──
        style = ttk.Style()
        dpi = self._frame.winfo_toplevel().winfo_fpixels('1i')
        scale = max(dpi / 96.0, 1.0)
        base_size = 14
        scaled_size = max(int(base_size * scale), base_size)
        scaled_rowheight = max(int(28 * scale), 28)
        style.configure("CombineTree.Treeview", rowheight=scaled_rowheight,
                        font=("Microsoft YaHei UI", scaled_size))
        style.configure("CombineTree.Treeview.Heading",
                        font=("Microsoft YaHei UI", scaled_size, "bold"))

        tree_container = ctk.CTkFrame(self._frame)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)

        self._tree = ttk.Treeview(
            tree_container,
            columns=("check", "pages", "size"),
            show="tree headings",
            selectmode="browse",
            style="CombineTree.Treeview",
        )
        self._tree.heading("#0", text="文件名", anchor="w")
        self._tree.heading("check", text="", anchor="center")
        self._tree.heading("pages", text="页数", anchor="center")
        self._tree.heading("size", text="大小", anchor="e")
        self._tree.column("#0", width=300, minwidth=200)
        self._tree.column("check", width=40, minwidth=40, anchor="center", stretch=False)
        self._tree.column("pages", width=60, minwidth=50, anchor="center")
        self._tree.column("size", width=80, minwidth=60, anchor="e")

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 拖拽事件
        self._tree.bind("<ButtonPress-1>", self._on_tree_press)
        self._tree.bind("<B1-Motion>", self._on_tree_motion)
        self._tree.bind("<ButtonRelease-1>", self._on_tree_release)

    # ── 文件操作 ──

    def _add_files(self):
        """添加 PDF 文件。"""
        initial = self._combine.input_files[0] if self._combine.input_files else os.path.expanduser("~")
        if os.path.isfile(initial):
            initial = os.path.dirname(initial)
        paths = filedialog.askopenfilenames(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
            initialdir=initial,
        )
        if not paths:
            return
        for path in paths:
            if path not in self._combine.input_files:
                self._combine.input_files.append(path)
                if self._app:
                    self._app.log(f"[i] 添加：{os.path.basename(path)}")
        self._refresh_tree()

    def _remove_selected(self):
        """移除未勾选（已取消选中）的文件。"""
        to_remove = [iid for iid in self._tree_items if iid not in self._checked]
        if not to_remove:
            if self._app:
                self._app.log("[i] 请取消勾选要移除的文件")
            return
        for iid in to_remove:
            item = self._tree_items.get(iid, {})
            path = item.get("path", "")
            if path in self._combine.input_files:
                self._combine.input_files.remove(path)
        self._refresh_tree()

    def _clear_all(self):
        """清空所有文件。"""
        self._combine.input_files.clear()
        self._refresh_tree()

    def _refresh_tree(self):
        """根据 config.input_files 刷新树形列表。"""
        self._tree.delete(*self._tree.get_children())
        self._tree_items = {}
        self._checked = set()

        from pikepdf import Pdf as _Pdf

        for path in self._combine.input_files:
            name = os.path.basename(path)
            try:
                with _Pdf.open(path) as f:
                    pages = len(f.pages)
            except Exception:
                pages = "?"
            try:
                size_kb = os.path.getsize(path) / 1024
                if size_kb > 1024:
                    size_str = f"{size_kb / 1024:.1f} MB"
                else:
                    size_str = f"{size_kb:.0f} KB"
            except Exception:
                size_str = "?"

            iid = self._tree.insert(
                "", "end",
                text=f"📄 {name}",
                values=("☑", pages, size_str),
            )
            self._tree_items[iid] = {"path": path, "name": name}
            self._checked.add(iid)

    # ── 复选框切换 ──

    def _toggle_check(self, iid):
        if iid in self._checked:
            self._checked.discard(iid)
            self._tree.set(iid, "check", "☐")
        else:
            self._checked.add(iid)
            self._tree.set(iid, "check", "☑")

    # ── 拖拽排序 ──

    def _on_tree_press(self, event):
        item = self._tree.identify_row(event.y)
        self._press_item = item
        self._press_x = event.x
        self._press_y = event.y
        self._drag_started = False

    def _on_tree_motion(self, event):
        if not self._press_item:
            return
        dx = event.x - self._press_x
        dy = event.y - self._press_y
        if not self._drag_started and (abs(dx) > 5 or abs(dy) > 5):
            self._drag_started = True
        if self._drag_started:
            target = self._tree.identify_row(event.y)
            self._tree.selection_remove(*self._tree.selection())
            if target and target != self._press_item:
                self._tree.selection_set(target)

    def _on_tree_release(self, event):
        item = self._press_item
        self._press_item = None
        self._tree.selection_remove(*self._tree.selection())

        if not item:
            return

        if self._drag_started:
            target = self._tree.identify_row(event.y)
            if not target or target == item:
                return
            target_index = self._tree.index(target)
            self._tree.move(item, "", target_index)
            self._sync_order_to_config()
        else:
            region = self._tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            column = self._tree.identify_column(event.x)
            if column != "#1":
                return
            clicked = self._tree.identify_row(event.y)
            if clicked:
                self._toggle_check(clicked)

    def _sync_order_to_config(self):
        """将树形列表的顺序同步到 config.input_files。"""
        ordered = []
        for iid in self._tree.get_children():
            item = self._tree_items.get(iid, {})
            path = item.get("path", "")
            if path:
                ordered.append(path)
        self._combine.input_files = ordered

    # ── 配置 ──

    def apply_to_config(self, config: AppConfig):
        """排除未勾选的文件后写回。"""
        excluded = [item.get("path", "") for iid, item in self._tree_items.items()
                    if iid not in self._checked]
        config.combine.input_files = [
            p for p in self._combine.input_files if p not in excluded
        ]
        config.combine.output_path = self._combine.output_path
