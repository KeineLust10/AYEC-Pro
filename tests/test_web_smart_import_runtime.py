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
    assert str(Path(status["packaged_source_root"]) / "ecosystem" / "src") in sys.path


def test_web_source_resolves_shared_parser_without_installed_core_package(tmp_path):
    script = (
        "from pathlib import Path; from Web_Arayuzu import Main; "
        "Main.ensure_packaged_source(); import ayec_core; "
        "assert Path(ayec_core.__file__).resolve().is_relative_to("
        "Path('ecosystem/src').resolve())"
    )
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    subprocess.run([sys.executable, "-c", script], cwd=Path.cwd(), env=env,
                   capture_output=True, text=True, check=True, timeout=45)


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


def test_web_smart_import_reads_pdf_text_and_dispatches_image_ocr(monkeypatch):
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from PIL import Image
    from src.utils.stock_import_parser import StockImportParser

    pdf_data = BytesIO()
    document = canvas.Canvas(pdf_data)
    document.drawString(40, 760, "CAM-42 Wireless Camera")
    document.save()
    pdf_result = web_main.smart_import("inventory.pdf", pdf_data.getvalue())
    assert any("CAM-42 Wireless Camera" in row.get("name", "") for row in pdf_result["rows"])

    monkeypatch.setattr(StockImportParser, "_ocr_image_to_text", staticmethod(lambda _image: "CAM-43;Outdoor Camera;1;20;35"))
    monkeypatch.setattr(
        StockImportParser,
        "parse_file",
        classmethod(lambda _cls, _path: {"rows": [], "metadata": {}, "warnings": []}),
    )
    image_data = BytesIO()
    Image.new("RGB", (32, 32), "white").save(image_data, format="PNG")
    image_result = web_main.smart_import("inventory.png", image_data.getvalue())
    assert image_result["text"] == "CAM-43;Outdoor Camera;1;20;35"


def test_web_venv_easyocr_recognizes_a_sample_image():
    root = Path.cwd()
    venv_python = root / "Web_Arayuzu" / ".venv" / "Scripts" / "python.exe"
    model_dir = Path.home() / ".EasyOCR" / "model"
    if not venv_python.is_file() or not (model_dir / "craft_mlt_25k.pth").is_file():
        import pytest
        pytest.skip("Web virtual environment or cached EasyOCR models are unavailable")

    script = (
        "import os, sys; from PIL import Image, ImageDraw, ImageFont; "
        f"os.environ['EASYOCR_MODULE_PATH'] = {str(model_dir.parent)!r}; "
        f"sys.path.insert(0, {str(root / 'ecosystem' / 'src')!r}); "
        "from ayec_core.smart_import import StockImportParser; "
        "image = Image.new('RGB', (1000, 180), 'white'); "
        "draw = ImageDraw.Draw(image); "
        "draw.text((24, 42), 'CAM-42 Wireless Camera 123', fill='black', "
        "font=ImageFont.truetype('arial.ttf', 62)); "
        "text = StockImportParser._ocr_image_to_text(image); "
        "assert 'CAM-42' in text.upper() or 'CAM42' in text.upper(), repr(text)"
    )
    subprocess.run([str(venv_python), "-c", script], cwd=root, check=True,
                   capture_output=True, text=True, timeout=180)


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
