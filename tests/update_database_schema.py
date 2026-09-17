# -*- coding: utf-8 -*-
"""
Veritabani Sema Guncelleme Scripti
Eksik tablolari ve kolonlari ekler
"""

import sqlite3
import sys
import os

# Proje kok dizinini Python path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def update_database_schema():
    """Veritabani semasini guncelle"""
    print("\n" + "="*70)
    print("VERITABANI SEMA GUNCELLEME BASLIYOR")
    print("="*70 + "\n")
    
    conn = sqlite3.connect("ayecpro.db")
    cursor = conn.cursor()
    
    # 1. Stock tablosunu olustur
    print("[1/3] Stock tablosu kontrol ediliyor...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                category TEXT,
                quantity INTEGER DEFAULT 0,
                price REAL DEFAULT 0,
                barcode TEXT,
                min_stock INTEGER DEFAULT 5,
                supplier TEXT,
                notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  [OK] Stock tablosu hazir")
    except Exception as e:
        print(f"  [HATA] Stock tablosu olusturulamadi: {str(e)}")
    
    # 2. Personnel tablosuna commission kolonu ekle
    print("\n[2/3] Personnel tablosu guncelleniyor...")
    try:
        # Mevcut kolonlari kontrol et
        cursor.execute("PRAGMA table_info(personnel)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'commission' not in columns:
            cursor.execute("ALTER TABLE personnel ADD COLUMN commission REAL DEFAULT 0")
            print("  [OK] Commission kolonu eklendi")
        else:
            print("  [OK] Commission kolonu zaten mevcut")
            
        if 'department' not in columns:
            cursor.execute("ALTER TABLE personnel ADD COLUMN department TEXT")
            print("  [OK] Department kolonu eklendi")
        else:
            print("  [OK] Department kolonu zaten mevcut")
            
    except Exception as e:
        print(f"  [HATA] Personnel tablosu guncellenemedi: {str(e)}")
    
    # 3. Customers tablosuna tax kolonlari ekle
    print("\n[3/3] Customers tablosu guncelleniyor...")
    try:
        cursor.execute("PRAGMA table_info(customers)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'tax_no' not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN tax_no TEXT")
            print("  [OK] tax_no kolonu eklendi")
        else:
            print("  [OK] tax_no kolonu zaten mevcut")
            
        if 'tax_office' not in columns:
            cursor.execute("ALTER TABLE customers ADD COLUMN tax_office TEXT")
            print("  [OK] tax_office kolonu eklendi")
        else:
            print("  [OK] tax_office kolonu zaten mevcut")
            
    except Exception as e:
        print(f"  [HATA] Customers tablosu guncellenemedi: {str(e)}")
    
    # Degisiklikleri kaydet
    conn.commit()
    conn.close()
    
    print("\n" + "="*70)
    print("VERITABANI SEMA GUNCELLEME TAMAMLANDI")
    print("="*70 + "\n")

if __name__ == "__main__":
    update_database_schema()
