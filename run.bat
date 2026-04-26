@echo off
:: 1. 使用 call 调用激活脚本，Windows 下路径是 Scripts\activate
call .venv\Scripts\activate

:: 2. 运行你的 Python 脚本
python main.py

:: 3. 加上 pause，如果程序报错退出，窗口会停住让你看报错信息，而不是直接闪退
pause