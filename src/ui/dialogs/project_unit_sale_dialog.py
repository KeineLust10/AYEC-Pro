# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QComboBox, QDoubleSpinBox, QTabWidget, QTextEdit, QDateTimeEdit, 
                             QTableWidget, QHeaderView, QAbstractItemView, 
                             QListWidget, QFileDialog, QProgressDialog, QApplication, QMessageBox)
from PyQt6.QtCore import Qt, QDateTime, QUrl
from PyQt6.QtGui import QDesktopServices, QRegularExpressionValidator
from PyQt6.QtCore import QRegularExpression
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.message_helper import show_question
from src.ui.styles.tab_styles import TAB_STYLE
import json

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except Exception:
    QWebEngineView = None



class ProjectUnitSaleDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, project_id, unit_id, unit_name, parent=None):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            if geo.width() < 768:
                width = geo.width()
                height = geo.height()
            else:
                width = min(1100, int(geo.width() * 0.9))
                height = min(800, int(geo.height() * 0.9))
        else:
            width = 900
            height = 700
        super().__init__(parent, title=f" Daire Sat - {unit_name}", width=width, height=height)
        self.db = db
        self.project_id = project_id
        self.unit_id = unit_id
        self.unit_name = unit_name
        self._dirty = False
        self._saved = False
        self._updating_totals = False
        self.setup_ui()
        self._wire_ui_signals()
        self._load_personnel()
        self._check_unit_status()
        self._update_totals("init")

    def setup_ui(self):
        content = self.content_layout
        content.setSpacing(12)

        title = QLabel(f"{self.unit_name} Sat Kayd")
        title.setStyleSheet(theme_qss("font-size: 16px; font-weight: 800; color: @selection_text;"))
        content.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss(TAB_STYLE))
        content.addWidget(self.tabs, 1)

        self.tab_info = QWidget()
        self.tab_plan = QWidget()
        self.tab_docs = QWidget()
        self.tab_map = QWidget()
        self.tabs.addTab(self.tab_info, "Sat Bilgileri")
        self.tabs.addTab(self.tab_plan, "deme Plan")
        self.tabs.addTab(self.tab_docs, "Belgeler")
        self.tabs.addTab(self.tab_map, "Harita/Adres")

        self._build_info_tab()
        self._build_plan_tab()
        self._build_docs_tab()
        self._build_map_tab()

        footer = QHBoxLayout()
        footer.addStretch()
        btn_cancel = QPushButton("ptal")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(lambda: self.save_sale("save"))
        btn_save_print = QPushButton("Kaydet ve Yazdr")
        btn_save_print.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_save_print.clicked.connect(lambda: self.save_sale("print"))
        btn_proforma = QPushButton("Proforma Oluştur")
        btn_proforma.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_proforma.clicked.connect(lambda: self.save_sale("proforma"))
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_save)
        footer.addWidget(btn_save_print)
        footer.addWidget(btn_proforma)
        content.addLayout(footer)

    def _wire_ui_signals(self):
        self.cmb_sales_rep.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _input_qss(self):
        return """
            QLineEdit, QComboBox, QTextEdit, QDateTimeEdit {
                border: 1px solid @border;
                border-radius: 8px;
                padding: 8px 10px;
                background: @surface;
                font-size: 12px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus, QDateTimeEdit:focus {
                border-color: @accent;
            }
        """

    def _build_info_tab(self):
        layout = QVBoxLayout(self.tab_info)
        layout.setSpacing(10)

        label_buyer = QLabel("Alc Bilgileri")
        label_buyer.setStyleSheet(theme_qss("font-size: 13px; font-weight: 700; color: @text;"))
        layout.addWidget(label_buyer)

        buyer_form = QHBoxLayout()
        buyer_left = QVBoxLayout()
        buyer_right = QVBoxLayout()

        self.txt_buyer_name = QLineEdit()
        self.txt_buyer_name.setPlaceholderText("Ad Soyad")
        self.txt_buyer_name.setStyleSheet(theme_qss(self._input_qss()))
        self.txt_tc = QLineEdit()
        self.txt_tc.setPlaceholderText("TC Kimlik No")
        self.txt_tc.setMaxLength(11)
        self.txt_tc.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,11}")))
        self.txt_tc.setStyleSheet(theme_qss(self._input_qss()))
        self.txt_phone = QLineEdit()
        self.txt_phone.setPlaceholderText("Telefon")
        self.txt_phone.setStyleSheet(theme_qss(self._input_qss()))

        buyer_left.addWidget(self.txt_buyer_name)
        buyer_left.addWidget(self.txt_tc)
        buyer_left.addWidget(self.txt_phone)

        self.txt_email = QLineEdit()
        self.txt_email.setPlaceholderText("Email")
        self.txt_email.setStyleSheet(theme_qss(self._input_qss()))
        self.txt_address = QTextEdit()
        self.txt_address.setPlaceholderText("Adres")
        self.txt_address.setFixedHeight(90)
        self.txt_address.setStyleSheet(theme_qss(self._input_qss()))

        buyer_right.addWidget(self.txt_email)
        buyer_right.addWidget(self.txt_address)

        buyer_form.addLayout(buyer_left, 1)
        buyer_form.addLayout(buyer_right, 1)
        layout.addLayout(buyer_form)

        label_sale = QLabel("Sat Bilgileri")
        label_sale.setStyleSheet(theme_qss("font-size: 13px; font-weight: 700; color: @text;"))
        layout.addWidget(label_sale)

        sale_form = QHBoxLayout()
        sale_left = QVBoxLayout()
        sale_right = QVBoxLayout()

        self.spin_list_price = QDoubleSpinBox()
        self.spin_list_price.setRange(0, 1000000000)
        self.spin_list_price.setDecimals(2)
        self.spin_list_price.setSuffix(" ")
        DesignTokens.apply_spinbox_styles(self.spin_list_price)
        self.spin_sale_price = QDoubleSpinBox()
        self.spin_sale_price.setRange(0, 1000000000)
        self.spin_sale_price.setDecimals(2)
        self.spin_sale_price.setSuffix(" ")
        DesignTokens.apply_spinbox_styles(self.spin_sale_price)
        self.spin_down_rate = QDoubleSpinBox()
        self.spin_down_rate.setRange(0, 100)
        self.spin_down_rate.setDecimals(2)
        self.spin_down_rate.setSuffix(" %")
        DesignTokens.apply_spinbox_styles(self.spin_down_rate)
        self.spin_down_amount = QDoubleSpinBox()
        self.spin_down_amount.setRange(0, 1000000000)
        self.spin_down_amount.setDecimals(2)
        self.spin_down_amount.setSuffix(" ")
        DesignTokens.apply_spinbox_styles(self.spin_down_amount)
        self.spin_remaining = QDoubleSpinBox()
        self.spin_remaining.setRange(0, 1000000000)
        self.spin_remaining.setDecimals(2)
        self.spin_remaining.setSuffix(" ")
        self.spin_remaining.setReadOnly(True)
        self.spin_remaining.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        DesignTokens.apply_spinbox_styles(self.spin_remaining)

        sale_left.addWidget(QLabel("Liste Fiyat"))
        sale_left.addWidget(self.spin_list_price)
        sale_left.addWidget(QLabel("Sat Fiyat"))
        sale_left.addWidget(self.spin_sale_price)
        sale_left.addWidget(QLabel("Peinat Oran"))
        sale_left.addWidget(self.spin_down_rate)

        self.date_delivery = QDateTimeEdit()
        self.date_delivery.setCalendarPopup(True)
        self.date_delivery.setDateTime(QDateTime.currentDateTime())
        self.date_delivery.setMinimumDateTime(QDateTime.currentDateTime())
        self.date_delivery.setStyleSheet(theme_qss(self._input_qss()))

        self.cmb_sales_rep = QComboBox()
        self.cmb_sales_rep.setStyleSheet(theme_qss(self._input_qss()))

        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Notlar")
        self.txt_notes.setFixedHeight(90)
        self.txt_notes.setStyleSheet(theme_qss(self._input_qss()))

        sale_right.addWidget(QLabel("Peinat Tutar"))
        sale_right.addWidget(self.spin_down_amount)
        sale_right.addWidget(QLabel("Kalan Bakiye"))
        sale_right.addWidget(self.spin_remaining)
        sale_right.addWidget(QLabel("Teslim Tarihi"))
        sale_right.addWidget(self.date_delivery)
        sale_right.addWidget(QLabel("Sat Temsilcisi"))
        sale_right.addWidget(self.cmb_sales_rep)

        sale_form.addLayout(sale_left, 1)
        sale_form.addLayout(sale_right, 1)
        layout.addLayout(sale_form)
        layout.addWidget(QLabel("Notlar"))
        layout.addWidget(self.txt_notes)

        for widget in [
            self.txt_buyer_name, self.txt_tc, self.txt_phone, self.txt_email, self.txt_address,
            self.spin_list_price, self.spin_sale_price, self.spin_down_rate, self.spin_down_amount,
            self.date_delivery, self.cmb_sales_rep, self.txt_notes
        ]:
            if hasattr(widget, "textChanged"):
                widget.textChanged.connect(self._mark_dirty)
            if hasattr(widget, "valueChanged"):
                widget.valueChanged.connect(self._mark_dirty)

        self.spin_sale_price.valueChanged.connect(lambda: self._update_totals("sale"))
        self.spin_down_rate.valueChanged.connect(lambda: self._update_totals("rate"))
        self.spin_down_amount.valueChanged.connect(lambda: self._update_totals("amount"))

    def _build_plan_tab(self):
        layout = QVBoxLayout(self.tab_plan)
        self.tbl_plan = QTableWidget()
        self.tbl_plan.setColumnCount(3)
        self.tbl_plan.setHorizontalHeaderLabels(["Tarih", "Tutar", "Durum"])
        self.tbl_plan.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tbl_plan.verticalHeader().setVisible(False)
        self.tbl_plan.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tbl_plan.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tbl_plan.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.tbl_plan)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Satr Ekle")
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_add.clicked.connect(self._add_plan_row)
        btn_remove = QPushButton("Satr Sil")
        btn_remove.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_remove.clicked.connect(self._remove_plan_row)
        btn_row.addStretch()
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        layout.addLayout(btn_row)

    def _build_docs_tab(self):
        layout = QVBoxLayout(self.tab_docs)
        self.list_docs = QListWidget()
        self.list_docs.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.list_docs)
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Belge Ekle")
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_add.clicked.connect(self._add_doc)
        btn_remove = QPushButton("Belge Kaldr")
        btn_remove.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_remove.clicked.connect(self._remove_doc)
        btn_row.addStretch()
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        layout.addLayout(btn_row)

    def _build_map_tab(self):
        layout = QVBoxLayout(self.tab_map)
        search_row = QHBoxLayout()
        self.txt_map_query = QLineEdit()
        self.txt_map_query.setPlaceholderText("Adres veya koordinat")
        self.txt_map_query.setStyleSheet(theme_qss(self._input_qss()))
        btn_search = QPushButton("Ara")
        btn_search.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_search.clicked.connect(self._load_map)
        btn_external = QPushButton("Haritada A")
        btn_external.setStyleSheet(theme_qss(DesignTokens.get_button_qss("ghost")))
        btn_external.clicked.connect(self._open_external_map)
        search_row.addWidget(self.txt_map_query, 1)
        search_row.addWidget(btn_search)
        search_row.addWidget(btn_external)
        layout.addLayout(search_row)

        if QWebEngineView:
            self.map_view = QWebEngineView()
            layout.addWidget(self.map_view, 1)
        else:
            self.map_view = None
            self.txt_map_fallback = QTextEdit()
            self.txt_map_fallback.setReadOnly(True)
            self.txt_map_fallback.setStyleSheet(theme_qss(self._input_qss()))
            self.txt_map_fallback.setText("Harita bileeni bulunamad. Haritada A ile tarayc kullanabilirsiniz.")
            layout.addWidget(self.txt_map_fallback, 1)

    def _load_personnel(self):
        self.cmb_sales_rep.clear()
        self.cmb_sales_rep.addItem("Atanmad")
        try:
            self.db.cursor.execute("SELECT name FROM personnel ORDER BY name")
            rows = self.db.cursor.fetchall()
            for r in rows:
                name = r[0] if isinstance(r, (list, tuple)) else r.get("name")
                if name:
                    self.cmb_sales_rep.addItem(name)
        except Exception:
            pass

    def _check_unit_status(self):
        try:
            self.db.cursor.execute("SELECT status FROM project_units WHERE id=?", (self.unit_id,))
            row = self.db.cursor.fetchone()
            if not row:
                show_error(self, "Daire bilgisi bulunamad.")
                self.reject()
                return
            status = row[0] if not isinstance(row, dict) else row.get("status")
            if status == "Satld":
                show_warning(self, "Bu daire zaten satlm.")
                self._disable_form()
        except Exception as e:
            show_error(self, f"Durum okunamad: {e}")

    def _disable_form(self):
        for widget in [
            self.txt_buyer_name, self.txt_tc, self.txt_phone, self.txt_email, self.txt_address,
            self.spin_list_price, self.spin_sale_price, self.spin_down_rate, self.spin_down_amount,
            self.date_delivery, self.cmb_sales_rep, self.txt_notes, self.tabs
        ]:
            widget.setEnabled(False)

    def _add_plan_row(self):
        row = self.tbl_plan.rowCount()
        self.tbl_plan.insertRow(row)
        date_edit = QDateTimeEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDateTime(QDateTime.currentDateTime())
        date_edit.setStyleSheet(theme_qss(self._input_qss()))
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 1000000000)
        amount_spin.setDecimals(2)
        amount_spin.setSuffix(" ")
        DesignTokens.apply_spinbox_styles(amount_spin)
        status_combo = QComboBox()
        status_combo.addItems(["Bekliyor", "Ödendi"])
        status_combo.setStyleSheet(theme_qss(self._input_qss()))
        self.tbl_plan.setCellWidget(row, 0, date_edit)
        self.tbl_plan.setCellWidget(row, 1, amount_spin)
        self.tbl_plan.setCellWidget(row, 2, status_combo)
        date_edit.dateTimeChanged.connect(self._mark_dirty)
        amount_spin.valueChanged.connect(self._mark_dirty)
        status_combo.currentIndexChanged.connect(self._mark_dirty)
        self._mark_dirty()

    def _remove_plan_row(self):
        row = self.tbl_plan.currentRow()
        if row >= 0:
            self.tbl_plan.removeRow(row)
            self._mark_dirty()

    def _add_doc(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Belge Se", "", "Tm Dosyalar (*.*)")
        for f in files:
            self.list_docs.addItem(f)
        if files:
            self._mark_dirty()

    def _remove_doc(self):
        row = self.list_docs.currentRow()
        if row >= 0:
            self.list_docs.takeItem(row)
            self._mark_dirty()

    def _load_map(self):
        query = self.txt_map_query.text().strip()
        if not query:
            query = self.txt_address.toPlainText().strip()
        if not query:
            return
        url = QUrl(f"https://www.google.com/maps/search/api=1&query={QUrl.toPercentEncoding(query).data().decode()}")
        if self.map_view:
            self.map_view.load(url)
        else:
            self.txt_map_fallback.setText(url.toString())

    def _open_external_map(self):
        query = self.txt_map_query.text().strip()
        if not query:
            query = self.txt_address.toPlainText().strip()
        if not query:
            return
        url = QUrl(f"https://www.google.com/maps/search/api=1&query={QUrl.toPercentEncoding(query).data().decode()}")
        QDesktopServices.openUrl(url)

    def _mark_dirty(self):
        self._dirty = True

    def _update_totals(self, source):
        if self._updating_totals:
            return
        self._updating_totals = True
        sale_price = self.spin_sale_price.value()
        if source in ["rate", "sale", "init"]:
            down_amount = sale_price * (self.spin_down_rate.value() / 100)
            self.spin_down_amount.setValue(down_amount)
        elif source == "amount":
            if sale_price > 0:
                rate = (self.spin_down_amount.value() / sale_price) * 100
                self.spin_down_rate.setValue(rate)
        remaining = max(0, sale_price - self.spin_down_amount.value())
        self.spin_remaining.setValue(remaining)
        self._updating_totals = False

    def _validate_tc(self, tc):
        if not tc.isdigit() or len(tc) != 11 or tc[0] == "0":
            return False
        digits = [int(d) for d in tc]
        odd_sum = sum(digits[0:9:2])
        even_sum = sum(digits[1:8:2])
        digit10 = ((odd_sum * 7) - even_sum) % 10
        digit11 = (odd_sum + even_sum + digit10) % 10
        return digits[9] == digit10 and digits[10] == digit11

    def _collect_plan(self):
        plan = []
        for row in range(self.tbl_plan.rowCount()):
            date_edit = self.tbl_plan.cellWidget(row, 0)
            amount_spin = self.tbl_plan.cellWidget(row, 1)
            status_combo = self.tbl_plan.cellWidget(row, 2)
            if not date_edit or not amount_spin or not status_combo:
                continue
            plan.append({
                "date": date_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
                "amount": amount_spin.value(),
                "status": status_combo.currentText()
            })
        return plan

    def _collect_docs(self):
        docs = []
        for i in range(self.list_docs.count()):
            docs.append(self.list_docs.item(i).text())
        return docs

    def closeEvent(self, event):
        if self._dirty and not self._saved:
            reply = show_question(self, "Uyarı", "Kaydedilmemiş değişiklikler var. Kapatılsın mı?")
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
        event.accept()

    def save_sale(self, action):
        buyer_name = self.txt_buyer_name.text().strip()
        buyer_tc = self.txt_tc.text().strip()
        buyer_phone = self.txt_phone.text().strip()
        buyer_email = self.txt_email.text().strip()
        buyer_address = self.txt_address.toPlainText().strip()
        delivery_dt = self.date_delivery.dateTime()
        sales_rep = self.cmb_sales_rep.currentText().strip()
        list_price = self.spin_list_price.value()
        sale_price = self.spin_sale_price.value()
        down_rate = self.spin_down_rate.value()
        down_amount = self.spin_down_amount.value()
        remaining = self.spin_remaining.value()

        if not all([buyer_name, buyer_tc, buyer_phone, buyer_email, buyer_address]):
            show_warning(self, "Tm alc bilgileri zorunludur.")
            return
        if not self._validate_tc(buyer_tc):
            show_warning(self, "TC Kimlik No geersiz.")
            return
        if delivery_dt < QDateTime.currentDateTime():
            show_warning(self, "Teslim tarihi gemi olamaz.")
            return
        if sale_price <= 0:
            show_warning(self, "Sat fiyat 0 olamaz.")
            return

        progress = QProgressDialog("Sat kaydediliyor...", "", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.show()

        try:
            self.db.cursor.execute("SELECT status FROM project_units WHERE id=?", (self.unit_id,))
            status_row = self.db.cursor.fetchone()
            current_status = status_row[0] if not isinstance(status_row, dict) else status_row.get("status")
            if current_status == "Satld":
                progress.close()
                show_warning(self, "Bu daire daha nce satlm.")
                return

            payment_plan = json.dumps(self._collect_plan(), ensure_ascii=False)
            documents = json.dumps(self._collect_docs(), ensure_ascii=False)

            self.db.add_project_unit_sale({
                "project_id": self.project_id,
                "unit_id": self.unit_id,
                "buyer_name": buyer_name,
                "buyer_tc": buyer_tc,
                "buyer_phone": buyer_phone,
                "buyer_email": buyer_email,
                "buyer_address": buyer_address,
                "delivery_date": delivery_dt.toString("yyyy-MM-dd HH:mm:ss"),
                "sales_rep": sales_rep,
                "notes": self.txt_notes.toPlainText().strip(),
                "list_price": list_price,
                "sale_price": sale_price,
                "down_payment_rate": down_rate,
                "down_payment_amount": down_amount,
                "remaining_balance": remaining,
                "payment_plan": payment_plan,
                "documents": documents
            })

            self.db.cursor.execute("""
                UPDATE project_units
                SET status=?, price=?
                WHERE id=?
            """, ("Satıldı", sale_price, self.unit_id))

            desc = f"{self.unit_name} satış kaydı"
            self.db.add_project_transaction({
                'project_id': self.project_id,
                'type': 'Gelir',
                'category': 'Konut Satışı',
                'amount': sale_price,
                'payment_method': 'Sözleşme',
                'date': QDateTime.currentDateTime().toString("yyyy-MM-dd"),
                'description': desc,
                'status': 'Ödendi',
                'ref_table': 'project_units',
                'ref_id': self.unit_id
            })

            self.db.add_transaction(
                t_type="Gelir",
                category="Konut Satışı",
                amount=sale_price,
                description=f"{self.unit_name} satışı",
                customer_name=buyer_name,
                project_id=self.project_id
            )

            self.db.conn.commit()
            self._saved = True
            self._dirty = False

            if action == "print":
                show_success(self, "Sat kaydedildi ve yazdrma kuyrua alnd.")
            elif action == "proforma":
                show_success(self, "Sat kaydedildi ve proforma oluturuldu.")
            else:
                show_success(self, "Sat kaydedildi.")
            self.accept()
        except Exception as e:
            self.db.conn.rollback()
            show_error(self, f"Sat kaydedilemedi: {e}")
        finally:
            progress.close()
