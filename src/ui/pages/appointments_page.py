# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel, 
                             QFormLayout, QLineEdit, QDateEdit, 
                             QTextEdit, QFrame, QAbstractItemView, QComboBox, 
                             QMenu, QMessageBox, QGraphicsDropShadowEffect, QScrollArea, QListWidget)
from PyQt6.QtCore import Qt, QDate, QMimeData, QPoint, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QDrag, QIcon, QCursor, QPainter, QPixmap, QAction
from datetime import datetime, timedelta

from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.modern_inputs import InlineNumberStepper, ValidatedLineEdit, ModernComboBox
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.design_system import DesignTokens
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.date_formatter import format_date
from src.utils.logger import logger

# --- DIALOG ---

class AddAppointmentDialog(ModernDialog):
    WORKFLOW_OPTIONS = [
        ("Ar\u0131za Ke\u015ffi / Servis Onar\u0131m", "kesif_onarim"),
        ("Verilen Teklif / Montaj", "teklif_montaj"),
    ]

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None, selected_date=None, appointment_data=None):
        self.db = db
        self.db.ensure_appointment_montage_schema()
        self.appointment_data = appointment_data
        self.created_appointment_id = None
        self.open_montage_preparation = False
        self.selected_date = selected_date or QDate.currentDate()
        self.selected_color = appointment_data.get('color', tc("accent")) if appointment_data else tc("accent")
        
        title = "Randevu Düzenle" if appointment_data else "Yeni Randevu"
        super().__init__(title, parent, width=820, height=620)
        self.setup_content()
        if appointment_data:
            self.load_data()
        self.select_color(self.selected_color)
        self._wire_ui_signals()

    def _wire_ui_signals(self):
        self.cmb_customer.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_personnel.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_workflow.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_customer.currentIndexChanged.connect(self._refresh_offer_choices)
        self.cmb_workflow.currentIndexChanged.connect(self._sync_workflow_fields)

    def setup_content(self):
        # Content layout
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        plan_intro = QFrame()
        plan_intro.setObjectName("AppointmentDialogHero")
        plan_intro.setStyleSheet(theme_qss("""
            QFrame#AppointmentDialogHero {
                background: @selection_bg; border: 1px solid @accent; border-radius: 14px;
            }
            QLabel#AppointmentDialogHeroTitle {
                background: transparent; border: none; color: @text;
                font-family: Segoe UI; font-size: 17px; font-weight: bold;
            }
            QLabel#AppointmentDialogHeroText {
                background: transparent; border: none; color: @text_muted;
                font-family: Segoe UI; font-size: 12px;
            }
        """))
        plan_intro_layout = QVBoxLayout(plan_intro)
        plan_intro_layout.setContentsMargins(18, 15, 18, 15)
        plan_intro_title = QLabel("Randevu Planlama")
        plan_intro_title.setObjectName("AppointmentDialogHeroTitle")
        plan_intro_text = QLabel("Ak\u0131\u015f\u0131, m\u00fc\u015fteri ve teklif ba\u011flant\u0131s\u0131n\u0131 tek ad\u0131mda planlay\u0131n.")
        plan_intro_text.setObjectName("AppointmentDialogHeroText")
        plan_intro_layout.addWidget(plan_intro_title)
        plan_intro_layout.addWidget(plan_intro_text)
        layout.addWidget(plan_intro)
        
        form_frame = QFrame()
        form_frame.setObjectName("AppointmentDialogForm")
        form_frame.setStyleSheet(theme_qss("""
            QFrame#AppointmentDialogForm {
                background: @surface; border: 1px solid @border; border-radius: 14px;
            }
            QLabel { font-family: Segoe UI; color: @text_muted; font-size: 11px; font-weight: bold; }
            QLineEdit, QComboBox, QDateEdit, QTextEdit {
                min-height: 34px; background: @surface_alt; border: 1px solid @border;
                border-radius: 8px; color: @text; padding: 4px 10px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus {
                border: 1px solid @accent; background: @surface;
            }
        """))
        form_layout = QFormLayout(form_frame)
        form_layout.setContentsMargins(22, 20, 22, 20)
        form_layout.setHorizontalSpacing(18)
        form_layout.setVerticalSpacing(13)
        
        # Müşteri
        self.cmb_customer = ModernComboBox()
        self.cmb_customer.setEditable(True)
        self.load_customers()
        form_layout.addRow("M\u00fc\u015fteri", self.cmb_customer)
        
        # Personel
        self.cmb_personnel = ModernComboBox()
        self.load_personnel()
        form_layout.addRow("Atanan Personel", self.cmb_personnel)
        
        # Zamanlama
        time_row = QHBoxLayout()
        self.inp_date = QDateEdit(self.selected_date)
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        self.inp_date.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        try:
            cal = self.inp_date.calendarWidget()
            # HEADER COLOR FIX -> light Text
            cal.setStyleSheet(theme_qss("""
                QCalendarWidget QWidget { background: @surface; color: @text; }
                
                /* Navigation Bar (Month/Year) */
                QCalendarWidget QWidget#qt_calendar_navigationbar { background-color: @surface_alt; }
                QCalendarWidget QToolButton { 
                    color: @text; 
                    background: transparent; 
                    font-weight: bold;
                    border: none;
                }
                QCalendarWidget QToolButton:hover { background-color: @surface; border-radius: 4px; }
                
                /* Day View */
                QCalendarWidget QAbstractItemView:enabled { 
                    color: @text; 
                    background-color: @surface;
                    selection-background-color: @accent; 
                    selection-color: @surface; 
                }
                QCalendarWidget QMenu { background: @surface; color: @text; border: 1px solid @border; }
                QCalendarWidget QSpinBox { 
                    background-color: @surface; 
                    color: @text; 
                    selection-background-color: @accent;
                    selection-color: @selection_text;
                }
            """))
        except Exception:
            pass
        self.inp_date.setFixedHeight(45)
        
        self.inp_hour = InlineNumberStepper(value=9, decimals=0)
        self.inp_hour.setRange(0, 23)
        self.inp_hour.setSuffix(":00")
        
        time_row.addWidget(self.inp_date, 2)
        time_row.addWidget(self.inp_hour, 1)
        form_layout.addRow("Zamanlama", time_row)
        
        # Cihaz & İşlem
        self.inp_device = ValidatedLineEdit("Cihaz Marka / Model")
        form_layout.addRow("Cihaz", self.inp_device)
        
        self.cmb_type = ModernComboBox(items=["Arıza Tespiti", "Tamir", "Teslimat", "Bakım", "Diğer"])
        form_layout.addRow("İşlem Tipi:", self.cmb_type)
        
        self.cmb_workflow = ModernComboBox()
        for label, value in self.WORKFLOW_OPTIONS:
            self.cmb_workflow.addItem(label, value)
        form_layout.addRow("Randevu Ak\u0131\u015f\u0131", self.cmb_workflow)
        self.workflow_hint = QLabel("Secilen akis, randevu kapatma ve odeme adimlarini belirler.")
        self.workflow_hint.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 10px; color: @text_muted; padding-left: 2px;"))
        form_layout.addRow("", self.workflow_hint)
        legacy_type_label = form_layout.labelForField(self.cmb_type)
        if legacy_type_label:
            legacy_type_label.setVisible(False)
        self.cmb_type.setVisible(False)

        self.cmb_offer = ModernComboBox()
        self.offer_label = QLabel("Verilen Teklif")
        form_layout.addRow(self.offer_label, self.cmb_offer)
        self._refresh_offer_choices()
        self._sync_workflow_fields()

        # Renk Etiketi
        self.color_layout = QHBoxLayout()
        self.color_layout.setSpacing(10)
        colors = [tc("accent"), tc("danger"), tc("success"), tc("warning"), tc("accent"), tc("warning")]
        self.color_buttons = {}
        for c in colors:
            btn = QPushButton()
            btn.setFixedSize(36, 36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, col=c: self.select_color(col))
            self.color_layout.addWidget(btn)
            self.color_buttons[c] = btn
        
        color_widget = QWidget()
        color_widget.setLayout(self.color_layout)
        form_layout.addRow("Renk Etiketi", color_widget)
        
        # Notlar
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Randevu icin kisa not veya ozel talimat...")
        self.txt_notes.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.txt_notes.setFixedHeight(88)
        form_layout.addRow("Notlar", self.txt_notes)
        
        layout.addWidget(form_frame)
        self.add_widget(content)
        
        # Footer Actions
        self.add_cancel_button("Vazge\u00e7")
        self.add_button("Randevuyu Kaydet", "primary", self.save)

    def select_color(self, color):
        self.selected_color = color
        for c, btn in self.color_buttons.items():
            if c == color:
                btn.setStyleSheet(theme_qss(f"background-color: {c}; border-radius: 16px; border: 3px solid @selection_text;"))
            else:
                btn.setStyleSheet(theme_qss(f"background-color: {c}; border-radius: 16px; border: 2px solid transparent;"))

    def load_customers(self):
        try:
            custs = self.db.get_customers()
            for c in custs: self.cmb_customer.addItem(c[1], c[0])
        except Exception as e:
            logger.warning(f"Appointments customer load failed: {e}")

    def load_personnel(self):
        try:
            self.cmb_personnel.addItem("Seçilmedi", None)
            curs = self.db.conn.cursor()
            curs.execute("SELECT name FROM personnel")
            for p in curs.fetchall(): self.cmb_personnel.addItem(p[0])
        except Exception as e:
            logger.warning(f"Appointments personnel load failed: {e}")

    def _selected_customer_id(self):
        customer_id = self.cmb_customer.currentData()
        if customer_id:
            return customer_id
        try:
            return self.db.get_customer_id_by_name(self.cmb_customer.currentText())
        except Exception:
            return None

    def _refresh_offer_choices(self):
        if not hasattr(self, "cmb_offer"):
            return
        selected_offer_id = self.cmb_offer.currentData()
        customer_id = self._selected_customer_id()
        customer_name = self.cmb_customer.currentText().strip()
        self.cmb_offer.blockSignals(True)
        self.cmb_offer.clear()
        self.cmb_offer.addItem("Teklif se\u00e7ilmedi", None)
        try:
            cursor = self.db.cursor
            cursor.execute("PRAGMA table_info(offers)")
            columns = {row[1] for row in (cursor.fetchall() or [])}
            if not columns:
                return
            customer_id_col = "customer_id" if "customer_id" in columns else "NULL"
            customer_name_col = "customer_name" if "customer_name" in columns else "''"
            offer_no_col = "offer_no" if "offer_no" in columns else "id"
            total_col = "total" if "total" in columns else "0"
            currency_col = "currency_code" if "currency_code" in columns else "'TRY'"
            order_col = "created_at" if "created_at" in columns else "id"
            cursor.execute(
                "SELECT id, {}, {}, {}, {}, {} FROM offers ORDER BY {} DESC, id DESC".format(
                    customer_id_col,
                    customer_name_col,
                    offer_no_col,
                    total_col,
                    currency_col,
                    order_col,
                )
            )
            for row in cursor.fetchall() or []:
                offer_id, offer_customer_id, offer_customer_name, offer_no, total, currency_code = row
                if customer_id and str(offer_customer_id or "") != str(customer_id):
                    continue
                if not customer_id and customer_name and str(offer_customer_name or "").strip() != customer_name:
                    continue
                currency_code = str(currency_code or "TRY").strip().upper() or "TRY"
                label = "{} | {} | {:.2f} {}".format(
                    str(offer_no or "Teklif"),
                    str(offer_customer_name or "-"),
                    float(total or 0),
                    currency_code,
                )
                self.cmb_offer.addItem(
                    label,
                    {
                        "id": offer_id,
                        "offer_no": str(offer_no or ""),
                        "total": float(total or 0),
                        "currency_code": currency_code,
                    },
                )
        except Exception as exc:
            logger.debug("Appointment offer lookup failed: %s", exc)
        if isinstance(selected_offer_id, dict):
            index = self.cmb_offer.findData(selected_offer_id)
            if index >= 0:
                self.cmb_offer.setCurrentIndex(index)
        self.cmb_offer.blockSignals(False)

    def _sync_workflow_fields(self):
        workflow = self.cmb_workflow.currentData()
        is_installation = workflow == "teklif_montaj"
        self.cmb_offer.setVisible(is_installation)
        self.offer_label.setVisible(is_installation)
        if is_installation:
            self.cmb_type.setCurrentText("Montaj")

    def load_data(self):
        d = self.appointment_data
        self.inp_date.setDate(QDate.fromString(d['date'], "yyyy-MM-dd"))
        try:
            self.inp_hour.setValue(int(d['time'].split(':')[0]))
        except Exception as e:
            logger.warning(f"Appointments hour parse failed for {d.get('time')}: {e}")
        self.cmb_customer.setCurrentText(d['customer'])
        self.cmb_personnel.setCurrentText(d.get('personnel', ''))
        self.inp_device.setText(d.get('device', ''))
        self.cmb_type.setCurrentText(d.get('type', ''))
        workflow = d.get("workflow", "kesif_onarim")
        workflow_index = self.cmb_workflow.findData(workflow)
        if workflow_index >= 0:
            self.cmb_workflow.setCurrentIndex(workflow_index)
        self._sync_workflow_fields()
        self._refresh_offer_choices()
        offer_id = d.get("offer_id")
        for index in range(self.cmb_offer.count()):
            offer_data = self.cmb_offer.itemData(index)
            if isinstance(offer_data, dict) and offer_data.get("id") == offer_id:
                self.cmb_offer.setCurrentIndex(index)
                break
        self.txt_notes.setText(d.get('notes', ''))
        self.select_color(d.get('color', tc("accent")))

    def save(self):
        try:
            cust_name = self.cmb_customer.currentText()
            if not cust_name.strip():
                show_warning(self, "Randevu i\u00e7in m\u00fc\u015fteri se\u00e7ilmelidir.")
                return
            pers_name = self.cmb_personnel.currentText()
            if pers_name == "Seçilmedi": pers_name = ""
            date_str = self.inp_date.date().toString("yyyy-MM-dd")
            time_str = f"{int(self.inp_hour.value()):02d}:00"
            
            txn_type = self.cmb_workflow.currentText()
            device = self.inp_device.text()
            notes = self.txt_notes.toPlainText()
            full_desc = f"{txn_type} - {device} - {notes}"
            customer_id = self._selected_customer_id()
            if not customer_id:
                show_warning(self, "M\u00fc\u015fteri listesinden kay\u0131tl\u0131 bir m\u00fc\u015fteri se\u00e7ilmelidir.")
                return
            workflow = self.cmb_workflow.currentData() or "kesif_onarim"
            offer_data = self.cmb_offer.currentData()
            offer_id = offer_data.get("id") if isinstance(offer_data, dict) else None
            offer_no = offer_data.get("offer_no") if isinstance(offer_data, dict) else ""
            if workflow == "teklif_montaj" and not offer_id:
                show_warning(self, "Montaj randevusu i\u00e7in verilen teklif se\u00e7ilmelidir.")
                return
            
            if self.appointment_data and 'id' in self.appointment_data:
                appointment_id = int(self.appointment_data['id'])
                current_status = str(self.appointment_data.get("status") or "").strip()
                next_status = "Bekliyor" if current_status.casefold() == "iptal" else current_status
                if not next_status:
                    next_status = "Bekliyor"
                self.db.cursor.execute("""
                    UPDATE appointments 
                    SET customer_name=?, customer_id=?, personnel_name=?, date=?, time=?,
                        description=?, color=?, status=?, workflow=?, offer_id=?, offer_no=?
                    WHERE id=?
                """, (
                    cust_name, customer_id, pers_name, date_str, time_str, full_desc,
                    self.selected_color, next_status, workflow, offer_id, offer_no, appointment_id
                ))
            else:
                self.db.cursor.execute("""
                    INSERT INTO appointments (
                        customer_name, customer_id, personnel_name, date, time, description,
                        color, status, workflow, offer_id, offer_no, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cust_name, customer_id, pers_name, date_str, time_str, full_desc,
                    self.selected_color, 'Bekliyor', workflow, offer_id, offer_no,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
                appointment_id = int(self.db.cursor.lastrowid)

            self.db.conn.commit()
            if workflow == "teklif_montaj" and offer_id:
                self.db.create_appointment_offer_plan(appointment_id, offer_id)
                self.open_montage_preparation = True
            self.created_appointment_id = appointment_id
            show_success(self, "Kayıt başarıyla güncellendi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Hata: {e}")


class MontagePreparationDialog(ModernDialog):
    def __init__(self, db, appointment_id, parent=None):
        self.db = db
        self.appointment_id = int(appointment_id)
        self.quantity_inputs = {}
        super().__init__("Montaj Hazirligi", parent, width=920, height=590)
        self.setup_content()

    def setup_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setStyleSheet(theme_qss("""
            QFrame { background: @selection_bg; border: 1px solid @accent; border-radius: 12px; }
        """))
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 12, 16, 12)
        hero_title = QLabel("Araca Yukleme Kontrolu")
        hero_title.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 15px; font-weight: bold; color: @text;"))
        hero_note = QLabel("Teklif kalemlerini kontrol edin; malzemeleri sahaya cikmadan once araca transfer edin.")
        hero_note.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 11px; color: @text_muted;"))
        hero_layout.addWidget(hero_title)
        hero_layout.addWidget(hero_note)
        layout.addWidget(hero)

        locations_row = QHBoxLayout()
        self.source_combo = ModernComboBox()
        self.vehicle_combo = ModernComboBox()
        source_label = QLabel("Kaynak Konum")
        vehicle_label = QLabel("Servis Araci")
        for label in (source_label, vehicle_label):
            label.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 11px; font-weight: bold; color: @text_muted;"))
        locations_row.addWidget(source_label)
        locations_row.addWidget(self.source_combo, 1)
        locations_row.addWidget(vehicle_label)
        locations_row.addWidget(self.vehicle_combo, 1)
        layout.addLayout(locations_row)

        self.plan_table = QTableWidget(0, 6)
        self.plan_table.setHorizontalHeaderLabels([
            "Kalem", "Tur", "Teklif", "Depo", "Yukle", "Durum"
        ])
        self.plan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 6):
            self.plan_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setFont(QFont("Segoe UI", 9))
        self.plan_table.horizontalHeader().setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.plan_table.setStyleSheet(theme_qss("""
            QTableWidget { font-family: Segoe UI; background: @surface; border: 1px solid @border; border-radius: 10px; gridline-color: @border; }
            QHeaderView::section { font-family: Segoe UI; background: @surface_alt; color: @text_muted; border: none; padding: 8px; font-weight: bold; }
            QTableWidget::item { font-family: Segoe UI; color: @text; padding: 6px; }
        """))
        layout.addWidget(self.plan_table, 1)
        self.add_widget(content)
        self.add_cancel_button("Kapat")
        self.add_button("Araca Yukle", "primary", self.load_to_vehicle)

        self._load_locations()
        self.source_combo.currentIndexChanged.connect(self.render_plan)
        self.render_plan()

    def _load_locations(self):
        locations = self.db.get_stock_locations() if hasattr(self.db, "get_stock_locations") else []
        for location in locations:
            label = str(location.get("name") or "-")
            if location.get("vehicle_plate"):
                label = "{} ({})".format(label, location["vehicle_plate"])
            if location.get("location_type") == "vehicle":
                self.vehicle_combo.addItem(label, location["id"])
            else:
                self.source_combo.addItem(label, location["id"])

    def _source_quantity_map(self):
        source_id = self.source_combo.currentData()
        if not source_id or not hasattr(self.db, "get_location_inventory"):
            return {}
        return {
            int(row["part_id"]): float(row.get("quantity") or 0)
            for row in self.db.get_location_inventory(source_id)
        }

    def render_plan(self):
        plans = self.db.get_appointment_offer_plan(self.appointment_id)
        source_stock = self._source_quantity_map()
        self.quantity_inputs = {}
        self.plan_table.setRowCount(len(plans))
        for row_index, plan in enumerate(plans):
            self.plan_table.setRowHeight(row_index, 46)
            self.plan_table.setItem(row_index, 0, QTableWidgetItem(str(plan.get("name") or "-")))
            role = plan.get("item_role")
            is_material = role == "material"
            is_manual_material = role == "manual_material"
            kind = "Malzeme" if (is_material or is_manual_material) else "Hizmet"
            self.plan_table.setItem(row_index, 1, QTableWidgetItem(kind))
            planned_text = "{:g} {}".format(float(plan.get("planned_qty") or 0), plan.get("unit") or "Adet")
            self.plan_table.setItem(row_index, 2, QTableWidgetItem(planned_text))
            if not is_material:
                self.plan_table.setItem(row_index, 3, QTableWidgetItem("-"))
                self.plan_table.setItem(row_index, 4, QTableWidgetItem("-"))
                state = "Stok karti gerekli" if is_manual_material else "Planlandi"
                self.plan_table.setItem(row_index, 5, QTableWidgetItem(state))
                continue
            available = float(source_stock.get(int(plan.get("part_id") or 0), 0))
            self.plan_table.setItem(row_index, 3, QTableWidgetItem("{:g}".format(available)))
            remaining = max(0.0, float(plan.get("planned_qty") or 0) - float(plan.get("loaded_qty") or 0))
            stepper = InlineNumberStepper(value=remaining, decimals=0)
            stepper.setRange(0, remaining)
            self.plan_table.setCellWidget(row_index, 4, stepper)
            self.quantity_inputs[int(plan["id"])] = stepper
            loaded = float(plan.get("loaded_qty") or 0)
            used = float(plan.get("used_qty") or 0)
            returned = float(plan.get("returned_qty") or 0)
            if loaded > 0 and returned + used >= loaded - 0.000001:
                state = "Depoya iade edildi"
            else:
                state = "Yuklendi" if remaining <= 0 else "Hazirlanacak"
            self.plan_table.setItem(row_index, 5, QTableWidgetItem(state))

    def load_to_vehicle(self):
        source_id = self.source_combo.currentData()
        vehicle_id = self.vehicle_combo.currentData()
        if not source_id or not vehicle_id:
            show_warning(self, "Kaynak konum ve servis araci secilmelidir.")
            return
        lines = [
            {"plan_id": plan_id, "quantity": stepper.value()}
            for plan_id, stepper in self.quantity_inputs.items()
            if float(stepper.value() or 0) > 0
        ]
        try:
            reference = self.db.load_appointment_offer_plan(
                self.appointment_id, source_id, vehicle_id, lines
            )
            self._save_loading_summary_to_notes()
            show_success(self, "Malzemeler araca yuklendi: {}".format(reference))
            self.render_plan()
        except Exception as exc:
            show_error(self, "Araca y\u00fckleme yap\u0131lamad\u0131. {}".format(exc))

    def _save_loading_summary_to_notes(self):
        plans = [
            plan for plan in self.db.get_appointment_offer_plan(self.appointment_id)
            if plan.get("item_role") == "material" and float(plan.get("loaded_qty") or 0) > 0
        ]
        if not plans:
            return
        row = self.db.cursor.execute(
            "SELECT description FROM appointments WHERE id=?", (self.appointment_id,)
        ).fetchone()
        current = str(row[0] or "") if row else ""
        marker = "Araca y\u00fcklenmi\u015f malzemeler:"
        base = current.split(marker, 1)[0].rstrip()
        lines = [marker]
        for plan in plans:
            quantity = float(plan.get("loaded_qty") or 0)
            unit = str(plan.get("unit") or "Adet")
            name = str(plan.get("name") or "-")
            lines.append("- {}: {:g} {}".format(name, quantity, unit))
        description = base + ("\n\n" if base else "") + "\n".join(lines)
        self.db.cursor.execute(
            "UPDATE appointments SET description=? WHERE id=?",
            (description, self.appointment_id),
        )
        self.db.conn.commit()


class MontageCompletionDialog(ModernDialog):
    def __init__(self, db, appointment_id, parent=None, cancellation=False):
        self.db = db
        self.appointment_id = int(appointment_id)
        self.used_inputs = {}
        self.cancellation = cancellation
        title = "\u0130ptal ve Ara\u00e7 Malzeme Karar\u0131" if cancellation else "Montaj Tamamlama"
        super().__init__(title, parent, width=860, height=540)
        self.setup_content()

    def setup_content(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        notice_text = (
            "\u0130ptal edilen randevu i\u00e7in ara\u00e7 malzemelerini se\u00e7in. Kullan\u0131lan miktar\n"
            "ara\u00e7ta kal\u0131r; kullan\u0131lmayan miktar ana depoya iade edilir."
            if self.cancellation
            else "Kullanilan miktarlari girin. Kullanilmayan malzemeler kaynak konuma iade edilir."
        )
        notice = QLabel(notice_text)
        notice.setStyleSheet(theme_qss("font-family: Segoe UI; color: @text_muted; padding: 10px; background: @surface_alt; border: 1px solid @border; border-radius: 10px;"))
        layout.addWidget(notice)

        self.plan_table = QTableWidget(0, 5)
        self.plan_table.setHorizontalHeaderLabels(["Kalem", "Yuklenen", "Kullanilan", "Iade", "Durum"])
        self.plan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            self.plan_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.plan_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.plan_table.setFont(QFont("Segoe UI", 9))
        self.plan_table.horizontalHeader().setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.plan_table.setStyleSheet(theme_qss("""
            QTableWidget { font-family: Segoe UI; background: @surface; border: 1px solid @border; border-radius: 10px; gridline-color: @border; }
            QHeaderView::section { font-family: Segoe UI; background: @surface_alt; color: @text_muted; border: none; padding: 8px; font-weight: bold; }
            QTableWidget::item { font-family: Segoe UI; color: @text; padding: 6px; }
        """))
        layout.addWidget(self.plan_table, 1)
        self.add_widget(content)
        self.add_cancel_button("Vazgec")
        action_text = "\u0130ptali ve Malzeme Karar\u0131n\u0131 Kaydet" if self.cancellation else "Montaj\u0131 Tamamla"
        self.add_button(action_text, "primary", self.complete_plan)
        self.render_plan()

    def render_plan(self):
        plans = [
            plan for plan in self.db.get_appointment_offer_plan(self.appointment_id)
            if plan.get("item_role") == "material"
        ]
        self.plan_table.setRowCount(len(plans))
        self.used_inputs = {}
        for row_index, plan in enumerate(plans):
            loaded = float(plan.get("loaded_qty") or 0)
            self.plan_table.setRowHeight(row_index, 46)
            self.plan_table.setItem(row_index, 0, QTableWidgetItem(str(plan.get("name") or "-")))
            self.plan_table.setItem(row_index, 1, QTableWidgetItem("{:g} {}".format(loaded, plan.get("unit") or "Adet")))
            used = InlineNumberStepper(value=loaded, decimals=0)
            used.setRange(0, loaded)
            returned = QLabel("0")
            returned.setAlignment(Qt.AlignmentFlag.AlignCenter)
            used.valueChanged.connect(lambda value, amount=loaded, label=returned: label.setText("{:g}".format(max(0.0, amount - value))))
            self.plan_table.setCellWidget(row_index, 2, used)
            self.plan_table.setCellWidget(row_index, 3, returned)
            self.plan_table.setItem(row_index, 4, QTableWidgetItem("Yuklendi" if loaded else "Yukleme yok"))
            self.used_inputs[int(plan["id"])] = used

    def complete_plan(self):
        lines = [
            {"plan_id": plan_id, "used_qty": stepper.value()}
            for plan_id, stepper in self.used_inputs.items()
        ]
        try:
            self.db.complete_appointment_offer_plan(self.appointment_id, lines)
            show_success(self, "Montaj malzeme kullanimi kaydedildi.")
            self.accept()
        except Exception as exc:
            show_error(self, "Montaj tamamlanamadi: {}".format(exc))


# --- Takvim Kart ---
class CalendarCard(QFrame):
    clicked = pyqtSignal(int)
    rightClicked = pyqtSignal(int, QPoint)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.app_id = data.get('id')
        self.data = data
        self.setup_ui()
    def setup_ui(self):
        color = self.data.get('color')
        if not color or color == 'None': color = tc("accent")
        # Lighter tint for background
        self.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: rgba({QColor(color).red()}, {QColor(color).green()}, {QColor(color).blue()}, 25);
                border-left: 4px solid {color};
                border-radius: 6px;
                border-right: 1px solid @border;
                border-top: 1px solid @border;
                border-bottom: 1px solid @border;
            }}
            QFrame:hover {{
                background-color: rgba({QColor(color).red()}, {QColor(color).green()}, {QColor(color).blue()}, 45);
                margin: 0px;
            }}
        """))
        
        # Hafif Gölge
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 30))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Müşteri İsmi
        lbl_name = QLabel(self.data.get('customer_name', ''))
        lbl_name.setMinimumHeight(30)
        lbl_name.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_name.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
        lbl_name.setWordWrap(True)
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(lbl_name)
        
        # İşlem Tipi
        desc = self.data.get('description') or ''
        type_text = desc.split(' - ')[0] if ' - ' in desc else desc
        self.setToolTip("{}\n{}\n{}".format(self.data.get("time", ""), self.data.get("customer_name", ""), desc))
        lbl_type = QLabel(str(self.data.get("time", "")) + "  " + (type_text[:22] + "..." if len(type_text) > 22 else type_text))
        lbl_type.setWordWrap(True)
        lbl_type.setStyleSheet(theme_qss(f"color: {color}; font-size: 10px; font-weight: bold; border: none; background: transparent;"))
        layout.addWidget(lbl_type)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.__drag_start_pos = event.pos()
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightClicked.emit(self.app_id, event.globalPosition().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton): return
        if (event.pos() - self.__drag_start_pos).manhattanLength() < 10: return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(self.app_id))
        drag.setMimeData(mime)
        
        # Sürükleme görseli - Premium Ghost Effect
        original = self.grab()
        pixmap = QPixmap(original.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setOpacity(0.8)
        painter.drawPixmap(0, 0, original)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Border çiz
        raw_color = self.data.get('color')
        if not raw_color or raw_color == 'None':
            raw_color = tc("accent")
        pen_color = QColor(raw_color)
        if not pen_color.isValid():
            pen_color = qc("accent")
        painter.setPen(pen_color)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(pixmap.rect().adjusted(1,1,-1,-1), 6, 6)
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        
        drag.exec(Qt.DropAction.MoveAction)

    def mouseDoubleClickEvent(self, event):
        self.clicked.emit(self.app_id)

# --- Özel Takvim Tablosu ---
class CalendarTable(QTableWidget):
    itemDropped = pyqtSignal(int, int, int) # id, row, col

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.last_highlighted = None
        
        self.apply_theme_styles()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.verticalHeader().setDefaultSectionSize(112)
        self.horizontalHeader().setMinimumSectionSize(80)
        self.verticalHeader().setVisible(False)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True) # Satırları renklendir
        
        # Scrollbar styler
        self.verticalScrollBar().setStyleSheet(theme_qss("""
            QScrollBar:vertical {
                border: none;
                background: @surface_alt;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: @border;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """))
        self.apply_theme_styles()
        
    def _setup_kanban_board(self, root_layout):
        self.kanban_board = QFrame()
        self.kanban_board.setObjectName("AppointmentKanbanBoard")
        self.kanban_board.setMinimumHeight(260)
        self.kanban_board.setStyleSheet(theme_qss("""
            QFrame#AppointmentKanbanBoard {
                background: @surface_alt; border: 1px solid @border; border-radius: 15px;
            }
        """))
        board_layout = QVBoxLayout(self.kanban_board)
        board_layout.setContentsMargins(16, 8, 16, 8)
        board_layout.setSpacing(6)

        board_header = QHBoxLayout()
        title = QLabel("Haftal\u0131k Planlama Kanban")
        title.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 13px; font-weight: bold; color: @text;"))
        subtitle = QLabel("Planlanan i\u015fleri durumuna g\u00f6re takip edin")
        subtitle.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 10px; color: @text_muted; padding-left: 6px;"))
        board_header.addWidget(title)
        board_header.addWidget(subtitle)
        board_header.addStretch()
        board_layout.addLayout(board_header)

        self.kanban_columns = {}
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)
        columns = [
            ("planned", "Planland\u0131", tc("accent")),
            ("onsite", "Sahada", tc("warning")),
            ("working", "\u0130\u015flemde", tc("danger")),
            ("done", "Tamamland\u0131", tc("success")),
        ]
        for key, label, color in columns:
            column = QFrame()
            column.setObjectName("AppointmentKanbanColumn")
            column.setStyleSheet(theme_qss("""
                QFrame#AppointmentKanbanColumn {
                    background: @surface; border: 1px solid @border; border-radius: 11px;
                }
            """))
            column_layout = QVBoxLayout(column)
            column_layout.setContentsMargins(10, 7, 10, 7)
            column_layout.setSpacing(4)
            heading = QHBoxLayout()
            heading_label = QLabel(label)
            heading_label.setStyleSheet(theme_qss(
                "font-family: Segoe UI; font-size: 11px; font-weight: bold; color: {};".format(color)
            ))
            count_label = QLabel("0")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            count_label.setFixedSize(22, 22)
            count_label.setStyleSheet(theme_qss(
                "background: {}; color: @selection_text; border-radius: 11px; font-size: 10px; font-weight: bold;".format(color)
            ))
            heading.addWidget(heading_label)
            heading.addStretch()
            heading.addWidget(count_label)
            column_layout.addLayout(heading)
            card_layout = QVBoxLayout()
            card_layout.setSpacing(6)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            column_layout.addLayout(card_layout)
            self.kanban_columns[key] = {"layout": card_layout, "count": count_label, "color": color}
            columns_layout.addWidget(column, 1)
        board_layout.addLayout(columns_layout)
        root_layout.addWidget(self.kanban_board)

    @staticmethod
    def _kanban_status_key(status):
        normalized = str(status or "").casefold()
        if normalized.startswith("tamam") or normalized.startswith("iptal"):
            return "done"
        if normalized.startswith("gid"):
            return "onsite"
        if normalized.startswith("is") or "lem" in normalized:
            return "working"
        return "planned"

    def refresh_kanban_board(self):
        if not hasattr(self, "kanban_columns"):
            return
        for meta in self.kanban_columns.values():
            layout = meta["layout"]
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            meta["count"].setText("0")
        try:
            week_start = self.monday.strftime("%Y-%m-%d")
            week_end = (self.monday + timedelta(days=6)).strftime("%Y-%m-%d")
            deleted_col = self._get_deleted_col() or None
            query = (
                "SELECT id, customer_name, date, time, status, workflow, offer_no "
                "FROM appointments WHERE date BETWEEN ? AND ?"
            )
            if deleted_col:
                query += " AND ({}=0 OR {} IS NULL)".format(deleted_col, deleted_col)
            query += " ORDER BY date, time"
            rows = self.db.cursor.execute(query, (week_start, week_end)).fetchall() or []
            counts = {key: 0 for key in self.kanban_columns}
            for app_id, customer_name, date_value, time_value, status, workflow, offer_no in rows:
                key = self._kanban_status_key(status)
                meta = self.kanban_columns[key]
                route = "Teklif / Montaj" if workflow == "teklif_montaj" else "Ke\u015fif / Onar\u0131m"
                if offer_no:
                    route = "{} | {}".format(route, offer_no)
                card = QPushButton("{}  {}\n{}\n{}".format(
                    str(time_value or "--:--"), str(customer_name or "-"), route, str(date_value or "")
                ))
                card.setCursor(Qt.CursorShape.PointingHandCursor)
                card.setMinimumHeight(46)
                card.setStyleSheet(theme_qss("""
                    QPushButton {
                        background: @surface_alt; color: @text; border: 1px solid @border;
                        border-left: 3px solid %s; border-radius: 9px; text-align: left;
                        padding: 7px 9px; font-size: 11px; font-weight: bold;
                    }
                    QPushButton:hover { background: @selection_bg; border-color: %s; }
                """ % (meta["color"], meta["color"])))
                card.clicked.connect(lambda _checked=False, aid=app_id: self.open_edit_dialog(aid))
                meta["layout"].addWidget(card)
                counts[key] += 1
            for key, count in counts.items():
                self.kanban_columns[key]["count"].setText(str(count))
        except Exception as exc:
            logger.warning("Appointment kanban refresh failed: %s", exc)

    def apply_theme_styles(self):
        self.setStyleSheet(theme_qss("""
            QTableWidget {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 12px;
                gridline-color: @text_muted; /* Biraz daha belirgin grid */
                alternate-background-color: @surface_alt; /* Slate 50 - çok hafif gri */
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid @surface_alt;
                border-right: 1px dashed @surface_alt; /* Hafif dikey ayrım */
            }
            QHeaderView::section {
                background-color: @surface_alt;
                color: @text_muted;
                padding: 12px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: bold;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QTableCornerButton::section {
                background-color: @surface_alt;
                border: none;
            }
        """))

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            # Highlight cell under cursor
            pos = event.position().toPoint()
            row = self.rowAt(pos.y())
            col = self.columnAt(pos.x())
            
            # Clean old highlight
            if self.last_highlighted and self.last_highlighted != (row, col):
                lr, lc = self.last_highlighted
                item = self.item(lr, lc)
                if item: item.setBackground(qc("surface"))

            # New highlight    
            if row >= 0 and col >= 1:
                item = self.item(row, col)
                if item:
                    item.setBackground(qc("selection_bg")) # Very light accent
                    self.last_highlighted = (row, col)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        if self.last_highlighted:
            lr, lc = self.last_highlighted
            item = self.item(lr, lc)
            if item: item.setBackground(qc("surface"))
            self.last_highlighted = None
            
        event.accept()

    def dropEvent(self, event):
        if self.last_highlighted:
            lr, lc = self.last_highlighted
            item = self.item(lr, lc)
            if item: item.setBackground(qc("surface"))
            self.last_highlighted = None
            
        try:
            text_data = event.mimeData().text()
            # Try to parse ID
            if text_data.isdigit():
                app_id = int(text_data)
                
                pos = event.position().toPoint()
                row = self.rowAt(pos.y())
                col = self.columnAt(pos.x())
                
                if row >= 0 and col >= 1: # Saat sütununa bırakma yapılamaz
                    # Success
                    self.itemDropped.emit(app_id, row, col)
                    event.acceptProposedAction()
                else:
                    event.ignore()
            else:
                event.ignore()
        except (RuntimeError, AttributeError):
            event.ignore()


# --- ANA SAYFA ---
class AppointmentsPage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        # Defensive local import for environments where module-level symbol cache is stale.
        from PyQt6.QtCore import QTimer as _QTimer
        self.db = db
        self.db.ensure_appointment_montage_schema()
        self.hours = list(range(9, 20)) # 09:00 - 19:00
        self._appointments_deleted_col = None
        self._refresh_in_progress = False
        self._refresh_pending = False
        self._refresh_timer = _QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._run_scheduled_refresh)
        
        # Mevcut haftanın başlangıcını bul (Pazartesi)
        today = datetime.now()
        self.monday = today - timedelta(days=today.weekday())
        self.monday = self.monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        self.setup_ui()
        # Sayfa açılışında UI'nin kilitlenmemesi için ilk veri yüklemesini kısa gecikmeyle başlat.
        self.schedule_refresh(120)

    def schedule_refresh(self, delay_ms=0):
        self._refresh_timer.start(max(0, delay_ms))

    def _run_scheduled_refresh(self):
        if self._refresh_in_progress:
            self._refresh_pending = True
            return
        self.refresh_calendar()

    def _get_deleted_col(self):
        if self._appointments_deleted_col is not None:
            return self._appointments_deleted_col
        try:
            curs = self.db.conn.cursor()
            curs.execute("PRAGMA table_info(appointments)")
            cols = [c[1] for c in curs.fetchall()]
            self._appointments_deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else "")
        except Exception:
            self._appointments_deleted_col = ""
        return self._appointments_deleted_col
    
    def setup_ui(self):
        self.setObjectName("AppointmentsPage")
        self.setStyleSheet(theme_qss("""
            QWidget#AppointmentsPage { background-color: @window; }
            QFrame#AppointmentsToolbar {
                background: @surface_alt; border: 1px solid @border; border-radius: 15px;
            }
        """))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 28)
        layout.setSpacing(14)
        
        # --- ÜST MENÜ (NAVİGASYON) ---
        toolbar = QFrame()
        toolbar.setObjectName("AppointmentsToolbar")
        toolbar.setMinimumHeight(66)
        nav_layout = QHBoxLayout(toolbar)
        nav_layout.setContentsMargins(16, 9, 16, 9)
        nav_layout.setSpacing(10)
        
        # Navigasyon Grubu
        nav_group = QHBoxLayout()
        btn_prev = QPushButton("\u2039")
        btn_prev.setFixedSize(40, 40)
        btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_prev.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        btn_prev.clicked.connect(self.prev_week)
        
        btn_today = QPushButton("Bug\u00fcn")
        btn_today.setFixedHeight(40)
        btn_today.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_today.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        btn_today.clicked.connect(self.go_today)
        
        btn_next = QPushButton("\u203a")
        btn_next.setFixedSize(40, 40)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        btn_next.clicked.connect(self.next_week)
        
        nav_group.addWidget(btn_prev)
        nav_group.addWidget(btn_today)
        nav_group.addWidget(btn_next)
        nav_layout.addLayout(nav_group)
        
        # Tarih Aralığı Label
        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        page_title = QLabel("Randevu Merkezi")
        page_title.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 16px; font-weight: bold; color: @text;"))
        self.lbl_week = QLabel("")
        self.lbl_week.setStyleSheet(theme_qss("font-family: Segoe UI; font-size: 11px; font-weight: bold; color: @text_muted;"))
        title_stack.addWidget(page_title)
        title_stack.addWidget(self.lbl_week)
        nav_layout.addLayout(title_stack)
        
        nav_layout.addStretch()
        
        btn_add = QPushButton("+ Yeni Randevu")
        btn_add.setFixedSize(166, 38)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_add.clicked.connect(self.open_add_dialog)
        nav_layout.addWidget(btn_add)
        btn_planned = QPushButton("Planlanan Randevular")
        btn_planned.setFixedSize(190, 38)
        btn_planned.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_planned.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_planned.clicked.connect(self.open_planned_appointments_dialog)
        nav_layout.addWidget(btn_planned)
        
        layout.addWidget(toolbar)

        
        # --- ANA EKRAN (SOL: TAKVİM | SAĞ: İŞLEM PANELİ) ---
        main_content = QHBoxLayout()
        main_content.setSpacing(12)
        
        # TAKVİM (SOL)
        self.table = CalendarTable(self)
        self.table.db = self.db
        self.table.monday = self.monday
        self.table._get_deleted_col = self._get_deleted_col
        self.table.open_edit_dialog = self.open_edit_dialog
        self.table._setup_kanban_board(layout)
        self.table.kanban_board.hide()
        self.table.setRowCount(len(self.hours))
        self.table.setColumnCount(8) # Saat + 7 Gün
        
        # Header'ları hazırla
        days = ["Saat", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
        self.table.setHorizontalHeaderLabels(days)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 64)
        
        # Saat sütununu doldur
        for i, h in enumerate(self.hours):
            hour_item = QTableWidgetItem(f"{h:02d}:00")
            hour_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hour_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            hour_item.setBackground(qc("surface_alt"))
            hour_item.setForeground(qc("disabled_text"))
            hour_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            self.table.setItem(i, 0, hour_item)
            
        self.table.itemDropped.connect(self.handle_drop)
        self.table.cellDoubleClicked.connect(self.handle_cell_double_click)
        main_content.addWidget(self.table, 4) # 4 birim genişlik
        
        # SAĞ PANEL (GÜNÜN AKIŞI)
        self.side_panel = QFrame()
        self.side_panel.setFixedWidth(280)
        
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(14, 14, 14, 14)
        side_layout.setSpacing(10)
        
        lbl_side_title = QLabel(" Bugünün İşlemleri")
        lbl_side_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lbl_side_title.setStyleSheet(theme_qss("color: @text; border: none;"))
        side_layout.addWidget(lbl_side_title)
        
        # İşlem alanı (Scrollable)
        self.side_scroll = QScrollArea()
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll.setStyleSheet(theme_qss("background: transparent; border: none;"))
        
        self.side_container = QWidget()
        self.side_container.setStyleSheet(theme_qss("background: transparent; border: none;"))
        self.side_list_layout = QVBoxLayout(self.side_container)
        self.side_list_layout.setContentsMargins(0, 0, 0, 0)
        self.side_list_layout.setSpacing(10)
        self.side_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.side_scroll.setWidget(self.side_container)
        side_layout.addWidget(self.side_scroll)
        
        main_content.addWidget(self.side_panel, 1) # 1 birim genişlik
        
        layout.addLayout(main_content)
        
        self.apply_theme_styles()

    def apply_theme_styles(self):
        if hasattr(self, "side_panel"):
            self.side_panel.setStyleSheet(theme_qss(f"""
                QFrame {{
                    background-color: @surface_alt;
                    border: 1px solid @border;
                    border-radius: 14px;
                }}
                QLabel {{
                    background: transparent;
                }}
            """))
        if hasattr(self, "table"):
            if hasattr(self.table, "apply_theme_styles"):
                self.table.apply_theme_styles()
            
            # Explicitly style the header to fix white header issue in dark themes
            self.table.horizontalHeader().setStyleSheet(theme_qss("""
                QHeaderView::section {
                    background-color: @surface_alt;
                    color: @text_muted;
                    padding: 10px 8px;
                    border: none;
                    border-bottom: 1px solid @border;
                    font-weight: bold;
                    font-size: 11px;
                }
            """))
            if not getattr(self, "_refresh_in_progress", False):
                self.schedule_refresh(0)

    def refresh_calendar(self):
        self._refresh_in_progress = True
        from src.utils.ayec_accelerator import fast_render_context
        with fast_render_context(self.table):
            try:
                self.refresh_side_panel()
                self.table.monday = self.monday
                self.table.refresh_kanban_board()
                # Hafta başlığı güncelleme
                end_date = self.monday + timedelta(days=6)
                self.lbl_week.setText(f"{format_date(self.monday, self.db)} - {format_date(end_date, self.db)}")
                
                # Sütun başlıklarındaki tarihleri güncelle
                day_names = ["Saat", "Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
                headers = ["Saat"]
                for i in range(7):
                    d = self.monday + timedelta(days=i)
                    date_disp = format_date(d, self.db)
                    headers.append(f"{day_names[i+1]} {date_disp}")
                self.table.setHorizontalHeaderLabels(headers)
                
                # Tabloyu temizle
                self.table.setUpdatesEnabled(False)
                self.table.clearSelection()
                for r in range(self.table.rowCount()):
                    for c in range(1, self.table.columnCount()):
                        old_w = self.table.cellWidget(r, c)
                        if old_w:
                            try:
                                old_w.deleteLater()
                            except RuntimeError:
                                pass
                        
                        self.table.setCellWidget(r, c, None)
                        item = QTableWidgetItem("")
                        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDropEnabled)
                        item.setBackground(qc("surface"))
                        self.table.setItem(r, c, item)

                # Veritabanından verileri ekle
                start_str = self.monday.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")
                
                curs = self.db.conn.cursor()
                deleted_col = self._get_deleted_col() or None
                query = """
                    SELECT id, customer_name, date, time, description, color, personnel_name 
                    FROM appointments 
                    WHERE date BETWEEN ? AND ?
                """
                if deleted_col:
                    query = query.replace(
                        "WHERE date BETWEEN ? AND ?",
                        f"WHERE date BETWEEN ? AND ? AND ({deleted_col}=0 OR {deleted_col} IS NULL)",
                    )
                curs.execute(query, (start_str, end_str))
                
                rows = curs.fetchall()
                for r in rows:
                    app_id, cust, date_val, time_val, desc, color, pers = r
                    desc = desc or ''
                    dt = datetime.strptime(date_val, "%Y-%m-%d")
                    col = (dt - self.monday).days + 1
                    
                    try:
                        hour_int = int(str(time_val).split(':')[0])
                        row = self.hours.index(hour_int)
                    except (ValueError, IndexError):
                        continue
                    
                    if 0 <= row < len(self.hours) and 1 <= col < 8:
                        data = {
                            'id': app_id, 'customer_name': cust, 'date': date_val, 
                            'time': time_val, 'description': desc, 'color': color, 'personnel_name': pers
                        }
                        card = CalendarCard(data)
                        card.clicked.connect(self.open_edit_dialog)
                        card.rightClicked.connect(self.handle_card_right_click)
                        self.table.setCellWidget(row, col, card)
            except Exception as e:
                logger.error(f"AppointmentsPage calendar refresh error: {e}")
            finally:
                self.table.setUpdatesEnabled(True)
                self._refresh_in_progress = False
                if self._refresh_pending:
                    self._refresh_pending = False
                    QTimer.singleShot(0, self._run_scheduled_refresh)


    def handle_drop(self, app_id, row, col):
        try:
            new_hour = self.hours[row]
            new_date_dt = self.monday + timedelta(days=col-1)
            new_date_str = new_date_dt.strftime("%Y-%m-%d")
            new_time_str = f"{new_hour:02d}:00"
            
            self.db.cursor.execute("UPDATE appointments SET date=?, time=? WHERE id=?", 
                                   (new_date_str, new_time_str, app_id))
            self.db.conn.commit()
            
            # Anlık yenileme
            self.schedule_refresh(60)
            show_success(self, "Randevu başarıyla taşındı.")
        except Exception as e:
            show_error(self, f"Taşıma sırasında hata: {e}")

    def handle_cell_double_click(self, row, col):
        if col < 1: return
        # Eğer hücrede zaten bir widget varsa düzenle, yoksa yeni oluştur
        if not self.table.cellWidget(row, col):
            qd = QDate.fromString((self.monday + timedelta(days=col-1)).strftime("%Y-%m-%d"), "yyyy-MM-dd")
            dlg = AddAppointmentDialog(self.db, self, selected_date=qd)
            dlg.inp_hour.setValue(self.hours[row])
            if dlg.exec():
                if dlg.open_montage_preparation and dlg.created_appointment_id:
                    self.open_montage_preparation(dlg.created_appointment_id)
                self.schedule_refresh(60)

    def open_planned_appointments_dialog(self):
        dialog = ModernDialog(title="Planlanan Randevular", parent=self, width=760, height=560)
        dialog.set_footer_visible(False)
        listing = QListWidget()
        start = self.monday.strftime("%Y-%m-%d")
        end = (self.monday + timedelta(days=6)).strftime("%Y-%m-%d")
        rows = self.db.cursor.execute(
            "SELECT date, time, customer_name, status FROM appointments "
            "WHERE date BETWEEN ? AND ? AND COALESCE(status, '') NOT LIKE 'Tamam%' "
            "AND COALESCE(status, '') NOT LIKE 'Iptal%' ORDER BY date, time",
            (start, end),
        ).fetchall() or []
        for date_value, time_value, customer_name, status in rows:
            listing.addItem("{} {}  |  {}  |  {}".format(
                date_value or "", time_value or "--:--", customer_name or "-", status or "Planlandi"
            ))
        if not rows:
            listing.addItem("Bu hafta planlanan randevu bulunmuyor.")
        dialog.add_widget(listing)
        dialog.exec()

    def open_add_dialog(self):
        dlg = AddAppointmentDialog(self.db, self)
        if dlg.exec():
            if dlg.open_montage_preparation and dlg.created_appointment_id:
                self.open_montage_preparation(dlg.created_appointment_id)
            self.schedule_refresh(60)

    def open_montage_preparation(self, appointment_id):
        try:
            workflow_row = self.db.cursor.execute(
                "SELECT workflow, offer_id FROM appointments WHERE id=?", (int(appointment_id),)
            ).fetchone()
            if not workflow_row or str(workflow_row[0] or "") != "teklif_montaj":
                show_warning(self, "Hazirlik listesi sadece teklif ve montaj randevularinda kullanilir.")
                return
            if hasattr(self.db, "reconcile_appointment_vehicle_stock"):
                self.db.reconcile_appointment_vehicle_stock(appointment_id)
            # Repair legacy plans that were created as services although the
            # offer line is linked to a stock card.
            offer_id = workflow_row[1]
            if offer_id:
                self.db.ensure_appointment_montage_schema()
                material_count = self.db.cursor.execute(
                    """
                    SELECT COUNT(*) FROM appointment_plan_items
                    WHERE appointment_id=? AND item_role='material'
                    """,
                    (int(appointment_id),),
                ).fetchone()[0]
                linked_count = self.db.cursor.execute(
                    """
                    SELECT COUNT(*) FROM offer_items
                    WHERE offer_id=? AND item_id IS NOT NULL
                    """,
                    (int(offer_id),),
                ).fetchone()[0]
                if material_count == 0 and linked_count > 0:
                    self.db.create_appointment_offer_plan(
                        appointment_id, offer_id, replace=True
                    )
            MontagePreparationDialog(self.db, appointment_id, self).exec()
            self.schedule_refresh(60)
        except Exception as exc:
            logger.warning("Montage preparation dialog failed: %s", exc)
            show_error(self, "Montaj hazirligi acilamadi.")

    def open_edit_dialog(self, app_id):
        try:
            curs = self.db.conn.cursor()
            deleted_col = self._get_deleted_col() or None
            query = (
                "SELECT id, customer_name, personnel_name, date, time, description, color, status, "
                "customer_id, workflow, offer_id FROM appointments WHERE id=?"
            )
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            r = curs.execute(query, (app_id,)).fetchone()
            if r:
                data = {
                    'id': r[0], 'customer': r[1], 'personnel': r[2], 'date': r[3], 'time': r[4], 
                    'notes': r[5], 'color': r[6], 'status': r[7], 'device': "", 'type': "Tamir",
                    'customer_id': r[8], 'workflow': r[9] or "kesif_onarim", 'offer_id': r[10],
                }
                if data['notes'] and " - " in data['notes']:
                    parts = data['notes'].split(' - ')
                    if len(parts) >= 3:
                        data['type'], data['device'], data['notes'] = parts[0], parts[1], parts[2]
                
                dlg = AddAppointmentDialog(self.db, self, appointment_data=data)
                if dlg.exec():
                    if dlg.open_montage_preparation and dlg.created_appointment_id:
                        self.open_montage_preparation(dlg.created_appointment_id)
                    self.schedule_refresh(60)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def refresh_side_panel(self):
        """Bugünün randevularını sağ panelde listeler ve işlem düğmeleri ekler"""
        try:
            # Temizle
            while self.side_list_layout.count():
                item = self.side_list_layout.takeAt(0)
                if item.widget(): item.widget().deleteLater()
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            curs = self.db.conn.cursor()
            deleted_col = self._get_deleted_col() or None
            query = """
                SELECT id, customer_name, time, description, status, color
                FROM appointments
                WHERE date = ?
                ORDER BY time ASC
            """
            if deleted_col:
                query = query.replace(
                    "WHERE date = ?",
                    f"WHERE date = ? AND ({deleted_col}=0 OR {deleted_col} IS NULL)",
                )
            curs.execute(query, (today_str,))
            
            rows = curs.fetchall()
            
            if not rows:
                lbl_empty = QLabel("Bugün için kayıtlı\nrandevu bulunamadı.")
                lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl_empty.setStyleSheet(theme_qss("color: @disabled_text; font-style: italic; margin-top: 20px; border: none;"))
                self.side_list_layout.addWidget(lbl_empty)
                return
            
            for r in rows:
                app_id, cust, time, desc, status, color = r
                desc = desc or ''
                status = status or 'Bekliyor'
                
                # Kart Frame - Using SidePanelCard for double click
                card = SidePanelCard(app_id)
                card.doubleClicked.connect(self.open_edit_dialog)
                
                status_colors = {
                    'Gidildi': tc("success"),
                    'Gidilmedi': tc("danger"),
                    'İşlemde': tc("warning"),
                    'Tamamlandı': tc("success"),
                    'İptal': tc("disabled_text")
                }
                border_color = status_colors.get(status, tc("border"))
                
                card.setStyleSheet(theme_qss(f"""
                    SidePanelCard {{
                        background-color: @surface;
                        border-radius: 10px;
                        border: 1px solid {border_color};
                    }}
                    SidePanelCard:hover {{ border: 2px solid {border_color}; }}
                """))
                
                # Gölge
                sh = QGraphicsDropShadowEffect()
                sh.setBlurRadius(8)
                sh.setColor(QColor(0, 0, 0, 15))
                sh.setOffset(0, 2)
                card.setGraphicsEffect(sh)
                
                c_layout = QVBoxLayout(card)
                c_layout.setContentsMargins(12, 12, 12, 12)
                
                # Üst Satır (Saat + Status)
                top = QHBoxLayout()
                lbl_time = QLabel(f" {time}")
                lbl_time.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                lbl_time.setStyleSheet(theme_qss("color: @text_muted; border: none; background: transparent;"))
                top.addWidget(lbl_time)
                top.addStretch()
                
                st_display = {
                    'Bekliyor': 'Bekliyor',
                    'Gidildi': 'Geldi',
                    'Gidilmedi': 'Gelmedi',
                    'İşlemde': ' İşlemde',
                    'Tamamlandı': ' Tamamlandı',
                    'İptal': ' İptal'
                }
                lbl_st = QLabel(st_display.get(status, status))
                lbl_st.setStyleSheet(theme_qss(f"""
                    background-color: {border_color}20;
                    color: {border_color if status != 'Bekliyor' else tc('disabled_text')};
                    padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: bold; border: none;
                """))
                top.addWidget(lbl_st)
                c_layout.addLayout(top)
                
                # Müşteri
                lbl_c = QLabel(cust)
                lbl_c.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
                lbl_c.setStyleSheet(theme_qss("color: @text; border: none; background: transparent;"))
                lbl_c.setWordWrap(True)
                c_layout.addWidget(lbl_c)
                
                # Açıklama (Kısa)
                short_desc = desc.split(' - ')[0] if ' - ' in desc else desc
                lbl_d = QLabel(short_desc)
                lbl_d.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none; background: transparent;"))
                c_layout.addWidget(lbl_d)
                
                # İşlem Butonları (Grid şeklinde 2 satır)
                if status not in ["Tamamlandı", "İptal"]:
                    btns_grid = QVBoxLayout()
                    btns_grid.setSpacing(5)
                    
                    row1 = QHBoxLayout()
                    row1.setSpacing(5)
                    
                    if status == "Bekliyor":
                        b_ok = self.create_outcome_btn("Gidildi", tc("success"), app_id)
                        b_no = self.create_outcome_btn("Gidilmedi", tc("danger"), app_id)
                        row1.addWidget(b_ok)
                        row1.addWidget(b_no)
                    
                    if status in ["Bekliyor", "Gidildi"]:
                        b_work = self.create_outcome_btn("İşlemde", tc("warning"), app_id)
                        if status == "Bekliyor": row1.addWidget(b_work)
                        else: row1.addWidget(b_work) # If already Gidildi, put in row1
                    
                    btns_grid.addLayout(row1)
                    
                    row2 = QHBoxLayout()
                    row2.setSpacing(5)
                    b_done = self.create_outcome_btn("Tamamlandı", tc("success"), app_id)
                    b_cancel = self.create_outcome_btn("İptal", tc("disabled_text"), app_id)
                    row2.addWidget(b_done)
                    row2.addWidget(b_cancel)
                    btns_grid.addLayout(row2)
                    
                    c_layout.addLayout(btns_grid)
                
                self.side_list_layout.addWidget(card)
                
        except Exception as e:
            logger.error(f"AppointmentsPage side panel error: {e}")

    def create_outcome_btn(self, text, color, app_id):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(28)
        btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {color}; color: @selection_text; border-radius: 4px; 
                font-weight: bold; font-size: 10px; border: none;
            }}
            QPushButton:hover {{ background-color: {QColor(color).darker(110).name()}; }}
        """))
        btn.clicked.connect(lambda ch, aid=app_id, res=text: self.update_appointment_outcome(aid, res))
        return btn

    def update_appointment_outcome(self, app_id, result):
        """Randevu sonucunu günceller"""
        try:
            normalized_result = str(result or "").strip().casefold().replace("\u0307", "")
            is_completed = normalized_result.startswith("tamam")
            is_cancelled = normalized_result.startswith("iptal")
            if is_completed:
                montage_row = self.db.cursor.execute(
                    "SELECT workflow FROM appointments WHERE id=?", (int(app_id),)
                ).fetchone()
                plan_count = self.db.cursor.execute(
                    "SELECT COUNT(*) FROM appointment_plan_items WHERE appointment_id=?",
                    (int(app_id),),
                ).fetchone()[0]
                if montage_row and str(montage_row[0] or "") == "teklif_montaj" and plan_count:
                    if not MontageCompletionDialog(self.db, app_id, self).exec():
                        return
            if is_cancelled:
                loaded_plan = self.db.get_appointment_offer_plan(app_id)
                has_vehicle_stock = any(
                    plan.get("item_role") == "material"
                    and (
                        float(plan.get("loaded_qty") or 0)
                        > float(plan.get("used_qty") or 0)
                        + float(plan.get("returned_qty") or 0)
                        + 0.000001
                    )
                    for plan in loaded_plan
                )
                if has_vehicle_stock:
                    if not MontageCompletionDialog(
                        self.db, app_id, self, cancellation=True
                    ).exec():
                        return
            completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if is_completed else None
            self.db.cursor.execute(
                "UPDATE appointments SET status=?, completed_at=COALESCE(?, completed_at) WHERE id=?",
                (result, completed_at, app_id),
            )
            self.db.conn.commit()
            show_success(self, f"Randevu durumu güncellendi: {result}")
            if is_completed:
                self._open_montage_payment(app_id)
            self.schedule_refresh(60)
        except Exception as e:
            show_error(self, f"Güncelleme hatası: {e}")
            
    def _open_montage_payment(self, app_id):
        try:
            row = self.db.cursor.execute(
                "SELECT customer_id, customer_name, workflow, offer_no FROM appointments WHERE id=?",
                (app_id,),
            ).fetchone()
            if not row or str(row[2] or "") != "teklif_montaj":
                return
            customer_id, customer_name, _workflow, offer_no = row
            if not customer_id:
                customer_id = self.db.get_customer_id_by_name(customer_name)
            if not customer_id:
                show_warning(self, "\u00d6deme i\u00e7in randevuya ba\u011fl\u0131 bir m\u00fc\u015fteri se\u00e7ilmelidir.")
                return
            customer = self.db.cursor.execute(
                "SELECT id, name, phone FROM customers WHERE id=?", (customer_id,)
            ).fetchone()
            if not customer:
                return
            from src.ui.dialogs.payment_dialog import PaymentDialog
            payment = PaymentDialog(
                self,
                self.db,
                {"id": customer[0], "name": customer[1], "phone": customer[2]},
            )
            payment.reference_desc = "Montaj tamamland\u0131 | Teklif: {}".format(offer_no or "-")
            payment.exec()
        except Exception as exc:
            logger.warning("Montage payment flow could not open: %s", exc)

    def delete_appointment(self, app_id):
        confirm = SimpleConfirmDialog(self, "Randevuyu Sil", "Bu randevuyu silmek istediğinize emin misiniz? Bu işlem geri alınamaz.").exec()
        if confirm:
            try:
                if self.db.delete_appointment(app_id):
                    show_success(self, "Randevu silindi.")
                    self.schedule_refresh(60)
                else:
                    show_error(self, "Silme hatası oluştu.")
            except Exception as e:
                show_error(self, f"Silme hatası: {e}")

    # --- Context Menu & Events ---
    def handle_card_right_click(self, app_id, global_pos):
        if not is_context_menu_enabled(self.db, page_id=30):
            return
        menu = QMenu(self)
        
        edit_action = menu.addAction(" Düzenle")
        edit_action.triggered.connect(lambda: self.open_edit_dialog(app_id))

        plan_action = menu.addAction("Montaj Hazirligi")
        plan_action.triggered.connect(lambda: self.open_montage_preparation(app_id))
        
        status_menu = menu.addMenu(" Durum Değiştir")
        for st in ["Bekliyor", "İşlemde", "Tamamlandı", "İptal", "Gidildi", "Gidilmedi"]:
            act = status_menu.addAction(st)
            act.triggered.connect(lambda ch, s=st, a=app_id: self.update_appointment_outcome(a, s))
            
        menu.addSeparator()
        
        del_action = menu.addAction(" Sil")
        # del_action.setStyleSheet(theme_qss("color: @danger;")) # QAction does not support setStyleSheet
        del_action.triggered.connect(lambda: self.delete_appointment(app_id))
        
        menu.exec(global_pos)

    # Navigasyon Metodları
    def prev_week(self):
        self.monday -= timedelta(weeks=1)
        self.schedule_refresh(40)

    def next_week(self):
        self.monday += timedelta(weeks=1)
        self.schedule_refresh(40)

    def go_today(self):
        today = datetime.now()
        self.monday = today - timedelta(days=today.weekday())
        self.monday = self.monday.replace(hour=0, minute=0, second=0, microsecond=0)
        self.schedule_refresh(40)
        
    def refresh_data(self): self.schedule_refresh(40)

# --- Helper Classes ---

class SidePanelCard(QFrame):
    doubleClicked = pyqtSignal(int)
    
    def __init__(self, app_id, parent=None):
        super().__init__(parent)
        self.app_id = app_id
        
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit(self.app_id)
