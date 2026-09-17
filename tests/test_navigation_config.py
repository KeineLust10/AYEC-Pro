from src.utils.navigation_config import (
    PAGE_LABELS,
    build_web_navigation,
    iter_menu_page_ids,
)
from src.utils.sector_config import SECTOR_PAGES, SectorType


class _SettingsDb:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_internal_setting(self, key, default=None):
        return self.values.get(key, default)


def test_navigation_covers_current_desktop_pages_for_both_sectors():
    expected = {140, 145, 146, 147, 150, 313, 314}
    for sector, sector_type in (
        ("teknik_servis", SectorType.TEKNIK_SERVIS),
        ("otomotiv", SectorType.OTOMOTIV),
    ):
        page_ids = set(iter_menu_page_ids(sector))
        assert expected <= page_ids
        assert 170 not in page_ids
        assert page_ids <= set(SECTOR_PAGES[sector_type])


def test_web_navigation_uses_interface_editor_visibility_and_label():
    db = _SettingsDb(
        {
            "menu_label_page_313": "Onay Bekleyen Teklifler",
            "menu_visible_page_314": "0",
        }
    )

    groups = build_web_navigation(db, "teknik_servis")
    items = {
        item["page_id"]: item
        for group in groups
        for item in group["items"]
    }

    assert items[313]["label"] == "Onay Bekleyen Teklifler"
    assert 314 not in items


def test_automotive_navigation_uses_automotive_stock_page():
    page_ids = set(iter_menu_page_ids("otomotiv"))
    assert 60 in page_ids
    assert 50 not in page_ids
