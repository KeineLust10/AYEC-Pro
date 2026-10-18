"""
AYEC Pro Admin Konsol - Firma Yonetimi Sayfasi
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QScrollArea, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QCheckBox, QMessageBox, QDialog, QFormLayout, QApplication, QInputDialog,
    QTextEdit, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
import api_client
from product_catalog import product_code


def _flag(value, default=False) -> bool:
    """Normalize SQLite/API boolean values, including string zero/one."""
    if isinstance(value, str):
        text = value.strip().casefold()
        if text in {"", "0", "false", "no", "off", "pasif"}:
            return False
        if text in {"1", "true", "yes", "on", "aktif"}:
            return True
    if value is None:
        return bool(default)
    return bool(value)


class _CompanyButton(QPushButton):
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class _FetchCompanies(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, search: str = "", product_code: str = ""):
        super().__init__()
        self._search = search
        self._product_code = product_code

    def run(self):
        try:
            self.done.emit(api_client.companies(self._search, self._product_code))
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchUsers(QThread):
    done = pyqtSignal(str, list)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tid = tenant_id

    def run(self):
        try:
            self.done.emit(self._tid, api_client.company_users(self._tid))
        except Exception as exc:
            self.error.emit(str(exc))


class _ResetPwThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, user_id: int, pw: str):
        super().__init__()
        self._tid = tenant_id
        self._uid = user_id
        self._pw = pw

    def run(self):
        try:
            self.done.emit(api_client.reset_user_password(self._tid, self._uid, self._pw))
        except Exception as exc:
            self.error.emit(str(exc))


class _ResetLinkThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, user_id: int):
        super().__init__()
        self._tid = tenant_id
        self._uid = user_id

    def run(self):
        try:
            self.done.emit(api_client.create_password_reset_link(self._tid, self._uid))
        except Exception as exc:
            self.error.emit(str(exc))


class _TemporaryPasswordThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, user_id: int):
        super().__init__()
        self._tid = tenant_id
        self._uid = user_id

    def run(self):
        try:
            self.done.emit(api_client.send_temporary_password(self._tid, self._uid))
        except Exception as exc:
            self.error.emit(str(exc))


class _RepairUsersThread(QThread):
    done = pyqtSignal(str, dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tid = tenant_id

    def run(self):
        try:
            self.done.emit(self._tid, api_client.repair_company_users(self._tid))
        except Exception as exc:
            self.error.emit(str(exc))


class _ToggleActiveThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, active: bool):
        super().__init__()
        self._tid = tenant_id
        self._active = active

    def run(self):
        try:
            self.done.emit(api_client.update_company(self._tid, {"active": self._active}))
        except Exception as exc:
            self.error.emit(str(exc))


class _ToggleMutedThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, muted: bool):
        super().__init__()
        self._tid = tenant_id
        self._muted = muted

    def run(self):
        try:
            self.done.emit(api_client.update_company(self._tid, {"muted": self._muted}))
        except Exception as exc:
            self.error.emit(str(exc))


class _DeleteCompanyThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tid = tenant_id

    def run(self):
        try:
            self.done.emit(api_client.delete_company(self._tid))
        except Exception as exc:
            self.error.emit(str(exc))


class _UpdateSectorThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, tenant_id: str, sector: str):
        super().__init__()
        self._tid = tenant_id
        self._sector = sector

    def run(self):
        try:
            self.done.emit(api_client.update_company_sector(self._tid, self._sector))
        except Exception as exc:
            self.error.emit(str(exc))


class _FetchCompanyOverview(QThread):
    loaded = pyqtSignal(str, dict)
    failed = pyqtSignal(str)

    def __init__(self, tenant_id: str):
        super().__init__()
        self._tenant_id = tenant_id

    def run(self):
        try:
            self.loaded.emit(self._tenant_id, api_client.customer_360(self._tenant_id))
        except Exception as exc:
            self.failed.emit(str(exc))


class CompaniesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._companies: list[dict] = []
        self._selected_tenant: dict | None = None
        self._thread = None
        self._company_workers = set()
        self._overview_thread = None
        self._overview_workers = set()
        self._company_filter = "all"
        self._build_ui()
        self._load_companies()

    def set_product_filter(self, product_name: str):
        """Keep product context visible for pages that expose tenant data."""
        self._product_filter = str(product_name or '').strip()
        self._product_code = product_code(self._product_filter)
        self._load_companies(self._search.text() if hasattr(self, '_search') else '')

    def _build_ui(self):
        self.setObjectName("companiesPage")
        self.setStyleSheet("""
            QWidget#companiesPage { background: #0e1321; color: #dee2f6; }
            QFrame#adminCompanyContext { background: #0e1321; border-bottom: 1px solid #252a39; }
            QLabel#companyBreadcrumb { color: #4cd7f6; font: 11px 'Arial'; font-weight: 700; }
            QFrame#leftPanel { background: #161b2a; border-right: 1px solid #252a39; }
            QFrame#companyMetric { background: #161b2a; border: 1px solid #252a39; border-radius: 4px; }
            QLabel#companyMetricValue { color: #4cd7f6; font-size: 21px; font-weight: 700; }
            QFrame#companyMetric QLabel { background: transparent; border: none; }
            QLabel#companyMetricCaption { color: #8c909f; font: 10px 'Arial'; font-weight: 700; }
            QPushButton#companyFilter { background: #090e1c; color: #c2c6d6; border: none; border-radius: 3px; padding: 6px 9px; }
            QPushButton#companyFilter:checked { background: #4d8eff; color: #00285d; font-weight: 700; }
            QPushButton#companyFilter:hover { background: #252a39; }
            QLabel#companyLicenseKey { background: #090e1c; color: #4cd7f6; padding: 8px; font: 10px 'Arial'; }
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        context = QFrame()
        context.setObjectName("adminCompanyContext")
        context.setFixedHeight(40)
        context_layout = QHBoxLayout(context)
        context_layout.setContentsMargins(20, 0, 16, 0)
        self._breadcrumb = QLabel("AYEC PRO / YONETIM MERKEZI / FIRMA YONETIMI & MUSTERI 360")
        self._breadcrumb.setObjectName("companyBreadcrumb")
        context_layout.addWidget(self._breadcrumb, 1)
        self._tenant_pool = QLabel("TENANT POOL: 0 AKTIF")
        self._tenant_pool.setObjectName("metricSub")
        context_layout.addWidget(self._tenant_pool)
        self._database_status = QLabel("MERKEZI VERI TABANI CANLI")
        self._database_status.setObjectName("counterLabel")
        context_layout.addWidget(self._database_status)
        refresh_companies = QPushButton("Yenile")
        refresh_companies.setObjectName("secondaryBtn")
        refresh_companies.clicked.connect(self._load_companies)
        context_layout.addWidget(refresh_companies)
        root.addWidget(context)

        workspace = QHBoxLayout()
        workspace.setContentsMargins(16, 12, 16, 12)
        workspace.setSpacing(12)

        # --- Sol panel: Firma listesi ---
        left = QFrame()
        left.setObjectName("leftPanel")
        left.setFixedWidth(365)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(12, 12, 12, 12)
        left_lay.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("Firma Listesi")
        title.setObjectName("panelTitle")
        title_row.addWidget(title, 1)
        self._company_counts = QLabel("0 / 0")
        self._company_counts.setObjectName("metricSub")
        title_row.addWidget(self._company_counts)
        left_lay.addLayout(title_row)

        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setPlaceholderText("Firma adi, yetkili veya vergi no ara...")
        self._search.textChanged.connect(self._on_search)
        left_lay.addWidget(self._search)

        status_filters = QHBoxLayout()
        self._company_filter_buttons = {}
        for filter_key, label in (("all", "Tumu"), ("active", "Aktif"), ("inactive", "Pasif")):
            button = QPushButton(label)
            button.setObjectName("companyFilter")
            button.setCheckable(True)
            button.setChecked(filter_key == "all")
            button.clicked.connect(lambda _checked, key=filter_key: self._set_company_filter(key))
            status_filters.addWidget(button)
            self._company_filter_buttons[filter_key] = button
        left_lay.addLayout(status_filters)

        self._company_list = QScrollArea()
        self._company_list.setWidgetResizable(True)
        self._company_list.setObjectName("companyList")
        self._list_inner = QFrame()
        self._list_inner_lay = QVBoxLayout(self._list_inner)
        self._list_inner_lay.setContentsMargins(0, 0, 0, 0)
        self._list_inner_lay.setSpacing(4)
        self._company_group = QButtonGroup(self)
        self._company_group.setExclusive(True)
        self._company_list.setWidget(self._list_inner)
        left_lay.addWidget(self._company_list, 1)

        workspace.addWidget(left, 4)

        # --- Sag panel: Detay ---
        self._detail = QFrame()
        self._detail.setObjectName("detailPanel")
        detail_lay = QVBoxLayout(self._detail)
        detail_lay.setContentsMargins(0, 0, 0, 0)
        detail_lay.setSpacing(10)

        # Ust: bilgiler
        detail_header = QFrame()
        detail_header.setObjectName("formCard")
        detail_header_layout = QHBoxLayout(detail_header)
        detail_header_layout.setContentsMargins(12, 10, 12, 10)
        self._detail_title = QLabel("Firma secin")
        self._detail_title.setObjectName("detailTitle")
        detail_header_layout.addWidget(self._detail_title, 1)
        self._company_identity = QLabel("UID: -")
        self._company_identity.setObjectName("metricSub")
        detail_header_layout.addWidget(self._company_identity)
        self._company_state = QLabel("-")
        self._company_state.setObjectName("counterLabel")
        detail_header_layout.addWidget(self._company_state)
        self._company_action_layout = QHBoxLayout()
        self._company_action_layout.setSpacing(6)
        detail_header_layout.addLayout(self._company_action_layout)
        detail_lay.addWidget(detail_header)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self._metric_values = {}
        for key, caption in (("user_count", "KULLANICI HAVUZU"), ("backup_count", "BULUT YEDEK"), ("error_count", "KRITIK HATA LOGU"), ("online", "CANLI OTURUM")):
            metric = QFrame()
            metric.setObjectName("companyMetric")
            metric_layout = QVBoxLayout(metric)
            metric_layout.setContentsMargins(10, 8, 10, 8)
            value = QLabel("-")
            value.setObjectName("companyMetricValue")
            label = QLabel(caption)
            label.setObjectName("companyMetricCaption")
            note = QLabel("-")
            note.setObjectName("metricSub")
            metric_layout.addWidget(value)
            metric_layout.addWidget(label)
            metric_layout.addWidget(note)
            metrics.addWidget(metric, 1)
            self._metric_values[key] = (value, note)
        profile = QFrame()
        profile.setObjectName("formCard")
        profile_layout = QVBoxLayout(profile)
        profile_layout.setContentsMargins(10, 8, 10, 8)
        profile_layout.setSpacing(7)
        profile_title = QLabel("Firma ve Lisans Parametreleri")
        profile_title.setObjectName("panelTitle")
        profile_layout.addWidget(profile_title)
        info_row = QHBoxLayout()
        self._info_left = QFormLayout()
        self._info_right = QFormLayout()
        info_row.addLayout(self._info_left)
        info_row.addSpacing(40)
        info_row.addLayout(self._info_right)
        info_row.addStretch()
        profile_layout.addLayout(info_row)

        # Aksiyon butonlari
        btn_row = QHBoxLayout()
        sector_lbl = QLabel("Sekt\u00f6r:")
        sector_lbl.setObjectName("infoKey")
        btn_row.addWidget(sector_lbl)
        self._sector_combo = QComboBox()
        self._sector_combo.setObjectName("fieldInput")
        self._sector_combo.setFixedHeight(36)
        self._sector_combo.addItem("Teknik Servis", "teknik_servis")
        self._sector_combo.addItem("Otomotiv Servis", "otomotiv")
        self._sector_combo.setEnabled(False)
        btn_row.addWidget(self._sector_combo)
        self._sector_btn = QPushButton("Sekt\u00f6r\u00fc Uygula")
        self._sector_btn.setObjectName("primaryBtn")
        self._sector_btn.setFixedHeight(36)
        self._sector_btn.clicked.connect(self._change_sector)
        self._sector_btn.setEnabled(False)
        btn_row.addWidget(self._sector_btn)
        btn_row.addSpacing(12)
        self._toggle_btn = QPushButton("Pasif Yap")
        self._toggle_btn.setObjectName("dangerBtn")
        self._toggle_btn.setFixedHeight(36)
        self._toggle_btn.clicked.connect(self._toggle_active)
        self._toggle_btn.setEnabled(False)
        self._company_action_layout.addWidget(self._toggle_btn)
        self._mute_btn = QPushButton("Firmayi Sustur")
        self._mute_btn.setObjectName("dangerBtn")
        self._mute_btn.setFixedHeight(36)
        self._mute_btn.clicked.connect(self._toggle_muted)
        self._mute_btn.setEnabled(False)
        self._company_action_layout.addWidget(self._mute_btn)
        self._delete_btn = QPushButton("\U0001f5d1 Firma Sil")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setFixedHeight(36)
        self._delete_btn.clicked.connect(self._delete_company)
        self._delete_btn.setEnabled(False)
        self._company_action_layout.addWidget(self._delete_btn)
        btn_row.addStretch()
        detail_lay.addLayout(btn_row)
        detail_lay.addLayout(metrics)
        detail_lay.addWidget(profile)

        license_key_card = QFrame()
        license_key_card.setObjectName("formCard")
        license_key_layout = QHBoxLayout(license_key_card)
        license_key_layout.setContentsMargins(10, 7, 10, 7)
        license_key_caption = QLabel("AKTIF LISANS ANAHTARI")
        license_key_caption.setObjectName("metricSub")
        license_key_layout.addWidget(license_key_caption)
        self._license_key_value = QLabel("-")
        self._license_key_value.setObjectName("companyLicenseKey")
        self._license_key_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        license_key_layout.addWidget(self._license_key_value, 1)
        self._copy_license_button = QPushButton("Kodu Kopyala")
        self._copy_license_button.setObjectName("secondaryBtn")
        self._copy_license_button.clicked.connect(self._copy_license_key)
        self._copy_license_button.setEnabled(False)
        license_key_layout.addWidget(self._copy_license_button)
        detail_lay.addWidget(license_key_card)

        # Kullanici tablosu
        usr_lbl = QLabel("Kullan\u0131c\u0131lar")
        usr_lbl.setObjectName("sectionTitle")
        detail_lay.addWidget(usr_lbl)

        self._user_table = QTableWidget()
        self._user_table.setObjectName("dataTable")
        self._user_table.setColumnCount(8)
        self._user_table.setHorizontalHeaderLabels([
            "ID", "Ad Soyad", "Kullan\u0131c\u0131 Ad\u0131", "E-posta", "Telefon",
            "Rol", "Durum", "Son Giri\u015f"
        ])
        self._user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        detail_lay.addWidget(self._user_table, 1)

        pw_row = QHBoxLayout()
        self._pw_input = QLineEdit()
        self._pw_input.setObjectName("fieldInput")
        self._pw_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pw_input.setPlaceholderText("Ge\u00e7ici parola girin...")
        pw_row.addWidget(self._pw_input, 1)
        self._reset_btn = QPushButton("\ud83d\udd11 Ge\u00e7ici Parola Ata")
        self._reset_btn.setObjectName("primaryBtn")
        self._reset_btn.setFixedHeight(36)
        self._reset_btn.clicked.connect(self._reset_password)
        self._reset_btn.setEnabled(False)
        pw_row.addWidget(self._reset_btn)
        self._email_temp_btn = QPushButton("\ud83d\udce7 E-posta ile Gecici Parola")
        self._email_temp_btn.setObjectName("primaryBtn")
        self._email_temp_btn.setFixedHeight(36)
        self._email_temp_btn.clicked.connect(self._send_temporary_password)
        self._email_temp_btn.setEnabled(False)
        pw_row.addWidget(self._email_temp_btn)
        self._reset_link_btn = QPushButton("\ud83d\udd17 S\u0131f\u0131rlama Ba\u011flant\u0131s\u0131")
        self._reset_link_btn.setObjectName("secondaryBtn")
        self._reset_link_btn.setFixedHeight(36)
        self._reset_link_btn.clicked.connect(self._create_reset_link)
        self._reset_link_btn.setEnabled(False)
        pw_row.addWidget(self._reset_link_btn)
        self._repair_users_btn = QPushButton("Eksik Yonetici Kaydini Kurtar")
        self._repair_users_btn.setObjectName("secondaryBtn")
        self._repair_users_btn.setFixedHeight(36)
        self._repair_users_btn.clicked.connect(self._repair_missing_users)
        self._repair_users_btn.setVisible(False)
        pw_row.addWidget(self._repair_users_btn)
        detail_lay.addLayout(pw_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("statusLabel")
        detail_lay.addWidget(self._status_lbl)

        workspace.addWidget(self._detail, 8)
        root.addLayout(workspace, 1)
        self._user_table.cellClicked.connect(self._on_user_select)
        self._user_table.itemDoubleClicked.connect(self._show_user_details)

    def _load_companies(self, search: str = ""):
        requested_search = str(search or "")
        requested_product = str(getattr(self, "_product_code", ""))
        t = _FetchCompanies(requested_search, requested_product)
        t.done.connect(
            lambda companies, query=requested_search, product=requested_product:
                self._populate_list_if_current(query, product, companies)
        )
        t.error.connect(
            lambda error, query=requested_search, product=requested_product:
                self._show_company_error_if_current(query, product, error)
        )
        self._company_workers.add(t)
        t.finished.connect(lambda current=t: self._company_workers.discard(current))
        t.start()
        self._thread = t

    def _company_request_is_current(self, search: str, product_code_value: str) -> bool:
        return (
            product_code_value == str(getattr(self, "_product_code", ""))
            and search == (self._search.text() if hasattr(self, "_search") else "")
        )

    def _populate_list_if_current(self, search: str, product_code_value: str, companies: list):
        if self._company_request_is_current(search, product_code_value):
            self._populate_list(companies)

    def _show_company_error_if_current(self, search: str, product_code_value: str, error: str):
        if self._company_request_is_current(search, product_code_value):
            self._status_lbl.setText(f"Hata: {error}")

    def _on_search(self, text: str):
        self._load_companies(text)

    def _populate_list(self, companies: list):
        self._companies = companies
        while self._list_inner_lay.count():
            item = self._list_inner_lay.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self._company_group.removeButton(widget)
                widget.deleteLater()

        for c in companies:
            btn = _CompanyButton(c.get("company_name", "?"))
            btn.setObjectName("companyBtn")
            btn.setCheckable(True)
            is_active = _flag(c.get("active"), True)
            is_muted = _flag(c.get("muted"))
            status = "[SUSTURULDU]" if is_muted else "[AKTIF]" if is_active else "[PASIF]"
            contact = str(c.get("contact_name") or "-")
            phone = str(c.get("phone") or "-")
            email = str(c.get("email") or "-")
            sector = "Otomotiv" if str(c.get("sector") or "") == "otomotiv" else "Teknik Servis"
            license_name = str(c.get("license_type") or "-")
            btn.setText(f"{status}  {c.get('company_name', '?')}  |  {sector}\n{contact} | {phone}\n{email}  |  {license_name}")
            btn.setStyleSheet("text-align: left; padding: 9px 10px; font-size: 11px;")
            btn.setMinimumHeight(82)
            btn._company_data = dict(c)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._company_group.addButton(btn)
            btn.clicked.connect(lambda checked, firm=c: self._select_company(firm))
            btn.double_clicked.connect(lambda firm=c: self._show_company_details(firm))
            self._list_inner_lay.addWidget(btn)
        self._list_inner_lay.addStretch()
        self._company_list.verticalScrollBar().setValue(0)
        active_count = sum(_flag(company.get("active"), True) for company in companies)
        self._company_counts.setText(f"{active_count} / {len(companies)} active")
        self._tenant_pool.setText(f"TENANT POOL: {active_count} AKTIF")
        self._refresh_company_filter()

    def _set_company_filter(self, filter_key: str):
        self._company_filter = filter_key
        for key, button in self._company_filter_buttons.items():
            button.setChecked(key == filter_key)
        self._refresh_company_filter()

    def _refresh_company_filter(self):
        if not hasattr(self, "_company_group"):
            return
        counts = {"all": len(self._companies), "active": 0, "inactive": 0}
        for company in self._companies:
            counts["active" if _flag(company.get("active"), True) else "inactive"] += 1
        for key, button in self._company_filter_buttons.items():
            base = button.property("baseLabel") or button.text()
            button.setProperty("baseLabel", base.split(" (")[0])
            button.setText(f"{button.property('baseLabel')} ({counts[key]})")
        for button in self._company_group.buttons():
            company = getattr(button, "_company_data", {})
            active = _flag(company.get("active"), True)
            status_visible = self._company_filter == "all" or (self._company_filter == "active" and active) or (self._company_filter == "inactive" and not active)
            button.setVisible(status_visible)

    def _select_company(self, c: dict):
        self._selected_tenant = c
        self._status_lbl.setText("")
        tid = c.get("id", "")
        name = c.get("company_name", "?")
        self._detail_title.setText(str(name))
        self._company_identity.setText(f"UID: {tid or '-'}")
        is_active = _flag(c.get("active"), True)
        is_muted = _flag(c.get("muted"))
        self._company_state.setText("SISTEM SUSTURULDU" if is_muted else "SISTEM AKTIF" if is_active else "SISTEM PASIF")
        self._toggle_btn.setEnabled(True)
        self._mute_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._toggle_btn.setText("Pasif Yap" if is_active else "Aktif Yap")
        self._toggle_btn.setObjectName("dangerBtn" if is_active else "successBtn")
        is_muted = _flag(c.get("muted"))
        self._mute_btn.setText("Susturmayi Kaldir" if is_muted else "Firmayi Sustur")
        self._mute_btn.setObjectName("successBtn" if is_muted else "dangerBtn")
        sector = str(c.get("sector") or "teknik_servis")
        sector_index = self._sector_combo.findData(sector)
        self._sector_combo.setCurrentIndex(max(0, sector_index))
        self._sector_combo.setEnabled(True)
        self._sector_btn.setEnabled(True)
        for key, fallback in (("user_count", "-"), ("backup_count", "-"), ("error_count", "-"), ("online", "-")):
            self._metric_values[key][0].setText(str(c.get(key, fallback)))
            self._metric_values[key][1].setText("-")
        self._license_key_value.setText("-")
        self._copy_license_button.setEnabled(False)

        # Sol bilgiler doldur
        for lay in [self._info_left, self._info_right]:
            while lay.rowCount():
                lay.removeRow(0)

        left_fields = [
            ("Firma Adi", name),
            ("Yetkili", c.get("contact_name", "-")),
            ("Telefon", c.get("phone", "-")),
            ("E-posta", c.get("email", "-")),
            ("Kurulum Adresi", c.get("company_address", "-")),
        ]
        right_fields = [
            ("Sekt\u00f6r", "Otomotiv Servis" if sector == "otomotiv" else "Teknik Servis"),
            ("Kayit", c.get("created_at", "-")),
            ("Lisans", c.get("license_type", "Standart")),
            ("Lisans Bitis", c.get("license_end", "-")),
            ("Son Giris", c.get("last_login", "-")),
            ("Enlem", c.get("installation_lat", "-")),
            ("Boylam", c.get("installation_lng", "-")),
        ]
        for label, val in left_fields:
            lbl = QLabel(label + ":")
            lbl.setObjectName("infoKey")
            v = QLabel(str(val or "-"))
            v.setObjectName("infoVal")
            self._info_left.addRow(lbl, v)
        for label, val in right_fields:
            lbl = QLabel(label + ":")
            lbl.setObjectName("infoKey")
            v = QLabel(str(val or "-"))
            v.setObjectName("infoVal")
            if label == "Sekt\u00f6r":
                self._sector_info_value = v
            self._info_right.addRow(lbl, v)

        # Kullanicilari yukle
        self._user_table.setRowCount(0)
        self._reset_btn.setEnabled(False)
        self._email_temp_btn.setEnabled(False)
        self._reset_link_btn.setEnabled(False)
        self._repair_users_btn.setVisible(False)
        t = _FetchUsers(tid)
        t.done.connect(self._populate_users)
        t.error.connect(lambda e: self._status_lbl.setText(f"Kullanici hatasi: {e}"))
        t.start()
        self._thread = t
        overview = _FetchCompanyOverview(str(tid))
        overview.loaded.connect(self._populate_company_overview)
        overview.failed.connect(lambda error: self._status_lbl.setText(f"Firma ozeti alinamadi: {error}"))
        overview.finished.connect(lambda worker=overview: self._overview_workers.discard(worker))
        self._overview_workers.add(overview)
        self._overview_thread = overview
        overview.start()

    def _populate_company_overview(self, tenant_id: str, payload: dict):
        if str((self._selected_tenant or {}).get("id") or "") != str(tenant_id or ""):
            return
        summary = payload.get("summary") or {}
        live = payload.get("live_status") or {}
        backup = (payload.get("backups") or [{}])[0]
        users = payload.get("users") or payload.get("company_users") or []
        values = {
            "user_count": (summary.get("user_count", len(users)), "S\u0131n\u0131rs\u0131z"),
            "backup_count": (summary.get("backup_count", len(payload.get("backups") or [])), str(backup.get("filename") or "Guncel (Bugun)")),
            "error_count": (summary.get("error_count", len(payload.get("error_logs") or [])), "Kayit Yok" if not summary.get("error_count") else "Kritik kayit"),
            "online": ("Cevrimici" if summary.get("online") else "Cevrimdisi", f"Ping: {live.get('ping_ms', '-')} ms"),
        }
        for key, (value, note) in values.items():
            self._metric_values[key][0].setText(str(value))
            self._metric_values[key][1].setText(str(note))
        license_item = (payload.get("licenses") or [{}])[0]
        license_key = str(license_item.get("license_code") or license_item.get("license_key") or "")
        self._license_key_value.setText(license_key or "-")
        self._copy_license_button.setEnabled(bool(license_key))

    def _copy_license_key(self):
        license_key = self._license_key_value.text().strip()
        if license_key and license_key != "-":
            QApplication.clipboard().setText(license_key)
            self._status_lbl.setText("Lisans anahtari panoya kopyalandi.")

    def _populate_users(self, tid: str, users: list):
        selected_id = str((self._selected_tenant or {}).get("id") or "")
        if str(tid or "") != selected_id:
            return
        self._user_table.setRowCount(0)
        for u in users:
            row = self._user_table.rowCount()
            self._user_table.insertRow(row)
            self._user_table.setItem(row, 0, QTableWidgetItem(str(u.get("id", ""))))
            self._user_table.setItem(row, 1, QTableWidgetItem(str(u.get("full_name") or u.get("username", ""))))
            self._user_table.setItem(row, 2, QTableWidgetItem(str(u.get("username", ""))))
            self._user_table.setItem(row, 3, QTableWidgetItem(str(u.get("email", "-"))))
            self._user_table.setItem(row, 4, QTableWidgetItem(str(u.get("phone", "-"))))
            self._user_table.setItem(row, 5, QTableWidgetItem(str(u.get("role", ""))))
            self._user_table.setItem(
                row, 6, QTableWidgetItem("Aktif" if int(u.get("active", 1) or 0) else "Pasif")
            )
            self._user_table.setItem(row, 7, QTableWidgetItem(str(u.get("last_login", "-"))))
        self._repair_users_btn.setVisible(not users)
        if not users:
            self._status_lbl.setText(
                "Bu firmada kullanici kaydi bulunamadi. Korunan yedekten kurtarabilirsiniz."
            )

    def _repair_missing_users(self):
        if not self._selected_tenant:
            return
        tenant_id = str(self._selected_tenant.get("id") or "")
        reply = QMessageBox.question(
            self,
            "Kullanici Kaydini Kurtar",
            "Bu firmanin kullanicilari son korunan silme-oncesi yedekten geri "
            "yuklenecek. Devam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._repair_users_btn.setEnabled(False)
        worker = _RepairUsersThread(tenant_id)
        worker.done.connect(self._users_repaired)
        worker.error.connect(self._users_repair_failed)
        worker.start()
        self._thread = worker

    def _users_repaired(self, tenant_id: str, result: dict):
        self._repair_users_btn.setEnabled(True)
        restored = int(result.get("restored_users") or 0)
        self._status_lbl.setText(f"{restored} kullanici kaydi korunan yedekten kurtarildi.")
        if str((self._selected_tenant or {}).get("id") or "") == tenant_id:
            worker = _FetchUsers(tenant_id)
            worker.done.connect(self._populate_users)
            worker.error.connect(self._users_repair_failed)
            worker.start()
            self._thread = worker

    def _users_repair_failed(self, error: str):
        self._repair_users_btn.setEnabled(True)
        self._status_lbl.setText(f"Kullanici kurtarma hatasi: {error}")

    def _on_user_select(self, row: int, col: int):
        self._reset_btn.setEnabled(True)
        self._email_temp_btn.setEnabled(True)
        self._reset_link_btn.setEnabled(True)

    def _send_temporary_password(self):
        if not self._selected_tenant:
            return
        row = self._user_table.currentRow()
        if row < 0:
            self._status_lbl.setText("Lutfen bir kullanici secin.")
            return
        user_id = int(self._user_table.item(row, 0).text())
        username = self._user_table.item(row, 2).text()
        email = self._user_table.item(row, 3).text()
        reply = QMessageBox.question(
            self,
            "Gecici Parola",
            f"{username} kullanicisina {email} adresine tek kullanimlik gecici parola gonderilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._email_temp_btn.setEnabled(False)
        worker = _TemporaryPasswordThread(str(self._selected_tenant["id"]), user_id)
        worker.done.connect(self._temporary_password_ready)
        worker.error.connect(lambda error: self._status_lbl.setText(f"Hata: {error}"))
        worker.finished.connect(lambda: self._email_temp_btn.setEnabled(True))
        worker.start()
        self._thread = worker

    def _temporary_password_ready(self, result: dict):
        if result.get("mail_sent"):
            self._status_lbl.setText(
                f"Gecici parola {result.get('recipient', '-') } adresine gonderildi."
            )
        else:
            self._status_lbl.setText(
                f"E-posta gonderilemedi: {result.get('mail_message') or 'SMTP hatasi'}"
            )

    def _show_company_details(self, company: dict | None = None):
        company = company or self._selected_tenant
        if not company:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Firma Ayrintilari")
        dialog.setMinimumWidth(620)
        layout = QVBoxLayout(dialog)
        title = QLabel(str(company.get("company_name") or "Firma"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        form = QFormLayout()
        fields = (
            ("Firma Kimligi", "id"), ("Firma Adi", "company_name"),
            ("Yetkili", "contact_name"), ("Telefon", "phone"),
            ("E-posta", "email"), ("Sektor", "sector"),
            ("Kayit Tarihi", "created_at"), ("Lisans", "license_type"),
            ("Lisans Durumu", "license_status"), ("Lisans Bitisi", "license_end"),
            ("Adres", "company_address"), ("Enlem", "installation_lat"),
            ("Boylam", "installation_lng"), ("Son Giris", "last_login"),
        )
        for label, key in fields:
            value = str(company.get(key) or "-")
            field = QTextEdit()
            field.setReadOnly(True)
            field.setPlainText(value)
            field.setMaximumHeight(42 if key != "company_address" else 64)
            form.addRow(QLabel(label + ":"), field)
        layout.addLayout(form)
        close_button = QPushButton("Kapat")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _show_user_details(self, item):
        row = item.row()
        if row < 0:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Kullanici Ayrintilari")
        dialog.setMinimumWidth(560)
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        labels = ("ID", "Ad Soyad", "Kullanici Adi", "E-posta", "Telefon", "Rol", "Durum", "Son Giris")
        for col, label in enumerate(labels):
            table_item = self._user_table.item(row, col)
            value = str(table_item.text() if table_item else "-")
            field = QTextEdit()
            field.setReadOnly(True)
            field.setPlainText(value)
            field.setMaximumHeight(42)
            form.addRow(QLabel(label + ":"), field)
        layout.addLayout(form)
        close_button = QPushButton("Kapat")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        dialog.exec()

    def _reset_password(self):
        if not self._selected_tenant:
            return
        row = self._user_table.currentRow()
        if row < 0:
            self._status_lbl.setText("Lutfen bir kullanici secin.")
            return
        user_id = int(self._user_table.item(row, 0).text())
        username = self._user_table.item(row, 2).text()
        new_pw = self._pw_input.text().strip()
        if len(new_pw) < 6:
            self._status_lbl.setText("Sifre en az 6 karakter olmali.")
            return
        reply = QMessageBox.question(self, "Onay",
            f"'{username}' kullanicisinin sifresi '{new_pw}' olarak degistirilsin mi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        t = _ResetPwThread(self._selected_tenant["id"], user_id, new_pw)
        t.done.connect(lambda d: self._status_lbl.setText("\u2705 Sifre basariyla sifirlandi!"))
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t
        self._pw_input.clear()

    def _create_reset_link(self):
        if not self._selected_tenant:
            return
        row = self._user_table.currentRow()
        if row < 0:
            self._status_lbl.setText("L\u00fctfen bir kullan\u0131c\u0131 se\u00e7in.")
            return
        user_id = int(self._user_table.item(row, 0).text())
        worker = _ResetLinkThread(self._selected_tenant["id"], user_id)
        worker.done.connect(self._reset_link_ready)
        worker.error.connect(lambda error: self._status_lbl.setText(f"Hata: {error}"))
        worker.start()
        self._thread = worker

    def _reset_link_ready(self, result: dict):
        reset_url = str(result.get("reset_url") or "")
        if not reset_url:
            self._status_lbl.setText("S\u0131f\u0131rlama ba\u011flant\u0131s\u0131 olu\u015fturulamad\u0131.")
            return
        QApplication.clipboard().setText(reset_url)
        expires_at = str(result.get("expires_at") or "")
        self._status_lbl.setText(
            f"\u2713 Tek kullan\u0131ml\u0131k ba\u011flant\u0131 panoya kopyaland\u0131. Biti\u015f: {expires_at}"
        )

    def _toggle_active(self):
        if not self._selected_tenant:
            return
        is_active = _flag(self._selected_tenant.get("active"), True)
        action = "Pasif Yap" if is_active else "Aktif Yap"
        reply = QMessageBox.question(self, "Onay",
            f"'{self._selected_tenant.get('company_name')}' firmasi {action.lower()} isteniyor. Devam?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        new_active = not is_active
        t = _ToggleActiveThread(self._selected_tenant["id"], new_active)
        t.done.connect(lambda d: self._active_updated(new_active, d))
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t

    def _active_updated(self, active: bool, _result: dict):
        if self._selected_tenant:
            self._selected_tenant["active"] = int(active)
            for company in self._companies:
                if company.get("id") == self._selected_tenant.get("id"):
                    company["active"] = int(active)
                    break
            self._toggle_btn.setText("Pasif Yap" if active else "Aktif Yap")
            self._toggle_btn.setObjectName("dangerBtn" if active else "successBtn")
            self._toggle_btn.style().unpolish(self._toggle_btn)
            self._toggle_btn.style().polish(self._toggle_btn)
        self._status_lbl.setText("Firma durumu guncellendi.")
        self._load_companies()

    def _toggle_muted(self):
        if not self._selected_tenant:
            return
        is_muted = _flag(self._selected_tenant.get("muted"))
        action = "susturmayi kaldirmak" if is_muted else "firmayi susturmak"
        message = (
            "Susturulan firma programi acamaz, lisans talebi olusturamaz ve "
            "yonetici ile iletisime gecmesi istenir.\n\n"
            if not is_muted else "Firma yeniden erisim kontrolune alinacak.\n\n"
        )
        reply = QMessageBox.question(
            self, "Firma Susturma Onayi",
            message + f"'{self._selected_tenant.get('company_name')}' icin {action} istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        worker = _ToggleMutedThread(self._selected_tenant["id"], not is_muted)
        worker.done.connect(lambda _data: (self._status_lbl.setText("Firma susturma durumu guncellendi."), self._load_companies()))
        worker.error.connect(lambda error: self._status_lbl.setText(f"Hata: {error}"))
        worker.start()
        self._thread = worker

    def _delete_company(self):
        if not self._selected_tenant:
            return
        company_name = str(self._selected_tenant.get("company_name") or "")
        prompt = (
            f"'{company_name}' firmasi aktif listeden kaldirilacak ve veritabani sunucuda arsivlenecek.\n\n"
            f"Onaylamak icin firma adini aynen yazin: {company_name}"
        )
        confirmation, accepted = QInputDialog.getText(self, "Firma Silme Onayi", prompt)
        if not accepted:
            return
        if confirmation.strip() != company_name:
            self._status_lbl.setText("Firma adi dogrulanamadi. Silme islemi iptal edildi.")
            return
        self._delete_btn.setEnabled(False)
        worker = _DeleteCompanyThread(str(self._selected_tenant.get("id") or ""))
        worker.done.connect(self._company_deleted)
        worker.error.connect(self._company_delete_failed)
        worker.start()
        self._thread = worker

    def _company_deleted(self, result: dict):
        archive = str(result.get("archive") or "")
        self._selected_tenant = None
        self._detail_title.setText("Firma secin")
        self._toggle_btn.setEnabled(False)
        self._mute_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._sector_combo.setEnabled(False)
        self._sector_btn.setEnabled(False)
        self._user_table.setRowCount(0)
        self._repair_users_btn.setVisible(False)
        self._reset_btn.setEnabled(False)
        self._email_temp_btn.setEnabled(False)
        self._reset_link_btn.setEnabled(False)
        self._status_lbl.setText(f"Firma silindi ve arsive tasindi: {archive}")
        self._load_companies()

    def _company_delete_failed(self, error: str):
        self._delete_btn.setEnabled(bool(self._selected_tenant))
        self._status_lbl.setText(f"Firma silinemedi: {error}")

    def _change_sector(self):
        if not self._selected_tenant:
            return
        sector = str(self._sector_combo.currentData() or "")
        current = str(self._selected_tenant.get("sector") or "teknik_servis")
        same_sector = sector == current
        sector_name = "Otomotiv Servis" if sector == "otomotiv" else "Teknik Servis"
        company_name = str(self._selected_tenant.get("company_name") or "")
        action_text = "yeniden uygulansin" if same_sector else "sektorune gecirilsin"
        reply = QMessageBox.question(
            self,
            "Sekt\u00f6r Degisikligi",
            f"'{company_name}' firmasi icin {sector_name} {action_text} mi?\n\n"
            "Firma verileri silinmez. Web, mobil ve masaustu menuleri yeni sektore gore acilir.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            self._sector_combo.setCurrentIndex(max(0, self._sector_combo.findData(current)))
            return
        self._sector_combo.setEnabled(False)
        self._sector_btn.setEnabled(False)
        t = _UpdateSectorThread(self._selected_tenant["id"], sector)
        t.done.connect(lambda result: self._sector_updated(sector, result))
        t.error.connect(self._sector_update_failed)
        t.start()
        self._thread = t

    def _sector_updated(self, sector: str, _result: dict):
        if self._selected_tenant:
            self._selected_tenant["sector"] = sector
            selected_id = self._selected_tenant.get("id")
            for company in self._companies:
                if company.get("id") == selected_id:
                    company["sector"] = sector
                    break
            if hasattr(self, "_sector_info_value"):
                self._sector_info_value.setText(
                    "Otomotiv Servis" if sector == "otomotiv" else "Teknik Servis"
                )
        self._sector_combo.setEnabled(True)
        self._sector_btn.setEnabled(True)
        self._status_lbl.setText("\u2705 Sekt\u00f6r firmaya uygulandi ve yerel kayit onarildi.")

    def _sector_update_failed(self, error: str):
        if self._selected_tenant:
            current = str(self._selected_tenant.get("sector") or "teknik_servis")
            self._sector_combo.setCurrentIndex(max(0, self._sector_combo.findData(current)))
        self._sector_combo.setEnabled(True)
        self._sector_btn.setEnabled(True)
        self._status_lbl.setText(f"Sekt\u00f6r guncelleme hatasi: {error}")
