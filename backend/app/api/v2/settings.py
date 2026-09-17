from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Setting


router = APIRouter()


class SettingUpsert(BaseModel):
    key: str
    value: str


@router.get("")
def list_settings(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_dashboard")),
):
    rows = db.query(Setting).order_by(Setting.key.asc()).all()
    return {"data": rows}


@router.get("/{key}")
def get_setting(
    key: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_dashboard")),
):
    row = db.query(Setting).filter(Setting.key == key).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
    return {"data": row}


@router.put("")
def upsert_setting(
    payload: SettingUpsert,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_service")),
):
    row = db.query(Setting).filter(Setting.key == payload.key).first()
    if not row:
        row = Setting(key=payload.key, value=payload.value)
        db.add(row)
    else:
        row.value = payload.value
    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="settings",
        action="UPDATE",
        details=f"Setting upsert: key={payload.key}",
    )
    return {"data": row}
