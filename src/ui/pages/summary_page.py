# -*- coding: utf-8 -*-


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QGraphicsDropShadowEffect, QGridLayout, QSizePolicy,
                             QScrollArea, QProgressBar, QListWidget, QListWidgetItem, 
                             QPushButton, QDialog, QFileDialog)
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
import csv
import pandas as pd
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss, tc
from src.utils.page_ids import PageIds
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from PyQt6.QtGui import QFont, QColor, QIcon
from src.utils.design_system import DesignTokens

class MiniStat(QFrame):
    def __init__(self, title, value, unit="", icon="📊", color=tc("accent")):
        super().__init__()
        self.setObjectName("Card")
        self.setMinimumHeight(90)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)
        
        # Icon Section
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(theme_qss(f"font-size: 24px; color: {color}; padding: 10px; background: {color}15; border-radius: 10px;"))
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setFixedSize(50, 50)
        
        # Text Section
        text_vbox = QVBoxLayout()
        text_vbox.setSpacing(2)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setObjectName("CardTitle")
        
        lbl_val = QLabel(f"{value}{unit}")
        lbl_val.setObjectName("CardValue")
        
        text_vbox.addWidget(lbl_title)
        text_vbox.addWidget(lbl_val)
        text_vbox.addStretch()
        
        layout.addWidget(lbl_icon)
        layout.addLayout(text_vbox)
        layout.addStretch()

class SummaryPage(QWidget):
    """
    Yönetici Özeti Ekranı (20+ Veri Widget'ı)
    Tüm işletme verilerini tek bir modern panelde toplar.
    """
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QHBoxLayout()
        title_vbox = QVBoxLayout()
        lbl_title = QLabel("Yönetici Özeti & Analitik")
        lbl_title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        lbl_subtitle = QLabel("İşletmenizin tüm departmanlarını tek ekrandan kontrol edin.")
        lbl_subtitle.setStyleSheet(theme_qss("color: @text_muted;"))
        title_vbox.addWidget(lbl_title)
        title_vbox.addWidget(lbl_subtitle)
        header.addLayout(title_vbox)
        
        btn_refresh = QPushButton("🔄 VERİLERİ TAZELA")
        btn_refresh.setFixedSize(200, 48)
        btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_refresh.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_refresh.clicked.connect(self.refresh_all)
        header.addStretch()
        btn_excel = QPushButton("📊 Excel")
        btn_excel.setFixedSize(160, 48)
        btn_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_excel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_excel.clicked.connect(self.export_to_excel)
        header.addWidget(btn_excel)

        btn_pdf = QPushButton("📄 PDF")
        btn_pdf.setFixedSize(120, 48)
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_pdf.clicked.connect(self.export_to_pdf)
        header.addWidget(btn_pdf)

        btn_print = QPushButton("🖨️ Yazdır")
        btn_print.setFixedSize(140, 48)
        btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_print.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_print.clicked.connect(self.print_report)
        header.addWidget(btn_print)
        header.addWidget(btn_refresh)
        main_layout.addLayout(header)

        # Scroll Area for high density
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(20)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        
        self.refresh_all()

    def refresh_all(self):
        # Clear existing
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        data = self.db.get_summary_data()
        tech_perf = self.db.get_technician_performance()
        popular_parts = self.db.get_popular_parts()
        stats = self.db.get_stats()
        
        # --- ROW 1: Finansal Özet (5 Özellik) ---
        self.grid.addWidget(MiniStat("GÜNLÜK CİRO", CurrencyHelper.format_try_for_display(data['daily_turnover'], db=self.db, include_try_reference=False), "", "💰", tc("success")), 0, 0)
        self.grid.addWidget(MiniStat("BEKLEYEN TAHSİLAT", CurrencyHelper.format_try_for_display(data['total_receivables'], db=self.db, include_try_reference=False), "", "🧾", tc("warning")), 0, 1)
        self.grid.addWidget(MiniStat("AKTİF MÜŞTERİLER", data['unique_customers'], "", "👥", tc("accent")), 0, 2)
        self.grid.addWidget(MiniStat("BUGÜNKÜ KAYITLAR", data['new_jobs_today'], "", "📥", tc("warning")), 0, 3)

        # --- ROW 2: Operasyon & Teknik (5 Özellik) ---
        op_card = QFrame()
        op_card.setObjectName("Card")
        op_layout = QVBoxLayout(op_card)
        op_title = QLabel("🛠️ TEKNİSYEN PERFORMANSI (TOP 5)")
        op_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        op_layout.addWidget(op_title)
        
        for name, count in tech_perf[:5]:
            row = QHBoxLayout()
            row.addWidget(QLabel(name))
            pb = QProgressBar()
            pb.setMaximum(50) # Örn hedef 50
            pb.setValue(min(count, 50))
            pb.setFixedHeight(8)
            pb.setTextVisible(False)
            row.addWidget(pb)
            row.addWidget(QLabel(str(count)))
            op_layout.addLayout(row)
        
        if not tech_perf: op_layout.addWidget(QLabel("Kayıt bulunamadı."))
        self.grid.addWidget(op_card, 1, 0, 1, 2)

        # Marka Dağılımı
        brand_card = QFrame()
        brand_card.setObjectName("Card")
        br_layout = QVBoxLayout(brand_card)
        br_title = QLabel("📱 EN ÇOK GELEN MARKALAR")
        br_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        br_layout.addWidget(br_title)
        for brand, count in data['brand_dist']:
            br_layout.addWidget(QLabel(f"• {brand}: {count} cihaz"))
        self.grid.addWidget(brand_card, 1, 2, 1, 2)

        # --- ROW 3: Stok & Envanter (5 Özellik) ---
        self.grid.addWidget(MiniStat("KRİTİK STOK", data['critical_stock_count'], " PARÇA", "⚠️", tc("danger")), 2, 0)
        self.grid.addWidget(MiniStat("DEPO TOPLAM DEĞERİ", CurrencyHelper.format_try_for_display(data['inventory_value'], db=self.db, include_try_reference=False), "", "📦", tc("accent_hover")), 2, 1)
        
        part_card = QFrame()
        part_card.setObjectName("Card")
        pk_layout = QVBoxLayout(part_card)
        pk_title = QLabel("🔄 EN ÇOK KULLANILAN PARÇALAR")
        pk_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        pk_layout.addWidget(pk_title)
        for name, count in popular_parts:
            pk_layout.addWidget(QLabel(f"{name}: {count} kullanım"))
        self.grid.addWidget(part_card, 2, 2, 1, 2)

        # --- ROW 4: Analitik Kartlar (5+ Özellik) ---
        flow_card = QFrame()
        flow_card.setObjectName("Card")
        fl_layout = QVBoxLayout(flow_card)
        fl_title = QLabel("📈 İŞ AKIŞI ANALİZİ")
        fl_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        fl_layout.addWidget(fl_title)
        for s_name, s_count in stats.items():
            fl_layout.addWidget(QLabel(f"{s_name}: {s_count}"))
        self.grid.addWidget(flow_card, 3, 0, 1, 1)
        
        # Tools Widget
        tool_card = QFrame()
        tool_card.setObjectName("Card")
        tl_layout = QVBoxLayout(tool_card)
        tl_layout.addWidget(QLabel("🧰 YÖNETİCİ ARAÇLARI"))
        
        btn_excel = QPushButton("📊 Excel Raporu Al")
        btn_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_excel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
        btn_excel.clicked.connect(self.export_to_excel)
        tl_layout.addWidget(btn_excel)
        
        btn_close_kasa = QPushButton("🔒 Kasayı Kapat")
        btn_close_kasa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_kasa.setStyleSheet(theme_qss(DesignTokens.get_button_qss("destructive", size="sm")))
        btn_close_kasa.clicked.connect(self.close_register)
        tl_layout.addWidget(btn_close_kasa)
        
        btn_pay_staff = QPushButton("💸 Personel Maaş Öde")
        btn_pay_staff.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pay_staff.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        btn_pay_staff.clicked.connect(self.open_personnel)
        tl_layout.addWidget(btn_pay_staff)
        
        self.grid.addWidget(tool_card, 3, 1, 1, 1)

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Rapor Kaydet", "yonetici_ozeti.xlsx", "Excel Dosyasi (*.xlsx)")
            if not path:
                return

            data = self.db.get_summary_data()
            df = pd.DataFrame([
                ["Gunluk Ciro", CurrencyHelper.format_try_for_display(data["daily_turnover"], db=self.db, include_try_reference=False)],
                ["Alacaklar", CurrencyHelper.format_try_for_display(data["total_receivables"], db=self.db, include_try_reference=False)],
                ["Aktif Musteri", data["unique_customers"]],
                ["Bugunku Is", data["new_jobs_today"]],
                ["Kritik Stok", data["critical_stock_count"]],
                ["Envanter Degeri", CurrencyHelper.format_try_for_display(data["inventory_value"], db=self.db, include_try_reference=False)],
            ], columns=["Metrik", "Deger"])
            df.to_excel(path, index=False)
            show_info(self, "Rapor kaydedildi.")
        except Exception as e:
            show_error(self, f"Disa aktarma hatasi: {e}")

    def _build_report_html(self):
        data = self.db.get_summary_data()
        tech_perf = self.db.get_technician_performance()
        popular_parts = self.db.get_popular_parts()
        stats = self.db.get_stats()
        sections = [
            ("Finansal Ozet", [
                ("Gunluk Ciro", CurrencyHelper.format_try_for_display(data['daily_turnover'], db=self.db, include_try_reference=False)),
                ("Bekleyen Tahsilat", CurrencyHelper.format_try_for_display(data['total_receivables'], db=self.db, include_try_reference=False)),
                ("Aktif Musteriler", str(data['unique_customers'])),
                ("Bugunku Kayitlar", str(data['new_jobs_today'])),
                ("Kritik Stok", str(data['critical_stock_count'])),
                ("Envanter Degeri", CurrencyHelper.format_try_for_display(data['inventory_value'], db=self.db, include_try_reference=False)),
            ]),
            ("Teknisyen Performansi", [(name, str(count)) for name, count in tech_perf[:10]] or [("Veri", "Bulunamadi")]),
            ("Populer Parcalar", [(name, str(count)) for name, count in popular_parts[:10]] or [("Veri", "Bulunamadi")]),
            ("Is Akisi Analizi", [(str(k), str(v)) for k, v in stats.items()] or [("Veri", "Bulunamadi")]),
        ]
        html = [
            "<html><head><meta charset='UTF-8'></head><body>",
            f"<h1>AYEC Pro - Yonetici Ozeti</h1><p>Tarih: {__import__('datetime').datetime.now().strftime('%d.%m.%Y %H:%M')}</p>",
        ]
        for title, rows in sections:
            html.append(f"<h2>{title}</h2>")
            html.append("<table cellspacing='0' cellpadding='0' style='width:100%;border-collapse:collapse;font-size:10pt;margin-bottom:18px;'>")
            for key, value in rows:
                html.append(
                    "<tr>"
                    f"<td style='padding:8px;border:1px solid #d9d9d9;background:#f8fafc;font-weight:bold;width:40%;'>{key}</td>"
                    f"<td style='padding:8px;border:1px solid #d9d9d9;'>{value}</td>"
                    "</tr>"
                )
            html.append("</table>")
        html.append("</body></html>")
        return "".join(html)

    def export_to_pdf(self):
        try:
            path, _ = QFileDialog.getSaveFileName(self, "Yonetici Ozeti PDF", "yonetici_ozeti.pdf", "PDF Dosyasi (*.pdf)")
            if not path:
                return
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            doc = QTextDocument()
            doc.setHtml(self._build_report_html())
            doc.print(printer)
            show_success(self, "Yonetici ozeti PDF olarak kaydedildi.")
        except Exception as e:
            show_error(self, f"PDF hatasi: {e}")

    def print_report(self):
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            dialog = QPrintDialog(printer, self)
            if dialog.exec() != QPrintDialog.DialogCode.Accepted:
                return
            doc = QTextDocument()
            doc.setHtml(self._build_report_html())
            doc.print(printer)
            show_info(self, "Yonetici ozeti yazdirmaya gonderildi.")
        except Exception as e:
            show_error(self, f"Yazdirma hatasi: {e}")

    def close_register(self):
        from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
        
        dialog = SimpleConfirmDialog(
            self,
            "Kasa Kapanışı",
            "Gün sonu kapanışını yapmak istiyor musunuz\nBu işlem 'Kasa Kapandı' logu oluşturur.",
            "Evet",
            "Hayır"
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.db.add_audit_log("Yönetici", "accounting", "CLOSE_REGISTER", "Gün sonu kapanışı yapıldı.")
            show_info(self.window(), "Kasa başarıyla kapatıldı ve kayıt altına alındı.")

    def open_personnel(self):
        if hasattr(self.main_window, 'switch_page'):
            self.main_window.switch_page(PageIds.PERSONNEL)
        else:
            self.main_window.stack.setCurrentIndex(3)
