"""Provisioning invitation code management page."""

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView,
)

import api_client


class _InviteWorker(QThread):
    done = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, action, payload=None):
        super().__init__()
        self.action = action
        self.payload = dict(payload or {})

    def run(self):
        try:
            if self.action == "create":
                result = api_client.create_provision_invite(**self.payload)
            elif self.action == "revoke":
                result = api_client.revoke_provision_invite(**self.payload)
            else:
                result = api_client.provision_invites()
            self.done.emit(result)
        except Exception as error:
            self.failed.emit(str(error))


class InviteCodesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._workers = set()
        self._last_code = ""
        self._build()
        self.reload()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        top = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Davet Kodu Uretme")
        title.setObjectName("pageTitle")
        title_box.addWidget(title)
        subtitle = QLabel("Yeni firma kurulumu icin guvenli, tek kullanimlik kodlar uretin.")
        subtitle.setObjectName("sectionTitle")
        title_box.addWidget(subtitle)
        top.addLayout(title_box)
        top.addStretch()
        top.addWidget(QLabel("Gecerlilik:"))
        self.hours = QComboBox()
        for label, hours in (("24 saat", 24), ("72 saat", 72), ("7 gun", 168), ("30 gun", 720)):
            self.hours.addItem(label, hours)
        self.hours.setCurrentIndex(1)
        top.addWidget(self.hours)
        self.create_button = QPushButton("Davet Kodu Uret")
        self.create_button.setObjectName("primaryBtn")
        self.create_button.clicked.connect(self.create_code)
        top.addWidget(self.create_button)
        root.addLayout(top)

        info = QLabel(
            "Uretilen kod yeni firma kurulumu veya davet kodu ile lisans etkinlestirme "
            "isleminde bir kez kullanilir. Listeden bir koda tiklayarak goruntuleyebilir "
            "ve panoya kopyalayabilirsiniz."
        )
        info.setWordWrap(True)
        info.setObjectName("statusLabel")
        root.addWidget(info)

        code_row = QHBoxLayout()
        self.code_label = QLabel("Yeni kod henuz uretilmedi.")
        self.code_label.setObjectName("codeBox")
        self.code_label.setMinimumHeight(56)
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.code_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        code_row.addWidget(self.code_label, 1)
        self.copy_button = QPushButton("Kopyala")
        self.copy_button.setObjectName("secondaryBtn")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_code)
        code_row.addWidget(self.copy_button)
        root.addLayout(code_row)

        self.table = QTableWidget(0, 7)
        self.table.setObjectName("dataTable")
        self.table.setHorizontalHeaderLabels(
            ["ID", "Davet Kodu", "Olusturma", "Bitis", "Kullanim", "Durum", "Islem"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 150)
        self.table.itemSelectionChanged.connect(self._select_code)
        self.table.setMinimumHeight(360)
        root.addWidget(self.table, 1)
        self.status = QLabel("")
        self.status.setObjectName("statusLabel")
        root.addWidget(self.status)

    def _run(self, action, payload=None, callback=None):
        worker = _InviteWorker(action, payload)
        if callback:
            worker.done.connect(callback)
        worker.failed.connect(lambda error: self.status.setText(f"Hata: {error}"))
        worker.failed.connect(lambda _error: self.create_button.setEnabled(True))
        worker.finished.connect(lambda current=worker: self._workers.discard(current))
        self._workers.add(worker)
        worker.start()

    def reload(self):
        self._run("list", callback=self._populate)

    def create_code(self):
        self.create_button.setEnabled(False)
        self._run(
            "create",
            {"expires_in_hours": int(self.hours.currentData()), "max_uses": 1},
            self._created,
        )

    def _created(self, result):
        self.create_button.setEnabled(True)
        self._last_code = str(result.get("invite_code") or "")
        self.code_label.setText(self._last_code or "Kod uretilemedi.")
        self.copy_button.setEnabled(bool(self._last_code))
        self.status.setText("Davet kodu uretildi. Guvenli sekilde musterinizle paylasin.")
        self.reload()

    def copy_code(self):
        if self._last_code:
            QApplication.clipboard().setText(self._last_code)
            self.status.setText("Davet kodu panoya kopyalandi.")

    def _populate(self, result):
        invites = list(result.get("invites") or [])
        self.table.setRowCount(0)
        for item in invites:
            row = self.table.rowCount()
            self.table.insertRow(row)
            revoked = bool(item.get("revoked_at"))
            used = int(item.get("use_count") or 0)
            maximum = int(item.get("max_uses") or 0)
            state = "Iptal" if revoked else "Kullanildi" if used >= maximum else "Aktif"
            invite_code = str(item.get("invite_code") or "").strip()
            visible_code = invite_code or "Eski kayit - kod saklanmamis"
            values = (
                item.get("id"), visible_code, item.get("created_at"),
                item.get("expires_at"), f"{used}/{maximum}", state,
            )
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(str(value or "-"))
                if column == 1:
                    table_item.setData(Qt.ItemDataRole.UserRole, invite_code)
                    table_item.setToolTip(visible_code)
                self.table.setItem(row, column, table_item)
            button = QPushButton("Iptal Et")
            button.setObjectName("tableDangerBtn")
            button.setEnabled(state == "Aktif")
            button.clicked.connect(
                lambda _, invite_id=int(item.get("id") or 0): self.revoke(invite_id)
            )
            self.table.setCellWidget(row, 6, button)
        self.status.setText(f"{len(invites)} davet kodu kaydi listelendi.")

    def _select_code(self):
        row = self.table.currentRow()
        if row < 0 or not self.table.item(row, 1):
            self._last_code = ""
            self.copy_button.setEnabled(False)
            return
        item = self.table.item(row, 1)
        self._last_code = str(item.data(Qt.ItemDataRole.UserRole) or "").strip()
        if self._last_code:
            self.code_label.setText(self._last_code)
            self.copy_button.setEnabled(True)
            self.status.setText("Davet kodu secildi. Kopyala dugmesi kullanima hazir.")
        else:
            self.code_label.setText(
                "Bu eski kayit yalnizca guvenlik ozetiyle saklanmis; tam kod geri alinamaz."
            )
            self.copy_button.setEnabled(False)
            self.status.setText("Eski kod geri alinamaz. Yeni bir davet kodu uretin.")

    def revoke(self, invite_id):
        self._run(
            "revoke", {"invite_id": int(invite_id)}, lambda _result: self.reload()
        )
