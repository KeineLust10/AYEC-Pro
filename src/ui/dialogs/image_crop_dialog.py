# -*- coding: utf-8 -*-
"""
image_crop_dialog.py
--------------------
WhatsApp / modern fotoğraf kırpma dialogo.

Özellikler:
  • Tam saydam karartma overlay (seçim dışı bölge)
  • 8 köşe + kenar handle (sürüklenebilir)
  • Seçim alanını sürükleyerek taşıma
  • Aspect-ratio kilidi (Shift tuşu ile)
  • Zoom: mouse wheel ile
  • "Kırp" / "Vazgeç" / "Sıfırla" butonları
  • Fade-in animasyonu
"""

from __future__ import annotations

import math
from typing import Optional

from PyQt6.QtCore import (
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    QSizeF,
    Qt,
    QPropertyAnimation,
    QEasingCurve,
    pyqtProperty,
)
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from src.utils.theme_colors import theme_qss


# ─────────────────────────────────────────────────────────────────────────────
# Sabitler
# ─────────────────────────────────────────────────────────────────────────────
HANDLE_SIZE   = 14     # px — handle karesi yarı-kenarı (toplam 2*HANDLE_SIZE)
HANDLE_BORDER = 2
OVERLAY_ALPHA = 160    # 0-255, karartma koyuluğu
MIN_CROP_PX   = 20     # minimum kırpma boyutu (piksel, ekran koordinatında)
ACCENT        = QColor("#7C4DFF")    # mor vurgu
HANDLE_FILL   = QColor("#FFFFFF")
HANDLE_STROKE = QColor("#7C4DFF")
LINE_COLOR    = QColor(255, 255, 255, 180)
GRID_COLOR    = QColor(255, 255, 255, 60)


# ─────────────────────────────────────────────────────────────────────────────
# Yardımcı: hangi handle bölgesi?
# ─────────────────────────────────────────────────────────────────────────────
_HANDLES = [
    "tl", "tc", "tr",
    "ml",        "mr",
    "bl", "bc", "br",
]

_CURSORS = {
    "tl": Qt.CursorShape.SizeFDiagCursor,
    "tr": Qt.CursorShape.SizeBDiagCursor,
    "bl": Qt.CursorShape.SizeBDiagCursor,
    "br": Qt.CursorShape.SizeFDiagCursor,
    "tc": Qt.CursorShape.SizeVerCursor,
    "bc": Qt.CursorShape.SizeVerCursor,
    "ml": Qt.CursorShape.SizeHorCursor,
    "mr": Qt.CursorShape.SizeHorCursor,
    "move": Qt.CursorShape.SizeAllCursor,
}


class CropCanvas(QWidget):
    """Kırpma işleminin çizildiği interaktif canvas."""

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._orig_pixmap = pixmap          # orijinal tam çözünürlüklü
        self._zoom        = 1.0
        self._offset      = QPointF(0, 0)   # canvas içindeki görsel offset
        self._img_rect    = QRectF()        # ekrandaki görsel dikdörtgeni

        # Kırpma dikdörtgeni (görsel piksel koordinatında, float)
        self._crop: Optional[QRectF] = None
        self._aspect_locked = False
        self._aspect_ratio  = 1.0

        # Fare durumu
        self._drag_mode: Optional[str] = None   # handle adı | "move" | "new"
        self._drag_start  = QPointF()
        self._crop_start  = QRectF()
        self._lock_aspect = False

    # ─── public ──────────────────────────────────────────────────────────────

    def get_crop_rect_on_original(self) -> Optional[QRect]:
        """Orijinal piksel koordinatında kırpma rect'i döner."""
        if self._crop is None or self._crop.width() < 1 or self._crop.height() < 1:
            return None
        # Sınır içine al
        ow, oh = self._orig_pixmap.width(), self._orig_pixmap.height()
        r = self._crop.intersected(QRectF(0, 0, ow, oh))
        if r.width() < 4 or r.height() < 4:
            return None
        return QRect(int(r.x()), int(r.y()), int(r.width()), int(r.height()))

    def reset_crop(self):
        self._crop = None
        self.update()

    def fit_image(self):
        """Görüntüyü widget'a sığdır."""
        if self._orig_pixmap.isNull():
            return
        w, h = self.width(), self.height()
        iw, ih = self._orig_pixmap.width(), self._orig_pixmap.height()
        scale = min(w / iw, h / ih, 1.0)
        self._zoom = scale
        disp_w = iw * scale
        disp_h = ih * scale
        ox = (w - disp_w) / 2
        oy = (h - disp_h) / 2
        self._img_rect = QRectF(ox, oy, disp_w, disp_h)

    # ─── koordinat dönüşümleri ────────────────────────────────────────────────

    def _screen_to_img(self, sp: QPointF) -> QPointF:
        if self._img_rect.width() == 0:
            return QPointF()
        sx = (sp.x() - self._img_rect.x()) / self._img_rect.width()
        sy = (sp.y() - self._img_rect.y()) / self._img_rect.height()
        return QPointF(sx * self._orig_pixmap.width(), sy * self._orig_pixmap.height())

    def _img_to_screen(self, ip: QPointF) -> QPointF:
        if self._orig_pixmap.width() == 0 or self._img_rect.width() == 0:
            return QPointF()
        sx = self._img_rect.x() + ip.x() / self._orig_pixmap.width() * self._img_rect.width()
        sy = self._img_rect.y() + ip.y() / self._orig_pixmap.height() * self._img_rect.height()
        return QPointF(sx, sy)

    def _crop_to_screen(self) -> Optional[QRectF]:
        if self._crop is None:
            return None
        tl = self._img_to_screen(QPointF(self._crop.left(), self._crop.top()))
        br = self._img_to_screen(QPointF(self._crop.right(), self._crop.bottom()))
        return QRectF(tl, br)

    # ─── handle konumları (ekran koordinatı) ─────────────────────────────────

    def _handle_rects(self) -> dict[str, QRectF]:
        cr = self._crop_to_screen()
        if cr is None:
            return {}
        cx, cy = cr.center().x(), cr.center().y()
        pts = {
            "tl": QPointF(cr.left(),  cr.top()),
            "tc": QPointF(cx,         cr.top()),
            "tr": QPointF(cr.right(), cr.top()),
            "ml": QPointF(cr.left(),  cy),
            "mr": QPointF(cr.right(), cy),
            "bl": QPointF(cr.left(),  cr.bottom()),
            "bc": QPointF(cx,         cr.bottom()),
            "br": QPointF(cr.right(), cr.bottom()),
        }
        hs = HANDLE_SIZE
        return {
            k: QRectF(v.x() - hs, v.y() - hs, hs * 2, hs * 2)
            for k, v in pts.items()
        }

    def _hit_test(self, pos: QPointF) -> Optional[str]:
        for name, r in self._handle_rects().items():
            if r.contains(pos):
                return name
        cr = self._crop_to_screen()
        if cr and cr.contains(pos):
            return "move"
        return None

    # ─── Events ──────────────────────────────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_image()

    def wheelEvent(self, event: QWheelEvent):
        if self._img_rect.width() == 0:
            return
        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else (1 / 1.1)
        center = event.position()

        # Zoom pivot: mouse konumu
        old_w = self._img_rect.width()
        old_h = self._img_rect.height()
        new_w = old_w * factor
        new_h = old_h * factor

        # Orijinal görüntü boyutunun %15 - %600 aralığında tut
        ow, oh = self._orig_pixmap.width(), self._orig_pixmap.height()
        min_w = ow * 0.15
        max_w = ow * 6.0
        new_w = max(min_w, min(max_w, new_w))
        new_h = new_w * (oh / ow)

        # offset: mouse pivot altında sabit kalmalı
        rx = (center.x() - self._img_rect.x()) / old_w
        ry = (center.y() - self._img_rect.y()) / old_h
        new_x = center.x() - rx * new_w
        new_y = center.y() - ry * new_h

        self._img_rect = QRectF(new_x, new_y, new_w, new_h)
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position()
        self._lock_aspect = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        hit = self._hit_test(pos)

        if hit:
            self._drag_mode  = hit
            self._drag_start = pos
            self._crop_start = QRectF(self._crop) if self._crop else QRectF()
        else:
            # Yeni seçim başlat
            self._drag_mode  = "new"
            self._drag_start = pos
            ip = self._screen_to_img(pos)
            self._crop = QRectF(ip, QSizeF(0, 0))
            self._crop_start = QRectF(self._crop)

        self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        if self._drag_mode is None:
            hit = self._hit_test(pos)
            if hit and hit in _CURSORS:
                self.setCursor(_CURSORS[hit])
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return

        delta = pos - self._drag_start
        ow, oh = float(self._orig_pixmap.width()), float(self._orig_pixmap.height())
        iw, ih = self._img_rect.width(), self._img_rect.height()
        if iw == 0 or ih == 0:
            return
        # delta → piksel birimi
        dx = delta.x() / iw * ow
        dy = delta.y() / ih * oh

        mode = self._drag_mode
        cs   = self._crop_start

        if mode == "new":
            ip = self._screen_to_img(pos)
            ip0 = self._screen_to_img(self._drag_start)
            r = QRectF(ip0, ip).normalized()
            r = r.intersected(QRectF(0, 0, ow, oh))
            if r.width() > 0 and r.height() > 0:
                self._crop = r

        elif mode == "move":
            new_x = max(0, min(cs.x() + dx, ow - cs.width()))
            new_y = max(0, min(cs.y() + dy, oh - cs.height()))
            self._crop = QRectF(new_x, new_y, cs.width(), cs.height())

        else:
            # Handle resize
            l, r_coord, t, b = cs.left(), cs.right(), cs.top(), cs.bottom()

            if "l" in mode:
                l = min(cs.right() - MIN_CROP_PX * ow / iw, cs.left() + dx)
                l = max(0, l)
            if "r" in mode:
                r_coord = max(cs.left() + MIN_CROP_PX * ow / iw, cs.right() + dx)
                r_coord = min(ow, r_coord)
            if "t" in mode:
                t = min(cs.bottom() - MIN_CROP_PX * oh / ih, cs.top() + dy)
                t = max(0, t)
            if "b" in mode:
                b = max(cs.top() + MIN_CROP_PX * oh / ih, cs.bottom() + dy)
                b = min(oh, b)

            if self._lock_aspect and cs.width() > 0 and cs.height() > 0:
                aspect = cs.width() / cs.height()
                w_new = r_coord - l
                h_new = b - t
                if "l" in mode or "r" in mode:
                    h_new = w_new / aspect
                    b = t + h_new
                else:
                    w_new = h_new * aspect
                    r_coord = l + w_new

            self._crop = QRectF(l, t, r_coord - l, b - t)

        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_mode = None

    # ─── Paint ───────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. Arka plan
        painter.fillRect(self.rect(), QColor("#1A1A2E"))

        # 2. Görsel
        if not self._orig_pixmap.isNull() and self._img_rect.isValid():
            painter.drawPixmap(self._img_rect.toRect(), self._orig_pixmap)

        # 3. Kırpma seçimi yoksa çık
        cr = self._crop_to_screen()
        if cr is None or cr.width() < 1:
            return

        # 4. Overlay: seçim dışı karartma
        overlay_color = QColor(0, 0, 0, OVERLAY_ALPHA)
        path_outer = QPainterPath()
        path_outer.addRect(QRectF(self.rect()))
        path_inner = QPainterPath()
        path_inner.addRect(cr)
        path_shadow = path_outer - path_inner
        painter.fillPath(path_shadow, QBrush(overlay_color))

        # 5. Seçim çerçevesi
        painter.setPen(QPen(LINE_COLOR, 1.5, Qt.PenStyle.SolidLine))
        painter.drawRect(cr)

        # 6. Üçte-bir grid çizgileri (WhatsApp gibi)
        w3 = cr.width() / 3
        h3 = cr.height() / 3
        painter.setPen(QPen(GRID_COLOR, 0.8, Qt.PenStyle.SolidLine))
        for i in (1, 2):
            x = cr.left() + w3 * i
            painter.drawLine(QPointF(x, cr.top()), QPointF(x, cr.bottom()))
            y = cr.top() + h3 * i
            painter.drawLine(QPointF(cr.left(), y), QPointF(cr.right(), y))

        # 7. Handle'lar
        painter.setPen(QPen(HANDLE_STROKE, HANDLE_BORDER))
        painter.setBrush(QBrush(HANDLE_FILL))
        for rect in self._handle_rects().values():
            painter.drawRoundedRect(rect, 3, 3)

        # 8. Köşe L-çizgileri (WhatsApp imzası)
        c_len = 18  # köşe çizgisi uzunluğu
        painter.setPen(QPen(ACCENT, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        corners = [
            (cr.topLeft(),     ( c_len, 0), (0,  c_len)),
            (cr.topRight(),    (-c_len, 0), (0,  c_len)),
            (cr.bottomLeft(),  ( c_len, 0), (0, -c_len)),
            (cr.bottomRight(), (-c_len, 0), (0, -c_len)),
        ]
        for origin, h_vec, v_vec in corners:
            painter.drawLine(origin, origin + QPointF(*h_vec))
            painter.drawLine(origin, origin + QPointF(*v_vec))

        painter.end()



# ─────────────────────────────────────────────────────────────────────────────
# Dialog
# ─────────────────────────────────────────────────────────────────────────────

class ImageCropDialog(QDialog):
    """
    WhatsApp tarzı, tam ekran crop dialog.
    crop_rect: QRect | None  →  orijinal görüntü piksel koordinatı
    """

    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.crop_rect: Optional[QRect] = None

        self.setWindowTitle("Fotoğraf Kırp")
        self.setModal(True)
        self.setMinimumSize(820, 620)
        self.resize(1100, 780)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()
        self._fade_in()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Dış kart
        card = QFrame()
        card.setObjectName("cropCard")
        card.setStyleSheet("""
            QFrame#cropCard {
                background: #12121F;
                border-radius: 18px;
                border: 1px solid rgba(124,77,255,0.35);
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        root.addWidget(card)

        # Başlık bar
        title_bar = QWidget()
        title_bar.setFixedHeight(52)
        title_bar.setStyleSheet("background: transparent;")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(20, 0, 20, 0)

        from PyQt6.QtWidgets import QLabel
        lbl = QLabel("✂  Fotoğraf Kırp")
        lbl.setStyleSheet("color: #E0E0FF; font-size: 15px; font-weight: 600;")
        tb_layout.addWidget(lbl)
        tb_layout.addStretch()

        hint = QLabel("Shift → oran kilidi  •  Kaydır → zoom  •  Sürükle → taşı")
        hint.setStyleSheet("color: rgba(160,160,200,0.7); font-size: 11px;")
        tb_layout.addWidget(hint)

        card_layout.addWidget(title_bar)

        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: rgba(124,77,255,0.25);")
        card_layout.addWidget(sep)

        # Canvas
        pixmap = QPixmap(self.image_path)
        self._canvas = CropCanvas(pixmap)
        card_layout.addWidget(self._canvas, 1)

        # Alt bar
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(64)
        bottom_bar.setStyleSheet("background: rgba(255,255,255,0.03); border-bottom-left-radius: 18px; border-bottom-right-radius: 18px;")
        bb_layout = QHBoxLayout(bottom_bar)
        bb_layout.setContentsMargins(20, 0, 20, 0)

        btn_reset = QPushButton("⟳  Sıfırla")
        btn_cancel = QPushButton("✕  Vazgeç")
        btn_apply  = QPushButton("✓  Kırp ve Uygula")

        for btn in (btn_reset, btn_cancel):
            btn.setFixedHeight(40)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255,255,255,0.08);
                    color: #C0C0E0;
                    border: 1px solid rgba(255,255,255,0.12);
                    border-radius: 10px;
                    padding: 0 18px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.14);
                    color: #FFFFFF;
                }
            """)

        btn_apply.setFixedHeight(40)
        btn_apply.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #7C4DFF, stop:1 #651FFF);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 0 28px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #9C6FFF, stop:1 #7C4DFF);
            }
            QPushButton:pressed {
                background: #5E35B1;
            }
        """)

        btn_reset.clicked.connect(self._reset)
        btn_cancel.clicked.connect(self.reject)
        btn_apply.clicked.connect(self._accept_crop)

        bb_layout.addWidget(btn_reset)
        bb_layout.addStretch()
        bb_layout.addWidget(btn_cancel)
        bb_layout.addSpacerItem(QSpacerItem(12, 0))
        bb_layout.addWidget(btn_apply)
        card_layout.addWidget(bottom_bar)

        # Pixmap açılamazsa uyarı
        if pixmap.isNull():
            from PyQt6.QtWidgets import QLabel as _QLabel
            warn = _QLabel("  Görsel açılamadı. Lütfen farklı bir dosya seçin.")
            warn.setStyleSheet("color: #FF6E6E; font-size: 13px; padding: 8px;")
            card_layout.insertWidget(2, warn)
            btn_apply.setEnabled(False)

    def _fade_in(self):
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ─── Slots ───────────────────────────────────────────────────────────────

    def _reset(self):
        self._canvas.reset_crop()

    def _accept_crop(self):
        rect = self._canvas.get_crop_rect_on_original()
        if rect is None:
            # Seçim yoksa tüm görüntüyü döndür
            pm = self._canvas._orig_pixmap
            if pm and not pm.isNull():
                self.crop_rect = QRect(0, 0, pm.width(), pm.height())
                self.accept()
            return
        self.crop_rect = rect
        self.accept()

    # ─── Drag to move frameless window ───────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)
