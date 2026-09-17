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
from src.ui.pages.quick_notes_settings_widget import QuickNotesSettingsWidget
from src.utils.design_system import DesignTokens
from src.utils.appearance_mode import AppearanceModeManager
from src.ui.widgets.modern_dialog import ModernDialog

# Modülerleştirilmiş widget'lar (alias vererek dahili sınıflarla çakışmayı önler)
from src.ui.pages.settings_widgets.company_settings import CompanySettingsWidget
from src.ui.pages.settings_widgets.sms_settings import SMSSettingsWidget as SMSSettingsWidgetMod, SMSTemplatesWidget as SMSTemplatesWidgetMod, TemplateEditDialog
from src.ui.pages.settings_widgets.background_settings import BackgroundSettingsWidget as BackgroundSettingsWidgetMod
from src.ui.pages.settings_widgets.bank_settings import BankSettingsWidget as BankSettingsWidgetMod
from src.ui.pages.settings_widgets.cargo_settings import CargoSettingsWidget as CargoSettingsWidgetMod
from src.ui.pages.settings_widgets.stock_settings import StockSettingsWidget as StockSettingsWidgetMod
from src.ui.pages.settings_widgets.language_settings import LanguageSettingsWidget as LanguageSettingsWidgetMod
from src.ui.pages.settings_widgets.license_settings import LicenseManagementWidget
from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget
from src.ui.pages.settings_widgets.remote_settings import RemoteSettingsWidget
from src.ui.pages.settings_widgets.smtp_settings import SMTPSettingsWidget as SMTPSettingsWidgetMod
from src.ui.pages.settings_widgets.backup_settings import BackupSettingsWidget
try:
    from src.ui.pages.settings_widgets.user_management import UserManagementWidget
except ImportError as exc:
    # Keep the Settings screen available when an optional security dependency
    # is missing; the User Management page will show a controlled placeholder.
    UserManagementWidget = None
    import logging
    logging.getLogger("AYECProLogger").warning("User Management unavailable: %s", exc)
from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget
from src.ui.pages.settings_widgets.integration_hub import IntegrationHubWidget
from src.ui.pages.settings_widgets.voice_training_widget import VoiceTrainingWidget
from src.ui.pages.settings_widgets.system_identity_settings import SystemIdentitySettingsWidget
from src.ui.pages.settings_widgets.management_center_settings import ManagementCenterSettingsWidget
from src.ui.pages.settings_widgets.tax_exchange_settings import TaxExchangeSettingsWidget
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
from src.ui.pages.settings_widgets.gemini_settings_widget import GeminiSettingsWidget

class SettingsPage(QWidget):
    """
    Yenilenmiş Ayarlar Sayfası
    Sol tarafta menü, sağ tarafta içerik.
    """
    def __init__(self, db, main_window=None):
        super().__init__()
        self.setObjectName("SettingsPage")
        self.db = db
        self.main_window = main_window
        self.init_ui()

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
        self.sidebar = PremiumSettingsSidebar(self.change_page, db=self.db, current_user=current_user)
        main_layout.addWidget(self.sidebar)

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
        
        main_layout.addWidget(self.content_area)
        
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
        # Lazy Load Logic
        # Strategy: We store the CLASS in a mapping, and instantiate on first access.
        
        # Import SecuritySettingsWidget here to verify availability
        try:
            from src.ui.pages.security_settings_widget import SecuritySettingsWidget
        except ImportError:
            # If still failing, provide a dummy to prevent crash
            SecuritySettingsWidget = None

        # Mapping of Index -> Class
        page_map = {
            0: BankSettingsWidgetMod,
            1: SMSSettingsWidgetMod,
            2: SMTPSettingsWidgetMod,
            3: SMSTemplatesWidgetMod,
            4: CompanySettingsWidget, # Already loaded
            5: CargoSettingsWidgetMod,
            6: BackgroundSettingsWidgetMod,
            7: BackupSettingsWidget,
            8: None, # AuthorizationGroupsWidget removed (redundant)
            9: LanguageSettingsWidgetMod,
            10: LicenseManagementWidget,
            11: SecuritySettingsWidget,
            12: StockSettingsWidgetMod,
            13: GeminiSettingsWidget,
            14: QuickNotesSettingsWidget,
            16: TelegramSettingsWidget,
            17: None, # Will load AuditLogPage
            18: RemoteSettingsWidget,
            19: UserManagementWidget,
            20: WhatsAppSettingsWidget,
            21: IntegrationHubWidget,
            22: SystemIdentitySettingsWidget,
            23: VoiceTrainingWidget,
            24: ManagementCenterSettingsWidget,
            25: TaxExchangeSettingsWidget,
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
                cls_or_func = page_map.get(row)
                if not cls_or_func:
                    new_page = PlaceholderWidget("Bilinmeyen Modül")
                else:
                    try:
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

            # Replace the dummy widget in stack
            old_widget = self.content_area.widget(row)
            self.content_area.removeWidget(old_widget)
            self.content_area.insertWidget(row, new_page)
            
            self.pages[row] = new_page
            self.loaded_indices.add(row)
            if hasattr(new_page, "apply_theme_styles"):
                try:
                    new_page.apply_theme_styles()
                except Exception as e:
                    logger.debug(f"Settings child theme refresh skipped: {e}")
            if self.is_classic_appearance():
                new_page.setProperty("skipThemeTransform", False)
                new_page.setStyleSheet(self._content_area_qss())
            
        self.content_area.setCurrentIndex(row)
        # Re-assert enabled state for newly loaded page
        self.enable_all_controls()
        self.apply_theme_styles()

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

