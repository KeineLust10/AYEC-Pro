# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


class StockSmartImportDialog(ModernDialog):
    """Stock import selector for PDF, image, spreadsheet, and document files."""

    PDF_FILTER = "PDF Dosyalari (*.pdf)"
    IMAGE_FILTER = "Resim Dosyalari (*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.ppm)"
    DOCUMENT_FILTER = (
        "Excel ve Belge Dosyalari (*.xlsx *.xls *.csv *.xml *.docx);;"
        "Excel Dosyalari (*.xlsx *.xls *.csv);;"
        "Belge Dosyalari (*.xml *.docx)"
    )

    def __init__(self, parent=None):
        super().__init__(
            title="Ak\u0131ll\u0131 Stok \u0130\u00e7e Aktar",
            parent=parent,
            width=860,
            height=520,
        )
        self.set_footer_visible(False)
        self.selected_path = ""
        self.selected_mode = ""
        self._build_ui()

    @classmethod
    def get_import_request(cls, parent=None):
        dialog = cls(parent)
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.selected_path:
            return dialog.selected_path, dialog.selected_mode
        return "", ""

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        tabs = QTabWidget()
        tabs.setObjectName("StockSmartImportTabs")
        tabs.addTab(
            self._build_tab(
                title="Pdf İçe Aktar",
                subtitle="pdfplumber tablo çizgilerini ve kolon sınırlarını okuyarak fatura satırlarını ayırır.",
                pipeline="PDF tablo motoru: pdfplumber",
                button_text="PDF Seç",
                mode="pdf",
            ),
            "Pdf İçe Aktar",
        )
        tabs.addTab(
            self._build_tab(
                title="Excel / Belge \u0130\u00e7e Aktar",
                subtitle=(
                    "Excel, CSV, XML ve DOCX stok listelerini kolon adlarina gore "
                    "eslestirir ve onizlemeye aktarir."
                ),
                pipeline="Belge motoru: pandas, openpyxl, XML ve DOCX okuyucu",
                button_text="Belge Se\u00e7",
                mode="document",
            ),
            "Excel / Belge",
        )
        tabs.addTab(
            self._build_tab(
                title="Resim İçe Aktar",
                subtitle="PaddleOCR + LayoutLM yaklaşımı için kutu tabanlı belge okuma akışı hazırlanır.",
                pipeline="Resim OCR motoru: PaddleOCR varsa önce o, yoksa EasyOCR/Tesseract",
                button_text="Resim Seç",
                mode="image",
            ),
            "Resim İçe Aktar",
        )
        root.addWidget(tabs)

        self.add_layout(root)
        self.setStyleSheet(
            theme_qss(
                """
                QTabWidget#StockSmartImportTabs::pane {
                    border: 1px solid @border;
                    border-radius: 8px;
                    background: @surface;
                }
                QTabWidget#StockSmartImportTabs QTabBar::tab {
                    min-width: 170px;
                    padding: 10px 16px;
                    border: 1px solid @border;
                    border-bottom: none;
                    background: @surface_alt;
                    color: @text;
                }
                QTabWidget#StockSmartImportTabs QTabBar::tab:selected {
                    background: @surface;
                    color: @primary;
                    font-weight: 700;
                }
                QFrame#ImportPanel {
                    background: @surface;
                    border: none;
                }
                QLabel#ImportTitle {
                    font-size: 22px;
                    font-weight: 800;
                    color: @text;
                }
                QLabel#ImportSubtitle,
                QLabel#ImportPipeline {
                    font-size: 13px;
                    color: @text_muted;
                }
                QLabel#ImportBadge {
                    border: 1px solid @border;
                    border-radius: 6px;
                    padding: 8px 10px;
                    color: @text;
                    background: @surface_alt;
                }
                """
            )
        )

    def _build_tab(self, title, subtitle, pipeline, button_text, mode):
        panel = QFrame()
        panel.setObjectName("ImportPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setObjectName("ImportTitle")
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("ImportSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

        pipeline_label = QLabel(pipeline)
        pipeline_label.setObjectName("ImportPipeline")
        pipeline_label.setWordWrap(True)
        layout.addWidget(pipeline_label)

        badges = QHBoxLayout()
        for text in self._badges_for_mode(mode):
            badge = QLabel(text)
            badge.setObjectName("ImportBadge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badges.addWidget(badge)
        badges.addStretch()
        layout.addLayout(badges)

        layout.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setMinimumSize(120, 42)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="md")))
        cancel_btn.clicked.connect(self.reject)
        actions.addWidget(cancel_btn)

        choose_btn = QPushButton(button_text)
        choose_btn.setMinimumSize(150, 42)
        choose_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        choose_btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="md")))
        choose_btn.clicked.connect(lambda _=False, m=mode: self._select_file(m))
        actions.addWidget(choose_btn)
        layout.addLayout(actions)

        return panel

    def _badges_for_mode(self, mode):
        if mode == "pdf":
            return ["\u00c7izgili tablo", "Kolon ayr\u0131m\u0131", "DataFrame \u00f6nizleme"]
        if mode == "image":
            return ["Kutu bazl\u0131 OCR", "PaddleOCR haz\u0131r", "LayoutLM haz\u0131rl\u0131\u011f\u0131"]
        return ["Excel / CSV", "XML / DOCX", "Kolon e\u015fle\u015ftirme"]

    def _select_file(self, mode):
        if mode == "pdf":
            title = "PDF \u0130\u00e7e Aktar"
            file_filter = self.PDF_FILTER
        elif mode == "image":
            title = "Resim \u0130\u00e7e Aktar"
            file_filter = self.IMAGE_FILTER
        else:
            title = "Excel / Belge \u0130\u00e7e Aktar"
            file_filter = self.DOCUMENT_FILTER

        path, _ = QFileDialog.getOpenFileName(self, title, "", file_filter)
        if not path:
            return

        suffix = Path(path).suffix.lower()
        if mode == "pdf" and suffix != ".pdf":
            return
        if mode == "image" and suffix not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".webp",
            ".tif",
            ".tiff",
            ".ppm",
        }:
            return
        if mode == "document" and suffix not in {".xlsx", ".xls", ".csv", ".xml", ".docx"}:
            return

        self.selected_path = path
        self.selected_mode = mode
        self.accept()
