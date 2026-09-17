# -*- coding: utf-8 -*-
"""
loading_overlay.py
------------------
Modern animasyonlu loading overlay.
Spinner yerine firma adı harfleri dalga şeklinde sırayla parlayıp solar.
"""

import os
import math

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QLinearGradient, QPixmap, QFontMetrics
)
from PyQt6.QtWidgets import QWidget, QApplication

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "assets")
_LOGO_PATH  = os.path.normpath(os.path.join(_ASSETS_DIR, "ayec_logo.png"))

# Animasyon turu (ms): her kaç ms'de bir tick
_TICK_MS = 30


# ─────────────────────────────────────────────────────────────────────────────
# Harf dalga animasyonu widget'ı
# ─────────────────────────────────────────────────────────────────────────────
class _LetterWave(QWidget):
    """
    Firma adının harflerini dalga şeklinde parlatan widget.
    Her harf sinüs eğrisiyle opaklık + dikey titreşim animasyonu yapar.
    """

    def __init__(self, parent=None, firm_name: str = "AYEC Pro", size: int = 80):
        super().__init__(parent)
        self._firm_name  = firm_name
        self._size       = size          # toplam genişlik
        self._phase      = 0.0           # animasyon fazı (radyan)
        self._timer      = QTimer(self)
        self._timer.timeout.connect(self._tick)

        # Firma logosu (küçük, sol üst veya ortada — opsiyonel)
        self._logo: QPixmap | None = None
        self._logo_size = 32
        self._load_logo(_LOGO_PATH)

        # Boyutu içeriğe göre ayarla
        self._font_big   = QFont()
        self._font_big.setPointSize(22)
        self._font_big.setWeight(QFont.Weight.Bold)
        self._font_big.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)

        self._font_sub   = QFont()
        self._font_sub.setPointSize(9)
        self._font_sub.setWeight(QFont.Weight.Normal)
        self._font_sub.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)

        self.setFixedSize(320, 120)

    # ── logo yükleme ──────────────────────────────────────────────────────────
    def _load_logo(self, path: str):
        if path and os.path.exists(path):
            px = QPixmap(path)
            if not px.isNull():
                self._logo = px.scaled(
                    self._logo_size, self._logo_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                return
        self._logo = None

    def set_logo(self, path: str):
        self._load_logo(path if path else _LOGO_PATH)
        self.update()

    def set_firm_name(self, name: str):
        self._firm_name = name
        self.update()

    # ── timer ─────────────────────────────────────────────────────────────────
    def start(self): self._timer.start(_TICK_MS)
    def stop(self):  self._timer.stop()

    def _tick(self):
        self._phase += 0.12   # dalga hızı
        self.update()

    # ── paint ─────────────────────────────────────────────────────────────────
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w, h = self.width(), self.height()

        # Firma adını büyük/küçük kısımlara böl
        # "AYEC" büyük, "Pro" farklı renkli küçük yazı
        parts = self._split_name(self._firm_name)
        # parts: list of (char, is_main)

        fm_big = QFontMetrics(self._font_big)
        fm_sub = QFontMetrics(self._font_sub)

        # Toplam genişliği hesapla (her harfin genişliği)
        char_widths = []
        for ch, is_main in parts:
            fm = fm_big if is_main else fm_sub
            char_widths.append(fm.horizontalAdvance(ch))

        total_w = sum(char_widths) + 4 * (len(parts) - 1)   # 4px harf arası

        # Başlangıç X — ortaya hizalı, logo varsa sağa kaydır
        logo_offset = (self._logo_size + 8) if self._logo else 0
        start_x = (w - total_w - logo_offset) // 2 + logo_offset
        base_y  = h // 2 + 10

        # Logo çiz (sol orta)
        if self._logo:
            lx = start_x - self._logo_size - 10
            ly = base_y - self._logo_size // 2 - 6
            p.drawPixmap(lx, ly, self._logo)

        # Her harfi ayrı ayrı boya
        x_cursor = start_x
        for i, (ch, is_main) in enumerate(parts):
            cw = char_widths[i]

            # Sinüs dalgası: i harfi için faz kaydırması
            wave = math.sin(self._phase - i * 0.45)        # -1 … +1
            alpha_f = 0.45 + 0.55 * (wave * 0.5 + 0.5)     # 0.45 … 1.0
            dy = -int(wave * 5)                              # ±5 px dikey

            if is_main:
                # Gradient renk: mor → cyan
                t = i / max(len(parts) - 1, 1)
                r = int(156 + (64  - 156) * t)
                g = int(100 + (196 - 100) * t)
                b = int(255 + (255 - 255) * t)
                color = QColor(r, g, b, int(255 * alpha_f))
                p.setFont(self._font_big)
                char_y = base_y + dy
            else:
                # "Pro" gibi suffix — daha soluk, küçük, altta
                color = QColor(180, 180, 220, int(200 * alpha_f))
                p.setFont(self._font_sub)
                char_y = base_y + 8 + dy   # biraz aşağı

            p.setPen(color)

            # Harf gölgesi (parlak halo etkisi)
            if is_main:
                glow_alpha = int(80 * alpha_f)
                glow_color = QColor(124, 77, 255, glow_alpha)
                p.setPen(glow_color)
                p.drawText(x_cursor + 1, char_y + 1, ch)
                p.setPen(color)

            p.drawText(x_cursor, char_y, ch)
            x_cursor += cw + 4

        # Alt çizgi — ince gradient
        line_y  = base_y + 18
        grad = QLinearGradient(0, line_y, w, line_y)
        grad.setColorAt(0,   QColor(124, 77, 255, 0))
        grad.setColorAt(0.3, QColor(124, 77, 255, 120))
        grad.setColorAt(0.7, QColor(64,  196, 255, 120))
        grad.setColorAt(1,   QColor(64,  196, 255, 0))
        p.setPen(QPen(grad, 1.2))
        p.drawLine(start_x - logo_offset, line_y, start_x + total_w, line_y)

        p.end()

    @staticmethod
    def _split_name(name: str):
        """
        Firma adını (char, is_main) listesine dönüştür.
        Küçük harf kelimeler (pro, lite, v2...) is_main=False olur.
        """
        result = []
        for word in name.split():
            is_main = word[0].isupper() and word.upper() == word or word.isupper()
            for ch in word:
                result.append((ch, is_main))
            result.append((" ", True))   # kelime arası boşluk
        # sona eklenen boşluğu kaldır
        if result and result[-1][0] == " ":
            result.pop()
        # ikinci kelime (Pro) küçük harfli olduğunda is_main=False işaretle
        # Yeniden tarama: ilk kelime tamamen büyük → main, sonrakiler → not main
        words = name.split()
        if len(words) >= 2:
            result2 = []
            for word in words:
                is_main = word.isupper()
                for ch in word:
                    result2.append((ch, is_main))
                result2.append((" ", False))
            if result2 and result2[-1][0] == " ":
                result2.pop()
            return result2
        return result


# ─────────────────────────────────────────────────────────────────────────────
# Ana Overlay
# ─────────────────────────────────────────────────────────────────────────────
class LoadingOverlay(QWidget):
    """
    Ana pencereye göre tam-ekran overlay.

    Kullanım:
        self._overlay = LoadingOverlay(self)
        self._overlay.show_overlay("Analiz ediliyor...")
        self._overlay.hide_overlay()
    """

    def __init__(self, parent=None, text: str = "Yükleniyor...",
                 firm_name: str = "AYEC Pro"):
        super().__init__(parent)
        self._text       = text
        self._firm_name  = firm_name
        self._alpha      = 0
        self._target_alpha = 0
        self._on_done    = None

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_step)

        self._wave = _LetterWave(self, firm_name=firm_name)
        self._wave.hide()

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.hide()

    # ── public API ────────────────────────────────────────────────────────────

    def show_overlay(self, text: str = None):
        if text:
            self._text = text
        self._reposition()
        self._wave.start()
        self._wave.show()
        self.show()
        self.raise_()
        self._animate_to(220)

    def hide_overlay(self):
        self._animate_to(0, on_done=self._do_hide)

    def set_text(self, text: str):
        self._text = text
        self.update()

    def set_company_logo(self, logo_path: str):
        """Firma logosu değiştiğinde wave widget'ını güncelle."""
        self._wave.set_logo(logo_path)

    def set_firm_name(self, name: str):
        """Firma adını güncelle (veritabanından okunup set edilebilir)."""
        self._firm_name = name
        self._wave.set_firm_name(name)

    # ── konumlandırma ─────────────────────────────────────────────────────────

    def _reposition(self):
        top = self.parent()
        while top is not None and top.parent() is not None:
            top = top.parent()
        if top is None:
            top = QApplication.activeWindow()
        if top and top is not self:
            geo = top.rect()
            if self.parent() is not top:
                self.setParent(top)
            self.setGeometry(geo)
        elif self.parent():
            p = self.parent()
            self.setGeometry(0, 0, p.width(), p.height())
        self.raise_()

    # ── animasyon ─────────────────────────────────────────────────────────────

    def _animate_to(self, target: int, on_done=None):
        self._target_alpha = target
        self._on_done = on_done
        if not self._anim_timer.isActive():
            self._anim_timer.start(12)

    def _anim_step(self):
        diff = self._target_alpha - self._alpha
        step = max(8, abs(diff) // 3)
        if abs(diff) <= step:
            self._alpha = self._target_alpha
            self._anim_timer.stop()
            if self._on_done:
                self._on_done()
                self._on_done = None
        else:
            self._alpha += step if diff > 0 else -step
        self.update()

    def _do_hide(self):
        self._wave.stop()
        self._wave.hide()
        self.hide()

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if self._alpha == 0:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # 1. Arka plan karartma
        bg = QColor(8, 8, 20, self._alpha)
        p.fillRect(0, 0, w, h, bg)

        # 2. Kart boyutu ve konumu
        card_w, card_h = 340, 180
        cx = (w - card_w) // 2
        cy = (h - card_h) // 2

        # 3. Kart gölgesi
        for i in range(20, 0, -1):
            shadow = QColor(0, 0, 0, int(self._alpha * 0.35 * i / 20))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(shadow)
            p.drawRoundedRect(cx - i, cy - i + 5,
                              card_w + 2*i, card_h + 2*i,
                              24 + i, 24 + i)

        # 4. Kart arka planı
        card_bg = QColor(14, 14, 30)
        card_bg.setAlpha(min(255, int(self._alpha * 1.15)))
        p.setBrush(card_bg)

        border_color = QColor(124, 77, 255, min(255, int(self._alpha * 0.55)))
        p.setPen(QPen(border_color, 1.2))
        p.drawRoundedRect(cx, cy, card_w, card_h, 20, 20)

        # 5. Kart üst dekorasyon çizgisi
        grad = QLinearGradient(cx, cy, cx + card_w, cy)
        grad.setColorAt(0,   QColor(124, 77,  255, 0))
        grad.setColorAt(0.3, QColor(124, 77,  255, min(200, self._alpha)))
        grad.setColorAt(0.7, QColor(64,  196, 255, min(200, self._alpha)))
        grad.setColorAt(1,   QColor(64,  196, 255, 0))
        p.setPen(QPen(grad, 2))
        p.drawLine(cx + 24, cy + 1, cx + card_w - 24, cy + 1)

        # 6. Alt açıklama metni
        text_alpha = min(255, int(self._alpha * 1.2))
        text_color = QColor(180, 180, 220, text_alpha)
        p.setPen(text_color)
        font = QFont()
        font.setPointSize(9)
        font.setWeight(QFont.Weight.Normal)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(font)
        p.drawText(cx, cy + card_h - 40, card_w, 28,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                   self._text)

        # 7. Wave widget'ını kart içinde ortaya konumlandır
        wx = cx + (card_w - self._wave.width())  // 2
        wy = cy + 22
        self._wave.move(wx, wy)

        p.end()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        pp = self.parent()
        if pp and isinstance(pp, QWidget):
            self.setGeometry(0, 0, pp.width(), pp.height())
        self.update()
