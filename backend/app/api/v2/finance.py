from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Transaction, TransactionType


router = APIRouter()


class FinanceTransactionCreate(BaseModel):
    type: str
    category: Optional[str] = None
    amount: float
    description: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    date: Optional[date] = None


@router.get("/transactions")
def list_transactions(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_accounting")),
):
    query = db.query(Transaction).order_by(Transaction.id.desc())
    total = query.count()
    rows = query.offset((page - 1) * size).limit(size).all()
    return {"data": rows, "meta": {"page": page, "size": size, "total": total}}


@router.post("/transactions")
def create_transaction(
    payload: FinanceTransactionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission("add_transaction")),
):
    tx_type = TransactionType.GELIR
    if str(payload.type).lower() in {"gider", "expense"}:
        tx_type = TransactionType.GIDER

    row = Transaction(
        type=tx_type,
        category=payload.category,
        amount=payload.amount,
        description=payload.description,
        customer_id=payload.customer_id,
        customer_name=payload.customer_name,
        date=payload.date or date.today(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    write_audit_log(
        db=db,
        user_id=current_user.get("username", "system"),
        table_name="transactions",
        action="INSERT",
        details=f"Transaction created: id={row.id} type={row.type} amount={row.amount}",
    )
    return {"data": row}


@router.get("/summary")
def finance_summary(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_accounting")),
):
    gelir = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.type == TransactionType.GELIR).scalar()
    gider = db.query(func.coalesce(func.sum(Transaction.amount), 0.0)).filter(Transaction.type == TransactionType.GIDER).scalar()
    return {"data": {"income": float(gelir or 0), "expense": float(gider or 0), "net": float((gelir or 0) - (gider or 0))}}
