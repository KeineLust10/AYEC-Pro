# -*- coding: utf-8 -*-

"""
Personnel Mixin  
Personel yönetimi ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class PersonnelMixin:
    """Personel bilgileri için database metodları"""
    
    def add_personnel(self, name, role, phone, salary, commission=0):
        """Yeni personel ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO personnel (name, role, phone, salary, commission, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, role, phone, salary, commission, created_at)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Personnel add error: {e}")
            return False
    
    def add_personnel_extended(self, name, role, phone, salary, commission, tc, email, dept, password):
        """Genişletilmiş alanlarda personel ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO personnel (name, role, phone, salary, commission, tc_no, email, department, password, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, role, phone, salary, commission, tc, email, dept, password, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Personnel extended add error: {e}")
            return False
    
    def get_all_personnel(self):
        """Tüm personeli getir"""
        self.cursor.execute("SELECT * FROM personnel")
        return self.cursor.fetchall()
    
    def delete_personnel(self, p_id):
        """Personel sil"""
        self.cursor.execute("DELETE FROM personnel WHERE id=?", (p_id,))
        self.conn.commit()
    
    def update_personnel(self, p_id, name, role, phone, salary):
        """Personel bilgilerini güncelle"""
        self.cursor.execute(
            "UPDATE personnel SET name=?, role=?, phone=?, salary=? WHERE id=?",
            (name, role, phone, salary, p_id)
        )
        self.conn.commit()
    
    def get_personnel_performance(self):
        """Personel performans verilerini getir"""
        self.cursor.execute("""
            SELECT p.name, p.role, COUNT(d.id) as job_count 
            FROM personnel p 
            LEFT JOIN devices d ON d.technician = p.name 
            GROUP BY p.name 
            ORDER BY job_count DESC
        """)
        return self.cursor.fetchall()
    
    def get_technician_performance(self):
        """Teknisyen performans verilerini getir"""
        self.cursor.execute("""
            SELECT technician, COUNT(*) as jobs, 
                   SUM(CASE WHEN status='Tamamlandı' THEN 1 ELSE 0 END) as completed
            FROM devices 
            WHERE technician IS NOT NULL AND technician != ''
            GROUP BY technician
        """)
        return self.cursor.fetchall()
    
    def get_staff_productivity(self):
        """Personel verimlilik puanlarını hesapla"""
        self.cursor.execute("""
            SELECT name, role, 
                   (SELECT COUNT(*) FROM devices WHERE technician=name) as total_jobs,
                   (SELECT COUNT(*) FROM devices WHERE technician=name AND status='Tamamlandı') as completed_jobs
            FROM personnel
        """)
        return self.cursor.fetchall()
    
    def get_field_technicians(self):
        """Saha ekiplerini getir"""
        # Ensure schema exists (Lazy migration)
        self.update_personnel_location_schema()
        
        query = "SELECT * FROM personnel WHERE role LIKE '%Saha%' OR role LIKE '%Teknisyen%' OR role LIKE '%Destek%' OR role LIKE '%Personel%'"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        logger.info(f"get_field_technicians: Found {len(rows)} rows for query: {query}")
        
        # Convert to dict list for easier handling
        result = []
        columns = [d[0] for d in self.cursor.description]
        for row in rows:
            d = dict(zip(columns, row))
            d['job'] = d.get('role', 'Saha Personeli') # Map role to job
            # Ensure status is ASCII safe for UI if it's missing or TR
            s = d.get('status', 'Bosta')
            if s == 'Boşta': d['status'] = 'Bosta'
            elif s == 'Görevde': d['status'] = 'Gorevde'
            elif not s: d['status'] = 'Bosta'
            result.append(d)
        return result

    def update_personnel_location_schema(self):
        """Personel tablosuna konum ve durum kolonlarını ekle"""
        try:
            columns = [
                ("lat", "REAL"),
                ("lng", "REAL"),
                ("status", "TEXT DEFAULT 'Bosta'"),
                ("last_seen", "TEXT")
            ]
            
            self.cursor.execute("PRAGMA table_info(personnel)")
            existing_cols = [info[1] for info in self.cursor.fetchall()]
            
            for col_name, col_type in columns:
                if col_name not in existing_cols:
                    self.cursor.execute(
                        "ALTER TABLE personnel ADD COLUMN {column} {ddl}".format(
                            column=self._safe_identifier(col_name),
                            ddl=col_type,
                        )
                    )
            
            self.conn.commit()
            
            # If no personnel with location exists, seed some for demo
            # self.cursor.execute("SELECT COUNT(*) FROM personnel WHERE lat IS NOT NULL")
            # if self.cursor.fetchone()[0] == 0:
            #     self.seed_demo_personnel_locations()
                
        except Exception as e:
            logger.error(f"Personnel schema update error: {e}")

    def seed_demo_personnel_locations(self):
        """Demo için saha personeli konumlarını salla"""
        try:
            # Get existing field staff or create if none
            self.cursor.execute("SELECT id FROM personnel WHERE role LIKE '%Saha%' OR role LIKE '%Teknisyen%'")
            staff = self.cursor.fetchall()
            
            if not staff:
                # Create dummy staff
                self.add_personnel("Ahmet Yilmaz", "Saha Teknisyeni", "05551112233", 25000)
                self.add_personnel("Mehmet Demir", "Saha Operasyon", "05442223344", 26000)
                self.conn.commit()
                staff = self.get_all_personnel() # Reload
                
            # Update locations around default center (Balıkesir approx)
            import random
            base_lat, base_lng = 39.6484, 27.8826
            
            updates = [
                (base_lat + 0.005, base_lng + 0.005, "Gorevde", staff[0][0] if staff else 1),
                (base_lat - 0.003, base_lng - 0.002, "Bosta", staff[1][0] if len(staff)>1 else 2)
            ]
            
            for lat, lng, status, pid in updates:
                if pid:
                    self.cursor.execute("UPDATE personnel SET lat=?, lng=?, status=? WHERE id=?", (lat, lng, status, pid))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Seeding personnel error: {e}")

    def update_personnel_schema_extended(self):
        """Personel tablosuna login için gerekli kolonları ekle (Migration)"""
        try:
            self.cursor.execute("PRAGMA table_info(personnel)")
            existing_cols = [row[1] for row in self.cursor.fetchall()]
            
            updates = [
                ("username", "TEXT"), # UNIQUE removed for SQLite compatibility
                ("password", "TEXT"),
                ("email", "TEXT"),
                ("active", "INTEGER DEFAULT 1"), # 1: Active, 0: Passive
                ("salary", "REAL DEFAULT 0"),
                ("commission", "REAL DEFAULT 0"),
                ("tc_no", "TEXT"),
                ("department", "TEXT"),
                ("telegram_username", "TEXT"),
                ("password_hash", "TEXT"),
                ("employment_type", "TEXT DEFAULT 'monthly'"),
                ("daily_wage", "REAL DEFAULT 0")
            ]
            
            for col, dtype in updates:
                if col not in existing_cols:
                    try:
                        self.cursor.execute(
                            "ALTER TABLE personnel ADD COLUMN {column} {ddl}".format(
                                column=self._safe_identifier(col),
                                ddl=dtype,
                            )
                        )
                    except Exception as col_err:
                         # Ignore 'duplicate column name' errors if race condition
                         logger.warning(f"Column add warning ({col}): {col_err}")
            
            # Add Unique Index separately
            try:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_personnel_username ON personnel(username)")
            except Exception as idx_err:
                logger.warning(f"Index creation warning: {idx_err}")

            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS personnel_daily_wages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    personnel_id INTEGER NOT NULL,
                    work_year INTEGER NOT NULL,
                    work_month INTEGER NOT NULL,
                    work_days REAL NOT NULL,
                    daily_wage REAL NOT NULL,
                    total_amount REAL NOT NULL,
                    payment_date TEXT NOT NULL,
                    note TEXT,
                    accounting_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(personnel_id, work_year, work_month)
                )
                """
            )
            self.cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_personnel_daily_wages_period
                ON personnel_daily_wages(work_year, work_month, personnel_id)
                """
            )

            self.conn.commit()
        except Exception as e:
            logger.error(f"Personnel extended schema update error: {e}")

    def update_personnel_schema_telegram(self):
         """Telegram entegrasyonu için şema güncellemesi"""
         try:
             self.cursor.execute("PRAGMA table_info(personnel)")
             existing_cols = [row[1] for row in self.cursor.fetchall()]
             if "telegram_id" not in existing_cols:
                 self.cursor.execute("ALTER TABLE personnel ADD COLUMN telegram_id TEXT")
             self.conn.commit()
         except Exception as e:
             logger.error(f"Telegram schema update error: {e}")

