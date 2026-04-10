from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame, QDoubleSpinBox, QTableWidget, QHeaderView, QTableWidgetItem)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss, tc
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.premium_dialog import PremiumDialog
from datetime import datetime


class TaxAnalysisDialog(PremiumDialog):
    def __init__(self, finance_manager, parent=None):
        super().__init__("Vergi Hesaplama & Analiz (2026)", parent)
        self.finance_manager = finance_manager
        self.setMinimumSize(1200, 900)
        self.setMaximumSize(1600, 1040)
        self.resize(1320, 940)
        self.setup_ui()
        self.load_live_data()
        
    def setup_ui(self):
        # Header Info
        lbl_info = QLabel("Bu analiz, 2026 yılı Gelir Vergisi dilimlerine göre tahmini hesaplama yapar. KDV (%20) hem gelir hem de giderden ayrıştırılarak analiz edilmiştir.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; margin: 10px 0px 15px 0px; line-height: 1.4;"))
        self.body_layout.addWidget(lbl_info)
        
        # Main 2-Column Layout
        main_cols = QHBoxLayout()
        main_cols.setSpacing(15)
        
        # LEFT COLUMN - Inputs
        left_col = QFrame()
        left_col.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border-radius: 12px;
                border: 1px solid @border;
                padding: 15px;
            }
        """))
        left_layout = QVBoxLayout(left_col)
        left_layout.setSpacing(8)
        
        # Left column title
        lbl_left = QLabel("📊 Gelir ve Gider Bilgileri")
        lbl_left.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text; margin-bottom: 5px;"))
        left_layout.addWidget(lbl_left)
        
        # Input Rows - Interactive
        self.inp_income = self.create_input_row(left_layout, "Toplam Gelir (KDV Dahil)", tc("success"))
        self.lbl_vat_col = self.create_box_row(left_layout, "Tahsil Edilen KDV (%20)", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("accent"))
        
        sep1 = QFrame(); sep1.setFrameShape(QFrame.Shape.HLine); sep1.setStyleSheet(theme_qss("background-color: @border; min-height: 1px; max-height: 1px; border: none; margin: 5px 0px;"))
        left_layout.addWidget(sep1)
        
        self.inp_expense = self.create_input_row(left_layout, "Toplam Gider (KDV Dahil)", tc("danger"))
        self.lbl_expense_net = self.create_box_row(left_layout, "Gider (KDV Hariç)", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("danger"))
        self.lbl_vat_paid = self.create_box_row(left_layout, "Ödenen KDV (%20)", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("warning"))
        self.inp_cogs = self.create_input_row(left_layout, "SMM (Satılan Malın Maliyeti)", tc("danger"))
        
        left_layout.addStretch()
        
        # RIGHT COLUMN - Results (REMOVED card background for cleaner look)
        right_col = QFrame()
        right_col.setStyleSheet(theme_qss("""
            QFrame {
                background-color: transparent;
                border-radius: 8px;
                border: 1px solid @border;
                padding: 10px;
            }
        """))
        right_layout = QVBoxLayout(right_col)
        right_layout.setSpacing(8)
        
        # Right column title
        lbl_right = QLabel("💰 Vergi ve Net Kâr Hesaplaması")
        lbl_right.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text; margin-bottom: 5px;"))
        right_layout.addWidget(lbl_right)
        
        self.lbl_profit = self.create_box_row(right_layout, "Net Kâr (Vergi Matrahı)", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("text"), bold=True)
        self.lbl_vat_payable = self.create_box_row(right_layout, "Ödenecek KDV (Tahmini)", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("accent"), bold=True)
        
        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine); sep2.setStyleSheet(theme_qss("background-color: @border; min-height: 1px; max-height: 1px; border: none; margin: 5px 0px;"))
        right_layout.addWidget(sep2)
        
        self.lbl_tax = self.create_box_row(right_layout, "Hesaplanan Gelir Vergisi", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("warning"), bold=True)
        self.lbl_net = self.create_box_row(right_layout, "Vergi ve KDV Sonrası Net", CurrencyHelper.format_try_for_display(0, db=self.finance_manager.db, include_try_reference=False), tc("success"), bold=True, is_total=True)
        
        sep3 = QFrame(); sep3.setFrameShape(QFrame.Shape.HLine); sep3.setStyleSheet(theme_qss("background-color: @border; min-height: 1px; max-height: 1px; border: none; margin: 8px 0px;"))
        right_layout.addWidget(sep3)
        
        # Bracket Details in right column
        lbl_det = QLabel("Vergi Dilimleri Detayı")
        lbl_det.setStyleSheet(theme_qss("font-size: 13px; font-weight: 700; color: @text_muted; margin-top: 5px;"))
        right_layout.addWidget(lbl_det)
        
        self.tbl_details = QTableWidget()
        self.tbl_details.setColumnCount(3)
        self.tbl_details.setHorizontalHeaderLabels(["Dilim Tutarı", "Oran", "Ödenecek"])
        self.tbl_details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_details.verticalHeader().setVisible(False)
        self.tbl_details.setStyleSheet(theme_qss("""
            QTableWidget { border: 1px solid @border; border-radius: 8px; background-color: @surface; }
            QHeaderView::section { background-color: @surface_alt; padding: 8px; border-bottom: 1px solid @border; color: @selection_text; font-weight: bold; font-size: 11px; }
            QTableWidget::item { padding: 5px; font-size: 11px; }
        """))
        self.tbl_details.setWordWrap(True)
        self.tbl_details.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tbl_details.verticalHeader().setDefaultSectionSize(32)
        self.tbl_details.setMinimumHeight(280)
        right_layout.addWidget(self.tbl_details)
        
        # Add columns to main layout
        main_cols.addWidget(left_col)
        main_cols.addWidget(right_col)
        self.body_layout.addLayout(main_cols)
        
        # Actions at bottom
        actions = QHBoxLayout()
        self.btn_save = QPushButton("💾 Analizi Kaydet")
        self.btn_save.setFixedHeight(40)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss("background: @success; color: @selection_text; font-weight: bold; border-radius: 8px;"))
        self.btn_save.clicked.connect(self.save_report)
        self.btn_save.setEnabled(True)
        
        self.btn_reset = QPushButton("🔄 Verileri Yenile")
        self.btn_reset.setFixedHeight(40)
        self.btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reset.setStyleSheet(theme_qss("background: @text_muted; color: @selection_text; font-weight: bold; border-radius: 8px;"))
        self.btn_reset.clicked.connect(self.load_live_data)
        self.btn_reset.setEnabled(True)
        
        actions.addWidget(self.btn_reset)
        actions.addWidget(self.btn_save)
        self.body_layout.addLayout(actions)

        # Connect signals for real-time calculation
        self.inp_income.valueChanged.connect(self.calculate)
        self.inp_expense.valueChanged.connect(self.calculate)
        self.inp_cogs.valueChanged.connect(self.calculate)

    def create_input_row(self, layout, label, color):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(5, 2, 5, 2)
        
        box_label = QLabel(label)
        box_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; background: @surface; border: 1px solid @border; border-radius: 6px; padding: 8px 10px;"))
        box_label.setWordWrap(True)
        
        spinner = QDoubleSpinBox()
        spinner.setRange(0, 99999999)
        spinner.setDecimals(2)
        spinner.setGroupSeparatorShown(True)
        spinner.setSuffix(f" {CurrencyHelper.get_symbol(self.finance_manager.db, 'TRY')}")
        spinner.setStyleSheet(theme_qss(f"color: {color}; font-size: 13px; font-weight: 600; background: @surface; border: 1px solid {color}40; border-radius: 6px; padding: 8px 12px; min-width: 120px;"))
        spinner.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        row_layout.addWidget(box_label, 1)
        row_layout.addWidget(spinner, 0)
        layout.addLayout(row_layout)
        return spinner

    def create_box_row(self, layout, label, value, color, bold=False, is_total=False):
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(15, 2, 15, 2)
        
        box_label = QLabel(label)
        box_label.setStyleSheet(theme_qss(f"color: @text_muted; font-size: 14px; background: @surface; border: 1px solid @border; border-radius: 8px; padding: 10px 15px; min-width: 250px;"))
        
        if is_total: box_label.setStyleSheet(theme_qss(box_label.styleSheet() + "font-weight: 800; background: @surface_alt;"))
        
        box_value = QLabel(value)
        font_weight = "800" if (bold or is_total) else "600"
        box_value.setStyleSheet(theme_qss(f"color: {color}; font-size: 15px; font-weight: {font_weight}; background: @surface; border: 1px solid @border; border-radius: 8px; padding: 10px 20px; min-width: 150px;"))
        box_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        row_layout.addWidget(box_label)
        row_layout.addStretch()
        row_layout.addWidget(box_value)
        layout.addLayout(row_layout)
        return box_value

    def load_live_data(self):
        """Pull real data from FinanceManager as baseline"""
        summary = self.finance_manager.get_financial_summary("year")
        start, end = self.finance_manager._get_date_range("year")
        cogs = self.finance_manager.calculate_cogs(start, end)
        
        # Block signals to prevent redundant calculation during load
        self.inp_income.blockSignals(True)
        self.inp_expense.blockSignals(True)
        self.inp_cogs.blockSignals(True)
        
        self.inp_income.setValue(summary['revenue'])
        self.inp_expense.setValue(summary['expenses'])
        self.inp_cogs.setValue(cogs)
        
        self.inp_income.blockSignals(False)
        self.inp_expense.blockSignals(False)
        self.inp_cogs.blockSignals(False)
        
        self.calculate()

    def calculate(self):
        income = self.inp_income.value()
        expense = self.inp_expense.value()
        cogs_manual = self.inp_cogs.value()
        
        # Custom calculation using FinanceManager logic but with manual inputs
        # To avoid side effects, we temporarily override the COGS result if needed 
        # but FinanceManager logic is what we want.
        # We'll use calculate_income_tax provided in FinanceManager
        # but since that pulls its own COGS, we might want to pass it or have a variant.
        # For now, we'll use the logic directly or ensure FM can take these.
        
        # Quick fix: FinanceManager already has the logic, let's just use it and 
        # if COGS differs from what's in DB, we'll manually adjust the template.
        tax_res = self.finance_manager.calculate_income_tax(income, expense)
        
        # Override COGS with manual input if it's different from DB
        if cogs_manual != tax_res['cogs']:
            # Recalculate based on manual COGS
            profit = tax_res['income_excl_vat']-(tax_res['expense_excl_vat'] + cogs_manual)
            tax_res['profit_base'] = profit
            tax_res['cogs'] = cogs_manual
            # Recalculate brackets and tax locally if needed or just re-run FM logic
            # Actually FM logic is perfect, but it pulls COGS. 
            # Let's adjust slightly:
            if profit <= 0:
                tax_res['tax'] = 0.0
                tax_res['brackets'] = []
            else:
                # Recalculate progressive tax for the new matrah
                tax_res.update(self.recalc_tax_only(profit))
            
            # Re-update net after tax
            tax_res['net_after_tax'] = profit - tax_res['tax'] - tax_res['vat_payable']

        # Update UI
        self.lbl_vat_col.setText(CurrencyHelper.format_try_for_display(tax_res['vat_collected'], db=self.finance_manager.db, include_try_reference=False))
        self.lbl_expense_net.setText(CurrencyHelper.format_try_for_display(tax_res['expense_excl_vat'], db=self.finance_manager.db, include_try_reference=False))
        self.lbl_vat_paid.setText(CurrencyHelper.format_try_for_display(tax_res['vat_paid'], db=self.finance_manager.db, include_try_reference=False))
        
        profit = tax_res['profit_base']
        pref = "" if profit >= 0 else "- "
        self.lbl_profit.setText(f"{pref}{CurrencyHelper.format_try_for_display(abs(profit), db=self.finance_manager.db, include_try_reference=False)}")
        self.lbl_profit.setStyleSheet(theme_qss(self.lbl_profit.styleSheet() + f"color: {tc('text') if profit >= 0 else tc('danger')};"))
        
        self.lbl_vat_payable.setText(CurrencyHelper.format_try_for_display(tax_res['vat_payable'], db=self.finance_manager.db, include_try_reference=False))
        self.lbl_tax.setText(CurrencyHelper.format_try_for_display(tax_res['tax'], db=self.finance_manager.db, include_try_reference=False))
        
        net = tax_res['net_after_tax']
        pref_n = "" if net >= 0 else "- "
        self.lbl_net.setText(f"{pref_n}{CurrencyHelper.format_try_for_display(abs(net), db=self.finance_manager.db, include_try_reference=False)}")
        self.lbl_net.setStyleSheet(theme_qss(self.lbl_net.styleSheet() + f"color: {tc('success') if net >= 0 else tc('danger')};"))
        
        # Brackets Table
        self.tbl_details.setRowCount(0)
        if profit <= 0:
            self.tbl_details.insertRow(0)
            item = QTableWidgetItem("Zarar durumunda vergi hesaplanmaz")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tbl_details.setItem(0, 0, item)
            self.tbl_details.setSpan(0, 0, 1, 3)
        else:
            for b in tax_res['brackets']:
                row = self.tbl_details.rowCount()
                self.tbl_details.insertRow(row)
                self.tbl_details.setItem(row, 0, QTableWidgetItem(CurrencyHelper.format_try_for_display(b['base'], db=self.finance_manager.db, include_try_reference=False)))
                self.tbl_details.setItem(row, 1, QTableWidgetItem(f"%{int(round(b['rate']*100,0))}"))
                self.tbl_details.setItem(row, 2, QTableWidgetItem(CurrencyHelper.format_try_for_display(b['tax'], db=self.finance_manager.db, include_try_reference=False)))
        self.tbl_details.resizeRowsToContents()

        self.last_result = tax_res # Cache for saving

    def recalc_tax_only(self, profit):
        tax_total = 0.0
        remaining = profit
        breakdown = []
        brackets = [(158000, 0.15), (330000-158000, 0.20), (800000-330000, 0.27), (4300000-800000, 0.35), (float('inf'), 0.40)]
        for limit, rate in brackets:
            if remaining <= 0: break
            taxable = min(remaining, limit)
            chunk = taxable * rate
            tax_total += chunk
            remaining -= taxable
            breakdown.append({"base": taxable, "rate": rate, "tax": chunk})
        return {"tax": tax_total, "brackets": breakdown}

    def save_report(self):
        try:
            res = self.last_result
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.finance_manager.db.cursor.execute("""
                CREATE TABLE IF NOT EXISTS financial_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period_year INTEGER,
                    total_income REAL,
                    total_expense REAL,
                    cogs REAL,
                    taxable_income REAL,
                    calculated_tax REAL,
                    payable_vat REAL,
                    net_profit REAL,
                    created_at TEXT
                )
            """)
            self.finance_manager.db.cursor.execute("""
                INSERT INTO financial_reports 
                (period_year, total_income, total_expense, cogs, taxable_income, calculated_tax, payable_vat, net_profit, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (2026, res['income_excl_vat'], res['expense_excl_vat'], res['cogs'], res['profit_base'], res['tax'], res['vat_payable'], res['net_after_tax'], created_at))
            self.finance_manager.db.conn.commit()
            PremiumDialog.success("Analiz başarıyla kaydedildi!", self)
        except Exception as e:
            PremiumDialog.error(f"Kayıt Hatası: {e}", self)
