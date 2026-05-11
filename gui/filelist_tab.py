# =============================================================================
#  filelist_tab.py — 文件列表选项卡
#  树形文件浏览 + 拖拽排序
# =============================================================================

import os
import threading
import tkinter.ttk as ttk

import customtkinter as ctk

from config import AppConfig


class FileListTab:
    """文件列表选项卡：树形文件浏览 + 拖拽排序。"""

    def __init__(self, parent, config: AppConfig, app=None):
        self._config = config
        self._adv = config.advanced
        self._app = app
        self._press_item = None

        self._frame = ctk.CTkFrame(parent)
        self._frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._build()

    def _build(self):
        # 标题行
        tree_header = ctk.CTkFrame(self._frame, fg_color="transparent")
        tree_header.pack(fill="x", padx=5, pady=(5, 0))
        ctk.CTkLabel(tree_header, text="文件列表",
                     font=ctk.CTkFont(weight="bold", size=15)).pack(side="left")
        ctk.CTkButton(tree_header, text="刷新列表", width=90,
                      command=self.refresh_file_list).pack(side="right", padx=5)
        ctk.CTkLabel(tree_header, text="（拖拽可调整同级文件顺序）",
                     text_color="gray").pack(side="right", padx=5)

        # Treeview 样式 — 根据 DPI 缩放
        style = ttk.Style()
        dpi = self._frame.winfo_toplevel().winfo_fpixels('1i')
        scale = max(dpi / 96.0, 1.0)
        base_font_size = 14
        base_rowheight = 28
        scaled_size = max(int(base_font_size * scale), base_font_size)
        scaled_rowheight = max(int(base_rowheight * scale), base_rowheight)
        style.configure("FileTree.Treeview", rowheight=scaled_rowheight,
                        font=("Microsoft YaHei UI", scaled_size))
        style.configure("FileTree.Treeview.Heading",
                        font=("Microsoft YaHei UI", scaled_size, "bold"))

        tree_container = ctk.CTkFrame(self._frame)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)

        self._tree = ttk.Treeview(
            tree_container,
            columns=("check", "type"),
            show="tree headings",
            selectmode="browse",
            style="FileTree.Treeview",
        )
        self._tree.heading("#0", text="名称", anchor="w")
        self._tree.heading("check", text="", anchor="center")
        self._tree.heading("type", text="类型", anchor="w")
        self._tree.column("#0", width=420, minwidth=250)
        self._tree.column("check", width=40, minwidth=40, anchor="center", stretch=False)
        self._tree.column("type", width=80, minwidth=60)

        scrollbar = ttk.Scrollbar(tree_container, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 统一事件处理：按下→拖拽→释放
        self._tree.bind("<ButtonPress-1>", self._on_tree_press)
        self._tree.bind("<B1-Motion>", self._on_tree_motion)
        self._tree.bind("<ButtonRelease-1>", self._on_tree_release)

        self._tree_items = {}
        self._checked = set()  # 选中的 iid 集合

    # ── 刷新 ──

    def refresh_file_list(self):
        input_root = self._config.path.input_root
        if not input_root or not os.path.isdir(input_root):
            return

        def _scan():
            try:
                from core import collect_file_tree
                items, _ = collect_file_tree(input_root, self._config)
                if self._app:
                    self._app.after(0, lambda: self._populate_tree(items))
            except Exception as e:
                if self._app:
                    self._app.after(0, lambda: self._app.log(
                        f"[!] 扫描文件列表失败：{e}"))

        threading.Thread(target=_scan, daemon=True).start()

    def _populate_tree(self, items):
        self._tree.delete(*self._tree.get_children())
        self._tree_items = {}
        self._checked = set()
        parent_map = {}

        for item in items:
            name = item.get("name", "")
            path = item.get("path", "")
            level = item.get("level", 0)
            parent_path = os.path.dirname(path)
            parent_iid = parent_map.get(parent_path, "")

            if item["type"] == "folder":
                iid = self._tree.insert(
                    parent_iid, "end",
                    text=f"📁 {name}",
                    values=("☑", "文件夹"),
                    open=False,
                    tags=("folder",)
                )
                parent_map[path] = iid
                self._checked.add(iid)
            else:
                is_image = item.get("is_image", False)
                type_label = "图片" if is_image else "PDF"
                icon = "🖼" if is_image else "📄"
                tags = ("file", "image") if is_image else ("file",)
                iid = self._tree.insert(
                    parent_iid, "end",
                    text=f"{icon} {name}",
                    values=("☑", type_label),
                    tags=tags,
                )
                self._checked.add(iid)
            self._tree_items[iid] = item

        for child in self._tree.get_children():
            self._tree.item(child, open=True)

    # ── 复选框切换 ──

    def _toggle_check(self, iid):
        """切换某项的复选框状态。"""
        if iid in self._checked:
            self._checked.discard(iid)
            self._tree.set(iid, "check", "☐")
        else:
            self._checked.add(iid)
            self._tree.set(iid, "check", "☑")

    # ── 统一鼠标事件：复选框点击 + 拖拽排序 ──

    def _on_tree_press(self, event):
        """鼠标按下：记录起始项和位置。"""
        item = self._tree.identify_row(event.y)
        self._press_item = item
        self._press_x = event.x
        self._press_y = event.y
        self._drag_started = False

    def _on_tree_motion(self, event):
        """鼠标移动：如果移动距离超过阈值，进入拖拽模式。"""
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
        """鼠标释放：判断是点击（复选框）还是拖拽（排序）。"""
        item = self._press_item
        self._press_item = None
        self._tree.selection_remove(*self._tree.selection())

        if not item:
            return

        if self._drag_started:
            # 拖拽结束 → 执行排序
            target = self._tree.identify_row(event.y)
            if not target or target == item:
                return
            drag_parent = self._tree.parent(item)
            target_parent = self._tree.parent(target)
            if drag_parent != target_parent:
                if self._app:
                    self._app.log("[i] 仅允许同级文件拖拽排序")
                return
            target_index = self._tree.index(target)
            self._tree.move(item, drag_parent, target_index)
            self._update_file_order()
        else:
            # 点击 → 检查是否点击了复选框列
            region = self._tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            column = self._tree.identify_column(event.x)
            if column != "#1":
                return
            clicked = self._tree.identify_row(event.y)
            if clicked:
                self._toggle_check(clicked)

    def _update_file_order(self):
        file_order = {}

        def _collect(parent_iid, parent_path):
            children = self._tree.get_children(parent_iid)
            names = []
            for cid in children:
                item = self._tree_items.get(cid, {})
                raw = item.get("raw_name", item.get("name", ""))
                p = item.get("path", "")
                if item.get("type") == "folder":
                    names.append(os.path.basename(p))
                    _collect(cid, p)
                else:
                    names.append(raw)
            if names:
                file_order[parent_path] = names

        root_path = self._config.path.input_root
        _collect("", root_path)
        self._adv.file_order = file_order

    def apply_to_config(self, config: AppConfig):
        # 收集未选中的文件路径
        excluded = []
        for iid, item in self._tree_items.items():
            if iid not in self._checked:
                excluded.append(item.get("path", ""))
        config.advanced.excluded_files = excluded
