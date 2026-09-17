import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.pages.report_templates_page import ReportTemplatesPage
from src.utils.page_config import PAGE_MAPPING, PAGE_NAMES


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db:
    def get_fast_notes(self):
        return [
            (index, "Process Detail", f"Report sentence {index:02d}", 1, index)
            for index in range(1, 14)
        ]


def test_report_templates_page_is_registered_and_paginated():
    assert PAGE_MAPPING[147][1] == "ReportTemplatesPage"
    assert PAGE_NAMES[147] == "Rapor C\u00fcmle Kal\u0131plar\u0131"

    page = ReportTemplatesPage(_Db())
    try:
        assert page.total_count == 13
        assert page.table.rowCount() == 10
        assert page.btn_next.isEnabled()

        page.next_page()

        assert page.current_page == 2
        assert page.table.rowCount() == 3
    finally:
        page.close()


def test_report_templates_page_filters_category_and_sentence():
    page = ReportTemplatesPage(_Db())
    try:
        page.search.setText("sentence 12")
        assert page.total_count == 1
        assert page.table.rowCount() == 1
        assert page.table.item(0, 1).text() == "Report sentence 12"
    finally:
        page.close()
