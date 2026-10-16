import os
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.pages.customers.logic.customer_manager import CustomerManager
from src.ui.pages.customers_page_parts import PartnersPage


APP = QApplication.instance() or QApplication([])


def test_partner_page_defers_initial_query_until_visible_and_loads_once():
    with patch.object(CustomerManager, "get_customers", return_value=[]) as get_customers:
        page = PartnersPage(SimpleNamespace())

        page.show()
        APP.processEvents()
        page.hide()
        QTest.qWait(130)
        get_customers.assert_not_called()

        page.show()
        APP.processEvents()
        QTest.qWait(180)
        get_customers.assert_called_once_with()

        page.hide()
        page.show()
        APP.processEvents()
        QTest.qWait(180)
        get_customers.assert_called_once_with()
        page.close()
