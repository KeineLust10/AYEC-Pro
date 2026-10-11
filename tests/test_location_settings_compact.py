# -*- coding: utf-8 -*-
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QVBoxLayout

from src.ui.pages.settings_widgets.location_settings import LocationSettingsWidget
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager


class _Db:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_location_settings_uses_compact_company_settings_layout(tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    ThemeManager.apply_theme(app, "AYEC", animate=False)
    page = LocationSettingsWidget(_Db(), None)
    try:
        page.resize(1200, 760)
        page.show()
        app.processEvents()
        layout = page.layout()
        assert isinstance(layout, QVBoxLayout)
        assert layout.contentsMargins().left() == 6
        assert layout.spacing() == 4
        assert page.btn_pick.height() == 30
        assert page.map_preview.height() == 160
        assert not page.inp_lat.isReadOnly()
        assert not page.inp_lng.isReadOnly()
        assert page.inp_lat.text() == "40.1044116"
        assert page.inp_lng.text() == "27.6563981"
        assert page.grab().save(str(tmp_path / "location_settings_compact.png"))
    finally:
        page.close()


def test_location_settings_validates_and_saves_manual_coordinates():
    app = QApplication.instance() or QApplication([])
    db = _Db()
    page = LocationSettingsWidget(db, None)
    try:
        page.inp_lat.setText("91")
        page.inp_lng.setText("27")
        page.save_data(silent=True)
        assert "installation_lat" not in db.values

        page.inp_lat.setText("40,5")
        page.inp_lng.setText("27,6")
        page.save_data(silent=True)
        assert db.values["installation_lat"] == "40.5"
        assert db.values["installation_lng"] == "27.6"
        assert page.map_preview.latitude == "40.5"
        assert page.map_preview.longitude == "27.6"
    finally:
        page.close()
