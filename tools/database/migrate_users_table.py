#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Database Migration: Add personnel_id to users table
This links user accounts to personnel records
"""

import sqlite3
import os
import sys

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.path_helper import PathHelper

def upgrade_users_table():
    """Add personnel_id column to users table"""
    db_path = PathHelper.get_db_path("ayecpro.db")
    print(f"Veritabanı: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'personnel_id' in columns:
            print("[OK] personnel_id kolonu zaten mevcut")
        else:
            print("[INFO] personnel_id kolonu ekleniyor...")
            cursor.execute("ALTER TABLE users ADD COLUMN personnel_id INTEGER")
            conn.commit()
            print("[OK] personnel_id kolonu basariyla eklendi")
        
        # Show current users table structure
        cursor.execute("PRAGMA table_info(users)")
        print("\n[INFO] Users Tablosu Yapisi:")
        for col in cursor.fetchall():
            print(f"  - {col[1]} ({col[2]})")
        
        # Show existing users
        cursor.execute("SELECT id, username, role, personnel_id FROM users")
        users = cursor.fetchall()
        print(f"\n[INFO] Mevcut Kullanicilar ({len(users)} adet):")
        for user in users:
            print(f"  - ID: {user[0]}, Username: {user[1]}, Role: {user[2]}, Personnel ID: {user[3]}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] HATA: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION: Add personnel_id to users")
    print("=" * 60)
    
    success = upgrade_users_table()
    
    if success:
        print("\n[OK] Migration basarili!")
    else:
        print("\n[ERROR] Migration basarisiz!")
    
    input("\nDevam etmek icin Enter'a basin...")
