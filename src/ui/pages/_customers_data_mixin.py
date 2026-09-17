# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QTableWidgetItem, QWidget, QHBoxLayout, QPushButton

from src.utils.logger import logger
from src.utils.date_formatter import format_date
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import tc, qc, theme_qss
from src.utils.performance_monitor import perf_span
from src.ui.pages.customers_page_parts import CustomerWorker

class CustomersDataMixin:
    """Data loading and table population logic for CustomersPage."""

    def refresh_data(self):
        """Müşteri verisini asenkron worker ile yükle"""
        logger.debug("CustomersPage.refresh_data called")
        try:
            self.table.setRowCount(0)
            self.lbl_total.setText("⏳ Yükleniyor...")
            self.btn_prev.setEnabled(False)
            self.btn_next.setEnabled(False)

            if self.worker is not None and self.worker.isRunning():
                # Never block the GUI thread waiting for a previous query.
                # The completed worker schedules one coalesced follow-up load.
                self._reload_pending = True
                return

            self.worker = CustomerWorker(
                self.db,
                self.limit,
                self.current_page * self.limit,
                self.search_query,
                self.current_filter_type,
            )
            self.worker.data_loaded.connect(self.on_data_loaded)
            self.worker.load_error.connect(
                lambda e: self.lbl_total.setText(f"Hata: {e}")
            )
            if getattr(self.db, "_db_name", "") == ":memory:":
                self.worker.run()
            else:
                self.worker.start()

        except Exception as e:
            logger.error(f"Customer refresh_data error: {e}", exc_info=True)
            self.lbl_total.setText(f"Hata: {e}")

    def on_data_loaded(self, customers, total):
        logger.debug(
            "CustomersPage.on_data_loaded total=%s rows=%s",
            total,
            len(customers) if customers else 0,
        )
        customers_list = [
            row
            for row in list(customers or [])
            if not self._looks_like_partner_row(row)
        ]
        self.total_count = (
            len(customers_list)
            if self.current_filter_type in (None, "DEBTORS", "OPEN_RECEIVABLES")
            else int(total or 0)
        )
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(0)
        success_count = 0
        for i, customer in enumerate(customers_list):
            try:
                self._add_row(i, customer)
                success_count += 1
            except Exception as e:
                logger.error(
                    f"CustomersPage _add_row failed at index {i}: {e}"
                )
        self.table.setSortingEnabled(True)
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()
        
        self.lbl_total.setText(f"Toplam Kayıt: {self.total_count}")
        self.lbl_time.setText(
            f"Son Güncelleme: {format_date(datetime.now(), self.db, include_time=True)}"
        )
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        self._update_pagination_ui()
        self._try_run_pending_reload()

    def _add_row(self, row_idx, data):
        try:
            self.table.insertRow(row_idx)

            customer_id = data["id"]
            item_id = QTableWidgetItem(str(customer_id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_id.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            self.table.setItem(row_idx, 0, item_id)

            name_display = str(data["name"])
            keys = data.keys() if hasattr(data, "keys") else []
            cust_type = str(data["type"] or "").strip() if "type" in keys else ""

            if cust_type in ("Kurumsal", "Bayi", "Tedarikçi"):
                if cust_type == "Kurumsal":
                    badge_text = "Kurumsal"
                elif cust_type == "Bayi":
                    badge_text = "Bayi"
                else:
                    badge_text = "Tedarikçi"
                name_display = f"{name_display}  [{badge_text}]"
            
            name_item = QTableWidgetItem(name_display)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if cust_type in ("Kurumsal", "Bayi", "Tedarikçi"):
                name_item.setForeground(qc("selection_text"))
            self.table.setItem(row_idx, 1, name_item)

            company = (
                data["company_name"]
                if "company_name" in keys and data["company_name"]
                else "—"
            )
            comp_item = QTableWidgetItem(str(company))
            comp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row_idx, 2, comp_item)

            phone_item = QTableWidgetItem(str(data["phone"]) if data["phone"] else "—")
            phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            phone_item.setFont(QFont("Consolas", 9))
            self.table.setItem(row_idx, 3, phone_item)

            mail_item = QTableWidgetItem(str(data["email"]) if data["email"] else "—")
            mail_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            mail_item.setFont(QFont("Segoe UI", 9))
            self.table.setItem(row_idx, 4, mail_item)

            try:
                balances = {
                    "TRY": float(data["balance_try"]) if "balance_try" in keys else 0.0,
                    "USD": float(data["balance_usd"]) if "balance_usd" in keys else 0.0,
                    "EUR": float(data["balance_eur"]) if "balance_eur" in keys else 0.0,
                }
            except Exception:
                balances = {"TRY": 0.0}

            bal_item = self._create_balance_item_multi(balances)
            self.table.setItem(row_idx, 5, bal_item)

            self.table.setCellWidget(
                row_idx, 6, self._create_action_widget(row_idx, data)
            )

            it = self.table.item(row_idx, 0)
            if it:
                it.setData(Qt.ItemDataRole.UserRole, data)

            visible_currency_count = getattr(bal_item, "_visible_currency_count", 1)
            self.table.setRowHeight(
                row_idx,
                76 if visible_currency_count <= 1 else 92 if visible_currency_count == 2 else 108,
            )
        except Exception as e:
            logger.error(f"ADD_ROW ERROR at index {row_idx}: {e}")

    def _create_balance_item_multi(self, balances):
        default_currency = CurrencyHelper.get_code(self.db)
        lines = []
        has_debt = False
        has_credit = False
        visible_codes = []

        for currency_code in ("TRY", "USD", "EUR"):
            try:
                amount = float(balances.get(currency_code, 0.0) or 0.0)
            except Exception:
                amount = 0.0

            should_show = currency_code == default_currency or abs(amount) > 0.0001
            if not should_show:
                continue

            visible_codes.append(currency_code)

            if amount < 0:
                status = " (Borc)"
                has_debt = True
            elif amount > 0:
                status = " (Alacak)"
                has_credit = True
            else:
                status = ""

            formatted_amount = CurrencyHelper.format_amount(
                abs(amount),
                db=self.db,
                currency_code=currency_code,
            )
            lines.append(f"{currency_code}: {formatted_amount}{status}")

        if not lines:
            lines.append(
                f"{default_currency}: "
                + CurrencyHelper.format_amount(0, db=self.db, currency_code=default_currency)
            )
            visible_codes.append(default_currency)

        color = tc("danger") if has_debt else tc("success") if has_credit else tc("text_muted")

        text = "\n".join(lines)
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        item._visible_currency_count = len(visible_codes)
        return item

    def _create_balance_item(self, balance):
        return self._create_balance_item_multi({"TRY": balance})

    def _try_run_pending_reload(self):
        if hasattr(self, "_reload_pending") and self._reload_pending:
            self._reload_pending = False
            QTimer.singleShot(100, self.refresh_data)

    def execute_search(self):
        self.search_query = self.inp_search.text().strip()
        self.current_page = 0
        self.request_reload()

    def _selected_customer_rows(self):
        return sorted(
            set(index.row() for index in self.table.selectionModel().selectedRows())
        )
