"""
AYEC Pro Admin Konsol - Canli Firma Durumu
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QGridLayout, QBoxLayout, QLineEdit,
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPainterPath, QPen
from pathlib import Path
from datetime import datetime
import api_client


_FONT_PATH = Path(__file__).resolve().parents[2] / "Web_Arayuzu" / "web" / "assets" / "fonts" / "Inter-Variable.ttf"


class _LatencyChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumHeight(150)
        self.setObjectName("latencyChart")

    def set_values(self, values):
        self.values = list(values[-360:])
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = self.rect().adjusted(12, 10, -12, -10)
        painter.fillRect(self.rect(), QColor("#090e1c"))
        for fraction in (0.2, 0.5, 0.8):
            y = bounds.top() + int(bounds.height() * fraction)
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1, Qt.PenStyle.DashLine))
            painter.drawLine(bounds.left(), y, bounds.right(), y)
        if len(self.values) < 2:
            painter.setPen(QColor("#8c909f"))
            painter.drawText(bounds, Qt.AlignmentFlag.AlignCenter, "Waiting for live latency samples")
            return
        maximum = max(max(self.values), 100.0)
        points = [
            (bounds.left() + index * bounds.width() / (len(self.values) - 1),
             bounds.bottom() - min(value, maximum) * bounds.height() / maximum)
            for index, value in enumerate(self.values)
        ]
        line = QPainterPath()
        line.moveTo(*points[0])
        for point in points[1:]:
            line.lineTo(*point)
        painter.setPen(QPen(QColor("#4cd7f6"), 2))
        painter.drawPath(line)
        area = QPainterPath(line)
        area.lineTo(bounds.right(), bounds.bottom())
        area.lineTo(bounds.left(), bounds.bottom())
        area.closeSubpath()
        painter.fillPath(area, QColor(76, 215, 246, 28))


class _FetchStatus(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.live_status())
        except Exception as exc:
            self.error.emit(str(exc))


def _status_card(company: dict, navigate=None, refresh=None) -> QFrame:
    card = QFrame()
    card.setObjectName("fleetCard")
    card.setMinimumWidth(0)
    card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    accent = "#4edea3" if company.get("online") else "#ffb4ab"
    card.setStyleSheet(f"QFrame#fleetCard {{ background: #161b2a; border: 1px solid #1e293b; border-top: 3px solid {accent}; border-radius: 4px; }}")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(16)

    online = company.get("online", False)
    root_tenant = bool(
        company.get("is_platform_root")
        or company.get("is_root_tenant")
        or str(company.get("tenant_role") or "").casefold() in {"root", "platform"}
    )
    identity = QHBoxLayout()
    identity.setSpacing(8)
    icon_symbol = company.get("icon_symbol") or ("\u25a3" if root_tenant else "\u25c7" if str(company.get("sector") or "").casefold() == "otomotiv" else "\u25a4")
    company_icon = QLabel(str(icon_symbol))
    company_icon.setObjectName("companyIcon")
    company_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    company_icon.setFixedSize(44, 44)
    company_icon.setStyleSheet(
        "color: #4edea3; background: #103b3b; border-radius: 8px; font-size: 20px;"
        if online else "color: #ffb4ab; background: #3a2027; border-radius: 8px; font-size: 20px;"
    )
    identity.addWidget(company_icon)
    name = QLabel(str(company.get("company_name", "?")))
    name.setObjectName("cardName")
    name.setWordWrap(True)
    name.setMinimumWidth(0)
    name_column = QVBoxLayout()
    name_column.setSpacing(2)
    name_row = QHBoxLayout()
    name_row.setSpacing(8)
    name_row.addWidget(name)
    sector = str(company.get("sector") or "").strip()
    sector_label = {"teknik_servis": "TEKN\u0130K SERV\u0130S", "otomotiv": "OTOMOT\u0130V"}.get(sector.casefold(), sector.upper())
    if sector_label:
        sector_badge = QLabel(sector_label)
        sector_badge.setObjectName("cardSector")
        sector_badge.setWordWrap(True)
        sector_badge.setMinimumWidth(0)
        name_row.addWidget(sector_badge)
    name_row.addStretch(1)
    name_column.addLayout(name_row)
    metadata = []
    if company.get("location"):
        metadata.append(str(company["location"]))
    if company.get("id"):
        metadata.append(f"ID: {company.get('display_id') or company['id']}")
    if metadata:
        meta_label = QLabel("  |  ".join(metadata))
        meta_label.setObjectName("cardMeta")
        meta_label.setWordWrap(True)
        meta_label.setMinimumWidth(0)
        name_column.addWidget(meta_label)
    identity.addLayout(name_column, 1)
    status_lbl = QLabel("\u00c7EVR\u0130M\u0130\u00c7\u0130" if online else "\u00c7EVR\u0130MDI\u015eI")
    status_lbl.setObjectName("cardStatus")
    status_lbl.setWordWrap(True)
    status_lbl.setMinimumWidth(0)
    status_lbl.setStyleSheet(f"color: {'#4edea3' if online else '#ffb4ab'};")
    status_column = QVBoxLayout()
    status_column.setSpacing(4)
    status_column.addWidget(status_lbl, 0, Qt.AlignmentFlag.AlignRight)
    heartbeat = str(company.get("heartbeat") or company.get("last_seen") or "").strip()
    if heartbeat:
        if heartbeat.casefold().startswith("heartbeat:"):
            heartbeat = heartbeat.split(":", 1)[1].strip()
        heartbeat_label = QLabel(f"Heartbeat: {heartbeat}")
        heartbeat_label.setObjectName("cardHeartbeat")
        heartbeat_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        heartbeat_label.setWordWrap(True)
        status_column.addWidget(heartbeat_label)
    identity.addLayout(status_column)
    lay.addLayout(identity)

    telemetry_panel = QFrame()
    telemetry_panel.setObjectName("telemetryPanel")
    telemetry = QGridLayout(telemetry_panel)
    telemetry.setContentsMargins(8, 12, 8, 12)
    telemetry.setHorizontalSpacing(14)
    telemetry.setVerticalSpacing(5)
    telemetry.setObjectName("telemetryMatrix")
    ping_value = company.get("display_ping_ms", company.get("ping_ms", company.get("latency_ms", company.get("ping"))))
    status_label = "SENKRON\u0130ZASYON" if company.get("sync_status") else "BEKLEYEN KUYRUK" if company.get("pending_orders") is not None else "UPTIME"
    status_value = str(company.get("sync_status")) if company.get("sync_status") else f"{company.get('pending_orders')} Fi\u015f Bekliyor" if company.get("pending_orders") is not None else str(company.get("uptime_text") or company.get("uptime") or "--")
    telemetry_values = (
        ("PING / GEC\u0130KME", f"{ping_value} ms" if ping_value is not None else "--"),
        ("S\u0130STEM S\u00dcR\u00dcM\u00dc", str(company.get("dashboard_version") or company.get("version") or company.get("client_version") or "--")),
        (status_label, status_value),
        (
            "SOCKET PORTU" if company.get("socket_port") else "IP SOKETI",
            f"{company.get('socket_port')} (SSL)" if company.get("ssl_enabled") and company.get("socket_port") else str(company.get("socket_port") or company.get("socket_ip") or company.get("ip_address") or "--"),
        ),
    )
    telemetry_pairs = []
    for index, (label_text, value_text) in enumerate(telemetry_values):
        label = QLabel(label_text)
        label.setObjectName("telemetryLabel")
        label.setMinimumWidth(0)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        value = QLabel(value_text)
        value.setObjectName("telemetryValue")
        value.setProperty("tone", ("success", "primary", "surface", "secondary")[index])
        value.setMinimumWidth(0)
        value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        telemetry.addWidget(label, 0, index)
        telemetry.addWidget(value, 1, index)
        telemetry_pairs.append((label, value))
    card._telemetry_layout = telemetry
    card._telemetry_pairs = telemetry_pairs
    lay.addWidget(telemetry_panel)

    session_details = []
    session_name = company.get("session_username") or company.get("username") or company.get("actor_username")
    session_role = company.get("session_role") or company.get("user_role") or company.get("role")
    if session_name:
        session_details.append(f"{session_name} ({session_role})" if session_role else str(session_name))
    elif company.get("user_id") is not None:
        session_details.append(f"Oturum kullan\u0131c\u0131s\u0131: #{company['user_id']}")
    if not session_name and company.get("user_agent"):
        session_details.append(str(company["user_agent"]))
    session_ip = company.get("session_ip") or company.get("ip_address")
    if session_ip and not company.get("socket_ip"):
        session_details.append(f"IP: {session_ip}")
    if company.get("session_port"):
        session_details.append(f"Port: {company['session_port']}")
    if online and company.get("active_users") and not session_name:
        session_details.append(f"{company['active_users']} aktif oturum")
    if session_details:
        session_label = QLabel("  |  ".join(session_details))
        session_label.setObjectName("cardDetail")
        session_label.setMinimumHeight(28)
        session_label.setWordWrap(True)
        session_label.setMinimumWidth(0)
        lay.addWidget(session_label)
    if company.get("db_filename"):
        db_details = [str(company.get("db_path") or f"Veritaban\u0131: {company['db_filename']}")]
        if company.get("db_size_mb") is not None:
            db_details.append(f"{company['db_size_mb']} MB")
        if company.get("wal_frames") is not None:
            db_details.append(f"WAL: {company['wal_frames']}")
        if company.get("unsynced_queue"):
            db_details.append(f"Kuyruk: {company['unsynced_queue']}")
        if company.get("sync_status"):
            db_details.append(str(company["sync_status"]))
        database_label = QLabel("  |  ".join(db_details))
        database_label.setObjectName("cardDetail")
        database_label.setMinimumHeight(28)
        database_label.setWordWrap(True)
        database_label.setMinimumWidth(0)
        lay.addWidget(database_label)

    actions = QGridLayout()
    action_buttons = []
    action_specs = [("Ping G\u00f6nder", None)]
    if root_tenant:
        action_specs.append(("Uzaktan Te\u015fhis", "server_settings"))
    action_specs.append(("Masa\u00fcst\u00fc Mesaj\u0131" if root_tenant else "Mesaj G\u00f6nder", "notifications"))
    action_specs.append(("Yedek Tetikle", "backups") if root_tenant else ("\u0130ncele & Loglar", "audit_logs"))
    for label, page_id in action_specs:
        button = QPushButton(label)
        button.setObjectName("liveButton")
        if page_id and navigate:
            button.clicked.connect(lambda _, target=page_id: navigate(target))
        elif refresh:
            button.clicked.connect(refresh)
        actions.addWidget(button, 0, len(action_buttons))
        action_buttons.append(button)
    if root_tenant and action_buttons:
        action_buttons[-1].setObjectName("livePrimary")
    card._action_layout = actions
    card._action_buttons = action_buttons
    lay.addLayout(actions)

    return card


class _LiveMetricIcon(QWidget):
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.setObjectName("liveMetricIcon")
        self.setFixedSize(44, 44)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#4cd7f6"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.kind == "terminal":
            painter.drawRoundedRect(10, 11, 24, 17, 3, 3)
            painter.drawLine(22, 28, 22, 33)
            painter.drawLine(16, 34, 28, 34)
        elif self.kind == "latency":
            path = QPainterPath()
            path.moveTo(9, 23)
            path.lineTo(15, 23)
            path.lineTo(19, 16)
            path.lineTo(24, 29)
            path.lineTo(29, 19)
            path.lineTo(35, 19)
            painter.drawPath(path)
        elif self.kind == "traffic":
            painter.drawLine(10, 17, 33, 17)
            painter.drawLine(28, 12, 33, 17)
            painter.drawLine(28, 22, 33, 17)
            painter.drawLine(34, 28, 11, 28)
            painter.drawLine(16, 23, 11, 28)
            painter.drawLine(16, 33, 11, 28)
        else:
            painter.drawRoundedRect(12, 10, 20, 7, 2, 2)
            painter.drawRoundedRect(12, 19, 20, 7, 2, 2)
            painter.drawRoundedRect(12, 28, 20, 7, 2, 2)


class LiveStatusPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._thread: _FetchStatus | None = None
        self._latency_history = []
        self._event_fingerprints = {}
        self._events = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._build_ui()
        self._refresh()
        self._timer.start(5_000)

    def _build_ui(self):
        self.setObjectName("liveStatusPage")
        if _FONT_PATH.is_file():
            font_id = QFontDatabase.addApplicationFont(str(_FONT_PATH))
            families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            if families:
                self.setFont(QFont(families[0], 10))
        self.setStyleSheet("""
            QWidget#liveStatusPage { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#liveStatusPage QLabel { background: transparent; }
            QWidget#livePageContent { background: #0e1321; }
            QWidget#liveStatusPage QFrame#statusPanel { background: #161b2a; border: 1px solid #1e293b; border-radius: 4px; }
            QWidget#liveHeaderActions { background: transparent; }
            QLabel#liveKicker { color: #adc6ff; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; letter-spacing: 1px; }
            QLabel#liveTitle { color: #dee2f6; font-size: 20px; font-weight: 700; }
            QLabel#liveSubtitle { color: #c2c6d6; font-size: 12px; }
            QLabel#liveCounter { color: #dee2f6; background: #252a39; border: 1px solid #252a39; border-radius: 8px; padding: 6px 10px; font-size: 11px; font-weight: 700; }
            QLabel#liveMetricValue { color: #dee2f6; font-size: 25px; font-weight: 700; }
            QLabel#liveMetricLabel { color: #8c909f; font-size: 10px; font-weight: 700; }
            QLabel#liveMetricDetail { color: #4edea3; font-size: 10px; }
            QWidget#liveMetricIcon { background: #252a39; border-radius: 8px; }
            QLabel#cardName { color: #dee2f6; font-size: 17px; font-weight: 700; }
            QLabel#cardSector { color: #adc6ff; background: #252a39; border-radius: 3px; padding: 3px 6px; font: 700 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#cardStatus { background: #1a1f2e; border-radius: 12px; padding: 4px 10px; font: 700 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#cardMeta { color: #8c909f; font: 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#cardHeartbeat { color: #8c909f; font: 9px "JetBrains Mono", "Segoe UI", Arial; }
            QWidget#liveStatusPage QLabel#cardDetail { color: #c2c6d6; background: #090e1c; border-radius: 4px; padding: 7px 8px; font-size: 10px; }
            QLineEdit#liveSearch { background: #252a39; border: 1px solid #424754; border-radius: 3px; padding: 8px 10px; color: #dee2f6; min-width: 250px; }
            QPushButton#liveFilter { background: #252a39; color: #dee2f6; border: none; border-radius: 3px; padding: 8px 12px; }
            QPushButton#liveFilter[active=true] { background: #4d8eff; color: #00285d; font-weight: 700; }
            QPushButton#liveButton { background: #252a39; color: #dee2f6; border: none; border-radius: 3px; padding: 6px 7px; font-size: 9px; }
            QPushButton#livePrimary { background: #4d8eff; color: #00285d; border: none; border-radius: 3px; padding: 6px 7px; font-size: 9px; font-weight: 700; }
            QFrame#fleetCard { border-top: 3px solid #4edea3; }
            QScrollArea#livePageScroll { background: #0e1321; border: none; }
            QFrame#fleetGridContainer { background: transparent; border: none; }
        QFrame#telemetryPanel { background: #252a39; border-radius: 4px; }
        QLabel#telemetryLabel { color: #8c909f; font-size: 9px; font-weight: 700; }
        QLabel#telemetryValue[tone="success"] { color: #4edea3; font-size: 10px; font-weight: 700; }
        QLabel#telemetryValue[tone="primary"] { color: #adc6ff; font-size: 10px; font-weight: 700; }
        QLabel#telemetryValue[tone="surface"] { color: #dee2f6; font-size: 10px; font-weight: 700; }
        QLabel#telemetryValue[tone="secondary"] { color: #4cd7f6; font-size: 10px; font-weight: 700; }
            QLabel#statusLabel { color: #8c909f; font-size: 10px; }
            QLabel#telemetryTitle { color: #dee2f6; font-size: 16px; font-weight: 700; }
            QLabel#telemetrySubtitle { color: #c2c6d6; font-size: 10px; }
            QListWidget#eventFeed { background: #090e1c; color: #c2c6d6; border: none; border-radius: 4px; font-size: 10px; }
            QListWidget#eventFeed::item { padding: 6px 8px; border-bottom: 1px solid #252a39; }
        """)
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_scroll = QScrollArea(self)
        page_scroll.setObjectName("livePageScroll")
        page_scroll.setWidgetResizable(True)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_content = QWidget()
        page_content.setObjectName("livePageContent")
        page_content.setMinimumWidth(0)
        page_content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(page_content)
        root.setContentsMargins(40, 8, 16, 16)
        root.setSpacing(16)
        page_scroll.setWidget(page_content)
        page_layout.addWidget(page_scroll)
        self._page_scroll = page_scroll
        self._scroll = page_scroll

        header = QFrame()
        self._header = header
        header.setObjectName("statusPanel")
        header.setMinimumHeight(118)
        top = QBoxLayout(QBoxLayout.Direction.LeftToRight, header)
        self._header_layout = top
        top.setContentsMargins(14, 10, 14, 10)
        title_col = QVBoxLayout()
        self._title_column = title_col
        kicker = QLabel("AYEC NET-RADAR v2.0  |  ROOT-TENANT-GATEWAY")
        kicker.setObjectName("liveKicker")
        kicker.setWordWrap(True)
        kicker.setMinimumWidth(0)
        title_col.addWidget(kicker)
        title = QLabel("Canl\u0131 Firma Durumu & \u0130stemci Telemetri \u0130zleme")
        title.setObjectName("liveTitle")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title_col.addWidget(title)
        subtitle = QLabel("T\u00fcm kirac\u0131 (tenant) masa\u00fcst\u00fc terminallerinin soket ba\u011flant\u0131lar\u0131n\u0131, yerel SQLite WAL d\u00fc\u011f\u00fcmlerini, gecikme s\u00fcrelerini ve veri senkronizasyon durumunu canl\u0131 izleyin.")
        self._subtitle = subtitle
        subtitle.setObjectName("liveSubtitle")
        subtitle.setWordWrap(True)
        title_col.addWidget(subtitle)
        top.addLayout(title_col, 1)
        actions = QWidget(header)
        actions.setObjectName("liveHeaderActions")
        action_column = QVBoxLayout(actions)
        self._action_column = action_column
        action_column.setContentsMargins(0, 0, 0, 0)
        action_column.setSpacing(6)
        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(8)
        self._status_action_row = action_row
        self._counter = QLabel("\u25cf  Canl\u0131 Ak\u0131\u015f (5sn)  OTOMAT\u0130K")
        self._counter.setObjectName("liveCounter")
        self._counter.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        action_row.addWidget(self._counter)
        refresh = QPushButton("Manuel Yenile")
        self._refresh_button = refresh
        refresh.setObjectName("liveButton")
        refresh.clicked.connect(self._refresh)
        action_row.addWidget(refresh)
        broadcast = QPushButton("Acil Anons G\u00f6nder")
        self._broadcast_button = broadcast
        broadcast.setObjectName("livePrimary")
        broadcast.clicked.connect(lambda: self.navigate_requested.emit("notifications"))
        action_column.addLayout(action_row)
        action_column.addWidget(broadcast, 0, Qt.AlignmentFlag.AlignLeft)
        self._mobile_action_buttons = QHBoxLayout()
        self._mobile_action_buttons.setContentsMargins(0, 0, 0, 0)
        self._mobile_action_buttons.setSpacing(8)
        self._mobile_actions_active = False
        self._header_actions = actions
        top.addWidget(actions, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(header)

        metrics = QGridLayout()
        self._metrics_layout = metrics
        metrics.setHorizontalSpacing(12)
        metrics.setVerticalSpacing(12)
        self._metric_widgets = []
        self._metric_detail_widgets = []
        self._metric_panels = []
        metric_items = (
            ("TOPLAM BA\u011eLI TERM\u0130NAL", "terminal"),
            ("ORTALAMA A\u011e P\u0130NG\u0130", "latency"),
            ("ANLIK VER\u0130 AKI\u015eI", "traffic"),
            ("E\u015e\u0130TLENMEM\u0130\u015e KUYRUK", "queue"),
        )
        for label, symbol in metric_items:
            panel = QFrame()
            panel.setObjectName("statusPanel")
            panel.setMinimumHeight(112)
            layout = QGridLayout(panel)
            layout.setContentsMargins(14, 10, 14, 10)
            value = QLabel("--")
            value.setObjectName("liveMetricValue")
            value.setMinimumWidth(0)
            caption = QLabel(label)
            caption.setObjectName("liveMetricLabel")
            caption.setWordWrap(True)
            caption.setMinimumWidth(0)
            detail = QLabel("Live status")
            detail.setObjectName("liveMetricDetail")
            detail.setWordWrap(True)
            detail.setMinimumWidth(0)
            icon = _LiveMetricIcon(symbol)
            panel.setMinimumWidth(0)
            layout.addWidget(caption, 0, 0, 1, 2)
            layout.addWidget(value, 1, 0, 1, 2)
            layout.addWidget(detail, 2, 0, 1, 2)
            layout.addWidget(icon, 0, 2, 3, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            metrics.addWidget(panel, 0, len(self._metric_widgets))
            self._metric_panels.append(panel)
            self._metric_widgets.append(value)
            self._metric_detail_widgets.append(detail)
        root.addLayout(metrics)

        shelf = QFrame()
        shelf.setObjectName("statusPanel")
        shelf.setMinimumHeight(60)
        shelf_layout = QGridLayout(shelf)
        self._filter_layout = shelf_layout
        shelf_layout.setContentsMargins(12, 8, 12, 8)
        shelf_layout.setHorizontalSpacing(6)
        shelf_layout.setVerticalSpacing(6)
        self._filter_buttons = {}
        for index, (key, label) in enumerate((("all", "T\u00fcm\u00fc"), ("online", "Sorunsuz"), ("slow", "Y\u00fcksek Gecikme"), ("offline", "\u00c7evrimd\u0131\u015f\u0131"))):
            button = QPushButton(label)
            button.setObjectName("liveFilter")
            button.setProperty("active", key == "all")
            button.clicked.connect(lambda _, value=key: self._set_filter(value))
            shelf_layout.addWidget(button, 0, index)
            self._filter_buttons[key] = button
        self._search = QLineEdit()
        self._search.setObjectName("liveSearch")
        self._search.setMinimumWidth(0)
        self._search.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._search.setPlaceholderText("Firma ad\u0131, IP veya terminal ara...")
        self._search.textChanged.connect(self._apply_filter)
        shelf_layout.addWidget(self._search, 0, 4)
        root.addWidget(shelf)

        self._inner = QFrame()
        self._inner.setObjectName("fleetGridContainer")
        self._inner.setMinimumWidth(0)
        self._inner.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._grid_lay = QGridLayout(self._inner)
        self._grid_lay.setContentsMargins(0, 0, 0, 0)
        self._grid_lay.setSpacing(16)
        root.addWidget(self._inner)

        telemetry_row = QGridLayout()
        self._telemetry_grid = telemetry_row
        telemetry_row.setHorizontalSpacing(12)
        telemetry_row.setVerticalSpacing(12)
        chart_panel = QFrame()
        chart_panel.setObjectName("statusPanel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(14, 12, 14, 12)
        chart_title = QLabel("Canl\u0131 A\u011f Gecikme Dalga Grafi\u011fi")
        chart_title.setObjectName("telemetryTitle")
        chart_title.setWordWrap(True)
        chart_layout.addWidget(chart_title)
        chart_subtitle = QLabel("Ba\u011fl\u0131 terminallerden al\u0131nan gecikme ge\u00e7mi\u015fi.")
        chart_subtitle.setObjectName("telemetrySubtitle")
        chart_subtitle.setWordWrap(True)
        chart_layout.addWidget(chart_subtitle)
        self._latency_chart = _LatencyChart()
        chart_layout.addWidget(self._latency_chart, 1)
        chart_footer = QLabel("Paket kayb\u0131: API verisi yok  |  TLS ba\u011flant\u0131 durumu sunucu durumuna ba\u011fl\u0131d\u0131r")
        chart_footer.setObjectName("statusLabel")
        chart_footer.setWordWrap(True)
        chart_layout.addWidget(chart_footer)
        chart_panel.setMinimumWidth(0)

        event_panel = QFrame()
        event_panel.setObjectName("statusPanel")
        event_layout = QVBoxLayout(event_panel)
        event_layout.setContentsMargins(14, 12, 14, 12)
        event_heading = QHBoxLayout()
        event_title = QLabel("Anl\u0131k Olay Terminali")
        event_title.setObjectName("telemetryTitle")
        event_heading.addWidget(event_title, 1)
        clear_events = QPushButton("Clear")
        clear_events.setObjectName("liveFilter")
        clear_events.clicked.connect(self._clear_events)
        event_heading.addWidget(clear_events)
        event_layout.addLayout(event_heading)
        self._event_feed = QListWidget()
        self._event_feed.setObjectName("eventFeed")
        event_layout.addWidget(self._event_feed, 1)
        self._event_daemon = QLabel("Canl\u0131 telemetri ak\u0131\u015f\u0131")
        self._event_daemon.setObjectName("statusLabel")
        event_layout.addWidget(self._event_daemon)
        self._telemetry_panels = (chart_panel, event_panel)
        root.addLayout(telemetry_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)
        self._set_metric_columns()
        self._set_telemetry_columns()

    def _refresh(self):
        if self._thread and self._thread.isRunning():
            return
        self._thread = _FetchStatus()
        self._thread.done.connect(self._populate)
        self._thread.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._thread.start()

    def _populate(self, companies: list):
        scroll_position = self._scroll.verticalScrollBar().value()
        while self._grid_lay.count():
            item = self._grid_lay.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        online = sum(1 for c in companies if c.get("online"))
        slow_count = sum(1 for company in companies if self._is_slow(company))
        total = len(companies)
        ping_values = []
        for company in companies:
            ping = company.get("ping_ms", company.get("latency_ms", company.get("ping")))
            try:
                if company.get("online") and ping is not None:
                    ping_values.append(float(ping))
            except (TypeError, ValueError):
                continue
        reported_average = next((company.get("average_ping_ms") for company in companies if company.get("average_ping_ms") is not None), None)
        try:
            avg_ping = round(float(reported_average)) if reported_average is not None else round(sum(ping_values) / len(ping_values)) if ping_values else None
        except (TypeError, ValueError):
            avg_ping = round(sum(ping_values) / len(ping_values)) if ping_values else None
        queue_values = [c.get("unsynced_queue", c.get("pending_packets", c.get("queue_count"))) for c in companies]
        known_queues = []
        for value in queue_values:
            try:
                if value is not None:
                    known_queues.append(int(value or 0))
            except (TypeError, ValueError):
                continue
        traffic = next((c.get("data_rate", c.get("bytes_per_second")) for c in companies if c.get("data_rate", c.get("bytes_per_second")) is not None), None)
        if traffic is not None and not any(c.get("data_rate") is not None for c in companies):
            try:
                traffic = round(float(traffic) / 1048576, 2)
            except (TypeError, ValueError):
                traffic = None
        self._metric_widgets[0].setText(f"{online} / {total} Online")
        self._metric_widgets[1].setText(f"{avg_ping} ms" if avg_ping is not None else "-- ms")
        self._metric_widgets[2].setText(f"{traffic} MB/s" if traffic is not None else "-- MB/s")
        self._metric_widgets[3].setText(f"{sum(known_queues)} Paket" if known_queues else "N/A")
        details = (
            f"{round(online * 100 / total) if total else 0}% canlilik indeksi" if total else "Firma verisi yok",
            "Olculen ag gecikmesi" if avg_ping is not None else "Ping telemetrisi API verisi yok",
            "Anlik veri akisi" if traffic is not None else "Veri ak\u0131\u015f\u0131 API verisi yok",
            "T\u00fcm firmalar senkron" if known_queues and sum(known_queues) == 0 else "Kuyruk telemetrisi API verisi yok" if not known_queues else "Bekleyen senkron kayitlari",
        )
        for label, text in zip(self._metric_detail_widgets, details):
            label.setText(text)
        if avg_ping is not None:
            self._latency_history.append(avg_ping)
            self._latency_history = self._latency_history[-360:]
            self._latency_chart.set_values(self._latency_history)
        self._record_events(companies)
        self._counter.setText(f"CANLI AKI\u015e (5sn)  OTOMAT\u0130K  |  {online} / {total} ONLINE")
        self._companies = list(companies)
        self._company_widgets = []

        # Online olanlar once
        sorted_companies = sorted(companies, key=lambda c: (0 if c.get("online") else 1, c.get("company_name", "")))

        for index, company in enumerate(sorted_companies):
            card = _status_card(company, self.navigate_requested.emit, self._refresh)
            self._company_widgets.append((company, card))
        self._layout_fleet_cards()
        for key, button in self._filter_buttons.items():
            count = total if key == "all" else online - slow_count if key == "online" else total - online if key == "offline" else slow_count
            button.setText({"all": "Tum Firmalar", "online": "Sorunsuz", "slow": "Yuksek Gecikme", "offline": "Cevrimdisi"}[key] + f"  {count}")
        self._apply_filter()
        self._status_lbl.setText("")
        QTimer.singleShot(
            0,
            lambda position=scroll_position: self._scroll.verticalScrollBar().setValue(
                min(position, self._scroll.verticalScrollBar().maximum())
            ),
        )

    def _set_filter(self, value: str):
        self._active_filter = value
        for key, button in self._filter_buttons.items():
            button.setProperty("active", key == value)
            button.style().unpolish(button)
            button.style().polish(button)
        self._apply_filter()

    def _apply_filter(self):
        query = self._search.text().strip().casefold()
        visible = 0
        for company, card in getattr(self, "_company_widgets", []):
            status = bool(company.get("online"))
            active_filter = getattr(self, "_active_filter", "all")
            match_filter = active_filter == "all" or (active_filter == "online" and status and not self._is_slow(company)) or (active_filter == "offline" and not status) or (active_filter == "slow" and self._is_slow(company))
            searchable = " ".join(str(company.get(key, "")) for key in ("company_name", "id", "ip", "ip_address", "hardware_id", "terminal_id"))
            match_text = not query or query in searchable.casefold()
            card.setVisible(match_filter and match_text)
            visible += int(match_filter and match_text)
        self._status_lbl.setText(f"{visible} / {len(getattr(self, '_companies', []))} firma gosteriliyor")

    @staticmethod
    def _is_slow(company):
        if not company.get("online"):
            return False
        value = company.get("display_ping_ms", company.get("ping_ms", company.get("latency_ms", company.get("ping"))))
        try:
            return float(value) >= 50
        except (TypeError, ValueError):
            return str(company.get("health") or "").casefold() in {"slow", "degraded", "yuksek gecikme"}

    def _record_events(self, companies):
        now = datetime.now().strftime("%H:%M:%S")
        for company in companies:
            name = str(company.get("company_name") or company.get("id") or "Tenant")
            key = str(company.get("id") or name)
            latency = company.get("ping_ms", company.get("latency_ms", company.get("ping")))
            try:
                latency_band = int(float(latency) // 10) if latency is not None else None
            except (TypeError, ValueError):
                latency_band = None
            try:
                queued = int(company.get("unsynced_queue", company.get("pending_packets", company.get("queue_count", 0))) or 0)
            except (TypeError, ValueError):
                queued = 0
            fingerprint = (bool(company.get("online")), latency_band, queued)
            if self._event_fingerprints.get(key) == fingerprint:
                continue
            self._event_fingerprints[key] = fingerprint
            status = "online" if company.get("online") else "offline"
            message = f"{name}: {status} heartbeat"
            if latency is not None:
                message += f" ({latency} ms ping)"
            if fingerprint[2]:
                message += f"; {fingerprint[2]} queued packets"
            color = "#ffb4ab" if not company.get("online") else "#4cd7f6" if self._is_slow(company) else "#4edea3"
            self._events.insert(0, (now, message, color))
        self._events = self._events[:50]
        self._render_events()

    def _render_events(self):
        self._event_feed.clear()
        for timestamp, message, color in self._events:
            item = QListWidgetItem(f"{timestamp}  {message}")
            item.setForeground(QColor(color))
            self._event_feed.addItem(item)
        self._event_daemon.setText(f"Telemetry changes: {len(self._events)}")

    def _clear_events(self):
        self._events.clear()
        self._render_events()

    def _set_metric_columns(self):
        columns = 4 if self.width() >= 1150 else 2 if self.width() >= 520 else 1
        if not hasattr(self, "_metric_panels"):
            return
        for panel in self._metric_panels:
            self._metrics_layout.removeWidget(panel)
        for index, panel in enumerate(self._metric_panels):
            self._metrics_layout.addWidget(panel, index // columns, index % columns)

    def _set_telemetry_columns(self):
        if not hasattr(self, "_telemetry_grid"):
            return
        while self._telemetry_grid.count():
            self._telemetry_grid.takeAt(0)
        for column in range(3):
            self._telemetry_grid.setColumnMinimumWidth(column, 0)
            self._telemetry_grid.setColumnStretch(column, 0)
        if self.width() >= 1000:
            self._telemetry_grid.addWidget(self._telemetry_panels[0], 0, 0, 1, 2)
            self._telemetry_grid.addWidget(self._telemetry_panels[1], 0, 2)
            self._telemetry_grid.setColumnStretch(0, 1)
            self._telemetry_grid.setColumnStretch(2, 1)
        else:
            self._telemetry_grid.addWidget(self._telemetry_panels[0], 0, 0)
            self._telemetry_grid.addWidget(self._telemetry_panels[1], 1, 0)
            self._telemetry_grid.setColumnStretch(0, 1)

    def _layout_fleet_cards(self, available_width=None):
        if not hasattr(self, "_grid_lay"):
            return
        while self._grid_lay.count():
            self._grid_lay.takeAt(0)
        width = self.width() if available_width is None else int(available_width)
        columns = 2 if width >= 760 else 1
        detail_columns = 4 if width >= 760 else 2
        for column in range(4):
            self._grid_lay.setColumnMinimumWidth(column, 0)
            self._grid_lay.setColumnStretch(column, int(column < columns))
        for index, (_, card) in enumerate(getattr(self, "_company_widgets", [])):
            self._grid_lay.addWidget(card, index // columns, index % columns)
            telemetry = card._telemetry_layout
            while telemetry.count():
                telemetry.takeAt(0)
            for column in range(4):
                telemetry.setColumnMinimumWidth(column, 0)
                telemetry.setColumnStretch(column, int(column < detail_columns))
            for item, (label, value) in enumerate(card._telemetry_pairs):
                row, column = divmod(item, detail_columns)
                telemetry.addWidget(label, row * 2, column)
                telemetry.addWidget(value, row * 2 + 1, column)
            actions = card._action_layout
            while actions.count():
                actions.takeAt(0)
            action_columns = 3 if width >= 760 else 2
            for action_index, button in enumerate(card._action_buttons):
                actions.addWidget(button, action_index // action_columns, action_index % action_columns)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < 760
        self._page_scroll.widget().layout().setContentsMargins(16, 8, 16, 16) if compact else self._page_scroll.widget().layout().setContentsMargins(40, 8, 16, 16)
        self._header.setMinimumHeight(270 if compact else 118)
        self._header_layout.setStretchFactor(self._title_column, 0 if compact else 1)
        self._action_column.setContentsMargins(0, 30 if compact else 0, 0, 0)
        if compact != self._mobile_actions_active:
            if compact:
                self._status_action_row.removeWidget(self._refresh_button)
                self._action_column.removeWidget(self._broadcast_button)
                self._mobile_action_buttons.addWidget(self._refresh_button, 1)
                self._mobile_action_buttons.addWidget(self._broadcast_button, 1)
                self._action_column.insertLayout(1, self._mobile_action_buttons)
            else:
                self._mobile_action_buttons.removeWidget(self._refresh_button)
                self._mobile_action_buttons.removeWidget(self._broadcast_button)
                self._status_action_row.addWidget(self._refresh_button)
                self._action_column.removeItem(self._mobile_action_buttons)
                self._action_column.addWidget(self._broadcast_button, 0, Qt.AlignmentFlag.AlignLeft)
            self._mobile_actions_active = compact
        if compact:
            self._action_column.setContentsMargins(0, 2, 0, 0)
            self._subtitle.setStyleSheet("font-size: 14px;")
        else:
            self._subtitle.setStyleSheet("")
        for panel in self._metric_panels:
            panel.setMinimumHeight(0 if compact else 112)
        for _, card in getattr(self, "_company_widgets", []):
            card.setMinimumHeight(0 if compact else 314)
        self._header_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        )
        while self._filter_layout.count():
            self._filter_layout.takeAt(0)
        if compact:
            for index, button in enumerate(self._filter_buttons.values()):
                self._filter_layout.addWidget(button, index // 2, index % 2)
            self._filter_layout.addWidget(self._search, 2, 0, 1, 2)
            self._filter_layout.setColumnStretch(0, 1)
            self._filter_layout.setColumnStretch(1, 1)
        else:
            for index, button in enumerate(self._filter_buttons.values()):
                self._filter_layout.addWidget(button, 0, index)
            self._filter_layout.addWidget(self._search, 0, 4)
            self._filter_layout.setColumnStretch(4, 1)
        self._set_metric_columns()
        self._layout_fleet_cards(self._page_scroll.viewport().width())
        self._set_telemetry_columns()
        QTimer.singleShot(
            0,
            lambda: self._layout_fleet_cards(max(1, self._page_scroll.viewport().width())),
        )

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
