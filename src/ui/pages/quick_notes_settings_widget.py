# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QComboBox, QLineEdit, QFormLayout, QMessageBox, QFrame, QMenu,
                             QGraphicsDropShadowEffect, QAbstractItemView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from src.utils.message_helper import show_success, show_error, show_question
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import theme_qss
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.widgets.modern_dialog import ModernDialog
import logging

logger = logging.getLogger("AYECProLogger")


class QuickNotesSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """
    Hızlı Notlar Ayar Sayfası (Modern UI)
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self.load_notes()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- HEADER ---
        header = QHBoxLayout()
        
        title_box = QVBoxLayout()
        lbl_title = QLabel("Hızlı Notlar & Makrolar")
        lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text;"))
        
        lbl_desc = QLabel("Teknisyen paneli ve süreçler için hazır metin şablonlarını yönetin.")
        lbl_desc.setFont(QFont("Segoe UI", 11))
        lbl_desc.setStyleSheet(theme_qss("color: @text_muted;"))
        
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_desc)
        
        header.addLayout(title_box)
        header.addStretch()
        
        # Action Buttons
        self.btn_add = QPushButton(" + Yeni Not Ekle")
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setFixedSize(160, 45)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6; 
                color: white; 
                font-family: 'Segoe UI'; font-weight: 600; font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #2563eb; }
            QPushButton:pressed { background-color: #1d4ed8; }
        """)
        self.btn_add.clicked.connect(self.open_add_dialog)
        
        self.btn_refresh = QPushButton(" Yenile")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setFixedSize(100, 45)
        self.btn_refresh.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface; 
                color: @text; 
                font-family: 'Segoe UI'; font-weight: 600; font-size: 14px;
                border: 1px solid @border;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: @hover; border-color: @primary; }
        """))
        self.btn_refresh.clicked.connect(self.load_notes)
        
        header.addWidget(self.btn_refresh)
        header.addWidget(self.btn_add)
        
        layout.addLayout(header)
        
        # --- FILTERS & SEARCH ---
        filter_frame = QFrame()
        filter_frame.setStyleSheet(theme_qss("QFrame { background-color: @surface; border-radius: 12px; border: 1px solid @border; }"))
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)
        
        # Category Filter
        self.combo_filter = QComboBox()
        self.combo_filter.setFixedWidth(200)
        self.combo_filter.addItems(["Tüm Kategoriler", "Arıza Notu", "İşlem Detayı", "Gizli Not"])
        self.combo_filter.setStyleSheet("""
            QComboBox {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Segoe UI'; font-size: 13px; color: @text;
            }
            QComboBox:focus { border-color: @accent; }
        """)
        self.combo_filter.currentIndexChanged.connect(self.load_notes)
        
        # Search Box
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Notlarda ara...")
        self.inp_search.setStyleSheet("""
            QLineEdit {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Segoe UI'; font-size: 13px; color: @text;
            }
            QLineEdit:focus { border-color: @accent; }
        """)
        self.inp_search.textChanged.connect(self.load_notes)
        
        filter_layout.addWidget(QLabel("Filtrele:", styleSheet=theme_qss("font-weight:bold; color:@text_muted;")))
        filter_layout.addWidget(self.combo_filter)
        filter_layout.addWidget(QLabel("Ara:", styleSheet=theme_qss("font-weight:bold; color:@text_muted; margin-left: 20px;")))
        filter_layout.addWidget(self.inp_search)
        
        layout.addWidget(filter_frame)

        # --- TABLE CARD ---
        table_frame = QFrame()
        table_frame.setStyleSheet(theme_qss("QFrame { background-color: @surface; border-radius: 12px; border: 1px solid @border; }"))
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Kategori", "Not İçeriği", "Sıra", "Durum"])
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: transparent;
                gridline-color: @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
            QTableWidget::item {
                padding-top: 15px;
                padding-bottom: 15px;
                padding-left: 10px;
                padding-right: 10px;
                border-bottom: 1px solid @border;
                font-family: 'Segoe UI'; font-size: 13px; color: @text;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                padding: 15px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: 600;
                color: @text_muted;
                font-family: 'Segoe UI';
                text-transform: uppercase;
                font-size: 12px;
            }
        """)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        # Column 3 is Order
        self.table.setColumnWidth(3, 80)
        # Column 4 is Status - Set fixed width to ensure visibility
        self.table.setColumnWidth(4, 150)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.doubleClicked.connect(self.open_edit_dialog)
        
        # Context Menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_frame)



    def load_notes(self):
        self.table.setRowCount(0)
        
        cat_filter = self.combo_filter.currentText()
        if cat_filter == "Tüm Kategoriler":
            cat_filter = None
        
        search_txt = self.inp_search.text().lower().strip()
        
        try:
            # Get all and filter manually for search, or use DB filtering
            # DB filtering for category is supported
            notes = self.db.get_fast_notes(cat_filter)
        except Exception as e:
            logger.error("Quick notes load error: %s", e)
            notes = []
            
        for note in notes:
            # (id, category, label, is_active, display_order)
            n_id, n_cat, n_label, n_active, n_order = note
            
            # Search Filter
            if search_txt:
                if search_txt not in str(n_label).lower() and search_txt not in str(n_cat).lower():
                    continue
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(n_id)))
            
            # Category Badge
            cat_item = QTableWidgetItem(n_cat)
            cat_item.setForeground(QColor("#3b82f6")) # Blue
            cat_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            self.table.setItem(row, 1, cat_item)
            
            # Label
            self.table.setItem(row, 2, QTableWidgetItem(n_label))
            
            # Order
            self.table.setItem(row, 3, QTableWidgetItem(str(n_order)))
            
            # Active Status (Animated Toggle)
            # Create a dummy item first to ensure cell existence
            self.table.setItem(row, 4, QTableWidgetItem(""))
            
            container = QWidget()
            clayout = QHBoxLayout(container)
            clayout.setContentsMargins(5, 5, 5, 5) # Small buffer
            clayout.setSpacing(10)
            clayout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            toggle = AnimatedToggle()
            toggle.setFixedSize(50, 26)
            toggle.setChecked(bool(n_active))
            
            lbl_status = QLabel("Aktif" if n_active else "Pasif")
            lbl_status.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl_status.setFixedWidth(40)
            
            if n_active:
                lbl_status.setStyleSheet("color: #10b981; border: none;") # Green, no background
            else:
                lbl_status.setStyleSheet("color: #ef4444; border: none;") # Red, no background
            
            toggle.stateChanged.connect(lambda state, nid=n_id, lbl=lbl_status: self.on_toggle_change(nid, state, lbl))
            
            clayout.addWidget(toggle)
            clayout.addWidget(lbl_status)
            
            container.setLayout(clayout)
            
            # Set the widget and force row height
            self.table.setCellWidget(row, 4, container)
            self.table.setRowHeight(row, 60)
            
            # Store ID
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, n_id)

    def on_toggle_change(self, note_id, state, lbl_status):
        is_active = 1 if state == Qt.CheckState.Checked else 0
        
        # Update Label UI immediately
        if is_active:
            lbl_status.setText("Aktif")
            lbl_status.setStyleSheet("color: #10b981; margin-left: 8px;")
        else:
            lbl_status.setText("Pasif")
            lbl_status.setStyleSheet("color: #ef4444; margin-left: 8px;")
            
        # Update DB
        try:
            self.db.cursor.execute("UPDATE fast_notes SET is_active=? WHERE id=?", (is_active, note_id))
            self.db.conn.commit()
        except Exception as e:
            logger.error("Quick notes toggle update error: %s", e)

    def open_add_dialog(self):
        dlg = QuickNoteDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self.db.add_fast_note(data['category'], data['label'], data['is_active'], data['order'])
                self.load_notes()
                show_success(self, "Başarılı", "Not eklendi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

    def open_edit_dialog(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        n_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        # Fetch remaining data from DB to be safe or use what we have
        # Since table doesn't hold all data in items anymore (widget used), fetch from DB is cleaner
        # But we can rely on what we see in table except active status is in widget
        
        n_cat = self.table.item(row, 1).text()
        n_label = self.table.item(row, 2).text()
        n_order = int(self.table.item(row, 3).text())
        
        # Get active status from toggle widget
        container = self.table.cellWidget(row, 4)
        toggle = container.findChild(AnimatedToggle)
        n_active = 1 if toggle.isChecked() else 0
        
        note_data = (n_id, n_cat, n_label, n_active, n_order)
        
        dlg = QuickNoteDialog(self, note_data)
        if dlg.exec():
            data = dlg.get_data()
            try:
                self.db.update_fast_note(n_id, data['label'], data['is_active'], data['category'], data['order'])
                self.load_notes()
                show_success(self, "Başarılı", "Not güncellendi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

    def open_context_menu(self, pos):
        if not is_context_menu_enabled(self.db):
            return
        menu = QMenu()
        menu.addAction("✏️ Düzenle", self.open_edit_dialog)
        menu.addAction("🗑️ Sil", self.delete_note)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_note(self):
        row = self.table.currentRow()
        if row < 0:
            return
        
        n_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        confirm = show_question(self, "Onay", "Bu notu silmek istediğinize emin misiniz")
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_fast_note(n_id)
                self.load_notes()
                show_success(self, "Başarılı", "Not silindi.")
            except Exception as e:
                show_error(self, "Hata", str(e))

class QuickNoteDialog(ModernDialog):
    def __init__(self, parent=None, note_data=None):
        super().__init__(parent)
        self.note_data = note_data
        
        # Frameless Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # self.setAttribute(Qt.WA_TranslucentBackground) # Removed to fix transparency issue
        
        self.setup_ui()
        if note_data:
            self.populate()

    def setup_ui(self):
        self.setWindowTitle("Hızlı Not Detayı")
        self.setFixedWidth(500)
        
        # Add shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
        
        # Modern Frameless Styling with Border and Shadow-like appearance
        self.setStyleSheet(theme_qss("""
            QDialog { 
                background-color: @surface; 
                border-radius: 16px;
                border: 2px solid @border;
            }
            QLabel { font-family: 'Segoe UI'; font-size: 14px; color: @text; font-weight: 500; border: none; background: transparent; }
            QLineEdit, QComboBox {
                padding: 12px; border: 1px solid @border; border-radius: 8px;
                font-family: 'Segoe UI'; font-size: 14px;
                background-color: @input_bg;
                color: @text;
            }
            QLineEdit:focus, QComboBox:focus { border-color: @primary; background-color: @surface; }
            QComboBox::drop-down { border: none; }
            QCheckBox { background: transparent; }
        """))
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0) # Zero margins for the outer layout, content via inner frame or margin
        
        # Create a container frame to hold content (for clean margins inside the border)
        content_frame = QFrame()
        content_frame.setStyleSheet("background: transparent; border: none;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(35, 35, 35, 35)
        content_layout.setSpacing(25)
        
        # Title
        title = QLabel("📝 Not Düzenle / Ekle")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #0f172a; border: none; margin-bottom: 10px;")
        content_layout.addWidget(title)
        
        form = QFormLayout()
        form.setVerticalSpacing(20)
        form.setHorizontalSpacing(15)
        
        self.cmb_cat = QComboBox()
        self.cmb_cat.addItems(["Arıza Notu", "İşlem Detayı", "Gizli Not"])
        self.cmb_cat.setEditable(True)
        self.cmb_cat.setFixedHeight(45)
        form.addRow("Kategori:", self.cmb_cat)
        
        self.inp_label = QLineEdit()
        self.inp_label.setPlaceholderText("Görünecek metin...")
        self.inp_label.setFixedHeight(45)
        form.addRow("İçerik:", self.inp_label)
        
        self.inp_order = QLineEdit("0")
        self.inp_order.setFixedHeight(45)
        form.addRow("Sıralama:", self.inp_order)
        
        # Animated Toggle for Active Status
        self.toggle_active = AnimatedToggle()
        self.toggle_active.setChecked(True)
        self.toggle_active.setFixedSize(50, 26)
        
        lbl_active = QLabel("Aktif Durum:")
        lbl_active.setStyleSheet("margin-top: 5px; border: none;")
        form.addRow(lbl_active, self.toggle_active)
        
        content_layout.addLayout(form)
        content_layout.addStretch()
        
        # Buttons
        btns = QHBoxLayout()
        btns.setSpacing(12)
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(120, 50)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface; border: 2px solid @border; border-radius: 10px; 
                color: @text; font-weight: 600; font-family: 'Segoe UI'; font-size: 14px;
            }
            QPushButton:hover { background: @hover; color: @text; border-color: @primary; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Kaydet")
        btn_save.setFixedSize(120, 50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet("""
            QPushButton {
                background: #0f172a; border: none; border-radius: 10px; 
                color: white; font-weight: 600; font-family: 'Segoe UI'; font-size: 14px;
            }
            QPushButton:hover { background: #1e293b; }
            QPushButton:pressed { background: #020617; }
        """)
        btn_save.clicked.connect(self.accept)
        
        btns.addStretch()
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        
        content_layout.addLayout(btns)
        
        layout.addWidget(content_frame)

    # Allow dragging the frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def populate(self):
        # (id, cat, label, active, order)
        idx = self.cmb_cat.findText(self.note_data[1])
        if idx >= 0:
            self.cmb_cat.setCurrentIndex(idx)
        else:
            self.cmb_cat.setCurrentText(self.note_data[1])
        
        self.inp_label.setText(self.note_data[2])
        self.toggle_active.setChecked(bool(self.note_data[3]))
        self.inp_order.setText(str(self.note_data[4]))

    def get_data(self):
        return {
            'category': self.cmb_cat.currentText(),
            'label': self.inp_label.text(),
            'is_active': 1 if self.toggle_active.isChecked() else 0,
            'order': int(self.inp_order.text() or 0)
        }
