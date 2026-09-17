
# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QTextEdit, QSizePolicy,
)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from src.ui.widgets.animated_toggle import AnimatedToggle


class NewServiceDialogWidgetsMixin:
    """Widget helpers, layout utilities, and reload functions (fault toggles, accessories)"""

    def create_workflow_strip(self, steps, active_index=0):
        """Build a compact, non-interactive service workflow indicator."""
        strip = QFrame()
        strip.setObjectName("ServiceWorkflowStrip")
        strip.setStyleSheet(theme_qss(
            """
            QFrame#ServiceWorkflowStrip {
                background: @surface_alt;
                border: 1px solid @border;
                border-radius: 8px;
            }
            QFrame#ServiceWorkflowStrip QLabel {
                background: transparent;
                border: none;
            }
            """
        ))
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        for index, step in enumerate(steps):
            item = QFrame()
            item.setObjectName("ServiceWorkflowItem")
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(8, 4, 8, 4)
            item_layout.setSpacing(7)

            badge = QLabel(str(index + 1))
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(theme_qss(
                (
                    "background: @accent; color: @selection_text;"
                    if index == active_index
                    else "background: @surface; color: @text_muted;"
                )
                + " border: 1px solid @border; border-radius: 12px; font-weight: 800;"
            ))

            label = QLabel(str(step))
            label.setStyleSheet(theme_qss(
                (
                    "color: @text; font-weight: 800;"
                    if index == active_index
                    else "color: @text_muted; font-weight: 700;"
                )
                + " font-size: 11px;"
            ))

            item_layout.addWidget(badge)
            item_layout.addWidget(label)
            item_layout.addStretch(1)
            layout.addWidget(item, 1)

            if index < len(steps) - 1:
                separator = QLabel(">")
                separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                separator.setStyleSheet(theme_qss(
                    "color: @text_muted; font-weight: 800; font-size: 12px;"
                ))
                layout.addWidget(separator)

        return strip

    def create_form_intro(self, title, subtitle):
        """Create a dense title block used above operational forms."""
        frame = QFrame()
        frame.setObjectName("ServiceFormIntro")
        frame.setStyleSheet(theme_qss(
            """
            QFrame#ServiceFormIntro {
                background: transparent;
                border: none;
            }
            """
        ))
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(theme_qss(
            "color: @text; font-size: 18px; font-weight: 800; border: none;"
        ))
        subtitle_label = QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 11px; border: none;"
        ))

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return frame

    def _sec(self, label_text):
        """Section header: thin line + small label"""
        w = QWidget()
        w.setFixedHeight(20)
        w.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)
        
        lbl = QLabel(label_text)
        lbl.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 10px; font-weight: 800; border: none; background: transparent;"
        ))
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        sep.setMaximumHeight(1)
        sep.setStyleSheet(theme_qss("border: none; border-top: 1px solid @border; background: @border;"))
        sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout.addWidget(lbl)
        layout.addWidget(sep, 1)
        return w

    def _note_editor_qss(self):
        return theme_qss(
            "QTextEdit {"
            " border: 1px solid @border;"
            " border-radius: 6px;"
            " padding: 6px 8px;"
            " font-size: 11px;"
            " background: @surface_alt;"
            " color: @text;"
            "}"
            "QTextEdit:focus {"
            " border: 1px solid @selection_bg;"
            " background: @surface;"
            "}"
        )

    def create_field_box(self, label_text, widget=None, layout=None):
        v = QVBoxLayout()
        v.setSpacing(2)
        v.setContentsMargins(0, 0, 0, 0)
        l = QLabel(label_text)
        l.setStyleSheet(theme_qss(
            "font-weight: 600; font-size: 10px; color: @text_muted; border: none; background: transparent;"
        ))
        v.addWidget(l)
        if widget:
            if isinstance(widget, QTextEdit) and (
                label_text.startswith("Genel Not") or label_text.startswith("Teknik Not")
            ):
                widget.setStyleSheet(self._note_editor_qss())
            v.addWidget(widget)
        elif layout:
            v.addLayout(layout)
        return v

    def create_card_group(self, title, color, _widget_or_layout, height=None):
        """Legacy compatibility stub for create_card_group"""
        return self._sec(title)

    def reload_fault_toggles(self):
        if not hasattr(self, 'fs_grid'):
            return
        try:
            while self.fs_grid.count():
                child = self.fs_grid.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            self.fault_toggles = {}
            labels = []
            provider = getattr(self, "_current_profile_labels", None)
            if callable(provider):
                labels = provider("Ar\u0131za H\u0131zl\u0131 Se\u00e7imi")
            if labels:
                active_notes = [(None, None, label, 1) for label in labels]
            else:
                active_notes = [
                    n for n in self.db.get_fast_notes('Ar\u0131za H\u0131zl\u0131 Se\u00e7imi')
                    if n[3] == 1
                ]
            row = 0
            col = 0
            for idx, note in enumerate(active_notes):
                label = str(note[2] or "").strip()
                if not label:
                    continue
                self.fault_note_order[label] = idx
                tgl = AnimatedToggle()
                tgl.setFixedSize(40, 20)
                tgl.setCursor(Qt.CursorShape.PointingHandCursor)
                tgl.toggled.connect(lambda checked, txt=label: self.toggle_fault_note(txt, checked))
                lbl = QLabel(label)
                lbl.setStyleSheet(theme_qss(
                    "color: @text; font-size: 12px; font-weight: 700; border: none;"
                ))
                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.mousePressEvent = lambda event, t=tgl: t.toggle()

                self.fs_grid.addWidget(tgl, row, col * 2)
                self.fs_grid.addWidget(lbl, row, col * 2 + 1)
                self.fault_toggles[label] = tgl

                col += 1
                if col >= 2:
                    col = 0
                    row += 1

            total_rows = max(row + (1 if col > 0 else 0), 1)
            if hasattr(self, 'fault_shortcuts_container'):
                self.fault_shortcuts_container.setMaximumHeight(min(38 * total_rows + 8, 120))
        except Exception as e:
            logger.error("NewServiceDialog reload_fault_toggles error: %s", e)

    def reload_accessory_cards(self):
        try:
            while self.acc_grid.count():
                child = self.acc_grid.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            self.accessory_checkboxes = {}
            labels = []
            provider = getattr(self, "_current_profile_labels", None)
            if callable(provider):
                labels = provider("Aksesuar")
            if labels:
                accs = [(None, None, label, 1) for label in labels]
            else:
                accs = [a for a in self.db.get_fast_notes('Aksesuar') if a[3] == 1]
            r, c = 0, 0
            for ac in accs:
                name = str(ac[2] or "").strip()
                if not name:
                    continue
                acc_card = QFrame()
                acc_card.setStyleSheet(theme_qss(
                    "background: @surface_alt; border: 1px solid @border; border-radius: 7px;"
                ))
                cl = QVBoxLayout(acc_card)
                cl.setContentsMargins(8, 5, 8, 5)
                cl.setSpacing(3)
                lbl = QLabel(name)
                lbl.setStyleSheet(theme_qss(
                    "font-size: 10px; font-weight: 800; color: @text; border: none;"
                ))
                tgl = AnimatedToggle()
                tgl.setFixedSize(36, 16)
                tgl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.setCursor(Qt.CursorShape.PointingHandCursor)
                lbl.mousePressEvent = lambda event, t=tgl: t.toggle()
                wrap = QHBoxLayout()
                wrap.addStretch()
                wrap.addWidget(tgl)
                wrap.addStretch()
                cl.addWidget(lbl, 0, Qt.AlignmentFlag.AlignCenter)
                cl.addLayout(wrap)
                self.acc_grid.addWidget(acc_card, r, c)
                self.accessory_checkboxes[name] = tgl
                tgl.toggled.connect(self._handle_accessory_toggle_changed)
                c += 1
                if c >= 3:
                    c = 0
                    r += 1
        except Exception as e:
            logger.error("NewServiceDialog reload_accessory_cards error: %s", e)
