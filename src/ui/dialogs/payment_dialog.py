# -*- coding: utf-8 -*-

from PyQt6.QtCore import QDate, QSize, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.design_system import DesignTokens
from src.utils.tax_settings import TaxSettings
from src.ui.widgets.navigation_glyph import navigation_icon



class ModernPaymentDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, parent, db, customer):
        super().__init__(title="Tahsilat Al", parent=parent, width=960, height=900)
        self.set_wheel_scroll_enabled(True)
        self.db = db
        self.customer = self._normalize_customer(customer)
        self.drag_pos = None
        self.selected_currency = CurrencyHelper.get_code(db)
        self.selected_exchange_rate = 1.0
        self.selected_method = "Nakit"
        self.balance_buttons = {}
        self.method_buttons = {}
        self.customer_balances = {}
        self.reference_tracking_no = None
        self.reference_desc = None
        self.debt_items = []  # List of debt widgets
        self.selected_debts = set()  # Set of selected debt IDs
        self._debt_selection_initialized = False

        self.set_footer_visible(False)

        self._build_ui()
        self._configure_payment_header()
        self._load_balances()
        self._load_debt_items()
        # En yüksek borçlu (negatif bakiyeli) para birimini otomatik seç
        best_currency = CurrencyHelper.get_code(self.db)
        best_debt = 0.0
        for code in ("TRY", "USD", "EUR"):
            bal = float(self.customer_balances.get(code, 0.0) or 0.0)
            if bal < 0 and abs(bal) > best_debt:
                best_debt = abs(bal)
                best_currency = code
        self._apply_selected_currency(best_currency)
        self._apply_selected_method("Nakit")

    def _configure_payment_header(self):
        """Put customer identity and live exchange rates in the dialog chrome."""
        header_layout = self.header.layout()
        header_layout.setContentsMargins(16, 0, 14, 0)
        if hasattr(self, "logo_label"):
            self.logo_label.setFixedSize(30, 30)

        identity = QWidget(self.header)
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(1)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title = QLabel("Tahsilat Al")
        title.setStyleSheet(theme_qss("font-size: 14px; font-weight: 900; color: @text;"))
        brand = QLabel("AYEC FINTECH v2.4")
        brand.setStyleSheet(theme_qss(
            "font-size: 8px; font-weight: 800; color: @finance_breadcrumb_active; "
            "background: @finance_active_bg; border: 1px solid @finance_outline; "
            "border-radius: 3px; padding: 2px 5px;"
        ))
        title_row.addWidget(title)
        title_row.addWidget(brand)
        title_row.addStretch(1)

        person = QLabel("{}  \u2022  {}".format(
            self.customer.get("name", ""), self.customer.get("phone", "") or "-"
        ))
        person.setStyleSheet(theme_qss("font-size: 10px; color: @text_muted;"))
        identity_layout.addLayout(title_row)
        identity_layout.addWidget(person)

        header_layout.removeWidget(self.lbl_title)
        self.lbl_title.hide()
        header_layout.insertWidget(2, identity)

        try:
            usd_rate = ExchangeRateManager.get_current_rate(self.db, "USD") or 0
            eur_rate = ExchangeRateManager.get_current_rate(self.db, "EUR") or 0
            rates_text = "USD: {:,.4f}  |  EUR: {:,.2f} TL".format(usd_rate, eur_rate)
        except Exception:
            rates_text = "USD / EUR"
        rates = QLabel(rates_text)
        rates.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rates.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 9px; color: @text_muted; "
            "background: @surface; border: 1px solid @border; border-radius: 8px; padding: 7px 10px;"
        ))
        rates.setFixedSize(216, 42)
        header_layout.insertWidget(4, rates)

        window_controls = QWidget(self.header)
        controls_layout = QHBoxLayout(window_controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(2)
        for label, standard_icon, slot in (
            ("Minimize", QStyle.StandardPixmap.SP_TitleBarMinButton, lambda: self.showMinimized()),
            ("Maximize", QStyle.StandardPixmap.SP_TitleBarMaxButton, self._toggle_dialog_maximized),
        ):
            control = QPushButton()
            control.setIcon(self.style().standardIcon(standard_icon))
            control.setFixedSize(22, 22)
            control.setCursor(Qt.CursorShape.PointingHandCursor)
            control.setAccessibleName(label)
            control.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; color: @text_muted; border: 1px solid @border; "
                "border-radius: 4px; font-size: 11px; } QPushButton:hover { color: @accent; border-color: @accent; }"
            ))
            control.clicked.connect(lambda _=False, action=slot: action())
            controls_layout.addWidget(control)
        header_layout.insertWidget(5, window_controls)
        self.header.setFixedHeight(62)

    def _toggle_dialog_maximized(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _normalize_customer(self, customer):
        if customer is None:
            return {}
        if isinstance(customer, dict):
            return customer
        try:
            return {key: customer[key] for key in customer.keys()}
        except Exception:
            pass
        if isinstance(customer, (list, tuple)):
            return {
                "id": customer[0] if len(customer) > 0 else None,
                "name": customer[1] if len(customer) > 1 else "",
                "phone": customer[2] if len(customer) > 2 else "",
            }
        return {}

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None
        super().mouseReleaseEvent(event)

    def _build_ui(self):
        root = self.content_layout
        root.setContentsMargins(10, 8, 10, 10)
        root.setSpacing(0)

        card = QFrame()
        card.setObjectName("PaymentCard")
        card.setStyleSheet(
            theme_qss(
                """
                QFrame#PaymentCard {
                    background: @surface;
                    border: 1px solid @border;
                    border-radius: 18px;
                }
                """
            )
        )
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 70))
        card.setGraphicsEffect(shadow)
        root.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(9)

        content_row = QHBoxLayout()
        content_row.setSpacing(34)

        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left_col = QVBoxLayout(left_panel)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(8)

        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_col = QVBoxLayout(right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(8)
        right_col.setAlignment(Qt.AlignmentFlag.AlignTop)

        content_row.addWidget(left_panel, 1)
        content_row.addWidget(right_panel, 1)
        layout.addLayout(content_row, 1)

        currencies_title = QLabel("Para Birimi Seçimi")
        currencies_title.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(currencies_title)

        self.currency_cards_layout = QGridLayout()
        self.currency_cards_layout.setHorizontalSpacing(8)
        self.currency_cards_layout.setVerticalSpacing(8)
        for column in range(3):
            self.currency_cards_layout.setColumnStretch(column, 1)
        left_col.addLayout(self.currency_cards_layout)

        # Sol panel - Ödeme tutarı ve yöntemi
        amount_title = QLabel("Tahsilat Tutarı")
        amount_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted; background: transparent;")
        )
        left_col.addWidget(amount_title)
        left_col.addSpacing(16)

        amount_field = QFrame()
        amount_field.setObjectName("PaymentAmountField")
        amount_field.setFixedHeight(46)
        amount_field.setStyleSheet(theme_qss(
            "QFrame#PaymentAmountField { background: @surface; border: 2px solid @accent; border-radius: 12px; }"
        ))
        amount_field_layout = QHBoxLayout(amount_field)
        amount_field_layout.setContentsMargins(12, 0, 12, 0)
        amount_field_layout.setSpacing(8)

        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0,00")
        self.inp_amount.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.inp_amount.setFixedHeight(38)
        self.inp_amount.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    background: transparent;
                    border: none;
                    border-radius: 0;
                    padding: 0;
                    color: @text;
                    font-family: 'JetBrains Mono';
                    font-size: 18px;
                    font-weight: 800;
                }
                """
            )
        )
        self.inp_amount.textChanged.connect(self._on_amount_changed)
        amount_field_layout.addWidget(self.inp_amount, 1)
        self.lbl_amount_currency = QLabel()
        self.lbl_amount_currency.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_amount_currency.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 800; "
            "color: @finance_breadcrumb_active; background: transparent; border: none;"
        ))
        amount_field_layout.addWidget(self.lbl_amount_currency)
        left_col.addWidget(amount_field)

        quick_amounts = QHBoxLayout()
        quick_amounts.setSpacing(6)
        quick_label = QLabel("H\u0131zl\u0131 Ekle:")
        quick_label.setStyleSheet(theme_qss("font-size: 9px; color: @text_muted;"))
        quick_amounts.addWidget(quick_label)
        self.quick_amount_buttons = {}
        for amount in (10, 20, 50, 100):
            button = QPushButton("+{}".format(amount))
            button.setFixedHeight(24)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text_muted; "
                "border: 1px solid @border; border-radius: 5px; padding: 0 7px; font-size: 9px; }"
                "QPushButton:hover { color: @accent; border-color: @accent; }"
            ))
            button.clicked.connect(lambda _=False, value=amount: self._add_quick_amount(value))
            quick_amounts.addWidget(button)
            self.quick_amount_buttons[amount] = button
        quick_amounts.addStretch(1)
        self.btn_select_all_debts = QPushButton("T\u00fcm\u00fcn\u00fc Kapat")
        self.btn_select_all_debts.setFixedHeight(24)
        self.btn_select_all_debts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all_debts.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_active_bg; color: @finance_breadcrumb_active; "
            "border: 1px solid @finance_outline; border-radius: 5px; padding: 0 7px; font-size: 9px; }"
        ))
        self.btn_select_all_debts.clicked.connect(self._select_all_debts)
        quick_amounts.addWidget(self.btn_select_all_debts)
        left_col.addLayout(quick_amounts)
        left_col.addSpacing(16)

        method_title = QLabel("Ödeme Yöntemi")
        method_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(method_title)

        self.method_row = QHBoxLayout()
        self.method_row.setSpacing(6)
        left_col.addLayout(self.method_row)
        self._build_method_cards()
        left_col.addSpacing(8)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(4)
        rate_title = self._label("Kur")
        rate_title.setFixedHeight(12)
        date_title = self._label("Tarih")
        date_title.setFixedHeight(12)
        form.addWidget(rate_title, 0, 0)
        form.addWidget(date_title, 0, 1)

        self.lbl_rate = QLabel("1,0000")
        self.lbl_rate.setFixedHeight(46)
        self.lbl_rate.setStyleSheet(
            theme_qss(
                """
                QLabel {
                    background: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 12px;
                    padding: 0 14px;
                    font-size: 13px;
                    font-weight: 700;
                }
                """
            )
        )

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setFixedHeight(40)
        self.lbl_rate.setFixedHeight(40)
        self.date_edit.setStyleSheet(theme_qss(self._date_qss()))

        form.addWidget(self.lbl_rate, 1, 0)
        form.addWidget(self.date_edit, 1, 1)
        notes_title = QLabel("İşlem Notu")
        notes_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
        )
        notes_title.setFixedHeight(12)

        self.inp_notes = QTextEdit()
        self.inp_notes.setPlaceholderText(
            "İşlemle ilgili notunuzu buraya ekleyebilirsiniz..."
        )
        self.inp_notes.setFixedHeight(38)
        self.inp_notes.setStyleSheet(
            theme_qss(
                """
                QTextEdit {
                    background: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 8px;
                    padding: 8px;
                    color: @text;
                    font-size: 13px;
                }
                QTextEdit:focus {
                    border-color: @accent;
                    background: @surface;
                }
                """
            )
        )
        form_notes = QVBoxLayout()
        form_notes.setContentsMargins(0, 0, 0, 0)
        form_notes.setSpacing(2)
        form_notes.addLayout(form)
        form_notes.addWidget(notes_title)
        form_notes.addWidget(self.inp_notes)
        form_notes.addSpacing(10)
        left_col.addLayout(form_notes)

        debt_header = QHBoxLayout()
        debt_section_title = QLabel("BOR\u00c7 KALEMLER\u0130 & FATURA E\u015eLE\u015eT\u0130RME")
        debt_section_title.setStyleSheet(
            theme_qss("font-size: 13px; font-weight: 900; color: @text_muted;")
        )
        self.lbl_debt_count = QLabel("0 Kalem Bulundu")
        self.lbl_debt_count.setStyleSheet(
            theme_qss("font-family: 'JetBrains Mono'; font-size: 11px; color: @text_muted;")
        )
        debt_header.addWidget(debt_section_title)
        debt_header.addStretch(1)
        debt_header.addWidget(self.lbl_debt_count)
        right_col.addLayout(debt_header)

        self.debt_scroll = QScrollArea()
        self.debt_scroll.setWidgetResizable(True)
        self.debt_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.debt_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.debt_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.debt_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.debt_scroll.setFixedHeight(146)
        self.debt_scroll.setStyleSheet(
            theme_qss("""
            QScrollArea { background: @surface_alt; border: 1px solid @border; border-radius: 18px; }
            QScrollBar:vertical {
                width: 10px;
                background: transparent;
                margin: 8px 6px 8px 0;
            }
            QScrollBar::handle:vertical {
                background: @border;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover { background: @text_muted; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        )

        self.debt_container = QWidget()
        self.debt_layout = QVBoxLayout(self.debt_container)
        self.debt_layout.setContentsMargins(20, 0, 0, 0)
        self.debt_layout.setSpacing(0)
        self.debt_layout.addStretch()
        self.debt_scroll.setWidget(self.debt_container)
        right_col.addWidget(self.debt_scroll)
        right_col.addSpacing(215)

        self.lbl_selected_total = QLabel("Seçili Toplam: 0,00")
        self.lbl_selected_total.setStyleSheet(
            theme_qss(
                "font-family: 'JetBrains Mono'; font-size: 10px; font-weight: 700; color: @text_muted; "
                "background: @surface; border-top: 1px solid @border; padding: 4px 8px;"
            )
        )
        self.lbl_selected_total.setFixedHeight(24)
        self.lbl_selected_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        vat_frame = QFrame()
        vat_frame.setObjectName("PaymentVatSummary")
        vat_frame.setFixedHeight(118)
        vat_frame.setStyleSheet(
            theme_qss("""
            QFrame#PaymentVatSummary {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 0;
            }
        """)
        )
        vat_layout = QVBoxLayout(vat_frame)
        vat_layout.setSpacing(4)
        vat_layout.setContentsMargins(8, 8, 8, 8)

        vat_header = QHBoxLayout()
        vat_header.addWidget(self._label("KDV Da\u011f\u0131l\u0131m\u0131"))
        vat_header.addStretch()

        self.combo_vat_rate = QComboBox()
        self.combo_vat_rate.addItems(["%0", "%10", "%20", "%18", "%8", "%1", "KDV Hari\u00e7"])
        default_vat_text = TaxSettings.combo_text(self.db)
        if self.combo_vat_rate.findText(default_vat_text) < 0:
            self.combo_vat_rate.insertItem(0, default_vat_text)
        self.combo_vat_rate.setCurrentText(default_vat_text)
        self.combo_vat_rate.setStyleSheet(theme_qss(self._combo_qss()))
        self.combo_vat_rate.currentTextChanged.connect(self._calculate_vat)
        self.combo_vat_rate.setFixedSize(104, 24)
        vat_header.addWidget(self.combo_vat_rate)
        vat_layout.addLayout(vat_header)

        vat_grid = QGridLayout()
        vat_grid.setHorizontalSpacing(8)
        vat_grid.setVerticalSpacing(4)

        vat_grid.addWidget(self._label("Net Tutar"), 0, 0)
        self.lbl_net_amount = QLabel("0,00")
        self.lbl_net_amount.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.lbl_net_amount.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 700; color: @text; background-color: transparent;")
        )
        vat_grid.addWidget(self.lbl_net_amount, 1, 0)

        vat_grid.addWidget(self._label("KDV Tutarı"), 0, 1)
        self.lbl_vat_amount = QLabel("0,00")
        self.lbl_vat_amount.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.lbl_vat_amount.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 700; color: @warning; background-color: transparent;")
        )
        vat_grid.addWidget(self.lbl_vat_amount, 1, 1)

        vat_grid.addWidget(self._label("GENEL TOPLAM"), 0, 2)
        self.lbl_total_with_vat = QLabel("0,00")
        self.lbl_total_with_vat.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.lbl_total_with_vat.setStyleSheet(
            theme_qss("font-size: 14px; font-weight: 900; color: @success; background-color: transparent;")
        )
        vat_grid.addWidget(self.lbl_total_with_vat, 1, 2)

        vat_layout.addLayout(vat_grid)
        right_col.addWidget(vat_frame)

        payment_preview = QFrame()
        payment_preview.setFixedHeight(58)
        payment_preview.setObjectName("PaymentBalancePreview")
        payment_preview.setStyleSheet(theme_qss(
            "QFrame#PaymentBalancePreview { background: @surface_alt; border: 1px solid @border; border-radius: 8px; }"
        ))
        preview_layout = QHBoxLayout(payment_preview)
        preview_layout.setContentsMargins(10, 6, 10, 6)
        preview_layout.setSpacing(8)
        preview_text = QVBoxLayout()
        preview_text.setContentsMargins(0, 0, 0, 0)
        preview_text.setSpacing(1)
        preview_title = QLabel("Tahsil Edilecek Net Bakiye")
        preview_title.setStyleSheet(theme_qss("font-size: 9px; font-weight: 700; color: @text_muted; background: transparent; border: none;"))
        self.lbl_net_balance_preview = QLabel("0,00")
        self.lbl_net_balance_preview.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 16px; font-weight: 900; color: @text; background: transparent; border: none;"
        ))
        preview_text.addWidget(preview_title)
        preview_text.addWidget(self.lbl_net_balance_preview)
        preview_layout.addLayout(preview_text)
        preview_layout.addStretch(1)
        self.lbl_try_equivalent = QLabel("0,00 TL")
        self.lbl_try_equivalent.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_try_equivalent.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 11px; font-weight: 800; color: @success; background: transparent; border: none;"
        ))
        preview_layout.addWidget(self.lbl_try_equivalent)
        right_col.addWidget(payment_preview)

        # Taksit Bölümü
        self.installment_frame = QFrame()
        self.installment_frame.setStyleSheet(
            theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 12px;
            }
        """)
        )
        inst_layout = QVBoxLayout(self.installment_frame)
        inst_layout.setSpacing(10)
        inst_layout.setContentsMargins(15, 15, 15, 15)

        inst_header = QHBoxLayout()
        self.chk_installment = QCheckBox("Taksitli Ödeme")
        self.chk_installment.setStyleSheet(
            theme_qss("font-size: 13px; font-weight: 700; color: @text; background: transparent;")
        )
        self.chk_installment.toggled.connect(self._toggle_installment)
        inst_header.addWidget(self.chk_installment)
        inst_header.addStretch()
        inst_layout.addLayout(inst_header)

        inst_form = QGridLayout()
        inst_form.setHorizontalSpacing(12)
        inst_form.setVerticalSpacing(8)

        inst_form.addWidget(self._label("Peşinat"), 0, 0)
        self.inp_down_payment = QLineEdit()
        self.inp_down_payment.setPlaceholderText("0,00")
        self.inp_down_payment.setEnabled(False)
        self.inp_down_payment.setStyleSheet(theme_qss(self._input_qss()))
        self.inp_down_payment.textChanged.connect(self._calculate_installment)
        inst_form.addWidget(self.inp_down_payment, 1, 0)

        inst_form.addWidget(self._label("Taksit Sayısı"), 0, 1)
        self.spin_installment = QSpinBox()
        self.spin_installment.setRange(2, 36)
        self.spin_installment.setValue(3)
        self.spin_installment.setEnabled(False)
        DesignTokens.apply_spinbox_styles(self.spin_installment)
        self.spin_installment.valueChanged.connect(self._calculate_installment)
        inst_form.addWidget(self.spin_installment, 1, 1)

        inst_layout.addLayout(inst_form)

        self.lbl_monthly = QLabel("Aylık Taksit: -")
        self.lbl_monthly.setStyleSheet(
            theme_qss("font-size: 14px; font-weight: 800; color: @accent;")
        )
        self.lbl_monthly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_layout.addWidget(self.lbl_monthly)

        left_col.addWidget(self.installment_frame)
        left_col.addStretch(1)

        # Makbuz yazdırma seçeneği
        self.chk_print_receipt = QCheckBox("Ödeme makbuzu yazdır")
        self.chk_print_receipt.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 600; color: @text;")
        )
        self.chk_print_receipt.setChecked(True)
        right_col.addWidget(self.chk_print_receipt)

        # Buttons
        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setFixedHeight(52)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: @surface_alt;
                    color: @text_muted;
                    border: none;
                    border-radius: 14px;
                    font-size: 15px;
                    font-weight: 800;
                }
                QPushButton:hover {
                    background: @border;
                    color: @text;
                }
                """
            )
        )
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Tahsilatı Tamamla")
        btn_save.setFixedHeight(52)
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: @success;
                    color: @selection_text;
                    border: none;
                    border-radius: 14px;
                    font-size: 16px;
                    font-weight: 900;
                }
                QPushButton:hover {
                    background: @accent;
                }
                """
            )
        )
        btn_save.clicked.connect(self.handle_save)

        buttons.addWidget(btn_cancel, 1)
        buttons.addWidget(btn_save, 2)
        layout.addLayout(buttons)

    def _label(self, text):
        lbl = QLabel(text)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        lbl.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted; background-color: transparent;")
        )
        return lbl

    def _date_qss(self):
        return """
            QDateEdit {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 0 14px;
                font-size: 13px;
                font-weight: 700;
            }
            QDateEdit:focus {
                border-color: @accent;
                background: @surface;
            }
        """

    def _build_currency_cards(self):
        """Show supported currencies in a single reference-aligned card row."""
        while self.currency_cards_layout.count():
            item = self.currency_cards_layout.takeAt(0)
            self._dispose_layout_item(item)

        for idx, code in enumerate(("USD", "EUR", "TRY")):
            self.currency_cards_layout.addWidget(
                self._create_currency_card(code), 0, idx
            )

    def _create_currency_card(self, code):
        """Tek para birimi kartı oluştur"""
        balance = float(self.customer_balances.get(code, 0.0) or 0.0)

        card = QFrame()
        card.setObjectName(f"CurrencyCard_{code}")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setFixedHeight(74)
        card.setMinimumWidth(0)
        card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        # Borç durumuna göre renk
        has_debt = balance < -0.01
        is_selected = code == self.selected_currency

        # Stil belirle
        if is_selected:
            bg_color = "@surface"
            text_color = "@text"
            border_color = "@accent"
        else:
            bg_color = "@surface_alt"
            text_color = "@text"
            border_color = "@warning" if has_debt else "@border"

        card.setStyleSheet(
            theme_qss(f"""
            QFrame#CurrencyCard_{code} {{
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 16px;
            }}
            QFrame#CurrencyCard_{code}:hover {{
                border-color: @accent;
                background: @surface;
            }}
        """)
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(1)

        # Para birimi adı
        lbl_code = QLabel(code)
        lbl_code.setStyleSheet(
            theme_qss(f"""
            background: transparent;
            border: none;
            font-size: 10px;
            font-weight: 800;
            color: {text_color};
        """)
        )
        layout.addWidget(lbl_code)

        # Bakiye tutarı
        display_balance = abs(balance)
        lbl_amount = QLabel(
            CurrencyHelper.format_amount(
                display_balance, currency_code=code
            )
        )
        lbl_amount.setStyleSheet(
            theme_qss(f"""
            background: transparent;
            border: none;
            font-size: 16px;
            font-weight: 900;
            color: {text_color};
        """)
        )
        layout.addWidget(lbl_amount)

        # Durum metni
        if abs(balance) < 0.01:
            status_text = "Bakiye Kapalı"
        elif balance < 0:
            status_text = f"Bor\u00e7: {CurrencyHelper.format_amount(display_balance, currency_code=code)}"
        else:
            status_text = f"Fazla Ödeme"

        lbl_status = QLabel(status_text)
        lbl_status.setStyleSheet(
            theme_qss(f"""
            background: transparent;
            border: none;
            font-size: 11px;
            font-weight: 600;
            color: {"@danger" if has_debt else "@text_muted"};
        """)
        )
        layout.addWidget(lbl_status)

        def select_card(_event, currency_code=code):
            self._apply_selected_currency(currency_code)

        card.mousePressEvent = select_card

        return card

    def _build_method_cards(self):
        methods = ["Nakit", "Kredi Kartı", "Havale / EFT", "Çek / Senet"]
        icons = {
            "Nakit": "money",
            "Kredi Kart\u0131": "card",
            "Havale / EFT": "bank",
            "\u00c7ek / Senet": "document",
        }
        self._method_icon_kinds = icons
        for method in methods:
            btn = QToolButton()
            btn.setText(method)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(16, 16))
            btn.setIcon(navigation_icon(icons[method], 16, "text_muted"))
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(54)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(
                lambda _=False, value=method: self._apply_selected_method(value)
            )
            self.method_buttons[method] = btn
            self.method_row.addWidget(btn, 1)

    def _load_balances(self):
        try:
            self.customer_balances = (
                self.db.get_customer_all_balances(self.customer.get("id")) or {}
            )
        except Exception:
            self.customer_balances = {}

        if not self.customer_balances:
            self.customer_balances = {"TRY": 0.0, "USD": 0.0, "EUR": 0.0}

        self._build_currency_cards()

    def _load_debt_items(self):
        """Load outstanding amounts from the shared payment allocation query."""
        customer_id = self.customer.get("id")
        if not customer_id:
            return

        try:
            raw_items = self.db.get_unpaid_debts(customer_id) or []
            unique_items = []
            seen_ids = set()
            for debt in raw_items:
                debt_id = debt[0] if len(debt) > 0 else None
                if debt_id in seen_ids:
                    continue
                seen_ids.add(debt_id)
                unique_items.append(debt)
            self.debt_items = unique_items
            self.debt_items.sort(
                key=lambda debt: str(debt[5] or "") if len(debt) > 5 else ""
            )
            self._refresh_debt_list()
        except Exception as e:
            print(f"Borç kalemleri yüklenirken hata: {e}")
            self.debt_items = []

    def _refresh_debt_list(self):
        """Borç listesini güncelle - seçili para birimine göre filtrele"""
        while self.debt_layout.count():
            item = self.debt_layout.takeAt(0)
            self._dispose_layout_item(item)

        filtered_debts = []
        seen_ids = set()
        for debt in self.debt_items:
            debt_id = debt[0] if len(debt) > 0 else None
            debt_currency = str((debt[2] if len(debt) > 2 else "TRY") or "TRY").upper()
            if debt_currency != self.selected_currency:
                continue
            if debt_id in seen_ids:
                continue
            seen_ids.add(debt_id)
            filtered_debts.append(debt)

        if not self._debt_selection_initialized:
            self.selected_debts = {
                debt[0] for debt in filtered_debts if debt and debt[0] is not None
            }
            self._debt_selection_initialized = True

        if hasattr(self, "lbl_debt_count"):
            self.lbl_debt_count.setText("{} Kalem Bulundu".format(len(filtered_debts)))

        visible_debt_ids = {debt[0] for debt in filtered_debts}
        self.selected_debts = {
            debt_id for debt_id in self.selected_debts if debt_id in visible_debt_ids
        }

        table_header = QWidget()
        table_header.setObjectName("PaymentDebtTableHeader")
        table_header.setFixedHeight(26)
        table_header.setStyleSheet(theme_qss(
            "QWidget#PaymentDebtTableHeader { background: @surface; border-bottom: 1px solid @border; }"
        ))
        table_header_layout = QHBoxLayout(table_header)
        table_header_layout.setContentsMargins(6, 2, 6, 2)
        table_header_layout.setSpacing(6)
        for text, width, alignment in (
            ("Se\u00e7", 18, Qt.AlignmentFlag.AlignCenter),
            ("Tarih / Ref", 102, Qt.AlignmentFlag.AlignLeft),
        ):
            header_cell = QLabel(text)
            header_cell.setFixedWidth(width)
            header_cell.setAlignment(alignment | Qt.AlignmentFlag.AlignVCenter)
            header_cell.setStyleSheet(theme_qss(
                "font-size: 12px; font-weight: 800; color: @text_muted; background: transparent; border: none;"
            ))
            table_header_layout.addWidget(header_cell)
        description_header = QLabel("\u0130\u015flem / Hizmet Tan\u0131m\u0131")
        description_header.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text_muted; background: transparent; border: none;"
        ))
        table_header_layout.addWidget(description_header, 1)
        amount_header = QLabel("Tutar")
        amount_header.setFixedWidth(86)
        amount_header.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        amount_header.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text_muted; background: transparent; border: none;"
        ))
        table_header_layout.addWidget(amount_header)
        self.debt_layout.addWidget(table_header)

        if not filtered_debts:
            no_debt_lbl = QLabel("Açık borç bulunmamaktadır.")
            no_debt_lbl.setStyleSheet(
                theme_qss("font-size: 13px; color: @text_muted; padding: 20px;")
            )
            no_debt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.debt_layout.addWidget(no_debt_lbl)
        else:
            for debt in filtered_debts:
                debt_widget = self._create_debt_item_widget(debt)
                self.debt_layout.addWidget(debt_widget)

        self.debt_layout.addWidget(self.lbl_selected_total)
        self.debt_layout.addStretch()
        self._update_selected_total()
        self.debt_container.adjustSize()
        self.debt_container.updateGeometry()
        self.debt_scroll.viewport().update()
        QApplication.processEvents()

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            self._dispose_layout_item(item)

    def _dispose_layout_item(self, item):
        if item is None:
            return
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
            return
        child_layout = item.layout()
        if child_layout is not None:
            self._clear_layout(child_layout)

    def _create_debt_item_widget(self, debt):
        """Tek borç kalemi widget'ı oluştur (açılır/kapanır)"""
        (
            debt_id,
            amount,
            currency,
            description,
            tracking_no,
            created_at,
            current_balance,
        ) = debt

        # Ana frame
        frame = QFrame()
        frame.setObjectName(f"DebtItem_{debt_id}")
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        frame.setStyleSheet(theme_qss(f"""
            QFrame#DebtItem_{debt_id} {{
                background: transparent;
                border: none;
                border-bottom: 1px solid @border;
                border-radius: 0;
            }}
            QFrame#DebtItem_{debt_id}:hover {{ background: @surface; }}
        """))

        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(6, 1, 6, 1)
        main_layout.setSpacing(0)

        # Üst satır - Checkbox + Özet bilgi
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 4, 0, 4)

        checkbox = QCheckBox()
        checkbox.setChecked(debt_id in self.selected_debts)
        checkbox.stateChanged.connect(
            lambda state, did=debt_id: self._on_debt_selected(did, state)
        )
        header_layout.addWidget(checkbox)

        date_ref = QWidget()
        date_ref_layout = QVBoxLayout(date_ref)
        date_ref_layout.setContentsMargins(0, 0, 0, 0)
        date_ref_layout.setSpacing(1)
        date_ref.setStyleSheet(theme_qss("background: transparent;"))
        date_text = str(created_at or "-")[:10]
        if len(date_text) == 10 and date_text[4] == "-":
            date_text = "{}.{}.{}".format(date_text[8:10], date_text[5:7], date_text[0:4])
        lbl_date = QLabel(date_text)
        lbl_date.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 12px; color: @text_muted; background: transparent;"
        ))
        lbl_ref = QLabel("#{}".format(tracking_no or "-"))
        lbl_ref.setStyleSheet(theme_qss(
            "font-family: 'JetBrains Mono'; font-size: 11px; color: @finance_breadcrumb_active; background: transparent;"
        ))
        date_ref_layout.addWidget(lbl_date)
        date_ref_layout.addWidget(lbl_ref)
        date_ref.setFixedWidth(102)
        header_layout.addWidget(date_ref)

        # Açıklama
        desc_text = description or "Borç Kaydı"
        if len(desc_text) > 56:
            desc_text = desc_text[:53] + "..."
        lbl_desc = QLabel(desc_text)
        lbl_desc.setStyleSheet(
            theme_qss("font-size: 13px; font-weight: 700; color: @text; background: transparent;")
        )
        lbl_desc.setWordWrap(True)
        header_layout.addWidget(lbl_desc, 1)

        remaining_amount = self._get_debt_remaining_amount(debt)
        display_amount = CurrencyHelper.convert_amount(
            self.db,
            remaining_amount,
            from_currency=currency,
            to_currency=self.selected_currency,
        )
        lbl_amount = QLabel(
            CurrencyHelper.format_amount(
                display_amount, currency_code=self.selected_currency
            )
        )
        lbl_amount.setStyleSheet(
            theme_qss("font-family: 'JetBrains Mono'; font-size: 13px; font-weight: 800; color: @text; background: transparent;")
        )
        lbl_amount.setFixedWidth(86)
        lbl_amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Detay butonu
        btn_toggle = QPushButton("▼")
        btn_toggle.setFixedSize(18, 18)
        btn_toggle.setStyleSheet(
            theme_qss("""
            QPushButton {
                background: transparent;
                border: none;
                color: @text_muted;
                font-size: 12px;
            }
            QPushButton:hover {
                color: @accent;
            }
        """)
        )
        header_layout.addWidget(btn_toggle)
        header_layout.addWidget(lbl_amount)

        main_layout.addLayout(header_layout)

        # Detay bölümü (başlangıçta gizli)
        details_widget = QWidget()
        details_widget.setVisible(False)
        details_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        details_widget.setMaximumHeight(0)
        details_widget.setStyleSheet(
            theme_qss("background: transparent; border: none;")
        )
        details_layout = QGridLayout(details_widget)
        details_layout.setContentsMargins(30, 6, 0, 2)
        details_layout.setHorizontalSpacing(14)
        details_layout.setVerticalSpacing(6)

        debt_context = self._get_debt_context(tracking_no, description)

        row = 0
        if debt_context.get("service_label"):
            details_layout.addWidget(self._detail_label("Is"), row, 0)
            details_layout.addWidget(
                self._detail_value(debt_context.get("service_label")), row, 1
            )
            row += 1

        if debt_context.get("work_summary"):
            details_layout.addWidget(self._detail_label("Detay"), row, 0)
            details_layout.addWidget(
                self._detail_value(debt_context.get("work_summary"), muted=True), row, 1
            )
            row += 1

        if debt_context.get("parts_summary"):
            details_layout.addWidget(self._detail_label("Parcalar"), row, 0)
            details_layout.addWidget(
                self._detail_value(debt_context.get("parts_summary"), muted=True),
                row,
                1,
            )
            row += 1

        if tracking_no:
            details_layout.addWidget(self._detail_label("Takip No"), row, 0)
            details_layout.addWidget(self._detail_value(tracking_no), row, 1)
            row += 1

        details_layout.addWidget(self._detail_label("Tarih"), row, 0)
        details_layout.addWidget(
            self._detail_value(created_at[:10] if created_at else "-"), row, 1
        )
        row += 1

        details_layout.addWidget(self._detail_label("Borclanan"), row, 0)
        details_layout.addWidget(
            self._detail_value(
                CurrencyHelper.format_amount(float(amount or 0), currency_code=currency)
            ),
            row,
            1,
        )
        row += 1

        details_layout.addWidget(self._detail_label("Kalan"), row, 0)
        remaining_source = self._get_debt_remaining_amount(debt)
        remaining_display = CurrencyHelper.convert_amount(
            self.db,
            remaining_source,
            from_currency=currency,
            to_currency=self.selected_currency,
        )
        details_layout.addWidget(
            self._detail_value(
                CurrencyHelper.format_amount(
                    remaining_display, currency_code=self.selected_currency
                )
            ),
            row,
            1,
        )

        main_layout.addWidget(details_widget)

        # Toggle fonksiyonu
        def toggle_details():
            is_visible = details_widget.isVisible()
            show_details = not is_visible
            details_widget.setVisible(show_details)
            details_widget.setMaximumHeight(
                details_widget.sizeHint().height() if show_details else 0
            )
            btn_toggle.setText("\u25b2" if show_details else "\u25bc")

            details_widget.updateGeometry()
            frame.adjustSize()
            frame.updateGeometry()
            self.debt_container.adjustSize()
            self.debt_container.updateGeometry()
            self.debt_scroll.viewport().update()
            if show_details:
                self.debt_scroll.ensureWidgetVisible(frame, 0, 24)
            QApplication.processEvents()

        btn_toggle.clicked.connect(toggle_details)

        return frame

    def _get_debt_remaining_amount(self, debt):
        """Borç kaleminde ödenmesi gereken güncel kalan tutarı döndür."""
        try:
            amount = float((debt[1] if len(debt) > 1 else 0) or 0)
            current_balance = debt[6] if len(debt) > 6 else None
            if current_balance is None:
                return max(0.0, amount)
            current_balance = float(current_balance or 0)
            return max(0.0, abs(current_balance) if current_balance < 0 else 0.0)
        except Exception:
            return 0.0

    def _detail_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(
            theme_qss(
                "font-size: 11px; font-weight: 700; color: @text_muted; background: transparent; border: none;"
            )
        )
        return lbl

    def _detail_value(self, text, muted=False):
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        color_token = "@text_muted" if muted else "@text"
        lbl.setStyleSheet(
            theme_qss(
                f"font-size: 12px; font-weight: 700; color: {color_token}; background: transparent; border: none; padding: 0;"
            )
        )
        return lbl

    def _get_debt_context(self, tracking_no, description):
        context = {
            "service_label": "",
            "work_summary": "",
            "parts_summary": "",
        }

        desc_text = str(description or "").strip()
        if desc_text:
            first_line = desc_text.split("|")[0].strip()
            if first_line:
                context["work_summary"] = first_line

        if not tracking_no:
            return context

        try:
            cur = self.db.conn.cursor()
            cur.execute(
                """
                SELECT device_brand, device_model, fault_description, repair_details
                FROM devices
                WHERE tracking_no=?
                LIMIT 1
                """,
                (tracking_no,),
            )
            row = cur.fetchone()
            if row:
                brand = str(row[0] or "").strip()
                model = str(row[1] or "").strip()
                fault = str(row[2] or "").strip()
                repair = str(row[3] or "").strip()
                context["service_label"] = " ".join(
                    part for part in (brand, model) if part
                ).strip()
                if repair:
                    context["work_summary"] = repair
                elif fault and not context["work_summary"]:
                    context["work_summary"] = fault
        except Exception:
            pass

        try:
            cur = self.db.conn.cursor()
            cur.execute(
                """
                SELECT part_name, COALESCE(quantity, 1)
                FROM used_parts
                WHERE tracking_no=?
                ORDER BY id ASC
                LIMIT 4
                """,
                (tracking_no,),
            )
            parts = []
            for part_name, qty in cur.fetchall() or []:
                pname = str(part_name or "").strip()
                if not pname:
                    continue
                try:
                    qty_val = int(float(qty or 1))
                except Exception:
                    qty_val = 1
                parts.append(f"{pname} x{qty_val}" if qty_val > 1 else pname)
            if parts:
                context["parts_summary"] = ", ".join(parts)
        except Exception:
            pass

        return context

    def _on_debt_selected(self, debt_id, state):
        """Borç seçimi değiştiğinde"""
        if state:
            self.selected_debts.add(debt_id)
        else:
            self.selected_debts.discard(debt_id)

        self._update_selected_total()

    def _update_selected_total(self):
        """Seçili borçların toplamını hesapla ve göster"""
        total = 0.0
        total_try = 0.0

        for debt in self.debt_items:
            debt_id, _amount, currency, _, _, _, _ = debt
            if debt_id in self.selected_debts:
                remaining_amount = self._get_debt_remaining_amount(debt)
                total += CurrencyHelper.convert_amount(
                    self.db,
                    remaining_amount,
                    from_currency=currency,
                    to_currency=self.selected_currency,
                )
                total_try += CurrencyHelper.convert_amount(
                    self.db,
                    remaining_amount,
                    from_currency=currency,
                    to_currency="TRY",
                )

        symbol = self._symbol(self.selected_currency)
        try_symbol = self._symbol("TRY")
        self.lbl_selected_total.setText(
            f"Se\u00e7ilen Kalemler Toplam\u0131: {total:,.2f} {symbol} "
            f"({total_try:,.2f} {try_symbol})"
        )

        if total > 0:
            self.inp_amount.setText(
                f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

    def _apply_selected_currency(self, currency):
        self.selected_currency = currency or CurrencyHelper.get_code(self.db)
        self.selected_exchange_rate = self._get_rate(self.selected_currency)
        if hasattr(self, "lbl_amount_currency"):
            self.lbl_amount_currency.setText(
                "{} {}".format(self._symbol(self.selected_currency), self.selected_currency)
            )
        self.lbl_rate.setText(
            f"{self.selected_exchange_rate:,.4f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )
        for amount, button in getattr(self, "quick_amount_buttons", {}).items():
            button.setText("+{} {}".format(amount, self._symbol(self.selected_currency)))

        # Kartları yeniden çiz
        self._build_currency_cards()

        # Borç listesini güncelle
        self._refresh_debt_list()
        self._update_selected_total()
        self._update_net_balance_preview()

    def _apply_selected_method(self, method):
        self.selected_method = method
        for name, button in self.method_buttons.items():
            is_active = name == self.selected_method
            button.setChecked(is_active)
            button.setIcon(navigation_icon(
                self._method_icon_kinds[name], 16,
                "selection_text" if is_active else "text_muted",
            ))
            button.setStyleSheet(
                theme_qss(
                    f"""
                    QToolButton {{
                        background: {"@accent" if is_active else "@surface_alt"};
                        color: {"@selection_text" if is_active else "@text"};
                        border: 1px solid {"@accent" if is_active else "@border"};
                        border-radius: 12px;
                        padding: 5px 4px;
                        font-size: 11px;
                        font-weight: 800;
                    }}
                    QToolButton:hover {{
                        border-color: @accent;
                        background: {"@accent" if is_active else "@surface"};
                    }}
                    """
                )
            )

    def _get_rate(self, currency):
        if currency == "TRY":
            return 1.0
        try:
            from src.utils.exchange_rate_manager import ExchangeRateManager

            rate = ExchangeRateManager.get_current_rate(self.db, currency, "selling")
            return float(rate or 1.0)
        except Exception:
            return 1.0

    def _symbol(self, currency):
        return CurrencyHelper.get_symbol(currency_code=currency)

    def _on_amount_changed(self):
        """Tutar değiştiğinde KDV hesapla"""
        self._calculate_vat()
        self._update_net_balance_preview()
        if self.chk_installment.isChecked():
            self._calculate_installment()

    def _update_net_balance_preview(self):
        if not hasattr(self, "lbl_net_balance_preview"):
            return
        amount_text = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            amount = float(amount_text or 0.0)
        except Exception:
            amount = 0.0
        self.lbl_net_balance_preview.setText(
            CurrencyHelper.format_amount(amount, currency_code=self.selected_currency)
        )
        try:
            equivalent = amount * float(self.selected_exchange_rate or 1.0)
        except Exception:
            equivalent = amount
        self.lbl_try_equivalent.setText(
            "{:,.2f} TL".format(equivalent).replace(",", "X").replace(".", ",").replace("X", ".")
        )

    def _add_quick_amount(self, increment):
        amount_text = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            amount = float(amount_text or 0.0) + float(increment)
        except Exception:
            amount = float(increment)
        self.inp_amount.setText(
            "{:,.2f}".format(amount).replace(",", "X").replace(".", ",").replace("X", ".")
        )

    def _select_all_debts(self):
        checkboxes = self.debt_container.findChildren(QCheckBox)
        for checkbox in checkboxes:
            checkbox.setChecked(True)

    def handle_save(self):
        amount_str = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            amount = float(amount_str)
        except Exception:
            amount = 0.0

        if amount <= 0:
            self.inp_amount.setFocus()
            self.inp_amount.selectAll()
            return

        selected_ids = [int(value) for value in self.selected_debts if str(value).isdigit()]
        open_debts = self.db.get_unpaid_debts(self.customer.get("id"), self.selected_currency) or []
        if selected_ids:
            open_debts = [row for row in open_debts if row[0] in selected_ids]
        open_total = round(sum(max(0.0, abs(float(row[6] or 0.0))) for row in open_debts), 2)
        if open_total <= 0.009:
            self.inp_amount.setFocus()
            self.inp_amount.selectAll()
            return
        if amount > open_total + 0.009:
            self.inp_amount.setText(
                f"{open_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
            self.inp_amount.setFocus()
            self.inp_amount.selectAll()
            return

        # KDV Hesaplaması
        vat_rate = TaxSettings.ratio_from_text(
            self.combo_vat_rate.currentText()
        )

        net_amount = amount / (1 + vat_rate) if vat_rate > 0 else amount
        vat_amount = amount - net_amount if vat_rate > 0 else 0.0

        # Taksit bilgileri
        is_installment = self.chk_installment.isChecked()
        down_payment = 0.0
        installment_count = 1
        monthly_payment = 0.0

        if is_installment:
            down_str = (
                self.inp_down_payment.text().strip().replace(".", "").replace(",", ".")
            )
            try:
                down_payment = float(down_str) if down_str else 0.0
            except ValueError:
                down_payment = 0.0
            installment_count = self.spin_installment.value()
            remaining = amount - down_payment
            if remaining > 0 and installment_count > 0:
                try:
                    monthly_payment = remaining / installment_count
                except ZeroDivisionError:
                    monthly_payment = 0.0

        # Seçili borç kalemleri
        selected_debt_ids = list(self.selected_debts)

        self.result_data = {
            "amount": amount,
            "method": self.selected_method,
            "date": self.date_edit.date().toString("dd.MM.yyyy"),
            "notes": self.inp_notes.toPlainText().strip(),
            "currency": self.selected_currency,
            "exchange_rate": self.selected_exchange_rate,
            "selected_services": [
                {"kind": "balance", "currency": self.selected_currency}
            ],
            "bank_account_id": None,
            "reference_tracking_no": self.reference_tracking_no,
            "reference_desc": self.reference_desc,
            "vat_rate": vat_rate,
            "net_amount": net_amount,
            "vat_amount": vat_amount,
            "is_installment": is_installment,
            "down_payment": down_payment,
            "installment_count": installment_count,
            "monthly_payment": monthly_payment,
            "print_receipt": self.chk_print_receipt.isChecked(),
            "selected_debt_ids": selected_debt_ids,  # Seçili borç kayıtları
        }

        # Makbuz yazdırma
        if self.chk_print_receipt.isChecked():
            self._print_receipt()

        self.accept()

    def _toggle_installment(self, enabled):
        """Taksit bölümünü aç/kapat"""
        self.inp_down_payment.setEnabled(enabled)
        self.spin_installment.setEnabled(enabled)
        if enabled:
            self._calculate_installment()
        else:
            self.lbl_monthly.setText("Aylık Taksit: -")

    def _calculate_installment(self):
        """Aylık taksit tutarını hesapla"""
        if not self.chk_installment.isChecked():
            return

        amount_str = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            total = float(amount_str) if amount_str else 0.0
        except ValueError:
            total = 0.0

        down_str = (
            self.inp_down_payment.text().strip().replace(".", "").replace(",", ".")
        )
        try:
            down = float(down_str) if down_str else 0.0
        except ValueError:
            down = 0.0

        count = self.spin_installment.value()

        remaining = total - down
        if remaining > 0 and count > 0:
            try:
                monthly = remaining / count
            except ZeroDivisionError:
                monthly = 0.0
            symbol = self._symbol(self.selected_currency)
            self.lbl_monthly.setText(
                f"Aylık Taksit: {symbol}{monthly:,.2f} x {count} ay"
            )
        else:
            self.lbl_monthly.setText("Aylık Taksit: -")

    def _calculate_vat(self):
        """KDV hesaplaması yap ve göster"""
        amount_str = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            total = float(amount_str) if amount_str else 0.0
        except ValueError:
            total = 0.0

        vat_rate = TaxSettings.ratio_from_text(
            self.combo_vat_rate.currentText()
        )

        if vat_rate > 0 and (1 + vat_rate) != 0:
            try:
                net_amount = total / (1 + vat_rate)
                vat_amount = total - net_amount
            except ZeroDivisionError:
                net_amount = total
                vat_amount = 0.0
        else:
            net_amount = total
            vat_amount = 0.0

        symbol = self._symbol(self.selected_currency)
        self.lbl_net_amount.setText(f"{symbol}{net_amount:,.2f}")
        self.lbl_vat_amount.setText(f"{symbol}{vat_amount:,.2f}")
        self.lbl_total_with_vat.setText(f"{symbol}{total:,.2f}")

    def _print_receipt(self):
        """Ödeme makbuzu yazdır"""
        data = self.result_data
        if not data:
            return

        receipt_lines = []
        receipt_lines.append("=" * 40)
        receipt_lines.append("AYEC PRO - TAHSLAT MAKBUZU")
        receipt_lines.append("=" * 40)
        receipt_lines.append(f"Tarih: {data.get('date', '')}")
        receipt_lines.append(f"Musteri: {self.customer.get('name', '')}")
        receipt_lines.append("-" * 40)
        receipt_lines.append(f"Odeme Yontemi: {data.get('method', '')}")
        receipt_lines.append(f"Para Birimi: {data.get('currency', 'TRY')}")
        receipt_lines.append("-" * 40)

        if data.get("vat_rate", 0) > 0:
            vat_percent = int(data["vat_rate"] * 100)
            receipt_lines.append(f"Net Tutar: {data.get('net_amount', 0):,.2f}")
            receipt_lines.append(
                f"KDV (%{vat_percent}): {data.get('vat_amount', 0):,.2f}"
            )
            receipt_lines.append("-" * 40)

        receipt_lines.append(f"TOPLAM: {data.get('amount', 0):,.2f}")

        if data.get("is_installment"):
            receipt_lines.append("-" * 40)
            receipt_lines.append("TAKSIT BILGISI:")
            receipt_lines.append(f"Pesinat: {data.get('down_payment', 0):,.2f}")
            receipt_lines.append(f"Taksit Sayisi: {data.get('installment_count', 1)}")
            receipt_lines.append(f"Aylik Taksit: {data.get('monthly_payment', 0):,.2f}")

        receipt_lines.append("=" * 40)
        receipt_lines.append("Tesekkur ederiz!")
        receipt_lines.append("")

        receipt_text = "\n".join(receipt_lines)

        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
            from PyQt6.QtGui import QTextDocument

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)

            if dialog.exec() == QPrintDialog.DialogCode.Accepted:
                doc = QTextDocument()
                doc.setPlainText(receipt_text)
                doc.print(printer)
        except Exception as e:
            from PyQt6.QtWidgets import QFileDialog

            filename, _ = QFileDialog.getSaveFileName(
                self, "Makbuzu Kaydet", "makbuz.txt", "Text Files (*.txt)"
            )
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(receipt_text)

    def _input_qss(self):
        """Input alanı stili"""
        return """
            QLineEdit {
                background: @surface;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: @text;
            }
            QLineEdit:focus {
                border-color: @accent;
            }
            QLineEdit:disabled {
                background: @surface_alt;
                color: @text_muted;
            }
        """

    def _combo_qss(self):
        """ComboBox stili"""
        return """
            QComboBox {
                background: @surface;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: @text;
            }
            QComboBox:focus {
                border-color: @accent;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background: @surface;
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
        """

    def get_data(self):
        return getattr(self, "result_data", None)

    def _wire_ui_signals(self):
        self.chk_print_receipt.stateChanged.connect(self._on_ui_widget_changed)


# Geriye d\u00f6n\u00fck uyumluluk alias
PaymentDialog = ModernPaymentDialog
