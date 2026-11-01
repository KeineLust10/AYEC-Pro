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
from src.utils.theme_manager import ThemeManager
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
            QTabWidget::pane { border: 1px solid @border; border-radius: 6px; background: @surface; }
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
            QTabBar::tab:selected { background: @surface; color: @accent_hover; border-bottom: 1px solid @surface; }
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
        viewer.setProperty("skipThemeTransform", True)
        viewer.setOpenExternalLinks(True)
        viewer.setStyleSheet(theme_qss(
            "QTextBrowser { border: none; padding: 14px; background-color: @surface; color: @text; }"
        ))
        
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
            palette = ThemeManager.current_palette()
            viewer.setMarkdown(content)
            viewer.document().setDefaultStyleSheet(self._manual_document_css(palette))
            return viewer

        # Convert MD to HTML
        try:
            html_content = markdown.markdown(content, extensions=['tables', 'fenced_code'])
            palette = ThemeManager.current_palette()
            styled_html = "<html><head><style>{}</style></head><body>{}</body></html>".format(
                self._manual_document_css(palette), html_content
            )
            viewer.setHtml(styled_html)
        except Exception as e:
            viewer.setMarkdown(content)
            
        return viewer

    @staticmethod
    def _manual_document_css(palette):
        text = palette.get("text", "#E2E8F0")
        muted = palette.get("text_muted", "#94A3B8")
        surface = palette.get("surface", "#0F172A")
        surface_alt = palette.get("surface_alt", "#1E293B")
        border = palette.get("border", "#334155")
        accent = palette.get("accent", "#3B82F6")
        return (
            "body { font-family: 'Segoe UI', sans-serif; color: " + text + "; "
            "background-color: " + surface + "; line-height: 1.55; } "
            "h1, h2, h3 { color: " + text + "; border-bottom: 1px solid " + border + "; "
            "padding-bottom: 5px; } a { color: " + accent + "; } "
            "code, pre { background-color: " + surface_alt + "; color: " + text + "; "
            "border-radius: 4px; font-family: Consolas, monospace; } "
            "code { padding: 2px 5px; } pre { padding: 10px; } "
            "blockquote { border-left: 4px solid " + accent + "; margin: 0; "
            "padding-left: 15px; color: " + muted + "; } "
            "table { border-collapse: collapse; width: 100%; margin: 15px 0; } "
            "th, td { border: 1px solid " + border + "; padding: 8px; text-align: left; } "
            "th { background-color: " + surface_alt + "; color: " + text + "; }"
        )

