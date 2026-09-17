# -*- coding: utf-8 -*-

import csv
import html

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QLineEdit,
                             QFileDialog, QGridLayout, QCheckBox, QSpinBox, QDoubleSpinBox, QHeaderView,
                             QTableWidget, QTableWidgetItem)
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

from src.utils import message_helper
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss, tc
from src.utils.toast_notification import show_success, show_error
from src.ui.widgets.animated_toggle import AnimatedToggle

class JobServiceNumberSettingsWidget(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self.load_numbers()

    def _spinbox_qss(self):
        """QSpinBox artırma/azaltma butonlarını görünür ve renkli yapar."""
        return theme_qss("""
            QSpinBox {
                border: 1px solid @border;
                border-radius: 5px;
                padding: 5px 36px 5px 8px;
                background-color: @surface;
                color: @text;
                font-size: 13px;
                min-height: 34px;
            }
            QSpinBox:focus {
                border: 1px solid @accent;
            }
            QSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 30px;
                min-height: 17px;
                border-left: 1px solid @border;
                border-bottom: 1px solid @border;
                border-top-right-radius: 4px;
                background-color: @accent;
            }
            QSpinBox::up-button:hover { background-color: @accent_hover; }
            QSpinBox::up-button:pressed { background-color: @success; }
            QSpinBox::up-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid white;
                width: 0; height: 0;
            }
            QSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 30px;
                min-height: 17px;
                border-left: 1px solid @border;
                border-top: 1px solid @border;
                border-bottom-right-radius: 4px;
                background-color: @accent;
            }
            QSpinBox::down-button:hover { background-color: @accent_hover; }
            QSpinBox::down-button:pressed { background-color: @success; }
            QSpinBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid white;
                width: 0; height: 0;
            }
        """)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("🧾 İş / Servis / Referans Takip Numaraları")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

        subtitle = QLabel("Yeni iş, servis, proje, referans ve ödeme numaralarının başlangıç değerlerini buradan yönetebilirsiniz.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        tools_layout = QHBoxLayout()
        tools = [
            ("KOPYALA", self.copy_number_settings, "warning"),
            ("CSV \u00c7IKTI", self.export_number_settings_csv, "secondary"),
            ("EXCEL \u00c7IKTI", self.export_number_settings_excel, "secondary"),
            ("PDF KAYDET", self.export_number_settings_pdf, "secondary"),
            ("YAZDIR", self.print_number_settings, "ghost"),
        ]
        for text, callback, variant in tools:
            button = QPushButton(text)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant, size="sm")))
            button.clicked.connect(callback)
            tools_layout.addWidget(button)
        tools_layout.addStretch()
        layout.addLayout(tools_layout)

        card = QFrame()
        card.setProperty("settingsCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)

        form = QGridLayout()
        form.setHorizontalSpacing(20)
        form.setVerticalSpacing(12)

        spn_qss = self._spinbox_qss()

        # İş Numarası Ayarları
        lbl_job_prefix = QLabel("İş Numarası Ön Ek")
        self.inp_job_prefix = QLineEdit()
        form.addWidget(lbl_job_prefix, 0, 0)
        form.addWidget(self.inp_job_prefix, 0, 1)

        lbl_job_next = QLabel("Sonraki İş Numarası")
        self.spn_job_next = QSpinBox()
        self.spn_job_next.setRange(0, 999999)
        self.spn_job_next.setStyleSheet(spn_qss)
        form.addWidget(lbl_job_next, 1, 0)
        form.addWidget(self.spn_job_next, 1, 1)

        # Servis Numarası Ayarları
        lbl_srv_prefix = QLabel("Servis Numarası Ön Ek")
        self.inp_srv_prefix = QLineEdit()
        form.addWidget(lbl_srv_prefix, 2, 0)
        form.addWidget(self.inp_srv_prefix, 2, 1)

        lbl_srv_next = QLabel("Sonraki Servis Numarası")
        self.spn_srv_next = QSpinBox()
        self.spn_srv_next.setRange(0, 999999)
        self.spn_srv_next.setStyleSheet(spn_qss)
        form.addWidget(lbl_srv_next, 3, 0)
        form.addWidget(self.spn_srv_next, 3, 1)

        # Proje Numarası Ayarları
        lbl_prj_prefix = QLabel("Proje Numarası Ön Ek")
        self.inp_prj_prefix = QLineEdit()
        form.addWidget(lbl_prj_prefix, 4, 0)
        form.addWidget(self.inp_prj_prefix, 4, 1)

        lbl_prj_next = QLabel("Sonraki Proje Numarası")
        self.spn_prj_next = QSpinBox()
        self.spn_prj_next.setRange(0, 999999)
        self.spn_prj_next.setStyleSheet(spn_qss)
        form.addWidget(lbl_prj_next, 5, 0)
        form.addWidget(self.spn_prj_next, 5, 1)

        # Referans Numarası Ayarları
        lbl_ref_prefix = QLabel("Referans Numarası Ön Ek")
        self.inp_ref_prefix = QLineEdit()
        form.addWidget(lbl_ref_prefix, 6, 0)
        form.addWidget(self.inp_ref_prefix, 6, 1)

        lbl_ref_next = QLabel("Sonraki Referans Numarası")
        self.spn_ref_next = QSpinBox()
        self.spn_ref_next.setRange(0, 999999)
        self.spn_ref_next.setStyleSheet(spn_qss)
        form.addWidget(lbl_ref_next, 7, 0)
        form.addWidget(self.spn_ref_next, 7, 1)

        # Ödeme Numarası Ayarları
        lbl_pay_prefix = QLabel("Ödeme Numarası Ön Ek")
        self.inp_pay_prefix = QLineEdit()
        form.addWidget(lbl_pay_prefix, 8, 0)
        form.addWidget(self.inp_pay_prefix, 8, 1)

        lbl_pay_next = QLabel("Sonraki Ödeme Numarası")
        self.spn_pay_next = QSpinBox()
        self.spn_pay_next.setRange(0, 999999)
        self.spn_pay_next.setStyleSheet(spn_qss)
        form.addWidget(lbl_pay_next, 9, 0)
        form.addWidget(self.spn_pay_next, 9, 1)

        card_layout.addLayout(form)

        btn_save = QPushButton("Kaydet")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setFixedHeight(38)
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(self.save_data)
        card_layout.addWidget(btn_save, 0, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(card)
        layout.addStretch()

    def load_numbers(self):
        job_prefix = self.db.get_setting("job_number_prefix", "JOB")
        job_next_raw = self.db.get_setting("job_number_next", "1")
        srv_prefix = self.db.get_setting("service_number_prefix", "SRV")
        srv_next_raw = self.db.get_setting("service_number_next", "1")
        prj_prefix = self.db.get_setting("project_number_prefix", "PRJ")
        prj_next_raw = self.db.get_setting("project_number_next", "1")
        ref_prefix = self.db.get_setting("reference_number_prefix", "REF")
        ref_next_raw = self.db.get_setting("reference_number_next", "1")
        pay_prefix = self.db.get_setting("payment_number_prefix", "PAY")
        pay_next_raw = self.db.get_setting("payment_number_next", "1")

        self.inp_job_prefix.setText(job_prefix)
        try:
            self.spn_job_next.setValue(int(job_next_raw))
        except Exception:
            self.spn_job_next.setValue(1)

        self.inp_srv_prefix.setText(srv_prefix)
        try:
            self.spn_srv_next.setValue(int(srv_next_raw))
        except Exception:
            self.spn_srv_next.setValue(1)

        self.inp_prj_prefix.setText(prj_prefix)
        try:
            self.spn_prj_next.setValue(int(prj_next_raw))
        except Exception:
            self.spn_prj_next.setValue(1)

        self.inp_ref_prefix.setText(ref_prefix)
        try:
            self.spn_ref_next.setValue(int(ref_next_raw))
        except Exception:
            self.spn_ref_next.setValue(1)

        self.inp_pay_prefix.setText(pay_prefix)
        try:
            self.spn_pay_next.setValue(int(pay_next_raw))
        except Exception:
            self.spn_pay_next.setValue(1)

    def save_data(self):
        self.db.set_setting("job_number_prefix", self.inp_job_prefix.text().strip() or "JOB")
        self.db.set_setting("job_number_next", str(self.spn_job_next.value()))
        self.db.set_setting("service_number_prefix", self.inp_srv_prefix.text().strip() or "SRV")
        self.db.set_setting("service_number_next", str(self.spn_srv_next.value()))
        self.db.set_setting("project_number_prefix", self.inp_prj_prefix.text().strip() or "PRJ")
        self.db.set_setting("project_number_next", str(self.spn_prj_next.value()))
        self.db.set_setting("reference_number_prefix", self.inp_ref_prefix.text().strip() or "REF")
        self.db.set_setting("reference_number_next", str(self.spn_ref_next.value()))
        self.db.set_setting("payment_number_prefix", self.inp_pay_prefix.text().strip() or "PAY")
        self.db.set_setting("payment_number_next", str(self.spn_pay_next.value()))

        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification("İş / servis / referans numara ayarları güncellendi.", "success")
        else:
            message_helper.show_info(self, "Kaydedildi", "İş / servis / referans numara ayarları kaydedildi.")

    def _number_settings_rows(self):
        return [
            ("\u0130\u015f", self.inp_job_prefix.text().strip(), self.spn_job_next.value()),
            ("Servis", self.inp_srv_prefix.text().strip(), self.spn_srv_next.value()),
            ("Proje", self.inp_prj_prefix.text().strip(), self.spn_prj_next.value()),
            ("Referans", self.inp_ref_prefix.text().strip(), self.spn_ref_next.value()),
            ("\u00d6deme", self.inp_pay_prefix.text().strip(), self.spn_pay_next.value()),
        ]

    @staticmethod
    def _number_settings_tsv(rows):
        return "\n".join(["T\u00fcr\t\u00d6n Ek\tSonraki Numara"] + ["\t".join(map(str, row)) for row in rows])

    def copy_number_settings(self):
        QApplication.clipboard().setText(self._number_settings_tsv(self._number_settings_rows()))
        show_success(self, "Numara ayarlar\u0131 panoya kopyaland\u0131.")

    def export_number_settings_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Numara Ayarlar\u0131 CSV \u00c7\u0131kt\u0131s\u0131",
            "numara_ayarlari.csv",
            "CSV Dosyas\u0131 (*.csv)",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(["Tur", "On Ek", "Sonraki Numara"])
                writer.writerows(self._number_settings_rows())
            show_success(self, "CSV \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except OSError as exc:
            show_error(self, f"CSV kaydedilemedi: {exc}")

    def export_number_settings_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Numara Ayarlar\u0131 Excel \u00c7\u0131kt\u0131s\u0131",
            "numara_ayarlari.xlsx",
            "Excel Dosyas\u0131 (*.xlsx)",
        )
        if not path:
            return
        try:
            import pandas as pd

            pd.DataFrame(
                self._number_settings_rows(),
                columns=["Tur", "On Ek", "Sonraki Numara"],
            ).to_excel(path, index=False)
            show_success(self, "Excel \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except Exception as exc:
            show_error(self, f"Excel \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def _number_settings_document(self):
        headers = ("T\u00fcr", "\u00d6n Ek", "Sonraki Numara")
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>"
            for row in self._number_settings_rows()
        )
        document = QTextDocument(self)
        document.setHtml(
            "<h2>Numara Ayarlari</h2>"
            "<table border='1' cellspacing='0' cellpadding='6'>"
            "<thead><tr>"
            + "".join(f"<th>{header}</th>" for header in headers)
            + "</tr></thead><tbody>"
            + body
            + "</tbody></table>"
        )
        return document

    def export_number_settings_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Numara Ayarlar\u0131 PDF \u00c7\u0131kt\u0131s\u0131",
            "numara_ayarlari.pdf",
            "PDF Dosyas\u0131 (*.pdf)",
        )
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self._number_settings_document().print(printer)
            show_success(self, "PDF \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except Exception as exc:
            show_error(self, f"PDF \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def print_number_settings(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self._number_settings_document().print(printer)

    def _legacy_bank_rows(self):
        if not hasattr(self, "table"):
            return []
        rows = []
        for row in range(self.table.rowCount()):
            rows.append(tuple(
                self.table.item(row, column).text() if self.table.item(row, column) else ""
                for column in range(7)
            ))
        return rows

    @staticmethod
    def _legacy_bank_headers():
        return ("Banka", "Sube", "Hesap Adi", "Hesap No", "IBAN", "Bakiye", "Aktif")

    def copy_legacy_bank_accounts(self):
        rows = self._legacy_bank_rows()
        if not rows:
            show_error(self, "Kopyalanacak banka hesab\u0131 bulunamad\u0131.")
            return
        QApplication.clipboard().setText(
            "\n".join(["\t".join(self._legacy_bank_headers())] + ["\t".join(row) for row in rows])
        )
        show_success(self, "Banka hesaplar\u0131 panoya kopyaland\u0131.")

    def export_legacy_bank_accounts_csv(self):
        rows = self._legacy_bank_rows()
        if not rows:
            show_error(self, "CSV \u00e7\u0131kt\u0131s\u0131 i\u00e7in banka hesab\u0131 bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Banka Hesaplar\u0131 CSV", "banka_hesaplari.csv", "CSV Dosyas\u0131 (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as stream:
                writer = csv.writer(stream)
                writer.writerow(self._legacy_bank_headers())
                writer.writerows(rows)
            show_success(self, "CSV \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except OSError as exc:
            show_error(self, f"CSV kaydedilemedi: {exc}")

    def export_legacy_bank_accounts_excel(self):
        rows = self._legacy_bank_rows()
        if not rows:
            show_error(self, "Excel \u00e7\u0131kt\u0131s\u0131 i\u00e7in banka hesab\u0131 bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Banka Hesaplar\u0131 Excel", "banka_hesaplari.xlsx", "Excel Dosyas\u0131 (*.xlsx)")
        if not path:
            return
        try:
            import pandas as pd

            pd.DataFrame(rows, columns=self._legacy_bank_headers()).to_excel(path, index=False)
            show_success(self, "Excel \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except Exception as exc:
            show_error(self, f"Excel \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def _legacy_bank_document(self):
        headers = self._legacy_bank_headers()
        body = "".join(
            "<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>"
            for row in self._legacy_bank_rows()
        )
        document = QTextDocument(self)
        document.setHtml(
            "<h2>Banka Hesaplari</h2><table border='1' cellspacing='0' cellpadding='6'><thead><tr>"
            + "".join(f"<th>{header}</th>" for header in headers)
            + "</tr></thead><tbody>" + body + "</tbody></table>"
        )
        return document

    def export_legacy_bank_accounts_pdf(self):
        if not self._legacy_bank_rows():
            show_error(self, "PDF \u00e7\u0131kt\u0131s\u0131 i\u00e7in banka hesab\u0131 bulunamad\u0131.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Banka Hesaplar\u0131 PDF", "banka_hesaplari.pdf", "PDF Dosyas\u0131 (*.pdf)")
        if not path:
            return
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            self._legacy_bank_document().print(printer)
            show_success(self, "PDF \u00e7\u0131kt\u0131s\u0131 kaydedildi.")
        except Exception as exc:
            show_error(self, f"PDF \u00e7\u0131kt\u0131s\u0131 kaydedilemedi: {exc}")

    def print_legacy_bank_accounts(self):
        if not self._legacy_bank_rows():
            show_error(self, "Yazd\u0131r\u0131lacak banka hesab\u0131 bulunamad\u0131.")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            self._legacy_bank_document().print(printer)

    @staticmethod
    def _bank_field(acc, key, index, default=None):
        try:
            if hasattr(acc, "keys") and key in acc.keys():
                return acc[key]
        except Exception:
            pass
        try:
            return acc[index]
        except Exception:
            return default

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QLabel("🏛️ Banka Hesap Numaralarınız")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(header)

        # Form Area
        form_frame = QFrame()
        form_frame.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 5px;
            }
        """))
        form_layout = QGridLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)

        # Input Helper
        def add_input(row, col, label_text, icon_text="i", placeholder="", width=None, colspan=1):
            lbl = QLabel(label_text)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            lbl.setStyleSheet(theme_qss("color: @text; border: none;"))
            
            inp = QLineEdit()
            inp.setPlaceholderText(placeholder)
            inp.setStyleSheet(theme_qss("""
                QLineEdit {
                    border: 1px solid @border;
                    border-radius: 4px;
                    padding: 8px;
                    background-color: @surface;
                    color: @text;
                }
                QLineEdit:focus { border: 1px solid @warning; }
            """))
            if width:
                inp.setFixedWidth(width)
            
            # Icon (simulated with label for now or internal placeholder if requested, but label is fine)
            
            form_layout.addWidget(lbl, row*2, col, 1, colspan)
            form_layout.addWidget(inp, row*2+1, col, 1, colspan)
            return inp

        self.inp_bank = add_input(0, 0, "Banka Adı", "🏛️", "Banka Adı")
        self.inp_branch = add_input(0, 1, "Şube Adı", "i", "Şube Adı")
        
        self.inp_acc_name = add_input(1, 0, "Hesap Adı", "i", "Hesap Adı")
        self.inp_acc_no = add_input(1, 1, "Hesap No", "i", "Hesap No")
        self.inp_iban = add_input(1, 2, "Iban", "i", "TR...", colspan=1)

        lbl_balance = QLabel("Mevcut Bakiye")
        lbl_balance.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        lbl_balance.setStyleSheet(theme_qss("color: @text; border: none;"))

        self.inp_balance = QDoubleSpinBox()
        self.inp_balance.setRange(-999999999, 999999999)
        self.inp_balance.setDecimals(2)
        self.inp_balance.setGroupSeparatorShown(True)
        self.inp_balance.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        self.inp_balance.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.inp_balance.setStyleSheet(theme_qss("""
            QDoubleSpinBox {
                border: 1px solid @border;
                border-radius: 4px;
                padding: 8px;
                background-color: @surface;
                color: @text;
            }
            QDoubleSpinBox:focus { border: 1px solid @warning; }
        """))

        form_layout.addWidget(lbl_balance, 4, 0)
        form_layout.addWidget(self.inp_balance, 5, 0)

        layout.addWidget(form_frame)

        # Add Button (Right Aligned)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_add = QPushButton("+ EKLE")
        self.btn_add.setFixedSize(100, 40)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        self.btn_add.clicked.connect(self.add_or_update_account)
        btn_layout.addWidget(self.btn_add)

        self.btn_cancel_edit = QPushButton("İPTAL")
        self.btn_cancel_edit.setFixedSize(100, 40)
        self.btn_cancel_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_cancel_edit.clicked.connect(self.cancel_edit)
        self.btn_cancel_edit.setVisible(False)
        btn_layout.addWidget(self.btn_cancel_edit)
        
        layout.addLayout(btn_layout)
        
        # Tools Layout (Copy, Excel, etc.)
        tools_layout = QHBoxLayout()
        tools_buttons = [
            ("📋 KOPYALA", "warning"), 
            ("📄 CSV ÇIKTI", "secondary"), 
            ("📊 EXCEL ÇIKTI", "secondary"), 
            ("📑 PDF KAYDET", "secondary"), 
            ("🖨️ YAZDIR", "ghost")
        ]
        
        legacy_callbacks = [
            self.copy_legacy_bank_accounts,
            self.export_legacy_bank_accounts_csv,
            self.export_legacy_bank_accounts_excel,
            self.export_legacy_bank_accounts_pdf,
            self.print_legacy_bank_accounts,
        ]
        for (text, variant), callback in zip(tools_buttons, legacy_callbacks):
            b = QPushButton(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant, size="sm")))
            b.clicked.connect(callback)
            tools_layout.addWidget(b)
            
        tools_layout.addStretch()
        
        # Search Box
        lbl_search = QLabel("Arama:")
        lbl_search.setStyleSheet(theme_qss("color: @text; border: none;"))
        self.inp_search = QLineEdit()
        self.inp_search.setFixedWidth(150)
        self.inp_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        
        tools_layout.addWidget(lbl_search)
        tools_layout.addWidget(self.inp_search)
        
        layout.addLayout(tools_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["BANKA", "ŞUBE ADI", "HESAP ADI", "HESAP NO", "IBAN", "MEVCUT BAKİYE", "AKTİF", "DÜZENLE", "SİL"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.table)
        
        # Empty State Label
        self.lbl_empty = QLabel("Henüz kayıtlı banka hesabı bulunmuyor.\n'+ EKLE' butonuna tıklayarak yeni hesap ekleyebilirsiniz.")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px; padding: 40px; border: 2px dashed @border; border-radius: 10px; margin: 20px;"))
        self.lbl_empty.setVisible(False)
        layout.addWidget(self.lbl_empty)
        
        # Footer Pagination Stub
        self.lbl_footer = QLabel("0 kayıttan 0 - 0 kayıt gösteriliyor.")
        self.lbl_footer.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border:none;"))
        layout.addWidget(self.lbl_footer)

    def load_data(self):
        accounts = self.db.get_bank_accounts()
        self.table.setRowCount(0)
        
        if not accounts:
            self.table.setVisible(False)
            self.lbl_empty.setVisible(True)
            self.lbl_footer.setText("Kayıt bulunamadı.")
            return
            
        self.table.setVisible(True)
        self.lbl_empty.setVisible(False)
        self.lbl_footer.setText(f"Toplam {len(accounts)} hesap listeleniyor.")
        
        for i, acc in enumerate(accounts):
            # acc: id, bank, branch, name, no, iban, is_active, created
            self.table.insertRow(i)
            
            self.table.setItem(i, 0, QTableWidgetItem(str(self._bank_field(acc, "bank_name", 1, "") or "")))
            self.table.setItem(i, 1, QTableWidgetItem(str(self._bank_field(acc, "branch_code", 5, "") or "")))
            self.table.setItem(i, 2, QTableWidgetItem(str(self._bank_field(acc, "account_holder", 2, "") or "")))
            self.table.setItem(i, 3, QTableWidgetItem(str(self._bank_field(acc, "account_number", 4, "") or "")))
            self.table.setItem(i, 4, QTableWidgetItem(str(self._bank_field(acc, "iban", 3, "") or "")))
            try:
                balance_val = float(self._bank_field(acc, "current_balance", 9, 0) or 0)
            except Exception:
                balance_val = 0.0
            item_balance = QTableWidgetItem(
                CurrencyHelper.format_try_for_display(balance_val, db=self.db, include_try_reference=False)
            )
            item_balance.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight)
            self.table.setItem(i, 5, item_balance)
            
            is_active = False
            try:
                is_active = int(self._bank_field(acc, "is_active", 7, 1) or 0) == 1
            except Exception:
                is_active = True

            tgl = AnimatedToggle(active_color=tc("success"))
            tgl.setChecked(is_active)
            tgl.setCursor(Qt.CursorShape.PointingHandCursor)
            tgl.toggled.connect(lambda checked, aid=self._bank_field(acc, "id", 0): self.set_active(aid, checked))
            w_t = QWidget()
            lt = QHBoxLayout(w_t)
            lt.setContentsMargins(0, 0, 0, 0)
            lt.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lt.addWidget(tgl)
            self.table.setCellWidget(i, 6, w_t)

            btn_edit = QPushButton("✏️")
            btn_edit.setFixedSize(36, 36)
            btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("warning", size="sm")))
            btn_edit.clicked.connect(lambda _, a=acc: self.start_edit(a))
            w_e = QWidget()
            le = QHBoxLayout(w_e)
            le.setContentsMargins(0, 0, 0, 0)
            le.setAlignment(Qt.AlignmentFlag.AlignCenter)
            le.addWidget(btn_edit)
            self.table.setCellWidget(i, 7, w_e)

            btn_del = QPushButton("🗑️")
            btn_del.setFixedSize(36, 36)
            btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_del.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
            btn_del.clicked.connect(lambda _, aid=self._bank_field(acc, "id", 0): self.delete_account(aid))
            
            widget = QWidget()
            l = QHBoxLayout(widget)
            l.setContentsMargins(0,0,0,0)
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.addWidget(btn_del)
            self.table.setCellWidget(i, 8, widget)

        self.lbl_footer.setText(f"{len(accounts)} kayıttan 1 - {len(accounts)} kayıt gösteriliyor.")

    def add_or_update_account(self):
        bank = self.inp_bank.text().strip()
        if not bank:
            if self.main_window: self.main_window.show_notification("Banka adı zorunludur.", "warning")
            return

        bank_name = self.inp_bank.text()
        branch_name = self.inp_branch.text()
        account_name = self.inp_acc_name.text()
        account_no = self.inp_acc_no.text()
        iban = self.inp_iban.text()
        balance = float(self.inp_balance.value())

        if self.editing_account_id is None:
            ok = self.db.add_bank_account(bank_name, branch_name, account_name, account_no, iban, balance)
            if ok and self.main_window:
                self.main_window.show_notification("Hesap eklendi.", "success")
        else:
            ok = self.db.update_bank_account(self.editing_account_id, bank_name, branch_name, account_name, account_no, iban, balance)
            if ok and self.main_window:
                self.main_window.show_notification("Hesap güncellendi.", "success")

        if ok:
            self.cancel_edit()
            self.load_data()
        else:
            if self.main_window:
                self.main_window.show_notification("Kayıt işlemi sırasında hata oluştu.", "error")

    def start_edit(self, acc):
        try:
            self.editing_account_id = self._bank_field(acc, "id", 0)
            self.inp_bank.setText(str(self._bank_field(acc, "bank_name", 1, "") or ""))
            self.inp_branch.setText(str(self._bank_field(acc, "branch_code", 5, "") or ""))
            self.inp_acc_name.setText(str(self._bank_field(acc, "account_holder", 2, "") or ""))
            self.inp_acc_no.setText(str(self._bank_field(acc, "account_number", 4, "") or ""))
            self.inp_iban.setText(str(self._bank_field(acc, "iban", 3, "") or ""))
            try:
                self.inp_balance.setValue(float(self._bank_field(acc, "current_balance", 9, 0) or 0))
            except Exception:
                self.inp_balance.setValue(0)
            self.btn_add.setText("GÜNCELLE")
            self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("warning")))
            self.btn_cancel_edit.setVisible(True)
        except Exception:
            return

    def cancel_edit(self):
        self.editing_account_id = None
        self.inp_bank.clear()
        self.inp_branch.clear()
        self.inp_acc_name.clear()
        self.inp_acc_no.clear()
        self.inp_iban.clear()
        self.inp_balance.setValue(0)
        self.btn_add.setText("+ EKLE")
        self.btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        self.btn_cancel_edit.setVisible(False)

    def set_active(self, account_id, checked):
        self.db.set_bank_account_active(account_id, checked)

    def delete_account(self, aid):
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        from PyQt6.QtWidgets import QDialog
        
        dialog = SimpleConfirmDialog(
            self,
            "Onay",
            "Silmek istediğinize emin misiniz",
            "Evet",
            "Hayır"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.delete_bank_account(aid)
            if self.editing_account_id == aid:
                self.cancel_edit()
            self.load_data()
            if self.main_window:
                self.main_window.show_notification("Hesap başarıyla silindi.", "success")

