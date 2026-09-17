import os
import re

search_dir = r"c:\Users\engin\Desktop\yapay zeka\AYEC Pro"
exclude_dirs = ['dist', 'backups', 'venv', '.git', '__pycache__', '.agents']

for root, dirs, files in os.walk(search_dir):
    dirs[:] = [d for d in dirs if d not in exclude_dirs]
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Find for loops that contain cursor.execute soon after
                if re.search(r'for\s+.*\n(?:.*\n){0,10}\s+.*?cursor\.execute', content):
                    print('Possible N+1 query in:', os.path.relpath(filepath, search_dir))
