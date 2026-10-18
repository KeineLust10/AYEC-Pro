import sys
import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main
from src.utils import desktop_web_ai
from src.utils import local_turkish_tts


def test_assistant_query_requires_a_bounded_nonempty_question():
    with pytest.raises(ValueError, match="required"):
        desktop_web_ai.query_desktop_assistant("tenant.db", "  ")
    with pytest.raises(ValueError, match="too long"):
        desktop_web_ai.query_desktop_assistant("tenant.db", "x" * 1201)


def test_assistant_query_uses_read_only_tenant_database(monkeypatch):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            assert path == "tenant.db"
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(":memory:")
            self.closed = False

        def get_setting(self, key, default=""):
            return "gemini-test" if key == "gemini_model" else default

        def close(self):
            self.conn.close()
            self.closed = True

    database = FakeDatabase("tenant.db", "connection_only")

    class FakeAIService:
        def __init__(self, db):
            assert db is database
            assert db.conn.execute("SELECT 1").fetchone() == (1,)
            self.api_keys = ["gemini-secret-key"]

        def get_smart_response(self, question):
            assert question == "Stok durumu nedir?"
            with pytest.raises(sqlite3.OperationalError):
                database.conn.execute("CREATE TABLE should_be_blocked (id INTEGER)")
            return {"success": True, "answer": "No stock changes were made.", "error": "gemini-secret-key"}

    monkeypatch.setitem(sys.modules, "src.database", SimpleNamespace(Database=lambda path, init_mode: database))
    monkeypatch.setitem(sys.modules, "src.utils.ai_service", SimpleNamespace(AIService=FakeAIService))
    result = desktop_web_ai.query_desktop_assistant("tenant.db", "Stok durumu nedir?")

    assert result == {
        "success": True,
        "answer": "No stock changes were made.",
        "error": "[MASKED]",
        "model": "gemini-test",
    }
    assert database.closed


def test_assistant_status_never_returns_api_key(monkeypatch):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            self.closed = False

        def get_setting(self, key, default=""):
            return {"gemini_api_key": "enc:v1:secret-value", "gemini_model": "gemini-test"}.get(key, default)

        def close(self):
            self.closed = True

    database = FakeDatabase("tenant.db", "connection_only")
    monkeypatch.setitem(sys.modules, "src.database", SimpleNamespace(Database=lambda path, init_mode: database))
    monkeypatch.setattr(desktop_web_ai.importlib.util, "find_spec", lambda name: None)

    result = desktop_web_ai.desktop_assistant_status("tenant.db")

    assert result == {"configured": False, "key_present": True, "model": "gemini-test"}
    assert "secret-value" not in repr(result)
    assert database.closed


def test_assistant_browser_surface_and_routes_are_connected():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    index = (root / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    script = (root / "Web_Arayuzu" / "web" / "assistant-reference.js").read_text(encoding="utf-8")
    panel = (root / "Web_Arayuzu" / "web" / "desktop-assistant-panel.js").read_text(encoding="utf-8")
    assert 'src="assistant-reference.js?' in index
    assert 'href="assistant-reference.css?' in index
    assert 'apiFetch("/api/desktop/assistant/status")' in script
    assert 'apiFetch("/api/desktop/assistant/query"' in script
    assert 'fetch("/api/desktop/assistant/speech"' in panel


def test_assistant_http_routes_require_login_and_use_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(
        desktop_web_ai,
        "desktop_assistant_status",
        lambda path: calls.append(("status", Path(path))) or {"configured": False, "key_present": False, "model": "gemini-test"},
    )
    monkeypatch.setattr(
        desktop_web_ai,
        "query_desktop_assistant",
        lambda path, question: calls.append(("query", Path(path), question)) or {"success": True, "answer": "Fixture response", "error": ""},
    )
    speech_calls = []
    wav_payload = b"RIFF" + (36).to_bytes(4, "little") + b"WAVE" + b"fmt " + (16).to_bytes(4, "little") + (1).to_bytes(2, "little") + (1).to_bytes(2, "little") + (8000).to_bytes(4, "little") + (16000).to_bytes(4, "little") + (2).to_bytes(2, "little") + (16).to_bytes(2, "little") + b"data" + (0).to_bytes(4, "little")

    def synthesize(text, output_path, voice=None):
        speech_calls.append((text, voice, Path(output_path)))
        Path(output_path).write_bytes(wav_payload)

    monkeypatch.setattr(local_turkish_tts, "synthesize_to_file", synthesize)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(f"{base_url}/api/desktop/assistant/status").status_code == 401
        assert anonymous.post(f"{base_url}/api/desktop/assistant/query", json={"question": "hello"}).status_code == 401
        assert anonymous.post(f"{base_url}/api/desktop/assistant/speech", json={"text": "hello"}).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        status = session.get(f"{base_url}/api/desktop/assistant/status")
        answer = session.post(f"{base_url}/api/desktop/assistant/query", json={"question": "Tenant question"})
        speech = session.post(f"{base_url}/api/desktop/assistant/speech", json={"text": "Turkish reply"})
        invalid_speech = session.post(f"{base_url}/api/desktop/assistant/speech", json={"text": " "})

        assert status.json() == {"configured": False, "key_present": False, "model": "gemini-test"}
        assert answer.json()["answer"] == "Fixture response"
        assert speech.status_code == 200
        assert speech.headers["Content-Type"] == "audio/wav"
        assert speech.content == wav_payload
        assert invalid_speech.status_code == 400
        assert speech_calls[0][:2] == ("Turkish reply", None)
        assert not speech_calls[0][2].exists()
        assert calls == [
            ("status", tenant_path.resolve()),
            ("query", tenant_path.resolve(), "Tenant question"),
        ]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
