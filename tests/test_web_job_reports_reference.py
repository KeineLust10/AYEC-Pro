import io
from pathlib import Path

import openpyxl
import pytest

from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_job_report_tabs_match_native_desktop_buttons_at_reference_widths():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert r"Teknik servis performans\u0131, tahsilat dengesi, i\u015f emri durumlar\u0131 ve personel verimlilik analiti\u011fi" in app
    assert "@media screen and (min-width:1200px) and (max-width:1597px){" in styles
    assert 'body[data-page="job-reports"] .content{padding-top:8px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading{margin-top:-7px;margin-bottom:1px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading h2{margin-top:21px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading p{margin-top:5px}' in styles
    assert 'body[data-page="job-reports"] .job-report-panel{margin-top:12px}' in styles
    assert 'body[data-page="job-reports"] .job-report-filters{margin-top:11px;margin-bottom:15px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading .actions{grid-template-columns:70px 241px 112px 100px;gap:6px;width:541px;flex-basis:541px}' in styles
    assert 'body[data-page="job-reports"] .job-report-date-toggle{justify-content:flex-start;padding-left:16px}' in styles
    assert 'body[data-page="job-reports"] .job-report-heading .actions>[data-job-report-monthly]{width:116px;min-width:116px;margin-left:15px;justify-self:start}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs{gap:6px;margin-left:-8px;padding:0 2px}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button{min-height:48px;padding:0 18px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);font-size:13px;font-weight:700}' in styles
    assert 'body[data-page="job-reports"] .job-report-tabs button.active{border-color:var(--brand);background:var(--brand);color:#fff}' in styles
    assert 'body[data-page="job-reports"] .job-report-date{gap:8px;padding:0;border:0;border-radius:0;background:transparent}' in styles
    assert 'body[data-page="job-reports"] .job-report-date span{display:none}' in styles
    assert 'body[data-page="job-reports"] .job-report-date input{height:34px;min-height:0;box-sizing:border-box;padding:6px 8px;border:1px solid var(--line);border-radius:5px;background:var(--surface);color:var(--ink);font-size:11px}' in styles
    assert 'body[data-page="job-reports"] .job-report-status{width:100%;box-sizing:border-box;justify-content:center}' in styles


def test_job_report_uses_service_records_and_report_controls():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'page !== "job-reports" || meta?.table !== "devices"' in app
    assert 'id="jobReportStart"' in app
    assert 'id="jobReportStatus"' in app
    assert 'id="genericHost" hidden' in app
    assert 'data-job-report-tab="technicians"' in app
    assert 'row.tracking_no' in app
    assert 'row.customer_name' in app
    assert 'row.fault_description' in app
    assert 'data-job-report-view=' in app
    assert 'data-job-report-print-row' in app
    assert 'data-job-report-search>Ara</button>' in app
    assert 'if (event.target.closest("[data-job-report-search]")) { ayecJobReportPage=0;ayecJobReportRender();$("#genericSearch")?.focus();return; }' in app
    assert 'window.addEventListener("afterprint", restore, { once: true })' in app
    assert 'row.payment_status || row.collection_status' in app
    assert 'body[data-page="job-reports"] .job-report-table thead th{background:var(--bg)}' in styles
    assert 'body[data-page="job-reports"] .job-report-table tbody tr:nth-child(even){background:var(--bg)}' in styles
    report_renderer = app.split("const rowCells=row=>", 1)[1].split("const renderCell=", 1)[0].split("];return [[", 1)[1]
    desktop_columns = [r'["Teknisyen"', r'["A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem"', '["Durum"', '["Tutar"', '["Para Br."', '["Tarih"']
    positions = [report_renderer.index(value) for value in desktop_columns]
    assert positions == sorted(positions)
    assert '.job-report-table th:nth-child(2){width:11.14%}' in styles
    assert '.job-report-table th:nth-child(4){width:11.04%}' in styles
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
    assert "body[data-page=\"job-reports\"] .job-report-table{width:100%;min-width:996px;table-layout:fixed;font-size:10px}" in styles
    assert '.job-report-table th:nth-child(7){width:6.83%}' in styles
    assert "body[data-page=\"job-reports\"] .job-report-table th{height:38px;box-sizing:border-box;padding:6px 4px;white-space:nowrap;overflow:hidden;text-overflow:clip;line-height:1.1}" in styles
    parity_styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="job-reports"] .job-report-table td:nth-child(4){font-size:10px}' in parity_styles


def test_job_report_exposes_profitability_and_technician_matrix_workflows():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    renderer = app.split("ayecJobReportRender=function(){", 1)[1].split("async function exportJobReportXlsx", 1)[0]
    assert 'ayecJobReportTab==="technicians"' in renderer
    assert 'data-job-report-technician=' in renderer
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


def test_job_tracking_tab_uses_desktop_ledger_source_and_context_actions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert '/api/desktop/table/currency_transactions?limit=1000' in app
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
    assert 'body:JSON.stringify(ayecJobReportExportData)' in app
    assert 'rows:rows.map(row=>' in app
    expected_headers = r'["\u0130\u015f No","M\u00fc\u015fteri / Kurum","Teknisyen","A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem","Durum","Tutar","Para Br.","Tarih","Tahsilat"]'
    assert expected_headers in app
    assert 'const serviceHeaders=["Servis No","M\\u00fc\\u015fteri","Durum","Cihaz / \\u0130\\u015f","Toplam","Giri\\u015f Tarihi","Teslim Tarihi","Teknisyen"]' in app
    assert 'headers:serviceHeaders,rows:serviceExportRows' in app
    assert 'used_parts?limit=1000' in app
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
