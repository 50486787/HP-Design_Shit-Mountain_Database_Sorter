import os
import json
import re
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

def get_semantic_path(relative_dir):
    """
    🧠 核心去噪黑科技：去除路径末尾的无意义纯数字层级，提取核心语义
    """
    parts = relative_dir.split('/')
    valid_parts = []
    for p in parts:
        if re.fullmatch(r'\d+', p):
            break
        valid_parts.append(p)
    return '/'.join(valid_parts) if valid_parts else relative_dir

def process_batch(batch, batch_num, total_batches, system_prompt, api_config, log_callback):
    """处理单个批次的 AI 请求，自带重试和动态 API 配置"""
    client = OpenAI(
        api_key=api_config.get("KIMI_API_KEY", ""),
        base_url=api_config.get("BASE_URL", "https://api.moonshot.cn/v1"),
    )
    model_name = api_config.get("MODEL_NAME", "kimi-k2.5")
    temperature = float(api_config.get("TEMPERATURE", "1.0"))
    think_mode = api_config.get("THINK_MODE", "enabled")

    max_retries = 3
    for attempt in range(max_retries):
        log_callback(f"⏳ [线程池] 请求 Kimi 处理第 {batch_num}/{total_batches} 批线索...")
        try:
            kwargs = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请分类以下路径：\n" + "\n".join(batch)}
                ],
                "temperature": temperature,
                "timeout": 180
            }
            
            # 如果用户在界面上关掉了深度思考，强行闭嘴
            if think_mode == "disabled":
                kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

            response = client.chat.completions.create(**kwargs)
            
            result_text = response.choices[0].message.content
            content_no_think = re.sub(r'<think>.*?</think>', '', result_text, flags=re.DOTALL).strip()
            match = re.search(r'\{.*\}', content_no_think, re.DOTALL)
            
            if match:
                batch_mapping = json.loads(match.group(0))
                # 🌟 批次级细粒度质检：如果大模型敷衍返回了空字典，直接抛出异常触发重跑
                if not batch_mapping and len(batch) > 0:
                    raise ValueError("质检失败：大模型敷衍返回了空字典")
                log_callback(f"✅ 第 {batch_num} 批判定完成！")
                return batch_mapping
            else:
                raise ValueError("质检失败：未找到合法的 JSON 格式数据")
                
        except Exception as e:
            log_callback(f"⚠️ 第 {batch_num} 批触发重跑机制 ({e})，正在进行第 {attempt + 1} 次尝试...")
            if attempt < max_retries - 1:
                time.sleep(3)
                
    raise RuntimeError(f"🚨 第 {batch_num} 批线索经过 {max_retries} 次重试依然失败。API 可能已崩溃或被限流。")

def execute_ai_anchor(skeleton_json_path, output_json_path, user_name, api_config, log_callback):
    """
    供 GUI 调用的第二步执行入口
    """
    if not os.path.exists(skeleton_json_path):
        log_callback(f"❌ 错误：找不到目录骨架文件 {skeleton_json_path}")
        return False

    max_folder_retries = 2
    for folder_attempt in range(max_folder_retries + 1):
        if folder_attempt > 0:
            log_callback(f"\n⚠️ [文件夹级质检] 触发重跑机制，正在重新处理当前项目 (第 {folder_attempt + 1} 次尝试)...")

        with open(skeleton_json_path, 'r', encoding='utf-8') as f:
            skeleton = json.load(f)

        anchors = {}
        indesign_roots = set()
        for path in skeleton.keys():
            if path.endswith("/Links") or path.endswith("/Document fonts"):
                indesign_roots.add(path.rsplit('/', 1)[0])

        log_callback(f"🔒 [防断链机制] 锁定 {len(indesign_roots)} 个排版资产包。")

        semantic_paths_set = set()

        for path in skeleton.keys():
            parts = path.split('/')
            if len(parts) >= 2:
                semantic_paths_set.add(get_semantic_path(parts[1]))
                semantic_paths_set.add(get_semantic_path('/'.join(parts[1:])))
            if len(parts) >= 3:
                semantic_paths_set.add(get_semantic_path('/'.join(parts[2:])))

        unique_semantic_paths = sorted(list(semantic_paths_set))
        log_callback(f"🧠 [智能穿透] 动态层级解析完毕，实际发送判定: {len(unique_semantic_paths)} 条...")

        system_prompt = """你是一个资深的景观设计院数据治理专家。
请根据以下标准，将杂乱的【相对路径】映射到对应的标准节点。

【目标节点池】（严禁修改编号）：
- "01基础资料/01现场勘察"
- "01基础资料/02甲方提供"
- "02管理与依据"
- "03历史成果/01排版"
- "03历史成果/02模型与效果图" (⚠️专指：项目团队自己建的场地模型、工作SU模型)
- "03历史成果/03方案图"
- "03历史成果/04技术说明与指标"
- "03历史成果/05参考内容" (⚠️专指：外网下载的素材，含 ID_、attachment、素材等字眼)
- "03历史成果/06其他"
- "06其他"

【极度重要提示】：
1. 如果该路径仅仅是一个“包含日期的项目阶段”、“汇报批次名称”或“无明显特征的综合文件夹”（例如：“20230101_方案”、“一期提交”、“二标段”、“旧版”等），请你务必返回 "06其他"！只有具备明确专业属性的（如“CAD”、“效果图”、“文本”）才归入具体分类。
2. 🌟 特例豁免：凡是路径中包含“现场”、“勘察”、“现状”、“照片”、“实景”等字眼的文件夹（如“现场照片2014-11-17”），即使带有日期，也【绝对不能】当作普通的阶段文件夹，必须强制归入 "01基础资料/01现场勘察"！

请直接返回纯 JSON：{"原路径": "目标节点"}
"""
        
        ai_mapping = {}
        batch_size = 40 
        batches = [unique_semantic_paths[i:i+batch_size] for i in range(0, len(unique_semantic_paths), batch_size)]
        
        max_workers = int(api_config.get("MAX_WORKERS", 3))
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_batch, batch, idx + 1, len(batches), system_prompt, api_config, log_callback): idx for idx, batch in enumerate(batches)}
                for future in as_completed(futures):
                    ai_mapping.update(future.result())
        except Exception as e:
            if folder_attempt < max_folder_retries:
                log_callback(f"\n🛑 触发系统熔断机制 ({e})，准备重跑当前文件夹...")
                continue
            else:
                log_callback(f"\n🛑 触发系统熔断机制: {e}")
                log_callback("🛑 API 严重故障或 Key 错误，当前项目的锚定操作已终止！")
                return False

        log_callback("🚀 正在组装终极映射表...")
        for path in skeleton.keys():
            parts = path.split('/')
            
            # 优先处理 InDesign 防断链
            is_indesign = False
            for root in indesign_roots:
                if path == root or path.startswith(root + '/'):
                    root_parts = root.split('/')
                    if len(root_parts) >= 2:
                        top_level_folder = root_parts[1]
                        top_semantic = get_semantic_path(top_level_folder)
                        top_ai_choice = ai_mapping.get(top_semantic, "06其他")
                        is_cabin = top_ai_choice.endswith("06其他")
                        raw_cabin = top_level_folder if is_cabin else "项目归档"
                    else:
                        raw_cabin = "项目归档" # 如果包裹在最外层根目录，默认套上项目归档舱
                        
                    cabin_node = f"{raw_cabin}_{user_name}" if user_name else raw_cabin
                    package_name = root.split('/')[-1]
                    rel_path = path[len(root):]
                    anchors[path] = f"03历史成果/{cabin_node}/01排版/{package_name}{rel_path}"
                    is_indesign = True
                    break
            if is_indesign: continue

            if len(parts) < 2:
                raw_cabin = "项目归档"
                cabin_node = f"{raw_cabin}_{user_name}" if user_name else raw_cabin
                anchors[path] = f"03历史成果/{cabin_node}/06其他"
                continue
                
            top_level_folder = parts[1]
            top_semantic = get_semantic_path(top_level_folder)
            top_ai_choice = ai_mapping.get(top_semantic, "06其他")
            
            # 核心：智能判断 parts[1] 到底是“时间舱/项目阶段”还是“具体内容文件夹”
            is_cabin = top_ai_choice.endswith("06其他")
            raw_cabin = top_level_folder if is_cabin else "项目归档"
            cabin_node = f"{raw_cabin}_{user_name}" if user_name else raw_cabin
            
            # 动态提取需要去锚定的纯内容相对路径
            relative_dir_path = '/'.join(parts[2:]) if is_cabin else '/'.join(parts[1:])
                
            if not relative_dir_path:
                anchors[path] = f"03历史成果/{cabin_node}/06其他"
                continue
                
            semantic_dir = get_semantic_path(relative_dir_path)
            ai_choice = ai_mapping.get(semantic_dir, "03历史成果/06其他")
            
            if ai_choice.startswith("01基础资料/"):
                target_dir = f"{ai_choice}/{cabin_node}/{relative_dir_path}"
            elif ai_choice == "02管理与依据":
                target_dir = f"02管理与依据/{cabin_node}/{relative_dir_path}"
            elif ai_choice.startswith("03历史成果/"):
                sub_cat = ai_choice.split("/")[-1] 
                target_dir = f"03历史成果/{cabin_node}/{sub_cat}/{relative_dir_path}"
            else:
                target_dir = f"03历史成果/{cabin_node}/06其他/{relative_dir_path}"
                
            anchors[path] = target_dir

        # 🌟 文件夹级终极质检 🌟
        if not anchors:
            if folder_attempt < max_folder_retries:
                log_callback("⚠️ 质检失败：最终生成的映射为空！准备重跑当前文件夹...")
                continue
            else:
                log_callback("❌ 彻底失败：多次重试依然生成空字典。")
                return False

        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(anchors, f, indent=4, ensure_ascii=False)

        if not os.path.exists(output_json_path) or os.path.getsize(output_json_path) < 10:
            if folder_attempt < max_folder_retries:
                log_callback("⚠️ 质检失败：未能成功保存 JSON 文件！准备重跑当前文件夹...")
                continue
            else:
                log_callback("❌ 彻底失败：多次重试依然未能保存有效的 JSON 文件。")
                return False

        log_callback(f"🎉 【阶段 1.2】处理完毕！锚定表已保存至: {output_json_path}")
        return True
        
    return False