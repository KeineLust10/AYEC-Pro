import os
import sqlite3
import logging
import re

logger = logging.getLogger("AYECProLogger")

try:
    path = "ayecpro.db"
    if not os.path.exists(path):
        logger.error("Veritaban? bulunamad?.")
        exit()
        
    conn = sqlite3.connect(path)
    c = conn.cursor()
    
    # Tables to clear (User transactional data)
    tables = ['devices', 'customers', 'appointments', 'transactions', 'services', 'stock_items', 'audit_logs', 'sms_log']
    
    safe_tables = [t for t in tables if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", t)]

    for t in safe_tables:
        try:
            c.execute('DELETE FROM "{table}"'.format(table=t))
            logger.info("%s temizlendi.", t)
        except sqlite3.Error as e:
            logger.error("%s temizlenemedi: %s", t, e)
            
    # Reset Auto-Increment Sequences
    try:
        c.execute(
            "DELETE FROM sqlite_sequence WHERE name IN ({placeholders})".format(
                placeholders=",".join(["?"] * len(safe_tables))
            ),
            tuple(safe_tables),
        )
    except sqlite3.Error as e:
        logger.error("sqlite_sequence temizlenemedi: %s", e)
        
    conn.commit()
    conn.close()
    logger.info("Tüm eski veriler temizlendi.")
    logger.info("Admin kullanıcıları ve ayarlar korundu.")
except (sqlite3.Error, OSError) as e:
    logger.error("Hata: %s", e)
