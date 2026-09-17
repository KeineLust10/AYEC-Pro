from sqlalchemy import create_engine
from app.db.database import SessionLocal
from app.models.models import Service

db = SessionLocal()
try:
    new_service = Service(
        name="Test Service",
        price=99.99,
        description="A test service from script"
    )
    db.add(new_service)
    db.commit()
    print(f"Success: Created service with ID {new_service.id}")
except Exception as e:
    print(f"Failed to create service: {e}")
finally:
    db.close()
