# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, 
                             QComboBox, QTableWidget, QHeaderView, QPushButton, 
                             QTableWidgetItem, QScrollArea, QGroupBox, QTextEdit, 
                             QLineEdit, QFormLayout, QFileDialog, QTabWidget)

from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.logger import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime

from src.utils.pdf_generator import generate_service_html
from src.ui.widgets.qr_widget import QRWidget
from src.ui.widgets.signature_widget import SignatureWidget
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.date_formatter import format_date
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss


class ReportDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, device_data, parent=None):
        super().__init__(parent=parent, title=f"Servis Formu ve Test Raporu - {device_data[1]}", width=1080, height=820)
        self.db = db
        self.device = device_data
        self.tracking_no = device_data[1]
        self._apply_modern_styles()
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def _apply_modern_styles(self):
        content_widget = getattr(self, "content_widget", None) or getattr(self, "content_container", None)
        if content_widget is not None:
            content_widget.setStyleSheet(theme_qss("background-color: @surface;"))

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_from_try(
            amount,
            db=self.db,
            currency_code=CurrencyHelper.get_code(self.db),
            include_try_reference=include_try_reference,
        )

    def _get_service_contract_text(self):
        saved_contract = str(self.db.get_setting("service_contract", "") or "").strip()
        if saved_contract:
            return saved_contract
        return (
            f"1. Servisimize bırakılan cihazların arıza tespiti sonrasında onay verilmezse {self._fmt_try(200)} arıza tespit ücreti alınır.\n"
            "2. Sıvı temaslı cihazlarda onarım garantisi verilmemektedir.\n"
            "3. 90 gün içerisinde teslim alınmayan cihazlardan firmamız sorumlu değildir.\n"
            "4. Yedek parça değişimlerinde orijinal veya A kalite muadil parça kullanılır.\n"
            "5. Kullanıcı verilerinin yedeği müşterinin sorumluluğundadır. Veri kaybından servisimiz sorumlu tutulamaz.\n"
            "6. Onarım sonrası değiştirilen parçalar için garanti süresi 6 aydır.\n"
            "7. Müşteri bu formu imzalayarak yukarıdaki şartları kabul etmiş sayılır."
        )

    def setup_ui(self):
        intro = QLabel("Test kayıtlarını, servis sözleşmesini ve yazdırma akışını tek pencereden yönetin.")
        intro.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        intro.setWordWrap(True)
        self.content_layout.addWidget(intro)
        
        # Tab Yapısı
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane {
                border: 1px solid @border;
                border-radius: 12px;
                background: @surface;
                padding: 8px;
            }
            QTabBar::tab {
                background: @surface_alt;
                color: @text;
                padding: 10px 16px;
                border: 1px solid @border;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 6px;
                font-weight: 700;
            }
            QTabBar::tab:selected {
                background: @accent;
                color: @selection_text;
                border-color: @accent;
            }
        """))
        
        # TAB 1: Test Kontrol Listesi
        self.tab_tests = QWidget()
        self.setup_tests_tab()
        self.tabs.addTab(self.tab_tests, "Donanım Testleri")
        
        # TAB 2: Servis Formu ve Fiyatlandırma
        self.tab_form = QWidget()
        self.setup_form_tab()
        self.tabs.addTab(self.tab_form, "Servis Formu ve Fiyat")
        
        self.content_layout.addWidget(self.tabs, 1)

    def _wire_ui_signals(self):
        self.combo_tech.currentIndexChanged.connect(self._on_ui_widget_changed)

    def setup_tests_tab(self):
        layout = QVBoxLayout(self.tab_tests)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Üst Bilgi ve Teknisyen Seçimi
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Cihaz fonksiyon testlerini işaretleyiniz:"))
        top_layout.addStretch()
        
        self.combo_tech = QComboBox()
        self.combo_tech.addItem("Teknisyen Seçiniz")
        personnel = self.db.get_all_personnel()
        for p in personnel:
            self.combo_tech.addItem(p[1]) # p[1] is name
        
        top_layout.addWidget(QLabel("İşlemi Yapan:"))
        top_layout.addWidget(self.combo_tech)
        
        layout.addLayout(top_layout)
        
        self.test_table = QTableWidget()
        self.test_table.setColumnCount(2)
        self.test_table.setHorizontalHeaderLabels(["Bileşen", "Test Sonucu"])
        self.test_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.test_table.setStyleSheet(theme_qss("""
            QTableWidget {
                background: @surface;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                gridline-color: @border;
                outline: none;
            }
            QTableWidget::item {
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background: @surface_alt;
                color: @text;
                border: none;
                border-bottom: 1px solid @border;
                padding: 10px;
                font-weight: 800;
            }
        """))
        
        components = [
            "Ekran / Dokunmatik", "Batarya / Şarj", "Kamera (Ön/Arka)", 
            "Mikrofon / Hoparlör", "Wi-Fi / Bluetooth", "Sensörler", 
            "Tuşlar (Güç/Ses)", "Kasa / Kozmetik", "Yazılım / Sistem",
            "FaceID / TouchID", "Yakınlık Sensörü", "Titreşim Motoru"
        ]
        
        self.test_table.setRowCount(len(components))
        
        self.combos = []
        for i, comp in enumerate(components):
            self.test_table.setItem(i, 0, QTableWidgetItem(comp))
            
            combo = QComboBox()
            combo.addItems(["Test Edilmedi", "Geçti", "Kaldı"])
            self.test_table.setCellWidget(i, 1, combo)
            self.combos.append(combo)
            
        layout.addWidget(self.test_table)
        
        btn_save_tests = QPushButton("Test Sonuçlarını Kaydet")
        btn_save_tests.clicked.connect(self.save_tests)
        btn_save_tests.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save_tests.setStyleSheet(theme_qss("background: @warning; color: @selection_text; padding: 10px; border-radius: 10px; font-weight: 700;"))
        layout.addWidget(btn_save_tests)

    def setup_form_tab(self):
        layout = QHBoxLayout(self.tab_form)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(14)
        
        # Sol Taraf: Detaylar, Fiyat ve Şartlar
        left_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(theme_qss("QScrollArea { background: transparent; border: none; }"))
        left_content = QWidget()
        left_vbox = QVBoxLayout(left_content)
        left_vbox.setSpacing(12)
        
        # Yapılan İşlemler
        grp_details = QGroupBox("Yapılan İşlemler (SMC Arızalı Notu)")
        vbox_det = QVBoxLayout()
        self.txt_repair_details = QTextEdit()
        self.txt_repair_details.setPlaceholderText("Arıza tespiti, uygulanan işlemler...")
        self.txt_repair_details.setMaximumHeight(100)
        vbox_det.addWidget(self.txt_repair_details)
        grp_details.setLayout(vbox_det)
        left_vbox.addWidget(grp_details)
        
        # Fiyatlandırma
        grp_price = QGroupBox("Fiyatlandırma")
        form_price = QFormLayout()
        
        self.lbl_parts_total = QLabel(self._fmt_try(0))
        self.inp_labor = QLineEdit("0")
        self.inp_labor.textChanged.connect(self.calculate_total)
        self.lbl_total = QLabel(self._fmt_try(0))
        self.lbl_total.setStyleSheet(theme_qss("font-size: 18px; font-weight: 900; color: @danger;"))
        
        # Kullanılan Parçalar Listesi
        self.list_parts = QTextEdit()
        self.list_parts.setReadOnly(True)
        self.list_parts.setMaximumHeight(80)
        
        form_price.addRow("Kullanılan Parçalar:", self.list_parts)
        form_price.addRow("Parça Toplamı:", self.lbl_parts_total)
        form_price.addRow("İşçilik Ücreti:", self.inp_labor)
        form_price.addRow("GENEL TOPLAM:", self.lbl_total)
        
        grp_price.setLayout(form_price)
        left_vbox.addWidget(grp_price)
        
        # Servis Şartları (Resim 17 referansı)
        grp_terms = QGroupBox("Servis Sözleşmesi ve Şartları")
        vbox_terms = QVBoxLayout()
        self.txt_terms = QTextEdit()
        self.txt_terms.setReadOnly(True)
        self.txt_terms.setPlainText(self._get_service_contract_text())
        self.txt_terms.setMaximumHeight(120)
        vbox_terms.addWidget(self.txt_terms)
        grp_terms.setLayout(vbox_terms)
        left_vbox.addWidget(grp_terms)
        
        scroll.setWidget(left_content)
        left_layout.addWidget(scroll)
        
        # Sağ Taraf: QR ve Onay
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        
        # QR Kod
        grp_qr = QGroupBox("Müşteri Takip QR")
        vbox_qr = QVBoxLayout()
        # QRWidget kullanılıyor (qrcode kütüphanesi ile gerçek QR)
        # Link: https://ayecpro.com/track/{tracking_no}
        qr_data = f"https://ayecpro.com/track/{self.tracking_no}"
        self.qr_widget = QRWidget(qr_data)
        vbox_qr.addWidget(self.qr_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        vbox_qr.addWidget(QLabel(f"Takip No: {self.tracking_no}"), alignment=Qt.AlignmentFlag.AlignCenter)
        grp_qr.setLayout(vbox_qr)
        right_layout.addWidget(grp_qr)
        
        # İmza Alanı (Görsel)
        grp_sign = QGroupBox("Teknik Onay ve İmza")
        vbox_sign = QVBoxLayout()
        vbox_sign.addWidget(QLabel("Teknisyen: Ali Veli")) # Dinamik olabilir
        vbox_sign.addWidget(QLabel("Tarih: " + format_date(datetime.now(), self.db)))
        
        self.signature_widget = SignatureWidget()
        vbox_sign.addWidget(self.signature_widget)
        
        btn_clear_sign = QPushButton("İmzayı Temizle")
        btn_clear_sign.clicked.connect(self.signature_widget.clear)
        vbox_sign.addWidget(btn_clear_sign)
        
        grp_sign.setLayout(vbox_sign)
        right_layout.addWidget(grp_sign)
        
        # Butonlar
        btn_print = QPushButton("PDF OLUŞTUR VE YAZDIR")
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet(theme_qss("background: @warning; color: @selection_text; padding: 15px; font-weight: 800; border-radius: 10px;"))
        btn_print.clicked.connect(self.print_form)
        
        btn_deliver = QPushButton("TESLİM ET VE TAHSİL ET")
        btn_deliver.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deliver.setStyleSheet(theme_qss("background: @accent; color: @selection_text; padding: 15px; font-weight: 800; border-radius: 10px;"))
        btn_deliver.clicked.connect(self.deliver_and_pay)
        
        right_layout.addStretch()
        right_layout.addWidget(btn_print)
        right_layout.addWidget(btn_deliver)
        
        layout.addLayout(left_layout, 60)
        layout.addLayout(right_layout, 40)

    def load_data(self):
        # Testleri Yükle
        saved_tests = self.db.get_test_results(self.tracking_no)
        for i in range(self.test_table.rowCount()):
            comp = self.test_table.item(i, 0).text()
            if comp in saved_tests:
                combo = self.test_table.cellWidget(i, 1)
                combo.setCurrentText(saved_tests[comp])
                
        # Parçaları Yükle
        parts = self.db.get_used_parts(self.tracking_no)
        parts_str = ""
        total_parts = 0
        for p in parts:
            parts_str += f"- {p[2]} ({self._fmt_try(p[3])})\n"
            total_parts += p[3]
            
        self.list_parts.setText(parts_str if parts_str else "Parça kullanılmadı.")
        self.lbl_parts_total.setText(self._fmt_try(total_parts))
        self.parts_total = total_parts
        
        # Mevcut Finansal Veriler (Varsa)
        self.db.cursor.execute("SELECT labor_cost, repair_details FROM devices WHERE tracking_no=?", (self.tracking_no,))
        row = self.db.cursor.fetchone()
        if row:
            labor = row[0] if row[0] else 0
            details = row[1] if row[1] else ""
            self.inp_labor.setText(str(labor))
            self.txt_repair_details.setText(details)
            
        self.calculate_total()

    def calculate_total(self):
        try:
            labor = float(self.inp_labor.text())
        except Exception:
            labor = 0
        
        total = self.parts_total + labor
        self.lbl_total.setText(self._fmt_try(total))

    def save_tests(self):
        tests = {}
        for i in range(self.test_table.rowCount()):
            comp = self.test_table.item(i, 0).text()
            res = self.test_table.cellWidget(i, 1).currentText()
            tests[comp] = res
            
        tech = self.combo_tech.currentText()
        if tech == "Teknisyen Seçiniz":
            tech = "Belirsiz"
            
        self.db.save_test_results(self.tracking_no, tests, tech)
        
        # Cihaz kaydına teknisyeni işle (Performans raporu için)
        try:
            self.db.cursor.execute("UPDATE devices SET technician=? WHERE tracking_no=?", (tech, self.tracking_no))
            self.db.conn.commit()
        except Exception as e:
            logger.error(f"ReportDialog technician update error: {e}")
            
        show_info(self, "Test sonuçları başarıyla kaydedildi.")

    def deliver_and_pay(self):
        # Onay
        if SimpleConfirmDialog(self, "Onay", "Cihaz teslim edilecek ve ücret muhasebeye işlenecek. Onaylıyor musunuz").exec() != QDialog.DialogCode.Accepted:
            return

        # Hesapla
        try:
            labor = float(self.inp_labor.text()) if self.inp_labor.text() else 0
        except Exception:
            labor = 0
            
        total = self.parts_total + labor
        
        # Muhasebeye İşle
        desc = f"Servis Geliri: {self.tracking_no} - {self.device[2]}"
        # Eğer teknisyen seçili ise açıklamaya ekle
        tech = self.combo_tech.currentText()
        if tech != "Teknisyen Seçiniz":
            desc += f" (Teknisyen: {tech})"
            
        self.db.add_transaction("Gelir", "Servis Hizmeti", total, desc)

        # --- GİDER KAYDI: Malzeme Maliyeti (COGS) ---
        try:
            # used_parts tablosundaki sütunları kontrol et
            self.db.cursor.execute("PRAGMA table_info(used_parts)")
            up_cols = [r[1] for r in self.db.cursor.fetchall()]
            has_pps = "purchase_price_snapshot" in up_cols
            del_col = "is_deleted" if "is_deleted" in up_cols else ("is_archived" if "is_archived" in up_cols else None)

            total_material_cost = 0.0
            cost_parts_list = []

            if has_pps:
                cost_query = "SELECT part_name, purchase_price_snapshot, quantity FROM used_parts WHERE tracking_no=?"
                if del_col:
                    cost_query += f" AND ({del_col}=0 OR {del_col} IS NULL)"
                cost_rows = self.db.cursor.execute(cost_query, (self.tracking_no,)).fetchall()
                for r in cost_rows:
                    pp = float(r[1] or 0)
                    qty = int(r[2] or 1) if len(r) > 2 else 1
                    if pp > 0:
                        total_material_cost += pp * qty
                        cost_parts_list.append(f"{r[0]}x{qty}")
            else:
                quantity_expr = (
                    "COALESCE(quantity, 1)" if "quantity" in up_cols else "1"
                )
                parts_query = (
                    f"SELECT part_name, {quantity_expr} FROM used_parts "
                    "WHERE tracking_no=?"
                )
                if del_col:
                    parts_query += f" AND COALESCE({del_col}, 0)=0"
                parts_rows = self.db.cursor.execute(parts_query, (self.tracking_no,)).fetchall()
                part_names = sorted(
                    {
                        str(row[0])
                        for row in parts_rows
                        if row and row[0] not in (None, "")
                    }
                )
                purchase_prices = {}
                if part_names:
                    placeholders = ", ".join("?" for _ in part_names)
                    price_rows = self.db.cursor.execute(
                        f"""
                        SELECT name, purchase_price
                        FROM parts
                        WHERE name IN ({placeholders})
                        """,
                        tuple(part_names),
                    ).fetchall()
                    purchase_prices = {
                        str(row[0]): float(row[1] or 0.0)
                        for row in price_rows
                    }
                for r in parts_rows:
                    part_name = str(r[0] or "")
                    quantity = float(r[1] or 1.0)
                    purchase_price = purchase_prices.get(part_name, 0.0)
                    if purchase_price > 0:
                        total_material_cost += purchase_price * quantity
                        cost_parts_list.append(f"{part_name}x{quantity:g}")

            if total_material_cost > 0:
                cost_desc = f"Servis Malzeme Maliyeti: {self.tracking_no}"
                if cost_parts_list:
                    cost_desc += f" [{', '.join(cost_parts_list)}]"
                self.db.add_transaction(
                    t_type="Gider",
                    category="Malzeme Maliyeti",
                    amount=total_material_cost,
                    description=cost_desc,
                    tracking_no=self.tracking_no,
                    ref_no=self.tracking_no,
                )
        except Exception as e:
            logger.error(f"ReportDialog COGS transaction error: {e}")
        
        # Cihaz Durumunu Güncelle
        try:
            from datetime import datetime
            now = datetime.now()
            self.db.cursor.execute(
                "UPDATE devices SET status='Teslim Edildi', price=?, labor_cost=?, exit_date=?, delivered_at=? WHERE tracking_no=?",
                (total, labor, now.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d %H:%M:%S"), self.tracking_no),
            )
            self.db.conn.commit()
            
            show_success(self, f"İşlem tamamlandı!\n{self._fmt_try(total)} tahsilat kaydedildi.")
            self.accept()
            # Parent window refresh
            if self.parent():
                if hasattr(self.parent(), 'refresh_logs'):
                    self.parent().refresh_logs()
        except Exception as e:
            show_error(self, f"Veritabanı hatası: {e}")

    def print_form(self):
        # Önce veriyi kaydet/güncelle
        labor = float(self.inp_labor.text()) if self.inp_labor.text() else 0
        details = self.txt_repair_details.toPlainText()
        self.db.update_financials(self.tracking_no, labor, details)
        
        # HTML İçerik Hazırla
        tech_name = self.combo_tech.currentText()
        if tech_name == "Teknisyen Seçiniz":
            tech_name = "Ali Veli" 

        html = generate_service_html(
            db=self.db,
            tracking_no=self.tracking_no,
            customer_name=self.device[2],
            device_info=f"{self.device[3]} {self.device[4]}",
            details=details,
            parts_list=self.list_parts.toPlainText(),
            labor_cost=labor,
            total_cost=self.lbl_total.text(),
            terms_text=self.txt_terms.toPlainText(),
            technician_name=tech_name
        )
        
        # Yazıcı Diyaloğu
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QPrintDialog.Accepted:
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(printer)
            show_success(self, "Yazdırma işlemi başarıyla tamamlandı.")
        
        # Opsiyonel: PDF olarak da kaydetmek isterse
        # İstenirse buraya 'Ayrıca PDF Kaydet' butonu eklenebilir ama kullanıcı 'Yazdır' istediği için QPrintDialog yeterli.
