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
    QAbstractItemView, QLineEdit, QDialog, QFileDialog, QSlider,
    QCheckBox, QScrollArea,
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
        self.pool_card = pool
        pool.setMinimumHeight(252)
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
        rotation_row = QFrame(self)
        rotation_row.setStyleSheet(theme_qss("QFrame { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 4px; }"))
        rotation_layout = QHBoxLayout(rotation_row)
        rotation_layout.setContentsMargins(8, 5, 8, 5)
        rotation_layout.setSpacing(8)
        self.rotation_toggle = QCheckBox("Zero-Downtime Rotation")
        self.rotation_toggle.setObjectName("geminiZeroDowntimeRotation")
        self.rotation_toggle.setChecked(page.db.get_setting("gemini_zero_downtime_rotation", "1") == "1")
        self.rotation_toggle.setStyleSheet(theme_qss("QCheckBox { color: @text; font-size: 10px; spacing: 6px; }"))
        rotation_layout.addWidget(self.rotation_toggle)
        rotation_description = QLabel("429 kota hatalarinda sonraki kayitli Gemini anahtarina gecer.")
        rotation_description.setWordWrap(True)
        rotation_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; border: none; background: transparent;"))
        rotation_layout.addWidget(rotation_description, 1)
        pool_box.addWidget(rotation_row)
        configuration.addWidget(pool, 2)
        page.model_card.setParent(self)
        page.model_card.setObjectName("geminiReferenceModel")
        page.model_card.setGraphicsEffect(None)
        page.model_card.setMinimumHeight(352)
        page.model_card.setStyleSheet(theme_qss("QFrame#geminiReferenceModel { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        page.model_card.layout().setSpacing(6)
        for label in page.model_card.findChildren(QLabel):
            label.setFont(QFont(self.font().family(), 9, label.font().weight()))
        self._add_model_controls(page.model_card.layout())
        page.model_card.layout().addStretch()
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
        plot = QFrame(usage)
        plot.setObjectName("geminiUsagePlot")
        plot.setStyleSheet(theme_qss("QFrame#geminiUsagePlot { background: @finance_surface_alt; border: none; border-radius: 4px; }"))
        plot_layout = QVBoxLayout(plot)
        plot_layout.setContentsMargins(8, 6, 8, 6)
        plot_layout.setSpacing(6)
        for _index in range(3):
            grid_line = QFrame(plot)
            grid_line.setFixedHeight(1)
            grid_line.setStyleSheet(theme_qss("background: @finance_outline; border: none;"))
            plot_layout.addWidget(grid_line)
        note = QLabel("Token, kota ve maliyet telemetrisi bulunmuyor. \u00d6rnek veri g\u00f6sterilmez.")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        plot_layout.addWidget(note, 1)
        usage_box.addWidget(plot, 1)
        usage.setFixedHeight(154)
        root.addWidget(usage)
        feature_row = QHBoxLayout()
        feature_row.setSpacing(8)
        self.feature_toggles = {}
        for key, title, description, default in (
            ("gemini_smart_token_compression", "Ak\u0131ll\u0131 Token S\u0131k\u0131\u015ft\u0131rma", "Gereksiz ba\u011flamlar\u0131 temizler.", "1"),
            ("gemini_cost_limit_protection", "Maliyet \u00dcst S\u0131n\u0131r\u0131 Korumas\u0131", "G\u00fcnl\u00fck $50 s\u0131n\u0131r\u0131nda uyar\u0131r.", "1"),
            ("gemini_auto_load_shedding", "Otomatik Load Shedding", "Y\u00fck tepe yap\u0131nca kuyru\u011fa al\u0131r.", "0"),
        ):
            feature = QFrame(self)
            feature.setStyleSheet(theme_qss("QFrame { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
            feature_layout = QHBoxLayout(feature)
            feature_layout.setContentsMargins(8, 6, 8, 6)
            feature_layout.setSpacing(6)
            labels = QVBoxLayout()
            feature_title = QLabel(title)
            feature_title.setWordWrap(True)
            feature_title.setStyleSheet(theme_qss("color: @text; font-size: 9px; font-weight: 700; border: none; background: transparent;"))
            feature_description = QLabel(description)
            feature_description.setWordWrap(True)
            feature_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 8px; border: none; background: transparent;"))
            labels.addWidget(feature_title)
            labels.addWidget(feature_description)
            toggle = QCheckBox()
            toggle.setObjectName(key)
            toggle.setChecked(self.page.db.get_setting(key, default) == "1")
            toggle.setToolTip(title)
            toggle.toggled.connect(lambda checked, setting=key: self.page.db.set_setting(setting, "1" if checked else "0"))
            self.feature_toggles[key] = toggle
            feature_layout.addLayout(labels, 1)
            feature_layout.addWidget(toggle)
            feature_row.addWidget(feature, 1)
        root.addLayout(feature_row)
        actions = QHBoxLayout()
        self.advanced_button = QPushButton("T\u00fcm API, Otonom ve Ileti\u015fim Ayarlar\u0131")
        self.advanced_button.setCheckable(True)
        self.advanced_button.toggled.connect(page.setVisible)
        self.save_button = QPushButton("Ayarlar\u0131 Kaydet")
        self.save_button.clicked.connect(self._save_settings)
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

    def _add_model_controls(self, layout):
        db = self.page.db
        self.max_tokens = QSlider(Qt.Orientation.Horizontal, self.page.model_card)
        self.max_tokens.setRange(512, 8192)
        self.max_tokens.setSingleStep(256)
        self.max_tokens.setValue(int(db.get_setting("gemini_max_output_tokens", "8192") or 8192))
        self.max_tokens.setObjectName("geminiMaxOutputTokens")
        self.max_tokens_value = QLabel(str(self.max_tokens.value()), self.page.model_card)
        self.temperature = QSlider(Qt.Orientation.Horizontal, self.page.model_card)
        self.temperature.setRange(0, 20)
        self.temperature.setSingleStep(1)
        self.temperature.setValue(round(float(db.get_setting("gemini_temperature", "0.2") or 0.2) * 10))
        self.temperature.setObjectName("geminiTemperature")
        self.temperature_value = QLabel(f"{self.temperature.value() / 10:.1f}", self.page.model_card)
        control_style = theme_qss("QSlider::groove:horizontal { height: 4px; background: @finance_surface_alt; border-radius: 2px; } QSlider::sub-page:horizontal { background: @finance_primary; border-radius: 2px; } QSlider::handle:horizontal { background: @finance_primary; width: 12px; margin: -5px 0; border-radius: 6px; }")
        for control in (self.max_tokens, self.temperature):
            control.setFixedHeight(18)
            control.setStyleSheet(control_style)

        token_heading = QHBoxLayout()
        token_label = QLabel("Max Token Limiti")
        token_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        token_heading.addWidget(token_label, 1)
        token_heading.addWidget(self.max_tokens_value)
        layout.addLayout(token_heading)
        layout.addWidget(self.max_tokens)

        temperature_heading = QHBoxLayout()
        temperature_label = QLabel("S\u0131cakl\u0131k (Temperature)")
        temperature_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        temperature_heading.addWidget(temperature_label, 1)
        temperature_heading.addWidget(self.temperature_value)
        layout.addLayout(temperature_heading)
        layout.addWidget(self.temperature)

        self.max_tokens.valueChanged.connect(lambda value: self.max_tokens_value.setText(str(value)))
        self.temperature.valueChanged.connect(
            lambda value: self.temperature_value.setText(f"{value / 10:.1f}")
        )

        self.safety_toggle = QCheckBox("Otonom Ak\u0131\u015f G\u00fcvenli\u011fi")
        self.safety_toggle.setObjectName("geminiSensitiveDataMasking")
        self.safety_toggle.setChecked(db.get_setting("gemini_sensitive_data_masking", "1") == "1")
        self.safety_toggle.setStyleSheet(theme_qss("QCheckBox { color: @text; font-size: 10px; spacing: 6px; }"))
        layout.addWidget(self.safety_toggle)
        safety_hint = QLabel("Hassas teknik servis verileri bulut iste\u011finden \u00f6nce maskelenir.")
        safety_hint.setWordWrap(True)
        safety_hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; border: none; background: transparent;"))
        layout.addWidget(safety_hint)

        self.connection_test_button = QPushButton("Ba\u011flant\u0131 Test Suitini \u00c7al\u0131\u015ft\u0131r")
        self.connection_test_button.setObjectName("geminiConnectionTestSuite")
        self.connection_test_button.setFixedHeight(34)
        self.connection_test_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.connection_test_button.clicked.connect(self.page.test_connection)
        layout.addWidget(self.connection_test_button)

    def _save_settings(self):
        self.page.save_data()
        db = self.page.db
        db.set_setting("gemini_max_output_tokens", str(self.max_tokens.value()))
        db.set_setting("gemini_temperature", f"{self.temperature.value() / 10:.1f}")
        db.set_setting("gemini_sensitive_data_masking", "1" if self.safety_toggle.isChecked() else "0")
        db.set_setting("gemini_zero_downtime_rotation", "1" if self.rotation_toggle.isChecked() else "0")

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
        self.pool_card.setMinimumHeight(352 if keys else 252)
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
