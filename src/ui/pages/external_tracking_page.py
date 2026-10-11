# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QDialog, QFormLayout, QLineEdit, QDateEdit, QTextEdit, 
                             QFrame, QMessageBox, QGraphicsDropShadowEffect, QComboBox, QMenu,
                             QGridLayout, QFileDialog, QSizePolicy)
from src.utils.theme_colors import theme_qss, tc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from PyQt6.QtGui import QFont, QColor, QPixmap
from datetime import datetime
import os
import unicodedata
import html

from src.utils.toast_notification import show_success, show_error, show_info
from src.utils.date_utils import format_turkish_date

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon
from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.utils.context_menu_settings import is_context_menu_enabled


def _normalize_external_status(value):
    text = str(value or "").casefold().replace("\u0131", "i")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


class ExternalTrackingDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, data=None):
        self.db = db
        self.data = data
        super().__init__("Lojistik & Garanti Takip Ekle", parent, width=1000, height=850)
        self.setup_content()
        if data:
            self.load_data()
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.inp_customer.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def setup_content(self):
        # Header text and icon are handled by ModernDialog, 
        # but we can customize if needed. We'll use the default ModernDialog structure.
        
        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QVBoxLayout(content)
        form_layout.setContentsMargins(30, 20, 30, 20)
        form_layout.setSpacing(20)
        
        # Input Background Frame
        main_frame = QFrame()
        main_frame.setObjectName("ExternalTrackingForm")
        main_frame.setStyleSheet(theme_qss("""
            QFrame#ExternalTrackingForm {
                background: @surface_alt; border-radius: 15px; border: 1px solid @border;
            }
            QFrame#ExternalTrackingForm QLabel {
                background: transparent; border: none; color: @text_muted;
                font-size: 13px; font-weight: 700;
            }
        """))
        main_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_frame.setMinimumHeight(520)
        grid = QGridLayout(main_frame)
        grid.setContentsMargins(25, 25, 25, 25)
        grid.setSpacing(15)
        
        # Helper to add field
        def add_form_field(label_text, widget, row, col=0, colspan=1):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(theme_qss("background: transparent; color: @text_muted; font-size: 13px; font-weight: 700; border: none;"))
            vbox = QVBoxLayout()
            vbox.setSpacing(5)
            vbox.addWidget(lbl)
            vbox.addWidget(widget)
            grid.addLayout(vbox, row, col, 1, colspan)

        # Emanet No
        self.inp_internal_no = ValidatedLineEdit("Örn: M.NO 1025 / Cihaz Takip No")
        add_form_field("Müşteri Emanet No:", self.inp_internal_no, 0, 0, 2)
        
        # Müşteri (Editable ComboBox with Customer List)
        self.inp_customer = QComboBox()
        self.inp_customer.setEditable(True)
        self.inp_customer.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.inp_customer.setPlaceholderText("Müşteri seçin veya yazın...")
        self.inp_customer.setMinimumHeight(45)
        self.inp_customer.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self._load_customers()  # Load from database
        add_form_field("Müşteri Bilgisi:", self.inp_customer, 1, 0)
        
        # Ürün
        self.inp_product = ValidatedLineEdit("Marka / Model / Parça Adı")
        add_form_field("Ürün / Parça:", self.inp_product, 1, 1)
        
        # Servis
        self.inp_service = ValidatedLineEdit("Asus Servis, Penta, vb.")
        add_form_field("Gönderilen Yer:", self.inp_service, 2, 0)
        
        # Servis No
        self.inp_service_no = ValidatedLineEdit("Karşı tarafın verdiği servis no")
        add_form_field("Servis Kayıt No:", self.inp_service_no, 2, 1)
        
        # Tarih
        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        self.inp_date.setFixedHeight(45)
        self.inp_date.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        add_form_field("Gönderim Tarihi:", self.inp_date, 3, 0)
        
        # Durum
        self.cmb_status = ModernComboBox(items=["Hazırlanıyor", "Kargoya Verildi", "Servise Ulaştı", "Onarımda", "İade Bekleniyor", "Geri Geldi", "Müşteriye Teslim Edildi"])
        add_form_field("Güncel Durum:", self.cmb_status, 3, 1)
        
        # Kargo Group
        kargo_box = QFrame()
        kargo_box.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px solid @border;"))
        k_lay = QHBoxLayout(kargo_box)
        k_lay.setContentsMargins(15, 15, 15, 15)
        k_lay.setSpacing(15)
        
        self.inp_out_cargo = ValidatedLineEdit("Gidiş Kargo Takip No")
        self.inp_in_cargo = ValidatedLineEdit("Dönüş Kargo Takip No")
        
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("↗ Gidiş Kargo No:"))
        v1.addWidget(self.inp_out_cargo)
        
        v2 = QVBoxLayout()
        v2.addWidget(QLabel("↙ Dönüş Kargo No:"))
        v2.addWidget(self.inp_in_cargo)
        
        k_lay.addLayout(v1)
        k_lay.addLayout(v2)
        
        grid.addWidget(kargo_box, 4, 0, 1, 2)

        photos_box = QFrame()
        photos_box.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px dashed @border;"))
        photos_layout = QHBoxLayout(photos_box)
        photos_layout.setContentsMargins(15, 15, 15, 15)
        photos_layout.setSpacing(15)

        self.photo_preview = QLabel("Önizleme")
        self.photo_preview.setFixedSize(180, 135)
        self.photo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.photo_preview.setStyleSheet(theme_qss("""
            QLabel {
                background: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 700;
            }
        """))
        photos_layout.addWidget(self.photo_preview)

        lbl_photos = QLabel("📸 Garanti sürecine ait fotoğraflar")
        lbl_photos.setStyleSheet(theme_qss("background: transparent; color: @text; font-size: 13px; font-weight: 700; border: none;"))
        photos_layout.addWidget(lbl_photos)
        photos_layout.addStretch()

        self.btn_photos = QPushButton("➕ Fotoğraf Ekle / Galeri")
        self.btn_photos.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_photos.setFixedHeight(40)
        self.btn_photos.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        self.btn_photos.clicked.connect(self.open_photo_gallery)
        photos_layout.addWidget(self.btn_photos)

        grid.addWidget(photos_box, 5, 0, 1, 2)
        
        form_layout.addWidget(main_frame, 1)
        form_layout.setStretch(0, 1)
        self.add_widget(content)
        
        # Footer
        self.add_cancel_button("Vazgeç")
        self.add_button("💾 KAYDI TAMAMLA", "primary", self.save)
        self._update_photo_preview()
    
    def _load_customers(self):
        """Load customers into combobox"""
        try:
            customers = self.db.get_customers()
            self.inp_customer.clear()
            self.inp_customer.addItem("")
            for c in customers:
                if isinstance(c, dict):
                    name = c.get('name', '')
                else:
                    name = c[1] if len(c) > 1 else ''
                if name:
                    self.inp_customer.addItem(str(name))
        except Exception as e:
            logger.error(f"ExternalTrackingDialog customer load error: {e}")

    def load_data(self):
        d = self.data
        # d indexes: id=0, internal=1, cust=2, prod=3, serv=4, serv_no=5, date=6, out_cargo=7, in_cargo=8, status=9, notes=10
        self.inp_internal_no.setText(str(d[1] or ""))
        # Set ComboBox current text (editable)
        self.inp_customer.setCurrentText(str(d[2] or ""))
        self.inp_product.setText(str(d[3] or ""))
        self.inp_service.setText(str(d[4] or ""))
        self.inp_service_no.setText(str(d[5] or ""))
        if d[6]: self.inp_date.setDate(QDate.fromString(d[6], "yyyy-MM-dd"))
        self.inp_out_cargo.setText(str(d[7] or ""))
        self.inp_in_cargo.setText(str(d[8] or ""))
        self.cmb_status.setCurrentText(str(d[9] or "Hazırlanıyor"))
        self._update_photo_preview()

    def save(self):
        new_data = {
            'internal_no': self.inp_internal_no.text(),
            'customer': self.inp_customer.currentText(),
            'product': self.inp_product.text(),
            'service': self.inp_service.text(),
            'service_no': self.inp_service_no.text(),
            'date': self.inp_date.date().toString("yyyy-MM-dd"),
            'out_cargo': self.inp_out_cargo.text(),
            'in_cargo': self.inp_in_cargo.text(),
            'status': self.cmb_status.currentText(),
            'notes': ""
        }
        try:
            if self.data:
                self.db.update_external_tracking(self.data[0], new_data)
                show_success(self, "Kayıt başarıyla güncellendi.")
            else:
                self.db.add_external_tracking(new_data)
                show_success(self, "Yeni dış servis kaydı oluşturuldu.")
            self.accept()
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def open_photo_gallery(self):
        tracking_no = self.inp_internal_no.text().strip()
        if not tracking_no:
            show_info(self, "Lütfen önce Müşteri Emanet No alanını doldurun.")
            return
        try:
            from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
            dlg = PhotoGalleryDialog(self.db, tracking_no, self, read_only=False, stage="İşlem")
            dlg.exec()
            self._update_photo_preview()
        except Exception as e:
            show_error(self, f"Fotoğraf galerisi açılamadı: {e}")

    def _update_photo_preview(self):
        if not hasattr(self, "photo_preview"):
            return
        tracking_no = self.inp_internal_no.text().strip()
        if not tracking_no:
            self.photo_preview.setText("Önizleme")
            self.photo_preview.setPixmap(QPixmap())
            return
        photo_path = ""
        try:
            rows = self.db.get_photos(tracking_no, "İşlem") or []
            if not rows:
                rows = self.db.get_photos(tracking_no) or []
            for r in rows:
                p = r[1]
                if p and os.path.exists(p):
                    photo_path = p
                    break
        except Exception:
            photo_path = ""
        if photo_path and os.path.exists(photo_path):
            target = self.photo_preview.size()
            pix = QPixmap(photo_path).scaled(target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.photo_preview.setPixmap(pix)
            self.photo_preview.setText("")
        else:
            self.photo_preview.setText("Önizleme")
            self.photo_preview.setPixmap(QPixmap())

class ExternalTrackingPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.records = []
        self.current_page = 0
        self.page_size = 4
        self.setup_ui()
        self.refresh_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setObjectName("ExternalTrackingPage")
        self.setStyleSheet(theme_qss("QWidget#ExternalTrackingPage { background-color: @background; }"))

        # Modern Header with Gradient
        self.header_frame = QFrame()
        self.header_frame.setObjectName("ExternalTrackingHeader")
        self.header_frame.setFixedHeight(106)
        self.header_frame.setStyleSheet(theme_qss("""
            QFrame#ExternalTrackingHeader {
                background: @finance_surface;
                border-bottom: 1px solid @finance_outline;
            }
        """))
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(24, 12, 24, 12)
        
        # Left side - Title & Description
        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(8)
        
        # Icon + Title
        title_row = QHBoxLayout()
        icon_lbl = LoanerMetricIcon("truck", "finance_primary")
        icon_lbl.setFixedSize(42, 42)
        title_row.addWidget(icon_lbl)
        
        lbl_title = QLabel("Lojistik & Garanti Y\u00f6netimi")
        title_font = QFont(self.font())
        title_font.setPointSize(18)
        title_font.setWeight(QFont.Weight.Bold)
        lbl_title.setFont(title_font)
        lbl_title.setStyleSheet(theme_qss("color: @finance_text; background: transparent; border: none;"))
        title_row.addWidget(lbl_title)
        sla_badge = QLabel("V2.5 SLA SYNC")
        sla_badge.setStyleSheet(theme_qss(
            "color: @accent; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 5px; padding: 4px 7px; font-size: 10px; font-weight: 800;"
        ))
        title_row.addWidget(sla_badge)
        title_row.addStretch()
        title_vbox.addLayout(title_row)
        
        lbl_sub = QLabel("Anla\u015fmal\u0131 servisler ve garanti s\u00fcre\u00e7lerinin merkezi takip sistemi")
        subtitle_font = QFont(DesignTokens.FONT_NAME)
        subtitle_font.setPixelSize(13)
        lbl_sub.setFont(subtitle_font)
        lbl_sub.setWordWrap(True)
        lbl_sub.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lbl_sub.setStyleSheet(theme_qss("color: @finance_text_muted; background: transparent; border: none; margin-left: 55px;"))
        title_vbox.addWidget(lbl_sub)
        self.lbl_title = lbl_title
        self.lbl_sub = lbl_sub
        
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()

        header_commands = QVBoxLayout()
        header_commands.setSpacing(6)
        primary_commands = QHBoxLayout()
        primary_commands.setSpacing(6)
        self.cargo_sync_button = QPushButton("Kargo API Sync")
        self.cargo_sync_button.setEnabled(False)
        self.cargo_sync_button.setToolTip("Kargo saglayici API baglantisi bu modulde henuz mevcut degil.")
        manifest = QPushButton("Toplu Kargo Fi\u015fi")
        manifest.clicked.connect(self.print_cargo_manifest)
        report = QPushButton("Excel / Rapor")
        report.clicked.connect(self.export_to_csv)
        for command in (self.cargo_sync_button, manifest, report):
            command.setMinimumHeight(30)
            command.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
            primary_commands.addWidget(command)
        header_commands.addLayout(primary_commands)
        excel_layout = QHBoxLayout()
        excel_layout.setSpacing(6)
        
        def _hbtn(icon, tooltip):
            b = QPushButton(icon)
            b.setFixedSize(74, 32)
            b.setToolTip(tooltip)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(
                theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton { padding: 0; min-height: 26px; font-size: 10px; }")
            )
            return b

        btn_import = _hbtn("\u0130\u00e7e Aktar", "Excel \u0130\u00e7e Aktar")
        btn_import.clicked.connect(self.import_from_csv)
        excel_layout.addWidget(btn_import)

        btn_docs = _hbtn("Belgeler", "Belge Merkezi")
        btn_docs.clicked.connect(self.open_documents_center)
        excel_layout.addWidget(btn_docs)

        self.btn_multi = _hbtn("\u00c7oklu Se\u00e7im", "\u00c7oklu Se\u00e7im")
        self.btn_multi.setCheckable(True)
        self.btn_multi.clicked.connect(self.toggle_multiselect)
        excel_layout.addWidget(self.btn_multi)

        btn_add = QPushButton("+ Yeni Takip Ba\u015flat")
        btn_add.setFixedSize(180, 36)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="sm")))
        
        btn_add.clicked.connect(self.add_record)
        excel_layout.insertWidget(0, btn_add)
        header_commands.addLayout(excel_layout)
        header_layout.addLayout(header_commands)
        
        layout.addWidget(self.header_frame)

        # Content Area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Statistics Cards Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        # We'll populate these after loading data
        self.stats_layout = stats_layout
        content_layout.addLayout(stats_layout)

        filter_bar = QFrame()
        filter_bar.setObjectName("ExternalTrackingFilters")
        filter_bar.setStyleSheet(theme_qss(
            "QFrame#ExternalTrackingFilters { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"
        ))
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Kargo takip no, emanet no, m\u00fc\u015fteri veya yetkili servis ara...")
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet(theme_qss(
            "QLineEdit { background: @finance_surface_alt; border: 1px solid @finance_outline; border-radius: 6px; padding: 0 10px; color: @finance_text; }"
        ))
        self.search.textChanged.connect(self._filters_changed)
        filter_layout.addWidget(self.search, 1)
        self.status_filter = ModernComboBox()
        self.status_filter.addItem("Durum: T\u00fcm\u00fc", "")
        self.service_filter = ModernComboBox()
        self.service_filter.addItem("Yetkili Servis: T\u00fcm\u00fc", "")
        self.month_filter = ModernComboBox()
        self.month_filter.addItem("T\u00fcm Aylar", "")
        for control in (self.status_filter, self.service_filter, self.month_filter):
            control.setMinimumHeight(38)
            control.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
            control.set_reference_chevron()
            filter_layout.addWidget(control)
        self.status_filter.currentIndexChanged.connect(self._filters_changed)
        self.service_filter.currentIndexChanged.connect(self._filters_changed)
        self.month_filter.currentIndexChanged.connect(self._filters_changed)
        content_layout.addWidget(filter_bar)

        # Table Container
        table_frame = QFrame()
        table_frame.setObjectName("ExternalTrackingTableFrame")
        table_frame.setStyleSheet(theme_qss("QFrame#ExternalTrackingTableFrame { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }"))
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Takip No /\nServis No", "M\u00fc\u015fteri & \u00dcr\u00fcn", "D\u0131\u015f Servis / Yer",
            "G\u00f6nderim\nTarihi", "Kargo Takip", "Durum", "\u0130\u015flemler",
            "Garanti\nKapsam\u0131", "Maliyet /\nTutar"
        ])
        
        # Modern Table Style
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        header_view = self.table.horizontalHeader()
        header_view.setHighlightSections(False)
        
        # Column width adjustments
        header_view.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 130)  # Tracking and external service references
        self.table.setColumnWidth(1, 230)  # Müşteri & Ürün
        self.table.setColumnWidth(2, 140)  # External service and location
        self.table.setColumnWidth(3, 110)  # Gidiş Tarihi
        self.table.setColumnWidth(4, 174)  # Cargo tracking
        self.table.setColumnWidth(5, 120)  # Status
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 150)
        self.table.setColumnWidth(7, 124)
        self.table.setColumnWidth(8, 110)
        header_view.moveSection(header_view.visualIndex(7), 5)
        header_view.moveSection(header_view.visualIndex(8), 6)
        header_view.moveSection(header_view.visualIndex(6), 8)

        self.table.verticalHeader().setDefaultSectionSize(70)  # Satır yüksekliği azaltıldı
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.setAlternatingRowColors(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_context_menu)
        self.table.cellDoubleClicked.connect(self.open_selected_record)
        
        table_layout.addWidget(self.table)
        content_layout.addWidget(table_frame)
        self.sync_footer = QLabel()
        self.sync_footer.setStyleSheet(theme_qss("color: @text_muted; padding: 8px 2px; font-size: 10px; font-weight: 700;"))
        footer_layout = QHBoxLayout()
        footer_layout.addWidget(self.sync_footer, 1)
        self.page_label = QLabel("1 / 1")
        self.page_label.setMinimumWidth(52)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
        self.previous_page = QPushButton("<")
        self.next_page = QPushButton(">")
        for button in (self.previous_page, self.next_page):
            button.setFixedSize(34, 30)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton { padding: 0; min-height: 24px; }"))
        self.previous_page.clicked.connect(lambda: self._change_page(-1))
        self.next_page.clicked.connect(lambda: self._change_page(1))
        footer_layout.addWidget(self.previous_page)
        footer_layout.addWidget(self.page_label)
        footer_layout.addWidget(self.next_page)
        content_layout.addLayout(footer_layout)
        content_layout.addStretch(1)
        
        layout.addWidget(content)
        self.apply_theme_styles()


    def apply_theme_styles(self):
        if hasattr(self, "lbl_title"):
            self.lbl_title.setText("Lojistik & Garanti Yönetimi")
            self.lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setText("Anlaşmalı servisler ve garanti süreçlerinin merkezi takip sistemi")
            self.lbl_sub.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none; margin-left: 55px;"))

    def refresh_theme(self):
        self.apply_theme_styles()

    def _update_filter_options(self, records):
        filters = (
            (self.status_filter, "Durum: T\u00fcm\u00fc", 9),
            (self.service_filter, "Yetkili Servis: T\u00fcm\u00fc", 4),
        )
        for combo, default_label, column in filters:
            previous = combo.currentData()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(default_label, "")
            for value in sorted({str(row[column] or "").strip() for row in records if row[column]}):
                combo.addItem(value, value)
            selected = combo.findData(previous)
            combo.setCurrentIndex(selected if selected >= 0 else 0)
            combo.blockSignals(False)

        previous_month = self.month_filter.currentData()
        self.month_filter.blockSignals(True)
        self.month_filter.clear()
        self.month_filter.addItem("T\u00fcm Aylar", "")
        months = sorted({str(row[6] or "")[:7] for row in records if row[6]}, reverse=True)
        for month in months:
            self.month_filter.addItem(month, month)
        selected_month = self.month_filter.findData(previous_month)
        self.month_filter.setCurrentIndex(selected_month if selected_month >= 0 else 0)
        self.month_filter.blockSignals(False)

    def _filters_changed(self, *_args):
        self.current_page = 0
        self._apply_filters()

    def _change_page(self, delta):
        self.current_page += delta
        self._apply_filters()

    def _apply_filters(self, *_args):
        query = self.search.text().strip().casefold()
        status = self.status_filter.currentData()
        service = self.service_filter.currentData()
        month = self.month_filter.currentData()
        matching_rows = []
        for row_index, record in enumerate(self.records):
            matches = (
                (not query or query in " ".join(str(value or "") for value in record).casefold())
                and (not status or str(record[9] or "") == status)
                and (not service or str(record[4] or "") == service)
                and (not month or str(record[6] or "").startswith(month))
            )
            if matches:
                matching_rows.append(row_index)
        total_pages = max(1, (len(matching_rows) + self.page_size - 1) // self.page_size)
        self._matching_rows = list(matching_rows)
        self.current_page = max(0, min(self.current_page, total_pages - 1))
        start = self.current_page * self.page_size
        page_rows = set(matching_rows[start:start + self.page_size])
        for row_index in range(len(self.records)):
            self.table.setRowHidden(row_index, row_index not in page_rows)
        visible_count = len(page_rows)
        self.table.setFixedHeight(self.table.horizontalHeader().height() + max(1, visible_count) * 112 + 4)
        if hasattr(self, "sync_footer"):
            self.sync_footer.setText(
                f"G\u00f6sterilen {visible_count} / {len(matching_rows)} kay\u0131t"
            )
            self.page_label.setText(f"{self.current_page + 1} / {total_pages}")
            self.previous_page.setEnabled(self.current_page > 0)
            self.next_page.setEnabled(self.current_page + 1 < total_pages)

    def open_documents_center(self):
        dlg = UnifiedDocumentsCenterDialog(self.db, None, self)
        dlg.exec()

    @staticmethod
    def _cargo_manifest_html(records):
        headings = ("Takip No", "Musteri / Cihaz", "Yetkili Servis", "Gonderim", "Gidis Kargo", "Donus Kargo", "Durum")
        body = []
        for record in records:
            values = (record[1], "{} / {}".format(record[2] or '-', record[3] or '-'),
                      record[4], record[6], record[7], record[8], record[9])
            body.append("<tr>{}</tr>".format("".join("<td>{}</td>".format(html.escape(str(value or '-'))) for value in values)))
        return ('<html><head><style>body{{font-family:Inter;font-size:10pt}}table{{width:100%;border-collapse:collapse}}'
                'td,th{{border:1px solid #888;padding:6px;text-align:left}}</style></head><body>'
                '<h2>Lojistik / Toplu Kargo Fisi</h2><p>{} kayit</p><table><tr>{}</tr>{}</table></body></html>').format(
                    len(records), "".join("<th>{}</th>".format(value) for value in headings), "".join(body))

    def print_cargo_manifest(self):
        indices = self._selected_rows() or getattr(self, "_matching_rows", list(range(len(self.records))))
        records = [self.records[index] for index in indices if 0 <= index < len(self.records)]
        if not records:
            show_warning(self, "Kargo fisi icin kayit secin veya filtreleri degistirin.")
            return
        from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
        from PyQt6.QtGui import QTextDocument
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        document = QTextDocument(self)
        document.setHtml(self._cargo_manifest_html(records))
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Toplu Kargo Fisi")
        preview.paintRequested.connect(document.print)
        preview.exec()

    def refresh_data(self):
        try:
            records = list(self.db.get_external_trackings() or [])
            self.records = records
            self._update_filter_options(records)
            
            # Update Statistics Cards
            while self.stats_layout.count():
                item = self.stats_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            total_count = len(records)
            external_statuses = {"kargoya verildi", "servise ulasti", "onarimda", "dis serviste"}
            pending_statuses = {"onay bekliyor", "iade bekleniyor"}
            received_statuses = {"geri geldi", "teslim alindi", "musteriye hazir"}
            normalized_statuses = [_normalize_external_status(row[9]) for row in records]
            active_count = sum(status in external_statuses for status in normalized_statuses)
            pending_count = sum(status in pending_statuses for status in normalized_statuses)
            received_count = sum(status in received_statuses for status in normalized_statuses)
            
            # Create stat cards
            self.stats_layout.addWidget(self.create_stat_card("Toplam Kay\u0131t", str(total_count), "clipboard", "@finance_text"), 1)
            self.stats_layout.addWidget(self.create_stat_card("D\u0131\u015f Serviste (Aktif)", str(active_count), "outbound", "@finance_tertiary"), 1)
            self.stats_layout.addWidget(self.create_stat_card("Onay Bekleyen", str(pending_count), "clock", "@finance_primary"), 1)
            self.stats_layout.addWidget(self.create_stat_card("Teslim Al\u0131nan", str(received_count), "check", "@finance_secondary"), 1)
            
            # Update Table
            self.table.setRowCount(len(records))
            
            for i, r in enumerate(records):
                # r: id, internal, cust, prod, serv, serv_no, date, out_cargo, in_cargo, status, notes
                self.table.setRowHeight(i, 112)
                
                # Emanet No
                item_no = QTableWidgetItem(f"{r[1] or '-'}\nServis: {r[5] or '-'}")
                tracking_font = QFont(DesignTokens.MONO_FONT_NAME)
                tracking_font.setPixelSize(11)
                tracking_font.setWeight(QFont.Weight.Bold)
                item_no.setFont(tracking_font)
                item_no.setToolTip(item_no.text())
                self.table.setItem(i, 0, item_no)
                
                # Müşteri & Ürün
                cust_prod = f"{r[2] or '-'}\n{r[3] or '-'}"
                item_cp = QTableWidgetItem(cust_prod)
                item_cp.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 1, item_cp)

                # Servis Info
                serv_info = f"{r[4] or '-'}\nNo: {r[5] or '-'}"
                item_serv = QTableWidgetItem(serv_info)
                item_serv.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 2, item_serv)

                # Tarih
                date_item = QTableWidgetItem(format_turkish_date(str(r[6] or ""), "short"))
                date_font = QFont(tracking_font)
                date_font.setBold(False)
                date_item.setFont(date_font)
                date_item.setToolTip(str(r[6] or ''))
                self.table.setItem(i, 3, date_item)
                
                # Kargo
                cargo = "Gidis: {}\nDonus: {}".format(r[7] or '-', r[8] or '-')
                lbl_cargo = QLabel(cargo)
                lbl_cargo.setTextFormat(Qt.TextFormat.PlainText)
                lbl_cargo.setFont(QFont(DesignTokens.MONO_FONT_NAME))
                lbl_cargo.setToolTip(cargo)
                lbl_cargo.setMargin(8)
                lbl_cargo.setWordWrap(True)
                lbl_cargo.setStyleSheet(theme_qss("border: none; background: transparent; color: @finance_text_muted; font-size: 12px;"))
                self.table.setCellWidget(i, 4, lbl_cargo)
                fields = set(r.keys()) if hasattr(r, "keys") else set()
                coverage = str(r['warranty_coverage'] or '-') if 'warranty_coverage' in fields else '-'
                cost = str(r['repair_cost']) if 'repair_cost' in fields and r['repair_cost'] is not None else '-'
                coverage_item = QTableWidgetItem(coverage)
                cost_item = QTableWidgetItem(cost)
                cost_item.setFont(tracking_font)
                if cost != '-':
                    cost_item.setToolTip(cost)
                if coverage == '-':
                    coverage_item.setToolTip("Garanti kapsami kaydedilmemis.")
                if cost == '-':
                    cost_item.setToolTip("Maliyet kaydedilmemis; sifir tutar varsayilmadi.")
                self.table.setItem(i, 7, coverage_item)
                self.table.setItem(i, 8, cost_item)

                status_palette = {
                    "Onar\u0131mda": ("@warning_bg", "@warning"),
                    "\u0130ade Bekleniyor": ("@finance_surface_alt", "@finance_primary"),
                    "Onay Bekliyor": ("@finance_surface_alt", "@finance_primary"),
                    "D\u0131\u015f Serviste": ("@danger_bg", "@finance_tertiary"),
                    "Haz\u0131r": ("@success_bg", "@finance_secondary"),
                    "Geri Geldi": ("@success_bg", "@finance_secondary"),
                    "Teslim Al\u0131nd\u0131": ("@success_bg", "@finance_secondary"),
                    "M\u00fc\u015fteriye Haz\u0131r": ("@success_bg", "@finance_secondary"),
                    "Kargoya Verildi": ("@danger_bg", "@finance_tertiary"),
                    "Servise Ula\u015ft\u0131": ("@finance_surface_alt", "@finance_primary"),
                    "M\u00fc\u015fteriye Teslim Edildi": ("@success_bg", "@finance_secondary"),
                    "Haz\u0131rlan\u0131yor": ("@finance_surface_alt", "@finance_text_muted"),
                }
                normalized_palette = {
                    _normalize_external_status(key): value
                    for key, value in status_palette.items()
                }
                st_bg, st_fg = normalized_palette.get(
                    _normalize_external_status(r[9]),
                    ("@finance_surface_alt", "@finance_text_muted"),
                )
                st_lbl = QLabel(str(r[9] or "-"))
                st_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                st_lbl.setWordWrap(True)
                st_lbl.setMaximumHeight(42)
                st_lbl.setStyleSheet(theme_qss(f"""
                    QLabel {{
                        background-color: {st_bg};
                        color: {st_fg};
                        border: none;
                        border-radius: 4px;
                        min-height: 28px;
                        padding: 6px 10px;
                        font-weight: 800;
                        font-size: 11px;
                    }}
                """))
                status_cell = QWidget()
                status_cell.setStyleSheet(theme_qss("background: @surface; border: none;"))
                status_layout = QHBoxLayout(status_cell)
                status_layout.setContentsMargins(6, 0, 6, 0)
                status_layout.addWidget(st_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i, 5, QTableWidgetItem(str(r[9] or '-')))
                self.table.setCellWidget(i, 5, status_cell)

                btn_container = QWidget()
                btn_container.setStyleSheet("QWidget { background: transparent; border: none; }")
                btn_layout = QHBoxLayout(btn_container)
                btn_layout.setContentsMargins(4, 8, 4, 8)
                btn_layout.setSpacing(4)
                
                btn_edit = QPushButton("D\u00fczenle")
                btn_edit.setFixedSize(74, 30)
                btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm") + "QPushButton { padding: 0; min-height: 26px; }"))
                btn_edit.clicked.connect(lambda ch, rec=r: self.edit_record(rec))
                btn_layout.addWidget(btn_edit)
                
                btn_delete = QPushButton("Sil")
                btn_delete.setToolTip("Sil")
                btn_delete.setFixedSize(36, 30)
                btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_delete.setStyleSheet(theme_qss("QPushButton { background: @finance_surface_alt; color: @danger; border: 1px solid @finance_outline; border-radius: 4px; padding: 0; min-height: 26px; }"))
                btn_delete.clicked.connect(lambda ch, rec_id=r[0]: self.delete_record(rec_id))
                btn_layout.addWidget(btn_delete)
                
                self.table.setCellWidget(i, 6, btn_container)

            self._apply_filters()

        except Exception as e:
            logger.error(f"ExternalTrackingPage refresh_data error: {e}")

    def _selected_rows(self):
        return sorted(set(index.row() for index in self.table.selectionModel().selectedRows()))

    def toggle_multiselect(self, checked: bool):
        self.table.clearSelection()
        if checked:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im Ac\u0131k")
        else:
            self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
            self.btn_multi.setToolTip("\u00c7oklu Se\u00e7im")
    
    def create_stat_card(self, title, value, icon, color):
        """Create a compact token-driven operational metric."""
        card = QFrame()
        card.setObjectName("ExternalTrackingMetric")
        card.setFixedHeight(120)
        card.setStyleSheet(theme_qss("QFrame#ExternalTrackingMetric { background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; } QLabel { border: none; background: transparent; }"))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        heading = QHBoxLayout()
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(theme_qss("font-size: 11px; font-weight: 700; color: @finance_text_muted; background: transparent; border: none;"))
        heading.addWidget(title_lbl, 1)
        heading.addWidget(LoanerMetricIcon(icon, color.lstrip("@")))
        layout.addLayout(heading)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(theme_qss(f"font-size: 26px; font-weight: 800; color: {color}; border: none; background: transparent;"))
        layout.addWidget(val_lbl)
        subtitle = QLabel({"clipboard": "Garanti Havuzu", "outbound": "Kargoda / Serviste", "clock": "Fiyat / Onay", "check": "Teslim / Hazir"}[icon])
        subtitle.setStyleSheet(theme_qss("background: @finance_surface_alt; color: @finance_text_muted; border: none; padding: 4px 6px; font-size: 11px;"))
        layout.addWidget(subtitle)
        return card
    
    def delete_record(self, record_id):
        """Kaydı sil"""
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        if SimpleConfirmDialog(self, "Silme Onayı", "Bu kaydı silmek istediğinize emin misiniz", ok_text="Sil").exec():
            try:
                self.db.delete_external_tracking(record_id)
                show_success(self, "Kayıt başarıyla silindi.")
                self.refresh_data()
            except Exception as e:
                show_error(self, f"Silme hatası: {e}")

    def add_record(self):
        dlg = ExternalTrackingDialog(self.db, self)
        if dlg.exec():
            self.refresh_data()

    def edit_record(self, data):
        dlg = ExternalTrackingDialog(self.db, self, data=data)
        if dlg.exec():
            self.refresh_data()

    def open_selected_record(self, row, _column=0):
        try:
            records = self.records
            if 0 <= row < len(records):
                self.edit_record(records[row])
        except Exception as e:
            logger.error(f"ExternalTrackingPage open_selected_record error: {e}")

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=65):
            return
        row = self.table.rowAt(position.y())
        if row < 0:
            return
        if self.table.selectionMode() == QAbstractItemView.SelectionMode.SingleSelection:
            self.table.selectRow(row)
        try:
            records = self.records
            selected_rows = self._selected_rows() or [row]
            valid_rows = [r for r in selected_rows if 0 <= r < len(records)]
            if not valid_rows:
                return
            record = records[row]
        except Exception as e:
            logger.error(f"ExternalTrackingPage context menu data error: {e}")
            return

        menu = QMenu(self)
        act_edit = menu.addAction("Düzenle")
        act_delete = menu.addAction("Sil")
        act_gallery = menu.addAction("Fotoğraf Galerisi")
        act_export_selected = menu.addAction("Secilileri Excel Dışa Aktar")
        chosen = menu.exec(self.table.viewport().mapToGlobal(position))

        if chosen == act_edit:
            self.edit_record(record)
        elif chosen == act_delete:
            self.delete_record(record[0])
        elif chosen == act_gallery:
            try:
                dlg = ExternalTrackingDialog(self.db, self, data=record)
                dlg.open_photo_gallery()
            except Exception as e:
                logger.error(f"ExternalTrackingPage context gallery error: {e}")
        elif chosen == act_export_selected:
            self.export_selected_to_excel(valid_rows)

    def export_selected_to_excel(self, selected_rows=None):
        try:
            selected_rows = selected_rows or self._selected_rows()
            if not selected_rows:
                show_warning(self, "Disa aktarmak icin en az bir kayit secin.")
                return
            records = self.records
            export_rows = []
            for row in selected_rows:
                if 0 <= row < len(records):
                    r = records[row]
                    export_rows.append({
                        "emanet_no": r[1],
                        "musteri": r[2],
                        "urun": r[3],
                        "servis": r[4],
                        "servis_no": r[5],
                        "gidis_tarihi": r[6],
                        "gidis_kargo": r[7],
                        "donus_kargo": r[8],
                        "durum": r[9],
                        "notlar": r[10],
                    })
            if not export_rows:
                show_warning(self, "Secili kayitlar disa aktarilamadi.")
                return
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Secili Dis Takip Kayitlarini Disa Aktar",
                "dis_takip_secili.xlsx",
                "Excel Dosyasi (*.xlsx)",
            )
            if not path:
                return
            import pandas as pd
            pd.DataFrame(export_rows).to_excel(path, index=False)
            show_success(self, "Secili dis takip kayitlari Excel olarak disa aktarildi.")
        except Exception as e:
            logger.error(f"ExternalTrackingPage export_selected_to_excel error: {e}")
            show_error(self, f"Excel disa aktarimi basarisiz: {e}")

    def import_from_csv(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error
            path, _ = QFileDialog.getOpenFileName(
                self, "İçe Aktar (Dış Takip)", "", "Excel Dosyasi (*.xlsx *.xls)",
            )
            if not path:
                return

            import pandas as pd
            try:
                df = pd.read_excel(path, dtype=str, keep_default_na=False)
            except Exception as e:
                show_error(self, f"Excel okunamadi: {e}")
                return

            if df is None or df.empty:
                show_error(self, "Dosya bos veya okunamadi.")
                return

            def _norm_col(c):
                c = str(c).lower().strip()
                for src_char, dst_char in [("?","i"),("?","g"),("?","u"),("?","s"),("?","o"),("?","c")]:
                    c = c.replace(src_char, dst_char)
                return c.replace("_", " ").replace("-", " ")

            col_map = {
                "emanet no": "internal_no", "emanet": "internal_no", "no": "internal_no", "internal no": "internal_no",
                "musteri": "customer", "customer": "customer", "musteri adi": "customer",
                "urun": "product", "product": "product", "parca": "product", "urun parca": "product", "malzeme": "product",
                "servis": "service", "service": "service", "gonderilen yer": "service", "yer": "service", "firma": "service",
                "servis no": "service_no", "service no": "service_no", "kayit no": "service_no", "servis kayit no": "service_no",
                "tarih": "date", "date": "date", "gonderim tarihi": "date",
                "gidis kargo": "out_cargo", "out cargo": "out_cargo", "gidis": "out_cargo", "gonderim": "out_cargo",
                "donus kargo": "in_cargo", "in cargo": "in_cargo", "donus": "in_cargo", "gelis": "in_cargo",
                "durum": "status", "status": "status",
                "notlar": "notes", "not": "notes", "notes": "notes", "aciklama": "notes"
            }

            header_found = False
            matched_cols = {}
            for col in df.columns:
                n = _norm_col(col)
                if n in col_map:
                    matched_cols[col_map[n]] = str(col)

            if "product" in matched_cols or "customer" in matched_cols:
                header_found = True
            else:
                for idx, row in df.head(10).iterrows():
                    test_matched = {}
                    for col in df.columns:
                        n = _norm_col(row[col])
                        if n in col_map:
                            test_matched[col_map[n]] = str(col)
                    if "product" in test_matched or "customer" in test_matched:
                        matched_cols = test_matched
                        header_found = True
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break

            if not header_found or ("product" not in matched_cols and "customer" not in matched_cols):
                show_error(self, "Dosyada uygun basliklar ('Urun', 'Musteri' vb.) bulunamadi!")
                return

            def _get_val(row_s, key, default=""):
                if key not in matched_cols:
                    return default
                val = str(row_s[matched_cols[key]]).strip()
                return val if val.lower() not in ["nan", "nat", "null", "none"] else default

            success, fails = 0, 0
            for _, row in df.iterrows():
                try:
                    product = _get_val(row, "product")
                    customer = _get_val(row, "customer")
                    if not product and not customer:
                        continue
                    data = {
                        "internal_no": _get_val(row, "internal_no"),
                        "customer": customer,
                        "product": product,
                        "service": _get_val(row, "service"),
                        "service_no": _get_val(row, "service_no"),
                        "date": _get_val(row, "date", __import__("datetime").datetime.now().strftime("%Y-%m-%d")),
                        "out_cargo": _get_val(row, "out_cargo"),
                        "in_cargo": _get_val(row, "in_cargo"),
                        "status": _get_val(row, "status", "Hazirlaniyor"),
                        "notes": _get_val(row, "notes"),
                    }
                    if not data["status"]:
                        data["status"] = "Hazirlaniyor"
                    self.db.add_external_tracking(data)
                    success += 1
                except Exception:
                    fails += 1

            show_success(self, f"Ice aktarma tamamlandi:\nBasarili: {success}\nHatali: {fails}")
            self.refresh_data()
        except Exception as e:
            show_error(self, f"Ice Aktarma Hatasi: {e}")

    def export_to_csv(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error, show_warning
            path, _ = QFileDialog.getSaveFileName(
                self, "Disa Aktar", "Dis_Takip_Listesi.xlsx", "Excel Dosyasi (*.xlsx)"
            )
            if not path:
                return

            records = [self.records[index] for index in getattr(self, "_matching_rows", range(len(self.records)))]
            if not records:
                show_warning(self, "Disa aktarilacak kayit bulunamadi.")
                return

            import pandas as pd
            dict_rows = []
            for s in records:
                if isinstance(s, dict):
                    aliases = {
                        "id": "id", "internal_no": "internal_tracking_no", "customer": "customer_name",
                        "product": "product_name", "service": "external_service_name",
                        "service_no": "external_service_no", "date": "sent_date",
                        "out_cargo": "outbound_cargo_no", "in_cargo": "inbound_cargo_no",
                        "status": "status", "notes": "notes",
                    }
                    dict_rows.append({key: s.get(key, s.get(alias, "")) for key, alias in aliases.items()})
                else:
                    dict_rows.append({
                        "id": s[0], "internal_no": s[1], "customer": s[2], "product": s[3],
                        "service": s[4], "service_no": s[5], "date": s[6], "out_cargo": s[7],
                        "in_cargo": s[8], "status": s[9], "notes": s[10]
                    })

            df = pd.DataFrame(dict_rows)
            rename_map = {
                "id": "ID", "internal_no": "Emanet No", "customer": "Musteri", "product": "Urun",
                "service": "Servis", "service_no": "Servis No", "date": "Tarih",
                "out_cargo": "Gidis Kargo", "in_cargo": "Donus Kargo", "status": "Durum", "notes": "Notlar"
            }
            df = df.rename(columns=rename_map)
            keep_cols = [rename_map[k] for k in rename_map if rename_map[k] in df.columns]
            df = df[keep_cols]
            df.to_excel(path, index=False)
            show_success(self, f"Disa aktarma tamamlandi:\n{path}")
        except Exception as e:
            show_error(self, f"Disa aktarma hatasi: {e}")

