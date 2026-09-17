import sys
import os

# Add src to path
sys.path.append(os.getcwd())

try:
    from src.database import Database
    print("Import successful")
    
    db = Database("ayecpro.db")
    print("DB initialized")
    
    print("Calling get_field_technicians...")
    techs = db.get_field_technicians()
    print(f"Techs count: {len(techs)}")
    
    if len(techs) == 0:
        print("Debug: Fetching ALL personnel to check roles...")
        db.cursor.execute("SELECT name, role FROM personnel")
        all_p = db.cursor.fetchall()
        for p in all_p:
            print(f"Found: {p[0]} | Role: {p[1]}")
    else:
        for t in techs:
            print(t)
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
