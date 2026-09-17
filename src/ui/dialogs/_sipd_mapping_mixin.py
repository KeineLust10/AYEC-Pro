# -*- coding: utf-8 -*-
import json
from pathlib import Path
from src.utils.toast_notification import show_success, show_warning
from src.utils.stock_import_parser import StockImportParser

class StockImportPreviewMappingMixin:
    def _mapping_store_path(self):
        base = Path.home() / ".ayecpro"; base.mkdir(parents=True, exist_ok=True); return base / "stock_import_mappings.json"

    def _mapping_signature(self):
        normalized = sorted([col for col in [StockImportParser._normalize_key(c) for c in (self.source_columns or [])] if col])
        return "|".join(normalized)

    def _mapping_template_key(self): return f"{self.current_profile}::{self._mapping_signature()}"

    def _mapping_file_key(self):
        src = str(self.parse_result.get("source_path") or "").strip()
        return f"file::{self.current_profile}::{Path(src).name.lower()}" if src else None

    def _load_mapping_templates(self):
        try:
            p = self._mapping_store_path()
            if not p.exists(): return {}
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f); return data if isinstance(data, dict) else {}
        except Exception: return {}

    def _save_mapping_templates(self, payload):
        try:
            with open(self._mapping_store_path(), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception: pass

    def _save_current_mapping_template(self):
        if not self.current_mapping: return
        data = self._load_mapping_templates()
        data[self._mapping_template_key()] = dict(self.current_mapping)
        fk = self._mapping_file_key(); 
        if fk: data[fk] = dict(self.current_mapping)
        self._save_mapping_templates(data)

    def _apply_saved_mapping_if_available(self, manual=False):
        data = self._load_mapping_templates(); mapping = None; fk = self._mapping_file_key()
        if fk: mapping = data.get(fk)
        if not mapping: mapping = data.get(self._mapping_template_key())
        if not mapping:
            if manual: show_warning(self, "Bu dosya yapisi icin kayitli bir esleme sablonu bulunamadi.")
            return False
        applied = False
        for field, combo in self.mapping_widgets.items():
            if not manual and combo.currentText() != "(Yoksay)":
                continue
            src = mapping.get(field)
            if src and combo.findText(src) >= 0: combo.setCurrentText(src); applied = True
        if applied:
            self.apply_mapping(initial=True)
            if manual: show_success(self, "Kayitli esleme sablonu uygulandi.")
            return True
        if manual: show_warning(self, "Kayitli esleme bulundu ama bu dosyada uyumlu kolon yok.")
        return False

    def apply_profile(self, profile_name):
        if (self.is_automotive and profile_name != "otomotiv") or (not self.is_automotive and profile_name == "otomotiv"): return
        self.current_profile = profile_name
        pm = StockImportParser.build_profile_mapping(self.source_columns, profile_name)
        for f, c in self.mapping_widgets.items():
            src = pm.get(f, "(Yoksay)"); c.setCurrentText(src if c.findText(src) >= 0 else "(Yoksay)")
        self.apply_mapping()

    def _ensure_mapping_from_raw_rows(self):
        if not self.raw_rows: return
        keys = set()
        for r in self.raw_rows[:5]: keys.update(str(k or "").strip() for k in r.keys())
        auto = {f: f for f in self.active_fields if f in keys}
        if auto: self.current_mapping = auto

    def apply_mapping(self, initial=False):
        mapping = {}
        for field, _ in self.COLUMNS:
            c = self.mapping_widgets.get(field)
            if c and c.currentText() and c.currentText() != "(Yoksay)": mapping[field] = c.currentText()
        if not mapping:
            self._ensure_mapping_from_raw_rows(); mapping = dict(self.current_mapping or {})
        self.current_mapping = mapping; self._save_current_mapping_template()
        rebuilt = StockImportParser._normalize_mapped_rows(self.raw_rows, self.current_mapping)
        self.table.setRowCount(0)
        if not rebuilt:
            if not initial: show_warning(self, "Bu esleme ile okunabilir satir olusmadi. Elle duzenleyebilirsiniz.")
            self.add_empty_row(); return
        for r in rebuilt: self._append_row(r)
