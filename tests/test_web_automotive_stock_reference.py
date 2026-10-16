from pathlib import Path


def test_automotive_stock_view_matches_desktop_columns_tabs_and_feature_flag():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    script = (root / "automotive-stock-reference.js").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    css = (root / "automotive-stock-reference.css").read_text(encoding="utf-8")
    index = (root / "index.html").read_text(encoding="utf-8")

    for field in ("item.barcode", "item.brand", "item.oem_code", "item.equivalent_code", "item.compatible_models", "item.shelf_number"):
        assert field in script
    assert 'data-page="stock-locations">Depo Transferleri' in script
    assert r'data-page="movements">Par\u00e7a Hareketleri' in script
    assert "feature_usage_guides_active" in script
    assert 'data-automotive-stock-guide' in script
    assert 'page === "automotive-stock" ? automotiveStockTable' in script
    assert '[item.code,item.name,item.barcode,item.oem_code,item.equivalent_code,item.compatible_models]' in app
    assert 'priceVisible ? esc(value) : "***"' in script
    assert 'data-automotive-price-all' in script
    assert 'revealedPurchasePriceIds' in script
    assert "automotive-stock-reference.js" in index
    assert "automotive-stock-reference.css" in index
    assert ".automotive-stock-table{min-width:0}" in css


def test_automotive_stock_usage_guide_covers_desktop_shortcuts():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    script = (root / "automotive-stock-reference.js").read_text(encoding="utf-8")

    assert "OEM/muadil" in script
    assert r"Par\u00e7a Hareketleri Sekmesi" in script
    assert r"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma" in script
