"""Live income and expense workspace for the shared finance shell."""

from collections import defaultdict
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QBoxLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QProgressBar, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from src.ui.pages.accounting_dialogs.add_expense_dialog import AddExpenseDialog
from src.ui.pages.accounting_dialogs.add_income_dialog import AddIncomeDialog
from src.utils.finance_manager import FinanceManager
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success, show_warning


BG = "@window"
PANEL = "@surface"
FIELD = "@surface_alt"
TEXT = "@text"
MUTED = "@text_muted"
BORDER = "@border"
BLUE = "#2563eb"
GREEN = "#047857"
RED = "#b42318"


class IncomeExpensePage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.finance_manager = FinanceManager(db)
        self._rows = []
        self._receipt_path = None
        self._build_ui()
        if main_window and hasattr(main_window, "financial_data_changed"):
            main_window.financial_data_changed.connect(self.refresh_data)
        self.refresh_data()

    def _label(self, value, size=12, color=None, bold=False):
        label = QLabel(value)
        color = color or TEXT
        label.setStyleSheet(theme_qss(
            f"background:transparent;border:0;color:{color};font-size:{size}px;"
            f"font-weight:{700 if bold else 400};"
        ))
        return label

    def _button(self, value, color=FIELD):
        button = QPushButton(value)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(30)
        button.setStyleSheet(theme_qss(
            f"QPushButton{{background:{color};color:{TEXT};border:0;"
            "border-radius:3px;padding:5px 10px;font-weight:600;}"
            "QPushButton:hover{background:@selection_bg;color:@selection_text;}"
        ))
        return button

    def _panel(self):
        panel = QFrame()
        panel.setObjectName("incomeExpensePanel")
        panel.setStyleSheet(theme_qss(
            "QFrame#incomeExpensePanel{background:@surface;border:1px solid @border;}"
        ))
        return panel

    def _build_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss(
            "QWidget{background-color:@window;color:@text;}"
            "QLineEdit,QComboBox,QDateEdit,QDoubleSpinBox{background:@surface;"
            "color:@text;border:1px solid @border;padding:5px;min-height:22px;}"
            "QComboBox QAbstractItemView{background:@surface;color:@text;}"
            "QDoubleSpinBox::up-button,QDoubleSpinBox::down-button{width:0;}"
        ))
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(10)

        header = QHBoxLayout()
        heading = QVBoxLayout()
        heading.setSpacing(1)
        heading.addWidget(self._label("Gelir & Gider Y\u00f6netimi", 21, TEXT, True))
        heading.addWidget(self._label(
            "Kasa, fatura ve operasyonel gider hareketleri", 11, MUTED
        ))
        header.addLayout(heading, 1)
        close_period = self._button("Mali D\u00f6nem Kapatma", FIELD)
        close_period.clicked.connect(self._open_dashboard)
        header.addWidget(close_period)
        report = self._button("Raporu D\u0131\u015fa Aktar", FIELD)
        report.clicked.connect(self._export_visible_rows)
        header.addWidget(report)
        income = self._button("Yeni Gelir", GREEN)
        income.clicked.connect(self._open_income)
        header.addWidget(income)
        expense = self._button("Yeni Gider", RED)
        expense.clicked.connect(self._open_expense)
        header.addWidget(expense)
        root.addLayout(header)
        root.addSpacing(7)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_values = {}
        for key, title, color, detail, glyph in (
            ("gross_revenue", "TOPLAM AYLIK GEL\u0130R", GREEN, "Bu ay kaydedilen gelir", "\u2197"),
            ("expenses", "TOPLAM G\u0130DER & MASRAF", RED, "Operasyonel gider toplam\u0131", "\u25a4"),
            ("pocket_net", "NET \u0130\u015eLETME KARI", GREEN, "Gelir - gider net", "\u25a3"),
            ("pending", "BEKLEYEN ALACAKLAR", RED, "Tahsil edilmemi\u015f bakiye", "!"),
        ):
            card = self._panel()
            card.setFixedHeight(133)
            body = QVBoxLayout(card)
            body.setContentsMargins(12, 11, 12, 10)
            title_row = QHBoxLayout()
            title_row.addWidget(self._label(title, 10, MUTED, True), 1)
            title_row.addWidget(self._label(glyph, 16, color, True))
            body.addLayout(title_row)
            amount = self._label("-", 23, color, True)
            body.addWidget(amount)
            if key == "expenses":
                self.expense_ratio = QProgressBar()
                self.expense_ratio.setRange(0, 100)
                self.expense_ratio.setTextVisible(False)
                self.expense_ratio.setFixedHeight(5)
                self.expense_ratio.setStyleSheet(theme_qss(
                    f"QProgressBar{{background:{FIELD};border:0;}}"
                    f"QProgressBar::chunk{{background:{RED};}}"
                ))
                body.addWidget(self.expense_ratio)
            body.addStretch()
            body.addWidget(self._label(detail, 10, MUTED))
            self.metric_values[key] = amount
            metrics.addWidget(card, 1)
        root.addLayout(metrics)
        root.addSpacing(3)

        content = QHBoxLayout()
        content.setSpacing(9)
        left = QVBoxLayout()
        left.setSpacing(7)
        filters = QHBoxLayout()
        filters.setSpacing(3)
        self.filter_buttons = []
        for title, kind in (
            ("T\u00fcm Hareketler", "all"),
            ("Gider / Masraflar", "expense"),
            ("Tahsilatlar & Gelirler", "income"),
            ("Vergi & SGK", "tax"),
            ("Personel Harcamalar\u0131", "personnel"),
        ):
            button = self._button(title)
            button.setCheckable(True)
            button.clicked.connect(self._apply_filters)
            button.setProperty("filter_kind", kind)
            self.filter_buttons.append(button)
            filters.addWidget(button)
        self.filter_buttons[0].setChecked(True)
        for button in self.filter_buttons:
            button.setStyleSheet(theme_qss(
                f"QPushButton{{background:{PANEL};color:{MUTED};border:0;"
                "padding:5px 8px;font-weight:600;}"
                "QPushButton:checked{background:@selection_bg;color:@selection_text;}"
            ))
        filters.addStretch()
        left.addLayout(filters)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Fi\u015f no, tedarik\u00e7i, gider veya a\u00e7\u0131klama ara...")
        self.search.textChanged.connect(self._apply_filters)
        search_row.addWidget(self.search, 1)
        self.month = QComboBox()
        self.month.addItem("Bu Y\u0131l", 0)
        for month in range(1, 13):
            self.month.addItem(f"{month:02d} / {QDate.currentDate().year()}", month)
        self.month.setCurrentIndex(QDate.currentDate().month())
        self.month.currentIndexChanged.connect(self._apply_filters)
        search_row.addWidget(self.month)
        left.addLayout(search_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "TAR\u0130H / SAAT", "KATEGOR\u0130", "A\u00c7IKLAMA & CAR\u0130",
            "BELGE / NO", "\u00d6DEME KANALI",
        ])
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setShowGrid(False)
        self.table.cellDoubleClicked.connect(self._export_row_receipt)
        self.table.setFixedHeight(445)
        self.table.setStyleSheet(theme_qss(
            f"QTableWidget{{background:{PANEL};alternate-background-color:{BG};"
            f"color:{TEXT};border:1px solid {BORDER};gridline-color:{BORDER};}}"
            f"QHeaderView::section{{background:{FIELD};color:{MUTED};border:0;"
            "padding:10px 5px;font-size:10px;font-weight:700;}"
            f"QTableWidget::item{{padding:7px 5px;border:0;color:{TEXT};background-color:{PANEL};}}"
            f"QTableWidget::item:alternate{{background-color:{BG};color:{TEXT};}}"
            "QTableWidget::item:selected{background-color:@selection_bg;color:@selection_text;}"
            "QTableWidget::item:hover{background-color:@surface_alt;color:@text;}"
        ))
        header_view = self.table.horizontalHeader()
        for column in (0, 1, 3):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 132)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        left.addWidget(self.table)
        self.count_label = self._label("", 11, MUTED)
        left.addWidget(self.count_label)
        left.addStretch()
        content.addLayout(left, 7)

        right = QVBoxLayout()
        right.setSpacing(8)
        distribution = self._panel()
        distribution.setFixedHeight(210)
        dist_layout = QVBoxLayout(distribution)
        dist_layout.setContentsMargins(10, 10, 10, 9)
        dist_layout.addWidget(self._label("Gider Da\u011f\u0131l\u0131m\u0131", 14, TEXT, True))
        self.distribution_rows = QVBoxLayout()
        self.distribution_rows.setSpacing(5)
        dist_layout.addLayout(self.distribution_rows)
        dist_layout.addStretch()
        right.addWidget(distribution)

        quick = self._panel()
        quick.setMaximumHeight(420)
        quick_layout = QVBoxLayout(quick)
        quick_layout.setContentsMargins(10, 10, 10, 10)
        quick_layout.setSpacing(6)
        quick_layout.addWidget(self._label("H\u0131zl\u0131 Masraf / Gider Fi\u015fi", 14, TEXT, True))
        quick_layout.addWidget(self._label("Masraf Kategorisi", 10, MUTED))
        self.category = QComboBox()
        self.category.setEditable(True)
        self.category.addItems([
            "D\u00fckkan Kiras\u0131", "Fatura (Elektrik/Su)", "Personel",
            "Yemek", "Malzeme", "Vergi", "Di\u011fer",
        ])
        quick_layout.addWidget(self.category)
        quick_layout.addWidget(self._label("\u00c7\u0131k\u0131\u015f Hesab\u0131", 10, MUTED))
        self.bank = QComboBox()
        quick_layout.addWidget(self.bank)
        form_row = QHBoxLayout()
        self.expense_form_row = form_row
        amount_col = QVBoxLayout()
        amount_col.addWidget(self._label("Tutar", 10, MUTED))
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1_000_000_000)
        self.amount.setDecimals(2)
        amount_col.addWidget(self.amount)
        form_row.addLayout(amount_col, 1)
        ref_col = QVBoxLayout()
        ref_col.addWidget(self._label("Fi\u015f / Fatura No", 10, MUTED))
        self.reference = QLineEdit()
        ref_col.addWidget(self.reference)
        form_row.addLayout(ref_col, 1)
        quick_layout.addLayout(form_row)
        self._update_expense_form_orientation()
        receipt = self._button("Fi\u015f / Fatura G\u00f6rseli\nDosyay\u0131 se\u00e7in (JPG, PNG, PDF)", FIELD)
        receipt.setMinimumHeight(68)
        receipt.clicked.connect(self._select_receipt)
        quick_layout.addWidget(receipt)
        self.receipt_label = self._label("Dosya se\u00e7ilmedi", 10, MUTED)
        quick_layout.addWidget(self.receipt_label)
        save = self._button("Fi\u015fi Kaydet", RED)
        save.clicked.connect(self._save_expense)
        quick_layout.addWidget(save)
        right.addWidget(quick)
        right.addStretch()
        content.addLayout(right, 3)
        root.addLayout(content, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_expense_form_orientation()

    def _update_expense_form_orientation(self):
        form_row = getattr(self, "expense_form_row", None)
        if form_row is None:
            return
        direction = (
            QBoxLayout.Direction.TopToBottom
            if self.width() < 1500
            else QBoxLayout.Direction.LeftToRight
        )
        if form_row.direction() != direction:
            form_row.setDirection(direction)

    def _currency(self, amount):
        return f"\u20ba{float(amount or 0):,.2f}"

    def _load_banks(self):
        current = self.bank.currentData()
        self.bank.clear()
        self._bank_names = {}
        self.bank.addItem("Hesap se\u00e7in", None)
        try:
            accounts = self.db.get_bank_accounts() or []
        except Exception:
            accounts = []
        for account in accounts:
            active = AddExpenseDialog._bank_field(account, "is_active", 7, 0)
            if int(active or 0) != 1:
                continue
            bank_id = AddExpenseDialog._bank_field(account, "id", 0)
            name = AddExpenseDialog._bank_field(account, "bank_name", 1, "")
            holder = AddExpenseDialog._bank_field(account, "account_holder", 2, "")
            label = f"{name} - {holder}".strip(" -")
            self._bank_names[bank_id] = label
            self.bank.addItem(label, bank_id)
            if bank_id == current:
                self.bank.setCurrentIndex(self.bank.count() - 1)

    def refresh_data(self):
        self._load_banks()
        try:
            summary = self.finance_manager.get_financial_summary("month")
            self._rows = self.finance_manager.get_unified_ledger(
                limit=3000, period="year"
            ) or []
        except Exception as exc:
            show_error(self, f"Finans verileri okunamad\u0131: {exc}")
            return
        for key, label in self.metric_values.items():
            label.setText(self._currency(summary.get(key)))
        gross = float(summary.get("gross_revenue") or 0)
        expense = float(summary.get("expenses") or 0)
        self.expense_ratio.setValue(min(100, round(expense / gross * 100)) if gross else 0)
        self._apply_filters()

    def _visible_rows(self):
        month = self.month.currentData()
        search = self.search.text().strip().casefold()
        chosen = next((b.property("filter_kind") for b in self.filter_buttons if b.isChecked()), "all")
        for row in self._rows:
            date = str(row.get("date") or "")
            if month:
                try:
                    if datetime.fromisoformat(date[:10]).month != month:
                        continue
                except ValueError:
                    continue
            kind = str(row.get("type_label") or "").casefold()
            category = str(row.get("category") or "").casefold()
            is_expense = row.get("color_code") == "red" or "gider" in kind
            if chosen == "expense" and not is_expense:
                continue
            if chosen == "income" and is_expense:
                continue
            if chosen == "tax" and not any(term in category for term in ("vergi", "sgk", "kdv")):
                continue
            if chosen == "personnel" and not any(term in category for term in ("personel", "maa", "prim")):
                continue
            searchable = " ".join(str(row.get(field) or "") for field in (
                "date", "category", "description", "customer_name", "ref_no", "id"
            )).casefold()
            if search and search not in searchable:
                continue
            yield row

    def _apply_filters(self):
        sender = self.sender()
        if sender in self.filter_buttons:
            for button in self.filter_buttons:
                button.setChecked(button is sender)
        rows = list(self._visible_rows())
        self._display_rows = rows
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            raw_date = str(row.get("date") or "")
            try:
                parsed = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                date = parsed.strftime("%d.%m.%Y")
                if len(raw_date) > 10:
                    date += "\n" + parsed.strftime("%H:%M")
            except ValueError:
                date = raw_date[:16].replace("T", " ")
            expense = row.get("color_code") == "red" or "Gider" in str(row.get("type_label"))
            amount_text = ("-" if expense else "+") + self._currency(row.get("amount_try"))
            payment = self._bank_names.get(row.get("bank_account_id")) or str(
                row.get("payment_method") or ""
            )
            values = (
                date, str(row.get("category") or row.get("type_label") or ""),
                str(row.get("description") or ""), str(row.get("ref_no") or ""),
                f"{payment}\n{amount_text}" if payment else amount_text,
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 4:
                    item.setForeground(Qt.GlobalColor.red if expense else Qt.GlobalColor.green)
                self.table.setItem(index, column, item)
            self.table.setRowHeight(index, 58)
        self.count_label.setText(f"{len(rows)} hareket listeleniyor")
        self._render_distribution(rows)

    def _render_distribution(self, rows):
        while self.distribution_rows.count():
            item = self.distribution_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        totals = defaultdict(float)
        for row in rows:
            if row.get("color_code") == "red" or "Gider" in str(row.get("type_label")):
                totals[str(row.get("category") or "Di\u011fer")] += float(row.get("amount_try") or 0)
        total = sum(totals.values())
        for index, (category, amount) in enumerate(
            sorted(totals.items(), key=lambda pair: -pair[1])[:5]
        ):
            color = (BLUE, RED, GREEN, "#7284a8", "#9ba7c2")[index]
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self._label(category, 10, TEXT), 1)
            row.addWidget(self._label(
                f"{self._currency(amount)} ({amount / total * 100:.1f}%)" if total else "",
                10, MUTED
            ))
            layout.addLayout(row)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(round(amount / total * 100) if total else 0)
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setStyleSheet(theme_qss(
                f"QProgressBar{{background:{FIELD};border:0;}}"
                f"QProgressBar::chunk{{background:{color};}}"
            ))
            layout.addWidget(bar)
            self.distribution_rows.addWidget(container)
        if not totals:
            self.distribution_rows.addWidget(self._label("Bu d\u00f6nemde gider yok", 11, MUTED))

    def _open_dashboard(self):
        if self.main_window and hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(100)

    def _open_income(self):
        if AddIncomeDialog(self.db, self).exec():
            self.refresh_data()

    def _open_expense(self):
        if AddExpenseDialog(self.db, self).exec():
            self.refresh_data()

    def _select_receipt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Fi\u015f / Fatura", "", "Files (*.jpg *.jpeg *.png *.pdf)"
        )
        if path:
            self._receipt_path = path
            self.receipt_label.setText(Path(path).name)

    def _receipt_bytes(self):
        if not self._receipt_path:
            return None
        path = Path(self._receipt_path)
        mime_types = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".pdf": "application/pdf",
        }
        mime_type = mime_types.get(path.suffix.lower())
        if not mime_type or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("JPG, PNG veya PDF dosyas\u0131 se\u00e7in (en fazla 5 MB).")
        return path.name, mime_type, path.read_bytes()

    def _save_receipt(self, transaction_id, receipt):
        filename, mime_type, content = receipt
        self.db.cursor.execute(
            "CREATE TABLE IF NOT EXISTS accounting_receipts ("
            "accounting_id INTEGER PRIMARY KEY, filename TEXT NOT NULL, "
            "mime_type TEXT NOT NULL, content BLOB NOT NULL, "
            "created_at TEXT NOT NULL)"
        )
        self.db.cursor.execute(
            "INSERT INTO accounting_receipts "
            "(accounting_id, filename, mime_type, content, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (transaction_id, filename, mime_type, content, datetime.now().isoformat()),
        )
        self.db.conn.commit()

    def _export_row_receipt(self, row_index, _column):
        if row_index >= len(getattr(self, "_display_rows", [])):
            return
        row = self._display_rows[row_index]
        if row.get("source") != "accounting" or not row.get("id"):
            return
        try:
            self.db.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='accounting_receipts'"
            )
            if not self.db.cursor.fetchone():
                return
            self.db.cursor.execute(
                "SELECT filename, content FROM accounting_receipts WHERE accounting_id=?",
                (row["id"],),
            )
            receipt = self.db.cursor.fetchone()
            if not receipt:
                return
            path, _ = QFileDialog.getSaveFileName(self, "Fi\u015fi Kaydet", receipt[0])
            if path:
                Path(path).write_bytes(receipt[1])
                show_success(self, "Fi\u015f kaydedildi.")
        except Exception as exc:
            show_error(self, f"Fi\u015f okunamad\u0131: {exc}")

    def _save_expense(self):
        if self.bank.currentData() is None:
            show_warning(self, "Banka hesab\u0131 se\u00e7in.")
            return
        if self.amount.value() <= 0:
            show_warning(self, "S\u0131f\u0131rdan b\u00fcy\u00fck tutar girin.")
            return
        reference = self.reference.text().strip()
        description = reference or self.category.currentText().strip()
        try:
            receipt = self._receipt_bytes()
        except (OSError, ValueError) as exc:
            show_warning(self, str(exc))
            return
        try:
            transaction_id = self.db.add_transaction(
                t_type="Gider", category=self.category.currentText().strip(),
                amount=self.amount.value(), description=description,
                date=QDate.currentDate().toString("yyyy-MM-dd"),
                payment_method="Banka", bank_account_id=self.bank.currentData(),
                currency="TRY", original_amount=self.amount.value(),
                ref_no=reference or None,
            )
        except Exception as exc:
            show_error(self, f"Gider kaydedilemedi: {exc}")
            return
        if receipt:
            try:
                if transaction_id is None:
                    raise RuntimeError("Kay\u0131t numaras\u0131 al\u0131namad\u0131.")
                self._save_receipt(transaction_id, receipt)
            except Exception as exc:
                show_error(self, f"Gider kaydedildi, ancak fi\u015f eklenemedi: {exc}")
                return
        self.amount.setValue(0)
        self.reference.clear()
        self._receipt_path = None
        self.receipt_label.setText("Dosya se\u00e7ilmedi")
        self.refresh_data()
        if self.main_window and hasattr(self.main_window, "financial_data_changed"):
            self.main_window.financial_data_changed.emit()
        show_success(self, "Gider kaydedildi.")

    def _export_visible_rows(self):
        from csv import writer

        path, _ = QFileDialog.getSaveFileName(self, "D\u0131\u015fa Aktar", "gelir_gider.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                output = writer(handle)
                output.writerow(["Date", "Category", "Description", "Reference", "Amount TRY"])
                for row in self._visible_rows():
                    output.writerow([
                        row.get("date"), row.get("category"), row.get("description"),
                        row.get("ref_no"), row.get("amount_try"),
                    ])
        except OSError as exc:
            show_error(self, f"Dosya yaz\u0131lamad\u0131: {exc}")
            return
        show_success(self, "Rapor kaydedildi.")
