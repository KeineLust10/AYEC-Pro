# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QFrame, QPushButton, QGridLayout)
from PyQt6.QtCore import Qt
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper

class TransactionDetailDialog(BaseModernDialog):
    def __init__(self, parent, transaction_data):
        super().__init__(parent, title="İşlem Detayı", width=540, height=480)
        self.db = getattr(parent, "db", None)
        self.txn = transaction_data
        if not isinstance(self.txn, dict):
            try:
                self.txn = dict(self.txn)
            except Exception:
                self.txn = {}
        self.setup_ui()

    def _format_transaction_amount(self):
        amount = float(self.txn.get("amount", 0) or 0)
        currency_code = str(self.txn.get("currency", "TRY") or "TRY").upper()
        if currency_code == "TRY":
            return CurrencyHelper.format_from_try(
                amount,
                db=self.db,
                currency_code=CurrencyHelper.get_code(self.db),
            )
        converted = CurrencyHelper.convert_amount(
            self.db,
            amount,
            currency_code,
            CurrencyHelper.get_code(self.db),
        )
        return CurrencyHelper.format_amount(
            converted,
            db=self.db,
            currency_code=CurrencyHelper.get_code(self.db),
        )

    def setup_ui(self):
        layout = self.content_layout
        layout.setSpacing(20)

        # 1. Header Card (Amount & Type)
        header_card = QFrame()
        header_card.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
        """))
        h_layout = QVBoxLayout(header_card)
        h_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_type = QLabel(self.txn.get('type', 'İşlem'))
        lbl_type.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px; font-weight: 600; text-transform: uppercase;"))
        
        amount_color = tc("success") if self.txn.get('type') == 'Gelir' else tc("danger")
        lbl_amount = QLabel(self._format_transaction_amount())
        lbl_amount.setStyleSheet(theme_qss(f"color: {amount_color}; font-size: 32px; font-weight: 800;"))
        
        h_layout.addWidget(lbl_type, 0, Qt.AlignmentFlag.AlignHCenter)
        h_layout.addWidget(lbl_amount, 0, Qt.AlignmentFlag.AlignHCenter)
        
        layout.addWidget(header_card)

        # 2. Details Grid
        details_frame = QFrame()
        details_frame.setStyleSheet(theme_qss("""
            QFrame { background: @surface; }
            QLabel.label { color: @disabled_text; font-size: 12px; font-weight: 600; }
            QLabel.value { color: @text; font-size: 13px; font-weight: 500; }
        """))
        d_layout = QGridLayout(details_frame)
        d_layout.setVerticalSpacing(12)
        d_layout.setHorizontalSpacing(10)
        
        def add_row(row, label, value):
            label_widget = QLabel(label)
            label_widget.setProperty("class", "label")
            v = QLabel(str(value))
            v.setWordWrap(True)
            v.setProperty("class", "value")
            d_layout.addWidget(label_widget, row, 0)
            d_layout.addWidget(v, row, 1)

        add_row(0, "Tarih:", self.txn.get('date', '-'))
        add_row(1, "Kategori:", self.txn.get('category', '-'))
        add_row(2, "Açıklama:", self.txn.get('description', '-'))
        add_row(3, "Durum:", self.txn.get('status', 'Tamamlandı'))
        
        row_index = 4
        tracking_no = self.txn.get('tracking_no') or self.txn.get('ref_no')
        if tracking_no and self.db:
            add_row(row_index, "Takip No:", tracking_no)
            row_index += 1

            # Fetch device details
            try:
                dev = self.db.cursor.execute(
                    "SELECT customer_name, device_brand, device_model, vehicle_plate FROM devices WHERE tracking_no=?",
                    (tracking_no,)
                ).fetchone()
                if dev:
                    dev_dict = dict(dev) if hasattr(dev, "keys") else {}
                    dev_info = f"{dev_dict.get('device_brand', '')} {dev_dict.get('device_model', '')}".strip()
                    plate = dev_dict.get('vehicle_plate', '')
                    if plate:
                        dev_info += f" ({plate})"
                    if dev_info:
                        add_row(row_index, "Cihaz / Araç:", dev_info)
                        row_index += 1
            except Exception:
                pass

            # Fetch used parts
            try:
                parts_rows = self.db.cursor.execute(
                    "SELECT part_name, price, COALESCE(quantity, 1) FROM used_parts WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                    (tracking_no,)
                ).fetchall()
                if parts_rows:
                    part_lines = []
                    for pr in parts_rows:
                        p_name = pr[0] or "Parça"
                        p_price = float(pr[1] or 0.0)
                        p_qty = pr[2] or 1
                        part_lines.append(f"{p_name} ({p_qty} adet - {p_price:.2f} TL)")
                    parts_text = "• " + "\n• ".join(part_lines)
                    add_row(row_index, "Kullanılan Parçalar:", parts_text)
                    row_index += 1
            except Exception:
                pass
        elif self.txn.get('ref_no'):
            add_row(row_index, "Ref No:", self.txn.get('ref_no'))
            row_index += 1

        services = self.txn.get('selected_services')
        if services and not tracking_no:
            add_row(row_index, "İlgili Servisler:", services)
            row_index += 1
        
        if self.txn.get('ref_table'):
            add_row(row_index, "Referans:", f"{self.txn.get('ref_table')} (#{self.txn.get('ref_id')})")

        layout.addWidget(details_frame)
        layout.addStretch()

        # 3. Footer Actions
        btn_close = QPushButton("Kapat")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_close.clicked.connect(self.accept)
        
        layout.addWidget(btn_close)
