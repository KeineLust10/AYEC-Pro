import os
import re

search_dir = r"c:\Users\engin\Desktop\yapay zeka\AYEC Pro\src"
exclude_dirs = ['__pycache__']

for root, dirs, files in os.walk(search_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            in_loop = False
            loop_indent = 0
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                indent = len(line) - len(stripped)
                
                if stripped.startswith('for '):
                    in_loop = True
                    loop_indent = indent
                elif in_loop and indent <= loop_indent and not stripped.startswith('#') and len(stripped) > 0:
                    in_loop = False
                    
                if in_loop and '.execute(' in stripped and hasattr(stripped, 'index') and 'cursor.execute' in stripped:
                    print(f"File: {os.path.relpath(filepath, search_dir)}  Line: {i+1} -> {stripped}")
