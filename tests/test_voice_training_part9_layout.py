import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QToolButton

from src.ui.pages.settings_widgets.voice_training_reference import VoiceTrainingWidget
from src.utils.path_helper import PathHelper


class VoiceSettingsDb:
    def __init__(self):
        self.settings = {}
        self.alerts = {}

    def get_all_scheduled_alerts(self):
        return [dict(alert_type=key, trigger_time=value[0], is_enabled=value[1]) for key, value in self.alerts.items()]

    def update_scheduled_alert(self, alert_type, trigger_time=None, is_enabled=None):
        previous = self.alerts.get(alert_type, ("17:30", True))
        self.alerts[alert_type] = (trigger_time or previous[0], previous[1] if is_enabled is None else is_enabled)

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


def _app():
    app = QApplication.instance() or QApplication(sys.argv)
    for font in (r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if Path(font).exists():
            QFontDatabase.addApplicationFont(font)
    app.setFont(QFont("Segoe UI", 9))
    app.setQuitOnLastWindowClosed(False)
    return app


def test_part9_voice_settings_fill_page_and_keep_controls_functional(tmp_path, monkeypatch):
    app = _app()
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))
    db = VoiceSettingsDb()
    widget = VoiceTrainingWidget(db)
    widget.resize(1280, 901)
    widget.show()
    app.processEvents()

    assert widget.width() == 1280
    assert widget.height() == 901
    brand = next(label for label in widget.findChildren(QLabel) if "Komut Merkezi" in label.text())
    assert brand.text() == "AYEC Pro | Sesli Senaryo & AI Komut Merkezi"
    assert brand.textFormat() == Qt.TextFormat.PlainText
    assert brand.font().family() == "Inter"
    assert not widget.btn_save.isVisible()
    assert widget.list_recommended_commands.count() == 6
    first_row = widget.list_recommended_commands.itemWidget(widget.list_recommended_commands.item(0))
    assert first_row.objectName() == "voiceCommandRow"
    first_title = first_row.findChildren(QLabel)[0]
    assert first_title.text() == "Asistan finans \u00f6zet"
    assert "#22d3ee" in first_title.styleSheet()
    trigger = next(label for label in first_row.findChildren(QLabel) if label.text().startswith("Tetikleyici:"))
    assert trigger.width() == 100
    assert "background:transparent" in trigger.styleSheet()
    command_buttons = first_row.findChildren(QToolButton)
    assert len(command_buttons) == 2
    assert all(button.isVisible() for button in command_buttons)
    assert all(button.geometry().right() <= first_row.width() for button in command_buttons)
    command_buttons[0].click()
    assert QApplication.clipboard().text() == "Asistan finans \u00f6zet"
    capture_dir = Path("output/part9-captures")
    capture_dir.mkdir(parents=True, exist_ok=True)
    assert widget.grab().save(str(capture_dir / "voice-command-desktop.png"))

    widget.inp_command_search.setText("kritik stok")
    assert widget.list_recommended_commands.count() == 1
    widget.inp_command_search.clear()
    stock_filter = next(button for button in widget.findChildren(type(widget.btn_save)) if button.property("voiceFilter") == "Stok")
    stock_filter.click()
    assert widget.list_recommended_commands.count() == 3

    widget.time_dnd_start.setTime(widget.time_dnd_start.time().addSecs(60))
    widget.chk_critical_override.setChecked(True)
    widget.voice_volume.setValue(60)
    widget.voice_speed.setCurrentText("1.2x")
    widget.btn_save.click()
    app.processEvents()
    assert db.settings["critical_override_dnd"] == "1"
    assert db.settings["voice_volume"] == "60"
    assert db.settings["voice_speed"] == "1.2"
    assert db.alerts["service_delivery"] == ("17:30", True)
    assert (tmp_path / "asistan_ayarlari.json").exists()

    widget._select_command_filter("T\u00fcm\u00fc")
    widget.inp_command_search.clear()
    widget.time_dnd_start.setTime(widget.time_dnd_start.time().addSecs(-60))
    widget.chk_critical_override.setChecked(True)
    widget.voice_volume.setValue(85)
    widget.voice_speed.setCurrentText("1.0x")
    app.processEvents()

    widget.close()


def test_voice_settings_styles_follow_light_and_dark_theme_tokens():
    app = _app()
    db = VoiceSettingsDb()
    widget = VoiceTrainingWidget(db)
    widget.show()
    app.processEvents()
    from src.utils.theme_manager import ThemeManager

    previous_theme = ThemeManager._current_theme
    try:
        ThemeManager.apply_theme(app, "AYEC")
        app.processEvents()
        light_styles = (widget.styleSheet(), widget.btn_engine_refresh.styleSheet())
        ThemeManager.apply_theme(app, "Koyu Mavi")
        app.processEvents()
        dark_styles = (widget.styleSheet(), widget.btn_engine_refresh.styleSheet())
        assert all("@" not in style for style in light_styles + dark_styles)
        assert light_styles != dark_styles
        assert "#090e1c" not in widget.styleSheet().lower()
        assert "#0e1525" not in widget.styleSheet().lower()
    finally:
        ThemeManager.apply_theme(app, previous_theme)
        widget.close()


def test_desktop_voice_scenarios_import_web_json_export(tmp_path, monkeypatch):
    import json
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    from src.ui.pages.settings_widgets import voice_training_reference

    app = _app()
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))
    source = tmp_path / "web-scenarios.json"
    payload = {
        "Imported scenario": {
            "triggers": ["desktop import trigger"],
            "action": {"type": "builtin", "name": "accounting_summary"},
        }
    }
    source.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(source), ""))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    errors = []
    monkeypatch.setattr(voice_training_reference, "show_error", lambda parent, message: errors.append(message))

    widget = VoiceTrainingWidget(VoiceSettingsDb())
    widget.data["Existing custom scenario"] = {"triggers": ["old trigger"]}
    menu_labels = [action.text() for action in widget.scenario_files_menu.actions()]
    assert widget.btn_export_scenarios.menu() is widget.scenario_files_menu
    assert menu_labels == ["\u21e7  Senaryolar\u0131 D\u0131\u015fa Aktar", "\u21e7  Dosyadan Senaryo Al"]
    widget.import_scenarios()

    assert not errors
    assert widget.data["Imported scenario"]["triggers"] == ["desktop import trigger"]
    assert widget.data["Imported scenario"]["action"]["name"] == "accounting_summary"
    assert "Existing custom scenario" not in widget.data
    saved = json.loads((tmp_path / "asistan_ayarlari.json").read_text(encoding="utf-8"))
    assert saved["Imported scenario"]["triggers"] == ["desktop import trigger"]
    widget.close()
    app.processEvents()


def test_desktop_voice_scenario_import_rejects_oversized_json(tmp_path, monkeypatch):
    from PyQt6.QtWidgets import QFileDialog
    from src.ui.pages.settings_widgets import voice_training_reference

    app = _app()
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))
    source = tmp_path / "oversized.json"
    source.write_bytes(b" " * 1_048_577)
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: (str(source), ""))
    errors = []
    monkeypatch.setattr(voice_training_reference, "show_error", lambda parent, message: errors.append(message))

    widget = VoiceTrainingWidget(VoiceSettingsDb())
    original = dict(widget.data)
    widget.import_scenarios()

    assert widget.data == original
    assert errors and "1 MB" in errors[0]
    widget.close()
    app.processEvents()


def test_desktop_voice_scenarios_prefer_and_update_synced_tenant_setting(tmp_path, monkeypatch):
    import json
    from Web_Arayuzu.Main import SYNC_TABLES

    app = _app()
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(tmp_path))
    local_path = tmp_path / "asistan_ayarlari.json"
    local_path.write_text(json.dumps({"Old local scenario": {"triggers": ["old local"]}}), encoding="utf-8")
    shared_state = {
        "commands": [{"name": "Custom command", "phrase": "shared command"}],
        "scenarios": {"Shared scenario": {"triggers": ["shared trigger"], "action": {"type": "builtin", "name": "accounting_summary"}}},
        "alerts": [],
    }
    db = VoiceSettingsDb()
    assert "settings" in SYNC_TABLES
    db.settings["voice_command_settings"] = json.dumps(shared_state)

    widget = VoiceTrainingWidget(db)
    assert "Shared scenario" in widget.data
    assert "Old local scenario" not in widget.data
    assert json.loads(local_path.read_text(encoding="utf-8"))["Shared scenario"]["triggers"] == ["shared trigger"]

    widget.data["Shared scenario"]["triggers"].append("desktop update")
    widget._persist_voice_data()
    saved_state = json.loads(db.settings["voice_command_settings"])
    assert saved_state["commands"] == shared_state["commands"]
    assert saved_state["scenarios"]["Shared scenario"]["triggers"] == ["shared trigger", "desktop update"]
    widget.close()
    app.processEvents()
