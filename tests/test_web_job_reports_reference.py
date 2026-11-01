import io
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import openpyxl
import pytest
import requests
from pypdf import PdfReader

from tests.test_vendor_management_center import _setup_tenant
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_job_report_tabs_match_native_desktop_buttons_at_reference_widths():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert r"Teknik servis performans\u0131, tahsilat dengesi, i\u015f emri durumlar\u0131 ve personel verimlilik analiti\u011fi" in app
    assert "@media screen and (min-width:1200px) and (max-width:1597px){" in styles
    assert 'body[data-page="job-reports"] .content{padding-top:8px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading{transform:translateY(-6px)}body[data-page="job-reports"] .job-report-metrics{transform:translateY(0)}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading{align-items:flex-end;margin-top:0;margin-bottom:1px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading small{font-size:11px;letter-spacing:0}' in styles
    assert 'new Date(reportPeriodNow.getFullYear(), reportPeriodNow.getMonth() - 1, 1)' in app
    assert 'Math.floor(reportPeriodDate.getMonth() / 3) + 1' in app
    assert 'body[data-page="job-reports"] .job-report-heading h2{position:relative;top:-6px;margin-top:21px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading p{margin-top:5px}' in styles
    assert 'body[data-page="job-reports"] .job-report-panel{margin-top:18px;padding:1px 8px 8px}' in styles
    assert 'body[data-page="job-reports"] .job-report-table-wrap{margin-top:11px;margin-bottom:0}' in styles
    assert 'body[data-page="job-reports"] .job-report-filters{margin-top:3px;margin-bottom:12px;transform:translateY(9px)}' in styles
    assert 'body[data-page="job-reports"] .job-report-summary{margin-top:2px;transform:translateY(-1px)}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading .actions{grid-template-columns:70px 241px 112px 100px;gap:6px;width:541px;flex-basis:541px}' in styles
    assert 'data-generic-refresh>Raporu Yenile' not in app
    assert '$("#syncNowBtn").onclick=async' in app
    assert 'href="midnight-reference.css?v=' in index
    assert 'src="app.js?v=' in index
    assert 'body[data-page="job-reports"] .job-report-date-toggle{justify-content:flex-start;padding-left:16px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading .actions>[data-job-report-monthly]{width:116px;min-width:116px;margin-left:15px;justify-self:start}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs{gap:6px;margin-left:-8px;padding:0 2px}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button{min-height:48px;padding:0 19.75px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);font-family:"Segoe UI",Arial,sans-serif;font-size:13px;font-weight:700}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button.active{border-color:var(--brand);background:var(--brand);color:#080e1a}' in styles
    assert 'body[data-page="job-reports"] .job-report-date{gap:8px;padding:0;border:0;border-radius:0;background:transparent}' in styles
    assert 'body[data-page="job-reports"] .job-report-date span{display:none}' in styles
    assert 'body[data-page="job-reports"] .job-report-date input{height:34px;min-height:0;box-sizing:border-box;padding:6px 8px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);font-size:11px}' in styles
    assert 'body[data-page="job-reports"] .job-report-status{width:100%;box-sizing:border-box;justify-content:center}' in styles
    assert 'body[data-page="job-reports"] .job-report-filters>#jobReportCount{font-size:12px;white-space:nowrap}' in styles
    assert "job-report-page-size" not in app
    assert "const size = 15;" in app


def test_job_report_uses_service_records_and_report_controls():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'page !== "job-reports" || meta?.table !== "devices"' in app
    assert 'id="jobReportStart"' in app
    assert 'id="jobReportStatus"' in app
    assert 'class="job-report-filter-select status"' in app
    assert 'id="jobReportCurrency" aria-label="Para birimi filtresi"' in app
    assert r'<option value="all" selected>Birim: T\u00fcm\u00fc</option>' in app
    assert r'"Birim: T\u00fcm\u00fc"' in app
    assert r'"Sorumlu: T\u00fcm\u00fc"' in app
    assert 'id="genericHost" hidden' in app
    assert 'data-job-report-tab="technicians"' in app
    assert 'row.tracking_no' in app
    assert 'row.customer_name' in app
    assert 'row.fault_description' in app
    assert 'class="job-report-description" title="' in app
    assert 'aria-label="\' + esc(row.fault_description || row.fault_category || "-")' in app
    assert 'data-job-report-view=' in app
    assert 'data-job-report-print-row' in app
    assert 'data-job-report-search>Ara</button>' in app
    assert r'placeholder="\u0130\u015f no, m\u00fc\u015fteri, a\u00e7\u0131klama, durum veya para birimi ara..."' in app
    assert 'if (event.target.closest("[data-job-report-search]")) { ayecJobReportPage=0;ayecJobReportRender();$("#genericSearch")?.focus();return; }' in app
    assert 'window.addEventListener("afterprint",()=>rows.forEach((row,index)=>{row.hidden=keep[index]}),{once:true})' in app
    assert 'function ayecPrintJobReportDetail(row)' in app
    assert 'class="status-print-document job-report-detail-print"' in app
    assert 'if(tableRow?.dataset.jobReportKind==="job")' in app
    assert 'Number(value||0).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2})' in app
    assert '@media print{@page{size:A4 landscape;margin:10mm}}' in app
    assert 'row.payment_status || row.collection_status' in app
    assert 'body[data-page="job-reports"] .job-report-table thead th{background:var(--bg)}' in styles
    assert 'body[data-page="job-reports"] .job-report-table tbody tr:nth-child(even){background:var(--bg)}' in styles
    report_renderer = app.split("const rowCells=row=>", 1)[1].split("const renderCell=", 1)[0].split("];return [[", 1)[1]
    desktop_columns = [r'["Teknisyen"', r'["A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem"', '["Durum"', '["Tutar"', '["Para Br."', '["Tarih"']
    positions = [report_renderer.index(value) for value in desktop_columns]
    assert positions == sorted(positions)
    assert '.job-report-table th:nth-child(2){width:11.14%}' in styles
    assert '.job-report-table th:nth-child(4){width:11.04%}' in styles
    assert '.job-report-table[data-report-kind="jobs"] th:nth-child(4){white-space:normal}' in styles
    assert '.job-report-description{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;max-width:56px;line-height:1.2;text-wrap:balance}' in styles
    assert '.job-report-table th:nth-child(5){width:12.65%}' in styles
    assert '.job-report-table th:nth-child(7){width:6.83%}' in styles
    assert '.job-report-table th:nth-child(8){width:9.94%}' in styles
    assert '.job-report-table th:nth-child(9){width:11.65%}' in styles
    assert '.job-report-table th:nth-child(10){width:8.23%}' in styles
    assert '.job-report-table{width:100%;min-width:996px;table-layout:fixed' in styles
    assert '.job-report-actions .mini{width:28px;min-width:28px;height:26px;min-height:26px;padding:0}' in styles
    assert '.job-report-status.pending{color:var(--warning)}' in styles
    assert 'td:nth-child(6){font:700 11px var(--font-mono)}' in styles
    assert 'function ayecJobStatus(row)' in app and 'return "pending"' in app
    assert 'const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)' in app
    assert "@media(max-width:760px){.job-report-heading" in styles
    assert '.job-report-table td:before{content:attr(data-label)' in styles
    assert '.job-report-actions button' in styles
    assert '@media print{body[data-page="job-reports"]' in styles


def test_job_report_metrics_match_native_cards_and_progress_rules():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "job_service_tracking_page.py").read_text(encoding="utf-8")
    metrics = app[app.index('<section class="metric-grid job-report-metrics">'):]
    metrics = metrics[:metrics.index("</section>")]

    assert metrics.count('class="job-report-metric ') == 5
    assert '<strong id="jobReportTotal">0</strong><span>Kay\\u0131tl\\u0131 i\\u015fler</span>' in metrics
    assert '<span>Fiziksel cihaz</span>' in metrics
    assert metrics.count('role="progressbar"') == 5
    assert "function ayecJobUpdateSummaryMetrics(summary,revenueText)" in app
    assert 'total?open*100/total:0' in app
    assert 'total?paid*100/total:0' in app
    assert 'services?100:0' in app
    assert 'card.metric_progress.setFixedHeight(5)' in desktop
    assert ".job-report-metric-icon svg{width:20px;height:20px" in styles
    assert ".job-report-metric-value strong{font:800 32px/1.15 \"Segoe UI\",sans-serif" in styles
    assert 'height:132px;min-height:132px;flex-direction:column' in styles


def test_job_report_footer_summary_matches_native_empty_cards():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    summary = app[app.index('<footer class="job-report-summary">'):]
    summary = summary[:summary.index("</footer>")]

    assert "ORTALAMA ONARIM S\\u00dcRES\\u0130" in summary
    assert summary.count("<strong>-</strong>") == 3
    assert "<span>" not in summary
    assert "height:68px;box-sizing:border-box;gap:4px;padding:8px 12px" in styles
    assert ".job-report-summary small{font-size:10px;font-weight:700}" in styles
    assert ".job-report-summary article:nth-child(3) small{color:var(--brand)}" in styles
    assert ".job-report-summary strong{font-size:17px;font-weight:800}" in styles


def test_job_report_desktop_table_matches_native_text_sizing_and_header_clipping():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert "body[data-page=\"job-reports\"] .job-report-table-wrap{width:calc(100% + 12px);max-width:none;margin-left:-4px;margin-top:-1px;scrollbar-width:none}" in styles
    assert "body[data-page=\"job-reports\"] .job-report-table-wrap::-webkit-scrollbar{display:none}" in styles
    assert '#jobReportHost>.job-report-pagination{position:relative;right:auto;bottom:auto;left:auto;z-index:auto;height:34px' in styles
    assert 'body[data-page="job-reports"] .job-report-table-wrap{margin-top:11px;margin-bottom:0}' in styles
    assert 'body[data-page="job-reports"] .job-report-table-wrap{max-height:min(450px,calc(100vh - 596px));min-height:254px;flex:0 1 auto}' in styles
    assert "body[data-page=\"job-reports\"] .job-report-table{width:100%;min-width:996px;table-layout:fixed;font-size:10px}" in styles
    assert '.job-report-table th:nth-child(7){width:6.83%}' in styles
    assert "body[data-page=\"job-reports\"] .job-report-table th{height:38px;box-sizing:border-box;padding:6px 4px;white-space:nowrap;overflow:hidden;text-overflow:clip;line-height:1.1}" in styles
    parity_styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="job-reports"] .job-report-table td:nth-child(4){font-size:10px}' in parity_styles


def test_job_report_desktop_selection_footer_matches_native_control_order():
    parity_styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert "@media (min-width:1001px){body[data-page=\"job-reports\"] .job-report-pagination{justify-content:flex-start}" in parity_styles
    assert "body[data-page=\"job-reports\"] #jobReportHost>.job-report-pagination{left:-7px;padding-left:0}" in parity_styles
    assert "body[data-page=\"job-reports\"] .job-report-pagination [data-job-report-select-visible]{margin-left:14px}" in parity_styles
    assert "body[data-page=\"job-reports\"] .job-report-pagination>div{margin-left:auto}" in parity_styles


def test_job_report_exposes_profitability_and_technician_matrix_workflows():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    renderer = app.split("ayecJobReportRender=function(){", 1)[1].split("async function exportJobReportXlsx", 1)[0]
    assert 'ayecJobReportTab==="technicians"' in renderer
    assert 'data-job-report-technician=' in renderer
    assert 'Atanmam\\u0131\\u015f' in renderer
    assert 'rows=rows.filter(row=>row.technician_name||row.assigned_technician||row.technician)' not in renderer
    assert 'ayecJobReportRows.map(row=>row.technician_name||row.assigned_technician||row.technician||"Atanmam\\u0131\\u015f")' in renderer
    assert 'ayecJobReportTab==="profit"' in renderer
    assert 'apiFetch(`/api/desktop/job-reports/profitability?${query}`)' in app
    assert 'button.dataset.jobReportMonthly=""' in app
    assert 'apiFetch("/api/desktop/job-reports/monthly")' in app
    assert 'id="jobReportProfitPeriod"' in app
    assert 'input.id="jobReportDateEnabled"' in app
    assert 'id="jobReportRevenue"' in app
    assert 'id="jobReportPaid"' in app
    assert "function ayecJobSummary(transactions,serviceRows)" in app
    assert 'transaction.transaction_type==="CREDIT"' in app
    assert "transaction.try_equivalent||0" in app
    assert "id=\"jobReportDelivered\"" not in app
    assert "id=\"jobReportValue\"" not in app


def test_job_report_search_clear_preserves_active_filters():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'if (event.target.closest("[data-job-report-clear]")) {' in app
    assert 'const search = $("#genericSearch");' in app
    assert '$("#jobReportStatus").value = "all"' not in app
    assert "filterPreserved" in runner
    assert "filterCountBeforeSearch" in runner


def test_job_report_toolbar_widths_match_native_1300px_reference():
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'body[data-page="job-reports"] .job-report-tabs{gap:8px;margin-left:-7px}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button:nth-child(1){flex:0 0 146px;width:146px' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button:nth-child(2){flex:0 0 123px;width:123px' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button:nth-child(3){flex:0 0 166px;width:166px' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button:nth-child(4){flex:0 0 78px;width:78px' in styles
    assert '[data-job-report-search]{flex:0 0 62px;width:62px;min-width:62px' in styles
    assert '[data-job-report-clear]{flex:0 0 93px;width:93px;min-width:93px' in styles
    assert '.job-report-filter-select.status{flex:0 0 154px}' in styles
    assert '.job-report-filter-select.currency{flex:0 0 143px}' in styles
    assert '.job-report-filter-select.technician{flex:0 0 163px}' in styles
    assert '[data-job-report-advanced-toggle]{flex:0 0 100px;width:100px}' in styles


def test_job_tracking_tab_uses_desktop_ledger_source_and_context_actions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'loadAllDesktopTableRows("currency_transactions")' in app
    assert 'transaction.transaction_type==="DEBIT"' in app
    assert 'transaction.transaction_type==="CREDIT"' in app
    assert 'ayecJobReportTab==="jobs"?ayecJobLedgerRows:ayecJobServiceRows' in app
    assert 'data-job-report-kind="${isJobs?"job":"service"}"' in app
    assert 'data-job-report-context="${action}"' in app
    assert r'actions=isJob?[["detail","\uD83D\uDD0D \u0130\u015f Detay\u0131"]]' in app
    assert r'[["detail","\uD83D\uDD0D Detay"],["technician","\uD83D\uDEE0\uFE0F Teknisyen Paneli"],["form","\uD83D\uDCDD Servis Formu"]]' in app
    assert 'ayecJobTrackingDetail(record)' in app
    assert 'id="jobReportTechnician"' in app
    assert 'id="jobReportCustomer"' in app
    assert 'id="jobReportAmountEnabled"' in app
    assert 'amount>=minAmount&&(!maxAmount||amount<=maxAmount)' in app
    assert '''data-job-report-technician="'+esc(name)+'"''' in app
    assert 'ayecJobReportTab!=="technicians"||!db.settings.doubleClick' in app
    assert 'button.dataset.jobReportTab==="service"' in app



def test_job_report_xlsx_export_uses_filtered_rows_and_active_tab_data():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert '"/api/desktop/job-reports/export/xlsx"' in app
    assert '"/api/desktop/job-reports/export/pdf"' in app
    assert 'anchor.download="is-servis-raporu-"+today()+".pdf"' in app
    for export_name in ("exportJobReportXlsx", "exportJobReportPdf"):
        export = app.split(f"async function {export_name}()", 1)[1].split("\n}", 1)[0]
        assert "response.status===401&&window.handleUnauthorized" in export
    assert r'data-job-report-print>PDF \u00d6zeti' in app
    assert 'body:JSON.stringify(ayecJobReportExportData)' in app
    assert 'rows:rows.map(row=>' in app
    expected_headers = r'["\u0130\u015f No","M\u00fc\u015fteri / Kurum","Teknisyen","A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem","Durum","Tutar","Para Br.","Tarih","Tahsilat"]'
    assert expected_headers in app
    assert 'const serviceHeaders=["Servis No","M\\u00fc\\u015fteri","Durum","Cihaz / \\u0130\\u015f","Toplam","Giri\\u015f Tarihi","Teslim Tarihi","Teknisyen"]' in app
    assert 'headers:serviceHeaders,rows:serviceExportRows' in app
    assert 'loadAllDesktopTableRows("used_parts")' in app
    service_loader = app.split("async function ayecLoadJobServiceRows()", 1)[1].split("\n}", 1)[0]
    assert 'window.currentGenericData?.rows||await loadAllDesktopTableRows("devices")' in service_loader
    assert 'used_parts?limit=1000' not in service_loader
    assert 'report_total:Number(row.labor_cost||0)' in app
    assert 'Number(part.price??0)*Number(part.quantity??1)' in app
    assert 'amount=Number(row.report_total??row.debit??row.price??row.labor_cost)||0' in app
    assert 'exitDate.split("-").reverse().join(".")' in app and 'amountText].join(" ")' in app
    row_renderer = app.split("const rowCells=row=>", 1)[1].split("const renderCell=", 1)[0].split("];return [[", 1)[1]
    row_labels = [r'"\u0130\u015f No"', r'["M\u00fc\u015fteri / Kurum"', '["Teknisyen"', r'["A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem"', '["Durum"', '["Tutar"', '["Para Br."', '["Tarih"', '["Tahsilat"', r'["\u0130\u015flemler"']
    row_positions = [row_renderer.index(label) for label in row_labels]
    assert row_positions == sorted(row_positions)
    assert row_renderer.count('["Durum"') == 1
    assert 'rows:matrix.map(([name,stats])=>' in app
    assert 'download("servis-raporu-" + today() + ".csv", ayecJobReportRows)' not in app


def test_job_report_pdf_export_is_authenticated_and_contains_current_rows(monkeypatch, tmp_path):
    _, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/job-reports/export/pdf"
    payload = {
        "headers": ["Job", "Customer", "Status"],
        "rows": [["DEMO-JOB-001", "Audit Customer", "Open"]],
    }
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint, json=payload).status_code == 401

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
        assert login.status_code == 200
        response = session.post(endpoint, json=payload)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-")
        reader = PdfReader(io.BytesIO(response.content))
        assert reader.pages[0].mediabox.width > reader.pages[0].mediabox.height
        pdf_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "AYEC Pro - Is / Servis Takibi Raporu" in pdf_text
        assert "DEMO-JOB-001" in pdf_text
        assert "Audit Customer" in pdf_text
        assert "Open" in pdf_text
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_job_report_xlsx_export_is_authenticated_and_contains_current_rows(monkeypatch, tmp_path):
    _, _tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/job-reports/export/xlsx"
    payload = {
        "headers": ["Job", "Customer", "Status"],
        "rows": [["DEMO-JOB-001", "Audit Customer", "Open"]],
    }
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint, json=payload).status_code == 401

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
        assert login.status_code == 200
        response = session.post(endpoint, json=payload)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        workbook = openpyxl.load_workbook(io.BytesIO(response.content), data_only=True)
        rows = list(workbook.active.values)
        assert rows[0] == tuple(payload["headers"])
        assert rows[1] == tuple(payload["rows"][0])
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)



def test_technician_checklist_api_persists_with_tenant_isolation(monkeypatch, tmp_path):
    _, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    tenant_one = sqlite3.connect(tenant_one_path)
    device_columns = {row[1] for row in tenant_one.execute("PRAGMA table_info(devices)")}
    if "checklist_status" not in device_columns:
        tenant_one.execute("ALTER TABLE devices ADD COLUMN checklist_status TEXT DEFAULT ''")
    tenant_one.execute(
        "INSERT INTO devices(tracking_no,device_type,status,checklist_status) VALUES(?,?,?,?)",
        ("QA-TECH-1", "Laptop", "Tamirde", ""),
    )
    tenant_one.commit()
    tenant_one.close()

    registry = web_main.registry_connect()
    registry.execute(
        "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
        ("tenant-2", "Other Company", "Other Company.db", "2026-01-01T00:00:00"),
    )
    registry.commit()
    registry.close()
    tenant_two_path = web_main.TENANT_ROOT / "Other Company.db"
    tenant_two_path.parent.mkdir(parents=True, exist_ok=True)
    tenant_two = sqlite3.connect(tenant_two_path)
    web_main.ensure_operational_schema(tenant_two)
    web_main.ensure_web_schema(tenant_two)
    tenant_two.execute(
        "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
        ("tenant-two-admin", web_main.password_hash("second-pass123"), "second@example.com", "", "Admin"),
    )
    tenant_two.commit()
    tenant_two.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    catalog_url = f"{base_url}/api/desktop/technician/test-catalog?tracking_no=QA-TECH-1"
    checklist_url = f"{base_url}/api/desktop/technician/checklist"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(catalog_url).status_code == 401
        assert anonymous.post(checklist_url, json={"tracking_no": "QA-TECH-1", "selected_labels": []}).status_code == 401

        tenant_one_session = requests.Session()
        tenant_one_session.headers["Origin"] = base_url
        login = tenant_one_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        catalog = tenant_one_session.get(catalog_url)
        assert catalog.status_code == 200
        tests = catalog.json()["tests"]
        assert tests and tests[0]["active"] is True
        selected_label = tests[0]["name"]
        saved = tenant_one_session.post(
            checklist_url,
            json={"tracking_no": "QA-TECH-1", "selected_labels": [selected_label, selected_label]},
        )
        assert saved.status_code == 200
        assert saved.json()["checklist_status"] == selected_label
        assert tenant_one_session.get(f"{base_url}/api/desktop/technician/history?tracking_no=QA-TECH-1").status_code == 200
        assert tenant_one_session.get(f"{base_url}/api/desktop/technician/test-catalog?tracking_no=UNKNOWN").status_code == 404

        tenant_two_session = requests.Session()
        tenant_two_session.headers["Origin"] = base_url
        second_login = tenant_two_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "tenant-two-admin", "password": "second-pass123", "tenant_id": "tenant-2"},
        )
        assert second_login.status_code == 200
        assert tenant_two_session.get(catalog_url).status_code == 404
        cross_tenant_write = tenant_two_session.post(
            checklist_url,
            json={"tracking_no": "QA-TECH-1", "selected_labels": [selected_label]},
        )
        assert cross_tenant_write.status_code == 404
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

def test_job_report_workbook_validates_rows_and_sanitizes_formula_cells():
    payload = web_main.desktop_job_report_workbook({
        "headers": ["Report", "Amount"],
        "rows": [["=1+1", 12.5]],
    })
    sheet = openpyxl.load_workbook(io.BytesIO(payload), data_only=False).active

    assert list(sheet.values) == [("Report", "Amount"), ("'=1+1", 12.5)]
    assert sheet.freeze_panes == "A2"
    assert sheet.auto_filter.ref == "A1:B2"
    with pytest.raises(ValueError):
        web_main.desktop_job_report_workbook({"headers": ["A", "B"], "rows": [["only one"]]})


def test_job_report_description_uses_native_measured_wrap_width():
    css = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    route_audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert '@media screen and (min-width:1001px){body[data-page="job-reports"] .job-report-description{' in css
    assert "-webkit-line-clamp:2;overflow:hidden;max-width:56px;line-height:1.2;text-wrap:balance}" in css
    assert "layoutTextLines" in route_audit
    assert "visibleTextLines" in route_audit
    assert "!result.jobReportCaptureState.descriptionHeader?.fits" in route_audit


def test_job_report_keyboard_context_menu_has_offscreen_workflow_coverage():
    route_audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'event.key==="ContextMenu"||(event.shiftKey&&event.key==="F10")' in app
    assert "jobReportKeyboardContextAudit" in route_audit
    assert 'JSON.stringify(item.actions) !== JSON.stringify(item.kind === "job" ? ["detail"] : ["detail", "technician", "form"])' in route_audit
    assert 'technicianAction.title.includes("QA-SERVICE-1")' in route_audit
    assert 'technicianAction.parts' in route_audit
    assert 'technicianAction.technician' in route_audit
    assert 'technicianAction.labor' in route_audit
    assert 'detailAction.summary' in route_audit
    assert 'formAction.customer' in route_audit
    assert 'technicianWorkflow.checklistWrites.length !== 1' in route_audit
    assert 'technicianWorkflow.historyText.includes("QA technician history")' in route_audit

def test_job_report_pdf_export_recovery_is_exercised_in_hidden_browser():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "jobReportPdfExportRecoveryWorkflow" in runner
    assert 'root?.querySelector(".toast.error")' in runner
    assert 'requests !== 2' in runner
    assert 'noDownloadAfterFailure' in runner

def test_job_report_xlsx_export_recovery_is_exercised_in_hidden_browser():
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "jobReportXlsxExportRecoveryWorkflow" in runner
    assert 'root?.querySelector(".toast.error")' in runner
    assert 'requests !== 2' in runner
    assert 'noDownloadAfterFailure' in runner

def test_job_report_tabs_use_keyboard_accessible_aria_pattern():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'role="tablist" aria-orientation="horizontal"' in app
    assert "function ayecJobReportSyncTabs()" in app
    for key in ("ArrowLeft", "ArrowRight", "Home", "End"):
        assert f'"{key}"' in app
    assert "jobReportTabsKeyboardWorkflow" in runner


def test_job_report_rows_match_extended_selection_keyboard_and_pointer_behavior():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'aria-multiselectable="true"' in app
    assert 'toggle: event.ctrlKey || event.metaKey, extend: event.shiftKey' in app
    for key in ("ArrowDown", "ArrowUp", "Home", "End"):
        assert f'event.key === "{key}"' in app
    assert "jobReportExtendedSelectionAudit" in runner
    assert "jobReportTallViewport" in runner
    assert "visibleRows < 6" in runner
    assert "summary?.top < result.jobReportDensity.pagination?.bottom - 1" in runner
    assert "jobSelection.shiftEnd" in runner
    assert "jobSelection.selectAll" in runner
