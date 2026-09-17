# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import QTableWidgetItem, QMenu, QFileDialog
from PyQt6.QtCore import Qt, QDate
from datetime import datetime
import csv
import webbrowser
from collections import Counter
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import show_success, show_error
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
from src.ui.dialogs.partner_shipment_dialog import PartnerShipmentDialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.dialogs.partner_documents_dialog import PartnerDocumentsDialog
from src.ui.dialogs.partner_profile_dialog import PartnerProfileDialog
from src.ui.dialogs.partner_finance_dialog import PartnerFinanceDialog
from src.utils.context_menu_settings import is_context_menu_enabled

class PartnersPageLogicMixin:
    def _is_partner_row(self, row):
        try:
            if "is_partner" in row.keys() and int(row["is_partner"] or 0) == 1: return True
        except Exception: pass
        row_type = str(row.get("type") or "").strip().casefold()
        return row_type in {"bayi", "tedarikçi", "tedarikci"}

    def _partner_badge(self, partner):
        name = str(partner.get("name") or "").strip()
        initials = "".join(part[0].upper() for part in name.split()[:2] if part)
        return initials or "PT"

    def rebuild_service_type_filter(self):
        values = set()
        for row in self.all_partners:
            v = str(row.get("service_type") or "").strip()
            if v: values.add(v)
        self.cmb_service_type.blockSignals(True)
        self.cmb_service_type.clear(); self.cmb_service_type.addItems(["Tumu"] + sorted(values))
        self.cmb_service_type.blockSignals(False)

    def on_service_type_changed(self, _index):
        txt = self.cmb_service_type.currentText().strip()
        self.current_service_type = None if not txt or txt == "Tumu" else txt
        self.apply_filters()

    def on_commission_filter_changed(self, _index):
        txt = self.cmb_commission.currentText().strip()
        if txt == "Komisyonlu": self.current_commission_filter = "HAS"
        elif txt == "Komisyonsuz": self.current_commission_filter = "NONE"
        else: self.current_commission_filter = None
        self.apply_filters()

    def apply_filters(self):
        search = self.inp_search.text().strip().lower()
        rows = []
        for row in self.all_partners:
            name = str(row.get("name") or ""); phone = str(row.get("phone") or "")
            email = str(row.get("email") or ""); city = str(row.get("city") or "")
            stype = str(row.get("service_type") or "")
            blob = " ".join([name, phone, email, city, stype]).lower()
            if search and search not in blob: continue
            if self.current_service_type and stype != self.current_service_type: continue
            try: comm = float(row.get("commission_rate") or 0)
            except Exception: comm = 0.0
            if self.current_commission_filter == "HAS" and comm <= 0: continue
            if self.current_commission_filter == "NONE" and comm > 0: continue
            rows.append(row)
        self.filtered_partners = rows; self.populate_partner_list()

    def populate_partner_list(self):
        selected_id = self.selected_partner.get("id") if self.selected_partner else None
        self.partner_list.blockSignals(True); self.partner_list.clear()
        for p in self.filtered_partners:
            stype = str(p.get("service_type") or "Genel"); city = str(p.get("city") or "Sehir yok")
            label = "{badge} {name}\n{service}  |  {city}".format(badge=self._partner_badge(p), name=str(p.get("name") or "Adsiz Partner"), service=stype, city=city)
            item = QTableWidgetItem(label) # Aslında QListWidgetItem ama PartnersPage QListWidget kullanıyor.
            # Düzeltme: QListWidgetItem olmalı
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(label); item.setData(Qt.ItemDataRole.UserRole, int(p["id"]))
            self.partner_list.addItem(item)
        self.partner_list.blockSignals(False)
        has = len(self.filtered_partners) > 0
        self.partner_list.setVisible(has); self.partner_list_empty.setVisible(not has)
        self.lbl_total.setText(f"Toplam partner: {len(self.filtered_partners)}")
        if self.filtered_partners:
            target = 0
            if selected_id is not None:
                for i in range(self.partner_list.count()):
                    if self.partner_list.item(i).data(Qt.ItemDataRole.UserRole) == selected_id:
                        target = i; break
            self.partner_list.setCurrentRow(target)
        else: self.selected_partner = None; self.render_partner_details()

    def _partner_scorecard(self, partner, tracks):
        sla = self._sla_hours(partner); turnaround = []; on_time = 0; completed = 0; serials = []; issues = 0
        self.db.cursor.execute("SELECT COALESCE(serial_no, ''), COALESCE(sent_at, ''), COALESCE(returned_at, ''), COALESCE(return_qc, ''), COALESCE(missing_parts, '') FROM partner_shipments WHERE partner_id = ?", (int(partner["id"]),))
        for sn, sent, ret, qc, mp in (self.db.cursor.fetchall() or []):
            if sn: serials.append(sn)
            if mp and str(mp).strip().casefold() not in {"", "yok", "-"}: issues += 1
            if qc and str(qc).strip().casefold() not in {"gecti", "basarili", "tamam"}: issues += 1
            try:
                if sent and ret:
                    s_dt = datetime.strptime(sent, "%Y-%m-%d"); r_dt = datetime.strptime(ret, "%Y-%m-%d")
                    hrs = max((r_dt - s_dt).total_seconds() / 3600.0, 0)
                    turnaround.append(hrs); completed += 1
                    if hrs <= sla: on_time += 1
            except Exception: continue
        avg = round(sum(turnaround)/len(turnaround), 1) if turnaround else 0.0
        rep = sum(1 for c in Counter(serials).values() if c > 1)
        otr = round((on_time/completed)*100, 1) if completed else 0.0
        act = len([r for r in tracks if not self._is_completed_status(r["status"])])
        cbr = round((rep/len(serials))*100, 1) if serials else 0.0
        return {"avg_turnaround": avg, "on_time_rate": otr, "repeat_serials": rep, "quality_issues": issues, "active_count": act, "comeback_ratio": cbr}

    def _sla_hours(self, partner):
        try:
            raw = str(partner.get("sla_level") or ""); digits = "".join(ch for ch in raw if ch.isdigit())
            return int(digits) if digits else 24
        except Exception: return 24

    def _is_completed_status(self, status):
        return str(status or "").strip().casefold() in {"geri geldi", "musteriye teslim edildi", "tamamlandi", "teslim edildi"}

    def add_partner_tracking(self):
        if not self.selected_partner: return
        try:
            if PartnerShipmentDialog(self.db, self.selected_partner, self.window() or self).exec(): self.render_partner_details()
        except Exception as e: logger.error("Partner tracking error: %s", e); show_error(self, f"Gonderi kaydi hatasi: {e}")

    def edit_selected_partner(self):
        if self.selected_partner and PartnerProfileDialog(self.db, self, self.selected_partner).exec(): self.load_data()

    def open_selected_partner_menu(self):
        if self.selected_partner: self.open_partner_menu(self.selected_partner, self.btn_more)

    def open_selected_partner_notes(self):
        if self.selected_partner: CustomerNotesDialog(self.db, self.selected_partner["id"], self.selected_partner["name"], self).exec()

    def open_selected_partner_finance(self):
        if self.selected_partner:
            try: PartnerFinanceDialog(self.db, self.selected_partner, self.window() or self).exec(); self.load_data()
            except Exception as e: logger.error("Finance error: %s", e); show_error(self, f"Finans hatasi: {e}")

    def open_selected_partner_documents(self):
        if self.selected_partner: PartnerDocumentsDialog(self.db, self.selected_partner, self.window() or self).exec(); self.render_partner_details()

    def open_unified_documents_center(self):
        if self.selected_partner: UnifiedDocumentsCenterDialog(self.db, self.selected_partner, self.window() or self).exec(); self.render_partner_details()

    def export_partner_shipments_csv(self):
        if not self.selected_partner: return
        path, _ = QFileDialog.getSaveFileName(self, "Excel Disa Aktar", "partner_sevkleri.xlsx", "Excel (*.xlsx)")
        if not path: return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f); w.writerow(["Emanet No", "Musteri", "Urun", "Tarih", "Durum", "Gidis", "Donus", "Servis No"])
                for t in self._partner_trackings(self.selected_partner):
                    w.writerow([t["internal_no"], t["customer"], t["product"], t["date"], t["status"], t["out_cargo"], t["in_cargo"], t["service_no"]])
            show_success(self, "Basariyla disa aktarildi.")
        except Exception as e: show_error(self, f"Hata: {e}")
    
    def add_partner(self):
        if PartnerProfileDialog(self.db, self).exec(): self.load_data()
    
    def send_whatsapp_for_partner(self, c):
        phone = "".join(filter(str.isdigit, str(c.get("phone") or "")))
        if phone:
            if phone.startswith("0"): phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def _show_partner_tracking_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=21): return
        table = self.sender()
        if not table or not self.selected_partner: return
        row = table.rowAt(pos.y())
        if row < 0: return
        table.selectRow(row); shipment_id = table.item(row,0).data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("Ac / Duzenle", lambda: self.open_selected_tracking(row, 0))
        menu.addAction("Belgeler", lambda: PartnerDocumentsDialog(self.db, self.selected_partner, self.window() or self, shipment_id=shipment_id).exec())
        menu.addAction("Belge Merkezi", self.open_unified_documents_center)
        menu.addAction("Partner Finans", self.open_selected_partner_finance); menu.addSeparator()
        menu.addAction("Excel Disa Aktar", self.export_partner_shipments_csv)
        menu.exec(table.viewport().mapToGlobal(pos))
    
    def _normalize_tracking(self, row):
        return {
            "id": row[0], "internal_no": row[1] or "", "customer": row[2] or "", "product": row[3] or "",
            "service": row[4] or "", "service_no": row[5] or "", "date": row[6] or "",
            "out_cargo": row[7] or "", "in_cargo": row[8] or "", "status": row[9] or "", "notes": row[10] or ""
        }
