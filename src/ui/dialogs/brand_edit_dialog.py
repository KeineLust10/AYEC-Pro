# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFormLayout, QFrame, QLabel, QLineEdit, QVBoxLayout, QWidget

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error


class BrandEditDialog(ModernDialog):
    """Focused catalog editor shared by the device and technician screens."""

    def __init__(
        self,
        db,
        parent=None,
        initial_device_type="",
        initial_brand="",
        edit_mode=False,
    ):
        title = "Marka Kayd\u0131n\u0131 D\u00fczenle" if edit_mode else "Yeni Marka / Cihaz T\u00fcr\u00fc"
        super().__init__(title=title, parent=parent, width=540, height=400)
        self.db = db
        self.initial_device_type = initial_device_type
        self.initial_brand = initial_brand
        self.edit_mode = bool(edit_mode)
        self._setup_ui()

    def _setup_ui(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)

        intro = QFrame()
        intro.setObjectName("BrandEditIntro")
        intro.setStyleSheet(theme_qss("""
            QFrame#BrandEditIntro {
                background: @selection_bg; border: 1px solid @accent; border-radius: 12px;
            }
            QFrame#BrandEditIntro QLabel {
                background: transparent; border: none;
            }
        """))
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(16, 14, 16, 14)
        intro_layout.setSpacing(4)
        title = QLabel("Cihaz katalog bilgisi")
        title.setStyleSheet(theme_qss("color: @text; font-size: 15px; font-weight: 700;"))
        detail = QLabel(
            "Servis formu ve Teknisyen Panelinde g\u00f6r\u00fcnecek cihaz t\u00fcr\u00fc ile markay\u0131 tan\u0131mlay\u0131n."
        )
        detail.setWordWrap(True)
        detail.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        intro_layout.addWidget(title)
        intro_layout.addWidget(detail)
        layout.addWidget(intro)

        form_card = QFrame()
        form_card.setObjectName("BrandEditForm")
        form_card.setStyleSheet(theme_qss("""
            QFrame#BrandEditForm {
                background: @surface; border: 1px solid @border; border-radius: 12px;
            }
            QFrame#BrandEditForm QLabel {
                background: transparent; border: none; color: @text; font-weight: 600;
            }
            QFrame#BrandEditForm QLineEdit {
                min-height: 38px; background: @surface_alt; color: @text;
                border: 1px solid @border; border-radius: 8px; padding: 4px 10px;
            }
            QFrame#BrandEditForm QLineEdit:focus { border-color: @accent; background: @surface; }
        """))
        form = QFormLayout(form_card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(14)

        self.inp_device_type = QLineEdit(self.initial_device_type)
        self.inp_device_type.setPlaceholderText("Telefon, Laptop, Tablet...")
        self.inp_brand = QLineEdit(self.initial_brand)
        self.inp_brand.setPlaceholderText("Apple, Samsung, Xiaomi...")
        form.addRow("Cihaz T\u00fcr\u00fc", self.inp_device_type)
        form.addRow("Marka", self.inp_brand)
        layout.addWidget(form_card)
        layout.addStretch(1)
        self.add_widget(content)

        self.set_footer_visible(True, 64)
        self.clear_footer()
        self.footer_layout.addStretch(1)
        self.add_cancel_button("\u0130ptal")
        self.add_button("Kaydet", "primary", self.save)

    def save(self):
        device_type = (self.inp_device_type.text() or "").strip()
        brand = (self.inp_brand.text() or "").strip()
        if not device_type and not brand:
            show_error(
                self,
                "En az\u0131ndan cihaz t\u00fcr\u00fc veya marka alanlar\u0131ndan birini doldurun.",
            )
            return

        try:
            cur = self.db.cursor
            if self.edit_mode:
                cur.execute(
                    """
                    UPDATE device_brands
                    SET device_type=?, brand=?
                    WHERE device_type=? AND brand=?
                    """,
                    (device_type, brand, self.initial_device_type, self.initial_brand),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO device_brands (device_type, brand, is_active)
                    VALUES (?, ?, 1)
                    """,
                    (device_type, brand),
                )
            self.db.conn.commit()
            self.accept()
        except Exception as exc:
            show_error(self, f"Kaydedilemedi: {exc}")
