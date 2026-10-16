import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from src.ui.pages.project_management.project_detail_dialogs import AddSubDialog


class ProjectDB:
    def __init__(self):
        self.saved = None

    def get_project_units(self, project_id):
        return [
            {"id": 1, "project_id": project_id, "block_name": "Blok A", "unit_no": "A-1"},
            {"id": 2, "project_id": project_id, "block_name": "Blok A", "unit_no": "A-2"},
            {"id": 6, "project_id": project_id, "block_name": "Blok B", "unit_no": "B-1"},
        ]

    def add_subcontractor(self, values):
        self.saved = values


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(("model", "daily", "unit_rate"), [("daily", 1250.5, 0.0), ("unit", 0.0, 1250.5)])
def test_team_dialog_saves_pricing_and_block_selection(qapp, model, daily, unit_rate):
    db = ProjectDB()
    dialog = AddSubDialog(db, 7)
    dialog.txt_name.setText("Ahmet Yilmaz")
    dialog.txt_total.setText("1250,50")
    dialog.cmb_currency.setCurrentIndex(1)
    dialog.payment_radios[model].click()

    assert dialog.unit_all_button.isChecked()
    assert all(check.isChecked() for check in dialog.unit_checks)
    assert not any(button.isChecked() for button in dialog.unit_group_buttons)
    assert not dialog.cmb_job.isEditable()
    assert dialog.cmb_job.count() == 6
    block_a = next(button for button in dialog.unit_group_buttons if button.text() == "Blok A")
    block_a.click()
    assert [check.isChecked() for check in dialog.unit_checks] == [True, True, False]

    dialog.btn_toggle_units.click()
    assert not dialog.unit_list_widget.isHidden()
    dialog.save()

    assert db.saved["payment_model"] == model
    assert db.saved["total_contract_amount"] == 1250.5
    assert db.saved["daily_wage"] == daily
    assert db.saved["unit_rate"] == unit_rate
    assert db.saved["currency"] == "USD"
    assert json.loads(db.saved["assigned_units"]) == [1, 2]



def test_team_dialog_matches_reference_default_assignment_and_capture(qapp):
    db = ProjectDB()
    dialog = AddSubDialog(db, 7)
    assert dialog.unit_all_button.isChecked()
    assert all(check.isChecked() for check in dialog.unit_checks)
    assert not any(button.isChecked() for button in dialog.unit_group_buttons)
    assert dialog.cmb_job.count() == 6
    assert not dialog.cmb_job.isEditable()
    dialog.setFont(QFont("Segoe UI", 9))
    dialog.show()
    qapp.processEvents()
    dialog.setMaximumSize(1600, 1200)
    dialog.resize(840, 1044)
    qapp.processEvents()
    assert not dialog.scroll_area.verticalScrollBar().isVisible()
    output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "project-team-member-desktop.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    assert dialog.card.grab().save(str(output), "PNG")
    dialog.close()
