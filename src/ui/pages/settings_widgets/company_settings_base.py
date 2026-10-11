# -*- coding: utf-8 -*-

"""
Company Settings Base Widget
Firma ayarları ana widget'ı - Tab yapısı ve kontrol merkezi
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QComboBox,
                             QApplication, QHBoxLayout, QFileDialog, QDialog, QTabWidget, QSizePolicy)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils import message_helper
from src.utils.design_system import DesignTokens
from src.utils.appearance_mode import AppearanceModeManager
from src.ui.pages.settings_widgets.product_bank_mapping import ProductBankMappingWidget
from src.ui.pages.settings_widgets.location_settings import LocationSettingsWidget
from src.ui.pages.settings_widgets.job_service_number_widget import JobServiceNumberSettingsWidget
from src.ui.pages.settings_widgets.company_settings_dialog import CompanySettingsDialog


class CompanySettingsWidget(QWidget):
    """Firma Ayarı Tab - Ana widget, tab yapısı ile alt modülleri yönetir"""
    
    def __init__(self, db, main_window):
        super().__init__(main_window)
        self.setObjectName("CompanySettingsWidget")
        self.db = db
        self.main_window = main_window
        self.loaded_tabs = set()
        self.setup_ui()
        self.load_data()

    def _is_classic_appearance(self):
        app = QApplication.instance()
        return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

    def _tabs_qss(self):
        if self._is_classic_appearance():
            return AppearanceModeManager.classic_tab_qss()
        return theme_qss(
            "QTabWidget::pane { border: 1px solid @border; border-radius: 10px; background-color: @surface; } "
            "QTabBar::tab { padding: 7px 12px; background-color: @surface_alt; color: @text_muted; border: 1px solid @border; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 3px; font-weight: 600; } "
            "QTabBar::tab:hover { background-color: @surface; color: @text; } "
            "QTabBar::tab:selected { background-color: @surface; color: @accent; border-bottom: 2px solid @accent; font-weight: 700; }"
        )

    def _title_qss(self):
        if self._is_classic_appearance():
            return "color: #111827; margin-bottom: 6px; background: transparent; border: none;"
        return theme_qss("color: @text; margin-bottom: 15px;")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        margin = 10 if self._is_classic_appearance() else 14
        layout.setContentsMargins(margin, margin, margin, margin)
        self.setFont(QFont("Segoe UI", 10))
        
        title = QLabel("Firma Ayarları")
        title.setFont(QFont(DesignTokens.FONT_NAME, 16, QFont.Weight.Bold))
        title.setStyleSheet(self._title_qss())
        self.title_label = title
        layout.addWidget(title)
        
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsInnerTabs")
        self.tabs.setProperty("settingsTabs", True)
        if self._is_classic_appearance():
            self.tabs.setProperty("skipThemeTransform", False)
        self.tabs.setStyleSheet(self._tabs_qss())
        layout.addWidget(self.tabs)

        # Tab 0: Firma Bilgileri
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)

        info_card = QFrame()
        info_card.setProperty("settingsCard", True)
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(8, 8, 8, 8)
        info_card_layout.setSpacing(4)

        info_title = QLabel("Firma Bilgileri & Resmi Kimlik Y\u00f6netimi")
        info_title.setFont(QFont(DesignTokens.FONT_NAME, 12, QFont.Weight.Bold))
        info_title.setStyleSheet(theme_qss("color: @text;"))
        info_heading = QHBoxLayout()
        info_heading.addWidget(info_title)
        info_status = QLabel("Firma Profili")
        info_status.setStyleSheet(theme_qss(
            "color: @success; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 4px; padding: 3px 7px; font-size: 11px; font-weight: 700;"
        ))
        info_heading.addWidget(info_status)
        verified_status = QLabel("Kay\u0131tl\u0131 & Do\u011frulanm\u0131\u015f")
        verified_status.setStyleSheet(theme_qss(
            "color: @accent; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 4px; padding: 3px 7px; font-size: 11px; font-weight: 700;"
        ))
        info_heading.addWidget(verified_status)
        info_heading.addStretch(1)
        btn_open_dialog = QPushButton("Firma Bilgilerini D\u00fczenle")
        btn_open_dialog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_dialog.setFixedSize(184, 30)
        btn_open_dialog.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; border-radius: 6px; padding: 6px 12px; font-weight: 700; } QPushButton:hover { background-color: @accent_hover; }"
        ))
        btn_open_dialog.clicked.connect(self._open_company_settings_dialog)
        self.company_edit_button = btn_open_dialog
        company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
        company_email = self.db.get_setting("company_email", "") or ""
        company_phone = self.db.get_setting("company_phone", "") or ""
        tax_office = self.db.get_setting("company_tax_office", "") or ""
        tax_number = self.db.get_setting("company_tax_number", "") or ""
        company_summary = QLabel(
            f"{company_name}  \u00b7  {tax_office or '-'}  \u00b7  {tax_number or '-'}  \u00b7  "
            f"{company_phone or company_email or '-'}"
        )
        self.company_summary_label = company_summary
        company_summary.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 600;"))
        company_summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        category_row = QGridLayout()
        category_row.setHorizontalSpacing(4)
        category_row.setVerticalSpacing(4)
        category_row.setColumnMinimumWidth(0, 160)
        category_row.setColumnMinimumWidth(1, 160)
        for category_index, category in enumerate((
            "\u0130leti\u015fim Bilgileri",
            "Sosyal Medya",
            "Fatura & S\u00f6zle\u015fme Metinleri",
            "Kargo & Yaz\u0131c\u0131 Ayarlar\u0131",
        )):
            badge = QLabel(category)
            badge.setMinimumWidth(0)
            badge.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            badge.setWordWrap(True)
            badge.setStyleSheet(theme_qss(
                "color: @text; background: @surface_alt; border: 1px solid @border; border-radius: 4px; "
                "padding: 3px 5px; font-size: 10px;"
            ))
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            category_row.addWidget(badge, category_index // 2, category_index % 2)
        category_row.setColumnStretch(2, 1)
        identity_row = QHBoxLayout()
        identity_row.setSpacing(10)
        identity_details = QVBoxLayout()
        identity_details.setContentsMargins(0, 0, 0, 0)
        identity_details.setSpacing(4)
        identity_details.addLayout(info_heading)
        identity_details.addWidget(company_summary)
        identity_row.addLayout(identity_details, 3)
        identity_row.addLayout(category_row, 2)
        info_card_layout.addLayout(identity_row)

        info_layout.addWidget(info_card)
        self.tabs.addTab(info_tab, "Firma Bilgileri & Kimlik")

        # Tab 1: Logo & Arkaplan
        brand_tab = QWidget()
        brand_layout = QVBoxLayout(brand_tab)
        brand_layout.setContentsMargins(8, 8, 8, 8)
        brand_layout.setSpacing(6)

        brand_card = QFrame()
        brand_card.setProperty("settingsCard", True)
        brand_card_layout = QHBoxLayout(brand_card)
        brand_card_layout.setContentsMargins(8, 8, 8, 8)
        brand_card_layout.setSpacing(8)

        asset_specs = (
            ("Birincil Firma Logosu", "logo_path", "AYEC", "De\u011fi\u015ftir", self._select_logo),
            ("Fatura Antet / Ka\u015fe G\u00f6rseli", "company_stamp_path", "PDF", "Yenisini Y\u00fckle", self._select_invoice_stamp),
            ("Masa\u00fcst\u00fc Duvar Ka\u011f\u0131d\u0131", "background_image", "DESK", "Temay\u0131 Se\u00e7", self._select_bg),
        )
        self.lbl_logo = QLabel("Yok")
        self.lbl_invoice_stamp = QLabel("Y\u00fcklenmedi")
        self.lbl_bg = QLabel("Varsay\u0131lan (Dark Slate)")
        self.brand_asset_labels = {
            "logo_path": self.lbl_logo,
            "company_stamp_path": self.lbl_invoice_stamp,
            "background_image": self.lbl_bg,
        }
        for title_text, setting_key, icon_text, action_text, callback in asset_specs:
            asset = QFrame()
            asset.setObjectName("companyBrandAsset")
            asset.setMinimumHeight(62)
            asset.setMinimumWidth(0)
            asset.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            asset.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 6px;"))
            asset_layout = QHBoxLayout(asset)
            asset_layout.setContentsMargins(6, 6, 6, 6)
            asset_layout.setSpacing(5)
            preview = QLabel(icon_text)
            preview.setFixedSize(34, 34)
            preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview.setStyleSheet(theme_qss("color: @selection_text; background: @accent_soft; border: 1px solid @border; border-radius: 5px; font-size: 11px; font-weight: 800;"))
            copy = QVBoxLayout()
            copy.setContentsMargins(0, 0, 0, 0)
            copy.setSpacing(3)
            title_label = QLabel(title_text)
            title_label.setMinimumWidth(0)
            title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            title_label.setWordWrap(True)
            title_label.setStyleSheet(theme_qss("color: @text; font-size: 10px; font-weight: 700;"))
            value_label = self.brand_asset_labels[setting_key]
            value_label.setMinimumWidth(0)
            value_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            value_label.setWordWrap(True)
            value_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px;"))
            value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            copy.addWidget(title_label)
            copy.addWidget(value_label)
            action = QPushButton(action_text)
            action.setMinimumWidth(104 if setting_key == "company_stamp_path" else 88)
            action.setFixedHeight(24)
            action.clicked.connect(callback)
            asset_layout.addWidget(preview)
            asset_layout.addLayout(copy, 1)
            asset_layout.addWidget(action)
            brand_card_layout.addWidget(asset, 1)

        brand_layout.addWidget(brand_card)
        self.tabs.addTab(brand_tab, "Logo & G\u00f6rsel")
        info_layout.addSpacing(5)
        visual_heading = QLabel("LOGO & G\u00d6RSEL VARLIKLAR  \u00b7  Evrak antetlerinde, faturalarda ve masa\u00fcst\u00fcnde yer alan grafik materyaller")
        visual_heading.setMinimumWidth(0)
        visual_heading.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        visual_heading.setWordWrap(True)
        visual_heading.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700; padding: 2px 3px;"))
        visual_heading_row = QHBoxLayout()
        visual_heading_row.addWidget(visual_heading, 1)
        formats_label = QLabel("PNG, SVG, ICO Destekli")
        formats_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        visual_heading_row.addWidget(formats_label)
        info_layout.addLayout(visual_heading_row)
        brand_layout.removeWidget(brand_card)
        brand_card.setParent(info_tab)
        info_layout.addWidget(brand_card)

        # Tab 2: Konum & Harita (Lazy loaded)
        location_tab = QWidget()
        self.location_layout = QVBoxLayout(location_tab)
        self.location_layout.setContentsMargins(0, 0, 0, 0)
        self.location_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(location_tab, "Konum & GPS Harita")

        # Tab 3: İş/Servis/Referans Numaraları (Lazy loaded)
        number_tab = QWidget()
        self.number_layout = QVBoxLayout(number_tab)
        self.number_layout.setContentsMargins(0, 0, 0, 0)
        self.number_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(number_tab, "\u0130\u015f / Servis Saya\u00e7lar\u0131")
        
        # Tab 4: Stok Banka Eslesme (Lazy loaded)
        stock_tab = QWidget()
        self.stock_layout = QVBoxLayout(stock_tab)
        self.stock_layout.setContentsMargins(0, 0, 0, 0)
        self.stock_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(stock_tab, "Stok - Banka E\u015fle\u015ftirme")

        for tab_index in range(2, self.tabs.count()):
            self._ensure_tab_loaded(tab_index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.tabs.setCurrentIndex(0)

        # Save Button
        btn_save = QPushButton("G\u00dcNCELLE")
        btn_save.setObjectName("company_settings_save")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary", size="lg")))
        btn_save.clicked.connect(self.save_data)
        self.save_button = btn_save
        self._compose_reference_layout(layout, title, btn_save)

    def _compose_reference_layout(self, root_layout, title, save_button):
        pages = [self.tabs.widget(index) for index in range(self.tabs.count())]
        labels = ["Firma Bilgileri && Kimlik", "Logo && G\u00f6rsel", "Konum && GPS Harita", "\u0130\u015f / Servis Saya\u00e7lar\u0131", "Stok - Banka E\u015fle\u015ftirme"]
        descriptions = ["", "Evrak antetlerinde, faturalarda ve masa\u00fcst\u00fcnde yer alan grafik varl\u0131klar", "Harita ba\u015flang\u0131\u00e7 koordinat\u0131 ve eve d\u00f6n butonu hedefi", "Yeni kay\u0131tlar\u0131n otomatik artan numara formatlar\u0131", ""]
        for index in range(self.tabs.count()):
            self.tabs.removeTab(0)
        for page, label in zip(pages, labels):
            self.tabs.addTab(QWidget(), label)

        while root_layout.count():
            item = root_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        # The sections are presented as one continuous page; keep the tab
        # container only as an internal section index for existing signals.
        self.tabs.hide()
        self.tabs.setParent(self)

        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(8)
        title.setText("Firma & Kurumsal Ayarlar")
        title.setStyleSheet(theme_qss("color: @text; font-size: 10px; font-weight: 800; padding: 0;"))
        header = QFrame(self)
        header.setObjectName("companyReferenceHeader")
        header.setFixedHeight(38)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(6, 0, 6, 0)
        header_layout.setSpacing(5)
        brand = QLabel("\u2302 AYEC PRO")
        brand.setStyleSheet(theme_qss("color: @accent; background: @surface_alt; border: 1px solid @border; border-radius: 5px; padding: 5px 9px; font-size: 11px; font-weight: 800;"))
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setStyleSheet(theme_qss("color: @border;"))
        compact = QLabel("Kompakt Y\u00f6netici Modu")
        compact.setStyleSheet(theme_qss("color: @success; background: @surface_alt; border: 1px solid @border; border-radius: 10px; padding: 2px 6px; font-size: 10px; font-weight: 700;"))
        database_state = QLabel("\u25cf Veritaban\u0131: Ba\u011fl\u0131 (LocalDB)")
        database_state.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        refresh_button = QPushButton("Yenile")
        refresh_button.setFixedHeight(26)
        refresh_button.clicked.connect(self.load_data)
        header_layout.addWidget(brand)
        header_layout.addWidget(separator)
        header_layout.addWidget(title)
        header_layout.addWidget(compact)
        header_layout.addStretch(1)
        header_layout.addWidget(database_state)
        header_layout.addWidget(refresh_button)
        self.company_edit_button.setParent(header)
        header_layout.addWidget(self.company_edit_button)
        root_layout.addWidget(header)

        workspace = QWidget(self)
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        content = QWidget(workspace)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        scroll = QScrollArea(content)
        scroll.setObjectName("companyReferenceScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        sections_host = QWidget(scroll)
        sections_layout = QVBoxLayout(sections_host)
        sections_layout.setContentsMargins(0, 0, 0, 0)
        sections_layout.setSpacing(7)
        self.section_frames = []
        for index, (page, label) in enumerate(zip(pages, labels)):
            page.setParent(None)
            section = QFrame(sections_host)
            section.setObjectName("companyReferenceSection")
            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(7, 7, 7, 7) if index == 0 else section_layout.setContentsMargins(5, 4, 5, 4)
            section_layout.setSpacing(3)
            if index not in (0, 1, 3):
                section_header = QHBoxLayout()
                section_title = QLabel(label.upper())
                section_title.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 800;"))
                section_header.addWidget(section_title)
                if descriptions[index] and index != 3:
                    section_description = QLabel("  \u2022  " + descriptions[index])
                    section_description.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
                    section_header.addWidget(section_description, 1)
                section_header.addStretch(1)
                section_layout.addLayout(section_header)
            section_layout.addWidget(page)
            page.show()
            sections_layout.addWidget(section)
            self.section_frames.append(section)
        sections_layout.addStretch(1)
        scroll.setWidget(sections_host)
        content_layout.addWidget(scroll, 1)
        self.company_sections_scroll = scroll
        workspace_layout.addWidget(content, 1)
        root_layout.addWidget(workspace, 1)
        save_button.setText("G\u00dcNCELLE & KAYDET")
        save_button.setFixedSize(164, 30)
        save_button.setStyleSheet(theme_qss("QPushButton { color: #FFFFFF; background-color: @accent; border: 1px solid @accent; border-radius: 6px; font-size: 11px; font-weight: 800; padding: 4px; } QPushButton:hover { background-color: @accent_hover; }"))
        footer = QHBoxLayout()
        footer.setContentsMargins(10, 0, 10, 0)
        footer_status = QLabel("\u25cf AYEC PRO Finans Konsolu v2.0.4 Premium Enterprise  \u00b7  Yerel Veritaban\u0131 Aktif (LocalDB)")
        footer_status.setStyleSheet(theme_qss("color: @text_muted; font-size: 9px;"))
        footer.addWidget(footer_status)
        footer.addStretch(1)
        cancel_button = QPushButton("Vazge\u00e7")
        cancel_button.setFixedSize(74, 28)
        cancel_button.clicked.connect(self.load_data)
        footer.addWidget(cancel_button)
        footer.addWidget(save_button)
        root_layout.addLayout(footer)

        self.setStyleSheet(self.styleSheet() + theme_qss(
            "QFrame#companyReferenceHeader { background: @window; border-bottom: 1px solid @border; }"
            "QFrame#companyReferenceSection { background: @surface; border: 1px solid @border; border-radius: 8px; }"
            "QFrame#companyBrandAsset { background: @surface_alt; border: 1px solid @border; border-radius: 6px; }"
            "QWidget#companyReferenceScroll { background: @bg; }"
        ))

    def apply_theme_styles(self):
        if self._is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
            if hasattr(self, "tabs"):
                self.tabs.setProperty("skipThemeTransform", False)
        self.setStyleSheet("""
            QWidget#CompanySettingsWidget,
            QWidget#CompanySettingsWidget > QWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QFrame[settingsCard="true"] {
                background: #FFFFFF;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
            }
            QLabel {
                color: #111827;
                background: transparent;
                border: none;
            }
            QPushButton {
                background: #FFFFFF;
                color: #111827;
                border: 1px solid #AEB4BD;
                border-radius: 0px;
                padding: 4px 10px;
                min-height: 24px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: #F3F4F6;
                border-color: #1F4E79;
            }
        """ if self._is_classic_appearance() else "")
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(self._tabs_qss())
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(self._title_qss())
        layout = self.layout()
        if layout:
            if self._is_classic_appearance():
                layout.setContentsMargins(10, 10, 10, 10)
            else:
                layout.setContentsMargins(8, 6, 8, 8)
        ThemeManager.refresh_widget_tree(self, include_root=False)

    def _on_tab_changed(self, index):
        self._ensure_tab_loaded(index)
        if hasattr(self, "company_sections_scroll") and index < len(self.section_frames):
            self.company_sections_scroll.ensureWidgetVisible(self.section_frames[index], 0, 8)

    def _ensure_tab_loaded(self, index):
        if index in self.loaded_tabs:
            return
        
        # Helper to clear layout
        def clear_layout(layout):
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        if index == 2:  # Konum & Harita
            clear_layout(self.location_layout)
            self.location_widget = LocationSettingsWidget(self.db, self.main_window)
            self.location_layout.addWidget(self.location_widget)
            self.loaded_tabs.add(index)
        
        elif index == 3:  # İş/Servis/Referans Numaraları
            clear_layout(self.number_layout)
            self.number_widget = JobServiceNumberSettingsWidget(self.db, self.main_window)
            self.number_layout.addWidget(self.number_widget)
            self.loaded_tabs.add(index)
            
        elif index == 4:  # Stok Banka Eslesme
            clear_layout(self.stock_layout)
            self.stock_widget = ProductBankMappingWidget(self.db, self.main_window)
            self.stock_layout.addWidget(self.stock_widget)
            self.loaded_tabs.add(index)

    def load_data(self):
        for name, method_name in (
            ("location_widget", "load_data"),
            ("number_widget", "load_numbers"),
            ("stock_widget", "load_data"),
        ):
            widget = getattr(self, name, None)
            method = getattr(widget, method_name, None)
            if callable(method):
                method()
        self._refresh_branding_labels()
        if hasattr(self, "company_summary_label"):
            company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
            tax_office = self.db.get_setting("company_tax_office", "") or ""
            tax_number = self.db.get_setting("company_tax_number", "") or ""
            company_phone = self.db.get_setting("company_phone", "") or ""
            company_email = self.db.get_setting("company_email", "") or ""
            self.company_summary_label.setText(
                f"{company_name}  \u00b7  {tax_office or '-'}  \u00b7  {tax_number or '-'}  \u00b7  "
                f"{company_phone or company_email or '-'}"
            )

    def save_data(self):
        for name, method_name, args in (
            ("location_widget", "save_data", (True,)),
            ("number_widget", "save_data", (True,)),
            ("stock_widget", "save_all", (True,)),
        ):
            widget = getattr(self, name, None)
            method = getattr(widget, method_name, None)
            if callable(method):
                method(*args)
        self._refresh_main_window_branding()

        if self.main_window:
            self.main_window.show_notification("Firma bilgileri güncellendi.", "success")
        else:
            message_helper.show_info(self, "Başarılı", "Firma bilgileri güncellendi.")

    def _open_company_settings_dialog(self):
        dlg = CompanySettingsDialog(self.db, self.main_window, self)
        dlg.exec()
        self.load_data()

    def _refresh_branding_labels(self):
        for setting_key, label in getattr(self, "brand_asset_labels", {}).items():
            value = self.db.get_setting(setting_key, "") or ""
            if setting_key == "background_image" and not value:
                value = "Varsay\u0131lan (Dark Slate)"
            elif not value:
                value = "Yok" if setting_key == "logo_path" else "Y\u00fcklenmedi"
            label.setText(os.path.basename(value) if os.path.dirname(value) else value)

    def _select_invoice_stamp(self):
        fname, _ = QFileDialog.getOpenFileName(
            self,
            "Fatura antet / ka\u015fe g\u00f6rseli se\u00e7",
            "",
            "Images (*.png *.jpg *.jpeg *.svg *.ico)",
        )
        if fname:
            self.db.set_setting("company_stamp_path", fname)
        self._refresh_branding_labels()

    def _select_bg(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Arkaplan seç", "", "Images (*.png *.jpg *.jpeg)")
        if fname:
            self.db.set_setting("background_image", fname)
        self._refresh_branding_labels()

    def _refresh_main_window_branding(self):
        if not self.main_window:
            return
        try:
            logo_path = self.db.get_setting("logo_path", "") or ""
            company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
            site_title = self.db.get_setting("site_title", "") or ""
            side_menu = getattr(getattr(self.main_window, "app_sidebar", None), "side_menu", None)
            if side_menu and hasattr(side_menu, "update_branding"):
                side_menu.update_branding(logo_path, company_name, site_title)
            if hasattr(self.main_window, "refresh_side_menu"):
                self.main_window.refresh_side_menu()
        except Exception:
            pass

    def _select_logo(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Logo seç", "", "Images (*.png *.jpg *.jpeg *.ico)")
        if fname:
            self.db.set_setting("logo_path", fname)
            self._refresh_main_window_branding()
        self._refresh_branding_labels()
