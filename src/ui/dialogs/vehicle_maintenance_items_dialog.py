from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import QCheckBox, QDateEdit, QGridLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


class VehicleMaintenanceItemsDialog(ModernDialog):
    ITEM_DEFS = [
        {"type": "oil_change", "label": "Yag Degisimi", "days": 90, "km": 10000},
        {"type": "oil_filter", "label": "Yag Filtresi", "days": 90, "km": 10000},
        {"type": "air_filter", "label": "Hava Filtresi", "days": 180, "km": 15000},
        {"type": "cabin_filter", "label": "Polen Filtresi", "days": 180, "km": 15000},
        {"type": "glass_water", "label": "Cam Suyu", "days": 30, "km": 0},
        {"type": "antifreeze", "label": "Antifriz", "days": 365, "km": 30000},
        {"type": "brake_fluid", "label": "Fren Hidroligi", "days": 365, "km": 40000},
        {"type": "spark_plugs", "label": "Buji Kontrolu", "days": 365, "km": 30000},
        {"type": "timing_belt", "label": "Triger Kayisi", "days": 730, "km": 90000},
        {"type": "timing_chain", "label": "Triger Zinciri", "days": 1095, "km": 120000},
    ]

    def __init__(self, service_date, current_odometer, items=None, parent=None, item_defs=None):
        super().__init__("Bakim Kalemleri", parent, width=1180, height=760)
        self.service_date = service_date
        self.current_odometer = int(current_odometer or 0)
        self.widgets = {}
        self.initial_items = {
            (item.get("item_type") or item.get("item_key")): item
            for item in (items or [])
        }
        self.result_items = list(items or [])
        self.item_defs = list(item_defs or self.ITEM_DEFS)
        self.set_wheel_scroll_enabled(True)
        self._build_ui()

    def _build_ui(self):
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        intro = QLabel("Bakim kalemlerini bu ekrandan secin. Kaydedince ana forma otomatik ozet doner.")
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        root.addWidget(intro)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        headers = ["Kalem", "Yapildi", "Periyot (Gun)", "Periyot (KM)", "Sonraki Tarih", "Sonraki KM"]
        for col, header in enumerate(headers):
            hdr = QLabel(header)
            hdr.setStyleSheet(theme_qss("font-weight: 700; color: @text_muted;"))
            grid.addWidget(hdr, 0, col)

        base_date = self.service_date if isinstance(self.service_date, QDate) else QDate.currentDate()
        for row_idx, item_def in enumerate(self.item_defs, start=1):
            existing = self.initial_items.get(item_def["type"], {})
            lbl = QLabel(item_def["label"])
            chk = QCheckBox()
            chk.setChecked(bool(
                existing.get("performed") if "performed" in existing
                else existing.get("completed", True)
            ))

            spn_days = QSpinBox()
            spn_days.setRange(0, 3650)
            spn_days.setSingleStep(30)
            spn_days.setValue(int(existing.get("interval_days") or item_def["days"]))

            spn_km = QSpinBox()
            spn_km.setRange(0, 300000)
            spn_km.setSingleStep(5000)
            spn_km.setValue(int(existing.get("interval_km") or item_def["km"]))

            due_date = QDateEdit(base_date.addDays(spn_days.value()))
            due_date.setCalendarPopup(True)
            if existing.get("next_due_date"):
                due_date.setDate(QDate.fromString(existing["next_due_date"], "yyyy-MM-dd"))

            due_km = QSpinBox()
            due_km.setRange(0, 999999)
            due_km.setSingleStep(5000)
            due_km.setValue(int(existing.get("next_due_odometer") or (self.current_odometer + spn_km.value())))

            chk.toggled.connect(lambda _=None: self._sync_due_targets())
            spn_days.valueChanged.connect(lambda _=None: self._sync_due_targets())
            spn_km.valueChanged.connect(lambda _=None: self._sync_due_targets())

            grid.addWidget(lbl, row_idx, 0)
            grid.addWidget(chk, row_idx, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(spn_days, row_idx, 2)
            grid.addWidget(spn_km, row_idx, 3)
            grid.addWidget(due_date, row_idx, 4)
            grid.addWidget(due_km, row_idx, 5)
            self.widgets[item_def["type"]] = {
                "label": item_def["label"],
                "check": chk,
                "days": spn_days,
                "km": spn_km,
                "date": due_date,
                "next_km": due_km,
            }

        root.addLayout(grid)
        self.add_widget(body)
        self.add_cancel_button("Iptal")
        self.add_button("Bakim Kalemlerini Kaydet", "success", self._accept_items)
        self.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self._sync_due_targets()

    def _sync_due_targets(self):
        base_date = self.service_date if isinstance(self.service_date, QDate) else QDate.currentDate()
        for widget_map in self.widgets.values():
            if widget_map["check"].isChecked():
                widget_map["date"].setDate(base_date.addDays(widget_map["days"].value()))
                widget_map["next_km"].setValue(self.current_odometer + widget_map["km"].value())

    def _accept_items(self):
        items = []
        for item_type, widget_map in self.widgets.items():
            if not widget_map["check"].isChecked():
                continue
            items.append(
                {
                    "item_type": item_type,
                    "item_label": widget_map["label"],
                    "performed": True,
                    "interval_days": widget_map["days"].value(),
                    "interval_km": widget_map["km"].value(),
                    "next_due_date": widget_map["date"].date().toString("yyyy-MM-dd"),
                    "next_due_odometer": widget_map["next_km"].value(),
                    "notes": "",
                }
            )
        self.result_items = items
        self.accept()
