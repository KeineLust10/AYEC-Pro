"""Capture the native stock context menu without displaying desktop windows."""
from __future__ import annotations

import os
import json
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint, QTimer
from PyQt6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.database import Database
from src.ui.pages.stock_page import StockPage
from src.ui.pages import _stock_context_menus
from src.utils.theme_manager import ThemeManager
from src.utils.reference_typography import apply_reference_font


def main() -> None:
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    ThemeManager.apply_theme(app, "Koyu Mavi", animate=False)
    _stock_context_menus.is_context_menu_enabled = lambda *args, **kwargs: True
    original_load = StockPage.load_stock_list
    StockPage.load_stock_list = lambda self: None
    temporary = tempfile.TemporaryDirectory(prefix="ayec-stock-desktop-audit-")
    database = Database(str(Path(temporary.name) / "stock-audit.db"))
    page = None
    try:
        page = StockPage(database)
        page.resize(1280, 900)
        page.show()
        page._fill_table([{
            "id": 901,
            "code": "STK-AUDIT",
            "name": "Fixture Product",
            "description": "Context menu fixture",
            "category": "General",
            "stock": 12,
            "min_stock": 2,
            "unit": "Adet",
            "purchase_price": 10,
            "price": 15,
            "currency": "TRY",
            "location": "A-01",
        }])
        app.processEvents()
        output = Path("output/playwright")
        output.mkdir(parents=True, exist_ok=True)
        captured: dict[str, object] = {}

        def capture_and_close() -> None:
            menu = app.activePopupWidget()
            if menu is None:
                captured["error"] = "No active Qt popup menu"
                return
            captured["actions"] = [
                action.text() if not action.isSeparator() else "<separator>"
                for action in menu.actions()
            ]
            captured["width"] = menu.width()
            captured["height"] = menu.height()
            captured["saved"] = menu.grab().save(str(output / "stock-context-menu-desktop-headless.png"))
            menu.close()

        row_position = QPoint(40, page.table_stock.horizontalHeader().height() + 12)
        if page.table_stock.rowAt(row_position.y()) < 0:
            raise RuntimeError("Native stock fixture row is not visible.")
        QTimer.singleShot(250, capture_and_close)
        page.show_stock_context_menu(row_position)
        app.processEvents()
        if captured.get("error") or not captured.get("saved"):
            raise RuntimeError(str(captured))
        if captured.get("actions") != [
            "\U0001f4e6 Stok Ekle/\u00c7\u0131kar", "\u270f\ufe0f D\u00fczenle", "\U0001f4f7 Foto\u011fraf\u0131 G\u00f6r\u00fcnt\u00fcle", "<separator>",
            "\U0001f4c4 PDF Olarak Kaydet", "\U0001f5a8\ufe0f Yazd\u0131r", "\U0001f4ca Excel'e Aktar", "<separator>", "\U0001f5d1\ufe0f Sil",
        ]:
            raise RuntimeError(f"Unexpected desktop menu: {captured}")
        print(json.dumps(captured, ensure_ascii=True))
    finally:
        if page is not None:
            page.close()
        database.close()
        temporary.cleanup()
        StockPage.load_stock_list = original_load


if __name__ == "__main__":
    main()
