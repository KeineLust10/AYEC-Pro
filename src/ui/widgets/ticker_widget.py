# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QLabel, QFrame
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint
from PyQt6.QtWidgets import QApplication

from src.utils.theme_colors import theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.system_config import SystemConfig


class TickerWidget(QFrame):
    """
    Kayan yazı (marquee) widget'ı.
    ÖNEMLI: Label layout'a eklenmez - serbest child widget olarak bırakılır.
    QHBoxLayout label'ın pos'unu her frame sıfırlarsa animation çalışmaz.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db        = db
        self.animation = None
        self.setFixedHeight(35)
        self.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border-top: 1px solid @border;
                border-bottom: 1px solid @border;
            }
        """))

        # Label - layout'a EKLEME, serbest bırak ki animation.pos çalışsın
        self.lbl_text = QLabel(self)
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.lbl_text.setStyleSheet(theme_qss("""
            QLabel {
                color: @warning;
                font-weight: 700;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """))
        self.lbl_text.move(0, 0)
        self.apply_theme_styles()

        # 5 dakikada bir içerik yenile
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.update_content)
        self.refresh_timer.start(300_000)

        # Widget gösterilmeden önce width() = 0 olabilir; 150ms sonra başlat
        QTimer.singleShot(150, self.update_content)

    def _is_classic_appearance(self):
        app = QApplication.instance()
        return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

    def refresh_theme(self):
        self.apply_theme_styles()

    def apply_theme_styles(self):
        self.setProperty("skipThemeTransform", False)
        self.lbl_text.setProperty("skipThemeTransform", False)
        self.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border-top: 1px solid @border;
                border-bottom: 1px solid @border;
            }
        """))
        self.lbl_text.setStyleSheet(theme_qss("""
            QLabel {
                color: @text;
                font-family: Segoe UI;
                font-weight: bold;
                font-size: 12px;
                border: none;
                background-color: transparent;
                letter-spacing: 0.25px;
            }
        """))

    # Content
    def update_content(self):
        if SystemConfig.get_current_sector(self.db) == "otomotiv":
            default_text = (
                "AYEC Pro Otomotiv Servis Y\u00f6netimi v2026.1  |  "
                "H\u0131zl\u0131 Kay\u0131t: F5  |  Ara\u00e7 Bul: Ctrl+F"
            )
            user_text = str(self.db.get_setting("ticker_text", "") or "")
            if not user_text or user_text.startswith("AYEC Pro Teknik Servis"):
                user_text = default_text
            features = [
                "BAKIM PANEL\u0130: \u0130\u015f emrini a\u00e7arak ara\u00e7 bak\u0131m detaylar\u0131n\u0131 y\u00f6netin.",
                "HIZLI KAYIT: F5 ile yeni ara\u00e7 i\u015f emri olu\u015fturun.",
                "YEDEKLEME: Veri g\u00fcvenli\u011fi i\u00e7in d\u00fczenli yedek al\u0131n.",
                "FINANS Y\u00d6NET\u0130M\u0130: Gelir-gider dengesini Finans sayfas\u0131ndan izleyin.",
            ]
            if self.db.get_setting("show_feature_info", "1") == "1":
                user_text += "  |  " + "  |  ".join(features)
            self.lbl_text.setText(user_text + "          ")
            self.lbl_text.adjustSize()
            self.lbl_text.setFixedHeight(self.height())
            self.start_animation()
            return
        default_text = (
            "AYEC Pro Teknik Servis Yönetimi v2026.1  |  "
            "Hızlı Kayıt: F5  |  Ürün Bul: Ctrl+F"
        )
        user_text = self.db.get_setting("ticker_text", default_text)

        features = [
            "TEKNİSYEN PANELİ: Listeye sağ tıklayıp 'Teknisyen Paneli' ile detaylı onarım yapabilirsiniz.",
            "HIZLI SATIŞ: F8 ile anında satış ekranına erişin.",
            "YEDEKLEME: Veri güvenliği için düzenli yedek almayı unutmayın.",
            "AKILLI ARAMA: Hem sistemde hem Google üzerinde teknik doküman arayabilirsiniz.",
            "FİNANS YÖNETİMİ: Gelir-gider dengenizi Finans sayfasından takip edin.",
        ]

        show_info = self.db.get_setting("show_feature_info", "1") == "1"
        final_text = user_text
        if show_info:
            final_text += "  |  " + "  |  ".join(features)

        # Sona boşluk ekle (döngü arasında nefes aldır)
        self.lbl_text.setText(final_text + "          ")
        self.lbl_text.adjustSize()
        self.lbl_text.setFixedHeight(self.height())
        self.start_animation()

    # Animation
    def start_animation(self):
        if self.animation:
            self.animation.stop()
            self.animation = None

        widget_width = self.width()
        text_width   = self.lbl_text.width()

        # Widget henüz gösterilmediyse veya metin sığıyorsa animasyon yok
        if widget_width <= 0 or text_width <= 0:
            return
        if text_width <= widget_width:
            self.lbl_text.move(0, 0)
            return

        self.animation = QPropertyAnimation(self.lbl_text, b"pos")
        self.animation.setDuration(int(text_width * 14))   # px başına ~14ms
        self.animation.setStartValue(QPoint(widget_width, 0))
        self.animation.setEndValue(QPoint(-text_width, 0))
        self.animation.setLoopCount(-1)                    # sonsuz döngü
        self.animation.start()

    # Events
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.lbl_text.setFixedHeight(self.height())
        self.start_animation()
