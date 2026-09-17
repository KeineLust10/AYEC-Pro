# -*- coding: utf-8 -*-

"""
Advanced Loan Wizard - Step 3: Document Upload
Kredi evrakları ve notlar adımı
"""
import os
from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QTextEdit, QFrame, 
                             QHBoxLayout, QPushButton, QFileDialog, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QDesktopServices
from src.utils.theme_colors import theme_qss
from PyQt6.QtCore import QUrl
from typing import Dict, Tuple, List

from src.ui.widgets.wizard_step_base import WizardStepBase
from src.ui.widgets.modern_dialog import NoWheelScrollArea

class FileItemWidget(QFrame):
    """Yüklenen dosya için liste öğesi"""
    removed = pyqtSignal(str)
    
    def __init__(self, file_path, file_type_label="Belge"):
        super().__init__()
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.setup_ui(file_type_label)
        
    def setup_ui(self, type_label):
        self.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 5px;
            }
            QFrame:hover {
                background-color: @surface_alt;
            }
        """))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Icon based on extension
        ext = os.path.splitext(self.file_name)[1].lower()
        icon_text = "📄"
        if ext == '.pdf': icon_text = "📕"
        elif ext in ['.jpg', '.jpeg', '.png']: icon_text = "🖼️"
        elif ext in ['.doc', '.docx']: icon_text = "📘"
        elif ext in ['.xls', '.xlsx']: icon_text = "📗"
        
        lbl_icon = QLabel(icon_text)
        lbl_icon.setFont(QFont("Segoe UI", 12))
        layout.addWidget(lbl_icon)
        
        # Name and type
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        lbl_name = QLabel(self.file_name)
        lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_name.setStyleSheet(theme_qss("color: @text;"))
        
        lbl_type = QLabel(type_label)
        lbl_type.setFont(QFont("Segoe UI", 8))
        lbl_type.setStyleSheet(theme_qss("color: @text_muted;"))
        
        info_layout.addWidget(lbl_name)
        info_layout.addWidget(lbl_type)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Actions
        btn_open = QPushButton("👁️")
        btn_open.setToolTip("Aç")
        btn_open.setFixedSize(28, 28)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setStyleSheet(theme_qss("background: transparent; border: none; font-size: 14px;"))
        btn_open.clicked.connect(self._open_file)
        
        btn_remove = QPushButton("❌")
        btn_remove.setToolTip("Kaldır")
        btn_remove.setFixedSize(28, 28)
        btn_remove.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_remove.setStyleSheet(theme_qss("background: transparent; border: none; font-size: 12px; color: @danger;"))
        btn_remove.clicked.connect(lambda: self.removed.emit(self.file_path))
        
        layout.addWidget(btn_open)
        layout.addWidget(btn_remove)

    def _open_file(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.file_path))

class DropZoneWidget(QFrame):
    """Dosya sürükle bırak alanı"""
    filesDropped = pyqtSignal(list)
    
    def __init__(self, title="Evrak Yükle", subtitle="Sürükleyip bırakın veya seçin"):
        super().__init__()
        self.setAcceptDrops(True)
        self.setup_ui(title, subtitle)
        
    def setup_ui(self, title, subtitle):
        self.setMinimumHeight(120)
        self.setObjectName("DropZone")
        self.setStyleSheet(theme_qss("""
            QFrame#DropZone {
                border: 2px dashed @border;
                border-radius: 12px;
                background-color: @surface_alt;
            }
            QFrame#DropZone:hover {
                background-color: @surface_alt;
                border-color: @accent;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel("📥")
        lbl_icon.setFont(QFont("Segoe UI", 24))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text;"))
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_subtitle = QLabel(subtitle)
        lbl_subtitle.setFont(QFont("Segoe UI", 9))
        lbl_subtitle.setStyleSheet(theme_qss("color: @text_muted;"))
        lbl_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_subtitle)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet(theme_qss(self.styleSheet().replace("@border", "@accent").replace("@surface_alt", "@selection_bg")))
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet(theme_qss(self.styleSheet().replace("@accent", "@border").replace("@selection_bg", "@surface_alt")))

    def dropEvent(self, event):
        self.setStyleSheet(theme_qss(self.styleSheet().replace("@accent", "@border").replace("@selection_bg", "@surface_alt")))
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.filesDropped.emit(files)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            files, _ = QFileDialog.getOpenFileNames(self, "Dosya Seç", "", "Tüm Dosyalar (*.*);;PDF Belgeleri (*.pdf);;Resimler (*.png *.jpg *.jpeg)")
            if files:
                self.filesDropped.emit(files)

class Step3DocumentUpload(WizardStepBase):
    """Adım 3: Dosya ve Evrak Yükleme"""
    
    def __init__(self, parent=None):
        self.attachments = [] # List of tuples (path, type)
        super().__init__(parent)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("📂 Dosya ve Evrak Yükleme")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Kredi sözleşmesi, ödeme planı veya diğer ilgili evrakları sisteme yükleyebilirsiniz.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        # Left: Upload areas
        upload_layout = QVBoxLayout()
        
        # Contract DropZone
        self.drop_contract = DropZoneWidget("📄 Kredi Sözleşmesi", "PDF veya Görsel sürükle bırak")
        self.drop_contract.filesDropped.connect(lambda files: self._add_files(files, "Sözleşme"))
        upload_layout.addWidget(self.drop_contract)
        
        # Payment Plan DropZone
        self.drop_plan = DropZoneWidget("📊 Ödeme Planı", "Bankadan alınan orijinal planı yükle")
        self.drop_plan.filesDropped.connect(lambda files: self._add_files(files, "Ödeme Planı"))
        upload_layout.addWidget(self.drop_plan)
        
        # Notes
        lbl_notes = QLabel("📝 Notlar")
        lbl_notes.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_notes.setStyleSheet(theme_qss("color: @text;"))
        upload_layout.addWidget(lbl_notes)
        
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Kredi ile ilgili özel şartlar, hatırlatmalar veya banka yetkilisi notları...")
        self.txt_notes.setFixedHeight(72)
        self.txt_notes.setStyleSheet(theme_qss("""
            QTextEdit {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 10px;
                background-color: @surface;
            }
            QTextEdit:focus {
                border: 2px solid @accent;
            }
        """))
        upload_layout.addWidget(self.txt_notes)
        
        content_layout.addLayout(upload_layout, stretch=1)
        
        # Right: File List
        list_layout = QVBoxLayout()
        
        list_title = QLabel("📎 Yüklenen Dosyalar")
        list_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        list_title.setStyleSheet(theme_qss("color: @text;"))
        list_layout.addWidget(list_title)
        
        self.scroll_files = NoWheelScrollArea()
        self.scroll_files.setWidgetResizable(True)
        self.scroll_files.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_files.setStyleSheet(theme_qss("background: transparent;"))
        
        self.file_container = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_container)
        self.file_list_layout.setContentsMargins(0, 0, 0, 0)
        self.file_list_layout.setSpacing(8)
        self.file_list_layout.addStretch()
        
        self.scroll_files.setWidget(self.file_container)
        list_layout.addWidget(self.scroll_files)
        
        content_layout.addLayout(list_layout, stretch=1)
        
        layout.addLayout(content_layout)
        
    def _add_files(self, files, file_type):
        for path in files:
            # Check if already added
            if any(a[0] == path for a in self.attachments):
                continue
                
            self.attachments.append((path, file_type))
            
            # Create widget
            widget = FileItemWidget(path, file_type)
            widget.removed.connect(self._remove_file)
            
            # Add to layout (before stretch)
            self.file_list_layout.insertWidget(self.file_list_layout.count() - 1, widget)
            
    def _remove_file(self, path):
        # Remove from data
        self.attachments = [a for a in self.attachments if a[0] != path]
        
        # Remove from UI
        for i in range(self.file_list_layout.count()):
            item = self.file_list_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), FileItemWidget):
                if item.widget().file_path == path:
                    item.widget().deleteLater()
                    break

    def validate(self) -> Tuple[bool, str]:
        """Adım validasyonu - Dosya yüklemek opsiyonel olabilir"""
        return True, ""
    
    def get_data(self) -> Dict:
        """Return step data"""
        return {
            'attachments': self.attachments,
            'notes': self.txt_notes.toPlainText().strip()
        }
    
    def set_data(self, data: Dict):
        """Load data into step"""
        if 'attachments' in data:
            # Clear existing
            for i in reversed(range(self.file_list_layout.count())):
                item = self.file_list_layout.itemAt(i)
                if item and item.widget():
                    item.widget().deleteLater()
            self.attachments = []
            
            # Re-add
            for path, ftype in data['attachments']:
                self._add_files([path], ftype)
        
        if 'notes' in data:
            self.txt_notes.setPlainText(data['notes'])

