from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models.models import Part, StockMovement
from app.schemas.schemas import (
    PartCreate, PartUpdate, PartResponse, 
    StockMovementCreate, StockMovementResponse,
    StockAddRequest, StockUseRequest
)

router = APIRouter()

@router.get("/parts", response_model=List[PartResponse])
def get_stock_parts(
    search: str = None,
    category: str = None,
    low_stock: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List stock parts with filtering"""
    query = db.query(Part)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Part.name.ilike(search_filter)) | 
            (Part.code.ilike(search_filter)) |
            (Part.barcode.ilike(search_filter))
        )
    
    if category:
        query = query.filter(Part.category == category)
        
    if low_stock:
        query = query.filter(Part.stock <= Part.min_stock)
        
    return query.order_by(Part.name).limit(limit).all()

@router.post("/parts", response_model=PartResponse)
def create_part(
    part: PartCreate,
    db: Session = Depends(get_db)
):
    """Create new stock item"""
    # Check if code exists
    if part.code:
        exists = db.query(Part).filter(Part.code == part.code).first()
        if exists:
            raise HTTPException(status_code=400, detail="Part code already exists")
            
    db_part = Part(
        name=part.name,
        category=part.category,
        description=part.description,
        code=part.code,
        barcode=part.barcode,
        stock=part.stock,
        min_stock=part.min_stock,
        shelf_number=part.shelf_number,
        price=part.price,
        purchase_price=part.purchase_price
    )
    
    db.add(db_part)
    db.commit()
    db.refresh(db_part)
    
    # Log initial stock movement if stock > 0
    if part.stock > 0:
        movement = StockMovement(
            part_id=db_part.id,
            type="GİRİŞ",
            amount=part.stock,
            current_stock=part.stock,
            description="Initial stock",
            user="System"
        )
        db.add(movement)
        db.commit()
        
    return db_part

@router.get("/parts/{id}", response_model=PartResponse)
def get_part(id: int, db: Session = Depends(get_db)):
    """Get stock item details"""
    part = db.query(Part).filter(Part.id == id).first()
    if not part:
        raise HTTPException(status_code=404, detail="Part not found")
    return part

@router.patch("/parts/{id}", response_model=PartResponse)
def update_part(
    id: int,
    part_update: PartUpdate,
    db: Session = Depends(get_db)
):
    """Update stock item details"""
    db_part = db.query(Part).filter(Part.id == id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    update_data = part_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_part, key, value)
        
    db.commit()
    db.refresh(db_part)
    return db_part

@router.delete("/parts/{id}")
def delete_part(id: int, db: Session = Depends(get_db)):
    """Delete stock item"""
    db_part = db.query(Part).filter(Part.id == id).first()
    if not db_part:
        raise HTTPException(status_code=404, detail="Part not found")
        
    db.delete(db_part)
    db.commit()
    return {"message": "Part deleted successfully"}

# Stock Movements

@router.post("/add", response_model=StockMovementResponse)
def add_stock(
    request: StockAddRequest,
    db: Session = Depends(get_db)
):
    """Quick add stock (creates part if not exists, or updates stock)"""
    # Try to find part by name
    part = db.query(Part).filter(Part.name == request.name).first()
    
    if not part:
        # Create new part
        part = Part(
            name=request.name,
            category=request.category,
            stock=0,  # Will update below
            price=request.sale_price,
            purchase_price=request.purchase_price
        )
        db.add(part)
        db.commit()
        db.refresh(part)
        
    # Update stock
    old_stock = part.stock
    part.stock += request.quantity
    
    # Create movement log
    movement = StockMovement(
        part_id=part.id,
        type="GİRİŞ",
        amount=request.quantity,
        current_stock=part.stock,
        description="Hızlı Stok Girişi",
        user="System"
    )
    
    db.add(movement)
    db.commit()
    db.refresh(movement)
    
    return movement

@router.get("/movements", response_model=List[StockMovementResponse])
def get_movements(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent stock movements"""
    return db.query(StockMovement).order_by(desc(StockMovement.date)).limit(limit).all()
