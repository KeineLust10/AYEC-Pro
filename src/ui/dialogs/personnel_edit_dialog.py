# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QGridLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.password_security import hash_password, validate_new_password


class PersonnelEditDialog(ModernDialog):
    def __init__(self, db, personnel_id, parent=None):
        self.db = db
        self.personnel_id = int(personnel_id)
        super().__init__("Personel Bilgileri", parent, width=760, height=560)
        self._build_ui()
        self._load()

    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QLabel("Personel bilgilerini görüntüleyin ve güncelleyin.")
        header.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; border: none;"))
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(12)

        def add_field(row, col, title, widget):
            lbl = QLabel(title)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text; border: none;"))
            grid.addWidget(lbl, row * 2, col)
            widget.setMinimumHeight(42)
            widget.setStyleSheet(theme_qss(
                "QLineEdit { background: @surface; border: 1px solid @border; border-radius: 10px; padding: 10px 12px; }"
                "QLineEdit:focus { border: 1px solid @accent; }"
            ))
            grid.addWidget(widget, row * 2 + 1, col)

        self.inp_name = QLineEdit()
        self.inp_role = QLineEdit()
        self.inp_dept = QLineEdit()
        self.inp_phone = QLineEdit()
        self.inp_email = QLineEdit()
        self.inp_telegram = QLineEdit()
        self.inp_tc = QLineEdit()
        self.inp_salary = QLineEdit()
        self.inp_new_pass = QLineEdit()
        self.inp_new_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_new_pass.setPlaceholderText("Boş bırakırsanız değişmez")

        add_field(0, 0, "Ad Soyad", self.inp_name)
        add_field(0, 1, "Görevi", self.inp_role)
        add_field(0, 2, "Departman", self.inp_dept)

        add_field(1, 0, "Telefon", self.inp_phone)
        add_field(1, 1, "E-posta", self.inp_email)
        add_field(1, 2, "Telegram", self.inp_telegram)

        add_field(2, 0, "TC No", self.inp_tc)
        add_field(2, 1, "Maaş", self.inp_salary)
        add_field(2, 2, "Yeni Şifre", self.inp_new_pass)

        layout.addLayout(grid)

        self.add_widget(container)

        self.add_cancel_button("İptal")
        self.add_button("Kaydet", "primary", self._save)

    def _load(self):
        try:
            self.db.cursor.execute("SELECT * FROM personnel WHERE id=?", (self.personnel_id,))
            row = self.db.cursor.fetchone()
            if not row:
                show_error(self.window(), "Personel bulunamadı.")
                self.reject()
                return

            columns = self.db._get_table_columns("personnel") if hasattr(self.db, "_get_table_columns") else []

            def get_val(col_name, default=""):
                try:
                    idx = columns.index(col_name)
                except ValueError:
                    return default
                val = row[idx]
                return "" if val is None else str(val)

            self.inp_name.setText(get_val("name"))
            self.inp_role.setText(get_val("role"))
            self.inp_dept.setText(get_val("department"))
            self.inp_phone.setText(get_val("phone"))
            self.inp_email.setText(get_val("email"))
            self.inp_telegram.setText(get_val("telegram_username"))
            self.inp_tc.setText(get_val("tc_no"))
            self.inp_salary.setText(get_val("salary"))

        except Exception as e:
            show_error(self.window(), f"Veri okunamadı: {e}")
            self.reject()

    def _save(self):
        name = self.inp_name.text().strip()
        if not name:
            show_warning(self.window(), "Ad Soyad zorunludur.")
            return

        def to_float(txt):
            try:
                return float((txt or "").replace(".", "").replace(",", ".") or 0)
            except Exception:
                return None

        salary = to_float(self.inp_salary.text().strip())
        if salary is None:
            show_warning(self.window(), "Geçersiz maaş.")
            return

        payload = {
            "name": name,
            "role": self.inp_role.text().strip(),
            "department": self.inp_dept.text().strip(),
            "phone": self.inp_phone.text().strip(),
            "email": self.inp_email.text().strip(),
            "telegram_username": self.inp_telegram.text().strip(),
            "tc_no": self.inp_tc.text().strip(),
            "salary": salary,
        }

        new_pass = self.inp_new_pass.text()
        if new_pass:
            password_error = validate_new_password(new_pass)
            if password_error:
                show_warning(self.window(), password_error)
                return
            if len(new_pass) < 4:
                show_warning(self.window(), "Şifre en az 4 karakter olmalıdır.")
                return
            payload["password_hash"] = hash_password(new_pass)

        try:
            columns = set(self.db._get_table_columns("personnel")) if hasattr(self.db, "_get_table_columns") else set()

            sets = []
            values = []
            for k, v in payload.items():
                if k in columns:
                    sets.append(f"{k}=?")
                    values.append(v)

            if not sets:
                show_error(self.window(), "Güncellenecek alan bulunamadı.")
                return

            values.append(self.personnel_id)
            self.db.cursor.execute(
                "UPDATE personnel SET {assignments} WHERE id=?".format(
                    assignments=", ".join(sets)
                ),
                tuple(values),
            )
            self.db.conn.commit()

            show_success(self.window(), "Personel bilgileri güncellendi! ✅")
            self.accept()
        except Exception as e:
            show_error(self.window(), f"Kaydetme hatası: {e}")

