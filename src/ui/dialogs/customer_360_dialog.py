# -*- coding: utf-8 -*-

from datetime import datetime
import re

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.dialogs.customer_vehicle_dialog import CustomerVehicleDialog
from src.ui.dialogs.payment_dialog import ModernPaymentDialog
from src.utils.theme_colors import tc, theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger
from src.utils.date_formatter import format_date
from src.utils.system_config import SystemConfig
from src.utils.toast_notification import show_error, show_success


class StatBox(QFrame):
    def __init__(self, title, value, icon_char, color, parent=None):
        super().__init__(parent)
        self.setFixedSize(170, 85)
        self.setStyleSheet(
            theme_qss(
                """
                QFrame {
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                """
            )
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(12)

        icon_frame = QFrame()
        icon_frame.setFixedSize(45, 45)
        icon_frame.setStyleSheet(f"background-color: {color}; border-radius: 8px;")
        if_layout = QVBoxLayout(icon_frame)
        if_layout.setContentsMargins(0, 0, 0, 0)

        lbl_icon = QLabel(icon_char)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet(
            theme_qss(
                "color: @selection_text; font-size: 20px; background: transparent;"
            )
        )
        if_layout.addWidget(lbl_icon)

        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)

        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 10px; font-weight: bold; background: transparent;"
            )
        )

        lbl_val = QLabel(str(value))
        lbl_val.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 16px; font-weight: 800; background: transparent;"
            )
        )

        txt_layout.addWidget(lbl_title)
        txt_layout.addWidget(lbl_val)

        layout.addWidget(icon_frame)
        layout.addLayout(txt_layout)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)


class Customer360Dialog(BaseModernDialog):
    def __init__(
        self, db, customer_id, customer_name, parent=None, sector_manager=None
    ):
        self.db = db
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.sector_manager = sector_manager
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                self.is_automotive = (
                    self.sector_manager.get_current_plugin().sector_id == "otomotiv"
                )
            else:
                self.is_automotive = (
                    SystemConfig.get_current_sector(self.db) == "otomotiv"
                )
        except Exception:
            self.is_automotive = False

        super().__init__(
            parent, title=f"Müşteri 360° - {customer_name}", width=1500, height=920
        )

        self.set_wheel_scroll_enabled(True)
        self.setup_modern_content()
        self.load_stats()
        self.load_cari_table()
        self.load_service_table()
        self.load_currency_ledger()
        self.load_sales_table()
        if self.is_automotive:
            self.load_vehicle_table()

    def setup_modern_content(self):
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 10)

        avatar = QLabel(self.customer_name[0].upper() if self.customer_name else "")
        avatar.setFixedSize(64, 64)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            theme_qss(
                """
                background-color: @accent;
                color: @selection_text;
                border-radius: 32px;
                font-size: 28px;
                font-weight: bold;
                """
            )
        )
        header.addWidget(avatar)

        info_layout = QVBoxLayout()
        name_lbl = QLabel(self.customer_name)
        name_lbl.setStyleSheet(
            theme_qss("font-size: 22px; font-weight: bold; color: @text;")
        )

        phone = "Bilinmiyor"
        try:
            cur = self.db.cursor
            cur.execute(
                """
                SELECT phone_number
                FROM devices
                WHERE (customer_id=? OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
                  AND COALESCE(is_deleted, 0) = 0
                ORDER BY entry_date DESC
                LIMIT 1
                """,
                (self.customer_id, self.customer_name),
            )
            row = cur.fetchone()
            if row and row[0]:
                phone = row[0]
        except Exception as e:
            logger.debug(f"Customer360 phone lookup fallback used: {e}")

        sub_lbl = QLabel(f"Telefon: {phone}")
        sub_lbl.setStyleSheet(theme_qss("font-size: 14px; color: @text_muted;"))

        info_layout.addWidget(name_lbl)
        info_layout.addWidget(sub_lbl)
        header.addLayout(info_layout)
        header.addStretch()

        self.content_layout.addLayout(header)

        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(20)
        self.content_layout.addLayout(self.stats_layout)

        self.currency_layout = QHBoxLayout()
        self.currency_layout.setSpacing(20)
        self.currency_layout.setContentsMargins(0, 10, 0, 10)
        self.content_layout.addLayout(self.currency_layout)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            theme_qss(
                """
                QTabWidget::pane {
                    border: 1px solid @border;
                    background: @surface;
                    border-radius: 12px;
                    top: -1px;
                }
                QTabBar::tab {
                    background: @surface_alt;
                    color: @text_muted;
                    padding: 10px 20px;
                    margin-right: 5px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    font-weight: 600;
                }
                QTabBar::tab:selected {
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-bottom: none;
                }
                """
            )
        )

        self.tab_service = QWidget()
        self.setup_service_tab()
        self.tabs.addTab(self.tab_service, "Servis Geçmişi")

        self.tab_cari = QWidget()
        self.setup_cari_tab()
        self.tabs.addTab(self.tab_cari, "Cari İşlem Geçmişi")

        self.tab_ledger = QWidget()
        self.setup_ledger_tab()
        self.tabs.addTab(self.tab_ledger, "Döviz Defteri")

        self.tab_sales = QWidget()
        self.setup_sales_tab()
        self.tabs.addTab(self.tab_sales, "Ürün Satışları")

        if self.is_automotive:
            self.tab_vehicles = QWidget()
            self.setup_vehicle_tab()
            self.tabs.addTab(self.tab_vehicles, "Araclar")

        self.content_layout.addWidget(self.tabs)

        footer = QHBoxLayout()
        self.btn_xlsx = QPushButton("Excel'e Aktar")
        self.btn_pdf = QPushButton("PDF'e Aktar")
        for b in (self.btn_xlsx, self.btn_pdf):
            b.setFixedSize(140, 36)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_xlsx.setStyleSheet(
            theme_qss(
                "background-color: @success; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_xlsx.clicked.connect(self.export_excel)
        self.btn_pdf.setStyleSheet(
            theme_qss(
                "background-color: @danger; color: @selection_text; border-radius: 6px; font-weight: bold;"
            )
        )
        self.btn_pdf.clicked.connect(self.export_pdf)

        footer.addStretch()
        footer.addWidget(self.btn_xlsx)
        footer.addWidget(self.btn_pdf)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(120, 36)
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(
            theme_qss(
                "background-color: @surface_alt; border: 1px solid @border; border-radius: 6px; color: @text;"
            )
        )
        footer.addWidget(btn_close)

        self.content_layout.addLayout(footer)

    def _table_qss(self):
        return theme_qss(
            """
            QTreeWidget {
                border: 1px solid @border;
                border-radius: 10px;
                background: @surface;
                color: @text;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                border: none;
                border-bottom: 1px solid @border;
                padding: 8px;
                font-weight: 700;
            }
            """
        )

    def setup_service_tab(self):
        l = QVBoxLayout(self.tab_service)
        self.table_service = QTreeWidget()
        self.table_service.setColumnCount(5)
        self.table_service.setHeaderLabels(
            ["Tarih", "Cihaz / Detay", "Durum", "Tutar", "Ödeme"]
        )
        self.table_service.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_service.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_service.setStyleSheet(self._table_qss())
        l.addWidget(self.table_service)

    def setup_cari_tab(self):
        l = QVBoxLayout(self.tab_cari)
        self.table_cari = QTreeWidget()
        self.table_cari.setColumnCount(7)
        self.table_cari.setHeaderLabels(
            [
                "Tarih / Zaman",
                "İşlem / Ürün Detayı",
                "Döviz",
                "Kur",
                "Tutar",
                "Durum",
                "Ödeme",
            ]
        )
        self.table_cari.setIndentation(12)
        self.table_cari.setRootIsDecorated(False)
        self.table_cari.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_cari.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            5, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.header().setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_cari.setStyleSheet(self._table_qss())
        l.addWidget(self.table_cari)

    def setup_ledger_tab(self):
        l = QVBoxLayout(self.tab_ledger)
        self.table_ledger = QTreeWidget()
        self.table_ledger.setColumnCount(5)
        self.table_ledger.setHeaderLabels(
            ["Tarih", "Döviz", "İşlem Tipi", "Miktar", "Kalan Bakiye"]
        )
        self.table_ledger.setStyleSheet(self._table_qss())
        l.addWidget(self.table_ledger)

    def setup_sales_tab(self):
        l = QVBoxLayout(self.tab_sales)
        self.table_sales = QTreeWidget()
        self.table_sales.setColumnCount(5)
        self.table_sales.setHeaderLabels(
            ["Tarih", "Satış / Detay", "Ödeme", "Tutar", "Kaynak"]
        )
        self.table_sales.header().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_sales.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.header().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table_sales.setStyleSheet(self._table_qss())
        l.addWidget(self.table_sales)

    def setup_vehicle_tab(self):
        l = QVBoxLayout(self.tab_vehicles)
        tools = QHBoxLayout()
        self.btn_add_vehicle = QPushButton("Yeni Arac Ekle")
        self.btn_edit_vehicle = QPushButton("Arac Duzenle")
        self.btn_refresh_vehicle = QPushButton("Bakim Gecmisi")
        for btn in (
            self.btn_add_vehicle,
            self.btn_edit_vehicle,
            self.btn_refresh_vehicle,
        ):
            btn.setFixedHeight(34)
        self.btn_add_vehicle.clicked.connect(self.open_add_vehicle)
        self.btn_edit_vehicle.clicked.connect(self.open_edit_vehicle)
        self.btn_refresh_vehicle.clicked.connect(self.load_vehicle_table)
        tools.addWidget(self.btn_add_vehicle)
        tools.addWidget(self.btn_edit_vehicle)
        tools.addWidget(self.btn_refresh_vehicle)
        tools.addStretch()
        l.addLayout(tools)

        self.table_vehicles = QTreeWidget()
        self.table_vehicles.setColumnCount(7)
        self.table_vehicles.setHeaderLabels(
            ["Plaka", "Marka", "Model", "Yil", "Arac Tipi", "Yakit", "KM"]
        )
        self.table_vehicles.header().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.table_vehicles.setStyleSheet(self._table_qss())
        self.table_vehicles.itemSelectionChanged.connect(self.load_vehicle_history)
        l.addWidget(self.table_vehicles)

        self.table_vehicle_history = QTreeWidget()
        self.table_vehicle_history.setColumnCount(5)
        self.table_vehicle_history.setHeaderLabels(
            ["Bakim Tarihi", "Sonraki Bakim", "Randevu", "Hatirlatma", "Foto"]
        )
        self.table_vehicle_history.setStyleSheet(self._table_qss())
        l.addWidget(self.table_vehicle_history)

    def load_stats(self):
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        while self.currency_layout.count():
            item = self.currency_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cur = self.db.conn.cursor()

        def _scalar(default=0):
            row = cur.fetchone()
            if not row:
                return default
            try:
                return row[0] if row[0] is not None else default
            except Exception:
                return default

        cur.execute(
            """
            SELECT COUNT(*)
            FROM devices
            WHERE (customer_id=? OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
              AND COALESCE(is_deleted, 0) = 0
            """,
            (self.customer_id, self.customer_name),
        )
        total_serv = _scalar(0)

        cur.execute(
            """
            SELECT COUNT(*)
            FROM devices
            WHERE (customer_id=? OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
              AND COALESCE(is_deleted, 0) = 0
              AND status NOT IN ('Teslim Edildi', 'İptal', 'Bitti')
            """,
            (self.customer_id, self.customer_name),
        )
        active_serv = _scalar(0)

        cur.execute(
            "SELECT SUM(try_equivalent) FROM currency_transactions WHERE customer_id=?",
            (self.customer_id,),
        )
        total_ciro = _scalar(0.0)

        self.stats_layout.addWidget(
            StatBox("Toplam İşlem", total_serv, "🔧", tc("accent", default="#3B82F6"))
        )
        self.stats_layout.addWidget(
            StatBox("Aktif İşlem", active_serv, "⚡", tc("warning", default="#F59E0B"))
        )
        self.stats_layout.addWidget(
            StatBox(
                "Toplam Ciro",
                CurrencyHelper.format_from_try(
                    total_ciro,
                    db=self.db,
                    currency_code=CurrencyHelper.get_code(self.db),
                ),
                "💰",
                tc("success", default="#10B981"),
            )
        )
        self.stats_layout.addStretch()

        def create_cur_box(label, val, currency_code, color):
            box = QFrame()
            box.setFixedSize(140, 80)
            box.setStyleSheet(
                theme_qss(
                    "background-color: @surface; border: 1px solid @border; border-radius: 12px;"
                )
            )
            l = QVBoxLayout(box)
            title = QLabel(label)
            title.setStyleSheet(
                theme_qss("color: @text_muted; font-size: 9px; font-weight: bold;")
            )
            v = QLabel(CurrencyHelper.format_amount(val, currency_code=currency_code))
            v.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 800;")
            l.addWidget(title)
            l.addWidget(v)
            return box

        def _bal(cur_code):
            try:
                cur.execute(
                    "SELECT balance FROM customer_currency_balances WHERE customer_id=? AND currency=?",
                    (self.customer_id, cur_code),
                )
                row = cur.fetchone()
                return row[0] if row else 0.0
            except Exception as e:
                logger.debug(f"Customer360 balance lookup failed for {cur_code}: {e}")
                return 0.0

        display_currency = CurrencyHelper.get_code(self.db)
        display_balance = 0.0
        for code in ("TRY", "USD", "EUR"):
            display_balance += CurrencyHelper.convert_amount(
                self.db,
                _bal(code),
                from_currency=code,
                to_currency=display_currency,
            )
        balance_color = (
            tc("success", default="#10B981")
            if display_balance >= 0
            else tc("danger", default="#EF4444")
        )
        balance_label = f"AKTIF BAKIYE ({display_currency})"
        if display_balance < 0:
            balance_label = f"BEKLEYEN ALACAK ({display_currency})"
        elif display_balance > 0:
            balance_label = f"MUSTERI ALACAGI ({display_currency})"
        self.currency_layout.addWidget(
            create_cur_box(
                balance_label,
                abs(display_balance),
                display_currency,
                balance_color,
            )
        )
        self.currency_layout.addStretch()

    def load_service_table(self):
        self.table_service.clear()
        cur = self.db.conn.cursor()
        display_currency = CurrencyHelper.get_code(self.db)
        cur.execute(
            """
            SELECT tracking_no, device_brand, device_model, status, entry_date, labor_cost, cargo_fee
            FROM devices
            WHERE (customer_id=? OR TRIM(UPPER(customer_name))=TRIM(UPPER(?)))
              AND COALESCE(is_deleted, 0) = 0
            ORDER BY entry_date DESC
            """,
            (self.customer_id, self.customer_name),
        )
        rows = cur.fetchall()
        for tno, brand, model, status, date, labor, cargo_fee in rows:
            used_parts_sum_query = "SELECT SUM(price * COALESCE(quantity, 1)) FROM used_parts WHERE tracking_no=?"
            used_parts_list_query = "SELECT part_name, price, COALESCE(quantity, 1) FROM used_parts WHERE tracking_no=?"
            try:
                cur.execute("PRAGMA table_info(used_parts)")
                cols = [row[1] for row in cur.fetchall() or []]
                deleted_col = (
                    "is_deleted"
                    if "is_deleted" in cols
                    else ("is_archived" if "is_archived" in cols else None)
                )
                if deleted_col:
                    used_parts_sum_query += (
                        f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
                    )
                    used_parts_list_query += (
                        f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
                    )
            except Exception:
                pass

            cur.execute(used_parts_sum_query, (tno,))
            part_sum = cur.fetchone()[0] or 0.0
            raw_total = float(labor or 0) + float(cargo_fee or 0) + float(part_sum)

            tx_cur = self.db.conn.cursor()
            tx_cur.execute(
                """
                SELECT
                    currency,
                    COALESCE(SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END), 0) AS debit_amount,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN transaction_type='DEBIT' AND COALESCE(current_balance, 0) < 0
                                THEN ABS(COALESCE(current_balance, 0))
                                ELSE 0
                            END
                        ),
                        0
                    ) AS remaining_amount
                FROM currency_transactions
                WHERE customer_id=? AND tracking_no=?
                GROUP BY currency
                ORDER BY CASE WHEN currency=? THEN 0 ELSE 1 END, currency
                """,
                (self.customer_id, tno, display_currency),
            )
            tx_rows = tx_cur.fetchall()

            if tx_rows:
                primary_currency = tx_rows[0][0] or display_currency
                total = float(tx_rows[0][1] or 0.0)
                remaining = max(0.0, float(tx_rows[0][2] or 0.0))
            else:
                primary_currency = display_currency
                total = raw_total
                remaining = raw_total

            item = QTreeWidgetItem(self.table_service)
            item.setText(0, format_date(date, self.db) if date else "")
            item.setText(1, f"{brand} {model} (#{tno})")
            item.setText(2, status)
            item.setText(
                3,
                CurrencyHelper.format_amount(
                    total,
                    db=self.db,
                    currency_code=primary_currency,
                ),
            )

            if remaining > 0.01:
                btn_pay = QPushButton(
                    "Ödeme Al ({amount})".format(
                        amount=CurrencyHelper.format_amount(
                            remaining,
                            db=self.db,
                            currency_code=primary_currency,
                        )
                    )
                )
                btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pay.setFixedHeight(28)
                btn_pay.setStyleSheet(
                    theme_qss(
                        """
                        QPushButton {
                            background: @success;
                            color: @selection_text;
                            border: none;
                            border-radius: 8px;
                            padding: 0 10px;
                            font-size: 11px;
                            font-weight: 700;
                        }
                        QPushButton:hover { background: @accent; }
                        """
                    )
                )
                btn_pay.clicked.connect(
                    lambda _=False, t=tno, a=remaining, c=primary_currency, b=brand, m=model: (
                        self._pay_service(t, a, c, f"{b} {m}")
                    )
                )
                self.table_service.setItemWidget(item, 4, btn_pay)

            if float(labor or 0) > 0:
                child = QTreeWidgetItem(item)
                child.setText(1, "↳ Servis İşçilik Ücreti")
                child.setText(
                    3,
                    CurrencyHelper.format_amount(
                        float(labor or 0),
                        db=self.db,
                        currency_code=primary_currency,
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            if float(cargo_fee or 0) > 0:
                child = QTreeWidgetItem(item)
                child.setText(1, "↳ Kargo Ücreti")
                child.setText(
                    3,
                    CurrencyHelper.format_amount(
                        float(cargo_fee or 0),
                        db=self.db,
                        currency_code=primary_currency,
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            cur.execute(used_parts_list_query, (tno,))
            for p_name, p_price, p_qty in cur.fetchall():
                child = QTreeWidgetItem(item)
                qty_text = f" x{int(p_qty or 1)}" if int(p_qty or 1) > 1 else ""
                child.setText(1, f"↳ {p_name}{qty_text}")
                child.setText(
                    3,
                    CurrencyHelper.format_amount(
                        float(p_price or 0) * int(p_qty or 1),
                        db=self.db,
                        currency_code=primary_currency,
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            item.setExpanded(True)

    def load_cari_table(self):
        self.table_cari.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT created_at, description, amount, currency, exchange_rate, try_equivalent, transaction_type, id, tracking_no, current_balance
            FROM currency_transactions
            WHERE customer_id = ?
            ORDER BY created_at DESC
            """,
            (self.customer_id,),
        )

        for (
            date,
            desc,
            amt,
            curr,
            rate,
            try_val,
            t_type,
            tid,
            tracking_no,
            current_balance,
        ) in cur.fetchall():
            parent = QTreeWidgetItem(self.table_cari)
            parent.setText(0, format_date(date, self.db))
            description_lines = self._split_description_lines(desc)
            type_label = (
                description_lines[0]
                if description_lines
                else ("Satış İşlemi" if t_type == "DEBIT" else "Ödeme (Tahsilat)")
            )
            color_hex = (
                tc("accent", default="#3B82F6")
                if t_type == "DEBIT"
                else tc("success", default="#10B981")
            )
            parent.setText(1, type_label)
            parent.setForeground(1, QColor(color_hex))
            parent.setText(2, curr)
            parent.setText(3, f"{rate:.4f}" if rate else "1.0000")
            parent.setText(
                4,
                CurrencyHelper.format_amount(
                    float(amt or 0), currency_code=curr or "TRY"
                ),
            )

            is_settled = False
            remaining_debt = float(amt or 0)
            if t_type == "DEBIT":
                if current_balance is not None:
                    try:
                        remaining_debt = max(0.0, -float(current_balance or 0.0))
                    except Exception:
                        remaining_debt = float(amt or 0)
                else:
                    # Legacy fallback: current_balance boş eski satırlar için kaba hesap.
                    chk = self.db.conn.cursor()
                    if tracking_no:
                        chk.execute(
                            """SELECT COALESCE(SUM(amount), 0)
                               FROM currency_transactions
                               WHERE customer_id=? AND transaction_type='CREDIT' AND tracking_no=? AND currency=?""",
                            (self.customer_id, tracking_no, curr),
                        )
                    else:
                        chk.execute(
                            """SELECT COALESCE(SUM(amount), 0)
                               FROM currency_transactions
                               WHERE customer_id=? AND transaction_type='CREDIT' AND id > ? AND currency=?""",
                            (self.customer_id, tid, curr),
                        )
                    paid_total = float(chk.fetchone()[0] or 0)
                    remaining_debt = max(0.0, float(amt or 0) - paid_total)
                is_settled = remaining_debt <= 0.01

            if t_type == "DEBIT":
                status = "Tahsil Edildi" if is_settled else "Tahsilat Bekliyor"
                status_color = tc("success") if is_settled else tc("warning")
            else:
                status = "Tamamlandı"
                status_color = tc("success")

            parent.setText(5, status)
            parent.setForeground(5, QColor(status_color))
            parent.setText(6, "")

            if t_type == "DEBIT" and not is_settled:
                btn_pay = QPushButton(
                    f"Odeme Al ({CurrencyHelper.format_amount(remaining_debt, currency_code=curr or 'TRY')})"
                )
                btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_pay.setFixedSize(160, 30)
                btn_pay.setStyleSheet(
                    theme_qss(
                        """
                        QPushButton {
                            background: @success;
                            color: @selection_text;
                            border: none;
                            border-radius: 10px;
                            padding: 0 12px;
                            font-size: 11px;
                            font-weight: 800;
                        }
                        QPushButton:hover {
                            background: @accent;
                        }
                        """
                    )
                )
                btn_pay.clicked.connect(
                    lambda _=False, currency=curr, amount=remaining_debt, ref_tracking=tracking_no, ref_desc=desc, debt_id=tid: (
                        self.open_payment_dialog(
                            currency,
                            amount,
                            ref_tracking,
                            ref_desc,
                            preselected_debt_ids=[debt_id],
                        )
                    )
                )
                self.table_cari.setItemWidget(parent, 6, btn_pay)

            for line in description_lines[1:]:
                child = QTreeWidgetItem(parent)
                child.setText(1, f"-> {line}")
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))

            if tracking_no:
                self._append_tracking_parts(parent, tracking_no)
            else:
                t_match = re.search(r"#([A-Z]+-\d+|\d+)", desc or "", re.IGNORECASE)
                if t_match:
                    self._append_tracking_parts(parent, t_match.group(1))

            parent.setExpanded(True)

    def _split_description_lines(self, description):
        return [
            line.strip() for line in str(description or "").splitlines() if line.strip()
        ]

    def _append_tracking_parts(self, parent, tracking_no):
        try:
            cur = self.db.conn.cursor()
            cur.execute("PRAGMA table_info(used_parts)")
            cols = [row[1] for row in cur.fetchall() or []]
            deleted_col = (
                "is_deleted"
                if "is_deleted" in cols
                else ("is_archived" if "is_archived" in cols else None)
            )
            has_qty = "quantity" in cols
            query = "SELECT part_name, price, COALESCE(quantity, 1) FROM used_parts WHERE tracking_no=?"
            if not has_qty:
                query = "SELECT part_name, price, 1 FROM used_parts WHERE tracking_no=?"
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            cur.execute(query, (tracking_no,))
            for p_name, p_price, p_qty in cur.fetchall():
                qty = int(p_qty or 1)
                qty_text = f" x{qty}" if qty > 1 else ""
                child = QTreeWidgetItem(parent)
                child.setText(1, f"-> {p_name}{qty_text}")
                child.setText(
                    4,
                    CurrencyHelper.format_from_try(
                        float(p_price or 0) * qty,
                        db=self.db,
                        currency_code=CurrencyHelper.get_code(self.db),
                    ),
                )
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))
        except Exception as exc:
            logger.debug(f"Customer360 tracking part detail append skipped: {exc}")

    def _pay_service(self, tracking_no, amount, currency, device_label):
        """Servis listesinden doğrudan ödeme al"""
        desc = f"Servis tahsilatı - {device_label} (#{tracking_no})"
        preselected_debt_ids = self._get_open_debt_ids_for_tracking(
            tracking_no, currency
        )
        remaining_amount = self._get_remaining_debt_for_tracking(tracking_no, currency)
        self.open_payment_dialog(
            currency=currency,
            amount=remaining_amount if remaining_amount > 0 else amount,
            tracking_no=tracking_no,
            reference_desc=desc,
            preselected_debt_ids=preselected_debt_ids,
        )
        self.load_service_table()

    def _get_open_debt_ids_for_tracking(self, tracking_no, currency=None):
        try:
            query = """
                SELECT id
                FROM currency_transactions
                WHERE customer_id=?
                  AND tracking_no=?
                  AND transaction_type='DEBIT'
                  AND (current_balance < 0 OR current_balance IS NULL)
            """
            params = [self.customer_id, tracking_no]
            if currency:
                query += " AND currency=?"
                params.append(currency)
            query += " ORDER BY created_at ASC, id ASC"
            cur = self.db.conn.cursor()
            cur.execute(query, tuple(params))
            return [row[0] for row in (cur.fetchall() or [])]
        except Exception as exc:
            logger.debug(
                f"Customer360 open debt lookup skipped for {tracking_no}: {exc}"
            )
            return []

    def _get_remaining_debt_for_tracking(self, tracking_no, currency=None):
        try:
            query = """
                SELECT COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type='DEBIT' AND current_balance < 0 THEN ABS(current_balance)
                            ELSE 0
                        END
                    ),
                    0
                )
                FROM currency_transactions
                WHERE customer_id=? AND tracking_no=?
            """
            params = [self.customer_id, tracking_no]
            if currency:
                query += " AND currency=?"
                params.append(currency)
            cur = self.db.conn.cursor()
            cur.execute(query, tuple(params))
            row = cur.fetchone()
            return float(row[0] or 0.0) if row else 0.0
        except Exception as exc:
            logger.debug(
                f"Customer360 remaining debt lookup skipped for {tracking_no}: {exc}"
            )
            return 0.0

    def open_payment_dialog(
        self,
        currency=None,
        amount=None,
        tracking_no=None,
        reference_desc=None,
        preselected_debt_ids=None,
    ):
        dlg = ModernPaymentDialog(
            self, self.db, {"id": self.customer_id, "name": self.customer_name}
        )
        if currency:
            dlg._apply_selected_currency(currency)
        if preselected_debt_ids:
            dlg.selected_debts = set(preselected_debt_ids)
            dlg._refresh_debt_list()
            dlg._update_selected_total()
        if amount and float(amount or 0) > 0:
            dlg.inp_amount.setText(
                f"{float(amount):,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        dlg.reference_tracking_no = tracking_no
        dlg.reference_desc = reference_desc

        if dlg.exec():
            data = dlg.get_data() or {}
            if self._save_payment(data):
                self.load_stats()
                self.load_service_table()
                self.load_cari_table()
                self.load_currency_ledger()
                parent = self.parent()
                if parent and hasattr(parent, "request_reload"):
                    try:
                        parent.request_reload(delay_ms=0)
                    except TypeError:
                        parent.request_reload()

    def _save_payment(self, data):
        try:
            currency = data.get("currency", "TRY")
            exchange_rate = float(data.get("exchange_rate", 1.0) or 1.0)
            amount = float(data.get("amount", 0) or 0)
            if amount <= 0:
                return False

            base_desc = (data.get("notes") or "").strip()
            reference_tracking = data.get("reference_tracking_no") or None
            reference_desc = (data.get("reference_desc") or "").strip()
            ref_prefix = f"Ref: {reference_tracking}" if reference_tracking else ""
            full_desc = base_desc or "Cari borç kapatma tahsilatı"
            if ref_prefix:
                full_desc = f"{ref_prefix} | {full_desc}"
            if reference_desc:
                full_desc = (
                    f"{full_desc} | Borç Kaydı: {reference_desc.splitlines()[0][:120]}"
                )

            date_value = data.get("date")
            created_at = None
            accounting_date = None
            if date_value:
                parsed = QDate.fromString(str(date_value), "dd.MM.yyyy")
                if parsed.isValid():
                    accounting_date = parsed.toString("yyyy-MM-dd")
                    created_at = (
                        f"{accounting_date} {datetime.now().strftime('%H:%M:%S')}"
                    )

            saved = self.db.add_currency_transaction(
                customer_id=self.customer_id,
                amount=amount,
                currency=currency,
                transaction_type="CREDIT",
                exchange_rate=exchange_rate,
                description=full_desc,
                tracking_no=reference_tracking,
                created_at=created_at,
            )
            if not saved:
                show_error(self, "Ödeme kaydedilemedi.")
                return False

            payment_txn_id = None
            try:
                payment_txn_id = self.db.get_last_currency_transaction_id()
            except Exception:
                payment_txn_id = None

            if payment_txn_id:
                try:
                    self.db.create_payment_debt_links_table()
                except Exception:
                    pass
                try:
                    self.db.apply_payment_to_debts(
                        customer_id=self.customer_id,
                        payment_amount=amount,
                        currency=currency,
                        payment_transaction_id=payment_txn_id,
                        selected_debt_ids=data.get("selected_debt_ids") or None,
                    )
                except Exception as allocation_exc:
                    logger.warning(
                        f"Customer360 debt allocation skipped: {allocation_exc}"
                    )

            tl_amount = amount * (exchange_rate if currency != "TRY" else 1.0)

            try:
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Tahsilat",
                    amount=tl_amount,
                    description=full_desc,
                    customer_name=self.customer_name,
                    customer_id=self.customer_id,
                    date=accounting_date,
                    payment_method=data.get("method"),
                    bank_account_id=data.get("bank_account_id"),
                    tracking_no=reference_tracking,
                    ref_no=reference_tracking,
                    currency=currency,
                    original_amount=amount,
                )
            except Exception as accounting_exc:
                logger.warning(
                    f"Customer360 accounting mirror save skipped: {accounting_exc}"
                )

            show_success(self, "Tahsilat kaydedildi.")
            return True
        except Exception as exc:
            logger.exception("Customer360 payment save failed")
            show_error(self, f"Ödeme kaydı sırasında hata: {exc}")
            return False

    def load_currency_ledger(self):
        self.table_ledger.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT created_at, currency, transaction_type, amount, current_balance
            FROM currency_transactions
            WHERE customer_id = ? AND currency != 'TRY'
            ORDER BY created_at DESC
            """,
            (self.customer_id,),
        )
        for created_at, currency, tx_type, amount, balance in cur.fetchall():
            item = QTreeWidgetItem(self.table_ledger)
            item.setText(0, format_date(created_at, self.db))
            item.setText(1, currency)
            item.setText(2, "Borç" if tx_type == "DEBIT" else "Alacak")
            item.setText(3, f"{amount:,.2f}")
            item.setText(4, f"{balance:,.2f}")

    def load_sales_table(self):
        self.table_sales.clear()
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT date, description, amount, COALESCE(payment_method, ''), COALESCE(category, ''), COALESCE(currency, 'TRY')
            FROM accounting
            WHERE customer_id = ?
              AND type = 'Gelir'
              AND (
                    category = 'Satış'
                    OR description LIKE 'POS%'
                    OR description LIKE '%Satış%'
                  )
            ORDER BY date DESC, id DESC
            """,
            (self.customer_id,),
        )
        for (
            date,
            description,
            amount,
            payment_method,
            category,
            currency,
        ) in cur.fetchall():
            parent = QTreeWidgetItem(self.table_sales)
            parent.setText(0, format_date(date, self.db))
            lines = [
                line.strip()
                for line in str(description or "").splitlines()
                if line.strip()
            ]
            parent.setText(1, lines[0] if lines else "Ürün Satışı")
            parent.setText(2, payment_method or "Belirtilmedi")
            parent.setText(
                3,
                CurrencyHelper.format_amount(
                    float(amount or 0), currency_code=currency or "TRY"
                ),
            )
            parent.setText(4, category or "Satış")
            for line in lines[1:]:
                child = QTreeWidgetItem(parent)
                child.setText(1, f"↳ {line}")
                child.setForeground(1, QColor(tc("text_muted", default="#64748B")))
            parent.setExpanded(True)

    def load_vehicle_table(self):
        if not self.is_automotive:
            return
        self.table_vehicles.clear()
        vehicles = list(self.db.get_customer_vehicles(self.customer_id) or [])
        for row in vehicles:
            item = QTreeWidgetItem(self.table_vehicles)
            item.setData(0, Qt.ItemDataRole.UserRole, row["id"])
            item.setText(0, str(row["plate"] or ""))
            item.setText(1, str(row["brand"] or ""))
            item.setText(2, str(row["model"] or ""))
            item.setText(3, str(row["year"] or ""))
            item.setText(4, str(row["vehicle_type"] or ""))
            item.setText(5, str(row["fuel_type"] or ""))
            item.setText(6, str(row["last_known_odometer"] or 0))
        self.load_vehicle_history()

    def load_vehicle_history(self):
        if not self.is_automotive:
            return
        self.table_vehicle_history.clear()
        selected = self.table_vehicles.currentItem()
        if not selected:
            return
        plate = selected.text(0).strip()
        for row in self.db.get_vehicle_maintenance_cards(plate):
            if str(row["vehicle_plate"] or "").strip().upper() != plate.upper():
                continue
            item = QTreeWidgetItem(self.table_vehicle_history)
            item.setText(0, str(row["service_date"] or ""))
            item.setText(1, str(row["next_maintenance_date"] or ""))
            item.setText(2, str(row["appointment_date"] or ""))
            item.setText(3, str(row["reminder_date"] or ""))
            item.setText(4, str(row["photo_count"] or 0))

    def open_add_vehicle(self):
        if not self.is_automotive:
            return
        dlg = CustomerVehicleDialog(
            self.db, self.customer_id, self.customer_name, parent=self
        )
        if dlg.exec():
            self.load_vehicle_table()
            show_success(self, "Arac kaydedildi.")

    def open_edit_vehicle(self):
        if not self.is_automotive:
            return
        selected = self.table_vehicles.currentItem()
        if not selected:
            show_error(self, "Duzenlemek icin bir arac secin.")
            return
        vehicle_id = selected.data(0, Qt.ItemDataRole.UserRole)
        row = self.db.get_customer_vehicle(vehicle_id)
        dlg = CustomerVehicleDialog(
            self.db, self.customer_id, self.customer_name, vehicle_row=row, parent=self
        )
        if dlg.exec():
            self.load_vehicle_table()
            show_success(self, "Arac guncellendi.")

    def export_excel(self):
        from src.utils.toast_notification import show_info

        show_info(self, "Veriler Excel'e aktarılıyor...")

    def export_pdf(self):
        from src.utils.toast_notification import show_info

        show_info(self, "PDF raporu hazırlanıyor...")
