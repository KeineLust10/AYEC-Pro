import csv
from datetime import datetime

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.services.offer_service import OfferService
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success, show_warning


def _row_value(row, key, index=None, default=""):
    try:
        if hasattr(row, "keys") and key in row.keys():
            value = row[key]
        elif index is not None:
            value = row[index]
        else:
            value = default
    except Exception:
        value = default
    return default if value is None else value


def _money(value, currency="TRY"):
    symbols = {"TRY": "\u20ba", "USD": "$", "EUR": "\u20ac", "GBP": "\u00a3"}
    symbol = symbols.get(str(currency or "TRY").upper(), str(currency or "TRY"))
    return f"{float(value or 0):,.2f} {symbol}"


def _filter_offer_rows(rows, status_filter="all", currency_filter="all"):
    status_sets = {
        "pending": {"draft", "pending", "waiting", "beklemede", "revision_pending", "sent"},
        "accepted": {"accepted", "approved", "onaylandi", "processed"},
        "rejected": {"rejected", "declined", "reddedildi", "draft", "created"},
        "draft": {"draft", "created"},
    }
    filtered = []
    for row in rows:
        status = str(_row_value(row, "status")).strip().lower()
        for source, replacement in (("\u0131", "i"), ("\u0130", "i"), ("\u015f", "s"), ("\u00e7", "c"), ("\u00f6", "o"), ("\u00fc", "u"), ("\u011f", "g")):
            status = status.replace(source, replacement)
        currency = str(_row_value(row, "currency_code", default="TRY") or "TRY").upper()
        if status_filter != "all" and status not in status_sets.get(status_filter, set()):
            continue
        if currency_filter != "all" and currency != currency_filter:
            continue
        filtered.append(row)
    return filtered


def _page_title(title_text, subtitle_text):
    box = QVBoxLayout()
    title = QLabel(title_text)
    title.setStyleSheet(theme_qss(
        "font-size: 24px; font-weight: 850; color: @text; "
        "border: none; background: transparent;"
    ))
    subtitle = QLabel(subtitle_text)
    subtitle.setWordWrap(True)
    subtitle.setStyleSheet(theme_qss(
        "font-size: 12px; color: @text_muted; border: none; background: transparent;"
    ))
    box.addWidget(title)
    box.addWidget(subtitle)
    return box


def _button(text, variant="secondary"):
    button = QPushButton(text)
    button.setMinimumHeight(36)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant)))
    return button


def _table(columns):
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(38)
    table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def _card():
    frame = QFrame()
    frame.setObjectName("OfferCard")
    frame.setStyleSheet(theme_qss(
        DesignTokens.get_card_qss(hover=False).replace("QFrame", "QFrame#OfferCard")
    ))
    return frame

class _ListPageBase(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.store = OfferService(db)
        self.current_rows = []

    def _toolbar(self, placeholder):
        layout = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(placeholder)
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        search_handler = getattr(self, "_schedule_refresh_data", self.refresh_data)
        self.search.textChanged.connect(search_handler)
        layout.addWidget(self.search, 1)
        btn_export = _button("Excel \u00c7\u0131kt\u0131")
        btn_export.clicked.connect(self.export_csv)
        layout.addWidget(btn_export)
        return layout

    def export_csv(self):
        if not self.current_rows:
            show_warning(self, "D\u0131\u015fa aktar\u0131lacak kay\u0131t bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Excel Uyumlu CSV Kaydet",
            f"ayec_export_{datetime.now():%Y%m%d_%H%M}.csv",
            "CSV (*.csv)",
        )
        if not path:
            return
        headers = [
            self.table.horizontalHeaderItem(column).text()
            for column in range(self.table.columnCount())
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as output:
            writer = csv.writer(output, delimiter=";")
            writer.writerow(headers)
            for row in range(self.table.rowCount()):
                values = []
                for column in range(self.table.columnCount()):
                    item = self.table.item(row, column)
                    values.append(item.text() if item else "")
                writer.writerow(values)
        show_success(self, "CSV dosyas\u0131 kaydedildi.")


def _status_label(status):
    mapping = {
        "draft": "Taslak",
        "sent": "G\u00f6nderildi",
        "partial": "K\u0131smen Geldi",
        "received": "Teslim Al\u0131nd\u0131",
        "invoiced": "Fatura Kay\u0131tl\u0131",
        "accepted": "Onayland\u0131",
        "approved": "Onayland\u0131",
        "rejected": "Reddedildi",
        "created": "Olu\u015fturuldu",
    }
    return mapping.get(str(status or "").lower(), str(status or "-"))


class _ReportPageBase(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.store = OfferService(db)

    @staticmethod
    def _metric(title, value, accent="@accent"):
        card = _card()
        layout = QVBoxLayout(card)
        value_label = QLabel(str(value))
        value_label.setObjectName("value")
        value_label.setStyleSheet(
            theme_qss(
                f"font-size: 22px; font-weight: 900; color: {accent};"
            )
        )
        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss("font-weight: 700; color: @text_muted;"))
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return card

    @staticmethod
    def _metric_value(card, value):
        label = card.findChild(QLabel, "value")
        if label:
            label.setText(str(value))


class OffersPage(_ListPageBase):
    def __init__(self, db, main_window=None):
        super().__init__(db, main_window)
        self.current_page = 1
        self.page_size = 6
        self._last_search = ""
        self._search_refresh_timer = QTimer(self)
        self._search_refresh_timer.setSingleShot(True)
        self._search_refresh_timer.setInterval(180)
        self._search_refresh_timer.timeout.connect(self.refresh_data)
        self._build_ui()
        self.refresh_data()

    def _schedule_refresh_data(self, *_args):
        self._search_refresh_timer.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)
        self.header_frame = QFrame(self)
        self.header_frame.setObjectName("OfferReferenceHeader")
        self.header_frame.setStyleSheet(theme_qss(
            "QFrame#OfferReferenceHeader { background: @finance_surface; border: none; border-radius: 6px; }"
        ))
        heading_box = QVBoxLayout(self.header_frame)
        heading_box.setContentsMargins(8, 8, 8, 8)
        heading_box.setSpacing(4)
        header = QHBoxLayout()
        header.setSpacing(6)
        title = QLabel("Teklif Y\u00f6netimi", self.header_frame)
        title.setStyleSheet(theme_qss("color: @finance_text; font-size: 18px; font-weight: 700; border: none; background: transparent;"))
        header.addWidget(title)
        badge = QLabel("AYEC-QUOTES-v2")
        badge.setStyleSheet(theme_qss(
            "background: @finance_surface_high; color: @finance_text_muted; border: none; "
            "border-radius: 4px; padding: 2px 4px; font-size: 9px; font-weight: 700;"
        ))
        header.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch()
        self.btn_quick_basket = _button("H\u0131zl\u0131 Teklif Sepeti")
        self.btn_quick_basket.clicked.connect(self._open_sales)
        header.addWidget(self.btn_quick_basket)
        self.btn_header_export = _button("Excel \u00c7\u0131kt\u0131")
        self.btn_header_export.clicked.connect(self.export_csv)
        header.addWidget(self.btn_header_export)
        self.btn_reports = _button("Raporlar")
        self.btn_reports.clicked.connect(lambda: self._navigate_to_page(314))
        header.addWidget(self.btn_reports)
        btn_new = _button("+ Yeni Teklif Olu\u015ftur", "success")
        btn_new.clicked.connect(lambda: self._open_sales())
        header.addWidget(btn_new)
        self.reference_header_actions = [self.btn_quick_basket, self.btn_header_export, self.btn_reports, btn_new]
        for index, button in enumerate(self.reference_header_actions):
            button.setFixedHeight(28)
            button.setAccessibleName(button.text())
            button.setStyleSheet(theme_qss(
                "QPushButton { background: @" + ("finance_action_income" if index == 3 else "finance_surface_high")
                + "; color: @" + ("finance_action_income_text" if index == 3 else "finance_text")
                + "; border: none; border-radius: 4px; padding: 0 8px; font-size: 11px; font-weight: 600; }"
                "QPushButton:hover { background: @finance_active_bg; color: @finance_text; }"
            ))
        heading_box.addLayout(header)
        subtitle = QLabel("M\u00fc\u015fterilere sunulan teklifleri haz\u0131rlay\u0131n, durumlar\u0131n\u0131 ve d\u00f6viz bazl\u0131 onay s\u00fcre\u00e7lerini izleyin.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 11px; border: none; background: transparent;"))
        heading_box.addWidget(subtitle)
        root.addWidget(self.header_frame)
        stats = QHBoxLayout()
        stats.setSpacing(8)
        self.cards = [
            self._offer_card("T\u00fcm Teklifler", "@finance_action_collection", "excel"),
            self._offer_card("Onay Bekliyor", "@finance_tertiary", "clock"),
            self._offer_card("Onayland\u0131", "@finance_secondary", "collection"),
            self._offer_card("Red / Taslak", "@finance_tertiary", "expense"),
            self._offer_card("Teklif Hacmi", "@finance_text", "bank"),
        ]
        for card in self.cards:
            stats.addWidget(card)
        root.addLayout(stats)
        toolbar = self._toolbar("Teklif no, m\u00fc\u015fteri, firma veya \u00fcr\u00fcn ara...")
        self.status_filter = QComboBox()
        for label, value in (("Durum: T\u00fcm\u00fc", "all"), ("Onay Bekliyor", "pending"), ("Onayland\u0131", "accepted"), ("Red / Taslak", "rejected")):
            self.status_filter.addItem(label, value)
        self.currency_filter = QComboBox()
        for label, value in (("D\u00f6viz: T\u00fcm\u00fc", "all"), ("TRY", "TRY"), ("USD", "USD"), ("EUR", "EUR")):
            self.currency_filter.addItem(label, value)
        for combo in (self.status_filter, self.currency_filter):
            combo.setMinimumHeight(38)
            combo.setMinimumWidth(126)
            combo.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            combo.currentIndexChanged.connect(self._on_filters_changed)
        toolbar.insertWidget(1, self.status_filter)
        toolbar.insertWidget(2, self.currency_filter)
        toolbar_export = toolbar.itemAt(3).widget()
        toolbar.removeWidget(toolbar_export)
        toolbar_export.deleteLater()
        root.addLayout(toolbar)
        self.table = _table(
            [
                "Teklif No",
                "Tarih",
                "M\u00fc\u015fteri",
                "Firma",
                "Toplam Tutar",
                "G\u00f6nderen Personel",
                "Onay Durumu",
                "Not / Evrak",
                "A\u00e7",
                "D\u00fczenle",
            ]
        )
        self.table.itemSelectionChanged.connect(self._on_offer_selection_changed)
        header_view = self.table.horizontalHeader()
        header_view.setFixedHeight(32)
        header_view.setStretchLastSection(False)
        fixed_widths = {0: 90, 8: 66, 9: 88}
        for column in range(self.table.columnCount()):
            if column in fixed_widths:
                header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.table.setColumnWidth(column, fixed_widths[column])
            else:
                header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
            item = self.table.horizontalHeaderItem(column)
            item.setToolTip(item.text())
        for column, text in ((4, "TOPLAM\nTUTAR"), (5, "G\u00d6NDEREN\nPERSONEL"), (6, "ONAY\nDURUMU"), (7, "NOT /\nEVRAK")):
            self.table.horizontalHeaderItem(column).setText(text)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.setStyleSheet(
            theme_qss(
                """
                QTableWidget {
                    border-radius: 4px;
                    border: 1px solid @finance_outline;
                    background: @finance_surface;
                    alternate-background-color: @finance_surface_container;
                    color: @finance_text;
                    font-size: 11px;
                }
                QTableWidget:focus { outline: none; }
                QHeaderView::section {
                    background-color: @finance_canvas;
                    color: @finance_text_muted;
                    padding: 2px 4px;
                    font-size: 9px;
                    font-weight: bold;
                    border: none;
                }
                QTableWidget::item {
                    padding: 4px;
                    color: @finance_text;
                    border: none;
                }
                QTableWidget::item:hover {
                    background-color: @selection_bg;
                    color: @accent_pressed;
                }
                QTableWidget::item:selected {
                    background-color: @finance_active_bg;
                    color: @finance_text;
                }
                QTableWidget::item:focus { outline: none; }
                """
            )
        )
        content = QHBoxLayout()
        content.setSpacing(12)
        self.reference_list_column = QVBoxLayout()
        self.reference_list_column.setSpacing(4)
        self.reference_list_column.addWidget(self.table)
        content.addLayout(self.reference_list_column, 2)
        content.addWidget(self._build_preview_panel(), 1)
        root.addLayout(content, 1)
        footer = QHBoxLayout()
        self.page_info = QLabel("")
        self.page_info.setStyleSheet(theme_qss("color: @text_muted; font-weight: 650;"))
        footer.addWidget(self.page_info)
        footer.addStretch()
        self.btn_previous = _button("\u25c0 \u00d6nceki")
        self.page_number = QLabel("1 / 1")
        self.page_number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_number.setMinimumWidth(72)
        self.page_number.setStyleSheet(
            theme_qss(
                "padding: 9px 12px; border: 1px solid @border; "
                "border-radius: 10px; color: @text; font-weight: 750;"
            )
        )
        self.btn_next = _button("Sonraki \u25b6", "primary")
        self.btn_previous.clicked.connect(lambda: self._change_page(-1))
        self.btn_next.clicked.connect(lambda: self._change_page(1))
        footer.addWidget(self.btn_previous)
        footer.addWidget(self.page_number)
        footer.addWidget(self.btn_next)
        for control in (self.btn_previous, self.page_number, self.btn_next):
            control.setFixedHeight(28)
            control.setStyleSheet(theme_qss(
                "background: @finance_surface_high; color: @finance_text; border: none; "
                "border-radius: 4px; padding: 0 6px; font-size: 11px;"
            ))
        self.reference_list_column.addLayout(footer)
        self.reference_list_column.addStretch(1)

    @staticmethod
    def _offer_card(title, accent, glyph="excel"):
        card = _card()
        card.setFixedHeight(90)
        card.setStyleSheet(theme_qss("QFrame#OfferCard { background: @finance_surface_container; border: none; border-radius: 4px; }"))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        count = QLabel("0")
        count.setObjectName("count")
        count.setStyleSheet(
            theme_qss(f"font-size: 24px; font-weight: 700; color: {accent}; border: none; background: transparent;")
        )
        label = QLabel(title.replace("i", "\u0130").replace("\u0131", "I").upper())
        label.setStyleSheet(theme_qss("font-size: 10px; font-weight: 700; color: @finance_text_muted; background: transparent; border: none;"))
        heading = QHBoxLayout()
        heading.setSpacing(4)
        heading.addWidget(label, 1)
        heading.addWidget(FinancialMetricGlyph(glyph, accent.lstrip("@"), card))
        layout.addLayout(heading)
        layout.addWidget(count)
        accent_line = QFrame()
        accent_line.setFixedHeight(3)
        accent_line.setStyleSheet(theme_qss(f"background: {accent}; border: none; border-radius: 1px;"))
        layout.addWidget(accent_line)
        return card

    def _build_preview_panel(self):
        panel = QFrame()
        panel.setObjectName("OfferPreviewPanel")
        panel.setMinimumWidth(280)
        panel.setStyleSheet(theme_qss(
            "QFrame#OfferPreviewPanel { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"
        ))
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("M\u00fc\u015fteri ve \u0130\u015flem")
        title.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text;"))
        layout.addWidget(title)
        hint = QLabel("Bir teklif sat\u0131r\u0131n\u0131 a\u00e7\u0131n veya yeni teklif olu\u015fturun.")
        hint.setWordWrap(True)
        hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        layout.addWidget(hint)

        self.preview_fields = {}
        for key_name, label, value in (
            ("customer", "M\u00fc\u015fteri", "-"),
            ("date", "\u0130\u015flem Tarihi", "-"),
            ("currency", "Para Birimi", "-"),
            ("items", "H\u0131zl\u0131 Teklif", "-"),
        ):
            row = QFrame()
            row.setObjectName("OfferPreviewField")
            row.setStyleSheet(theme_qss(
                "QFrame#OfferPreviewField { background: @surface; border: 1px solid @border; border-radius: 4px; }"
            ))
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 7, 10, 7)
            row_layout.setSpacing(2)
            key = QLabel(label)
            key.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; font-weight: 700;"))
            val = QLabel(value)
            val.setStyleSheet(theme_qss("color: @text; font-weight: 750;"))
            self.preview_fields[key_name] = val
            row_layout.addWidget(key)
            row_layout.addWidget(val)
            layout.addWidget(row)

        selection_actions = QHBoxLayout()
        self.btn_add_to_basket = _button("Sepete Ekle", "success")
        self.btn_bulk_select = _button("Toplu Se\u00e7im")
        self.btn_add_to_basket.clicked.connect(self._edit_selected_offer)
        self.btn_bulk_select.clicked.connect(self._toggle_bulk_selection)
        selection_actions.setSpacing(8)
        selection_actions.addWidget(self.btn_add_to_basket, 1)
        selection_actions.addWidget(self.btn_bulk_select, 1)
        layout.addLayout(selection_actions)

        summary = QFrame()
        summary.setObjectName("OfferPreviewSummary")
        summary.setStyleSheet(theme_qss("QFrame#OfferPreviewSummary { background: @surface; border: 1px solid @border; border-radius: 4px; }"))
        summary_layout = QGridLayout(summary)
        summary_layout.setContentsMargins(10, 8, 10, 8)
        summary_layout.setHorizontalSpacing(12)
        self.preview_amounts = {}
        for row_index, (amount_key, caption, color) in enumerate((
            ("subtotal", "Ara Toplam", "@text"),
            ("discount", "\u0130ndirim", "@danger"),
            ("tax", "KDV", "@text"),
            ("total", "Genel Toplam", "@success"),
        )):
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px; font-weight: 700;"))
            value_label = QLabel("-")
            value_label.setStyleSheet(theme_qss(f"color: {color}; font-size: 12px; font-weight: 850;"))
            self.preview_amounts[amount_key] = value_label
            summary_layout.addWidget(caption_label, row_index, 0)
            summary_layout.addWidget(value_label, row_index, 1)
        layout.addWidget(summary)

        layout.addStretch()
        self.preview_total = QLabel("Teklif hacmi\n0")
        self.preview_total.setStyleSheet(theme_qss("color: @success; font-size: 18px; font-weight: 850;"))
        layout.addWidget(self.preview_total)
        approve = QPushButton("Teklif Aninda Onaylansin")
        approve.setCheckable(True)
        approve.setStyleSheet(theme_qss("QPushButton{background:@surface;color:@text;border:1px solid @border;border-radius:6px;padding:6px;} QPushButton:checked{background:@success_bg;color:@success;}"))
        layout.addWidget(approve)
        self.preview_action_buttons = []
        for action_label in (
            "Proforma Olu\u015ftur & \u0130let",
            "\u00d6deme Al ve Kaydet",
            "Servis Kayd\u0131na D\u00f6n\u00fc\u015ft\u00fcr",
        ):
            action_button = _button(action_label, "primary" if action_label.startswith("Proforma") else "secondary")
            action_button.clicked.connect(self._edit_selected_offer)
            layout.addWidget(action_button)
            self.preview_action_buttons.append(action_button)
        create_offer = _button("Teklif Olu\u015ftur", "success")
        create_offer.clicked.connect(self._open_sales)
        layout.addWidget(create_offer)
        return panel

    def _open_sales(self):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(150)

    def _navigate_to_page(self, page_id):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(int(page_id))

    def _selected_offer(self):
        row_index = self.table.currentRow() if hasattr(self, "table") else -1
        if row_index < 0:
            return None
        offer_id_item = self.table.item(row_index, 0)
        offer_id = offer_id_item.data(Qt.ItemDataRole.UserRole) if offer_id_item else None
        return next(
            (row for row in self.current_rows if int(_row_value(row, "id", default=0)) == int(offer_id or 0)),
            None,
        )

    def _on_offer_selection_changed(self):
        offer = self._selected_offer()
        if not offer:
            for field in self.preview_fields.values():
                field.setText("-")
            for value_label in self.preview_amounts.values():
                value_label.setText("-")
            self.preview_total.setText("Teklif Toplam\n-")
            for button in [self.btn_add_to_basket, *self.preview_action_buttons]:
                button.setEnabled(False)
            return
        currency = str(_row_value(offer, "currency_code", default="TRY") or "TRY").upper()
        customer = str(_row_value(offer, "customer_name", default="-") or "-")
        company = str(_row_value(offer, "company_name", default="") or "").strip()
        if company:
            customer = "{} | {}".format(customer, company)
        created = str(_row_value(offer, "created_at", default="") or "")[:10]
        self.preview_fields["customer"].setText(customer)
        self.preview_fields["date"].setText(created or "-")
        self.preview_fields["currency"].setText(currency)
        self.preview_fields["items"].setText(str(_row_value(offer, "items", default="-") or "-"))
        amounts = {
            "subtotal": _row_value(offer, "subtotal", default=_row_value(offer, "total", default=0)),
            "discount": _row_value(offer, "discount", default=0),
            "tax": _row_value(offer, "tax_amount", default=_row_value(offer, "tax_total", default=0)),
            "total": _row_value(offer, "total", default=0),
        }
        for key, value in amounts.items():
            self.preview_amounts[key].setText(_money(value, currency))
        try:
            calculated_total = (
                float(amounts["subtotal"] or 0)
                - float(amounts["discount"] or 0)
                + float(amounts["tax"] or 0)
            )
            stored_total = float(amounts["total"] or 0)
        except (TypeError, ValueError):
            calculated_total = stored_total = 0.0
        total_label = self.preview_amounts["total"]
        if abs(calculated_total - stored_total) > 0.01:
            delta = stored_total - calculated_total
            total_label.setText(_money(amounts["total"], currency) + " !")
            total_label.setStyleSheet(theme_qss(
                "color: @danger; font-size: 12px; font-weight: 850;"
            ))
            total_label.setToolTip(
                "Ara toplam - indirim + KDV ile kay\u0131tl\u0131 toplam e\u015fle\u015fmiyor. "
                "Fark: {}".format(_money(delta, currency))
            )
        else:
            total_label.setStyleSheet(theme_qss(
                "color: @success; font-size: 12px; font-weight: 850;"
            ))
            total_label.setToolTip("")
        self.preview_total.setText("Teklif Toplam\n{}".format(_money(amounts["total"], currency)))
        offer_id = int(_row_value(offer, "id", default=0) or 0)
        for button in [self.btn_add_to_basket, *self.preview_action_buttons]:
            button.setEnabled(offer_id > 0)

    def _edit_selected_offer(self):
        offer = self._selected_offer()
        if offer:
            self._edit_offer(int(_row_value(offer, "id", default=0)))
        else:
            self._open_sales()

    def _toggle_bulk_selection(self):
        multi = self.table.selectionMode() != QAbstractItemView.SelectionMode.MultiSelection
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.MultiSelection
            if multi else QAbstractItemView.SelectionMode.SingleSelection
        )
        self.btn_bulk_select.setText("Tekli Se\u00e7im" if multi else "Toplu Se\u00e7im")

    def _edit_offer(self, offer_id):
        self._open_sales()
        if not self.main_window or not hasattr(self.main_window, "get_page"):
            return
        page = self.main_window.get_page(150)
        if page and hasattr(page, "load_offer_for_edit"):
            try:
                page.load_offer_for_edit(int(offer_id))
            except Exception as exc:
                show_error(self, f"Teklif d\u00fczenlemeye a\u00e7\u0131lamad\u0131: {exc}")

    def _open_offer(self, offer_id):
        try:
            dialog = OfferDetailsDialog(self.db, int(offer_id), self)

            dialog.exec()
        except Exception as exc:
            show_error(self, f"Teklif a\u00e7\u0131lamad\u0131: {exc}")

    def _change_page(self, delta):
        self.current_page = max(1, self.current_page + int(delta))
        self.refresh_data()

    def _on_filters_changed(self, *_args):
        self.current_page = 1
        self.refresh_data()

    def refresh_data(self, *_args):
        search = self.search.text().strip() if hasattr(self, "search") else ""
        if search != self._last_search:
            self.current_page = 1
            self._last_search = search
        status_filter = self.status_filter.currentData() if hasattr(self, "status_filter") else "all"
        currency_filter = self.currency_filter.currentData() if hasattr(self, "currency_filter") else "all"
        total_rows, page_rows = self.store.offers_page(
            search,
            status_filter,
            currency_filter,
            self.page_size,
            (self.current_page - 1) * self.page_size,
        )
        total_pages = max(1, (total_rows + self.page_size - 1) // self.page_size)
        requested_page = self.current_page
        self.current_page = min(max(1, self.current_page), total_pages)
        if self.current_page != requested_page:
            total_rows, page_rows = self.store.offers_page(
                search,
                status_filter,
                currency_filter,
                self.page_size,
                (self.current_page - 1) * self.page_size,
            )
        self.current_rows = page_rows
        start = (self.current_page - 1) * self.page_size
        self.table.setRowCount(len(page_rows))
        for row_index, row in enumerate(page_rows):
            offer_id = int(_row_value(row, "id", default=0))
            currency = _row_value(row, "currency_code", default="TRY")
            values = [
                _row_value(row, "offer_no"),
                str(_row_value(row, "created_at"))[:10],
                _row_value(row, "customer_name"),
                _row_value(row, "company_name"),
                _money(_row_value(row, "total", default=0), currency),
                _row_value(row, "accepted_by") or "-",
                _status_label(_row_value(row, "status")),
                _row_value(row, "pdf_path") or "-",
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                if column == 0 and "-" in str(value):
                    prefix, suffix = str(value).rsplit("-", 1)
                    item.setText(prefix + "-\n" + suffix)
                elif column == 1 and len(str(value)) == 10:
                    item.setText(str(value)[:5] + "\n" + str(value)[5:])
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row_index, column, item)
            self.table.item(row_index, 0).setData(Qt.ItemDataRole.UserRole, offer_id)
            btn_open = QPushButton("A\u00e7")
            btn_edit = QPushButton("D\u00fczenle")
            for button in (btn_open, btn_edit):
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setFixedHeight(26)
            btn_open.setStyleSheet(
                theme_qss(
                    """
                    QPushButton {
                        background: @accent;
                        color: @selection_text;
                        border: 1px solid @accent;
                        border-radius: 6px;
                        padding: 1px 6px;
                        font-size: 11px;
                        font-weight: 650;
                    }
                    QPushButton:hover { background: @accent_hover; }
                    QPushButton:pressed { background: @accent_pressed; }
                    """
                )
            )
            btn_edit.setStyleSheet(
                theme_qss(
                    """
                    QPushButton {
                        background: @warning;
                        color: @selection_text;
                        border: 1px solid @warning;
                        border-radius: 6px;
                        padding: 1px 6px;
                        font-size: 11px;
                        font-weight: 650;
                    }
                    QPushButton:hover { background: @warning_bg; color: @text; }
                    QPushButton:pressed { background: @warning; }
                    """
                )
            )
            btn_open.clicked.connect(
                lambda _=False, oid=offer_id: self._open_offer(oid)
            )
            btn_edit.clicked.connect(
                lambda _=False, oid=offer_id: self._edit_offer(oid)
            )
            self.table.setCellWidget(row_index, 8, btn_open)
            self.table.setCellWidget(row_index, 9, btn_edit)
            for button in (btn_open, btn_edit):
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_high; color: @finance_text; "
                    "border: none; border-radius: 4px; padding: 0 4px; font-size: 10px; font-weight: 600; }"
                    "QPushButton:hover { background: @finance_active_bg; }"
                ))
        self.table.setFixedHeight(34 + max(1, len(page_rows)) * 46)
        shown_start = start + 1 if page_rows else 0
        shown_end = start + len(page_rows)
        self.page_info.setText(
            f"{total_rows} kay\u0131ttan {shown_start}-{shown_end} aras\u0131 g\u00f6steriliyor."
        )
        self.page_number.setText(f"{self.current_page} / {total_pages}")
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        total, pending, accepted, rejected, _amount = self.store.offer_summary()
        for card, value in zip(self.cards, [total, pending, accepted, rejected, _money(_amount, "TRY")]):
            label = card.findChild(QLabel, "count")
            if label:
                label.setText(str(value or 0))
        if page_rows:
            self.table.selectRow(0)
        else:
            self._on_offer_selection_changed()


class OfferDetailsDialog(QDialog):
    def __init__(self, db, offer_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.offer_id = int(offer_id)
        self.setWindowTitle("Teklif Detay\u0131")
        self.resize(920, 620)
        self._build_ui()

    def _build_ui(self):
        offer = self.db.get_offer_record(self.offer_id)
        if not offer:
            raise RuntimeError("Teklif kayd\u0131 bulunamad\u0131.")
        items = self.db.get_offer_items_detailed(self.offer_id) or []
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)
        title = QLabel(
            f"Teklif: {str(_row_value(offer, 'offer_no') or '-')}"
        )
        title.setStyleSheet(
            theme_qss("font-size: 22px; font-weight: 900; color: @text;")
        )
        root.addWidget(title)
        info = QLabel(
            "M\u00fc\u015fteri: "
            f"{str(_row_value(offer, 'customer_name') or '-')}"
            "   |   Firma: "
            f"{str(_row_value(offer, 'company_name') or '-')}"
            "   |   Tarih: "
            f"{str(_row_value(offer, 'created_at') or '-')[:10]}"
        )
        info.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700;"))
        root.addWidget(info)
        table = _table(
            [
                "T\u00fcr",
                "Hizmet",
                "A\u00e7\u0131klama",
                "Marka",
                "Adet",
                "Birim Fiyat",
                "Toplam",
            ]
        )
        table.setRowCount(len(items))
        currency = str(_row_value(offer, "currency_code") or "TRY")
        for row_index, row in enumerate(items):
            values = [

                _row_value(row, "item_type"),
                _row_value(row, "service"),
                _row_value(row, "description"),
                _row_value(row, "brand"),
                _row_value(row, "qty", default=1),
                _money(_row_value(row, "unit_price", default=0), currency),
                _money(_row_value(row, "line_total", default=0), currency),
            ]
            for column, value in enumerate(values):
                table.setItem(row_index, column, QTableWidgetItem(str(value)))
        root.addWidget(table, 1)
        summary = QLabel(
            "Ara Toplam: "
            f"{_money(_row_value(offer, 'subtotal', default=0), currency)}"
            "   |   KDV: "
            f"{_money(_row_value(offer, 'vat_amount', default=0), currency)}"
            "   |   Genel Toplam: "
            f"{_money(_row_value(offer, 'total', default=0), currency)}"
        )
        summary.setAlignment(Qt.AlignmentFlag.AlignRight)
        summary.setStyleSheet(
            theme_qss("font-size: 15px; font-weight: 900; color: @success;")
        )
        root.addWidget(summary)
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        pdf_path = str(_row_value(offer, "pdf_path") or "").strip()
        if pdf_path and os.path.isfile(pdf_path):
            btn_pdf = actions.addButton(
                "PDF A\u00e7",
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            btn_pdf.clicked.connect(lambda: os.startfile(pdf_path))
        actions.rejected.connect(self.reject)
        root.addWidget(actions)


class OfferReportsPage(_ReportPageBase):
    def __init__(self, db, main_window=None):
        super().__init__(db, main_window)
        self._build_ui()
        self.refresh_data()

    @staticmethod
    def _report_card(title, table):
        card = _card()
        layout = QVBoxLayout(card)
        label = QLabel(title)
        label.setStyleSheet(theme_qss("font-weight: 800; color: @text;"))
        layout.addWidget(label)
        layout.addWidget(table, 1)
        return card

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        root.addLayout(
            _page_title(
                "Teklif Raporlar\u0131 ve Analizler",
                "Teklif s\u00fcre\u00e7lerini, m\u00fc\u015fteri da\u011f\u0131l\u0131m\u0131n\u0131 "
                "ve onay performans\u0131n\u0131 analiz edin.",
            )
        )
        metrics = QGridLayout()
        self.cards = [
            self._metric("Toplam Teklifler", 0),
            self._metric("Onay Bekliyor", 0, "@warning"),
            self._metric("Onayland\u0131", 0, "@success"),
            self._metric("Reddedildi", 0, "@danger"),
            self._metric("Toplam Teklif De\u011feri (TL)", _money(0), "@success"),
        ]
        for index, card in enumerate(self.cards):
            metrics.addWidget(
                card,
                0 if index < 4 else 1,
                index if index < 4 else 0,
                1,
                4 if index == 4 else 1,
            )
        root.addLayout(metrics)
        split = QHBoxLayout()
        self.trend_table = _table(
            [
                "Ay",
                "Teklif Say\u0131s\u0131",
                "Teklif Verilenler",
                "Haz\u0131rlayan Personel",
                "Toplam TL",
            ]
        )
        self.customer_table = _table(
            ["M\u00fc\u015fteri / Firma", "Teklif Say\u0131s\u0131", "Toplam TL"]
        )
        self.personnel_table = _table(
            ["Personel", "Teklif Say\u0131s\u0131", "Toplam TL"]
        )
        split.addWidget(
            OfferReportsPage._report_card(
                "Son 12 Ay Teklif Trendi", self.trend_table
            ),
            1,
        )
        rankings = QVBoxLayout()
        rankings.addWidget(
            OfferReportsPage._report_card(
                "En \u00c7ok Teklif Verilen M\u00fc\u015fteriler",
                self.customer_table,
            ),
            1,
        )
        rankings.addWidget(
            OfferReportsPage._report_card(
                "En \u00c7ok Teklif Haz\u0131rlayan Personeller",
                self.personnel_table,
            ),
            1,
        )
        split.addLayout(rankings, 1)
        root.addLayout(split, 1)

    def refresh_data(self):
        total, pending, accepted, rejected, amount = self.store.offer_summary()
        for card, value in zip(
            self.cards,
            [total, pending, accepted, rejected, _money(amount)],
        ):
            self._metric_value(card, value or 0)
        trend = self.store.monthly_offer_trend()
        self.trend_table.setRowCount(len(trend))
        for row_index, row in enumerate(trend):
            for column, value in enumerate(
                [
                    row[0],
                    row[1],
                    row[3] or "-",
                    row[4] or "-",
                    _money(row[2]),
                ]
            ):
                item = QTableWidgetItem(str(value))
                item.setToolTip(str(value))
                self.trend_table.setItem(row_index, column, item)
        customers = self.store.customer_offer_distribution()
        self.customer_table.setRowCount(len(customers))
        for row_index, row in enumerate(customers):
            for column, value in enumerate(
                [row[0], row[1], _money(row[2])]
            ):
                self.customer_table.setItem(
                    row_index, column, QTableWidgetItem(str(value))
                )
        personnel = self.store.personnel_offer_distribution()
        self.personnel_table.setRowCount(len(personnel))
        for row_index, row in enumerate(personnel):
            for column, value in enumerate(
                [row[0], row[1], _money(row[2])]
            ):
                self.personnel_table.setItem(
                    row_index, column, QTableWidgetItem(str(value))
                )
