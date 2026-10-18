from __future__ import annotations

import os
import json
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.dialogs.service_invoice_dialog import ServiceInvoiceDialog


def main() -> None:
    output_dir = Path("output/playwright").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(prefix="service-invoice-desktop-", suffix=".db", delete=False)
    database_path = handle.name
    handle.close()
    app = QApplication.instance() or QApplication([])
    db = Database(db_name=database_path, init_mode="full")
    try:
        db.cursor.execute(
            "INSERT INTO customers (name, phone, email, type) VALUES (?, ?, ?, ?)",
            ("QA Service Customer", "", "", "Bireysel"),
        )
        customer_id = int(db.cursor.lastrowid)
        db.cursor.execute(
            "INSERT INTO accounting (customer_id, type, category, date, description, amount, is_invoiced) "
            "VALUES (?, 'Gelir', ?, ?, ?, ?, 0)",
            (customer_id, "Sat\u0131\u015f", "2026-10-10", "TRY service", 100),
        )
        db.cursor.execute(
            "INSERT INTO currency_transactions (customer_id, transaction_type, amount, currency, "
            "exchange_rate, try_equivalent, description, created_at, is_invoiced) VALUES (?, 'DEBIT', ?, ?, ?, ?, ?, ?, 0)",
            (customer_id, 2, "USD", 40, 80, "USD service", "2026-10-10"),
        )
        db.cursor.execute(
            "INSERT INTO exchange_rates (currency, buying_rate, selling_rate, effective_date, created_at) "
            "VALUES ('USD', 39, 40, '2026-10-10', '2026-10-10')"
        )
        db.conn.commit()
        dialog = ServiceInvoiceDialog(db, customer_id)
        dialog.resize(1180, 820)
        dialog.show()
        app.processEvents()
        dialog.setMaximumSize(1300, 900)
        dialog.resize(1180, 820)
        app.processEvents()
        app.processEvents()
        screenshot = output_dir / "service-invoice-desktop-offscreen.png"
        dialog.grab().save(str(screenshot))
        def widget_rect(widget):
            point = widget.mapTo(dialog, QPoint(0, 0))
            return [point.x(), point.y(), widget.width(), widget.height()]

        def item_rect(rect):
            if rect is None:
                return None
            point = dialog.table.viewport().mapTo(dialog, rect.topLeft())
            return [point.x(), point.y(), rect.width(), rect.height()]

        root_item = dialog.table.topLevelItem(0)
        parent_rect = dialog.table.visualItemRect(root_item) if root_item else None
        child_rect = dialog.table.visualItemRect(root_item.child(0)) if root_item and root_item.childCount() else None
        labels = dialog.findChildren(type(dialog.lbl_total_val))
        note_label = next((item for item in labels if item.text().startswith("\u24d8")), None)
        total_label = next((item for item in labels if item.text() == "Toplam:"), None)
        header_title = next((item for item in labels if item.text().startswith("Hizmet Faturas\u0131")), None)

        geometry = {
            "dialog": [dialog.width(), dialog.height()],
            "balance": widget_rect(dialog.lbl_cust_balance),
            "header_title": widget_rect(header_title) if header_title else None,
            "currency_text": dialog.lbl_active_currency.text(),
            "currency": widget_rect(dialog.lbl_active_currency),
            "template": widget_rect(dialog.cmb_template),
            "table_container": widget_rect(dialog.table.parentWidget()),
            "table": widget_rect(dialog.table),
            "table_header": dialog.table.header().height(),
            "group": item_rect(parent_rect),
            "row": item_rect(child_rect),
            "total_frame": widget_rect(dialog.lbl_total_val.parentWidget()),
            "note": widget_rect(note_label) if note_label else None,
            "total_label": widget_rect(total_label) if total_label else None,
            "total": widget_rect(dialog.lbl_total_val),
            "cancel": widget_rect(dialog.btn_cancel),
            "generate": widget_rect(dialog.btn_generate),
            "note_font": {"point_size": note_label.font().pointSizeF(), "italic": note_label.font().italic()} if note_label else None,
            "header_title_font": {"point_size": header_title.font().pointSizeF(), "weight": int(header_title.font().weight())} if header_title else None,
            "currency_font": {"point_size": dialog.lbl_active_currency.font().pointSizeF(), "weight": int(dialog.lbl_active_currency.font().weight())},
            "total_label_font": {"point_size": total_label.font().pointSizeF(), "weight": int(total_label.font().weight())} if total_label else None,
            "total_font": {"point_size": dialog.lbl_total_val.font().pointSizeF(), "weight": int(dialog.lbl_total_val.font().weight())},
            "cancel_font": {"point_size": dialog.btn_cancel.font().pointSizeF(), "weight": int(dialog.btn_cancel.font().weight())},
            "generate_font": {"point_size": dialog.btn_generate.font().pointSizeF(), "weight": int(dialog.btn_generate.font().weight())},
        }
        print(json.dumps({"screenshot": str(screenshot), "geometry": geometry, "rows": len(db.get_uninvoiced_transactions(customer_id)), "balance": dialog.lbl_cust_balance.text()}, ensure_ascii=True))
        dialog.close()
    finally:
        db.close()
        Path(database_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
