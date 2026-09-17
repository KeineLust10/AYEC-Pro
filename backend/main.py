"""
FastAPI Main Application
AYEC Pro - Web Backend

Tüm Desktop fonksiyonlarını REST API'ye dönüştürür
"""
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db, init_db, engine
from app.models import models
from app.core.security import verify_token
from app.db.database import SessionLocal
from app.models.models import AuditLog

# Import routers
from app.api.endpoints import auth, customers, devices, services, reports, stock, accounting, appointments
from app.api.v2 import navigation as navigation_v2
from app.api.v2 import customers as customers_v2
from app.api.v2 import devices as devices_v2
from app.api.v2 import service_workflow as workflow_v2
from app.api.v2 import finance as finance_v2
from app.api.v2 import reports as reports_v2
from app.api.v2 import settings as settings_v2

settings = get_settings()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AYEC Pro Teknik Servis Yönetimi - REST API",
    debug=settings.DEBUG
)

# CORS Middleware
allowed_origins = settings.ALLOWED_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

from fastapi.staticfiles import StaticFiles
import os

@app.get("/")
def root():
    """API Root - Health Check"""
    return {
        "message": "AYEC Pro API is running",
        "version": settings.APP_VERSION,
        "status": "healthy",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Ensure static files directory exists and mount it
# In a compiled PyInstaller build, the root path might change
import sys
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_path = os.path.join(base_path, "Web_Arayuzu", "web")

if os.path.exists(frontend_path):
    app.mount("/web", StaticFiles(directory=frontend_path, html=True), name="web_interface")
    print(f"Mounted web interface from {frontend_path} at /web")
else:
    print(f"Warning: Web interface directory not found at {frontend_path}")


@app.get("/api/v1/health")
def health_check():
    """
    API Health Check
    
    Desktop: N/A (Web only)
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT
    }


# ============================================================================
# REGISTER API ROUTERS
# ============================================================================

# Authentication
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)

# Customers (Müşteri Yönetimi)
app.include_router(
    customers.router,
    prefix="/api/v1/customers",
    tags=["Customers"]
)

# Devices/Services (Yeni İşlem, Servis Takibi)
app.include_router(
    devices.router,
    prefix="/api/v1/devices",
    tags=["Devices & Services"]
)

# Services (Hizmet Tanımları)
app.include_router(
    services.router,
    prefix="/api/v1/services",
    tags=["Service Definitions"]
)

# Stock (Stok Yönetimi)
app.include_router(
    stock.router,
    prefix="/api/v1/stock",
    tags=["Stock Management"]
)

# Accounting (Muhasebe)
app.include_router(
    accounting.router,
    prefix="/api/v1/accounting",
    tags=["Accounting"]
)

# Appointments (Randevu Takvimi)
app.include_router(
    appointments.router,
    prefix="/api/v1/appointments",
    tags=["Appointments"]
)

# Reports & Dashboard (Dashboard, Raporlar)
app.include_router(
    reports.router,
    prefix="/api/v1/reports",
    tags=["Reports & Dashboard"]
)


@app.middleware("http")
async def audit_request_middleware(request, call_next):
    response = await call_next(request)

    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return response
    if not request.url.path.startswith("/api/"):
        return response
    if request.url.path in {"/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/refresh"}:
        return response

    user_id = "anonymous"
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        try:
            payload = verify_token(token)
            user_id = payload.get("username") or str(payload.get("user_id")) or "anonymous"
        except Exception:
            user_id = "invalid_token"

    try:
        db = SessionLocal()
        table_name = request.url.path.strip("/").split("/")[-1][:100] or "api"
        db.add(
            AuditLog(
                user_id=user_id,
                table_name=table_name,
                action=request.method,
                details=f"path={request.url.path} status={response.status_code}",
            )
        )
        db.commit()
    except Exception:
        pass
    finally:
        try:
            db.close()
        except Exception:
            pass

    return response

# Navigation & migration helpers (v2)
app.include_router(
    navigation_v2.router,
    prefix="/api/v2/navigation",
    tags=["Navigation V2"]
)

app.include_router(
    customers_v2.router,
    prefix="/api/v2/customers",
    tags=["Customers V2"]
)

app.include_router(
    devices_v2.router,
    prefix="/api/v2/devices",
    tags=["Devices V2"]
)

app.include_router(
    workflow_v2.router,
    prefix="/api/v2/service-workflow",
    tags=["Service Workflow V2"]
)

app.include_router(
    finance_v2.router,
    prefix="/api/v2/finance",
    tags=["Finance V2"]
)

app.include_router(
    reports_v2.router,
    prefix="/api/v2/reports",
    tags=["Reports V2"]
)

app.include_router(
    settings_v2.router,
    prefix="/api/v2/settings",
    tags=["Settings V2"]
)


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    print(f"ERROR: {exc}")
    import traceback
    traceback.print_exc()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "message": "Internal Server Error"
        }
    )


# ============================================================================
# STARTUP EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("=" * 80)
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Database: {settings.DATABASE_URL}")
    print(f"CORS Origins: {settings.ALLOWED_ORIGINS}")
    print("=" * 80)
    
    # Initialize database
    init_db()
    print("[OK] Database initialized")
    
    # Create default admin user if not exists
    try:
        from app.models.models import User, UserRole
        from app.core.security import get_password_hash
        import os

        db = next(get_db())
        admin_exists = db.query(User).filter(User.username == "admin").first()

        if not admin_exists:
            # Use env var or fall back to MASTER2026! (change in production)
            admin_password = os.environ.get("AYEC_ADMIN_PASSWORD", "MASTER2026!")[:72]
            admin_user = User(
                username="admin",
                password=get_password_hash(admin_password),
                role=UserRole.ADMIN
            )
            db.add(admin_user)
            db.commit()
            print("[OK] Default admin user created (username: admin)")
        else:
            print("[OK] Admin user already exists")

        db.close()
    except Exception as e:
        print(f"[WARNING] Could not create admin user: {e}")



@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("Shutting down AYEC Pro API...")


# ============================================================================
# API DOCUMENTATION METADATA
# ============================================================================

"""
API ENDPOINT SUMMARY (Desktop â†’ Web Mapping)

AUTHENTICATION:
  POST   /api/v1/auth/login          â†’ database.authenticate_user()
  POST   /api/v1/auth/register       â†’ database.add_user()
  GET    /api/v1/auth/me             â†’ Get current user

CUSTOMERS (16 endpoints):
  GET    /api/v1/customers            â†’ database.get_customers()
  POST   /api/v1/customers            â†’ database.add_customer()
  GET    /api/v1/customers/search     â†’ database.search_customers()
  GET    /api/v1/customers/{id}       â†’ database.get_customer_by_id()
  PUT    /api/v1/customers/{id}       â†’ database.update_customer()
  DELETE /api/v1/customers/{id}       â†’ database.delete_customer()
  GET    /api/v1/customers/{id}/balance       â†’ database.get_customer_balance()
  GET    /api/v1/customers/{id}/history       â†’ database.get_customer_history()
  GET    /api/v1/customers/{id}/summary       â†’ database.get_customer_history_summary()
  GET    /api/v1/customers/debt               â†’ database.get_customers_with_debt()
  POST   /api/v1/customers/{id}/notes         â†’ database.add_customer_note()
  GET    /api/v1/customers/{id}/notes         â†’ database.get_customer_notes()
  DELETE /api/v1/customers/notes/{id}         â†’ database.delete_customer_note()

DEVICES/SERVICES (20 endpoints):
  GET    /api/v1/devices                      â†’ database.get_all_devices()
  POST   /api/v1/devices                      â†’ database.add_device()
  GET    /api/v1/devices/search               â†’ database.search_devices()
  POST   /api/v1/devices/advanced-search      â†’ database.advanced_search()
  GET    /api/v1/devices/status/{status}      â†’ database.get_devices_by_status()
  GET    /api/v1/devices/recent               â†’ database.get_recent_services()
  GET    /api/v1/devices/critical             â†’ database.get_critical_devices()
  GET    /api/v1/devices/{tracking_no}        â†’ database.get_device()
  PUT    /api/v1/devices/{tracking_no}        â†’ database.update_device()
  DELETE /api/v1/devices/{tracking_no}        â†’ database.delete_device()
  PATCH  /api/v1/devices/{tracking_no}/status â†’ database.update_status()
  PATCH  /api/v1/devices/{tracking_no}/financials â†’ database.update_financials()
  POST   /api/v1/devices/{tracking_no}/parts  â†’ database.add_used_part()
  GET    /api/v1/devices/{tracking_no}/parts  â†’ database.get_used_parts()
  POST   /api/v1/devices/{tracking_no}/tests  â†’ database.add_device_test()
  GET    /api/v1/devices/{tracking_no}/tests  â†’ database.get_device_tests()
  POST   /api/v1/devices/{tracking_no}/photos â†’ Upload photo
  GET    /api/v1/devices/{tracking_no}/logs   â†’ database.get_logs()

SERVICES (5 endpoints):
  GET    /api/v1/services           â†’ database.get_services_list()
  POST   /api/v1/services           â†’ database.add_service()
  PUT    /api/v1/services/{id}      â†’ database.update_service()
  DELETE /api/v1/services/{id}      â†’ database.delete_service()
  POST   /api/v1/services/load-ato  â†’ database.load_ato_2025_services()

REPORTS & DASHBOARD (10 endpoints):
  GET    /api/v1/reports/stats              â†’ database.get_stats()
  GET    /api/v1/reports/summary            â†’ database.get_summary_data()
  GET    /api/v1/reports/weekly-stats       â†’ database.get_weekly_stats()
  GET    /api/v1/reports/popular-parts      â†’ database.get_popular_parts()
  GET    /api/v1/reports/performance        â†’ database.get_personnel_performance()
  GET    /api/v1/reports/customer-balances  â†’ database.get_customer_balances()
  GET    /api/v1/reports/cari-list          â†’ database.get_cari_list()
  GET    /api/v1/reports/monthly-revenue    â†’ Monthly revenue chart

TOTAL: 51 Critical Endpoints Implemented
"""


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )

