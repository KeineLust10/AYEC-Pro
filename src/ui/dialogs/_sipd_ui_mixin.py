# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSplitter, QWidget,
    QTableWidget, QTextEdit, QScrollArea
)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QWheelEvent
from src.utils.theme_colors import theme_qss
from src.ui.dialogs._sipd_label import SourceSelectionLabel


class _WheelScrollArea(QScrollArea):
    """Mouse tekerleği ile kaydırmayı destekleyen QScrollArea."""
    def wheelEvent(self, event: QWheelEvent):
        bar = self.verticalScrollBar()
        if bar:
            delta = event.angleDelta().y()
            bar.setValue(bar.value() - delta // 2)
        event.accept()

class StockImportPreviewUiMixin:
    def _build_ui(self):
        content = QWidget(); root = QVBoxLayout(content); root.setContentsMargins(16, 16, 16, 16); root.setSpacing(10)
        splitter = QSplitter(Qt.Orientation.Horizontal); splitter.setChildrenCollapsible(False)

        # Sol panel: kaydırılabilir (mouse wheel scroll desteği ile)
        left_inner = QWidget(); layout = QVBoxLayout(left_inner); layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(12)
        left_scroll = _WheelScrollArea(); left_scroll.setWidgetResizable(True); left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(560)
        left_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        left_panel = left_inner  # compat alias — layout ekleme hedefi aynı
        source_lbl = QLabel(f"Kaynak dosya: {self.parse_result.get('source_path', '-')}")
        source_lbl.setWordWrap(True); source_lbl.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        layout.addWidget(source_lbl)
        
        metadata = self.parse_result.get("metadata") or {}
        if metadata:
            parts = [f"{k}: {v}" for k, v in metadata.items() if v]
            if parts:
                meta_lbl = QLabel(" | ".join(parts)); meta_lbl.setWordWrap(True)
                meta_lbl.setStyleSheet(theme_qss("font-size: 12px; color: @accent; font-weight: 700;"))
                layout.addWidget(meta_lbl)
        
        warnings = self.parse_result.get("warnings") or []
        if warnings:
            w_box = QLabel("\n".join(f"- {i}" for i in warnings)); w_box.setWordWrap(True)
            w_box.setStyleSheet(theme_qss("background: @warning_bg; color: @warning; border: 1px solid @warning; border-radius: 10px; padding: 10px 12px; font-weight: 600;"))
            layout.addWidget(w_box)
        
        hint = QLabel("Dusuk guvenli satirlar sari, meta veya toplam supheli satirlar kirmizi tonda gosterilir.")
        hint.setWordWrap(True); hint.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        layout.addWidget(hint)
        
        if self.parse_result.get("source_type") in {"jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff", "pdf"}:
            tools = QHBoxLayout(); tools.addStretch()
            self.btn_crop_retry = QPushButton("Belgeyi Kirp ve Yeniden Tara"); self.btn_crop_retry.clicked.connect(self.crop_and_reparse)
            tools.addWidget(self.btn_crop_retry); layout.addLayout(tools)
        
        layout.addWidget(self._build_mapping_card())
        
        toolbar = QHBoxLayout()
        h = QLabel("Cekilen listeyi burada duzenleyin. Kaydetmeden veritabani degismez.")
        h.setStyleSheet(theme_qss("font-size: 12px; color: @text; font-weight: 600;"))
        toolbar.addWidget(h); toolbar.addStretch()
        self.btn_add = QPushButton("Satir Ekle"); self.btn_remove = QPushButton("Secileni Sil"); self.btn_save = QPushButton("Kaydet ve Iceri Aktar")
        self.btn_add.clicked.connect(self.add_empty_row); self.btn_remove.clicked.connect(self.remove_selected_rows); self.btn_save.clicked.connect(self.save_rows)
        for b in (self.btn_add, self.btn_remove, self.btn_save): toolbar.addWidget(b)
        layout.addLayout(toolbar)
        
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([l for _, l in self.COLUMNS])
        from PyQt6.QtWidgets import QAbstractItemView; self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.table.verticalHeader().setVisible(False); self.table.horizontalHeader().setStretchLastSection(True); self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(260)
        self._apply_table_styles(); layout.addWidget(self.table, 1)
        
        footer = QHBoxLayout(); footer.addStretch()
        btn_cancel = QPushButton("Vazgec"); btn_cancel.clicked.connect(self.reject); footer.addWidget(btn_cancel)
        layout.addLayout(footer)

        # Sol scroll area'ya inner widget'ı yerleştir
        left_scroll.setWidget(left_inner)

        right_panel = self._build_source_preview_panel()
        right_panel.setMinimumWidth(620)
        splitter.addWidget(left_scroll); splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1); splitter.setStretchFactor(1, 2); splitter.setSizes([650, 1050])
        root.addWidget(splitter, 1)
        self.add_widget(content); self._apply_saved_mapping_if_available(); self._load_rows()

    def _build_source_preview_panel(self):
        panel = QFrame(); panel.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; } QLabel { border: none; background: transparent; }"))
        layout = QVBoxLayout(panel); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(10)
        t_row = QHBoxLayout(); t = QLabel("Kaynak Onizleme"); t.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text;")); t_row.addWidget(t); t_row.addStretch()
        self.btn_preview_zoom_out = QPushButton("🔍−"); self.btn_preview_zoom_in = QPushButton("🔍+")
        for b, tip in [(self.btn_preview_zoom_out, "Zoom Out"), (self.btn_preview_zoom_in, "Zoom In")]:
            b.setToolTip(tip); b.setFixedSize(38, 30); b.setStyleSheet(theme_qss("QPushButton { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 6px; font-weight: 800; } QPushButton:hover { background: @hover_bg; border-color: @accent; }"))
            t_row.addWidget(b)
        self.btn_preview_zoom_out.clicked.connect(self._zoom_preview_out); self.btn_preview_zoom_in.clicked.connect(self._zoom_preview_in)
        layout.addLayout(t_row); s = QLabel("Dosyayi goruntuleyin, surukleyerek alan secin veya sutunlara tiklayarak esleyin."); s.setWordWrap(True); s.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        layout.addWidget(s)
        src, stype = str(self.parse_result.get("source_path") or "").strip(), str(self.parse_result.get("source_type") or "").strip().lower()
        if src and stype in {"jpg", "jpeg", "png", "bmp", "webp", "tif", "tiff", "ppm"}: self._build_image_preview_section(layout, src)
        elif src and stype == "pdf": self._build_pdf_preview_section(layout, src)
        elif src and stype in {"xlsx", "xls", "ods", "csv", "docx", "doc"}: self._build_table_column_picker_section(layout)
        else: self._build_text_summary_section(layout, src, stype)
        return panel

    def _build_image_preview_section(self, layout, src):
        self.source_preview_label = SourceSelectionLabel(); self.source_preview_label.set_fit_width(True); self.source_preview_label.set_image_path(src)
        self._restore_last_expanded_selection(); self._live_preview_source_path = src
        self.source_preview_label.selection_committed.connect(self._schedule_live_selection_preview)
        if self.source_preview_label.original_pixmap.isNull(): self.source_preview_label.setText("Gorsel onizleme yuklenemedi.")
        layout.addWidget(self._wrap_source_preview_label(self.source_preview_label), 1)
        h = QLabel("Alan secmek icin fareyi basili tutup surukleyin — secili bolge otomatik taranir."); h.setWordWrap(True); h.setStyleSheet(theme_qss("font-size: 12px; color: @accent; font-weight: 700;")); layout.addWidget(h)
        aa = QHBoxLayout(); self.btn_apply_area = QPushButton("Secili Alani Tara ve Aktar"); bc = QPushButton("Secimi Temizle")
        self.btn_apply_area.clicked.connect(self._apply_preview_selection); bc.clicked.connect(self._clear_preview_selection)
        aa.addWidget(self.btn_apply_area); aa.addWidget(bc); aa.addStretch(); layout.addLayout(aa)
        pt = QLabel("Dinamik Onizleme (Secili Alan)"); pt.setStyleSheet(theme_qss("font-size: 12px; font-weight: 800; color: @text;")); layout.addWidget(pt)
        self.live_preview_table = self._make_live_preview_table(); layout.addWidget(self.live_preview_table); self._update_live_preview_table(self.parse_result.get("rows") or [])

    def _build_pdf_preview_section(self, layout, src):
        rendered = self._render_pdf_page_to_temp(src, page=0, dpi=150)
        if rendered:
            self.source_preview_label = SourceSelectionLabel(); self.source_preview_label.set_fit_width(True); self.source_preview_label.set_image_path(rendered)
            self._restore_last_expanded_selection(); self._live_preview_source_path = rendered; self._pdf_rendered_temp = rendered
            self.source_preview_label.selection_committed.connect(self._schedule_live_selection_preview)
            layout.addWidget(self._wrap_source_preview_label(self.source_preview_label), 1)
            self._pdf_source_path, self._pdf_current_page, self._pdf_total_pages = src, 0, self._get_pdf_page_count(src)
            nav = QHBoxLayout(); self._pdf_page_label = QLabel(f"Sayfa 1 / {self._pdf_total_pages}"); self._pdf_page_label.setStyleSheet(theme_qss("font-size: 12px; color: @text;"))
            bp, bn = QPushButton("◀ Önceki"), QPushButton("Sonraki ▶"); bp.clicked.connect(lambda: self._navigate_pdf_page(-1)); bn.clicked.connect(lambda: self._navigate_pdf_page(+1))
            for ww in (bp, self._pdf_page_label, bn): nav.addWidget(ww)
            nav.addStretch(); layout.addLayout(nav)
            h = QLabel("Tablo alanini surukleyerek secin, ardından 'Secili Alani Tara ve Aktar' butonuna basin."); h.setWordWrap(True); h.setStyleSheet(theme_qss("font-size: 12px; color: @accent; font-weight: 700;")); layout.addWidget(h)
            act = QHBoxLayout(); self.btn_apply_area = QPushButton("Secili Alani Tara ve Aktar"); bf = QPushButton("Tum Sayfayi Tara"); bc = QPushButton("Secimi Temizle")
            self.btn_apply_area.clicked.connect(self._apply_preview_selection); bf.clicked.connect(lambda: self._reparse_full_source(src)); bc.clicked.connect(self._clear_preview_selection)
            for ww in (self.btn_apply_area, bf, bc): act.addWidget(ww)
            act.addStretch(); layout.addLayout(act)
            self.live_preview_table = self._make_live_preview_table(); layout.addWidget(self.live_preview_table); self._update_live_preview_table(self.parse_result.get("rows") or [])
        else: self._build_text_summary_section(layout, src, "pdf", extra_note="PDF goruntu olarak render edilemedi. Metin modunda ayrıştırıldı.")

    def _build_text_summary_section(self, layout, src, stype, extra_note=None):
        if extra_note:
            n = QLabel(extra_note); n.setWordWrap(True); n.setStyleSheet(theme_qss("font-size: 12px; color: @warning; font-weight: 600;")); layout.addWidget(n)
        info = QTextEdit(); info.setReadOnly(True); info.setMinimumHeight(500); info.setStyleSheet(theme_qss("QTextEdit { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 10px; padding: 10px; font-size: 12px; }"))
        m, r = self.parse_result.get("metadata") or {}, self.parse_result.get("rows") or []
        lines = [f"Dosya: {src or '-'}", f"Tur: {stype or '-'}", "", "Meta:"] + [f"- {k}: {v}" for k, v in m.items()] + ["", f"Algilanan satir: {len(r)}"]
        for i, rr in enumerate(r[:20], 1): lines.append(f"{i}. {rr.get('name','')} | adet={rr.get('stock',0)} | alis={rr.get('purchase_price',0)}")
        info.setPlainText("\n".join(lines)); layout.addWidget(info, 1)
        act = QHBoxLayout(); br = QPushButton("Dosyayi Yeniden Tara"); br.clicked.connect(lambda: self._reparse_full_source(src)); act.addWidget(br); act.addStretch(); layout.addLayout(act)
        self.live_preview_table = self._make_live_preview_table(); layout.addWidget(self.live_preview_table); self._update_live_preview_table(r)

    def _wrap_source_preview_label(self, label):
        s = QScrollArea(); s.setWidgetResizable(True); s.setMinimumHeight(560); s.setFrameShape(QFrame.Shape.NoFrame); s.setWidget(label)
        s.setStyleSheet(theme_qss("QScrollArea { background: @surface_alt; border: 1px dashed @border; border-radius: 10px; } QScrollArea > QWidget > QWidget { background: @surface_alt; }"))
        return s

    def _make_live_preview_table(self):
        from PyQt6.QtWidgets import QHeaderView, QAbstractItemView; t = QTableWidget(0, 6); t.setHorizontalHeaderLabels(["Mal/Hizmet (Urun Adi)", "Miktar (Stok)", "Birim Fiyati (Alis)", "Satis Fiyati", "Mal Hizmet Tutari", "Para Birimi"])
        t.verticalHeader().setVisible(False); t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); t.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection); t.horizontalHeader().setStretchLastSection(True); t.setMinimumHeight(190)
        t.setStyleSheet(theme_qss("QTableWidget { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; outline: none; } QTableWidget::item { outline: none; } QTableWidget::item:focus { outline: none; border: none; } QHeaderView::section { background: @surface; color: @text; font-weight: 700; border: none; border-bottom: 1px solid @border; padding: 6px; }"))
        return t

    def _build_mapping_card(self):
        from PyQt6.QtWidgets import QGridLayout, QComboBox; from src.ui.widgets.modern_inputs import ModernComboBox; from src.utils.stock_import_parser import StockImportParser
        c = QWidget(); c.setStyleSheet(theme_qss("QWidget { background: @surface; border: 1px solid @border; border-radius: 12px; } QLabel { border: none; background: transparent; }"))
        o = QVBoxLayout(c); o.setContentsMargins(14,14,14,14); o.setSpacing(10)
        t = QLabel("Baslik Esleme"); t.setStyleSheet(theme_qss("font-size: 14px; font-weight: 800; color: @text;")); o.addWidget(t)
        h = QLabel("Kaynak dosyada bulunan basliklari kendi stok alanlariniza esleyin. Eslemeyi uyguladiginizda liste yeniden kurulur."); h.setWordWrap(True); h.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;")); o.addWidget(h)
        pr = QHBoxLayout(); pr.addWidget(QLabel("Hazir Profil:")); bt, ba, bm = QPushButton("Teknik Servis"), QPushButton("Otomotiv"), QPushButton("Resimdeki Gibi Ayarla")
        bt.clicked.connect(lambda: self.apply_profile("teknik_servis")); ba.clicked.connect(lambda: self.apply_profile("otomotiv")); bm.clicked.connect(lambda: self._apply_saved_mapping_if_available(manual=True))
        bt.setEnabled(not self.is_automotive); ba.setEnabled(self.is_automotive)
        for bb in (bt, ba, bm): pr.addWidget(bb)
        pr.addStretch(); o.addLayout(pr)
        s = QLabel("Otomotiv onerileri: Arac Marka, Arac Model, Tedarikci, Parca Konumu" if self.is_automotive else "Teknik servis icin fatura kolonlari: Mal/Hizmet, Miktar, Birim Fiyat, Tutar")
        s.setStyleSheet(theme_qss("font-size: 12px; color: @accent; font-weight: 700;")); o.addWidget(s)
        sc = _WheelScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.Shape.NoFrame)
        sc.setMaximumHeight(220)
        inner = QWidget(); grid = QGridLayout(inner); grid.setContentsMargins(0,0,0,0); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(8)
        choices = ["(Yoksay)"] + self.source_columns
        for i, (f, l) in enumerate(self.COLUMNS):
            row, col = i // 3, (i % 3) * 2; lbl = QLabel(l); lbl.setStyleSheet(theme_qss("font-weight: 700; color: @text;")); cb = QComboBox(); cb.addItems(choices)
            s_val = self.current_mapping.get(f, ""); cb.setCurrentText(s_val if s_val in choices else "(Yoksay)"); cb.setStyleSheet(theme_qss("min-height: 34px;")); self.mapping_widgets[f] = cb; grid.addWidget(lbl, row, col); grid.addWidget(cb, row, col+1)
        sc.setWidget(inner); o.addWidget(sc); act = QHBoxLayout(); act.addStretch(); bapp = QPushButton("Eslemeyi Uygula"); bapp.clicked.connect(self.apply_mapping); act.addWidget(bapp); o.addLayout(act); return c
