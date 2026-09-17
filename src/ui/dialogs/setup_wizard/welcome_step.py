# -*- coding: utf-8 -*-

"""
Welcome Step - Hoş Geldiniz
Modern açık tema — nefes alan, sade, profesyonel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout,
    QCheckBox, QTextEdit,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect

# Açık tema renkleri (QSS transformatörünü atlatmak için hafifçe kaydırılmış renk kodları)
_BG_CARD  = "#FFFFFE"
_BG_PAGE  = "#F8FAFB"
_BORDER   = "#E2E8F1"
_TXT1     = "#0F172B"   # başlık
_TXT2     = "#475568"   # açıklama
_TXT3     = "#94A3B7"   # alt metin
_ACCENT   = "#6366F0"   # indigo

FEATURES = [
    ("⚡", "#EEF2FE", "#6366F0", "Hızlı Kurulum",       "Tüm modüller otomatik yapılandırılır"),
    ("🔒", "#F5F3FE", "#7C3AEC", "Güvenli Veri",         "AES-256 şifreleme standartları"),
    ("☁️", "#EFF6FE", "#3B82F5", "Bulut Entegrasyonu",   "Gerçek zamanlı senkronizasyon"),
    ("📱", "#ECFDF4", "#10B980", "Mobil Erişim",          "iOS ve Android uyumlu"),
    ("💰", "#FFF1F1", "#F43F5D", "Ön Muhasebe",           "Cari, fatura ve kasa takibi"),
    ("🔄", "#F5F3FE", "#8B5CF5", "Otomatik Yedek",        "Verileriniz asla kaybolmaz"),
    ("📊", "#ECFEFE", "#06B6D3", "Gelişmiş Raporlar",     "Anlık iş performans göstergeleri"),
    ("🤖", "#FDF2F7", "#EC4898", "AI Asistan",            "Yapay zeka destekli iş önerileri"),
]

_LEGAL_SUMMARY = (
    "AYEC PRO KULLANIM, LISANS VE VERI ISLEME KOSULLARI (v2026.09)\n\n"
    "1. TARAFLAR VE KAPSAM\n"
    "Bu kosullar, AYEC Pro yaziliminin masaustu, web ve mobil bilesenlerini kullanan firma ile hizmet saglayici arasindaki kullanim iliskisini duzenler. "
    "Kullanici, firma adina islem yapmaya yetkili oldugunu kabul eder.\n\n"
    "2. LISANS HAKKI\n"
    "Yazilim, satin alinan veya tanimlanan lisans plani kapsaminda; belirlenen firma, kullanici, cihaz ve donanim kimligi ile sinirli, devredilemez bir kullanim hakki verir. "
    "Lisans mulkiyet devri anlamina gelmez.\n\n"
    "3. DENEME, ODEME VE SURE\n"
    "Deneme surumu, kurulum tarihinden itibaren 15 gun ile sinirlidir. Deneme veya lisans suresi sonunda ilgili hizmetler sinirlandirilabilir ya da erisim kapatilabilir. "
    "Ucret, yenileme, iptal ve iade kosullari; secilen paket, teklif ve varsa zorunlu mevzuat hukumlerine gore uygulanir.\n\n"
    "4. YASAKLI KULLANIM\n"
    "Yazilimin yetkisiz kopyalanmasi, dagitilmasi, tersine muhendisligi, lisans denetimini asmaya yonelik islem yapilmasi, yetkisiz erisim veya baskalarinin verilerine erisim yasaktir.\n\n"
    "5. KULLANICI VE FIRMA SORUMLULUGU\n"
    "Kullanici adi, parola, erisim yetkileri, girilen firma/musteri/servis verilerinin dogrulugu ve yasalara uygunlugu firmaya aittir. "
    "Yetkisiz erisim supheleri gecikmeden giderilmeli ve gerekli durumlarda destek ekibine bildirilmelidir.\n\n"
    "6. VERI, YEDEKLEME VE GERI YUKLEME\n"
    "Musteri kritik verilerini duzenli olarak yedeklemek, yedekleri test etmek ve kendi saklama yukumluluklerini yerine getirmekle sorumludur. "
    "Otomatik yedekleme kolaylastirici bir arac olup; kullanici hatasi, cihaz arizasi, elektrik kesintisi, baglanti sorunu veya ucuncu taraf hizmetlerinden kaynaklanan kayiplara karsi mutlak garanti vermez.\n\n"
    "7. HIZMET SUREKLILIGI VE DESTEK\n"
    "Bakim, guncelleme, guvenlik veya altyapi nedenleriyle planli ya da zorunlu kesintiler olabilir. Destek hizmeti makul surede saglanir; internet, cihaz, isletim sistemi veya harici entegrasyon kaynakli sorunlarin giderilmesi garanti edilmez.\n\n"
    "8. KISISEL VERILER VE GIZLILIK\n"
    "Hesap, firma ve servis verileri; hizmetin sunulmasi, guvenlik, destek, lisanslama ve yasal yukumluluklerin yerine getirilmesi amaclariyla islenir. "
    "Kisisel veri isleme rollerinin ve aktarimlarin kapsamı somut hizmete gore ayrica aydinlatilir; musterinin kendi musterilerine iliskin veri sorumlulugu saklidir.\n\n"
    "9. KVKK AYDINLATMASI\n"
    "Aydinlatma metni; veri sorumlusunun kimligi, isleme amaci, aktarimlar, toplama yontemi, hukuki sebep ve ilgili kisi haklarini acik ve anlasilir bicimde kapsamalidir. "
    "Pazarlama iletisim izni hizmetin kullanilmasi icin zorunlu degildir ve ayri, istege bagli bir onaydir.\n\n"
    "10. GUVENLIK VE BILDIRIM\n"
    "Taraflar, uygun teknik ve idari guvenlik onlemlerini almaya calisir. Supheli hesap hareketi, veri ihlali veya ciddi zafiyet fark edildiginde diger taraf makul surede bilgilendirilir.\n\n"
    "11. SORUMLULUGUN SINIRI\n"
    "Kanunen kaldirilamayacak sorumluluklar sakli kalmak uzere; dolayli zarar, kar kaybi, veri kaybi, is kesintisi veya ucuncu taraf kaynakli zararlardan dogan sorumluluk, uygulanabilir hukukun izin verdigi olcude sinirlanir.\n\n"
    "12. GUNCELLEME, FESIH VE UYUSMAZLIK\n"
    "Kosullar, mevzuat veya hizmetteki degisiklikler nedeniyle guncellenebilir; onemli degisiklikler makul bir yolla bildirilir. "
    "Agir ihlal, odeme gecikmesi veya guvenlik riski halinde erisim askıya alinabilir. Uyusmazliklarda once dostane cozum aranir; emredici hukuk kurallari saklidir.\n\n"
    "Bu metin urun ici bilgilendirme ve kabul kaydidir. Ticari, vergi, tuketici, KVKK veya veri isleme yukumlulukleri icin faaliyetinize ozel hukuki inceleme yapilmalidir."
)


class WelcomeStep(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {_BG_PAGE}; border: none;")
        self._init_ui()
        QTimer.singleShot(80, self._animate_in)

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 36, 48, 28)
        root.setSpacing(0)

        # ── Hero ──────────────────────────────────────────────
        hero = QFrame()
        hero.setStyleSheet("background:transparent; border:none;")
        hero_v = QVBoxLayout(hero)
        hero_v.setContentsMargins(0, 0, 0, 0)
        hero_v.setSpacing(10)

        # Badge
        badge = QLabel("  ✦  YENİ KURULUM  ✦  ")
        badge.setAlignment(Qt.AlignmentFlag.AlignLeft)
        badge.setStyleSheet(
            f"""
            color: {_ACCENT};
            background: #EEF2FE;
            border: 1px solid #C7D2FE;
            border-radius: 20px;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 2.5px;
            padding: 5px 16px;
            max-width: 185px;
            """
        )
        hero_v.addWidget(badge)
        hero_v.addSpacing(6)

        # Başlık
        title = QLabel("İşletmenizi Dijitalleştirin")
        title.setStyleSheet(
            f"""
            color: {_TXT1};
            font-size: 30px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: transparent;
            border: none;
            """
        )
        hero_v.addWidget(title)

        # Alt başlık
        subtitle = QLabel(
            "AYEC Pro ile servis yönetimi, muhasebe, stok takibi ve çok daha fazlası\n"
            "tek bir platformda. Kurulum birkaç dakikanızı alacak."
        )
        subtitle.setStyleSheet(
            f"""
            color: {_TXT2};
            font-size: 14px;
            background: transparent;
            border: none;
            """
        )
        subtitle.setWordWrap(True)
        hero_v.addWidget(subtitle)

        root.addWidget(hero)
        root.addSpacing(28)

        # ── Özellik Kartları ──────────────────────────────────
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background:transparent; border:none;")
        grid = QGridLayout(grid_frame)
        grid.setSpacing(12)
        grid.setContentsMargins(0, 0, 0, 0)

        self._cards = []
        for i, (icon, bg, color, ttl, sub) in enumerate(FEATURES):
            card = self._make_card(icon, bg, color, ttl, sub)
            grid.addWidget(card, i // 4, i % 4)
            self._cards.append(card)

        root.addWidget(grid_frame)
        root.addSpacing(18)

        root.addWidget(self._build_legal_card())
        root.addStretch()

        # ── Footer ────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_BORDER}; border: none;")
        root.addWidget(sep)
        root.addSpacing(12)

        footer_row = QHBoxLayout()
        dot = QLabel("●")
        dot.setStyleSheet("color:#10B980; font-size:8px; border:none; background:transparent;")
        footer_row.addWidget(dot)
        footer_row.addSpacing(6)
        note = QLabel("Kurulumu istediğiniz zaman durdurabilir, daha sonra devam edebilirsiniz.")
        note.setStyleSheet(f"color:{_TXT3}; font-size:12px; border:none; background:transparent;")
        footer_row.addWidget(note)
        footer_row.addStretch()
        root.addLayout(footer_row)

    def _build_legal_card(self):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#F8FAFF; border:1px solid #C7D2FE; border-radius:12px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(7)

        title = QLabel("Kullan\u0131m, Lisans, Veri ve Gizlilik Ko\u015fullar\u0131 (12 Madde)")
        title.setStyleSheet(
            "color:#1E1B4B; font-size:13px; font-weight:700; border:none; background:transparent;"
        )
        layout.addWidget(title)

        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(_LEGAL_SUMMARY)
        details.setFixedHeight(230)
        details.setStyleSheet(
            "QTextEdit { background:#FFFFFF; color:#334155; border:1px solid #CBD5E1; "
            "border-radius:8px; padding:7px; font-size:11px; }"
        )
        layout.addWidget(details)

        self.terms_accepted_check = QCheckBox(
            "Kullan\u0131m ve Lisans S\u00f6zle\u015fmesi'ni okudum ve kabul ediyorum."
        )
        self.backup_responsibility_check = QCheckBox(
            "Veri yedekleme sorumlulu\u011funu ve hizmet s\u0131n\u0131rlar\u0131n\u0131 okudum."
        )
        self.privacy_notice_check = QCheckBox(
            "KVKK ayd\u0131nlatma bildirimini okudum."
        )
        for checkbox in (
            self.terms_accepted_check,
            self.backup_responsibility_check,
            self.privacy_notice_check,
        ):
            checkbox.setStyleSheet(
                "QCheckBox { color:#334155; font-size:11px; background:transparent; border:none; spacing:7px; }"
            )
            layout.addWidget(checkbox)
        return card

    def _make_card(self, icon, bg_color, icon_color, title, sub):
        card = QFrame()
        card.setFixedHeight(82)
        card.setStyleSheet(
            f"""
            QFrame {{
                background: {_BG_CARD};
                border: 1px solid {_BORDER};
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: #FAFBFF;
                border-color: #C7D2FE;
            }}
            """
        )

        h = QHBoxLayout(card)
        h.setContentsMargins(14, 12, 14, 12)
        h.setSpacing(12)

        # İkon kutusu
        icon_box = QLabel(icon)
        icon_box.setFixedSize(40, 40)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(
            f"""
            background: {bg_color};
            border-radius: 10px;
            font-size: 18px;
            border: none;
            """
        )
        h.addWidget(icon_box)

        v = QVBoxLayout()
        v.setSpacing(2)
        t = QLabel(title)
        t.setStyleSheet(f"color:{_TXT1}; font-size:12px; font-weight:700; background:transparent; border:none;")
        s = QLabel(sub)
        s.setStyleSheet(f"color:{_TXT3}; font-size:10px; background:transparent; border:none;")
        s.setWordWrap(True)
        v.addWidget(t)
        v.addWidget(s)
        h.addLayout(v)
        return card

    def _animate_in(self):
        """Kartları sırayla fade-in ile göster."""
        for i, card in enumerate(self._cards):
            eff = QGraphicsOpacityEffect(card)
            card.setGraphicsEffect(eff)
            eff.setOpacity(0)
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(250)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)

            def _done(w=card):
                w.setGraphicsEffect(None)

            anim.finished.connect(_done)
            QTimer.singleShot(i * 45, anim.start)
            setattr(self, f"_anim_{i}", anim)

    def validate(self):
        return (
            self.terms_accepted_check.isChecked()
            and self.backup_responsibility_check.isChecked()
            and self.privacy_notice_check.isChecked()
        )

    def get_data(self):
        return {
            "legal_acceptance": {
                "terms_version": "2026.09",
                "terms_accepted": self.terms_accepted_check.isChecked(),
                "backup_responsibility_acknowledged": self.backup_responsibility_check.isChecked(),
                "privacy_notice_read": self.privacy_notice_check.isChecked(),
                "marketing_opt_in": False,
            }
        }
