from PyQt6.QtWidgets import QApplication, QPushButton
from types import SimpleNamespace

from src.services.voice_feature_settings import (
    VOICE_ASSISTANT_FEATURES,
    VoiceFeatureSettingsDialog,
    voice_feature_enabled,
)


def _app():
    return QApplication.instance() or QApplication([])


class _SettingsDb:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_setting(self, key, default=None):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_voice_feature_switches_load_and_persist_independently():
    _app()
    db = _SettingsDb({VOICE_ASSISTANT_FEATURES[0][0]: "0"})

    dialog = VoiceFeatureSettingsDialog.create(None, db)

    assert len(dialog._toggles) == len(VOICE_ASSISTANT_FEATURES)
    assert not dialog._toggles[VOICE_ASSISTANT_FEATURES[0][0]].isChecked()
    for key, _title, _detail, default in VOICE_ASSISTANT_FEATURES[1:]:
        assert dialog._toggles[key].isChecked() is default

    for index, (key, _title, _detail, _default) in enumerate(VOICE_ASSISTANT_FEATURES):
        dialog._toggles[key].setChecked(index % 2 == 1)
    save = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == "Kaydet"
    )
    save.click()

    for index, (key, _title, _detail, _default) in enumerate(VOICE_ASSISTANT_FEATURES):
        expected = index % 2 == 1
        assert db.values[key] == ("1" if expected else "0")
        assert voice_feature_enabled(db, key) is expected
    dialog.close()


def test_voice_feature_switch_defaults_on_malformed_saved_value():
    db = _SettingsDb({VOICE_ASSISTANT_FEATURES[0][0]: "unexpected"})

    assert voice_feature_enabled(db, VOICE_ASSISTANT_FEATURES[0][0]) is True
    assert voice_feature_enabled(db, VOICE_ASSISTANT_FEATURES[0][0], False) is False


def _disabled_feature_manager(disabled_key):
    notifications = []
    spoken = []
    manager = SimpleNamespace(
        _voice_feature_enabled=lambda key: key != disabled_key,
        _conversation_history=[],
        _assistant_action_root=lambda _page: None,
        _form_required_followup=lambda _root: "",
        main_window=SimpleNamespace(
            _current_page_index=17,
            show_notification=lambda *args: notifications.append(args),
        ),
        _speak_async=spoken.append,
    )
    return manager, notifications, spoken


def test_disabled_navigation_accessibility_and_undo_features_block_commands():
    from src.services.assistant_manager import AssistantManager

    _app()
    cases = (
        ("voice_feature_navigation", "voice_next_record"),
        ("voice_feature_screen_accessibility", "voice_read_screen"),
        ("voice_feature_voice_undo", "voice_undo"),
    )
    for feature, intent in cases:
        manager, notifications, spoken = _disabled_feature_manager(feature)
        AssistantManager._handle_voice_accessibility_command(manager, intent)
        assert notifications
        assert spoken


def test_disabled_form_guidance_recap_and_correction_features_are_gated():
    from src.services.assistant_manager import AssistantManager

    manager, _notifications, _spoken = _disabled_feature_manager("voice_feature_form_filling")
    assert AssistantManager._form_status_text(manager, object()).startswith("Sesle form doldurma")

    manager, _notifications, _spoken = _disabled_feature_manager("voice_feature_required_guidance")
    assert AssistantManager._form_required_followup(manager, object()) == ""

    manager, _notifications, _spoken = _disabled_feature_manager("voice_feature_spoken_recap")
    assert AssistantManager._voice_form_change_reply(manager, None, "private value", None) == "Alan guncellendi."
    assert AssistantManager._voice_form_batch_recap(manager, [], None) == ""

    manager, _notifications, _spoken = _disabled_feature_manager("voice_feature_field_correction")
    ok, message = AssistantManager._stage_form_reset(manager, object())
    assert not ok and "kapali" in message

    manager, _notifications, _spoken = _disabled_feature_manager("voice_feature_critical_confirmation")
    ok, message = AssistantManager._stage_form_reset(manager, object())
    assert not ok and "onay" in message


def test_disabled_ui_control_feature_prevents_voice_button_actions():
    from src.services.assistant_manager import AssistantManager

    manager, notifications, spoken = _disabled_feature_manager("voice_feature_ui_controls")
    manager._run_voice_control = lambda *_args: (_ for _ in ()).throw(AssertionError("control must stay untouched"))

    AssistantManager._apply_conversation_result(
        manager,
        {"intent": "click_control", "reply": "Click the button", "utterance": "open it"},
    )

    assert notifications and "kapali" in notifications[-1][0]
    assert spoken and "kapali" in spoken[-1]
