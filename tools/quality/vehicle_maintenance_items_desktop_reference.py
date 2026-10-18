"""Create a themed offscreen desktop reference for maintenance items."""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication

from src.ui.dialogs.vehicle_maintenance_items_dialog import VehicleMaintenanceItemsDialog
from src.utils.theme_manager import ThemeManager


OUTPUT = ROOT / "output" / "playwright" / "vehicle-maintenance-items-desktop-reference.png"


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    ThemeManager.apply_theme(app, "Koyu Mavi", animate=False)
    dialog = VehicleMaintenanceItemsDialog(QDate(2026, 4, 1), 100000)
    dialog.show()
    app.processEvents()
    dialog.setMinimumSize(1180, 760)
    dialog.setMaximumSize(1180, 760)
    dialog.resize(1180, 760)
    app.processEvents()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if not dialog.grab().save(str(OUTPUT), "PNG"):
        raise RuntimeError("Could not save the offscreen desktop reference image.")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
