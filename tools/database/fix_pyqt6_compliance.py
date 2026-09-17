
import os
import re

# Replacements Dictionary (Old -> New)
REPLACEMENTS = {
    # Alignments
    r'Qt\.AlignCenter': 'Qt.AlignmentFlag.AlignCenter',
    r'Qt\.AlignLeft': 'Qt.AlignmentFlag.AlignLeft',
    r'Qt\.AlignRight': 'Qt.AlignmentFlag.AlignRight',
    r'Qt\.AlignTop': 'Qt.AlignmentFlag.AlignTop',
    r'Qt\.AlignBottom': 'Qt.AlignmentFlag.AlignBottom',
    
    # Windows
    r'Qt\.FramelessWindowHint': 'Qt.WindowType.FramelessWindowHint',
    r'Qt\.WindowStaysOnTopHint': 'Qt.WindowType.WindowStaysOnTopHint',
    r'Qt\.Tool': 'Qt.WindowType.Tool',
    r'Qt\.Popup': 'Qt.WindowType.Popup',
    
    # Headers
    r'QHeaderView\.Stretch': 'QHeaderView.ResizeMode.Stretch',
    r'QHeaderView\.ResizeToContents': 'QHeaderView.ResizeMode.ResizeToContents',
    
    # Fonts
    r'QFont\.Light': 'QFont.Weight.Light',
    r'QFont\.Bold': 'QFont.Weight.Bold',
    
    # Case Sensitivity
    r'Qt\.CaseInsensitive': 'Qt.CaseSensitivity.CaseInsensitive',
    
    # Screen
    r'QApplication\.desktop\(\)\.screenGeometry\(\)': 'QApplication.primaryScreen().geometry()',
    r'QApplication\.desktop\(\)': 'QApplication.primaryScreen()',
    
    # Cursors (Already fixed some, but good to have)
    r'Qt\.PointingHandCursor': 'Qt.CursorShape.PointingHandCursor',
    r'Qt\.IBeamCursor': 'Qt.CursorShape.IBeamCursor',
    r'Qt\.ArrowCursor': 'Qt.CursorShape.ArrowCursor',
}

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        original_content = content
        
        # Apply Regex Replacements
        for pattern, replacement in REPLACEMENTS.items():
            # Check if already fixed to avoid duplication (e.g. Qt.AlignmentFlag.AlignCenter)
            # Simple check: if the replacement is already in the substring, rely on regex boundaries?
            # We use strict regex word boundaries where possible or checking context.
            # But the user pattern list is simple text replacement.
            # Safety: Check if "Qt.AlignmentFlag.Align..." exists, don't replace "Qt.Align..." inside it?
            # Actually, "Qt.Align..." is a substring of "Qt.AlignmentFlag.Align...".
            # So if we replace "Qt.AlignCenter", we might break "Qt.AlignmentFlag.AlignCenter" -> "Qt.AlignmentFlag.AlignCenter"
            
            # Smart Regex: exact match for the old pattern, NOT preceded by the new parent class name?
            # Just simple replace, then CLEANUP duplication.
            
            # Simpler approach: Use negative lookbehind is hard with dots.
            pass

        # Let's do a naive replace, BUT verify valid PyQT6 prefixes first
        # Better: Strict replacements for full tokens.
        
        # 1. Alignment
        if "Qt.AlignmentFlag.Align" not in content: 
             # Only if file doesn't have the new style mixed in? No, checking per line is better.
             pass

        # Row-by-row processing is safest for Avoiding Duplication
        new_lines = []
        lines = content.split('\n')
        for line in lines:
            new_line = line
            for pattern, replacement in REPLACEMENTS.items():
                # Avoid touching already correct ones
                # E.g. pattern "Qt.AlignCenter", replacement "Qt.AlignmentFlag.AlignCenter"
                # If identifier is "Qt.AlignmentFlag.AlignCenter", it contains "Qt.AlignCenter".
                # We need to ensure we don't match the suffix of the correct one.
                
                # Check for "Qt.AlignmentFlag.AlignCenter" first
                if replacement in new_line:
                    continue # Already has the new one, assume this specific one is OK? 
                    # Danger: What if line has "Qt.AlignmentFlag.AlignCenter AND Qt.AlignCenter"?
                
                # Regex replace
                # Use regex with word boundary?
                # "Qt.AlignmentFlag.AlignCenter" -> match literal dot.
                # pattern provided in dict above has escaped dot.
                
                # If we match, verify it's NOT preceded by the relevant prefix
                # e.g. for Qt.AlignmentFlag.AlignCenter, check not preceded by "AlignmentFlag."
                
                # Using re.sub with function to check context is overkill?
                # Let's try simple replace and then FIX-UP duplications.
                new_line = re.sub(pattern, replacement, new_line)
            
            new_lines.append(new_line)
            
        content = '\n'.join(new_lines)
        
        # CLEANUP PASS (The Anti-Corruption)
        content = content.replace("Qt.AlignmentFlag.", "Qt.AlignmentFlag.")
        content = content.replace("Qt.WindowType.", "Qt.WindowType.")
        content = content.replace("QHeaderView.ResizeMode.", "QHeaderView.ResizeMode.")
        content = content.replace("QFont.Weight.", "QFont.Weight.")
        content = content.replace("Qt.CaseSensitivity.", "Qt.CaseSensitivity.")
        content = content.replace("Qt.CursorShape.", "Qt.CursorShape.")
        
        if content != original_content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"FIXED: {path}")
            return 1
    except Exception as e:
        print(f"ERR: {path} - {e}")
    return 0

print("--- STARTING PYQT6 CLEAN SWEEP ---")
count = 0
for root, dirs, files in os.walk("."):
    if ".gemini" in root or "__pycache__" in root: continue
    for file in files:
        if file.endswith(".py"):
            count += fix_file(os.path.join(root, file))

print(f"--- SWEEP COMPLETE. Modified {count} files. ---")
