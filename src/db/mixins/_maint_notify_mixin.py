# -*- coding: utf-8 -*-
from datetime import datetime
from src.utils.logger import logger

class MaintenanceNotifyMixin:
    def ensure_due_vehicle_inspection_notifications(self, target_date=None):
        try:
            target = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("SELECT * FROM vehicle_maintenance_cards WHERE inspection_notice_date=? ORDER BY inspection_due_date ASC, id ASC", (target,))
            rows = self.cursor.fetchall() or []
            for row in rows:
                uk = f"vehicle_inspection:{row['id']}:{target}"
                self.add_notification("Otomotiv", "Muayene Hatirlatmasi", f"{row['customer_name']} - {row['vehicle_plate'] or row['vehicle_brand'] or 'Arac'} için muayene tarihi yaklaşıyor ({row['inspection_due_date'] or '-'}).", link_id=uk, priority="high", unique_key=uk)
            return rows
        except Exception as e:
            logger.error(f"Ensure due vehicle inspection notifications error: {e}"); return []

    def get_due_vehicle_inspection_whatsapp_rows(self, target_date=None):
        try:
            target = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("SELECT * FROM vehicle_maintenance_cards WHERE inspection_notice_date=? AND COALESCE(TRIM(customer_phone), '') != '' AND (inspection_notified_at IS NULL OR substr(inspection_notified_at, 1, 10) != ?) ORDER BY inspection_due_date ASC, id ASC", (target, target))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get due vehicle inspection WhatsApp rows error: {e}"); return []

    def mark_vehicle_inspection_notification_sent(self, card_id, sent_at=None):
        try:
            val = sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("UPDATE vehicle_maintenance_cards SET inspection_notified_at=?, updated_at=? WHERE id=?", (val, val, card_id))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Mark vehicle inspection notification sent error: {e}"); self.conn.rollback(); return False

    def ensure_due_vehicle_maintenance_notifications(self, target_date=None):
        try:
            target = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                "SELECT c.* FROM vehicle_maintenance_cards c "
                "WHERE c.reminder_date=? AND EXISTS ("
                "SELECT 1 FROM vehicle_maintenance_items i WHERE i.card_id=c.id "
                "AND COALESCE(i.performed, 1)=1 AND LOWER(COALESCE(i.item_type, ''))!='glass_water' "
                "AND LOWER(REPLACE(TRIM(COALESCE(i.item_label, '')), ' ', ''))!='camsuyu'"
                ") ORDER BY c.next_maintenance_date ASC, c.id ASC",
                (target,),
            )
            rows = self.cursor.fetchall() or []
            for row in rows:
                uk = f"vehicle_maintenance:{row['id']}:{target}"
                self.add_notification("Otomotiv", "Yarin Bakim Hatirlatmasi", f"{row['customer_name']} - {row['vehicle_plate'] or row['vehicle_brand'] or 'Arac'} için yarın bakım zamanı ({row['next_maintenance_date']}).", link_id=uk, priority="high", unique_key=uk)
            return rows
        except Exception as e:
            logger.error(f"Ensure due maintenance notifications error: {e}"); return []

    def ensure_upcoming_vehicle_maintenance_km_notifications(self, threshold_km=500, target_date=None):
        try:
            today = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("SELECT c.*, i.id AS item_id, i.item_label, i.next_due_odometer, COALESCE(v.last_known_odometer, c.odometer, 0) AS current_odometer FROM vehicle_maintenance_cards c JOIN vehicle_maintenance_items i ON i.card_id = c.id LEFT JOIN customer_vehicles v ON v.id = c.vehicle_id WHERE COALESCE(i.performed, 1)=1 AND LOWER(COALESCE(i.item_type, ''))!='glass_water' AND LOWER(REPLACE(TRIM(COALESCE(i.item_label, '')), ' ', ''))!='camsuyu' AND COALESCE(i.next_due_odometer, 0) > 0 AND (COALESCE(i.next_due_odometer, 0)-COALESCE(v.last_known_odometer, c.odometer, 0)) BETWEEN 0 AND ? ORDER BY (i.next_due_odometer-COALESCE(v.last_known_odometer, c.odometer, 0)) ASC, c.id ASC", (int(threshold_km or 500),))
            rows = self.cursor.fetchall() or []
            for row in rows:
                rem = max(0, int(row["next_due_odometer"] or 0)-int(row["current_odometer"] or 0))
                uk = f"vehicle_maintenance_km:{row['item_id']}:{today}"
                self.add_notification("Otomotiv", "Yaklasan KM Bakimi", f"{row['customer_name']} - {row['vehicle_plate'] or row['vehicle_brand'] or 'Arac'} için {row['item_label']} yaklaşıyor. Yaklaşık {rem} KM kaldı.", link_id=uk, priority="high", unique_key=uk)
            return rows
        except Exception as e:
            logger.error(f"Ensure upcoming maintenance KM notifications error: {e}"); return []

    def get_due_vehicle_maintenance_alerts(self, target_date=None):
        try:
            target = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                "SELECT c.* FROM vehicle_maintenance_cards c "
                "WHERE c.reminder_date=? AND EXISTS ("
                "SELECT 1 FROM vehicle_maintenance_items i WHERE i.card_id=c.id "
                "AND COALESCE(i.performed, 1)=1 AND LOWER(COALESCE(i.item_type, ''))!='glass_water' "
                "AND LOWER(REPLACE(TRIM(COALESCE(i.item_label, '')), ' ', ''))!='camsuyu'"
                ") ORDER BY c.next_maintenance_date ASC, c.id ASC",
                (target,),
            )
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get due maintenance alerts error: {e}"); return []

    def get_due_vehicle_maintenance_whatsapp_rows(self, target_date=None):
        try:
            target = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                "SELECT c.* FROM vehicle_maintenance_cards c "
                "WHERE c.reminder_date=? AND COALESCE(TRIM(c.customer_phone), '')!='' "
                "AND (c.whatsapp_sent_at IS NULL OR substr(c.whatsapp_sent_at, 1, 10)!=?) "
                "AND EXISTS (SELECT 1 FROM vehicle_maintenance_items i WHERE i.card_id=c.id "
                "AND COALESCE(i.performed, 1)=1 AND LOWER(COALESCE(i.item_type, ''))!='glass_water' "
                "AND LOWER(REPLACE(TRIM(COALESCE(i.item_label, '')), ' ', ''))!='camsuyu') "
                "ORDER BY c.next_maintenance_date ASC, c.id ASC",
                (target, target),
            )
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get due maintenance WhatsApp rows error: {e}"); return []

    def get_upcoming_vehicle_maintenance_km_whatsapp_rows(self, threshold_km=500, target_date=None):
        try:
            today = target_date or datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("SELECT c.*, i.id AS item_id, i.item_label, i.next_due_odometer, COALESCE(v.last_known_odometer, c.odometer, 0) AS current_odometer FROM vehicle_maintenance_cards c JOIN vehicle_maintenance_items i ON i.card_id = c.id LEFT JOIN customer_vehicles v ON v.id = c.vehicle_id WHERE COALESCE(i.performed, 1)=1 AND LOWER(COALESCE(i.item_type, ''))!='glass_water' AND LOWER(REPLACE(TRIM(COALESCE(i.item_label, '')), ' ', ''))!='camsuyu' AND COALESCE(i.next_due_odometer, 0) > 0 AND (COALESCE(i.next_due_odometer, 0)-COALESCE(v.last_known_odometer, c.odometer, 0)) BETWEEN 0 AND ? AND COALESCE(TRIM(c.customer_phone), '') != '' AND (i.km_whatsapp_sent_at IS NULL OR substr(i.km_whatsapp_sent_at, 1, 10) != ?) ORDER BY (i.next_due_odometer-COALESCE(v.last_known_odometer, c.odometer, 0)) ASC, c.id ASC", (int(threshold_km or 500), today))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get upcoming maintenance KM WhatsApp rows error: {e}"); return []

    def mark_vehicle_maintenance_whatsapp_sent(self, card_id, sent_at=None):
        try:
            val = sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("UPDATE vehicle_maintenance_cards SET whatsapp_sent_at=?, updated_at=? WHERE id=?", (val, val, card_id))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Mark maintenance WhatsApp sent error: {e}"); self.conn.rollback(); return False

    def mark_vehicle_maintenance_item_km_whatsapp_sent(self, item_id, sent_at=None):
        try:
            val = sent_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("UPDATE vehicle_maintenance_items SET km_whatsapp_sent_at=? WHERE id=?", (val, item_id))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Mark maintenance KM WhatsApp sent error: {e}"); self.conn.rollback(); return False
