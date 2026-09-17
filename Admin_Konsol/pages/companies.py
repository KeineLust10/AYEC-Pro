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


class CompaniesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._companies: list[dict] = []
        self._selected_tenant: dict | None = None
        self._thread = None
        self._build_ui()
        self._load_companies()

    def set_product_filter(self, product_name: str):
        """Keep product context visible for pages that expose tenant data."""
        self._product_filter = str(product_name or '').strip()
        self._product_code = product_code(self._product_filter)
        self._load_companies(self._search.text() if hasattr(self, '_search') else '')

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sol panel: Firma listesi ---
        left = QFrame()
        left.setObjectName("leftPanel")
        left.setFixedWidth(340)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 20, 16, 16)
        left_lay.setSpacing(12)

        title = QLabel("\ud83c\udfe2 Firma Listesi")
        title.setObjectName("panelTitle")
        left_lay.addWidget(title)

        self._search = QLineEdit()
        self._search.setObjectName("searchInput")
        self._search.setPlaceholderText("\ud83d\udd0d Firma ara...")
        self._search.textChanged.connect(self._on_search)
        left_lay.addWidget(self._search)

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

        root.addWidget(left)

        # --- Sag panel: Detay ---
        self._detail = QFrame()
        self._detail.setObjectName("detailPanel")
        detail_lay = QVBoxLayout(self._detail)
        detail_lay.setContentsMargins(28, 24, 28, 24)
        detail_lay.setSpacing(20)

        # Ust: bilgiler
        self._detail_title = QLabel("Firma secin")
        self._detail_title.setObjectName("detailTitle")
        detail_lay.addWidget(self._detail_title)

        info_row = QHBoxLayout()
        self._info_left = QFormLayout()
        self._info_right = QFormLayout()
        info_row.addLayout(self._info_left)
        info_row.addSpacing(40)
        info_row.addLayout(self._info_right)
        info_row.addStretch()
        detail_lay.addLayout(info_row)

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
        btn_row.addWidget(self._toggle_btn)
        self._delete_btn = QPushButton("\U0001f5d1 Firma Sil")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setFixedHeight(36)
        self._delete_btn.clicked.connect(self._delete_company)
        self._delete_btn.setEnabled(False)
        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        detail_lay.addLayout(btn_row)

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

        root.addWidget(self._detail, 1)
        self._user_table.cellClicked.connect(self._on_user_select)
        self._user_table.itemDoubleClicked.connect(self._show_user_details)

    def _load_companies(self, search: str = ""):
        t = _FetchCompanies(search, getattr(self, '_product_code', ''))
        t.done.connect(self._populate_list)
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t

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
            is_active = c.get("active", True)
            status = "[AKTIF]" if is_active else "[PASIF]"
            contact = str(c.get("contact_name") or "-")
            phone = str(c.get("phone") or "-")
            email = str(c.get("email") or "-")
            btn.setText(f"{status}  {c.get('company_name', '?')}\n{contact} | {phone}\n{email}")
            btn.setMinimumHeight(70)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._company_group.addButton(btn)
            btn.clicked.connect(lambda checked, firm=c: self._select_company(firm))
            btn.double_clicked.connect(lambda firm=c: self._show_company_details(firm))
            self._list_inner_lay.addWidget(btn)
        self._list_inner_lay.addStretch()
        self._company_list.verticalScrollBar().setValue(0)

    def _select_company(self, c: dict):
        self._selected_tenant = c
        self._status_lbl.setText("")
        tid = c.get("id", "")
        name = c.get("company_name", "?")
        self._detail_title.setText(f"\ud83c\udfe2 {name}")
        is_active = c.get("active", True)
        self._toggle_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._toggle_btn.setText("Pasif Yap" if is_active else "Aktif Yap")
        self._toggle_btn.setObjectName("dangerBtn" if is_active else "successBtn")
        sector = str(c.get("sector") or "teknik_servis")
        sector_index = self._sector_combo.findData(sector)
        self._sector_combo.setCurrentIndex(max(0, sector_index))
        self._sector_combo.setEnabled(True)
        self._sector_btn.setEnabled(True)

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
        self._reset_link_btn.setEnabled(False)
        self._repair_users_btn.setVisible(False)
        t = _FetchUsers(tid)
        t.done.connect(self._populate_users)
        t.error.connect(lambda e: self._status_lbl.setText(f"Kullanici hatasi: {e}"))
        t.start()
        self._thread = t

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
        self._reset_link_btn.setEnabled(True)

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
        is_active = self._selected_tenant.get("active", True)
        action = "Pasif Yap" if is_active else "Aktif Yap"
        reply = QMessageBox.question(self, "Onay",
            f"'{self._selected_tenant.get('company_name')}' firmasi {action.lower()} isteniyor. Devam?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        t = _ToggleActiveThread(self._selected_tenant["id"], not is_active)
        t.done.connect(lambda d: (self._status_lbl.setText("\u2705 Guncellendi."), self._load_companies()))
        t.error.connect(lambda e: self._status_lbl.setText(f"Hata: {e}"))
        t.start()
        self._thread = t

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
        self._delete_btn.setEnabled(False)
        self._sector_combo.setEnabled(False)
        self._sector_btn.setEnabled(False)
        self._user_table.setRowCount(0)
        self._repair_users_btn.setVisible(False)
        self._reset_btn.setEnabled(False)
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
