# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QDialog as QtDialog,
                             QFormLayout, QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox,
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame,
                             QSpinBox, QAbstractSpinBox, QScrollArea, QToolButton, QAbstractItemView, QMenu,
                             QGridLayout, QInputDialog, QProgressDialog, QApplication,
                             QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QColor, QFont, QAction
import json
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error
from src.utils.language_manager import LanguageManager
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.ui.dialogs.base_modern_dialog import BaseModernDialog

from src.ui.pages.project_management.project_detail_dialogs import AddUnitDialog, AddSubDialog


class FinanceTab(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, project_id):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Özet Kartları (2 satır) ────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.card_income   = self.create_summary_card("✅ Tahsil Edilen Gelir",  self._fmt_try(0), tc("success"))
        self.card_expense  = self.create_summary_card("💸 Ödenen Gider",         self._fmt_try(0), tc("danger"))
        self.card_profit   = self.create_summary_card("📈 Net Kâr",              self._fmt_try(0), tc("accent"))
        row1.addWidget(self.card_income)
        row1.addWidget(self.card_expense)
        row1.addWidget(self.card_profit)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.card_income_pending  = self.create_summary_card("⏳ Bekleyen Gelir",  self._fmt_try(0), tc("warning"), small=True)
        self.card_expense_pending = self.create_summary_card("⏳ Bekleyen Gider",  self._fmt_try(0), tc("warning"), small=True)
        row2.addWidget(self.card_income_pending)
        row2.addWidget(self.card_expense_pending)
        row2.addStretch()
        layout.addLayout(row2)

        # ── Butonlar ─────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.btn_income = QPushButton("➕ Gelir Ekle")
        self.btn_income.setStyleSheet(theme_qss("background-color: @success; color: @selection_text; border-radius: 6px; padding: 6px 14px; font-weight: bold;"))
        self.btn_income.clicked.connect(lambda: self.open_transaction_dialog("Gelir"))

        self.btn_expense = QPushButton("➖ Gider Ekle")
        self.btn_expense.setStyleSheet(theme_qss("background-color: @danger; color: @selection_text; border-radius: 6px; padding: 6px 14px; font-weight: bold;"))
        self.btn_expense.clicked.connect(lambda: self.open_transaction_dialog("Gider"))

        btn_layout.addWidget(self.btn_income)
        btn_layout.addWidget(self.btn_expense)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ── İşlem Tablosu (6 sütun — Durum dahil) ────────────────────────────
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Tarih", "Tür", "Kategori", "Açıklama", "Ödeme Şekli", "Tutar / Durum"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.open_detail_dialog)
        layout.addWidget(self.table)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()

    def update_texts(self):
        self.load_data()

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )

    def _get_project_currency(self):
        try:
            currency, rate = self.db.get_project_currency(self.project_id)
            return (currency or "TRY").upper(), float(rate or 1.0)
        except Exception:
            return "TRY", 1.0

    def _fmt_project_amount(self, amount_try):
        project_currency, _project_rate = self._get_project_currency()
        amount_try = float(amount_try or 0)
        if project_currency == "TRY":
            return CurrencyHelper.format_amount(amount_try, db=self.db, currency_code="TRY")
        converted = CurrencyHelper.convert_amount(self.db, amount_try, "TRY", project_currency)
        primary = CurrencyHelper.format_amount(converted, db=self.db, currency_code=project_currency)
        secondary = CurrencyHelper.format_amount(amount_try, db=self.db, currency_code="TRY")
        return f"{primary} ({secondary})"

    def _effective_rate(self, amount_try, original_amount, stored_rate, project_rate):
        try:
            original_amount = float(original_amount or 0)
            amount_try = float(amount_try or 0)
            stored_rate = float(stored_rate or 0)
            if stored_rate > 1.0001:
                return stored_rate
            if original_amount > 0 and amount_try > 0:
                derived = amount_try / original_amount
                if derived > 1.0001:
                    return derived
            if float(project_rate or 0) > 1.0001:
                return float(project_rate)
        except Exception:
            pass
        return 1.0

    def _pretty_txn_description(self, txn, project_currency, project_rate):
        desc = (txn["description"] or "") if "description" in txn.keys() else ""
        original_amount = txn["original_amount"] if "original_amount" in txn.keys() else None
        original_currency = ((txn["original_currency"] if "original_currency" in txn.keys() else project_currency) or project_currency).upper()
        amount_try = float(txn["amount"] or 0)
        stored_rate = txn["exchange_rate"] if "exchange_rate" in txn.keys() else None

        if original_amount in (None, "", 0) or original_currency == "TRY":
            return desc

        rate = self._effective_rate(amount_try, original_amount, stored_rate, project_rate)
        symbol = CurrencyHelper.get_symbol(db=self.db, currency_code=original_currency)
        kind = "Proje bütçesi" if (txn["type"] or "").lower() == "gelir" else "Proje maliyeti"
        project_name = desc.split(":", 1)[1].split("[", 1)[0].strip() if ":" in desc else ""
        base_text = f"{kind}: {project_name}".strip(": ").strip()
        return (
            f"{base_text} "
            f"[{float(original_amount):,.2f} {symbol} @ {rate:.4f} = {amount_try:,.2f} TL]"
        )

    def create_summary_card(self, title, value, color, small=False):
        frame = QFrame()
        frame.setStyleSheet(theme_qss(f"background-color: {color}; border-radius: 8px; color: @selection_text;"))
        h, font_size = (60, 11) if small else (80, 14)
        frame.setFixedHeight(h)
        l = QVBoxLayout(frame)
        l.setContentsMargins(10, 6, 10, 6)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 11px;")
        lbl_v = QLabel(value)
        lbl_v.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        frame.lbl_title_ref = lbl_t
        frame.lbl_value = lbl_v
        return frame

    def load_data(self):
        project_currency, project_rate = self._get_project_currency()

        # ── Özet kartları ──────────────────────────────────────────────────
        fin = self.db.get_project_financials(self.project_id)
        self.card_income.lbl_value.setText(self._fmt_project_amount(fin.get('income', 0)))
        self.card_expense.lbl_value.setText(self._fmt_project_amount(fin.get('expense', 0)))
        self.card_profit.lbl_value.setText(self._fmt_project_amount(fin.get('profit', 0)))
        self.card_income_pending.lbl_value.setText(self._fmt_project_amount(fin.get('income_pending', 0)))
        self.card_expense_pending.lbl_value.setText(self._fmt_project_amount(fin.get('expense_pending', 0)))

        # ── İşlem tablosu ─────────────────────────────────────────────────
        txns = self.db.get_project_transactions(self.project_id)
        self.table.setRowCount(len(txns))
        for row, txn in enumerate(txns):
            date_str  = txn['date'] or ''
            t_type    = txn['type'] or ''
            category  = txn['category'] or ''
            desc      = self._pretty_txn_description(txn, project_currency, project_rate)
            pmethod   = txn['payment_method'] or ''
            amount    = float(txn['amount'] or 0)
            status    = txn['status'] or 'Ödenmedi'
            original_amount = txn['original_amount'] if 'original_amount' in txn.keys() else None
            original_currency = (txn['original_currency'] if 'original_currency' in txn.keys() else 'TRY') or 'TRY'

            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, txn)
            self.table.setItem(row, 1, QTableWidgetItem(t_type))
            self.table.setItem(row, 2, QTableWidgetItem(category))
            desc_item = QTableWidgetItem(desc)
            desc_item.setToolTip(desc)
            self.table.setItem(row, 3, desc_item)
            self.table.setItem(row, 4, QTableWidgetItem(pmethod))

            # Tutar + durum ikonu
            durum_icon = "✅" if status == 'Ödendi' else "⏳"
            if original_amount not in (None, "", 0) and str(original_currency).upper() != "TRY":
                amount_text = CurrencyHelper.format_original_and_try(
                    float(original_amount),
                    original_currency,
                    db=self.db,
                )
            else:
                amount_text = self._fmt_project_amount(amount if project_currency != "TRY" else amount)
            amt_item = QTableWidgetItem(f"{durum_icon} {amount_text}")
            if t_type == 'Gelir':
                amt_item.setForeground(qc("success"))
            else:
                amt_item.setForeground(qc("danger"))
            self.table.setItem(row, 5, amt_item)

        try:
            self.table.resizeRowsToContents()
        except Exception:
            pass

    def open_transaction_dialog(self, txn_type):
        from src.ui.dialogs.project_transaction_dialog import ProjectTransactionDialog
        dlg = ProjectTransactionDialog(self.db, self.project_id, txn_type, self)
        if dlg.exec():
            self.load_data()

    def open_detail_dialog(self, item):
        row = item.row()
        txn_data = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if txn_data:
            from src.ui.dialogs.transaction_detail_dialog import TransactionDetailDialog
            TransactionDetailDialog(self, txn_data).exec()

# --- TAB 2: UNITS / STOCK (Akıllı Ev Oda/Ürün Takibi) ---

class UnitsTab(QWidget):
    def __init__(self, db, project_id, project_page=None):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.project_page = project_page   # ProjectDetailPage referansı
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ── Araç Çubuğu ──────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.btn_add = QPushButton("➕ Daire / Oda Ekle")
        self.btn_add.setFixedHeight(36)
        self.btn_add.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 13px; padding: 0 16px; } "
            "QPushButton:hover { background-color: @accent_hover; }"
        ))
        self.btn_add.clicked.connect(self.open_add_unit_dialog)
        toolbar.addWidget(self.btn_add)

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("🔍 Oda / daire ara...")
        self.search_inp.setFixedHeight(36)
        self.search_inp.setFixedWidth(200)
        self.search_inp.setStyleSheet(theme_qss(
            "QLineEdit { border: 1px solid @border; border-radius: 7px; padding: 0 10px; "
            "background: @surface; color: @text; font-size: 12px; }"
        ))
        self.search_inp.textChanged.connect(self.load_data)
        toolbar.addWidget(self.search_inp)

        toolbar.addStretch()

        self.btn_export = QPushButton("📊 Excel Raporu")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(theme_qss(
            "QPushButton { background-color: @success; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 12px; padding: 0 14px; } "
            "QPushButton:hover { background-color: @success; }"
        ))
        self.btn_export.clicked.connect(self.export_to_excel)
        toolbar.addWidget(self.btn_export)

        lbl_info = QLabel("Çift tık → ürün ekle   |   Sağ tık → durum değiştir")
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        toolbar.addWidget(lbl_info)
        layout.addLayout(toolbar)

        # ── Grid ─────────────────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(theme_qss("QScrollArea { border: none; background: transparent; }"))

        self.scroll_content = QWidget()
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.load_data()

    def update_texts(self):
        pass

    def load_data(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        units = self.db.get_project_root_units(self.project_id)

        # Arama filtresi
        search = self.search_inp.text().strip().lower() if hasattr(self, 'search_inp') else ""
        if search:
            def _match(u):
                no = (u['unit_no'] if isinstance(u, dict) else (u[4] if len(u) > 4 else "")) or ""
                bl = (u['block_name'] if isinstance(u, dict) else (u[2] if len(u) > 2 else "")) or ""
                return search in no.lower() or search in bl.lower()
            units = [u for u in units if _match(u)]

        if not units:
            empty_lbl = QLabel("Henüz oda/daire eklenmedi veya arama sonucu bulunamadı.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
            self.grid.addWidget(empty_lbl, 0, 0)
            if self.project_page:
                self.project_page.refresh_summary()
            return

        cols = 5
        for idx, unit in enumerate(units):
            ri, ci = idx // cols, idx % cols
            self.grid.addWidget(UnitCard(unit, self), ri, ci)

        if self.project_page:
            self.project_page.refresh_summary()

    def open_add_unit_dialog(self):
        dlg = AddUnitDialog(self.db, self.project_id, self)
        if dlg.exec():
            self.load_data()

    def open_unit_products(self, unit):
        dlg = UnitProductsDialog(self.db, self.project_id, unit, self)
        dlg.exec()
        self.load_data()

    def change_unit_status(self, unit_id, status):
        self.db.set_unit_install_status(unit_id, status)
        self.load_data()

    # ── Excel Export ─────────────────────────────────────────────────────────
    def export_to_excel(self):
        try:
            import pandas as pd
            from PyQt6.QtWidgets import QFileDialog
            import os, datetime
            from src.ui.utils.ui_helpers import show_success, show_error, show_warning

            path, _ = QFileDialog.getSaveFileName(
                self, "Excel Raporu Kaydet", 
                f"kurulum_raporu_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", 
                "Excel Dosyası (*.xlsx);;CSV Dosyası (*.csv)"
            )
            if not path:
                return

            units = self.db.get_project_units(self.project_id)
            if not units:
                show_warning(self, "Raporlanacak oda/daire bulunamadı.")
                return

            all_products = self.db.get_project_unit_products(self.project_id)
            products_by_unit = {}
            direct_counts = {}
            for product in all_products:
                product_unit_id = (
                    product["unit_id"]
                    if hasattr(product, "keys")
                    else product[1]
                )
                products_by_unit.setdefault(product_unit_id, []).append(product)
                direct_counts[product_unit_id] = (
                    direct_counts.get(product_unit_id, 0) + 1
                )

            child_units = {}
            for unit in units:
                unit_id = unit["id"] if hasattr(unit, "keys") else unit[0]
                parent_id = (
                    unit["parent_unit_id"]
                    if hasattr(unit, "keys")
                    else (unit[12] if len(unit) > 12 else None)
                )
                if parent_id is not None:
                    child_units.setdefault(parent_id, []).append(unit_id)

            # Sheet 1: Unit Summary
            unit_data = []
            for unit in units:
                if isinstance(unit, dict):
                    uid, block, uno, st = unit.get('id'), unit.get('block_name',''), unit.get('unit_no',''), unit.get('status','Bekliyor')
                else:
                    uid, block, uno, st = unit[0], unit[2], unit[4], (unit[5] if len(unit) > 5 else 'Bekliyor')

                installed_count = direct_counts.get(uid, 0)
                installed_count += sum(
                    direct_counts.get(child_id, 0)
                    for child_id in child_units.get(uid, [])
                )
                unit_data.append({
                    "Blok": block,
                    "Daire / Oda": uno,
                    "Durum": st,
                    "Kurulu \u00dcr\u00fcn Say\u0131s\u0131": installed_count,
                })
            
            df_units = pd.DataFrame(unit_data)

            # Sheet 2: Product Details
            prod_data = []
            for unit in units:
                if isinstance(unit, dict):
                    uid, block, uno = unit.get('id'), unit.get('block_name',''), unit.get('unit_no','')
                else:
                    uid, block, uno = unit[0], unit[2], unit[4]
                
                for prod in products_by_unit.get(uid, []):
                    if isinstance(prod, dict):
                        pname, pcode, qty, note, added = prod.get('part_name',''), prod.get('part_code','-') or '-', prod.get('quantity',1), prod.get('notes','') or '', prod.get('added_at','') or ''
                    else:
                        pname = prod[4] if len(prod) > 4 else ''
                        pcode = prod[5] if len(prod) > 5 else '-'
                        qty   = prod[6] if len(prod) > 6 else 1
                        note  = prod[7] if len(prod) > 7 else ''
                        added = prod[8] if len(prod) > 8 else ''
                    
                    prod_data.append({
                        "Blok": block,
                        "Daire / Oda": uno,
                        "Ürün Adı": pname,
                        "Kod": pcode,
                        "Adet": qty,
                        "Teknik Not": note,
                        "Eklenme Tarihi": added
                    })
            
            df_prods = pd.DataFrame(prod_data)

            if path.endswith(".csv"):
                # For CSV, we can only save one sheet. Usually we save the more detailed one.
                df_prods.to_csv(path, index=False, encoding="utf-8-sig", sep=";")
            else:
                with pd.ExcelWriter(path) as writer:
                    df_units.to_excel(writer, sheet_name="Oda Özeti", index=False)
                    df_prods.to_excel(writer, sheet_name="Ürün Detayları", index=False)
                
            show_success(self, f"Rapor oluşturuldu:\n{os.path.basename(path)}")
            try:
                os.startfile(path)
            except Exception:
                pass
        except Exception as e:
            show_error(self, f"Rapor oluşturulamadı: {e}")


# --- UNIT CARD (küçük kutu) ---

class UnitCard(QFrame):
    """Tek bir daire/odayı temsil eden küçük kart widgeti."""

    # Durum → (kenarlık rengi, etiket metni, etiket rengi)
    _STATUS_MAP = {
        'Tamamlandı':   ('#4CAF50', '✅ Tamamlandı',   '#4CAF50'),
        'Devam Ediyor': ('#FFC107', '🔄 Devam Ediyor', '#FFC107'),
        'Bekliyor':     (None,      '⏳ Bekliyor',      None),
    }
    _STATUS_ORDER = ['Bekliyor', 'Devam Ediyor', 'Tamamlandı']

    def __init__(self, unit, parent_tab):
        super().__init__()
        self.unit = unit
        self.parent_tab = parent_tab

        if isinstance(unit, dict):
            self.unit_id    = unit.get('id')
            self.block_name = unit.get('block_name', '') or ''
            self.unit_no    = unit.get('unit_no', '')    or ''
            raw_status      = unit.get('status', 'Bekliyor') or 'Bekliyor'
        else:
            self.unit_id    = unit[0]
            self.block_name = (unit[2] if len(unit) > 2 else '') or ''
            self.unit_no    = (unit[4] if len(unit) > 4 else '') or ''
            raw_status      = (unit[5] if len(unit) > 5 else 'Bekliyor') or 'Bekliyor'

        # Normalize: eski inşaat durumlarını "Bekliyor" olarak say
        self.status = raw_status if raw_status in self._STATUS_MAP else 'Bekliyor'

        border_color, _, _ = self._STATUS_MAP.get(self.status, (None, '', None))
        border_css = f"2px solid {border_color}" if border_color else "1px solid #555"

        self.setFixedSize(155, 120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-radius: 10px;
                border: {border_css};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(2)

        # Blok adı
        lbl_block = QLabel(self.block_name)
        lbl_block.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; border: none; background: transparent;"))
        layout.addWidget(lbl_block)

        # Oda no
        lbl_unit = QLabel(self.unit_no)
        lbl_unit.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_unit.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        layout.addWidget(lbl_unit)

        layout.addStretch()

        count = 0
        room_count = 0
        try:
            count = self.parent_tab.db.get_unit_total_product_count(self.unit_id)
            room_count = len(self.parent_tab.db.get_unit_rooms(self.unit_id) or [])
        except Exception:
            pass

        lbl_products = QLabel(f"📦 {count} ürün kurulu" if count > 0 else "📦 Ürün yok")
        lbl_products.setStyleSheet(theme_qss(
            ("color: @success;" if count > 0 else "color: @text_muted;") +
            " font-size: 10px; font-weight: bold; border: none; background: transparent;"
        ))
        layout.addWidget(lbl_products)

        lbl_rooms = QLabel(f"🏠 {room_count} oda" if room_count > 0 else "🏠 Oda yok")
        lbl_rooms.setStyleSheet(theme_qss(
            ("color: @accent;" if room_count > 0 else "color: @text_muted;") +
            " font-size: 10px; font-weight: bold; border: none; background: transparent;"
        ))
        layout.addWidget(lbl_rooms)

        # Durum etiketi
        _, status_lbl, status_color = self._STATUS_MAP.get(self.status, (None, '⏳ Bekliyor', None))
        lbl_status = QLabel(status_lbl)
        lbl_status.setStyleSheet(
            f"color: {status_color}; font-size: 9px; font-weight: bold; border: none; background: transparent;"
            if status_color else
            theme_qss("color: @text_muted; font-size: 9px; border: none; background: transparent;")
        )
        layout.addWidget(lbl_status)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_tab.open_unit_products(self.unit)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.parent_tab.open_unit_products(self.unit)

    def _show_context_menu(self, pos):
        if not is_context_menu_enabled(self.parent_tab.db, page_id=200):
            return
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss(
            "QMenu { background: @surface; border: 1px solid @border; border-radius: 6px; } "
            "QMenu::item { padding: 6px 20px; color: @text; } "
            "QMenu::item:selected { background: @surface_alt; }"
        ))
        act_bek  = menu.addAction("⏳ Bekliyor")
        act_dev  = menu.addAction("🔄 Devam Ediyor")
        act_tam  = menu.addAction("✅ Tamamlandı")
        menu.addSeparator()
        act_prod = menu.addAction("📦 Ürünleri Yönet")

        # Aktif durumu işaretle
        for act, st in [(act_bek,'Bekliyor'),(act_dev,'Devam Ediyor'),(act_tam,'Tamamlandı')]:
            act.setCheckable(True)
            act.setChecked(self.status == st)

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_bek:
            self.parent_tab.change_unit_status(self.unit_id, 'Bekliyor')
        elif action == act_dev:
            self.parent_tab.change_unit_status(self.unit_id, 'Devam Ediyor')
        elif action == act_tam:
            self.parent_tab.change_unit_status(self.unit_id, 'Tamamlandı')
        elif action == act_prod:
            self.parent_tab.open_unit_products(self.unit)


# --- UNIT PRODUCTS DIALOG ---

class UnitProductsDialog(BaseModernDialog):
    """Bir daire/odaya kurulu akıllı ev ürünlerini gösteren ve yönetilen dialog."""

    def __init__(self, db, project_id, unit, parent=None):
        if isinstance(unit, dict):
            unit_no = unit.get('unit_no', '')
            self.unit_id = unit.get('id')
            self.block_name = unit.get('block_name', '') or ''
        else:
            unit_no = unit[4] if len(unit) > 4 else ''
            self.unit_id = unit[0]
            self.block_name = unit[2] if len(unit) > 2 else ''

        super().__init__(parent, title=f"📦 Kurulu Ürünler — {unit_no}", width=1240, height=860)
        self.set_wheel_scroll_enabled(True)
        self.db = db
        self.project_id = project_id
        self.unit_no = unit_no
        self._all_parts = []
        self.active_target_unit_id = self.unit_id
        self.setup_ui()
        self._wire_ui_signals()
        self.load_rooms()
        self._load_general_note()
        self.load_installed()
        self.load_stock_items()
        self.set_footer_visible(False)
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def setup_ui(self):
        content = self.content_layout
        content.setSpacing(10)

        header_row = QHBoxLayout()
        self.lbl_target_info = QLabel()
        self.lbl_target_info.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text;"))
        header_row.addWidget(self.lbl_target_info)
        header_row.addStretch()
        self.btn_add_room = QPushButton("🚪 Oda Ekle")
        self.btn_add_room.setFixedHeight(32)
        self.btn_add_room.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_add_room.clicked.connect(self.add_room)
        header_row.addWidget(self.btn_add_room)
        content.addLayout(header_row)

        room_row = QHBoxLayout()
        lbl_rooms_title = QLabel("Hedef Kurulum Alanı:")
        lbl_rooms_title.setStyleSheet(theme_qss("color: @text; font-weight: bold;"))
        room_row.addWidget(lbl_rooms_title)
        self.cmb_target_room = QComboBox()
        self.cmb_target_room.setFixedHeight(34)
        self.cmb_target_room.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_target_room.currentIndexChanged.connect(self._on_room_changed)
        room_row.addWidget(self.cmb_target_room, 1)
        content.addLayout(room_row)

        lbl_general_note = QLabel("📝 Genel Teknik Not")
        lbl_general_note.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text;"))
        content.addWidget(lbl_general_note)

        note_row = QHBoxLayout()
        self.txt_general_note = QLineEdit()
        self.txt_general_note.setPlaceholderText("Daire veya seçili oda için genel teknik not yazın...")
        self.txt_general_note.setFixedHeight(34)
        self.txt_general_note.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        note_row.addWidget(self.txt_general_note, 1)
        self.btn_save_general_note = QPushButton("💾 Genel Notu Kaydet")
        self.btn_save_general_note.setFixedHeight(34)
        self.btn_save_general_note.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_save_general_note.clicked.connect(self.save_general_note)
        note_row.addWidget(self.btn_save_general_note)
        content.addLayout(note_row)

        # ── Kurulu Ürünler ─────────────────────────────────────────
        lbl_installed = QLabel("✅ Kurulu Ürünler")
        lbl_installed.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text;"))
        content.addWidget(lbl_installed)

        self.table_installed = QTableWidget()
        self.table_installed.setColumnCount(5)
        self.table_installed.setHorizontalHeaderLabels(["Ürün Adı", "Kod", "Adet", "Teknik Not", "Kaldır"])
        self.table_installed.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_installed.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table_installed.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_installed.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_installed.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_installed.setColumnWidth(1, 110)
        self.table_installed.setColumnWidth(2, 70)
        self.table_installed.setColumnWidth(4, 76)
        self.table_installed.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # We will trigger edit on specific column
        self.table_installed.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_installed.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_installed.verticalHeader().setVisible(False)
        self.table_installed.verticalHeader().setDefaultSectionSize(38)
        self.table_installed.setAlternatingRowColors(True)
        self.table_installed.setWordWrap(True)
        self.table_installed.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_installed.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_installed.setMinimumHeight(280)
        self.table_installed.setStyleSheet(theme_qss(
            "QTableWidget { border: 1px solid @border; border-radius: 10px; background: @surface; alternate-background-color: @surface_alt; } "
            "QTableWidget::item { padding: 6px 8px; } "
            "QTableWidget::item:hover { background: rgba(59,130,246,0.08); color: @text; } "
            "QTableWidget::item:selected { background: @selection_bg; color: @selection_text; } "
            "QHeaderView::section { background: @surface_alt; font-weight: bold; } "
            "QScrollBar:vertical { width: 10px; background: transparent; margin: 4px; } "
            "QScrollBar::handle:vertical { background: @border; border-radius: 5px; min-height: 24px; } "
            "QScrollBar::handle:vertical:hover { background: @text_muted; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        ))
        # Allow editing only on first double click or similar (we'll handle it below)
        self.table_installed.cellDoubleClicked.connect(self._on_cell_double_clicked)
        content.addWidget(self.table_installed)

        # ── Teknik Notları Kaydet Butonu ───────────────────────
        save_notes_row = QHBoxLayout()
        self.btn_save_notes = QPushButton("💾 Teknik Notları Kaydet")
        self.btn_save_notes.setFixedHeight(30)
        self.btn_save_notes.setStyleSheet(theme_qss(
            "QPushButton { background-color: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 0 12px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: @border; }"
        ))
        self.btn_save_notes.clicked.connect(self.save_notes)
        save_notes_row.addWidget(self.btn_save_notes)
        save_notes_row.addStretch()
        content.addLayout(save_notes_row)

        # ── Stoktan Ürün Ekle ──────────────────────────────────────
        lbl_add = QLabel("➕ Stoktan Ürün Ekle")
        lbl_add.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text; margin-top: 6px;"))
        content.addWidget(lbl_add)

        # Arama
        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("🔍 Ürün adı veya kod ile filtrele...")
        self.search_inp.setFixedHeight(36)
        self.search_inp.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search_inp.textChanged.connect(self.filter_stock_list)
        content.addWidget(self.search_inp)

        # Stok listesi (checkbox ile çoklu seçim)
        self.list_stock = QListWidget()
        self.list_stock.setAlternatingRowColors(True)
        self.list_stock.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_stock.setMinimumHeight(180)
        self.list_stock.setStyleSheet(theme_qss(
            "QListWidget { border: 1px solid @border; border-radius: 10px; background: @surface; } "
            "QListWidget::item { padding: 7px 10px; border-radius: 6px; margin: 2px 4px; color: @text; } "
            "QListWidget::item:hover { background: rgba(59,130,246,0.08); color: @text; } "
            "QListWidget::item:selected { background: @selection_bg; color: @selection_text; } "
            "QScrollBar:vertical { width: 10px; background: transparent; margin: 4px; } "
            "QScrollBar::handle:vertical { background: @border; border-radius: 5px; min-height: 24px; } "
            "QScrollBar::handle:vertical:hover { background: @text_muted; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }"
        ))
        content.addWidget(self.list_stock)

        # Adet + Teknik Not + Ekle butonu
        opts_row = QHBoxLayout()
        opts_row.setContentsMargins(0, 0, 0, 0)
        opts_row.setSpacing(8)
        lbl_qty = QLabel("Adet:")
        lbl_qty.setFixedWidth(42)
        lbl_qty.setStyleSheet(theme_qss(
            "color: @text; font-weight: bold; border: none; "
            "background: transparent; padding: 0;"
        ))
        self.spin_qty = QSpinBox()
        self.spin_qty.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_qty.setRange(1, 999)
        self.spin_qty.setValue(1)
        self.spin_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_qty.setFixedWidth(88)
        self.spin_qty.setFixedHeight(34)
        self.spin_qty.setStyleSheet(theme_qss(
            "QSpinBox { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 7px; padding: 0 10px; font-weight: 700; } "
            "QSpinBox:focus { border: 1px solid @accent; }"
        ))

        lbl_note = QLabel("Teknik Not:")
        lbl_note.setFixedWidth(82)
        lbl_note.setStyleSheet(theme_qss(
            "color: @text; font-weight: bold; border: none; "
            "background: transparent; padding: 0;"
        ))
        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("Örn: IP: 192.168.1.12  /  Kanal 3  /  WiFi: Ev_Ag")
        self.txt_note.setFixedHeight(34)
        self.txt_note.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        opts_row.addWidget(lbl_qty)
        opts_row.addWidget(self.spin_qty)
        opts_row.addWidget(lbl_note)
        opts_row.addWidget(self.txt_note, stretch=1)
        content.addLayout(opts_row)

        btn_row = QHBoxLayout()
        btn_add_items = QPushButton("✅ Seçilenleri Ekle")
        btn_add_items.setFixedHeight(36)
        btn_add_items.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; border-radius: 7px; "
            "padding: 0 18px; font-weight: bold; font-size: 13px; } "
            "QPushButton:hover { background-color: @accent_hover; }"
        ))
        btn_add_items.clicked.connect(self.add_selected_items)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedHeight(36)
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_close.clicked.connect(self.accept)

        btn_row.addStretch()
        btn_row.addWidget(btn_add_items)
        btn_row.addWidget(btn_close)
        content.addLayout(btn_row)

    def _wire_ui_signals(self):
        if hasattr(self, "cmb_cat"):
            self.cmb_cat.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _emit_data_changed(self):
        parent = self.parent()
        project_page = getattr(parent, "project_page", None)
        main_window = getattr(project_page, "main_window", None)
        if main_window is None:
            return
        for signal_name in ("stock_updated", "financial_data_changed"):
            signal = getattr(main_window, signal_name, None)
            if signal is not None:
                try:
                    signal.emit()
                except Exception:
                    pass

    def load_installed(self):
        products = self.db.get_unit_products(self.active_target_unit_id)
        self.table_installed.setRowCount(len(products))
        for row, prod in enumerate(products):
            if isinstance(prod, dict):
                pid   = prod.get('id')
                pname = prod.get('part_name', '') or ''
                pcode = prod.get('part_code')    or '-'
                qty   = prod.get('quantity', 1)
                note  = prod.get('notes', '')    or ''
            else:
                pid   = prod[0]
                pname = prod[4] if len(prod) > 4 else ''
                pcode = (prod[5] if len(prod) > 5 else '-') or '-'
                qty   = prod[6] if len(prod) > 6 else 1
                note  = prod[7] if len(prod) > 7 else ''

            self.table_installed.setItem(row, 0, QTableWidgetItem(str(pname)))
            self.table_installed.setItem(row, 1, QTableWidgetItem(str(pcode)))
            self.table_installed.setItem(row, 2, QTableWidgetItem(str(qty)))
            
            note_item = QTableWidgetItem(str(note))
            note_item.setData(Qt.ItemDataRole.UserRole, pid) # Store entry ID
            note_item.setToolTip(str(note))
            self.table_installed.setItem(row, 3, note_item)

            btn_rm = QPushButton("Kald\u0131r")
            btn_rm.setFixedSize(72, 28)
            btn_rm.setStyleSheet(theme_qss(
                "QPushButton { background: @danger; color: #FFFFFF; border: 1px solid @danger; "
                "border-radius: 6px; font-size: 11px; font-weight: 700; } "
                "QPushButton:hover { background: #C62828; border-color: #C62828; }"
            ))
            btn_rm.clicked.connect(lambda _checked, eid=pid: self.remove_product(eid))
            remove_widget = QWidget(self.table_installed)
            remove_layout = QHBoxLayout(remove_widget)
            remove_layout.setContentsMargins(4, 2, 4, 2)
            remove_layout.addWidget(btn_rm, alignment=Qt.AlignmentFlag.AlignCenter)
            self.table_installed.setCellWidget(row, 4, remove_widget)
        self.table_installed.resizeRowsToContents()

    def load_stock_items(self, search=""):
        rows, _ = self.db.get_parts_paginated(limit=300, search_query=search)
        self._all_parts = rows
        self._populate_list(rows)

    def _populate_list(self, parts):
        self.list_stock.clear()
        for part in parts:
            if isinstance(part, dict):
                part_id = part.get('id')
                code    = part.get('code', '') or ''
                name    = part.get('name', '') or ''
                stock   = part.get('stock', 0) or 0
            else:
                part_id = part[0]
                name    = part[1] if len(part) > 1 else ''
                code    = (part[7] if len(part) > 7 else '') or '-'
                stock   = part[3] if len(part) > 3 else 0

            item = QListWidgetItem(f"{name}   ({code})   —   Stok: {stock}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, {'id': part_id, 'name': name, 'code': code})
            self.list_stock.addItem(item)

    def filter_stock_list(self, text):
        text = text.lower()
        for i in range(self.list_stock.count()):
            item = self.list_stock.item(i)
            item.setHidden(text not in item.text().lower())

    def add_selected_items(self):
        qty  = self.spin_qty.value()
        note = self.txt_note.text().strip()
        added = 0
        for i in range(self.list_stock.count()):
            item = self.list_stock.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                d = item.data(Qt.ItemDataRole.UserRole)
                self.db.add_unit_product({
                    'unit_id':    self.active_target_unit_id,
                    'project_id': self.project_id,
                    'part_id':    d['id'],
                    'part_name':  d['name'],
                    'part_code':  d['code'],
                    'quantity':   qty,
                    'notes':      note,
                })
                item.setCheckState(Qt.CheckState.Unchecked)
                added += 1
        if added > 0:
            self.txt_note.clear()
            show_success(self, f"{added} ürün eklendi.")
            self.load_installed()
            self._emit_data_changed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()
        else:
            show_error(self, "Lütfen listeden en az bir ürün seçin.")

    def load_rooms(self):
        self.cmb_target_room.blockSignals(True)
        self.cmb_target_room.clear()
        self.cmb_target_room.addItem(f"Daire: {self.unit_no}", self.unit_id)
        for room in self.db.get_unit_rooms(self.unit_id) or []:
            if isinstance(room, dict):
                room_id = room.get("id")
                room_name = room.get("unit_no", "")
            else:
                room_id = room[0]
                room_name = room[4] if len(room) > 4 else ""
            self.cmb_target_room.addItem(f"Oda: {room_name}", room_id)
        idx = self.cmb_target_room.findData(self.active_target_unit_id)
        self.cmb_target_room.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_target_room.blockSignals(False)
        self._refresh_target_label()

    def _refresh_target_label(self):
        current_text = self.cmb_target_room.currentText() or f"Daire: {self.unit_no}"
        self.lbl_target_info.setText(f"{self.block_name} / {self.unit_no}  •  Aktif Hedef: {current_text}")

    def _on_room_changed(self):
        self.active_target_unit_id = self.cmb_target_room.currentData() or self.unit_id
        self._refresh_target_label()
        self._load_general_note()
        self.load_installed()

    def _load_general_note(self):
        unit = self.db.get_project_unit(self.active_target_unit_id)
        if not unit:
            self.txt_general_note.clear()
            return
        if isinstance(unit, dict):
            note = unit.get("description", "") or ""
        else:
            note = unit[12] if len(unit) > 12 else ""
        self.txt_general_note.setText(str(note))

    def save_general_note(self):
        if self.db.update_project_unit_note(self.active_target_unit_id, self.txt_general_note.text().strip()):
            show_success(self, "Genel teknik not kaydedildi.")
        else:
            show_error(self, "Genel teknik not kaydedilemedi.")

    def add_room(self):
        room_name, ok = QInputDialog.getText(self, "Oda Ekle", "Oda Adı:")
        if not ok:
            return
        room_name = str(room_name or "").strip()
        if not room_name:
            show_error(self, "Oda adı boş bırakılamaz.")
            return
        room_id = self.db.add_project_room(self.project_id, self.unit_id, room_name)
        if room_id:
            self.active_target_unit_id = room_id
            self.load_rooms()
            self._load_general_note()
            self.load_installed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()
            show_success(self, "Oda eklendi.")
        else:
            show_error(self, "Oda eklenemedi. Aynı isim zaten kullanılıyor olabilir.")

    def remove_product(self, entry_id):
        if self.db.remove_unit_product(entry_id):
            show_success(self, "Ürün kaldırıldı.")
            self.load_installed()
            self._emit_data_changed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()

    def _on_cell_double_clicked(self, row, col):
        # Sadece "Teknik Not" (index 3) kolonu düzenlenebilir olsun
        if col == 3:
            item = self.table_installed.item(row, col)
            if item is None:
                return
            note, accepted = QInputDialog.getMultiLineText(
                self,
                "Teknik Not",
                "Teknik notu d\u00fczenleyin:",
                item.text(),
            )
            if not accepted:
                return
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            if not entry_id or not self.db.update_unit_product_note(entry_id, note):
                show_error(self, "Teknik not kaydedilemedi.")
                return
            item.setText(note)
            item.setToolTip(note)
            self.table_installed.resizeRowToContents(row)
            show_success(self, "Teknik not g\u00fcncellendi.")

    def save_notes(self):
        """Tablodaki tüm ürünlerin teknik notlarını kaydeder."""
        success_count = 0
        for row in range(self.table_installed.rowCount()):
            item = self.table_installed.item(row, 3)
            if item:
                entry_id = item.data(Qt.ItemDataRole.UserRole)
                note     = item.text().strip()
                if entry_id:
                    if self.db.update_unit_product_note(entry_id, note):
                        success_count += 1
        
        if success_count > 0:
            show_success(self, f"{success_count} ürünün teknik notu güncellendi.")
            self.load_installed()
        else:
            show_error(self, "Güncellenecek not bulunamadı veya bir hata oluştu.")

# --- TAB 3: SUBCONTRACTORS ---

class SubcontractorsTab(QWidget):
    def __init__(self, db, project_id):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("👥 Ekip Üyesi Ekle")
        self.btn_add.setFixedHeight(36)
        self.btn_add.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 13px; padding: 0 16px; } "
            "QPushButton:hover { background-color: @accent_hover; }"
        ))
        self.btn_add.clicked.connect(self.add_sub)
        toolbar.addWidget(self.btn_add)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Ad / Firma", "Uzmanlık Alanı", "Ücret", "Kalan Bakiye", "İşlemler"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.load_data()

    def update_texts(self):
        pass

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )

    def load_data(self):
        subs = self.db.get_subcontractors_with_balance(self.project_id)
        self.table.setRowCount(len(subs))
        for row, sub in enumerate(subs):
            self.table.setRowHeight(row, 32)
            # sub: id, proj_id, name, job_type, total, contact, created
            self.table.setItem(row, 0, QTableWidgetItem(sub['name']))
            self.table.setItem(row, 1, QTableWidgetItem(sub['job_type']))
            self.table.setItem(row, 2, QTableWidgetItem(self._fmt_try(sub['total_contract_amount'])))
            
            balance = float(sub["remaining_balance"] or 0.0)
            bal_item = QTableWidgetItem(self._fmt_try(balance))
            bal_item.setForeground(qc("danger") if balance > 0 else qc("success"))
            self.table.setItem(row, 3, bal_item)
            
            btn_pay = QPushButton("\u00d6deme Yap")
            btn_pay.setFixedSize(92, 24)
            btn_pay.setStyleSheet(theme_qss(
                "QPushButton { background-color: @accent; color: @selection_text; "
                "border: 1px solid @accent; border-radius: 5px; font-weight: 700; "
                "font-size: 11px; padding: 0 8px; } "
                "QPushButton:hover { background-color: @accent_hover; }"
            ))
            # We need to pass sub_id to the slot. Lambdas capture variable by reference in loops unless defaulted.
            btn_pay.clicked.connect(lambda _, s_id=sub['id']: self.make_payment(s_id))
            action_widget = QWidget(self.table)
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 0, 2, 0)
            action_layout.addStretch()
            action_layout.addWidget(btn_pay)
            action_layout.addStretch()
            self.table.setCellWidget(row, 4, action_widget)

    def add_sub(self):
        dlg = AddSubDialog(self.db, self.project_id, self)
        if dlg.exec():
            self.load_data()

    def make_payment(self, sub_id):
        # Open Transaction Dialog pre-filled for this subcontractor
        dlg = TransactionDialog(self.db, self.project_id, "Gider", self, sub_id=sub_id)
        if dlg.exec():
            self.load_data()

# --- DIALOGS ---

class TransactionDialog(QtDialog):
    def __init__(self, db, project_id, txn_type, parent=None, sub_id=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.txn_type = txn_type
        self.sub_id = sub_id
        self.currency_code = CurrencyHelper.get_code(self.db)
        self.setWindowTitle(f"{txn_type} Ekle")
        self.setFixedSize(350, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cmb_cat = QComboBox()
        if self.txn_type == "Gider":
            cats = ["Malzeme", "İşçilik", "Taşeron Ödemesi", "Nakliye", "Resmi Gider", "Diğer"]
            self.cmb_cat.addItems(cats)
            if self.sub_id: 
                self.cmb_cat.setCurrentText("Taşeron Ödemesi")
                self.cmb_cat.setEnabled(False) 
        else:
            self.cmb_cat.addItems(["Daire Satışı", "Proje Hakedişi", "Diğer"])
            
        form.addRow("Kategori:", self.cmb_cat)
        
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 100000000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {CurrencyHelper.get_label(self.currency_code)}")
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.spin_amount.setKeyboardTracking(False)
        form.addRow("Tutar:", self.spin_amount)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Tarih:", self.date_edit)
        
        self.txt_desc = QLineEdit()
        form.addRow("Açıklama:", self.txt_desc)
        
        layout.addLayout(form)
        
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.save)
        layout.addWidget(self.btn_save)

    def save(self):
        if getattr(self, "_saving", False):
            return
        self._saving = True
        self.btn_save.setEnabled(False)
        data = {
            'project_id': self.project_id,
            'type': self.txn_type,
            'category': self.cmb_cat.currentText(),
            'amount': self.spin_amount.value(),
            'payment_method': 'Nakit', # Simplified
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'description': self.txt_desc.text(),
            'status': 'Ödendi',
            'ref_table': 'subcontractors' if self.sub_id else None,
            'ref_id': self.sub_id
        }
        try:
            transaction_id = self.db.add_project_transaction(data, commit=False)
            if not transaction_id:
                raise RuntimeError("Project transaction could not be created")

            self.db.conn.commit()
            show_success(self, f"{self.txn_type} başarıyla kaydedildi!")
            self.accept()
        except Exception as e:
            self.db.conn.rollback()
            self._saving = False
            self.btn_save.setEnabled(True)
            show_error(self, f"Kaydetme hatas\u0131: {str(e)}")


