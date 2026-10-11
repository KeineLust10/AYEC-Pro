# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QMenu, QWidget, QHBoxLayout, QPushButton, QAbstractItemView, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QItemSelectionModel

from src.utils.theme_colors import theme_qss
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.performance_monitor import perf_span
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
from src.ui.widgets.navigation_glyph import navigation_icon

class CustomersUIMixin:
    """UI styles, context menus and row actions for CustomersPage."""

    def _create_action_widget(self, row, data):
        container = QWidget()
        container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def add_action(label, width, callback, tone="neutral", icon=None):
            button = QPushButton(label)
            button.setFixedHeight(30)
            button.setMinimumWidth(max(22, width - 8))
            button.setMaximumWidth(width)
            button.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 7px; padding: 0 4px; font-size: 9px; font-weight: 700; } "
                "QPushButton:hover { background: @surface_high; border-color: @accent; }"
            ))
            if tone == "primary":
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @accent; color: @selection_text; border: 1px solid @accent; "
                    "border-radius: 7px; padding: 0 4px; font-size: 9px; font-weight: 700; } "
                    "QPushButton:hover { background: @accent; border-color: @accent; }"
                ))
            elif tone == "warning":
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @danger; color: @selection_text; border: 1px solid @danger; "
                    "border-radius: 7px; padding: 0 4px; font-size: 9px; font-weight: 700; } "
                    "QPushButton:hover { background: @danger; }"
                ))
            if icon:
                button.setIcon(navigation_icon(icon, 14, "selection_text" if tone == "primary" else "text_muted"))
            button.clicked.connect(callback)
            lay.addWidget(button)
            return button

        def add_more_button():
            more = QPushButton()
            more.setFixedHeight(30)
            more.setMinimumWidth(20)
            more.setMaximumWidth(22)
            more.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Fixed,
            )
            more.setIcon(navigation_icon("more_vertical", 14, "text_muted"))
            more.setToolTip("Di\u011fer m\u00fc\u015fteri i\u015flemleri")
            more.setAccessibleName("Di\u011fer m\u00fc\u015fteri i\u015flemleri")
            more.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text_muted; border: 1px solid @border; "
                "border-radius: 7px; font-size: 16px; font-weight: 700; } "
                "QPushButton:hover { background: @surface_high; color: @text; }"
            ))
            more.clicked.connect(lambda _checked=False, r=row: self.show_row_menu(r))
            lay.addWidget(more)

        customer_type = str(data.get("type") or "").casefold()
        contract_type = str(data.get("contract_type") or "").upper()
        is_vip = "VIP" in contract_type or customer_type == "vip"
        service_count = int(data.get("open_service_count", 0) or 0)
        balance = float(data.get("balance_try", 0) or 0)
        if is_vip:
            add_action("Cari Kart", 76, lambda _checked=False, c=data: self.open_customer_360(c), "primary", "chevron_right")
            add_more_button()
        elif balance < 0:
            add_action("Hat\u0131rlat", 72, lambda _checked=False, c=data: self.send_debt_reminder(c), "warning", "send")
            add_more_button()
        elif service_count > 0:
            add_action("Servis A\u00e7", 72, lambda _checked=False, c=data: self.create_service(c), "neutral", "tool")
            if str(data.get("phone") or "").strip():
                add_action("", 22, lambda _checked=False, c=data: self.send_whatsapp(c), "neutral", "message")
            add_more_button()
        else:
            menu_button = add_action("\u0130\u015flem Yap  \u2304", 92, lambda _checked=False, r=row: self.show_row_menu(r))
            menu_button.setToolTip("M\u00fc\u015fteri i\u015flemleri")
        return container

    def show_row_menu(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        customer = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        self.open_customer_menu(
            customer, self.table.cellWidget(row, 8).findChild(QPushButton)
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
        customer = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)

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

    def _on_customer_checkbox_changed(self, item):
        if item.column() != 0:
            return
        if item.checkState() == Qt.CheckState.Checked:
            self.table.selectRow(item.row())
        else:
            self.table.selectionModel().select(
                self.table.model().index(item.row(), 0),
                QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows,
            )

    def _toggle_customer_select_all(self, column):
        if column != 0:
            return
        select_all = any(
            self.table.item(row, 0)
            and self.table.item(row, 0).checkState() != Qt.CheckState.Checked
            for row in range(self.table.rowCount())
        )
        state = Qt.CheckState.Checked if select_all else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0):
                self.table.item(row, 0).setCheckState(state)

    def toggle_multiselect(self, checked: bool):
        self.table.clearSelection()
        self._multi_select = checked
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setText("✅")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setText("🔲")
