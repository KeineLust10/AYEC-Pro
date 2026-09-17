# -*- coding: utf-8 -*-
# _stock_history_tab.py
# Geçmiş sekmesi işlemleri

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFormLayout,
)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens, enable_row_hover
from src.utils.currency_helper import CurrencyHelper
from src.utils.date_formatter import format_date
from src.ui.widgets.modern_dialog import ModernDialog


class StockHistoryTabMixin:
    """Geçmiş sekmesi için mixin sınıfı."""

    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        self.table_hist = QTableWidget()
        self.table_hist.setColumnCount(8)
        self.table_hist.setHorizontalHeaderLabels(
            [
                "ID",
                "Parça",
                "İşlem",
                "Miktar",
                "PB",
                "Birim Maliyet",
                "Açıklama",
                "Tarih",
            ]
        )
        self.table_hist.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table_hist.verticalHeader().setVisible(False)
        self.table_hist.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_hist.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_hist.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_hist.setMouseTracking(True)
        self.table_hist.cellEntered.connect(self._on_history_cell_entered)
        self.table_hist.cellDoubleClicked.connect(self._show_history_detail)
        self.table_hist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_hist.customContextMenuRequested.connect(
            self.show_history_context_menu
        )
        self.table_hist.setStyleSheet(
            theme_qss(
                DesignTokens.get_table_qss()
                + """
            QTableWidget::item:hover {
                background-color: transparent;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
                font-weight: 600;
            }
        """
            )
        )
        enable_row_hover(self.table_hist, tc("selection_bg"), tc("selection_text"))
        layout.addWidget(self.table_hist)

        pager = QHBoxLayout()
        pager.addStretch()
        self.history_prev_button = QPushButton("< \u00d6nceki")
        self.history_page_label = QLabel("Sayfa 1 / 1")
        self.history_page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_next_button = QPushButton("Sonraki >")
        self.history_prev_button.clicked.connect(self._history_prev_page)
        self.history_next_button.clicked.connect(self._history_next_page)
        pager.addWidget(self.history_prev_button)
        pager.addWidget(self.history_page_label)
        pager.addWidget(self.history_next_button)
        pager.addStretch()
        layout.addLayout(pager)

    def _on_history_loaded(self, hists, total_count):
        try:
            self.history_total_count = int(total_count or 0)
            self._history_records = list(hists or [])
            self.table_hist.setRowCount(0)
            _symbol_cache: dict = {}

            def _get_symbol(curr):
                if curr not in _symbol_cache:
                    _symbol_cache[curr] = CurrencyHelper.get_symbol(self.db, curr)
                return _symbol_cache[curr]

            _date_fmt_cache: dict = {}

            for i, h in enumerate(hists):
                self.table_hist.insertRow(i)

                def _gv(key, default="-", _h=h):
                    try:
                        return _h[key] if _h[key] is not None else default
                    except Exception:
                        return default

                item_id = QTableWidgetItem(str(_gv("id")))
                item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 0, item_id)

                item_part = QTableWidgetItem(str(_gv("part_name")))
                item_part.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 1, item_part)

                mv_type = str(_gv("movement_type", "-"))
                t_item = QTableWidgetItem(mv_type)
                t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                is_incoming = any(
                    token in mv_type for token in ("Giriş", "Giris", "Giri")
                )
                t_item.setForeground(qc("success") if is_incoming else qc("danger"))
                self.table_hist.setItem(i, 2, t_item)

                item_amt = QTableWidgetItem(str(_gv("amount", 0)))
                item_amt.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 3, item_amt)

                item_curr = QTableWidgetItem(str(_gv("currency", "TRY")))
                item_curr.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 4, item_curr)

                unit_cost = float(_gv("unit_cost", 0) or 0)
                unit_curr = str(_gv("currency", "TRY") or "TRY").upper()
                unit_symbol = _get_symbol(unit_curr)
                item_cost = QTableWidgetItem(f"{unit_cost:,.2f} {unit_symbol}")
                item_cost.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 5, item_cost)

                item_desc = QTableWidgetItem(str(_gv("description", "")))
                item_desc.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table_hist.setItem(i, 6, item_desc)

                raw_date = _gv("created_at", "")
                formatted_date = format_date(raw_date, self.db, include_time=True)
                item_date = QTableWidgetItem(formatted_date)
                item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table_hist.setItem(i, 7, item_date)
            self._update_history_pagination()
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"StockPage history table load error: {e}")

    def _show_history_detail(self, row, _column):
        if row < 0 or row >= len(getattr(self, "_history_records", [])):
            return
        record = self._history_records[row]

        def value(key, default="-"):
            try:
                item = record[key]
            except Exception:
                item = default
            return default if item in (None, "") else str(item)

        dialog = ModernDialog("Stok Hareketi Detayi", self, width=620, height=430)
        body = QWidget()
        form = QFormLayout(body)
        form.setContentsMargins(18, 18, 18, 18)
        form.setVerticalSpacing(12)
        fields = (
            ("Hareket ID", value("id")),
            ("Urun", value("part_name")),
            ("Islem", value("movement_type")),
            ("Miktar", value("amount")),
            ("Para Birimi", value("currency", "TRY")),
            ("Birim Maliyet", value("unit_cost", "0")),
            ("Aciklama", value("description")),
            ("Tarih", format_date(value("created_at", ""), self.db, include_time=True)),
        )
        for label_text, field_value in fields:
            label = QLabel(field_value)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            form.addRow(QLabel(label_text), label)
        dialog.add_widget(body)
        dialog.add_cancel_button("Kapat")
        dialog.exec()

    def _update_history_pagination(self):
        page_limit = int(self.history_page_limit or 100)
        page_count = max(
            1,
            (int(self.history_total_count or 0) + page_limit - 1) // page_limit,
        )
        if self.history_current_page >= page_count:
            self.history_current_page = page_count - 1
        self.history_page_label.setText(
            f"Sayfa {self.history_current_page + 1} / {page_count}"
        )
        self.history_prev_button.setEnabled(self.history_current_page > 0)
        self.history_next_button.setEnabled(
            self.history_current_page + 1 < page_count
        )

    def _history_prev_page(self):
        if self.history_current_page <= 0:
            return
        self.history_current_page -= 1
        self.load_history()

    def _history_next_page(self):
        page_limit = int(self.history_page_limit or 100)
        page_count = max(
            1,
            (int(self.history_total_count or 0) + page_limit - 1) // page_limit,
        )
        if self.history_current_page + 1 >= page_count:
            return
        self.history_current_page += 1
        self.load_history()

    def _on_history_cell_entered(self, row, _column):
        if row >= 0:
            self.table_hist.selectRow(row)
