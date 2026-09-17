# -*- coding: utf-8 -*-
"""
Admin User Step - Yonetici Hesabi  (v5.0)
Premium form with password strength meter
"""

import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QFrame, QPushButton,
)
from PyQt6.QtCore import Qt
from src.utils.logger import logger


FS = """
    QLineEdit {
        background: #FFFFFF;
        color: #0F172B;
        border: 1.5px solid #CBD5E1;
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border-color: #6366F1;
        background: #FFFFFF;
    }
    QLineEdit::placeholder { color: #94A3B7; }
"""


class _PwField(QFrame):
    """Sifre alani — toggle gorunurluk"""
    def __init__(self, placeholder, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent; border:none;")
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.le = QLineEdit()
        self.le.setPlaceholderText(placeholder)
        self.le.setEchoMode(QLineEdit.EchoMode.Password)
        self.le.setMinimumHeight(44)
        self.le.setStyleSheet(FS)
        h.addWidget(self.le)

    def text(self):
        return self.le.text()

    def setFocus(self):
        self.le.setFocus()


class AdminUserStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 28, 44, 24)
        root.setSpacing(0)

        desc = QLabel(
            "Bu hesap, sisteme tam yetkili erisimi olan ilk yonetici hesabi olacaktir."
        )
        desc.setStyleSheet(
            "color:#475568; font-size:14px; border:none; background:transparent;"
        )
        root.addWidget(desc)
        root.addSpacing(28)

        cols = QHBoxLayout()
        cols.setSpacing(24)
        left  = QVBoxLayout(); left.setSpacing(20)
        right = QVBoxLayout(); right.setSpacing(20)

        # Sol: kimlik
        left.addLayout(self._fg("* Ad Soyad",       "full_name",   "Orn: Ahmet Yilmaz",     False))
        left.addLayout(self._fg("* Kullanici Adi",  "username",    "Orn: admin",              False))
        left.addLayout(self._fg("  E-posta",        "email_field", "Orn: admin@sirket.com",  False))
        left.addStretch()

        # Sag: sifre + guc
        right.addLayout(self._pwg("* Sifre",        "pw1", "En az 8 karakter"))
        right.addLayout(self._pwg("* Sifre Tekrar", "pw2", "Sifreyi tekrar girin"))

        self.str_label = QLabel("Sifre Gucu: —")
        self.str_label.setStyleSheet(
            "color:#475568; font-size:11px; background:transparent; border:none;"
        )
        right.addWidget(self.str_label)

        self.str_bg = QFrame()
        self.str_bg.setFixedHeight(5)
        self.str_bg.setStyleSheet(
            "background:rgba(0,0,0,0.07); border-radius:3px; border:none;"
        )
        self.str_fill = QFrame(self.str_bg)
        self.str_fill.setFixedHeight(5)
        self.str_fill.setStyleSheet(
            "background:#475568; border-radius:3px; border:none;"
        )
        self.str_fill.resize(0, 5)
        right.addWidget(self.str_bg)
        self.pw1.le.textChanged.connect(self._upd)
        right.addSpacing(14)

        # Guvenlik notu
        sec = QFrame()
        sec.setStyleSheet(
            "background:rgba(99,102,241,0.06);"
            "border:1px solid rgba(99,102,241,0.18);"
            "border-radius:12px;"
        )
        sv = QVBoxLayout(sec)
        sv.setContentsMargins(16, 14, 16, 14)
        sv.setSpacing(5)
        st = QLabel("Guvenlik Ipuclari")
        st.setStyleSheet(
            "color:#4F46E5; font-size:13px; font-weight:700;"
            "background:transparent; border:none;"
        )
        sv.addWidget(st)
        for tip in [
            "Buyuk-kucuk harf, rakam ve sembol karisimi kullanin",
            "Kullanici adi ve sifreyi guvenli bir yerde saklayin",
            "Bu bilgileri baskalarla paylasmayin",
        ]:
            tl = QLabel("- " + tip)
            tl.setStyleSheet(
                "color:#475568; font-size:12px; background:transparent; border:none;"
            )
            sv.addWidget(tl)
        right.addWidget(sec)
        right.addStretch()

        cols.addLayout(left,  1)
        cols.addLayout(right, 1)
        root.addLayout(cols)
        root.addStretch()

        note = QLabel("* Zorunlu alanlar")
        note.setStyleSheet(
            "color:#64748A; font-size:11px; font-style:italic;"
            "border:none; background:transparent;"
        )
        root.addWidget(note)

    def _fg(self, label, attr, placeholder, _unused):
        vbox = QVBoxLayout(); vbox.setSpacing(7)
        req = label.startswith("*")
        lbl = QLabel(label.strip())
        lbl.setStyleSheet(
            ("color:#4F46E5;" if req else "color:#475568;")
            + "font-size:13px; font-weight:600; background:transparent; border:none;"
        )
        vbox.addWidget(lbl)
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setMinimumHeight(44)
        f.setStyleSheet(FS)
        setattr(self, attr, f)
        vbox.addWidget(f)
        return vbox

    def _pwg(self, label, attr, placeholder):
        vbox = QVBoxLayout(); vbox.setSpacing(7)
        lbl = QLabel(label.strip())
        lbl.setStyleSheet(
            "color:#4F46E5; font-size:13px; font-weight:600;"
            "background:transparent; border:none;"
        )
        vbox.addWidget(lbl)
        f = _PwField(placeholder)
        setattr(self, attr, f)
        vbox.addWidget(f)
        return vbox

    def _upd(self, pw):
        score = 0
        if len(pw) >= 8:  score += 1
        if len(pw) >= 12: score += 1
        if re.search(r"[A-Z]", pw): score += 1
        if re.search(r"[0-9]", pw): score += 1
        if re.search(r"[^a-zA-Z0-9]", pw): score += 1
        score = min(score, 4)
        labels = ["Cok Zayif", "Zayif", "Orta", "Guclu", "Cok Guclu"]
        colors = ["#EF4444", "#F97316", "#F59E0B", "#10B981", "#6366F1"]
        c = colors[score]
        w = max(4, int(self.str_bg.width() * ((score + 1) * 20) / 100))
        self.str_fill.resize(w, 5)
        self.str_fill.setStyleSheet(
            f"background:{c}; border-radius:3px; border:none;"
        )
        self.str_label.setText(f"Sifre Gucu: {labels[score]}")
        self.str_label.setStyleSheet(
            f"color:{c}; font-size:11px; background:transparent; border:none;"
        )

    def _err(self, msg):
        if self.wizard and hasattr(self.wizard, "show_toast"):
            self.wizard.show_toast(msg, "warning")

    def validate(self):
        if not self.full_name.text().strip():
            self._err("Ad soyad giriniz.")
            self.full_name.setFocus()
            return False

        uname = self.username.text().strip()
        if not uname:
            self._err("Kullanici adi giriniz.")
            self.username.setFocus()
            return False
        if uname.lower() in ("admin", "master"):
            self._err("'admin' ve 'master' kullanici adlari teknik servis icin ayrilmistir.")
            self.username.setFocus()
            return False
        if not re.match(r"^[a-zA-Z0-9_]{3,}$", uname):
            self._err("Kullanici adi min 3 karakter, sadece harf/rakam/_")
            self.username.setFocus()
            return False

        if self.wizard and hasattr(self.wizard, "db"):
            try:
                tables = {
                    row[0]
                    for row in self.wizard.db.cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                ex_personnel = None
                ex_user = None
                if "personnel" in tables:
                    ex_personnel = self.wizard.db.cursor.execute(
                        "SELECT id FROM personnel WHERE username=?", (uname,)
                    ).fetchone()
                if "users" in tables:
                    ex_user = self.wizard.db.cursor.execute(
                        "SELECT id FROM users WHERE username=?", (uname,)
                    ).fetchone()
                if ex_personnel or ex_user:
                    self._err(f"'{uname}' kullanici adi kullaniliyor.")
                    self.username.setFocus()
                    return False
            except Exception as exc:
                logger.error(f"username check: {exc}")

        em = self.email_field.text().strip()
        if em and not re.match(
            r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", em
        ):
            self._err("Gecerli e-posta girin.")
            self.email_field.setFocus()
            return False

        pw = self.pw1.text()
        if not pw:
            self._err("Lutfen sifre girin.")
            self.pw1.setFocus()
            return False
        if len(pw) < 8:
            self._err("Sifre en az 8 karakter olmalidir.")
            self.pw1.setFocus()
            return False
        if pw != self.pw2.text():
            self._err("Sifreler eslesmemektedir.")
            self.pw2.setFocus()
            return False
        return True

    def get_data(self):
        return {
            "admin_user": {
                "full_name": self.full_name.text().strip(),
                "username":  self.username.text().strip(),
                "email":     self.email_field.text().strip(),
                "password":  self.pw1.text(),
            }
        }
