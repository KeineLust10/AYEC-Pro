# -*- coding: utf-8 -*-


from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sqlite3
import json
import os
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware

from src.database import Database
from src.utils.navigation_config import build_web_navigation
from src.utils.path_helper import PathHelper
from src.utils.system_config import SystemConfig

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Helper
DB_PATH = PathHelper.get_db_path("ayecpro.db")

try:
    db = Database()
except Exception:
    db = None

class DB:
    @staticmethod
    def get_conn():
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20)
        conn.text_factory = str  # UTF-8 desteği
        return conn

# Güvenli Sorgu Çalıştırıcı
def execute_query(query, params=(), commit=False):
    conn = DB.get_conn()
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
            last_id = cur.lastrowid
            return last_id
        else:
            if query.strip().upper().startswith("SELECT"):
                return [dict(r) for r in cur.fetchall()]
            return None
    except Exception as e:
        print(f"DB Error: {e} \nQuery: {query} \nParams: {params}")
        raise e # Endpoint will catch this
    finally:
        conn.close()

# Models
class ServiceDefinitionModel(BaseModel):
    service_name: str
    category: str
    price: float
    duration: Optional[int] = None
    description: Optional[str] = None

class CustomerModel(BaseModel):
    name: str
    phone: str
    email: Optional[str] = ""
    address: Optional[str] = ""
    tax_id: Optional[str] = ""

# DÜZELTİLDİ: Frontend ile uyumlu PartModel
class PartModel(BaseModel):
    part_name: str 
    stock: int
    min_stock: int
    price: float

class ProcessItemModel(BaseModel):
    id: int
    name: str # DB'de part_name veya ürün adı
    price: float
    qty: int # DB'de quantity

class ProcessWizardModel(BaseModel):
    customer_id: int
    customer_name: str
    process_date: str
    items: List[ProcessItemModel]

class ReminderModel(BaseModel):
    title: str
    description: str
    remind_date: str
    customer_id: Optional[int] = None
    service_id: Optional[int] = None

class AppointmentModel(BaseModel):
    customer_name: str
    phone: str
    appointment_date: str
    appointment_time: str
    service_type: str
    notes: Optional[str] = None

class CustomerServiceModel(BaseModel):
    customer_id: int
    service_id: int
    service_name: str
    quantity: int
    unit_price: float
    total_amount: float
    notes: Optional[str] = None
    date: str

class ContractModel(BaseModel):
    contract_no: str
    customer_id: int
    contract_type: str
    start_date: str
    end_date: str
    amount: float
    status: str

class AccountingModel(BaseModel):
    date: str
    description: str
    category: str
    type: str 
    amount: float

class PersonnelModel(BaseModel):
    name: str
    role: str
    phone: str
    email: str
    salary: float

class AnnouncementModel(BaseModel):
    title: str
    message: str
    send_sms: bool
    send_email: bool
    target_group: str

class RemoteCommandModel(BaseModel):
    device_id: str
    command_type: str
    parameters: Dict[str, Any] = {}

# ==================== ENDPOINTS ====================

@app.get("/api/navigation")
def get_navigation():
    sector = SystemConfig.get_current_sector(db) if db else "teknik_servis"
    return {
        "sector": sector,
        "groups": build_web_navigation(db, sector),
    }

@app.get("/api/dashboard")
def get_dashboard_stats():
    try:
        active = execute_query("SELECT COUNT(*) as c FROM devices WHERE status != 'Teslim Edildi'")[0]['c']
        today = execute_query("SELECT COUNT(*) as c FROM devices WHERE date(created_at) = date('now')")[0]['c']
        cust = execute_query("SELECT COUNT(*) as c FROM customers")[0]['c']
        # Stock tablosu düzeltildi: quantity ve min_stock
        stock = execute_query("SELECT COUNT(*) as c FROM stock WHERE quantity <= min_stock")[0]['c']
        return {"active_services": active, "today_new": today, "total_customers": cust, "low_stock": stock}
    except Exception as e:
        print(f"Dash Err: {e}")
        return {"active_services":0, "today_new":0, "total_customers":0, "low_stock":0}

# --- CUSTOMERS ---
@app.get("/api/customers")
def get_customers():
    return execute_query("SELECT * FROM customers ORDER BY created_at DESC")

@app.post("/api/customers")
def create_customer(c: CustomerModel):
    try:
        cust_id = execute_query("INSERT INTO customers (name, phone, email, address, tax_id) VALUES (?, ?, ?, ?, ?)", 
                            (c.name, c.phone, c.email, c.address, c.tax_id), commit=True)
        return {"success": True, "id": cust_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/customers/{cid}")
def update_customer(cid: int, c: CustomerModel):
    execute_query("UPDATE customers SET name=?, phone=?, email=?, address=?, tax_id=? WHERE id=?", 
                  (c.name, c.phone, c.email, c.address, c.tax_id, cid), commit=True)
    return {"success": True}

@app.delete("/api/customers/{cid}")
def delete_customer(cid: int):
    execute_query("DELETE FROM customers WHERE id=?", (cid,), commit=True)
    return {"success": True}

@app.get("/api/customers/{cid}/balance")
def get_customer_balance(cid: int):
    """Müşterinin toplam borç bakiyesini hesapla"""
    try:
        conn = DB.get_conn()
        cursor = conn.cursor()
        
        # 1. Müşteri adını al
        cursor.execute("SELECT name FROM customers WHERE id = ?", (cid,))
        res = cursor.fetchone()
        customer_name = res[0] if res else None
        
        total_debt = 0.0
        
        # 2. Servis borçları (devices + used_parts)
        if customer_name:
            cursor.execute("SELECT tracking_no, labor_cost FROM devices WHERE customer_id = ? OR customer_name = ?", (cid, customer_name))
        else:
            cursor.execute("SELECT tracking_no, labor_cost FROM devices WHERE customer_id = ?", (cid,))
        
        devices = cursor.fetchall()
        for tracking_no, labor in devices:
            total_debt += (labor or 0.0)
            cursor.execute("SELECT SUM(price * quantity) FROM used_parts WHERE tracking_no = ?", (tracking_no,))
            part_sum = cursor.fetchone()[0]
            total_debt += (part_sum or 0.0)
        
        # 3. Customer Services (Yeni eklenen hizmetler)
        cursor.execute("SELECT SUM(total_amount) FROM customer_services WHERE customer_id = ?", (cid,))
        service_sum = cursor.fetchone()[0]
        total_debt += (service_sum or 0.0)
        
        # 4. Accounting tablosundan satışlar
        if customer_name:
            cursor.execute("""
                SELECT SUM(amount) FROM accounting 
                WHERE (customer_id = ? OR customer_name = ?) 
                AND type = 'Gelir' AND category = 'Satış'
                AND description NOT LIKE 'Tahsilat%'
            """, (cid, customer_name))
        else:
            cursor.execute("""
                SELECT SUM(amount) FROM accounting 
                WHERE customer_id = ? AND type = 'Gelir' AND category = 'Satış'
                AND description NOT LIKE 'Tahsilat%'
            """, (cid,))
        total_sales = cursor.fetchone()[0] or 0.0
        
        # 5. Tahsilatlar
        if customer_name:
            cursor.execute("""
                SELECT SUM(amount) FROM accounting 
                WHERE (customer_id = ? OR customer_name = ?) 
                AND type = 'Gelir' 
                AND (category = 'Tahsilat' OR description LIKE 'Tahsilat%')
            """, (cid, customer_name))
        else:
            cursor.execute("""
                SELECT SUM(amount) FROM accounting 
                WHERE customer_id = ? AND type = 'Gelir' 
                AND (category = 'Tahsilat' OR description LIKE 'Tahsilat%')
            """, (cid,))
        total_paid = cursor.fetchone()[0] or 0.0
        
        balance = (total_debt + total_sales) - total_paid
        conn.close()
        
        return {"balance": balance}
    except Exception as e:
        print(f"Balance Error: {e}")
        return {"balance": 0.0}

@app.get("/api/customers/{cid}/history")
def get_customer_history_api(cid: int):
    """Müşterinin tüm geçmişini (Cihaz, Hizmet, Tahsilat) getir"""
    try:
        conn = DB.get_conn()
        cursor = conn.cursor()
        history = []
        
        # 1. Cihaz Servisleri
        cursor.execute("""
            SELECT id, tracking_no, entry_date, device_brand || ' ' || device_model, status, labor_cost 
            FROM devices WHERE customer_id = ?
        """, (cid,))
        for row in cursor.fetchall():
            # Parça maliyetini hesapla
            cursor.execute("SELECT SUM(price * quantity) FROM used_parts WHERE tracking_no = ?", (row['tracking_no'],))
            part_cost = cursor.fetchone()[0] or 0.0
            
            history.append({
                "id": f"device_{row['id']}",
                "date": row['entry_date'],
                "type": "Cihaz Servisi",
                "description": f"{row['tracking_no']} - {row[3]}",
                "status": row['status'],
                "amount": (row['labor_cost'] or 0.0) + part_cost,
                "notes": "Cihaz Kaydı"
            })
            
        # 2. Ekstra Hizmetler (Customer Services)
        cursor.execute("""
            SELECT id, date, service_name, quantity, total_amount, notes 
            FROM customer_services WHERE customer_id = ?
        """, (cid,))
        for row in cursor.fetchall():
            history.append({
                "id": f"service_{row['id']}",
                "date": row['date'],
                "type": "Hizmet",
                "description": f"{row['service_name']} (x{row['quantity']})",
                "status": "Tamamlandı",
                "amount": row['total_amount'],
                "notes": row['notes']
            })
            
        # 3. Tahsilatlar (Accounting)
        cursor.execute("""
            SELECT id, date, category, description, amount 
            FROM accounting 
            WHERE customer_id = ? AND type = 'Gelir' AND (category = 'Tahsilat' OR description LIKE 'Tahsilat%')
        """, (cid,))
        for row in cursor.fetchall():
            history.append({
                "id": f"payment_{row['id']}",
                "date": row['date'],
                "type": "Tahsilat",
                "description": row['description'],
                "status": "Ödendi",
                "amount": row['amount'],
                "notes": row['category']
            })

        conn.close()
        
        # Tarihe göre sırala (Yeniden eskiye)
        history.sort(key=lambda x: x['date'] or '', reverse=True)
        return history
    except Exception as e:
        print(f"History Error: {e}")
        return []

# --- SERVICES (DEVICES) ---
@app.get("/api/services")
def get_services():
    return execute_query("SELECT *, id as tracking_no FROM devices ORDER BY created_at DESC LIMIT 50")

@app.put("/api/services/{service_id}/status")
def update_status(service_id: int, data: Dict[str, str]):
    execute_query("UPDATE devices SET status = ? WHERE id = ?", (data.get('status'), service_id), commit=True)
    return {"success": True}

# --- PROCESS WIZARD ---
@app.post("/api/process-wizard/save")
def save_process_wizard(data: ProcessWizardModel):
    conn = DB.get_conn()
    try:
        cur = conn.cursor()
        
        # 1. SRV No
        cur.execute("SELECT MAX(id) as max_id FROM devices")
        row = cur.fetchone()
        max_id = row[0] if row and row[0] else 0
        tracking_no = f"SRV{max_id + 1:05d}"
        
        desc_str = ", ".join([f"{item.name} ({item.qty}x)" for item in data.items])
        
        # 2. Insert Device (customer_id dahil)
        # customer_id tablosunda yoksa execute hata verir, ama fix_stock_db.py ile ekledik.
        try:
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status, customer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, data.customer_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", data.process_date, "Yeni Kayıt", data.customer_id
            ))
        except sqlite3.OperationalError:
            # Fallback if customer_id missing
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, data.customer_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", data.process_date, "Yeni Kayıt"
            ))

        srv_id = cur.lastrowid
        
        # 3. Insert Used Parts (quantity eklendi)
        for item in data.items:
            cur.execute("""
                INSERT INTO used_parts (tracking_no, part_name, price, quantity, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tracking_no, item.name, item.price, item.qty, datetime.now().isoformat()))
            
        conn.commit()
        return {"success": True, "tracking_no": tracking_no, "service_id": srv_id}
    except Exception as e:
        error_msg = str(e)
        print(f"WIZARD ERROR: {error_msg}")
        
        # Log error to file for diagnosis
        try:
            with open("wizard_error.log", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}] ERROR: {error_msg}\n")
                import traceback
                f.write(traceback.format_exc() + "\n")
        except: pass
        
        raise HTTPException(status_code=500, detail=f"Sunucu Hatası: {error_msg}")
    finally:
        conn.close()

# --- SERVICE DEFINITIONS ---
@app.get("/api/service-definitions")
def get_defs():
    return execute_query("SELECT * FROM service_definitions ORDER BY service_name")

@app.post("/api/service-definitions")
def create_def(d: ServiceDefinitionModel):
    try:
        new_id = execute_query("""
            INSERT INTO service_definitions (service_name, category, price, duration, description)
            VALUES (?, ?, ?, ?, ?)
        """, (d.service_name, d.category, d.price, d.duration, d.description), commit=True)
        return {"success": True, "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/service-definitions/{sid}")
def update_def(sid: int, d: ServiceDefinitionModel):
    try:
        execute_query("""
            UPDATE service_definitions SET service_name=?, category=?, price=?, duration=?, description=? WHERE id=?
        """, (d.service_name, d.category, d.price, d.duration, d.description, sid), commit=True)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/service-definitions/{sid}")
def delete_def(sid: int):
    execute_query("DELETE FROM service_definitions WHERE id=?", (sid,), commit=True)
    return {"success": True}

# --- CUSTOMER SERVICES ---
@app.post("/api/customer-services")
def add_customer_service(cs: CustomerServiceModel):
    try:
        new_id = execute_query("""
            INSERT INTO customer_services (customer_id, service_id, service_name, quantity, unit_price, total_amount, notes, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (cs.customer_id, cs.service_id, cs.service_name, cs.quantity, cs.unit_price, cs.total_amount, cs.notes, cs.date), commit=True)
        return {"success": True, "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/customer-services/{customer_id}")
def get_customer_services(customer_id: int):
    return execute_query("SELECT * FROM customer_services WHERE customer_id=? ORDER BY date DESC", (customer_id,))


# --- STOCK (PARTS) - FIXED SCHEMA ---
@app.get("/api/parts")
def get_parts():
    # parts tablosundan veri çek
    return execute_query("SELECT id, name as part_name, stock, min_stock, price, code, category FROM parts ORDER BY name")

@app.post("/api/parts")
def create_part(p: PartModel):
    try:
        # parts tablosuna ekle (name, stock, min_stock, price)
        pid = execute_query("INSERT INTO parts (name, stock, min_stock, price) VALUES (?, ?, ?, ?)", 
                            (p.part_name, p.stock, p.min_stock, p.price), commit=True)
        return {"success": True, "id": pid}
    except Exception as e:
        print(f"PART ERR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ACCOUNTING ---
@app.get("/api/accounting")
def get_accounting():
    try: return execute_query("SELECT * FROM accounting_records ORDER BY date DESC LIMIT 100")
    except: return []

@app.post("/api/accounting")
def create_accounting(a: AccountingModel):
    aid = execute_query("INSERT INTO accounting_records (date, description, category, type, amount) VALUES (?, ?, ?, ?, ?)",
                  (a.date, a.description, a.category, a.type, a.amount), commit=True)
    return {"success": True, "id": aid}

# --- PERSONNEL ---
@app.get("/api/personnel")
def get_personnel():
    try: return execute_query("SELECT * FROM personnel ORDER BY name")
    except: return []

@app.post("/api/personnel")
def create_personnel(p: PersonnelModel):
    pid = execute_query("INSERT INTO personnel (name, role, phone, email, salary) VALUES (?, ?, ?, ?, ?)",
                  (p.name, p.role, p.phone, p.email, p.salary), commit=True)
    return {"success": True, "id": pid}

# --- CONTRACTS, APPOINTMENTS, LOGISTICS ---
@app.get("/api/contracts")
def get_contracts():
    try: return execute_query("SELECT * FROM contracts ORDER BY start_date DESC")
    except: return []

@app.get("/api/appointments")
def get_appointments():
    try: return execute_query("SELECT * FROM appointments ORDER BY date, time")
    except: return []

@app.post("/api/appointments")
def create_appointment(a: AppointmentModel):
    try:
        # Status defaulting to 'Bekliyor'
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Combine type and notes for description if needed, or just keep it simple
        description = f"{a.service_type}"
        if a.notes:
            description += f" - {a.notes}"
        
        # Schema uses 'type' for service type, and 'notes' for notes
        appt_id = execute_query("""
            INSERT INTO appointments (customer_name, phone, date, time, customer_id, description, status, created_at, type, notes) 
            VALUES (?, ?, ?, ?, NULL, ?, 'Bekliyor', ?, ?, ?)
        """, (a.customer_name, a.phone, a.appointment_date, a.appointment_time, description, created_at, a.service_type, a.notes), commit=True)
        return {"success": True, "id": appt_id}
    except Exception as e:
        print(f"Appointment Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/appointments/{aid}/status")
def update_appointment_status(aid: int, data: Dict[str, str]):
    try:
        execute_query("UPDATE appointments SET status=? WHERE id=?", (data.get('status'), aid), commit=True)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logistics")
def get_logistics():
    try: return execute_query("SELECT * FROM logistics ORDER BY date DESC")
    except: return []

@app.get("/api/field-map")
def get_field_map():
    try: return execute_query("SELECT * FROM field_operations")
    except: return []

@app.get("/api/logs")
def get_logs():
    try: return execute_query("SELECT * FROM system_logs ORDER BY timestamp DESC LIMIT 100")
    except: return []
    
@app.get("/api/support")
def get_support():
    return [{"ticket_id": 101, "subject": "Yazıcı Bağlantı Hatası", "status": "Açık"}, {"ticket_id": 102, "subject": "VPN Kurulumu", "status": "Kapalı"}]

# --- REMOTE ---
remote_devices = {}
@app.post("/api/remote/heartbeat")
def heartbeat(data: Dict[str, Any]):
    return {"success": True}

# --- STATIC FILES ---
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static"), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("PREMIUM BULUT BACKEND v3.2 (SCHEMA FIXED)")
    uvicorn.run(app, host="0.0.0.0", port=8001)

