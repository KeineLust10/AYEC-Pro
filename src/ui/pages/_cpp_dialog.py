# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QFrame, QGridLayout, QDoubleSpinBox
)
from datetime import datetime
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.modern_dialog import ModernDialog


class PartnerDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, data=None):
        self.db = db
        self.data = data
        title = "Çalışma Ortağı Düzenle" if data else "Yeni Çalışma Ortağı"
        super().__init__(title, parent, width=720, height=520)
        self.setup_content()
        if data:
            self.load_data()

    def setup_content(self):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        def add_field(label_text, widget, row, col, colspan=1):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: 700;"))
            v = QVBoxLayout(); v.setSpacing(6)
            v.addWidget(lbl); v.addWidget(widget)
            grid.addLayout(v, row, col, 1, colspan)

        self.cmb_type = ModernComboBox(items=["Kurumsal", "Bayi", "Tedarikçi"])
        self.cmb_type.setMinimumHeight(42)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Ortak adı / Ünvan")
        self.inp_name.setFixedHeight(42)
        self.inp_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("05xx ...")
        self.inp_phone.setFixedHeight(42)
        self.inp_phone.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("email@example.com")
        self.inp_email.setFixedHeight(42)
        self.inp_email.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_service_type = ModernComboBox(items=["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Satış"])
        self.cmb_service_type.setEditable(True); self.cmb_service_type.setMinimumHeight(42)

        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 100); self.spin_commission.setDecimals(2); self.spin_commission.setSuffix(" %")
        self.spin_commission.setFixedHeight(42); self.spin_commission.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_city = QLineEdit()
        self.inp_city.setPlaceholderText("Şehir")
        self.inp_city.setFixedHeight(42); self.inp_city.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        add_field("Ortak Tipi", self.cmb_type, 0, 0)
        add_field("Ortak Adı", self.inp_name, 0, 1)
        add_field("Telefon", self.inp_phone, 1, 0)
        add_field("E-Posta", self.inp_email, 1, 1)
        add_field("Hizmet Türü", self.cmb_service_type, 2, 0)
        add_field("Komisyon Oranı", self.spin_commission, 2, 1)
        add_field("Şehir", self.inp_city, 3, 0, 2)

        self.add_widget(card)
        self.add_cancel_button("Vazgeç")
        self.add_button("Kaydet", "primary", self.save)

    def _wire_ui_signals(self):
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_service_type.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        d = self.data
        try:
            self.inp_name.setText(str(d.get("name") or ""))
            self.inp_phone.setText(str(d.get("phone") or ""))
            self.inp_email.setText(str(d.get("email") or ""))
            self.inp_city.setText(str(d.get("city") or ""))
            stype = str(d.get("service_type") or "")
            if stype: self.cmb_service_type.setCurrentText(stype)
            ctype = str(d.get("type") or "")
            if ctype: self.cmb_type.setCurrentText(ctype)
            self.spin_commission.setValue(float(d.get("commission_rate") or 0))
        except Exception: pass

    def save(self):
        name = (self.inp_name.text() or "").strip()
        if not name:
            show_error(self, "Ortak adı zorunludur.")
            return
        data = {
            "name": name,
            "phone": (self.inp_phone.text() or "").strip(),
            "email": (self.inp_email.text() or "").strip(),
            "type": self.cmb_type.currentText().strip(),
            "city": (self.inp_city.text() or "").strip(),
            "service_type": self.cmb_service_type.currentText().strip(),
            "commission_rate": float(self.spin_commission.value() or 0),
        }
        try:
            if self.data and "id" in self.data.keys():
                set_clause = ", ".join([f"{k}=?" for k in data.keys()])
                values = list(data.values()) + [self.data["id"]]
                self.db.cursor.execute(f"UPDATE customers SET {set_clause} WHERE id=?", values)
                self.db.conn.commit()
            else:
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.add_customer(data)
            show_success(self, "Çalışma ortağı kaydedildi.")
            self.accept()
        except Exception as e: show_error(self, f"Kayıt başarısız: {e}")
