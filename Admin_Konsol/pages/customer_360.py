"""AYEC Pro Admin Console - isolated customer support overview."""

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QSizePolicy,
    QListWidget, QListWidgetItem, QLineEdit, QGridLayout, QScrollArea, QApplication,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QFontDatabase
from pathlib import Path

import api_client


_MONO_FONT_PATH = Path(__file__).resolve().parents[2] / "Web_Arayuzu" / "web" / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"


class _Customer360Thread(QThread):
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.loaded.emit(api_client.customer_360(self._tenant_id))
        except Exception as exc:
            self.failed.emit(str(exc))


class _CompanySectorThread(QThread):
    done = pyqtSignal(str, dict)
    failed = pyqtSignal(str)

    def __init__(self, tenant_id: str, sector: str):
        super().__init__()
        self._tenant_id = tenant_id
        self._sector = sector

    def run(self):
        try:
            self.done.emit(self._tenant_id, api_client.update_company_sector(self._tenant_id, self._sector))
        except Exception as exc:
            self.failed.emit(str(exc))


class Customer360Page(QWidget):
    """Single-firm support view backed by the central Admin API."""

    navigate_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._companies = []
        self._payload = {}
        self._thread = None
        self._build_ui()
        self._load_companies()

    def set_product_filter(self, _product_name: str):
        self._load_companies()

    def _build_ui(self):
        if _MONO_FONT_PATH.is_file():
            QFontDatabase.addApplicationFont(str(_MONO_FONT_PATH))
        self.setFont(QFont("Segoe UI", 10))
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(self)
        scroll.setObjectName("customer360Scroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._page_scroll = scroll
        page_layout.addWidget(scroll)
        content = QWidget()
        content.setObjectName("customer360Content")
        content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(content)
        root.setContentsMargins(40, 12, 16, 16)
        root.setSpacing(10)
        self._root_layout = root
        self.setStyleSheet(self.styleSheet() + """
            QWidget#customer360Page { background: #0e1321; color: #dee2f6; font-family: 'Plus Jakarta Sans', 'Segoe UI', Arial; }
            QWidget#customer360Content { background: #0e1321; }
            QScrollArea#customer360Scroll { background: #0e1321; }
            QWidget#customer360Page QLabel { background: transparent; }
            QWidget#customer360Page QLabel#pageTitle { color: #dee2f6; font-size: 22px; font-weight: 700; }
            QWidget#customer360Page QLabel#pageSubtitle { color: #c2c6d6; font-size: 11px; }
            QWidget#customer360Page QLabel#panelTitle { color: #dee2f6; font-size: 15px; font-weight: 700; }
            QWidget#customer360Page QLabel#referenceEyebrow { color: #4cd7f6; font: 700 10px 'JetBrains Mono', 'Segoe UI', Arial; letter-spacing: 1px; }
            QWidget#customer360Page QLabel#referenceLiveBadge { color: #4edea3; background: #090e1c; border-radius: 3px; padding: 5px 8px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QLabel#tenantUid { color: #adc6ff; background: #252a39; border-radius: 3px; padding: 4px 7px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QFrame#formCard { background: #161b2a; border: 1px solid #424754; border-radius: 8px; }
            QWidget#customer360Page QFrame#detailCard { background: #090e1c; border: 1px solid #252a39; border-radius: 4px; }
            QWidget#customer360Page QFrame#metricCard { background: #1a1f2e; border: 1px solid #252a39; border-radius: 4px; min-height: 96px; }
            QWidget#customer360Page QLabel#metricTitle { color: #8c909f; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; letter-spacing: 1px; }
            QWidget#customer360Page QLabel#metricValue { color: #4cd7f6; font-size: 25px; font-weight: 700; }
            QWidget#customer360Page QLabel#metricSub { color: #8c909f; font-size: 10px; }
            QWidget#customer360Page QLabel#fieldValue { color: #dee2f6; font-family: 'JetBrains Mono', 'Segoe UI', Arial; font-size: 11px; }
            QWidget#customer360Page QLineEdit#searchInput { background: #090e1c; color: #dee2f6; border: 1px solid #252a39; border-radius: 4px; min-height: 30px; }
            QWidget#customer360Page QComboBox#searchInput { background: #090e1c; color: #dee2f6; border: 1px solid #252a39; border-radius: 4px; padding: 6px 8px; min-height: 30px; }
            QWidget#customer360Page QPushButton#secondaryBtn { background: #252a39; color: #dee2f6; border: none; border-radius: 3px; padding: 6px 10px; }
            QWidget#customer360Page QPushButton#companyFilter { background: #090e1c; color: #c2c6d6; border: 1px solid #252a39; border-radius: 3px; padding: 6px; }
            QWidget#customer360Page QPushButton#companyFilter:checked { background: #252a39; color: #adc6ff; font-weight: 700; }
            QWidget#customer360Page QListWidget#companyList { background: transparent; border: none; border-radius: 0; }
            QWidget#customer360Page QListWidget#companyList::item { background: #252a39; color: #dee2f6; border: 1px solid #252a39; border-radius: 4px; margin: 4px 0; padding: 0; }
            QWidget#customer360Page QListWidget#companyList::item:selected { background: #252a39; border-left: 4px solid #adc6ff; color: #dee2f6; }
            QWidget#customer360Page QFrame#companyListItem { background: #252a39; border: 1px solid #303444; border-left: 4px solid #303444; border-radius: 4px; }
            QWidget#customer360Page QFrame#companyListItem[selected="true"] { border-left-color: #adc6ff; }
            QWidget#customer360Page QLabel#companyRowName { color: #dee2f6; font-size: 13px; font-weight: 700; }
            QWidget#customer360Page QLabel#companyRowMeta { color: #8c909f; font: 600 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QLabel#companyRowState { color: #4edea3; background: rgba(78, 222, 163, .12); padding: 2px 5px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QLabel#companyRowSector { color: #4cd7f6; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QTableWidget#dataTable { background: #090e1c; color: #dee2f6; border: 1px solid #252a39; border-radius: 4px; gridline-color: #1a1f2e; }
            QWidget#customer360Page QTableWidget#dataTable QHeaderView::section { background: #252a39; color: #8c909f; border: none; padding: 8px 6px; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial; }
            QWidget#customer360Page QPushButton#primaryBtn { background: #4d8eff; color: #00285d; border: none; border-radius: 3px; padding: 7px 10px; font-weight: 700; }
        """)
        self.setObjectName("customer360Page")

        header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._customer_header_layout = header
        title_box = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        title_box.setContentsMargins(12, 0, 0, 0)
        title_box.setSpacing(12)
        self._header_title_layout = title_box
        self._reference_eyebrow = QLabel("AYEC PRO / Y\u00d6NET\u0130M MERKEZ\u0130 / F\u0130RMA Y\u00d6NET\u0130M\u0130 & M\u00dc\u015eTER\u0130 360")
        self._reference_eyebrow.setObjectName("referenceEyebrow")
        self._reference_eyebrow.setWordWrap(True)
        self._reference_eyebrow.setMinimumWidth(0)
        self._reference_eyebrow.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._tenant_pool = QLabel("TENANT POOL: 0 AKT\u0130F")
        self._tenant_pool.setObjectName("tenantUid")
        self._tenant_pool.setFixedWidth(160)
        title_box.addWidget(self._reference_eyebrow)
        title_box.addWidget(self._tenant_pool)
        header.addLayout(title_box, 1)
        self._database_status = QLabel("\u25cf  MERKEZ\u0130 VER\u0130 TABANI CANLI")
        self._database_status.setObjectName("referenceLiveBadge")
        self._database_status.setFixedWidth(200)
        header.addWidget(self._database_status)
        refresh = QPushButton("Yenile")
        refresh.setObjectName("secondaryBtn")
        refresh.setFixedHeight(28)
        refresh.setFixedWidth(68)
        refresh.clicked.connect(self._load_companies)
        header.addWidget(refresh)
        root.addLayout(header)

        workspace = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        workspace.setSpacing(14)
        self._workspace_layout = workspace
        list_column = QWidget()
        list_column_layout = QVBoxLayout(list_column)
        list_column_layout.setContentsMargins(0, 0, 0, 0)
        list_column_layout.setSpacing(8)
        list_panel = QFrame()
        list_panel.setObjectName("formCard")
        list_panel.setMaximumHeight(132)
        self._list_panel = list_panel
        self._list_column = list_column
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(6)
        list_title_row = QHBoxLayout()
        list_title = QLabel("\u25a6  Firma Listesi")
        list_title.setObjectName("panelTitle")
        list_title_row.addWidget(list_title, 1)
        self._new_company = QPushButton("\u229e  Yeni Firma")
        self._new_company.setObjectName("primaryBtn")
        self._new_company.setFixedHeight(30)
        self._new_company.clicked.connect(lambda: self.navigate_requested.emit("companies"))
        list_title_row.addWidget(self._new_company)
        self._company_counts = QLabel("0 AKT\u0130F / 0 PAS\u0130F")
        self._company_counts.setObjectName("metricSub")
        list_layout.addLayout(list_title_row)
        self._company_search = QLineEdit()
        self._company_search.setObjectName("searchInput")
        self._company_search.setFixedHeight(36)
        self._company_search.setPlaceholderText("Firma, yetkili veya vergi no ara...")
        self._company_search.textChanged.connect(self._filter_companies)
        list_layout.addWidget(self._company_search)
        status_filters = QHBoxLayout()
        self._company_filter_buttons = {}
        self._company_filter_labels = {"all": "T\u00fcm\u00fc", "active": "Aktif", "inactive": "Pasif"}
        for key, label in self._company_filter_labels.items():
            button = QPushButton(label)
            button.setObjectName("companyFilter")
            button.setFixedHeight(26)
            button.setCheckable(True)
            button.setChecked(key == "all")
            button.clicked.connect(lambda _checked, target=key: self._set_company_filter(target))
            status_filters.addWidget(button)
            self._company_filter_buttons[key] = button
        list_layout.addLayout(status_filters)
        self._company_list = QListWidget()
        self._company_list.setObjectName("companyList")
        self._company_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._company_list.currentRowChanged.connect(self._company_row_changed)
        list_column_layout.addWidget(list_panel)
        list_column_layout.addWidget(self._company_list)
        self._company_counts.setText("KAYITLI L\u0130SANS HAVUZU: 0/1000")
        self._company_counts.setStyleSheet("color: #8c909f; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial;")
        self._online_summary = QLabel("\u2014")
        self._online_summary.setStyleSheet("color: #4edea3; font: 700 9px 'JetBrains Mono', 'Segoe UI', Arial;")
        list_footer = QHBoxLayout()
        list_footer.addWidget(self._company_counts, 1)
        list_footer.addWidget(self._online_summary)
        list_column_layout.addLayout(list_footer)
        list_column_layout.addStretch(1)
        self._company_combo = QComboBox()
        self._company_combo.setObjectName("fieldInput")
        self._company_combo.currentIndexChanged.connect(self._company_changed)
        self._company_combo.hide()
        workspace.addWidget(list_column, 4)

        detail_scroll = QWidget()
        self._detail_scroll = detail_scroll
        detail_layout = QVBoxLayout(detail_scroll)
        self._detail_layout = detail_layout
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)
        detail_header = QFrame()
        detail_header.setObjectName("formCard")
        detail_header.setMinimumHeight(172)
        detail_header_layout = QVBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 10, 12, 10)
        detail_header_layout.setSpacing(8)
        identity_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._identity_row = identity_row
        identity_row.setSpacing(8)
        identity_icon = QLabel("\u25a3")
        identity_icon.setObjectName("metricValue")
        identity_row.addWidget(identity_icon)
        self._company_label = QLabel("Firma secin")
        self._company_label.setObjectName("pageTitle")
        identity_row.addWidget(self._company_label)
        self._tenant_uid = QLabel("UID: --")
        self._tenant_uid.setObjectName("tenantUid")
        identity_row.addWidget(self._tenant_uid)
        self._company_status = QLabel("-")
        self._company_status.setObjectName("counterLabel")
        identity_row.addWidget(self._company_status)
        identity_row.addStretch(1)
        self._edit_company = QPushButton("D\u00fczenle")
        self._edit_company.setObjectName("secondaryBtn")
        self._edit_company.clicked.connect(lambda: self.navigate_requested.emit("companies"))
        identity_row.addWidget(self._edit_company)
        self._deactivate_company = QPushButton("Pasif Yap")
        self._deactivate_company.setObjectName("secondaryBtn")
        self._deactivate_company.clicked.connect(lambda: self.navigate_requested.emit("companies"))
        identity_row.addWidget(self._deactivate_company)
        self._mute_company = QPushButton("Sustur")
        self._mute_company.setObjectName("secondaryBtn")
        self._mute_company.setEnabled(False)
        self._mute_company.setToolTip("Susturma i\u015flemi merkezi API taraf\u0131nda sunulmuyor")
        identity_row.addWidget(self._mute_company)
        self._delete_company = QPushButton("Firmay\u0131 Sil")
        self._delete_company.setObjectName("secondaryBtn")
        self._delete_company.clicked.connect(lambda: self.navigate_requested.emit("companies"))
        identity_row.addWidget(self._delete_company)
        detail_header_layout.addLayout(identity_row)
        self._company_description = QLabel("M\u00fc\u015fteri 360 \u2022 Canl\u0131 servis telemetrisi, tenant izinleri ve lisans konsolu")
        self._company_description.setObjectName("pageSubtitle")
        self._company_description.setWordWrap(True)
        detail_header_layout.addWidget(self._company_description)
        sector_row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._sector_row = sector_row
        sector_row.addWidget(QLabel("\u0130\u015f Kolu & Mod\u00fcl:"))
        self._sector_combo = QComboBox()
        self._sector_combo.setObjectName("searchInput")
        self._sector_combo.addItem("Teknik Servis (AYEC Pro Enterprise)", "teknik_servis")
        self._sector_combo.addItem("Otomotiv", "automotive")
        self._sector_combo.addItem("IT & Servis", "it_services")
        sector_row.addWidget(self._sector_combo, 1)
        self._sector_apply = QPushButton("Sekt\u00f6r\u00fc Uygula")
        self._sector_apply.setObjectName("primaryBtn")
        self._sector_apply.clicked.connect(self._apply_sector)
        sector_row.addWidget(self._sector_apply)
        detail_header_layout.addLayout(sector_row)
        detail_layout.addWidget(detail_header)

        cards = QGridLayout()
        cards.setSpacing(8)
        self._metric_grid = cards
        self._metric_frames = []
        self._cards = {}
        self._card_subs = {}
        for index, (key, label) in enumerate((
            ("user_count", "KULLANICI HAVUZU"),
            ("backup_count", "BULUT YEDEK"),
            ("error_count", "KR\u0130T\u0130K HATA LOGU"),
            ("online", "CANLI OTURUM"),
        )):
            frame = QFrame()
            frame.setObjectName("metricCard")
            lay = QVBoxLayout(frame)
            value = QLabel("-")
            value.setObjectName("metricValue")
            caption = QLabel(label)
            caption.setObjectName("metricTitle")
            icon = QLabel(("\u2659", "\u2601", "\u2699", "\u25c9")[index])
            icon.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            icon.setObjectName("metricTitle")
            title_row = QHBoxLayout()
            title_row.addWidget(caption, 1)
            title_row.addWidget(icon)
            lay.addLayout(title_row)
            lay.addWidget(value)
            sub = QLabel("--")
            sub.setObjectName("metricSub")
            lay.addWidget(sub)
            cards.addWidget(frame, 0, index)
            self._metric_frames.append(frame)
            self._cards[key] = value
            self._card_subs[key] = sub
        detail_layout.addLayout(cards)

        profile = QFrame()
        profile.setObjectName("formCard")
        profile.setMinimumHeight(264)
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(14, 12, 14, 12)
        profile_title = QLabel("Firma ve Lisans Parametreleri")
        profile_title.setObjectName("panelTitle")
        profile_layout.addWidget(profile_title)
        self._detail_grid = QGridLayout()
        self._detail_grid.setHorizontalSpacing(10)
        self._detail_grid.setVerticalSpacing(8)
        self._detail_fields = {}
        self._detail_field_frames = []
        for index, (key, label) in enumerate((
            ("contact_name", "Firma Yetkilisi"),
            ("phone", "Telefon"),
            ("email", "E-posta"),
            ("license", "Lisans Turu / Bitis"),
            ("address", "Kurulum / Konum"),
            ("last_login", "Son Sistem Girisi"),
        )):
            field = QFrame()
            field.setObjectName("detailCard")
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(10, 8, 10, 8)
            caption = QLabel(label)
            caption.setObjectName("metricSub")
            value = QLabel("-")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            field_layout.addWidget(caption)
            field_layout.addWidget(value)
            self._detail_grid.addWidget(field, index // 3, index % 3)
            self._detail_field_frames.append(field)
            self._detail_fields[key] = value
        profile_layout.addLayout(self._detail_grid)
        self._license_code = QLabel("--")
        self._license_code.setObjectName("fieldValue")
        self._license_code.setWordWrap(True)
        self._license_code.setMinimumWidth(0)
        license_frame = QFrame()
        license_frame.setObjectName("detailCard")
        license_layout = QHBoxLayout(license_frame)
        self._license_layout = license_layout
        license_layout.setContentsMargins(10, 8, 10, 8)
        license_caption = QLabel("AKT\u0130F L\u0130SANS ANAHTARI")
        license_caption.setObjectName("metricTitle")
        license_layout.addWidget(license_caption)
        license_layout.addWidget(self._license_code, 1)
        self._copy_license = QPushButton("\u29c9  Kodu Kopyala")
        self._copy_license.setObjectName("secondaryBtn")
        self._copy_license.clicked.connect(self._copy_license_code)
        license_layout.addWidget(self._copy_license)
        profile_layout.addWidget(license_frame)
        detail_layout.addWidget(profile)

        users_card = QFrame()
        users_card.setObjectName("formCard")
        users_layout = QVBoxLayout(users_card)
        users_layout.setContentsMargins(14, 12, 14, 12)
        users_header = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self._users_header = users_header
        users_title = QLabel("Firma Kullan\u0131c\u0131lar\u0131")
        users_title.setObjectName("panelTitle")
        users_header.addWidget(users_title, 1)
        self._users_count = QLabel("Toplam: 0")
        self._users_count.setObjectName("metricSub")
        users_header.addWidget(self._users_count)
        self._add_user = QPushButton("\u229e  Kullan\u0131c\u0131 Ekle")
        self._add_user.setObjectName("secondaryBtn")
        self._add_user.clicked.connect(lambda: self.navigate_requested.emit("companies"))
        users_header.addWidget(self._add_user)
        users_layout.addLayout(users_header)
        self._users_table = QTableWidget(0, 8)
        self._users_table.setObjectName("dataTable")
        self._users_table.setHorizontalHeaderLabels([
            "ID", "Ad Soyad", "Kullan\u0131c\u0131 Ad\u0131", "E-posta", "Telefon",
            "Rol", "Durum", "Son Giri\u015f",
        ])
        self._users_table.setMinimumWidth(0)
        self._users_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._users_table.verticalHeader().setVisible(False)
        self._users_table.setWordWrap(True)
        users_header_view = self._users_table.horizontalHeader()
        users_header_view.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        users_header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._users_table.setMinimumHeight(108)
        users_layout.addWidget(self._users_table)
        detail_layout.addWidget(users_card)
        detail_layout.addSpacing(2)

        security_card = QFrame()
        security_card.setObjectName("formCard")
        security_layout = QVBoxLayout(security_card)
        security_layout.setContentsMargins(14, 12, 14, 12)
        security_title = QLabel("H\u0131zl\u0131 Parola ve Kimlik Do\u011frulama Masas\u0131")
        security_title.setObjectName("panelTitle")
        self._security_title = security_title
        security_title.setWordWrap(True)
        security_title.setMinimumWidth(0)
        security_layout.addWidget(security_title)
        security_controls = QHBoxLayout()
        self._security_controls = security_controls
        self._temporary_password = QLineEdit()
        self._temporary_password.setObjectName("searchInput")
        self._temporary_password.setPlaceholderText("Ge\u00e7ici parola belirleyin...")
        security_controls.addWidget(self._temporary_password, 1)
        self._password_assign = QPushButton("Ge\u00e7ici Parola Ata")
        self._password_assign.setObjectName("secondaryBtn")
        self._password_assign.clicked.connect(self._password_action_requested)
        security_controls.addWidget(self._password_assign)
        self._password_email = QPushButton("E-posta ile G\u00f6nder")
        self._password_email.setObjectName("secondaryBtn")
        self._password_email.clicked.connect(self._password_action_requested)
        security_controls.addWidget(self._password_email)
        self._password_link = QPushButton("S\u0131f\u0131rlama Ba\u011flant\u0131s\u0131")
        self._password_link.setObjectName("primaryBtn")
        self._password_link.clicked.connect(self._password_action_requested)
        security_controls.addWidget(self._password_link)
        security_layout.addLayout(security_controls)
        security_note = QLabel("Atanan tek seferlik parolalar ilk giri\u015fte de\u011fi\u015ftirilir ve 24 saat ge\u00e7erlidir.")
        security_note.setObjectName("metricSub")
        self._security_note = security_note
        security_note.setWordWrap(True)
        security_note.setMinimumWidth(0)
        security_layout.addWidget(security_note)
        detail_layout.addWidget(security_card)

        self._company_label.setObjectName("pageTitle")
        activity_card = QFrame()
        activity_card.setObjectName("formCard")
        activity_layout = QVBoxLayout(activity_card)
        activity_layout.setContentsMargins(12, 10, 12, 10)
        activity_header = QHBoxLayout()
        activity_title = QLabel("Aktivite Loglari")
        activity_title.setObjectName("panelTitle")
        activity_header.addWidget(activity_title, 1)
        self._audit_total = QLabel("0 kayit")
        self._audit_total.setObjectName("metricSub")
        activity_header.addWidget(self._audit_total)
        activity_layout.addLayout(activity_header)
        self._table = QTableWidget(0, 3)
        self._table.setObjectName("dataTable")
        self._table.setHorizontalHeaderLabels(["Aktivite", "Deger", "Kaynak"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setMinimumHeight(180)
        activity_layout.addWidget(self._table)
        detail_layout.addWidget(activity_card)
        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        detail_layout.addWidget(self._status)
        workspace.addWidget(detail_scroll, 8)
        root.addLayout(workspace, 1)
        scroll.setWidget(content)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        desktop = width >= 900
        self._root_layout.setContentsMargins(40 if desktop else 12, 12 if desktop else 8, 16 if desktop else 12, 16)
        self._root_layout.setSpacing(10 if desktop else 12)
        self._detail_layout.setSpacing(12 if desktop else 10)
        if desktop:
            self._reference_eyebrow.setFixedWidth(400)
        else:
            self._reference_eyebrow.setMinimumWidth(0)
            self._reference_eyebrow.setMaximumWidth(16_777_215)
            self._reference_eyebrow.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        self._customer_header_layout.setDirection(
            QBoxLayout.Direction.LeftToRight if desktop else QBoxLayout.Direction.TopToBottom
        )
        self._header_title_layout.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._workspace_layout.setDirection(
            QBoxLayout.Direction.LeftToRight if desktop else QBoxLayout.Direction.TopToBottom
        )
        self._workspace_layout.setSpacing(14 if desktop else 10)
        self._list_panel.setMaximumHeight(132 if desktop else 190)
        self._identity_row.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._sector_row.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._users_header.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._license_layout.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._security_controls.setDirection(
            QBoxLayout.Direction.LeftToRight if width >= 560 else QBoxLayout.Direction.TopToBottom
        )
        self._reflow_grid(self._metric_grid, self._metric_frames, 4 if desktop else 2 if width >= 560 else 1)
        self._reflow_grid(self._detail_grid, self._detail_field_frames, 3 if desktop else 2 if width >= 560 else 1)
        if width < 560:
            for column in range(self._users_table.columnCount()):
                self._users_table.horizontalHeader().setSectionResizeMode(
                    column, QHeaderView.ResizeMode.Stretch
                )
        else:
            self._users_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self._users_table.horizontalHeader().setSectionResizeMode(
                3, QHeaderView.ResizeMode.Stretch
            )
        self._detail_scroll.setMinimumHeight(0)
        if desktop:
            self._users_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._users_table.setFixedHeight(150)
        else:
            self._users_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            self._users_table.setMinimumHeight(108)
            self._users_table.setMaximumHeight(400)

    @staticmethod
    def _reflow_grid(layout, widgets, columns):
        while layout.count():
            layout.takeAt(0)
        for index, widget in enumerate(widgets):
            layout.addWidget(widget, index // columns, index % columns)

    def _load_companies(self):
        try:
            self._companies = api_client.companies()
        except Exception as exc:
            self._status.setText(f"Hata: {exc}")
            return
        current = self._company_combo.currentData()
        self._company_combo.blockSignals(True)
        self._company_list.blockSignals(True)
        self._company_combo.clear()
        self._company_list.clear()
        active_count = 0
        for company in self._companies:
            name = str(company.get("company_name") or "?")
            tenant_id = company.get("id")
            self._company_combo.addItem(
                name + "  [" + str(tenant_id or "") + "]",
                tenant_id,
            )
            active = self._company_active(company)
            active_count += int(active)
            item = QListWidgetItem("")
            item.setData(Qt.ItemDataRole.UserRole, tenant_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, dict(company))
            item.setToolTip(f"{name}\nID: {tenant_id or '-'}")
            item.setSizeHint(QSize(0, 90))
            self._company_list.addItem(item)
            self._company_list.setItemWidget(item, self._company_row_widget(company))
        self._company_combo.blockSignals(False)
        self._company_list.blockSignals(False)
        inactive_count = len(self._companies) - active_count
        self._company_counts.setText(
            f"KAYITLI L\u0130SANS HAVUZU: {len(self._companies)}/1000"
        )
        if self._companies and all("online" in company for company in self._companies):
            online_count = sum(bool(company.get("online")) for company in self._companies)
            online_percent = round(online_count * 100 / len(self._companies))
            self._online_summary.setText(f"%{online_percent} \u00c7EVR\u0130M\u0130\u00c7\u0130")
        else:
            self._online_summary.setText(f"{active_count} AKT\u0130F / {inactive_count} PAS\u0130F")
        self._tenant_pool.setText(f"TENANT POOL: {active_count} AKT\u0130F")
        self._company_filter_buttons["all"].setText(f"T\u00fcm\u00fc ({len(self._companies)})")
        self._company_filter_buttons["active"].setText(f"Aktif ({active_count})")
        self._company_filter_buttons["inactive"].setText(f"Pasif ({inactive_count})")
        self._filter_companies(self._company_search.text())
        self._set_company_filter(getattr(self, "_active_company_filter", "all"))
        if current:
            index = self._company_combo.findData(current)
            if index >= 0:
                self._company_combo.setCurrentIndex(index)
        if self._company_combo.count():
            selected = self._company_combo.currentIndex()
            self._company_list.setCurrentRow(selected if selected >= 0 else 0)
            if self._company_combo.currentIndex() < 0:
                self._company_combo.setCurrentIndex(0)
            self._company_changed(self._company_combo.currentIndex())

    @staticmethod
    def _company_active(company: dict) -> bool:
        value = company.get("active", company.get("is_active", 1))
        return str(value).casefold() not in {"0", "false", "inactive", "disabled", "pasif"}

    def _company_row_widget(self, company: dict) -> QFrame:
        row = QFrame()
        row.setObjectName("companyListItem")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(8)
        left = QVBoxLayout()
        left.setSpacing(3)
        state = QLabel("AKT\u0130F" if self._company_active(company) else "PAS\u0130F")
        state.setObjectName("companyRowState")
        name = QLabel(str(company.get("company_name") or "?"))
        name.setObjectName("companyRowName")
        contact = str(company.get("contact_name") or company.get("owner_name") or "--")
        phone = str(company.get("phone") or "--")
        email = str(company.get("email") or "--")
        name_line = QHBoxLayout()
        name_line.setSpacing(6)
        name_line.addWidget(state, 0, Qt.AlignmentFlag.AlignLeft)
        name_line.addWidget(name, 1)
        left.addLayout(name_line)
        detail = QLabel(contact + "  |  " + phone)
        detail.setObjectName("companyRowMeta")
        email_label = QLabel(email)
        email_label.setObjectName("companyRowMeta")
        left.addWidget(detail)
        left.addWidget(email_label)
        layout.addLayout(left, 1)
        right = QVBoxLayout()
        right.setSpacing(3)
        sector = QLabel(str(company.get("sector") or company.get("product_code") or "--"))
        sector.setObjectName("companyRowSector")
        plan = QLabel(str(company.get("license_type") or "--"))
        plan.setObjectName("companyRowMeta")
        right.addWidget(sector, 0, Qt.AlignmentFlag.AlignRight)
        right.addWidget(plan, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(right)
        return row

    def _company_row_changed(self, row: int):
        if row < 0:
            return
        for index in range(self._company_list.count()):
            row_widget = self._company_list.itemWidget(self._company_list.item(index))
            if row_widget:
                row_widget.setProperty("selected", index == row)
                row_widget.style().unpolish(row_widget)
                row_widget.style().polish(row_widget)
        item = self._company_list.item(row)
        tenant_id = item.data(Qt.ItemDataRole.UserRole)
        index = self._company_combo.findData(tenant_id)
        if index >= 0 and index != self._company_combo.currentIndex():
            self._company_combo.setCurrentIndex(index)

    def _filter_companies(self, query: str):
        needle = str(query or "").strip().casefold()
        for row in range(self._company_list.count()):
            item = self._company_list.item(row)
            company = item.data(Qt.ItemDataRole.UserRole + 1) or {}
            searchable = " ".join(str(company.get(key) or "") for key in (
                "company_name", "contact_name", "owner_name", "email", "phone", "tax_number", "id"
            ))
            item.setHidden(bool(needle) and needle not in searchable.casefold())
        self._refresh_company_filter()

    def _set_company_filter(self, filter_key: str):
        self._active_company_filter = filter_key
        for key, button in self._company_filter_buttons.items():
            button.setChecked(key == filter_key)
        self._refresh_company_filter()

    def _refresh_company_filter(self):
        if not hasattr(self, "_company_list"):
            return
        for row in range(self._company_list.count()):
            item = self._company_list.item(row)
            company = item.data(Qt.ItemDataRole.UserRole + 1) or {}
            active = self._company_active(company)
            key = getattr(self, "_active_company_filter", "all")
            visible_by_status = key == "all" or (key == "active" and active) or (key == "inactive" and not active)
            query = self._company_search.text().strip().casefold()
            searchable = " ".join(str(company.get(field) or "") for field in (
                "company_name", "contact_name", "owner_name", "email", "phone", "tax_number", "id"
            ))
            item.setHidden(not visible_by_status or (bool(query) and query not in searchable.casefold()))
        self._resize_company_list()

    def _resize_company_list(self):
        visible_count = sum(
            not self._company_list.item(row).isHidden()
            for row in range(self._company_list.count())
        )
        self._company_list.setFixedHeight(visible_count * 90)

    def _company_changed(self, _index: int):
        tenant_id = str(self._company_combo.currentData() or "")
        if tenant_id:
            self._load_customer(tenant_id)

    def _password_action_requested(self):
        self._status.setText("Parola i\u015flemleri merkezi kimlik servisiyle etkinle\u015ftirilmelidir.")

    def _copy_license_code(self):
        value = self._license_code.text().strip()
        if value and value != "--":
            QApplication.clipboard().setText(value)
            self._status.setText("Lisans anahtar\u0131 panoya kopyaland\u0131.")
        else:
            self._status.setText("Bu firma i\u00e7in lisans anahtar\u0131 bulunamad\u0131.")

    def _apply_sector(self):
        company = self._payload.get("company") or {}
        tenant_id = str(company.get("id") or self._company_combo.currentData() or "")
        sector = str(self._sector_combo.currentData() or "")
        if not tenant_id or not sector:
            self._status.setText("\u00d6nce bir firma se\u00e7in.")
            return
        self._status.setText("Firma sekt\u00f6r\u00fc g\u00fcncelleniyor...")
        self._sector_thread = _CompanySectorThread(tenant_id, sector)
        self._sector_thread.done.connect(self._sector_updated)
        self._sector_thread.failed.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._thread = self._sector_thread
        self._sector_thread.start()

    def _sector_updated(self, tenant_id: str, _result: dict):
        for company in self._companies:
            if str(company.get("id")) == tenant_id:
                company["sector"] = self._sector_combo.currentData()
                break
        self._status.setText("Firma sekt\u00f6r\u00fc g\u00fcncellendi.")
        self._load_customer(tenant_id)

    def _load_customer(self, tenant_id: str):
        self._status.setText("Merkezi destek verileri al\u0131n\u0131yor...")
        self._thread = _Customer360Thread(tenant_id)
        self._thread.loaded.connect(self._show_customer)
        self._thread.failed.connect(lambda error: self._status.setText(f"Hata: {error}"))
        self._thread.start()

    def _show_customer(self, payload: dict):
        self._payload = payload
        company = payload.get("company") or {}
        summary = payload.get("summary") or {}
        self._company_label.setText(str(company.get("company_name") or "Firma"))
        self._tenant_uid.setText("UID: " + str(company.get("id") or "--"))
        active = self._company_active(company)
        self._company_status.setText("AKTIF" if active else "PASIF")
        self._deactivate_company.setText("Pasif Yap" if active else "Aktif Yap")
        self._sector_combo.blockSignals(True)
        sector_index = self._sector_combo.findData(company.get("sector"))
        self._sector_combo.setCurrentIndex(sector_index if sector_index >= 0 else 0)
        self._sector_combo.blockSignals(False)
        self._company_status.setProperty("status", "success" if active else "muted")
        self._company_status.style().unpolish(self._company_status)
        self._company_status.style().polish(self._company_status)
        live = payload.get("live_status") or {}
        backup_rows = payload.get("backups") or []
        error_rows = payload.get("error_logs") or []
        self._cards["user_count"].setText(str(summary.get("user_count", len(payload.get("users") or []))))
        self._cards["backup_count"].setText(str(summary.get("backup_count", len(backup_rows))))
        self._cards["error_count"].setText(str(summary.get("error_count", len(error_rows))))
        self._cards["online"].setText("\u00c7evrimi\u00e7i" if summary.get("online") else "\u00c7evrimd\u0131\u015f\u0131")
        self._card_subs["user_count"].setText(str(summary.get("user_limit") or "Kullan\u0131c\u0131 hesaplar\u0131"))
        self._card_subs["backup_count"].setText("G\u00fcncel yedek" if backup_rows else "Kay\u0131tl\u0131 yedek yok")
        self._card_subs["error_count"].setText("Kay\u0131t yok" if not error_rows else "Son hata kayd\u0131")
        ping = live.get("ping_ms") or live.get("latency_ms")
        self._card_subs["online"].setText(("Ping: " + str(ping) + "ms") if ping is not None else "Ping verisi yok")
        self._audit_total.setText(f"{summary.get('audit_count', len(payload.get('audit_logs') or []))} kayit")
        license_item = (payload.get("licenses") or [{}])[0]
        license_code = license_item.get("license_key") or license_item.get("key") or company.get("license_key") or "--"
        self._license_code.setText(str(license_code))
        self._copy_license.setEnabled(str(license_code) != "--")
        self._detail_fields["contact_name"].setText(str(company.get("contact_name") or company.get("owner_name") or "-"))
        self._detail_fields["phone"].setText(str(company.get("phone") or "-"))
        self._detail_fields["email"].setText(str(company.get("email") or "-"))
        license_type = license_item.get("license_type") or company.get("license_type") or "-"
        license_end = company.get("license_end") or license_item.get("end_date") or "-"
        self._detail_fields["license"].setText(f"{license_type} / {license_end}")
        self._detail_fields["address"].setText(str(company.get("company_address") or company.get("address") or "-"))
        self._detail_fields["last_login"].setText(str(company.get("last_login") or live.get("last_seen") or "-"))
        users = payload.get("users") or payload.get("company_users") or []
        self._users_count.setText(f"Toplam: {len(users)}")
        self._users_table.setRowCount(len(users))
        for row, user in enumerate(users):
            values = (
                user.get("id"),
                user.get("full_name") or user.get("name"),
                user.get("username"),
                user.get("email"),
                user.get("phone"),
                "Admin" if "admin" in str(user.get("role") or "").casefold() else "User" if user.get("role") else "-",
                "AKTIF" if self._company_active(user) else "PASIF",
                user.get("last_login"),
            )
            for column, value in enumerate(values):
                self._users_table.setItem(row, column, QTableWidgetItem(str(value or "-")))
        backup = (payload.get("backups") or [{}])[0]
        latest_error = (payload.get("error_logs") or [{}])[0]
        latest_audit = (payload.get("audit_logs") or [{}])[0]
        rows = [
            ("Firma kimli\u011fi", company.get("id"), "tenants"),
            ("\u00dcr\u00fcn", company.get("product_code"), "tenants"),
            ("E-posta", company.get("email"), "tenants"),
            ("Telefon", company.get("phone"), "tenants"),
            ("Adres", company.get("company_address"), "tenants"),
            ("Lisans biti\u015fi", company.get("license_end"), "tenants"),
            ("Lisans", license_item.get("license_type") or company.get("license_type"), "licenses"),
            ("Lisans durumu", license_item.get("status"), "licenses"),
            ("Canl\u0131 cihaz", live.get("machine_name") or live.get("hardware_id"), "live_status"),
            ("Son yedek", backup.get("filename"), "backups"),
            ("Son hata", latest_error.get("message"), "error_logs"),
            ("Son audit", latest_audit.get("action") or latest_audit.get("event_type"), "audit_logs"),
        ]
        self._table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value or "-")))
        self._status.setText("Merkezi veriler g\u00fcncel.")

    def _refresh(self):
        tenant_id = str(self._company_combo.currentData() or "")
        if tenant_id:
            self._load_customer(tenant_id)
        else:
            QMessageBox.information(self, "Bilgi", "\u00d6nce bir firma se\u00e7in.")
