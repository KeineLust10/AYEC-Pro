# -*- coding: utf-8 -*-

"""
Language & Region Settings Widget
Matches the user's requested design from the screenshot.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QGroupBox,
    QPushButton,
    QFormLayout,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.utils.toast_notification import show_success
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens



class LanguageSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Dil ve Bölge Ayarları"""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        group = QGroupBox("Dil, Tarih ve Para Birimi")
        group.setStyleSheet(
            theme_qss(
                "QGroupBox { font-weight: bold; border: 1px solid @border; "
                "border-radius: 8px; margin-top: 20px; padding-top: 20px; color: @text; }"
            )
        )
        group_layout = QFormLayout()
        group_layout.setSpacing(20)
        group_layout.setContentsMargins(20, 30, 20, 20)

        label_font = QFont("Segoe UI", 10)

        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Türkçe (TR)", "English (EN)", "Deutsch (DE)", "Français (FR)"])
        self.cmb_lang.setFixedHeight(35)
        lbl_lang = QLabel("Uygulama Dili:")
        lbl_lang.setFont(label_font)
        group_layout.addRow(lbl_lang, self.cmb_lang)

        self.cmb_date = QComboBox()
        self.cmb_date.addItems(
            [
                "GG.AA.YYYY (31.12.2025)",
                "AA/GG/YYYY (12/31/2025)",
                "YYYY-AA-GG (2025-12-31)",
                "Uzun Tarih (5 Mart 2026)",
            ]
        )
        self.cmb_date.setFixedHeight(35)
        lbl_date = QLabel("Tarih Formatı:")
        lbl_date.setFont(label_font)
        group_layout.addRow(lbl_date, self.cmb_date)

        self.cmb_global_currency = QComboBox()
        self.cmb_global_currency.addItems(CurrencyHelper.get_choice_texts())
        self.cmb_global_currency.setFixedHeight(35)
        lbl_gcur = QLabel("Aktif Para Birimi:")
        lbl_gcur.setFont(label_font)
        group_layout.addRow(lbl_gcur, self.cmb_global_currency)

        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems(
            [
                "1.234,56 (TR Standart)",
                "1,234.56 (US Standart)",
                "1 234,56 (Alternatif)",
            ]
        )
        self.cmb_currency.setFixedHeight(35)
        lbl_cur = QLabel("Sayı Formatı:")
        lbl_cur.setFont(label_font)
        group_layout.addRow(lbl_cur, self.cmb_currency)

        self.cmb_timezone = QComboBox()
        self.cmb_timezone.addItems(
            [
                "(UTC+03:00) İstanbul",
                "(UTC+00:00) London",
                "(UTC+01:00) Berlin",
                "(UTC-05:00) New York",
            ]
        )
        self.cmb_timezone.setFixedHeight(35)
        lbl_tz = QLabel("Saat Dilimi:")
        lbl_tz.setFont(label_font)
        group_layout.addRow(lbl_tz, self.cmb_timezone)

        group.setLayout(group_layout)
        layout.addWidget(group)
        layout.addStretch()

        self.btn_save = QPushButton("KAYDET VE UYGULA")
        self.btn_save.setFixedHeight(45)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        self.btn_save.clicked.connect(self.save_settings)
        layout.addWidget(self.btn_save)

    def _wire_ui_signals(self):
        self.cmb_lang.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_date.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_global_currency.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_currency.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_timezone.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_settings(self):
        """Ayarları veritabanından yükle"""
        lang = self.db.get_setting("app_lang", "Türkçe (TR)")
        date_fmt = self.db.get_setting("date_format", "GG.AA.YYYY (31.12.2025)")
        global_curr = CurrencyHelper.get_code(self.db)
        curr_fmt = self.db.get_setting("currency_format", "1.234,56 (TR Standart)")
        tz = self.db.get_setting("timezone", "(UTC+03:00) İstanbul")

        self.cmb_lang.setCurrentText(lang)
        self.cmb_date.setCurrentText(date_fmt)
        CurrencyHelper.set_combo_to_code(self.cmb_global_currency, global_curr)
        self.cmb_currency.setCurrentText(curr_fmt)
        self.cmb_timezone.setCurrentText(tz)

    def save_settings(self):
        """Ayarları veritabanına kaydet"""
        self.db.set_setting("app_lang", self.cmb_lang.currentText())
        self.db.set_setting("date_format", self.cmb_date.currentText())
        CurrencyHelper.persist_code(self.db, self.cmb_global_currency.currentText())
        self.db.set_setting("currency_format", self.cmb_currency.currentText())
        self.db.set_setting("timezone", self.cmb_timezone.currentText())
        if self.main_window and hasattr(self.main_window, "refresh_currency_context"):
            self.main_window.refresh_currency_context()

        show_success(self, "Dil, tarih ve para birimi ayarları başarıyla kaydedildi.")
