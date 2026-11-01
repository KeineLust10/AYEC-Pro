import shutil
import sqlite3
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
NODE = shutil.which("node") or str(
    Path("C:/Users/yedek/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
)


def test_dashboard_uses_desktop_shell_and_dashboard_parity_assets_in_order():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert html.index("desktop-parity.css") < html.index("dashboard-parity.css")
    assert html.index("app.js?v=") < html.index("dashboard-parity.js")
    assert html.index("appointments-reference.js") < html.index("dashboard-parity.js")
    assert 'dashboard-parity.css?v=' in html
    assert 'automotive-parity.js?v=' in html
    assert 'dashboard-parity.js?v=' in html
    assert 'styles.css?v=' in html


def test_dashboard_mirrors_desktop_widgets_and_keeps_web_navigation_actions():
    script = (WEB / "dashboard-parity.js").read_text(encoding="utf-8")
    assert 'renderDashboard=renderDashboardParity' in script
    assert 'data-dashboard-parity-filter' in script
    assert 'navigate("service-status")' in script
    assert 'data-page="finance"' in script
    assert 'data-page="appointments"' in script
    assert 'data-action="export-all"' in script
    assert 'data-action="quick-add"' in script
    assert 'dashboardParityStatusPeriod' in script
    assert 'dashboardParityTrendMonths' in script
    assert 'dashboard-ticker' in script
    assert 'dashboard-bottom-status' in script
    assert 'Servis Durum Da' in script
    assert "Ayl" + chr(92) + "u0131k Servis Trendi" in script
    assert "Son " + chr(92) + "u0130" + chr(92) + "u015flemler" in script
    for source in ("db.appointments", "db.finance", "db.stock", "dashboardServices()"):
        assert source in script


def test_dashboard_recent_rows_preserve_native_cell_tooltips():
    script = (WEB / "dashboard-parity.js").read_text(encoding="utf-8")

    assert 'title="${esc(customer)}"' in script
    assert 'title="${esc(detail)}"' in script
    assert 'title="${esc(status)}"' in script


def test_dashboard_service_edit_round_trips_through_authenticated_tenant_api(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        customer_id = web_main.insert_available(connection, "customers", {
            "name": "Dashboard Test Customer",
            "phone": "05550001122",
        })
        device_id = web_main.insert_available(connection, "devices", {
            "tracking_no": "WEB-DASH-EDIT-1",
            "customer_id": customer_id,
            "customer_name": "Dashboard Test Customer",
            "device_type": "Laptop",
            "device_brand": "Old Brand",
            "device_model": "Old Model",
            "serial_no": "DASH-SERIAL-1",
            "fault_description": "Old fault",
            "status": "Bekliyor",
            "priority": "Normal",
            "created_at": "2026-10-14T10:00:00",
        })

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = base_url + "/api/desktop/table/devices?limit=500"
    try:
        assert requests.get(table_url).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            base_url + "/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200, login.text
        page = session.get(table_url)
        assert page.status_code == 200, page.text
        row = next(item for item in page.json()["rows"] if int(item["id"]) == device_id)
        assert row["device_brand"] == "Old Brand"

        saved = session.post(base_url + "/api/desktop/table/devices", json={
            "id": device_id,
            "_action": "update",
            "customer_id": customer_id,
            "customer_name": "Dashboard Test Customer",
            "device_type": "Laptop",
            "device_brand": "New Brand",
            "device_model": "New Model",
            "serial_no": "DASH-SERIAL-1",
            "urgency": "Yuksek",
            "priority": "Yuksek",
            "technician": "Tech One",
            "fault_description": "Updated fault",
            "internal_notes": "Desk review",
            "repair_details": "Replaced part",
            "estimated_date": "2026-10-20",
            "price": 149.5,
            "delivery_method": "Hand Delivery",
            "service_location": "Workshop",
            "warranty_status": "Active",
            "delivered_by_name": "Courier One",
            "delivered_by_phone": "05550002233",
            "other_info": "Keep upright",
            "bios_password": "BIOS-SAMPLE",
        })
        assert saved.status_code == 200, saved.text
        assert saved.json() == {"ok": True, "id": device_id, "action": "update"}
        with sqlite3.connect(tenant_path) as connection:
            updated = connection.execute(
                "SELECT device_type,device_brand,device_model,serial_no,urgency,priority,technician,fault_description,internal_notes,repair_details,estimated_date,price,delivery_method,service_location,warranty_status,delivered_by_name,delivered_by_phone,other_info,bios_password FROM devices WHERE id=?",
                (device_id,),
            ).fetchone()
        assert updated == (
            "Laptop", "New Brand", "New Model", "DASH-SERIAL-1", "Yuksek", "Yuksek",
            "Tech One", "Updated fault", "Desk review", "Replaced part", "2026-10-20", 149.5,
            "Hand Delivery", "Workshop", "Active", "Courier One", "05550002233", "Keep upright", "BIOS-SAMPLE",
        )
    finally:
        server.shutdown()
        server.server_close()


def test_dashboard_parity_layout_expands_on_desktop_and_reflows_on_mobile():
    styles = (WEB / "dashboard-parity.css").read_text(encoding="utf-8")
    assert "repeat(8, minmax(0, 1fr))" in styles
    assert "repeat(4, minmax(0, 1fr))" in styles
    assert "repeat(3, minmax(0, 1fr))" in styles
    assert ".dashboard-shortcut-overlay{container-type:inline-size}" in styles
    assert "@container (min-width:654px) and (max-width:973px)" in styles
    assert "@container (min-width:1294px)" in styles
    assert "@media (max-width: 760px)" in styles
    assert "width: 100vw;\n    max-width: 100vw;" in styles
    assert "margin: -16px -12px 10px;" in styles
    assert ".dashboard-chart-grid {\n    grid-template-columns: minmax(0, 1fr);" in styles
    assert "min-width: 0" in styles


def test_dashboard_renderer_keeps_live_data_period_and_status_navigation_behavior():
    script = r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const changes={},clicks={};
const data={id:'service-1',no:'S-1',customer:'Test Customer',customerId:'customer-1',
  date:'2026-10-07',status:'Tamir Edildi',amount:1250,labor_cost:250,device_type:'Phone'};
const sandbox={
  document:{addEventListener:(name,callback)=>{(name==='change'?changes:clicks)[name]=callback}},
  $:selector=>selector==='#currentUserName'?{textContent:'Test User'}:null,
  db:{appointments:[{date:'2026-10-08',status:'Bekliyor'}],finance:[],stock:[{qty:0,min:2}],activities:[]},
  currentSector:'teknik_servis',
  dashboardServices:()=>[data],serviceStatusKey:service=>service.status==='Tamir Edildi'?'test':'bekliyor',
  serviceIsDebt:()=>false,moneyNumber:Number,money:value=>'TRY '+value,esc:value=>String(value||''),
  customerName:()=>data.customer,dashboardFilter:'all',
  navigate:route=>{sandbox.navigated=route},render:()=>{sandbox.renderCount++;sandbox.output=sandbox.renderDashboard()},
  renderCount:0,output:'',navigated:''
};
sandbox.window=sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
assert.ok(sandbox.output.includes('dashboard-welcome'));
assert.ok(sandbox.output.includes("AYEC Pro Teknik Servis Y\u00f6netimi"));
assert.ok(sandbox.output.includes('dashboard-status-grid'));
assert.ok(sandbox.output.includes('dashboard-metric-grid'));
assert.ok(sandbox.output.includes('dashboard-donut'));
assert.ok(sandbox.output.includes('dashboard-trend'));
assert.ok(sandbox.output.includes('dashboard-recent-panel'));
assert.ok(sandbox.output.includes('service-detail'));
assert.ok(sandbox.output.includes('S-1'));
const filterButton={dataset:{dashboardParityFilter:'tamirde'}};
clicks.click({target:{closest:selector=>selector==='[data-dashboard-parity-filter]'?filterButton:null}});
assert.equal(sandbox.dashboardFilter,'tamirde');
assert.equal(sandbox.navigated,'service-status');
const periodSelect={id:'dashboardParityStatusPeriod',value:'all'};
changes.change({target:periodSelect});
assert.equal(sandbox.renderCount,2);
assert.ok(sandbox.output.includes('value="all" selected'));
const trendSelect={id:'dashboardParityTrendMonths',value:'6'};
changes.change({target:trendSelect});
assert.equal(sandbox.renderCount,3);
assert.ok(sandbox.output.includes('Son 6 Ay'));
'''
    result = subprocess.run(
        [NODE, "-e", script, str(WEB / "dashboard-parity.js")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_dashboard_services_include_unlinked_desktop_devices_and_keep_actions_resolvable():
    script = r'''
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(process.argv[1],'utf8');
const dashboardFn=source.match(/function dashboardServices\(\)\{[\s\S]*?\n\}/)?.[0];
const findFn=source.match(/function findService\(no\)\{[^\n]*\}/)?.[0];
assert.ok(dashboardFn&&findFn);
const sandbox={db:{customers:[{id:7,name:'Linked Customer',balances:{TRY:-12},services:[{id:70,no:'SRV-LINKED',device:'Laptop',note:'Customer service',status:'Tamirde'}]}],serviceDevices:[
 {id:70,no:'SRV-LINKED',tracking_no:'SRV-LINKED',customer_id:7,customer_name:'Linked Customer',device_brand:'Brand',device_model:'Laptop',status:'Tamirde'},
 {id:71,no:'SRV-UNLINKED',tracking_no:'SRV-UNLINKED',customer_id:null,customer_name:'Walk-in',device_type:'Phone',device_model:'Model X',fault_description:'Screen issue',status:'Bekliyor'}
]}};
vm.createContext(sandbox);
vm.runInContext(`${dashboardFn};${findFn};this.dashboardServices=dashboardServices;this.findService=findService;`,sandbox);
const rows=sandbox.dashboardServices();
assert.equal(rows.length,2);
assert.equal(rows.find(row=>row.no==='SRV-LINKED').balances.TRY,-12);
assert.equal(rows.find(row=>row.no==='SRV-UNLINKED').customer,'Walk-in');
assert.equal(rows.find(row=>row.no==='SRV-UNLINKED').note,'Screen issue');
const [customer,service]=sandbox.findService('SRV-UNLINKED');
assert.equal(customer.name,'Walk-in');
assert.equal(service.id,71);
assert.equal(service.no,'SRV-UNLINKED');
assert.equal(service.device,'Model X');
'''
    result = subprocess.run(
        [NODE, "-e", script, str(WEB / "app.js")],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr


def test_finance_pages_use_shared_midnight_slate_tokens():
    styles = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

    for page in ("finance", "income", "expense"):
        assert f'html[data-theme="forest"] body[data-page="{page}"]' in styles
    assert "--finance-canvas: var(--bg);" in styles
    assert "--finance-surface: var(--surface);" in styles
    assert "--finance-outline: var(--line);" in styles
    assert "--finance-primary: var(--brand);" in styles


def test_dashboard_service_context_menu_can_change_service_status():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert 'if(kind==="service")items=[["Teknisyen Panelinde A\\u00e7","technician"],["Durumu De\\u011fi\\u015ftir","change-status"]]' in app
    assert 'if(action==="change-status")return changeServiceStatusFromWeb(id)' in app
    assert 'function changeServiceStatusFromWeb(trackingNo)' in app
    assert '"/api/desktop/table/devices"' in app
    assert '_action:"update",status' in app
    assert 'data-service-context="change-status"' in app
    assert 'data-service-context="quick-close"' in app
    assert 'button.dataset.serviceContext==="quick-close")quickCloseServiceFromWeb(id)' in app
