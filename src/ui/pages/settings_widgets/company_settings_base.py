# -*- coding: utf-8 -*-

"""
Company Settings Base Widget
Firma ayarları ana widget'ı - Tab yapısı ve kontrol merkezi
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QComboBox,
                             QApplication, QHBoxLayout, QFileDialog, QDialog, QTabWidget)
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
        super().__init__()
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
            "QTabBar::tab { padding: 10px 18px; background-color: @surface_alt; color: @text_muted; border: 1px solid @border; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; font-weight: 600; } "
            "QTabBar::tab:hover { background-color: @surface; color: @text; } "
            "QTabBar::tab:selected { background-color: @surface; color: @accent; border-bottom: 2px solid @accent; font-weight: 700; }"
        )

    def _title_qss(self):
        if self._is_classic_appearance():
            return "color: #111827; margin-bottom: 6px; background: transparent; border: none;"
        return theme_qss("color: @text; margin-bottom: 15px;")

    def setup_ui(self):
        layout = QVBoxLayout(self)
        margin = 10 if self._is_classic_appearance() else 30
        layout.setContentsMargins(margin, margin, margin, margin)
        
        title = QLabel("Firma Ayarları")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
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
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(16)

        info_card = QFrame()
        info_card.setProperty("settingsCard", True)
        info_card_layout = QVBoxLayout(info_card)
        info_card_layout.setContentsMargins(20, 20, 20, 20)
        info_card_layout.setSpacing(12)

        info_title = QLabel("Firma Bilgileri")
        info_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        info_title.setStyleSheet(theme_qss("color: @text;"))
        info_desc = QLabel("Firma iletişim, sosyal medya, sözleşme ve temel bilgileri yönetin.")
        info_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        info_desc.setWordWrap(True)
        info_card_layout.addWidget(info_title)
        info_card_layout.addWidget(info_desc)

        btn_open_dialog = QPushButton("Firma Bilgilerini Düzenle")
        btn_open_dialog.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open_dialog.setFixedHeight(40)
        btn_open_dialog.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; border-radius: 6px; padding: 8px 14px; font-weight: 700; } QPushButton:hover { background-color: @accent_hover; }"
        ))
        btn_open_dialog.clicked.connect(self._open_company_settings_dialog)
        info_card_layout.addWidget(btn_open_dialog, 0, Qt.AlignmentFlag.AlignLeft)

        info_layout.addWidget(info_card)
        info_layout.addStretch()
        self.tabs.addTab(info_tab, "Firma Bilgileri")

        # Tab 1: Logo & Arkaplan
        brand_tab = QWidget()
        brand_layout = QVBoxLayout(brand_tab)
        brand_layout.setContentsMargins(20, 20, 20, 20)
        brand_layout.setSpacing(16)

        brand_card = QFrame()
        brand_card.setProperty("settingsCard", True)
        brand_card_layout = QGridLayout(brand_card)
        brand_card_layout.setContentsMargins(20, 20, 20, 20)
        brand_card_layout.setSpacing(12)

        brand_title = QLabel("Logo ve Arkaplan")
        brand_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        brand_title.setStyleSheet(theme_qss("color: @text;"))
        brand_layout.addWidget(brand_title)

        brand_card_layout.addWidget(QLabel("Masaüstü arkaplanı:"), 0, 0)
        self.lbl_bg = QLabel("Varsayılan")
        self.lbl_bg.setStyleSheet(theme_qss("color: @text_muted; font-style: italic;"))
        brand_card_layout.addWidget(self.lbl_bg, 0, 1)
        btn_bg = QPushButton("Değiştir")
        btn_bg.setFixedSize(110, 34)
        btn_bg.setStyleSheet(theme_qss("QPushButton { background-color: @surface_alt; color: @text; border-radius: 6px; border: 1px solid @border; } QPushButton:hover { background-color: @surface; }"))
        btn_bg.clicked.connect(self._select_bg)
        brand_card_layout.addWidget(btn_bg, 0, 2)

        brand_card_layout.addWidget(QLabel("Firma logosu:"), 1, 0)
        self.lbl_logo = QLabel("Yok")
        self.lbl_logo.setStyleSheet(theme_qss("color: @text_muted; font-style: italic;"))
        brand_card_layout.addWidget(self.lbl_logo, 1, 1)
        btn_logo = QPushButton("Değiştir")
        btn_logo.setFixedSize(110, 34)
        btn_logo.setStyleSheet(theme_qss("QPushButton { background-color: @surface_alt; color: @text; border-radius: 6px; border: 1px solid @border; } QPushButton:hover { background-color: @surface; }"))
        btn_logo.clicked.connect(self._select_logo)
        brand_card_layout.addWidget(btn_logo, 1, 2)

        brand_layout.addWidget(brand_card)
        brand_layout.addStretch()
        self.tabs.addTab(brand_tab, "Logo & Arkaplan")

        # Tab 2: Konum & Harita (Lazy loaded)
        location_tab = QWidget()
        self.location_layout = QVBoxLayout(location_tab)
        self.location_layout.setContentsMargins(0, 0, 0, 0)
        self.location_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(location_tab, "Konum & Harita")

        # Tab 3: İş/Servis/Referans Numaraları (Lazy loaded)
        number_tab = QWidget()
        self.number_layout = QVBoxLayout(number_tab)
        self.number_layout.setContentsMargins(0, 0, 0, 0)
        self.number_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(number_tab, "İş/Servis/Referans Numaraları")
        
        # Tab 4: Proforma PDF Düzenleyici (Lazy loaded)
        proforma_tab = QWidget()
        self.proforma_layout = QVBoxLayout(proforma_tab)
        self.proforma_layout.setContentsMargins(12, 12, 12, 12)
        self.proforma_layout.setSpacing(12)
        self.proforma_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(proforma_tab, "Proforma PDF Düzenleyici")
        
        # Tab 5: Stok Banka Eşleştirme (Lazy loaded)
        stock_tab = QWidget()
        self.stock_layout = QVBoxLayout(stock_tab)
        self.stock_layout.setContentsMargins(0, 0, 0, 0)
        self.stock_layout.addWidget(QLabel("Yükleniyor..."))
        self.tabs.addTab(stock_tab, "Stok Banka Eşleştirme")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        # Load initial tab (0: Firma Bilgileri)
        self._on_tab_changed(0)

        # Save Button
        btn_save = QPushButton("GÜNCELLE")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="lg")))
        btn_save.clicked.connect(self.save_data)
        layout.addWidget(btn_save)

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
            margin = 10 if self._is_classic_appearance() else 30
            layout.setContentsMargins(margin, margin, margin, margin)
        ThemeManager.refresh_widget_tree(self, include_root=False)

    def _on_tab_changed(self, index):
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
            self.location_layout.addWidget(LocationSettingsWidget(self.db, self.main_window))
            self.loaded_tabs.add(index)
        
        elif index == 3:  # İş/Servis/Referans Numaraları
            clear_layout(self.number_layout)
            self.number_layout.addWidget(JobServiceNumberSettingsWidget(self.db, self.main_window))
            self.loaded_tabs.add(index)
            
        elif index == 4:  # Proforma PDF Düzenleyici
            clear_layout(self.proforma_layout)
            self._load_proforma_tab()
            self.loaded_tabs.add(index)

        elif index == 5:  # Stok Banka Eşleştirme
            clear_layout(self.stock_layout)
            self.stock_layout.addWidget(ProductBankMappingWidget(self.db, self.main_window))
            self.loaded_tabs.add(index)

    def _load_proforma_tab(self):
        """Load the proforma template editor tab content."""
        lbl_tab_title = QLabel("\U0001F4C4  Proforma \u015eablon Edit\u00f6r\u00fc")
        lbl_tab_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl_tab_title.setStyleSheet(theme_qss("color: @text; padding-bottom: 2px;"))
        self.proforma_layout.addWidget(lbl_tab_title)

        lbl_hint = QLabel(
            "\U0001F4A1  Word benzeri edit\u00f6rle kendi proforma \u015fablonunuzu haz\u0131rlay\u0131n. "
            "'Alan Ekle' men\u00fcs\u00fcnden eklenen alanlar (m\u00fc\u015fteri, tarih, \u00fcr\u00fcn tablosu, "
            "toplamlar vb.) her PDF \u00fcretiminde ger\u00e7ek teklif verileriyle doldurulur. "
            "Be\u011fenmezseniz 'Varsay\u0131lana D\u00f6n' ile g\u00f6m\u00fcl\u00fc profesyonel \u00fcreticiye d\u00f6nebilirsiniz."
        )
        lbl_hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 8pt;"))
        lbl_hint.setWordWrap(True)
        self.proforma_layout.addWidget(lbl_hint)

        from src.ui.pages.settings_widgets.proforma_editor import ProformaTemplateEditor
        self.proforma_editor = ProformaTemplateEditor(self.db, self)
        self.proforma_layout.addWidget(self.proforma_editor, 1)

    def load_data(self):
        self._refresh_branding_labels()

    def save_data(self):
        self._refresh_main_window_branding()

        if self.main_window:
            self.main_window.show_notification("Firma bilgileri güncellendi.", "success")
        else:
            message_helper.show_info(self, "Başarılı", "Firma bilgileri güncellendi.")

    def _open_company_settings_dialog(self):
        dlg = CompanySettingsDialog(self.db, self.main_window, self)
        dlg.exec()

    def _refresh_branding_labels(self):
        bg_path = self.db.get_setting("background_image", "")
        logo_path = self.db.get_setting("logo_path", "")
        self.lbl_bg.setText(os.path.basename(bg_path) if bg_path else "Varsayılan")
        self.lbl_logo.setText(os.path.basename(logo_path) if logo_path else "Yok")

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
