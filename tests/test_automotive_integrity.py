import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from pypdf import PdfReader

from src.database import Database
from src.ui.dialogs.automotive_checklist_dialog import AutomotiveChecklistDialog
from src.ui.dialogs.automotive_damage_dialog import AutomotiveDamageDialog
from src.ui.dialogs.automotive_new_service_dialog import AutomotiveNewServiceDialog
from src.ui.dialogs.automotive_technician_panel import AutomotiveTechnicianPanel
from src.ui.pages.service_board_page import ServiceBoardPage
from src.ui.pages.vehicle_maintenance_page import VehicleMaintenancePage
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.mixins._main_window_nav_mixin import MainWindowNavMixin
from src.utils.currency_helper import CurrencyHelper
from src.utils.sector_config import SECTOR_MENU_GROUPS, SECTOR_PAGES, SectorType
from Web_Arayuzu import Main as web_main


def _qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    return app


def test_automotive_service_board_new_record_opens_maintenance_card(monkeypatch):
    opened = []

    class _Dialog:
        def __init__(self, db, parent, sector_manager=None):
            opened.append((db, parent, sector_manager))

        def exec(self):
            return True

    class _Page:
        db = object()
        sector_manager = object()
        parent_window = object()
        refreshed = False

        def _is_automotive(self):
            return True

        def window(self):
            return self.parent_window

        def refresh_data(self):
            self.refreshed = True

    monkeypatch.setattr(
        "src.ui.dialogs.vehicle_maintenance_dialog.VehicleMaintenanceDialog",
        _Dialog,
    )
    page = _Page()

    ServiceBoardPage.open_new_service_dialog(page)

    assert opened == [(page.db, page.parent_window, page.sector_manager)]
    assert page.refreshed is True


def test_automotive_menu_matches_allowed_pages():
    groups = SECTOR_MENU_GROUPS[SectorType.OTOMOTIV]
    menu_pages = {page_id for pages in groups.values() for page_id in pages}
    allowed = SECTOR_PAGES[SectorType.OTOMOTIV]

    assert menu_pages == allowed
    assert 60 in menu_pages
    assert 210 in menu_pages
    assert 50 not in menu_pages
    assert 61 not in menu_pages
    assert 200 not in menu_pages
    assert 300 not in menu_pages


class _Plugin:
    def __init__(self, sector_id):
        self.sector_id = sector_id


class _SectorManager:
    def __init__(self, sector_id):
        self.plugin = _Plugin(sector_id)

    def get_current_plugin(self):
        return self.plugin


class _NavigationHarness(MainWindowNavMixin):
    def __init__(self, sector_id):
        self.sector_manager = _SectorManager(sector_id)
        self.db = None
        self.pages_requested = []
        self.panel_opened = False

    def open_technician_panel(self):
        self.panel_opened = True

    def get_page(self, index):
        self.pages_requested.append(index)
        return object()

    def _switch_content_with_fade(self, _page):
        return None


def test_page_60_routes_by_sector():
    automotive = _NavigationHarness("otomotiv")
    automotive.on_menu_click(60)
    assert automotive.pages_requested == [60]
    assert automotive.panel_opened is False

    technical = _NavigationHarness("teknik_servis")
    technical.on_menu_click(60)
    assert technical.pages_requested == []
    assert technical.panel_opened is True


def test_automotive_part_use_and_remove_restores_stock(tmp_path):
    db = Database(str(tmp_path / "automotive.db"))
    tracking_no = "AUTO-TEST-001"
    customer_id = db.add_customer({"name": "Automotive Test Customer"})
    assert customer_id
    device_id = db.add_device(
        {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": "Automotive Test Customer",
            "device_type": "Vehicle",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "status": "Tamirde",
        }
    )
    assert device_id
    part_id = db.add_part(
        "Automotive Test Filter",
        "Motor / Mekanik",
        5,
        150,
        purchase_price=100,
        code="AUTO-TEST-PART",
    )
    assert part_id

    assert db.use_part(part_id, 2, tracking_no)
    db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,))
    assert int(db.cursor.fetchone()[0]) == 3
    db.cursor.execute(
        "SELECT id FROM used_parts WHERE tracking_no=? AND part_id=? ORDER BY id DESC LIMIT 1",
        (tracking_no, part_id),
    )
    used_part_id = int(db.cursor.fetchone()[0])

    assert db.remove_used_part(used_part_id)
    db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,))
    assert int(db.cursor.fetchone()[0]) == 5
    db.close()


def test_foreign_currency_part_uses_try_snapshot_for_service_debt(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        CurrencyHelper,
        "_get_rate",
        staticmethod(lambda _db, code: 47.0 if code == "USD" else 1.0),
    )
    db = Database(str(tmp_path / "automotive-currency.db"))
    customer_id = db.add_customer({"name": "Currency Test Customer"})
    tracking_no = "AUTO-USD-001"
    db.add_device(
        {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "device_type": "Vehicle",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "status": "Tamirde",
            "labor_cost": 2500,
        }
    )
    part_id = db.add_part(
        "USD Service Part",
        "Computer",
        2,
        245,
        purchase_price=120,
        currency="USD",
    )

    assert db.use_part(part_id, 1, tracking_no)
    saved = db.cursor.execute(
        "SELECT currency, exchange_rate, price_try FROM used_parts "
        "WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
        (tracking_no,),
    ).fetchone()
    assert saved[0] == "USD"
    assert float(saved[1]) == 47.0
    assert float(saved[2]) == 11515.0
    assert db._get_used_parts_total_try(tracking_no) == 11515.0
    assert db._get_service_total_amount(tracking_no, labor_cost=2500) == 14015.0

    debt = db.cursor.execute(
        "SELECT amount, currency FROM currency_transactions "
        "WHERE tracking_no=? AND transaction_type='DEBIT' ORDER BY id DESC LIMIT 1",
        (tracking_no,),
    ).fetchone()
    assert debt is not None
    assert float(debt[0]) == 14015.0
    assert debt[1] == "TRY"

    db.cursor.execute(
        "UPDATE used_parts SET exchange_rate=1, price_try=0 WHERE tracking_no=?",
        (tracking_no,),
    )
    db.cursor.execute(
        "UPDATE currency_transactions SET amount=2745 WHERE tracking_no=? "
        "AND transaction_type='DEBIT'",
        (tracking_no,),
    )
    db.conn.commit()
    db.update_used_parts_schema()

    repaired = db.cursor.execute(
        "SELECT exchange_rate, price_try FROM used_parts WHERE tracking_no=?",
        (tracking_no,),
    ).fetchone()
    repaired_debt = db.cursor.execute(
        "SELECT amount FROM currency_transactions WHERE tracking_no=? "
        "AND transaction_type='DEBIT'",
        (tracking_no,),
    ).fetchone()
    assert tuple(map(float, repaired)) == (47.0, 11515.0)
    assert float(repaired_debt[0]) == 14015.0
    db.close()


def test_editable_vehicle_combo_accepts_completion_with_tab():
    app = _qapp()
    combo = ModernComboBox(items=["Fiat", "Ford", "Renault"], editable=True)
    combo.show()
    combo.setEditText("For")
    combo.completer().setCompletionPrefix("For")
    combo.completer().complete()
    app.processEvents()
    combo.completer().setCurrentRow(0)

    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Tab)

    assert combo.currentText() == "Ford"
    combo.close()
    combo.deleteLater()
    app.processEvents()


def test_automotive_dialogs_construct_with_current_contract():
    app = _qapp()
    templates = {"engine": [{"name": "Oil level"}]}
    checklist = AutomotiveChecklistDialog(templates, existing_data={})
    damage = AutomotiveDamageDialog(existing_data={})

    assert checklist.widgets
    assert damage.widgets

    checklist.close()
    damage.close()
    checklist.deleteLater()
    damage.deleteLater()
    app.processEvents()


def test_automotive_service_and_technician_dialogs_construct(tmp_path):
    app = _qapp()
    db = Database(str(tmp_path / "automotive-dialogs.db"))
    customer_id = db.add_customer({"name": "Automotive Dialog Customer"})
    device_id = db.add_device(
        {
            "tracking_no": "AUTO-DIALOG-001",
            "customer_id": customer_id,
            "customer_name": "Automotive Dialog Customer",
            "device_type": "Vehicle",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "status": "Bekliyor",
        }
    )
    db.cursor.execute("SELECT * FROM devices WHERE id=?", (device_id,))
    device = dict(db.cursor.fetchone())

    service_dialog = AutomotiveNewServiceDialog(db)
    technician_dialog = AutomotiveTechnicianPanel(db, device)
    app.processEvents()

    assert service_dialog is not None
    assert technician_dialog is not None
    assert technician_dialog.wizard_page1.pattern_group is None

    test_items = [label for label, visible in technician_dialog._get_test_items() if visible]
    assert "LCD Goruntu" not in test_items
    assert "Touchpad" not in test_items
    assert any("FREN" in label for label in test_items)
    assert any("OBD" in label for label in test_items)

    service_dialog.close()
    technician_dialog.close()
    service_dialog.deleteLater()
    technician_dialog.deleteLater()
    app.processEvents()
    db.close()


def test_glass_water_is_excluded_from_maintenance_messages(tmp_path, monkeypatch):
    db = Database(str(tmp_path / "automotive-reminders.db"))
    customer_id = db.add_customer(
        {"name": "Reminder Customer", "phone": "05340000000"}
    )
    target_date = "2026-07-20"
    common_card = {
        "customer_id": customer_id,
        "customer_name": "Reminder Customer",
        "customer_phone": "05340000000",
        "vehicle_plate": "10TEST10",
        "vehicle_brand": "Test",
        "vehicle_model": "Vehicle",
        "odometer": 10000,
        "service_date": "2026-07-19",
        "next_maintenance_date": "2026-07-21",
        "appointment_date": "2026-07-21",
        "appointment_time": "09:00",
        "reminder_date": target_date,
    }
    glass_card_id = db.save_vehicle_maintenance_card(
        dict(common_card),
        [
            {
                "item_type": "glass_water",
                "item_label": "Cam Suyu",
                "performed": True,
                "interval_days": 30,
                "interval_km": 0,
                "next_due_date": "2026-08-18",
                "next_due_odometer": 10000,
            }
        ],
    )
    oil_card = dict(common_card)
    oil_card["vehicle_plate"] = "10TEST11"
    oil_card_id = db.save_vehicle_maintenance_card(
        oil_card,
        [
            {
                "item_type": "oil_change",
                "item_label": "Yag Degisimi",
                "performed": True,
                "interval_days": 90,
                "interval_km": 10000,
                "next_due_date": "2026-10-17",
                "next_due_odometer": 10050,
            }
        ],
    )

    due_ids = {
        int(row["id"])
        for row in db.get_due_vehicle_maintenance_whatsapp_rows(target_date)
    }
    km_item_labels = {
        row["item_label"]
        for row in db.get_upcoming_vehicle_maintenance_km_whatsapp_rows(
            500, target_date
        )
    }

    assert glass_card_id not in due_ids
    assert oil_card_id in due_ids
    assert "Cam Suyu" not in km_item_labels
    assert "Yag Degisimi" in km_item_labels

    app = _qapp()
    page = VehicleMaintenancePage(db)
    app.processEvents()
    assert not page.btn_print.icon().isNull()
    assert not page.btn_pdf.icon().isNull()
    assert not page.btn_excel.icon().isNull()

    opened_urls = []
    monkeypatch.setattr(
        "src.ui.components.message_box.ModernConfirm.ask",
        staticmethod(lambda *_args, **_kwargs: True),
    )
    monkeypatch.setattr(
        "src.ui.pages.vehicle_maintenance_page.webbrowser.open",
        lambda url: opened_urls.append(url),
    )
    page._offer_appointment_whatsapp(glass_card_id)
    assert opened_urls == []
    page._offer_appointment_whatsapp(oil_card_id)
    assert len(opened_urls) == 1
    assert "Cam%20Suyu" not in opened_urls[0]
    assert "Yag%20Degisimi" in opened_urls[0]

    opened_panels = []

    class _FakeAutomotivePanel:
        def __init__(self, _db, tracking_no, _parent, sector_manager=None):
            opened_panels.append((tracking_no, sector_manager))

        def exec(self):
            return 0

    monkeypatch.setattr(
        "src.ui.dialogs.automotive_technician_panel.AutomotiveTechnicianPanel",
        _FakeAutomotivePanel,
    )
    page.load_cards()
    oil_row = next(
        index
        for index, payload in enumerate(page._row_payloads)
        if int(payload["id"]) == oil_card_id
    )
    page.table.selectRow(oil_row)
    expected_tracking = page._row_payloads[oil_row]["linked_device_tracking_no"]
    page.open_linked_service_form()
    assert opened_panels[0][0] == expected_tracking

    page.close()
    page.deleteLater()
    app.processEvents()
    db.close()


def test_web_maintenance_save_creates_full_automotive_workflow(tmp_path, monkeypatch):
    database_path = tmp_path / "web-maintenance.db"
    db = Database(str(database_path))
    customer_id = db.add_customer(
        {"name": "Web Maintenance Customer", "phone": "05551112233"}
    )
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    result = web_main.save_vehicle_maintenance_web(
        {
            "customer_id": customer_id,
            "vehicle_plate": "10TEST10",
            "vehicle_brand": "Ford",
            "vehicle_model": "Focus",
            "vehicle_year": 2022,
            "odometer": 45000,
            "service_date": "2026-07-19",
            "appointment_date": "2026-07-22",
            "appointment_time": "10:30",
            "items": [
                {
                    "item_type": "oil_change",
                    "item_label": "Yag Degisimi",
                    "performed": True,
                    "interval_days": 90,
                    "interval_km": 10000,
                    "next_due_date": "2026-10-17",
                    "next_due_odometer": 55000,
                },
                {
                    "item_type": "glass_water",
                    "item_label": "Cam Suyu",
                    "performed": True,
                    "interval_days": 30,
                    "interval_km": 0,
                    "next_due_date": "2026-08-18",
                    "next_due_odometer": 45000,
                },
            ],
        }
    )
    detail = web_main.vehicle_maintenance_detail(result["id"])

    assert result["tracking_no"].startswith("SRV-WEB-")
    assert result["important_items"] == ["Yag Degisimi"]
    assert len(detail["items"]) == 2
    assert detail["appointment"]["date"] == "2026-07-22"
    assert detail["appointment"]["time"] == "10:30"
    assert detail["service"]["tracking_no"] == result["tracking_no"]
    assert detail["service"]["fault_description"] == "Yag Degisimi, Cam Suyu"
    web_main.clear_tenant_context()


def test_web_automotive_navigation_and_sector_choice_contract():
    root = Path(__file__).resolve().parents[1]
    index_text = (root / "Web_Arayuzu" / "web" / "index.html").read_text(
        encoding="utf-8"
    )
    app_text = (root / "Web_Arayuzu" / "web" / "app.js").read_text(
        encoding="utf-8"
    )
    server_text = (root / "Web_Arayuzu" / "Main.py").read_text(
        encoding="utf-8"
    )

    assert 'id="sectorSelect"' not in index_text
    assert 'type="radio" name="sector" value="otomotiv"' in app_text
    assert '"automotive-stock"' in app_text
    assert '"vehicle-maintenance"' in app_text
    assert '"control-center"' in app_text
    assert "can_access_control_center" in app_text
    assert 'path == "/api/control/overview"' in server_text
    assert "def can_manage_tenant" in server_text
    assert 'path == "/api/control/tenant"' in server_text
    assert 'path == "/api/control/user"' in server_text
    assert 'id="managementCenterBtn"' in index_text
    assert 'managementCenterBtn.onclick=()=>navigate("control-center")' in app_text


def test_control_center_accepts_all_owner_role_labels():
    for role in (
        "Admin",
        "Administrator",
        "Super Admin",
        "Master",
        "Y\u00f6netici",
        "Sistem Y\u00f6neticisi",
        "Firma Y\u00f6neticisi",
        "Firma Sahibi",
        "En Yetkili Ki\u015fi",
        "Owner",
    ):
        assert web_main.role_is_admin(role), role

    for role in ("Manager", "Technician", "User", "Muhasebe"):
        assert not web_main.role_is_admin(role), role


def test_web_and_mobile_offer_pdf_expand_automotive_work_items(tmp_path, monkeypatch):
    database_path = tmp_path / "web-offer.db"
    db = Database(str(database_path))
    customer_id = db.add_customer({"name": "Web Offer Customer"})
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    maintenance = web_main.save_vehicle_maintenance_web(
        {
            "customer_id": customer_id,
            "vehicle_plate": "10PDF10",
            "vehicle_brand": "Ford",
            "vehicle_model": "Focus",
            "service_date": "2026-07-19",
            "items": [
                {"item_type": "oil", "item_label": "Yag Degisimi", "performed": True},
                {"item_type": "filter", "item_label": "Yag Filtresi", "performed": True},
                {"item_type": "air", "item_label": "Hava Filtresi", "performed": True},
            ],
        }
    )
    db = Database(str(database_path))
    offer_id = db.save_offer_record(
        {
            "offer_no": "WEB-AUTO-1",
            "customer_id": customer_id,
            "customer_name": "Web Offer Customer",
            "company_name": "AYEC Pro",
            "contact_name": "Web Offer Customer",
            "project_name": maintenance["tracking_no"],
            "template_type": "modern",
            "currency_code": "TRY",
            "totals": {
                "subtotal": 1000,
                "discount": 0,
                "vat_rate": 0.20,
                "vat_amount": 200,
                "total": 1200,
            },
            "items": [
                {
                    "service": "Servis Iscilik - Ford Focus",
                    "description": "Bakim kalemleri: Yag Degisimi ve 2 kalem daha",
                    "qty": 1,
                    "price": 1000,
                }
            ],
        }
    )
    db.close()

    target, offer_no = web_main.build_offer_pdf(offer_id)
    text_value = "\n".join(page.extract_text() or "" for page in PdfReader(target).pages)

    assert offer_no == "WEB-AUTO-1"
    assert "1. Yag Degisimi" in text_value
    assert "2. Yag Filtresi" in text_value
    assert "3. Hava Filtresi" in text_value
    assert "kalem daha" not in text_value
    target.unlink(missing_ok=True)
    web_main.clear_tenant_context()


def test_web_mobile_stock_camera_and_automotive_parity_contract():
    root = Path(__file__).resolve().parents[1]
    index_text = (root / "Web_Arayuzu" / "web" / "index.html").read_text(
        encoding="utf-8"
    )
    parity_text = (
        root / "Web_Arayuzu" / "web" / "automotive-parity.js"
    ).read_text(encoding="utf-8")

    assert "automotive-parity.js" in index_text
    assert 'id="stockSearchCameraBtn"' in parity_text
    assert 'capture="environment"' in parity_text
    assert "_ayecStartProductBarcodeLive" in parity_text
    assert "_ayecDecodeBarcodeImage" in parity_text
    assert 'name="oem_code"' in parity_text
    assert 'name="equivalent_code"' in parity_text
    assert 'name="compatible_models"' in parity_text
    assert 'name="shelf_number"' in parity_text
    assert 'data-c360-tab="vehicles"' in parity_text
    assert "automotive_form" in parity_text
    assert "service.plate=service.vehicle_plate" in parity_text


def test_web_stock_save_preserves_automotive_metadata(tmp_path, monkeypatch):
    database_path = tmp_path / "web-automotive-stock.db"
    Database(str(database_path)).close()
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)

    created = web_main.save_stock_card(
        {
            "name": "Oil Filter",
            "code": "AUTO-STOCK-1",
            "currency": "TRY",
            "stock": 4,
            "purchase_price": 100,
            "price": 150,
            "oem_code": "OEM-123",
            "equivalent_code": "EQ-456",
            "compatible_models": "Ford Focus 2020-2025",
            "shelf_number": "A-12",
        }
    )
    assert created["part"]["oem_code"] == "OEM-123"

    updated = web_main.save_stock_card(
        {
            "id": created["id"],
            "name": "Oil Filter",
            "code": "AUTO-STOCK-1",
            "currency": "TRY",
            "stock": 4,
            "purchase_price": 100,
            "price": 160,
        }
    )
    assert updated["part"]["oem_code"] == "OEM-123"
    assert updated["part"]["equivalent_code"] == "EQ-456"
    assert updated["part"]["compatible_models"] == "Ford Focus 2020-2025"
    assert updated["part"]["shelf_number"] == "A-12"
    web_main.clear_tenant_context()


def test_web_technician_update_saves_automotive_form(tmp_path, monkeypatch):
    database_path = tmp_path / "web-automotive-technician.db"
    db = Database(str(database_path))
    customer_id = db.add_customer({"name": "Vehicle Customer"})
    device_id = db.add_device(
        {
            "tracking_no": "AUTO-WEB-TECH-1",
            "customer_id": customer_id,
            "customer_name": "Vehicle Customer",
            "device_type": "Vehicle",
            "device_brand": "Ford",
            "device_model": "Focus",
            "vehicle_plate": "10AUTO10",
            "status": "Waiting",
        }
    )
    db.cursor.execute(
        "INSERT INTO customer_vehicles "
        "(customer_id, plate, brand, model, last_known_odometer, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (customer_id, "10AUTO10", "Ford", "Focus", 45000, 1),
    )
    vehicle_id = int(db.cursor.lastrowid)
    db.conn.commit()
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    result = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": "AUTO-WEB-TECH-1",
            "status": "Testing",
            "automotive_form": {
                "vehicle_id": vehicle_id,
                "vehicle_plate": "10AUTO10",
                "vehicle_vin": "VIN123456789",
                "engine_code": "ENG-1",
                "entry_odometer": 45000,
                "exit_odometer": 45025,
                "fuel_level_entry": "1/2",
                "fuel_level_exit": "1/2",
                "acceptance_notes": "Front bumper mark",
                "checklist": {"brakes": True, "road_test": True},
                "customer_approval": True,
                "kvkk_approval": True,
            },
        }
    )
    assert result["automotive_form_id"]

    db = Database(str(database_path))
    form = db.cursor.execute(
        "SELECT vehicle_vin, exit_odometer, checklist_json, customer_approval "
        "FROM automotive_service_forms WHERE device_id=?",
        (device_id,),
    ).fetchone()
    vehicle = db.cursor.execute(
        "SELECT last_known_odometer FROM customer_vehicles WHERE id=?",
        (vehicle_id,),
    ).fetchone()
    assert form[0] == "VIN123456789"
    assert int(form[1]) == 45025
    assert '"road_test": true' in form[2]
    assert int(form[3]) == 1
    assert int(vehicle[0]) == 45025
    db.close()
    web_main.clear_tenant_context()


def test_web_bootstrap_exposes_vehicle_identity_for_technician_form(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "web-automotive-bootstrap.db"
    db = Database(str(database_path))
    customer_id = db.add_customer({"name": "Bootstrap Vehicle Customer"})
    db.add_device(
        {
            "tracking_no": "AUTO-BOOT-1",
            "customer_id": customer_id,
            "customer_name": "Bootstrap Vehicle Customer",
            "device_type": "Vehicle",
            "device_brand": "Ford",
            "device_model": "Courier",
            "serial_no": "10 AUTO 10",
            "vehicle_plate": "10 AUTO 10",
            "vehicle_vin": "VIN-BOOT-1",
            "status": "Waiting",
        }
    )
    db.cursor.execute(
        "INSERT INTO customer_vehicles "
        "(customer_id, plate, brand, model, last_known_odometer, is_active) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (customer_id, "10 AUTO 10", "Ford", "Courier", 48250, 1),
    )
    vehicle_id = int(db.cursor.lastrowid)
    db.conn.commit()
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    payload = web_main.desktop_bootstrap()
    service = payload["customers"][0]["services"][0]

    assert service["plate"] == "10 AUTO 10"
    assert service["vehicle_vin"] == "VIN-BOOT-1"
    assert service["vehicle_id"] == vehicle_id
    assert service["odometer"] == 48250
    assert payload["customer_vehicles"][0]["plate"] == "10 AUTO 10"
    web_main.clear_tenant_context()


def test_web_bootstrap_exposes_shared_stock_location_summary(tmp_path, monkeypatch):
    database_path = tmp_path / "web-stock-locations.db"
    db = Database(str(database_path))
    part_id = db.add_part("Field Camera", "General", 10, 100, min_stock=1)
    db.ensure_stock_location_schema()
    main_id = db.get_stock_locations()[0]["id"]
    vehicle_id = db.create_stock_location("Field Van", "vehicle", "10 WEB 10")
    db.transfer_stock(
        main_id,
        vehicle_id,
        [{"part_id": part_id, "quantity": 3, "unit": "Adet"}],
    )
    db.close()

    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    payload = web_main.desktop_bootstrap()

    vehicle = next(item for item in payload["stock_locations"] if item["id"] == vehicle_id)
    assert payload["stock_location_summary"] == {
        "warehouses": 1,
        "vehicles": 1,
        "vehicle_quantity": 3,
        "locations": 2,
    }
    assert vehicle["vehicle_plate"] == "10 WEB 10"
    assert float(vehicle["quantity"]) == 3.0
    assert int(vehicle["part_count"]) == 1
    web_main.clear_tenant_context()


def test_web_sync_whitelist_contains_extended_automotive_tables():
    expected = {
        "automotive_checkup_forms",
        "automotive_quote_forms",
        "automotive_delivery_forms",
        "automotive_vehicle_history_events",
        "automotive_warranty_campaigns",
        "automotive_tire_suspension_records",
        "automotive_battery_electrical_tests",
        "automotive_parts_requests",
        "automotive_damage_marks",
        "vehicle_maintenance_photos",
    }
    assert expected <= web_main.TABLES


def test_web_customer_balances_are_saved_atomically(tmp_path):
    database_path = tmp_path / "web-customer-balances.db"
    db = Database(str(database_path))
    customer_id = db.add_customer({"name": "Balance Customer"})

    web_main.save_web_customer_balances(
        db.conn,
        customer_id,
        {"TRY": 1250.5, "USD": -20, "EUR": 7.25},
    )
    db.conn.commit()
    balances = {
        row[0]: float(row[1])
        for row in db.cursor.execute(
            "SELECT currency,balance FROM customer_currency_balances "
            "WHERE customer_id=?",
            (customer_id,),
        ).fetchall()
    }
    assert balances == {"TRY": 1250.5, "USD": -20.0, "EUR": 7.25}

    web_main.save_web_customer_balances(
        db.conn,
        customer_id,
        {"TRY": 40, "USD": 2.5, "EUR": -1},
    )
    db.conn.commit()
    updated = db.cursor.execute(
        "SELECT currency,balance FROM customer_currency_balances "
        "WHERE customer_id=? ORDER BY currency",
        (customer_id,),
    ).fetchall()
    assert [(row[0], float(row[1])) for row in updated] == [
        ("EUR", -1.0),
        ("TRY", 40.0),
        ("USD", 2.5),
    ]
    db.close()


def test_web_automotive_service_links_preserve_vehicle_fields(tmp_path):
    database_path = tmp_path / "web-automotive-service-links.db"
    db = Database(str(database_path))
    customer_id = db.add_customer(
        {"name": "Automotive Customer", "phone": "05550000000"}
    )
    device_values = {
        "tracking_no": "AUTO-LINK-1",
        "customer_id": customer_id,
        "customer_name": "Automotive Customer",
        "device_type": "Vehicle",
        "device_brand": "Ford",
        "device_model": "Courier",
        "serial_no": "10 QA 001",
        "vehicle_plate": "10 QA 001",
        "vehicle_vin": "VIN-LINK-1",
        "fault_description": "Periodic maintenance",
        "entry_date": "2026-07-20",
        "estimated_date": "2026-07-21",
        "service_source": "Web Otomotiv",
        "created_at": "2026-07-20T10:00:00",
    }
    device_id = db.add_device(device_values)
    linked = web_main.link_web_automotive_service(
        db.conn,
        device_id,
        device_values,
        {
            "vehicle_plate": "10 QA 001",
            "vehicle_vin": "VIN-LINK-1",
            "vehicle_model_name": "Courier",
            "vehicle_year": 2022,
            "vehicle_type": "Commercial",
            "engine_type": "1.5 TDCI",
            "fuel_type": "Diesel",
            "vehicle_odometer": 48275,
            "customer_phone": "05550000000",
        },
    )
    db.conn.commit()

    vehicle = db.cursor.execute(
        "SELECT model,year,vehicle_type,engine_type,fuel_type,last_known_odometer "
        "FROM customer_vehicles WHERE id=?",
        (linked["vehicle_id"],),
    ).fetchone()
    form = db.cursor.execute(
        "SELECT customer_id,vehicle_plate,vehicle_vin,entry_odometer "
        "FROM automotive_service_forms WHERE id=?",
        (linked["form_id"],),
    ).fetchone()
    card = db.cursor.execute(
        "SELECT customer_phone,vehicle_model,vehicle_year,fuel_type,odometer "
        "FROM vehicle_maintenance_cards WHERE id=?",
        (linked["card_id"],),
    ).fetchone()
    maintenance_card_id = db.cursor.execute(
        "SELECT vehicle_maintenance_card_id FROM devices WHERE id=?",
        (device_id,),
    ).fetchone()[0]

    assert tuple(vehicle) == (
        "Courier",
        "2022",
        "Commercial",
        "1.5 TDCI",
        "Diesel",
        48275,
    )
    assert tuple(form) == (customer_id, "10 QA 001", "VIN-LINK-1", 48275)
    assert tuple(card) == ("05550000000", "Courier", "2022", "Diesel", 48275)
    assert maintenance_card_id == linked["card_id"]
    db.close()


def test_web_automotive_forms_wait_for_persistence_before_refresh():
    parity_text = (
        Path(__file__).resolve().parents[1]
        / "Web_Arayuzu"
        / "web"
        / "automotive-parity.js"
    ).read_text(encoding="utf-8")

    assert "saveCustomer=async function" in parity_text
    assert 'await apiFetch("/api/desktop/table/customers"' in parity_text
    assert "appointmentDialog=function" in parity_text
    assert 'await apiFetch("/api/desktop/table/appointments"' in parity_text
    assert "serviceDialog=function" in parity_text
    assert 'await apiFetch("/api/desktop/table/devices"' in parity_text
    assert "financeDialog=function" in parity_text
    assert 'await apiFetch("/api/desktop/table/accounting"' in parity_text
    assert "contextAction=function" in parity_text
    assert 'await apiFetch("/api/desktop/table/appointments"' in parity_text
    assert parity_text.count("await hydrateDesktop(true)") >= 5


def test_web_visible_actions_have_click_signal_handlers():
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (web_root / "index.html", web_root / "app.js", web_root / "automotive-parity.js")
    )
    actions = set(re.findall(r'data-action=["\']([^"\']+)', sources))
    missing = sorted(action for action in actions if sources.count(action) < 2)

    assert actions
    assert not missing
    assert "_ayecBoundActions" in sources
    assert "bindPage=function" in sources


def test_automotive_parity_loads_after_the_main_web_application():
    index_text = (
        Path(__file__).resolve().parents[1]
        / "Web_Arayuzu"
        / "web"
        / "index.html"
    ).read_text(encoding="utf-8")

    assert index_text.index('src="app.js') < index_text.index(
        'src="automotive-parity.js'
    )
