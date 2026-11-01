from pathlib import Path
import shutil
import socket
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import time
import urllib.request
import zipfile

import pytest

from Web_Arayuzu.check_public_deployment import expected_app_key, probe_public_deployment
from Web_Arayuzu.tools.build_deployment_bundle import should_include


ROOT = Path(__file__).resolve().parents[1] / "Web_Arayuzu"


def test_iis_asset_publisher_copies_files_preserves_uploads_and_backs_up_overwrites(tmp_path):
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is required to exercise the IIS asset publisher.")

    source = tmp_path / "source-web"
    site = tmp_path / "iis-root"
    backup = tmp_path / "backup"
    (source / "uploads").mkdir(parents=True)
    (site / "uploads").mkdir(parents=True)
    (source / "index.html").write_text("new index", encoding="ascii")
    (source / "app.js").write_text("new app", encoding="ascii")
    (source / "uploads" / "tenant.bin").write_bytes(b"package upload")
    (site / "index.html").write_text("old index", encoding="ascii")
    (site / "obsolete.js").write_text("keep existing site files", encoding="ascii")
    (site / "uploads" / "tenant.bin").write_bytes(b"production upload")

    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "tools" / "publish_iis_web_assets.ps1"),
            "-SourceRoot",
            str(source),
            "-SiteRoot",
            str(site),
            "-BackupRoot",
            str(backup),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout.strip().endswith("2")
    assert (site / "index.html").read_text(encoding="ascii") == "new index"
    assert (site / "app.js").read_text(encoding="ascii") == "new app"
    assert (site / "obsolete.js").read_text(encoding="ascii") == "keep existing site files"
    assert (site / "uploads" / "tenant.bin").read_bytes() == b"production upload"
    assert (backup / "index.html").read_text(encoding="ascii") == "old index"


def test_deployment_bundle_excludes_private_signing_key_material():
    for filename in (
        "config/license-signing-key.pem",
        "config/private-key.pem",
        "config/private.key",
        "config/certificate.p12",
        "config/certificate.pfx",
        "id_rsa",
        "id_ed25519",
    ):
        assert should_include(Path(filename)) is False


def test_server_deployment_bundle_has_required_files_and_persistent_mounts():
    for filename in ("Dockerfile", "docker-compose.yml", ".env.example", "DEPLOYMENT.md"):
        assert (ROOT / filename).is_file()
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    deployment = (ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    windows_installer = (ROOT / "server-windows-install.ps1").read_text(encoding="utf-8")
    windows_start = (ROOT / "server-windows-start.ps1").read_text(encoding="utf-8")
    ayec_start = (ROOT / "AYEC_START.ps1").read_text(encoding="utf-8")
    asset_publisher = (ROOT / "tools" / "publish_iis_web_assets.ps1").read_text(encoding="utf-8")
    assert '"${AYEC_PORT:-8501}:8501"' in compose
    assert "./data:/data" in compose
    assert "./Kullan" in compose
    assert "./web/uploads:/app/web/uploads" in compose
    assert ".env" in ignore and "data" in ignore and "web/uploads" in ignore
    assert "backups" in ignore and "support_backups" in ignore and "Kullan*" in ignore
    assert "docker compose config --quiet" in deployment
    assert "docker compose build ayec-web" in deployment
    assert "docker compose up -d ayec-web" in deployment
    assert "private signing key" in deployment
    assert "$expectedAppScript" in windows_installer
    assert '$sourceWebRoot = Join-Path $ProjectPath "web"' in windows_installer
    assert '$assetPublisher = Join-Path $ProjectPath "tools\\publish_iis_web_assets.ps1"' in windows_installer
    assert '$publishedFileCount = & $assetPublisher -SourceRoot $sourceWebRoot -SiteRoot $siteRoot -BackupRoot $webBackupRoot' in windows_installer
    assert '$targetPath = Join-Path $siteFullPath $relativePath' in asset_publisher
    assert "Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetPath -Force" in asset_publisher
    assert "-notmatch '(^|[\\\\/])uploads([\\\\/]|$)'" in asset_publisher
    assert "web/uploads is preserved" in windows_installer
    assert '$ErrorActionPreference = "Continue"' in windows_start
    assert '$PSNativeCommandUseErrorActionPreference = $false' in windows_start
    assert '2>> $ErrorLog' in windows_start
    assert 'Start-ScheduledTask -TaskName $taskName' in ayec_start
    assert 'Start-Process -FilePath "powershell.exe"' in ayec_start
    assert '-WindowStyle Hidden' in ayec_start
    assert 'api/desktop/health' in ayec_start
    assert 'Stop-OwnedServerListener' in ayec_start
    assert 'AYEC_ADMIN_RESET_PASSWORD' not in ayec_start
    assert 'Read-Host "AYEC Admin password' not in ayec_start
    assert 'task points to another project folder' in ayec_start
    assert 'api/auth/status' in ayec_start
    assert 'running API version does not match this package' in ayec_start
    assert 'server-windows-install.ps1 as Administrator' in ayec_start
    assert '$webBackupRoot = Join-Path $env:ProgramData' in windows_installer
    assert "app\\.js\\?v=([A-Za-z0-9._-]+)" in windows_installer
    assert '$appResponse.ContentType -match "javascript"' in windows_installer
    assert 'Content.Contains("allowHtmlRetry")' in windows_installer
    assert '[string]$IisHostName = "panel.ayecpro.com"' in windows_installer
    assert 'Get-Website -Name $IisSiteName' in windows_installer
    assert 'Invoke-IisLocalGet -Uri $publicSiteUrl -HostName $IisHostName' in windows_installer
    assert '$deploymentProbe = Join-Path $ProjectPath "check_public_deployment.py"' in windows_installer
    assert '$deploymentProbe --base-url "http://127.0.0.1"' in windows_installer
    assert "--host-header $IisHostName" in windows_installer
    assert "-IisHostName your.host" in deployment
    assert '-IisSiteName "Your IIS Site"' in deployment
    assert "--check-login-post" in windows_installer
    assert 'Write-Host "IIS deployment probe diagnostics:"' in windows_installer
    assert "Write-Host $probeOutput" in windows_installer
    assert "unauthenticated profile/login results above" in windows_installer
    assert '$template = Get-Content -LiteralPath (Join-Path $ProjectPath "iis\\web.config") -Raw' in windows_installer
    assert '$template.Replace("__AYEC_BACKEND_PORT__", "$BackendPort") | Set-Content -LiteralPath $webConfig' in windows_installer
    assert '& iisreset.exe /restart' in windows_installer


def test_clean_server_bundle_contains_runtime_and_excludes_local_state(tmp_path):
    output = tmp_path / "AYEC_Pro_Web_Server.zip"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_deployment_bundle.py"), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )

    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        bundled_index = archive.read("Web_Arayuzu/web/index.html").decode("utf-8")
        bundled_app = archive.read("Web_Arayuzu/web/app.js").decode("utf-8")
        bundled_main = archive.read("Web_Arayuzu/Main.py").decode("utf-8")
        bundled_probe = archive.read("Web_Arayuzu/check_public_deployment.py").decode("utf-8")
        bundled_voice = archive.read("Web_Arayuzu/web/voice-command-reference.js").decode("utf-8")
        bundled_project_css = archive.read("Web_Arayuzu/web/project-list-parity.css").decode("utf-8")
        bundled_report_templates = archive.read("Web_Arayuzu/web/report-templates.js").decode("utf-8")
        bundled_iis_config = archive.read("Web_Arayuzu/iis/web.config").decode("utf-8")

    assert "Web_Arayuzu/Dockerfile" in names
    assert "Web_Arayuzu/.env.example" in names
    assert "Web_Arayuzu/check_public_deployment.py" in names
    assert "Web_Arayuzu/CHECK_PUBLIC_DEPLOYMENT.cmd" in names
    assert "Web_Arayuzu/AYEC_START.cmd" in names
    assert "Web_Arayuzu/AYEC_START.ps1" in names
    assert "Web_Arayuzu/server-windows-install.ps1" in names
    assert "Web_Arayuzu/server-windows-start.ps1" in names
    assert "Web_Arayuzu/CONFIGURE_GOOGLE_SIGNIN.cmd" in names
    assert "Web_Arayuzu/tools/configure_google_oauth.py" in names
    assert "Web_Arayuzu/tools/diagnose_server_502.ps1" in names
    assert "Web_Arayuzu/src/__init__.py" in names
    assert "Web_Arayuzu/src/database.py" in names
    assert "Web_Arayuzu/src/utils/finance_manager.py" in names
    assert "Web_Arayuzu/RESET_ADMIN_PASSWORD.ps1" in names
    for filename in (
        "BACKUP_BEFORE_WIPE.cmd",
        "BACKUP_BEFORE_WIPE.ps1",
        "CHECK_ADMIN_LOGIN.cmd",
        "CHECK_ADMIN_LOGIN.ps1",
        "CLEAN_INSTALL.cmd",
        "CLEAN_INSTALL.ps1",
        "CLEANUP_SERVER.ps1",
        "FIX_ADMIN_LOGIN.cmd",
        "FIX_ADMIN_LOGIN.ps1",
        "ONE_CLICK_CLEAN_INSTALL.cmd",
        "ONE_CLICK_CLEAN_INSTALL.ps1",
        "RESET_ADMIN_PASSWORD.cmd",
    ):
        assert f"Web_Arayuzu/{filename}" not in names
    assert "Web_Arayuzu/web/index.html" in names
    assert not any("/data/" in name or "/backups/" in name for name in names)
    assert not any("/output/" in name for name in names)
    assert not any("/node_modules/" in name for name in names)
    assert not any("/Kullan" in name or "/.venv" in name for name in names)
    assert not any(name.lower().endswith(".zip") for name in names)
    assert not any(name.endswith((".db", ".sqlite", ".sqlite3")) for name in names)
    assert bundled_index.replace("\r\n", "\n") == (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert bundled_app.replace("\r\n", "\n") == (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    assert 'app.js?v=' in bundled_index
    assert 'app.js?v=20261029-registration-onboarding-2' in bundled_index
    assert 'google-auth.js?v=20261029-registration-onboarding-2' in bundled_index
    assert 'report-templates.js?v=20261028-template-preview-title-parity-1' in bundled_index
    assert 'template-preview-meta' in bundled_report_templates
    assert 'class="job-report-description" title="' in bundled_app
    assert 'aria-label="\' + esc(row.fault_description || row.fault_category || "-")' in bundled_app
    assert 'project-list-parity.css?v=20261028-project-list-cards-1' in bundled_index
    assert ".p9-project-list-grid{display:grid;grid-template-columns:repeat(3,minmax(0,300px))" in bundled_project_css
    assert 'smart-home-sales-reference.js?v=20261027-smart-home-missing-rate-guard-1' in bundled_index
    assert 'manual-reference.js?v=20261027-manual-tabs-keyboard-ordered-nested-lists-1' in bundled_index
    assert 'styles.css?v=20261029-registration-onboarding-2' in bundled_index
    assert 'sales-draft-parity.js?v=20261027-offer-approval-draft-parity-1' in bundled_index
    assert 'midnight-reference.css?v=20261029-finance-detail-print-1' in bundled_index
    assert 'reminders-reference.js?v=20261028-reminder-tabs-roving-keyboard-1' in bundled_index
    assert 'stock-context-parity.js?v=20261027-stock-password-whitespace-1' in bundled_index
    assert 'audit-reference.js?v=20261028-audit-tabs-roving-keyboard-1' in bundled_index
    assert 'audit-reference.css?v=20261027-audit-total-count-parity-1' in bundled_index
    assert 'bulk-sales-selection.js?v=20261027-offer-edit-unit-price-parity-1' in bundled_index
    assert 'external-tracking-reference.js?v=20261026-export-session-guard-1' in bundled_index
    assert 'automotive-parity.js?v=20261026-web-parity-v111-1' in bundled_index
    assert 'settings-theme-reference.js?v=20261028-company-settings-tabs-keyboard-1' in bundled_index
    assert 'contracts-reference.js?v=20261026-contract-search-shortcut-1' in bundled_index
    assert 'customer-context-parity.js?v=20261027-isolated-customer-print-1' in bundled_index
    assert 'stock-movements-page.js?v=20261027-pdf-print-preview-2' in bundled_index
    assert 'brand-export-parity.js?v=20261027-filtered-pdf-print-1' in bundled_index
    assert 'product-groups.js?v=20261028-product-groups-page-fill-1' in bundled_index
    assert 'quick-sale-reference.css?v=20261026-quick-sale-customer-parity-1' in bundled_index
    assert 'quick-sale-reference.js?v=20261028-quick-sale-stale-customer-reconcile-1' in bundled_index
    assert 'stock-summary-navigation.js?v=20261027-stock-transfer-tab-parity-1' in bundled_index
    assert "Web_Arayuzu/web/customer-360-voice-reference.js" in names
    assert 'customer-360-voice-reference.js?v=20261026-assistant-help-browser-guards-1' in bundled_index
    assert 'voice-command-reference.js?v=20261026-voice-query-parity-2' in bundled_index
    assert '"assistant_help","voice_help_next"' in bundled_voice
    assert 'cache:options.cache==="reload"?"reload":"no-store"' in bundled_app
    assert "allowHtmlRetry" in bundled_app
    assert 'if not user:\n                    return self.send_json({"error": "Authentication required"}, 401)' in bundled_main.replace("\r\n", "\n")
    assert 'if not identifier or not password:' in bundled_main
    assert 'api_login_rejects_empty_credentials' in bundled_probe
    assert 'api_post_missing_require_user' in bundled_probe
    assert 'api_build_matches' in bundled_probe
    assert 'api_bootstrap_rejects_anonymous' in bundled_probe
    assert '<match url="(.*)" />' in bundled_iis_config
    assert 'url="http://127.0.0.1:__AYEC_BACKEND_PORT__/{R:1}"' in bundled_iis_config
    assert 'appendQueryString="true"' in bundled_iis_config


def test_offscreen_route_runner_can_start_an_extracted_server_bundle():
    runner = (ROOT.parent / "tools" / "quality" / "run_web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'process.env.AYEC_AUDIT_SERVER_ROOT' in runner
    assert 'path.join(serverRoot, "Main.py")' in runner
    assert 'cwd: serverCwd' in runner


def test_extracted_server_bundle_passes_public_deployment_probe(tmp_path):
    archive = tmp_path / "AYEC_Pro_Web_Server.zip"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "build_deployment_bundle.py"), "--output", str(archive)],
        check=True,
        capture_output=True,
        text=True,
    )
    with zipfile.ZipFile(archive) as package:
        package.extractall(tmp_path / "extracted")

    package_root = tmp_path / "extracted" / "Web_Arayuzu"
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    command = [
        sys.executable,
        str(package_root / "Main.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--db",
        str(tmp_path / "registry.db"),
        "--tenant-dir",
        str(tmp_path / "tenants"),
    ]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    process = subprocess.Popen(
        command,
        cwd=package_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    try:
        ready = False
        for _ in range(100):
            if process.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                    ready = response.status == 200
            except OSError:
                time.sleep(0.2)
            if ready:
                break
        assert ready, f"Packaged server did not start (exit={process.poll()})"
        result = probe_public_deployment(
            f"http://127.0.0.1:{port}",
            expected_app_key(ROOT / "web" / "index.html"),
            timeout=5,
            check_login_post=True,
        )
        assert result["ok"] is True, result
        assert result["api_build_matches"] is True, result
        assert result["api_build_id"] == expected_app_key(ROOT / "web" / "index.html")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_deployment_probe_honors_host_header_for_virtual_iis_site():
    app_key = "qa-host-build-key"
    hosts_seen = []
    post_headers_seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def _send(self, status, content_type, body):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            hosts_seen.append(self.headers.get("Host"))
            if self.path == "/":
                return self._send(200, "text/html", f'<script src="/app.js?v={app_key}"></script>')
            if self.path.startswith("/app.js?"):
                return self._send(200, "application/javascript", "window.apiFetch = function apiFetch() {};")
            if self.path.startswith("/api/auth/status"):
                return self._send(200, "application/json", f'{{"authenticated":false,"app_build_id":"{app_key}"}}')
            if self.path == "/api/desktop/bootstrap":
                return self._send(401, "application/json", '{"error":"Authentication required"}')
            return self._send(404, "application/json", '{"error":"Not found"}')

        def do_POST(self):
            hosts_seen.append(self.headers.get("Host"))
            post_headers_seen.append((self.headers.get("Origin"), self.headers.get("Referer")))
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            return self._send(401, "application/json", '{"error":"Authentication required"}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = probe_public_deployment(
            f"http://127.0.0.1:{server.server_port}",
            app_key,
            timeout=5,
            host_header="panel.ayecpro.com",
        )
        assert result["ok"] is True, result
        assert result["host"] == "panel.ayecpro.com"
        assert result["api_bootstrap_status"] == 401
        assert result["api_bootstrap_is_json"] is True
        assert result["api_bootstrap_rejects_anonymous"] is True
        assert hosts_seen == ["panel.ayecpro.com"] * 5
        assert post_headers_seen == [
            ("http://panel.ayecpro.com", "http://panel.ayecpro.com/#login")
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_deployment_probe_rejects_html_from_login_api(tmp_path):
    app_key = "qa-build-key"
    post_headers_seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def _send(self, status, content_type, body):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/":
                return self._send(200, "text/html", f'<script src="/app.js?v={app_key}"></script>')
            if self.path.startswith("/app.js?"):
                return self._send(200, "application/javascript", "window.apiFetch = function apiFetch() {};")
            if self.path.startswith("/api/auth/status"):
                return self._send(200, "application/json", f'{{"authenticated":false,"app_build_id":"{app_key}"}}')
            if self.path == "/api/desktop/bootstrap":
                return self._send(401, "application/json", '{"error":"Authentication required"}')
            return self._send(404, "application/json", '{"error":"Not found"}')

        def do_POST(self):
            post_headers_seen.append(
                (self.headers.get("Origin"), self.headers.get("Referer"))
            )
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.path == "/api/auth/profile":
                return self._send(401, "application/json", '{"error":"Authentication required"}')
            if self.path == "/api/auth/login":
                return self._send(200, "text/html", "<!doctype html><html><body>SPA fallback</body></html>")
            return self._send(404, "application/json", '{"error":"Not found"}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = probe_public_deployment(
            f"http://127.0.0.1:{server.server_port}",
            app_key,
            timeout=5,
            check_login_post=True,
        )
        assert result["api_login_status"] == 200
        assert result["api_login_content_type"] == "text/html"
        assert result["api_login_is_json"] is False
        assert result["ok"] is False
        assert post_headers_seen == [
            ("http://127.0.0.1:%s" % server.server_port, "http://127.0.0.1:%s/#login" % server.server_port),
            ("http://127.0.0.1:%s" % server.server_port, "http://127.0.0.1:%s/#login" % server.server_port),
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_deployment_probe_rejects_html_from_desktop_bootstrap():
    app_key = "qa-bootstrap-build-key"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format, *_args):
            return

        def _send(self, status, content_type, body):
            payload = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/":
                return self._send(200, "text/html", f'<script src="/app.js?v={app_key}"></script>')
            if self.path.startswith("/app.js?"):
                return self._send(200, "application/javascript", "window.apiFetch = function apiFetch() {};")
            if self.path.startswith("/api/auth/status"):
                return self._send(200, "application/json", f'{{"authenticated":false,"app_build_id":"{app_key}"}}')
            if self.path == "/api/desktop/bootstrap":
                return self._send(200, "text/html", "<!doctype html><html><body>SPA fallback</body></html>")
            return self._send(404, "application/json", '{"error":"Not found"}')

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            return self._send(401, "application/json", '{"error":"Authentication required"}')

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = probe_public_deployment(
            f"http://127.0.0.1:{server.server_port}", app_key, timeout=5
        )
        assert result["api_bootstrap_status"] == 200
        assert result["api_bootstrap_content_type"] == "text/html"
        assert result["api_bootstrap_is_json"] is False
        assert result["api_bootstrap_rejects_anonymous"] is False
        assert "desktop_bootstrap_auth_contract_failed" in result["deployment_issues"]
        assert result["ok"] is False
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
