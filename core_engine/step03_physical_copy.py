import os
import json
import shutil

def get_target_dir(rel_file_dir, anchors):
    """【层级向下穿透匹配】拿着文件的相对路径，去地图上找最近的锚点"""
    rel_file_dir = rel_file_dir.replace('\\', '/')
    parts = rel_file_dir.split('/')
    
    # 从最深层级开始往上找，看哪个父文件夹被 Kimi 锚定过
    for i in range(len(parts), 0, -1):
        parent_dir = '/'.join(parts[:i])
        if parent_dir in anchors:
            base_target = anchors[parent_dir]
            # 把没有被锚定到的底层子文件夹拼接回去，保证层级不丢失
            remaining_sub = '/'.join(parts[i:])
            if remaining_sub:
                return f"{base_target}/{remaining_sub}"
            return base_target
            
    # 找不到家的散落文件，直接扔进 06其他
    return "06其他"

def execute_physical_copy(anchor_json_path, source_root_dir, target_root_dir, log_callback):
    """
    供 GUI 调用的第三步执行入口
    """
    log_callback("🛠️ 正在读取 AI 生成的锚定地图...")
    
    if not os.path.exists(anchor_json_path):
        log_callback(f"❌ 错误：找不到锚定表 {anchor_json_path}")
        return False
        
    if not os.path.exists(source_root_dir):
        log_callback(f"❌ 错误：找不到源文件夹 {source_root_dir}")
        return False

    with open(anchor_json_path, 'r', encoding='utf-8') as f:
        anchors = json.load(f)

    if not os.path.exists(target_root_dir):
        os.makedirs(target_root_dir, exist_ok=True)
        log_callback(f"🔧 已自动创建目标根目录: {target_root_dir}")

    log_callback(f"🔎 正在扫描真实源文件夹: {source_root_dir}")
    
    copy_tasks = []
    parent_of_source = os.path.dirname(os.path.normpath(source_root_dir))

    for root, dirs, files in os.walk(source_root_dir):
        for file in files:
            abs_file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            # 1. 垃圾文件直接抛弃
            if ext in ['.bak', '.tmp', '.log', '.recover', '.dwl', '.dwl2'] or file.startswith('~$'):
                continue

            # 2. 计算相对路径
            rel_path_to_parent = os.path.relpath(abs_file_path, parent_of_source).replace('\\', '/')
            file_dir = os.path.dirname(rel_path_to_parent)
            
            # 3. 找新家
            target_dir = get_target_dir(file_dir, anchors)

            # 4. 组装目标绝对路径并防覆盖
            clean_target_dir = target_dir.replace("//", "/")
            final_new_rel_path = f"{clean_target_dir}/{file}"
            abs_target_path = os.path.join(target_root_dir, os.path.normpath(final_new_rel_path))
            
            if os.path.exists(abs_target_path):
                name, ext_name = os.path.splitext(file)
                counter = 1
                while os.path.exists(abs_target_path):
                    final_new_rel_path = f"{clean_target_dir}/{name}_副本{counter}{ext_name}"
                    abs_target_path = os.path.join(target_root_dir, os.path.normpath(final_new_rel_path))
                    counter += 1

            copy_tasks.append((abs_file_path, abs_target_path))

    total_files = len(copy_tasks)
    log_callback(f"🚀 路径规划完毕！共找到 {total_files} 个有效文件，开始纯 COPY 搬运...")
    
    success_count, fail_count = 0, 0
    log_interval = max(1, total_files // 10) # 动态计算汇报频率，界面汇报10次进度

    for idx, (src, dst) in enumerate(copy_tasks, 1):
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst) # 真实拷贝，保留原文件时间元数据
            success_count += 1
            
            if idx % log_interval == 0 or idx == total_files:
                log_callback(f"⏳ 拷贝进度: [{idx}/{total_files}]...")
        except Exception as e:
            log_callback(f"❌ 拷贝失败 [{os.path.basename(src)}]: {e}")
            fail_count += 1

    log_callback(f"🎉 【阶段 2】物理拷贝大功告成！成功: {success_count} 个 | 失败: {fail_count} 个")
    return True