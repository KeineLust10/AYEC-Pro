from pathlib import Path
import sqlite3

import src.database as database_module
from src.db.mixins.stock_location_mixin import StockLocationMixin
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_stock_location_context_menu_matches_desktop_labels_and_actions():
    desktop = (ROOT / "src/ui/pages/stock_locations_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = desktop.index("def _show_inventory_context_menu(self, pos):")
    end = desktop.index("def _build_transfer_tab", start)
    desktop_menu = desktop[start:end]
    start = app.index("const ayecStockLocationShowContextBase = showContext;")
    end = app.index("function contextAction(kind,id,action,row)", start)
    web_menu = app[start:end]

    assert 'menu.addAction("\u270f\ufe0f Stok Kart\u0131n\u0131 D\u00fczenle (\u00c7ift T\u0131k)")' in desktop_menu
    assert 'menu.addAction("\U0001f6e0\ufe0f M\u00fc\u015fteriye / Servis Cihaz\u0131na Tak (Stoktan D\u00fc\u015f)")' in desktop_menu
    assert 'menu.addAction("\U0001f504 Ba\u015fka Depoya / Araca Transfer Et")' in desktop_menu
    assert r'"\u270f\ufe0f Stok Kart\u0131n\u0131 D\u00fczenle (\u00c7ift T\u0131k)"' in web_menu
    assert r'"\u{1f6e0}\ufe0f M\u00fc\u015fteriye / Servis Cihaz\u0131na Tak (Stoktan D\u00fc\u015f)"' in web_menu
    assert r'"\u{1f504} Ba\u015fka Depoya / Araca Transfer Et"' in web_menu
    assert 'contextAction(kind, id, button.dataset.contextAction, row)' in web_menu


def test_stock_location_page_is_exposed_in_navigation_and_routes():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert r'id:"stock-locations",label:"Stok Lokasyonlar\u0131"' in app
    assert '"stock-locations":renderStockLocations' in app
    assert '"stock-locations"' in app[app.index("const sectorPages"):app.index("const titles")]
    assert 'data-location-tab="history"' in app
    assert 'id="stockLocationSearch"' in app
    assert 'id="stockLocationFilter"' in app
    assert 'ayecCreateStockLocationDialog()' in app
    assert 'ayecTransferStockDialog()' in app
    assert '<th>Birim</th>' in app
    assert 'H\\u0131zl\\u0131 \\u0130\\u015flemler' in app
    assert 'data-stock-row-action="transfer"' in app
    assert 'data-stock-row-action="use"' in app
    assert 'data-stock-row-action="edit"' in app
    assert 'stockLocationUsePartDialog(part,row?.dataset.locationId)' in app
    assert 'const ayecStockLocationPageSize=5;' in app


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


def test_stock_count_dialog_supports_location_selection_live_differences_and_confirmation():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    dialog = app[app.index("function ayecStockCountDialog"):app.index("function ayecStockKitDialog")]

    assert 'id="stockCountLocation" name="location_id"' in dialog
    assert 'data-stock-count-refresh' in dialog
    assert 'data-count-difference' in dialog
    assert 'Math.abs(Number(item.quantity||0))>0.000001' in dialog
    assert 'data-stock-count-confirm' in dialog
    assert 'if(!confirmation.checked)' in dialog
    assert 'check.checked=false' in dialog
    assert 'counted_quantity:values[`count_${item.part_id}`]' in dialog


def test_stock_transfer_form_supports_multiple_items_and_reverse_direction_returns():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'data-transfer-add-kit' in app
    assert 'data-transfer-add-line' in app
    assert 'data-transfer-swap' in app
    assert 'index===1?"selected":""' in app
    assert 'kit.lines' in app
    assert 'stockLocationBalances||[]).filter(item=>item.location_id===String(locationId)' in app
    assert 'data-transfer-remove' in app


def test_stock_card_editor_preserves_desktop_detail_fields_for_both_sectors():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    automotive = (WEB / "automotive-parity.js").read_text(encoding="utf-8")
    editor = app[app.index('productForm=function(product={}){const categories=sectorStockCategories();'):]
    save = automotive[automotive.index('saveProduct=async function(formData,existing)'):]

    assert 'name="brand"' in editor
    assert 'name="description"' in editor
    assert 'name="unit"' in editor
    assert 'name="shelf_number"' in editor
    assert 'name="compatible_models"' in editor
    assert 'name="oem_code"' in automotive
    assert 'name="equivalent_code"' in automotive
    assert 'compatible_models:values.compatible_models||""' in save
    assert 'shelf_number:values.shelf_number||""' in save
    assert 'unit:values.unit||"Adet"' in save
    assert 'Iade icin kaynak ve hedef konumlari ters secin' in app
    assert 'lines:transferLines' in app


def test_stock_transfer_bootstrap_includes_stock_units_and_kit_lines():
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert "COALESCE(p.unit,'Adet') AS unit" in backend
    assert "SELECT line.kit_id,line.part_id,part.name" in backend
    assert 'kit["lines"] = kit_lines_by_id.get(int(kit["id"]), [])' in backend


def test_stock_transfer_bootstrap_returns_saved_kit_composition(monkeypatch, tmp_path):
    database_path = tmp_path / "stock-kit-bootstrap.db"
    db = database_module.Database(str(database_path))
    part_id = db.add_part("Kit disk", "General", 4, 80, min_stock=1)
    db.ensure_stock_location_schema()
    db.save_stock_kit("Install kit", [{"part_id": part_id, "quantity": 2}])
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    payload = web_main.desktop_bootstrap()
    kit = next(item for item in payload["stock_kits"] if item["name"] == "Install kit")

    assert kit["lines"] == [
        {"part_id": part_id, "name": "Kit disk", "unit": "Adet", "quantity": 2.0}
    ]
    web_main.clear_tenant_context()


def test_stock_kit_builder_matches_desktop_add_merge_and_remove_flow():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    builder = app[app.index("function ayecStockKitDialog"):app.index("function ayecTransferStockDialog")]

    assert 'data-stock-kit-add' in builder
    assert 'data-stock-kit-remove' in builder
    assert 'kitLines.find(line=>String(line.part_id)===String(product.id))' in builder
    assert 'lines:kitLines' in builder
    assert 'Array.from({length:5}' not in builder


def test_stock_location_creation_preserves_desktop_location_types():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    form = app[app.index("function ayecCreateStockLocationDialog"):app.index("function ayecStockCountDialog")]
    route = backend[backend.index('if path == "/api/desktop/stock/location-management"'):]

    assert '<option value="personnel">Personel Stogu</option>' in form
    assert '<option value="project">Proje Stogu</option>' in form
    assert '"warehouse", "vehicle", "personnel", "project", "site"' in route


def test_stock_location_endpoint_accepts_desktop_location_types(monkeypatch, tmp_path):
    class FakeLocationDatabase(StockLocationMixin):
        created = []

        def __init__(self, db_name, init_mode):
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row
            self.conn.execute(
                "CREATE TABLE parts (id INTEGER PRIMARY KEY, stock REAL, is_deleted INTEGER)"
            )

        def create_stock_location(self, name, location_type, vehicle_plate):
            location_id = super().create_stock_location(name, location_type, vehicle_plate)
            self.created.append((name, location_type, vehicle_plate))
            return location_id

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeLocationDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/stock/location-management"
    handler.headers = {"Content-Length": "128"}
    handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
    handler.same_origin = lambda: True
    handler.read_json = lambda: {
        "action": "create-location",
        "name": "People stock",
        "location_type": "personnel",
        "vehicle_plate": "",
    }
    sent = []
    handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))

    handler.do_POST()

    assert sent[-1][0] == 200
    assert sent[-1][1]["ok"] is True
    assert FakeLocationDatabase.created[-1] == ("People stock", "personnel", None)


def test_use_part_note_is_present_in_web_form_and_sent_through_api():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    dialog = app[app.index("function stockLocationUsePartDialog"):app.index("function ayecCreateStockLocationDialog")]
    route = backend[backend.index('if path == "/api/desktop/stock/location-management"'):]

    assert 'name="note" maxlength="500"' in dialog
    assert 'note:String(values.note||"").trim()' in dialog
    assert 'note = str(payload.get("note") or "").strip()[:500]' in route
    assert 'commit=True, location_id=location_id, note=note' in route


def test_use_part_endpoint_passes_operation_note_to_database(monkeypatch, tmp_path):
    class FakeLocationDatabase(StockLocationMixin):
        used_parts = []

        def __init__(self, db_name, init_mode):
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(":memory:")
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self.conn.executescript(
                "CREATE TABLE parts (id INTEGER PRIMARY KEY, stock REAL, is_deleted INTEGER);"
                "CREATE TABLE devices (tracking_no TEXT, is_archived INTEGER, is_deleted INTEGER);"
                "INSERT INTO parts VALUES (9, 5, 0);"
                "INSERT INTO devices VALUES ('SRV-1', 0, 0);"
            )

        def use_part(self, **values):
            self.used_parts.append(values)
            return True

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeLocationDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/stock/location-management"
    handler.headers = {"Content-Length": "128"}
    handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
    handler.same_origin = lambda: True
    handler.read_json = lambda: {
        "action": "use-part",
        "part_id": 9,
        "location_id": 1,
        "tracking_no": "SRV-1",
        "quantity": 1,
        "note": "Replace damaged cable",
    }
    sent = []
    handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))

    handler.do_POST()

    assert sent[-1][0] == 200
    assert FakeLocationDatabase.used_parts[-1]["note"] == "Replace damaged cable"
