# -*- coding: utf-8 -*-

import os
import sys

# Proje dizinini sys.path'e ekle
sys.path.append(os.getcwd())

try:
    from src.database import Database
    from src.utils.path_helper import PathHelper
    
    db_path = PathHelper.get_db_path()
    print(f"Initializing database at: {db_path}")
    
    # Database nesnesi oluşturulduğunda _initialize_full_schema otomatik çağrılır (default init_mode='full')
    db = Database()
    print("Database schema initialized successfully.")
    
    # Verify tables
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Total tables created: {len(tables)}")
    print("Tables list:", tables)
    
except Exception as e:
    print(f"Initialization failed: {e}")
    import traceback
    traceback.print_exc()
