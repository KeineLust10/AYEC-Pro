# -*- coding: utf-8 -*-

"""Helper: Wizard adım dosyalarını yazar (v5.0 premium redesign)"""
import os, textwrap

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "src", "ui", "dialogs", "setup_wizard")

# ─────────────────────────────────────────────────────────────────────────────
ADMIN_USER = textwrap.dedent('''
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
        background: #08090F;
        color: #F1F5F9;
        border: 1.5px solid rgba(255,255,255,0.09);
        border-radius: 10px;
        padding: 10px 14px;
        font-size: 14px;
    }
    QLineEdit:focus {
        border-color: #6366F1;
        background: #0A0C16;
    }
    QLineEdit::placeholder { color: #475569; }
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
            "color:#94A3B8; font-size:14px; border:none; background:transparent;"
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
            "color:#475569; font-size:11px; background:transparent; border:none;"
        )
        right.addWidget(self.str_label)

        self.str_bg = QFrame()
        self.str_bg.setFixedHeight(5)
        self.str_bg.setStyleSheet(
            "background:rgba(255,255,255,0.07); border-radius:3px; border:none;"
        )
        self.str_fill = QFrame(self.str_bg)
        self.str_fill.setFixedHeight(5)
        self.str_fill.setStyleSheet(
            "background:#475569; border-radius:3px; border:none;"
        )
        self.str_fill.resize(0, 5)
        right.addWidget(self.str_bg)
        self.pw1.le.textChanged.connect(self._upd)
        right.addSpacing(14)

        # Guvenlik notu
        sec = QFrame()
        sec.setStyleSheet(
            "background:rgba(99,102,241,0.08);"
            "border:1px solid rgba(99,102,241,0.25);"
            "border-radius:12px;"
        )
        sv = QVBoxLayout(sec)
        sv.setContentsMargins(16, 14, 16, 14)
        sv.setSpacing(5)
        st = QLabel("Guvenlik Ipuclari")
        st.setStyleSheet(
            "color:#818CF8; font-size:13px; font-weight:700;"
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
                "color:#64748B; font-size:12px; background:transparent; border:none;"
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
            "color:#475569; font-size:11px; font-style:italic;"
            "border:none; background:transparent;"
        )
        root.addWidget(note)

    def _fg(self, label, attr, placeholder, _unused):
        vbox = QVBoxLayout(); vbox.setSpacing(7)
        req = label.startswith("*")
        lbl = QLabel(label.strip())
        lbl.setStyleSheet(
            ("color:#A78BFA;" if req else "color:#94A3B8;")
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
            "color:#A78BFA; font-size:13px; font-weight:600;"
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
        if not re.match(r"^[a-zA-Z0-9_]{3,}$", uname):
            self._err("Kullanici adi min 3 karakter, sadece harf/rakam/_")
            self.username.setFocus()
            return False

        if self.wizard and hasattr(self.wizard, "db"):
            try:
                ex = self.wizard.db.cursor.execute(
                    "SELECT id FROM personnel WHERE username=?", (uname,)
                ).fetchone()
                if ex:
                    self._err(f"'{uname}' kullanici adi kullaniliyor.")
                    self.username.setFocus()
                    return False
            except Exception as exc:
                logger.error(f"username check: {exc}")

        em = self.email_field.text().strip()
        if em and not re.match(
            "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$", em
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
''').lstrip()

# ─────────────────────────────────────────────────────────────────────────────
BASIC_SETTINGS = textwrap.dedent('''
"""
Basic Settings Step - Temel Ayarlar  (v5.0)
Premium toggle-switch settings
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QButtonGroup, QRadioButton, QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal


class _ToggleCard(QFrame):
    """Baslik + aciklama + iki radio secenegi"""
    def __init__(self, icon, title, desc, opt_yes, opt_no, default_yes=True, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 14px;
            }
            QFrame:hover {
                background: rgba(255,255,255,0.04);
                border-color: rgba(255,255,255,0.11);
            }
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 18, 20, 18)
        main.setSpacing(10)

        # Baslik satiri
        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet("font-size:20px; background:transparent; border:none;")
        top.addWidget(ico)
        top.addSpacing(8)
        v2 = QVBoxLayout(); v2.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(
            "color:#F1F5F9; font-size:14px; font-weight:700;"
            "background:transparent; border:none;"
        )
        d = QLabel(desc)
        d.setStyleSheet(
            "color:#64748B; font-size:12px; background:transparent; border:none;"
        )
        d.setWordWrap(True)
        v2.addWidget(t); v2.addWidget(d)
        top.addLayout(v2); top.addStretch()
        main.addLayout(top)

        # Radio butonlari
        rb_row = QHBoxLayout(); rb_row.setSpacing(20)
        self.grp = QButtonGroup(self)
        for txt, val, checked in [(opt_yes, True, default_yes),
                                   (opt_no,  False, not default_yes)]:
            rb = QRadioButton(txt)
            rb.setChecked(checked)
            rb.setProperty("val", val)
            rb.setStyleSheet("""
                QRadioButton {
                    color: #94A3B8; font-size: 13px; spacing: 8px;
                    font-weight: 500;
                }
                QRadioButton::indicator { width:18px; height:18px; }
                QRadioButton::indicator:unchecked {
                    border:1.5px solid rgba(255,255,255,0.15);
                    border-radius:9px; background:#08090F;
                }
                QRadioButton::indicator:checked {
                    border:2px solid #6366F1;
                    border-radius:9px; background:#6366F1;
                }
                QRadioButton:hover { color:#F1F5F9; }
            """)
            self.grp.addButton(rb)
            rb_row.addWidget(rb)
        rb_row.addStretch()
        main.addLayout(rb_row)

    def value(self):
        btn = self.grp.checkedButton()
        return btn.property("val") if btn else True


class BasicSettingsStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 28, 44, 24)
        root.setSpacing(16)

        desc = QLabel(
            "Sisteminizin temel calisma parametrelerini yapilandirin."
            " Bu ayarlari daha sonra degistirebilirsiniz."
        )
        desc.setStyleSheet(
            "color:#94A3B8; font-size:14px; border:none; background:transparent;"
        )
        desc.setWordWrap(True)
        root.addWidget(desc)

        # Para birimi karti (ozel — ComboBox)
        cur_card = QFrame()
        cur_card.setStyleSheet("""
            QFrame {
                background: rgba(255,255,255,0.025);
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 14px;
            }
        """)
        cl = QVBoxLayout(cur_card)
        cl.setContentsMargins(20, 18, 20, 18)
        cl.setSpacing(10)

        ch = QHBoxLayout()
        ci = QLabel("💱")
        ci.setStyleSheet("font-size:20px; background:transparent; border:none;")
        ch.addWidget(ci); ch.addSpacing(8)
        cv = QVBoxLayout(); cv.setSpacing(2)
        ct = QLabel("Varsayilan Para Birimi")
        ct.setStyleSheet(
            "color:#F1F5F9; font-size:14px; font-weight:700;"
            "background:transparent; border:none;"
        )
        cd = QLabel("Faturalar ve raporlar icin kullanilacak ana para birimi")
        cd.setStyleSheet("color:#64748B; font-size:12px; background:transparent; border:none;")
        cv.addWidget(ct); cv.addWidget(cd)
        ch.addLayout(cv); ch.addStretch()
        cl.addLayout(ch)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems([
            "TRY  —  Turk Lirasi",
            "USD  —  Amerikan Dolari",
            "EUR  —  Euro",
            "GBP  —  Ingiliz Sterlini",
        ])
        self.currency_combo.setFixedHeight(44)
        self.currency_combo.setStyleSheet("""
            QComboBox {
                background: #08090F;
                color: #F1F5F9;
                border: 1.5px solid rgba(255,255,255,0.09);
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 14px;
            }
            QComboBox:hover, QComboBox:focus {
                border-color: #6366F1;
                background: #0A0C16;
            }
            QComboBox::drop-down { border:none; width:32px; }
            QComboBox::down-arrow {
                border-left:5px solid transparent;
                border-right:5px solid transparent;
                border-top:5px solid #6366F1;
                margin-right:12px;
            }
            QComboBox QAbstractItemView {
                background: #10131C;
                color: #F1F5F9;
                selection-background-color: #4F46E5;
                border: 1px solid rgba(255,255,255,0.09);
                border-radius: 8px;
                outline: none;
            }
        """)
        cl.addWidget(self.currency_combo)
        root.addWidget(cur_card)

        # Toggle kartlari
        self.exc_card = _ToggleCard(
            "🔄", "Otomatik Kur Guncellemesi",
            "TCMB den guncel doviz kurlarini otomatik olarak cek",
            "Evet, otomatik", "Hayir, manuel", default_yes=True,
        )
        root.addWidget(self.exc_card)

        self.bak_card = _ToggleCard(
            "💾", "Otomatik Yedekleme",
            "Veritabanini duzenli olarak otomatik yedekle",
            "Evet, otomatik", "Hayir, manuel", default_yes=True,
        )
        root.addWidget(self.bak_card)

        self.sms_card = _ToggleCard(
            "📱", "SMS Bildirimleri",
            "Musterilere servis durumu hakkinda SMS gonder",
            "Aktif", "Pasif", default_yes=False,
        )
        root.addWidget(self.sms_card)

        root.addStretch()

        note = QLabel("Bu ayarlarin tamamini Ayarlar menusu uzerinden degistirebilirsiniz.")
        note.setStyleSheet(
            "color:#475569; font-size:11px; font-style:italic; border:none; background:transparent;"
        )
        root.addWidget(note)

    def validate(self):
        return True

    def get_data(self):
        cur_txt = self.currency_combo.currentText()
        currency = cur_txt.split("—")[0].strip() if "—" in cur_txt else "TRY"
        return {
            "basic_settings": {
                "default_currency":     currency,
                "auto_exchange_update": self.exc_card.value(),
                "auto_backup":          self.bak_card.value(),
                "sms_notifications":    self.sms_card.value(),
            }
        }
''').lstrip()

# ─────────────────────────────────────────────────────────────────────────────
COMPLETION = textwrap.dedent('''
"""
Completion Step - Kurulum Tamamlandi  (v5.0)
Premium animated success screen
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QGraphicsOpacityEffect


class CompletionStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.wizard = parent
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 32, 44, 28)
        root.setSpacing(0)
        root.addStretch(1)

        # Ikon
        self.ico = QLabel("✓")
        self.ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico.setStyleSheet("""
            color: #10B981;
            font-size: 56px;
            font-weight: 800;
            background: rgba(16,185,129,0.1);
            border: 2px solid rgba(16,185,129,0.3);
            border-radius: 50px;
            min-width: 100px;
            max-width: 100px;
            min-height: 100px;
            max-height: 100px;
        """)
        ico_row = QHBoxLayout()
        ico_row.addStretch(); ico_row.addWidget(self.ico); ico_row.addStretch()
        root.addLayout(ico_row)
        root.addSpacing(24)

        # Baslik
        title = QLabel("Kurulum Tamamlandi!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#F1F5F9; font-size:26px; font-weight:800;"
            "background:transparent; border:none;"
        )
        root.addWidget(title)
        root.addSpacing(8)

        sub = QLabel("AYEC Pro sisteminiz kullanima hazir.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "color:#94A3B8; font-size:15px; background:transparent; border:none;"
        )
        root.addWidget(sub)
        root.addSpacing(28)

        # Ozet kart
        self.sum_card = QFrame()
        self.sum_card.setStyleSheet("""
            background: rgba(255,255,255,0.025);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
        """)
        sv = QVBoxLayout(self.sum_card)
        sv.setContentsMargins(24, 20, 24, 20)
        sv.setSpacing(12)

        hdr = QLabel("Kurulum Ozeti")
        hdr.setStyleSheet(
            "color:#818CF8; font-size:11px; font-weight:700; letter-spacing:2px;"
            "text-transform:uppercase; background:transparent; border:none;"
        )
        sv.addWidget(hdr)

        self.lbl_company = QLabel()
        self.lbl_admin   = QLabel()
        for lbl in [self.lbl_company, self.lbl_admin]:
            lbl.setStyleSheet(
                "color:#F1F5F9; font-size:13px; background:transparent; border:none;"
            )
            lbl.setWordWrap(True)
            sv.addWidget(lbl)

        # Uyari bandı
        warn = QLabel(
            "   Kullanici adinizi ve sifrenizi guvenli bir yerde saklayin!"
        )
        warn.setStyleSheet("""
            color: #FBBF24;
            background: rgba(251,191,36,0.08);
            border: 1px solid rgba(251,191,36,0.2);
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 12px;
        """)
        sv.addWidget(warn)
        root.addWidget(self.sum_card)
        root.addSpacing(20)

        # Sonraki adimlar
        ns = QFrame()
        ns.setStyleSheet("""
            background: rgba(79,70,229,0.06);
            border: 1px solid rgba(79,70,229,0.18);
            border-radius: 14px;
        """)
        nv = QVBoxLayout(ns)
        nv.setContentsMargins(20, 16, 20, 16)
        nv.setSpacing(8)

        nt = QLabel("Sonraki Adimlar")
        nt.setStyleSheet(
            "color:#818CF8; font-size:13px; font-weight:700;"
            "background:transparent; border:none;"
        )
        nv.addWidget(nt)

        for step in [
            "1.  Giris ekraninda kullanici adi ve sifrenizle sisteme giris yapin",
            "2.  Ayarlar menusu uzerinden sirket logonuzu yukleyin",
            "3.  Ilk musterinizi ve servis kaydinizi olusturun",
            "4.  Stok ve finans modullerini verilerle doldurun",
        ]:
            sl = QLabel(step)
            sl.setStyleSheet(
                "color:#94A3B8; font-size:12px;"
                "background:transparent; border:none; margin-left:4px;"
            )
            sl.setWordWrap(True)
            nv.addWidget(sl)
        root.addWidget(ns)

        root.addStretch(1)

        foot = QLabel(
            "Tamamla butonuna tikladiginizda giris ekranina yonlendirileceksiniz."
        )
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setStyleSheet(
            "color:#475569; font-size:11px; font-style:italic;"
            "background:transparent; border:none;"
        )
        root.addWidget(foot)

    def showEvent(self, event):
        super().showEvent(event)
        if self.wizard and hasattr(self.wizard, "setup_data"):
            d = self.wizard.setup_data
            ci = d.get("company_info", {})
            au = d.get("admin_user",   {})
            self.lbl_company.setText(
                f"Sirket :  {ci.get('company_name','—')}     "
                f"Yetkili :  {ci.get('authorized_person','—')}"
            )
            self.lbl_admin.setText(
                f"Yonetici :  {au.get('username','—')}     "
                f"Ad Soyad :  {au.get('full_name','—')}"
            )
        # Kisa gecikme sonrasi ikon animasyonu
        QTimer.singleShot(100, self._animate_icon)

    def _animate_icon(self):
        eff = QGraphicsOpacityEffect(self.ico)
        self.ico.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(500)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _done():
            self.ico.setGraphicsEffect(None)

        anim.finished.connect(_done)
        anim.start()
        self._ico_anim = anim

    def validate(self):
        return True

    def get_data(self):
        return {}
''').lstrip()


# ─────────────────────────────────────────────────────────────────────────────
def write(filename, content):
    path = os.path.join(BASE, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  OK: {filename}")


if __name__ == "__main__":
    print("Writing wizard step files...")
    write("admin_user_step.py",    ADMIN_USER)
    write("basic_settings_step.py", BASIC_SETTINGS)
    write("completion_step.py",    COMPLETION)
    print("Done.")
