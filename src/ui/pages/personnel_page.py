# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QGroupBox, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAbstractItemView, QInputDialog, 
                             QFrame, QGridLayout, QComboBox, QTabWidget, QDateEdit, QSplitter, QDialog,
                             QDoubleSpinBox)
from PyQt6.QtGui import QAction
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtGui import QFont, QIcon, QColor
from PyQt6.QtCore import Qt, QDate
from src.ui.styles.tab_styles import TAB_STYLE
from src.utils.design_system import DesignTokens
from src.utils.context_menu_settings import is_context_menu_enabled
import re
import logging
from datetime import datetime
from src.utils.password_security import hash_password, validate_new_password

logger = logging.getLogger("AYECProLogger")


class PersonnelPage(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        # Ensure schema is updated
        self.db.update_personnel_schema_extended()
        self.editing_id = None # Track edit mode
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.tabBar().setDocumentMode(True)
        self.tabs.tabBar().setExpanding(True)
        self.tabs.setStyleSheet(TAB_STYLE)
        
        self.tab_personnel = QWidget()
        self.setup_personnel_tab()
        
        self.tab_payroll = QWidget()
        self.setup_payroll_tab()
        
        self.tabs.addTab(self.tab_personnel, "👥 Personel Yönetimi")
        self.tabs.addTab(self.tab_payroll, "💰 Maaş ve Prim Yönetimi")
        
        main_layout.addWidget(self.tabs)

    def setup_personnel_tab(self):
        layout = QVBoxLayout(self.tab_personnel)
        
        # --- Add/Edit Form ---
        form_group = QGroupBox("+ Personel İşlemleri")
        form_group.setStyleSheet("""
            QGroupBox { font-weight: bold; border: none; border-top: 3px solid #f39c12; margin-top: 10px; padding-top: 10px; background: white; }
            QLabel { color: #2c3e50; font-weight: bold; font-size: 11px; }
            QLineEdit, QComboBox { 
                padding: 10px; 
                border: 1px solid #bdc3c7; 
                border-radius: 4px; 
                background: #fdfdfd;
                min-height: 20px;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #3498db; background: white; }
        """)
        
        form_layout = QGridLayout()
        form_layout.setSpacing(20)
        form_layout.setContentsMargins(15, 15, 15, 15)
        
        # Fields
        self.inp_name = QLineEdit(); self.inp_name.setPlaceholderText("Personel Adı")
        self.inp_phone = QLineEdit(); self.inp_phone.setPlaceholderText("Telefon")
        self.inp_tc = QLineEdit(); self.inp_tc.setPlaceholderText("TC Kimlik No")
        self.inp_email = QLineEdit(); self.inp_email.setPlaceholderText("E-posta veya Kullanıcı Adı")
        self.inp_telegram = QLineEdit(); self.inp_telegram.setPlaceholderText("Telegram Kullanıcı Adı (@ornek)")
        
        self.inp_role = QLineEdit(); self.inp_role.setPlaceholderText("Görevi")
        self.inp_dept = QLineEdit(); self.inp_dept.setPlaceholderText("Departman")
        self.inp_salary = QLineEdit(); self.inp_salary.setPlaceholderText("Maaş")
        self.cmb_employment_type = QComboBox()
        self.cmb_employment_type.addItem("Ayl\u0131k Maa\u015f", "monthly")
        self.cmb_employment_type.addItem("Yevmiye", "daily")
        self.inp_daily_wage = QLineEdit()
        self.inp_daily_wage.setPlaceholderText("G\u00fcnl\u00fck yevmiye")
        self.inp_pass = QLineEdit(); self.inp_pass.setPlaceholderText("Şifresi (Boş bırakılırsa değişmez)"); self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        
        def add_input(label, widget, row, col):
            lbl = QLabel(label)
            form_layout.addWidget(lbl, row, col)
            form_layout.addWidget(widget, row+1, col)

        add_input("Personel Adı", self.inp_name, 0, 0)
        add_input("Telefon", self.inp_phone, 0, 1)
        add_input("TC Kimlik No", self.inp_tc, 0, 2)
        add_input("E-posta", self.inp_email, 0, 3)
        add_input("Telegram (@kullanici)", self.inp_telegram, 0, 4)
        
        add_input("G\u00f6revi", self.inp_role, 2, 0)
        add_input("Departman", self.inp_dept, 2, 1)
        add_input("\u00c7al\u0131\u015fma Tipi", self.cmb_employment_type, 2, 2)
        add_input("Ayl\u0131k Maa\u015f", self.inp_salary, 2, 3)
        add_input("G\u00fcnl\u00fck Yevmiye", self.inp_daily_wage, 2, 4)
        add_input("\u015eifresi", self.inp_pass, 4, 0)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_clear = QPushButton("TEMİZLE / YENİ")
        self.btn_clear.setStyleSheet("background-color: #95a5a6; color: white; border: none; padding: 10px 20px; font-weight: bold; border-radius: 4px;")
        self.btn_clear.clicked.connect(self.reset_form)
        
        self.btn_add = QPushButton("EKLE")
        self.btn_add.setStyleSheet("background-color: #27ae60; color: white; border: none; padding: 10px 30px; font-weight: bold; border-radius: 4px;")
        self.btn_add.clicked.connect(self.add_personnel)
        
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_add)
        
        full_form_layout = QVBoxLayout()
        full_form_layout.addLayout(form_layout)
        full_form_layout.addSpacing(20)
        full_form_layout.addLayout(btn_layout)
        
        form_group.setLayout(full_form_layout)
        layout.addWidget(form_group)
        
        # --- Personnel List Table ---
        self.table = QTableWidget()
        self.table.setColumnCount(10) # Added employment type and unit wage columns
        self.table.setHorizontalHeaderLabels([
            "ID", "Ad Soyad", "G\u00f6revi", "Departman", "Telefon", "E-posta", "Telegram",
            "TC No", "\u00dccret Tipi", "Birim \u00dccret",
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID Column
        self.table.verticalHeader().setDefaultSectionSize(35)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        self.table.setStyleSheet(DesignTokens.get_table_qss())
        
        layout.addWidget(self.table)
        self.refresh_personnel_list()

    def setup_payroll_tab(self):
        layout = QVBoxLayout(self.tab_payroll)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        calculator_group = QGroupBox("\U0001f4c5 Yevmiye Hesaplama")
        calculator_group.setStyleSheet(
            "QGroupBox { font-weight: 700; border: 1px solid #bdc3c7; border-radius: 8px; margin-top: 10px; padding: 14px; }"
            "QLabel { font-weight: 600; font-size: 11px; }"
            "QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox { padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px; min-height: 20px; }"
        )
        calculator_layout = QGridLayout(calculator_group)
        calculator_layout.setHorizontalSpacing(14)
        calculator_layout.setVerticalSpacing(8)

        self.cmb_month = QDateEdit()
        self.cmb_month.setDisplayFormat("MMMM yyyy")
        self.cmb_month.setCalendarPopup(True)
        self.cmb_month.setDate(QDate.currentDate())
        self.cmb_personnel = QComboBox()
        self.spin_work_days = QDoubleSpinBox()
        self.spin_work_days.setDecimals(1)
        self.spin_work_days.setRange(0.5, 31.0)
        self.spin_work_days.setSingleStep(0.5)
        self.spin_work_days.setValue(1.0)
        self.spin_work_days.setSuffix(" g\u00fcn")
        self.lbl_daily_rate = QLabel("0.00 TL")
        self.lbl_daily_rate.setObjectName("DailyWageRate")
        self.lbl_total = QLabel("0.00 TL")
        self.lbl_total.setObjectName("DailyWageTotal")
        self.inp_daily_note = QLineEdit()
        self.inp_daily_note.setPlaceholderText("A\u00e7\u0131klama (iste\u011fe ba\u011fl\u0131)")
        self.btn_save_daily_wage = QPushButton("\U0001f4be Yevmiyeyi Kaydet")
        self.btn_save_daily_wage.setStyleSheet(
            "background-color: #27ae60; color: white; border: none; border-radius: 6px; padding: 10px 18px; font-weight: 700;"
        )
        self.btn_save_daily_wage.clicked.connect(self.save_daily_wage)

        def add_calculator_field(label, widget, row, column):
            calculator_layout.addWidget(QLabel(label), row, column)
            calculator_layout.addWidget(widget, row + 1, column)

        add_calculator_field("D\u00f6nem", self.cmb_month, 0, 0)
        add_calculator_field("Personel", self.cmb_personnel, 0, 1)
        add_calculator_field("\u00c7al\u0131\u015fma G\u00fcn\u00fc", self.spin_work_days, 0, 2)
        add_calculator_field("G\u00fcnl\u00fck Yevmiye", self.lbl_daily_rate, 0, 3)
        add_calculator_field("Hesaplanan \u00d6deme", self.lbl_total, 0, 4)
        calculator_layout.addWidget(QLabel("Not"), 2, 0)
        calculator_layout.addWidget(self.inp_daily_note, 3, 0, 1, 4)
        calculator_layout.addWidget(self.btn_save_daily_wage, 3, 4)
        layout.addWidget(calculator_group)

        self.tbl_payroll = QTableWidget()
        self.tbl_payroll.setColumnCount(7)
        self.tbl_payroll.setHorizontalHeaderLabels([
            "D\u00f6nem", "Personel", "\u00c7al\u0131\u015fma G\u00fcn\u00fc", "G\u00fcnl\u00fck Yevmiye",
            "Toplam \u00d6deme", "Not", "\u0130\u015flem",
        ])
        self.tbl_payroll.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_payroll.verticalHeader().setDefaultSectionSize(40)
        self.tbl_payroll.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_payroll.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_payroll.setAlternatingRowColors(True)
        self.tbl_payroll.setStyleSheet(DesignTokens.get_table_qss())
        layout.addWidget(self.tbl_payroll)

        self.refresh_personnel_dropdown()
        self.cmb_personnel.currentIndexChanged.connect(self.refresh_daily_wage_preview)
        self.cmb_month.dateChanged.connect(self.refresh_daily_wage_list)
        self.spin_work_days.valueChanged.connect(self.refresh_daily_wage_preview)

    def _selected_daily_personnel(self):
        personnel_id = self.cmb_personnel.currentData()
        if not personnel_id:
            return None
        self.db.cursor.execute(
            "SELECT id, name, employment_type, daily_wage FROM personnel WHERE id=?",
            (personnel_id,),
        )
        return self.db.cursor.fetchone()

    def refresh_daily_wage_preview(self, *args):
        personnel = self._selected_daily_personnel()
        if not personnel:
            self.lbl_daily_rate.setText("0.00 TL")
            self.lbl_total.setText("0.00 TL")
            self.btn_save_daily_wage.setEnabled(False)
            return

        employment_type = str(personnel[2] or "monthly")
        daily_wage = float(personnel[3] or 0)
        if employment_type != "daily" or daily_wage <= 0:
            self.lbl_daily_rate.setText("Yevmiye tan\u0131ml\u0131 de\u011fil")
            self.lbl_total.setText("0.00 TL")
            self.btn_save_daily_wage.setEnabled(False)
            return

        total_amount = self.spin_work_days.value() * daily_wage
        self.lbl_daily_rate.setText(f"{daily_wage:,.2f} TL")
        self.lbl_total.setText(f"{total_amount:,.2f} TL")
        self.btn_save_daily_wage.setEnabled(True)

    def save_daily_wage(self):
        personnel = self._selected_daily_personnel()
        if not personnel:
            show_warning(self.window(), "Yevmiye kayd\u0131 i\u00e7in personel se\u00e7in.")
            return

        personnel_id, personnel_name, employment_type, daily_wage = personnel
        daily_wage = float(daily_wage or 0)
        if str(employment_type or "monthly") != "daily" or daily_wage <= 0:
            show_warning(self.window(), "Se\u00e7ilen personel i\u00e7in g\u00fcnl\u00fck yevmiye tan\u0131ml\u0131 de\u011fil.")
            return

        work_days = float(self.spin_work_days.value())
        total_amount = round(work_days * daily_wage, 2)
        period_date = self.cmb_month.date()
        work_year = period_date.year()
        work_month = period_date.month()
        payment_date = QDate(work_year, work_month, period_date.daysInMonth()).toString("yyyy-MM-dd")
        note = self.inp_daily_note.text().strip()
        description = (
            f"{personnel_name} | Yevmiye | {work_days:g} gun x "
            f"{daily_wage:,.2f} TL"
        )
        if note:
            description = f"{description} | {note}"

        try:
            self.db.cursor.execute(
                "SELECT id, accounting_id FROM personnel_daily_wages "
                "WHERE personnel_id=? AND work_year=? AND work_month=?",
                (personnel_id, work_year, work_month),
            )
            existing = self.db.cursor.fetchone()
            accounting_id = existing[1] if existing else None
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if accounting_id:
                self.db.cursor.execute(
                    "UPDATE accounting SET type=?, category=?, amount=?, description=?, date=?, customer_name=? WHERE id=?",
                    ("Gider", "Yevmiye", total_amount, description, payment_date, personnel_name, accounting_id),
                )
            else:
                self.db.cursor.execute(
                    "INSERT INTO accounting (type, category, amount, description, date, created_at, customer_name) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("Gider", "Yevmiye", total_amount, description, payment_date, created_at, personnel_name),
                )
                accounting_id = self.db.cursor.lastrowid

            if existing:
                self.db.cursor.execute(
                    "UPDATE personnel_daily_wages SET work_days=?, daily_wage=?, total_amount=?, "
                    "payment_date=?, note=?, accounting_id=? WHERE id=?",
                    (work_days, daily_wage, total_amount, payment_date, note, accounting_id, existing[0]),
                )
                result_text = "Yevmiye kayd\u0131 g\u00fcncellendi."
            else:
                self.db.cursor.execute(
                    "INSERT INTO personnel_daily_wages "
                    "(personnel_id, work_year, work_month, work_days, daily_wage, total_amount, payment_date, note, accounting_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (personnel_id, work_year, work_month, work_days, daily_wage, total_amount, payment_date, note, accounting_id),
                )
                result_text = "Yevmiye kayd\u0131 ve gider fi\u015fi olu\u015fturuldu."
            self.db.conn.commit()
            show_success(self.window(), result_text)
            self.refresh_daily_wage_list()
        except Exception as exc:
            self.db.conn.rollback()
            logger.exception("Daily wage save error")
            show_error(self.window(), f"Yevmiye kayd\u0131 olu\u015fturulamad\u0131: {exc}")

    def refresh_daily_wage_list(self, *args):
        if not hasattr(self, "tbl_payroll"):
            return
        period_date = self.cmb_month.date()
        self.tbl_payroll.setRowCount(0)
        try:
            self.db.cursor.execute(
                "SELECT w.id, p.name, w.work_days, w.daily_wage, w.total_amount, w.note "
                "FROM personnel_daily_wages w JOIN personnel p ON p.id=w.personnel_id "
                "WHERE w.work_year=? AND w.work_month=? ORDER BY p.name COLLATE NOCASE",
                (period_date.year(), period_date.month()),
            )
            for row_index, row in enumerate(self.db.cursor.fetchall()):
                self.tbl_payroll.insertRow(row_index)
                record_id, personnel_name, work_days, daily_wage, total_amount, note = row
                values = (
                    period_date.toString("MMMM yyyy"),
                    personnel_name,
                    f"{float(work_days):g} g\u00fcn",
                    f"{float(daily_wage):,.2f} TL",
                    f"{float(total_amount):,.2f} TL",
                    note or "",
                )
                for column, value in enumerate(values):
                    self.tbl_payroll.setItem(row_index, column, QTableWidgetItem(str(value)))
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(4, 3, 4, 3)
                action_layout.setSpacing(6)
                edit_button = QPushButton("D\u00fczenle")
                edit_button.clicked.connect(
                    lambda _checked=False, item_id=record_id: self.load_daily_wage_record(item_id)
                )
                delete_button = QPushButton("Sil")
                delete_button.setStyleSheet("background-color: #e74c3c; color: white; border: none; border-radius: 5px; padding: 5px 10px;")
                delete_button.clicked.connect(
                    lambda _checked=False, item_id=record_id: self.delete_daily_wage_record(item_id)
                )
                action_layout.addWidget(edit_button)
                action_layout.addWidget(delete_button)
                self.tbl_payroll.setCellWidget(row_index, 6, action_widget)
        except Exception as exc:
            logger.error("Daily wage list refresh error: %s", exc)

    def load_daily_wage_record(self, record_id):
        try:
            self.db.cursor.execute(
                "SELECT personnel_id, work_year, work_month, work_days, note "
                "FROM personnel_daily_wages WHERE id=?",
                (record_id,),
            )
            row = self.db.cursor.fetchone()
            if not row:
                return
            personnel_id, work_year, work_month, work_days, note = row
            self.cmb_month.setDate(QDate(int(work_year), int(work_month), 1))
            combo_index = self.cmb_personnel.findData(personnel_id)
            self.cmb_personnel.setCurrentIndex(max(0, combo_index))
            self.spin_work_days.setValue(float(work_days))
            self.inp_daily_note.setText(note or "")
            self.refresh_daily_wage_preview()
        except Exception as exc:
            logger.error("Daily wage record load error: %s", exc)

    def delete_daily_wage_record(self, record_id):
        try:
            self.db.cursor.execute(
                "SELECT accounting_id FROM personnel_daily_wages WHERE id=?",
                (record_id,),
            )
            row = self.db.cursor.fetchone()
            if not row:
                return
            accounting_id = row[0]
            self.db.cursor.execute("DELETE FROM personnel_daily_wages WHERE id=?", (record_id,))
            if accounting_id:
                self.db.cursor.execute("DELETE FROM accounting WHERE id=?", (accounting_id,))
            self.db.conn.commit()
            show_success(self.window(), "Yevmiye kayd\u0131 ve ilgili gider fi\u015fi silindi.")
            self.refresh_daily_wage_list()
        except Exception as exc:
            self.db.conn.rollback()
            logger.error("Daily wage record delete error: %s", exc)
            show_error(self.window(), f"Yevmiye kayd\u0131 silinemedi: {exc}")

    def reset_form(self):
        """Reset form to 'Add Mode'"""
        self.editing_id = None
        self.btn_add.setText("EKLE")
        self.btn_add.setStyleSheet("background-color: #27ae60; color: white; border: none; padding: 10px 30px; font-weight: bold; border-radius: 4px;")
        
        self.inp_name.clear()
        self.inp_phone.clear()
        self.inp_tc.clear()
        self.inp_email.clear()
        self.inp_telegram.clear()
        self.inp_role.clear()
        self.inp_dept.clear()
        self.inp_salary.clear()
        self.cmb_employment_type.setCurrentIndex(0)
        self.inp_daily_wage.clear()
        self.inp_pass.clear()
        self.table.clearSelection()

    def edit_personnel(self, pid):
        """Populate form with personnel data for editing"""
        try:
            self.db.cursor.execute("SELECT * FROM personnel WHERE id=?", (pid,))
            row = self.db.cursor.fetchone()
            if row:
                # Map based on standard+extended schema
                # Assume: id(0), name(1), role(2), phone(3), salary(4), start(5), perf(6), tc(7), email(8), dept(9), pass(10), active(11), comm(12), telegram(13)
                
                # Retrieve column names to be safe
                columns = self.db._get_table_columns("personnel") if hasattr(self.db, "_get_table_columns") else []
                
                def get_val(col_name):
                    try:
                        idx = columns.index(col_name)
                        return str(row[idx]) if row[idx] is not None else ""
                    except ValueError:
                        return ""

                self.inp_name.setText(get_val('name'))
                self.inp_role.setText(get_val('role'))
                self.inp_phone.setText(get_val('phone'))
                self.inp_salary.setText(get_val('salary'))
                employment_type = get_val('employment_type') or "monthly"
                employment_index = self.cmb_employment_type.findData(employment_type)
                self.cmb_employment_type.setCurrentIndex(max(0, employment_index))
                self.inp_daily_wage.setText(get_val('daily_wage'))
                self.inp_tc.setText(get_val('tc_no'))
                self.inp_email.setText(get_val('email'))
                self.inp_dept.setText(get_val('department'))
                self.inp_telegram.setText(get_val('telegram_username'))

                self.editing_id = pid
                self.btn_add.setText("GÜNCELLE")
                self.btn_add.setStyleSheet("background-color: #f39c12; color: white; border: none; padding: 10px 30px; font-weight: bold; border-radius: 4px;")
                
                show_info(self.window(), f"'{get_val('name')}' düzenleniyor...")
                self.inp_name.setFocus()
        except Exception as e:
            show_error(self.window(), f"Veri okunamadı: {e}")

    def add_personnel(self):
        self.db.update_personnel_schema_extended()
        name = self.inp_name.text().strip()
        phone = self.inp_phone.text().strip()
        tc = self.inp_tc.text().strip()
        email = self.inp_email.text().strip()
        telegram = self.inp_telegram.text().strip()
        role = self.inp_role.text().strip()
        dept = self.inp_dept.text().strip()
        employment_type = self.cmb_employment_type.currentData() or "monthly"
        passw = self.inp_pass.text()

        # Validation
        if not name:
            show_warning(self.window(), "Personel Adı zorunludur. 👤")
            return
        
        try:
            salary = float(self.inp_salary.text().replace('.', '').replace(',', '.') or 0)
        except Exception:
            show_warning(self.window(), "Geçersiz maaş tutarı.")
            return

        try:
            daily_wage = float(self.inp_daily_wage.text().replace('.', '').replace(',', '.') or 0)
        except Exception:
            show_warning(self.window(), "Ge\u00e7ersiz g\u00fcnl\u00fck yevmiye tutar\u0131.")
            return
        if employment_type == "daily" and daily_wage <= 0:
            show_warning(self.window(), "Yevmiye ile \u00e7al\u0131\u015fan personel i\u00e7in g\u00fcnl\u00fck \u00fccret girilmelidir.")
            return

        # Prepare Password Hash if provided
        pass_hash = None
        if passw:
            password_error = validate_new_password(passw)
            if password_error:
                show_warning(self.window(), password_error)
                return
            pass_hash = hash_password(passw)

        try:
            if self.editing_id:
                # --- UPDATE MODE ---
                # Construct query dynamically or fixed
                query = """UPDATE personnel SET name=?, role=?, phone=?, salary=?, tc_no=?, email=?, department=?, telegram_username=?, employment_type=?, daily_wage=? WHERE id=?"""
                params = [name, role, phone, salary, tc, email, dept, telegram, employment_type, daily_wage, self.editing_id]
                
                self.db.cursor.execute(query, params)
                
                if pass_hash:
                    # Update password separately if provided
                    self.db.cursor.execute("UPDATE personnel SET password_hash=? WHERE id=?", (pass_hash, self.editing_id))
                
                self.db.conn.commit()
                show_success(self.window(), "Personel bilgileri güncellendi! ✅")
                self.reset_form()
                
            else:
                # --- INSERT MODE ---
                # Manual Insert including new columns
                self.db.cursor.execute("""
                    INSERT INTO personnel (name, role, phone, salary, tc_no, email, department, telegram_username, password_hash, employment_type, daily_wage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, role, phone, salary, tc, email, dept, telegram, pass_hash or "", employment_type, daily_wage))
                self.db.conn.commit()

                show_success(self.window(), "Personel eklendi. ✨")
                self.reset_form()
            
            self.refresh_personnel_list()
            self.refresh_personnel_dropdown()
            
        except Exception as e:
            self.db.conn.rollback()
            error_text = str(e).lower()
            if "no such column" in error_text:
                message = (
                    "Personel veritaban\u0131nda eksik bir alan bulundu. "
                    "Gerekli g\u00fcncelleme yap\u0131ld\u0131; kayd\u0131 tekrar kaydedin."
                )
            elif "unique constraint" in error_text:
                message = "Bu kullan\u0131c\u0131 ad\u0131 veya e-posta adresi zaten kay\u0131tl\u0131."
            else:
                message = "Personel kaydedilemedi. Zorunlu alanlar\u0131 ve girilen tutarlar\u0131 kontrol edin."
            logger.exception("Personnel save error: %s", e)
            show_error(self.window(), message)

    def show_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=10):
            return
        item = self.table.itemAt(pos)
        if not item: return
        
        row = item.row()
        pid = self.table.item(row, 0).text() # ID column 0
        
        menu = QMenu(self)
        
        act_edit = QAction("📝 Düzenle", self)
        act_edit.triggered.connect(lambda: self.edit_personnel(pid))
        
        act_del = QAction("🗑️ Personel Çıkar", self)
        act_del.triggered.connect(lambda: self.delete_personnel(pid))
        menu.addAction(act_edit)
        menu.addSeparator()
        menu.addAction(act_del)
        
        menu.exec(self.table.viewport().mapToGlobal(pos))

    def delete_personnel(self, pid):
        from src.ui.dialogs.modern_confirm import ModernConfirmDialog
        correct_pass = self.db.get_setting("admin_pass", "")

        dlg = ModernConfirmDialog("Onay", "Personeli silmek istediğinize emin misiniz", correct_pass, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            try:
                self.db.cursor.execute(
                    "SELECT accounting_id FROM personnel_daily_wages WHERE personnel_id=?",
                    (pid,),
                )
                accounting_ids = [
                    row[0] for row in self.db.cursor.fetchall() if row[0]
                ]
                self.db.cursor.execute(
                    "DELETE FROM personnel_daily_wages WHERE personnel_id=?",
                    (pid,),
                )
                if accounting_ids:
                    placeholders = ", ".join("?" for _ in accounting_ids)
                    self.db.cursor.execute(
                        f"DELETE FROM accounting WHERE id IN ({placeholders})",
                        accounting_ids,
                    )
                self.db.cursor.execute("DELETE FROM personnel WHERE id=?", (pid,))
                self.db.conn.commit()
                show_success(self.window(), "Personel silindi.")
                self.refresh_personnel_list()
                self.refresh_personnel_dropdown()
                if self.editing_id == pid:
                    self.reset_form()
            except Exception as e:
                show_error(self.window(), f"Silme hatası: {e}")

    def refresh_personnel_list(self):
        self.table.setRowCount(0)
        try:
            self.db.cursor.execute("SELECT * FROM personnel")
            rows = self.db.cursor.fetchall()

            for r, row in enumerate(rows):
                self.table.insertRow(r)

                def get_val(row, col_name):
                    try:
                        val = row[col_name]
                        return str(val) if val is not None else ""
                    except (IndexError, KeyError):
                        return ""

                # Personnel table columns are kept compact for the management view.
                self.table.setItem(r, 0, QTableWidgetItem(get_val(row, 'id')))
                self.table.setItem(r, 1, QTableWidgetItem(get_val(row, 'name')))
                self.table.setItem(r, 2, QTableWidgetItem(get_val(row, 'role')))
                self.table.setItem(r, 3, QTableWidgetItem(get_val(row, 'department')))
                self.table.setItem(r, 4, QTableWidgetItem(get_val(row, 'phone')))
                self.table.setItem(r, 5, QTableWidgetItem(get_val(row, 'email')))
                self.table.setItem(r, 6, QTableWidgetItem(get_val(row, 'telegram_username')))
                self.table.setItem(r, 7, QTableWidgetItem(get_val(row, 'tc_no')))
                employment_type = get_val(row, 'employment_type') or "monthly"
                is_daily = employment_type == "daily"
                unit_wage = get_val(row, 'daily_wage') if is_daily else get_val(row, 'salary')
                self.table.setItem(r, 8, QTableWidgetItem("Yevmiye" if is_daily else "Ayl\u0131k Maa\u015f"))
                self.table.setItem(r, 9, QTableWidgetItem((unit_wage or "0") + " TL"))
        except Exception as e:
            logger.error("Personnel list refresh error: %s", e)

    def refresh_personnel_dropdown(self):
        self.cmb_personnel.blockSignals(True)
        self.cmb_personnel.clear()
        self.cmb_personnel.addItem("Personel se\u00e7in", None)
        try:
            self.db.cursor.execute("SELECT id, name FROM personnel")
            for pid, name in self.db.cursor.fetchall():
                self.cmb_personnel.addItem(name, pid)
        except Exception as e:
            logger.error("Personnel dropdown refresh error: %s", e)
        finally:
            self.cmb_personnel.blockSignals(False)
        if hasattr(self, "lbl_daily_rate"):
            self.refresh_daily_wage_preview()
        if hasattr(self, "tbl_payroll"):
            self.refresh_daily_wage_list()

    def open_add_transaction_dialog(self):
        try:
            from src.ui.dialogs.transaction_dialog import TransactionAddDialog

            # Prepare personnel dict {Name: ID}
            p_dict = {}
            # Skip "Tüm Personel" (index 0)
            for i in range(1, self.cmb_personnel.count()):
                p_dict[self.cmb_personnel.itemText(i)] = self.cmb_personnel.itemData(i)

            # Fallback if combo is empty or not loaded
            if not p_dict:
                try:
                    self.db.cursor.execute("SELECT name, id FROM personnel")
                    for name, pid in self.db.cursor.fetchall():
                        p_dict[name] = pid
                except Exception as e:
                    logger.warning(f"Personnel transaction dialog personnel fallback failed: {e}")

            dlg = TransactionAddDialog(self.db, self, p_dict)

            if dlg.exec():
                data = dlg.data
                if data:
                    final_desc = f"{data['personnel_name']} - {data['type']}: {data['desc']}"

                    # Add to accounting as Expense
                    try:
                        self.db.add_transaction(
                            category="Gider",
                            subcategory="Maaş/Prim",
                            amount=data['amount'],
                            description=final_desc,
                            customer_name=data['personnel_name']
                        )
                        show_success(self.window(), "Maaş/Prim işlemi kaydedildi. ✅")
                    except AttributeError:
                        # Fallback if add_transaction has different signature or db wrapper varies
                        self.db.cursor.execute(
                            "INSERT INTO accounting (category, type, amount, description, date, customer_name) VALUES (?, ?, ?, ?, ?, ?)",
                            ("Gider", "Maaş/Prim", data['amount'], final_desc, data['date'], data['personnel_name'])
                        )
                        self.db.conn.commit()
                        show_success(self.window(), "Kayıt eklendi.")

        except Exception as e:
            show_error(self.window(), f"İşlem hatası: {e}")

    def _wire_ui_signals(self):
        self.cmb_personnel.currentIndexChanged.connect(self._on_ui_widget_changed)
