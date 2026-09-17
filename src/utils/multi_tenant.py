# -*- coding: utf-8 -*-

"""
Multi-Tenant Architecture
AYEC Pro Teknik Servis Yonetim Sistemi

Çoklu şirket/organizasyon desteği - Veri izolasyonu ve merkezi yönetim
"""

import sqlite3
import logging
from datetime import datetime
import json
from src.utils.password_security import hash_password, verify_password

logger = logging.getLogger('MultiTenant')

class TenantManager:
    """
    Multi-tenant yönetim sistemi
    """
    
    def __init__(self, master_db='master_tenant.db'):
        self.master_db = master_db
        self.conn = sqlite3.connect(master_db)
        self.cursor = self.conn.cursor()
        self._init_master_db()
    
    def _init_master_db(self):
        """Master veritabanını başlat"""
        
        # Tenants (Şirketler/Organizasyonlar)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_code TEXT UNIQUE NOT NULL,
                company_name TEXT NOT NULL,
                domain TEXT,
                database_name TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                plan TEXT DEFAULT 'basic',
                max_users INTEGER DEFAULT 5,
                max_storage_mb INTEGER DEFAULT 1000,
                created_at TEXT,
                expires_at TEXT,
                settings TEXT
            )
        ''')
        
        # Tenant Users (Her tenant'ın kullanıcıları)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                role TEXT DEFAULT 'user',
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                last_login TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                UNIQUE(tenant_id, username)
            )
        ''')
        
        # Tenant Subscriptions (Abonelik bilgileri)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER,
                plan_name TEXT,
                price REAL,
                billing_cycle TEXT,
                start_date TEXT,
                end_date TEXT,
                auto_renew INTEGER DEFAULT 1,
                payment_method TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')
        
        # Tenant Usage Stats (Kullanım istatistikleri)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tenant_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER,
                metric_name TEXT,
                metric_value REAL,
                recorded_at TEXT,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            )
        ''')
        
        self.conn.commit()
        logger.info("Master tenant database initialized")
    
    def create_tenant(self, company_name, admin_username, admin_password, admin_email, plan='basic'):
        """
        Yeni tenant (şirket) oluştur
        
        Args:
            company_name: Şirket adı
            admin_username: Admin kullanıcı adı
            admin_password: Admin şifresi
            admin_email: Admin e-posta
            plan: Abonelik planı
        
        Returns:
            dict: Tenant bilgileri
        """
        try:
            # Tenant code oluştur (şirket adından)
            tenant_code = self._generate_tenant_code(company_name)
            
            # Database adı
            db_name = f'tenant_{tenant_code}.db'
            
            # Tenant kaydı oluştur
            self.cursor.execute('''
                INSERT INTO tenants (
                    tenant_code, company_name, database_name, 
                    status, plan, created_at, settings
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                tenant_code,
                company_name,
                db_name,
                'active',
                plan,
                datetime.now().isoformat(),
                json.dumps({})
            ))
            
            tenant_id = self.cursor.lastrowid
            
            # Admin kullanıcı oluştur
            password_hash = hash_password(admin_password)
            
            self.cursor.execute('''
                INSERT INTO tenant_users (
                    tenant_id, username, password, email, role, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                tenant_id,
                admin_username,
                password_hash,
                admin_email,
                'admin',
                datetime.now().isoformat()
            ))
            
            self.conn.commit()
            
            # Tenant database'i oluştur
            self._create_tenant_database(db_name)
            
            logger.info(f"Tenant created: {tenant_code} ({company_name})")
            
            return {
                'success': True,
                'tenant_id': tenant_id,
                'tenant_code': tenant_code,
                'database_name': db_name,
                'admin_username': admin_username
            }
            
        except sqlite3.IntegrityError:
            return {'success': False, 'error': 'Tenant code already exists'}
        except Exception as e:
            logger.error(f"Create tenant error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_tenant_code(self, company_name):
        """Tenant code oluştur"""
        # Şirket adından code üret
        code = ''.join(c for c in company_name if c.isalnum()).lower()[:10]
        
        # Benzersiz yap
        counter = 1
        original_code = code
        while self._tenant_code_exists(code):
            code = f"{original_code}{counter}"
            counter += 1
        
        return code
    
    def _tenant_code_exists(self, code):
        """Tenant code var mı?"""
        self.cursor.execute('SELECT id FROM tenants WHERE tenant_code = ?', (code,))
        return self.cursor.fetchone() is not None
    
    def _create_tenant_database(self, db_name):
        """Tenant için ayrı database oluştur"""
        # Yeni database bağlantısı
        tenant_conn = sqlite3.connect(db_name)
        tenant_cursor = tenant_conn.cursor()
        
        # Ana uygulama tablolarını oluştur
        # (Database sınıfındaki create_table metodlarını kullan)
        from src.database import Database
        
        # Geçici Database instance
        temp_db = Database(db_name)
        temp_db.close()
        
        tenant_conn.close()
        
        logger.info(f"Tenant database created: {db_name}")
    
    def get_tenant_by_code(self, tenant_code):
        """Tenant bilgilerini getir"""
        self.cursor.execute('SELECT * FROM tenants WHERE tenant_code = ?', (tenant_code,))
        row = self.cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'tenant_code': row[1],
                'company_name': row[2],
                'domain': row[3],
                'database_name': row[4],
                'status': row[5],
                'plan': row[6],
                'max_users': row[7],
                'max_storage_mb': row[8],
                'created_at': row[9],
                'expires_at': row[10]
            }
        return None
    
    def authenticate_tenant_user(self, tenant_code, username, password):
        """
        Tenant kullanıcı girişi
        
        Args:
            tenant_code: Tenant kodu
            username: Kullanıcı adı
            password: Şifre
        
        Returns:
            dict: Kullanıcı bilgileri veya None
        """
        # Tenant'ı bul
        tenant = self.get_tenant_by_code(tenant_code)
        if not tenant:
            return None
        
        # Şifreyi hashle
        
        # Kullanıcıyı kontrol et
        self.cursor.execute('''
            SELECT * FROM tenant_users 
            WHERE tenant_id = ? AND username = ? AND is_active = 1
        ''', (tenant['id'], username))
        
        row = self.cursor.fetchone()
        
        if row:
            valid, upgraded = verify_password(password, row[3])
            if not valid:
                return None
            if upgraded:
                self.cursor.execute(
                    "UPDATE tenant_users SET password=? WHERE id=?",
                    (upgraded, row[0]),
                )
                self.conn.commit()

            # Son giriş zamanını güncelle
            self.cursor.execute('''
                UPDATE tenant_users SET last_login = ? WHERE id = ?
            ''', (datetime.now().isoformat(), row[0]))
            self.conn.commit()
            
            return {
                'user_id': row[0],
                'tenant_id': row[1],
                'username': row[2],
                'email': row[4],
                'role': row[5],
                'tenant_code': tenant_code,
                'database_name': tenant['database_name']
            }
        
        return None
    
    def get_tenant_database(self, tenant_code):
        """Tenant'ın database bağlantısını getir"""
        tenant = self.get_tenant_by_code(tenant_code)
        if not tenant:
            return None
        
        from src.database import Database
        return Database(tenant['database_name'])
    
    def list_tenants(self, status='active'):
        """Tüm tenant'ları listele"""
        query = 'SELECT * FROM tenants'
        params = []
        
        if status:
            query += ' WHERE status = ?'
            params.append(status)
        
        query += ' ORDER BY created_at DESC'
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        tenants = []
        for row in rows:
            tenants.append({
                'id': row[0],
                'tenant_code': row[1],
                'company_name': row[2],
                'database_name': row[4],
                'status': row[5],
                'plan': row[6],
                'created_at': row[9]
            })
        
        return tenants
    
    def update_tenant_status(self, tenant_id, status):
        """Tenant durumunu güncelle"""
        self.cursor.execute('''
            UPDATE tenants SET status = ? WHERE id = ?
        ''', (status, tenant_id))
        self.conn.commit()
        
        logger.info(f"Tenant {tenant_id} status updated to {status}")
    
    def record_usage(self, tenant_id, metric_name, metric_value):
        """Kullanım metriği kaydet"""
        self.cursor.execute('''
            INSERT INTO tenant_usage (tenant_id, metric_name, metric_value, recorded_at)
            VALUES (?, ?, ?, ?)
        ''', (tenant_id, metric_name, metric_value, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_tenant_usage(self, tenant_id, metric_name=None, days=30):
        """Tenant kullanım istatistikleri"""
        query = '''
            SELECT metric_name, metric_value, recorded_at 
            FROM tenant_usage 
            WHERE tenant_id = ?
        '''
        params = [tenant_id]
        
        if metric_name:
            query += ' AND metric_name = ?'
            params.append(metric_name)
        
        query += ' ORDER BY recorded_at DESC LIMIT ?'
        params.append(days * 24)  # Saatlik kayıt varsayımı
        
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        return [{'metric': row[0], 'value': row[1], 'timestamp': row[2]} for row in rows]
    
    def close(self):
        """Bağlantıyı kapat"""
        self.conn.close()

class TenantContext:
    """
    Tenant bağlamı - Her istek için tenant bilgisi
    """
    
    def __init__(self, tenant_code, user_id=None):
        self.tenant_code = tenant_code
        self.user_id = user_id
        self.tenant_manager = TenantManager()
        self.tenant = self.tenant_manager.get_tenant_by_code(tenant_code)
        self.db = None
    
    def get_database(self):
        """Tenant database'i getir"""
        if self.db is None:
            self.db = self.tenant_manager.get_tenant_database(self.tenant_code)
        return self.db
    
    def __enter__(self):
        """Context manager enter"""
        return self
    
    def __exit__(self, exc_type, exc_val, _exc_tb):
        """Context manager exit"""
        if self.db:
            self.db.close()
        self.tenant_manager.close()

# Global tenant manager
_tenant_manager = None

def get_tenant_manager():
    """Global tenant manager instance"""
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager

if __name__ == '__main__':
    # Test
    logger.info("Multi-Tenant System - Test")
    
    manager = TenantManager()
    
    # Test tenant oluştur
    result = manager.create_tenant(
        company_name="Test Şirketi A",
        admin_username="admin",
        admin_password="DemoTenant2026A",
        admin_email="admin@testfirma.com",
        plan="premium"
    )
    
    logger.info("Yeni Tenant:")
    logger.info(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Tenant listesi
    logger.info("Tüm Tenant'lar:")
    tenants = manager.list_tenants()
    for tenant in tenants:
        logger.info("  - %s (%s)", tenant["company_name"], tenant["tenant_code"])
    
    # Authentication test
    if result['success']:
        auth = manager.authenticate_tenant_user(
            result['tenant_code'],
            'admin',
            'DemoTenant2026A'
        )
        logger.info("Authentication Test:")
        logger.info(json.dumps(auth, indent=2, ensure_ascii=False))
    
    manager.close()
    logger.info("Multi-tenant system test completed")
