import re
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_public_password_reset_request_sends_single_use_link_without_disclosing_account(
    monkeypatch, tmp_path
):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    sent_mail = []
    monkeypatch.setattr(
        web_main,
        "send_license_email",
        lambda tenant_id, recipient, subject, body: (
            sent_mail.append((tenant_id, recipient, subject, body)) or (True, "sent")
        ),
    )
    web_main._PASSWORD_RESET_REQUESTS.clear()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        rejected = requests.post(
            f"{base_url}/api/auth/request-password-reset",
            json={"identifier": "customer@example.com", "tenant_id": "tenant-1"},
        )
        assert rejected.status_code == 403
        response = session.post(
            f"{base_url}/api/auth/request-password-reset",
            json={"identifier": "customer@example.com", "tenant_id": "tenant-1"},
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert len(sent_mail) == 1
        assert sent_mail[0][1] == "customer@example.com"
        token = re.search(r"\?reset=([A-Za-z0-9_-]+)", sent_mail[0][3]).group(1)
        assert token not in response.text

        unknown = session.post(
            f"{base_url}/api/auth/request-password-reset",
            json={"identifier": "missing@example.com", "tenant_id": "tenant-1"},
        )
        assert unknown.status_code == response.status_code
        assert unknown.json() == response.json()
        assert len(sent_mail) == 1

        third = session.post(
            f"{base_url}/api/auth/request-password-reset",
            json={"identifier": "missing@example.com", "tenant_id": "tenant-1"},
        )
        limited = session.post(
            f"{base_url}/api/auth/request-password-reset",
            json={"identifier": "missing@example.com", "tenant_id": "tenant-1"},
        )
        assert third.status_code == 200
        assert limited.status_code == 429

        reset = session.post(
            f"{base_url}/api/auth/reset-password",
            json={"token": token, "password": "newsecurepass123"},
        )
        assert reset.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute(
                "SELECT password,must_change_password,password_updated_at FROM users WHERE id=1"
            ).fetchone()
        assert web_main.password_matches("newsecurepass123", row[0])
        assert row[1] == 0
        assert row[2]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_login_screen_exposes_password_reset_request_flow():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'button.id="authPasswordReset"' in source
    assert "function renderPasswordResetRequest" in source
    assert 'password_reset_dialog:()=>renderPasswordResetRequest("")' in source
    assert '"/api/auth/request-password-reset"' in source
