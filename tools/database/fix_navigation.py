"""Patch ModernDesktopApp.py navigation fix - processEvents before page construction."""
import sys

path = r"C:\Users\Admin\Desktop\AYEC Pro\ModernDesktopApp.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# FIX 1: _complete_menu_navigation - add processEvents before page construction
old1 = '''    def _complete_menu_navigation(self, index, placeholder=None):
        try:
            page = self.get_page(index)
            if not page:'''

new1 = '''    def _complete_menu_navigation(self, index, placeholder=None):
        try:
            # Process pending events so placeholder renders BEFORE page construction.
            # This ensures placeholder is visible and prevents "frozen" appearance.
            try:
                QApplication.processEvents()
            except Exception:
                pass
            page = self.get_page(index)
            if not page:'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("FIX 1 applied: processEvents added to _complete_menu_navigation")
else:
    print("FIX 1 FAILED: target not found")
    sys.exit(1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE")
