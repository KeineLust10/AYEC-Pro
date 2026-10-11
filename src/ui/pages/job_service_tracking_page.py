# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMenu, QLabel, QFrame, QPushButton, QDialog,
    QGridLayout, QLineEdit, QSizePolicy, QComboBox, QFileDialog, QDateEdit, QCheckBox, QProgressBar, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QDate, QSize, QItemSelectionModel
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from datetime import datetime
import sqlite3
import html
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.logger import logger
from src.ui.widgets.empty_state import EmptyState
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon
from src.ui.widgets.reference_date_edit import ReferenceDateEdit
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel
from src.ui.pages._dashboard_utils import render_svg_icon



class JobServiceTrackingPage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.job_page = 0
        self.job_page_size = 15
        self.setup_ui()
        self._wire_ui_signals()
        self.load_jobs()
        self.load_services()
        self.update_stat_cards()
        self._refresh_metric_progress()

    def show_service_list(self, category="all"):
        """Open the service tab and apply a dashboard status filter."""
        self.tabs.setCurrentWidget(self.service_tab)
        self._service_category = str(category or "all")
        self._service_technician = ""
        self.apply_service_filter()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        report_today = QDate.currentDate()
        breadcrumb = QLabel("TEKN\u0130K SERV\u0130S MOD\u00dcL\u00dc / OPERASYONEL RAPORLAR / AYEC-Q{}-{}".format(
            (report_today.month() - 1) // 3 + 1, report_today.year()))
        breadcrumb.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:11px;font-weight:700;border:none;"))
        layout.addWidget(breadcrumb)

        header_row = QGridLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(8)

        header = QLabel("\u0130\u015f / Servis Takibi Raporlar\u0131")
        header_font = self.font()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet(theme_qss("color: @text;"))
        header_row.addWidget(header, 0, 0)
        header_row.setColumnStretch(0, 1)
        export_row = QHBoxLayout()
        self.report_date_enabled = QCheckBox("Tarih")
        self.report_date_enabled.setToolTip("Tarih aral\u0131\u011f\u0131n\u0131 i\u015f ve servis raporlar\u0131na uygula")
        export_row.addWidget(self.report_date_enabled)
        today = QDate.currentDate()
        self.report_date_from = ReferenceDateEdit(QDate(today.year(), today.month(), 1))
        self.report_date_to = ReferenceDateEdit(today)
        for date_edit in (self.report_date_from, self.report_date_to):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd.MM.yyyy")
            date_edit.setFixedWidth(116)
            date_edit.setFixedHeight(34)
            date_edit.setFont(QFont(DesignTokens.MONO_FONT_NAME))
            date_edit.setStyleSheet(theme_qss(
                'QDateEdit { background: @finance_surface_lowest; color: @finance_text; '
                'border: 1px solid @finance_outline; border-radius: 4px; padding: 0 6px; '
                'min-height: 32px; max-height: 32px; font-size: 11px; } '
                'QDateEdit::drop-down { width: 24px; background: transparent; border: none; } '
                'QDateEdit::down-arrow { image: none; width: 0; height: 0; border: none; }'
            ))
            export_row.addWidget(date_edit)

        self.btn_report = QPushButton("Rapor / Analiz")
        self.btn_report.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_report.setFixedHeight(36)
        try:
            self.btn_report.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        except Exception:
            self.btn_report.setStyleSheet(theme_qss(
                "QPushButton { background-color: @accent_hover; color: white; border-radius: 8px; padding: 6px 14px; "
                "border: none; font-weight: 600; } QPushButton:hover { background-color: @accent_pressed; }"
            ))
        self.btn_report.clicked.connect(self.show_monthly_report)
        header_row.addWidget(self.btn_report, 1, 1, Qt.AlignmentFlag.AlignLeft)
        self.btn_excel = QPushButton("Excel Ciktisi")
        self.btn_pdf = QPushButton("PDF Ozeti")
        for export_button in (self.btn_excel, self.btn_pdf):
            export_button.setFixedHeight(36)
            export_button.setStyleSheet(theme_qss(
                "QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:4px;padding:6px 12px;font-weight:700;}"
                "QPushButton:hover{background:@selection_bg;color:@accent;}"
            ))
            export_row.addWidget(export_button)
        header_row.addLayout(export_row, 0, 1)
        self.btn_excel.clicked.connect(self.export_report_excel)
        self.btn_pdf.clicked.connect(self.export_report_pdf)

        subtitle = QLabel("Teknik servis performans\u0131, tahsilat dengesi, i\u015f emri durumlar\u0131 ve personel verimlilik analiti\u011fi")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; padding-left: 2px;"))
        header_row.addWidget(subtitle, 1, 0)
        layout.addLayout(header_row)

        # Renkli İstatistik Kartları
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)

        # Card 1: Toplam İşler
        self.card_total_jobs = self._create_stat_card("Toplam \u0130\u015fler", "0", "@finance_primary", "@finance_text")
        self.card_total_jobs.setMinimumWidth(160)
        self.card_total_jobs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.card_total_jobs)

        # Card 2: Açık İşler
        self.card_open_jobs = self._create_stat_card("A\u00e7\u0131k \u0130\u015fler", "0", "@finance_tertiary", "@finance_tertiary")
        self.card_open_jobs.setMinimumWidth(160)
        self.card_open_jobs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.card_open_jobs)

        # Card 3: Tahsil Edilen İşler
        self.card_paid_jobs = self._create_stat_card("Tahsil Edilen", "0", "@finance_secondary", "@finance_secondary")
        self.card_paid_jobs.setMinimumWidth(160)
        self.card_paid_jobs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.card_paid_jobs)

        # Card 4: Toplam Servisler
        self.card_total_services = self._create_stat_card("Toplam Servis", "0", "@finance_primary", "@finance_text")
        self.card_total_services.setMinimumWidth(160)
        self.card_total_services.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.card_total_services)

        # Card 5: Tamamlanan Servisler
        self.card_completed_services = self._create_stat_card("Tamamlanan", "0", "@finance_secondary", "@finance_secondary")
        self.card_completed_services.setMinimumWidth(160)
        # The reference screen keeps the summary strip to five primary metrics.
        # Keep the completed-services widget alive for existing update logic, but
        # omit it from the visual strip.
        self.card_completed_services.setVisible(False)

        # Card 6: Toplam Tahsilat
        self.card_total_revenue = self._create_stat_card(
            "Net Tahsilat Hacmi",
            CurrencyHelper.format_try_for_display(0, db=self.db, include_try_reference=False),
            "@finance_secondary",
            "@finance_secondary",
        )
        self.card_total_revenue.setMinimumWidth(160)
        self.card_total_revenue.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        stats_layout.addWidget(self.card_total_revenue)

        layout.addLayout(stats_layout)

        # Boşluk
        layout.addSpacing(8)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.setStyleSheet(theme_qss(
            "QTabWidget::pane { border: none; } "
            "QTabBar::tab {"
            "  background: @background;"
            "  color: @text;"
            "  padding: 6px 16px;"
            "  border-radius: 4px;"
            "  margin-right: 4px;"
            "  font-weight: 700;"
            "  font-size: 13px;"
            "  min-height: 28px;"
            "} "
            "QTabBar::tab:selected {"
            "  background: @finance_primary;"
            "  color: @background;"
            "} "
            "QTabBar::tab:hover {"
            "  background: @selection_bg;"
            "} "
            "QTabBar::tab:selected:hover {"
            "  background: @accent_pressed;"
            "}"
        ))
        layout.addWidget(self.tabs)

        # İş Takip sekmesi (Yeni İşlemler)
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(8)
        self.job_table.setHorizontalHeaderLabels([
            "\u0130\u015f No", "M\u00fc\u015fteri", "Durum", "A\u00e7\u0131klama", "Tutar", "Tarih", "Para Br.", "Teknisyen"
        ])
        self._style_table(self.job_table)
        job_header = self.job_table.horizontalHeader()
        job_header.moveSection(job_header.visualIndex(7), 2)
        job_header.moveSection(job_header.visualIndex(3), 3)
        job_header.moveSection(job_header.visualIndex(6), 6)
        self.job_table.verticalHeader().setDefaultSectionSize(54)
        self.job_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.job_table.customContextMenuRequested.connect(self.on_job_context_menu)
        self.job_table.cellDoubleClicked.connect(self._open_job_detail_from_cell)
        self.job_tab = QWidget()
        job_tab_layout = QVBoxLayout(self.job_tab)
        job_tab_layout.setContentsMargins(0, 0, 0, 0)
        job_tab_layout.setSpacing(8)
        self.job_search_input = QLineEdit()
        self.job_search_input.setPlaceholderText("İş no, müşteri, açıklama, durum veya para birimi ara...")
        self.job_search_button = QPushButton("Ara")
        self.job_search_clear_button = QPushButton("Temizle")
        job_tab_layout.addLayout(self._create_search_bar(
            self.job_search_input,
            self.job_search_button,
            self.job_search_clear_button,
            self.apply_job_filter,
        ))
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        self.job_status_filter = ModernComboBox()
        self.job_currency_filter = ModernComboBox()
        self.job_technician_filter = ModernComboBox()
        for combo, label in ((self.job_status_filter, "Durum: T\u00fcm\u00fc"), (self.job_currency_filter, "Birim: T\u00fcm\u00fc"), (self.job_technician_filter, "Sorumlu: T\u00fcm\u00fc")):
            combo.addItem(label, "")
            combo.setFixedHeight(32)
            combo.setStyleSheet(theme_qss(
                'QComboBox { background: @finance_surface; color: @finance_text; '
                'border: 1px solid @finance_outline; border-radius: 4px; padding: 0 8px; '
                'min-height: 30px; max-height: 30px; font-size: 11px; }'
            ))
            combo.set_reference_chevron()
            combo.currentIndexChanged.connect(self.apply_job_filter)
            filter_bar.addWidget(combo)
        self.job_advanced_button = QPushButton("Geli\u015fmi\u015f")
        self.job_advanced_button.setCheckable(True)
        self.job_advanced_button.setFixedHeight(32)
        self.job_advanced_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        filter_bar.addWidget(self.job_advanced_button)
        filter_bar.addStretch()
        self.job_result_label = QLabel("Goruntulenen: 0 Is Kaydi")
        self.job_result_label.setStyleSheet(theme_qss("color: @text_muted; padding: 5px;"))
        filter_bar.addWidget(self.job_result_label)
        job_tab_layout.addLayout(filter_bar)
        job_tab_layout.setAlignment(filter_bar, Qt.AlignmentFlag.AlignTop)
        self.job_advanced_panel = QFrame()
        self.job_advanced_panel.setObjectName("JobAdvancedFilters")
        self.job_advanced_panel.setStyleSheet(theme_qss("QFrame#JobAdvancedFilters{background:@finance_surface;border:1px solid @finance_outline;border-radius:6px;}"))
        advanced_layout = QHBoxLayout(self.job_advanced_panel)
        advanced_layout.setContentsMargins(10, 8, 10, 8)
        self.job_customer_filter = QComboBox()
        self.job_customer_filter.addItem("M\u00fc\u015fteri: T\u00fcm\u00fc", "")
        advanced_layout.addWidget(self.job_customer_filter, 1)
        self.job_amount_enabled = QCheckBox("Tutar aral\u0131\u011f\u0131")
        self.job_amount_enabled.setToolTip("Kayd\u0131n para birimindeki tutar; d\u00f6viz d\u00f6n\u00fc\u015f\u00fcm\u00fc yap\u0131lmaz.")
        advanced_layout.addWidget(self.job_amount_enabled)
        self.job_amount_min = QDoubleSpinBox()
        self.job_amount_max = QDoubleSpinBox()
        for amount in (self.job_amount_min, self.job_amount_max):
            amount.setRange(0, 1e12)
            amount.setDecimals(2)
            amount.setMinimumWidth(160)
            amount.setFixedHeight(34)
            amount.setStyleSheet(theme_qss("QDoubleSpinBox{background:@background;color:@text;border:1px solid @border;border-radius:4px;padding:0 6px;min-height:26px;max-height:34px;}"))
            amount.setEnabled(False)
            advanced_layout.addWidget(amount)
        self.job_amount_min.setPrefix("Min: ")
        self.job_amount_max.setPrefix("Max: ")
        self.job_amount_max.setSpecialValueText("Max: S\u0131n\u0131rs\u0131z")
        for amount in (self.job_amount_min, self.job_amount_max):
            amount.valueChanged.connect(self.apply_job_filter)
        self.job_advanced_reset = QPushButton("S\u0131f\u0131rla")
        self.job_advanced_reset.setFixedHeight(32)
        self.job_advanced_reset.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.job_advanced_reset.clicked.connect(self._reset_job_advanced_filters)
        advanced_layout.addWidget(self.job_advanced_reset)
        self.job_customer_filter.currentIndexChanged.connect(self.apply_job_filter)
        self.job_amount_enabled.toggled.connect(self._toggle_job_amount_filter)
        self.job_advanced_button.toggled.connect(self.job_advanced_panel.setVisible)
        self.job_advanced_panel.hide()
        job_tab_layout.addWidget(self.job_advanced_panel)
        self.job_empty_state = EmptyState("Açık iş kaydı yok", "Bu görünümde gösterilecek iş kaydı bulunamadı.", parent=self)
        self.job_empty_state.hide()
        self.job_table.setMinimumHeight(250)
        self.job_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        job_tab_layout.addWidget(self.job_table, 1)
        job_tab_layout.addWidget(self.job_empty_state)
        pager = QHBoxLayout()
        self.job_selection_label = QLabel("Secilen: 0 satir")
        self.job_table.itemSelectionChanged.connect(self._update_job_selection_count)
        pager.addWidget(self.job_selection_label)
        self.job_select_all = QPushButton("T\u00fcm\u00fcn\u00fc Se\u00e7")
        self.job_select_all.setFlat(True)
        self.job_select_all.setToolTip("Bu sayfada g\u00f6r\u00fcnen i\u015f kay\u0131tlar\u0131n\u0131 se\u00e7")
        self.job_select_all.clicked.connect(self._select_visible_jobs)
        self.job_select_all.setStyleSheet(theme_qss("QPushButton{background:transparent;color:@finance_text_muted;border:none;padding:4px;}QPushButton:hover{color:@finance_primary;}"))
        pager.addWidget(self.job_select_all)
        pager.addStretch()
        self.job_previous = QPushButton("<")
        self.job_next = QPushButton(">")
        self.job_page_label = QLabel("1 / 1")
        for button in (self.job_previous, self.job_next):
            button.setFixedSize(32, 30)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton { padding: 0; min-height: 24px; }"))
        self.job_previous.clicked.connect(lambda: self._change_job_page(-1))
        self.job_next.clicked.connect(lambda: self._change_job_page(1))
        pager.addWidget(self.job_previous)
        pager.addWidget(self.job_page_label)
        pager.addWidget(self.job_next)
        job_tab_layout.addLayout(pager)
        summary_row = QHBoxLayout()
        summary_row.setSpacing(10)
        for title_text, value_text, color_name in (
            ("ORTALAMA ONARIM SURESI", "-", "accent"),
            ("MUSTERI MEMNUNIYET SKORU", "-", "success"),
            ("ILK SEFERDE COZUM ORANI", "-", "accent"),
        ):
            summary_card = QFrame()
            summary_card.setFixedHeight(68)
            summary_card.setStyleSheet(theme_qss(
                f"background: @finance_surface; border: 1px solid @finance_outline; "
                f"border-radius: 6px;"
            ))
            summary_box = QVBoxLayout(summary_card)
            summary_box.setContentsMargins(12, 8, 12, 8)
            summary_title = QLabel(title_text)
            summary_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 700; border: none;"))
            summary_value = QLabel(value_text)
            summary_value.setToolTip("Bu metrik icin dogrulanmis veri henuz yok.")
            summary_value.setStyleSheet(theme_qss(f"color: @{color_name}; font-size: 17px; font-weight: 800; border: none;"))
            summary_box.addWidget(summary_title)
            summary_box.addWidget(summary_value)
            summary_row.addWidget(summary_card)
        job_tab_layout.addLayout(summary_row)
        self.tabs.addTab(self.job_tab, "\u0130\u015f Takip Raporu")

        # Servis Takip sekmesi (Servis Formları / Devices)
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(9)
        self.service_table.setHorizontalHeaderLabels([
            "Servis No", "M\u00fc\u015fteri", "Durum", "Cihaz / \u0130\u015f", "Toplam",
            "Giri\u015f Tarihi", "Teslim Tarihi", "Teknisyen", "\u0130\u015flemler"
        ])
        self._style_table(self.service_table)
        self.service_table.verticalHeader().setDefaultSectionSize(54)
        self.service_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.service_table.customContextMenuRequested.connect(self.on_service_context_menu)
        self.service_table.cellDoubleClicked.connect(self._open_service_detail_from_cell)
        self.service_tab = QWidget()
        service_tab_layout = QVBoxLayout(self.service_tab)
        service_tab_layout.setContentsMargins(0, 0, 0, 0)
        service_tab_layout.setSpacing(8)
        self.service_search_input = QLineEdit()
        self.service_search_input.setPlaceholderText("Servis no, müşteri, cihaz, durum, teknisyen veya tarih ara...")
        self.service_search_button = QPushButton("Ara")
        self.service_search_clear_button = QPushButton("Temizle")
        service_tab_layout.addLayout(self._create_search_bar(
            self.service_search_input,
            self.service_search_button,
            self.service_search_clear_button,
            self.apply_service_filter,
        ))
        self.service_empty_state = EmptyState("Açık servis kaydı yok", "Bu görünümde gösterilecek servis kaydı bulunamadı.", parent=self)
        self.service_empty_state.hide()
        self.service_table.setMinimumHeight(250)
        self.service_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        service_tab_layout.addWidget(self.service_table, 1)
        service_tab_layout.addWidget(self.service_empty_state)
        self.tabs.addTab(self.service_tab, "Servis Takip")
        self.technician_tab = QWidget()
        matrix_layout = QVBoxLayout(self.technician_tab)
        matrix_layout.setContentsMargins(0, 8, 0, 0)
        matrix_note = QLabel("Teknisyen baz\u0131nda servis da\u011f\u0131l\u0131m\u0131. Tarih aral\u0131\u011f\u0131 ve servis aramas\u0131 uygulan\u0131r. Detaylar i\u00e7in sat\u0131ra \u00e7ift t\u0131klay\u0131n.")
        matrix_note.setWordWrap(True)
        matrix_note.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:12px;"))
        matrix_layout.addWidget(matrix_note)
        self.technician_table = QTableWidget(0, 6)
        self.technician_table.setHorizontalHeaderLabels([
            "Teknisyen", "Toplam Servis", "Aktif", "Tamamlanan", "\u0130ptal / \u0130ade", "Ort. S\u00fcre (G\u00fcn)"])
        self._style_table(self.technician_table)
        matrix_header = self.technician_table.horizontalHeader()
        matrix_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            matrix_header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.technician_table.verticalHeader().setDefaultSectionSize(54)
        self.technician_table.cellDoubleClicked.connect(self._open_technician_services)
        self.technician_table.setMinimumHeight(250)
        self.technician_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        matrix_layout.addWidget(self.technician_table, 1)
        self.tabs.addTab(self.technician_tab, "Teknisyen Matrisi")
        self.profitability_tab = QWidget()
        profitability_layout = QVBoxLayout(self.profitability_tab)
        profitability_layout.setContentsMargins(0, 8, 0, 0)
        self.profitability_period = QComboBox()
        for title, period in (("Bu Ay", "month"), ("Bu Y\u0131l", "year"), ("Mali Y\u0131l", "fiscal")):
            self.profitability_period.addItem(title, period)
        self.profitability_period.setCurrentIndex(2)
        profitability_layout.addWidget(self.profitability_period, 0, Qt.AlignmentFlag.AlignLeft)
        self.profitability_note = QLabel("Finans defteri (TRY). Gelir - gider neti; i\u015f aramas\u0131 ve m\u00fc\u015fteri filtreleri bu toplam\u0131 de\u011fi\u015ftirmez. Vergi ve ayr\u0131 stok maliyeti tahmini uygulanmaz.")
        self.profitability_note.setWordWrap(True)
        self.profitability_note.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:12px;"))
        profitability_layout.addWidget(self.profitability_note)
        self.profitability_table = QTableWidget(0, 5)
        self.profitability_table.setHorizontalHeaderLabels(["D\u00f6nem", "Defter Geliri (TRY)", "Defter Gideri (TRY)", "Defter Neti (TRY)", "Net / Gelir"])
        self._style_table(self.profitability_table)
        profit_header = self.profitability_table.horizontalHeader()
        for column in range(5):
            profit_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
        self.profitability_table.verticalHeader().setDefaultSectionSize(70)
        self.profitability_table.setMinimumHeight(150)
        self.profitability_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        profitability_layout.addWidget(self.profitability_table, 1)
        self.profitability_status = QLabel()
        self.profitability_status.setWordWrap(True)
        self.profitability_status.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:12px;"))
        profitability_layout.addWidget(self.profitability_status)
        self.tabs.addTab(self.profitability_tab, "K\u00e2rl\u0131l\u0131k")

    def _wire_ui_signals(self):
        self.job_search_button.clicked.connect(self._on_ui_widget_changed)
        self.job_search_clear_button.clicked.connect(self._on_ui_widget_changed)
        self.service_search_button.clicked.connect(self._on_ui_widget_changed)
        self.service_search_clear_button.clicked.connect(self._on_ui_widget_changed)
        self.report_date_enabled.toggled.connect(self._apply_report_date_filters)
        self.report_date_from.dateChanged.connect(self._report_dates_changed)
        self.report_date_to.dateChanged.connect(self._report_dates_changed)
        self.tabs.currentChanged.connect(self._refresh_technician_matrix)
        self.tabs.currentChanged.connect(self._refresh_profitability)
        self.profitability_period.currentIndexChanged.connect(self._refresh_profitability)

    def _refresh_profitability(self, *_args):
        if self.tabs.currentWidget() is not self.profitability_tab:
            return
        from src.utils.finance_manager import FinanceManager
        manager = FinanceManager(self.db)
        if self.report_date_enabled.isChecked():
            start = self.report_date_from.date().toString("yyyy-MM-dd")
            end = self.report_date_to.date().toString("yyyy-MM-dd")
        else:
            start, end = manager._get_date_range(self.profitability_period.currentData())
            start, end = start[:10], end[:10]
        self.profitability_period.setEnabled(not self.report_date_enabled.isChecked())
        period_label = "{} - {}".format(start, end)
        values = [period_label, "-", "-", "-", "-"]
        try:
            cursor = self.db.cursor
            if cursor is None or start > end:
                raise ValueError("Ge\u00e7erli tarih aral\u0131\u011f\u0131 ve defter ba\u011flant\u0131s\u0131 gerekli.")
            requirements = {
                "currency_transactions": {"amount", "try_equivalent", "currency", "created_at", "transaction_type"},
                "accounting": {"amount", "try_equivalent", "currency", "date", "type", "customer_id", "category"},
            }
            for table, columns in requirements.items():
                actual = {record[1] for record in cursor.execute("PRAGMA table_info({})".format(table)).fetchall()}
                if not columns.issubset(actual):
                    raise ValueError("Finans defteri alanlar\u0131 eksik: {}".format(table))
            for table, date_column, type_condition in (
                    ("currency_transactions", "created_at", "transaction_type='DEBIT'"),
                    ("accounting", "date", "type IN ('Gelir', 'Gider')")):
                missing = cursor.execute(
                    "SELECT COUNT(*) FROM {} WHERE {} AND SUBSTR({},1,10) BETWEEN ? AND ? "
                    "AND UPPER(TRIM(COALESCE(currency,'TRY'))) NOT IN ('TRY','TL','') "
                    "AND (try_equivalent IS NULL OR (try_equivalent=0 AND amount!=0))".format(table, type_condition, date_column),
                    (start, end)).fetchone()[0]
                if missing:
                    raise ValueError("{} kay\u0131tta TRY kur kar\u015f\u0131l\u0131\u011f\u0131 eksik; net hesaplanmad\u0131.".format(missing))
            # Include date-only, SQLite and ISO timestamps through the final day.
            revenue = manager._calculate_revenue(start, end + "\uffff")
            expenses = manager._calculate_expenses(start, end + "\uffff")
            net = revenue - expenses
            values = [period_label, "{:,.2f}".format(revenue), "{:,.2f}".format(expenses), "{:,.2f}".format(net),
                      "{:.1f}%".format(net * 100 / revenue) if revenue else "-"]
            self.profitability_status.setText("Mevcut finans hesaplamas\u0131 kullan\u0131ld\u0131. Tahsilat / sat\u0131\u015f yans\u0131malar\u0131 \u00e7ift say\u0131lmaz; deftere yazma i\u015flemi yap\u0131lmad\u0131.")
        except (sqlite3.Error, ValueError, AttributeError) as error:
            self.profitability_status.setText(str(error))
        self.profitability_table.setRowCount(1)
        for column, value in enumerate(values):
            self.profitability_table.setItem(0, column, QTableWidgetItem(value))

    def _refresh_technician_matrix(self, *_args):
        if self.tabs.currentWidget() is not self.technician_tab:
            return
        groups = {}
        for row in range(self.service_table.rowCount()):
            if self.service_table.isRowHidden(row):
                continue
            technician = self._table_text(self.service_table, row, 7) or "Atanmam\u0131\u015f"
            stats = groups.setdefault(technician, {"total": 0, "complete": 0, "cancel": 0, "days": []})
            stats["total"] += 1
            status = self._table_text(self.service_table, row, 2).casefold()
            completed = any(word in status for word in ("teslim", "tamam", "haz\u0131r", "tamir edildi"))
            cancelled = any(word in status for word in ("iptal", "iade"))
            if cancelled:
                stats["cancel"] += 1
            elif completed:
                stats["complete"] += 1
                start = QDate.fromString(self._table_text(self.service_table, row, 5), "dd.MM.yyyy")
                end = QDate.fromString(self._table_text(self.service_table, row, 6), "dd.MM.yyyy")
                if start.isValid() and end.isValid() and end >= start:
                    stats["days"].append(start.daysTo(end))
        self.technician_table.setRowCount(len(groups))
        for row, (technician, stats) in enumerate(sorted(groups.items())):
            days = stats["days"]
            values = [technician, stats["total"], stats["total"] - stats["complete"] - stats["cancel"],
                      stats["complete"], stats["cancel"], "{:.1f}".format(sum(days) / len(days)) if days else "-"]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 5:
                    item.setToolTip("{} ge\u00e7erli giri\u015f / teslim tarihli tamamlanm\u0131\u015f servis".format(len(days)))
                self.technician_table.setItem(row, column, item)

    def _open_technician_services(self, row, _column):
        technician = self._table_text(self.technician_table, row, 0)
        self.tabs.setCurrentWidget(self.service_tab)
        self._service_category = "all"
        self._service_technician = technician
        self.service_search_input.clear()
        self.apply_service_filter()

    def _report_dates_changed(self, *_args):
        if not self.report_date_enabled.isChecked():
            self.report_date_enabled.setChecked(True)
        else:
            self._apply_report_date_filters()

    def _apply_report_date_filters(self, *_args):
        self.apply_job_filter()
        self.apply_service_filter()
        self._refresh_profitability()

    def _in_report_date_range(self, text):
        if not self.report_date_enabled.isChecked():
            return True
        date = QDate.fromString(text, "dd.MM.yyyy")
        if not date.isValid():
            date = QDate.fromString(text[:10], "yyyy-MM-dd")
        return date.isValid() and self.report_date_from.date() <= date <= self.report_date_to.date()

    def _report_export_data(self):
        table = {self.job_tab: self.job_table, self.service_tab: self.service_table,
                 self.technician_tab: self.technician_table, self.profitability_tab: self.profitability_table}[self.tabs.currentWidget()]
        rows = (getattr(self, "_job_matching_rows", list(range(table.rowCount())))
                if table is self.job_table else [row for row in range(table.rowCount()) if not table.isRowHidden(row)])
        header = table.horizontalHeader()
        columns = [header.logicalIndex(index) for index in range(table.columnCount())
                   if table is not self.service_table or header.logicalIndex(index) != 8]
        headings = [table.horizontalHeaderItem(column).text() for column in columns]
        values = [[self._table_text(table, row, column) for column in columns] for row in rows]
        return headings, values

    def export_report_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Excel Raporu", "is_servis_raporu.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        headings, values = self._report_export_data()
        try:
            import pandas as pd
            pd.DataFrame(values, columns=headings).to_excel(path, index=False)
        except (OSError, ValueError, ImportError) as error:
            logger.error("Job report Excel export failed: %s", error)
            from src.utils.message_helper import show_error
            show_error(self, "Rapor", "Rapor kaydedilemedi: {}".format(error))

    @staticmethod
    def _report_print_html(headings, values):
        cells = lambda row, tag: "".join("<{}>{}</{}>".format(tag, html.escape(str(value)), tag) for value in row)
        return ('<html><head><style>body{font-family:Inter;font-size:9pt}table{width:100%;border-collapse:collapse}'
                'th,td{border:1px solid #888;padding:4px}</style></head><body><h2>Is / Servis Takibi Raporu</h2>'
                '<table><tr>' + cells(headings, "th") + '</tr>'
                + "".join("<tr>" + cells(row, "td") + "</tr>" for row in values) + '</table></body></html>')

    def export_report_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "PDF Raporu", "is_servis_raporu.pdf", "PDF (*.pdf)")
        if not path:
            return
        from PyQt6.QtCore import QMarginsF
        from PyQt6.QtGui import QTextDocument, QPageLayout, QPageSize, QPdfWriter
        printer = QPdfWriter(path)
        printer.setResolution(1200)
        printer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Landscape, QMarginsF(10, 10, 10, 10)))
        document = QTextDocument(self)
        document.setHtml(self._report_print_html(*self._report_export_data()))
        document.print(printer)

    def _create_search_bar(self, search_input, search_button, clear_button, apply_callback):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        search_input.setClearButtonEnabled(True)
        search_input.setFixedHeight(34)
        search_input.returnPressed.connect(apply_callback)
        search_button.clicked.connect(apply_callback)
        clear_button.clicked.connect(lambda: self._clear_search(search_input, apply_callback))

        search_input.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid @accent;
                background: @surface;
            }
        """))
        button_qss = theme_qss(DesignTokens.get_button_qss("secondary", size="sm"))
        search_button.setStyleSheet(button_qss)
        clear_button.setStyleSheet(button_qss)

        row.addWidget(search_input, 1)
        row.addWidget(search_button)
        row.addWidget(clear_button)
        return row

    def _clear_search(self, search_input, apply_callback):
        if search_input is self.service_search_input:
            self._service_technician = ""
        search_input.clear()
        apply_callback()

    def _toggle_job_amount_filter(self, enabled):
        self.job_amount_min.setEnabled(enabled)
        self.job_amount_max.setEnabled(enabled)
        self.apply_job_filter()

    def _reset_job_advanced_filters(self):
        widgets = (self.job_customer_filter, self.job_amount_enabled, self.job_amount_min, self.job_amount_max)
        for widget in widgets:
            widget.blockSignals(True)
        self.job_customer_filter.setCurrentIndex(0)
        self.job_amount_enabled.setChecked(False)
        self.job_amount_min.setValue(0)
        self.job_amount_max.setValue(0)
        for widget in widgets:
            widget.blockSignals(False)
        self._toggle_job_amount_filter(False)

    def _job_amount_matches(self, row):
        if not self.job_amount_enabled.isChecked():
            return True
        item = self.job_table.item(row, 4)
        value = item.data(Qt.ItemDataRole.UserRole) if item else None
        if value is None:
            try:
                value = float(self._table_text(self.job_table, row, 4).replace(",", ""))
            except ValueError:
                return False
        maximum = self.job_amount_max.value()
        return self.job_amount_min.value() <= value and (maximum == 0 or value <= maximum)

    def _style_table(self, table):
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        table.setColumnWidth(2, 126)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        if table.columnCount() > 7:
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        if table.columnCount() > 8:
            header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(8, 140)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setMouseTracking(True)
        table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @finance_surface;
                border: 1px solid @border;
                border-radius: 6px;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid @border;
                outline: none;
            }
            QTableWidget::item:alternate { background: @background; }
            QHeaderView::section {
                background: @background; color: @finance_text_muted;
                border: none; border-bottom: 1px solid @finance_outline;
                padding: 9px 8px; font-size: 11px; font-weight: 700;
            }
            QTableWidget::item:hover {
                background: @finance_surface;
            }
            QTableWidget::item:selected {
                background: @accent;
                color: white;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
        """))

    def _create_stat_card(self, title, value, color_primary, color_accent):
        """Renkli istatistik kartı oluştur"""
        card = QFrame()
        card.setObjectName("JobReportMetricCard")
        card.setFixedHeight(112)
        card.setStyleSheet(theme_qss(f"""
            QFrame#JobReportMetricCard {{
                background: @finance_surface;
                border: 1px solid @finance_outline;
                border-radius: 6px;
            }}
            QLabel {{ background: transparent; border: none; }}
        """))

        # Gölge efekti ekle
        try:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(8)
            shadow.setColor(QColor(0, 0, 0, 15))
            shadow.setOffset(0, 2)
            card.setGraphicsEffect(shadow)
        except Exception as e:
            logger.error(f"Archive context menu action failed: {e}")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Title
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(theme_qss(f"""
            color: @finance_text_muted;
            background: transparent;
            border: none;
            font-size: 11px;
            font-weight: 700;
        """))
        heading = QHBoxLayout()
        kind = "clipboard" if "Toplam" in title else "check"
        if "Servis" in title:
            kind = "truck"
        elif "A\u00e7\u0131k" in title:
            kind = "clock"
        heading.addWidget(LoanerMetricIcon(kind, color_primary.lstrip("@")))
        heading.addWidget(lbl_title, 1)
        layout.addLayout(heading)

        # Value
        if title == 'Net Tahsilat Hacmi':
            lbl_value = ReferenceMetricValueLabel(value, primary_token=color_accent.lstrip('@'), primary_size=32)
            lbl_value.setMinimumHeight(42)
        else:
            lbl_value = QLabel(value)
        lbl_value.setStyleSheet(theme_qss(f"""
            color: {color_accent};
            background: transparent;
            border: none;
            font-size: 32px;
            font-weight: 800;
        """))
        value_row = QHBoxLayout()
        value_row.addWidget(lbl_value, 1)
        caption = QLabel("Fiziksel cihaz" if "Servis" in title else ("Kay\u0131tl\u0131 i\u015fler" if "Toplam" in title else ""))
        caption.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:11px;border:none;"))
        value_row.addWidget(caption)
        layout.addLayout(value_row)
        layout.addStretch()
        card.metric_progress = QProgressBar(card)
        card.metric_progress.setRange(0, 100)
        card.metric_progress.setValue(0)
        card.metric_progress.setTextVisible(False)
        card.metric_progress.setFixedHeight(5)
        card.metric_progress.setStyleSheet(theme_qss(
            "QProgressBar{background:@finance_outline;border:none;border-radius:2px;min-height:5px;max-height:5px;padding:0;}"
            + "QProgressBar::chunk{background:" + color_primary + ";border-radius:2px;}"))
        layout.addWidget(card.metric_progress)

        return card

    def _refresh_metric_progress(self):
        def count(card):
            text = card.findChildren(QLabel)[1].text()
            return int(text) if text.isdigit() else 0
        total = count(self.card_total_jobs)
        for card in (self.card_total_jobs, self.card_open_jobs, self.card_paid_jobs):
            value = count(card)
            card.metric_progress.setValue(round(value * 100 / total) if total else 0)
            card.metric_progress.setToolTip("{} / {} i\u015f kayd\u0131".format(value, total))
        self.card_total_services.metric_progress.setValue(100 if count(self.card_total_services) else 0)
        self.card_total_services.metric_progress.setToolTip("Kay\u0131tl\u0131 servislerin tamam\u0131")
        self.card_total_revenue.metric_progress.setToolTip("Tahsilat hedefi tan\u0131ml\u0131 de\u011fil")

    def _format_tr_date(self, value):
        text = str(value or "").strip()
        if not text or text in {"-", "None", "NULL"}:
            return "-"

        normalized = text.replace("T", " ").replace("/", "-")
        if "." in normalized:
            normalized = normalized.split(".", 1)[0]

        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d-%m-%Y %H:%M",
            "%d-%m-%Y",
        ):
            try:
                dt = datetime.strptime(normalized, fmt)
                if "%H" in fmt:
                    return dt.strftime("%d.%m.%Y %H:%M")
                return dt.strftime("%d.%m.%Y")
            except ValueError:
                continue
        return text

    def _row_matches_query(self, table, row, query):
        if not query:
            return True
        needle = query.casefold()
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item and needle in item.text().casefold():
                return True
        return False

    def _apply_table_filter(self, table, search_input, empty_state):
        query = search_input.text().strip()
        visible_count = 0
        for row in range(table.rowCount()):
            visible = self._row_matches_query(table, row, query)
            table.setRowHidden(row, not visible)
            if visible:
                visible_count += 1

        table.setVisible(visible_count > 0)
        empty_state.setVisible(visible_count == 0)

    def apply_job_filter(self, *_args):
        if not getattr(self, "_job_page_change", False):
            self.job_page = 0
        self._apply_table_filter(self.job_table, self.job_search_input, self.job_empty_state)
        status = self.job_status_filter.currentData()
        currency = self.job_currency_filter.currentData()
        technician = self.job_technician_filter.currentData()
        customer = self.job_customer_filter.currentData()
        matching = []
        for row in range(self.job_table.rowCount()):
            visible = (not self.job_table.isRowHidden(row)
                       and (not status or self._table_text(self.job_table, row, 2) == status)
                       and (not currency or self._table_text(self.job_table, row, 6) == currency)
                       and (not technician or self._table_text(self.job_table, row, 7) == technician)
                       and (not customer or self._table_text(self.job_table, row, 1) == customer)
                       and self._job_amount_matches(row)
                       and self._in_report_date_range(self._table_text(self.job_table, row, 5)))
            self.job_table.setRowHidden(row, not visible)
            if visible:
                matching.append(row)
        count = len(matching)
        pages = max(1, (count + self.job_page_size - 1) // self.job_page_size)
        self.job_page = max(0, min(self.job_page, pages - 1))
        page_rows = set(matching[self.job_page * self.job_page_size:(self.job_page + 1) * self.job_page_size])
        self._job_matching_rows = matching
        for row in range(self.job_table.rowCount()):
            self.job_table.setRowHidden(row, row not in page_rows)
        self.job_page_label.setText("{} / {}".format(self.job_page + 1, pages))
        self.job_previous.setEnabled(self.job_page > 0)
        self.job_next.setEnabled(self.job_page + 1 < pages)
        self.job_table.setVisible(count > 0)
        self.job_empty_state.setVisible(count == 0)
        self.job_result_label.setText("Goruntulenen: {} / {} Is Kaydi".format(count, self.job_table.rowCount()))

    def _change_job_page(self, delta):
        self.job_page += delta
        self._job_page_change = True
        try:
            self.apply_job_filter()
        finally:
            self._job_page_change = False

    def _update_job_selection_count(self):
        count = len(self.job_table.selectionModel().selectedRows())
        self.job_selection_label.setText("Secilen: {} satir".format(count))

    def _select_visible_jobs(self):
        selection = self.job_table.selectionModel()
        selection.clearSelection()
        for row in range(self.job_table.rowCount()):
            if not self.job_table.isRowHidden(row):
                selection.select(self.job_table.model().index(row, 0),
                                 QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows)

    def _update_job_filter_options(self):
        for combo, label, column in ((self.job_status_filter, "Durum: T\u00fcm\u00fc", 2),
                                     (self.job_currency_filter, "Birim: T\u00fcm\u00fc", 6),
                                     (self.job_technician_filter, "Sorumlu: T\u00fcm\u00fc", 7),
                                     (self.job_customer_filter, "M\u00fc\u015fteri: T\u00fcm\u00fc", 1)):
            previous = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(label, "")
            values = {self._table_text(self.job_table, row, column) for row in range(self.job_table.rowCount())}
            for value in sorted(values - {""}):
                combo.addItem(value, value)
            combo.setCurrentIndex(max(0, combo.findData(previous)))
            combo.blockSignals(False)

    def apply_service_filter(self):
        self._apply_table_filter(self.service_table, self.service_search_input, self.service_empty_state)
        category = getattr(self, "_service_category", "all")
        aliases = {
            "test": ("test",), "tamirde": ("tamir",),
            "bekliyor": ("bekliyor", "al"), "iptal": ("iptal", "iade"),
            "kargo": ("kargo",), "teslim": ("teslim",),
            "parca": ("parça",), "borclu": ("borç", "borclu"),
        }.get(category, ())
        for row in range(self.service_table.rowCount()):
            status = self._table_text(self.service_table, row, 2).casefold()
            visible = (not self.service_table.isRowHidden(row)
                       and (not aliases or any(alias in status for alias in aliases))
                       and (not getattr(self, "_service_technician", "")
                            or (self._table_text(self.service_table, row, 7) or "Atanmam\u0131\u015f") == self._service_technician)
                       and self._in_report_date_range(self._table_text(self.service_table, row, 5)))
            self.service_table.setRowHidden(row, not visible)
        visible_count = sum(not self.service_table.isRowHidden(row) for row in range(self.service_table.rowCount()))
        self.service_table.setVisible(visible_count > 0)
        self.service_empty_state.setVisible(visible_count == 0)
        self._refresh_technician_matrix()

    def _table_text(self, table, row, col):
        item = table.item(row, col)
        return item.text().strip() if item else ""

    @staticmethod
    def _set_report_number_fonts(table, row, columns):
        for column in columns:
            item = table.item(row, column)
            if item is None:
                continue
            font = QFont(DesignTokens.MONO_FONT_NAME)
            font.setPixelSize(11)
            font.setBold(column in (0, 4))
            item.setFont(font)
            if column in (0, 4):
                item.setToolTip(item.text())

    def _set_report_status_badge(self, table, row):
        status = self._table_text(table, row, 2)
        normalized = status.casefold()
        if any(word in normalized for word in ("tahsil", "teslim", "tamam", "haz\u0131r")):
            color = "finance_secondary"
        elif any(word in normalized for word in ("par\u00e7a", "bekliyor", "iptal")):
            color = "finance_tertiary"
        else:
            color = "finance_primary"
        container = QWidget()
        container.setObjectName("ReportStatusCell")
        row_background = "background" if row % 2 else "finance_surface"
        container.setStyleSheet(theme_qss("QWidget#ReportStatusCell{background:@" + row_background + ";border:none;padding:0;}"))
        box = QHBoxLayout(container)
        box.setContentsMargins(6, 0, 6, 0)
        badge = QLabel(status)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedHeight(24)
        badge.setStyleSheet(theme_qss(
            "QLabel{color:@" + color + ";background:@finance_surface_alt;border:none;border-radius:4px;padding:0;min-height:24px;max-height:24px;font-size:11px;font-weight:600;}"))
        box.addWidget(badge)
        table.setCellWidget(row, 2, container)

    def _open_job_detail_from_cell(self, row, column):
        self._open_job_detail(row)

    def _open_service_detail_from_cell(self, row, column):
        tracking_no = self._table_text(self.service_table, row, 0)
        if tracking_no:
            self._open_service_archive_detail(tracking_no)

    def _open_service_archive_detail(self, tracking_no):
        try:
            row = self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                (tracking_no,),
            ).fetchone()
            if row:
                from src.utils.system_config import SystemConfig
                is_auto = SystemConfig.get_current_sector(self.db) == "otomotiv" if hasattr(SystemConfig, "get_current_sector") else False
                if is_auto:
                    from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel as panel_cls
                else:
                    from src.ui.dialogs.technical_service_technician_panel import TechnicalServiceTechnicianPanel as panel_cls

                panel = panel_cls(
                    self.db,
                    row,
                    self,
                    sector_manager=getattr(self.main_window, "sector_manager", None),
                    read_only=True
                )
                panel.exec()
            else:
                from src.ui.dialogs.archive_detail_dialog import ArchiveDetailDialog
                dlg = ArchiveDetailDialog(self.db, tracking_no, self)
                dlg.exec()
        except Exception as e:
            logger.error(f"Service archive detail open failed: {e}", exc_info=True)

    def _open_service_technician_panel(self, tracking_no):
        opener = getattr(self.main_window, "open_technician_panel", None)
        if callable(opener):
            opener(tracking_no)

    def _open_service_form(self, tracking_no):
        opener = getattr(self.main_window, "open_service_form", None)
        if callable(opener):
            opener(tracking_no)

    def _service_action_button(self, tooltip, svg_content, callback, color):
        button = QPushButton()
        button.setToolTip(tooltip)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(32, 30)
        button.setIcon(render_svg_icon(svg_content, color, size=16))
        button.setIconSize(QSize(16, 16))
        button.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 7px;
                padding: 0;
            }
            QPushButton:hover {
                background: @selection_bg;
                border-color: @accent;
            }
            QPushButton:pressed {
                background: @accent;
            }
        """))
        button.clicked.connect(callback)
        return button

    def _set_service_actions(self, row, tracking_no):
        container = QWidget(self.service_table)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        icons = {
            "detail": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><circle cx="12" cy="12" r="3"/>'
                '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/></svg>'
            ),
            "technician": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><path d="M14.7 6.3a4 4 0 0 0-5-5L8 3l3 3 1.7-1.7a4 4 0 0 0 2 2z"/>'
                '<path d="m5 21 9-9"/><path d="m3 17 4 4"/></svg>'
            ),
            "form": (
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
                '<path d="M14 2v6h6M8 13h8M8 17h8"/></svg>'
            ),
        }
        layout.addWidget(self._service_action_button(
            "Detay",
            icons["detail"],
            lambda checked=False, value=tracking_no: self._open_service_archive_detail(value),
            tc("accent"),
        ))
        layout.addWidget(self._service_action_button(
            "Teknisyen Paneli",
            icons["technician"],
            lambda checked=False, value=tracking_no: self._open_service_technician_panel(value),
            tc("success"),
        ))
        layout.addWidget(self._service_action_button(
            "Servis Formu",
            icons["form"],
            lambda checked=False, value=tracking_no: self._open_service_form(value),
            tc("warning"),
        ))
        self.service_table.setCellWidget(row, 8, container)


    def _fetch_job_detail(self, job_no):
        detail = {
            "job_no": job_no,
            "customer": "",
            "customer_id": None,
            "description": "",
            "status": "",
            "currency": "",
            "debit": 0.0,
            "credit": 0.0,
            "remaining": 0.0,
            "created_at": "",
            "transactions": [],
            "service": None,
        }
        cur = getattr(self.db, "cursor", None)
        if cur is None or not job_no:
            return detail

        try:
            cur.execute(
                """
                SELECT ct.id,
                       ct.transaction_type,
                       ct.amount,
                       ct.currency,
                       ct.try_equivalent,
                       ct.description,
                       ct.created_at,
                       ct.customer_id,
                       COALESCE(c.name, '') AS customer_name
                FROM currency_transactions ct
                LEFT JOIN customers c ON c.id = ct.customer_id
                WHERE ct.tracking_no=?
                ORDER BY ct.created_at ASC, ct.id ASC
                """,
                (job_no,),
            )
            rows = cur.fetchall() or []
            for row in rows:
                if hasattr(row, "keys"):
                    typ = str(row["transaction_type"] or "")
                    amount = float(row["amount"] or 0.0)
                    currency = str(row["currency"] or "")
                    try_amount = float(row["try_equivalent"] or 0.0)
                    desc = str(row["description"] or "")
                    created = str(row["created_at"] or "")
                    customer_id = row["customer_id"]
                    customer = str(row["customer_name"] or "")
                else:
                    typ = str(row[1] or "")
                    amount = float(row[2] or 0.0)
                    currency = str(row[3] or "")
                    try_amount = float(row[4] or 0.0)
                    desc = str(row[5] or "")
                    created = str(row[6] or "")
                    customer_id = row[7]
                    customer = str(row[8] or "")

                if typ == "DEBIT":
                    detail["debit"] += amount
                elif typ == "CREDIT":
                    detail["credit"] += amount
                if not detail["customer"] and customer:
                    detail["customer"] = customer
                if detail["customer_id"] is None and customer_id is not None:
                    detail["customer_id"] = customer_id
                if not detail["description"] and desc:
                    detail["description"] = desc
                if not detail["created_at"] and created:
                    detail["created_at"] = created
                if not detail["currency"] and currency:
                    detail["currency"] = currency
                detail["transactions"].append((created, typ, desc, amount, currency, try_amount))
        except Exception as e:
            logger.error(f"Job detail transaction query failed: {e}", exc_info=True)

        detail["remaining"] = detail["debit"] - detail["credit"]
        detail["status"] = "Tahsil Edildi" if detail["remaining"] <= 0.01 else "Açık"

        try:
            cur.execute(
                """
                SELECT tracking_no, customer_name, status, device_brand, device_model,
                       labor_cost, entry_date, exit_date, delivered_at, technician, general_note, technician_note
                FROM devices
                WHERE tracking_no=?
                LIMIT 1
                """,
                (job_no,),
            )
            row = cur.fetchone()
            if row:
                if hasattr(row, "keys"):
                    detail["service"] = {key: row[key] for key in row.keys()}
                else:
                    keys = [
                        "tracking_no", "customer_name", "status", "device_brand", "device_model",
                        "labor_cost", "entry_date", "exit_date", "delivered_at", "technician",
                        "general_note", "technician_note",
                    ]
                    detail["service"] = dict(zip(keys, row))
                if not detail["customer"]:
                    detail["customer"] = str(detail["service"].get("customer_name") or "")
        except Exception as e:
            logger.debug(f"Job detail service lookup skipped: {e}")

        return detail

    def _open_job_detail(self, row):
        job_no = self._table_text(self.job_table, row, 0)
        if not job_no:
            return
        detail = self._fetch_job_detail(job_no)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"İş Detayı - {job_no}")
        dlg.resize(980, 680)
        dlg.setModal(True)
        dlg.setStyleSheet(theme_qss("""
            QDialog { background: @surface_alt; color: @text; }
            QFrame#DetailCard { background: @surface; border: 1px solid @border; border-radius: 14px; }
            QLabel { color: @text; }
            QTableWidget { background: @surface; color: @text; border: 1px solid @border; border-radius: 10px; gridline-color: @border; outline: none; }
            QHeaderView::section { background: @surface_alt; color: @text; border: 1px solid @border; padding: 7px; font-weight: 700; }
            QTableWidget::item { padding: 7px; border-bottom: 1px solid @border; outline: none; }
            QTableWidget::item:focus { outline: none; border: none; }
            QTableWidget::item:selected { outline: none; }
            QPushButton { background: @accent; color: @selection_text; border: none; border-radius: 8px; padding: 9px 18px; font-weight: 700; }
            QPushButton:hover { background: @accent_hover; }
        """))

        root = QVBoxLayout(dlg)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        title = QLabel(f"Yapılan İş Özeti - {job_no}")
        title.setFont(QFont(DesignTokens.FONT_NAME, 17, QFont.Weight.Bold))
        root.addWidget(title)

        summary = QFrame()
        summary.setObjectName("DetailCard")
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(10)

        def add_summary(label, value, r, c):
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700;"))
            val = QLabel(str(value or "-"))
            val.setWordWrap(True)
            val.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
            summary_layout.addWidget(lbl, r * 2, c)
            summary_layout.addWidget(val, r * 2 + 1, c)

        add_summary("Müşteri", detail["customer"], 0, 0)
        add_summary("Durum", detail["status"], 0, 1)
        add_summary("Borçlandırılan", f"{detail['debit']:,.2f} {detail['currency'] or ''}".strip(), 0, 2)
        add_summary("Tahsil Edilen", f"{detail['credit']:,.2f} {detail['currency'] or ''}".strip(), 0, 3)
        add_summary("Kalan", f"{detail['remaining']:,.2f} {detail['currency'] or ''}".strip(), 1, 0)
        add_summary("Tarih", self._format_tr_date(detail["created_at"]), 1, 1)
        add_summary("Açıklama", detail["description"], 1, 2)
        if detail["service"]:
            service = detail["service"]
            device = f"{service.get('device_brand') or ''} {service.get('device_model') or ''}".strip()
            add_summary("Servis / Cihaz", device, 1, 3)
        root.addWidget(summary)

        if detail["service"]:
            service = detail["service"]
            service_frame = QFrame()
            service_frame.setObjectName("DetailCard")
            service_layout = QGridLayout(service_frame)
            service_layout.setContentsMargins(16, 12, 16, 12)
            service_layout.setHorizontalSpacing(18)
            service_layout.setVerticalSpacing(8)
            fields = [
                ("Servis Durumu", service.get("status")),
                ("Giriş Tarihi", self._format_tr_date(service.get("entry_date"))),
                ("Teslim Tarihi", self._format_tr_date(service.get("exit_date") or service.get("delivered_at"))),
                ("Teknisyen", service.get("technician")),
                ("Müşteri Notu", service.get("general_note")),
                ("Teknik Not", service.get("technician_note")),
            ]
            for idx, (label, value) in enumerate(fields):
                r = idx // 3
                c = idx % 3
                box = QLabel(f"<b>{label}</b><br>{str(value or '-')}")
                box.setWordWrap(True)
                service_layout.addWidget(box, r, c)
            root.addWidget(service_frame)

        tx_table = QTableWidget()
        tx_table.setColumnCount(6)
        tx_table.setHorizontalHeaderLabels(["Tarih", "Tür", "Açıklama", "Tutar", "Para Br.", "TRY Karşılığı"])
        tx_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tx_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        tx_table.setAlternatingRowColors(True)
        tx_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tx_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tx_table.verticalHeader().setVisible(False)
        for created, typ, desc, amount, currency, try_amount in detail["transactions"]:
            r = tx_table.rowCount()
            tx_table.insertRow(r)
            display_type = "Borç" if typ == "DEBIT" else "Tahsilat" if typ == "CREDIT" else typ
            values = [
                self._format_tr_date(created),
                display_type,
                desc,
                f"{amount:,.2f}",
                currency,
                CurrencyHelper.format_try_for_display(try_amount, db=self.db, include_try_reference=False),
            ]
            for c, value in enumerate(values):
                tx_table.setItem(r, c, QTableWidgetItem(str(value or "")))
        root.addWidget(tx_table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(dlg.accept)
        actions.addWidget(btn_close)
        root.addLayout(actions)
        dlg.exec()

    def load_jobs(self):
        self.job_table.setRowCount(0)
        cur = getattr(self.db, "cursor", None)
        if cur is None:
            return

        try:
            cur.execute(
                """
                SELECT ct.customer_id,
                       ct.tracking_no,
                       MAX(CASE WHEN ct.transaction_type='DEBIT' THEN ct.description END) AS description,
                       SUM(CASE WHEN ct.transaction_type='DEBIT' THEN ct.amount ELSE 0 END) AS debit_amount,
                       MAX(ct.currency) AS currency,
                       MAX(CASE WHEN ct.transaction_type='DEBIT' THEN ct.created_at END) AS created_at,
                       COALESCE(c.name, '') AS customer_name,
                       SUM(CASE WHEN ct.transaction_type='DEBIT' THEN ct.amount ELSE 0 END) -
                       SUM(CASE WHEN ct.transaction_type='CREDIT' THEN ct.amount ELSE 0 END) AS remaining_amount
                FROM currency_transactions ct
                LEFT JOIN customers c
                    ON c.id = ct.customer_id
                   AND COALESCE(c.is_deleted, 0) = 0
                WHERE ct.tracking_no IS NOT NULL
                  AND TRIM(COALESCE(ct.tracking_no, '')) <> ''
                GROUP BY ct.customer_id, ct.tracking_no, c.name
                HAVING SUM(CASE WHEN ct.transaction_type='DEBIT' THEN ct.amount ELSE 0 END) > 0
                ORDER BY MAX(CASE WHEN ct.transaction_type='DEBIT' THEN ct.created_at END) DESC
                """,
            )
            rows = cur.fetchall()
        except Exception:
            rows = []

        technicians = {}
        try:
            device_rows = cur.execute("SELECT tracking_no, technician FROM devices WHERE COALESCE(is_deleted, 0)=0").fetchall()
            technicians = {str(record[0]): str(record[1] or '-') for record in device_rows}
        except sqlite3.Error:
            pass

        for row in rows:
            try:
                if hasattr(row, "keys"):
                    job_no = str(row["tracking_no"] or "")
                    customer = str(row["customer_name"] or "")
                    desc = str(row["description"] or "")
                    amt = float(row["debit_amount"] or 0.0)
                    currency = str(row["currency"] or "TRY")
                    date_val = str(row["created_at"] or "")
                    remaining = float(row["remaining_amount"] or 0.0)
                else:
                    job_no = str(row[1] or "")
                    customer = str(row[6] or "")
                    desc = str(row[2] or "")
                    amt = float(row[3] or 0.0)
                    currency = str(row[4] or "TRY")
                    date_val = str(row[5] or "")
                    remaining = float(row[7] or 0.0) if len(row) > 7 else 0.0
            except Exception:
                continue

            status = "Tahsil Edildi" if remaining <= 0.01 else "Açık"
            note = desc

            r = self.job_table.rowCount()
            self.job_table.insertRow(r)
            self.job_table.setItem(r, 0, QTableWidgetItem(job_no))
            self.job_table.setItem(r, 1, QTableWidgetItem(customer))
            self.job_table.setItem(r, 2, QTableWidgetItem(status))
            self.job_table.setItem(r, 3, QTableWidgetItem(note))
            amount_item = QTableWidgetItem(f"{amt:,.2f}")
            amount_item.setData(Qt.ItemDataRole.UserRole, amt)
            self.job_table.setItem(r, 4, amount_item)
            self.job_table.setItem(r, 5, QTableWidgetItem(self._format_tr_date(date_val)))
            self.job_table.item(r, 5).setToolTip(str(date_val or ''))
            self.job_table.setItem(r, 6, QTableWidgetItem(currency))
            self.job_table.setItem(r, 7, QTableWidgetItem(technicians.get(job_no, '-')))
            self._set_report_number_fonts(self.job_table, r, (0, 4, 5, 6))
            self._set_report_status_badge(self.job_table, r)
        has_rows = self.job_table.rowCount() > 0
        if hasattr(self, "job_result_label"):
            self.job_result_label.setText(f"Goruntulenen: {self.job_table.rowCount()} Is Kaydi")
        self.job_table.setVisible(has_rows)
        self.job_empty_state.setVisible(not has_rows)
        self._update_job_filter_options()
        self.apply_job_filter()

    def load_services(self):
        self.service_table.setRowCount(0)
        cur = getattr(self.db, "cursor", None)
        if cur is None:
            return
        try:
            cur.execute("""
                SELECT tracking_no, customer_name, status, device_brand, device_model,
                       labor_cost, entry_date, exit_date, technician
                FROM devices
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY entry_date DESC
            """)
            rows = cur.fetchall()
        except Exception:
            rows = []
        for row in rows:
            srv_no = row[0] or ""
            customer = row[1] or ""
            status = row[2] or ""
            dev = f"{row[3] or ''} {row[4] or ''}".strip()
            labor_cost = float(row[5] or 0.0)
            entry_date = row[6] or ""
            exit_date = row[7] or ""
            tech = row[8] or ""
            parts_total = 0.0
            try:
                cur.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(price, 0) * COALESCE(quantity, 1)), 0)
                    FROM used_parts
                    WHERE tracking_no=?
                      AND (is_deleted IS NULL OR is_deleted=0)
                    """,
                    (srv_no,),
                )
                parts_total = float(cur.fetchone()[0] or 0.0)
            except Exception:
                parts_total = 0.0
            total = labor_cost + parts_total
            r = self.service_table.rowCount()
            self.service_table.insertRow(r)
            self.service_table.setItem(r, 0, QTableWidgetItem(srv_no))
            self.service_table.setItem(r, 1, QTableWidgetItem(customer))
            self.service_table.setItem(r, 2, QTableWidgetItem(status))
            self.service_table.setItem(r, 3, QTableWidgetItem(dev))
            self.service_table.setItem(r, 4, QTableWidgetItem(f"{total:,.2f}"))
            self.service_table.setItem(r, 5, QTableWidgetItem(self._format_tr_date(entry_date)))
            self.service_table.setItem(r, 6, QTableWidgetItem(self._format_tr_date(exit_date)))
            self.service_table.item(r, 5).setToolTip(str(entry_date or ''))
            self.service_table.item(r, 6).setToolTip(str(exit_date or ''))
            self.service_table.setItem(r, 7, QTableWidgetItem(tech))
            self._set_report_number_fonts(self.service_table, r, (0, 4, 5, 6))
            self._set_report_status_badge(self.service_table, r)
            self._set_service_actions(r, srv_no)
        has_rows = self.service_table.rowCount() > 0
        self.service_table.setVisible(has_rows)
        self.service_empty_state.setVisible(not has_rows)
        self.apply_service_filter()

    def update_stat_cards(self):
        """İstatistik kartlarını güncelle"""
        try:
            cur = getattr(self.db, "cursor", None)
            if cur is None:
                return

            # İş Takip Istatistikleri
            try:
                # Toplam İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE transaction_type = 'DEBIT'
                      AND tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                """)
                total_jobs = cur.fetchone()[0] or 0
                labels = self.card_total_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(total_jobs))

                # Açık İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                    GROUP BY tracking_no
                    HAVING SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) >
                           SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END)
                """)
                open_groups = cur.fetchall() or []
                open_jobs = len(open_groups)
                labels = self.card_open_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(open_jobs))

                # Tahsil Edilen İşler
                cur.execute("""
                    SELECT COUNT(DISTINCT tracking_no)
                    FROM currency_transactions
                    WHERE tracking_no IS NOT NULL
                      AND TRIM(COALESCE(tracking_no, '')) <> ''
                    GROUP BY tracking_no
                    HAVING ABS(
                        SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END) -
                        SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END)
                    ) <= 0.01
                """)
                paid_groups = cur.fetchall() or []
                paid_jobs = len(paid_groups)
                labels = self.card_paid_jobs.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(paid_jobs))

                # Servis Takip Istatistikleri
                cur.execute("SELECT COUNT(*) FROM devices")
                total_services = cur.fetchone()[0] or 0
                labels = self.card_total_services.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(total_services))

                # Tamamlanan Servisler
                cur.execute("""
                    SELECT COUNT(*) FROM devices
                    WHERE status IN ('Teslim Edildi', 'Tamir Edildi', 'Hazır')
                """)
                completed_services = cur.fetchone()[0] or 0
                labels = self.card_completed_services.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(str(completed_services))

                # Toplam Tahsilat
                cur.execute("""
                    SELECT SUM(try_equivalent) FROM currency_transactions
                    WHERE transaction_type = 'CREDIT'
                """)
                total_revenue = float(cur.fetchone()[0] or 0)
                labels = self.card_total_revenue.findChildren(QLabel)
                if len(labels) > 1:
                    labels[1].setText(
                        CurrencyHelper.format_try_for_display(total_revenue, db=self.db, include_try_reference=False)
                    )

            except Exception:
                pass

        except Exception:
            pass

    def show_monthly_report(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Aylık İş / Servis Analizi")
        dlg.resize(600, 400)
        dlg.setModal(True)
        dlg.setStyleSheet(theme_qss("QDialog { background-color: @surface_alt; }"))

        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(24, 24, 24, 24)
        vbox.setSpacing(18)

        title = QLabel("Aylık Özet")
        title.setFont(QFont(DesignTokens.FONT_NAME, 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        vbox.addWidget(title)

        desc = QLabel("Son 12 ay için gelen cihaz ve iş adetleri, kapanan servisler ve tahsilatlı işler.")
        desc.setStyleSheet(theme_qss("color: @text_muted;"))
        desc.setWordWrap(True)
        vbox.addWidget(desc)

        today = QDate.currentDate()
        cur = getattr(self.db, "cursor", None)

        rows = []
        for i in range(12):
            month_date = today.addMonths(-i)
            month_label = month_date.toString("MM.yyyy")

            srv_new = 0
            srv_done = 0
            job_paid = 0
            job_total = 0.0

            if cur is not None:
                try:
                    start = QDate(month_date.year(), month_date.month(), 1).toString("yyyy-MM-dd")
                    next_month = month_date.addMonths(1)
                    end = QDate(next_month.year(), next_month.month(), 1).toString("yyyy-MM-dd")
                    
                    # 1. Yeni Servis Kaydı
                    cur.execute(
                        "SELECT COUNT(*) FROM devices WHERE entry_date >= ? AND entry_date < ?",
                        (start, end),
                    )
                    srv_new = cur.fetchone()[0] or 0
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage new services stat error: {e}")
                    srv_new = 0

                try:
                    # 2. Tamamlanan Servis
                    cur.execute(
                        "SELECT COUNT(*) FROM devices WHERE status IN ('Teslim Edildi','Tamir Edildi','Hazır') "
                        "AND COALESCE(exit_date, delivered_at, entry_date) >= ? AND COALESCE(exit_date, delivered_at, entry_date) < ?",
                        (start, end),
                    )
                    srv_done = cur.fetchone()[0] or 0
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage done services stat error: {e}")
                    srv_done = 0

                try:
                    # 3. Tahsilatlı İş ve Tutar
                    # (Note: Job tracking uses currency_transactions DEBIT/CREDIT now in AYEC Pro, 
                    # but if 'Peşin Satış: JOB%' works, we keep it, or we look at currency_transactions)
                    # For safety, let's fix the SQL syntax first.
                    cur.execute(
                        "SELECT COUNT(*), SUM(amount) FROM accounting WHERE category='Tahsilat' "
                        "AND date >= ? AND date < ?",
                        (start, end),
                    )
                    res = cur.fetchone() or (0, 0.0)
                    job_paid = res[0] or 0
                    job_total = float(res[1] or 0.0)
                except Exception as e:
                    logger.error(f"JobServiceTrackingPage paid jobs stat error: {e}")
                    job_paid = 0
                    job_total = 0.0

            rows.append((month_label, srv_new, srv_done, job_paid, job_total))

        if rows:
            current = rows[0]
        else:
            current = ("", 0, 0, 0, 0.0)

        cards = QHBoxLayout()
        cards.setSpacing(12)

        def add_card(title_text, value_text, color_bg, color_fg):
            card = QFrame()
            card.setStyleSheet(theme_qss(
                f"QFrame {{ background-color: {color_bg}; border-radius: 12px; padding: 12px 16px; }} "
                "QLabel { border: none; }"
            ))
            c_layout = QVBoxLayout(card)
            c_layout.setContentsMargins(0, 0, 0, 0)
            c_layout.setSpacing(4)
            lbl_t = QLabel(title_text)
            lbl_t.setStyleSheet(theme_qss(f"color: {color_fg}; font-size: 11px; font-weight: 600;"))
            lbl_v = QLabel(value_text)
            lbl_v.setStyleSheet(theme_qss(f"color: {color_fg}; font-size: 18px; font-weight: 700;"))
            c_layout.addWidget(lbl_t)
            c_layout.addWidget(lbl_v)
            cards.addWidget(card)

        add_card("Bu Ay Gelen Servis", str(current[1]), tc("selection_bg"), tc("accent_pressed"))
        add_card("Bu Ay Tamamlanan Servis", str(current[2]), tc("surface_alt"), tc("success"))
        add_card("Bu Ay Tahsilatlı İş", str(current[3]), tc("warning_bg"), tc("warning"))
        add_card(
            "Bu Ay Tahsilat Tutarı",
            CurrencyHelper.format_try_for_display(current[4], db=self.db, include_try_reference=False),
            tc("warning_bg"),
            tc("warning"),
        )

        cards.addStretch()
        vbox.addLayout(cards)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        header_labels = ["Ay", "Yeni Servis Kaydı", "Tamamlanan Servis", "Tahsilatlı İş", "Tahsilat Tutarı"]
        for c, text in enumerate(header_labels):
            lbl = QLabel(text)
            lbl.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text_muted;"))
            grid.addWidget(lbl, 0, c)

        for row_idx, (month_label, srv_new, srv_done, job_paid, job_total) in enumerate(rows, start=1):
            lbl_month = QLabel(month_label)
            lbl_month.setStyleSheet(theme_qss("color: @selection_text;"))
            grid.addWidget(lbl_month, row_idx, 0)

            lbl_new = QLabel(str(srv_new))
            lbl_new.setStyleSheet(theme_qss("color: @accent_hover; font-weight: 600;"))
            grid.addWidget(lbl_new, row_idx, 1)

            lbl_done = QLabel(str(srv_done))
            lbl_done.setStyleSheet(theme_qss("color: @success; font-weight: 600;"))
            grid.addWidget(lbl_done, row_idx, 2)

            lbl_job = QLabel(str(job_paid))
            lbl_job.setStyleSheet(theme_qss("color: @warning; font-weight: 600;"))
            grid.addWidget(lbl_job, row_idx, 3)

            lbl_total = QLabel(f"{job_total:,.2f}")
            lbl_total.setStyleSheet(theme_qss("color: @selection_text; font-weight: 600;"))
            grid.addWidget(lbl_total, row_idx, 4)

        vbox.addLayout(grid)

        close_row = QHBoxLayout()
        close_row.addStretch()
        btn_close = QPushButton("Kapat")
        btn_close.setFixedHeight(34)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        except Exception:
            btn_close.setStyleSheet(theme_qss(
                "QPushButton { background-color: @border; color: @selection_text; border-radius: 8px; padding: 6px 16px; "
                "border: 1px solid @border; } QPushButton:hover { background-color: @border; }"
            ))
        btn_close.clicked.connect(dlg.accept)
        close_row.addWidget(btn_close)
        vbox.addLayout(close_row)

        dlg.exec()

    def on_job_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=201):
            return
        index = self.job_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        self.job_table.selectRow(row)
        job_no_item = self.job_table.item(row, 0)
        if not job_no_item:
            pass # Keep logic intact if they were just read for some side effect, or just read the item. Actually, better just remove the assignment.
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu { background-color: @surface; border: 1px solid @border; padding: 4px; }
            QMenu::item { padding: 8px 18px; color: @selection_text; }
            QMenu::item:selected { background-color: @accent_hover; color: @surface; }
        """))
        act_detail = menu.addAction("🔍 İş Detayı")
        action = menu.exec(self.job_table.viewport().mapToGlobal(pos))
        if action != act_detail:
            return
        try:
            self._open_job_detail(row)
        except Exception as e:
            logger.error(f"Archive action failed: {e}")

    def on_service_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=201):
            return
        index = self.service_table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        self.service_table.selectRow(row)
        item_tracking = self.service_table.item(row, 0)
        tracking_no = item_tracking.text() if item_tracking else ""
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss("""
            QMenu { background-color: @surface; border: 1px solid @border; padding: 4px; }
            QMenu::item { padding: 8px 18px; color: @selection_text; }
            QMenu::item:selected { background-color: @accent_hover; color: @surface; }
        """))
        act_detail = menu.addAction("🔍 Detay")
        act_panel = menu.addAction("🛠️ Teknisyen Paneli")
        act_form = menu.addAction("📝 Servis Formu")
        action = menu.exec(self.service_table.viewport().mapToGlobal(pos))
        if not tracking_no:
            return
        try:
            if action == act_detail:
                self._open_service_archive_detail(tracking_no)
            elif action == act_panel and self.main_window is not None and hasattr(self.main_window, "open_technician_panel"):
                self.main_window.open_technician_panel(tracking_no)
            elif action == act_form and self.main_window is not None and hasattr(self.main_window, "open_service_form"):
                self.main_window.open_service_form(tracking_no)
        except Exception as e:
            logger.error(f"Archive action failed: {e}")


