# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QDate, QSize
from PyQt6.QtGui import QFont, QColor, QPalette
from PyQt6.QtWidgets import (
    QTableWidgetItem, QLabel, QFrame, QHBoxLayout, 
    QSizePolicy, QPushButton, QWidget
)
from src.ui.pages.dashboard_widgets.action_widget import ActionWidget
from src.utils.currency_helper import CurrencyHelper
from src.utils.status_utils import is_active_device_status, normalize_device_status
from src.utils.logger import logger
from src.utils.theme_colors import tc, theme_qss
from ._dashboard_utils import render_svg_icon

class DashboardDataMixin:
    def _get_devices_columns(self):
        cols = getattr(self, "_devices_columns_cache", None)
        if cols is not None:
            return cols
        try:
            self.db.cursor.execute("PRAGMA table_info(devices)")
            rows = self.db.cursor.fetchall() or []
            cols = {r[1] for r in rows if len(r) > 1}
        except Exception:
            cols = set()
        self._devices_columns_cache = cols
        return cols

    def update_dashboard_status_tiles(self):
        if not hasattr(self, "_status_tiles"):
            return

        counts = {
            "test": 0, "tamirde": 0, "bekliyor": 0,
            "iptal": 0, "kargo": 0, "teslim": 0,
            "parca": 0, "borclu": 0,
        }
        total = 0
        try:
            # Use a fresh cursor for dashboard reads. The shared UI cursor can
            # be left on a closed result after navigating between pages.
            conn = getattr(self.db, "conn", None)
            read_cursor = conn.cursor() if conn is not None else self.db.cursor
            read_cursor.execute("PRAGMA table_info(devices)")
            cols = {row[1] for row in (read_cursor.fetchall() or []) if len(row) > 1}
            selected = ["status"]
            for optional in ("price", "payment_status", "service_source", "delivery_type"):
                if optional in cols:
                    selected.append(optional)

            where = []
            if "is_deleted" in cols:
                where.append("COALESCE(is_deleted, 0) = 0")
            if "is_archived" in cols:
                where.append("COALESCE(is_archived, 0) = 0")

            query = "SELECT {cols} FROM devices".format(cols=", ".join(selected))
            if where:
                query += " WHERE " + " AND ".join(where)
            read_cursor.execute(query)
            rows = read_cursor.fetchall() or []
            idx = {name: pos for pos, name in enumerate(selected)}

            for row in rows:
                total += 1
                raw_status = str(row[idx["status"]] or "").strip() if row else ""
                status = normalize_device_status(raw_status)
                if status == "Bekliyor": counts["bekliyor"] += 1
                elif status == "Tamirde": counts["tamirde"] += 1
                elif status == "Par\u00e7a Bekliyor": counts["parca"] += 1
                elif status == "Test S\u00fcrecinde": counts["test"] += 1
                elif status == "Teslim Edildi": counts["teslim"] += 1
                elif status == "\u0130ptal": counts["iptal"] += 1

                price = 0.0
                if "price" in idx:
                    try:
                        price = float(row[idx["price"]] or 0)
                    except (TypeError, ValueError):
                        price = 0.0
                payment_status = str(row[idx["payment_status"]] or "").lower() if "payment_status" in idx else ""
                if price > 0 and status != "Teslim Edildi" and payment_status not in {"ödendi", "odendi", "paid"}:
                    counts["borclu"] += 1

                shipment_text = " ".join(
                    str(row[idx[col]] or "").lower()
                    for col in ("service_source", "delivery_type")
                    if col in idx
                )
                if "kargo" in shipment_text:
                    counts["kargo"] += 1
        except Exception as e:
            # Keep the last known values when a transient refresh fails.
            # A failed reconnect must not make valid cards appear as zero.
            logger.exception("Dashboard status tile update failed: %s", e)
            return

        for key, tile in self._status_tiles.items():
            count = int(counts.get(key, 0))
            if tile.get("count"):
                tile["count"].setText(str(count))
            if tile.get("pct"):
                pct = int(round((count / total) * 100)) if total else 0
                tile["pct"].setText(f"{pct}%")
            if tile.get("sub"):
                base = tile.get("base_sub", "")
                pct = int(round((count / total) * 100)) if total else 0
                tile["sub"].setText(f"{pct}% {base}")

    def populate_table(self):
        if not hasattr(self, "table"):
            return
        self.table.setRowCount(0)

        cols = self._get_devices_columns()
        wanted = [
            "tracking_no", "customer_name", "device_type", "fault_category",
            "device_brand", "device_model", "vehicle_plate", "service_source",
            "delivery_type",
            "entry_date", "exit_date", "estimated_date", "price", "labor_cost",
            "status", "urgency", "approval_status", "payment_status",
        ]
        selected = [c for c in wanted if c in cols]
        if not selected:
            if hasattr(self, "_update_recent_empty_state"):
                self._update_recent_empty_state()
            return

        sorting_was_enabled = self.table.isSortingEnabled()
        self.table.setUpdatesEnabled(False)
        self.table.setSortingEnabled(False)

        idx = {name: pos for pos, name in enumerate(selected)}
        where = []
        params = []
        if "is_archived" in cols:
            where.append("COALESCE(is_archived, 0) = 0")
        if "is_deleted" in cols:
            where.append("COALESCE(is_deleted, 0) = 0")

        category = getattr(self, "current_filter_category", "all")
        if category == "active":
            where.append("status IN ('Tamirde', 'Serviste', 'İşlemde', 'Islemde', 'Onarımda', 'Onarimda')")
        elif category == "done":
            where.append("status IN ('Teslim Edildi', 'Teslim', 'Hazır', 'Hazir', 'Bitti', 'Tamir Edildi')")
        elif category == "waiting":
            where.append("status IN ('Bekliyor', 'Beklemede', 'İşleme Alınacak', 'Isleme Alinacak')")
        elif category == "test":
            where.append("status IN ('Test Sürecinde', 'Test Surecinde', 'Test Aşaması', 'Test Asamasi', 'Onay Bekleyen', 'Onay Bekliyor')")
        elif category == "part":
            where.append("status IN ('Parça Bekliyor', 'Parca Bekliyor', 'Sipariş Geçildi', 'Siparis Gecildi')")
        elif category == "debt":
            if "price" in cols:
                where.append("CAST(COALESCE(price, 0) AS REAL) > 0")
            if "payment_status" in cols:
                where.append("LOWER(COALESCE(payment_status, '')) NOT IN ('ödendi', 'odendi', 'paid')")
        elif category == "cargo_waiting":
            cargo_filters = []
            if "delivery_type" in cols:
                cargo_filters.append(
                    "LOWER(COALESCE(delivery_type, '')) LIKE '%kargo%'"
                )
            if "service_source" in cols:
                cargo_filters.append(
                    "LOWER(COALESCE(service_source, '')) LIKE '%kargo%'"
                )
            if "status" in cols:
                cargo_filters.append(
                    "status IN ('Kargo Bekliyor', 'Kargoya Verildi')"
                )
            where.append(
                f"({' OR '.join(cargo_filters)})"
                if cargo_filters
                else "1=0"
            )
        elif category == "invoiced":
            where.append(
                """
                EXISTS (
                    SELECT 1
                    FROM accounting a
                    WHERE a.tracking_no=devices.tracking_no
                      AND COALESCE(a.is_invoiced, 0)=1
                )
                """
            )
        elif category == "uninvoiced":
            where.append(
                """
                NOT EXISTS (
                    SELECT 1
                    FROM accounting a
                    WHERE a.tracking_no=devices.tracking_no
                      AND COALESCE(a.is_invoiced, 0)=1
                )
                """
            )
        elif category == "external_out":
            external_filters = [
                "status IN ('Dis Servise Verildi', 'D\u0131\u015f Servise Verildi')"
            ]
            if "service_source" in cols:
                external_filters.append(
                    "LOWER(COALESCE(service_source, '')) LIKE '%dis servis%'"
                )
                external_filters.append(
                    "LOWER(COALESCE(service_source, '')) LIKE '%d\u0131\u015f servis%'"
                )
            where.append(f"({' OR '.join(external_filters)})")
        elif category == "external_return":
            external_return_filters = [
                "status IN ("
                "'Dis Servisten Dondu', "
                "'D\u0131\u015f Servisten D\u00f6nd\u00fc', "
                "'Onarimdan Geldi', "
                "'Onar\u0131mdan Geldi'"
                ")"
            ]
            if "service_source" in cols:
                external_return_filters.append(
                    "LOWER(COALESCE(service_source, '')) LIKE '%dondu%'"
                )
                external_return_filters.append(
                    "LOWER(COALESCE(service_source, '')) LIKE '%d\u00f6nd\u00fc%'"
                )
            where.append(f"({' OR '.join(external_return_filters)})")
        elif category == "today" and "entry_date" in cols:
            today_db = QDate.currentDate().toString("yyyy-MM-dd")
            today_tr = QDate.currentDate().toString("dd.MM.yyyy")
            where.append("(entry_date LIKE ? OR entry_date LIKE ?)")
            params.extend([f"{today_db}%", f"{today_tr}%"])
        elif category == "pending_approval":
            base = "status IN ('Onay Bekliyor', 'Onay Bekleyen', 'Parça Bekliyor', 'Parca Bekliyor', 'Test Sürecinde', 'Test Surecinde')"
            if "approval_status" in cols:
                base = f"({base} OR COALESCE(approval_status, '') IN ('Musteri Onayi Bekliyor', 'Beklemede', 'Bekleme'))"
            where.append(base)
        elif category == "delivered_today":
            where.append("status IN ('Teslim Edildi', 'Teslim')")
            if "exit_date" in cols:
                where.append("exit_date LIKE ?")
                params.append(f"{QDate.currentDate().toString('yyyy-MM-dd')}%")
        else:
            where.append(
                "COALESCE(status, '') NOT IN ("
                "'Teslim Edildi', 'Teslim', 'Hazır', 'Hazir', 'Bitti', 'Tamamlandı', 'Tamamlandi', 'Tamir Edildi', "
                "'Teslime Hazır', 'Teslime Hazir', 'Teslim Alındı', 'Teslim Alindi', 'Müşteriye Teslim', 'Musteriye Teslim', "
                "'Kapandı', 'Kapandi', 'Kapalı', 'Kapali', 'İptal', 'Iptal', 'İptal Edildi', 'Iptal Edildi', "
                "'İptal İade', 'Iptal Iade', 'İade Edildi', 'Iade Edildi'"
                ")"
            )

        query = "SELECT {cols} FROM devices".format(cols=", ".join(selected))
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY id DESC LIMIT 80"

        try:
            self.db.cursor.execute(query, params)
            services = self.db.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Dashboard table query error: {e}")
            services = []

        def value(row, name, default=""):
            if name not in idx: return default
            return row[idx[name]] if row[idx[name]] is not None else default

        # If category is "all", we show all records without throwing away non-active/delivered ones.
        # This fixes showing zero devices on the main list.
        if category in {"all", "", None}:
            pass


        status_display = {
            "Bekliyor": ("İŞLEME ALINACAK", "#DDEBFF", "#08345F"),
            "Tamirde": ("TAMİRDE", "#DDF7E9", "#065F46"),
            "Parça Bekliyor": ("PARÇA BEKLİYOR", "#DDF3FF", "#075985"),
            "Test Sürecinde": ("TEST SÜRECİNDE", "#EEE8FF", "#4C1D95"),
            "Teslim Edildi": ("TESLİM EDİLDİ", "#DDF9FF", "#155E75"),
            "İptal": ("İPTAL İADE", "#FFE2DE", "#991B1B"),
        }
        if hasattr(self, "_is_automotive") and self._is_automotive():
            status_display.update({
                "Bekliyor": ("SIRAYA ALINACAK", "#DDEBFF", "#08345F"),
                "Tamirde": ("SERVİSTE", "#DDF7E9", "#065F46"),
                "Test Sürecinde": ("KONTROLDE", "#EEE8FF", "#4C1D95"),
                "Teslim Edildi": ("ARAÇ TESLİM", "#DDF9FF", "#155E75"),
            })

        surface_color = QColor(tc("surface"))
        surface_luminance = ((0.299 * surface_color.red()) + (0.587 * surface_color.green()) + (0.114 * surface_color.blue())) if surface_color.isValid() else 255
        classic = bool(hasattr(self, "_is_classic_appearance") and self._is_classic_appearance())

        if classic:
            status_display = {
                "Bekliyor": ("ISLEME ALINACAK", "#EEF4FF", "#1F4E79"),
                "Tamirde": ("TAMIRDE", "#EAF5EA", "#2F6B2F"),
                "Parça Bekliyor": ("PARCA BEKLIYOR", "#EEF7FA", "#1F5F75"),
                "Test Sürecinde": ("TEST SURECINDE", "#F2EEFA", "#4B3F72"),
                "Teslim Edildi": ("TESLIM EDILDI", "#EAF7F3", "#1F6F5B"),
                "İptal": ("IPTAL IADE", "#FAECEA", "#8A2C24"),
            }
            if hasattr(self, "_is_automotive") and self._is_automotive():
                status_display.update({
                    "Bekliyor": ("SIRAYA ALINACAK", "#EEF4FF", "#1F4E79"),
                    "Tamirde": ("SERVISTE", "#EAF5EA", "#2F6B2F"),
                    "Test Sürecinde": ("KONTROLDE", "#F2EEFA", "#4B3F72"),
                    "Teslim Edildi": ("ARAC TESLIM", "#EAF7F3", "#1F6F5B"),
                })
        elif surface_luminance < 120 or "forest" in str(getattr(self, "current_theme", "")).lower():
            dark_specs = [("#1E3A5F", "#DBEAFE"), ("#14532D", "#DCFCE7"), ("#164E63", "#CFFAFE"), ("#312E81", "#EDE9FE"), ("#155E75", "#ECFEFF"), ("#7F1D1D", "#FEE2E2")]
            status_display = {k: (status_display.get(k, (k.upper(), "#EEF2F7", "#334155"))[0], bg, fg) for k, (bg, fg) in zip(list(status_display.keys()), dark_specs)}


        self.table.setRowCount(len(services))
        for row_idx, row in enumerate(services):
            self.table.setRowHeight(row_idx, 42 if classic else 58)
            tracking_no = str(value(row, "tracking_no"))
            customer = str(value(row, "customer_name"))
            if hasattr(self, "_is_automotive") and self._is_automotive():
                product_group = str(value(row, "vehicle_plate") or value(row, "device_type") or value(row, "fault_category") or "ARAÇ")
            else:
                product_group = str(value(row, "device_type") or value(row, "fault_category") or "SERVİS")
            brand, model = str(value(row, "device_brand")), str(value(row, "device_model"))
            entry_date = str(value(row, "entry_date"))
            delivery_date = str(value(row, "exit_date") or value(row, "estimated_date") or "TESLİM EDİLMEDİ")
            status, urgency = str(value(row, "status")), str(value(row, "urgency", "Düşük"))

            price_raw = value(row, "price") or value(row, "labor_cost")
            try:
                amount = float(price_raw or 0)
                price_text = CurrencyHelper.format_amount(amount, db=self.db) if amount else "Ücretsiz İşlem"
            except:
                price_text = str(price_raw or "Ücretsiz İşlem")

            self._set_tracking_cell(row_idx, tracking_no)
            self._set_action_cell(row_idx, tracking_no)
            for col, text in enumerate([customer, product_group, brand, model, entry_date, delivery_date], start=2):
                self._set_text_cell(row_idx, col, text)

            source_text = str(value(row, "service_source") or "")
            is_automotive = bool(
                hasattr(self, "_is_automotive") and self._is_automotive()
            )
            if is_automotive:
                delivery_date = str(value(row, "exit_date") or "Teslim Edilmedi")
                source_key = source_text.strip().casefold()
                source_text = {
                    "cle_maintenance": "Bak\u0131m / Servis",
                    "maintenance": "Bak\u0131m / Servis",
                    "service": "Servis",
                    "automotive": "\u0130\u015f Emri",
                }.get(source_key, source_text.replace("_", " ").title() or "\u0130\u015f Emri")
                self._set_text_cell(row_idx, 7, delivery_date, center=True)
                self._set_text_cell(row_idx, 8, source_text, center=True, bold=True)
                self._set_text_cell(row_idx, 9, price_text, center=True, bold=True)
                normalized = normalize_device_status(status.strip())
                status_text = {
                    "Bekliyor": "S\u0131raya Al\u0131nacak",
                    "Tamirde": "Serviste",
                    "Par\u00e7a Bekliyor": "Par\u00e7a Bekliyor",
                    "Test S\u00fcrecinde": "Kontrolde",
                    "Teslim Edildi": "Teslim Edildi",
                    "\u0130ptal": "\u0130ptal",
                }.get(normalized, normalized or "Belirsiz")
                self._set_text_cell(row_idx, 10, status_text, center=True, bold=True)
                urgency_key = urgency.strip().casefold()
                urgency_text = {
                    "high": "Y\u00fcksek",
                    "yuksek": "Y\u00fcksek",
                    "medium": "Orta",
                    "orta": "Orta",
                }.get(urgency_key, "D\u00fc\u015f\u00fck")
                self._set_text_cell(row_idx, 11, urgency_text, center=True, bold=True)
                continue
            if hasattr(self, "_is_automotive") and self._is_automotive():
                source_badge = source_text.upper() if source_text else "İŞ EMRİ"
            else:
                source_badge = source_text.upper() if source_text else "SERVİS"
            source_bg = "#1E3A5F" if surface_luminance < 120 else "#0F172A"
            if classic: source_bg = "#EEF2F7"
            self._set_badge_cell(row_idx, 8, source_badge, source_bg, "#334155" if classic else "#DBEAFE", font_size=9)
            self._set_text_cell(row_idx, 9, price_text, center=True, bold=True)

            normalized = normalize_device_status(status.strip())
            status_text, status_color, status_fg = status_display.get(normalized, ((status or "BELİRSİZ").upper(), "#EEF2F7", "#334155"))
            self._set_badge_cell(row_idx, 10, status_text, status_color, status_fg, font_size=9)

            urgency_norm = urgency.strip().lower()
            if classic:
                if "yuksek" in urgency_norm or "high" in urgency_norm: self._set_badge_cell(row_idx, 11, "YUKSEK", "#FAECEA", "#8A2C24", font_size=9)
                elif urgency_norm in {"orta", "medium"}: self._set_badge_cell(row_idx, 11, "ORTA", "#F2EEFA", "#4B3F72", font_size=9)
                else: self._set_badge_cell(row_idx, 11, "DUSUK", "#EEF2F7", "#334155", font_size=9)
                continue
            if urgency_norm in {"yüksek", "yuksek", "high"}: self._set_badge_cell(row_idx, 11, "YÜKSEK", "#E24A3B", "#FFFFFF", font_size=9)
            elif urgency_norm in {"orta", "medium"}: self._set_badge_cell(row_idx, 11, "ORTA", "#625DA8", "#FFFFFF", font_size=9)
            else:
                low_bg = "#475569" if surface_luminance < 120 else "#64748B"
                self._set_badge_cell(row_idx, 11, "DÜŞÜK", low_bg, "#F8FAFC", font_size=9)

        self.table.setSortingEnabled(sorting_was_enabled)
        self.table.setUpdatesEnabled(True)
        self.table.viewport().update()
        if hasattr(self, "_update_recent_empty_state"):
            self._update_recent_empty_state()

    def _set_text_cell(self, row, col, text, center=False, bold=False):
        item = QTableWidgetItem(str(text or ""))
        item.setToolTip(str(text or ""))
        align = Qt.AlignmentFlag.AlignVCenter
        align |= Qt.AlignmentFlag.AlignCenter if center else Qt.AlignmentFlag.AlignLeft
        item.setTextAlignment(align)
        if bold:
            item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        # Explicitly set foreground so text is visible regardless of theme/palette.
        text_color = QColor(tc("text") or "#111827")
        if text_color.isValid():
            item.setForeground(text_color)
        self.table.setItem(row, col, item)


    def _set_badge_cell(self, row, col, text, bg, fg=None, font_size=10):
        fg = fg or (self._contrast_on(bg) if hasattr(self, "_contrast_on") else "#FFFFFF")
        classic = bool(hasattr(self, "_is_classic_appearance") and self._is_classic_appearance())
        frame = QFrame()
        frame.setObjectName("DashboardBadgeFrame")
        frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if classic: frame.setProperty("skipThemeTransform", False)
        frame.setStyleSheet("QFrame#DashboardBadgeFrame { background: transparent; border: none; }")
        layout = QHBoxLayout(frame); layout.setContentsMargins(4, 4, 4, 4); layout.setSpacing(0)
        label = QLabel(str(text or ""))
        label.setObjectName("DashboardBadgeText")
        if classic: label.setProperty("skipThemeTransform", False)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(22 if classic else 26)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        st = f"background-color: {bg}; color: {fg}; font-family: 'Segoe UI'; padding: 2px 6px; font-weight: 800;"
        if classic: label.setStyleSheet(f"QLabel#DashboardBadgeText {{ {st} border: 1px solid #B8C0CC; border-radius: 0px; font-size: {max(9, font_size)}px; }}")
        else: label.setStyleSheet(f"QLabel#DashboardBadgeText {{ {st} border: none; border-radius: 4px; font-size: {font_size}px; font-weight: 900; padding: 5px 8px; }}")
        palette = label.palette()
        tc_obj = QColor(fg)
        for g in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
            palette.setColor(g, QPalette.ColorRole.WindowText, tc_obj)
            palette.setColor(g, QPalette.ColorRole.Text, tc_obj)
            palette.setColor(g, QPalette.ColorRole.ButtonText, tc_obj)
        label.setPalette(palette); layout.addWidget(label); self.table.setCellWidget(row, col, frame)

    def _make_track_action_button(self, text, bg, tooltip, callback):
        classic = bool(hasattr(self, "_is_classic_appearance") and self._is_classic_appearance())
        btn = QPushButton(text) if classic else QPushButton()
        btn.setToolTip(tooltip); btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if classic: btn.setProperty("skipThemeTransform", False)
        btn.setFixedSize(28 if classic else 30, 26 if classic else 30)
        btn.clicked.connect(callback)
        fg = "#111827" if classic else (self._contrast_on(bg) if hasattr(self, "_contrast_on") else "#ffffff")
        hv = "#E5E7EB" if classic else (self._hover_on(bg) if hasattr(self, "_hover_on") else bg)
        hf = self._contrast_on(hv) if hasattr(self, "_contrast_on") else fg
        if classic:
            btn.setStyleSheet(f"QPushButton {{ background-color: #F8FAFC; color: {fg}; border: 1px solid #AEB4BD; border-left: 3px solid {bg}; border-radius: 0px; font-size: 11px; font-weight: 800; padding: 0px; }} QPushButton:hover {{ background-color: {hv}; border-color: #2563EB; color: #111827; }} QPushButton:pressed {{ background-color: #DCEBFF; }} QToolTip {{ background-color: #FFFFFF; color: #111827; border: 1px solid #94A3B8; padding: 5px 8px; }}")
            palette = btn.palette()
            for g in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
                palette.setColor(g, QPalette.ColorRole.ButtonText, QColor(fg))
            btn.setPalette(palette)
        else:
            icon_obj = render_svg_icon(text, bg, size=15)
            btn.setIcon(icon_obj)
            btn.setIconSize(QSize(15, 15))
            btn.setStyleSheet(theme_qss(f"""
                QPushButton {{
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {bg}22;
                    border-color: {bg};
                }}
                QPushButton:pressed {{
                    background-color: {bg}44;
                }}
                QToolTip {{
                    background-color: #FFFFFF;
                    color: #111827;
                    border: 1px solid #94A3B8;
                    padding: 5px 8px;
                }}
            """))
        return btn

    def _set_tracking_cell(self, row, tracking_no):
        item = QTableWidgetItem(str(tracking_no or ""))
        item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignCenter)
        text_color = QColor(tc("text") or "#111827")
        if text_color.isValid():
            item.setForeground(text_color)
        self.table.setItem(row, 0, item)


    def _set_action_cell(self, row, tracking_no):
        cell = QWidget()
        classic = bool(hasattr(self, "_is_classic_appearance") and self._is_classic_appearance())
        if classic: cell.setProperty("skipThemeTransform", False)
        cell.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(4 if classic else 6, 4 if classic else 6, 4 if classic else 6, 4 if classic else 6)
        layout.setSpacing(2 if classic else 6)
        st = "Bakım / Servis Paneli" if hasattr(self, "_is_automotive") and self._is_automotive() else "Teknisyen Paneli"
        lt = (
            "Detayl\u0131 Fi\u015f Yazd\u0131r"
            if hasattr(self, "_is_automotive") and self._is_automotive()
            else "Barkod Yazd\u0131r"
        )
        
        if classic:
            actions = [
                ("i", "#F97316", "Detay", lambda: self.open_context_menu_action("info", tracking_no)),
                ("*", "#00A65A", st, lambda: self.open_technician_panel(tracking_no)),
                ("M", "#0F172A", "Müşteri Bilgileri", lambda: self.open_context_menu_action("customer", tracking_no)),
                ("S", "#625DA8", "SMS Gönder", lambda: self.open_context_menu_action("sms", tracking_no)),
                ("W", "#00A65A", "WhatsApp", lambda: self.open_context_menu_action("whatsapp", tracking_no)),
                ("□", "#D41462", lt, lambda: self.print_service(tracking_no)),
                ("₺", "#9B59B6", "Ödeme Al", lambda: self.open_context_menu_action("payment", tracking_no)),
            ]
        else:
            icon_info = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>"""
            icon_settings = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>"""
            icon_building = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="12" y1="22" x2="12" y2="22.01"></line><line x1="12" y1="2" x2="12" y2="22"></line><line x1="4" y1="10" x2="20" y2="10"></line><line x1="4" y1="16" x2="20" y2="16"></line></svg>"""
            icon_sms = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>"""
            icon_whatsapp = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>"""
            icon_barcode = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5v14"/><path d="M8 5v14"/><path d="M12 5v14"/><path d="M17 5v14"/><path d="M21 5v14"/></svg>"""
            icon_payment = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>"""
            
            actions = [
                (icon_info, "#F97316", "Detay", lambda: self.open_context_menu_action("info", tracking_no)),
                (icon_settings, "#00A65A", st, lambda: self.open_technician_panel(tracking_no)),
                (icon_building, "#0F172A", "Müşteri Bilgileri", lambda: self.open_context_menu_action("customer", tracking_no)),
                (icon_sms, "#625DA8", "SMS Gönder", lambda: self.open_context_menu_action("sms", tracking_no)),
                (icon_whatsapp, "#00A65A", "WhatsApp", lambda: self.open_context_menu_action("whatsapp", tracking_no)),
                (icon_barcode, "#D41462", lt, lambda: self.print_service(tracking_no)),
                (icon_payment, "#9B59B6", "Ödeme Al", lambda: self.open_context_menu_action("payment", tracking_no)),
            ]
            
        for t, c, tt, cb in actions: layout.addWidget(self._make_track_action_button(t, c, tt, cb))
        self.table.setCellWidget(row, 1, cell)
