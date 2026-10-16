# -*- coding: utf-8 -*-

"""
Hizmet Tanımları Sayfası
- Inline form kaldırıldı
- Modern Add/Edit dialog akışı
- Tekli/çoklu silme
- Excel içe/dışa aktarma (TR sayı parse esnek)
"""

import re
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QItemSelectionModel
from PyQt6.QtGui import QAction, QColor, QFont, QPainter, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QBoxLayout,
    QLabel,
    QLineEdit,
    QLayout,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QAbstractItemView,
    QComboBox,
    QCheckBox,
    QInputDialog,
    QSizePolicy,
)



from src.ui.dialogs.add_service_definition_dialog import AddServiceDefinitionDialog
from src.ui.dialogs.service_import_preview_dialog import ServiceImportPreviewDialog
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.audit_logger import get_audit_logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_error, show_info, show_success, show_warning
from src.ui.widgets.loading_overlay import LoadingOverlay
from src.ui.widgets.navigation_glyph import navigation_icon
# ServiceParseProcessWorker (spawn-process) kaldırıldı; ServiceParseWorker (QThread) kullanılıyor


class ServiceParseWorker(QThread):
    """parse_file() işlemini arka planda çalıştırır."""
    finished = pyqtSignal(dict, bool)  # (parse_result, is_auto)
    error = pyqtSignal(str)

    def __init__(self, path, is_auto):
        super().__init__()
        self.path = path
        self.is_auto = is_auto

    def run(self):
        try:
            from src.utils.stock_import_parser import StockImportParser
            result = StockImportParser.parse_file(self.path)
            self.finished.emit(result, self.is_auto)
        except Exception as e:
            self.error.emit(str(e))


class _LaborMetricCard(QFrame):
    def __init__(self, icon_kind, icon_token, parent=None):
        super().__init__(parent)
        self._watermark = navigation_icon(icon_kind, 58, icon_token).pixmap(58, 58)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setOpacity(0.25)
        painter.drawPixmap(self.width() - 66, self.height() - 64, self._watermark)
        painter.end()


class ServicesPage(QWidget):
    PAGE_SIZE = 6

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.audit_logger = get_audit_logger(db)
        self._multi_select = False
        self._selected_id: Optional[int] = None
        self.current_page = 1
        self.total_count = 0
        self._build_ui()
        self._initial_services_load_timer = QTimer(self)
        self._initial_services_load_timer.setSingleShot(True)
        self._initial_services_load_timer.timeout.connect(self.load_services)
        self._services_loaded = False
        # Modern loading overlay
        self._svc_loading_overlay = LoadingOverlay(self, text="Dosya analiz ediliyor...")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._services_loaded and not self._initial_services_load_timer.isActive():
            self._initial_services_load_timer.start(100)

    def hideEvent(self, event):
        self._initial_services_load_timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        timer = getattr(self, "_initial_services_load_timer", None)
        if timer is not None:
            timer.stop()
        super().closeEvent(event)

    def _is_automotive(self) -> bool:
        """Aktif sektörün otomotiv olup olmadığını döner."""
        try:
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _build_ui(self):
        is_auto = self._is_automotive()
        self._is_auto_mode = is_auto
        if not is_auto:
            self._build_labor_ui()
            return
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(16)
        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        if is_auto:
            title_text = "🚗 Servis ve Fiyat Yönetimi"
            sub_text   = "Otomotiv servis hizmetleri — Tablodan seçip işlem uygulayın."
        else:
            title_text = "⚙️ Hizmet ve Ücret Yönetimi"
            sub_text   = "Hizmet ekleme/düzenleme dialog ile yapılır. Tablodan seçip işlem uygulayın."

        title = QLabel(title_text)
        title.setStyleSheet(theme_qss("font-size: 25px; font-weight: 800; color: @text;"))
        sub = QLabel(sub_text)
        sub.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch()
        action_bar = QFrame()
        action_bar.setStyleSheet(theme_qss("background: transparent; border: none;"))
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        def _mkbtn(icon, tooltip):
            b = QPushButton(icon)
            b.setFixedSize(40, 40)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                theme_qss(DesignTokens.get_icon_btn_qss())
            )
            return b

        self.btn_multi = _mkbtn("\U0001f532", "\u00c7oklu Se\u00e7im")
        self.btn_multi.setCheckable(True)
        self.btn_multi.setStyleSheet(
            theme_qss(
                DesignTokens.get_icon_btn_qss()
                + "QPushButton:checked { background: @accent; color: @selection_text; }"
            )
        )
        self.btn_multi.clicked.connect(self.toggle_multiselect)

        new_icon = "\U0001f697" if is_auto else "\u2728"
        new_tip  = "Yeni Servis Ekle" if is_auto else "Yeni Hizmet Ekle"
        btn_new = _mkbtn(new_icon, new_tip)
        btn_new.clicked.connect(self.open_add_dialog)

        self.btn_edit = _mkbtn("\U0001f4dd", "Se\u00e7ileni D\u00fczenle")
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_edit.setEnabled(False)

        self.btn_delete = _mkbtn("\U0001f5d1\ufe0f", "Se\u00e7ileni Sil")
        self.btn_delete.clicked.connect(self.delete_selected_action)
        self.btn_delete.setEnabled(False)

        btn_import_smart = _mkbtn("\U0001f9e0", "Ak\u0131ll\u0131 \u0130\u00e7e Aktar")
        btn_import_smart.clicked.connect(self.smart_import)

        btn_import = _mkbtn("\U0001f4e5", "Excel \u0130\u00e7e Aktar")
        btn_import.clicked.connect(self.import_from_csv)

        btn_export = _mkbtn("\U0001f4e4", "Excel D\u0131\u015fa Aktar")
        btn_export.clicked.connect(self.export_to_csv)

        for b in (self.btn_multi, btn_new, self.btn_edit, self.btn_delete,
                  btn_import_smart, btn_import, btn_export):
            action_layout.addWidget(b)

        header.addWidget(action_bar, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        summary = QFrame()
        summary.setStyleSheet(theme_qss("QFrame { background: transparent; border: none; }"))
        summary_grid = QGridLayout(summary)
        summary_grid.setContentsMargins(0, 0, 0, 0)
        summary_grid.setHorizontalSpacing(10)
        self.summary_metric_labels = {}
        for index, (caption, value, color) in enumerate((
            ("TOPLAM HIZMET", "0", "@finance_primary"),
            ("AKTIF TANIM", "0", "@finance_secondary"),
            ("ORTALAMA FIYAT", "0.00", "@finance_tertiary"),
            ("SECILI KAYIT", "YOK", "@finance_outline"),
        )):
            card = QFrame()
            card.setStyleSheet(theme_qss(f"QFrame {{ background: @finance_surface; border: 1px solid {color}; border-radius: 8px; }}"))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 8, 12, 8)
            card_layout.setSpacing(2)
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(theme_qss("color: @text_muted; border: none;"))
            value_label = QLabel(value)
            value_label.setStyleSheet(theme_qss(f"color: {color}; border: none; font-weight: bold;"))
            card_layout.addWidget(caption_label)
            card_layout.addWidget(value_label)
            self.summary_metric_labels[caption] = value_label
            summary_grid.addWidget(card, 0, index)
        root.addWidget(summary)

        tools_card = QFrame()
        tools_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        tools_l = QHBoxLayout(tools_card)
        tools_l.setContentsMargins(14, 12, 14, 12)
        tools_l.setSpacing(10)
        self.search = QLineEdit()
        if is_auto:
            self.search.setPlaceholderText("Servis adı / araç tipi / plaka / açıklama ara...")
        else:
            self.search.setPlaceholderText("Hizmet adı / barkod / açıklama ara...")
        self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search.textChanged.connect(self._on_search_changed)
        tools_l.addWidget(self.search, 1)
        root.addWidget(tools_card)

        # Sektöre göre tablo sütunları
        self._is_auto_mode = is_auto
        if is_auto:
            col_headers = ["ID", "Barkod/Kod", "Servis Adı", "Birim Fiyat", "Açıklama",
                           "Araç Tipi", "Marka", "Model", "Yıl"]
        else:
            col_headers = ["ID", "Barkod", "Hizmet Adı", "Birim Fiyat", "Açıklama"]

        if not is_auto:
            col_headers = [
                "ID",
                "\u0130\u015f\u00e7ilik Ad\u0131",
                "TL",
                "Dolar (Anl\u0131k Kur)",
                "Euro (Anl\u0131k Kur)",
                "Durum",
                "D\u00fczenle",
                "Sil",
            ]

        self.table = QTableWidget()
        self.table.setObjectName("ServicesTable")
        self.table.setColumnCount(len(col_headers))
        self.table.setHorizontalHeaderLabels(col_headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        if not is_auto:
            self.table.setShowGrid(False)
        self.table.setMouseTracking(False)
        self.table.viewport().setMouseTracking(False)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setStyleSheet(
            theme_qss(
                DesignTokens.get_table_qss()
                + "QTableWidget#ServicesTable::item:hover { background-color: transparent; color: @text; }"
                + "QTableWidget#ServicesTable::item:selected:hover { background-color: @selection_bg; color: @selection_text; }"
            )
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 70)
        if not is_auto:
            self.table.setColumnHidden(0, True)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            for column, width in ((2, 150), (3, 150), (4, 150), (5, 120), (6, 128), (7, 116)):
                self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(column, width)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemSelectionChanged.connect(self._sync_selected_id)
        root.addWidget(self.table, 1)
        self.empty_state = EmptyState(
            "Henüz hizmet yok",
            "Kaydedilmiş bir hizmet tanımı bulunamadı.",
            parent=self,
        )
        self.empty_state.hide()
        root.addWidget(self.empty_state, 1)

        footer = QHBoxLayout()
        self.lbl_page_info = QLabel("")
        footer.addWidget(self.lbl_page_info)
        footer.addStretch()
        self.btn_previous = QPushButton("\u00d6nceki")
        self.btn_next = QPushButton("Sonraki")
        self.lbl_page = QLabel("1")
        self.btn_previous.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        page_button_qss = theme_qss(
            """
            QPushButton {
                min-width: 86px;
                min-height: 32px;
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                font-weight: 700;
                padding: 4px 10px;
            }
            QPushButton:hover {
                border-color: @accent;
                background: @surface;
            }
            QPushButton:disabled {
                background: @surface;
                color: @text_muted;
                border-color: @border;
            }
            """
        )
        self.btn_previous.setStyleSheet(page_button_qss)
        self.btn_next.setStyleSheet(page_button_qss)
        footer.addWidget(self.btn_previous)
        footer.addWidget(self.lbl_page)
        footer.addWidget(self.btn_next)
        root.addLayout(footer)
        for widget in (
            self.lbl_page_info,
            self.btn_previous,
            self.lbl_page,
            self.btn_next,
        ):
            widget.setVisible(not is_auto)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not getattr(self, "_is_auto_mode", True) and hasattr(self, "table"):
            self._fit_labor_table()
            compact = self.width() < 1150
            mobile = self.width() < 700
            if mobile != getattr(self, "_labor_mobile", None):
                self._labor_mobile = mobile
                QTimer.singleShot(0, lambda mobile=mobile: self._apply_labor_responsive(mobile))
            if compact != getattr(self, "_labor_compact", None):
                self._labor_compact = compact
                QTimer.singleShot(0, lambda compact=compact: self._apply_labor_compact(compact))

    def _apply_labor_responsive(self, mobile):
        self.labor_root_layout.setContentsMargins(
            12, 12, 12, 10
        ) if mobile else self.labor_root_layout.setContentsMargins(20, 23, 20, 14)
        self.labor_root_layout.setSpacing(8 if mobile else 14)
        self.labor_header_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        self.labor_header_layout.setStretch(0, 0 if mobile else 1)
        self.labor_header_layout.setStretch(1, 0)
        self.labor_header_actions.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.labor_footer_layout.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        self.labor_footer_controls.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_page_info.setWordWrap(mobile)
        self.labor_title_row.setDirection(
            QBoxLayout.Direction.TopToBottom if mobile
            else QBoxLayout.Direction.LeftToRight
        )
        for spacer, desktop_size in (
            (self._labor_header_gap, 19),
            (self._labor_summary_gap, 19),
            (self._labor_table_gap, 44),
        ):
            spacer.changeSize(
                0, 8 if mobile else desktop_size,
                QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed,
            )
        while self.labor_summary_grid.count():
            self.labor_summary_grid.takeAt(0)
        self.labor_summary_grid.setHorizontalSpacing(8 if mobile else 16)
        self.labor_summary_grid.setVerticalSpacing(8 if mobile else 0)
        for column in range(4):
            self.labor_summary_grid.setColumnStretch(column, 0)
        for index, card in enumerate(self.labor_metric_cards):
            row, column = divmod(index, 2) if mobile else (0, index)
            card.setMinimumWidth(0)
            card.setMinimumHeight(146 if mobile else 122)
            self.labor_summary_grid.addWidget(card, row, column)
            self.labor_summary_grid.setColumnStretch(column, 1)
        self.labor_summary_grid.invalidate()
        self.labor_root_layout.invalidate()
        self.labor_root_layout.activate()

    def _fit_labor_table(self):
        if getattr(self, "_is_auto_mode", True) or not hasattr(self, "table"):
            return
        natural_height = 76 + self.table.rowCount() * 100
        mobile = self.width() < 700
        available_height = max(160 if mobile else 280, self.height() - (664 if mobile else 430))
        self.table.setFixedHeight(min(natural_height, available_height))

    def _apply_labor_compact(self, compact):
        self.btn_bulk_price.setToolTip("Toplu Fiyat G\u00fcncelle / Enflasyon Fark\u0131")
        self.btn_new_labor.setToolTip("Yeni Hizmet & \u0130\u015f\u00e7ilik Ekle")
        if compact:
            self.btn_bulk_price.setText("\u2197")
            self.btn_bulk_price.setFixedWidth(42)
            self.btn_new_labor.setText("+")
            self.btn_new_labor.setFixedWidth(42)
            for column in (7, 8):
                self.table.setColumnHidden(column, True)
            for column, width in ((1, 44), (2, 92), (4, 102), (5, 64), (6, 110), (9, 78), (10, 94)):
                self.table.setColumnWidth(column, width)
            self.table.setHorizontalHeaderLabels([
                "ID", "", "KOD", "H\u0130ZMET / OPERASYON", "KATEGOR\u0130",
                "S\u00dcRE", "TABAN (TL)", "D\u00d6V\u0130Z", "KDV", "DURUM", "\u0130\u015eLEM",
            ])
            self.table.horizontalHeader().setStretchLastSection(True)
        else:
            self.btn_bulk_price.setText("\u2197  Toplu Fiyat G\u00fcncelle /\nEnflasyon Fark\u0131")
            self.btn_bulk_price.setFixedWidth(238)
            self.btn_new_labor.setText("\u2295  Yeni Hizmet &&\n\u0130\u015f\u00e7ilik Ekle")
            self.btn_new_labor.setFixedWidth(188)
            for column in (7, 8):
                self.table.setColumnHidden(column, False)
            for column, width in enumerate((48, 58, 122, 315, 104, 92, 126, 92, 54, 90, 112)):
                self.table.setColumnWidth(column, width)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.table.setHorizontalHeaderLabels([
                "ID", "", "\u0130\u015eLEM KODU", "H\u0130ZMET / OPERASYON TANIMI", "KATEGOR\u0130",
                "ORT. S\u00dcRE", "TABAN \u00dcCRET (TL)", "D\u00d6V\u0130Z BAZI", "KDV", "DURUM", "\u0130\u015eLEMLER",
            ])
            self.table.horizontalHeader().setStretchLastSection(True)
        self.search.setMinimumWidth(120 if compact else 180)
        self.search.setMaximumWidth(340 if compact else 408)
        self.category_filter.setMinimumWidth(120 if compact else 0)
        self.category_filter.setMaximumWidth(220 if compact else 0)
        self.category_filter.setVisible(compact)
        compact_widths = (76, 122, 122, 112, 104)
        desktop_widths = (102, 184, 176, 165, 154)
        for index, (pill, _key, _label) in enumerate(self.category_pills):
            pill.setVisible(not compact)
            pill.setFixedWidth(compact_widths[index] if compact else desktop_widths[index])
        self._position_labor_header_checkbox()

    def _position_labor_header_checkbox(self):
        if not hasattr(self, "header_select_all"):
            return
        header = self.table.horizontalHeader()
        section = 1
        x = header.sectionViewportPosition(section)
        x += max(0, (header.sectionSize(section) - self.header_select_all.width()) // 2)
        y = max(0, (header.height() - self.header_select_all.height()) // 2)
        self.header_select_all.move(x, y)
        self.header_select_all.raise_()

    def _set_all_labor_rows_checked(self, state):
        if state == Qt.CheckState.PartiallyChecked.value:
            return
        checked = state == Qt.CheckState.Checked.value
        if checked and not self._multi_select:
            self.btn_multi.setChecked(True)
            self.toggle_multiselect(True)
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 1)
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(checked)

    def _set_labor_row_checked(self, row, state):
        selected = state == Qt.CheckState.Checked.value
        if selected and not self._multi_select:
            self.btn_multi.setChecked(True)
            self.toggle_multiselect(True)
        index = self.table.model().index(row, 1)
        command = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
        if not selected:
            command = QItemSelectionModel.SelectionFlag.Deselect | QItemSelectionModel.SelectionFlag.Rows
        self.table.selectionModel().select(index, command)
        checked_rows = sum(
            1 for current_row in range(self.table.rowCount())
            if isinstance(self.table.cellWidget(current_row, 1), QCheckBox)
            and self.table.cellWidget(current_row, 1).isChecked()
        )
        self.header_select_all.blockSignals(True)
        target_state = (
            Qt.CheckState.Unchecked if checked_rows == 0 else
            Qt.CheckState.Checked if checked_rows == self.table.rowCount() else
            Qt.CheckState.PartiallyChecked
        )
        self.header_select_all.setCheckState(target_state)
        self.header_select_all.blockSignals(False)

    def _build_labor_ui(self):
        root = QVBoxLayout(self)
        self.labor_root_layout = root
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        root.setContentsMargins(20, 23, 20, 14)
        root.setSpacing(14)
        header = QHBoxLayout()
        self.labor_header_layout = header
        title = QLabel("Hizmet ve \u00dccret Y\u00f6netimi")
        title.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        title.setStyleSheet(theme_qss("font-size: 20px; font-weight: 800; color: @text;"))
        badge = QLabel("Standart \u0130\u015f\u00e7ilik Tarifesi")
        badge.setStyleSheet(theme_qss("color: @accent; background: @surface_alt; border: 1px solid @border; border-radius: 12px; padding: 4px 9px;"))
        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addWidget(badge)
        self.labor_title_row = title_row
        heading = QVBoxLayout()
        title_icon = QLabel("\u2699")
        title_icon.setFixedSize(32, 40)
        title_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_icon.setStyleSheet(theme_qss("QLabel { color: @accent; background: @surface_alt; border: 1px solid @border; border-radius: 9px; font-size: 17px; }"))
        title_content = QWidget()
        title_content.setMinimumWidth(0)
        title_content_layout = QVBoxLayout(title_content)
        title_content_layout.setContentsMargins(0, 0, 0, 0)
        title_content_layout.setSpacing(3)
        title_content_layout.addLayout(title_row)
        subtitle = QLabel("Servis formlar\u0131na otomatik yans\u0131yan standart i\u015f\u00e7ilik kalemleri, par\u00e7a hari\u00e7 onar\u0131m s\u00fcreleri ve KDV'li fiyat tan\u0131mlar\u0131.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        title_content_layout.addWidget(subtitle)
        title_group = QHBoxLayout()
        title_group.setSpacing(12)
        title_group.addWidget(title_icon)
        title_group.addWidget(title_content, 1)
        heading.addLayout(title_group)
        header.addLayout(heading, 1)
        self.labor_heading_layout = heading
        self.btn_bulk_price = QPushButton("\u2197  Toplu Fiyat G\u00fcncelle /\nEnflasyon Fark\u0131")
        self.btn_bulk_price.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_bulk_price.setFixedWidth(238)
        self.btn_bulk_price.setFixedHeight(56)
        self.btn_bulk_price.setStyleSheet(theme_qss("color: @text; background: @surface; border: 1px solid @border; border-radius: 9px; padding: 10px 12px; font-weight: 600;"))
        self.btn_bulk_price.clicked.connect(self.open_bulk_price_dialog)
        self.btn_new_labor = QPushButton("\u2295  Yeni Hizmet &&\n\u0130\u015f\u00e7ilik Ekle")
        self.btn_new_labor.setFixedWidth(188)
        self.btn_new_labor.setFixedHeight(56)
        self.btn_new_labor.setStyleSheet(theme_qss("QPushButton { color: @selection_text; background: @accent; border: 0; border-radius: 9px; padding: 10px 14px; font-weight: 700; }"))
        self.btn_new_labor.clicked.connect(self.open_add_dialog)
        action_group = QFrame()
        action_group.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 8px; }"))
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(2, 2, 2, 2)
        action_layout.setSpacing(0)
        for glyph, tooltip, callback in (("\u25a6", "Excel Aktar", self.export_to_csv), ("\u25a4", "PDF Fiyat Listesi", self.export_to_pdf), ("\u2399", "Yazd\u0131r", self.print_list)):
            action = QPushButton(glyph)
            action.setToolTip(tooltip)
            action.setFixedSize(27, 30)
            action.setStyleSheet(theme_qss("QPushButton { color: @text_muted; background: transparent; border: 0; font-size: 15px; } QPushButton:hover { color: @text; background: @surface_alt; border-radius: 6px; }"))
            action.clicked.connect(callback)
            action_layout.addWidget(action)
        self.btn_multi = QPushButton("\u22ef")
        self.btn_multi.setCheckable(True)
        self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im")
        self.btn_multi.clicked.connect(self.toggle_multiselect)
        self.btn_edit = QPushButton("D\u00fczenle")
        self.btn_edit.clicked.connect(self.open_edit_dialog)
        self.btn_edit.setEnabled(False)
        self.btn_delete = QPushButton("Sil")
        self.btn_delete.clicked.connect(self.delete_selected_action)
        self.btn_delete.setEnabled(False)
        self.more_menu = QMenu(self)
        self.more_menu.addAction("\u00c7oklu Se\u00e7im", self.btn_multi.click)
        self.more_menu.addAction("Se\u00e7ileni D\u00fczenle", self.open_edit_dialog)
        self.more_menu.addAction("Se\u00e7ileni Sil", self.delete_selected_action)
        self.more_menu.addSeparator()
        self.more_menu.addAction("Ak\u0131ll\u0131 \u0130\u00e7e Aktar", self.smart_import)
        self.more_menu.addAction("Excel \u0130\u00e7e Aktar", self.import_from_csv)
        more = QPushButton("\u22ef")
        more.setToolTip("Di\u011fer i\u015flemler")
        more.setMenu(self.more_menu)
        more.setFixedSize(27, 30)
        more.setStyleSheet(theme_qss("QPushButton { color: @text_muted; background: transparent; border: 0; font-size: 15px; } QPushButton::menu-indicator { image: none; width: 0; }"))
        action_layout.addWidget(more)
        self.labor_header_actions = QHBoxLayout()
        self.labor_header_actions.addWidget(self.btn_bulk_price)
        self.labor_header_actions.addWidget(self.btn_new_labor)
        self.labor_header_actions.addWidget(action_group)
        header.addLayout(self.labor_header_actions)
        root.addLayout(header)
        root.addSpacing(19)
        self._labor_header_gap = root.itemAt(root.count() - 1).spacerItem()
        summary = QGridLayout()
        self.labor_summary_grid = summary
        summary.setHorizontalSpacing(16)
        self.labor_metric_cards = []
        self.summary_metric_labels = {}
        cards = (("TOPLAM H\u0130ZMET", "0", "@accent"), ("AKT\u0130F F\u0130YAT L\u0130STES\u0130", "0", "@success"), ("ORTALAMA \u0130\u015e\u00c7\u0130L\u0130K \u00dcCRET\u0130", "0,00 \u20ba", "@finance_tertiary"), ("EN \u00c7OK KULLANILAN \u0130\u015e\u00c7\u0130L\u0130K", "Termal Macun & Fan Temizli\u011fi", "@warning"))
        metric_icons = (("bank", "accent"), ("shield", "finance_action_income"), ("money", "finance_tertiary"), ("tool", "warning"))
        for i, (caption, value, color) in enumerate(cards):
            summary.setColumnStretch(i, 1)
            card = _LaborMetricCard(*metric_icons[i])
            card.setStyleSheet(theme_qss(f"QFrame {{ background: @surface; border: 1px solid {color}; border-top: 3px solid {color}; border-radius: 12px; }}"))
            layout = QVBoxLayout(card)
            layout.setContentsMargins(14, 8, 14, 12)
            label = QLabel(caption)
            label.setWordWrap(True)
            label.setStyleSheet(theme_qss(f"color: {color}; font-size: 11px; font-weight: 700; border: 0;"))
            val = QLabel(value)
            value_size = 28 if i < 2 else (20 if i == 2 else 16)
            val.setWordWrap(i == 3)
            val.setStyleSheet(theme_qss(
                f"QLabel {{ color: @text; font-size: {value_size}px; font-weight: 800; border: 0; }}"
            ))
            card.setMinimumHeight(122)
            support = QLabel(("Katalogda kay\u0131tl\u0131" if i == 0 else "2 pasif ar\u015fivde \u00b7 Teknisyen ekranlar\u0131nda aktif" if i == 1 else "KDV Hari\u00e7 net baz \u00fccret" if i == 2 else "148 Servis Kayd\u0131     T\u00fcm i\u015flerin %34'\u00fc"))
            support.setStyleSheet(theme_qss("QLabel { color: @text_muted; font-size: 10px; border: 0; }"))
            layout.addWidget(label)
            layout.addWidget(val)
            layout.addWidget(support)
            self.summary_metric_labels[caption] = val
            summary.addWidget(card, 0, i)
            self.labor_metric_cards.append(card)
        root.addLayout(summary)
        root.addSpacing(19)
        self._labor_summary_gap = root.itemAt(root.count() - 1).spacerItem()
        tools = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Hizmet ad\u0131, i\u015flem kodu (#SRV), barkod veya a\u00e7\u0131klama ara...")
        self.search.setMinimumWidth(180)
        self.search.setMaximumWidth(408)
        self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search.textChanged.connect(self._on_search_changed)
        tools.addWidget(self.search, 1)
        self.category_filter = QComboBox()
        self.category_filter.addItem("T\u00fcm\u00fc (0)", "all")
        for text, key in (("Donan\u0131m & Lehim", "donanim"), ("Yaz\u0131l\u0131m & Kurulum", "yazilim"), ("Periyodik Bak\u0131m", "bakim"), ("Saha & Montaj", "saha")):
            self.category_filter.addItem(text, key)
        self.category_filter.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.category_filter.currentIndexChanged.connect(
            lambda index: self._set_labor_category(self.category_filter.itemData(index))
        )
        self.category_filter.hide()
        tools.addWidget(self.category_filter)
        self._labor_category = "all"
        self.category_pills = []
        for label, key in (("T\u00fcm\u00fc", "all"), ("Donan\u0131m & Lehim", "donanim"), ("Yaz\u0131l\u0131m & Kurulum", "yazilim"), ("Periyodik Bak\u0131m", "bakim"), ("Saha & Montaj", "saha")):
            pill = QPushButton(label)
            pill.setCheckable(True)
            pill.setChecked(key == "all")
            pill.setStyleSheet(theme_qss("QPushButton { color: @text_muted; background: @surface; border: 1px solid @border; border-radius: 8px; padding: 8px; font-size: 10px; } QPushButton:checked { color: @selection_text; background: @accent; border-color: @accent; }"))
            pill.clicked.connect(lambda _checked=False, selected=key: self._set_labor_category(selected))
            tools.addWidget(pill)
            self.category_pills.append((pill, key, label))
        for (pill, _key, _label), width in zip(self.category_pills, (102, 184, 176, 165, 154)):
            pill.setFixedWidth(width)
        root.addLayout(tools)
        root.addSpacing(44)
        self._labor_table_gap = root.itemAt(root.count() - 1).spacerItem()
        headers = ["ID", "\u0130\u015eLEM KODU", "H\u0130ZMET / OPERASYON TANIMI", "KATEGOR\u0130", "ORT. S\u00dcRE", "TABAN \u00dcCRET (TL)", "D\u00d6V\u0130Z BAZI", "KDV", "DURUM", "\u0130\u015eLEMLER"]
        self.table = QTableWidget(0, len(headers) + 1)
        self.table.setObjectName("ServicesTable")
        self.table.setHorizontalHeaderLabels([headers[0], "", *headers[1:]])
        self.table.verticalHeader().hide()
        self.table.setColumnHidden(0, True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setMinimumWidth(0)
        self.table.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(theme_qss("QTableWidget { background: @surface; color: @text; border: 1px solid @border; border-radius: 12px; gridline-color: transparent; } QHeaderView::section { background: @surface_alt; color: @text_muted; border: 0; border-bottom: 1px solid @border; padding: 12px 5px; font-size: 12px; font-weight: 700; } QTableWidget::item { padding: 7px; border: 0; border-bottom: 1px solid @border; } QTableWidget::item:selected { background: @selection_bg; color: @selection_text; }"))
        widths = (56, 58, 118, 324, 96, 126, 142, 82, 64, 100, 128)
        for col, width in enumerate(widths):
            self.table.setColumnWidth(col, width)
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setFixedHeight(72)
        self.header_select_all = QCheckBox(self.table.horizontalHeader().viewport())
        self.header_select_all.setAccessibleName("T\u00fcm hizmetleri se\u00e7")
        self.header_select_all.setTristate(True)
        checkbox_style = (
            "QCheckBox{margin:0;padding:0;} QCheckBox::indicator{width:16px;height:16px;"
            "border:1px solid @border;border-radius:5px;background:@surface;} "
            "QCheckBox::indicator:checked{background:@accent;border-color:@accent;}"
        )
        checkbox_style = theme_qss(checkbox_style)
        self._labor_checkbox_style = checkbox_style
        self.header_select_all.setStyleSheet(checkbox_style)
        self.header_select_all.stateChanged.connect(self._set_all_labor_rows_checked)
        self.table.horizontalHeader().sectionResized.connect(
            lambda *_args: self._position_labor_header_checkbox()
        )
        root.addWidget(self.table, 0)
        self._position_labor_header_checkbox()
        self.empty_state = EmptyState("Hen\u00fcz hizmet yok", "Kaydedilmi\u015f bir hizmet tan\u0131m\u0131 bulunamad\u0131.", parent=self)
        self.empty_state.hide()
        root.addWidget(self.empty_state, 1)
        root.addStretch(1)
        footer = QHBoxLayout()
        self.labor_footer_layout = footer
        self.lbl_page_info = QLabel("")
        self.lbl_page_info.setStyleSheet(theme_qss("color: @text_muted;"))
        footer.addWidget(self.lbl_page_info)
        self.labor_footer_controls = QHBoxLayout()
        self.btn_previous = QPushButton("\u00d6nceki")
        self.btn_next = QPushButton("Sonraki")
        self.lbl_page = QLabel("1")
        self.btn_previous.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        self.labor_footer_controls.addWidget(self.btn_previous)
        self.page_buttons = []
        for page_number in range(1, 4):
            page_button = QPushButton(str(page_number))
            page_button.setFixedSize(32, 32)
            page_button.clicked.connect(lambda _checked=False, page=page_number: self._go_to_labor_page(page))
            self.labor_footer_controls.addWidget(page_button)
            self.page_buttons.append(page_button)
        self.lbl_page.hide()
        self.labor_footer_controls.addWidget(self.btn_next)
        footer.addLayout(self.labor_footer_controls)
        root.addLayout(footer)

    def toggle_multiselect(self, checked: bool):
        self._multi_select = checked
        self.table.clearSelection()
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im Ac\u0131k")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im")
        self._sync_selected_id()

    def _sync_selected_id(self):
        rows = self._selected_rows()
        if len(rows) == 1:
            item = self.table.item(rows[0], 0)
            self._selected_id = int(item.text()) if item and item.text().isdigit() else None
        else:
            self._selected_id = None
        if hasattr(self, "summary_metric_labels"):
            selected_label = self.summary_metric_labels.get("SECILI KAYIT")
            if selected_label is not None:
                selected_label.setText(
                    str(self._selected_id) if self._selected_id is not None else "YOK"
                )
        # Sil butonu: en az 1 satır seçiliyse aktif
        has_sel = len(rows) > 0
        if hasattr(self, "btn_delete"):
            self.btn_delete.setEnabled(has_sel)
        # Düzenle butonu: yalnızca tek seçimde aktif
        if hasattr(self, "btn_edit"):
            self.btn_edit.setEnabled(len(rows) == 1)

    def _selected_rows(self) -> List[int]:
        return sorted(set(i.row() for i in self.table.selectionModel().selectedRows()))

    def _service_dict_from_row(self, row: int) -> Dict:
        if not getattr(self, "_is_auto_mode", False):
            item = self.table.item(row, 0)
            data = item.data(Qt.ItemDataRole.UserRole) if item else None
            if isinstance(data, dict):
                return dict(data)
        return {
            "id": int(self.table.item(row, 0).text()),
            "barcode": self.table.item(row, 1).text(),
            "name": self.table.item(row, 2).text(),
            "price": float(self.table.item(row, 3).data(Qt.ItemDataRole.UserRole) or 0.0),
            "description": self.table.item(row, 4).text(),
        }

    def load_services(self, filtered: Optional[List[Dict]] = None):
        timer = getattr(self, "_initial_services_load_timer", None)
        if timer is not None and timer.isActive():
            timer.stop()
        data = filtered if filtered is not None else list(self.db.get_services_list() or [])
        self._services_loaded = True
        if not getattr(self, "_is_auto_mode", False):
            self._load_labor_services(data)
            return
        self.summary_metric_labels["TOPLAM HIZMET"].setText(str(len(data)))
        self.summary_metric_labels["AKTIF TANIM"].setText(str(len(data)))
        prices = [float(item.get("price", 0) or 0) if isinstance(item, dict) else float(item[2] or 0) for item in data]
        average = sum(prices) / len(prices) if prices else 0.0
        self.summary_metric_labels["ORTALAMA FIYAT"].setText(f"{average:,.2f}")
        self.table.setRowCount(0)
        for r, s in enumerate(data):
            self.table.insertRow(r)
            sid     = s["id"]          if isinstance(s, dict) else s[0]
            name    = s["name"]        if isinstance(s, dict) else (s[1] if len(s) > 1 else "")
            price   = s["price"]       if isinstance(s, dict) else (s[2] if len(s) > 2 else 0)
            desc    = s.get("description", "") if isinstance(s, dict) else (s[3] if len(s) > 3 else "")
            barcode = s.get("barcode", "")     if isinstance(s, dict) else (s[4] if len(s) > 4 else "")

            self.table.setItem(r, 0, QTableWidgetItem(str(sid)))
            self.table.setItem(r, 1, QTableWidgetItem(str(barcode or "")))
            self.table.setItem(r, 2, QTableWidgetItem(str(name or "")))
            p_item = QTableWidgetItem(CurrencyHelper.format_amount(float(price or 0.0)))
            p_item.setData(Qt.ItemDataRole.UserRole, float(price or 0.0))
            self.table.setItem(r, 3, p_item)
            self.table.setItem(r, 4, QTableWidgetItem(str(desc or "")))

            # Otomotiv ek sütunlar (5-8)
            if getattr(self, "_is_auto_mode", False):
                vtype = s.get("vehicle_type", "") if isinstance(s, dict) else ""
                vbrand = s.get("vehicle_brand", "") if isinstance(s, dict) else ""
                vmodel = s.get("vehicle_model", "") if isinstance(s, dict) else ""
                vyear  = s.get("vehicle_year", "") if isinstance(s, dict) else ""
                self.table.setItem(r, 5, QTableWidgetItem(str(vtype  or "")))
                self.table.setItem(r, 6, QTableWidgetItem(str(vbrand or "")))
                self.table.setItem(r, 7, QTableWidgetItem(str(vmodel or "")))
                self.table.setItem(r, 8, QTableWidgetItem(str(vyear  or "")))

        self._sync_selected_id()
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)

    def _load_labor_services(self, data):
        if not getattr(self, "_is_auto_mode", False):
            self._render_labor_services(data)
            return
        self.total_count = len(data)
        self.summary_metric_labels["TOPLAM HIZMET"].setText(str(self.total_count))
        self.summary_metric_labels["AKTIF TANIM"].setText(str(sum(1 for item in data if bool(item.get("is_active", 1)))))
        average = sum(float(item.get("price_try", 0) or 0) for item in data) / self.total_count if self.total_count else 0.0
        self.summary_metric_labels["ORTALAMA FIYAT"].setText(f"{average:,.2f}")
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * self.PAGE_SIZE
        page_rows = data[start:start + self.PAGE_SIZE]
        usd_rate = CurrencyHelper._get_rate(self.db, "USD")
        eur_rate = CurrencyHelper._get_rate(self.db, "EUR")
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for row_index, service in enumerate(page_rows):
            self.table.insertRow(row_index)
            self.table.setRowHeight(row_index, 46)
            item_id = QTableWidgetItem(str(service.get("id", "")))
            item_id.setData(Qt.ItemDataRole.UserRole, dict(service))
            self.table.setItem(row_index, 0, item_id)
            self.table.setItem(
                row_index,
                1,
                QTableWidgetItem(str(service.get("name", "") or "")),
            )
            try_value = float(service.get("price_try", 0) or 0)
            prices = (
                (try_value, "TRY", False),
                (try_value / usd_rate if usd_rate > 0 else None, "USD", True),
                (try_value / eur_rate if eur_rate > 0 else None, "EUR", True),
            )
            for offset, (value, code, is_live_rate) in enumerate(prices, start=2):
                display = f"{value:,.2f} {code}" if value is not None else f"-- {code}"
                price_item = QTableWidgetItem(display)
                if value is not None:
                    price_item.setData(Qt.ItemDataRole.UserRole, value)
                if is_live_rate and value is not None:
                    rate = usd_rate if code == "USD" else eur_rate
                    price_item.setToolTip(
                        f"Anl\u0131k kur: 1 {code} = {rate:,.4f} TRY"
                    )
                self.table.setItem(row_index, offset, price_item)
            is_active = bool(service.get("is_active", 1))
            status_item = QTableWidgetItem("Aktif" if is_active else "Pasif")
            status_item.setData(Qt.ItemDataRole.UserRole, int(is_active))
            self.table.setItem(row_index, 5, status_item)

            edit_button = self._make_row_action_button("D\u00fczenle", "edit")
            edit_button.clicked.connect(
                lambda _checked=False, sid=service.get("id"): self._edit_labor_row(sid)
            )
            self.table.setCellWidget(row_index, 6, edit_button)
            delete_button = self._make_row_action_button("Sil", "delete")
            delete_button.clicked.connect(
                lambda _checked=False, sid=service.get("id"): self._delete_labor_row(sid)
            )
            self.table.setCellWidget(row_index, 7, delete_button)
        self.table.setSortingEnabled(True)
        has_rows = bool(page_rows)
        self.table.setVisible(has_rows)
        self.empty_state.setVisible(not has_rows)
        first = start + 1 if self.total_count else 0
        last = min(start + len(page_rows), self.total_count)
        self.lbl_page_info.setText(
            f"{self.total_count} kay\u0131ttan {first} - {last} aras\u0131 g\u00f6steriliyor."
        )
        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        self._sync_selected_id()

    def _render_labor_services(self, data):
        data = sorted(data, key=lambda item: int(item.get("id", 0) or 0))
        self.total_count = len(data)
        active_count = sum(1 for item in data if bool(item.get("is_active", 1)))
        self.summary_metric_labels["TOPLAM H\u0130ZMET"].setText(str(self.total_count))
        self.summary_metric_labels["AKT\u0130F F\u0130YAT L\u0130STES\u0130"].setText(str(active_count))
        average = sum(float(item.get("price_try", 0) or 0) for item in data) / self.total_count if self.total_count else 0
        average_display = f"{average:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
        self.summary_metric_labels["ORTALAMA \u0130\u015e\u00c7\u0130L\u0130K \u00dcCRET\u0130"].setText(f"{average_display} \u20ba  ~ $27.10")
        self.category_filter.setItemText(0, f"T\u00fcm\u00fc ({self.total_count})")
        categories = {"Donan\u0131m & Lehim": "donanim", "Yaz\u0131l\u0131m & Kurulum": "yazilim", "Periyodik Bak\u0131m": "bakim", "Saha & Montaj": "saha"}
        selected = self.category_filter.currentData()
        category_counts = {name: sum(1 for item in data if item.get("service_category") == name) for name in categories}
        for index, name in enumerate(categories, 1):
            self.category_filter.setItemText(index, f"{name} ({category_counts[name]})")
        self.category_filter.blockSignals(True)
        if selected:
            index = self.category_filter.findData(selected)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
        self.category_filter.blockSignals(False)
        for pill, key, label in getattr(self, "category_pills", []):
            category_name = next((name for name, key_value in categories.items() if key_value == key), None)
            count = self.total_count if key == "all" else category_counts.get(category_name, 0)
            pill.setText(f"{label.replace('&', '&&')} ({count})")
            pill.setChecked(key == getattr(self, "_labor_category", "all"))
        pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(max(1, self.current_page), pages)
        start = (self.current_page - 1) * self.PAGE_SIZE
        visible = data[start:start + self.PAGE_SIZE]
        usd_rate = CurrencyHelper._get_rate(self.db, "USD")
        self.table.setSortingEnabled(False)
        self.header_select_all.blockSignals(True)
        self.header_select_all.setCheckState(Qt.CheckState.Unchecked)
        self.header_select_all.blockSignals(False)
        self.table.setRowCount(0)
        for row, service in enumerate(visible):
            self.table.insertRow(row)
            self.table.setRowHeight(row, 100)
            usd_price = float(service.get("price_usd", 0) or 0) or (float(service.get("price_try", 0) or 0) / usd_rate if usd_rate else 0)
            try_value = float(service.get("price_try", 0) or 0)
            try_display = f"{try_value:,.2f}".replace(",", "TEMP").replace(".", ",").replace("TEMP", ".")
            values = [str(service.get("id", "")), "", str(service.get("barcode") or f"#SRV-{int(service.get('id') or 0):03d}"), str(service.get("name", "")), str(service.get("service_category", "Donan\u0131m & Lehim")), f"{int(service.get('duration_minutes', 60) or 60)} Dk", f"{try_display} \u20ba", f"${usd_price:,.2f}" if usd_price else "--", f"%{float(service.get('vat_rate', 20) or 20):g}", "Aktif" if service.get("is_active", 1) else "Pasif", ""]
            for col, value in enumerate(values[:9]):
                if col in (3, 4, 9):
                    continue
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, dict(service))
                if col == 3 and service.get("description"):
                    item.setToolTip(str(service["description"]))
                if col == 2:
                    item.setForeground(QColor(tc("accent")))
                    item.setFont(QFont("JetBrains Mono", 10))
                elif col == 6:
                    item.setFont(QFont(DesignTokens.FONT_NAME, 11, QFont.Weight.Bold))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif col in (7, 8):
                    item.setFont(QFont("JetBrains Mono", 10))
                    item.setForeground(QColor(tc("text_muted")))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, col, item)
            checkbox = QCheckBox()
            checkbox.setStyleSheet(self._labor_checkbox_style + "QCheckBox{margin-left:12px;}")
            checkbox.stateChanged.connect(
                lambda state, selected_row=row: self._set_labor_row_checked(selected_row, state)
            )
            self.table.setCellWidget(row, 1, checkbox)
            duration_cell = QWidget()
            duration_cell_layout = QHBoxLayout(duration_cell)
            duration_cell_layout.setContentsMargins(4, 0, 4, 0)
            duration_cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            duration_card = QFrame()
            duration_card.setFixedSize(76, 46)
            duration_card.setStyleSheet(theme_qss(
                "QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"
            ))
            duration_layout = QHBoxLayout(duration_card)
            duration_layout.setContentsMargins(7, 3, 7, 3)
            duration_layout.setSpacing(5)
            duration_icon = QLabel()
            duration_icon.setPixmap(navigation_icon("clock", 12, "text_muted").pixmap(12, 12))
            duration_layout.addWidget(duration_icon)
            duration_text = QLabel(values[5])
            duration_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
            duration_text.setStyleSheet(theme_qss(
                "color: @text; background: transparent; border: none; font-size: 10px;"
            ))
            duration_layout.addWidget(duration_text, 1)
            duration_cell_layout.addWidget(duration_card)
            self.table.setCellWidget(row, 5, duration_cell)
            detail = QWidget()
            detail_layout = QVBoxLayout(detail)
            detail_layout.setContentsMargins(2, 3, 2, 3)
            detail_layout.setSpacing(3)
            name_label = QLabel(str(service.get("name", "")))
            name_label.setMinimumWidth(0)
            name_label.setWordWrap(True)
            name_label.setStyleSheet(theme_qss("color: @text; background: transparent; font-size: 13px; font-weight: 600;"))
            name_row = QHBoxLayout()
            name_row.setContentsMargins(0, 0, 0, 0)
            name_row.addWidget(name_label, 1)
            badge_text = "Pop\u00fcler" if service.get("barcode") == "#SRV-101" else ("\u0130leri D\u00fczey" if service.get("barcode") == "#SRV-204" else "")
            if badge_text:
                badge = QLabel(badge_text)
                badge.setStyleSheet(theme_qss("QLabel { color: @success; background: @success_bg; border: 1px solid @success; border-radius: 4px; padding: 2px 5px; font-size: 9px; }"))
                name_row.addWidget(badge)
            name_row.addStretch()
            description = QLabel(str(service.get("description", "")))
            description.setWordWrap(True)
            description.setMaximumHeight(32)
            description.setStyleSheet(theme_qss("QLabel { color: @text_muted; font-size: 11px; }"))
            detail_layout.addLayout(name_row)
            detail_layout.addWidget(description)
            self.table.setCellWidget(row, 3, detail)
            category_label = QLabel(str(service.get("service_category", "Donan\u0131m & Lehim")))
            category_color = {"Periyodik Bak\u0131m": "@warning", "Donan\u0131m & Lehim": "@danger", "Yaz\u0131l\u0131m & Kurulum": "@accent", "Saha & Montaj": "@success"}.get(service.get("service_category"), "@text_muted")
            color_value = QColor(tc(category_color[1:]))
            color_value.setAlpha(30)
            category_background = "rgba({}, {}, {}, {})".format(*color_value.getRgb())
            category_label.setStyleSheet(theme_qss(
                f"QLabel {{ color: {category_color}; background: {category_background}; "
                f"border: 1px solid {category_color}; border-radius: 5px; padding: 4px; font-size: 10px; }}"
            ))
            category_label.setWordWrap(True)
            category_label.setFixedSize(96, 46)
            category_cell = QWidget()
            category_cell_layout = QHBoxLayout(category_cell)
            category_cell_layout.setContentsMargins(0, 0, 0, 0)
            category_cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            category_cell_layout.addWidget(category_label)
            self.table.setCellWidget(row, 4, category_cell)
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(2, 4, 2, 4)
            for icon_kind, tip, callback in (("pencil", "D\u00fczenle", lambda sid=service.get("id"): self._edit_labor_row(sid)), ("copy", "Kopyala", lambda sid=service.get("id"): self._duplicate_labor_row(sid)), ("trash", "Sil", lambda sid=service.get("id"): self._delete_labor_row(sid))):
                button = QPushButton()
                button.setAccessibleName(tip)
                button.setIcon(navigation_icon(icon_kind, 16, "text_muted"))
                button.setToolTip(tip)
                button.setFixedSize(30, 30)
                button.setStyleSheet(theme_qss("QPushButton { color: @text_muted; background: transparent; border: 0; } QPushButton:hover { color: @accent; background: @surface_alt; border-radius: 6px; }"))
                button.clicked.connect(callback)
                actions_layout.addWidget(button)
            self.table.setCellWidget(row, 10, actions)
            toggle = QPushButton("\u25cf  Aktif" if service.get("is_active", 1) else "\u25cf  Pasif")
            toggle.setCheckable(True)
            toggle.setChecked(not bool(service.get("is_active", 1)))
            toggle.setFixedSize(66, 30)
            toggle.setStyleSheet(theme_qss("QPushButton { color: @success; background: @success_bg; border: 1px solid @success; border-radius: 12px; padding: 4px 8px; } QPushButton:checked { color: @text_muted; background: @surface_alt; border-color: @border; }"))
            toggle.clicked.connect(lambda checked, sid=service.get("id"): self._toggle_labor_active(sid, not checked))
            self.table.setCellWidget(row, 9, toggle)
        self._fit_labor_table()
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.table.setVisible(bool(visible))
        self.empty_state.setVisible(not bool(visible))
        self.lbl_page_info.setText(f"Toplam {self.total_count} kay\u0131ttan {start + 1 if data else 0} - {min(start + len(visible), self.total_count)} aras\u0131 g\u00f6steriliyor    \u2022    TCMB Kur Senkronu: 1 USD = {usd_rate:.2f} \u20ba")
        self.lbl_page.setText(f"{self.current_page} / {pages}")
        for number, button in enumerate(self.page_buttons, 1):
            button.setVisible(number <= pages)
            button.setStyleSheet(theme_qss("QPushButton { color: @text; background: @surface; border: 1px solid @border; border-radius: 7px; }" + ("QPushButton { color: @selection_text; background: @accent; border-color: @accent; }" if number == self.current_page else "")))
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < pages)
        self._sync_selected_id()

    def _set_labor_category(self, category):
        self._labor_category = category
        if hasattr(self, "category_filter") and self.category_filter.currentData() != category:
            self.category_filter.blockSignals(True)
            index = self.category_filter.findData(category)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
            self.category_filter.blockSignals(False)
        for pill, key, _label in getattr(self, "category_pills", []):
            pill.setChecked(key == category)
        self.current_page = 1
        self._apply_filter()

    def _go_to_labor_page(self, page):
        self.current_page = page
        self._apply_filter()

    def _toggle_labor_active(self, service_id, active):
        row = next((i for i in range(self.table.rowCount()) if self.table.item(i, 0).text() == str(service_id)), -1)
        if row >= 0:
            data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.db.update_service(service_id, data.get("name"), data.get("price", data.get("price_try", 0)), data.get("description", ""), data.get("barcode", ""), data.get("currency", "TRY"), price_try=data.get("price_try", 0), price_usd=data.get("price_usd", 0), price_eur=data.get("price_eur", 0), is_active=active, service_category=data.get("service_category", "Donan\u0131m & Lehim"), duration_minutes=data.get("duration_minutes", 60), vat_rate=data.get("vat_rate", 20))
            self.load_services()

    def _duplicate_labor_row(self, service_id):
        service = next((item for item in self.db.get_services_list() if str(item.get("id")) == str(service_id)), None)
        if service:
            service["name"] = f"{service['name']} (Kopya)"
            service["barcode"] = ""
            self.db.add_service(service["name"], service.get("price_try", 0), service.get("description", ""), "", "TRY", price_try=service.get("price_try", 0), price_usd=service.get("price_usd", 0), price_eur=service.get("price_eur", 0), is_active=service.get("is_active", 1), service_category=service.get("service_category", "Donan\u0131m & Lehim"), duration_minutes=service.get("duration_minutes", 60), vat_rate=service.get("vat_rate", 20))
            self.load_services()

    def open_bulk_price_dialog(self):
        percentage, accepted = QInputDialog.getDouble(self, "Toplu Fiyat G\u00fcncelle", "Fiyat de\u011fi\u015fimi (%)", 0, -100, 1000, 2)
        if not accepted:
            return
        for service in self.db.get_services_list():
            price = float(service.get("price_try", 0) or 0) * (1 + percentage / 100)
            self.db.update_service(service["id"], service["name"], price, service.get("description", ""), service.get("barcode", ""), "TRY", price_try=price, is_active=service.get("is_active", 1))
        self.load_services()

    @staticmethod
    def _make_row_action_button(text: str, action: str) -> QPushButton:
        button = QPushButton(text)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(34)
        button.setStyleSheet(
            theme_qss(
                "QPushButton { border: none; border-radius: 6px; font-weight: 700; padding: 0 10px; }"
                + (
                    "QPushButton { background: @accent; color: @selection_text; }"
                    "QPushButton:hover { background: @accent_hover; }"
                    if action == "edit"
                    else "QPushButton { background: @danger; color: @selection_text; }"
                    "QPushButton:hover { background: @danger_bg; color: @danger; }"
                )
            )
        )
        return button

    def _edit_labor_row(self, service_id):
        self._select_row_by_service_id(service_id)
        self.open_edit_dialog()

    def _delete_labor_row(self, service_id):
        self._select_row_by_service_id(service_id)
        self.delete_selected_action()

    def _select_row_by_service_id(self, service_id):
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and str(item.text()) == str(service_id):
                self.table.selectRow(row)
                break

    def _on_search_changed(self):
        self.current_page = 1
        self._apply_filter()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._apply_filter()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        if self.current_page < total_pages:
            self.current_page += 1
            self._apply_filter()

    def _apply_filter(self):
        q = self.search.text().strip().lower()
        category = getattr(self, "_labor_category", "all")
        category_names = {"donanim": "Donan\u0131m & Lehim", "yazilim": "Yaz\u0131l\u0131m & Kurulum", "bakim": "Periyodik Bak\u0131m", "saha": "Saha & Montaj"}
        raw = list(self.db.get_services_list() or [])
        out = []
        for s in raw:
            name = str(s["name"] if isinstance(s, dict) else s[1] or "").lower()
            desc = str((s.get("description", "") if isinstance(s, dict) else (s[3] if len(s) > 3 else "")) or "").lower()
            barcode = str((s.get("barcode", "") if isinstance(s, dict) else (s[4] if len(s) > 4 else "")) or "").lower()
            category_match = category in (None, "all") or s.get("service_category", "Donan\u0131m & Lehim") == category_names.get(category)
            if category_match and (not q or q in name or q in desc or q in barcode):
                out.append(s)
        self.load_services(out)

    def open_documents_center(self):
        UnifiedDocumentsCenterDialog(self.db, None, self).exec()

    def open_add_dialog(self):
        dlg = AddServiceDefinitionDialog(self)
        if dlg.exec():
            d = dlg.get_data()
            if not d["name"]:
                show_warning(self, "Hizmet adı boş olamaz.")
                return
            sid = self.db.add_service(
                d["name"],
                d["price"],
                d["description"],
                d["barcode"],
                d["currency"],
                price_try=d.get("price_try"),
                price_usd=d.get("price_usd"),
                price_eur=d.get("price_eur"),
                is_active=d.get("is_active", 1),
                service_category=d.get("service_category", "Donan\u0131m & Lehim"),
                duration_minutes=d.get("duration_minutes", 60),
                vat_rate=d.get("vat_rate", 20),
            )
            if sid:
                self.audit_logger.log_action("services", "INSERT", f"Hizmet eklendi: {d['name']}")
                show_success(self, "Hizmet eklendi.")
                self.load_services()
            else:
                show_error(self, "Hizmet eklenemedi. Aynı isim/barkod kontrol edin.")

    def open_edit_dialog(self):
        rows = self._selected_rows()
        if len(rows) != 1:
            show_warning(self, "Düzenlemek için tek bir satır seçin.")
            return
        item = self._service_dict_from_row(rows[0])
        dlg = AddServiceDefinitionDialog(self, service_data=item)
        if dlg.exec():
            d = dlg.get_data()
            ok = self.db.update_service(
                item["id"],
                d["name"],
                d["price"],
                d["description"],
                d["barcode"],
                d["currency"],
                price_try=d.get("price_try"),
                price_usd=d.get("price_usd"),
                price_eur=d.get("price_eur"),
                is_active=d.get("is_active", 1),
                service_category=d.get("service_category", "Donan\u0131m & Lehim"),
                duration_minutes=d.get("duration_minutes", 60),
                vat_rate=d.get("vat_rate", 20),
            )
            if ok:
                self.audit_logger.log_action("services", "UPDATE", f"Hizmet güncellendi: {item['id']}")
                show_info(self, "Hizmet güncellendi.")
                self.load_services()
            else:
                show_error(self, "Hizmet güncellenemedi.")

    def delete_selected_action(self):
        rows = self._selected_rows()
        if not rows:
            show_warning(self, "Silmek için satır seçin.")
            return
        if len(rows) == 1:
            item = self._service_dict_from_row(rows[0])
            txt = f"'{item['name']}' hizmeti silinsin mi"
        else:
            txt = f"{len(rows)} adet hizmet silinsin mi Bu işlem geri alınamaz."
        if SimpleConfirmDialog(parent=self, title="Onay", text=txt).exec() != 1:
            return
        ok_count = 0
        for r in rows:
            sid = self.table.item(r, 0).text()
            if self.db.delete_service(sid):
                ok_count += 1
        self.audit_logger.log_action("services", "DELETE", f"Toplu silme: {ok_count} kayıt")
        show_success(self, f"{ok_count} kayıt silindi.")
        self.load_services()

    def show_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=140):
            return
        idx = self.table.indexAt(pos)
        if not idx.isValid():
            return
        if not self.table.item(idx.row(), 0).isSelected():
            self.table.selectRow(idx.row())
        menu = QMenu(self)
        a_new = QAction("➕ Yeni Hizmet", self)
        a_edit = QAction("📝 Düzenle", self)
        a_del = QAction("🗑️ Sil", self)
        a_export = QAction("📤 Excel Aktar", self)
        a_pdf = QAction("📄 PDF Olarak Kaydet", self)
        a_print = QAction("🖨️ Yazdır", self)
        a_new.triggered.connect(self.open_add_dialog)
        a_edit.triggered.connect(self.open_edit_dialog)
        a_del.triggered.connect(self.delete_selected_action)
        a_export.triggered.connect(self.export_to_excel)
        a_pdf.triggered.connect(self.export_to_pdf)
        a_print.triggered.connect(self.print_list)
        menu.addAction(a_new)
        menu.addAction(a_edit)
        menu.addAction(a_del)
        menu.addSeparator()
        menu.addAction(a_export)
        menu.addAction(a_pdf)
        menu.addAction(a_print)
        menu.exec(self.table.viewport().mapToGlobal(pos))

    @staticmethod
    def _parse_tl_number(raw) -> Optional[float]:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        s = str(raw).strip()
        if not s:
            return None
        s = s.replace("₺", "").replace("TL", "").replace("tl", "").replace(" ", "")
        s = re.sub(r"[^\d,.\-]", "", s)
        if not s:
            return None
        # both separators exist -> rightmost one is decimal sep
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s:
            # single comma: decimal separator
            if s.count(",") == 1:
                s = s.replace(",", ".")
            else:
                # thousands commas
                last = s.rfind(",")
                s = s[:last].replace(",", "") + "." + s[last + 1 :]
        elif "." in s and s.count(".") > 1:
            last = s.rfind(".")
            s = s[:last].replace(".", "") + "." + s[last + 1 :]
        try:
            return float(s)
        except Exception:
            return None

    def _collect_service_rows(self) -> List[Dict[str, str]]:
        if not getattr(self, "_is_auto_mode", False):
            query = self.search.text().strip().lower()
            source_rows = list(self.db.get_services_list() or [])
            if query:
                source_rows = [
                    service
                    for service in source_rows
                    if query in str(service.get("name", "")).lower()
                    or query in str(service.get("description", "")).lower()
                    or query in str(service.get("barcode", "")).lower()
                ]
            return [
                {
                    "\u0130\u015f\u00e7ilik Ad\u0131": str(service.get("name", "") or ""),
                    "TL": f"{float(service.get('price_try', 0) or 0):,.2f}",
                    "USD": f"{float(service.get('price_usd', 0) or 0):,.2f}",
                    "EURO": f"{float(service.get('price_eur', 0) or 0):,.2f}",
                    "Durum": (
                        "Aktif" if bool(service.get("is_active", 1)) else "Pasif"
                    ),
                }
                for service in source_rows
            ]
        rows: List[Dict[str, str]] = []
        headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
        for row in range(self.table.rowCount()):
            rows.append(
                {
                    headers[col]: self.table.item(row, col).text() if self.table.item(row, col) else ""
                    for col in range(self.table.columnCount())
                }
            )
        return rows

    def _build_service_html(self) -> str:
        rows = self._collect_service_rows()
        header_keys = list(rows[0].keys()) if rows else ["ID", "Barkod", "Hizmet Adı", "Birim Fiyat", "Açıklama"]
        header_html = "".join(
            f"<th style='padding:8px;border:1px solid #d9d9d9;background:#f3f4f6;'>{key}</th>"
            for key in header_keys
        )
        body_rows = []
        for row in rows:
            body_rows.append(
                "<tr>" + "".join(f"<td style='padding:6px;border:1px solid #d9d9d9;'>{value}</td>" for value in row.values()) + "</tr>"
            )
        return f"""
        <html><head><meta charset='UTF-8'></head><body>
        <h2>AYEC Pro - Hizmet Tanimlari</h2>
        <p>Tarih: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        <table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:10pt;'>
        <thead><tr>{header_html}</tr></thead>
        <tbody>{''.join(body_rows)}</tbody>
        </table></body></html>
        """

    def export_to_csv(self):
        try:
            is_auto = self._is_automotive()
            default_name = "Servis_Listesi.xlsx" if is_auto else "Hizmet_Listesi.xlsx"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Servis Listesi Dışa Aktar" if is_auto else "Hizmet Listesi Dışa Aktar",
                default_name,
                "Excel Dosyası (*.xlsx)",
            )
            if not path:
                return

            rows = list(self.db.get_services_list() or [])
            if not rows:
                show_warning(self, "Dışa aktarılacak kayıt bulunamadı.")
                return

            import pandas as pd

            dict_rows = []
            for s in rows:
                if isinstance(s, dict) or hasattr(s, "keys"):
                    dict_rows.append(dict(s))
                else:
                    dict_rows.append({
                        "id": s[0],
                        "name": s[1] if len(s) > 1 else "",
                        "price": s[2] if len(s) > 2 else 0,
                        "description": s[3] if len(s) > 3 else "",
                        "barcode": s[4] if len(s) > 4 else "",
                    })

            df = pd.DataFrame(dict_rows)
            label = getattr(self.db, "get_setting", lambda k, d: d)("currency", "TRY")

            if is_auto:
                rename_map = {
                    "id": "ID",
                    "barcode": "Barkod/Kod",
                    "name": "Servis Adı",
                    "price": f"Birim Fiyat ({label})",
                    "description": "Açıklama",
                    "vehicle_type": "Araç Tipi",
                    "vehicle_brand": "Marka",
                    "vehicle_model": "Model",
                    "vehicle_year": "Yıl",
                    "vehicle_plate": "Plaka",
                    "currency": "Para Birimi",
                }
            else:
                rename_map = {
                    "id": "ID",
                    "barcode": "Barkod",
                    "name": "Hizmet Adı",
                    "price": f"Birim Fiyat ({label})",
                    "description": "Açıklama",
                    "currency": "Para Birimi",
                }

            if not is_auto:
                if "is_active" in df.columns:
                    df["is_active"] = df["is_active"].map(
                        lambda value: "Aktif" if bool(value) else "Pasif"
                    )
                rename_map = {
                    "name": "\u0130\u015f\u00e7ilik Ad\u0131",
                    "price_try": "TL",
                    "price_usd": "USD",
                    "price_eur": "EURO",
                    "is_active": "Durum",
                    "barcode": "Barkod",
                    "description": "A\u00e7\u0131klama",
                }

            df = df.rename(columns=rename_map)
            keep_cols = [v for k, v in rename_map.items() if v in df.columns]
            df = df[keep_cols]
            df.to_excel(path, index=False)
            show_success(self, f"Dışa aktarma tamamlandı:\n{path}")
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def export_to_excel(self):
        self.export_to_csv()

    def export_to_pdf(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "PDF icin hizmet verisi bulunamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Hizmet Listesi PDF Kaydet",
                "hizmet_listesi.pdf",
                "PDF Dosyasi (*.pdf)",
            )
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_service_html())
            doc.print(printer)
            show_success(self, f"PDF olusturuldu:\n{path}")
        except Exception as e:
            show_error(self, f"PDF olusturma hatasi: {e}")

    def print_list(self):
        try:
            if self.table.rowCount() == 0:
                show_warning(self, "Yazdirilacak hizmet verisi bulunamadi.")
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_service_html())
            doc.print(printer)
            show_info(self, "Hizmet listesi yazdirmaya gonderildi.")
        except Exception as e:
            show_error(self, f"Yazdirma hatasi: {e}")

    def import_from_csv(self):
        try:
            is_auto = self._is_automotive()
            dialog_title = "Servis Listesi İçe Aktar" if is_auto else "Hizmet Listesi İçe Aktar"
            path, _ = QFileDialog.getOpenFileName(
                self, dialog_title, "", "Excel Dosyası (*.xlsx *.xls *.csv)",
            )
            if not path: return

            import pandas as pd

            df = None
            if path.endswith(".csv"):
                for enc in ["utf-8-sig", "utf-8", "cp1254", "latin-1"]:
                    for sep in [",", ";", "\t"]:
                        try:
                            temp_df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
                            if len(temp_df.columns) > 1 or (len(temp_df.columns) == 1 and sep == ","):
                                df = temp_df
                                break
                        except Exception:
                            pass
                    if df is not None: break
                if df is None:
                    try: df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
                    except Exception:
                        show_error(self, "CSV dosyası okunamadı.")
                        return
            else:
                try: df = pd.read_excel(path, dtype=str, keep_default_na=False)
                except Exception as e:
                    show_error(self, f"Excel okunamadı: {e}")
                    return

            if df is None or df.empty:
                show_error(self, "Dosya boş veya okunamadı.")
                return

            def _norm_col(c):
                c = str(c).lower().strip()
                for src_char, dst_char in [("ı","i"),("ğ","g"),("ü","u"),("ş","s"),("ö","o"),("ç","c")]:
                    c = c.replace(src_char, dst_char)
                return c.replace("_", " ").replace("-", " ")

            # Ortak alanlar
            col_map = {
                "hizmet adi": "name", "hizmet": "name", "servis adi": "name", "servis": "name",
                "ad": "name", "isim": "name", "service name": "name", "service": "name",
                "name": "name", "baslik": "name", "title": "name",
                "fiyat": "price", "tutar": "price", "birim fiyat": "price", "birim fiyat (tl)": "price",
                "ucret": "price", "price": "price", "unit price": "price", "amount": "price", "cost": "price",
                "aciklama": "description", "not": "description", "notlar": "description",
                "aciklama notlar": "description", "description": "description", "notes": "description", "desc": "description",
                "barkod": "barcode", "kod": "barcode", "referans": "barcode", "referans kodu": "barcode",
                "urun kodu": "barcode", "barcode": "barcode", "code": "barcode", "sku": "barcode",
                "para birimi": "currency", "currency": "currency", "doviz": "currency",
            }

            # Otomotiv ek alanları
            if is_auto:
                col_map.update({
                    "plaka": "vehicle_plate", "arac plaka": "vehicle_plate",
                    "vehicle plate": "vehicle_plate", "plate": "vehicle_plate",
                    "marka": "vehicle_brand", "arac marka": "vehicle_brand",
                    "vehicle brand": "vehicle_brand", "brand": "vehicle_brand",
                    "model": "vehicle_model", "arac model": "vehicle_model",
                    "vehicle model": "vehicle_model",
                    "yil": "vehicle_year", "model yili": "vehicle_year",
                    "year": "vehicle_year", "vehicle year": "vehicle_year",
                    "km": "vehicle_km", "kilometre": "vehicle_km", "odometer": "vehicle_km",
                    "arac tipi": "vehicle_type", "tip": "vehicle_type", "vehicle type": "vehicle_type",
                })

            header_found = False
            matched_cols = {}
            for col in df.columns:
                n = _norm_col(col)
                if n in col_map:
                    matched_cols[col_map[n]] = str(col)

            if "name" in matched_cols:
                header_found = True
            else:
                for idx, row in df.head(10).iterrows():
                    test_matched = {}
                    for col in df.columns:
                        n = _norm_col(str(row[col]))
                        if n in col_map:
                            test_matched[col_map[n]] = str(col)
                    if "name" in test_matched:
                        matched_cols = test_matched
                        header_found = True
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break

            if not header_found or "name" not in matched_cols:
                expected = "'Servis Adı, Fiyat, Plaka, Marka, Model'" if is_auto else "'Hizmet Adı, Fiyat, Açıklama, Barkod'"
                show_error(self, f"Dosyada 'Hizmet/Servis Adı' sütunu bulunamadı!\nBeklenen başlıklar: {expected}")
                return

            def parse_val(val, to_type=float):
                if val is None: return 0 if to_type in (int, float) else ""
                try:
                    is_missing = bool(pd.isna(val))
                except Exception:
                    is_missing = False
                if is_missing:
                    return 0 if to_type in (int, float) else ""
                val_str = str(val).strip()
                if not val_str or val_str.lower() in ["nan", "nat", "null", "none"]:
                    return 0 if to_type in (int, float) else ""
                if to_type in (int, float):
                    val_str = val_str.replace(".", "").replace(",", ".") if "," in val_str and "." in val_str else val_str.replace(",", ".")
                    try: return to_type(float(val_str))
                    except Exception: return 0 if to_type is int else 0.0
                return val_str

            def _str(row, key):
                if key not in matched_cols: return ""
                val = str(row[matched_cols[key]]).strip() if pd.notnull(row[matched_cols[key]]) else ""
                return "" if val.lower() in ("nan", "none", "null", "") else val

            success, fails = 0, 0
            for _, row in df.iterrows():
                try:
                    n_val = _str(row, "name")
                    if not n_val: continue
                    p_val   = parse_val(row[matched_cols["price"]], float) if "price" in matched_cols else 0.0
                    d_val   = _str(row, "description")
                    c_val   = _str(row, "barcode")
                    cur_val = _str(row, "currency") or "TRY"

                    # Otomotiv ek alanlar - description'a ekle
                    if is_auto:
                        plate  = _str(row, "vehicle_plate")
                        brand  = _str(row, "vehicle_brand")
                        model  = _str(row, "vehicle_model")
                        year   = _str(row, "vehicle_year")
                        km     = _str(row, "vehicle_km")
                        vtype  = _str(row, "vehicle_type")
                        # description'ı araç bilgisiyle zenginleştir
                        auto_extra = " | ".join(
                            f"{k}: {v}" for k, v in [
                                ("Plaka", plate), ("Marka", brand), ("Model", model),
                                ("Yıl", year), ("KM", km), ("Tip", vtype)
                            ] if v
                        )
                        if auto_extra and not d_val:
                            d_val = auto_extra
                        elif auto_extra:
                            d_val = f"{d_val} | {auto_extra}"

                    self.db.add_service(name=n_val, price=p_val, description=d_val, barcode=c_val, currency=cur_val)
                    success += 1
                except Exception:
                    fails += 1

            show_success(self, f"İçe aktarma tamamlandı.\nBaşarılı: {success}\nHatalı: {fails}")
            self.load_services()
        except Exception as e:
            show_error(self, f"İçe Aktarma Hatası: {e}")

    def smart_import(self):
        """Akıllı içe aktarma: Excel/CSV/PDF/Görsel/OCR destekli, önizlemeli."""
        try:
            is_auto = self._is_automotive()
            title = "Akıllı Servis İçe Aktar" if is_auto else "Akıllı Hizmet İçe Aktar"
            path, _ = QFileDialog.getOpenFileName(
                self,
                title,
                "",
                "Desteklenen Dosyalar (*.xlsx *.xls *.csv *.pdf *.docx *.jpg *.jpeg *.png *.bmp *.webp *.xml *.tif *.tiff *.ppm);;Tüm Dosyalar (*.*)",
            )
            if not path:
                return

            self._svc_loading_overlay.show_overlay("Dosya analiz ediliyor...")

            self._svc_parse_worker = ServiceParseWorker(path, is_auto)
            self._svc_parse_worker.finished.connect(self._on_svc_parse_done)
            self._svc_parse_worker.error.connect(self._on_svc_parse_error)
            self._svc_parse_worker.start()
        except Exception as e:
            show_error(self, f"Akıllı içe aktarma hatası: {e}")

    def _on_svc_parse_done(self, parse_result, is_auto):
        try:
            self._svc_loading_overlay.hide_overlay()
            dlg = ServiceImportPreviewDialog(self.db, parse_result, self, is_automotive=is_auto)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.load_services()
        except Exception as e:
            show_error(self, f"Akıllı içe aktarma hatası: {e}")

    def _on_svc_parse_error(self, err_msg):
        self._svc_loading_overlay.hide_overlay()
        show_error(self, f"Dosya analiz hatası: {err_msg}")
