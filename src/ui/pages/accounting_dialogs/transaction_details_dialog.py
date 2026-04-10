from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFormLayout, QTableWidget, QHeaderView, QFrame,
                             QAbstractItemView, QTableWidgetItem)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.utils.theme_colors import theme_qss, tc
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.toast_notification import show_warning, show_error
from src.utils.logger import logger
import json


class TransactionDetailsDialog(PremiumDialog):
    def __init__(self, db, entry, parent=None):
        super().__init__("İşlem Detayı", parent)
        self.db = db
        self.entry = entry or {}
        self.resize(960, 620)

        layout = self.body_layout
        layout.setSpacing(14)

        body = QHBoxLayout()
        body.setSpacing(14)

        def add_row(label, value):
            from src.utils.date_utils import format_turkish_date
            l = QLabel(label)
            l.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700;"))
            
            # Format date value if it looks like YYYY-MM-DD
            display_value = str(value) if value is not None else "—"
            if label == "Tarih:" and value:
                display_value = format_turkish_date(value, "short")
                
            v = QLabel(display_value)
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            v.setStyleSheet(theme_qss("color: @selection_text; font-weight: 800;"))
            form.addRow(l, v)

        left_card = QFrame()
        left_card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 14px;"))
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setVerticalSpacing(10)

        add_row("Kaynak:", "Döviz İşlemi" if self.entry.get("source") == "currency" else "Muhasebe")
        add_row("Kayıt ID:", self.entry.get("id"))
        add_row("Tarih:", self.entry.get("date"))
        add_row("İşlem Türü:", self.entry.get("type_label"))
        if self.entry.get("tracking_no"):
            add_row("Takip No:", self.entry.get("tracking_no"))
        ref_no = self.entry.get("ref_no")
        if ref_no:
            add_row("Ref No:", ref_no)

        currency = self.entry.get("currency") or "TRY"
        amount = self.entry.get("amount", 0)
        amount_try = self.entry.get("amount_try", 0)
        rate = self.entry.get("rate", 1.0)

        if currency != "TRY":
            add_row("Tutar:", CurrencyHelper.format_amount(amount, db=self.db, currency_code=currency))
            add_row("Kur:", f"{float(rate):.4f}")
            add_row("TL Karşılığı:", CurrencyHelper.format_amount(amount_try, db=self.db, currency_code="TRY"))
        else:
            add_row("Tutar:", CurrencyHelper.format_try_for_display(amount_try, db=self.db, include_try_reference=False))

        payment_method = self.entry.get("payment_method")
        if payment_method:
            add_row("Ödeme Yöntemi:", payment_method)

        bank_account_id = self.entry.get("bank_account_id")
        if bank_account_id:
            bank_label = None
            try:
                for acc in self.db.get_bank_accounts() or []:
                    acc_id, bank, branch, acc_name, acc_no, iban, balance_val, is_active_val, created_at = acc
                    if int(acc_id) == int(bank_account_id):
                        label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
                        label_parts = [p for p in label_parts if p]
                        bank_label = " - ".join(label_parts) if label_parts else "Banka Hesabı"
                        if acc_no:
                            bank_label = f"{bank_label} ({acc_no})"
                        break
            except Exception:
                bank_label = None
            add_row("Banka Hesabı:", bank_label or str(bank_account_id))

        if self.entry.get("balance") is not None:
            add_row("Bakiye:", CurrencyHelper.format_try_for_display(float(self.entry.get('balance', 0) or 0), db=self.db))
        add_row("Durum:", self.entry.get("status"))

        cname = self.entry.get("customer_name")
        if cname:
            add_row("Müşteri:", cname)

        # Ürün/Hizmet bilgisi
        ps_id = self.entry.get("product_service_id")
        ps_type = self.entry.get("product_service_type")
        if ps_id:
            ps_label = "Stok" if ps_type == "product" else "Hizmet"
            ps_name = None
            try:
                if ps_type == "product":
                    parts = self.db.get_all_parts() or []
                    for p in parts:
                        pid = p[0] if not isinstance(p, dict) else p.get("id")
                        if int(pid) == int(ps_id):
                            ps_name = p[1] if not isinstance(p, dict) else p.get("name")
                            break
                elif ps_type == "service":
                    services = self.db.get_services_list() or []
                    for s in services:
                        sid = s[0] if not isinstance(s, dict) else s.get("id")
                        if int(sid) == int(ps_id):
                            ps_name = s[1] if not isinstance(s, dict) else s.get("name")
                            break
            except Exception:
                pass
            add_row(f"{ps_label}:", ps_name or f"ID: {ps_id}")

        left_layout.addLayout(form)

        left_btns = QHBoxLayout()
        left_btns.addStretch()

        btn_service = QPushButton("Servis Formu")
        btn_service.setFixedHeight(38)
        btn_service.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_service.setStyleSheet(theme_qss("background: @accent_pressed; color: @selection_text; font-weight: 800; border-radius: 10px; padding: 0 14px;"))
        btn_service.clicked.connect(self.open_service_form)
        left_btns.addWidget(btn_service)

        self.btn_open_360 = QPushButton("Müşteri 360°")
        self.btn_open_360.setFixedHeight(38)
        self.btn_open_360.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_360.setStyleSheet(theme_qss("background: @accent; color: @selection_text; font-weight: 800; border-radius: 10px; padding: 0 14px;"))
        self.btn_open_360.clicked.connect(self.open_customer_360)
        left_btns.addWidget(self.btn_open_360)

        left_layout.addLayout(left_btns)
        body.addWidget(left_card, 40)

        right_card = QFrame()
        right_card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 14px;"))
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(10)
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(3)
        self.items_table.setHorizontalHeaderLabels(["Stok / Detay", "Adet", "Tutar"])
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setShowGrid(False)
        self.items_table.setWordWrap(True)
        self.items_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.items_table.setStyleSheet(theme_qss("""
            QTableWidget { border: 1px solid @border; border-radius: 10px; selection-background-color: @selection_bg; selection-color: @selection_text; }
            QHeaderView::section { background: @surface_alt; border: none; border-bottom: 1px solid @border; padding: 10px; font-weight: 900; color: @text; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid @surface_alt; }
            QTableWidget::item:selected { background: @selection_bg; color: @selection_text; }
            QTableWidget::item:focus { outline: none; }
        """))
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        right_layout.addWidget(self.items_table, 1)

        body.addWidget(right_card, 60)

        layout.addLayout(body)

        self.populate_items_table()

        if not self.entry.get("customer_id"):
            self.btn_open_360.setVisible(False)
        if not self.entry.get("tracking_no"):
            btn_service.setVisible(False)

    def open_customer_360(self):
        customer_id = self.entry.get("customer_id")
        customer_name = self.entry.get("customer_name")
        if not customer_id:
            return
        try:
            from src.ui.dialogs.customer_360_dialog import Customer360Dialog
            Customer360Dialog(self.db, int(customer_id), customer_name or "", self).exec()
        except Exception:
            return

    def _parse_service_rows(self, payload):
        rows = []
        if not payload:
            return rows

        parsed_payload = payload
        if isinstance(payload, str):
            try:
                parsed_payload = json.loads(payload)
            except Exception:
                parsed_payload = payload

        if isinstance(parsed_payload, dict):
            parsed_payload = [parsed_payload]

        if isinstance(parsed_payload, (list, tuple, set)):
            for item in parsed_payload:
                if not isinstance(item, dict):
                    continue
                if item.get("kind") == "balance":
                    continue
                name = (
                    item.get("service")
                    or item.get("name")
                    or item.get("part_name")
                    or item.get("item_name")
                    or item.get("description")
                    or "Kalem"
                )
                qty = item.get("qty") or item.get("quantity") or item.get("adet") or 1
                try:
                    qty_val = int(qty)
                except Exception:
                    qty_val = 1
                try:
                    price_val = float(item.get("price", 0) or 0) * qty_val
                    price = CurrencyHelper.format_try_for_display(price_val, db=self.db, include_try_reference=False)
                except Exception:
                    price = ""
                rows.append((str(name).strip(), str(qty_val), price))
        return rows

    def _parse_description_rows(self, desc):
        import re

        rows = []
        for raw_line in str(desc or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line_l = line.lower()
            if line.startswith("Ref:") or ("cari bor" in line_l and "tahsilat" in line_l) or ("pesin" in line_l and "tahsilat" in line_l):
                continue
            match = re.match(r"^(?P<name>.+?)\s*\(x(?P<qty>\d+)\)\s*-\s*(?P<price>.+)$", line)
            if match:
                rows.append((match.group("name").strip(), match.group("qty").strip(), match.group("price").strip()))
        return rows

    def _load_related_service_rows(self):
        ref_no = self.entry.get("ref_no") or self.entry.get("tracking_no")
        if not ref_no:
            return []

        try:
            cols = set(self.db._get_table_columns("accounting")) if hasattr(self.db, "_get_table_columns") else set()
            select_cols = ["id", "description"]
            if "selected_services" in cols:
                select_cols.append("selected_services")
            where_parts = []
            params = []
            if "tracking_no" in cols:
                where_parts.append("tracking_no = ?")
                params.append(ref_no)
            if "ref_no" in cols:
                where_parts.append("ref_no = ?")
                params.append(ref_no)
            if not where_parts:
                return []

            current_id = self.entry.get("id")
            sql = f"SELECT {', '.join(select_cols)} FROM accounting WHERE ({' OR '.join(where_parts)})"
            if current_id:
                sql += " AND id <> ?"
                params.append(current_id)
            sql += " ORDER BY id DESC LIMIT 10"

            rows = self.db.cursor.execute(sql, tuple(params)).fetchall()
            for row in rows:
                record = dict(zip(select_cols, row))
                parsed_rows = self._parse_service_rows(record.get("selected_services"))
                if parsed_rows:
                    return parsed_rows
                parsed_rows = self._parse_description_rows(record.get("description"))
                if parsed_rows:
                    return parsed_rows
        except Exception:
            return []
        return []

    def populate_items_table(self):
        desc = str(self.entry.get("description") or "")
        parsed = self._parse_service_rows(self.entry.get("selected_services"))
        if not parsed:
            parsed = self._load_related_service_rows()
        if not parsed:
            parsed = self._parse_description_rows(desc)
        if not parsed and desc.strip():
            parsed.append((desc.strip(), "", ""))

        amount_try = self.entry.get("amount_try", None)
        try:
            amount_try = float(amount_try) if amount_try is not None else None
        except Exception:
            amount_try = None
        if amount_try and len(parsed) == 1:
            name, qty, price = parsed[0]
            if not price:
                parsed[0] = (name, qty, CurrencyHelper.format_try_for_display(amount_try, db=self.db, include_try_reference=False))

        self.items_table.setRowCount(0)
        self.items_table.setUpdatesEnabled(False)
        self.items_table.setSortingEnabled(False)
        for i, (name, qty, price) in enumerate(parsed):
            self.items_table.insertRow(i)
            self.items_table.setItem(i, 0, QTableWidgetItem(f"{i+1}. {name}"))
            self.items_table.setItem(i, 1, QTableWidgetItem(qty))
            self.items_table.setItem(i, 2, QTableWidgetItem(price))
        self.items_table.setUpdatesEnabled(True)
        self.items_table.setSortingEnabled(True)

        self.items_table.resizeRowsToContents()
        header_h = self.items_table.horizontalHeader().height()
        rows_h = sum(self.items_table.rowHeight(r) for r in range(self.items_table.rowCount()))
        extra = 16
        self.items_table.setFixedHeight(header_h + rows_h + extra)

    def open_service_form(self):
        tracking_no = self.entry.get("tracking_no")
        if not tracking_no:
            show_warning(self, "Takip numarası bulunamadı.")
            return
        try:
            main_window = self.window()
            if main_window and hasattr(main_window, "open_service_form"):
                main_window.open_service_form(tracking_no)
                return
            show_warning(self, "Servis formu penceresi açılamadı.")
        except Exception as e:
            show_error(self, f"Servis formu açılamadı: {e}")
