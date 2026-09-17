# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QTextBrowser, QLabel)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QAction
import os
try:
    import markdown
except ImportError:
    markdown = None
from src.utils.theme_colors import theme_qss
from src.utils.path_helper import PathHelper

class UserManualPage(QWidget):
    """
    Kullanım Kılavuzu ve Kurulum Rehberi Görüntüleyici
    """
    def __init__(self, db=None):
        super().__init__()
        self.db = db
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("📚 Yardım ve Kılavuzlar")
        header.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text; margin-bottom: 10px;"))
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane { border: 1px solid @border; border-radius: 6px; background: white; }
            QTabBar::tab {
                background: @surface_alt;
                padding: 10px 20px;
                border: 1px solid @border;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
                color: @text;
            }
            QTabBar::tab:selected { background: white; color: @accent_hover; border-bottom: 1px solid white; }
        """))
        
        # Guide 1: Kullanım Kılavuzu
        self.tab_user_guide = self.create_doc_viewer("KULLANIM_KILAVUZU.md")
        self.tabs.addTab(self.tab_user_guide, "Kullanım Kılavuzu")
        
        # Guide 2: Kurulum Rehberi
        self.tab_setup_guide = self.create_doc_viewer("KURULUM_REHBERI.md")
        self.tabs.addTab(self.tab_setup_guide, "Kurulum Rehberi")
        
        layout.addWidget(self.tabs)
        
    def create_doc_viewer(self, filename):
        """Markdown dosyasını okuyup HTML olarak gösteren widget"""
        viewer = QTextBrowser()
        viewer.setOpenExternalLinks(True)
        viewer.setStyleSheet(theme_qss("border: none; padding: 15px; background-color: white;"))
        
        # Try to find file in root or dist
        paths_to_check = [
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(os.getcwd()), filename),
            os.path.join(PathHelper.get_app_data_dir(), filename) # Check AppData too
        ]
        
        content = f"# {filename} Bulunamadı\nLütfen dosyanın mevcut olduğundan emin olun."
        
        for path in paths_to_check:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    break
                except Exception as e:
                    content = f"Error reading file: {e}"
        
        if markdown is None:
            viewer.setPlainText(content)
            return viewer

        # Convert MD to HTML
        try:
            html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
            # Basic styling
            styled_html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', sans-serif; color: black; line-height: 1.6; }}
                    h1, h2, h3 {{ color: black; border-bottom: 1px solid lightgray; padding-bottom: 5px; }}
                    code {{ background-color: whitesmoke; padding: 2px 5px; border-radius: 3px; font-family: Consolas, monospace; }}
                    pre {{ background-color: whitesmoke; padding: 10px; border-radius: 5px; overflow-x: auto; }}
                    blockquote {{ border-left: 4px solid dodgerblue; margin: 0; padding-left: 15px; color: gray; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                    th, td {{ border: 1px solid silver; padding: 8px; text-align: left; }}
                    th {{ background-color: gainsboro; }}
                </style>
            </head>
            <body>
            {html_content}
            </body>
            </html>
            """
            viewer.setHtml(styled_html)
        except Exception as e:
            viewer.setText(f"Markdown render hatası: {e}\n\n{content}")
            
        return viewer

