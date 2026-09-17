import importlib
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.widgets.side_menu import SideMenu
from src.database import Database
from src.ui.pages.finance.bank_page import BankPage
from src.utils.page_config import PAGE_MAPPING
from src.utils.sector_config import SECTOR_PAGES, SectorType


class _Cursor:
    def execute(self, *_args, **_kwargs):
        return self

    def fetchone(self):
        return None


class _MenuDb:
    def __init__(self, sector):
        self.sector = sector
        self.cursor = _Cursor()

    def get_setting(self, key, default=None):
        if key in {"current_sector", "selected_sector"}:
            return self.sector
        return default

    def get_internal_setting(self, key, default=None):
        if key == "current_sector":
            return self.sector
        return default

    def get_language(self):
        return "tr"

    def get_all_labels(self):
        return {}


def _app():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


def _menu_page_ids(menu):
    page_ids = {int(pid) for _button, pid in menu.flat_buttons}
    for group in menu.accordion_groups:
        page_ids.update(int(pid) for _button, pid in group.sub_buttons)
    return page_ids


def test_every_desktop_page_mapping_imports():
    for page_id, (module_name, class_name, _attribute, _args) in PAGE_MAPPING.items():
        module = importlib.import_module(module_name)
        page_class = getattr(module, class_name)
        assert page_class is not None, page_id


def test_two_sector_menus_only_target_loadable_or_virtual_pages():
    app = _app()
    virtual_pages = {62}
    for sector in ("teknik_servis", "otomotiv"):
        menu = SideMenu(
            db=_MenuDb(sector),
            current_user={"username": "owner", "role": "Admin"},
        )
        app.processEvents()
        page_ids = _menu_page_ids(menu)
        assert page_ids
        assert page_ids <= (set(PAGE_MAPPING) | virtual_pages)
        assert 62 in page_ids
        if sector == "teknik_servis":
            assert 50 in page_ids
            assert 60 not in page_ids
        else:
            assert 60 in page_ids
            assert 50 not in page_ids
            assert 150 in page_ids
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_sector_page_sets_do_not_reuse_stock_id_for_technician_panel():
    technical = SECTOR_PAGES[SectorType.TEKNIK_SERVIS]
    automotive = SECTOR_PAGES[SectorType.OTOMOTIV]
    assert 62 in technical
    assert 62 in automotive
    assert 50 in technical
    assert 60 not in technical
    assert 60 in automotive


def test_finance_schema_cache_recovers_when_database_file_is_recreated(tmp_path):
    app = _app()
    database_path = Path(tmp_path) / "recreated.db"
    first_db = Database(str(database_path))
    assert first_db.cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='loans'"
    ).fetchone()
    first_db.close()

    database_path.unlink()
    second_db = Database(str(database_path))
    assert second_db.cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='loans'"
    ).fetchone()
    page = BankPage(second_db, None)
    assert page.loans_tab is not None
    page.close()
    page.deleteLater()
    app.processEvents()
    second_db.close()
