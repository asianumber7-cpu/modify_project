import os

# 제외할 폴더 및 파일 패턴 (필요에 따라 추가하세요)
IGNORE_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', 'env', '.venv', 
    'dist', 'build', '.idea', '.vscode', '.pytest_cache', 'migrations'
}
IGNORE_FILES = {
    '.DS_Store', 'package-lock.json', 'yarn.lock', '__init__.py'
}

def print_tree(startpath, prefix=""):
    files = []
    dirs = []
    
    # 현재 디렉토리의 항목 분류
    try:
        entries = sorted(os.listdir(startpath))
    except PermissionError:
        return

    for entry in entries:
        if entry in IGNORE_DIRS or entry in IGNORE_FILES:
            continue
        
        full_path = os.path.join(startpath, entry)
        if os.path.isdir(full_path):
            dirs.append(entry)
        else:
            files.append(entry)
            
    # 항목 출력
    entries = dirs + files
    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        
        print(f"{prefix}{connector}{entry}")
        
        full_path = os.path.join(startpath, entry)
        if os.path.isdir(full_path):
            extension = "    " if is_last else "│   "
            print_tree(full_path, prefix + extension)

if __name__ == "__main__":
    print(f". (Project Root: {os.path.basename(os.getcwd())})")
    print_tree(".")