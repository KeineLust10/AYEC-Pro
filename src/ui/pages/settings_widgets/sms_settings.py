# -*- coding: utf-8 -*-

"""
SMS Settings Widget
SMS ayarlari ve sablon yonetimi widget'lari.
"""

import html

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
from PyQt6.QtGui import QColor, QFont, QTextDocument
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter

from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success



class SMSSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """SMS Settings Tab"""

    def __init__(self, db, main_window=None, use_internal_scroll=True):
        super().__init__()
        self.setObjectName("part9_sms_settings")
        self.setStyleSheet(
            "QWidget#part9_sms_settings { background-color: #0e1321; color: #dee2f6; } "
            "QWidget#part9_sms_settings QLabel { color: #c2c6d6; }"
        )
        self.db = db
        self.main_window = main_window
        fallback_font = QFont()
        fallback_font.setFamilies(["Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.setup_ui(use_internal_scroll=use_internal_scroll)
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self, use_internal_scroll=True):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        if use_internal_scroll:
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setStyleSheet("QScrollArea { background: #0e1321; border: 0; } QWidget { background: #0e1321; }")
            scroll.setWidget(body)
            root.addWidget(scroll)
        else:
            root.addWidget(body)

        title_row = QHBoxLayout()
        title = QLabel("SMS Servis Sa\u011flay\u0131c\u0131 & API Ayarlar\u0131")
        title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
        title.setStyleSheet("color: #dee2f6; background: transparent;")
        title_row.addWidget(title)
        title_row.addStretch()
        provider = QLabel("SA\u011eLAYICI: NetGSM / Ileti Merkezi    \u2022    KALAN KRED\u0130: --")
        provider.setStyleSheet("color: #4cd7f6; background: #161b2a; border: 1px solid #252a39; border-radius: 5px; padding: 7px 10px; font: 700 10px 'Segoe UI', Arial;")
        title_row.addWidget(provider)
        layout.addLayout(title_row)

        info = QLabel("SMS g\u00f6nderebilmek i\u00e7in servis API kullan\u0131c\u0131 ad\u0131 ve \u015fifrenizi girin. Onayl\u0131 SMS ba\u015fl\u0131\u011f\u0131 operat\u00f6r onay\u0131ndan sonra aktifle\u015fir.")
        info.setWordWrap(True)
        info.setStyleSheet("background: #161b2a; color: #c2c6d6; padding: 12px; border: 1px solid #252a39; border-radius: 5px;")
        layout.addWidget(info)

        cred_card = QFrame()
        cred_card.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }")
        cred_layout = QGridLayout(cred_card)
        cred_layout.setContentsMargins(12, 12, 12, 12)
        cred_layout.setHorizontalSpacing(10)
        cred_layout.setVerticalSpacing(6)

        def add_field(label, column, password=False):
            field = QWidget(cred_card)
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            caption = QLabel(label)
            caption.setStyleSheet("color: #c2c6d6; background: transparent; font: 700 9px 'Segoe UI', Arial;")
            field_layout.addWidget(caption)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            edit.setMinimumHeight(36)
            edit.setStyleSheet("QLineEdit { background: #0b1220; color: #dce4f2; border: 1px solid #26334a; border-radius: 4px; padding: 7px 9px; selection-background-color: #2563eb; }")
            row.addWidget(edit, 1)
            if password:
                toggle = QPushButton("G\u00f6ster")
                toggle.setFixedHeight(36)
                toggle.setStyleSheet("QPushButton { background: #252a39; color: #c2c6d6; border: 1px solid #424754; border-radius: 4px; padding: 0 8px; }")
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
        status_label.setStyleSheet("color: #c2c6d6; background: transparent; font: 700 9px 'Segoe UI', Arial;")
        status_layout.addWidget(status_label)
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Pasif", "Aktif (Canl\u0131 \u0130letim)"])
        self.cmb_status.setFixedHeight(36)
        self.cmb_status.setStyleSheet("QComboBox { background: #0b1220; color: #dce4f2; border: 1px solid #26334a; border-radius: 4px; padding: 6px 9px; } QComboBox QAbstractItemView { background: #111a2a; color: #dce4f2; selection-background-color: #2563eb; }")
        status_layout.addWidget(self.cmb_status)
        cred_layout.addWidget(status_field, 0, 3)
        for column in range(4):
            cred_layout.setColumnStretch(column, 1)

        action_row = QHBoxLayout()
        safety = QLabel("API anahtarlar\u0131 g\u00fcvenli ayar deposunda AES-256 ile korunur.")
        safety.setStyleSheet("color: #8c909f; background: transparent; font-size: 10px;")
        action_row.addWidget(safety)
        action_row.addStretch()
        self.btn_test_sms = QPushButton("Test SMS G\u00f6nder")
        self.btn_test_sms.setFixedHeight(34)
        self.btn_test_sms.setStyleSheet("QPushButton { background: #111a2a; color: #49d8ed; border: 1px solid #26334a; border-radius: 5px; padding: 0 12px; font-weight: 600; } QPushButton:hover { background: #19273b; }")
        self.btn_test_sms.clicked.connect(self.test_sms)
        action_row.addWidget(self.btn_test_sms)
        btn_update_cred = QPushButton("G\u00dcNCELLE & KAYDET")
        btn_update_cred.setFixedHeight(36)
        btn_update_cred.setStyleSheet("QPushButton { background: #4edea3; color: #071326; border: 1px solid #4edea3; border-radius: 5px; padding: 0 14px; font-weight: 700; } QPushButton:hover { background: #36c98f; }")
        btn_update_cred.clicked.connect(self.save_credentials)
        action_row.addWidget(btn_update_cred)
        cred_layout.addLayout(action_row, 1, 0, 1, 4)
        layout.addWidget(cred_card)

        loop_head = QHBoxLayout()
        loop_title = QLabel("SMS G\u00d6NDER\u0130M D\u00d6NG\u00dc AYARLARI")
        loop_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        loop_title.setStyleSheet("color: #dee2f6; background: transparent;")
        loop_head.addWidget(loop_title)
        loop_head.addStretch()
        loop_badge = QLabel("CRON OTOMASYONU DEVREDE    \u2022    D\u00f6ng\u00fc taramas\u0131: 15 dk")
        loop_badge.setStyleSheet("color: #4edea3; background: #161b2a; border-radius: 4px; padding: 6px 8px; font: 700 9px 'Segoe UI', Arial;")
        loop_head.addWidget(loop_badge)
        layout.addLayout(loop_head)
        description = QLabel("Belirli durum kodlar\u0131na g\u00f6re otomatik g\u00f6nderilen SMS'lerin g\u00fcn d\u00f6ng\u00fcs\u00fcn\u00fc ve kullan\u0131lacak \u015fablonu belirleyin.")
        description.setStyleSheet("color: #8c909f; background: transparent; font-size: 10px;")
        layout.addWidget(description)

        self._loop_template_widgets = {}
        self._loop_active_widgets = {}
        self._loop_spin_widgets = {}
        self.db.cursor.execute("SELECT name FROM whatsapp_templates ORDER BY id")
        template_names = [row[0] for row in self.db.cursor.fetchall() if row and row[0]]
        loop_grid = QGridLayout()
        loop_grid.setHorizontalSpacing(8)
        loop_grid.setVerticalSpacing(8)

        def create_card(label, setting_key, code):
            card = QFrame()
            card.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(9, 9, 9, 9)
            card_layout.setSpacing(6)
            title_row = QHBoxLayout()
            dot = QLabel("\u2022")
            dot.setStyleSheet("color: #4cd7f6; background: transparent; font-size: 14px;")
            title_row.addWidget(dot)
            name = QLabel(label)
            name.setStyleSheet("color: #dee2f6; background: transparent; font: 700 9px 'Segoe UI', Arial;")
            title_row.addWidget(name)
            title_row.addStretch()
            active = QCheckBox()
            active.setChecked(True)
            active.setObjectName(f"sms_loop_active_{setting_key}")
            active.setToolTip(f"{label} SMS d\u00f6ng\u00fcs\u00fcn\u00fc etkinle\u015ftir")
            active.setStyleSheet("QCheckBox::indicator { width: 25px; height: 14px; border-radius: 7px; background: #303444; } QCheckBox::indicator:checked { background: #4d8eff; }")
            title_row.addWidget(active)
            card_layout.addLayout(title_row)
            days_label = QLabel("D\u00f6ng\u00fc Aral\u0131\u011f\u0131")
            days_label.setStyleSheet("color: #8c909f; background: transparent; font-size: 9px;")
            days_row = QHBoxLayout()
            days_row.setContentsMargins(0, 0, 0, 0)
            days_row.addWidget(days_label)
            days_row.addStretch()
            spin = QSpinBox()
            spin.setRange(0, 30)
            spin.setSuffix(" g\u00fcn")
            spin.setFixedHeight(36)
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            spin.setStyleSheet("QSpinBox { background: #090e1c; color: #adc6ff; border: 0; border-radius: 4px; padding: 0 8px; font-size: 16px; font-weight: 700; }")
            spin.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            days_row.addWidget(spin)
            card_layout.addLayout(days_row)
            template_label = QLabel("BA\u011eLI \u015eABLON")
            template_label.setStyleSheet("color: #8c909f; background: transparent; font: 700 8px 'Segoe UI', Arial;")
            card_layout.addWidget(template_label)
            combo = QComboBox()
            combo.addItems(template_names or ["\u015eablon tan\u0131ml\u0131 de\u011fil"])
            combo.setFixedHeight(30)
            combo.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
            card_layout.addWidget(combo)
            code_row = QHBoxLayout()
            code_label = QLabel(f"KOD: #STA-{code}")
            code_label.setStyleSheet("color: #9ba8bc; background: transparent; font: 700 9px 'Segoe UI', Arial;")
            code_row.addWidget(code_label)
            code_row.addStretch()
            quick = QPushButton("Save")
            quick.setFixedSize(30, 30)
            quick.setToolTip(f"{label} d\u00f6ng\u00fcs\u00fcn\u00fc kaydet")
            quick.setStyleSheet("QPushButton { background: #4d8eff; color: #00285d; border: 0; border-radius: 4px; font-weight: 700; }")
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
        self.lbl_loop_status.setStyleSheet("color: #9ba8bc; background: transparent; font-size: 10px;")
        save_loop_row.addWidget(self.lbl_loop_status)
        save_loop_row.addStretch()
        btn_update_loop = QPushButton("T\u00dcM D\u00d6NG\u00dc AYARLARINI G\u00dcNCELLE")
        btn_update_loop.setFixedHeight(36)
        btn_update_loop.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_update_loop.clicked.connect(self.save_loops)
        save_loop_row.addWidget(btn_update_loop)
        layout.addLayout(save_loop_row)

        metric_row = QHBoxLayout()
        metric_specs = [("BUG\u00dcN G\u00d6NDER\u0130LEN SMS", "--", "G\u00f6nderim ge\u00e7mi\u015fi"), ("KUYRUKTA BEKLEYENLER", "--", "Kuyruk API ba\u011flant\u0131s\u0131 yok"), ("ORTALAMA \u0130LET\u0130M GEC\u0130KMES\u0130", "--", "Operat\u00f6r DLR verisi yok")]
        self.metric_values = []
        for heading, value, detail in metric_specs:
            card = QFrame()
            card.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 9, 10, 9)
            label = QLabel(heading)
            label.setStyleSheet("color: #8c909f; background: transparent; font: 700 8px 'Segoe UI', Arial;")
            number = QLabel(value)
            number.setStyleSheet("color: #4cd7f6; background: transparent; font-size: 21px; font-weight: 700;")
            note = QLabel(detail)
            note.setStyleSheet("color: #c2c6d6; background: transparent; font-size: 9px;")
            card_layout.addWidget(label)
            card_layout.addWidget(number)
            card_layout.addWidget(note)
            metric_row.addWidget(card, 1)
            self.metric_values.append(number)
        layout.addLayout(metric_row)
        for label_widget in body.findChildren(QLabel):
            label_font = label_widget.font()
            label_font.setFamilies(["Segoe UI", "Arial"])
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

        self.spn_repaired.setValue(int(self.db.get_setting("loop_repaired", "0")))
        self.spn_approval.setValue(int(self.db.get_setting("loop_approval", "0")))
        self.spn_parts.setValue(int(self.db.get_setting("loop_parts", "0")))
        self.spn_testing.setValue(int(self.db.get_setting("loop_testing", "0")))
        self.spn_done.setValue(int(self.db.get_setting("loop_done", "0")))
        for key, combo in self._loop_template_widgets.items():
            saved = self.db.get_setting(f"loop_template_{key}", "")
            index = combo.findText(saved)
            if index >= 0:
                combo.setCurrentIndex(index)
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
        vars_info.setStyleSheet("color: #8c909f; font-size: 12px; font-style: italic;")
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

    def __init__(self, db, main_window=None):
        super().__init__()
        self.setObjectName("part9_sms_templates")
        self.setStyleSheet(
            "QWidget#part9_sms_templates { background-color: #0e1321; color: #dee2f6; } "
            "QWidget#part9_sms_templates QLabel { color: #c2c6d6; }"
        )
        self.db = db
        self.main_window = main_window
        fallback_font = QFont()
        fallback_font.setFamilies(["Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.setup_ui()
        self.init_default_templates()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        variables = QFrame()
        variables.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #252a39; border-radius: 5px; }")
        variables.setMaximumHeight(150)
        variables_layout = QVBoxLayout(variables)
        variables_layout.setContentsMargins(11, 9, 11, 9)
        variables_layout.setSpacing(6)
        variables_header = QHBoxLayout()
        variables_title = QLabel("Dinamik De\u011fi\u015fken Havuzu")
        variables_title.setStyleSheet("color: #dee2f6; font-weight: 700; background: transparent;")
        variables_header.addWidget(variables_title)
        variables_header.addWidget(QLabel("(\u015eablon kurgusunda panoya kopyalamak i\u00e7in t\u0131klay\u0131n)"))
        variables_header.addStretch()
        encoding_badge = QLabel("GSM 7-Bit  &  UTF-8 Uyumlu")
        encoding_badge.setStyleSheet("color: #4edea3; background: transparent; font: 700 9px 'Segoe UI', Arial;")
        variables_header.addWidget(encoding_badge)
        variables_layout.addLayout(variables_header)
        token_row = QHBoxLayout()
        token_row.setSpacing(5)
        tokens = [
            ("{musteri}", "Ad Soyad"), ("{tutar}", "Hizmet Bedeli"),
            ("{bakiye}", "Kalan Cari"), ("{cihaz}", "Marka & Model"),
            ("{servis_no}", "Kay\u0131t Barkodu"), ("{randevu_araligi}", "Tarih / Saat"),
            ("{takip_linki}", "K\u0131sa URL"), ("{odeme_linki}", "Online \u00d6deme"),
        ]
        self.token_buttons = []
        for token, description in tokens:
            button = QPushButton(f"{token}  {description}  \u25a1")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip("De\u011fi\u015fkeni panoya kopyala")
            button.setStyleSheet("QPushButton { color: #c2c6d6; background: transparent; border: 0; padding: 4px 5px; font-size: 9px; } QPushButton:hover { background: #252a39; border-radius: 3px; }")
            button.clicked.connect(lambda checked=False, value=token: QApplication.clipboard().setText(value))
            token_row.addWidget(button)
            self.token_buttons.append(button)
        token_row.addStretch()
        variables_layout.addLayout(token_row)
        layout.addWidget(variables)

        header = QHBoxLayout()
        title_column = QVBoxLayout()
        title = QLabel("SMS \u015eablonlar\u0131")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #dee2f6; background: transparent;")
        title_column.addWidget(title)
        subtitle = QLabel("Otomatik ve manuel SMS g\u00f6nderim d\u00f6ng\u00fclerine ait \u015fablon parametreleri")
        subtitle.setStyleSheet("color: #8c909f; background: transparent; font-size: 9px;")
        title_column.addWidget(subtitle)
        header.addLayout(title_column)
        header.addStretch()

        self.btn_copy = QPushButton("KOPYALA")
        self.btn_copy.clicked.connect(self.copy_templates)
        self.btn_excel = QPushButton("EXCEL")
        self.btn_excel.clicked.connect(self.export_templates_excel)
        self.btn_pdf = QPushButton("PDF")
        self.btn_pdf.clicked.connect(self.export_templates_pdf)
        for button in (self.btn_copy, self.btn_excel, self.btn_pdf):
            button.setFixedHeight(32)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            header.addWidget(button)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("\u015eablon veya eylem ara...")
        self.inp_search.setFixedWidth(215)
        self.inp_search.setFixedHeight(32)
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.inp_search.textChanged.connect(self.load_data)
        header.addWidget(self.inp_search)

        self.btn_add_template = QPushButton("+ Yeni \u015eablon Ekle")
        self.btn_add_template.setFixedHeight(32)
        self.btn_add_template.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_add_template.clicked.connect(self.add_template)
        header.addWidget(self.btn_add_template)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "NO", "EYLEM / TET\u0130KLEY\u0130C\u0130 DURUM", "SMS \u0130\u00c7ER\u0130\u011e\u0130 VE D\u0130NAM\u0130K ALANLAR",
            "UZUNLUK / KRED\u0130", "DURUM", "\u0130\u015eLEMLER"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 44)
        self.table.setColumnWidth(5, 180)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(68)
        self.table.setAlternatingRowColors(False)
        self.table.setWordWrap(True)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { border: 1px solid #424754; background: #161b2a; color: #dee2f6; } "
            "QHeaderView::section { background: #090e1c; color: #c2c6d6; border: 0; padding: 8px; font-weight: bold; font-size: 9px; } "
            "QTableWidget::item { color: #dee2f6; background: #161b2a; border-bottom: 1px solid #252a39; padding: 7px; }"
        ))
        self.table.setMinimumHeight(350)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.table, 1)

        self.footer_label = QLabel("Kay\u0131tlar listeleniyor.")
        self.footer_label.setStyleSheet("color: #8c909f; font-size: 10px; background: transparent;")
        layout.addWidget(self.footer_label)
        self.table.setFont(QFont("Segoe UI", 9))
        self.table.horizontalHeader().setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for widget in self.findChildren(QWidget):
            widget_font = widget.font()
            widget_font.setFamilies(["Segoe UI", "Arial"])
            widget.setFont(widget_font)

    def init_default_templates(self):
        self.db.cursor.execute("SELECT COUNT(*) FROM whatsapp_templates")
        if self.db.cursor.fetchone()[0] == 0:
            defaults = [
                ("MANUEL BORC EKLEME", "Sayin {musteri}: {tutar} TL borc sisteme islenmistir. Kalan borcunuz: {bakiye} TL."),
                ("RANDEVU IPTAL SMS MUSTERIYE", "Sayin {musteri}: {randevu_araligi} tarihli randevunuz iptal edilmistir."),
                ("MOBIL ONAY", "Sayin {musteri}: lutfen cihazinizin tamiri icin belirlenen tutari onaylayiniz. Link: {link}"),
                ("RANDEVU OLUSTURULDU", "Sayin {musteri}: {randevu} tarihli randevunuz olusturulmustur."),
                ("PERIYODIK BAKIM", "Sayin {musteri}: {serino} nolu urununuzun bakim gunu gelmistir."),
            ]
            for name, content in defaults:
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
                item.setForeground(QColor("#8c909f" if column in (0, 3) else "#4edea3" if column == 4 else "#dee2f6"))
                if column == 2:
                    item.setToolTip(value)
                item.setFont(QFont("Segoe UI", 9))
                self.table.setItem(row, column, item)

            action_host = QWidget()
            action_layout = QHBoxLayout(action_host)
            action_layout.setContentsMargins(4, 4, 4, 4)
            action_layout.setSpacing(6)
            btn_edit = QPushButton("Düzenle")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
            btn_edit.clicked.connect(lambda checked, i=tid, n=name, c=content: self.edit_template(i, n, c))
            btn_send = QPushButton("\u25b6")
            btn_send.setToolTip("SMS \u015fablon metnini \u00f6nizle")
            btn_send.setFixedWidth(32)
            btn_send.setStyleSheet("QPushButton { background: #252a39; color: #4cd7f6; border: 1px solid #303444; border-radius: 4px; }")
            btn_send.clicked.connect(lambda checked=False, n=name, c=content: self.preview_template(n, c))
            btn_delete = QPushButton("Sil")
            btn_delete.setFixedWidth(42)
            btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_delete.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
            btn_delete.clicked.connect(lambda checked=False, i=tid: self.delete_template(i))
            btn_edit.setFixedWidth(80)
            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_send)
            action_layout.addWidget(btn_delete)
            self.table.setCellWidget(row, 5, action_host)

        self.footer_label.setText(f"\u2713 Toplam {self.table.rowCount()} Aktif SMS \u015fablonu listeleniyor    \u2022    GSM Karakter Standard\u0131: UTF-8 / T\u00fcrk\u00e7e Destekli")

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
                content.text() if content else "",
                status.text() if status else "",
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
