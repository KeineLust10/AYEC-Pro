from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_pc_builder_is_loaded_after_shell_and_has_desktop_component_catalog():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")

    assert index.index('src="app.js?') < index.index('src="pc-builder-reference.js?')
    assert '["Anakart", "Anakart"' in script
    assert '["RAM (Bellek)", "RAM"' in script
    assert 'data-pc-preset="gaming"' in script
    assert 'data-pc-action="add-component"' in script


def test_pc_builder_preserves_desktop_pricing_calculation_and_existing_tenant_routes():
    script = (WEB / "pc-builder-reference.js").read_text(encoding="utf-8")

    assert "cost * pcMargin / 100" in script
    assert "vatBase * pcVat / 100" in script
    assert 'apiFetch("/api/desktop/table/parts?limit=1000")' in script
    assert 'apiFetch("/api/desktop/table/customers?limit=1000")' in script
    assert '$("#pcComponents") || $(".pc-builder-page") || $("#content")' in script
    assert 'apiFetch("/api/desktop/table/customer_notes"' in script
    assert 'apiFetch("/api/desktop/pc-builder/deduct-stock"' in script
    assert 'items: rows.map((row) => ({ part_id: row.part_id, quantity: row.qty }))' in script
    assert 'apiFetch("/api/desktop/table/accounting"' in script
    assert 'data-pc-action="pdf"' in script
