# -*- coding: utf-8 -*-

from PyQt6.QtCore import QDate, Qt
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
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.tax_settings import TaxSettings



class ModernPaymentDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, parent, db, customer):
        super().__init__(title="Tahsilat Al", parent=parent, width=1280, height=860)
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

        self.set_footer_visible(False)

        self._build_ui()
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
        layout.setContentsMargins(18, 14, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        head_left = QVBoxLayout()
        head_left.setContentsMargins(0, 0, 0, 0)
        head_left.setSpacing(4)
        title = QLabel("Tahsilat Al")
        title.setStyleSheet(
            theme_qss("font-size: 24px; font-weight: 900; color: @text;")
        )
        customer_name = self.customer.get("name", "")
        customer_phone = self.customer.get("phone", "") or "-"
        customer_lbl = QLabel(f"{customer_name}  |  {customer_phone}")
        customer_lbl.setStyleSheet(theme_qss("font-size: 13px; color: @text;"))
        head_left.addWidget(title)
        head_left.addWidget(customer_lbl)
        header.addLayout(head_left)
        header.addStretch()

        btn_close = QPushButton("×")
        btn_close.setFixedSize(34, 34)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background: @surface_alt;
                    color: @text_muted;
                    border: none;
                    border-radius: 17px;
                    font-size: 18px;
                    font-weight: 900;
                }
                QPushButton:hover {
                    background: @danger;
                    color: @selection_text;
                }
                """
            )
        )
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        layout.addLayout(header)

        content_row = QHBoxLayout()
        content_row.setSpacing(14)

        left_panel = QWidget()
        left_col = QVBoxLayout(left_panel)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(14)

        right_panel = QWidget()
        right_col = QVBoxLayout(right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(12)

        content_row.addWidget(left_panel, 5)
        content_row.addWidget(right_panel, 6)
        layout.addLayout(content_row, 1)

        currencies_title = QLabel("Para Birimi Seçimi")
        currencies_title.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(currencies_title)

        self.currency_cards_layout = QGridLayout()
        self.currency_cards_layout.setHorizontalSpacing(12)
        self.currency_cards_layout.setVerticalSpacing(12)
        left_col.addLayout(self.currency_cards_layout)

        # Sol panel - Ödeme tutarı ve yöntemi
        amount_title = QLabel("Tahsilat Tutarı")
        amount_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(amount_title)

        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0,00")
        self.inp_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inp_amount.setFixedHeight(70)
        self.inp_amount.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    background: @surface;
                    border: 2px solid @border;
                    border-radius: 16px;
                    padding: 12px;
                    color: @text;
                    font-size: 24px;
                    font-weight: 900;
                }
                QLineEdit:focus {
                    border-color: @accent;
                    background: @surface_alt;
                }
                """
            )
        )
        self.inp_amount.textChanged.connect(self._on_amount_changed)
        left_col.addWidget(self.inp_amount)

        method_title = QLabel("Ödeme Yöntemi")
        method_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(method_title)

        self.method_row = QHBoxLayout()
        self.method_row.setSpacing(10)
        left_col.addLayout(self.method_row)
        self._build_method_cards()

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        form.addWidget(self._label("Kur"), 0, 0)
        form.addWidget(self._label("Tarih"), 0, 1)

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
        self.date_edit.setFixedHeight(46)
        self.date_edit.setStyleSheet(theme_qss(self._date_qss()))

        form.addWidget(self.lbl_rate, 1, 0)
        form.addWidget(self.date_edit, 1, 1)
        left_col.addLayout(form)

        notes_title = QLabel("İşlem Notu")
        notes_title.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
        )
        left_col.addWidget(notes_title)

        self.inp_notes = QTextEdit()
        self.inp_notes.setPlaceholderText(
            "İşlemle ilgili notunuzu buraya ekleyebilirsiniz..."
        )
        self.inp_notes.setFixedHeight(100)
        self.inp_notes.setStyleSheet(
            theme_qss(
                """
                QTextEdit {
                    background: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 14px;
                    padding: 12px;
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
        left_col.addWidget(self.inp_notes)

        debt_section_title = QLabel("Borç Kalemleri")
        debt_section_title.setStyleSheet(
            theme_qss("font-size: 12px; font-weight: 800; color: @text_muted;")
        )
        right_col.addWidget(debt_section_title)

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
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.debt_scroll.setMinimumHeight(360)
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
        self.debt_layout.setContentsMargins(12, 12, 12, 12)
        self.debt_layout.setSpacing(10)
        self.debt_layout.addStretch()
        self.debt_scroll.setWidget(self.debt_container)
        right_col.addWidget(self.debt_scroll, 1)

        self.lbl_selected_total = QLabel("Seçili Toplam: 0,00")
        self.lbl_selected_total.setStyleSheet(
            theme_qss("font-size: 16px; font-weight: 900; color: @accent;")
        )
        self.lbl_selected_total.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self.lbl_selected_total)

        vat_frame = QFrame()
        vat_frame.setStyleSheet(
            theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 12px;
            }
        """)
        )
        vat_layout = QVBoxLayout(vat_frame)
        vat_layout.setSpacing(10)
        vat_layout.setContentsMargins(15, 15, 15, 15)

        vat_header = QHBoxLayout()
        vat_header.addWidget(self._label("KDV Hesaplama"))
        vat_header.addStretch()

        self.combo_vat_rate = QComboBox()
        self.combo_vat_rate.addItems(["%20", "%18", "%10", "%8", "%1", "KDV Hariç"])
        default_vat_text = TaxSettings.combo_text(self.db)
        if self.combo_vat_rate.findText(default_vat_text) < 0:
            self.combo_vat_rate.insertItem(0, default_vat_text)
        self.combo_vat_rate.setCurrentText(default_vat_text)
        self.combo_vat_rate.setStyleSheet(theme_qss(self._combo_qss()))
        self.combo_vat_rate.currentTextChanged.connect(self._calculate_vat)
        self.combo_vat_rate.setFixedWidth(120)
        vat_header.addWidget(self.combo_vat_rate)
        vat_layout.addLayout(vat_header)

        vat_grid = QGridLayout()
        vat_grid.setHorizontalSpacing(12)
        vat_grid.setVerticalSpacing(8)

        vat_grid.addWidget(self._label("Net Tutar"), 0, 0)
        self.lbl_net_amount = QLabel("0,00")
        self.lbl_net_amount.setStyleSheet(
            theme_qss("font-size: 14px; font-weight: 700; color: @text;")
        )
        vat_grid.addWidget(self.lbl_net_amount, 1, 0)

        vat_grid.addWidget(self._label("KDV Tutarı"), 0, 1)
        self.lbl_vat_amount = QLabel("0,00")
        self.lbl_vat_amount.setStyleSheet(
            theme_qss("font-size: 14px; font-weight: 700; color: @warning;")
        )
        vat_grid.addWidget(self.lbl_vat_amount, 1, 1)

        vat_grid.addWidget(self._label("GENEL TOPLAM"), 0, 2)
        self.lbl_total_with_vat = QLabel("0,00")
        self.lbl_total_with_vat.setStyleSheet(
            theme_qss("font-size: 16px; font-weight: 900; color: @success;")
        )
        vat_grid.addWidget(self.lbl_total_with_vat, 1, 2)

        vat_layout.addLayout(vat_grid)
        right_col.addWidget(vat_frame)

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
            theme_qss("font-size: 13px; font-weight: 700; color: @text;")
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
        lbl.setStyleSheet(
            theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;")
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
        """Varsayılan dövizi her zaman, diğerlerini sadece bakiye varsa göster."""
        while self.currency_cards_layout.count():
            item = self.currency_cards_layout.takeAt(0)
            self._dispose_layout_item(item)

        default_currency = CurrencyHelper.get_code(self.db)
        visible_codes = []
        for code in ("TRY", "USD", "EUR"):
            balance = float(self.customer_balances.get(code, 0.0) or 0.0)
            if code == default_currency or abs(balance) > 0.0001:
                visible_codes.append(code)

        if not visible_codes:
            visible_codes = [default_currency]

        for idx, code in enumerate(visible_codes):
            row = idx // 2
            col = idx % 2
            self.currency_cards_layout.addWidget(
                self._create_currency_card(code), row, col
            )

    def _create_currency_card(self, code):
        """Tek para birimi kartı oluştur"""
        balance = float(self.customer_balances.get(code, 0.0) or 0.0)

        card = QFrame()
        card.setObjectName(f"CurrencyCard_{code}")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setFixedHeight(100)

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
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        # Para birimi adı
        lbl_code = QLabel(code)
        lbl_code.setStyleSheet(
            theme_qss(f"""
            background: transparent;
            border: none;
            font-size: 13px;
            font-weight: 800;
            color: {text_color};
        """)
        )
        layout.addWidget(lbl_code)

        # Bakiye tutarı
        display_balance = CurrencyHelper.convert_amount(
            self.db,
            abs(balance),
            from_currency=code,
            to_currency=self.selected_currency,
        )
        lbl_amount = QLabel(
            CurrencyHelper.format_amount(
                display_balance, currency_code=self.selected_currency
            )
        )
        lbl_amount.setStyleSheet(
            theme_qss(f"""
            background: transparent;
            border: none;
            font-size: 24px;
            font-weight: 900;
            color: {text_color};
        """)
        )
        layout.addWidget(lbl_amount)

        # Durum metni
        if abs(balance) < 0.01:
            status_text = "Bakiye Kapalı"
        elif balance < 0:
            status_text = f"Borç: {CurrencyHelper.format_amount(display_balance, currency_code=self.selected_currency)}"
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
        for method in methods:
            btn = QPushButton(method)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(50)
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

        visible_debt_ids = {debt[0] for debt in filtered_debts}
        self.selected_debts = {
            debt_id for debt_id in self.selected_debts if debt_id in visible_debt_ids
        }

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

        self.debt_layout.addStretch()
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
        frame.setStyleSheet(
            theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
            }
            QFrame:hover {
                border-color: @accent;
            }
        """)
        )

        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # Üst satır - Checkbox + Özet bilgi
        header_layout = QHBoxLayout()

        checkbox = QCheckBox()
        checkbox.setChecked(debt_id in self.selected_debts)
        checkbox.stateChanged.connect(
            lambda state, did=debt_id: self._on_debt_selected(did, state)
        )
        header_layout.addWidget(checkbox)

        # Açıklama
        desc_text = description or "Borç Kaydı"
        if len(desc_text) > 56:
            desc_text = desc_text[:53] + "..."
        lbl_desc = QLabel(desc_text)
        lbl_desc.setStyleSheet(
            theme_qss("font-size: 13px; font-weight: 700; color: @text;")
        )
        lbl_desc.setWordWrap(True)
        header_layout.addWidget(lbl_desc, 1)

        lbl_currency = QLabel(str(currency or "TRY").upper())
        lbl_currency.setStyleSheet(
            theme_qss("""
            font-size: 11px;
            font-weight: 800;
            color: @selection_text;
            background: @accent;
            border-radius: 10px;
            padding: 4px 8px;
        """)
        )
        header_layout.addWidget(lbl_currency)

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
            theme_qss("font-size: 14px; font-weight: 900; color: @warning;")
        )
        header_layout.addWidget(lbl_amount)

        # Detay butonu
        btn_toggle = QPushButton("▼")
        btn_toggle.setFixedSize(28, 28)
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

        symbol = self._symbol(self.selected_currency)
        self.lbl_selected_total.setText(f"Seçili Toplam: {symbol}{total:,.2f}")

        if total > 0:
            self.inp_amount.setText(
                f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

    def _apply_selected_currency(self, currency):
        self.selected_currency = currency or CurrencyHelper.get_code(self.db)
        self.selected_exchange_rate = self._get_rate(self.selected_currency)
        self.lbl_rate.setText(
            f"{self.selected_exchange_rate:,.4f}".replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        # Kartları yeniden çiz
        self._build_currency_cards()

        # Borç listesini güncelle
        self._refresh_debt_list()
        self._update_selected_total()

    def _apply_selected_method(self, method):
        self.selected_method = method
        for name, button in self.method_buttons.items():
            is_active = name == self.selected_method
            button.setStyleSheet(
                theme_qss(
                    f"""
                    QPushButton {{
                        background: {"@accent" if is_active else "@surface_alt"};
                        color: {"@selection_text" if is_active else "@text"};
                        border: 1px solid {"@accent" if is_active else "@border"};
                        border-radius: 12px;
                        padding: 10px 12px;
                        font-size: 12px;
                        font-weight: 800;
                    }}
                    QPushButton:hover {{
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
        if self.chk_installment.isChecked():
            self._calculate_installment()

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
