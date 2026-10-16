import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_mobile_guide_renders_steps_and_stock_scanner_handoff():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    script = (root / "mobile-guide-reference.js").read_text(encoding="utf-8")
    stylesheet = (root / "mobile-guide-reference.css").read_text(encoding="utf-8")
    index = (root / "index.html").read_text(encoding="utf-8")

    assert 'if (page !== "mobile-guide")' in script
    assert 'new URL("/?page=stock", window.location.origin)' in script
    assert 'api/desktop/mobile-guide/qr?target=' in script
    app = (root / "app.js").read_text(encoding="utf-8")
    assert 'id="stockSearch"' in app
    assert 'navigator.mediaDevices.getUserMedia' in app
    assert 'new BarcodeDetector({formats:["ean_13","ean_8","code_128","code_39","upc_a","upc_e"]})' in app
    assert "_ayecDecodeBarcodeImage(video)" in app
    assert "mobile-guide-reference.js" in index
    assert "mobile-guide-reference.css" in index
    assert "@media(max-width:720px)" in stylesheet


def test_mobile_guide_qr_requires_login_and_same_origin_stock_target(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    target = f"{base_url}/?page=stock"
    try:
        anonymous = requests.get(
            f"{base_url}/api/desktop/mobile-guide/qr",
            params={"target": target},
            headers={"Referer": f"{base_url}/?page=mobile-guide"},
        )
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        headers = {"Referer": f"{base_url}/?page=mobile-guide"}
        response = session.get(
            f"{base_url}/api/desktop/mobile-guide/qr",
            params={"target": target},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "image/png"
        assert response.content.startswith(b"\x89PNG\r\n\x1a\n")

        invalid = session.get(
            f"{base_url}/api/desktop/mobile-guide/qr",
            params={"target": "https://other.example/?page=stock"},
            headers=headers,
        )
        assert invalid.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
