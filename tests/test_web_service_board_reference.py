from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_board_today_filter_accepts_localized_desktop_dates():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert "ayecFinanceDateKey(item.date||item.entry)!==ayecLocalDateKey(new Date())" in app
    assert 'match(/^(\\d{2})\\.(\\d{2})\\.(\\d{4})$/)' in app
    assert '"bekliyor","BEK\\u0130YOR"' in app
    assert '"teslim","TESL\\u0130M"' in app
    assert "@media(max-width:760px){.service-board-toolbar" in styles


def test_service_board_stage_quick_filters_match_desktop():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    native = (ROOT / "src" / "ui" / "pages" / "service_board_page.py").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'addItem("Par\\u00e7a bekliyor", "parts")' in native
    assert 'addItem("Test / Onay", "test")' in native
    assert 'data-service-board-filter="parts"' in app
    assert 'data-service-board-filter="test"' in app
    assert 'data-service-board-filter="urgent"' in app
    assert r'ayecServiceBoardFilter==="urgent"&&!/acil|urgent|kritik|y\u00fcksek|yuksek/i' in app
    assert 'ayecServiceBoardFilter==="parts"&&!/par\\u00e7a|parca/i.test(status)' in app
    assert 'ayecServiceBoardFilter==="test"&&!/test|onay|haz\\u0131r|hazir/i.test(status)' in app
    assert "serviceBoardStageQuickFilters" in audit
    assert 'aria-label="${label} men\u00fc">...</button>' not in app
    assert "laneHeaderButtons" in audit


def test_service_board_bulk_status_action_matches_desktop():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    native = (ROOT / "src" / "ui" / "pages" / "service_board_page.py").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'data-service-board-bulk' in app
    assert 'function openServiceBoardBulkDialog()' in app
    assert 'allServices().slice(0,300).filter' in app
    assert 'name="service_id"' in app
    assert 'data-service-bulk-select="all"' in app
    assert 'data-service-bulk-select="none"' in app
    assert 'self.db.update_status(tno, new_status)' in native
    assert "serviceBoardBulkWorkflow" in audit


def test_service_board_archive_action_opens_job_tracking_route():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    native = (ROOT / "src" / "ui" / "pages" / "service_board_page.py").read_text(encoding="utf-8")
    assert "PageIds.JOB_TRACKING" in native
    assert 'data-page="job-reports">T\\u00fcm \\u0130\\u015flemler / Ar\\u015fiv</button>' in app
    assert '"job-reports":201' in app


def test_offscreen_mobile_audit_covers_service_board_card_actions():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "serviceBoardMobileActions" in audit
    assert "serviceBoardMobileActions.viewInside" in audit
    assert "serviceBoardMobileActions.technicianInside" in audit
    assert "serviceBoardMobileActions.technicianFormContainsRecord" in audit


def test_dashboard_service_delete_audit_covers_failure_retry():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "dashboardServiceDeleteWorkflow.failureRetained" in audit
    assert "QA dashboard service delete unavailable" in audit
    assert "dashboardServiceDeleteWorkflow.attempts !== 2" in audit
