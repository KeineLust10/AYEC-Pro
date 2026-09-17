# -*- coding: utf-8 -*-

"""
Reports Mixin
Database helpers for reporting and dashboard statistics.
"""

from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.status_utils import normalize_device_status


class ReportsMixin:
    """Database methods for reports and summary widgets."""

    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value

    @staticmethod
    def _date_prefix(value):
        return f"{value}%"

    def get_stats(self):
        """Return active customer/device/stock counts."""
        self.cursor.execute(
            "SELECT COUNT(*) FROM customers WHERE COALESCE(is_deleted, 0) = 0"
        )
        total_customers = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM devices WHERE COALESCE(is_deleted, 0) = 0"
        )
        total_devices = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM parts WHERE COALESCE(is_deleted, 0) = 0"
        )
        total_parts = self.cursor.fetchone()[0]

        return {
            "customers": total_customers,
            "devices": total_devices,
            "parts": total_parts,
        }

    def get_summary_data(self):
        """Return aggregate values for dashboard summary cards."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            date_like = self._date_prefix(today)

            # Tüm aktif kayıtların durumlarını çek
            self.cursor.execute(
                "SELECT status FROM devices WHERE COALESCE(is_deleted, 0) = 0"
            )
            status_rows = self.cursor.fetchall() or []

            # Normalize ederek sınıflandır
            waiting_count = 0
            active_count = 0
            done_total = 0
            for row in status_rows:
                norm = normalize_device_status(row[0] if row else None)
                if norm == "Bekliyor":
                    waiting_count += 1
                elif norm in ("Tamirde", "Parça Bekliyor", "Test Sürecinde"):
                    active_count += 1
                elif norm == "Teslim Edildi":
                    done_total += 1

            # Bugün teslim edilenler (exit_date veya delivered_at veya updated_at)
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM devices
                WHERE COALESCE(is_deleted, 0) = 0
                  AND COALESCE(exit_date, delivered_at, updated_at, '') LIKE ?
                  AND status IN ('Teslim Edildi','Teslim','Hazır','Hazir','Tamamlandı','Tamamlandi','Bitti','Tamir Edildi')
                """,
                (date_like,),
            )
            delivered_today = self.cursor.fetchone()[0] or 0

            # Bugün kayıt alınan
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM devices
                WHERE COALESCE(is_deleted, 0) = 0
                  AND COALESCE(entry_date, created_at, '') LIKE ?
                """,
                (date_like,),
            )
            today_jobs = self.cursor.fetchone()[0] or 0

            # Kritik stok sayısı
            critical_stock_count = 0
            try:
                self.cursor.execute(
                    """
                    SELECT COUNT(*) FROM parts
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND CAST(COALESCE(quantity, 0) AS INTEGER) <= CAST(COALESCE(min_quantity, 0) AS INTEGER)
                      AND CAST(COALESCE(min_quantity, 0) AS INTEGER) > 0
                    """
                )
                critical_stock_count = self.cursor.fetchone()[0] or 0
            except Exception:
                pass

            # Toplam gelir (tamamlananlar)
            self.cursor.execute(
                """
                SELECT SUM(COALESCE(price, 0))
                FROM devices
                WHERE COALESCE(is_deleted, 0) = 0
                  AND status IN ('Teslim Edildi','Teslim','Hazır','Hazir','Tamamlandı','Tamamlandi','Bitti','Tamir Edildi')
                """
            )
            total_revenue = self.cursor.fetchone()[0] or 0

            return {
                # Dashboard insight kartları için
                "waiting_count": waiting_count,
                "active_count": active_count,
                "delivered_today": delivered_today,
                "pending_count": waiting_count,     # perf kartı uyumu
                "critical_stock_count": critical_stock_count,
                # Geriye dönük uyumluluk
                "today_jobs": today_jobs,
                "completed_jobs": done_total,
                "pending_jobs": waiting_count,
                "total_revenue": total_revenue,
            }
        except Exception as e:
            logger.error(f"Summary data error: {e}")
            return {}

    def get_weekly_stats(self):
        """Return service counts for the last 7 days."""
        try:
            stats = []
            for i in range(7):
                date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                self.cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM devices
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND COALESCE(entry_date, created_at, '') LIKE ?
                    """,
                    (self._date_prefix(date),),
                )
                count = self.cursor.fetchone()[0]
                stats.append({"date": date, "count": count})
            return stats
        except Exception as e:
            logger.error(f"Weekly stats error: {e}")
            return []

    def export_to_csv(self, table_name, file_path):
        """Export a table to CSV without requiring pandas."""
        try:
            import csv

            safe_table = self._safe_identifier(table_name)
            self.cursor.execute(
                "SELECT * FROM {table_name}".format(table_name=safe_table)
            )
            rows = self.cursor.fetchall()

            self.cursor.execute(
                "PRAGMA table_info({table_name})".format(table_name=safe_table)
            )
            headers = [col[1] for col in self.cursor.fetchall()]

            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(headers)
                writer.writerows(rows)

            logger.info(f"CSV export completed: {file_path}")
            return True
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            return False

    def get_sectoral_widget_data(self, sector="teknik_servis"):
        """Return dashboard widget values for a sector."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            date_like = self._date_prefix(today)
            data = {}

            if sector in ("teknik_servis", "otomotiv"):
                self.cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM devices
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND status='Teslim Edildi'
                      AND COALESCE(exit_date, '') LIKE ?
                    """,
                    (date_like,),
                )
                data["delivered_today"] = self.cursor.fetchone()[0]

                self.cursor.execute(
                    """
                    SELECT status
                    FROM devices
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND status NOT IN ('Teslim Edildi', 'İptal', 'İptal Edildi', 'İade Edildi')
                    """
                )
                status_rows = self.cursor.fetchall() or []
                data["pending_repair"] = sum(
                    1
                    for row in status_rows
                    if normalize_device_status(row[0] if row else None) == "Bekliyor"
                )

                self.cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM parts
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND COALESCE(stock, 0) <= COALESCE(min_stock, 0)
                    """
                )
                data["critical_stock"] = self.cursor.fetchone()[0]

                self.cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM devices
                    WHERE COALESCE(is_deleted, 0) = 0
                      AND COALESCE(entry_date, created_at, '') LIKE ?
                    """,
                    (date_like,),
                )
                data["new_entries_today"] = self.cursor.fetchone()[0]

                if sector == "otomotiv":
                    self.cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM vehicle_maintenance_cards
                        WHERE next_maintenance_date = ?
                        """,
                        (today,),
                    )
                    data["delivered_today"] = self.cursor.fetchone()[0]
                    self.cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM vehicle_maintenance_cards
                        WHERE next_maintenance_date >= ?
                        """,
                        (today,),
                    )
                    data["pending_repair"] = self.cursor.fetchone()[0]

            return data
        except Exception as e:
            logger.error(f"Sectoral widget data error: {e}")
            return {}
