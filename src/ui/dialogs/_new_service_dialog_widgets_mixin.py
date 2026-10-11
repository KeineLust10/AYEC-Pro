# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QTextEdit, QSizePolicy, QComboBox, QLineEdit, QDateEdit, QCheckBox, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPen, QFont, QIcon, QPixmap
from decimal import Decimal, InvalidOperation
from src.utils.theme_colors import theme_qss, qc
from src.utils.logger import logger
from src.ui.widgets.animated_toggle import AnimatedToggle


class ServiceSectionGlyph(QWidget):
    def __init__(self, kind, token="finance_primary", parent=None):
        super().__init__(parent)
        self.kind = kind
        self.token = token
        self.setObjectName("serviceReferenceGlyph")
        self.setFixedSize(24, 24)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = qc(self.token)
        fill = qc(self.token)
        fill.setAlpha(24)
        border = qc(self.token)
        border.setAlpha(80)
        painter.setPen(QPen(border, 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(1, 1, 22, 22, 4, 4)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(color, 1.2))
        if self.kind == "customer":
            painter.drawEllipse(6, 5, 6, 6)
            painter.drawArc(4, 13, 11, 9, 0, 180 * 16)
            painter.drawLine(18, 10, 18, 16)
            painter.drawLine(15, 13, 21, 13)
        elif self.kind == "device":
            painter.drawRoundedRect(7, 4, 10, 16, 2, 2)
            painter.drawLine(10, 17, 14, 17)
        elif self.kind == "warning":
            painter.drawLine(12, 4, 3, 19)
            painter.drawLine(3, 19, 21, 19)
            painter.drawLine(21, 19, 12, 4)
            painter.drawLine(12, 9, 12, 13)
            painter.drawPoint(12, 16)
        elif self.kind == "lock":
            painter.drawRoundedRect(6, 11, 12, 9, 2, 2)
            painter.drawArc(8, 5, 8, 12, 0, 180 * 16)
            painter.drawLine(12, 14, 12, 17)
        elif self.kind == "photo":
            painter.drawRoundedRect(4, 7, 16, 12, 2, 2)
            painter.drawRect(8, 5, 5, 2)
            painter.drawEllipse(9, 10, 6, 6)
        elif self.kind == "delivery":
            painter.drawRect(3, 8, 11, 9)
            painter.drawRect(14, 11, 7, 6)
            painter.drawEllipse(5, 16, 4, 4)
            painter.drawEllipse(16, 16, 4, 4)
        else:
            for y in (7, 12, 17):
                painter.drawLine(8, y, 19, y)
                painter.drawPoint(5, y)


class ServiceAcceptGlyph(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(56, 56)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 56, self.height() / 56)
        painter.setPen(QPen(qc("finance_primary"), 1.5))
        painter.setBrush(qc("finance_surface_alt"))
        painter.drawRoundedRect(0, 0, 56, 56, 12, 12)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(qc("finance_primary_text"), 2))
        painter.drawRoundedRect(13, 18, 30, 21, 3, 3)
        painter.drawLine(22, 28, 34, 28)
        painter.drawLine(28, 22, 28, 34)


class ServiceWindowButton(QPushButton):
    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().buttonText().color(), 1.2))
        if self.kind == "minimize":
            painter.drawLine(8, 15, 16, 15)
        else:
            painter.drawRect(8, 8, 8, 8)


class ServiceVoiceButton(QPushButton):
    """Native microphone glyph using the active button palette."""

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().buttonText().color(), 1.4))
        painter.drawRoundedRect(10, 5, 8, 12, 4, 4)
        painter.drawArc(7, 10, 14, 11, 180 * 16, 180 * 16)
        painter.drawLine(14, 21, 14, 24)
        painter.drawLine(10, 24, 18, 24)


class NewServiceDialogWidgetsMixin:
    """Widget helpers, layout utilities, and reload functions (fault toggles, accessories)"""

    def _reference_search_icon(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(qc("@finance_primary"), 1.4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, 8, 8)
        painter.drawLine(9, 9, 14, 14)
        painter.end()
        return QIcon(pixmap)

    def _reference_customer_field_icon(self):
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(qc("@text_muted"), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(5, 2, 6, 6)
        painter.drawArc(2, 8, 12, 9, 0, 180 * 16)
        painter.end()
        return QIcon(pixmap)

    def _wrap_reference_section(self, layout, start, name):
        """Move existing layout items into a card without replacing controls."""
        card = QFrame()
        card.setObjectName(name)
        card.setStyleSheet(theme_qss(f"QFrame#{name} {{ background: @finance_surface; border: 1px solid @finance_outline; border-radius: 6px; }}"))
        if name == "serviceDeviceCard":
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        reference_heights = {
            "serviceCustomerCard": 245,
            "serviceDeviceCard": 357,
            "serviceLockCard": 239,
            "servicePhotoCard": 288,
        }
        if name in reference_heights:
            card.setMinimumHeight(reference_heights[name])
        body = QVBoxLayout(card)
        body.setContentsMargins(0, 14, 0, 12)
        body.setSpacing(10)
        if name == "serviceCustomerCard":
            body.setContentsMargins(0, 0, 0, 0)
            body.setSpacing(6)
        elif name == "serviceDeviceCard":
            body.setContentsMargins(0, 18, 0, 15)
            body.setSpacing(11)
        elif name == "serviceLockCard":
            body.setContentsMargins(0, 12, 0, 8)
            body.setSpacing(8)
        elif name == "servicePhotoCard":
            body.setContentsMargins(0, 14, 0, 8)
            body.setSpacing(8)
        elif name == "serviceFaultCard":
            body.setContentsMargins(0, 4, 0, 4)
            body.setSpacing(4)
        while layout.count() > start:
            item = layout.takeAt(start)
            if item.widget() is not None:
                body.addWidget(item.widget())
            elif item.layout() is not None:
                inner = item.layout()
                inner.setParent(None)
                body.addLayout(inner)
            else:
                body.addItem(item)
        kinds = {
            "serviceCustomerCard": ("customer", "finance_primary"),
            "serviceDeviceCard": ("device", "finance_primary"),
            "serviceFaultCard": ("warning", "warning"),
            "serviceLockCard": ("lock", "finance_primary"),
            "serviceDeliveryCard": ("delivery", "finance_primary"),
            "serviceFaultShortcutsCard": ("list", "finance_primary"),
            "servicePhotoCard": ("photo", "finance_primary"),
        }
        heading = body.itemAt(0).widget() if body.count() else None
        if name in kinds and heading is not None and heading.layout() is not None:
            row = heading.layout()
            last = row.itemAt(row.count() - 1).widget()
            if isinstance(last, QFrame):
                row.removeWidget(last)
                last.hide()
                row.addStretch()
            title = row.itemAt(0).widget()
            if isinstance(title, QLabel):
                title.setStyleSheet(theme_qss("color: @text; font-size: 10px; font-weight: 700; letter-spacing: 0px; border: none; background: transparent;"))
            row.insertWidget(0, ServiceSectionGlyph(*kinds[name], parent=heading))
            heading.setFixedHeight(30)
            if name == "serviceCustomerCard" and isinstance(title, QLabel):
                row.removeWidget(title)
                titles = QVBoxLayout()
                titles.setContentsMargins(0, 0, 0, 0)
                titles.setSpacing(2)
                titles.addWidget(title)
                self.lbl_reference_customer_status = QLabel("Durum: M\u00fc\u015fteri se\u00e7ilmedi")
                self.lbl_reference_customer_status.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px; letter-spacing: 0px; border: none; background: transparent;"))
                titles.addWidget(self.lbl_reference_customer_status)
                row.insertLayout(1, titles)
                heading.setFixedHeight(38)
            elif name in {"serviceDeviceCard", "serviceFaultCard", "servicePhotoCard", "serviceLockCard"}:
                meta_text = "Envanter E\u015fle\u015fmesi: Otomatik" if name == "serviceDeviceCard" else "\u2727 AI Destekli"
                if name == "servicePhotoCard":
                    meta_text = "Maks. 5 Foto\u011fraf"
                elif name == "serviceLockCard":
                    meta_text = "Opsiyonel"
                meta_label = QLabel(meta_text)
                meta_color = "@text_muted" if name == "serviceDeviceCard" else "@warning"
                if name in {"servicePhotoCard", "serviceLockCard"}:
                    meta_color = "@text_muted"
                meta_label.setStyleSheet(theme_qss(
                    "color: " + meta_color + "; font-size: 10px; font-weight: 600; "
                    "border: none; background: transparent;"
                ))
                row.addWidget(meta_label)
            divider = QFrame()
            divider.setFixedHeight(1)
            divider.setStyleSheet(theme_qss("background: @finance_outline; border: none;"))
            body.insertWidget(1, divider)
        layout.addWidget(card)
        return card

    def _capture_reference_form_defaults(self):
        fields = {}
        candidates = dict(vars(self))
        for group in ("sector_service_widgets", "descriptor_service_widgets"):
            candidates.update({group + ":" + name: widget for name, widget in getattr(self, group, {}).items()})
        for name, widget in candidates.items():
            if isinstance(widget, QComboBox):
                fields[name] = ("combo", (widget.currentData(), widget.currentText()))
            elif isinstance(widget, QDateEdit):
                fields[name] = ("date", widget.date())
            elif isinstance(widget, QTextEdit):
                fields[name] = ("multiline", widget.toPlainText())
            elif isinstance(widget, QLineEdit) and not widget.isReadOnly():
                fields[name] = ("text", widget.text())
            elif isinstance(widget, QCheckBox):
                fields[name] = ("check", widget.isChecked())
        self._reference_form_defaults = {
            "fields": fields,
            "toggles": {group: {name: widget.isChecked() for name, widget in getattr(self, group, {}).items()}
                        for group in ("fault_toggles", "accessory_checkboxes")},
            "selected_fault_notes": set(self.selected_fault_notes),
            "fault_note_order": dict(self.fault_note_order),
            "pattern": self.pattern_lock.get_pattern_string(),
            "photo_paths": list(self.photo_paths),
            "photo_labels": list(self.photo_labels),
            "photo_button": (self.btn_photo.text(), self.btn_photo.styleSheet()),
            "estimate_currency": getattr(self, "_estimate_currency", None),
            "estimate_factor": getattr(self, "_estimate_rate_to_base", None),
            "estimate_anchor": (getattr(self, "_estimate_anchor_text", None), getattr(self, "_estimate_anchor_base", None)),
        }

    def _reset_reference_form(self):
        defaults = getattr(self, "_reference_form_defaults", None)
        if defaults is None:
            return
        previous = getattr(self, "_restoring_reference_form", False)
        self._restoring_reference_form = True
        try:
            self._restore_reference_form_values(defaults)
        finally:
            self._restoring_reference_form = previous

    def _restore_reference_form_values(self, defaults):
        if getattr(self, "_fault_voice_worker", None) is not None:
            self._fault_voice_discarded = True
        fields = defaults["fields"]
        priority = ("cmb_service_profile", "cmb_device", "cmb_brand", "cmb_model")
        for name in list(priority) + [key for key in fields if key not in priority]:
            if name not in fields:
                continue
            if ":" in name:
                group, key = name.split(":", 1)
                widget = getattr(self, group, {}).get(key)
            else:
                widget = getattr(self, name, None)
            if widget is None:
                continue
            kind, value = fields[name]
            if kind == "combo":
                data, text = value
                index = widget.findData(data) if data is not None else widget.findText(text)
                widget.setCurrentIndex(index)
                if index < 0 and widget.isEditable():
                    widget.setCurrentText(text)
            elif kind == "date":
                widget.setDate(value)
            elif kind == "multiline":
                widget.setPlainText(value)
            elif kind == "text":
                widget.setText(value)
            elif kind == "check":
                widget.setChecked(value)
        for group, values in defaults["toggles"].items():
            for name, widget in getattr(self, group, {}).items():
                widget.setChecked(values.get(name, False))
        self.selected_fault_notes = set(defaults["selected_fault_notes"])
        self.fault_note_order = dict(defaults["fault_note_order"])
        self._update_fault_selected_label()
        self.pattern_lock.set_pattern_string(defaults["pattern"])
        self.photo_paths = list(defaults["photo_paths"])
        self.photo_labels = list(defaults["photo_labels"])
        self.photo_path = self.photo_paths[0] if self.photo_paths else ""
        self._snapshot_photo_state()
        self._refresh_photo_table()
        self.btn_photo.setText(defaults["photo_button"][0])
        self.btn_photo.setStyleSheet(defaults["photo_button"][1])
        if defaults["estimate_currency"] is not None:
            self._estimate_currency = defaults["estimate_currency"]
            self._estimate_rate_to_base = defaults["estimate_factor"]
            self._estimate_anchor_text, self._estimate_anchor_base = defaults["estimate_anchor"]
            self.estimate_currency_buttons[self._estimate_currency].setChecked(True)


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
        lbl.setFont(QFont("Segoe UI", 9))
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
        l.setFont(QFont("Segoe UI", 9))
        l.setStyleSheet(theme_qss(
            "font-weight: 600; font-size: 11px; color: @text_muted; border: none; background: transparent;"
        ))
        v.addWidget(l)
        if widget is not None:
            if isinstance(widget, QComboBox):
                self._compact_reference_combo(widget)
            if isinstance(widget, QTextEdit) and (
                label_text.startswith("Genel Not") or label_text.startswith("Teknik Not")
            ):
                widget.setStyleSheet(self._note_editor_qss())
            v.addWidget(widget)
        elif layout is not None:
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
                cl = QHBoxLayout(acc_card)
                cl.setContentsMargins(10, 7, 10, 7)
                checkbox = QCheckBox()
                checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
                checkbox.setAccessibleName(name)
                checkbox.setStyleSheet(theme_qss(
                    "QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid @border; "
                    "border-radius: 4px; background: @surface; } "
                    "QCheckBox::indicator:checked { background: @accent; border-color: @accent; }"
                ))
                label = QLabel(name)
                label.setCursor(Qt.CursorShape.PointingHandCursor)
                label.setStyleSheet(theme_qss(
                    "color: @text; font-size: 10px; font-weight: 600; border: none; "
                    "background: transparent;"
                ))
                label.mousePressEvent = lambda event, control=checkbox: control.toggle()
                cl.addWidget(checkbox)
                cl.addWidget(label, 1)
                self.acc_grid.addWidget(acc_card, r, c)
                self.accessory_checkboxes[name] = checkbox
                checkbox.toggled.connect(self._handle_accessory_toggle_changed)
                c += 1
                if c >= 4:
                    c = 0
                    r += 1
        except Exception as e:
            logger.error("NewServiceDialog reload_accessory_cards error: %s", e)
    def _compact_reference_combo(self, combo):
        if self.is_automotive:
            return
        combo.set_reference_chevron()
        is_reference_text_combo = (
            combo is getattr(self, "cmb_customer", None)
            or combo is getattr(self, "cmb_model", None)
        )
        if is_reference_text_combo:
            combo.setProperty("skipThemeTransform", True)
            combo.setStyleSheet(combo.styleSheet() + theme_qss(
                "QComboBox { background: @finance_surface_lowest; color: @finance_text; border-color: @finance_outline; }"))
        combo.setStyleSheet(combo.styleSheet() +
            "QComboBox { min-height: 18px; padding: 2px 8px; border-radius: 4px; font-size: 12px; }")
        combo.setFixedHeight(32)
        editor = combo.lineEdit()
        if editor is not None:
            editor.setMinimumHeight(0)
            editor.setMaximumHeight(34)
            if is_reference_text_combo:
                editor.setProperty("skipThemeTransform", True)
                editor.setStyleSheet(
                    theme_qss("QLineEdit { background: @finance_surface_lowest; color: @finance_text; border: none; ") +
                    "padding: 0; min-height: 0; font-size: 12px; "
                    "selection-background-color: #2563eb; selection-color: #ffffff; }"
                )
            else:
                editor.setStyleSheet(theme_qss(
                    "QLineEdit { background: transparent; color: @text; border: none; "
                    "padding: 0; min-height: 0; font-size: 12px; }"))

    def _estimate_price_in_base(self):
        text = self.inp_est_price.text().strip().replace(",", ".")
        if text == getattr(self, "_estimate_anchor_text", None):
            return self._estimate_anchor_base
        try:
            value = Decimal(text or "0")
        except InvalidOperation as exc:
            raise ValueError("Invalid estimate amount") from exc
        if not value.is_finite() or value < 0:
            raise ValueError("Invalid estimate amount")
        return value * self._estimate_rate_to_base

    def _estimate_local_rate(self, code):
        if code == "TRY":
            return Decimal("1")
        row = self.db.conn.execute(
            "SELECT selling_rate FROM exchange_rates WHERE currency=? "
            "ORDER BY DATE(effective_date) DESC, created_at DESC LIMIT 1", (code,)).fetchone()
        if row is None:
            raise ValueError("Local exchange rate unavailable: " + code)
        rate = Decimal(str(row[0]))
        if not rate.is_finite() or rate <= 0:
            raise ValueError("Invalid local exchange rate: " + code)
        return rate

    def _select_estimate_currency(self, code):
        from src.utils.toast_notification import ToastManager
        if code == self._estimate_currency:
            return
        try:
            base_amount = self._estimate_price_in_base()
            factor = self._estimate_local_rate(code) / self._estimate_local_rate(self._estimate_base_currency)
            display = format(base_amount / factor, ".2f")
        except Exception as exc:
            self.estimate_currency_buttons[self._estimate_currency].setChecked(True)
            ToastManager.warning(self, "Para birimi de\u011fi\u015ftirilemedi: " + str(exc))
            return
        self._estimate_currency = code
        self._estimate_rate_to_base = factor
        self._estimate_anchor_text = display
        self._estimate_anchor_base = base_amount
        self.inp_est_price.setText(display)
        self.estimate_currency_buttons[code].setChecked(True)

    def _build_reference_service_header(self):
        if getattr(self, "_reference_header_built", False):
            return
        self._reference_header_built = True
        header = self.header.layout()
        while header.count():
            header.takeAt(0)
        self.logo_label.hide()
        header.setContentsMargins(12, 0, 12, 0)
        header.setSpacing(8)
        glyph = ServiceAcceptGlyph(self.header)
        glyph.setFixedSize(24, 24)
        header.addWidget(glyph)
        text = QWidget()
        text.setStyleSheet("background: transparent; border: none;")
        text_layout = QVBoxLayout(text)
        text_layout.setContentsMargins(0, 6, 0, 6)
        text_layout.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.setSpacing(6)
        self.lbl_title.setText("YEN\u0130 SERV\u0130S KAYDI OLU\u015eTUR")
        self.lbl_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(theme_qss("color: @text; border: none; background: transparent; font-size: 14px; letter-spacing: 0px; font-weight: 700;"))
        title_row.addWidget(self.lbl_title)
        self.lbl_service_accept_badge = QLabel("Servis Kabul v3.4")
        self.lbl_service_accept_badge.setStyleSheet(theme_qss(
            "color: @finance_primary; background: @finance_surface_alt; border: 1px solid @finance_outline; "
            "border-radius: 6px; padding: 2px 6px; font-size: 10px; letter-spacing: 0px;"))
        title_row.addWidget(self.lbl_service_accept_badge)
        title_row.addStretch()
        text_layout.addLayout(title_row)
        self.lbl_service_accept_subtitle = QLabel("M\u00fc\u015fteri kabul\u00fc, donan\u0131m kontrol\u00fc ve i\u015f emri olu\u015fturma formu")
        self.lbl_service_accept_subtitle.setStyleSheet(theme_qss("color: @text_muted; background: transparent; border: none; font-size: 11px; letter-spacing: 0px;"))
        text_layout.addWidget(self.lbl_service_accept_subtitle)
        header.addWidget(text, 1)
        self.btn_reference_minimize = ServiceWindowButton("minimize")
        self.btn_reference_minimize.setToolTip("K\u00fc\u00e7\u00fclt")
        self.btn_reference_minimize.clicked.connect(self.showMinimized)
        self.btn_reference_maximize = ServiceWindowButton("maximize")
        self.btn_reference_maximize.setToolTip("B\u00fcy\u00fct / Geri Al")
        self.btn_reference_maximize.clicked.connect(lambda: self.showNormal() if self.isMaximized() else self.showMaximized())
        self.btn_close.setText("\u00d7")
        for button in (self.btn_reference_minimize, self.btn_reference_maximize):
            button.setFixedSize(28, 28)
            button.show()
            header.addWidget(button)
        close_hint = QLabel("ESC  ile kapat")
        close_hint.setFixedSize(140, 36)
        close_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        close_hint.setStyleSheet(theme_qss(
            "color: @text_muted; background: @finance_surface_alt; border: 1px solid @finance_outline; "
            "border-radius: 5px; padding: 5px 9px; font-family: 'Consolas'; font-size: 10px; "
            "letter-spacing: 0px;"
        ))
        close_hint.hide()
        header.addWidget(close_hint)
        for button in (self.btn_close,):
            button.setFixedSize(28, 28)
            button.setStyleSheet(theme_qss("QPushButton { background: transparent; color: @text_muted; border: none; border-radius: 4px; padding: 0; font-size: 14px; } QPushButton:hover { background: @finance_surface_alt; }"))
            header.addWidget(button)
