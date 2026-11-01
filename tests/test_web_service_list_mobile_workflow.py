from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_offscreen_mobile_audit_covers_service_list_technician_handoff():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "serviceListTechnicianHandoffWorkflow" in audit
    assert "serviceListTechnicianHandoffWorkflow.actionVisible" in audit
    assert "serviceListTechnicianHandoffWorkflow.dialogOpen" in audit
    assert "serviceListTechnicianHandoffWorkflow.faultShown" in audit
    assert "serviceListPaginationWorkflow" in audit
    assert "serviceListPaginationMobile" in audit

def test_offscreen_audit_covers_service_list_cargo_receipt_print():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "serviceListCargoReceiptWorkflow" in audit
    assert "receiverShown" in audit
    assert "serialShown" in audit
    assert "popup.printed" in audit

def test_service_list_refresh_resets_native_row_selection_only_after_success():
    source = (ROOT / "Web_Arayuzu" / "web" / "service-list-reference.js").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'await hydrateDesktop(false); ayecServiceListState.selected.clear(); ayecServiceListState.currentId = null; render();' in source
    assert "serviceListRefreshSelectionWorkflow.successCleared" in audit
    assert "serviceListRefreshSelectionWorkflow.failureRetained" in audit
    assert "serviceListRefreshSelectionWorkflow.currentRetained" in audit

def test_service_list_defaults_to_all_dates_instead_of_hiding_older_repairs():
    source = (ROOT / "Web_Arayuzu" / "web" / "service-list-reference.js").read_text(encoding="utf-8")
    html = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")

    assert 'tab: "all", query: "", status: "all", date: "all", priority: "all"' in source
    assert 'option value="all"' in source
    assert "service-list-reference.js?v=20261029-service-list-show-all-default-1" in html

\n