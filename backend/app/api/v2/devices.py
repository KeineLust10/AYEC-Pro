from datetime import datetime
from typing import Optional
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Device


router = APIRouter()


def _generate_tracking_no(db: Session) -> str:
    while True:
        candidate = f"SRV{random.randint(100000, 999999)}"
        exists = db.query(Device).filter(Device.tracking_no == candidate).first()
        if not exists:
            return candidate


class DeviceCreateV2(BaseModel):
    customer_name: str
    brand: str
    model: str
    device_type: Optional[str] = None
    fault_description: Optional[str] = None
    status: Optional[str] = "Beklemede"
    price: float = 0.0


class DeviceStatusUpdateV2(BaseModel):
    status: str
    technician: Optional[str] = None


@router.get("")
def list_devices(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    q: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_dashboard")),
):
    query = db.query(Device)
    if status_filter:
        query = query.filter(Device.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Device.customer_name.ilike(like))
            | (Device.brand.ilike(like))
            | (Device.model.ilike(like))
            | (Device.tracking_no.ilike(like))
        )

    total = query.count()
    rows = query.order_by(Device.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"data": rows, "meta": {"page": page, "size": size, "total": total}}


@router.get("/{tracking_no}")
def get_device(
    tracking_no: str,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_dashboard")),
):
    row = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return {"data": row}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreateV2,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("add_service")),
):
    tracking_no = _generate_tracking_no(db)
    row = Device(
        tracking_no=tracking_no,
        customer_name=payload.customer_name,
        brand=payload.brand,
        model=payload.model,
        device_type=payload.device_type,
        fault_description=payload.fault_description,
        status=payload.status or "Beklemede",
        price=payload.price,
        entry_date=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="devices",
        action="INSERT",
        details=f"Device created: tracking_no={row.tracking_no} customer={row.customer_name}",
    )
    return {"data": row}


@router.patch("/{tracking_no}/status")
def update_device_status(
    tracking_no: str,
    payload: DeviceStatusUpdateV2,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_service")),
):
    row = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    row.status = payload.status
    if payload.technician is not None:
        row.technician = payload.technician
    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="devices",
        action="UPDATE",
        details=f"Device status changed: tracking_no={row.tracking_no} status={row.status}",
    )
    return {"data": row}
