import customtkinter as ctk
from customtkinter import filedialog
import os
import threading

from core_engine.step03_physical_copy import execute_physical_copy

class TabPhase2:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.setup_ui()

    def setup_ui(self):
        app = self.app
        parent = self.parent

        self.label_b = ctk.CTkLabel(parent, text="2. 添加复核后的 JSON 及对应源文件夹，集中复制至新文件夹", font=app.font_title)
        self.label_b.pack(pady=10)
        
        self.frame_target_b = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_target_b.pack(pady=(0, 5), fill="x", padx=20)
        
        self.btn_target_b = ctk.CTkButton(self.frame_target_b, text="设定全局新文件夹根目录", font=app.font_body, command=self.select_default_target_nas_b)
        self.btn_target_b.pack(side="left", padx=10)
        
        self.entry_target_b = ctk.CTkEntry(self.frame_target_b, placeholder_text="先选根目录，下方批量添加时会自动拼接项目名...", font=app.font_body)
        self.entry_target_b.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.frame_pairs = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_pairs.pack(pady=5, fill="x", padx=20)
        
        self.btn_add_pair = ctk.CTkButton(self.frame_pairs, text="➕ 批量选择 JSON (自动匹配源文件夹)", font=app.font_body, command=self.add_merge_pair)
        self.btn_add_pair.pack(side="left", padx=10)
        
        self.btn_import_from_a = ctk.CTkButton(self.frame_pairs, text="⬇️ 从阶段1导入", fg_color="#2b7b46", hover_color="#1e5c33", font=app.font_body, command=self.import_from_phase_a)
        self.btn_import_from_a.pack(side="left", padx=10)
        
        self.btn_clear_pairs = ctk.CTkButton(self.frame_pairs, text="🗑️ 清空列表", fg_color="darkred", hover_color="red", font=app.font_body, command=self.clear_merge_pairs)
        self.btn_clear_pairs.pack(side="right", padx=10)
        
        self.scroll_pairs = ctk.CTkScrollableFrame(parent, height=150)
        self.scroll_pairs.pack(pady=5, fill="both", expand=True, padx=20)
        
        self.btn_run_b = ctk.CTkButton(parent, text="🚀 执行复制 (执行 Step 03)", font=app.font_btn_main, command=self.start_phase_b_thread)
        self.btn_run_b.pack(pady=10)
        
        self.log_textbox_b = ctk.CTkTextbox(parent, height=150, font=app.font_body)
        self.log_textbox_b.pack(pady=(0, 10), padx=20, fill="both", expand=True)

    def add_merge_pair(self):
        json_paths = filedialog.askopenfilenames(title="请批量选择复核后的 JSON 文件", filetypes=[("JSON Files", "*锚定表.json"), ("All JSON", "*.json")])
        if not json_paths: return
        
        default_root = self.entry_target_b.get().strip()
        added_count = 0
        
        for json_path in json_paths:
            json_path = json_path.replace("\\", "/")
            dir_name = os.path.dirname(json_path)
            base_name = os.path.basename(json_path)
            
            project_name = base_name.split('_锚定表')[0] if '_锚定表' in base_name else base_name.split('.')[0]
            expected_folder = os.path.join(dir_name, project_name).replace("\\", "/")
            
            if os.path.isdir(expected_folder):
                if any(task["json"] == json_path for task in self.app.merge_tasks_b): continue
                target_path = os.path.join(default_root, project_name).replace("\\", "/") if default_root else ""
                self.add_task_ui_row(project_name, json_path, expected_folder, target_path)
                added_count += 1
            else:
                self.app.log_message("B", f"⚠️ [警告] 匹配失败: 找不到 {base_name} 对应的源文件夹，期待路径为 {expected_folder}")
                
        if added_count > 0: self.app.log_message("B", f"✅ [系统] 智能匹配成功，已添加 {added_count} 个复制任务！")

    def import_from_phase_a(self):
        if not self.app.source_folders_a:
            self.app.log_message("B", "⚠️ [提示] 阶段 1 暂无源文件夹可导入。")
            return
        default_root = self.entry_target_b.get().strip()
        added_count = 0
        for source_path in self.app.source_folders_a:
            source_path = source_path.replace("\\", "/")
            parent_dir = os.path.dirname(source_path)
            project_name = os.path.basename(source_path)
            expected_json = f"{parent_dir}/{project_name}_锚定表.json"
            
            if os.path.isfile(expected_json):
                if any(task["json"] == expected_json for task in self.app.merge_tasks_b): continue
                target_path = os.path.join(default_root, project_name).replace("\\", "/") if default_root else ""
                self.add_task_ui_row(project_name, expected_json, source_path, target_path)
                added_count += 1
            else:
                self.app.log_message("B", f"⚠️ [警告] 导入跳过: 找不到 {project_name} 对应的锚定表 (尚未生成或已删除)")
        if added_count > 0: self.app.log_message("B", f"✅ [系统] 成功从阶段 1 导入 {added_count} 个复制任务！")
        else: self.app.log_message("B", "⚠️ [提示] 没有新增任何有效任务。")

    def add_task_ui_row(self, project_name, json_path, source_path, target_path):
        row_frame = ctk.CTkFrame(self.scroll_pairs)
        row_frame.pack(fill="x", pady=2, padx=2)
        info_label = ctk.CTkLabel(row_frame, text=f"📁 项目: {project_name} | 源: {source_path}", font=self.app.font_body_bold)
        info_label.pack(anchor="w", padx=10, pady=(5, 0))
        target_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
        target_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(target_frame, text="独立目标路径:", font=self.app.font_body).pack(side="left")
        target_var = ctk.StringVar(value=target_path)
        target_entry = ctk.CTkEntry(target_frame, textvariable=target_var, font=self.app.font_body)
        target_entry.pack(side="left", fill="x", expand=True, padx=5)
        btn_browse = ctk.CTkButton(target_frame, text="修改", width=50, font=self.app.font_body, command=lambda v=target_var: self.browse_specific_target(v))
        btn_browse.pack(side="left", padx=2)
        btn_del = ctk.CTkButton(target_frame, text="✖", width=30, fg_color="darkred", hover_color="red", font=self.app.font_body,
                                command=lambda f=row_frame, j=json_path: self.remove_task_row(f, j))
        btn_del.pack(side="left", padx=2)
        self.app.merge_tasks_b.append({"json": json_path, "source": source_path, "target_var": target_var, "ui": row_frame})

    def browse_specific_target(self, target_var):
        folder = filedialog.askdirectory(title="选择此项目的独立目标路径")
        if folder: target_var.set(folder.replace("\\", "/"))

    def remove_task_row(self, frame, json_path):
        frame.destroy()
        self.app.merge_tasks_b = [t for t in self.app.merge_tasks_b if t["json"] != json_path]

    def clear_merge_pairs(self):
        for task in self.app.merge_tasks_b: task["ui"].destroy()
        self.app.merge_tasks_b.clear()

    def select_default_target_nas_b(self):
        folder = filedialog.askdirectory(title="选择全局新文件夹根目录")
        if folder:
            self.entry_target_b.delete(0, "end")
            self.entry_target_b.insert(0, folder.replace("\\", "/"))

    def start_phase_b_thread(self):
        if not self.app.merge_tasks_b:
            self.app.log_message("B", "⚠️ [警告] 请至少添加一个 JSON 与源文件夹组合！")
            return
        for task in self.app.merge_tasks_b:
            if not task["target_var"].get().strip():
                self.app.log_message("B", f"⚠️ [警告] 请为所有项目配置独立目标路径！")
                return
        self.btn_run_b.configure(state="disabled")
        self.app.log_message("B", "-"*50)
        self.app.log_message("B", f"🚀 [系统] 正在启动后台引擎进行物理复制 (Step 03)...")
        threading.Thread(target=self._worker_phase_b, daemon=True).start()

    def _worker_phase_b(self):
        log_cb = lambda msg: self.app.log_message("B", msg)
        success_count = 0
        
        for task in self.app.merge_tasks_b:
            json_path = task["json"]
            source_path = task["source"]
            target_path = task["target_var"].get().strip()
            
            log_cb(f"\n▶️ 开始合并项目: {source_path}")
            if execute_physical_copy(json_path, source_path, target_path, log_cb):
                success_count += 1
                
        self.app.log_message("B", f"\n🎉 [成功] 阶段 2 执行完毕！成功复制 {success_count} 个项目。")
        self.btn_run_b.configure(state="normal")