# -*- coding: utf-8 -*-
"""Quick theme stress test for AYEC app (100ms toggle) with report output."""
import os
import sys
from pathlib import Path
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QWidget

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.utils.theme_manager import ThemeManager


def main():
    app = QApplication(sys.argv)

    # Minimal window so screenshot capture can work when backend supports it.
    w = QWidget()
    w.resize(900, 600)
    w.show()

    interval = int(os.environ.get("AYEC_THEME_STRESS_INTERVAL_MS", "100"))
    switches = int(os.environ.get("AYEC_THEME_STRESS_SWITCHES", "50"))
    capture_every = int(os.environ.get("AYEC_THEME_STRESS_CAPTURE_EVERY", "10"))
    report_dir = os.environ.get("AYEC_THEME_STRESS_REPORT_DIR", "tools/theme_stress_reports")
    report_prefix = os.environ.get("AYEC_THEME_STRESS_REPORT_PREFIX", "script")

    ThemeManager.run_stress_test(
        app,
        window=w,
        interval_ms=interval,
        switches=switches,
        report_dir=report_dir,
        report_prefix=report_prefix,
        capture_every=capture_every,
    )

    # Safety timeout
    QTimer.singleShot(max(5000, switches * interval + 5000), lambda: app.exit(0))

    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
