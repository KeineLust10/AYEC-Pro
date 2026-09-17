# -*- coding: utf-8 -*-
import os
import re
import json
import tempfile
import logging
from pathlib import Path
from PIL import Image, ImageOps
from PyQt6.QtCore import QThread, QTimer, QSize, QRect
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QTableWidgetItem, QDialog, QVBoxLayout, QLabel, QGridLayout, QSpinBox, QDialogButtonBox
from src.utils.toast_notification import show_error, show_success, show_info, show_warning
from src.utils.stock_import_parser import StockImportParser
from src.ui.dialogs._sipd_worker import _OcrWorker

_LOG = logging.getLogger(__name__)

# Lazy import to avoid circular dependency
def get_parse_process_worker():
    try:
        from src.utils.parse_subprocess_worker import ParseProcessWorker
        return ParseProcessWorker
    except ImportError:
        return None

class StockImportPreviewLogicMixin:
    def _zoom_preview_in(self):
        lbl = getattr(self, "source_preview_label", None)
        if lbl: lbl.zoom_in()

    def _zoom_preview_out(self):
        lbl = getattr(self, "source_preview_label", None)
        if lbl: lbl.zoom_out()

    def _render_pdf_page_to_temp(self, pdf_path, page=0, dpi=150):
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf:
                if page >= len(pdf.pages): page = 0
                pg = pdf.pages[page]
                pil_img = pg.to_image(resolution=dpi).original
                fd, tmp = tempfile.mkstemp(prefix="ayec_pdf_preview_", suffix=".png")
                os.close(fd); pil_img.save(tmp); return tmp
        except Exception: pass
        try:
            from PyQt6.QtPdf import QPdfDocument, QPdfPageRenderer
            doc = QPdfDocument(None)
            if doc.load(str(pdf_path)) != QPdfDocument.Status.Ready: return None
            renderer = QPdfPageRenderer(None); renderer.setDocument(doc)
            if page >= doc.pageCount(): page = 0
            ps = doc.pagePointSize(page); scale = dpi / 72.0
            img = renderer.render(page, QSize(max(1, int(ps.width()*scale)), max(1, int(ps.height()*scale))))
            if img.isNull(): return None
            fd, tmp = tempfile.mkstemp(prefix="ayec_pdf_preview_", suffix=".png")
            os.close(fd); img.save(tmp, "PNG"); return tmp
        except Exception: return None

    def _get_pdf_page_count(self, pdf_path):
        try:
            import pdfplumber
            with pdfplumber.open(str(pdf_path)) as pdf: return max(1, len(pdf.pages))
        except Exception: pass
        return 1

    def _navigate_pdf_page(self, delta):
        p = max(0, min(getattr(self, "_pdf_total_pages", 1)-1, getattr(self, "_pdf_current_page", 0)+delta))
        if p == getattr(self, "_pdf_current_page", 0): return
        self._pdf_current_page = p
        src = getattr(self, "_pdf_source_path", ""); rendered = self._render_pdf_page_to_temp(src, page=p)
        if rendered and self.source_preview_label:
            old = getattr(self, "_pdf_rendered_temp", None)
            if old and old != rendered:
                try: os.remove(old)
                except Exception: pass
            self._pdf_rendered_temp = rendered; self._live_preview_source_path = rendered; self.source_preview_label.set_image_path(rendered)
        lbl = getattr(self, "_pdf_page_label", None)
        if lbl: lbl.setText(f"Sayfa {p + 1} / {getattr(self, '_pdf_total_pages', 1)}")

    def _load_rows(self):
        self.table.setRowCount(0); rows = self.parse_result.get("rows") or []
        if rows:
            for r in rows:
                # Fatura kaynakli satirlar (_from_invoice=True) icin marka ayirma yapma
                # Cunku bu satirlar zaten dogrulanmis isimlerle geliyor
                if not r.get("_from_invoice") and not str(r.get("brand") or "").strip():
                    b, c = self._split_brand_from_name(str(r.get("name") or ""))
                    if b: r["brand"], r["name"] = b, c
                self._append_row(r)
            return
        if self.raw_rows:
            if not self.current_mapping: self._ensure_mapping_from_raw_rows()
            self.apply_mapping(initial=True); return
        self.add_empty_row()

    def _append_row(self, row_data):
        idx = self.table.rowCount(); self.table.insertRow(idx)
        for ci, (f, _) in enumerate(self.COLUMNS):
            val = row_data.get(f, "")
            if f == "price":
                try: 
                    if float(val) == 0: val = ""
                except (TypeError, ValueError): pass
            self.table.setItem(idx, ci, QTableWidgetItem(str(val)))
        self._decorate_row(idx, row_data)

    def add_empty_row(self): self._append_row({f: "" for f, _ in self.COLUMNS})

    def remove_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()}, reverse=True)
        if not rows: show_info(self, "Silmek icin en az bir satir secin."); return
        for r in rows: self.table.removeRow(r)

    def crop_and_reparse(self):
        src = str(self.parse_result.get("source_path") or "").strip()
        if not src: show_error(self, "Kaynak dosya bulunamadi."); return
        work = src; stype = str(self.parse_result.get("source_type") or "").lower()
        if stype == "pdf":
            rendered = getattr(self, "_pdf_rendered_temp", None)
            if rendered and Path(rendered).exists(): work = rendered
        if self.source_preview_label:
            sel = self.source_preview_label.get_selected_rect_on_original()
            if sel: self._start_area_ocr(work, sel, apply_mode=True); return
        try:
            img = Image.open(work); img = ImageOps.exif_transpose(img)
            rect = self._open_safe_crop_dialog(img.width, img.height)
            if rect: self._start_area_ocr(work, rect, apply_mode=True)
        except Exception as e: show_error(self, f"Kirpma hatasi: {e}")

    def _apply_preview_selection(self):
        src = str(self.parse_result.get("source_path") or "").strip()
        if not src: show_warning(self, "Kaynak dosya bulunamadi."); return
        work = src; stype = str(self.parse_result.get("source_type") or "").lower()
        if stype == "pdf":
            rendered = getattr(self, "_pdf_rendered_temp", None)
            if rendered and Path(rendered).exists(): work = rendered
        try:
            sel = self.source_preview_label.get_selected_rect_on_original() if self.source_preview_label else None
            if sel is None or sel.width() < 30 or sel.height() < 30:
                try:
                    img = Image.open(work); img = ImageOps.exif_transpose(img); sel = self._fallback_crop_rect(img.width, img.height); 
                    show_info(self, "Secili alan kucuk. Otomatik tablo bolgesi tarandi.")
                except Exception: self._reparse_full_source(src); return
            self._start_area_ocr(work, sel, apply_mode=True)
        except Exception as e: show_error(self, f"Secili alan tarama hatasi: {e}"); self._reparse_full_source(src)

    def _start_area_ocr(self, source_path, selected, apply_mode=False):
        selected = self._expand_selected_area_horizontally(source_path, selected, update_preview=True)
        old_thread = getattr(self, "_ocr_thread", None)
        if old_thread and old_thread.isRunning():
            try: old_thread.quit(); old_thread.wait(300)
            except RuntimeError: pass
        self._ocr_thread = None; self._ocr_worker = None
        fb = self.parse_result.get("rows") or []; thread = QThread(); worker = _OcrWorker(source_path, selected, apply_mode=apply_mode, fallback_rows=fb)
        worker.moveToThread(thread)
        if apply_mode: self._set_area_scan_busy(True)
        def _on_done(res, _t=thread, _w=worker):
            p = res if isinstance(res, dict) else {"rows": res or []}
            rows = p.get("rows") or []
            if apply_mode:
                self._set_area_scan_busy(False)
                if rows: p["source_path"] = str(self.parse_result.get("source_path") or source_path); self._refresh_from_parse_result(p)
                else: show_warning(self, p.get("message") or "Okunabilir satir bulunamadi.")
            else: self._update_live_preview_table(rows)
            try: _t.quit(); _t.wait(200)
            except RuntimeError: pass
            _w.deleteLater(); _t.deleteLater()
            if getattr(self, "_ocr_thread", None) is _t: self._ocr_thread = None; self._ocr_worker = None
        thread.started.connect(worker.run); worker.finished.connect(_on_done); self._ocr_thread = thread; self._ocr_worker = worker; thread.start()

    def _reparse_full_source(self, source_path):
        if getattr(self, "_full_parse_worker", None) and self._full_parse_worker.isRunning(): show_info(self, "Tarama zaten devam ediyor."); return
        pw = get_parse_process_worker()
        if not pw: show_error(self, "Process worker yuklenemedi."); return
        self.setEnabled(False); self._full_parse_worker = pw(source_path)
        def _done(f):
            f["source_path"] = source_path; self._refresh_from_parse_result(f); self.setEnabled(True); self._cleanup_full_parse_worker()
        def _err(m): self.setEnabled(True); self._cleanup_full_parse_worker(); show_error(self, f"Tarama hatasi: {m}")
        self._full_parse_worker.finished.connect(_done); self._full_parse_worker.error.connect(_err); self._full_parse_worker.start()

    def _cleanup_full_parse_worker(self):
        w = getattr(self, "_full_parse_worker", None); self._full_parse_worker = None
        if w: w.deleteLater()

    def _schedule_live_selection_preview(self):
        if not self.source_preview_label or not self.live_preview_table: return
        src = self._live_preview_source_path or str(self.parse_result.get("source_path") or "").strip()
        sel = self.source_preview_label.get_selected_rect_on_original()
        if src and sel: self._expand_selected_area_horizontally(src, sel, update_preview=True)
        self._live_preview_timer.start(400)

    def _refresh_live_preview(self):
        src = self._live_preview_source_path or str(self.parse_result.get("source_path") or "").strip()
        if not src or not self.source_preview_label: return
        sel = self.source_preview_label.get_selected_rect_on_original()
        if sel is None: self._update_live_preview_table(self.parse_result.get("rows") or []); return
        self._start_area_ocr(src, sel, apply_mode=False)

    def _update_live_preview_table(self, rows):
        if not self.live_preview_table: return
        self.live_preview_table.setRowCount(0); pr = list(rows or [])[:8]
        for r in pr:
            n, s, pp = str(r.get("name") or "").strip(), str(r.get("stock") or "").strip(), str(r.get("purchase_price") or "").strip()
            if not n: continue
            cur = str(r.get("currency") or "TRY").strip(); idx = self.live_preview_table.rowCount(); self.live_preview_table.insertRow(idx)
            for ci, v in enumerate([n, s, pp, str(r.get("price") or ""), str(r.get("line_total") or ""), cur]):
                self.live_preview_table.setItem(idx, ci, QTableWidgetItem(v))

    def _expand_selected_area_horizontally(self, source_path, rect, update_preview=False):
        if not rect: return rect
        try:
            img = Image.open(source_path); img = ImageOps.exif_transpose(img)
            top = max(0, rect.y()); bottom = min(img.height, rect.y() + rect.height())
            exp = QRect(0, top, max(1, img.width), max(1, bottom - top))
            self._last_expanded_selection_rect = QRect(exp); self._last_focus_selection_rect = QRect(rect.intersected(QRect(0,0,img.width,img.height)))
            if update_preview and self.source_preview_label: self.source_preview_label.focus_on_original_rect(self._last_focus_selection_rect)
            return exp
        except Exception: return rect

    def _restore_last_expanded_selection(self):
        r = getattr(self, "_last_focus_selection_rect", None) or getattr(self, "_last_expanded_selection_rect", None)
        if r and self.source_preview_label: QTimer.singleShot(0, lambda: self.source_preview_label.focus_on_original_rect(r))

    def _clear_preview_selection(self):
        self._last_expanded_selection_rect = self._last_focus_selection_rect = None
        if self.source_preview_label: self.source_preview_label.clear_selection()

    def _open_safe_crop_dialog(self, w, h):
        def_r = self._fallback_crop_rect(w, h); dlg = QDialog(self); dlg.setWindowTitle("Guvenli Kirpma"); lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("Sol/Ust/Genislik/Yukseklik ayarla.")); grid = QGridLayout(); lay.addLayout(grid)
        s_l, s_t = QSpinBox(), QSpinBox(); s_w, s_h = QSpinBox(), QSpinBox()
        for s, v, m in [(s_l, def_r.x(), w-1), (s_t, def_r.y(), h-1), (s_w, def_r.width(), w), (s_h, def_r.height(), h)]:
            s.setRange(0, m); s.setValue(v); s.setSingleStep(10)
        grid.addWidget(QLabel("Sol"), 0, 0); grid.addWidget(s_l, 0, 1); grid.addWidget(QLabel("Ust"), 0, 2); grid.addWidget(s_t, 0, 3)
        grid.addWidget(QLabel("Genislik"), 1, 0); grid.addWidget(s_w, 1, 1); grid.addWidget(QLabel("Yukseklik"), 1, 2); grid.addWidget(s_h, 1, 3)
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); box.accepted.connect(dlg.accept); box.rejected.connect(dlg.reject); lay.addWidget(box)
        if dlg.exec() != QDialog.DialogCode.Accepted: return None
        return QRect(s_l.value(), s_t.value(), s_w.value(), s_h.value())

    @staticmethod
    def _fallback_crop_rect(w, h):
        if w<=0 or h<=0: return QRect(0,0,1,1)
        l, t = int(w*0.05), int(h*0.15); return QRect(l, t, int(w*0.95)-l, int(h*0.88)-t)

    @staticmethod
    def _split_brand_from_name(name):
        if not name: return "", name
        nl = name.lower()
        for b in sorted(StockImportParser.BRAND_HINTS, key=len, reverse=True):
            m = re.search(r'(?:^|[\s\-/])(' + re.escape(b) + r')(?:$|[\s\-/])', nl)
            if m:
                pretty = b.strip().upper() if len(b) <= 4 else b.strip().title()
                cl = (name[:m.start(1)] + name[m.end(1):]).strip(" \t\\-/")
                cl = re.sub(r'\s{2,}', ' ', cl).strip()
                return pretty, cl if cl else name
        return "", name

    def _collect_rows(self):
        rows = []
        for r in range(self.table.rowCount()):
            d = {f: (self.table.item(r, ci).text().strip() if self.table.item(r, ci) else "") for ci, (f, _) in enumerate(self.COLUMNS)}
            if d["name"]: rows.append(d)
        return rows

    def _find_existing_import_part(self, name, category, brand="", code=""):
        clean_code = str(code or "").strip()
        if clean_code:
            self.db.cursor.execute(
                """
                SELECT *
                FROM parts
                WHERE LOWER(TRIM(COALESCE(code, ''))) = LOWER(TRIM(?))
                  AND COALESCE(is_deleted, 0) = 0
                ORDER BY id
                LIMIT 1
                """,
                (clean_code,),
            )
        else:
            query = """
                SELECT *
                FROM parts
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                  AND LOWER(TRIM(COALESCE(category, ''))) =
                      LOWER(TRIM(COALESCE(?, '')))
                  AND COALESCE(is_deleted, 0) = 0
            """
            params = [name, category]
            clean_brand = str(brand or "").strip()
            if clean_brand:
                query += (
                    " AND LOWER(TRIM(COALESCE(brand, ''))) = "
                    "LOWER(TRIM(?))"
                )
                params.append(clean_brand)
            query += " ORDER BY id LIMIT 1"
            self.db.cursor.execute(query, tuple(params))
        row = self.db.cursor.fetchone()
        if not row:
            return None
        if hasattr(row, "keys"):
            return dict(row)
        columns = [item[0] for item in self.db.cursor.description]
        return dict(zip(columns, row))

    def _compose_description(self, row):
        base = str(row.get("desc") or "").strip()
        meta = []
        pairs = [
            ("condition", "URUN_DURUMU"),
            ("unit", "URUN_BIRIM"),
            ("supplier", "TEDARIKCI"),
        ]
        if self.is_automotive:
            pairs.extend([
                ("vehicle_brand", "OTO_VEHICLE_BRAND"),
                ("vehicle_model", "OTO_VEHICLE_MODEL"),
                ("position", "OTO_POSITION"),
            ])
        for key, tag in pairs:
            value = str(row.get(key) or "").strip()
            if value:
                meta.append(f"[{tag}] {value}")
        if not meta: return base
        return (f"{base}\n" + "\n".join(meta)) if base else "\n".join(meta)

    def save_rows(self):
        rows = self._collect_rows()
        if not rows:
            show_warning(self, "Kaydedilecek satir yok.")
            return
        if getattr(self, "selection_only", False):
            self.selected_rows = [dict(row) for row in rows]
            self.accept()
            return

        saved_count = 0
        stock_failures = []
        finance_failures = []
        for row_number, source_row in enumerate(rows, start=1):
            try:
                row = dict(source_row)
                name = str(row.get("name") or "").strip()
                if not name:
                    raise ValueError("product name is empty")
                stock = self._to_int(row.get("stock"))
                purchase_price = self._to_float(row.get("purchase_price"))
                sale_price = self._to_float(row.get("price"))
                currency = StockImportParser._normalize_currency(
                    row.get("currency"), f"{row.get('desc', '')} {name}"
                )
                if not purchase_price and sale_price:
                    purchase_price = sale_price
                if not sale_price and purchase_price:
                    sale_price = purchase_price
                if stock <= 0:
                    stock = 1
                category = (
                    str(row.get("category") or "Genel").strip() or "Genel"
                )
                brand = str(row.get("brand") or "").strip()
                code = str(row.get("code") or "").strip()
                description = self._compose_description(row)
                existing = self._find_existing_import_part(
                    name,
                    category,
                    brand=brand,
                    code=code,
                )
                if existing:
                    part_id = self.db.merge_imported_part(
                        part_id=existing["id"],
                        quantity=stock,
                        purchase_price=purchase_price,
                        sale_price=sale_price,
                        currency=currency,
                        name=name,
                        category=category,
                        brand=brand,
                        description=description,
                        code=code,
                        shelf=str(row.get("shelf") or "").strip(),
                        oem_code=str(row.get("oem_code") or "").strip(),
                        equivalent_code=str(
                            row.get("equivalent_code") or ""
                        ).strip(),
                        compatible_models=str(
                            row.get("compatible_models") or ""
                        ).strip(),
                    )
                else:
                    part_id = self.db.add_part(
                        name=name,
                        category=category,
                        stock=stock,
                        price=sale_price,
                        desc=description,
                        min_stock=5,
                        code=code,
                        shelf=str(row.get("shelf") or "").strip(),
                        purchase_price=purchase_price,
                        currency=currency,
                        brand=brand,
                        oem_code=str(row.get("oem_code") or "").strip(),
                        equivalent_code=str(
                            row.get("equivalent_code") or ""
                        ).strip(),
                        compatible_models=str(
                            row.get("compatible_models") or ""
                        ).strip(),
                    )
                if not part_id:
                    detail = str(getattr(self.db, "_last_part_error", "")).strip()
                    raise RuntimeError(detail or "add_part returned no identifier")
            except Exception as exc:
                _LOG.exception("Smart stock import failed for row %s", row_number)
                stock_failures.append(f"{row_number}: {exc}")
                continue

            saved_count += 1
            if purchase_price <= 0:
                continue
            try:
                total_cost = stock * purchase_price
                tx_exchange_rate = None
                if currency != "TRY":
                    from src.utils.currency_helper import CurrencyHelper

                    raw_rate = CurrencyHelper._get_rate(self.db, currency)
                    tx_exchange_rate = (
                        float(raw_rate)
                        if raw_rate and float(raw_rate) > 1.0
                        else (47.5736 if currency == "USD" else (51.50 if currency == "EUR" else 1.0))
                    )
                transaction_id = self.db.add_transaction(
                    t_type="Gider",
                    category="Yedek Parca Alimi" if self.is_automotive else "Stok Alimi",
                    amount=total_cost,
                    description=f"Stok Alimi (Akilli Iceri Aktarim): {stock} x {name}",
                    payment_method="Nakit",
                    currency=currency,
                    original_amount=total_cost,
                    exchange_rate=tx_exchange_rate,
                    selected_services=[{
                        "kind": "stock_purchase",
                        "name": name,
                        "quantity": stock,
                        "unit_price": purchase_price,
                        "currency": currency,
                        "line_total": total_cost,
                    }],
                )
                if transaction_id is None:
                    raise RuntimeError("finance transaction was not created")
            except Exception as exc:
                _LOG.exception("Stock import finance entry failed for row %s", row_number)
                finance_failures.append(f"{row_number}: {exc}")

        if not saved_count:
            detail = stock_failures[0] if stock_failures else ""
            show_error(self, f"Satirlar kaydedilemedi. {detail}".strip())
            return

        message = (
            f"Aktarma tamamlandi. Basarili: {saved_count} | "
            f"Hatali: {len(stock_failures)}"
        )
        if stock_failures:
            message += f"\nIlk stok hatasi: {stock_failures[0]}"
        if finance_failures:
            message += f" | Finans kaydi olusturulamayan: {len(finance_failures)}"
            message += f"\nIlk finans hatasi: {finance_failures[0]}"
            show_warning(self, message)
        elif stock_failures:
            show_warning(self, message)
        else:
            show_success(self, message)
        self._cleanup_pdf_temp()
        self.accept()

    def _cleanup_pdf_temp(self):
        tmp = getattr(self, "_pdf_rendered_temp", None)
        if tmp:
            try: os.remove(tmp)
            except Exception: pass
            self._pdf_rendered_temp = None

    @staticmethod
    def _to_int(v):
        try:
            t = str(v).strip(); 
            if not t: return 0
            t = t.replace(".", "").replace(",", ".") if "," in t and "." in t else t.replace(",", ".")
            return int(float(t))
        except Exception: return 0

    @staticmethod
    def _to_float(v):
        try:
            t = str(v).strip(); 
            if not t: return 0.0
            t = "".join(c for c in t if c.isdigit() or c in ",.-")
            t = t.replace(".", "").replace(",", ".") if "," in t and "." in t else t.replace(",", ".")
            return float(t)
        except Exception: return 0.0
