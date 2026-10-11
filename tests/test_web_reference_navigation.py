import shutil
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Web_Arayuzu' / 'web' / 'app.js'
NODE = shutil.which('node') or str(
    Path('C:/Users/yedek/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
)


def _section(start, end):
    selected = []
    collecting = False
    with SOURCE.open(encoding='utf-8') as stream:
        for line in stream:
            if not collecting and line.startswith(start):
                collecting = True
            if collecting and line.startswith(end):
                break
            if collecting:
                selected.append(line)
    assert selected, start
    return ''.join(selected)


def test_web_nested_reference_menu_routes_and_ancestor_expansion():
    model = _section('ayecSectorMenuModels.teknik_servis=[', 'const ayecDesktopPageIds=')
    runtime = _section('function ayecMenuItems(', 'const ayecNavigateBeforeSectorMenus=')
    editor = _section('function ayecEditorRow(', 'interfaceEditorDialog=function')
    script = r'''
const assert=require('node:assert/strict');
const ayecSectorMenuModels={};
const modernMenu=[],menu=[];
let currentSector='teknik_servis',page='brands',stored={};
const hidden=new Set();
const nav={innerHTML:''};
const localStorage={getItem:()=>JSON.stringify(stored),setItem:(_key,value)=>{stored=JSON.parse(value)}};
const $=selector=>selector==='#nav'?nav:null;
const esc=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;');
const menuVisible=item=>!hidden.has(item.id);
const labelFor=item=>item.label;
const ayecSectorMenu=sector=>ayecSectorMenuModels[sector];
const menuLabels=()=>({}),menuVisibility=()=>({});
''' + model + runtime + editor + r'''
assert.deepEqual(ayecMenuPath('brands').map(item=>item.id),['service-settings-parent','brands']);
assert.equal(ayecParentForPage('brands'),'service-settings-parent');
assert.deepEqual(ayecMenuPath('dashboard').map(item=>item.id),['service-parent','dashboard']);
for(const sector of ['teknik_servis','otomotiv']){
  for(const id of ['brands','product-groups','report-templates','service-definitions','services']){
    assert.equal(ayecMenuItems(sector).filter(item=>item.id===id).length,1);
    assert.equal(ayecMenuItem(id,sector).id,id);
  }
}
assert.deepEqual(ayecMenuPath('brands','otomotiv').map(item=>item.id),['service-settings-parent','brands']);
renderNav();
assert.ok(nav.innerHTML.includes('data-parent="nav-teknik_servis-service-settings-parent"'));
assert.ok(nav.innerHTML.includes('active" data-page="brands"'));
hidden.add('service-settings-parent');
renderNav();
assert.ok(!nav.innerHTML.includes('data-page="brands"'));
assert.ok(nav.innerHTML.includes('data-page="services"'));
hidden.clear();
hidden.add('dashboard');
assert.equal(firstVisiblePage(),'services');
for(const sector of ['teknik_servis','otomotiv']){
  const output=ayecEditorPanel(sector,'Title','Description');
  for(const id of ['brands','product-groups','report-templates','service-definitions']){
    assert.ok(output.includes(`name="menu_${sector}_${id}"`));
    assert.ok(output.includes(`name="visible_${sector}_${id}"`));
  }
}
console.log('nested navigation passed');
'''
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_web_uses_the_desktop_forest_theme_when_configured():
    source = SOURCE.read_text(encoding='utf-8')
    assert 'desktopSettings.color_theme_full||""' in source
    assert 'desktopThemeName==="forest"||desktopThemeName==="orman"?"forest":""' in source
    assert 'const theme=desktopTheme||desktopSettings.web_theme||db.settings.theme||"midnight"' in source


def test_web_status_footer_matches_the_desktop_shell():
    html = (ROOT / 'Web_Arayuzu' / 'web' / 'index.html').read_text(encoding='utf-8')
    styles = (ROOT / 'Web_Arayuzu' / 'web' / 'desktop-parity.css').read_text(encoding='utf-8')
    source = SOURCE.read_text(encoding='utf-8')
    assert 'id="shellStatusBar"' in html
    assert 'ERP Core Yerel Veritabani Hazir' in html
    assert 'AYEC PRO Finans Konsolu v2.0.4 Premium Enterprise' in html
    assert 'function updateShellStatus()' in source
    assert 'exchangeRateState=source.exchange_rates||exchangeRateState' in source
    assert '.shell-status-bar' in styles
    assert 'position: fixed' in styles
    assert 'html[data-theme="forest"] .topbar' in styles
    assert 'html[data-theme="forest"] .customer-workspace-head' in styles
    assert 'grid-template-columns: repeat(4, max-content)' in styles
    assert 'html[data-theme="forest"] .customer-data-table td' in styles


def test_opening_nested_accordion_preserves_its_ancestor():
    toggle = _section('function toggleNavParent(', '$("#nav").addEventListener(')
    script = r'''
const assert=require('node:assert/strict');
function node(classes,id){
  const values=new Set(classes);
  return {dataset:{parent:id},hidden:false,style:{},attributes:{},
    classList:{contains:key=>values.has(key),remove:key=>values.delete(key),
      toggle:(key,on)=>on?values.add(key):values.delete(key)},
    setAttribute(key,value){this.attributes[key]=value}};
}
const nav={};
const ancestor=node(['nav-parent','open'],'service');
const ancestorMenu=node(['submenu','open']);
const button=node(['nav-parent'],'settings');
const submenu=node(['submenu']);
const sibling=node(['nav-parent','open'],'other');
const siblingMenu=node(['submenu','open']);
button.closest=()=>nav;
button.parentElement={children:[button,submenu,sibling,siblingMenu]};
const document={getElementById:id=>id==='settings'?submenu:null};
''' + toggle + r'''
assert.equal(toggleNavParent(button),true);
assert.ok(ancestor.classList.contains('open'));
assert.ok(ancestorMenu.classList.contains('open'));
assert.ok(button.classList.contains('open'));
assert.equal(button.attributes['aria-expanded'],'true');
assert.equal(submenu.hidden,false);
assert.ok(!sibling.classList.contains('open'));
assert.equal(siblingMenu.hidden,true);
console.log('nested toggle passed');
'''
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_mobile_menu_search_opens_nested_matches_and_restores_normal_navigation():
    search = _section('function filterMobileNavigation(', ' mobileNavSearch.addEventListener(')
    script = r'''
const assert=require('node:assert/strict');
let restored=0;
const renderNav=()=>{restored++};
const values=new Set();
const parent={hidden:true,attributes:{},classList:{toggle:()=>{}},setAttribute(key,value){this.attributes[key]=value}};
const match={textContent:'Marka Adlari',hidden:true};
const other={textContent:'Finans',hidden:false};
const submenu={textContent:'Marka Adlari',hidden:true,style:{display:'none'},
  previousElementSibling:parent,classList:{toggle:(key,on)=>on?values.add(key):values.delete(key)}};
const nav={};
const $=()=>nav;
const $$=selector=>selector==='.nav-button'?[match,other]:selector==='.submenu'?[submenu]:[];
''' + search + r'''
filterMobileNavigation('Marka');
assert.equal(match.hidden,false);
assert.equal(other.hidden,true);
assert.equal(submenu.hidden,false);
assert.equal(submenu.style.display,'block');
assert.equal(parent.hidden,false);
assert.equal(parent.attributes['aria-expanded'],'true');
filterMobileNavigation('');
assert.equal(restored,1);
'''
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_reference_navigation_styles_are_linked_and_keep_mobile_controls_available():
    web = ROOT / 'Web_Arayuzu' / 'web'
    css = (web / 'reference-navigation.css').read_text(encoding='utf-8')
    html = (web / 'index.html').read_text(encoding='utf-8')
    assert html.index('reference-navigation.css') > html.index('styles.css')
    assert '.nav-button[hidden]' in css
    assert '.submenu .submenu' in css
    assert '--nav-active: var(--brand)' in css
    assert 'background: var(--nav-active)' in css
    assert '.nav-button .nav-active-dot' in css
    desktop_parity = (web / 'desktop-parity.css').read_text(encoding='utf-8')
    assert '.sidebar .submenu {\n  display: none;\n  margin: 8px 0 5px 34px;' in desktop_parity
    assert '.sidebar .submenu .nav-button {\n  min-height: 42px;\n  padding: 6px 0;' in desktop_parity
    assert 'background: var(--ayec-slate-raised);\n  border-color: transparent;\n  color: var(--ayec-electric);' in desktop_parity
    assert 'height: 100dvh' in css
    assert 'width: min(82vw, 292px)' in css
    assert '.top-actions .global-search' in css
    assert 'flex-wrap: wrap' in css
    assert '--type-body: 13px' in css
    assert '--field-height: 40px' in css
    assert 'max-width: 420px' in css
    assert 'env(safe-area-inset-bottom' in css
    assert '.table-wrap table' in css


def test_desktop_parity_shell_uses_one_full_width_sidebar_contract():
    index = (ROOT / 'Web_Arayuzu' / 'web' / 'index.html').read_text(encoding='utf-8')
    styles = (ROOT / 'Web_Arayuzu' / 'web' / 'styles.css').read_text(encoding='utf-8')
    assert '--sidebar:260px' not in styles
    assert 'One shared Midnight Slate navigation contract' not in styles
    assert '<div class="sidebar-license">' in index
    assert 'v2.0.4 Premium</span>' in index
    assert 'id="logoutBtn"' in index and 'Oturumu Kapat</button>' in index
    assert '.sidebar-bottom .user-logout{width:100%;height:42px' in styles
    styles = (ROOT / 'Web_Arayuzu' / 'web' / 'desktop-parity.css').read_text(encoding='utf-8')
    styles = (ROOT / 'Web_Arayuzu' / 'web' / 'desktop-parity.css').read_text(encoding='utf-8')
    assert index.index('midnight-reference.css') < index.index('desktop-parity.css')
    assert index.index('automotive-parity.css') < index.index('desktop-parity.css')
    assert 'desktop-parity.css?v=' in index
    assert '--sidebar: 320px' in styles
    assert '.sidebar .nav-button.active' in styles
    assert '.sidebar-bottom > .nav-button[data-page="settings"]' in styles
    assert 'customer-banners button[data-customer-filter="vip"]' in styles
    assert 'customer-export-actions .mini' in styles
    assert '@media (max-width: 760px)' in styles
    assert 'width: min(320px, calc(100vw - 40px))' in styles
    assert 'grid-template-columns: minmax(0, var(--sidebar)) minmax(0, 1fr)' in styles
    assert '.content > section' in styles
    assert '.content .form-grid {\n    grid-template-columns: minmax(0, 1fr);' in styles
    forest = (ROOT / 'src' / 'themes' / 'forest_theme.json').read_text(encoding='utf-8')
    assert '"window": "#0A1410"' in forest
    assert '"accent": "#10B981"' in forest
    assert 'html[data-theme="forest"]' in styles
    assert '--bg: #0a1410' in styles
    assert '--brand: #10b981' in styles
    assert 'background: var(--sidebar-bg, var(--ayec-slate-bg))' in styles
    assert '.template-categories button.active' in styles
    assert '.template-table-card th' in styles
    assert '.einvoice-table th' in styles
    assert '.content table th' in styles
    assert '.main nav {\n  flex-direction: row;' in styles
    assert '.appointment-ref-toolbar [aria-selected=\"true\"]' in styles


def test_web_sidebar_uses_the_desktop_menu_sections_and_retains_page_routes():
    app = SOURCE.read_text(encoding='utf-8')
    menu = app[app.index('ayecSectorMenuModels.teknik_servis=['):app.index('const ayecDesktopPageIds=')]
    for label in (
        'SERVIS OPERASYON', 'TICARI & SATI\\u015e', 'FINANS & MUHASEBE',
        'Y\\u00d6NET\\u0130M', 'S\\u0130STEM', 'service-settings-parent',
        'customer-parent', 'project-parent', 'offer-parent', 'management-parent',
    ):
        assert label in menu
    for route in (
        'dashboard', 'services', 'service-list', 'service-status', 'technician', 'field-service',
        'appointments', 'logistics', 'job-reports', 'assistant', 'service-definitions',
        'brands', 'customers', 'contracts', 'partners', 'reminders', 'announcements',
        'stock', 'stock-locations', 'movements', 'import', 'loaners', 'sales',
        'finance', 'income', 'expense', 'banks', 'loans', 'checks', 'invoices', 'personnel',
        'projects', 'project-archive', 'knowledge', 'settings', 'backup', 'support',
        'audit', 'manual', 'dialog-catalog',
    ):
        assert f'id:"{route}"' in menu
    assert 'loans:{group:"Finans",title:"Krediler & Taksitler",table:"loans"' in app
    assert 'item.children.filter(child=>allowed.has(child.id))' in app
    assert 'item.children.length>0:allowed.has(item.id)' in app
    assert '"service-list":42,"service-status":43' in app
    assert '"stock-locations":51' in app

    desktop_navigation = (ROOT / 'src' / 'utils' / 'navigation_config.py').read_text(encoding='utf-8')
    desktop_sections = desktop_navigation[
        desktop_navigation.index('TECHNICAL_MENU_SECTIONS:'):
        desktop_navigation.index('AUTOMOTIVE_MENU_SECTIONS:')
    ]
    automotive_sections = desktop_navigation[
        desktop_navigation.index('AUTOMOTIVE_MENU_SECTIONS:'):
        desktop_navigation.index('PAGE_WEB_ROUTES:')
    ]
    expected_page_ids = {
        int(value)
        for sections in (desktop_sections, automotive_sections)
        for value in re.findall(r'\b\d+\b', sections)
    }
    page_id_map = app[app.index('const ayecDesktopPageIds='):app.index('function ayecSectorMenu(')]
    mapped_page_ids = {int(value) for value in re.findall(r':\s*(\d+)', page_id_map)}
    assert expected_page_ids <= mapped_page_ids


def test_unified_sidebar_pin_persists_desktop_expand_and_hover_behavior():
    index = (ROOT / 'Web_Arayuzu' / 'web' / 'index.html').read_text(encoding='utf-8')
    app = SOURCE.read_text(encoding='utf-8')
    styles = (ROOT / 'Web_Arayuzu' / 'web' / 'desktop-parity.css').read_text(encoding='utf-8')
    assert 'id="sidebarPin"' in index
    assert 'aria-pressed="true"' in index
    assert 'localStorage.getItem("ayec-sidebar-pinned")' in app
    assert 'localStorage.setItem("ayec-sidebar-pinned"' in app
    assert 'pointerenter' in app and 'sidebar-peek' in app
    assert 'currentSector==="otomotiv"?"OTOMOTIV MODU":"ERP"' in app
    assert 'width: 76px' in styles
    assert '.sidebar .brand-sector' in styles
    assert '.sidebar-pin {\n    display: none;' in styles


def test_sidebar_pin_updates_collapse_accessibility_and_saved_preference():
    pin = _section(' function setSidebarPinned(', ' setSidebarPinned(sidebarPinned,false);')
    script = r'''
const assert=require('node:assert/strict');
const classes=new Set();
const attributes={};
const storage={values:{},setItem(key,value){this.values[key]=value}};
const sidebarShell={classList:{toggle:(name,on)=>on?classes.add(name):classes.delete(name)}};
const sidebarPin={setAttribute:(name,value)=>attributes[name]=value};
let sidebarPinned=true;
const localStorage=storage;
''' + pin + r'''
setSidebarPinned(false);
assert.equal(sidebarPinned,false);
assert.ok(classes.has('sidebar-collapsed'));
assert.equal(attributes['aria-pressed'],'false');
assert.equal(attributes.title,'Sol men\u00fc hover ile a\u00e7\u0131l\u0131r');
assert.equal(storage.values['ayec-sidebar-pinned'],'0');
setSidebarPinned(true,false);
assert.equal(sidebarPinned,true);
assert.ok(!classes.has('sidebar-collapsed'));
assert.equal(attributes['aria-pressed'],'true');
assert.equal(storage.values['ayec-sidebar-pinned'],'0');
'''
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr























