"""Native key-pool reference layout backed by the existing settings editor."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QDialog, QFileDialog,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error


class GeminiReferenceCanvas(QWidget):
    def __init__(self, page, parent=None):
        super().__init__(parent)
        self.page = page
        self.test_results = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        statistics = QGridLayout()
        statistics.setSpacing(8)
        self.summary_labels = {}
        for column, (key, title) in enumerate((
            ("engine", "Latency & Engine"), ("quota", "API Quota Remaining"),
            ("rotation", "Load Balancing Mode"), ("keys", "Active Keys Pool"),
        )):
            card, box = self._card("geminiSummaryCard")
            card.setFixedHeight(84)
            caption = QLabel(title)
            caption.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
            value = QLabel()
            value.setWordWrap(True)
            value.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none; background: transparent;"))
            box.addWidget(caption)
            box.addWidget(value)
            self.summary_labels[key] = value
            statistics.addWidget(card, 0, column)
        root.addLayout(statistics)

        configuration = QHBoxLayout()
        configuration.setSpacing(8)
        pool, pool_box = self._card("geminiPoolCard")
        pool.setMinimumHeight(352)
        heading = QHBoxLayout()
        title = QLabel("API Key Pool & Fallback Matrix")
        title.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; border: none; background: transparent;"))
        heading.addWidget(title, 1)
        self.add_key_button = QPushButton("+ Yeni Key Ekle")
        self.add_key_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.add_key_button.clicked.connect(lambda: self._edit_key())
        heading.addWidget(self.add_key_button)
        pool_box.addLayout(heading)
        description = QLabel("Anahtarlar mevcut havuzdan okunur; test edilmemi\u015f ba\u011flant\u0131lar aktif say\u0131lmaz.")
        description.setWordWrap(True)
        description.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        pool_box.addWidget(description)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Key Identifier", "Provider", "Weight / Priority", "Status", "Latency", "Actions"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().resizeSection(5, 70)
        self.table.setStyleSheet(theme_qss("QTableWidget { background: @finance_surface; color: @text; border: none; } QHeaderView::section { background: @finance_surface; color: @text_muted; font-size: 10px; padding: 6px; border: none; border-bottom: 1px solid @finance_outline; } QTableWidget::item { border-bottom: 1px solid @finance_outline; padding: 4px; }"))
        pool_box.addWidget(self.table, 1)
        configuration.addWidget(pool, 2)
        page.model_card.setParent(self)
        page.model_card.setObjectName("geminiReferenceModel")
        page.model_card.setGraphicsEffect(None)
        page.model_card.setStyleSheet(theme_qss("QFrame#geminiReferenceModel { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        page.model_card.layout().setSpacing(6)
        page.model_card.layout().addStretch()
        for label in page.model_card.findChildren(QLabel):
            label.setFont(QFont(self.font().family(), 9, label.font().weight()))
        configuration.addWidget(page.model_card, 1)
        root.addLayout(configuration)

        usage, usage_box = self._card("geminiUsageCard")
        usage_heading = QLabel("Kullan\u0131m & Maliyet Analizi (Son 24 Saat)")
        usage_heading.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; background: transparent; border: none;"))
        usage_header = QHBoxLayout()
        usage_header.addWidget(usage_heading, 1)
        self.export_button = QPushButton("Rapor Indir")
        self.export_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.export_button.clicked.connect(self._export_report)
        usage_header.addWidget(self.export_button)
        usage_box.addLayout(usage_header)
        note = QLabel("Token, kota ve maliyet telemetrisi bulunmuyor. \u00d6rnek veri g\u00f6sterilmez.")
        note.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        usage_box.addWidget(note)
        usage.setFixedHeight(104)
        root.addWidget(usage)
        actions = QHBoxLayout()
        self.advanced_button = QPushButton("T\u00fcm API, Otonom ve Ileti\u015fim Ayarlar\u0131")
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(page.setVisible)
        self.save_button = QPushButton("Ayarlar\u0131 Kaydet")
        self.save_button.clicked.connect(page.save_data)
        for button in (self.advanced_button, self.save_button):
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            actions.addWidget(button)
        root.addLayout(actions)
        root.addWidget(page)
        page.hide()
        root.addStretch()
        page.inp_api_key.textChanged.connect(self.refresh_keys)
        page.cmb_model.currentTextChanged.connect(self.refresh_keys)
        self.refresh_keys()

    def _card(self, name):
        card = QFrame()
        card.setObjectName(name)
        card.setStyleSheet(theme_qss(f"QFrame#{name} {{ background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }}"))
        box = QVBoxLayout(card)
        box.setContentsMargins(12, 10, 12, 10)
        box.setSpacing(6)
        return card, box

    def _keys(self):
        return [key.strip() for key in self.page.inp_api_key.toPlainText().replace(",", "\n").split("\n") if key.strip()]

    def refresh_keys(self, *_args):
        keys = self._keys()
        model = self.page.cmb_model.currentText().split(' ')[0]
        matching = [result for result in self.test_results.values() if result[2] == model]
        latency = f"{matching[-1][1]} ms" if matching else "- ms"
        self.summary_labels["engine"].setText(f"{latency}\n{model}")
        self.summary_labels["quota"].setText("-\nKota telemetrisi yok")
        self.summary_labels["rotation"].setText("S\u0131ral\u0131 anahtar havuzu")
        self.summary_labels["keys"].setText(f"{len(keys)} Kay\u0131tl\u0131 Anahtar")
        self.table.setRowCount(len(keys))
        for row, key in enumerate(keys):
            identity = "GEMINI_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8].upper()
            result = self.test_results.get(identity)
            status, latency = "Test edilmedi", "-"
            if result and result[2] == model:
                status = "Test ba\u015far\u0131l\u0131" if result[0] else "Test ba\u015far\u0131s\u0131z"
                latency = f"{result[1]} ms"
            for column, value in enumerate((identity, "Google Gemini", "-", status, latency)):
                self.table.setItem(row, column, QTableWidgetItem(value))
            test = QPushButton("Ping Test")
            test.clicked.connect(lambda _checked=False, index=row: self._test_key(index))
            test.setStyleSheet(theme_qss("QPushButton { color: @text; background: @finance_surface_alt; border: none; border-radius: 4px; padding: 2px 4px; font-size: 10px; } QPushButton:hover { color: @finance_primary; }"))
            self.table.setCellWidget(row, 5, test)

    def _test_key(self, index):
        keys = self._keys()
        if 0 <= index < len(keys) and self.page.btn_test.isEnabled():
            identity = "GEMINI_" + hashlib.sha256(keys[index].encode("utf-8")).hexdigest()[:8].upper()
            model = self.page.cmb_model.currentText().split(' ')[0]
            started = perf_counter()
            self.page.test_connection(keys_override=[keys[index]])
            worker = getattr(self.page, "worker", None)
            if worker is not None:
                worker.finished.connect(lambda success, _data: self._record_test(identity, model, started, success))

    def _record_test(self, identity, model, started, success):
        self.test_results[identity] = (bool(success), max(0, round((perf_counter() - started) * 1000)), model)
        self.refresh_keys()

    def _edit_key(self):
        dialog = ModernDialog("Yeni API Anahtar\u0131", self, width=460, height=240)
        field = QLineEdit()
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setPlaceholderText("Google Gemini API anahtar\u0131")
        dialog.content_layout.addWidget(field)
        dialog.add_button("Iptal", "secondary", dialog.reject)
        dialog.add_button("Havuza Ekle", "primary", dialog.accept)
        if dialog.exec() == QDialog.DialogCode.Accepted and field.text().strip():
            keys = self._keys()
            keys.append(field.text().strip())
            self.page.inp_api_key.setPlainText("\n".join(keys))

    def _export_report(self):
        filename, _filter = QFileDialog.getSaveFileName(self, "API Havuzu Raporu", "api_pool_report.json", "JSON (*.json)")
        if not filename:
            return
        rows = [
            {name: self.table.item(row, column).text() for column, name in enumerate(
                ("key_identifier", "provider", "weight", "test_status", "latency")
            )}
            for row in range(self.table.rowCount())
        ]
        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "current_local_key_pool_snapshot",
            "model": self.page.cmb_model.currentText().split(" ")[0],
            "token_usage": None, "quota_remaining": None, "cost": None,
            "keys": rows,
        }
        try:
            Path(filename).write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")
            show_success(self, f"{len(rows)} anahtar\u0131n maskelenmi\u015f raporu kaydedildi.")
        except OSError as error:
            show_error(self, f"Rapor kaydedilemedi: {error}")
