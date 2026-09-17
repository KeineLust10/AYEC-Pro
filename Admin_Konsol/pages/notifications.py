"""
AYEC Pro Admin Konsol - Bildirim & Mesaj Gonderme
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QComboBox, QCheckBox, QFrame,
    QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal
import api_client


class _SendThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, target: str, title: str, body: str, icon: str, popup: bool):
        super().__init__()
        self._target = target
        self._title = title
        self._body = body
        self._icon = icon
        self._popup = popup

    def run(self):
        try:
            self.done.emit(api_client.send_notification(
                self._target, self._title, self._body, self._icon, self._popup
            ))
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchCompanies(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception:
            self.done.emit([])


class NotificationsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._companies: list[dict] = []
        self._thread = None
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(20)

        title = QLabel("\ud83d\udd14 Bildirim & Mesaj Gonder")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        form = QFrame()
        form.setObjectName("formCard")
        form_lay = QVBoxLayout(form)
        form_lay.setContentsMargins(24, 24, 24, 24)
        form_lay.setSpacing(16)

        # Hedef
        form_lay.addWidget(QLabel("Hedef Kitle"))
        self._target_combo = QComboBox()
        self._target_combo.setObjectName("combo")
        self._target_combo.addItem("Tum Firmalar", "all")
        self._target_combo.currentIndexChanged.connect(self._on_target_change)
        form_lay.addWidget(self._target_combo)

        # Mesaj basligi
        form_lay.addWidget(QLabel("Mesaj Basligi"))
        self._title_input = QLineEdit()
        self._title_input.setObjectName("fieldInput")
        self._title_input.setPlaceholderText("Ornegin: Yeni Surum Yayinlandi")
        form_lay.addWidget(self._title_input)

        # Mesaj icerigi
        form_lay.addWidget(QLabel("Mesaj Icerigi"))
        self._body_input = QTextEdit()
        self._body_input.setObjectName("textArea")
        self._body_input.setFixedHeight(120)
        self._body_input.setPlaceholderText("Lutfen programinizi guncelleyiniz...")
        form_lay.addWidget(self._body_input)

        # Ikon & popup row
        icon_row = QHBoxLayout()
        icon_row.addWidget(QLabel("Ikon:"))
        self._icon_combo = QComboBox()
        self._icon_combo.setObjectName("combo")
        self._icon_combo.addItems(["info", "warning", "error", "success"])
        icon_row.addWidget(self._icon_combo)
        icon_row.addSpacing(24)
        self._popup_check = QCheckBox("Masaustunde Popup Olarak Goster")
        self._popup_check.setChecked(True)
        self._popup_check.setObjectName("rememberCheck")
        icon_row.addWidget(self._popup_check)
        icon_row.addStretch()
        form_lay.addLayout(icon_row)

        # Gonder butonu
        send_btn = QPushButton("\ud83d\udce4 Mesaj Yayinla / Gonder")
        send_btn.setObjectName("primaryBtn")
        send_btn.setFixedHeight(46)
        send_btn.clicked.connect(self._send)
        form_lay.addWidget(send_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        form_lay.addWidget(self._status_lbl)

        root.addWidget(form)
        root.addStretch()

    def _load_companies(self):
        t = _FetchCompanies()
        t.done.connect(self._populate_companies)
        t.start()
        self._thread = t

    def _populate_companies(self, companies: list):
        self._companies = companies
        self._target_combo.clear()
        self._target_combo.addItem("Tum Firmalar", "all")
        for c in companies:
            self._target_combo.addItem(c.get("company_name", "?"), c.get("id", ""))

    def _on_target_change(self, idx: int):
        pass

    def _send(self):
        target = self._target_combo.currentData() or "all"
        title_text = self._title_input.text().strip()
        body_text = self._body_input.toPlainText().strip()
        icon = self._icon_combo.currentText()
        popup = self._popup_check.isChecked()

        if not title_text or not body_text:
            self._status_lbl.setText("Basl\u0131k ve icerik bos birakilamaz.")
            return

        target_label = self._target_combo.currentText()
        reply = QMessageBox.question(self, "Onay",
            f"'{target_label}' hedefine mesaj gonderilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        t = _SendThread(target, title_text, body_text, icon, popup)
        t.done.connect(lambda d: self._status_lbl.setText(
            f"\u2705 Mesaj gonderildi. Alici: {d.get('sent_to', '?')}"
        ))
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t
