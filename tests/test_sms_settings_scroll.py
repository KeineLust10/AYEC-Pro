import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel, QScrollArea, QWidget

from src.database import Database
from src.ui.pages.settings_widgets.integration_hub import IntegrationHubWidget
from src.ui.pages.settings_widgets.sms_settings import SMSSettingsWidget
from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget


def test_integration_hub_adapts_legacy_dark_styles_to_theme_tokens():
    app = QApplication.instance() or QApplication([])
    root = QWidget()
    label = QLabel("Theme probe", root)
    label.setStyleSheet(
        "QLabel { background: #0e1321; color: #dee2f6; "
        "border: 1px solid #252a39; }"
    )

    IntegrationHubWidget._apply_adaptive_integration_styles(root)

    raw_stylesheet = getattr(label, "_theme_raw_stylesheet", "")
    assert "@window" in raw_stylesheet
    assert "@text" in raw_stylesheet
    assert "@border" in raw_stylesheet
    assert label.property("skipThemeTransform") is False
    root.close()


def test_integration_hub_preserves_explicit_reference_action_styles(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "telegram_reference_styles.db"))
    widget = TelegramSettingsWidget(db)
    try:
        IntegrationHubWidget._apply_adaptive_integration_styles(widget)
        for button in (
            widget.token_eye,
            widget.btn_copy_token,
            widget.btn_reset_webhook,
            widget.btn_drop_pending,
        ):
            assert button.property("skipThemeTransform") is True
            assert "background:#1f2937" in button.styleSheet()
            assert "color:#dbeafe" in button.styleSheet()
    finally:
        widget.close()
        db.close()


def test_sms_settings_fit_scroll_view_without_clipping_controls(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "sms_scroll.db"))
    hub = IntegrationHubWidget(db)
    scroll = hub._create_page("sms", None, "SMS")
    try:
        assert isinstance(scroll, QScrollArea)
        assert isinstance(scroll.widget(), SMSSettingsWidget)
        scroll.resize(1000, 500)
        scroll.show()
        app.processEvents()
        assert scroll.verticalScrollBar().maximum() > 0
        assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    finally:
        hub.close()
        scroll.close()
        db.close()


def test_telegram_integration_page_expands_to_available_height(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "telegram_full_height.db"))
    hub = IntegrationHubWidget(db)
    wrapper = hub._create_page("telegram", "#00cde8", "Telegram Bot")
    try:
        page = wrapper.layout().itemAt(0).widget()
        assert isinstance(page, TelegramSettingsWidget)
        wrapper.resize(1280, 900)
        wrapper.show()
        app.processEvents()
        assert page.content_scroll.viewport().height() >= 850
        capture = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "telegram-settings-full-page.png"
        capture.parent.mkdir(parents=True, exist_ok=True)
        assert wrapper.grab().save(str(capture), "PNG")
    finally:
        hub.close()
        wrapper.close()
        db.close()
