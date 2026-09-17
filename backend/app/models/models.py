"""
SQLAlchemy Database Models
Premium Bulut Backend - Complete Schema
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean, 
    ForeignKey, Enum, Date, Time
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, enum.Enum):
    ADMIN = "Admin"
    TEKNISYEN = "Teknisyen"
    MUHASEBE = "Muhasebe"
    STAJYER = "Stajyer"
    PERSONEL = "Personel"


class DeviceStatus(str, enum.Enum):
    BEKLEMEDE = "Beklemede"
    TAMIRDE = "Tamirde"
    PARCA_BEKLIYOR = "Parça Bekliyor"
    TAMAMLANDI = "Tamamlandı"
    TESLIM_EDILDI = "Teslim Edildi"
    IPTAL = "İptal Edildi"


class CustomerType(str, enum.Enum):
    BIREYSEL = "Bireysel"
    KURUMSAL = "Kurumsal"


class TransactionType(str, enum.Enum):
    GELIR = "Gelir"
    GIDER = "Gider"


class AppointmentStatus(str, enum.Enum):
    BEKLIYOR = "Bekliyor"
    TAMAMLANDI = "Tamamlandı"
    IPTAL = "İptal"


class ContractStatus(str, enum.Enum):
    AKTIF = "Aktif"
    BITTI = "Bitti"
    IPTAL = "İptal"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


# ============================================================================
# AUTHENTICATION & USERS
# ============================================================================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)  # Hashed
    role = Column(Enum(UserRole), default=UserRole.PERSONEL)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# ============================================================================
# CUSTOMERS
# ============================================================================

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20))
    phone2 = Column(String(20))
    email = Column(String(255))
    type = Column(Enum(CustomerType), default=CustomerType.BIREYSEL)
    
    # Tax Info
    tax_id = Column(String(50))
    tax_no = Column(String(50))
    tax_office = Column(String(100))
    tc_no = Column(String(11))  # TC Kimlik No
    
    # Address
    address = Column(Text)
    city = Column(String(100))
    district = Column(String(100))
    zip_code = Column(String(10))
    
    # Company Info
    company_name = Column(String(255))
    
    # Settings
    sms_enabled = Column(Boolean, default=True)
    is_problematic = Column(Boolean, default=False)
    
    # Notes
    notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    devices = relationship("Device", back_populates="customer")
    notes_history = relationship("CustomerNote", back_populates="customer")
    contracts = relationship("Contract", back_populates="customer")


class CustomerNote(Base):
    __tablename__ = "customer_notes"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    type = Column(String(50))  # Note, WhatsApp, SMS, Call
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="notes_history")


# ============================================================================
# DEVICES / SERVICES
# ============================================================================

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    tracking_no = Column(String(50), unique=True, nullable=False, index=True)
    
    # Customer
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    customer_name = Column(String(255))  # Legacy support
    customer_contact = Column(String(20))
    customer_type = Column(String(20))
    customer_tax_id = Column(String(50))
    
    # Device Info
    device_type = Column(String(100))  # Laptop, Desktop, Phone, etc.
    brand = Column(String(100), index=True)
    model = Column(String(100))
    serial_no = Column(String(100))
    imei = Column(String(50))
    pattern_lock = Column(String(50))
    
    # Problem Description
    fault_category = Column(String(255))
    fault_description = Column(Text)
    urgency = Column(String(20))  # Düşük, Normal, Yüksek, Kritik
    
    # Status & Workflow
    status = Column(Enum(DeviceStatus), default=DeviceStatus.BEKLEMEDE, index=True)
    approval_status = Column(String(50))
    priority = Column(String(20))
    
    # Dates
    entry_date = Column(DateTime, default=datetime.utcnow, index=True)
    estimated_date = Column(DateTime)
    exit_date = Column(DateTime)
    
    # Financials
    price = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    
    # Invoicing
    is_invoiced = Column(Boolean, default=False)
    invoice_no = Column(String(50))
    
    # Technical
    technician = Column(String(100))
    repair_details = Column(Text)
    warranty = Column(String(50))
    
    # Photos & Files
    photo_path = Column(Text)
    
    # Payment
    payment_status = Column(String(50))
    payment_method = Column(String(50))
    
    # Archive
    is_archived = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", back_populates="devices")
    used_parts = relationship("UsedPart", back_populates="device")
    tests = relationship("DeviceTest", back_populates="device")
    logs = relationship("ServiceLog", back_populates="device")


class UsedPart(Base):
    __tablename__ = "used_parts"
    
    id = Column(Integer, primary_key=True)
    tracking_no = Column(String(50), ForeignKey("devices.tracking_no"), nullable=False)
    part_name = Column(String(255), nullable=False)
    price = Column(Float, default=0.0)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="used_parts")


class DeviceTest(Base):
    __tablename__ = "device_tests"
    
    id = Column(Integer, primary_key=True)
    tracking_no = Column(String(50), ForeignKey("devices.tracking_no"), nullable=False)
    test_name = Column(String(100), nullable=False)
    result = Column(String(20))  # OK, FAIL, N/A
    note = Column(Text)
    technician = Column(String(100))
    test_date = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="tests")


class ServiceLog(Base):
    __tablename__ = "service_logs"
    
    id = Column(Integer, primary_key=True)
    device_tracking_no = Column(String(50), ForeignKey("devices.tracking_no"), nullable=False)
    log_type = Column(String(50))  # Customer, Technician, System
    message = Column(Text, nullable=False)
    user = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    device = relationship("Device", back_populates="logs")


# ============================================================================
# STOCK / PARTS
# ============================================================================

class Part(Base):
    __tablename__ = "parts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100))
    description = Column(Text)
    
    # Codes
    code = Column(String(50), unique=True)
    barcode = Column(String(50), unique=True)
    
    # Inventory
    stock = Column(Integer, default=0)
    min_stock = Column(Integer, default=5)
    shelf_number = Column(String(50))
    
    # Pricing
    price = Column(Float, default=0.0)
    purchase_price = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    movements = relationship("StockMovement", back_populates="part")


class StockMovement(Base):
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    type = Column(String(20))  # GİRİŞ, ÇIKIŞ, DÜZELTME
    amount = Column(Integer, nullable=False)
    current_stock = Column(Integer, nullable=False)
    description = Column(Text)
    date = Column(DateTime, default=datetime.utcnow)
    user = Column(String(100))
    
    part = relationship("Part", back_populates="movements")


# ============================================================================
# ACCOUNTING
# ============================================================================

class Transaction(Base):
    __tablename__ = "accounting"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(Enum(TransactionType), nullable=False)
    category = Column(String(100))  # Satış, Kira, Maaş, etc.
    amount = Column(Float, nullable=False)
    description = Column(Text)
    
    # Customer Link
    customer_id = Column(Integer, ForeignKey("customers.id"))
    customer_name = Column(String(255))
    
    # Invoice
    is_invoiced = Column(Boolean, default=False)
    invoice_no = Column(String(50))
    
    # Dates
    date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BankAccount(Base):
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True)
    bank_name = Column(String(100), nullable=False)
    branch_name = Column(String(100))
    account_name = Column(String(255))
    account_no = Column(String(50))
    iban = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# PERSONNEL
# ============================================================================

class Personnel(Base):
    __tablename__ = "personnel"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(String(100))
    department = Column(String(100))
    
    # Contact
    phone = Column(String(20))
    email = Column(String(255))
    tc_no = Column(String(11))
    
    # Employment
    start_date = Column(Date)
    salary = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    
    # Login (if needed)
    password_hash = Column(String(255))
    
    # Performance
    performance_score = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# APPOINTMENTS & REMINDERS
# ============================================================================

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    customer = Column(String(255))
    customer_name = Column(String(255))  # Legacy
    phone = Column(String(20))
    
    # Schedule
    date = Column(Date, nullable=False, index=True)
    time = Column(Time, nullable=False)
    
    # Service Details
    personnel = Column(String(100))
    brand = Column(String(100))
    model = Column(String(100))
    serial_no = Column(String(100))
    device = Column(String(100))
    urgency = Column(String(20))
    fault = Column(Text)
    description = Column(Text)
    
    # Status
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.BEKLIYOR)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    personnel = Column(String(100))
    personnel_id = Column(Integer)
    date = Column(DateTime, nullable=False)
    status = Column(String(20), default="Aktif")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# CONTRACTS
# ============================================================================

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    title = Column(String(255))
    contract_type = Column(String(100))  # Bakım, Destek, etc.
    description = Column(Text)
    
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Financials
    price = Column(Float, default=0.0)
    
    # Status
    status = Column(Enum(ContractStatus), default=ContractStatus.AKTIF)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="contracts")
    attachments = relationship("ContractAttachment", back_populates="contract")


class ContractAttachment(Base):
    __tablename__ = "contract_attachments"
    
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    contract = relationship("Contract", back_populates="attachments")


# ============================================================================
# SUPPORT & KNOWLEDGE BASE
# ============================================================================

class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    priority = Column(String(20))  # Low, Medium, High, Critical
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class KBArticle(Base):
    __tablename__ = "kb_articles"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================================
# SETTINGS & CONFIGURATION
# ============================================================================

class Setting(Base):
    __tablename__ = "settings"
    
    key = Column(String(100), primary_key=True)
    value = Column(Text)


class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)


class QuickNote(Base):
    __tablename__ = "quick_notes"
    
    id = Column(Integer, primary_key=True)
    group_name = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    category = Column(String(100))
    is_active = Column(Boolean, default=True)


class FastNote(Base):
    __tablename__ = "fast_notes"
    
    id = Column(Integer, primary_key=True)
    category = Column(String(100), nullable=False)
    label = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)


class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)
    barcode = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# AUDIT & LOGGING
# ============================================================================

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    table_name = Column(String(100), nullable=False)
    action = Column(String(20), nullable=False)  # INSERT, UPDATE, DELETE
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class SMSLog(Base):
    __tablename__ = "sms_log"
    
    id = Column(Integer, primary_key=True)
    tracking_no = Column(String(50))
    phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    twilio_sid = Column(String(100))
    sent_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# AI / JARVIS
# ============================================================================

class JarvisNotification(Base):
    __tablename__ = "jarvis_notifications"
    
    id = Column(Integer, primary_key=True)
    message = Column(Text, nullable=False)
    type = Column(String(50))  # info, payment, stock, device
    is_critical = Column(Boolean, default=False)
    status = Column(String(20), default="unread")  # unread, read
    created_at = Column(DateTime, default=datetime.utcnow)


class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String(20))  # Low, Normal, High
    author = Column(String(100))
    date = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# LICENSING
# ============================================================================

class Registration(Base):
    __tablename__ = "registration"
    
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    company_name = Column(String(255))
    phone = Column(String(20))
    purpose = Column(String(100))
    trial_start_date = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)


class LicenseInfo(Base):
    __tablename__ = "license_info"
    
    id = Column(Integer, primary_key=True)
    encrypted_key = Column(Text, nullable=False)
    license_type = Column(String(50))  # Trial, Pro, Enterprise
    expiry_date = Column(Date)
    hwid = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


class ActiveDevice(Base):
    __tablename__ = "active_devices"
    
    id = Column(Integer, primary_key=True)
    device_name = Column(String(255))
    hwid = Column(String(255), nullable=False)
    last_login = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# EXTERNAL TRACKING
# ============================================================================

class ExternalTracking(Base):
    __tablename__ = "external_warranty_tracking"
    
    id = Column(Integer, primary_key=True)
    internal_tracking_no = Column(String(50), nullable=False)
    external_tracking_no = Column(String(50))
    external_service_name = Column(String(255))
    sent_date = Column(Date)
    expected_return_date = Column(Date)
    status = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
