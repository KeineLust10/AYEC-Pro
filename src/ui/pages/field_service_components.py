from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import tc, theme_qss
from src.utils.design_system import DesignTokens
from src.ui.widgets.loaner_summary_visuals import LoanerMetricIcon


class FieldMapOverview(QFrame):
    """Header actions and field-operation summary metrics."""

    ACTIONS = (
        ("field_action_new_task", "+ Yeni Saha Gorevi Ata", "create_task", "accent"),
        ("field_action_optimize_route", "Rota Optimizasyonu", "optimize_route", "surface_alt"),
        ("field_action_live_traffic", "Canli Trafik", "toggle_traffic", "surface_alt"),
        ("field_action_filter", "Filtrele", "filter_personnel", "surface_alt"),
        ("field_action_map_mode", "3D Vektor", "toggle_map_mode", "surface_alt"),
    )
    METRICS = (
        ("SAHADAKI EKIPLER", "finance_text", "truck"),
        ("BUGUNKU SAHA GOREVLERI", "finance_text", "check"),
        ("ORTALAMA VARIS SURESI", "finance_secondary", "clock"),
        ("ACIL SAHA CAGRISI", "finance_tertiary", "warning"),
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

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 12, 0, 0)
        root.setSpacing(10)
        title_block = QVBoxLayout()
        breadcrumb = QLabel("SERVIS OPERASYON  >  SAHA YONETIMI  >  AYEC-FIELD-RADAR")
        breadcrumb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        breadcrumb.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:11px;font-weight:700;"))
        title_block.addWidget(breadcrumb)
        title = QLabel("Saha Haritasi & Canli Teknisyen Takibi")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title.setFont(QFont(self.font().family(), 18, QFont.Weight.Bold))
        title.setStyleSheet("color: {}; border: none;".format(tc("text")))
        title_block.addWidget(title)
        self.subtitle = QLabel(
            "Saha ekiplerinin anlik konumlarini, servis rotalarini ve acil saha cagrilarini izleyin."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.subtitle.setMaximumWidth(760)
        self.subtitle.setStyleSheet("color: {}; border: none;".format(tc("text_muted")))
        title_block.addWidget(self.subtitle)

        action_row = QHBoxLayout()
        action_row.setContentsMargins(0, 0, 0, 0)
        action_row.setSpacing(6)
        action_widths = {
            "create_task": 164,
            "optimize_route": 154,
            "toggle_traffic": 112,
            "filter_personnel": 88,
            "toggle_map_mode": 104,
        }
        for object_name, caption, action_name, accent in self.ACTIONS:
            button = QPushButton(caption)
            button.setObjectName(object_name)
            button.setFixedSize(action_widths[action_name], 32)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            foreground = tc("selection_text") if accent == "accent" else tc("text")
            button.setStyleSheet(
                "background: {}; color: {}; border: 1px solid {}; border-radius: 6px; "
                "padding: 0 10px; font-weight: 700;".format(
                    tc(accent), foreground, tc("border")
                )
            )
            callback = actions.get(action_name)
            if callback:
                button.clicked.connect(callback)
            if action_name == "toggle_traffic":
                self.live_traffic_button = button
            if action_name == "toggle_map_mode":
                self.map_mode_button = button
            action_row.addWidget(button)
        root.addLayout(title_block)
        actions_container = QHBoxLayout()
        actions_container.setContentsMargins(0, 0, 0, 0)
        actions_container.addStretch(1)
        actions_container.addLayout(action_row)
        root.addLayout(actions_container)

        metrics = QHBoxLayout()
        metrics.setSpacing(10)
        for caption, color, icon in self.METRICS:
            card = QFrame()
            self.metric_cards.append(card)
            card.setObjectName("FieldMetric")
            card.setFixedHeight(108)
            card.setStyleSheet(theme_qss(
                "QFrame#FieldMetric{background:@finance_surface;border:1px solid @finance_outline;"
                "border-radius:8px;}QLabel{border:none;background:transparent;}"
            ))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 9, 12, 9)
            card_layout.setSpacing(4)
            card_heading = QHBoxLayout()
            metric_title = QLabel(caption)
            metric_title.setStyleSheet(
                "color: {}; font-size: 10px; border: none;".format(tc("text_muted"))
            )
            card_heading.addWidget(metric_title, 1)
            card_heading.addWidget(LoanerMetricIcon(icon, color))
            value = QLabel("-")
            value.setStyleSheet(
                "color: {}; font-size: 23px; font-weight: 800; border: none;".format(tc(color))
            )
            note = QLabel("Veri kaynagi bagli degil")
            note.setWordWrap(True)
            note.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:10px;"))
            self.metric_values.append(value)
            self.metric_notes.append(note)
            card_layout.addLayout(card_heading)
            card_layout.addWidget(value)
            card_layout.addStretch(1)
            card_layout.addWidget(note)
            metrics.addWidget(card, 1)
        root.addLayout(metrics)

    def set_dense(self, dense):
        self.subtitle.setVisible(not dense)
        for card in self.metric_cards:
            card.setFixedHeight(100 if dense else 108)


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
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        title = QLabel("Saha Operasyon Merkezi")
        title.setFont(QFont(self.font().family(), 13, QFont.Weight.Bold))
        title.setStyleSheet("color: {};".format(tc("text")))
        root.addWidget(title)
        subtitle = QLabel("Canli Takip ve Gorev Yonetimi")
        subtitle.setFont(QFont(DesignTokens.FONT_NAME, 10))
        subtitle.setStyleSheet("color: {}; margin-bottom: 4px;".format(tc("text_muted")))
        root.addWidget(subtitle)

        self.personnel_search = QLineEdit()
        self.personnel_search.setPlaceholderText("Teknisyen veya is yeri ara...")
        self.personnel_search.setClearButtonEnabled(True)
        self.personnel_search.setFixedHeight(36)
        self.personnel_search.textChanged.connect(refresh_callback)
        root.addWidget(self.personnel_search)

        filters = QHBoxLayout()
        filters.setSpacing(4)
        self.radar_filter_buttons = {}
        for category, caption in self.FILTERS:
            button = QPushButton(caption)
            button.setCheckable(True)
            button.setChecked(category == "all")
            button.setFixedHeight(30)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:@finance_surface_alt;color:@finance_text_muted;border:none;"
                "border-radius:5px;padding:0 6px;min-height:24px;font-size:11px;font-weight:700;}"
                "QPushButton:checked{background:@selection_bg;color:@selection_text;}"
            ))
            callback = actions.get("filter_category")
            if callback:
                button.clicked.connect(
                    lambda checked=False, value=category: callback(value)
                )
            filters.addWidget(button, 1)
            self.radar_filter_buttons[category] = button
        root.addLayout(filters)

        self.location_toggle = QPushButton("Konum Islemleri  +")
        self.location_toggle.setCheckable(True)
        self.location_toggle.setFixedHeight(34)
        self.location_toggle.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid "
            "@finance_outline;border-radius:6px;padding:0 10px;min-height:28px;font-size:11px;"
            "font-weight:700;text-align:left;}QPushButton:checked{color:@finance_primary;"
            "border-color:@finance_primary;}"
        ))
        root.addWidget(self.location_toggle)
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
        root.addWidget(self.location_scroll)
        self.location_toggle.toggled.connect(self._toggle_location_tools)

        location_layout = QVBoxLayout(self.location_controls)
        location_layout.setContentsMargins(0, 0, 0, 0)
        location_layout.setSpacing(5)
        actions_header = QLabel("Hizli Islemler")
        actions_header.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
        actions_header.setStyleSheet("color: {}; margin: 3px 2px;".format(tc("text_muted")))
        location_layout.addWidget(actions_header)
        self.location_action_buttons = []
        for text, action_name, icon in (
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

        status_title = QLabel("Personel Durumu")
        status_title.setFont(QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold))
        status_title.setStyleSheet("color: {}; margin-top: 8px;".format(tc("text_muted")))
        root.addWidget(status_title)
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

        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.setFixedHeight(32)
        self.refresh_button.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface_alt;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:6px;padding:4px 8px;}"
        ))
        self.refresh_button.clicked.connect(refresh_callback)
        root.addWidget(self.refresh_button)

    def _toggle_location_tools(self, active):
        self.location_scroll.setVisible(bool(active))
        self.location_toggle.setText("Konum Islemleri  -" if active else "Konum Islemleri  +")

    def _action_button(self, text, callback, action_name):
        button = QPushButton(text)
        button.setObjectName("field_location_{}".format(action_name))
        button.setFixedHeight(36)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        border = "#25d366" if action_name == "whatsapp" else tc("border")
        color = tc("accent") if action_name == "assign" else tc("text")
        button.setStyleSheet(
            "QPushButton{{background:{};color:{};border:1px solid {};border-radius:6px;"
            "text-align:left;padding:0 10px;font-size:11px;}}"
            "QPushButton:hover{{background:{};border-color:{};}}".format(
                tc("surface"), color, border, tc("surface_alt"),
                tc("accent") if action_name == "assign" else border
            )
        )
        if callback:
            button.clicked.connect(callback)
        return button

    def set_dense(self, dense, short_screen):
        self.location_scroll.setMinimumHeight(150 if short_screen else 190)
        self.location_toggle.setFixedHeight(32 if dense else 34)
        self.personnel_search.setFixedHeight(34 if dense else 36)
        for button in self.location_action_buttons:
            button.setFixedHeight(34 if dense else 36)


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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        name_lbl = QLabel(t_data["name"])
        name_lbl.setStyleSheet("border: none; background: transparent;")
        name_lbl.setFont(QFont(DesignTokens.FONT_NAME, 11, QFont.Weight.Bold))
        name_lbl.setTextFormat(Qt.TextFormat.PlainText)
        name_lbl.setToolTip(name_lbl.text())
        name_lbl.setWordWrap(True)

        status_text = t_data.get("status") or "Durum bildirilmemis"
        normalized = str(status_text).casefold().replace("\u0131", "i").replace("\u015f", "s")
        status_token = "finance_secondary" if normalized == "bosta" else "finance_text_muted"
        status_lbl = QLabel(f"* {status_text}")
        status_lbl.setTextFormat(Qt.TextFormat.PlainText)
        status_lbl.setFont(QFont(DesignTokens.FONT_NAME, 9))
        status_lbl.setWordWrap(True)
        status_lbl.setToolTip(status_lbl.text())
        status_lbl.setStyleSheet(theme_qss("color:@" + status_token + ";border:none;background:transparent;font-size:11px;"))

        layout.addWidget(name_lbl)
        role = QLabel(str(t_data.get("job") or t_data.get("role") or "Personel"))
        role.setTextFormat(Qt.TextFormat.PlainText)
        role.setFont(QFont(DesignTokens.FONT_NAME, 9))
        role.setToolTip(role.text())
        role.setWordWrap(True)
        role.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:11px;"))
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
        coordinates.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:10px;"))
        layout.addWidget(coordinates)
        if t_data.get("last_seen"):
            timestamp = QLabel("Son konum: " + str(t_data["last_seen"]))
            timestamp.setTextFormat(Qt.TextFormat.PlainText)
            timestamp.setFont(QFont(DesignTokens.MONO_FONT_NAME, 9))
            timestamp.setWordWrap(True)
            timestamp.setToolTip(timestamp.text())
            timestamp.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:10px;"))
            layout.addWidget(timestamp)
        self.finish_button = QPushButton("Gorevi Tamamla")
        self.finish_button.setEnabled(callable(finish_callback))
        self.finish_button.setFixedHeight(26)
        self.finish_button.setStyleSheet(theme_qss("QPushButton{background:@finance_surface_alt;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:0 8px;min-height:22px;font-size:10px;}"))
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
