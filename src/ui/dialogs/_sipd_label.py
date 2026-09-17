# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QMouseEvent, QBrush
from PyQt6.QtWidgets import QLabel, QSizePolicy
from src.utils.theme_colors import theme_qss

class SourceSelectionLabel(QLabel):
    """
    WhatsApp/ekran görüntüsü tarzı kırpma seçici.
    - Seçim dışı alan yarı-saydam siyah overlay ile karartılır.
    - Seçili alan parlak, net görünür.
    - Köşe tutamaçları ve boyutlama bilgisi gösterilir.
    - Resim, widget alanını dolduracak şekilde maksimum boyutla gösterilir.
    """
    selection_changed = pyqtSignal()
    selection_committed = pyqtSignal()
    _HANDLE_SIZE = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_pixmap = QPixmap(); self.display_pixmap = QPixmap()
        self.selection_rect = QRect(); self.dragging = False
        self.start_point = None; self.fit_width = False; self.zoom_factor = 1.0; self.view_crop_rect = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter); self.setMouseTracking(True); self.setMinimumSize(400, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setStyleSheet(theme_qss("background: @surface_alt; border: 1px dashed @border; border-radius: 10px;"))

    def set_fit_width(self, enabled=True):
        self.fit_width = bool(enabled); self.setMinimumHeight(620 if self.fit_width else 500); self._refresh_scaled()

    def set_zoom_factor(self, factor):
        self.zoom_factor = max(0.5, min(4.0, float(factor))); self._refresh_scaled(); self.update()

    def zoom_in(self): self.set_zoom_factor(self.zoom_factor + 0.25)
    def zoom_out(self): self.set_zoom_factor(self.zoom_factor - 0.25)

    def set_image_path(self, path):
        self.original_pixmap = QPixmap(path); self.selection_rect = QRect(); self.view_crop_rect = None
        self._refresh_scaled(); self.selection_changed.emit()

    def resizeEvent(self, event): super().resizeEvent(event); self._refresh_scaled()

    def _refresh_scaled(self):
        if self.original_pixmap.isNull() or self.width() <= 1 or self.height() <= 1:
            self.clear(); return
        source_pixmap = self._source_pixmap_for_view()
        if source_pixmap.isNull(): self.clear(); return
        viewport = self.parentWidget(); base_size = viewport.size() if viewport else self.size()
        target_size = QSize(max(1, int(base_size.width() * self.zoom_factor)), max(1, int(base_size.height() * self.zoom_factor)))
        self.display_pixmap = source_pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setMinimumSize(max(400, self.display_pixmap.width() + 4), max(500, self.display_pixmap.height() + 4))
        self.setPixmap(self.display_pixmap)

    def _source_rect_for_view(self):
        if self.original_pixmap.isNull(): return QRect()
        full = QRect(0, 0, self.original_pixmap.width(), self.original_pixmap.height())
        if self.view_crop_rect is None: return full
        cropped = self.view_crop_rect.intersected(full)
        return cropped if not cropped.isNull() else full

    def _source_pixmap_for_view(self):
        if self.original_pixmap.isNull(): return QPixmap()
        rect = self._source_rect_for_view()
        if rect.size() == self.original_pixmap.size(): return self.original_pixmap
        return self.original_pixmap.copy(rect)

    def focus_on_original_rect(self, rect):
        if rect is None or self.original_pixmap.isNull(): return
        full = QRect(0, 0, self.original_pixmap.width(), self.original_pixmap.height())
        rect = rect.intersected(full)
        if rect.isNull() or rect.width() < 10 or rect.height() < 10: return
        self.view_crop_rect = QRect(rect); self.selection_rect = QRect(); self._refresh_scaled(); self.update(); self.selection_changed.emit()

    def reset_view_crop(self):
        self.view_crop_rect = None; self.selection_rect = QRect(); self._refresh_scaled(); self.update(); self.selection_changed.emit()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.display_pixmap.isNull():
            self.dragging = True; self.start_point = event.position().toPoint()
            self.selection_rect = QRect(self.start_point, self.start_point); self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging and self.start_point:
            self.selection_rect = QRect(self.start_point, event.position().toPoint()).normalized(); self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.dragging and self.start_point:
            self.dragging = False; self.selection_rect = QRect(self.start_point, event.position().toPoint()).normalized()
            self.update(); self.selection_changed.emit(); self.selection_committed.emit()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.display_pixmap.isNull(): return
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        x_offset, y_offset = (self.width() - self.display_pixmap.width()) // 2, (self.height() - self.display_pixmap.height()) // 2
        img_rect = QRect(x_offset, y_offset, self.display_pixmap.width(), self.display_pixmap.height())
        if not self.selection_rect.isNull() and self.selection_rect.width() > 4 and self.selection_rect.height() > 4:
            sel = self.selection_rect.intersected(img_rect); overlay_color = QColor(0, 0, 0, 130)
            p.fillRect(img_rect.left(), img_rect.top(), img_rect.width(), sel.top() - img_rect.top(), overlay_color)
            p.fillRect(img_rect.left(), sel.bottom(), img_rect.width(), img_rect.bottom() - sel.bottom(), overlay_color)
            p.fillRect(img_rect.left(), sel.top(), sel.left() - img_rect.left(), sel.height(), overlay_color)
            p.fillRect(sel.right(), sel.top(), img_rect.right() - sel.right(), sel.height(), overlay_color)
            p.setPen(QPen(QColor(255, 255, 255), 2)); p.drawRect(sel)
            p.setPen(QPen(QColor(255, 255, 255, 90), 1, Qt.PenStyle.DashLine))
            tw, th = sel.width() // 3, sel.height() // 3
            for i in (1, 2):
                p.drawLine(sel.left() + tw * i, sel.top(), sel.left() + tw * i, sel.bottom())
                p.drawLine(sel.left(), sel.top() + th * i, sel.right(), sel.top() + th * i)
            hs = self._HANDLE_SIZE; p.setPen(QPen(QColor(255, 255, 255), 2)); p.setBrush(QBrush(QColor(30, 144, 255)))
            for c in [QRect(sel.left()-hs//2, sel.top()-hs//2, hs, hs), QRect(sel.right()-hs//2, sel.top()-hs//2, hs, hs),
                      QRect(sel.left()-hs//2, sel.bottom()-hs//2, hs, hs), QRect(sel.right()-hs//2, sel.bottom()-hs//2, hs, hs)]:
                p.drawRect(c)
            orig_rect = self.get_selected_rect_on_original()
            if orig_rect:
                dim_text = f"{orig_rect.width()} x {orig_rect.height()}"; font = p.font(); font.setPixelSize(12); font.setBold(True); p.setFont(font)
                lx, ly = sel.left() + 6, sel.top() - 6
                if ly < img_rect.top() + 16: ly = sel.top() + 20
                p.setPen(QColor(0, 0, 0, 160)); p.drawText(lx + 1, ly + 1, dim_text)
                p.setPen(QColor(255, 255, 255)); p.drawText(lx, ly, dim_text)
        p.end()

    def clear_selection(self): self.reset_view_crop()

    def get_selected_rect_on_original(self):
        if self.selection_rect.isNull() and self.view_crop_rect and not self.original_pixmap.isNull(): return QRect(self.view_crop_rect)
        if self.selection_rect.isNull() or self.display_pixmap.isNull() or self.original_pixmap.isNull(): return None
        x_off, y_off = (self.width() - self.display_pixmap.width()) // 2, (self.height() - self.display_pixmap.height()) // 2
        visible = QRect(x_off, y_off, self.display_pixmap.width(), self.display_pixmap.height())
        rect = self.selection_rect.intersected(visible)
        if rect.width() < 10 or rect.height() < 10: return None
        src_rect = self._source_rect_for_view(); sx, sy = src_rect.width() / self.display_pixmap.width(), src_rect.height() / self.display_pixmap.height()
        ox, oy = src_rect.x() + int((rect.x() - x_off) * sx), src_rect.y() + int((rect.y() - y_off) * sy)
        return QRect(ox, oy, max(1, int(rect.width() * sx)), max(1, int(rect.height() * sy)))

    def set_selection_from_original(self, rect):
        if not rect or self.display_pixmap.isNull() or self.original_pixmap.isNull(): return
        xo, yo = (self.width() - self.display_pixmap.width()) // 2, (self.height() - self.display_pixmap.height()) // 2
        src_rect = self._source_rect_for_view(); relative = rect.intersected(src_rect)
        if relative.isNull(): return
        sx, sy = self.display_pixmap.width() / max(1, src_rect.width()), self.display_pixmap.height() / max(1, src_rect.height())
        x, y = xo + int((relative.x() - src_rect.x()) * sx), yo + int((relative.y() - src_rect.y()) * sy)
        w, h = max(1, int(relative.width() * sx)), max(1, int(relative.height() * sy))
        self.selection_rect = QRect(x, y, w, h).intersected(QRect(xo, yo, self.display_pixmap.width(), self.display_pixmap.height()))
        self.update(); self.selection_changed.emit()
