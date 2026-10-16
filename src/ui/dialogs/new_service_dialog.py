
# -*- coding: utf-8 -*-

import random
import os
import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QCompleter, QCheckBox,
    QApplication, QWidget, QFrame, QGridLayout, QTableWidget, QDialog, QLineEdit, QButtonGroup, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDateEdit
from PyQt6.QtGui import QFont

from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import ToastManager
from src.utils.design_system import DesignTokens
from src.ui.widgets.pattern_lock import PatternLockWidget
from src.ui.widgets.animated_toggle import AnimatedToggle
from src.ui.dialogs.automotive_checklist_dialog import AutomotiveChecklistDialog
from src.ui.dialogs.automotive_damage_dialog import AutomotiveDamageDialog
from src.ui.dialogs.new_service_dialog_media_mixin import NewServiceDialogMediaMixin
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.logger import logger
from src.ui.dialogs.quick_notes_editor import PROFILE_PRESETS
from src.utils.system_config import SystemConfig
from src.utils.currency_helper import CurrencyHelper
from decimal import Decimal

from ._new_service_dialog_widgets_mixin import NewServiceDialogWidgetsMixin, ServiceVoiceButton
from ._new_service_dialog_sector_mixin import NewServiceDialogSectorMixin


TECH_SERVICE_AREAS = [
    "Bilgisayar",
    "Ak\u0131ll\u0131 Ev",
    "G\u00fcvenlik Sistemleri",
]

TECH_DEVICE_TYPES = {
    "Bilgisayar": [
        "Laptop", "Masa\u00fcst\u00fc PC", "All In One", "Mini PC",
        "Monit\u00f6r", "Sunucu", "Yaz\u0131c\u0131",
    ],
    "Ak\u0131ll\u0131 Ev": [
        "Ak\u0131ll\u0131 Ev Merkezi", "Ak\u0131ll\u0131 Anahtar",
        "Ak\u0131ll\u0131 Priz", "Sens\u00f6r", "R\u00f6le Mod\u00fcl\u00fc",
        "Ak\u0131ll\u0131 Perde Motoru", "Termostat", "Gateway",
    ],
    "Cep Telefonu": [
        "Cep Telefonu", "Tablet", "Ak\u0131ll\u0131 Saat",
    ],
    "G\u00fcvenlik Sistemleri": [
        "IP Kamera", "Analog Kamera", "NVR", "DVR", "Alarm Paneli",
        "Sens\u00f6r", "Interkom", "Kartl\u0131 Ge\u00e7i\u015f",
    ],
}

OTHER_DEVICE_TYPE = "Di\u011fer"

DEVICE_PROFILE_AREAS = {
    "bilgisayar": "Bilgisayar",
    "cep_telefonu": "Cep Telefonu",
    "akilli_ev": "Ak\u0131ll\u0131 Ev",
}



class NewServiceDialog(
    NewServiceDialogMediaMixin,
    NewServiceDialogWidgetsMixin,
    NewServiceDialogSectorMixin,
    ModernDialog,
):
    SECTOR_ID = None

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def __init__(self, db, parent=None, customer_name=None, device_data=None, sector_manager=None):
        self.db = db
        self.sector_manager = sector_manager
        self.sector_service_fields = self.sector_manager.get_service_fields() if self.sector_manager else []
        self.service_form_descriptors = self.sector_manager.get_form_descriptors("service") if self.sector_manager else []
        self.sector_service_widgets = {}
        self.descriptor_service_widgets = {}
        if self.SECTOR_ID:
            self.is_automotive = self.SECTOR_ID == "otomotiv"
        elif self.sector_manager and self.sector_manager.get_current_plugin():
            self.is_automotive = self.sector_manager.get_current_plugin().sector_id == "otomotiv"
        else:
            self.is_automotive = SystemConfig.get_current_sector(self.db) == "otomotiv"
        self.device_data = device_data 
        self._service_area = "Bilgisayar"
        if not self.is_automotive:
            self._service_area = self._available_service_areas()[0]
        self.photo_path = ""
        self.photo_path_list = [] # Legacy compatibility
        self.photo_paths = []
        self.photo_labels = []
        self.photo_snapshot_paths = []
        self.photo_snapshot_labels = []
        self.automotive_checklist_data = {"items": []}
        self.automotive_damage_data = {"items": [], "general_note": ""}
        
        mode_title = "Servis Kayd\u0131 D\u00fczenle" if device_data else "Yeni Servis Kayd\u0131 Olu\u015ftur"

        screen = QApplication.primaryScreen().geometry()
        width = min(1440, max(760, screen.width() - 16))
        height = min(1188, max(600, screen.height() - 48))
        super().__init__(mode_title, parent, width=width, height=height)
        self.setFont(QFont("Segoe UI", 9))
        self.setup_content()
        self.finished.connect(lambda _result: setattr(self, "_fault_voice_discarded", True))
        self._initial_customer_name = customer_name
        QTimer.singleShot(0, self._deferred_bootstrap_step_customers)

    def _deferred_bootstrap_step_customers(self):
        self.load_customers()
        QTimer.singleShot(0, self._deferred_bootstrap_step_personnel)

    def _deferred_bootstrap_step_personnel(self):
        self.load_personnel()
        QTimer.singleShot(0, self._deferred_bootstrap_finalize)

    def _deferred_bootstrap_finalize(self):
        if self.device_data:
            self.load_device_from_data()
        elif self._initial_customer_name:
            self.cmb_customer.setCurrentText(self._initial_customer_name)
        for name in ("cmb_customer", "cmb_device", "cmb_brand", "cmb_model", "cmb_urgency", "cmb_personnel"):
            widget = getattr(self, name, None)
            if isinstance(widget, QComboBox):
                widget.setFixedHeight(32)
        if not self.is_automotive:
            self._capture_reference_form_defaults()
            self.btn_reset_form.setEnabled(True)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

    def setup_content(self):
        # Rebuild-safe
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        screen = QApplication.primaryScreen().geometry()
        new_w = min(1440, max(760, screen.width() - 16))
        new_h = min(1188, max(600, screen.height() - 48))
        self.set_dialog_size(new_w, new_h)
        self.setMinimumSize(min(1080, new_w), min(720, new_h))

        self.set_footer_visible(True, 78)
        if not self.is_automotive:
            self.header.setFixedHeight(56)
            self._build_reference_service_header()
        self.clear_footer()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self._apply_dialog_contrast_guard()

        self.set_wheel_scroll_enabled(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


        # Main service workflow and 2-column form
        main_widget = QWidget()
        main_widget.setStyleSheet(theme_qss("background: @surface; border: none;"))
        root_layout = QVBoxLayout(main_widget)
        root_layout.setContentsMargins(12, 12, 12, 14)
        root_layout.setSpacing(12)

        if self.is_automotive:
            intro_title = "Ara\u00e7 Servis Kayd\u0131"
            intro_text = (
                "M\u00fc\u015fteri, ara\u00e7 kabul, ar\u0131za ve teslim bilgilerini "
                "tek i\u015f ak\u0131\u015f\u0131nda tamamlay\u0131n."
            )
            workflow_steps = [
                "M\u00fc\u015fteri",
                "Ara\u00e7",
                "Kabul ve Ar\u0131za",
                "Kay\u0131t",
            ]
        else:
            intro_title = "Teknik Servis Kayd\u0131"
            intro_text = (
                "M\u00fc\u015fteri, cihaz, ar\u0131za ve teslim bilgilerini "
                "tek i\u015f ak\u0131\u015f\u0131nda tamamlay\u0131n."
            )
            workflow_steps = [
                "M\u00fc\u015fteri",
                "Cihaz",
                "Ar\u0131za ve Kabul",
                "Kay\u0131t",
            ]

        if self.is_automotive:
            root_layout.addWidget(self.create_form_intro(intro_title, intro_text))
            root_layout.addWidget(self.create_workflow_strip(workflow_steps, active_index=0))

        columns_widget = QWidget()
        columns_widget.setStyleSheet("background: transparent; border: none;")
        main_lay = QHBoxLayout(columns_widget)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(16)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # 1. Customer
        left_col.addWidget(self._sec("M\u00dc\u015eTER\u0130 B\u0130LG\u0130LER\u0130"))
        left_col.addSpacing(6 if not self.is_automotive else 4)
        cust_row = QHBoxLayout()
        cust_row.setSpacing(8)
        self.cmb_customer = ModernComboBox()
        self.cmb_customer.setMinimumHeight(32)
        self._compact_reference_combo(self.cmb_customer)
        self.cmb_customer.setEditable(True)
        self.cmb_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_customer.setFixedHeight(32)
        customer_placeholder = "Ad Soyad veya Firma \u00dcnvan\u0131 giriniz..."
        self.cmb_customer.setPlaceholderText(customer_placeholder)
        if self.cmb_customer.lineEdit() is not None:
            self.cmb_customer.lineEdit().setPlaceholderText(customer_placeholder)
            self.cmb_customer.lineEdit().addAction(
                self._reference_customer_field_icon(),
                QLineEdit.ActionPosition.LeadingPosition,
            )
        btn_add_cust = QPushButton("+ Yeni")
        btn_add_cust.setFixedSize(76, 36)
        btn_add_cust.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_cust.setStyleSheet(theme_qss(
            "QPushButton { background-color: @finance_primary; color: @finance_primary_text; "
            "border: 1px solid @finance_outline; border-radius: 4px; font-weight: bold; }"
        ))
        btn_add_cust.clicked.connect(self.quick_add_customer)
        if self.is_automotive:
            cust_row.addWidget(self.cmb_customer, 1)
        else:
            customer_name_field = self.create_field_box(
                "M\u00fc\u015fteri Ad\u0131 / \u00dcnvan\u0131 *", self.cmb_customer
            )
            customer_name_field.setSpacing(6)
            cust_row.addLayout(customer_name_field, 1)
        left_col.addLayout(cust_row)
        if not self.is_automotive:
            customer_fields = QGridLayout()
            customer_fields.setHorizontalSpacing(8)
            customer_fields.setVerticalSpacing(10)
            self.inp_customer_identity = QLineEdit()
            self.inp_customer_phone = QLineEdit()
            for column, (label, editor) in enumerate((
                ("Kimlik / Vergi No", self.inp_customer_identity),
                ("\u0130leti\u015fim Telefonu", self.inp_customer_phone),
            )):
                editor.setReadOnly(False)
                editor.setPlaceholderText("TCKN veya Vergi No" if column == 0 else "0 (5XX) XXX XX XX")
                editor.setToolTip("Yeni musteri icin doldurun; kayitli musteri secilince bilgiler otomatik gelir.")
                editor.setFixedHeight(32)
                editor.setFont(QFont(DesignTokens.MONO_FONT_NAME, 10))
                editor.setStyleSheet(theme_qss(
                    "QLineEdit { background: @finance_surface_lowest; color: @finance_text; "
                    "border: 1px solid @finance_outline; border-radius: 4px; "
                    "padding: 3px 8px; min-height: 22px; font-size: 12px; "
                    "selection-background-color: @selection_bg; selection-color: @selection_text; }"))
                field_box = self.create_field_box(label, editor)
                field_box.setSpacing(5)
                customer_fields.addLayout(field_box, 0, column)
            left_col.addLayout(customer_fields)
            left_col.addSpacing(1)
            handover_fields = QGridLayout()
            handover_fields.setHorizontalSpacing(8)
            handover_fields.setVerticalSpacing(10)
            self.inp_delivered_by = QLineEdit()
            self.inp_delivered_phone = QLineEdit()
            for column, (label, editor, placeholder) in enumerate((
                ("Teslim Eden Ki\u015fi", self.inp_delivered_by, "Cihaz\u0131 teslim eden ki\u015fi"),
                ("Teslim Eden Tel", self.inp_delivered_phone, "Teslim eden ileti\u015fim no"),
            )):
                editor.setPlaceholderText(placeholder)
                editor.setFixedHeight(32)
                if column == 1:
                    editor.setFont(QFont(DesignTokens.MONO_FONT_NAME, 10))
                editor.setStyleSheet(theme_qss(
                    "QLineEdit { background: @finance_surface_lowest; color: @finance_text; "
                    "border: 1px solid @finance_outline; border-radius: 4px; "
                    "padding: 4px 8px; min-height: 18px; font-size: 11px; "
                    "selection-background-color: @selection_bg; selection-color: @selection_text; }"))
                field_box = self.create_field_box(label, editor)
                field_box.setSpacing(6)
                handover_fields.addLayout(field_box, 0, column)
            left_col.addLayout(handover_fields)
            self.cmb_customer.currentIndexChanged.connect(self._refresh_reference_customer_fields)
        left_col.addSpacing(12)
        self.btn_add_customer = btn_add_cust
        if not self.is_automotive:
            customer_card = self._wrap_reference_section(left_col, 0, "serviceCustomerCard")
            btn_add_cust.setParent(customer_card)
            btn_add_cust.hide()
            heading = customer_card.layout().itemAt(0).widget()
            if heading is not None and heading.layout() is not None:
                btn_select_customer = QPushButton("\u2315  Kay\u0131tl\u0131 M\u00fc\u015fteri Se\u00e7")
                btn_select_customer.setFixedSize(142, 26)
                btn_select_customer.setText("Kay\u0131tl\u0131 M\u00fc\u015fteri Se\u00e7")
                btn_select_customer.setIcon(self._reference_search_icon())
                btn_select_customer.setIconSize(QSize(12, 12))
                btn_select_customer.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_select_customer.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @finance_primary; "
                    "border: 1px solid @finance_outline; border-radius: 5px; padding: 0px 1px; "
                    "font-size: 9px; font-weight: 600; }"
                    "QPushButton:hover { border-color: @finance_primary; }"
                ))
                btn_select_customer.clicked.connect(self.cmb_customer.showPopup)
                heading.layout().addWidget(btn_select_customer)
                self.btn_select_customer = btn_select_customer
            left_col.setSpacing(14)

        # 2. Device
        left_col.addWidget(self._sec("C\u0130HAZ B\u0130LG\u0130LER\u0130"))
        left_col.addSpacing(4)
        dev_grid = QGridLayout()
        dev_grid.setHorizontalSpacing(8)
        dev_grid.setVerticalSpacing(20)
        dev_grid.setColumnStretch(0, 1)
        dev_grid.setColumnStretch(1, 1)
        dev_grid.setVerticalSpacing(14)
        device_items = []
        try:
            cur = self.db.cursor
            cur.execute(
                """
                SELECT name AS device_type
                FROM product_groups
                WHERE TRIM(COALESCE(name, '')) <> ''
                  AND COALESCE(is_active, 1)=1
                UNION
                SELECT DISTINCT device_type
                FROM device_brands
                WHERE TRIM(COALESCE(device_type, '')) <> ''
                  AND COALESCE(is_active, 1)=1
                ORDER BY device_type
                """
            )
            rows = cur.fetchall() or []
            device_items = [str(r[0]) for r in rows if r[0]]
        except Exception as e:
            logger.warning(f"Device type preload failed: {e}")
        if not device_items:
            device_items = ["Laptop", "Masaüstü", "All In One", "Monitör", "Mini PC"]
        if not self.is_automotive:
            device_items = self._device_types_for_service_area(self._service_area)
            if OTHER_DEVICE_TYPE not in device_items:
                device_items.append(OTHER_DEVICE_TYPE)
        self.cmb_device = ModernComboBox(items=device_items)
        self.cmb_device.setMinimumHeight(40)
        dev_grid.addLayout(self.create_field_box("Cihaz Türü", self.cmb_device), 0, 0)
        self.cmb_brand = ModernComboBox()
        self.cmb_brand.setEditable(True)
        self.cmb_brand.setMinimumHeight(40)
        self._load_brands_for_device_type(self.cmb_device.currentText(), preserve_current=False)
        self.cmb_device.currentTextChanged.connect(self._on_device_type_changed)
        dev_grid.addLayout(self.create_field_box("Marka", self.cmb_brand), 0, 1)
        self.inp_model = ValidatedLineEdit("Örn: Nitro 5 / ThinkPad E14 / RTX Sistem")
        self.cmb_model = ModernComboBox()
        self.cmb_model.setEditable(True)
        self.cmb_model.setMinimumHeight(40)
        self.cmb_model.setPlaceholderText("\u00d6rn: Aspire 7 A715-42G")
        if self.cmb_model.lineEdit():
            self.cmb_model.lineEdit().setPlaceholderText("\u00d6rn: Aspire 7 A715-42G")
        if not self.is_automotive:
            device_combo_style = theme_qss(
                "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 7px; padding: 0 10px; } "
                "QComboBox QAbstractItemView { background: @surface_alt; color: @text; "
                "selection-background-color: @accent; selection-color: @selection_text; }"
            )
            for device_combo in (self.cmb_device, self.cmb_brand, self.cmb_model):
                device_combo.setStyleSheet(device_combo.styleSheet() + device_combo_style)
        self.cmb_brand.currentTextChanged.connect(self._on_brand_changed)
        self._load_models_for_device_brand(
            self.cmb_device.currentText(), self.cmb_brand.currentText(), preserve_current=False
        )
        dev_grid.addLayout(self.create_field_box("Model Ad\u0131 / Kodu", self.cmb_model), 1, 0)
        self.inp_serial = ValidatedLineEdit("Seri Numaras\u0131 veya IMEI girin")
        self.inp_serial.setMinimumHeight(40)
        if not self.is_automotive:
            self.inp_serial.setFont(QFont(DesignTokens.MONO_FONT_NAME, 10))
            self.inp_serial.setStyleSheet(
                theme_qss("QLineEdit { background: @finance_surface_lowest; color: @finance_text; border: 1px solid @finance_outline; "
                "border-radius: 4px; padding: 3px 8px; font-size: 12px; "
                "selection-background-color: @selection_bg; selection-color: @selection_text; }")
            )
        dev_grid.addLayout(self.create_field_box("Seri No / IMEI", self.inp_serial), 1, 1)
        self.inp_other_device = ValidatedLineEdit("Cihaz t\u00fcr\u00fcn\u00fc yaz\u0131n")
        self.inp_other_device.setMinimumHeight(36)
        self.other_device_wrap = QFrame()
        self.other_device_wrap.setLayout(
            self.create_field_box("Di\u011fer Cihaz T\u00fcr\u00fc", self.inp_other_device)
        )
        self.other_device_wrap.setVisible(False)
        dev_grid.addWidget(self.other_device_wrap, 2, 0, 1, 2)
        self.inp_vehicle_plate = ValidatedLineEdit("34ABC123")
        self.inp_vehicle_plate.setMinimumHeight(36)
        self.inp_vehicle_vin = ValidatedLineEdit("VIN / Şasi No")
        self.inp_vehicle_vin.setMinimumHeight(36)
        self.vehicle_plate_wrap = QFrame()
        self.vehicle_plate_wrap.setLayout(self.create_field_box("Plaka", self.inp_vehicle_plate))
        self.vehicle_vin_wrap = QFrame()
        self.vehicle_vin_wrap.setLayout(self.create_field_box("VIN / Şasi No", self.inp_vehicle_vin))
        dev_grid.addWidget(self.vehicle_plate_wrap, 3, 0)
        dev_grid.addWidget(self.vehicle_vin_wrap, 3, 1)
        self.inp_vehicle_plate.setEnabled(self.is_automotive)
        self.inp_vehicle_vin.setEnabled(self.is_automotive)
        self.vehicle_plate_wrap.setVisible(self.is_automotive)
        self.vehicle_vin_wrap.setVisible(self.is_automotive)
        left_col.addLayout(dev_grid)
        left_col.addSpacing(12)
        if not self.is_automotive:
            self.reference_device_card = self._wrap_reference_section(
                left_col, 1, "serviceDeviceCard"
            )

        # Keep the compact customer and device fields on the left. The service
        # workflow continues in the right column so both sides use the space.
        primary_col = left_col
        primary_col.addStretch(1)
        primary_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_col = QVBoxLayout()
        right_col.setSpacing(0)
        left_col = right_col

        # 3. Service details
        left_col.addWidget(self._sec("SERV\u0130S DETAYLARI" if self.is_automotive else "ARIZA & SERV\u0130S DETAYLARI"))
        left_col.addSpacing(4)
        servis_grid = QGridLayout()
        servis_grid.setSpacing(8)
        self.inp_password = ValidatedLineEdit("Cihaz / Windows A\u00e7\u0131l\u0131\u015f \u015eifresi")
        self.inp_password.setPlaceholderText("\u00d6rn: 1234, aslan2024")
        self.inp_password.setMinimumHeight(36)
        if not self.is_automotive:
            self.inp_password.setStyleSheet(
                theme_qss("QLineEdit { background: @finance_surface_lowest; color: @finance_text; border: 1px solid @finance_outline; "
                "border-radius: 4px; padding: 4px 8px; font-size: 14px; "
                "selection-background-color: @selection_bg; selection-color: @selection_text; }")
            )
        servis_grid.addLayout(
            self.create_field_box("Cihaz / Windows A\u00e7\u0131l\u0131\u015f \u015eifresi", self.inp_password),
            0,
            0,
        )
        self.cmb_urgency = ModernComboBox(items=["Düşük", "Normal", "Yüksek", "🔥 ACİL"])
        self.cmb_urgency.setCurrentText("Normal")
        self.cmb_urgency.setMinimumHeight(32)
        if not self.is_automotive:
            self.cmb_urgency.setStyleSheet(theme_qss(
                "QComboBox { background: @surface_alt; color: @text; border: 1px solid @border; "
                "border-radius: 7px; padding: 0 10px; }"
            ))
        servis_grid.addLayout(self.create_field_box("\u00d6ncelik Derecesi", self.cmb_urgency), 0, 1)
        self.cmb_personnel = ModernComboBox()
        self.cmb_personnel.setMinimumHeight(36)
        servis_grid.addLayout(self.create_field_box("Teknisyen", self.cmb_personnel), 1, 0)
        self.inp_est_price = ValidatedLineEdit("")
        self.inp_est_price.setPlaceholderText("")
        self.inp_est_price.setMinimumHeight(32)
        self.inp_est_price.setStyleSheet(theme_qss(
            "QLineEdit { font-size: 12px; font-weight: bold; color: @finance_secondary; "
            "background: @finance_surface_alt; border: 1px solid @finance_outline; "
            "border-radius: 4px; padding: 5px 8px; }"
        ))
        if self.is_automotive:
            servis_grid.addLayout(self.create_field_box("Tahmini Tutar", self.inp_est_price), 1, 1)
        else:
            self.inp_est_price.setFont(QFont(DesignTokens.MONO_FONT_NAME, 10))
            self.inp_est_price.setStyleSheet(
                theme_qss("QLineEdit { font-size: 12px; font-weight: bold; color: @finance_text; "
                "background: @finance_surface_lowest; border: 1px solid @finance_outline; border-radius: 4px; "
                "padding: 5px 8px; selection-background-color: @selection_bg; "
                "selection-color: @selection_text; }")
            )
            self._estimate_base_currency = CurrencyHelper.get_code(self.db)
            self._estimate_currency = self._estimate_base_currency
            self._estimate_rate_to_base = Decimal("1")
            estimate_row = QHBoxLayout()
            estimate_row.setSpacing(2)
            estimate_row.addWidget(self.inp_est_price, 1)
            self.estimate_currency_group = QButtonGroup(self)
            self.estimate_currency_buttons = {}
            for code in ("TRY", "USD", "EUR"):
                button = QPushButton(CurrencyHelper.get_symbol(currency_code=code))
                button.setCheckable(True)
                button.setFixedSize(26, 30)
                button.setToolTip(code + ": Tutar " + self._estimate_base_currency + " olarak kaydedilir. Yerel kay\u0131tl\u0131 kur kullan\u0131l\u0131r.")
                button.setStyleSheet(theme_qss(
                    "QPushButton { background: @finance_surface_alt; color: @text_muted; "
                    "border: 1px solid @finance_outline; border-radius: 4px; padding: 0; font-size: 11px; } "
                    "QPushButton:checked { background: @finance_primary; color: @finance_primary_text; }"))
                self.estimate_currency_group.addButton(button)
                self.estimate_currency_buttons[code] = button
                button.clicked.connect(lambda _checked=False, currency=code: self._select_estimate_currency(currency))
                estimate_row.addWidget(button)
            self.estimate_currency_buttons[self._estimate_currency].setChecked(True)
            servis_grid.addLayout(self.create_field_box("Tahmini Tutar (KDV Dahil)", layout=estimate_row), 1, 1)
        self.cmb_delivery_method = ModernComboBox(
            items=[
                "Elden Teslim Al\u0131nd\u0131",
                "Kargo ile Geldi",
                "Yerinde Servis",
                "Bayi Arac\u0131l\u0131\u011f\u0131yla",
            ]
        )
        self.cmb_delivery_method.setMinimumHeight(36)
        servis_grid.addLayout(
            self.create_field_box(
                "Teslim Al\u0131n\u0131\u015f \u015eekli",
                self.cmb_delivery_method,
            ),
            2,
            0,
        )
        self.dt_estimated_delivery = QDateEdit()
        self.dt_estimated_delivery.setCalendarPopup(True)
        self.dt_estimated_delivery.setDisplayFormat("dd.MM.yyyy")
        self.dt_estimated_delivery.setDate(QDate.currentDate().addDays(3))
        self.dt_estimated_delivery.setMinimumHeight(36)
        delivery_calendar = self.dt_estimated_delivery.calendarWidget()
        delivery_calendar.setObjectName("serviceDeliveryCalendar")
        delivery_calendar.setAutoFillBackground(True)
        servis_grid.addLayout(
            self.create_field_box(
                "Tahmini Teslim Tarihi",
                self.dt_estimated_delivery,
            ),
            2,
            1,
        )
        self.inp_service_location = ValidatedLineEdit(
            "Konum ad\u0131, Google Maps ba\u011flant\u0131s\u0131 veya koordinat"
        )
        self.inp_service_location.setMinimumHeight(36)
        servis_grid.addLayout(
            self.create_field_box("Konum", self.inp_service_location),
            3,
            0,
            1,
            2,
        )
        self.inp_other_info = ValidatedLineEdit(
            "Teslim alan, ileti\u015fim tercihi veya di\u011fer bilgiler"
        )
        self.inp_other_info.setMinimumHeight(36)
        servis_grid.addLayout(
            self.create_field_box("Di\u011fer Bilgiler", self.inp_other_info),
            4,
            0,
            1,
            2,
        )
        if self.is_automotive:
            left_col.addLayout(servis_grid)
        else:
            password_field = servis_grid.itemAtPosition(0, 0).layout()
            servis_grid.removeItem(password_field)
            password_field.setParent(None)
            priority_fields = QGridLayout()
            priority_fields.setSpacing(8)
            for column, position in enumerate(((0, 1), (1, 1))):
                field = servis_grid.itemAtPosition(*position).layout()
                servis_grid.removeItem(field)
                field.setParent(None)
                priority_fields.addLayout(field, 0, column)
            left_col.addLayout(priority_fields)
            primary_col.takeAt(primary_col.count() - 1)
            self.btn_delivery_details = QPushButton("Ek Servis Bilgileri")
            self.btn_delivery_details.setAccessibleName("Ek servis ve teslim bilgileri")
            self.btn_delivery_details.setToolTip("Teknisyen, teslim tarihi, garanti ve not bilgilerini gosterir.")
            self.btn_delivery_details.setCheckable(True)
            self.btn_delivery_details.setMinimumSize(116, 24)
            self.btn_delivery_details.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_delivery_details.setStyleSheet(theme_qss(
                "QPushButton { background: @surface_alt; color: @text_muted; "
                "border: 1px solid @border; border-radius: 6px; padding: 0 7px; "
                "font-size: 10px; font-weight: 700; } "
                "QPushButton:checked { color: @text; border-color: @accent; }"
            ))
            self.delivery_details_panel = QFrame()
            self.delivery_details_panel.setObjectName("serviceDeliveryCard")
            self.delivery_details_panel.setStyleSheet(theme_qss(
                "QFrame#serviceDeliveryCard { background: @surface_alt; "
                "border: 1px solid @border; border-radius: 8px; }"
            ))
            delivery_panel_layout = QVBoxLayout(self.delivery_details_panel)
            delivery_panel_layout.setContentsMargins(12, 10, 12, 10)
            delivery_panel_layout.setSpacing(8)
            delivery_panel_title = QLabel("Servis ve teslim bilgileri")
            delivery_panel_title.setStyleSheet(theme_qss(
                "color: @text; font-size: 12px; font-weight: 700; "
                "border: none; background: transparent;"
            ))
            delivery_panel_layout.addWidget(delivery_panel_title)
            delivery_panel_layout.addLayout(servis_grid)
            self.delivery_details_panel.setVisible(False)
            self.btn_delivery_details.toggled.connect(
                self.delivery_details_panel.setVisible
            )
            self.btn_delivery_details.toggled.connect(
                lambda checked: self.btn_delivery_details.setText(
                    "Ek Servis Bilgilerini Gizle" if checked else "Ek Servis Bilgileri"
                )
            )
            primary_col.addWidget(self.delivery_details_panel)
            self.reference_delivery_card = self.delivery_details_panel
            device_card = getattr(self, "reference_device_card", None)
            device_layout = device_card.layout() if device_card is not None else None
            if device_layout is not None:
                device_layout.addWidget(self.btn_delivery_details)
            primary_col.addStretch(1)
        left_col.addSpacing(12)

        # 4. Fault description (fills remaining space)
        fault_extras_start = left_col.count()
        left_col.addWidget(self._sec("ARIZA TANIMI"))
        left_col.addSpacing(4)
        sector_fields_layout = self._build_sector_service_fields()
        if sector_fields_layout is not None:
            left_col.addWidget(self._sec("SEKTÖREL ALANLAR"))
            left_col.addSpacing(4)
            left_col.addLayout(sector_fields_layout)
            left_col.addSpacing(12)
        self.selected_fault_notes = set()
        self.fault_note_order = {}
        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)
        profile_items = ["Otomotiv"] if self.is_automotive else self._available_service_areas()
        self.cmb_service_profile = ModernComboBox(items=profile_items)
        self.cmb_service_profile.setCurrentText(self._service_area)
        self.cmb_service_profile.setMinimumHeight(34)
        self.cmb_service_profile.currentTextChanged.connect(self._on_service_area_changed)
        profile_row.addLayout(
            self.create_field_box("Hizmet Alan\u0131", self.cmb_service_profile), 1
        )
        left_col.addLayout(profile_row)
        left_col.addSpacing(6)
        self.lbl_fault_selected = QLabel("Kısayol seçimi yok")
        self.lbl_fault_selected.setFixedHeight(24)
        self.lbl_fault_selected.setStyleSheet(theme_qss(
            "color: @text_muted; padding: 3px 10px; background: @surface_alt; border: 1px solid @border; border-radius: 5px; font-size: 10px;"
        ))
        left_col.addWidget(self.lbl_fault_selected)
        left_col.addSpacing(4)
        self.txt_fault = QTextEdit()
        self.txt_fault.setPlaceholderText("Müşteri şikayeti ve detaylı arıza açıklaması...")
        self.txt_fault.setFixedHeight(64 if not self.is_automotive else 72)
        fault_padding = "6px 8px" if self.is_automotive else "6px 38px 6px 8px"
        self.txt_fault.setStyleSheet(theme_qss(
            "QTextEdit { border: 1px solid @border; border-radius: 6px; padding: " + fault_padding +
            "; font-size: 11px; background: @surface_alt; color: @text; }"
        ))
        self.txt_fault.textChanged.connect(self._on_fault_manual_changed)
        if not self.is_automotive:
            self.btn_fault_voice = ServiceVoiceButton(self.txt_fault)
            self.btn_fault_voice.setFixedSize(28, 28)
            self.btn_fault_voice.setToolTip("Mikrofon ile dikte et. Ses mevcut Google Speech Recognition hizmetiyle metne \u00e7evrilir.")
            self.btn_fault_voice.setAccessibleName("Ar\u0131za i\u00e7in sesli giri\u015f")
            self.btn_fault_voice.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_alt; color: @text_muted; "
                "border: 1px solid @finance_outline; border-radius: 4px; } "
                "QPushButton:disabled { color: @danger; }"))
            self.btn_fault_voice.clicked.connect(self._start_fault_dictation)
            self.txt_fault.installEventFilter(self)
        left_col.addWidget(self.txt_fault)
        left_col.addSpacing(6)
        sc_header = QHBoxLayout()
        lbl_sc = QLabel("Servis Profili Arızaları:")
        lbl_sc.setStyleSheet(theme_qss("font-weight: 800; color: @text_muted; font-size: 10px;"))
        btn_edit_sc = QPushButton("⚙️ Düzenle")
        btn_edit_sc.setFixedSize(74, 22)
        btn_edit_sc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit_sc.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 4px; color: @text_muted; font-weight: 600; font-size: 10px; }"
            "QPushButton:hover { color: @text; }"
        ))
        btn_edit_sc.clicked.connect(self.open_quick_notes_editor)
        sc_header.addWidget(lbl_sc)
        sc_header.addStretch()
        sc_header.addWidget(btn_edit_sc)
        left_col.addLayout(sc_header)
        left_col.addSpacing(4)
        self.fault_shortcuts_container = QFrame()
        self.fault_shortcuts_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        self.fs_grid = QGridLayout(self.fault_shortcuts_container)
        self.fs_grid.setContentsMargins(0, 0, 0, 0)
        self.fs_grid.setHorizontalSpacing(8)
        self.fs_grid.setVerticalSpacing(6)
        self.reload_fault_toggles()
        left_col.addWidget(self.fault_shortcuts_container)
        if not self.is_automotive:
            left_col.removeWidget(self.txt_fault)
            fault_label_row = QWidget()
            fault_labels = QHBoxLayout(fault_label_row)
            fault_labels.setContentsMargins(0, 0, 0, 0)
            fault_labels.setSpacing(6)
            self.lbl_reference_fault_description = QLabel("Ar\u0131za Tan\u0131m\u0131 ve M\u00fc\u015fteri \u015eikayeti *")
            self.lbl_reference_fault_description.setBuddy(self.txt_fault)
            self.lbl_reference_fault_hint = QLabel("Sesle yazd\u0131r\u0131labilir")
            for label in (self.lbl_reference_fault_description, self.lbl_reference_fault_hint):
                label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; letter-spacing: 0px; border: none; background: transparent;"))
            fault_labels.addWidget(self.lbl_reference_fault_description)
            fault_labels.addStretch()
            fault_labels.addWidget(self.lbl_reference_fault_hint)
            left_col.insertWidget(2, fault_label_row)
            left_col.insertWidget(3, self.txt_fault)
            shortcuts_card = self._wrap_reference_section(
                left_col, fault_extras_start + 2, "serviceFaultShortcutsCard")
            shortcuts_card.setVisible(False)
            fault_card = self._wrap_reference_section(left_col, 0, "serviceFaultCard")
            quick_issue_row = QWidget()
            quick_issue_layout = QHBoxLayout(quick_issue_row)
            quick_issue_layout.setContentsMargins(0, 0, 0, 0)
            quick_issue_layout.setSpacing(6)
            self.quick_issue_buttons = []
            for issue_text in ("G\u00f6r\u00fcnt\u00fc Gelmiyor", "S\u0131v\u0131 Temas\u0131", "A\u015f\u0131r\u0131 Is\u0131nma / Fan", "Format & Bak\u0131m"):
                issue_button = QPushButton(issue_text)
                issue_button.setFixedHeight(28)
                issue_button.setCursor(Qt.CursorShape.PointingHandCursor)
                issue_button.setStyleSheet(theme_qss(
                    "QPushButton { background: @surface_alt; border: 1px solid @border; "
                    "border-radius: 6px; padding: 0 8px; color: @text_muted; font-size: 10px; } "
                    "QPushButton:hover { border-color: @accent; color: @accent; }"
                ))
                issue_button.clicked.connect(
                    lambda checked=False, value=issue_text: self._append_quick_issue(value)
                )
                quick_issue_layout.addWidget(issue_button)
                self.quick_issue_buttons.append(issue_button)
            fault_card.layout().addWidget(quick_issue_row)
            fault_layout = fault_card.layout()
            priority_index = next(
                (index for index in range(fault_layout.count())
                 if fault_layout.itemAt(index).layout() is priority_fields),
                -1,
            )
            quick_index = fault_layout.indexOf(quick_issue_row)
            if priority_index >= 0 and quick_index > priority_index:
                fault_layout.takeAt(quick_index)
                fault_layout.takeAt(priority_index)
                fault_layout.insertWidget(priority_index, quick_issue_row)
                fault_layout.insertLayout(priority_index + 1, priority_fields)
            quick_issue_row.setVisible(False)
            self.btn_fault_advanced = QPushButton("+ Daha fazla ar\u0131za se\u00e7ene\u011fi")
            self.btn_fault_advanced.setCheckable(True)
            self.btn_fault_advanced.setFixedHeight(22)
            self.btn_fault_advanced.setStyleSheet(theme_qss(
                "QPushButton { background: transparent; border: none; color: @accent; "
                "text-align: left; font-size: 10px; }"
            ))
            self.btn_fault_advanced.toggled.connect(shortcuts_card.setVisible)
            self.btn_fault_advanced.toggled.connect(quick_issue_row.setVisible)
            self.btn_fault_advanced.toggled.connect(
                lambda checked: self.btn_fault_advanced.setText(
                    "- Daha fazla ar\u0131za se\u00e7ene\u011fi" if checked else "+ Daha fazla ar\u0131za se\u00e7ene\u011fi"
                )
            )
            fault_card.layout().addWidget(self.btn_fault_advanced)

        main_lay.addLayout(primary_col, 1)

        if self.is_automotive:
            v_line = QFrame()
            v_line.setFrameShape(QFrame.Shape.VLine)
            v_line.setFrameShadow(QFrame.Shadow.Plain)
            v_line.setStyleSheet(theme_qss(
                "border: none; border-left: 1px solid @border; background: @border;"
            ))
            v_line.setMaximumWidth(1)
            main_lay.addWidget(v_line)

        # The right column was prepared before the service details so they
        # remain at the top of the dialog.

        lock_section_start = right_col.count()

        # 1. Lock & Photos
        right_col.addWidget(self._sec("K\u0130L\u0130T DESEN\u0130 & G\u00dcVENL\u0130K \u015e\u0130FRES\u0130"))
        right_col.addSpacing(4)
        kilit_row = QHBoxLayout()
        kilit_row.setSpacing(12)
        self.pattern_lock = PatternLockWidget()
        self.pattern_lock.setFixedSize(150, 150)
        try:
            self.pattern_lock.setReadOnly(False)
        except Exception as e:
            logger.debug(f"Pattern lock read-only toggle unsupported: {e}")
        self.pattern_lock.setEnabled(True)
        foto_col = QVBoxLayout()
        foto_col.setSpacing(6)
        foto_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.btn_photo = QPushButton("Cihaz G\u00f6rseli Ekle")
        self.btn_photo.setFixedHeight(36)
        self.btn_photo.setCursor(Qt.CursorShape.PointingHandCursor)
        if not self.is_automotive:
            self.btn_photo.setAcceptDrops(True)
            self.btn_photo.installEventFilter(self)
        self.btn_photo.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; border: 1px solid @border; border-radius: 8px; font-weight: 600; color: @text; }"
            "QPushButton:hover { background: @border; }"
        ))
        self.btn_photo.setFixedWidth(136)
        self.btn_photo.clicked.connect(self.upload_photo)
        self.btn_photo_count = QPushButton("Seçilen Fotoğraflar")
        self.btn_photo_count.setVisible(False)
        self.btn_photo_count.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_photo_count.setStyleSheet(theme_qss(
            "QPushButton { background: @surface; border: 1px solid @accent; border-radius: 8px; color: @accent; font-weight: 700; font-size: 11px; padding: 4px 8px; }"
            "QPushButton:hover { background: @surface_alt; }"
        ))
        self.btn_photo_count.setFixedWidth(136)
        self.btn_photo_count.clicked.connect(self._open_photo_gallery)
        if not self.is_automotive:
            self.pattern_lock.setFixedSize(88, 88)
            self.btn_pattern_lock = QPushButton("Desen Kilidi")
            self.btn_pattern_lock.setFixedHeight(22)
            self.btn_pattern_lock.setFixedWidth(136)
            self.btn_pattern_lock.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_pattern_lock.setStyleSheet(
                theme_qss("QPushButton { background: transparent; color: @finance_primary; border: none; padding: 0; font-size: 9px; } QPushButton:hover { color: @accent; }")
            )
            self.btn_pattern_lock.clicked.connect(self.open_pattern_lock_dialog)
        foto_col.addWidget(self.btn_photo)
        foto_col.addWidget(self.btn_photo_count)
        if self.is_automotive:
            foto_col.addStretch()
        if not self.is_automotive:
            self.btn_pattern_lock.setText("Desen Kilidi Tan\u0131mla")
            for button in (self.btn_pattern_lock, self.btn_photo, self.btn_photo_count):
                button.setMinimumWidth(0)
                button.setMaximumWidth(16777215)
            self.reference_photo_preview = QWidget()
            self.reference_photo_preview_layout = QHBoxLayout(self.reference_photo_preview)
            self.reference_photo_preview_layout.setContentsMargins(0, 0, 0, 0)
            self.reference_photo_preview_layout.setSpacing(8)
            foto_col.addWidget(self.reference_photo_preview)
            self.btn_photo.setFixedHeight(138)
            self._update_photo_button()
            self._update_reference_photo_preview()
            self.reference_pattern_card = QFrame()
            self.reference_pattern_card.setStyleSheet(theme_qss(
                "QFrame { background: @window; border: 1px solid @border; border-radius: 10px; }"
            ))
            pattern_column = QVBoxLayout(self.reference_pattern_card)
            pattern_column.setContentsMargins(10, 8, 10, 8)
            pattern_column.setSpacing(5)
            pattern_title = QLabel("Desen Kilidi")
            pattern_title.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 10px; border: none; background: transparent;"
            ))
            pattern_column.addWidget(pattern_title, 0, Qt.AlignmentFlag.AlignCenter)
            pattern_column.addWidget(self.pattern_lock, 0, Qt.AlignmentFlag.AlignCenter)
            pattern_column.addWidget(self.btn_pattern_lock)
            kilit_row.addWidget(self.reference_pattern_card, 0)
            password_column = QVBoxLayout()
            password_column.setContentsMargins(0, 0, 0, 0)
            password_column.setSpacing(8)
            self.inp_bios_password = ValidatedLineEdit("Varsa giriniz...")
            self.inp_bios_password.setPlaceholderText("Varsa giriniz...")
            self.inp_bios_password.setMinimumHeight(36)
            self.inp_bios_password.setStyleSheet(
                theme_qss("QLineEdit { background: @finance_surface_lowest; color: @finance_text; border: 1px solid @finance_outline; "
                "border-radius: 4px; padding: 4px 8px; font-size: 14px; "
                "selection-background-color: @selection_bg; selection-color: @selection_text; }")
            )
            password_column.addLayout(password_field)
            password_column.addLayout(
                self.create_field_box("BIOS / Supervisor Parolas\u0131", self.inp_bios_password)
            )
            kilit_row.addLayout(password_column, 1)
        else:
            kilit_row.addLayout(foto_col, 0)
            kilit_row.addStretch()
        self.lbl_photo_list = QLabel()
        self.lbl_photo_list.setVisible(False)
        self.table_photos = QTableWidget()
        self.table_photos.setVisible(False)
        if self.is_automotive:
            kilit_row.addWidget(self.pattern_lock, 0)
        right_col.addLayout(kilit_row)
        if self.is_automotive:
            right_col.addLayout(foto_col)
        right_col.addSpacing(12)
        lock_section_items = []
        while right_col.count() > lock_section_start:
            lock_section_items.append(right_col.takeAt(lock_section_start))

        # 2. Optional notes stay available without displacing the photo/security cards.
        self.btn_service_notes = QPushButton("+ Notlar ve ek bilgiler")
        self.btn_service_notes.setCheckable(True)
        self.btn_service_notes.setFixedHeight(32)
        self.btn_service_notes.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; border: 1px solid @border; "
            "border-radius: 6px; color: @text_muted; text-align: left; padding: 0 10px; }"
        ))
        right_col.addWidget(self.btn_service_notes)
        notes_panel = QWidget()
        notes_layout = QVBoxLayout(notes_panel)
        notes_layout.setContentsMargins(0, 6, 0, 0)
        notes_layout.setSpacing(6)
        self.txt_public_note = QTextEdit()
        self.txt_public_note.setPlaceholderText("Müşteri fişi notu...")
        self.txt_public_note.setFixedHeight(46)
        notes_layout.addLayout(self.create_field_box("Genel Not (M\u00fc\u015fteri)", self.txt_public_note))
        self.txt_tech_note = QTextEdit()
        self.txt_tech_note.setPlaceholderText("Gizli teknik not...")
        self.txt_tech_note.setFixedHeight(46)
        notes_layout.addLayout(self.create_field_box("Teknik Not (Gizli)", self.txt_tech_note))
        notes_panel.setMaximumHeight(0)
        right_col.addWidget(notes_panel)
        self.btn_service_notes.toggled.connect(
            lambda checked: notes_panel.setMaximumHeight(16777215 if checked else 0)
        )
        self.btn_service_notes.toggled.connect(
            lambda checked: self.btn_service_notes.setText(
                "- Notlar ve ek bilgiler" if checked else "+ Notlar ve ek bilgiler"
            )
        )

        if self.is_automotive:
            right_col.addWidget(self._sec("SERVİS KABUL & YASAL"))
            right_col.addSpacing(4)
            acceptance_grid = QGridLayout()
            acceptance_grid.setSpacing(8)
            self.cmb_fuel_level_entry = ModernComboBox(
                items=["Boş", "Çeyrek", "Yarım", "Üç Çeyrek", "Full"],
                editable=False
            )
            self.cmb_fuel_level_entry.setMinimumHeight(36)
            self.inp_engine_code = ValidatedLineEdit("Motor Kodu")
            self.inp_engine_code.setMinimumHeight(36)
            self.chk_customer_approval = QCheckBox("Müşteri onayı alındı")
            self.chk_kvkk_approval = QCheckBox("KVKK bilgilendirmesi yapıldı")
            self.chk_customer_approval.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
            self.chk_kvkk_approval.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
            self.txt_approval_text = QTextEdit()
            self.txt_approval_text.setFixedHeight(60)
            self.txt_approval_text.setPlaceholderText("Müşteri onay metni")
            self.txt_kvkk_text = QTextEdit()
            self.txt_kvkk_text.setFixedHeight(60)
            self.txt_kvkk_text.setPlaceholderText("KVKK / yasal metin")
            acceptance_grid.addLayout(self.create_field_box("Yakıt Seviyesi", self.cmb_fuel_level_entry), 0, 0)
            acceptance_grid.addLayout(self.create_field_box("Motor Kodu", self.inp_engine_code), 0, 1)
            acceptance_grid.addWidget(self.chk_customer_approval, 1, 0)
            acceptance_grid.addWidget(self.chk_kvkk_approval, 1, 1)
            acceptance_grid.addLayout(self.create_field_box("Müşteri Onay Metni", self.txt_approval_text), 2, 0, 1, 2)
            acceptance_grid.addLayout(self.create_field_box("KVKK Metni", self.txt_kvkk_text), 3, 0, 1, 2)
            right_col.addLayout(acceptance_grid)
            right_col.addSpacing(8)
            action_row = QHBoxLayout()
            action_row.setSpacing(8)
            self.btn_edit_checklist = QPushButton("Kontrol Formu")
            self.btn_edit_checklist.setFixedHeight(36)
            self.btn_edit_checklist.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
            self.btn_edit_checklist.clicked.connect(self.open_automotive_checklist_dialog)
            self.btn_edit_damage = QPushButton("Hasar Tespiti")
            self.btn_edit_damage.setFixedHeight(36)
            self.btn_edit_damage.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            self.btn_edit_damage.clicked.connect(self.open_automotive_damage_dialog)
            action_row.addWidget(self.btn_edit_checklist)
            action_row.addWidget(self.btn_edit_damage)
            action_row.addStretch(1)
            right_col.addLayout(action_row)
            self.lbl_automotive_form_summary = QLabel("Kontrol formu ve hasar tespiti henüz doldurulmadı.")
            self.lbl_automotive_form_summary.setWordWrap(True)
            self.lbl_automotive_form_summary.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
            right_col.addWidget(self.lbl_automotive_form_summary)
            self.txt_approval_text.setPlainText(self._default_approval_text())
            self.txt_kvkk_text.setPlainText(self._default_kvkk_text())
            self._update_automotive_form_summary()
            right_col.addSpacing(12)

        descriptor_sections = self._build_descriptor_service_sections()
        for section_layout in descriptor_sections:
            right_col.addLayout(section_layout)
            right_col.addSpacing(12)

        # 3. Accessories (fills remaining space)
        accessory_col = right_col if self.is_automotive else None
        accessory_heading = self._sec("TESL\u0130M ALINAN AKSESUAR & DONANIMLAR")
        if accessory_col is not None:
            accessory_col.addWidget(accessory_heading)
            accessory_col.addSpacing(4)
        self.acc_grid = QGridLayout()
        self.acc_grid.setSpacing(6)
        self.accessory_checkboxes = {}
        try:
            accs = [a for a in self.db.get_fast_notes('Aksesuar') if a[3] == 1]
            if not accs:
                accs = [a for a in self.db.get_quick_notes('accessories_notes') if a[3] == 1]
            r, c = 0, 0
            for ac in accs:
                name = str(ac[2] or "").strip()
                if not name:
                    continue
                acc_card = QFrame()
                acc_card.setStyleSheet(theme_qss(
                    "background: @surface_alt; border: 1px solid @border; border-radius: 7px;"
                ))
                cl = QHBoxLayout(acc_card)
                cl.setContentsMargins(10, 7, 10, 7)
                checkbox = QCheckBox()
                checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
                checkbox.setAccessibleName(name)
                checkbox.setStyleSheet(theme_qss(
                    "QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @border; "
                    "border-radius: 4px; background: @surface; } "
                    "QCheckBox::indicator:checked { background: @accent; border-color: @accent; }"
                ))
                label = QLabel(name)
                label.setCursor(Qt.CursorShape.PointingHandCursor)
                label.setStyleSheet(theme_qss(
                    "color: @text; font-size: 10px; font-weight: 600; border: none; "
                    "background: transparent;"
                ))
                label.mousePressEvent = lambda event, control=checkbox: control.toggle()
                cl.addWidget(checkbox)
                cl.addWidget(label, 1)
                self.acc_grid.addWidget(acc_card, r, c)
                self.accessory_checkboxes[name] = checkbox
                checkbox.toggled.connect(self._handle_accessory_toggle_changed)
                c += 1
                if c >= 4:
                    c = 0
                    r += 1
        except Exception as e:
            logger.warning(f"NewServiceDialog accessory card build failed: {e}")
        if self.is_automotive:
            accessory_col.addLayout(self.acc_grid)
        else:
            device_card = getattr(self, "reference_device_card", None)
            device_layout = device_card.layout() if device_card is not None else None
            if device_layout is not None:
                accessory_divider = QFrame()
                accessory_divider.setFixedHeight(1)
                accessory_divider.setStyleSheet(
                    theme_qss("background: @finance_outline; border: none;")
                )
                device_layout.addWidget(accessory_divider)
                if self.btn_delivery_details is not None:
                    device_layout.removeWidget(self.btn_delivery_details)
                    accessory_header = QHBoxLayout()
                    accessory_header.setContentsMargins(0, 0, 0, 0)
                    accessory_header.setSpacing(8)
                    accessory_header.addWidget(accessory_heading, 1)
                    accessory_header.addWidget(self.btn_delivery_details)
                    device_layout.addLayout(accessory_header)
                else:
                    device_layout.addWidget(accessory_heading)
                device_layout.addLayout(self.acc_grid)
                delivery_card = getattr(self, "reference_delivery_card", None)
                if delivery_card is not None:
                    primary_col.removeWidget(delivery_card)
                    device_layout.addWidget(delivery_card)

        if not self.is_automotive:
            primary_col.addStretch(1)
        else:
            right_col.addStretch(1)
        for item in lock_section_items:
            if item.widget() is not None:
                right_col.addWidget(item.widget())
            elif item.layout() is not None:
                right_col.addLayout(item.layout())
            elif item.spacerItem() is not None:
                right_col.addItem(item)
        if not self.is_automotive:
            lock_start = right_col.count() - len(lock_section_items)
            lock_card = self._wrap_reference_section(right_col, lock_start, "serviceLockCard")
            right_col.removeWidget(lock_card)
            right_col.insertWidget(1, lock_card)
            photo_start = right_col.count()
            right_col.addWidget(self._sec("C\u0130HAZ G\u00d6RSEL\u0130 & EKSPERT\u0130Z FOTO\u011eRAFLARI"))
            right_col.addLayout(foto_col)
            photo_card = self._wrap_reference_section(
                right_col, photo_start, "servicePhotoCard"
            )
            right_col.removeWidget(photo_card)
            right_col.insertWidget(2, photo_card)
            right_col.setSpacing(16)

        main_lay.addLayout(right_col, 1)
        root_layout.addWidget(columns_widget, 1)
        self.scroll_area.setWidget(main_widget)
        self._apply_wheel_bridge_recursive(main_widget)

        # Footer

        self.footer_layout.setContentsMargins(24, 0, 24, 0)
        self.footer_layout.setSpacing(12)
        if not self.is_automotive:
            self.lbl_service_accept_status = QLabel(
                "ERP Core v2.0.4 Online   \u00b7   USD Kuru: 49.20 TL   \u00b7   Servis Kayd\u0131"
            )
            self.lbl_service_accept_status.setStyleSheet(theme_qss(
                "color: @text_muted; background: transparent; border: none; "
                "font-family: 'Consolas'; font-size: 10px; letter-spacing: 0px;"
            ))
            self.footer_layout.addWidget(self.lbl_service_accept_status)
            self.footer_layout.addStretch(1)
        btn_cancel = QPushButton("\u0130ptal")
        self.btn_cancel = btn_cancel
        btn_cancel.setFixedSize(76, 40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss(
            "QPushButton { background: @finance_surface_alt; color: @text_muted; "
            "border: 1px solid @finance_outline; border-radius: 4px; font-weight: bold; }"
        ))
        btn_cancel.clicked.connect(self.reject)
        self.btn_save_and_form = QPushButton("Kayd\u0131 Tamamla ve Fi\u015f Olu\u015ftur")
        self.btn_save_and_form.setFixedHeight(40)
        self.btn_save_and_form.setMinimumWidth(312)
        self.btn_save_and_form.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_and_form.setStyleSheet(theme_qss(
            "QPushButton { background-color: @finance_primary; color: @finance_primary_text; "
            "border-radius: 4px; font-weight: bold; border: none; font-size: 11px; }"
        ))
        self.btn_save_and_form.clicked.connect(lambda: self.save(open_service_form_after=True))
        action_text = "Kayd\u0131 G\u00fcncelle" if self.device_data else "Servis Kayd\u0131 Olu\u015ftur"
        self.btn_action = QPushButton(action_text)
        self.btn_action.setFixedHeight(40)
        self.btn_action.setMinimumWidth(200)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(theme_qss(
            "QPushButton { background-color: @finance_secondary; color: @selection_text; "
            "border-radius: 4px; font-weight: bold; border: none; font-size: 11px; }"
        ))
        self.btn_action.clicked.connect(self.save)
        self.btn_action.setVisible(False)
        self.footer_layout.addWidget(btn_cancel)
        if not self.is_automotive:
            self.btn_reset_form = QPushButton("De\u011fi\u015fiklikleri Geri Al" if self.device_data else "Temizle")
            self.btn_reset_form.setFixedSize(122, 40)
            self.btn_reset_form.setStyleSheet(theme_qss(
                "QPushButton { background: @finance_surface_alt; color: @text_muted; "
                "border: 1px solid @finance_outline; border-radius: 4px; padding: 4px 12px; "
                "font-weight: bold; }"))
            self.btn_reset_form.setEnabled(False)
            self.btn_reset_form.setToolTip("Formu ilk a\u00e7\u0131ld\u0131\u011f\u0131 de\u011ferlere d\u00f6nd\u00fcr\u00fcr; kay\u0131tlara yazmaz.")
            self.btn_reset_form.clicked.connect(self._reset_reference_form)
            self.footer_layout.addWidget(self.btn_reset_form)
        if self.is_automotive:
            self.footer_layout.addStretch()
        self.footer_layout.addWidget(self.btn_save_and_form)
        self.footer_layout.addWidget(self.btn_action)

        self.setStyleSheet(theme_qss(
            "QLineEdit, QTextEdit, QComboBox { background: @surface; border: 1px solid @border; border-radius: 6px; padding: 4px 8px; color: @text; }"
            "QLineEdit:focus, QTextEdit:focus, QComboBox:focus { border: 1px solid @accent; }"
            "QLabel { color: @text; }"
        ))

    def open_quick_notes_editor(self):
        from src.ui.dialogs.quick_notes_editor import QuickNotesEditor
        try:
            try:
                self.btn_action.setEnabled(False)
            except Exception as e:
                logger.debug(f"Action button disable skipped: {e}")
            try:
                editor = QuickNotesEditor(self.db, self, initial_category="Arıza Hızlı Seçimi", sector_manager=self.sector_manager)
            except TypeError:
                editor = QuickNotesEditor(self.db, self, initial_category="Arıza Hızlı Seçimi")
            if editor.exec():
                self.reload_fault_toggles()
                self.reload_accessory_cards()
        finally:
            try:
                self.btn_action.setEnabled(True)
            except Exception as e:
                logger.debug(f"Action button enable skipped: {e}")

    def _enabled_device_profiles(self):
        raw = ""
        try:
            raw = self.db.get_internal_setting("device_business_profiles", "")
        except Exception:
            raw = ""
        profiles = [
            item.strip() for item in str(raw or "").split(",")
            if item.strip() in DEVICE_PROFILE_AREAS
        ]
        return profiles or ["bilgisayar"]

    def _available_service_areas(self):
        areas = [DEVICE_PROFILE_AREAS[item] for item in self._enabled_device_profiles()]
        return list(dict.fromkeys(areas)) or ["Bilgisayar"]

    def _profiles_for_service_area(self, area):
        selected = [
            profile for profile in self._enabled_device_profiles()
            if DEVICE_PROFILE_AREAS.get(profile) == area
        ]
        return selected or self._enabled_device_profiles()

    def _device_types_for_service_area(self, area):
        device_types = []
        try:
            rows = self.db.get_device_model_catalog(
                profiles=self._profiles_for_service_area(area)
            )
            device_types = [str(row[1]).strip() for row in rows if row[1]]
        except Exception as exc:
            logger.debug("Device catalog type lookup failed: %s", exc)
        defaults = TECH_DEVICE_TYPES.get(area, TECH_DEVICE_TYPES["Bilgisayar"])
        return list(dict.fromkeys(list(defaults) + device_types))

    def _current_profile_labels(self, category):
        profile = getattr(self, "_service_area", "Bilgisayar")
        preset = PROFILE_PRESETS.get(profile) or {}
        labels = list(preset.get(category, []) or [])
        if category == "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi" and OTHER_DEVICE_TYPE not in labels:
            labels.append(OTHER_DEVICE_TYPE)
        return labels

    def _on_service_area_changed(self, area):
        if self.is_automotive:
            return
        area = str(area or "Bilgisayar").strip()
        if area not in self._available_service_areas():
            area = self._available_service_areas()[0]
        self._service_area = area
        current = self._selected_device_type() if hasattr(self, "cmb_device") else ""
        self.cmb_device.blockSignals(True)
        self.cmb_device.clear()
        device_types = self._device_types_for_service_area(area)
        self.cmb_device.addItems(device_types + [OTHER_DEVICE_TYPE])
        if current in device_types:
            self.cmb_device.setCurrentText(current)
        else:
            self.cmb_device.setCurrentIndex(0)
        self.cmb_device.blockSignals(False)
        self._on_device_type_changed(self.cmb_device.currentText())
        self.selected_fault_notes.clear()
        self.fault_note_order.clear()
        self.reload_fault_toggles()
        self.reload_accessory_cards()
        self._update_fault_selected_label()

    def _on_device_type_changed(self, device_type):
        is_other = str(device_type or "").strip() == OTHER_DEVICE_TYPE
        if hasattr(self, "other_device_wrap"):
            self.other_device_wrap.setVisible(is_other)
        query_type = self.inp_other_device.text().strip() if is_other else device_type
        self._load_brands_for_device_type(query_type, preserve_current=False)

    def _on_brand_changed(self, brand):
        self._load_models_for_device_brand(
            self._selected_device_type(), brand, preserve_current=False
        )

    def _selected_device_type(self):
        selected = self.cmb_device.currentText().strip()
        if selected == OTHER_DEVICE_TYPE and hasattr(self, "inp_other_device"):
            return self.inp_other_device.text().strip()
        return selected

    def apply_service_profile(self):
        profile_name = self.cmb_service_profile.currentText().strip()
        preset = PROFILE_PRESETS.get(profile_name)
        if not preset:
            ToastManager.warning(self, "Profil bulunamadı.")
            return
        try:
            for category, labels in preset.items():
                self.db.cursor.execute("DELETE FROM fast_notes WHERE category=?", (category,))
                for idx, label in enumerate(labels):
                    self.db.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        (category, label, 1, idx),
                    )
            self.db.conn.commit()
            self.reload_fault_toggles()
            self.reload_accessory_cards()
            ToastManager.success(self, f"{profile_name} profili uygulandı. Teknisyen paneli de bu listeyi kullanacak.")
        except Exception as e:
            ToastManager.error(self, f"Profil uygulanamadı: {e}")

    # Legacy page navigation methods (no-op now)
    def update_navigation(self): pass
    def next_step(self): pass
    def prev_step(self): pass
    def handle_action_button(self): self.save()

    def _legacy_page3_stub(self):
        """Legacy page3 reference compatibility; not called"""
        acc_grid = QGridLayout()
        self.accessory_checkboxes = {}
        try:
            accs = [a for a in self.db.get_fast_notes('Aksesuar') if a[3] == 1]
            if not accs:
                accs = [a for a in self.db.get_quick_notes('accessories_notes') if a[3] == 1]
            r, c = 0, 0
            for ac in accs:
                name = str(ac[2] or "").strip()
                if not name:
                    continue
                card = QFrame()
                card.setStyleSheet(theme_qss(
                    "background: @surface_alt; border: 1px solid @border; border-radius: 12px;"
                ))
                cl = QVBoxLayout(card)
                cl.setContentsMargins(14, 12, 14, 12)
                cl.setSpacing(8)
                lbl = QLabel(name)
                lbl.setStyleSheet(theme_qss(
                    "font-size: 12px; font-weight: 800; color: @text; border: none;"
                ))
                tgl = AnimatedToggle()
                tgl.setFixedSize(40, 20)
                tgl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.mousePressEvent = lambda event, t=tgl: t.toggle()
                wrap = QHBoxLayout()
                wrap.addStretch()
                wrap.addWidget(tgl)
                wrap.addStretch()
                cl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
                cl.addLayout(wrap)
                acc_grid.addWidget(card, r, c)
                self.accessory_checkboxes[name] = tgl
                tgl.toggled.connect(self._handle_accessory_toggle_changed)
                c += 1
                if c >= 3:
                    c = 0
                    r += 1
        except Exception as e:
            logger.warning(f"NewServiceDialog accessory grid load failed: {e}")

    def load_customers(self):
        self.cmb_customer.clear()
        customers = self.db.get_customers()
        description = getattr(getattr(self.db, "cursor", None), "description", None) or []
        columns = [column[0] for column in description]
        self._reference_customer_rows = {}
        for c in customers:
            row = dict(c) if hasattr(c, "keys") else dict(zip(columns, c))
            self._reference_customer_rows[c[0]] = row
            self.cmb_customer.addItem(c[1], c[0])
        self.cmb_customer.addItem("+ Yeni M\u00fc\u015fteri Ekle", "__new_customer__")
        self.cmb_customer.activated.connect(self._on_service_customer_activated)
        if not self.device_data and not self._initial_customer_name:
            self.cmb_customer.setCurrentIndex(-1)
            self.cmb_customer.setEditText("")
        self._refresh_reference_customer_fields()

    def _refresh_reference_customer_fields(self, _index=None):
        if not hasattr(self, "inp_customer_identity"):
            return
        row = getattr(self, "_reference_customer_rows", {}).get(self.cmb_customer.currentData(), {})
        self.inp_customer_identity.setText(str(row.get("tc_no") or row.get("tax_id") or row.get("tax_no") or ""))
        self.inp_customer_phone.setText(str(row.get("phone") or ""))
        if hasattr(self, "lbl_reference_customer_status"):
            selected = self.cmb_customer.currentData() is not None
            self.lbl_reference_customer_status.setText(
                "Durum: Kay\u0131tl\u0131 m\u00fc\u015fteri se\u00e7ildi"
                if selected else "Durum: Yeni M\u00fc\u015fteri Kayd\u0131"
            )
            color = "@finance_secondary"
            self.lbl_reference_customer_status.setStyleSheet(theme_qss("color: " + color + "; font-size: 10px; letter-spacing: 0px; border: none; background: transparent;"))

    def _on_service_customer_activated(self, index):
        if self.cmb_customer.itemData(index) != "__new_customer__":
            return
        self.cmb_customer.setCurrentIndex(-1)
        self.cmb_customer.setEditText("")
        self._refresh_reference_customer_fields()
        self.quick_add_customer()

    def load_personnel(self):
        self.cmb_personnel.clear()
        self.cmb_personnel.addItem("Atanmadı", None)
        try:
            self.cmb_personnel.setEditable(True)
        except Exception as e:
            logger.debug(f"Personnel combo editable mode not supported: {e}")

        try:
            cur = self.db.conn.cursor()
            cols = self.db._get_table_columns("personnel") if hasattr(self.db, "_get_table_columns") else []
            name_idx = cols.index("name") if "name" in cols else 1
            id_idx = cols.index("id") if "id" in cols else 0
            active_col = "is_active" if "is_active" in cols else ("active" if "active" in cols else None)
            active_idx = cols.index(active_col) if active_col and active_col in cols else None

            cur.execute("SELECT * FROM personnel ORDER BY name")
            rows = cur.fetchall()
            names = []
            for r in rows:
                try:
                    if active_idx is not None:
                        a = r[active_idx]
                        if a is not None and int(a) == 0:
                            continue
                except Exception:
                    logger.debug("Personnel row active flag parse failed")

                name = str(r[name_idx] or "").strip()
                if not name:
                    continue
                pid = r[id_idx]
                self.cmb_personnel.addItem(name, pid)
                names.append(name)

            try:
                completer = QCompleter(names)
                completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                completer.setFilterMode(Qt.MatchFlag.MatchContains)
                self.cmb_personnel.setCompleter(completer)
            except Exception as e:
                logger.debug(f"Personnel completer setup failed: {e}")
        except Exception as e:
            logger.warning(f"Personnel load failed: {e}")
            try:
                for p in self.db.get_all_personnel():
                    if len(p) > 1 and p[1]:
                        self.cmb_personnel.addItem(str(p[1]))
            except Exception as fallback_e:
                logger.warning(f"Personnel fallback load failed: {fallback_e}")

    def quick_add_customer(self):
        sector_manager = getattr(self, "sector_manager", None)
        if not hasattr(self, "is_automotive"):
            from src.ui.dialogs.add_customer_dialog import AddCustomerDialog as dialog_cls
        elif getattr(self, "is_automotive", False):
            from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog as dialog_cls
        try:
            dialog = dialog_cls(self.db, self, sector_manager=sector_manager)
        except TypeError:
            dialog = dialog_cls(self.db, self)
        if dialog.exec():
            self.load_customers()
            if dialog.saved_customer_name:
                self.cmb_customer.setCurrentText(dialog.saved_customer_name)

    def toggle_fault_note(self, note_text, is_checked):
        note_text = str(note_text or "").strip()
        if not note_text:
            return
        if is_checked:
            self.selected_fault_notes.add(note_text)
        else:
            try:
                self.selected_fault_notes.remove(note_text)
            except KeyError:
                logger.debug("Fault note remove skipped; key already missing")
        self._update_fault_selected_label()

    def _append_quick_issue(self, issue_text):
        current = self.txt_fault.toPlainText().strip()
        if issue_text in current:
            return
        self.txt_fault.setPlainText((current + "\n" if current else "") + issue_text)

    def _on_fault_manual_changed(self):
        if not hasattr(self, "selected_fault_notes"):
            return
        self._update_fault_selected_label()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "btn_photo", None):
            if event.type() == QEvent.Type.DragEnter and event.mimeData().hasUrls():
                event.acceptProposedAction()
                return True
            if event.type() == QEvent.Type.Drop and event.mimeData().hasUrls():
                paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
                self._add_selected_photos(paths)
                event.acceptProposedAction()
                return True
        if obj is getattr(self, "txt_fault", None) and event.type() == QEvent.Type.Resize:
            button = getattr(self, "btn_fault_voice", None)
            if button is not None:
                button.move(max(0, obj.width() - button.width() - 8), 8)
                button.raise_()
        return super().eventFilter(obj, event)

    def _voice_input_available(self):
        import importlib.util
        return all(importlib.util.find_spec(module) is not None for module in ("speech_recognition", "pyaudio"))

    def _create_fault_voice_worker(self):
        from src.utils.ai_service import AIService
        from src.utils.voice_worker import VoiceWorker
        return VoiceWorker(AIService(self.db), QApplication.instance())

    def _start_fault_dictation(self):
        worker = getattr(self, "_fault_voice_worker", None)
        if worker is not None:
            return
        try:
            if not self._voice_input_available():
                ToastManager.warning(self, "Sesli giri\u015f i\u00e7in speech_recognition ve PyAudio gerekir.")
                return
            worker = self._create_fault_voice_worker()
            self._fault_voice_worker = worker
            self._fault_voice_discarded = False
            self._fault_voice_placeholder = self.txt_fault.placeholderText()
            worker.text_received.connect(self._append_fault_dictation)
            worker.error_occurred.connect(self._fault_dictation_error)
            worker.finished.connect(self._finish_fault_dictation)
            worker.finished.connect(worker.deleteLater)
            self.btn_fault_voice.setEnabled(False)
            self.txt_fault.setPlaceholderText("Dinleniyor... Ar\u0131zay\u0131 anlat\u0131n.")
            worker.start()
        except Exception as exc:
            self._finish_fault_dictation()
            self._fault_dictation_error(str(exc))

    def _append_fault_dictation(self, text):
        if getattr(self, "_fault_voice_discarded", False):
            return
        text = str(text or "").strip()
        if text:
            current = self.txt_fault.toPlainText().rstrip()
            self.txt_fault.setPlainText(current + ("\n" if current else "") + text)

    def _fault_dictation_error(self, message):
        if not getattr(self, "_fault_voice_discarded", False):
            ToastManager.warning(self, "Sesli giri\u015f tamamlanamad\u0131: " + str(message))

    def _finish_fault_dictation(self):
        self._fault_voice_worker = None
        self.btn_fault_voice.setEnabled(True)
        placeholder = getattr(self, "_fault_voice_placeholder", None)
        if placeholder is not None:
            self.txt_fault.setPlaceholderText(placeholder)

    def _compose_fault_description(self):
        selected = list(getattr(self, "selected_fault_notes", set()) or [])
        if hasattr(self, "fault_note_order") and self.fault_note_order:
            selected.sort(key=lambda x: self.fault_note_order.get(x, 10_000))
        else:
            selected.sort()
        selected_line = "  •  ".join(selected).strip()
        manual = self.txt_fault.toPlainText().strip() if hasattr(self, "txt_fault") else ""
        if selected_line and manual:
            return f"{selected_line}\n{manual}"
        if selected_line:
            return selected_line
        return manual

    def _update_fault_selected_label(self):
        if not hasattr(self, "lbl_fault_selected"):
            return
        selected = list(getattr(self, "selected_fault_notes", set()) or [])
        if hasattr(self, "fault_note_order") and self.fault_note_order:
            selected.sort(key=lambda x: self.fault_note_order.get(x, 10_000))
        else:
            selected.sort()
        if selected:
            self.lbl_fault_selected.setText("  •  ".join(selected))
        else:
            self.lbl_fault_selected.setText("Kısayol seçimi yok")

    def load_device_from_data(self):
        d = self.device_data
        if not d:
            return

        tracking_no = d[1]

        if self.sector_manager and hasattr(self.db, "get_device_with_extensions"):
            full_data = self.db.get_device_with_extensions(tracking_no=tracking_no, sector_id=self._active_sector_id())
        else:
            self.db.cursor.execute(
                "SELECT * FROM devices WHERE tracking_no=?",
                (tracking_no,)
            )
            row = self.db.cursor.fetchone()
            columns = [column[0] for column in (self.db.cursor.description or [])]
            full_data = (dict(row) if hasattr(row, "keys") else dict(zip(columns, row))) if row else None

        if not full_data:
            return

        # Set fields
        getter = (lambda key, idx: full_data.get(key)) if isinstance(full_data, dict) else (lambda key, idx: full_data[idx])
        self.cmb_customer.setCurrentText(str(getter("customer_name", 1) or ""))
        if hasattr(self, "inp_delivered_by"):
            self.inp_delivered_by.setText(str(getter("delivered_by_name", None) or ""))
            self.inp_delivered_phone.setText(str(getter("delivered_by_phone", None) or ""))
        saved_model = str(getter("device_model", 3) or "")
        self.inp_serial.setText(str(getter("serial_no", 4) or ""))
        self.cmb_urgency.setCurrentText(str(getter("urgency", 6) or ""))
        device_type = str(getter("device_type", 12) or "Laptop")
        if not self.is_automotive:
            matching_area = next(
                (
                    area for area, items in TECH_DEVICE_TYPES.items()
                    if device_type in items
                ),
                None,
            )
            if matching_area:
                self.cmb_service_profile.setCurrentText(matching_area)
                self.cmb_device.setCurrentText(device_type)
            else:
                self.cmb_device.setCurrentText(OTHER_DEVICE_TYPE)
                self.inp_other_device.setText(device_type)
                self.other_device_wrap.setVisible(True)
        else:
            self.cmb_device.setCurrentText(device_type)
        self._load_brands_for_device_type(device_type, preserve_current=False)
        self.cmb_brand.setCurrentText(str(getter("device_brand", 2) or ""))
        self._load_models_for_device_brand(
            device_type, self.cmb_brand.currentText(), preserve_current=False
        )
        self.cmb_model.setCurrentText(saved_model)
        if hasattr(self, "cmb_delivery_method"):
            self.cmb_delivery_method.setCurrentText(
                str(getter("delivery_method", None) or "")
            )
        if hasattr(self, "dt_estimated_delivery"):
            estimated_text = str(getter("estimated_date", None) or "")[:10]
            estimated_value = QDate.fromString(estimated_text, "yyyy-MM-dd")
            if estimated_value.isValid():
                self.dt_estimated_delivery.setDate(estimated_value)
        if hasattr(self, "inp_service_location"):
            self.inp_service_location.setText(
                str(getter("service_location", None) or "")
            )
        if hasattr(self, "inp_other_info"):
            self.inp_other_info.setText(
                str(getter("other_info", None) or "")
            )
        if hasattr(self, "inp_est_price"):
            self.inp_est_price.setText(
                str(getter("price", None) or "0.00")
            )
        self._set_sector_service_values({
            "device_type": getter("device_type", 12),
            "serial_no": getter("serial_no", 4),
            "vehicle_plate": getter("vehicle_plate", 13),
            "vehicle_vin": getter("vehicle_vin", 14),
            "warranty_status": getter("warranty_status", None),
            "current_km": getter("current_km", None),
            "service_type": getter("service_type", None),
        })
        self._set_descriptor_service_values({
            "approval_status": getter("approval_status", None),
            "estimated_date": getter("estimated_date", None),
            "inspection_summary": getter("inspection_summary", None),
            "invoice_ready": bool(getter("invoice_ready_at", None)),
        })
        if self.is_automotive and hasattr(self.db, "get_automotive_service_form"):
            form_row = self.db.get_automotive_service_form(tracking_no=tracking_no)
            if form_row:
                import json
                form_data = dict(form_row) if hasattr(form_row, "keys") else {}
                if hasattr(self, "cmb_fuel_level_entry"):
                    self.cmb_fuel_level_entry.setCurrentText(str(form_data.get("fuel_level_entry", "") or ""))
                if hasattr(self, "inp_engine_code"):
                    self.inp_engine_code.setText(str(form_data.get("engine_code", "") or ""))
                if hasattr(self, "chk_customer_approval"):
                    self.chk_customer_approval.setChecked(bool(form_data.get("customer_approval")))
                if hasattr(self, "chk_kvkk_approval"):
                    self.chk_kvkk_approval.setChecked(bool(form_data.get("kvkk_approval")))
                if hasattr(self, "txt_approval_text"):
                    self.txt_approval_text.setPlainText(str(form_data.get("customer_approval_text", "") or ""))
                if hasattr(self, "txt_kvkk_text"):
                    self.txt_kvkk_text.setPlainText(str(form_data.get("kvkk_text", "") or ""))
                try:
                    self.automotive_checklist_data = {"items": json.loads(form_data.get("checklist_json", "[]"))}
                except Exception:
                    self.automotive_checklist_data = {"items": []}
                try:
                    damage_loaded = json.loads(form_data.get("damage_marks_json", "{}"))
                    self.automotive_damage_data = damage_loaded if isinstance(damage_loaded, dict) else {"items": damage_loaded}
                except Exception:
                    self.automotive_damage_data = {"items": [], "general_note": ""}
                self._update_automotive_form_summary()

        # Load fault description
        fault_text = str(getter("fault_description", 5) or "")
        try:
            for t in self.fault_toggles.values():
                t.blockSignals(True)
                t.setChecked(False)
                t.blockSignals(False)
        except Exception as e:
            logger.debug(f"Fault toggles reset failed: {e}")
        try:
            self.selected_fault_notes = set()
        except Exception as e:
            logger.debug(f"Fault selection set reset failed: {e}")

        lines = [ln for ln in str(fault_text).splitlines()]
        first_line = lines[0] if lines else ""
        manual_text = str(fault_text).strip()
        try:
            if self.fault_toggles and any(k.upper() in first_line.upper() for k in self.fault_toggles.keys()):
                manual_text = "\n".join(lines[1:]).strip()
        except Exception as e:
            logger.debug(f"Fault manual text compose fallback used: {e}")

        try:
            self.txt_fault.blockSignals(True)
            self.txt_fault.setText(manual_text)
            self.txt_fault.blockSignals(False)
        except Exception:
            self.txt_fault.setText(manual_text)

        # Load notes
        self.txt_tech_note.setText(str(getter("internal_notes", 8) or ""))
        self.txt_public_note.setText(str(getter("repair_details", 9) or ""))

        # Parse and activate toggles
        fault_text_upper = fault_text.upper()
        for fault_name, toggle in self.fault_toggles.items():
            if fault_name.upper() in fault_text_upper:
                toggle.blockSignals(True)
                toggle.setChecked(True)
                toggle.blockSignals(False)
                try:
                    self.selected_fault_notes.add(fault_name)
                except Exception as e:
                    logger.debug(f"Fault selection add failed for '{fault_name}': {e}")
        self._update_fault_selected_label()

        # Load accessories
        accessories_str = str(getter("accessories", 10) or "")
        saved_accs = [s.strip().upper() for s in accessories_str.split(",") if s.strip()]
        for acc_name, tgl in self.accessory_checkboxes.items():
            if acc_name.upper() in saved_accs:
                tgl.blockSignals(True)
                tgl.setChecked(True)
                tgl.blockSignals(False)

        # Load pattern lock
        if getter("pattern_lock", 11):
            self.pattern_lock.set_pattern_string(str(getter("pattern_lock", 11)))

        # Load technician
        if getter("technician", 7):
            try:
                self.cmb_personnel.setCurrentText(str(getter("technician", 7)))
            except Exception as e:
                logger.debug(f"Personnel current text set failed: {e}")

        # Load device password if available
        try:
            self.db.cursor.execute("SELECT device_password FROM devices WHERE tracking_no=?", (tracking_no,))
            pwd_result = self.db.cursor.fetchone()
            if pwd_result and pwd_result[0]:
                self.inp_password.setText(str(pwd_result[0]))
        except Exception as e:
            logger.warning(f"Device password load failed: {e}")
        try:
            self.db.cursor.execute("SELECT bios_password FROM devices WHERE tracking_no=?", (tracking_no,))
            bios_result = self.db.cursor.fetchone()
            if bios_result and bios_result[0]:
                self.inp_bios_password.setText(str(bios_result[0]))
        except Exception as e:
            logger.warning(f"BIOS password load failed: {e}")

        try:
            self.photo_paths = []
            self.photo_labels = []
            if self._photos_table_exists():
                rows = self.db.get_photos(tracking_no) or []
                for r in rows:
                    path = r[1]
                    label = r[2] or ""
                    if path and os.path.exists(path):
                        self.photo_paths.append(path)
                        self.photo_labels.append(label)
            if not self.photo_paths:
                self.db.cursor.execute("SELECT photo_path, photo_paths FROM devices WHERE tracking_no=?", (tracking_no,))
                photo_result = self.db.cursor.fetchone()
                paths = []
                if photo_result:
                    if photo_result[0]:
                        paths.append(str(photo_result[0]))
                    if photo_result[1]:
                        paths.extend([p.strip() for p in str(photo_result[1]).split(",") if p.strip()])
                self.photo_paths = [p for p in paths if p and os.path.exists(p)]
                self.photo_labels = [""] * len(self.photo_paths)
            self.photo_path = self.photo_paths[0] if self.photo_paths else ""
            self._update_photo_button()
            self._refresh_photo_table()
            self._snapshot_photo_state()
        except Exception as e:
            logger.warning(f"Photo data preload failed: {e}")

    def validate_form(self):
        if not self.cmb_customer.currentText().strip():
            ToastManager.error(self, "Müşteri seçilmelidir.")
            return False
        if not self._selected_device_type():
            ToastManager.error(self, "Cihaz t\u00fcr\u00fc girilmelidir.")
            return False
        if (
            OTHER_DEVICE_TYPE in getattr(self, "selected_fault_notes", set())
            and not self.txt_fault.toPlainText().strip()
        ):
            ToastManager.error(
                self,
                "Di\u011fer ar\u0131za se\u00e7ildi. Ar\u0131za a\u00e7\u0131klamas\u0131n\u0131 yaz\u0131n.",
            )
            return False
        if not self.cmb_brand.currentText().strip():
            ToastManager.error(self, "Marka girilmelidir.")
            return False
        if not self._compose_fault_description().strip():
            ToastManager.error(self, "Arıza açıklaması boş bırakılamaz.")
            return False
        service_values = self._collect_sector_service_values()
        for field in self.sector_service_fields:
            if field.get("required") and not str(service_values.get(field.get("name", ""), "") or "").strip():
                ToastManager.error(self, f"{field.get('title', field.get('name'))} alanı zorunludur.")
                return False
        if self.is_automotive and not str(service_values.get("current_km", "") or "").strip():
            ToastManager.error(self, "Giriş KM alanı zorunludur.")
            return False
        return True

    def _default_approval_text(self):
        return "Yukarıdaki işlemlerin yapılmasını onaylıyorum."

    def _default_kvkk_text(self):
        return "Verileriniz servis sürecinin yürütülmesi amacıyla AYEC Pro sisteminde işlenir."

    def _update_automotive_form_summary(self):
        if not self.is_automotive or not hasattr(self, "lbl_automotive_form_summary"):
            return
        checklist_count = len((self.automotive_checklist_data or {}).get("items", []))
        damage_count = len((self.automotive_damage_data or {}).get("items", []))
        fuel = self.cmb_fuel_level_entry.currentText().strip() if hasattr(self, "cmb_fuel_level_entry") else "-"
        self.lbl_automotive_form_summary.setText(
            f"Kontrol maddesi: {checklist_count} | Hasar kaydı: {damage_count} | Yakıt: {fuel}"
        )

    def open_pattern_lock_dialog(self):
        if self.is_automotive:
            return
        dialog = self._create_pattern_lock_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pattern_lock.set_pattern_string(dialog.pattern_editor.get_pattern_string())

    def _create_pattern_lock_dialog(self):
        dialog = ModernDialog("Desen Kilidi", self, width=380, height=450)
        dialog.service_owner = self
        dialog.clear_footer()
        layout = dialog.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        title = QLabel("Desen Kilidi")
        title.setStyleSheet(theme_qss("font-size: 16px; font-weight: 800; color: @text;"))
        layout.addWidget(title)

        editor = PatternLockWidget()
        dialog.pattern_editor = editor
        if self.pattern_lock.get_pattern_string():
            editor.set_pattern_string(self.pattern_lock.get_pattern_string())
        layout.addWidget(editor, alignment=Qt.AlignmentFlag.AlignCenter)

        dialog.footer_layout.addStretch()
        dialog.btn_cancel = dialog.add_button("\u0130ptal", "secondary", dialog.reject)
        dialog.btn_save = dialog.add_button("Kaydet", "primary", dialog.accept)
        for button, token in ((dialog.btn_cancel, "@finance_surface_alt"), (dialog.btn_save, "@finance_primary")):
            button.setFixedHeight(32)
            button.setStyleSheet(theme_qss(
                "QPushButton { background: " + token + "; color: @text; border: 1px solid @finance_outline; "
                "border-radius: 4px; padding: 4px 12px; font-size: 11px; }"))
        dialog.set_footer_visible(True, 52)
        return dialog

    def open_automotive_checklist_dialog(self):
        templates = self.sector_manager.get_checklist_templates() if self.sector_manager else {}
        dlg = AutomotiveChecklistDialog(templates, self.automotive_checklist_data, self)
        if dlg.exec():
            self.automotive_checklist_data = dlg.result_data or {"items": []}
            self._update_automotive_form_summary()

    def open_automotive_damage_dialog(self):
        dlg = AutomotiveDamageDialog(self.automotive_damage_data, self)
        if dlg.exec():
            self.automotive_damage_data = dlg.result_data or {"items": [], "general_note": ""}
            self._update_automotive_form_summary()

    def _device_columns(self):
        if hasattr(self, "_device_cols_cache"):
            return self._device_cols_cache
        try:
            self._device_cols_cache = set(self.db._get_table_columns("devices")) if hasattr(self.db, "_get_table_columns") else set()
        except Exception as e:
            logger.warning(f"Device columns discovery failed: {e}")
            self._device_cols_cache = set()
        return self._device_cols_cache

    @staticmethod
    def _device_type_key(value):
        text = " ".join(str(value or "").casefold().split())
        return text.replace(" pc", "").replace(" bilgisayar", "")

    def _load_brands_for_device_type(self, device_type, preserve_current=True):
        current = self.cmb_brand.currentText().strip() if preserve_current else ""
        device_type = (device_type or "").strip()
        brand_set = set()
        try:
            catalog_rows = self.db.get_device_model_catalog(
                profiles=self._profiles_for_service_area(self._service_area),
                device_type=device_type or None,
            )
            brand_set.update(str(row[2]).strip() for row in catalog_rows if row[2])
        except Exception as exc:
            logger.debug("Catalog brand lookup failed: %s", exc)
        try:
            cur = self.db.cursor
            if device_type:
                try:
                    cur.execute(
                        "SELECT device_type, brand FROM device_brands WHERE brand IS NOT NULL AND brand != '' AND is_active=1 ORDER BY brand ASC"
                    )
                    rows = cur.fetchall() or []
                    for r in rows:
                        if len(r) >= 2 and self._device_type_key(r[0]) == self._device_type_key(device_type):
                            brand_set.add(str(r[1]))
                except Exception as e:
                    logger.debug(f"Device-type brand query failed: {e}")
                try:
                    cur.execute(
                        "SELECT DISTINCT device_brand FROM devices WHERE device_brand IS NOT NULL AND device_brand != '' AND device_type=? ORDER BY device_brand ASC",
                        (device_type,)
                    )
                    rows = cur.fetchall() or []
                    for r in rows:
                        if r[0]:
                            brand_set.add(str(r[0]))
                except Exception as e:
                    logger.debug(f"Device history brand query failed: {e}")
            if not brand_set:
                try:
                    cur.execute(
                        "SELECT DISTINCT brand FROM device_brands WHERE brand IS NOT NULL AND brand != '' AND is_active=1 ORDER BY brand ASC"
                    )
                    rows = cur.fetchall() or []
                    for r in rows:
                        if r[0]:
                            brand_set.add(str(r[0]))
                except Exception as e:
                    logger.debug(f"Global brand query failed: {e}")
                if not brand_set:
                    cur.execute(
                        "SELECT DISTINCT device_brand FROM devices WHERE device_brand IS NOT NULL AND device_brand != '' ORDER BY device_brand ASC"
                    )
                    rows = cur.fetchall() or []
                    for r in rows:
                        if r[0]:
                            brand_set.add(str(r[0]))
        except Exception as e:
            logger.warning(f"Brand loading failed: {e}")
            brand_set = set()

        brands = sorted(brand_set) if brand_set else ["Monster", "Lenovo", "ASUS", "MSI", "Dell", "HP", "Acer", "OEM"]
        self.cmb_brand.blockSignals(True)
        self.cmb_brand.clear()
        self.cmb_brand.addItems(brands)
        if current:
            self.cmb_brand.setCurrentText(current)
        else:
            reference_brand_index = self.cmb_brand.findText("Acer")
            if reference_brand_index >= 0:
                self.cmb_brand.setCurrentIndex(reference_brand_index)
        self.cmb_brand.blockSignals(False)
        self._load_models_for_device_brand(
            device_type, self.cmb_brand.currentText(), preserve_current=False
        )

    def _load_models_for_device_brand(self, device_type, brand, preserve_current=True):
        if not hasattr(self, "cmb_model"):
            return
        current = self.cmb_model.currentText().strip() if preserve_current else ""
        model_set = set()
        try:
            rows = self.db.get_device_model_catalog(
                profiles=self._profiles_for_service_area(self._service_area),
                device_type=(device_type or None),
                brand=(brand or None),
            )
            model_set.update(str(row[3]).strip() for row in rows if row[3])
        except Exception as exc:
            logger.debug("Catalog model lookup failed: %s", exc)
        self.cmb_model.blockSignals(True)
        self.cmb_model.clear()
        self.cmb_model.addItems(sorted(model_set, key=str.casefold))
        if current:
            self.cmb_model.setCurrentText(current)
        self.cmb_model.blockSignals(False)

    def _open_saved_service_form(self, tracking_no):
        try:
            host = self.window()
            if host and hasattr(host, "open_service_form"):
                host.open_service_form(tracking_no)
        except Exception as e:
            logger.warning(f"NewServiceDialog open saved service form failed for {tracking_no}: {e}")

    def save(self, open_service_form_after=False):
        if not self.validate_form():
            return

        device_cols = self._device_columns()
        core_device_columns = {
            "customer_name", "device_brand", "device_model", "serial_no", "urgency", "technician",
            "fault_description", "internal_notes", "repair_details", "pattern_lock", "accessories",
            "photo_path", "photo_paths", "device_password", "bios_password", "device_type", "warranty_status",
            "vehicle_plate", "vehicle_vin", "invoice_ready_at",
            "delivery_method", "service_location", "other_info", "price",
        }
        if len(set(device_cols) & core_device_columns) < 5:
            try:
                pragma_rows = self.db.cursor.execute("PRAGMA table_info(devices)").fetchall()
                pragma_cols = {row[1] for row in pragma_rows if len(row) > 1}
                if pragma_cols:
                    device_cols = pragma_cols
            except Exception:
                pass
        collect_descriptor_values = getattr(self, "_collect_descriptor_service_values", None)
        descriptor_values = collect_descriptor_values() if callable(collect_descriptor_values) else {}
        data = {
            "customer_name": self.cmb_customer.currentText(),
            "device_brand": self.cmb_brand.currentText(),
            "device_model": (
                self.cmb_model.currentText().strip()
                if hasattr(self, "cmb_model") and self.cmb_model.currentText().strip()
                else self.inp_model.text().strip()
            ),
            "serial_no": self.inp_serial.text(),
            "urgency": self.cmb_urgency.currentText(),
            "technician": self.cmb_personnel.currentText(),
            "fault_description": self._compose_fault_description(),
            "internal_notes": self.txt_tech_note.toPlainText(),
            "repair_details": self.txt_public_note.toPlainText(),
            "pattern_lock": self.pattern_lock.get_pattern_string(),
            "photo_path": self.photo_path if self.photo_path else "",
            "device_password": self.inp_password.text().strip(),
            "bios_password": self.inp_bios_password.text().strip() if hasattr(self, "inp_bios_password") else "",
            "device_type": (
                self._selected_device_type()
                if hasattr(self, "_selected_device_type")
                else self.cmb_device.currentText().strip()
            ),
            "status": "Bekliyor",
            "approval_status": "Bekleme"
        }
        if hasattr(self, "inp_est_price"):
            try:
                price_text = (
                    self.inp_est_price.text().strip().replace(",", ".")
                )
                if hasattr(self, "_estimate_currency"):
                    data["price"] = float(self._estimate_price_in_base())
                    if not math.isfinite(data["price"]):
                        raise ValueError("Estimate exceeds numeric storage range")
                else:
                    data["price"] = float(price_text or 0)
            except (TypeError, ValueError):
                if hasattr(self, "_estimate_currency"):
                    ToastManager.warning(self, "Tahmini tutar ge\u00e7erli, s\u0131f\u0131r veya pozitif bir say\u0131 olmal\u0131d\u0131r.")
                    return
                data["price"] = 0.0
        if hasattr(self, "dt_estimated_delivery"):
            data["estimated_date"] = (
                self.dt_estimated_delivery.date().toString("yyyy-MM-dd")
            )
        if hasattr(self, "cmb_delivery_method"):
            data["delivery_method"] = (
                self.cmb_delivery_method.currentText().strip()
            )
        if hasattr(self, "inp_service_location"):
            data["service_location"] = (
                self.inp_service_location.text().strip()
            )
        if hasattr(self, "inp_other_info"):
            data["other_info"] = self.inp_other_info.text().strip()
        for column, field in (("delivered_by_name", "inp_delivered_by"), ("delivered_by_phone", "inp_delivered_phone")):
            if column in device_cols and hasattr(self, field):
                data[column] = getattr(self, field).text().strip()
        if descriptor_values.get("estimated_date"):
            data["estimated_date"] = descriptor_values.get("estimated_date")
        if descriptor_values.get("inspection_summary"):
            data["inspection_summary"] = descriptor_values.get("inspection_summary")
        if "approval_status" in descriptor_values and str(descriptor_values.get("approval_status", "") or "").strip():
            approval_value = str(descriptor_values.get("approval_status", "") or "").strip()
            try:
                plugin = self.sector_manager.get_current_plugin() if self.sector_manager else None
                if plugin and hasattr(plugin, "approval_label_to_db"):
                    approval_value = plugin.approval_label_to_db(approval_value)
            except Exception:
                pass
            data["approval_status"] = approval_value
        if "invoice_ready_at" in device_cols and descriptor_values.get("invoice_ready"):
            data["invoice_ready_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif "invoice_ready_at" in device_cols:
            data["invoice_ready_at"] = None
        sector_service_widgets = getattr(self, "sector_service_widgets", {})
        if "warranty_status" in sector_service_widgets:
            data["warranty_status"] = sector_service_widgets["warranty_status"].currentText().strip()
        if getattr(self, "is_automotive", False):
            data["vehicle_plate"] = self.inp_vehicle_plate.text().strip().upper()
            data["vehicle_vin"] = self.inp_vehicle_vin.text().strip().upper()
        if getattr(self, "is_automotive", False) and hasattr(self, "inp_engine_code"):
            data["device_model"] = self.inp_engine_code.text()
        if "photo_paths" in device_cols:
            data["photo_paths"] = ",".join(self.photo_paths) if self.photo_paths else ""
        extension_data = {}
        sector_manager = getattr(self, "sector_manager", None)
        if sector_manager:
            extension_data = sector_manager.map_core_to_extension_payload(
                "service", self._collect_sector_service_values()
            )

        data["accessories"] = self._collect_selected_accessories()

        # Also store notes inside fault description for backward compatibility/reporting
        full_desc = data["fault_description"]
        if data["repair_details"].strip():
            full_desc += f"\n[NOT]: {data['repair_details']}"
        if data["internal_notes"].strip():
            full_desc += f"\n[TEKNİK]: {data['internal_notes']}"
        data["fault_description"] = full_desc

        if self.device_data:
            try:
                columns = [
                    "customer_name", "device_brand", "device_model", "serial_no",
                    "urgency", "technician", "fault_description", "internal_notes",
                    "repair_details", "pattern_lock", "accessories", "photo_path",
                    "device_password", "bios_password", "device_type",
                ]
                values = [
                    data["customer_name"], data["device_brand"], data["device_model"],
                    data["serial_no"], data["urgency"], data["technician"],
                    data["fault_description"], data["internal_notes"], data["repair_details"],
                    data["pattern_lock"], data["accessories"], data["photo_path"],
                    self.inp_password.text(), data.get("bios_password", ""), data["device_type"],
                ]
                for optional_column in (
                    "estimated_date",
                    "price",
                    "delivery_method",
                    "service_location",
                    "other_info",
                    "delivered_by_name",
                    "delivered_by_phone",
                ):
                    if optional_column in data:
                        columns.append(optional_column)
                        values.append(data[optional_column])
                if "warranty_status" in data:
                    columns.append("warranty_status")
                    values.append(data["warranty_status"])
                if getattr(self, "is_automotive", False):
                    columns.extend(["vehicle_plate", "vehicle_vin"])
                    values.extend([data.get("vehicle_plate", ""), data.get("vehicle_vin", "")])
                if "photo_paths" in device_cols:
                    columns.insert(12, "photo_paths")
                    values.insert(12, ",".join(self.photo_paths) if self.photo_paths else "")
                safe_pairs = [(c, v) for c, v in zip(columns, values) if c in device_cols]
                set_clause = ", ".join([f"{c}=?" for c, _ in safe_pairs])
                values = [v for _, v in safe_pairs]
                self.db.cursor.execute(
                    f"UPDATE devices SET {set_clause} WHERE id=?",
                    (*values, self.device_data[0])
                )
                self.db.conn.commit()
                if extension_data and hasattr(self.db, "upsert_sector_extension"):
                    self.db.upsert_sector_extension("service", self.device_data[0], extension_data, self._active_sector_id())
                if getattr(self, "is_automotive", False) and hasattr(self.db, "upsert_automotive_service_form"):
                    import json
                    service_values = self._collect_sector_service_values()
                    tracking_no = self.device_data[1] if len(self.device_data) > 1 else ""
                    self.db.upsert_automotive_service_form({
                        "device_id": self.device_data[0],
                        "tracking_no": tracking_no,
                        "vehicle_plate": data.get("vehicle_plate", ""),
                        "vehicle_vin": data.get("vehicle_vin", ""),
                        "engine_code": self.inp_engine_code.text().strip() if hasattr(self, "inp_engine_code") else "",
                        "entry_odometer": int(float(service_values.get("current_km", "0"))),
                        "fuel_level_entry": self.cmb_fuel_level_entry.currentText().strip() if hasattr(self, "cmb_fuel_level_entry") else "",
                        "acceptance_notes": self.txt_public_note.toPlainText().strip(),
                        "checklist_json": json.dumps((self.automotive_checklist_data or {}).get("items", []), ensure_ascii=False),
                        "damage_marks_json": json.dumps(self.automotive_damage_data or {}, ensure_ascii=False),
                        "customer_approval": 1 if self.chk_customer_approval.isChecked() else 0,
                        "kvkk_approval": 1 if self.chk_kvkk_approval.isChecked() else 0,
                        "customer_approval_text": self.txt_approval_text.toPlainText().strip() or self._default_approval_text(),
                        "kvkk_text": self.txt_kvkk_text.toPlainText().strip() or self._default_kvkk_text(),
                    })
                try:
                    tracking_no = self.device_data[1] if len(self.device_data) > 1 else ""
                    self._sync_photos_table(tracking_no)
                except Exception as e:
                    logger.warning(f"Photo sync during update failed: {e}")
                ToastManager.success(self, "Kayıt başarıyla güncellendi! ✅")
                self._refresh_customer_list_if_loaded()
                self.accept()
                if open_service_form_after and tracking_no:
                    QTimer.singleShot(0, lambda tn=tracking_no: self._open_saved_service_form(tn))
            except Exception as e:
                ToastManager.error(self, f"Hata: {e}")
        else:
            if hasattr(self.db, "get_next_service_number"):
                try:
                    data["tracking_no"] = self.db.get_next_service_number()
                except Exception as e:
                    logger.warning(f"Service number generation failed; fallback random used: {e}")
                    data["tracking_no"] = f"SRV{random.randint(100000, 999999)}"
            else:
                data["tracking_no"] = f"SRV{random.randint(100000, 999999)}"
            data["entry_date"] = datetime.now().strftime("%Y-%m-%d")
            insert_data = {
                key: value
                for key, value in data.items()
                if not device_cols or key in device_cols
            }
            selected_customer_id = self.cmb_customer.currentData()
            selected_customer_name = (
                self.cmb_customer.itemText(self.cmb_customer.currentIndex())
                if self.cmb_customer.currentIndex() >= 0 else ""
            )
            if not selected_customer_id or selected_customer_name != data["customer_name"]:
                try:
                    self.db.cursor.execute(
                        "SELECT id FROM customers WHERE TRIM(UPPER(name))=TRIM(UPPER(?)) LIMIT 1",
                        (data["customer_name"],),
                    )
                    existing_customer = self.db.cursor.fetchone()
                    selected_customer_id = existing_customer[0] if existing_customer else None
                    if not selected_customer_id:
                        selected_customer_id = self.db.add_customer({
                            "name": data["customer_name"],
                            "phone": self.inp_customer_phone.text().strip(),
                            "tc_no": self.inp_customer_identity.text().strip(),
                            "tax_id": self.inp_customer_identity.text().strip(),
                            "type": "Kurumsal" if self.inp_customer_identity.text().strip() else "Bireysel",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    if not selected_customer_id:
                        ToastManager.error(self, "M\u00fc\u015fteri kayd\u0131 olu\u015fturulamad\u0131.")
                        return
                    if "customer_id" in device_cols:
                        insert_data["customer_id"] = selected_customer_id
                except Exception as customer_error:
                    logger.exception("New service customer save failed: %s", customer_error)
                    ToastManager.error(self, "M\u00fc\u015fteri kayd\u0131 olu\u015fturulamad\u0131.")
                    return
            device_id = self.db.add_device(insert_data)
            if device_id:
                if extension_data and hasattr(self.db, "upsert_sector_extension"):
                    self.db.upsert_sector_extension("service", device_id, extension_data, self._active_sector_id())
                if getattr(self, "is_automotive", False) and hasattr(self.db, "upsert_automotive_service_form"):
                    import json
                    service_values = self._collect_sector_service_values()
                    self.db.upsert_automotive_service_form({
                        "device_id": device_id,
                        "tracking_no": data["tracking_no"],
                        "vehicle_plate": data.get("vehicle_plate", ""),
                        "vehicle_vin": data.get("vehicle_vin", ""),
                        "engine_code": self.inp_engine_code.text().strip() if hasattr(self, "inp_engine_code") else "",
                        "entry_odometer": int(float(service_values.get("current_km", "0"))),
                        "fuel_level_entry": self.cmb_fuel_level_entry.currentText().strip() if hasattr(self, "cmb_fuel_level_entry") else "",
                        "acceptance_notes": self.txt_public_note.toPlainText().strip(),
                        "checklist_json": json.dumps((self.automotive_checklist_data or {}).get("items", []), ensure_ascii=False),
                        "damage_marks_json": json.dumps(self.automotive_damage_data or {}, ensure_ascii=False),
                        "customer_approval": 1 if self.chk_customer_approval.isChecked() else 0,
                        "kvkk_approval": 1 if self.chk_kvkk_approval.isChecked() else 0,
                        "customer_approval_text": self.txt_approval_text.toPlainText().strip() or self._default_approval_text(),
                        "kvkk_text": self.txt_kvkk_text.toPlainText().strip() or self._default_kvkk_text(),
                    })
                self._sync_photos_table(data["tracking_no"])

                # Müşteriye yeni servis kayıt maili gönder
                try:
                    from src.utils.email_manager import EmailManager
                    em = EmailManager(self.db)
                    cust_name = data.get("customer_name", "")
                    cust_id = self.cmb_customer.currentData()
                    cust_email = ""
                    if cust_id:
                        cust = self.db.get_customer(cust_id)
                        if cust:
                            cust_email = cust.get("email", "")
                    if not cust_email and hasattr(self.db, "get_customer_by_name"):
                        cust = self.db.get_customer_by_name(cust_name)
                        if cust:
                            cust_email = cust.get("email", "")
                    if cust_email:
                        dev_label = f"{data.get('device_brand', '')} {data.get('device_model', '')}".strip() or data.get('device_type', 'Cihaz')
                        em.send_new_service_email(
                            to_email=cust_email,
                            customer_name=cust_name,
                            tracking_no=data["tracking_no"],
                            device_name=dev_label
                        )
                except Exception as mail_err:
                    logger.warning("New service email sending failed: %s", mail_err)

                self._refresh_customer_list_if_loaded()
                self.accept()
                if open_service_form_after:
                    QTimer.singleShot(0, lambda tn=data["tracking_no"]: self._open_saved_service_form(tn))
            else:
                ToastManager.error(self, "Kayıt eklenemedi.")



    def _wire_ui_signals(self):
        self.cmb_customer.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_device.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_brand.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_urgency.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_personnel.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_service_profile.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_fuel_level_entry.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.chk_customer_approval.stateChanged.connect(self._on_ui_widget_changed)
        self.chk_kvkk_approval.stateChanged.connect(self._on_ui_widget_changed)
