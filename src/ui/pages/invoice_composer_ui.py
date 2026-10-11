"""Midnight Enterprise Slate layout for the e-invoice composer."""

from PyQt6.QtCore import QDate, QTime, Qt, QSize, QObject, QEvent, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.navigation_glyph import navigation_icon
from src.utils.theme_colors import theme_qss
from src.utils.theme_manager import ThemeManager


class _InvoiceInputDelegate(QStyledItemDelegate):
    """Paint editable invoice cells as compact controls without changing their data model."""

    INPUT_COLUMNS = frozenset((3, 4, 5, 6, 7))

    def createEditor(self, parent, option, index):
        if index.column() == 4:
            editor = QComboBox(parent)
            editor.addItems(("Adet", "Hizmet", "Saat", "Kg", "Metre"))
            editor.setStyleSheet(_input_style())
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            editor.setCurrentText(str(index.data(Qt.ItemDataRole.EditRole) or ""))
            return
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
            return
        super().setModelData(editor, model, index)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        super().paint(painter, option, index)
        if index.column() not in self.INPUT_COLUMNS:
            return

        palette = ThemeManager.current_palette()
        rect = option.rect.adjusted(5, 9, -5, -9)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QColor(palette.get("border", "#233047")))
        painter.setBrush(QColor(palette.get("finance_surface_lowest", "#060E20")))
        painter.drawRoundedRect(rect, 5, 5)
        painter.setPen(QColor(palette.get("text", "#F1F5F9")))
        painter.drawText(
            rect.adjusted(7, 0, -7, 0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            str(index.data(Qt.ItemDataRole.DisplayRole) or ""),
        )
        if index.column() == 4:
            arrow_x = rect.right() - 11
            arrow_y = rect.center().y()
            painter.setPen(QColor(palette.get("text_muted", "#CBD5E1")))
            painter.drawLine(arrow_x - 3, arrow_y - 1, arrow_x, arrow_y + 2)
            painter.drawLine(arrow_x, arrow_y + 2, arrow_x + 3, arrow_y - 1)
        painter.restore()


class _InvoiceResponsiveFilter(QObject):
    def __init__(self, page, primary, aside, primary_scroll, aside_scroll):
        super().__init__(page)
        self.page = page
        self.primary = primary
        self.aside = aside
        self.primary_scroll = primary_scroll
        self.aside_scroll = aside_scroll
        self.root_layout = page.layout
        self.primary_layout = primary.layout()
        self.stacked = False

    def eventFilter(self, watched, event):
        if watched is self.page and event.type() == QEvent.Type.Resize:
            page_width = event.size().width()
            compact = page_width < 1250
            if compact != self.stacked:
                if compact:
                    self.root_layout.removeWidget(self.aside_scroll)
                    self.aside_scroll.takeWidget()
                    self.aside.setParent(self.primary)
                    self.aside.setMinimumWidth(0)
                    self.aside.setMaximumWidth(16777215)
                    self.aside.setSizePolicy(
                        QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                    )
                    self.primary_layout.insertWidget(
                        max(0, self.primary_layout.count() - 1), self.aside
                    )
                    self.aside_scroll.hide()
                else:
                    self.primary_layout.removeWidget(self.aside)
                    self.aside.setParent(None)
                    self.aside_scroll.setWidget(self.aside)
                    self.aside_scroll.setFixedWidth(462)
                    self.root_layout.addWidget(self.aside_scroll, 0)
                    self.aside_scroll.show()
                self.stacked = compact
            if not compact:
                self.aside.setFixedWidth(462)
                self.aside_scroll.setFixedWidth(462)
            else:
                self.aside.setMinimumWidth(0)
                self.aside.setMaximumWidth(16777215)
            self.primary.setMinimumWidth(0)
            self.primary_scroll.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
            self.aside_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            QTimer.singleShot(0, self._fit_line_columns)
        return False

    def _fit_line_columns(self):
        table = getattr(self.page, "items_table", None)
        if table is None:
            return
        base_widths = (42, 300, 90, 70, 74, 110, 70)
        visible_columns = [
            (column, width)
            for column, width in enumerate(base_widths)
            if not table.isColumnHidden(column)
        ]
        total_width = sum(width for _, width in visible_columns)
        available_width = max(0, table.viewport().width() - 2)
        if total_width <= available_width or available_width <= 0:
            return
        scale = available_width / total_width
        for column, width in visible_columns:
            table.setColumnWidth(column, max(38, int(width * scale)))


def _label(text, token="text_muted", size=11, weight=500):
    label = QLabel(text)
    label.setStyleSheet(theme_qss(
        f"color: @{token}; background: transparent; font-size: {size}px; font-weight: {weight};"
    ))
    return label


def _card(object_name, margins=(12, 10, 12, 10)):
    frame = QFrame()
    frame.setObjectName(object_name)
    frame.setStyleSheet(theme_qss(
        f"QFrame#{object_name} {{ background: @finance_surface; border: 1px solid @border; border-radius: 9px; }}"
    ))
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(9)
    return frame, layout


def _field(label_text, widget, *, label_size=11):
    holder = QWidget()
    layout = QVBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(_label(label_text, "text_muted", label_size, 500))
    layout.addWidget(widget)
    return holder


def _input_style():
    return theme_qss(
        "QLineEdit, QComboBox, QDateEdit, QTimeEdit, QTextEdit { background: @finance_surface_lowest; "
        "color: @text; border: 1px solid @border; border-radius: 5px; padding: 6px 8px; "
        "selection-background-color: @accent; min-height: 22px; font-size: 12px; } "
        "QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QTextEdit:focus { border-color: @finance_breadcrumb_active; }"
    )


def _button_style(kind="secondary"):
    if kind == "primary":
        return theme_qss(
            "QPushButton { background: @accent; color: @selection_text; border: 1px solid @accent; "
            "border-radius: 6px; padding: 7px 10px; font-size: 12px; font-weight: 700; } "
            "QPushButton:hover { background: @finance_breadcrumb_active; border-color: @finance_breadcrumb_active; }"
        )
    if kind == "success":
        return theme_qss(
            "QPushButton { background: @success; color: @selection_text; border: 1px solid @success; "
            "border-radius: 6px; padding: 7px 10px; font-size: 12px; font-weight: 700; }"
        )
    return theme_qss(
        "QPushButton { background: @finance_surface_alt; color: @text; border: 1px solid @border; "
        "border-radius: 6px; padding: 6px 9px; font-size: 12px; font-weight: 600; } "
        "QPushButton:hover { background: @finance_surface_high; border-color: @finance_outline; }"
    )


def build_invoice_composer(page):
    """Create the responsive two-column composer and retain its legacy hooks."""
    page.setStyleSheet(theme_qss(
        "QWidget { color: @text; background: transparent; } "
        "QFrame#InvoiceRoot { background: @finance_canvas; }"
    ))
    root = QHBoxLayout(page)
    page.layout = root
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    primary = QWidget()
    primary.setObjectName("InvoicePrimaryColumn")
    primary.setStyleSheet("background: transparent;")
    primary_layout = QVBoxLayout(primary)
    primary_layout.setContentsMargins(15, 9, 27, 27)
    primary_layout.setSpacing(17)
    primary_scroll = QScrollArea()
    primary_scroll.setWidgetResizable(True)
    primary_scroll.setFrameShape(QFrame.Shape.NoFrame)
    primary_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    primary_scroll.setWidget(primary)
    root.addWidget(primary_scroll, 1)

    aside = QFrame()
    aside.setObjectName("InvoiceSummaryAside")
    aside.setFixedWidth(462)
    aside.setFixedHeight(1210)
    aside.setStyleSheet(theme_qss(
        "QFrame#InvoiceSummaryAside { background: @finance_surface_lowest; border-left: 1px solid @border; }"
    ))
    aside_layout = QVBoxLayout(aside)
    aside_layout.setContentsMargins(17, 10, 18, 28)
    aside_layout.setSpacing(18)
    aside_scroll = QScrollArea()
    aside_scroll.setWidgetResizable(True)
    aside_scroll.setFrameShape(QFrame.Shape.NoFrame)
    aside_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    aside_scroll.setWidget(aside)
    root.addWidget(aside_scroll, 0)

    page._invoice_primary = primary
    page._invoice_aside = aside
    page._invoice_primary_scroll = primary_scroll
    page._invoice_aside_scroll = aside_scroll
    page._invoice_responsive_filter = _InvoiceResponsiveFilter(
        page, primary, aside, primary_scroll, aside_scroll
    )
    page.installEventFilter(page._invoice_responsive_filter)

    ribbon, ribbon_layout = _card("InvoiceTitleRibbon", (12, 9, 12, 9))
    ribbon.setFixedHeight(119)
    ribbon_row = QHBoxLayout()
    ribbon_row.setContentsMargins(0, 0, 0, 0)
    ribbon_row.setSpacing(10)
    icon = QLabel()
    icon.setFixedSize(36, 36)
    icon.setPixmap(navigation_icon("document", 22, "finance_breadcrumb_active").pixmap(QSize(22, 22)))
    icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon.setStyleSheet(theme_qss(
        "background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 8px;"
    ))
    ribbon_row.addWidget(icon)
    title_holder = QWidget()
    title_holder.setFixedWidth(230)
    title_column = QVBoxLayout(title_holder)
    title_column.setContentsMargins(0, 0, 0, 0)
    title_column.setSpacing(3)
    page.page_title = QLabel("E-Fatura Olu\u015fturma Studio")
    page.page_title.setWordWrap(True)
    page.page_title.setStyleSheet(theme_qss("color: @text; font-size: 14px; font-weight: 800;"))
    title_column.addWidget(page.page_title)
    description = _label(
        "Resmi e-Fatura, e-Ar\u015fiv ve ihracat faturalar\u0131 olu\u015fturma ve m\u00fckellef do\u011frulama ekran\u0131.",
        "text_muted", 11, 400,
    )
    description.setWordWrap(True)
    title_column.addWidget(description)
    ribbon_row.addWidget(title_holder)
    ribbon_row.addStretch(1)
    page.ubl_badge = QLabel("G\u0130B UBL 2.1\nTR")
    page.ubl_badge.setWordWrap(True)
    page.ubl_badge.setStyleSheet(theme_qss(
        "color: @finance_breadcrumb_active; background: @finance_surface_alt; border: 1px solid @finance_outline; "
        "border-radius: 5px; padding: 4px 7px; font: 10px 'JetBrains Mono';"
    ))
    page.ubl_badge.setFixedWidth(130)
    ribbon_actions = QVBoxLayout()
    ribbon_actions.setContentsMargins(0, 0, 0, 0)
    ribbon_actions.setSpacing(5)
    badge_row = QHBoxLayout()
    badge_row.setContentsMargins(0, 0, 0, 0)
    badge_row.addWidget(page.ubl_badge)
    page.btn_integration = QPushButton()
    page.btn_integration.setToolTip("Entegrasyon Ayarlar\u0131")
    page.btn_integration.setFixedSize(36, 36)
    page.btn_integration.setStyleSheet(_button_style())
    page.btn_integration.clicked.connect(page.open_integration_settings)
    page.btn_integration.setIcon(navigation_icon("plug", 15, "finance_breadcrumb_active"))
    page.btn_integration.setIconSize(QSize(15, 15))
    badge_row.addWidget(page.btn_integration)
    ribbon_actions.addLayout(badge_row)
    action_row = QHBoxLayout()
    action_row.setContentsMargins(0, 0, 0, 0)
    action_row.setSpacing(7)
    page.btn_import_order = QPushButton("\u0130rsaliye /\nSipari\u015ften \u00c7ek")
    page.btn_import_order.setStyleSheet(_button_style())
    page.btn_import_order.setIcon(navigation_icon("document", 15, "finance_breadcrumb_active"))
    page.btn_import_order.setIconSize(QSize(15, 15))
    page.btn_import_order.setFixedWidth(140)
    page.btn_import_order.setFixedHeight(56)
    page.btn_import_order.clicked.connect(page.open_linked_order_picker)
    action_row.addWidget(page.btn_import_order)
    page.btn_add_item = QPushButton("Yeni Sat\u0131r\nEkle (F2)")
    page.btn_add_item.setStyleSheet(_button_style("primary"))
    page.btn_add_item.setIcon(navigation_icon("plus_circle", 15, "selection_text"))
    page.btn_add_item.setIconSize(QSize(15, 15))
    page.btn_add_item.setFixedWidth(120)
    page.btn_add_item.setFixedHeight(56)
    page.btn_add_item.clicked.connect(page.add_row)
    action_row.addWidget(page.btn_add_item)
    page.btn_remove_item = QPushButton("Sat\u0131r\nSil")
    page.btn_remove_item.setStyleSheet(_button_style())
    page.btn_remove_item.setIcon(navigation_icon("document", 14, "danger"))
    page.btn_remove_item.setIconSize(QSize(14, 14))
    page.btn_remove_item.setFixedWidth(72)
    page.btn_remove_item.setFixedHeight(56)
    page.btn_remove_item.clicked.connect(lambda _checked=False: page.remove_row())
    action_row.addWidget(page.btn_remove_item)
    ribbon_actions.addLayout(action_row)
    ribbon_row.addLayout(ribbon_actions)
    ribbon_layout.addLayout(ribbon_row)
    primary_layout.addWidget(ribbon)
    primary_layout.addSpacing(14)

    meta, meta_layout = _card("InvoiceMasterData", (12, 0, 12, 10))
    meta_layout.setSpacing(0)
    meta.setMinimumHeight(282)
    page.master_data_heading = _label("M\u00fc\u015fteri & Fatura \u00dcst Bilgileri", "text", 12, 700)
    page.master_data_heading.setParent(meta)
    page.master_data_heading.setGeometry(12, 4, 300, 20)
    page.master_data_heading.setStyleSheet(theme_qss(
        "color: @text; background: @finance_surface; font-size: 12px; font-weight: 700; padding: 0 5px;"
    ))
    page.master_data_heading.show()
    page.master_data_heading.raise_()

    inputs = _input_style()
    page.cmb_customer = QComboBox()
    page.cmb_customer.setEditable(False)
    page.cmb_customer.setPlaceholderText("M\u00fc\u015fteri Se\u00e7in...")
    page.cmb_customer.setStyleSheet(inputs)
    page.cmb_customer.currentIndexChanged.connect(page.on_customer_change)
    customer_label = _label("M\u00fc\u015fteri / Cari \u00dcnvan\u0131 *", "text_muted", 11)
    customer_row = QHBoxLayout()
    customer_row.setContentsMargins(0, 0, 0, 0)
    customer_row.setSpacing(5)
    customer_row.addWidget(page.cmb_customer, 1)
    page.btn_customer_directory = QPushButton("Cari Rehber (F4)")
    page.btn_customer_directory.setStyleSheet(theme_qss(
        "QPushButton { background: transparent; color: @finance_breadcrumb_active; border: none; font-size: 9px; }"
    ))
    page.btn_customer_directory.setFixedWidth(92)
    page.btn_customer_directory.clicked.connect(page.cmb_customer.setFocus)
    customer_row.addWidget(page.btn_customer_directory)
    customer_holder = QWidget()
    customer_holder_layout = QVBoxLayout(customer_holder)
    customer_holder_layout.setContentsMargins(0, 0, 0, 0)
    customer_holder_layout.setSpacing(4)
    customer_holder_layout.addWidget(customer_label)
    customer_holder_layout.addLayout(customer_row)

    page.inp_vkn = QLineEdit()
    page.inp_vkn.setMaxLength(11)
    page.inp_vkn.setReadOnly(True)
    page.inp_vkn.setStyleSheet(inputs + theme_qss("QLineEdit { color: @success; font: 11px 'JetBrains Mono'; }"))
    page.tax_office = QLineEdit()
    page.tax_office.setStyleSheet(inputs)

    top_fields = QGridLayout()
    top_fields.setContentsMargins(0, 0, 0, 0)
    top_fields.setHorizontalSpacing(9)
    top_fields.setVerticalSpacing(6)
    meta_layout.addSpacing(37)
    top_fields.addWidget(customer_holder, 0, 0, 1, 6)
    top_fields.addWidget(_field("Vergi / TC Kimlik No", page.inp_vkn), 0, 6, 1, 3)
    top_fields.addWidget(_field("Vergi Dairesi", page.tax_office), 0, 9, 1, 3)
    meta_layout.addLayout(top_fields)

    page.invoice_scenario = QComboBox()
    page.invoice_scenario.addItems(["TICARIFATURA", "TEMELFATURA", "KAMU", "IHRACAT"])
    page.invoice_scenario.setStyleSheet(inputs + theme_qss("QComboBox { font: 10px 'JetBrains Mono'; }"))
    page.invoice_type = QComboBox()
    page.invoice_type.addItems([
        "SATIS (Sat\u0131\u015f)", "TEVKIFAT (Tevkifatl\u0131)", "ISTISNA (0 KDV)", "IADE (Sat\u0131\u015f \u0130adesi)", "OZELMATRAH",
    ])
    page.invoice_type.setStyleSheet(inputs + theme_qss("QComboBox { font-size: 10px; }"))
    page.invoice_date = QDateEdit(QDate.currentDate())
    page.invoice_date.setCalendarPopup(True)
    page.invoice_date.setDisplayFormat("MM/dd/yyyy")
    page.invoice_date.setStyleSheet(inputs + theme_qss("QDateEdit { font: 10px 'JetBrains Mono'; }"))
    page.invoice_time = QTimeEdit(QTime.currentTime())
    page.invoice_time.setDisplayFormat("hh:mm AP")
    page.invoice_time.setStyleSheet(inputs + theme_qss(
        "QTimeEdit { font: 10px 'JetBrains Mono'; } "
        "QTimeEdit::up-button, QTimeEdit::down-button { width: 12px; height: 11px; "
        "background: transparent; border: none; }"
    ))
    page.currency_select = QComboBox()
    page.currency_select.addItem("TRY (\u20ba) T\u00fcrk Liras\u0131", "TRY")
    page.currency_select.addItem("USD ($) Dolar", "USD")
    page.currency_select.addItem("EUR (\u20ac) Euro", "EUR")
    currency_index = page.currency_select.findData(page.current_currency_code)
    page.currency_select.setCurrentIndex(currency_index if currency_index >= 0 else 0)
    page.currency_select.setStyleSheet(inputs + theme_qss("QComboBox { font-size: 10px; }"))
    page.exchange_rate = QLineEdit()
    page.exchange_rate.setMinimumWidth(96)
    page.exchange_rate.setAlignment(Qt.AlignmentFlag.AlignRight)
    page.exchange_rate.setStyleSheet(inputs + theme_qss("QLineEdit { font: 10px 'JetBrains Mono'; }"))
    page.exchange_rate.textChanged.connect(page.calculate_totals)
    page.currency_select.currentIndexChanged.connect(page.on_currency_change)
    currency_rate = QHBoxLayout()
    currency_rate.setContentsMargins(0, 0, 0, 0)
    currency_rate.setSpacing(5)
    currency_rate.addWidget(page.currency_select, 5)
    currency_rate.addWidget(page.exchange_rate, 4)
    currency_holder = QWidget()
    currency_holder.setLayout(currency_rate)
    for control, minimum in (
        (page.invoice_scenario, 82),
        (page.invoice_type, 104),
        (page.invoice_date, 96),
        (page.invoice_time, 96),
        (page.currency_select, 104),
        (page.exchange_rate, 84),
    ):
        control.setMinimumWidth(minimum)
        control.setSizePolicy(
            QSizePolicy.Policy.Ignored, control.sizePolicy().verticalPolicy()
        )
    page.invoice_scenario.setMinimumContentsLength(6)
    page.invoice_type.setMinimumContentsLength(8)
    page.currency_select.setMinimumContentsLength(8)
    currency_holder.setMinimumWidth(190)
    currency_holder.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    row_two = QGridLayout()
    row_two.setContentsMargins(0, 1, 0, 11)
    row_two.setHorizontalSpacing(9)
    row_two.setVerticalSpacing(6)
    for column, title, widget in (
        (0, "Senaryo", page.invoice_scenario),
        (1, "Fatura Tipi", page.invoice_type),
        (2, "Fatura Tarihi", page.invoice_date),
        (3, "D\u00fczenleme Saati", page.invoice_time),
        (4, "Para Birimi & Fatura Kuru", currency_holder),
    ):
        row_two.addWidget(_field(title, widget), 0, column)
    for column, stretch in enumerate((5, 6, 5, 5, 9)):
        row_two.setColumnStretch(column, stretch)
    meta_layout.addLayout(row_two)

    page.inp_addr = QLineEdit()
    page.inp_addr.setReadOnly(True)
    page.inp_addr.setStyleSheet(inputs)
    page.inp_delivery_reference = QLineEdit()
    page.inp_delivery_reference.setStyleSheet(inputs + theme_qss("QLineEdit { font: 10px 'JetBrains Mono'; }"))
    row_three = QGridLayout()
    row_three.setContentsMargins(0, 0, 0, 0)
    row_three.setHorizontalSpacing(9)
    row_three.addWidget(_field("A\u00e7\u0131k Adres & Posta Kodu", page.inp_addr), 0, 0, 1, 8)
    row_three.addWidget(_field("Ba\u011fl\u0131 \u0130rsaliye No / Belge Ref", page.inp_delivery_reference), 0, 8, 1, 4)
    meta_layout.addLayout(row_three)
    primary_layout.addWidget(meta)

    lines, lines_layout = _card("InvoiceLineCard", (0, 0, 0, 0))
    lines.setFixedHeight(560)
    lines_layout.setSpacing(0)
    lines.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    lines_bar = QWidget()
    lines_bar.setFixedHeight(70)
    lines_bar.setStyleSheet(theme_qss("background: @finance_surface_alt; border-bottom: 1px solid @border;"))
    lines_bar_layout = QHBoxLayout(lines_bar)
    lines_bar_layout.setContentsMargins(10, 7, 10, 7)
    lines_bar_layout.addWidget(_label("\u2637", "accent", 13, 700))
    page.items_title_label = _label("Fatura Kalemleri & Hizmet\nSat\u0131rlar\u0131", "text", 12, 700)
    page.items_title_label.setFixedWidth(215)
    page.items_title_label.setWordWrap(True)
    lines_bar_layout.addWidget(page.items_title_label)
    page.item_count_label = _label("0 Kalem Listelendi", "accent", 10, 600)
    page.item_count_label.setFixedSize(168, 48)
    page.item_count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.item_count_label.setWordWrap(True)
    page.item_count_label.setStyleSheet(theme_qss(
        "color: @finance_breadcrumb_active; background: @finance_surface_alt; "
        "border: 1px solid @border; border-radius: 6px; padding: 3px 8px; "
        "font: 10px 'JetBrains Mono';"
    ))
    lines_bar_layout.addWidget(page.item_count_label)
    lines_bar_layout.addStretch(1)
    page.stock_status = _label("\u25cf Stoktan Rezerveli", "success", 10, 500)
    lines_bar_layout.addWidget(page.stock_status)
    page.withholding_status = _label("Tevkifat Oran\u0131: Yok", "text_muted", 10, 400)
    lines_bar_layout.addWidget(page.withholding_status)
    lines_layout.addWidget(lines_bar)

    page.items_table = QTableWidget(0, 11)
    page.items_table.setObjectName("InvoiceItemsTable")
    page.items_table.setHorizontalHeaderLabels([
        "#", "\u00dcr\u00fcn / Hizmet A\u00e7\u0131klamas\u0131", "Stok Kodu", "Miktar", "Birim",
        "Birim Fiyat ($)", "\u0130sk (%)", "KDV (%)", "KDV Tutar\u0131", "Net Sat\u0131r ($)", "\u0130\u015flem",
    ])
    header = page.items_table.horizontalHeader()
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setFixedHeight(68)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    for column, width in enumerate((40, 260, 112, 80, 80, 112, 80, 80, 96, 112, 48)):
        page.items_table.setColumnWidth(column, width)
    page.items_table.setMinimumHeight(300)
    page.items_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    page.items_table.setItemDelegate(_InvoiceInputDelegate(page.items_table))
    page.items_table.setWordWrap(True)
    page.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    page.items_table.verticalHeader().setVisible(False)
    page.items_table.verticalHeader().setDefaultSectionSize(80)
    page.items_table.setAlternatingRowColors(False)
    page.items_table.setShowGrid(False)
    page.items_table.setStyleSheet(theme_qss(
        "QTableWidget { background: @finance_surface; color: @text; border: none; gridline-color: @border; "
        "selection-background-color: @finance_surface_high; } "
        "QTableWidget::item { padding: 6px 5px; border-bottom: 1px solid @border; } "
        "QHeaderView::section { background: @finance_surface_alt; color: @text_muted; border: none; "
        "border-bottom: 1px solid @border; padding: 8px 5px; font-size: 11px; font-weight: 700; }"
    ))
    page.items_table.cellChanged.connect(page.calculate_totals)
    lines_layout.addWidget(page.items_table, 1)
    page.items_footer = QWidget()
    page.items_footer.setFixedHeight(58)
    page.items_footer.setStyleSheet(theme_qss("background: @finance_canvas; border-top: 1px solid @border;"))
    footer_layout = QHBoxLayout(page.items_footer)
    footer_layout.setContentsMargins(10, 4, 10, 4)
    footer_layout.setSpacing(8)
    page.total_units_label = _label("Toplam Miktar: 0 Birim", "text_muted", 10, 500)
    page.discounted_rows_label = _label("\u0130skonto Yap\u0131lan Sat\u0131r: 0", "text_muted", 10, 500)
    page.rate_footer_label = _label("Para Birimi Kuru: 1.0000 TRY", "success", 10, 500)
    for label, width in (
        (page.total_units_label, 145),
        (page.discounted_rows_label, 165),
        (page.rate_footer_label, 165),
    ):
        label.setFixedWidth(width)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(theme_qss(
            "font: 11px 'JetBrains Mono'; color: @text_muted; background: transparent;"
            if label is not page.rate_footer_label else
            "font: 11px 'JetBrains Mono'; color: @success; background: transparent;"
        ))
    footer_layout.addWidget(page.total_units_label)
    footer_layout.addWidget(_label("|", "border", 9))
    footer_layout.addWidget(page.discounted_rows_label)
    footer_layout.addWidget(_label("|", "border", 9))
    footer_layout.addWidget(page.rate_footer_label)
    footer_layout.addStretch(1)
    page.api_status_label = _label("e-Fatura API Haz\u0131r", "text_muted", 10, 400)
    page.api_status_label.setMinimumWidth(150)
    page.api_status_label.setStyleSheet(theme_qss(
        "font: 10px 'JetBrains Mono'; color: @text_muted; background: transparent;"
    ))
    footer_layout.addWidget(page.api_status_label)
    lines_layout.addWidget(page.items_footer)
    primary_layout.addWidget(lines)

    notes, notes_layout = _card("InvoiceNotesCard", (10, 8, 10, 8))
    notes.setFixedHeight(138)
    notes_row = QHBoxLayout()
    notes_row.setContentsMargins(0, 0, 0, 0)
    notes_row.setSpacing(10)
    page.invoice_notes = QTextEdit()
    page.invoice_notes.setPlaceholderText("Faturaya eklenecek banka, garanti veya sevk notu...")
    page.invoice_notes.setStyleSheet(inputs)
    page.invoice_notes.setMaximumHeight(64)
    notes_column = QVBoxLayout()
    notes_column.setSpacing(4)
    notes_column.addWidget(_label("Fatura Notu / Yasal A\u00e7\u0131klamalar", "text", 12, 600))
    notes_column.addWidget(_label("G\u0130B fatura alt\u0131nda g\u00f6sterilir", "text_muted", 9, 400))
    notes_column.addWidget(page.invoice_notes)
    notes_row.addLayout(notes_column, 8)
    order_column = QVBoxLayout()
    order_column.setSpacing(4)
    order_column.addWidget(_label("\u00d6zel Kod & Sipari\u015f No", "text", 12, 600))
    page.inp_order_reference = QLineEdit()
    page.inp_order_reference.setStyleSheet(inputs + theme_qss("QLineEdit { font: 10px 'JetBrains Mono'; }"))
    page.inp_order_reference.setPlaceholderText("M\u00fc\u015fteri sipari\u015f numaras\u0131")
    order_column.addWidget(page.inp_order_reference)
    order_column.addWidget(_label("OrderReference etiketine i\u015flenir.", "text_muted", 9, 400))
    notes_row.addLayout(order_column, 4)
    notes_layout.addLayout(notes_row)
    primary_layout.addWidget(notes)
    primary_layout.addStretch(1)

    summary_title = QHBoxLayout()
    title_block = QVBoxLayout()
    title_block.setSpacing(3)
    title_block.addWidget(_label("F\u0130NANSAL GENEL TOPLAM", "text", 14, 800))
    title_block.addWidget(_label("Vergi ve kur matrah\u0131 canl\u0131 hesaplama", "text_muted", 12, 400))
    summary_title.addLayout(title_block, 1)
    page.summary_currency_badge = QLabel("TRY / USD")
    page.summary_currency_badge.setStyleSheet(theme_qss(
        "color: @finance_breadcrumb_active; background: @finance_surface_alt; border: 1px solid @border; "
        "border-radius: 4px; padding: 3px 6px; font: 9px 'JetBrains Mono';"
    ))
    summary_title.addWidget(page.summary_currency_badge, 0, Qt.AlignmentFlag.AlignTop)
    aside_layout.addLayout(summary_title)
    summary_rule = QFrame()
    summary_rule.setFixedHeight(1)
    summary_rule.setStyleSheet(theme_qss("background: @border; border: none;"))
    aside_layout.addWidget(summary_rule)

    totals_card, totals_layout = _card("InvoiceTotalsCard", (12, 10, 12, 10))
    totals_layout.setSpacing(12)
    totals_card.setMinimumHeight(395)
    page.lbl_subtotal = QLabel("0.00")
    page.lbl_discount = QLabel("-0.00")
    page.lbl_taxable = QLabel("0.00")
    page.lbl_vat = QLabel("0.00")
    page.lbl_total = QLabel("0.00")
    page.lbl_total_try = QLabel("0.00 \u20ba")
    for label in (page.lbl_subtotal, page.lbl_discount, page.lbl_taxable, page.lbl_vat):
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(theme_qss("color: @text; font: 12px 'JetBrains Mono';"))
    page.lbl_discount.setStyleSheet(theme_qss("color: @danger; font: 12px 'JetBrains Mono';"))
    page.lbl_vat.setStyleSheet(theme_qss("color: @success; font: 12px 'JetBrains Mono';"))
    page.lbl_total.setAlignment(Qt.AlignmentFlag.AlignCenter)
    page.lbl_total.setStyleSheet(theme_qss("color: @text; font: 800 25px 'JetBrains Mono';"))
    page.lbl_total_try.setAlignment(Qt.AlignmentFlag.AlignRight)
    page.lbl_total_try.setStyleSheet(theme_qss("color: @success; font: 700 13px 'JetBrains Mono';"))
    for title, widget, token in (
        ("Ara Toplam:", page.lbl_subtotal, "text_muted"),
        ("Toplam \u0130skonto:", page.lbl_discount, "danger"),
        ("KDV Matrah\u0131:", page.lbl_taxable, "text_muted"),
        ("Hesaplanan KDV:", page.lbl_vat, "text_muted"),
    ):
        row = QHBoxLayout()
        row.addWidget(_label(title, token, 10, 500))
        row.addStretch(1)
        row.addWidget(widget)
        totals_layout.addLayout(row)
        if title != "Ara Toplam:":
            divider = QFrame()
            divider.setFixedHeight(1)
            divider.setStyleSheet(theme_qss("background: @border; border: none;"))
            totals_layout.addWidget(divider)

    payable = QFrame()
    payable.setObjectName("InvoicePayableTotal")
    payable.setStyleSheet(theme_qss(
        "QFrame#InvoicePayableTotal { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 8px; }"
    ))
    payable_layout = QVBoxLayout(payable)
    payable_layout.setContentsMargins(10, 8, 10, 8)
    payable_layout.setSpacing(5)
    payable_header = QHBoxLayout()
    payable_header.addWidget(_label("\u00d6DENECEK GENEL TUTAR", "finance_breadcrumb_active", 9, 800))
    payable_header.addStretch(1)
    payable_header.addWidget(_label("T\u00dcM VERG\u0130LER DAH\u0130L", "finance_breadcrumb_active", 8, 700))
    payable_layout.addLayout(payable_header)
    payable_layout.addWidget(page.lbl_total)
    payable_bottom = QHBoxLayout()
    payable_bottom.addWidget(_label("TL Kar\u015f\u0131l\u0131\u011f\u0131 (TCMB):", "text_muted", 9, 400))
    payable_bottom.addStretch(1)
    payable_bottom.addWidget(page.lbl_total_try)
    payable_layout.addLayout(payable_bottom)
    totals_layout.addWidget(payable)
    aside_layout.addWidget(totals_card)

    payment_card, payment_layout = _card("InvoicePaymentCard", (12, 10, 12, 10))
    payment_card.setMinimumHeight(258)
    payment_heading = QHBoxLayout()
    payment_heading.addWidget(_label("Tahsilat & Kasa Bilgisi", "text", 11, 700))
    payment_heading.addStretch(1)
    payment_heading.addWidget(_label("Zorunlu", "text_muted", 9, 400))
    payment_layout.addLayout(payment_heading)
    page.cmb_bank = QComboBox()
    page.cmb_bank.addItem("A\u00e7\u0131k Hesap / Tahsilat Se\u00e7in", -1)
    try:
        for account in page.db.get_bank_accounts():
            bank_name = account.get("bank_name") if isinstance(account, dict) else account[1]
            bank_id = account.get("id") if isinstance(account, dict) else account[0]
            page.cmb_bank.addItem(str(bank_name), bank_id)
    except Exception:
        pass
    page.cmb_bank.setStyleSheet(inputs)
    payment_layout.addWidget(_field("Tahsilat Hesab\u0131 / Kasa", page.cmb_bank, label_size=10))
    payment_row = QHBoxLayout()
    payment_row.setSpacing(8)
    page.due_date = QDateEdit(QDate.currentDate().addDays(14))
    page.due_date.setCalendarPopup(True)
    page.due_date.setDisplayFormat("MM/dd/yyyy")
    page.due_date.setStyleSheet(inputs + theme_qss("QDateEdit { font: 10px 'JetBrains Mono'; }"))
    page.payment_channel = QComboBox()
    page.payment_channel.addItems(["Havale / EFT", "Kredi Kart\u0131", "Nakit", "DBS / \u00c7ek"])
    page.payment_channel.setStyleSheet(inputs)
    payment_row.addWidget(_field("Vade Tarihi", page.due_date), 1)
    payment_row.addWidget(_field("\u00d6deme Kanal\u0131", page.payment_channel), 1)
    payment_layout.addLayout(payment_row)
    page.chk_auto_reconcile = QCheckBox("Cari Hesaba Otomatik \u0130\u015fle")
    page.chk_auto_reconcile.setChecked(True)
    page.chk_auto_reconcile.setStyleSheet(theme_qss("QCheckBox { color: @text_muted; font-size: 10px; spacing: 6px; }"))
    payment_layout.addWidget(page.chk_auto_reconcile)
    aside_layout.addWidget(payment_card)
    aside_layout.addStretch(1)

    action_rule = QFrame()
    action_rule.setFixedHeight(1)
    action_rule.setStyleSheet(theme_qss("background: @border; border: none;"))
    aside_layout.addWidget(action_rule)
    page.btn_send = QPushButton("E-Faturay\u0131 Resmile\u015ftir ve G\u00f6nder (F12)")
    page.btn_send.setFixedHeight(63)
    page.btn_send.setStyleSheet(theme_qss(
        "QPushButton { background: @accent; color: @selection_text; border: 1px solid @finance_outline; "
        "border-radius: 8px; font-size: 13px; font-weight: 800; padding: 8px; } "
        "QPushButton:hover { background: @finance_breadcrumb_active; }"
    ))
    page.btn_send.setIcon(navigation_icon("send", 17, "selection_text"))
    page.btn_send.setIconSize(QSize(17, 17))
    page.btn_send.clicked.connect(page.send_invoice)
    aside_layout.addWidget(page.btn_send)
    secondary_actions = QHBoxLayout()
    secondary_actions.setSpacing(6)
    page.btn_preview = QPushButton("PDF G\u00f6r")
    page.btn_save_draft = QPushButton("Taslak")
    page.btn_proforma = QPushButton("Proforma")
    for button, kind, callback in (
        (page.btn_preview, "document", page.preview_invoice),
        (page.btn_save_draft, "save", page.save_draft),
        (page.btn_proforma, "document", page.export_proforma),
    ):
        button.setStyleSheet(_button_style())
        button.setFixedHeight(42)
        button.setIcon(navigation_icon(kind, 14, "finance_breadcrumb_active"))
        button.setIconSize(QSize(14, 14))
        button.clicked.connect(callback)
        secondary_actions.addWidget(button, 1)
    aside_layout.addLayout(secondary_actions)
    page.api_connection_label = _label("\u25cf e-Fatura API ba\u011flant\u0131s\u0131", "success", 9, 400)
    page.api_connection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    aside_layout.addWidget(page.api_connection_label)

    shortcuts = [
        ("F2", page.add_row),
        ("F12", page.send_invoice),
        ("F4", page.cmb_customer.setFocus),
    ]
    page._invoice_shortcuts = []
    for key, callback in shortcuts:
        shortcut = QShortcut(QKeySequence(key), page)
        shortcut.activated.connect(callback)
        page._invoice_shortcuts.append(shortcut)

