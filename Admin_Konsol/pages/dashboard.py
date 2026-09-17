"""
AYEC Pro Admin Konsol - Dashboard Sayfasi
Sunucu istatistikleri, firma ozeti, sistem sagli\u011fi.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
import api_client


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

    def run(self):
        try:
            self.done.emit(api_client.dashboard())
        except Exception as exc:
            self.error.emit(str(exc))


def _metric_card(title: str, value: str, sub: str, color: str = "#7c6af7") -> QFrame:
    card = QFrame()
    card.setObjectName("metricCard")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(20, 18, 20, 18)

    t = QLabel(title)
    t.setObjectName("metricTitle")
    lay.addWidget(t)

    v = QLabel(value)
    v.setObjectName("metricValue")
    v.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 900;")
    lay.addWidget(v)

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
    def __init__(self):
        super().__init__()
        self._thread: _FetchThread | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._build_ui()
        self._refresh()
        self._timer.start(30_000)  # 30 sn auto yenile

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(24)

        # Baslik
        title_row = QHBoxLayout()
        title_lbl = QLabel("\ud83d\udcca Ana Dashboard")
        title_lbl.setObjectName("pageTitle")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        refresh_btn = QPushButton("\u21bb Yenile")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._refresh)
        title_row.addWidget(refresh_btn)
        root.addLayout(title_row)

        # Metrik kartlar
        self._metric_grid = QGridLayout()
        self._metric_grid.setSpacing(16)
        root.addLayout(self._metric_grid)

        # Log bolumu
        log_lbl = QLabel("Son \u0130\u015flemler")
        log_lbl.setObjectName("sectionTitle")
        root.addWidget(log_lbl)

        self._log_frame = QFrame()
        self._log_frame.setObjectName("logFrame")
        self._log_layout = QVBoxLayout(self._log_frame)
        self._log_layout.setContentsMargins(0, 0, 0, 0)
        self._log_layout.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._log_frame)
        scroll.setObjectName("logScroll")
        root.addWidget(scroll, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

    def _refresh(self):
        if self._thread and self._thread.isRunning():
            return
        self._status_lbl.setText("Veriler y\u00fckleniyor...")
        self._thread = _FetchThread()
        self._thread.done.connect(self._populate)
        self._thread.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        self._thread.start()

    def _populate(self, data: dict):
        self._status_lbl.setText("")

        # Metrikleri temizle
        for i in reversed(range(self._metric_grid.count())):
            w = self._metric_grid.itemAt(i).widget()
            if w:
                w.deleteLater()

        metrics = [
            ("Toplam Firma", str(data.get("total_companies", 0)), "Kayitli", "#7c6af7"),
            ("Aktif Firma", str(data.get("active_companies", 0)), "Lisans gecerli", "#10b981"),
            ("Pasif Firma", str(data.get("inactive_companies", 0)), "Lisans suresi doldu", "#f87171"),
            ("Online Kullanici", str(data.get("online_users", 0)), "Simdi bagli", "#60a5fa"),
            ("Bugun Giris", str(data.get("logins_today", 0)), "Son 24 saat", "#f59e0b"),
            ("Disk Kullanimi", data.get("disk_usage", "?"), "Sunucu diski", "#ec4899"),
            (
                "Yedek Kapsami",
                f"{data.get('backup_coverage', 0)}/{data.get('total_companies', 0)}",
                "Yedegi bulunan firma",
                "#14b8a6",
            ),
            (
                "Bekleyen Komut",
                str(data.get("pending_commands", 0)),
                "Istemci teslimati bekliyor",
                "#f59e0b",
            ),
            (
                "Basarisiz Komut",
                str(data.get("failed_commands", 0)),
                "Mudahale gerekli",
                "#f87171",
            ),
            (
                "Lisans Uyarisi",
                str(data.get("expiring_licenses", 0)),
                "30 gun icinde bitecek",
                "#fb923c",
            ),
        ]

        for idx, (title, value, sub, color) in enumerate(metrics):
            card = _metric_card(title, value, sub, color)
            self._metric_grid.addWidget(card, idx // 4, idx % 4)

        # Loglari temizle ve doldur
        for i in reversed(range(self._log_layout.count())):
            w = self._log_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        logs = data.get("recent_logs", [])
        if not logs:
            empty = QLabel("Henuz islem logu yok.")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._log_layout.addWidget(empty)
        else:
            for entry in logs[:20]:
                self._log_layout.addWidget(_log_row(entry))
        self._log_layout.addStretch()

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
