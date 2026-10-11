import os
import sys
import unittest
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from src.ui.pages.project_management.project_detail_components import FinanceTab


APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)


class FinanceDatabaseStub:
    def get_setting(self, _key, default=""):
        return default or "TRY"

    def get_project_currency(self, _project_id):
        return "TRY", 1

    def get_project_financials(self, _project_id):
        return {"income": 0, "expense": 0, "profit": 0,
                "income_pending": 5000, "expense_pending": 0}

    def get_project_transactions(self, _project_id):
        return [
            {"id": 1, "date": "2026-09-21", "type": "Gelir", "category": "Avans",
             "description": "Project advance", "payment_method": "Bank transfer", "amount": 5000,
             "status": "Bekliyor", "original_amount": None, "original_currency": "TRY",
             "invoice_no": "FTR-01", "document_no": "FTR-01", "counterparty": "Client"},
            {"id": 2, "date": "2026-09-22", "type": "Gider", "category": "Malzeme",
             "description": "Cable supply", "payment_method": "Credit card", "amount": 14250,
             "status": "\u00d6dendi", "original_amount": None, "original_currency": "TRY",
             "invoice_no": "IRS-02", "document_no": "IRS-02", "counterparty": "Vendor"},
            {"id": 3, "date": "2026-09-24", "type": "Gider", "category": "\u0130\u015f\u00e7ilik",
             "description": "Subcontractor site installation advance", "payment_method": "Bank transfer", "amount": 8500,
             "status": "\u00d6dendi", "original_amount": None, "original_currency": "TRY",
             "invoice_no": "HKD-2026-01", "document_no": "HKD-2026-01", "counterparty": "Ege Altyapi Ltd."},
            {"id": 4, "date": "2026-09-25", "type": "Gider", "category": "Hakedi\u015f",
             "description": "Infrastructure cabling and tray installation", "payment_method": "Cash", "amount": 3750,
             "status": "\u00d6dendi", "original_amount": None, "original_currency": "TRY",
             "invoice_no": "MAK-09-112", "document_no": "MAK-09-112", "counterparty": "Project cash desk"},
        ]


class Part9ProjectFinanceLayoutTests(unittest.TestCase):
    def setUp(self):
        self.page = FinanceTab(FinanceDatabaseStub(), 1)
        self.page._fmt_project_amount = lambda amount: f"{amount:.0f} TRY"
        self.page._pretty_txn_description = lambda txn, _currency, _rate: txn["description"]
        self.page.load_data()

    def tearDown(self):
        self.page.close()

    def test_reference_finance_dashboard_uses_full_width_eight_column_ledger(self):
        self.assertEqual(self.page.table.columnCount(), 8)
        self.assertEqual(self.page.table.rowCount(), 4)
        self.assertTrue(self.page.table.verticalHeader().isHidden())
        self.assertIn("Client", self.page.table.item(0, 4).text())
        self.assertGreater(self.page.table.horizontalHeader().count(), 0)
        self.assertIn("\u0130\u015flem", self.page.search_input.placeholderText())
        self.page.setFont(QFont("Segoe UI", 10))
        self.page.resize(1280, 1024)
        self.page.show()
        APP.processEvents()
        self.assertFalse(self.page.grab().isNull())
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "project-finance-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.page.grab().save(str(output), "PNG"))

    def test_finance_filters_update_visible_rows(self):
        self.page.filter_type.setCurrentIndex(self.page.filter_type.findData("Gider"))
        self.assertEqual(self.page.table.rowCount(), 3)
        self.assertEqual(self.page.table.item(0, 2).text(), "Gider")
        self.page.filter_type.setCurrentIndex(0)
        self.page.filter_status.setCurrentIndex(self.page.filter_status.findData("paid"))
        self.assertEqual(self.page.table.rowCount(), 3)
        self.assertEqual(self.page.table.item(0, 2).text(), "Gider")
        self.page.filter_status.setCurrentIndex(0)
        self.page.filter_date.setCurrentIndex(self.page.filter_date.findData("2026-09"))
        self.assertEqual(self.page.table.rowCount(), 4)
        self.page.filter_date.setCurrentIndex(0)
        self.page.search_input.setText("no-match")
        self.assertEqual(self.page.table.rowCount(), 0)
        self.page._reset_filters()
        self.assertEqual(self.page.table.rowCount(), 4)

    def test_finance_csv_export_matches_eight_column_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "project-finance.csv"
            with patch(
                "src.ui.pages.project_management.project_detail_components.QFileDialog.getSaveFileName",
                return_value=(str(output), ""),
            ), patch("src.ui.pages.project_management.project_detail_components.show_success"):
                self.page._export_report("csv")
            with output.open("r", encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file, delimiter=";"))
        self.assertEqual(len(rows[0]), 8)
        self.assertEqual(len(rows[1]), 8)


if __name__ == "__main__":
    unittest.main()
