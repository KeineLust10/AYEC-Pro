# -*- coding: utf-8 -*-

import sys
sys.path.append('.')
from src.database import Database

try:
    db = Database('data/ayec.db') 
    # Use fallback if not found
    print("Database loaded.")
    
    db.add_transaction(
        t_type="Gider",
        category="Stok Alımı",
        amount=1500.0,
        description="Test Stok Alımı via Script",
        payment_method="Nakit"
    )
    print("Add transaction executed successfully.")
    
except Exception as e:
    print("Error:", e)
