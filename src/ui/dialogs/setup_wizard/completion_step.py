# -*- coding: utf-8 -*-

"""
Completion Step - Kurulum Tamamlandı (v5.0)
Premium animated success screen
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect


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

        self.ico = QLabel("✓")
        self.ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ico.setStyleSheet(
            """
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
            """
        )
        ico_row = QHBoxLayout()
        ico_row.addStretch()
        ico_row.addWidget(self.ico)
        ico_row.addStretch()
        root.addLayout(ico_row)
        root.addSpacing(24)

        title = QLabel("Kurulum Tamamlandı!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "color:#0F172B; font-size:26px; font-weight:800;"
            "background:transparent; border:none;"
        )
        root.addWidget(title)
        root.addSpacing(8)

        sub = QLabel("AYEC Pro sisteminiz kullanıma hazır.")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(
            "color:#475568; font-size:15px; background:transparent; border:none;"
        )
        root.addWidget(sub)
        root.addSpacing(28)

        self.sum_card = QFrame()
        self.sum_card.setStyleSheet(
            """
            background: #FFFFFF;
            border: 1.5px solid #E2E8F0;
            border-radius: 14px;
            """
        )
        sv = QVBoxLayout(self.sum_card)
        sv.setContentsMargins(24, 20, 24, 20)
        sv.setSpacing(12)

        hdr = QLabel("Kurulum Özeti")
        hdr.setStyleSheet(
            "color:#4F46E5; font-size:11px; font-weight:700; letter-spacing:2px;"
            "text-transform:uppercase; background:transparent; border:none;"
        )
        sv.addWidget(hdr)

        self.lbl_company = QLabel()
        self.lbl_admin = QLabel()
        for lbl in [self.lbl_company, self.lbl_admin]:
            lbl.setStyleSheet(
                "color:#0F172B; font-size:13px; background:transparent; border:none;"
            )
            lbl.setWordWrap(True)
            sv.addWidget(lbl)

        warn = QLabel("   Kullanıcı adınızı ve şifrenizi güvenli bir yerde saklayın!")
        warn.setStyleSheet(
            """
            color: #B45309;
            background: #FEF3C7;
            border: 1px solid #FCD34D;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            padding: 8px 12px;
            """
        )
        sv.addWidget(warn)
        root.addWidget(self.sum_card)
        root.addSpacing(20)

        ns = QFrame()
        ns.setStyleSheet(
            """
            background: #EEF2FF;
            border: 1.5px solid #C7D2FE;
            border-radius: 14px;
            """
        )
        nv = QVBoxLayout(ns)
        nv.setContentsMargins(20, 16, 20, 16)
        nv.setSpacing(8)

        nt = QLabel("Sonraki Adımlar")
        nt.setStyleSheet(
            "color:#4F46E5; font-size:13px; font-weight:700;"
            "background:transparent; border:none;"
        )
        nv.addWidget(nt)

        for step in [
            "1.  Giriş ekranında kullanıcı adı ve şifrenizle sisteme giriş yapın",
            "2.  Ayarlar menüsü üzerinden şirket logonuzu yükleyin",
            "3.  İlk müşterinizi ve servis kaydınızı oluşturun",
            "4.  Stok ve finans modüllerini verilerle doldurun",
        ]:
            sl = QLabel(step)
            sl.setStyleSheet(
                "color:#334155; font-size:12px;"
                "background:transparent; border:none; margin-left:4px;"
            )
            sl.setWordWrap(True)
            nv.addWidget(sl)
        root.addWidget(ns)

        root.addStretch(1)

        foot = QLabel("Tamamla butonuna tıkladığınızda giriş ekranına yönlendirileceksiniz.")
        foot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        foot.setStyleSheet(
            "color:#64748A; font-size:11px; font-style:italic;"
            "background:transparent; border:none;"
        )
        root.addWidget(foot)

    def showEvent(self, event):
        super().showEvent(event)
        if self.wizard and hasattr(self.wizard, "setup_data"):
            d = self.wizard.setup_data
            ci = d.get("company_info", {})
            au = d.get("admin_user", {})
            self.lbl_company.setText(
                f"Şirket :  {ci.get('company_name', '-')}     "
                f"Yetkili :  {ci.get('authorized_person', '-')}"
            )
            self.lbl_admin.setText(
                f"Yönetici :  {au.get('username', '-')}     "
                f"Ad Soyad :  {au.get('full_name', '-')}"
            )
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
