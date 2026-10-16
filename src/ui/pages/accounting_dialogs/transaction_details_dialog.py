from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QBoxLayout, QLayout, QLabel, QPushButton,
                             QFormLayout, QTableWidget, QHeaderView, QFrame,
                             QAbstractItemView, QTableWidgetItem, QTextBrowser,
                             QApplication, QWidget, QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap, QColor, QPen
from src.utils.theme_colors import theme_qss, tc
from src.utils.currency_helper import CurrencyHelper
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.toast_notification import show_warning, show_error
from src.utils.logger import logger
from src.utils.service_work_details import (
    format_numbered_work_lines,
    load_service_work_lines,
)
import json
import re


def _format_service_item_total(db, entry, item, qty):
    currency = str(
        item.get("currency")
        or entry.get("currency")
        or "TRY"
    ).upper()
    line_total = item.get("line_total")
    if line_total in (None, ""):
        unit_price = item.get("unit_price", item.get("price", 0))
        line_total = float(unit_price or 0) * qty
    return CurrencyHelper.format_amount(
        float(line_total or 0),
        db=db,
        currency_code=currency,
    )


class TransactionDetailsDialog(BaseModernDialog):

    def __init__(self, db, entry, parent=None):
        super().__init__(parent=parent, title="\u0130\u015flem Detay\u0131", width=1440, height=1040)
        self.db = db
        self.entry = dict(entry or {})
        resolved_tracking = self._resolve_tracking_no()
        if resolved_tracking:
            self.entry["tracking_no"] = resolved_tracking
            self.entry["ref_no"] = self.entry.get("ref_no") or resolved_tracking
        self.setMinimumSize(340, 480)
        self.footer.setFixedHeight(94)
        self.content_layout.setContentsMargins(31, 30, 32, 25)
        self.content_layout.setSpacing(12)
        self._build_reference_header()

        body = QHBoxLayout()
        self.body_layout = body
        body.setSpacing(22)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(20)
        amount_card = QFrame()
        amount_card.setMinimumHeight(212)
        amount_card.setStyleSheet(theme_qss(
            "background: @surface_alt; border: 1px solid @border; border-radius: 12px;"
        ))
        amount_layout = QVBoxLayout(amount_card)
        amount_layout.setContentsMargins(18, 16, 24, 16)
        amount_layout.setSpacing(6)
        amount_header = QHBoxLayout()
        amount_title = QLabel("\u0130\u015eLEM TUTARI (D\u00d6V\u0130Z)")
        amount_title.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none; font-weight: 800;"
        ))
        amount_header.addWidget(amount_title)
        amount_header.addStretch(1)
        amount_source = QLabel(
            "D\u00f6viz \u0130\u015flemi" if self.entry.get("source") == "currency" else "Muhasebe"
        )
        amount_source.setStyleSheet(theme_qss(
            "color: @finance_breadcrumb_active; background: @finance_surface_alt; "
            "border: 1px solid @finance_outline; border-radius: 5px; padding: 4px 8px;"
        ))
        amount_source.setFixedSize(121, 33)
        amount_source.setAlignment(Qt.AlignmentFlag.AlignCenter)
        amount_header.addWidget(amount_source)
        amount_layout.addLayout(amount_header)

        currency = str(self.entry.get("currency") or "TRY").upper()
        amount = float(self.entry.get("amount") or 0)
        amount_try = float(self.entry.get("amount_try") or 0)
        rate = float(self.entry.get("rate") or 1.0)
        self.amount_value = QLabel(CurrencyHelper.format_amount(
            amount if currency != "TRY" else amount_try,
            db=self.db,
            currency_code=currency,
        ))
        self.amount_value.setObjectName("TransactionAmountValue")
        self.amount_value.setStyleSheet(theme_qss(
            "color: @text; background: transparent; border: none; padding: 0; "
            "font: 700 36px 'JetBrains Mono';"
        ))
        amount_layout.addWidget(self.amount_value)
        amount_layout.addSpacing(14)
        amount_divider = QFrame()
        amount_divider.setFixedHeight(1)
        amount_divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        amount_layout.addWidget(amount_divider)
        amount_layout.addSpacing(8)
        rate_row = QHBoxLayout()
        rate_row.setSpacing(6)
        self.rate_title = QLabel("D\u00f6viz Kuru")
        self.rate_title.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none; font-size: 12px;"
        ))
        self.rate_value = QLabel(f"{rate:.4f} \u20ba")
        self.rate_value.setObjectName("TransactionAmountRate")
        self.rate_value.setStyleSheet(theme_qss(
            "color: @text; background: transparent; border: none; font: 12px 'JetBrains Mono';"
        ))
        self.try_title = QLabel("TL Kar\u015f\u0131l\u0131\u011f\u0131")
        self.try_title.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none; font-size: 12px;"
        ))
        self.try_value = QLabel(CurrencyHelper.format_amount(
            amount_try, db=self.db, currency_code="TRY"
        ))
        self.try_value.setObjectName("TransactionAmountTry")
        self.try_value.setStyleSheet(theme_qss(
            "color: @success; background: transparent; border: none; font: 700 12px 'JetBrains Mono';"
        ))
        rate_group = QVBoxLayout()
        rate_group.setSpacing(2)
        rate_group.addWidget(self.rate_title)
        rate_group.addWidget(self.rate_value)
        try_group = QVBoxLayout()
        try_group.setSpacing(2)
        try_group.addWidget(self.try_title)
        try_group.addWidget(self.try_value)
        rate_row.addLayout(rate_group, 1)
        rate_row.addLayout(try_group, 1)
        amount_layout.addLayout(rate_row)
        left_column.addWidget(amount_card)

        left_card = QFrame()
        left_card.setStyleSheet(theme_qss(
            "background: @surface; border: 1px solid @border; border-radius: 12px;"
        ))
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(16, 14, 16, 14)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(20, 8, 20, 12)
        left_layout.setSpacing(0)

        def add_divider():
            divider = QFrame(left_card)
            divider.setFixedHeight(1)
            divider.setStyleSheet(theme_qss("background: @border; border: none;"))
            left_layout.addWidget(divider)

        def add_inline_row(label, value, value_color="@text"):
            row = QWidget(left_card)
            row.setStyleSheet("background: transparent; border: none;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(12)
            label_widget = QLabel(label)
            label_widget.setStyleSheet(theme_qss(
                "color: @text_muted; background: transparent; border: none; font-size: 12px;"
            ))
            value_widget = QLabel(str(value) if value is not None else "\u2014")
            value_widget.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value_widget.setStyleSheet(theme_qss(
                f"color: {value_color}; background: transparent; border: none; "
                "font-weight: 600; font-size: 12px;"
            ))
            row_layout.addWidget(label_widget, 1)
            row_layout.addWidget(value_widget)
            left_layout.addWidget(row)
            add_divider()
            return value_widget

        def add_stacked_row(label, value_widget, top_padding=8, bottom_padding=8):
            block = QWidget(left_card)
            block.setStyleSheet("background: transparent; border: none;")
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, top_padding, 0, bottom_padding)
            block_layout.setSpacing(8)
            label_widget = QLabel(label)
            label_widget.setStyleSheet(theme_qss(
                "color: @text_muted; background: transparent; border: none; font-size: 12px;"
            ))
            block_layout.addWidget(label_widget)
            block_layout.addWidget(value_widget)
            left_layout.addWidget(block)
            add_divider()

        add_inline_row(
            "Kaynak", "D\u00f6viz \u0130\u015flemi" if self.entry.get("source") == "currency" else "Muhasebe"
        )
        add_inline_row("Kay\u0131t ID", self.entry.get("id"))
        from src.utils.date_utils import format_turkish_date
        date_value = self.entry.get("date")
        if date_value:
            date_value = format_turkish_date(date_value, "short")
        add_inline_row("\u0130\u015flem Tarihi", date_value)
        add_inline_row("\u0130\u015flem T\u00fcr\u00fc", self.entry.get("type_label"), "@success")
        tracking = self.entry.get("tracking_no") or self.entry.get("ref_no")
        if tracking:
            tracking_value = QLabel(str(tracking))
            tracking_value.setStyleSheet(theme_qss(
                "color: @finance_breadcrumb_active; background: transparent; border: none; "
                "font: 11px 'JetBrains Mono';"
            ))
            tracking_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.btn_copy_tracking = QPushButton("\u29c9")
            self.btn_copy_tracking.setToolTip("Kopyala")
            self.btn_copy_tracking.setFixedSize(28, 28)
            tracking_row = QHBoxLayout()
            tracking_row.setContentsMargins(0, 0, 0, 0)
            tracking_row.addWidget(tracking_value, 1)
            tracking_row.addWidget(self.btn_copy_tracking)
            tracking_holder = QWidget(left_card)
            tracking_holder.setStyleSheet("background: transparent; border: none;")
            tracking_holder.setLayout(tracking_row)
            add_stacked_row("Takip / Teklif No", tracking_holder, 21, 8)
            self.btn_copy_tracking.clicked.connect(
                lambda _checked=False, value=str(tracking): QApplication.clipboard().setText(value)
            )
        if self.entry.get("payment_method"):
            add_inline_row("\u00d6deme Y\u00f6ntemi", self.entry.get("payment_method"))
        if self.entry.get("bank_account_id"):
            add_inline_row("Banka Hesab\u0131", self.entry.get("bank_account_id"))
        if self.entry.get("balance") is not None:
            add_inline_row(
                "Bakiye",
                CurrencyHelper.format_try_for_display(float(self.entry.get("balance") or 0), db=self.db),
            )
        if self.entry.get("customer_name"):
            customer_value = QLabel("\u25ce  " + str(self.entry.get("customer_name")) + "  \u2197")
            customer_value.setStyleSheet(theme_qss(
                "color: @finance_breadcrumb_active; background: transparent; border: none; "
                "font-size: 14px; font-weight: 600;"
            ))
            add_stacked_row("Cari / M\u00fc\u015fteri", customer_value, 8, 23)
        reference_text = (
            self.entry.get("debt_close_reference")
            or self.entry.get("description")
        )
        if reference_text:
            reference_box = QLabel(str(reference_text))
            reference_box.setWordWrap(True)
            reference_box.setMinimumHeight(104)
            reference_box.setStyleSheet(theme_qss(
                "color: @text; background: @finance_surface_lowest; border: 1px solid @border; "
                "border-radius: 8px; padding: 12px; font: 11px 'JetBrains Mono';"
            ))
            add_stacked_row("Cari Bor\u00e7 Kapatma Referans\u0131", reference_box)
        product_id = self.entry.get("product_service_id")
        if product_id:
            product_type = self.entry.get("product_service_type")
            add_inline_row("Stok" if product_type == "product" else "Hizmet", product_id)
        left_column.addWidget(left_card, 1)

        left_panel = QWidget()
        left_panel.setLayout(left_column)
        left_panel.setMinimumWidth(428)
        self.left_panel = left_panel
        body.addWidget(left_panel, 33)

        right_card = QFrame()
        right_card.setStyleSheet(theme_qss(
            "background: @surface; border: 1px solid @border; border-radius: 12px;"
        ))
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(0, 14, 0, 14)
        right_layout.setSpacing(6)
        table_header = QHBoxLayout()
        table_title = QLabel("\u25c7   STOK / H\u0130ZMET KALEMLER\u0130")
        table_title.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text; background: transparent; border: none;"
        ))
        table_header.setContentsMargins(20, 0, 20, 0)
        table_header.addWidget(table_title)
        table_header.addStretch(1)
        self.items_count = QLabel("Toplam 0 Kalem")
        self.items_count.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none; font: 12px 'JetBrains Mono';"
        ))
        table_header.addWidget(self.items_count)
        right_layout.addLayout(table_header)
        right_layout.addSpacing(15)

        self.items_table = QTableWidget()
        self.items_table.setMinimumWidth(0)
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "#",
            "STOK / DETAY A\u00c7IKLAMASI",
            "ADET",
            "B\u0130R\u0130M F\u0130YAT",
            "TUTAR",
        ])
        self.items_table.horizontalHeaderItem(0).setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.items_table.horizontalHeaderItem(1).setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.items_table.horizontalHeaderItem(2).setTextAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        for column in (3, 4):
            self.items_table.horizontalHeaderItem(column).setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_table.setShowGrid(False)
        self.items_table.setWordWrap(True)
        self.items_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.items_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.items_table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface;
                border: 1px solid @border;
                border-radius: 10px;
                color: @text;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
            QHeaderView::section {
                background: @surface_alt;
                border: none;
                border-bottom: 1px solid @border;
                padding: 10px 12px;
                font-size: 13px;
                font-weight: 800;
                color: @text_muted;
            }
            QTableWidget::item {
                padding: 10px 12px;
                border-bottom: 1px solid @border;
                font-size: 14px;
            }
        """))
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in (2, 3, 4):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        self.items_table.setColumnWidth(0, 40)
        self.items_table.setColumnWidth(2, 70)
        self.items_table.setColumnWidth(3, 155)
        self.items_table.setColumnWidth(4, 153)
        self.items_table.verticalHeader().setDefaultSectionSize(71)
        right_layout.addWidget(self.items_table, 1)

        items_footer = QHBoxLayout()
        items_footer.setContentsMargins(16, 10, 16, 38)
        items_footer.setSpacing(14)
        self.stock_status = QLabel("\u2713 T\u00fcm kalemler stoktan d\u00fc\u015ft\u00fc ve faturaya i\u015flendi.")
        self.stock_status.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none;"
        ))
        items_footer.addWidget(self.stock_status, 1)
        self.vat_total = QLabel("KDV\n0.00")
        self.grand_total = QLabel("Genel Toplam\n0.00")
        self.vat_total.setStyleSheet(theme_qss(
            "color: @text_muted; background: transparent; border: none; "
            "font: 10px 'JetBrains Mono'; padding-right: 10px;"
        ))
        self.grand_total.setStyleSheet(theme_qss(
            "color: @success; background: transparent; border: none; "
            "font-weight: 800; font: 13px 'JetBrains Mono';"
        ))
        items_footer.addWidget(self.vat_total)
        footer_divider = QFrame()
        footer_divider.setFixedSize(1, 42)
        footer_divider.setStyleSheet(theme_qss("background: @border; border: none;"))
        items_footer.addWidget(footer_divider)
        items_footer.addWidget(self.grand_total)
        right_layout.addLayout(items_footer)

        self.desc_group = QFrame()
        self.desc_group.setStyleSheet(theme_qss(
            "background: @surface_alt; border: 1px solid @border; border-radius: 10px;"
        ))
        desc_layout = QVBoxLayout(self.desc_group)
        desc_layout.setContentsMargins(17, 20, 17, 12)
        desc_layout.setSpacing(20)
        desc_title = QLabel("\u270e     \u0130\u015eLEM A\u00c7IKLAMASI & NOTLAR")
        desc_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        desc_title.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        desc_title.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text_muted; background: transparent; border: none;"
        ))
        desc_layout.addWidget(desc_title)
        self.txt_desc = QTextBrowser()
        self.txt_desc.setStyleSheet(theme_qss("""
            QTextBrowser {
                background: @finance_surface_lowest;
                border: 1px solid @border;
                border-radius: 8px;
                color: @text;
                font: 12px 'JetBrains Mono';
                padding: 18px 10px 10px 10px;
            }
        """))
        self.txt_desc.setMinimumHeight(180)
        desc_layout.addWidget(self.txt_desc, 1)
        right_layout.addWidget(self.desc_group, 1)
        body.addWidget(right_card, 67)
        self.right_card = right_card
        self.content_layout.addLayout(body, 1)

        self.btn_service = self.add_button(
            "Servis Formu", "primary", self.open_service_form
        )
        self.btn_service.setVisible(bool(tracking))
        self.btn_open_360 = self.add_button(
            "M\u00fc\u015fteri 360\u00b0", "secondary", self.open_customer_360
        )
        self.btn_open_360.setVisible(bool(self.entry.get("customer_id")))
        self.footer_layout.addStretch(1)
        footer_spacer = self.footer_layout.itemAt(self.footer_layout.count() - 1).spacerItem()
        self.btn_print = self.add_button(
            "Makbuz Yazd\u0131r", "secondary", self.print_receipt
        )
        self.btn_edit = self.add_button(
            "D\u00fczenle", "secondary", self.edit_transaction
        )
        self.btn_close_action = self.add_button(
            "Kapat (ESC)", "secondary", self.reject
        )
        self.btn_close_action.setShortcut("Esc")
        self.set_footer_visible(True, 94)
        self._footer_spacer = footer_spacer
        self.populate_items_table()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        mobile = event.size().width() < 760
        self.setMinimumSize(320, 420)
        if hasattr(self, "card"):
            self.card.setMinimumSize(300 if mobile else 420, 240)
        if hasattr(self, "header"):
            self.header.setFixedHeight(82 if mobile else 100)
        if hasattr(self, "content_layout"):
            self.content_layout.setSizeConstraint(
                QLayout.SizeConstraint.SetNoConstraint if mobile
                else QLayout.SizeConstraint.SetDefaultConstraint
            )
            self.content_layout.setContentsMargins(
                12, 12, 12, 12
            ) if mobile else self.content_layout.setContentsMargins(31, 30, 32, 25)
            self.content_layout.setSpacing(8 if mobile else 12)
        if hasattr(self, "content_container") and mobile:
            available_width = max(320, event.size().width() - 10)
            self.content_container.setMinimumWidth(available_width)
            self.content_container.setMaximumWidth(available_width)
        elif hasattr(self, "content_container"):
            self.content_container.setMinimumWidth(0)
            self.content_container.setMaximumWidth(16777215)
        if hasattr(self, "body_layout"):
            self.body_layout.setDirection(
                QBoxLayout.Direction.TopToBottom if mobile else QBoxLayout.Direction.LeftToRight
            )
            self.body_layout.setSpacing(12 if mobile else 22)
            self.left_panel.setMinimumWidth(0 if mobile else 428)
            self.left_panel.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self.right_card.setMinimumWidth(0)
            self.right_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
            self.items_table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded if mobile
                else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
            )
        if hasattr(self, "scroll_area"):
            self.scroll_area.setMinimumWidth(0)
            self.scroll_area.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAlwaysOff if mobile
                else Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
        if hasattr(self, "footer_layout"):
            self.footer_layout.setDirection(
                QBoxLayout.Direction.TopToBottom if mobile else QBoxLayout.Direction.LeftToRight
            )
            self._footer_spacer.changeSize(
                0, 0,
                QSizePolicy.Policy.Fixed if mobile else QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed if mobile else QSizePolicy.Policy.Minimum,
            )
            self.footer_layout.invalidate()
            self.footer.setFixedHeight(260 if mobile else 94)
            for button in (
                self.btn_service, self.btn_open_360, self.btn_print,
                self.btn_edit, self.btn_close_action,
            ):
                button.setMinimumWidth(0)
                button.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
                )

    def _build_reference_header(self):
        from PyQt6.QtWidgets import QVBoxLayout
        self.header.setFixedHeight(100)
        header_layout = self.header.layout()
        header_layout.setContentsMargins(31, 0, 33, 0)
        title_index = header_layout.indexOf(self.lbl_title)
        header_layout.removeWidget(self.lbl_title)
        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(7, 0, 0, 0)
        title_layout.setSpacing(2)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_top = QHBoxLayout()
        title_top.setContentsMargins(0, 0, 0, 0)
        title_top.setSpacing(13)
        self.lbl_title.setText("\u0130\u015flem Detay\u0131")
        title_top.addWidget(self.lbl_title)
        self.status_badge = QLabel(str(
            self.entry.get("status_label") or self.entry.get("status") or "Kay\u0131t"
        ))
        self.status_badge.setStyleSheet(theme_qss(
            "color: @success; background: @finance_surface_alt; border: 1px solid @success; "
            "border-radius: 12px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
        ))
        title_top.addWidget(self.status_badge)
        record_id = self.entry.get("id")
        self.record_badge = QLabel(f"#KAYIT-{record_id}" if record_id is not None else "#KAYIT")
        self.record_badge.setStyleSheet(theme_qss(
            "color: @text_muted; background: @surface; border: 1px solid @border; "
            "border-radius: 5px; padding: 4px 8px; font: 10px 'JetBrains Mono';"
        ))
        title_top.addWidget(self.record_badge)
        title_layout.addLayout(title_top)
        self.header_subtitle = QLabel("Finans & Servis Entegrasyon Kart\u0131")
        self.header_subtitle.setObjectName("TransactionHeaderSubtitle")
        title_layout.addWidget(self.header_subtitle)
        header_layout.insertLayout(max(0, title_index), title_layout)
        self.status_badge.setFixedSize(126, 30)
        self.record_badge.setFixedSize(104, 28)
        self.lbl_title.setMinimumWidth(124)
        icon = QPixmap(40, 40)
        icon.fill(Qt.GlobalColor.transparent)
        painter = QPainter(icon)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#1e3a5f"), 1))
        painter.setBrush(QColor("#0c1b2c"))
        painter.drawRoundedRect(0, 0, 39, 39, 11, 11)
        painter.setPen(QPen(QColor("#38bdf8"), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(12, 8, 16, 24, 1, 1)
        painter.drawLine(16, 16, 24, 16)
        painter.drawLine(16, 21, 24, 21)
        painter.drawLine(16, 26, 22, 26)
        painter.end()
        self.logo_label.setPixmap(icon)

        self.btn_minimize = QPushButton("\u2212")
        self.btn_maximize = QPushButton("\u25a1")
        for button in (self.btn_minimize, self.btn_maximize):
            button.setFixedSize(28, 28)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @text_muted; "
                "border: 1px solid transparent; border-radius: 5px; font-size: 14px; } "
                "QPushButton:hover { background: @surface; border-color: @border; }"
            ))
        self.btn_minimize.clicked.connect(self.showMinimized)
        self.btn_maximize.clicked.connect(
            lambda: self.showNormal() if self.isMaximized() else self.showMaximized()
        )
        close_index = header_layout.indexOf(self.btn_close)
        header_layout.insertWidget(close_index, self.btn_minimize)
        header_layout.insertWidget(close_index + 1, self.btn_maximize)

    def print_receipt(self):
        from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
        from PyQt6.QtGui import QTextDocument
        from html import escape

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            text = [
                "AYEC Pro - Islem Makbuzu",
                f"Kayit: {self.entry.get('id', '')}",
                f"Tarih: {self.entry.get('date', '')}",
                f"Tur: {self.entry.get('type_label', '')}",
                f"Musteri: {self.entry.get('customer_name', '')}",
                f"Tutar: {self.amount_value.text()}",
                f"Aciklama: {self.entry.get('description', '')}",
            ]
            document = QTextDocument()
            document.setHtml("<br>".join(escape(line) for line in text))
            document.print(printer)

    def edit_transaction(self):
        main_window = self.parentWidget()
        while main_window is not None and not hasattr(main_window, "edit_transaction"):
            main_window = main_window.parentWidget()
        callback = getattr(main_window, "edit_transaction", None) if main_window else None
        if callable(callback):
            callback(dict(self.entry))
            return
        show_warning(self, "Islem duzenleme bu ekrandan kullanilamiyor.")

    def open_customer_360(self):
        customer_id = self.entry.get("customer_id")
        customer_name = self.entry.get("customer_name")
        if not customer_id:
            return
        try:
            from src.ui.dialogs.customer_360_dialog import Customer360Dialog
            Customer360Dialog(self.db, int(customer_id), customer_name or "", self).exec()
        except Exception:
            return

    def _parse_service_rows(self, payload):
        rows = []
        if not payload:
            return rows

        parsed_payload = payload
        if isinstance(payload, str):
            try:
                parsed_payload = json.loads(payload)
            except Exception:
                parsed_payload = payload

        if isinstance(parsed_payload, dict):
            parsed_payload = [parsed_payload]

        if isinstance(parsed_payload, (list, tuple, set)):
            for item in parsed_payload:
                if not isinstance(item, dict):
                    continue
                if item.get("kind") == "balance":
                    continue
                name = (
                    item.get("service")
                    or item.get("name")
                    or item.get("part_name")
                    or item.get("item_name")
                    or item.get("description")
                    or "Kalem"
                )
                sku = str(item.get("sku") or item.get("stock_code") or "").strip()
                if sku:
                    name = f"{name}\nSKU: {sku}"
                qty = item.get("qty") or item.get("quantity") or item.get("adet") or 1
                try:
                    qty_val = int(qty)
                except Exception:
                    qty_val = 1
                try:
                    price = _format_service_item_total(
                        self.db,
                        self.entry,
                        item,
                        qty_val,
                    )
                except Exception:
                    price = ""
                try:
                    currency = str(item.get("currency") or self.entry.get("currency") or "TRY").upper()
                    unit_price = CurrencyHelper.format_amount(
                        float(item.get("unit_price", item.get("price", 0)) or 0),
                        db=self.db,
                        currency_code=currency,
                    )
                except Exception:
                    unit_price = "\u2014"
                rows.append((str(name).strip(), str(qty_val), unit_price, price))
        return rows

    def _resolve_tracking_no(self):
        for value in (self.entry.get("tracking_no"), self.entry.get("ref_no")):
            candidate = str(value or "").strip()
            if candidate:
                return candidate
        description = str(self.entry.get("description") or "")
        match = re.search(
            r"(?:^|[|\s])Ref\s*[:#]?\s*([A-Za-z0-9._-]+)",
            description,
            flags=re.IGNORECASE,
        )
        return match.group(1) if match else ""

    def _load_device_service_rows(self):
        tracking_no = self._resolve_tracking_no()
        if not tracking_no:
            return []
        try:
            device = self.db.cursor.execute(
                "SELECT repair_details, fault_description, labor_cost, cargo_fee "
                "FROM devices WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
                (tracking_no,),
            ).fetchone()
            if not device:
                return []

            result = []
            repair_details = str(device[0] or "").strip()
            fault_description = str(device[1] or "").strip()
            work_lines = load_service_work_lines(
                self.db,
                tracking_no,
                repair_details=repair_details,
                fault_description=fault_description,
            )
            self._service_work_lines = work_lines
            for line in work_lines:
                result.append((f"Yap\u0131lan \u0130\u015flem: {line}", "1", ""))

            labor_cost = float(device[2] or 0)
            if labor_cost:
                result.append(
                    (
                        "\u0130\u015f\u00e7ilik",
                        "1",
                        CurrencyHelper.format_try_for_display(
                            labor_cost,
                            db=self.db,
                            include_try_reference=False,
                        ),
                    )
                )

            part_rows = self.db.cursor.execute(
                "SELECT part_name, quantity, price, currency, price_try, exchange_rate "
                "FROM used_parts WHERE tracking_no=? AND COALESCE(is_deleted,0)=0 "
                "ORDER BY id ASC",
                (tracking_no,),
            ).fetchall()
            for part in part_rows:
                quantity = float(part[1] or 1)
                quantity_text = str(int(quantity)) if quantity.is_integer() else f"{quantity:g}"
                price_try = float(part[4] or 0)
                if price_try:
                    total_text = CurrencyHelper.format_try_for_display(
                        price_try * quantity,
                        db=self.db,
                        include_try_reference=False,
                    )
                else:
                    total_text = CurrencyHelper.format_amount(
                        float(part[2] or 0) * quantity,
                        db=self.db,
                        currency_code=str(part[3] or "TRY").upper(),
                    )
                result.append((str(part[0] or "Par\u00e7a"), quantity_text, total_text))

            cargo_fee = float(device[3] or 0)
            if cargo_fee:
                result.append(
                    (
                        "Kargo",
                        "1",
                        CurrencyHelper.format_try_for_display(
                            cargo_fee,
                            db=self.db,
                            include_try_reference=False,
                        ),
                    )
                )
            return result
        except Exception as exc:
            logger.warning("Related service detail load failed: %s", exc)
            return []

    def _parse_description_rows(self, desc):
        import re

        rows = []
        for raw_line in str(desc or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line_l = line.lower()
            if line.startswith("Ref:") or ("cari bor" in line_l and "tahsilat" in line_l) or ("pesin" in line_l and "tahsilat" in line_l):
                continue
            match = re.match(r"^(?P<name>.+?)\s*\(x(?P<qty>\d+)\)\s*-\s*(?P<price>.+)$", line)
            if match:
                rows.append((match.group("name").strip(), match.group("qty").strip(), match.group("price").strip()))
        return rows

    def _load_related_service_rows(self):
        ref_no = self.entry.get("ref_no") or self.entry.get("tracking_no")
        if not ref_no:
            return []

        try:
            cols = set(self.db._get_table_columns("accounting")) if hasattr(self.db, "_get_table_columns") else set()
            select_cols = ["id", "description"]
            if "selected_services" in cols:
                select_cols.append("selected_services")
            where_parts = []
            params = []
            if "tracking_no" in cols:
                where_parts.append("tracking_no = ?")
                params.append(ref_no)
            if "ref_no" in cols:
                where_parts.append("ref_no = ?")
                params.append(ref_no)
            if not where_parts:
                return []

            current_id = self.entry.get("id")
            sql = f"SELECT {', '.join(select_cols)} FROM accounting WHERE ({' OR '.join(where_parts)})"
            if current_id:
                sql += " AND id <> ?"
                params.append(current_id)
            sql += " ORDER BY id DESC LIMIT 10"

            rows = self.db.cursor.execute(sql, tuple(params)).fetchall()
            for row in rows:
                record = dict(zip(select_cols, row))
                parsed_rows = self._parse_service_rows(record.get("selected_services"))
                if parsed_rows:
                    return parsed_rows
                parsed_rows = self._parse_description_rows(record.get("description"))
                if parsed_rows:
                    return parsed_rows
        except Exception:
            return []
        return []

    def populate_items_table(self):
        desc = str(self.entry.get("description") or "")
        transaction_note = str(self.entry.get("transaction_note") or desc)
        service_rows = self._load_device_service_rows()
        parsed = service_rows or self._parse_service_rows(self.entry.get("selected_services"))
        if not parsed:
            parsed = self._load_related_service_rows()
        if not parsed:
            parsed = self._parse_description_rows(desc)

        # Populate dedicated description box
        work_lines = list(
            self.entry.get("service_work_lines")
            or getattr(self, "_service_work_lines", [])
            or []
        )
        description_blocks = []
        if work_lines:
            description_blocks.append(
                "Yap\u0131lan \u0130\u015flemler:\n" + format_numbered_work_lines(work_lines)
            )
        if transaction_note.strip():
            description_blocks.append("Tahsilat / \u0130\u015flem Notu:\n" + transaction_note.strip())
        description_text = "\n\n".join(description_blocks)
        if description_text:
            from html import escape
            sections = []
            if work_lines:
                numbered_lines = format_numbered_work_lines(work_lines).splitlines()
                work_html = "<br>".join(escape(line) for line in numbered_lines)
                sections.append(
                    "<p><b>YAPILAN \u0130\u015eLEMLER:</b></p>"
                    f"<p style='line-height:1.65;'>{work_html}</p>"
                )
            if transaction_note.strip():
                sections.append(
                    "<hr>"
                    "<p><b>TAHS\u0130LAT / \u0130\u015eLEM NOTU:</b></p>"
                    f"<p style='line-height:1.65;'>{escape(transaction_note.strip())}</p>"
                )
            operator = str(
                self.entry.get("operator_name")
                or self.entry.get("created_by_name")
                or "Sistem Operat\u00f6r\u00fc (Admin)"
            )
            timestamp = str(
                self.entry.get("timestamp")
                or self.entry.get("created_at")
                or self.entry.get("updated_at")
                or ""
            )
            sections.append(
                "<hr>"
                "<table width='100%'><tr>"
                f"<td>\u0130\u015flem Yetkilisi: {escape(operator)}</td>"
                f"<td align='right'>Zaman Damgas\u0131: {escape(timestamp)}</td>"
                "</tr></table>"
            )
            self.txt_desc.setHtml(
                "<style>p { margin-bottom: 0px; } hr { margin-top: 0px; margin-bottom: 0px; }</style>"
                + "".join(sections)
            )
            self.desc_group.setVisible(True)
            line_count = max(1, len(description_text.splitlines()))
            self.txt_desc.setMinimumHeight(min(360, max(220, 70 + line_count * 19)))
        else:
            self.txt_desc.setPlainText("A\u00e7\u0131klama veya i\u015flem notu kayd\u0131 bulunmuyor.")
            self.desc_group.setVisible(True)

        # If no items are parsed, hide the empty items table
        if not parsed:
            self.items_table.setRowCount(0)
            self.items_table.setVisible(True)

        self.items_table.setVisible(True)
        amount_try = self.entry.get("amount_try", None)
        try:
            amount_try = float(amount_try) if amount_try is not None else None
        except Exception:
            amount_try = None
        if amount_try and len(parsed) == 1 and len(parsed[0]) == 3:
            name, qty, price = parsed[0]
            if not price:
                parsed[0] = (name, qty, CurrencyHelper.format_try_for_display(amount_try, db=self.db, include_try_reference=False))

        self.items_count.setText(f"Toplam {len(parsed)} Kalem")
        currency = str(self.entry.get("currency") or "TRY").upper()
        total_value = (
            float(self.entry.get("amount") or 0)
            if currency != "TRY"
            else float(amount_try or self.entry.get("amount") or 0)
        )
        vat_value = float(self.entry.get("vat_amount") or self.entry.get("tax_amount") or 0)
        if not vat_value and total_value > 0:
            try:
                vat_rate = float(self.entry.get("vat_rate") or 20.0)
            except (TypeError, ValueError):
                vat_rate = 20.0
            vat_value = total_value * vat_rate / (100.0 + vat_rate)
        self.vat_total.setText(
            f"KDV (%20 Dahil)\n{CurrencyHelper.format_amount(vat_value, db=self.db, currency_code=currency)}"
        )
        self.grand_total.setText(
            f"Genel Toplam\n{CurrencyHelper.format_amount(total_value, db=self.db, currency_code=currency)}"
        )

        self.items_table.setRowCount(0)
        self.items_table.setUpdatesEnabled(False)
        self.items_table.setSortingEnabled(False)
        for i, row_data in enumerate(parsed):
            if len(row_data) >= 4:
                name, qty, unit_price, price = row_data[:4]
            else:
                name, qty, price = row_data[:3]
                unit_price = "\u2014"
            self.items_table.insertRow(i)
            self.items_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.items_table.setItem(i, 1, QTableWidgetItem(str(name)))
            self.items_table.setItem(i, 2, QTableWidgetItem(str(qty)))
            self.items_table.setItem(i, 3, QTableWidgetItem(str(unit_price)))
            self.items_table.setItem(i, 4, QTableWidgetItem(str(price)))
            for column in (2, 3, 4):
                item = self.items_table.item(i, column)
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                    if column == 2
                    else Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                item_font = QFont("JetBrains Mono", 13)
                item_font.setBold(column == 4)
                item.setFont(item_font)
        self.items_table.setUpdatesEnabled(True)
        self.items_table.setSortingEnabled(True)

        self.items_table.resizeRowsToContents()
        for row in range(self.items_table.rowCount()):
            self.items_table.setRowHeight(
                row, max(71, self.items_table.rowHeight(row))
            )
        self.items_table.horizontalHeader().setMinimumHeight(51)
        header_h = self.items_table.horizontalHeader().height()
        rows_h = sum(self.items_table.rowHeight(r) for r in range(self.items_table.rowCount()))
        extra = 0
        desired_table_height = header_h + rows_h + extra
        table_height = min(420, desired_table_height)
        self.items_table.setFixedHeight(table_height)
        self.items_table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
            if desired_table_height > table_height
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        screen = QApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QApplication.primaryScreen()
        max_height = int(screen.availableGeometry().height() * 0.92) if screen else 900
        self.resize(1440, min(max_height, 1040))

    def open_service_form(self):
        tracking_no = self._resolve_tracking_no()
        if not tracking_no:
            show_warning(self, "Takip numarası bulunamadı.")
            return
        try:
            main_window = self.window()
            if main_window and hasattr(main_window, "open_service_form"):
                main_window.open_service_form(tracking_no)
                return
            show_warning(self, "Servis formu penceresi açılamadı.")
        except Exception as e:
            show_error(self, f"Servis formu açılamadı: {e}")
