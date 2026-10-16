import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QListWidget, QLineEdit, QWidget

from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget


APP = QApplication.instance() or QApplication([])


class SettingsDb:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_integration_shortcuts_navigate_to_real_settings_pages():
    host = QWidget()
    rows = [None, 20, 21, 14, 5, 13, 3, 16]
    sidebar_list = QListWidget(host)
    for _ in rows:
        sidebar_list.addItem("")
    search = QLineEdit(host)
    host.sidebar = SimpleNamespace(
        items_map=rows,
        list_widget=sidebar_list,
        search_inp=search,
    )
    selected_pages = []
    sidebar_list.currentRowChanged.connect(
        lambda row: selected_pages.append(rows[row]) if row >= 0 else None
    )
    search.setText("api")

    widget = WhatsAppSettingsWidget(SettingsDb())
    widget.setParent(host)

    for button in widget.integration_nav_buttons:
        button.click()
    for button in (
        widget.telegram_settings_button,
        widget.quick_notes_settings_button,
        widget.ai_settings_button,
        widget.cargo_settings_button,
        widget.sms_settings_button,
    ):
        button.click()

    assert selected_pages == [20, 21, 14, 5, 13, 3, 16, 14, 13, 5, 3]
    assert search.text() == ""
    widget.close()
    host.close()


def test_provider_credentials_follow_selected_delivery_mode():
    widget = WhatsAppSettingsWidget(SettingsDb())

    assert not widget.inp_provider_sid.isHidden()
    assert not widget.inp_provider_sid.isEnabled()
    provider_index = widget.cmb_mode.findData("provider_api")
    widget.cmb_mode.setCurrentIndex(provider_index)
    assert not widget.inp_provider_sid.isHidden()
    assert widget.inp_provider_sid.isEnabled()

    widget.cmb_mode.setCurrentIndex(widget.cmb_mode.findData("disabled"))
    assert not widget.inp_provider_sid.isHidden()
    assert not widget.inp_provider_sid.isEnabled()
    widget.close()


def test_test_message_uses_admin_phone_and_approved_template(monkeypatch):
    from src.services.whatsapp_service import WhatsAppService
    from src.utils import toast_notification

    database = SettingsDb()
    database.values.update(
        {
            "whatsapp_mode": "cloud_api",
            "whatsapp_admin_phone": "+905551234567",
            "company_name": "AYEC Demo",
        }
    )
    calls = []
    monkeypatch.setattr(
        WhatsAppService,
        "send",
        lambda self, *args: calls.append(args) or {"ok": True},
    )
    monkeypatch.setattr(toast_notification, "show_success", lambda *args: None)
    widget = WhatsAppSettingsWidget(database)

    widget.btn_test_message.click()

    assert len(calls) == 1
    assert calls[0][0] == "+905551234567"
    assert calls[0][2] == "payment_reminder_tr"
    assert calls[0][3] == ["Test", "AYEC Demo", "0.00"]
    widget.close()


def test_payment_template_preview_tracks_editable_tokens():
    database = SettingsDb()
    database.values["company_name"] = "AYEC Demo"
    widget = WhatsAppSettingsWidget(database)

    widget.inp_template.setPlainText("Merhaba {musteri_adi}, {firma_adi}: {borc_tutari} TRY")

    assert widget.template_preview.text() == "Merhaba Ornek Musteri, AYEC Demo: 500.00 TRY"
    widget.close()


def test_cloud_status_card_refreshes_after_credentials_are_saved():
    widget = WhatsAppSettingsWidget(SettingsDb())
    widget.inp_cloud_phone_id.setText("test-phone-id")
    widget.inp_cloud_token.setText("test-cloud-token")

    widget.cmb_mode.setCurrentIndex(widget.cmb_mode.findData("cloud_api"))

    assert widget._summary_note_values[0].text() == "Aktif"
    widget.close()


def test_loading_cloud_mode_preserves_saved_credentials():
    database = SettingsDb()
    database.values.update(
        {
            "whatsapp_mode": "cloud_api",
            "whatsapp_cloud_phone_id": "saved-phone-id",
            "whatsapp_cloud_token": "saved-cloud-token",
        }
    )

    widget = WhatsAppSettingsWidget(database)

    assert widget.cmb_mode.currentData() == "cloud_api"
    assert widget.inp_cloud_phone_id.text() == "saved-phone-id"
    assert widget.inp_cloud_token.text() == "saved-cloud-token"
    assert database.values["whatsapp_cloud_token"]
    widget.close()
