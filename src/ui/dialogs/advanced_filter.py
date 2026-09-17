# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QComboBox, QDateEdit, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtCore import QDate

from src.ui.widgets.modern_dialog import ModernDialog


class AdvancedFilterDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(title="Gelismis Filtreleme", parent=parent, width=400, height=440)
        self.setModal(True)
        self.set_footer_visible(False)
        self.criteria = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout()

        self.inp_customer = QLineEdit()
        self.inp_tracking = QLineEdit()
        self.inp_serial = QLineEdit()

        self.combo_fault = QComboBox()
        self.combo_fault.addItems(
            ["Tümü", "Ekran Kırık", "Şarj Almıyor", "Yazılım Hatası", "Sıvı Teması", "Genel Bakım", "Diğer"]
        )

        self.inp_status = QComboBox()
        self.inp_status.addItems(
            ["Hepsi", "Bekliyor", "Tamirde", "Tamir Edildi", "Teslim Edildi", "İptal İade"]
        )

        self.date_start = QDateEdit()
        self.date_start.setSpecialValueText(" ")
        self.date_start.setDate(QDate.currentDate().addMonths(-1))
        self.date_start.setCalendarPopup(True)

        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)

        layout.addRow("Müşteri Adı:", self.inp_customer)
        layout.addRow("Takip No:", self.inp_tracking)
        layout.addRow("Seri No:", self.inp_serial)
        layout.addRow("Arıza Kategorisi:", self.combo_fault)
        layout.addRow("Durum:", self.inp_status)
        layout.addRow("Başlangıç Tarihi:", self.date_start)
        layout.addRow("Bitiş Tarihi:", self.date_end)

        btn_filter = QPushButton("Filtrele")
        btn_filter.clicked.connect(self.apply_filter)
        btn_filter.setStyleSheet(
            "background-color: #F59E0B; color: white; padding: 10px; border-radius: 8px;"
        )
        layout.addRow(btn_filter)
        self.content_layout.addLayout(layout)

        self.combo_fault.currentIndexChanged.connect(self._sync_criteria_preview)
        self.inp_status.currentIndexChanged.connect(self._sync_criteria_preview)

    def _sync_criteria_preview(self):
        """Filtre alanları değişince önizleme kriterlerini günceller (dialog kapanmaz)."""
        self.criteria = {
            "customer": self.inp_customer.text(),
            "tracking": self.inp_tracking.text(),
            "serial": self.inp_serial.text(),
            "fault": self.combo_fault.currentText(),
            "status": self.inp_status.currentText(),
            "date_start": self.date_start.date().toString("yyyy-MM-dd"),
            "date_end": self.date_end.date().toString("yyyy-MM-dd"),
        }

    def apply_filter(self):
        self._sync_criteria_preview()
        self.accept()
