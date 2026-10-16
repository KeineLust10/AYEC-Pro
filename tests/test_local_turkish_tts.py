import sys
import threading
import time
import io
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import asistan_motoru
from src.utils import local_turkish_tts
from src.utils import local_turkish_tts_worker


@pytest.mark.parametrize("legacy_engine", ["auto", "system", "edge", "premium", "freya", "qwen", "ema-lightning"])
def test_all_engine_choices_use_local_turkish_voice(monkeypatch, legacy_engine):
    calls = []
    played = threading.Event()

    def synthesize(text, output_path, voice=None):
        calls.append(text)
        Path(output_path).write_bytes(b"wav-payload" * 20)
        return output_path

    def play(path):
        assert Path(path).read_bytes().startswith(b"wav-payload")
        played.set()
        return True

    monkeypatch.setattr(local_turkish_tts, "synthesize_to_file", synthesize)
    monkeypatch.setattr(asistan_motoru, "_play_mp3", play)
    asistan_motoru.sesli_cevap_ver_async("Merhaba", engine_type=legacy_engine)

    assert played.wait(3)
    assert calls == ["Merhaba"]


def test_local_adapter_uses_isolated_runtime(monkeypatch, tmp_path):
    runtime = tmp_path / "python.exe"
    runtime.write_bytes(b"runtime")
    output = tmp_path / "speech.wav"
    requests = []

    def dispatch(text, path, python):
        requests.append((text, path, python))
        Path(path).write_bytes(b"RIFF-ema-test")

    monkeypatch.setattr(local_turkish_tts, "_runtime_python", lambda: runtime)
    monkeypatch.setattr(local_turkish_tts, "_request_worker", dispatch)

    assert local_turkish_tts.synthesize_to_file("Merhaba", output, "ema_default") == output
    assert output.read_bytes() == b"RIFF-ema-test"
    assert requests[0] == ("Merhaba", output, runtime)


def test_worker_loop_reports_ready_and_a_json_result(monkeypatch):
    requests = [json.dumps({"text": "Merhaba"}), json.dumps({"command": "shutdown"})]
    stdout = io.StringIO()
    monkeypatch.setattr(local_turkish_tts_worker.sys, "stdin", io.StringIO("\n".join(requests)))
    monkeypatch.setattr(local_turkish_tts_worker.sys, "stdout", stdout)
    monkeypatch.setattr(local_turkish_tts_worker, "_load_model", lambda: object())
    monkeypatch.setattr(local_turkish_tts_worker, "_synthesize", lambda request: {"ok": request["text"] == "Merhaba"})
    local_turkish_tts_worker.main()
    assert [json.loads(line) for line in stdout.getvalue().splitlines()] == [
        {"ready": True},
        {"ok": True},
    ]


def test_empty_text_is_not_sent_to_worker(monkeypatch, tmp_path):
    monkeypatch.setattr(local_turkish_tts, "_runtime_python", lambda: tmp_path / "python.exe")
    monkeypatch.setattr(
        local_turkish_tts,
        "_request_worker",
        lambda *_args: pytest.fail("empty text must not reach the worker"),
    )

    with pytest.raises(ValueError, match="Speech text must not be empty"):
        local_turkish_tts.synthesize_to_file("  ", tmp_path / "speech.wav")


def test_missing_local_runtime_does_not_fall_back_to_system_voice(monkeypatch):
    finished = threading.Event()

    def missing_runtime(*_args):
        raise ImportError("optional local TTS runtime is missing")

    def log_failure(*_args, **_kwargs):
        finished.set()

    monkeypatch.setattr(local_turkish_tts, "synthesize_to_file", missing_runtime)
    monkeypatch.setattr(asistan_motoru.logger, "exception", log_failure)
    monkeypatch.setattr(asistan_motoru, "_play_mp3", lambda *_args: pytest.fail("must not play a fallback"))
    asistan_motoru.sesli_cevap_ver_async("Merhaba", engine_type="auto")

    assert finished.wait(3)


def test_async_preload_reuses_active_warmup_thread(monkeypatch, tmp_path):
    entered = threading.Event()
    release = threading.Event()
    runtime = tmp_path / "python.exe"
    monkeypatch.setattr(local_turkish_tts, "_runtime_python", lambda: runtime)
    monkeypatch.setattr(local_turkish_tts, "_preload_thread", None)

    def wait_for_release(_runtime):
        entered.set()
        release.wait(3)

    monkeypatch.setattr(local_turkish_tts, "_preload_worker", wait_for_release)

    first = local_turkish_tts.preload_async()
    assert entered.wait(1)
    second = local_turkish_tts.preload_async()
    third = local_turkish_tts.preload_async()

    assert first is second is third
    release.set()
    first.join(1)
    assert not first.is_alive()


@pytest.mark.parametrize("synthesis_fails", [False, True])
def test_tts_completion_releases_microphone_gate(monkeypatch, synthesis_fails):
    completed = threading.Event()

    def synthesize(_text, output_path, voice=None):
        if synthesis_fails:
            raise RuntimeError("synthetic TTS failure")
        Path(output_path).write_bytes(b"wav-payload" * 20)
        return output_path

    monkeypatch.setattr(local_turkish_tts, "synthesize_to_file", synthesize)
    monkeypatch.setattr(asistan_motoru, "_play_mp3", lambda *_args: True)
    monkeypatch.setattr(asistan_motoru.logger, "exception", lambda *_args, **_kwargs: None)

    with asistan_motoru._tts_generation_lock:
        asistan_motoru._tts_generation += 1
        asistan_motoru._tts_playback_active = False
        asistan_motoru._tts_mic_cooldown_until = 0.0
    asistan_motoru.sesli_cevap_ver_async("Merhaba", engine_type="auto")

    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        with asistan_motoru._tts_generation_lock:
            if not asistan_motoru._tts_playback_active:
                completed.set()
                break
        threading.Event().wait(0.01)
    assert completed.is_set()
    assert asistan_motoru._tts_capture_snapshot()[1]
    time.sleep(max(0, asistan_motoru._tts_mic_cooldown_until - time.monotonic()) + 0.02)
    assert not asistan_motoru._tts_capture_snapshot()[1]


def test_settings_offer_local_ema_voice_and_save_choice(monkeypatch, qapp):
    from src.ui.pages.settings_widgets.voice_assistant_settings import VoiceAssistantSettingsWidget

    class FakeDb:
        values = {"asistan_tts_engine": "ema-lightning", "asistan_edge_voice": "ema_default"}

        def get_setting(self, key, default=None):
            return self.values.get(key, default)

        def set_setting(self, key, value):
            self.values[key] = value

    db = FakeDb()
    widget = VoiceAssistantSettingsWidget(db)

    assert [widget.cmb_engine.itemText(i) for i in range(widget.cmb_engine.count())] == ["EMA Lightning (Yerel)"]
    assert widget.cmb_voice.count() == 1
    assert widget.cmb_voice.currentData() == "ema_default"
    assert not widget.cmb_tone.isEnabled()
    assert not widget.cmb_rate.isEnabled()
    preview = []
    monkeypatch.setattr(
        asistan_motoru,
        "sesli_cevap_ver_async",
        lambda text, engine, **kwargs: preview.append((text, engine, kwargs)),
    )
    widget._play_speech_preview()
    assert preview[0][1] == "ema-lightning"
    assert preview[0][2]["voice"] == "ema_default"
    widget._save_all(show_feedback=False)
    assert db.values["asistan_tts_engine"] == "ema-lightning"
    assert db.values["asistan_edge_voice"] == "ema_default"


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app
