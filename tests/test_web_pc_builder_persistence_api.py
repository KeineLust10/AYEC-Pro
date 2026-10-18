import json
import io
import os
import base64
import subprocess
import sqlite3
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from pypdf import PdfReader
from reportlab.pdfgen import canvas as pdf_canvas

import Web_Arayuzu.Main as web
import src.utils.pdf_manager as pdf_manager
from PIL import Image


def test_customer_note_fields_migrate_without_losing_legacy_data(tmp_path):
    db_path = tmp_path / "legacy_customer_notes.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE customer_notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, type TEXT, "
        "content TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO customer_notes(customer_id, type, content, created_at) "
        "VALUES(?, ?, ?, ?)",
        (7, "Call", "Existing note", "2026-10-14T10:00:00"),
    )
    web._ensure_path_schema(conn, db_path)

    columns = {row[1] for row in conn.execute('PRAGMA table_info("customer_notes")')}
    assert {"note_type", "title"}.issubset(columns)
    assert conn.execute(
        "SELECT customer_id, type, content, created_at FROM customer_notes"
    ).fetchone() == (7, "Call", "Existing note", "2026-10-14T10:00:00")
    conn.close()


def test_pc_builder_quote_note_and_finance_persist_in_authenticated_tenant(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    monkeypatch.setattr(web, "ensure_control_owner", lambda: None)
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("PC Builder Persistence Test", email="qa@example.invalid")
    tenant_db = web._tenant_path(tenant)

    with sqlite3.connect(tenant_db) as conn:
        conn.execute(
            "INSERT INTO users(username, password, email, role, active, full_name) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (
                "qa",
                web.password_hash("test-password"),
                "qa@example.invalid",
                "Admin",
                "QA User",
            ),
        )
        customer_id = conn.execute(
            "INSERT INTO customers(name, email, type) VALUES (?, ?, ?)",
            ("QA Customer", "customer@example.invalid", "Bireysel"),
        ).lastrowid
        conn.execute(
            "INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,source,created_at) "
            "VALUES('USD',40,40,'2026-10-17','TEST','2026-10-17 12:00:00')"
        )

    token, _ = web.create_session(
        1, False, "PC Builder Persistence Test", "127.0.0.1", tenant["id"]
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    headers = {
        "Cookie": f"{web.SESSION_COOKIE}={token}",
        "Content-Type": "application/json",
    }
    generated_pdf = {}
    original_pdf_manager = pdf_manager.PDFManagerQt

    class RecordingPDFManager:
        def __init__(self, settings):
            self.settings = settings

        def create_proforma(self, **kwargs):
            generated_pdf.update(kwargs)
            Path(kwargs["save_path"]).write_bytes(b"%PDF-1.4 pc-builder-test")
            return True, kwargs["save_path"]

    monkeypatch.setattr(pdf_manager, "PDFManagerQt", RecordingPDFManager)

    def request(path, payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            base_url + path,
            data=body,
            headers=headers,
            method="POST" if payload is not None else "GET",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())

    try:
        status, saved_note = request(
            "/api/desktop/table/customer_notes",
            {
                "customer_id": customer_id,
                "note_type": "PC Teklif",
                "type": "PC Teklif",
                "title": "PC Teklif #PC-QA-1",
                "content": "Build quote detail",
                "created_at": "2026-10-14T10:00:00",
            },
        )
        assert status == 200
        assert saved_note["action"] == "insert"
        _, notes = request("/api/desktop/table/customer_notes?limit=100")
        note = next(row for row in notes["rows"] if row["id"] == saved_note["id"])
        assert note["customer_id"] == customer_id
        assert note["note_type"] == "PC Teklif"
        assert note["type"] == "PC Teklif"
        assert note["title"] == "PC Teklif #PC-QA-1"
        assert note["content"] == "Build quote detail"

        status, saved_finance = request(
            "/api/desktop/table/accounting",
            {
                "type": "Gelir",
                "category": "Sat\u0131\u015f",
                "amount": 1200,
                "description": "Bilgisayar Topla / Teklif #PC-QA-1",
                "customer_name": "QA Customer",
                "customer_id": customer_id,
                "payment_method": "Nakit",
                "currency": "TRY",
                "date": "2026-10-14T10:00:00",
            },
        )
        assert status == 200
        assert saved_finance["action"] == "insert"
        _, finance_rows = request("/api/desktop/table/accounting?limit=100")
        finance = next(
            row for row in finance_rows["rows"] if row["id"] == saved_finance["id"]
        )
        assert finance["type"] == "Gelir"
        assert finance["category"] == "Sat\u0131\u015f"
        assert finance["amount"] == 1200
        assert finance["customer_id"] == customer_id
        assert finance["description"] == "Bilgisayar Topla / Teklif #PC-QA-1"

        status, saved_audit = request(
            "/api/desktop/table/audit_logs",
            {
                "user_id": "sistem",
                "table_name": "pc_offers",
                "action": "INSERT",
                "details": "PC offer without a customer",
            },
        )
        assert status == 200
        assert saved_audit["action"] == "insert"
        with sqlite3.connect(tenant_db) as conn:
            audit = conn.execute(
                "SELECT user_id, table_name, action, details FROM audit_logs WHERE id=?",
                (saved_audit["id"],),
            ).fetchone()
        assert audit == (
            "sistem",
            "pc_offers",
            "INSERT",
            "PC offer without a customer",
        )

        proforma_data = {
            "company_name": "AYEC QA Company",
            "customer_name": "QA Customer",
            "project_name": "PC Builder QA",
            "reference_no": "PC-QA-1",
            "currency": "USD",
            "template": "corporate",
            "margin_percent": 20,
            "vat_percent": 20,
            "items": [
                {
                    "component": "Anakart",
                    "category": "Anakart",
                    "brand": "Audit",
                    "product": "Audit B550 Board",
                    "qty": 2,
                    "price": 50,
                }
            ],
        }
        proforma_request = urllib.request.Request(
            base_url + "/api/desktop/pc-builder/proforma.pdf",
            data=json.dumps(proforma_data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(proforma_request, timeout=10) as response:
            pdf_payload = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/pdf"
            assert "inline" in response.headers.get("Content-Disposition", "")
        assert pdf_payload.startswith(b"%PDF-1.4")
        assert generated_pdf["template_type"] == "corporate"
        assert generated_pdf["company_name"] == "AYEC QA Company"
        assert generated_pdf["customer_name"] == "QA Customer"
        assert generated_pdf["project_name"] == "PC Builder QA"
        assert generated_pdf["currency_code"] == "USD"
        assert generated_pdf["exchange_rate"] == 40
        assert generated_pdf["cart_items"][0]["name"] == "Anakart - Audit B550 Board"
        assert generated_pdf["cart_items"][0]["price"] == 1.25
        assert generated_pdf["totals"] == (2.5, 0.0, 0.2, 0.6, 3.6)

        monkeypatch.setattr(pdf_manager, "PDFManagerQt", original_pdf_manager)
        actual_proforma_request = urllib.request.Request(
            base_url + "/api/desktop/pc-builder/proforma.pdf",
            data=json.dumps(proforma_data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(actual_proforma_request, timeout=30) as response:
            actual_pdf = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/pdf"
        assert actual_pdf.startswith(b"%PDF-")

        image_buffer = io.BytesIO()
        Image.new("RGB", (2, 2), (12, 34, 56)).save(image_buffer, format="PNG")
        embedded_image = base64.b64encode(image_buffer.getvalue()).decode("ascii")
        editor_html = (
            "<p>Editor Template QA</p>"
            f'<img src="data:image/png;base64,{embedded_image}" />'
            '<img src="file:///private/secret.png" />'
            "<p>{{firma_adi}}</p>"
            "<p>{{musteri_adi}}</p><p>{{proje}}</p><p>{{teklif_no}}</p>"
            "{{urun_tablosu}}{{toplamlar}}"
        )
        with sqlite3.connect(tenant_db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)",
                ("proforma_editor_html", editor_html),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES (?,?)",
                ("proforma_use_custom_editor", "0"),
            )
        editor_data = {**proforma_data, "template": "editor_template"}
        editor_request = urllib.request.Request(
            base_url + "/api/desktop/pc-builder/proforma.pdf",
            data=json.dumps(editor_data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(editor_request, timeout=30) as response:
            editor_pdf = response.read()
            assert response.status == 200
            assert response.headers.get_content_type() == "application/pdf"
        editor_text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(editor_pdf)).pages)
        assert "Editor Template QA" in editor_text
        assert "AYEC QA Company" in editor_text
        assert "QA Customer" in editor_text
        assert "PC Builder QA" in editor_text
        assert "PC-QA-1" in editor_text
        editor_xobjects = PdfReader(io.BytesIO(editor_pdf)).pages[0]["/Resources"].get("/XObject")
        assert editor_xobjects and len(editor_xobjects) == 1

        template_stream = io.BytesIO()
        template_doc = pdf_canvas.Canvas(template_stream, pagesize=(612, 792))
        template_doc.setFont("Helvetica-Bold", 18)
        template_doc.drawString(48, 744, "CUSTOM TEMPLATE BACKGROUND QA")
        template_doc.showPage()
        template_doc.save()
        template_bytes = template_stream.getvalue()
        proforma_env = os.environ.copy()
        proforma_env.update(
            {
                "AYEC_PROFORMA_BASE_URL": base_url,
                "AYEC_PROFORMA_SESSION_COOKIE": token,
                "AYEC_PROFORMA_TEMPLATE_BASE64": base64.b64encode(template_bytes).decode("ascii"),
                "AYEC_PROFORMA_CDP_PORT": str(19400 + (os.getpid() % 500)),
            }
        )
        proforma_browser = subprocess.run(
            ["node", "tools/quality/proforma_template_authenticated_roundtrip.cjs"],
            cwd=Path(__file__).resolve().parents[1],
            env=proforma_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=False,
        )
        assert proforma_browser.returncode == 0, proforma_browser.stderr or proforma_browser.stdout
        assert '"legacyRestoreRejected":true' in proforma_browser.stdout
        assert '"legacyRestorePreserved":true' in proforma_browser.stdout
        assert '"uploaded":"1"' in proforma_browser.stdout
        assert '"uploaded":"0"' in proforma_browser.stdout
        assert '"invalidPdfRejected":true' in proforma_browser.stdout
        assert '"oversizeRejected":true' in proforma_browser.stdout
        assert '"browserExceptions":0' in proforma_browser.stdout
        assert '"editorSaved":true' in proforma_browser.stdout
        assert '"editorPreviewStatus":200' in proforma_browser.stdout
        assert '"editorPreviewContentType":"application/pdf"' in proforma_browser.stdout
        assert '"legacyGuardVerified":true' in proforma_browser.stdout
        legacy_pdf_path = r"C:\Legacy\AYEC\proforma.pdf"
        with sqlite3.connect(tenant_db) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                ("proforma_template_path", legacy_pdf_path),
            )
        status, legacy_bootstrap = request("/api/desktop/bootstrap")
        assert status == 200
        assert legacy_bootstrap["settings"]["proforma_local_pdf_path_present"] == "1"
        assert legacy_bootstrap["settings"].get("proforma_template_path", "") == ""
        assert legacy_pdf_path not in json.dumps(legacy_bootstrap)
        status, upload_result = request(
            "/api/desktop/pc-builder/proforma-template",
            {
                "filename": "QA Custom Template.pdf",
                "data_base64": base64.b64encode(template_bytes).decode("ascii"),
            },
        )
        assert status == 200
        assert upload_result == {
            "ok": True,
            "uploaded": True,
            "filename": "QA Custom Template.pdf",
            "page_count": 1,
            "size_bytes": len(template_bytes),
        }
        status, bootstrap = request("/api/desktop/bootstrap")
        assert status == 200
        assert bootstrap["settings"]["proforma_template_uploaded"] == "1"
        assert bootstrap["settings"]["proforma_template_filename"] == "QA Custom Template.pdf"
        assert bootstrap["settings"]["proforma_local_pdf_path_present"] == "1"
        assert bootstrap["settings"]["proforma_template_pdf_base64"] == ""

        custom_data = {**proforma_data, "template": "custom_template"}
        custom_request = urllib.request.Request(
            base_url + "/api/desktop/pc-builder/proforma.pdf",
            data=json.dumps(custom_data).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(custom_request, timeout=30) as response:
                custom_pdf = response.read()
                assert response.status == 200
                assert response.headers.get_content_type() == "application/pdf"
        except urllib.error.HTTPError as error:
            raise AssertionError(error.read().decode("utf-8", errors="replace")) from error
        custom_pdf_text = "\n".join(
            page.extract_text() or "" for page in PdfReader(io.BytesIO(custom_pdf)).pages
        )
        assert "CUSTOM TEMPLATE BACKGROUND QA" in custom_pdf_text
        assert "Audit B550 Board" in custom_pdf_text
        assert web.role_is_admin(web.session_user(token).get("role"))

        try:
            status, removal_result = request(
                "/api/desktop/pc-builder/proforma-template", {"action": "delete"}
            )
        except urllib.error.HTTPError as error:
            raise AssertionError(error.read().decode("utf-8", errors="replace")) from error
        assert status == 200
        assert removal_result == {"ok": True, "uploaded": False, "filename": ""}
        status, bootstrap = request("/api/desktop/bootstrap")
        assert status == 200
        assert bootstrap["settings"]["proforma_template_uploaded"] == "0"
        assert bootstrap["settings"]["proforma_local_pdf_path_present"] == "1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)
