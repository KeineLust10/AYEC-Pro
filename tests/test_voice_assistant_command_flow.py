import os
import sys
import json
import threading
from pathlib import Path
from types import SimpleNamespace
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QObject
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QComboBox, QDialog, QTabWidget, QVBoxLayout, QPushButton, QWidget

from src.services.assistant_manager import AssistantManager
from src.services.assistant_conversation import LocalAssistantConversation
import src.services.assistant_manager as assistant_manager_module
from src.ui.pages.settings_widgets.voice_training_base import VoiceTrainingWidget
from src.ui.widgets.assistant_sidebar import AssistantSidebarDialog
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


def test_assistant_sidebar_uses_shared_turkish_speech_pipeline(monkeypatch):
    calls = []
    monkeypatch.setattr(
        asistan_motoru,
        "sesli_cevap_ver_async",
        lambda text, engine_type: calls.append((text, engine_type)),
    )
    AssistantSidebarDialog.speak(object(), "Merhaba")
    assert calls == [("Merhaba", "auto")]


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


def test_default_voice_commands_work_without_wake_word(monkeypatch):
    _qapp()
    defaults = VoiceTrainingWidget._default_scenarios(None)
    assistant = BulutAsistan()
    monkeypatch.setattr(assistant, "_get_wake_words", lambda: ["asistan"])
    monkeypatch.setattr(assistant, "_load_settings", lambda: defaults)

    for name, config in defaults.items():
        action = config["action"]
        expected = "open_page" if action["type"] == "page" else action["name"]
        emitted = _capture(assistant, config["triggers"][0])
        assert emitted, name
        assert emitted[0][0] == expected, (name, emitted)


def test_offer_creation_phrase_opens_offer_page_without_wake_word(monkeypatch):
    _qapp()
    assistant = BulutAsistan()
    monkeypatch.setattr(assistant, "_get_wake_words", lambda: ["asistan"])

    assert _capture(assistant, "teklif olustur") == [("open_page", "150")]
    assert _capture(assistant, "yeni teklif") == [("open_page", "150")]


def test_bare_menu_name_routes_without_ollama():
    conversation = LocalAssistantConversation(
        "Servis Listesi", [(42, "Servis Listesi")], 40, controls=[]
    )

    result = conversation._resolve()

    assert result["intent"] == "navigate"
    assert result["page_id"] == 42


@pytest.mark.parametrize(
    ("utterance", "control_type", "control_label", "options", "expected_intent"),
    [
        ("Yenile", "button", "Yenile", [], "click_control"),
        ("Ayarlar", "tabs", "Sekmeler", ["Genel", "Ayarlar"], "select_option"),
    ],
)
def test_bare_button_and_tab_names_resolve_without_ollama(
    utterance, control_type, control_label, options, expected_intent
):
    conversation = LocalAssistantConversation(
        utterance,
        [],
        40,
        controls=[{"id": "c0", "type": control_type, "label": control_label, "options": options}],
    )

    result = conversation._resolve()

    assert result["intent"] == expected_intent
    assert result["control_id"] == "c0"
    if expected_intent == "select_option":
        assert result["value"] == "Ayarlar"


def test_unwoken_exact_page_button_and_tab_names_route_to_the_named_target():
    app = _qapp()
    root = QDialog()
    layout = QVBoxLayout(root)
    tabs = QTabWidget(root)
    first_tab = QWidget()
    first_layout = QVBoxLayout(first_tab)
    refresh_button = QPushButton("Yenile", first_tab)
    first_layout.addWidget(refresh_button)
    clicked = []
    refresh_button.clicked.connect(lambda: clicked.append(True))
    tabs.addTab(first_tab, "Genel")
    tabs.addTab(QWidget(), "Ayarlar")
    layout.addWidget(tabs)
    root.show()
    app.processEvents()

    class _Database:
        def get_setting(self, _key, default=None):
            return default

    class _SideMenu:
        _btn_map = {40: object(), 42: object()}
        _badge_names = {40: "Genel Bakis", 42: "Servis Listesi"}

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()
            self.app_sidebar = SimpleNamespace(side_menu=_SideMenu())
            self._current_page_index = 40
            self.pages = []
            self.notifications = []

        def _is_page_allowed_for_active_sector(self, _page_id):
            return True

        def get_page(self, _page_id):
            return root

        def on_menu_click(self, page_id):
            self.pages.append(page_id)
            self._current_page_index = page_id

        def show_notification(self, message, level):
            self.notifications.append((message, level))

    window = _Window()
    manager = AssistantManager(window)
    manager._speak_async = lambda _message: None

    assert manager._resolve_named_ui_target("Yenile") is True
    assert clicked == [True]
    assert manager._resolve_named_ui_target("Ayarlar") is True
    assert tabs.currentIndex() == 1
    assert manager._resolve_named_ui_target("Servis Listesi") is True
    assert window.pages == [42]
    root.close()


def test_every_generated_menu_phrase_routes_to_its_linked_page(monkeypatch):
    _qapp()
    defaults = VoiceTrainingWidget._default_scenarios(None)
    assistant = BulutAsistan()
    monkeypatch.setattr(assistant, "_get_wake_words", lambda: ["asistan"])
    monkeypatch.setattr(assistant, "_load_settings", lambda: defaults)

    for name, config in defaults.items():
        action = config["action"]
        if action.get("type") != "page":
            continue
        triggers = config["triggers"]
        assert len(triggers) >= 8, name
        indexes = sorted({0, 1, len(triggers) // 2, len(triggers) - 1})
        for phrase in (triggers[index] for index in indexes):
            emitted = _capture(assistant, phrase)
            assert emitted and emitted[0] == ("open_page", str(action["index"])), (name, phrase, emitted)


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


def test_saved_default_scenarios_gain_new_menu_phrases_without_losing_custom_triggers():
    saved = {
        "M\u00fc\u015fteri Listesi": {
            "triggers": ["\u00f6zel m\u00fc\u015fteri komutum"],
            "action": {"type": "page", "index": 21},
        }
    }

    class _Harness:
        _default_scenarios = VoiceTrainingWidget._default_scenarios

    merged = VoiceTrainingWidget._sanitize_data(_Harness(), saved)
    customer_scenario = merged["M\u00fc\u015fteri Listesi"]

    assert "\u00f6zel m\u00fc\u015fteri komutum" in customer_scenario["triggers"]
    assert "bana m\u00fc\u015fteriler g\u00f6ster" in customer_scenario["triggers"]


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
    assert window.pending_action == {
        "type": "apply_zam", "percentage": 10, "scope": "all_active_stock",
        "category": None, "affected_count": None,
    }

    manager.aksiyon_merkezi("confirm_yes", "")
    assert window.db.percentages == [10]
    assert window.pending_action is None
    assert manager.pending_action is None
    assert window.pages == [999]
    assert any("yuzde 10 zam uyguladim" in message for message in spoken)


def test_stock_raise_without_percentage_asks_instead_of_defaulting_to_ten():
    class _Database:
        def get_setting(self, _key, default=None):
            return default

        def apply_stock_price_increase(self, _percentage):
            raise AssertionError("A stock update must not be staged without an explicit rate")

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()
            self.pending_action = {"type": "stale"}
            self.notifications = []

        def show_notification(self, message, level):
            self.notifications.append((message, level))

    window = _Window()
    manager = AssistantManager(window)
    spoken = []
    manager._speak_async = spoken.append

    manager.aksiyon_merkezi("apply_zam", "")

    assert window.pending_action is None
    assert manager.pending_action is None
    assert spoken and "yuzde kac" in spoken[-1]


def test_voice_stock_scope_matches_category_and_never_falls_back_to_all():
    class _Cursor:
        def execute(self, query, params=()):
            self.query = query
            self.params = params

        def fetchall(self):
            return [("Elektronik",), ("Kucuk Ev Aletleri",)]

        def fetchone(self):
            return (12,)

    manager = SimpleNamespace(
        db=SimpleNamespace(cursor=_Cursor()),
        _log_soft_failure=lambda *_args: None,
    )
    scope = AssistantManager._resolve_voice_stock_scope(
        manager, "Stoklara %5 elektronik kategorisinde zam"
    )
    assert scope == ("category", "Elektronik", 12, "")

    unresolved = AssistantManager._resolve_voice_stock_scope(
        manager, "Stoklara %5 bilinmeyen kategorisinde zam"
    )
    assert unresolved[0] is None and "tum stoklara zam uygulamadim" in unresolved[3]


def test_voice_listener_reference_is_kept_until_worker_finishes(monkeypatch):
    class _Database:
        def get_setting(self, _key, default=None):
            return "1" if _key == "voice_assistant_active" else default

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()
            self.notifications = []

        def show_notification(self, message, level):
            self.notifications.append((message, level))

    class _SlowStoppingThread:
        def __init__(self):
            self.running = True
            self.is_running = True

        def stop(self):
            self.is_running = False

        def isRunning(self):
            return self.running

    manager = AssistantManager(_Window())
    thread = _SlowStoppingThread()
    manager.voice_assistant_thread = thread

    manager.stop_voice_assistant(notify=True)

    assert manager.voice_assistant_thread is thread
    assert manager.start_voice_assistant() is True
    assert manager.main_window.notifications == []
    assert manager._voice_assistant_restart_pending is True

    callbacks = []
    starts = []
    monkeypatch.setattr(
        assistant_manager_module.QTimer,
        "singleShot",
        staticmethod(lambda delay, callback: callbacks.append((delay, callback))),
    )
    manager.start_voice_assistant = lambda notify=False: starts.append(notify) or True
    thread.running = False
    manager._on_voice_assistant_finished()

    assert manager.voice_assistant_thread is None
    assert len(callbacks) == 1 and callbacks[0][0] == 0
    callbacks[0][1]()
    assert starts == [False]


def test_voice_listener_is_disabled_when_user_has_not_opted_in():
    class _Database:
        def get_setting(self, _key, default=None):
            return default

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()

    manager = AssistantManager(_Window())

    assert manager.is_voice_assistant_enabled() is False
    assert manager.start_voice_assistant() is False
    assert manager.voice_assistant_thread is None


def test_voice_listener_success_is_reported_only_after_ready():
    class _Database:
        def get_setting(self, _key, default=None):
            return default

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()
            self.notifications = []

        def show_notification(self, message, level):
            self.notifications.append((message, level))

    manager = AssistantManager(_Window())
    manager._voice_assistant_notify_when_ready = True

    manager._handle_voice_assistant_ready()

    assert manager.main_window.notifications == [
        ("Sesli asistan dinleme modu ba\u015flat\u0131ld\u0131.", "success")
    ]

    manager._voice_assistant_notify_when_ready = False
    manager._handle_voice_assistant_ready()
    assert len(manager.main_window.notifications) == 1


def test_assistant_amount_speaks_turkish_lira_and_rounds_half_up():
    _qapp()

    class _Database:
        def get_setting(self, key, default=None):
            return "TRY" if key == "currency" else default

    class _Window(QObject):
        def __init__(self):
            super().__init__()
            self.db = _Database()

    manager = AssistantManager(_Window())

    assert manager._amount_in_words(12.345) == "on iki T\u00fcrk liras\u0131 otuz be\u015f kuru\u015f"
