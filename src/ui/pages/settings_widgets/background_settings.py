# -*- coding: utf-8 -*-

"""Background settings widget (Görünüm & Tema)."""

import os

from PyQt6.QtCore import QSignalBlocker, Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.utils.design_system import DesignTokens

from src.ui.widgets.animated_toggle import AnimatedToggle
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import tc, theme_qss
from src.utils.theme_manager import ThemeManager



class BackgroundSettingsWidget(QWidget):
    """Görünüm, tema, renk ve menü ayarları."""

    def __init__(self, db, main_window):
        super().__init__()
        self.setObjectName("BackgroundSettingsWidget")
        self.db = db
        self.main_window = main_window
        self.init_ui()
        self.load_data()

    def _card_qss(self):
        if self._is_classic_appearance():
            return """
            QGroupBox {
                font-weight: 800;
                font-size: 12px;
                border: 1px solid #B8C0CC;
                border-radius: 0px;
                margin-top: 12px;
                padding: 14px;
                background: #FFFFFF;
                color: #111827;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                background: #FFFFFF;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                border: none;
            }
            """
        return theme_qss(
            """
            QGroupBox {
                font-weight: 800;
                font-size: 13px;
                border: 1px solid @border;
                border-radius: 10px;
                margin-top: 12px;
                padding: 14px;
                background: @surface;
                color: @text;
            }
            QLabel {
                color: @text;
                background: transparent;
                border: none;
            }
            """
        )

    def _soft_button_qss(self):
        if self._is_classic_appearance():
            return """
            QPushButton {
                background: #FFFFFF;
                color: #111827;
                border-radius: 0px;
                font-weight: 700;
                border: 1px solid #AEB4BD;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: #E5E7EB;
                border-color: #2563EB;
            }
            """
        return theme_qss(
            """
            QPushButton {
                background: @surface_alt;
                color: @text;
                border-radius: 8px;
                font-weight: 700;
                border: 1px solid @border;
            }
            QPushButton:hover {
                background: @selection_bg;
                color: @selection_text;
                border-color: @selection_bg;
            }
            """
        )

    def _is_classic_appearance(self):
        app = QApplication.instance()
        return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

    def _reference_section(self, title, marker_color, note, content):
        section = QFrame()
        section.setObjectName("ThemeReferenceSection")
        section.setMinimumWidth(0)
        section.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        section.setStyleSheet(theme_qss(
            "QFrame#ThemeReferenceSection { background: @surface; border: 1px solid @border; "
            "border-radius: 12px; }"
        ))
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(14, 11, 14, 12)
        section_layout.setSpacing(8)

        header = QHBoxLayout()
        marker = QLabel("\u25cf")
        marker.setStyleSheet(f"color: {marker_color}; border: none; font-size: 13px;")
        header.addWidget(marker)
        heading = QLabel(title)
        heading.setStyleSheet(theme_qss("color: @text; border: none; font-size: 13px; font-weight: 700;"))
        header.addWidget(heading)
        header.addStretch(1)
        note_label = QLabel(note)
        note_label.setStyleSheet(theme_qss("color: @text_muted; border: none; font-size: 11px;"))
        header.addWidget(note_label)
        section_layout.addLayout(header)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(theme_qss("color: @border; background: @border; max-height: 1px;"))
        section_layout.addWidget(divider)
        section_layout.addWidget(content)
        return section

    def _tabs_qss(self):
        if self._is_classic_appearance():
            return AppearanceModeManager.classic_tab_qss()
        return theme_qss("QTabWidget::pane { border: 1px solid @border; border-radius: 10px; } QTabBar::tab { padding: 8px 16px; }")

    def init_ui(self):
        layout = QVBoxLayout(self)
        margin = 10 if self._is_classic_appearance() else 12
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(12 if self._is_classic_appearance() else 16)

        scroll = QScrollArea()
        self.scroll_area = scroll
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: #FFFFFF; border: none; } QScrollArea > QWidget > QWidget { background: #FFFFFF; }"
            if self._is_classic_appearance()
            else theme_qss("QScrollArea { background: @surface; border: none; } QScrollArea > QWidget > QWidget { background: @surface; }")
        )

        container = QWidget()
        self.container = container
        container.setStyleSheet("QWidget { background: #FFFFFF; color: #111827; }" if self._is_classic_appearance() else theme_qss("QWidget { background: @surface; }"))
        cl = QVBoxLayout(container)
        cl.setSpacing(2)

        title = QLabel("Temalar & Yazı Tipi")
        title.setFont(QFont(DesignTokens.FONT_NAME, 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #111827; background: transparent; border: none;" if self._is_classic_appearance() else theme_qss("color: @text; border: none;"))
        self.title_label = title
        title_column = QVBoxLayout()
        title_column.setContentsMargins(0, 0, 0, 0)
        title_column.setSpacing(2)
        title_line = QHBoxLayout()
        title_line.setSpacing(10)
        title_line.addWidget(title)
        config_badge = QLabel("Aray\u00fcz Konfig\u00fcrasyonu")
        config_badge.setStyleSheet(theme_qss(
            "color: @accent; background: @surface_alt; border: 1px solid @border; "
            "border-radius: 5px; padding: 3px 8px; font-size: 10px; font-weight: 600;"
        ))
        title_line.addWidget(config_badge)
        title_line.addStretch(1)
        title_column.addLayout(title_line)
        description = QLabel(
            "Aray\u00fcz temas\u0131, tipografi boyutlar\u0131, renk vurgular\u0131 ve pencere yerle\u015fim davran\u0131\u015flar\u0131n\u0131 yap\u0131land\u0131r\u0131n."
        )
        description.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        title_column.addWidget(description)

        header_tabs = QTabBar()
        header_tabs.setExpanding(False)
        header_tabs.setDrawBase(False)
        header_tabs.setStyleSheet(theme_qss(
            "QTabBar { background: @surface_alt; border: 1px solid @border; border-radius: 8px; "
            "padding: 3px; } QTabBar::tab { color: @text_muted; padding: 7px 14px; "
            "border-radius: 6px; font-size: 11px; } QTabBar::tab:selected { color: @selection_text; "
            "background: @selection_bg; font-weight: 700; }"
        ))
        page_header = QWidget(container)
        page_header.setStyleSheet(theme_qss("background: @surface; border: none;"))
        page_header_layout = QHBoxLayout(page_header)
        page_header_layout.setContentsMargins(8, 6, 8, 4)
        page_header_layout.addLayout(title_column, 1)
        page_header_layout.addWidget(header_tabs, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        cl.addWidget(page_header)
        
        tabs = QTabWidget()
        tabs.setObjectName("SettingsInnerTabs")
        tabs.setProperty("settingsTabs", True)
        if self._is_classic_appearance():
            tabs.setProperty("skipThemeTransform", False)
        tabs.setStyleSheet(theme_qss("QTabWidget::pane { border: none; background: transparent; }"))
        tabs.tabBar().hide()
        self.tabs = tabs
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setSpacing(10)
        general_layout.setContentsMargins(10, 10, 10, 4)
        right_click_tab = QWidget()
        right_click_layout = QVBoxLayout(right_click_tab)
        right_click_layout.setSpacing(16)
        right_click_layout.setContentsMargins(0, 0, 0, 0)

        theme_group = QGroupBox("Tema Seçimi")
        theme_group.setStyleSheet(self._card_qss())
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(8)

        lbl_theme = QLabel("Uygulama Teması:")
        lbl_theme.setStyleSheet(theme_qss("font-weight: 700; color: @text; border: none;"))

        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(ThemeManager.get_available_themes(self.db))
        self.cmb_theme.setStyleSheet(
            theme_qss(
                """
                QComboBox {
                    border: 1px solid @border;
                    border-radius: 10px;
                    padding: 8px 10px;
                    background: @surface_alt;
                    color: @text;
                    min-height: 36px;
                    min-width: 150px;
                }
                QComboBox:hover { border-color: @selection_bg; }
                """
            )
        )
        theme_layout.addWidget(lbl_theme)
        theme_layout.addWidget(self.cmb_theme)
        theme_hint = QLabel("Arka plan ve kart renk profillerini belirler.")
        theme_hint.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        theme_layout.addWidget(theme_hint)
        theme_layout.addStretch()
        general_layout.addWidget(theme_group)

        scale_group = QGroupBox("Yaz\u0131 ve \u0130kon Boyutu")
        scale_group.setStyleSheet(self._card_qss())
        scale_layout = QVBoxLayout(scale_group)
        scale_layout.setSpacing(6)

        scale_heading_row = QHBoxLayout()
        scale_heading = QLabel("Yaz\u0131 ve \u0130kon Boyutu")
        scale_heading.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 600; border: none;"))
        scale_heading_row.addWidget(scale_heading)
        scale_heading_row.addStretch(1)
        scale_layout.addLayout(scale_heading_row)

        scale_desc = QLabel(
            "Program genelindeki yaz\u0131lar\u0131 ve ikonlar\u0131 kademeli olarak b\u00fcy\u00fct\u00fcn veya k\u00fc\u00e7\u00fclt\u00fcn."
        )
        scale_desc.setWordWrap(True)
        scale_desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        scale_layout.addWidget(scale_desc)

        scale_row = QHBoxLayout()
        scale_row.setSpacing(12)
        small_label = QLabel("A")
        small_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
        large_label = QLabel("A")
        large_label.setStyleSheet(theme_qss("color: @text; font-size: 20px; font-weight: 800; border: none;"))
        self.lbl_interface_scale = QLabel("%100")
        self.lbl_interface_scale.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_interface_scale.setMinimumWidth(58)
        self.lbl_interface_scale.setStyleSheet(
            theme_qss(
                "background: rgba(59, 130, 246, 0.12); color: @accent; border: 1px solid @border; "
                "border-radius: 5px; padding: 4px 8px; font-weight: 800;"
            )
        )
        scale_heading_row.addWidget(self.lbl_interface_scale)

        self.interface_scale_steps = ThemeManager.INTERFACE_SCALE_STEPS
        self.sld_interface_scale = QSlider(Qt.Orientation.Horizontal)
        self.sld_interface_scale.setRange(0, len(self.interface_scale_steps) - 1)
        self.sld_interface_scale.setSingleStep(1)
        self.sld_interface_scale.setPageStep(1)
        self.sld_interface_scale.setTickInterval(1)
        self.sld_interface_scale.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.sld_interface_scale.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sld_interface_scale.setAccessibleName("Aray\u00fcz yaz\u0131 ve ikon boyutu")
        self.sld_interface_scale.setStyleSheet(
            theme_qss(
                """
                QSlider::groove:horizontal {
                    height: 8px;
                    border-radius: 4px;
                    background: @surface_alt;
                }
                QSlider::sub-page:horizontal {
                    border-radius: 4px;
                    background: @accent;
                }
                QSlider::handle:horizontal {
                    width: 24px;
                    height: 24px;
                    margin: -8px 0;
                    border-radius: 12px;
                    border: 2px solid @border;
                    background: @selection_text;
                }
                QSlider::handle:horizontal:hover { border-color: @accent; }
                """
            )
        )
        scale_row.addWidget(small_label)
        scale_row.addWidget(self.sld_interface_scale, 1)
        scale_row.addWidget(large_label)
        scale_layout.addLayout(scale_row)
        scale_legend = QHBoxLayout()
        scale_legend.addWidget(QLabel("%80"))
        scale_legend.addStretch(1)
        scale_legend.addWidget(QLabel("%100 (Varsay\u0131lan)"), 0, Qt.AlignmentFlag.AlignCenter)
        scale_legend.addStretch(1)
        scale_legend.addWidget(QLabel("%130"))
        for index in (0, 2, 4):
            scale_legend.itemAt(index).widget().setStyleSheet(
                theme_qss("color: @text_muted; font-size: 10px; border: none;")
            )
        scale_layout.addLayout(scale_legend)
        general_layout.addWidget(scale_group)

        menu_label_group = QGroupBox("Sol Men\u00fc G\u00f6r\u00fcn\u00fcm\u00fc")
        menu_label_group.setStyleSheet(self._card_qss())
        menu_label_layout = QVBoxLayout(menu_label_group)
        menu_label_layout.setSpacing(8)
        menu_label_heading = QLabel("Sol Men\u00fc G\u00f6r\u00fcn\u00fcm\u00fc")
        menu_label_heading.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 600; border: none;"))
        menu_label_layout.addWidget(menu_label_heading)
        menu_label_text = QLabel(
            "Men\u00fcde yaln\u0131zca simgeleri veya simge ile men\u00fc ad\u0131n\u0131 birlikte g\u00f6sterin."
        )
        menu_label_text.setWordWrap(True)
        menu_label_text.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        menu_label_layout.addWidget(menu_label_text)
        menu_label_layout.addStretch(1)
        menu_label_divider = QFrame()
        menu_label_divider.setFrameShape(QFrame.Shape.HLine)
        menu_label_divider.setStyleSheet(theme_qss("color: @border; background: @border; max-height: 1px;"))
        menu_label_layout.addWidget(menu_label_divider)
        menu_label_options = QHBoxLayout()
        menu_label_options.addStretch(1)
        self._menu_label_btn_group = QButtonGroup(self)
        self._menu_label_radio_btns = {}
        for value, title, tooltip in (
            ("icons", "\U0001f5bc  Sadece \u0130konlar", "Men\u00fc adlar\u0131 gizlenir."),
            ("labels", "\U0001f5bc  \u0130kon + Men\u00fc Ad\u0131", "Simgeler ve men\u00fc adlar\u0131 birlikte g\u00f6r\u00fcn\u00fcr."),
        ):
            radio = QRadioButton(title)
            radio.setToolTip(tooltip)
            radio.setStyleSheet(theme_qss(
                "QRadioButton { font-weight: 700; font-size: 12px; color: @text; }"
                "QRadioButton::indicator { width: 15px; height: 15px; }"
            ))
            radio.toggled.connect(
                lambda checked, selected=value: self._on_menu_label_mode_changed(checked, selected)
            )
            self._menu_label_btn_group.addButton(radio)
            self._menu_label_radio_btns[value] = radio
            menu_label_options.addWidget(radio)
        menu_label_layout.addLayout(menu_label_options)
        general_layout.addWidget(menu_label_group)

        self._scale_apply_timer = QTimer(self)
        self._scale_apply_timer.setSingleShot(True)
        self._scale_apply_timer.setInterval(120)
        self._scale_apply_timer.timeout.connect(self._apply_interface_scale_preview)
        self.sld_interface_scale.valueChanged.connect(self._on_interface_scale_changed)

        appearance_group = QGroupBox("Arayüz Görünümü")
        appearance_group.setStyleSheet(self._card_qss())
        appearance_lay = QVBoxLayout(appearance_group)
        appearance_lay.setSpacing(8)

        appearance_desc = QLabel(
            "Programın görsel yoğunluğunu seçin. Klasik görünüm daha düz, az efektli ve hızlı çalışmaya odaklıdır."
        )
        appearance_desc.setWordWrap(True)
        appearance_desc.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))
        density_label = QLabel("G\u00f6rsel Yo\u011funluk Modu:")
        density_label.setStyleSheet(theme_qss("font-size: 12px; font-weight: 600; color: @text_muted;"))
        appearance_lay.addWidget(density_label)
        appearance_desc.hide()

        self._appearance_btn_group = QButtonGroup(self)
        self._appearance_radio_btns = {}
        appearance_cards_lay = QVBoxLayout()
        appearance_cards_lay.setSpacing(6)

        appearance_options = [
            ("modern", "Modern", "Mevcut görsel zengin arayüz,\ngölge ve geniş boşluklar."),
            ("classic", "Klasik", "Daha sade, kompakt ve\ndüşük efektli arayüz."),
        ]
        for val, title, desc in appearance_options:
            card = QFrame()
            card.setObjectName("AppearanceModeCard")
            card.setStyleSheet(theme_qss(
                "QFrame#AppearanceModeCard { background: @surface_alt; border: 2px solid @border;"
                " border-radius: 12px; padding: 4px; }"
                "QFrame#AppearanceModeCard:hover { border-color: @accent; }"
            ))
            card_lay = QVBoxLayout(card)
            card_lay.setSpacing(4)
            card_lay.setContentsMargins(9, 8, 9, 8)

            rb = QRadioButton(title)
            rb.setStyleSheet(theme_qss(
                "QRadioButton { font-weight: 700; font-size: 13px; color: @text; }"
                "QRadioButton::indicator { width: 16px; height: 16px; }"
            ))
            rb.setProperty("appearance_value", val)
            rb.toggled.connect(lambda checked, v=val: self._on_appearance_mode_changed(checked, v))

            sub_lbl = QLabel(desc)
            sub_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
            sub_lbl.setWordWrap(True)

            card_lay.addWidget(rb)
            card_lay.addWidget(sub_lbl)

            self._appearance_btn_group.addButton(rb)
            self._appearance_radio_btns[val] = rb
            appearance_cards_lay.addWidget(card)

        appearance_lay.addLayout(appearance_cards_lay)
        general_layout.addWidget(appearance_group)

        # --- ComboBox Davranış Ayarı ---
        combo_group = QGroupBox("ComboBox Davranışı")
        combo_group.setStyleSheet(self._card_qss())
        combo_lay = QVBoxLayout(combo_group)
        combo_lay.setSpacing(8)

        combo_toggle_lay = QHBoxLayout()
        combo_text = QVBoxLayout()
        combo_head = QLabel("Tıklayınca otomatik açılır liste")
        combo_head.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        combo_sub = QLabel("Açıldığında, herhangi bir ComboBox\'a tıkladığınızda açılır liste otomatik açılır. Kapalıyken ok butonuna basarak açabilirsiniz.")
        combo_sub.setWordWrap(True)
        combo_sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        combo_text.addWidget(combo_head)
        combo_text.addWidget(combo_sub)

        self.toggle_combo_popup = AnimatedToggle()
        self.toggle_combo_popup.clicked.connect(self._on_combo_popup_toggle)

        combo_toggle_lay.addLayout(combo_text)
        combo_toggle_lay.addStretch()
        combo_toggle_lay.addWidget(self.toggle_combo_popup)
        combo_lay.addLayout(combo_toggle_lay)

        general_layout.addWidget(combo_group)

        color_group = QGroupBox("Tema Renkleri (Vurgu + Metin)")
        color_group.setStyleSheet(self._card_qss())
        color_layout = QVBoxLayout(color_group)

        info_lbl = QLabel(
            "Biçim boyası alanları: 1) Tema vurgu rengi, 2) Genel yazı rengi. "
            "Tema değiştiğinde tüm formlar ve tablolar bu renklere göre güncellenir."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 500;"))
        color_layout.addWidget(info_lbl)
        color_layout.addSpacing(8)

        self.preset_accent_colors = [
            "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#64748B", "#14B8A6", "#0EA5E9"
        ]
        self.preset_text_colors = [
            "#0F172A", "#1E293B", "#334155", "#475569", "#E2E8F0", "#F1F5F9", "#F8FAFC", "#FFFFFF", "#FACC15"
        ]

        color_layout.addWidget(self._build_color_row(
            "1) Tema vurgu rengi (butonlar/seçimler)",
            self.preset_accent_colors,
            "Vurgu rengi seç",
            lambda value: self.apply_custom_color(value, "accent"),
            lambda: self.select_custom_color("accent"),
            lambda: self.apply_custom_color("", "accent"),
        ))
        color_layout.addSpacing(8)

        color_layout.addWidget(self._build_color_row(
            "2) Yazı rengi (metinler/başlıklar)",
            self.preset_text_colors,
            "Metin rengi seç",
            lambda value: self.apply_custom_color(value, "text"),
            lambda: self.select_custom_color("text"),
            lambda: self.apply_custom_color("", "text"),
        ))
        general_layout.addWidget(color_group)

        # --- Navigasyon Menüsü Ayarı ---
        nav_group = QGroupBox("Navigasyon Menüsü")
        nav_group.setStyleSheet(self._card_qss())
        nav_lay = QVBoxLayout(nav_group)
        nav_lay.setSpacing(8)

        nav_desc = QLabel("Uygulamanın navigasyon düzenini seçin:")
        nav_desc.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))
        nav_lay.addWidget(nav_desc)

        self._nav_btn_group = QButtonGroup(self)
        nav_cards_lay = QVBoxLayout()
        nav_cards_lay.setSpacing(6)

        nav_options = [
            ("sol_menu",   "🗂  Sol Menü",    "Klasik sol kenar çubuğu\nnavigasyonu kullanılır."),
            ("ust_bar",    "↑  Üst Bar",     "Üst sekmeli navigasyon.\nSol menü gizlenir."),
            ("her_ikisi",  "⊞  Her İkisi",   "Sol menü + üst sekme\nçubuğu birlikte aktif."),
        ]
        self._nav_radio_btns = {}
        for val, title, desc in nav_options:
            card = QFrame()
            card.setObjectName("NavModeCard")
            card.setStyleSheet(theme_qss(
                "QFrame#NavModeCard { background: @surface_alt; border: 2px solid @border;"
                " border-radius: 12px; padding: 4px; }"
                "QFrame#NavModeCard:hover { border-color: @accent; }"
            ))
            card_lay = QVBoxLayout(card)
            card_lay.setSpacing(4)
            card_lay.setContentsMargins(14, 12, 14, 12)

            rb = QRadioButton(title)
            rb.setStyleSheet(theme_qss(
                "QRadioButton { font-weight: 700; font-size: 13px; color: @text; }"
                "QRadioButton::indicator { width: 16px; height: 16px; }"
            ))
            rb.setProperty("nav_value", val)
            rb.toggled.connect(lambda checked, v=val: self._on_nav_mode_changed(checked, v))

            sub_lbl = QLabel(desc)
            sub_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
            sub_lbl.setWordWrap(True)

            card_lay.addWidget(rb)
            card_lay.addWidget(sub_lbl)

            self._nav_btn_group.addButton(rb)
            self._nav_radio_btns[val] = rb
            nav_cards_lay.addWidget(card)

        nav_lay.addLayout(nav_cards_lay)
        general_layout.addWidget(nav_group)

        display_group = QGroupBox("Ekran Yerleşimi")
        display_group.setStyleSheet(self._card_qss())
        display_lay = QVBoxLayout(display_group)
        display_lay.setSpacing(12)

        display_desc = QLabel("Laptop ve büyük monitör için arayüz sıkışma davranışını seçin:")
        display_desc.setWordWrap(True)
        display_desc.setStyleSheet(theme_qss("font-weight: 700; color: @text; font-size: 13px;"))
        display_lay.addWidget(display_desc)

        self.cmb_display_profile = QComboBox()
        self.cmb_display_profile.addItem("Otomatik", "auto")
        self.cmb_display_profile.addItem("Laptop ekranı (14-15 inç)", "laptop")
        self.cmb_display_profile.addItem("Büyük monitör", "desktop")
        self.cmb_display_profile.setMinimumHeight(38)
        self.cmb_display_profile.setStyleSheet(theme_qss(
            "QComboBox { background:@surface_alt; color:@text; border:1px solid @border; "
            "border-radius:10px; padding:8px 10px; font-weight:700; }"
        ))
        self.cmb_display_profile.currentIndexChanged.connect(self._on_display_profile_changed)
        display_lay.addWidget(self.cmb_display_profile)
        general_layout.addWidget(display_group)

        ticker_group = QGroupBox("Kayan Yazı ve Duyuru Sistemi")
        ticker_group.setStyleSheet(self._card_qss())
        tl = QVBoxLayout(ticker_group)
        tl.setSpacing(8)

        feat_lay = QHBoxLayout()
        fl_text = QVBoxLayout()
        fl_head = QLabel("Program özelliklerini kayan yazıda göster")
        fl_head.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        fl_sub = QLabel("Kullanım ipuçları ve kısa yardım bilgilerini duyuru şeridinde döndürür.")
        fl_sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        fl_text.addWidget(fl_head)
        fl_text.addWidget(fl_sub)

        self.toggle_features = AnimatedToggle()
        self.toggle_features.clicked.connect(self.save_data)

        feat_lay.addLayout(fl_text)
        feat_lay.addStretch()
        feat_lay.addWidget(self.toggle_features)
        tl.addLayout(feat_lay)

        self.inp_ticker = QTextEdit()
        self.inp_ticker.setPlaceholderText("Kendi duyuru metninizi buraya yazın...")
        self.inp_ticker.setFixedHeight(80)
        self.inp_ticker.setStyleSheet(
            theme_qss(
                """
                QTextEdit {
                    border: 1px solid @border;
                    border-radius: 10px;
                    padding: 10px;
                    font-size: 13px;
                    background: @surface_alt;
                    color: @text;
                }
                """
            )
        )
        tl.addWidget(self.inp_ticker)

        btn_update_lay = QHBoxLayout()
        btn_update_lay.addStretch()
        self.btn_refresh_ticker = QPushButton("Duyuruları hemen güncelle")
        self.btn_refresh_ticker.setFixedSize(220, 38)
        self.btn_refresh_ticker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh_ticker.setStyleSheet(self._soft_button_qss())
        self.btn_refresh_ticker.clicked.connect(self.save_data)
        btn_update_lay.addWidget(self.btn_refresh_ticker)
        tl.addLayout(btn_update_lay)
        general_layout.addWidget(ticker_group)

        menu_group = QGroupBox()
        menu_group.setStyleSheet(self._card_qss())
        ml = QVBoxLayout(menu_group)
        ml.setSpacing(16)
        menu_title = QLabel("FARE SA\u011e TU\u015e MEN\u00dc Y\u00d6NET\u0130M\u0130")
        menu_title.setStyleSheet(theme_qss("font-size: 18px; font-weight: 800; color: @accent;"))
        ml.addWidget(menu_title)
        menu_divider = QFrame()
        menu_divider.setFrameShape(QFrame.Shape.HLine)
        menu_divider.setStyleSheet(theme_qss("color: @border; background: @border; max-height: 1px;"))
        ml.addWidget(menu_divider)

        rc_lay = QHBoxLayout()
        rc_text = QVBoxLayout()
        rc_head = QLabel("Uygulama genelinde sağ tık menüsünü etkinleştir")
        rc_head.setStyleSheet(theme_qss("font-size: 16px; font-weight: 700; color: @text;"))
        rc_sub = QLabel("Kapatıldığında tablolardaki hızlı işlem menüleri devre dışı kalır.")
        rc_sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        rc_text.addWidget(rc_head)
        rc_text.addWidget(rc_sub)

        self.toggle_rc = AnimatedToggle()
        self.toggle_rc.clicked.connect(self.on_rc_toggle)

        rc_lay.addLayout(rc_text)
        rc_lay.addStretch()
        rc_lay.addWidget(self.toggle_rc)
        ml.addLayout(rc_lay)
        right_click_layout.addWidget(menu_group)

        page_group = QGroupBox()
        page_group.setStyleSheet(self._card_qss())
        page_group_layout = QVBoxLayout(page_group)
        page_group_layout.setSpacing(12)
        page_header = QHBoxLayout()
        page_title = QLabel("Men\u00fcn\u00fcn aktif oldu\u011fu sayfalar:")
        page_title.setStyleSheet(theme_qss("font-size: 15px;"))
        page_header.addWidget(page_title)
        page_header.addStretch(1)
        self.toggle_all_pages_button = QPushButton("T\u00fcm\u00fcn\u00fc Se\u00e7 / Kald\u0131r")
        self.toggle_all_pages_button.setStyleSheet(theme_qss(
            "QPushButton { background: transparent; color: @accent; border: 0; "
            "font-size: 13px; font-weight: 700; padding: 4px; } "
            "QPushButton:hover { color: @text; }"
        ))
        self.toggle_all_pages_button.clicked.connect(self._toggle_all_pages)
        page_header.addWidget(self.toggle_all_pages_button)
        page_group_layout.addLayout(page_header)
        page_list_frame = QFrame()
        page_list_frame.setStyleSheet(theme_qss("background: transparent; border: none; padding: 0;"))
        pll = QGridLayout(page_list_frame)
        pll.setContentsMargins(0, 0, 0, 0)
        pll.setHorizontalSpacing(16)
        pll.setVerticalSpacing(12)
        pll.setAlignment(Qt.AlignmentFlag.AlignTop)
        pll.setColumnStretch(0, 1)
        pll.setColumnStretch(1, 1)

        self.page_toggles = {}
        pages = [
            ("Dashboard (Son İşlemler)", "rc_dashboard"),
            ("Stok & Envanter", "rc_stock"),
            ("Servis Formu Sayfası", "rc_service_form"),
            ("Duyurular", "rc_announcements"),
            ("Personeller", "rc_personnel"),
            ("Bankalar", "rc_bank"),
            ("Bakım Sözleşmeleri", "rc_contracts"),
            ("Proje Yönetimi", "rc_projects"),
            ("Emanet (Konsinye) Cihazlar", "rc_loaner"),
            ("M\u00fc\u015fteri & Cari Listesi", "rc_customers"),
            ("Kasa \u0130\u015flemleri", "rc_accounting"),
            ("Randevu Takvimi", "rc_appointments"),
            ("Bilgi Bankas\u0131", "rc_knowledge_base"),
            ("Hizmetler", "rc_services"),
            ("Hat\u0131rlat\u0131c\u0131lar", "rc_reminders"),
            ("\u0130\u015f/Servis Takip Raporlar\u0131", "rc_job_service"),
            ("Lojistik Garanti Y\u00f6netimi", "rc_logistics"),
        ]

        for i, (name, setting_key) in enumerate(pages):
            toggle = AnimatedToggle()
            toggle.setFixedSize(45, 24)
            toggle.clicked.connect(self.save_data)
            self.page_toggles[setting_key] = toggle

            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(theme_qss("color: @text; font-size: 15px; font-weight: 600;"))
            card = QFrame()
            card.setObjectName("RightClickPageCard")
            card.setStyleSheet(theme_qss(
                "QFrame#RightClickPageCard { background: @surface_alt; border: 1px solid @border; "
                "border-radius: 8px; }"
            ))
            card.setMinimumHeight(52)
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(14, 8, 14, 8)
            card_layout.setSpacing(12)
            card_layout.addWidget(toggle)
            card_layout.addWidget(name_lbl, 1)
            pll.addWidget(card, i % 9, i // 9)

        page_group_layout.addWidget(page_list_frame)
        right_click_layout.addWidget(page_group)
        right_click_layout.addStretch(1)

        while general_layout.count():
            general_layout.takeAt(0)

        settings_grid = QGridLayout()
        settings_grid.setContentsMargins(0, 0, 0, 0)
        settings_grid.setHorizontalSpacing(10)
        settings_grid.setVerticalSpacing(10)
        general_layout.addLayout(settings_grid)
        left_column = QWidget(general_tab)
        left_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        right_column = QWidget(general_tab)
        right_column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        theme_appearance_row = QWidget(general_tab)
        theme_appearance_layout = QVBoxLayout(theme_appearance_row)
        theme_appearance_layout.setContentsMargins(0, 0, 0, 0)
        theme_appearance_layout.setSpacing(8)
        theme_appearance_row.setMinimumHeight(0)
        for group in (theme_group, appearance_group):
            group.setFlat(True)
            group.setTitle("")
            group.setStyleSheet(theme_qss(
                "QGroupBox { border: none; margin: 0; padding: 0; background: transparent; } "
                "QLabel { color: @text; background: transparent; border: none; }"
            ))
            group.layout().setContentsMargins(0, 0, 0, 0)
        theme_appearance_layout.addWidget(theme_group, 1)
        theme_appearance_layout.addWidget(appearance_group, 2)
        left_layout.addWidget(self._reference_section(
            "Tema Se\u00e7imi & Aray\u00fcz G\u00f6r\u00fcn\u00fcm\u00fc", "#3b82f6",
            "Genel sistem \u015fablonu", theme_appearance_row
        ))

        scale_navigation_row = QWidget(general_tab)
        scale_navigation_layout = QVBoxLayout(scale_navigation_row)
        scale_navigation_layout.setContentsMargins(0, 0, 0, 0)
        scale_navigation_layout.setSpacing(8)
        scale_navigation_row.setMinimumHeight(0)
        for group in (scale_group, menu_label_group):
            group.setTitle("")
            group.setStyleSheet(theme_qss(
                "QGroupBox { background: @surface_alt; border: 1px solid @border; "
                "border-radius: 9px; margin: 0; padding: 14px; } "
                "QLabel { color: @text; background: transparent; border: none; }"
            ))
        scale_navigation_layout.addWidget(scale_group, 1)
        scale_navigation_layout.addWidget(menu_label_group, 1)
        left_layout.addWidget(self._reference_section(
            "Yaz\u0131, \u0130kon Boyutu ve Sol Men\u00fc G\u00f6r\u00fcn\u00fcm\u00fc", "#22d3ee",
            "\u00d6l\u00e7eklendirme", scale_navigation_row
        ))

        color_group.setTitle("")
        color_group.setFlat(True)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_group.setStyleSheet(theme_qss(
            "QGroupBox { border: none; margin: 0; padding: 0; background: transparent; } "
            "QLabel { color: @text; background: transparent; border: none; }"
        ))
        left_layout.addWidget(self._reference_section(
            "Tema Renkleri (Vurgu + Metin)", "#34d399", "Bi\u00e7im Boyas\u0131", color_group
        ))

        navigation_content = QWidget(general_tab)
        navigation_content_layout = QVBoxLayout(navigation_content)
        navigation_content_layout.setContentsMargins(0, 0, 0, 0)
        navigation_content_layout.setSpacing(8)
        nav_group.setTitle("")
        nav_group.setStyleSheet(theme_qss(
            "QGroupBox { border: none; margin: 0; padding: 0; background: transparent; } "
            "QLabel { color: @text; background: transparent; border: none; }"
        ))
        nav_group.layout().setContentsMargins(0, 0, 0, 0)
        navigation_content_layout.addWidget(nav_group)
        display_combo_row = QWidget(navigation_content)
        display_combo_layout = QVBoxLayout(display_combo_row)
        display_combo_layout.setContentsMargins(0, 0, 0, 0)
        display_combo_layout.setSpacing(8)
        for group in (combo_group, display_group):
            group.setTitle("")
            group.setStyleSheet(theme_qss(
                "QGroupBox { background: @surface_alt; border: 1px solid @border; "
                "border-radius: 9px; margin: 0; padding: 14px; } "
                "QLabel { color: @text; background: transparent; border: none; }"
            ))
        display_combo_layout.addWidget(combo_group, 1)
        display_combo_layout.addWidget(display_group, 1)
        navigation_content_layout.addWidget(display_combo_row)
        right_layout.addWidget(self._reference_section(
            "Navigasyon D\u00fczeni & Pencere Davran\u0131\u015f\u0131", "#818cf8",
            "Pencere Mimarisi", navigation_content
        ))

        right_layout.addWidget(self._reference_section(
            "Kayan Yaz\u0131 ve Duyuru Sistemi", "#fbbf24", "", ticker_group
        ))
        right_layout.addStretch(1)
        settings_grid.addWidget(left_column, 0, 0)
        settings_grid.addWidget(right_column, 0, 1)
        settings_grid.setColumnStretch(0, 1)
        settings_grid.setColumnStretch(1, 1)

        tabs.addTab(general_tab, "Genel")
        tabs.addTab(right_click_tab, "Fare Sağ Tuş Yönetimi")
        header_tabs.addTab("Genel")
        header_tabs.addTab("Fare Sa\u011f Tu\u015f Y\u00f6netimi")

        def sync_header_layout(index):
            if index == 1:
                page_header_layout.removeWidget(header_tabs)
                page_header_layout.setContentsMargins(8, 6, 8, 4)
                title_column.setSpacing(10)
                title_column.addWidget(header_tabs, 0, Qt.AlignmentFlag.AlignLeft)
                config_badge.hide()
                description.hide()
            else:
                title_column.removeWidget(header_tabs)
                page_header_layout.setContentsMargins(8, 6, 8, 23)
                page_header_layout.addWidget(
                    header_tabs, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                title_column.setSpacing(2)
                config_badge.show()
                description.show()

        tabs.currentChanged.connect(sync_header_layout)
        header_tabs.currentChanged.connect(tabs.setCurrentIndex)
        tabs.currentChanged.connect(header_tabs.setCurrentIndex)
        sync_header_layout(tabs.currentIndex())
        cl.addWidget(tabs)
        cl.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.btn_save = QPushButton("Tüm değişiklikleri uygula")
        self.btn_save.setFixedHeight(44)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(
            theme_qss(
                """
                QPushButton {
                    background-color: @accent;
                    color: @selection_text;
                    border-radius: 12px;
                    font-weight: 800;
                    border: none;
                    font-size: 15px;
                }
                QPushButton:hover { background-color: @accent_hover; }
                QPushButton:pressed { background-color: @accent_pressed; }
                """
            )
        )
        self.btn_save.clicked.connect(self.save_data)
        layout.addWidget(self.btn_save)

    def _toggle_all_pages(self):
        target_state = not all(toggle.isChecked() for toggle in self.page_toggles.values())
        for toggle in self.page_toggles.values():
            toggle.blockSignals(True)
            toggle.setChecked(target_state)
            toggle.blockSignals(False)
        self.save_data()

    def _build_color_row(self, title, colors, custom_btn_text, on_color_click, on_custom_click, on_reset_click):
        wrapper = QFrame()
        wrapper.setObjectName("ThemeColorPresetRow")
        wrapper.setStyleSheet(theme_qss(
            "QFrame#ThemeColorPresetRow { background: @surface_alt; border: 1px solid @border; "
            "border-radius: 9px; }"
        ))
        row_layout = QVBoxLayout(wrapper)
        row_layout.setContentsMargins(14, 12, 14, 12)
        row_layout.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(theme_qss("font-weight: 700; color: @text;"))
        row_layout.addWidget(title_lbl)

        actions = QHBoxLayout()
        actions.setSpacing(10)

        for hex_code in colors:
            btn = QPushButton()
            btn.setFixedSize(34, 34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            base_border = "#E2E8F0" if hex_code.upper() in {"#FFFFFF", "#F8FAFC", "#F1F5F9"} else "transparent"
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {hex_code};
                    border-radius: 17px;
                    border: 2px solid {base_border};
                }}
                QPushButton:hover {{ border: 2px solid {tc('selection_bg', default='#3B82F6')}; }}
                """
            )
            btn.clicked.connect(lambda checked=False, c=hex_code: on_color_click(c))
            actions.addWidget(btn)

        actions.addSpacing(16)

        btn_custom = QPushButton(custom_btn_text)
        btn_custom.setFixedSize(180, 34)
        btn_custom.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_custom.setStyleSheet(self._soft_button_qss())
        btn_custom.clicked.connect(on_custom_click)
        actions.addWidget(btn_custom)

        btn_reset = QPushButton("Varsayılana dön")
        btn_reset.setFixedSize(130, 34)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.setStyleSheet(theme_qss("QPushButton { background: transparent; color: @danger; border: none; text-decoration: underline; font-weight: 600; }"))
        btn_reset.clicked.connect(on_reset_click)
        actions.addWidget(btn_reset)

        actions.addStretch()
        row_layout.addLayout(actions)
        return wrapper

    def on_rc_toggle(self):
        is_enabled = self.toggle_rc.isChecked()
        for toggle in self.page_toggles.values():
            toggle.setEnabled(is_enabled)
            toggle.setCursor(Qt.CursorShape.PointingHandCursor if is_enabled else Qt.CursorShape.ForbiddenCursor)
        self.save_data()

    def _on_combo_popup_toggle(self):
        """ComboBox otomatik popup ayarını kaydeder ve anında uygular."""
        self.save_data()

    def _on_appearance_mode_changed(self, checked: bool, val: str):
        if not checked:
            return
        mode = AppearanceModeManager.normalize(val)
        self.db.set_setting(AppearanceModeManager.SETTING_KEY, mode)
        if self.main_window and hasattr(self.main_window, "apply_appearance_mode"):
            self.main_window.apply_appearance_mode(mode)
        self._refresh_appearance_cards()
        self.apply_theme_styles()

    def _refresh_appearance_cards(self):
        for radio in self._appearance_radio_btns.values():
            card = radio.parentWidget()
            border_color = "@accent" if radio.isChecked() else "@border"
            card.setStyleSheet(theme_qss(
                "QFrame#AppearanceModeCard { background: @surface_alt; border: 2px solid "
                f"{border_color}; border-radius: 12px; padding: 4px; }}"
                "QFrame#AppearanceModeCard:hover { border-color: @accent; }"
            ))

    def apply_theme_styles(self):
        if self._is_classic_appearance():
            self.setProperty("skipThemeTransform", False)
            if hasattr(self, "tabs"):
                self.tabs.setProperty("skipThemeTransform", False)
        self.setStyleSheet("""
            QWidget#BackgroundSettingsWidget {
                background: #FFFFFF;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
                border: none;
            }
        """ if self._is_classic_appearance() else "")
        if hasattr(self, "tabs"):
            self.tabs.setStyleSheet(self._tabs_qss())
        if hasattr(self, "scroll_area"):
            self.scroll_area.setStyleSheet(
                "QScrollArea { background: #FFFFFF; border: none; } QScrollArea > QWidget > QWidget { background: #FFFFFF; }"
                if self._is_classic_appearance()
                else theme_qss("QScrollArea { background: @surface; border: none; } QScrollArea > QWidget > QWidget { background: @surface; }")
            )
        if hasattr(self, "container"):
            self.container.setStyleSheet(
                "QWidget { background: #FFFFFF; color: #111827; }"
                if self._is_classic_appearance()
                else theme_qss("QWidget { background: @surface; }")
            )
        if hasattr(self, "title_label"):
            self.title_label.setStyleSheet(
                "color: #111827; margin-bottom: 4px; background: transparent; border: none;"
                if self._is_classic_appearance()
                else theme_qss("color: @text; margin-bottom: 10px;")
            )
        layout = self.layout()
        if layout:
            margin = 10 if self._is_classic_appearance() else 24
            layout.setContentsMargins(margin, margin, margin, margin)
            layout.setSpacing(12 if self._is_classic_appearance() else 16)
        for group in self.findChildren(QGroupBox):
            group.setStyleSheet(self._card_qss())

    def _on_nav_mode_changed(self, checked: bool, val: str):
        """Navigasyon modu radio button değişince - sadece seçilen (checked=True) için uygula."""
        if not checked:
            return
        self.db.set_setting("nav_mode", val)
        if self.main_window and hasattr(self.main_window, "apply_nav_mode"):
            self.main_window.apply_nav_mode(val)

    def _on_menu_label_mode_changed(self, checked: bool, value: str):
        if not checked:
            return
        self.db.set_setting("side_menu_label_mode", value)
        side_menu = getattr(getattr(self.main_window, "app_sidebar", None), "side_menu", None)
        if side_menu and hasattr(side_menu, "set_menu_label_mode"):
            side_menu.set_menu_label_mode(value, persist=False)

    def _on_display_profile_changed(self):
        self.save_data()
        if self.main_window and hasattr(self.main_window, "apply_display_profile"):
            self.main_window.apply_display_profile()

    def _wire_ui_signals(self):
        self.cmb_theme.currentIndexChanged.connect(self._on_theme_preview_changed)
        self.toggle_combo_popup.toggled.connect(self.save_data)
        self.toggle_features.toggled.connect(self.save_data)
        self.toggle_rc.toggled.connect(self.save_data)

    def _on_theme_preview_changed(self, _index=None):
        selected_theme = ThemeManager.normalize_theme_name(self.cmb_theme.currentText())
        if self.main_window and hasattr(self.main_window, "apply_theme"):
            self.main_window.apply_theme(selected_theme)
        else:
            self.db.set_setting("color_theme_full", selected_theme)

    def load_data(self):
        self.inp_ticker.setPlainText(
            self.db.get_setting(
                "ticker_text",
                "AYEC Pro Teknik Servis Yönetimi | Hızlı Kayıt: F5 | Ürün Bul: Ctrl+F",
            )
        )

        current_theme = ThemeManager.normalize_theme_name(self.db.get_setting("color_theme_full", "Koyu Mavi"))
        idx_theme = self.cmb_theme.findText(current_theme)
        if idx_theme >= 0:
            self.cmb_theme.setCurrentIndex(idx_theme)

        scale_percent = ThemeManager.normalize_interface_scale(
            self.db.get_setting(ThemeManager.INTERFACE_SCALE_SETTING, "100")
        )
        scale_index = self.interface_scale_steps.index(scale_percent)
        self.sld_interface_scale.blockSignals(True)
        self.sld_interface_scale.setValue(scale_index)
        self.sld_interface_scale.blockSignals(False)
        self.lbl_interface_scale.setText(f"%{scale_percent}")

        appearance_mode = AppearanceModeManager.current(self.db)
        if appearance_mode in self._appearance_radio_btns:
            self._appearance_radio_btns[appearance_mode].setChecked(True)
        else:
            self._appearance_radio_btns[AppearanceModeManager.MODERN].setChecked(True)

        self.toggle_rc.setChecked(self.db.get_setting("enable_right_click", "1") == "1")
        self.toggle_features.setChecked(self.db.get_setting("show_feature_info", "1") == "1")

        # ComboBox auto-popup ayarı
        combo_popup_val = self.db.get_setting("combo_auto_popup", "0") == "1"
        self.toggle_combo_popup.setChecked(combo_popup_val)
        ThemeManager._combo_auto_popup_enabled = combo_popup_val

        # Navigasyon modu ayarı
        nav_mode = self.db.get_setting("nav_mode", "sol_menu")
        if nav_mode in self._nav_radio_btns:
            self._nav_radio_btns[nav_mode].setChecked(True)
        else:
            self._nav_radio_btns["sol_menu"].setChecked(True)

        menu_label_mode = self.db.get_setting("side_menu_label_mode", "labels")
        radio_signal_blockers = [
            QSignalBlocker(radio) for radio in self._menu_label_radio_btns.values()
        ]
        if menu_label_mode in self._menu_label_radio_btns:
            self._menu_label_radio_btns[menu_label_mode].setChecked(True)
        else:
            self._menu_label_radio_btns["labels"].setChecked(True)
        del radio_signal_blockers

        display_profile = self.db.get_setting("display_profile", "auto")
        idx_display = self.cmb_display_profile.findData(display_profile)
        if idx_display < 0:
            idx_display = 0
        self.cmb_display_profile.blockSignals(True)
        self.cmb_display_profile.setCurrentIndex(idx_display)
        self.cmb_display_profile.blockSignals(False)

        is_global_enabled = self.toggle_rc.isChecked()
        for key, toggle in self.page_toggles.items():
            toggle.setChecked(self.db.get_setting(key, "1") == "1")
            toggle.setEnabled(is_global_enabled)
            toggle.setCursor(Qt.CursorShape.PointingHandCursor if is_global_enabled else Qt.CursorShape.ForbiddenCursor)
        self._refresh_appearance_cards()

    def save_data(self):
        selected_theme = ThemeManager.normalize_theme_name(self.cmb_theme.currentText())
        old_theme = ThemeManager.normalize_theme_name(self.db.get_setting("color_theme_full", "Koyu Mavi"))
        if selected_theme != old_theme:
            self.db.set_setting("color_theme_full", selected_theme)
            if self.main_window and hasattr(self.main_window, "apply_theme"):
                self.main_window.apply_theme(selected_theme)

        self.db.set_setting("ticker_text", self.inp_ticker.toPlainText())
        self.db.set_setting("enable_right_click", "1" if self.toggle_rc.isChecked() else "0")
        self.db.set_setting("show_feature_info", "1" if self.toggle_features.isChecked() else "0")
        self.db.set_setting("combo_auto_popup", "1" if self.toggle_combo_popup.isChecked() else "0")
        self.db.set_setting("display_profile", self.cmb_display_profile.currentData() or "auto")
        scale_percent = self.interface_scale_steps[self.sld_interface_scale.value()]
        self.db.set_setting(ThemeManager.INTERFACE_SCALE_SETTING, str(scale_percent))
        ThemeManager.set_interface_scale(scale_percent, QApplication.instance())
        selected_appearance = AppearanceModeManager.MODERN
        for val, rb in self._appearance_radio_btns.items():
            if rb.isChecked():
                selected_appearance = AppearanceModeManager.normalize(val)
                break
        self.db.set_setting(AppearanceModeManager.SETTING_KEY, selected_appearance)

        # Navigasyon modu kaydet
        for val, rb in self._nav_radio_btns.items():
            if rb.isChecked():
                self.db.set_setting("nav_mode", val)
                break
        for value, radio in self._menu_label_radio_btns.items():
            if radio.isChecked():
                self.db.set_setting("side_menu_label_mode", value)
                break
        ThemeManager._combo_auto_popup_enabled = self.toggle_combo_popup.isChecked()
        if self.main_window and hasattr(self.main_window, "apply_appearance_mode"):
            self.main_window.apply_appearance_mode(selected_appearance)

        for key, toggle in self.page_toggles.items():
            self.db.set_setting(key, "1" if toggle.isChecked() else "0")

        if self.main_window:
            self.main_window.show_notification("Görünüm ve menü ayarları güncellendi.", "success")
            for page in self.main_window.pages.values():
                if hasattr(page, "ticker"):
                    page.ticker.update_content()
                if hasattr(page, "marquee"):
                    page.marquee.setText(self.inp_ticker.toPlainText())

            if hasattr(self.main_window, "refresh_side_menu"):
                self.main_window.refresh_side_menu()
            if hasattr(self.main_window, "top_nav") and hasattr(self.main_window.top_nav, "refresh"):
                self.main_window.top_nav.refresh()

    def _on_interface_scale_changed(self, index):
        percent = self.interface_scale_steps[index]
        self.lbl_interface_scale.setText(f"%{percent}")
        self._scale_apply_timer.start()

    def _apply_interface_scale_preview(self):
        percent = self.interface_scale_steps[self.sld_interface_scale.value()]
        self.db.set_setting(ThemeManager.INTERFACE_SCALE_SETTING, str(percent))
        ThemeManager.set_interface_scale(percent, QApplication.instance())

    def apply_custom_color(self, hex_color, color_type="accent"):
        if color_type == "accent":
            if hex_color:
                self.db.set_setting("custom_accent_color", hex_color)
                ThemeManager.set_custom_accent_color(hex_color)
            else:
                self.db.set_setting("custom_accent_color", "")
                ThemeManager.set_custom_accent_color(None)
        else:
            if hex_color:
                self.db.set_setting("custom_text_color", hex_color)
                ThemeManager.set_custom_text_color(hex_color)
            else:
                self.db.set_setting("custom_text_color", "")
                ThemeManager.set_custom_text_color(None)

        if self.main_window and hasattr(self.main_window, "apply_theme"):
            self.main_window.apply_theme(self.cmb_theme.currentText())
            if hasattr(self.main_window, "show_notification"):
                if hex_color:
                    msg = "Özel vurgu rengi uygulandı." if color_type == "accent" else "Özel metin rengi uygulandı."
                    self.main_window.show_notification(msg, "success")
                else:
                    msg = "Vurgu rengi varsayılana döndü." if color_type == "accent" else "Metin rengi varsayılana döndü."
                    self.main_window.show_notification(msg, "info")

    def select_custom_color(self, color_type="accent"):
        key = "custom_accent_color" if color_type == "accent" else "custom_text_color"
        current_hex = self.db.get_setting(key, "")
        initial = QColor(current_hex) if current_hex else QColor(tc("text", default="#1F2937"))
        caption = "Özel tema vurgu rengi seç" if color_type == "accent" else "Özel metin rengi seç"
        color = QColorDialog.getColor(initial, self, caption)
        if color.isValid():
            self.apply_custom_color(color.name(), color_type)
