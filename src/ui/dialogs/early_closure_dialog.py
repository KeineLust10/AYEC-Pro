"""
Early Loan Closure Confirmation Dialog
Erken kredi kapatma onay ve tasarruf hesaplama dialogu
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QHeaderView,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import tc, theme_qss
from src.utils.design_system import DesignTokens


class EarlyClosureDialog(ModernDialog):
    """Erken Kapatma Onay ve Tasarruf Hesaplama Dialogu"""

    def __init__(self, loan_data, unpaid_installments, parent=None):
        super().__init__(title="Kredi Erken Kapatma", parent=parent, width=700, height=650)
        self.loan_data = loan_data
        self.unpaid_installments = unpaid_installments
        self.penalty_rate = 0.0
        self.setModal(True)
        self.set_footer_visible(False)
        self.setup_ui()
        self.calculate_savings()

    def setup_ui(self):
        layout = self.content_layout
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Erken Kredi Kapatma Hesaplamasi")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(header)

        info = QLabel(f"{self.loan_data.get('bank_name', 'Kredi')}")
        info.setFont(QFont("Segoe UI", 12))
        info.setStyleSheet(theme_qss("color: @text_muted;"))
        layout.addWidget(info)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(theme_qss("background-color: @surface_alt;"))
        layout.addWidget(line)

        penalty_layout = QFormLayout()
        penalty_layout.setSpacing(10)

        penalty_label = QLabel("Erken Kapatma Tazminat Orani:")
        penalty_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; font-weight: bold;"))

        self.penalty_spin = QSpinBox()
        self.penalty_spin.setRange(0, 5)
        self.penalty_spin.setValue(0)
        self.penalty_spin.setSuffix(" %")
        self.penalty_spin.setFixedWidth(100)
        DesignTokens.apply_spinbox_styles(self.penalty_spin)
        self.penalty_spin.valueChanged.connect(self.on_penalty_changed)

        penalty_layout.addRow(penalty_label, self.penalty_spin)
        layout.addLayout(penalty_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Kalem", "Tutar"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().resizeSection(1, 200)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            theme_qss(
                """
                QTableWidget {
                    border: 2px solid @border;
                    border-radius: 8px;
                    font-size: 13px;
                    gridline-color: @surface_alt;
                }
                QTableWidget::item {
                    padding: 12px;
                }
                QHeaderView::section {
                    background-color: @surface_alt;
                    padding: 10px;
                    border: none;
                    font-weight: bold;
                    color: @text_muted;
                }
                """
            )
        )
        layout.addWidget(self.table)

        self.lbl_comparison = QLabel("")
        self.lbl_comparison.setWordWrap(True)
        self.lbl_comparison.setStyleSheet(
            theme_qss(
                """
                QLabel {
                    color: @warning;
                    font-size: 13px;
                    font-weight: bold;
                    padding: 15px;
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 @surface_alt, stop:1 @warning);
                    border-left: 4px solid @warning;
                    border-radius: 8px;
                }
                """
            )
        )
        layout.addWidget(self.lbl_comparison)

        note = QLabel(
            "Not: Erken kapatmada sadece kalan ana parayi odersiniz. "
            "Faiz ve vergilerden tamamen kurtulursunuz!"
        )
        note.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; padding: 10px; background-color: @selection_bg; border-radius: 6px;"
            )
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        btn_layout = QHBoxLayout()

        self.btn_cancel = QPushButton("Iptal")
        self.btn_cancel.setFixedSize(120, 45)
        self.btn_cancel.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @surface_alt;
                    color: @text_muted;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                    border: 1px solid @border;
                }
                QPushButton:hover { background-color: @surface; border-color: @accent_hover; color: @text; }
                """
            )
        )
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_confirm = QPushButton("Evet, Kapat")
        self.btn_confirm.setFixedSize(150, 45)
        self.btn_confirm.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @success;
                    color: @selection_text;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover { background-color: @success; }
                """
            )
        )
        self.btn_confirm.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_confirm)
        layout.addLayout(btn_layout)

    def on_penalty_changed(self, value):
        self.penalty_rate = value
        self.calculate_savings()

    def calculate_savings(self):
        total_principal = 0.0
        total_interest = 0.0
        total_kkdf = 0.0
        total_bsmv = 0.0

        for installment in self.unpaid_installments:
            inst_dict = dict(installment) if hasattr(installment, "keys") else installment
            total_principal += inst_dict.get("principal_part", 0)
            total_interest += inst_dict.get("interest_part", 0)
            total_kkdf += inst_dict.get("kkdf_amount", 0)
            total_bsmv += inst_dict.get("bsmv_amount", 0)

        if total_principal == 0:
            total_amount = 0
            for installment in self.unpaid_installments:
                inst_dict = dict(installment) if hasattr(installment, "keys") else installment
                total_amount += inst_dict["amount"]
            total_principal = total_amount * 0.65
            total_interest = total_amount * 0.28
            total_kkdf = total_interest * 0.15
            total_bsmv = total_interest * 0.10

        total_tax = total_kkdf + total_bsmv
        penalty = total_principal * (self.penalty_rate / 100)
        total_savings = total_interest + total_tax - penalty

        self.table.setRowCount(0)
        rows = [
            ("Kapatmak Icin Gereken (Ana Para)", total_principal, tc("accent"), False),
            ("", 0, "", False),
            ("Odemekten Kurtuldugunuz Faiz", total_interest, tc("success"), True),
            ("Odemekten Kurtuldugunuz Vergi (KKDF+BSMV)", total_tax, tc("success"), True),
        ]
        if penalty > 0:
            rows.append(("Erken Kapatma Tazminati", penalty, tc("danger"), False))
        rows.append(("", 0, "", False))
        rows.append(("TOPLAM KAZANCINIZ", total_savings, tc("success"), True))

        for label, amount, color, is_bold in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            if not label:
                continue

            label_item = QTableWidgetItem(label)
            if is_bold:
                label_item.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            if color:
                label_item.setForeground(QColor(color))
            self.table.setItem(row, 0, label_item)

            if amount > 0:
                amount_item = QTableWidgetItem(
                    CurrencyHelper.format_try_for_display(amount, include_try_reference=False)
                )
                amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if is_bold:
                    amount_item.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
                if color:
                    amount_item.setForeground(QColor(color))
                self.table.setItem(row, 1, amount_item)

        self.total_principal = total_principal
        self.total_savings = total_savings
        self.total_interest = total_interest
        self.total_tax = total_tax
        self.penalty_amount = penalty
        self.lbl_comparison.setText(f"AYEC Pro Finansal Zekasi: {self.get_smart_comparison(total_savings)}")

    def get_smart_comparison(self, savings_amount):
        laptop_price = 45000
        iphone_price = 95000
        car_downpayment = 500000

        if savings_amount > car_downpayment:
            return f"Bu tasarrufla tam {int(savings_amount / car_downpayment)} adet sifir arac pesinati odeyebilirdiniz!"
        if savings_amount > iphone_price:
            return f"Tam {int(savings_amount / iphone_price)} adet son model akilli telefon bedavaya geldi!"
        if savings_amount > laptop_price:
            return (
                f"Teknik servisiniz icin {int(savings_amount / laptop_price)} adet "
                "yuksek performansli laptop alabilirdiniz!"
            )
        return "Onemli bir faiz yukunden kurtuldunuz!"
