# -*- coding: utf-8 -*-
"""
Hizmet İçe Aktarma Önizleme Dialogu
- StockImportParser tabanlı akıllı parse
- Excel, CSV, PDF, Görsel (OCR) destekli
- Hizmet alanlarına (name, price, currency, description, barcode) özel
"""

import re
import tempfile
import os
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_info, show_success, show_warning
from src.utils.currency_helper import CurrencyHelper

# StockImportParser lazy — modül yüklenirken pandas/PIL/easyocr başlatılmaz
class _LazyParserModule:
    def __getattr__(self, name):
        from src.utils.stock_import_parser import StockImportParser as _P
        return getattr(_P, name)
StockImportParser = _LazyParserModule()

# Teknik Servis alanları
_SERVICE_FIELDS_TECH = [
    ("name",        "Hizmet Adı",         "name"),
    ("price",       "Birim Fiyat",        "purchase_price"),
    ("currency",    "Para Birimi",        "currency"),
    ("description", "Açıklama",           "desc"),
    ("barcode",     "Barkod / Kod",       "code"),
]

# Otomotiv ek alanları
_SERVICE_FIELDS_AUTO = [
    ("name",          "Servis Adı",         "name"),
    ("price",         "Birim Fiyat",        "purchase_price"),
    ("currency",      "Para Birimi",        "currency"),
    ("description",   "Açıklama",           "desc"),
    ("barcode",       "Barkod / Kod",       "code"),
    ("vehicle_type",  "Araç Tipi",          "vehicle_type"),
    ("vehicle_brand", "Marka",              "vehicle_brand"),
    ("vehicle_model", "Model",              "vehicle_model"),
    ("vehicle_year",  "Yıl",               "vehicle_year"),
    ("vehicle_plate", "Plaka",             "vehicle_plate"),
]

# Geriye dönük uyumluluk için
_SERVICE_FIELDS = _SERVICE_FIELDS_TECH
_PARSER_TO_SVC = {p: s for s, _, p in _SERVICE_FIELDS_TECH}
_SVC_TO_PARSER = {s: p for s, _, p in _SERVICE_FIELDS_TECH}

_PARSER_TO_SVC = {p: s for s, _, p in _SERVICE_FIELDS}
_SVC_TO_PARSER = {s: p for s, _, p in _SERVICE_FIELDS}


def _normalize_currency(val: str) -> str:
    val = str(val or "").strip().upper()
    if val in ("USD", "$", "US"):
        return "USD"
    if val in ("EUR", "€"):
        return "EUR"
    return "TRY"


def _to_float(value) -> float:
    try:
        text = str(value).strip()
        if not text:
            return 0.0
        # Sayısal olmayan karakterleri (₺, $, €, boşluk vb.) temizle
        text = "".join(ch for ch in text if ch.isdigit() or ch in ",.-")
        if not text:
            return 0.0
        # Türkçe format: 1.810,50 → binlik=nokta, ondalık=virgül
        # İngilizce format: 1,810.50 → binlik=virgül, ondalık=nokta
        if "," in text and "." in text:
            # Son hangi geliyorsa o ondalık ayraç
            if text.rfind(",") > text.rfind("."):
                # Türkçe: 1.810,50
                text = text.replace(".", "").replace(",", ".")
            else:
                # İngilizce: 1,810.50
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")
        # Sadece nokta varsa: 1.810 → Türk formatında binlik ayraç
        # Eğer rakam kısmı 4+ haneli: binlik ayraç
        elif "." in text:
            parts = text.split(".")
            if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) >= 1:
                # 1.810 → binlik ayraç → 1810
                text = text.replace(".", "")
        return float(text)
    except Exception:
        return 0.0


class ServiceImportPreviewDialog(ModernDialog):
    """
    Akıllı Hizmet/Servis İçe Aktarma Dialogu.

    Kullanım:
        parse_result = StockImportParser.parse_file(path)
        dlg = ServiceImportPreviewDialog(db, parse_result, parent, is_automotive=False)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            parent_page.load_services()
    """

    def __init__(self, db, parse_result: dict, parent=None, is_automotive: bool = False):
        self.db = db
        self.is_automotive = is_automotive
        self._fields = _SERVICE_FIELDS_AUTO if is_automotive else _SERVICE_FIELDS_TECH
        self.parse_result = parse_result or {}
        self._recover_if_empty(parse_result)
        self.raw_rows = list(self.parse_result.get("raw_rows") or [])
        self.source_columns = list(self.parse_result.get("detected_columns") or [])
        if not self.source_columns and self.raw_rows:
            self.source_columns = list(self.raw_rows[0].keys())
        self.current_mapping: dict = {}
        self._mapping_widgets: dict = {}
        self._table: QTableWidget | None = None

        dialog_title = "Akıllı Servis İçe Aktarma" if is_automotive else "Akıllı Hizmet İçe Aktarma"
        super().__init__(
            title=dialog_title,
            parent=parent,
            width=1200,
            height=760,
        )
        self.set_footer_visible(False)
        self._build_ui()
        QTimer.singleShot(80, self._auto_map)

    # ------------------------------------------------------------------
    #  Recovery
    # ------------------------------------------------------------------
    def _recover_if_empty(self, original: dict):
        """Parse sonucu boş gelirse sessizce geç — yeniden parse main thread'i dondurur."""
        return

    # ------------------------------------------------------------------
    #  UI Build
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Kaynak bilgisi
        src_lbl = QLabel(f"Kaynak: {self.parse_result.get('source_path', '-')}")
        src_lbl.setWordWrap(True)
        src_lbl.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        root.addWidget(src_lbl)

        # Uyarılar
        for w in (self.parse_result.get("warnings") or []):
            lbl = QLabel(f"⚠ {w}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(theme_qss("font-size: 12px; color: @warning; font-weight: 600;"))
            root.addWidget(lbl)

        # Sütun eşleme kartı
        root.addWidget(self._build_mapping_card())

        # Önizleme tablosu
        tbl_lbl = QLabel("Önizleme (Düzenlenebilir)")
        tbl_lbl.setStyleSheet(theme_qss("font-weight: 800; font-size: 13px; color: @text;"))
        root.addWidget(tbl_lbl)

        self._table = self._make_table()
        root.addWidget(self._table, 1)

        # Alt butonlar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_add = QPushButton("➕ Satır Ekle")
        btn_add.setStyleSheet(theme_qss("QPushButton { min-height: 38px; min-width: 110px; }"))
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._add_empty_row)

        btn_del = QPushButton("🗑 Seçileni Sil")
        btn_del.setStyleSheet(theme_qss("QPushButton { min-height: 38px; min-width: 110px; }"))
        btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del.clicked.connect(self._remove_selected_rows)

        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(theme_qss("QPushButton { min-height: 38px; min-width: 100px; }"))
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_import = QPushButton("✅ Hizmetleri Kaydet")
        btn_import.setStyleSheet(
            theme_qss(
                "QPushButton { min-height: 38px; min-width: 150px; "
                "background: @success; color: white; font-weight: 700; border-radius: 8px; }"
                "QPushButton:hover { background: @success_hover; }"
            )
        )
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self._save_rows)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_del)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_import)
        root.addLayout(btn_row)

        wrapper = QWidget()
        wrapper.setLayout(root)
        self.content_layout.addWidget(wrapper)

    def _build_mapping_card(self) -> QWidget:
        card = QFrame()
        card.setStyleSheet(
            theme_qss(
                "QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; }"
                "QLabel { border: none; background: transparent; }"
            )
        )
        outer = QVBoxLayout(card)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        title = QLabel("Sütun Eşleme")
        title.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text;"))
        outer.addWidget(title)

        hint = QLabel(
            "Kaynak dosyadaki sütunları hizmet alanlarıyla eşleyin, ardından 'Eşlemeyi Uygula'ya basın."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        grid_layout = QHBoxLayout(inner)
        grid_layout.setSpacing(14)

        choices = ["(Yoksay)"] + self.source_columns

        for svc_key, label, _ in self._fields:
            col_widget = QWidget()
            col_vbox = QVBoxLayout(col_widget)
            col_vbox.setContentsMargins(0, 0, 0, 0)
            col_vbox.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("font-weight: 700; font-size: 12px; color: @text;"))
            combo = QComboBox()
            combo.addItems(choices)
            combo.setMinimumWidth(140)
            combo.setStyleSheet(theme_qss("min-height: 34px;"))
            self._mapping_widgets[svc_key] = combo
            col_vbox.addWidget(lbl)
            col_vbox.addWidget(combo)
            grid_layout.addWidget(col_widget)

        grid_layout.addStretch()
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_apply = QPushButton("Eşlemeyi Uygula")
        btn_apply.setStyleSheet(theme_qss("QPushButton { min-height: 34px; min-width: 130px; }"))
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._apply_mapping)
        actions.addWidget(btn_apply)
        outer.addLayout(actions)

        return card

    def _make_table(self) -> QTableWidget:
        headers = [label for _, label, _ in self._fields]
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.verticalHeader().setVisible(False)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tbl.setAlternatingRowColors(True)
        tbl.setMouseTracking(False)
        tbl.viewport().setMouseTracking(False)
        tbl.verticalHeader().setDefaultSectionSize(42)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        # İç dikey scroll — satır sayısı arttıkça tablo kendi içinde kayar
        tbl.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tbl.setMinimumHeight(220)
        tbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tbl.setStyleSheet(
            theme_qss(
                "QTableWidget { background: @surface_alt; color: @text; "
                "border: 1px solid @border; border-radius: 8px; }"
                "QHeaderView::section { background: @surface; color: @text; "
                "font-weight: 700; border: none; border-bottom: 1px solid @border; padding: 6px; }"
                "QTableWidget::item:hover { background: @surface; color: @text; }"
                "QTableWidget::item:selected:hover { background: @selection_bg; color: @selection_text; }"
            )
        )
        return tbl

    # ------------------------------------------------------------------
    #  Auto-mapping
    # ------------------------------------------------------------------
    def _auto_map(self):
        """Parser'ın önerdiği mapping'i + akıllı hizmet eşlemesini uygula."""
        suggested = dict(self.parse_result.get("suggested_mapping") or {})

        _hints = {
            "name":          ["hizmet", "servis", "aciklama", "adi", "isim", "mal", "urun", "name", "service"],
            "price":         ["fiyat", "tutar", "ucret", "birim", "price", "purchase", "amount"],
            "currency":      ["para", "doviz", "currency", "birim"],
            "description":   ["not", "aciklama", "description", "desc", "yorum"],
            "barcode":       ["barkod", "kod", "code", "referans", "sku", "barcode"],
            "vehicle_type":  ["tip", "type", "arac tipi", "vehicle type"],
            "vehicle_brand": ["marka", "brand", "vehicle brand"],
            "vehicle_model": ["model", "vehicle model"],
            "vehicle_year":  ["yil", "year", "vehicle year", "model yili"],
            "vehicle_plate": ["plaka", "plate", "vehicle plate", "arac plaka"],
        }

        def _norm(s: str) -> str:
            s = s.lower()
            for src, dst in [("ı","i"),("ğ","g"),("ü","u"),("ş","s"),("ö","o"),("ç","c")]:
                s = s.replace(src, dst)
            return re.sub(r"[^a-z0-9]", " ", s)

        # 1. parser'ın suggested_mapping'inden dönüştür (parser_key → svc_key)
        for svc_key, _, parser_key in self._fields:
            if parser_key in suggested:
                self.current_mapping[svc_key] = suggested[parser_key]

        # 2. hâlâ eşlenmemiş alanlar için hint-based
        for svc_key, _, _ in self._fields:
            if svc_key in self.current_mapping:
                continue
            for col in self.source_columns:
                col_n = _norm(col)
                for hint in _hints.get(svc_key, []):
                    if hint in col_n:
                        self.current_mapping[svc_key] = col
                        break
                if svc_key in self.current_mapping:
                    break

        # Widget'ları güncelle
        for svc_key, combo in self._mapping_widgets.items():
            src = self.current_mapping.get(svc_key, "")
            if src and combo.findText(src) >= 0:
                combo.setCurrentText(src)

        self._apply_mapping(silent=True)

    # ------------------------------------------------------------------
    #  Mapping → Table
    # ------------------------------------------------------------------
    def _apply_mapping(self, silent: bool = False):
        mapping = {}
        for svc_key, combo in self._mapping_widgets.items():
            val = combo.currentText()
            if val and val != "(Yoksay)":
                mapping[svc_key] = val
        self.current_mapping = mapping

        source_rows = self.raw_rows or []

        if not source_rows:
            parsed_rows = list(self.parse_result.get("rows") or [])
            service_rows = [self._parser_row_to_svc(r) for r in parsed_rows]
        else:
            service_rows = []
            for raw in source_rows:
                svc_row = {}
                for svc_key, _, _ in self._fields:
                    src_col = mapping.get(svc_key)
                    if src_col:
                        svc_row[svc_key] = str(raw.get(src_col) or "").strip()
                    else:
                        svc_row[svc_key] = ""
                service_rows.append(svc_row)

        service_rows = [r for r in service_rows if r.get("name")]

        if not service_rows and not silent:
            show_warning(self, "Bu eşleme ile hizmet adı bulunan satır oluşmadı.")

        self._load_table(service_rows)

    @staticmethod
    def _parser_row_to_svc(row: dict) -> dict:
        """StockImportParser satırını hizmet satırına dönüştür."""
        return {
            "name":          str(row.get("name") or "").strip(),
            "price":         str(row.get("purchase_price") or row.get("price") or "").strip(),
            "currency":      _normalize_currency(row.get("currency") or "TRY"),
            "description":   str(row.get("desc") or row.get("description") or "").strip(),
            "barcode":       str(row.get("code") or "").strip(),
            "vehicle_type":  str(row.get("vehicle_type") or "").strip(),
            "vehicle_brand": str(row.get("vehicle_brand") or row.get("brand") or "").strip(),
            "vehicle_model": str(row.get("vehicle_model") or row.get("model") or "").strip(),
            "vehicle_year":  str(row.get("vehicle_year") or row.get("year") or "").strip(),
            "vehicle_plate": str(row.get("vehicle_plate") or row.get("plate") or "").strip(),
        }

    def _load_table(self, rows: list):
        if self._table is None:
            return
        self._table.setRowCount(0)
        for row in rows:
            self._append_row(row)
        if not rows:
            self._add_empty_row()

    def _append_row(self, row: dict):
        r = self._table.rowCount()
        self._table.insertRow(r)
        self._table.setRowHeight(r, 42)
        for c, (svc_key, _, _) in enumerate(self._fields):
            val = str(row.get(svc_key) or "")
            item = QTableWidgetItem(val)
            self._table.setItem(r, c, item)

    def _add_empty_row(self):
        self._append_row({k: "" for k, _, _ in self._fields})

    def _remove_selected_rows(self):
        rows = sorted(
            {idx.row() for idx in self._table.selectionModel().selectedRows()},
            reverse=True,
        )
        if not rows:
            show_info(self, "Silmek için en az bir satır seçin.")
            return
        for r in rows:
            self._table.removeRow(r)

    # ------------------------------------------------------------------
    #  Save
    # ------------------------------------------------------------------
    def _collect_rows(self) -> list:
        result = []
        for r in range(self._table.rowCount()):
            row = {}
            for c, (svc_key, _, _) in enumerate(self._fields):
                item = self._table.item(r, c)
                row[svc_key] = item.text().strip() if item else ""
            if row.get("name"):
                result.append(row)
        return result

    def _save_rows(self):
        rows = self._collect_rows()
        if not rows:
            show_warning(self, "Kaydedilecek satır yok.")
            return

        # Program para birimi
        program_currency = CurrencyHelper.get_code(self.db)

        success, fail = 0, 0
        first_error: str = ""
        for row in rows:
            try:
                name = row["name"].upper()
                raw_price = _to_float(row.get("price") or 0)
                row_currency = _normalize_currency(row.get("currency") or "TRY")
                description = row.get("description") or ""
                barcode = row.get("barcode") or ""

                # Fiyatı program para birimine çevir
                if row_currency != program_currency:
                    price = CurrencyHelper.convert_amount(
                        self.db, raw_price, row_currency, program_currency
                    )
                    currency = program_currency
                else:
                    price = raw_price
                    currency = row_currency

                # Otomotiv modunda araç bilgilerini description'a ekle
                if self.is_automotive:
                    auto_parts = " | ".join(
                        f"{k}: {v}" for k, v in [
                            ("Plaka", row.get("vehicle_plate", "")),
                            ("Marka", row.get("vehicle_brand", "")),
                            ("Model", row.get("vehicle_model", "")),
                            ("Yıl", row.get("vehicle_year", "")),
                            ("Tip", row.get("vehicle_type", "")),
                        ] if v
                    )
                    if auto_parts and not description:
                        description = auto_parts
                    elif auto_parts:
                        description = f"{description} | {auto_parts}"

                sid = self.db.add_service(
                    name=name,
                    price=price,
                    description=description,
                    barcode=barcode,
                    currency=currency,
                )
                if sid:
                    success += 1
                else:
                    fail += 1
                    if not first_error:
                        first_error = f"'{name}' kaydedilemedi (db.add_service None döndürdü)"
            except Exception as exc:
                fail += 1
                if not first_error:
                    first_error = traceback.format_exc()

        if success == 0 and fail > 0:
            detail = f"\n\nDetay: {first_error}" if first_error else ""
            show_error(self, f"Hiçbir hizmet kaydedilemedi.{detail}")
            return

        show_success(
            self,
            f"İçe aktarma tamamlandı.\nBaşarılı: {success} | Hatalı: {fail}",
        )
        self.accept()
