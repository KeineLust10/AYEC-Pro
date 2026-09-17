
# -*- coding: utf-8 -*-

import random
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTextEdit, QCompleter, QCheckBox,
    QApplication, QWidget, QFrame, QGridLayout, QTableWidget, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QDateEdit

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

from ._new_service_dialog_widgets_mixin import NewServiceDialogWidgetsMixin
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
        if not self.is_automotive:
            raise RuntimeError("NewServiceDialog is reserved for the automotive sector")
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
        
        mode_title = "Servis Kaydı Düzenle" if device_data else "Yeni Servis Kaydı Oluştur"

        screen = QApplication.primaryScreen().geometry()
        width = min(int(screen.width() * 0.985), 1720)
        height = min(int(screen.height() * 0.95), 1020)
        super().__init__(mode_title, parent, width=width, height=height)
        self.setup_content()
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
        new_w = min(int(screen.width() * 0.985), 1720)
        new_h = min(int(screen.height() * 0.95), 1020)
        self.set_dialog_size(new_w, new_h)
        self.setMinimumSize(1380, 800)

        self.set_footer_visible(True, 62)
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
        root_layout.setContentsMargins(16, 10, 16, 8)
        root_layout.setSpacing(10)

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

        root_layout.addWidget(self.create_form_intro(intro_title, intro_text))
        root_layout.addWidget(self.create_workflow_strip(workflow_steps, active_index=0))

        columns_widget = QWidget()
        columns_widget.setStyleSheet("background: transparent; border: none;")
        main_lay = QHBoxLayout(columns_widget)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(16)

        # Left column
        left_col = QVBoxLayout()
        left_col.setSpacing(0)

        # 1. Customer
        left_col.addWidget(self._sec("MÜŞTERİ"))
        left_col.addSpacing(4)
        cust_row = QHBoxLayout()
        cust_row.setSpacing(8)
        self.cmb_customer = ModernComboBox()
        self.cmb_customer.setMinimumHeight(36)
        btn_add_cust = QPushButton("+ Yeni")
        btn_add_cust.setFixedSize(76, 36)
        btn_add_cust.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_cust.setStyleSheet(theme_qss(
            "background-color: @selection_bg; color: @selection_text; border: 1px solid @border; border-radius: 8px; font-weight: bold;"
        ))
        btn_add_cust.clicked.connect(self.quick_add_customer)
        cust_row.addWidget(self.cmb_customer, 1)
        cust_row.addWidget(btn_add_cust)
        left_col.addLayout(cust_row)
        left_col.addSpacing(12)

        # 2. Device
        left_col.addWidget(self._sec("CİHAZ BİLGİLERİ"))
        left_col.addSpacing(4)
        dev_grid = QGridLayout()
        dev_grid.setSpacing(8)
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
        self.cmb_device.setMinimumHeight(36)
        dev_grid.addLayout(self.create_field_box("Cihaz Türü", self.cmb_device), 0, 0)
        self.cmb_brand = ModernComboBox()
        self.cmb_brand.setEditable(True)
        self.cmb_brand.setMinimumHeight(36)
        self._load_brands_for_device_type(self.cmb_device.currentText(), preserve_current=False)
        self.cmb_device.currentTextChanged.connect(self._on_device_type_changed)
        dev_grid.addLayout(self.create_field_box("Marka", self.cmb_brand), 0, 1)
        self.inp_model = ValidatedLineEdit("Örn: Nitro 5 / ThinkPad E14 / RTX Sistem")
        self.cmb_model = ModernComboBox()
        self.cmb_model.setEditable(True)
        self.cmb_model.setMinimumHeight(36)
        self.cmb_model.setPlaceholderText("Model secin veya yazin")
        self.cmb_brand.currentTextChanged.connect(self._on_brand_changed)
        self._load_models_for_device_brand(
            self.cmb_device.currentText(), self.cmb_brand.currentText(), preserve_current=False
        )
        dev_grid.addLayout(self.create_field_box("Model", self.cmb_model), 1, 0)
        self.inp_serial = ValidatedLineEdit("Seri No / Servis Etiketi")
        self.inp_serial.setMinimumHeight(36)
        dev_grid.addLayout(self.create_field_box("Seri No", self.inp_serial), 1, 1)
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

        # Keep the compact customer and device fields on the left. The service
        # workflow continues in the right column so both sides use the space.
        primary_col = left_col
        primary_col.addStretch(1)
        primary_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        right_col = QVBoxLayout()
        right_col.setSpacing(0)
        left_col = right_col

        # 3. Service details
        left_col.addWidget(self._sec("SERVİS DETAYLARI"))
        left_col.addSpacing(4)
        servis_grid = QGridLayout()
        servis_grid.setSpacing(8)
        self.inp_password = ValidatedLineEdit("Ekran Şifresi")
        self.inp_password.setPlaceholderText("Ekran Şifresi")
        self.inp_password.setMinimumHeight(36)
        servis_grid.addLayout(self.create_field_box("Ekran Şifresi", self.inp_password), 0, 0)
        self.cmb_urgency = ModernComboBox(items=["Düşük", "Normal", "Yüksek", "🔥 ACİL"])
        self.cmb_urgency.setCurrentText("Normal")
        self.cmb_urgency.setMinimumHeight(36)
        servis_grid.addLayout(self.create_field_box("Aciliyet", self.cmb_urgency), 0, 1)
        self.cmb_personnel = ModernComboBox()
        self.cmb_personnel.setMinimumHeight(36)
        servis_grid.addLayout(self.create_field_box("Teknisyen", self.cmb_personnel), 1, 0)
        self.inp_est_price = ValidatedLineEdit("0.00")
        self.inp_est_price.setPlaceholderText("Tahmini Tutar")
        self.inp_est_price.setMinimumHeight(36)
        self.inp_est_price.setStyleSheet(theme_qss(
            "font-size: 13px; font-weight: bold; color: @success; padding: 6px 8px;"
        ))
        servis_grid.addLayout(self.create_field_box("💰 Tahmini Tutar", self.inp_est_price), 1, 1)
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
        left_col.addLayout(servis_grid)
        left_col.addSpacing(12)

        # 4. Fault description (fills remaining space)
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
        self.txt_fault.setFixedHeight(72)
        self.txt_fault.setStyleSheet(theme_qss(
            "border: 1px solid @border; border-radius: 6px; padding: 6px 8px; font-size: 11px; background: @surface;"
        ))
        self.txt_fault.textChanged.connect(self._on_fault_manual_changed)
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

        main_lay.addLayout(primary_col, 50)

        # Vertical separator
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
        right_col.addWidget(self._sec("KİLİT DESENİ & FOTOĞRAF"))
        right_col.addSpacing(4)
        kilit_row = QHBoxLayout()
        kilit_row.setSpacing(12)
        self.pattern_lock = PatternLockWidget()
        self.pattern_lock.setFixedSize(220, 220)
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
            self.btn_pattern_lock = QPushButton("Desen Kilidi")
            self.btn_pattern_lock.setFixedHeight(32)
            self.btn_pattern_lock.setFixedWidth(136)
            self.btn_pattern_lock.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_pattern_lock.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary", size="sm"))
            )
            self.btn_pattern_lock.clicked.connect(self.open_pattern_lock_dialog)
            foto_col.addWidget(self.btn_pattern_lock)
        foto_col.addWidget(self.btn_photo)
        foto_col.addWidget(self.btn_photo_count)
        foto_col.addStretch()
        kilit_row.addLayout(foto_col, 0)
        kilit_row.addStretch()
        self.lbl_photo_list = QLabel()
        self.lbl_photo_list.setVisible(False)
        self.table_photos = QTableWidget()
        self.table_photos.setVisible(False)
        right_col.addLayout(kilit_row)
        right_col.addSpacing(12)
        lock_section_items = []
        while right_col.count() > lock_section_start:
            lock_section_items.append(right_col.takeAt(lock_section_start))

        # 2. Notes
        right_col.addWidget(self._sec("NOTLAR"))
        right_col.addSpacing(4)
        self.txt_public_note = QTextEdit()
        self.txt_public_note.setPlaceholderText("Müşteri fişi notu...")
        self.txt_public_note.setFixedHeight(46)
        right_col.addLayout(self.create_field_box("Genel Not (Müşteri)", self.txt_public_note))
        right_col.addSpacing(6)
        self.txt_tech_note = QTextEdit()
        self.txt_tech_note.setPlaceholderText("Gizli teknik not...")
        self.txt_tech_note.setFixedHeight(46)
        right_col.addLayout(self.create_field_box("Teknik Not (Gizli)", self.txt_tech_note))
        right_col.addSpacing(12)

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
        right_col.addWidget(self._sec("TESLİM ALINAN AKSESUARLAR"))
        right_col.addSpacing(4)
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
                cl = QVBoxLayout(acc_card)
                cl.setContentsMargins(8, 5, 8, 5)
                cl.setSpacing(3)
                lbl = QLabel(name)
                lbl.setStyleSheet(theme_qss(
                    "font-size: 10px; font-weight: 800; color: @text; border: none;"
                ))
                tgl = AnimatedToggle()
                tgl.setFixedSize(36, 16)
                tgl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.mousePressEvent = lambda event, t=tgl: t.toggle()
                wrap = QHBoxLayout()
                wrap.addStretch()
                wrap.addWidget(tgl)
                wrap.addStretch()
                cl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
                cl.addLayout(wrap)
                self.acc_grid.addWidget(acc_card, r, c)
                self.accessory_checkboxes[name] = tgl
                tgl.toggled.connect(self._handle_accessory_toggle_changed)
                c += 1
                if c >= 3:
                    c = 0
                    r += 1
        except Exception as e:
            logger.warning(f"NewServiceDialog accessory card build failed: {e}")
        right_col.addLayout(self.acc_grid)

        right_col.addStretch(1)
        for item in lock_section_items:
            if item.widget() is not None:
                right_col.addWidget(item.widget())
            elif item.layout() is not None:
                right_col.addLayout(item.layout())
            elif item.spacerItem() is not None:
                right_col.addItem(item)

        main_lay.addLayout(right_col, 50)
        root_layout.addWidget(columns_widget, 1)
        self.scroll_area.setWidget(main_widget)
        self._apply_wheel_bridge_recursive(main_widget)

        # Footer

        self.footer_layout.setContentsMargins(20, 0, 20, 0)
        self.footer_layout.setSpacing(12)
        btn_cancel = QPushButton("İptal")
        btn_cancel.setFixedSize(100, 40)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss(
            "background: @surface_alt; color: @text_muted; border: 1px solid @border; border-radius: 8px; font-weight: bold;"
        ))
        btn_cancel.clicked.connect(self.reject)
        self.btn_save_and_form = QPushButton("🖨️ Kaydet ve Servis Formu Aç")
        self.btn_save_and_form.setFixedHeight(40)
        self.btn_save_and_form.setMinimumWidth(220)
        self.btn_save_and_form.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_and_form.setStyleSheet(theme_qss(
            "background-color: @accent; color: @selection_text; border-radius: 8px; font-weight: bold; border: none; font-size: 13px;"
        ))
        self.btn_save_and_form.clicked.connect(lambda: self.save(open_service_form_after=True))
        action_text = "✅ Kaydı Güncelle" if self.device_data else "✅ Servis Kaydı Oluştur"
        self.btn_action = QPushButton(action_text)
        self.btn_action.setFixedHeight(40)
        self.btn_action.setMinimumWidth(200)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setStyleSheet(theme_qss(
            "background-color: @success; color: @selection_text; border-radius: 8px; font-weight: bold; border: none; font-size: 13px;"
        ))
        self.btn_action.clicked.connect(self.save)
        self.footer_layout.addWidget(btn_cancel)
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
        for c in self.db.get_customers():
            self.cmb_customer.addItem(c[1], c[0])

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

    def _on_fault_manual_changed(self):
        if not hasattr(self, "selected_fault_notes"):
            return
        self._update_fault_selected_label()

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
                "SELECT tracking_no, customer_name, device_brand, device_model, "
                "serial_no, fault_description, urgency, technician, "
                "internal_notes, repair_details, accessories, pattern_lock, "
                "device_type, vehicle_plate, vehicle_vin "
                "FROM devices WHERE tracking_no=?",
                (tracking_no,)
            )
            row = self.db.cursor.fetchone()
            full_data = dict(row) if row and hasattr(row, "keys") else row

        if not full_data:
            return

        # Set fields
        getter = (lambda key, idx: full_data.get(key)) if isinstance(full_data, dict) else (lambda key, idx: full_data[idx])
        self.cmb_customer.setCurrentText(str(getter("customer_name", 1) or ""))
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
        dialog = ModernDialog("Desen Kilidi", self, width=380, height=450)
        dialog.set_footer_visible(False)
        layout = dialog.content_layout
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        title = QLabel("Desen Kilidi")
        title.setStyleSheet(theme_qss("font-size: 16px; font-weight: 800; color: @text;"))
        layout.addWidget(title)

        editor = PatternLockWidget()
        if self.pattern_lock.get_pattern_string():
            editor.set_pattern_string(self.pattern_lock.get_pattern_string())
        layout.addWidget(editor, alignment=Qt.AlignmentFlag.AlignCenter)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_button = QPushButton("Iptal")
        cancel_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        cancel_button.clicked.connect(dialog.reject)
        save_button = QPushButton("Kaydet")
        save_button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        save_button.clicked.connect(dialog.accept)
        actions.addWidget(cancel_button)
        actions.addWidget(save_button)
        layout.addLayout(actions)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.pattern_lock.set_pattern_string(editor.get_pattern_string())

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
            "photo_path", "photo_paths", "device_password", "device_type", "warranty_status",
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
            "device_model": self.cmb_model.currentText(),
            "serial_no": self.inp_serial.text(),
            "urgency": self.cmb_urgency.currentText(),
            "technician": self.cmb_personnel.currentText(),
            "fault_description": self._compose_fault_description(),
            "internal_notes": self.txt_tech_note.toPlainText(),
            "repair_details": self.txt_public_note.toPlainText(),
            "pattern_lock": self.pattern_lock.get_pattern_string(),
            "photo_path": self.photo_path if self.photo_path else "",
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
                data["price"] = float(price_text or 0)
            except (TypeError, ValueError):
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
                    "device_password", "device_type",
                ]
                values = [
                    data["customer_name"], data["device_brand"], data["device_model"],
                    data["serial_no"], data["urgency"], data["technician"],
                    data["fault_description"], data["internal_notes"], data["repair_details"],
                    data["pattern_lock"], data["accessories"], data["photo_path"],
                    self.inp_password.text(), data["device_type"],
                ]
                for optional_column in (
                    "estimated_date",
                    "price",
                    "delivery_method",
                    "service_location",
                    "other_info",
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
