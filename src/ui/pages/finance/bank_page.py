# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
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
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Banka & Finans Yönetimi")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("FinanceTabs")
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget#FinanceTabs::pane {
                border: 1px solid @border;
                background: @surface;
                border-radius: 15px;
                top: -15px;
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
        layout.addWidget(self.tabs)

        # Tab 1: Hesap Listesi
        self.accounts_tab = BankAccountsWidget(self.db)
        self.tabs.addTab(self.accounts_tab, "Banka Hesapları")

        # Tab 2: Krediler
        self.loans_tab = LoansWidget(self.db, self.main_window)
        self.tabs.addTab(self.loans_tab, "Krediler")

    def refresh_data(self):
        if hasattr(self.accounts_tab, 'load_data'):
            self.accounts_tab.load_data()
        if hasattr(self.loans_tab, 'load_loans'):
            self.loans_tab.load_loans()


from src.ui.pages.finance.bank_loans_widget import LoansWidget
