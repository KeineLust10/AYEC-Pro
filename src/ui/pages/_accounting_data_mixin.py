# -*- coding: utf-8 -*-

from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QColor
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import tc, theme_qss
from src.utils.date_formatter import format_date
from src.utils.logger import logger
from src.utils.performance_monitor import perf_span

class LedgerWorker(QThread):
    finished = pyqtSignal(list, dict, bool)

    def __init__(self, db_name, limit=100, offset=0):
        super().__init__()
        self.db_name = db_name or "ayecpro.db"
        self.limit = limit
        self.offset = offset

    def run(self):
        db = None
        try:
            from src.database import Database
            from src.utils.finance_manager import FinanceManager
            db = Database(self.db_name, init_mode="connection_only")
            manager = FinanceManager(db)
            with perf_span(
                "sql.finance.summary",
                extra=f"offset={self.offset}",
                threshold_ms=75,
            ):
                summary = manager.get_financial_summary("fiscal")
            with perf_span(
                "sql.finance.ledger",
                extra=f"limit={self.limit + 1} offset={self.offset}",
                threshold_ms=75,
            ):
                data = manager.get_unified_ledger(
                    self.limit + 1,
                    offset=self.offset,
                )
            has_more = len(data) > self.limit
            self.finished.emit(data[: self.limit], summary, has_more)
        except Exception as e:
            logger.error(f"LedgerWorker error: {e}")
            self.finished.emit([], {}, False)
        finally:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass

class FinanceCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title, value, subtext="", color=None, icon="💰", parent=None):
        super().__init__(parent)
        self.setObjectName("FinanceCard")
        color = color or tc("accent")
        self.setMinimumSize(0, 104)
        self.setMaximumHeight(122)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(14)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

        self.setStyleSheet(theme_qss(f"QFrame#FinanceCard {{ background-color: @surface; border: 1px solid @border; border-top: 4px solid {color}; border-radius: 14px; }}"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        header = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 700; border:none;"))
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(theme_qss(f"font-size: 16px; background: {color}15; color: {color}; border:none; border-radius: 10px; padding: 6px;"))
        header.addWidget(lbl_title)
        header.addStretch()
        header.addWidget(lbl_icon)
        layout.addLayout(header)

        self.lbl_value = QLabel(value)
        self.lbl_value.setWordWrap(True)
        self.lbl_value.setStyleSheet(theme_qss("color: @text; font-size: 18px; font-weight: 800; border:none;"))
        layout.addWidget(self.lbl_value)

        self.lbl_sub_value = QLabel("")
        self.lbl_sub_value.setWordWrap(True)
        self.lbl_sub_value.setVisible(False)
        self.lbl_sub_value.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 600; border:none;"))
        layout.addWidget(self.lbl_sub_value)

        self.lbl_subtext = QLabel(subtext)
        self.lbl_subtext.setWordWrap(True)
        self.lbl_subtext.setStyleSheet(theme_qss(f"color: {color}; font-size: 10px; font-weight: 700; border:none;"))
        layout.addWidget(self.lbl_subtext)

    def set_sub_value(self, text):
        self.lbl_sub_value.setText(text)
        self.lbl_sub_value.setVisible(bool(text))

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class AccountingDataMixin:
    def _update_summary_cards(self, data):
        summary = {
            "gross_revenue": float(data.get("gross_revenue", 0) or 0),
            "net_revenue": float(data.get("net_revenue", 0) or 0),
            "expenses": float(data.get("expenses", 0) or 0),
            "pocket_net": float(data.get("pocket_net", 0) or 0),
            "hot_cash": float(data.get("hot_cash", 0) or 0),
        }
        display_code = CurrencyHelper.get_code(self.db)
        cards = [
            (
                f"Toplam Ciro ({display_code})",
                CurrencyHelper.format_try_for_display(
                    summary["gross_revenue"],
                    db=self.db,
                    include_try_reference=False,
                ),
                "Br\u00fct Sat\u0131\u015f (KDV Dahil)",
                tc("success"),
                "\U0001f4c8",
                "Net Ciro: "
                + CurrencyHelper.format_try_for_display(
                    summary["net_revenue"],
                    db=self.db,
                    include_try_reference=False,
                ),
                "INCOME",
            ),
            (
                f"Maliyet ve Gider ({display_code})",
                CurrencyHelper.format_try_for_display(
                    summary["expenses"],
                    db=self.db,
                    include_try_reference=False,
                ),
                "Al\u0131\u015f + Operasyonel",
                tc("danger"),
                "\U0001f4c9",
                "",
                "EXPENSE",
            ),
            (
                f"Net K\u00e2r ({display_code})",
                CurrencyHelper.format_try_for_display(
                    summary["pocket_net"],
                    db=self.db,
                    include_try_reference=False,
                ),
                "Gelir - Gider (KDV Dahil)",
                tc("warning"),
                "\U0001f4b0",
                "",
                "ALL",
            ),
            (
                f"S\u0131cak Nakit ({display_code})",
                CurrencyHelper.format_try_for_display(
                    summary["hot_cash"],
                    db=self.db,
                    include_try_reference=False,
                ),
                "Kasa ve Banka Mevcudu",
                tc("accent"),
                "\U0001f3e7",
                "",
                "ALL",
            ),
        ]

        if not hasattr(self, "card_widgets") or not self.card_widgets:
            self.card_widgets = []
            for title, value, subtext, color, icon, sub_value, filter_key in cards:
                card = FinanceCard(
                    title,
                    value,
                    subtext,
                    color,
                    icon,
                    parent=self.cards_container,
                )
                if sub_value:
                    card.set_sub_value(sub_value)
                card.clicked.connect(
                    lambda _=False, fk=filter_key: self.apply_filter(fk)
                )
                self.card_widgets.append(card)
            self._relayout_summary_cards()
            return

        for idx, (_, value, subtext, _, _, sub_value, _) in enumerate(cards):
            if idx >= len(self.card_widgets):
                continue
            card = self.card_widgets[idx]
            card.lbl_value.setText(value)
            card.lbl_subtext.setText(subtext)
            if sub_value:
                card.set_sub_value(sub_value)
            else:
                card.lbl_sub_value.setVisible(False)

    def refresh_data(self):
        if getattr(self, "_refresh_lock", False):
            self._pending_refresh = True
            return
        self._refresh_lock = True
        self._pending_refresh = False

        try:
            if not hasattr(self, "cards_layout") or self.cards_layout is None:
                self._refresh_lock = False
                return

            if hasattr(self, "_refresh_amount_headers"):
                self._refresh_amount_headers()
            self._update_summary_cards(
                getattr(self, "_financial_summary", {})
            )

            self.worker = LedgerWorker(
                getattr(self.db, "_db_name", "ayecpro.db"),
                limit=getattr(self, "ledger_page_limit", 100),
                offset=(
                    getattr(self, "ledger_current_page", 0)
                    * getattr(self, "ledger_page_limit", 100)
                ),
            )
            self.worker.finished.connect(self.on_data_loaded)
            self.worker.start()
        except Exception as e:
            self._refresh_lock = False
            logger.error(f"Error in refresh_data: {e}")

    def on_data_loaded(self, data, summary, has_more):
        self._refresh_lock = False
        try:
            self.ledger_has_more = bool(has_more)
            self._update_ledger_pagination()
            self._financial_summary = summary or {}
            self._update_summary_cards(self._financial_summary)
            self.ledger_data = data or []
            for row in self.ledger_data:
                date_str = row.get("date") or ""
                row["display_date"] = format_date(date_str, self.db, include_time=False)
                if "T" in str(date_str):
                    row["time"] = str(date_str).split("T")[1][:5]
                elif " " in str(date_str):
                    row["time"] = str(date_str).split(" ")[1][:5]
                else:
                    row["time"] = "--"
                currency, amount, rate = (row.get("currency") or "TRY").upper(), row.get("amount") or 0, row.get("rate") or 1.0
                display_code = CurrencyHelper.get_code(self.db)
                if currency != display_code and float(amount or 0) != 0:
                    row["amount_original_str"] = CurrencyHelper.format_amount(amount, db=self.db, currency_code=currency)
                    row["exchange_rate_str"] = f"{float(rate):,.4f}" if float(rate) != 1.0 else "--"
                else:
                    row["amount_original_str"] = row["exchange_rate_str"] = "--"
                row["status_text"], row["balance_value"] = row.get("status") or "", row.get("balance")

            self.apply_filter(getattr(self, "_current_filter_key", "ALL"))
            if getattr(self, "_pending_refresh", False):
                self._pending_refresh = False
                QTimer.singleShot(50, self.refresh_data)
        except Exception as e:
            logger.error(f"Error in on_data_loaded: {e}")

    def _update_ledger_pagination(self):
        if not hasattr(self, "ledger_page_label"):
            return
        self.ledger_page_label.setText(
            f"Sayfa {getattr(self, 'ledger_current_page', 0) + 1}"
        )
        self.ledger_prev_button.setEnabled(
            getattr(self, "ledger_current_page", 0) > 0
        )
        self.ledger_next_button.setEnabled(
            bool(getattr(self, "ledger_has_more", False))
        )

    def _ledger_prev_page(self):
        if getattr(self, "ledger_current_page", 0) <= 0:
            return
        self.ledger_current_page -= 1
        self.refresh_data()

    def _ledger_next_page(self):
        if not getattr(self, "ledger_has_more", False):
            return
        self.ledger_current_page += 1
        self.refresh_data()

    def update_footer(self):
        try:
            while self.footer_layout.count():
                item = self.footer_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            data = getattr(self, "_financial_summary", {})
            cash, pending = float(data.get("hot_cash") or 0), float(data.get("pending") or 0)
            cash_lbl = QLabel("<b>Kasa:</b> " + CurrencyHelper.format_try_for_display(cash, db=self.db, include_try_reference=False))
            rec_lbl = QLabel("<b>Bekleyen Alacaklar:</b> " + CurrencyHelper.format_try_for_display(pending, db=self.db, include_try_reference=False))
            for lbl in (cash_lbl, rec_lbl):
                lbl.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
                self.footer_layout.addWidget(lbl)
            self.footer_layout.addStretch()
        except Exception as e:
            logger.error(f"Error in update_footer: {e}")
