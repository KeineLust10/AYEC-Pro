from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.models import AuditLog


def write_audit_log(
    db: Session,
    user_id: str,
    table_name: str,
    action: str,
    details: Optional[str] = None,
) -> None:
    row = AuditLog(
        user_id=user_id,
        table_name=table_name,
        action=action,
        details=details,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()

