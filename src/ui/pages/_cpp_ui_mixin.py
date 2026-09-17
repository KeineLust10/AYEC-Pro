# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSplitter, QListWidget,
    QTabWidget, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from src.utils.theme_colors import theme_qss
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.empty_state import EmptyState

class PartnersPageUiMixin:
    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20); self.layout.setSpacing(16)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(theme_qss(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0f172a, stop:0.55 #1e293b, stop:1 #334155); border-radius: 18px; border: 1px solid @border;"
        ))
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(22, 18, 22, 18); header_layout.setSpacing(18)

        title_box = QVBoxLayout()
        self.lbl_title = QLabel("Calisma Ortaklari")
        self.lbl_sub = QLabel("Partner kartlarinizi, gonderdiginiz urunleri ve donus surecini tek ekranda yonetin.")
        title_box.addWidget(self.lbl_title); title_box.addWidget(self.lbl_sub)
        header_layout.addLayout(title_box); header_layout.addStretch()

        self.btn_add_partner = QPushButton("+ Yeni Ortak")
        self.btn_add_partner.setCursor(Qt.CursorShape.PointingHandCursor); self.btn_add_partner.setFixedHeight(38)
        self.btn_add_partner.clicked.connect(self.add_partner)
        header_layout.addWidget(self.btn_add_partner)
        self.layout.addWidget(self.header_frame)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False); self.splitter.setHandleWidth(1)
        self.layout.addWidget(self.splitter, 1)

        self._build_partner_sidebar()
        self._build_partner_workspace()
        self.splitter.setSizes([340, 980])

    def _build_partner_sidebar(self):
        self.sidebar = QFrame()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0); sidebar_layout.setSpacing(14)
        filter_card = QFrame()
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 16, 16, 16); filter_layout.setSpacing(10)
        from PyQt6.QtWidgets import QLineEdit
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Ortak ara: ad, sehir, telefon, hizmet...")
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        filter_layout.addWidget(self.inp_search)
        filter_row = QHBoxLayout(); filter_row.setSpacing(10)
        self.cmb_service_type = ModernComboBox(); self.cmb_service_type.setPlaceholderText("Hizmet")
        self.cmb_service_type.currentIndexChanged.connect(self.on_service_type_changed)
        filter_row.addWidget(self.cmb_service_type, 1)
        self.cmb_commission = ModernComboBox(); self.cmb_commission.addItems(["Tumu", "Komisyonlu", "Komisyonsuz"])
        self.cmb_commission.currentIndexChanged.connect(self.on_commission_filter_changed)
        filter_row.addWidget(self.cmb_commission, 1)
        filter_layout.addLayout(filter_row); sidebar_layout.addWidget(filter_card)
        self.partner_list = QListWidget(); self.partner_list.currentRowChanged.connect(self.on_partner_selected)
        sidebar_layout.addWidget(self.partner_list, 1)
        self.partner_list_empty = EmptyState(
            icon="🤝", title="Partner bulunamadı", message="Henüz çalışma ortağı kaydı yok veya arama kriteri sonuç vermedi.",
            action_text="+ Yeni Ortak", action_callback=self.add_partner
        )
        sidebar_layout.addWidget(self.partner_list_empty); self.partner_list_empty.hide()
        self.lbl_total = QLabel("Toplam partner: 0")
        sidebar_layout.addWidget(self.lbl_total); self.splitter.addWidget(self.sidebar)

    def _build_partner_workspace(self):
        self.workspace = QFrame()
        workspace_layout = QVBoxLayout(self.workspace); workspace_layout.setContentsMargins(0, 0, 0, 0); workspace_layout.setSpacing(14)
        self.partner_hero = QFrame()
        hero_layout = QVBoxLayout(self.partner_hero); hero_layout.setContentsMargins(20, 18, 20, 18); hero_layout.setSpacing(12)
        top_row = QHBoxLayout(); text_col = QVBoxLayout()
        self.partner_name = QLabel("Partner secin")
        self.partner_meta = QLabel("Soldan bir calisma ortagi secerek sevk ve takip ekranini acin.")
        self.partner_scorecard = QLabel("Scorecard metrikleri partner secildiginde guncellenir.")
        text_col.addWidget(self.partner_name); text_col.addWidget(self.partner_meta); text_col.addWidget(self.partner_scorecard)
        top_row.addLayout(text_col); top_row.addStretch()
        actions = QHBoxLayout(); actions.setSpacing(10)
        self.btn_add_shipment = QPushButton("+ Gonderi Kaydi"); self.btn_add_shipment.clicked.connect(self.add_partner_tracking)
        self.btn_documents = QPushButton("Belgeler"); self.btn_documents.clicked.connect(self.open_selected_partner_documents)
        self.btn_docs_center = QPushButton("Belge Merkezi"); self.btn_docs_center.clicked.connect(self.open_unified_documents_center)
        self.btn_edit_partner = QPushButton("Ortak Bilgilerini Duzenle"); self.btn_edit_partner.clicked.connect(self.edit_selected_partner)
        self.btn_more = QPushButton("Daha Fazla"); self.btn_more.clicked.connect(self.open_selected_partner_menu)
        for btn in (self.btn_add_shipment, self.btn_documents, self.btn_docs_center, self.btn_edit_partner, self.btn_more):
            btn.setFixedHeight(36); btn.setCursor(Qt.CursorShape.PointingHandCursor); actions.addWidget(btn)
        top_row.addLayout(actions); hero_layout.addLayout(top_row)
        stats_row = QHBoxLayout(); stats_row.setSpacing(12)
        self.stat_total = self._create_stat_card("Toplam Gonderi", "0")
        self.stat_active = self._create_stat_card("Surecte", "0")
        self.stat_done = self._create_stat_card("Tamamlanan", "0")
        self.stat_last = self._create_stat_card("Son Gonderim", "-")
        for card in (self.stat_total, self.stat_active, self.stat_done, self.stat_last): stats_row.addWidget(card, 1)
        hero_layout.addLayout(stats_row); workspace_layout.addWidget(self.partner_hero)

        self.shipment_card = QFrame()
        shipment_layout = QVBoxLayout(self.shipment_card); shipment_layout.setContentsMargins(18, 18, 18, 18); shipment_layout.setSpacing(12)
        self.lbl_shipments_title = QLabel("Gonderilen Urunler"); self.lbl_shipments_sub = QLabel("Secili partnerin acik, servis ve gecmis kayitlari.")
        shipment_layout.addWidget(self.lbl_shipments_title); shipment_layout.addWidget(self.lbl_shipments_sub)
        self.partner_tabs = QTabWidget(); self.partner_tabs.setDocumentMode(True)
        
        self.tab_active = QWidget(); active_layout = QVBoxLayout(self.tab_active); active_layout.setContentsMargins(0, 8, 0, 0)
        self.shipment_table = self._create_tracking_table(); active_layout.addWidget(self.shipment_table)
        self.empty_label = QLabel("Bu partner icin henuz aktif sevk kaydi yok."); self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter); active_layout.addWidget(self.empty_label)
        
        self.tab_history = QWidget(); history_layout = QVBoxLayout(self.tab_history); history_layout.setContentsMargins(0, 8, 0, 0)
        self.history_table = self._create_tracking_table(); history_layout.addWidget(self.history_table)
        self.history_empty_label = QLabel("Tamamlanmis veya kapanmis kayit bulunmuyor."); self.history_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter); history_layout.addWidget(self.history_empty_label)

        self.tab_notes = QWidget(); notes_layout = QVBoxLayout(self.tab_notes); notes_layout.setContentsMargins(0, 12, 0, 0)
        self.notes_summary = QLabel("Secili partner icin hizli notlar ve baglamsal aciklamalar."); self.notes_summary.setWordWrap(True)
        self.btn_open_notes = QPushButton("Partner Notlarini Ac"); self.btn_open_notes.setFixedHeight(38); self.btn_open_notes.clicked.connect(self.open_selected_partner_notes)
        notes_layout.addWidget(self.notes_summary); notes_layout.addWidget(self.btn_open_notes, 0, Qt.AlignmentFlag.AlignLeft); notes_layout.addStretch()

        self.tab_finance = QWidget(); finance_layout = QVBoxLayout(self.tab_finance); finance_layout.setContentsMargins(0, 12, 0, 0)
        self.finance_summary = QLabel("Komisyon, tahsilat ve partner bazli finans hareketlerini yonetin."); self.finance_summary.setWordWrap(True)
        self.finance_card = QFrame(); finance_card_layout = QVBoxLayout(self.finance_card); finance_card_layout.setContentsMargins(16, 16, 16, 16); finance_card_layout.setSpacing(6)
        self.finance_commission = QLabel("Komisyon: -"); self.finance_contact = QLabel("Iletisim: -")
        self.btn_open_finance = QPushButton("Tahsilat / Finans Islemi"); self.btn_open_finance.setFixedHeight(38); self.btn_open_finance.clicked.connect(self.open_selected_partner_finance)
        finance_card_layout.addWidget(self.finance_commission); finance_card_layout.addWidget(self.finance_contact); finance_card_layout.addWidget(self.btn_open_finance, 0, Qt.AlignmentFlag.AlignLeft)
        finance_layout.addWidget(self.finance_summary); finance_layout.addWidget(self.finance_card); finance_layout.addStretch()

        self.tab_documents = QWidget(); documents_layout = QVBoxLayout(self.tab_documents); documents_layout.setContentsMargins(0, 12, 0, 0)
        self.documents_summary = QLabel("Secili partnerin sozlesme, teklif, fatura ve sevk belgeleri."); self.documents_summary.setWordWrap(True)
        self.btn_open_documents = QPushButton("Belgeleri Ac"); self.btn_open_documents.setFixedHeight(38); self.btn_open_documents.clicked.connect(self.open_selected_partner_documents)
        self.documents_table = QTableWidget(); self.documents_table.setColumnCount(4); self.documents_table.setHorizontalHeaderLabels(["Baslik", "Kategori", "Sevk", "Eklenme"])
        self.documents_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.documents_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.documents_table.setShowGrid(False)
        documents_layout.addWidget(self.documents_summary); documents_layout.addWidget(self.btn_open_documents, 0, Qt.AlignmentFlag.AlignLeft); documents_layout.addWidget(self.documents_table)

        self.tab_timeline = QWidget(); timeline_layout = QVBoxLayout(self.tab_timeline); timeline_layout.setContentsMargins(0, 12, 0, 0)
        self.timeline_summary = QLabel("Partner sevklerinin olusturma, teklif, onay, gonderim ve donus olaylari."); self.timeline_summary.setWordWrap(True)
        self.timeline_table = QTableWidget(); self.timeline_table.setColumnCount(4); self.timeline_table.setHorizontalHeaderLabels(["Tarih", "Tip", "Detay", "Sevk"])
        self.timeline_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.timeline_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.timeline_table.setShowGrid(False)
        timeline_layout.addWidget(self.timeline_summary); timeline_layout.addWidget(self.timeline_table)

        self.tab_trends = QWidget(); trends_layout = QVBoxLayout(self.tab_trends); trends_layout.setContentsMargins(0, 12, 0, 0)
        self.trends_summary = QLabel("Partnerin aylik sevk, donus, maliyet ve teklif trendleri."); self.trends_summary.setWordWrap(True)
        self.trend_table = QTableWidget(); self.trend_table.setColumnCount(6); self.trend_table.setHorizontalHeaderLabels(["Donem", "Sevk", "Tamamlanan", "Partner Maliyeti", "Musteriye Yansiyan", "Teklif"])
        self.trend_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.trend_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.trend_table.setShowGrid(False)
        trends_layout.addWidget(self.trends_summary); trends_layout.addWidget(self.trend_table)

        self.partner_tabs.addTab(self.tab_active, "Aktif Gonderiler"); self.partner_tabs.addTab(self.tab_history, "Gecmis")
        self.partner_tabs.addTab(self.tab_notes, "Notlar"); self.partner_tabs.addTab(self.tab_finance, "Finans")
        self.partner_tabs.addTab(self.tab_documents, "Belgeler"); self.partner_tabs.addTab(self.tab_timeline, "Zaman Cizelgesi")
        self.partner_tabs.addTab(self.tab_trends, "Trendler"); shipment_layout.addWidget(self.partner_tabs)
        workspace_layout.addWidget(self.shipment_card, 1); self.splitter.addWidget(self.workspace)

    def _create_tracking_table(self):
        table = QTableWidget(); table.setColumnCount(6); table.setHorizontalHeaderLabels(["Emanet No", "Musteri", "Urun", "Gonderim", "Durum", "Kargo / Servis No"])
        header = table.horizontalHeader(); header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed); header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed); header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 130); table.setColumnWidth(3, 120); table.setColumnWidth(4, 150)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); table.setShowGrid(False)
        table.cellDoubleClicked.connect(self.open_selected_tracking)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu); table.customContextMenuRequested.connect(self._show_partner_tracking_context_menu)
        return table

    def _create_stat_card(self, title, value):
        card = QFrame(); layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12); layout.setSpacing(4)
        v_lbl = QLabel(value); t_lbl = QLabel(title); card._value_label = v_lbl; card._title_label = t_lbl
        layout.addWidget(v_lbl); layout.addWidget(t_lbl); return card

    def on_partner_selected(self, row):
        self.selected_partner = self.filtered_partners[row] if 0 <= row < len(self.filtered_partners) else None
        self.render_partner_details()

    def render_partner_details(self):
        from src.utils.currency_helper import CurrencyHelper
        if not self.selected_partner:
            self.partner_name.setText("Partner secin")
            self.partner_meta.setText("Soldaki listeden bir partner secin veya yeni ortak ekleyin.")
            for c in (self.stat_total, self.stat_active, self.stat_done): self._set_stat_card(c, "0")
            self._set_stat_card(self.stat_last, "-")
            self.partner_scorecard.setText("Ortalama donus, SLA uyumu, tekrar ariza ve kalite sorunlari bu alanda gorunur.")
            for t in (self.shipment_table, self.history_table, self.documents_table, self.timeline_table, self.trend_table): t.setRowCount(0)
            self.empty_label.show(); self.history_empty_label.show()
            for btn in (self.btn_add_shipment, self.btn_documents, self.btn_docs_center, self.btn_edit_partner, self.btn_more, self.btn_open_notes, self.btn_open_finance, self.btn_open_documents):
                btn.setEnabled(False)
            return

        for btn in (self.btn_add_shipment, self.btn_documents, self.btn_docs_center, self.btn_edit_partner, self.btn_more, self.btn_open_notes, self.btn_open_finance, self.btn_open_documents):
            btn.setEnabled(True)

        p = self.selected_partner
        p_type = str(p.get("type") or "Partner"); s_type = str(p.get("service_type") or "Genel")
        city = str(p.get("city") or ""); contract = str(p.get("contract_type") or "Standart Anlasma")
        sla = str(p.get("sla_level") or "24 Saat Donus")
        comm = 0.0
        try: comm = float(p.get("commission_rate") or 0)
        except Exception: comm = 0.0
        meta = [p_type, s_type]; 
        if city: meta.append(city)
        if comm: meta.append("Komisyon %{0:.2f}".format(comm))
        self.partner_name.setText("{badge}  {name}".format(badge=self._partner_badge(p), name=str(p.get("name") or "Partner")))
        self.partner_meta.setText("  |  ".join(meta))
        
        fin = self._partner_finance_summary(p); quote = self._partner_quote_summary(p)
        self.finance_commission.setText("Partner Borcu: {cost} | Odenen: {paid} | Kalan: {balance}".format(
            cost=CurrencyHelper.format_try_for_display(fin["partner_cost"], db=self.db, include_try_reference=False),
            paid=CurrencyHelper.format_try_for_display(fin["paid_total"], db=self.db, include_try_reference=False),
            balance=CurrencyHelper.format_try_for_display(fin["balance"], db=self.db, include_try_reference=False)
        ))
        self.finance_contact.setText("Iletisim: {ph}  |  {em}  |  Sozlesme: {ct}  |  SLA: {sla} | Teklif: {q} | Musteri: {cto}".format(
            ph=str(p.get("phone") or "-"), em=str(p.get("email") or "-"), ct=contract, sla=sla,
            q=CurrencyHelper.format_try_for_display(quote["quote_total"], db=self.db, include_try_reference=False),
            cto=CurrencyHelper.format_try_for_display(fin["customer_total"], db=self.db, include_try_reference=False)
        ))
        
        tracks = self._partner_trackings(p); scorecard = self._partner_scorecard(p, tracks)
        self.partner_scorecard.setText("Donus: {avg}s | SLA: %{sla} | Tekrar: {rep} | Geri: %{cb} | Kalite: {q} | Aktif: {act}".format(
            avg=scorecard["avg_turnaround"], sla=scorecard["on_time_rate"], rep=scorecard["repeat_serials"],
            cb=scorecard["comeback_ratio"], q=scorecard["quality_issues"], act=scorecard["active_count"]
        ))
        for c, v in [(self.stat_total, len(tracks)), (self.stat_active, scorecard["active_count"]), (self.stat_done, len(tracks)-scorecard["active_count"])]:
            self._set_stat_card(c, str(v))
        self._set_stat_card(self.stat_last, tracks[0]["date"] if tracks else "-")

        self.shipment_table.setRowCount(0); self.history_table.setRowCount(0)
        active_t = [t for t in tracks if not self._is_completed_status(t["status"])]
        history_t = [t for t in tracks if self._is_completed_status(t["status"])]
        
        for table, tt in [(self.shipment_table, active_t), (self.history_table, history_t)]:
            for i, t in enumerate(tt):
                table.insertRow(i)
                vals = [t["internal_no"] or "-", t["customer"] or "-", t["product"] or "-", t["date"] or "-", t["status"] or "-", 
                        " / ".join([v for v in [t.get("out_cargo"), t.get("in_cargo"), t.get("service_no")] if v]) or "-"]
                for j, v in enumerate(vals):
                    item = QTableWidgetItem(str(v)); item.setData(Qt.ItemDataRole.UserRole, t["id"])
                    if j in (0, 3, 4): item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(i, j, item)
                table.setRowHeight(i, 54)
        self.empty_label.setVisible(not active_t); self.history_empty_label.setVisible(not history_t)
        
        self.documents_table.setRowCount(0); self._populate_simple_table(self.documents_table, self._partner_document_rows(p))
        self.timeline_table.setRowCount(0); self._populate_simple_table(self.timeline_table, self._partner_timeline_rows(p))
        self.trend_table.setRowCount(0); self._populate_trend_table(self.trend_table, self._partner_trend_rows(p))

    def _set_stat_card(self, card, value):
        card._value_label.setText(str(value))

    def _populate_simple_table(self, table, rows):
        table.setRowCount(0)
        for i, row in enumerate(rows):
            table.insertRow(i)
            for j, v in enumerate(row):
                item = QTableWidgetItem(str(v if v not in (None, "") else "-"))
                if j in (0, 1, 3): item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i, j, item)
            table.setRowHeight(i, 44)

    def _populate_trend_table(self, table, rows):
        from src.utils.currency_helper import CurrencyHelper
        table.setRowCount(0)
        for i, row in enumerate(rows):
            table.insertRow(i)
            vals = [row[0], row[1], row[2], 
                    CurrencyHelper.format_try_for_display(float(row[3] or 0), db=self.db, include_try_reference=False),
                    CurrencyHelper.format_try_for_display(float(row[4] or 0), db=self.db, include_try_reference=False),
                    CurrencyHelper.format_try_for_display(float(row[5] or 0), db=self.db, include_try_reference=False)]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if j != 0: item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(i, j, item)
            table.setRowHeight(i, 42)

    def open_selected_tracking(self, row, _column=0):
        from src.ui.dialogs.partner_shipment_dialog import PartnerShipmentDialog
        sender = self.sender(); item = sender.item(row, 0) if sender else self.shipment_table.item(row, 0)
        if not item: return
        t_id = item.data(Qt.ItemDataRole.UserRole)
        if PartnerShipmentDialog(self.db, self.selected_partner, self.window() or self, shipment_id=t_id).exec():
            self.render_partner_details()
