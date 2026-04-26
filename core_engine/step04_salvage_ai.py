import os
import json
import re
import time
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

def process_batch(batch, batch_num, total_batches, system_prompt, api_config, log_callback):
    """处理单个批次的 AI 请求，自带重试和动态 API 配置"""
    client = OpenAI(
        api_key=api_config.get("KIMI_API_KEY", ""),
        base_url=api_config.get("BASE_URL", "https://api.moonshot.cn/v1"),
    )
    model_name = api_config.get("MODEL_NAME", "kimi-k2.5")
    temperature = float(api_config.get("TEMPERATURE", "0.6"))
    think_mode = api_config.get("THINK_MODE", "disabled")

    max_retries = 3
    for attempt in range(max_retries):
        log_callback(f"⏳ [线程池] 正在请 Kimi 鉴定第 {batch_num}/{total_batches} 批杂物...")
        try:
            kwargs = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "请分类以下文件：\n" + "\n".join(batch)}
                ],
                "temperature": temperature,
                "timeout": 120
            }
            
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

def execute_salvage_ai(target_root_dir, api_config, log_callback):
    """
    供 GUI 调用的第四步执行入口：零散文件 AI 打捞
    """
    max_folder_retries = 2
    for folder_attempt in range(max_folder_retries + 1):
        if folder_attempt > 0:
            log_callback(f"\n⚠️ 触发重跑机制，正在重新处理打捞任务 (第 {folder_attempt + 1} 次尝试)...")

        log_callback(f"🔎 正在深入【06其他】杂物箱扫描文件...")
        
        trash_files = []
        
        for root, dirs, files in os.walk(target_root_dir):
            normalized_root = root.replace('\\', '/')
            if "/06其他" in normalized_root or normalized_root.endswith("06其他"):
                for file in files:
                    abs_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_file_path, target_root_dir).replace('\\', '/')
                    trash_files.append(rel_path)

        if not trash_files:
            log_callback("🎉 太棒了！这个项目的【06其他】里面空空如也，无需清理！")
            return True, None

        trash_files = sorted(trash_files)
        log_callback(f"📦 共发现 {len(trash_files)} 个待鉴定文件，呼叫 AI...")

        system_prompt = """你是一个极其严谨的景观设计院数据治理专家。
现在，你面临的是一批掉入【06其他】杂物箱的孤儿文件。
我将提供这些文件的【相对路径】。请你通过文件名语义和特有扩展名，将其精准打捞回标准的专业大类中。

【目标节点池（你只能输出以下固定词汇之一）】：
- "01基础资料/01现场勘察"
- "01基础资料/02甲方提供"
- "02管理与依据"
- "03历史成果/01排版"
- "03历史成果/02模型与效果图"
- "03历史成果/03方案图"
- "03历史成果/04技术说明与指标"
- "03历史成果/05参考内容"
- "06其他" (完全无语义的文件，继续留在这)

【打捞核心判定规则 (严格执行)】：
1. 🛑【防误判：垃圾命名绝对隔离】：凡是文件名包含“新建”、“未命名”、“微信图片”、“QQ图片”、纯数字（如 111.jpg）、或者纯英文字母乱码的文件，【绝对禁止】归入项目大类中，必须输出 `06其他`！
2. 【专业软件后缀强字典】：
   - 包含 .drs, .d5a, .ls, .skb, .skp, .max, .3dm, .rvt, .obj, .fbx, .dae ➔ `03历史成果/02模型与效果图`。
   - 包含 .idml, .indd ➔ `03历史成果/01排版`。
   - 包含 .psb, .psd, .ai ➔ 若含“彩平/总图”入 `03历史成果/03方案图`，若含“效果/鸟瞰”入 `03历史成果/02模型与效果图`，否则输出 `06其他`。
3. 🎯【过程稿与参考文本法则】：
   - PDF 包含 "Model"、"Layout"、"导出"、"图纸"，放入 `03历史成果/03方案图`。
   - 包含“策划”、“汇报”、“文本”的 .pdf 或 .ppt，若是工作过程稿，放入 `03历史成果/01排版`；若是外部案例参考，放入 `03历史成果/05参考内容`。
   - 其他无明确特征的 PDF，一律留在 `06其他`。
4. 【防误判：图片与压缩包】：
   - 包含“效果”、“渲染”、“透视”、“鸟瞰” ➔ `03历史成果/02模型与效果图`。
   - 文件名带有具体物件（如“雕塑”、“坐凳”、“铺装”、“灯具”）的单张图片，或者是包含“意向”、“参考”的文件 ➔ `03历史成果/05参考内容`。
   - 包含“模型”且带有 ID_、attachment 的 .zip 压缩包 ➔ `03历史成果/05参考内容`。
5. 💰【造价与指标法则】：
   - 凡是文件名包含“估算”、“概算”、“预算”、“造价”、“清单”、“经济指标”、“算量”的 Excel或文档 ➔ 强制归入 `03历史成果/04技术说明与指标`。

请直接输出一个 JSON 格式字典：{"输入的文件相对路径": "目标类别池里的固定词汇"}。
"""

        ai_mapping = {}
        batch_size = 40 
        batches = [trash_files[i:i+batch_size] for i in range(0, len(trash_files), batch_size)]
        
        max_workers = int(api_config.get("MAX_WORKERS", 3))
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_batch, batch, idx + 1, len(batches), system_prompt, api_config, log_callback): idx for idx, batch in enumerate(batches)}
                for future in as_completed(futures):
                    ai_mapping.update(future.result())
        except Exception as e:
            if folder_attempt < max_folder_retries:
                log_callback(f"\n🛑 触发系统异常 ({e})，准备重新扫描分析此项目...")
                continue
            else:
                log_callback(f"\n🛑 触发系统熔断机制: {e}")
                log_callback("🛑 API 严重故障或 Key 错误，当前打捞操作已终止！")
                return False, None

        log_callback("🚀 正在生成《杂物箱打捞表》...")
        
        # 🌟 智能推断默认时间舱
        default_cabin = "项目归档"
        hist_dir = os.path.join(target_root_dir, "03历史成果")
        if os.path.exists(hist_dir):
            try:
                cabins = [d for d in os.listdir(hist_dir) if os.path.isdir(os.path.join(hist_dir, d)) and d != "06其他"]
                if cabins:
                    archive_cabins = [c for c in cabins if "项目归档" in c]
                    default_cabin = archive_cabins[0] if archive_cabins else cabins[0]
            except Exception:
                pass

        salvage_mapping = {}
        for rel_path, new_category in ai_mapping.items():
            if new_category == "06其他": continue
            parts = rel_path.split('/')
            if '06其他' not in parts:
                continue
                
            idx = parts.index('06其他')
            tail_sub_path = '/'.join(parts[idx+1:])
            if not tail_sub_path:
                continue
                
            cabin_name = default_cabin
            if idx >= 2 and parts[0] in ["03历史成果", "02管理与依据", "01基础资料"]:
                cabin_name = parts[1]
                
            if new_category.startswith("01基础资料/"):
                target_file_path = f"{new_category}/{cabin_name}/{tail_sub_path}".strip('/')
            elif new_category == "02管理与依据":
                target_file_path = f"02管理与依据/{cabin_name}/{tail_sub_path}".strip('/')
            elif new_category.startswith("03历史成果/"):
                sub_cat = new_category.split("/")[-1]
                target_file_path = f"03历史成果/{cabin_name}/{sub_cat}/{tail_sub_path}".strip('/')
            else:
                continue
                
            salvage_mapping[rel_path] = target_file_path

        project_name = os.path.basename(os.path.normpath(target_root_dir))
        parent_dir = os.path.dirname(os.path.normpath(target_root_dir))
        output_json_path = os.path.join(parent_dir, f"{project_name}_打捞锚定表.json")
        
        with open(output_json_path, 'w', encoding='utf-8') as f: json.dump(salvage_mapping, f, indent=4, ensure_ascii=False)
        
        if not salvage_mapping:
            log_callback("ℹ️ 鉴定完毕：全是纯正垃圾，无需打捞，已正常放行！")
        else:
            log_callback(f"🎉 扫描完毕！共生成 {len(salvage_mapping)} 条打捞计划。")
            
        return True, output_json_path
        
    return False, None