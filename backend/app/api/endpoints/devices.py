"""
Device/Service Endpoints - COMPLETE (YENİ İŞLEM)
Premium Bulut Backend API

Desktop Mapping:
- GET    /api/v1/devices                      -> database.get_all_devices()
- POST   /api/v1/devices                      -> database.add_device(data)
- GET    /api/v1/devices/{tracking_no}        -> database.get_device_by_tracking()
- PUT    /api/v1/devices/{tracking_no}        -> database.update_device()
- DELETE /api/v1/devices/{tracking_no}        -> database.delete_device()
- PATCH  /api/v1/devices/{tracking_no}/status -> database.update_status()
- GET    /api/v1/devices/search               -> database.search_devices()
- POST   /api/v1/devices/advanced-search      -> database.advanced_search()
- GET    /api/v1/devices/status/{status}      -> database.get_devices_by_status()
- POST   /api/v1/devices/{tracking_no}/parts  -> database.add_used_part()
- GET    /api/v1/devices/{tracking_no}/parts  -> database.get_used_parts()
- POST   /api/v1/devices/{tracking_no}/tests  -> database.add_device_test()
- GET    /api/v1/devices/{tracking_no}/tests  -> database.get_device_tests()
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from datetime import datetime, timedelta
import random
import os

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.models import (
    Device, Customer, UsedPart, DeviceTest, ServiceLog,
    Part, Transaction, TransactionType, DeviceStatus
)
from app.schemas.schemas import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceStatusUpdate,
    DeviceFinancialsUpdate,
    DeviceSearchCriteria,
    UsedPartCreate,
    UsedPartResponse,
    DeviceTestCreate,
    DeviceTestResponse
)

router = APIRouter()


@router.get("", response_model=List[DeviceResponse])
def get_all_devices(
    skip: int = 0,
    limit: int = 100,
    include_archived: bool = False,
    customer_id: Optional[int] = Query(None),
    is_invoiced: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get All Devices/Services
    
    Desktop: database.get_all_devices(include_archived)
    Auto-archives devices delivered > 1 day ago
    """
    # Auto-archive old completed devices
    yesterday = datetime.now() - timedelta(days=1)
    db.query(Device).filter(
        Device.status == DeviceStatus.TESLIM_EDILDI,
        Device.exit_date <= yesterday,
        Device.is_archived == False
    ).update({"is_archived": True})
    db.commit()
    
    # Query devices
    query = db.query(Device)
    
    if not include_archived:
        query = query.filter(Device.is_archived == False)
    
    if customer_id:
        query = query.filter(Device.customer_id == customer_id)
        
    if is_invoiced is not None:
        query = query.filter(Device.is_invoiced == is_invoiced)
    
    devices = query.order_by(Device.entry_date.desc()).offset(skip).limit(limit).all()
    return devices


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def create_device(
    device: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create New Service Record (YENİ İŞLEM)
    
    Desktop: database.add_device(data)
    Generates unique tracking number and creates service record
    """
    # Generate unique tracking number
    while True:
        tracking_no = f"SRV{random.randint(100000, 999999)}"
        existing = db.query(Device).filter(Device.tracking_no == tracking_no).first()
        if not existing:
            break
    
    # Prepare device data
    device_data = device.dict()
    device_data['tracking_no'] = tracking_no
    device_data['status'] = DeviceStatus.BEKLEMEDE
    
    # Handle customer_id vs customer_name (hybrid support)
    if device.customer_id:
        customer = db.query(Customer).filter(Customer.id == device.customer_id).first()
        if customer:
            device_data['customer_name'] = customer.name
    
    # Create device
    new_device = Device(**device_data)
    db.add(new_device)
    db.commit()
    db.refresh(new_device)
    
    # Add audit log
    add_service_log(
        db, 
        tracking_no, 
        "System", 
        f"Yeni servis kaydı oluşturuldu - {device.brand} {device.model}",
        current_user['username']
    )
    
    return new_device


@router.get("/search", response_model=List[DeviceResponse])
def search_devices(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Search Devices by Multiple Fields
    
    Desktop: database.search_devices(query)
    Searches: customer, tracking, serial, fault
    """
    search_term = f"%{q}%"
    devices = db.query(Device).filter(
        or_(
            Device.customer_name.like(search_term),
            Device.tracking_no.like(search_term),
            Device.serial_no.like(search_term),
            Device.fault_category.like(search_term),
            Device.fault_description.like(search_term),
            Device.brand.like(search_term),
            Device.model.like(search_term)
        )
    ).order_by(Device.entry_date.desc()).all()
    
    return devices


@router.post("/advanced-search", response_model=List[DeviceResponse])
def advanced_search(
    criteria: DeviceSearchCriteria,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Advanced Multi-Criteria Search
    
    Desktop: database.advanced_search(criteria)
    """
    query = db.query(Device)
    
    if criteria.customer:
        query = query.filter(Device.customer_name.like(f"%{criteria.customer}%"))
    
    if criteria.tracking:
        query = query.filter(Device.tracking_no.like(f"%{criteria.tracking}%"))
    
    if criteria.serial:
        query = query.filter(Device.serial_no.like(f"%{criteria.serial}%"))
    
    if criteria.fault:
        query = query.filter(
            or_(
                Device.fault_category.like(f"%{criteria.fault}%"),
                Device.fault_description.like(f"%{criteria.fault}%")
            )
        )
    
    if criteria.status:
        query = query.filter(Device.status == criteria.status)
    
    if criteria.date_start:
        query = query.filter(Device.entry_date >= criteria.date_start)
    
    if criteria.date_end:
        query = query.filter(Device.entry_date <= criteria.date_end)
    
    devices = query.order_by(Device.entry_date.desc()).all()
    return devices


@router.get("/status/{status}", response_model=List[DeviceResponse])
def get_devices_by_status(
    status: DeviceStatus,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Filter Devices by Status
    
    Desktop: database.get_devices_by_status(status)
    """
    devices = db.query(Device).filter(Device.status == status).order_by(Device.entry_date.desc()).all()
    return devices


@router.get("/recent")
def get_recent_devices(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Recent Service Records
    
    Desktop: database.get_recent_services(limit)
    """
    devices = db.query(Device).order_by(Device.entry_date.desc()).limit(limit).all()
    return devices


@router.get("/critical")
def get_critical_devices(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Critical/High Priority Devices
    
    Desktop: database.get_critical_devices(limit)
    """
    devices = db.query(Device).filter(
        Device.status.in_([DeviceStatus.BEKLEMEDE, DeviceStatus.TAMIRDE, DeviceStatus.PARCA_BEKLIYOR]),
        Device.urgency.in_(["Kritik", "Yüksek"])
    ).order_by(Device.entry_date.desc()).limit(limit).all()
    
    return devices


@router.get("/{tracking_no}", response_model=DeviceResponse)
def get_device(
    tracking_no: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Single Device by Tracking Number
    
    Desktop: database.get_device_by_tracking(tracking_no)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    return device


@router.put("/{tracking_no}", response_model=DeviceResponse)
def update_device(
    tracking_no: str,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Device Information
    
    Desktop: database.update_device(tracking_no, data)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    # Update fields
    update_data = device_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)
    
    db.commit()
    db.refresh(device)
    
    # Add log
    add_service_log(db, tracking_no, "Technician", f"Servis güncellendi", current_user['username'])
    
    return device


@router.patch("/{tracking_no}/status", response_model=DeviceResponse)
def update_device_status(
    tracking_no: str,
    status_update: DeviceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Device Status
    
    Desktop: database.update_status(tracking_no, status)
    Sets exit_date when status = Teslim Edildi
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    old_status = device.status
    device.status = status_update.status
    
    # Set exit date if delivered
    if status_update.status == DeviceStatus.TESLIM_EDILDI:
        device.exit_date = datetime.now()
    
    db.commit()
    db.refresh(device)
    
    # Add log
    add_service_log(
        db, 
        tracking_no, 
        "System", 
        f"Durum değiştirildi: {old_status} → {status_update.status.value}",
        current_user['username']
    )
    
    # TODO: Trigger notification (SMS/WhatsApp)
    # trigger_status_notification(tracking_no, status_update.status)
    
    return device


@router.patch("/{tracking_no}/financials", response_model=DeviceResponse)
def update_device_financials(
    tracking_no: str,
    financial_data: DeviceFinancialsUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Device Financial Information
    
    Desktop: database.update_financials(tracking_no, labor_cost, repair_details)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    device.labor_cost = financial_data.labor_cost
    if financial_data.repair_details:
        device.repair_details = financial_data.repair_details
    
    db.commit()
    db.refresh(device)
    
    return device


@router.delete("/{tracking_no}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    tracking_no: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete Device Record
    
    Desktop: database.delete_device(tracking_no)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    # Audit log before deletion
    add_service_log(db, tracking_no, "System", f"Servis kaydı silindi", current_user['username'])
    
    db.delete(device)
    db.commit()
    
    return None


# ============================================================================
# USED PARTS ENDPOINTS
# ============================================================================

@router.post("/{tracking_no}/parts", response_model=UsedPartResponse, status_code=status.HTTP_201_CREATED)
def add_used_part(
    tracking_no: str,
    part_data: UsedPartCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add Used Part to Service
    
    Desktop: database.add_used_part(tracking_no, part_name, price)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    # Create used part record
    used_part = UsedPart(
        tracking_no=tracking_no,
        part_name=part_data.part_name,
        price=part_data.price,
        quantity=part_data.quantity
    )
    
    db.add(used_part)
    db.commit()
    db.refresh(used_part)
    
    # Add log
    add_service_log(
        db, 
        tracking_no, 
        "Technician", 
        f"Parça kullanıldı: {part_data.part_name} x{part_data.quantity}",
        current_user['username']
    )
    
    return used_part


@router.get("/{tracking_no}/parts", response_model=List[UsedPartResponse])
def get_used_parts(
    tracking_no: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get All Parts Used on Service
    
    Desktop: database.get_used_parts(tracking_no)
    """
    parts = db.query(UsedPart).filter(UsedPart.tracking_no == tracking_no).all()
    return parts


# ============================================================================
# DEVICE TESTS ENDPOINTS
# ============================================================================

@router.post("/{tracking_no}/tests", response_model=DeviceTestResponse, status_code=status.HTTP_201_CREATED)
def add_device_test(
    tracking_no: str,
    test_data: DeviceTestCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Add Device Test Result
    
    Desktop: database.add_device_test(tracking_no, test_name, result, note, technician)
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    test = DeviceTest(
        tracking_no=tracking_no,
        test_name=test_data.test_name,
        result=test_data.result,
        note=test_data.note,
        technician=test_data.technician or current_user['username']
    )
    
    db.add(test)
    db.commit()
    db.refresh(test)
    
    return test


@router.get("/{tracking_no}/tests", response_model=List[DeviceTestResponse])
def get_device_tests(
    tracking_no: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get All Test Results for Device
    
    Desktop: database.get_device_tests(tracking_no)
    """
    tests = db.query(DeviceTest).filter(
        DeviceTest.tracking_no == tracking_no
    ).order_by(DeviceTest.test_date.desc()).all()
    
    return tests


# ============================================================================
# FILE UPLOAD (PHOTOS)
# ============================================================================

@router.post("/{tracking_no}/photos", status_code=status.HTTP_201_CREATED)
async def upload_device_photo(
    tracking_no: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload Device Photo
    
    Desktop: Saves to photos/ directory
    Web: Saves to uploads/photos/
    """
    device = db.query(Device).filter(Device.tracking_no == tracking_no).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with tracking number {tracking_no} not found"
        )
    
    # Create upload directory
    upload_dir = "uploads/photos"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate filename
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{tracking_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Update device photo_path
    if device.photo_path:
        device.photo_path += f",{file_path}"
    else:
        device.photo_path = file_path
    
    db.commit()
    
    return {
        "message": "Photo uploaded successfully",
        "filename": filename,
        "path": file_path
    }


# ============================================================================
# SERVICE LOGS
# ============================================================================

@router.get("/{tracking_no}/logs")
def get_service_logs(
    tracking_no: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get Service Activity Logs
    
    Desktop: database.get_logs(tracking_no)
    """
    logs = db.query(ServiceLog).filter(
        ServiceLog.device_tracking_no == tracking_no
    ).order_by(ServiceLog.created_at.desc()).all()
    
    return logs


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def add_service_log(db: Session, tracking_no: str, log_type: str, message: str, user: str):
    """Add log entry to service_logs table"""
    log = ServiceLog(
        device_tracking_no=tracking_no,
        log_type=log_type,
        message=message,
        user=user
    )
    db.add(log)
    db.commit()
