import base64
import io
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
import sqlite3
import subprocess
import threading
from datetime import datetime, timedelta

import requests
import openpyxl

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_history_export_handles_expired_sessions_and_html_fallbacks():
    source = (WEB / "customer-history-parity.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "response.status === 401 && window.handleUnauthorized" in source
    assert "assertDownloadResponse(response)" in source
    assert "customer-history-parity.js?v=20261026-customer-history-export-auth-1" in index
    assert "result.customerHistoryExportSessionWorkflow" in route_smoke
    assert "historyExport.unauthorizedCalls !== 1" in route_smoke
    assert "historyExport.htmlFallbackRejected" in route_smoke


def test_customer_device_summary_uses_all_database_devices():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    start = app.index("function renderCustomers()")
    end = app.index("\nfunction ", start + 10)
    customer_renderer = app[start:end]

    assert "const metricDevices=db.devices||[]" in customer_renderer
    assert "assemblyCount=metricDevices.filter" in customer_renderer
    assert "testCount=metricDevices.filter" in customer_renderer
    assert "activeDeviceCount=metricDevices.filter" in customer_renderer
    assert 'customerListParity.databaseMetrics.active !== "3 Adet Aktif"' in audit


def test_customer_header_actions_match_reference_hierarchy_and_mobile_widths():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    start = app.index("function renderCustomers()")
    end = app.index("function customerTable", start)
    template = app[start:end]

    assert template.index("customer-page-head") < template.index("customer-head-actions")
    assert r'placeholder="\u2315  \u0130sim, unvan, telefon, vergi no veya e-posta ile anl\u0131k filtrele..."' in template
    assert template.index("customer-head-actions") < template.index("customer-management")
    assert template.index("customer-export-actions") < template.index("customer-add")
    assert ".customer-head-actions{display:grid" in styles
    assert "@media(max-width:760px){.customer-page-head" in styles
    assert "@media(max-width:420px){.customer-export-actions" in styles
    assert ".customer-export-actions .mini{min-height:38px;padding:8px;font-size:12px}" in styles
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="customers"] .customer-page-head{min-height:112px;align-items:center;margin:0;padding:14px 16px;border:1px solid var(--line);border-radius:12px;background:var(--surface)}' in parity
    assert 'body[data-page="customers"] .customer-page-head .customer-export-actions {\n    display: grid;' in parity
    assert 'body[data-page="customers"] .customer-page-head .customer-export-actions .mini {\n    width: 100%;' in parity
    assert ".customer-filterbar{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:12px}" in styles
    assert "@media(max-width:420px){.customer-filterbar{grid-template-columns:minmax(0,1fr)}" in styles


def test_customer_bulk_sms_action_uses_selected_rows_and_tenant_endpoint():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function customerSmsSelected()")
    end = app.index("function customerHistorySelected()", start)
    action = app[start:end]

    assert 'data-action="customer-sms-selected"' in app
    assert 'if(action==="customer-sms-selected")customerSmsSelected()' in app
    assert '$$(".customer-row-select:checked")' in action
    assert "openCustomerSmsDialog(selected[index++],next)" in action
    assert '/api/desktop/customer-sms' in app


def test_customer_desktop_filter_rows_and_main_content_spacing_match_reference():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="customers"] .customer-filterbar' in styles
    assert "grid-template-columns: 285px 240px 225px max-content;" in styles
    assert "min-height: 132px;" in styles
    assert "grid-column: 1 / -1;" in styles
    assert "width: 560px;" in styles





def test_customer_reference_table_and_metrics_fit_viewport():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="customers"] #customerTable { height: 285px; min-height: 285px; flex: none; }' in styles
    assert 'body[data-page="customers"] #customerTable { height: auto; min-height: 0; flex: none; }' in styles


def test_customer_metrics_and_hover_use_midnight_enterprise_surfaces():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="customers"] .customer-metrics {\n  background: transparent;' in styles
    assert 'body[data-page="customers"] .customer-metrics .metric {\n  background: var(--surface);' in styles
    assert 'body[data-page="customers"] .customer-filterbar {\n  background: var(--surface);' in styles
    assert 'body[data-page="customers"] .customer-data-table th{background:var(--surface-2)}' in (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="customers"] .customer-data-table tbody tr:not(:hover) td{background:var(--bg)}' in styles
    assert '@media(min-width:761px){body[data-page="customers"] .customer-data-table tbody tr{height:60px}}' in styles
    assert 'body[data-page="customers"] .customer-data-table td{height:48px!important;padding:6px;font-size:11px;line-height:1.12}' in styles
    assert 'body[data-page="customers"] .customer-data-table tbody tr{height:48px}' in styles
    assert 'body[data-page="customers"] .customer-data-table td{height:36px!important}' in styles
    assert 'body[data-page="customers"] .customer-data-table tbody tr:hover td {\n  background: var(--surface-2);' in styles


def test_customer_page_uses_native_sans_serif_font_stack():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'body[data-page="customers"] .customer-page-head,body[data-page="customers"] .customer-metrics' in styles
    assert 'font-family:"Segoe UI",Arial,sans-serif' in styles
    assert 'font:700 12px "Segoe UI",Arial,sans-serif' in styles
    assert "Times New Roman" not in styles
    assert 'body[data-page="customers"] .customer-filterbar{display:flex;flex-wrap:nowrap;align-items:center;gap:7px;min-height:0;grid-template-columns:none;margin:12px 0 0;' in styles
    assert 'desktop-parity.css?v=20261028-sidebar-section-heading-typography-1' in index


def test_customer_desktop_table_fits_native_responsive_column_sizing():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "_customers_base_mixin.py").read_text(encoding="utf-8")

    assert "self._customer_column_widths = (32, 156, 339, 202, 209, 410, 132, 182, 218)" in desktop
    assert "if available < 1100:" in desktop
    assert "widths = (34, 68, 175, 78, 128, 108, 110, 76, 145)" in desktop
    assert "scale = available / total" in desktop
    assert "container-type:inline-size;container-name:customer-table" in styles
    assert "@container customer-table (max-width:1099px)" in styles
    assert "width:100%;min-width:0;max-width:100%;table-layout:fixed" in styles
    assert "width:3.7%" in styles and "width:21.8%" in styles


def test_customer_contact_values_keep_native_hover_tooltips():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function customerTable(rows)")
    end = app.index("\nfunction ", start + 10)
    template = app[start:end]

    assert 'class="customer-contact"><span title="${esc(c.phone||"-")}"' in template
    assert '<small title="${esc(c.email||"-")}"' in template


def test_customer_table_supports_native_sortable_headers():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "_customers_data_mixin.py").read_text(encoding="utf-8")

    assert "header.setSortIndicator(2, Qt.SortOrder.AscendingOrder)" in (ROOT / "src" / "ui" / "pages" / "_customers_base_mixin.py").read_text(encoding="utf-8")
    assert "self.table.setSortingEnabled(True)" in desktop
    assert 'data-customer-sort="2" tabindex="0" aria-sort="ascending"' in app
    assert 'rows.sort((left,right)=>' in app
    assert 'th.onkeydown=event=>' in app
    assert 'th[data-customer-sort][aria-sort="descending"]::after' in styles


def test_customer_directory_defaults_to_non_deleted_non_partner_rows():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    start = app.index("function renderCustomers(){")
    end = app.index("\nfunction ", start + 10)
    renderer = app[start:end]

    assert 'function isCustomerDirectoryPartner(customer)' in app
    assert 'function customerDirectoryRows(includePartners=false)' in app
    assert 'customers=customerDirectoryRows()' in renderer
    assert 'customerTable(customers)' in renderer
    assert 'customerDirectoryRows(type==="partner"||type==="dealer")' in app
    assert 'result.customerDirectoryIsolation' in route_smoke
    assert 'defaultHasPartner || result.customerDirectoryIsolation.defaultHasDeleted' in route_smoke


def test_customer_selection_is_scoped_to_the_visible_page():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    context = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "_customers_ui_mixin.py").read_text(encoding="utf-8")

    assert "for row in range(self.table.rowCount())" in desktop
    assert "const selectedCustomerIds=new Set" in app
    assert "selectedCustomerIds.add(id)" in app
    assert "input.checked=selectedCustomerIds.has(String(input.dataset.id))" in app
    assert "selectedCustomerIds.clear();page=Math.max(0,page-1)" in app
    assert "selectedCustomerIds.clear();page++" in app
    assert "window.ayecSelectedCustomerIds" in context


def test_authenticated_customer_directory_loads_reference_fixture_in_browser(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    fixture_path = ROOT / "tools" / "quality" / "fixtures" / "customer_management_reference.json"
    customers = json.loads(fixture_path.read_text(encoding="utf-8"))
    native_customer_order = [1, 2, 58, 25, 44, 19, 32]
    customers.sort(
        key=lambda customer: (
            native_customer_order.index(int(customer["id"]))
            if int(customer["id"]) in native_customer_order
            else len(native_customer_order) + int(customer["id"])
        )
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url.rstrip("/")
        login = session.post(
            f"{base_url.rstrip('/')}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text
        assert login.json()["user"]["role"] == "Admin"
        assert login.json()["user"]["is_control_admin"] is False
        with sqlite3.connect(tenant_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(customers)")}
            assert {"is_partner", "contract_type", "sla_level"}.issubset(columns)
            assert "Kurumsal" not in columns
            assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
        customer_ids = {}
        for customer in reversed(customers):
            payload = {
                key: value
                for key, value in customer.items()
                if key in columns
                and key != "id"
                and (value is None or isinstance(value, (str, int, float)))
            }
            response = session.post(f"{base_url.rstrip('/')}/api/desktop/table/customers", json=payload)
            assert response.status_code in {200, 201}, response.content.decode("utf-8", errors="replace")
            customer_ids[int(customer["id"])] = response.json()["id"]
        report_date = (datetime.now().replace(day=1) - timedelta(days=15)).strftime("%Y-%m-%d")
        for customer in customers:
            customer_id = customer_ids[int(customer["id"])]
            for currency, balance in (customer.get("balances") or {}).items():
                response = session.post(
                    f"{base_url.rstrip('/')}/api/desktop/table/customer_currency_balances",
                    json={"customer_id": customer_id, "currency": currency, "balance": balance},
                )
                assert response.status_code in {200, 201}, response.content.decode("utf-8", errors="replace")
            for service_index, service in enumerate(customer.get("services") or []):
                service_payload = {
                    "customer_id": customer_id,
                    "customer_name": customer["name"],
                    "status": service.get("status") or "",
                    "is_archived": service.get("is_archived") or 0,
                }
                if customer is customers[0] and service_index == 0:
                    service_payload.update(
                        tracking_no="QA-SERVICE-ROUNDTRIP",
                        technician="QA Technician",
                        fault_description="Authenticated service report fixture",
                        entry_date=report_date,
                    )
                response = session.post(
                    f"{base_url.rstrip('/')}/api/desktop/table/devices",
                    json=service_payload,
                )
                assert response.status_code in {200, 201}, response.content.decode("utf-8", errors="replace")
        report_customer_id = customer_ids[int(customers[0]["id"])]
        report_timestamp = report_date + "T09:00:00"
        with sqlite3.connect(tenant_path) as conn:
            for transaction_type, amount, description in (
                ("DEBIT", 2500, "Authenticated job charge"),
                ("CREDIT", 1000, "Authenticated partial collection"),
            ):
                conn.execute(
                    "INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,description,tracking_no,created_at,current_balance) VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (report_customer_id, transaction_type, amount, "TRY", 1, amount, description, "QA-JOB-ROUNDTRIP", report_timestamp, 1500),
                )
            conn.commit()
        session_cookie = session.cookies.get("ayec_session")
        assert session_cookie
        screenshot_path = ROOT / "output" / "playwright" / "customer-directory-tenant-parity-20261018" / "customer-directory-live-tenant-1300x850.png"
        job_report_screenshot_path = screenshot_path.with_name("job-report-live-tenant-1300x850.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        expected_filter_counts = {
            "vip": sum(
                "vip" in str(customer.get("type") or "").lower()
                or "VIP" in str(customer.get("contract_type") or "").upper()
                for customer in customers
            ),
            "locationAnkara": sum(customer.get("city") == "Ankara" for customer in customers),
            "debt": sum(
                any(float(balance or 0) < 0 for balance in (customer.get("balances") or {}).values())
                for customer in customers
            ),
        }
        env = os.environ.copy()
        env.update(
            {
                "AYEC_CUSTOMER_BASE_URL": base_url,
                "AYEC_CUSTOMER_SESSION_COOKIE": session_cookie,
                "AYEC_CUSTOMER_SEARCH_TERM": str(customers[0]["name"]),
                "AYEC_CUSTOMER_CDP_PORT": str(19500 + (os.getpid() % 400)),
                "AYEC_CUSTOMER_SCREENSHOT_PATH": str(screenshot_path),
                "AYEC_JOB_REPORT_SCREENSHOT_PATH": str(job_report_screenshot_path),
                "AYEC_CUSTOMER_FILTER_EXPECTATIONS": json.dumps(expected_filter_counts, ensure_ascii=True),
            }
        )
        audit = subprocess.run(
            ["node", "tools/quality/customer_directory_authenticated_roundtrip.cjs"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        audit_result_path = screenshot_path.with_name("customer-directory-live-tenant-audit.json")
        audit_result_path.write_text(audit.stdout, encoding="utf-8")
        browser_result = json.loads(audit.stdout)
        initial = browser_result["initial"]
        assert initial["total"] == 28
        assert initial["visibleRows"] == 15
        assert initial["page"] == "1 / 2"
        assert browser_result["nextPageEnabled"] is True
        assert browser_result["secondPage"] == "2 / 2"
        assert browser_result["searchMatches"] == 1
        assert browser_result["filterAudit"] == expected_filter_counts
        assert initial["metrics"][:2] == ["\u20ba22,300.00 TRY", "\u20ba0.00 TRY"]
        assert initial["metrics"][2] == "4 Adet Aktif"
        assert initial["metrics"][3] == "28.6%"
        assert initial["metricSecondary"][0] == "USD: $235.00"
        assert initial["firstNames"] == [customer["name"] for customer in customers[:5]]
        customer_edit = browser_result["customerEdit"]
        assert customer_edit["observedEditedPhone2"] == customer_edit["editedPhone2"]
        assert customer_edit["restoredPhone2"] == (customers[0].get("phone2") or "")
        assert customer_edit["restored"] is True
        job_report = browser_result["jobReport"]
        assert job_report["targetJob"] == {
            "customer": customers[0]["name"],
            "tracking": "QA-JOB-ROUNDTRIP",
            "debit": 2500,
            "credit": 1000,
            "remaining": 1500,
            "payment": "K\u0131smi \u00d6deme",
        }
        assert job_report["metrics"]["labels"] == [
            "Toplam \u0130\u015fler",
            "A\u00e7\u0131k \u0130\u015fler",
            "Tahsil Edilen",
            "Toplam Servis",
            "Net Tahsilat Hacmi",
        ]
        metric_values = [int(value) for value in job_report["metrics"]["values"][:4]]
        total_jobs, open_jobs, paid_jobs, total_services = metric_values
        assert total_jobs == 1 and open_jobs == 1 and paid_jobs == 0 and total_services > 0
        assert job_report["metrics"]["progress"] == [
            100,
            round(open_jobs * 100 / total_jobs),
            round(paid_jobs * 100 / total_jobs),
            100,
            0,
        ]
        assert job_report["historyRows"] == 2
        assert job_report["detailShowsTracking"] and job_report["detailShowsCustomer"]
        assert job_report["serviceVisible"] and job_report["serviceTracking"] == "QA-SERVICE-ROUNDTRIP"
        assert job_report["monthlyRows"] == 12
        assert job_report["profitabilityRows"] == 1 and job_report["profitabilityStatus"]
        assert job_report["exportFilename"].endswith(".xlsx")
        workbook = openpyxl.load_workbook(
            io.BytesIO(base64.b64decode(job_report["workbookBase64"])),
            data_only=True,
            read_only=True,
        )
        export_rows = list(workbook.active.iter_rows(values_only=True))
        assert export_rows[0] == (
            "\u0130\u015f No",
            "M\u00fc\u015fteri / Kurum",
            "Teknisyen",
            "A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem",
            "Durum",
            "Tutar",
            "Para Br.",
            "Tarih",
            "Tahsilat",
        )
        assert export_rows[1][0] == "QA-JOB-ROUNDTRIP"
        assert export_rows[1][5] == 2500
        saved_note = browser_result["customerNote"]
        with sqlite3.connect(tenant_path) as conn:
            restored_phone = conn.execute(
                "SELECT phone2 FROM customers WHERE id=?",
                (customer_edit["customerId"],),
            ).fetchone()[0]
            assert restored_phone == (customers[0].get("phone2") or "")
            transactions = conn.execute(
                "SELECT transaction_type,amount FROM currency_transactions WHERE tracking_no=? ORDER BY transaction_type",
                ("QA-JOB-ROUNDTRIP",),
            ).fetchall()
            assert transactions == [("CREDIT", 1000.0), ("DEBIT", 2500.0)]
            note_row = conn.execute(
                "SELECT customer_id,title,content FROM customer_notes WHERE id=?",
                (saved_note["id"],),
            ).fetchone()
            assert note_row == (
                saved_note["customerId"],
                "Authenticated browser note QA",
                "Saved from the authenticated customer 360 workflow.",
            )
        cleanup_note = session.post(
            f"{base_url.rstrip('/')}/api/desktop/table/customer_notes",
            json={"id": saved_note["id"], "_action": "delete"},
        )
        assert cleanup_note.status_code == 200, cleanup_note.content.decode("utf-8", errors="replace")
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM customer_notes").fetchone()[0] == 0
        assert browser_result["browserExceptions"] == 0
        assert screenshot_path.exists() and screenshot_path.stat().st_size > 0
        assert job_report_screenshot_path.exists() and job_report_screenshot_path.stat().st_size > 0
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 28
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_offscreen_route_audit_covers_selected_customer_sms_sequence():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.customerSmsSelectionWorkflow" in route_smoke
    assert 'sms.selectedIds.join(",") !== "9901,9902,9903"' in route_smoke
    assert "sms.payloads.length !== 2" in route_smoke
    assert "Number(sms.payloads[0].customer_id) !== 9902" in route_smoke
    assert "Number(sms.payloads[1].customer_id) !== 9903" in route_smoke
    assert "!sms.noPhoneToast" in route_smoke
    assert "!sms.dialogClosed" in route_smoke


def test_offscreen_route_audit_covers_sequential_customer_history_cards():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.customerHistorySequenceWorkflow" in route_smoke
    assert 'history.opened.join(",") !== "9911,9912"' in route_smoke
    assert 'history.firstTitle.includes("QA History One")' in route_smoke
    assert 'history.secondTitle.includes("QA History Two")' in route_smoke
    assert "!history.dialogClosed" in route_smoke
