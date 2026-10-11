import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.pages import sales_hub_page as module


def test_compact_reference_tabs_keep_original_lazy_page_mapping(monkeypatch):
    app = QApplication.instance() or QApplication([])
    created = []
    database = object()
    main_window = object()

    def factory(name):
        def create(db, window):
            assert db is database
            assert window is main_window
            page = QWidget()
            page.setObjectName(name)
            created.append(name)
            return page
        return create

    monkeypatch.setattr(module.SalesHubPage, '_is_automotive', lambda self: False)
    monkeypatch.setattr(module, 'NewTransactionV2Page', factory('sales'))
    monkeypatch.setattr(module, 'SmartHomeSalesPage', factory('smart_home'))
    monkeypatch.setattr(module, 'PCBuilderPage', factory('pc_builder'))
    page = module.SalesHubPage(database, main_window)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1320, 1226)
        page.show()
        app.processEvents()
        bar = page.tabs.tabBar()
        assert bar.height() <= 38
        assert page.layout().contentsMargins().top() == 0
        assert 'border-radius: 4px' in page.tabs.styleSheet()
        assert 'qlineargradient' not in page.tabs.styleSheet()
        assert page.tabs.count() == 3
        assert created == ['sales']
        for index, attribute in ((1, 'smart_home_page'), (2, 'pc_builder_page'), (0, 'sales_page')):
            QTest.mouseClick(bar, Qt.MouseButton.LeftButton, pos=bar.tabRect(index).center())
            app.processEvents()
            assert page.tabs.currentIndex() == index
            assert page.tabs.currentWidget() is getattr(page, attribute)
        assert sorted(created) == ['pc_builder', 'sales', 'smart_home']
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
