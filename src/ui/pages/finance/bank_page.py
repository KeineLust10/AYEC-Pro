# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.pages.finance.bank_accounts_widget import BankAccountsWidget
from src.ui.pages.finance.bank_loans_widget import LoansWidget


class BankPage(QWidget):
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("FinanceTabs")
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget#FinanceTabs::pane {
                border: 0;
                background: @finance_canvas;
            }
            QTabBar::tab {
                background: @surface_alt;
                color: @text_muted;
                padding: 12px 25px;
                margin-right: 8px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-weight: bold;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background: @accent;
                color: @selection_text;
                margin-bottom: -1px;
            }
            QTabBar::tab:hover {
                background: @border;
            }
        """))
        self.tabs.tabBar().hide()
        layout.addWidget(self.tabs)

        # Tab 1: Hesap Listesi
        self.accounts_tab = BankAccountsWidget(self.db)
        self.tabs.addTab(self.accounts_tab, "Banka Hesapları")

        # Tab 2: Krediler
        self.loans_tab = LoansWidget(self.db, self.main_window)
        self.tabs.addTab(self.loans_tab, "Krediler")
        self.accounts_tab.btn_loans.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.loans_tab.btn_accounts.clicked.connect(lambda: self.tabs.setCurrentIndex(0))

    def refresh_data(self):
        if hasattr(self.accounts_tab, 'load_data'):
            self.accounts_tab.load_data()
        if hasattr(self.loans_tab, 'load_loans'):
            self.loans_tab.load_loans()


from src.ui.pages.finance.bank_loans_widget import LoansWidget
