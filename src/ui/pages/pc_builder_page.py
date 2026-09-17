# -*- coding: utf-8 -*-
"""
Bilgisayar Topla Sayfası
Servis Operasyon > Bilgisayar Topla
Bileşen bazlı PC konfigürasyonu, teklif ve satış işlemleri.
"""

import os
import json
import tempfile
import re
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QSizePolicy, QTextEdit, QGridLayout,
    QGraphicsDropShadowEffect, QFileDialog,
    QToolButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.utils.page_ids import PageIds
from src.utils.tax_settings import TaxSettings
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.modern_inputs import InlineNumberStepper

# ──────────────────────────────────────────────────────────────────────────────
#  Sabit Veri
# ──────────────────────────────────────────────────────────────────────────────

PC_COMPONENTS = [
    # (display_name, stock_category, spec_label, spec_options)
    ("Anakart",           "Anakart",           "Form Faktör",   ["ATX", "mATX", "ITX", "E-ATX"]),
    ("İşlemci (CPU)",     "İşlemci",           "Soket",         ["LGA1700", "LGA1200", "AM5", "AM4", "TR4"]),
    ("RAM (Bellek)",      "RAM",               "Tip",           ["DDR5", "DDR4", "DDR3", "ECC DDR4"]),
    ("SSD / M.2",         "SSD",               "Arayüz",        ["NVMe M.2", "SATA SSD", "M.2 SATA"]),
    ("HDD",               "HDD",               "RPM",           ["7200 RPM", "5400 RPM", "10000 RPM"]),
    ("Ekran Kartı (GPU)", "Ekran Kartı",       "Bağlantı",      ["PCIe 4.0 x16", "PCIe 3.0 x16"]),
    ("İşlemci Soğutucu",  "CPU Soğutucu",      "Tip",           ["Hava", "Sıvı (AIO)", "Custom Loop"]),
    ("Güç Kaynağı (PSU)", "Güç Kaynağı",       "Sertifika",     ["80+ Gold", "80+ Platinum", "80+ Bronze", "80+ Titanium"]),
    ("Kasa",              "Kasa",              "Form Faktör",   ["Mid Tower", "Full Tower", "Mini ITX", "Slim ATX"]),
    ("Monitör",           "Monitör",           "Panel",         ["IPS", "VA", "TN", "OLED", "Mini-LED"]),
    ("Klavye",            "Klavye",            "Tip",           ["Mekanik", "Membran", "Hybrid"]),
    ("Mouse",             "Mouse",             "DPI",           ["Standart", "Gaming", "Ergonomik"]),
    ("İşletim Sistemi",   "Yazılım",           "Sürüm",         ["Windows 11 Pro", "Windows 11 Home", "Windows 10 Pro"]),
    ("Thermal Pasta",     "Aksesuar",          "Tip",           ["Standart", "Premium", "Liquid Metal"]),
    ("Kablo Yönetimi",    "Aksesuar",          "Tip",           ["Standart", "Modüler PSU"]),
]

COMMON_BRANDS = {
    "Anakart":       ["ASUS", "MSI", "Gigabyte", "ASRock", "Biostar"],
    "İşlemci":       ["Intel", "AMD"],
    "RAM":           ["Corsair", "Kingston", "G.Skill", "Samsung", "Crucial", "HyperX", "TeamGroup"],
    "SSD":           ["Samsung", "WD", "Seagate", "Crucial", "Kingston", "Sabrent", "Corsair", "ADATA"],
    "HDD":           ["Seagate", "WD", "Toshiba", "HGST"],
    "Ekran Kartı":   ["ASUS", "MSI", "Gigabyte", "Zotac", "Sapphire", "PowerColor", "EVGA", "PNY"],
    "CPU Soğutucu":  ["Noctua", "be quiet!", "Corsair", "Cooler Master", "DeepCool", "Arctic", "Thermalright"],
    "Güç Kaynağı":   ["Corsair", "Seasonic", "be quiet!", "EVGA", "Cooler Master", "Thermaltake", "FSP"],
    "Kasa":          ["Fractal Design", "Phanteks", "NZXT", "Corsair", "Lian Li", "Cooler Master", "be quiet!"],
    "Monitör":       ["LG", "Samsung", "ASUS", "BenQ", "AOC", "Dell", "ViewSonic"],
    "Klavye":        ["Logitech", "Corsair", "Razer", "HyperX", "SteelSeries", "Ducky"],
    "Mouse":         ["Logitech", "Razer", "Corsair", "SteelSeries", "Zowie"],
    "Yazılım":       ["Microsoft", "OEM"],
    "Aksesuar":      ["Noctua", "Thermal Grizzly", "Arctic", "Diğer"],
}

# ──────────────────────────────────────────────────────────────────────────────
#  Bileşen Satırı Widget'ı
# ──────────────────────────────────────────────────────────────────────────────

class ComponentRow(QFrame):
    """Tek bir PC bileşeni için satır."""
    price_changed = pyqtSignal()
    removed       = pyqtSignal(object)   # self

    def __init__(self, db, comp_name, stock_category, spec_label, spec_options, row_index, parent=None):
        super().__init__(parent)
        self.db             = db
        self.comp_name      = comp_name
        self.stock_category = stock_category
        self.spec_label     = spec_label
        self.spec_options   = spec_options
        self.row_index      = row_index
        self._all_parts     = []   # tüm parçalar (category bazlı)
        self._part_map      = {}   # name → row dict

        self.setObjectName("ComponentRow")
        self._setup_ui()
        self._load_parts()

    def _normalize_text(self, value):
        text = str(value or "").strip().lower()
        text = text.replace("ı", "i").replace("ğ", "g").replace("ü", "u")
        text = text.replace("ş", "s").replace("ö", "o").replace("ç", "c")
        text = text.replace("!", "").replace(".", " ")
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _matches_brand(self, brand, name):
        brand_norm = self._normalize_text(brand)
        name_norm = self._normalize_text(name)
        if not brand_norm:
            return True
        if brand_norm in name_norm:
            return True

        aliases = {
            "g skill": ["gskill"],
            "be quiet": ["bequiet"],
            "cooler master": ["coolermaster"],
            "fractal design": ["fractal"],
            "thermal grizzly": ["grizzly"],
            "teamgroup": ["team group"],
        }
        for alias in aliases.get(brand_norm, []):
            if alias in name_norm.replace(" ", "") or alias in name_norm:
                return True
        return False

    def _refresh_brand_options(self):
        current = self.cmb_brand.currentText().strip()
        dynamic_brands = set(COMMON_BRANDS.get(self.stock_category, []))
        for r in self._all_parts:
            try:
                name = str(r["name"] if hasattr(r, "keys") else r[1] or "").strip()
                if not name:
                    continue
                name_upper = name.upper()
                for brand in COMMON_BRANDS.get(self.stock_category, []):
                    if self._matches_brand(brand, name):
                        dynamic_brands.add(brand)
                first_two = " ".join(name.split()[:2]).strip()
                first_one = name.split()[0].strip() if name.split() else ""
                for candidate in [first_two, first_one]:
                    if candidate and len(candidate) > 1 and not candidate.isdigit():
                        if candidate.upper() == candidate and len(candidate) <= 8:
                            dynamic_brands.add(candidate)
                        elif candidate in {"Fractal Design", "Cooler Master", "Thermal Grizzly", "be quiet!"}:
                            dynamic_brands.add(candidate)
            except Exception:
                continue

        self.cmb_brand.blockSignals(True)
        self.cmb_brand.clear()
        self.cmb_brand.addItem("Tüm Markalar")
        for brand in sorted(dynamic_brands, key=lambda x: self._normalize_text(x)):
            self.cmb_brand.addItem(brand)
        idx = self.cmb_brand.findText(current)
        self.cmb_brand.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_brand.blockSignals(False)

    # ── UI Kurulum ────────────────────────────────────────────────────────────
    def _setup_ui(self):
        self.setFixedHeight(56)
        # NOT: QGraphicsDropShadowEffect ComponentRow gibi ComboBox içeren
        # widget'lara UYGULANMAMALI — PyQt6'da popup'ların anında kapanmasına
        # yol açar. Görsel derinlik CSS border ile sağlanır.
        self.setStyleSheet(theme_qss("""
            #ComponentRow {
                background: @surface;
                border: 1px solid @border;
                border-bottom: 2px solid @border;
                border-radius: 10px;
                margin: 2px 0;
            }
            #ComponentRow:hover {
                border: 1px solid @accent;
                border-bottom: 2px solid @accent;
                background: @surface_alt;
            }
        """))

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 0, 12, 0)
        row.setSpacing(8)

        # ── 1. Bileşen Adı ────────────────────────────────────────────────────
        lbl = QLabel(self.comp_name)
        lbl.setFixedWidth(160)
        lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        lbl.setStyleSheet(theme_qss("color: @text;"))
        row.addWidget(lbl)

        # ── 2. Marka ──────────────────────────────────────────────────────────
        self.cmb_brand = QComboBox()
        self.cmb_brand.setFixedWidth(150)
        self.cmb_brand.setFixedHeight(34)
        self.cmb_brand.addItem("Tüm Markalar")
        brands = COMMON_BRANDS.get(self.stock_category, [])
        for b in brands:
            self.cmb_brand.addItem(b)
        self.cmb_brand.setStyleSheet(self._cmb_style())
        self.cmb_brand.currentIndexChanged.connect(self._on_brand_changed)
        row.addWidget(self.cmb_brand)

        # ── 3. Özellik (DDR4 vb.) ─────────────────────────────────────────────
        self.cmb_spec = QComboBox()
        self.cmb_spec.setFixedWidth(135)
        self.cmb_spec.setFixedHeight(34)
        self.cmb_spec.addItem(f"— {self.spec_label} —")
        for opt in self.spec_options:
            self.cmb_spec.addItem(opt)
        self.cmb_spec.setStyleSheet(self._cmb_style())
        # BUG FIX: Spec seçimi ürün filtresini tetiklemeli
        self.cmb_spec.currentIndexChanged.connect(self._on_spec_changed)
        row.addWidget(self.cmb_spec)

        # ── 4. Ürün (Stoktan Filtreli) ────────────────────────────────────────
        self.cmb_product = QComboBox()
        self.cmb_product.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.cmb_product.setFixedHeight(34)
        self.cmb_product.addItem("— Ürün Seç —")
        self.cmb_product.setStyleSheet(self._cmb_style())
        self.cmb_product.currentIndexChanged.connect(self._on_product_changed)
        row.addWidget(self.cmb_product)

        # ── 5. Adet ───────────────────────────────────────────────────────────
        self.spn_qty = InlineNumberStepper(value=1, decimals=0)
        self.spn_qty.setRange(0, 99)
        self.spn_qty.setFixedWidth(112)
        self.spn_qty.setFixedHeight(34)
        self.spn_qty.valueChanged.connect(self._on_qty_changed)
        row.addWidget(self.spn_qty)

        # ── 6. Birim Fiyat ────────────────────────────────────────────────────
        self.spn_price = InlineNumberStepper(value=0.0, decimals=2)
        self.spn_price.setRange(0, 999999)
        self.spn_price.setSuffix(" ₺")
        self.spn_price.setFixedWidth(148)
        self.spn_price.setFixedHeight(34)
        # BUG FIX: Fiyat değişince hem toplam etiketi güncellenmeli hem de üst toplamı tetiklemeli
        self.spn_price.valueChanged.connect(self._on_price_changed)
        row.addWidget(self.spn_price)

        # ── 7. Satır Toplamı ──────────────────────────────────────────────────
        self.lbl_total = QLabel("0,00 ₺")
        self.lbl_total.setFixedWidth(105)
        self.lbl_total.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_total.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lbl_total.setStyleSheet(theme_qss("color: @accent; background: transparent;"))
        row.addWidget(self.lbl_total)

        # ── 8. Stok Göstergesi ────────────────────────────────────────────────
        self.lbl_stock = QLabel("—")
        self.lbl_stock.setFixedWidth(55)
        self.lbl_stock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_stock.setFont(QFont("Segoe UI", 9))
        self.lbl_stock.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        row.addWidget(self.lbl_stock)

        # ── 9. Sil Butonu ─────────────────────────────────────────────────────
        btn_del = QToolButton()
        btn_del.setText("✕")
        btn_del.setFixedSize(28, 28)
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.setStyleSheet(theme_qss("""
            QToolButton { background: transparent; color: @text_muted; border: none; border-radius: 6px; font-size: 13px; }
            QToolButton:hover { background: @danger; color: white; }
        """))
        btn_del.clicked.connect(lambda: self.removed.emit(self))
        row.addWidget(btn_del)

    # ── Stil Yardımcıları ─────────────────────────────────────────────────────
    def _cmb_style(self):
        return theme_qss("""
            QComboBox {
                background: @window;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QComboBox:hover { border-color: @accent; }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView {
                background: @surface;
                color: @text;
                selection-background-color: @accent;
                border: 1px solid @border;
            }
        """)

    def _spin_style(self):
        return theme_qss("""
            QSpinBox, QDoubleSpinBox {
                background: @window;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 3px 34px 3px 8px;
                font-size: 11px;
            }
            QSpinBox:hover, QDoubleSpinBox:hover { border-color: @accent; }
            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
                width: 26px;
                subcontrol-origin: border;
                background-color: @accent;
                border-left: 1px solid @border;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-position: top right;
                border-bottom: 1px solid @border;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-position: bottom right;
                border-top: 1px solid @border;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid @selection_text;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid @selection_text;
            }
        """)

    # ── Stok Yükleme ──────────────────────────────────────────────────────────
    def _load_parts(self):
        """Stock'tan bu kategoriye ait ürünleri yükle.
        Kategori eşleşmesi: büyük/küçük harf bağımsız Python tarafında yapılır,
        böylece DB'deki "ram", "RAM", "Ram" hepsi eşleşir.
        """
        try:
            # Kategori filtresi olmadan tümünü çek, Python tarafında filtrele
            rows, _ = self.db.get_parts_paginated(
                limit=1000, offset=0, search_query="", category="Tümü"
            )
            cat_lower = self.stock_category.lower()
            self._all_parts = []
            for r in (rows or []):
                try:
                    cat = (r["category"] if hasattr(r, "keys") else r[2]) or ""
                    if cat.strip().lower() == cat_lower:
                        self._all_parts.append(r)
                except Exception:
                    pass
            self._part_map = {}
            for r in self._all_parts:
                try:
                    name = r["name"] if hasattr(r, "keys") else r[1]
                    self._part_map[name] = r
                except Exception:
                    pass
            self._refresh_brand_options()
            # Yenileme sonrası mevcut marka + spec filtresini koru
            current_brand = getattr(self, "cmb_brand", None)
            current_spec  = getattr(self, "cmb_spec",  None)
            brand = current_brand.currentText() if current_brand else None
            spec  = current_spec.currentText()  if current_spec  else None
            self._populate_products(
                brand=brand if brand and brand != "Tüm Markalar" else None,
                spec=spec   if spec  and "—" not in spec         else None,
            )
        except Exception as e:
            logger.warning(f"PCBuilder part load error ({self.comp_name}): {e}")

    def _populate_products(self, brand=None, spec=None):
        """Ürün listesini marka ve spec filtresine göre doldur.
        brand : None → filtresiz, str → ürün adında içerik araması
        spec  : None → filtresiz, str → ürün adında içerik araması (DDR4 vb.)
        """
        # Mevcut seçimi sakla
        prev_name = ""
        prev_idx  = self.cmb_product.currentIndex()
        if prev_idx > 0:
            prev_data = self.cmb_product.currentData()
            prev_name = prev_data.get("name", "") if prev_data else ""

        self.cmb_product.blockSignals(True)
        self.cmb_product.clear()

        filtered = []
        for r in self._all_parts:
            try:
                name      = r["name"]  if hasattr(r, "keys") else r[1]
                price     = r["price"] if hasattr(r, "keys") else r[4]
                stock_qty = r["stock"] if hasattr(r, "keys") else r[3]
                name_low  = (name or "").lower()

                code = str((r["code"] if hasattr(r, "keys") and "code" in r.keys() else "") or "")
                desc = str((r["description"] if hasattr(r, "keys") and "description" in r.keys() else "") or "")
                haystack = f"{name} {code} {desc}".lower()

                # Marka filtresi
                if brand and brand != "Tüm Markalar":
                    if not self._matches_brand(brand, haystack):
                        continue
                # Spec filtresi (DDR4, NVMe vb.) — sadece "—" placeholder değilse
                if spec and "—" not in spec:
                    if spec.lower() not in name_low:
                        continue

                filtered.append((name, price, stock_qty))
            except Exception:
                continue

        count = len(filtered)
        placeholder = f"— Ürün Seç ({count} ürün) —" if count else "— Stokta yok —"
        self.cmb_product.addItem(placeholder)

        restore_idx = 0
        for i, (name, price, stock_qty) in enumerate(filtered, start=1):
            stk_int = int(stock_qty or 0)
            display = f"{name}  [{stk_int} adet]"
            self.cmb_product.addItem(display, userData={"name": name, "price": float(price or 0), "stock": stk_int})
            if name == prev_name:
                restore_idx = i   # önceki seçimi geri yükle

        self.cmb_product.blockSignals(False)

        # Önceki seçimi geri yükle (marka değişince değil, yenileme durumunda)
        if restore_idx > 0:
            self.cmb_product.setCurrentIndex(restore_idx)
        else:
            # Seçim kayboldu → fiyat ve stok etiketini sıfırla
            self._reset_price_stock()

    # ── Sinyal İşleyicileri ───────────────────────────────────────────────────
    def _on_brand_changed(self, _):
        brand = self.cmb_brand.currentText()
        spec  = self.cmb_spec.currentText()
        self._populate_products(
            brand=brand if brand != "Tüm Markalar" else None,
            spec=spec if "—" not in spec else None,
        )

    def _on_spec_changed(self, _):
        brand = self.cmb_brand.currentText()
        spec  = self.cmb_spec.currentText()
        self._populate_products(
            brand=brand if brand != "Tüm Markalar" else None,
            spec=spec if "—" not in spec else None,
        )

    def _on_product_changed(self, idx):
        if idx <= 0:
            self._reset_price_stock()
            return
        data = self.cmb_product.currentData()
        if data:
            price     = float(data.get("price") or 0)
            stock_qty = int(data.get("stock") or 0)
            # Sinyali geçici blokla → _update_total tek seferde çalışsın
            self.spn_price.blockSignals(True)
            self.spn_price.setValue(price)
            self.spn_price.blockSignals(False)
            # Stok renk kodlaması
            color = "#10B981" if stock_qty > 3 else "#F59E0B" if stock_qty > 0 else "#EF4444"
            self.lbl_stock.setText(str(stock_qty))
            self.lbl_stock.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent;")
        self._update_total()

    def _on_qty_changed(self, _):
        self._update_total()

    def _on_price_changed(self, _):
        """Kullanıcı fiyatı elle değiştirince toplam ve üst özet güncellenir."""
        self._update_total()

    def _update_total(self):
        qty   = self.spn_qty.value()
        price = self.spn_price.value()
        total = qty * price
        self.lbl_total.setText(f"{total:,.2f} ₺")
        self.price_changed.emit()   # üst PCBuilderPage._recalc() tetiklenir

    def _reset_price_stock(self):
        """Ürün seçimi yokken fiyat ve stok etiketlerini sıfırla."""
        self.lbl_stock.setText("—")
        self.lbl_stock.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        self.spn_price.blockSignals(True)
        self.spn_price.setValue(0.0)
        self.spn_price.blockSignals(False)
        self.lbl_total.setText("0,00 ₺")
        self.price_changed.emit()

    # ── Veri Erişimi ──────────────────────────────────────────────────────────
    def get_row_data(self):
        """Satır verilerini dict olarak döndür."""
        data     = self.cmb_product.currentData() or {}
        qty      = self.spn_qty.value()
        price    = self.spn_price.value()
        brand    = self.cmb_brand.currentText()
        spec     = self.cmb_spec.currentText()
        prod_name = data.get("name", "") if data else ""
        if not prod_name and self.cmb_product.currentIndex() > 0:
            raw = self.cmb_product.currentText()
            prod_name = raw.split("  (Stok:")[0] if "  (Stok:" in raw else raw
        return {
            "component":  self.comp_name,
            "category":   self.stock_category,
            "brand":      brand if brand != "Tüm Markalar" else "",
            "spec":       spec if "—" not in spec else "",
            "product":    prod_name,
            "part_id":    data.get("id"),
            "stock":      data.get("stock"),
            "qty":        qty,
            "unit_price": price,
            "total":      qty * price,
        }

    def is_filled(self):
        return self.cmb_product.currentIndex() > 0 and self.spn_qty.value() > 0


# ──────────────────────────────────────────────────────────────────────────────
#  Müşteri Seçim Satırı (küçük inline arama)
# ──────────────────────────────────────────────────────────────────────────────

class CustomerSearchBar(QFrame):
    customer_selected = pyqtSignal(dict)  # {id, name}

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._customers = []
        self.selected   = None

        self.setObjectName("CustSearch")
        self.setFixedHeight(44)
        self.setStyleSheet(theme_qss("""
            #CustSearch { background: @surface; border: 1px solid @border; border-radius: 10px; }
        """))
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 10, 4)
        lay.setSpacing(8)

        icon_lbl = QLabel("👤")
        icon_lbl.setFont(QFont("Segoe UI", 14))
        icon_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(icon_lbl)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Müşteri ara veya seç…")
        self.search_edit.setFixedHeight(32)
        self.search_edit.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @window; color: @text; border: 1px solid @border;
                border-radius: 8px; padding: 4px 10px; font-size: 11px;
            }
            QLineEdit:focus { border-color: @accent; }
        """))
        lay.addWidget(self.search_edit, 1)

        self.cmb_customer = QComboBox()
        self.cmb_customer.setFixedHeight(32)
        self.cmb_customer.setFixedWidth(250)
        self.cmb_customer.setStyleSheet(theme_qss("""
            QComboBox {
                background: @window; color: @text; border: 1px solid @border;
                border-radius: 8px; padding: 4px 10px; font-size: 11px;
            }
            QComboBox:hover { border-color: @accent; }
            QComboBox::drop-down { border: none; width: 22px; }
            QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @accent; }
        """))
        lay.addWidget(self.cmb_customer)

        self.search_edit.textChanged.connect(self._filter_customers)
        self.cmb_customer.currentIndexChanged.connect(self._on_select)
        self._load_customers()

    def _load_customers(self):
        try:
            self._customers = self.db.get_all_customers() or []
        except Exception:
            self._customers = []
        self._fill_combo(self._customers)

    def _fill_combo(self, customers):
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        self.cmb_customer.addItem("— Müşteri Seç —")
        for c in customers:
            try:
                cid  = c["id"]   if hasattr(c, "keys") else c[0]
                name = c["name"] if hasattr(c, "keys") else c[1]
                self.cmb_customer.addItem(name, userData={"id": cid, "name": name})
            except Exception:
                continue
        self.cmb_customer.blockSignals(False)

    def _filter_customers(self, text):
        if not text:
            self._fill_combo(self._customers)
            return
        filtered = []
        for c in self._customers:
            try:
                name = c["name"] if hasattr(c, "keys") else c[1]
                if text.lower() in name.lower():
                    filtered.append(c)
            except Exception:
                continue
        self._fill_combo(filtered)

    def _on_select(self, idx):
        if idx <= 0:
            self.selected = None
            return
        self.selected = self.cmb_customer.currentData()
        if self.selected:
            self.customer_selected.emit(self.selected)

    def get_selected(self):
        return self.selected

    def clear_selection(self):
        self.selected = None
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)
        self._fill_combo(self._customers)
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.setCurrentIndex(0)
        self.cmb_customer.blockSignals(False)


# ──────────────────────────────────────────────────────────────────────────────
#  Ana Sayfa
# ──────────────────────────────────────────────────────────────────────────────

class PCBuilderPage(QWidget):
    """Bilgisayar Topla — bileşen bazlı PC konfigürasyon & teklif sayfası."""

    def apply_theme_styles(self):
        for child in self.findChildren(QFrame):
            if child.objectName() == "PCHeader":
                child.setStyleSheet(theme_qss("""
                    #PCHeader {
                        background: @surface;
                        border: 1px solid @border;
                        border-radius: 18px;
                    }
                """))
            elif child.objectName() == "PresetBar":
                child.setStyleSheet(theme_qss("""
                    #PresetBar { background: @surface; border: 1px solid @border; border-radius: 10px; }
                """))
            elif child.objectName() == "CustSearch":
                child.setStyleSheet(theme_qss("""
                    #CustSearch { background: @surface; border: 1px solid @border; border-radius: 10px; }
                """))
            elif child.objectName() == "ComponentRow":
                child.setStyleSheet(theme_qss("""
                    #ComponentRow {
                        background: @surface;
                        border: 1px solid @border;
                        border-bottom: 2px solid @border;
                        border-radius: 10px;
                        margin: 2px 0;
                    }
                    #ComponentRow:hover {
                        border: 1px solid @accent;
                        border-bottom: 2px solid @accent;
                        background: @surface_alt;
                    }
                """))

        if hasattr(self, "lbl_offer_no"):
            self.lbl_offer_no.setStyleSheet(theme_qss("""
                color: @text;
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 10px;
                padding: 4px 10px;
            """))

        for row in getattr(self, "_rows", []):
            if hasattr(row, "cmb_brand") and hasattr(row, "_cmb_style"):
                row.cmb_brand.setStyleSheet(row._cmb_style())
            if hasattr(row, "cmb_spec") and hasattr(row, "_cmb_style"):
                row.cmb_spec.setStyleSheet(row._cmb_style())
            if hasattr(row, "cmb_product") and hasattr(row, "_cmb_style"):
                row.cmb_product.setStyleSheet(row._cmb_style())
            if hasattr(row, "lbl_total"):
                row.lbl_total.setStyleSheet(theme_qss("color: @accent; background: transparent;"))
            if hasattr(row, "lbl_stock"):
                data = row.cmb_product.currentData()
                stock_qty = int(data.get("stock") or 0) if data else 0
                color = "#10B981" if stock_qty > 3 else "#F59E0B" if stock_qty > 0 else "#EF4444"
                row.lbl_stock.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent;")

        c_bar = getattr(self, "customer_bar", None)
        if c_bar:
            if hasattr(c_bar, "search_edit"):
                c_bar.search_edit.setStyleSheet(theme_qss("""
                    QLineEdit {
                        background: @window; color: @text; border: 1px solid @border;
                        border-radius: 8px; padding: 4px 10px; font-size: 11px;
                    }
                    QLineEdit:focus { border-color: @accent; }
                """))
            if hasattr(c_bar, "cmb_customer"):
                c_bar.cmb_customer.setStyleSheet(theme_qss("""
                    QComboBox {
                        background: @window; color: @text; border: 1px solid @border;
                        border-radius: 8px; padding: 4px 10px; font-size: 11px;
                    }
                    QComboBox:hover { border-color: @accent; }
                    QComboBox::drop-down { border: none; width: 22px; }
                    QComboBox QAbstractItemView { background: @surface; color: @text; selection-background-color: @accent; }
                """))

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db          = db
        self.main_window = main_window
        self._rows: list[ComponentRow] = []
        self._offer_no   = self._gen_offer_no()

        main_lay = QVBoxLayout(self)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self._build_header(main_lay)

        # İçerik alanı
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.setContentsMargins(20, 16, 20, 16)
        content_lay.setSpacing(12)

        # Müşteri arama
        self._build_customer_bar(content_lay)
        # Filtreler (Hızlı hazır config)
        self._build_preset_bar(content_lay)
        # Bileşen başlıkları
        self._build_column_header(content_lay)
        # Bileşen scroll alanı
        self._build_component_area(content_lay)
        # Özet + Ayarlar
        self._build_summary(content_lay)
        # Aksiyon butonları
        self._build_actions(content_lay)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        main_lay.addWidget(scroll, 1)

        # İlk yükleme
        self._add_default_rows()
        self._recalc()

    def _calculate_totals(self):
        cost = sum(r.get_row_data()["total"] for r in self._rows)
        margin_pct = self.spn_margin.value() / 100.0
        profit = cost * margin_pct
        sale_before = cost + profit

        vat_rate = TaxSettings.ratio_from_text(
            self.cmb_vat.currentText()
        )

        vat_amount = sale_before * vat_rate
        grand_total = sale_before + vat_amount
        return {
            "cost": cost,
            "margin_pct": margin_pct,
            "profit": profit,
            "sale_before": sale_before,
            "vat_rate": vat_rate,
            "vat_amount": vat_amount,
            "grand_total": grand_total,
        }

    def refresh_financial_defaults(self):
        default_percent = TaxSettings.get_percent(self.db)
        vat_text = (
            "KDV Yok"
            if default_percent == 0
            else f"KDV %{default_percent:g}"
        )
        if self.cmb_vat.findText(vat_text) < 0:
            self.cmb_vat.addItem(vat_text)
        self.cmb_vat.setCurrentText(vat_text)
        self._recalc()

    # ──────────────────────────────────────────────────────────────────────────
    #  Header
    # ──────────────────────────────────────────────────────────────────────────
    def _build_header(self, parent_lay):
        header = QFrame()
        header.setObjectName("PCHeader")
        header.setFixedHeight(82)
        header.setStyleSheet(theme_qss("""
            #PCHeader {
                background: @surface;
                border: 1px solid @border;
                border-radius: 18px;
            }
        """))
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        header.setGraphicsEffect(shadow)

        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(28, 0, 28, 0)

        # Sol: İkon + Başlık
        left = QVBoxLayout()
        left.setSpacing(2)
        title = QLabel("🖥  Bilgisayar Topla")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        sub = QLabel("Bileşen seç · Fiyatlandır · Teklif oluştur · Satışa dönüştür")
        sub.setFont(QFont("Segoe UI", 10))
        sub.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        left.addWidget(title)
        left.addWidget(sub)
        hlay.addLayout(left, 1)

        # Sağ: Teklif No + Tarih
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        right.setSpacing(2)
        self.lbl_offer_no = QLabel(f"Teklif No: {self._offer_no}")
        self.lbl_offer_no.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_offer_no.setStyleSheet(theme_qss("""
            color: @text;
            background: @surface_alt;
            border: 1px solid @border;
            border-radius: 10px;
            padding: 4px 10px;
        """))
        self.lbl_offer_no.setAlignment(Qt.AlignmentFlag.AlignRight)
        lbl_date = QLabel(f"Tarih: {datetime.now().strftime('%d.%m.%Y')}")
        lbl_date.setFont(QFont("Segoe UI", 10))
        lbl_date.setStyleSheet(theme_qss("color: @text_muted; background: transparent; padding-right: 4px;"))
        lbl_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.lbl_offer_no)
        right.addWidget(lbl_date)
        hlay.addLayout(right)

        parent_lay.addWidget(header)

    # ──────────────────────────────────────────────────────────────────────────
    #  Müşteri Çubuğu
    # ──────────────────────────────────────────────────────────────────────────
    def _build_customer_bar(self, parent_lay):
        self.customer_bar = CustomerSearchBar(self.db)
        self.customer_bar.customer_selected.connect(self._on_customer_selected)
        parent_lay.addWidget(self.customer_bar)

    def _on_customer_selected(self, data):
        self.lbl_offer_no.setText(f"Teklif No: {self._offer_no}  |  Müşteri: {data.get('name','')}")

    # ──────────────────────────────────────────────────────────────────────────
    #  Hazır Konfigürasyon Çubuğu
    # ──────────────────────────────────────────────────────────────────────────
    def _build_preset_bar(self, parent_lay):
        bar = QFrame()
        bar.setObjectName("PresetBar")
        bar.setFixedHeight(44)
        bar.setStyleSheet(theme_qss("""
            #PresetBar { background: @surface; border: 1px solid @border; border-radius: 10px; }
        """))
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(8)

        lbl = QLabel("Hızlı Şablon:")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        lay.addWidget(lbl)

        presets = [
            ("🏠 Ev & Ofis",    "home"),
            ("🎮 Gaming",        "gaming"),
            ("🎨 İçerik Üretici","content"),
            ("🖥 İş İstasyonu",  "workstation"),
            ("🧹 Temizle",       "clear"),
        ]
        for label, key in presets:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setProperty("preset_key", key)
            btn.setStyleSheet(theme_qss("""
                QPushButton { background: @window; color: @text; border: 1px solid @border;
                    border-radius: 8px; padding: 4px 12px; font-size: 11px; }
                QPushButton:hover { background: @accent; color: white; border-color: @accent; }
            """))
            btn.clicked.connect(lambda _, k=key: self._apply_preset(k))
            lay.addWidget(btn)

        lay.addStretch()

        # Bileşen Ekle butonu
        btn_add = QPushButton("+ Bileşen Ekle")
        btn_add.setFixedHeight(30)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss("""
            QPushButton { background: @success; color: white; border: none;
                border-radius: 8px; padding: 4px 14px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: @accent; }
        """))
        btn_add.clicked.connect(self._show_add_component_dialog)
        lay.addWidget(btn_add)

        parent_lay.addWidget(bar)

    # ──────────────────────────────────────────────────────────────────────────
    #  Kolon Başlıkları
    # ──────────────────────────────────────────────────────────────────────────
    def _build_column_header(self, parent_lay):
        header_row = QFrame()
        header_row.setFixedHeight(32)
        header_row.setObjectName("ColHeader")
        header_row.setStyleSheet(theme_qss("""
            #ColHeader { background: @surface_alt; border-radius: 8px; }
        """))
        lay = QHBoxLayout(header_row)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        cols = [
            ("Bileşen",        160, Qt.AlignmentFlag.AlignLeft),
            ("Marka",          150, Qt.AlignmentFlag.AlignLeft),
            ("Özellik",        135, Qt.AlignmentFlag.AlignLeft),
            ("Ürün (Stoktan)", None, Qt.AlignmentFlag.AlignLeft),
            ("Adet",           56,  Qt.AlignmentFlag.AlignCenter),
            ("Birim Fiyat",    110, Qt.AlignmentFlag.AlignRight),
            ("Toplam",         105, Qt.AlignmentFlag.AlignRight),
            ("Stok",           55,  Qt.AlignmentFlag.AlignCenter),
            ("",               28,  Qt.AlignmentFlag.AlignCenter),
        ]
        for text, width, align in cols:
            lbl = QLabel(text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
            lbl.setAlignment(align)
            if width:
                lbl.setFixedWidth(width)
            else:
                lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            lay.addWidget(lbl)

        parent_lay.addWidget(header_row)

    # ──────────────────────────────────────────────────────────────────────────
    #  Bileşen Alanı
    # ──────────────────────────────────────────────────────────────────────────
    def _build_component_area(self, parent_lay):
        self.rows_container = QWidget()
        self.rows_layout    = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)
        self.rows_layout.addStretch()
        parent_lay.addWidget(self.rows_container)

    def _add_default_rows(self):
        for idx, (name, cat, spec_lbl, spec_opts) in enumerate(PC_COMPONENTS):
            self._add_component_row(name, cat, spec_lbl, spec_opts)

    def _add_component_row(self, comp_name, category, spec_label, spec_options):
        row = ComponentRow(self.db, comp_name, category, spec_label, spec_options,
                           len(self._rows))
        row.price_changed.connect(self._recalc)
        row.removed.connect(self._remove_row)
        # Stretch'ten önce ekle
        count = self.rows_layout.count()
        self.rows_layout.insertWidget(count - 1, row)
        self._rows.append(row)

    def _remove_row(self, row_widget):
        self.rows_layout.removeWidget(row_widget)
        row_widget.deleteLater()
        if row_widget in self._rows:
            self._rows.remove(row_widget)
        self._recalc()

    # ──────────────────────────────────────────────────────────────────────────
    #  Özet Paneli
    # ──────────────────────────────────────────────────────────────────────────
    def _build_summary(self, parent_lay):
        summary = QFrame()
        summary.setObjectName("SummaryPanel")
        # NOT: Burada da QGraphicsDropShadowEffect YOK — cmb_vat ComboBox'ı
        # içeriyor; shadow effect PyQt6'da ComboBox popup'larını bozar.
        summary.setStyleSheet(theme_qss("""
            #SummaryPanel {
                background: @surface;
                border: 1px solid @border;
                border-bottom: 3px solid @accent;
                border-radius: 14px;
            }
        """))

        grid = QGridLayout(summary)
        grid.setContentsMargins(24, 16, 24, 16)
        grid.setHorizontalSpacing(32)
        grid.setVerticalSpacing(8)

        def add_kv(row, col, key, value_widget):
            k = QLabel(key)
            k.setFont(QFont("Segoe UI", 10))
            k.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
            grid.addWidget(k, row, col * 2)
            grid.addWidget(value_widget, row, col * 2 + 1)

        # ── Toplam Maliyet ────────────────────────────────────────────────────
        self.lbl_cost = QLabel("0,00 ₺")
        self.lbl_cost.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_cost.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        add_kv(0, 0, "Maliyet Toplamı:", self.lbl_cost)

        # ── KDV ───────────────────────────────────────────────────────────────
        self.cmb_vat = QComboBox()
        for v in ["KDV Yok", "KDV %1", "KDV %8", "KDV %18", "KDV %20"]:
            self.cmb_vat.addItem(v)
        default_percent = TaxSettings.get_percent(self.db)
        default_vat_text = (
            "KDV Yok"
            if default_percent == 0
            else f"KDV %{default_percent:g}"
        )
        if self.cmb_vat.findText(default_vat_text) < 0:
            self.cmb_vat.addItem(default_vat_text)
        self.cmb_vat.setCurrentText(default_vat_text)
        self.cmb_vat.setFixedWidth(120)
        self.cmb_vat.setFixedHeight(32)
        self.cmb_vat.setStyleSheet(theme_qss("""
            QComboBox { background: @window; color: @text; border: 1px solid @border;
                border-radius: 8px; padding: 3px 8px; font-size: 11px; }
            QComboBox:hover { border-color: @accent; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: @surface; color: @text; }
        """))
        self.cmb_vat.currentIndexChanged.connect(self._recalc)
        add_kv(0, 1, "KDV:", self.cmb_vat)

        # ── KDV Tutarı ────────────────────────────────────────────────────────
        self.lbl_vat_amount = QLabel("0,00 ₺")
        self.lbl_vat_amount.setFont(QFont("Segoe UI", 12))
        self.lbl_vat_amount.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        add_kv(0, 2, "KDV Tutarı:", self.lbl_vat_amount)

        # ── Kâr Marjı ─────────────────────────────────────────────────────────
        self.spn_margin = InlineNumberStepper(value=20, decimals=1)
        self.spn_margin.setRange(0, 500)
        self.spn_margin.setSuffix(" %")
        self.spn_margin.setFixedWidth(134)
        self.spn_margin.setFixedHeight(32)
        self.spn_margin.valueChanged.connect(self._recalc)
        add_kv(1, 0, "Kâr Marjı:", self.spn_margin)

        # ── Kâr Tutarı ────────────────────────────────────────────────────────
        self.lbl_profit = QLabel("0,00 ₺")
        self.lbl_profit.setFont(QFont("Segoe UI", 12))
        self.lbl_profit.setStyleSheet(theme_qss("color: @success; background: transparent;"))
        add_kv(1, 1, "Kâr:", self.lbl_profit)

        # ── Genel Toplam ──────────────────────────────────────────────────────
        self.lbl_grand_total = QLabel("0,00 ₺")
        self.lbl_grand_total.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_grand_total.setStyleSheet(theme_qss("color: @accent; background: transparent;"))
        add_kv(1, 2, "Genel Toplam:", self.lbl_grand_total)

        # ── Notlar ────────────────────────────────────────────────────────────
        note_lbl = QLabel("Teklif Notu:")
        note_lbl.setFont(QFont("Segoe UI", 10))
        note_lbl.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
        grid.addWidget(note_lbl, 2, 0)
        self.txt_note = QTextEdit()
        self.txt_note.setFixedHeight(52)
        self.txt_note.setPlaceholderText("Müşteriye iletilecek notlar, garanti şartları, kurulum ücreti vb.")
        self.txt_note.setStyleSheet(theme_qss("""
            QTextEdit { background: @window; color: @text; border: 1px solid @border;
                border-radius: 8px; padding: 6px 10px; font-size: 11px; }
            QTextEdit:focus { border-color: @accent; }
        """))
        grid.addWidget(self.txt_note, 2, 1, 1, 5)

        parent_lay.addWidget(summary)

    # ──────────────────────────────────────────────────────────────────────────
    #  Aksiyon Butonları
    # ──────────────────────────────────────────────────────────────────────────
    def _build_actions(self, parent_lay):
        bar = QFrame()
        bar.setObjectName("ActionBar")
        bar.setFixedHeight(58)
        bar.setStyleSheet(theme_qss("""
            #ActionBar { background: @surface; border: 1px solid @border; border-radius: 12px; }
        """))
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(10)

        def make_btn(text, color, handler, tooltip=""):
            btn = QPushButton(text)
            btn.setFixedHeight(38)
            btn.setMinimumWidth(140)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if tooltip:
                btn.setToolTip(tooltip)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color}; color: white; border: none;
                    border-radius: 9px; padding: 6px 16px;
                    font-size: 12px; font-weight: bold;
                }}
                QPushButton:hover {{ background: {color}CC; }}
                QPushButton:pressed {{ background: {color}99; }}
            """)
            btn.clicked.connect(handler)
            return btn

        lay.addWidget(make_btn("🖨  PDF Teklif",     "#3B82F6", self._generate_pdf,       "PDF teklif belgesi oluştur"))
        lay.addWidget(make_btn("👤 Müşteri 360",     "#8B5CF6", self._register_customer360, "Müşteri kaydına ekle"))
        lay.addWidget(make_btn("📦 Stok Düşür",      "#10B981", self._deduct_stock,         "Seçili ürünleri stoktan düş"))
        lay.addWidget(make_btn("💰 Finans Kaydı",    "#F59E0B", self._add_finance_record,   "Gelir/gider kaydı oluştur"))
        lay.addWidget(make_btn("📋 Sipariş Kaydet",  "#6366F1", self._save_offer,           "Teklifi sisteme kaydet"))
        lay.addStretch()
        lay.addWidget(make_btn("🗑  Temizle",         "#EF4444", self._clear_all,            "Tüm seçimleri temizle"))

        parent_lay.addWidget(bar)

    # ──────────────────────────────────────────────────────────────────────────
    #  Hesaplama
    # ──────────────────────────────────────────────────────────────────────────
    def _recalc(self):
        totals = self._calculate_totals()
        cost = totals["cost"]
        profit = totals["profit"]
        vat_amount = totals["vat_amount"]
        grand_total = totals["grand_total"]

        self.lbl_cost.setText(f"{cost:,.2f} ₺")
        self.lbl_profit.setText(f"+{profit:,.2f} ₺")
        self.lbl_vat_amount.setText(f"{vat_amount:,.2f} ₺")
        self.lbl_grand_total.setText(f"{grand_total:,.2f} ₺")

    # ──────────────────────────────────────────────────────────────────────────
    #  Hazır Şablon
    # ──────────────────────────────────────────────────────────────────────────
    def _apply_preset(self, key):
        if key == "clear":
            self._clear_all()
            return
        # Preset, sadece kâr marjını ve notu ayarlar
        presets = {
            "home":       (15, "Ev ve Ofis kullanımı için hazırlanmıştır. 1 yıl garanti."),
            "gaming":     (20, "Gaming konfigürasyonu. Yüksek FPS odaklı seçim. 1 yıl garanti."),
            "content":    (22, "Yaratıcı içerik üretimi & video düzenleme için optimize edilmiştir."),
            "workstation":(18, "Profesyonel iş istasyonu. ECC RAM & iş yükü optimizasyonu."),
        }
        margin, note = presets.get(key, (20, ""))
        self.spn_margin.setValue(margin)
        self.txt_note.setPlainText(note)
        self._recalc()

    # ──────────────────────────────────────────────────────────────────────────
    #  Bileşen Ekleme Dialogu
    # ──────────────────────────────────────────────────────────────────────────
    def _show_add_component_dialog(self):
        dlg = _AddComponentDialog(self)
        if dlg.exec() == _AddComponentDialog.DialogCode.Accepted:
            name, cat, spec_lbl, specs = dlg.get_result()
            if name and cat:
                self._add_component_row(name, cat, spec_lbl, specs)
            elif not name:
                self._warn("Bileşen adı boş bırakılamaz.")

    # ──────────────────────────────────────────────────────────────────────────
    #  Eylemler
    # ──────────────────────────────────────────────────────────────────────────
    def _get_filled_rows(self):
        return [r.get_row_data() for r in self._rows if r.is_filled()]

    def _validate(self):
        filled = self._get_filled_rows()
        if not filled:
            self._warn("Lütfen en az bir bileşen seçin.")
            return None
        return filled

    def _generate_pdf(self):
        filled = self._validate()
        if not filled:
            return
        try:
            from src.ui.pages.transaction.dialogs.proforma_dialog import ProformaDialog
            customer = self.customer_bar.get_selected()
            cust_name = customer.get("name", "") if customer else "Perakende Müşteri"
            cust_company = customer.get("company_name", "") if customer else ""
            totals_calc = self._calculate_totals()
            cost = totals_calc["cost"]
            vat_rate = totals_calc["vat_rate"]
            vat_amount = totals_calc["vat_amount"]
            grand_total = totals_calc["grand_total"]

            # Proforma cart_items formatına çevir
            cart_items = []
            for r in filled:
                cart_items.append({
                    "name":     f"{r['component']} — {r['product']}",
                    "brand":    r.get("brand", ""),
                    "qty":      r["qty"],
                    "price":    r["unit_price"],
                    "total":    r["total"],
                    "category": r["category"],
                })
            totals = (
                cost,          # subtotal
                0.0,           # discount
                vat_rate,      # vat_rate
                vat_amount,    # vat_amount
                grand_total,   # total
            )
            dialog = ProformaDialog(
                self,
                self.db,
                cart_items,
                totals,
                cust_name,
                currency_mode="TL",
                customer_id=customer.get("id") if customer else None,
                customer_company=cust_company,
                initial_company=cust_company,
                initial_project=f"Bilgisayar Toplama {self._offer_no}",
                preferred_template="modern",
                source="pc_builder",
            )
            dialog.exec()
        except Exception as e:
            logger.error(f"PCBuilder PDF error: {e}")
            self._err(f"PDF oluşturulamadı: {e}")

    def _register_customer360(self):
        customer = self.customer_bar.get_selected()
        if not customer:
            self._warn("Lütfen önce bir müşteri seçin.")
            return
        filled = self._validate()
        if not filled:
            return
        try:
            lines = "\n".join(
                f"• {r['component']}: {r['product']}  x{r['qty']}  {r['unit_price']:,.2f}₺"
                for r in filled
            )
            totals_calc = self._calculate_totals()
            grand_total = totals_calc["grand_total"]
            note_text = (
                f"[Bilgisayar Teklifi #{self._offer_no}]\n"
                f"{lines}\n"
                f"Teklif Toplamı: {grand_total:,.2f} ₺\n"
                f"{self.txt_note.toPlainText()}"
            )
            ok = self.db.add_customer_note(customer["id"], "Teklif", note_text)
            if not ok:
                raise RuntimeError("Müşteri notu eklenemedi.")
            if self.main_window and hasattr(self.main_window, "open_customer_360_by_id"):
                self.main_window.open_customer_360_by_id(customer["id"])
            self._toast(f"Müşteri 360'a kayıt eklendi: {customer['name']}", "success")
        except Exception as e:
            logger.error(f"PCBuilder customer360 error: {e}")
            self._err(f"Müşteri kaydı eklenemedi: {e}")

    def _deduct_stock(self):
        filled = self._validate()
        if not filled:
            return
        errors = []
        successes = 0
        for r in filled:
            if not r["product"]:
                continue
            try:
                pid = r.get("part_id")
                in_stk = r.get("stock")
                if not pid:
                    self.db.cursor.execute(
                        "SELECT id, stock FROM parts WHERE name=? ORDER BY id DESC LIMIT 1",
                        (r["product"],)
                    )
                    part = self.db.cursor.fetchone()
                    if not part:
                        errors.append(f"{r['product']}: Stokta bulunamadı")
                        continue
                    pid = part[0] if not hasattr(part, "keys") else part["id"]
                    in_stk = int(part[1] if not hasattr(part, "keys") else part["stock"])
                else:
                    in_stk = int(in_stk or 0)
                if not pid:
                    errors.append(f"{r['product']}: Stokta bulunamadı")
                    continue
                qty    = r["qty"]
                if in_stk < qty:
                    errors.append(f"{r['product']}: Yetersiz stok ({in_stk} var, {qty} gerekli)")
                    continue
                self.db.adjust_stock(pid, -qty, f"Bilgisayar Topla — Teklif #{self._offer_no}")
                successes += 1
            except Exception as e:
                errors.append(f"{r['product']}: {e}")

        msg = f"{successes} ürün stoktan düşüldü."
        if errors:
            self._toast(msg, "success") if successes else None
            for err in errors:
                self._warn(err)
        else:
            self._toast(msg, "success")
        # Satırları yenile
        for row in self._rows:
            row._load_parts()

    def _add_finance_record(self):
        filled = self._validate()
        if not filled:
            return
        totals_calc = self._calculate_totals()
        grand_total = totals_calc["grand_total"]
        customer    = self.customer_bar.get_selected()
        cust_name   = customer.get("name") if customer else None
        cust_id     = customer.get("id")   if customer else None
        desc        = f"Bilgisayar Topla / Teklif #{self._offer_no} — {', '.join(r['component'] for r in filled[:3])}{'...' if len(filled) > 3 else ''}"
        try:
            self.db.add_transaction(
                t_type="Gelir",
                category="Satış",
                amount=grand_total,
                description=desc,
                customer_name=cust_name,
                customer_id=cust_id,
                payment_method="Nakit",
            )
            self._toast(f"Finans kaydı oluşturuldu: {grand_total:,.2f} ₺", "success")
        except Exception as e:
            logger.error(f"PCBuilder finance error: {e}")
            self._err(f"Finans kaydı eklenemedi: {e}")

    def _save_offer(self):
        filled = self._validate()
        if not filled:
            return
        try:
            customer   = self.customer_bar.get_selected()
            totals_calc = self._calculate_totals()
            cost = totals_calc["cost"]
            grand = totals_calc["grand_total"]
            margin_pct = totals_calc["margin_pct"]
            vat_rate = totals_calc["vat_rate"]
            lines      = "\n".join(
                f"  • {r['component']}: {r['product']}  ×{r['qty']}  {r['unit_price']:,.2f}₺  = {r['total']:,.2f}₺"
                for r in filled
            )
            note_body = (
                f"[PC Teklif Kaydı] No: {self._offer_no}\n"
                f"Tarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"Müşteri: {customer.get('name','Belirtilmedi') if customer else 'Belirtilmedi'}\n\n"
                f"Bileşenler:\n{lines}\n\n"
                f"Maliyet: {cost:,.2f} ₺  |  Kâr Marjı: {margin_pct*100:.1f}%  |  KDV: %{vat_rate*100:.0f}  |  Toplam: {grand:,.2f} ₺\n"
                f"Not: {self.txt_note.toPlainText()}"
            )
            # Notlar tablosuna kaydet (audit log yerine knowledge base notu)
            if hasattr(self.db, "add_audit_log"):
                self.db.add_audit_log("sistem", "pc_offers", "INSERT", note_body[:500])
            if customer and hasattr(self.db, "add_customer_note"):
                self.db.add_customer_note(customer["id"], "PC Teklif", note_body)
            self._toast(f"Teklif #{self._offer_no} kaydedildi.", "success")
        except Exception as e:
            logger.error(f"PCBuilder save offer error: {e}")
            self._err(f"Teklif kaydedilemedi: {e}")

    def _clear_all(self):
        # Tüm satırları sil ve yeniden oluştur
        for row in list(self._rows):
            self.rows_layout.removeWidget(row)
            row.deleteLater()
        self._rows.clear()
        self._offer_no = self._gen_offer_no()
        self.lbl_offer_no.setText(f"Teklif No: {self._offer_no}")
        self.txt_note.clear()
        self.spn_margin.setValue(20)
        self.customer_bar.clear_selection()
        self._add_default_rows()
        self._recalc()

    # ──────────────────────────────────────────────────────────────────────────
    #  Yardımcılar
    # ──────────────────────────────────────────────────────────────────────────
    def _gen_offer_no(self):
        prefix = str(self.db.get_setting("reference_number_prefix", "REF") or "REF").strip() or "REF"
        next_raw = str(self.db.get_setting("reference_number_next", "1") or "1").strip()
        next_number = int(next_raw) if next_raw.isdigit() else 1
        return f"{prefix}{next_number}"

    def _toast(self, msg, level="info"):
        try:
            from src.ui.widgets.toast_notification import show_success, show_error, show_info, show_warning
            if level == "success":
                show_success(self, msg)
            elif level == "error":
                show_error(self, msg)
            elif level == "warning":
                show_warning(self, msg)
            else:
                show_info(self, msg)
        except Exception as e:
            logger.debug(f"PCBuilder toast fallback: {e}")
            try:
                if self.main_window and hasattr(self.main_window, "show_notification"):
                    self.main_window.show_notification(msg, level)
            except Exception:
                pass

    def _warn(self, msg):
        self._toast(msg, "warning")

    def _err(self, msg):
        self._toast(msg, "error")


# ──────────────────────────────────────────────────────────────────────────────
#  Özel Bileşen Ekleme Dialogu  (BaseModernDialog tabanlı)
# ──────────────────────────────────────────────────────────────────────────────

class _AddComponentDialog(BaseModernDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="➕  Yeni Bileşen Ekle", width=460, height=330)
        self._build_form()

    def _build_form(self):
        field_style = theme_qss("""
            QLabel   { color: @text_muted; font-size: 11px; background: transparent; }
            QLineEdit {
                background: @window; color: @text; border: 1px solid @border;
                border-radius: 9px; padding: 7px 12px; font-size: 12px;
            }
            QLineEdit:focus { border-color: @accent; }
        """)

        def make_field(label_text, placeholder, default=""):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 10))
            lbl.setStyleSheet(theme_qss("color: @text_muted; background: transparent;"))
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(36)
            edit.setStyleSheet(theme_qss("""
                QLineEdit {
                    background: @window; color: @text; border: 1px solid @border;
                    border-radius: 9px; padding: 6px 12px; font-size: 12px;
                }
                QLineEdit:focus { border-color: @accent; }
            """))
            if default:
                edit.setText(default)
            self.content_layout.addWidget(lbl)
            self.content_layout.addWidget(edit)
            return edit

        self.edit_name = make_field(
            "Bileşen Adı  *",
            "Örn: Optik Sürücü, UPS, Web Kamerası…"
        )
        self.edit_cat = make_field(
            "Stok Kategorisi  *",
            "Örn: Optik Sürücü  (stok tablosundaki kategori adı)"
        )
        self.edit_spec = make_field(
            "Özellik Etiketi",
            "Örn: Tip, Bağlantı, Hız…",
            default="Standart"
        )

        self.content_layout.addStretch()

        # ── Alt buton çubuğu ──────────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        btn_ok = QPushButton("➕  Ekle")
        btn_ok.setFixedHeight(38)
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setStyleSheet(theme_qss("""
            QPushButton {
                background: @accent; color: white; border: none;
                border-radius: 10px; padding: 6px 24px;
                font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background: @accent_hover; }
        """))
        btn_ok.clicked.connect(self.accept)

        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedHeight(38)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background: @surface; color: @text; border: 1px solid @border;
                border-radius: 10px; padding: 6px 20px; font-size: 12px;
            }
            QPushButton:hover { background: @surface_alt; }
        """))
        btn_cancel.clicked.connect(self.reject)

        btn_bar.addStretch()
        btn_bar.addWidget(btn_cancel)
        btn_bar.addWidget(btn_ok)
        self.content_layout.addLayout(btn_bar)

    def get_result(self):
        return (
            self.edit_name.text().strip(),
            self.edit_cat.text().strip(),
            self.edit_spec.text().strip() or "Tip",
            ["Standart"],
        )
