import io
from pathlib import Path

from pypdf import PdfReader

from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_invoice_reference_controls_and_mobile_line_cards_are_present():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")
    reference_styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert 'id="invoiceVkn"' in app
    assert 'id="invoiceScenario"' in app
    assert 'id="invoiceDeliveryRef"' in app
    assert 'id="invoiceLinesBody"' in app
    assert 'data-invoice-action="send"' in app
    assert 'data-invoice-action="integration"' in app
    assert '/api/desktop/einvoice/settings' in app
    assert '/api/desktop/einvoice/send' in app
    assert '/api/desktop/einvoice/proforma.pdf' in app
    assert 'data-invoice-action="proforma"' in app
    assert "const invoicePreviewText=()=>" in app
    assert 'class="einvoice-preview-text"' in app
    assert 'window.print()' not in app[app.index('[data-invoice-action="preview"]'):app.index('[data-invoice-action="send"]')]
    invoice_bind = app[app.index("function bindInvoiceComposer"):app.index("function renderFinance")]
    assert 'if(!confirm(' not in invoice_bind
    assert '<option>KAMU</option>' in app
    assert 'value="OZELMATRAH"' in app
    assert 'id="einvoiceTestButton"' in app
    assert 'class="einvoice-integration-info"' in app
    assert '#appDialog.einvoice-integration-dialog' in reference_styles
    assert '#appDialog.einvoice-preview-dialog' in reference_styles
    assert 'id="invoiceReferenceEntry"' in app
    assert 'formData.get("reference")' in app
    assert 'return true},"Uygula")' in app
    assert '@media(max-width:620px){.einvoice-ribbon' in styles
    assert '.einvoice-table tbody{display:grid;gap:10px' in styles


def test_invoice_persists_numeric_total_without_parsing_localized_currency_text():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'let savedId=null,currentTotal=0' in app
    assert 'currentTotal=total' in app
    assert 'amount:currentTotal,status,json_data:' in app
    assert 'invoiceGrandTotal").textContent.replace(/[^0-9.-]/g' not in app


def test_invoice_reference_typography_remains_readable_on_narrow_screens():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert ".einvoice-fields label,.einvoice-payment label,.einvoice-notes label{font-size:12px}" in styles
    assert ".einvoice-table td,.einvoice-table input,.einvoice-table select{font-size:12px}" in styles
    assert "@media(max-width:620px){.einvoice-ribbon p,.einvoice-summary p{font-size:12px}" in styles


def test_invoice_summary_rows_keep_semantic_colors_without_filled_blocks():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert ".einvoice-summary .invoice-total-row.danger" in styles
    assert ".einvoice-summary .invoice-total-row.success" in styles
    assert "background: transparent;" in styles


def test_invoice_desktop_uses_a_single_reference_header_and_full_width_columns():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="invoices"] .content > .page-head' in styles
    assert "grid-template-rows: 32px 52px;" in styles
    assert 'content: "GIB UBL 2.1 TR";' in styles
    assert "gap: 27px;" in styles


def test_einvoice_settings_store_api_key_encrypted_and_preserve_it_when_blank():
    from src.utils.secure_setting_store import SecureSettingStore

    class FakeDatabase:
        def __init__(self):
            self.values = {}

        def get_setting(self, key, default=""):
            return self.values.get(key, default)

        def set_setting(self, key, value):
            self.values[key] = value
            return True

    database = FakeDatabase()
    saved = web_main.save_einvoice_settings(database, {
        "provider": "logo",
        "environment": "sandbox",
        "api_url": "https://sandbox.example.test",
        "api_key": "secret-token",
    })
    assert saved["api_key_configured"] is True
    assert database.values["einvoice_api_key"].startswith(SecureSettingStore.PREFIX)
    assert "secret-token" not in database.values["einvoice_api_key"]

    web_main.save_einvoice_settings(database, {
        "provider": "logo",
        "environment": "sandbox",
        "api_url": "https://sandbox.example.test",
    })
    assert SecureSettingStore.get(database, "einvoice_api_key") == "secret-token"


def test_einvoice_settings_api_is_authenticated_and_does_not_return_secret(monkeypatch):
    class FakeDatabase:
        values = {"einvoice_provider": "logo", "einvoice_environment": "sandbox", "einvoice_api_url": ""}

        def __init__(self, *args, **kwargs):
            pass

        def get_setting(self, key, default=""):
            return self.values.get(key, default)

        def set_setting(self, key, value):
            self.values[key] = value
            return True

        def close(self):
            pass

    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: ROOT / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/einvoice/settings"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    assert replies == [({
        "provider": "logo",
        "environment": "sandbox",
        "api_url": "",
        "api_key_configured": False,
    }, 200)]
    assert "api_key" not in replies[0][0]

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {}
    unauthenticated.current_user = lambda: None
    denied = []
    unauthenticated.send_json = lambda payload, status=200: denied.append((payload, status))
    unauthenticated.do_GET()
    assert denied == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_einvoice_settings_api_saves_encrypted_value_and_tests_sandbox(monkeypatch):
    from src.utils.secure_setting_store import SecureSettingStore

    class FakeDatabase:
        values = {}

        def __init__(self, *args, **kwargs):
            pass

        def get_setting(self, key, default=""):
            return self.values.get(key, default)

        def set_setting(self, key, value):
            self.values[key] = value
            return True

        def close(self):
            pass

    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: ROOT / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/einvoice/settings"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {
        "action": "save",
        "provider": "uyumsoft",
        "environment": "sandbox",
        "api_url": "",
        "api_key": "encrypted-key",
    }
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_POST()

    assert replies[0][0]["ok"] is True
    assert FakeDatabase.values["einvoice_api_key"].startswith(SecureSettingStore.PREFIX)
    assert "encrypted-key" not in FakeDatabase.values["einvoice_api_key"]

    handler.read_json = lambda: {
        "action": "test",
        "provider": "uyumsoft",
        "environment": "sandbox",
        "api_url": "",
    }
    replies.clear()
    handler.do_POST()
    assert replies == [({"ok": True, "detail": "Sandbox testi yerelde calisir."}, 200)]


def test_einvoice_send_maps_desktop_payload_and_persists_provider_response(monkeypatch):
    calls = []

    class FakeCursor:
        lastrowid = 22

        def execute(self, query, values=()):
            calls.append((query, values))
            return self

        def fetchone(self):
            return None

    class FakeConnection:
        def commit(self):
            calls.append(("commit",))

    class FakeDatabase:
        cursor = FakeCursor()
        conn = FakeConnection()

        def get_setting(self, key, default=""):
            return {
                "einvoice_provider": "custom",
                "einvoice_environment": "sandbox",
                "einvoice_api_url": "",
            }.get(key, default)

    sent = {}

    class FakeClient:
        def __init__(self, **kwargs):
            sent["settings"] = kwargs

        def validate_configuration(self):
            return True, "ok"

        def send_invoice(self, invoice):
            sent["invoice"] = invoice
            return True, {"uuid": "ETTN-22", "status": "TEST_QUEUED", "message": "Sandbox"}

    monkeypatch.setattr("src.api.einvoice_client.EInvoiceClient", FakeClient)
    result = web_main.send_einvoice_invoice(FakeDatabase(), {
        "draft_id": 0,
        "receiver_name": "Ada Customer",
        "receiver_vkn": "1234567890",
        "invoice_type": "TEVKIFAT",
        "invoice": {
            "scenario": "KAMU",
            "date": "2026-10-15",
            "time": "10:30",
            "currency": "TRY",
            "exchange_rate": "1",
            "tax_office": "Ankara",
            "address": "Main St",
            "payment_account": "5",
            "payment_channel": "Bank",
            "due_date": "2026-11-01",
            "auto_reconcile": True,
            "lines": [{
                "invoice-line-description": "Repair",
                "invoice-line-code": "SVC-1",
                "invoice-line-qty": "2",
                "invoice-line-unit": "Hizmet",
                "invoice-line-price": "100",
                "invoice-line-discount": "10",
                "invoice-line-vat": "20",
            }],
        },
    })

    assert sent["invoice"]["fatura_bilgileri"]["senaryo"] == "KAMU"
    assert sent["invoice"]["fatura_bilgileri"]["tip"] == "TEVKIFAT"
    assert sent["invoice"]["fatura_bilgileri"]["tahsilat_hesabi_id"] == 5
    assert sent["invoice"]["kalemler"][0]["urun_adi"] == "Repair"
    assert sent["invoice"]["toplamlar"]["genel_toplam"] == 216
    assert result == {
        "ok": True,
        "id": 22,
        "uuid": "ETTN-22",
        "status": "TEST_QUEUED",
        "message": "Sandbox",
        "sandbox": True,
        "finance_error": "",
    }
    insert = next(call for call in calls if call[0].startswith("INSERT INTO e_invoices"))
    assert insert[1][0:5] == ("ETTN-22", "TEVKIFAT", "Ada Customer", "1234567890", 216)
    assert calls[-1] == ("commit",)


def test_einvoice_send_rejects_nonfinite_and_empty_invoice_lines():
    base = {
        "receiver_name": "Ada",
        "invoice_type": "SATIS",
        "invoice": {
            "currency": "TRY",
            "exchange_rate": "1",
            "lines": [{
                "invoice-line-description": "Repair",
                "invoice-line-qty": "1",
                "invoice-line-price": "NaN",
            }],
        },
    }
    try:
        web_main.send_einvoice_invoice(object(), base)
    except ValueError as error:
        assert str(error) == "Invoice line values must be finite numbers"
    else:
        raise AssertionError("Nonfinite invoice value was accepted")

    base["invoice"]["lines"] = []
    try:
        web_main.send_einvoice_invoice(object(), base)
    except ValueError as error:
        assert str(error) == "Add at least one invoice line"
    else:
        raise AssertionError("Empty invoice was accepted")


def test_einvoice_live_send_reconciles_the_try_total_only_after_success(monkeypatch):
    calls = []

    class FakeCursor:
        lastrowid = 12

        def execute(self, query, values=()):
            calls.append((query, values))
            return self

    class FakeConnection:
        def commit(self):
            calls.append(("commit",))

    class FakeDatabase:
        cursor = FakeCursor()
        conn = FakeConnection()

        def get_setting(self, key, default=""):
            return {
                "einvoice_provider": "custom",
                "einvoice_environment": "live",
                "einvoice_api_url": "https://provider.example.test",
                "einvoice_api_key": "",
            }.get(key, default)

        def set_setting(self, key, value):
            calls.append(("setting", key, value))

        def add_transaction_extended(self, **kwargs):
            calls.append(("finance", kwargs))

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def validate_configuration(self):
            return True, "ok"

        def send_invoice(self, invoice):
            return True, {"uuid": "ETTN-LIVE", "status": "SENT"}

    monkeypatch.setattr("src.api.einvoice_client.EInvoiceClient", FakeClient)
    result = web_main.send_einvoice_invoice(FakeDatabase(), {
        "receiver_name": "Ada",
        "invoice_type": "SATIS",
        "invoice": {
            "currency": "USD",
            "exchange_rate": "3",
            "auto_reconcile": True,
            "payment_account": "8",
            "lines": [{
                "invoice-line-description": "Service",
                "invoice-line-qty": "1",
                "invoice-line-price": "100",
                "invoice-line-discount": "0",
                "invoice-line-vat": "0",
            }],
        },
    })

    stored = next(call for call in calls if call[0].startswith("INSERT INTO e_invoices"))
    finance = next(call[1] for call in calls if call[0] == "finance")
    assert stored[1][4] == 100
    assert finance["amount"] == 300
    assert finance["bank_account_id"] == 8
    assert finance["category"] == "Resmi Fatura"
    assert result["sandbox"] is False
    assert result["finance_error"] == ""


def test_einvoice_send_route_uses_authenticated_active_database(monkeypatch, tmp_path):
    calls = []

    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("open", Path(path), init_mode))

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    monkeypatch.setattr(
        web_main,
        "send_einvoice_invoice",
        lambda database, payload: calls.append(("send", payload)) or {"ok": True, "uuid": "ETTN"},
    )
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/einvoice/send"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {"invoice": {"lines": []}}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_POST()

    assert calls == [
        ("open", tmp_path / "tenant.db", "connection_only"),
        ("send", {"invoice": {"lines": []}}),
        ("close",),
    ]
    assert replies == [({"ok": True, "uuid": "ETTN"}, 200)]


def test_einvoice_proforma_pdf_preserves_preview_fields_and_turkish_text():
    payload = web_main.einvoice_proforma_pdf({
        "receiver_name": "\u0130pek Ada",
        "receiver_vkn": "1234567890",
        "invoice_type": "SATIS",
        "invoice": {
            "scenario": "TICARIFATURA",
            "date": "2026-10-15",
            "time": "10:30",
            "currency": "TRY",
            "notes": "\u0130yi \u00e7al\u0131\u015fmalar",
            "lines": [{
                "invoice-line-description": "Servis i\u015flemi",
                "invoice-line-qty": "2",
                "invoice-line-unit": "Hizmet",
                "invoice-line-price": "100",
                "invoice-line-discount": "10",
                "invoice-line-vat": "20",
            }],
        },
    })
    reader = PdfReader(io.BytesIO(payload))
    text = reader.pages[0].extract_text()

    assert payload.startswith(b"%PDF-")
    assert "Proforma" in text
    assert "\u0130pek Ada" in text
    assert "Servis i\u015flemi" in text
    assert "\u0130yi \u00e7al\u0131\u015fmalar" in text
    assert "216.00" in text


def test_einvoice_proforma_route_returns_pdf_attachment(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/einvoice/proforma.pdf"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {"receiver_name": "Ada"}
    replies = []
    handler.send_bytes = lambda *args, **kwargs: replies.append((args, kwargs))
    monkeypatch.setattr(web_main, "einvoice_proforma_pdf", lambda payload: b"%PDF-proforma")

    handler.do_POST()

    assert replies[0][0] == (b"%PDF-proforma", "application/pdf")
    assert replies[0][1]["disposition"].startswith('attachment; filename="proforma_')
