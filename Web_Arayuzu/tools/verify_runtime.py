#!/usr/bin/env python3
"""AYEC Pro'nun sunucuya taşınan PDF ve içe aktarma motorunu doğrular."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = (
    ROOT
    if (ROOT / "src" / "utils" / "stock_import_parser.py").is_file()
    else ROOT.parent
)
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))


class _Settings:
    def __init__(self, logo_path: str = "") -> None:
        self.values = {
            "company_name": "AYEC Pro Test",
            "company_phone": "+90 555 000 00 00",
            "company_email": "test@example.com",
            "company_address": "Türkiye",
            "logo_path": logo_path,
            "offer_contract": "Fiyatlar test amaçlıdır.",
        }

    def get_setting(self, key: str, default=""):
        return self.values.get(key, default)


def _version(module, *names: str) -> str:
    for name in names:
        value = getattr(module, name, None)
        if value:
            return str(value)
    return "yüklü"


def verify(require_ocr: bool = False) -> dict:
    import defusedxml
    import numpy
    import openpyxl
    import pandas
    import pdfplumber
    import PIL
    import pypdf
    import pytesseract
    import reportlab

    from src.utils.pdf_manager import PDFManagerQt
    from src.utils.stock_import_parser import StockImportParser

    report = {
        "python": sys.version.split()[0],
        "packages": {
            "defusedxml": _version(defusedxml, "__version__"),
            "numpy": _version(numpy, "__version__"),
            "openpyxl": _version(openpyxl, "__version__"),
            "pandas": _version(pandas, "__version__"),
            "pdfplumber": _version(pdfplumber, "__version__"),
            "pillow": _version(PIL, "__version__"),
            "pypdf": _version(pypdf, "__version__"),
            "pytesseract": _version(pytesseract, "__version__"),
            "reportlab": _version(reportlab, "Version", "__version__"),
        },
        "pdf_templates": [],
        "smart_import": False,
        "tesseract": "",
    }
    optional_packages = {
        "easyocr": "easyocr",
        "opencv": "opencv-python-headless",
        "torch": "torch",
        "torchvision": "torchvision",
        "scikit-image": "scikit-image",
        "paddleocr": "paddleocr",
        "paddlepaddle": "paddlepaddle",
    }
    report["optional_packages"] = {}
    for label, distribution in optional_packages.items():
        try:
            report["optional_packages"][label] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            report["optional_packages"][label] = ""

    tesseract_cmd = os.environ.get("TESSERACT_CMD", "").strip() or shutil.which("tesseract") or ""
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        try:
            report["tesseract"] = f"{tesseract_cmd} ({pytesseract.get_tesseract_version()})"
        except Exception as error:
            if require_ocr:
                raise RuntimeError(f"Tesseract çalıştırılamadı: {error}") from error
            report["tesseract"] = f"bulundu fakat doğrulanamadı: {error}"
    elif require_ocr:
        raise RuntimeError("Tesseract bulunamadı; TESSERACT_CMD tanımlayın.")

    with tempfile.TemporaryDirectory(prefix="ayec-runtime-") as temp_dir:
        temp = Path(temp_dir)

        class _PDFManager(PDFManagerQt):
            def _open_file(self, filename):
                return None

        manager = _PDFManager(_Settings())
        items = [
            {
                "service": "Kamera Sistemi",
                "description": "Sunucu taşınabilirlik testi",
                "qty": 2,
                "price": 1250.0,
                "currency": "TRY",
            }
        ]
        totals = (2500.0, 0.0, 0.20, 500.0, 3000.0)
        for template in ("modern", "corporate", "minimal"):
            target = temp / f"{template}.pdf"
            ok, result = manager.create_proforma(
                template,
                items,
                totals,
                company_name="AYEC Pro Test",
                customer_name="Test Müşteri",
                save_path=str(target),
                currency="TL",
                reference_no="PRF-TEST-0001",
            )
            if not ok:
                raise RuntimeError(f"{template} PDF üretilemedi: {result}")
            if not target.exists() or target.read_bytes()[:4] != b"%PDF":
                raise RuntimeError(f"{template} PDF çıktısı geçersiz.")
            if not pypdf.PdfReader(str(target)).pages:
                raise RuntimeError(f"{template} PDF sayfası bulunamadı.")
            report["pdf_templates"].append(template)

        csv_path = temp / "stok.csv"
        csv_path.write_text(
            "Stok Kodu,Ürün Adı,Kategori,Stok,Alış Fiyatı,Satış Fiyatı,Para Birimi\n"
            "TEST-001,IP Kamera,Güvenlik Sistemleri,4,1000,1500,TRY\n",
            encoding="utf-8-sig",
        )
        parsed = StockImportParser.parse_file(csv_path)
        if not parsed.get("rows"):
            raise RuntimeError("Akıllı içe aktarma CSV satırını okuyamadı.")
        report["smart_import"] = True
        report["smart_import_rows"] = len(parsed["rows"])

    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-ocr", action="store_true", help="Tesseract eksikse testi başarısız say")
    args = parser.parse_args()
    try:
        result = verify(require_ocr=args.require_ocr)
    except Exception as error:
        print(f"AYEC çalışma zamanı doğrulanamadı: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("AYEC PDF ve akıllı içe aktarma çalışma zamanı doğrulandı.")
    if not result.get("tesseract"):
        print("UYARI: Görsel OCR için Tesseract ve Türkçe dil paketi ayrıca kurulmalıdır.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
