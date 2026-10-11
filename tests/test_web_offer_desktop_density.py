from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


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
