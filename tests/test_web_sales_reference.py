from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_offers_list_matches_desktop_summary_and_column_order():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")

    assert '["offer_no","TEKLIF NO"]' in app
    assert '["created_at","TARIH"]' in app
    assert '["company_name","FIRMA"]' in app
    assert '["pdf_path","NOT / EVRAK"]' in app
    assert 'function ayecOfferStatusLabel' in app
    assert 'class="mini offer-open"' in app
    assert 'body[data-page="offers"] .offers-reference-metrics{grid-template-columns:repeat(5,minmax(0,1fr))' in styles
    assert 'grid-template-columns:minmax(0,2fr) minmax(420px,1fr)' in styles
    assert 'min-width:900px;table-layout:fixed' in styles
    assert 'white-space:normal!important;word-break:normal' in styles
    assert 'min-height:90px;height:auto' in styles
    assert 'width:170px;white-space:nowrap' in styles


def test_offer_reports_use_month_customer_and_staff_aggregates():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")

    assert "function renderOfferReports()" in app
    assert 'new Map()' in app[app.index("function renderOfferReports()"):]
    assert "Son 12 Ay Teklif Trendi" in app
    assert "En Cok Teklif Verilen" in app
    assert "En Cok Teklif Haz" in app
    assert "offer-report-total" in app
    assert 'grid-template-columns:repeat(4,minmax(0,1fr))' in styles
    assert 'body[data-page="offer-reports"] .offer-report-layout' in styles
    assert 'item.customers].slice(0,3)' in app
    assert 'table-layout:fixed' in styles
    assert '@media(max-width:430px){body[data-page="offer-reports"] .offer-report-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}' in styles
    assert 'body[data-page="offer-reports"] .offer-report-layout>.offer-report-panel:first-child table{min-width:640px}' in styles


def test_quote_builder_matches_reference_sections_and_responsive_cards():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'class="sales-reference-layout"' in app
    assert 'class="sales-reference-customer"' in app
    assert 'data-sales-category="${esc(id)}"' in app
    assert 'class="sales-cart-line"' in app
    assert 'data-sales-discount="${value}"' in app
    assert 'data-sales-currency="${code}"' in app
    assert "discount_percent:salesDiscountPercent" in app
    assert "data-sales-qty" in app
    assert "data-sales-focus-barcode" in app
    assert "@media(max-width:760px){body[data-page=\"sales\"] .sales-reference-layout" in styles
    assert "@media(max-width:430px){body[data-page=\"sales\"] .sales-reference-customer" in styles


def test_quote_builder_controls_have_bound_interactions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'event.target.closest("[data-sales-category]")' in app
    assert 'event.target.closest("[data-sales-discount]")' in app
    assert 'event.target.closest("[data-sales-currency]")' in app
    assert 'event.key==="F2"' in app
    assert 'event.key==="F5"' in app
    assert 'event.key==="F8"' in app
    assert 'event.key==="Enter"' in app


def test_offer_reference_list_uses_desktop_table_viewport():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="offers"] .offers-reference-list #genericHost .table-wrap { height: 310px; max-height: 310px; overflow: auto; }' in styles
    assert 'body[data-page="offers"] .offers-reference-list #genericHost .table-wrap { height: 360px; max-height: 360px; }' in styles
