import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel

from src.database import Database
from src.ui.pages.settings_widgets import voice_assistant_settings as settings


def test_turkish_voice_settings_use_local_ema_and_preserve_unrelated_settings(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "voice_settings.db"))
    stored = {
        "voice_assistant_active": "0", "asistan_voice_enabled": "0",
        "telsiz_efekti_aktif": "1", "asistan_hitap_aktif": "1",
        "asistan_edge_pitch": "+10Hz", "asistan_edge_voice": "tr-TR-EmelNeural",
        "asistan_tts_engine": "system", "asistan_edge_rate": "-10%",
        "asistan_user_name": "Operator", "asistan_ozel_adi": "Warehouse Assistant",
        "unrelated_setting": "preserve-this",
    }
    for key, value in stored.items():
        db.set_setting(key, value)
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM settings ORDER BY key")]
    page = settings.VoiceAssistantSettingsWidget(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1088, 685)
    page.show()
    app.processEvents()
    try:
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM settings ORDER BY key")] == before
        assert not page.toggle_assistant_active.isChecked()
        assert not page.toggle_voice.isChecked()
        assert page.toggle_radio.isChecked()
        assert page.toggle_hitap.isChecked()
        assert page.cmb_tone.currentText() == "Model Varsay\u0131lan\u0131"
        assert page.cmb_voice.currentText() == "EMA Do\u011fal T\u00fcrk\u00e7e Ses"
        assert page.cmb_engine.currentText() == "EMA Lightning (Yerel)"
        assert page.cmb_rate.currentText() == "Model Varsay\u0131lan\u0131"
        assert not any(label.text() == "ON" for label in page.findChildren(QLabel))
        writes = []
        original_set = db.set_setting
        monkeypatch.setattr(db, "set_setting", lambda *args: writes.append(args))
        page.reload_button.click()
        assert writes == []
        monkeypatch.setattr(db, "set_setting", original_set)
        calls = []
        from src.utils import asistan_motoru
        monkeypatch.setattr(asistan_motoru, "sesli_cevap_ver_async", lambda *args, **kwargs: calls.append((args, kwargs)))
        page.speech_test.click()
        assert len(calls) == 1
        assert calls[0][0] == ("Warehouse Assistant ses testi, Operator.", "ema-lightning")
        assert calls[0][1] == {"voice": "ema_default", "efekt_aktif": True}
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM settings ORDER BY key")] == before
        page.toggle_radio.setChecked(False)
        assert db.get_setting("telsiz_efekti_aktif") == "0"
        assert db.get_setting("asistan_edge_pitch") == "model"
        assert db.get_setting("asistan_edge_voice") == "ema_default"
        assert db.get_setting("asistan_tts_engine") == "ema-lightning"
        assert db.get_setting("unrelated_setting") == "preserve-this"
        page.inp_user_name.setText("New Operator")
        page.header_save_button.click()
        assert db.get_setting("asistan_user_name") == "New Operator"
        assert 24 <= page.inp_user_name.height() <= 32
        assert 24 <= page.cmb_voice.height() <= 32
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.conn.close()
