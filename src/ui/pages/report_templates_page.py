from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QIcon, QKeySequence, QPainter, QPalette, QPen, QPixmap, QShortcut
from PyQt6.QtCore import QRect, QSize, Qt
import csv
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QGridLayout,
    QHeaderView,
    QFrame,
    QSplitter,
    QScrollArea,
    QTabBar,
    QLabel,
    QLineEdit,
    QLayout,
    QPushButton,
    QPlainTextEdit,
    QStyle,
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QMenu,
    QWidget,
    QApplication,
    QFileDialog,
    QMessageBox,
    QToolButton,
    QComboBox,
)
from datetime import date
import json
import time

from src.ui.dialogs.quick_notes_editor import QuickNotesEditor
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.reference_status_delegate import ReferenceStatusDelegate
from src.ui.widgets.navigation_glyph import navigation_icon


class _TemplatePreviewText(QPlainTextEdit):
    def text(self):
        return self.toPlainText()

    def setText(self, text):
        self.setPlainText(str(text))


class _ReferenceSearchLineEdit(QLineEdit):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        badge = self.rect().adjusted(self.width() - 66, 8, -9, -8)
        painter.setPen(QColor("#334155"))
        painter.setBrush(QColor("#1e293b"))
        painter.drawRoundedRect(badge, 4, 4)
        painter.setPen(QColor("#94a3b8"))
        painter.setFont(QFont("JetBrains Mono", 8))
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "Ctrl + F")


class _TemplateLabelDelegate(QStyledItemDelegate):
    @staticmethod
    def _split_text(text):
        title, separator, detail = str(text or "").partition(" (")
        if separator:
            nested_title, nested_separator, nested_detail = detail.partition(") (")
            if nested_separator:
                title = title + " (" + nested_title + ")"
                detail = "(" + nested_detail
            else:
                detail = "(" + detail
        else:
            detail = ""
        return title, detail

    def sizeHint(self, option, index):
        title, detail = self._split_text(index.data(Qt.ItemDataRole.DisplayRole))
        text_width = max(24, option.rect.width() - 20)
        title_width = int(text_width * 0.55)
        detail_width = max(24, text_width - title_width - 5)
        flags = Qt.TextFlag.TextWordWrap
        title_font = QFont("Inter", 9, QFont.Weight.Bold)
        title_height = QFontMetrics(title_font).boundingRect(
            QRect(0, 0, title_width, 1000), int(flags), title
        ).height()
        detail_font = QFont("Inter", 8)
        detail_height = QFontMetrics(detail_font).boundingRect(
            QRect(0, 0, detail_width, 1000), int(flags), detail
        ).height() if detail else 0
        if detail and len(title) <= 13 and len(detail) > 28:
            row_minimum = 130
        elif detail and (len(title) > 13 or len(detail) > 28):
            row_minimum = 112
        else:
            row_minimum = 76
        return QSize(option.rect.width(), max(row_minimum, max(title_height, detail_height) + 24))

    def paint(self, painter, option, index):
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        text = item.text
        item.text = ""
        style = item.widget.style() if item.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, item.widget)
        title, detail = self._split_text(text)
        category = str(index.data(Qt.ItemDataRole.UserRole) or "").lower()
        text_color = item.palette.color(QPalette.ColorRole.Text)
        light_background = item.palette.color(QPalette.ColorRole.Base).lightness() >= 150
        title_color = text_color if light_background else QColor(
            "#38bdf8" if "i\u015flem" in category else (
                "#34d399" if "gizli" in category else "#f8fafc"
            )
        )
        rect = option.rect.adjusted(12, 4, -8, -4)
        title_width = int(rect.width() * 0.55)
        title_rect = QRect(rect.x(), rect.y(), title_width, rect.height())
        detail_rect = QRect(title_rect.right() + 5, rect.y(), rect.width() - title_width - 5, rect.height())
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        font = QFont("Inter", 9)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(title_color)
        flags = int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter) | int(Qt.TextFlag.TextWordWrap)
        painter.drawText(title_rect, flags, title)
        if detail:
            font.setPointSize(8)
            font.setWeight(QFont.Weight.Normal)
            painter.setFont(font)
            detail_color = QColor(text_color if light_background else "#94a3b8")
            painter.setPen(detail_color)
            painter.drawText(detail_rect, flags, detail)
        painter.restore()


class ReportTemplatesPage(QWidget):
    PAGE_SIZE = 10

    def __init__(self, db, main_window=None):
        super().__init__(main_window)
        self.db = db
        self.main_window = main_window
        self.current_page = 1
        self.page_size = self.PAGE_SIZE
        self.total_count = 0
        self._rows = []
        self._selection_started_at = time.monotonic()
        self._usage_metrics = self._load_usage_metrics()
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        self.setMinimumSize(0, 0)
        root = QVBoxLayout(self)
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        root.setContentsMargins(0, 27, 0, 2)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setContentsMargins(24, 0, 20, 0)
        self.header_layout = header
        title_box = QVBoxLayout()
        title = QLabel("\u275d    Rapor C\u00fcmle Kal\u0131plar\u0131")
        title.setFixedWidth(286)
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setStyleSheet(
            theme_qss("font-size: 20px; font-weight: 800; color: @text; background: transparent; border: none;")
        )
        description = QLabel(
            "Servis kabul, teknisyen te\u015fhis paneli ve fatura teslim tutanaklar\u0131nda "
            "kullan\u0131lan h\u0131zl\u0131 se\u00e7im haz\u0131r c\u00fcmlelerini y\u00f6netin."
        )
        description.setMaximumWidth(680)
        description.setMinimumHeight(34)
        description.setWordWrap(True)
        description.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; background: transparent; border: none;"))
        title_row = QHBoxLayout()
        title_row.setSpacing(10)
        title_row.addWidget(title)
        self.total_badge = QLabel("Toplam 0 \u015eablon")
        self.total_badge.setFixedSize(163, 28)
        self.total_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_badge.setStyleSheet(theme_qss(
            "QLabel { color: @electric_blue; background: #0b2b3d; border: 1px solid @electric_blue; "
            "border-radius: 14px; padding: 3px 10px; font-size: 12px; font-weight: 700; }"
        ))
        title_row.addWidget(self.total_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch(1)
        title_box.addLayout(title_row)
        title_box.addWidget(description)
        header.addLayout(title_box, 1)
        self.import_button = QPushButton("\u0130\u00e7e/D\u0131\u015fa\nAktar")
        self.import_button.setIcon(navigation_icon("document", 16, "text_muted"))
        self.import_button.setIconSize(QSize(16, 16))
        import_menu = QMenu(self.import_button)
        import_menu.addAction("CSV\u2019den \u0130\u00e7e Aktar", self.import_templates)
        import_menu.addAction("CSV\u2019ye D\u0131\u015fa Aktar", self.export_templates)
        self.import_button.setMenu(import_menu)
        self.import_button.setToolTip("CSV kal\u0131plar\u0131n\u0131 i\u00e7e veya d\u0131\u015fa aktar")
        manage_button = QPushButton("Kal\u0131plar\u0131\nY\u00f6net")
        manage_button.setIcon(navigation_icon("filter", 16, "text_muted"))
        manage_button.setIconSize(QSize(16, 16))
        manage_button.clicked.connect(self.open_editor)
        self.add_button = QPushButton("Yeni C\u00fcmle Kal\u0131b\u0131\nEkle")
        self.add_button.setIcon(navigation_icon("plus_circle", 17, "selection_text"))
        self.add_button.setIconSize(QSize(17, 17))
        self.add_button.clicked.connect(self._add_template)
        for button, role in ((self.import_button, "secondary"), (manage_button, "secondary"), (self.add_button, "primary")):
            button.setFixedHeight(44)
            button.setStyleSheet(theme_qss(
                DesignTokens.get_button_qss(role)
                + " QPushButton { font-size: 12px; font-weight: 700; padding: 3px 8px; }"
            ))
            header.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)
        self.import_button.setFixedWidth(143)
        manage_button.setFixedWidth(143)
        self.add_button.setFixedWidth(192)
        root.addLayout(header)
        self.mobile_action_row = QHBoxLayout()
        self.mobile_action_row.setContentsMargins(24, 0, 20, 0)
        self.mobile_action_row.setSpacing(8)
        root.addLayout(self.mobile_action_row)
        self.header_action_widgets = (self.import_button, manage_button, self.add_button)
        for button in self.header_action_widgets:
            self.header_layout.removeWidget(button)
            self.mobile_action_row.addWidget(button)
        self._actions_in_mobile_row = True

        metrics = QHBoxLayout()
        metrics.setContentsMargins(24, 0, 20, 0)
        metrics.setSpacing(10)
        self.metric_total = self._metric_card("Toplam \u015eablon", "0")
        self.metric_active = self._metric_card("Aktif \u015eablon", "0")
        self.metric_categories = self._metric_card("Kategori \u00c7e\u015fitlili\u011fi", "0")
        for metric in (self.metric_total, self.metric_active, self.metric_categories):
            metrics.addWidget(metric, 1)
        for metric in (self.metric_total, self.metric_active, self.metric_categories):
            metric.hide()
        root.addLayout(metrics)
        root.addSpacing(14)

        self.category_tabs = QTabBar()
        self.category_tabs.setExpanding(False)
        self.category_tabs.setUsesScrollButtons(True)
        self.category_tabs.setDrawBase(False)
        self.category_tabs.setStyleSheet(theme_qss(
            "QTabBar::tab { background: @surface; color: @text_muted; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px 18px; margin-right: 6px; font-size: 14px; } "
            "QTabBar::tab:selected { background: @electric_blue; color: @selection_text; "
            "border-color: @electric_blue; }"
        ))
        self.category_tabs.currentChanged.connect(self._category_tab_changed)
        tabs_container = QWidget(self)
        tabs_layout = QHBoxLayout(tabs_container)
        tabs_layout.setContentsMargins(24, 0, 20, 0)
        tabs_layout.addWidget(self.category_tabs)
        root.addWidget(tabs_container)
        root.addSpacing(33)
        self.filter_grid = QGridLayout()
        self.filter_grid.setContentsMargins(24, 0, 20, 0)
        self.search = _ReferenceSearchLineEdit()
        search_icon = QPixmap(16, 16)
        search_icon.fill(Qt.GlobalColor.transparent)
        search_painter = QPainter(search_icon)
        search_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        search_painter.setPen(QColor("#64748b"))
        search_painter.drawEllipse(2, 2, 9, 9)
        search_painter.drawLine(10, 10, 14, 14)
        search_painter.end()
        self.search.addAction(QIcon(search_icon), QLineEdit.ActionPosition.LeadingPosition)
        self.search.setTextMargins(0, 0, 64, 0)
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(self.search.setFocus)
        self.search.setPlaceholderText("Kategori, cihaz t\u00fcr\u00fc veya kal\u0131p metni ara... (\u00d6rn: G\u00d6R\u00dcNT\u00dc YOK)")
        self.search.setMaximumWidth(650)
        self.search.textChanged.connect(self._search_changed)
        refresh_button = QPushButton("Yenile")
        self.refresh_button = refresh_button
        refresh_button.clicked.connect(self.refresh_data)
        self.device_filter = ModernComboBox()
        self.device_filter.setFixedWidth(270)
        self.device_filter.addItem('T\u00fcm Cihazlar (PC, Telefon, Tablet)', '')
        self.device_filter.currentIndexChanged.connect(self._search_changed)
        self.device_filter_label = QLabel("Cihaz:")
        self.status_filter_label = QLabel("Durum:")
        for label in (self.device_filter_label, self.status_filter_label):
            label.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        self.category_filter = ModernComboBox()
        self.category_filter.setMinimumWidth(180)
        self.category_filter.currentIndexChanged.connect(self._search_changed)
        self.status_filter = ModernComboBox()
        self.status_filter.addItem("T\u00fcm Durumlar", "all")
        self.status_filter.addItem("Aktif Kal\u0131plar", "active")
        self.status_filter.addItem("Pasif Kal\u0131plar", "inactive")
        self.status_filter.setCurrentIndex(1)
        self.status_filter.setFixedWidth(120)
        self.status_filter.currentIndexChanged.connect(self._search_changed)
        self.search.setFixedHeight(38)
        refresh_button.setFixedSize(40, 38)
        filter_icon = QPixmap(16, 16)
        filter_icon.fill(Qt.GlobalColor.transparent)
        filter_painter = QPainter(filter_icon)
        filter_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        filter_painter.setPen(QPen(QColor("#94a3b8"), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        filter_painter.drawLine(2, 3, 14, 3)
        filter_painter.drawLine(2, 3, 6, 8)
        filter_painter.drawLine(14, 3, 10, 8)
        filter_painter.drawLine(6, 8, 10, 8)
        filter_painter.drawLine(8, 8, 8, 14)
        filter_painter.end()
        refresh_button.setText("")
        refresh_button.setIcon(QIcon(filter_icon))
        refresh_button.setIconSize(QSize(16, 16))
        refresh_button.setToolTip("Yenile")
        refresh_button.setStyleSheet(theme_qss(
            "QPushButton { background: @surface; color: @text_muted; border: 1px solid @border; border-radius: 8px; }"
            "QPushButton:hover { background: @surface_alt; color: @electric_blue; border-color: @electric_blue; }"
        ))
        for control in (self.device_filter, self.category_filter, self.status_filter):
            control.setFixedHeight(38)
            control.set_reference_chevron()
        self.device_filter.setStyleSheet(self.device_filter.styleSheet() + theme_qss(
            "QComboBox { padding-left: 8px; padding-right: 20px; } "
            "QComboBox::drop-down { width: 20px; }"
        ))
        self.status_filter.setStyleSheet(self.status_filter.styleSheet() + theme_qss(
            "QComboBox { min-width: 120px; max-width: 120px; padding-left: 8px; padding-right: 24px; }"
            "QComboBox::drop-down { width: 20px; }"
        ))
        root.addLayout(self.filter_grid)
        self._layout_filters(self.width())

        self.table = QTableWidget(0, 8)
        self.table.setMinimumWidth(0)
        self.table.setHorizontalHeaderLabels(
            ["KATEGOR\u0130 & KAPSAM", "C\u00dcMLE KALIBI /\nHAZIR MET\u0130N", "DURUM", "#", "KULLANIM\nALANI", "KISAYOL", "", "\u0130\u015eLEMLER"]
        )
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(False)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(theme_qss(
            DesignTokens.get_table_qss() +
            " QTableWidget { background: @bg; gridline-color: transparent; font-size: 12px; } "
            " QTableWidget::item { padding: 0 8px; } "
            " QTableWidget::item:selected { background: @surface_alt; color: @text; } "
            " QHeaderView::section { background: @surface; color: @text_muted; "
            "border: none; border-bottom: 1px solid @border; padding: 10px 7px; "
                "font-size: 11px; font-weight: 800; }"
        ))
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(64)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setWordWrap(True)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setItemDelegateForColumn(2, ReferenceStatusDelegate(self.table))
        self.table.setItemDelegateForColumn(1, _TemplateLabelDelegate(self.table))
        self.table.horizontalHeader().setFixedHeight(54)
        for column, width in {
            0: 280, 1: 210, 2: 70, 3: 48,
            4: 105, 5: 56, 6: 38, 7: 80,
        }.items():
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Fixed
            )
            self.table.horizontalHeader().resizeSection(column, width)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.horizontalHeaderItem(6).setText("\u2195")
        self.table.horizontalHeaderItem(6).setToolTip("S\u0131rala")
        self.table.horizontalHeaderItem(7).setText("")
        self.table.horizontalHeaderItem(7).setToolTip("\u0130\u015flemler")
        self.table.horizontalHeader().moveSection(3, 0)
        self.table.horizontalHeader().moveSection(4, 3)
        self.table.horizontalHeader().moveSection(5, 4)
        self.table.horizontalHeader().moveSection(6, 1)
        self.table.horizontalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.template_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table_panel = QWidget(self)
        self.table_panel_layout = QVBoxLayout(self.table_panel)
        self.table_panel_layout.setContentsMargins(0, 0, 0, 0)
        self.table_panel_layout.setSpacing(0)
        self.table_panel_layout.addWidget(self.table, 1)
        self.template_splitter.addWidget(self.table_panel)
        preview = QFrame()
        preview.setObjectName("ReportTemplatePreview")
        preview.setMinimumWidth(0)
        preview.setStyleSheet(theme_qss(
            "QFrame#ReportTemplatePreview { background: @surface; border: 1px solid @border; border-radius: 6px; }"
        ))
        preview_layout = QVBoxLayout(preview)
        self.preview_layout = preview_layout
        preview_layout.setContentsMargins(18, 24, 18, 18)
        preview_header = QWidget(preview)
        preview_header_layout = QHBoxLayout(preview_header)
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_layout.setSpacing(6)
        preview_heading_icon = QLabel("\u25c9")
        preview_heading_icon.setStyleSheet(theme_qss("color: @electric_blue; font-size: 16px;"))
        preview_title = QLabel("CANLI \u00c7IKTI \u00d6N\u0130ZLEME")
        preview_title.setStyleSheet(theme_qss("color: @text; font-size: 13px; font-weight: 800;"))
        preview_header_layout.addWidget(preview_heading_icon)
        preview_header_layout.addWidget(preview_title)
        preview_header_layout.addStretch(1)
        self.preview_id = QLabel("Se\u00e7ili \u015eablon #01")
        self.preview_id.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_id.setFixedSize(124, 24)
        self.preview_id.setStyleSheet(theme_qss(
            "color: @finance_action_income; background: @finance_active_bg; border: 1px solid @finance_outline; "
            "border-radius: 5px; padding: 0 7px; font-family: " + DesignTokens.MONO_FONT_FAMILY + "; font-size: 10px;"
        ))
        preview_header_layout.addWidget(self.preview_id)
        preview_layout.addWidget(preview_header)
        receipt = QFrame()
        receipt.setObjectName('ReportTemplateReceipt')
        receipt.setFixedHeight(427)
        self.preview_receipt = receipt
        receipt.setStyleSheet(theme_qss(
            'QFrame#ReportTemplateReceipt { background: @finance_surface_lowest; '
            'border: 1px solid @finance_outline; border-radius: 12px; }'
        ))
        receipt_layout = QVBoxLayout(receipt)
        self.preview_receipt_layout = receipt_layout
        receipt_layout.setContentsMargins(20, 20, 20, 20)
        receipt_layout.setSpacing(8)
        company = 'AYEC Pro'
        try:
            company = self.db.get_setting('company_name', company) or company
        except (AttributeError, TypeError):
            pass
        self.preview_company = QLabel(str(company))
        self.preview_company.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_company.setWordWrap(True)
        self.preview_company.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_company.setStyleSheet(theme_qss('color: @finance_text; font-weight: 800; font-size: 16px;'))
        receipt_layout.addWidget(self.preview_company)
        document_type = QLabel('AYEC PRO TEKN\u0130K SERV\u0130S F\u0130\u015e\u0130')
        self.preview_document_type = document_type
        document_type.setAlignment(Qt.AlignmentFlag.AlignCenter)
        document_type.setStyleSheet(theme_qss('color: @text_muted; font-size: 10px;'))
        receipt_layout.addWidget(document_type)
        self.preview_serial = QLabel('SERI NO: -')
        self.preview_serial.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_serial.setStyleSheet(theme_qss(
            'color: @text_muted; font-family: ' + DesignTokens.MONO_FONT_FAMILY + '; font-size: 9px;'
        ))
        receipt_layout.addWidget(self.preview_serial)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
        self.preview_header_rule = rule
        receipt_layout.addWidget(rule)
        self.preview_context_labels = []
        self.preview_context_values = {}
        for caption, object_name, key in (
            ('M\u00fc\u015fteri:', 'ReportTemplateCustomer', 'customer'),
            ('Cihaz:', 'ReportTemplateDevice', 'device'),
        ):
            context_row = QWidget(receipt)
            context_layout = QHBoxLayout(context_row)
            context_layout.setContentsMargins(0, 0, 0, 0)
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(theme_qss('color: @text_muted; font-size: 12px;'))
            value_label = QLabel('\u2014')
            value_label.setObjectName(object_name)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_label.setStyleSheet(theme_qss('color: @text; font-size: 12px; font-weight: 700;'))
            context_layout.addWidget(caption_label)
            context_layout.addWidget(value_label, 1)
            receipt_layout.addWidget(context_row)
            self.preview_context_labels.append(context_row)
            self.preview_context_values[key] = value_label
        receipt_rule = QFrame()
        receipt_rule.setFixedHeight(1)
        receipt_rule.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
        self.preview_context_rule = receipt_rule
        receipt_layout.addWidget(receipt_rule)
        self.preview_category = QLabel("")
        self.preview_category.setTextFormat(Qt.TextFormat.PlainText)
        self.preview_category.setWordWrap(True)
        self.preview_category.setStyleSheet(theme_qss("color: @accent; font-weight: 700;"))
        self.preview_template_type = QLabel("")
        self.preview_template_type.setWordWrap(True)
        self.preview_template_type.setStyleSheet(theme_qss(
            "color: @finance_action_expense; font-size: 11px; font-weight: 800;"
        ))
        self.preview_text = _TemplatePreviewText()
        self.preview_text.setText("\u00d6nizlemek i\u00e7in bir \u015fablon se\u00e7in.")
        self.preview_text.setReadOnly(True)
        self.preview_text.setFixedHeight(44)
        self.preview_text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.preview_text.setStyleSheet(theme_qss(
            'color: @finance_text; background: @finance_surface; border: 1px solid @finance_outline; '
            'border-radius: 6px; padding: 12px; font-size: 14px;'
        ))
        receipt_layout.addWidget(self.preview_category)
        receipt_layout.addSpacing(14)
        receipt_layout.addWidget(self.preview_template_type)
        receipt_layout.addSpacing(6)
        receipt_layout.addWidget(self.preview_text)
        receipt_layout.addSpacing(18)
        receipt_layout.addStretch(1)
        self.preview_accessory_title = QLabel('ALINAN AKSESUAR:')
        self.preview_accessory_title.setStyleSheet(theme_qss(
            'color: @warning; font-size: 10px; font-weight: 800;'
        ))
        receipt_layout.addWidget(self.preview_accessory_title)
        self.preview_accessory = QLabel('\u2014')
        self.preview_accessory.setWordWrap(True)
        self.preview_accessory.setMinimumHeight(54)
        self.preview_accessory.setStyleSheet(theme_qss(
            'color: @text; background: @surface; border: 1px solid @border; '
            'border-radius: 6px; padding: 7px; font-family: ' + DesignTokens.MONO_FONT_FAMILY + '; font-size: 11px;'
        ))
        receipt_layout.addWidget(self.preview_accessory)
        footer_rule = QFrame()
        footer_rule.setFixedHeight(1)
        footer_rule.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
        receipt_layout.addWidget(footer_rule)
        self.preview_footer_rule = footer_rule
        footer_row = QWidget(receipt)
        self.preview_footer_row = footer_row
        footer_layout = QHBoxLayout(footer_row)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_date = QLabel('Tarih: -')
        self.preview_date.setStyleSheet(theme_qss(
            'color: @text_muted; font-family: ' + DesignTokens.MONO_FONT_FAMILY + '; font-size: 9px;'
        ))
        footer_layout.addWidget(self.preview_date)
        footer_layout.addStretch(1)
        receipt_layout.addWidget(footer_row)
        self.preview_status = QLabel('')
        self.preview_status.setObjectName("ReportTemplateStatus")
        self.preview_status.setStyleSheet(theme_qss('color: @finance_action_income; font-size: 11px;'))
        receipt_layout.addWidget(self.preview_status)
        preview_layout.addSpacing(10)
        preview_layout.addWidget(receipt, 0)
        preview_layout.addSpacing(14)
        self.preview_stats = QFrame()
        self.preview_stats.setObjectName("ReportTemplateStats")
        self.preview_stats.setFixedHeight(134)
        self.preview_stats.setStyleSheet(theme_qss(
            "QFrame#ReportTemplateStats { background: @surface; border: 1px solid @border; "
            "border-radius: 10px; }"
        ))
        stats_layout = QVBoxLayout(self.preview_stats)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(10)
        stats_title = QLabel("\u015eablon \u0130statistikleri")
        stats_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700;"))
        stats_layout.addWidget(stats_title)
        stats_values = QHBoxLayout()
        self.preview_stat_total = QLabel("0")
        self.preview_stat_active = QLabel("0")
        for label, value in (("Bug\u00fcnk\u00fc Kullan\u0131m", self.preview_stat_total), ("Ortalama Se\u00e7im", self.preview_stat_active)):
            cell = QFrame()
            cell.setStyleSheet(theme_qss("QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"))
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(8, 8, 8, 8)
            caption = QLabel(label)
            caption.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px;"))
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setStyleSheet(theme_qss("color: @accent; font-family: " + DesignTokens.MONO_FONT_FAMILY + "; font-size: 14px; font-weight: 800;"))
            cell_layout.addWidget(caption)
            cell_layout.addWidget(value)
            stats_values.addWidget(cell, 1)
        stats_layout.addLayout(stats_values)
        preview_layout.addWidget(self.preview_stats, 0)
        self.copy_button = QPushButton('Metni Kopyala')
        self.copy_button.clicked.connect(self._copy_selected_template)
        self.copy_button.hide()
        self.preview_assistant = QFrame()
        self.preview_assistant.setObjectName("ReportTemplateAssistant")
        self.preview_assistant.setFixedHeight(72)
        self.preview_assistant.setStyleSheet(theme_qss(
            "QFrame#ReportTemplateAssistant { background: @surface_alt; border: 1px solid @finance_outline; "
            "border-radius: 10px; }"
        ))
        assistant_layout = QHBoxLayout(self.preview_assistant)
        assistant_layout.setContentsMargins(12, 10, 12, 10)
        assistant_icon = QLabel("\u2728")
        assistant_icon.setFixedSize(34, 34)
        assistant_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        assistant_icon.setStyleSheet(theme_qss(
            "color: @electric_blue; background: @finance_surface_lowest; border-radius: 8px; font-size: 16px;"
        ))
        assistant_text = QVBoxLayout()
        assistant_title = QLabel("Ak\u0131ll\u0131 Tamamlama")
        assistant_title.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700;"))
        assistant_description = QLabel("Teknisyen yazarken otomatik \u00f6nerir")
        assistant_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px;"))
        assistant_text.addWidget(assistant_title)
        assistant_text.addWidget(assistant_description)
        assistant_layout.addWidget(assistant_icon)
        assistant_layout.addLayout(assistant_text, 1)
        preview_layout.addStretch(1)
        preview_layout.addWidget(self.preview_assistant)

        self.template_splitter.addWidget(preview)
        self.preview_panel = preview
        self.template_splitter.setStretchFactor(0, 7)
        self.template_splitter.setStretchFactor(1, 3)
        self.template_splitter.setHandleWidth(1)
        self.template_splitter.setSizes([880, 400])
        self.template_splitter.setMinimumWidth(0)
        self.template_splitter.setChildrenCollapsible(True)
        self.table.itemSelectionChanged.connect(self._update_preview)
        root.addSpacing(4)
        self.template_scroll = QScrollArea()
        self.template_scroll.setWidgetResizable(True)
        self.template_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.template_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.template_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.template_scroll_content = QWidget()
        scroll_layout = QVBoxLayout(self.template_scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(0)
        scroll_layout.addWidget(self.template_splitter, 1)
        self.template_scroll.setWidget(self.template_scroll_content)
        root.addWidget(self.template_scroll, 1)

        self.footer_widget = QWidget(self)
        self.footer_widget.setFixedHeight(78)
        self.footer_widget.setFixedWidth(max(0, int(self.width() * 0.69)))
        footer = QHBoxLayout(self.footer_widget)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(6)
        self.lbl_info = QLabel("")
        footer.addWidget(self.lbl_info)
        footer.addStretch()
        footer.addWidget(QLabel("|"))
        footer.addWidget(QLabel("Sayfa Ba\u015f\u0131na:"))
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItem("10", 10)
        self.page_size_combo.addItem("25", 25)
        self.page_size_combo.addItem("50", 50)
        self.page_size_combo.setFixedSize(48, 36)
        self.page_size_combo.setStyleSheet(theme_qss(
            "QComboBox { min-width: 48px; max-width: 48px; color: @text; background: @surface; "
            "border: 1px solid @border; border-radius: 6px; padding: 4px; }"
        ))
        self.page_size_combo.currentIndexChanged.connect(self._page_size_changed)
        footer.addWidget(self.page_size_combo)
        footer.addSpacing(8)
        self.btn_first = QPushButton("\u00ab\u00ab\n\u0130lk")
        self.btn_first.setFixedSize(54, 48)
        self.btn_first.setToolTip("\u0130lk sayfa")
        self.btn_previous = QPushButton("\u2039\n\u00d6nceki")
        self.btn_previous.setFixedSize(64, 48)
        self.btn_previous.setToolTip("\u00d6nceki sayfa")
        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.hide()
        self.page_numbers = QHBoxLayout()
        self.page_numbers.setContentsMargins(0, 0, 0, 0)
        self.page_numbers.setSpacing(6)
        self.btn_next = QPushButton("Sonraki\n\u203a")
        self.btn_next.setFixedSize(70, 48)
        self.btn_first.clicked.connect(lambda: self._go_to_page(1))
        self.btn_previous.clicked.connect(self.previous_page)
        self.btn_next.clicked.connect(self.next_page)
        footer.addWidget(self.btn_first)
        footer.addWidget(self.btn_previous)
        footer.addLayout(self.page_numbers)
        footer.addWidget(self.btn_next)
        self.table_panel_layout.addWidget(self.footer_widget, 0, Qt.AlignmentFlag.AlignLeft)

    def set_preview_context(self, *, customer='', device='', serial='', accessory='', date=''):
        self.preview_context_values['customer'].setText(str(customer or '\u2014'))
        self.preview_context_values['device'].setText(str(device or '\u2014'))
        self.preview_serial.setText('SERI NO: {}'.format(serial or '\u2014'))
        self.preview_accessory.setText(str(accessory or '\u2014'))
        self.preview_date.setText('Tarih: {}'.format(date or '\u2014'))

    def _layout_filters(self, width):
        while self.filter_grid.count():
            self.filter_grid.takeAt(0)
        self.category_filter.hide()
        for column in range(6):
            self.filter_grid.setColumnStretch(column, 0)
        if width < 650:
            self.filter_grid.addWidget(self.search, 0, 0, 1, 4)
            self.filter_grid.addWidget(self.device_filter_label, 1, 0)
            self.filter_grid.addWidget(self.device_filter, 1, 1, 1, 3)
            self.filter_grid.addWidget(self.status_filter_label, 2, 0)
            self.filter_grid.addWidget(self.status_filter, 2, 1, 1, 2)
            self.filter_grid.addWidget(self.refresh_button, 2, 3)
            self.filter_grid.setColumnStretch(1, 1)
        elif width < 1200:
            self.filter_grid.addWidget(self.search, 0, 0, 1, 5)
            self.filter_grid.addWidget(self.device_filter_label, 1, 0)
            self.filter_grid.addWidget(self.device_filter, 1, 1)
            self.filter_grid.addWidget(self.status_filter_label, 1, 2)
            self.filter_grid.addWidget(self.status_filter, 1, 3)
            self.filter_grid.addWidget(self.refresh_button, 1, 4)
        else:
            self.filter_grid.addWidget(self.search, 0, 0)
            self.filter_grid.addWidget(self.device_filter_label, 0, 1)
            self.filter_grid.addWidget(self.device_filter, 0, 2)
            self.filter_grid.addWidget(self.status_filter_label, 0, 3)
            self.filter_grid.addWidget(self.status_filter, 0, 4)
            self.filter_grid.addWidget(self.refresh_button, 0, 5)
            self.filter_grid.setColumnStretch(0, 1)
        self.status_filter.setFixedWidth(120)

    @staticmethod
    def _device_scope(category):
        parts = str(category or '').split('::')
        return parts[-2].strip() if len(parts) >= 3 else ''

    def _metric_card(self, title, value):
        card = QFrame()
        card.setObjectName("ReportTemplateMetric")
        card.setStyleSheet(theme_qss(
            "QFrame#ReportTemplateMetric { background: @surface; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px; }"
        ))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        label = QLabel(title)
        label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 700;"))
        number = QLabel(value)
        number.setStyleSheet(theme_qss("color: @accent; font-size: 18px; font-weight: 800;"))
        layout.addWidget(label)
        layout.addWidget(number)
        card.metric_value = number
        return card

    @staticmethod
    def _value(row, key, index, default=""):
        if isinstance(row, dict):
            return row.get(key, default)
        if hasattr(row, "keys") and key in row.keys():
            return row[key]
        try:
            return row[index]
        except (IndexError, TypeError):
            return default

    def refresh_data(self):
        try:
            rows = list(self.db.get_fast_notes() or [])
        except Exception:
            rows = []
        self._rows = [
            {
                "id": self._value(row, "id", 0),
                "category": self._value(row, "category", 1),
                "label": self._value(row, "label", 2),
                "is_active": self._value(row, "is_active", 3, 1),
                "display_order": self._value(row, "display_order", 4, 0),
                "display_category": self._value(row, "display_category", 5, ""),
                "title": self._value(row, "title", 6, ""),
            }
            for row in rows
        ]
        selected_device = self.device_filter.currentData()
        self.device_filter.blockSignals(True)
        self.device_filter.clear()
        self.device_filter.addItem('T\u00fcm Cihazlar (PC, Telefon, Tablet)', '')
        for device in sorted({self._device_scope(row['category']) for row in self._rows} - {''}):
            self.device_filter.addItem(device, device)
        self.device_filter.setCurrentIndex(max(0, self.device_filter.findData(selected_device)))
        self.device_filter.blockSignals(False)
        self.total_badge.setText(f"Toplam {len(self._rows):,} \u015eablon")
        self.metric_total.metric_value.setText(f"{len(self._rows):,}")
        self.metric_active.metric_value.setText(
            f"{sum(1 for row in self._rows if int(row.get('is_active') or 0)):,}"
        )
        self.metric_categories.metric_value.setText(
            f"{len({str(row.get('category') or '').strip() for row in self._rows if str(row.get('category') or '').strip()}):,}"
        )
        self._refresh_usage_stats()
        selected = self.category_filter.currentData()
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("T\u00fcm Kategoriler", "")
        reference_categories = (
            "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi",
            "\u0130\u015flem Detay\u0131",
            "Cihaz Testi",
            "Aksesuar",
            "Gizli Not",
        )
        observed_categories = {
            str(row["category"] or "") for row in self._rows if str(row["category"] or "")
        }
        categories = list(reference_categories) + sorted(
            category for category in observed_categories
            if not any(token in category for token in reference_categories)
        )
        for category in categories:
            count = sum(category in str(row["category"] or "") for row in self._rows)
            self.category_filter.addItem(f"{category} ({count})", category)
        self.category_filter.setCurrentIndex(max(0, self.category_filter.findData(selected)))
        self.category_filter.blockSignals(False)
        self.category_tabs.blockSignals(True)
        while self.category_tabs.count():
            self.category_tabs.removeTab(0)
        category_colors = (
            "#0ea5e9", "#f43f5e", "#0ea5e9", "#10b981", "#f59e0b", "#a855f7"
        )
        category_labels = {
            "\u0130\u015flem Detay\u0131": "\u0130\u015flem Detaylar\u0131",
            "Cihaz Testi": "Cihaz Testi && Donan\u0131m",
            "Aksesuar": "Aksesuar Bilgileri",
            "Gizli Not": "Dahili Gizli Not",
        }
        for index in range(self.category_filter.count()):
            label = self.category_filter.itemText(index)
            full_label = label
            if index == 0:
                label = "T\u00fcm\u00fc"
                count = str(len(self._rows))
            else:
                count = label.rsplit("(", 1)[-1].rstrip(")")
                label = label.rsplit("(", 1)[0].strip().rsplit("::", 1)[-1]
                label = category_labels.get(label, label)
            tab_index = self.category_tabs.addTab(label)
            dot = QPixmap(12, 12)
            dot.fill(Qt.GlobalColor.transparent)
            painter = QPainter(dot)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(category_colors[min(index, len(category_colors) - 1)]))
            painter.drawEllipse(1, 1, 10, 10)
            painter.end()
            self.category_tabs.setTabIcon(tab_index, QIcon(dot))
            count_badge = QLabel(count)
            count_badge.setObjectName("ReportTemplateTabCount")
            count_badge.setStyleSheet(theme_qss(
                "QLabel#ReportTemplateTabCount { background: @surface_alt; color: @text; "
                "border-radius: 5px; padding: 2px 6px; font-size: 11px; font-weight: 700; }"
            ))
            self.category_tabs.setTabButton(
                tab_index, QTabBar.ButtonPosition.RightSide, count_badge
            )
            self.category_tabs.setTabToolTip(tab_index, full_label)
        self.category_tabs.setCurrentIndex(self.category_filter.currentIndex())
        self.category_tabs.blockSignals(False)
        self._render()

    def _category_tab_changed(self, index):
        if index >= 0:
            self.category_filter.setCurrentIndex(index)

    def _filtered_rows(self):
        query = self.search.text().strip().lower()
        category = self.category_filter.currentData() or ""
        device = self.device_filter.currentData() or ''
        status = self.status_filter.currentData()
        return [
            row
            for row in self._rows
            if (not category or category in str(row["category"] or ""))
            and (not device or self._device_scope(row['category']) == device)
            and (status == "all" or bool(int(row["is_active"] or 0)) == (status == "active"))
            and (not query or query in str(row["category"]).lower()
                 or query in str(row["label"]).lower())
        ]

    def _render(self):
        rows = self._filtered_rows()
        self.total_count = len(rows)
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * self.page_size
        page_rows = rows[start:start + self.page_size]
        self._visible_rows = page_rows
        self.table.setRowCount(len(page_rows))
        for index, row in enumerate(page_rows):
            category_parts = [part.strip() for part in str(row["category"] or "").split("::") if part.strip()]
            scope = "::".join(category_parts[:2]) if len(category_parts) >= 3 else str(row["category"] or "")
            usage_area = str(row.get("display_category") or (category_parts[-1] if category_parts else ""))
            scope_label = QLabel(scope)
            scope_label.setWordWrap(True)
            scope_label.setMinimumWidth(0)
            scope_label.setFixedWidth(156)
            tone = next((
                (foreground, background)
                for token, foreground, background in (
                    ("Ar\u0131za", "#fb7185", "#2a1420"),
                    ("\u0130\u015flem", "#38bdf8", "#0b2231"),
                    ("Gizli", "#c084fc", "#20162f"),
                    ("Aksesuar", "#fbbf24", "#2a210d"),
                    ("Cihaz Testi", "#34d399", "#0b261e"),
                )
                if token.lower() in str(row["category"]).lower()
            ), ("#7dd3fc", "#0b2231"))
            scope_label.setStyleSheet(
                "background: {}; color: {}; border: 1px solid {}; border-radius: 6px; "
                "padding: 4px 6px; font-family: {}; font-size: 10px; font-weight: 600;".format(
                    tone[1], tone[0], tone[0], DesignTokens.MONO_FONT_FAMILY
                )
            )
            scope_label.setFixedHeight(52)
            category_cell = QWidget(self.table)
            category_layout = QHBoxLayout(category_cell)
            category_layout.setContentsMargins(25, 4, 12, 4)
            category_layout.setSpacing(4)
            category_layout.addWidget(scope_label)
            category_arrow = QLabel("\u203a")
            category_arrow.setStyleSheet(theme_qss("color: @text_muted; font-size: 16px;"))
            category_layout.addWidget(category_arrow)
            category_name = QLabel(category_parts[-1] if len(category_parts) >= 3 else "")
            category_name.setWordWrap(True)
            category_name.setStyleSheet(theme_qss("color: @text; font-weight: 650;"))
            category_layout.addWidget(category_name, 1)
            category_cell.setMinimumWidth(0)
            self.table.setCellWidget(index, 0, category_cell)
            label_item = QTableWidgetItem(str(row["label"] or ""))
            label_font = label_item.font()
            label_font.setFamily("Inter")
            label_font.setPointSize(11)
            label_font.setWeight(QFont.Weight.DemiBold)
            label_item.setFont(label_font)
            label_item.setData(Qt.ItemDataRole.UserRole, str(row["category"] or ""))
            normalized_category = str(row["category"] or "").lower()
            title_color = "#0369a1" if "i\u015flem" in normalized_category else (
                "#047857" if "gizli" in normalized_category else "#0f172a"
            )
            label_item.setForeground(QColor(title_color))
            self.table.setItem(index, 1, label_item)
            status = "Aktif" if bool(int(row["is_active"] or 0)) else "Pasif"
            self.table.setItem(index, 2, QTableWidgetItem(status))
            order_item = QTableWidgetItem(f"{int(row.get('display_order') or index + 1):02d}")
            order_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            order_item.setForeground(QColor("#94a3b8"))
            order_item.setFont(QFont("Inter", 9, QFont.Weight.Bold))
            self.table.setItem(index, 3, order_item)
            usage_item = QTableWidgetItem(usage_area)
            usage_item.setForeground(QColor("#475569"))
            self.table.setItem(index, 4, usage_item)
            shortcut_item = QTableWidgetItem(str(row.get("title") or "-"))
            shortcut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            shortcut_item.setForeground(QColor("#334155"))
            shortcut_item.setBackground(QColor("#1e293b"))
            shortcut_item.setFont(QFont("JetBrains Mono", 10, QFont.Weight.DemiBold))
            self.table.setItem(index, 5, shortcut_item)
            handle = QTableWidgetItem("\u28bf")
            handle.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            handle.setToolTip("S\u0131ralama tutamac\u0131")
            self.table.setItem(index, 6, handle)
            self.table.setCellWidget(index, 7, self._row_actions(index, row))
        first = start + 1 if self.total_count else 0
        last = min(start + len(page_rows), self.total_count)
        self.lbl_info.setText(
            f"{self.total_count} kay\u0131ttan {first} - {last} aras\u0131 g\u00f6steriliyor."
        )
        self.lbl_page.setText(f"{self.current_page} / {total_pages}")
        self._render_page_numbers(total_pages)
        self.btn_first.setEnabled(self.current_page > 1)
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        self._update_preview()

    def _update_preview(self):
        index = self.table.currentRow()
        rows = getattr(self, "_visible_rows", [])
        if index < 0 or index >= len(rows):
            self.preview_category.clear()
            self.preview_template_type.clear()
            self.preview_text.setText("\u00d6nizlemek i\u00e7in bir \u015fablon se\u00e7in.")
            self.preview_id.setText("Se\u00e7ili \u015eablon #--")
            self.preview_status.clear()
            self.copy_button.setEnabled(False)
            return
        row = rows[index]
        self._selection_started_at = time.monotonic()
        self.preview_category.setText(
            str(row.get("display_category") or row["category"] or "")
        )
        category_name = str(row.get("category") or "").split("::")[-1].strip()
        type_labels = {
            "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi": "M\u00dc\u015eTER\u0130 BEYANI / HIZLI ARIZA:",
            "\u0130\u015flem Detay\u0131": "\u0130\u015eLEM DETAYI:",
            "Cihaz Testi": "C\u0130HAZ TEST\u0130:",
            "Aksesuar": "ALINAN AKSESUAR:",
            "Gizli Not": "DAH\u0130L\u0130 G\u0130ZL\u0130 NOT:",
        }
        self.preview_template_type.setText(type_labels.get(category_name, category_name.upper()))
        preview_label, _preview_detail = _TemplateLabelDelegate._split_text(row["label"])
        self.preview_text.setText("\u00bb  " + preview_label)
        self.preview_text.setStyleSheet(theme_qss(
            "color: @finance_text; background: #251725; border: 1px solid #9f1239; "
            "border-radius: 6px; padding: 12px; font-size: 14px; font-weight: 700;"
        ))
        self.preview_id.setText("Se\u00e7ili \u015eablon #{:02d}".format(int(row["id"] or 0)))
        self.preview_status.setText("KAYIT ALINDI" if int(row['is_active'] or 0) else "PASIF KALIP")
        self.preview_status.setStyleSheet(theme_qss(
            'color: @finance_action_income; font-size: 11px;' if int(row['is_active'] or 0)
            else 'color: @text_muted; font-size: 11px;'
        ))
        self.copy_button.setEnabled(True)

    def _row_actions(self, index, row):
        actions = QWidget(self.table)
        layout = QHBoxLayout(actions)
        layout.setContentsMargins(1, 0, 1, 0)
        layout.setSpacing(4)
        layout.addStretch(1)
        action_specs = (
            ("\u29c9", "Metni Kopyala", lambda: self._copy_template_row(row)),
            ("\u270e", "D\u00fczenle", lambda: self._edit_row(index)),
            ("\u232b", "Sil", lambda: self._delete_row(row)),
        )
        for glyph, tooltip, callback in action_specs:
            button = QToolButton(actions)
            button.setText(glyph)
            button.setAccessibleName(tooltip)
            button.setToolTip(tooltip)
            button.setFixedSize(30, 30)
            button.clicked.connect(callback)
            button.setStyleSheet(theme_qss(
                "QToolButton { color: @text_muted; background: transparent; border: 1px solid transparent; "
                "border-radius: 5px; font-size: 16px; } "
                "QToolButton:hover { color: @electric_blue; background: @surface_alt; "
                "border-color: @finance_outline; }"
            ))
            layout.addWidget(button)
        return actions

    def _edit_row(self, index):
        if 0 <= index < len(getattr(self, "_visible_rows", [])):
            self.table.selectRow(index)
            self.open_editor()

    def _delete_row(self, row):
        answer = QMessageBox.question(
            self, "Kal\u0131b\u0131 Sil", "Se\u00e7ili c\u00fcmle kal\u0131b\u0131 silinsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_fast_note(row["id"])
        self.refresh_data()

    def _add_template(self):
        self.open_editor()

    def import_templates(self):
        path, _selected_filter = QFileDialog.getOpenFileName(
            self, "CSV kal\u0131plar\u0131n\u0131 i\u00e7e aktar", "", "CSV files (*.csv)"
        )
        if not path:
            return
        inserted = 0
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    category = str(row.get("category") or row.get("Kategori") or "").strip()
                    label = str(row.get("label") or row.get("Kal\u0131p") or "").strip()
                    if category and label:
                        self.db.add_fast_note(category, label, int(str(row.get("is_active", "1")).strip() != "0"), inserted)
                        inserted += 1
            self.db.conn.commit()
            self.refresh_data()
        except (OSError, ValueError, AttributeError, TypeError) as error:
            from src.utils.toast_notification import show_error
            show_error(self, "CSV aktar\u0131m\u0131 ba\u015far\u0131s\u0131z", str(error))

    def export_templates(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self, "CSV kal\u0131plar\u0131n\u0131 d\u0131\u015fa aktar", "rapor-cumle-kaliplari.csv", "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=("id", "category", "label", "is_active", "display_order"))
                writer.writeheader()
                writer.writerows(self._rows)
        except OSError as error:
            from src.utils.toast_notification import show_error
            show_error(self, "CSV d\u0131\u015fa aktar\u0131m\u0131 ba\u015far\u0131s\u0131z", str(error))

    def _copy_selected_template(self):
        index = self.table.currentRow()
        rows = getattr(self, '_visible_rows', [])
        if 0 <= index < len(rows):
            self._copy_template_row(rows[index])

    def _load_usage_metrics(self):
        today = date.today().isoformat()
        try:
            stored = json.loads(self.db.get_setting("report_template_usage_metrics", "{}"))
        except (AttributeError, TypeError, ValueError):
            stored = {}
        if not isinstance(stored, dict) or stored.get("date") != today:
            return {"date": today, "count": 0, "average_seconds": 0.0}
        try:
            return {
                "date": today,
                "count": max(0, int(stored.get("count", 0))),
                "average_seconds": max(0.0, float(stored.get("average_seconds", 0.0))),
            }
        except (TypeError, ValueError):
            return {"date": today, "count": 0, "average_seconds": 0.0}

    def _refresh_usage_stats(self):
        metrics = self._usage_metrics
        self.preview_stat_total.setText("{} kez".format(metrics["count"]))
        self.preview_stat_active.setText("{:.1f} sn".format(metrics["average_seconds"]))

    def _copy_template_row(self, row):
        QApplication.clipboard().setText(str(row.get("label") or ""))
        elapsed = max(0.1, min(300.0, time.monotonic() - self._selection_started_at))
        metrics = self._usage_metrics
        count = int(metrics["count"])
        metrics["average_seconds"] = (
            (float(metrics["average_seconds"]) * count + elapsed) / (count + 1)
        )
        metrics["count"] = count + 1
        try:
            self.db.set_setting("report_template_usage_metrics", json.dumps(metrics))
        except (AttributeError, TypeError, ValueError):
            pass
        self._refresh_usage_stats()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        narrow_header = event.size().width() < 1050
        if narrow_header != getattr(self, "_actions_in_mobile_row", False):
            for button in self.header_action_widgets:
                self.header_layout.removeWidget(button)
                self.mobile_action_row.removeWidget(button)
                if narrow_header:
                    self.mobile_action_row.addWidget(button)
                else:
                    self.header_layout.addWidget(button)
            self._actions_in_mobile_row = narrow_header
        if hasattr(self, 'filter_grid'):
            self._layout_filters(event.size().width())
        if not hasattr(self, "template_splitter"):
            return
        self.footer_widget.setFixedWidth(max(0, int(self.width() * 0.69)))
        compact_layout = self.width() < 1200
        stacked_layout = self.width() < 1150
        self.template_scroll_content.setMinimumHeight(720 if stacked_layout else 0)
        self.preview_receipt.setFixedHeight(180 if compact_layout else 427)
        self.preview_stats.setFixedHeight(116 if compact_layout else 134)
        self.preview_company.setVisible(not compact_layout)
        self.preview_document_type.setVisible(not compact_layout)
        self.preview_serial.setVisible(not compact_layout)
        self.preview_header_rule.setVisible(not compact_layout)
        for label in self.preview_context_labels:
            label.setVisible(not compact_layout)
        self.preview_context_rule.setVisible(not compact_layout)
        self.preview_accessory_title.setVisible(not compact_layout)
        self.preview_accessory.setVisible(not compact_layout)
        self.preview_footer_rule.setVisible(not compact_layout)
        self.preview_footer_row.setVisible(not compact_layout)
        self.preview_status.setVisible(not compact_layout)
        self.preview_assistant.setVisible(not compact_layout)
        self.preview_layout.setContentsMargins(
            18, 12 if compact_layout else 24, 18, 8
        )
        self.preview_layout.setSpacing(4 if compact_layout else 6)
        self.preview_receipt_layout.setContentsMargins(
            10 if compact_layout else 20, 8 if compact_layout else 20,
            10 if compact_layout else 20, 8 if compact_layout else 20
        )
        self.preview_receipt_layout.setSpacing(6 if compact_layout else 16)
        self.preview_text.setFixedHeight(64 if compact_layout else 44)
        orientation = (
            Qt.Orientation.Vertical if stacked_layout
            else Qt.Orientation.Horizontal
        )
        if self.template_splitter.orientation() != orientation:
            self.template_splitter.setOrientation(orientation)
            self.template_splitter.setSizes(
                [600, 240] if stacked_layout else [650, 320]
            )

    def _search_changed(self):
        self.category_tabs.blockSignals(True)
        category_index = self.category_filter.currentIndex()
        self.category_tabs.setCurrentIndex(category_index if category_index < self.category_tabs.count() else 0)
        self.category_tabs.blockSignals(False)
        self.current_page = 1
        self._render()

    def previous_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self._render()

    def next_page(self):
        total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
        if self.current_page < total_pages:
            self.current_page += 1
            self._render()

    def _go_to_page(self, page):
        self.current_page = max(1, int(page))
        self._render()

    def _page_size_changed(self):
        self.page_size = int(self.page_size_combo.currentData() or self.PAGE_SIZE)
        self.current_page = 1
        self._render()

    def _render_page_numbers(self, total_pages):
        while self.page_numbers.count():
            item = self.page_numbers.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        if total_pages <= 4:
            pages = list(range(1, total_pages + 1))
        elif self.current_page <= 3:
            pages = [1, 2, 3, None, total_pages]
        elif self.current_page >= total_pages - 2:
            pages = [1, None, total_pages - 2, total_pages - 1, total_pages]
        else:
            pages = [1, None, self.current_page - 1, self.current_page, self.current_page + 1, None, total_pages]
        for page in pages:
            if page is None:
                self.page_numbers.addWidget(QLabel("..."))
                continue
            button = QPushButton(str(page))
            button.setFixedSize(40, 40)
            button.setToolTip("Sayfa {}".format(page))
            if page == self.current_page:
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @electric_blue; color: @selection_text; border: 1px solid @electric_blue; border-radius: 6px; font-weight: 700; }"
                ))
            else:
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @surface; color: @text; border: 1px solid @border; border-radius: 6px; } QPushButton:hover { border-color: @electric_blue; }"
                ))
            button.clicked.connect(lambda checked=False, selected_page=page: self._go_to_page(selected_page))
            self.page_numbers.addWidget(button)

    def open_editor(self):
        index = self.table.currentRow()
        rows = getattr(self, '_visible_rows', [])
        category = str(rows[index]['category'] or '') if 0 <= index < len(rows) else '\u0130\u015flem Detay\u0131'
        options = {}
        parts = category.split('::')
        if len(parts) >= 3 and parts[0] == 'Teknik Servis':
            category = parts[-1]
            options['profile_name'] = parts[-2]
        editor = QuickNotesEditor(
            self.db,
            self,
            initial_category=category,
            **options,
        )
        editor.exec()
        self.refresh_data()
