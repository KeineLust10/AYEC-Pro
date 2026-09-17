"""Render a representative proforma for visual acceptance checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.utils.professional_proforma import build_professional_proforma
from src.utils._pdf_base_mixin import PDFBaseMixin


class _SettingsDb:
    def __init__(self, settings):
        self.settings = settings

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)


class _PdfManager(PDFBaseMixin):
    def __init__(self, settings, output_dir):
        self.db = _SettingsDb(settings)
        self.output_dir = Path(output_dir)

    def _get_save_path(self):
        return str(self.output_dir)

    @staticmethod
    def _safe_filename(value):
        return str(value or "offer").replace(" ", "_")

    @staticmethod
    def _open_file(_path):
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--logo", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    settings = {
        "logo_path": args.logo,
        "company_name": "AYEC PRO",
        "company_email": "ayecpro@gmail.com",
        "offer_contract": (
            "Fiyat : Amerikan Dolar\u0131 cinsinden verilmi\u015ftir.\n"
            "\u00d6deme : Sipari\u015fte toplam tutar\u0131n %50'si, kalan bakiye i\u015f tesliminde \u00f6denir.\n"
            "Teslimat : Sipari\u015f ve \u00f6n \u00f6demeyi takiben stok durumuna g\u00f6re 6 haftad\u0131r.\n"
            "Garanti : \u00dcretim hatalar\u0131na kar\u015f\u0131 2 y\u0131ld\u0131r.\n"
            "Opsiyon : Teklif 15 g\u00fcn ge\u00e7erlidir."
        ),
    }
    manager = _PdfManager(settings, output.parent)
    ok, result = build_professional_proforma(
        manager,
        template_type="modern",
        cart_items=[
            {
                "name": "1230S 2MP BULLET KAMERA",
                "description": "Stok \u00fcr\u00fcn: 1230S 2MP BULLET KAMERA",
                "qty": 1,
                "price": 36.50,
            },
            {
                "name": "2MP Dome Kamera",
                "description": "Stok \u00fcr\u00fcn: 2MP Dome Kamera",
                "qty": 1,
                "price": 30.41,
            },
        ],
        totals=(66.91, 0.0, 0.20, 13.38, 80.29),
        company_name="AYEC PRO",
        customer_name="MURAT MADEN",
        customer_company="MURAT MADEN",
        save_path=str(output),
        currency="\u20ac",
        currency_code="EUR",
        project_name="A",
        reference_no="REF1",
        offer_date="2026-08-01",
        validity_days=15,
    )
    if not ok:
        raise SystemExit(result)
    print(result)


if __name__ == "__main__":
    main()
