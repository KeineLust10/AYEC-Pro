import sys
import os

# Set up path to import src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.utils.theme_manager import ThemeManager

def main():
    ThemeManager._current_theme = "Nord"
    ThemeManager._last_palette = ThemeManager.current_palette()
    
    test_qss = "background: @surface_alt;"
    result = ThemeManager.transform_qss(test_qss)
    
    print(f"Current theme: {ThemeManager._current_theme}")
    print(f"Is dark theme: {ThemeManager.is_dark_theme(ThemeManager._current_theme)}")
    print(f"Original: {test_qss}")
    print(f"Transformed: {result}")
    print("Nord Palette:")
    for k, v in ThemeManager.current_palette().items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
