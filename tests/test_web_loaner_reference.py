from pathlib import Path
import os
import subprocess
import threading
from http.server import ThreadingHTTPServer

import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_loaner_workspace_matches_reference_and_supports_mobile_layout():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'meta?.table !== "loaner_devices"' in app
    assert 'let ayecLoanerDevices = [];' in app
    assert 'data-loaner-view="depot"' in app
    assert 'data-loaner-view="overdue"' in app
    assert 'loaner_transactions?limit=500' in app
    assert 'id="loanerMetricAvailable"' in app
    assert 'id="loanerSmsEnabled"' in app
    assert "const buttons = $$('.loaner-ref-tabs [data-loaner-view]')" in app
    assert "$$('.loaner-ref-tabs [data-loaner-view]').forEach" in app
    assert "loaner-ref-tabs" in styles
    assert "loaner-ref-table" in styles
    assert "loaner-ref-category-layout" in styles
    assert '@media print{body[data-page="loaners"]' in styles
    assert 'data-loaner-row-action="return"' in app
    assert 'if (page !== "loaners" || !ayecContextMenuEnabled("loaners")) return;' in app
    assert 'loaners:"rc_loaner"' in app
    assert 'class="loaner-ref-actions"' in app
    assert ".loaner-ref-actions{display:flex" in styles
    assert 'data-loaner-page="1"' in app
    assert "@media(max-width:600px){.loaner-ref-metrics" in styles
    assert "@media(max-width:420px){.loaner-ref-metrics" in styles


def test_loaner_context_menu_supports_touch_long_press_and_movement_cancel():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index('document.addEventListener("pointerdown", event => {', app.index('document.addEventListener("contextmenu", event => {'))
    end = app.index('document.addEventListener("dblclick", event => {', start)
    block = app[start:end]

    assert 'event.pointerType === "mouse"' in block
    assert 'ayecContextMenuEnabled("loaners")' in block
    assert '}, 550);' in block
    assert 'Math.hypot(event.clientX - ayecLoanerContextPressOrigin.x, event.clientY - ayecLoanerContextPressOrigin.y) <= 10' in block
    assert 'document.addEventListener("pointerup", cancelAyecLoanerContextPress);' in block
    assert 'document.addEventListener("pointercancel", cancelAyecLoanerContextPress);' in block


def test_loaner_desktop_metrics_and_full_width_workspace_match_desktop_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="loaners"] .loaner-ref-metrics article' in styles
    assert "height: 84px;" in styles
    assert "min-height: 438px;" in styles
    assert "grid-template-columns: minmax(0, 1fr) 370px 125px;" in styles
    assert 'body[data-page="loaners"] .loaner-ref-category-filter button.active' in styles
    assert "@media (max-width: 760px)" in styles


def test_logistics_workspace_uses_real_tracking_fields_and_mobile_cards():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'meta?.table !== "logistics"' in app
    assert 'id="logisticsMetricTotal"' in app
    assert 'id="logisticsStatus"' in app
    assert 'id="logisticsCarrier"' in app
    assert 'id="genericHost" hidden' in app
    assert 'row.cargo_firm' in app
    assert 'row.tracking_no' in app
    assert "@media(max-width:760px){.logistics-ref-table" in styles
    assert '@media print{body[data-page="logistics"]' in styles


def test_logistics_month_filter_accepts_iso_and_localized_dates():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "function ayecLogisticsMonthMatches(dateValue, month)" in app
    assert 'value.match(/^(\\d{4})-(\\d{2})/)' in app
    assert 'value.match(/^(\\d{1,2})[./-](\\d{1,2})[./-](\\d{4})/)' in app
    assert "ayecLogisticsMonthMatches(row.date, month)" in app


def test_logistics_print_actions_build_row_or_filtered_manifest():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "function ayecLogisticsFilteredRows()" in app
    assert "function ayecPrintLogisticsManifest(records)" in app
    assert 'row ? [row] : ayecLogisticsFilteredRows()' in app
    assert 'event.target.closest("[data-logistics-print-all]")' in app
    assert 'popup.document.write(' in app
    manifest = app[app.index("function ayecPrintLogisticsManifest"):app.index("function ayecLogisticsRender")]
    assert "popup.print()" in manifest
    assert "window.print()" not in manifest
    assert 'const records = ayecLogisticsFilteredRows();' in app
    assert 'if (!records.length) { toast("Dis aktarilacak kayit bulunamadi.", "warning"); return; }' in app
    assert 'download("lojistik-takip-" + today() + ".csv", records)' in app


def test_loaner_actions_and_category_filters_are_wired():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'data-loaner-action="return-selected"' in app
    assert 'data-loaner-type="Switch"' in app
    assert 'data-loaner-select-all' in app
    assert 'loanerMetricOverdueDetail' in app


def test_loaner_context_menu_and_atomic_return_match_desktop_workflow():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "loaner_devices_page.py").read_text(encoding="utf-8")
    assert 'data-loaner-kind="depot"' in app
    assert 'data-loaner-kind="transaction"' in app
    assert '"delete-device"' in app
    assert '[\"active\", \"overdue\"]' in app and '\"return\"' in app
    assert 'data-loaner-context="gallery"' not in app
    inventory_start = desktop.index("def open_inventory_context_menu(self, position):")
    active_start = desktop.index("def open_active_context_menu(self, position):", inventory_start)
    active_end = desktop.index("def _handle_inventory_double_click", active_start)
    inventory_menu = desktop[inventory_start:active_start]
    active_menu = desktop[active_start:active_end]
    assert 'menu.addAction("\u2795 Yeni Cihaz Ekle", self.add_new_device)' in inventory_menu
    assert 'menu.addAction("\U0001f504 Yenile", self.refresh_data)' in inventory_menu
    assert 'menu.addAction("\U0001f4e4 Cihaz\u0131 Zimmetle"' in inventory_menu
    assert 'menu.addAction("\U0001f5d1\ufe0f Cihaz\u0131 Sil"' in inventory_menu
    assert inventory_menu.count("menu.addSeparator()") == 1
    assert '"\U0001f4e5 Cihaz\u0131 \u0130ade Al"' in active_menu
    assert active_menu.count("menu.addSeparator()") == 1
    web_menu = app[app.index('const actions = kind === "depot"'):app.index('menu.style.left = Math.max(8', app.index('const actions = kind === "depot"'))]
    assert r'"\u2795 Yeni Cihaz Ekle"' in web_menu
    assert r'"\ud83d\udd04 Yenile"' in web_menu
    assert r'"\ud83d\udce4 Cihaz\u0131 Zimmetle"' in web_menu
    assert r'"\ud83d\uddd1\ufe0f Cihaz\u0131 Sil"' in web_menu
    assert 'action === "separator" ? \'<hr class="context-menu-separator">\'' in web_menu
    assert r'"\ud83d\udce5 Cihaz\u0131 \u0130ade Al"' in web_menu
    assert '"/api/desktop/loaners/return"' in app
    route = backend[backend.index('if path == "/api/desktop/loaners/return":'):]
    route = route[:route.index('if path == "/api/desktop/personnel/daily-wages/delete":')]
    assert 'UPDATE loaner_transactions SET date_returned=?, condition_in=?, penalty_applied=?, status=? WHERE id=?' in route
    assert 'UPDATE loaner_devices SET status=? WHERE id=?' in route
    assert 'conn.rollback()' in route


def test_loaner_assignment_dialog_preserves_desktop_fields_and_submit_workflow():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "loaner_devices_page.py").read_text(encoding="utf-8")
    desktop_start = desktop.index("def assign_device(self, dev_id):")
    desktop_end = desktop.index("def _save_assignment", desktop_start)
    desktop_form = desktop[desktop_start:desktop_end]
    assert 'ModernDialog("M\u00fc\u015fteriye Tesis Et (Zimmetle)"' in desktop_form
    for field in ("f_name", "f_phone", "f_track", "f_cond", "f_date"):
        assert field in desktop_form
    assert "QDateTime.currentDateTime().addDays(3)" in desktop_form
    assert 'form.addRow("Beklenen \u0130ade Tarihi:", f_date)' in desktop_form
    web_start = app.index("function ayecLoanerAssignDialog(row)")
    web_end = app.index("function ayecLoanerReturnDialog(row)", web_start)
    web_form = app[web_start:web_end]
    for field in ("customer_name", "customer_phone", "tracking_no", "condition_out", "expected_return"):
        assert 'name="' + field + '"' in web_form
    assert 'type="datetime-local"' in web_form
    assert 'Date.now() + 3 * 86400000' in web_form
    assert '"/api/desktop/loaners/assign"' in web_form
    assert 'if (action === "assign") {\n    ayecLoanerAssignDialog(row);' in app
    assert 'if (action.dataset.loanerRowAction === "assign") { ayecLoanerAssignDialog(row); return; }' in app


def test_loaner_device_forms_and_new_loan_selector_match_desktop_fields():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "loaner_devices_page.py").read_text(encoding="utf-8")
    add_start = desktop.index("def add_new_device(self):")
    add_end = desktop.index("def _save_device", add_start)
    desktop_add = desktop[add_start:add_end]
    edit_start = desktop.index("def edit_device(self, dev_id):")
    edit_end = desktop.index("def _update_device", edit_start)
    desktop_edit = desktop[edit_start:edit_end]
    for field_label in ("Cihaz Tipi:", "Marka & Model:", "Seri / MAC No:", "Raf No:", "Demirba\u015f Notu:"):
        assert field_label in desktop_add and field_label in desktop_edit
    assert 'QLineEdit("50.0")' in desktop_add
    assert "notes_w.setMinimumHeight(100)" in desktop_add
    assert "self._save_device" in desktop_add
    assert "self._update_device" in desktop_edit
    device_start = app.index("function ayecLoanerDeviceDialog(row = {})")
    device_end = app.index("function ayecLoanerAssignDialog(row)", device_start)
    web_device = app[device_start:device_end]
    for field in ("device_type", "brand_model", "serial_mac", "shelf_no", "daily_penalty_fee", "notes"):
        assert 'name="' + field + '"' in web_device
    assert '"Ak\\u0131ll\\u0131 Telefon", "Diz\\u00fcst\\u00fc Bilgisayar", "Tablet", "Router/Modem", "Yedek Par\\u00e7a", "Di\\u011fer"' in web_device
    assert 'daily_penalty_fee ?? "50.0"' in web_device
    assert 'payload._action = "update"' in web_device
    assert '"/api/desktop/table/loaner_devices"' in web_device
    assert 'data-generic-add' in app and 'ayecLoanerStartNewLoan();' in app
    assert 'loaner_transactions?limit=1000' in app
    assert 'item.status || ""' in app and 'item.status || "Depoda"' in app
    assert '"Teslim Bilgileri"' in app


def test_authenticated_offscreen_loaner_search_shortcut_matches_desktop(monkeypatch, tmp_path):
    desktop = (ROOT / "src" / "ui" / "pages" / "loaner_devices_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'QShortcut(QKeySequence("Ctrl+F"), self)' in desktop
    assert "self.loaner_search_shortcut.activated.connect(self._focus_loaner_search)" in desktop
    assert '(page !== "loaners" && page !== "report-templates")' in app
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        env = os.environ.copy()
        env["AYEC_AUDIT_URL"] = f"{base_url}/"
        env["AYEC_LOANER_SESSION_COOKIE"] = session.cookies.get("ayec_session")
        env["AYEC_AUDIT_CDP_PORT"] = "9262"
        audit = subprocess.run(
            ["node", "tools/quality/loaner_keyboard_offscreen.cjs"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        assert '"focused":true' in audit.stdout
        assert '"selected":true' in audit.stdout
        assert '"prevented":true' in audit.stdout
        assert '"role":"Admin"' in audit.stdout
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_contract_ctrl_k_targets_page_search_before_global_search(monkeypatch, tmp_path):
    desktop = (ROOT / "src" / "ui" / "pages" / "contracts_page.py").read_text(encoding="utf-8")
    script = (WEB / "global-search-reference.js").read_text(encoding="utf-8")
    assert 'QShortcut(QKeySequence("Ctrl+K"), self)' in desktop
    assert 'self.contract_search_shortcut.activated.connect(self.contract_search.setFocus)' in desktop
    assert 'page==="contracts"?document.querySelector("#genericSearch")' in script and 'pageSearch.select()' in script
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        env = os.environ.copy()
        env["AYEC_AUDIT_URL"] = f"{base_url}/"
        env["AYEC_LOANER_SESSION_COOKIE"] = session.cookies.get("ayec_session")
        env["AYEC_KEYBOARD_PAGE"] = "contracts"
        env["AYEC_KEYBOARD_KEY"] = "k"
        env["AYEC_AUDIT_CDP_PORT"] = "9263"
        audit = subprocess.run(
            ["node", "tools/quality/loaner_keyboard_offscreen.cjs"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        assert '"focused":true' in audit.stdout
        assert '"selected":true' in audit.stdout
        assert '"paletteOpen":false' in audit.stdout
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_report_templates_ctrl_f_focuses_its_search_in_hidden_edge(monkeypatch, tmp_path):
    desktop = (ROOT / "src" / "ui" / "pages" / "report_templates_page.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'QShortcut(QKeySequence("Ctrl+F"), self)' in desktop
    assert "self.search_shortcut.activated.connect(self.search.setFocus)" in desktop
    assert 'page !== "report-templates"' in app
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        env = os.environ.copy()
        env["AYEC_AUDIT_URL"] = f"{base_url}/"
        env["AYEC_LOANER_SESSION_COOKIE"] = session.cookies.get("ayec_session")
        env["AYEC_KEYBOARD_PAGE"] = "report-templates"
        env["AYEC_KEYBOARD_KEY"] = "f"
        env["AYEC_AUDIT_CDP_PORT"] = "9264"
        audit = subprocess.run(
            ["node", "tools/quality/loaner_keyboard_offscreen.cjs"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        assert '"focused":true' in audit.stdout
        assert '"selected":true' in audit.stdout
        assert '"prevented":true' in audit.stdout
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_customer_ctrl_k_focuses_customer_filter_before_global_search(monkeypatch, tmp_path):
    desktop = (ROOT / "src" / "ui" / "pages" / "_customers_base_mixin.py").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    global_search = (WEB / "global-search-reference.js").read_text(encoding="utf-8")
    assert 'QShortcut(QKeySequence("Ctrl+K"), self)' in desktop
    assert "self.search_shortcut.activated.connect(self._focus_customer_search)" in desktop
    assert 'id="customerSearch"' in app
    assert 'page==="customers"?document.querySelector("#customerSearch")' in global_search
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        env = os.environ.copy()
        env["AYEC_AUDIT_URL"] = f"{base_url}/"
        env["AYEC_LOANER_SESSION_COOKIE"] = session.cookies.get("ayec_session")
        env["AYEC_KEYBOARD_PAGE"] = "customers"
        env["AYEC_KEYBOARD_KEY"] = "k"
        env["AYEC_KEYBOARD_INPUT"] = "customerSearch"
        env["AYEC_AUDIT_CDP_PORT"] = "9265"
        audit = subprocess.run(
            ["node", "tools/quality/loaner_keyboard_offscreen.cjs"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        assert '"focused":true' in audit.stdout
        assert '"selected":true' in audit.stdout
        assert '"paletteOpen":false' in audit.stdout
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
