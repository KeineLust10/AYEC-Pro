# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
                             QLabel, QFrame, QProgressBar, QFileDialog)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from src.utils.theme_colors import theme_qss, tc
from src.utils.language_manager import LanguageManager
from src.utils.toast_notification import show_success, show_error
from src.utils.logger import logger
import os

from src.ui.pages.project_management.project_detail_components import (
    FinanceTab, UnitsTab, SubcontractorsTab, TransactionDialog, AddUnitDialog, AddSubDialog
)


class ProjectDetailPage(QWidget):
    def __init__(self, db, main_window, project_id, project_name):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.project_id = project_id
        self.project_name = project_name
        self.lang = LanguageManager()
        self.contract_path = self._get_contract_path()
        self.init_ui()
        self.lang.labels_updated.connect(self.update_texts)

    # ── UI ────────────────────────────────────────────────────────────────────

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Başlık
        header = QHBoxLayout()
        self.lbl_title = QLabel(f"📋 {self.project_name}")
        self.lbl_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(theme_qss("color: @text;"))
        header.addWidget(self.lbl_title)
        header.addStretch()

        # PDF Raporu butonu
        self.btn_pdf = QPushButton("📄 PDF Raporu")
        self.btn_pdf.setFixedHeight(36)
        self.btn_pdf.setStyleSheet(theme_qss(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #1e3a5f,stop:1 #2563eb); color: white; "
            "border-radius: 8px; font-weight: bold; font-size: 12px; padding: 0 16px; } "
            "QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #172d4a,stop:1 #1d4cc7); }"
        ))
        self.btn_pdf.clicked.connect(self.export_pdf_report)
        header.addWidget(self.btn_pdf)

        # Sözleşme butonu (Eğer varsa)
        self.btn_contract = QPushButton("📜 Sözleşmeyi Aç")
        self.btn_contract.setFixedHeight(36)
        self.btn_contract.setStyleSheet(theme_qss(
            "QPushButton { background: @surface_alt; color: @text; "
            "border: 1px solid @border; border-radius: 8px; font-weight: bold; font-size: 12px; padding: 0 16px; } "
            "QPushButton:hover { background: @border; }"
        ))
        self.btn_contract.clicked.connect(self.open_contract)
        self.btn_contract.setVisible(bool(self.contract_path))
        header.addWidget(self.btn_contract)

        layout.addLayout(header)

        # ── Özet Şeridi ───────────────────────────────────────────────────────
        self.summary_frame = QFrame()
        self.summary_frame.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border-radius: 10px; border: 1px solid @border; }"
        ))
        summary_h = QHBoxLayout(self.summary_frame)
        summary_h.setContentsMargins(16, 10, 16, 10)
        summary_h.setSpacing(0)

        def _stat_chip(icon, label, color_key="text"):
            w = QFrame()
            w.setStyleSheet("border: none; background: transparent;")
            h = QHBoxLayout(w)
            h.setContentsMargins(12, 0, 12, 0)
            h.setSpacing(6)
            lbl = QLabel(f"{icon}  —")
            lbl.setStyleSheet(theme_qss(f"color: @{color_key}; font-weight: bold; font-size: 13px; border: none;"))
            sub = QLabel(label)
            sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; border: none;"))
            h.addWidget(lbl)
            h.addWidget(sub)
            return w, lbl

        self._chip_total,      self._lbl_total      = _stat_chip("🏠 0", "Oda")
        self._chip_completed,  self._lbl_completed  = _stat_chip("✅ 0", "Tamamlandı", "success")
        self._chip_inprogress, self._lbl_inprogress = _stat_chip("🔄 0", "Devam Ediyor", "warning")
        self._chip_products,   self._lbl_products   = _stat_chip("📦 0", "Ürün Kurulu", "accent")
        self._chip_team,       self._lbl_team       = _stat_chip("👥 0", "Ekip Üyesi")

        def _divider():
            d = QFrame()
            d.setFrameShape(QFrame.Shape.VLine)
            d.setStyleSheet(theme_qss("color: @border; background: @border;"))
            d.setFixedWidth(1)
            return d

        for chip in [self._chip_total, self._chip_completed,
                     self._chip_inprogress, self._chip_products, self._chip_team]:
            summary_h.addWidget(chip)
            if chip is not self._chip_team:
                summary_h.addWidget(_divider())

        summary_h.addStretch()

        # Yüzde etiketi
        self._lbl_pct = QLabel("0%")
        self._lbl_pct.setStyleSheet(theme_qss(
            "color: @accent; font-size: 20px; font-weight: bold; border: none;"
        ))
        self._lbl_pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        summary_h.addWidget(self._lbl_pct)

        layout.addWidget(self.summary_frame)

        # ── Sekmeler ──────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(theme_qss(
            "QTabBar::tab { padding: 8px 18px; font-size: 13px; } "
            "QTabBar::tab:selected { font-weight: bold; }"
        ))
        layout.addWidget(self.tabs)

        # Finans
        self.tab_finance = FinanceTab(self.db, self.project_id)
        self.tabs.addTab(self.tab_finance, "💰  Finans Durumu")

        # Kurulum (Daire/Oda)
        self.tab_units = UnitsTab(self.db, self.project_id, project_page=self)
        self.tabs.addTab(self.tab_units, "🏠  Kurulum")

        # Ekip
        self.tab_subs = SubcontractorsTab(self.db, self.project_id)
        self.tabs.addTab(self.tab_subs, "👥  Ekip")

        # Tab değişince özeti güncelle
        self.tabs.currentChanged.connect(self.refresh_summary)

        # İlk yükleme
        QTimer.singleShot(100, self.refresh_summary)

    # ── Özet Güncelleme ───────────────────────────────────────────────────────

    def refresh_summary(self):
        try:
            s = self.db.get_project_install_summary(self.project_id)
            self._lbl_total.setText(f"🏠 {s['total']}  —")
            self._lbl_completed.setText(f"✅ {s['completed']}  —")
            self._lbl_inprogress.setText(f"🔄 {s['in_progress']}  —")
            self._lbl_products.setText(f"📦 {s['total_products']}  —")
            self._lbl_team.setText(f"👥 {s['team_count']}  —")
            self._lbl_pct.setText(f"{s['pct']}%")
        except Exception:
            pass

    # ── PDF Raporu ────────────────────────────────────────────────────────────

    def export_pdf_report(self):
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c for c in self.project_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
        default_name = f"proje_raporu_{safe_name}_{ts}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Proje Raporunu Kaydet",
            default_name,
            "PDF Dosyası (*.pdf);;HTML Raporu (*.html)"
        )
        if not path:
            return

        from src.ui.utils.background_task import run_cancellable_task

        def produce_report(is_cancelled):
            if is_cancelled():
                return False, "cancelled"
            from src.utils.project_pdf_report import generate_project_report

            return generate_project_report(self.db, self.project_id, path)

        def report_ready(result):
            ok, message = result
            if not ok:
                show_error(self, message)
                return
            show_success(self, message)
            open_path = path
            if not os.path.exists(open_path) and path.lower().endswith(".pdf"):
                open_path = path[:-4] + ".html"
            try:
                os.startfile(open_path)
            except Exception:
                pass

        self.btn_pdf.setEnabled(False)
        run_cancellable_task(
            owner=self,
            title="Proje raporu olu\u015fturuluyor...",
            target=produce_report,
            on_success=report_ready,
            on_error=lambda message: show_error(
                self,
                f"Rapor olu\u015fturulamad\u0131: {message}",
            ),
            on_done=lambda: self.btn_pdf.setEnabled(True),
            output_path=path,
        )

    def _get_contract_path(self):
        try:
            details = self.db.get_project_details(self.project_id)
            if details:
                # 'contract_path' kolonu projects tablosunda (ProjectMixin migration ile eklendi)
                keys = details.keys() if hasattr(details, 'keys') else []
                # SQLitedict veya tuple durumuna göre
                if isinstance(details, dict):
                    return details.get('contract_path')
                elif len(details) > 13: # projects tablosunda 13. kolondan sonra eklendi
                    # Projesi tablosundaki kolon sırasına göre bulalım. 
                    # create_project_tables'da sırayla bakarsak:
                    # id, name, start, end, budget, status, desc, created, cost, p_method, cust_id, cust_name, ref, archived, cur, ex_rate, contract_path
                    # Toplam 17 kolon. id=0, contract_path=16 olabilir.
                    # Ama daha güvenli olması için cursor.description kullanmalıyız eğer db manager bunu dönüyorsa.
                    # Çoğu sqlite sarmalayıcısı dict-like döner.
                    pass
            
            # Alternatif: Manuel sorgu
            self.db.cursor.execute("SELECT contract_path FROM projects WHERE id=?", (self.project_id,))
            row = self.db.cursor.fetchone()
            if row:
                return row['contract_path'] if isinstance(row, dict) else row[0]
        except Exception as e:
            logger.error(f"Error getting contract path: {e}")
        return None

    def open_contract(self):
        if not self.contract_path:
            show_error(self, "Bu projeye ait bir sözleşme bulunamadı.")
            return
            
        full_path = os.path.join(os.getcwd(), self.contract_path)
        if os.path.exists(full_path):
            try:
                os.startfile(full_path)
            except Exception as e:
                show_error(self, f"Sözleşme açılamadı: {e}")
        else:
            show_error(self, "Sözleşme dosyası sistemde bulunamadı.")

    # ── Metin Güncellemesi ────────────────────────────────────────────────────

    def update_texts(self):
        self.lbl_title.setText(f"📋 {self.project_name}")
        if hasattr(self.tab_finance,  'update_texts'): self.tab_finance.update_texts()
        if hasattr(self.tab_units,    'update_texts'): self.tab_units.update_texts()
        if hasattr(self.tab_subs,     'update_texts'): self.tab_subs.update_texts()
