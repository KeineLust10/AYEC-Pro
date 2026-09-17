import sys
import os

from PyQt6.QtWidgets import QApplication, QWidget, QScrollArea, QTableWidget
from src.utils.theme_manager import ThemeManager

def main():
    app = QApplication(sys.argv)
    
    ThemeManager._current_theme = "Nord"
    ThemeManager._install_stylesheet_patch()
    
    w = QWidget()
    s = QScrollArea()
    t = QTableWidget()
    
    test_qss = "background: @surface_alt;"
    
    w.setStyleSheet(test_qss)
    s.setStyleSheet(test_qss)
    t.setStyleSheet(test_qss)
    
    print("QWidget style:", w.styleSheet())
    print("QScrollArea style:", s.styleSheet())
    print("QTableWidget style:", t.styleSheet())

if __name__ == "__main__":
    main()
