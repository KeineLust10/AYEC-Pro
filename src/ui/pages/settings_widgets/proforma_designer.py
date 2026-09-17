# -*- coding: utf-8 -*-

"""
Proforma Designer
Proforma PDF Şablon Tasarımcısı - Canvas ve Dialog
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QFrame, QScrollArea, QComboBox, QDialog as QtDialog)
from PyQt6.QtGui import QFont, QAction, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtPdf import QPdfDocument

from src.utils.theme_colors import theme_qss
from src.utils import message_helper


class ProformaTemplateCanvas(QWidget):
    """Proforma şablonu üzerinde alan çizim canvas'ı"""
    
    # Alan label'ları (key → Türkçe isim)
    FIELD_LABELS = {
        "company_name": "Firma Adı",
        "customer_name": "Müşteri Adı",
        "date": "Tarih",
        "table": "Ürün Tablosu",
        "totals": "Toplamlar",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.field_rects = {}
        self.current_field = None
        self.drag_start = None
        self.temp_rect = None
        self.setMouseTracking(True)          # mouseMoveEvent her zaman gelsin
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.colors = {
            "company_name": QColor(0, 102, 204, 200),
            "customer_name": QColor(46, 204, 113, 200),
            "date": QColor(241, 196, 15, 200),
            "table": QColor(155, 89, 182, 200),
            "totals": QColor(231, 76, 60, 200),
        }

    def set_image(self, image):
        self.image = image
        if image:
            self.setFixedSize(image.size())
        self.update()

    def set_current_field(self, field_key):
        self.current_field = field_key
        # Crosshair imleç: alan seçiliyken çizim modu aktif
        if field_key:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def set_field_rects(self, rects):
        self.field_rects = rects
        self.update()

    def get_field_rects(self):
        return self.field_rects

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.current_field:
            # self.window() → en üst dialog'u bul (viewport değil)
            message_helper.show_warning(
                self.window(), "Uyarı",
                "Lütfen önce sol panelden bir alan seçin.\n"
                "(Firma Adı, Müşteri Adı, Tarih vs.)"
            )
            return
        if not self.image:
            return
        self.drag_start = event.position()
        self.temp_rect = QRectF(self.drag_start, self.drag_start)
        self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start is None or self.temp_rect is None:
            return
        self.temp_rect = QRectF(self.drag_start, event.position())
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.temp_rect is None or not self.image:
            return
        rect = self.temp_rect.normalized()
        bounds = QRectF(0, 0, self.image.width(), self.image.height())
        rect = rect.intersected(bounds)
        if rect.width() > 5 and rect.height() > 5:
            self.field_rects[self.current_field] = rect
        # Her iki değişkeni sıfırla (bug fix: drag_start sıfırlanmıyordu)
        self.temp_rect = None
        self.drag_start = None
        self.update()

    def paintEvent(self, event):
        if not self.image:
            return
        painter = QPainter(self)
        painter.drawImage(0, 0, self.image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        for key, rect in self.field_rects.items():
            color = self.colors.get(key, QColor(52, 152, 219, 200))
            # Aktif alan ise kenarlık daha kalın
            border_w = 3 if key == self.current_field else 2
            pen = QPen(color, border_w)
            painter.setPen(pen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 50))
            painter.drawRect(rect)
            # Etiket: Türkçe isim göster
            label = self.FIELD_LABELS.get(key, key)
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.setPen(QPen(color, 1))
            painter.drawText(
                rect.adjusted(4, 2, -4, -2),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                label
            )

        # Sürükleme sırasında geçici dikdörtgen
        if self.temp_rect:
            color = self.colors.get(self.current_field, QColor(52, 152, 219, 200))
            pen = QPen(color, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 40))
            painter.drawRect(self.temp_rect.normalized())


class ProformaTemplateDesignerDialog(QtDialog):
    """Şablon Tasarımcısı - PDF üzerinde alan yerleştirme dialog'u"""
    
    def __init__(self, db, template_path, parent=None):
        super().__init__(parent)
        self.db = db
        self.template_path = os.path.abspath(template_path)
        self.pdf_doc = QPdfDocument(self)
        self.page_size = None
        self.scale = 1.0
        self.current_page_index = 0
        self.setWindowTitle("Şablon Tasarımcısı")
        self.resize(1200, 900)
        self.canvas = ProformaTemplateCanvas()
        self.field_buttons = {}
        self.active_field_label = QLabel()
        self.page_selector = QComboBox()
        self._init_ui()
        self._load_pdf()
    
    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        left_panel = QVBoxLayout()
        title = QLabel("Alanları Seçip Çizin")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        left_panel.addWidget(title)
        page_label = QLabel("Sayfa Seçimi")
        left_panel.addWidget(page_label)
        self.page_selector.setStyleSheet(theme_qss("QComboBox { padding: 6px; border-radius: 6px; background-color: @surface_alt; color: @text; }"))
        self.page_selector.currentIndexChanged.connect(self._on_page_change)
        left_panel.addWidget(self.page_selector)
        fields = [
            ("company_name", "Firma Adı"),
            ("customer_name", "Müşteri Adı"),
            ("date", "Tarih"),
            ("table", "Ürün Tablosu"),
            ("totals", "Toplamlar"),
        ]
        for key, label in fields:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(theme_qss(
                "QPushButton { background-color: @surface_alt; color: @text; "
                "padding: 8px; border-radius: 6px; border: 2px solid transparent; } "
                "QPushButton:hover { background-color: @surface; }"
            ))
            btn.clicked.connect(lambda checked, k=key, l=label: self._select_field(k, l))
            left_panel.addWidget(btn)
            self.field_buttons[key] = btn
        self.active_field_label.setText("Aktif Alan: -")
        self.active_field_label.setStyleSheet(theme_qss(
            "color: @accent; font-size: 11px; font-weight: bold; padding: 4px 0;"
        ))
        left_panel.addWidget(self.active_field_label)
        btn_clear = QPushButton("Seçili Alanı Temizle")
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(theme_qss("QPushButton { background-color: @danger; color: @selection_text; padding: 8px; border-radius: 6px; } QPushButton:hover { background-color: @danger; }"))
        btn_clear.clicked.connect(self._clear_current_field)
        left_panel.addWidget(btn_clear)
        left_panel.addStretch()
        btn_save = QPushButton("Kaydet")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(theme_qss("QPushButton { background-color: @accent; color: @selection_text; padding: 10px; border-radius: 6px; font-weight: bold; } QPushButton:hover { background-color: @accent_hover; }"))
        btn_save.clicked.connect(self._save_layout)
        btn_close = QPushButton("Kapat")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet(theme_qss("QPushButton { background-color: @surface_alt; color: @text; padding: 10px; border-radius: 6px; } QPushButton:hover { background-color: @surface; }"))
        btn_close.clicked.connect(self.reject)
        left_panel.addWidget(btn_save)
        left_panel.addWidget(btn_close)
        main_layout.addLayout(left_panel, 20)
        canvas_container = QScrollArea()
        canvas_container.setWidgetResizable(False)   # Canvas boyutunu koru (fix)
        canvas_container.setFrameShape(QFrame.Shape.NoFrame)
        canvas_container.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        canvas_container.setWidget(self.canvas)
        main_layout.addWidget(canvas_container, 80)
        self.setStyleSheet(theme_qss("""
            QDialog { background-color: @background; }
            QLabel { color: @text; }
            QScrollArea { background-color: @surface; }
        """))

    def _load_pdf(self):
        try:
            self.pdf_doc.load(self.template_path)
            page_count = self.pdf_doc.pageCount()
            self.page_selector.clear()
            for i in range(page_count):
                self.page_selector.addItem(f"Sayfa {i + 1}", i)
            if page_count > 0:
                self._load_page(0)
            # Load saved field rects from DB
            import json
            saved = self.db.get_setting("proforma_field_rects", "{}")
            if saved:
                try:
                    rects_data = json.loads(saved)
                    rects = {}
                    for k, v in rects_data.items():
                        if isinstance(v, (list, tuple)) and len(v) == 4:
                            rects[k] = QRectF(v[0], v[1], v[2], v[3])
                    self.canvas.set_field_rects(rects)
                except Exception:
                    pass
        except Exception as e:
            message_helper.show_error(
                self,
                "Hata",
                f"PDF y\u00fcklenemedi: {e}",
            )

    def _load_page(self, index):
        if self.pdf_doc.status() != QPdfDocument.Status.Ready:
            return
        if index is None or not 0 <= int(index) < self.pdf_doc.pageCount():
            return

        self.current_page_index = int(index)
        self.page_size = self.pdf_doc.pagePointSize(self.current_page_index)
        if not self.page_size.isValid() or self.page_size.isEmpty():
            message_helper.show_error(
                self,
                "Hata",
                "PDF sayfa boyutu okunamad\u0131.",
            )
            return

        render_scale = 150.0 / 72.0
        image_size = QSize(
            max(1, round(self.page_size.width() * render_scale)),
            max(1, round(self.page_size.height() * render_scale)),
        )
        image = self.pdf_doc.render(self.current_page_index, image_size)
        if image.isNull():
            message_helper.show_error(
                self,
                "Hata",
                "PDF sayfas\u0131 g\u00f6r\u00fcnt\u00fcye d\u00f6n\u00fc\u015ft\u00fcr\u00fclemedi.",
            )
            return
        self.canvas.set_image(image)

    def _on_page_change(self, idx):
        if idx >= 0:
            page_index = self.page_selector.currentData()
            self._load_page(page_index)

    def _select_field(self, key, label):
        self.canvas.set_current_field(key)
        self.active_field_label.setText(f"Aktif Alan: {label}")
        for k, btn in self.field_buttons.items():
            if k == key:
                btn.setStyleSheet(theme_qss(
                    f"QPushButton {{ background-color: {self.canvas.colors.get(k, QColor(52, 152, 219)).name()}; "
                    f"color: white; padding: 8px; border-radius: 6px; border: 2px solid @accent; }} "
                    f"QPushButton:hover {{ background-color: {self.canvas.colors.get(k, QColor(52, 152, 219)).darker(110).name()}; }}"
                ))
            else:
                btn.setStyleSheet(theme_qss(
                    "QPushButton { background-color: @surface_alt; color: @text; "
                    "padding: 8px; border-radius: 6px; border: 2px solid transparent; } "
                    "QPushButton:hover { background-color: @surface; }"
                ))

    def _clear_current_field(self):
        if self.canvas.current_field and self.canvas.current_field in self.canvas.field_rects:
            del self.canvas.field_rects[self.canvas.current_field]
            self.canvas.update()
            self.active_field_label.setText("Aktif Alan: -")
            self.canvas.set_current_field(None)
            for btn in self.field_buttons.values():
                btn.setStyleSheet(theme_qss(
                    "QPushButton { background-color: @surface_alt; color: @text; "
                    "padding: 8px; border-radius: 6px; border: 2px solid transparent; } "
                    "QPushButton:hover { background-color: @surface; }"
                ))

    def _save_layout(self):
        rects = self.canvas.get_field_rects()
        import json
        rects_data = {}
        for k, rect in rects.items():
            rects_data[k] = [rect.x(), rect.y(), rect.width(), rect.height()]
        self.db.set_setting("proforma_field_rects", json.dumps(rects_data))
        message_helper.show_success(self, "Başarılı", "Şablon düzeni kaydedildi.")
        self.accept()
