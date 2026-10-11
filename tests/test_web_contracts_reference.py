from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_contracts_reference_uses_desktop_controls_and_columns():
    source = (WEB / "contracts-reference.js").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'window.renderContractsReference = function' in source
    for control in (
        "data-contract-plan",
        "data-contract-export",
        "data-contract-delete",
        "data-generic-add",
        "data-contract-status",
        "contractType",
        "contractSla",
        "data-contract-page",
    ):
        assert control in source
    for column in ("M\\u00dc\\u015eTER\\u0130", "BA\\u015eLIK", "BA\\u015eLANGI\\u00c7", "B\\u0130T\\u0130\\u015e", "KALAN S\\u00dcRE"):
        assert column in source
    assert '"contracts-reference.js?v=20261008-4"' in page


def test_contracts_reference_layout_is_full_width_and_mobile_adaptive():
    styles = (WEB / "contracts-reference.css").read_text(encoding="utf-8")

    assert ".contracts-reference-table{width:100%" in styles
    assert ".contracts-reference-table{min-width:0" in styles
    assert "@media(max-width:760px)" in styles
    assert "grid-template-columns:minmax(0,1fr)" in styles
