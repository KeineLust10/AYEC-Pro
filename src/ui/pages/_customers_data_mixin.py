# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter
from PyQt6.QtWidgets import QTableWidgetItem, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton

from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import tc, qc, theme_qss
from src.utils.performance_monitor import perf_span
from src.ui.pages.customers_page_parts import CustomerWorker
from src.ui.widgets.navigation_glyph import navigation_icon


def _format_reference_customer_phone(value):
    text = str(value or "\u2014")
    digits = "".join(character for character in text if character.isdigit())
    if len(digits) == 11 and digits.startswith("0"):
        return "{} {} {} {}".format(digits[:4], digits[4:7], digits[7:9], digits[9:])
    return text


class _CustomerStatusPill(QFrame):
    def __init__(self, background, parent=None):
        super().__init__(parent)
        self._pill_background = QColor(background)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._pill_background)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2.0
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()


class _CustomerSortItem(QTableWidgetItem):
    def __init__(self, sort_value):
        super().__init__("")
        self.setData(Qt.ItemDataRole.UserRole + 1, sort_value)

    def __lt__(self, other):
        left = self.data(Qt.ItemDataRole.UserRole + 1)
        right = other.data(Qt.ItemDataRole.UserRole + 1)
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return left < right
        return str(left or "").casefold() < str(right or "").casefold()


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
        if self.current_filter_type == "OPEN_SERVICES":
            customers_list = [
                row for row in customers_list
                if int(row.get("open_service_count", 0) or 0) > 0
            ]
        self._refresh_customer_locations(customers_list)
        self.total_count = max(len(customers_list), int(total or 0))
        if hasattr(self, "_customer_metric_values"):
            debt_total = sum(max(0.0, float(row["balance_try"] if "balance_try" in row.keys() else 0)) for row in customers_list)
            advance_total = 0.0
            debt_customer_count = sum(1 for row in customers_list if float(row["balance_try"] if "balance_try" in row.keys() else 0) > 0)
            vip_count = sum(
                1
                for row in customers_list
                if "VIP" in str(row["contract_type"] if "contract_type" in row.keys() else "").upper()
                or str(row["type"] if "type" in row.keys() else "").casefold() == "vip"
            )
            customer_total = len(customers_list)
            try:
                aggregate = self.db.cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(MAX(COALESCE(balance_try, 0), 0)), 0),
                        0,
                        COALESCE(SUM(CASE WHEN COALESCE(balance_try, 0) > 0 THEN 1 ELSE 0 END), 0),
                        COALESCE(SUM(CASE WHEN UPPER(COALESCE(c.contract_type, '')) LIKE '%VIP%' OR LOWER(COALESCE(c.type, ''))='vip' THEN 1 ELSE 0 END), 0),
                        COUNT(*)
                    FROM customers c
                    LEFT JOIN (
                        SELECT customer_id,
                               SUM(CASE WHEN currency='TRY' THEN balance ELSE 0 END) AS balance_try
                        FROM customer_currency_balances
                        GROUP BY customer_id
                    ) b ON b.customer_id=c.id
                    WHERE COALESCE(c.is_deleted, 0)=0
                      AND COALESCE(c.is_partner, 0)=0
                    """
                ).fetchone()
                if aggregate:
                    debt_total = float(aggregate[0] or 0)
                    advance_total = float(aggregate[1] or 0)
                    debt_customer_count = int(aggregate[2] or 0)
                    vip_count = int(aggregate[3] or 0)
                    customer_total = int(aggregate[4] or 0)
            except Exception:
                pass
            device_count = 0
            assembly_count = 0
            test_count = 0
            try:
                device_count = int(self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE status NOT LIKE '%Teslim Edildi%' AND LOWER(status) NOT LIKE '%teslimata haz%' AND status NOT LIKE '%Iptal%'").fetchone()[0] or 0)
                assembly_count = int(self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE LOWER(status) LIKE '%montaj%'").fetchone()[0] or 0)
                test_count = int(self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE LOWER(status) LIKE '%test%'").fetchone()[0] or 0)
            except Exception:
                pass
            usd_receivable = 0.0
            usd_advance = 0.0
            try:
                usd_values = self.db.cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN UPPER(currency)='USD' AND balance > 0 THEN balance ELSE 0 END), 0),
                        0
                    FROM customer_currency_balances
                    """
                ).fetchone()
                if usd_values:
                    usd_receivable = float(usd_values[0] or 0)
                    usd_advance = float(usd_values[1] or 0)
            except Exception:
                pass
            self._customer_metric_captions[0].setText(
                "{} Bor\u00e7lu M\u00fc\u015fteri Portf\u00f6y\u00fc".format(debt_customer_count)
            )
            self._customer_metric_secondary[0].setText(
                "USD: {}{:,.2f}".format(chr(36), usd_receivable)
            )
            self._customer_metric_captions[1].setText(
                "Dengeli \u2022 A\u00e7\u0131k Avans Yok"
                if advance_total <= 0
                else "A\u00e7\u0131k Avans: {:,.2f} TRY".format(advance_total)
            )
            self._customer_metric_secondary[1].setText(
                "USD: {}{:,.2f}".format(chr(36), usd_advance)
            )
            self._customer_metric_captions[2].setText(
                "{} At\u00f6lye Montaj \u2022 {} Testte".format(assembly_count, test_count)
            )
            for metric_label, amount in zip(
                self._customer_metric_values[:2],
                (debt_total, advance_total),
            ):
                whole, fraction = "{:,.2f}".format(amount).split(".")
                metric_label.setText(
                    "<span style='font-size:32px;font-weight:700;color:#f8fafc'>{}{}</span>"
                    "<span style='font-size:16px;font-weight:400;color:#94a3b8'>.{}</span>"
                    "<span style='font-size:10px;font-weight:700;color:#00dce6'> TRY</span>".format(
                        chr(0x20BA), whole, fraction
                    )
                )
            self._customer_metric_values[2].setText(
                "<span style='font-size:32px;font-weight:700;color:#00f2fe'>{}</span> "
                "<span style='font-size:18px;font-weight:500;color:#f8fafc'>Adet Aktif</span>".format(
                    device_count
                )
            )
            vip_rate = (vip_count / customer_total * 100.0) if customer_total else 0.0
            vip_whole, vip_fraction = "{:.1f}".format(vip_rate).split(".")
            self._customer_metric_values[3].setText(
                "<span style='font-size:32px;font-weight:700;color:#f8fafc'>%{}</span>"
                "<span style='font-size:16px;font-weight:400;color:#94a3b8'>.{}</span>".format(
                    vip_whole, vip_fraction
                )
            )
            if hasattr(self, "_customer_metric_bars") and len(self._customer_metric_bars) > 3:
                self._customer_metric_bars[3].setValue(round(vip_rate))
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
        self.total_count = max(self.total_count, self.table.rowCount())
        self.lbl_total.setText(f"Toplam Kayıt: {self.total_count}")
        self.lbl_time.setText(
            "Son G\u00fcncelleme: {}".format(datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        )
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        self._update_pagination_ui()
        self._apply_customer_toolbar_filters()
        self._try_run_pending_reload()

    def _refresh_customer_locations(self, customers):
        combo = getattr(self, "customer_location_filter", None)
        if combo is None:
            return
        selected = combo.currentData()
        locations = sorted({
            str(row.get("city") or row.get("location") or "").strip()
            for row in customers
            if str(row.get("city") or row.get("location") or "").strip()
        })
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("T\u00fcm Lokasyonlar (\u0130l / \u0130l\u00e7e)", "")
        for location in locations:
            combo.addItem(location, location)
        selected_index = combo.findData(selected)
        combo.setCurrentIndex(selected_index if selected_index >= 0 else 0)
        combo.blockSignals(False)

    def _add_row(self, row_idx, data):
        try:
            self.table.insertRow(row_idx)
            compact_table = self.table.viewport().width() < 1100

            customer_id = data["id"]
            check_item = QTableWidgetItem("")
            check_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            check_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row_idx, 0, check_item)
            customer_id_text = "#{:03d}".format(int(customer_id))
            item_id = _CustomerSortItem(int(customer_id))
            item_id.setFont(QFont("JetBrains Mono", 9, QFont.Weight.Bold))
            item_id.setForeground(qc("accent"))
            item_id.setData(Qt.ItemDataRole.UserRole, data)
            self.table.setItem(row_idx, 1, item_id)
            customer_type = str(data.get("type") or "").casefold()
            contract_type = str(data.get("contract_type") or "").upper()
            customer_balance = float(data.get("balance_try", 0.0) or 0.0)
            id_is_problematic = str(data.get("is_problematic", 0) or 0).strip().lower() not in {
                "", "0", "false", "no"
            }
            if customer_balance < 0 or id_is_problematic:
                id_badge_color = "#ef4444"
            elif "bayi" in customer_type:
                id_badge_color = "#00f2fe"
            elif "VIP" in contract_type and customer_type == "kurumsal":
                id_badge_color = "#f59e0b"
            elif "VIP" in contract_type:
                id_badge_color = "#00f2fe"
            elif int(customer_id) == 2:
                id_badge_color = "#adc6ff"
            else:
                id_badge_color = "#94a3b8"
            id_badge = QLabel(customer_id_text)
            id_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            id_badge.setStyleSheet(
                "QLabel { color: %s; background: rgba(%d, %d, %d, 26); "
                "border: none; border-radius: 4px; padding: 2px 8px; "
                "font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }"
                % (
                    id_badge_color,
                    QColor(id_badge_color).red(),
                    QColor(id_badge_color).green(),
                    QColor(id_badge_color).blue(),
                )
            )
            id_cell = QWidget()
            id_cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            id_cell.setStyleSheet("background: transparent; border: none;")
            id_cell_layout = QHBoxLayout(id_cell)
            id_cell_layout.setContentsMargins(4, 0, 0, 0)
            id_cell_layout.addWidget(
                id_badge,
                alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )
            self.table.setCellWidget(row_idx, 1, id_cell)
            item_id.setForeground(QColor(0, 0, 0, 0))

            name_display = str(data["name"])
            keys = data.keys() if hasattr(data, "keys") else []
            cust_type = str(data["type"] or "").strip() if "type" in keys else ""

            tax_id = str(data.get("tc_no") or data.get("tax_number") or data.get("tax_no") or "").strip()
            company = (
                data["company_name"]
                if "company_name" in keys and data["company_name"]
                else ""
            )
            district = str(data.get("district") or "").strip()
            city = str(data.get("city") or "").strip()
            location = ", ".join(part for part in (district, city) if part)
            name_item = _CustomerSortItem(name_display)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            name_item.setFont(QFont("Times New Roman", 10, QFont.Weight.DemiBold))
            if cust_type.casefold() in {"kurumsal", "vip", "tedarik\u00e7i"} or "bayi" in cust_type.casefold():
                name_item.setForeground(qc("selection_text"))
            self.table.setItem(row_idx, 2, name_item)
            identity = QWidget()
            identity.setStyleSheet(theme_qss("background: transparent; border: none;"))
            identity_layout = QHBoxLayout(identity)
            identity_layout.setContentsMargins(0, 0, 0, 0)
            identity_layout.setSpacing(10)
            initials = "".join(part[0] for part in name_display.split()[:2] if part).upper() or "M"
            avatar = QLabel(initials)
            avatar.setFixedSize(27, 27)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_palette = ("#00f2fe", "#adc6ff", "#f59e0b", "#10b981", "#ef4444", "#b9cacb", "#00dce6")
            avatar_color = QColor(avatar_palette[row_idx % len(avatar_palette)])
            avatar_color.setAlpha(38)
            avatar.setProperty("skipThemeTransform", True)
            avatar.setStyleSheet(
                "QLabel { background: rgba(" + str(avatar_color.red()) + "," +
                str(avatar_color.green()) + "," + str(avatar_color.blue()) + "," +
                str(avatar_color.alpha()) + "); color: " +
                avatar_palette[row_idx % len(avatar_palette)] + "; border: 1px solid " +
                avatar_palette[row_idx % len(avatar_palette)] + "; border-radius: 8px; "
                "font-size: 11px; font-weight: 800; }"
            )
            identity_text = QVBoxLayout()
            identity_text.setContentsMargins(0, 0, 0, 0)
            identity_text.setSpacing(3)
            identity_name = QLabel(str(data["name"]))
            identity_name.setWordWrap(True)
            identity_name.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 700; border: none; background: transparent;"))
            identity_line = QHBoxLayout()
            identity_line.setContentsMargins(0, 0, 0, 0)
            identity_line.setSpacing(6)
            identity_line.addWidget(identity_name)
            if "VIP" in str(data.get("contract_type") or "").upper():
                vip_badge = QLabel("VIP")
                vip_badge.setFixedSize(38, 22)
                vip_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                vip_badge.setStyleSheet(theme_qss("QLabel { background: @surface_alt; color: @warning; border: 1px solid @warning; border-radius: 5px; padding: 1px 6px; font-size: 10px; font-weight: 800; }"))
                identity_line.addWidget(vip_badge)
            identity_line.addStretch(1)
            identity_text.addLayout(identity_line)
            identity_meta = QWidget()
            identity_meta.setStyleSheet("background: transparent; border: none;")
            meta_layout = QVBoxLayout(identity_meta)
            meta_layout.setContentsMargins(0, 0, 0, 0)
            meta_layout.setSpacing(2)
            if company and company.casefold() != name_display.casefold():
                company_label = QLabel(company)
                company_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none; background: transparent;"))
                meta_layout.addWidget(company_label)
            if location:
                location_row = QHBoxLayout()
                location_row.setContentsMargins(0, 0, 0, 0)
                location_row.setSpacing(3)
                location_icon = QLabel()
                location_icon.setFixedSize(11, 11)
                location_icon.setPixmap(navigation_icon("pin", 11, "text_muted").pixmap(11, 11))
                location_label = QLabel(location)
                location_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none; background: transparent;"))
                location_row.addWidget(location_icon)
                location_row.addWidget(location_label)
                location_row.addStretch(1)
                meta_layout.addLayout(location_row)
            elif tax_id:
                tax_label = QLabel(("VN: " if cust_type.casefold() in {"kurumsal", "vip", "bayi"} else "TC: ") + tax_id)
                tax_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none; background: transparent;"))
                meta_layout.addWidget(tax_label)
            identity_text.addWidget(identity_meta)
            identity_layout.addWidget(avatar)
            identity_layout.addLayout(identity_text, 1)
            self.table.setCellWidget(row_idx, 2, identity)

            comp_item = _CustomerSortItem(cust_type or "Bireysel")
            comp_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            comp_item.setForeground(qc("accent" if cust_type.casefold() in {"kurumsal", "vip"} or "bayi" in cust_type.casefold() else "text"))
            self.table.setItem(row_idx, 3, comp_item)
            contract_type = str(data.get("contract_type") or "").upper()
            is_vip = "VIP" in contract_type or cust_type.casefold() == "vip"
            is_vip_segment = is_vip and cust_type.casefold() in {"kurumsal", "vip"}
            segment_text = "VIP KURUMSAL" if is_vip_segment else "Kurumsal Bayi" if "bayi" in cust_type.casefold() else cust_type or "Bireysel"
            type_badge = QLabel(segment_text)
            type_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_badge.setStyleSheet(theme_qss("QLabel { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 4px 8px; font-size: 10px; font-weight: 700; }"))
            if is_vip_segment:
                type_badge.setStyleSheet(theme_qss("QLabel { background: @surface_alt; color: @warning; border: 1px solid @warning; border-radius: 8px; padding: 4px 8px; font-size: 10px; font-weight: 700; }"))
            elif cust_type.casefold() in {"kurumsal", "vip"} or "bayi" in cust_type.casefold():
                type_badge.setStyleSheet(theme_qss("QLabel { background: @accent; color: @selection_text; border: 1px solid @accent; border-radius: 8px; padding: 4px 8px; font-size: 10px; font-weight: 700; }"))
            if compact_table:
                type_badge.setStyleSheet(
                    type_badge.styleSheet()
                    .replace("padding: 4px 8px", "padding: 2px 4px")
                    .replace("font-size: 10px", "font-size: 8px")
                    .replace("border-radius: 8px", "border-radius: 6px")
                )
            type_container = QWidget()
            type_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
            type_layout = QHBoxLayout(type_container)
            type_layout.setContentsMargins(0, 0, 0, 0)
            type_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_layout.addWidget(type_badge)
            self.table.setCellWidget(row_idx, 3, type_container)

            phone = _format_reference_customer_phone(data["phone"])
            email = str(data["email"] or "\u2014")
            contact_item = _CustomerSortItem(phone)
            contact_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            contact_item.setFont(QFont("JetBrains Mono", 9))
            self.table.setItem(row_idx, 4, contact_item)
            contact_container = QWidget()
            contact_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
            contact_layout = QVBoxLayout(contact_container)
            contact_layout.setContentsMargins(0, 0, 0, 0)
            contact_layout.setSpacing(4)
            phone_label = QLabel(f"\u260e  {phone}")
            phone_label.setStyleSheet(theme_qss("color: @text; font-family: 'JetBrains Mono'; font-size: 12px; border: none; background: transparent;"))
            phone_label.setToolTip(phone)
            email_label = QLabel(f"\u2709  {email}")
            email_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
            email_label.setToolTip(email)
            contact_layout.addWidget(phone_label)
            contact_layout.addWidget(email_label)
            self.table.setCellWidget(row_idx, 4, contact_container)

            try:
                balances = {
                    "TRY": float(data["balance_try"]) if "balance_try" in keys else 0.0,
                    "USD": float(data["balance_usd"]) if "balance_usd" in keys else 0.0,
                    "EUR": float(data["balance_eur"]) if "balance_eur" in keys else 0.0,
                }
            except Exception:
                balances = {"TRY": 0.0}

            service_count = int(data.get("open_service_count", 0) or 0)
            pending_offer_count = int(data.get("pending_offer_count", 0) or 0)
            service_item = QTableWidgetItem(str(service_count))
            service_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if service_count:
                service_item.setForeground(qc("accent"))
            self.table.setItem(row_idx, 5, service_item)
            service_container = QWidget()
            service_container.setStyleSheet("background: transparent; border: none;")
            service_layout = QHBoxLayout(service_container)
            service_layout.setContentsMargins(0, 0, 0, 0)
            service_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if pending_offer_count:
                offer_label = QLabel("{} Teklif Yan\u0131t\u0131 Bekliyor".format(pending_offer_count))
                offer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                offer_label.setWordWrap(True)
                offer_label.setStyleSheet(
                    "QLabel { background: rgba(245,158,11,0.12); color: #f59e0b; "
                    "border: none; border-radius: 7px; padding: 4px 7px; "
                    "font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 10px; font-weight: 700; }"
                )
                service_layout.addWidget(offer_label)
            elif service_count:
                open_test_count = int(data.get("open_test_count", 0) or 0)
                open_repair_count = int(data.get("open_repair_count", 0) or 0)
                maintenance_count = int(data.get("open_maintenance_count", 0) or 0)
                delivery_ready_count = int(data.get("open_delivery_ready_count", 0) or 0)
                service_details = []
                if open_test_count:
                    service_details.append("{} Test".format(open_test_count))
                if open_repair_count:
                    service_details.append("{} Onar\u0131m".format(open_repair_count))
                if maintenance_count and maintenance_count < service_count:
                    service_details.append("{} Y\u0131ll\u0131k Bak\u0131m".format(maintenance_count))
                if delivery_ready_count and delivery_ready_count < service_count:
                    service_details.append("{} Teslimata Haz\u0131r".format(delivery_ready_count))
                details_text = " ({})".format(" / ".join(service_details)) if service_details else ""
                if delivery_ready_count == service_count:
                    service_text = "{} Cihaz Teslimata Haz\u0131r".format(service_count)
                elif maintenance_count == service_count:
                    service_text = "{} Cihaz Y\u0131ll\u0131k Bak\u0131mda".format(service_count)
                else:
                    service_text = "{} Cihaz Serviste{}".format(service_count, details_text)
                if service_details and not (maintenance_count == service_count or delivery_ready_count == service_count):
                    service_text = "{} Cihaz Serviste\n({})".format(
                        service_count, " / ".join(service_details)
                    )
                if self.table.viewport().width() < 1100:
                    service_text = "{} Serviste".format(service_count)
                service_badge_frame = QFrame()
                service_badge_frame.setObjectName("CustomerServiceBadge")
                service_badge_frame.setProperty("skipThemeTransform", True)
                service_badge_frame.setStyleSheet(
                    "QFrame#CustomerServiceBadge { background: rgba(0,242,254,0.10); "
                    "color: #00f2fe; border: none; border-radius: 8px; }"
                )
                service_badge_frame.setFixedWidth(max(72, min(176, self.table.columnWidth(5) - 8)))
                badge_layout = QHBoxLayout(service_badge_frame)
                badge_layout.setContentsMargins(6, 4, 6, 4)
                badge_layout.setSpacing(3)
                service_icon = QLabel()
                service_icon.setFixedSize(12, 12)
                service_icon.setPixmap(navigation_icon("tool", 12, "#00f2fe").pixmap(12, 12))
                badge_layout.addWidget(service_icon)
                service_badge_label = QLabel(service_text)
                service_badge_label.setWordWrap(True)
                service_badge_label.setToolTip("{}".format("{} Cihaz Serviste{}".format(service_count, details_text)))
                service_badge_label.setStyleSheet(
                    "QLabel { background: transparent; color: #00f2fe; border: none; "
                    "font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 10px; }"
                )
                badge_layout.addWidget(service_badge_label)
                service_layout.addWidget(service_badge_frame)
            else:
                delivered_count = int(data.get("delivered_device_count", 0) or 0)
                service_text = "0 Aktif Cihaz"
                if delivered_count:
                    service_text = "0 Aktif (Ge\u00e7mi\u015fte {} Teslim)".format(delivered_count)
                service_badge = QLabel(service_text)
                service_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                service_badge.setWordWrap(True)
                service_badge.setStyleSheet(
                    "QLabel { background: transparent; color: #94a3b8; border: none; "
                    "font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 10px; }"
                )
                service_layout.addWidget(service_badge)
            self.table.setCellWidget(row_idx, 5, service_container)

            balance_detail_item = self._create_balance_item_multi(balances)
            balance_numeric = sum(float(value or 0.0) for value in balances.values())
            bal_item = _CustomerSortItem(balance_numeric)
            bal_item._visible_currency_count = getattr(balance_detail_item, "_visible_currency_count", 1)
            self.table.setItem(row_idx, 6, bal_item)
            balance_cell = self._create_customer_balance_widget(
                balances, overdue_days=data.get("overdue_days", 0)
            )
            self.table.setCellWidget(row_idx, 6, balance_cell)

            active_value = data.get("is_active", 1)
            is_active = str(active_value).strip().lower() not in {"0", "false", "no"}
            is_problematic = str(data.get("is_problematic", 0) or 0).strip().lower() not in {"0", "false", "no", ""}
            status_text = "Pasif" if not is_active else "\u0130ncelemede" if is_problematic else "Aktif VIP" if is_vip_segment else "Aktif"
            status_item = _CustomerSortItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(qc("warning" if status_text == "\u0130ncelemede" else "accent" if status_text == "Aktif VIP" else "success" if status_text == "Aktif" else "text_muted"))
            self.table.setItem(row_idx, 7, status_item)
            status_container = QWidget()
            status_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
            status_layout = QHBoxLayout(status_container)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_color = "#f59e0b" if status_text == "\u0130ncelemede" else "#94a3b8" if status_text == "Pasif" else "#10b981"
            status_background = (
                QColor(245, 158, 11, 38)
                if status_text == "\u0130ncelemede"
                else QColor(148, 163, 184, 26)
                if status_text == "Pasif"
                else QColor(16, 185, 129, 26)
            )
            status_badge = _CustomerStatusPill(status_background)
            status_badge.setObjectName("CustomerStatusBadge")
            status_badge.setProperty("skipThemeTransform", True)
            status_badge.setStyleSheet("background: transparent; border: none;")
            badge_layout = QHBoxLayout(status_badge)
            badge_layout.setContentsMargins(8, 2, 8, 2)
            badge_layout.setSpacing(5)
            status_dot = QLabel("\u25cf")
            status_dot.setStyleSheet("color: {}; font-size: 6px; background: transparent; border: none;".format(status_color))
            badge_layout.addWidget(status_dot)
            status_text_label = QLabel(status_text)
            status_text_label.setStyleSheet(
                "color: {}; font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 10px; font-weight: 600; background: transparent; border: none;".format(status_color)
            )
            badge_layout.addWidget(status_text_label)
            status_layout.addWidget(status_badge)
            self.table.setCellWidget(row_idx, 7, status_container)

            self.table.setCellWidget(
                row_idx, 8, self._create_action_widget(row_idx, data)
            )

            visible_currency_count = getattr(bal_item, "_visible_currency_count", 1)
            if compact_table:
                base_height = 48 if visible_currency_count <= 2 else 56
            else:
                base_height = 60 if visible_currency_count <= 2 else 72
            if len(str(data["name"])) > 20:
                base_height = max(base_height, 72 if compact_table else 78)
            self.table.setRowHeight(row_idx, base_height)
        except Exception as e:
            logger.error(f"ADD_ROW ERROR at index {row_idx}: {e}")

    def _create_customer_balance_widget(self, balances, overdue_days=0):
        default_currency = CurrencyHelper.get_code(self.db)
        primary_code = default_currency
        amount = float(balances.get(primary_code, 0.0) or 0.0)
        amount_color = "#ef4444" if amount < 0 else "#10b981" if amount > 0 else "#94a3b8"
        cell = QWidget()
        cell.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        symbol = CurrencyHelper.get_symbol(self.db, primary_code)
        amount_text = "{}{}{:,.2f}".format("-" if amount < 0 else "", symbol, abs(amount))
        if amount:
            amount_pill = QWidget()
            amount_pill.setStyleSheet(
                "background: rgba(16,185,129,0.12); border: none; border-radius: 8px;"
                if amount > 0
                else "background: rgba(239,68,68,0.12); border: none; border-radius: 8px;"
            )
            amount_row = QHBoxLayout(amount_pill)
            amount_row.setContentsMargins(7, 2, 7, 2)
            amount_row.setSpacing(5)
            amount_label = QLabel(amount_text)
            amount_label.setStyleSheet(
                "color: {}; font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 12px; font-weight: 700; border: none; background: transparent;".format(amount_color)
            )
            amount_row.addWidget(amount_label)
            balance_label = QLabel("BOR\u00c7" if amount < 0 else "ALACAK")
            balance_label.setStyleSheet(
                "color: {}; font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 8px; font-weight: 700; border: none; background: transparent;".format(amount_color)
            )
            amount_row.addWidget(balance_label)
            layout.addWidget(amount_pill, alignment=Qt.AlignmentFlag.AlignRight)
        else:
            amount_label = QLabel(amount_text)
            amount_label.setStyleSheet(
                "color: #94a3b8; font-family: 'Times New Roman', 'Segoe UI', Arial; font-size: 14px; font-weight: 600; border: none; background: transparent;"
            )
            layout.addWidget(amount_label)
        secondary_code = next(
            (
                code for code in ("USD", "EUR", "TRY")
                if code != primary_code and abs(float(balances.get(code, 0.0) or 0.0)) > 0.0001
            ),
            None,
        )
        if secondary_code:
            secondary_amount = float(balances.get(secondary_code, 0.0) or 0.0)
            secondary_text = "{}: {}{:,.2f}".format(
                secondary_code,
                CurrencyHelper.get_symbol(self.db, secondary_code),
                abs(secondary_amount),
            )
            usd_label = QLabel(secondary_text)
            usd_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            usd_label.setStyleSheet("color: #94a3b8; font-family: 'JetBrains Mono'; font-size: 9px; border: none; background: transparent;")
            layout.addWidget(usd_label)
        elif not amount:
            balance_label = QLabel("Dengeli")
            balance_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            balance_label.setStyleSheet("color: rgba(148,163,184,0.6); font-family: 'JetBrains Mono'; font-size: 9px; border: none; background: transparent;")
            layout.addWidget(balance_label)
        if amount < 0 and int(overdue_days or 0) > 0:
            overdue_label = QLabel(
                "Vadesi {} G\u00fcn Ge\u00e7ti".format(int(overdue_days))
            )
            overdue_label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            overdue_label.setStyleSheet(
                "color: #ef4444; font-family: 'JetBrains Mono', 'Segoe UI', Arial; "
                "font-size: 9px; border: none; background: transparent;"
            )
            layout.addWidget(overdue_label)
        return cell

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
        item.setFont(QFont("Times New Roman", 9, QFont.Weight.Bold))
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
        checked_rows = [
            row for row in range(self.table.rowCount())
            if self.table.item(row, 0)
            and self.table.item(row, 0).checkState() == Qt.CheckState.Checked
        ]
        if checked_rows:
            return checked_rows
        return sorted(
            set(index.row() for index in self.table.selectionModel().selectedRows())
        )
