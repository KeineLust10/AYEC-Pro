# -*- coding: utf-8 -*-

from datetime import datetime

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QLineEdit, QDoubleSpinBox

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success



class PartnerProfileDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, data=None):
        self.db = db
        self.data = data
        title = "Calisma Ortagi Duzenle" if data else "Yeni Calisma Ortagi"
        super().__init__(title, parent, width=720, height=560)
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
            box = QVBoxLayout()
            box.setSpacing(6)
            box.addWidget(lbl)
            box.addWidget(widget)
            grid.addLayout(box, row, col, 1, colspan)

        self.cmb_type = ModernComboBox(items=["Kurumsal", "Bayi", "Tedarikci"])
        self.cmb_type.setMinimumHeight(42)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Ortak adi / Unvan")
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

        self.cmb_service_type = ModernComboBox(
            items=["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Satis"]
        )
        self.cmb_service_type.setEditable(True)
        self.cmb_service_type.setMinimumHeight(42)

        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 100)
        self.spin_commission.setDecimals(2)
        self.spin_commission.setSuffix(" %")
        self.spin_commission.setFixedHeight(42)
        self.spin_commission.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_city = QLineEdit()
        self.inp_city.setPlaceholderText("Sehir")
        self.inp_city.setFixedHeight(42)
        self.inp_city.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_contract_type = ModernComboBox(
            items=["Standart Anlasma", "Premium SLA", "Parca Tedarik", "Kurumsal Servis"]
        )
        self.cmb_contract_type.setMinimumHeight(42)

        self.cmb_sla_level = ModernComboBox(
            items=["24 Saat Donus", "Ayni Gun", "48 Saat", "Haftalik Batch"]
        )
        self.cmb_sla_level.setMinimumHeight(42)

        add_field("Ortak Tipi", self.cmb_type, 0, 0)
        add_field("Ortak Adi", self.inp_name, 0, 1)
        add_field("Telefon", self.inp_phone, 1, 0)
        add_field("E-Posta", self.inp_email, 1, 1)
        add_field("Hizmet Turu", self.cmb_service_type, 2, 0)
        add_field("Komisyon Orani", self.spin_commission, 2, 1)
        add_field("Sehir", self.inp_city, 3, 0)
        add_field("Sozlesme", self.cmb_contract_type, 3, 1)
        add_field("SLA", self.cmb_sla_level, 4, 0)

        self.add_widget(card)
        self.add_cancel_button("Vazgec")
        self.add_button("Kaydet", "primary", self.save)

    def _wire_ui_signals(self):
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_service_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_contract_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_sla_level.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        d = self.data
        try:
            self.inp_name.setText(str(d["name"] or ""))
            self.inp_phone.setText(str(d["phone"] or ""))
            self.inp_email.setText(str(d["email"] or ""))
            self.inp_city.setText(str(d["city"] or ""))
            if str(d["service_type"] or ""):
                self.cmb_service_type.setCurrentText(str(d["service_type"] or ""))
            if str(d["type"] or ""):
                self.cmb_type.setCurrentText(str(d["type"] or ""))
            self.spin_commission.setValue(float(d["commission_rate"] or 0))
            if str(d["contract_type"] or ""):
                self.cmb_contract_type.setCurrentText(str(d["contract_type"] or ""))
            if str(d["sla_level"] or ""):
                self.cmb_sla_level.setCurrentText(str(d["sla_level"] or ""))
        except Exception:
            pass

    def _ensure_partner_fields(self):
        self.db.cursor.execute("PRAGMA table_info(customers)")
        existing = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for col_name, col_type in (
            ("is_partner", "INTEGER DEFAULT 0"),
            ("contract_type", "TEXT"),
            ("sla_level", "TEXT"),
        ):
            if col_name not in existing:
                self.db.cursor.execute(
                    "ALTER TABLE customers ADD COLUMN {column_name} {column_type}".format(
                        column_name=col_name,
                        column_type=col_type,
                    )
                )
        self.db.conn.commit()

    def save(self):
        name = (self.inp_name.text() or "").strip()
        if not name:
            show_error(self, "Ortak adi zorunludur.")
            return

        data = {
            "name": name,
            "phone": (self.inp_phone.text() or "").strip(),
            "email": (self.inp_email.text() or "").strip(),
            "type": self.cmb_type.currentText().strip(),
            "city": (self.inp_city.text() or "").strip(),
            "service_type": self.cmb_service_type.currentText().strip(),
            "commission_rate": float(self.spin_commission.value() or 0),
            "is_partner": 1,
            "contract_type": self.cmb_contract_type.currentText().strip(),
            "sla_level": self.cmb_sla_level.currentText().strip(),
        }

        try:
            self._ensure_partner_fields()
            if self.data and "id" in self.data.keys():
                set_clause = ", ".join([f"{k}=?" for k in data.keys()])
                values = list(data.values()) + [self.data["id"]]
                self.db.cursor.execute(f"UPDATE customers SET {set_clause} WHERE id=?", values)
                self.db.conn.commit()
            else:
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.add_customer(data)
            show_success(self, "Calisma ortagi kaydedildi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Kayit basarisiz: {e}")
