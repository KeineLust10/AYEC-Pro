# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QComboBox, QDateEdit, QDoubleSpinBox, QFrame, QGraphicsDropShadowEffect,
                                 QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget)
from PyQt6.QtCore import Qt, QDate
from src.utils.theme_colors import theme_qss
from PyQt6.QtGui import QAction, QColor, QFont
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog


class TransactionAddDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, personnel_dict={}):
        super().__init__(title="Yeni Maas Prim Ekle", parent=parent, width=450, height=700)
        self.db = db
        self.personnel_dict = personnel_dict
        self.data = None
        
        self.set_footer_visible(False)
        
        self.setup_ui()

        self._wire_ui_signals()
    def setup_ui(self):
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 80))
        
        self.container = QFrame()
        self.container.setGraphicsEffect(shadow)
        self.container.setStyleSheet(theme_qss("QFrame { background-color: @surface; border-radius: 20px; border: 1px solid @border; }"))
        
        main_layout = self.content_layout
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(theme_qss("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 @success, stop:1 @success); border-top-left-radius: 20px; border-top-right-radius: 20px;"))
        hl = QHBoxLayout(header)
        hl.setContentsMargins(25, 0, 25, 0)
        
        icon_lbl = QLabel("💰")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 24))
        icon_lbl.setStyleSheet(theme_qss("border: none; background: transparent;"))
        
        t = QLabel("Yeni Maaş/Prim Ekle")
        t.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        t.setStyleSheet(theme_qss("color: @selection_text; border: none; background: transparent; margin-left: 10px;"))
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(35, 35)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet(theme_qss("""
            QPushButton { background: @surface_alt; color: @text_muted; border-radius: 17px; font-weight: bold; border: none; font-size: 16px; }
            QPushButton:hover { background: @danger; color: @selection_text; }
        """))
        
        hl.addWidget(icon_lbl)
        hl.addWidget(t)
        hl.addStretch()
        hl.addWidget(btn_close)
        layout.addWidget(header)
        
        # Form
        form_widget = QWidget()
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(35, 35, 35, 35)
        form.setSpacing(25)
        
        style = """
            QLabel { font-weight: 700; color: @text_muted; font-size: 13px; margin-bottom: 5px; }
            QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { 
                padding: 12px; border: 2px solid @border; border-radius: 10px; font-size: 14px; color: @text; bg-color: @surface_alt;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus { 
                border: 2px solid @warning; background-color: @warning_bg; 
            }
            QComboBox::drop-down { border: none; width: 30px; }
        """
        form_widget.setStyleSheet(theme_qss(style))
        
        # Fields
        
        # Personel
        lbl_p = QLabel("PERSONEL SEÇİMİ")
        form.addWidget(lbl_p)
        self.cmb_p = QComboBox()
        self.cmb_p.setFixedHeight(50)
        for name, pid in self.personnel_dict.items():
            self.cmb_p.addItem(name, pid)
        form.addWidget(self.cmb_p)
        
        # Tip
        lbl_t = QLabel("İŞLEM TİPİ")
        form.addWidget(lbl_t)
        self.cmb_t = QComboBox()
        self.cmb_t.setFixedHeight(50)
        self.cmb_t.addItems(["Maaş", "Prim", "Avans", "Yol/Yemek", "Kesinti"])
        form.addWidget(self.cmb_t)
        
        # Tutar
        lbl_a = QLabel("TUTAR (TL)")
        form.addWidget(lbl_a)
        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0.00")
        self.inp_amount.setFixedHeight(50)
        form.addWidget(self.inp_amount)
        
        # Tarih
        lbl_d = QLabel("İŞLEM TARİHİ")
        form.addWidget(lbl_d)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setFixedHeight(50)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        form.addWidget(self.date_edit)
        
        # Açıklama
        lbl_desc = QLabel("AÇIKLAMA / NOT")
        form.addWidget(lbl_desc)
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("İsteğe bağlı açıklama...")
        self.inp_desc.setFixedHeight(50)
        form.addWidget(self.inp_desc)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        # Footer
        footer = QFrame()
        footer.setFixedHeight(90)
        footer.setStyleSheet(theme_qss("background: @surface_alt; border-bottom-left-radius: 20px; border-bottom-right-radius: 20px; border-top: 1px solid @border;"))
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(30, 0, 30, 0)
        fl.setSpacing(15)
        
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(50)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; border-radius: 12px; font-weight: bold; font-size: 14px; min-width: 100px; }
            QPushButton:hover { background: @surface_alt; color: @text; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("💾 İşlemi Kaydet")
        btn_save.setFixedHeight(50)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton { background-color: @success; color: @selection_text; border-radius: 12px; font-weight: bold; font-size: 14px; border: none; padding-left: 20px; padding-right: 20px; }
            QPushButton:hover { opacity: 0.8; }
        """))
        btn_save.clicked.connect(self.save)
        
        fl.addWidget(btn_cancel)
        fl.addStretch()
        fl.addWidget(btn_save)
        layout.addWidget(footer)
        
    def _wire_ui_signals(self):
        self.cmb_p.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_t.currentIndexChanged.connect(self._on_ui_widget_changed)

    def save(self):
        try:
            amt_text = self.inp_amount.text().replace('.', '').replace(',', '.')
            if not amt_text: amt_text = "0"
            amt = float(amt_text)
            
            # if amt <= 0: return # Allow 0 or negative maybe No, let's keep it safe.
            
            self.data = {
                "amount": amt,
                "personnel_name": self.cmb_p.currentText(),
                "type": self.cmb_t.currentText(),
                "desc": self.inp_desc.text(),
                "date": self.date_edit.date().toString("yyyy-MM-dd")
            }
            self.accept()
        except ValueError as e:
            logger.debug(f"TransactionAddDialog amount parse error: {e}")

