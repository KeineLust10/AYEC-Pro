# -*- coding: utf-8 -*-

"""
Proforma Guide Widget
Proforma PDF Düzenleyici - Nasıl Kullanılır Kılavuzu
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QFrame, QScrollArea, QHBoxLayout)
from PyQt6.QtGui import QFont, QAction, QPainter, QPen, QColor, QPainterPath, QBrush
from PyQt6.QtCore import Qt, QSize, QRectF, QTimer, QPointF

from src.utils.theme_colors import theme_qss


class _StepAnimCanvas(QWidget):
    """QTimer tabanlı GIF-benzeri mini animasyon — her adım için ayrı çizim"""

    def __init__(self, step: int, parent=None):
        super().__init__(parent)
        self.step = step
        self.frame = 0
        self.N = 90          # döngü frame sayısı
        self.setFixedSize(218, 138)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        t = QTimer(self)
        t.setInterval(40)        # 25 fps
        t.timeout.connect(self._tick)
        t.start()

    def _tick(self):
        self.frame = (self.frame + 1) % self.N
        self.update()

    @staticmethod
    def _ease(t: float) -> float:
        """Ease in-out cubic"""
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Arka plan
        p.fillRect(self.rect(), QColor("#141c2b"))
        draw = {1: self._draw_step1, 2: self._draw_step2,
                3: self._draw_step3, 4: self._draw_step4,
                5: self._draw_step5}.get(self.step)
        if draw:
            draw(p)
        p.end()

    # ── Adım 1: Dosya Seç ────────────────────────────────────────
    def _draw_step1(self, p):
        t = self.frame / self.N
        W, H = self.width(), self.height()

        # PDF ikonu (sol)
        p.setPen(QPen(QColor("#e74c3c"), 2))
        p.setBrush(QColor("#c0392b"))
        p.drawRoundedRect(18, H//2 - 35, 50, 65, 5, 5)
        p.setBrush(QColor("#e74c3c"))
        p.drawPolygon([QPointF(48, H//2 - 35), QPointF(68, H//2 - 15),
                       QPointF(48, H//2 - 15)])
        p.setPen(QPen(QColor("white"), 1))
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.drawText(24, H//2 + 2,  "PDF")
        p.setFont(QFont("Segoe UI", 6))
        p.drawText(24, H//2 + 14, "Şablon")

        # Animasyonlu ok
        prog = self._ease((t * 1.5) % 1.0)
        arrow_x = 82 + int(prog * 28)
        p.setPen(QPen(QColor("#3498db"), 2))
        p.drawLine(82, H//2, arrow_x, H//2)
        p.drawLine(arrow_x, H//2, arrow_x - 7, H//2 - 5)
        p.drawLine(arrow_x, H//2, arrow_x - 7, H//2 + 5)

        # Dosya Seç butonu (sağ) — nabız etkisi
        pulse = abs(self._ease(t * 2 % 1.0) * 2 - 1)
        a = int(160 + 95 * pulse)
        p.setPen(QPen(QColor(41, 128, 185, a), 2))
        p.setBrush(QColor(52, 152, 219, a // 4))
        p.drawRoundedRect(122, H//2 - 16, 84, 30, 7, 7)
        p.setPen(QPen(QColor("white")))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(128, H//2 + 3, "📂 Dosya Seç")

    # ── Adım 2: Tasarımcıyı Aç ───────────────────────────────────
    def _draw_step2(self, p):
        t = self.frame / self.N
        W, H = self.width(), self.height()

        # Pencere çerçevesi
        p.setPen(QPen(QColor("#2c3e50"), 2))
        p.setBrush(QColor("#1a2535"))
        p.drawRoundedRect(8, 8, W - 16, H - 16, 8, 8)
        p.setBrush(QColor("#2c3e50"))
        p.drawRoundedRect(8, 8, W - 16, 20, 8, 8)
        p.setPen(QPen(QColor("#94a3b8")))
        p.setFont(QFont("Segoe UI", 6))
        p.drawText(16, 22, "Firma Ayarları › Proforma PDF Düzenleyici")

        # Kılavuz adımı etiketi
        p.setPen(QPen(QColor("#64748b")))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(16, 45, "Şablon PDF seçildi ✓")
        p.drawText(16, 58, "Tasarımcıyı açın ↓")

        # Nabız eden buton
        pulse = abs(self._ease(t * 2 % 1.0) * 2 - 1)
        r = int(52 + 30 * pulse)
        g = int(152 + 30 * pulse)
        btn_c = QColor(r, g, 219)
        p.setPen(QPen(btn_c.darker(110), 2))
        p.setBrush(QColor(btn_c.red(), btn_c.green(), btn_c.blue(), 200))
        p.drawRoundedRect(28, H//2 + 10, 130, 28, 7, 7)
        p.setPen(QPen(QColor("white")))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(34, H//2 + 29, "🎨 Şablon Tasarımcısı")

        # Fare imleci (tıklamak için yaklaşıyor)
        if t > 0.45:
            prog = self._ease((t - 0.45) / 0.45)
            cx = int(W - 30 - prog * (W - 30 - 93))
            cy = int(H//2 - 14 + prog * (H//2 + 24 - (H//2 - 14)))
            self._draw_cursor(p, cx, cy)

    # ── Adım 3: Alan Seç ─────────────────────────────────────────
    def _draw_step3(self, p):
        t = self.frame / self.N
        W, H = self.width(), self.height()

        fields = ["Firma Adı", "Müşteri Adı", "Tarih", "Ürün Tablosu", "Toplamlar"]
        colors = [QColor(0, 102, 204), QColor(46, 204, 113),
                  QColor(241, 196, 15), QColor(155, 89, 182), QColor(231, 76, 60)]

        active = int(t * len(fields)) % len(fields)

        # Sol panel
        p.setPen(QPen(QColor("#2c3e50"), 1))
        p.setBrush(QColor("#1e2d3d"))
        p.drawRoundedRect(8, 8, 108, H - 16, 7, 7)
        p.setPen(QPen(QColor("#64748b")))
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.drawText(14, 26, "Alan Seçin:")

        for i, (name, color) in enumerate(zip(fields, colors)):
            y = 32 + i * 20
            if i == active:
                p.setBrush(color)
                p.setPen(QPen(color.lighter(140), 2))
            else:
                p.setBrush(QColor("#243044"))
                p.setPen(QPen(QColor("#34495e"), 1))
            p.drawRoundedRect(12, y, 96, 16, 4, 4)
            p.setPen(QPen(QColor("white")))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(16, y + 11, name)

        # Ok → sağa
        ay = 32 + active * 20 + 8
        p.setPen(QPen(QColor("#3498db"), 2))
        p.drawLine(120, ay, 140, ay)
        p.drawLine(140, ay, 133, ay - 5)
        p.drawLine(140, ay, 133, ay + 5)

        # Sağda seçili alan bilgisi
        if active < len(colors):
            c = colors[active]
            p.setPen(QPen(c, 1))
            p.setBrush(QColor(c.red(), c.green(), c.blue(), 40))
            p.drawRoundedRect(145, ay - 10, 62, 20, 4, 4)
            p.setPen(QPen(c))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(149, ay + 3, "Aktif ✓")

    # ── Adım 4: Canvas'a Çiz ─────────────────────────────────────
    def _draw_step4(self, p):
        t = self.frame / self.N
        W, H = self.width(), self.height()

        # PDF arka plan (beyaz kağıt)
        p.setBrush(QColor("#f8fafc"))
        p.setPen(QPen(QColor("#cbd5e1"), 1))
        p.drawRect(8, 8, W - 16, H - 16)

        # Yatay çizgiler (metin simgesi)
        p.setPen(QPen(QColor("#e2e8f0"), 1))
        for row in range(7):
            y = 22 + row * 16
            p.drawLine(16, y, W - 16, y)

        # Faz 1 (0→0.35): imleç hareket ediyor
        # Faz 2 (0.35→0.75): sürükleyerek çiziyor
        # Faz 3 (0.75→1.0): tamamlanmış dikdörtgen + etiket

        PHASE2, PHASE3 = 0.35, 0.75
        bx, by = 28, 25   # çizim başlangıcı

        if t < PHASE2:
            prog = self._ease(t / PHASE2)
            cx = int(W - 20 - prog * (W - 20 - bx))
            cy = int(H - 20 - prog * (H - 20 - by))
            rect = None
        elif t < PHASE3:
            prog = self._ease((t - PHASE2) / (PHASE3 - PHASE2))
            cx = int(bx + prog * 140)
            cy = int(by + prog * 70)
            rect = QRectF(bx, by, cx - bx, cy - by)
        else:
            cx, cy = bx + 140, by + 70
            rect = QRectF(bx, by, 140, 70)

        if rect and rect.width() > 4 and rect.height() > 4:
            p.setPen(QPen(QColor(0, 102, 204, 200), 2, Qt.PenStyle.DashLine))
            p.setBrush(QColor(0, 102, 204, 45))
            p.drawRect(rect)

        if t >= PHASE3:
            p.setPen(QPen(QColor(0, 102, 204)))
            p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
            p.drawText(bx + 4, by + 14, "Firma Adı")

        self._draw_cursor(p, cx, cy)

    # ── Adım 5: Kaydet ───────────────────────────────────────────
    def _draw_step5(self, p):
        t = self.frame / self.N
        W, H = self.width(), self.height()

        # Küçük canvas önizlemesi
        p.setBrush(QColor("#f8fafc"))
        p.setPen(QPen(QColor("#cbd5e1"), 1))
        p.drawRoundedRect(10, 10, 130, 85, 5, 5)

        # Alan dikdörtgenleri
        areas = [
            (QRectF(16, 16, 118, 16), QColor(0, 102, 204), "Firma Adı"),
            (QRectF(16, 36, 100, 16), QColor(46, 204, 113), "Müşteri"),
            (QRectF(16, 56, 80, 14), QColor(241, 196, 15), "Tarih"),
            (QRectF(16, 74, 118, 14), QColor(155, 89, 182), "Ürün Tablosu"),
        ]
        for rect, c, lbl in areas:
            p.setPen(QPen(c, 1, Qt.PenStyle.DashLine))
            p.setBrush(QColor(c.red(), c.green(), c.blue(), 35))
            p.drawRect(rect)
            p.setPen(QPen(c))
            p.setFont(QFont("Segoe UI", 6))
            p.drawText(int(rect.x()) + 2, int(rect.y()) + 11, lbl)

        # Kaydet butonu
        saved = t > 0.5
        bc = QColor("#27ae60") if saved else QColor("#3498db")
        p.setPen(QPen(bc.darker(120), 2))
        p.setBrush(bc)
        p.drawRoundedRect(148, 55, 60, 26, 7, 7)
        p.setPen(QPen(QColor("white")))
        p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        p.drawText(154, 72, "💾 Kaydet")

        # Fare → Kaydet'e yaklaşıyor
        if not saved:
            prog = self._ease(t / 0.5)
            cx = int(W - 15 - prog * (W - 15 - 178))
            cy = int(H - 12 - prog * (H - 12 - 68))
            self._draw_cursor(p, cx, cy)

        # Kaydedildi onayı
        if t > 0.55:
            alpha = int(min(1.0, (t - 0.55) / 0.2) * 255)
            p.setPen(QPen(QColor(46, 204, 113, alpha)))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(148, 100, "✅ Kaydedildi!")

    # ── Yardımcı: fare imleci çiz ────────────────────────────────
    @staticmethod
    def _draw_cursor(p: QPainter, cx: int, cy: int):
        path = QPainterPath()
        path.moveTo(cx, cy)
        path.lineTo(cx, cy + 13)
        path.lineTo(cx + 3, cy + 9)
        path.lineTo(cx + 6, cy + 15)
        path.lineTo(cx + 8, cy + 14)
        path.lineTo(cx + 5, cy + 8)
        path.lineTo(cx + 9, cy + 8)
        path.closeSubpath()
        p.setPen(QPen(QColor("#1e293b"), 1))
        p.setBrush(QColor("white"))
        p.drawPath(path)


class ProformaGuideWidget(QFrame):
    """Proforma PDF Düzenleyici — 'Nasıl Kullanılır?' kılavuz bölümü"""

    STEPS = [
        (1, "1️⃣  PDF Şablon Seçin",
         "Antetli kağıt veya hazır\nteklif PDF'inizi\n'Dosya Seç' ile yükleyin."),
        (2, "2️⃣  Tasarımcıyı Açın",
         "'Şablon Tasarımcısı'\nbutonuna tıklayarak\nyerleştirme ekranını açın."),
        (3, "3️⃣  Alan Seçin",
         "Sol panelden Firma Adı,\nMüşteri Adı, Tarih vb.\nbir alan seçin."),
        (4, "4️⃣  Canvas'a Çizin",
         "PDF önizlemesi üzerinde\nfareyle sürükleyerek\nalanın konumunu çizin."),
        (5, "5️⃣  Kaydedin",
         "'Kaydet' butonuna basın.\nKoordinatlar saklanır,\nPDF doğru yere yazar."),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ProformaGuide")
        self._expanded = False
        self._setup_ui()
        self.setStyleSheet(theme_qss("""
            QFrame#ProformaGuide {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 10px;
            }
        """))

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Aç/Kapat başlık butonu
        self._toggle_btn = QPushButton("  📖  Nasıl Kullanılır?   ▼")
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle_btn.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent;
                color: @accent;
                border: none;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: bold;
                text-align: left;
                border-radius: 10px;
            }
            QPushButton:hover { background: @surface; }
        """))
        self._toggle_btn.clicked.connect(self._toggle)
        outer.addWidget(self._toggle_btn)

        # ── Gizlenebilir içerik
        self._content = QFrame()
        self._content.setObjectName("GuideContent")
        self._content.setStyleSheet("QFrame#GuideContent { background: transparent; }")
        self._content.setMaximumHeight(0)
        content_v = QVBoxLayout(self._content)
        content_v.setContentsMargins(10, 0, 10, 12)
        content_v.setSpacing(6)

        # Ayırıcı çizgi
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(theme_qss("color: @border;"))
        content_v.addWidget(sep)

        # Yatay kaydırılabilir adım kartları
        h_scroll = QScrollArea()
        h_scroll.setFrameShape(QFrame.Shape.NoFrame)
        h_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        h_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        h_scroll.setFixedHeight(272)
        h_scroll.setWidgetResizable(True)
        h_scroll.setStyleSheet("QScrollArea { background: transparent; }")

        steps_w = QWidget()
        steps_w.setStyleSheet("background: transparent;")
        steps_h = QHBoxLayout(steps_w)
        steps_h.setContentsMargins(0, 6, 0, 6)
        steps_h.setSpacing(12)

        for step_num, title, desc in self.STEPS:
            steps_h.addWidget(self._make_card(step_num, title, desc))
        steps_h.addStretch()

        h_scroll.setWidget(steps_w)
        content_v.addWidget(h_scroll)
        outer.addWidget(self._content)

    def _make_card(self, step_num: int, title: str, desc: str) -> QFrame:
        card = QFrame()
        card.setFixedWidth(248)
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: @surface;
                border: 1px solid @border;
                border-radius: 10px;
            }
            QLabel { background: transparent; }
        """))
        lay = QVBoxLayout(card)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(6)

        # Animasyon canvas
        anim = _StepAnimCanvas(step_num)
        anim.setStyleSheet("border-radius: 8px;")
        lay.addWidget(anim, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Başlık
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: bold; color: @accent;"
        ))
        lbl_title.setWordWrap(True)
        lay.addWidget(lbl_title)

        # Açıklama
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(theme_qss(
            "font-size: 11px; color: @text_muted; line-height: 18px;"
        ))
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_desc)

        return card

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._content.setMaximumHeight(99999)
            self._toggle_btn.setText("  📖  Nasıl Kullanılır?   ▲")
        else:
            self._content.setMaximumHeight(0)
            self._toggle_btn.setText("  📖  Nasıl Kullanılır?   ▼")
