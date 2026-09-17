
# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QGridLayout, QDateEdit, QTextEdit, QCheckBox, QFrame, QVBoxLayout, QHBoxLayout, QComboBox
from PyQt6.QtCore import QDate
from src.utils.theme_colors import theme_qss
from src.ui.widgets.modern_inputs import ValidatedLineEdit, ModernComboBox
from src.utils.logger import logger


class NewServiceDialogSectorMixin:
    """Sector fields, descriptor fields, and value handling"""

    def _active_sector_id(self):
        if getattr(self, "SECTOR_ID", None):
            return self.SECTOR_ID
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                return self.sector_manager.get_current_plugin().sector_id
        except Exception:
            pass
        return "otomotiv" if getattr(self, "is_automotive", False) else "teknik_servis"

    def _build_sector_service_fields(self):
        visible_dynamic_fields = []
        builtin_names = {"vehicle_plate", "vehicle_vin", "device_type", "serial_no"}
        for field in self.sector_service_fields:
            if field.get("name") in builtin_names:
                continue
            visible_dynamic_fields.append(field)
        if not visible_dynamic_fields:
            return None

        wrapper = QGridLayout()
        wrapper.setSpacing(8)
        for index, field in enumerate(visible_dynamic_fields):
            title = field.get("title", field.get("name", "Alan"))
            if field.get("required"):
                title = f"{title} *"
            if str(field.get("type", "text")).lower() == "select":
                widget = ModernComboBox(items=field.get("options", []), editable=True)
            else:
                widget = ValidatedLineEdit(field.get("placeholder", "") or title)
            widget.setMinimumHeight(36)
            self.sector_service_widgets[field["name"]] = widget
            wrapper.addLayout(self.create_field_box(title, widget), index // 2, index % 2)
        return wrapper

    def _create_descriptor_widget(self, field):
        field_type = str(field.get("type", "text") or "text").lower()
        if field_type == "select":
            widget = ModernComboBox(items=field.get("options", []), editable=True)
            widget.setMinimumHeight(36)
            return widget
        if field_type == "multiline":
            widget = QTextEdit()
            widget.setPlaceholderText(field.get("placeholder", "") or field.get("title", ""))
            widget.setFixedHeight(86)
            widget.setStyleSheet(theme_qss(
                "border: 1px solid @border; border-radius: 6px; padding: 6px 8px; font-size: 11px; background: @surface;"
            ))
            return widget
        if field_type == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setMinimumHeight(36)
            return widget
        if field_type == "checkbox":
            widget = QCheckBox(field.get("title", ""))
            widget.setStyleSheet(theme_qss("color: @text; font-weight: 700;"))
            return widget
        widget = ValidatedLineEdit(field.get("placeholder", "") or field.get("title", ""))
        widget.setMinimumHeight(36)
        return widget

    def _build_descriptor_service_sections(self):
        sections = []
        skip_names = {"vehicle_plate", "vehicle_vin", "device_type", "serial_no", "current_km", "service_type"}
        for section in self.service_form_descriptors:
            visible_fields = []
            for field in section.get("fields", []):
                if field.get("name") in skip_names:
                    continue
                visible_fields.append(field)
            if not visible_fields:
                continue
            container = QVBoxLayout()
            container.setSpacing(8)
            container.addWidget(self._sec(str(section.get("title", "Ek Alanlar")).upper()))
            grid = QGridLayout()
            grid.setSpacing(8)
            grid_row = 0
            grid_col = 0
            for field in visible_fields:
                title = field.get("title", field.get("name", "Alan"))
                widget = self._create_descriptor_widget(field)
                self.descriptor_service_widgets[field["name"]] = widget
                if str(field.get("type", "")).lower() == "checkbox":
                    holder = QFrame()
                    row_lay = QHBoxLayout(holder)
                    row_lay.setContentsMargins(0, 0, 0, 0)
                    row_lay.addWidget(widget)
                    row_lay.addStretch()
                    grid.addWidget(holder, grid_row, 0, 1, 2)
                    grid_row += 1
                    grid_col = 0
                    continue
                grid.addLayout(self.create_field_box(title, widget), grid_row, grid_col)
                grid_col += 1
                if grid_col >= 2:
                    grid_col = 0
                    grid_row += 1
            container.addLayout(grid)
            sections.append(container)
        return sections

    def _collect_sector_service_values(self):
        values = {
            "device_type": self.cmb_device.currentText().strip() if hasattr(self, "cmb_device") else "",
            "serial_no": self.inp_serial.text().strip() if hasattr(self, "inp_serial") else "",
            "vehicle_plate": self.inp_vehicle_plate.text().strip().upper() if hasattr(self, "inp_vehicle_plate") else "",
            "vehicle_vin": self.inp_vehicle_vin.text().strip().upper() if hasattr(self, "inp_vehicle_vin") else "",
        }
        for name, widget in self.sector_service_widgets.items():
            if isinstance(widget, (ModernComboBox, QComboBox)):
                values[name] = widget.currentText().strip()
            else:
                values[name] = widget.text().strip()
        return values

    def _set_sector_service_values(self, payload):
        if hasattr(self, "inp_vehicle_plate"):
            self.inp_vehicle_plate.setText(str(payload.get("vehicle_plate", "") or ""))
        if hasattr(self, "inp_vehicle_vin"):
            self.inp_vehicle_vin.setText(str(payload.get("vehicle_vin", "") or ""))
        if hasattr(self, "inp_serial"):
            self.inp_serial.setText(str(payload.get("serial_no", self.inp_serial.text()) or ""))
        if hasattr(self, "cmb_device") and payload.get("device_type"):
            self.cmb_device.setCurrentText(str(payload.get("device_type")))
        for name, widget in self.sector_service_widgets.items():
            value = payload.get(name, "")
            if isinstance(widget, (ModernComboBox, QComboBox)):
                widget.setCurrentText("" if value is None else str(value))
            else:
                widget.setText("" if value is None else str(value))

    def _collect_descriptor_service_values(self):
        values = {}
        for name, widget in self.descriptor_service_widgets.items():
            if isinstance(widget, (ModernComboBox, QComboBox)):
                values[name] = widget.currentText().strip()
            elif isinstance(widget, QTextEdit):
                values[name] = widget.toPlainText().strip()
            elif isinstance(widget, QDateEdit):
                values[name] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QCheckBox):
                values[name] = widget.isChecked()
            else:
                values[name] = widget.text().strip()
        return values

    def _set_descriptor_service_values(self, payload):
        for name, widget in self.descriptor_service_widgets.items():
            value = payload.get(name)
            if name == "approval_status" and value:
                try:
                    plugin = self.sector_manager.get_current_plugin() if self.sector_manager else None
                    if plugin and hasattr(plugin, "approval_db_to_label"):
                        value = plugin.approval_db_to_label(value)
                except Exception:
                    pass
            if isinstance(widget, (ModernComboBox, QComboBox)):
                widget.setCurrentText("" if value is None else str(value))
            elif isinstance(widget, QTextEdit):
                widget.setPlainText("" if value is None else str(value))
            elif isinstance(widget, QDateEdit):
                text = str(value or "").strip()
                if text:
                    parsed = QDate.fromString(text[:10], "yyyy-MM-dd")
                    if parsed.isValid():
                        widget.setDate(parsed)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(value))
            else:
                widget.setText("" if value is None else str(value))

