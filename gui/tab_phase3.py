import customtkinter as ctk
from tkinter import ttk
import os
import threading

from core_engine.step04_salvage_ai import execute_salvage_ai
from core_engine.step05_salvage_move import execute_physical_move

class TabPhase3:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        app = self.app
        parent = self.parent

        self.label_c = ctk.CTkLabel(parent, text="3. 对新文件夹中的“06其他”执行 AI 识别整理与最终物理归位", font=app.font_title)
        self.label_c.pack(pady=10)
        
        self.frame_settings_c = app.build_settings_frame(parent, "API_B")
        self.frame_settings_c.pack(fill="x", padx=20, pady=(0, 10))
        
        self.content_frame_c = ctk.CTkFrame(parent, fg_color="transparent")
        self.content_frame_c.pack(fill="both", expand=True, padx=20, pady=5)
        self.content_frame_c.grid_columnconfigure(0, weight=1)
        self.content_frame_c.grid_columnconfigure(1, weight=0)
        self.content_frame_c.grid_columnconfigure(2, weight=1)
        self.content_frame_c.grid_rowconfigure(0, weight=1)

        self.frame_explorer_c = ctk.CTkFrame(self.content_frame_c)
        self.frame_explorer_c.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self.frame_explorer_c.grid_rowconfigure(0, weight=1)
        self.frame_explorer_c.grid_columnconfigure(0, weight=1)

        self.tree_c = ttk.Treeview(self.frame_explorer_c, show='tree', selectmode='extended')
        self.tree_c.grid(row=0, column=0, sticky="nsew")
        self.tree_scrollbar_c = ctk.CTkScrollbar(self.frame_explorer_c, command=self.tree_c.yview)
        self.tree_scrollbar_c.grid(row=0, column=1, sticky="ns")
        self.tree_c.configure(yscrollcommand=self.tree_scrollbar_c.set)
        self.tree_c.bind("<<TreeviewOpen>>", app.on_tree_open)
        app.populate_drives(self.tree_c)

        self.frame_actions_c = ctk.CTkFrame(self.content_frame_c, fg_color="transparent")
        self.frame_actions_c.grid(row=0, column=1, padx=5, sticky="ns")
        self.btn_add_from_tree_c = ctk.CTkButton(self.frame_actions_c, text="➡️\n添\n加", width=40, font=app.font_body, command=self.add_folder_from_tree_c)
        self.btn_add_from_tree_c.pack(expand=True)

        self.frame_selection_c = ctk.CTkFrame(self.content_frame_c)
        self.frame_selection_c.grid(row=0, column=2, padx=(5, 0), sticky="nsew")
        self.frame_selection_c.grid_rowconfigure(1, weight=1)
        self.frame_selection_c.grid_columnconfigure(0, weight=1)
        
        self.frame_sub_actions_c = ctk.CTkFrame(self.frame_selection_c, fg_color="transparent")
        self.frame_sub_actions_c.pack(fill="x", padx=10, pady=(10, 5))
        self.btn_import_from_b = ctk.CTkButton(self.frame_sub_actions_c, text="⬇️ 从阶段2导入", fg_color="#2b7b46", hover_color="#1e5c33", font=app.font_body, command=self.import_from_phase_b)
        self.btn_import_from_b.pack(side="left", expand=True, padx=(0, 5))
        self.btn_clear_c = ctk.CTkButton(self.frame_sub_actions_c, text="🗑️ 清空", fg_color="darkred", hover_color="red", font=app.font_body, command=self.clear_salvage_folders_c)
        self.btn_clear_c.pack(side="right", expand=True, padx=(5, 0))
        
        self.textbox_c = ctk.CTkTextbox(self.frame_selection_c, font=app.font_body)
        self.textbox_c.pack(fill="both", expand=True, padx=10, pady=5)
        self.update_salvage_textbox_c()
        
        self.btn_run_c = ctk.CTkButton(parent, text="🧹 零散文件识别和整理 (执行 Step 04 & 05)", font=app.font_btn_main, command=self.start_phase_c_thread)
        self.btn_run_c.pack(pady=10)
        
        self.log_textbox_c = ctk.CTkTextbox(parent, height=120, font=app.font_body)
        self.log_textbox_c.pack(pady=(0, 10), padx=20, fill="both", expand=True)

    def add_folder_from_tree_c(self):
        selected_items = self.tree_c.selection()
        if not selected_items: return
        added_count = 0
        for item_id in selected_items:
            folder_path = self.app.get_path_from_item(self.tree_c, item_id)
            if folder_path and folder_path.replace("\\", "/") not in self.app.salvage_folders_c:
                self.app.salvage_folders_c.append(folder_path.replace("\\", "/"))
                added_count += 1
        if added_count > 0:
            self.update_salvage_textbox_c()
            self.app.log_message("C", f"✅ [系统] 成功手动添加 {added_count} 个待整理项目！")

    def import_from_phase_b(self):
        added = 0
        for task in self.app.merge_tasks_b:
            target_path = task["target_var"].get().strip()
            if target_path and target_path not in self.app.salvage_folders_c:
                self.app.salvage_folders_c.append(target_path)
                added += 1
        if added > 0:
            self.update_salvage_textbox_c()
            self.app.log_message("C", f"✅ [系统] 成功从阶段 2 导入 {added} 个项目路径！")
        else:
            self.app.log_message("C", "⚠️ [提示] 阶段 2 中没有新的有效目标路径可导入。")

    def clear_salvage_folders_c(self):
        self.app.salvage_folders_c.clear()
        self.update_salvage_textbox_c()

    def update_salvage_textbox_c(self):
        self.textbox_c.configure(state="normal")
        self.textbox_c.delete("1.0", "end")
        if not self.app.salvage_folders_c:
            self.textbox_c.insert("end", "暂未添加任何待整理的项目路径...\n")
        else:
            for idx, folder in enumerate(self.app.salvage_folders_c, 1):
                self.textbox_c.insert("end", f"{idx}. {folder}\n")
        self.textbox_c.configure(state="disabled")

    def start_phase_c_thread(self):
        if not self.app.salvage_folders_c:
            self.app.log_message("C", "⚠️ [警告] 请至少添加一个待识别的新文件夹项目路径！")
            return
        self.btn_run_c.configure(state="disabled")
        self.app.log_message("C", "-"*50)
        self.app.log_message("C", f"🧹 [系统] 正在启动后台引擎进行 AI 零散文件识别和整理 (Step 04 & 05)...")
        threading.Thread(target=self._worker_phase_c, daemon=True).start()

    def _worker_phase_c(self):
        # 核心：直接从界面输入框实时提取配置，防止用户忘记点击保存
        api_config = self.app.get_api_config("API_B")
        log_cb = lambda msg: self.app.log_message("C", msg)
        success_count = 0
        
        for target_root_dir in self.app.salvage_folders_c:
            log_cb(f"\n▶️ 开始整理打捞: {target_root_dir}")
            
            # 执行 Step 04 (扫描鉴定)
            success, salvage_json = execute_salvage_ai(target_root_dir, api_config, log_cb)
            
            # 执行 Step 05 (物理移动)
            if success and (not salvage_json or execute_physical_move(salvage_json, target_root_dir, log_cb)):
                success_count += 1
                
        self.app.log_message("C", f"\n🎉 [成功] 阶段 3 执行完毕！共完成 {success_count} 个项目的零散文件整理。")
        self.btn_run_c.configure(state="normal")