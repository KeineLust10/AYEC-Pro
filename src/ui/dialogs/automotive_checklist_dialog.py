# -*- coding: utf-8 -*-

import json

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss


class AutomotiveChecklistDialog(ModernDialog):
    STATUS_OPTIONS = ["Tamam", "Degismeli", "Incelenmeli"]

    def __init__(self, templates, existing_data=None, parent=None):
        super().__init__("Otomotiv Kontrol Formu", parent, width=1120, height=760)
        self.templates = templates or {}
        self.widgets = {}
        self.result_data = existing_data or {}
        self._build_ui()
        self._load_existing_data(existing_data or {})

    def _build_ui(self):
        body = QWidget()
        body.setObjectName("AutomotiveChecklistBody")
        root = QVBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        intro = QLabel("Kontrol kalemlerini Tamam / Degismeli / Incelenmeli olarak isaretleyin ve gerekli notlari dusun.")
        intro.setWordWrap(True)
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        root.addWidget(intro)

        for section_id, items in self.templates.items():
            section_title = QLabel(str(section_id).replace("_", " ").title())
            section_title.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text;"))
            root.addWidget(section_title)

            grid = QGridLayout()
            grid.setHorizontalSpacing(10)
            grid.setVerticalSpacing(8)
            for row_index, item in enumerate(items or []):
                item_name = str(item.get("name", "") or "").strip()
                if not item_name:
                    continue
                key = f"{section_id}:{item_name}"
                lbl = QLabel(item_name)
                lbl.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
                cmb = QComboBox()
                cmb.addItems(self.STATUS_OPTIONS)
                cmb.setStyleSheet(theme_qss("padding: 6px; border: 1px solid @border; border-radius: 6px; background: @surface; color: @text;"))
                txt = QTextEdit()
                txt.setPlaceholderText("Opsiyonel not")
                txt.setFixedHeight(54)
                txt.setStyleSheet(theme_qss("border: 1px solid @border; border-radius: 6px; padding: 6px; background: @surface; color: @text;"))
                self.widgets[key] = {"status": cmb, "note": txt, "section": section_id, "label": item_name}
                grid.addWidget(lbl, row_index, 0)
                grid.addWidget(cmb, row_index, 1)
                grid.addWidget(txt, row_index, 2)
            root.addLayout(grid)

        scroll = QScrollArea()
        scroll.setObjectName("AutomotiveChecklistScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(body)
        scroll.setStyleSheet(theme_qss("""
            QScrollArea#AutomotiveChecklistScroll {
                background: transparent;
                border: none;
            }
            QScrollArea#AutomotiveChecklistScroll::viewport {
                background: transparent;
                border: none;
            }
            QWidget#AutomotiveChecklistBody {
                background: transparent;
            }
            QScrollBar:vertical {
                background: @surface_alt;
                border: none;
                width: 10px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: @border;
                min-height: 32px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: @accent;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """))
        self.add_widget(scroll)
        self.add_cancel_button("Iptal")
        self.add_button("Kontrol Formunu Kaydet", "success", self._accept)

    def _load_existing_data(self, existing_data):
        entries = existing_data if isinstance(existing_data, list) else existing_data.get("items", [])
        for entry in entries or []:
            key = f"{entry.get('section')}:{entry.get('label')}"
            widget_map = self.widgets.get(key)
            if not widget_map:
                continue
            status = str(entry.get("status", "Tamam") or "Tamam")
            note = str(entry.get("note", "") or "")
            widget_map["status"].setCurrentText(status)
            widget_map["note"].setPlainText(note)

    def _accept(self):
        items = []
        for widget_map in self.widgets.values():
            items.append(
                {
                    "section": widget_map["section"],
                    "label": widget_map["label"],
                    "status": widget_map["status"].currentText().strip(),
                    "note": widget_map["note"].toPlainText().strip(),
                }
            )
        self.result_data = {"items": items, "raw_json": json.dumps(items, ensure_ascii=False)}
        self.accept()
