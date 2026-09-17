# -*- coding: utf-8 -*-


import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(service_definitions)")
columns = cursor.fetchall()
print("Sütunlar:", columns)
conn.close()

