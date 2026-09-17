# -*- coding: utf-8 -*-
from PyQt6.QtGui import QColor
from src.utils.theme_colors import theme_qss

class StockImportPreviewStyleMixin:
    def _apply_table_styles(self):
        self.table.setStyleSheet(theme_qss("""
            QTableWidget { background: @surface; color: @text; border: 1px solid @border; border-radius: 10px; gridline-color: @border; outline: none; }
            QTableWidget::item { outline: none; }
            QTableWidget::item:focus { outline: none; border: none; }
            QHeaderView::section { background: @surface_alt; color: @text; font-weight: 700; padding: 8px; border: none; border-bottom: 1px solid @border; }
            QTableWidget QLineEdit { background: #ffffff; color: #111111; border: 1px solid #4f77ff; border-radius: 6px; selection-background-color: #d9e7ff; selection-color: #111111; padding: 2px 6px; }
        """))

    def _decorate_row(self, row_index, row_data):
        from src.utils.stock_import_parser import StockImportParser
        confidence = float(row_data.get("_confidence") or 0.0)
        flags = list(row_data.get("_flags") or [])
        tooltip = f"Guven: %{round(confidence * 100)}"
        if flags: tooltip += "\n" + "\n".join(flags)
        background = None
        if any("meta" in str(f).lower() or "toplam" in str(f).lower() for f in flags): background = QColor(255, 236, 236)
        elif confidence < StockImportParser.LOW_CONFIDENCE_THRESHOLD: background = QColor(255, 248, 214)
        for col in range(self.table.columnCount()):
            item = self.table.item(row_index, col)
            if item:
                item.setToolTip(tooltip)
                if background: item.setBackground(background)

    def _set_area_scan_busy(self, busy):
        for btn in [getattr(self, "btn_apply_area", None), getattr(self, "btn_scan_crop", None), getattr(self, "btn_crop_retry", None)]:
            if btn: btn.setEnabled(not busy)
        if getattr(self, "btn_apply_area", None): self.btn_apply_area.setText("Taraniyor..." if busy else "Secili Alani Tara ve Aktar")
        if getattr(self, "btn_crop_retry", None): self.btn_crop_retry.setText("Taraniyor..." if busy else "Belgeyi Kirp ve Yeniden Tara")
