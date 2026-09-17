"""
Reports & Dashboard Endpoints - COMPLETE
Premium Bulut Backend API

Desktop Mapping:
- GET /api/v1/reports/stats          -> database.get_stats()
- GET /api/v1/reports/summary        -> database.get_summary_data()
- GET /api/v1/reports/weekly-stats   -> database.get_weekly_stats()
- GET /api/v1/reports/popular-parts  -> database.get_popular_parts()
- GET /api/v1/reports/performance    -> database.get_personnel_performance()
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Dict
from datetime import datetime, timedelta, date

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Device, Customer, Part, Transaction, UsedPart,
    Personnel, DeviceStatus, TransactionType
)
from app.schemas.schemas import DashboardStats, SummaryData

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Dashboard Statistics
    
    Desktop: database.get_stats()
    Returns device counts by status
    """
    # Count devices by status
    stats = {
        "Beklemede": 0,
        "Tamirde": 0,
        "Tamamlandı": 0,
        "total": 0
    }
    
    # Get counts
    status_counts = db.query(
        Device.status,
        func.count(Device.id).label("count")
    ).filter(
        Device.is_archived == False
    ).group_by(Device.status).all()
    
    for status, count in status_counts:
        stats[status.value] = count
        stats["total"] += count
    
    return stats


@router.get("/summary", response_model=SummaryData)
def get_summary_data(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Executive Dashboard Summary
    
    Desktop: database.get_summary_data()
    Returns comprehensive business metrics
    """
    # Today's date
    today = date.today()
    
    # 1. Daily Turnover (Today's income)
    daily_turnover = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.GELIR,
        Transaction.date == today
    ).scalar() or 0.0
    
    # 2. Total Receivables (Customer debts)
    # This requires calculating balance for each customer
    customers = db.query(Customer).all()
    total_receivables = 0.0
    for customer in customers:
        balance = calculate_customer_balance_helper(db, customer.id)
        if balance > 0:
            total_receivables += balance
    
    # 3. Today's New Jobs
    today_new_jobs = db.query(func.count(Device.id)).filter(
        func.date(Device.entry_date) == today
    ).scalar() or 0
    
    # 4. Brand Distribution (Top 5 brands)
    brand_counts = db.query(
        Device.brand,
        func.count(Device.id).label("count")
    ).filter(
        Device.is_archived == False
    ).group_by(Device.brand).order_by(func.count(Device.id).desc()).limit(5).all()
    
    brand_distribution = {brand: count for brand, count in brand_counts if brand}
    
    # 5. Critical Stock Count
    critical_stock_count = db.query(func.count(Part.id)).filter(
        Part.stock <= Part.min_stock
    ).scalar() or 0
    
    # 6. Total Inventory Value
    inventory_value = db.query(func.sum(Part.stock * Part.price)).scalar() or 0.0
    
    # 7. Unique Customers
    unique_customers = db.query(func.count(func.distinct(Customer.id))).scalar() or 0
    
    return {
        "daily_turnover": round(daily_turnover, 2),
        "total_receivables": round(total_receivables, 2),
        "today_new_jobs": today_new_jobs,
        "brand_distribution": brand_distribution,
        "critical_stock_count": critical_stock_count,
        "total_inventory_value": round(inventory_value, 2),
        "unique_customers": unique_customers
    }


@router.get("/weekly-stats")
def get_weekly_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Weekly Service Statistics (Last 7 Days)
    
    Desktop: database.get_weekly_stats()
    Returns array of service counts for charting
    """
    stats = []
    today = date.today()
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        count = db.query(func.count(Device.id)).filter(
            func.date(Device.entry_date) == target_date
        ).scalar() or 0
        
        stats.append({
            "date": target_date.isoformat(),
            "count": count
        })
    
    return stats


@router.get("/popular-parts")
def get_popular_parts(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Most Frequently Used Parts
    
    Desktop: database.get_popular_parts()
    Returns top N parts by usage
    """
    popular = db.query(
        UsedPart.part_name,
        func.count(UsedPart.id).label("usage_count"),
        func.sum(UsedPart.quantity).label("total_quantity")
    ).group_by(UsedPart.part_name).order_by(
        func.count(UsedPart.id).desc()
    ).limit(limit).all()
    
    return [
        {
            "part_name": name,
            "usage_count": usage,
            "total_quantity": qty
        }
        for name, usage, qty in popular
    ]


@router.get("/performance")
def get_personnel_performance(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Technician Performance Metrics
    
    Desktop: database.get_personnel_performance()
    Returns jobs completed and revenue per technician
    """
    performance = db.query(
        Device.technician,
        func.count(Device.id).label("jobs_completed"),
        func.sum(Device.labor_cost).label("total_revenue")
    ).filter(
        Device.status == DeviceStatus.TAMAMLANDI,
        Device.technician.isnot(None)
    ).group_by(Device.technician).order_by(
        func.count(Device.id).desc()
    ).all()
    
    return [
        {
            "technician": tech,
            "jobs_completed": jobs,
            "total_revenue": round(revenue or 0, 2)
        }
        for tech, jobs, revenue in performance
    ]


@router.get("/customer-balances")
def get_customer_balances(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Customer Revenue Summary
    
    Desktop: database.get_customer_balances()
    Returns total spend per customer
    """
    balances = db.query(
        Device.customer_name,
        func.count(Device.id).label("job_count"),
        func.sum(Device.price).label("total_spend")
    ).filter(
        Device.status == DeviceStatus.TAMAMLANDI
    ).group_by(Device.customer_name).order_by(
        func.sum(Device.price).desc()
    ).all()
    
    return [
        {
            "customer_name": name,
            "job_count": count,
            "total_spend": round(spend or 0, 2)
        }
        for name, count, spend in balances if name
    ]


@router.get("/cari-list")
def get_cari_list(
    search_query: str = "",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Detailed Customer Account Ledger (Cari Hesap)
    
    Desktop: database.get_cari_list(search_query)
    Returns: Borç (Debt), Alacak (Credit), Bakiye (Balance)
    """
    query = db.query(Customer)
    
    if search_query:
        query = query.filter(
            or_(
                Customer.name.like(f"%{search_query}%"),
                Customer.phone.like(f"%{search_query}%")
            )
        )
    
    customers = query.all()
    result = []
    
    for customer in customers:
        # Calculate services total
        services_total = db.query(func.sum(Device.price)).filter(
            or_(
                Device.customer_id == customer.id,
                Device.customer_name == customer.name
            )
        ).scalar() or 0.0
        
        # Calculate parts total
        parts_total = db.query(func.sum(UsedPart.price * UsedPart.quantity)).join(Device).filter(
            or_(
                Device.customer_id == customer.id,
                Device.customer_name == customer.name
            )
        ).scalar() or 0.0
        
        # Calculate payments
        payments = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type == TransactionType.GELIR,
            or_(
                Transaction.customer_id == customer.id,
                Transaction.customer_name == customer.name
            )
        ).scalar() or 0.0
        
        total_debt = services_total + parts_total
        balance = total_debt - payments
        
        result.append({
            "id": customer.id,
            "name": customer.name,
            "phone": customer.phone,
            "total_debt": round(total_debt, 2),
            "total_paid": round(payments, 2),
            "balance": round(balance, 2)
        })
    
    return result


@router.get("/monthly-revenue")
def get_monthly_revenue(
    year: int = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Monthly Revenue Chart Data
    
    Returns income and expense by month for charting
    """
    if not year:
        year = datetime.now().year
    
    monthly_data = []
    
    for month in range(1, 13):
        # Income
        income = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type == TransactionType.GELIR,
            func.extract('year', Transaction.date) == year,
            func.extract('month', Transaction.date) == month
        ).scalar() or 0.0
        
        # Expense
        expense = db.query(func.sum(Transaction.amount)).filter(
            Transaction.type == TransactionType.GIDER,
            func.extract('year', Transaction.date) == year,
            func.extract('month', Transaction.date) == month
        ).scalar() or 0.0
        
        monthly_data.append({
            "month": month,
            "income": round(income, 2),
            "expense": round(expense, 2),
            "profit": round(income - expense, 2)
        })
    
    return monthly_data


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_customer_balance_helper(db: Session, customer_id: int) -> float:
    """Calculate customer balance"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return 0.0
    
    # Services
    services = db.query(func.sum(Device.price)).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    # Parts
    parts = db.query(func.sum(UsedPart.price * UsedPart.quantity)).join(Device).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    # Payments
    payments = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.GELIR,
        or_(
            Transaction.customer_id == customer_id,
            Transaction.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    return round(services + parts - payments, 2)
