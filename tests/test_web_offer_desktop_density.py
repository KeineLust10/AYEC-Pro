import json
import sqlite3
import subprocess
from pathlib import Path
from types import SimpleNamespace

from src.services.offer_service import OfferService


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
APP = WEB / "app.js"


def test_offer_desktop_table_and_toolbar_use_compact_reference_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="offers"] .offers-reference-metrics .metric' in styles
    assert 'body[data-page="offers"] .offers-reference-list > .toolbar' in styles
    assert 'body[data-page="offers"] .offers-reference-table td' in styles
    assert "height: 90px;" in styles
    assert "line-height: 1.15;" in styles


def test_offer_report_metric_cards_match_reference_height():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="offer-reports"] .offer-report-metrics .metric' in styles
    assert "height: 64px;" in styles


def test_offer_report_cells_preserve_desktop_value_tooltips():
    app = APP.read_text(encoding="utf-8")
    start = app.index("function renderOfferReports()")
    end = app.index("\nconst ayecRenderBeforeDesktopOfferReports", start)
    renderer = app[start:end]

    assert "const tooltipCell=value=>`<td title=\"${esc(value)}\">${esc(value)}</td>`" in renderer
    assert '<td title="${esc(customers)}">${esc(visibleCustomers)}</td>' in renderer
    assert "${tooltipCell(staff)}${tooltipCell(total)}" in renderer


def test_offer_page_has_status_and_currency_filters_with_visible_count():
    app = APP.read_text(encoding="utf-8")

    assert 'id="offerStatusFilter"' in app
    assert 'id="offerCurrencyFilter"' in app
    assert 'id="offerReferencePagination"' in app
    assert 'event.target.id==="offerStatusFilter"||event.target.id==="offerCurrencyFilter"' in app
    assert 'element.hidden=matchIndex<first||matchIndex>=last' in app
    assert '(window.currentGenericData?.rows||[]).filter(offerReferenceMatches)' in app
    assert 'data-offer-page' in app
    assert '`${rangeStart}-${rangeEnd} / ${matching.length} Teklif`' in app
    assert "function updateOfferReferenceSummary(rows,totalCount)" in app
    assert 'updateOfferReferenceSummary(summaryRows,summaryCount)' in app


def test_offer_list_edit_loads_the_selected_offer_into_the_sales_editor():
    app = APP.read_text(encoding="utf-8")

    assert '$$("#genericHost .generic-edit").forEach(button=>' in app
    assert 'String(item.id)===String(row?.id)' in app
    assert "beginOfferEdit(offer)" in app


def test_offer_report_month_order_matches_desktop_trend_query():
    fixtures = [
        {"created_at": "2025-10-31T23:59:59Z", "total_try": 100, "company_name": "Outside Window", "customer_name": "Outside Window", "created_by": "A", "status": "draft"},
        {"created_at": "2025-11-01T00:00:00Z", "total_try": 200, "company_name": "November", "customer_name": "November", "created_by": "A", "status": "pending"},
        {"created_at": "2025-12-15T12:00:00Z", "total_try": 300, "company_name": "December", "customer_name": "December", "created_by": "B", "status": "accepted"},
        {"created_at": "2026-10-20T12:00:00Z", "total_try": 0, "company_name": "October", "customer_name": "October", "created_by": "B", "status": "rejected"},
        {"created_at": "2026-10-21T12:00:00Z", "total_try": 500, "company_name": "October", "customer_name": "October", "created_by": "C", "status": "onaylandi"},
        {"created_at": "2026-10-21T13:00:00Z", "total_try": 50, "company_name": "Whitespace", "customer_name": "Whitespace", "created_by": "D", "status": " pending "},
        {"created_at": "2026-10-21T14:00:00Z", "total_try": 25, "company_name": "Unicode", "customer_name": "Unicode", "created_by": "E", "status": "onayland\u0131"},
        {"created_at": "2026-10-21T15:00:00Z", "total_try": 10, "company_name": " ", "customer_name": "Trim fallback", "created_by": "F", "status": "pending"},
        {"created_at": "2026-10-21T16:00:00Z", "total_try": 5, "company_name": "", "customer_name": "", "created_by": "G", "status": "pending"},
    ]
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE offers (id INTEGER, created_at TEXT, total_try REAL, company_name TEXT, customer_name TEXT, created_by TEXT, status TEXT)"
    )
    connection.create_function(
        "date",
        -1,
        lambda *args: "2025-11-01" if args == ("now", "-11 months", "start of month") else None,
    )
    connection.executemany(
        "INSERT INTO offers(created_at,total_try,company_name,customer_name,created_by,status) VALUES(?,?,?,?,?,?)",
        [(row["created_at"], row["total_try"], row["company_name"], row["customer_name"], row["created_by"], row["status"]) for row in fixtures],
    )
    service = OfferService(SimpleNamespace(conn=connection, cursor=connection.cursor()))
    desktop_months = [row[0] for row in service.monthly_offer_trend()]

    source = APP.read_text(encoding="utf-8")
    normalize_start = source.index("function normalizeOfferStatus")
    normalize_end = source.index("\n", normalize_start)
    report_normalize_start = source.index("function normalizeOfferReportStatus")
    report_normalize_end = source.index("\n", report_normalize_start)
    start = source.index("function buildOfferReportData")
    end = source.index("function renderOfferReports()", start)
    web_functions = (
        source[normalize_start:normalize_end]
        + "\n"
        + source[report_normalize_start:report_normalize_end]
        + "\n"
        + source[start:end]
    )
    web_script = (
        web_functions
        + "\nconst rows="
        + json.dumps(fixtures)
        + ";const data=buildOfferReportData(rows,new Date('2026-10-21T12:00:00.000Z'));process.stdout.write(JSON.stringify({total:data.total,pending:data.pending,accepted:data.accepted,rejected:data.rejected,amount:data.amount,months:data.months.map(([month,item])=>[month,item.count,item.total,[...item.customers].sort(),[...item.staff].sort()]),customers:data.customers.map(([name,item])=>[name,item.count,item.total]),staff:data.staff.map(([name,item])=>[name,item.count,item.total,item.latest])}));"
    )
    result = subprocess.run(["node", "-e", web_script], capture_output=True, text=True, check=True)
    web_data = json.loads(result.stdout)

    summary = service.offer_summary()
    desktop_month_rows = service.monthly_offer_trend()
    desktop_customer_rows = service.customer_offer_distribution()
    desktop_staff_rows = service.personnel_offer_distribution()
    assert web_data["total"] == summary[0]
    assert web_data["pending"] == summary[1]
    assert web_data["accepted"] == summary[2]
    assert web_data["rejected"] == summary[3]
    assert web_data["amount"] == summary[4]
    assert [row[0] for row in web_data["months"]] == desktop_months == ["2026-10", "2025-12", "2025-11"]
    assert web_data["months"] == [
        [row[0], row[1], row[2], sorted((row[3] or "").split(",")), sorted((row[4] or "").split(","))]
        for row in desktop_month_rows
    ]
    assert web_data["customers"] == [[row[0], row[1], row[2]] for row in desktop_customer_rows]
    assert web_data["staff"] == [[row[0], row[1], row[2], row[3]] for row in desktop_staff_rows]


def test_offer_list_summary_statuses_match_desktop_sql():
    statuses = [
        "draft",
        "pending",
        "waiting",
        "beklemede",
        "accepted",
        "approved",
        "onaylandi",
        "rejected",
        "declined",
        "reddedildi",
        "revision_pending",
        "sent",
        "created",
        " pending ",
        "onayland\u0131",
    ]
    rows = [{"status": status, "total_try": index + 1} for index, status in enumerate(statuses)]
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE offers (status TEXT, total_try REAL)")
    connection.executemany(
        "INSERT INTO offers(status,total_try) VALUES (?,?)",
        [(row["status"], row["total_try"]) for row in rows],
    )
    service = OfferService(SimpleNamespace(conn=connection, cursor=connection.cursor()))
    desktop_summary = service.offer_summary()

    source = APP.read_text(encoding="utf-8")
    start = source.index("function normalizeOfferStatus")
    end = source.index("function renderOffersReference()", start)
    web_script = (
        source[start:end]
        + "\nconst rows="
        + json.dumps(rows)
        + ";process.stdout.write(JSON.stringify(buildOfferListSummary(rows)));"
    )
    result = subprocess.run(["node", "-e", web_script], capture_output=True, text=True, check=True)
    web_summary = json.loads(result.stdout)

    assert (web_summary["total"], web_summary["pending"], web_summary["accepted"], web_summary["rejected"], web_summary["volume"]) == desktop_summary
