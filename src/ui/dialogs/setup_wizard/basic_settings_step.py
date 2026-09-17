# -*- coding: utf-8 -*-
"""
Basic Settings Step - Temel Ayarlar (v5.0)
Premium toggle-switch settings
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QButtonGroup, QRadioButton, QComboBox, QCheckBox, QTextEdit, QMessageBox,
)
from datetime import datetime

from src.utils.system_config import SYSTEM_MODES
from src.utils.currency_helper import CurrencyHelper


class _ToggleCard(QFrame):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Başlık + açıklama + iki radyo seçeneği."""

    def __init__(self, icon, title, desc, opt_yes, opt_no, default_yes=True, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 14px;
            }
            QFrame:hover {
                background: #FAFBFF;
                border-color: #C7D2FE;
            }
            """
        )

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 18, 20, 18)
        main.setSpacing(10)

        top = QHBoxLayout()
        ico = QLabel(icon)
        ico.setStyleSheet("font-size:20px; background:transparent; border:none;")
        top.addWidget(ico)
        top.addSpacing(8)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color:#0F172B; font-size:14px; font-weight:700;"
            "background:transparent; border:none;"
        )
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(
            "color:#475568; font-size:12px; background:transparent; border:none;"
        )
        desc_label.setWordWrap(True)

        text_col.addWidget(title_label)
        text_col.addWidget(desc_label)
        top.addLayout(text_col)
        top.addStretch()
        main.addLayout(top)

        rb_row = QHBoxLayout()
        rb_row.setSpacing(20)
        self.grp = QButtonGroup(self)

        for txt, val, checked in [
            (opt_yes, True, default_yes),
            (opt_no, False, not default_yes),
        ]:
            rb = QRadioButton(txt)
            rb.setChecked(checked)
            rb.setProperty("val", val)
            rb.setStyleSheet(
                """
                QRadioButton {
                    color: #475568; font-size: 13px; spacing: 8px;
                    font-weight: 500;
                }
                QRadioButton::indicator { width:18px; height:18px; }
                QRadioButton::indicator:unchecked {
                    border:1.5px solid #CBD5E1;
                    border-radius:9px; background:#FFFFFF;
                }
                QRadioButton::indicator:checked {
                    border:2px solid #6366F1;
                    border-radius:9px; background:#6366F1;
                }
                QRadioButton:hover { color:#0F172B; }
                """
            )
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
        self._wire_ui_signals()

    def _build_legal_card(self):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#F8FAFF; border:1.5px solid #C7D2FE; border-radius:14px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title = QLabel("Kullan\u0131m, Veri ve Gizlilik Bildirimi")
        title.setStyleSheet("color:#1E1B4B; font-size:14px; font-weight:700; border:none;")
        layout.addWidget(title)

        summary = QTextEdit()
        summary.setReadOnly(True)
        summary.setFixedHeight(132)
        summary.setPlainText(
            "KULLANIM VE LISANS SOZLESMESI (v2026.08)\n"
            "AYEC Pro, lisanslanan kullanici ve firma icin sunulan bir yazilim hizmetidir. "
            "Yazilimin yetkisiz kopyalanmasi, tersine muhendisligi ve lisans sinirlarini asan kullanimi yasaktir.\n\n"
            "VERI VE YEDEKLEME SORUMLULUGU\n"
            "Musteri, kritik verilerinin duzenli yedegini almak ve yedekleri kontrol etmekle sorumludur. "
            "Otomatik yedekleme araci destek niteligindedir; kullanici hatasi, cihaz arizasi, baglanti kesintisi "
            "veya ucuncu taraf hizmetinden dogan veri kaybi icin mutlak veri kaybi garantisi vermez. "
            "Zorunlu hukuk kurallari ile kasit veya agir kusur halleri saklidir.\n\n"
            "GIZLILIK AYDINLATMASI\n"
            "Hesap, firma ve servis verileri hizmetin sunulmasi, guvenlik, destek ve yasal yukumlulukler icin islenir. "
            "Aydinlatma metnini okumak zorunludur; pazarlama iletisim izni istege baglidir."
        )
        summary.setStyleSheet(
            "QTextEdit { background:#FFFFFF; color:#334155; border:1px solid #CBD5E1; "
            "border-radius:9px; padding:8px; font-size:11px; }"
        )
        layout.addWidget(summary)

        self.terms_accepted_check = QCheckBox(
            "Kullan\u0131m ve Lisans S\u00f6zle\u015fmesi'ni okudum ve kabul ediyorum."
        )
        self.backup_responsibility_check = QCheckBox(
            "Veri yedekleme sorumlulu\u011funu ve hizmet s\u0131n\u0131rlar\u0131n\u0131 okudum."
        )
        self.privacy_notice_check = QCheckBox(
            "KVKK ayd\u0131nlatma bildirimini okudum."
        )
        self.marketing_opt_in_check = QCheckBox(
            "Kampanya ve hizmet duyurular\u0131 i\u00e7in ileti\u015fim izni veriyorum (iste\u011fe ba\u011fl\u0131)."
        )
        for checkbox in (
            self.terms_accepted_check,
            self.backup_responsibility_check,
            self.privacy_notice_check,
            self.marketing_opt_in_check,
        ):
            checkbox.setStyleSheet(
                "QCheckBox { color:#334155; font-size:12px; background:transparent; border:none; spacing:8px; }"
            )
            layout.addWidget(checkbox)
        return card

    def _build_select_card(self, icon, title, desc, combo):
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                background: #FFFFFF;
                border: 1.5px solid #E2E8F0;
                border-radius: 14px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size:20px; background:transparent; border:none;")
        header.addWidget(icon_label)
        header.addSpacing(8)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title_label = QLabel(title)
        title_label.setStyleSheet(
            "color:#0F172B; font-size:14px; font-weight:700;"
            "background:transparent; border:none;"
        )
        desc_label = QLabel(desc)
        desc_label.setStyleSheet(
            "color:#475568; font-size:12px; background:transparent; border:none;"
        )
        desc_label.setWordWrap(True)
        text_col.addWidget(title_label)
        text_col.addWidget(desc_label)

        header.addLayout(text_col)
        header.addStretch()
        layout.addLayout(header)
        layout.addWidget(combo)
        return card

    def _combo_style(self):
        return """
            QComboBox {
                background: #FFFFFF;
                color: #0F172B;
                border: 1.5px solid #CBD5E1;
                border-radius: 10px;
                padding: 8px 14px;
                font-size: 14px;
            }
            QComboBox:hover, QComboBox:focus {
                border-color: #6366F1;
                background: #FFFFFF;
            }
            QComboBox::drop-down { border:none; width:32px; }
            QComboBox::down-arrow {
                border-left:5px solid transparent;
                border-right:5px solid transparent;
                border-top:5px solid #6366F1;
                margin-right:12px;
            }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                color: #0F172B;
                selection-background-color: #6366F1;
                selection-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                outline: none;
            }
        """

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(44, 28, 44, 24)
        root.setSpacing(16)

        desc = QLabel(
            "Sisteminizin temel çalışma parametrelerini yapılandırın. "
            "Bu ayarları daha sonra değiştirebilirsiniz."
        )
        desc.setStyleSheet(
            "color:#475568; font-size:14px; border:none; background:transparent;"
        )
        desc.setWordWrap(True)
        root.addWidget(desc)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(CurrencyHelper.get_choice_texts())
        self.currency_combo.setFixedHeight(44)
        self.currency_combo.setStyleSheet(self._combo_style())
        root.addWidget(
            self._build_select_card(
                "💱",
                "Varsayılan Para Birimi",
                "Faturalar ve raporlar için kullanılacak ana para birimi",
                self.currency_combo,
            )
        )

        profile_widget = QWidget()
        profile_layout = QHBoxLayout(profile_widget)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        profile_layout.setSpacing(18)
        self.device_profile_checks = {}
        for profile_id, label in (
            ("bilgisayar", "Bilgisayar"),
            ("cep_telefonu", "Cep Telefonu"),
            ("akilli_ev", "Akilli Ev"),
        ):
            checkbox = QCheckBox(label)
            checkbox.setChecked(profile_id == "bilgisayar")
            self.device_profile_checks[profile_id] = checkbox
            profile_layout.addWidget(checkbox)
        profile_layout.addStretch()
        root.addWidget(
            self._build_select_card(
                "C",
                "Cihaz Katalog Is Kollari",
                "Yeni cihaz eklerken gosterilecek marka ve model gruplarini secin",
                profile_widget,
            )
        )

        self.sector_combo = QComboBox()
        for sector_key, sector_meta in SYSTEM_MODES.items():
            self.sector_combo.addItem(sector_meta.get("display_name", sector_key), sector_key)
        default_sector_index = self.sector_combo.findData("otomotiv")
        if default_sector_index >= 0:
            self.sector_combo.setCurrentIndex(default_sector_index)
        self.sector_combo.setFixedHeight(44)
        self.sector_combo.setStyleSheet(self._combo_style())
        root.addWidget(
            self._build_select_card(
                "🏭",
                "Sektör Seçimi",
                "Programı hangi iş kolu için kullanacağınızı seçin",
                self.sector_combo,
            )
        )

        self.exc_card = _ToggleCard(
            "🔄",
            "Otomatik Kur Güncellemesi",
            "TCMB'den güncel döviz kurlarını otomatik olarak çek",
            "Evet, otomatik",
            "Hayır, manuel",
            default_yes=True,
        )
        root.addWidget(self.exc_card)

        self.bak_card = _ToggleCard(
            "💾",
            "Otomatik Yedekleme",
            "Veritabanını düzenli olarak otomatik yedekle",
            "Evet, otomatik",
            "Hayır, manuel",
            default_yes=True,
        )
        root.addWidget(self.bak_card)

        self.sms_card = _ToggleCard(
            "📱",
            "SMS Bildirimleri",
            "Müşterilere servis durumu hakkında SMS gönder",
            "Aktif",
            "Pasif",
            default_yes=False,
        )
        root.addWidget(self.sms_card)

        root.addStretch()

        note = QLabel("Bu ayarların tamamını Ayarlar menüsü üzerinden değiştirebilirsiniz.")
        note.setStyleSheet(
            "color:#64748A; font-size:11px; font-style:italic; border:none; background:transparent;"
        )
        root.addWidget(note)

    def validate(self):
        return True

    def get_data(self):
        currency = CurrencyHelper.combo_to_code(self.currency_combo)
        return {
            "basic_settings": {
                "currency": currency,
                "default_currency": currency,
                "current_sector": self.sector_combo.currentData() or "otomotiv",
                "device_business_profiles": ",".join(
                    profile_id for profile_id, checkbox in self.device_profile_checks.items()
                    if checkbox.isChecked()
                ) or "bilgisayar",
                "auto_exchange_update": self.exc_card.value(),
                "auto_backup": self.bak_card.value(),
                "sms_notifications": self.sms_card.value(),
            }
        }

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)

    def _wire_ui_signals(self):
        self.currency_combo.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.sector_combo.currentIndexChanged.connect(self._on_ui_widget_changed)
        for checkbox in self.device_profile_checks.values():
            checkbox.toggled.connect(self._on_ui_widget_changed)
