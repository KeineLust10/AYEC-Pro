"""Capture the native contract detail dialog for paired parity checks."""

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from src.ui.pages.contracts_page import ContractDetailsDialog
from src.utils.theme_manager import ThemeManager


class FixtureDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.executescript(
            "CREATE TABLE contracts(id INTEGER, customer_id INTEGER, title TEXT, contract_type TEXT, description TEXT);"
            "CREATE TABLE customers(id INTEGER, name TEXT);"
            "INSERT INTO contracts VALUES(44, 7, 'Fixture contract', 'Servis', 'Details');"
            "INSERT INTO customers VALUES(7, 'Fixture customer');"
        )

    def get_contract_attachments(self, _contract_id):
        return [(14, 44, "fixture/service.pdf", "service.pdf", "2026-10-16")]


def main():
    app = QApplication.instance() or QApplication([])
    ThemeManager._current_theme = "Koyu Mavi"
    ThemeManager._install_stylesheet_patch()
    dialog = ContractDetailsDialog(FixtureDatabase(), 44)
    dialog.show()
    app.processEvents()
    output = ROOT / "output" / "playwright" / "contract-detail-desktop-reference.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    if not dialog.grab().save(str(output)):
        raise RuntimeError("Could not save the native contract detail capture.")
    result = {"size": [dialog.width(), dialog.height()], "screenshot": str(output)}
    print(json.dumps(result))
    dialog.close()
    app.quit()


if __name__ == "__main__":
    main()
