import os
import json
import re
import time
import datetime

try:
    import exifread
except ImportError:
    exifread = None

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

# ================= 1. 时间嗅探器函数区 =================

def get_date_from_regex(filename):
    match1 = re.search(r'(20[1-2][0-9])[-_]?([0-1][0-9])[-_]?([0-3][0-9])', filename)
    if match1: return f"{match1.group(1)}-{match1.group(2)}-{match1.group(3)}"
    match2 = re.search(r'(2[0-9])[-_]?([0-1][0-9])[-_]?([0-3][0-9])', filename)
    if match2: return f"20{match2.group(1)}-{match2.group(2)}-{match2.group(3)}"
    match3 = re.search(r'(20[1-2][0-9])', filename)
    if match3: return f"{match3.group(1)}-01-01"
    return None

def get_date_from_exif(filepath):
    if not exifread: return None
    try:
        with open(filepath, 'rb') as f:
            tags = exifread.process_file(f, stop_tag="EXIF DateTimeOriginal", details=False)
            if "EXIF DateTimeOriginal" in tags:
                raw_date = str(tags["EXIF DateTimeOriginal"])
                return raw_date.split(" ")[0].replace(":", "-")
    except Exception:
        pass
    return None

def get_date_from_pdf(filepath):
    if not PdfReader: return None
    try:
        reader = PdfReader(filepath)
        info = reader.metadata
        if info and '/CreationDate' in info:
            raw_date = info['/CreationDate']
            if raw_date.startswith('D:'):
                return f"{raw_date[2:6]}-{raw_date[6:8]}-{raw_date[8:10]}"
    except Exception:
        pass
    return None

def get_true_date(filepath, filename, ext):
    date_str = get_date_from_regex(filename)
    if date_str: return f"{date_str}(正则)"
    
    if ext in ['.jpg', '.jpeg']:
        date_str = get_date_from_exif(filepath)
        if date_str: return f"{date_str}(EXIF)"
    elif ext == '.pdf':
        date_str = get_date_from_pdf(filepath)
        if date_str: return f"{date_str}(PDF)"
            
    try:
        mtime = os.path.getmtime(filepath)
        dt = datetime.datetime.fromtimestamp(mtime)
        return f"{dt.strftime('%Y-%m-%d')}(系统)"
    except Exception:
        return "未知时间"

def get_file_size_str(filepath):
    try:
        size_bytes = os.path.getsize(filepath)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb < 1:
            return f"{size_bytes / 1024:.0f}KB"
        elif size_mb >= 1024:
            return f"{size_mb / 1024:.2f}GB"
        else:
            return f"{size_mb:.1f}MB"
    except Exception:
        return "未知大小"

# ================= 2. 核心：多维标签树状扫描 =================

def build_time_aware_tree(dir_path):
    tree = {}
    try:
        entries = os.listdir(dir_path)
    except PermissionError:
        return "[无访问权限]"

    files_with_info = []
    dirs = []
    junk_extensions = ['.bak', '.dwl', '.dwl2', '.tmp', '.err', '.log', '.recover']

    for entry in entries:
        ext_lower = os.path.splitext(entry)[1].lower()
        if entry.startswith('~$') or entry.lower() in ['thumbs.db', 'ehthumbs.db', '.ds_store'] or ext_lower in junk_extensions:
            continue
            
        full_path = os.path.join(dir_path, entry)
        if os.path.isdir(full_path):
            dirs.append(entry)
        else:
            true_date = get_true_date(full_path, entry, ext_lower)
            size_str = get_file_size_str(full_path)
            type_hint = ""
            if ext_lower == '.dwg': type_hint = " 📐[CAD源文件]"
            elif ext_lower in ['.skp', '.3dm', '.max', '.obj', '.fbx']: type_hint = " 🧊[三维模型]"
            elif ext_lower == '.indd': type_hint = " 📰[排版源文件]"
            elif ext_lower == '.psd': type_hint = " 🎨[后期源文件]"
            elif ext_lower in ['.mp4', '.avi', '.mov'] and "GB" in size_str: type_hint = " 🚁[大体积视频-重资产]"

            files_with_info.append(f"{entry} [{true_date}] [{size_str}]{type_hint}")

    if files_with_info: tree["_files"] = sorted(files_with_info)
    for d in sorted(dirs): tree[d] = build_time_aware_tree(os.path.join(dir_path, d))
    return tree

def extract_directory_skeleton(tree_node, current_path=""):
    skeleton = {}
    file_count = len(tree_node.get("_files", []))
    if current_path: skeleton[current_path] = file_count
    for key, value in tree_node.items():
        if key != "_files" and isinstance(value, dict):
            next_path = f"{current_path}/{key}" if current_path else key
            skeleton.update(extract_directory_skeleton(value, next_path))
    return skeleton

# ================= 3. 供 GUI 调用的执行入口 =================

def execute_scan(target_dir, log_callback):
    """
    target_dir: 要扫描的源文件夹路径
    log_callback: 接收字符串的回调函数，用于打印到 GUI 面板
    """
    if not os.path.exists(target_dir):
        log_callback(f"❌ 错误：找不到目标路径 {target_dir}！")
        return False, None
        
    if not exifread: log_callback("⚠️ 未安装 exifread 库，EXIF时间提取功能将失效。")
    if not PdfReader: log_callback("⚠️ 未安装 PyPDF2 库，PDF内部时间提取功能将失效。")

    project_name = os.path.basename(os.path.abspath(target_dir))
    parent_dir = os.path.dirname(os.path.abspath(target_dir))
    
    output_tree_json = os.path.join(parent_dir, f"{project_name}_多维资产树.json")
    output_skeleton_json = os.path.join(parent_dir, f"{project_name}_目录骨架与数量.json")

    log_callback(f"🚀 开始深度扫描项目: {project_name}")
    log_callback("🔎 正在解析文件真实时间、体量及类型，请稍候...")
    
    # 核心运算
    master_tree = {project_name: build_time_aware_tree(target_dir)}
    skeleton_summary = extract_directory_skeleton(master_tree)

    # 输出保存
    with open(output_tree_json, 'w', encoding='utf-8') as f:
        json.dump(master_tree, f, indent=4, ensure_ascii=False)
    with open(output_skeleton_json, 'w', encoding='utf-8') as f:
        json.dump(skeleton_summary, f, indent=4, ensure_ascii=False)

    log_callback(f"✅ 【阶段 1.1】扫描完毕！骨架提取成功。")
    log_callback(f"🦴 已保存骨架字典供 AI 使用。")
    
    # 返回 True 并在元组中带上生成的 json 路径，交给 Step 02 使用
    return True, output_skeleton_json