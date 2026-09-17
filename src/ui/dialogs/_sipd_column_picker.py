# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
    QAbstractItemView, QHeaderView
)
from PyQt6.QtGui import QColor
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_warning, show_success
from src.utils.stock_import_parser import StockImportParser

class StockImportPreviewColumnPickerMixin:
    """Excel/CSV/Word için sütun tıklama ile eşleme mantığı."""
    
    def _build_table_column_picker_section(self, layout):
        self._col_picker_role_map = {}
        self._col_picker_raw_columns = list(self.source_columns or [])
        
        hint = QLabel(
            "Sutun basliklarina tiklayarak rolleri belirleyin:\n"
            "  • 1. tik → Mal/Hizmet\n  • 2. tik → Miktar\n  • 3. tik → Birim Fiyat\n  • 4. tik → Para Birimi\n  • 5. tik → Temizle"
        )
        hint.setWordWrap(True); hint.setStyleSheet(theme_qss("font-size: 12px; color: @accent; font-weight: 700;")); layout.addWidget(hint)
        
        raw_rows = list(self.raw_rows or []); cols = self._col_picker_raw_columns
        if not cols and raw_rows: cols = list(raw_rows[0].keys()); self._col_picker_raw_columns = cols
        
        if not cols: layout.addWidget(QLabel("Kolon bilgisi bulunamadi.")); return
        
        picker = QTableWidget(min(len(raw_rows), 30), len(cols))
        picker.setHorizontalHeaderLabels(cols); picker.verticalHeader().setVisible(True)
        picker.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); picker.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        picker.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch); picker.setMinimumHeight(280)
        picker.setStyleSheet(theme_qss("""
            QTableWidget { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; }
            QHeaderView::section { background: @surface; color: @text; font-weight: 700; border: none; border-bottom: 1px solid @border; padding: 6px; }
            QHeaderView::section:hover { background: @accent; color: white; }
        """))
        
        for ri, row in enumerate(raw_rows[:30]):
            for ci, col in enumerate(cols):
                picker.setItem(ri, ci, QTableWidgetItem(str(row.get(col) or "")))
        
        self._col_picker_table = picker; self._col_picker_click_counts = [0] * len(cols)
        picker.horizontalHeader().sectionClicked.connect(self._on_col_picker_header_clicked)
        layout.addWidget(picker, 1)
        
        self._col_picker_status_label = QLabel("Henuz sutun secilmedi.")
        self._col_picker_status_label.setStyleSheet(theme_qss("font-size: 12px; color: @text_muted;"))
        layout.addWidget(self._col_picker_status_label)
        
        act = QHBoxLayout(); bi, br, ba = QPushButton("Secili Sutunlari Aktar"), QPushButton("Sifirla"), QPushButton("Otomatik Esle")
        bi.clicked.connect(self._apply_column_picker_selection); br.clicked.connect(self._reset_col_picker); ba.clicked.connect(self.apply_mapping)
        for w in (bi, br, ba): act.addWidget(w)
        act.addStretch(); layout.addLayout(act)
        
        layout.addWidget(QLabel("Result Preview").setParent(None)); # Spacer logic
        self.live_preview_table = self._make_live_preview_table(); layout.addWidget(self.live_preview_table); self._update_live_preview_table(self.parse_result.get("rows") or [])

    def _on_col_picker_header_clicked(self, ci):
        ROLES = [("name", "Mal/Hizmet", "#2196F3"), ("stock", "Miktar", "#4CAF50"), ("purchase_price", "Birim Fiyat", "#FF9800"), ("currency", "Para Birimi", "#9C27B0")]
        counts, rmap = getattr(self, "_col_picker_click_counts", []), getattr(self, "_col_picker_role_map", {})
        if ci >= len(counts): return
        click = counts[ci]
        if click < len(ROLES):
            rk, rl, color = ROLES[click]
            for pc, pr in list(rmap.items()):
                if pr == rk and pc != ci: rmap.pop(pc, None); counts[pc] = 0; self._col_picker_set_header_color(pc, None, "")
            rmap[ci] = rk; self._col_picker_set_header_color(ci, color, f"[{rl}]"); counts[ci] = click + 1
        else:
            rmap.pop(ci, None); self._col_picker_set_header_color(ci, None, ""); counts[ci] = 0
        self._col_picker_role_map, self._col_picker_click_counts = rmap, counts; self._refresh_col_picker_status()

    def _col_picker_set_header_color(self, ci, color, suffix):
        tbl = getattr(self, "_col_picker_table", None)
        if not tbl: return
        cols = getattr(self, "_col_picker_raw_columns", [])
        if ci >= len(cols): return
        base = cols[ci]; item = tbl.horizontalHeaderItem(ci) or QTableWidgetItem(base)
        if not tbl.horizontalHeaderItem(ci): tbl.setHorizontalHeaderItem(ci, item)
        item.setText(f"{base}\n{suffix}" if suffix else base)
        if color: item.setBackground(QColor(color)); item.setForeground(QColor("#ffffff"))
        else: item.setBackground(QColor(0,0,0,0)); item.setForeground(QColor(0,0,0,0)) # Reset

    def _refresh_col_picker_status(self):
        lbl = getattr(self, "_col_picker_status_label", None)
        if not lbl: return
        rmap, cols = getattr(self, "_col_picker_role_map", {}), getattr(self, "_col_picker_raw_columns", [])
        LABELS = {"name": "Mal/Hizmet", "stock": "Miktar", "purchase_price": "Birim Fiyat", "currency": "Para Birimi"}
        parts = [f"{LABELS.get(r, r)} ← '{cols[ci]}'" for ci, r in rmap.items() if ci < len(cols)]
        lbl.setText(("Secim: " + " | ".join(parts)) if parts else "Henuz sutun secilmedi.")

    def _apply_column_picker_selection(self):
        rmap, cols = getattr(self, "_col_picker_role_map", {}), getattr(self, "_col_picker_raw_columns", [])
        if not rmap: show_warning(self, "En az bir sutun secin."); return
        nm = {r: cols[ci] for ci, r in rmap.items() if ci < len(cols)}
        for f, cb in self.mapping_widgets.items():
            if f in nm:
                idx = cb.findText(nm[f])
                if idx >= 0: cb.setCurrentIndex(idx)
            else: cb.setCurrentText("(Yoksay)")
        self.current_mapping = nm; self.apply_mapping(); rebuilt = StockImportParser._normalize_mapped_rows(self.raw_rows, nm)
        self._update_live_preview_table(rebuilt); show_success(self, f"{len(rebuilt)} satir yeniden duzenlendi.")

    def _reset_col_picker(self):
        self._col_picker_role_map = {}; cols = getattr(self, "_col_picker_raw_columns", [])
        self._col_picker_click_counts = [0] * len(cols)
        for ci in range(len(cols)): self._col_picker_set_header_color(ci, None, "")
        self._refresh_col_picker_status()
