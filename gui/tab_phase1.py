import customtkinter as ctk
from tkinter import ttk
import threading
import time
import os

from core_engine.step01_scanner import execute_scan
from core_engine.step02_ai_anchor import execute_ai_anchor

class TabPhase1:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        app = self.app
        parent = self.parent

        self.label_a = ctk.CTkLabel(parent, text="1. 从左侧选择源文件夹，添加至右侧列表，并输入作者", font=app.font_title)
        self.label_a.pack(pady=(10, 5))

        self.frame_settings_a = app.build_settings_frame(parent, "API_A")
        self.frame_settings_a.pack(fill="x", padx=20, pady=(0, 5))

        self.entry_author = ctk.CTkEntry(parent, placeholder_text="请输入作者 (如: 张三)", width=350, font=app.font_body)
        self.entry_author.pack(pady=5)

        self.content_frame_a = ctk.CTkFrame(parent, fg_color="transparent")
        self.content_frame_a.pack(fill="both", expand=True, padx=20, pady=5)
        self.content_frame_a.grid_columnconfigure(0, weight=1)
        self.content_frame_a.grid_columnconfigure(1, weight=0)
        self.content_frame_a.grid_columnconfigure(2, weight=1)
        self.content_frame_a.grid_rowconfigure(0, weight=1)

        self.frame_explorer = ctk.CTkFrame(self.content_frame_a)
        self.frame_explorer.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self.frame_explorer.grid_rowconfigure(0, weight=1)
        self.frame_explorer.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.frame_explorer, show='tree', selectmode='extended')
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree_scrollbar = ctk.CTkScrollbar(self.frame_explorer, command=self.tree.yview)
        self.tree_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree.bind("<<TreeviewOpen>>", app.on_tree_open)
        app.populate_drives(self.tree)

        self.frame_actions = ctk.CTkFrame(self.content_frame_a, fg_color="transparent")
        self.frame_actions.grid(row=0, column=1, padx=5, sticky="ns")
        self.btn_add_from_tree = ctk.CTkButton(self.frame_actions, text="➡️\n添\n加", width=40, font=app.font_body, command=self.add_folder_from_tree)
        self.btn_add_from_tree.pack(expand=True)

        self.frame_selection = ctk.CTkFrame(self.content_frame_a)
        self.frame_selection.grid(row=0, column=2, padx=(5, 0), sticky="nsew")
        self.frame_selection.grid_rowconfigure(1, weight=1)
        self.frame_selection.grid_columnconfigure(0, weight=1)
        self.label_selection = ctk.CTkLabel(self.frame_selection, text="待处理文件夹列表:", font=app.font_body_bold)
        self.label_selection.pack(fill="x", padx=10, pady=(10, 5))
        self.textbox_folders = ctk.CTkTextbox(self.frame_selection, font=app.font_body)
        self.textbox_folders.pack(fill="both", expand=True, padx=10, pady=5)
        self.update_folder_textbox()
        
        self.btn_clear_folders = ctk.CTkButton(self.frame_selection, text="🗑️ 清空列表", fg_color="darkred", hover_color="red", font=app.font_body, command=self.clear_source_folders)
        self.btn_clear_folders.pack(fill="x", padx=10, pady=(5, 10))
        
        self.btn_run_a = ctk.CTkButton(parent, text="🚀 启动解析 (执行 Step 01 & 02) -> 生成锚定表.json", font=app.font_btn_main, command=self.start_phase_a_thread)
        self.btn_run_a.pack(pady=10)
        
        self.log_textbox_a = ctk.CTkTextbox(parent, height=200, font=app.font_body)
        self.log_textbox_a.pack(pady=(0, 10), padx=20, fill="both", expand=True)

    def add_folder_from_tree(self):
        selected_items = self.tree.selection()
        if not selected_items: return
        added_count = 0
        for item_id in selected_items:
            folder_path = self.app.get_path_from_item(self.tree, item_id)
            if folder_path and folder_path.replace("\\", "/") not in self.app.source_folders_a:
                self.app.source_folders_a.append(folder_path.replace("\\", "/"))
                added_count += 1
        if added_count > 0:
            self.update_folder_textbox()
            self.app.log_message("A", f"✅ [系统] 成功批量添加 {added_count} 个源文件夹！")

    def clear_source_folders(self):
        self.app.source_folders_a.clear()
        self.update_folder_textbox()

    def update_folder_textbox(self):
        self.textbox_folders.configure(state="normal")
        self.textbox_folders.delete("1.0", "end")
        if not self.app.source_folders_a:
            self.textbox_folders.insert("end", "暂未选择任何文件夹...\n")
        else:
            for idx, folder in enumerate(self.app.source_folders_a, 1):
                self.textbox_folders.insert("end", f"{idx}. {folder}\n")
        self.textbox_folders.configure(state="disabled")

    def start_phase_a_thread(self):
        author = self.entry_author.get().strip()
        if not self.app.source_folders_a:
            self.app.log_message("A", "⚠️ [警告] 请至少添加一个源文件夹！")
            return
        if not author:
            self.app.log_message("A", "⚠️ [警告] 请输入作者！")
            return
            
        self.btn_run_a.configure(state="disabled")
        self.app.log_message("A", "-"*50)
        self.app.log_message("A", f"🚀 [系统] 启动多源解析，作者: {author}")
        threading.Thread(target=self._worker_phase_a, daemon=True).start()

    def _worker_phase_a(self):
        author = self.entry_author.get().strip()
        # 核心：直接从界面输入框实时提取配置，防止用户忘记点击保存
        api_config = self.app.get_api_config("API_A")
        log_cb = lambda msg: self.app.log_message("A", msg)
        
        success_count = 0
        for folder in self.app.source_folders_a:
            log_cb(f"\n▶️ 开始处理源文件夹: {folder}")
            
            # 执行 Step 01
            success, skeleton_json = execute_scan(folder, log_cb)
            if not success or not skeleton_json: continue
                
            # 执行 Step 02
            project_name = os.path.basename(os.path.normpath(folder))
            parent_dir = os.path.dirname(os.path.normpath(folder))
            output_anchor_json = os.path.join(parent_dir, f"{project_name}_锚定表.json")
            if execute_ai_anchor(skeleton_json, output_anchor_json, author, api_config, log_cb):
                success_count += 1
                
        self.app.log_message("A", f"\n🎉 [成功] 阶段 1 执行完毕！共完成 {success_count} 个项目，生成的 JSON 请人工复核！")
        self.btn_run_a.configure(state="normal")