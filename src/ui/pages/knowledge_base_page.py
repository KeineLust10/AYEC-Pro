# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QTextBrowser, QTextEdit,
                             QPushButton, QFrame, QSplitter, QMenu, QApplication, QDialog,
                             QStackedWidget)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QColor, QIcon, QDesktopServices, QAction

from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.system_config import SystemConfig
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning

class KnowledgeBasePage(QWidget):
    def __init__(self, db, sector_manager=None):
        super().__init__()
        self.db = db
        self.sector_manager = sector_manager
        self.automotive_resources = [
            (
                "CarCareKiosk",
                "Araca ozel bakim, parca ve kullanim videolari.",
                "https://www.carcarekiosk.com/",
            ),
            (
                "NHTSA Recall Lookup",
                "Geri cagirma ve guvenlik kontrolleri icin resmi kaynak.",
                "https://www.nhtsa.gov/recalls",
            ),
            (
                "AutoZone Repair Help",
                "Onarim rehberleri, ariza cozumleri ve bakim icerikleri.",
                "https://www.autozone.com/lp/repair-help/",
            ),
        ]
        self.setup_ui()

    def _is_automotive(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 50, 40, 50)
        layout.setSpacing(35)
        self.is_automotive = self._is_automotive()
        
        # Header (Bespoke Typography)
        header = QHBoxLayout()
        title_vbox = QVBoxLayout()
        title = QLabel("TEKNİK BİLGİ BANKASI")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("letter-spacing: -0.5px; color: @text;"))

        subtitle = QLabel("KURUMSAL ÇÖZÜM REHBERİ VE PROTOKOLLER")
        subtitle.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        subtitle.setStyleSheet(theme_qss("color: @text_muted; letter-spacing: 2px;"))
        
        title_vbox.addWidget(title)
        title_vbox.addWidget(subtitle)
        header.addLayout(title_vbox)
        
        self.btn_new = QPushButton("📝 Yeni Çözüm Ekle")
        self.btn_new.setObjectName("Primary")
        self.btn_new.setToolTip("Bilgi bankasına yeni bir teknik çözüm makalesi ekler")
        self.btn_new.setStatusTip("Yeni makale yazma penceresini açar")
        self.btn_new.clicked.connect(self.open_add_dialog)
        
        self.btn_delete = QPushButton("🗑️ Sil")
        self.btn_delete.setObjectName("Destructive")
        self.btn_delete.setToolTip("Seçili makaleyi siler")
        self.btn_delete.clicked.connect(self.delete_article)
        
        header.addStretch()
        header.addWidget(self.btn_delete)
        header.addWidget(self.btn_new)
        header.setSpacing(10)
        
        layout.addLayout(header)
        
        # Search (Minimalist & Focused)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 Arıza, Model veya Anahtar Kelime Ara...")
        self.search.setToolTip("Hızlı arama için anahtar kelime veya hata kodu girin. FTS5 teknolojisi ile tüm makalelerde arama yapar.")
        self.search.setFixedHeight(55)
        self.search.setStyleSheet(theme_qss("""
            QLineEdit {
                border: 1px solid @border;
                background: @surface;
                color: @text;
                border-radius: 12px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QLineEdit:focus {
                border: 2px solid @accent;
            }
        """))
        self.search.textChanged.connect(self.filter_articles)
        layout.addWidget(self.search)

        # Automotive-only external recommendation
        self.external_resource_card = QFrame()
        self.external_resource_card.setObjectName("AutomotiveResourceCard")
        self.external_resource_card.setVisible(self.is_automotive)
        self.external_resource_card.setStyleSheet(theme_qss("""
            #AutomotiveResourceCard {
                background: @surface;
                border: 1px solid @border;
                border-radius: 16px;
            }
            #AutomotiveResourceCard QLabel {
                color: @text;
            }
        """))
        ext_layout = QVBoxLayout(self.external_resource_card)
        ext_layout.setContentsMargins(20, 16, 20, 16)
        ext_layout.setSpacing(14)

        ext_title = QLabel("Otomotiv Icin Onerilen Dis Kaynak")
        ext_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        ext_title.setStyleSheet(theme_qss("color: @text;"))

        ext_desc = QLabel("Otomotiv seciliyken bilgi bankasi icinde kullanabileceginiz sabit referans kaynaklari.")
        ext_desc.setWordWrap(True)
        ext_desc.setStyleSheet(theme_qss("color: @text_muted;"))

        ext_layout.addWidget(ext_title)
        ext_layout.addWidget(ext_desc)

        for name, description, url in self.automotive_resources:
            row = QFrame()
            row.setStyleSheet(theme_qss("""
                QFrame {
                    background: rgba(255,255,255,0.02);
                    border: 1px solid @border;
                    border-radius: 12px;
                }
            """))
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(14, 12, 14, 12)
            row_layout.setSpacing(12)

            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)

            name_label = QLabel(name)
            name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            name_label.setStyleSheet(theme_qss("color: @text;"))

            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(theme_qss("color: @text_muted;"))

            text_layout.addWidget(name_label)
            text_layout.addWidget(desc_label)

            open_btn = QPushButton("Ac")
            open_btn.setObjectName("Primary")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda _checked=False, target=url: QDesktopServices.openUrl(QUrl(target)))

            row_layout.addLayout(text_layout, 1)
            row_layout.addWidget(open_btn)
            ext_layout.addWidget(row)

        layout.addWidget(self.external_resource_card)

        # Main Splitter (Refined Spacing)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: transparent; width: 10px; }")
        
        # Left Side: Article List with empty state
        from src.ui.widgets.empty_state import EmptyState
        
        self.kb_content_stack = QStackedWidget()
        
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ArticleList")
        self.list_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget.itemClicked.connect(self.show_article)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        self.kb_content_stack.addWidget(self.list_widget)
        
        # Empty state for KB
        self.kb_empty_state = EmptyState(
            icon="📚",
            title="Henüz makale yok",
            message="Bilgi bankasına teknik çözümler ekleyerek başlayın.",
            action_text="Yeni Makale Ekle"
        )
        self.kb_empty_state.action_clicked.connect(self.open_add_dialog)
        self.kb_content_stack.addWidget(self.kb_empty_state)
        
        # Right Side: Content View
        self.content_view = QFrame()
        self.content_view.setObjectName("Card")
        self.content_view.setStyleSheet(theme_qss("#Card { background: @surface; border: 1px solid @border; border-radius: 16px; }"))
        cv_layout = QVBoxLayout(self.content_view)
        cv_layout.setContentsMargins(30, 30, 30, 30)
        cv_layout.setSpacing(20)
        
        self.lbl_art_title = QLabel("MAKALE SEÇİLMEDİ")
        self.lbl_art_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_art_title.setStyleSheet(theme_qss("color: @text; letter-spacing: -0.5px;"))
        self.lbl_art_title.setWordWrap(True)
        cv_layout.addWidget(self.lbl_art_title)
        
        # Divider Line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(theme_qss("background-color: @border; border: none; height: 1px;"))
        cv_layout.addWidget(line)

        self.txt_content = QTextEdit()
        self.txt_content.setReadOnly(True)
        self.txt_content.setFrameShape(QFrame.Shape.NoFrame)
        self.txt_content.setStyleSheet(theme_qss("font-size: 14px; line-height: 160%; color: @text; selection-background-color: @accent;"))
        cv_layout.addWidget(self.txt_content)
        
        splitter.addWidget(self.kb_content_stack)
        splitter.addWidget(self.content_view)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        self.refresh_list()

    def open_add_dialog(self):
        from src.ui.dialogs.add_kb_article_dialog import AddKBArticleDialog
        dialog = AddKBArticleDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            try:
                self.db.add_kb_article(data['title'], data['content'], data['tags'])
                self.refresh_list()
            except Exception as e:
                show_error(self.window(), f"Makale eklenirken hata oluştu: {e}")

    def refresh_list(self):
        self.list_widget.clear()
        query = self.search.text() if len(self.search.text()) > 2 else ""
        articles = self.db.get_kb_articles(query)
        
        # Show empty state if no articles
        if not articles:
            self.kb_content_stack.setCurrentWidget(self.kb_empty_state)
            return
        
        self.kb_content_stack.setCurrentWidget(self.list_widget)
        # articles: [(id, title, content, tags), ...]
        for art in articles:
            item = QListWidgetItem(f"📄 {art[1]}")
            item.setData(Qt.ItemDataRole.UserRole, art[2]) # content
            item.setData(Qt.ItemDataRole.UserRole + 1, art[0]) # ID
            self.list_widget.addItem(item)

    def filter_articles(self):
        # We handle filtering through refresh_list which uses FTS5 DB search
        self.refresh_list()

    def show_article(self, item):
        self.lbl_art_title.setText(item.text().replace("📄 ", ""))
        self.txt_content.setText(item.data(Qt.ItemDataRole.UserRole))

    def show_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=160):
            return
        item = self.list_widget.itemAt(position)
        if not item: return
        
        menu = QMenu()
        action_delete = QAction("❌ Sil", self)
        action_delete.triggered.connect(self.delete_article)
        menu.addAction(action_delete)
        
        # Copy Content
        action_copy = QAction("📋 İçeriği Kopyala", self)
        action_copy.triggered.connect(lambda: QApplication.clipboard().setText(item.data(Qt.ItemDataRole.UserRole)))
        menu.addAction(action_copy)
        
        menu.exec(self.list_widget.mapToGlobal(position))

    def delete_article(self):
        item = self.list_widget.currentItem()
        if not item:
            show_warning(self.window(), "Silinecek makaleyi seçin.")
            return

        article_id = item.data(Qt.ItemDataRole.UserRole + 1)
        
        # SimpleConfirmDialog ile onay al
        dialog = SimpleConfirmDialog(
            self,
            "Onay",
            "Bu makaleyi silmek istediğinize emin misiniz",
            "Evet",
            "Hayır"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.db.delete_kb_article(article_id)
                self.lbl_art_title.setText("MAKALE SEÇİLMEDİ")
                self.txt_content.clear()
                self.refresh_list()
                show_success(self.window(), "Makale başarıyla silindi")
            except Exception as e:
                show_error(self.window(), f"Silme hatası: {e}")
