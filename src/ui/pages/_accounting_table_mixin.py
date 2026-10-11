# -*- coding: utf-8 -*-

from collections import defaultdict
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QAction
from PyQt6.QtWidgets import QTableWidgetItem, QMenu
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import qc
from src.utils.context_menu_settings import is_context_menu_enabled
from src.ui.pages.accounting_dialogs import TransactionDetailsDialog

class AccountingTableMixin:
    def apply_filter(self, filter_key):
        self._current_filter_key = filter_key
        from src.utils.ayec_accelerator import fast_render_context
        with fast_render_context(self.table):
            try:
                grouped = defaultdict(list)
                self.table.clearSpans()
                self.table.setRowCount(0)

                for row in self.ledger_data:
                    type_label = str(row.get("type_label", ""))
                    if filter_key == "INCOME" and type_label not in {"Satış", "Gelir", "Tahsilat"}: continue
                    if filter_key == "EXPENSE" and type_label not in {"Gider"}: continue
                    if filter_key == "OPENING" and type_label not in {"Açılış"}: continue
                    display_date = row.get("display_date") or row.get("date") or "-"
                    grouped[display_date].append(row)

                group_sort = {d: max(float(r.get("sort_ts") or 0) for r in rs) for d, rs in grouped.items()}
                sorted_dates = sorted(grouped.keys(), key=lambda d: group_sort.get(d, 0), reverse=True)

                for display_date in sorted_dates:
                    rows = sorted(grouped[display_date], key=lambda r: (float(r.get("sort_ts") or 0), int(r.get("id") or 0)), reverse=True)
                    header_row = self.table.rowCount(); self.table.insertRow(header_row)
                    income_total = sum(float(t.get("amount_try") or 0) for t in rows if t.get("type_label") in {"Satış", "Gelir", "Tahsilat", "Açılış"})
                    expense_total = sum(abs(float(t.get("amount_try") or 0)) for t in rows if t.get("type_label") == "Gider")
                    expanded = str(display_date or "-") in self._expanded_ledger_dates
                    self._set_ledger_group_header(header_row, display_date, rows, expanded, income_total, expense_total)
                    if not expanded: continue

                    for row in rows:
                        data_row = self.table.rowCount(); self.table.insertRow(data_row)
                        type_label = self._clean_ledger_text(row.get("type_label", "-"))
                        is_income = type_label in {"Satış", "Gelir", "Tahsilat", "Açılış"}
                        icon = "A" if type_label == "Açılış" else ("S" if type_label == "Satış" else ("T" if is_income else "G"))
                        amt_try, bal_val = float(row.get("amount_try") or 0), row.get("balance_value")
                        display_amount = -abs(amt_try) if type_label == "Gider" else amt_try
                        bal_float = float(bal_val or 0) if bal_val is not None else None
                        values = [row.get("time") or "--", f"{icon} {type_label}", self._ledger_description_text(row), row.get("amount_original_str") or "--", row.get("exchange_rate_str") or "--", CurrencyHelper.format_try_for_display(display_amount, db=self.db, include_try_reference=False), self._clean_ledger_text(row.get("status_text") or "-"), "--" if bal_val is None else CurrencyHelper.format_try_for_display(bal_float, db=self.db, include_try_reference=False)]
                        for col, val in enumerate(values):
                            item = QTableWidgetItem(str(val))
                            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                            if col == 2: item.setToolTip(str(val))
                            if col in (3, 4, 5, 7): item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                            if col == 1: item.setForeground(qc("success") if is_income else qc("danger"))
                            elif col == 6:
                                st = str(val).lower()
                                if "bekliyor" in st: item.setForeground(qc("warning"))
                                elif "tamam" in st: item.setForeground(qc("success"))
                            elif col in (5, 7):
                                if str(val).strip() in ("", "-", "--"): item.setForeground(qc("finance_text_muted"))
                                elif str(val).startswith("-") or (col == 5 and display_amount < 0) or (col == 7 and bal_float is not None and bal_float < 0): item.setForeground(qc("danger"))
                                else: item.setForeground(qc("text"))
                            self.table.setItem(data_row, col, item); self.table.item(data_row, col).setData(Qt.ItemDataRole.UserRole, row)

                if hasattr(self, "ledger_empty_state"):
                    has_rows = self.table.rowCount() > 0
                    self.table.setVisible(has_rows); self.ledger_empty_state.setVisible(not has_rows)
                if hasattr(self, "update_footer"): self.update_footer()
                if self._is_classic_appearance(): self.table.verticalHeader().setDefaultSectionSize(30)
                else:
                    self.table.resizeRowsToContents()
                    for index in range(self.table.rowCount()):
                        payload = self.table.item(index, 0).data(Qt.ItemDataRole.UserRole) if self.table.item(index, 0) else None
                        if isinstance(payload, dict) and payload.get("kind") == "date_group":
                            self.table.setRowHeight(index, 30)
                        else:
                            self.table.setRowHeight(index, max(55, self.table.rowHeight(index)))
            except Exception as e: import traceback; print(f"apply_filter error: {e}\n{traceback.format_exc()}")


    def _set_ledger_group_header(self, row_idx, display_date, rows, expanded, income_total, expense_total):
        net_total = income_total - expense_total
        arrow = "v" if expanded else ">"
        summary = f"Ciro: {CurrencyHelper.format_try_for_display(income_total, db=self.db, include_try_reference=False)}   Gider: {CurrencyHelper.format_try_for_display(expense_total, db=self.db, include_try_reference=False)}   Net: {CurrencyHelper.format_try_for_display(net_total, db=self.db, include_try_reference=False)}"
        values = [f"{arrow} {display_date}", f"{len(rows)} i\u015flem", summary, "", "", CurrencyHelper.format_try_for_display(net_total, db=self.db, include_try_reference=False), "A\u00e7\u0131k" if expanded else "Kapal\u0131", ""]
        payload = {
            "kind": "date_group", "display_date": str(display_date or "-"),
            "expanded": expanded, "count": len(rows),
            "income_text": CurrencyHelper.format_try_for_display(income_total, db=self.db, include_try_reference=False),
            "expense_text": CurrencyHelper.format_try_for_display(expense_total, db=self.db, include_try_reference=False),
            "net_text": CurrencyHelper.format_try_for_display(net_total, db=self.db, include_try_reference=False),
            "net_negative": net_total < 0,
        }
        bg, fg = qc("finance_active_bg" if expanded else "finance_surface_high"), qc("finance_text")
        for col, val in enumerate(values):
            item = QTableWidgetItem(str(val))
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            item.setData(Qt.ItemDataRole.UserRole, payload); item.setBackground(bg); item.setForeground(fg)
            f = item.font(); f.setBold(True); item.setFont(f)
            item.setTextAlignment((Qt.AlignmentFlag.AlignRight if col in (5, 7) else Qt.AlignmentFlag.AlignLeft) | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row_idx, col, item)
        self.table.setSpan(row_idx, 0, 1, 8)
        primary = self.table.item(row_idx, 0)
        primary.setText(f"{arrow} {display_date}   {len(rows)} i\u015flem    {summary}")
        primary.setToolTip(primary.text())
        font = primary.font()
        font.setPixelSize(10)
        primary.setFont(font)
        self.table.setRowHeight(row_idx, 34 if self._is_classic_appearance() else 38)

    def _toggle_ledger_date_group(self, display_date):
        key = str(display_date or "-")
        if key in self._expanded_ledger_dates: self._expanded_ledger_dates.remove(key)
        else: self._expanded_ledger_dates.add(key)
        self.apply_filter(getattr(self, "_current_filter_key", "ALL"))

    def _ledger_description_text(self, row):
        description = self._clean_ledger_text(row.get("description") or "-")
        details = []
        for key, label in (("ref_no", "Ref"), ("customer_name", "M\u00fc\u015fteri")):
            value = str(row.get(key) or "").strip()
            if value and value.casefold() not in description.casefold():
                details.append(label + ": " + self._clean_ledger_text(value))
        return description + ("\n" + " | ".join(details) if details else "")

    def _clean_ledger_text(self, value):
        text = str(value or "")
        for bad, good in {"i\u00c5\u0178lem": "işlem"}.items(): text = text.replace(bad, good)
        return text

    def on_table_double_click(self, row, column):
        item = self.table.item(row, column) or self.table.item(row, 0)
        if not item: return
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry: return
        if isinstance(entry, dict) and entry.get("kind") == "date_group":
            self._toggle_ledger_date_group(entry.get("display_date")); return
        TransactionDetailsDialog(self.db, entry, self).exec()

    def _refresh_amount_headers(self):
        code = CurrencyHelper.get_code(self.db)
        self.table.setHorizontalHeaderLabels(["TARİH", "İŞLEM TÜRÜ", "AÇIKLAMA", "TUTAR (DÖVİZ)", "KUR", f"TOPLAM ({code})", "DURUM", f"BAKİYE ({code})"])

    def show_table_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=101): return
        idx = self.table.indexAt(pos)
        if not idx.isValid(): return
        self.table.selectRow(idx.row())
        item = self.table.item(idx.row(), idx.column()) or self.table.item(idx.row(), 0)
        entry = item.data(Qt.ItemDataRole.UserRole) if item else None
        menu = QMenu(self)
        if isinstance(entry, dict) and entry.get("kind") == "date_group":
            label = "Günü Kapat" if entry.get("display_date") in self._expanded_ledger_dates else "Günü Aç"
            a = QAction(label, self); a.triggered.connect(lambda: self._toggle_ledger_date_group(entry.get("display_date"))); menu.addAction(a)
            menu.exec(self.table.viewport().mapToGlobal(pos)); return
        a_det = QAction("Hareket Detayı", self); a_det.triggered.connect(lambda: self.on_table_double_click(idx.row(), idx.column()))
        a_ex = QAction("Excel'e Aktar", self); a_ex.triggered.connect(self.export_to_excel)
        a_pdf = QAction("PDF Olarak Kaydet", self); a_pdf.triggered.connect(self.export_to_pdf)
        a_prnt = QAction("Yazdır", self); a_prnt.triggered.connect(self.print_ledger)
        menu.addActions([a_det]); menu.addSeparator(); menu.addActions([a_ex, a_pdf, a_prnt])
        menu.exec(self.table.viewport().mapToGlobal(pos))
