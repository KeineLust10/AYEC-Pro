import os
import sys
import json
import threading
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QObject
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox

from src.services.assistant_manager import AssistantManager
from src.ui.pages.settings_widgets.voice_training_base import VoiceTrainingWidget
from src.utils.asistan_motoru import BulutAsistan
from src.utils import asistan_motoru


def _qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    return app


def _capture(assistant, phrase):
    emitted = []

    def receive(action, parameter):
        emitted.append((action, parameter))

    assistant.tetik_sinyali.connect(receive)
    try:
        assistant.komut_coz(phrase)
    finally:
        assistant.tetik_sinyali.disconnect(receive)
    return emitted


def test_wake_word_and_short_confirmation_are_actionable(monkeypatch):
    _qapp()
    assistant = BulutAsistan()
    monkeypatch.setattr(assistant, "_get_wake_words", lambda: ["asistan"])

    assert _capture(assistant, "hey asistan") == [("wake_ack", "")]
    assert _capture(assistant, "yap") == [("confirm_yes", "")]
    assert _capture(assistant, "evet") == [("confirm_yes", "")]


def test_system_tts_engine_speaks_instead_of_exiting_silently(monkeypatch):
    spoken = []
    completed = threading.Event()

    class _FakeEngine:
        def getProperty(self, key):
            if key == "voices":
                return []
            if key == "rate":
                return 180
            return None

        def setProperty(self, _key, _value):
            return None

        def say(self, text):
            spoken.append(text)

        def runAndWait(self):
            completed.set()

        def stop(self):
            return None

    monkeypatch.setattr(asistan_motoru.pyttsx3, "init", lambda: _FakeEngine())
    asistan_motoru.sesli_cevap_ver_async("Dinliyorum", engine_type="system")

    assert completed.wait(2)
    assert spoken == ["Dinliyorum"]


def test_every_default_voice_scenario_emits_its_linked_action(monkeypatch):
    _qapp()
    defaults = VoiceTrainingWidget._default_scenarios(None)
    assistant = BulutAsistan()
    monkeypatch.setattr(assistant, "_get_wake_words", lambda: ["hey asistan", "asistan"])
    monkeypatch.setattr(assistant, "_load_settings", lambda: defaults)

    assert defaults
    for name, config in defaults.items():
        action = config["action"]
        expected = "open_page" if action["type"] == "page" else action["name"]
        phrase = f"hey asistan {config['triggers'][0]}"
        emitted = _capture(assistant, phrase)
        assert emitted, name
        assert emitted[0][0] == expected, (name, emitted)


def test_action_editor_lists_every_default_scenario_action():
    app = _qapp()

    class _EditorHarness:
        main_window = None

    combo = QComboBox()
    VoiceTrainingWidget._init_action_options(_EditorHarness(), combo)
    listed = {
        combo.itemData(index, Qt.ItemDataRole.UserRole)
        for index in range(combo.count())
    }
    defaults = VoiceTrainingWidget._default_scenarios(None)

    for name, config in defaults.items():
        payload = json.dumps(config["action"], ensure_ascii=False, sort_keys=True)
        assert payload in listed, name
    app.processEvents()


def test_stock_raise_confirmation_executes_pending_action():
    class _Database:
        def __init__(self):
            self.percentages = []

        def get_setting(self, _key, default=None):
            return default

        def apply_stock_price_increase(self, percentage):
            self.percentages.append(percentage)
            return True

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()
            self.pending_action = None
            self.notifications = []
            self.pages = []

        def show_notification(self, message, level):
            self.notifications.append((message, level))

        def on_menu_click(self, page):
            self.pages.append(page)

    window = _Window()
    manager = AssistantManager(window)
    spoken = []
    manager._speak_async = spoken.append

    manager.aksiyon_merkezi("apply_zam", "Stoklara %10")
    assert window.pending_action == {"type": "apply_zam", "percentage": 10}

    manager.aksiyon_merkezi("confirm_yes", "")
    assert window.db.percentages == [10]
    assert window.pending_action is None
    assert manager.pending_action is None
    assert window.pages == [999]
    assert any("yuzde 10 zam uyguladim" in message for message in spoken)
