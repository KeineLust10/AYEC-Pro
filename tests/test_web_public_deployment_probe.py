from __future__ import annotations

import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from Web_Arayuzu.check_public_deployment import expected_app_key, probe_public_deployment


@contextmanager
def local_site(app_key="fresh", api_mode="json", asset_mode="javascript", profile_mode=None, login_mode=None, root_status=200):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" and root_status != 200:
                self.send_response(root_status)
                self.send_header("Server", "Microsoft-IIS/10.0")
                self.end_headers()
                self.wfile.write(b"Bad Gateway")
                return
            if self.path.startswith("/app.js"):
                if asset_mode == "javascript":
                    body = b"async function apiFetch() {}"
                    content_type = "application/javascript; charset=utf-8"
                else:
                    body = b"<!doctype html><html><body>login</body></html>"
                    content_type = "text/html; charset=utf-8"
            elif self.path == "/api/desktop/bootstrap":
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"error":"Authentication required"}')
                return
            elif self.path.startswith("/api/auth/status"):
                if api_mode == "502":
                    self.send_response(502)
                    self.send_header("Server", "Microsoft-IIS/10.0")
                    self.end_headers()
                    self.wfile.write(b"Bad Gateway")
                    return
                elif api_mode == "json":
                    body = f'{{"ok":true,"authenticated":false,"app_build_id":"{app_key}"}}'.encode()
                    content_type = "application/json; charset=utf-8"
                else:
                    body = b"<!doctype html><html><body>login</body></html>"
                    content_type = "text/html; charset=utf-8"
            else:
                body = f'<script src="app.js?v={app_key}"></script>'.encode()
                content_type = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if profile_mode == "legacy" and self.path.startswith("/api/auth/profile"):
                body = b'{"error":"AYECRequestHandler has no attribute require_user"}'
                content_type = "application/json; charset=utf-8"
                status = 400
            elif (profile_mode or api_mode) == "json" and self.path.startswith("/api/auth/profile"):
                body = b'{"error":"Authentication required"}'
                content_type = "application/json; charset=utf-8"
                status = 401
            elif (login_mode or api_mode) == "json" and self.path.startswith("/api/auth/login"):
                body = b'{"error":"Identifier and password are required"}'
                content_type = "application/json; charset=utf-8"
                status = 400
            else:
                body = b"<!doctype html><html><body>login</body></html>"
                content_type = "text/html; charset=utf-8"
                status = 200
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_expected_key_reads_the_app_script_version(tmp_path: Path):
    index = tmp_path / "index.html"
    index.write_text(
        '<script src="vendor.js?v=old"></script>'
        '<script src="app.js?v=release-7"></script>',
        encoding="utf-8",
    )

    assert expected_app_key(index) == "release-7"


def test_public_deployment_probe_accepts_current_frontend_and_json_api():
    with local_site(app_key="release-7") as base_url:
        result = probe_public_deployment(base_url, "release-7", check_login_post=True)

    assert result["ok"] is True
    assert result["frontend_matches"] is True
    assert result["root_server"]
    assert result["root_date"]
    assert result["asset_is_javascript"] is True
    assert result["api_is_json"] is True
    assert result["api_post_status"] == 401
    assert result["api_post_rejects_unauthenticated_profile"] is True
    assert result["api_login_post_checked"] is True
    assert result["api_login_status"] == 400
    assert result["api_login_rejects_empty_credentials"] is True


def test_public_deployment_probe_skips_login_post_by_default():
    with local_site(app_key="release-7") as base_url:
        result = probe_public_deployment(base_url, "release-7")

    assert result["ok"] is True
    assert result["api_login_post_checked"] is False
    assert result["api_login_status"] is None


def test_public_deployment_probe_identifies_stale_frontend():
    with local_site(app_key="release-6") as base_url:
        result = probe_public_deployment(base_url, "release-7")

    assert result["ok"] is False
    assert result["frontend_matches"] is False
    assert result["asset_is_javascript"] is True
    assert result["api_is_json"] is True


def test_public_deployment_probe_reports_iis_upstream_failure_without_fake_frontend_mismatch():
    with local_site(app_key="release-7", root_status=502) as base_url:
        result = probe_public_deployment(base_url, "release-7")

    assert result["ok"] is False
    assert "backend_unavailable" in result["deployment_issues"]
    assert "frontend_build_mismatch" not in result["deployment_issues"]
    assert "desktop_bootstrap_auth_contract_failed" not in result["deployment_issues"]


def test_public_deployment_probe_detects_api_only_upstream_failure():
    with local_site(app_key="release-7", api_mode="502") as base_url:
        result = probe_public_deployment(base_url, "release-7")

    assert result["root_status"] == 200
    assert result["api_status"] == 502
    assert "backend_unavailable" in result["deployment_issues"]
    assert "desktop_bootstrap_auth_contract_failed" not in result["deployment_issues"]


def test_public_deployment_probe_rejects_html_from_auth_api():
    with local_site(api_mode="html") as base_url:
        result = probe_public_deployment(base_url, "fresh", check_login_post=True)

    assert result["ok"] is False
    assert result["frontend_matches"] is True
    assert result["api_status"] == 200
    assert result["api_content_type"] == "text/html"
    assert result["api_is_json"] is False
    assert result["api_post_status"] == 200
    assert result["api_post_content_type"] == "text/html"
    assert result["api_post_rejects_unauthenticated_profile"] is False
    assert result["api_login_status"] == 200
    assert result["api_login_content_type"] == "text/html"
    assert result["api_login_rejects_empty_credentials"] is False
    assert result["deployment_issues"] == [
        "api_status_route_returns_non_json",
        "backend_build_id_missing",
        "login_api_returns_non_json",
    ]


def test_public_deployment_probe_checks_login_even_when_profile_probe_fails():
    with local_site(profile_mode="html", login_mode="json") as base_url:
        result = probe_public_deployment(base_url, "fresh", check_login_post=True)

    assert result["ok"] is False
    assert result["api_post_rejects_unauthenticated_profile"] is False
    assert result["api_login_status"] == 400
    assert result["api_login_rejects_empty_credentials"] is True


def test_public_deployment_probe_identifies_legacy_profile_auth_handler():
    with local_site(profile_mode="legacy") as base_url:
        result = probe_public_deployment(base_url, "fresh")

    assert result["ok"] is False
    assert result["api_post_status"] == 400
    assert result["api_post_missing_require_user"] is True
    assert result["deployment_issues"] == ["legacy_backend_auth_handler"]


def test_public_deployment_probe_rejects_html_fallback_for_app_script():
    with local_site(asset_mode="html") as base_url:
        result = probe_public_deployment(base_url, "fresh")

    assert result["ok"] is False
    assert result["asset_status"] == 200
    assert result["asset_content_type"] == "text/html"
    assert result["asset_is_javascript"] is False
