# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication, QLineEdit
from src.ui.pages.settings_widgets.smtp_settings import SMTPSettingsWidget
from src.utils.reference_typography import apply_reference_font

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class SettingsDB:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_part9_smtp_layout_presets_and_connection_status():
    db = SettingsDB()
    with patch(
        "src.ui.pages.settings_widgets.smtp_settings.SecureSettingStore.get",
        return_value="smtp-secret",
    ):
        widget = SMTPSettingsWidget(db)

    widget.resize(1336, 970)
    widget.show()
    APP.processEvents()
    assert widget.smtp_metric_test.parentWidget().height() == 32
    assert widget.smtp_metric_test.parentWidget().parentWidget().height() == 32
    assert widget.lbl_connection_state.text() == "SSL \u015e\u0130FREL\u0130 (Port 465)"
    assert widget.smtp_metric_test.text() == "13:12:04"
    assert widget.smtp_metric_test_detail.text() == "BASARILI"
    assert widget.inp_smtp_password.echoMode() == QLineEdit.EchoMode.Password
    assert widget.inp_smtp_server.width() > 250
    assert widget.smtp_form_card.height() <= 550
    assert widget.smtp_test_card.height() <= 360
    assert widget.log_card.height() <= 150
    assert widget.smtp_test_card.height() >= 340

    widget.resize(1280, 753)
    APP.processEvents()
    output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "email-smtp-desktop.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    assert widget.grab().save(str(output), "PNG")

    widget.btn_show_password.click()
    assert widget.inp_smtp_password.echoMode() == QLineEdit.EchoMode.Normal
    widget.btn_show_password.click()
    assert widget.inp_smtp_password.echoMode() == QLineEdit.EchoMode.Password
    widget.apply_preset("smtp.gmail.com", "587", "starttls")
    assert widget.inp_smtp_server.text() == "smtp.gmail.com"
    assert widget.inp_smtp_port.text() == "587"
    assert widget.cmb_security.currentData() == "starttls"
    assert widget.lbl_connection_state.text() == "TLS \u015e\u0130FREL\u0130 (Port 587)"

    server = MagicMock()
    server.__enter__.return_value = server
    with patch(
        "src.ui.pages.settings_widgets.smtp_settings.smtplib.SMTP",
        return_value=server,
    ) as smtp_connect:
        widget.btn_test.click()
    smtp_connect.assert_called_once()
    server.starttls.assert_called_once()
    server.send_message.assert_called_once()
    assert widget.lbl_connection_state.text() == "BAGLANTI BASARILI"
    assert widget.smtp_metric_test_detail.text() == "BASARILI"
    with patch("src.ui.pages.settings_widgets.smtp_settings.SecureSettingStore.set"):
        widget.btn_save.click()
    assert db.values["smtp_server"] == "smtp.gmail.com"
    widget.btn_reset.click()
    assert widget.inp_smtp_server.text() == "srvm07.trwww.com"
    widget.close()
