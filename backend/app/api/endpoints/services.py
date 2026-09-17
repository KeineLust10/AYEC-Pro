"""
Services Endpoints - COMPLETE (HİZMET TANIMLAMA)
Premium Bulut Backend API

Desktop Mapping:
- GET    /api/v1/services           -> database.get_services_list()
- POST   /api/v1/services           -> database.add_service()
- PUT    /api/v1/services/{id}      -> database.update_service()
- DELETE /api/v1/services/{id}      -> database.delete_service()
- POST   /api/v1/services/load-ato  -> database.load_ato_2025_services()
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.core.security import get_current_user
from app.models.models import Service
from app.schemas.schemas import ServiceCreate, ServiceUpdate, ServiceResponse

router = APIRouter()


@router.get("", response_model=List[ServiceResponse])
def get_services(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get All Services
    
    Desktop: database.get_services_list()
    Returns all billable service definitions
    """
    services = db.query(Service).order_by(Service.name).offset(skip).limit(limit).all()
    return services


@router.post("", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    service: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create New Service Definition
    
    Desktop: database.add_service(name, price, description)
    """
    # Check for duplicate name
    existing = db.query(Service).filter(Service.name == service.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Service '{service.name}' already exists"
        )
    
    new_service = Service(**service.dict())
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    
    return new_service


@router.put("/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update Service Definition
    
    Desktop: database.update_service(service_id, name, price, description)
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {service_id} not found"
        )
    
    # Update fields
    update_data = service_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    db.commit()
    db.refresh(service)
    
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete Service Definition
    
    Desktop: database.delete_service(service_id)
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service with ID {service_id} not found"
        )
    
    db.delete(service)
    db.commit()
    
    return None


@router.post("/load-ato", status_code=status.HTTP_201_CREATED)
def load_ato_2025_services(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Load ATO 2025 Official Service Prices
    
    Desktop: database.load_ato_2025_services()
    Loads 46 predefined Turkish computer repair services
    """
    # Get existing service names to avoid duplicates
    existing_names = {s.name for s in db.query(Service.name).all()}
    
    # ATO 2025 Service Definitions (From Desktop App)
    ato_services = [
        ("Laptop Ekran Değişimi", 1500.0, "LCD/LED ekran değişimi"),
        ("Klavye Değişimi", 800.0, "Laptop klavye değişimi"),
        ("Batarya Değişimi", 1200.0, "Laptop batarya değişimi"),
        ("HDD/SSD Yükseltme", 500.0, "Sabit disk değişimi veya yükseltme"),
        ("RAM Yükseltme", 300.0, "Bellek yükseltme"),
        ("Anakart Tamiri", 2500.0, "Anakart onarımı"),
        ("Şarj Soketi Tamiri", 600.0, "Şarj girişi tamiri"),
        ("Fan Temizliği", 400.0, "Soğutma fanı temizliği ve termal macun değişimi"),
        ("İşletim Sistemi Kurulumu", 500.0, "Windows/Linux kurulumu"),
        ("Virüs Temizleme", 400.0, "Virüs tarama ve temizleme"),
        ("Veri Kurtarma", 1500.0, "Kayıp veri kurtarma hizmeti"),
        ("Ekran Kartı Tamiri", 2000.0, "GPU onarımı"),
        ("Ses Kartı Tamiri", 800.0, "Ses sistemi tamiri"),
        ("Wifi Kartı Değişimi", 600.0, "Kablosuz ağ kartı değişimi"),
        ("Touchpad Değişimi", 700.0, "Dokunmatik panel değişimi"),
        ("Webcam Tamiri", 500.0, "Kamera tamiri"),
        ("Hoparlör Değişimi", 400.0, "Dahili hoparlör değişimi"),
        ("Kasa Değişimi", 1000.0, "Laptop kasası değişimi"),
        ("Menteşe Tamiri", 600.0, "Ekran menteşesi tamiri"),
        ("Yazılım Optimizasyonu", 300.0, "Sistem hızlandırma"),
        ("Driver Kurulumu", 200.0, "Sürücü yükleme ve güncelleme"),
        ("BIOS Güncelleme", 500.0, "BIOS/UEFI güncelleme"),
        ("Güvenlik Duvarı Kurulumu", 300.0, "Firewall yapılandırma"),
        ("Yedekleme Sistemi Kurulumu", 400.0, "Otomatik yedekleme kurulumu"),
        ("Ağ Yapılandırması", 500.0, "Network ayarları ve sorun giderme"),
        ("Yazıcı Kurulumu", 200.0, "Yazıcı sürücü ve yapılandırma"),
        ("E-posta Kurulumu", 150.0, "E-posta hesabı yapılandırma"),
        ("Bulut Depolama Kurulumu", 200.0, "Cloud storage entegrasyonu"),
        ("Antivirüs Kurulumu", 250.0, "Antivirüs yazılımı kurulumu"),
        ("Office Kurulumu", 300.0, "Microsoft Office kurulumu"),
        ("Oyun Optimizasyonu", 600.0, "Oyun performans iyileştirme"),
        ("Overclocking", 800.0, "Donanım hız aşırtma"),
        ("Su Soğutma Kurulumu", 1500.0, "Liquid cooling sistemi kurulumu"),
        ("RGB Aydınlatma Kurulumu", 400.0, "LED ışıklandırma kurulumu"),
        ("Kablo Yönetimi", 300.0, "Kablo düzenleme ve toplama"),
        ("Masaüstü Toplama", 1000.0, "Özel masaüstü bilgisayar toplama"),
        ("Telefon Ekran Değişimi", 1200.0, "Akıllı telefon ekran değişimi"),
        ("Telefon Batarya Değişimi", 600.0, "Telefon pil değişimi"),
        ("Telefon Şarj Soketi Tamiri", 400.0, "Telefon şarj girişi tamiri"),
        ("Telefon Kamera Değişimi", 800.0, "Arka/ön kamera değişimi"),
        ("Telefon Hoparlör Tamiri", 350.0, "Telefon hoparlör tamiri"),
        ("Telefon Mikrofon Tamiri", 350.0, "Mikrofon tamiri"),
        ("Telefon Su Hasarı Tamiri", 1500.0, "Su teması onarımı"),
        ("Tablet Ekran Değişimi", 1000.0, "Tablet dokunmatik ekran değişimi"),
        ("Konsol Tamiri", 1200.0, "PlayStation/Xbox tamiri"),
        ("Modem/Router Kurulumu", 300.0, "İnternet cihazı kurulumu"),
    ]
    
    # Bulk insert
    services_created = 0
    for name, price, description in ato_services:
        if name not in existing_names:
            service = Service(name=name, price=price, description=description)
            db.add(service)
            services_created += 1
    
    db.commit()
    
    return {
        "message": "ATO 2025 services loaded successfully",
        "count": services_created
    }
