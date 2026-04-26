import os
import json
import shutil
import uuid

def get_unique_dst(path):
    """
    如果路径已存在，则在文件名后添加短 UUID 确保唯一性
    """
    if not os.path.exists(path):
        return path
    
    base, ext = os.path.splitext(path)
    short_id = uuid.uuid4().hex[:6]
    new_path = f"{base}_{short_id}{ext}"
    
    return get_unique_dst(new_path)

def remove_empty_folders(path):
    """🌟 强迫症福音：递归删除所有空文件夹，不留幽灵空壳"""
    cleaned_count = 0
    if not os.path.isdir(path):
        return cleaned_count

    # topdown=False 确保先清理最底层的子文件夹，再清理父文件夹
    for root, dirs, files in os.walk(path, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    cleaned_count += 1
            except Exception:
                pass
    return cleaned_count

def execute_physical_move(salvage_json_path, target_root_dir, log_callback):
    """
    供 GUI 调用的第五步执行入口：执行物理移动并清理空壳
    """
    log_callback("🚀 启动【物理打捞-智能移动】程序 (支持自动重命名 & 空壳清理)...")

    if not os.path.exists(salvage_json_path):
        log_callback("❌ 找不到打捞表 JSON 文件！")
        return False

    with open(salvage_json_path, 'r', encoding='utf-8') as f:
        salvage_mapping = json.load(f)

    if not salvage_mapping:
        log_callback("🤷 打捞表为空，无任务。")
        return True

    total_files = len(salvage_mapping)
    success_count, fail_count, skip_count, rename_count = 0, 0, 0, 0

    for idx, (old_rel_path, new_rel_path) in enumerate(salvage_mapping.items(), 1):
        src_path = os.path.normpath(os.path.join(target_root_dir, old_rel_path))
        dst_path = os.path.normpath(os.path.join(target_root_dir, new_rel_path))
        if not os.path.exists(src_path):
            skip_count += 1
            continue
        try:
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            final_dst = dst_path
            is_renamed = False
            if os.path.exists(dst_path):
                final_dst = get_unique_dst(dst_path)
                is_renamed, rename_count = True, rename_count + 1
            shutil.move(src_path, final_dst)
            status = f" (⚠️ 重命名为: {os.path.basename(final_dst)})" if is_renamed else ""
            log_callback(f"✅ [{idx}/{total_files}] 移动: {os.path.basename(src_path)} -> {new_rel_path}{status}")
            success_count += 1
        except Exception as e:
            log_callback(f"❌ [{idx}/{total_files}] 失败: {os.path.basename(src_path)}, 错误: {e}")
            fail_count += 1

    log_callback("🧹 正在清理遗留的空壳文件夹...")
    empty_removed = remove_empty_folders(target_root_dir)
    log_callback(f"🎉 【阶段 3】物理打捞移动彻底结束！")
    log_callback(f"✅ 成功抢救: {success_count} 个文件")
    if rename_count > 0: log_callback(f"🔄 冲突解决: {rename_count} 个 (已自动加短UUID)")
    if fail_count > 0: log_callback(f"⚠️ 移动失败: {fail_count} 个")
    if empty_removed > 0: log_callback(f"✨ 强迫症极度舒适: 成功粉碎了 {empty_removed} 个幽灵空文件夹！")
    
    return True