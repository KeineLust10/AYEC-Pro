import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QToolButton

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
    widget.resize(1280, 900)
    widget.show()
    app.processEvents()

    assert widget.width() == 1280
    assert widget.height() == 900
    assert not widget.btn_save.isVisible()
    assert widget.list_recommended_commands.count() == 6
    first_row = widget.list_recommended_commands.itemWidget(widget.list_recommended_commands.item(0))
    assert first_row.objectName() == "voiceCommandRow"
    first_row.findChildren(QToolButton)[0].click()
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
