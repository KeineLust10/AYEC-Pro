# -*- coding: utf-8 -*-

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.path_helper import PathHelper
from src.utils.role_utils import is_admin_role, normalize_role


class DatabaseLegacyPart5Mixin:
    def load_ato_2025_services(self):
        """ATO 2025 Resmi Fiyat Listesini yükle (eğer boşsa)"""
        self.create_services_table()
        
        # Önce mevcut hizmet sayısını kontrol et
        self.cursor.execute("SELECT COUNT(*) FROM services")
        # count kontrolü kaldırıldı, her zaman eksikleri tamamla

        
        # ATO 2025 Resmi Fiyat Listesi (PDF'ten aktarıldı)
        ATO_2025_SERVICES = [
            ("MONİTÖR TAMİRİ", 1330.0, "Monitör Tamiri (Parça Hariç)"),
            ("UPS TAMİRİ 0-2000VA", 1330.0, "0-2000VA Arası Güç Kaynakları Tamiri (Parça Hariç)"),
            ("UPS TAMİRİ 2000VA+", 1330.0, "2000VA'den yukarı güçteki Kesintisiz Güç Kaynakları Tamiri (Parça Hariç)"),
            ("DOT-MATRIX YAZICI Tamir/Bakım", 1161.0, "Nokta vuruşlu yazıcı mekanik tamir bakım ve temizlik hizmeti"),
            ("INKJET YAZICI Tamir/Bakım", 846.0, "Inkjet yazıcı mekanik tamir bakım ve temizlik hizmeti"),
            ("LASER YAZICI Tamir/Bakım", 1016.0, "Laser yazıcı mekanik tamir bakım ve temizlik hizmeti"),
            ("KURULUM", 1209.0, "Yeni alınmış bilgisayar kurulumu ve sürücü yüklemesi"),
            ("MODEM KURULUM", 725.0, "ADSL/VDSL/Fiber Modem Kurulumu (Kablo Hariç)"),
            ("EĞİTİM (İç Kaynak)", 2177.0, "1 Saat'lik bilgisayar ve donanım eğitimi (Buradan alınan ürün)"),
            ("EĞİTİM (Dış Kaynak)", 2177.0, "1 Saat'lik bilgisayar ve donanım eğitimi (Dışarıdan alınan ürün)"),
            ("DONANIM YÜKSELTME (İç)", 919.0, "Disk, RAM, Kart vb. montajı (Buradan alınan ürün)"),
            ("DONANIM YÜKSELTME (Dış)", 919.0, "Disk, RAM, Kart vb. montajı (Dışarıdan alınan ürün)"),
            ("DİSK BİLGİLERİNİN YENİLENMESİ", 1209.0, "Eski diskten ham veri aktarımı"),
            ("İŞLETİM SİSTEMİ YÜKLEME", 1209.0, "Format, Windows yükleme ve sürücü tanıtımı"),
            ("YAZILIM YÜKLEME", 1088.0, "Ticari ve diğer yazılımların kurulumu"),
            ("YAZILIM DESTEK (Saatlik)", 1209.0, "Yazılım destek hizmeti (1 Saat)"),
            ("YAZILIM FORM DİZAYNI", 919.0, "Form dizayn hizmeti (Adet)"),
            ("İSTEMCİ KURULUMU", 1209.0, "İstemcinin sunucuya bağlanması"),
            ("E-POSTA SUNUCU KURULUMU", 12096.0, "E-posta sunucusu kurulum ve yapılandırma"),
            ("VERİ TABANI SUNUCU KURULUMU", 12096.0, "Veritabanı sunucusu kurulum ve yapılandırma"),
            ("GÜVENLİK DUVARI KURULUMU", 12096.0, "İstemci güvenlik duvarı yapılandırması"),
            ("GÜVENLİK DUVARI SUNUCUSU", 12096.0, "Firewall Server kurulumu"),
            ("VEKİL SUNUCU (PROXY) KURULUMU", 12096.0, "Proxy sunucu kurulumu"),
            ("ADRESE TESLİM (0-30 KM)", 1209.0, "Yerinde servis (0-30 Km)"),
            ("ADRESE TESLİM (30-50 KM)", 1451.0, "Yerinde servis (30-50 Km)"),
            ("ADRESE TESLİM (50-90 KM)", 1838.0, "Yerinde servis (50-90 Km)"),
            ("ADRESE TESLİM (90-140 KM)", 2419.0, "Yerinde servis (90-140 Km)"),
            ("ARIZA TESPİT", 725.0, "Arıza tespit bedeli (Tamir edilmezse alınır)"),
            ("BİLGİ KURTARMA (Donanım)", 2419.0, "Elektronik devre değişimi ile kurtarma"),
            ("BİLGİ KURTARMA (Yazılım)", 4838.0, "Yazılımsal veri kurtarma"),
            ("BİLGİ KURTARMA (Forensic)", 4838.0, "Profesyonel veri kurtarma (GB Başı)"),
            ("İnternet Cafe - En Az", 24.0, "En az kullanım ücreti"),
            ("İnternet Cafe - Saatlik", 38.0, "Saat başı kullanım"),
            ("Siyah Çıktı", 9.0, "A4 Siyah baskı"),
            ("Renkli Çıktı", 19.0, "A4 Renkli baskı"),
            ("1 Sayfa Çıktı", 9.0, "Tek sayfa çıktı alma"),
            ("Belge Tarama", 19.0, "Scanner tarama ücreti"),
            ("Sorgulama (Belgesiz)", 24.0, "İnternet bilgi sorgulama"),
            ("Ehliyet Sonuç Sorgulama", 33.0, "Ehliyet sonucu"),
            ("Sınav Sonuç Sorgulama", 9.0, "ÖSYM/MEB sonuç"),
            ("Vergi No Sorgulama", 33.0, "Vergi numarası sorgulama"),
            ("TC No Sorgulama", 24.0, "TC Kimlik No sorgulama"),
            ("CD/Dosya Kopyalama", 48.0, "Medya kopyalama ücreti"),
            ("Faks (Şehir İçi/Dışı)", 33.0, "Faks gönderim ücreti"),
            ("Faks (Yurt Dışı)", 145.0, "Yurt dışı faks gönderimi")
        ]
        
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for name, price, desc in ATO_2025_SERVICES:
            try:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO services (name, price, description, created_at) VALUES (?, ?, ?, ?)",
                    (name, price, desc, created_at)
                )
            except Exception as e:
                logger.error(f"Service insert error for {name}: {e}")
        
        self.conn.commit()
        pass


    def delete_personnel(self, p_id):
        self.soft_delete_record("personnel", "id", p_id)


    def update_personnel(self, p_id, name, role, phone, salary):
        self.cursor.execute("""
            UPDATE personnel SET name=?, role=?, phone=?, salary=? WHERE id=?
        """, (name, role, phone, salary, p_id))
        self.conn.commit()
    


    def delete_transaction(self, t_id):
        try:
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [r[1] for r in self.cursor.fetchall()]
            self.cursor.execute("SELECT * FROM accounting WHERE id=? AND COALESCE(is_deleted, 0) = 0", (t_id,))
            old_txn = self.cursor.fetchone()
            if old_txn:
                old_dict = {cols[i]: old_txn[i] for i in range(len(cols))}
                old_bank_id = old_dict.get('bank_account_id')
                old_amount = float(old_dict.get('amount') or 0.0)
                old_type = old_dict.get('type')
                
                if old_bank_id:
                    old_delta = -old_amount if str(old_type).lower() == "gelir" else old_amount
                    try:
                        self.update_bank_balance(old_bank_id, old_delta)
                    except Exception as e:
                        logger.warning(f"Failed to revert old bank balance for deleted transaction: {e}")
        except Exception as e:
            logger.error(f"Delete transaction revert error: {e}")
            
        self.soft_delete_record("accounting", "id", t_id)


    def add_appointment(self, title, customer, date, time, status="Bekliyor"):
        try:
            self.cursor.execute("""
                INSERT INTO appointments (title, customer, date, time, status)
                VALUES (?, ?, ?, ?, ?)
            """, (title, customer, date, time, status))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment error: {e}")
            return False


    def check_permission(self, role, action):
        """Rol bazlı yetki kontrolü (Kurumsal Güvenlik)"""
        # Admin her şeyi yapabilir
        if is_admin_role(role):
            return True
        
        permissions = {
            "Teknisyen": ["view_dashboard", "add_service", "update_status", "view_stock"],
            "Muhasebe": ["view_dashboard", "view_accounting", "add_transaction", "export_excel"],
            "Stajyer": ["view_dashboard", "view_stock"]
        }
        
        allowed_actions = permissions.get(normalize_role(role), [])
        return action in allowed_actions


    def trigger_status_notification(self, tracking_no, status):
        """Durum değiştiğinde otomatik bildirim (SMS/WhatsApp)"""
        # Gelecekte bir API (Twilio, Netgsm vb.) buraya bağlanacak
        # Şimdilik log alıp, WhatsApp şablonunu hazırlıyor gibi yapalım
        self.add_audit_log("Sistem", "notifications", "AUTO_SEND", f"Cihaz #{tracking_no} için '{status}' bildirimi tetiklendi.")
        logger.info(f"NOTIFY: Cihaz #{tracking_no} durumu '{status}' oldu. Müşteriye bilgi iletiliyor...")


    def get_appointments(self):
        query = "SELECT * FROM appointments"
        try:
            cols = self._get_table_columns("appointments")
            deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
            if deleted_col:
                query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
        except Exception as e:
            logger.debug(f"Appointments schema inspection skipped: {e}")
        query += " ORDER BY date, time"
        try:
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Appointments fetch error: {e}")
            return []
    
    

    def create_stock_tables(self):
        try:
            # Parts tablosunu güncelle (min_stock kolonu yoksa ekle - SQLite alter table if not exists tricky, so we ignore error)
            try:
                self.cursor.execute(
                    "ALTER TABLE parts ADD COLUMN {column_name} INTEGER DEFAULT 5".format(
                        column_name=self._safe_identifier("min_stock")
                    )
                )
            except Exception as e:
                logger.debug(f"min_stock column already exists or table parts missing: {e}")
            try:
                self.cursor.execute(
                    "ALTER TABLE parts ADD COLUMN {column_name} TEXT".format(
                        column_name=self._safe_identifier("photo_path")
                    )
                )
            except Exception as e:
                logger.debug(f"photo_path column already exists or table parts missing: {e}")
            
            # Hareket tablosu - StockMixin ile uyumlu schema
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_id INTEGER,
                    movement_type TEXT,
                    amount REAL DEFAULT 0,
                    new_stock REAL DEFAULT 0,
                    description TEXT,
                    created_at TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT
                )
            """)
            
            # Kullanılan parçalar tablosu (Eksik tablo hatasını önlemek için)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS used_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_no TEXT,
                    part_id INTEGER,
                    part_name TEXT,
                    price REAL,
                    quantity INTEGER DEFAULT 1,
                    purchase_price_snapshot REAL DEFAULT 0,
                    currency TEXT DEFAULT 'TRY',
                    exchange_rate REAL DEFAULT 1,
                    price_try REAL DEFAULT 0,
                    created_at TEXT
                )
            """)
            self.conn.commit()
            self.update_used_parts_schema()
        except Exception as e:
            logger.error(f"Stock table error: {e}")


    def update_used_parts_schema(self):
        """used_parts tablosuna eksik kolonları ekler ve kısıtlamaları (Foreign Key) kaldırır."""
        try:
            # 1. Check for legacy Foreign Key constraints that block direct sales/services
            self.cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='used_parts'")
            tbl_sql = self.cursor.fetchone()
            if tbl_sql and "REFERENCES" in tbl_sql[0].upper():
                logger.info("Migrating used_parts table to remove Foreign Key constraints (allowing non-repair items)...")
                try:
                    # Rename old table
                    self.cursor.execute("ALTER TABLE used_parts RENAME TO used_parts_old")
                    
                    # Create new table without constraints
                    self.cursor.execute("""
                        CREATE TABLE used_parts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            tracking_no TEXT,
                            part_id INTEGER,
                            part_name TEXT,
                            price REAL,
                            quantity INTEGER DEFAULT 1,
                            purchase_price_snapshot REAL DEFAULT 0,
                            currency TEXT DEFAULT 'TRY',
                            exchange_rate REAL DEFAULT 1,
                            price_try REAL DEFAULT 0,
                            created_at TEXT
                        )
                    """)

                    # Discover common columns to preserve data
                    self.cursor.execute("PRAGMA table_info(used_parts_old)")
                    old_cols = {r[1].lower() for r in self.cursor.fetchall()}
                    new_cols = ["id", "tracking_no", "part_id", "part_name", "price", "quantity", "purchase_price_snapshot", "currency", "exchange_rate", "price_try", "created_at"]
                    common = [c for c in new_cols if c.lower() in old_cols]
                    
                    if common:
                        cols_str = ", ".join(self._safe_identifier(col) for col in common)
                        self.cursor.execute(
                            "INSERT INTO used_parts ({columns}) SELECT {columns} FROM used_parts_old".format(
                                columns=cols_str
                            )
                        )
                    
                    self.cursor.execute("DROP TABLE used_parts_old")
                    self.conn.commit()
                    logger.info("used_parts migration successful: Table is now flexible.")
                except Exception as m_err:
                    logger.error(f"used_parts migration failed: {m_err}")
                    # Rollback or handle sqlite rename is risky if it partially fails
                    self.conn.rollback()

            # 2. Add individual columns if missing (safety check)
            self.cursor.execute("PRAGMA table_info(used_parts)")
            cols = [row[1].lower() for row in self.cursor.fetchall()]
            
            if "part_id" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN {column_name} INTEGER".format(
                        column_name=self._safe_identifier("part_id")
                    )
                )
            if "quantity" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN {column_name} INTEGER DEFAULT 1".format(
                        column_name=self._safe_identifier("quantity")
                    )
                )
            if "purchase_price_snapshot" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN {column_name} REAL DEFAULT 0".format(
                        column_name=self._safe_identifier("purchase_price_snapshot")
                    )
                )
            if "currency" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN {column_name} TEXT DEFAULT 'TRY'".format(
                        column_name=self._safe_identifier("currency")
                    )
                )
            if "exchange_rate" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN exchange_rate REAL DEFAULT 1"
                )
            if "price_try" not in cols:
                self.cursor.execute(
                    "ALTER TABLE used_parts ADD COLUMN price_try REAL DEFAULT 0"
                )

            self.conn.commit()

            affected_tracking = set()
            try:
                from src.utils.currency_helper import CurrencyHelper

                rows = self.cursor.execute(
                    "SELECT id, tracking_no, price, COALESCE(currency, 'TRY'), "
                    "COALESCE(exchange_rate, 1), COALESCE(price_try, 0) "
                    "FROM used_parts WHERE COALESCE(price_try, 0) <= 0"
                ).fetchall()
                for row_id, tracking_no, price, currency, stored_rate, _ in rows:
                    currency = str(currency or "TRY").upper()
                    rate = float(stored_rate or 0.0)
                    if currency == "TRY":
                        rate = 1.0
                    elif rate <= 1.0:
                        rate = float(CurrencyHelper._get_rate(self, currency) or 0.0)
                    if rate <= 0 or (currency != "TRY" and rate <= 1.0):
                        continue
                    price_try = round(float(price or 0.0) * rate, 4)
                    self.cursor.execute(
                        "UPDATE used_parts SET exchange_rate=?, price_try=? WHERE id=?",
                        (rate, price_try, row_id),
                    )
                    if tracking_no:
                        affected_tracking.add(str(tracking_no))
                self.conn.commit()
            except Exception as backfill_error:
                logger.warning(
                    "Used part currency snapshot backfill skipped: %s",
                    backfill_error,
                )

            for tracking_no in affected_tracking:
                try:
                    if hasattr(self, "_sync_service_debt_from_tracking"):
                        self._sync_service_debt_from_tracking(
                            tracking_no,
                            create_if_missing=False,
                            reason="currency_snapshot_backfill",
                        )
                except Exception as sync_error:
                    logger.warning(
                        "Used part debt refresh skipped for %s: %s",
                        tracking_no,
                        sync_error,
                    )
        except Exception as e:
            logger.error(f"used_parts schema update error: {e}")


    def create_contract_attachment_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contract_attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id INTEGER,
                file_path TEXT,
                filename TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()


    def add_contract_attachment(self, contract_id, file_path, filename):
        self.create_contract_attachment_table()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO contract_attachments (contract_id, file_path, filename, created_at) VALUES (?, ?, ?, ?)",
                            (contract_id, file_path, filename, created_at))
        self.conn.commit()


    def get_contract_attachments(self, contract_id):
        self.create_contract_attachment_table()
        self.cursor.execute("SELECT * FROM contract_attachments WHERE contract_id=?", (contract_id,))
        return self.cursor.fetchall()
            



    def add_stock_movement(self, part_id, amount, new_stock, m_type, desc):
        """Standardized method for stock updates and logging — delegates to StockMixin."""
        if hasattr(self, "record_stock_movement"):
            current_stock = new_stock - amount if m_type in ("Giriş", "Giris") else new_stock + amount
            return self.record_stock_movement(
                part_id, amount if m_type in ("Giriş", "Giris") else -amount,
                current_stock=current_stock, type_val=m_type, desc=desc,
            )
        try:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id))
            if hasattr(self, "_ensure_stock_movements_schema"):
                self._ensure_stock_movements_schema()
            self.cursor.execute("""
                INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (part_id, m_type, amount, new_stock, desc, date_str))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Movement log error: {e}")
            return False



    def get_summary_data(self):
        """Yönetici özeti için konsolide veriler"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Günlük Ciro
        self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE date=? AND type='Gelir' AND COALESCE(is_deleted, 0) = 0", (today,))
        daily_turnover = self.cursor.fetchone()[0] or 0
        
        # 2. Toplam Alacak (Basit mantık: Henüz ödenmemiş veya cari bakiye analizi gerekebilir)
        # Şimdilik toplam cari bakiye (cari defter toplamı gibi)
        self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gider' AND COALESCE(is_deleted, 0) = 0") # Örnek
        total_receivables = 0 # Placeholder if no clear logic exists yet
        
        # 3. Aktif Müşteriler
        self.cursor.execute("SELECT COUNT(DISTINCT customer_name) FROM devices")
        unique_customers = self.cursor.fetchone()[0] or 0
        
        # 4. Bugünkü Kayıtlar
        self.cursor.execute("SELECT COUNT(*) FROM devices WHERE entry_date=?", (today,))
        new_jobs_today = self.cursor.fetchone()[0] or 0
        
        # 5. Kritik Stok Sayısı
        self.cursor.execute("SELECT COUNT(*) FROM parts WHERE stock <= min_stock")
        critical_stock_count = self.cursor.fetchone()[0] or 0
        
        # 6. Envanter Değeri
        self.cursor.execute("SELECT SUM(price * stock) FROM parts")
        inventory_value = self.cursor.fetchone()[0] or 0
        
        # 7. Marka Dağılımı (Top 5)
        self.cursor.execute("SELECT device_brand, COUNT(*) as c FROM devices GROUP BY device_brand ORDER BY c DESC LIMIT 5")
        brand_dist = self.cursor.fetchall()
        
        return {
            "daily_turnover": daily_turnover,
            "total_receivables": total_receivables,
            "unique_customers": unique_customers,
            "new_jobs_today": new_jobs_today,
            "critical_stock_count": critical_stock_count,
            "inventory_value": inventory_value,
            "brand_dist": brand_dist
        }


    def get_technician_performance(self):
        """Teknisyen performans verileri"""
        # status listesinde olan cihazları kimin yaptığına bak (technician kolonu varsa)
        try:
            self.cursor.execute("SELECT technician, COUNT(*) as c FROM devices WHERE technician IS NOT NULL AND status='Tamamlandı' GROUP BY technician ORDER BY c DESC")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Technician performance fetch error: {e}")
            return []


    def get_popular_parts(self):
        """En çok kullanılan parçalar"""
        try:
            self.cursor.execute("SELECT part_name, COUNT(*) as c FROM used_parts GROUP BY part_name ORDER BY c DESC LIMIT 5")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Popular parts fetch error: {e}")
            return []


    def get_weekly_stats(self):
        """Son 7 günün servis sayılarını döndürür"""
        from datetime import timedelta
        stats = []
        for i in range(6, -1, -1):
            date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            self.cursor.execute("SELECT COUNT(*) FROM devices WHERE entry_date LIKE ?", (date_str + "%",))
            count = self.cursor.fetchone()[0] or 0
            stats.append(count)
        return stats


    def get_upcoming_appointments(self, minutes=15):
        """Yaklaşan randevuları getir"""
        try:
            from datetime import datetime, timedelta
            now = datetime.now()
            target = now + timedelta(minutes=minutes)
            
            current_date = now.strftime("%Y-%m-%d")
            
            # Randevular tablosu: id, customer, date(YYYY-MM-DD), time(HH:MM), desc, status
            # Sadece bugünün randevularına bakıp saat farkını Python tarafında kontrol etmek daha güvenli
            self.cursor.execute(
                "SELECT * FROM appointments WHERE date=? AND status='Aktif'",
                (current_date,),
            )
            all_today = self.cursor.fetchall()
            
            upcoming = []
            for app in all_today:
                # app schema: id, customer, date, time, description, status, created_at...
                # Assuming index 3 is time (HH:MM)
                try:
                    app_time_str = app[3] 
                    app_time = datetime.strptime(f"{current_date} {app_time_str}", "%Y-%m-%d %H:%M")
                    
                    if now <= app_time <= target:
                        upcoming.append(app)
                except Exception as e:
                    logger.debug(f"Skipping appointment with invalid time format {app}: {e}")
            return upcoming
        except Exception as e:
            logger.error(f"Upcoming appointments error: {e}")
            return []


    def export_to_csv(self, table_name, file_path):
        """Herhangi bir tabloyu CSV'ye aktar (Pandas bağımsız)"""
        try:
            import csv
            safe_table = self._safe_identifier(table_name)
            self.cursor.execute("SELECT * FROM {table_name}".format(table_name=safe_table))
            rows = self.cursor.fetchall()
            
            if self.cursor.description:
                colnames = [column[0] for column in self.cursor.description]
                
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(colnames)
                    writer.writerows(rows)
                return True
            return False
        except Exception as e:
            logger.error(f"CSV export error: {e}")
            return False


    def execute_read_only_query(self, sql):
        """Jarvis için salt-okunur SQL sorgusu çalıştırır."""
        try:
            # Güvenlik Kontrolü
            forbidden = ["DELETE", "UPDATE", "INSERT", "DROP", "TRUNCATE", "ALTER", "CREATE", "REPLACE"]
            if any(cmd in sql.upper() for cmd in forbidden):
                return "HATA: Güvenlik nedeniyle sadece SELECT sorguları çalıştırılabilir."
            
            self.cursor.execute(sql)
            if self.cursor.description is None:
                return []
                
            columns = [column[0] for column in self.cursor.description]
            results = self.cursor.fetchall()
            
            # Format as list of dicts for Gemini
            data = []
            for row in results:
                data.append(dict(zip(columns, row)))
            return data
        except Exception as e:
            return f"SQL Hatası: {str(e)}"





    def add_transaction_extended(
        self,
        type,
        category,
        amount,
        description,
        date,
        customer_name=None,
        customer_id=None,
        payment_method=None,
        bank_account_id=None,
        related_account_id=None,
        project_id=None,
        tracking_no=None,
        ref_no=None,
        selected_services=None,
    ):
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [r[1] for r in self.cursor.fetchall()]
            insert_cols = ["type", "category", "amount", "description", "date", "created_at", "customer_name", "customer_id"]
            values = [type, category, amount, description, date, created_at, customer_name, customer_id]
            if "payment_method" in cols:
                insert_cols.append("payment_method")
                values.append(payment_method)
            if "bank_account_id" in cols:
                insert_cols.append("bank_account_id")
                values.append(bank_account_id)
            if "related_account_id" in cols:
                insert_cols.append("related_account_id")
                values.append(related_account_id)
            if "project_id" in cols:
                insert_cols.append("project_id")
                values.append(project_id)
            if "tracking_no" in cols:
                insert_cols.append("tracking_no")
                values.append(tracking_no)
            if "ref_no" in cols:
                ref_val = ref_no or tracking_no
                insert_cols.append("ref_no")
                values.append(ref_val)
            if "selected_services" in cols:
                encoded = None
                if isinstance(selected_services, (list, tuple, set, dict)):
                    try:
                        encoded = json.dumps(selected_services, ensure_ascii=False)
                    except Exception:
                        encoded = None
                elif isinstance(selected_services, str):
                    encoded = selected_services
                insert_cols.append("selected_services")
                values.append(encoded)
            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list = ", ".join(self._safe_identifier(col) for col in insert_cols)
            self.cursor.execute(
                "INSERT INTO accounting ({columns}) VALUES ({placeholders})".format(
                    columns=col_list,
                    placeholders=placeholders,
                ),
                tuple(values),
            )
            self.conn.commit()
            if bank_account_id:
                try:
                    delta = amount if str(type).lower() == "gelir" else -float(amount or 0)
                    self.update_bank_balance(bank_account_id, delta)
                except Exception as e:
                    logger.warning(f"Failed to update bank balance in extended transaction: {e}")
            pm = str(payment_method or "").lower()
            if bank_account_id or pm in ("banka", "havale", "eft", "transfer"):
                try:
                    from src.utils.audit_logger import get_audit_logger
                    audit = get_audit_logger(self)
                    audit.log_action("accounting", "BANK_TX", f"{type} | {category} | {amount} | {payment_method or ''} | Bank ID {bank_account_id or ''}")
                except Exception as e:
                    logger.debug(f"Skipping accounting bank audit log: {e}")
            return True
        except Exception as e:
            logger.error(f"Add transaction error: {e}")
            return False

    # --- FINANCE & ACCOUNTING (Shadowed methods removed - using unified Mixins) ---


    def update_reminders_schema(self):
        # 1. Create table if it doesn't exist (possibly old or new schema)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                personnel TEXT,
                date TEXT,
                description TEXT,
                status TEXT DEFAULT 'Aktif',
                created_at TEXT
            )
        """)
        
        # 2. Check and add columns if missing (Migration from old to new schema)
        try:
            self.cursor.execute("PRAGMA table_info(reminders)")
            cols = [row[1] for row in self.cursor.fetchall()]
            
            new_cols = [
                ("title", "TEXT"),
                ("personnel", "TEXT"),
                ("date", "TEXT"),
                ("description", "TEXT"),
                ("status", "TEXT DEFAULT 'Aktif'")
            ]
            
            for col, dtype in new_cols:
                if col not in cols:
                    safe_col = self._safe_identifier(col)
                    self.cursor.execute(
                        "ALTER TABLE reminders ADD COLUMN {column_name} {dtype}".format(
                            column_name=safe_col,
                            dtype=dtype,
                        )
                    )
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Reminders schema update error: {e}")
        

    def add_reminder(self, title, personnel_id, date, desc):
        try:
            # We can store personnel name or ID. Let's store name if ID is passed to look it up, or just text.
            # UI passed 'pid' (int) or None.
            p_name = ""
            if personnel_id:
                try:
                    self.cursor.execute("SELECT name FROM personnel WHERE id=?", (personnel_id,))
                    res = self.cursor.fetchone()
                    if res: p_name = res[0]
                except Exception as e:
                    logger.error(f"Personel adı alınamadı: {e}")
            
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO reminders (title, personnel, date, description, created_at) VALUES (?, ?, ?, ?, ?)",
                                (title, p_name, date, desc, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add reminder error: {e}")
            return False
            

    def get_reminders(self):
        try:
            self.cursor.execute("SELECT * FROM reminders ORDER BY date DESC")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Reminders fetch error: {e}")
            return []
    
    # --- STOK YÖNETİMİ METODLARI ---

    def add_part(self, name, category, stock, price, desc="", min_stock=5, code="", purchase_price=0, shelf=""):
        """Yeni parça/ürün ekle - Kapsamlı versiyon"""
        try:
            try:
                self.create_parts_table()
                self.update_parts_schema()
            except Exception as e:
                logger.debug(f"Schema update skipped or failed during add_part: {e}")
            
            # Locale-safe numeric conversion (Turkish comma support)
            def safe_float(val):
                if val is None or val == "": return 0.0
                try:
                    return float(str(val).replace(',', '.'))
                except Exception as e:
                    logger.debug(f"safe_float fallback for value {val}: {e}")
                    return 0.0

            def safe_int(val):
                if val is None or val == "": return 0
                try:
                    return int(float(str(val).replace(',', '.')))
                except Exception as e:
                    logger.debug(f"safe_int fallback for value {val}: {e}")
                    return 0

            stock_val = safe_int(stock)
            price_val = safe_float(price)
            purchase_val = safe_float(purchase_price)
            min_stock_val = safe_int(min_stock) if min_stock else 5
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 0. Check for existing part with same code (Active or Deleted)
            if code and str(code).strip():
                try:
                    self.cursor.execute("SELECT id, is_deleted, name, stock FROM parts WHERE code=?", (code,))
                    existing = self.cursor.fetchone()
                    
                    if existing:
                        part_id, is_deleted, part_name, current_stock = existing
                        
                        if is_deleted:
                            # RESTORE and UPDATE
                            logger.info(f"Restoring deleted part: {part_name} (ID: {part_id}) with code {code}")
                            
                            # 1. Update basic info and clear deleted flags
                            self.cursor.execute("""
                                UPDATE parts 
                                SET name=?, part_name=?, category=?, price=?, purchase_price=?, description=?, min_stock=?, shelf_number=?, 
                                    is_deleted=0, deleted_at=NULL
                                WHERE id=?
                            """, (name, name, category, price_val, purchase_val, desc, min_stock_val, shelf, part_id))
                            
                            self.conn.commit() # Commit to guarantee ID is valid for history

                            # 2. Adjust stock to match input (TARGET STOCK)
                            old_stock = current_stock if current_stock is not None else 0
                            delta = stock_val - old_stock
                            
                            if delta != 0:
                                self.adjust_stock(part_id, delta, f"Ürün Geri Yükleme - Stok Girişi: {name}", "Giriş" if delta > 0 else "Çıkış")
                            
                            self.conn.commit()
                            
                            # Audit Log for Restore
                            try:
                                from src.utils.audit_logger import get_audit_logger
                                audit = get_audit_logger(self)
                                audit.log_action('parts', 'RESTORE', f"Silinen ürün geri yüklendi: {name} (ID: {part_id})")
                            except Exception as e:
                                logger.debug(f"Skipping restore audit log for part {part_id}: {e}")
                            
                            return part_id
                        else:
                            logger.warning(f"Duplicate part code prevented: {code}")
                            return None # Duplicate exists and is active
                except Exception as e:
                    logger.error(f"Error checking duplicate part: {e}")

            # Insert part with stock=0 initially
            # Use both name and part_name columns
            self.cursor.execute("""
                INSERT INTO parts (name, part_name, category, stock, price, purchase_price, description, min_stock, code, shelf_number, created_at, is_deleted, deleted_at)
                VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, 0, NULL)
            """, (name, name, category, price_val, purchase_val, desc, min_stock_val, code, shelf, created_at))
            
            part_id = self.cursor.lastrowid
            
            # IMPORTANT: Commit before adjust_stock to ensure record_stock_movement sees the valid ID
            self.conn.commit()

            # If initial stock > 0, record it through adjust_stock
            if stock_val > 0:
                self.adjust_stock(
                    part_id=part_id,
                    delta=stock_val,
                    description=f"Yeni Ürün Girişi: {name}",
                    type_val="Giriş"
                )
            
            self.conn.commit()
            
            # Audit Log
            try:
                from src.utils.audit_logger import get_audit_logger
                audit = get_audit_logger(self)
                audit.log_action('parts', 'INSERT', f"Yeni stok kartı: {name} ({stock_val} adet) - Alış: {purchase_val} TL, Satış: {price_val} TL")
            except Exception as e:
                logger.error(f"Audit log kaydedilemedi: {e}")
            
            return part_id
        except Exception as e:
            logger.error(f"Add part error: {e}")
            return None


    def update_part(self, part_id, name, category, stock, price, desc, min_stock, code, shelf, purchase_price=0):
        try:
            stock_val = 0 if stock in (None, "") else stock
            price_val = 0 if price in (None, "") else price
            purchase_val = 0 if purchase_price in (None, "") else purchase_price
            min_stock_val = 5 if min_stock in (None, "") else min_stock
            
            # Get current stock before updating
            self.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,))
            row = self.cursor.fetchone()
            old_stock = int(row[0]) if row and row[0] is not None else 0
            
            # Update part info WITHOUT stock field (we'll handle stock separately)
            self.cursor.execute("""
                UPDATE parts 
                SET name=?, category=?, price=?, purchase_price=?, description=?, min_stock=?, code=?, shelf_number=?
                WHERE id=?
            """, (name, category, float(price_val), float(purchase_val), desc, int(min_stock_val), code, shelf, part_id))
            
            # Handle stock change if there's a difference
            delta = int(stock_val) - old_stock
            if delta != 0:
                m_type = "Giriş" if delta > 0 else "Çıkış"
                # Use record_stock_movement directly (it updates parts.stock + logs movement)
                self.record_stock_movement(
                    part_id=part_id,
                    delta=delta,
                    current_stock=old_stock,
                    type_val=m_type,
                    desc=f"Manuel Bilgi Güncelleme - {name}"
                )
                
                # If stock increased and purchase_price exists, create accounting expense
                if delta > 0 and float(purchase_val) > 0:
                    total_cost = float(purchase_val) * delta
                    today = datetime.now().strftime("%Y-%m-%d")
                    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    description = f"Stok Artışı: {name} ({delta} Adet)"
                    
                    try:
                        self.cursor.execute("""
                            INSERT INTO accounting (date, type, category, amount, description, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (today, "Gider", "Stok Güncelleme", total_cost, description, created_at))
                        logger.info(f"[STOCK] {description} → {total_cost:.2f} ₺ gider olarak kaydedildi.")
                    except Exception as e:
                        logger.error(f"Stok artışı muhasebe kaydı hatası: {e}")
            
            self.conn.commit()
            
            # Audit Log
            try:
                from src.utils.audit_logger import get_audit_logger
                audit = get_audit_logger(self)
                audit.log_action('parts', 'UPDATE', f"Stok kartı güncellendi: {name} (ID: {part_id})")
            except Exception as e:
                logger.error(f"Audit log kaydedilemedi: {e}")
            
            return True
        except Exception as e:
            logger.error(f"Update part error: {e}")
            return False


    # --- CUSTOMER BALANCE (Shadowed methods removed - using CurrencyMixin) ---


    def create_customer_notes_table(self):
        """Müşteri özel notları ve mesaj kayıtları için tablo"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                type TEXT, -- 'Note', 'WhatsApp', 'SMS', 'Call'
                content TEXT,
                created_at TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id)
            )
        """)
        self.conn.commit()


    def add_customer_note(self, customer_id, note_type, content):
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO customer_notes (customer_id, type, content, created_at)
            VALUES (?, ?, ?, ?)
        """, (customer_id, note_type, content, created_at))
        self.conn.commit()


    def get_customer_notes(self, customer_id):
        self.cursor.execute("""
            SELECT id, type, content, created_at 
            FROM customer_notes 
            WHERE customer_id = ? 
            ORDER BY created_at DESC
        """, (customer_id,))
        return self.cursor.fetchall()
            

    def delete_customer_note(self, note_id):
        self.cursor.execute("DELETE FROM customer_notes WHERE id=?", (note_id,))
        self.conn.commit()


