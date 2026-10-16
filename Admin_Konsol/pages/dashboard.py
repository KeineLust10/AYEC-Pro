"""
AYEC Pro Admin Konsol - Dashboard Sayfasi
Sunucu istatistikleri, firma ozeti, sistem sagli\u011fi.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QFileDialog
)
from PyQt6.QtCore import QPoint, Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPolygon
import api_client
import csv
import time

_ACTION_LABELS = {
    "admin_password_reset": "Ge\u00e7ici parola atand\u0131",
    "admin_password_reset_link": "Parola s\u0131f\u0131rlama ba\u011flant\u0131s\u0131 olu\u015fturuldu",
    "admin_license_updated": "Lisans g\u00fcncellendi",
    "admin_notification_sent": "Bildirim g\u00f6nderildi",
    "admin_update_deployed": "G\u00fcncelleme da\u011f\u0131t\u0131m\u0131 kuyrukland\u0131",
    "admin_restore_queued": "Geri y\u00fckleme kuyrukland\u0131",
    "admin_readonly_query": "Salt okunur sorgu \u00e7al\u0131\u015ft\u0131r\u0131ld\u0131",
    "tenant_updated": "Firma bilgileri g\u00fcncellendi",
    "user_updated": "Kullan\u0131c\u0131 bilgileri g\u00fcncellendi",
}


class _FetchThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._fetch_dashboard = api_client.dashboard
        self._fetch_live_status = api_client.live_status

    def run(self):
        try:
            request_started = time.perf_counter()
            data = self._fetch_dashboard()
            data["dashboard_latency_ms"] = max(0.0, (time.perf_counter() - request_started) * 1000)
            try:
                data["live_companies"] = self._fetch_live_status()
            except Exception:
                data["live_companies"] = []
            self.done.emit(data)
        except Exception as exc:
            self.error.emit(str(exc))


_ACTIVE_FETCH_THREADS = set()


class _MetricIcon(QLabel):
    def __init__(self, icon: str, color: str, accessible_name: str):
        super().__init__()
        self._icon = icon
        self._color = QColor(color)
        self.setObjectName("metricIcon")
        self.setAccessibleName(accessible_name)
        self.setFixedSize(18, 18)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self._color, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self._icon == "building":
            painter.drawRect(3, 2, 12, 14)
            for x in (6, 10, 13):
                painter.drawPoint(x, 6)
                painter.drawPoint(x, 10)
            painter.drawLine(8, 16, 8, 13)
        elif self._icon == "active":
            painter.drawPolygon(QPolygon([QPoint(9, 1), QPoint(16, 4), QPoint(15, 10), QPoint(9, 16), QPoint(3, 10), QPoint(2, 4)]))
            painter.drawLine(5, 8, 8, 11)
            painter.drawLine(8, 11, 13, 5)
        elif self._icon == "paused":
            painter.drawEllipse(2, 2, 14, 14)
            painter.drawLine(7, 6, 7, 12)
            painter.drawLine(11, 6, 11, 12)
        elif self._icon == "users":
            painter.drawEllipse(7, 2, 5, 5)
            painter.drawEllipse(1, 5, 4, 4)
            painter.drawEllipse(14, 5, 4, 4)
            painter.drawArc(5, 8, 10, 9, 0, 180 * 16)
            painter.drawArc(0, 10, 6, 7, 0, 180 * 16)
            painter.drawArc(13, 10, 6, 7, 0, 180 * 16)
        elif self._icon == "login":
            painter.drawLine(2, 9, 13, 9)
            painter.drawLine(9, 5, 13, 9)
            painter.drawLine(9, 13, 13, 9)
            painter.drawLine(13, 3, 16, 3)
            painter.drawLine(16, 3, 16, 15)
            painter.drawLine(16, 15, 13, 15)
        elif self._icon == "storage":
            painter.drawRoundedRect(2, 3, 14, 12, 2, 2)
            painter.drawLine(2, 7, 16, 7)
            painter.drawPoint(13, 11)
        elif self._icon == "backup":
            painter.drawPolygon(QPolygon([QPoint(9, 1), QPoint(16, 4), QPoint(15, 10), QPoint(9, 16), QPoint(3, 10), QPoint(2, 4)]))
            painter.drawLine(6, 8, 8, 10)
            painter.drawLine(8, 10, 12, 6)
        elif self._icon == "command":
            painter.drawRoundedRect(2, 3, 14, 12, 2, 2)
            painter.drawLine(6, 7, 9, 9)
            painter.drawLine(9, 9, 6, 11)
            painter.drawLine(10, 11, 13, 11)
        elif self._icon == "warning":
            painter.drawPolygon(QPolygon([QPoint(9, 1), QPoint(17, 15), QPoint(1, 15)]))
            painter.drawLine(9, 5, 9, 10)
            painter.drawPoint(9, 13)
        elif self._icon == "terminal":
            painter.drawRoundedRect(1, 2, 16, 14, 2, 2)
            painter.drawLine(4, 7, 7, 9)
            painter.drawLine(7, 9, 4, 11)
            painter.drawLine(9, 11, 13, 11)


class _LatencyChart(QWidget):
    def __init__(self):
        super().__init__()
        self._samples = []
        self.setObjectName("dashLatencyChart")
        self.setFixedHeight(64)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_samples(self, samples):
        self._samples = list(samples)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        plot = self.rect().adjusted(4, 4, -4, -20)
        painter.setPen(QPen(QColor(140, 144, 159, 32), 1))
        for row in range(1, 4):
            y = plot.top() + (plot.height() * row / 4)
            painter.drawLine(plot.left(), int(y), plot.right(), int(y))
        now = time.time()
        recent = [(stamp, value) for stamp, value in self._samples if stamp >= now - 3600]
        if recent and plot.width() > 0:
            maximum = max(1.0, max(value for _, value in recent) * 1.15)
            points = []
            for stamp, value in recent:
                ratio = max(0.0, min(1.0, (stamp - (now - 3600)) / 3600))
                x = plot.left() + int(ratio * plot.width())
                y = plot.bottom() - int((max(0.0, value) / maximum) * (plot.height() - 8))
                points.append(QPoint(x, y))
            if len(points) == 1:
                points.insert(0, QPoint(max(plot.left(), points[0].x() - 16), points[0].y()))
            area = QPainterPath()
            area.moveTo(points[0].x(), points[0].y())
            for point in points[1:]:
                area.lineTo(point.x(), point.y())
            area.lineTo(points[-1].x(), plot.bottom())
            area.lineTo(points[0].x(), plot.bottom())
            area.closeSubpath()
            painter.fillPath(area, QColor(83, 141, 255, 28))
            painter.setPen(QPen(QColor("#538dff"), 2))
            for previous, current in zip(points, points[1:]):
                painter.drawLine(previous, current)
            painter.setBrush(QColor("#4edea3"))
            painter.drawEllipse(points[-1], 3, 3)
        painter.end()


def _metric_card(
    title: str,
    value: str,
    sub: str,
    color: str = "#7c6af7",
    icon: str = "",
    badge: str = "",
    status: str = "",
) -> QFrame:
    card = QFrame()
    card.setObjectName("metricCard")
    card.setMinimumHeight(104)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(12, 10, 12, 10)

    title_row = QHBoxLayout()
    t = QLabel(title)
    t.setObjectName("metricTitle")
    title_row.addWidget(t, 1)
    icon_label = _MetricIcon(icon, color, title)
    title_row.addWidget(icon_label)
    lay.addLayout(title_row)

    value_row = QHBoxLayout()
    value_row.setSpacing(6)
    v = QLabel(value)
    v.setObjectName("metricValue")
    v.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: 900; background: transparent;")
    value_row.addWidget(v)
    badge_label = QLabel(badge)
    badge_label.setObjectName("metricBadge")
    badge_label.setVisible(bool(badge))
    value_row.addWidget(badge_label)
    value_row.addStretch(1)
    status_label = QLabel(status)
    status_label.setObjectName("metricTrend")
    status_label.setVisible(bool(status))
    if status == "Ge\u00e7erlilik TAM":
        status_label.setStyleSheet("color: #8c909f;")
    value_row.addWidget(status_label)
    lay.addLayout(value_row)

    s = QLabel(sub)
    s.setObjectName("metricSub")
    lay.addWidget(s)

    return card


def _log_row(entry: dict) -> QFrame:
    row = QFrame()
    row.setObjectName("logRow")
    lay = QHBoxLayout(row)
    lay.setContentsMargins(12, 8, 12, 8)

    time_lbl = QLabel(str(entry.get("time", "")))
    time_lbl.setObjectName("logTime")
    time_lbl.setFixedWidth(140)
    lay.addWidget(time_lbl)

    action = str(entry.get("action", ""))
    action_lbl = QLabel(_ACTION_LABELS.get(action, action.replace("_", " ").title()))
    action_lbl.setObjectName("logAction")
    lay.addWidget(action_lbl, 1)

    firm_lbl = QLabel(str(entry.get("company", "")))
    firm_lbl.setObjectName("logFirm")
    firm_lbl.setFixedWidth(160)
    lay.addWidget(firm_lbl)

    return row


class DashboardPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread: _FetchThread | None = None
        self._metric_cards = []
        self._primary_count = 4
        self._secondary_count = 5
        self._narrow_table = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._latency_samples = []
        self._build_ui()
        self._refresh()
        self._timer.start(30_000)  # 30 sn auto yenile

    def _build_ui(self):
        self.setObjectName("dashboardPage")
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._dashboard_scroll = scroll
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("dashboardContent")
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(content)
        self._dashboard_root_layout = root
        self.setStyleSheet("""
            QWidget#dashboardPage { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#dashboardPage QLabel { background: transparent; }
            QWidget#dashboardContent { background: #0e1321; }
            QScrollArea#dashboardScroll { background: #0e1321; }
            QFrame#dashTopStrip { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; }
            QFrame#dashIconTile { background: rgba(77, 142, 255, 0.16); border: 1px solid #1e293b; border-radius: 4px; }
            QLabel#dashTitle { color: #dee2f6; font-size: 18px; font-weight: 700; }
            QLabel#dashLiveBadge { color: #4cd7f6; background: #1a1f2e; border-radius: 4px; padding: 7px 10px; font-family: 'JetBrains Mono', 'Segoe UI', Arial, 'Inter'; font-size: 11px; }
            QFrame#metricCard { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; min-height: 104px; }
            QLabel#metricTitle { color: #c2c6d6; font-size: 12px; font-weight: 500; }
            QLabel#metricBadge { color: #adc6ff; background: #252a39; border-radius: 3px; padding: 2px 5px; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#metricTrend { color: #4edea3; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#metricSub { color: #8c909f; font-size: 11px; }
            QFrame#dashPanel { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; }
            QFrame#dashPerformancePanel { background: #1b2030; border: 1px solid #1e293b; border-radius: 4px; }
            QLabel#dashPerformanceTitle { color: #dee2f6; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 10px; font-weight: 700; }
            QLabel#dashPerformanceAverage { color: #4edea3; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 10px; font-weight: 700; }
            QLabel#dashPerformanceSubtitle { color: #8c909f; font-size: 9px; }
            QLabel#dashPerformanceAxis { color: #8c909f; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 9px; }
            QLabel#dashPerformanceAxisCurrent { color: #4edea3; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 9px; font-weight: 700; }
            QLabel#dashPanelTitle { color: #dee2f6; font-size: 18px; font-weight: 600; }
            QLabel#dashHealth { background: #1a1f2e; border: 1px solid #252a39; border-radius: 3px; padding: 4px 8px; color: #4edea3; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QFrame#dashCompanyRow { background: #090e1c; border: 1px solid #252a39; border-radius: 3px; }
            QLabel#dashCompanyName { color: #dee2f6; font-size: 13px; font-weight: 700; }
            QLabel#dashCompanyMeta { color: #8c909f; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 9px; }
            QLabel#dashSecurity { background: #090e1c; border: 1px solid #1e293b; border-radius: 4px; padding: 10px; color: #8c909f; font-size: 10px; }
            QLineEdit#dashSearch { background: #252a39; border: 1px solid #424754; border-radius: 3px; padding: 6px 9px; color: #dee2f6; min-width: 210px; }
            QTableWidget#dashTable { background: #090e1c; border: none; color: #dee2f6; gridline-color: #252a39; }
            QTableWidget#dashTable::item { background: #090e1c; padding: 8px 10px; border-bottom: 1px solid #252a39; }
            QTableWidget#dashTable QHeaderView::section { background: #0e1321; color: #8c909f; border: none; padding: 4px 6px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QPushButton#dashPrimaryButton { background: #4d8eff; color: #00285d; border: none; border-radius: 3px; padding: 8px 12px; font-weight: 700; }
            QPushButton#dashSecondaryButton, QPushButton#dashActionButton { background: #252a39; color: #dee2f6; border: none; border-radius: 3px; padding: 8px 10px; text-align: left; }
            QPushButton#dashSecondaryButton:hover, QPushButton#dashActionButton:hover { background: #343948; }
            QLabel#dashStatus { color: #8c909f; font-family: 'JetBrains Mono', 'Segoe UI', Arial, 'Inter'; font-size: 10px; }
        """)
        root.setContentsMargins(40, 0, 16, 4)
        root.setSpacing(12)

        top = QFrame()
        top.setObjectName("dashTopStrip")
        top.setFixedHeight(56)
        self._top_strip = top
        top_lay = QBoxLayout(QBoxLayout.Direction.LeftToRight, top)
        top_lay.setContentsMargins(8, 8, 8, 8)
        top_lay.setSpacing(8)
        identity_layout = QHBoxLayout()
        identity_layout.setSpacing(8)
        icon_tile = QFrame()
        icon_tile.setObjectName("dashIconTile")
        icon_tile.setFixedSize(36, 36)
        icon_layout = QHBoxLayout(icon_tile)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.addWidget(_MetricIcon("terminal", "#4d8eff", "Dashboard"), 0, Qt.AlignmentFlag.AlignCenter)
        identity_layout.addWidget(icon_tile)
        title_box = QVBoxLayout()
        title_line = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        brand = QLabel("Ana Dashboard & Komuta Merkezi")
        brand.setObjectName("dashTitle")
        brand.setWordWrap(True)
        title_line.addWidget(brand)
        version_badge = QLabel("CANLI V2.4")
        version_badge.setObjectName("dashLiveBadge")
        version_badge.setMinimumWidth(90)
        version_badge.setFixedHeight(24)
        version_badge.setStyleSheet("padding: 4px 8px;")
        title_line.addWidget(version_badge)
        title_box.addLayout(title_line)
        self._title_line = title_line
        subtitle = QLabel("AYEC Pro Enterprise Da\u011f\u0131t\u0131k Lisans & Telemetri Hub")
        subtitle.setObjectName("metricSub")
        title_box.addWidget(subtitle)
        identity_layout.addLayout(title_box, 1)
        top_lay.addLayout(identity_layout, 1)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(6)
        self._server_badge = QLabel("\u25cf lisans.ayecpro.com  |  Canl\u0131")
        self._server_badge.setObjectName("dashLiveBadge")
        actions_layout.addWidget(self._server_badge, 1)
        refresh_btn = QPushButton("Yenile (30s)")
        refresh_btn.setObjectName("dashSecondaryButton")
        refresh_btn.clicked.connect(self._refresh)
        actions_layout.addWidget(refresh_btn)
        quick_btn = QPushButton("+ H\u0131zl\u0131 Lisans A\u00e7")
        quick_btn.setObjectName("dashPrimaryButton")
        quick_btn.clicked.connect(lambda: self.navigate_requested.emit("license_requests"))
        actions_layout.addWidget(quick_btn)
        top_lay.addLayout(actions_layout)
        root.addWidget(top)

        metric_area = QVBoxLayout()
        metric_area.setSpacing(12)
        self._primary_grid = QGridLayout()
        self._primary_grid.setSpacing(12)
        self._secondary_grid = QGridLayout()
        self._secondary_grid.setSpacing(12)
        metric_area.addLayout(self._primary_grid)
        metric_area.addLayout(self._secondary_grid)
        root.addLayout(metric_area)

        body = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        body.setSpacing(12)
        self._log_panel = QFrame()
        self._log_panel.setObjectName("dashPanel")
        self._log_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        log_layout = QVBoxLayout(self._log_panel)
        log_layout.setContentsMargins(12, 14, 12, 12)
        log_layout.setSpacing(10)
        log_head = QHBoxLayout()
        log_icon = _MetricIcon("command", "#adc6ff", "Son islemler")
        log_head.addWidget(log_icon)
        title = QLabel("Son \u0130\u015flemler & Sistem Telemetrisi")
        title.setObjectName("dashPanelTitle")
        log_head.addWidget(title, 1)
        self._search = QLineEdit()
        self._search.setPlaceholderText("\u0130\u015flem veya firma filtrele...")
        self._search.setObjectName("dashSearch")
        self._search.textChanged.connect(self._filter_logs)
        self._search.setFixedWidth(240)
        log_head.addWidget(self._search)
        self._csv_button = QPushButton("\u21e9 CSV")
        self._csv_button.setObjectName("dashSecondaryButton")
        self._csv_button.setFixedWidth(60)
        self._csv_button.clicked.connect(self._export_logs)
        log_head.addWidget(self._csv_button)
        log_layout.addLayout(log_head)
        self._log_head = log_head
        self._log_table = QTableWidget(0, 5)
        self._log_table.setObjectName("dashTable")
        self._log_table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self._log_table.setHorizontalHeaderLabels(["ZAMAN DAMGASI", "\u0130\u015flem / Olay", "\u0130lgili Firma", "DURUM", "OPERAT\u00d6R"])
        self._log_table.setWordWrap(True)
        self._log_table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._log_table.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideNone)
        self._log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._log_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._log_table.verticalHeader().hide()
        self._log_table.setShowGrid(False)
        self._log_table.setAlternatingRowColors(False)
        self._log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._log_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._log_table.setMaximumHeight(340)
        self._log_table.setMinimumHeight(320)
        self._log_table.setFixedHeight(340)
        self._log_table.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background: #0e1321; color: #8c909f; "
            "border: none; padding: 4px 6px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }"
        )
        self._log_table.horizontalHeader().setFixedHeight(32)
        log_layout.addWidget(self._log_table)
        self._status_lbl = QLabel("Canl\u0131 ak\u0131\u015f haz\u0131r")
        self._status_lbl.setObjectName("dashStatus")
        log_layout.addWidget(self._status_lbl)
        performance = QFrame()
        performance.setObjectName("dashPerformancePanel")
        performance_layout = QVBoxLayout(performance)
        performance_layout.setContentsMargins(10, 8, 10, 7)
        performance_layout.setSpacing(4)
        performance_header = QHBoxLayout()
        performance_title = QLabel("GER\u00c7EK ZAMANLI SORGU & YANIT PERFORMANSI (SON 60 DAK\u0130KA)")
        performance_title.setObjectName("dashPerformanceTitle")
        performance_title.setWordWrap(True)
        performance_header.addWidget(performance_title, 1)
        self._latency_average = QLabel("Ortalama: -- ms")
        self._latency_average.setObjectName("dashPerformanceAverage")
        self._latency_average.setMinimumWidth(116)
        self._latency_average.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        performance_header.addWidget(self._latency_average)
        performance_layout.addLayout(performance_header)
        performance_subtitle = QLabel("Bu oturumdaki Dashboard API yan\u0131t s\u00fcreleri")
        performance_subtitle.setObjectName("dashPerformanceSubtitle")
        performance_layout.addWidget(performance_subtitle)
        self._latency_chart = _LatencyChart()
        self._latency_chart.setFixedHeight(64)
        performance_layout.addWidget(self._latency_chart)
        performance_axis = QHBoxLayout()
        performance_axis.setSpacing(6)
        for index, caption in enumerate(("-60 dk", "-45 dk", "-30 dk", "-15 dk", "\u015eimdi")):
            axis_label = QLabel(caption)
            axis_label.setObjectName("dashPerformanceAxisCurrent" if index == 4 else "dashPerformanceAxis")
            axis_label.setAlignment(Qt.AlignmentFlag.AlignRight if index == 4 else Qt.AlignmentFlag.AlignLeft if index == 0 else Qt.AlignmentFlag.AlignHCenter)
            performance_axis.addWidget(axis_label, 1)
        performance_layout.addLayout(performance_axis)
        log_layout.addWidget(performance)
        body.addWidget(self._log_panel, 8, Qt.AlignmentFlag.AlignTop)

        side = QWidget()
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(12)
        health_panel = QFrame()
        health_panel.setObjectName("dashPanel")
        health_panel.setMinimumHeight(280)
        health_lay = QVBoxLayout(health_panel)
        health_lay.setContentsMargins(12, 12, 12, 12)
        health_lay.setSpacing(6)
        health = QLabel("Canl\u0131 Firma Sa\u011fl\u0131\u011f\u0131")
        health.setObjectName("dashPanelTitle")
        health_header = QHBoxLayout()
        health_header.setSpacing(8)
        health_header.addWidget(health, 1)
        self._health_summary = QLabel("Firma durumlar\u0131 y\u00fckleniyor...")
        self._health_summary.setObjectName("dashHealth")
        self._health_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        health_header.addWidget(self._health_summary)
        health_lay.addLayout(health_header)
        self._health_rows = QVBoxLayout()
        self._health_rows.setSpacing(6)
        health_lay.addLayout(self._health_rows)
        side_lay.addWidget(health_panel)

        actions_panel = QFrame()
        actions_panel.setObjectName("dashPanel")
        actions_panel.setMinimumHeight(252)
        actions_lay = QVBoxLayout(actions_panel)
        actions_lay.setContentsMargins(14, 14, 14, 14)
        actions_lay.setSpacing(8)
        quick = QLabel("H\u0131zl\u0131 Komuta Eylemleri")
        quick.setObjectName("dashPanelTitle")
        actions_lay.addWidget(quick)
        quick_subtitle = QLabel("Sistem \u00e7ap\u0131nda anl\u0131k i\u015flem ve toplu da\u011f\u0131t\u0131m")
        quick_subtitle.setObjectName("dashPerformanceSubtitle")
        actions_lay.addWidget(quick_subtitle)
        action_pages = (
            ("\u26bf  Yeni Lisans Talebi Onayla", "license_requests"),
            ("\u2601  Anl\u0131k Genel Yedek Tetikle", "backups"),
            ("\u25ce  T\u00fcm Firmalara Bildirim G\u00f6nder", "notifications"),
            ("\u21bb  Core Servisleri Yeniden Baslat", "server_settings"),
        )
        for caption, page_id in action_pages:
            action = QPushButton(caption + "   \u203a")
            action.setObjectName("dashActionButton")
            action.setMinimumHeight(36)
            action.clicked.connect(lambda _, target=page_id: self.navigate_requested.emit(target))
            actions_lay.addWidget(action)
        side_lay.addWidget(actions_panel)
        side_lay.addStretch(1)
        self._security = QLabel(
            "<span style='color:#8c909f;letter-spacing:1px'>L\u0130SANS DO\u011eRULAMA PROTOKOL\u00dc</span> "
            "<span style='color:#4edea3'>TLS 1.3 / AES-256</span><br>"
            "<span style='color:#4cd7f6'>KEY: AYEC-CORE-9984-X812-7801-TK</span><br>"
            "<span style='color:#4edea3'>\u26bf</span> Lisans sunucusu tamper korumas\u0131 devrede."
        )
        self._security.setObjectName("dashSecurity")
        self._security.setWordWrap(True)
        self._security.setMinimumHeight(78)
        side_lay.addWidget(self._security)
        body.addWidget(side, 4)
        root.addLayout(body, 1)
        self._body_layout = body
        self._top_layout = top_lay
        self._actions_layout = actions_layout
        self._refresh_button = refresh_btn
        self._quick_button = quick_btn
        self._side_panel = side
        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        self._log_table.setWordWrap(width >= 640)
        if width < 640:
            for row in range(self._log_table.rowCount()):
                self._log_table.setRowHeight(row, 44)
        else:
            self._log_table.resizeRowsToContents()
            for row in range(self._log_table.rowCount()):
                self._log_table.setRowHeight(row, max(49, self._log_table.rowHeight(row)))
        panel_max_width = max(160, width - 32) if width < 640 else 16_777_215
        self._log_panel.setMaximumWidth(panel_max_width)
        self._side_panel.setMaximumWidth(panel_max_width)
        if width >= 980:
            self._log_panel.setMinimumHeight(568)
            self._log_panel.setMaximumHeight(568)
        else:
            self._log_panel.setMinimumHeight(0)
            self._log_panel.setMaximumHeight(16_777_215)
        self._dashboard_root_layout.setContentsMargins(40 if width >= 760 else 16, 0, 16, 4)
        self._log_table.setMaximumWidth(max(100, panel_max_width - 28))
        self._layout_log_table(width)
        QTimer.singleShot(0, lambda: self._layout_log_table(self.width()))
        self._top_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if width < 760 else QBoxLayout.Direction.LeftToRight
        )
        self._actions_layout.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 360 else QBoxLayout.Direction.TopToBottom
        )
        self._refresh_button.setFixedWidth(112 if width >= 640 else 76)
        self._quick_button.setFixedWidth(126 if width >= 640 else 84)
        if width < 640:
            self._server_badge.setText("\u25cf lisans.ayecpro.com")
            self._server_badge.setStyleSheet("font-size: 9px;")
            self._refresh_button.setText("Yenile\n(30s)")
            self._quick_button.setText("+ H\u0131zl\u0131\nLisans A\u00e7")
            self._refresh_button.setMinimumHeight(48)
            self._quick_button.setMinimumHeight(48)
        else:
            self._server_badge.setText("\u25cf lisans.ayecpro.com  |  Canl\u0131")
            self._server_badge.setStyleSheet("")
            self._refresh_button.setText("Yenile (30s)")
            self._quick_button.setText("+ H\u0131zl\u0131 Lisans A\u00e7")
            self._refresh_button.setMinimumHeight(0)
            self._quick_button.setMinimumHeight(0)
        if width < 760:
            self._top_strip.setMinimumHeight(0)
            self._top_strip.setMaximumHeight(16_777_215)
            self._top_layout.setContentsMargins(8, 8, 8, 8)
        else:
            self._top_strip.setFixedHeight(56)
            self._top_layout.setContentsMargins(8, 8, 8, 8)
        self._title_line.setDirection(
            QBoxLayout.Direction.TopToBottom if width < 340 else QBoxLayout.Direction.LeftToRight
        )
        self._log_head.setDirection(
            QBoxLayout.Direction.TopToBottom if width < 640 else QBoxLayout.Direction.LeftToRight
        )
        primary_count = 1 if width < 640 else 2 if width < 1024 else 4
        secondary_count = 1 if width < 640 else 2 if width < 1024 else 5
        if (primary_count, secondary_count) != (self._primary_count, self._secondary_count):
            self._primary_count = primary_count
            self._secondary_count = secondary_count
            self._reflow_metrics()
        self._body_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if width < 980 else QBoxLayout.Direction.LeftToRight
        )
        self._body_layout.setStretch(0, 102 if width >= 980 else 1)
        self._body_layout.setStretch(1, 50 if width >= 980 else 1)

    def _layout_log_table(self, width: int):
        narrow_table = width < 640
        if not hasattr(self, "_log_table"):
            self._narrow_table = narrow_table
            return
        self._narrow_table = narrow_table
        available_width = max(160, self._log_table.viewport().width())
        if narrow_table:
            widths = (160, 220, 150, 120, 140)
        else:
            proportions = (0.20, 0.28, 0.205, 0.17, 0.145)
            widths = [int(available_width * ratio) for ratio in proportions]
            widths[-1] += available_width - sum(widths)
        header = self._log_table.horizontalHeader()
        for column, column_width in enumerate(widths):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self._log_table.setColumnWidth(column, column_width)

    def _reflow_metrics(self):
        for grid in (self._primary_grid, self._secondary_grid):
            for row in range(grid.rowCount()):
                grid.setRowMinimumHeight(row, 0)
            while grid.count():
                grid.takeAt(0)
        for index, card in enumerate(self._metric_cards):
            if index < 4:
                row = index // self._primary_count
                self._primary_grid.setRowMinimumHeight(row, card.minimumHeight())
                self._primary_grid.addWidget(card, row, index % self._primary_count)
            else:
                offset = index - 4
                row = offset // self._secondary_count
                self._secondary_grid.setRowMinimumHeight(row, card.minimumHeight())
                self._secondary_grid.addWidget(card, row, offset % self._secondary_count)

    def _refresh(self):
        if self._thread and self._thread.isRunning():
            return
        self._status_lbl.setText("Veriler y\u00fckleniyor...")
        self._thread = _FetchThread()
        _ACTIVE_FETCH_THREADS.add(self._thread)
        self._thread.finished.connect(
            lambda thread=self._thread: _ACTIVE_FETCH_THREADS.discard(thread)
        )
        self._thread.done.connect(self._populate)
        self._thread.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._thread.start()

    def _populate(self, data: dict):
        self._status_lbl.setText("")
        try:
            latency = float(data.get("dashboard_latency_ms"))
        except (TypeError, ValueError):
            latency = None
        if latency is not None and latency >= 0:
            self._latency_samples.append((time.time(), latency))
            cutoff = time.time() - 3600
            self._latency_samples = [sample for sample in self._latency_samples if sample[0] >= cutoff][-120:]
        self._latency_chart.set_samples(self._latency_samples)
        if self._latency_samples:
            average = sum(sample[1] for sample in self._latency_samples) / len(self._latency_samples)
            self._latency_average.setText(f"Ortalama: {average:.1f}ms")

        for card in self._metric_cards:
            card.deleteLater()
        self._metric_cards = []

        total = int(data.get("total_companies", 0) or 0)
        active = int(data.get("active_companies", 0) or 0)
        inactive = int(data.get("inactive_companies", max(0, total - active)) or 0)
        coverage = max(0, int(data.get("backup_coverage", 0) or 0))
        coverage_percent = min(100, round(coverage * 100 / total)) if total else 0
        active_percent = min(100, round(active * 100 / total)) if total else 0
        expiring = max(0, int(data.get("expiring_licenses", 0) or 0))
        risk_count = inactive + expiring
        metrics = [
            ("Toplam Kay\u0131tl\u0131 Firma", str(total), "Kay\u0131tl\u0131 ve veritaban\u0131 aktif firmalar", "#adc6ff", "building", "Tenant", "+1 bu ay"),
            ("Aktif Lisansl\u0131 Firma", str(active), "Lisans ve token s\u00fcresi ge\u00e7erli", "#4edea3", "active", f"%{active_percent} Aktif", "Ge\u00e7erlilik TAM" if active_percent == 100 else "Kontrol gerekli"),
            ("Pasif / Ask\u0131da Firma", str(inactive), "Lisans kontrol\u00fc gerekli" if risk_count else "S\u00fcresi dolan lisans bulunmuyor", "#c2c6d6", "paused", f"{risk_count} Risk", "Stabil" if not risk_count else "Kontrol"),
            ("Canl\u0131 \u0130stemci & Kullan\u0131c\u0131", str(data.get("online_users", 0)), "Aktif oturum a\u00e7m\u0131\u015f operat\u00f6rler", "#4cd7f6", "users", "WebSocket Ba\u011fl\u0131", ""),
            ("Bug\u00fcn Giri\u015f", str(data.get("logins_today", 0)), "Son 24 saat i\u00e7inde", "#adc6ff", "login", "", ""),
            ("Sunucu SSD Alan\u0131", str(data.get("disk_usage", "?")), "Sunucu diski", "#4cd7f6", "storage", "", ""),
            ("Yedek Kapsam\u0131", f"{coverage} / {total} Firma", f"%{coverage_percent} " + ("Tam Koruma (Bulut)" if coverage_percent == 100 else "Koruma (Bulut)"), "#4edea3" if coverage_percent == 100 else "#adc6ff", "backup", "", ""),
            ("Bekleyen Komut", str(data.get("pending_commands", 0)), "Kuyrukta", "#dee2f6", "command", "", ""),
            ("Lisans Biti\u015f Uyar\u0131s\u0131", str(expiring), "30 g\u00fcn i\u00e7inde", "#ffb4ab", "warning", "", ""),
        ]

        for idx, (title, value, sub, color, icon, badge, status) in enumerate(metrics):
            card = _metric_card(title, value, sub, color, icon, badge, status)
            if idx < 4:
                card.setFixedHeight(108)
            else:
                card.setFixedHeight(106)
            self._metric_cards.append(card)
        self._reflow_metrics()

        logs = data.get("recent_logs", [])
        self._rows = []
        self._log_table.setRowCount(0)
        for entry in logs[:20]:
            action = str(entry.get("action", ""))
            values = (
                str(entry.get("time", "")),
                _ACTION_LABELS.get(action, action.replace("_", " ").title()),
                str(entry.get("company", "")),
                str(entry.get("status", "Recorded")),
                str(entry.get("operator", "System")),
            )
            row = self._log_table.rowCount()
            self._log_table.insertRow(row)
            for col, value in enumerate(values):
                display_value = value.replace(" ", "\n", 1) if col == 0 else value
                item = QTableWidgetItem(display_value)
                item.setData(Qt.ItemDataRole.UserRole, value)
                if col in (0, 1, 3, 4):
                    cell_font = QFont("JetBrains Mono", 9)
                    if col == 1:
                        cell_font.setWeight(QFont.Weight.DemiBold)
                else:
                    cell_font = QFont("Segoe UI", 10)
                    cell_font.setWeight(QFont.Weight.DemiBold)
                item.setFont(cell_font)
                item.setForeground(QColor("#dee2f6" if col != 4 else "#c2c6d6"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | (Qt.AlignmentFlag.AlignRight if col == 4 else Qt.AlignmentFlag.AlignLeft))
                if col == 3:
                    status_text = value.casefold()
                    status_color = "#f3b84d" if "bekle" in status_text else "#4cd7f6" if "mb" in status_text or "ms" in status_text else "#adc6ff" if "365" in status_text else "#4edea3"
                    item.setForeground(QColor(status_color))
                self._log_table.setItem(row, col, item)
                if col in (1, 2, 3):
                    cell = QWidget()
                    cell_layout = QHBoxLayout(cell)
                    cell_layout.setContentsMargins(6, 0, 6, 0)
                    cell_layout.setSpacing(6)
                    cell.setStyleSheet("background: transparent;")
                    if col == 1:
                        status_text = str(entry.get("status", "Recorded")).casefold()
                        dot_color = "#f3b84d" if any(word in status_text for word in ("bekle", "pending", "queue")) else "#ffb4ab" if any(word in status_text for word in ("fail", "error", "reject")) else "#4edea3"
                        dot = QLabel("\u25cf")
                        dot.setStyleSheet(f"color: {dot_color}; font-size: 9px; background: transparent;")
                        cell_layout.addWidget(dot)
                        action_label = QLabel(value)
                        action_label.setObjectName("dashActionLabel")
                        action_label.setWordWrap(True)
                        action_label.setStyleSheet("color: #dee2f6; font: 600 11px 'JetBrains Mono', 'Segoe UI', Arial; background: transparent;")
                        cell_layout.addWidget(action_label, 1)
                    elif col == 2:
                        company_icon = QLabel("\u25a6")
                        company_icon.setStyleSheet("color: #4cd7f6; font-size: 12px; background: transparent;")
                        cell_layout.addWidget(company_icon)
                        company_label = QLabel(value)
                        company_label.setWordWrap(True)
                        company_label.setStyleSheet("color: #dee2f6; font: 600 11px 'Segoe UI', Arial; background: transparent;")
                        cell_layout.addWidget(company_label, 1)
                    else:
                        status_label = QLabel(value)
                        status_label.setObjectName("dashStatusPill")
                        status_background = "#173a30" if status_color == "#4edea3" else "#153b45" if status_color == "#4cd7f6" else "#202d47" if status_color == "#adc6ff" else "#3d3020"
                        status_label.setStyleSheet(f"color: {status_color}; background: {status_background}; border-radius: 3px; padding: 3px 6px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial;")
                        cell_layout.addWidget(status_label, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    self._log_table.setCellWidget(row, col, cell)
                    item.setData(Qt.ItemDataRole.DisplayRole, "")
            self._rows.append(values)
        self._layout_log_table(self.width())
        self._log_table.resizeRowsToContents()
        for row in range(self._log_table.rowCount()):
            self._log_table.setRowHeight(row, max(49, self._log_table.rowHeight(row)))
        self._filter_logs()
        active = int(data.get("active_companies", 0) or 0)
        companies = data.get("live_companies", [])
        online = sum(bool(company.get("online")) for company in companies)
        self._health_summary.setText(f"{online} / {len(companies) or total} ONLINE")
        while self._health_rows.count():
            item = self._health_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for company in companies[:5]:
            row = QFrame()
            row.setObjectName("dashCompanyRow")
            row.setMinimumHeight(52)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            details_layout = QVBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(2)
            status = "Online" if company.get("online") else "Offline"
            indicator = QLabel("\u25cf")
            indicator.setStyleSheet(
                "color: #4edea3; font-size: 13px;" if company.get("online")
                else "color: #ffb4ab; font-size: 13px;"
            )
            row_layout.addWidget(indicator, 0, Qt.AlignmentFlag.AlignVCenter)
            company_name = QLabel(str(company.get("company_name", "?")))
            company_name.setObjectName("dashCompanyName")
            details_layout.addWidget(company_name)
            active_users = int(company.get("active_users", 0) or 0)
            last_seen = str(company.get("last_seen", "") or "")
            metadata = []
            client_version = str(company.get("client_version", "") or "").strip()
            ping_ms = company.get("ping_ms")
            if client_version:
                client_meta = client_version
                if ping_ms is not None:
                    client_meta += f" \u2022 Ping: {ping_ms}ms"
                metadata.append(client_meta)
            elif active_users:
                metadata.append(f"{active_users} aktif kullan\u0131c\u0131")
            if last_seen and not client_version:
                metadata.append(f"Son g\u00f6r\u00fclme: {last_seen}")
            if metadata:
                company_details = QLabel("  |  ".join(metadata))
                company_details.setObjectName("dashCompanyMeta")
                details_layout.addWidget(company_details)
            row_layout.addLayout(details_layout, 1)
            status_column = QVBoxLayout()
            status_column.setContentsMargins(0, 0, 0, 0)
            status_column.setSpacing(2)
            company_status = QLabel(status)
            company_status.setObjectName("dashCompanyStatus")
            company_status.setStyleSheet("color: #4edea3; background: rgba(78, 222, 163, 0.10); border-radius: 3px; padding: 2px 5px; font: 9px 'JetBrains Mono', 'Segoe UI', Arial;" if company.get("online") else "color: #ffb4ab; background: rgba(255, 180, 171, 0.10); border-radius: 3px; padding: 2px 5px; font: 9px 'JetBrains Mono', 'Segoe UI', Arial;")
            status_column.addWidget(company_status, 0, Qt.AlignmentFlag.AlignRight)
            if last_seen:
                seen_label = QLabel(last_seen)
                seen_label.setObjectName("dashCompanySeen")
                status_column.addWidget(seen_label, 0, Qt.AlignmentFlag.AlignRight)
            row_layout.addLayout(status_column)
            self._health_rows.addWidget(row)
        if not companies:
            self._health_summary.setText(f"{active} / {total} AKTIF")

    def _filter_logs(self):
        query = self._search.text().strip().casefold()
        visible = 0
        for row in range(self._log_table.rowCount()):
            match = not query or any(
                query in (
                    f"{self._log_table.item(row, col).text()} {self._log_table.item(row, col).data(Qt.ItemDataRole.UserRole) or ''}".casefold()
                    if self._log_table.item(row, col) else ""
                )
                for col in range(self._log_table.columnCount())
            )
            self._log_table.setRowHidden(row, not match)
            visible += int(match)
        self._status_lbl.setText(f"Toplam {visible} sistem kayd\u0131 listeleniyor (Canl\u0131 ak\u0131\u015f)")

    def _export_logs(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV Olarak Indir", "admin-telemetry.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as output:
            writer = csv.writer(output)
            writer.writerow(("ZAMAN DAMGASI", "\u0130\u015eLEM / OLAY", "\u0130LG\u0130L\u0130 F\u0130RMA", "DURUM", "OPERAT\u00d6R"))
            for row in range(self._log_table.rowCount()):
                if self._log_table.isRowHidden(row):
                    continue
                writer.writerow(self._rows[row] if row < len(self._rows) else tuple(self._log_table.item(row, col).text() if self._log_table.item(row, col) else "" for col in range(self._log_table.columnCount())))

    def closeEvent(self, event):
        self._timer.stop()
        if self._thread and self._thread.isRunning():
            for signal in (self._thread.done, self._thread.error):
                try:
                    signal.disconnect()
                except TypeError:
                    pass
            self._thread.wait(1000)
        super().closeEvent(event)
