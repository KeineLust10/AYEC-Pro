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
    assert 'data-job-report-view=' in app
    assert 'data-job-report-print-row' in app
    assert 'row.payment_status || row.collection_status' in app
    assert 'const first = new Date(now.getFullYear(), now.getMonth() - 1, 1)' in app
    assert "@media(max-width:760px){.job-report-heading" in styles
    assert '.job-report-table td:before{content:attr(data-label)' in styles
    assert '.job-report-actions button' in styles
    assert '@media print{body[data-page="job-reports"]' in styles


def test_job_report_does_not_claim_unavailable_profit_or_staff_data():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Teknisyen verisi bulunamad" in app
    assert "Net k\\u00e2rl\\u0131l\\u0131k i\\u00e7in maliyet verisi gerekir" in app
    assert 'id="jobReportValue"' in app


def test_job_tracking_tab_uses_desktop_ledger_source_and_context_actions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert '/api/desktop/table/currency_transactions?limit=1000' in app
    assert 'transaction.transaction_type==="DEBIT"' in app
    assert 'transaction.transaction_type==="CREDIT"' in app
    assert 'ayecJobReportTab==="jobs"?ayecJobLedgerRows:ayecJobServiceRows' in app
    assert 'data-job-report-kind="\'+kind+\'"' in app
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
