# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QTabWidget, QWidget, QComboBox, QFrame, QButtonGroup
)
from PyQt6.QtCore import QTimer, QElapsedTimer, Qt
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

            title_str = f"Teknisyen Paneli & Atolye Is Istasyonu [ Arsiv - Salt Okunur ] - {tracking_no_str}" if read_only else f"Teknisyen Paneli & Atolye Is Istasyonu - {tracking_no_str}"
            super().__init__(
                title=title_str,
                parent=parent,
                width=1240,
                height=900,
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
        self.header.setFixedHeight(44)
        self.lbl_title.setToolTip(self.lbl_title.text())
        self.lbl_title.setText("Teknisyen \u00c7al\u0131\u015fma Alan\u0131")
        self.lbl_title.setWordWrap(True)
        self.lbl_title.setFixedWidth(140)
        self.lbl_title.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        self.content_layout.setSpacing(8)
        self.footer.setFixedHeight(48)
        self.footer_layout.setContentsMargins(12, 0, 12, 0)
        for button in self.footer.findChildren(QPushButton):
            button.setFixedHeight(30)
            background = "@accent" if "kaydet" in button.text().casefold() else "@finance_surface_alt"
            foreground = "@selection_text" if "kaydet" in button.text().casefold() else "@finance_text"
            button.setStyleSheet(theme_qss("QPushButton{background:" + background + ";color:" + foreground + ";border:1px solid @finance_outline;border-radius:4px;padding:0 8px;min-height:26px;font-size:11px;}QPushButton:disabled{color:@finance_text_muted;}"))

        summary = QFrame()
        summary.setObjectName("TechnicianPanelSummary")
        summary.setStyleSheet(theme_qss(f"""
            QFrame#TechnicianPanelSummary {{
                background: @finance_surface_alt;
                border: 1px solid {DesignTokens.BORDER};
                border-radius: 4px;
            }}
            QLabel {{ background: transparent; border: none; color: @text_muted; }}
            QLabel#PanelSummaryValue {{ color: @text; font-weight: bold; }}
        """))
        summary_grid = QGridLayout(summary)
        summary_grid.setContentsMargins(10, 4, 10, 4)
        summary_grid.setHorizontalSpacing(28)
        summary_values = (
            ("SERVIS KAYDI", str(self.tracking_no or "-")),
            ("PROFIL", str(self.technical_service_profile or "-")),
            ("MUSTERI", str(self.device_dict.get("customer_name") or "-")),
            ("DURUM", str(self.device_dict.get("status") or "-")),
        )
        self.panel_summary_values = {}
        for column, (caption, value) in enumerate(summary_values):
            block = QHBoxLayout()
            block.setSpacing(6)
            caption_label = QLabel(caption)
            caption_label.setFont(QFont(DesignTokens.FONT_NAME, 8, QFont.Weight.Bold))
            caption_label.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:9px;border:none;background:transparent;"))
            value_label = QLabel(value)
            value_label.setTextFormat(Qt.TextFormat.PlainText)
            value_label.setWordWrap(True)
            self.panel_summary_values[caption] = value_label
            value_label.setObjectName("PanelSummaryValue")
            value_label.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
            if caption == "SERVIS KAYDI":
                value_label.setProperty("referenceFont", "mono")
                value_label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold))
                QTimer.singleShot(0, lambda label=value_label: label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold)))
            value_font = DesignTokens.MONO_FONT_NAME if caption == "SERVIS KAYDI" else DesignTokens.FONT_NAME
            value_label.setToolTip(value)
            value_label.setStyleSheet(theme_qss(f"color:@finance_text;font-size:10px;font-family:\"{value_font}\";font-weight:700;border:none;background:transparent;"))
            if caption == "SERVIS KAYDI":
                value_label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold))
            block.addWidget(caption_label)
            block.addWidget(value_label)
            summary_grid.addLayout(block, 0, column)
        summary_grid.setColumnStretch(4, 1)
        self.header.layout().insertWidget(3, summary, 1)

        station_bar = QFrame()
        station_bar.setObjectName("TechnicianStationBar")
        station_bar.setStyleSheet(theme_qss(f"""
            QFrame#TechnicianStationBar {{
                background: @surface_alt;
                border: 1px solid {DesignTokens.BORDER};
                border-radius: 4px;
            }}
            QLabel {{ background: transparent; border: none; color: @text_muted; }}
            QLabel#StationValue {{ color: @text; font-weight: bold; }}
            QLabel#StationState {{ color: @success; font-weight: bold; }}
        """))
        station_layout = QHBoxLayout(station_bar)
        self.station_layout = station_layout
        station_layout.setContentsMargins(10, 4, 10, 4)
        station_layout.setSpacing(18)
        station_id = str(self.db.get_setting("technician_station_id", "") or "").strip()
        technician = str(self.device_dict.get("technician") or "").strip()
        station = " - ".join(value for value in (station_id, technician) if value) or "Atanmamis"
        self.station_values = {}
        for caption, value, object_name in (
            ("ISTASYON", station, "StationValue"),
            ("GUVENLIK", str(self.db.get_setting("technician_station_esd_status", "") or "Bildirilmemis"), "StationValue"),
            ("PANEL SURESI", "00:00:00", "StationValue"),
            ("DONANIM", str(self.db.get_setting("technician_station_equipment", "") or "Bagli degil"), "StationValue"),
        ):
            block = QHBoxLayout()
            block.setSpacing(6)
            label = QLabel(caption)
            label.setFont(QFont(DesignTokens.FONT_NAME, 8, QFont.Weight.Bold))
            value_label = QLabel(value)
            value_label.setTextFormat(Qt.TextFormat.PlainText)
            value_label.setWordWrap(True)
            self.station_values[caption] = value_label
            value_label.setObjectName(object_name)
            value_label.setFont(QFont(DesignTokens.FONT_NAME, 9, QFont.Weight.Bold))
            if caption == "PANEL SURESI":
                value_label.setProperty("referenceFont", "mono")
                value_label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold))
                value_label.setStyleSheet(theme_qss(f"font-family:\"{DesignTokens.MONO_FONT_NAME}\";"))
                QTimer.singleShot(0, lambda label=value_label: label.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9, QFont.Weight.Bold)))
            block.addWidget(label)
            block.addWidget(value_label)
            station_layout.addLayout(block)
        station_layout.addStretch()
        self.station_bar = station_bar
        station_bar.setParent(self)
        station_bar.hide()
        self.panel_elapsed = QElapsedTimer()
        self.panel_elapsed.start()
        self.panel_elapsed_timer = QTimer(self)
        self.panel_elapsed_timer.timeout.connect(self._refresh_panel_elapsed)
        self.panel_elapsed_timer.start(1000)
        self.station_values["PANEL SURESI"].setToolTip("Bu panelin acik kalma suresi; is emri calisma suresi degildir")

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
        self.tabs.tabBar().hide()
        self.reference_tab_group = QButtonGroup(self)
        self.reference_tab_group.setExclusive(True)
        self.reference_tab_buttons = []
        for index, caption in enumerate(("Genel Bak\u0131\u015f", "Test Uygulama", "\u0130\u015flem Ge\u00e7mi\u015fi")):
            button = QPushButton(caption)
            button.setCheckable(True)
            button.setFixedSize(90, 26)
            button.setStyleSheet(theme_qss("QPushButton{background:@finance_canvas;color:@finance_text_muted;border:1px solid @finance_outline;border-radius:4px;padding:0 4px;min-height:22px;font-size:10px;}QPushButton:checked{background:@accent;color:@selection_text;}"))
            button.clicked.connect(lambda checked=False, tab_index=index: self.tabs.setCurrentIndex(tab_index))
            self.reference_tab_group.addButton(button, index)
            self.reference_tab_buttons.append(button)
            self.header.layout().insertWidget(self.header.layout().count() - 2, button)
        self.reference_tab_buttons[0].setChecked(True)
        self.tabs.currentChanged.connect(lambda index: self.reference_tab_buttons[index].setChecked(True) if 0 <= index < len(self.reference_tab_buttons) else None)
        self.reference_station_button = QPushButton("Istasyon")
        self.reference_station_button.setFixedSize(64, 26)
        self.reference_station_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 4px;min-height:22px;font-size:10px;}"))
        self.reference_station_button.clicked.connect(self._show_reference_station)
        self.header.layout().insertWidget(self.header.layout().count() - 2, self.reference_station_button)

        # Load first tab with a slight delay to allow diallog to show
        QTimer.singleShot(0, lambda: self._ensure_lazy_tab_loaded(0))

        # Styling
        self.apply_theme_styles()
        self._apply_classic_panel_shell_styles()

    def _show_reference_station(self):
        dialog = ModernDialog("Istasyon Bilgileri", self, width=700, height=210)
        dialog.content_layout.addWidget(self.station_bar)
        self.station_bar.show()
        dialog.add_button("Kapat", "secondary", dialog.accept)
        try:
            dialog.exec()
        finally:
            self.station_bar.setParent(self)
            self.station_bar.hide()

    def _refresh_panel_elapsed(self):
        seconds = max(0, self.panel_elapsed.elapsed() // 1000)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.station_values["PANEL SURESI"].setText("{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds))

    def _apply_read_only_mode(self, root_widget):
        if not root_widget or not getattr(self, "read_only", False):
            return
        from PyQt6.QtWidgets import QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox, QCheckBox, QPushButton

        for input_w in root_widget.findChildren((QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QAbstractSpinBox, QCheckBox, AnimatedToggle)):
            if isinstance(input_w, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
                input_w.setReadOnly(True)
            else:
                input_w.setEnabled(False)

        for btn in root_widget.findChildren(QPushButton):
            btn_txt = btn.text().strip().lower()
            if btn.accessibleName().startswith("delete_") or any(k in btn_txt for k in ["kaydet", "ekle", "sil", "g\u00fcncelle", "\u00e7\u0131kar", "de\u011fi\u015ftir", "temizle", "kullan", "manuel", "d\u00fczenle", "duzenle"]):
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
        self._place_reference_test_panel(index)
        self._schedule_classic_panel_styles()

    def closeEvent(self, event):
        if hasattr(self, "panel_elapsed_timer"):
            self.panel_elapsed_timer.stop()
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
        title.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
        self.general_profile_badge = QLabel(self.get_technical_service_profile())
        self.general_profile_badge.setStyleSheet(f"color: {DesignTokens.ACCENT}; font-weight: bold;")
        info_lay.addWidget(title)
        info_lay.addWidget(self.general_profile_badge)

        self.cmb_technical_profile_main = QComboBox()
        self.cmb_technical_profile_main.addItems(TECHNICAL_SERVICE_PROFILE_ORDER)
        self.cmb_technical_profile_main.setCurrentText(self.get_technical_service_profile())
        self.cmb_technical_profile_main.setFixedWidth(200)
        self.cmb_technical_profile_main.setEnabled(not getattr(self, "read_only", False))
        self.cmb_technical_profile_main.currentTextChanged.connect(self._on_technical_service_profile_changed)

        layout.addLayout(info_lay, 1)
        layout.addWidget(self.cmb_technical_profile_main)

        if hasattr(self, "reference_hardware_layout"):
            self.reference_hardware_layout.addWidget(self.cmb_technical_profile_main, 1, 0, 1, 2)
            profile_card.setVisible(False)
        elif hasattr(self, "station_layout"):
            caption = QLabel("PROFIL")
            caption.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:9px;font-weight:700;"))
            self.station_layout.addWidget(caption)
            self.station_layout.addWidget(self.cmb_technical_profile_main)
            profile_card.setVisible(False)

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
