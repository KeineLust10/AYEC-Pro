from PyQt6.QtWidgets import QApplication, QPushButton

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

    target = VOICE_ASSISTANT_FEATURES[1][0]
    dialog._toggles[target].setChecked(False)
    save = next(
        button
        for button in dialog.findChildren(QPushButton)
        if button.text() == "Kaydet"
    )
    save.click()

    assert db.values[VOICE_ASSISTANT_FEATURES[0][0]] == "0"
    assert db.values[target] == "0"
    assert voice_feature_enabled(db, target) is False
    assert all(
        voice_feature_enabled(db, key, default)
        == dialog._toggles[key].isChecked()
        for key, _title, _detail, default in VOICE_ASSISTANT_FEATURES
    )
    dialog.close()


def test_voice_feature_switch_defaults_on_malformed_saved_value():
    db = _SettingsDb({VOICE_ASSISTANT_FEATURES[0][0]: "unexpected"})

    assert voice_feature_enabled(db, VOICE_ASSISTANT_FEATURES[0][0]) is True
    assert voice_feature_enabled(db, VOICE_ASSISTANT_FEATURES[0][0], False) is False
