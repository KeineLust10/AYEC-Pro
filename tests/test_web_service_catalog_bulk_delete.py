from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
PARITY = ROOT / "Web_Arayuzu" / "web" / "service-catalog-context-parity.js"
INDEX = ROOT / "Web_Arayuzu" / "web" / "index.html"
ROUTE_AUDIT = ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs"


def test_service_catalog_bulk_delete_tracks_ids_and_reports_partial_failures():
    source = PARITY.read_text(encoding="utf-8")

    assert 'const failed = []' in source
    assert 'failed.push(row)' in source
    assert 'failed.forEach(row => window.laborSelectedIds.add(String(row.id)))' in source
    assert 'window.laborMultiSelect = failed.length > 0' in source
    assert 'hizmet silindi, ${failed.length} kay' in source
    assert 'service-catalog-context-parity.js?v=20261025-bulk-delete-partial-retry-1' in INDEX.read_text(encoding="utf-8")


def test_service_catalog_offscreen_audit_covers_cancel_partial_failure_and_retry():
    source = ROUTE_AUDIT.read_text(encoding="utf-8")

    assert "async function auditServiceDefinitionMultiDelete(evaluate)" in source
    assert "cancelNoWrite" in source
    assert "partialResult" in source
    assert "retryOpened" in source
    assert "Service definition bulk-delete workflow failed" in source
