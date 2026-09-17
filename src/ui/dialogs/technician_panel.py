# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QWidget, QComboBox, QFrame
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont

# Internal Mixins & Components
from src.ui.dialogs.technician_panel_inventory_mixin import TechnicianPanelInventoryMixin
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.utils.technical_service_profiles import TECHNICAL_SERVICE_PROFILE_ORDER, DEFAULT_TECHNICAL_SERVICE_PROFILE
from src.utils.toast_notification import show_warning

# New Modular Mixins
from src.ui.dialogs._tp_styles import _TpStyles
from src.ui.dialogs._tp_helpers import _TpHelpers
from src.ui.dialogs._tp_automotive import _TpAutomotive
from src.ui.dialogs._tp_operations import _TpOperations
from src.ui.dialogs._tp_tabs import _TpTabs

class TechnicianPanel(TechnicianPanelInventoryMixin, _TpStyles, _TpHelpers, _TpAutomotive, _TpOperations, _TpTabs, ModernDialog):
    """
    Modular Technician Panel for managing service records.
    Inherits from multiple mixins to keep file size manageable and logic separated.
    """
    _session_toggle_cache = {}
    _profile_seed_cache = set()

    def __init__(self, db, tracking_no, parent=None, sector_manager=None, read_only=False):
        # Extract actual tracking number if a dictionary, sqlite3.Row, or list/tuple was passed
        tracking_no_str = None
        if isinstance(tracking_no, str):
            tracking_no_str = tracking_no
        elif hasattr(tracking_no, "keys") and callable(tracking_no.keys):
            try:
                keys = list(tracking_no.keys())
                if "tracking_no" in keys:
                    tracking_no_str = str(tracking_no["tracking_no"])
                elif "tracking_id" in keys:
                    tracking_no_str = str(tracking_no["tracking_id"])
            except Exception:
                pass

        if not tracking_no_str:
            try:
                if len(tracking_no) > 1:
                    tracking_no_str = str(tracking_no[1])
            except Exception:
                pass

        if not tracking_no_str:
            tracking_no_str = str(tracking_no)

        perf_key = f"TechnicianPanelInit_{tracking_no_str}"
        from src.utils.performance_monitor import perf_span
        with perf_span(perf_key):
            self.db = db
            self.sector_manager = sector_manager
            self.ai_service = None
            self.voice_thread = None
            self.read_only = read_only

            title_str = f"Teknisyen \u00c7al\u0131\u015fma Alan\u0131 [ Ar\u015fiv - Salt Okunur ] - {tracking_no_str}" if read_only else f"Teknisyen \u00c7al\u0131\u015fma Alan\u0131 - {tracking_no_str}"
            super().__init__(
                title=title_str,
                parent=parent,
                width=1380,
                height=920,
            )
            self.tracking_no = tracking_no_str

            from src.utils.audit_logger import get_audit_logger
            self.audit_logger = get_audit_logger(self.db)


            # Fetch device data
            device_data = self.db.get_device_by_tracking_no(tracking_no_str)
            if not device_data:
                show_warning(self, f"{tracking_no_str} numaral\u0131 cihaz bulunamad\u0131.")
                QTimer.singleShot(0, self.reject)
                return

            self.device_dict = self._device_data_to_dict(device_data)
            self.technical_service_profile = self.device_dict.get("device_type") or DEFAULT_TECHNICAL_SERVICE_PROFILE
            self._ensure_technical_service_profile_seed()

            # Additional automotive data
            self.automotive_service_form = {}
            if self._is_automotive():
                try:
                    row = self.db.cursor.execute(
                        "SELECT * FROM automotive_service_forms WHERE tracking_no=?", (self.tracking_no,)
                    ).fetchone()
                    if row:
                        from src.utils.db_utils import sqlite_row_to_dict
                        self.automotive_service_form = sqlite_row_to_dict(row, self.db.cursor.description)
                except Exception as e:
                    logger.warning(f"Failed to load automotive service form: {e}")

            self._init_ui()

    def _init_ui(self):
        self.set_footer_visible(True)
        self.add_footer_actions()

        # Main Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("TechnicianPanelTabs")
        self.content_layout.addWidget(self.tabs)

        # Create empty tabs for lazy loading
        self.general_loaded = False
        self.test_loaded = False
        self.log_loaded = False

        self.tabs.addTab(QWidget(), " Genel Bak\u0131\u015f ")
        self.tabs.addTab(QWidget(), " Test Uygulama ")
        self.tabs.addTab(QWidget(), " \u0130\u015flem Ge\u00e7mi\u015fi ")

        self.tabs.currentChanged.connect(self._ensure_lazy_tab_loaded)

        # Load first tab with a slight delay to allow diallog to show
        QTimer.singleShot(0, lambda: self._ensure_lazy_tab_loaded(0))

        # Styling
        self.apply_theme_styles()
        self._apply_classic_panel_shell_styles()

    def _apply_read_only_mode(self, root_widget):
        if not root_widget or not getattr(self, "read_only", False):
            return
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox, QPushButton

        for input_w in root_widget.findChildren((QLineEdit, QTextEdit, QComboBox, QSpinBox, QCheckBox, AnimatedToggle)):
            if isinstance(input_w, (QLineEdit, QTextEdit)):
                input_w.setReadOnly(True)
            else:
                input_w.setEnabled(False)

        for btn in root_widget.findChildren(QPushButton):
            btn_txt = btn.text().strip().lower()
            if any(k in btn_txt for k in ["kaydet", "ekle", "sil", "g\u00fcncelle", "\u00e7\u0131kar", "de\u011fi\u015ftir", "temizle"]):
                btn.setEnabled(False)

    def _ensure_lazy_tab_loaded(self, index):
        self.tabs.blockSignals(True)
        try:
            if index == 0 and not self.general_loaded:
                self.create_general_tab()
                self.tabs.removeTab(0)
                self.tabs.insertTab(0, self.general_widget, " Genel Bak\u0131\u015f ")
                self.general_loaded = True
                if self.read_only:
                    self._apply_read_only_mode(self.general_widget)
            elif index == 1 and not self.test_loaded:
                self.create_test_tab()
                self.tabs.removeTab(1)
                self.tabs.insertTab(1, self.test_widget, " Test Uygulama ")
                self.test_loaded = True
                if self.read_only:
                    self._apply_read_only_mode(self.test_widget)
            elif index == 2 and not self.log_loaded:
                self.create_logs_tab()
                self.tabs.removeTab(2)
                self.tabs.insertTab(2, self.log_widget, " \u0130\u015flem Ge\u00e7mi\u015fi ")
                self.log_loaded = True
                if self.read_only:
                    self._apply_read_only_mode(self.log_widget)
        finally:
            self.tabs.blockSignals(False)

        self.tabs.setCurrentIndex(index)
        self._schedule_classic_panel_styles()

    def closeEvent(self, event):
        if not getattr(self, "read_only", False):
            self._perform_silent_save()
        if self.voice_thread and self.voice_thread.isRunning():
            self.voice_thread.stop()
        super().closeEvent(event)

    def add_footer_actions(self):
        if getattr(self, "read_only", False):
            self.add_cancel_button("Kapat")
            self.add_button("Etiket Yazd\u0131r", "secondary", self.print_label)
        else:
            self.add_cancel_button("Kapat")
            self.add_button("Etiket Yazd\u0131r", "secondary", self.print_label)
            self.add_button("Kaydet ve Kapat", "primary", self.save_update)

class TechnicalServiceTechnicianPanel(TechnicianPanel):
    def _is_automotive(self):
        return False

    def create_general_tab(self):
        super().create_general_tab()
        self._insert_technical_service_profile_card()
        self._apply_technical_service_profile(self.get_technical_service_profile(), persist=False)
        self._upgrade_technical_service_general_tab()

    def _upgrade_technical_service_general_tab(self):
        if not hasattr(self, "general_widget"):
            return

        self._relax_technical_service_group_heights()
        self._hide_embedded_save_buttons()

    def _hide_embedded_save_buttons(self):
        for button in self.general_widget.findChildren(QPushButton):
            if button.text().strip() == "Kaydet":
                button.hide()
                button.setEnabled(False)

    def _relax_technical_service_group_heights(self):
        flexible_groups = (
            "accessories_group",
            "fault_group",
            "process_group",
            "pattern_group",
            "photo_group",
            "private_group",
            "status_group",
            "finance_group",
            "parts_group",
        )
        for page_name in ("wizard_page1", "wizard_page2", "wizard_page3"):
            page = getattr(self, page_name, None)
            if page is None:
                continue
            for group_name in flexible_groups:
                group = getattr(page, group_name, None)
                if group is not None:
                    group.setMaximumHeight(16777215)

    def _insert_technical_service_profile_card(self):
        """Adds a card at the top of the general tab to switch technical service profiles."""
        if not hasattr(self, "general_content_layout"):
            return

        profile_card = QFrame()
        profile_card.setObjectName("TechnicalProfileCard")
        profile_card.setStyleSheet(theme_qss("""
            #TechnicalProfileCard { background: @surface_alt; border: 1px solid @border; border-radius: 12px; }
        """))
        layout = QHBoxLayout(profile_card)
        layout.setContentsMargins(15, 10, 15, 10)

        info_lay = QVBoxLayout()
        title = QLabel("Teknik Servis Profili")
        title.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        self.general_profile_badge = QLabel(self.get_technical_service_profile())
        self.general_profile_badge.setStyleSheet(f"color: {DesignTokens.ACCENT}; font-weight: bold;")
        info_lay.addWidget(title)
        info_lay.addWidget(self.general_profile_badge)

        self.cmb_technical_profile_main = QComboBox()
        self.cmb_technical_profile_main.addItems(TECHNICAL_SERVICE_PROFILE_ORDER)
        self.cmb_technical_profile_main.setCurrentText(self.get_technical_service_profile())
        self.cmb_technical_profile_main.setFixedWidth(200)
        self.cmb_technical_profile_main.currentTextChanged.connect(self._on_technical_service_profile_changed)

        layout.addLayout(info_lay, 1)
        layout.addWidget(self.cmb_technical_profile_main)

        # Insert at top (index 0)
        self.general_content_layout.insertWidget(0, profile_card)

class AutomotiveTechnicianPanel(TechnicianPanel):
    def _is_automotive(self):
        return True

    def create_general_tab(self):
        super().create_general_tab()

    def add_footer_actions(self):
        if getattr(self, "read_only", False):
            self.add_cancel_button("Kapat")
            self.add_button("Servis Formu PDF", "secondary", self._create_service_receipt_pdf)
        else:
            self.add_cancel_button("Kapat")
            self.add_button("QR / Ara\u00e7 Ge\u00e7mi\u015fi", "secondary", self._open_vehicle_history_qr)
            self.add_button("Servis Formu PDF", "secondary", self._create_service_receipt_pdf)
            self.add_button("Tahsilat / Fatura", "success", self._open_payment_and_invoice_flow)
            self.add_button("Kaydet", "primary", self.save_update)


LegacyTechnicianPanel = TechnicianPanel
