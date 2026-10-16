import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.invoice_page import InvoiceCreationPage


def test_einvoice_composer_preserves_line_math_actions_and_compact_layout(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "einvoice_composer.db"))
    page = InvoiceCreationPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1080, 800)
        page.show()
        app.processEvents()

        assert page.items_table.columnCount() == 11
        assert page.items_table.rowCount() == 1
        if page.cmb_customer.count() == 0:
            page.cmb_customer.addItem("Visual Test Customer", 1)
        page.cmb_customer.setCurrentIndex(0)
        app.processEvents()
        assert not page.customer_registered_badge.isHidden()
        page.cmb_customer.setCurrentIndex(-1)
        app.processEvents()
        assert page.customer_registered_badge.isHidden()
        assert page._invoice_responsive_filter.stacked
        assert page._invoice_aside.parentWidget() is page._invoice_primary
        assert page._invoice_aside.width() == page._invoice_primary.width() - 42
        assert sum(page.items_table.columnWidth(column) for column in range(7)) <= page.items_table.viewport().width()

        page.resize(1400, 800)
        app.processEvents()
        assert not page._invoice_responsive_filter.stacked
        assert page._invoice_mobile_layouts["ribbon"].direction().name == "LeftToRight"
        assert page.master_data_heading.y() == 2
        assert not page.master_data_icon.pixmap().isNull()
        assert page._invoice_aside_scroll.widget() is page._invoice_aside
        assert page._invoice_aside_scroll.width() == 462
        reconcile_states = []
        page.chk_auto_reconcile.toggled.connect(reconcile_states.append)
        page.chk_auto_reconcile.click()
        page.chk_auto_reconcile.click()
        assert reconcile_states == [False, True]
        page.resize(1080, 800)
        app.processEvents()
        assert page._invoice_responsive_filter.stacked

        page.resize(390, 800)
        app.processEvents()
        app.processEvents()
        assert page.width() == 390
        assert page._invoice_primary.width() <= page.width()
        assert page._invoice_aside.width() <= page._invoice_primary.width()
        assert page.items_table.width() <= page._invoice_primary.width()
        assert page._invoice_mobile_layouts["ribbon"].direction().name == "TopToBottom"

        page.resize(1400, 800)
        app.processEvents()
        assert not page._invoice_responsive_filter.stacked
        assert page._invoice_mobile_layouts["ribbon"].direction().name == "LeftToRight"
        assert page._invoice_mobile_layouts["grids"][1][0].itemAtPosition(0, 4) is not None

        delegate = page.items_table.itemDelegate()
        assert delegate.INPUT_COLUMNS == frozenset((3, 4, 5, 6, 7))
        assert page.items_table.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAsNeeded
        assert not any(page.items_table.isColumnHidden(column) for column in range(7, 11))
        unit_index = page.items_table.model().index(0, 4)
        unit_editor = delegate.createEditor(None, None, unit_index)
        delegate.setEditorData(unit_editor, unit_index)
        unit_editor.setCurrentText("Hizmet")
        delegate.setModelData(unit_editor, page.items_table.model(), unit_index)
        assert page.items_table.item(0, 4).text() == "Hizmet"
        page.items_table.item(0, 4).setText("Adet")

        page.items_table.item(0, 1).setText("Service")
        page.items_table.item(0, 3).setText("2")
        page.items_table.item(0, 5).setText("100")
        page.items_table.item(0, 6).setText("10")
        page.items_table.item(0, 7).setText("20")
        page.calculate_totals()
        assert page.get_float(0, 8) == 36.0
        assert page.get_float(0, 9) == 216.0
        assert page.current_total_try == 216.0

        page.btn_add_item.click()
        assert page.items_table.rowCount() == 2
        page.items_table.setCurrentCell(0, 1)
        page.btn_remove_item.click()
        assert page.items_table.rowCount() == 1
        page.items_table.setCurrentCell(0, 1)
        page.items_table.cellWidget(0, 10).click()
        assert page.items_table.rowCount() == 0
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
