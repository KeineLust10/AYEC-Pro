"""AYEC Pro Admin Console - controlled desktop update deployment."""
import re

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

import api_client


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(api_client.companies())
        except Exception as exc:
            self.error.emit(str(exc))


class _DeployUpdate(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, version: str, targets: list, changelog: str, channel: str):
        super().__init__()
        self._version = version
        self._targets = targets
        self._changelog = changelog
        self._channel = channel

    def run(self):
        try:
            self.done.emit(api_client.deploy_update(
                self._version,
                self._targets,
                self._changelog,
                self._channel,
            ))
        except Exception as exc:
            self.error.emit(str(exc))


class UpdatesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._workers: set[QThread] = set()
        self._build_ui()
        self._load_companies()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        title = QLabel("\U0001f680 G\u00fcncelleme Da\u011f\u0131t\u0131m\u0131")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        info = QLabel(
            "Yeni s\u00fcr\u00fcm\u00fc \u00f6nce se\u00e7ili pilot firmalarda do\u011frulay\u0131n. "
            "Kararl\u0131 da\u011f\u0131t\u0131m\u0131 yaln\u0131zca pilot sonu\u00e7lar\u0131 temizse t\u00fcm firmalara g\u00f6nderin."
        )
        info.setObjectName("metricSub")
        info.setWordWrap(True)
        root.addWidget(info)

        version_row = QHBoxLayout()
        version_row.addWidget(QLabel("S\u00fcr\u00fcm:"))
        self._version = QLineEdit()
        self._version.setObjectName("fieldInput")
        self._version.setPlaceholderText("2.0.1")
        version_row.addWidget(self._version, 2)
        version_row.addWidget(QLabel("Kanal:"))
        self._channel = QComboBox()
        self._channel.setObjectName("combo")
        self._channel.addItem("Pilot", "pilot")
        self._channel.addItem("Kararl\u0131", "stable")
        version_row.addWidget(self._channel, 1)
        root.addLayout(version_row)

        scope_row = QHBoxLayout()
        scope_row.addWidget(QLabel("Hedef:"))
        self._pilot = QRadioButton("Se\u00e7ili pilot firmalar")
        self._all = QRadioButton("T\u00fcm aktif firmalar")
        self._pilot.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self._pilot)
        group.addButton(self._all)
        self._scope_group = group
        scope_row.addWidget(self._pilot)
        scope_row.addWidget(self._all)
        scope_row.addStretch()
        select_all = QPushButton("T\u00fcm\u00fcn\u00fc Se\u00e7")
        select_all.setObjectName("secondaryBtn")
        select_all.clicked.connect(lambda: self._set_all_checks(Qt.CheckState.Checked))
        scope_row.addWidget(select_all)
        clear = QPushButton("Se\u00e7imi Temizle")
        clear.setObjectName("secondaryBtn")
        clear.clicked.connect(lambda: self._set_all_checks(Qt.CheckState.Unchecked))
        scope_row.addWidget(clear)
        root.addLayout(scope_row)

        self._companies = QListWidget()
        self._companies.setObjectName("dataTable")
        root.addWidget(self._companies, 1)

        root.addWidget(QLabel("S\u00fcr\u00fcm Notlar\u0131"))
        self._changelog = QTextEdit()
        self._changelog.setObjectName("textArea")
        self._changelog.setFixedHeight(130)
        self._changelog.setPlaceholderText(
            "D\u00fczeltilen hatalar\u0131 ve kullan\u0131c\u0131y\u0131 etkileyen de\u011fi\u015fiklikleri yaz\u0131n."
        )
        root.addWidget(self._changelog)

        action_row = QHBoxLayout()
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        action_row.addWidget(self._status, 1)
        deploy = QPushButton("\U0001f680 Da\u011f\u0131t\u0131m\u0131 Kuyrukla")
        deploy.setObjectName("primaryBtn")
        deploy.clicked.connect(self._deploy)
        action_row.addWidget(deploy)
        root.addLayout(action_row)

    def _keep(self, worker: QThread):
        self._workers.add(worker)
        worker.finished.connect(lambda: self._workers.discard(worker))
        worker.start()

    def _load_companies(self):
        worker = _FetchCompanies()
        worker.done.connect(self._populate_companies)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _populate_companies(self, companies: list):
        self._companies.clear()
        for company in companies:
            if int(company.get("active", 1) or 0) != 1:
                continue
            item = QListWidgetItem(company.get("company_name", "?"))
            item.setData(Qt.ItemDataRole.UserRole, company.get("id", ""))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._companies.addItem(item)
        self._status.setText(f"{self._companies.count()} aktif firma y\u00fcklendi.")

    def _set_all_checks(self, state: Qt.CheckState):
        for index in range(self._companies.count()):
            self._companies.item(index).setCheckState(state)

    def _selected_targets(self) -> list[str]:
        return [
            str(self._companies.item(index).data(Qt.ItemDataRole.UserRole))
            for index in range(self._companies.count())
            if self._companies.item(index).checkState() == Qt.CheckState.Checked
        ]

    def _deploy(self):
        version = self._version.text().strip()
        changelog = self._changelog.toPlainText().strip()
        channel = str(self._channel.currentData() or "pilot")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-+][A-Za-z0-9.-]+)?", version):
            self._status.setText("Ge\u00e7erli bir s\u00fcr\u00fcm numaras\u0131 girin. \u00d6rnek: 2.0.1")
            return
        if not changelog:
            self._status.setText("S\u00fcr\u00fcm notlar\u0131 bo\u015f olamaz.")
            return
        targets = [] if self._all.isChecked() else self._selected_targets()
        if self._pilot.isChecked() and not targets:
            self._status.setText("En az bir pilot firma se\u00e7in.")
            return
        if self._all.isChecked():
            answer = QMessageBox.warning(
                self,
                "Genel Da\u011f\u0131t\u0131m Onay\u0131",
                f"{version} s\u00fcr\u00fcm\u00fc t\u00fcm aktif firmalara g\u00f6nderilecek. "
                "Pilot do\u011frulamas\u0131n\u0131 tamamlad\u0131\u011f\u0131n\u0131zdan emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        else:
            answer = QMessageBox.question(
                self,
                "Pilot Da\u011f\u0131t\u0131m Onay\u0131",
                f"{version} s\u00fcr\u00fcm\u00fc {len(targets)} pilot firmaya g\u00f6nderilsin mi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._status.setText("Da\u011f\u0131t\u0131m komutlar\u0131 olu\u015fturuluyor...")
        worker = _DeployUpdate(version, targets, changelog, channel)
        worker.done.connect(self._deploy_done)
        worker.error.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._keep(worker)

    def _deploy_done(self, result: dict):
        targets = result.get("targets", "all")
        target_text = "t\u00fcm firmalar" if targets == "all" else f"{len(targets)} firma"
        self._status.setText(
            f"\u2713 {result.get('version', '')} s\u00fcr\u00fcm\u00fc {target_text} i\u00e7in kuyru\u011fa al\u0131nd\u0131."
        )

