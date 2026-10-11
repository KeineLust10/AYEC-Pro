from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_360_tabs_and_summary_match_reference_on_desktop_and_mobile():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert 'class="c360-stats"' in app
    assert 'data-c360-tab="cari"' in app
    assert 'data-c360-tab="ledger"' in app
    assert 'data-c360-tab="sales"' in app
    assert 'data-c360-tab="offers"' in app
    assert "dataset.c360Panel===tab.dataset.c360Tab" in app
    assert 'dialog.c360-dialog .c360-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr))' in styles
    assert '@media(max-width:760px){dialog.c360-dialog .c360-stats{grid-template-columns:repeat(2,minmax(0,1fr))' in styles
    assert 'dialog.c360-dialog .c360-panel td{font-size:12px}' in styles
