from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.income_tax_tariff_service import IncomeTaxTariffService
from src.utils.theme_colors import tc, theme_qss


class TaxAnalysisDialog(PremiumDialog):
    def __init__(self, finance_manager, parent=None):
        super().__init__("Vergi Dilimi Hesaplama", parent)
        self.finance_manager = finance_manager
        self.tariff_service = IncomeTaxTariffService()
        self.last_result = None
        self.setMinimumSize(960, 660)
        self.resize(1080, 720)
        self.setup_ui()
        self.load_live_data()

    def _format_money(self, amount):
        return CurrencyHelper.format_amount(
            float(amount or 0), db=self.finance_manager.db, currency_code="TRY"
        )

    def setup_ui(self):
        intro = QLabel(
            "Gelir vergisi, resmi G\u0130B tarifesine g\u00f6re kademeli olarak hesaplan\u0131r. "
            "Sonu\u00e7lar tahminidir; beyanname ve mali m\u00fc\u015favir kontrol\u00fcn\u00fcn "
            "yerine ge\u00e7mez."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(theme_qss(
            "color: @text_muted; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 8px; padding: 12px; font-size: 12px;"
        ))
        self.body_layout.addWidget(intro)

        controls = QFrame()
        controls.setStyleSheet(theme_qss(
            "QFrame { background: @surface_alt; border: 1px solid @border; "
            "border-radius: 8px; } QLabel { border: none; background: transparent; }"
        ))
        grid = QGridLayout(controls)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)

        grid.addWidget(QLabel("Tarife Y\u0131l\u0131"), 0, 0)
        self.cmb_year = QComboBox()
        for year in self.tariff_service.available_years():
            self.cmb_year.addItem(str(year), year)
        current_index = self.cmb_year.findData(datetime.now().year)
        if current_index >= 0:
            self.cmb_year.setCurrentIndex(current_index)
        grid.addWidget(self.cmb_year, 1, 0)

        grid.addWidget(QLabel("Gelir T\u00fcr\u00fc"), 0, 1)
        self.cmb_income_type = QComboBox()
        self.cmb_income_type.addItem("\u00dccret D\u0131\u015f\u0131 Gelir", "non_wage")
        self.cmb_income_type.addItem("\u00dccret Geliri", "wage")
        grid.addWidget(self.cmb_income_type, 1, 1)

        grid.addWidget(QLabel("Gelir (TRY)"), 2, 0)
        self.inp_income = self._money_input()
        grid.addWidget(self.inp_income, 3, 0)

        grid.addWidget(QLabel("Gider (TRY)"), 2, 1)
        self.inp_expense = self._money_input()
        grid.addWidget(self.inp_expense, 3, 1)

        grid.addWidget(QLabel("SMM / Maliyet (TRY)"), 4, 0)
        self.inp_cogs = self._money_input()
        grid.addWidget(self.inp_cogs, 5, 0)

        grid.addWidget(QLabel("Mahsup Edilecek Vergi (TRY)"), 4, 1)
        self.inp_withheld = self._money_input()
        grid.addWidget(self.inp_withheld, 5, 1)
        self.body_layout.addWidget(controls)

        summary = QFrame()
        summary.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-radius: 8px; }"
        ))
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(12, 12, 12, 12)
        self.lbl_base = self._summary_item(summary_layout, "Vergi Matrah\u0131", tc("text"))
        self.lbl_tax = self._summary_item(summary_layout, "Hesaplanan Vergi", tc("warning"))
        self.lbl_payable = self._summary_item(summary_layout, "\u00d6denecek Vergi", tc("danger"))
        self.lbl_effective = self._summary_item(summary_layout, "Efektif Oran", tc("accent"))
        self.body_layout.addWidget(summary)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Dilim", "Oran", "Bu Dilimdeki Matrah", "Dilim Vergisi", "Kalan Matrah"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { background: @surface; border: 1px solid @border; "
            "border-radius: 8px; gridline-color: @border; } "
            "QHeaderView::section { background: @surface_alt; color: @text; "
            "font-weight: 700; padding: 8px; border: none; border-bottom: 1px solid @border; }"
        ))
        self.body_layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.lbl_source = QLabel()
        self.lbl_source.setWordWrap(True)
        self.lbl_source.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        footer.addWidget(self.lbl_source, 1)
        self.btn_reload = QPushButton("Finans Verilerini Yenile")
        self.btn_reload.clicked.connect(self.load_live_data)
        self.btn_save = QPushButton("Analizi Kaydet")
        self.btn_save.clicked.connect(self.save_report)
        for button, color in ((self.btn_reload, "#0284c7"), (self.btn_save, "#10b981")):
            button.setMinimumHeight(40)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                f"background: {color}; color: @selection_text; border: none; "
                "border-radius: 8px; padding: 8px 16px; font-weight: 700;"
            ))
            footer.addWidget(button)
        self.body_layout.addLayout(footer)

        self.cmb_year.currentIndexChanged.connect(self.calculate)
        self.cmb_income_type.currentIndexChanged.connect(self.calculate)
        self.inp_income.valueChanged.connect(self.calculate)
        self.inp_expense.valueChanged.connect(self.calculate)
        self.inp_cogs.valueChanged.connect(self.calculate)
        self.inp_withheld.valueChanged.connect(self.calculate)

    def _money_input(self):
        spinner = QDoubleSpinBox()
        spinner.setRange(0, 999999999999.99)
        spinner.setDecimals(2)
        spinner.setGroupSeparatorShown(True)
        spinner.setSuffix(" TL")
        spinner.setAlignment(Qt.AlignmentFlag.AlignRight)
        spinner.setMinimumHeight(40)
        spinner.setStyleSheet(theme_qss(
            "QDoubleSpinBox { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 7px; padding: 7px 10px; font-weight: 600; }"
        ))
        return spinner

    def _summary_item(self, layout, title, color):
        frame = QFrame()
        frame.setStyleSheet(theme_qss(
            "QFrame { background: @surface_alt; border: 1px solid @border; border-radius: 7px; }"
        ))
        item_layout = QVBoxLayout(frame)
        item_layout.setContentsMargins(10, 8, 10, 8)
        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 11px;"))
        value_label = QLabel(self._format_money(0))
        value_label.setStyleSheet(theme_qss(
            f"color: {color}; border: none; font-size: 15px; font-weight: 800;"
        ))
        item_layout.addWidget(title_label)
        item_layout.addWidget(value_label)
        layout.addWidget(frame, 1)
        return value_label

    def load_live_data(self):
        try:
            summary = self.finance_manager.get_financial_summary("year") or {}
            start, end = self.finance_manager._get_date_range("year")
            values = (
                (self.inp_income, float(summary.get("revenue", 0) or 0)),
                (self.inp_expense, float(summary.get("expenses", 0) or 0)),
                (self.inp_cogs, float(self.finance_manager.calculate_cogs(start, end) or 0)),
            )
            for widget, value in values:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
            self.calculate()
        except Exception as exc:
            PremiumDialog.error(f"Vergi verileri y\u00fcklenemedi: {exc}", self)

    def calculate(self, *args):
        try:
            tax_base = max(
                0.0,
                self.inp_income.value() - self.inp_expense.value() - self.inp_cogs.value(),
            )
            year = self.cmb_year.currentData()
            income_type = self.cmb_income_type.currentData() or "non_wage"
            result = self.tariff_service.calculate(tax_base, year, income_type)
            withheld = min(self.inp_withheld.value(), result["tax"])
            payable = max(0.0, result["tax"] - withheld)
            result["withheld"] = withheld
            result["payable"] = payable
            result["net_after_tax"] = tax_base - result["tax"]
            self.last_result = result

            self.lbl_base.setText(self._format_money(tax_base))
            self.lbl_tax.setText(self._format_money(result["tax"]))
            self.lbl_payable.setText(self._format_money(payable))
            effective = (result["tax"] / tax_base * 100.0) if tax_base else 0.0
            self.lbl_effective.setText(f"%{effective:.2f}")
            self._fill_table(result)

            updated = result.get("updated_at") or "yerle\u015fik do\u011frulanm\u0131\u015f veri"
            self.lbl_source.setText(
                f"Kaynak: {result.get('source') or 'G\u0130B'} | Son g\u00fcncelleme: {updated} | "
                "Otomatik kontrol: program a\u00e7\u0131ld\u0131ktan 10 dakika sonra, g\u00fcnde bir kez"
            )
        except Exception as exc:
            PremiumDialog.error(f"Vergi hesaplama hatas\u0131: {exc}", self)

    def _fill_table(self, result):
        self.table.setRowCount(0)
        remaining = result["tax_base"]
        for bracket in result["brackets"]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            lower = bracket["lower"]
            upper = bracket["upper"]
            band = (
                f"{self._format_money(lower)} - {self._format_money(upper)}"
                if upper is not None
                else f"{self._format_money(lower)} \u00fczeri"
            )
            remaining = max(0.0, remaining - bracket["base"])
            values = [
                band,
                f"%{int(bracket['rate'] * 100)}",
                self._format_money(bracket["base"]),
                self._format_money(bracket["tax"]),
                self._format_money(remaining),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row, column, item)

    def save_report(self):
        result = self.last_result or {}
        if not result:
            PremiumDialog.error("Kaydedilecek analiz verisi yok.", self)
            return
        try:
            cursor = self.finance_manager.db.cursor
            cursor.execute(
                """
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
                    created_at TEXT,
                    income_type TEXT,
                    withheld_tax REAL DEFAULT 0,
                    payable_tax REAL DEFAULT 0
                )
                """
            )
            columns = {
                row[1] for row in cursor.execute("PRAGMA table_info(financial_reports)").fetchall()
            }
            for name, sql_type in (
                ("income_type", "TEXT"),
                ("withheld_tax", "REAL DEFAULT 0"),
                ("payable_tax", "REAL DEFAULT 0"),
            ):
                if name not in columns:
                    cursor.execute(f"ALTER TABLE financial_reports ADD COLUMN {name} {sql_type}")
            cursor.execute(
                """
                INSERT INTO financial_reports
                (period_year, total_income, total_expense, cogs, taxable_income,
                 calculated_tax, payable_vat, net_profit, created_at, income_type,
                 withheld_tax, payable_tax)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result["year"],
                    self.inp_income.value(),
                    self.inp_expense.value(),
                    self.inp_cogs.value(),
                    result["tax_base"],
                    result["tax"],
                    0.0,
                    result["net_after_tax"],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    result["income_type"],
                    result["withheld"],
                    result["payable"],
                ),
            )
            self.finance_manager.db.conn.commit()
            PremiumDialog.success("Vergi analizi kaydedildi.", self)
        except Exception as exc:
            PremiumDialog.error(f"Kay\u0131t hatas\u0131: {exc}", self)
