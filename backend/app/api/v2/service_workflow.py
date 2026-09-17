from datetime import datetime
from typing import Optional
import random

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Device, UsedPart, ServiceLog


router = APIRouter()


def _generate_tracking_no(db: Session) -> str:
    while True:
        candidate = f"SRV{random.randint(100000, 999999)}"
        exists = db.query(Device).filter(Device.tracking_no == candidate).first()
        if not exists:
            return candidate


class WorkflowCreateOrder(BaseModel):
    customer_name: str
    brand: str
    model: str
    fault_description: Optional[str] = None
    device_type: Optional[str] = None
    technician: Optional[str] = None


class WorkflowUsePart(BaseModel):
    part_name: str
    quantity: int = 1
    unit_price: float = 0.0


class WorkflowTransition(BaseModel):
    status: str
    note: Optional[str] = None
    technician: Optional[str] = None


@router.post("/orders", status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkflowCreateOrder,
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
        technician=payload.technician,
        status="Beklemede",
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
        details=f"Work order created: tracking_no={row.tracking_no} customer={row.customer_name}",
    )
    return {"data": row}


@router.post("/orders/{tracking_no}/parts")
def add_used_part(
    tracking_no: str,
    payload: WorkflowUsePart,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("use_part")),
):
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    part = UsedPart(
        tracking_no=tracking_no,
        part_name=payload.part_name,
        quantity=payload.quantity,
        price=payload.unit_price,
        created_at=datetime.utcnow(),
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="used_parts",
        action="INSERT",
        details=f"Part added to {tracking_no}: {payload.part_name} x{payload.quantity}",
    )
    return {"data": part}


@router.post("/orders/{tracking_no}/transition")
def transition_status(
    tracking_no: str,
    payload: WorkflowTransition,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("update_service")),
):
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")

    old_status = device.status
    device.status = payload.status
    if payload.technician is not None:
        device.technician = payload.technician

    log = ServiceLog(
        device_tracking_no=tracking_no,
        log_type="System",
        message=(payload.note or f"Durum değişti: {old_status} -> {payload.status}"),
        user=payload.technician or "system",
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(device)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="devices",
        action="UPDATE",
        details=f"Workflow transition: tracking_no={tracking_no} {old_status}->{payload.status}",
    )
    return {"data": device}
