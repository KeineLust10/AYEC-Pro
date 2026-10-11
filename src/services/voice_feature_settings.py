"""Persistent feature switches for the voice assistant."""

VOICE_ASSISTANT_FEATURES = (
    (
        "voice_feature_navigation",
        "Men\u00fc ve kay\u0131tlarda sesle gezinme",
        "Men\u00fcleri a\u00e7ma, ekranlarda arama ve kay\u0131tlar aras\u0131nda gezinme komutlar\u0131n\u0131 a\u00e7ar.",
        True,
    ),
    (
        "voice_feature_ui_controls",
        "D\u00fc\u011fme ve anahtarlar\u0131 sesle kullanma",
        "Ekrandaki d\u00fc\u011fmeleri \u00e7al\u0131\u015ft\u0131rma ve anahtar kontrollerini de\u011fi\u015ftirme komutlar\u0131n\u0131 a\u00e7ar.",
        True,
    ),
    (
        "voice_feature_form_filling",
        "Sesle form doldurma",
        "Form a\u00e7\u0131l\u0131nca izin sorar; s\u00f6yledi\u011finiz bilgileri ilgili alanlara yazar.",
        True,
    ),
    (
        "voice_feature_required_guidance",
        "Zorunlu alanlarda ad\u0131m ad\u0131m rehberlik",
        "Eksik zorunlu alanlar\u0131 s\u0131rayla sorar ve formun ilerlemesini bildirir.",
        True,
    ),
    (
        "voice_feature_spoken_recap",
        "Duyulan bilgiyi geri okuma",
        "Doldurulan alanlar\u0131 sesli \u00f6zetler; hassas de\u011ferleri gizli tutar.",
        True,
    ),
    (
        "voice_feature_field_correction",
        "Alan d\u00fczeltme ve temizleme",
        "Alan de\u011ferini d\u00fczeltme, ad\u0131yla temizleme ve formu s\u0131f\u0131rlama komutlar\u0131n\u0131 a\u00e7ar.",
        True,
    ),
    (
        "voice_feature_voice_undo",
        "Son sesli de\u011fi\u015fikli\u011fi geri alma",
        "Son sesli alan de\u011fi\u015fikli\u011fini k\u0131sa s\u00fcre i\u00e7inde geri almay\u0131 sa\u011flar.",
        True,
    ),
    (
        "voice_feature_screen_accessibility",
        "Ekran okuma ve eri\u015filebilirlik komutlar\u0131",
        "Ekran\u0131 ve etkin alan\u0131 okuma, odak ta\u015f\u0131ma ve dikte yard\u0131mlar\u0131n\u0131 a\u00e7ar.",
        True,
    ),
    (
        "voice_feature_critical_confirmation",
        "Kritik i\u015flemlerde sesli onay",
        "Kapal\u0131yken sesle kritik i\u015flem yap\u0131lamaz. Kaydetme, silme ve \u00f6deme onay\u0131 zorunludur.",
        True,
    ),
)


def voice_feature_enabled(db, key, default=True):
    """Read a feature switch, treating malformed values as the safe default."""
    try:
        raw = db.get_setting(key, "1" if default else "0")
    except Exception:
        return bool(default)
    value = str(raw).strip().lower()
    if value in {"0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    return bool(default)


class VoiceFeatureSettingsDialog:
    """Factory namespace kept separate from the integration page widget."""

    @staticmethod
    def create(parent, db):
        from PyQt6.QtCore import Qt
        from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
        from src.ui.widgets.animated_toggle import AnimatedToggle
        from src.ui.widgets.modern_dialog import ModernDialog
        from src.utils.theme_colors import theme_qss

        class _Dialog(ModernDialog):
            def __init__(self):
                super().__init__(
                    "Sesli Asistan \u00d6zellikleri",
                    parent,
                    width=680,
                    height=620,
                )
                self.setModal(True)
                self._toggles = {}
                intro = QLabel(
                    "Sesli asistan\u0131 kullan\u0131m ihtiyac\u0131n\u0131za g\u00f6re yap\u0131land\u0131r\u0131n. "
                    "De\u011fi\u015fiklikler Kaydet d\u00fc\u011fmesine bas\u0131nca uygulan\u0131r."
                )
                intro.setWordWrap(True)
                intro.setStyleSheet(theme_qss("color: @text_muted; padding: 2px 0 8px 0;"))
                self.add_widget(intro)

                for key, title, detail, default in VOICE_ASSISTANT_FEATURES:
                    row = QFrame()
                    row.setObjectName("VoiceFeatureSettingRow")
                    row.setStyleSheet(theme_qss(
                        "QFrame#VoiceFeatureSettingRow { background: @surface_alt; "
                        "border: 1px solid @border; border-radius: 8px; }"
                    ))
                    line = QHBoxLayout(row)
                    line.setContentsMargins(14, 9, 12, 9)
                    text_column = QVBoxLayout()
                    text_column.setSpacing(3)
                    title_label = QLabel(title)
                    title_label.setStyleSheet(theme_qss("color: @text; font-weight: 700; border: none;"))
                    detail_label = QLabel(detail)
                    detail_label.setWordWrap(True)
                    detail_label.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
                    text_column.addWidget(title_label)
                    text_column.addWidget(detail_label)
                    line.addLayout(text_column, 1)
                    toggle = AnimatedToggle(row)
                    toggle.setAccessibleName(title)
                    toggle.setChecked(voice_feature_enabled(db, key, default))
                    self._toggles[key] = toggle
                    line.addWidget(toggle, 0, Qt.AlignmentFlag.AlignVCenter)
                    self.add_widget(row)

                safety = QLabel(
                    "G\u00fcvenlik: Sesle kritik kaydetme, silme ve \u00f6deme i\u015flemleri "
                    "her durumda ayr\u0131 onay ister."
                )
                safety.setWordWrap(True)
                safety.setStyleSheet(theme_qss("color: @warning; padding: 4px 0;"))
                self.add_widget(safety)
                self.error_label = QLabel()
                self.error_label.setWordWrap(True)
                self.error_label.setStyleSheet(theme_qss("color: @danger;"))
                self.add_widget(self.error_label)
                self.add_button("Vazge\u00e7", "secondary", self.reject)
                self.add_button("Kaydet", "primary", self._save)

            def _save(self):
                try:
                    for key, toggle in self._toggles.items():
                        db.set_setting(key, "1" if toggle.isChecked() else "0")
                except Exception:
                    self.error_label.setText(
                        "Ayarlar kaydedilemedi. Veritabani baglantisini kontrol edip yeniden deneyin."
                    )
                    return
                self.accept()

        return _Dialog()
