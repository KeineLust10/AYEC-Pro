"""
Pydantic Schemas - Request/Response Models
Premium Bulut Backend

COMPLETE mapping of all database functions to API schemas
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date, time
from enum import Enum


# ============================================================================
# ENUMS (Match SQLAlchemy models)
# ============================================================================

class UserRoleEnum(str, Enum):
    ADMIN = "Admin"
    TEKNISYEN = "Teknisyen"
    MUHASEBE = "Muhasebe"
    STAJYER = "Stajyer"
    PERSONEL = "Personel"


class DeviceStatusEnum(str, Enum):
    BEKLEMEDE = "Beklemede"
    TAMIRDE = "Tamirde"
    PARCA_BEKLIYOR = "Parça Bekliyor"
    TAMAMLANDI = "Tamamlandı"
    TESLIM_EDILDI = "Teslim Edildi"
    IPTAL = "İptal Edildi"


class CustomerTypeEnum(str, Enum):
    BIREYSEL = "Bireysel"
    KURUMSAL = "Kurumsal"


class TransactionTypeEnum(str, Enum):
    GELIR = "Gelir"
    GIDER = "Gider"


class AppointmentStatusEnum(str, Enum):
    BEKLIYOR = "Bekliyor"
    TAMAMLANDI = "Tamamlandı"
    IPTAL = "İptal"


# ============================================================================
# AUTHENTICATION SCHEMAS
# ============================================================================

class UserLogin(BaseModel):
    """POST /api/v1/auth/login"""
    username: str
    password: str


class UserRegister(BaseModel):
    """POST /api/v1/auth/register"""
    username: str
    password: str
    email: EmailStr
    role: UserRoleEnum = UserRoleEnum.PERSONEL


class Token(BaseModel):
    """Response for login"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: Optional[int] = None
    user: dict


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    """User information response"""
    id: int
    username: str
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# CUSTOMER SCHEMAS
# ============================================================================

class CustomerBase(BaseModel):
    """Base customer data"""
    name: str
    phone: Optional[str] = None
    phone2: Optional[str] = None
    email: Optional[str] = None  # Changed from EmailStr to str to accept empty strings
    type: CustomerTypeEnum = CustomerTypeEnum.BIREYSEL
    tax_id: Optional[str] = None
    tax_no: Optional[str] = None
    tax_office: Optional[str] = None
    tc_no: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    zip_code: Optional[str] = None
    company_name: Optional[str] = None
    sms_enabled: bool = True
    is_problematic: bool = False
    notes: Optional[str] = None


class CustomerCreate(CustomerBase):
    """POST /api/v1/customers"""
    pass


class CustomerUpdate(CustomerBase):
    """PUT /api/v1/customers/{id}"""
    name: Optional[str] = None


class CustomerResponse(CustomerBase):
    """GET /api/v1/customers"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CustomerBalance(BaseModel):
    """GET /api/v1/customers/{id}/balance"""
    customer_id: int
    customer_name: str
    total_services: float
    total_paid: float
    balance: float


class CustomerHistorySummary(BaseModel):
    """GET /api/v1/customers/{name}/summary"""
    total_jobs: int
    total_spend: float
    device_history: List[dict]
    recent_jobs: List[dict]
    last_visit: Optional[str] = None


class CustomerNoteCreate(BaseModel):
    """POST /api/v1/customers/{id}/notes"""
    type: str = Field(..., description="Note, WhatsApp, SMS, Call")
    content: str


class CustomerNoteResponse(BaseModel):
    """GET /api/v1/customers/{id}/notes"""
    id: int
    type: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# DEVICE / SERVICE SCHEMAS
# ============================================================================

class DeviceBase(BaseModel):
    """Base device/service data"""
    customer_name: str
    device_type: Optional[str] = None
    brand: str
    model: str
    serial_no: Optional[str] = None
    imei: Optional[str] = None
    pattern_lock: Optional[str] = None
    fault_category: Optional[str] = None
    fault_description: Optional[str] = None
    urgency: Optional[str] = "Normal"
    estimated_date: Optional[datetime] = None
    price: float = 0.0
    labor_cost: float = 0.0
    technician: Optional[str] = None
    repair_details: Optional[str] = None


class DeviceCreate(DeviceBase):
    """POST /api/v1/devices"""
    customer_id: Optional[int] = None


class DeviceUpdate(BaseModel):
    """PATCH /api/v1/devices/{tracking_no}"""
    status: Optional[DeviceStatusEnum] = None
    technician: Optional[str] = None
    repair_details: Optional[str] = None
    price: Optional[float] = None
    labor_cost: Optional[float] = None
    estimated_date: Optional[datetime] = None


class DeviceResponse(DeviceBase):
    """GET /api/v1/devices"""
    id: int
    tracking_no: str
    customer_id: Optional[int] = None
    status: str
    entry_date: datetime
    exit_date: Optional[datetime] = None
    is_archived: bool
    is_invoiced: bool = False
    invoice_no: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceStatusUpdate(BaseModel):
    """PATCH /api/v1/devices/{tracking_no}/status"""
    status: DeviceStatusEnum


class DeviceFinancialsUpdate(BaseModel):
    """PATCH /api/v1/devices/{tracking_no}/financials"""
    labor_cost: float
    repair_details: Optional[str] = None


class DeviceSearchCriteria(BaseModel):
    """POST /api/v1/devices/advanced-search"""
    customer: Optional[str] = None
    tracking: Optional[str] = None
    serial: Optional[str] = None
    fault: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    status: Optional[DeviceStatusEnum] = None


class UsedPartCreate(BaseModel):
    """POST /api/v1/devices/{tracking_no}/used-parts"""
    part_name: str
    price: float
    quantity: int = 1


class UsedPartResponse(BaseModel):
    """GET /api/v1/devices/{tracking_no}/used-parts"""
    id: int
    part_name: str
    price: float
    quantity: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class DeviceTestCreate(BaseModel):
    """POST /api/v1/devices/{tracking_no}/tests"""
    test_name: str
    result: str = Field(..., description="OK, FAIL, N/A")
    note: Optional[str] = None
    technician: Optional[str] = None


class DeviceTestResponse(BaseModel):
    """GET /api/v1/devices/{tracking_no}/tests"""
    id: int
    test_name: str
    result: str
    note: Optional[str] = None
    technician: Optional[str] = None
    test_date: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# STOCK / PARTS SCHEMAS
# ============================================================================

class PartBase(BaseModel):
    """Base part data"""
    name: str
    category: str
    description: Optional[str] = None
    code: Optional[str] = None
    barcode: Optional[str] = None
    stock: int = 0
    min_stock: int = 5
    shelf_number: Optional[str] = None
    price: float = 0.0
    purchase_price: float = 0.0


class PartCreate(PartBase):
    """POST /api/v1/stock/parts"""
    pass


class PartUpdate(PartBase):
    """PATCH /api/v1/stock/parts/{id}"""
    name: Optional[str] = None
    category: Optional[str] = None


class PartResponse(PartBase):
    """GET /api/v1/stock/parts"""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class StockAddRequest(BaseModel):
    """POST /api/v1/stock/add"""
    name: str
    category: str
    quantity: int
    purchase_price: float
    sale_price: float


class StockUseRequest(BaseModel):
    """POST /api/v1/stock/use/{id}"""
    quantity: int = 1
    tracking_no: Optional[str] = None


class StockMovementCreate(BaseModel):
    """POST /api/v1/stock/movements"""
    part_id: int
    type: str = Field(..., description="GİRİŞ, ÇIKIŞ, DÜZELTME")
    amount: int
    current_stock: int
    description: Optional[str] = None


class StockMovementResponse(BaseModel):
    """GET /api/v1/stock/history"""
    id: int
    part_id: int
    type: str
    amount: int
    current_stock: int
    description: Optional[str] = None
    date: datetime
    user: Optional[str] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# ACCOUNTING SCHEMAS
# ============================================================================

class TransactionBase(BaseModel):
    """Base transaction data"""
    type: TransactionTypeEnum
    category: str
    amount: float
    description: Optional[str] = None
    date: date


class TransactionCreate(TransactionBase):
    """POST /api/v1/accounting/transactions"""
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None


class TransactionUpdate(TransactionBase):
    """PATCH /api/v1/accounting/transactions/{id}"""
    type: Optional[TransactionTypeEnum] = None
    category: Optional[str] = None
    amount: Optional[float] = None


class TransactionResponse(TransactionBase):
    """GET /api/v1/accounting/transactions"""
    id: int
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    is_invoiced: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    """GET /api/v1/accounting/balance"""
    total_income: float
    total_expense: float
    balance: float


class BulkInvoiceRequest(BaseModel):
    """POST /api/v1/accounting/bulk-invoice"""
    transaction_ids: Optional[List[int]] = []
    device_ids: Optional[List[int]] = []


class BankAccountCreate(BaseModel):
    """POST /api/v1/accounting/bank-accounts"""
    bank_name: str
    branch_name: Optional[str] = None
    account_name: Optional[str] = None
    account_no: Optional[str] = None
    iban: Optional[str] = None


class BankAccountResponse(BaseModel):
    """GET /api/v1/accounting/bank-accounts"""
    id: int
    bank_name: str
    branch_name: Optional[str] = None
    account_name: Optional[str] = None
    account_no: Optional[str] = None
    iban: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# PERSONNEL SCHEMAS
# ============================================================================

class PersonnelBase(BaseModel):
    """Base personnel data"""
    name: str
    role: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    department: Optional[str] = None
    salary: float = 0.0
    commission_rate: float = 0.0


class PersonnelCreate(PersonnelBase):
    """POST /api/v1/personnel"""
    tc_no: Optional[str] = None
    password: Optional[str] = None


class PersonnelUpdate(PersonnelBase):
    """PATCH /api/v1/personnel/{id}"""
    name: Optional[str] = None
    role: Optional[str] = None


class PersonnelResponse(PersonnelBase):
    """GET /api/v1/personnel"""
    id: int
    tc_no: Optional[str] = None
    start_date: Optional[date] = None
    is_active: bool
    performance_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class PersonnelPerformance(BaseModel):
    """GET /api/v1/personnel/performance"""
    name: str
    jobs_completed: int
    total_revenue: float


class PersonnelProductivity(BaseModel):
    """GET /api/v1/personnel/productivity"""
    name: str
    jobs: int
    volume: float
    score: float


# ============================================================================
# APPOINTMENT & REMINDER SCHEMAS
# ============================================================================

class AppointmentBase(BaseModel):
    """Base appointment data"""
    customer_name: str
    phone: Optional[str] = None
    date: date
    time: time
    description: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """POST /api/v1/appointments"""
    personnel: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    device: Optional[str] = None
    urgency: Optional[str] = None


class AppointmentUpdate(BaseModel):
    """PATCH /api/v1/appointments/{id}"""
    status: Optional[AppointmentStatusEnum] = None
    date: Optional[date] = None
    time: Optional[time] = None


class AppointmentResponse(AppointmentBase):
    """GET /api/v1/appointments"""
    id: int
    personnel: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ReminderCreate(BaseModel):
    """POST /api/v1/reminders"""
    title: str
    description: Optional[str] = None
    personnel_id: Optional[int] = None
    date: datetime


class ReminderResponse(BaseModel):
    """GET /api/v1/reminders"""
    id: int
    title: str
    description: Optional[str] = None
    personnel: Optional[str] = None
    date: datetime
    status: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# CONTRACT SCHEMAS
# ============================================================================

class ContractBase(BaseModel):
    """Base contract data"""
    customer_id: int
    title: str
    contract_type: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    price: float


class ContractCreate(ContractBase):
    """POST /api/v1/contracts"""
    pass


class ContractResponse(ContractBase):
    """GET /api/v1/contracts"""
    id: int
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# SETTINGS & SERVICES SCHEMAS
# ============================================================================

class SettingUpdate(BaseModel):
    """POST /api/v1/settings/{key}"""
    value: str


class SettingResponse(BaseModel):
    """GET /api/v1/settings/{key}"""
    key: str
    value: str


class ServiceCreate(BaseModel):
    """POST /api/v1/services"""
    name: str
    price: float
    description: Optional[str] = None


class ServiceUpdate(BaseModel):
    """PATCH /api/v1/services/{id}"""
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None


class ServiceResponse(BaseModel):
    """GET /api/v1/services"""
    id: int
    name: str
    price: float
    description: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# REPORTS & STATS SCHEMAS
# ============================================================================

class DashboardStats(BaseModel):
    """GET /api/v1/reports/stats"""
    Beklemede: int = 0
    Tamirde: int = 0
    Tamamlandı: int = 0
    total: int = 0


class SummaryData(BaseModel):
    """GET /api/v1/reports/summary"""
    daily_turnover: float
    total_receivables: float
    today_new_jobs: int
    brand_distribution: dict
    critical_stock_count: int
    total_inventory_value: float
    unique_customers: int


class ExportRequest(BaseModel):
    """POST /api/v1/reports/export/{table}"""
    file_path: str


# ============================================================================
# AUDIT & LOGS SCHEMAS
# ============================================================================

class AuditLogResponse(BaseModel):
    """GET /api/v1/audit-logs"""
    id: int
    user_id: Optional[str] = None
    table_name: str
    action: str
    details: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# AI / JARVIS SCHEMAS
# ============================================================================

class JarvisNotificationResponse(BaseModel):
    """GET /api/v1/jarvis/notifications"""
    id: int
    message: str
    type: str
    is_critical: bool
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class JarvisQueryRequest(BaseModel):
    """POST /api/v1/jarvis/query"""
    query: str


class JarvisQueryResponse(BaseModel):
    """Response for Jarvis query"""
    answer: str
    data: Optional[dict] = None


# ============================================================================
# TICKET & KNOWLEDGE BASE SCHEMAS
# ============================================================================

class TicketCreate(BaseModel):
    """POST /api/v1/tickets"""
    customer_id: int
    subject: str
    description: str
    priority: str = "Medium"


class TicketUpdate(BaseModel):
    """PATCH /api/v1/tickets/{id}"""
    status: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None


class TicketResponse(BaseModel):
    """GET /api/v1/tickets"""
    id: int
    customer_id: int
    subject: str
    description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class KBArticleCreate(BaseModel):
    """POST /api/v1/kb"""
    title: str
    content: str
    tags: Optional[str] = None


class KBArticleResponse(BaseModel):
    """GET /api/v1/kb"""
    id: int
    title: str
    content: str
    tags: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
