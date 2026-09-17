from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models.models import Appointment, AppointmentStatus, Customer
from app.schemas.schemas import AppointmentCreate, AppointmentUpdate, AppointmentResponse

router = APIRouter()

@router.get("/", response_model=List[AppointmentResponse])
def get_appointments(
    start_date: date = None,
    end_date: date = None, 
    status: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List appointments with optional date and status filter"""
    query = db.query(Appointment)
    
    if start_date:
        query = query.filter(Appointment.date >= start_date)
    if end_date:
        query = query.filter(Appointment.date <= end_date)
    if status:
        query = query.filter(Appointment.status == status)
        
    return query.order_by(desc(Appointment.date), desc(Appointment.time)).limit(limit).all()

@router.post("/", response_model=AppointmentResponse)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db)
):
    """Create a new appointment"""
    # Create DB object
    db_appointment = Appointment(
        customer_name=appointment.customer_name,
        phone=appointment.phone,
        date=appointment.date,
        time=appointment.time,
        description=appointment.description,
        personnel=appointment.personnel,
        brand=appointment.brand,
        model=appointment.model,
        device=appointment.device,
        urgency=appointment.urgency,
        status=AppointmentStatus.BEKLIYOR
    )
    
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@router.get("/{id}", response_model=AppointmentResponse)
def get_appointment(id: int, db: Session = Depends(get_db)):
    """Get specific appointment"""
    appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return appointment

@router.patch("/{id}", response_model=AppointmentResponse)
def update_appointment(
    id: int, 
    appointment_update: AppointmentUpdate,
    db: Session = Depends(get_db)
):
    """Update appointment status or details"""
    db_appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    update_data = appointment_update.dict(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_appointment, key, value)
        
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@router.delete("/{id}")
def delete_appointment(id: int, db: Session = Depends(get_db)):
    """Delete appointment"""
    db_appointment = db.query(Appointment).filter(Appointment.id == id).first()
    if not db_appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    db.delete(db_appointment)
    db.commit()
    return {"message": "Appointment deleted successfully"}
