from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_stock_location_page_is_exposed_in_navigation_and_routes():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert r'id:"stock-locations",label:"Depo ve Ara\u00e7 Stoklar\u0131"' in app
    assert '"stock-locations":renderStockLocations' in app
    assert '"stock-locations"' in app[app.index("const sectorPages"):app.index("const titles")]
    assert 'data-location-tab="history"' in app
    assert 'id="stockLocationSearch"' in app
    assert 'id="stockLocationFilter"' in app
    assert 'ayecCreateStockLocationDialog()' in app
    assert 'ayecTransferStockDialog()' in app


def test_stock_location_transfer_uses_tenant_api_and_existing_core_transfer():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert '"/api/desktop/stock/location-management"' in app
    assert 'path == "/api/desktop/stock/location-management"' in backend
    assert 'Database(\n                        db_name=str(active_db_path()), init_mode="connection_only"' in backend
    assert 'location_db.transfer_stock(' in backend
    assert 'location_db.create_stock_location(' in backend


def test_stock_location_state_supplies_item_balances_and_transfer_history():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert 'source.stock_location_balances||[]' in app
    assert 'source.stock_transfer_history||[]' in app
    assert '"stock_location_balances": stock_location_balances' in backend
    assert '"stock_transfer_history": stock_transfer_history' in backend
    assert 'b.reserved_quantity,b.min_quantity' in backend


def test_stock_location_page_uses_responsive_compact_tables_and_live_export():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'data-location-export' in app
    assert 'download("depo-arac-stok.csv",csv(rows))' in app
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in styles
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in styles
    assert "@media(max-width:600px)" in styles
    assert ".stock-location-web-table table{min-width:840px}" in styles


def test_stock_location_reference_has_all_five_work_areas_and_count_action():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    for tab in ("stock", "requests", "counts", "kits", "history"):
        assert f'data-location-tab="{tab}"' in app
    assert 'data-location-count' in app
    assert 'action:"save-count"' in app
    assert 'action == "save-count"' in backend
    assert 'location_db.save_stock_count(' in backend
    assert 'source.stock_counts||[]' in app
    assert 'source.stock_kits||[]' in app
    assert 'data-location-kit' in app
    assert 'action:"save-kit"' in app
    assert 'action == "save-kit"' in backend
    assert 'location_db.save_stock_kit(' in backend


def test_stock_count_endpoint_validates_tenant_inventory_and_bounds():
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    route = backend[backend.index('if path == "/api/desktop/stock/location-management"'):]

    assert 'user = self.current_user()' in backend
    assert 'if not self.same_origin()' in backend
    assert 'active_db_path()' in route
    assert 'len(lines) > 1000' in route
    assert 'location_db.save_stock_count(' in route


def test_stock_transfer_form_supports_multiple_items_and_reverse_direction_returns():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'Array.from({length:5}' in app
    assert 'name="part_${index}"' in app
    assert 'name="quantity_${index}"' in app
    assert 'Iade icin kaynak ve hedef konumlari ters secin' in app
    assert 'lines:transferLines' in app
