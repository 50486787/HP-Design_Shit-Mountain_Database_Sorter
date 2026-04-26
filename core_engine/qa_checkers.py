import os
import json
import time
import logging

class QualityInspectionError(Exception):
    """自定义的质检异常，用于触发重试机制"""
    pass

def run_step02_with_healing(json_path, step02_ai_func, *args, max_retries=2):
    """
    📍 Step 2.5 智能质检与自愈层
    负责执行 Step02 的 AI 锚定，并对结果进行严格体检。
    
    :param json_path: 预期的 JSON 产出路径
    :param step02_ai_func: 你的 step02 核心大模型请求函数
    :param max_retries: 最大重试次数（防抱死阀门）
    """
    for attempt in range(max_retries + 1):
        try:
            # 1. 执行核心 AI 生成任务
            step02_ai_func(*args)
            
            # 2. 查缺失：大模型是否中断未生成？
            if not os.path.exists(json_path):
                raise QualityInspectionError("体检失败：文件缺失，大模型未生成 JSON 文件。")
                
            # 3. 查空壳：文件体积极小？
            if os.path.getsize(json_path) < 10:
                raise QualityInspectionError("体检失败：文件体积异常过小，疑似残缺。")
                
            # 4. 查空字典：大模型严重敷衍？
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data:  # 匹配 {} 或 [] 
                    raise QualityInspectionError("体检失败：JSON 内容为空字典或空列表。")
                    
            # 如果能走到这里，说明全部体检通过！
            return True, f"✅ [{os.path.basename(json_path)}] 质检通过"
            
        except Exception as e:
            if attempt < max_retries:
                logging.warning(f"⚠️ 命中 [需重跑] 标签 ({str(e)})，正在进行第 {attempt + 1} 次重跑...")
                time.sleep(2)  # 给 API 缓冲时间
            else:
                # 触发防抱死阀门，抛出运行时错误交由上层或 UI 捕获
                error_msg = f"❌ 彻底失败：已达到最大重试次数 {max_retries}。最后异常：{str(e)}"
                logging.error(error_msg)
                # 依据架构规范：遇到致命错误向上抛出
                raise RuntimeError(error_msg)

def run_step04_with_qa(target_06_folder, salvage_json_path, step04_ai_func, *args, max_retries=2):
    """
    📍 Step 4.5 终极扫尾质检层（精准防误判）
    负责执行 Step04 打捞，并判断是否需要进入 Step05。
    
    :return: (bool) 是否需要继续执行后续的 Step05 (物理移动与粉碎)
    """
    # 【状态 A：真干净（常规拦截）】
    # 如果 06其他 文件夹不存在，或者里面完全没有文件/子文件夹
    if not os.path.exists(target_06_folder) or not os.listdir(target_06_folder):
        logging.info("✨ 状态 A 拦截：[06其他] 内部本就空无一物，无需打捞，绿灯通行。")
        return False  # 返回 False 告诉外层，不需要执行 step05 了
        
    # 开始带重试机制的打捞
    for attempt in range(max_retries + 1):
        try:
            # 执行核心 AI 打捞判定
            step04_ai_func(*args)
            
            # 【状态 C：正常生成（通行许可）】
            # 验证生成的打捞表 JSON
            if not os.path.exists(salvage_json_path):
                raise QualityInspectionError("未找到生成的打捞表 JSON。")
            
            with open(salvage_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not data:
                    raise QualityInspectionError("打捞表 JSON 成功生成，但内容为空。")
            
            logging.info("✅ 状态 C 许可：打捞表 JSON 质检通过，允许执行物理归位。")
            return True  # 明确返回 True，指示上层去执行 step05
            
        except Exception as e:
            # 【状态 B：真报错（异常拦截）】
            if attempt < max_retries:
                logging.warning(f"⚠️ 打捞过程触发异常拦截 ({str(e)})，正在重跑...")
                time.sleep(2)
            else:
                error_msg = f"❌ 终极扫尾崩溃：已达到最大重试次数。最后异常：{str(e)}"
                logging.error(error_msg)
                # 依据架构规范：遇到致命错误向上抛出
                raise RuntimeError(error_msg)

    return False