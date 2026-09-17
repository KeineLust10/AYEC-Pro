# -*- coding: utf-8 -*-
from pathlib import Path

from src.utils.toast_notification import show_error, show_warning


class StockImportMixin:
    """Stok icin yeni PDF/Resim tabanli akilli ice aktarma akisi."""

    SUPPORTED_IMPORT_MODES = {
        "pdf": {".pdf"},
        "image": {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".ppm"},
        "document": {".xlsx", ".xls", ".csv", ".xml", ".docx"},
    }

    def open_smart_stock_import(self):
        try:
            from src.ui.dialogs.stock_smart_import_dialog import StockSmartImportDialog

            path, import_mode = StockSmartImportDialog.get_import_request(self)
            if not path:
                return

            self._validate_smart_import_request(path, import_mode)
            self._stock_import_mode = import_mode
            self._start_smart_import(path)
        except Exception as exc:
            self._hide_stock_import_overlay()
            show_error(self, f"Akilli ice aktarma hatasi: {exc}")

    def _validate_smart_import_request(self, path, import_mode):
        suffix = Path(path).suffix.lower()
        allowed = self.SUPPORTED_IMPORT_MODES.get(import_mode, set())
        if suffix not in allowed:
            raise ValueError("Secilen dosya tipi bu ice aktarma sekmesiyle uyumlu degil.")

    def _start_smart_import(self, path):
        try:
            worker = getattr(self, "parse_worker", None)
            if worker is not None and worker.isRunning():
                show_warning(
                    self,
                    "Devam eden bir ice aktarma analizi var. Yeni dosya secmeden once mevcut islemin bitmesini bekleyin.",
                )
                return

            worker_cls = self._stock_parse_worker_class()
            self._show_stock_import_overlay()
            self.parse_worker = worker_cls(path)
            self.parse_worker.finished.connect(self._on_parse_done)
            self.parse_worker.error.connect(self._on_parse_error)
            self.parse_worker.finished.connect(self._cleanup_parse_worker)
            self.parse_worker.error.connect(self._cleanup_parse_worker)
            self.parse_worker.start()
        except Exception as exc:
            self._hide_stock_import_overlay()
            show_error(self, f"Akilli ice aktarma hatasi: {exc}")

    def _stock_parse_worker_class(self):
        from ._stock_workers import ParseWorker

        return ParseWorker

    def _on_parse_done(self, parse_result):
        try:
            self._hide_stock_import_overlay()
            if self._looks_like_customer_export(parse_result):
                show_error(
                    self,
                    "Secilen dosya stok listesi degil, musteri kayitlari iceriyor. "
                    "Bu dosyayi Musteri Hub uzerindeki ice aktarma araciyla acin.",
                )
                return
            metadata = dict(parse_result.get("metadata") or {})
            metadata["import_mode"] = getattr(self, "_stock_import_mode", "")
            parse_result["metadata"] = metadata

            from src.ui.dialogs.stock_import_preview_dialog import StockImportPreviewDialog

            preview = StockImportPreviewDialog(
                parent=self,
                parse_result=parse_result,
                db=self.db,
            )
            if preview.exec():
                self.current_page = 0
                self.reload_data()
        except Exception as exc:
            show_error(self, f"Akilli ice aktarma hatasi: {exc}")

    @staticmethod
    def _normalize_import_header(value):
        translation = str.maketrans({
            "\u0131": "i",
            "\u0130": "i",
            "\u015f": "s",
            "\u015e": "s",
            "\u011f": "g",
            "\u011e": "g",
            "\u00fc": "u",
            "\u00dc": "u",
            "\u00f6": "o",
            "\u00d6": "o",
            "\u00e7": "c",
            "\u00c7": "c",
        })
        return " ".join(str(value or "").translate(translation).casefold().split())

    @classmethod
    def _looks_like_customer_export(cls, parse_result):
        source_name = cls._normalize_import_header(
            Path(str(parse_result.get("source_path") or "")).stem
        )
        if "musteri" in source_name:
            return True
        raw_rows = list(parse_result.get("raw_rows") or [])
        detected = list(parse_result.get("detected_columns") or [])
        if raw_rows:
            detected.extend(
                key
                for row in raw_rows[:5]
                if isinstance(row, dict)
                for key in row.keys()
            )
        headers = {cls._normalize_import_header(value) for value in detected}
        customer_markers = {
            "ad soyad",
            "musteri",
            "musteri adi",
            "musteri no",
            "telefon",
            "e-posta",
            "email",
            "vergi no",
            "firma",
        }
        stock_markers = {
            "stok",
            "stok kodu",
            "urun",
            "urun adi",
            "barkod",
            "alis fiyati",
            "satis fiyati",
            "kategori",
        }
        customer_score = len(headers & customer_markers)
        stock_score = len(headers & stock_markers)
        raw_text = cls._normalize_import_header(
            " ".join(
                str(value)
                for row in raw_rows[:3]
                if isinstance(row, dict)
                for value in row.values()
            )
        )
        customer_value_hits = sum(
            marker in raw_text
            for marker in ("ad soyad", "telefon", "e-posta", "musteri")
        )
        if customer_value_hits >= 2 and stock_score < 2:
            return True
        return customer_score >= 2 and customer_score > stock_score

    def _on_parse_error(self, err_msg):
        self._hide_stock_import_overlay()
        show_error(self, f"Dosya analiz hatasi: {err_msg}")

    def _cleanup_parse_worker(self, *_args):
        worker = getattr(self, "parse_worker", None)
        self.parse_worker = None
        if worker is not None:
            worker.deleteLater()

    def _show_stock_import_overlay(self):
        overlay = getattr(self, "_loading_overlay", None)
        if overlay is not None:
            overlay.show_overlay("Dosya analiz ediliyor...")

    def _hide_stock_import_overlay(self):
        overlay = getattr(self, "_loading_overlay", None)
        if overlay is not None:
            overlay.hide_overlay()
