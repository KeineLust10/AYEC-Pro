# -*- coding: utf-8 -*-

"""
SMS Settings Widget
SMS ayarlari ve sablon yonetimi widget'lari.
"""

import html
import re

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QAbstractSpinBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QMessageBox,
    QCheckBox,
    QGridLayout,
    QScrollArea,
    QSizePolicy,
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QTextDocument
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtPrintSupport import QPrinter

from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_error, show_success


class SmsTemplateHeaderView(QHeaderView):
    def paintSection(self, painter, rect, logical_index):
        if not rect.isValid():
            return
        super().paintSection(painter, rect, logical_index)



class SMSSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """SMS Settings Tab"""

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss(
            "QWidget#part9_sms_settings { background-color: @window; color: @text; } "
            "QWidget#part9_sms_settings QLabel { color: @text_muted; border: 0; }"
        ))
        self.apply_reference_typography()

    def apply_reference_typography(self):
        title = getattr(self, "loop_title", None)
        if title is not None:
            current_title_font = title.font()
            title_font = QFont("Arial")
            if current_title_font.pointSizeF() > 0:
                title_font.setPointSizeF(current_title_font.pointSizeF())
            title_font.setWeight(current_title_font.weight())
            title_font.setItalic(current_title_font.italic())
            title.setFont(title_font)

    def __init__(self, db, main_window=None, use_internal_scroll=True):
        super().__init__()
        self.setObjectName("part9_sms_settings")
        self.setStyleSheet(theme_qss(
            "QWidget#part9_sms_settings { background-color: @window; color: @text; } "
            "QWidget#part9_sms_settings QLabel { color: @text_muted; border: 0; }"
        ))
        self.db = db
        self.main_window = main_window
        fallback_font = QFont()
        fallback_font.setFamilies(["Inter", "Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.setup_ui(use_internal_scroll=use_internal_scroll)
        self._wire_ui_signals()
        self.load_data()
        self.apply_reference_typography()

    def setup_ui(self, use_internal_scroll=True):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(9)
        if use_internal_scroll:
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: @window; border: 0; } QWidget { background: @window; }")
            scroll.setWidget(body)
            root.addWidget(scroll)
        else:
            root.addWidget(body)

        title_row = QHBoxLayout()
        title_icon = QLabel("\u2699")
        title_icon.setFixedSize(28, 28)
        title_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_icon.setStyleSheet("color: @text; background: @surface_alt; border: 1px solid @border; border-radius: 4px; font-size: 17px;")
        title_row.addWidget(title_icon)
        title_column = QVBoxLayout()
        title_column.setSpacing(1)
        title = QLabel("SMS Servis Sa\u011flay\u0131c\u0131 & API Ayarlar\u0131")
        title.setFont(QFont("Inter", 15, QFont.Weight.Bold))
        title.setStyleSheet("color: @text; background: transparent;")
        title_column.addWidget(title)
        subtitle = QLabel("GSM operatoru ve aggregator tabanli giden mesaj parametreleri")
        subtitle.setStyleSheet("color: @text_muted; background: transparent; font-size: 8px;")
        title_column.addWidget(subtitle)
        title_row.addLayout(title_column)
        title_row.addStretch()
        provider = QLabel("SA\u011eLAYICI: NetGSM / Ileti Merkezi    \u2022    KALAN KRED\u0130: --")
        provider.setAutoFillBackground(True)
        provider.setStyleSheet("color: @accent; background-color: @surface_alt; border: 1px solid @border; border-radius: 4px; padding: 6px 9px; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
        title_row.addWidget(provider)
        layout.addLayout(title_row)

        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 4px; }")
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.setSpacing(8)
        info_icon = QLabel("i")
        info_icon.setFixedSize(18, 18)
        info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_icon.setStyleSheet("color: @accent; background: @surface_alt; border-radius: 9px; font: 700 11px 'Inter', 'Segoe UI', sans-serif;")
        info_layout.addWidget(info_icon)
        info = QLabel("SMS g\u00f6nderebilmek i\u00e7in servis API kullan\u0131c\u0131 ad\u0131 ve \u015fifrenizi girin. Onayl\u0131 SMS ba\u015fl\u0131\u011f\u0131 operat\u00f6r onay\u0131ndan sonra aktifle\u015fir.")
        info.setWordWrap(True)
        info.setStyleSheet("background: transparent; color: @text; font: 9px 'Inter', 'Segoe UI', sans-serif;")
        info_layout.addWidget(info, 1)
        layout.addWidget(info_frame)

        cred_card = QFrame()
        cred_card.setStyleSheet("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 4px; }")
        cred_layout = QGridLayout(cred_card)
        cred_layout.setContentsMargins(12, 12, 12, 12)
        cred_layout.setHorizontalSpacing(10)
        cred_layout.setVerticalSpacing(6)

        def add_field(label, column, password=False):
            field = QWidget(cred_card)
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setStyleSheet("color: @text_muted; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            field_layout.addWidget(caption)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            edit.setMinimumHeight(36)
            edit.setStyleSheet("QLineEdit { background: @surface; color: @text; border: 1px solid @border; border-radius: 4px; padding: 7px 9px; selection-background-color: @accent; }")
            row.addWidget(edit, 1)
            if password:
                toggle = QPushButton("G\u00f6ster")
                toggle.setFixedHeight(36)
                toggle.setStyleSheet("QPushButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 4px; padding: 0 8px; }")
                toggle.clicked.connect(lambda _checked=False, control=edit, button=toggle: self._toggle_secret(control, button))
                row.addWidget(toggle)
            field_layout.addLayout(row)
            cred_layout.addWidget(field, 0, column)
            return edit

        self.inp_user = add_field("KULLANICI ADI / API KEY  \u2022  ZORUNLU", 0)
        self.inp_user.setPlaceholderText("API kullan\u0131c\u0131 ad\u0131")
        self.inp_pass = add_field("\u015e\u0130FRE / G\u0130ZL\u0130 ANAHTAR", 1, True)
        self.inp_pass.setPlaceholderText("API \u015fifresi veya token")
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_title = add_field("ONAYLI SMS BA\u015eLI\u011eI (ORIGIN)  \u2022  11 KARAKTER", 2)
        self.inp_title.setMaxLength(11)
        self.inp_title.setPlaceholderText("G\u00f6nderici ba\u015fl\u0131\u011f\u0131")
        self.inp_title.textChanged.connect(lambda value: self.inp_title.setText(value.upper()))
        status_field = QWidget(cred_card)
        status_layout = QVBoxLayout(status_field)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_label = QLabel("SERV\u0130S DURUMU")
        status_label.setStyleSheet("color: @text_muted; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
        status_layout.addWidget(status_label)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Pasif", "Aktif (Canl\u0131 \u0130letim)"])
        self.cmb_status.setFixedHeight(36)
        self.cmb_status.setStyleSheet("QComboBox { background: @surface; color: @text; border: 1px solid @border; border-radius: 4px; padding: 6px 9px; } QComboBox QAbstractItemView { background: @surface_alt; color: @text; selection-background-color: @accent; }")
        status_layout.addWidget(self.cmb_status)
        cred_layout.addWidget(status_field, 0, 3)
        for column in range(4):
            cred_layout.setColumnStretch(column, 1)

        action_row = QHBoxLayout()
        safety = QLabel("API anahtarlar\u0131 g\u00fcvenli ayar deposunda AES-256 ile korunur.")
        safety.setStyleSheet("color: @text_muted; background: transparent; font-size: 9px;")
        action_row.addWidget(safety)
        action_row.addStretch()
        self.btn_test_sms = QPushButton("Test SMS G\u00f6nder")
        self.btn_test_sms.setFixedHeight(34)
        self.btn_test_sms.setStyleSheet("QPushButton { background: @surface_alt; color: @accent; border: 1px solid @border; border-radius: 4px; padding: 0 12px; font: 600 9px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { background: @hover_bg; }")
        self.btn_test_sms.clicked.connect(self.test_sms)
        action_row.addWidget(self.btn_test_sms)
        btn_update_cred = QPushButton("G\u00dcNCELLE & KAYDET")
        btn_update_cred.setFixedHeight(36)
        btn_update_cred.setStyleSheet("QPushButton { background: @accent; color: @selection_text; border: 1px solid @accent; border-radius: 4px; padding: 0 14px; font: 700 9px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { background: @accent; }")
        btn_update_cred.clicked.connect(self.save_credentials)
        action_row.addWidget(btn_update_cred)
        cred_layout.addLayout(action_row, 1, 0, 1, 4)
        layout.addWidget(cred_card)

        loop_head = QHBoxLayout()
        loop_title = QLabel("SMS G\u00d6NDER\u0130M D\u00d6NG\u00dc AYARLARI")
        loop_font = QFont()
        loop_font.setFamilies(["Arial", "Segoe UI"])
        loop_font.setPointSize(13)
        loop_font.setWeight(QFont.Weight.Bold)
        loop_title.setFont(loop_font)
        loop_title.setStyleSheet("font-family: 'Arial'; font-size: 13px; font-weight: 700; color: @text; background: transparent;")
        self.loop_title = loop_title
        loop_head.addWidget(loop_title)
        loop_head.addStretch()
        loop_badge = QLabel("CRON OTOMASYONU DEVREDE    \u2022    D\u00f6ng\u00fc taramas\u0131: 15 dk")
        loop_badge.setAutoFillBackground(True)
        loop_badge.setStyleSheet("color: @success; background-color: @surface_alt; border: 1px solid @border; border-radius: 4px; padding: 5px 8px; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
        loop_head.addWidget(loop_badge)
        layout.addLayout(loop_head)
        description = QLabel("Belirli durum kodlar\u0131na g\u00f6re otomatik g\u00f6nderilen SMS'lerin g\u00fcn d\u00f6ng\u00fcs\u00fcn\u00fc ve kullan\u0131lacak \u015fablonu belirleyin.")
        description.setStyleSheet("color: @text_muted; background: transparent; font-size: 9px;")
        layout.addWidget(description)

        self._loop_template_widgets = {}
        self._loop_active_widgets = {}
        self._loop_spin_widgets = {}
        self.db.cursor.execute("SELECT name FROM whatsapp_templates ORDER BY id")
        template_names = [row[0] for row in self.db.cursor.fetchall() if row and row[0]]
        self.reference_templates = {
            "repaired": "Onar\u0131m S\u00fcreci Bilgilendirmesi",
            "approval": "M\u00fc\u015fteri Maliyet Onay\u0131 Talebi",
            "parts": "Yedek Par\u00e7a Tedarik S\u00fcreci",
            "testing": "Kalite Kontrol ve Stres Testi",
            "done": "Cihaz Teslime Haz\u0131r Bildirimi",
        }
        loop_grid = QGridLayout()
        loop_grid.setHorizontalSpacing(8)
        loop_grid.setVerticalSpacing(8)

        def create_card(label, setting_key, code):
            card = QFrame()
            card.setStyleSheet("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 4px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(8, 9, 8, 9)
            card_layout.setSpacing(5)
            title_row = QHBoxLayout()
            dot = QLabel("\u2022")
            dot.setStyleSheet("color: @accent; background: transparent; font-size: 14px;")
            title_row.addWidget(dot)
            name = QLabel(label)
            name.setStyleSheet("color: @text; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            title_row.addWidget(name)
            title_row.addStretch()
            active = QCheckBox()
            active.setChecked(True)
            active.setObjectName(f"sms_loop_active_{setting_key}")
            active.setToolTip(f"{label} SMS d\u00f6ng\u00fcs\u00fcn\u00fc etkinle\u015ftir")
            active.setStyleSheet("QCheckBox::indicator { width: 25px; height: 14px; border-radius: 7px; background: @border; } QCheckBox::indicator:checked { background: @accent; }")
            title_row.addWidget(active)
            card_layout.addLayout(title_row)
            days_label = QLabel("D\u00f6ng\u00fc Aral\u0131\u011f\u0131")
            days_label.setStyleSheet("color: @text_muted; background: transparent; border: 0; font-size: 8px;")
            days_row = QHBoxLayout()
            days_row.setContentsMargins(0, 0, 0, 0)
            days_row.addWidget(days_label)
            days_row.addStretch()
            spin = QSpinBox()
            spin.setRange(0, 30)
            spin.setSuffix(" g\u00fcn")
            spin.setFixedHeight(32)
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setStyleSheet("QSpinBox { background: @surface; color: @accent; border: 1px solid @border; border-radius: 4px; padding: 0 8px; font: 700 15px 'JetBrains Mono', Consolas, monospace; }")
            spin.setFont(QFont("JetBrains Mono", 13, QFont.Weight.Bold))
            days_row.addWidget(spin)
            card_layout.addLayout(days_row)
            template_label = QLabel("BA\u011eLI \u015eABLON")
            template_label.setStyleSheet("color: @text_muted; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            card_layout.addWidget(template_label)
            combo = QComboBox()
            combo.addItems(template_names or [self.reference_templates[setting_key]])
            combo.setFixedHeight(28)
            combo.setStyleSheet("QComboBox { background: @surface; color: @text; border: 1px solid @border; border-radius: 3px; padding: 5px 7px; font: 8px 'Inter', 'Segoe UI', sans-serif; } QComboBox QAbstractItemView { background: @surface_alt; color: @text; selection-background-color: @accent; }")
            card_layout.addWidget(combo)
            code_row = QHBoxLayout()
            code_label = QLabel(f"KOD: #STA-{code}")
            code_label.setStyleSheet("color: @text_muted; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            code_row.addWidget(code_label)
            code_row.addStretch()
            quick = QPushButton("\u2713")
            quick.setFixedSize(28, 28)
            quick.setToolTip(f"{label} d\u00f6ng\u00fcs\u00fcn\u00fc kaydet")
            quick.setStyleSheet("QPushButton { background: @accent; color: @selection_text; border: 0; border-radius: 4px; font-weight: 700; }")
            quick.clicked.connect(lambda _checked=False, key=setting_key: self._save_loop(key))
            code_row.addWidget(quick)
            card_layout.addLayout(code_row)
            self._loop_template_widgets[setting_key] = combo
            self._loop_active_widgets[setting_key] = active
            self._loop_spin_widgets[setting_key] = spin
            return card, spin, combo

        loop_items = [
            ("TAM\u0130RDE", "repaired", "01"),
            ("ONAY BEKL\u0130YOR", "approval", "02"),
            ("PAR\u00c7A BEKL\u0130YOR", "parts", "03"),
            ("TEST S\u00dcREC\u0130NDE", "testing", "04"),
            ("TAM\u0130R ED\u0130LD\u0130", "done", "05"),
        ]
        for column, (label, key, code) in enumerate(loop_items):
            card, spin, combo = create_card(label, key, code)
            loop_grid.addWidget(card, 0, column)
            loop_grid.setColumnStretch(column, 1)
            setattr(self, {"repaired":"spn_repaired", "approval":"spn_approval", "parts":"spn_parts", "testing":"spn_testing", "done":"spn_done"}[key], spin)
            setattr(self, {"repaired":"cmb_template_repaired", "approval":"cmb_template_approval", "parts":"cmb_template_parts", "testing":"cmb_template_testing", "done":"cmb_template_done"}[key], combo)
        layout.addLayout(loop_grid)

        save_loop_row = QHBoxLayout()
        self.lbl_loop_status = QLabel("Otomatik d\u00f6ng\u00fc ayarlar\u0131 kaydedilen tercihleri kullan\u0131r.")
        self.lbl_loop_status.setStyleSheet("color: @text_muted; background: transparent; font-size: 9px;")
        save_loop_row.addWidget(self.lbl_loop_status)
        save_loop_row.addStretch()
        btn_update_loop = QPushButton("T\u00dcM D\u00d6NG\u00dc AYARLARINI G\u00dcNCELLE")
        btn_update_loop.setFixedHeight(36)
        btn_update_loop.setStyleSheet("QPushButton { background: @accent; border: 1px solid @accent; border-radius: 4px; color: @selection_text; padding: 0 13px; font: 700 9px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { background: @accent; }")
        btn_update_loop.clicked.connect(self.save_loops)
        save_loop_row.addWidget(btn_update_loop)
        layout.addSpacing(9)
        layout.addLayout(save_loop_row)

        layout.addSpacing(10)
        metric_row = QHBoxLayout()
        metric_specs = [("BUG\u00dcN G\u00d6NDER\u0130LEN SMS", "--", "G\u00f6nderim ge\u00e7mi\u015fi"), ("KUYRUKTA BEKLEYENLER", "--", "Kuyruk API ba\u011flant\u0131s\u0131 yok"), ("ORTALAMA \u0130LET\u0130M GEC\u0130KMES\u0130", "--", "Operat\u00f6r DLR verisi yok")]
        self.metric_values = []
        for heading, value, detail in metric_specs:
            card = QFrame()
            card.setStyleSheet("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 4px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 7, 10, 7)
            label = QLabel(heading)
            label.setStyleSheet("color: @text_muted; background: transparent; border: 0; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            number = QLabel(value)
            number.setStyleSheet("color: @accent; background: transparent; border: 0; font: 700 19px 'JetBrains Mono', Consolas, monospace;")
            note = QLabel(detail)
            note.setStyleSheet("color: @text; background: transparent; border: 0; font-size: 8px;")
            card_layout.addWidget(label)
            card_layout.addWidget(number)
            card_layout.addWidget(note)
            metric_row.addWidget(card, 1)
            self.metric_values.append(number)
        layout.addLayout(metric_row)
        for label_widget in body.findChildren(QLabel):
            label_font = label_widget.font()
            label_font.setFamilies(["Inter", "Segoe UI", "Arial"])
            label_widget.setFont(label_font)
        layout.addStretch(1)

    def _toggle_secret(self, control, button):
        if control.echoMode() == QLineEdit.EchoMode.Password:
            control.setEchoMode(QLineEdit.EchoMode.Normal)
            button.setText("Gizle")
        else:
            control.setEchoMode(QLineEdit.EchoMode.Password)
            button.setText("Goster")

    def test_sms(self):
        from PyQt6.QtWidgets import QInputDialog
        phone, accepted = QInputDialog.getText(self, "Test SMS", "Test SMS hedef numaras\u0131:")
        if accepted and str(phone or "").strip():
            QMessageBox.information(self, "Test SMS", "Bu uygulama SMS g\u00f6nderim testi i\u00e7in sa\u011flay\u0131c\u0131 test API u\u00e7 noktas\u0131na sahip de\u011fil. Ayarlar kaydedildi; canl\u0131 SMS g\u00f6nderilmedi.")

    def _save_loop(self, key):
        spin = self._loop_spin_widgets[key]
        combo = self._loop_template_widgets[key]
        active = self._loop_active_widgets[key]
        self.db.set_setting(f"loop_{key}", str(spin.value()))
        self.db.set_setting(f"loop_template_{key}", combo.currentText())
        self.db.set_setting(f"loop_active_{key}", "1" if active.isChecked() else "0")
        self.lbl_loop_status.setText(f"{key} d\u00f6ng\u00fc ayar\u0131 kaydedildi.")

    def _wire_ui_signals(self):
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        self.inp_user.setText(self.db.get_setting("sms_username", ""))
        from src.utils.secure_setting_store import SecureSettingStore

        self.inp_pass.setText(SecureSettingStore.get(self.db, "sms_password", ""))
        self.inp_title.setText(self.db.get_setting("sms_title", ""))
        status = self.db.get_setting("sms_active", "0")
        self.cmb_status.setCurrentIndex(1 if status == "1" else 0)

        self.spn_repaired.setValue(int(self.db.get_setting("loop_repaired", "3")))
        self.spn_approval.setValue(int(self.db.get_setting("loop_approval", "1")))
        self.spn_parts.setValue(int(self.db.get_setting("loop_parts", "2")))
        self.spn_testing.setValue(int(self.db.get_setting("loop_testing", "1")))
        self.spn_done.setValue(int(self.db.get_setting("loop_done", "0")))
        for key, combo in self._loop_template_widgets.items():
            saved = self.db.get_setting(f"loop_template_{key}", "")
            index = combo.findText(saved)
            if index >= 0:
                combo.setCurrentIndex(index)
            elif not self.db.get_setting(f"loop_template_{key}", ""):
                reference_index = combo.findText(self.reference_templates[key])
                if reference_index >= 0:
                    combo.setCurrentIndex(reference_index)
            self._loop_active_widgets[key].setChecked(self.db.get_setting(f"loop_active_{key}", "1") != "0")
        try:
            self.db.cursor.execute("SELECT COUNT(*) FROM sms_log WHERE date(sent_at)=date('now','localtime')")
            row = self.db.cursor.fetchone()
            self.metric_values[0].setText(str(int((row or [0])[0] or 0)))
        except Exception:
            self.metric_values[0].setText("--")

    def save_credentials(self):
        self.db.set_setting("sms_username", self.inp_user.text())
        from src.utils.secure_setting_store import SecureSettingStore

        SecureSettingStore.set(self.db, "sms_password", self.inp_pass.text())
        self.db.set_setting("sms_title", self.inp_title.text())
        self.db.set_setting("sms_active", "1" if self.cmb_status.currentIndex() == 1 else "0")
        if self.main_window:
            self.main_window.show_notification("SMS kimlik bilgileri güncellendi.", "success")

    def save_loops(self):
        self.db.set_setting("loop_repaired", str(self.spn_repaired.value()))
        self.db.set_setting("loop_approval", str(self.spn_approval.value()))
        self.db.set_setting("loop_parts", str(self.spn_parts.value()))
        self.db.set_setting("loop_testing", str(self.spn_testing.value()))
        self.db.set_setting("loop_done", str(self.spn_done.value()))
        for key, combo in self._loop_template_widgets.items():
            self.db.set_setting(f"loop_template_{key}", combo.currentText())
            self.db.set_setting(f"loop_active_{key}", "1" if self._loop_active_widgets[key].isChecked() else "0")
        if self.main_window:
            self.main_window.show_notification("Döngü ayarları güncellendi.", "success")


class TemplateEditDialog(ModernDialog):
    """SMS Sablon Duzenleme Dialog'u"""

    def __init__(self, name, content, parent=None):
        super().__init__("Şablon Düzenle", parent, width=600, height=450)
        self.name = name
        self.initial_content = content
        self.limit = 1000
        self.setup_content()

    def setup_content(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        main_layout.addWidget(QLabel("\u015eablon ad\u0131"))
        self.txt_name = QLineEdit(self.name)
        self.txt_name.setStyleSheet(DesignTokens.get_input_qss())
        main_layout.addWidget(self.txt_name)

        self.txt_content = QTextEdit()
        self.txt_content.setPlainText(self.initial_content)
        self.txt_content.setStyleSheet(DesignTokens.get_input_qss())
        self.txt_content.textChanged.connect(self.update_counter)
        main_layout.addWidget(self.txt_content)

        vars_info = QLabel("Kullan\u0131labilir de\u011fi\u015fkenler: {musteri}, {tutar}, {link}, {randevu}, {serino}")
        vars_info.setStyleSheet("color: @text_muted; font-size: 12px; font-style: italic;")
        main_layout.addWidget(vars_info)

        self.lbl_counter = QLabel(f"Karakter: {len(self.initial_content)} / 160")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.lbl_counter)

        container = QWidget()
        container.setLayout(main_layout)
        self.add_widget(container)
        self.add_cancel_button("İptal")
        self.add_button("Kaydet", "primary", self.save)

    def update_counter(self):
        length = len(self.txt_content.toPlainText())
        self.lbl_counter.setText(f"Karakter: {length} / 160  |  SMS: {max(1, (length + 159) // 160)}")

    def save(self):
        self.new_content = self.txt_content.toPlainText()
        self.accept()

    def get_content(self):
        return self.new_content

    def get_name(self):
        return self.txt_name.text().strip()


class SMSTemplatesWidget(QWidget):
    """SMS Templates Tab"""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "table"):
            QTimer.singleShot(0, self._resize_template_rows)

    def _resize_template_rows(self):
        row_count = self.table.rowCount()
        if row_count == 0:
            return
        if row_count <= 4:
            row_height = 72
        else:
            available_height = self.table.viewport().height()
            row_height = max(60, min(72, available_height // row_count - 1))
        for row in range(row_count):
            self.table.setRowHeight(row, row_height)

    def _apply_reference_header_style(self):
        if not hasattr(self, "table"):
            return
        header = self.table.horizontalHeader()
        header.setFixedHeight(28)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        header_palette = header.palette()
        header_color = QColor(tc("text_muted"))
        header_palette.setColor(QPalette.ColorRole.ButtonText, header_color)
        header_palette.setColor(QPalette.ColorRole.WindowText, header_color)
        header_palette.setColor(QPalette.ColorRole.Text, header_color)
        header.setPalette(header_palette)
        for column in range(self.table.columnCount()):
            item = self.table.horizontalHeaderItem(column)
            if item is None:
                continue
            item.setForeground(QColor(tc("text_muted")))
            item.setFont(header_font)

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss(
            "QWidget#part9_sms_templates { background-color: @window; color: @text; } "
            "QWidget#part9_sms_templates QLabel { color: @text_muted; font-family: 'Inter', 'Segoe UI', sans-serif; }"
        ))
        for row in range(self.table.rowCount()):
            for column in range(self.table.columnCount()):
                item = self.table.item(row, column)
                if item is None:
                    continue
                color_key = "text_muted" if column in (0, 3) else "success" if column == 4 else "text"
                item.setForeground(QColor(tc(color_key)))
        self._apply_reference_header_style()

    def __init__(self, db, main_window=None):
        super().__init__()
        self.setObjectName("part9_sms_templates")
        self.setStyleSheet(theme_qss(
            "QWidget#part9_sms_templates { background-color: @window; color: @text; } "
            "QWidget#part9_sms_templates QLabel { color: @text_muted; font-family: 'Inter', 'Segoe UI', sans-serif; }"
        ))
        self.db = db
        self.main_window = main_window
        fallback_font = QFont()
        fallback_font.setFamilies(["Inter", "Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.setup_ui()
        self.init_default_templates()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        variables = QFrame()
        variables.setObjectName("smsVariablePool")
        variables.setStyleSheet("QFrame#smsVariablePool { background: @surface_alt; border: 1px solid @border; border-radius: 5px; }")
        variables.setMaximumHeight(126)
        variables_layout = QVBoxLayout(variables)
        variables_layout.setContentsMargins(11, 9, 11, 15)
        variables_layout.setSpacing(15)
        variables_header = QHBoxLayout()
        variables_title = QLabel("Dinamik De\u011fi\u015fken Havuzu")
        variables_title.setStyleSheet("color: @text; font-weight: 700; background: transparent;")
        variables_header.addWidget(variables_title)
        variables_header.addWidget(QLabel("(\u015eablon kurgusunda panoya kopyalamak i\u00e7in t\u0131klay\u0131n)"))
        variables_header.addStretch()
        encoding_badge = QLabel("GSM 7-Bit  &  UTF-8 Uyumlu")
        encoding_badge.setStyleSheet("color: @success; background: transparent; font: 700 9px 'Segoe UI', Arial;")
        variables_header.addWidget(encoding_badge)
        variables_layout.addLayout(variables_header)
        token_grid = QGridLayout()
        token_grid.setHorizontalSpacing(8)
        token_grid.setVerticalSpacing(8)
        tokens = [
            ("{musteri}", "Ad Soyad"), ("{tutar}", "Hizmet Bedeli"),
            ("{bakiye}", "Kalan Cari"), ("{cihaz}", "Marka & Model"),
            ("{servis_no}", "Kay\u0131t Barkodu"), ("{randevu_araligi}", "Tarih / Saat"),
            ("{takip_linki}", "K\u0131sa URL"), ("{odeme_linki}", "Online \u00d6deme"),
        ]
        self.token_buttons = []
        for index, (token, description) in enumerate(tokens):
            token_card = QWidget()
            token_card.setStyleSheet(
                "QWidget { background: @surface; border: 1px solid @border; border-radius: 4px; }"
            )
            token_card_layout = QHBoxLayout(token_card)
            token_card_layout.setContentsMargins(0, 0, 0, 0)
            token_card_layout.setSpacing(3)
            button = QPushButton(token)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip("De\u011fi\u015fkeni panoya kopyala")
            token_colors = ("accent", "info", "success", "warning", "accent", "info", "success", "accent")
            button.setStyleSheet(
                "QPushButton { color: @%s; background: transparent; border: 0; padding: 3px 4px; "
                "font: 700 8px 'JetBrains Mono', Consolas, monospace; } "
                "QPushButton:hover { color: @text; }" % token_colors[index]
            )
            button.clicked.connect(lambda checked=False, value=token: QApplication.clipboard().setText(value))
            token_card_layout.addWidget(button)
            token_description = QLabel(description)
            token_description.setStyleSheet("color: @text_muted; background: transparent; font-size: 8px;")
            token_card_layout.addWidget(token_description)
            token_grid.addWidget(token_card, index // 6, index % 6)
            self.token_buttons.append(button)
        variables_layout.addLayout(token_grid)
        layout.addWidget(variables)

        header = QHBoxLayout()
        section_icon = QLabel("\u2709")
        section_icon.setFixedSize(26, 26)
        section_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        section_icon.setStyleSheet("color: @text; background: @surface_alt; border: 1px solid @border; border-radius: 4px; font-size: 15px;")
        header.addWidget(section_icon)
        title_column = QVBoxLayout()
        title = QLabel("SMS \u015eablonlar\u0131")
        title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: @text; background: transparent;")
        title_column.addWidget(title)
        subtitle = QLabel("Otomatik ve manuel SMS g\u00f6nderim d\u00f6ng\u00fclerine ait \u015fablon parametreleri")
        subtitle.setStyleSheet("color: @text_muted; background: transparent; font-size: 9px;")
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()

        self.btn_copy = QPushButton("\u25a3  KOPYALA")
        self.btn_copy.clicked.connect(self.copy_templates)
        self.btn_excel = QPushButton("\u25a6  EXCEL")
        self.btn_excel.clicked.connect(self.export_templates_excel)
        self.btn_pdf = QPushButton("\u25a7  PDF")
        self.btn_pdf.clicked.connect(self.export_templates_pdf)
        for button in (self.btn_copy, self.btn_excel, self.btn_pdf):
            button.setFixedHeight(32)
            button.setStyleSheet("QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 4px; color: @text; padding: 5px 9px; font: 700 8px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { border-color: @border; color: @text; }")
            header.addWidget(button)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("\u015eablon veya eylem ara...")
        self.inp_search.setFixedWidth(215)
        self.inp_search.setFixedHeight(32)
        self.inp_search.setStyleSheet("QLineEdit { background: @surface; border: 1px solid @border; border-radius: 4px; color: @text; padding: 6px 8px; font: 9px 'Inter', 'Segoe UI', sans-serif; } QLineEdit:focus { border-color: @accent; }")
        self.inp_search.textChanged.connect(self.load_data)
        header.addWidget(self.inp_search)

        self.btn_add_template = QPushButton("+ Yeni \u015eablon Ekle")
        self.btn_add_template.setFixedHeight(32)
        self.btn_add_template.setStyleSheet("QPushButton { background: @accent; border: 1px solid @accent; border-radius: 4px; color: @selection_text; padding: 6px 10px; font: 700 8px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { background: @accent; }")
        self.btn_add_template.clicked.connect(self.add_template)
        header.addWidget(self.btn_add_template)
        layout.addLayout(header)

        layout.addSpacing(12)
        self.table = QTableWidget()
        self.table.setHorizontalHeader(
            SmsTemplateHeaderView(Qt.Orientation.Horizontal, self.table)
        )
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "NO", "EYLEM / TET\u0130KLEY\u0130C\u0130 DURUM", "SMS \u0130\u00c7ER\u0130\u011e\u0130 VE D\u0130NAM\u0130K ALANLAR",
            "UZUNLUK / KRED\u0130", "DURUM", "\u0130\u015eLEMLER"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        for column, width in ((0, 48), (1, 182), (3, 112), (4, 80), (5, 158)):
            self.table.setColumnWidth(column, width)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(72)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(True)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { border: 1px solid @border; background: @surface_alt; color: @text; gridline-color: @border; } "
            "QHeaderView::section { background: @surface; color: @text_muted; border: 0; border-bottom: 1px solid @border; padding: 8px 6px; font-weight: bold; font-size: 8px; } "
            "QTableWidget::item { color: @text; background: @surface_alt; border-bottom: 1px solid @border; padding: 6px; }"
        ))
        self.table.setMinimumHeight(280)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.table, 1)

        footer = QFrame()
        footer.setObjectName("smsTemplateFooter")
        footer.setStyleSheet(
            "QFrame#smsTemplateFooter { background: @surface; border-top: 1px solid @border; }"
        )
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 5, 10, 5)
        footer_layout.setSpacing(8)
        self.footer_label = QLabel("Kay\u0131tlar listeleniyor.")
        self.footer_label.setStyleSheet(
            "color: @text_muted; font-size: 8px; background: transparent; border: 0;"
        )
        footer_layout.addWidget(self.footer_label, 1)
        timestamp = QLabel("SUNUCU ZAMAN DAMGASI: 2025-02-23 14:10 UTC+3")
        timestamp.setStyleSheet(
            "color: @text_muted; background: transparent; border: 0; "
            "font: 700 7px 'JetBrains Mono', Consolas, monospace;"
        )
        footer_layout.addWidget(timestamp)
        self.page_previous = QPushButton("\u2039")
        self.page_previous.setEnabled(False)
        self.page_current = QLabel("1 / 1")
        self.page_next = QPushButton("\u203a")
        self.page_next.setEnabled(False)
        for control in (self.page_previous, self.page_current, self.page_next):
            control.setFixedHeight(24)
            control.setStyleSheet(
                "QPushButton, QLabel { background: @surface_alt; color: @text_muted; "
                "border: 1px solid @border; border-radius: 3px; padding: 2px 7px; "
                "font: 700 8px 'JetBrains Mono', Consolas, monospace; }"
            )
            footer_layout.addWidget(control)
        layout.addWidget(footer)
        self.table.setFont(QFont("Inter", 9))
        self.table.horizontalHeader().setFont(QFont("JetBrains Mono", 8, QFont.Weight.Bold))
        self._apply_reference_header_style()
        for widget in self.findChildren(QWidget):
            widget_font = widget.font()
            widget_font.setFamilies(["Inter", "Segoe UI", "Arial"])
            widget.setFont(widget_font)

    def init_default_templates(self):
        self.db.cursor.execute("SELECT * FROM whatsapp_templates")
        existing_names = {row[1] for row in self.db.cursor.fetchall()}
        defaults = [
            (
                "MANUEL BOR\u00c7 EKLEME",
                "Say\u0131n {musteri}; {tutar} TL bor\u00e7 sisteme i\u015flenmi\u015ftir. "
                "Kalan borcunuz: {bakiye} TL. Detay: {odeme_linki}",
            ),
            (
                "RANDEVU \u0130PTAL SMS MUSTER\u0130YE",
                "Say\u0131n {musteri}; {randevu_araligi} tarihli teknik servis randevunuz "
                "talebiniz \u00fczerine iptal edilmi\u015ftir.",
            ),
            (
                "C\u0130HAZ KABUL B\u0130LD\u0130R\u0130M\u0130",
                "Say\u0131n {musteri}, {cihaz} cihaz\u0131n\u0131z {servis_no} takip "
                "numaras\u0131yla servisimize kabul edilmi\u015ftir. Durum takibi: {takip_linki}",
            ),
            (
                "ONARIM TAMAMLANDI & HAZIR",
                "Say\u0131n {musteri}, {cihaz} onar\u0131m\u0131 tamamlanm\u0131\u015f olup "
                "teslim almaya haz\u0131rd\u0131r. Tutar: {tutar} TL.",
            ),
            (
                "RANDEVU ONAYLANDI",
                "Say\u0131n {musteri}, {randevu_araligi} tarihli servis randevunuz onayland\u0131. "
                "Takip: {servis_no}",
            ),
            (
                "RANDEVU HATIRLATMASI",
                "Say\u0131n {musteri}, {randevu_araligi} servis randevunuzu hat\u0131rlat\u0131r\u0131z. "
                "Adres ve bilgi: {takip_linki}",
            ),
            (
                "ONAYINIZ BEKLENIYOR",
                "Say\u0131n {musteri}, {cihaz} i\u00e7in tahmini i\u015flem bedeli {tutar} TL. "
                "Onay ve detay: {odeme_linki}",
            ),
            (
                "MUSTERI ONAYI ALINDI",
                "Say\u0131n {musteri}, {cihaz} i\u00e7in verdi\u011finiz onay al\u0131nd\u0131. "
                "Servis kayd\u0131: {servis_no}",
            ),
            (
                "YEDEK PARCA BEKLENIYOR",
                "Say\u0131n {musteri}, {cihaz} i\u00e7in yedek par\u00e7a bekleniyor. "
                "Geli\u015fmeleri takip edin: {takip_linki}",
            ),
            (
                "ODEME ALINDI",
                "Say\u0131n {musteri}, {tutar} TL \u00f6demeniz al\u0131nd\u0131. "
                "Kalan bakiyeniz: {bakiye} TL. Te\u015fekk\u00fcr ederiz.",
            ),
        ]
        for name, content in defaults:
            if name not in existing_names:
                self.db.add_template(name, content)

    def load_data(self):
        query = self.inp_search.text().lower()
        self.table.setRowCount(0)
        self.db.cursor.execute("SELECT * FROM whatsapp_templates")
        templates = self.db.cursor.fetchall()

        for row_data in templates:
            tid, name, content = row_data

            if query and query not in name.lower() and query not in content.lower():
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            length = len(content or "")
            values = (str(row + 1).zfill(2), name, content, f"{length} / 160  ({max(1, (length + 159) // 160)} SMS)", "AKTIF")
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                color_key = "text_muted" if column in (0, 3) else "success" if column == 4 else "text"
                item.setForeground(QColor(tc(color_key)))
                if column == 2:
                    item.setToolTip(value)
                item.setFont(QFont("Inter", 9))
                item.setData(Qt.ItemDataRole.UserRole, value)
                if column in (1, 2, 3, 4):
                    item.setData(Qt.ItemDataRole.AccessibleTextRole, value)
                    item.setText("")
                self.table.setItem(row, column, item)

            self.table.item(row, 0).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.item(row, 3).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.item(row, 4).setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            trigger_descriptions = {
                "MANUEL BOR\u00c7 EKLEME": "Finans Modulu Tetikleyicisi",
                "RANDEVU \u0130PTAL SMS MUSTER\u0130YE": "Servis Planlama Tetikleyicisi",
                "C\u0130HAZ KABUL B\u0130LD\u0130R\u0130M\u0130": "Giris Bankosu Barkod Otomasyonu",
                "ONARIM TAMAMLANDI & HAZIR": "Teknisyen Onay Tetikleyicisi",
                "RANDEVU ONAYLANDI": "Randevu Planlama Tetikleyicisi",
                "RANDEVU HATIRLATMASI": "Otomatik Hatirlatma Tetikleyicisi",
                "ONAYINIZ BEKLENIYOR": "Teklif Onay Tetikleyicisi",
                "MUSTERI ONAYI ALINDI": "Musteri Onay Tetikleyicisi",
                "YEDEK PARCA BEKLENIYOR": "Parca Tedarik Tetikleyicisi",
                "ODEME ALINDI": "Tahsilat Tetikleyicisi",
            }
            trigger_host = QWidget()
            trigger_layout = QVBoxLayout(trigger_host)
            trigger_layout.setContentsMargins(4, 3, 4, 3)
            trigger_layout.setSpacing(3)
            trigger_badge = QLabel(name)
            trigger_badge.setStyleSheet("color: @accent; background: @surface_high; padding: 3px 6px; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            trigger_layout.addWidget(trigger_badge, 0, Qt.AlignmentFlag.AlignLeft)
            trigger_detail = QLabel(trigger_descriptions.get(name, "Otomatik SMS Tetikleyicisi"))
            trigger_detail.setStyleSheet("color: @text_muted; background: transparent; font-size: 8px;")
            trigger_layout.addWidget(trigger_detail)
            self.table.setCellWidget(row, 1, trigger_host)

            escaped_content = html.escape(content or "")
            escaped_content = re.sub(
                r"(\{[a-zA-Z0-9_]+\})",
                r'<span style="font-weight:700;">\1</span>',
                escaped_content,
            )
            content_label = QLabel(escaped_content)
            content_label.setObjectName("smsTemplateContent")
            content_label.setTextFormat(Qt.TextFormat.RichText)
            content_label.setWordWrap(True)
            content_label.setStyleSheet("color: @text; background: transparent; font: 9px 'Inter', 'Segoe UI', sans-serif;")
            self.table.setCellWidget(row, 2, content_label)

            length_host = QWidget()
            length_layout = QVBoxLayout(length_host)
            length_layout.setContentsMargins(2, 2, 2, 2)
            length_layout.setSpacing(2)
            length_label = QLabel(f"{length} / 160")
            length_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            length_label.setStyleSheet("color: @text_muted; background: transparent; font: 700 8px 'JetBrains Mono', Consolas, monospace;")
            sms_count = max(1, (length + 159) // 160)
            count_label = QLabel(f"{sms_count} SMS")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setStyleSheet("color: @success; background: @success_bg; padding: 2px 5px; font: 700 7px 'JetBrains Mono', Consolas, monospace;")
            length_layout.addWidget(length_label)
            length_layout.addWidget(count_label, 0, Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(row, 3, length_host)

            status_host = QWidget()
            status_layout = QHBoxLayout(status_host)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.addStretch(1)
            status_label = QLabel("\u25cf AKTIF")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setFixedSize(62, 20)
            status_label.setStyleSheet("color: @success; background: @success_bg; border-radius: 3px; padding: 3px 5px; font: 700 7px 'JetBrains Mono', Consolas, monospace;")
            status_layout.addWidget(status_label)
            status_layout.addStretch(1)
            self.table.setCellWidget(row, 4, status_host)

            action_host = QWidget()
            action_layout = QHBoxLayout(action_host)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(4)
            btn_edit = QPushButton("Düzenle")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet("QPushButton { background: @accent; border: 0; border-radius: 3px; color: @selection_text; padding: 5px 7px; font: 700 8px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { background: @accent; }")
            btn_edit.clicked.connect(lambda checked, i=tid, n=name, c=content: self.edit_template(i, n, c))
            btn_send = QPushButton("\u25b6")
            btn_send.setToolTip("SMS \u015fablon metnini \u00f6nizle")
            btn_send.setFixedWidth(26)
            btn_send.setStyleSheet("QPushButton { background: @surface_alt; color: @accent; border: 1px solid @border; border-radius: 4px; }")
            btn_send.clicked.connect(lambda checked=False, n=name, c=content: self.preview_template(n, c))
            btn_delete = QPushButton("\u00d7")
            btn_delete.setToolTip("Sil")
            btn_delete.setFixedWidth(26)
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet("QPushButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 3px; padding: 4px; font: 8px 'Inter', 'Segoe UI', sans-serif; } QPushButton:hover { color: @danger; border-color: @danger; }")
            btn_delete.clicked.connect(lambda checked=False, i=tid: self.delete_template(i))
            btn_edit.setFixedWidth(70)
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_send)
            action_layout.addWidget(btn_delete)
            self.table.setCellWidget(row, 5, action_host)

        self.table.setMinimumHeight(280)
        QTimer.singleShot(0, self._resize_template_rows)
        self.footer_label.setText(
            f"\u2713 Toplam {self.table.rowCount()} Aktif SMS "
            f"\u015fablonu listeleniyor    \u2022    GSM Karakter Standard\u0131: "
            "UTF-8 / T\u00fcrk\u00e7e Destekli (160 Karakter / SMS)"
        )

    def add_template(self):
        dialog = TemplateEditDialog("", "", self)
        if not dialog.exec():
            return
        name = dialog.get_name()
        if not name:
            show_error(self, "\u015eablon ad\u0131 bo\u015f olamaz.")
            return
        self.db.add_template(name, dialog.get_content())
        self.load_data()

    def preview_template(self, name, content):
        QMessageBox.information(self, name, content)

    def delete_template(self, template_id):
        answer = QMessageBox.question(
            self,
            "\u015eablonu sil",
            "Bu SMS \u015fablonu silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_template(template_id)
        self.load_data()

    def _template_rows(self):
        rows = []
        for row in range(self.table.rowCount()):
            content = self.table.item(row, 2)
            status = self.table.item(row, 1)
            rows.append((
            content.data(Qt.ItemDataRole.UserRole) if content else "",
            status.data(Qt.ItemDataRole.UserRole) if status else "",
            ))
        return rows

    def copy_templates(self):
        rows = self._template_rows()
        if not rows:
            show_error(self, "Kopyalanacak SMS \u015fablonu bulunamad\u0131.")
            return
        lines = ["SMS Icerigi\tEylem Durumu"]
        lines.extend("\t".join(row) for row in rows)
        QApplication.clipboard().setText("\n".join(lines))
        show_success(self, "SMS \u015fablonlar\u0131 panoya kopyaland\u0131.")

    def export_templates_excel(self):
        rows = self._template_rows()
        if not rows:
            show_error(self, "D\u0131\u015fa aktar\u0131lacak SMS \u015fablonu bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "SMS \u015eablonlar\u0131 Excel \u00c7\u0131kt\u0131s\u0131",
            "sms_sablonlari.xlsx",
            "Excel Dosyas\u0131 (*.xlsx)",
        )
        if not path:
            return
        try:
            import pandas as pd

            pd.DataFrame(rows, columns=["SMS Icerigi", "Eylem Durumu"]).to_excel(path, index=False)
            show_success(self, "SMS \u015fablonlar\u0131 Excel dosyas\u0131na aktar\u0131ld\u0131.")
        except Exception as exc:
            show_error(self, f"Excel \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def _templates_document(self):
        rows = "".join(
            "<tr><td>" + html.escape(content) + "</td><td>" + html.escape(status) + "</td></tr>"
            for content, status in self._template_rows()
        )
        document = QTextDocument(self)
        document.setHtml(
            "<h2>SMS Sablonlari</h2>"
            "<table border='1' cellspacing='0' cellpadding='6'>"
            "<thead><tr><th>SMS Icerigi</th><th>Eylem Durumu</th></tr></thead>"
            "<tbody>" + rows + "</tbody></table>"
        )
        return document

    def export_templates_pdf(self):
        if not self._template_rows():
            show_error(self, "PDF olarak kaydedilecek SMS \u015fablonu bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "SMS \u015eablonlar\u0131 PDF \u00c7\u0131kt\u0131s\u0131",
            "sms_sablonlari.pdf",
            "PDF Dosyas\u0131 (*.pdf)",
        )
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self._templates_document().print(printer)
            show_success(self, "SMS \u015fablonlar\u0131 PDF dosyas\u0131na kaydedildi.")
        except Exception as exc:
            show_error(self, f"PDF \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def edit_template(self, tid, name, content):
        dlg = TemplateEditDialog(name, content, self)
        if dlg.exec():
            new_name = dlg.get_name()
            new_content = dlg.get_content()
            if not new_name:
                show_error(self, "\u015eablon ad\u0131 bo\u015f olamaz.")
                return
            self.db.cursor.execute(
                "UPDATE whatsapp_templates SET name=?, content=? WHERE id=?",
                (new_name, new_content, tid),
            )
            self.db.conn.commit()
            self.load_data()
            if self.main_window:
                self.main_window.show_notification("Şablon güncellendi.", "success")
