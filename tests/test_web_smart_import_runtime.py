from pathlib import Path
import os
import subprocess
import sys

from Web_Arayuzu import Main as web_main
from tools.setup.package_web_mobile import copy_web_runtime


def test_web_smart_import_runtime_resolves_shared_parser():
    status = web_main.runtime_status()

    assert status["smart_import"] is True
    assert status["packaged_source"] is True
    assert Path(status["packaged_source_root"]).is_dir()


def test_web_smart_import_parses_csv_rows():
    payload = (
        "kod;urun;kategori;adet;minimum;alis;satis;para birimi;barkod\n"
        "CAM-01;IP Kamera;Guvenlik;3;1;20;35;USD;869000000001\n"
    ).encode("utf-8")

    result = web_main.smart_import("stok.csv", payload)

    assert result["rows"]
    first = result["rows"][0]
    assert first["brand"] == "IP"
    assert first["name"] == "Kamera"


def test_web_release_contains_smart_import_engine(tmp_path):
    copy_web_runtime(tmp_path)
    assert (tmp_path / "ecosystem" / "products.json").read_bytes() == Path("ecosystem/products.json").read_bytes()

    utils = tmp_path / "src" / "utils"
    assert (utils / "stock_import_parser.py").is_file()
    shared = tmp_path / "ayec_core" / "smart_import"
    assert (shared / "stock_import_parser.py").is_file()
    assert (shared / "_ocr_subprocess_helper.py").is_file()
    assert (utils / "_sip_file.py").is_file()
    assert (utils / "_sip_ocr.py").is_file()
    assert (utils / "pdf_manager.py").is_file()
    assert (utils / "service_work_details.py").is_file()
    csv = tmp_path / "stock.csv"
    csv.write_text("barkod;urun;adet;alis;satis\n0012345678905;Kalem;8;5;10\n", encoding="utf-8")
    script = (
        "from pathlib import Path; import ayec_core; "
        "assert Path(ayec_core.__file__).resolve().is_relative_to(Path.cwd()); "
        "from src.utils.stock_import_parser import StockImportParser; "
        "row = StockImportParser.parse_file('stock.csv')['rows'][0]; "
        "assert row['code'] == '0012345678905' and row['stock'] == 8"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    subprocess.run([sys.executable, "-c", script], cwd=tmp_path, env=env,
                   capture_output=True, text=True, check=True, timeout=45)


def test_web_offer_editor_uses_atomic_sales_endpoint():
    source = Path("Web_Arayuzu/web/app.js").read_text(encoding="utf-8")

    assert "function beginOfferEdit(offer)" in source
    assert 'offer_id:mode==="proforma"&&editingOfferId' in source
    assert 'class="mini quote-edit"' in source
