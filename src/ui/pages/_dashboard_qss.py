
# -*- coding: utf-8 -*-
from PyQt6.QtGui import QColor
from src.utils.theme_colors import theme_qss, tc
from ._dashboard_utils import is_classic_appearance, contrast_on, hover_on


def card_shell_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QFrame#DashboardCardShell {
            background-color: #FFFFFF;
            border: 1px solid #B8C0CC;
            border-radius: 0px;
        }
        """
    return theme_qss("""
    QFrame#DashboardCardShell {
        background-color: @surface;
        border: 1px solid @border;
        border-radius: 22px;
    }
    """)


def recent_container_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QFrame#DashboardCardShell {
            background-color: transparent;
            border: none;
            border-radius: 0px;
        }
        """
    return theme_qss("""
    QFrame#DashboardCardShell {
        background-color: transparent;
        border: none;
        border-radius: 0px;
    }
    """)


def actions_card_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QFrame#DashboardActionsCard {
            background-color: #F3F4F6;
            border: 1px solid #B8C0CC;
            border-radius: 0px;
        }
        """
    return theme_qss("""
    QFrame#DashboardActionsCard {
        background-color: @surface_alt;
        border: 1px solid @border;
        border-radius: 22px;
    }
    """)


def filter_strip_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QFrame#TakipOnlineFilterStrip {
            background-color: #F3F4F6;
            border-top: 1px solid #B8C0CC;
            border-bottom: 1px solid #B8C0CC;
        }
        """
    return theme_qss("""
    QFrame#TakipOnlineFilterStrip {
        background-color: @surface_alt;
        border-top: 3px solid @warning;
        border-bottom: 1px solid @border;
    }
    """)


def dashboard_tabs_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QTabWidget#DashboardMainTabs::pane {
            background-color: #F3F4F6;
            border: none;
        }
        QTabWidget#DashboardMainTabs QTabBar::tab {
            background: #FFFFFF;
            color: #111827;
            padding: 8px 18px;
            border: 1px solid #B8C0CC;
            border-bottom: none;
            border-radius: 0px;
            margin-right: 2px;
            min-height: 18px;
            font-weight: 700;
        }
        QTabWidget#DashboardMainTabs QTabBar::tab:selected {
            background: #FFFFFF;
            color: #0F3F74;
            border-bottom: 2px solid #2563EB;
        }
        QTabWidget#DashboardMainTabs QTabBar::tab:hover {
            background: #EAF2FF;
            color: #111827;
            border-color: #8BAFD8;
        }
        QTabWidget#DashboardMainTabs QTabBar::tab:pressed {
            background: #DCEBFF;
            color: #111827;
        }
        """
    return theme_qss("""
    QTabWidget::pane { background-color: @surface_alt; border: none; }
    QTabBar::tab { background: @surface; color: @text; padding: 8px 18px; border: 1px solid @border; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px; }
    QTabBar::tab:selected { background: @surface_alt; font-weight: bold; border-bottom: 2px solid @accent; }
    QTabBar::tab:hover { background: @surface_alt; }
    """)


def takiponline_table_qss(db=None):
    if is_classic_appearance(db=db):
        return """
        QTableWidget {
            border: 1px solid #B8C0CC;
            background-color: #FFFFFF;
            gridline-color: #D1D5DB;
            alternate-background-color: #F7F8FA;
            color: #111827;
            selection-background-color: #DCEBFF;
            selection-color: #111827;
        }
        QHeaderView {
            background-color: #E5E7EB;
            color: #111827;
            border: none;
        }
        QHeaderView::section {
            background-color: #E5E7EB;
            color: #111827;
            padding-left: 6px;
            padding-right: 6px;
            border: none;
            border-right: 1px solid #B8C0CC;
            border-bottom: 1px solid #B8C0CC;
            font-weight: 700;
            font-size: 11px;
            min-height: 24px;
        }
        QTableCornerButton::section {
            background-color: #E5E7EB;
            border: none;
            border-right: 1px solid #B8C0CC;
            border-bottom: 1px solid #B8C0CC;
        }
        QTableWidget::item {
            padding-left: 6px;
            padding-right: 6px;
            border-bottom: 1px solid #D1D5DB;
            border-right: 1px solid #E5E7EB;
            color: #111827;
            font-size: 11px;
        }
        QTableWidget::item:alternate {
            background-color: #F7F8FA;
            color: #111827;
        }
        QTableWidget::item:selected {
            background-color: #DCEBFF;
            color: #111827;
            border: none;
            outline: none;
        }
        """
    return theme_qss("""
    QTableWidget {
        border: none;
        background-color: @surface;
        gridline-color: @border;
        alternate-background-color: @surface_alt;
        color: @text;
    }
    QHeaderView::section {
        background-color: @selection_bg;
        color: @selection_text;
        padding-left: 10px;
        padding-right: 10px;
        border: none;
        border-right: 1px solid @border;
        border-bottom: 1px solid @border;
        font-weight: 900;
        font-size: 12px;
    }
    QTableWidget::item {
        padding-left: 10px;
        padding-right: 10px;
        border-bottom: 1px solid @border;
        border-right: 1px solid @border;
        color: @text;
        font-size: 12px;
    }
    QTableWidget::item:alternate {
        background-color: @surface_alt;
        color: @text;
    }
    QTableWidget::item:selected {
        background-color: @selection_bg;
        color: @selection_text;
        border: none;
        outline: none;
    }
    """)


def insight_card_qss(accent_color):
    return theme_qss(f"""
        QFrame#DashboardInsightCard {{
            background-color: @surface;
            border: 1px solid @border;
            border-left: 4px solid {accent_color};
            border-radius: 18px;
        }}
        QFrame#DashboardInsightCard:hover {{
            background-color: @surface_alt;
            border-color: {accent_color};
            border-left: 4px solid {accent_color};
        }}
    """)
