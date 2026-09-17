# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QFrame,
    QWidget,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss


class AutomotiveDamageDialog(ModernDialog):
    DAMAGE_ZONES = {
        "On": ["On Tampon", "Kaput", "Sol On Camurluk", "Sag On Camurluk"],
        "Arka": ["Arka Tampon", "Bagaj", "Sol Arka Camurluk", "Sag Arka Camurluk"],
        "Sol": ["Sol On Kapi", "Sol Arka Kapi", "Sol Ayna", "Sol Marspiyel"],
        "Sag": ["Sag On Kapi", "Sag Arka Kapi", "Sag Ayna", "Sag Marspiyel"],
    }
    STATUS_OPTIONS = ["Yok", "Cizik", "Gocuk", "Boya Hasari", "Kirildi"]

    def __init__(self, existing_data=None, parent=None):
        super().__init__("Hasar Tespit Formu", parent, width=1040, height=760)
        self.widgets = {}
        self.zone_badges = {}
        self.note_field = None
        self.result_data = existing_data or {}
        self._build_ui()
        self._load_existing(existing_data or {})
        self._refresh_preview()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            theme_qss("QScrollArea { background: transparent; border: none; }")
        )

        body = QWidget()
        root = QHBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(16)

        form_wrap = QWidget()
        form_root = QVBoxLayout(form_wrap)
        form_root.setContentsMargins(0, 0, 0, 0)
        form_root.setSpacing(12)

        intro = QLabel(
            "Aracin dort yonundeki bolgeleri isaretleyin. Hasar olmayan alanlari 'Yok' olarak birakin."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        form_root.addWidget(intro)

        for side, zones in self.DAMAGE_ZONES.items():
            title = QLabel(f"{side} Gorunus")
            title.setStyleSheet(
                theme_qss("font-size: 14px; font-weight: 800; color: @text;")
            )
            form_root.addWidget(title)
            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)
            for row_index, zone in enumerate(zones):
                lbl = QLabel(zone)
                lbl.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
                cmb = QComboBox()
                cmb.addItems(self.STATUS_OPTIONS)
                cmb.setStyleSheet(
                    theme_qss(
                        "padding: 6px; border: 1px solid @border; border-radius: 6px; background: @surface; color: @text;"
                    )
                )
                cmb.currentTextChanged.connect(self._refresh_preview)
                note = QLineEdit()
                note.setPlaceholderText("Opsiyonel not")
                note.setStyleSheet(
                    theme_qss(
                        "border: 1px solid @border; border-radius: 6px; padding: 6px; background: @surface; color: @text;"
                    )
                )
                self.widgets[f"{side}:{zone}"] = {
                    "status": cmb,
                    "note": note,
                    "side": side,
                    "zone": zone,
                }
                grid.addWidget(lbl, row_index, 0)
                grid.addWidget(cmb, row_index, 1)
                grid.addWidget(note, row_index, 2)
            form_root.addLayout(grid)

        extra_title = QLabel("Genel Hasar Notu")
        extra_title.setStyleSheet(
            theme_qss("font-size: 14px; font-weight: 800; color: @text;")
        )
        form_root.addWidget(extra_title)
        self.note_field = QTextEdit()
        self.note_field.setPlaceholderText(
            "Teslim alindiginda gorulen genel cizik, gocuk veya aciklama"
        )
        self.note_field.setFixedHeight(90)
        self.note_field.setStyleSheet(
            theme_qss(
                "border: 1px solid @border; border-radius: 6px; padding: 6px; background: @surface; color: @text;"
            )
        )
        form_root.addWidget(self.note_field)
        form_root.addStretch(1)

        preview_card = QFrame()
        preview_card.setMinimumWidth(260)
        preview_card.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border: 1px solid @border; border-radius: 12px;"
            )
        )
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        preview_layout.setSpacing(10)
        preview_title = QLabel("Arac Uzeri Hasar Ozeti")
        preview_title.setStyleSheet(
            theme_qss("font-size: 13px; font-weight: 800; color: @text;")
        )
        preview_layout.addWidget(preview_title)
        preview_sub = QLabel("Secilen alanlar burada renkli olarak vurgulanir.")
        preview_sub.setWordWrap(True)
        preview_sub.setStyleSheet(theme_qss("font-size: 11px; color: @text_muted;"))
        preview_layout.addWidget(preview_sub)

        for side, zones in self.DAMAGE_ZONES.items():
            section = QLabel(f"{side} Gorunus")
            section.setStyleSheet(
                theme_qss(
                    "font-size: 12px; font-weight: 800; color: @text; margin-top: 4px;"
                )
            )
            preview_layout.addWidget(section)
            section_grid = QGridLayout()
            section_grid.setHorizontalSpacing(6)
            section_grid.setVerticalSpacing(6)
            for index, zone in enumerate(zones):
                badge = QLabel(zone)
                badge.setWordWrap(True)
                badge.setMinimumHeight(40)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setStyleSheet(
                    theme_qss(
                        "background: @surface; border: 1px solid @border; border-radius: 10px; color: @text_muted; font-size: 11px; font-weight: 700; padding: 4px;"
                    )
                )
                self.zone_badges[f"{side}:{zone}"] = badge
                section_grid.addWidget(badge, index // 2, index % 2)
            preview_layout.addLayout(section_grid)
        preview_layout.addStretch(1)

        root.addWidget(form_wrap, 1)
        root.addWidget(preview_card, 0)

        scroll.setWidget(body)

        self.add_widget(scroll)
        self.add_cancel_button("Iptal")
        self.add_button("Hasar Formunu Kaydet", "success", self._accept)

    def _load_existing(self, existing_data):
        for entry in (
            existing_data.get("items", []) if isinstance(existing_data, dict) else []
        ):
            key = f"{entry.get('side')}:{entry.get('zone')}"
            widget_map = self.widgets.get(key)
            if not widget_map:
                continue
            widget_map["status"].setCurrentText(
                str(entry.get("status", "Yok") or "Yok")
            )
            widget_map["note"].setText(str(entry.get("note", "") or ""))
        if isinstance(existing_data, dict) and self.note_field is not None:
            self.note_field.setPlainText(
                str(existing_data.get("general_note", "") or "")
            )

    def _refresh_preview(self, *_args):
        palette = {
            "Yok": ("@surface", "@text_muted"),
            "Cizik": ("#FDE68A", "#92400E"),
            "Gocuk": ("#FCA5A5", "#991B1B"),
            "Boya Hasari": ("#93C5FD", "#1D4ED8"),
            "Kirildi": ("#C4B5FD", "#5B21B6"),
        }
        for key, widget_map in self.widgets.items():
            badge = self.zone_badges.get(key)
            if badge is None:
                continue
            status = widget_map["status"].currentText().strip() or "Yok"
            bg, fg = palette.get(status, ("@surface", "@text"))
            badge.setText(f"{widget_map['zone']}\n{status}")
            badge.setStyleSheet(
                theme_qss(
                    f"background: {bg}; border: 1px solid @border; border-radius: 10px; color: {fg}; font-size: 11px; font-weight: 800; padding: 4px;"
                )
            )

    def _accept(self):
        items = []
        for widget_map in self.widgets.values():
            status = widget_map["status"].currentText().strip()
            note = widget_map["note"].text().strip()
            if status == "Yok" and not note:
                continue
            items.append(
                {
                    "side": widget_map["side"],
                    "zone": widget_map["zone"],
                    "status": status,
                    "note": note,
                }
            )
        self.result_data = {
            "items": items,
            "general_note": self.note_field.toPlainText().strip()
            if self.note_field is not None
            else "",
        }
        self.accept()
