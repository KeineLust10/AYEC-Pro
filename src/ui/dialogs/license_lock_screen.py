from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.security_manager import SecurityManager
from src.utils.theme_colors import theme_qss


_FIELD_QSS = """
QLineEdit, QComboBox {
    border: 1px solid @border; border-radius: 10px; padding: 10px 12px;
    background: @surface; color: @text; min-height: 22px;
}
QLineEdit:focus, QComboBox:focus { border: 2px solid @primary; }
"""

_LICENSE_PLANS = (
    {"code": "monthly", "label": "Ayl\u0131k Esnek", "months": 1, "amount": 990.0, "badge": "Esnek"},
    {"code": "six_months", "label": "6 Ayl\u0131k Avantaj", "months": 6, "amount": 5490.0, "badge": "%8 avantaj"},
    {"code": "one_year", "label": "1 Y\u0131ll\u0131k Profesyonel", "months": 12, "amount": 9900.0, "badge": "En \u00e7ok tercih"},
    {"code": "two_years", "label": "2 Y\u0131ll\u0131k \u0130\u015fletme", "months": 24, "amount": 17900.0, "badge": "%25 avantaj"},
    {"code": "three_years", "label": "3 Y\u0131ll\u0131k Kurumsal", "months": 36, "amount": 24900.0, "badge": "%30 avantaj"},
)

_PAYMENT_HOLDER = "Engin ASLAN"
_PAYMENT_BANK = "Vak\u0131fBank"
_PAYMENT_IBAN = "TR66 0001 5001 5800 7321 0690 01"
_ADMIN_LICENSE_EMAIL = "destek@ayecpro.com"
_OFFICIAL_LICENSE_EMAIL = "info@ayecpro.com"


class LicenseRequestDialog(ModernDialog):
    """Authenticated license order and payment screen."""

    def __init__(self, hwid, parent=None, locked=False, warning_message=""):
        self.locked_mode = bool(locked)
        self.warning_message = str(warning_message or "")
        super().__init__(
            title=(
                "Lisans S\u00fcresi Sona Erdi"
                if self.locked_mode
                else "Lisans Talebi ve \u00d6deme Bilgileri"
            ),
            parent=parent,
            width=820,
            height=920 if self.locked_mode else 720,
        )
        if self.locked_mode:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
            self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.hwid = str(hwid or "")
        self.client = None
        self.connection_error = ""
        self.fallback_mail_sent = False
        self.selected_plan = None
        self.plan_buttons = {}
        self._build()
        self._load_catalog()

    def _build(self):
        self.content_layout.setContentsMargins(24, 18, 24, 18)
        self.content_layout.setSpacing(14)
        if self.locked_mode:
            warning = QLabel(
                self.warning_message
                or (
                    "Lisans eri\u015fiminizin s\u00fcresi sona ermi\u015ftir. "
                    "AYEC Pro \u00fczerindeki i\u015flemler ge\u00e7ici olarak "
                    "durdurulmu\u015ftur. Kesintisiz kullan\u0131ma devam etmek "
                    "i\u00e7in uygun paketi se\u00e7erek lisans talebinizi iletin."
                )
            )
            warning.setWordWrap(True)
            warning.setStyleSheet(
                "background:#FFF7ED;color:#9A3412;border:1px solid #FDBA74;"
                "border-radius:12px;padding:12px;font-size:13px;font-weight:700;"
            )
            self.content_layout.addWidget(warning)
        plan_title = QLabel("Lisans Paketinizi Se\u00e7in")
        plan_title.setStyleSheet(theme_qss("font-size:15px;font-weight:800;color:@text;"))
        self.content_layout.addWidget(plan_title)
        plan_widget = QWidget()
        plan_widget.setFixedWidth(680)
        self.plan_grid = QGridLayout(plan_widget)
        self.plan_grid.setContentsMargins(0, 0, 0, 0)
        self.plan_grid.setHorizontalSpacing(10)
        self.plan_grid.setVerticalSpacing(10)
        self.content_layout.addWidget(
            plan_widget, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.amount_label = QLabel("\u00d6denecek Tutar: -")
        self.amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.amount_label.setStyleSheet(
            "background:#ECFDF5;color:#047857;border:1px solid #6EE7B7;"
            "border-radius:12px;padding:12px;font-size:18px;font-weight:800;"
        )
        self.amount_label.setFixedWidth(680)
        self.content_layout.addWidget(
            self.amount_label, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.payment_holder = QLabel(f"Al\u0131c\u0131\n{_PAYMENT_HOLDER}")
        self.payment_bank = QLabel(f"Banka\n{_PAYMENT_BANK}")
        self.payment_iban = QLabel(f"IBAN\n{_PAYMENT_IBAN}")
        self.payment_iban.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        payment_box = QWidget()
        payment_box.setFixedWidth(680)
        payment_box.setObjectName("paymentBox")
        payment_box.setStyleSheet(theme_qss(
            "#paymentBox{background:#EFF6FF;border:1px solid #93C5FD;border-radius:14px;}"
            "#paymentBox QLabel{border:none;background:transparent;color:#0F172A;"
            "font-size:13px;font-weight:700;}"
        ))
        payment_layout = QVBoxLayout(payment_box)
        payment_layout.setContentsMargins(18, 16, 18, 16)
        payment_layout.setSpacing(12)
        payment_title = QLabel("Havale / EFT Bilgileri")
        payment_title.setStyleSheet("font-size:15px;font-weight:800;color:#1D4ED8;")
        payment_layout.addWidget(payment_title)
        payment_layout.addWidget(self.payment_holder)
        payment_layout.addWidget(self.payment_bank)
        iban_row = QHBoxLayout()
        iban_row.addWidget(self.payment_iban, 1)
        copy_iban = QPushButton("IBAN Kopyala")
        copy_iban.setMinimumHeight(36)
        copy_iban.setMaximumWidth(120)
        copy_iban.clicked.connect(self._copy_iban)
        iban_row.addWidget(copy_iban)
        payment_layout.addLayout(iban_row)
        self.content_layout.addWidget(
            payment_box, 0, Qt.AlignmentFlag.AlignHCenter
        )

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addStretch()

        close_text = "Programdan \u00c7\u0131k" if self.locked_mode else "Kapat"
        close_callback = self._exit_application if self.locked_mode else self.reject
        self.add_button(close_text, "danger" if self.locked_mode else "secondary", close_callback)
        self.btn_unpaid = self.add_button(
            "\u00d6deme Yapmad\u0131m", "secondary", lambda: self._submit(False)
        )
        self.btn_paid = self.add_button(
            "\u00d6deme Yapt\u0131m - Talep Et", "primary", lambda: self._submit(True)
        )
        self._render_plan_cards()
        self._set_submission_enabled(True)

    def reject(self):
        if getattr(self, "locked_mode", False):
            self._exit_application()
            return
        super().reject()

    def _exit_application(self):
        super().reject()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _render_plan_cards(self):
        colors = ("#2563EB", "#7C3AED", "#059669", "#EA580C", "#BE123C")
        for index, plan in enumerate(_LICENSE_PLANS):
            monthly = float(plan["amount"]) / int(plan["months"])
            button = QPushButton(
                f"{plan['label']}\n{self._format_try(plan['amount'], 0)} TL\n"
                f"{plan['badge']}  |  Ayl\u0131k {self._format_try(monthly, 0)} TL"
            )
            button.setCheckable(True)
            button.setMinimumHeight(78)
            button.setMinimumWidth(0)
            button.setMaximumWidth(670 if index == len(_LICENSE_PLANS) - 1 else 330)
            button.setSizePolicy(
                QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
            )
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            color = colors[index]
            button.setStyleSheet(
                "QPushButton{background:" + color + ";color:white;border:2px solid "
                + color + ";border-radius:14px;padding:10px;font-size:12px;font-weight:700;}"
                "QPushButton:hover{border:2px solid #FBBF24;}"
                "QPushButton:checked{border:4px solid #FBBF24;background:" + color + ";}"
            )
            button.clicked.connect(
                lambda _checked=False, selected=dict(plan): self._select_plan(selected)
            )
            self.plan_buttons[str(plan["code"])] = button
            if index == len(_LICENSE_PLANS) - 1:
                self.plan_grid.addWidget(button, index // 2, 0, 1, 2)
            else:
                self.plan_grid.addWidget(button, index // 2, index % 2)
        self._select_plan(dict(_LICENSE_PLANS[2]))

    def _select_plan(self, plan):
        self.selected_plan = dict(plan or {})
        selected_code = str(self.selected_plan.get("code") or "")
        for code, button in self.plan_buttons.items():
            button.setChecked(code == selected_code)
        amount = float(self.selected_plan.get("amount") or 0)
        self.amount_label.setText(
            f"\u00d6denecek Tutar: {self._format_try(amount)} TL  |  "
            f"{self.selected_plan.get('label', '')}"
        )

    @staticmethod
    def _format_try(amount, decimals=2):
        formatted = f"{float(amount or 0):,.{int(decimals)}f}"
        return formatted.replace(",", "_").replace(".", ",").replace("_", ".")

    def _copy_iban(self):
        QApplication.clipboard().setText(_PAYMENT_IBAN.replace(" ", ""))
        self._status("IBAN panoya kopyalandi.", True)

    def _load_catalog(self):
        try:
            client = self._connect_client()
            catalog = client.catalog()
            if not list(catalog.get("plans") or []):
                raise RuntimeError("Lisans paketi bulunamadi.")
        except Exception as error:
            self.connection_error = str(error)
            self._status(
                "Paket secilebilir. Talep dugmesine basildiginda sunucu "
                f"baglantisi yeniden denenecek: {error}",
                False,
            )

    def _connect_client(self):
        from src.utils.license_api_client import LicenseApiClient

        client = LicenseApiClient(timeout=20)
        self.client = client
        self.connection_error = ""
        return client

    def _set_submission_enabled(self, enabled):
        self.btn_unpaid.setEnabled(enabled)
        self.btn_paid.setEnabled(enabled)

    def _status(self, text, success):
        color = "@success" if success else "@danger"
        self.status_label.setStyleSheet(theme_qss(f"color:{color};font-size:12px;"))
        self.status_label.setText(text)

    def _submit(self, paid):
        if not self.selected_plan:
            self._status("Lisans paketi secin.", False)
            return
        self._set_submission_enabled(False)
        try:
            client = self.client or self._connect_client()
            identity = self._license_identity()
            result = client.create_order({
                "hardware_id": self.hwid,
                "plan_code": str(self.selected_plan.get("code") or ""),
                "payment_reported": bool(paid),
                **identity,
            })
            order = dict(result.get("order") or {})
            mail = dict(result.get("mail") or {})
            if paid:
                if not bool(mail.get("admin_sent")):
                    fallback_sent, fallback_note = self._send_admin_email_fallback(
                        order, paid=True
                    )
                    if fallback_sent:
                        self.fallback_mail_sent = True
                        mail = {
                            "admin_sent": True,
                            "admin_message": fallback_note,
                            "admin_recipient": _ADMIN_LICENSE_EMAIL,
                        }
                if bool(mail.get("admin_sent")):
                    self._status(
                        "Odeme bildirimi ve lisans talebi yonetime gonderildi. "
                        "destek@ayecpro.com adresine e-posta iletildi.",
                        True,
                    )
                else:
                    self._status(
                        "Talep yonetime kaydedildi; ancak e-posta gonderilemedi: "
                        f"{mail.get('admin_message') or 'SMTP yaniti alinamadi.'}",
                        False,
                    )
            else:
                self._status(
                    "Lisans talebi kaydedildi. Odeme sonrasi yeniden bildirebilirsiniz.",
                    True,
                )
        except Exception as error:
            self.client = None
            if paid and not self.fallback_mail_sent:
                fallback_sent, fallback_note = self._send_admin_email_fallback(
                    {}, paid=True
                )
                if fallback_sent:
                    self.fallback_mail_sent = True
                    self._status(
                        "Talep e-postasi destek@ayecpro.com adresine gonderildi; "
                        "sunucu kaydi tamamlanamadi. Sunucu guncellendikten sonra "
                        f"yeniden deneyin: {error}",
                        False,
                    )
                    self._set_submission_enabled(True)
                    return
            self._status(f"Lisans talebi gonderilemedi: {error}", False)
            self._set_submission_enabled(True)

    def _license_identity(self):
        db = self._find_database()
        values = {
            "company_name": "",
            "requester_name": "",
            "requester_email": "",
            "requester_phone": "",
        }
        session_username = ""
        session_password = ""
        session_tenant_id = ""
        widget = self.parent()
        while widget is not None:
            current_user = getattr(widget, "current_user", None)
            if isinstance(current_user, dict):
                session_username = str(
                    current_user.get("username")
                    or current_user.get("email")
                    or session_username
                    or ""
                ).strip()
            session_username = str(
                getattr(widget, "username", "")
                or getattr(widget, "current_username", "")
                or session_username
                or ""
            ).strip()
            session_password = str(
                getattr(widget, "_web_sync_password", "")
                or session_password
                or ""
            )
            session_tenant_id = str(
                getattr(widget, "_web_sync_tenant_id", "")
                or session_tenant_id
                or ""
            ).strip()
            if session_username and session_password:
                break
            widget = widget.parent() if hasattr(widget, "parent") else None
        if db is not None:
            try:
                row = db.cursor.execute(
                    "SELECT full_name,email,company_name,phone FROM registration "
                    "ORDER BY id DESC LIMIT 1"
                ).fetchone()
                if row:
                    if hasattr(row, "keys"):
                        values.update({key: str(row[key] or "") for key in row.keys()})
                    else:
                        values.update(
                            dict(
                                zip(
                                    ("full_name", "email", "company_name", "phone"),
                                    (str(item or "") for item in row),
                                )
                            )
                        )
            except Exception:
                pass
            setting_map = {
                "company_name": ("company_name", "company"),
                "requester_name": ("authorized_person", "admin_name"),
                "requester_email": ("company_email", "admin_email", "email"),
                "requester_phone": ("company_phone", "phone"),
            }
            for target, keys in setting_map.items():
                if values.get(target):
                    continue
                for key in keys:
                    try:
                        value = str(db.get_setting(key, "") or "").strip()
                    except Exception:
                        value = ""
                    if value:
                        values[target] = value
                        break
            if not values.get("requester_email") or not values.get("requester_name"):
                try:
                    row = None
                    if session_username:
                        row = db.cursor.execute(
                            "SELECT full_name,email,username,phone "
                            "FROM users WHERE username=? AND COALESCE(active,1)=1 "
                            "ORDER BY id DESC LIMIT 1",
                            (session_username,),
                        ).fetchone()
                    if row:
                        row_values = {
                            "requester_name": str(row[0] or ""),
                            "requester_email": str(row[1] or ""),
                            "requester_phone": str(row[3] or ""),
                        }
                        for key, value in row_values.items():
                            if not values.get(key) and value:
                                values[key] = value
                except Exception:
                    pass
            try:
                row = db.cursor.execute(
                    "SELECT company_name,authorized_person,phone,email "
                    "FROM company_info ORDER BY rowid DESC LIMIT 1"
                ).fetchone()
                if row:
                    company_values = {
                        "company_name": str(row[0] or ""),
                        "requester_name": str(row[1] or ""),
                        "requester_phone": str(row[2] or ""),
                        "requester_email": str(row[3] or ""),
                    }
                    for key, value in company_values.items():
                        if not values.get(key) and value:
                            values[key] = value
            except Exception:
                pass
            if not session_tenant_id:
                try:
                    session_tenant_id = str(
                        db.get_setting("web_sync_tenant_id", "") or ""
                    ).strip()
                except Exception:
                    session_tenant_id = ""
        values["requester_name"] = values.get("requester_name") or values.pop("full_name", "")
        values["requester_email"] = values.get("requester_email") or values.pop("email", "")
        values["requester_phone"] = values.get("requester_phone") or values.pop("phone", "")
        values["identifier"] = session_username
        values["username"] = session_username
        values["password"] = session_password
        values["tenant_id"] = session_tenant_id
        return values

    def _send_admin_email_fallback(self, order, paid):
        import smtplib
        import ssl
        from email.message import EmailMessage

        from src.utils.email_manager import EmailManager

        try:
            manager = EmailManager(self._find_database())
            if not manager.smtp_user or not manager.smtp_pass:
                raise RuntimeError("Masaustu SMTP bilgileri yapilandirilmamis.")
            plan_label = str(order.get("plan_label") or self.selected_plan.get("label") or "")
            amount = float(order.get("amount_try") or self.selected_plan.get("amount") or 0)
            message = EmailMessage()
            message["Subject"] = "AYEC Pro Odeme Yapildi - Lisans Talebi"
            message["From"] = _OFFICIAL_LICENSE_EMAIL if manager.smtp_user.lower() == _OFFICIAL_LICENSE_EMAIL else manager.smtp_user
            message["To"] = _ADMIN_LICENSE_EMAIL
            message["Reply-To"] = _ADMIN_LICENSE_EMAIL
            message.set_content(
                f"Tarih/Saat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Talep: {order.get('request_no') or '-'}\n"
                f"Firma: {order.get('company_name') or '-'}\n"
                f"Talep eden: {order.get('requester_name') or '-'}\n"
                f"E-posta: {order.get('requester_email') or '-'}\n"
                f"Paket: {plan_label}\n"
                f"Tutar: {self._format_try(amount)} TL\n"
                f"Odeme durumu: {'Odeme bildirildi' if paid else 'Odeme bekleniyor'}\n"
                f"HWID: {self.hwid}\n"
            )
            port = int(manager.smtp_port or 587)
            if port == 465:
                server = smtplib.SMTP_SSL(
                    manager.smtp_server,
                    port,
                    timeout=20,
                    context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(manager.smtp_server, port, timeout=20)
                server.ehlo()
                if manager.use_tls:
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
            with server:
                server.login(manager.smtp_user, manager.smtp_pass.replace(" ", ""))
                server.send_message(message)
            return True, "Masaustu SMTP kanaliyla e-posta gonderildi."
        except Exception as error:
            return False, str(error)

    def _find_database(self):
        widget = self.parent()
        while widget is not None:
            if hasattr(widget, "db"):
                return widget.db
            widget = widget.parent() if hasattr(widget, "parent") else None
        return None


class LicenseLockScreen(ModernDialog):
    def __init__(
        self, parent=None, hwid="Bilinmiyor", message="Deneme sureniz dolmustur",
        request_only=False, username="",
    ):
        title = "Lisans Islemleri" if request_only else "Lisans Gerekli"
        super().__init__(title=title, parent=parent, width=610, height=540)
        self.hwid = str(hwid or "")
        self.message = str(message or "")
        self.request_only = bool(request_only)
        self.username = str(username or "")
        self.setWindowFlag(
            Qt.WindowType.WindowStaysOnTopHint, not self.request_only
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._build()

    def _build(self):
        self.content_layout.setContentsMargins(24, 18, 24, 18)
        self.content_layout.setSpacing(12)
        message = QLabel(self.message)
        message.setWordWrap(True)
        message.setStyleSheet(theme_qss("font-size:13px;color:@text_muted;"))
        self.content_layout.addWidget(message)

        self.mode = QComboBox()
        self.mode.addItem("Lisans Anahtari", "license")
        self.mode.addItem("Davet Kodu", "invite")
        self.mode.setStyleSheet(theme_qss(_FIELD_QSS))
        self.mode.currentIndexChanged.connect(self._show_mode)
        self.content_layout.addWidget(self.mode)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._license_page())
        self.stack.addWidget(self._invite_page())
        self.content_layout.addWidget(self.stack)

        hwid_row = QHBoxLayout()
        self.hwid_val = QLineEdit(self.hwid)
        self.hwid_val.setReadOnly(True)
        self.hwid_val.setStyleSheet(theme_qss(_FIELD_QSS))
        hwid_row.addWidget(self.hwid_val, 1)
        copy_button = QPushButton("Cihaz Kodunu Kopyala")
        copy_button.setMinimumHeight(42)
        copy_button.clicked.connect(self.copy_hwid)
        hwid_row.addWidget(copy_button)
        self.content_layout.addLayout(hwid_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.content_layout.addWidget(self.status_label)
        self.content_layout.addStretch()

        self.add_button("Kapat", "secondary", self.reject)
        self.add_button(
            "Lisans Talebi / Odeme", "secondary", self.request_license
        )
        self.btn_primary = self.add_button(
            "Lisans Dogrula", "primary", self._primary_action
        )
        self._show_mode()

    def _license_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.addWidget(QLabel("Lisans anahtarinizi girin"))
        self.inp_license = QLineEdit()
        self.inp_license.setPlaceholderText("XXXXX-XXXXX-XXXXX-XXXXX-XXXXX")
        self.inp_license.setStyleSheet(theme_qss(_FIELD_QSS))
        layout.addWidget(self.inp_license)
        return page

    def _invite_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.addWidget(QLabel("Davet kodu ile etkinlestir"))
        self.inp_invite = QLineEdit()
        self.inp_invite.setPlaceholderText("Davet kodu")
        self.inp_username = QLineEdit(self.username)
        self.inp_username.setPlaceholderText("Sunucu kullanici adi veya e-posta")
        self.inp_password = QLineEdit()
        self.inp_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_password.setPlaceholderText("Sunucu sifresi")
        for field in (self.inp_invite, self.inp_username, self.inp_password):
            field.setStyleSheet(theme_qss(_FIELD_QSS))
            layout.addWidget(field)
        return page

    def _show_mode(self):
        invite = self.mode.currentData() == "invite"
        self.stack.setCurrentIndex(1 if invite else 0)
        if hasattr(self, "btn_primary"):
            self.btn_primary.setText(
                "Davet Kodunu Dogrula" if invite else "Lisans Dogrula"
            )

    def _primary_action(self):
        if self.mode.currentData() == "invite":
            self.activate_invitation()
        else:
            self.activate_license()

    def _status(self, text, success=False):
        color = "@success" if success else "@danger"
        self.status_label.setStyleSheet(
            theme_qss(f"font-size:12px;color:{color};")
        )
        self.status_label.setText(text)

    def copy_hwid(self):
        QApplication.clipboard().setText(self.hwid)
        self._status("Cihaz kimligi kopyalandi.", True)

    def activate_license(self):
        key = self.inp_license.text().strip().upper()
        if not key or not SecurityManager.validate_license_format(key):
            self._status("Gecerli bir lisans anahtari girin.")
            return
        if not SecurityManager.verify_license_key(key, SecurityManager.get_hwid()):
            self._status("Lisans dogrulanamadi.")
            return
        try:
            self._store_license(key, "PRO", key)
        except Exception as error:
            self._status(str(error))
            return
        self._status("Lisans dogrulandi.", True)
        self.accept()

    def activate_invitation(self):
        code = self.inp_invite.text().strip()
        identifier = self.inp_username.text().strip()
        password = self.inp_password.text()
        if not code or not identifier or not password:
            self._status("Davet kodu, kullanici adi ve sifre zorunludur.")
            return
        try:
            from src.utils.license_api_client import LicenseApiClient

            client = LicenseApiClient(timeout=20)
            client.activate_invitation(identifier, password, code)
            self._store_license("INVITATION", "INVITATION", "INVITATION")
        except Exception as error:
            self._status(f"Davet kodu dogrulanamadi: {error}")
            return
        self._status("Davet kodu dogrulandi.", True)
        self.accept()

    def _store_license(self, setting_key, license_type, encrypted_value):
        parent = self.parent()
        if not parent or not hasattr(parent, "db"):
            raise RuntimeError("Veritabani baglantisi bulunamadi.")
        hwid = SecurityManager.get_hwid()
        parent.db.set_setting("is_licensed", "1")
        parent.db.set_setting("license_key", setting_key)
        encrypted = encrypted_value
        if license_type == "PRO":
            encrypted = SecurityManager.encrypt_data(encrypted_value, hwid)
        parent.db.cursor.execute("DELETE FROM license_info")
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parent.db.cursor.execute(
            "INSERT INTO license_info (encrypted_key, license_type, hwid, "
            "start_date, expiry_date, last_check_date) VALUES (?, ?, ?, ?, ?, ?)",
            (
                encrypted, license_type, hwid, now_text,
                "2099-12-31 23:59:59", now_text,
            ),
        )
        parent.db.conn.commit()

    def request_license(self):
        LicenseRequestDialog(self.hwid, self).exec()
