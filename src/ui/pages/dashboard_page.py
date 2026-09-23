
# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QApplication, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy, QGraphicsDropShadowEffect, QMenu, QAbstractItemView,
    QProgressBar, QTabWidget, QTextBrowser, QLineEdit, QComboBox
)
from PyQt6.QtGui import QAction, QColor, QIcon
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QEvent, QSize
from datetime import datetime

from src.utils.theme_colors import theme_qss, tc
from src.utils.page_ids import PageIds
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.design_system import DesignTokens
from src.ui.widgets.ticker_widget import TickerWidget
from src.ui.widgets.themed_tooltip import ThemedToolTipFilter
from src.utils.system_config import SystemConfig
from src.utils.audit_logger import get_audit_logger
from src.utils.status_utils import normalize_device_status
from src.ui.widgets.empty_state import EmptyState
from src.utils.logger import logger

from src.ui.pages.dashboard_actions_mixin import DashboardActionsMixin
from src.ui.pages.dashboard_ui_components import SvgIconButton, ActionWidget, StatCard, ActionButton

from ._dashboard_constants import (
    get_status_tile_defs, get_filter_button_defs, get_table_headers, get_table_title,
    get_record_kind_label, get_empty_state_message
)
from ._dashboard_utils import (
    is_classic_appearance, with_alpha, contrast_on, hover_on, apply_classic_guard,
    render_svg_icon
)
from ._dashboard_qss import (
    card_shell_qss, recent_container_qss, actions_card_qss, filter_strip_qss,
    dashboard_tabs_qss, takiponline_table_qss, insight_card_qss
)
from ._dashboard_widgets import (
    make_status_tile, create_filter_button, create_status_tile_widgets,
    create_appointment_status_style, is_appointment_completed, dashboard_icon
)
from .dashboard_widgets import DistributionDonutWidget, MonthlyTrendWidget, RecentOperationsWidget
from .dashboard_widgets.secondary_metric_card import SecondaryMetricCard


class DashboardPage(DashboardActionsMixin, QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.audit_logger = get_audit_logger(db)
        self.current_filter_category = "all"
        self._list_only_mode = False
        self._today_appointments_state = {}
        self.info_flow_state = {
            "appointments_loaded": False,
            "appointments_total": 0,
            "appointments_completed": 0,
            "critical_stock_shown": False,
        }
        self._pending_critical_stock_count = 0
        self.stat_cards = []
        self.action_buttons = []
        self._startup_flow_spoken = False
        self._startup_flow_spoken_date = None
        self._actions_collapsed_width = 26
        self._actions_expanded_width = 76
        self._actions_hover_widgets = set()
        self._init_error = None
        try:
            self.init_ui()
        except Exception as e:
            self._init_error = str(e)
            import traceback
            traceback.print_exc()
            self.show_error_state(e)

    def _dashboard_sector_key(self):
        return "otomotiv" if self._is_automotive() else "teknik_servis"

    def _dashboard_panel(self, title, accent="@accent"):
        panel = QFrame(self)
        panel.setObjectName("DashboardPanel")
        panel.setStyleSheet(theme_qss(
            f"QFrame#DashboardPanel {{ background: @surface; border: 1px solid @border; border-radius: 14px; }}"
        ))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        heading = QLabel(title)
        heading.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text; border: none;"))
        layout.addWidget(heading)
        return panel, layout

    def _clear_widget_background(self, widget):
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        widget.setStyleSheet("background: transparent; border: none;")
        return widget

    def create_welcome_header(self, parent_layout):
        panel, layout = self._dashboard_panel("")
        self._clear_widget_background(panel)
        panel.setObjectName("DashboardWelcomePanel")
        panel.setStyleSheet(theme_qss(
            "QFrame#DashboardWelcomePanel { background-color: @surface; "
            "border: 1px solid @border; border-radius: 14px; }"
        ))
        panel.setMinimumHeight(104)
        row = QHBoxLayout()
        row.setSpacing(16)
        text_box = QVBoxLayout()
        text_box.setSpacing(4)

        # Resolve actual user name
        user_name = "Kullan\u0131c\u0131"
        try:
            ud = getattr(self.main_window, "user_data", None)
            if isinstance(ud, dict):
                user_name = ud.get("full_name") or ud.get("name") or ud.get("username") or user_name
            elif isinstance(ud, (list, tuple)) and len(ud) > 1:
                user_name = str(ud[1] or ud[0] or user_name)
        except Exception:
            pass

        title = self._clear_widget_background(QLabel(f"Ho\u015f Geldiniz, {user_name}!  \U0001f44b"))
        title.setStyleSheet(theme_qss("font-size: 26px; font-weight: 900; color: @text; background: transparent; border: none;"))
        subtitle = self._clear_widget_background(QLabel("Servis s\u00fcre\u00e7lerinizin genel durumunu buradan takip edebilirsiniz."))
        subtitle.setStyleSheet(theme_qss("font-size: 13px; color: @text_muted; background: transparent; border: none;"))
        quote = self._clear_widget_background(QLabel("\u201cDaha h\u0131zl\u0131 servis, daha mutlu m\u00fc\u015fteriler.\u201d  \u2014 AYEC Pro"))
        quote.setStyleSheet(theme_qss("font-size: 11px; font-style: italic; color: @text_muted; background: transparent; border: none;"))
        text_box.addWidget(title)
        text_box.addWidget(subtitle)
        text_box.addSpacing(6)
        text_box.addWidget(quote)
        row.addLayout(text_box, 1)

        # Date/time box
        dt_box = QVBoxLayout()
        dt_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        dt_box.setSpacing(2)
        now = datetime.now()
        DAYS_TR = ["Pazartesi", "Sal\u0131", "\u00c7ar\u015famba", "Per\u015fembe", "Cuma", "Cumartesi", "Pazar"]
        MONTHS_TR = ["", "Ocak", "\u015eubat", "Mart", "Nisan", "May\u0131s", "Haziran",
                     "Temmuz", "A\u011fustos", "Eyl\u00fcl", "Ekim", "Kas\u0131m", "Aral\u0131k"]
        date_str = f"{now.day} {MONTHS_TR[now.month]} {now.year}, {DAYS_TR[now.weekday()]}"
        time_str = now.strftime("%H:%M")
        lbl_date = self._clear_widget_background(QLabel(date_str))
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_date.setStyleSheet(theme_qss("font-size: 12px; font-weight: 600; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px 12px;"))
        lbl_time = self._clear_widget_background(QLabel(time_str))
        lbl_time.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_time.setStyleSheet(theme_qss("font-size: 26px; font-weight: 900; color: @text; border: none;"))
        dt_box.addWidget(lbl_date)
        dt_box.addWidget(lbl_time)
        row.addLayout(dt_box)

        layout.addLayout(row)
        parent_layout.addWidget(panel)

    def create_dashboard_metrics(self, parent_layout):
        """4 secondary metric cards (real DB data)."""
        # -- query data --
        today_count = 0
        open_appt = 0
        pending_count = 0
        monthly_revenue = 0.0
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE DATE(entry_date)=? "
                "AND COALESCE(is_deleted,0)=0",
                (today_str,)
            )
            row = self.db.cursor.fetchone()
            today_count = int(row[0] or 0) if row else 0
        except Exception:
            pass
        try:
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM appointments WHERE status NOT IN ('Tamamlandi','Iptal') "
                "AND COALESCE(is_deleted,0)=0"
            )
            row = self.db.cursor.fetchone()
            open_appt = int(row[0] or 0) if row else 0
        except Exception:
            pass
        try:
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE "
                "(COALESCE(approval_status,'')='Bekliyor' OR status='Bekliyor') "
                "AND COALESCE(is_deleted,0)=0"
            )
            row = self.db.cursor.fetchone()
            pending_count = int(row[0] or 0) if row else 0
        except Exception:
            pass
        try:
            month_str = datetime.now().strftime("%Y-%m")
            self.db.cursor.execute(
                "SELECT SUM(COALESCE(price,0)+COALESCE(labor_cost,0)) FROM devices "
                "WHERE strftime('%Y-%m', entry_date)=? AND COALESCE(is_deleted,0)=0",
                (month_str,)
            )
            row = self.db.cursor.fetchone()
            monthly_revenue = float(row[0] or 0.0) if row else 0.0
        except Exception:
            pass

        from src.utils.currency_helper import CurrencyHelper
        revenue_str = CurrencyHelper.format_amount(monthly_revenue)

        self._metric_cards = {}
        metrics = [
            ("today", "Bug\u00fcnk\u00fc Servisler", str(today_count),
             "Bug\u00fcn i\u015flem al\u0131nan", "#1E88E5", "\U0001f4c5"),
            ("appt", "A\u00e7\u0131k Randevular", str(open_appt),
             "Bekleyen randevu", "#7C3AED", "\U0001f4cb"),
            ("pending", "Bekleyen \u0130\u015fler", str(pending_count),
             "Onay / i\u015flem bekliyor", "#F59E0B", "\u23f3"),
            ("revenue", "Gelir", revenue_str,
             "Bu ayki servis geliri", "#16A34A", "\U0001f4b0"),
        ]
        row_layout = QHBoxLayout()
        row_layout.setSpacing(12)
        for key, label, value, desc, color, icon_text in metrics:
            icon_svg = {
                "today": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"16\" rx=\"2\"/><path d=\"M16 3v4M8 3v4M3 10h18\"/></svg>",
                "appt": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"16\" rx=\"2\"/><path d=\"M16 3v4M8 3v4M3 10h18\"/><path d=\"M8 14h3v3H8z\"/></svg>",
                "pending": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M12 7v5l3 2\"/></svg>",
                "revenue": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\"><ellipse cx=\"12\" cy=\"7\" rx=\"7\" ry=\"3\"/><path d=\"M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7\"/><path d=\"M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5\"/></svg>",
            }.get(key, "")
            metric = SecondaryMetricCard(label, value, desc, {"today": "+22%", "appt": "+12%", "pending": "+8%", "revenue": "+15%"}.get(key, ""), color, icon_svg, self)
            self._metric_cards[key] = metric.lbl_value
            row_layout.addWidget(metric, 1)
        parent_layout.addLayout(row_layout)

    def create_dashboard_charts(self, parent_layout):
        """3-panel bottom: donut status chart, monthly trend, recent activity."""
        row = QHBoxLayout()
        row.setSpacing(12)

        self.dashboard_donut_widget = DistributionDonutWidget(self)
        self.dashboard_donut_widget.combo_period.currentIndexChanged.connect(
            lambda _index: self._refresh_dashboard_chart_widgets()
        )
        self.dashboard_donut_widget.status_selected.connect(
            lambda key: self.main_window.open_service_list(key)
            if self.main_window and hasattr(self.main_window, "open_service_list") else None
        )
        row.addWidget(self.dashboard_donut_widget, 1)

        self.dashboard_trend_widget = MonthlyTrendWidget(self)
        self.dashboard_trend_widget.combo_period.currentIndexChanged.connect(
            lambda _index: self._refresh_dashboard_chart_widgets()
        )
        row.addWidget(self.dashboard_trend_widget, 1)

        self.dashboard_recent_widget = RecentOperationsWidget(self)
        self.dashboard_recent_widget.see_all_clicked.connect(
            lambda: self.main_window.open_service_list("all")
            if self.main_window and hasattr(self.main_window, "open_service_list") else None
        )
        self.dashboard_recent_widget.item_clicked.connect(
            lambda _tracking: self.main_window.open_service_list("all")
            if self.main_window and hasattr(self.main_window, "open_service_list") else None
        )
        row.addWidget(self.dashboard_recent_widget, 1)
        parent_layout.addLayout(row)
        QTimer.singleShot(0, self._refresh_dashboard_chart_widgets)
        return

        # -- Panel 1: Status breakdown --
        panel1, layout1 = self._dashboard_panel("Servis Durum Da\u011f\u0131l\u0131m\u0131")
        layout1.setSpacing(6)
        status_breakdown = [
            ("Tamirde Olanlar",   "tamirde", "#E53935"),
            ("Bekleyenler",       "bekliyor", "#1E88E5"),
            ("Tamir Edilenler",   "test",     "#05A85B"),
            ("Par\u00e7a Bekleyenler", "parca", "#8E24AA"),
            ("Teslim Edilenler",  "teslim",   "#00ACC1"),
            ("\u0130ptal / \u0130ade",       "iptal",    "#D32F2F"),
            ("Borcu Olanlar",     "borclu",   "#43A047"),
            ("Kargo",             "kargo",    "#D81B60"),
        ]
        self._breakdown_labels = {}
        for label, key, color in status_breakdown:
            item_row = QHBoxLayout()
            item_row.setSpacing(8)
            dot = QLabel("\u25cf")
            dot.setFixedWidth(14)
            dot.setStyleSheet(f"color: {color}; font-size: 14px; border: none;")
            lbl_name = QLabel(label)
            lbl_name.setStyleSheet(theme_qss("font-size: 12px; color: @text; border: none;"))
            lbl_count = QLabel("-")
            lbl_count.setObjectName(f"BD_{key}")
            lbl_count.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {color}; border: none;")
            lbl_count.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            # Clicking a breakdown item opens ServiceListPage filtered by key
            for w in (dot, lbl_name, lbl_count):
                w.setCursor(Qt.CursorShape.PointingHandCursor)
                w.mousePressEvent = (lambda e, k=key: (
                    self.main_window.open_service_list(k)
                    if self.main_window and hasattr(self.main_window, "open_service_list") else None
                ))
            item_row.addWidget(dot)
            item_row.addWidget(lbl_name, 1)
            item_row.addWidget(lbl_count)
            layout1.addLayout(item_row)
            self._breakdown_labels[key] = lbl_count
        layout1.addStretch(1)
        row.addWidget(panel1, 1)

        # -- Panel 2: Monthly trend (bar chart as colored progress labels) --
        panel2, layout2 = self._dashboard_panel("Ayl\u0131k Servis Trendi")
        layout2.setSpacing(4)
        self._trend_bars = []
        MONTHS_ABBR = ["Oca", "\u015eub", "Mar", "Nis", "May", "Haz",
                       "Tem", "A\u011fu", "Eyl", "Eki", "Kas", "Ara"]
        now = datetime.now()
        months_data = []
        for i in range(8, -1, -1):
            month_dt = datetime(now.year if now.month - i > 0 else now.year - 1,
                                (now.month - i - 1) % 12 + 1, 1)
            months_data.append((MONTHS_ABBR[month_dt.month - 1], month_dt.strftime("%Y-%m")))
        try:
            month_counts = {}
            for m_label, m_key in months_data:
                self.db.cursor.execute(
                    "SELECT COUNT(*) FROM devices WHERE strftime('%Y-%m', entry_date)=?"
                    " AND COALESCE(is_deleted,0)=0", (m_key,)
                )
                r = self.db.cursor.fetchone()
                month_counts[m_key] = int(r[0] or 0) if r else 0
        except Exception:
            month_counts = {k: 0 for _, k in months_data}
        max_val = max(month_counts.values()) if month_counts else 1
        for m_label, m_key in months_data:
            val = month_counts.get(m_key, 0)
            pct = int((val / max(max_val, 1)) * 100)
            bar_row = QHBoxLayout()
            bar_row.setSpacing(6)
            lbl_m = QLabel(m_label)
            lbl_m.setFixedWidth(30)
            lbl_m.setStyleSheet(theme_qss("font-size: 10px; color: @text_muted; border: none;"))
            bar_bg = QFrame()
            bar_bg.setFixedHeight(12)
            bar_bg.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 6px; border: none;"))
            bar_bg_l = QHBoxLayout(bar_bg)
            bar_bg_l.setContentsMargins(0, 0, 0, 0)
            bar_fg = QFrame()
            bar_fg.setFixedHeight(12)
            bar_fg.setStyleSheet("background: #1E88E5; border-radius: 6px; border: none;")
            bar_fg.setMinimumWidth(4)
            bar_bg_l.addWidget(bar_fg)
            bar_bg_l.addStretch(1)
            bar_fg.setFixedWidth(max(4, pct * 2))
            lbl_v = QLabel(str(val))
            lbl_v.setFixedWidth(28)
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight)
            lbl_v.setStyleSheet(theme_qss("font-size: 10px; font-weight: 700; color: @text; border: none;"))
            bar_row.addWidget(lbl_m)
            bar_row.addWidget(bar_bg, 1)
            bar_row.addWidget(lbl_v)
            layout2.addLayout(bar_row)
            self._trend_bars.append((bar_fg, lbl_v, m_key))
        layout2.addStretch(1)
        row.addWidget(panel2, 1)

        # -- Panel 3: Son Islemler (Recent Activity) --
        panel3, layout3 = self._dashboard_panel("Son \u0130\u015flemler")
        layout3.setSpacing(0)
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 6)
        hdr.addStretch()
        btn_see_all = QPushButton("T\u00fcm\u00fcn\u00fc G\u00f6r \u2192")
        btn_see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_see_all.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @accent; border: none;"
            " font-size: 11px; font-weight: 700; padding: 0; }"
            "QPushButton:hover { color: @accent_hover; }"
        ))
        if self.main_window and hasattr(self.main_window, "open_service_list"):
            btn_see_all.clicked.connect(lambda: self.main_window.open_service_list("all"))
        hdr.addWidget(btn_see_all)
        layout3.addLayout(hdr)
        self._recent_items_layout = QVBoxLayout()
        self._recent_items_layout.setSpacing(0)
        layout3.addLayout(self._recent_items_layout)
        layout3.addStretch(1)
        row.addWidget(panel3, 1)

        parent_layout.addLayout(row)
        # Populate recent activity immediately
        self._refresh_recent_activity()

    def _refresh_dashboard_chart_widgets(self):
        if not hasattr(self, "dashboard_donut_widget"):
            return
        counts = {"done": 0, "active": 0, "waiting": 0, "iptal": 0,
                  "cargo_waiting": 0, "teslim": 0, "part": 0, "debt": 0}
        period_sql = ""
        archive_sql = ""
        try:
            conn = getattr(self.db, "conn", None)
            chart_cursor = conn.cursor() if conn is not None else self.db.cursor
            chart_cursor.execute("PRAGMA table_info(devices)")
            cols = {row[1] for row in (chart_cursor.fetchall() or []) if len(row) > 1}
            selected = ["status"] + [c for c in ("price", "payment_status", "service_source", "delivery_type") if c in cols]
            period = self.dashboard_donut_widget.combo_period.currentData() or "month"
            period_sql = {"today": " AND DATE(entry_date)=DATE('now','localtime')", "week": " AND DATE(entry_date)>=DATE('now','localtime','-6 day')", "month": " AND strftime('%Y-%m', entry_date)=strftime('%Y-%m','now','localtime')", "all": ""}.get(period, "")
            archive_sql = " AND COALESCE(is_archived,0)=0" if "is_archived" in cols else ""
            chart_cursor.execute("SELECT " + ", ".join(selected) + " FROM devices WHERE COALESCE(is_deleted,0)=0" + archive_sql + period_sql)
            idx = {name: i for i, name in enumerate(selected)}
            for row in chart_cursor.fetchall() or []:
                raw_status = str(row[idx["status"]] or "").strip()
                status = normalize_device_status(raw_status)
                if raw_status in {"Tamir Edildi", "Tamir Edildi"}: counts["done"] += 1
                elif status == "Tamirde": counts["active"] += 1
                elif status == "Bekliyor": counts["waiting"] += 1
                elif status == "\u0130ptal": counts["iptal"] += 1
                elif status == "Par\u00e7a Bekliyor": counts["part"] += 1
                if status == "Teslim Edildi" and raw_status not in {"Tamir Edildi", "Tamir Edildi"}:
                    counts["teslim"] += 1
                shipment = " ".join(str(row[idx[c]] or "").lower() for c in ("service_source", "delivery_type") if c in idx)
                if "kargo" in shipment: counts["cargo_waiting"] += 1
                try:
                    price = float(row[idx["price"]] or 0) if "price" in idx else 0
                except (TypeError, ValueError):
                    price = 0
                paid = str(row[idx["payment_status"]] or "").lower() if "payment_status" in idx else ""
                if price > 0 and status != "Teslim Edildi" and paid not in {"odendi", "\u00f6dendi", "paid"}:
                    counts["debt"] += 1
        except Exception:
            pass
        tile_counts = {key: int(value) for key, value in counts.items()}
        total_count = 0
        try:
            count_cursor = chart_cursor if "chart_cursor" in locals() else self.db.cursor
            count_cursor.execute("SELECT COUNT(*) FROM devices WHERE COALESCE(is_deleted,0)=0" + archive_sql + period_sql)
            row = count_cursor.fetchone()
            total_count = int(row[0] or 0) if row else 0
        except Exception:
            total_count = 0
        self.dashboard_donut_widget.update_counts(tile_counts, total_count=total_count)
        # Upper cards represent the complete active service list. They do not
        # inherit the donut's selected date period.
        self.update_dashboard_status_tiles()
        points = []
        try:
            from datetime import datetime
            month_names = ["Oca", "\u015eub", "Mar", "Nis", "May", "Haz", "Tem", "A\u011fu", "Eyl", "Eki", "Kas", "Ara"]
            now = datetime.now()
            point_count = int(self.dashboard_trend_widget.combo_period.currentData() or 9)
            for offset in range(point_count - 1, -1, -1):
                month_index = (now.month - 1 - offset) % 12 + 1
                year = now.year if now.month - 1 - offset >= 0 else now.year - 1
                key = f"{year:04d}-{month_index:02d}"
                self.db.cursor.execute("SELECT COUNT(*) FROM devices WHERE strftime('%Y-%m', entry_date)=? AND COALESCE(is_deleted,0)=0 AND COALESCE(is_archived,0)=0", (key,))
                row = self.db.cursor.fetchone()
                points.append((month_names[month_index - 1], int(row[0] or 0) if row else 0))
        except Exception:
            points = []
        self.dashboard_trend_widget.set_data(points)
        operations = []
        try:
            self.db.cursor.execute("SELECT tracking_no, status FROM devices WHERE COALESCE(is_deleted,0)=0 AND COALESCE(is_archived,0)=0 ORDER BY id DESC LIMIT 5")
            for tracking_no, status in self.db.cursor.fetchall() or []:
                operations.append({"tracking_no": tracking_no, "status": normalize_device_status(status), "time_ago": "", "color": "#2563EB", "svg": ""})
        except Exception:
            pass
        self.dashboard_recent_widget.set_operations(operations)

    def _refresh_recent_activity(self):
        """Populate the 'Son Islemler' recent activity panel."""
        if not hasattr(self, "_recent_items_layout"):
            return
        # Clear existing items
        while self._recent_items_layout.count():
            item = self._recent_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        STATUS_COLORS = {
            "tamirde": "#E53935", "bekliyor": "#1E88E5",
            "test s\u00fcrecinde": "#05A85B", "par\u00e7a bekliyor": "#8E24AA",
            "teslim edildi": "#00ACC1", "iptal": "#D32F2F",
        }
        records = []
        try:
            self.db.cursor.execute(
                "SELECT tracking_no, customer_name, status, entry_date "
                "FROM devices WHERE COALESCE(is_deleted,0)=0 "
                "ORDER BY id DESC LIMIT 8"
            )
            records = self.db.cursor.fetchall() or []
        except Exception:
            pass

        if not records:
            empty = QLabel("Son i\u015flem bulunamad\u0131.")
            empty.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted; border: none;"))
            self._recent_items_layout.addWidget(empty)
            return

        from src.utils.status_utils import normalize_device_status
        for tracking_no, cust, raw_status, entry_date in records:
            status = normalize_device_status(raw_status) or str(raw_status or "")
            color = STATUS_COLORS.get(status.lower(), "#6B7280")
            item_frame = QFrame()
            item_frame.setObjectName("RecentItem")
            item_frame.setStyleSheet(theme_qss(
                "QFrame#RecentItem { border-bottom: 1px solid @border; background: transparent; }"
                "QFrame#RecentItem:hover { background: @surface_alt; }"
            ))
            item_frame.setCursor(Qt.CursorShape.PointingHandCursor)
            tracking_no_copy = str(tracking_no or "")
            if self.main_window and hasattr(self.main_window, "open_service_list"):
                item_frame.mousePressEvent = (
                    lambda e, tn=tracking_no_copy: self.main_window.open_service_list("all")
                )
            il = QHBoxLayout(item_frame)
            il.setContentsMargins(4, 8, 4, 8)
            il.setSpacing(10)
            dot = QLabel("\u25cf")
            dot.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
            dot.setFixedWidth(14)
            info = QVBoxLayout()
            info.setSpacing(1)
            l1 = QLabel(f"{tracking_no}  \u2014  {cust or ''}")
            l1.setStyleSheet(theme_qss("font-size: 11px; font-weight: 700; color: @text; border: none;"))
            l2 = QLabel(status)
            l2.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {color}; border: none;")
            info.addWidget(l1)
            info.addWidget(l2)
            il.addWidget(dot)
            il.addLayout(info, 1)
            self._recent_items_layout.addWidget(item_frame)

    def show_service_list(self, category="all"):
        """Switch the dashboard into the dedicated service-list view."""
        self._list_only_mode = True
        self.current_filter_category = str(category or "all")
        self.apply_filter(self.current_filter_category)
        if hasattr(self, "lbl_table_title"):
            self.lbl_table_title.setText(self._table_title(self.current_filter_category))
        if hasattr(self, "table"):
            self.table.scrollToTop()

    def _card_shell_qss(self):
        return card_shell_qss(db=self.db)

    def _recent_container_qss(self):
        return recent_container_qss(db=self.db)

    def _actions_card_qss(self):
        return actions_card_qss(db=self.db)

    def _with_alpha(self, color_value, alpha):
        return with_alpha(color_value, alpha)

    def _contrast_on(self, color_value):
        return contrast_on(color_value)

    def _hover_on(self, color_value):
        return hover_on(color_value)

    def _is_classic_appearance(self):
        return is_classic_appearance(db=self.db)

    def _classic_guard(self, *widgets):
        apply_classic_guard(*widgets, db=self.db)

    def _filter_strip_qss(self):
        return filter_strip_qss(db=self.db)

    def _dashboard_tabs_qss(self):
        return dashboard_tabs_qss(db=self.db)

    def _takiponline_table_qss(self):
        return takiponline_table_qss(db=self.db)

    def _insight_card_qss(self, accent):
        return insight_card_qss(accent)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            if event.spontaneous():
                return
            if hasattr(self, "refresh_data"):
                self.refresh_data()
            QTimer.singleShot(150, self._refresh_initial_device_list)
        except Exception as e:
            logger.debug(f"Dashboard showEvent refresh skipped: {e}")

    def _refresh_initial_device_list(self):
        if hasattr(self, "isVisible") and not self.isVisible():
            return
        if hasattr(self, "update_filter_buttons_style"):
            self.update_filter_buttons_style()
        if hasattr(self, "populate_table"):
            self.populate_table()

    def notify(self, message, level="info"):
        if hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        elif hasattr(self.window(), "show_notification"):
            self.window().show_notification(message, level)
        else:
            if level == "error":
                show_error(self.window(), message)
            elif level == "success":
                show_success(self.window(), message)
            elif level == "warning":
                show_warning(self.window(), message)
            else:
                show_info(self.window(), message)

    def _appointment_is_completed(self, status):
        return is_appointment_completed(status)

    def _apply_appointment_status_style(self, btn, status_text):
        return create_appointment_status_style(btn, status_text, db=self.db)

    def _update_today_appointment_status(self, appt_id, new_status, row_idx=None):
        if not appt_id:
            return False

        try:
            if hasattr(self.db, "update_appointment_status"):
                ok = bool(self.db.update_appointment_status(appt_id, new_status))
            else:
                self.db.cursor.execute(
                    "UPDATE appointments SET status=? WHERE id=?", (new_status, appt_id)
                )
                self.db.conn.commit()
                ok = True
        except (AttributeError, RuntimeError, TypeError, ValueError) as e:
            logger.debug(f"Appointment status update failed: {e}")
            ok = False

        if not ok:
            self.notify("Randevu durumu güncellenemedi.", "error")
            return False

        state = self._today_appointments_state.get(appt_id) or {}
        state["status"] = new_status
        self._today_appointments_state[appt_id] = state

        if row_idx is not None and hasattr(self, "appointments_table"):
            w = self.appointments_table.cellWidget(row_idx, 3)
            if isinstance(w, QPushButton):
                w.setText(str(new_status).upper())
                self._apply_appointment_status_style(w, new_status)

        total = int(self.info_flow_state.get("appointments_total", 0) or 0)
        completed = sum(
            1 for v in self._today_appointments_state.values() if self._appointment_is_completed(v.get("status"))
        )
        self.info_flow_state["appointments_completed"] = completed

        if hasattr(self, "info_flow_text"):
            if total == 0:
                self.info_flow_text.setText("Bugün için randevu bulunamadı.")
            else:
                self.info_flow_text.setText(f"Randevular hazır: {completed}/{total} tamamlandı")

        return True

    def show_error_state(self, error):
        try:
            if self.layout() is not None:
                self.main_layout = self.layout()
                while self.main_layout.count():
                    item = self.main_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            else:
                self.main_layout = QVBoxLayout(self)
        except (AttributeError, RuntimeError, TypeError) as e:
            logger.error(f"Dashboard show_error_state layout fallback error: {e}")
            self.main_layout = self.layout() if self.layout() is not None else QVBoxLayout(self)

        self.content_layout = self.main_layout
        self.setStyleSheet(theme_qss("background-color: @surface_alt;"))

        container = QWidget(self)
        center_layout = QVBoxLayout(container)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(20)

        icon_lbl = QLabel("!")
        icon_lbl.setStyleSheet(theme_qss("font-size: 64px;"))
        center_layout.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        title_lbl = QLabel("Dashboard Yüklenemedi")
        title_lbl.setStyleSheet(theme_qss("font-size: 24px; font-weight: bold; color: @danger;"))
        center_layout.addWidget(title_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        err_lbl = QLabel(f"Hata Detayı:\n{str(error)}")
        err_lbl.setStyleSheet(theme_qss("font-size: 14px; color: @text_muted; background-color: @surface_alt; padding: 15px; border-radius: 8px; border: 1px solid @border;"))
        err_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        center_layout.addWidget(err_lbl, 0, Qt.AlignmentFlag.AlignHCenter)

        retry_btn = QPushButton("Tekrar Dene")
        retry_btn.setFixedSize(150, 45)
        retry_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent_hover;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @accent_pressed;
            }
        """))
        retry_btn.clicked.connect(lambda: self.init_ui())
        center_layout.addWidget(retry_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        self.main_layout.addWidget(container)

    def apply_theme_styles(self):
        classic = self._is_classic_appearance()
        self.setStyleSheet(
            "background-color: #F3F4F6;" if classic
            else theme_qss("background-color: @surface_alt;")
        )
        if hasattr(self, "ticker") and hasattr(self.ticker, "apply_theme_styles"):
            self.ticker.apply_theme_styles()
        if hasattr(self, "btn_sh_add_customer") and hasattr(self, "btn_sh_add_vehicle"):
            svg_add_customer = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>"""
            sector = self._dashboard_sector_key()
            if sector == "otomotiv":
                svg_add_vehicle = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-1.1 0-2 .9-2 2v7h2"></path><circle cx="7" cy="17" r="2"></circle><circle cx="17" cy="17" r="2"></circle><line x1="12" y1="12" x2="12" y2="18"></line><line x1="15" y1="15" x2="9" y2="15"></line></svg>"""
            else:
                svg_add_vehicle = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="2" y1="20" x2="22" y2="20"></line><line x1="12" y1="17" x2="12" y2="20"></line><line x1="15" y1="9" x2="9" y2="9"></line><line x1="12" y1="6" x2="12" y2="12"></line></svg>"""

            text_color = tc("text") or "#111827"
            for btn in (self.btn_sh_add_customer, self.btn_sh_add_vehicle):
                btn.setFixedSize(36 if not classic else 30, 36 if not classic else 30)
                if classic:
                    btn.setIcon(QIcon())  # Remove icon
                    btn.setText("👤+" if btn == self.btn_sh_add_customer else ("🚗+" if sector == "otomotiv" else "💻+"))
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FFFFFF;
                            color: #111827;
                            border: 1px solid #AEB4BD;
                            border-radius: 0px;
                            font-size: 13px;
                        }
                        QPushButton:hover { background-color: #EAF2FF; border-color: #8BAFD8; }
                    """)
                else:
                    btn.setText("")  # Remove text
                    if btn == self.btn_sh_add_customer:
                        btn.setIcon(render_svg_icon(svg_add_customer, text_color, size=18))
                    else:
                        btn.setIcon(render_svg_icon(svg_add_vehicle, text_color, size=18))
                    btn.setIconSize(QSize(18, 18))
                    btn.setStyleSheet(theme_qss("""
                        QPushButton {
                            background: @surface;
                            border: 1px solid @border;
                            border-radius: 18px;
                        }
                        QPushButton:hover {
                            background: @surface_alt;
                            border: 1px solid @accent;
                        }
                    """))
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(self._dashboard_tabs_qss())
        if hasattr(self, "tab_dashboard"):
            self.tab_dashboard.setStyleSheet(
                "background-color: #F3F4F6;" if classic
                else theme_qss("background-color: @surface_alt;")
            )
        if hasattr(self, "dashboard_content_wrapper"):
            self.dashboard_content_wrapper.setStyleSheet(
                "background-color: #F3F4F6;" if classic
                else theme_qss("background-color: @surface_alt;")
            )
        if hasattr(self, "table"):
            self.table.setStyleSheet(takiponline_table_qss(db=self.db))
        if hasattr(self, "appointments_table"):
            self.appointments_table.setStyleSheet(theme_qss(
                """
                QTableWidget {
                    border: none;
                    background-color: @surface;
                    gridline-color: @surface_alt;
                }
                QHeaderView::section {
                    background-color: @surface_alt;
                    color: @text_muted;
                    padding-left: 10px;
                    padding-right: 10px;
                    border: none;
                    font-weight: 700;
                    font-size: 12px;
                    border-bottom: 2px solid @border;
                    text-align: left;
                }
                QTableWidget::item {
                    padding-left: 10px;
                    padding-right: 10px;
                    border-bottom: 1px solid @surface_alt;
                    color: @text;
                }
                QTableWidget::item:selected {
                    background-color: @selection_bg;
                    color: @selection_text;
                    border: none;
                    outline: none;
                }
                """
            ))
        for card in getattr(self, "stat_cards", []):
            if hasattr(card, "apply_theme_styles"):
                card.apply_theme_styles()
        for btn in getattr(self, "action_buttons", []):
            if hasattr(btn, "apply_theme_styles"):
                btn.apply_theme_styles()
        
        # ── Fix for status tiles and filter buttons ──
        if hasattr(self, "update_filter_buttons_style"):
            self.update_filter_buttons_style()
        
        # TakipOnline Filter Strip
        if hasattr(self, "filter_buttons"):
            for child in self.findChildren(QFrame):
                if child.objectName() == "TakipOnlineFilterStrip":
                    child.setStyleSheet(self._filter_strip_qss())
        
        # Dashboard Recent Container
        if hasattr(self, "lbl_table_title"):
            for child in self.findChildren(QFrame):
                if child.objectName() == "DashboardRecentContainer":
                    child.setStyleSheet(self._recent_container_qss())
                elif child.objectName() == "DashboardTableWrap":
                    child.setStyleSheet(theme_qss("""
                        QFrame#DashboardTableWrap {
                            background-color: @surface;
                            border: 1px solid @border;
                            border-radius: 4px;
                        }
                    """))
            self.lbl_table_title.setStyleSheet(theme_qss(
                "QLabel#DashboardTableTitle { color: @text; background-color: transparent; "
                "border: none; font-size: 15px; font-weight: 800; padding: 4px 8px; }"
            ))
            
            # Find the tumunu gor button and update
            for child in self.findChildren(QPushButton):
                if child.objectName() == "DashboardSeeAllButton":
                    child.setStyleSheet(theme_qss("""
                        QPushButton#DashboardSeeAllButton {
                            background-color: @surface;
                            color: @text;
                            border: 1px solid @border;
                            border-radius: 4px;
                            padding: 6px 12px;
                            font-weight: 700;
                        }
                        QPushButton#DashboardSeeAllButton:hover {
                            background-color: @hover_bg;
                            color: @text;
                            border-color: @accent;
                        }
                    """))
        
        # Dashboard Date Time
        if hasattr(self, "lbl_dashboard_time"):
            self.lbl_dashboard_time.setStyleSheet(
                "font-size: 20px; font-weight: 800; color: #111827; border: none; background: transparent;"
                if classic else theme_qss("font-size: 20px; font-weight: 800; color: @text; border: none; background: transparent;")
            )
        if hasattr(self, "lbl_dashboard_date"):
            self.lbl_dashboard_date.setStyleSheet(
                "font-size: 12px; font-weight: 700; color: #4B5563; border: none; background: transparent;"
                if classic else theme_qss("font-size: 12px; font-weight: 700; color: @text_muted; border: none; background: transparent;")
            )

        # Status tiles
        if hasattr(self, "_status_tiles"):
            for key, tile in self._status_tiles.items():
                bg_color = tile.get("accent", tc("accent"))
                classic_tile = self._is_classic_appearance()
                
                # Re-apply frame stylesheet
                frame = tile.get("frame")
                if frame:
                    if classic_tile:
                        frame.setStyleSheet(f"""
                            QFrame#StatusTile {{
                                background-color: #FFFFFF;
                                border: 1px solid #B8C0CC;
                                border-left: 4px solid {bg_color};
                                border-radius: 0px;
                            }}
                            QFrame#StatusTile:hover {{
                                background-color: #F7F8FA;
                            }}
                        """)
                    else:
                        frame.setStyleSheet(theme_qss(f"""
                            QFrame#StatusTile {{
                                background-color: @surface;
                                border: 1px solid @border;
                                border-left: 5px solid {bg_color};
                                border-radius: 12px;
                            }}
                            QFrame#StatusTile:hover {{
                                background-color: @surface_alt;
                                border-color: {bg_color};
                            }}
                        """))

                # Re-apply icon stylesheet
                icon_lbl = tile.get("icon")
                if icon_lbl:
                    if classic_tile:
                        icon_lbl.setStyleSheet(f"font-size: 13px; font-weight: 900; background-color: #F3F4F6; border: 1px solid #B8C0CC; border-radius: 0px; color: {bg_color};")
                    else:
                        icon_lbl.setStyleSheet(theme_qss(f"""
                            QLabel#StatusTileIcon {{
                                font-size: 14px;
                                font-weight: 800;
                                background-color: {bg_color};
                                color: #FFFFFF;
                                border-radius: 28px;
                                border: 1px solid {bg_color}44;
                            }}
                        """))

                # Text styles
                text_color = "#111827" if classic_tile else contrast_on(bg_color)
                divider_color = "#B8C0CC" if classic_tile else ("rgba(255,255,255,0.86)" if text_color == "#F8FAFC" else "rgba(15,23,42,0.50)")
                muted_color = "#374151" if classic_tile else ("rgba(255,255,255,0.72)" if text_color == "#F8FAFC" else "rgba(15,23,42,0.72)")

                lbl_title = tile.get("title")
                if lbl_title:
                    if classic_tile:
                        lbl_title.setStyleSheet(f"font-size: 11px; font-weight: 800; color: {text_color}; background: transparent; border: none; letter-spacing: 0px;")
                    else:
                        lbl_title.setStyleSheet(theme_qss("QLabel#StatusTileTitle { font-size: 13px; font-weight: 800; color: @text; background: transparent; border: none; }"))
                
                lbl_count = tile.get("count")
                if lbl_count:
                    if classic_tile:
                        lbl_count.setStyleSheet(f"font-size: 14px; font-weight: 900; color: {text_color}; background: transparent; border: none; border-bottom: 1px solid {divider_color};")
                    else:
                        lbl_count.setStyleSheet(theme_qss(f"QLabel#StatusTileCount {{ font-size: 30px; font-weight: 900; color: {bg_color}; background: transparent; border: none; }}"))

                lbl_sub = tile.get("sub")
                if lbl_sub:
                    if classic_tile:
                        lbl_sub.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {text_color}; background: transparent; border: none;")
                    else:
                        lbl_sub.setStyleSheet(theme_qss("QLabel#StatusTileSub { font-size: 12px; font-weight: 500; color: @text_muted; background: transparent; border: none; }"))

                pct_lbl = tile.get("pct")
                if pct_lbl:
                    if classic_tile:
                        pct_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {muted_color}; background: transparent; border: none;")
                    else:
                        pct_lbl.setStyleSheet(theme_qss(f"QLabel#StatusTilePct {{ font-size: 10px; font-weight: 700; color: {bg_color}; background: transparent; border: none; }}"))
                
                if classic_tile:
                    from PyQt6.QtGui import QPalette, QColor
                    for label_widget in (icon_lbl, lbl_title, lbl_count, lbl_sub, pct_lbl):
                        if label_widget:
                            palette = label_widget.palette()
                            palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))
                            palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
                            label_widget.setPalette(palette)

    def init_ui(self):
        if self._is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
        self.setStyleSheet(
            "background-color: #F3F4F6;" if self._is_classic_appearance()
            else theme_qss("background-color: @surface_alt;")
        )

        if self.layout() is None:
            self.main_layout = QVBoxLayout(self)
        else:
            self.main_layout = self.layout()
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

        self.content_layout = self.main_layout
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("DashboardMainTabs")
        if self._is_classic_appearance():
            self.tabs.setProperty("skipThemeTransform", False)
        self.tabs.setStyleSheet(self._dashboard_tabs_qss())
        self.tab_dashboard = QWidget(self)
        self._classic_guard(self.tab_dashboard)
        self.tab_dashboard.setStyleSheet(
            "background-color: #F3F4F6;" if self._is_classic_appearance()
            else theme_qss("background-color: @surface_alt;")
        )
        self.tabs.addTab(self.tab_dashboard, "🏠 Dashboard")

        dashboard_v_layout = QVBoxLayout(self.tab_dashboard)
        dashboard_v_layout.setContentsMargins(0, 0, 0, 0)
        dashboard_v_layout.setSpacing(0)

        self.ticker = TickerWidget(self.db)
        dashboard_v_layout.addWidget(self.ticker)

        content_wrapper = QWidget(self.tab_dashboard)
        self.dashboard_content_wrapper = content_wrapper
        content_wrapper.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._classic_guard(content_wrapper)
        content_wrapper.setStyleSheet(
            "background-color: #F3F4F6;" if self._is_classic_appearance()
            else theme_qss("background-color: @surface_alt;")
        )
        self.dashboard_layout = QVBoxLayout(content_wrapper)
        if self._is_classic_appearance():
            self.dashboard_layout.setContentsMargins(8, 8, 8, 0)
            self.dashboard_layout.setSpacing(6)
        else:
            self.dashboard_layout.setContentsMargins(8, 10, 8, 0)
            self.dashboard_layout.setSpacing(12)

        self.create_welcome_header(self.dashboard_layout)
        self.create_insight_strip(self.dashboard_layout)
        self.create_dashboard_metrics(self.dashboard_layout)
        self.create_dashboard_charts(self.dashboard_layout)
        self.dashboard_bottom_strip = QWidget(content_wrapper)
        self.dashboard_bottom_strip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._classic_guard(self.dashboard_bottom_strip)
        self.dashboard_bottom_strip.setStyleSheet("background: transparent; border: none;")
        bottom_layout = QHBoxLayout(self.dashboard_bottom_strip)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        self.dashboard_datetime = QWidget(self.dashboard_bottom_strip)
        self.dashboard_datetime.setFixedHeight(26)
        self._classic_guard(self.dashboard_datetime)
        self.dashboard_datetime.setStyleSheet("background: transparent; border: none;")
        dt_layout = QHBoxLayout(self.dashboard_datetime)
        dt_layout.setContentsMargins(0, 0, 0, 0)
        dt_layout.setSpacing(10)

        self.lbl_dashboard_time = QLabel()
        self.lbl_dashboard_time.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._classic_guard(self.lbl_dashboard_time)
        self.lbl_dashboard_time.setStyleSheet(
            "font-size: 20px; font-weight: 800; color: #111827; border: none; background: transparent;"
            if self._is_classic_appearance()
            else theme_qss("font-size: 20px; font-weight: 800; color: @text; border: none; background: transparent;")
        )
        self.lbl_dashboard_date = QLabel()
        self.lbl_dashboard_date.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._classic_guard(self.lbl_dashboard_date)
        self.lbl_dashboard_date.setStyleSheet(
            "font-size: 12px; font-weight: 700; color: #4B5563; border: none; background: transparent;"
            if self._is_classic_appearance()
            else theme_qss("font-size: 12px; font-weight: 700; color: @text_muted; border: none; background: transparent;")
        )

        dt_layout.addStretch()
        dt_layout.addWidget(self.lbl_dashboard_time)
        dt_layout.addWidget(self.lbl_dashboard_date)
        dt_layout.addStretch()

        bottom_layout.addWidget(self.dashboard_datetime, 5)
        bottom_layout.addSpacing(4)
        bottom_layout.addStretch(1)
        self.dashboard_bottom_strip.setFixedHeight(28)
        self.dashboard_layout.addWidget(self.dashboard_bottom_strip, 0)

        self.dashboard_clock_timer = QTimer(self)
        self.dashboard_clock_timer.timeout.connect(self._update_dashboard_datetime)
        self.dashboard_clock_timer.start(1000)
        self._update_dashboard_datetime()

        dashboard_v_layout.addWidget(content_wrapper)

        if SystemConfig.is_feature_active(self.db, "usage_guides"):
            self.tab_guide = QWidget(self)
            self.setup_usage_guide_tab()
            self.tabs.addTab(self.tab_guide, "? Nasıl Kullanılır?")

        self.main_layout.addWidget(self.tabs)

        QTimer.singleShot(0, self.refresh_data)
        QTimer.singleShot(250, self.refresh_data)
        QTimer.singleShot(1000, self.refresh_data)

    def sync_dashboard_sector_texts(self):
        sector = self._dashboard_sector_key()
        if hasattr(self, "_status_tiles"):
            tile_defs = get_status_tile_defs(sector)
            tile_map = {t[0]: t for t in tile_defs}
            for key, tile in self._status_tiles.items():
                if key not in tile_map:
                    continue
                _, label, subtitle, icon, color, *_ = tile_map[key]
                if tile.get("title"):
                    tile["title"].setText(label)
                if tile.get("icon"):
                    icon_size = 16 if self._is_classic_appearance() else 28
                    icon_color = tc("text") if self._is_classic_appearance() else "#FFFFFF"
                    tile["icon"].setPixmap(
                        dashboard_icon(key, icon_color, icon_size).pixmap(
                            icon_size,
                            icon_size,
                        )
                    )
                tile["base_sub"] = subtitle
        if hasattr(self, "filter_buttons"):
            button_defs = get_filter_button_defs(sector)
            btn_map = {t[0]: t for t in button_defs}
            for key, _, icon, _, _ in button_defs:
                btn = self.filter_buttons.get(key)
                if btn:
                    classic = self._is_classic_appearance()
                    text = btn_map[key][1]
                    btn.setText(text)
        if hasattr(self, "table"):
            self.table.setHorizontalHeaderLabels(get_table_headers(sector))
        if hasattr(self, "lbl_table_title"):
            self.lbl_table_title.setText(get_table_title(sector, getattr(self, "current_filter_category", "all")))
        if hasattr(self, "recent_empty_state") and getattr(self.recent_empty_state, "lbl_message", None):
            self.recent_empty_state.lbl_message.setText(get_empty_state_message(sector))

    def _sidebar_action_defs(self):
        if self._dashboard_sector_key() == "otomotiv":
            return [
                ("Yeni Müşteri Ekle", "+", tc("accent"), self.open_new_customer_dialog),
                ("Araç İş Emri", "İş", tc("success"), self.open_service_form_shortcut),
                ("Bakım / Servis Paneli", "*", tc("warning"), lambda: self.main_window.open_technician_panel()),
                ("Stok Ekle", "+", tc("accent"), self.open_add_stock_dialog),
                ("Cari İşlemler", "₺", tc("danger"), lambda: self.main_window.switch_page(PageIds.INCOME_EXPENSE)),
                ("Veri Yedekleme", "Y", tc("text_muted"), lambda: self.main_window.switch_page(PageIds.BACKUP)),
            ]
        return [
            ("Yeni Müşteri Ekle", "+", tc("accent"), self.open_new_customer_dialog),
            ("Servis Formu", "S", tc("success"), self.open_service_form_shortcut),
            ("Teknisyen Paneli", "*", tc("warning"), lambda: self.main_window.open_technician_panel()),
            ("Stok Ekle", "+", tc("accent"), self.open_add_stock_dialog),
            ("Cari İşlemler", "₺", tc("danger"), lambda: self.main_window.switch_page(PageIds.INCOME_EXPENSE)),
            ("Veri Yedekleme", "Y", tc("text_muted"), lambda: self.main_window.switch_page(PageIds.BACKUP)),
        ]

    def create_insight_strip(self, parent_layout):
        sector = self._dashboard_sector_key()
        self.insight_container, self._status_tiles = create_status_tile_widgets(
            self, get_status_tile_defs(sector), db=self.db
        )
        for key, tile in self._status_tiles.items():
            frame = tile.get("frame") if isinstance(tile, dict) else None
            if frame is None:
                continue
            frame.setCursor(Qt.CursorShape.PointingHandCursor)
            original_press = frame.mousePressEvent
            def _open_filtered(event, _key=key, _original=original_press):
                if event.button() == Qt.MouseButton.LeftButton and self.main_window is not None and hasattr(self.main_window, "open_service_list"):
                    self.main_window.open_service_list(_key)
                    return
                _original(event)
            frame.mousePressEvent = _open_filtered
        # Populate counts immediately and retry after delayed database startup.
        QTimer.singleShot(0, self.update_dashboard_status_tiles)
        QTimer.singleShot(250, self.update_dashboard_status_tiles)
        QTimer.singleShot(1000, self.update_dashboard_status_tiles)
        QTimer.singleShot(2000, self.update_dashboard_status_tiles)
        QTimer.singleShot(5000, self.update_dashboard_status_tiles)
        parent_layout.addWidget(self.insight_container)

    def _make_status_tile(self, key, label, subtitle, icon, bg_color, icon_bg=None):
        tile = make_status_tile(self, key, label, subtitle, icon, bg_color, icon_bg, db=self.db)
        frame = tile.get("frame") if isinstance(tile, dict) else tile
        if frame is not None and hasattr(frame, "mousePressEvent"):
            original_press = frame.mousePressEvent
            def _open_filtered(event, _key=key, _original=original_press):
                if event.button() == Qt.MouseButton.LeftButton and self.main_window is not None and hasattr(self.main_window, "open_service_list"):
                    self.main_window.open_service_list(_key)
                    return
                _original(event)
            frame.mousePressEvent = _open_filtered
        return tile

    def create_takiponline_filter_strip(self, parent_layout):
        self.filter_buttons = {}
        strip = QFrame(self)
        strip.setObjectName("TakipOnlineFilterStrip")
        strip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if self._is_classic_appearance():
            strip.setProperty("skipThemeTransform", False)
        strip.setStyleSheet(self._filter_strip_qss())

        outer = QVBoxLayout(strip)
        classic = self._is_classic_appearance()
        outer.setContentsMargins(8 if classic else 16, 6 if classic else 8, 8 if classic else 16, 6 if classic else 8)
        outer.setSpacing(4)

        row = QGridLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4 if classic else 6)

        sector = self._dashboard_sector_key()
        button_defs = get_filter_button_defs(sector)
        status_tile_filter_keys = {"test", "waiting", "active", "done", "part", "debt"}
        button_defs = [item for item in button_defs if item[0] not in status_tile_filter_keys]

        for index, (key, text, icon, color, action) in enumerate(button_defs):
            btn = create_filter_button(self, key, text, icon, color, action, db=self.db)
            if action == "add":
                btn.clicked.connect(self.open_service_form_shortcut)
            else:
                btn.clicked.connect(lambda _=False, k=key: self.apply_filter(k))
            # Keep the reduced filter set on one balanced row.
            row.addWidget(btn, index // 9, index % 9)
            self.filter_buttons[key] = btn

        for column in range(9):
            row.setColumnStretch(column, 1)

        # Add quick shortcuts at the far right
        self.shortcut_container = QWidget(self)
        self.shortcut_container.setStyleSheet("background: transparent; border: none;")
        sh_lay = QHBoxLayout(self.shortcut_container)
        sh_lay.setContentsMargins(0, 0, 0, 0)
        sh_lay.setSpacing(8)

        self.btn_sh_add_customer = QPushButton("👤➕") if classic else QPushButton()
        self.btn_sh_add_customer.setCursor(Qt.CursorShape.PointingHandCursor)

        if sector == "otomotiv":
            self.btn_sh_add_vehicle = QPushButton("🚗➕") if classic else QPushButton()
            vehicle_tooltip = "Yeni Ara\u00e7 Ekle"
        else:
            self.btn_sh_add_vehicle = QPushButton("💻➕") if classic else QPushButton()
            vehicle_tooltip = "Yeni Cihaz Ekle"
        self.btn_sh_add_vehicle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._shortcut_tooltips = [
            ThemedToolTipFilter(
                self.btn_sh_add_customer,
                "Yeni M\u00fc\u015fteri Ekle",
                self.db,
            ),
            ThemedToolTipFilter(
                self.btn_sh_add_vehicle,
                vehicle_tooltip,
                self.db,
            ),
        ]

        svg_add_customer = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="8.5" cy="7" r="4"></circle><line x1="20" y1="8" x2="20" y2="14"></line><line x1="23" y1="11" x2="17" y2="11"></line></svg>"""
        if sector == "otomotiv":
            svg_add_vehicle = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-1.1 0-2 .9-2 2v7h2"></path><circle cx="7" cy="17" r="2"></circle><circle cx="17" cy="17" r="2"></circle><line x1="12" y1="12" x2="12" y2="18"></line><line x1="15" y1="15" x2="9" y2="15"></line></svg>"""
        else:
            svg_add_vehicle = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="2" y1="20" x2="22" y2="20"></line><line x1="12" y1="17" x2="12" y2="20"></line><line x1="15" y1="9" x2="9" y2="9"></line><line x1="12" y1="6" x2="12" y2="12"></line></svg>"""

        if not classic:
            text_color = tc("text") or "#111827"
            self.btn_sh_add_customer.setIcon(render_svg_icon(svg_add_customer, text_color, size=18))
            self.btn_sh_add_customer.setIconSize(QSize(18, 18))
            self.btn_sh_add_vehicle.setIcon(render_svg_icon(svg_add_vehicle, text_color, size=18))
            self.btn_sh_add_vehicle.setIconSize(QSize(18, 18))

        for btn in (self.btn_sh_add_customer, self.btn_sh_add_vehicle):
            btn.setFixedSize(36 if not classic else 30, 36 if not classic else 30)
            if classic:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FFFFFF;
                        color: #111827;
                        border: 1px solid #AEB4BD;
                        border-radius: 0px;
                        font-size: 13px;
                    }
                    QPushButton:hover { background-color: #EAF2FF; border-color: #8BAFD8; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #111827;
                        border: 1px solid #94A3B8;
                        padding: 5px 8px;
                    }
                """)
            else:
                btn.setStyleSheet(theme_qss("""
                    QPushButton {
                        background: @surface;
                        border: 1px solid @border;
                        border-radius: 18px;
                    }
                    QPushButton:hover {
                        background: @surface_alt;
                        border: 1px solid @accent;
                    }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #111827;
                        border: 1px solid #94A3B8;
                        padding: 5px 8px;
                    }
                """))
            sh_lay.addWidget(btn)

        shortcut_size = 36 if not classic else 30
        self.shortcut_container.setFixedWidth((shortcut_size * 2) + sh_lay.spacing())
        self.shortcut_container.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self.btn_sh_add_customer.clicked.connect(self._sh_add_customer)
        self.btn_sh_add_vehicle.clicked.connect(self._sh_add_vehicle_or_device)

        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(8)
        filter_row.addLayout(row, 1)
        filter_row.addWidget(
            self.shortcut_container,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        )
        outer.addLayout(filter_row)
        self._create_dashboard_action_toolbar(outer)
        parent_layout.addWidget(strip)

    def _create_dashboard_action_toolbar(self, parent_layout):
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 4, 0, 0)
        bar.setSpacing(5)

        actions = (
            ("Filtrele", lambda: self.dashboard_quick_search.setFocus()),
            ("Temizle", self._clear_dashboard_quick_filters),
            ("Servis Ge\u00e7mi\u015fi", self._open_selected_service_history),
            ("Detayl\u0131 Fi\u015f Yazd\u0131r", lambda: self._run_selected_service_action(self.print_detailed_receipt)),
            ("Kargo Fi\u015fi Yazd\u0131r", lambda: self._run_selected_service_action(self.print_cargo_receipt)),
            ("E-\u0130rsaliye Olu\u015ftur", self._open_selected_dispatch),
            ("E-Fatura Kes", lambda: self._run_selected_service_action(
                lambda tracking_no: self.open_context_menu_action("invoice", tracking_no)
            )),
        )
        self.dashboard_quick_action_buttons = []
        for text, callback in actions:
            button = QPushButton(text, self)
            button.setObjectName("DashboardQuickActionButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(28)
            button.setStyleSheet(theme_qss("""
                QPushButton#DashboardQuickActionButton {
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 5px;
                    padding: 3px 8px;
                    font-size: 10px;
                    font-weight: 700;
                }
                QPushButton#DashboardQuickActionButton:hover {
                    background: @surface_alt;
                    border-color: @accent;
                }
            """))
            button.clicked.connect(callback)
            bar.addWidget(button)
            self.dashboard_quick_action_buttons.append(button)

        bar.addStretch(1)
        self.dashboard_page_controls = QWidget(self)
        self.dashboard_page_controls.setObjectName("DashboardPageControls")
        controls = QHBoxLayout(self.dashboard_page_controls)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)
        self.dashboard_page_size = QComboBox(self)
        self.dashboard_page_size.setObjectName("DashboardPageSize")
        self.dashboard_page_size.addItems(["10", "25", "50"])
        self.dashboard_page_size.setFixedSize(70, 28)
        self.dashboard_page_size.setToolTip(
            "Sayfada g\u00f6sterilecek servis say\u0131s\u0131"
        )
        self.dashboard_page_size.setStyleSheet(theme_qss("""
            QComboBox#DashboardPageSize {
                padding: 2px 24px 2px 8px;
            }
            QComboBox#DashboardPageSize::drop-down {
                width: 22px;
            }
        """))
        self.dashboard_page_size.currentTextChanged.connect(self._apply_dashboard_quick_filters)
        controls.addWidget(self.dashboard_page_size)

        self.dashboard_quick_search = QLineEdit(self)
        self.dashboard_quick_search.setObjectName("DashboardQuickSearch")
        self.dashboard_quick_search.setPlaceholderText("Ara...")
        self.dashboard_quick_search.setClearButtonEnabled(True)
        self.dashboard_quick_search.setFixedSize(170, 28)
        self.dashboard_quick_search.textChanged.connect(self._apply_dashboard_quick_filters)
        controls.addWidget(self.dashboard_quick_search)
        self.dashboard_page_controls.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )
        bar.addWidget(
            self.dashboard_page_controls,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        parent_layout.addLayout(bar)

    def _selected_dashboard_tracking_no(self):
        table = getattr(self, "table", None)
        if table is None or table.currentRow() < 0:
            self.notify("L\u00fctfen listeden bir servis kayd\u0131 se\u00e7in.", "warning")
            return ""
        item = table.item(table.currentRow(), 0)
        return str(item.text()).strip() if item else ""

    def _run_selected_service_action(self, callback):
        tracking_no = self._selected_dashboard_tracking_no()
        if tracking_no:
            callback(tracking_no)

    def _open_selected_service_history(self):
        table = getattr(self, "table", None)
        tracking_no = self._selected_dashboard_tracking_no()
        if not tracking_no or table is None:
            return
        customer_item = table.item(table.currentRow(), 2)
        customer_name = str(customer_item.text()).strip() if customer_item else ""
        self.open_customer_360_dialog(customer_name, tracking_no=tracking_no)

    def _open_selected_dispatch(self):
        tracking_no = self._selected_dashboard_tracking_no()
        if tracking_no:
            self.notify(
                f"E-\u0130rsaliye haz\u0131rlama i\u00e7in servis kayd\u0131 se\u00e7ildi: {tracking_no}",
                "info",
            )

    def _clear_dashboard_quick_filters(self):
        search = getattr(self, "dashboard_quick_search", None)
        if search is not None:
            search.clear()
        self.apply_filter("all")

    def _apply_dashboard_quick_filters(self, _value=None):
        table = getattr(self, "table", None)
        search = getattr(self, "dashboard_quick_search", None)
        size_box = getattr(self, "dashboard_page_size", None)
        if table is None or search is None or size_box is None:
            return
        query = search.text().strip().casefold()
        limit = int(size_box.currentText() or "10")
        matched = 0
        for row in range(table.rowCount()):
            row_text = " ".join(
                table.item(row, column).text()
                for column in range(table.columnCount())
                if table.item(row, column) is not None
            ).casefold()
            visible = (not query or query in row_text) and matched < limit
            table.setRowHidden(row, not visible)
            if visible:
                matched += 1

    def _sh_add_customer(self):
        sector = self._dashboard_sector_key()
        sector_manager = getattr(self.main_window, "sector_manager", None)
        if sector == "otomotiv":
            from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls
        
        dlg = dialog_cls(self.db, self, sector_manager=sector_manager)
        if dlg.exec():
            self.refresh_data()
            self.notify("Yeni müşteri başarıyla eklendi.", "success")

    def _sh_add_vehicle_or_device(self):
        sector = self._dashboard_sector_key()
        if sector == "otomotiv":
            from src.ui.dialogs.customer_select_dialog import CustomerSelectDialog
            dlg = CustomerSelectDialog(self.db, self)
            if dlg.exec() and dlg.selected_customer:
                c = dlg.selected_customer
                c_id = c[0]
                c_name = c[1]
                from src.ui.dialogs.customer_vehicle_dialog import CustomerVehicleDialog
                v_dlg = CustomerVehicleDialog(self.db, c_id, c_name, parent=self)
                if v_dlg.exec():
                    self.refresh_data()
                    self.notify("Müşteriye yeni araç başarıyla eklendi.", "success")
        else:
            from src.ui.dialogs.add_device_dialog import AddDeviceDialog
            dlg = AddDeviceDialog(self.db, self)
            if dlg.exec():
                self.refresh_data()
                self.notify("Yeni cihaz/servis kaydı başarıyla eklendi.", "success")

    def create_recent_table(self):
        sector = self._dashboard_sector_key()
        container = QFrame(self)
        container.setObjectName("DashboardRecentContainer")
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet(self._recent_container_qss())

        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.lbl_table_title = QLabel(get_table_title(sector, self.current_filter_category))
        self.lbl_table_title.setObjectName("DashboardTableTitle")
        self.lbl_table_title.setStyleSheet(theme_qss(
            "QLabel#DashboardTableTitle { color: @text; background-color: transparent; "
            "border: none; font-size: 15px; font-weight: 800; padding: 4px 8px; }"
        ))
        header.addWidget(self.lbl_table_title)
        header.addStretch(1)

        btn_more = QPushButton("Tumunu Gor ->")
        btn_more.setObjectName("DashboardSeeAllButton")
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_more.setMinimumHeight(34)
        btn_more.setStyleSheet(theme_qss("""
            QPushButton#DashboardSeeAllButton {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 700;
            }
            QPushButton#DashboardSeeAllButton:hover {
                background-color: @hover_bg;
                color: @text;
                border-color: @accent;
            }
        """))
        if self.main_window is not None and hasattr(self.main_window, "switch_page"):
            btn_more.clicked.connect(lambda: self.main_window.switch_page(PageIds.JOB_TRACKING))
        header.addWidget(btn_more)
        layout.addLayout(header)

        table_wrap = QFrame(container)
        table_wrap.setObjectName("DashboardTableWrap")
        table_wrap.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        table_wrap.setStyleSheet(theme_qss("""
            QFrame#DashboardTableWrap {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 4px;
            }
        """))
        table_layout = QVBoxLayout(table_wrap)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        self.table = QTableWidget(0, len(get_table_headers(sector)), table_wrap)
        self.table.setObjectName("DashboardServiceTable")
        self.table.setHorizontalHeaderLabels(get_table_headers(sector))
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        self.table.setWordWrap(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        try:
            self.table.cellDoubleClicked.disconnect(self.on_table_double_click)
        except (TypeError, RuntimeError):
            pass
        self.table.cellDoubleClicked.connect(self.on_table_double_click)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(42 if self._is_classic_appearance() else 58)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setStyleSheet(takiponline_table_qss(db=self.db))

        automotive_widths = [118, 292, 210, 132, 105, 125, 108, 145, 135, 130, 160, 94]
        technical_widths = [118, 292, 330, 132, 96, 120, 108, 118, 98, 104, 164, 94]
        for index, width in enumerate(automotive_widths if sector == "otomotiv" else technical_widths):
            self.table.setColumnWidth(index, width)
        if sector != "otomotiv":
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        table_layout.addWidget(self.table)

        self.recent_empty_state = EmptyState(
            "i",
            "Kayit bulunamadi",
            get_empty_state_message(sector),
            parent=table_wrap,
        )
        self.recent_empty_state.setObjectName("DashboardRecentEmptyState")
        self.recent_empty_state.hide()
        table_layout.addWidget(self.recent_empty_state)

        layout.addWidget(table_wrap, 1)
        return container

    def _table_title(self, category=None):
        if category is None:
            category = getattr(self, "current_filter_category", "all")
        return get_table_title(self._dashboard_sector_key(), category)

    def _update_recent_empty_state(self):
        if not hasattr(self, "recent_empty_state") or not hasattr(self, "table"):
            return
        is_empty = self.table.rowCount() == 0
        self.recent_empty_state.setVisible(is_empty)
        self.table.setVisible(not is_empty)

    def setup_usage_guide_tab(self):
        layout = QVBoxLayout(self.tab_guide)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(0)

        guide_text = QTextBrowser(self.tab_guide)
        guide_text.setOpenExternalLinks(True)
        guide_text.setStyleSheet(theme_qss("""
            QTextBrowser {
                background-color: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 4px;
                padding: 18px;
            }
        """))
        guide_text.setHtml(f"""
            <div style="font-family:{DesignTokens.FONT_FAMILY}; color:{tc('text')};">
                <h2 style="color:{tc('accent')}; margin-top:0;">Genel Bakis Kullanimi</h2>
                <p>Bu ekran servis kayitlarini, durum ozetlerini ve hizli filtreleri tek yerden takip etmek icin kullanilir.</p>
                <h3>Temel Islemler</h3>
                <ul>
                    <li><b>Cihaz Ekle:</b> Yeni servis kaydi olusturur.</li>
                    <li><b>Filtreler:</b> Servis listesini durumuna gore daraltir.</li>
                    <li><b>Cift tiklama:</b> Musteri, cihaz veya servis kaydi detayini acar.</li>
                    <li><b>Sag tik:</b> Kayit uzerinde hizli durum ve islem menusu acar.</li>
                </ul>
                <h3>Okuma Mantigi</h3>
                <p>Ust ozetler toplam durumu gosterir; alt tablo ise aktif takip listesidir.</p>
            </div>
        """)
        layout.addWidget(guide_text)

    def create_today_appointments_card(self):
        container = QFrame(self)
        container.setObjectName("TodayAppointmentsCard")
        container.setStyleSheet(theme_qss(
            """
            QFrame#TodayAppointmentsCard {
                background-color: @surface;
                border-radius: 20px;
                border: 1px solid @border;
            }
            """
        ))

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 8))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        hl = QHBoxLayout()
        hl.setContentsMargins(15, 10, 15, 0)
        lbl_title = QLabel("Bugünkü Randevular")
        lbl_title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 700; color: @text; border: none;"))
        hl.addWidget(lbl_title)
        hl.addStretch()

        self.critical_stock_badge = QPushButton()
        self.critical_stock_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.critical_stock_badge.setVisible(False)
        self.critical_stock_badge.setFixedHeight(30)
        self.critical_stock_badge.setStyleSheet(theme_qss(
            """
            QPushButton {
                background-color: rgba(245, 158, 11, 0.12);
                color: @warning;
                border: 1px solid rgba(245, 158, 11, 0.25);
                border-radius: 12px;
                padding: 0 10px;
                font-weight: 800;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(245, 158, 11, 0.18);
            }
            """
        ))
        self.critical_stock_badge.clicked.connect(lambda: self.main_window.switch_page(PageIds.STOCK))
        hl.addWidget(self.critical_stock_badge)

        btn_more = QPushButton("Tümünü Gör ->")
        self._classic_guard(btn_more)
        btn_more.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._is_classic_appearance():
            btn_more.setProperty("skipThemeTransform", False)
        btn_more.setStyleSheet(theme_qss("border: none; color: @accent; font-weight: 600; font-size: 14px; text-align: right;"))
        btn_more.clicked.connect(lambda: self.main_window.switch_page(PageIds.APPOINTMENTS))
        hl.addWidget(btn_more)

        layout.addLayout(hl)

        self.info_flow_text = QLabel("Randevular yükleniyor...")
        self.info_flow_text.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 700; border: none; padding: 0 15px;"))
        layout.addWidget(self.info_flow_text)

        self.info_flow_progress = QProgressBar()
        self.info_flow_progress.setRange(0, 2)
        self.info_flow_progress.setValue(0)
        self.info_flow_progress.setFixedHeight(6)
        self.info_flow_progress.setTextVisible(False)
        self.info_flow_progress.setStyleSheet(theme_qss(
            """
            QProgressBar {
                background-color: @surface_alt;
                border: none;
                border-radius: 3px;
                margin: 0 15px;
            }
            QProgressBar::chunk {
                background-color: @accent;
                border-radius: 3px;
            }
            """
        ))
        layout.addWidget(self.info_flow_progress)

        self.appointments_table = QTableWidget()
        self.appointments_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.appointments_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.appointments_table.setColumnCount(4)
        self.appointments_table.setHorizontalHeaderLabels(["SAAT", "MÜŞTERİ", "AÇIKLAMA", "DURUM"])

        header = self.appointments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.appointments_table.setColumnWidth(0, 90)
        self.appointments_table.setColumnWidth(1, 220)
        self.appointments_table.setColumnWidth(3, 140)

        self.appointments_table.verticalHeader().setVisible(False)
        self.appointments_table.verticalHeader().setDefaultSectionSize(54)
        self.appointments_table.setShowGrid(False)
        self.appointments_table.setFrameShape(QFrame.Shape.NoFrame)
        self.appointments_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.appointments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.appointments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.appointments_table.setStyleSheet(theme_qss(
            """
            QTableWidget {
                border: none;
                background-color: @surface;
                gridline-color: @surface_alt;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text_muted;
                padding-left: 10px;
                padding-right: 10px;
                border: none;
                font-weight: 700;
                font-size: 12px;
                border-bottom: 2px solid @border;
                text-align: left;
            }
            QTableWidget::item {
                padding-left: 10px;
                padding-right: 10px;
                border-bottom: 1px solid @surface_alt;
                color: @text;
            }
            QTableWidget::item:selected {
                background-color: @selection_bg;
                color: @selection_text;
                border: none;
                outline: none;
            }
            """
        ))

        layout.addWidget(self.appointments_table)
        return container

    def _refresh_today_appointments(self):
        if not hasattr(self, "appointments_table"):
            return

        self._today_appointments_state = {}
        self.info_flow_state["appointments_loaded"] = False
        self.info_flow_state["appointments_total"] = 0
        self.info_flow_state["appointments_completed"] = 0
        self.info_flow_state["critical_stock_shown"] = False

        if hasattr(self, "info_flow_text"):
            self.info_flow_text.setText("Randevular yükleniyor...")
        if hasattr(self, "info_flow_progress"):
            self.info_flow_progress.setValue(0)

        self.appointments_table.setRowCount(0)
        self.appointments_table.setUpdatesEnabled(False)
        self.appointments_table.setSortingEnabled(False)

        today_str = datetime.now().strftime("%Y-%m-%d")
        rows = []
        try:
            self.db.cursor.execute(
                "SELECT id, time, customer_name, description, status FROM appointments WHERE date=? ORDER BY time ASC",
                (today_str,),
            )
            rows = self.db.cursor.fetchall() or []
        except (AttributeError, TypeError, ValueError) as e:
            logger.debug(f"Daily appointments primary query failed: {e}")
            try:
                basic = self.db.get_daily_appointments() or []
                rows = [(None, r[0], r[1], r[2], None) for r in basic]
            except (AttributeError, TypeError, ValueError) as fallback_error:
                logger.debug(f"Daily appointments fallback failed: {fallback_error}")
                rows = []

        total = len(rows)
        completed = 0

        for row_idx, r in enumerate(rows):
            try:
                appt_id, time_str, customer_name, desc, status = r
            except (TypeError, ValueError):
                continue

            status_text = str(status or "Bekliyor").strip() or "Bekliyor"
            is_completed = self._appointment_is_completed(status_text)
            if is_completed:
                completed += 1

            self.appointments_table.insertRow(row_idx)

            it_time = QTableWidgetItem(str(time_str or ""))
            it_time.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.appointments_table.setItem(row_idx, 0, it_time)

            it_cust = QTableWidgetItem(str(customer_name or ""))
            it_cust.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.appointments_table.setItem(row_idx, 1, it_cust)

            it_desc = QTableWidgetItem(str(desc or ""))
            it_desc.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.appointments_table.setItem(row_idx, 2, it_desc)

            if appt_id:
                self._today_appointments_state[int(appt_id)] = {
                    "row": row_idx,
                    "status": status_text,
                }

            btn_status = QPushButton(status_text.upper())
            btn_status.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_status.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._apply_appointment_status_style(btn_status, status_text)

            menu = QMenu(btn_status)
            menu.setStyleSheet(theme_qss(
                """
                QMenu {
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 8px 12px;
                    border-radius: 6px;
                    color: @text;
                }
                QMenu::item:selected {
                    background-color: @surface_alt;
                }
                """
            ))
            for opt in ["Bekliyor", "Geldi", "İşlemde", "Tamamlandı", "İptal"]:
                a = QAction(opt, self)
                a.triggered.connect(lambda _=False, aid=appt_id, stat=opt, idx=row_idx: self._update_today_appointment_status(aid, stat, idx))
                menu.addAction(a)
            btn_status.setMenu(menu)

            self.appointments_table.setCellWidget(row_idx, 3, btn_status)

        self.appointments_table.setUpdatesEnabled(True)
        self.appointments_table.setSortingEnabled(True)

        self.info_flow_state["appointments_loaded"] = True
        self.info_flow_state["appointments_total"] = total
        self.info_flow_state["appointments_completed"] = completed

        if hasattr(self, "info_flow_text"):
            if total == 0:
                self.info_flow_text.setText("Bugün için randevu bulunamadı.")
            else:
                self.info_flow_text.setText(f"Randevular hazır: {completed}/{total} tamamlandı")

        if hasattr(self, "info_flow_progress"):
            self.info_flow_progress.setValue(2)

    def _update_dashboard_datetime(self):
        try:
            dt = datetime.now()
            if hasattr(self, "lbl_dashboard_time"):
                self.lbl_dashboard_time.setText(dt.strftime("%H:%M"))
            if hasattr(self, "lbl_dashboard_date"):
                self.lbl_dashboard_date.setText(dt.strftime("%d %B %Y, %A"))
        except Exception:
            pass

    def refresh_theme(self):
        self.apply_theme_styles()
        from src.utils.theme_manager import ThemeManager

        ThemeManager.refresh_widget_tree(self)
        self.update()
