from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


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
    assert "@media(max-width:760px){.job-report-heading" in styles
    assert '@media print{body[data-page="job-reports"]' in styles


def test_job_report_does_not_claim_unavailable_profit_or_staff_data():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Teknisyen verisi bulunamad" in app
    assert "Net k\\u00e2rl\\u0131l\\u0131k i\\u00e7in maliyet verisi gerekir" in app
    assert 'id="jobReportValue"' in app
