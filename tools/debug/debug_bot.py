# -*- coding: utf-8 -*-


import sqlite3
import requests
import json
import time
import sys

# Force UTF-8 for console output if possible, but fallback to replacing errors
sys.stdout.reconfigure(encoding='utf-8')

from src.utils.path_helper import PathHelper

def check_bot():
    print("[INFO] DIAGNOSTIC TOOL STARTING...")
    
    try:
        db_path = PathHelper.get_db_path("ayecpro.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Check Table Schema
        print("   -> Settings Tablo Yapisina Bakiliyor...")
        c.execute("PRAGMA table_info(settings)")
        cols = c.fetchall()
        print(f"      Tablo Kolonlari: {cols}")
        
        # Check Key
        c.execute("SELECT * FROM settings WHERE key LIKE 'telegram%'")
        rows = c.fetchall()
        print(f"      Telegram ile ilgili ayarlar: {rows}")
        
        c.execute("SELECT value FROM settings WHERE key='telegram_bot_token'")
        row = c.fetchone()
        if not row:
            print("[ERROR] TOKEN BULUNAMADI! Ayarlardan token kaydedilmemis.")
            return
        token = row[0]
        print(f"[OK] TOKEN OKUNDU: {token[:5]}...{token[-5:]}")
    except Exception as e:
        print(f"[ERROR] DATABASE HATASI: {e}")
        return

    print("[INFO] TELEGRAM API BAĞLANTISI KONTROL EDILIYOR...")
    try:
        me_url = f"https://api.telegram.org/bot{token}/getMe"
        resp = requests.get(me_url)
        data = resp.json()
        if data.get("ok"):
            print(f"[OK] API BASARILI! Bot: @{data['result']['username']} (ID: {data['result']['id']})")
        else:
            print(f"[ERROR] API HATASI (Token yanlis olabilir): {data}")
            return
    except Exception as e:
        print(f"[ERROR] BAGLANTI HATASI: {e}")
        return

    print("[INFO] MESAJLAR KONTROL EDILIYOR (Son gelenler)...")
    updates_url = f"https://api.telegram.org/bot{token}/getUpdates"
    resp = requests.get(updates_url)
    data = resp.json()
    
    if not data.get("ok"):
        print(f"[ERROR] UPDATE HATASI: {data}")
        return
        
    updates = data.get("result", [])
    if not updates:
        print("[WARN] HIC MESAJ YOK. Lutfen bota gidip bir 'Konum' gonderin.")
    
    for u in updates:
        msg = u.get("message", {})
        user = msg.get("from", {})
        username = user.get("username")
        first_name = user.get("first_name")
        print(f"--------------------------------------------------")
        print(f"GONDEREN: {first_name} (@{username})")
        
        if "location" in msg:
            loc = msg["location"]
            print(f"KONUM VERISI VAR: {loc}")
            
            print("   -> Veritabaninda eslesme araniyor...")
            # Try exact match, @ match, and case insensitive
            c.execute("SELECT id, name, telegram_username FROM personnel WHERE telegram_username=? OR telegram_username=? OR telegram_username=?", 
                     (username, f"@{username}", username.lower() if username else ""))
            match = c.fetchone()
            if match:
                print(f"   [OK] ESLESME BASARILI! Personel: {match[1]} (ID: {match[0]})")
            else:
                print(f"   [FAIL] ESLESME YOK! Veritabaninda telegram_username = '{username}' veya '@{username}' olan kimse yok.")
                print(f"   COZUM: Personel kartina '{username}' veya '@{username}' yazin.")
        else:
            print(f"METIN MESAJI: {msg.get('text', '[Medya]')}")
            print("   Not: Bu bir konum mesaji degil.")

    conn.close()
    print("--------------------------------------------------")
    print("DONE.")

if __name__ == "__main__":
    check_bot()
