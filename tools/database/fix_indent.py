
import os

file_path = "ModernDesktopApp.py"
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    commenting = False
    
    for i, line in enumerate(lines):
        # Detect the start of the block we want to comment out
        if "# def check_registration(self):" in line:
            commenting = True
            new_lines.append(line)
            continue
            
        # Stop commenting when we hit the next method
        if "def complete_registration(self, data):" in line:
            commenting = False
            
        if commenting:
            # Check if line is already empty or just whitespace
            if line.strip():
                new_lines.append("# " + line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    print("File updated successfully.")
    
except Exception as e:
    print(f"Error: {e}")
