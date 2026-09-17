import sqlite3
import sys
import os

try:
    db_path = "C:/Users/Pc/AppData/Local/AYEC Pro/ayecpro.db"
    conn = sqlite3.connect(db_path)
    res = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table'").fetchall()
    for name, sql in res:
        if sql:
            print(f"-- Table: {name}\n{sql}\n")
except Exception as e:
    print(f"Error: {e}")
