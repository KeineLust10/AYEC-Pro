"""
Customer Endpoints - COMPLETE
Premium Bulut Backend API

Desktop Mapping:
- GET    /api/v1/customers              -> database.get_customers()
- POST   /api/v1/customers              -> database.add_customer(data)
- GET    /api/v1/customers/{id}         -> database.get_customer_by_id(id)
- PUT    /api/v1/customers/{id}         -> database.update_customer(id, data)
- DELETE /api/v1/customers/{id}         -> database.delete_customer(id)
- GET    /api/v1/customers/search       -> database.search_customers(query)
- GET    /api/v1/customers/{id}/history -> database.get_customer_history(name)
- GET    /api/v1/customers/{id}/summary -> database.get_customer_history_summary(name)
- GET    /api/v1/customers/{id}/balance -> database.get_customer_balance(id)
- GET    /api/v1/customers/debt         -> database.get_customers_with_debt()
- POST   /api/v1/customers/{id}/notes   -> database.add_customer_note(id, type, content)
- GET    /api/v1/customers/{id}/notes   -> database.get_customer_notes(id)
- DELETE /api/v1/customers/notes/{id}   -> database.delete_customer_note(id)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.models import Customer, CustomerNote, Device, UsedPart, Transaction, TransactionType
from app.schemas.schemas import (
    CustomerCreate, 
    CustomerUpdate, 
    CustomerResponse,
    CustomerBalance,
    CustomerHistorySummary,
    CustomerNoteCreate,
    CustomerNoteResponse
)

router = APIRouter()


@router.get("", response_model=List[CustomerResponse])
def get_customers(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    customer_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get All Customers
    
    Desktop: database.get_customers()
    Returns list of all customers ordered by name
    """
    query = db.query(Customer)
    
    # Apply search filter
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_filter),
                Customer.phone.ilike(search_filter)
            )
        )
    
    # Filter by type if specified
    if customer_type and customer_type != "Tümü":
        query = query.filter(Customer.type == customer_type)
    
    customers = query.order_by(Customer.name).offset(skip).limit(limit).all()
    return customers


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create New Customer
    
    Desktop: database.add_customer(data)
    Creates customer record with all fields
    """
    # Check for duplicate phone (only if phone is provided and not empty)
    if customer.phone and customer.phone.strip():
        existing = db.query(Customer).filter(Customer.phone == customer.phone).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Customer with phone {customer.phone} already exists"
            )
    
    # Create customer
    new_customer = Customer(**customer.dict())
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    
    # Audit log (optional - implement later)
    # add_audit_log(current_user['username'], 'customers', 'INSERT', f"Added customer: {customer.name}")
    
    return new_customer


@router.get("/search", response_model=List[CustomerResponse])
def search_customers(
    q: str = Query(..., min_length=1, description="Search query"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search Customers by Name or Phone
    
    Desktop: database.search_customers(query)
    """
    search_term = f"%{q}%"
    customers = db.query(Customer).filter(
        or_(
            Customer.name.like(search_term),
            Customer.phone.like(search_term),
            Customer.email.like(search_term),
            Customer.company_name.like(search_term)
        )
    ).order_by(Customer.name).all()
    
    return customers


@router.get("/debt", response_model=List[CustomerBalance])
def get_customers_with_debt(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Customers with Outstanding Balance
    
    Desktop: database.get_customers_with_debt()
    Returns customers where balance > 0
    """
    customers = db.query(Customer).all()
    result = []
    
    for customer in customers:
        balance = calculate_customer_balance(db, customer.id)
        if balance > 0:
            result.append({
                "customer_id": customer.id,
                "customer_name": customer.name,
                "total_services": balance + get_customer_payments(db, customer.id),
                "total_paid": get_customer_payments(db, customer.id),
                "balance": balance
            })
    
    return result


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Single Customer by ID
    
    Desktop: database.get_customer_by_id(id)
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: int,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Customer Information
    
    Desktop: database.update_customer(id, data)
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    # Update fields
    update_data = customer_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(customer, field, value)
    
    db.commit()
    db.refresh(customer)
    
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete Customer
    
    Desktop: database.delete_customer(id)
    WARNING: This will cascade delete all related records
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    # Check if customer has active services
    active_services = db.query(Device).filter(
        Device.customer_id == customer_id,
        Device.status.in_(["Beklemede", "Tamirde", "Parça Bekliyor"])
    ).count()
    
    if active_services > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete customer with {active_services} active service(s)"
        )
    
    db.delete(customer)
    db.commit()
    
    return None


@router.get("/{customer_id}/balance", response_model=CustomerBalance)
def get_customer_balance(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate Customer Balance (Cari Hesap)
    
    Desktop: database.get_customer_balance(customer_id)
    Formula: (Services + Parts + Customer Services) - (Payments)
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    # Calculate total services
    total_services = calculate_customer_balance(db, customer_id)
    total_paid = get_customer_payments(db, customer_id)
    
    return {
        "customer_id": customer.id,
        "customer_name": customer.name,
        "total_services": total_services + total_paid,
        "total_paid": total_paid,
        "balance": total_services
    }


@router.get("/{customer_id}/history")
def get_customer_history(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Customer Service History
    
    Desktop: database.get_customer_history(customer_name)
    Returns all devices/services for this customer
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    # Get devices by customer_id or customer_name (hybrid support)
    devices = db.query(Device).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).all()
    
    # Get services recorded as transactions (Quick Service/Sale)
    service_transactions = db.query(Transaction).filter(
        Transaction.customer_id == customer_id,
        Transaction.category == 'Hizmet'
    ).all()
    
    # Combine and sort by date
    history = []
    for d in devices:
        history.append({
            "id": d.id,
            "tracking_no": d.tracking_no,
            "brand": d.brand,
            "model": d.model,
            "fault_description": d.fault_description,
            "status": d.status,
            "price": d.price or 0.0,
            "entry_date": d.entry_date.isoformat() if d.entry_date else None,
            "is_device": True
        })
        
    for t in service_transactions:
        history.append({
            "id": f"tx-{t.id}",
            "tracking_no": f"POS-{t.id}",
            "brand": "Hizmet",
            "model": t.description,
            "fault_description": t.category,
            "status": "Tamamlandı",
            "price": t.amount or 0.0,
            "entry_date": t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
            "is_device": False
        })
        
    history.sort(key=lambda x: str(x['entry_date']), reverse=True)
    return history


@router.get("/{customer_id}/summary", response_model=CustomerHistorySummary)
def get_customer_summary(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Customer Summary Statistics
    
    Desktop: database.get_customer_history_summary(customer_name)
    Returns: total jobs, total spend, device history, recent jobs
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    # Get all devices
    devices = db.query(Device).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).all()
    
    # Get service transactions
    service_tx = db.query(Transaction).filter(
        Transaction.customer_id == customer_id,
        Transaction.category == 'Hizmet'
    ).all()
    
    # Calculate statistics
    total_jobs = len(devices) + len(service_tx)
    total_spend = sum(d.price or 0 for d in devices) + sum(t.amount or 0 for t in service_tx)
    
    # Device history (group by brand/model)
    device_history = {}
    for device in devices:
        key = f"{device.brand} {device.model}"
        if key in device_history:
            device_history[key] += 1
        else:
            device_history[key] = 1
    
    # Recent jobs (last 3)
    recent_jobs = devices[:3] if len(devices) >= 3 else devices
    recent_jobs_data = [
        {
            "tracking_no": d.tracking_no,
            "device": f"{d.brand} {d.model}",
            "status": d.status,
            "date": d.entry_date.isoformat() if d.entry_date else None
        }
        for d in recent_jobs
    ]
    
    # Last visit
    last_visit = devices[0].entry_date.isoformat() if devices else None
    
    return {
        "total_jobs": total_jobs,
        "total_spend": total_spend,
        "device_history": [{"device": k, "count": v} for k, v in device_history.items()],
        "recent_jobs": recent_jobs_data,
        "last_visit": last_visit
    }


@router.post("/{customer_id}/notes", response_model=CustomerNoteResponse, status_code=status.HTTP_201_CREATED)
def add_customer_note(
    customer_id: int,
    note: CustomerNoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add Customer Communication Note
    
    Desktop: database.add_customer_note(customer_id, note_type, content)
    Types: Note, WhatsApp, SMS, Call
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found"
        )
    
    new_note = CustomerNote(
        customer_id=customer_id,
        type=note.type,
        content=note.content
    )
    
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    
    return new_note


@router.get("/{customer_id}/notes", response_model=List[CustomerNoteResponse])
def get_customer_notes(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Customer Communication History
    
    Desktop: database.get_customer_notes(customer_id)
    """
    notes = db.query(CustomerNote).filter(
        CustomerNote.customer_id == customer_id
    ).order_by(CustomerNote.created_at.desc()).all()
    
    return notes


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete Customer Note
    
    Desktop: database.delete_customer_note(note_id)
    """
    note = db.query(CustomerNote).filter(CustomerNote.id == note_id).first()
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note with ID {note_id} not found"
        )
    
    db.delete(note)
    db.commit()
    
    return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_customer_balance(db: Session, customer_id: int) -> float:
    """
    Calculate total unpaid balance for customer
    
    Desktop: database.get_customer_balance(customer_id)
    Formula: (Devices + Parts + QuickSales) - Payments
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return 0.0
    
    # 1. Sum device prices
    device_total = db.query(func.sum(Device.price)).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    # 2. Sum used parts
    parts_total = db.query(func.sum(UsedPart.price)).join(Device).filter(
        or_(
            Device.customer_id == customer_id,
            Device.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    # 3. Sum Quick Sales / Service Sales (Transaction based)
    # These are recorded as 'Gelir' but represent a Sale (Debt), not a Payment.
    quick_sales = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.GELIR,
        Transaction.category.in_(['Satış', 'Hizmet']),
        or_(
            Transaction.customer_id == customer_id,
            Transaction.customer_name == customer.name
        )
    ).scalar() or 0.0

    # 4. Get payments (Only 'Tahsilat')
    payments = get_customer_payments(db, customer_id)
    
    total = device_total + parts_total + quick_sales - payments
    return round(total, 2)


def get_customer_payments(db: Session, customer_id: int) -> float:
    """Get total payments from accounting table (Category = Tahsilat)"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return 0.0
    
    payments = db.query(func.sum(Transaction.amount)).filter(
        Transaction.type == TransactionType.GELIR,
        or_(
            Transaction.category == 'Tahsilat',
            Transaction.description.ilike('%Tahsilat%'),
            Transaction.description.ilike('%Ödeme%')
        ),
        or_(
            Transaction.customer_id == customer_id,
            Transaction.customer_name == customer.name
        )
    ).scalar() or 0.0
    
    return round(payments, 2)
