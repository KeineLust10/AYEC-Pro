# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont

from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page
from src.ui.pages.pc_builder_page import PCBuilderPage
from src.ui.pages.smart_home_sales_page import SmartHomeSalesPage
from src.utils.system_config import SystemConfig
from src.utils.theme_colors import theme_qss


class SalesHubPage(QWidget):
    def __init__(self, db, main_window=None, initial_tab=0, sector_manager=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.sector_manager = sector_manager or getattr(main_window, "sector_manager", None)
        self.is_automotive = self._is_automotive()
        requested_tab = int(initial_tab or 0)
        allowed_tabs = (0,) if self.is_automotive else (0, 1, 2)
        self.initial_tab = requested_tab if requested_tab in allowed_tabs else 0
        self.sales_page = None
        self.pc_builder_page = None
        self.smart_home_page = None
        self._build_ui()

    def _is_automotive(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def _build_ui(self):
        self.setObjectName("SalesHubPage")
        self.setStyleSheet(theme_qss("""
            QWidget#SalesHubPage {
                background: transparent;
            }
        """))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("SalesHubTabs")
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane {
                border: none;
                background: transparent;
                top: 4px;
            }
            QTabBar {
                background: transparent;
            }
            QTabBar::tab {
                background: @surface;
                color: @text_muted;
                border: 1px solid @border;
                padding: 8px 16px;
                min-width: 130px;
                min-height: 36px;
                border-radius: 8px;
                margin-right: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 @accent,
                    stop:1 @accent_hover);
                color: @selection_text;
                border-color: @accent;
                padding: 8px 16px;
            }
            QTabBar::tab:hover {
                color: @text;
                border-color: @accent;
                background: @surface_alt;
            }
            QTabBar::tab:selected:hover {
                color: @selection_text;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 @accent,
                    stop:1 @accent_hover);
            }
        """))
        tab_bar = self.tabs.tabBar()
        tab_bar.setDocumentMode(False)
        tab_bar.setExpanding(False)
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setElideMode(tab_bar.elideMode())
        tab_bar.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

        self.tabs.addTab(self._build_placeholder(), "💼  Satış İşlemi")
        if not self.is_automotive:
            self.tabs.addTab(self._build_placeholder(), "🏠  Akıllı Ev Satış")
            self.tabs.addTab(self._build_placeholder(), "🖥️  Bilgisayar Topla")
        self._normalize_tab_titles()
        self.tabs.currentChanged.connect(self._ensure_tab_loaded)
        self.tabs.setCurrentIndex(self.initial_tab)
        self._ensure_tab_loaded(self.initial_tab)

        layout.addWidget(self.tabs)

    def _build_placeholder(self):
        page = QWidget()
        page.setStyleSheet(theme_qss("""
            QWidget {
                background: transparent;
            }
        """))
        return page

    def _normalize_tab_titles(self):
        self.tabs.setTabText(0, "Güvenlik Sistemleri")
        if not self.is_automotive and self.tabs.count() > 2:
            self.tabs.setTabText(1, "Akıllı Ev")
            self.tabs.setTabText(2, "Bilgisayar")

    def _ensure_tab_loaded(self, index):
        if index == 0 and self.sales_page is None:
            self.sales_page = NewTransactionV2Page(self.db, self.main_window)
            old = self.tabs.widget(0)
            self.tabs.removeTab(0)
            self.tabs.insertTab(0, self.sales_page, "💼  Satış İşlemi")
            if old is not None:
                old.deleteLater()
            self._normalize_tab_titles()
            self.tabs.setCurrentIndex(0)
            return

        if self.is_automotive:
            return

        if index == 1 and self.smart_home_page is None:
            self.smart_home_page = SmartHomeSalesPage(self.db, self.main_window)
            old = self.tabs.widget(1)
            self.tabs.removeTab(1)
            self.tabs.insertTab(1, self.smart_home_page, "🏠  Akıllı Ev Satış")
            if old is not None:
                old.deleteLater()
            self._normalize_tab_titles()
            self.tabs.setCurrentIndex(1)
            return

        if index == 2 and self.pc_builder_page is None:
            self.pc_builder_page = PCBuilderPage(self.db, self.main_window)
            old = self.tabs.widget(2)
            self.tabs.removeTab(2)
            self.tabs.insertTab(2, self.pc_builder_page, "🖥️  Bilgisayar Topla")
            if old is not None:
                old.deleteLater()
            self._normalize_tab_titles()
            self.tabs.setCurrentIndex(2)
            return

    def refresh_data(self):
        pages = [self.sales_page]
        if not self.is_automotive:
            pages.extend([self.smart_home_page, self.pc_builder_page])
        for page in pages:
            if hasattr(page, "refresh_data") and callable(getattr(page, "refresh_data")):
                try:
                    page.refresh_data()
                except Exception:
                    pass

    def refresh_financial_defaults(self):
        pages = [self.sales_page]
        if not self.is_automotive:
            pages.extend([self.smart_home_page, self.pc_builder_page])
        for page in pages:
            if page and hasattr(page, "refresh_financial_defaults"):
                page.refresh_financial_defaults()

    def load_offer_for_edit(self, offer_id):
        self.tabs.setCurrentIndex(0)
        self._ensure_tab_loaded(0)
        if not self.sales_page:
            raise RuntimeError("Sales page is not available.")
        if not hasattr(self.sales_page, "load_offer_for_edit"):
            raise RuntimeError("Offer editor is not available.")
        return self.sales_page.load_offer_for_edit(int(offer_id))


class SalesHubPCBuilderPage(SalesHubPage):
    def __init__(self, db, main_window=None, sector_manager=None):
        super().__init__(db, main_window=main_window, initial_tab=2, sector_manager=sector_manager)
