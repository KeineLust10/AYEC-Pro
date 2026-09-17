from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.rbac import require_permission
from app.db.database import get_db
from app.models.models import Customer, Device, Transaction, TransactionType


router = APIRouter()


@router.get("/dashboard")
def dashboard_report(
    db: Session = Depends(get_db),
    _user: dict = Depends(require_permission("view_reports")),
):
    today = date.today()
    week_start = today - timedelta(days=7)

    total_customers = db.query(func.count(Customer.id)).scalar() or 0
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    active_devices = db.query(func.count(Device.id)).filter(Device.status.in_(["Beklemede", "Tamirde", "Parça Bekliyor"])).scalar() or 0

    revenue_week = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.type == TransactionType.GELIR, Transaction.date >= week_start)
        .scalar()
        or 0
    )
    expense_week = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0.0))
        .filter(Transaction.type == TransactionType.GIDER, Transaction.date >= week_start)
        .scalar()
        or 0
    )

    return {
        "data": {
            "generated_at": datetime.utcnow().isoformat(),
            "customers_total": int(total_customers),
            "devices_total": int(total_devices),
            "devices_active": int(active_devices),
            "weekly_income": float(revenue_week),
            "weekly_expense": float(expense_week),
            "weekly_net": float(revenue_week - expense_week),
        }
    }
