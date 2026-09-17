"""Capture fresh AYEC Pro screens from the active desktop database."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import Database
from src.ui.main_window import MainWindow


PAGES = (
    (40, "dashboard"),
    (21, "customers"),
    (50, "stock"),
    (30, "appointments"),
    (41, "service_board"),
    (101, "finance"),
)


class LiveCapture:
    def __init__(self, output_root: Path) -> None:
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.db = Database()
        self.output_dir = output_root / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self.results: list[dict[str, object]] = []
        self.page_index = 0

        MainWindow.start_initial_tasks = lambda window: None
        MainWindow.configure_auto_web_sync = lambda window, enabled: None
        self.window = MainWindow(
            self.db,
            user_data={
                "username": "ayec_demo",
                "full_name": "AYEC Demo",
                "role": "admin",
            },
        )
        self.window.showMaximized()

    def start(self) -> int:
        QTimer.singleShot(800, self.capture_next)
        return self.app.exec()

    def capture_next(self) -> None:
        if self.page_index >= len(PAGES):
            self.finish()
            return
        page_id, page_name = PAGES[self.page_index]
        self.window.on_menu_click(page_id)
        if page_name == "customers":
            page = self.window.pages.get(page_id)
            if page is not None and hasattr(page, "inp_search"):
                page.inp_search.setText("Test M\u00fc\u015fterisi")
                page.search_query = "Test M\u00fc\u015fterisi"
                page.refresh_data()
        QTimer.singleShot(1800, lambda: self.save_page(page_id, page_name))

    def save_page(self, page_id: int, page_name: str) -> None:
        path = self.output_dir / f"ayec_live_{page_name}.png"
        saved = bool(self.window.grab().save(str(path), "PNG"))
        self.results.append(
            {
                "page_id": page_id,
                "page": page_name,
                "path": str(path),
                "saved": saved,
                "bytes": path.stat().st_size if path.exists() else 0,
            }
        )
        self.page_index += 1
        QTimer.singleShot(250, self.capture_next)

    def finish(self) -> None:
        report_path = self.output_dir / "capture_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "database": str(self.db._db_name),
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "screens": self.results,
                },
                indent=2,
                ensure_ascii=True,
            ),
            encoding="utf-8",
        )
        print(str(report_path))
        self.window.hide()
        self.db.close()
        self.app.exit(0)


def main() -> int:
    capture = LiveCapture(ROOT / "artifacts" / "live-program-screens")
    return capture.start()


if __name__ == "__main__":
    raise SystemExit(main())
