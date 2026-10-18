from pathlib import Path


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
