from base64 import b64encode
from http.server import ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
import os
import subprocess
import sys
import threading

import requests

from Web_Arayuzu import Main as web_main
from tools.setup.package_web_mobile import copy_web_runtime
from tests.test_vendor_management_center import _setup_tenant


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
    document.showPage()
    document.drawString(40, 760, "CAM-42 Page Two")
    document.save()
    pdf_result = web_main.smart_import("inventory.pdf", pdf_data.getvalue())
    assert any("CAM-42 Wireless Camera" in row.get("name", "") for row in pdf_result["rows"])
    preview = Image.open(BytesIO(__import__("base64").b64decode(pdf_result["preview_image"])))
    assert preview.format == "PNG"
    assert max(preview.size) <= 1800
    assert pdf_result["preview_page"] == 0
    assert pdf_result["preview_page_count"] == 2
    second_image, second_page, page_count = web_main._render_pdf_preview(pdf_data.getvalue(), 1)
    assert (second_page, page_count) == (1, 2)
    second_preview = Image.open(BytesIO(__import__("base64").b64decode(second_image)))
    assert second_preview.format == "PNG"

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



def test_web_smart_import_selected_area_uses_native_expansion_when_rows_improve(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from src.utils.stock_import_parser import StockImportParser

    calls = []

    def parse_selected_area(_cls, path):
        width = Image.open(path).width
        calls.append(width)
        rows = ([{"name": "One Row"}] if width == 72 else [
            {"name": "Camera A", "stock": 3, "purchase_price": 20, "currency": "TRY"},
            {"name": "Camera B", "stock": 4, "purchase_price": 30, "currency": "USD"},
        ])
        return {"rows": rows, "metadata": {}, "warnings": []}

    monkeypatch.setattr(StockImportParser, "parse_selected_area", classmethod(parse_selected_area))
    selected = BytesIO()
    Image.new("RGB", (72, 72), "white").save(selected, format="PNG")
    expanded = BytesIO()
    Image.new("RGB", (120, 120), "white").save(expanded, format="PNG")

    result = web_main.smart_import(
        "selection.png",
        selected.getvalue(),
        selected_area=True,
        expanded_payload=expanded.getvalue(),
    )

    assert calls == [72, 120]
    assert result["area_expansion_used"] is True
    assert [row["name"] for row in result["rows"]] == ["Camera A", "Camera B"]


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


def test_offscreen_route_audit_covers_smart_stock_import_and_merge():
    route_smoke = (Path(__file__).parents[1] / "tools/quality/web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.stockImportWorkflow" in route_smoke
    assert "function looksLikeCustomerStockExport" in (Path(__file__).parents[1] / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    assert "!workflow.customerExportRejected" in route_smoke
    assert "Number(workflow.existingStock) !== 5" in route_smoke
    assert 'workflow.newCurrency !== "USD"' in route_smoke
    assert "workflow.rowsAfterSuccessfulCommit !== 0" in route_smoke
    assert "workflow.partialRemainingCode !== \"QA-FAIL\"" in route_smoke
    assert "workflow.partialSuccessSaved !== 1" in route_smoke


def test_web_smart_import_http_upload_uses_authenticated_pdf_and_image_parsers(monkeypatch, tmp_path):
    from PIL import Image
    from reportlab.pdfgen import canvas
    from src.utils.stock_import_parser import StockImportParser

    _actor, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.post(
            f"{base_url}/api/desktop/smart-import",
            json={"name": "inventory.pdf", "data": "cGRm"},
        )
        assert anonymous.status_code == 401
        anonymous_preview = requests.post(
            f"{base_url}/api/desktop/smart-import/pdf-preview",
            json={"data": "cGRm", "page": 0},
        )
        assert anonymous_preview.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200, login.text

        empty_response = session.post(
            f"{base_url}/api/desktop/smart-import",
            json={"name": "empty.pdf", "data": ""},
        )
        assert empty_response.status_code == 400
        invalid_response = session.post(
            f"{base_url}/api/desktop/smart-import",
            json={"name": "invalid.pdf", "data": "not base64!"},
        )
        assert invalid_response.status_code == 400
        oversized_data = b64encode(b"x" * (25 * 1024 * 1024 + 1)).decode("ascii")
        oversized_response = session.post(
            f"{base_url}/api/desktop/smart-import",
            json={"name": "oversized.pdf", "data": oversized_data},
        )
        assert oversized_response.status_code == 413

        pdf_data = BytesIO()
        document = canvas.Canvas(pdf_data)
        document.drawString(40, 760, "CAM-82 Wireless Camera")
        document.showPage()
        document.drawString(40, 760, "CAM-82 Page Two")
        document.save()
        response = session.post(
            f"{base_url}/api/desktop/smart-import",
            json={
                "name": "inventory.pdf",
                "data": b64encode(pdf_data.getvalue()).decode("ascii"),
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["original_name"] == "inventory.pdf"
        assert result["rows"]
        assert any("CAM-82 Wireless Camera" in row.get("name", "") for row in result["rows"])
        assert result["preview_page_count"] == 2
        page_two = session.post(
            f"{base_url}/api/desktop/smart-import/pdf-preview",
            json={"data": b64encode(pdf_data.getvalue()).decode("ascii"), "page": 1},
        )
        assert page_two.status_code == 200, page_two.text
        assert page_two.json()["page"] == 1
        assert page_two.json()["page_count"] == 2
        assert page_two.json()["preview_image"]

        monkeypatch.setattr(
            StockImportParser,
            "parse_file",
            classmethod(lambda _cls, _path: {"rows": [], "metadata": {}, "warnings": []}),
        )
        monkeypatch.setattr(
            StockImportParser,
            "_ocr_image_to_text",
            staticmethod(lambda _image: "CAM-83;Outdoor Camera;1;20;35"),
        )
        image_data = BytesIO()
        Image.new("RGB", (32, 32), "white").save(image_data, format="PNG")
        image_response = session.post(
            f"{base_url}/api/desktop/smart-import",
            json={
                "name": "inventory.png",
                "data": b64encode(image_data.getvalue()).decode("ascii"),
            },
        )
        assert image_response.status_code == 200, image_response.text
        image_result = image_response.json()
        assert image_result["original_name"] == "inventory.png"
        assert image_result["text"] == "CAM-83;Outdoor Camera;1;20;35"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
