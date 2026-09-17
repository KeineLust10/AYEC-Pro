"""
AYEC Pro Admin Konsol - Canli Firma Durumu
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import api_client


class _FetchStatus(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.live_status())
        except Exception as exc:
            self.error.emit(str(exc))


def _status_card(company: dict) -> QFrame:
    card = QFrame()
    card.setObjectName("statusCard")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(6)

    online = company.get("online", False)
    dot = "\ud83d\udfe2" if online else "\ud83d\udd34"
    status_txt = "Online" if online else "Offline"

    name = QLabel(f"{dot}  {company.get('company_name', '?')}")
    name.setObjectName("cardName")
    lay.addWidget(name)

    status_lbl = QLabel(status_txt)
    status_lbl.setObjectName("cardStatus")
    status_lbl.setStyleSheet(f"color: {'#10b981' if online else '#f87171'};")
    lay.addWidget(status_lbl)

    users = company.get("active_users", 0)
    if online and users:
        usr_lbl = QLabel(f"\ud83d\udc65 {users} aktif kullanici")
        usr_lbl.setObjectName("cardDetail")
        lay.addWidget(usr_lbl)

    last = company.get("last_seen", "")
    if last:
        last_lbl = QLabel(f"\u23f1\ufe0f Son: {last}")
        last_lbl.setObjectName("cardDetail")
        lay.addWidget(last_lbl)

    return card


class LiveStatusPage(QWidget):
    def __init__(self):
        super().__init__()
        self._thread: _FetchStatus | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._build_ui()
        self._refresh()
        self._timer.start(30_000)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        top = QHBoxLayout()
        title = QLabel("\ud83d\udccc Canli Firma Durumu")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch()
        self._counter = QLabel("")
        self._counter.setObjectName("counterLabel")
        top.addWidget(self._counter)
        refresh = QPushButton("\u21bb Yenile (30s)")
        refresh.setObjectName("secondaryBtn")
        refresh.clicked.connect(self._refresh)
        top.addWidget(refresh)
        root.addLayout(top)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setObjectName("statusScroll")
        self._inner = QFrame()
        self._grid_lay = QVBoxLayout(self._inner)
        self._grid_lay.setContentsMargins(0, 0, 0, 0)
        self._grid_lay.setSpacing(12)
        self._scroll.setWidget(self._inner)
        root.addWidget(self._scroll, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        root.addWidget(self._status_lbl)

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
        total = len(companies)
        self._counter.setText(f"{online} / {total} online")

        # Online olanlar once
        sorted_companies = sorted(companies, key=lambda c: (0 if c.get("online") else 1, c.get("company_name", "")))

        for c in sorted_companies:
            self._grid_lay.addWidget(_status_card(c))
        self._grid_lay.addStretch()
        self._status_lbl.setText("")
        QTimer.singleShot(
            0,
            lambda position=scroll_position: self._scroll.verticalScrollBar().setValue(
                min(position, self._scroll.verticalScrollBar().maximum())
            ),
        )

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)
