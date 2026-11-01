import io
import sqlite3
from pathlib import Path

import openpyxl
from pypdf import PdfReader

from Web_Arayuzu import Main as web_main
import src.database as database_module


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_context_menu_matches_desktop_actions_and_routes():
    source = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    for action in (
        "notes", "360", "edit", "service", "invoice", "payment", "whatsapp",
        "debt-reminder", "excel", "pdf", "print", "selected-excel", "delete",
    ):
        assert f'"{action}"' in source
    assert 'customer/open-debts?customer_id=${id}&currency=TRY' in source
    assert 'customers/export/xlsx' in source
    assert 'customers/export/pdf' in source
    assert 'if (action === "pdf") return exportCustomerPdf()' in source
    assert 'if (action === "print") return printCustomerList()' in source
    assert 'customer/delete' in source
    assert 'navigate("invoices")' in source


def test_customer_delete_cancel_and_confirm_have_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerDeleteWorkflow = await evaluate(" in runner
    assert "customerDeleteWorkflow.cancelNoWrite" in runner
    assert "customerDeleteWorkflow.retainedAfterFailure" in runner
    assert 'customerDeleteWorkflow.request?.url !== "/api/desktop/customer/delete"' in runner
    assert "customerDeleteWorkflow.serviceFixturePreserved" in runner


def test_selected_customer_excel_export_has_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerSelectedExcelWorkflow = await evaluate(" in runner
    assert "!customerSelectedExcelWorkflow.emptyNoWrite" in runner
    assert "!customerSelectedExcelWorkflow.exportAllActionFound" in runner
    assert "!customerSelectedExcelWorkflow.pdfActionFound" in runner
    assert 'customerSelectedExcelWorkflow.calls[2]?.url !== "/api/desktop/customers/export/pdf"' in runner
    assert 'customerSelectedExcelWorkflow.calls[0]?.url !== "/api/desktop/customers/export/xlsx"' in runner
    assert 'customerSelectedExcelWorkflow.downloads?.[0] !== "musteriler-secili.xlsx"' in runner
    assert "selectedCustomerPayload.rows[0]?.[0] !== 96111" in runner


def test_customer_debt_reminder_has_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerDebtReminderWorkflow = await evaluate(" in runner
    assert "customerDebtReminderWorkflow.noDebtNoOpen" in runner
    assert "!customerDebtReminderWorkflow.failureNoOpen" in runner
    assert 'customerDebtReminderWorkflow.openedUrl.startsWith("https://wa.me/905551000001?text=")' in runner


def test_customer_payment_context_cancel_has_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerPaymentContextWorkflow = await evaluate(" in runner
    assert "customerPaymentContextWorkflow.writeCount!==0" in runner
    assert "customerPaymentContextWorkflow.customerBalance!==250" in runner


def test_customer_payment_context_save_updates_balance_and_finance():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerPaymentSaveContextWorkflow = await evaluate(" in runner
    assert 'item.url==="/api/desktop/customer/payment"' in runner
    assert "paymentWrite.payload.amount!==100" in runner
    assert "paymentWrite.payload.customer_id!==96289" in runner
    assert "customerPaymentSaveContextWorkflow.balance!==-150" in runner
    assert 'customerPaymentSaveContextWorkflow.receiptHtml.includes("KDV (%20)")' in runner
    assert 'customerPaymentSaveContextWorkflow.receiptHtml.includes("TOPLAM:")' in runner


def test_customer_payment_context_blocks_amount_above_outstanding_debt():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerPaymentLimitContextWorkflow = await evaluate(" in runner
    assert "customerPaymentLimitContextWorkflow.writeCount!==0" in runner
    assert "customerPaymentLimitContextWorkflow.rangeOverflow" in runner
    assert "customerPaymentLimitContextWorkflow.max!==250" in runner


def test_customer_edit_context_cancel_has_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerEditContextWorkflow = await evaluate(" in runner
    assert "customerEditContextWorkflow.formLoaded" in runner
    assert "customerEditContextWorkflow.writeCount!==0" in runner
    assert 'customerEditContextWorkflow.customerName!=="QA Edit Customer"' in runner


def test_customer_edit_context_save_has_offscreen_runtime_coverage():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerEditSaveContextWorkflow = await evaluate(" in runner
    assert 'customerEditSaveContextWorkflow.write?.url!=="/api/desktop/table/customers"' in runner
    assert "customerEditSaveContextWorkflow.write?.payload?._action!==\"update\"" in runner


def test_customer_360_pdf_requires_an_offer_selection_and_uses_the_offer_document():
    source = (WEB / "app.js").read_text(encoding="utf-8")
    start = source.index("function customer360(c)")
    end = source.index("function openCustomerNotes(c)", start)
    customer_360 = source[start:end]
    assert 'data-c360-offer-row="${index}"' in customer_360
    assert 'activeTab!=="offers"' in customer_360
    assert 'selectedRow=dialog.querySelector("[data-c360-offer-row].is-selected")' in customer_360
    assert 'selectedIndex<0||!offers[selectedIndex]' in customer_360
    assert 'openProformaDocument(offers[selectedIndex],c)' in customer_360
    assert 'onclick=()=>printCustomer(c)' not in customer_360


def test_customer_360_context_action_loads_selected_customer_without_writing():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customer360ContextWorkflow = await evaluate(" in runner
    assert "customer360ContextWorkflow.customerVisible" in runner
    assert "customer360ContextWorkflow.serviceVisible" in runner
    assert 'customer360ContextWorkflow.tabs.includes("service")' in runner
    assert "customer360ContextWorkflow.writeCount!==0" in runner


def test_customer_list_print_button_uses_the_isolated_filtered_report():
    source = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "event.stopImmediatePropagation();\n    printCustomerList();" in source
    assert "const customerListPrintWorkflow = await evaluate(" in runner
    assert "customerListPrintWorkflow.reportVisible" in runner
    assert "customerListPrintWorkflow.actionsExcluded" in runner
    assert "customerListPrintWorkflow.cleaned" in runner


def test_customer_360_finance_tab_shows_selected_customer_activity():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customer360TabWorkflow = await evaluate(" in runner
    assert 'customer360TabWorkflow.activeTab!=="cari"' in runner
    assert "customer360TabWorkflow.panelActive" in runner
    assert "customer360TabWorkflow.saleVisible" in runner


def test_customer_context_notes_save_to_selected_customer():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerNotesContextWorkflow = await evaluate(" in runner
    assert 'customerNotesContextWorkflow.write.url!=="/api/desktop/table/customer_notes"' in runner
    assert "customerNotesContextWorkflow.write.payload.customer_id!==96271" in runner
    assert 'customerNotesContextWorkflow.customerNotes!=="Saved through customer context"' in runner


def test_customer_context_notes_update_existing_record():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerNotesUpdateWorkflow = await evaluate(" in runner
    assert 'customerNotesUpdateWorkflow.write.payload._action!=="update"' in runner
    assert "customerNotesUpdateWorkflow.write.payload.id!==96274" in runner
    assert 'customerNotesUpdateWorkflow.customerNotes!=="Updated customer detail"' in runner


def test_customer_context_notes_delete_requires_confirmation_and_removes_record():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerNotesDeleteWorkflow = await evaluate(" in runner
    assert 'customerNotesDeleteWorkflow.confirmTitle!=="M\\u00fc\\u015fteri Notunu Sil"' in runner
    assert "customerNotesDeleteWorkflow.write.payload.id!==96277" in runner
    assert "customerNotesDeleteWorkflow.noteHistory.length!==0" in runner


def test_customer_context_service_creates_device_for_selected_customer():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerServiceContextWorkflow = await evaluate(" in runner
    assert 'customerServiceContextWorkflow.prefilledCustomer!=="QA Service Customer"' in runner
    assert "customerServiceContextWorkflow.write.payload.customer_id!==96282" in runner
    assert 'customerServiceContextWorkflow.write.payload.device_type!=="Laptop / Notebook"' in runner
    assert 'customerServiceContextWorkflow.write.payload.fault_description!=="QA context service request"' in runner


def test_customer_context_invoice_draft_uses_selected_customer_and_line_item():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerInvoiceDraftContextWorkflow = await evaluate(" in runner
    assert "customerInvoiceDraftContextWorkflow.write?.payload?.receiver_name!==\"QA Invoice Draft Customer\"" in runner
    assert "customerInvoiceDraftContextWorkflow.write?.payload?.status!==\"DRAFT\"" in runner
    assert 'invoiceDraftSerialized.includes("QA Service Fee")' in runner


def test_customer_context_whatsapp_normalizes_phone_and_handles_missing_phone():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "const customerWhatsAppContextWorkflow = await evaluate(" in runner
    assert "customerWhatsAppContextWorkflow.openedCount!==1" in runner
    assert 'customerWhatsAppContextWorkflow.opened[0]?.url!=="https://wa.me/905554000008"' in runner
    assert 'customerWhatsAppContextWorkflow.messages.at(-1)?.type!=="warning"' in runner


def test_customer_list_workbook_matches_desktop_export_and_escapes_formulas():
    payload = web_main.customer_list_workbook([
        [7, "=1+1", "Company", "555", "a@example.test", "Business", "@home"],
    ])
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    sheet = workbook.active

    assert sheet.title == "Sheet1"
    assert [cell.value for cell in sheet[1]] == [
        "M\u00fc\u015fteri No", "Ad Soyad", "Firma", "Telefon", "E-posta", "T\u00fcr", "Adres",
    ]
    assert [cell.value for cell in sheet[2]] == [
        7, "'=1+1", "Company", "555", "a@example.test", "Business", "'@home",
    ]


def test_customer_list_pdf_is_downloadable_and_keeps_turkish_text():
    payload = web_main.customer_list_pdf([
        [7, "\u0130pek Ada", "AYEC Servis", "555 0100", "a@example.test", "Kurumsal", "\u0130stanbul"],
    ])
    reader = PdfReader(io.BytesIO(payload))

    assert payload.startswith(b"%PDF-")
    assert "\u0130pek Ada" in reader.pages[0].extract_text()
    assert "\u0130stanbul" in reader.pages[0].extract_text()


def test_customer_list_pdf_route_requires_authentication_and_returns_pdf(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customers/export/pdf"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {"rows": [[7, "Ada", "", "555", "a@example.test", "Person", ""]]}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "customer_list_pdf", lambda rows: b"%PDF-test")

    handler.do_POST()

    assert sent[0][0][0] == b"%PDF-test"
    assert sent[0][0][1] == "application/pdf"

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {"Content-Length": "2"}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_POST()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_customer_list_export_route_requires_authentication_and_returns_xlsx(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customers/export/xlsx"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {"rows": [[7, "Ada", "", "555", "a@example.test", "Person", ""]]}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "customer_list_workbook", lambda rows: b"xlsx")

    handler.do_POST()

    assert sent[0][0][0] == b"xlsx"
    assert sent[0][0][1] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {"Content-Length": "2"}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_POST()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_customer_delete_route_uses_the_active_tenant_database(monkeypatch, tmp_path):
    calls = []

    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("open", Path(path), init_mode))

        def delete_customer(self, customer_id):
            calls.append(("delete", customer_id))
            return True

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customer/delete"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {"id": 17}
    responses = []
    handler.send_json = lambda payload, status=200: responses.append((payload, status))

    handler.do_POST()

    assert calls == [
        ("open", tmp_path / "tenant.db", "connection_only"),
        ("delete", 17),
        ("close",),
    ]
    assert responses == [({"ok": True, "id": 17, "action": "delete"}, 200)]


def test_customer_delete_route_soft_deletes_without_removing_service_history(monkeypatch, tmp_path):
    from tests.test_vendor_management_center import _setup_tenant

    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    conn = sqlite3.connect(tenant_path)
    conn.execute(
        "INSERT INTO customers(name,phone) VALUES(?,?)",
        ("QA Delete History Customer", "5550100123"),
    )
    customer_id = conn.execute(
        "SELECT id FROM customers WHERE name=?", ("QA Delete History Customer",)
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO devices(tracking_no,customer_name,status) VALUES(?,?,?)",
        ("QA-HISTORY-1", "QA Delete History Customer", "Done"),
    )
    conn.commit()
    conn.close()

    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customer/delete"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: actor
    handler.read_json = lambda: {"id": customer_id}
    responses = []
    handler.send_json = lambda payload, status=200: responses.append((payload, status))

    handler.do_POST()

    assert responses == [({"ok": True, "id": customer_id, "action": "delete"}, 200)]
    conn = sqlite3.connect(tenant_path)
    conn.row_factory = sqlite3.Row
    customer = conn.execute(
        "SELECT is_deleted,deleted_at FROM customers WHERE id=?", (customer_id,)
    ).fetchone()
    history = conn.execute(
        "SELECT tracking_no FROM devices WHERE customer_name=?",
        ("QA Delete History Customer",),
    ).fetchone()
    conn.close()
    assert customer[0] == 1
    assert customer[1]
    assert history[0] == "QA-HISTORY-1"


def test_customer_list_workbook_rejects_malformed_and_oversized_payloads():
    try:
        web_main.customer_list_workbook([["bad"]])
    except ValueError as error:
        assert str(error) == "Invalid customer export row"
    else:
        raise AssertionError("Malformed customer row was accepted")

    try:
        web_main.customer_list_workbook([[]] * 5001)
    except ValueError as error:
        assert str(error) == "Invalid customer export rows"
    else:
        raise AssertionError("Oversized customer export was accepted")


def test_customer_search_ctrl_k_focuses_and_selects_search():
    source = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "page !== \"customers\"" in source
    assert "event.key.toLowerCase() !== \"k\"" in source
    assert "search.focus();\n    search.select();" in source
    assert "customer-context-parity.js?v=20261027-isolated-customer-print-1" in index
