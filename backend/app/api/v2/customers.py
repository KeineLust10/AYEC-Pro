from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Customer


router = APIRouter()


class CustomerCreateV2(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    type: Optional[str] = "Bireysel"
    notes: Optional[str] = None


class CustomerUpdateV2(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    type: Optional[str] = None
    notes: Optional[str] = None
    is_problematic: Optional[bool] = None
    sms_enabled: Optional[bool] = None


@router.get("")
def list_customers(
    q: Optional[str] = Query(default=None, description="Name/phone search"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_customer")),
):
    query = db.query(Customer)
    if q:
        like = f"%{q}%"
        query = query.filter((Customer.name.ilike(like)) | (Customer.phone.ilike(like)))

    total = query.count()
    rows = (
        query.order_by(Customer.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {"data": rows, "meta": {"page": page, "size": size, "total": total}}


@router.get("/{customer_id}")
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_customer")),
):
    row = db.query(Customer).filter(Customer.id == customer_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return {"data": row}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreateV2,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("add_customer")),
):
    row = Customer(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        address=payload.address,
        type=payload.type or "Bireysel",
        notes=payload.notes,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="customers",
        action="INSERT",
        details=f"Customer created: id={row.id} name={row.name}",
    )
    return {"data": row}


@router.put("/{customer_id}")
def update_customer(
    customer_id: int,
    payload: CustomerUpdateV2,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("add_customer")),
):
    row = db.query(Customer).filter(Customer.id == customer_id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, str(v) if k == "email" and v is not None else v)

    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="customers",
        action="UPDATE",
        details=f"Customer updated: id={row.id} name={row.name}",
    )
    return {"data": row}
