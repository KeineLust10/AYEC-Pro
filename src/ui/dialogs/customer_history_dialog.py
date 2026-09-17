# -*- coding: utf-8 -*-
import os
import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger
from src.utils.toast_notification import show_error, show_success, show_warning
from src.utils.theme_colors import theme_qss, qc
from src.utils.design_system import DesignTokens


class CustomerHistoryDialog(ModernDialog):
    def __init__(self, customer_name, history_data, db=None, parent=None):
        super().__init__(title=f"Musteri 360 - {customer_name}", parent=parent, width=1000, height=700)
        self.db = db
        self.customer_name = customer_name
        self.customer_id = None
        self.history_data = history_data
        self.set_footer_visible(False)
        self.setup_ui()

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        return CurrencyHelper.format_from_try(
            amount_try,
            db=self.db,
            currency_code=self._display_currency(),
            include_try_reference=False,
        )

    def _resolve_customer_id(self):
        if not self.db:
            return None
        if self.customer_id:
            return self.customer_id
        try:
            self.db.cursor.execute(
                "SELECT id FROM customers WHERE TRIM(UPPER(name))=TRIM(UPPER(?)) LIMIT 1",
                (self.customer_name,),
            )
            row = self.db.cursor.fetchone()
            self.customer_id = row[0] if row else None
        except Exception as exc:
            logger.error("CustomerHistoryDialog customer resolve error: %s", exc)
        return self.customer_id

    def setup_ui(self):
        main_layout = self.content_layout
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        profile_frame = QFrame()
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(20, 20, 20, 20)

        avatar = QLabel("M")
        avatar.setFixedSize(60, 60)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile_layout.addWidget(avatar)

        info_layout = QVBoxLayout()
        lbl_name = QLabel(self.customer_name)
        lbl_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        info_layout.addWidget(lbl_name)
        info_layout.addWidget(QLabel("Musteri Profili"))
        profile_layout.addLayout(info_layout)
        profile_layout.addStretch()

        total_services = len(self.history_data)
        service_spent = sum(float(record[11]) if len(record) > 11 and record[11] else 0 for record in self.history_data)
        acc_spent = 0
        current_balance = 0
        if self.db:
            try:
                customer_id = self._resolve_customer_id()
                self.db.cursor.execute(
                    """
                    SELECT SUM(amount)
                    FROM accounting
                    WHERE ((? IS NOT NULL AND customer_id=?) OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
                      AND type='Gelir' AND category='Satış'
                    """,
                    (customer_id, customer_id, self.customer_name),
                )
                acc_spent = self.db.cursor.fetchone()[0] or 0
                if customer_id:
                    current_balance = self.db.get_customer_balance(customer_id)
            except Exception as exc:
                logger.error("Customer history stats calculation error: %s", exc)

        display_currency = self._display_currency()
        total_spent = float(service_spent) + float(acc_spent)
        active_services = sum(1 for row in self.history_data if "Tamamlan" not in str(row[8]) and "Iptal" not in str(row[8]))
        self.add_header_stat(profile_layout, "TOPLAM SERVIS", str(total_services), "#00a65a")
        self.add_header_stat(profile_layout, "AKTIF ISLER", str(active_services), "#f39c12")
        self.add_header_stat(profile_layout, "TOPLAM HARCAMA", self._format_display_money(total_spent), "#3c8dbc")
        balance_color = "#27ae60" if current_balance >= 0 else "#e74c3c"
        self.add_header_stat(
            profile_layout,
            f"AKTIF BAKIYE ({display_currency})",
            self._format_display_money(abs(current_balance)),
            balance_color,
        )

        export_layout = QVBoxLayout()
        btn_excel = QPushButton("Listeyi Excel'e Aktar")
        btn_excel.clicked.connect(self.export_to_excel)
        self.btn_pdf = QPushButton("PDF'e Aktar")
        self.btn_pdf.clicked.connect(self.export_to_pdf)
        export_layout.addWidget(btn_excel)
        export_layout.addWidget(self.btn_pdf)
        profile_layout.addLayout(export_layout)
        main_layout.addWidget(profile_frame)

        tabs = QTabWidget()
        tab_history = QWidget()
        vbox_hist = QVBoxLayout(tab_history)
        self.btn_select_all_hist = QPushButton("Tumunu Sec / Kaldir")
        self.btn_select_all_hist.clicked.connect(self.toggle_all_history)
        vbox_hist.addWidget(self.btn_select_all_hist)

        from PyQt6.QtWidgets import QAbstractItemView
        self.history_table = QTableWidget()
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.history_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels(["Sec", "Takip No", "Cihaz", "Ariza", "Durum", "Ucret", "Tarih"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.history_table.setColumnWidth(0, 40)
        for i, row in enumerate(self.history_data):
            self.history_table.insertRow(i)
            cb = QCheckBox()
            cb.setChecked(True)
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.history_table.setCellWidget(i, 0, cb_container)
            self.history_table.setItem(i, 1, QTableWidgetItem(str(row[1])))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"{row[3]} {row[4]}"))
            self.history_table.setItem(i, 3, QTableWidgetItem(str(row[6])))
            status_item = QTableWidgetItem(str(row[8]))
            if "Tamamlan" in str(row[8]):
                status_item.setForeground(QColor("#00a65a"))
            elif "Tamir" in str(row[8]):
                status_item.setForeground(QColor("#f39c12"))
            self.history_table.setItem(i, 4, status_item)
            self.history_table.setItem(i, 5, QTableWidgetItem(self._format_display_money(row[11] if len(row) > 11 and row[11] else 0)))
            self.history_table.setItem(i, 6, QTableWidgetItem(str(row[9])[:10] if len(row) > 9 else ""))
        vbox_hist.addWidget(self.history_table)
        tabs.addTab(tab_history, "Servis Gecmisi")

        tab_finance = QWidget()
        vbox_fin = QVBoxLayout(tab_finance)
        self.btn_select_all_fin = QPushButton("Tumunu Sec / Kaldir")
        self.btn_select_all_fin.clicked.connect(self.toggle_all_finance)
        vbox_fin.addWidget(self.btn_select_all_fin)

        self.fin_table = QTableWidget()
        self.fin_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.fin_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.fin_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.fin_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.fin_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.fin_table.setColumnCount(6)
        self.fin_table.setHorizontalHeaderLabels(["Sec", "Kategori", "Aciklama", "Tip", "Tarih", "Tutar"])
        self.fin_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fin_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.fin_table.setColumnWidth(0, 40)
        fin_records = []
        if self.db:
            try:
                customer_id = self._resolve_customer_id()
                self.db.cursor.execute(
                    """
                    SELECT category, description, type, date, amount
                    FROM accounting
                    WHERE ((? IS NOT NULL AND customer_id=?)
                       OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
                    ORDER BY date DESC
                    """,
                    (customer_id, customer_id, self.customer_name),
                )
                fin_records = self.db.cursor.fetchall()
            except Exception as exc:
                logger.error("Customer history finance fetch error: %s", exc)
        for i, row in enumerate(fin_records):
            self.fin_table.insertRow(i)
            cb = QCheckBox()
            cb.setChecked(True)
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.fin_table.setCellWidget(i, 0, cb_container)
            self.fin_table.setItem(i, 1, QTableWidgetItem(row[0] or "-"))
            self.fin_table.setItem(i, 2, QTableWidgetItem(row[1] or "-"))
            type_item = QTableWidgetItem(row[2] or "-")
            if "GELIR" in str(row[2]).upper():
                type_item.setForeground(QColor("#27ae60"))
            elif "GIDER" in str(row[2]).upper():
                type_item.setForeground(QColor("#c0392b"))
            self.fin_table.setItem(i, 3, type_item)
            self.fin_table.setItem(i, 4, QTableWidgetItem(str(row[3])[:10]))
            try:
                self.fin_table.setItem(i, 5, QTableWidgetItem(self._format_display_money(float(row[4]))))
            except Exception:
                self.fin_table.setItem(i, 5, QTableWidgetItem(str(row[4])))
        vbox_fin.addWidget(self.fin_table)
        tabs.addTab(tab_finance, "Finansal Hareketler")
        main_layout.addWidget(tabs)

    def add_header_stat(self, layout, title, value, color):
        frame = QFrame()
        vbox = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_val = QLabel(str(value))
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_val.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        layout.addWidget(frame)

    def toggle_all_history(self):
        first_cb = None
        if self.history_table.rowCount() > 0:
            widget = self.history_table.cellWidget(0, 0)
            if widget:
                first_cb = widget.layout().itemAt(0).widget()
        target_state = not first_cb.isChecked() if first_cb else True
        for i in range(self.history_table.rowCount()):
            widget = self.history_table.cellWidget(i, 0)
            if widget:
                widget.layout().itemAt(0).widget().setChecked(target_state)

    def toggle_all_finance(self):
        first_cb = None
        if self.fin_table.rowCount() > 0:
            widget = self.fin_table.cellWidget(0, 0)
            if widget:
                first_cb = widget.layout().itemAt(0).widget()
        target_state = not first_cb.isChecked() if first_cb else True
        for i in range(self.fin_table.rowCount()):
            widget = self.fin_table.cellWidget(i, 0)
            if widget:
                widget.layout().itemAt(0).widget().setChecked(target_state)

    def export_to_excel(self):
        try:
            file_path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", f"Bakim_Raporu_{self.customer_name}.xlsx", "Excel Files (*.xlsx)")
            if not file_path:
                return
            history_rows = []
            for i in range(self.history_table.rowCount()):
                cb_widget = self.history_table.cellWidget(i, 0)
                if cb_widget and cb_widget.layout().itemAt(0).widget().isChecked():
                    history_rows.append([self.history_table.item(i, col).text() for col in range(1, 7)])
            finance_rows = []
            for i in range(self.fin_table.rowCount()):
                cb_widget = self.fin_table.cellWidget(i, 0)
                if cb_widget and cb_widget.layout().itemAt(0).widget().isChecked():
                    finance_rows.append([self.fin_table.item(i, col).text() for col in range(1, 6)])
            with pd.ExcelWriter(file_path) as writer:
                pd.DataFrame(history_rows, columns=["Takip No", "Cihaz", "Ariza", "Durum", "Ucret", "Tarih"]).to_excel(writer, sheet_name="Servis Gecmisi", index=False)
                pd.DataFrame(finance_rows, columns=["Kategori", "Aciklama", "Islem Tipi", "Tarih", "Tutar"]).to_excel(writer, sheet_name="Finansal Hareketler", index=False)
            show_success(self, f"Secilen kayitlar kaydedildi:\n{file_path}")
            os.startfile(file_path)
        except Exception as exc:
            show_error(self, f"Excel'e aktarilirken hata olustu:\n{exc}")

    def export_to_pdf(self):
        try:
            from src.utils.pdf_manager import PDFManagerQt
            from src.ui.utils.background_task import run_cancellable_task

            service_items = []
            for i in range(self.history_table.rowCount()):
                cb_widget = self.history_table.cellWidget(i, 0)
                if cb_widget and cb_widget.layout().itemAt(0).widget().isChecked():
                    price_text = self.history_table.item(i, 5).text()
                    price_value = float(price_text.split(" ")[0].replace(",", "")) if price_text else 0.0
                    service_items.append({"service": self.history_table.item(i, 2).text(), "description": self.history_table.item(i, 3).text(), "price": price_value, "date": self.history_table.item(i, 6).text()})
            if not service_items:
                show_warning(self, "PDF raporu icin en az bir servis kaydi secin.")
                return
            subtotal = sum(item["price"] for item in service_items)
            totals = (subtotal, 0, 0, 0, subtotal)
            customer_name = f"{self.customer_name} - Secili Kayitlar"
            self.btn_pdf.setEnabled(False)

            def produce_pdf(is_cancelled):
                if is_cancelled():
                    return None
                pdf = PDFManagerQt(self.db)
                return pdf.create_invoice(
                    "modern",
                    service_items,
                    totals,
                    customer_name=customer_name,
                )

            def pdf_ready(result):
                if not result:
                    return
                success, result_path = result
                if success:
                    show_success(self, "Secilen kayitlar PDF olarak olusturuldu.")
                    if result_path and os.path.isfile(result_path):
                        os.startfile(result_path)
                else:
                    show_warning(self, f"PDF olusturulamadi: {result_path}")

            run_cancellable_task(
                owner=self,
                title="PDF raporu olusturuluyor",
                target=produce_pdf,
                on_success=pdf_ready,
                on_error=lambda message: show_error(
                    self,
                    f"PDF'e aktarilirken hata olustu:\n{message}",
                ),
                on_done=lambda: self.btn_pdf.setEnabled(True),
            )
        except Exception as exc:
            self.btn_pdf.setEnabled(True)
            show_error(self, f"PDF'e aktarilirken hata olustu:\n{exc}")
