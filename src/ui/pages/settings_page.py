# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QTabWidget, QScrollArea, QFrame, QFileDialog, QMessageBox, QLineEdit,
                             QDialog, QListWidget, QListWidgetItem, QGraphicsDropShadowEffect,
                             QComboBox, QCheckBox, QStackedWidget, QTextEdit, QPlainTextEdit,
                             QGridLayout, QFormLayout, QSpinBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QSizePolicy, QSpacerItem, QMenu, QGroupBox,
                             QDateEdit, QTimeEdit, QDoubleSpinBox)
from PyQt6.QtCore import Qt, QTimer, QSize, QDate, QThread, pyqtSignal, QEvent
from PyQt6.QtGui import QIcon, QFont, QAction, QColor
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
import os
import shutil
import sys
import json
from datetime import datetime
from src.utils.theme_manager import ThemeManager
from src.utils.security_manager import SecurityManager
from src.utils import message_helper
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.design_system import DesignTokens
from src.utils.appearance_mode import AppearanceModeManager
from src.ui.widgets.modern_dialog import ModernDialog

# Modülerleştirilmiş widget'lar (alias vererek dahili sınıflarla çakışmayı önler)
from src.ui.pages.settings_widgets.company_settings import CompanySettingsWidget
import importlib
from src.utils.logger import logger

# --- STYLING CONSTANTS ---
SIDEBAR_BG = tc("surface_alt")
SIDEBAR_TEXT = tc("text")
SIDEBAR_HOVER = tc("surface_alt")
SIDEBAR_ACTIVE = tc("selection_bg")
SIDEBAR_ACTIVE_TEXT = tc("accent")
CONTENT_BG = tc("surface")
CARD_BG = tc("surface")
BORDER_COLOR = tc("border")


from src.ui.pages.settings_sidebar import PremiumSettingsSidebar, PlaceholderWidget

class SettingsPage(QWidget):
    """
    Yenilenmiş Ayarlar Sayfası
    Sol tarafta menü, sağ tarafta içerik.
    """
    def __init__(self, db, main_window=None):
        super().__init__(main_window)
        self.setObjectName("SettingsPage")
        self.db = db
        self.main_window = main_window
        self._shell_menu = None
        self.init_ui()
        self._shell_menu = getattr(getattr(main_window, "app_sidebar", None), "side_menu", None)
        if self._shell_menu is not None:
            self._shell_menu.navigation_layout_about_to_change.connect(self._restore_shell_sidebar)
            self._shell_menu.navigation_layout_changed.connect(self._sync_shell_sidebar)
            self._shell_menu.installEventFilter(self)

    def _shell_sidebar_width(self):
        menu = getattr(getattr(self.main_window, "app_sidebar", None), "side_menu", None)
        if menu is not None and hasattr(menu, "expanded_width_for_window"):
            return menu.expanded_width_for_window()
        viewport_width = self.main_window.width() if self.main_window is not None else 0
        return 260 if viewport_width and viewport_width <= 1366 else 300

    def _restore_shell_sidebar(self):
        if self.main_window is not None:
            self.main_window._settings_header_mode = False
        self.sidebar.hide()
        if hasattr(self, "settings_page_selector"):
            self.settings_page_selector.show()
        shell_sidebar = getattr(self.main_window, "app_sidebar", None)
        if shell_sidebar is not None:
            shell_sidebar.show()
        app_header = getattr(self.main_window, "app_header", None)
        if app_header is not None:
            app_header.setFixedHeight(70)
            breadcrumb = getattr(app_header, "breadcrumb", None)
            search_input = getattr(breadcrumb, "search_input", None)
            if search_input is not None:
                search_input.setVisible(breadcrumb.width() >= 700 and self.main_window.width() >= 1400)

    def _sync_shell_sidebar(self):
        if getattr(self, "_syncing_shell_sidebar", False):
            return
        self._syncing_shell_sidebar = True
        try:
            if not self.isVisible():
                self._restore_shell_sidebar()
                return
            if self.main_window is not None:
                self.main_window._settings_header_mode = False
            use_embedded_navigation = self.main_window is not None and self.main_window.width() >= 1366
            page_has_internal_navigation = self.content_area.currentIndex() == 21
            self.sidebar.setFixedWidth(260)
            self.sidebar.setVisible(use_embedded_navigation)
            self.settings_page_selector.setVisible(
                not use_embedded_navigation and not page_has_internal_navigation
            )
            if hasattr(self, "settings_navigation_row"):
                self.settings_navigation_row.setVisible(
                    not use_embedded_navigation and not page_has_internal_navigation
                )
            if use_embedded_navigation:
                self.sidebar.list_widget.scrollToTop()
            shell_sidebar = getattr(self.main_window, "app_sidebar", None)
            if shell_sidebar is not None:
                shell_sidebar.show()
            app_header = getattr(self.main_window, "app_header", None)
            if app_header is not None:
                app_header.setFixedHeight(70)
                breadcrumb = getattr(app_header, "breadcrumb", None)
                search_input = getattr(breadcrumb, "search_input", None)
                if search_input is not None:
                    search_input.setVisible(breadcrumb.width() >= 700 and self.main_window.width() >= 1400)
        finally:
            self._syncing_shell_sidebar = False

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_shell_sidebar()

    def hideEvent(self, event):
        self._restore_shell_sidebar()
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._sync_shell_sidebar)

    def eventFilter(self, watched, event):
        if watched is getattr(self, "_shell_menu", None) and event.type() in (QEvent.Type.Show, QEvent.Type.Hide, QEvent.Type.Resize):
            QTimer.singleShot(0, self._sync_shell_sidebar)
        return super().eventFilter(watched, event)

    def is_classic_appearance(self):
        return AppearanceModeManager.current(self.db) == AppearanceModeManager.CLASSIC

    def _content_area_qss(self):
        if self.is_classic_appearance():
            return theme_qss("""
            QWidget#SettingsPage {
                background-color: @window;
                color: @text;
            }
            QStackedWidget {
                background-color: @surface;
                border: none;
            }
            QStackedWidget#SettingsContentArea,
            QStackedWidget#SettingsContentArea > QWidget {
                background-color: @surface;
                color: @text;
            }
            QTabWidget::pane {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 0px;
            }
            QTabBar::tab {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-bottom: 1px solid @border;
                border-radius: 0px;
                padding: 6px 12px;
                margin-right: 2px;
                min-height: 22px;
                min-width: 84px;
                font-size: 11px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background-color: @surface;
                color: @text;
                border-bottom-color: @surface;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
                background: @surface;
                border: 1px solid @border;
                border-radius: 0px;
                padding: 4px 8px;
                color: @text;
                min-height: 22px;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
                border: 1px solid @accent;
            }
            QFrame[settingsCard="true"] {
                background: @surface;
                border: 1px solid @border;
                border-radius: 0px;
            }
            QGroupBox {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 0px;
                margin-top: 12px;
                padding-top: 18px;
                font-weight: bold;
                color: @text;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: @text;
                background-color: @surface;
            }
            """)
        return theme_qss(f"""
            background-color: {CONTENT_BG};
            QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
                background: @surface;
                border: 1px solid @border;
                border-radius: 4px;
                padding: 6px 10px;
                color: @text;
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
                border: 1px solid @accent;
            }}
            QFrame[settingsCard="true"] {{
                background: @surface;
                border: 1px solid {BORDER_COLOR};
                border-radius: 12px;
            }}
            QGroupBox {{
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 25px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: {SIDEBAR_TEXT};
            }}
        """)

    def init_ui(self):
        if self.is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Left Sidebar ---
        current_user = getattr(self.main_window, "current_user", {}) or {}
        self.sidebar = PremiumSettingsSidebar(
            self.change_page,
            db=self.db,
            current_user=current_user,
            parent=self,
        )
        self.sidebar.set_embedded(True, width=260)

        # --- Right Content ---
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("SettingsContentArea")
        if self.is_classic_appearance():
            self.content_area.setProperty("skipThemeTransform", False)
        self.content_area.setStyleSheet(self._content_area_qss())
        
        # Initialize Pages Dictionary (Lazy Loading)
        self.pages = {}
        
        # Pre-load only the default page (Company Settings - Index 4)
        
        max_index = max([i for i in self.sidebar.items_map if i is not None] + [4])
        for i in range(max_index + 1):
            self.pages[i] = None
        
        # Pre-load only the default page (Company Settings - Index 4)
        self.pages[4] = CompanySettingsWidget(self.db, self.main_window)

        # Add initial pages to stack, for None we add a temporary placeholder
        # Note: QStackedWidget needs widgets. We will manage this dynamically in change_page 
        # or just add empty QWidgets now.
        for i in range(max_index + 1):
            if self.pages[i]:
                self.content_area.addWidget(self.pages[i])
            else:
                w = QWidget() # Empty place holder
                self.content_area.addWidget(w)
                self.pages[i] = w # Temporarily store the empty widget
        
        content_column = QVBoxLayout()
        content_column.setContentsMargins(16, 12, 16, 12)
        content_column.setSpacing(10)
        self.settings_page_selector = QComboBox(self)
        self.settings_page_selector.setObjectName("SettingsPageSelector")
        self.settings_page_selector.setFixedHeight(32)
        self.settings_page_selector.setMaximumWidth(300)
        for item in self.sidebar.iter_items():
            self.settings_page_selector.addItem(item["title"], item["page_id"])
        self.settings_page_selector.activated.connect(
            lambda index: self.change_page(self.settings_page_selector.itemData(index))
        )
        self.settings_navigation_row = QWidget(self)
        settings_navigation = QHBoxLayout(self.settings_navigation_row)
        settings_navigation.setContentsMargins(0, 0, 0, 0)
        settings_navigation.addStretch(1)
        settings_navigation.addWidget(self.settings_page_selector)
        self.settings_navigation_layout = settings_navigation
        content_column.addWidget(self.settings_navigation_row, 0)
        content_column.addWidget(self.content_area, 1)
        main_layout.addWidget(self.sidebar, 0)
        main_layout.addLayout(content_column, 1)
        
        # Select default
        # Select default (Firma Ayarları - Index in list widget needs to be calculated)
        # We need to find which row corresponds to index 4
        # Our map has Nones for headers.
        # Structure: Header, 4 items, Header, 3 items...
        # Firma is in first group, index 1 (0 is header)
        self.sidebar.list_widget.setCurrentRow(1)
        # Ensure all controls are enabled and interactive
        self.enable_all_controls()
        self.apply_theme_styles()

    def change_page(self, row):
        diagnostics = getattr(self.main_window, "_menu_window_diagnostics", None)
        if diagnostics is not None:
            item = next(
                (entry for entry in self.sidebar.iter_items() if entry["page_id"] == row),
                None,
            )
            diagnostics.record_menu_click(
                "Settings menu",
                item["title"] if item else "Unknown settings page",
                row,
            )
        # Lazy Load Logic
        # Strategy: We store the CLASS in a mapping, and instantiate on first access.
        
        # Keep settings feature modules unloaded until their page is opened.
        page_map = {
            0: ("src.ui.pages.settings_widgets.bank_settings", "BankSettingsWidget"),
            1: ("src.ui.pages.settings_widgets.sms_settings", "SMSSettingsWidget"),
            2: ("src.ui.pages.settings_widgets.smtp_settings", "SMTPSettingsWidget"),
            3: ("src.ui.pages.settings_widgets.sms_settings", "SMSTemplatesWidget"),
            4: ("src.ui.pages.settings_widgets.company_settings", "CompanySettingsWidget"),
            5: ("src.ui.pages.settings_widgets.cargo_settings", "CargoSettingsWidget"),
            6: ("src.ui.pages.settings_widgets.background_settings", "BackgroundSettingsWidget"),
            7: ("src.ui.pages.settings_widgets.backup_settings", "BackupSettingsWidget"),
            8: None,
            9: ("src.ui.pages.settings_widgets.language_settings", "LanguageSettingsWidget"),
            10: ("src.ui.pages.settings_widgets.license_settings", "LicenseManagementWidget"),
            11: ("src.ui.pages.security_settings_widget", "SecuritySettingsWidget"),
            12: ("src.ui.pages.settings_widgets.stock_settings", "StockSettingsWidget"),
            13: ("src.ui.pages.settings_widgets.gemini_settings_widget", "GeminiSettingsWidget"),
            14: ("src.ui.pages.quick_notes_settings_widget", "QuickNotesSettingsWidget"),
            16: ("src.ui.pages.settings_widgets.telegram_settings", "TelegramSettingsWidget"),
            17: None,
            18: ("src.ui.pages.settings_widgets.remote_settings", "RemoteSettingsWidget"),
            19: ("src.ui.pages.settings_widgets.user_management", "UserManagementWidget"),
            20: ("src.ui.pages.settings_widgets.whatsapp_settings", "WhatsAppSettingsWidget"),
            21: ("src.ui.pages.settings_widgets.integration_hub", "IntegrationHubWidget"),
            22: ("src.ui.pages.settings_widgets.system_identity_settings", "SystemIdentitySettingsWidget"),
            23: ("src.ui.pages.settings_widgets.voice_training_widget", "VoiceTrainingWidget"),
            24: ("src.ui.pages.settings_widgets.management_center_settings", "ManagementCenterSettingsWidget"),
            25: ("src.ui.pages.settings_widgets.tax_exchange_settings", "TaxExchangeSettingsWidget"),
        }
        
        # If it's the empty placeholder (QWidget) or we haven't loaded it properly
        current_widget = self.content_area.widget(row)
        
        # We need to know if 'current_widget' is just the dummy we added.
        # Let's check if it has a specific attribute or just type check.
        # Simpler: Keep a set of 'loaded_indices'.
        if not hasattr(self, 'loaded_indices'):
            self.loaded_indices = {4}
            
        if row not in self.loaded_indices:
            # Load it now
            # Instantiate
            # Check specific overrides first
            if row == 17:
                from src.ui.pages.audit_log_page import AuditLogPage
                new_page = AuditLogPage(self.db)
            else:
                page_spec = page_map.get(row)
                if not page_spec:
                    new_page = PlaceholderWidget("Bilinmeyen Modül")
                else:
                    try:
                        module_path, class_name = page_spec
                        cls_or_func = getattr(
                            importlib.import_module(module_path), class_name
                        )
                        if row in [4, 6, 10, 24]: # These take main_window
                            new_page = cls_or_func(self.db, self.main_window)
                        else:
                            # Modified: ALL widgets now accept main_window
                            try:
                                new_page = cls_or_func(self.db, self.main_window)
                            except TypeError:
                                # Fallback if I missed updating one specific class init
                                new_page = cls_or_func(self.db)
                    except Exception as e:
                        logger.error(f"Error loading settings page {row}: {e}")
                        new_page = PlaceholderWidget(f"Hata: {e}")

            page_container = new_page
            if row in (7, 10, 11):
                page_container = QScrollArea()
                page_container.setWidgetResizable(True)
                page_container.setFrameShape(QFrame.Shape.NoFrame)
                page_container.setHorizontalScrollBarPolicy(
                    Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                )
                page_container.setWidget(new_page)

            # Replace the dummy widget in stack
            old_widget = self.content_area.widget(row)
            self.content_area.removeWidget(old_widget)
            self.content_area.insertWidget(row, page_container)
            
            self.pages[row] = page_container
            self.loaded_indices.add(row)
            if hasattr(new_page, "apply_theme_styles"):
                try:
                    new_page.apply_theme_styles()
                except Exception as e:
                    logger.debug(f"Settings child theme refresh skipped: {e}")
            if self.is_classic_appearance() and not bool(new_page.property("skipThemeTransform")):
                new_page.setProperty("skipThemeTransform", False)
                new_page.setStyleSheet(self._content_area_qss())
            
        self.content_area.setCurrentIndex(row)
        if row in self.sidebar.items_map:
            navigation_row = self.sidebar.items_map.index(row)
            navigation_item = self.sidebar.list_widget.item(navigation_row)
            if navigation_item is not None and not navigation_item.isHidden():
                self.sidebar._active_page_id = row
                previous = self.sidebar.list_widget.blockSignals(True)
                try:
                    self.sidebar.list_widget.setCurrentRow(navigation_row)
                finally:
                    self.sidebar.list_widget.blockSignals(previous)
        selector_index = self.settings_page_selector.findData(row)
        if selector_index >= 0 and self.settings_page_selector.currentIndex() != selector_index:
            self.settings_page_selector.blockSignals(True)
            self.settings_page_selector.setCurrentIndex(selector_index)
            self.settings_page_selector.blockSignals(False)
        selector_host = getattr(self, "_settings_selector_host", None)
        if selector_host is not None:
            selector_host.detach_settings_page_selector(self.settings_page_selector)
            self._settings_selector_host = None
        if self.settings_navigation_layout.indexOf(self.settings_page_selector) < 0:
            self.settings_navigation_layout.addWidget(self.settings_page_selector)
        self.sidebar.setFixedWidth(260)
        self.sidebar.setVisible(True)
        self.settings_navigation_row.setVisible(row != 21)
        self.settings_page_selector.setVisible(False)
        app_header = getattr(self.main_window, "app_header", None)
        breadcrumb = getattr(app_header, "breadcrumb", None)
        if breadcrumb is not None:
            list_row = self.sidebar.items_map.index(row) if row in self.sidebar.items_map else row
            item = self.sidebar.list_widget.item(list_row)
            page_title = item.text() if item is not None else "Ayarlar"
            if self.content_area.currentIndex() == 14:
                page_title = "H\u0131zl\u0131 Notlar & Makrolar"
            breadcrumb.update_path([
                ("AYEC Pro", None),
                ("Sistem Ayarlar\u0131", 130),
                (page_title, None),
            ])
        # Re-assert enabled state for newly loaded page
        self.enable_all_controls()
        self.apply_theme_styles()
        if self.isVisible():
            self._sync_shell_sidebar()

    def apply_theme_styles(self):
        if self.is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
        self.setStyleSheet(
            theme_qss("QWidget#SettingsPage { background-color: @window; color: @text; }")
            if self.is_classic_appearance()
            else theme_qss("QWidget#SettingsPage { background-color: @surface; color: @text; }")
        )
        if hasattr(self, "content_area"):
            if self.is_classic_appearance():
                self.content_area.setProperty("skipThemeTransform", False)
            self.content_area.setStyleSheet(self._content_area_qss())
        if hasattr(self, "sidebar") and hasattr(self.sidebar, "apply_theme_styles"):
            self.sidebar.apply_theme_styles()
        for page in getattr(self, "pages", {}).values():
            if page and hasattr(page, "apply_theme_styles"):
                try:
                    page.apply_theme_styles()
                except Exception as e:
                    logger.debug(f"Settings page theme refresh skipped: {e}")

    def enable_all_controls(self):
        """Enable all menu items and related buttons/inputs across settings."""
        # Enable sidebar items (skip headers)
        for i in range(self.sidebar.list_widget.count()):
            item = self.sidebar.list_widget.item(i)
            if item.flags() & Qt.ItemFlag.NoItemFlags:
                continue
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

# --- WIDGET IMPLEMENTATIONS ---

