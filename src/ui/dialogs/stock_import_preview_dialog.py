# -*- coding: utf-8 -*-
import os
import json
import re
import tempfile
from pathlib import Path
from PIL import Image, ImageOps

from PyQt6.QtCore import Qt, QTimer, QSize, QRect, QThread
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QHeaderView, QSplitter,
    QWidget, QFrame, QScrollArea, QTextEdit, QDialog, QSpinBox, QDialogButtonBox
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success, show_info, show_warning
from src.utils.stock_import_parser import StockImportParser

# Mixins
from src.ui.dialogs._sipd_style_mixin import StockImportPreviewStyleMixin
from src.ui.dialogs._sipd_mapping_mixin import StockImportPreviewMappingMixin
from src.ui.dialogs._sipd_ui_mixin import StockImportPreviewUiMixin
from src.ui.dialogs._sipd_logic_mixin import StockImportPreviewLogicMixin
from src.ui.dialogs._sipd_column_picker import StockImportPreviewColumnPickerMixin

# Components
from src.ui.dialogs._sipd_label import SourceSelectionLabel
from src.ui.dialogs._sipd_worker import _OcrWorker

class StockImportPreviewDialog(
    ModernDialog,
    StockImportPreviewStyleMixin,
    StockImportPreviewMappingMixin,
    StockImportPreviewUiMixin,
    StockImportPreviewLogicMixin,
    StockImportPreviewColumnPickerMixin
):
    """
    Stok içeri aktarma işlemi öncesi önizleme ve düzenleme diyaloğu.
    Artık modüler mixin yapısı ile yönetilmektedir (<= 800 satır kuralı).
    """
    
    TECH_FIELDS = [
        "category", "code", "name", "brand",
        "unit", "stock",
        "purchase_price", "price", "currency", "supplier", "shelf", "desc",
    ]
    AUTO_FIELDS = [
        "category", "code", "compatible_models", "condition", "name", "brand",
        "unit", "stock",
        "purchase_price", "price", "currency", "supplier",
        "oem_code", "equivalent_code", "vehicle_brand", "vehicle_model",
        "position", "shelf", "desc",
    ]

    def __init__(
        self,
        parent=None,
        parse_result=None,
        db=None,
        selection_only=False,
        active_fields=None,
        field_labels=None,
        action_text=None,
        dialog_title=None,
    ):
        super().__init__(parent=parent, title="Akıllı Stok İçe Aktarım Önizleme", size=(1500, 920))
        self.set_footer_visible(False)
        if dialog_title:
            self._title = str(dialog_title)
            self.setWindowTitle(self._title)
            if hasattr(self, "lbl_title"):
                self.lbl_title.setText(self._title)
        self.setMinimumSize(1280, 820)
        self.db = db
        self.selection_only = bool(selection_only)
        self.selected_rows = []
        self.parse_result = parse_result or {}
        self._recover_if_empty_result()
        
        self.is_automotive = self._is_automotive()
        self.source_columns = self._filter_source_columns(
            self.parse_result.get("detected_columns") or []
        )
        self.raw_rows = list(self.parse_result.get("raw_rows") or [])
        self.current_profile = "otomotiv" if self.is_automotive else "teknik_servis"

        self.active_fields = list(
            active_fields
            or (self.AUTO_FIELDS if self.is_automotive else self.TECH_FIELDS)
        )
        labels = dict(field_labels or {})
        self.COLUMNS = [
            (
                field,
                labels.get(
                    field,
                    StockImportParser.FIELD_LABELS.get(field, field),
                ),
            )
            for field in self.active_fields
        ]
        
        if not self.source_columns and self.raw_rows:
            self.source_columns = self._filter_source_columns(
                StockImportParser._detect_columns_from_rows(self.raw_rows)
            )
        
        self.current_mapping = self._filter_mapping(
            self.parse_result.get("suggested_mapping") or {}
        )
        if not self.current_mapping and self.source_columns:
            self.current_mapping = self._filter_mapping(
                StockImportParser.build_profile_mapping(
                    self.source_columns,
                    self.current_profile,
                )
            )
        
        self.mapping_widgets = {}
        self.live_preview_table = None
        self._live_preview_source_path = ""
        self._live_preview_timer = QTimer(self); self._live_preview_timer.setSingleShot(True)
        self._live_preview_timer.timeout.connect(self._refresh_live_preview)
        
        self._ocr_thread = None
        self._ocr_worker = None
        self._full_parse_worker = None
        
        self._build_ui()
        if self.selection_only:
            self.btn_save.setText(
                action_text or "Se\u00e7ilenleri Sipari\u015fe Aktar"
            )
        QTimer.singleShot(0, self.showMaximized)

    def _is_automotive(self):
        try:
            return self.db.get_setting("sector") == "otomotiv"
        except Exception:
            return False

    @staticmethod
    def _is_retired_import_column(value):
        normalized = re.sub(r"\s+", " ", str(value or "").strip()).casefold()
        return normalized in {"aydin", "merkez"}

    def _filter_source_columns(self, columns):
        return [
            column
            for column in list(columns or [])
            if not self._is_retired_import_column(column)
        ]

    def _filter_mapping(self, mapping):
        visible_columns = set(self.source_columns)
        return {
            field: source
            for field, source in dict(mapping or {}).items()
            if source in visible_columns
        }

    def _recover_if_empty_result(self):
        if not self.parse_result and getattr(self, "db", None):
            pass

    def _refresh_from_parse_result(self, parse_result):
        self.parse_result = parse_result or {}
        self.source_columns = self._filter_source_columns(
            self.parse_result.get("detected_columns") or []
        )
        self.raw_rows = list(self.parse_result.get("raw_rows") or [])
        if not self.source_columns and self.raw_rows:
            self.source_columns = self._filter_source_columns(
                StockImportParser._detect_columns_from_rows(self.raw_rows)
            )
        self.current_mapping = self._filter_mapping(
            self.parse_result.get("suggested_mapping") or {}
        )
        if not self.current_mapping and self.source_columns:
            self.current_mapping = self._filter_mapping(
                StockImportParser.build_profile_mapping(
                    self.source_columns,
                    self.current_profile,
                )
            )
        
        self._col_picker_role_map = {}
        self._col_picker_raw_columns = []
        self._col_picker_click_counts = []
        
        self.mapping_widgets = {}
        self._clear_content_layout()
        self._build_ui()

    def _clear_content_layout(self):
        layout = getattr(self, "content_layout", None)
        if not layout: return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def closeEvent(self, event):
        self._cleanup_pdf_temp()
        if self._ocr_thread and self._ocr_thread.isRunning():
            self._ocr_thread.quit(); self._ocr_thread.wait(1000)
        if self._full_parse_worker and self._full_parse_worker.isRunning():
            self._full_parse_worker.stop(); self._full_parse_worker.wait(1000)
        super().closeEvent(event)
