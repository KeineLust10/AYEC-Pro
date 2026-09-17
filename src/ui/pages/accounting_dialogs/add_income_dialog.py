# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QFormLayout, QComboBox, QLineEdit, QDateEdit,
                             QDoubleSpinBox, QPushButton, QHBoxLayout, QRadioButton, QButtonGroup, QLabel)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QCursor
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.toast_notification import show_warning, show_error, show_success
from src.utils.logger import logger



class AddIncomeDialog(PremiumDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__("Gelir Ekle", parent)
        self.db = db
        self.resize(450, 620)
        self._selected_product_data = None
        self.setup_ui()

        self._wire_ui_signals()
    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        return CurrencyHelper.format_from_try(
            amount_try,
            db=self.db,
            currency_code=self._display_currency(),
            include_try_reference=False,
        )

    def setup_ui(self):
        form = QFormLayout()
        form.setSpacing(15)
        self.bank_accounts = self._load_bank_accounts()

        # Stok/Hizmet Seçici
        self.cmb_product = QComboBox()
        self.cmb_product.setEditable(True)
        self.cmb_product.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.cmb_product.lineEdit():
            self.cmb_product.lineEdit().setPlaceholderText("Stok veya hizmet arayın...")
        self.cmb_product.addItem("Stok/Hizmet seçin (isteğe bağlı)", None)
        self._populate_product_combo()
        self.cmb_product.currentIndexChanged.connect(self._on_product_selected)
        form.addRow("Stok/Hizmet:", self.cmb_product)

        self.cmb_cat = QComboBox()
        self.cmb_cat.addItems(["Satış", "Hizmet", "Tahsilat", "Kira", "Diğer"])
        self.cmb_cat.setEditable(True)
        form.addRow("Kategori:", self.cmb_cat)

        self.cmb_bank = QComboBox()
        self.cmb_bank.setEditable(True)
        self.cmb_bank.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.cmb_bank.lineEdit():
            self.cmb_bank.lineEdit().setReadOnly(True)
            self.cmb_bank.lineEdit().setPlaceholderText("Banka hesabı seçin")
            self.cmb_bank.lineEdit().installEventFilter(self)
        self.cmb_bank.addItem("Banka hesabı seçin", None)
        for acc in self.bank_accounts:
            acc_id = self._bank_field(acc, "id", 0)
            bank = self._bank_field(acc, "bank_name", 1, "")
            acc_name = self._bank_field(acc, "account_holder", 2, "")
            acc_no = self._bank_field(acc, "account_number", 4, "")
            is_active_val = self._bank_field(acc, "is_active", 7, 0)
            if int(is_active_val or 0) != 1:
                continue
            label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
            label_parts = [p for p in label_parts if p]
            label = " - ".join(label_parts) if label_parts else "Banka Hesabı"
            if acc_no:
                label = f"{label} ({acc_no})"
            self.cmb_bank.addItem(label, acc_id)
        form.addRow("Banka Hesabı:", self.cmb_bank)

        self.inp_amount = QDoubleSpinBox()
        self.inp_amount.setRange(0, 1_000_000_000)
        self.inp_amount.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")
        self.inp_amount.setDecimals(2)

        # Currency Chip Buttons
        _c_style = theme_qss("""
            QRadioButton {
                background: @surface_alt; color: @text_muted;
                padding: 6px 12px; border-radius: 10px;
                font-weight: bold; font-size: 13px;
                border: 1px solid @border;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked { background: @accent; color: @selection_text; border: 1px solid @accent; }
            QRadioButton:!checked:hover { background: @surface; color: @text; }
        """)
        self.inc_btn_try = QRadioButton("TRY")
        self.inc_btn_usd = QRadioButton("$ USD")
        self.inc_btn_eur = QRadioButton("€ EUR")
        self.inc_btn_grp = QButtonGroup(self)
        self.inc_btn_grp.addButton(self.inc_btn_try, 1)
        self.inc_btn_grp.addButton(self.inc_btn_usd, 2)
        self.inc_btn_grp.addButton(self.inc_btn_eur, 3)
        for _b in [self.inc_btn_try, self.inc_btn_usd, self.inc_btn_eur]:
            _b.setStyleSheet(_c_style)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
        # default to global setting
        try:
            _g = CurrencyHelper.get_code(self.db)
            if _g == "USD":
                self.inc_btn_usd.setChecked(True)
            elif _g == "EUR":
                self.inc_btn_eur.setChecked(True)
            else:
                self.inc_btn_try.setChecked(True)
        except Exception:
            self.inc_btn_try.setChecked(True)

        def _inc_suffix():
            _code = "USD" if self.inc_btn_usd.isChecked() else "EUR" if self.inc_btn_eur.isChecked() else "TRY"
            _s = CurrencyHelper.get_symbol(self.db, _code)
            self.inp_amount.setSuffix(f" {_s}")
        self.inc_btn_try.toggled.connect(_inc_suffix)
        self.inc_btn_usd.toggled.connect(_inc_suffix)
        self.inc_btn_eur.toggled.connect(_inc_suffix)
        _inc_suffix()

        inc_amount_row = QHBoxLayout()
        inc_amount_row.addWidget(self.inp_amount)
        inc_amount_row.addWidget(self.inc_btn_try)
        inc_amount_row.addWidget(self.inc_btn_usd)
        inc_amount_row.addWidget(self.inc_btn_eur)
        form.addRow("Tutar:", inc_amount_row)

        # KDV bilgi satırı
        kdv_row = QHBoxLayout()
        self.lbl_kdv_rate = QLabel("KDV: %0")
        self.lbl_kdv_rate.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; font-size: 12px;"))
        self.lbl_kdv_amount = QLabel(self._format_display_money(0))
        self.lbl_kdv_amount.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600; font-size: 12px;"))
        kdv_row.addWidget(self.lbl_kdv_rate)
        kdv_row.addStretch()
        kdv_row.addWidget(self.lbl_kdv_amount)
        form.addRow("KDV Bilgisi:", kdv_row)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Açıklama...")
        form.addRow("Açıklama:", self.inp_desc)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Tarih:", self.inp_date)

        self.body_layout.addLayout(form)

        btn_save = QPushButton("Kaydet")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(theme_qss("background: @success; color: @selection_text; border-radius: 8px; font-weight: bold;"))
        btn_save.clicked.connect(self.save)
        self.body_layout.addWidget(btn_save)

    def _wire_ui_signals(self):
        self.cmb_cat.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _populate_product_combo(self):
        """Stok ve hizmetleri gruplandırılmış olarak combo'ya ekle."""
        # Stoklar
        try:
            parts = self.db.get_all_parts() or []
        except Exception:
            parts = []
        if parts:
            self.cmb_product.addItem("── Stoklar ──", "header")
            for p in parts:
                if hasattr(p, "keys") or isinstance(p, dict):
                    pid = p["id"]
                    pname = p["name"]
                    pprice = p["price"]
                else:
                    pid = p[0]
                    pname = p[1]
                    pprice = p[5] if len(p) > 5 else (p[3] if len(p) > 3 else 0)
                try:
                    pprice = float(pprice or 0)
                except Exception:
                    pprice = 0.0
                self.cmb_product.addItem(
                    f"{pname} ({self._format_display_money(pprice)})",
                    {"type": "product", "id": pid, "name": pname, "price": pprice}
                )

        # Hizmetler
        try:
            services = self.db.get_services_list() or []
        except Exception:
            services = []
        if services:
            self.cmb_product.addItem("── Hizmetler ──", "header")
            for s in services:
                if isinstance(s, dict):
                    sid, sname, sprice = s.get("id"), s.get("name", ""), s.get("price", 0)
                else:
                    sid, sname, sprice = s[0], s[1], s[2] if len(s) > 2 else 0
                sprice = float(sprice or 0)
                self.cmb_product.addItem(
                    f"{sname} ({self._format_display_money(sprice)})",
                    {"type": "service", "id": sid, "name": sname, "price": sprice}
                )

    def _on_product_selected(self, index):
        """Ürün/hizmet seçildiğinde fiyat, banka ve kategori otomatik doldur."""
        data = self.cmb_product.currentData()
        if data is None or isinstance(data, str):
            self._selected_product_data = None
            self.lbl_kdv_rate.setText("KDV: %0")
            self.lbl_kdv_amount.setText(self._format_display_money(0))
            return

        self._selected_product_data = data
        item_type = data["type"]
        item_id = data["id"]
        price = float(data.get("price", 0) or 0)

        # Fiyat doldur
        self.inp_amount.setValue(price)

        # Eşleştirme ara
        mapping = None
        try:
            mapping = self.db.get_product_bank_mapping(item_type, item_id)
        except Exception:
            pass

        if mapping:
            # Banka hesabı seç
            bank_id = mapping.get("bank_account_id")
            if bank_id is not None:
                for i in range(self.cmb_bank.count()):
                    if self.cmb_bank.itemData(i) == bank_id:
                        self.cmb_bank.setCurrentIndex(i)
                        break

            # Kategori seç
            cat = mapping.get("default_category")
            if cat:
                idx = self.cmb_cat.findText(cat)
                if idx >= 0:
                    self.cmb_cat.setCurrentIndex(idx)
                else:
                    self.cmb_cat.setEditText(cat)

            # KDV bilgisi güncelle
            kdv_rate = float(mapping.get("default_kdv_rate", 0) or 0)
            self._update_kdv_display(price, kdv_rate)
        else:
            # Varsayılan kategori ata
            if item_type == "service":
                self.cmb_cat.setCurrentText("Hizmet")
            else:
                self.cmb_cat.setCurrentText("Satış")
            self.lbl_kdv_rate.setText("KDV: %0")
            self.lbl_kdv_amount.setText(self._format_display_money(0))

    def _update_kdv_display(self, base_price, kdv_rate):
        """KDV bilgi etiketlerini güncelle."""
        kdv_amount = float(base_price or 0) * float(kdv_rate or 0) / 100
        self.lbl_kdv_rate.setText(f"KDV: %{int(kdv_rate)}")
        self.lbl_kdv_amount.setText(self._format_display_money(kdv_amount))

    def _load_bank_accounts(self):
        try:
            return self.db.get_bank_accounts() or []
        except Exception:
            return []

    @staticmethod
    def _bank_field(account, key, index, default=None):
        if account is None:
            return default
        if hasattr(account, "keys"):
            try:
                if key in account.keys():
                    return account[key]
            except Exception:
                pass
        if isinstance(account, dict):
            if key in account:
                return account.get(key, default)
            if key == "account_holder":
                return account.get("account_name", default)
            if key == "account_number":
                return account.get("account_no", default)
        try:
            return account[index]
        except Exception:
            return default

    def eventFilter(self, obj, event):
        if obj == self.cmb_bank.lineEdit() and event.type() == QEvent.Type.MouseButtonRelease:
            if not self.cmb_bank.view().isVisible():
                QTimer.singleShot(0, self.cmb_bank.showPopup)
            return False
        return super().eventFilter(obj, event)

    def save(self):
        try:
            cat = self.cmb_cat.currentText()
            amt = self.inp_amount.value()
            desc = self.inp_desc.text()
            date = self.inp_date.date().toString("yyyy-MM-dd")
            bank_account_id = self.cmb_bank.currentData()
            if bank_account_id is None:
                show_warning(self, "Banka hesabı seçimi zorunludur.")
                return

            # Ürün/hizmet bilgisi
            product_service_id = None
            product_service_type = None
            if self._selected_product_data and isinstance(self._selected_product_data, dict):
                product_service_id = self._selected_product_data.get("id")
                product_service_type = self._selected_product_data.get("type")
                # Açıklamaya ürün/hizmet adını ekle
                pname = self._selected_product_data.get("name", "")
                if pname and pname not in desc:
                    desc = f"{pname} | {desc}" if desc else pname

            payment_method = "Banka"
            self.db.add_transaction(
                t_type="Gelir",
                category=cat,
                amount=amt,
                description=desc,
                date=date,
                payment_method=payment_method,
                bank_account_id=bank_account_id,
                currency="USD" if self.inc_btn_usd.isChecked() else "EUR" if self.inc_btn_eur.isChecked() else "TRY",
                original_amount=amt,
                product_service_id=product_service_id,
                product_service_type=product_service_type,
            )
            self._refresh_bank_pages()
            account = self.db.get_bank_account_by_id(bank_account_id)
            acc_label = ""
            if account:
                bank = self._bank_field(account, "bank_name", 1, "")
                acc_name = self._bank_field(account, "account_holder", 2, "")
                label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
                label_parts = [p for p in label_parts if p]
                if label_parts:
                    acc_label = f" ({' - '.join(label_parts)})"
            show_success(self, f"Gelir kaydedildi. {CurrencyHelper.format_amount(amt, db=self.db, currency_code='USD' if self.inc_btn_usd.isChecked() else 'EUR' if self.inc_btn_eur.isChecked() else 'TRY')}{acc_label} bakiyesine eklendi.")
            self.accept()
        except Exception as e:
            logger.error(f"Income save error: {e}")
            show_error(self, f"Gelir kaydedilirken hata oluştu: {e}")

    def _refresh_bank_pages(self):
        parent = self.parent()
        main_window = getattr(parent, "main_window", None) if parent else None
        if main_window and hasattr(main_window, "bank_page"):
            bank_page = getattr(main_window, "bank_page")
            if bank_page and hasattr(bank_page, "refresh_data"):
                bank_page.refresh_data()
