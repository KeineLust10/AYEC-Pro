# -*- coding: utf-8 -*-
# _tp_automotive.py

from datetime import datetime
from src.utils.logger import logger
from src.utils.toast_notification import show_success, show_error, show_warning

class _TpAutomotive:
    def _get_automotive_checklist_data(self):
        """Otomotiv kontrol formu verilerini al"""
        try:
            return self.automotive_service_form.get("checklist_data", {})
        except Exception:
            return {}

    def _get_automotive_damage_data(self):
        """Otomotiv hasar işaretleme verilerini al"""
        try:
            return self.automotive_service_form.get("damage_data", {})
        except Exception:
            return {}

    def _upsert_automotive_service_form_from_panel(self):
        if not self._is_automotive():
            return
        
        # UI'dan verileri topla
        form_data = {
            "tracking_no": self.tracking_no,
            "engine_code": getattr(self, "txt_engine_code", None).text().strip() if hasattr(self, "txt_engine_code") else "",
            "exit_odometer": getattr(self, "inp_exit_odometer", None).text().strip() if hasattr(self, "inp_exit_odometer") else "",
            "fuel_level_exit": getattr(self, "cmb_fuel_level_exit", None).currentText().strip() if hasattr(self, "cmb_fuel_level_exit") else "",
            "customer_approval": 1 if (hasattr(self, "chk_customer_approval_done") and self.chk_customer_approval_done.isChecked()) else 0,
            "kvkk_approval": 1 if (hasattr(self, "chk_kvkk_done") and self.chk_kvkk_done.isChecked()) else 0,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            # Mevcut kayıt var mı kontrol et
            exists = self.db.cursor.execute(
                "SELECT 1 FROM automotive_service_forms WHERE tracking_no=?", (self.tracking_no,)
            ).fetchone()
            
            if exists:
                self.db.cursor.execute("""
                    UPDATE automotive_service_forms 
                    SET engine_code=?, exit_odometer=?, fuel_level_exit=?, 
                        customer_approval=?, kvkk_approval=?, updated_at=?
                    WHERE tracking_no=?
                """, (
                    form_data["engine_code"], form_data["exit_odometer"], form_data["fuel_level_exit"],
                    form_data["customer_approval"], form_data["kvkk_approval"], form_data["updated_at"],
                    self.tracking_no
                ))
            else:
                self.db.cursor.execute("""
                    INSERT INTO automotive_service_forms (
                        tracking_no, engine_code, exit_odometer, fuel_level_exit,
                        customer_approval, kvkk_approval, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.tracking_no, form_data["engine_code"], form_data["exit_odometer"], form_data["fuel_level_exit"],
                    form_data["customer_approval"], form_data["kvkk_approval"], form_data["updated_at"], form_data["updated_at"]
                ))
            self.db.conn.commit()
            
            # Local cache güncelle
            self.automotive_service_form.update(form_data)
            
        except Exception as e:
            logger.error(f"Automotive service form upsert error: {e}")

    def _update_automotive_panel_summary(self):
        if not self._is_automotive() or not hasattr(self, "lbl_automotive_panel_summary"):
            return
        
        customer_approval = "ONAY Alındı" if (hasattr(self, "chk_customer_approval_done") and self.chk_customer_approval_done.isChecked()) else "Onay Bekliyor"
        kvkk = "KVKK Tamam" if (hasattr(self, "chk_kvkk_done") and self.chk_kvkk_done.isChecked()) else "KVKK Onayı Eksik"
        
        exit_km = getattr(self, "inp_exit_odometer", None).text().strip() if hasattr(self, "inp_exit_odometer") else "-"
        if not exit_km:
            exit_km = "-"
        
        fuel = getattr(self, "cmb_fuel_level_exit", None).currentText() if hasattr(self, "cmb_fuel_level_exit") else "-"
        
        summary = (
            f"🚗 ARAÇ ÖZETİ: {customer_approval} • {kvkk}\n"
            f"📍 ÇIKIŞ KM: {exit_km}  |  ⛽ YAKIT: {fuel}"
        )
        self.lbl_automotive_panel_summary.setText(summary)

    def _open_automotive_checklist_dialog(self):
        from src.ui.dialogs.automotive_checklist_dialog import AutomotiveChecklistDialog
        
        # Mevcut verileri al
        current_data = self._get_automotive_checklist_data() or {}
        templates = {}
        try:
            plugin = self.sector_manager.get_current_plugin()
            if plugin and hasattr(plugin, "get_checklist_templates"):
                templates = plugin.get_checklist_templates() or {}
        except Exception as exc:
            logger.warning(f"Automotive checklist templates unavailable: {exc}")

        dlg = AutomotiveChecklistDialog(
            templates,
            existing_data=current_data,
            parent=self,
        )
        if dlg.exec():
            new_data = dlg.result_data
            # Veritabanına kaydet
            try:
                import json
                self.db.cursor.execute(
                    "UPDATE automotive_service_forms SET checklist_data=?, updated_at=? WHERE tracking_no=?",
                    (json.dumps(new_data), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.tracking_no)
                )
                self.db.conn.commit()
                self.automotive_service_form["checklist_data"] = new_data
                show_success(self, "Kontrol listesi kaydedildi.")
            except Exception as e:
                show_error(self, f"Hata: {e}")

    def _open_automotive_damage_dialog(self):
        from src.ui.dialogs.automotive_damage_dialog import AutomotiveDamageDialog
        
        # Mevcut verileri al
        current_data = self._get_automotive_damage_data() or {}

        dlg = AutomotiveDamageDialog(existing_data=current_data, parent=self)
        if dlg.exec():
            new_data = dlg.result_data
            try:
                import json
                self.db.cursor.execute(
                    "UPDATE automotive_service_forms SET damage_data=?, updated_at=? WHERE tracking_no=?",
                    (json.dumps(new_data), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.tracking_no)
                )
                self.db.conn.commit()
                self.automotive_service_form["damage_data"] = new_data
                show_success(self, "Hasar bilgileri kaydedildi.")
            except Exception as e:
                show_error(self, f"Hata: {e}")

    def _open_vehicle_history_qr(self):
        from src.ui.dialogs.vehicle_history_qr_dialog import VehicleHistoryQrDialog

        plate = str(self.device_dict.get("vehicle_plate", "") or "").strip().upper()
        if not plate:
            show_warning(self, "Bu servis kaydına bağlı plaka bulunamadı.")
            return
        dlg = VehicleHistoryQrDialog(self.db, plate, self)
        dlg.exec()

    def _mark_invoice_ready(self):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.db.cursor.execute(
                "UPDATE devices SET invoice_ready_at=?, updated_at=? WHERE tracking_no=?",
                (now_str, now_str, self.tracking_no),
            )
            self.db.conn.commit()
            self.device_dict["invoice_ready_at"] = now_str
            show_success(self, "Servis kaydı belge hazırlığı için işaretlendi.")
        except Exception as e:
            show_error(self, f"Belge hazırlık işareti kaydedilemedi: {e}")
