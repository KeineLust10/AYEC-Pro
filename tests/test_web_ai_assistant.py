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
    assert 'desktop-assistant-panel.css?v=20261026-assistant-voice-edit-undo-1' in index
    assert 'desktop-assistant-panel.js?v=20261026-assistant-voice-edit-undo-1' in index
    assert 'apiFetch("/api/desktop/assistant/status")' in script
    assert 'apiFetch("/api/desktop/assistant/query"' in script
    assert 'fetch("/api/desktop/assistant/speech"' in panel
    assert 'data-assistant-voice' in panel
    assert 'window.SpeechRecognition || window.webkitSpeechRecognition' in panel
    assert 'recognition.lang = "tr-TR"' in panel
    assert 'recognition.abort()' in panel
    assert 'function resolveNamedPage(text)' in panel
    assert 'sectorPages[currentSector]?.has(item.id)' in panel
    assert 'const pageTarget = action ? null : resolveNamedPage(text)' in panel
    assert 'const readScreenRequested = ["ekrani oku", "sayfayi oku", "read screen"]' in panel
    assert 'document.querySelector("#content")?.innerText' in panel
    assert 'const readFieldRequested = ["alani oku", "odaklanan alani oku", "read field"]' in panel
    assert 'function describeActivePageField()' in panel
    assert 'function describeFormFeedback()' in panel
    assert 'function scrollActivePage(forward)' in panel
    assert 'function appendDictation(text)' in panel
    assert 'function searchActivePage(query)' in panel
    assert 'function editFocusedTextControl(operation, value = "")' in panel
    assert 'function requestFocusedFieldClear()' in panel
    assert 'function resolveFieldClear(confirmed)' in panel
    assert 'function moveRecordSelection(forward)' in panel
    assert 'function activateSelectedRecord()' in panel
    assert 'function stopReplySpeech()' in panel
    assert 'function requestFormReset()' in panel
    assert 'function undoLastFieldChange()' in panel
    assert 'function requestNamedFieldClear(spokenLabel)' in panel
    assert 'function navigateAssistantBack()' in panel
    assert 'function describeFormStatus()' in panel
    assert 'const stockOcrRequested =' in panel
    assert 'const repeatSpeechRequested =' in panel
    assert 'const stopSpeechRequested =' in panel
    assert 'generation !== speechGeneration' in panel
    assert 'const clearFieldRequested = ["alani temizle", "metni temizle", "clear field"]' in panel
    assert 'const screenSearchRequested = ["bu ekranda ara", "sayfada ara", "ekranda ara", "burada ara", "search this screen"]' in panel
    assert 'const result = searchActivePage(match?.[1] || "")' in panel
    assert '{ phrases: ["virgul ekle", "virgul koy", "insert comma"], operation: "insert", value: ", " }' in panel
    assert '{ phrases: ["son kelimeyi sil", "onceki kelimeyi sil", "delete word"], operation: "delete_word" }' in panel
    assert 'const dictationStartRequested = ["dikte modunu ac", "dikteye basla", "yazmaya basla", "start dictation"]' in panel
    assert 'if (dictationMode)' in panel
    assert 'control.value = current + separator + value' in panel
    assert 'const scrollDirection = ["asagi kaydir", "ekrani asagi kaydir", "scroll down"]' in panel
    assert 'const result = scrollActivePage(scrollDirection > 0)' in panel
    assert 'const readFormFeedbackRequested = ["form geri bildirimini oku", "form hatalarini oku", "eksik alanlari oku", "read form feedback"]' in panel
    assert 'control.validationMessage || "deger dogrulamadan gecmedi."' in panel
    assert 'describeFormFeedback(), true' in panel
    assert 'control.value ? "dolu" : "bo\\u015f"' in panel
    assert 'function activeAssistantContentRoot()' in panel
    assert 'function movePageFocus(forward)' in panel
    assert 'const focusDirection = ["sonraki alana gec"' in panel
    assert 'if (!keepPageFocus) input.focus();' in panel


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

def test_offscreen_assistant_query_failure_preserves_input_and_allows_retry():
    root = Path(__file__).resolve().parents[1]
    audit = (root / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "assistant.failureShown" in audit
    assert "assistant.inputRetained" in audit
    assert "assistant.buttonRecovered" in audit
    assert "assistant.attempts !== 2" in audit

def test_offscreen_route_audit_checks_assistant_on_desktop_viewport():
    root = Path(__file__).resolve().parents[1]
    audit = (root / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.assistantDesktopWorkflow" in audit
    assert "assistant.viewport < 1024" in audit
    assert '"Desktop audit question"' in audit
