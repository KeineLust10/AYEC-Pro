import csv
from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
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
    frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
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
        self.search.textChanged.connect(self.refresh_data)
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
        self.page_size = 100
        self._last_search = ""
        self._build_ui()
        self.refresh_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        header = QHBoxLayout()
        header.addLayout(
            _page_title(
                "T\u00fcm Teklifler",
                "M\u00fc\u015fterilere verilen teklifleri ve onay durumlar\u0131n\u0131 izleyin.",
            )
        )
        header.addStretch()
        btn_new = _button("Teklif Olu\u015ftur", "success")
        btn_new.clicked.connect(lambda: self._open_sales())
        header.addWidget(btn_new)
        root.addLayout(header)
        stats = QHBoxLayout()
        self.cards = [
            self._offer_card("T\u00fcm Teklifler", "@accent"),
            self._offer_card("Onay Bekliyor", "@warning"),
            self._offer_card("Onayland\u0131", "@success"),
            self._offer_card("Reddedildi", "@danger"),
        ]
        for card in self.cards:
            stats.addWidget(card)
        root.addLayout(stats)
        root.addLayout(self._toolbar("Teklif no, m\u00fc\u015fteri, firma veya \u00fcr\u00fcn ara..."))
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
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 66)
        self.table.setColumnWidth(9, 88)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setStyleSheet(
            theme_qss(
                """
                QTableWidget {
                    border-radius: 10px;
                    border: 1px solid @border;
                    background: @surface;
                }
                QTableWidget:focus { outline: none; }
                QHeaderView::section {
                    background-color: @surface_alt;
                    color: @text;
                    padding: 10px;
                    font-weight: bold;
                    border: none;
                }
                QTableWidget::item {
                    padding: 7px;
                    color: @text;
                    border-bottom: 1px solid @surface_alt;
                }
                QTableWidget::item:hover {
                    background-color: @selection_bg;
                    color: @accent_pressed;
                }
                QTableWidget::item:selected {
                    background-color: @accent;
                    color: @selection_text;
                }
                QTableWidget::item:focus { outline: none; }
                """
            )
        )
        root.addWidget(self.table, 1)
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
        root.addLayout(footer)

    @staticmethod
    def _offer_card(title, accent):
        card = _card()
        layout = QVBoxLayout(card)
        count = QLabel("0")
        count.setObjectName("count")
        count.setStyleSheet(
            theme_qss(f"font-size: 24px; font-weight: 900; color: {accent};")
        )
        label = QLabel(title)
        label.setStyleSheet(theme_qss("font-weight: 750; color: @text_muted;"))
        layout.addWidget(count)
        layout.addWidget(label)
        return card

    def _open_sales(self):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(150)

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

    def refresh_data(self, *_args):
        search = self.search.text().strip() if hasattr(self, "search") else ""
        if search != self._last_search:
            self.current_page = 1
            self._last_search = search
        rows = self.store.offers(search)
        self.current_rows = rows
        total_pages = max(1, (len(rows) + self.page_size - 1) // self.page_size)
        self.current_page = min(max(1, self.current_page), total_pages)
        start = (self.current_page - 1) * self.page_size
        page_rows = rows[start : start + self.page_size]
        self.table.setRowCount(len(page_rows))
        for row_index, row in enumerate(page_rows):
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
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self.table.setItem(row_index, column, item)
            offer_id = int(_row_value(row, "id", default=0))
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
        shown_start = start + 1 if page_rows else 0
        shown_end = start + len(page_rows)
        self.page_info.setText(
            f"{len(rows)} kay\u0131ttan {shown_start}-{shown_end} aras\u0131 g\u00f6steriliyor."
        )
        self.page_number.setText(f"{self.current_page} / {total_pages}")
        self.btn_previous.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < total_pages)
        total, pending, accepted, rejected, _amount = self.store.offer_summary()
        for card, value in zip(self.cards, [total, pending, accepted, rejected]):
            label = card.findChild(QLabel, "count")
            if label:
                label.setText(str(value or 0))


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
