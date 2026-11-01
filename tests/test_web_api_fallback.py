from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import subprocess
import sys
import threading

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_unknown_api_path_returns_json_not_single_page_app(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        status = session.get(f"{base_url}/api/auth/status")
        assert status.status_code == 200
        assert status.headers["Content-Type"].startswith("application/json")
        assert status.json()["authenticated"] is False
        empty_login = session.post(f"{base_url}/api/auth/login", json={})
        assert empty_login.status_code == 400
        assert empty_login.headers["Content-Type"].startswith("application/json")
        assert empty_login.json() == {"error": "Kullan\u0131c\u0131 ad\u0131 ve parola gereklidir."}
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123"},
        )
        assert login.status_code == 200
        response = session.get(f"{base_url}/api/auth/not-a-route")
        assert response.status_code == 404
        assert response.headers["Content-Type"].startswith("application/json")
        assert response.json() == {"error": "API endpoint not found"}
        unknown_post = session.post(f"{base_url}/api/auth/not-a-route", json={})
        assert unknown_post.status_code == 404
        assert unknown_post.headers["Content-Type"].startswith("application/json")
        assert unknown_post.json() == {"error": "Endpoint bulunamad\u0131"}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_api_client_retries_html_once_for_get_and_never_retries_writes():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    match = re.search(r"^async function apiFetch\(.*$", app, re.MULTILINE)
    assert match is not None
    harness = r'''const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(0, "utf8");
function response(status, body) {
  return { status, ok: status >= 200 && status < 300, text: async () => body };
}
function createClient(bodies) {
  const calls = [];
  const context = {
    URL,
    setTimeout,
    location: { href: "https://example.test/#login" },
    window: {},
    ayecFiscalArchiveHeaders: () => ({}),
    fetch: async (path, options) => {
      calls.push({ path, cache: options.cache, method: options.method || "GET" });
      return response(200, bodies.shift());
    }
  };
  vm.runInNewContext(`${source}\nglobalThis.apiFetch = apiFetch;`, context);
  return { calls, apiFetch: context.apiFetch };
}
(async () => {
  const get = createClient(["<!doctype html><title>Fallback</title>", "{\"authenticated\":false}"]);
  const status = await get.apiFetch("/api/auth/status");
  assert.equal(status.authenticated, false);
  assert.deepEqual(get.calls.map(call => call.cache), ["no-store", "reload"]);
  assert.deepEqual(get.calls.map(call => call.method), ["GET", "GET"]);

  const post = createClient(["<!doctype html><title>Private IIS fallback</title>"]);
  await assert.rejects(
    post.apiFetch("/api/auth/login", { method: "POST", body: "{}" }),
    error => {
      assert.match(error.message, /(?=.*\/api\/auth\/login)(?=.*server-windows-install\.ps1)/);
      assert.doesNotMatch(error.message, /Private IIS fallback|<!doctype|<html/i);
      return true;
    }
  );
  assert.equal(post.calls.length, 1);
  assert.equal(post.calls[0].cache, "no-store");
  assert.equal(post.calls[0].method, "POST");
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=match.group(0),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_auth_status_warns_when_frontend_and_server_builds_do_not_match():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function authBuildCompatibilityWarning(serverBuildId){")
    end = app.index("\n}", start) + 2
    helper = app[start:end]
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
const context = {
  URL,
  location: { href: "https://panel.example.test/#login" },
  document: { scripts: [{ src: "https://panel.example.test/app.js?v=web-build-2" }] }
};
vm.runInNewContext(`${source}\nglobalThis.check = authBuildCompatibilityWarning;`, context);
assert.equal(context.check("web-build-2"), "");
assert.match(context.check("web-build-1"), /web-build-2.*web-build-1/);
assert.match(context.check(""), /Sunucu/);
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=helper,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_login_is_blocked_before_credentials_are_sent_to_mismatched_server():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert app.count("const compatibility=authBuildCompatibilityWarning(priorStatus?.app_build_id);") == 2
    login_positions = [match.start() for match in re.finditer(r'const result=await apiFetch\("/api/auth/login"', app)]
    assert len(login_positions) == 2
    for login in login_positions:
        handler_start = app.rfind("const priorStatus=await apiFetch(\"/api/auth/status\")", 0, login)
        assert handler_start >= 0
        preflight = app[handler_start:login]
        assert "const compatibility=authBuildCompatibilityWarning(priorStatus?.app_build_id);" in preflight
        assert "if(compatibility){authCompatibilityMessage=compatibility;throw Error(compatibility)}" in preflight



def test_authenticated_legacy_backend_shows_login_compatibility_gate():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function initializeAuth(){")
    end = app.index("\nwindow.handleUnauthorized", start)
    initialize_auth = app[start:end]
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
const loginViews = [];
const context = {
  URLSearchParams,
  window: { location: { search: "" }, ayecApplicationReady: true },
  apiFetch: async () => ({ authenticated: true, app_build_id: "", user: { username: "legacy-user" } }),
  authBuildCompatibilityWarning: () => "Server package mismatch",
  renderPasswordReset() { throw new Error("Unexpected password reset"); },
  renderWizard() { throw new Error("Unexpected setup wizard"); },
  renderLogin(message, identifier, type) { loginViews.push({ message, identifier, type }); },
  completeAuthenticatedLogin() { throw new Error("Mismatched backend reached the app shell"); },
  applicationStarted: true,
  currentAuthUser: { username: "legacy-user" }
};
vm.runInNewContext(`${source}\nglobalThis.run = initializeAuth;`, context);
(async () => {
  const result = await context.run();
  assert.equal(result, false);
  assert.equal(context.applicationStarted, false);
  assert.equal(context.currentAuthUser, null);
  assert.equal(context.window.ayecApplicationReady, false);
  assert.deepEqual(loginViews[0], { message: "Server package mismatch", identifier: "legacy-user", type: "warning" });
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=initialize_auth,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_authenticated_startup_failure_keeps_session_and_allows_retry():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function completeAuthenticatedLogin(result,identifier=")
    end = app.index("\nfunction renderLogin(", start)
    helpers = app[start:end]
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
let attempts = 0;
let loginRenders = 0;
let hidden = 0;
let authMarkup = "";
const toasts = [];
const retry = { disabled: false };
const logout = { disabled: false };
const context = {
  currentAuthUser: null,
  applicationStarted: true,
  window: {},
  updateCurrentUser: null,
  hideAuth() { hidden += 1; },
  startApplication: async () => { attempts += 1; if (attempts === 1) throw Error("API endpoint returned HTML"); },
  renderLogin() { loginRenders += 1; },
  renderLicenseActivation() { throw Error("Unexpected license activation route"); },
  showAuth(markup) { authMarkup = markup; },
  authAlert(message, type) { return `<div class="auth-alert ${type}">${String(message)}</div>`; },
  esc(value) { return String(value); },
  $(selector) { return selector === "#authStartupRetry" ? retry : selector === "#authStartupLogout" ? logout : null; },
  toast(message, type) { toasts.push({ message, type }); },
  apiFetch: async () => ({ ok: true })
};
context.updateCurrentUser = user => { context.currentAuthUser = user; };
context.__retry = retry;
context.__logout = logout;
vm.runInNewContext(`${source}\nglobalThis.run = completeAuthenticatedLogin; globalThis.startupError = renderAuthenticatedStartupError; globalThis.retryAction = () => globalThis.__retry.onclick(); globalThis.logoutAction = () => globalThis.__logout.onclick();`, context);
(async () => {
  const accepted = await context.run({ user: { username: "demo", full_name: "Demo" } }, "demo");
  assert.equal(accepted, false);
  assert.equal(context.currentAuthUser.username, "demo");
  assert.equal(loginRenders, 0);
  assert.match(authMarkup, /authStartupRetry/);
  assert.match(authMarkup, /authStartupLogout/);
  assert.equal(typeof retry.onclick, "function");
  await context.retryAction();
  assert.equal(attempts, 2);
  assert.equal(hidden, 1);
  assert.equal(context.currentAuthUser.username, "demo");
  assert.equal(toasts.length, 1);
  context.startupError(Error("API endpoint returned HTML"), "demo");
  await context.logoutAction();
  assert.equal(context.currentAuthUser, null);
  assert.equal(context.applicationStarted, false);
  assert.equal(context.window.ayecApplicationReady, false);
  assert.equal(loginRenders, 1);
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=helpers,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout


def test_binary_downloads_reject_200_html_and_json_api_fallbacks():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function assertDownloadResponse(response){")
    end = app.index("\n}", start) + 2
    helper = app[start:end]
    assert app.count("assertDownloadResponse(response);const blob=await response.blob()") == 12
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
const context = { URL, location: { href: "https://example.test/#login" } };
vm.runInNewContext(`${source}\nglobalThis.check = assertDownloadResponse;`, context);
const response = (type, status = 200) => ({ status, url: "https://example.test/api/desktop/export", headers: { get: () => type } });
assert.throws(() => context.check(response("text/html")), /web/);
assert.throws(() => context.check(response("application/json")), /JSON/);
assert.throws(() => context.check(response("application/problem+json")), /JSON/);
assert.equal(context.check(response("application/pdf")), undefined);
assert.equal(context.check(response("text/csv; charset=utf-8")), undefined);
'''
    result = subprocess.run(["node", "-e", harness], input=helper, check=False, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr or result.stdout


def test_existing_authenticated_session_uses_startup_recovery_flow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    login_start = app.index("async function completeAuthenticatedLogin(result,identifier=")
    login_end = app.index("\nasync function recoverAuthenticatedLoginRedirect", login_start)
    error_start = app.index("function renderAuthenticatedStartupError(error,identifier=")
    error_end = app.index("\nfunction renderLogin(", error_start)
    initialize_start = app.index("async function initializeAuth(){")
    initialize_end = app.index("\nwindow.handleUnauthorized", initialize_start)
    startup = "\n".join((app[login_start:login_end], app[error_start:error_end], app[initialize_start:initialize_end]))
    harness = r'''const assert = require("node:assert/strict");
const vm = require("node:vm");
const source = require("node:fs").readFileSync(0, "utf8");
const status = { authenticated: true, user: { username: "demo" } };
let startAttempts = 0;
let hidden = 0;
let loginRenders = 0;
let authMarkup = "";
let currentAuthUser = null;
const retry = { disabled: false };
const logout = { disabled: false };
const context = {
  URLSearchParams,
  window: { location: { search: "" }, ayecApplicationReady: false },
  authCompatibilityMessage: "",
  get currentAuthUser() { return currentAuthUser; },
  applicationStarted: false,
  apiFetch: async () => status,
  authBuildCompatibilityWarning: () => "",
  updateCurrentUser(user) { currentAuthUser = user; },
  hideAuth() { hidden += 1; },
  startApplication: async () => { startAttempts += 1; if (startAttempts === 1) throw Error("API endpoint returned HTML"); },
  renderWizard() {},
  renderLogin() { loginRenders += 1; },
  renderLicenseActivation() { throw Error("Unexpected license activation route"); },
  showAuth(markup) { authMarkup = markup; },
  authAlert(message, type) { return `<div class="auth-alert ${type}">${String(message)}</div>`; },
  esc(value) { return String(value); },
  toast() {},
  $(selector) { return selector === "#authStartupRetry" ? retry : selector === "#authStartupLogout" ? logout : null; }
};
vm.runInNewContext(`${source}\nglobalThis.run = initializeAuth; globalThis.retryAction = () => globalThis.__retry.onclick();`, context);
context.__retry = retry;
(async () => {
  await context.run();
  assert.equal(startAttempts, 1);
  assert.equal(hidden, 0);
  assert.equal(context.currentAuthUser.username, "demo");
  assert.match(authMarkup, /authStartupRetry/);
  assert.match(authMarkup, /authStartupLogout/);
  assert.equal(loginRenders, 0);
  await context.retryAction();
  assert.equal(startAttempts, 2);
  assert.equal(hidden, 1);
  assert.equal(context.currentAuthUser.username, "demo");
  assert.equal(loginRenders, 0);
})().catch(error => { console.error(error); process.exitCode = 1; });
'''
    result = subprocess.run(
        ["node", "-e", harness],
        input=startup,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert result.returncode == 0, result.stderr or result.stdout



def test_auth_boot_gate_hides_dashboard_until_session_verification_finishes():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    html = (root / "index.html").read_text(encoding="utf-8")
    app = (root / "app.js").read_text(encoding="utf-8")
    styles = (root / "styles.css").read_text(encoding="utf-8")
    assert '<div id="authRoot" class="auth-root" aria-live="polite">' in html
    assert 'class="auth-boot-status" role="status">Oturum kontrol ediliyor...</div>' in html
    assert "app.js?v=20261029-auth-boot-gate-1" in html
    start = app.index("async function completeAuthenticatedLogin(result,identifier=")
    end = app.index("\nasync function recoverAuthenticatedLoginRedirect", start)
    startup = app[start:end]
    assert startup.index("await startApplication()") < startup.index("hideAuth()")
    assert ".auth-boot-status" in styles
