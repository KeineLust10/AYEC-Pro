"""Admin server status and connection settings page."""

from PyQt6.QtCore import QThread, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import api_client
import config


class _FetchServer(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.server_status())
        except Exception as exc:
            self.error.emit(str(exc))


class ServerSettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread: _FetchServer | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._build_ui()
        self._refresh_status()
        self._timer.start(20_000)

    def _build_ui(self):
        self.setObjectName("serverSettingsPage")
        self.setStyleSheet(
            """
            QWidget#serverSettingsPage { background: #0e1321; color: #dee2f6; }
            QWidget#serverSettingsPage QLabel { background: transparent; }
            QScrollArea#serverSettingsScroll { border: 0; background: #0e1321; }
            QScrollArea#serverSettingsScroll > QWidget > QWidget { background: #0e1321; }
            QScrollBar:vertical { width: 8px; background: #0e1321; }
            QScrollBar::handle:vertical { min-height: 28px; background: #303444; border-radius: 4px; }
            QFrame#serverHero, QFrame#metricCard, QGroupBox#serverPanel {
                background: #161b2a; border: 1px solid #1e293b; border-radius: 4px;
            }
            QFrame#serverHero { background: #111827; }
            QLabel#serverEyebrow { color: #10b981; font: 700 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#serverTitle { color: #dee2f6; font: 700 20px "Segoe UI", Arial; }
            QLabel#serverDescription { color: #c2c6d6; font: 12px "Segoe UI", Arial; }
            QLabel#metricLabel { color: #c2c6d6; font: 700 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#metricValue { color: #dee2f6; font: 700 30px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#metricState, QLabel#serverMeta { color: #8c909f; font: 8px "JetBrains Mono", "Segoe UI", Arial; }
            QProgressBar#metricBar { background: #303444; border: 0; border-radius: 3px; min-height: 6px; max-height: 6px; text-align: center; }
            QProgressBar#metricBar::chunk { background: #4edea3; border-radius: 3px; }
            QProgressBar#metricBar[tone="ram"]::chunk { background: #4cd7f6; }
            QProgressBar#metricBar[tone="disk"]::chunk { background: #4d8eff; }
            QProgressBar#metricBar[tone="network"]::chunk { background: #4cd7f6; }
            QGroupBox#serverPanel { margin-top: 12px; padding: 14px 12px 12px; color: #adc6ff; font: 700 12px "Segoe UI", Arial; }
            QGroupBox#serverPanel::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            QLabel#fieldLabel { color: #c2c6d6; font: 700 8px "JetBrains Mono", "Segoe UI", Arial; }
            QLineEdit#fieldInput { min-height: 30px; padding: 5px 8px; color: #dee2f6; background: #090e1c; border: 1px solid #303444; border-radius: 4px; font: 9px "JetBrains Mono", "Segoe UI", Arial; }
            QLineEdit#fieldInput:focus { border-color: #4d8eff; }
            QLineEdit#fieldInput:read-only { color: #8c909f; }
            QPushButton { min-height: 32px; padding: 5px 9px; color: #dee2f6; background: #252a39; border: 1px solid #303444; border-radius: 4px; font: 9px "Segoe UI", Arial; }
            QPushButton#primaryBtn { color: #002e6a; background: #adc6ff; border-color: #adc6ff; font-weight: 700; }
            QPushButton#secondaryBtn { color: #dee2f6; background: #252a39; }
            QPushButton#primaryBtn:disabled, QPushButton:disabled { color: #8c909f; background: #252a39; border-color: #303444; }
            QLabel#infoValue { color: #dee2f6; font: 9px "JetBrains Mono", "Segoe UI", Arial; }
            QFrame#topologyNode, QFrame#topologyRow { background: #090e1c; border: 1px solid #1e293b; border-radius: 5px; }
            QLabel#topologyIcon { color: #adc6ff; font: 700 28px "Segoe UI", Arial; }
            QLabel#topologyValue { color: #dee2f6; font: 700 10px "JetBrains Mono", "Segoe UI", Arial; }
            QLabel#topologyState { color: #8c909f; font: 700 8px "JetBrains Mono", "Segoe UI", Arial; }
            QFrame#infoRow { border-bottom: 1px solid #252a39; }
            QPushButton#maintenanceAction { min-height: 48px; text-align: left; color: #8c909f; }
            QLabel#statusLabel { color: #4cd7f6; font: 9px "Segoe UI", Arial; }
            """
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._scroll = QScrollArea(self)
        self._scroll.setObjectName("serverSettingsScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 18)
        layout.setSpacing(12)
        self._page_layout = layout

        hero = QFrame()
        self._hero = hero
        hero.setObjectName("serverHero")
        hero_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, hero)
        hero_layout.setContentsMargins(14, 11, 14, 11)
        hero.setMinimumHeight(126)
        title_block = QVBoxLayout()
        eyebrow = QLabel("PLATFORM INFRASTRUCTURE / OPERATIONS")
        eyebrow.setObjectName("serverEyebrow")
        eyebrow.setWordWrap(True)
        eyebrow.setMinimumWidth(0)
        eyebrow.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title = QLabel("Sunucu Ayarlar\u0131 & Altyap\u0131 Telemetrisi")
        title.setObjectName("serverTitle")
        title.setWordWrap(True)
        title.setMinimumWidth(0)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        description = QLabel("Merkezi API kaynaklar\u0131n\u0131 izleyin; sunucu konfig\u00fcrasyonu yaln\u0131zca desteklenen ayarlardan de\u011fi\u015ftirilebilir.")
        description.setObjectName("serverDescription")
        description.setWordWrap(True)
        description.setMinimumWidth(0)
        description.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_block.addWidget(eyebrow)
        title_block.addWidget(title)
        title_block.addWidget(description)
        hero_layout.addLayout(title_block, 1)
        self._title_block = title_block
        self._hero_layout = hero_layout
        self._api_state = QLabel("API DURUMU: BEKLEN\u0130YOR")
        self._api_state.setObjectName("serverMeta")
        hero_layout.addWidget(self._api_state, 0, Qt.AlignmentFlag.AlignVCenter)
        self._refresh_button = QPushButton("Yeniden Y\u00fckle")
        self._refresh_button.setObjectName("secondaryBtn")
        self._refresh_button.clicked.connect(self._refresh_status)
        hero_layout.addWidget(self._refresh_button)
        restart = QPushButton("Servisleri Yeniden Ba\u015flat")
        self._restart_button = restart
        restart.setEnabled(False)
        restart.setToolTip("Restart API endpoint is not available.")
        hero_layout.addWidget(restart)
        layout.addWidget(hero)

        metric_grid = QGridLayout()
        metric_grid.setSpacing(10)
        self._metric_grid = metric_grid
        self._cpu_bar, self._cpu_lbl, self._cpu_state, cpu_card = self._metric_card("CPU", "cpu")
        self._ram_bar, self._ram_lbl, self._ram_state, ram_card = self._metric_card("RAM", "ram")
        self._disk_bar, self._disk_lbl, self._disk_state, disk_card = self._metric_card("NVME SSD DISK", "disk")
        self._database_bar, self._database_lbl, self._database_state, database_card = self._metric_card("VERITABANI BOYUTU", "database")
        self._network_bar, self._network_lbl, self._network_state, network_card = self._metric_card("AG ILETIMI", "network")
        self._metric_cards = [cpu_card, ram_card, disk_card, database_card, network_card]
        self._metric_columns = 0
        layout.addLayout(metric_grid)

        self._topology_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._topology_layout.setSpacing(12)
        self._infrastructure_panel = self._topology_panel(
            "Altyap\u0131 Donan\u0131m ve Topoloji Analizi", "infrastructure")
        self._replication_panel = self._topology_panel(
            "D\u00fc\u011f\u00fcm Replikasyonu", "replication")
        self._infrastructure_panel.setMinimumHeight(222)
        self._replication_panel.setMinimumHeight(222)
        self._topology_layout.addWidget(self._infrastructure_panel, 2)
        self._topology_layout.addWidget(self._replication_panel, 1)
        layout.addLayout(self._topology_layout)

        main_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        main_row.setSpacing(12)
        self._main_row = main_row
        connection = QGroupBox("Merkezi Konsol Ba\u011flant\u0131 Ayarlar\u0131")
        connection.setObjectName("serverPanel")
        connection.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._connection_panel = connection
        connection_layout = QVBoxLayout(connection)
        connection_layout.setSpacing(8)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        self._srv_url = QLineEdit(config.server_url())
        self._srv_url.setObjectName("fieldInput")
        self._srv_url.setMinimumWidth(0)
        self._srv_url.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self._timeout_input = QLineEdit(str(config.timeout()))
        self._timeout_input.setObjectName("fieldInput")
        self._timeout_input.setMinimumWidth(0)
        self._timeout_input.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        form.addRow(self._field_label("Sunucu URL (Ana D\u00fc\u011f\u00fcm)"), self._srv_url)
        form.addRow(self._field_label("Zaman A\u015f\u0131m\u0131 (sn)"), self._timeout_input)
        for label in ("Failover endpoint", "Heartbeat", "WebSocket port", "Master secret"):
            field = QLineEdit("API data unavailable" if label != "Master secret" else "Secret values are not exposed")
            field.setObjectName("fieldInput")
            field.setReadOnly(True)
            field.setMinimumWidth(0)
            field.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            field.setAccessibleName(label)
            form.addRow(self._field_label(label), field)
        connection_layout.addLayout(form)
        action_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._actions_layout = action_row
        action_row.addStretch()
        self._test_button = QPushButton("Ba\u011flant\u0131y\u0131 Test Et")
        self._test_button.setObjectName("secondaryBtn")
        self._test_button.clicked.connect(self._refresh_status)
        action_row.addWidget(self._test_button)
        self._save_button = QPushButton("Ba\u011flant\u0131 Ayarlar\u0131n\u0131 Kaydet")
        self._save_button.setObjectName("primaryBtn")
        self._save_button.clicked.connect(self._save_conn)
        action_row.addWidget(self._save_button)
        connection_layout.addLayout(action_row)
        main_row.addWidget(connection, 1)

        right_widget = QWidget()
        right_column = QVBoxLayout(right_widget)
        right_column.setSpacing(12)
        info = QGroupBox("Sistem ve \u00c7evre Durumu")
        info.setObjectName("serverPanel")
        self._info_panel = info
        info_layout = QVBoxLayout(info)
        info_layout.setSpacing(2)
        self._info_values = {}
        for key, label in (("version", "Servis S\u00fcr\u00fcm\u00fc"), ("uptime", "\u00c7al\u0131\u015fma S\u00fcresi"), ("tenant_count", "Aktif Tenant"), ("server_time", "Sunucu Zaman\u0131"), ("db_path", "Veritaban\u0131 Konumu")):
            row = QWidget()
            row.setObjectName("infoRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(1, 6, 1, 6)
            key_label = QLabel(label)
            key_label.setObjectName("serverMeta")
            value = QLabel("API verisi bekleniyor")
            value.setObjectName("infoValue")
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setWordWrap(True)
            value.setMinimumWidth(0)
            value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            row_layout.addWidget(key_label)
            row_layout.addWidget(value, 1, Qt.AlignmentFlag.AlignRight)
            info_layout.addWidget(row)
            self._info_values[key] = value
        self._srv_version = self._info_values["version"]
        self._srv_uptime = self._info_values["uptime"]
        self._srv_tenants = self._info_values["tenant_count"]
        self._srv_db = self._info_values["db_path"]
        info_actions = QHBoxLayout()
        info_actions.addStretch()
        copy = QPushButton("Durum Bilgisini Kopyala")
        copy.setObjectName("secondaryBtn")
        copy.clicked.connect(self._copy_status)
        info_actions.addWidget(copy)
        info_layout.addLayout(info_actions)
        right_column.addWidget(info)

        maintenance = QGroupBox("H\u0131zl\u0131 Sunucu Bak\u0131m Komutlar\u0131")
        maintenance.setObjectName("serverPanel")
        self._maintenance_panel = maintenance
        maintenance_layout = QVBoxLayout(maintenance)
        maintenance_layout.setSpacing(5)
        self._maintenance_buttons = []
        for title_text, detail in (
            ("SQLite VACUUM & Optimize", "Database maintenance API is unavailable."),
            ("WebSocket Istemcilerini Yenile", "Active socket management API is unavailable."),
            ("Onbellegi Temizle", "Cache status and clearing API are unavailable."),
            ("Sunucu Loglarini Disari Aktar", "Log archive API is unavailable."),
        ):
            item = QWidget()
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 4)
            item_layout.setSpacing(1)
            button = QPushButton(title_text)
            button.setObjectName("maintenanceAction")
            button.setEnabled(False)
            button.setMinimumWidth(0)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            button.setToolTip(detail)
            detail_label = QLabel(detail)
            detail_label.setObjectName("serverMeta")
            detail_label.setWordWrap(True)
            self._maintenance_buttons.append(button)
            item_layout.addWidget(button)
            item_layout.addWidget(detail_label)
            maintenance_layout.addWidget(item)
        right_column.addWidget(maintenance)
        right_column.addStretch(1)
        main_row.addWidget(right_widget, 1)
        layout.addLayout(main_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        self._status_lbl.setWordWrap(True)
        layout.addWidget(self._status_lbl)
        layout.addStretch(1)
        self._scroll.setWidget(content)
        root.addWidget(self._scroll, 1)
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        compact = self.width() < 900
        mobile = self.width() < 760
        self._page_layout.setSpacing(20 if mobile else 12)
        self._page_layout.setContentsMargins(20, 20 if mobile else 16, 20, 18)
        self._hero.setMinimumHeight(344 if mobile else 126)
        self._hero_layout.setStretchFactor(self._title_block, 0 if mobile else 1)
        self._hero_layout.setSpacing(12 if mobile else 14)
        for card in self._metric_cards:
            card.setMinimumHeight(136 if mobile else 186)
        if mobile:
            self._refresh_button.setFixedHeight(32)
            self._restart_button.setFixedHeight(32)
        else:
            self._refresh_button.setMinimumHeight(32)
            self._refresh_button.setMaximumHeight(16777215)
            self._restart_button.setMinimumHeight(32)
            self._restart_button.setMaximumHeight(16777215)
        direction = QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight
        self._main_row.setDirection(direction)
        hero_direction = QBoxLayout.Direction.TopToBottom if self.width() < 760 else QBoxLayout.Direction.LeftToRight
        self._hero_layout.setDirection(hero_direction)
        self._topology_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        if hasattr(self, "_actions_layout"):
            self._actions_layout.setDirection(QBoxLayout.Direction.TopToBottom if compact else QBoxLayout.Direction.LeftToRight)
        columns = 1 if self.width() < 760 else (3 if compact else 5)
        if columns != self._metric_columns:
            for card in self._metric_cards:
                self._metric_grid.removeWidget(card)
            for index, card in enumerate(self._metric_cards):
                self._metric_grid.addWidget(card, index // columns, index % columns)
            self._metric_columns = columns
        for column in range(5):
            self._metric_grid.setColumnStretch(column, 1 if column < columns else 0)
        for panel in (self._connection_panel, self._info_panel, self._maintenance_panel, self._infrastructure_panel, self._replication_panel):
            panel.setMinimumWidth(0)
            panel.setSizePolicy(QSizePolicy.Policy.Ignored if compact else QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_layout()

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        return label

    def _placeholder_panel(self, title: str, detail: str, state: str) -> QGroupBox:
        panel = QGroupBox(title)
        panel.setObjectName("serverPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body = QVBoxLayout(panel)
        body.setSpacing(8)
        detail_label = QLabel(detail)
        detail_label.setObjectName("serverMeta")
        detail_label.setWordWrap(True)
        state_label = QLabel(state)
        state_label.setObjectName("infoValue")
        state_label.setWordWrap(True)
        body.addWidget(detail_label)
        body.addWidget(state_label)
        return panel

    def _topology_panel(self, title: str, kind: str) -> QGroupBox:
        panel = QGroupBox(title)
        panel.setObjectName("serverPanel")
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        body = QVBoxLayout(panel)
        body.setSpacing(10)
        if kind == "infrastructure":
            row = QHBoxLayout()
            node = QFrame()
            node.setObjectName("topologyNode")
            node.setMinimumSize(180, 132)
            node.setMaximumWidth(224)
            node_layout = QVBoxLayout(node)
            node_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon = QLabel("[+] ")
            icon.setObjectName("topologyIcon")
            icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            node_name = QLabel("ANA D\u00dc\u011e\u00dcM")
            node_name.setObjectName("topologyValue")
            node_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            node_state = QLabel("API VER\u0130S\u0130 YOK")
            node_state.setObjectName("topologyState")
            node_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            node_layout.addWidget(icon)
            node_layout.addWidget(node_name)
            node_layout.addWidget(node_state)
            row.addWidget(node)
            content = QVBoxLayout()
            description = QLabel("Donan\u0131m ve uplink ayr\u0131nt\u0131lar\u0131 sunucu durum API'sinde bulunmuyor.")
            description.setObjectName("serverDescription")
            description.setWordWrap(True)
            content.addWidget(description)
            status = QLabel("Topoloji sa\u011fl\u0131\u011f\u0131 do\u011frulanam\u0131yor")
            status.setObjectName("serverMeta")
            content.addWidget(status)
            content.addStretch(1)
            row.addLayout(content, 1)
            body.addLayout(row, 1)
            metrics = QHBoxLayout()
            for label in ("UPLINK", "SOCKET", "KULLANILAB\u0130L\u0130RL\u0130K"):
                metric = QVBoxLayout()
                caption = QLabel(label)
                caption.setObjectName("topologyState")
                value = QLabel("API verisi yok")
                value.setObjectName("topologyValue")
                metric.addWidget(caption)
                metric.addWidget(value)
                metrics.addLayout(metric, 1)
            body.addLayout(metrics)
        else:
            for title_text in ("Ana d\u00fc\u011f\u00fcm", "Yedek d\u00fc\u011f\u00fcm"):
                row = QFrame()
                row.setObjectName("topologyRow")
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(10, 8, 10, 8)
                name = QLabel(title_text)
                name.setObjectName("topologyValue")
                value = QLabel("API verisi yok")
                value.setObjectName("topologyState")
                row_layout.addWidget(name)
                row_layout.addStretch(1)
                row_layout.addWidget(value)
                body.addWidget(row)
            body.addStretch(1)
            detail = QLabel("Birincil ve yedek d\u00fc\u011f\u00fcm durumlar\u0131 sunucu durum API'sinde bulunmuyor.")
            detail.setObjectName("serverMeta")
            detail.setWordWrap(True)
            body.addWidget(detail)
        return panel

    def _metric_card(self, title: str, tone: str) -> tuple:
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(186)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        label = QLabel(title)
        label.setObjectName("metricLabel")
        label.setWordWrap(True)
        value = QLabel("...")
        value.setObjectName("metricValue")
        value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        bar = QProgressBar()
        bar.setObjectName("metricBar")
        bar.setProperty("tone", tone)
        bar.setRange(0, 100)
        bar.setTextVisible(False)
        state = QLabel("Veri bekleniyor")
        state.setObjectName("metricState")
        layout.addWidget(label)
        layout.addWidget(value)
        layout.addWidget(bar)
        layout.addWidget(state)
        return bar, value, state, card

    def _refresh_status(self):
        if self._thread and self._thread.isRunning():
            return
        self._refresh_button.setEnabled(False)
        self._thread = _FetchServer()
        self._thread.done.connect(self._populate)
        self._thread.error.connect(self._show_error)
        self._thread.finished.connect(lambda: self._refresh_button.setEnabled(True))
        self._thread.start()

    def _show_error(self, message: str):
        self._api_state.setText("API DURUMU: HATA")
        self._status_lbl.setText(f"Sunucuya ba\u011flan\u0131lamad\u0131: {message}")

    def _populate(self, data: dict):
        self._status_lbl.setText("")
        self._api_state.setText("API DURUMU: AKT\u0130F")
        metrics = (
            ("cpu_percent", self._cpu_bar, self._cpu_lbl, self._cpu_state, 80),
            ("ram_percent", self._ram_bar, self._ram_lbl, self._ram_state, 80),
            ("disk_percent", self._disk_bar, self._disk_lbl, self._disk_state, 85),
        )
        for key, bar, label, state, threshold in metrics:
            raw_value = data.get(key)
            if raw_value is None:
                bar.setValue(0)
                label.setText("Veri yok")
                state.setText("API yaniti yok")
                continue
            value = max(0, min(100, int(float(raw_value))))
            bar.setValue(value)
            label.setText(f"{value}%")
            bar.setToolTip("Normal" if value < threshold else "Y\u00fcksek kullan\u0131m")
            state.setText("Normal" if value < threshold else "Y\u00fcksek kullan\u0131m")
        self._disk_lbl.setText(str(data.get("disk_usage") or (f"{data['disk_percent']}%" if data.get("disk_percent") is not None else "Veri yok")))
        database_size = data.get("database_size_bytes")
        if database_size is None:
            self._database_lbl.setText("Veri yok")
            self._database_state.setText("API yaniti yok")
            self._database_bar.setValue(0)
            self._database_bar.hide()
        else:
            size = max(0, float(database_size))
            unit = "GB" if size >= 1024 ** 3 else "MB"
            amount = size / (1024 ** 3 if unit == "GB" else 1024 ** 2)
            self._database_lbl.setText(f"{amount:.2f} {unit}")
            database_percent = data.get("database_percent")
            self._database_bar.setVisible(database_percent is not None)
            self._database_bar.setValue(max(0, min(100, int(float(database_percent or 0)))))
            self._database_state.setText(f"{int(float(database_percent))}% dolu" if database_percent is not None else "Kullanim limiti sunulmuyor")
        network_speed = data.get("network_mbps")
        if network_speed is None:
            self._network_lbl.setText("Veri yok")
            self._network_state.setText("API yaniti yok")
            self._network_bar.setValue(0)
            self._network_bar.hide()
        else:
            self._network_lbl.setText(f"{float(network_speed) / 8:.2f} MB/s")
            network_percent = data.get("network_percent")
            self._network_bar.setVisible(network_percent is not None)
            self._network_bar.setValue(max(0, min(100, int(float(network_percent or 0)))))
            self._network_state.setText("Ag trafigi" if network_percent is not None else "Anlik aktarim hizi")
        values = {
            "version": data.get("version") or "Veri yok",
            "uptime": data.get("uptime") or "Veri yok",
            "tenant_count": data.get("tenant_count", "Veri yok"),
            "server_time": data.get("server_time") or "Veri yok",
            "db_path": data.get("db_path") or "Veri yok",
        }
        for key, value in values.items():
            self._info_values[key].setText(str(value))

    def _copy_status(self):
        values = [f"{key}: {label.text()}" for key, label in self._info_values.items()]
        QApplication.clipboard().setText("\n".join(values))
        self._status_lbl.setText("Durum bilgisi panoya kopyaland\u0131.")

    def _save_conn(self):
        url = config.normalize_server_url(self._srv_url.text())
        if not url:
            self._status_lbl.setText("URL bo\u015f olamaz.")
            return False
        try:
            timeout = int(self._timeout_input.text().strip())
            if not 1 <= timeout <= 300:
                raise ValueError
        except ValueError:
            self._status_lbl.setText("Zaman a\u015f\u0131m\u0131 1 ile 300 saniye aras\u0131nda olmal\u0131d\u0131r.")
            return False
        self._srv_url.setText(url)
        config.set("server_url", url)
        config.set("timeout", timeout)
        self._status_lbl.setText("Ba\u011flant\u0131 ayarlar\u0131 kaydedildi.")
        return True

    def closeEvent(self, event):
        self._timer.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        super().closeEvent(event)
