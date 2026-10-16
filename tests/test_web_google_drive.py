import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from Web_Arayuzu import Main as web_main
from Web_Arayuzu.google_drive_web import new_authorization, upload_backup, validate_web_client_config


def test_google_drive_requires_web_oauth_client_and_keeps_secret_out_of_plaintext():
    with pytest.raises(ValueError, match="Web application"):
        validate_web_client_config({"installed": {"client_id": "local.apps.googleusercontent.com"}})

    config = validate_web_client_config({
        "web": {
            "client_id": "tenant.apps.googleusercontent.com",
            "client_secret": "private-client-secret",
        }
    })

    assert config["web"]["client_id"] == "tenant.apps.googleusercontent.com"
    assert config["web"]["token_uri"] == "https://oauth2.googleapis.com/token"
    protected = web_main._protect_google_drive_value(json.dumps(config))
    assert "private-client-secret" not in protected
    assert web_main._reveal_google_drive_value(protected) == json.dumps(config)


def test_google_drive_authorization_uses_server_callback_and_csrf_state():
    from urllib.parse import parse_qs, urlparse

    config = validate_web_client_config({
        "web": {
            "client_id": "tenant.apps.googleusercontent.com",
            "client_secret": "private-client-secret",
        }
    })
    url = new_authorization(config, "https://panel.example.test/oauth/callback", "opaque-state")
    params = parse_qs(urlparse(url).query)

    assert params["redirect_uri"] == ["https://panel.example.test/oauth/callback"]
    assert params["state"] == ["opaque-state"]
    assert params["access_type"] == ["offline"]
    assert "drive.file" in params["scope"][0]


def test_google_drive_callback_url_must_be_https_and_fixed_endpoint(monkeypatch):
    monkeypatch.setattr(web_main, "PUBLIC_SERVER_URL", "https://panel.example.test")
    assert web_main._google_drive_redirect_uri() == (
        "https://panel.example.test/api/desktop/backups/google-drive/callback"
    )
    monkeypatch.setenv("AYEC_GOOGLE_DRIVE_REDIRECT_URI", "https://panel.example.test/other")
    with pytest.raises(ValueError, match="HTTPS"):
        web_main._google_drive_redirect_uri()


def test_google_drive_upload_sends_backup_bytes_and_returns_refreshed_credentials(monkeypatch):
    google_api = pytest.importorskip("googleapiclient.discovery")
    google_http = pytest.importorskip("googleapiclient.http")
    from google.oauth2.credentials import Credentials

    captured = {}

    class Media:
        def __init__(self, stream, mimetype, resumable):
            captured["payload"] = stream.read()
            captured["mimetype"] = mimetype
            captured["resumable"] = resumable

    class UploadRequest:
        def execute(self):
            return {"id": "drive-file-1", "name": "tenant.db"}

    class Files:
        def create(self, **kwargs):
            captured["metadata"] = kwargs["body"]
            captured["media"] = kwargs["media_body"]
            return UploadRequest()

    class Service:
        def files(self):
            return Files()

    monkeypatch.setattr(google_api, "build", lambda *args, **kwargs: Service())
    monkeypatch.setattr(google_http, "MediaIoBaseUpload", Media)
    creds = Credentials(
        token="access-token",
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        refresh_token="refresh-token",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="tenant.apps.googleusercontent.com",
        client_secret="client-secret",
    )

    file_id, refreshed_token = upload_backup(creds.to_json(), "tenant.db", b"sqlite-snapshot")

    assert file_id == "drive-file-1"
    assert captured["payload"] == b"sqlite-snapshot"
    assert captured["metadata"] == {"name": "tenant.db"}
    assert captured["resumable"] is True
    assert json.loads(refreshed_token)["refresh_token"] == "refresh-token"


def test_google_drive_oauth_state_is_short_lived_and_consumed_once(monkeypatch, tmp_path):
    database_path = tmp_path / "registry.db"
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE google_drive_oauth_states ("
        "state_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,user_id INTEGER NOT NULL,created_at TEXT NOT NULL)"
    )
    now = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    state = "random-state-value"
    import hashlib

    conn.execute(
        "INSERT INTO google_drive_oauth_states VALUES(?,?,?,?)",
        (hashlib.sha256(state.encode()).hexdigest(), "tenant-a", 8, now.isoformat()),
    )
    conn.commit()
    conn.close()

    def open_registry():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(web_main, "registry_connect", open_registry)
    monkeypatch.setattr(web_main, "utc_now", lambda: now)

    assert web_main._consume_google_drive_state(state) == {"tenant_id": "tenant-a", "user_id": 8}
    assert web_main._consume_google_drive_state(state) is None

    expired_state = "expired-state"
    with sqlite3.connect(database_path) as conn:
        conn.execute(
            "INSERT INTO google_drive_oauth_states VALUES(?,?,?,?)",
            (hashlib.sha256(expired_state.encode()).hexdigest(), "tenant-a", 8, (now - timedelta(minutes=11)).isoformat()),
        )
    assert web_main._consume_google_drive_state(expired_state) is None


def test_connect_route_encrypts_client_config_and_creates_tenant_bound_state(monkeypatch, tmp_path):
    tenant_db = tmp_path / "tenant.db"
    registry_db = tmp_path / "registry.db"
    with sqlite3.connect(tenant_db) as conn:
        conn.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
    with sqlite3.connect(registry_db) as conn:
        conn.execute(
            "CREATE TABLE google_drive_oauth_states ("
            "state_hash TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,user_id INTEGER NOT NULL,created_at TEXT NOT NULL)"
        )
    monkeypatch.setattr(web_main, "clear_tenant_context", lambda: None)
    monkeypatch.setattr(web_main, "_desktop_backup_context", lambda user: ({}, "tenant-a", "teknik_servis"))
    monkeypatch.setattr(web_main, "db_connect", lambda: sqlite3.connect(tenant_db))
    monkeypatch.setattr(web_main, "registry_connect", lambda: sqlite3.connect(registry_db))
    monkeypatch.setattr(web_main, "new_google_drive_authorization", lambda config, uri, state: "https://accounts.google.com/authorize?state=" + state)
    monkeypatch.setattr(web_main, "_google_drive_redirect_uri", lambda: "https://panel.example.test/api/desktop/backups/google-drive/callback")
    actor = {"id": 17, "role": "Admin", "_tenant_id": "tenant-a"}
    client_config = {"web": {"client_id": "tenant.apps.googleusercontent.com", "client_secret": "secret"}}
    responses = []
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/backups/google-drive/connect"
    handler.headers = {"Content-Length": "128"}
    handler.current_user = lambda: actor
    handler.same_origin = lambda: True
    handler.read_json = lambda: {"client_config": client_config}
    handler.send_json = lambda payload, status=200, headers=None: responses.append((payload, status))

    handler.do_POST()

    assert responses[0][0].get("authorization_url", "").startswith("https://accounts.google.com/authorize?state="), repr(responses)
    assert responses[0][1] == 200
    with sqlite3.connect(tenant_db) as conn:
        stored = conn.execute("SELECT value FROM settings WHERE key='google_drive_client_config'").fetchone()[0]
    assert "secret" not in stored
    assert web_main._reveal_google_drive_value(stored)
    with sqlite3.connect(registry_db) as conn:
        state_record = conn.execute("SELECT tenant_id,user_id FROM google_drive_oauth_states").fetchone()
    assert state_record == ("tenant-a", 17)


