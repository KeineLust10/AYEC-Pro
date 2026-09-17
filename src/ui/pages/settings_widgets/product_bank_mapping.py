# -*- coding: utf-8 -*-

"""
Stok/Hizmet - Banka Hesabı Eşleştirme Ayarları Widget'ı
Her stok ve hizmet için varsayılan banka hesabı, KDV oranı ve gelir kategorisi atanır.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget, QAbstractItemView, QDialog as QtDialog,
)

from src.utils.theme_colors import theme_qss
from src.utils.tax_settings import TaxSettings
from src.utils.toast_notification import show_success, show_warning, show_error



class ProductBankMappingWidget(QWidget):
    """Stok/Hizmet - Banka Eslestirme ayar paneli."""

    INCOME_CATEGORIES = ["Satış", "Hizmet", "Tahsilat", "Kira", "Diğer"]

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.bank_accounts = []
        self.menu_items = []
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)

        # Başlık
        title = QLabel("Menü - Banka Eşleştirme")
        title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 800; color: @text;"))
        root.addWidget(title)

        subtitle = QLabel(
            "Menü bazında varsayılan banka hesabı, KDV oranı ve gelir kategorisi belirleyin. "
            "Gelir eklerken stok/hizmet seçildiğinde bu bilgiler otomatik olarak doldurulacaktır."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        root.addWidget(subtitle)

        # Araç çubuğu
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Menü ara...")
        self.inp_search.setFixedHeight(38)
        self.inp_search.setStyleSheet(theme_qss(
            "QLineEdit { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 6px 12px; } QLineEdit:focus { border-color: @accent; }"
        ))
        self.inp_search.textChanged.connect(self._filter_table)
        toolbar.addWidget(self.inp_search, 1)

        btn_bulk = QPushButton("Menüye Göre Ata")
        btn_bulk.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_bulk.setFixedHeight(38)
        btn_bulk.setStyleSheet(theme_qss(
            "QPushButton { background: @accent; color: @selection_text; border-radius: 8px; "
            "padding: 0 16px; font-weight: 700; } QPushButton:hover { opacity: 0.9; }"
        ))
        btn_bulk.clicked.connect(self.open_bulk_assign_dialog)
        toolbar.addWidget(btn_bulk)

        btn_refresh = QPushButton("Yenile")
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setFixedHeight(38)
        btn_refresh.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0 16px; font-weight: 700; } QPushButton:hover { background: @surface; }"
        ))
        btn_refresh.clicked.connect(self.load_data)
        toolbar.addWidget(btn_refresh)

        root.addLayout(toolbar)

        # Tablo
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "MENÜ", "BANKA HESABI", "KDV %", "GELİR KATEGORİSİ"
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { border: 1px solid @border; border-radius: 8px; font-size: 13px; } "
            "QTableWidget::item { padding: 6px; border-bottom: 1px solid @surface_alt; } "
            "QHeaderView::section { background: @surface; padding: 8px; border-bottom: 2px solid @border; "
            "font-weight: 700; color: @text_muted; }"
        ))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        root.addWidget(self.table, 1)

        # Kaydet butonu
        btn_save = QPushButton("Eşleştirmeleri Kaydet")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(theme_qss(
            "QPushButton { background: @success; color: @selection_text; border-radius: 8px; "
            "font-size: 14px; font-weight: 800; } QPushButton:hover { opacity: 0.9; }"
        ))
        btn_save.clicked.connect(self.save_all)
        root.addWidget(btn_save)

    def _wire_ui_signals(self):
        # No class-level combo boxes on this widget; signals are wired per-row in _populate_table
        pass

    def load_data(self):
        """Veritabanından tüm stok/hizmet ve banka verilerini yükle."""
        try:
            self.bank_accounts = self.db.get_bank_accounts() or []
        except Exception:
            self.bank_accounts = []

        self.menu_items = self._build_menu_items()

        self._populate_table()

    @staticmethod
    def _bank_field(acc, key, index, default=None):
        try:
            if hasattr(acc, "keys") and key in acc.keys():
                return acc[key]
        except Exception:
            pass
        try:
            return acc[index]
        except Exception:
            return default

    def _build_menu_items(self):
        menu_items = [
            {
                "item_type": "product_stock",
                "item_id": 0,
                "menu_name": "Stok Yönetimi",
                "default_category": "Satış",
            },
            {
                "item_type": "product_mobile",
                "item_id": 0,
                "menu_name": "Mobil Stok",
                "default_category": "Satış",
            },
            {
                "item_type": "service_definitions",
                "item_id": 0,
                "menu_name": "Hizmet Tanımları",
                "default_category": "Hizmet",
            },
            {
                "item_type": "product_loaner",
                "item_id": 0,
                "menu_name": "Emanet (Konsinye) Cihazlar",
                "default_category": "Satış",
            },
        ]
        default_vat = TaxSettings.get_percent(self.db)
        for item in menu_items:
            mapping = None
            try:
                mapping = self.db.get_product_bank_mapping(item["item_type"], item["item_id"])
            except Exception:
                mapping = None
            if mapping:
                item["bank_account_id"] = mapping.get("bank_account_id")
                item["default_kdv_rate"] = mapping.get(
                    "default_kdv_rate",
                    default_vat,
                )
                item["default_category"] = mapping.get("default_category") or item["default_category"]
            else:
                item["bank_account_id"] = None
                item["default_kdv_rate"] = default_vat
        return menu_items

    def _bank_label(self, acc):
        """Banka hesabı tuple'ından okunabilir etiket oluştur."""
        try:
            acc_id = self._bank_field(acc, "id", 0)
            bank = str(self._bank_field(acc, "bank_name", 1, "") or "").strip()
            acc_name = str(self._bank_field(acc, "account_holder", 2, "") or "").strip()
            if not acc_name:
                acc_name = str(self._bank_field(acc, "account_name", 3, "") or "").strip()
            acc_no = str(self._bank_field(acc, "account_number", 4, "") or "").strip()
            if not acc_no:
                acc_no = str(self._bank_field(acc, "account_no", 4, "") or "").strip()
            parts = [p for p in [bank, acc_name] if p]
            label = " - ".join(parts) if parts else "Banka Hesabı"
            if acc_no:
                label = f"{label} ({acc_no})"
            return label, acc_id
        except Exception:
            return "Banka Hesabı", None

    def _make_bank_combo(self, selected_bank_id=None):
        """Banka hesabı seçim combo'su oluştur."""
        cmb = QComboBox()
        cmb.setMinimumWidth(200)
        cmb.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 4px 8px; min-height: 28px; } "
            "QComboBox:focus { border-color: @accent; }"
        ))
        cmb.addItem("Atanmamış", None)
        selected_idx = 0
        for acc in self.bank_accounts:
            try:
                is_active = int(self._bank_field(acc, "is_active", 7, 0) or 0)
            except (IndexError, ValueError):
                is_active = 0
            if is_active != 1:
                continue
            label, acc_id = self._bank_label(acc)
            cmb.addItem(label, acc_id)
            if acc_id == selected_bank_id:
                selected_idx = cmb.count() - 1
        cmb.setCurrentIndex(selected_idx)
        return cmb

    def _make_kdv_spin(self, value=20):
        """KDV oranı spin box'ı oluştur."""
        spin = QDoubleSpinBox()
        spin.setRange(0, 100)
        spin.setDecimals(0)
        spin.setSuffix(" %")
        spin.setValue(float(value or 20))
        spin.setFixedWidth(80)
        spin.setStyleSheet(theme_qss(
            "QDoubleSpinBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 4px 30px 4px 6px; min-height: 28px; } "
            "QDoubleSpinBox:focus { border-color: @accent; } "
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 24px; subcontrol-origin: border; background-color: @accent; border-left: 1px solid @border; } "
            "QDoubleSpinBox::up-button { subcontrol-position: top right; border-bottom: 1px solid @border; } "
            "QDoubleSpinBox::down-button { subcontrol-position: bottom right; border-top: 1px solid @border; } "
            "QDoubleSpinBox::up-arrow { image: none; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid @selection_text; } "
            "QDoubleSpinBox::down-arrow { image: none; width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid @selection_text; }"
        ))
        return spin

    def _make_category_combo(self, selected=None):
        """Gelir kategorisi combo'su oluştur."""
        cmb = QComboBox()
        cmb.setMinimumWidth(100)
        cmb.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 4px 8px; min-height: 28px; } "
            "QComboBox:focus { border-color: @accent; }"
        ))
        for cat in self.INCOME_CATEGORIES:
            cmb.addItem(cat)
        if selected:
            idx = cmb.findText(selected)
            if idx >= 0:
                cmb.setCurrentIndex(idx)
        return cmb

    def _populate_table(self):
        """Tabloyu stok/hizmet verileriyle doldur."""
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.menu_items))

        for row_idx, item in enumerate(self.menu_items):
            menu_item = QTableWidgetItem(str(item.get("menu_name", "")))
            menu_item.setData(Qt.ItemDataRole.UserRole, {
                "item_type": item.get("item_type", "product"),
                "item_id": item.get("item_id", 0),
            })
            self.table.setItem(row_idx, 0, menu_item)

            bank_combo = self._make_bank_combo(item.get("bank_account_id"))
            self.table.setCellWidget(row_idx, 1, bank_combo)

            kdv_spin = self._make_kdv_spin(
                item.get(
                    "default_kdv_rate",
                    TaxSettings.get_percent(self.db),
                )
            )
            self.table.setCellWidget(row_idx, 2, kdv_spin)

            default_cat = item.get("default_category") or "Satış"
            cat_combo = self._make_category_combo(default_cat)
            self.table.setCellWidget(row_idx, 3, cat_combo)

        self.table.resizeRowsToContents()

    def _filter_table(self, text):
        """Arama metnine göre satırları filtrele."""
        search = text.strip().lower()
        for row_idx in range(self.table.rowCount()):
            menu_item = self.table.item(row_idx, 0)
            name = (menu_item.text() if menu_item else "").lower()
            visible = not search or search in name
            self.table.setRowHidden(row_idx, not visible)

    def save_all(self):
        """Tüm eşleştirmeleri kaydet."""
        saved = 0
        for row_idx in range(self.table.rowCount()):
            type_item = self.table.item(row_idx, 0)
            if not type_item:
                continue
            data = type_item.data(Qt.ItemDataRole.UserRole)
            if not data:
                continue

            item_type = data["item_type"]
            item_id = data["item_id"]

            bank_combo = self.table.cellWidget(row_idx, 1)
            kdv_spin = self.table.cellWidget(row_idx, 2)
            cat_combo = self.table.cellWidget(row_idx, 3)

            bank_id = bank_combo.currentData() if bank_combo else None
            kdv_rate = kdv_spin.value() if kdv_spin else 20
            income_cat = cat_combo.currentText() if cat_combo else "Satış"

            if bank_id is not None:
                self.db.set_product_bank_mapping(
                    item_type, item_id, bank_id, kdv_rate, income_cat
                )
                saved += 1
            else:
                # Atanmamış seçildiyse mevcut eşleştirmeyi sil
                self.db.delete_product_bank_mapping(item_type, item_id)

        show_success(self, f"{saved} eşleştirme kaydedildi.")

    def open_bulk_assign_dialog(self):
        """Kategoriye göre toplu banka ataması dialog'u aç."""
        dlg = MenuBankAssignDialog(self.db, self.bank_accounts, self)
        if dlg.exec():
            self.load_data()

    def notify(self, msg, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(msg, level)


class MenuBankAssignDialog(QtDialog):
    """Menüye göre banka ataması dialog'u."""

    def __init__(self, db, bank_accounts, parent=None):
        super().__init__(parent)
        self.db = db
        self.bank_accounts = bank_accounts
        self.setWindowTitle("Menüye Göre Banka Ataması")
        self.setMinimumWidth(420)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Menüye Göre Banka Ataması")
        title.setStyleSheet(theme_qss("font-size: 15px; font-weight: 700; color: @text;"))
        layout.addWidget(title)

        desc = QLabel("Seçtiğiniz menüye varsayılan banka hesabı, KDV ve gelir kategorisi atayın.")
        desc.setWordWrap(True)
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(12)

        # Kategori seçimi
        self.cmb_menu = QComboBox()
        self.cmb_menu.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px; min-height: 34px; }"
        ))
        self.cmb_menu.addItem("Stok Yönetimi", "product_stock")
        self.cmb_menu.addItem("Mobil Stok", "product_mobile")
        self.cmb_menu.addItem("Hizmet Tanımları", "service_definitions")
        self.cmb_menu.addItem("Emanet (Konsinye) Cihazlar", "product_loaner")
        form.addRow("Menü:", self.cmb_menu)

        # Banka seçimi
        self.cmb_bank = QComboBox()
        self.cmb_bank.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px; min-height: 34px; }"
        ))
        for acc in self.bank_accounts:
            try:
                is_active = int(ProductBankMappingWidget._bank_field(acc, "is_active", 7, 0) or 0)
            except (IndexError, ValueError):
                is_active = 0
            if is_active != 1:
                continue
            bank = str(ProductBankMappingWidget._bank_field(acc, "bank_name", 1, "") or "").strip()
            acc_name = str(ProductBankMappingWidget._bank_field(acc, "account_holder", 2, "") or "").strip()
            if not acc_name:
                acc_name = str(ProductBankMappingWidget._bank_field(acc, "account_name", 3, "") or "").strip()
            parts_list = [p for p in [bank, acc_name] if p]
            label = " - ".join(parts_list) if parts_list else "Banka Hesabı"
            self.cmb_bank.addItem(label, ProductBankMappingWidget._bank_field(acc, "id", 0))
        form.addRow("Banka Hesabı:", self.cmb_bank)

        # KDV
        self.spin_kdv = QDoubleSpinBox()
        self.spin_kdv.setRange(0, 100)
        self.spin_kdv.setDecimals(0)
        self.spin_kdv.setSuffix(" %")
        self.spin_kdv.setValue(TaxSettings.get_percent(self.db))
        self.spin_kdv.setStyleSheet(theme_qss(
            "QDoubleSpinBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px 36px 8px 10px; min-height: 34px; } "
            "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button { width: 28px; subcontrol-origin: border; background-color: @accent; border-left: 1px solid @border; } "
            "QDoubleSpinBox::up-button { subcontrol-position: top right; border-bottom: 1px solid @border; } "
            "QDoubleSpinBox::down-button { subcontrol-position: bottom right; border-top: 1px solid @border; } "
            "QDoubleSpinBox::up-arrow { image: none; width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-bottom: 7px solid @selection_text; } "
            "QDoubleSpinBox::down-arrow { image: none; width: 0; height: 0; border-left: 5px solid transparent; border-right: 5px solid transparent; border-top: 7px solid @selection_text; }"
        ))
        form.addRow("Varsayılan KDV:", self.spin_kdv)

        self.cmb_income_category = QComboBox()
        self.cmb_income_category.setStyleSheet(theme_qss(
            "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 8px; min-height: 34px; }"
        ))
        for cat in ProductBankMappingWidget.INCOME_CATEGORIES:
            self.cmb_income_category.addItem(cat)
        form.addRow("Gelir Kategorisi:", self.cmb_income_category)

        layout.addLayout(form)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(40)
        btn_cancel.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 8px; padding: 0 20px; font-weight: 700; }"
        ))
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_apply = QPushButton("Uygula")
        btn_apply.setFixedHeight(40)
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.setStyleSheet(theme_qss(
            "QPushButton { background: @success; color: @selection_text; border-radius: 8px; "
            "padding: 0 20px; font-weight: 700; }"
        ))
        btn_apply.clicked.connect(self._apply)
        btn_row.addWidget(btn_apply)

        layout.addLayout(btn_row)

    def _apply(self):
        menu_type = self.cmb_menu.currentData()
        bank_id = self.cmb_bank.currentData()
        kdv = self.spin_kdv.value()
        income_cat = self.cmb_income_category.currentText()

        if not menu_type:
            show_warning(self, "Lütfen bir menü seçin.")
            return
        if bank_id is None:
            show_warning(self, "Lütfen bir banka hesabı seçin.")
            return

        self.db.set_product_bank_mapping(menu_type, 0, bank_id, kdv, income_cat)
        show_success(self, "Menü eşleştirmesi güncellendi.")
        self.accept()
