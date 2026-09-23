"""Reset business data and create a coherent AYEC Pro demo dataset."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


KEEP = {
    "_migrations", "settings", "internal_settings", "license_info",
    "company_info", "sector_presets", "app_labels", "exchange_rates",
    "device_brands", "device_models", "sqlite_sequence", "sqlite_stat1",
}


def ins(c, table, values):
    schema_columns = {
        row[1] for row in c.execute(f'PRAGMA table_info("{table}")')
    }
    values = {key: value for key, value in values.items() if key in schema_columns}
    if not values:
        raise RuntimeError(f"No compatible columns found for table: {table}")
    cols = list(values)
    marks = ",".join("?" for _ in cols)
    cur = c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({marks})", tuple(values.values()))
    return cur.lastrowid


def reset(c):
    c.execute("PRAGMA foreign_keys=OFF")
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for table in tables:
        if table not in KEEP and not table.startswith("sqlite_"):
            c.execute(f'DELETE FROM "{table}"')
    c.execute("PRAGMA foreign_keys=ON")


def seed(c):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    customers = []
    names = [
        "Ahmet Yilmaz", "Ayse Demir", "Mehmet Kaya", "Zeynep Celik", "Okan Yilmaz",
        "Esra Yilmaz", "Deniz Yildiz", "Tolga Acar", "Selin Yilmaz", "Kaan Yilmaz",
        "Can Yilmaz", "Elif Yilmaz", "Murat Arslan", "Derya Aydin", "Burak Sahin",
        "Seda Koc", "Hakan Kurt", "Nehir Ozkan", "Berk Eren", "Ece Tas",
        "Gokhan Polat", "Pelin Aksoy", "Emre Uslu", "Cemre Ekin", "Baris Cevik",
    ]
    for i, name in enumerate(names, 1):
        customers.append(ins(c, "customers", {
            "name": name, "phone": f"0555000{i:04d}", "email": f"demo{i}@example.test",
            "type": "Bireysel", "address": f"Demo Mahallesi No: {i}",
            "city": "Istanbul", "created_at": now, "term_days": 30,
            "limit_amount": 50000, "is_deleted": 0,
        }))

    categories = [
        ("Akilli Ev Sistemleri", "AES", "TRY"),
        ("Bilgisayar", "PC", "USD"),
        ("Guvenlik Sistemleri", "GUV", "EUR"),
    ]
    part_ids = []
    for category, prefix, currency in categories:
        for i in range(1, 31):
            price = round((250 + i * 37) if currency == "TRY" else (35 + i * 4.5), 2)
            part_ids.append(ins(c, "parts", {
                "name": f"{category} Urun {i:02d}", "part_name": f"{category} Urun {i:02d}",
                "stock": 50 + i, "price": price, "purchase_price": round(price * .65, 2),
                "currency": currency, "code": f"{prefix}-{i:03d}", "barcode": f"869000{len(part_ids)+1:06d}",
                "category": category, "min_stock": 10, "description": "Demo stok urunu",
                "created_at": now, "unit": "Adet", "is_deleted": 0,
            }))

    personnel = []
    for i, (name, role, dep) in enumerate([
        ("Ali Teknik", "Teknisyen", "Teknik Servis"), ("Banu Finans", "Muhasebe", "Finans"),
        ("Cihan Proje", "Proje Yoneticisi", "Projeler"), ("Dilan Satis", "Satis", "Satis"),
        ("Eren Depo", "Depo Sorumlusu", "Depo"),
    ], 1):
        personnel.append(ins(c, "personnel", {"name": name, "username": f"demo_user_{i}",
            "password": "demo", "role": role, "phone": f"0544000{i:04d}", "department": dep,
            "created_at": now, "active": 1, "status": "Aktif", "is_deleted": 0}))

    locations = [
        ins(c, "stock_locations", {"name": "Ana Depo", "location_type": "warehouse", "active": 1, "created_at": now}),
        ins(c, "stock_locations", {"name": "Teknisyen Araci", "location_type": "vehicle", "vehicle_plate": "34 AY 001", "personnel_id": personnel[0], "active": 1, "created_at": now}),
        ins(c, "stock_locations", {"name": "Emanet Deposu", "location_type": "warehouse", "active": 1, "created_at": now}),
    ]

    tracking = []
    for i in range(15):
        customer_id = customers[i]
        tno = f"DEMO-SRV-{i+1:04d}"
        cur = ("TRY", "USD", "EUR")[i % 3]
        rate = {"TRY": 1.0, "USD": 40.0, "EUR": 44.0}[cur]
        device_id = ins(c, "devices", {"tracking_no": tno, "customer_name": names[i], "customer_id": customer_id,
            "device_brand": "AYEC", "device_model": f"Test Cihaz {i+1:02d}", "serial_no": f"SN-DEMO-{i+1:04d}",
            "status": "Teslim Edildi" if i % 3 == 0 else "Serviste", "entry_date": now[:10],
            "price": 1000 + i * 100, "device_type": "Elektronik Cihaz", "fault_category": "Bakim",
            "labor_cost": 1200 + i * 50, "cargo_fee": 0, "technician": "Ali Teknik",
            "repair_details": "Bakim, test ve yazilim guncelleme", "created_at": now, "updated_at": now,
            "service_source": "shop", "payment_status": "Bekliyor", "is_deleted": 0})
        tracking.append((tno, customer_id, cur, rate, device_id))
        for j in range(2):
            pid = part_ids[(i * 2 + j) % len(part_ids)]
            prow = c.execute("SELECT name,price,currency FROM parts WHERE id=?", (pid,)).fetchone()
            ins(c, "used_parts", {"tracking_no": tno, "part_id": pid, "part_name": prow[0], "price": prow[1],
                "quantity": 1, "currency": prow[2], "exchange_rate": {"TRY": 1.0, "USD": 40.0, "EUR": 44.0}[prow[2]],
                "price_try": round(prow[1] * {"TRY": 1.0, "USD": 40.0, "EUR": 44.0}[prow[2]], 2),
                "created_at": now, "stock_location_id": locations[0], "is_deleted": 0})
        total = round((1800 + i * 125) / rate, 2)
        ins(c, "currency_transactions", {"customer_id": customer_id, "transaction_type": "DEBIT", "amount": total,
            "currency": cur, "exchange_rate": rate, "try_equivalent": round(total * rate, 2),
            "description": f"Servis borcu {tno}", "tracking_no": tno, "created_at": now,
            "current_balance": -total, "is_invoiced": 0})
        if i % 2 == 0:
            pay = round(total / 2, 2)
            ins(c, "currency_transactions", {"customer_id": customer_id, "transaction_type": "CREDIT", "amount": pay,
                "currency": cur, "exchange_rate": rate, "try_equivalent": round(pay * rate, 2),
                "description": f"Onceki is tahsilati {tno}", "tracking_no": tno + "-PAY", "created_at": now,
                "current_balance": -round(total - pay, 2), "is_invoiced": 0})

    for i in range(10):
        cid = customers[(i + 15) % len(customers)]
        offer_id = ins(c, "offers", {"offer_no": f"TEKLIF-{i+1:04d}", "customer_id": cid, "customer_name": names[(i+15)%25],
            "project_name": f"Demo Proje {i+1:02d}", "currency_code": ("TRY","USD","EUR")[i%3],
            "currency_symbol": ("TL","$","EUR")[i%3], "exchange_rate": (1.0,40.0,44.0)[i%3],
            "subtotal": 5000 + i*250, "total": 5900 + i*295, "total_try": (5900+i*295)*(1 if i%3==0 else (40 if i%3==1 else 44)),
            "status": "Onaylandi" if i%2==0 else "Taslak", "created_by": "Dilan Satis", "created_at": now, "updated_at": now})
        ins(c, "offer_items", {"offer_id": offer_id, "item_id": part_ids[i], "item_type": "part", "description": "Teklif urunu",
            "qty": 2, "unit_price": 500 + i*25, "line_total": 1000 + i*50})

    for i in range(8):
        cid = customers[i]
        ins(c, "appointments", {"customer_name": names[i], "customer_id": cid, "phone": f"0555000{i+1:04d}",
            "date": (datetime.now()+timedelta(days=i+1)).strftime("%Y-%m-%d"), "time": "10:00", "description": "Bakim randevusu",
            "status": "Planlandi", "personnel_id": personnel[0], "personnel_name": "Ali Teknik", "created_at": now, "type": "Servis"})
        project_id = ins(c, "projects", {"name": f"Demo Proje {i+1:02d}", "customer_id": cid, "customer_name": names[i],
            "start_date": now[:10], "end_date": (datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"),
            "budget": 25000+i*1000, "cost": 9000+i*500, "status": "Devam Ediyor", "currency": "TRY",
            "description": "Akilli ev ve guvenlik sistemi kurulum projesi", "created_at": now})
        ins(c, "project_transactions", {"project_id": project_id, "type": "Gelir", "amount": 5000+i*100,
            "category": "Avans", "payment_method": "Banka", "date": now[:10],
            "description": "Proje avans tahsilati", "created_at": now})

    for bank, cur, bal in [("Demo Banka", "TRY", 125000), ("Demo Banka Doviz", "USD", 3500), ("Demo Katilim", "EUR", 2400)]:
        bid = ins(c, "bank_accounts", {"bank_name": bank, "account_holder": "AYEC Demo Firma", "iban": "TR000000000000000000000000",
            "currency": cur, "is_active": 1, "created_at": now, "current_balance": bal, "is_deleted": 0})
        ins(c, "accounting", {"type": "Gelir", "category": "Tahsilat", "amount": 2500, "try_equivalent": bal,
            "currency": cur, "exchange_rate": 1 if cur == "TRY" else (40 if cur == "USD" else 44),
            "original_amount": 2500, "description": "Demo banka tahsilat kaydi", "date": now[:10], "created_at": now,
            "payment_method": "Banka Havalesi", "bank_account_id": bid, "customer_id": customers[0], "customer_name": names[0]})

    for i in range(6):
        ins(c, "checks_notes", {"type": "Cek" if i%2==0 else "Senet", "direction": "Alinan", "portfolio_no": f"PORT-{i+1:04d}",
            "amount": 5000+i*750, "due_date": (datetime.now()+timedelta(days=30+i*15)).strftime("%Y-%m-%d"),
            "issuer": names[i], "recipient": "AYEC Demo Firma", "bank_name": "Demo Banka", "status": "Portfoyde", "created_at": now})

    for i in range(4):
        ins(c, "external_warranty_tracking", {"internal_tracking_no": f"GARANTI-{i+1:04d}", "customer_name": names[i],
            "product_name": f"Garanti Urunu {i+1}", "external_service_name": "Demo Yetkili Servis",
            "status": "Gonderildi", "sent_date": now[:10], "created_at": now})
        ins(c, "subcontractors", {"name": f"Ortak Firma {i+1}", "job_type": "Elektrik ve montaj", "total_contract_amount": 12000+i*1000,
            "contact_info": f"02120000{i+1:02d}", "created_at": now})
        ins(c, "loaner_devices", {"device_type": "Laptop", "brand_model": f"Emanet Cihaz {i+1}", "serial_mac": f"LOAN-{i+1:04d}",
            "status": "Depoda", "daily_penalty_fee": 100, "shelf_no": f"E-{i+1}", "notes": "Demo emanet", "created_at": now})

    for i in range(10):
        ins(c, "stock_movements", {"part_id": part_ids[i], "movement_type": "IN", "amount": 50,
            "new_stock": 50, "description": "Demo ilk stok girisi", "created_at": now, "is_deleted": 0})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=r"C:\Users\yedek\AppData\Local\AYEC Pro\Data\ayecpro.db")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args()
    if not args.yes:
        raise SystemExit("Refusing destructive reset without --yes")
    db = Path(args.db)
    backup = db.with_name(f"{db.stem}.before_demo_reset_{datetime.now():%Y%m%d_%H%M%S}.db")
    shutil.copy2(db, backup)
    conn = sqlite3.connect(db)
    try:
        reset(conn)
        seed(conn)
        conn.commit()
    finally:
        conn.close()
    print(f"backup={backup}")
    print(f"seeded={db}")


if __name__ == "__main__":
    main()
