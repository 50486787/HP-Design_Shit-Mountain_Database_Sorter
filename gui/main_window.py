import customtkinter as ctk
from tkinter import ttk
import os
import configparser
import datetime

# 引入独立拆分出的三个页面组件
from gui.tab_phase1 import TabPhase1
from gui.tab_phase2 import TabPhase2
from gui.tab_phase3 import TabPhase3

class DataGovernanceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("资产智能治理引擎 V0.1")
        self.geometry("1200x800")
        
        # 加载配置
        self.config = configparser.ConfigParser()
        self.config.read("config.ini", encoding="utf-8")
        
        # === 全局字体设置中心 ===
        self.font_title = ("黑体", 20, "bold")
        self.font_tab = ("黑体", 18, "bold")
        self.font_btn_main = ("黑体", 18, "bold")
        self.font_body_bold = ("黑体", 18, "bold")
        self.font_body = ("黑体", 18)

        # 初始化本地日志保存目录
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

        self.setup_styles()

        # 核心数据流中心 (供各个子页面共享使用)
        self.source_folders_a = []
        self.merge_tasks_b = [] 
        self.salvage_folders_c = []
        self.api_widgets = {} # 统一管理 API 设置的输入框组件

        # 搭建三大核心工作区
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(padx=20, pady=20, fill="both", expand=True)
        self.tabview._segmented_button.configure(font=self.font_tab)
        
        self.tab_a = self.tabview.add("阶段1: 生成文件夹锚定表")
        self.tab_b = self.tabview.add("阶段2: 复制到新文件夹")
        self.tab_c = self.tabview.add("阶段3: 整理零散文件")
        
        # 实例化各个独立的 Tab 页面，并把自己 (self) 传给它们
        self.phase1 = TabPhase1(self.tab_a, self)
        self.phase2 = TabPhase2(self.tab_b, self)
        self.phase3 = TabPhase3(self.tab_c, self)

    def setup_styles(self):
        self.style = ttk.Style(self)
        self.style.theme_use("default")
        mode = ctk.get_appearance_mode()
        if mode == "Dark":
            tree_bg, tree_fg, tree_heading_bg = "#2b2b2b", "white", "#565b5e"
        else: 
            tree_bg, tree_fg, tree_heading_bg = "#ebebeb", "black", "#d6d6d6"

        self.style.configure("Treeview", font=self.font_body, background=tree_bg, foreground=tree_fg,
                             rowheight=40, fieldbackground=tree_bg, bordercolor="#333333", borderwidth=0)
        self.style.map('Treeview', background=[('selected', ctk.ThemeManager.theme["CTkButton"]["fg_color"][1])])
        self.style.configure("Treeview.Heading", font=self.font_body_bold, background=tree_heading_bg,
                             foreground=tree_fg, relief="flat")

    def build_settings_frame(self, parent, section):
        frame = ctk.CTkFrame(parent)
        api_key = self.config.get(section, "KIMI_API_KEY", fallback="")
        base_url = self.config.get(section, "BASE_URL", fallback="https://api.moonshot.cn/v1")
        model = self.config.get(section, "MODEL_NAME", fallback="kimi-k2.5")
        temp = self.config.get(section, "TEMPERATURE", fallback="1.0" if section=="API_A" else "0.6")
        think = self.config.get(section, "THINK_MODE", fallback="enabled" if section=="API_A" else "disabled")
        max_workers = self.config.get("APP", "max_workers", fallback="3")
        
        frame.grid_columnconfigure((1, 3), weight=1)
        
        ctk.CTkLabel(frame, text=f"⚙️ {section} Key:", font=self.font_body).grid(row=0, column=0, padx=(10, 5), pady=(5, 2), sticky="e")
        entry_key = ctk.CTkEntry(frame, show="*", height=25, font=self.font_body)
        entry_key.insert(0, api_key)
        entry_key.grid(row=0, column=1, padx=5, pady=(5, 2), sticky="ew")
        
        ctk.CTkLabel(frame, text="Base URL:", font=self.font_body).grid(row=0, column=2, padx=(10, 5), pady=(5, 2), sticky="e")
        entry_url = ctk.CTkEntry(frame, height=25, font=self.font_body)
        entry_url.insert(0, base_url)
        entry_url.grid(row=0, column=3, padx=5, pady=(5, 2), sticky="ew")
        
        ctk.CTkLabel(frame, text="模型名称:", font=self.font_body).grid(row=1, column=0, padx=(10, 5), pady=(2, 5), sticky="e")
        entry_model = ctk.CTkEntry(frame, height=25, font=self.font_body)
        entry_model.insert(0, model)
        entry_model.grid(row=1, column=1, padx=5, pady=(2, 5), sticky="ew")
        
        inner_frame = ctk.CTkFrame(frame, fg_color="transparent")
        inner_frame.grid(row=1, column=2, columnspan=2, sticky="w", padx=5, pady=(2, 5))
        
        ctk.CTkLabel(inner_frame, text="温度:", font=self.font_body).pack(side="left", padx=(5, 2))
        entry_temp = ctk.CTkEntry(inner_frame, width=50, height=25, font=self.font_body)
        entry_temp.insert(0, temp)
        entry_temp.pack(side="left", padx=(0, 15))
        
        think_var = ctk.StringVar(value=think)
        switch_think = ctk.CTkSwitch(inner_frame, text="深度思考", font=self.font_body, variable=think_var, onvalue="enabled", offvalue="disabled", switch_width=36, switch_height=18)
        switch_think.pack(side="left")
        
        ctk.CTkLabel(inner_frame, text="并发数:", font=self.font_body).pack(side="left", padx=(15, 2))
        entry_workers = ctk.CTkEntry(inner_frame, width=40, height=25, font=self.font_body)
        entry_workers.insert(0, max_workers)
        entry_workers.pack(side="left")
        
        btn_save = ctk.CTkButton(frame, text="💾 保存本页模型设置", width=120, font=self.font_body_bold,
                                 command=lambda: self.save_specific_settings(section, entry_key, entry_url, entry_model, entry_temp, think_var, entry_workers))
        btn_save.grid(row=0, column=4, rowspan=2, padx=15, pady=10)
        
        # 记录下这些输入框，方便后续直接从界面上“偷数据”
        self.api_widgets[section] = {
            "key": entry_key,
            "url": entry_url,
            "model": entry_model,
            "temp": entry_temp,
            "think": think_var,
            "workers": entry_workers
        }
        return frame

    def get_api_config(self, section):
        """不管用户有没有点击保存，直接从界面实时读取当前填写的 API 参数"""
        w = self.api_widgets.get(section)
        if w:
            return {
                "KIMI_API_KEY": w["key"].get().strip(),
                "BASE_URL": w["url"].get().strip(),
                "MODEL_NAME": w["model"].get().strip(),
                "TEMPERATURE": w["temp"].get().strip(),
                "THINK_MODE": w["think"].get(),
                "MAX_WORKERS": w["workers"].get().strip()
            }
        return {}

    def save_specific_settings(self, section, w_key, w_url, w_model, w_temp, w_think_var, w_workers):
        if not self.config.has_section(section): self.config.add_section(section)
        if not self.config.has_section("APP"): self.config.add_section("APP")
        
        self.config.set(section, "KIMI_API_KEY", w_key.get().strip())
        self.config.set(section, "BASE_URL", w_url.get().strip())
        self.config.set(section, "MODEL_NAME", w_model.get().strip())
        self.config.set(section, "TEMPERATURE", w_temp.get().strip())
        self.config.set(section, "THINK_MODE", w_think_var.get())
        self.config.set("APP", "max_workers", w_workers.get().strip())
        
        with open("config.ini", "w", encoding="utf-8") as f: self.config.write(f)
        tab_name = "A" if section == "API_A" else "C"
        self.log_message(tab_name, f"✅ [系统] {section} 与并发数已成功保存！")

    def log_message(self, tab, message):
        if tab == "A" and hasattr(self, 'phase1'): textbox = self.phase1.log_textbox_a
        elif tab == "B" and hasattr(self, 'phase2'): textbox = self.phase2.log_textbox_b
        elif tab == "C" and hasattr(self, 'phase3'): textbox = self.phase3.log_textbox_c
        else: return
        
        tab_num = {"A": "1", "B": "2", "C": "3"}.get(tab, tab)
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        display_msg = f"[{timestamp}] {message}"
        
        textbox.insert("end", display_msg + "\n")
        textbox.see("end") 
        log_path = os.path.join(self.log_dir, f"run_log_{datetime.datetime.now().strftime('%Y-%m-%d')}.txt")
        with open(log_path, "a", encoding="utf-8") as f: f.write(f"[阶段 {tab_num}] {display_msg}\n")

    # --- 共享的左侧 TreeView 文件树控制逻辑 ---
    def get_path_from_item(self, tree, item_id):
        text = tree.item(item_id, "text")
        if text == "...":
            return None # 拦截并忽略用于显示的占位符节点
            
        path_parts = [text.replace("🚫 ", "")]
        parent_id = tree.parent(item_id)
        while parent_id:
            path_parts.insert(0, tree.item(parent_id, "text"))
            parent_id = tree.parent(parent_id)
        return os.path.join(*path_parts)

    def populate_drives(self, tree):
        if os.name == 'nt':
            import string
            for drive in [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:")]:
                tree.insert(tree.insert("", "end", text=drive, open=False), "end", text="...")
        else:
            tree.insert(tree.insert("", "end", text="/", open=False), "end", text="...")

    def on_tree_open(self, event):
        tree = event.widget
        item_id = tree.focus()
        children = tree.get_children(item_id)
        if children and tree.item(children[0])['text'] == '...': tree.delete(children[0])
        else: return

        path = self.get_path_from_item(tree, item_id)
        try:
            for item in sorted(os.listdir(path)):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    try:
                        child_node = tree.insert(item_id, "end", text=item, open=False)
                        if os.listdir(full_path): tree.insert(child_node, "end", text="...")
                    except PermissionError:
                        tree.insert(item_id, "end", text=f"🚫 {item}", open=False)
        except PermissionError: pass