# -*- coding: utf-8 -*-
# stock_import_parser.py  —  Public API
#
# Tüm mixin sınıfları burada birleştirilir.
# Dış import'lar DEĞİŞMEZ:
#   from src.utils.stock_import_parser import StockImportParser
#
# Mimari: Her _Sip* dosyası bağımsız bir mixin sınıfıdır.
# StockImportParser hepsini tek MRO zincirinde miras alır.

from pathlib import Path

from ._sip_lazy_imports import _ensure_heavy_imports
from ._sip_constants       import _SipConstants
from ._sip_utils           import _SipUtils
from ._sip_ocr             import _SipOcr
from ._sip_normalize       import _SipNormalize
from ._sip_invoice_line    import _SipInvoiceLine
from ._sip_invoice_parsers import _SipInvoiceParsers
from ._sip_image           import _SipImage
from ._sip_file            import _SipFile


class StockImportParser(
    _SipConstants,
    _SipUtils,
    _SipOcr,
    _SipNormalize,
    _SipInvoiceLine,
    _SipInvoiceParsers,
    _SipImage,
    _SipFile,
):
    """
    Stok içe aktarma parser'ı.

    Desteklenen formatlar:
      .xlsx / .xls  — Excel
      .csv          — Virgülle ayrılmış değerler
      .pdf          — pdfplumber (tablo) + OCR fallback
      .xml          — UBL e-Fatura XML
      .docx         — Word belgesi (metin tabanlı)
      .jpg/.png/...  — Görsel OCR (EasyOCR / Tesseract)

    Public API:
      StockImportParser.parse_file(path)         → dict
      StockImportParser.parse_selected_area(path) → dict
      StockImportParser.build_profile_mapping(detected_columns, profile_name) → dict
    """

    @classmethod
    def parse_file(cls, path):
        """Verilen dosyayı parse et ve normalize edilmiş satırları döndür."""
        _ensure_heavy_imports()  # ağır kütüphaneleri lazy yükle

        file_path = Path(path)
        ext       = file_path.suffix.lower()
        warnings  = []
        parsed    = {
            "raw_rows": [],
            "metadata": {},
            "detected_columns": [],
            "suggested_mapping": {},
        }

        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError("Desteklenmeyen dosya turu.")

        # e-Arşiv XML eşlik mi ediyor?
        companion_xml = cls._find_companion_xml(file_path) if ext != ".xml" else None
        if companion_xml:
            xml_parsed = cls._parse_xml_invoice(companion_xml)
            if xml_parsed.get("raw_rows"):
                parsed   = xml_parsed
                metadata = parsed.get("metadata") or {}
                metadata["xml_source"] = str(companion_xml)
                parsed["metadata"] = metadata
                warnings.append(
                    "Ayni klasorde bulunan e-Arsiv XML ile OCR yerine dogrudan veri alindi."
                )

        if ext in {".xlsx", ".xls"} and not parsed.get("raw_rows"):
            parsed = cls._parse_spreadsheet(file_path)
        elif ext == ".csv" and not parsed.get("raw_rows"):
            parsed = cls._parse_csv(file_path)
        elif ext == ".docx":
            parsed = cls._parse_text_content(cls._read_docx_text(file_path))
        elif ext == ".xml":
            parsed = cls._parse_xml_invoice(file_path)
        elif ext == ".pdf":
            if not parsed.get("raw_rows"):
                parsed = cls._parse_pdf_document(file_path)
            metadata = parsed.get("metadata") or {}
            metadata.setdefault("import_engine", "pdfplumber")
            metadata.setdefault("import_mode", "pdf")
            parsed["metadata"] = metadata
        else:
            if not parsed.get("raw_rows"):
                paddle_rows = cls._parse_selected_area_with_paddle_boxes(file_path)
                if paddle_rows:
                    parsed = {
                        "raw_rows": paddle_rows,
                        "detected_columns": ["name", "stock", "purchase_price", "line_total", "currency"],
                        "suggested_mapping": {
                            "name": "name",
                            "stock": "stock",
                            "purchase_price": "purchase_price",
                            "line_total": "line_total",
                            "currency": "currency",
                        },
                        "metadata": {"parser": "paddleocr_boxes"},
                    }
                else:
                    parsed = cls._parse_image(file_path)
            metadata = parsed.get("metadata") or {}
            metadata.setdefault("import_engine", "PaddleOCR/LayoutLM-ready OCR")
            metadata.setdefault("import_mode", "image")
            parsed["metadata"] = metadata
            if not parsed.get("raw_rows"):
                grid_rows = cls._parse_grid_rows_from_image(file_path)
                if grid_rows:
                    detected_cols = cls._detect_columns_from_rows(grid_rows)
                    mapping_grid  = cls._match_column_names(detected_cols)
                    parsed = {
                        "raw_rows": grid_rows,
                        "detected_columns": detected_cols,
                        "suggested_mapping": mapping_grid,
                        "metadata": {},
                    }
            if not parsed.get("raw_rows"):
                warnings.append(
                    "Gorselden okunabilir stok satiri bulunamadi. "
                    "Listeyi onizlemede duzenleyebilirsiniz."
                )

        raw_rows = parsed.get("raw_rows") or []
        mapping  = parsed.get("suggested_mapping") or {}

        if raw_rows and cls._looks_like_internal_rows(raw_rows):
            mapping = {
                field: field
                for field in cls.FIELD_ORDER
                if any(field in row for row in raw_rows)
            }

        if (parsed.get("metadata") or {}).get("parser") == "paddleocr_boxes":
            rows = list(raw_rows)
        else:
            rows = cls._normalize_mapped_rows(raw_rows, mapping)
        rows = cls._filter_core_rows(rows)

        if not rows:
            warnings.append(
                "Dosyadan otomatik stok satiri cikartilamadi. "
                "Listeyi elle duzenleyebilirsiniz."
            )
        elif ext in cls.IMAGE_EXTENSIONS and len(rows) < 2:
            warnings.append(
                "Gorsel kaynakta az satir algilandi. "
                "Daha net kirpma veya PDF/XML kaynak onerilir."
            )

        metadata = parsed.get("metadata") or {}
        if metadata.get("invoice_scenario"):
            warnings.append(f"Fatura senaryosu algilandi: {metadata['invoice_scenario']}")
        if metadata.get("invoice_type"):
            warnings.append(f"Fatura tipi algilandi: {metadata['invoice_type']}")

        return {
            "rows":              rows,
            "raw_rows":          raw_rows,
            "detected_columns":  parsed.get("detected_columns") or [],
            "suggested_mapping": mapping,
            "warnings":          warnings,
            "metadata":          metadata,
            "source_path":       str(file_path),
            "source_type":       ext.lstrip("."),
        }
