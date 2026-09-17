import os
import re

def scan_files(root_dir):
    print(f"Scanning {root_dir} for incorrect QAction imports...")
    pattern = re.compile(r'from\s+PyQt6\.QtWidgets\s+import\s+\(([\s\S]*?)\)', re.MULTILINE)
    simple_pattern = re.compile(r'from\s+PyQt6\.QtWidgets\s+import\s+.*QAction')
    
    found_files = []
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        
                        # Match multiline imports
                        for match in pattern.finditer(content):
                            if 'QAction' in match.group(1):
                                found_files.append(path)
                                break
                        else:
                            # Match single line imports
                            if simple_pattern.search(content):
                                found_files.append(path)
                except Exception as e:
                    print(f"Error reading {path}: {e}")
    
    return found_files

if __name__ == "__main__":
    src_dir = r"c:\Users\Admin\Desktop\AYEC Pro - Kopya\src"
    results = scan_files(src_dir)
    if results:
        print("\nFound files with incorrect QAction imports:")
        for r in results:
            print(r)
    else:
        print("\nNo incorrect QAction imports found.")
