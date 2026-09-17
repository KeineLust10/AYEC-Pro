# -*- coding: utf-8 -*-
from PyQt6.QtCore import QObject, pyqtSignal
from PIL import Image, ImageOps
import tempfile
import os
from pathlib import Path

class _OcrWorker(QObject):
    """OCR işlemini arka thread'de çalıştırır; UI donmaz."""
    finished = pyqtSignal(object)

    def __init__(self, source_path, rect, apply_mode=False, fallback_rows=None):
        super().__init__()
        self.source_path = source_path
        self.rect = rect
        self.apply_mode = apply_mode
        self.fallback_rows = fallback_rows or []

    def run(self):
        try:
            img = Image.open(self.source_path)
            img = ImageOps.exif_transpose(img)
            left = max(0, self.rect.x())
            top = max(0, self.rect.y())
            right = min(img.width, self.rect.x() + self.rect.width())
            bottom = min(img.height, self.rect.y() + self.rect.height())
            if right - left < 30 or bottom - top < 30:
                self.finished.emit({"rows": [], "warnings": ["Secili alan cok kucuk."]})
                return

            reparsed = self._parse_crop(img, left, top, right, bottom)
            raw = reparsed.get("rows") or []
            if len(raw) <= 1:
                w, h = max(1, right - left), max(1, bottom - top)
                pad_x, pad_y = max(60, int(w * 0.25)), max(80, int(h * 0.45))
                expanded = (max(0, left - pad_x), max(0, top - pad_y), min(img.width, right + pad_x), min(img.height, bottom + pad_y))
                candidate = self._parse_crop(img, *expanded)
                if self._rows_quality_score(candidate.get("rows") or []) > self._rows_quality_score(raw):
                    reparsed = candidate; raw = reparsed.get("rows") or []

            if self.apply_mode and len(raw) <= 1 and len(self.fallback_rows) > len(raw):
                reparsed = {"rows": self.fallback_rows, "warnings": ["Secili alan zayif sonuc verdi; mevcut on tarama satirlari kullanildi."]}
                raw = self.fallback_rows

            result = []
            from src.ui.dialogs.stock_import_preview_dialog import StockImportPreviewDialog # Circular avoidance
            for r in raw:
                name = str(r.get("name") or "").strip()
                if not name: continue
                brand = str(r.get("brand") or "").strip()
                if not brand: brand, name = StockImportPreviewDialog._split_brand_from_name(name)
                result.append({
                    "name": name, "stock": r.get("stock") or "", "purchase_price": r.get("purchase_price") or "",
                    "price": r.get("price") or "", "line_total": r.get("line_total") or "",
                    "currency": str(r.get("currency") or "TRY").strip(), "brand": brand,
                    "_confidence": r.get("_confidence") or 1.0, "_flags": r.get("_flags") or []
                })
            reparsed["rows"] = result
            self.finished.emit(reparsed if self.apply_mode else {"rows": result})
        except Exception as exc:
            self.finished.emit({"rows": [], "warnings": [f"OCR hatasi: {exc}"]})

    def _parse_crop(self, img, left, top, right, bottom):
        cropped = img.crop((left, top, right, bottom))
        fd, tmp_name = tempfile.mkstemp(prefix=f"ayec_stock_area_{Path(self.source_path).stem}_", suffix=".png")
        try:
            os.close(fd); cropped.save(tmp_name)
            from src.utils.stock_import_parser import StockImportParser
            return StockImportParser.parse_selected_area(tmp_name)
        finally:
            try: os.remove(tmp_name)
            except Exception: pass

    @staticmethod
    def _rows_quality_score(rows):
        score = 0.0
        for row in rows or []:
            if str(row.get("name") or "").strip(): score += 5.0
            if float(row.get("stock") or 0) > 0: score += 2.0
            if float(row.get("purchase_price") or 0) > 0: score += 2.0
            if str(row.get("currency") or "").strip(): score += 0.5
        return score + len(rows or [])
