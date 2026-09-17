import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page
from src.ui.pages.settings_page import SettingsPage
from src.ui.pages.settings_sidebar import PremiumSettingsSidebar
from src.ui.pages.settings_widgets.tax_exchange_settings import (
    TaxExchangeSettingsWidget,
)
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.tax_settings import TaxSettings


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def test_tax_settings_store_percent_and_expose_ratio():
    db = Database(":memory:")
    try:
        assert TaxSettings.get_percent(db) == 20
        assert TaxSettings.get_ratio(db) == 0.20
        assert TaxSettings.set_percent(db, 18) == 18
        assert TaxSettings.get_percent(db) == 18
        assert TaxSettings.get_ratio(db) == 0.18
        assert TaxSettings.combo_text(db) == "%18"
        assert TaxSettings.ratio_from_text("%1") == 0.01
    finally:
        db.close()


def test_manual_exchange_rates_replace_cached_values():
    db = Database(":memory:")
    try:
        ExchangeRateManager._rates_cache = {"USD": 1.0}
        ExchangeRateManager._last_cache_update = "2099-01-01"
        saved = ExchangeRateManager.save_manual_rates(
            db,
            {"USD": 42.5, "EUR": 47.25},
        )
        assert saved is True
        assert ExchangeRateManager._rates_cache == {}
        assert ExchangeRateManager._last_cache_update is None
        assert ExchangeRateManager.get_current_rate(db, "USD") == 42.5
        assert ExchangeRateManager.get_current_rate(db, "EUR") == 47.25
    finally:
        db.close()


def test_sales_page_uses_and_refreshes_central_vat():
    db = Database(":memory:")
    TaxSettings.set_percent(db, 18)
    page = NewTransactionV2Page(db)
    try:
        assert page.cmb_vat.currentText() == "%18"
        TaxSettings.set_percent(db, 10)
        page.refresh_financial_defaults()
        assert page.cmb_vat.currentText() == "%10"
    finally:
        page.close()
        page.deleteLater()
        APP.processEvents()
        db.close()


def test_settings_menu_exposes_tax_and_exchange_sync(monkeypatch):
    db = Database(":memory:")
    sidebar = PremiumSettingsSidebar(
        lambda _page_id: None,
        db=db,
        current_user={"role": "Admin"},
    )
    widget = TaxExchangeSettingsWidget(db)
    monkeypatch.setattr(
        "src.ui.pages.settings_widgets.tax_exchange_settings.show_success",
        lambda *_args, **_kwargs: None,
    )
    try:
        assert 25 in sidebar.items_map
        widget.spin_vat.setValue(8)
        widget.save_vat()
        assert TaxSettings.get_percent(db) == 8
        widget.rate_inputs["USD"].setValue(45.5)
        widget.rate_inputs["EUR"].setValue(49.25)
        widget.save_manual_rates()
        assert ExchangeRateManager.get_current_rate(db, "USD") == 45.5
        assert ExchangeRateManager.get_current_rate(db, "EUR") == 49.25
    finally:
        widget.close()
        sidebar.close()
        db.close()


def test_settings_page_loads_tax_exchange_panel():
    db = Database(":memory:")
    page = SettingsPage(db)
    try:
        page.change_page(25)
        assert isinstance(
            page.content_area.currentWidget(),
            TaxExchangeSettingsWidget,
        )
    finally:
        page.close()
        page.deleteLater()
        APP.processEvents()
        db.close()
