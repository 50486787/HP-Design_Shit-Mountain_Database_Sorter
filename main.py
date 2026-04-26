import customtkinter as ctk
from gui.main_window import DataGovernanceApp

if __name__ == "__main__":
    # 启用深色/浅色模式
    ctk.set_appearance_mode("light") # 你可以在 "dark" 和 "light" 之间切换
    ctk.set_default_color_theme("blue")
    
    app = DataGovernanceApp()
    app.mainloop()