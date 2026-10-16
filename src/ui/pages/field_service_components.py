from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon


class FieldMapOverview(QFrame):
    """Header actions and field-operation summary metrics."""

    ACTIONS = (
        ("field_action_new_task", "+ Yeni Saha G\u00f6revi Ata", "create_task", "accent"),
        ("field_action_optimize_route", "Rota Optimizasyonu (AI)", "optimize_route", "surface_alt"),
        ("field_action_live_traffic", "Canl\u0131 Trafik", "toggle_traffic", "surface_alt"),
        ("field_action_share_location", "WhatsApp H\u0131zl\u0131 Payla\u015f", "share_location", "surface_alt"),
        ("field_action_map_mode", "3D Vekt\u00f6r", "toggle_map_mode", "surface_alt"),
    )
    METRICS = (
        ("SAHADAK\u0130 EK\u0130PLER", "finance_text", "truck"),
        ("BUG\u00dcNK\u00dc SAHA G\u00d6REVLER\u0130", "finance_text", "check"),
        ("ORTALAMA VARI\u015e S\u00dcRES\u0130", "finance_secondary", "clock"),
        ("AC\u0130L SAHA \u00c7A\u011eRISI", "finance_tertiary", "warning"),
    )

    def __init__(self, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("FieldOverview")
        self.setStyleSheet(theme_qss(
            "QFrame#FieldOverview{background:@finance_canvas;border:none;}"
            "QLabel{background:transparent;border:none;}"
        ))
        self.metric_cards = []
        self.metric_values = []
        self.metric_notes = []
        self.action_buttons = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.subtitle = QLabel("")
        self.subtitle.hide()
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 4, 0)
        header.setSpacing(10)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_block = QHBoxLayout()
        title_block.setContentsMargins(0, 0, 0, 0)
        title_block.setSpacing(8)
        brand = QPushButton("\u25a3 AYEC PRO")
        brand.setFixedHeight(32)
        brand.setCursor(Qt.CursorShape.PointingHandCursor)
        brand.setStyleSheet(theme_qss(
            "QPushButton{background:transparent;color:@text;border:none;padding:0;"
            "font-size:18.75px;font-weight:900;text-align:left;}"
        ))
        home_callback = actions.get("home")
        if home_callback:
            brand.clicked.connect(home_callback)
        title_block.addWidget(brand)
        breadcrumb = QLabel("SERV\u0130S OPERASYON  /  SAHA Y\u00d6NET\u0130M\u0130  /  AYEC-FIELD-RADAR")
        breadcrumb.setFixedHeight(32)
        breadcrumb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.breadcrumb = breadcrumb
        breadcrumb.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:13.75px;font-weight:700;"))
        title_block.addWidget(breadcrumb)
        header.addLayout(title_block)
        header.addStretch(1)
        self.live_teams_label = QLabel("GPS CANLI VER\u0130 AKI\u015eI")
        self.live_teams_label.setFixedHeight(32)
        self.live_teams_label.setStyleSheet(theme_qss("color:@finance_secondary;font-size:13.75px;font-weight:800;"))
        header.addWidget(self.live_teams_label)
        action_widths = {
            "create_task": 158,
            "optimize_route": 210,
            "toggle_traffic": 116,
            "share_location": 166,
            "toggle_map_mode": 106,
        }
        for object_name, caption, action_name, accent in self.ACTIONS:
            button = QPushButton(caption)
            button.setObjectName(object_name)
            button.setFixedSize(action_widths[action_name], 32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if accent == "accent":
                button_style = (
                    "QPushButton{background:@accent;color:@accent_foreground;"
                    "border:1px solid @border;border-radius:6px;padding:0 8px;"
                    "font-size:15px;font-weight:700;}"
                )
            else:
                button_style = (
                    "QPushButton{background:@surface_alt;color:@text;"
                    "border:1px solid @border;border-radius:6px;padding:0 8px;"
                    "font-size:15px;font-weight:700;}"
                )
            button.setStyleSheet(theme_qss(button_style))
            callback = actions.get(action_name)
            if callback:
                button.clicked.connect(callback)
            if action_name == "toggle_traffic":
                self.live_traffic_button = button
            if action_name == "share_location":
                self.share_location_button = button
            if action_name == "toggle_map_mode":
                self.map_mode_button = button
            self.action_buttons[action_name] = button
            header.addWidget(button)
        self.window_buttons = []
        for action_name, tooltip, icon_name in (
            ("window_minimize", "Simge durumuna k\u00fc\u00e7\u00fclt", "SP_TitleBarMinButton"),
            ("window_maximize", "Pencereyi b\u00fcy\u00fclt / geri al", "SP_TitleBarMaxButton"),
            ("window_close", "Kapat", "SP_TitleBarCloseButton"),
        ):
            button = QPushButton()
            button.setObjectName("field_{}".format(action_name))
            button.setFixedSize(32, 32)
            button.setIcon(self.style().standardIcon(getattr(QStyle.StandardPixmap, icon_name)))
            button.setIconSize(QSize(18, 18))
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:@surface_alt;color:@text;border:1px solid @border;"
                "border-radius:5px;font-size:17.5px;font-weight:700;}"
                "QPushButton:hover{background:@surface;}"
            ))
            callback = actions.get(action_name)
            if callback:
                button.clicked.connect(callback)
            self.window_buttons.append(button)
            header.addWidget(button)
        self.header_row = header
        root.addLayout(header)

        metrics = QHBoxLayout()
        metrics.setContentsMargins(12, 0, 12, 0)
        metrics.setSpacing(8)
        for caption, color, icon in self.METRICS:
            card = QFrame()
            self.metric_cards.append(card)
            card.setObjectName("FieldMetric")
            card.setFixedHeight(76)
            card.setStyleSheet(theme_qss(
                "QFrame#FieldMetric{background:@finance_surface;border:1px solid @finance_outline;"
                "border-radius:10px;}QLabel{border:none;background:transparent;}"
            ))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(9, 5, 9, 5)
            card_layout.setSpacing(0)
            card_heading = QHBoxLayout()
            metric_title = QLabel(caption)
            metric_title.setFixedHeight(19)
            metric_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            metric_title.setStyleSheet(theme_qss(
                "color:@text_muted;font-size:14px;border:none;"
            ))
            card_heading.addWidget(metric_title, 1)
            metric_icon = LoanerMetricIcon(icon, color)
            metric_icon.setFixedSize(16, 16)
            card_heading.addWidget(metric_icon, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            value = QLabel("-")
            value.setFixedHeight(25)
            value.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            value.setStyleSheet(theme_qss(
                "color:@{};font-size:25px;font-weight:800;border:none;".format(color)
            ))
            note = QLabel("Veri kayna\u011f\u0131 ba\u011fl\u0131 de\u011fil")
            note.setWordWrap(True)
            note.setFixedHeight(17)
            note.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            note.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:12.5px;"))
            self.metric_values.append(value)
            self.metric_notes.append(note)
            card_layout.addLayout(card_heading)
            card_layout.addWidget(value)
            card_layout.addStretch(1)
            card_layout.addWidget(note)
            metrics.addWidget(card, 1)
        root.addLayout(metrics)

    def set_dense(self, dense):
        return None

    def set_compact(self, compact):
        labels = {
            "create_task": ("Yeni G\u00f6rev", "+ Yeni Saha G\u00f6revi Ata"),
            "optimize_route": ("AI Rota", "Rota Optimizasyonu (AI)"),
            "toggle_traffic": ("Trafik", "Canl\u0131 Trafik"),
            "share_location": ("WhatsApp Payla\u015f", "WhatsApp H\u0131zl\u0131 Payla\u015f"),
            "toggle_map_mode": ("3D Harita", "3D Vekt\u00f6r"),
        }
        widths = {
            "create_task": (120, 158),
            "optimize_route": (84, 210),
            "toggle_traffic": (78, 116),
            "share_location": (150, 166),
            "toggle_map_mode": (92, 106),
        }
        self.breadcrumb.setVisible(not compact)
        self.live_teams_label.setVisible(not compact)
        for name, button in self.action_buttons.items():
            button.setText(labels[name][0 if compact else 1])
            button.setFixedWidth(widths[name][0 if compact else 1])


class FieldOperationsPanel(QFrame):
    """Search, filters, location tools, and personnel list for the field map."""

    FILTERS = (("all", "Ekipler"), ("idle", "Bekleyen"), ("warnings", "Uyarilar"))

    def __init__(self, actions, refresh_callback, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setMaximumWidth(368)
        self.setObjectName("FieldSidebar")
        self.setStyleSheet(theme_qss(
            "QFrame#FieldSidebar{background:@finance_surface;border:none;border-radius:8px;}"
            "QLabel{border:none;background:transparent;}"
        ))
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 2, 12, 10)
        root.setSpacing(8)

        tabs = QHBoxLayout()
        tabs.setContentsMargins(2, 2, 2, 2)
        tabs.setSpacing(3)
        self.mode_buttons = {}
        for key, caption in (
            ("customer", "M\u00fc\u015fteri && WhatsApp"),
            ("teams", "Ekipler (0)"),
            ("jobs", "\u0130\u015f Emirleri (0)"),
        ):
            button = QPushButton(caption)
            button.setObjectName("field_sidebar_tab_{}".format(key))
            button.setCheckable(True)
            button.setChecked(key == "customer")
            button.setMinimumWidth(0)
            button.setFixedHeight(34)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:transparent;color:@finance_text_muted;border:none;"
                "border-radius:6px;padding:0 8px;font-size:17.5px;font-weight:700;}"
                "QPushButton:checked{background:@finance_surface_alt;color:@finance_primary;}"
            ))
            button.clicked.connect(lambda checked=False, value=key: self.select_tab(value))
            tabs.addWidget(button, 1)
            self.mode_buttons[key] = button
        root.addLayout(tabs)

        self.personnel_search = QLineEdit()
        self.personnel_search.setPlaceholderText("Teknisyen veya i\u015f emri ara...")
        self.personnel_search.setClearButtonEnabled(True)
        self.personnel_search.setFixedHeight(36)
        self.personnel_search.textChanged.connect(refresh_callback)
        root.addWidget(self.personnel_search)
        self.personnel_search.hide()

        self.filter_container = QWidget()
        filters = QHBoxLayout(self.filter_container)
        filters.setContentsMargins(0, 0, 0, 0)
        filters.setSpacing(4)
        self.radar_filter_buttons = {}
        for category, caption in self.FILTERS:
            button = QPushButton(caption)
            button.setCheckable(True)
            button.setChecked(category == "all")
            button.setFixedHeight(30)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:@finance_surface_alt;color:@finance_text_muted;border:none;"
                "border-radius:5px;padding:0 8px;min-height:34px;font-size:16px;font-weight:700;}"
                "QPushButton:checked{background:@selection_bg;color:@selection_text;}"
            ))
            callback = actions.get("filter_category")
            if callback:
                button.clicked.connect(
                    lambda checked=False, value=category: callback(value)
                )
            filters.addWidget(button, 1)
            self.radar_filter_buttons[category] = button
        root.addWidget(self.filter_container)
        self.filter_container.hide()

        self.location_card = QFrame()
        self.location_card.setObjectName("FieldLocationShareCard")
        self.location_card.setStyleSheet(theme_qss(
            "QFrame#FieldLocationShareCard{background:@finance_surface_alt;"
            "border:1px solid @finance_outline;border-radius:10px;}"
            "QLabel{background:transparent;border:none;}"
        ))
        location_card_layout = QVBoxLayout(self.location_card)
        location_card_layout.setContentsMargins(10, 10, 10, 10)
        location_card_layout.setSpacing(6)
        location_heading = QHBoxLayout()
        location_title = QLabel("M\u00fc\u015fteri Konum & WhatsApp")
        location_title.setStyleSheet(theme_qss(
            "color:@finance_text;font-size:22.5px;font-weight:700;"
        ))
        location_heading.addWidget(location_title, 1)
        self.location_badge = QLabel("KONUM SECIN")
        self.location_badge.setStyleSheet(theme_qss(
            "color:@finance_secondary;background:@finance_success_bg;border-radius:4px;"
            "padding:4px 7px;font-size:15px;font-weight:700;"
        ))
        location_heading.addWidget(self.location_badge)
        location_card_layout.addLayout(location_heading)

        customer_info = QFrame()
        customer_info.setObjectName("FieldCustomerInfo")
        customer_info.setStyleSheet(theme_qss(
            "QFrame#FieldCustomerInfo{background:@finance_surface;border:1px solid "
            "@finance_outline;border-radius:7px;}QLabel{background:transparent;border:none;}"
        ))
        customer_info_layout = QVBoxLayout(customer_info)
        customer_info_layout.setContentsMargins(7, 5, 7, 5)
        customer_info_layout.setSpacing(2)
        customer_info_heading = QHBoxLayout()
        customer_info_title = QLabel("M\u00dc\u015eTER\u0130 B\u0130LG\u0130S\u0130")
        customer_info_title.setStyleSheet(theme_qss(
            "color:@finance_text_muted;font-size:15px;font-weight:700;letter-spacing:0.4px;"
        ))
        customer_info_heading.addWidget(customer_info_title, 1)
        self.customer_selection_label = QLabel("IS EMRI SECILMEDI")
        self.customer_selection_label.setStyleSheet(theme_qss(
            "color:@finance_text_muted;font-family:'JetBrains Mono';font-size:14px;font-weight:700;"
        ))
        customer_info_heading.addWidget(self.customer_selection_label)
        customer_info_layout.addLayout(customer_info_heading)

        customer_fields = QGridLayout()
        customer_fields.setContentsMargins(0, 0, 0, 0)
        customer_fields.setHorizontalSpacing(8)
        customer_fields.setVerticalSpacing(2)
        name_label = QLabel("M\u00dc\u015eTER\u0130 ADI")
        phone_label = QLabel("GSM / WHATSAPP")
        for field_label in (name_label, phone_label):
            field_label.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;font-weight:700;"))
        self.customer_name_value = QLabel("\u0130\u015f emri se\u00e7ilmedi")
        self.customer_phone_value = QLabel("Kay\u0131tl\u0131 telefon yok")
        for value_label in (self.customer_name_value, self.customer_phone_value):
            value_label.setStyleSheet(theme_qss("color:@finance_text;font-size:18.75px;font-weight:600;"))
        customer_fields.addWidget(name_label, 0, 0)
        customer_fields.addWidget(phone_label, 0, 1)
        customer_fields.addWidget(self.customer_name_value, 1, 0)
        customer_fields.addWidget(self.customer_phone_value, 1, 1)
        customer_info_layout.addLayout(customer_fields)

        address_title = QLabel("SE\u00c7\u0130LEN SERV\u0130S ADRES\u0130")
        address_title.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;font-weight:700;"))
        customer_info_layout.addWidget(address_title)
        self.selected_address_label = QLabel("Haritadan se\u00e7ilen nokta")
        self.selected_address_label.setObjectName("field_selected_address")
        self.selected_address_label.setTextFormat(Qt.TextFormat.PlainText)
        self.selected_address_label.setWordWrap(True)
        self.selected_address_label.setStyleSheet(theme_qss(
            "color:@finance_text;background:@finance_surface_alt;border:1px solid @finance_outline;"
            "border-radius:5px;padding:8px 10px;font-size:17.5px;"
        ))
        location_card_layout.addWidget(customer_info)

        self.selected_location_label = QLabel("Haritadan bir nokta secin")
        self.selected_location_label.setStyleSheet(theme_qss(
            "color:@finance_text;font-family:'JetBrains Mono';font-size:16.25px;font-weight:700;"
        ))
        location_card_layout.addWidget(self.selected_location_label)
        share_message_title = QLabel("G\u00d6NDER\u0130LECEK WHATSAPP MESAJI")
        share_message_title.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;font-weight:700;"))
        location_card_layout.addWidget(share_message_title)
        self.share_preview_label = QLabel("AYEC Pro Saha Konum Paylasimi")
        self.share_preview_label.setObjectName("field_whatsapp_preview")
        self.share_preview_label.setWordWrap(True)
        self.share_preview_label.setStyleSheet(theme_qss(
            "color:@finance_text;background:@finance_surface;border:1px solid @finance_outline;"
            "border-radius:6px;padding:9px;font-size:17.5px;"
        ))
        location_card_layout.addWidget(self.share_preview_label)
        location_actions = QVBoxLayout()
        location_actions.setSpacing(4)
        self.share_location_button = self._action_button(
            "WhatsApp ile Paylas", actions.get("share"), "share_location_direct"
        )
        self.share_location_button.setFixedHeight(42)
        self.share_location_button.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_success_bg;color:@finance_secondary;"
            "border:1px solid @finance_secondary;border-radius:6px;padding:0 8px;"
            "font-size:17.5px;font-weight:700;}"
            "QPushButton:hover{background:@finance_surface_alt;}"
        ))
        self.assign_location_button = self._action_button(
            "Personele Ata", actions.get("assign"), "assign_location_direct"
        )
        self.assign_location_button.setFixedHeight(38)
        location_actions.addWidget(self.share_location_button)
        location_actions.addWidget(self.assign_location_button)
        location_card_layout.addLayout(location_actions)
        root.addWidget(self.location_card)

        self.location_toggle = QPushButton("Konum Islemleri  +")
        self.location_toggle.setCheckable(True)
        self.location_toggle.setFixedHeight(38)
        self.location_toggle.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid "
            "@finance_outline;border-radius:6px;padding:0 10px;min-height:34px;font-size:17.5px;"
            "font-weight:700;text-align:left;}QPushButton:checked{color:@finance_primary;"
            "border-color:@finance_primary;}"
        ))
        self.location_scroll = QScrollArea()
        self.location_scroll.setWidgetResizable(True)
        self.location_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.location_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.location_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.location_scroll.setMaximumHeight(260)
        self.location_scroll.setMinimumHeight(190)
        self.location_controls = QWidget()
        self.location_scroll.setWidget(self.location_controls)
        self.location_scroll.hide()
        self.location_toggle.toggled.connect(self._toggle_location_tools)

        location_layout = QVBoxLayout(self.location_controls)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setSpacing(5)
        actions_header = QLabel("Hizli Islemler")
        actions_header.setFont(QFont(DesignTokens.FONT_NAME, 13, QFont.Weight.Bold))
        actions_header.setStyleSheet(theme_qss("color:@text_muted;font-size:15px;font-weight:700;margin:3px 2px;"))
        location_layout.addWidget(actions_header)
        self.location_action_buttons = []
        for text, action_name, icon in (
            ("Yeni Rota Ciz", "draw_route", "\\U0001F5FA"),
            ("Manuel Koordinat Gir", "manual", "\\U0001F4CD"),
            ("Eve Don (Merkez)", "home", "\\U0001F3E0"),
            ("WhatsApp Konumu Yapistir", "whatsapp", "\\U0001F4F1"),
            ("Konum Baglantisini Paylas", "share", "\\U0001F517"),
            ("Secili Konumu Personele Ata", "assign", "\\U0001F464"),
        ):
            button = self._action_button(
                "{} {}".format(icon.encode("ascii").decode("unicode_escape"), text),
                actions.get(action_name), action_name
            )
            location_layout.addWidget(button)
            self.location_action_buttons.append(button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(8)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        root.addWidget(self.scroll_area, 1)

        self.jobs_scroll_area = QScrollArea()
        self.jobs_scroll_area.setObjectName("field_jobs_scroll")
        self.jobs_scroll_area.setWidgetResizable(True)
        self.jobs_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.jobs_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.jobs_content = QWidget()
        self.jobs_layout = QVBoxLayout(self.jobs_content)
        self.jobs_layout.setContentsMargins(0, 0, 0, 0)
        self.jobs_layout.setSpacing(8)
        self.jobs_scroll_area.setWidget(self.jobs_content)
        self.jobs_scroll_area.hide()
        root.addWidget(self.jobs_scroll_area, 1)
        root.addWidget(self.location_toggle)
        root.addWidget(self.location_scroll)

        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.setFixedHeight(38)
        self.refresh_button.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface_alt;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:6px;padding:4px 8px;font-size:16.25px;}"
        ))
        self.refresh_button.clicked.connect(refresh_callback)
        root.addWidget(self.refresh_button)

    def select_tab(self, key):
        selected = key if key in self.mode_buttons else "customer"
        for name, button in self.mode_buttons.items():
            button.setChecked(name == selected)
        customer = selected == "customer"
        teams = selected == "teams"
        self.location_card.setVisible(customer)
        self.scroll_area.setVisible(customer or teams)
        self.jobs_scroll_area.setVisible(selected == "jobs")
        self.filter_container.setVisible(teams)
        self.location_toggle.setVisible(customer)
        self.location_scroll.setVisible(customer and self.location_toggle.isChecked())

    def set_mode_counts(self, team_count, job_count):
        self.mode_buttons["teams"].setText("Ekipler ({})".format(int(team_count)))
        self.mode_buttons["jobs"].setText("\u0130\u015f Emirleri ({})".format(int(job_count)))

    def set_jobs(self, jobs):
        while self.jobs_layout.count():
            item = self.jobs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not jobs:
            empty = QLabel("G\u00f6sterilecek a\u00e7\u0131k i\u015f emri bulunmuyor.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;padding:20px;"))
            self.jobs_layout.addWidget(empty)
            self.jobs_layout.addStretch(1)
            return
        for job in jobs:
            card = QFrame()
            card.setObjectName("FieldJobCard")
            card.setStyleSheet(theme_qss(
                "QFrame#FieldJobCard{background:@finance_surface_alt;"
                "border:1px solid @finance_outline;border-radius:8px;}"
                "QLabel{background:transparent;border:none;}"
            ))
            layout = QVBoxLayout(card)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(4)
            title = str(job.get("customer_name") or job.get("customer") or job.get("title") or "Saha i\u015f emri")
            heading = QLabel(title)
            heading.setStyleSheet(theme_qss("color:@finance_text;font-size:22.5px;font-weight:700;"))
            layout.addWidget(heading)
            date_time = " ".join(str(job.get(key) or "") for key in ("date", "time")).strip()
            status = str(job.get("status") or "Bekliyor")
            meta = QLabel("{}  |  {}".format(date_time or "Tarih belirtilmedi", status))
            meta.setStyleSheet(theme_qss("color:@finance_secondary;font-size:17.5px;font-weight:600;"))
            layout.addWidget(meta)
            description = str(job.get("description") or job.get("notes") or "")
            if description:
                detail = QLabel(description)
                detail.setWordWrap(True)
                detail.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:17.5px;"))
                layout.addWidget(detail)
            self.jobs_layout.addWidget(card)
        self.jobs_layout.addStretch(1)

    def _toggle_location_tools(self, active):
        self.location_scroll.setVisible(bool(active))
        self.location_toggle.setText("Konum Islemleri  -" if active else "Konum Islemleri  +")

    def set_selected_location(self, latitude, longitude):
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            self.set_selected_address("")
            self.selected_location_label.setText(
                "{:.5f}, {:.5f}".format(latitude, longitude)
            )
            self.location_badge.setText("SECILI NOKTA")
            self.share_preview_label.setText(
                "AYEC Pro Saha Konum Paylasimi\n"
                "Haritada secilen konum: {:.6f}, {:.6f}\n"
                "https://www.google.com/maps?q={:.6f},{:.6f}".format(
                    latitude, longitude, latitude, longitude
                )
            )
        except (TypeError, ValueError):
            self.selected_location_label.setText("Haritadan bir nokta secin")
            self.location_badge.setText("KONUM SECIN")
            self.share_preview_label.setText("AYEC Pro Saha Konum Paylasimi")
            self.set_selected_address("")

    def set_selected_address(self, address):
        text = str(address or "").strip()
        self.selected_address_label.setText(text or "Haritadan se\u00e7ilen nokta")

    def _action_button(self, text, callback, action_name):
        button = QPushButton(text)
        button.setObjectName("field_location_{}".format(action_name))
        button.setFixedHeight(40)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        border = "finance_secondary" if action_name == "whatsapp" else "border"
        color = "finance_primary" if action_name == "assign" else "text"
        button.setStyleSheet(theme_qss(
            "QPushButton{{background:@surface;color:@{color};border:1px solid @{border};"
            "border-radius:6px;text-align:left;padding:0 10px;font-size:15px;}}"
            "QPushButton:hover{{background:@surface_alt;border-color:@{border};}}".format(
                color=color, border=border
            )
        ))
        if callback:
            button.clicked.connect(callback)
        return button

    def set_dense(self, dense, short_screen):
        self.location_scroll.setMinimumHeight(150 if short_screen else 190)
        self.location_toggle.setFixedHeight(38 if dense else 40)
        self.personnel_search.setFixedHeight(34 if dense else 36)
        for button in self.location_action_buttons:
            button.setFixedHeight(38 if dense else 40)


class ManualLocationDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(title="Konuma Git", parent=parent, width=400, height=320)

        desc = QLabel("Gitmek istediginiz nokta icin koordinat giriniz.")
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)

        self.inp_lat = QLineEdit()
        self.inp_lat.setPlaceholderText("Enlem (Lat) orn: 39.6484")
        self.content_layout.addWidget(self.inp_lat)

        self.inp_lng = QLineEdit()
        self.inp_lng.setPlaceholderText("Boylam (Lng) orn: 27.8826")
        self.content_layout.addWidget(self.inp_lng)
        self.content_layout.addStretch()

        self.add_button("Vazgec", variant="secondary", callback=self.reject)
        self.add_button("Konuma Git", callback=self.accept)

    def get_coordinates(self):
        try:
            lat = float(self.inp_lat.text().replace(",", "."))
            lng = float(self.inp_lng.text().replace(",", "."))
            return lat, lng
        except ValueError:
            return None


class PersonnelCard(QFrame):
    def __init__(self, t_data, callback, finish_callback, parent=None):
        super().__init__(parent)
        self.t_data = t_data
        self.callback = callback
        self.finish_callback = finish_callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("FieldPersonnelCard")
        self.setStyleSheet(theme_qss("QFrame#FieldPersonnelCard{background:@finance_surface;border:1px solid @finance_outline;border-radius:4px;}QFrame#FieldPersonnelCard:hover{border-color:@finance_primary;}QLabel{background:transparent;border:none;}"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        name_lbl = QLabel(t_data["name"])
        name_lbl.setStyleSheet("border: none; background: transparent;")
        name_lbl.setFont(QFont(DesignTokens.FONT_NAME, 14, QFont.Weight.Bold))
        name_lbl.setTextFormat(Qt.TextFormat.PlainText)
        name_lbl.setToolTip(name_lbl.text())
        name_lbl.setWordWrap(True)

        status_text = t_data.get("status") or "Durum bildirilmemis"
        normalized = str(status_text).casefold().replace("\u0131", "i").replace("\u015f", "s")
        status_token = "finance_secondary" if normalized == "bosta" else "finance_text_muted"
        status_lbl = QLabel(f"* {status_text}")
        status_lbl.setTextFormat(Qt.TextFormat.PlainText)
        status_lbl.setFont(QFont(DesignTokens.FONT_NAME, 11))
        status_lbl.setWordWrap(True)
        status_lbl.setToolTip(status_lbl.text())
        status_lbl.setStyleSheet(theme_qss("color:@" + status_token + ";border:none;background:transparent;font-size:16.25px;"))

        layout.addWidget(name_lbl)
        role = QLabel(str(t_data.get("job") or t_data.get("role") or "Personel"))
        role.setTextFormat(Qt.TextFormat.PlainText)
        role.setFont(QFont(DesignTokens.FONT_NAME, 11))
        role.setToolTip(role.text())
        role.setWordWrap(True)
        role.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:17.5px;"))
        layout.addWidget(role)
        layout.addWidget(status_lbl)
        try:
            coordinate_text = "GPS: {:.5f}, {:.5f}".format(float(t_data["lat"]), float(t_data["lng"]))
        except (KeyError, ValueError, TypeError):
            coordinate_text = "GPS: Konum tanimli degil"
        coordinates = QLabel(coordinate_text)
        coordinates.setTextFormat(Qt.TextFormat.PlainText)
        coordinates.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9))
        coordinates.setToolTip(coordinates.text())
        coordinates.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;"))
        layout.addWidget(coordinates)
        if t_data.get("last_seen"):
            timestamp = QLabel("Son konum: " + str(t_data["last_seen"]))
            timestamp.setTextFormat(Qt.TextFormat.PlainText)
            timestamp.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9))
            timestamp.setWordWrap(True)
            timestamp.setToolTip(timestamp.text())
            timestamp.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:15px;"))
            layout.addWidget(timestamp)
        self.finish_button = QPushButton("Gorevi Tamamla")
        self.finish_button.setEnabled(callable(finish_callback))
        self.finish_button.setFixedHeight(32)
        self.finish_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 8px;min-height:36px;font-size:17.5px;}"))
        self.finish_button.clicked.connect(lambda checked=False: self.finish_callback(self.t_data))
        layout.addWidget(self.finish_button)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback(self.t_data)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        db = None
        owner = self.parent()
        while owner is not None:
            db = getattr(owner, "db", None)
            if db is not None:
                break
            owner = owner.parent()
        if not is_context_menu_enabled(db):
            return
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        finish_action = menu.addAction("Gorevi Tamamla / Bosa Cikar")
        action = menu.exec(event.globalPos())
        if action == finish_action and self.finish_callback:
            self.finish_callback(self.t_data)


class ModernConfirmDialog(ModernDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(title=title, parent=parent, width=360, height=220)
        self.set_footer_visible(False)

        lbl_msg = QLabel(message)
        lbl_msg.setWordWrap(True)
        self.content_layout.addWidget(lbl_msg)
        self.content_layout.addStretch()

        self.add_button("Iptal", variant="secondary", callback=self.reject)
        self.add_button("Onayla", callback=self.accept)
