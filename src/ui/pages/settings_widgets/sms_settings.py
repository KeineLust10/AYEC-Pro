# -*- coding: utf-8 -*-

"""
SMS Settings Widget
SMS ayarlari ve sablon yonetimi widget'lari.
"""

import html

from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QSpinBox,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
)
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinter

from src.utils.design_system import DesignTokens
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success



class SMSSettingsWidget(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """SMS Settings Tab"""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("SMS Ayarları")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        info = QLabel(
            "SMS gönderebilmeniz için önce iletimerkezi.com üzerinde hesap oluşturup "
            "kullanıcı adı ve şifrenizi aşağıdaki alanlara yazmanız gerekir.\n"
            "Not: Onaylı başlık ilk kayıtta varsayılan olarak oluşabilir. Kendinize özel "
            "başlık için servis sağlayıcı panelinden başvuru yapın."
        )
        info.setWordWrap(True)
        info.setStyleSheet(theme_qss(
            "background: @surface; color: @text_muted; padding: 14px 16px; border: 1px solid @border; border-radius: 12px;"
        ))
        layout.addWidget(info)

        cred_card = QFrame()
        cred_card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 16px;"))
        cred_card_layout = QVBoxLayout(cred_card)
        cred_card_layout.setContentsMargins(20, 20, 20, 20)
        cred_card_layout.setSpacing(14)
        cred_layout = QHBoxLayout()

        def create_input(label, placeholder="", is_password=False):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            if is_password:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setMinimumHeight(42)
            inp.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            lbl.setStyleSheet(theme_qss("color: @text;"))
            l.addWidget(lbl)
            l.addWidget(inp)
            return w, inp

        w1, self.inp_user = create_input("Kullanıcı Adı", "Kullanıcı Adı")
        cred_layout.addWidget(w1)

        w2, self.inp_pass = create_input("Şifre", "Şifre", True)
        cred_layout.addWidget(w2)

        w3, self.inp_title = create_input("Onaylı Başlık", "Onaylı Başlık")
        cred_layout.addWidget(w3)

        w4 = QWidget()
        l4 = QVBoxLayout(w4)
        l4.setContentsMargins(0, 0, 0, 0)
        lbl4 = QLabel("Durum")
        lbl4.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl4.setStyleSheet(theme_qss("color: @text;"))
        self.cmb_status = QComboBox()
        self.cmb_status.addItems(["Pasif", "Aktif"])
        self.cmb_status.setFixedHeight(35)
        self.cmb_status.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        l4.addWidget(lbl4)
        l4.addWidget(self.cmb_status)
        cred_layout.addWidget(w4)

        cred_card_layout.addLayout(cred_layout)

        btn_update_cred = QPushButton("GÜNCELLE")
        btn_update_cred.setFixedWidth(140)
        btn_update_cred.setMinimumHeight(42)
        btn_update_cred.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_update_cred.clicked.connect(self.save_credentials)
        cred_card_layout.addWidget(btn_update_cred, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(cred_card)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("margin-top: 20px; margin-bottom: 20px;")
        layout.addWidget(line)

        loop_title = QLabel("SMS GÖNDERİM DÖNGÜ AYARLARI")
        loop_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        loop_title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(loop_title)

        loop_desc = QLabel("Belirli durum kodlarına göre otomatik gönderilen SMS'lerin gün döngüsünü belirleyebilirsiniz.")
        loop_desc.setWordWrap(True)
        loop_desc.setStyleSheet(theme_qss("color: @text_muted; margin-bottom: 10px;"))
        layout.addWidget(loop_desc)

        loop_card = QFrame()
        loop_card.setStyleSheet(theme_qss("background: @surface; border: 1px solid @border; border-radius: 16px;"))
        loop_card_layout = QVBoxLayout(loop_card)
        loop_card_layout.setContentsMargins(20, 20, 20, 20)
        loop_card_layout.setSpacing(14)
        loop_layout = QHBoxLayout()

        def create_spin(label):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text;"))
            spn = QSpinBox()
            spn.setRange(0, 365)
            spn.setSuffix(" gün")
            spn.setFixedHeight(42)
            spn.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
            l.addWidget(lbl)
            l.addWidget(spn)
            return w, spn

        l1, self.spn_repaired = create_spin("TAMİRDE")
        loop_layout.addWidget(l1)
        l2, self.spn_approval = create_spin("ONAY BEKLİYOR")
        loop_layout.addWidget(l2)
        l3, self.spn_parts = create_spin("PARÇA BEKLİYOR")
        loop_layout.addWidget(l3)
        l4, self.spn_testing = create_spin("TEST SÜRECİNDE")
        loop_layout.addWidget(l4)
        l5, self.spn_done = create_spin("TAMİR EDİLDİ")
        loop_layout.addWidget(l5)

        loop_card_layout.addLayout(loop_layout)

        btn_update_loop = QPushButton("GÜNCELLE")
        btn_update_loop.setFixedWidth(140)
        btn_update_loop.setMinimumHeight(42)
        btn_update_loop.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success", size="md")))
        btn_update_loop.clicked.connect(self.save_loops)
        loop_card_layout.addWidget(btn_update_loop, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(loop_card)
        layout.addStretch()

    def _wire_ui_signals(self):
        self.cmb_status.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        self.inp_user.setText(self.db.get_setting("sms_username", ""))
        self.inp_pass.setText(self.db.get_setting("sms_password", ""))
        self.inp_title.setText(self.db.get_setting("sms_title", ""))
        status = self.db.get_setting("sms_active", "0")
        self.cmb_status.setCurrentIndex(1 if status == "1" else 0)

        self.spn_repaired.setValue(int(self.db.get_setting("loop_repaired", "0")))
        self.spn_approval.setValue(int(self.db.get_setting("loop_approval", "0")))
        self.spn_parts.setValue(int(self.db.get_setting("loop_parts", "0")))
        self.spn_testing.setValue(int(self.db.get_setting("loop_testing", "0")))
        self.spn_done.setValue(int(self.db.get_setting("loop_done", "0")))

    def save_credentials(self):
        self.db.set_setting("sms_username", self.inp_user.text())
        self.db.set_setting("sms_password", self.inp_pass.text())
        self.db.set_setting("sms_title", self.inp_title.text())
        self.db.set_setting("sms_active", "1" if self.cmb_status.currentIndex() == 1 else "0")
        if self.main_window:
            self.main_window.show_notification("SMS kimlik bilgileri güncellendi.", "success")

    def save_loops(self):
        self.db.set_setting("loop_repaired", str(self.spn_repaired.value()))
        self.db.set_setting("loop_approval", str(self.spn_approval.value()))
        self.db.set_setting("loop_parts", str(self.spn_parts.value()))
        self.db.set_setting("loop_testing", str(self.spn_testing.value()))
        self.db.set_setting("loop_done", str(self.spn_done.value()))
        if self.main_window:
            self.main_window.show_notification("Döngü ayarları güncellendi.", "success")


class TemplateEditDialog(ModernDialog):
    """SMS Sablon Duzenleme Dialog'u"""

    def __init__(self, name, content, parent=None):
        super().__init__("Şablon Düzenle", parent, width=600, height=450)
        self.name = name
        self.initial_content = content
        self.limit = 1000
        self.setup_content()

    def setup_content(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)

        info = QLabel(f"<b>{self.name}</b> şablonunu düzenliyorsunuz.")
        info.setStyleSheet("color: #2c3e50; font-size: 14px;")
        main_layout.addWidget(info)

        self.txt_content = QTextEdit()
        self.txt_content.setPlainText(self.initial_content)
        self.txt_content.setStyleSheet(DesignTokens.get_input_qss())
        self.txt_content.textChanged.connect(self.update_counter)
        main_layout.addWidget(self.txt_content)

        vars_info = QLabel("Kullanılabilir Değişkenler: {musteri}, {tutar}, {link}, {randevu}, {serino}")
        vars_info.setStyleSheet("color: #7f8c8d; font-size: 12px; font-style: italic;")
        main_layout.addWidget(vars_info)

        self.lbl_counter = QLabel(f"Karakter: {len(self.initial_content)}")
        self.lbl_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.lbl_counter)

        container = QWidget()
        container.setLayout(main_layout)
        self.add_widget(container)
        self.add_cancel_button("İptal")
        self.add_button("Kaydet", "primary", self.save)

    def update_counter(self):
        length = len(self.txt_content.toPlainText())
        self.lbl_counter.setText(f"Karakter: {length}")

    def save(self):
        self.new_content = self.txt_content.toPlainText()
        self.accept()

    def get_content(self):
        return self.new_content


class SMSTemplatesWidget(QWidget):
    """SMS Templates Tab"""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self.init_default_templates()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        title = QLabel("SMS Şablonları")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.addWidget(title)

        tools = [
            ("KOPYALA", self.copy_templates, "secondary"),
            ("EXCEL", self.export_templates_excel, "outline"),
            ("PDF", self.export_templates_pdf, "outline"),
        ]
        for text, callback, variant in tools:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(DesignTokens.get_button_qss(variant, size="sm"))
            btn.clicked.connect(callback)
            header.addWidget(btn)

        layout.addLayout(header)

        search_layout = QHBoxLayout()
        search_layout.addStretch()
        search_layout.addWidget(QLabel("Arama:"))
        self.inp_search = QLineEdit()
        self.inp_search.setFixedWidth(200)
        self.inp_search.setStyleSheet(DesignTokens.get_input_qss())
        self.inp_search.textChanged.connect(self.load_data)
        search_layout.addWidget(self.inp_search)
        layout.addLayout(search_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["SMS İÇERİĞİ", "EYLEM DURUMU", "DÜZENLE"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(DesignTokens.get_table_qss())
        layout.addWidget(self.table)

        footer_label = QLabel("Kayitlar listeleniyor.")
        footer_label.setStyleSheet("color: #7f8c8d; font-size: 12px;")
        layout.addWidget(footer_label)

    def init_default_templates(self):
        self.db.cursor.execute("SELECT COUNT(*) FROM whatsapp_templates")
        if self.db.cursor.fetchone()[0] == 0:
            defaults = [
                ("MANUEL BORC EKLEME", "Sayin {musteri}: {tutar} TL borc sisteme islenmistir. Kalan borcunuz: {bakiye} TL."),
                ("RANDEVU IPTAL SMS MUSTERIYE", "Sayin {musteri}: {randevu_araligi} tarihli randevunuz iptal edilmistir."),
                ("MOBIL ONAY", "Sayin {musteri}: lutfen cihazinizin tamiri icin belirlenen tutari onaylayiniz. Link: {link}"),
                ("RANDEVU OLUSTURULDU", "Sayin {musteri}: {randevu} tarihli randevunuz olusturulmustur."),
                ("PERIYODIK BAKIM", "Sayin {musteri}: {serino} nolu urununuzun bakim gunu gelmistir."),
            ]
            for name, content in defaults:
                self.db.add_template(name, content)

    def load_data(self):
        query = self.inp_search.text().lower()
        self.table.setRowCount(0)
        self.db.cursor.execute("SELECT * FROM whatsapp_templates")
        templates = self.db.cursor.fetchall()

        for row_data in templates:
            tid, name, content = row_data

            if query and query not in name.lower() and query not in content.lower():
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(content))
            self.table.setItem(row, 1, QTableWidgetItem(name))

            btn_edit = QPushButton("Düzenle")
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(DesignTokens.get_button_qss("warning", size="sm"))
            btn_edit.clicked.connect(lambda checked, i=tid, n=name, c=content: self.edit_template(i, n, c))
            self.table.setCellWidget(row, 2, btn_edit)

    def _template_rows(self):
        rows = []
        for row in range(self.table.rowCount()):
            content = self.table.item(row, 0)
            status = self.table.item(row, 1)
            rows.append((
                content.text() if content else "",
                status.text() if status else "",
            ))
        return rows

    def copy_templates(self):
        rows = self._template_rows()
        if not rows:
            show_error(self, "Kopyalanacak SMS \u015fablonu bulunamad\u0131.")
            return
        lines = ["SMS Icerigi\tEylem Durumu"]
        lines.extend("\t".join(row) for row in rows)
        QApplication.clipboard().setText("\n".join(lines))
        show_success(self, "SMS \u015fablonlar\u0131 panoya kopyaland\u0131.")

    def export_templates_excel(self):
        rows = self._template_rows()
        if not rows:
            show_error(self, "D\u0131\u015fa aktar\u0131lacak SMS \u015fablonu bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "SMS \u015eablonlar\u0131 Excel \u00c7\u0131kt\u0131s\u0131",
            "sms_sablonlari.xlsx",
            "Excel Dosyas\u0131 (*.xlsx)",
        )
        if not path:
            return
        try:
            import pandas as pd

            pd.DataFrame(rows, columns=["SMS Icerigi", "Eylem Durumu"]).to_excel(path, index=False)
            show_success(self, "SMS \u015fablonlar\u0131 Excel dosyas\u0131na aktar\u0131ld\u0131.")
        except Exception as exc:
            show_error(self, f"Excel \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def _templates_document(self):
        rows = "".join(
            "<tr><td>" + html.escape(content) + "</td><td>" + html.escape(status) + "</td></tr>"
            for content, status in self._template_rows()
        )
        document = QTextDocument(self)
        document.setHtml(
            "<h2>SMS Sablonlari</h2>"
            "<table border='1' cellspacing='0' cellpadding='6'>"
            "<thead><tr><th>SMS Icerigi</th><th>Eylem Durumu</th></tr></thead>"
            "<tbody>" + rows + "</tbody></table>"
        )
        return document

    def export_templates_pdf(self):
        if not self._template_rows():
            show_error(self, "PDF olarak kaydedilecek SMS \u015fablonu bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "SMS \u015eablonlar\u0131 PDF \u00c7\u0131kt\u0131s\u0131",
            "sms_sablonlari.pdf",
            "PDF Dosyas\u0131 (*.pdf)",
        )
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self._templates_document().print(printer)
            show_success(self, "SMS \u015fablonlar\u0131 PDF dosyas\u0131na kaydedildi.")
        except Exception as exc:
            show_error(self, f"PDF \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def edit_template(self, tid, name, content):
        dlg = TemplateEditDialog(name, content, self)
        if dlg.exec():
            new_content = dlg.get_content()
            self.db.cursor.execute("UPDATE whatsapp_templates SET content=? WHERE id=?", (new_content, tid))
            self.db.conn.commit()
            self.load_data()
            if self.main_window:
                self.main_window.show_notification("Şablon güncellendi.", "success")
