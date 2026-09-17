# -*- coding: utf-8 -*-

"""
Company Info Step - Şirket Bilgileri (v5.0)
Premium two-column form with icon-prefixed fields
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
)

from src.ui.dialogs.location_picker_dialog import LocationPickerDialog


def _fstyle():
    return """
        QLineEdit, QTextEdit {
            background: #FFFFFF;
            color: #0F172B;
            border: 1.5px solid #CBD5E1;
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 14px;
        }
        QLineEdit:focus, QTextEdit:focus {
            border-color: #6366F1;
            background: #FFFFFF;
        }
        QLineEdit::placeholder, QTextEdit::placeholder {
            color: #94A3B7;
        }
    """


class CompanyInfoStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self.installation_lat = None
        self.installation_lng = None
        self.installation_address = ""
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 28, 44, 24)
        root.setSpacing(0)

        desc = QLabel("Bu bilgiler faturalarınızda, raporlarınızda ve müşteri yazışmalarınızda kullanılacaktır.")
        desc.setStyleSheet("color:#475568; font-size:14px; border:none; background:transparent;")
        desc.setWordWrap(True)
        root.addWidget(desc)
        root.addSpacing(28)

        cols = QHBoxLayout()
        cols.setSpacing(24)
        left = QVBoxLayout()
        left.setSpacing(20)
        right = QVBoxLayout()
        right.setSpacing(20)

        left.addLayout(self._fgroup("🏢", "Şirket Adı", True, "company_name", "Örn: AYEC Pro Ltd. Şti."))
        left.addLayout(self._fgroup("👤", "Yetkili Kişi", True, "authorized_person", "Örn: Ahmet Yılmaz"))
        left.addLayout(self._fgroup("📞", "Telefon", True, "phone", "Örn: 0555 123 45 67"))
        left.addLayout(self._fgroup("✉️", "E-posta", True, "email", "Örn: info@sirket.com"))

        right.addLayout(self._fgroup("🏛️", "Vergi Dairesi", False, "tax_office", "Örn: Kadıköy VD"))
        right.addLayout(self._fgroup("#️⃣", "Vergi Numarası", False, "tax_number", "Örn: 1234567890"))

        addr_lbl = QLabel("📍  Adres")
        addr_lbl.setStyleSheet("color:#334155; font-size:13px; font-weight:600; background:transparent; border:none;")
        right.addWidget(addr_lbl)

        self.address = QTextEdit()
        self.address.setPlaceholderText("Örn: Atatürk Cad. No:123, Kadıköy / İstanbul")
        self.address.setFixedHeight(90)
        self.address.setStyleSheet(_fstyle())
        right.addWidget(self.address)

        self.location_button = QPushButton("Haritadan Kurulum Konumu Sec *")
        self.location_button.setMinimumHeight(44)
        self.location_button.setStyleSheet(
            "QPushButton{background:#4F46E5;color:white;border:none;border-radius:10px;"
            "font-size:13px;font-weight:600;padding:10px;}"
            "QPushButton:hover{background:#4338CA;}"
        )
        self.location_button.clicked.connect(self._pick_location)
        right.addWidget(self.location_button)
        self.location_status = QLabel("Konum secimi zorunludur.")
        self.location_status.setWordWrap(True)
        self.location_status.setStyleSheet(
            "color:#DC2626;font-size:11px;background:transparent;border:none;"
        )
        right.addWidget(self.location_status)
        right.addStretch()

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        root.addLayout(cols)
        root.addStretch()

        note = QLabel("★ ile işaretli alanlar zorunludur")
        note.setStyleSheet("color:#64748A; font-size:11px; font-style:italic; border:none; background:transparent;")
        root.addWidget(note)

    def _fgroup(self, icon, label, required, attr, placeholder):
        vbox = QVBoxLayout()
        vbox.setSpacing(7)
        row = QHBoxLayout()
        il = QLabel(icon)
        il.setStyleSheet("font-size:13px; background:transparent; border:none;")
        tl = QLabel(("★  " if required else "") + label)
        tl.setStyleSheet(
            f"color:{'#4F46E5' if required else '#475568'}; font-size:13px; font-weight:600; background:transparent; border:none;"
        )
        row.addWidget(il)
        row.addWidget(tl)
        row.addStretch()
        vbox.addLayout(row)
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setMinimumHeight(44)
        f.setStyleSheet(_fstyle())
        setattr(self, attr, f)
        vbox.addWidget(f)
        return vbox

    def _err(self, msg):
        if self.wizard and hasattr(self.wizard, "show_toast"):
            self.wizard.show_toast(msg, "warning")

    def _pick_location(self):
        dialog = LocationPickerDialog(
            self,
            current_lat=self.installation_lat,
            current_lng=self.installation_lng,
        )
        dialog.location_selected.connect(self._location_selected)
        dialog.exec()

    def _location_selected(self, lat, lng, address):
        self.installation_lat = float(lat)
        self.installation_lng = float(lng)
        self.installation_address = str(address or "").strip()
        if self.installation_address and not self.address.toPlainText().strip():
            self.address.setPlainText(self.installation_address)
        self.location_status.setText(
            f"Konum secildi: {self.installation_lat:.6f}, {self.installation_lng:.6f}"
        )
        self.location_status.setStyleSheet(
            "color:#059669;font-size:11px;background:transparent;border:none;"
        )

    def validate(self):
        for f, m in [
            (self.company_name, "Lütfen şirket adını girin."),
            (self.authorized_person, "Lütfen yetkili kişi adını girin."),
        ]:
            if not f.text().strip():
                self._err(m)
                f.setFocus()
                return False

        ph = self.phone.text().strip()
        if not ph:
            self._err("Lütfen telefon numarasını girin.")
            self.phone.setFocus()
            return False
        digits = re.sub(r"[\s\-\(\)]", "", ph)
        if not re.match(r"^0[0-9]{9,10}$", digits):
            self._err("Geçerli telefon girin. Örnek: 05551234567 veya 0555 123 45 67")
            self.phone.setFocus()
            return False

        em = self.email.text().strip()
        if not em:
            self._err("Lütfen e-posta adresini girin.")
            self.email.setFocus()
            return False
        if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", em):
            self._err("Geçerli e-posta girin. Örnek: info@sirket.com")
            self.email.setFocus()
            return False
        if self.installation_lat is None or self.installation_lng is None:
            self._err("Lutfen haritadan kurulum konumunu secin.")
            self.location_button.setFocus()
            return False
        return True

    def get_data(self):
        return {
            "company_info": {
                "company_name": self.company_name.text().strip(),
                "authorized_person": self.authorized_person.text().strip(),
                "phone": self.phone.text().strip(),
                "email": self.email.text().strip(),
                "tax_office": self.tax_office.text().strip(),
                "tax_number": self.tax_number.text().strip(),
                "address": self.address.toPlainText().strip(),
                "installation_lat": self.installation_lat,
                "installation_lng": self.installation_lng,
                "installation_address": self.installation_address,
            }
        }
