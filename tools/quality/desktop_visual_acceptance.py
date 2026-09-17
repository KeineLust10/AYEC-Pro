from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QPushButton,
    QWidget,
)


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def image_has_visual_content(widget: QWidget) -> tuple[bool, int]:
    image = widget.grab().toImage()
    if image.isNull():
        return False, 0
    colors: set[int] = set()
    x_step = max(1, image.width() // 32)
    y_step = max(1, image.height() // 18)
    for y_pos in range(0, image.height(), y_step):
        for x_pos in range(0, image.width(), x_step):
            colors.add(image.pixel(x_pos, y_pos))
            if len(colors) >= 8:
                return True, len(colors)
    return len(colors) >= 2, len(colors)


def visible_table_selection_issues(widget: QWidget) -> list[str]:
    issues: list[str] = []
    for table in widget.findChildren(QAbstractItemView):
        if not table.isVisible() or isinstance(table, QHeaderView):
            continue
        if (
            table.selectionBehavior()
            != QAbstractItemView.SelectionBehavior.SelectRows
        ):
            name = table.objectName() or table.__class__.__name__
            issues.append(name)
    return issues


def clipped_button_warnings(widget: QWidget) -> list[str]:
    warnings: list[str] = []
    for button in widget.findChildren(QPushButton):
        if not button.isVisible() or not button.text().strip():
            continue
        required = button.fontMetrics().horizontalAdvance(button.text()) + 18
        if button.width() < required and button.width() >= 44:
            name = button.objectName() or button.text()
            warnings.append(name)
    return warnings


def page_factories(db):
    from src.ui.pages.customers_page import CustomersPage
    from src.ui.pages.product_groups_page import ProductGroupsPage
    from src.ui.pages.purchase_order_pages import NewPurchaseOrderPage, OffersPage
    from src.ui.pages.stock_page import StockPage
    from src.ui.pages.supplier_management_page import SupplierManagementPage

    return {
        "customers": lambda: CustomersPage(db),
        "stock": lambda: StockPage(db),
        "offers": lambda: OffersPage(db),
        "purchase_order": lambda: NewPurchaseOrderPage(db),
        "product_groups": lambda: ProductGroupsPage(db),
        "suppliers": lambda: SupplierManagementPage(db),
    }


def run(output_root: Path) -> dict[str, object]:
    from src.database import Database
    from src.utils.theme_manager import ThemeManager

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Segoe UI", 9))
    db = Database(":memory:")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = output_root.resolve() / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, object]] = []

    try:
        for theme_name in ("AYEC", "Koyu Mavi"):
            for page_name, factory in page_factories(db).items():
                page = factory()
                page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
                page.resize(1600, 900)
                ThemeManager.apply_theme(
                    app,
                    theme_name,
                    window=page,
                    animate=False,
                )
                page.show()
                app.processEvents()
                screenshot = output_dir / (
                    f"{theme_name.lower().replace(' ', '_')}_{page_name}.png"
                )
                saved = bool(page.grab().save(str(screenshot), "PNG"))
                has_content, sampled_colors = image_has_visual_content(page)
                selection_issues = visible_table_selection_issues(page)
                button_warnings = clipped_button_warnings(page)
                passed = saved and has_content and not selection_issues
                results.append(
                    {
                        "theme": theme_name,
                        "page": page_name,
                        "screenshot": str(screenshot),
                        "saved": saved,
                        "has_visual_content": has_content,
                        "sampled_colors": sampled_colors,
                        "table_selection_issues": selection_issues,
                        "clipped_button_warnings": button_warnings,
                        "status": "passed" if passed else "failed",
                    }
                )
                page.close()
                page.deleteLater()
                app.processEvents()
    finally:
        if hasattr(db, "close"):
            db.close()

    passed = all(item["status"] == "passed" for item in results)
    report = {
        "status": "passed" if passed else "failed",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "resolution": [1600, 900],
        "results": results,
    }
    report_path = output_dir / "desktop_visual_acceptance.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report["report"] = str(report_path)
    if not passed:
        raise RuntimeError(f"Desktop visual acceptance failed: {report_path}")
    return report


def main() -> int:
    report = run(ROOT / "artifacts" / "desktop_visual_acceptance")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": report["report"],
                "screenshots": len(report["results"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
