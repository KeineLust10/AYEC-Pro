from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
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
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper


class ModernPaymentDialog(ModernDialog):
    def __init__(self, parent, db, customer):
        super().__init__(title="Odeme Al", parent=parent, width=920, height=760)
        self.db = db
        self.customer = self._normalize_customer(customer)
        self.drag_pos = None
        self.selected_currency = "TRY"
        self.selected_exchange_rate = 1.0
        self.selected_method = "Nakit"
        self.balance_buttons = {}
        self.method_buttons = {}
        self.customer_balances = {}
        self.reference_tracking_no = None
        self.reference_desc = None

        self.set_footer_visible(False)

        self._build_ui()
        self._load_balances()
        # En yüksek borçlu (negatif bakiyeli) para birimini otomatik seç
        best_currency = "TRY"
        best_debt = 0.0
        for code in ("TRY", "USD", "EUR"):
            bal = float(self.customer_balances.get(code, 0.0) or 0.0)
            if bal < 0 and abs(bal) > best_debt:
                best_debt = abs(bal)
                best_currency = code
        self._apply_selected_currency(best_currency, prefill=(best_debt > 0.01))
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
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
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
        root.setContentsMargins(18, 18, 18, 18)

        card = QFrame()
        card.setObjectName("PaymentCard")
        card.setStyleSheet(
            theme_qss(
                """
                QFrame#PaymentCard {
                    background: @surface;
                    border: 1px solid @border;
                    border-radius: 28px;
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
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(18)

        header = QHBoxLayout()
        head_left = QVBoxLayout()
        title = QLabel("Ödeme Al")
        title.setStyleSheet(theme_qss("font-size: 28px; font-weight: 900; color: @text;"))
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
        content_row.setSpacing(16)

        left_panel = QWidget()
        left_col = QVBoxLayout(left_panel)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(12)

        right_panel = QWidget()
        right_col = QVBoxLayout(right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(12)

        content_row.addWidget(left_panel, 3)
        content_row.addWidget(right_panel, 2)
        layout.addLayout(content_row, 1)

        balance_title = QLabel("Açık bakiyeler")
        balance_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
        left_col.addWidget(balance_title)

        self.balance_row = QHBoxLayout()
        self.balance_row.setSpacing(10)
        left_col.addLayout(self.balance_row)

        self.lbl_balance_hint = QLabel("")
        self.lbl_balance_hint.setStyleSheet(theme_qss("font-size: 12px; font-weight: 700; color: @text;"))
        left_col.addWidget(self.lbl_balance_hint)

        amount_title = QLabel("Ödeme tutarı")
        amount_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
        left_col.addWidget(amount_title)

        self.inp_amount = QLineEdit()
        self.inp_amount.setPlaceholderText("0.00")
        self.inp_amount.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.inp_amount.setFixedHeight(88)
        self.inp_amount.setStyleSheet(
            theme_qss(
                """
                QLineEdit {
                    background: @surface;
                    border: 2px solid @border;
                    border-radius: 18px;
                    padding: 12px;
                    color: @text;
                    font-size: 28px;
                    font-weight: 900;
                }
                QLineEdit:focus {
                    border-color: @accent;
                    background: @surface_alt;
                }
                """
            )
        )
        left_col.addWidget(self.inp_amount)

        method_title = QLabel("Ödeme yöntemi")
        method_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
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

        self.lbl_rate = QLabel("1.0000")
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

        notes_title = QLabel("İşlem notu")
        notes_title.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
        left_col.addWidget(notes_title)

        self.inp_notes = QTextEdit()
        self.inp_notes.setPlaceholderText("İşlemle ilgili notunuzu buraya ekleyebilirsiniz...")
        self.inp_notes.setFixedHeight(120)
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

        # ===== TAKSİT BÖLÜMÜ =====
        self.installment_frame = QFrame()
        self.installment_frame.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 12px;
            }
        """))
        inst_layout = QVBoxLayout(self.installment_frame)
        inst_layout.setSpacing(10)
        inst_layout.setContentsMargins(15, 15, 15, 15)
        
        # Taksit checkbox
        inst_header = QHBoxLayout()
        self.chk_installment = QCheckBox("Taksitli Ödeme")
        self.chk_installment.setStyleSheet(theme_qss("font-size: 13px; font-weight: 700; color: @text;"))
        self.chk_installment.toggled.connect(self._toggle_installment)
        inst_header.addWidget(self.chk_installment)
        inst_header.addStretch()
        inst_layout.addLayout(inst_header)
        
        # Peşinat ve Taksit Sayısı
        inst_form = QGridLayout()
        inst_form.setHorizontalSpacing(12)
        inst_form.setVerticalSpacing(8)
        
        # Peşinat
        inst_form.addWidget(self._label("Peşinat"), 0, 0)
        self.inp_down_payment = QLineEdit()
        self.inp_down_payment.setPlaceholderText("0.00")
        self.inp_down_payment.setEnabled(False)
        self.inp_down_payment.setStyleSheet(theme_qss(self._input_qss()))
        self.inp_down_payment.textChanged.connect(self._calculate_installment)
        inst_form.addWidget(self.inp_down_payment, 1, 0)
        
        # Taksit Sayısı
        inst_form.addWidget(self._label("Taksit Sayısı"), 0, 1)
        self.spin_installment = QSpinBox()
        self.spin_installment.setRange(2, 36)
        self.spin_installment.setValue(3)
        self.spin_installment.setEnabled(False)
        self.spin_installment.setStyleSheet(theme_qss(self._spin_qss()))
        self.spin_installment.valueChanged.connect(self._calculate_installment)
        inst_form.addWidget(self.spin_installment, 1, 1)
        
        inst_layout.addLayout(inst_form)
        
        # Aylık Taksit Gösterimi
        self.lbl_monthly = QLabel("Aylık Taksit: -")
        self.lbl_monthly.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @accent;"))
        self.lbl_monthly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inst_layout.addWidget(self.lbl_monthly)
        
        right_col.addWidget(self.installment_frame)
        
        # ===== KDV HESAPLAMA BÖLÜMÜ =====
        vat_frame = QFrame()
        vat_frame.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 14px;
                padding: 12px;
            }
        """))
        vat_layout = QVBoxLayout(vat_frame)
        vat_layout.setSpacing(10)
        vat_layout.setContentsMargins(15, 15, 15, 15)
        
        vat_header = QHBoxLayout()
        vat_header.addWidget(self._label("KDV Hesaplama"))
        vat_header.addStretch()
        
        # KDV Oranı
        self.combo_vat_rate = QComboBox()
        self.combo_vat_rate.addItems(["%20", "%18", "%10", "%8", "%1", "KDV Hariç"])
        self.combo_vat_rate.setCurrentIndex(0)  # Default %20
        self.combo_vat_rate.setStyleSheet(theme_qss(self._combo_qss()))
        self.combo_vat_rate.currentTextChanged.connect(self._calculate_vat)
        self.combo_vat_rate.setFixedWidth(120)
        vat_header.addWidget(self.combo_vat_rate)
        vat_layout.addLayout(vat_header)
        
        # KDV Detayları
        vat_grid = QGridLayout()
        vat_grid.setHorizontalSpacing(12)
        vat_grid.setVerticalSpacing(8)
        
        # Net Tutar
        vat_grid.addWidget(self._label("Net Tutar"), 0, 0)
        self.lbl_net_amount = QLabel("0,00")
        self.lbl_net_amount.setStyleSheet(theme_qss("font-size: 14px; font-weight: 700; color: @text;"))
        vat_grid.addWidget(self.lbl_net_amount, 1, 0)
        
        # KDV Tutarı
        vat_grid.addWidget(self._label("KDV Tutarı"), 0, 1)
        self.lbl_vat_amount = QLabel("0,00")
        self.lbl_vat_amount.setStyleSheet(theme_qss("font-size: 14px; font-weight: 700; color: @warning;"))
        vat_grid.addWidget(self.lbl_vat_amount, 1, 1)
        
        # Toplam
        vat_grid.addWidget(self._label("GENEL TOPLAM"), 0, 2)
        self.lbl_total_with_vat = QLabel("0,00")
        self.lbl_total_with_vat.setStyleSheet(theme_qss("font-size: 16px; font-weight: 900; color: @success;"))
        vat_grid.addWidget(self.lbl_total_with_vat, 1, 2)
        
        vat_layout.addLayout(vat_grid)
        right_col.addWidget(vat_frame)
        
        # Makbuz yazdırma seçeneği
        self.chk_print_receipt = QCheckBox("Ödeme makbuzu yazdır")
        self.chk_print_receipt.setStyleSheet(theme_qss("font-size: 12px; font-weight: 600; color: @text;"))
        self.chk_print_receipt.setChecked(True)
        right_col.addWidget(self.chk_print_receipt)

        right_col.addStretch(1)

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

        btn_save = QPushButton("Ödemeyi Tamamla")
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
        lbl.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text_muted;"))
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

    def _build_method_cards(self):
        methods = ["Nakit", "Kredi Kartı", "Havale / EFT", "Çek / Senet"]
        for method in methods:
            btn = QPushButton(method)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(56)
            btn.clicked.connect(lambda _=False, value=method: self._apply_selected_method(value))
            self.method_buttons[method] = btn
            self.method_row.addWidget(btn, 1)

    def _load_balances(self):
        try:
            self.customer_balances = self.db.get_customer_all_balances(self.customer.get("id")) or {}
        except Exception:
            self.customer_balances = {}

        if not self.customer_balances:
            self.customer_balances = {"TRY": 0.0, "USD": 0.0, "EUR": 0.0}

        while self.balance_row.count():
            item = self.balance_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for code in ("TRY", "USD", "EUR"):
            btn = QPushButton(self._format_balance_text(code))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setMinimumHeight(62)
            btn.clicked.connect(lambda _=False, curr=code: self._apply_selected_currency(curr, prefill=True))
            self.balance_buttons[code] = btn
            self.balance_row.addWidget(btn, 1)

    def _format_balance_text(self, code):
        balance = float(self.customer_balances.get(code, 0.0) or 0.0)
        # Negatif bakiye = müşteri bize borçlu (Alacak), pozitif = müşteri alacaklı
        if abs(balance) < 0.01:
            status = "Kapalı"
        elif balance < 0:
            status = "Alacak (Borç)"
        else:
            status = "Fazla Ödeme"
        return f"{code}\n{CurrencyHelper.format_amount(abs(balance), currency_code=code)}\n{status}"

    def _apply_selected_currency(self, currency, prefill=False):
        self.selected_currency = currency or "TRY"
        self.selected_exchange_rate = self._get_rate(self.selected_currency)
        self.lbl_rate.setText(f"{self.selected_exchange_rate:,.4f}")

        balance = float(self.customer_balances.get(self.selected_currency, 0.0) or 0.0)
        debt = abs(balance) if balance < 0 else 0.0   # negatif bakiye = borç
        if debt > 0.01:
            self.lbl_balance_hint.setText(
                f"Tahsil edilecek: {CurrencyHelper.format_amount(debt, currency_code=self.selected_currency)}"
            )
        elif balance > 0.01:
            self.lbl_balance_hint.setText(
                f"{self.selected_currency} fazla ödeme: "
                f"{CurrencyHelper.format_amount(balance, currency_code=self.selected_currency)}"
            )
        else:
            self.lbl_balance_hint.setText(f"{self.selected_currency} bakiyesi kapalı")

        for code, button in self.balance_buttons.items():
            is_active = code == self.selected_currency
            # Negatif bakiye = müşteri borçlu; pozitif = fazla ödeme
            code_balance = float(self.customer_balances.get(code, 0.0) or 0.0)
            has_debt = code_balance < -0.01
            accent = "@warning" if has_debt else "@surface_alt"
            button.setStyleSheet(
                theme_qss(
                    f"""
                    QPushButton {{
                        background: {'@accent' if is_active else '@surface_alt'};
                        color: {'@selection_text' if is_active else '@text'};
                        border: 1px solid {'@accent' if is_active else '@border'};
                        border-radius: 16px;
                        font-size: 12px;
                        font-weight: 800;
                        padding: 8px 10px;
                    }}
                    QPushButton:hover {{
                        border-color: {accent};
                    }}
                    """
                )
            )

        if prefill and debt > 0.01:
            self.inp_amount.setText(f"{debt:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    def _apply_selected_method(self, method):
        self.selected_method = method
        for name, button in self.method_buttons.items():
            is_active = name == self.selected_method
            button.setStyleSheet(
                theme_qss(
                    f"""
                    QPushButton {{
                        background: {'@accent' if is_active else '@surface_alt'};
                        color: {'@selection_text' if is_active else '@text'};
                        border: 1px solid {'@accent' if is_active else '@border'};
                        border-radius: 16px;
                        padding: 10px 12px;
                        font-size: 12px;
                        font-weight: 800;
                    }}
                    QPushButton:hover {{
                        border-color: @accent;
                        background: {'@accent' if is_active else '@surface'};
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
        vat_rate_text = self.combo_vat_rate.currentText()
        vat_rate = 0.0
        if vat_rate_text == "%20":
            vat_rate = 0.20
        elif vat_rate_text == "%18":
            vat_rate = 0.18
        elif vat_rate_text == "%10":
            vat_rate = 0.10
        elif vat_rate_text == "%8":
            vat_rate = 0.08
        elif vat_rate_text == "%1":
            vat_rate = 0.01
        
        net_amount = amount / (1 + vat_rate) if vat_rate > 0 else amount
        vat_amount = amount - net_amount if vat_rate > 0 else 0.0
        
        # Taksit bilgileri
        is_installment = self.chk_installment.isChecked()
        down_payment = 0.0
        installment_count = 1
        monthly_payment = 0.0
        
        if is_installment:
            down_str = self.inp_down_payment.text().strip().replace(".", "").replace(",", ".")
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

        self.result_data = {
            "amount": amount,
            "method": self.selected_method,
            "date": self.date_edit.date().toString("dd.MM.yyyy"),
            "notes": self.inp_notes.toPlainText().strip(),
            "currency": self.selected_currency,
            "exchange_rate": self.selected_exchange_rate,
            "selected_services": [{"kind": "balance", "currency": self.selected_currency}],
            "bank_account_id": None,
            "reference_tracking_no": self.reference_tracking_no,
            "reference_desc": self.reference_desc,
            # Yeni alanlar
            "vat_rate": vat_rate,
            "net_amount": net_amount,
            "vat_amount": vat_amount,
            "is_installment": is_installment,
            "down_payment": down_payment,
            "installment_count": installment_count,
            "monthly_payment": monthly_payment,
            "print_receipt": self.chk_print_receipt.isChecked(),
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
        
        # Toplam tutar
        amount_str = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            total = float(amount_str) if amount_str else 0.0
        except ValueError:
            total = 0.0

        # Peşinat
        down_str = self.inp_down_payment.text().strip().replace(".", "").replace(",", ".")
        try:
            down = float(down_str) if down_str else 0.0
        except ValueError:
            down = 0.0
        
        # Taksit sayısı
        count = self.spin_installment.value()
        
        # Kalan tutar
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
        # Toplam tutarı al
        amount_str = self.inp_amount.text().strip().replace(".", "").replace(",", ".")
        try:
            total = float(amount_str) if amount_str else 0.0
        except ValueError:
            total = 0.0
        
        # KDV oranı
        vat_rate_text = self.combo_vat_rate.currentText()
        vat_rate = 0.0
        if vat_rate_text == "%20":
            vat_rate = 0.20
        elif vat_rate_text == "%18":
            vat_rate = 0.18
        elif vat_rate_text == "%10":
            vat_rate = 0.10
        elif vat_rate_text == "%8":
            vat_rate = 0.08
        elif vat_rate_text == "%1":
            vat_rate = 0.01
        
        # Hesapla
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
        
        # Göster
        symbol = self._symbol(self.selected_currency)
        self.lbl_net_amount.setText(f"{symbol}{net_amount:,.2f}")
        self.lbl_vat_amount.setText(f"{symbol}{vat_amount:,.2f}")
        self.lbl_total_with_vat.setText(f"{symbol}{total:,.2f}")

    def _print_receipt(self):
        """Ödeme makbuzu yazdır"""
        data = self.result_data
        if not data:
            return
        
        # Makbuz içeriği oluştur
        receipt_lines = []
        receipt_lines.append("=" * 40)
        receipt_lines.append("AYEC PRO - ÖDEME MAKBUZU")
        receipt_lines.append("=" * 40)
        receipt_lines.append(f"Tarih: {data.get('date', '')}")
        receipt_lines.append(f"Müşteri: {self.customer.get('name', '')}")
        receipt_lines.append("-" * 40)
        receipt_lines.append(f"Ödeme Yöntemi: {data.get('method', '')}")
        receipt_lines.append(f"Para Birimi: {data.get('currency', 'TRY')}")
        receipt_lines.append("-" * 40)
        
        # KDV detayları
        if data.get('vat_rate', 0) > 0:
            vat_percent = int(data['vat_rate'] * 100)
            receipt_lines.append(f"Net Tutar: {data.get('net_amount', 0):,.2f}")
            receipt_lines.append(f"KDV (%{vat_percent}): {data.get('vat_amount', 0):,.2f}")
            receipt_lines.append("-" * 40)
        
        receipt_lines.append(f"TOPLAM: {data.get('amount', 0):,.2f}")
        
        # Taksit detayları
        if data.get('is_installment'):
            receipt_lines.append("-" * 40)
            receipt_lines.append("TAKSİT BİLGİSİ:")
            receipt_lines.append(f"Peşinat: {data.get('down_payment', 0):,.2f}")
            receipt_lines.append(f"Taksit Sayısı: {data.get('installment_count', 1)}")
            receipt_lines.append(f"Aylık Taksit: {data.get('monthly_payment', 0):,.2f}")
        
        receipt_lines.append("=" * 40)
        receipt_lines.append("Teşekkür ederiz!")
        receipt_lines.append("")
        
        receipt_text = "\n".join(receipt_lines)
        
        # Termal yazıcıya gönder veya PDF olarak kaydet
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
            # Yazıcı yoksa dosyaya kaydet
            from PyQt6.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "Makbuzu Kaydet", "makbuz.txt", "Text Files (*.txt)"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
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

    def _spin_qss(self):
        """SpinBox stili"""
        return """
            QSpinBox {
                background: @surface;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                color: @text;
            }
            QSpinBox:focus {
                border-color: @accent;
            }
            QSpinBox:disabled {
                background: @surface_alt;
                color: @text_muted;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                background: @surface_alt;
                border: 1px solid @border;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background: @accent;
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
