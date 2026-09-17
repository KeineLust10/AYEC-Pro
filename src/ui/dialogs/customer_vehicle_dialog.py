from PyQt6.QtWidgets import QComboBox, QFormLayout, QLineEdit, QTextEdit, QVBoxLayout, QWidget

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning
from src.utils.vehicle_catalog import get_models_for_brand, get_vehicle_brands, get_vehicle_years



class CustomerVehicleDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    VEHICLE_TYPES = ["Binek", "Hafif Ticari", "SUV", "Minivan", "Kamyonet", "Motosiklet", "Diger"]
    ENGINE_TYPES = ["Benzinli", "Dizel", "Hibrit", "Elektrikli", "LPG", "Turbo Dizel", "Diger"]
    FUEL_TYPES = ["Benzin", "Dizel", "LPG", "Elektrik", "Hibrit", "Diger"]

    def __init__(self, db, customer_id, customer_name="", vehicle_row=None, parent=None):
        super().__init__("Arac Bilgisi", parent, width=760, height=560)
        self.db = db
        self.customer_id = customer_id
        self.customer_name = customer_name
        self.vehicle_row = vehicle_row
        self.saved_vehicle_id = None
        self._build_ui()
        self._load_row()

    def _build_ui(self):
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(12, 12, 12, 12)

        title = QLineEdit(self.customer_name)
        title.setReadOnly(True)
        title.setStyleSheet(theme_qss("QLineEdit { background: @surface; color: @text_muted; }"))

        form = QFormLayout()
        form.setSpacing(12)
        self.inp_plate = QLineEdit()
        self.inp_brand = ModernComboBox(items=get_vehicle_brands(), editable=True)
        self.inp_model = ModernComboBox(items=[], editable=True)
        self.inp_year = ModernComboBox(items=get_vehicle_years(), editable=True)
        self.cmb_vehicle_type = QComboBox()
        self.cmb_vehicle_type.addItems(self.VEHICLE_TYPES)
        self.cmb_engine_type = QComboBox()
        self.cmb_engine_type.addItems(self.ENGINE_TYPES)
        self.cmb_fuel_type = QComboBox()
        self.cmb_fuel_type.addItems(self.FUEL_TYPES)
        self.inp_odometer = QLineEdit("0")
        self.txt_notes = QTextEdit()
        self.txt_notes.setFixedHeight(100)

        form.addRow("Musteri", title)
        form.addRow("Plaka", self.inp_plate)
        form.addRow("Marka", self.inp_brand)
        form.addRow("Model", self.inp_model)
        form.addRow("Yil", self.inp_year)
        form.addRow("Arac Tipi", self.cmb_vehicle_type)
        form.addRow("Motor Tipi", self.cmb_engine_type)
        form.addRow("Yakit Turu", self.cmb_fuel_type)
        form.addRow("Son Bilinen KM", self.inp_odometer)
        form.addRow("Notlar", self.txt_notes)
        root.addLayout(form)

        self.inp_brand.currentTextChanged.connect(self._sync_model_options)

        self.add_widget(body)
        self.add_cancel_button("Iptal")
        self.add_button("Araci Kaydet", "success", self._save)

    def _set_combo_text(self, combo, value):
        text = str(value or "").strip()
        if not text:
            return
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return
        combo.setEditText(text)

    def _sync_model_options(self):
        current_brand = self.inp_brand.currentText().strip()
        current_model = self.inp_model.currentText().strip()
        models = get_models_for_brand(current_brand)
        self.inp_model.blockSignals(True)
        self.inp_model.clear()
        if models:
            self.inp_model.addItems(models)
        self.inp_model.set_completion_items(models)
        self.inp_model.setEditText(current_model)
        self.inp_model.blockSignals(False)

    def _load_row(self):
        row = self.vehicle_row
        if not row:
            return
        self.inp_plate.setText(str(row["plate"] or ""))
        self._set_combo_text(self.inp_brand, row["brand"])
        self._sync_model_options()
        self._set_combo_text(self.inp_model, row["model"])
        self._set_combo_text(self.inp_year, row["year"])
        self.cmb_vehicle_type.setCurrentText(str(row["vehicle_type"] or self.cmb_vehicle_type.currentText()))
        self.cmb_engine_type.setCurrentText(str(row["engine_type"] or self.cmb_engine_type.currentText()))
        self.cmb_fuel_type.setCurrentText(str(row["fuel_type"] or self.cmb_fuel_type.currentText()))
        self.inp_odometer.setText(str(row["last_known_odometer"] or "0"))
        self.txt_notes.setPlainText(str(row["notes"] or ""))

    def _save(self):
        plate = self.inp_plate.text().strip().upper()
        if not plate:
            show_warning(self, "Plaka zorunludur.")
            return
        try:
            odometer = int(float((self.inp_odometer.text().strip() or "0").replace(",", ".")))
        except Exception:
            show_warning(self, "KM alani sayisal olmali.")
            return

        payload = {
            "id": self.vehicle_row["id"] if self.vehicle_row else None,
            "customer_id": self.customer_id,
            "plate": plate,
            "brand": self.inp_brand.currentText().strip(),
            "model": self.inp_model.currentText().strip(),
            "year": self.inp_year.currentText().strip(),
            "vehicle_type": self.cmb_vehicle_type.currentText().strip(),
            "engine_type": self.cmb_engine_type.currentText().strip(),
            "fuel_type": self.cmb_fuel_type.currentText().strip(),
            "last_known_odometer": odometer,
            "notes": self.txt_notes.toPlainText().strip(),
            "is_active": 1,
        }
        self.saved_vehicle_id = self.db.save_customer_vehicle(payload)
        if not self.saved_vehicle_id:
            show_warning(self, "Arac kaydedilemedi.")
            return
        self.accept()

    def _wire_ui_signals(self):
        self.inp_brand.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.inp_model.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.inp_year.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_vehicle_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_engine_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_fuel_type.currentIndexChanged.connect(self._on_ui_widget_changed)
