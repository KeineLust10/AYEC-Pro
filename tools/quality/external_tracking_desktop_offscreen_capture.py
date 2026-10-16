import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from src.ui.pages.external_tracking_page import ExternalTrackingPage
from src.utils.theme_manager import ThemeManager


OUTPUT = ROOT / "output" / "playwright" / "external-tracking-desktop-offscreen.png"


class FixtureDatabase:
    def get_external_trackings(self):
        rows = [
            (93, "GAR-2026-058", "Demo Musteri 13", "Demo Cihaz 13", "Yetkili Servis TR", "450000013", "2026-09-14", "", "", "Onay Bekliyor", ""),
            (94, "GAR-2026-059", "Demo Musteri 12", "Demo Cihaz 12", "Yetkili Servis TR", "450000012", "2026-09-13", "Yurtici", "", "Dis Serviste", ""),
            (95, "GAR-2026-060", "Demo Musteri 11", "Demo Cihaz 11", "Yetkili Servis TR", "450000011", "2026-09-12", "", "", "Musteriye Hazir", ""),
            (96, "GAR-2026-061", "Demo Musteri 10", "Demo Cihaz 10", "Yetkili Servis TR", "450000010", "2026-09-11", "", "", "Teslim Alindi", ""),
        ]
        rows.extend(
            (97 + index, "GAR-2026-" + str(62 + index), "", "", "", "", "2026-09-10", "", "", "Onay Bekliyor", "")
            for index in range(4)
        )
        rows.extend(
            (101 + index, "GAR-2026-" + str(66 + index), "", "", "", "", "2026-09-10", "", "", "Kargoya Verildi", "")
            for index in range(4)
        )
        rows.extend(
            (105 + index, "GAR-2026-" + str(70 + index), "", "", "", "", "2026-09-10", "", "", "Geri Geldi", "")
            for index in range(6)
        )
        return rows


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    ThemeManager.apply_theme(app, "Koyu Mavi")
    page = ExternalTrackingPage(FixtureDatabase())
    page.resize(1268, 1220)
    page.show()
    app.processEvents()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    saved = page.grab().save(str(OUTPUT), "PNG")
    if not saved:
        raise RuntimeError("Could not save the offscreen desktop reference image.")
    print(str(OUTPUT))


if __name__ == "__main__":
    main()
