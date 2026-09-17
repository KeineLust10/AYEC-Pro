import sys
import os
# Add current directory to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, text
from app.db.database import engine
from app.models.models import Service, Base

# Option 1: Just add the column
try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE services ADD COLUMN barcode VARCHAR(50)"))
        conn.commit()
    print("Success: Added barcode column to services table.")
except Exception as e:
    print(f"Failed to alter table: {e}")
    # Option 2: Drop and recreate if alter fails
    try:
        print("Attempting to recreate table...")
        Service.__table__.drop(engine)
        Service.__table__.create(engine)
        print("Success: Recreated services table.")
    except Exception as e2:
        print(f"Failed to recreate table: {e2}")
