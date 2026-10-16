import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_manual_viewer_has_desktop_tabs_and_escapes_document_content():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    script = (root / "manual-reference.js").read_text(encoding="utf-8")
    styles = (root / "manual-reference.css").read_text(encoding="utf-8")
    index = (root / "index.html").read_text(encoding="utf-8")

    assert 'usage: "Kullan\\u0131m K\\u0131lavuzu"' in script
    assert 'setup: "Kurulum Rehberi"' in script
    assert 'result.content' in script
    assert 'replace(/</g, "&lt;")' in script
    assert "manual-reference.js" in index
    assert "manual-reference.css" in index
    assert "@media(max-width:640px)" in styles


def test_manual_content_route_requires_login_and_serves_only_allowlisted_docs(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.get(f"{base_url}/api/desktop/manual/content?document=usage")
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        usage = session.get(f"{base_url}/api/desktop/manual/content?document=usage")
        setup = session.get(f"{base_url}/api/desktop/manual/content?document=setup")
        invalid = session.get(f"{base_url}/api/desktop/manual/content?document=../../Main.py")
        assert usage.status_code == 200
        assert usage.json()["content"] == Path("KULLANIM_KILAVUZU.md").read_text(encoding="utf-8")
        assert setup.status_code == 200
        assert setup.json()["content"] == Path("KURULUM_REHBERI.md").read_text(encoding="utf-8")
        assert invalid.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
