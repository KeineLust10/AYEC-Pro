from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_stock_desktop_metrics_and_inventory_rows_match_reference_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="stock"] .stock-reference-metrics .metric' in styles
    assert 'body[data-page="stock"] .stock-reference-table td' in styles
    assert "height: 82px;" in styles
    assert "padding: 6px 8px;" in styles


def test_stock_page_matches_desktop_paging_and_inventory_summary():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    navigation = (WEB / "stock-summary-navigation.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")

    assert "const ayecStockPageSize=50" in app
    assert 'data-stock-page="-1"' in app
    assert 'data-stock-page="1"' in app
    assert 'data-stock-refresh' in app
    assert 'stock-active-count' in app
    assert 'Bilgisayar Bile\\u015fenleri' in app
    assert 'stock-reference-summary' in app
    assert 'Son Fiziksel Depo Say' in app
    assert 'data-page="${esc(page)}"' in navigation
    assert 'renderStock = function ()' in navigation
    assert '["stock-locations", "Son Fiziksel Depo Say\\u0131m\\u0131"' in navigation
    assert '["loaners", "\\u015eantiye / Servis Konsinye' in navigation
    assert '["income", "Muhasebe Entegrasyonu"' in navigation
    assert 'data-stock-transfer-tab>Depo Transferleri</button>' in navigation
    assert 'stock-summary-navigation.js?v=20261027-stock-transfer-tab-parity-1' in index
    assert 'body[data-page="stock"] .stock-reference-table-wrap { max-height: 500px;' in styles
    assert 'height: 49px; padding: 12px 8px;' in styles
    assert 'body[data-page="stock"] .stock-reference-summary { display: grid; grid-template-columns: repeat(3,minmax(0,1fr));' in styles
    assert 'body[data-page="stock"] .stock-reference-summary-action:focus-visible' in styles
    assert 'body[data-page="stock"] .stock-reference-table-wrap { height: 52vh; max-height: 52vh; overflow: auto !important; }' in styles
    assert 'body[data-page="stock"] #stockTable td { display: block; height: auto; min-width: 0; overflow-wrap: anywhere; white-space: normal; }' in styles


def test_stock_mobile_cards_keep_all_inventory_fields_visible():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="stock"] #stockTable td:nth-child(1),' in styles
    assert 'body[data-page="stock"] #stockTable td:nth-child(3),' in styles
    assert 'body[data-page="stock"] #stockTable td:nth-child(5){display:block}' in styles
    assert 'body[data-page="stock"] #stockTable td:nth-child(12){grid-column:1/-1;grid-row:7;' in styles
