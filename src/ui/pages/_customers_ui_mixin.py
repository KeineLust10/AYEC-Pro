# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QMenu, QWidget, QHBoxLayout, QPushButton, QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer

from src.utils.theme_colors import theme_qss
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.performance_monitor import perf_span
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog

class CustomersUIMixin:
    """UI styles, context menus and row actions for CustomersPage."""

    def _create_action_widget(self, row, data):
        btn = QPushButton("İşlem Yap ▼")
        btn.setMinimumWidth(160)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            theme_qss("""
            QPushButton { background: @accent; color: @selection_text; border-radius: 15px; font-weight: bold; font-size: 11px; border: 1px solid @accent; }
            QPushButton:hover { background: @accent_hover; color: @selection_text; border-color: @accent_hover; }
        """)
        )
        btn.clicked.connect(lambda checked, r=row: self.show_row_menu(r))

        container = QWidget()
        container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(btn)
        return container

    def show_row_menu(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.open_customer_menu(
            customer, self.table.cellWidget(row, 6).findChild(QPushButton)
        )

    def show_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=21):
            return
        item = self.table.itemAt(position)
        if not item:
            return
        row = item.row()
        if self.table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection:
            self.table.selectRow(row)
        customer = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        self.populate_customer_menu(menu, customer)
        menu.exec(self.table.viewport().mapToGlobal(position))

    def open_customer_menu(self, customer, source_widget):
        menu = QMenu(self)
        self.populate_customer_menu(menu, customer)
        pos = source_widget.mapToGlobal(source_widget.rect().bottomLeft())
        menu.exec(pos)

    def populate_customer_menu(self, menu, customer):
        menu.addAction(
            "Müşteri Notları",
            lambda: CustomerNotesDialog(
                self.db, customer["id"], customer["name"], self
            ).exec(),
        )
        menu.addAction("Müşteri 360", lambda: self.open_customer_360(customer))
        menu.addAction("Düzenle", lambda: self.edit_customer(customer))
        menu.addSeparator()
        menu.addAction("Yeni Servis Kaydı", lambda: self.create_service(customer))
        menu.addAction("Fatura Kes", lambda: self.create_invoice(customer))
        menu.addAction("Tahsilat / Ödeme Al", lambda: self.record_payment(customer))
        menu.addSeparator()
        menu.addAction("WhatsApp Mesaj", lambda: self.send_whatsapp(customer))
        menu.addAction(
            "Bakiye Hatırlat (WA)", lambda: self.send_debt_reminder(customer)
        )
        menu.addSeparator()
        menu.addAction("Excel'e Aktar", self.export_excel)
        menu.addAction("PDF Olarak Kaydet", self.export_pdf)
        menu.addAction("Yazdır", self.print_list)
        if hasattr(self, "_multi_select") and self._multi_select:
            menu.addSeparator()
            menu.addAction("Seçilileri Excel Aktar", self.export_selected_csv)
        menu.addSeparator()
        menu.addAction("Müşteriyi Sil", lambda: self.delete_customer(customer))

    def _on_table_cell_entered(self, row, _column):
        if row >= 0:
            self.table.selectRow(row)

    def toggle_multiselect(self, checked: bool):
        self.table.clearSelection()
        self._multi_select = checked
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setText("✅")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setText("🔲")
