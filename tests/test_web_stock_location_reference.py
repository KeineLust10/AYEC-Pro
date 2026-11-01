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
    assert web_menu.index('menu.classList.add("open")') < web_menu.index('innerHeight - menu.offsetHeight - 8')
    assert 'items.length * 42' not in web_menu


def test_use_part_dialog_uses_all_active_devices_and_desktop_unit_precision():
    desktop = (ROOT / "src/ui/pages/stock_locations_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function stockLocationUsePartDialog")
    end = app.index("function ayecCreateStockLocationDialog", start)
    dialog = app[start:end]

    assert 'db.serviceDevices=(source.devices||[]).filter(item=>!Number(item.is_archived||0)&&!Number(item.is_deleted||0)' in app
    assert 'SELECT tracking_no, customer_name, device_brand, device_model, status' in desktop
    assert 'WHERE COALESCE(is_archived, 0) = 0 AND COALESCE(is_deleted, 0) = 0' in desktop
    assert 'Array.isArray(db.serviceDevices)&&db.serviceDevices.length?db.serviceDevices' in dialog
    assert 'const quantityStep=["Metre","Kg","Lt"].includes(balance.unit)?"0.001":"1"' in dialog
    assert 'min="${quantityStep}" max="${available}" step="${quantityStep}"' in dialog
    assert 'self.spn_qty.setDecimals(3 if unit in ("Metre", "Kg", "Lt") else 0)' in desktop


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


def test_stock_location_dynamic_count_and_kit_actions_use_delegated_click_binding():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index('if(page==="stock-locations"){', app.index("function bindPage"))
    end = app.index('const ss=$("#stockSearch")', start)
    binding = app[start:end]

    assert "stockLocationDialogsDelegated" in binding
    assert 'target?.closest("[data-location-count]")' in binding
    assert 'target?.closest("[data-location-kit]")' in binding
    assert 'addEventListener("click",ayecStockCountDialog)' not in binding
    assert 'addEventListener("click",ayecStockKitDialog)' not in binding


def test_mobile_stock_location_use_part_workflow_is_verified_offscreen():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "mobileStockLocationUseWorkflow" in audit
    assert 'action?.scrollIntoView({block:"center",inline:"end"})' in audit
    assert "Mobile stock location use workflow failed" in audit
    assert 'stockLocationUseWorkflow = mobileStockLocationUseWorkflow' in audit


def test_fractional_stock_location_use_preserves_desktop_precision_offscreen():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'precisionQuantity?.min==="0.001"&&precisionQuantity?.step==="0.001"' in audit
    assert 'precisionCall?.payload?.quantity !== 0.125' in audit
    assert "QA fractional stock use" in audit


def test_stock_location_transfer_uses_tenant_api_and_existing_core_transfer():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "stock_locations_page.py").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert '"/api/desktop/stock/location-management"' in app
    assert 'path == "/api/desktop/stock/location-management"' in backend
    assert 'Database(\n                        db_name=str(active_db_path()), init_mode="connection_only"' in backend
    assert 'location_db.transfer_stock(' in backend
    assert 'location_db.create_stock_location(' in backend
    assert 'self.transfer_quantity = self._count_spinbox()' in desktop
    assert 'id="transferQuantity" type="number" min="1" step="1" inputmode="numeric"' in app
    assert "transferIntegerStep" in audit


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
    desktop = (ROOT / "src" / "ui" / "pages" / "stock_locations_page.py").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    for tab in ("stock", "requests", "counts", "kits", "history"):
        assert f'data-location-tab="{tab}"' in app
    assert 'data-location-count' in app
    assert 'action:"save-count"' in app
    assert 'action == "save-count"' in backend
    assert 'location_db.save_stock_count(' in backend
    assert 'CountStepper(expected, 3 if unit in ("Metre", "Kg", "Lt") else 0)' in desktop
    assert 'step="${["Metre","Kg","Lt"].includes(item.unit)?"0.001":"1"}"' in app
    assert 'counted.is_integer()' in backend
    assert 'counted != round(counted, 3)' in backend
    assert "countPrecisionStep" in audit
    assert 'source.stock_counts||[]' in app
    assert 'source.stock_kits||[]' in app
    assert 'data-location-kit' in app
    assert 'action:"save-kit"' in app
    assert 'action == "save-kit"' in backend
    assert 'location_db.save_stock_kit(' in backend


def test_stock_location_footer_cards_match_desktop_reference_copy():
    desktop = (ROOT / "src/ui/pages/stock_locations_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop_footer = desktop[desktop.index("def _build_reference_footer(self):"):desktop.index("for title_text, body_text, accent in cards", desktop.index("def _build_reference_footer(self):"))]
    start = app.index('<section class="stock-location-web-insights">')
    web_footer = app[start:app.index("</section>", start)]

    for title in ("Mobil Stok Guvence Protokolu", "Ikmal Talebi: TR-2024-884", "El Terminali ve Kamera Tarama"):
        assert title in desktop_footer
        assert f"<h3>{title}</h3>" in web_footer
    for detail in (
        "Arac bagaj kapak sensoru ve RFID donanim kasasi aktif.",
        "Barkod okuyucu hazir. Klavye kisayolu: F2 ile aninda seri numarasi okutun.",
    ):
        assert detail in desktop_footer
        assert detail in web_footer
    assert "34 AY 001" in desktop_footer and "34 AY 001" in web_footer


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


def test_stock_transfer_bootstrap_includes_all_active_kits(monkeypatch, tmp_path):
    database_path = tmp_path / "stock-kit-pagination.db"
    db = database_module.Database(str(database_path))
    part_id = db.add_part("Kit part", "General", 1, 1, min_stock=0)
    for index in range(251):
        db.save_stock_kit(f"Kit-{index:03d}", [{"part_id": part_id, "quantity": 1}])
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    payload = web_main.desktop_bootstrap()
    web_main.clear_tenant_context()

    assert len(payload["stock_kits"]) == 251


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

        def get_stock_locations(self):
            return [{"id": 1}]

        def get_location_inventory(self, location_id):
            assert location_id == 1
            return [{"part_id": 9, "quantity": 5, "reserved_quantity": 2, "unit": "Adet"}]

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


def test_use_part_endpoint_enforces_available_balance_and_desktop_unit_precision(monkeypatch, tmp_path):
    class FakeLocationDatabase(StockLocationMixin):
        scenario = {}
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

        def get_stock_locations(self):
            return [{"id": 1}]

        def get_location_inventory(self, location_id):
            assert location_id == 1
            return [{"part_id": 9, **self.scenario}]

        def use_part(self, **values):
            self.used_parts.append(values)
            return True

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeLocationDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    def dispatch(unit, quantity, reserved_quantity=0):
        FakeLocationDatabase.scenario = {
            "quantity": 5,
            "reserved_quantity": reserved_quantity,
            "unit": unit,
        }
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
            "quantity": quantity,
            "note": "precision check",
        }
        sent = []
        handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))
        handler.do_POST()
        return sent[-1]

    FakeLocationDatabase.used_parts.clear()
    assert dispatch("Adet", 3.1, reserved_quantity=2)[0] == 409
    assert dispatch("Adet", 0.5)[0] == 400
    assert dispatch("Kg", 0.1255)[0] == 400
    status, payload = dispatch("Kg", 0.125, reserved_quantity=1)

    assert status == 200
    assert payload["ok"] is True
    assert FakeLocationDatabase.used_parts[-1]["quantity"] == 0.125
    assert len(FakeLocationDatabase.used_parts) == 1


def test_stock_use_api_applies_reserved_and_fractional_rules_to_tenant_database(monkeypatch, tmp_path):
    db_path = tmp_path / "tenant-stock.db"
    seed = database_module.Database(str(db_path))
    customer_id = seed.add_customer({"name": "Stock Use API Customer"})
    seed.add_device(
        {
            "tracking_no": "STOCK-USE-API-1",
            "customer_id": customer_id,
            "customer_name": "Stock Use API Customer",
            "device_type": "Computer",
            "device_brand": "Test",
            "device_model": "Stock Use Device",
            "status": "Tamirde",
        }
    )
    discrete_part = seed.add_part("Discrete API Part", "Computer", 5, 10, code="API-DISC-1")
    fractional_part = seed.add_part("Fractional API Part", "Computer", 5, 10, code="API-FRAC-1")
    seed.ensure_stock_location_schema()
    main_location_id = next(
        item["id"] for item in seed.get_stock_locations()
        if item["location_type"] == "main"
    )
    seed.cursor.execute("UPDATE parts SET unit='Kg' WHERE id=?", (fractional_part,))
    seed.cursor.execute(
        "UPDATE stock_location_balances SET quantity=5,reserved_quantity=2 "
        "WHERE part_id=? AND location_id=?",
        (discrete_part, main_location_id),
    )
    seed.cursor.execute(
        "UPDATE stock_location_balances SET quantity=5,reserved_quantity=1 "
        "WHERE part_id=? AND location_id=?",
        (fractional_part, main_location_id),
    )
    seed.conn.commit()
    seed.close()
    other_path = tmp_path / "other-tenant-stock.db"
    other = database_module.Database(str(other_path))
    other_customer_id = other.add_customer({"name": "Stock Use API Customer"})
    other.add_device(
        {
            "tracking_no": "STOCK-USE-API-1",
            "customer_id": other_customer_id,
            "customer_name": "Stock Use API Customer",
            "device_type": "Computer",
            "device_brand": "Test",
            "device_model": "Stock Use Device",
            "status": "Tamirde",
        }
    )
    other_discrete_part = other.add_part("Discrete API Part", "Computer", 5, 10, code="API-DISC-1")
    other_fractional_part = other.add_part("Fractional API Part", "Computer", 5, 10, code="API-FRAC-1")
    other.ensure_stock_location_schema()
    other_location_id = next(
        item["id"] for item in other.get_stock_locations()
        if item["location_type"] == "main"
    )
    other.cursor.execute("UPDATE parts SET unit='Kg' WHERE id=?", (other_fractional_part,))
    other.cursor.execute(
        "UPDATE stock_location_balances SET quantity=5,reserved_quantity=2 "
        "WHERE part_id=? AND location_id=?",
        (other_discrete_part, other_location_id),
    )
    other.cursor.execute(
        "UPDATE stock_location_balances SET quantity=5,reserved_quantity=1 "
        "WHERE part_id=? AND location_id=?",
        (other_fractional_part, other_location_id),
    )
    other.conn.commit()
    other.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: db_path)

    def dispatch(part_id, quantity):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = "/api/desktop/stock/location-management"
        handler.headers = {"Content-Length": "128"}
        handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
        handler.same_origin = lambda: True
        handler.read_json = lambda: {
            "action": "use-part",
            "part_id": part_id,
            "location_id": main_location_id,
            "tracking_no": "STOCK-USE-API-1",
            "quantity": quantity,
            "note": "API inventory validation",
        }
        sent = []
        handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))
        handler.do_POST()
        return sent[-1]

    assert dispatch(discrete_part, 3.1)[0] == 409
    assert dispatch(discrete_part, 0.5)[0] == 400
    assert dispatch(fractional_part, 0.1255)[0] == 400
    assert dispatch(discrete_part, 3)[0] == 200
    assert dispatch(fractional_part, 0.125)[0] == 200

    check = database_module.Database(str(db_path), init_mode="connection_only")
    try:
        stock = {
            int(part_id): float(quantity)
            for part_id, quantity in check.cursor.execute(
                "SELECT id,stock FROM parts WHERE id IN (?,?)",
                (discrete_part, fractional_part),
            ).fetchall()
        }
        assert stock == {discrete_part: 2, fractional_part: 4.875}
    finally:
        check.close()
    other_check = database_module.Database(str(other_path), init_mode="connection_only")
    try:
        other_stock = {
            int(part_id): float(quantity)
            for part_id, quantity in other_check.cursor.execute(
                "SELECT id,stock FROM parts WHERE id IN (?,?)",
                (other_discrete_part, other_fractional_part),
            ).fetchall()
        }
        assert other_stock == {other_discrete_part: 5, other_fractional_part: 5}
    finally:
        other_check.close()


def test_stock_count_api_enforces_desktop_unit_precision(monkeypatch, tmp_path):
    class FakeLocationDatabase(StockLocationMixin):
        units = {9: "Adet", 10: "Kg"}
        saved_counts = []

        def __init__(self, db_name, init_mode):
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(":memory:")
            self.cursor = self.conn.cursor()
            self.cursor.executescript(
                "CREATE TABLE parts (id INTEGER PRIMARY KEY, is_deleted INTEGER);"
                "INSERT INTO parts VALUES (9, 0);"
                "INSERT INTO parts VALUES (10, 0);"
            )

        def get_stock_locations(self):
            return [{"id": 1}]

        def get_location_inventory(self, location_id):
            assert location_id == 1
            return [
                {"part_id": part_id, "unit": unit}
                for part_id, unit in self.units.items()
            ]

        def save_stock_count(self, location_id, lines, note, created_by):
            self.saved_counts.append((location_id, lines, note, created_by))
            return 501

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeLocationDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    def dispatch(part_id, counted_quantity):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = "/api/desktop/stock/location-management"
        handler.headers = {"Content-Length": "128"}
        handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
        handler.same_origin = lambda: True
        handler.read_json = lambda: {
            "action": "save-count",
            "location_id": 1,
            "lines": [{"part_id": part_id, "counted_quantity": counted_quantity}],
            "note": "unit precision check",
        }
        sent = []
        handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))
        handler.do_POST()
        return sent[-1]

    FakeLocationDatabase.saved_counts.clear()
    assert dispatch(9, 2.5)[0] == 400
    assert dispatch(10, 0.1255)[0] == 400
    status, payload = dispatch(10, 0.125)

    assert status == 200
    assert payload["count_id"] == 501
    assert FakeLocationDatabase.saved_counts[-1][1][0]["counted_quantity"] == 0.125
    assert len(FakeLocationDatabase.saved_counts) == 1


def test_stock_count_api_persists_unit_valid_counts_in_tenant_database(monkeypatch, tmp_path):
    db_path = tmp_path / "count-tenant.db"
    seed = database_module.Database(str(db_path))
    discrete_part = seed.add_part("Discrete Count Part", "Computer", 5, 10, code="COUNT-DISC-1")
    fractional_part = seed.add_part("Fractional Count Part", "Computer", 5, 10, code="COUNT-FRAC-1")
    seed.ensure_stock_location_schema()
    location_id = next(
        item["id"] for item in seed.get_stock_locations()
        if item["location_type"] == "main"
    )
    seed.cursor.execute("UPDATE parts SET unit='Kg' WHERE id=?", (fractional_part,))
    seed.cursor.execute(
        "UPDATE stock_location_balances SET quantity=5 WHERE part_id=? AND location_id=?",
        (discrete_part, location_id),
    )
    seed.cursor.execute(
        "UPDATE stock_location_balances SET quantity=4 WHERE part_id=? AND location_id=?",
        (fractional_part, location_id),
    )
    assert seed.cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='appointment_plan_items'"
    ).fetchone() is None
    seed.conn.commit()
    seed.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: db_path)

    def dispatch(part_id, counted_quantity):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = "/api/desktop/stock/location-management"
        handler.headers = {"Content-Length": "128"}
        handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
        handler.same_origin = lambda: True
        handler.read_json = lambda: {
            "action": "save-count",
            "location_id": location_id,
            "lines": [{"part_id": part_id, "counted_quantity": counted_quantity}],
            "note": "tenant count precision integration",
        }
        sent = []
        handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))
        handler.do_POST()
        return sent[-1]

    assert dispatch(discrete_part, 2.5)[0] == 400
    assert dispatch(fractional_part, 0.1255)[0] == 400
    valid_discrete_count = dispatch(discrete_part, 2)
    assert valid_discrete_count[0] == 200, valid_discrete_count
    assert dispatch(fractional_part, 0.125)[0] == 200

    check = database_module.Database(str(db_path), init_mode="connection_only")
    try:
        stock = {
            int(part_id): float(quantity)
            for part_id, quantity in check.cursor.execute(
                "SELECT id,stock FROM parts WHERE id IN (?,?)",
                (discrete_part, fractional_part),
            ).fetchall()
        }
        count_rows = int(check.cursor.execute("SELECT COUNT(*) FROM stock_counts").fetchone()[0])
        plan_table = check.cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='appointment_plan_items'"
        ).fetchone()
        assert stock == {discrete_part: 2, fractional_part: 0.125}
        assert count_rows == 2
        assert plan_table is None
    finally:
        check.close()


def test_stock_kit_api_rejects_fractional_components_like_desktop(monkeypatch, tmp_path):
    class FakeLocationDatabase(StockLocationMixin):
        saved_kits = []

        def __init__(self, db_name, init_mode):
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(":memory:")
            self.cursor = self.conn.cursor()
            self.cursor.executescript(
                "CREATE TABLE parts (id INTEGER PRIMARY KEY, is_deleted INTEGER);"
                "INSERT INTO parts VALUES (9, 0);"
            )

        def save_stock_kit(self, name, lines):
            self.saved_kits.append((name, lines))
            return 501

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeLocationDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    def dispatch(quantity):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = "/api/desktop/stock/location-management"
        handler.headers = {"Content-Length": "128"}
        handler.current_user = lambda: {"id": 1, "role": "admin", "username": "tester"}
        handler.same_origin = lambda: True
        handler.read_json = lambda: {
            "action": "save-kit",
            "name": "QA Kit",
            "lines": [{"part_id": 9, "quantity": quantity}],
        }
        sent = []
        handler.send_json = lambda payload, status=200, **kwargs: sent.append((status, payload))
        handler.do_POST()
        return sent[-1]

    FakeLocationDatabase.saved_kits.clear()
    assert dispatch(1.5)[0] == 400
    status, payload = dispatch(2)

    assert status == 200
    assert payload["kit_id"] == 501
    assert FakeLocationDatabase.saved_kits[-1][1][0]["quantity"] == 2
    assert len(FakeLocationDatabase.saved_kits) == 1


def test_stock_kit_quantity_contract_matches_desktop_and_web_form():
    desktop = (ROOT / "src" / "ui" / "pages" / "stock_locations_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    assert 'self.kit_quantity = self._count_spinbox()' in desktop
    assert 'if(!product||!Number.isInteger(quantity)||quantity<=0)' in app
    assert 'if not quantity.is_integer()' in backend

def test_offscreen_stock_transfer_retry_keeps_lines_after_api_failure():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "stockLocationTransferRetryWorkflow" in audit
    assert "failureRetained" in audit
    assert "retry.firstPayload?.lines?.[0]?.quantity !== 5" in audit
    assert "retry.retryPayload?.note !== \"QA retry transfer\"" in audit


def test_stock_location_tabs_have_roving_keyboard_and_panel_semantics():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'role="tablist" aria-label="Depo ve saha stok bolumleri"' in app
    assert 'role="tab" id="stock-location-tab-stock"' in app
    assert 'role="tabpanel" aria-labelledby="stock-location-tab-${ayecStockLocationTab}"' in app
    assert 'event.key==="ArrowRight"' in app
    assert 'event.key==="ArrowLeft"' in app
    assert 'event.key==="Home"' in app
    assert 'event.key==="End"' in app
    assert "audit.locationTabKeyboard" in audit
