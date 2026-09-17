from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db.database import get_db
from app.models.models import Transaction, TransactionType
from app.schemas.schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse, 
    BalanceResponse, BulkInvoiceRequest
)

router = APIRouter()

@router.get("/", response_model=List[TransactionResponse])
def get_transactions(
    start_date: date = None,
    end_date: date = None, 
    type: str = None,
    customer_id: int = None,
    is_invoiced: bool = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List transactions with filtering"""
    query = db.query(Transaction)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if type:
        query = query.filter(Transaction.type == type)
    if customer_id:
        query = query.filter(Transaction.customer_id == customer_id)
    if is_invoiced is not None:
        query = query.filter(Transaction.is_invoiced == is_invoiced)
        
    return query.order_by(desc(Transaction.date), desc(Transaction.created_at)).limit(limit).all()

@router.post("/bulk-invoice")
def bulk_invoice_transactions(
    request: BulkInvoiceRequest,
    invoice_no: str = Query(...),
    db: Session = Depends(get_db)
):
    """Mark multiple transactions and devices as invoiced"""
    if request.transaction_ids:
        db.query(Transaction).filter(Transaction.id.in_(request.transaction_ids)).update(
            {"is_invoiced": True, "invoice_no": invoice_no}, 
            synchronize_session=False
        )
    
    if request.device_ids:
        from app.models.models import Device
        db.query(Device).filter(Device.id.in_(request.device_ids)).update(
            {"is_invoiced": True, "invoice_no": invoice_no},
            synchronize_session=False
        )
        
    db.commit()
    return {"message": "Successfully invoiced selected items"}

@router.post("/", response_model=TransactionResponse)
def create_transaction(
    transaction: TransactionCreate,
    db: Session = Depends(get_db)
):
    """Create new transaction"""
    db_txn = Transaction(
        type=transaction.type,
        category=transaction.category,
        amount=transaction.amount,
        description=transaction.description,
        date=transaction.date,
        customer_id=transaction.customer_id,
        customer_name=transaction.customer_name
    )
    
    db.add(db_txn)
    db.commit()
    db.refresh(db_txn)
    return db_txn


@router.put("/{id}", response_model=TransactionResponse)
def update_transaction(
    id: int,
    transaction: TransactionUpdate,
    db: Session = Depends(get_db)
):
    """Update transaction"""
    db_txn = db.query(Transaction).filter(Transaction.id == id).first()
    if not db_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = transaction.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_txn, field, value)

    db.commit()
    db.refresh(db_txn)
    return db_txn

@router.delete("/{id}")
def delete_transaction(id: int, db: Session = Depends(get_db)):
    """Delete transaction"""
    db_txn = db.query(Transaction).filter(Transaction.id == id).first()
    if not db_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    db.delete(db_txn)
    db.commit()
    return {"message": "Transaction deleted successfully"}

@router.get("/balance", response_model=BalanceResponse)
def get_balance(db: Session = Depends(get_db)):
    """Get total financial balance"""
    income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == TransactionType.GELIR).scalar() or 0.0
    expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == TransactionType.GIDER).scalar() or 0.0
    
    return {
        "total_income": income,
        "total_expense": expense,
        "balance": income - expense
    }
