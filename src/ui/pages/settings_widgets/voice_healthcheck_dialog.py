# -*- coding: utf-8 -*-

"""
Voice Healthcheck Dialog
Sesli Asistan Sağlık Testi Sonuç Dialog'u
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QDialog, QTextEdit, QApplication, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
import json
import os

from src.utils.theme_colors import theme_qss
from src.utils.path_helper import PathHelper
from src.utils.toast_notification import show_success, show_error
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog


class VoiceHealthcheckResultDialog(ModernDialog):
    """Sesli Asistan Sağlık Testi Sonuç Dialog'u"""
    
    def __init__(self, parent, payload):
        super().__init__(title="Sesli Asistan Saglik Testi", parent=parent, width=860, height=640)
        self.payload = payload or {}
        self.setModal(True)
        self.set_footer_visible(False)
        self._build_ui()

    def _build_ui(self):
        self.setStyleSheet(theme_qss("QDialog { background: @surface_alt; }"))
        layout = self.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Sesli Asistan Sağlık Testi")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        wake_word = self.payload.get("wake_word", "-")
        overall_ok = bool(self.payload.get("overall_ok"))
        summary = QLabel(
            f"Genel Durum: {'Başarılı' if overall_ok else 'Sorun Var'}\n"
            f"Uyanma Adı: {wake_word}"
        )
        summary.setStyleSheet(theme_qss(
            """
            QLabel {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 12px 14px;
                font-weight: 700;
            }
            """
        ))
        layout.addWidget(summary)

        details = QTextEdit()
        details.setReadOnly(True)
        details.setStyleSheet(theme_qss(
            """
            QTextEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 10px;
                font-size: 12px;
            }
            """
        ))

        lines = ["Senaryo Sonuçları:"]
        for item in self.payload.get("scenario_results", []):
            mark = "OK" if item.get("ok") else "HATA"
            phrase = item.get("phrase", "-")
            expected = item.get("expected_action", "-")
            emitted = item.get("emitted", [])
            lines.append(f"- [{mark}] {phrase}")
            lines.append(f"  Beklenen: {expected}")
            lines.append(f"  Gelen: {emitted if emitted else '-'}")

        lines.append("")
        lines.append("Bağımlılık Sonuçları:")
        for item in self.payload.get("db_dependency_results", []):
            mark = "OK" if item.get("ok") else "HATA"
            lines.append(f"- [{mark}] {item.get('name', '-')}")

        details.setPlainText("\n".join(lines))
        self.details = details
        layout.addWidget(details, 1)

        footer = QHBoxLayout()
        btn_copy = QPushButton("JSON Kopyala")
        btn_copy.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        btn_copy.clicked.connect(self.copy_json)
        btn_export = QPushButton("Raporu Dışa Aktar")
        btn_export.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        btn_export.clicked.connect(self.export_json)
        footer.addWidget(btn_copy)
        footer.addWidget(btn_export)
        footer.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def copy_json(self):
        try:
            QApplication.clipboard().setText(json.dumps(self.payload, ensure_ascii=False, indent=2))
            show_success(self, "Sağlık testi JSON verisi panoya kopyalandı.")
        except Exception as e:
            show_error(self, f"JSON kopyalanamadı: {e}")

    def export_json(self):
        try:
            default_name = "voice_healthcheck_report.json"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Sağlık Testi Raporunu Kaydet",
                os.path.join(PathHelper.get_app_data_dir(), default_name),
                "JSON Files (*.json)",
            )
            if not path:
                return
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.payload, f, ensure_ascii=False, indent=2)
            show_success(self, "Sağlık testi raporu kaydedildi.")
        except Exception as e:
            show_error(self, f"Rapor dışa aktarılamadı: {e}")

