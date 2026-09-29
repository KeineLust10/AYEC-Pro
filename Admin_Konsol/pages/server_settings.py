"""
AYEC Pro Admin Konsol - Sunucu Durumu & Ayarlar
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QFormLayout, QGroupBox, QProgressBar,
    QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
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
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(24)

        title_row = QHBoxLayout()
        title = QLabel("\u2699\ufe0f Sunucu Yonetimi")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        refresh = QPushButton("\u21bb Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._refresh_status)
        title_row.addWidget(refresh)
        root.addLayout(title_row)

        # Sistem metrikleri
        metrics_group = QGroupBox("Sunucu Kaynaklar\u0131")
        metrics_group.setObjectName("groupBox")
        metrics_lay = QVBoxLayout(metrics_group)
        metrics_lay.setSpacing(12)

        def _bar_row(label: str) -> tuple:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("metricTitle")
            lbl.setFixedWidth(120)
            row.addWidget(lbl)
            bar = QProgressBar()
            bar.setObjectName("metricBar")
            bar.setRange(0, 100)
            bar.setFixedHeight(18)
            row.addWidget(bar, 1)
            val_lbl = QLabel("...")
            val_lbl.setObjectName("metricSub")
            val_lbl.setFixedWidth(80)
            row.addWidget(val_lbl)
            metrics_lay.addLayout(row)
            return bar, val_lbl

        self._cpu_bar, self._cpu_lbl = _bar_row("CPU")
        self._ram_bar, self._ram_lbl = _bar_row("RAM")
        self._disk_bar, self._disk_lbl = _bar_row("Disk")
        root.addWidget(metrics_group)

        # Ayarlar bolumu (iki sutun)
        settings_row = QHBoxLayout()
        settings_row.setSpacing(24)

        # Konsol baglanti ayarlari
        conn_group = QGroupBox("Konsol Baglanti Ayarlari")
        conn_group.setObjectName("groupBox")
        conn_lay = QFormLayout(conn_group)
        self._srv_url = QLineEdit(config.server_url())
        self._srv_url.setObjectName("fieldInput")
        conn_lay.addRow("Sunucu URL:", self._srv_url)
        self._timeout_input = QLineEdit(str(config.timeout()))
        self._timeout_input.setObjectName("fieldInput")
        conn_lay.addRow("Zaman Asimi (sn):", self._timeout_input)
        save_conn = QPushButton("Kaydet")
        save_conn.setObjectName("primaryBtn")
        save_conn.clicked.connect(self._save_conn)
        conn_lay.addRow("", save_conn)
        settings_row.addWidget(conn_group)

        # Sunucu bilgisi
        info_group = QGroupBox("Sunucu Bilgisi")
        info_group.setObjectName("groupBox")
        info_lay = QFormLayout(info_group)
        self._srv_version = QLabel("...")
        self._srv_version.setObjectName("infoVal")
        info_lay.addRow("Surum:", self._srv_version)
        self._srv_uptime = QLabel("...")
        self._srv_uptime.setObjectName("infoVal")
        info_lay.addRow("Calisma Suresi:", self._srv_uptime)
        self._srv_db = QLabel("...")
        self._srv_db.setObjectName("infoVal")
        info_lay.addRow("Veritabani:", self._srv_db)
        self._srv_tenants = QLabel("...")
        self._srv_tenants.setObjectName("infoVal")
        info_lay.addRow("Kayitli Firma:", self._srv_tenants)
        settings_row.addWidget(info_group)
        root.addLayout(settings_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)
        root.addStretch()

    def _refresh_status(self):
        if self._thread and self._thread.isRunning():
            return
        self._thread = _FetchServer()
        self._thread.done.connect(self._populate)
        self._thread.error.connect(lambda e: self._status_lbl.setText(f"Sunucu baglanamadi: {e}"))
        self._thread.start()

    def _populate(self, data: dict):
        self._status_lbl.setText("")
        cpu = int(data.get("cpu_percent", 0))
        ram = int(data.get("ram_percent", 0))
        disk = int(data.get("disk_percent", 0))

        self._cpu_bar.setValue(cpu)
        self._cpu_lbl.setText(f"%{cpu}")
        self._cpu_bar.setStyleSheet("QProgressBar::chunk { background: #7c6af7; }" if cpu < 80 else "QProgressBar::chunk { background: #f87171; }")

        self._ram_bar.setValue(ram)
        self._ram_lbl.setText(f"%{ram}")
        self._ram_bar.setStyleSheet("QProgressBar::chunk { background: #10b981; }" if ram < 80 else "QProgressBar::chunk { background: #f59e0b; }")

        self._disk_bar.setValue(disk)
        self._disk_lbl.setText(data.get("disk_usage", f"%{disk}"))
        self._disk_bar.setStyleSheet("QProgressBar::chunk { background: #60a5fa; }" if disk < 85 else "QProgressBar::chunk { background: #f87171; }")

        self._srv_version.setText(data.get("version", "-"))
        self._srv_uptime.setText(data.get("uptime", "-"))
        self._srv_db.setText(data.get("db_path", "-"))
        self._srv_tenants.setText(str(data.get("tenant_count", "-")))

    def _save_conn(self):
        url = config.normalize_server_url(self._srv_url.text())
        timeout = self._timeout_input.text().strip()
        if not url:
            self._status_lbl.setText("URL bos olamaz.")
            return
        self._srv_url.setText(url)
        config.set("server_url", url)
        try:
            config.set("timeout", int(timeout))
        except ValueError:
            pass
        self._status_lbl.setText("\u2705 Baglanti ayarlari kaydedildi.")

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
