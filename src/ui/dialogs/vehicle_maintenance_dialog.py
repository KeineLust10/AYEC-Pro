# -*- coding: utf-8 -*-

from PyQt6.QtCore import QDate, QTime, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from src.ui.dialogs.vehicle_maintenance_items_dialog import VehicleMaintenanceItemsDialog
from src.ui.dialogs.vehicle_maintenance_photo_gallery_dialog import VehicleMaintenancePhotoGalleryDialog
from src.ui.dialogs.vehicle_history_qr_dialog import VehicleHistoryQrDialog
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning



class VehicleMaintenanceDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    VEHICLE_CATALOG = {
        "Ford": ["Courier", "Connect", "Focus", "Fiesta", "Transit"],
        "Fiat": ["Doblo", "Egea", "Fiorino", "Linea"],
        "Renault": ["Clio", "Fluence", "Kangoo", "Megane", "Symbol"],
        "Volkswagen": ["Caddy", "Golf", "Jetta", "Passat", "Polo", "Transporter"],
        "Peugeot": ["208", "301", "308", "Partner", "Rifter"],
        "Toyota": ["Corolla", "Hilux", "RAV4", "Yaris"],
        "Hyundai": ["Accent", "i10", "i20", "i30", "Tucson"],
        "Opel": ["Astra", "Combo", "Corsa", "Insignia"],
    }
    VEHICLE_TYPES = ["Binek", "Hafif Ticari", "SUV", "Minivan", "Kamyonet", "Motosiklet", "Diger"]
    ENGINE_TYPES = ["Benzinli", "Dizel", "Hibrit", "Elektrikli", "LPG", "Turbo Dizel", "Diger"]
    FUEL_TYPES = ["Benzin", "Dizel", "LPG", "Elektrik", "Hibrit", "Diger"]

    def __init__(self, db, parent=None, card_id=None, sector_manager=None):
        self.db = db
        self.sector_manager = sector_manager
        self.maintenance_sections = self.sector_manager.get_maintenance_card_sections() if self.sector_manager else []
        self.customer_rows = list(self.db.get_customers() or [])
        self.vehicle_rows = []
        self.selected_items = []
        self.card_id = card_id
        self.saved_card_id = card_id
        super().__init__("Arac Bakim Karti", parent, width=1340, height=840)
        self.set_wheel_scroll_enabled(True)
        self._build_ui()
        if self.card_id:
            self._load_existing_card(self.card_id)

    def _build_ui(self):
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)

        intro = QLabel("Bakim ana formunu sade tutun. Bakim kalemleri ve galeri ayri araclarla yonetilir.")
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        root.addWidget(intro)

        top = QGridLayout()
        top.setHorizontalSpacing(16)
        top.setVerticalSpacing(12)

        left_card = self._make_card()
        left_wrap = QVBoxLayout(left_card)
        left_wrap.setContentsMargins(18, 18, 18, 18)
        left_wrap.setSpacing(10)
        left_wrap.addWidget(self._title_label("Musteri ve Arac Bilgisi"))
        left_form = QFormLayout()
        left_form.setSpacing(12)

        customer_layout = QHBoxLayout()
        customer_layout.setSpacing(6)
        customer_layout.setContentsMargins(0, 0, 0, 0)
        self.cmb_customer = QComboBox()
        self.cmb_customer.addItem("Musteri secin", None)
        for row in self.customer_rows:
            try:
                self.cmb_customer.addItem(row[1], row[0])
            except Exception:
                continue
        self.cmb_customer.currentIndexChanged.connect(self._reload_customer_vehicles)

        self.btn_add_customer_shortcut = QPushButton("+")
        self.btn_add_customer_shortcut.setFixedSize(30, 30)
        self.btn_add_customer_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_customer_shortcut.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: 1px solid @border;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        self.btn_add_customer_shortcut.clicked.connect(self._add_customer_shortcut)
        customer_layout.addWidget(self.cmb_customer, 1)
        customer_layout.addWidget(self.btn_add_customer_shortcut)

        vehicle_layout = QHBoxLayout()
        vehicle_layout.setSpacing(6)
        vehicle_layout.setContentsMargins(0, 0, 0, 0)
        self.cmb_vehicle = QComboBox()
        self.cmb_vehicle.addItem("Musteriye ait arac secin", None)
        self.cmb_vehicle.currentIndexChanged.connect(self._apply_vehicle_selection)

        self.btn_add_vehicle_shortcut = QPushButton("+")
        self.btn_add_vehicle_shortcut.setFixedSize(30, 30)
        self.btn_add_vehicle_shortcut.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_vehicle_shortcut.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: 1px solid @border;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        self.btn_add_vehicle_shortcut.clicked.connect(self._add_vehicle_shortcut)
        vehicle_layout.addWidget(self.cmb_vehicle, 1)
        vehicle_layout.addWidget(self.btn_add_vehicle_shortcut)

        self.inp_plate = QLineEdit()
        self.inp_plate.editingFinished.connect(self._lookup_plate)

        self.cmb_brand = QComboBox()
        self.cmb_brand.setEditable(True)
        self.cmb_brand.addItem("Marka secin")
        self.cmb_brand.addItems(sorted(self.VEHICLE_CATALOG.keys()))
        self.cmb_brand.currentTextChanged.connect(self._refresh_model_combo)

        self.cmb_model = QComboBox()
        self.cmb_model.setEditable(True)
        self.cmb_model.addItem("Model secin")

        self.cmb_year = QComboBox()
        self.cmb_year.addItem("Yil secin")
        for year in range(QDate.currentDate().year() + 1, 1989, -1):
            self.cmb_year.addItem(str(year))

        self.cmb_vehicle_type = QComboBox()
        self.cmb_vehicle_type.addItems(self.VEHICLE_TYPES)
        self.cmb_engine_type = QComboBox()
        self.cmb_engine_type.addItems(self.ENGINE_TYPES)
        self.cmb_fuel_type = QComboBox()
        self.cmb_fuel_type.addItems(self.FUEL_TYPES)

        self.inp_odometer = QLineEdit("0")

        left_form.addRow("Musteri", customer_layout)
        left_form.addRow("Arac", vehicle_layout)
        left_form.addRow("Plaka", self.inp_plate)
        left_form.addRow("Marka", self.cmb_brand)
        left_form.addRow("Model", self.cmb_model)
        left_form.addRow("Yil", self.cmb_year)
        left_form.addRow("Arac Tipi", self.cmb_vehicle_type)
        left_form.addRow("Motor Tipi", self.cmb_engine_type)
        left_form.addRow("Yakit Turu", self.cmb_fuel_type)
        left_form.addRow("KM", self.inp_odometer)
        left_wrap.addLayout(left_form)

        right_card = self._make_card()
        right_wrap = QVBoxLayout(right_card)
        right_wrap.setContentsMargins(18, 18, 18, 18)
        right_wrap.setSpacing(10)
        right_wrap.addWidget(self._title_label("Bakim Tarihi ve Randevu"))
        right_form = QFormLayout()
        right_form.setSpacing(12)

        self.date_service = QDateEdit(QDate.currentDate())
        self.date_service.setCalendarPopup(True)
        self.date_service.dateChanged.connect(self._sync_dates)
        self.date_next = QDateEdit(QDate.currentDate().addDays(90))
        self.date_next.setCalendarPopup(True)
        self.date_manual_appt = QDateEdit(QDate.currentDate().addDays(90))
        self.date_manual_appt.setCalendarPopup(True)
        self.time_appt = QTimeEdit(QTime(9, 0))
        self.time_appt.setDisplayFormat("HH:mm")
        self.date_inspection = QDateEdit(QDate.currentDate().addYears(1))
        self.date_inspection.setCalendarPopup(True)

        right_form.addRow("Bakim Tarihi", self.date_service)
        right_form.addRow("Sonraki Bakim", self.date_next)
        right_form.addRow("Randevu Tarihi", self.date_manual_appt)
        right_form.addRow("Randevu Saati", self.time_appt)
        right_form.addRow("Muayene Tarihi", self.date_inspection)
        right_wrap.addLayout(right_form)
        self.lbl_whatsapp = QLabel("Hatirlatma bir gun once zil, asistan ve WhatsApp uzerinden tetiklenir.")
        self.lbl_whatsapp.setStyleSheet(theme_qss("color: @success; font-size: 12px; font-weight: 700;"))
        right_wrap.addWidget(self.lbl_whatsapp)

        top.addWidget(left_card, 0, 0)
        top.addWidget(right_card, 0, 1)
        root.addLayout(top)

        item_card = self._make_card()
        item_wrap = QVBoxLayout(item_card)
        item_wrap.setContentsMargins(18, 18, 18, 18)
        item_wrap.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(self._title_label("Bakim Kalemleri Formu"))
        header.addStretch()
        btn_items = QPushButton("Bakim Karti Ekle")
        btn_items.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_items.clicked.connect(self._open_items_dialog)
        self.btn_gallery = QPushButton("Galeriyi Ac")
        self.btn_gallery.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_gallery.clicked.connect(self._open_gallery)
        self.btn_gallery.setEnabled(bool(self.saved_card_id))
        self.btn_history = QPushButton("QR / Gecmis")
        self.btn_history.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_history.clicked.connect(self._open_history_qr)
        self.btn_history.setEnabled(bool(self.saved_card_id))
        header.addWidget(self.btn_gallery)
        header.addWidget(self.btn_history)
        header.addWidget(btn_items)
        item_wrap.addLayout(header)

        self.lbl_item_summary = QLabel("Henüz bakım kalemi seçilmedi.")
        self.lbl_item_summary.setWordWrap(True)
        self.lbl_item_summary.setStyleSheet(theme_qss("color: @text; font-size: 13px;"))
        item_wrap.addWidget(self.lbl_item_summary)
        self.lbl_section_summary = QLabel(self._build_section_summary_text())
        self.lbl_section_summary.setWordWrap(True)
        self.lbl_section_summary.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        item_wrap.addWidget(self.lbl_section_summary)
        root.addWidget(item_card)

        notes_card = self._make_card()
        notes_wrap = QVBoxLayout(notes_card)
        notes_wrap.setContentsMargins(18, 18, 18, 18)
        notes_wrap.setSpacing(10)
        notes_wrap.addWidget(self._title_label("Notlar"))
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(120)
        notes_wrap.addWidget(self.txt_notes)
        root.addWidget(notes_card)

        self.add_widget(body)
        self.add_cancel_button("Iptal")
        self.add_button("Taslak Randevu ve Karti Olustur", "success", self._save)
        self._sync_dates()

    @staticmethod
    def _row_value(row, key, default=None):
        if row is None:
            return default
        try:
            return row[key]
        except Exception:
            return default

    def _load_existing_card(self, card_id):
        try:
            card, items = self.db.get_vehicle_maintenance_card(card_id)
        except Exception:
            card, items = None, []
        if not card:
            return

        customer_id = card["customer_id"]
        customer_index = self.cmb_customer.findData(customer_id)
        if customer_index >= 0:
            self.cmb_customer.setCurrentIndex(customer_index)
            self._reload_customer_vehicles()

        vehicle_id = card["vehicle_id"]
        if vehicle_id is not None:
            vehicle_index = self.cmb_vehicle.findData(vehicle_id)
            if vehicle_index >= 0:
                self.cmb_vehicle.setCurrentIndex(vehicle_index)

        self.inp_plate.setText(str(card["vehicle_plate"] or ""))
        self.cmb_brand.setCurrentText(str(card["vehicle_brand"] or ""))
        self._refresh_model_combo(self.cmb_brand.currentText())
        self.cmb_model.setCurrentText(str(card["vehicle_model"] or ""))
        self.cmb_year.setCurrentText(str(card["vehicle_year"] or ""))
        if card["vehicle_type"]:
            self.cmb_vehicle_type.setCurrentText(str(card["vehicle_type"]))
        if card["engine_type"]:
            self.cmb_engine_type.setCurrentText(str(card["engine_type"]))
        if card["fuel_type"]:
            self.cmb_fuel_type.setCurrentText(str(card["fuel_type"]))
        self.inp_odometer.setText(str(card["odometer"] or "0"))

        if card["service_date"]:
            parsed = QDate.fromString(str(card["service_date"]), "yyyy-MM-dd")
            if parsed.isValid():
                self.date_service.setDate(parsed)
        if card["next_maintenance_date"]:
            parsed = QDate.fromString(str(card["next_maintenance_date"]), "yyyy-MM-dd")
            if parsed.isValid():
                self.date_next.setDate(parsed)
        manual_appt = card["manual_appointment_date"] or card["appointment_date"]
        if manual_appt:
            parsed = QDate.fromString(str(manual_appt), "yyyy-MM-dd")
            if parsed.isValid():
                self.date_manual_appt.setDate(parsed)
        if card["appointment_time"]:
            parsed_time = QTime.fromString(str(card["appointment_time"]), "HH:mm")
            if parsed_time.isValid():
                self.time_appt.setTime(parsed_time)
        if card["inspection_due_date"]:
            parsed = QDate.fromString(str(card["inspection_due_date"]), "yyyy-MM-dd")
            if parsed.isValid():
                self.date_inspection.setDate(parsed)

        self.txt_notes.setPlainText(str(card["notes"] or ""))
        self.selected_items = []
        for item in items or []:
            item_key = str(
                self._row_value(item, "item_key", "")
                or self._row_value(item, "item_label", "")
                or ""
            )
            item_label = str(
                self._row_value(item, "item_label", "")
                or self._row_value(item, "item_key", "")
                or ""
            )
            self.selected_items.append(
                {
                    "item_type": item_key,
                    "item_label": item_label,
                    "completed": bool(
                        self._row_value(
                            item,
                            "completed",
                            self._row_value(item, "performed", 1),
                        )
                    ),
                    "interval_days": int(self._row_value(item, "interval_days", 0) or 0),
                    "interval_km": int(self._row_value(item, "interval_km", 0) or 0),
                    "next_due_date": str(self._row_value(item, "next_due_date", "") or ""),
                    "next_due_odometer": int(self._row_value(item, "next_due_odometer", 0) or 0),
                    "notes": str(self._row_value(item, "notes", "") or ""),
                }
            )
        self.btn_gallery.setEnabled(True)
        self.btn_history.setEnabled(True)
        self._refresh_item_summary()

    def _make_card(self):
        frame = QFrame()
        frame.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        return frame

    def _title_label(self, title):
        label = QLabel(title)
        label.setStyleSheet(theme_qss("font-size: 15px; font-weight: 800; color: @text;"))
        return label

    def _sync_dates(self):
        self.date_next.setDate(self.date_service.date().addDays(90))
        self.date_manual_appt.setDate(self.date_next.date())
        if not self.date_inspection.date().isValid():
            self.date_inspection.setDate(self.date_service.date().addYears(1))

    def _reload_customer_vehicles(self):
        customer_id = self.cmb_customer.currentData()
        self.vehicle_rows = list(self.db.get_customer_vehicles(customer_id) or []) if customer_id else []
        self.cmb_vehicle.blockSignals(True)
        self.cmb_vehicle.clear()
        self.cmb_vehicle.addItem("Musteriye ait arac secin", None)
        for row in self.vehicle_rows:
            label = f"{row['plate']} | {row['brand'] or '-'} {row['model'] or ''}".strip()
            self.cmb_vehicle.addItem(label, row["id"])
        self.cmb_vehicle.blockSignals(False)

    def _apply_vehicle_selection(self):
        vehicle_id = self.cmb_vehicle.currentData()
        if not vehicle_id:
            return
        row = next((row for row in self.vehicle_rows if row["id"] == vehicle_id), None)
        if row:
            self._apply_vehicle_row(row)

    def _apply_vehicle_row(self, row):
        self.inp_plate.setText(str(row["plate"] or ""))
        self.cmb_brand.setCurrentText(str(row["brand"] or ""))
        self._refresh_model_combo(self.cmb_brand.currentText())
        self.cmb_model.setCurrentText(str(row["model"] or ""))
        self.cmb_year.setCurrentText(str(row["year"] or ""))
        self.cmb_vehicle_type.setCurrentText(str(row["vehicle_type"] or self.cmb_vehicle_type.currentText()))
        self.cmb_engine_type.setCurrentText(str(row["engine_type"] or self.cmb_engine_type.currentText()))
        self.cmb_fuel_type.setCurrentText(str(row["fuel_type"] or self.cmb_fuel_type.currentText()))
        self.inp_odometer.setText(str(row["last_known_odometer"] or "0"))
        try:
            inspection_due = str(row["inspection_due_date"] or "")
        except Exception:
            inspection_due = ""
        parsed = QDate.fromString(inspection_due, "yyyy-MM-dd")
        if parsed.isValid():
            self.date_inspection.setDate(parsed)
        self.btn_history.setEnabled(bool(self.inp_plate.text().strip()))

    def _lookup_plate(self):
        plate = self.inp_plate.text().strip().upper()
        if not plate:
            return
        row = self.db.get_customer_vehicle_by_plate(plate)
        if not row:
            return
        try:
            customer_id = row["customer_id"]
            if customer_id:
                index = self.cmb_customer.findData(customer_id)
                if index >= 0:
                    self.cmb_customer.setCurrentIndex(index)
        except Exception:
            pass
        self._apply_vehicle_row(row)

    def _refresh_model_combo(self, brand_text):
        current_model = self.cmb_model.currentText().strip()
        self.cmb_model.blockSignals(True)
        self.cmb_model.clear()
        self.cmb_model.addItem("Model secin")
        for model in sorted(self.VEHICLE_CATALOG.get(brand_text.strip(), [])):
            self.cmb_model.addItem(model)
        if current_model and self.cmb_model.findText(current_model) >= 0:
            self.cmb_model.setCurrentText(current_model)
        self.cmb_model.blockSignals(False)

    def _open_items_dialog(self):
        try:
            current_km = int(float((self.inp_odometer.text().strip() or "0").replace(",", ".")))
        except Exception:
            current_km = 0
        dlg = VehicleMaintenanceItemsDialog(
            self.date_service.date(),
            current_km,
            self.selected_items,
            self,
            item_defs=self._maintenance_item_defs(),
        )
        if dlg.exec():
            self.selected_items = list(dlg.result_items or [])
            self._refresh_item_summary()

    def _maintenance_item_defs(self):
        if not self.maintenance_sections:
            return None
        items = []
        for section in self.maintenance_sections:
            for item in section.get("items", []):
                items.append(
                    {
                        "type": item.get("type"),
                        "label": item.get("label"),
                        "days": int(item.get("days", 90) or 90),
                        "km": int(item.get("km", 0) or 0),
                    }
                )
        return items or None

    def _build_section_summary_text(self):
        if not self.maintenance_sections:
            return "Bakim kalemleri sabit varsayilan set ile yonetilir."
        parts = []
        for section in self.maintenance_sections:
            title = str(section.get("title", "") or "").strip()
            description = str(section.get("description", "") or "").strip()
            if not title:
                continue
            parts.append(f"{title}: {description}" if description else title)
        return " | ".join(parts) if parts else "Bakim kalemleri plugin section yapisindan besleniyor."

    def _refresh_item_summary(self):
        if not self.selected_items:
            self.lbl_item_summary.setText("Henüz bakım kalemi seçilmedi.")
            return
        labels = ", ".join(item["item_label"] for item in self.selected_items[:4])
        suffix = "" if len(self.selected_items) <= 4 else f" ve {len(self.selected_items) - 4} kalem daha"
        nearest_date = min((item.get("next_due_date") for item in self.selected_items if item.get("next_due_date")), default="-")
        nearest_km = min((int(item.get("next_due_odometer") or 0) for item in self.selected_items if int(item.get("next_due_odometer") or 0) > 0), default=0)
        self.lbl_item_summary.setText(
            f"Secili {len(self.selected_items)} kalem: {labels}{suffix}\n"
            f"En yakin tarih: {nearest_date} | En yakin KM: {nearest_km if nearest_km else '-'}"
        )

    def _open_gallery(self):
        if not self.saved_card_id:
            show_warning(self, "Galeri icin once bakim kartini kaydetmeniz gerekiyor.")
            return
        dlg = VehicleMaintenancePhotoGalleryDialog(self.db, self.saved_card_id, self.inp_plate.text().strip(), self)
        dlg.exec()

    def _save(self):
        customer_id = self.cmb_customer.currentData()
        plate = self.inp_plate.text().strip().upper()
        if not customer_id or not plate:
            show_warning(self, "Musteri ve plaka zorunludur.")
            return
        if not self.selected_items:
            show_warning(self, "En az bir bakim kalemi secin.")
            return
        try:
            odometer = int(float((self.inp_odometer.text().strip() or "0").replace(",", ".")))
        except Exception:
            show_warning(self, "KM alani sayisal olmali.")
            return

        vehicle_id = self.cmb_vehicle.currentData()
        card_data = {
            "id": self.card_id,
            "vehicle_id": vehicle_id,
            "customer_id": customer_id,
            "customer_name": self.cmb_customer.currentText().strip(),
            "vehicle_plate": plate,
            "vehicle_brand": self.cmb_brand.currentText().replace("Marka secin", "").strip(),
            "vehicle_model": self.cmb_model.currentText().replace("Model secin", "").strip(),
            "vehicle_year": self.cmb_year.currentText().replace("Yil secin", "").strip(),
            "vehicle_type": self.cmb_vehicle_type.currentText().strip(),
            "engine_type": self.cmb_engine_type.currentText().strip(),
            "fuel_type": self.cmb_fuel_type.currentText().strip(),
            "odometer": odometer,
            "service_date": self.date_service.date().toString("yyyy-MM-dd"),
            "next_maintenance_date": self.date_next.date().toString("yyyy-MM-dd"),
            "manual_appointment_date": self.date_manual_appt.date().toString("yyyy-MM-dd"),
            "appointment_date": self.date_manual_appt.date().toString("yyyy-MM-dd"),
            "appointment_time": self.time_appt.time().toString("HH:mm"),
            "inspection_due_date": self.date_inspection.date().toString("yyyy-MM-dd"),
            "inspection_notice_date": self.date_inspection.date().addDays(-30).toString("yyyy-MM-dd"),
            "notes": self.txt_notes.toPlainText().strip(),
            "reminder_date": self.date_next.date().addDays(-1).toString("yyyy-MM-dd"),
        }
        if hasattr(self.db, "_build_vehicle_qr_token"):
            card_data["qr_token"] = self.db._build_vehicle_qr_token(card_data)
        username = ""
        try:
            username = getattr(self.parent(), "username", "") or getattr(self.parent(), "current_user", {}).get("username", "")
        except Exception:
            username = ""

        card_id = self.db.save_vehicle_maintenance_card(card_data, self.selected_items, username=username)
        if not card_id:
            show_warning(self, "Bakim karti kaydedilemedi.")
            return
        self.saved_card_id = card_id
        self.card_id = card_id
        self.btn_gallery.setEnabled(True)
        self.btn_history.setEnabled(True)
        self.accept()

    def _open_history_qr(self):
        plate = self.inp_plate.text().strip().upper()
        if not plate:
            show_warning(self, "Once plaka girin veya kayitli arac secin.")
            return
        dlg = VehicleHistoryQrDialog(self.db, plate, self)
        dlg.exec()


    def _wire_ui_signals(self):
        self.cmb_model.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_year.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_vehicle_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_engine_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_fuel_type.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _reload_customers(self):
        prev_id = self.cmb_customer.currentData()
        self.customer_rows = list(self.db.get_customers() or [])
        self.cmb_customer.blockSignals(True)
        self.cmb_customer.clear()
        self.cmb_customer.addItem("Musteri secin", None)
        for row in self.customer_rows:
            try:
                self.cmb_customer.addItem(row[1], row[0])
            except Exception:
                continue
        if prev_id:
            idx = self.cmb_customer.findData(prev_id)
            if idx >= 0:
                self.cmb_customer.setCurrentIndex(idx)
        self.cmb_customer.blockSignals(False)

    def _add_customer_shortcut(self):
        from src.ui.dialogs.automotive_customer_dialog import AutomotiveCustomerDialog
        dlg = AutomotiveCustomerDialog(self.db, self, sector_manager=self.sector_manager)
        if dlg.exec():
            self._reload_customers()

    def _add_vehicle_shortcut(self):
        customer_id = self.cmb_customer.currentData()
        if not customer_id:
            show_warning(self, "Lütfen önce bir müşteri seçin.")
            return
        customer_name = self.cmb_customer.currentText()
        from src.ui.dialogs.customer_vehicle_dialog import CustomerVehicleDialog
        dlg = CustomerVehicleDialog(self.db, customer_id, customer_name, parent=self)
        if dlg.exec():
            self._reload_customer_vehicles()
            try:
                cur = self.db.conn.cursor()
                cur.execute("SELECT id FROM customer_vehicles WHERE customer_id=? ORDER BY id DESC LIMIT 1", (customer_id,))
                row = cur.fetchone()
                if row:
                    new_vehicle_id = row[0]
                    idx = self.cmb_vehicle.findData(new_vehicle_id)
                    if idx >= 0:
                        self.cmb_vehicle.setCurrentIndex(idx)
                        self._apply_vehicle_selection()
            except Exception as e:
                from src.utils.logger import logger
                logger.debug(f"Failed to auto-select new vehicle: {e}")
