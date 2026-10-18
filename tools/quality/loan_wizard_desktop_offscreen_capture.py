from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication, QLabel

from src.database import Database
from src.ui.dialogs.loan_wizard_advanced import AdvancedLoanWizard


def main() -> None:
    output_dir = Path("output/playwright").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    db = Database(db_name=":memory:", init_mode="full")
    dialog = AdvancedLoanWizard(db)
    if len(dialog.step_pages) < 4:
        raise RuntimeError("The document upload step is not available in the native wizard.")
    dialog.current_step_idx = 0
    dialog.stack.setCurrentIndex(0)
    dialog._update_stepper_ui()
    dialog.show()
    app.processEvents()
    dialog.setMaximumSize(1400, 900)
    dialog.resize(1320, 820)
    dialog.move(0, 0)
    app.processEvents()
    def rect(widget):
        point = widget.mapTo(dialog, QPoint(0, 0))
        return [point.x(), point.y(), widget.width(), widget.height()]

    screenshots = []
    geometries = {}
    final_index = len(dialog.step_pages) - 1
    dialog.wizard_data = {
        "bank_name": "QA Bank (QA)",
        "title": "QA Loan",
        "loan_type": "Taksitli Ticari Kredi",
        "principal": 100000,
        "interest_rate": 24,
        "months": 36,
        "start_date": date(2026, 10, 17),
        "kkdf_rate": 0,
        "bsmv_rate": 0,
        "notes": "",
        "attachments": [],
    }
    for index, page in enumerate(dialog.step_pages):
        dialog.current_step_idx = index
        dialog.stack.setCurrentIndex(index)
        if index == final_index:
            page.set_data(dialog.wizard_data)
        dialog.btn_back.setEnabled(index > 0)
        dialog.btn_next.setVisible(index < final_index)
        dialog.btn_save.setVisible(index == final_index)
        dialog._update_stepper_ui()
        app.processEvents()
        screenshot = output_dir / f"loan-wizard-desktop-step{index + 1}-matched.png"
        if not dialog.grab().save(str(screenshot)):
            raise RuntimeError(f"Could not save native wizard step {index + 1} capture.")
        screenshots.append(str(screenshot))
        if index == 2:
            page = dialog.step_pages[index]
            geometries["documents"] = {
                "dialog": [dialog.width(), dialog.height()],
                "stepper": rect(dialog.stepper_container),
                "document_step": rect(page),
                "contract_zone": rect(page.drop_contract),
                "payment_plan_zone": rect(page.drop_plan),
                "notes_label": rect(next(label for label in page.findChildren(QLabel) if label.text().startswith("\U0001F4DD"))),
                "notes": rect(page.txt_notes),
                "file_list": rect(page.scroll_files),
                "back": rect(dialog.btn_back),
                "next": rect(dialog.btn_next),
            }
        elif index == 0:
            geometries["step_1"] = {
                "dialog": [dialog.width(), dialog.height()],
                "page": rect(page),
                "bank": rect(page.cmb_bank),
                "loan_type": rect(page.cmb_loan_type),
                "title": rect(page.txt_title),
                "eft": rect(page.txt_eft),
                "swift": rect(page.txt_swift),
            }
        elif index == 1:
            geometries["step_2"] = {
                "dialog": [dialog.width(), dialog.height()],
                "page": rect(page),
                "principal": rect(page.spin_principal),
                "interest": rect(page.spin_interest),
                "months": rect(page.spin_months),
                "first_payment_date": rect(page.date_start),
                "kkdf": rect(page.spin_kkdf),
                "bsmv": rect(page.spin_bsmv),
                "preview": rect(page.preview_card),
            }
        elif index == 3:
            geometries["step_4"] = {
                "dialog": [dialog.width(), dialog.height()],
                "page": rect(page),
                "bank_card": rect(page.card_bank),
                "finance_card": rect(page.card_finance),
                "extras_card": rect(page.card_extras),
                "payment_table": rect(page.table),
            }
    print(json.dumps({"screenshots": screenshots, "geometry": geometries}, ensure_ascii=True))
    dialog.close()
    db.close()
    app.quit()


if __name__ == "__main__":
    main()
