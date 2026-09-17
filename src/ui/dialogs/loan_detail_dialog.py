# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                             QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QTabWidget, QGridLayout, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, QUrl, QSize
from PyQt6.QtGui import QIcon, QDesktopServices, QPixmap, QColor, QFont
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.modern_dialog import NoWheelScrollArea
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper

class LoanDetailDialog(BaseModernDialog):
    def __init__(self, db, loan_id, parent=None):
        super().__init__(parent, title="Kredi Detayları", width=1040, height=780)
        self.db = db
        self.loan_id = loan_id
        self.loan_data = None
        self.installments = []
        self.attachments = []
        self.fetch_data()
        self.setup_ui()

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_from_try(
            amount,
            db=self.db,
            currency_code=CurrencyHelper.get_code(self.db),
            include_try_reference=include_try_reference,
        )

    def fetch_data(self):
        self.db.cursor.execute("SELECT * FROM loans WHERE id=?", (self.loan_id,))
        row = self.db.cursor.fetchone()
        if row:
            self.loan_data = {
                'id': row['id'],
                'bank_name': row['bank_name'],
                'amount': row['amount'],
                'interest_rate': row['interest_rate'],
                'months': row['term_months'],
                'start_date': row['start_date'],
                'total_payment': row['total_payment'],
                'desc': row['description'],
                'status': row['status']
            }

        raw_installments = self.db.get_loan_installments(self.loan_id)
        self.installments = [dict(ix) for ix in raw_installments]
        
        try:
            self.db.cursor.execute("SELECT * FROM loan_attachments WHERE loan_id=?", (self.loan_id,))
            raw_attachments = self.db.cursor.fetchall()
            self.attachments = [dict(a) for a in raw_attachments]
        except Exception:
            self.attachments = []

    def setup_ui(self):
        if not self.loan_data:
            self.content_layout.addWidget(QLabel("Kredi bulunamadı."))
            return
            
        tabs = QTabWidget()
        tabs.setStyleSheet(theme_qss("""
             QTabWidget::pane { border: none; }
             QTabBar::tab {
                 background: transparent;
                 color: @text_muted;
                 padding: 10px 20px;
                 font-weight: 600;
                 border-bottom: 2px solid transparent;
             }
             QTabBar::tab:selected {
                 color: @accent_hover;
                 border-bottom: 2px solid @accent_hover;
             }
        """))
        
        tab_overview = QWidget()
        self.setup_overview_tab(tab_overview)
        tabs.addTab(tab_overview, "📊 Genel Bakış")
        
        tab_plan = QWidget()
        self.setup_plan_tab(tab_plan)
        tabs.addTab(tab_plan, "📅 Ödeme Planı")
        
        tab_docs = QWidget()
        self.setup_docs_tab(tab_docs)
        tabs.addTab(tab_docs, "📁 Evraklar ve Sözleşmeler")
        
        self.content_layout.addWidget(tabs)
        
        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(100, 40)
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_close.clicked.connect(self.accept)
        
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(btn_close)
        self.content_layout.addLayout(h_layout)

    def setup_overview_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(20, 20, 20, 20)
        
        card = QFrame()
        card.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        c_layout = QHBoxLayout(card)
        
        v_bank = QVBoxLayout()
        lbl_bank = QLabel(self.loan_data['bank_name'])
        lbl_bank.setStyleSheet(theme_qss("font-size: 18px; font-weight: bold; color: @text;"))
        lbl_desc = QLabel(self.loan_data['desc'])
        lbl_desc.setStyleSheet(theme_qss("color: @text_muted;"))
        v_bank.addWidget(lbl_bank)
        v_bank.addWidget(lbl_desc)
        c_layout.addLayout(v_bank)
        c_layout.addStretch()
        
        lbl_status = QLabel(self.loan_data['status'])
        color = tc("success") if self.loan_data['status'] == 'Aktif' else "@text_muted"
        lbl_status.setStyleSheet(theme_qss(f"background: {color}; color: @selection_text; padding: 5px 15px; border-radius: 15px; font-weight: bold;"))
        c_layout.addWidget(lbl_status)
        
        layout.addWidget(card)
        
        grid_frame = QFrame()
        g_layout = QGridLayout(grid_frame)
        g_layout.setVerticalSpacing(20)
        g_layout.setHorizontalSpacing(40)
        
        def add_item(row, col, label, value, color=tc("text")):
            l = QLabel(label)
            l.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: 600; text-transform: uppercase;"))
            v = QLabel(str(value))
            v.setStyleSheet(theme_qss(f"color: {color}; font-size: 16px; font-weight: 600;"))
            g_layout.addWidget(l, row*2, col)
            g_layout.addWidget(v, row*2+1, col)
            
        amount_val = self.loan_data.get('amount') or 0
        payment_val = self.loan_data.get('total_payment') or 0
        
        add_item(0, 0, "Kredi Tutarı", self._fmt_try(amount_val))
        add_item(0, 1, "Geri Ödeme", self._fmt_try(payment_val))
        
        paid = sum((inst.get('amount') or inst.get('total_amount') or 0) for inst in self.installments if inst.get('status') == 'Ödendi')
        remaining = payment_val - paid if self.loan_data.get('status') != 'Kapalı' else 0
        
        add_item(1, 0, "Ödenen Tutar", self._fmt_try(paid), "@success")
        add_item(1, 1, "Kalan Borç", self._fmt_try(remaining), "@danger")
        
        add_item(2, 0, "Faiz Oranı", f"%{self.loan_data.get('interest_rate', 0)}")
        add_item(2, 1, "Vade", f"{self.loan_data.get('months', 0)} Ay")
        
        add_item(3, 0, "Başlangıç", self.loan_data['start_date'])
        
        layout.addWidget(grid_frame)
        layout.addStretch()

    def setup_plan_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 20, 0, 0)
        
        if not self.installments:
            lbl_empty = QLabel("🚫 Ödeme planı bulunamadı.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px; font-weight: bold;"))
            layout.addWidget(lbl_empty)
            return

        from PyQt6.QtWidgets import QAbstractItemView
        table = QTableWidget()
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["No", "Tarih", "Tutar", "Durum"])
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 60)
        header.resizeSection(1, 150)
        header.resizeSection(2, 150)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        
        table.setRowCount(len(self.installments))
        for i, inst in enumerate(self.installments):
            inst_no = inst.get('installment_no', i+1)
            due_date = inst.get('due_date', '-')
            amount = inst.get('amount') or inst.get('total_amount') or 0
            status = inst.get('status', 'Bekliyor')

            table.setItem(i, 0, QTableWidgetItem(str(inst_no)))
            table.setItem(i, 1, QTableWidgetItem(due_date))
            table.setItem(i, 2, QTableWidgetItem(self._fmt_try(amount)))
            
            s_item = QTableWidgetItem(status)
            if inst['status'] == 'Ödendi':
                s_item.setForeground(qc("success"))
            elif inst['status'] == 'Gecikmiş':
                s_item.setForeground(qc("danger"))
            else:
                s_item.setForeground(qc("warning"))
            s_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(i, 3, s_item)
            
        layout.addWidget(table)

    def setup_docs_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        if not self.attachments:
            layout.addStretch()
            empty = QLabel("📂 Henüz belge yüklenmemiş.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px;"))
            layout.addWidget(empty)
            layout.addStretch()
            return
            
        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(20)
        
        for i, doc in enumerate(self.attachments):
            f_name = doc['file_name']
            f_path = doc['file_path']
            
            card = QFrame()
            card.setFixedSize(160, 180)
            card.setStyleSheet(theme_qss("""
                QFrame { background: @surface; border: 1px solid @border; border-radius: 8px; }
                QFrame:hover { border: 1px solid @accent; }
            """))
            cl = QVBoxLayout(card)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            icon_lbl = QLabel("📄")
            if f_name.endswith(('.png', '.jpg', '.jpeg')):
                icon_lbl.setText("🖼️")
            elif f_name.endswith('.pdf'):
                icon_lbl.setText("📕")
                
            icon_lbl.setFont(QFont("Segoe UI", 32))
            cl.addWidget(icon_lbl)
            
            name_lbl = QLabel(f_name)
            name_lbl.setWordWrap(True)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_lbl.setStyleSheet(theme_qss("font-size: 12px; color: @text;"))
            cl.addWidget(name_lbl)
            
            btn_open = QPushButton("Aç")
            btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_open.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline", size="sm")))
            btn_open.clicked.connect(lambda _, p=f_path: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
            cl.addWidget(btn_open)
            
            row = i // 4
            col = i % 4
            grid.addWidget(card, row, col)
            
        grid.setRowStretch(grid.rowCount(), 1)
        grid.setColumnStretch(grid.columnCount(), 1)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
