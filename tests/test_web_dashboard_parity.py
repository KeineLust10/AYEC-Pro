import shutil
import subprocess
from pathlib import Path


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
    assert 'dashboard-parity.css?v=20261008-8' in html
    assert 'dashboard-parity.js?v=20261008-1' in html


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


def test_dashboard_parity_layout_expands_on_desktop_and_reflows_on_mobile():
    styles = (WEB / "dashboard-parity.css").read_text(encoding="utf-8")
    assert "repeat(8, minmax(0, 1fr))" in styles
    assert "repeat(4, minmax(0, 1fr))" in styles
    assert "repeat(3, minmax(0, 1fr))" in styles
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


def test_finance_pages_use_shared_midnight_slate_tokens():
    styles = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

    for page in ("finance", "income", "expense"):
        assert f'html[data-theme="forest"] body[data-page="{page}"]' in styles
    assert "--finance-canvas: var(--bg);" in styles
    assert "--finance-surface: var(--surface);" in styles
    assert "--finance-outline: var(--line);" in styles
    assert "--finance-primary: var(--brand);" in styles
