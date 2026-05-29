import os
import json

SUPPORTED_MEDIA = {'.jpg', '.png', '.gif', '.pdf'}
SUPPORTED_TEXT = {'.txt'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

def parse_profile(root_dir):
    profile_path = os.path.join(root_dir, 'profile.txt')
    profile_data = {
        "title": "Web designer",
        "name": "Lee ah young",
        "birthdate": "1985.12.25",
        "skills": ["photoshop", "Figma", "Pakage", "webcontents", "Ai"]
    }
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
                if len(lines) >= 4:
                    profile_data["title"] = lines[0]
                    profile_data["name"] = lines[1]
                    profile_data["birthdate"] = lines[2]
                    skill_line = lines[3]
                    if "Skill" in skill_line or "#" in skill_line:
                        skills = [s.strip() for s in skill_line.replace("Skill", "").split("#") if s.strip()]
                        profile_data["skills"] = skills
                elif len(lines) > 0:
                    profile_data["name"] = lines[0]
                    if len(lines) > 1:
                        profile_data["title"] = lines[1]
        except Exception as e:
            print(f"[Warning] Failed to parse profile.txt: {e}")
    return profile_data

def get_file_info(file_path, rel_path):
    try:
        size = os.path.getsize(file_path)
        if size > MAX_FILE_SIZE or size == 0:
            return None
        
        ext = os.path.splitext(file_path)[1].lower()
        file_type = None
        if ext in SUPPORTED_MEDIA:
            file_type = 'media'
        elif ext in SUPPORTED_TEXT:
            file_type = 'text'
        else:
            return None
            
        return {
            "name": os.path.basename(file_path),
            "path": rel_path.replace("\\", "/"),
            "type": file_type,
            "ext": ext,
            "mtime": os.path.getmtime(file_path)
        }
    except Exception:
        return None

def parse_tree(root_dir, current_dir=None, depth=1):
    if current_dir is None:
        current_dir = root_dir
        
    tree = []
    
    # 4단계 이상 중첩 방지 (Root=0, 대분류=1, 중분류=2, 소분류=3)
    if depth > 4:
        return tree

    try:
        entries = os.listdir(current_dir)
    except PermissionError:
        return tree

    # 폴더와 파일 분류 및 정렬
    folders = []
    files = []
    
    for entry in entries:
        if entry.startswith('.') or entry in ['agent_core', 'templates', 'mainbg', '_site']:
            continue
            
        full_path = os.path.join(current_dir, entry)
        rel_path = os.path.relpath(full_path, root_dir)
        
        if os.path.isdir(full_path):
            folders.append((entry, full_path, rel_path))
        else:
            # 루트 디렉토리의 파일은 처리하지 않음 (profile.txt 등은 따로 처리)
            if depth > 1:
                files.append((entry, full_path, rel_path))
                
    folders.sort(key=lambda x: x[0])
    files.sort(key=lambda x: x[0])
    
    for entry, full_path, rel_path in folders:
        node = {
            "name": entry,
            "path": rel_path.replace("\\", "/"),
            "type": "folder",
            "children": parse_tree(root_dir, full_path, depth + 1),
            "files": []
        }
        
        # 현재 폴더 안의 파일들
        for f_entry, f_full, f_rel in files:
            # 자신이 포함된 폴더의 파일인지 확인 (상위에서 이미 걸렀으므로 현재 레벨의 파일만)
            pass
        
        tree.append(node)
        
    # 현재 디렉토리의 파일 목록
    current_files = []
    for f_entry, f_full, f_rel in files:
        f_info = get_file_info(f_full, f_rel)
        if f_info:
            current_files.append(f_info)
            
    if depth == 1:
        # 루트 레벨에서는 카테고리만 반환
        return tree
        
    return tree, current_files

def build_full_tree(root_dir):
    categories = []
    try:
        entries = os.listdir(root_dir)
        folders = [e for e in entries if os.path.isdir(os.path.join(root_dir, e)) and not e.startswith('.') and e not in ['agent_core', 'templates', 'mainbg', '_site']]
        folders.sort()
        
        for folder in folders:
            full_path = os.path.join(root_dir, folder)
            children = _parse_recursive(root_dir, full_path, 1)
            categories.append({
                "name": folder,
                "path": folder.replace("\\", "/"),
                "children": children.get("children", []),
                "files": children.get("files", [])
            })
    except Exception as e:
        print(f"[Error] Tree parsing failed: {e}")
        
    return {
        "profile": parse_profile(root_dir),
        "categories": categories
    }

def _parse_recursive(root_dir, current_dir, depth):
    if depth >= 3:
        # 최대 3단계 (대->중->소)
        return {"children": [], "files": _get_files(root_dir, current_dir)}
        
    children = []
    files = _get_files(root_dir, current_dir)
    
    try:
        entries = os.listdir(current_dir)
        folders = [e for e in entries if os.path.isdir(os.path.join(current_dir, e))]
        folders.sort()
        
        for folder in folders:
            full_path = os.path.join(current_dir, folder)
            rel_path = os.path.relpath(full_path, root_dir)
            child_data = _parse_recursive(root_dir, full_path, depth + 1)
            children.append({
                "name": folder,
                "path": rel_path.replace("\\", "/"),
                "children": child_data.get("children", []),
                "files": child_data.get("files", [])
            })
    except Exception:
        pass
        
    return {"children": children, "files": files}

def _get_files(root_dir, dir_path):
    files = []
    try:
        entries = os.listdir(dir_path)
        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            if os.path.isfile(full_path):
                rel_path = os.path.relpath(full_path, root_dir)
                f_info = get_file_info(full_path, rel_path)
                if f_info:
                    files.append(f_info)
        # Sort files by modification time descending (newest first)
        files.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    except Exception:
        pass
    return files
