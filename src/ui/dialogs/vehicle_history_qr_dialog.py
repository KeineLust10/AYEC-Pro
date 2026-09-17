# -*- coding: utf-8 -*-

import urllib.parse
import urllib.request

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QHBoxLayout, QWidget, QHeaderView, QAbstractItemView
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_info, show_warning


class VehicleHistoryQrDialog(ModernDialog):
    def __init__(self, db, plate, parent=None):
        self.db = db
        self.plate = str(plate or "").strip().upper()
        super().__init__(f"Araç Geçmişi - {self.plate or 'Araç'}", parent, width=1080, height=760)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        wrapper = QWidget()
        root = QVBoxLayout(wrapper)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(16)

        left = QVBoxLayout()
        title = QLabel("QR Paylaşımı ve Araç Geçmişi")
        title.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text;"))
        subtitle = QLabel("Bakım ve servis geçmişi bu araç için tek ekranda gösterilir.")
        subtitle.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        self.lbl_token = QLabel("-")
        self.lbl_token.setStyleSheet(theme_qss("font-size: 13px; color: @accent; font-weight: 700;"))
        btn_copy = QPushButton("QR Bağlantısını Kopyala")
        btn_copy.clicked.connect(self._copy_share_link)
        btn_copy.setStyleSheet(theme_qss("background: @accent; color: @selection_text; border-radius: 8px; padding: 8px 14px;"))
        left.addWidget(title)
        left.addWidget(subtitle)
        left.addWidget(self.lbl_token)
        left.addWidget(btn_copy, 0, Qt.AlignmentFlag.AlignLeft)
        left.addStretch()

        right = QVBoxLayout()
        self.lbl_qr = QLabel("QR hazırlanıyor...")
        self.lbl_qr.setFixedSize(220, 220)
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_qr.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 16px; background: @surface_alt; color: @text_muted;"))
        right.addWidget(self.lbl_qr)

        top.addLayout(left, 1)
        top.addLayout(right)
        root.addLayout(top)

        self.table_maintenance = QTableWidget()
        self.table_maintenance.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_maintenance.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_maintenance.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_maintenance.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_maintenance.setColumnCount(5)
        self.table_maintenance.setHorizontalHeaderLabels(["Bakım Tarihi", "Sonraki Bakım", "Muayene", "Not", "Servis No"])
        self.table_maintenance.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_maintenance.verticalHeader().setVisible(False)
        self.table_maintenance.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        root.addWidget(self.table_maintenance, 1)

        self.table_services = QTableWidget()
        self.table_services.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_services.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_services.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_services.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_services.setColumnCount(6)
        self.table_services.setHorizontalHeaderLabels(["Takip No", "Giriş", "Durum", "Onay", "Arıza", "İşçilik"])
        self.table_services.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_services.verticalHeader().setVisible(False)
        self.table_services.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        root.addWidget(self.table_services, 1)

        self.add_widget(wrapper)
        self.add_cancel_button("Kapat")

    def _load_data(self):
        maintenance_rows, service_rows = self.db.get_vehicle_history_snapshot(self.plate)
        token = ""
        if maintenance_rows:
            try:
                token = str(maintenance_rows[0]["qr_token"] or "")
            except Exception:
                token = ""
        self.lbl_token.setText(f"Paylaşım Kodu: {token or 'Henüz yok'}")
        self._render_qr(token or self.plate or "AYEC")

        self.table_maintenance.setRowCount(0)
        for row_idx, row in enumerate(maintenance_rows):
            self.table_maintenance.insertRow(row_idx)
            values = [
                str(row["service_date"] or ""),
                str(row["next_maintenance_date"] or ""),
                str(row["inspection_due_date"] or ""),
                str(row["notes"] or ""),
                str(row["linked_device_tracking_no"] or ""),
            ]
            for col_idx, value in enumerate(values):
                self.table_maintenance.setItem(row_idx, col_idx, QTableWidgetItem(value))

        self.table_services.setRowCount(0)
        for row_idx, row in enumerate(service_rows):
            self.table_services.insertRow(row_idx)
            values = [
                str(row["tracking_no"] or ""),
                str(row["entry_date"] or ""),
                str(row["status"] or ""),
                str(row["approval_status"] or ""),
                str(row["fault_description"] or ""),
                str(row["labor_cost"] or ""),
            ]
            for col_idx, value in enumerate(values):
                self.table_services.setItem(row_idx, col_idx, QTableWidgetItem(value))

    def _copy_share_link(self):
        token_text = self.lbl_token.text().replace("Paylaşım Kodu:", "").strip()
        if not token_text:
            show_warning(self, "Paylaşım kodu henüz oluşmadı.")
            return
        QApplication.clipboard().setText(f"ayec://vehicle-history/{token_text}")
        show_info(self, "Paylaşım bağlantısı panoya kopyalandı.")

    def _render_qr(self, payload):
        try:
            data_url = (
                "https://api.qrserver.com/v1/create-qr-code/?size=220x220&data="
                + urllib.parse.quote(str(payload))
            )
            data = urllib.request.urlopen(data_url, timeout=6).read()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.lbl_qr.setPixmap(pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                return
        except Exception:
            pass
        self.lbl_qr.setText(f"QR hazır değil\n{payload}")
