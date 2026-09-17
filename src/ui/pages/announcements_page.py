# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QDialog)
from src.utils.theme_colors import theme_qss, qc, tc, qc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QColor, QAction
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.appearance_mode import AppearanceModeManager
import logging

logger = logging.getLogger("AYECProLogger")


class AnnouncementDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, announcement_data=None):
        super().__init__(
            title="Duyuru Duzenle" if announcement_data else "Yeni Duyuru Ekle",
            parent=parent,
            width=550,
            height=480,
        )
        self.db = db
        self.announcement_data = announcement_data # (date, priority, title, content, author, id)
        self.set_footer_visible(False)
        self.setup_ui()
        
        self._wire_ui_signals()
    def setup_ui(self):
        self.setStyleSheet(theme_qss("""
            QDialog { background-color: @surface; }
            QLabel { color: @text; font-weight: 600; font-size: 10pt; }
            QLineEdit, QTextEdit, QComboBox {
                border: 2px solid @border; border-radius: 6px; padding: 10px;
                background-color: @surface_alt; color: @text; font-size: 10pt;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 2px solid @accent; }
        """))
        
        layout = self.content_layout
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Header
        header_title = "📢 Duyuru Düzenle" if self.announcement_data else "📢 Yeni Duyuru Oluştur"
        header_label = QLabel(header_title)
        header_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_label.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(header_label)
        
        # Fields
        layout.addWidget(QLabel("Başlık *"))
        self.inp_title = QLineEdit()
        self.inp_title.setPlaceholderText("Duyuru başlığını giriniz")
        self.inp_title.setFixedHeight(40)
        layout.addWidget(self.inp_title)
        
        layout.addWidget(QLabel("Öncelik"))
        self.cmb_priority = QComboBox()
        self.cmb_priority.addItems(["Normal", "Yüksek", "Düşük"])
        self.cmb_priority.setFixedHeight(40)
        layout.addWidget(self.cmb_priority)
        
        layout.addWidget(QLabel("İçerik *"))
        self.txt_content = QTextEdit()
        self.txt_content.setPlaceholderText("Duyuru içeriğini giriniz...")
        self.txt_content.setMinimumHeight(140)
        layout.addWidget(self.txt_content)
        
        # Populate if editing
        if self.announcement_data:
            # data: date, priority, title, content, author, id
            self.inp_title.setText(str(self.announcement_data[2]))
            self.cmb_priority.setCurrentText(str(self.announcement_data[1]))
            self.txt_content.setPlainText(str(self.announcement_data[3]))
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        if self.announcement_data:
            btn_delete = QPushButton("🗑 Sil")
            btn_delete.setFixedSize(100, 45)
            btn_delete.setStyleSheet(theme_qss("""
                QPushButton { background-color: @danger; color: white; border-radius: 6px; font-weight: 600; font-size: 11pt; }
                QPushButton:hover { background-color: @danger; }
            """))
            btn_delete.clicked.connect(self.delete_announcement)
            btn_layout.addWidget(btn_delete)
            
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(100, 45)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton { background-color: @disabled_text; color: white; border-radius: 6px; font-weight: 600; font-size: 11pt; }
            QPushButton:hover { background-color: @text_muted; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("💾 Kaydet" if self.announcement_data else "📢 Yayınla")
        btn_ok.setFixedSize(120, 45)
        btn_ok.setStyleSheet(theme_qss("""
            QPushButton { background-color: @accent; color: white; border-radius: 6px; font-weight: 600; font-size: 11pt; }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_ok.clicked.connect(self.save_announcement)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _wire_ui_signals(self):
        self.cmb_priority.currentIndexChanged.connect(self._on_ui_widget_changed)

    def delete_announcement(self):
        dialog = SimpleConfirmDialog(self, "Silme Onayı", "Bu duyuruyu silmek istediğinize emin misiniz")
        if dialog.exec():
            try:
                if self.db.soft_delete_record("announcements", "id", self.announcement_data[5]):
                    show_success(self, "Duyuru başarıyla silindi!")
                else:
                    show_error(self, "Silme hatası oluştu.")
                self.accept()
            except Exception as e:
                show_error(self, f"Silme hatası: {str(e)}")

    def save_announcement(self):
        title = self.inp_title.text().strip()
        content = self.txt_content.toPlainText().strip()
        priority = self.cmb_priority.currentText()
        
        if not title or not content:
            show_warning(self, "Başlık ve içerik alanları zorunludur.")
            return

        try:
            self.db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='announcements'")
            if not self.db.cursor.fetchone():
                self.db.cursor.execute("CREATE TABLE announcements (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, priority TEXT, title TEXT, content TEXT, author TEXT, is_deleted INTEGER DEFAULT 0)")
                self.db.conn.commit()
            if self.announcement_data:
                # Update
                self.db.cursor.execute(
                    """
                    UPDATE announcements
                    SET title=?, content=?, priority=?
                    WHERE id=?
                    """,
                    (title, content, priority, self.announcement_data[5]),
                )
            else:
                # Insert
                self.db.cursor.execute("""
                    INSERT INTO announcements (date, priority, title, content, author)
                    VALUES (?, ?, ?, ?, ?)
                """, (QDate.currentDate().toString("dd.MM.yyyy"), priority, title, content, "Yönetici"))
            
            self.db.conn.commit()
            show_success(self, "Duyuru kaydedildi.")
            self.accept()
        except Exception as e:
            show_error(self, str(e))

class AnnouncementsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        self.layout.setSpacing(20)
        
        self.init_ui()
        self.load_announcements()

    def _is_classic_appearance(self):
        app = QApplication.instance()
        if app and app.property("appearanceMode") == "classic":
            return True
        try:
            return AppearanceModeManager.is_classic(self.db)
        except Exception:
            return False

    def _classic_table_qss(self):
        return """
            QTableWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F3F6FA;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                gridline-color: #C9CDD3;
                color: #111827;
                selection-background-color: #DCEBFF;
                selection-color: #111827;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border: none;
                color: #111827;
            }
            QTableWidget::item:!selected:hover {
                background-color: #EEF2F7;
                color: #111827;
            }
            QTableWidget::item:selected,
            QTableWidget::item:selected:active {
                background-color: #DCEBFF;
                color: #111827;
                font-weight: 600;
            }
            QTableWidget::item:alternate {
                background-color: #F3F6FA;
            }
            QHeaderView::section {
                background-color: #E5E7EB;
                color: #111827;
                padding: 8px 10px;
                font-weight: 700;
                font-size: 10pt;
                border: 1px solid #B8C0CC;
                border-left: none;
                border-top: none;
                border-radius: 0px;
            }
            QHeaderView::section:hover {
                background-color: #DCEBFF;
                color: #111827;
            }
        """

    def _modern_table_qss(self):
        return theme_qss("""
            QTableWidget {
                background-color: @surface;
                border: 2px solid @border;
                border-radius: 8px;
                gridline-color: @border;
                color: @text;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border: none;
                color: @text;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @accent;
                font-weight: 600;
            }
            QTableWidget::item:hover {
                background-color: @surface_alt;
            }
            QHeaderView::section {
                background-color: @text;
                color: white;
                padding: 12px;
                font-weight: 600;
                font-size: 11pt;
                border: none;
                border-right: 1px solid @text;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item:alternate {
                background-color: @surface_alt;
            }
        """)

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        self.setProperty("skipThemeTransform", False)
        if not hasattr(self, "table"):
            return
        self.table.setProperty("skipThemeTransform", False)
        self.table.horizontalHeader().setProperty("skipThemeTransform", False)
        self.table.verticalHeader().setProperty("skipThemeTransform", False)
        self.table.setStyleSheet(self._classic_table_qss() if classic else self._modern_table_qss())
        if classic:
            self.table.horizontalHeader().setStyleSheet(
                "QHeaderView::section { background-color: #E5E7EB; color: #111827; "
                "padding: 8px 10px; font-weight: 700; border: 1px solid #B8C0CC; }"
            )
        else:
            self.table.horizontalHeader().setStyleSheet("")

    def init_ui(self):
        # Header
        header = QHBoxLayout()
        title = QLabel("📢 Duyurular ve Bildirimler")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        header.addWidget(title)
        
        btn_add = QPushButton("+ Yeni Duyuru")
        btn_add.setFixedSize(150, 45)
        btn_add.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @accent; 
                color: white; 
                border-radius: 6px; 
                font-weight: 600;
                font-size: 11pt;
            }
            QPushButton:hover { 
                background-color: @accent_hover; 
            }
        """))
        btn_add.clicked.connect(self.add_announcement)
        
        btn_refresh = QPushButton("🔄 Yenile")
        btn_refresh.setFixedSize(120, 45)
        btn_refresh.setStyleSheet(theme_qss("""
            QPushButton { 
                background-color: @success; 
                color: white; 
                border-radius: 6px; 
                font-weight: 600;
                font-size: 11pt;
            }
            QPushButton:hover { 
                background-color: @success; 
            }
        """))
        btn_refresh.clicked.connect(self.load_announcements)
        
        header.addStretch()
        header.addWidget(btn_refresh)
        header.addWidget(btn_add)
        
        self.layout.addLayout(header)
        
        # Responsive Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tarih", "Öncelik", "Başlık", "İçerik", "Yayınlayan"])
        
        # Responsive column sizing
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Tarih
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Öncelik
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Başlık
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # İçerik - en geniş
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Yayınlayan
        
        # Set column widths
        self.table.setColumnWidth(2, 250)  # Başlık için sabit genişlik
        
        # Table settings
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        
        # Enable word wrap for content column
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        
        self.apply_theme_styles()
        
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        
        # Add context menu support
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        
        self.table.itemDoubleClicked.connect(self.on_table_double_clicked)
        self.layout.addWidget(self.table)

    def _ensure_announcements_table(self):
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                priority TEXT,
                title TEXT,
                content TEXT,
                author TEXT,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        self.db.conn.commit()

    def load_announcements(self):
        """Duyuruları yükle"""
        self.table.setRowCount(0)
        
        try:
            self._ensure_announcements_table()
            query = "SELECT date, priority, title, content, author, id FROM announcements"
            try:
                self.db.cursor.execute("PRAGMA table_info(announcements)")
                cols = [col[1] for col in self.db.cursor.fetchall()]
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                if deleted_col:
                    query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
            except Exception:
                pass
            query += " ORDER BY id DESC"
            self.db.cursor.execute(query)
            announcements = self.db.cursor.fetchall()
        except Exception as e:
            logger.error("Announcement load error: %s", e)
            announcements = []
        
        # If no data, use mock data
        if not announcements or len(announcements) == 0:
            announcements = [
                ("04.01.2026", "Yüksek", "⚡ Sistem Bakımı", 
                 "Bu hafta sonu (06-07 Ocak) sunucu bakımı yapılacaktır. Sistemde geçici aksaklıklar yaşanabilir.", 
                 "Sistem Yöneticisi", None),
                ("01.01.2026", "Normal", "🎉 Yeni Yıl Kutlaması", 
                 "Tüm çalışanlarımızın ve müşterilerimizin yeni yılı kutlu olsun! Sağlık, mutluluk ve başarı dolu bir yıl dileriz.", 
                 "İnsan Kaynakları", None),
                ("03.01.2026", "Yüksek", "🚀 v2.0 Yayında", 
                 "AYEC Pro v2.0 sürümü aktif edilmiştir. Yeni özellikler ve iyileştirmeler için dokümantasyonu inceleyiniz.", 
                 "Geliştirme Ekibi", None),
                ("02.01.2026", "Normal", "📊 Aylık Rapor Hatırlatması", 
                 "Ocak ayı performans raporları 10 Ocak'a kadar hazırlanmalıdır. Lütfen verilerinizi sisteme giriniz.", 
                 "Muhasebe", None),
                ("31.12.2025", "Düşük", "📅 Tatil Takvimi", 
                 "2026 yılı resmi tatil takvimi paylaşıldı. Detaylar için şirket portalını ziyaret ediniz.", 
                 "İdari İşler", None)
            ]
        
        # Populate table
        for row_data in announcements:
            row_num = self.table.rowCount()
            self.table.insertRow(row_num)
            
            date, priority, title, content, author, ann_id = row_data
            
            # Tarih
            date_item = QTableWidgetItem(date)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item.setFont(QFont("Segoe UI", 10))
            date_item.setData(Qt.ItemDataRole.UserRole, ann_id) # Store ID
            self.table.setItem(row_num, 0, date_item)
            
            # Öncelik badge
            priority_item = QTableWidgetItem(priority)
            priority_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            priority_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            
            if priority == "Yüksek" or priority == "high":
                priority_item.setForeground(QColor("#B91C1C" if self._is_classic_appearance() else tc("danger")))
                priority_item.setBackground(QColor("#FEE2E2") if self._is_classic_appearance() else qc("danger_bg"))
            elif priority == "Normal" or priority == "normal":
                priority_item.setForeground(QColor("#1D4ED8" if self._is_classic_appearance() else tc("accent")))
                priority_item.setBackground(QColor("#DBEAFE") if self._is_classic_appearance() else qc("selection_bg"))
            else:  # Düşük
                priority_item.setForeground(QColor("#047857" if self._is_classic_appearance() else tc("success")))
                priority_item.setBackground(QColor("#D1FAE5") if self._is_classic_appearance() else qc("success_bg"))
            
            self.table.setItem(row_num, 1, priority_item)
            
            # Başlık
            title_item = QTableWidgetItem(title)
            title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            title_item.setForeground(QColor("#111827" if self._is_classic_appearance() else tc("text")))
            self.table.setItem(row_num, 2, title_item)
            
            # İçerik (word wrap enabled)
            content_item = QTableWidgetItem(content)
            content_item.setFont(QFont("Segoe UI", 10))
            content_item.setForeground(QColor("#374151") if self._is_classic_appearance() else qc("text_muted"))
            content_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            self.table.setItem(row_num, 3, content_item)
            
            # Yayınlayan
            author_item = QTableWidgetItem(author or "Sistem")
            author_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            author_item.setFont(QFont("Segoe UI", 9))
            author_item.setForeground(QColor("#374151" if self._is_classic_appearance() else tc("text_muted")))
            self.table.setItem(row_num, 4, author_item)
        
        self.table.resizeRowsToContents()

    def add_announcement(self):
        """Yeni duyuru ekle"""
        dialog = AnnouncementDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_announcements()
            show_success(self.window(), "İşlem başarıyla tamamlandı!")

    def show_context_menu(self, position):
        """Right-click context menu for announcements"""
        if not is_context_menu_enabled(self.db, page_id=120):
            return
        item = self.table.itemAt(position)
        if not item:
            return
            
        row = item.row()
        ann_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not ann_id:
            return
        
        menu = QAction(self)
        menu.setParent(self)
        
        # Create menu using QMenu from QtWidgets
        from PyQt6.QtWidgets import QMenu
        context_menu = QMenu(self)
        
        # Edit action
        edit_action = context_menu.addAction("✏ Düzenle")
        edit_action.triggered.connect(lambda: self.on_table_double_clicked(item))
        
        # Delete action
        delete_action = context_menu.addAction("🗑 Sil")
        delete_action.triggered.connect(lambda: self.delete_announcement_from_table(row, ann_id))
        
        # Show menu at cursor
        context_menu.exec(self.table.viewport().mapToGlobal(position))
    
    def delete_announcement_from_table(self, row, ann_id):
        """Delete announcement from context menu"""
        dialog = SimpleConfirmDialog(self, "Silme Onayı", "Bu duyuruyu silmek istediğinize emin misiniz")
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if self.db.soft_delete_record("announcements", "id", ann_id):
                    show_success(self, "Duyuru başarıyla silindi!")
                    self.load_announcements()
                else:
                    show_error(self, "Silme hatası oluştu.")
            except Exception as e:
                show_error(self, f"Silme hatası: {str(e)}")

    def on_table_double_clicked(self, item):
        """Tabloya çift tıklandığında düzenleme aç"""
        try:
            row = item.row()
            ann_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if not ann_id: return
            
            date = self.table.item(row, 0).text()
            priority = self.table.item(row, 1).text()
            title = self.table.item(row, 2).text()
            content = self.table.item(row, 3).text()
            author = self.table.item(row, 4).text()
            
            data = (date, priority, title, content, author, ann_id)
            
            dialog = AnnouncementDialog(self.db, self, data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.load_announcements()
                show_info(self.window(), "Duyuru güncellendi/silindi.")
                
        except Exception as e:
            logger.error("Announcement edit error: %s", e)
