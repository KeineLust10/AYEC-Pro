# -*- coding: utf-8 -*-
import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import Database

SEED_TAG = "ZT260405"
NOW = datetime(2026, 4, 5, 10, 0, 0)
RNG = random.Random(260405)
REGULAR_CUSTOMER_COUNT = 50
PARTNER_CUSTOMER_COUNT = 10
SERVICE_COUNT = 30
PART_COUNT = 100


def ts(days=0, hours=0):
    return (NOW + timedelta(days=days, hours=hours)).strftime("%Y-%m-%d %H:%M:%S")


def date_str(days=0):
    return (NOW + timedelta(days=days)).strftime("%Y-%m-%d")


def ensure_partner_tables(db):
    db.cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS partner_shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_customer_id INTEGER NOT NULL,
            shipment_no TEXT UNIQUE,
            customer_name TEXT,
            device_type TEXT,
            device_brand TEXT,
            device_model TEXT,
            serial_no TEXT,
            fault_description TEXT,
            service_tracking_no TEXT,
            cargo_tracking_no TEXT,
            status TEXT DEFAULT 'Yolda',
            direction TEXT DEFAULT 'OUT',
            shipment_date TEXT,
            received_date TEXT,
            completed_date TEXT,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'TRY',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS partner_finance_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER,
            partner_customer_id INTEGER,
            entry_type TEXT,
            amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'TRY',
            description TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS partner_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id INTEGER,
            title TEXT,
            detail TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS partner_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            partner_customer_id INTEGER,
            shipment_id INTEGER,
            title TEXT,
            file_path TEXT,
            file_type TEXT,
            created_at TEXT
        );
        """
    )
    db.conn.commit()


def cleanup(db):
    like = f"%{SEED_TAG}%"
    exact = SEED_TAG
    statements = [
        ("DELETE FROM payment_debt_links WHERE payment_txn_id IN (SELECT id FROM currency_transactions WHERE description LIKE ?) OR debt_txn_id IN (SELECT id FROM currency_transactions WHERE description LIKE ?)", (like, like)),
        ("DELETE FROM project_unit_products WHERE notes LIKE ?", (like,)),
        ("DELETE FROM project_transactions WHERE description LIKE ?", (like,)),
        ("DELETE FROM project_units WHERE description LIKE ?", (like,)),
        ("DELETE FROM partner_documents WHERE title LIKE ?", (like,)),
        ("DELETE FROM partner_timeline WHERE detail LIKE ?", (like,)),
        ("DELETE FROM partner_finance_entries WHERE description LIKE ?", (like,)),
        ("DELETE FROM partner_shipments WHERE notes LIKE ? OR shipment_no LIKE ?", (like, like)),
        ("DELETE FROM stock_movements WHERE notes LIKE ? OR reference_no LIKE ?", (like, like)),
        ("DELETE FROM used_parts WHERE tracking_no LIKE ?", (like,)),
        ("DELETE FROM service_logs WHERE device_tracking_no LIKE ? OR message LIKE ?", (like, like)),
        ("DELETE FROM devices WHERE tracking_no LIKE ? OR customer_name LIKE ?", (like, like)),
        ("DELETE FROM accounting WHERE description LIKE ? OR tracking_no LIKE ? OR ref_no LIKE ?", (like, like, like)),
        ("DELETE FROM currency_transactions WHERE description LIKE ? OR tracking_no LIKE ?", (like, like)),
        ("DELETE FROM customer_currency_balances WHERE customer_id IN (SELECT id FROM customers WHERE notes = ?)", (exact,)),
        ("DELETE FROM contracts WHERE description LIKE ? OR title LIKE ?", (like, like)),
        ("DELETE FROM projects WHERE description LIKE ? OR ref_no LIKE ? OR name LIKE ?", (like, like, like)),
        ("DELETE FROM checks_notes WHERE description LIKE ? OR portfolio_no LIKE ?", (like, like)),
        ("DELETE FROM loan_installments WHERE loan_id IN (SELECT id FROM loans WHERE description LIKE ? OR loan_title LIKE ?)", (like, like)),
        ("DELETE FROM loans WHERE description LIKE ? OR loan_title LIKE ?", (like, like)),
        ("DELETE FROM appointments WHERE description LIKE ? OR notes LIKE ?", (like, like)),
        ("DELETE FROM reminders WHERE message LIKE ? OR title LIKE ?", (like, like)),
        ("DELETE FROM announcements WHERE title LIKE ? OR content LIKE ?", (like, like)),
        ("DELETE FROM notifications WHERE title LIKE ? OR content LIKE ? OR link_id LIKE ?", (like, like, like)),
        ("DELETE FROM services WHERE description LIKE ? OR name LIKE ?", (like, like)),
        ("DELETE FROM parts WHERE description LIKE ? OR code LIKE ? OR name LIKE ? OR part_name LIKE ?", (like, like, like, like)),
        ("DELETE FROM bank_accounts WHERE account_holder LIKE ? OR iban LIKE ?", (like, like)),
        ("DELETE FROM personnel WHERE email LIKE ? OR username LIKE ?", (like, like)),
        ("DELETE FROM customers WHERE notes = ?", (exact,)),
    ]
    for sql, params in statements:
        try:
            db.cursor.execute(sql, params)
        except Exception:
            pass
    db.conn.commit()


def seed_personnel(db):
    rows = []
    for i in range(10):
        rows.append(
            (
                f"{SEED_TAG} Personel {i+1}",
                f"zt260405_p{i+1}",
                "1234",
                ["Teknisyen", "Muhasebe", "Saha", "Yonetici"][i % 4],
                f"0535{1000000 + i:07d}",
                25000 + i * 1750,
                5 + i,
                ts(-20 + i),
                f"zt260405_personel_{i+1}@test.local",
                1,
                ["Servis", "Finans", "Lojistik"][i % 3],
                "Aktif",
            )
        )
    db.cursor.executemany(
        """
        INSERT INTO personnel
        (name, username, password, role, phone, salary, commission, created_at, email, active, department, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    db.conn.commit()
    return db.cursor.execute(
        "SELECT id, name FROM personnel WHERE username LIKE 'zt260405_%' ORDER BY id"
    ).fetchall()


def seed_customers(db):
    regular = []
    partner = []
    first_names = [
        "Ahmet", "Ayse", "Mehmet", "Fatma", "Murat", "Elif", "Can", "Zeynep",
        "Burak", "Selin", "Emre", "Derya", "Kaan", "Buse", "Okan", "Gamze",
        "Tolga", "Seda", "Deniz", "Esra", "Hakan", "Cem", "Umut", "Merve",
        "Levent", "Gokce", "Onur", "Pelin", "Serkan", "Nazan",
    ]
    last_names = [
        "Yilmaz", "Demir", "Kaya", "Celik", "Sahin", "Ozturk", "Aydin", "Koc",
        "Arslan", "Dogan", "Kilic", "Gunes", "Polat", "Yavuz", "Bulut",
        "Turan", "Ozkan", "Aksoy", "Simsek", "Eren",
    ]
    districts = ["Kadikoy", "Besiktas", "Uskudar", "Atasehir", "Pendik", "Maltepe", "Bakirkoy", "Kartal"]
    for i in range(REGULAR_CUSTOMER_COUNT):
        full_name = f"{first_names[i % len(first_names)]} {last_names[(i * 3) % len(last_names)]}"
        regular.append(
            (
                f"{SEED_TAG} {full_name}",
                f"0501{1000000 + i:07d}",
                f"musteri{i+1:02d}@test.local",
                ["Bireysel", "Kurumsal"][i % 2],
                f"{SEED_TAG} Teknik Musteri {i+1}",
                f"Istanbul {districts[i % len(districts)]} Test Mah. No:{i+1}",
                SEED_TAG,
                0,
                ["Standart", "Bakim Anlasmali", "Kurumsal"][i % 3],
                ["SLA-8", "SLA-24", "SLA-48"][i % 3],
            )
        )
    for i in range(PARTNER_CUSTOMER_COUNT):
        partner.append(
            (
                f"{SEED_TAG} Partner {i+1}",
                f"0551{1000000 + i:07d}",
                f"partner{i+1}@test.local",
                "Kurumsal",
                f"{SEED_TAG} Partner Servis {i+1}",
                f"Partner adres {i+1}",
                SEED_TAG,
                1,
                "Partner",
                "SLA-8",
            )
        )
    db.cursor.executemany(
        """
        INSERT INTO customers
        (name, phone, email, type, company_name, address, notes, is_partner, contract_type, sla_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        regular + partner,
    )
    db.conn.commit()
    return db.cursor.execute(
        "SELECT id, name, is_partner FROM customers WHERE notes = ? ORDER BY id", (SEED_TAG,)
    ).fetchall()


def seed_services_and_parts(db):
    service_rows = []
    service_names = [
        "Bilgisayar Ariza Tespit", "Laptop Anakart Onarimi", "SSD Montaj ve Klonlama",
        "Windows Kurulum ve Optimizasyon", "Veri Yedekleme", "Kamera Montaj",
        "IP Kamera Konfigurasyon", "NVR Kurulum", "Guvenlik Sistemi Bakim",
        "Network Kablolama", "Access Point Kurulum", "Alarm Panel Bakim",
        "Termal Kamera Ayar", "UPS Bakim", "Yazici Bakim", "Sunucu Kontrol",
        "Firewall Temel Kurulum", "Kartli Gecis Bakim", "Zayif Akim Kesif",
        "Yerinde Servis", "Bilgisayar Satis Kurulum", "Kamera Satis Kurulum",
        "Periyodik Bakim", "Acil Servis", "Uzak Destek", "Lisans Kurulum",
        "RAM Upgrade", "Ekran Degisimi", "Adaptör Test", "Switch Kurulum",
    ]
    for i in range(SERVICE_COUNT):
        currency = ["TRY", "USD", "EUR"][i % 3]
        price = [950, 120, 85][i % 3] + i * 15
        service_rows.append(
            (f"{SEED_TAG} {service_names[i % len(service_names)]}", price, currency, f"{SEED_TAG} teknik servis hizmet kaydi {i+1}", ts(-15 + i), 0, f"{SEED_TAG}-SRV-{i+1:03d}")
        )
    db.cursor.executemany(
        "INSERT INTO services (name, price, currency, description, created_at, is_deleted, barcode) VALUES (?, ?, ?, ?, ?, ?, ?)",
        service_rows,
    )
    part_rows = []
    part_names = [
        "SSD 500GB", "SSD 1TB", "DDR4 8GB RAM", "DDR4 16GB RAM", "DDR5 16GB RAM",
        "Laptop Adaptoru", "Notebook Batarya", "Termal Macun", "CPU Fan",
        "Laptop Klavye", "Mouse", "Klavye", "Monitor 24 Inc", "HDMI Kablo",
        "CAT6 Kablo", "RJ45 Konnektor", "Patch Panel", "Switch 8 Port",
        "Switch 16 Port", "Router", "Access Point", "IP Kamera 2MP",
        "IP Kamera 4MP", "Dome Kamera", "Bullet Kamera", "NVR 4 Kanal",
        "NVR 8 Kanal", "NVR 16 Kanal", "HDD Surveillance 2TB",
        "HDD Surveillance 4TB", "Kamera Adaptoru", "PoE Enjektor",
        "PoE Switch", "Alarm Panel", "PIR Sensor", "Manyetik Kontak",
        "Siren", "Kart Okuyucu", "Access Kontrol Panel", "UPS 1000VA",
    ]
    categories = ["Bilgisayar Parcalari", "Guvenlik Sistemleri", "Network", "Sarf Malzeme", "Aksesuar"]
    brands = ["Kingston", "Samsung", "WD", "Hikvision", "Dahua", "TP-Link", "Dell", "HP", "Logitech", "Generic"]
    for i in range(PART_COUNT):
        currency = ["TRY", "USD", "EUR"][i % 3]
        code = f"{SEED_TAG}-PRT-{i+1:03d}"
        stock = 12 + (i % 35)
        sale = round((350 + i * 17) / (1 if currency == 'TRY' else 10), 2)
        buy = round(sale * 0.7, 2)
        base_name = part_names[i % len(part_names)]
        part_rows.append(
            (
                f"{SEED_TAG} {base_name} {i+1:03d}",
                f"{SEED_TAG} {base_name} {i+1:03d}",
                stock,
                sale,
                buy,
                currency,
                code,
                f"{code}-B",
                categories[i % len(categories)],
                5,
                f"{SEED_TAG} teknik servis stok urunu {i+1}",
                f"R{(i % 10) + 1}",
                ts(-30 + i),
                brands[i % len(brands)],
            )
        )
    db.cursor.executemany(
        """
        INSERT INTO parts
        (name, part_name, stock, price, purchase_price, currency, code, barcode, category, min_stock, description, shelf_number, created_at, brand)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        part_rows,
    )
    part_rows_db = db.cursor.execute(
        """
        SELECT id, stock, code, name, purchase_price, currency
        FROM parts
        WHERE code LIKE ?
        ORDER BY id
        """,
        (f"{SEED_TAG}-%",),
    ).fetchall()
    db.cursor.executemany(
        "INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        [(row[0], "Giris", row[1], row[1], f"{SEED_TAG} ilk stok girisi {row[2]}", ts(-4 + (idx % 5))) for idx, row in enumerate(part_rows_db)],
    )
    for idx, row in enumerate(part_rows_db):
        part_id, stock_qty, code, part_name, purchase_price, currency = row
        total_cost = round(float(stock_qty or 0) * float(purchase_price or 0), 2)
        if total_cost <= 0:
            continue
        db.add_transaction(
            t_type="Gider",
            category="Stok Alımı",
            amount=total_cost,
            description=f"{SEED_TAG} ilk stok alimi {code} - {stock_qty} x {part_name}",
            payment_method="Nakit",
            currency=currency or "TRY",
            original_amount=total_cost,
            date=date_str(-4 + (idx % 5)),
            selected_services=[{
                "kind": "stock_purchase",
                "name": part_name,
                "quantity": stock_qty,
                "unit_price": purchase_price,
                "currency": currency or "TRY",
                "line_total": total_cost,
                "part_id": part_id,
            }],
        )
    db.conn.commit()


def seed_finance_assets(db, customers):
    customer_ids = [row[0] for row in customers if row[2] == 0]
    bank_rows = []
    contract_rows = []
    for i in range(10):
        currency = ["TRY", "USD", "EUR"][i % 3]
        bank_rows.append(
            (
                f"{SEED_TAG} Banka {i+1}",
                f"{SEED_TAG} Hesap {i+1}",
                f"TR{100000000000000000000000 + i}",
                f"10020030{i:04d}",
                f"{1000+i}",
                currency,
                1,
                ts(-40 + i),
                round(25000 + i * 2300, 2),
                0,
            )
        )
        contract_rows.append(
            (
                customer_ids[i],
                f"{SEED_TAG} Bakim Sozlesmesi {i+1}",
                date_str(-30 + i),
                date_str(365 + i),
                ["Yillik", "Aylik"][i % 2],
                5000 + i * 750,
                "Aktif",
                f"{SEED_TAG} sozlesme aciklamasi {i+1}",
                ts(-30 + i),
            )
        )
    db.cursor.executemany(
        """
        INSERT INTO bank_accounts
        (bank_name, account_holder, iban, account_number, branch_code, currency, is_active, created_at, current_balance, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        bank_rows,
    )
    db.cursor.executemany(
        """
        INSERT INTO contracts
        (customer_id, title, start_date, end_date, contract_type, price, status, description, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        contract_rows,
    )
    db.conn.commit()


def seed_projects(db, customers):
    customer_ids = [row[0] for row in customers if row[2] == 0]
    part_map = dict(db.cursor.execute("SELECT id, name FROM parts WHERE code LIKE ? ORDER BY id", (f"{SEED_TAG}-%",)).fetchall())
    project_ids = []
    for i in range(10):
        currency = ["TRY", "USD", "EUR"][i % 3]
        db.cursor.execute(
            """
            INSERT INTO projects
            (name, start_date, end_date, budget, status, description, created_at, cost, payment_method, customer_id, customer_name, ref_no, is_archived, currency, exchange_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"{SEED_TAG} Proje {i+1}",
                date_str(-25 + i),
                date_str(60 + i),
                100000 + i * 5000,
                ["Planlama", "Devam", "Tamamlandi"][i % 3],
                f"{SEED_TAG} proje aciklamasi {i+1}",
                ts(-25 + i),
                40000 + i * 2500,
                ["Nakit", "Havale", "Kredi Karti"][i % 3],
                customer_ids[i],
                next(row[1] for row in customers if row[0] == customer_ids[i]),
                f"{SEED_TAG}-PRJ-{i+1:03d}",
                0,
                currency,
                1.0 if currency == "TRY" else (44.5 if currency == "USD" else 48.2),
            ),
        )
        project_id = db.cursor.lastrowid
        project_ids.append(project_id)
        for unit_idx in range(2):
            db.cursor.execute(
                """
                INSERT INTO project_units
                (project_id, block_name, floor_no, unit_no, status, price, unit_type, area, unit_price, total_price, customer_id, description, created_at, unit_kind)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id, f"B{unit_idx+1}", unit_idx + 1, f"{i+1}{unit_idx+1}",
                    ["Bos", "Kurulumda", "Teslim"][unit_idx % 3], 15000 + unit_idx * 5000,
                    "Daire", 120 + unit_idx * 15, 1000, 15000 + unit_idx * 5000,
                    customer_ids[i], f"{SEED_TAG} unite {i+1}-{unit_idx+1}", ts(-20 + i + unit_idx), "independent"
                ),
            )
            unit_id = db.cursor.lastrowid
            chosen = list(part_map.items())[i + unit_idx : i + unit_idx + 2]
            for part_id, part_name in chosen:
                db.cursor.execute(
                    "INSERT INTO project_unit_products (unit_id, project_id, part_id, part_name, part_code, quantity, notes, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (unit_id, project_id, part_id, part_name, f"{SEED_TAG}-AUTO", 1 + unit_idx, f"{SEED_TAG} bagli urun", ts(-19 + i)),
                )
        db.cursor.execute(
            "INSERT INTO project_transactions (project_id, type, category, amount, payment_method, date, description, status, paid_date, ref_table, ref_id, created_at, original_amount, original_currency, exchange_rate) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (project_id, "Gelir", "Proje", 25000 + i * 1000, "Havale", date_str(-10 + i), f"{SEED_TAG} proje tahsilati", "Tamamlandi", date_str(-10 + i), "projects", project_id, ts(-10 + i), 25000 + i * 1000, "TRY", 1.0),
        )
    db.conn.commit()
    return project_ids


def seed_customer_flow(db, customers, personnel):
    regulars = [row for row in customers if row[2] == 0]
    part_ids = [row[0] for row in db.cursor.execute("SELECT id FROM parts WHERE code LIKE ? ORDER BY id", (f"{SEED_TAG}-%",)).fetchall()]
    service_ids = [row[0] for row in db.cursor.execute("SELECT id FROM services WHERE barcode LIKE ? ORDER BY id", (f"{SEED_TAG}-%",)).fetchall()]
    personnel_names = [row[1] for row in personnel]
    currencies = ["TRY", "USD", "EUR"]
    device_types = ["Laptop", "Masaustu Bilgisayar", "IP Kamera", "NVR", "Alarm Paneli", "Access Point"]
    device_brands = ["Dell", "HP", "Lenovo", "Asus", "Dahua", "Hikvision", "TP-Link", "Paradox"]
    fault_categories = ["Donanim", "Yazilim", "Kamera", "Network", "Guc", "Bakim"]
    statuses = ["Kayit", "Tamirde", "Hazir", "Teslim Edildi", "Parca Bekliyor"]
    for i, (customer_id, customer_name, _) in enumerate(regulars):
        currency = currencies[i % 3]
        rate = 1.0 if currency == "TRY" else (44.5 if currency == "USD" else 48.2)
        tracking_no = f"{SEED_TAG}-SRV-{i+1:03d}"
        amount = [18500, 420, 310][i % 3] + i * 35
        device_type = device_types[i % len(device_types)]
        device_brand = device_brands[i % len(device_brands)]
        db.cursor.execute(
            """
            INSERT INTO devices
            (tracking_no, customer_name, device_brand, device_model, serial_no, fault_category, urgency, status, entry_date, estimated_date, price, device_type, customer_id, labor_cost, repair_details, technician, payment_status, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                tracking_no, customer_name, device_brand, f"{device_type} Model {i+1}", f"SN{26040500+i}",
                fault_categories[i % len(fault_categories)], ["Normal", "Acil", "Kritik"][i % 3], statuses[i % len(statuses)],
                date_str(-12 + i), date_str(2 + i), amount, ["Laptop", "Kamera", "NVR"][i % 3],
                customer_id, round(amount * 0.35, 2), f"{SEED_TAG} teknik onarim {i+1}", personnel_names[i % len(personnel_names)], "Bekliyor",
            ),
        )
        device_id = db.cursor.lastrowid
        for j in range(2):
            pid = part_ids[(i * 2 + j) % len(part_ids)]
            db.cursor.execute(
                "INSERT INTO used_parts (tracking_no, part_id, part_name, price, quantity, purchase_price_snapshot, currency, created_at, is_deleted) SELECT ?, id, name, price, ?, purchase_price, currency, ?, 0 FROM parts WHERE id = ?",
                (tracking_no, j + 1, ts(-8 + i), pid),
            )
        for j in range(2):
            db.cursor.execute(
                "INSERT INTO service_logs (device_tracking_no, log_type, message, created_at, user) VALUES (?, ?, ?, ?, ?)",
                (tracking_no, "INFO", f"{SEED_TAG} servis log {j+1}", ts(-7 + i, j), personnel_names[(i + j) % len(personnel_names)]),
            )
        debit_desc = f"{SEED_TAG} servis satisi {tracking_no}"
        db.add_currency_transaction(customer_id, amount, currency, "DEBIT", exchange_rate=rate, description=debit_desc, tracking_no=tracking_no, created_at=ts(-6 + i), is_invoiced=0)
        debt_txn_id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.cursor.execute(
            """
            INSERT INTO accounting
            (type, category, amount, try_equivalent, currency, exchange_rate, original_amount, description, date, created_at, customer_id, customer_name, is_invoiced, payment_method, tracking_no, ref_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("Gelir", "Satis", round(amount * rate, 2), round(amount * rate, 2), currency, rate, amount, debit_desc, date_str(-6 + i), ts(-6 + i), customer_id, customer_name, 0, "Cari", tracking_no, tracking_no),
        )
        if i < 35:
            pay_ratio = 1.0 if i % 2 == 0 else 0.55
            payment = round(amount * pay_ratio, 2)
            pay_desc = f"{SEED_TAG} tahsilat {tracking_no}"
            db.add_currency_transaction(customer_id, payment, currency, "CREDIT", exchange_rate=rate, description=pay_desc, tracking_no=tracking_no, created_at=ts(-4 + i), is_invoiced=0)
            pay_txn_id = db.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.apply_payment_to_debts(customer_id, payment, currency, payment_transaction_id=pay_txn_id, selected_debt_ids=[debt_txn_id])
            db.cursor.execute(
                "INSERT INTO accounting (type, category, amount, try_equivalent, currency, exchange_rate, original_amount, description, date, created_at, customer_id, customer_name, is_invoiced, payment_method, tracking_no, ref_no) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("Gelir", "Tahsilat", round(payment * rate, 2), round(payment * rate, 2), currency, rate, payment, pay_desc, date_str(-4 + i), ts(-4 + i), customer_id, customer_name, 0, ["Nakit", "Havale", "Kart"][i % 3], tracking_no, tracking_no),
            )
        db.cursor.execute(
            "INSERT INTO appointments (customer_name, phone, date, time, description, status, created_at, personnel_name, device, brand, model, urgency, customer_id, type, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (customer_name, f"0501{1000000 + i:07d}", date_str(i), f"{9 + (i % 9):02d}:00", f"{SEED_TAG} randevu {i+1}", "Planli", ts(-2 + i), personnel_names[i % len(personnel_names)], device_type, device_brand, f"Model {i+1}", "Normal", customer_id, "Servis", SEED_TAG),
        )
        db.cursor.execute("INSERT INTO reminders (tracking_no, message, due_date, is_read, created_at, title, personnel, date, description, status) VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?, ?)",
                          (tracking_no, f"{SEED_TAG} hatirlatma {i+1}", date_str(3 + i), ts(-1 + i), f"{SEED_TAG} Hatirlatma", personnel_names[i % len(personnel_names)], date_str(3 + i), f"{SEED_TAG} aciklama", "Bekliyor"))
        db.cursor.execute("INSERT INTO notifications (category, title, content, link_id, status, priority, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          ("servis", f"{SEED_TAG} Bildirim {i+1}", f"{customer_name} icin test bildirimi", tracking_no, "new", ["low", "medium", "high"][i % 3], ts(-1 + i)))
    db.conn.commit()


def seed_misc(db, customers):
    regular_ids = [row[0] for row in customers if row[2] == 0][:10]
    partner_rows = [row for row in customers if row[2] == 1][:10]
    for i in range(10):
        db.cursor.execute("INSERT INTO announcements (date, priority, title, content, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                          (date_str(-i), ["Dusuk", "Orta", "Yuksek"][i % 3], f"{SEED_TAG} Duyuru {i+1}", f"{SEED_TAG} sistem duyurusu {i+1}", "Codex", ts(-i)))
        db.cursor.execute("INSERT INTO checks_notes (type, direction, portfolio_no, amount, due_date, issuer, recipient, bank_name, description, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          ("Cek", ["IN", "OUT"][i % 2], f"{SEED_TAG}-CHK-{i+1:03d}", 5000 + i * 450, date_str(15 + i), f"{SEED_TAG} Kesideci {i+1}", f"{SEED_TAG} Alici {i+1}", f"{SEED_TAG} Banka {i+1}", f"{SEED_TAG} cek senet", "Portfoyde", ts(-i)))
        db.cursor.execute("INSERT INTO loans (bank_account_id, bank_name, amount, interest_rate, term_months, start_date, total_payment, description, status, created_at, loan_type, loan_title, kkdf_rate, bsmv_rate, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                          (None, f"{SEED_TAG} Banka {i+1}", 75000 + i * 5000, 2.1 + i * 0.1, 12, date_str(-30 + i), 90000 + i * 5500, f"{SEED_TAG} kredi {i+1}", "Aktif", ts(-20 + i), "Ticari", f"{SEED_TAG} Kredi {i+1}", 15, 5))
        loan_id = db.cursor.lastrowid
        for inst in range(1, 4):
            db.cursor.execute("INSERT INTO loan_installments (loan_id, installment_no, due_date, total_amount, principal_part, interest_part, kkdf_amount, bsmv_amount, status, paid_date, created_at, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                              (loan_id, inst, date_str(30 * inst), 9000 + inst * 150, 7000, 1400, 350, 100, "Bekliyor", None, ts(-10 + inst)))
        partner_id, partner_name, _ = partner_rows[i]
        shipment_no = f"{SEED_TAG}-PRTNR-{i+1:03d}"
        db.cursor.execute("INSERT INTO partner_shipments (partner_customer_id, shipment_no, customer_name, device_type, device_brand, device_model, serial_no, fault_description, service_tracking_no, cargo_tracking_no, status, direction, shipment_date, received_date, completed_date, amount, currency, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          (partner_id, shipment_no, f"{SEED_TAG} Musteri {i+1}", "Laptop", "Dell", f"Latitude {i+1}", f"{SEED_TAG}SN{i+1}", f"{SEED_TAG} partner servis", f"{SEED_TAG}-SRV-{i+1:03d}", f"KRG{i+1:06d}", ["Yolda", "Tamirde", "Tamamlandi"][i % 3], ["OUT", "IN"][i % 2], date_str(-8 + i), date_str(-5 + i), date_str(-1 + i), 250 + i * 15, ["TRY", "USD", "EUR"][i % 3], f"{SEED_TAG} partner notu", ts(-8 + i), ts(-1 + i)))
        shipment_id = db.cursor.lastrowid
        db.cursor.execute("INSERT INTO partner_finance_entries (shipment_id, partner_customer_id, entry_type, amount, currency, description, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                          (shipment_id, partner_id, "Borclandirma", 250 + i * 15, ["TRY", "USD", "EUR"][i % 3], f"{SEED_TAG} partner finans", ts(-7 + i)))
        db.cursor.execute("INSERT INTO partner_timeline (shipment_id, title, detail, created_at) VALUES (?, ?, ?, ?)",
                          (shipment_id, "Kayit Acildi", f"{SEED_TAG} partner timeline", ts(-7 + i)))
    db.conn.commit()


def write_partner_docs(db):
    docs_dir = Path(__file__).resolve().parents[1] / "test_assets" / "partner_docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    shipments = db.cursor.execute(
        "SELECT id, partner_customer_id, shipment_no FROM partner_shipments WHERE shipment_no LIKE ? ORDER BY id LIMIT 10",
        (f"{SEED_TAG}-%",),
    ).fetchall()
    for i, (shipment_id, partner_id, shipment_no) in enumerate(shipments, start=1):
        file_path = docs_dir / f"{shipment_no}.txt"
        file_path.write_text(f"{shipment_no}\n{SEED_TAG} test partner belgesi {i}\n", encoding="utf-8")
        db.cursor.execute(
            "INSERT INTO partner_documents (partner_customer_id, shipment_id, title, file_path, file_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (partner_id, shipment_id, f"{SEED_TAG} Belge {i}", str(file_path), "txt", ts(-i)),
        )
    db.conn.commit()


def summarize(db):
    tables = [
        "customers", "personnel", "services", "parts", "devices", "currency_transactions",
        "accounting", "bank_accounts", "contracts", "projects", "appointments",
        "announcements", "notifications", "checks_notes", "loans", "partner_shipments"
    ]
    summary = {}
    for table in tables:
        try:
            if table in {"customers"}:
                count = db.cursor.execute("SELECT COUNT(*) FROM customers WHERE notes = ?", (SEED_TAG,)).fetchone()[0]
            elif table == "personnel":
                count = db.cursor.execute("SELECT COUNT(*) FROM personnel WHERE username LIKE 'zt260405_%'").fetchone()[0]
            elif table == "services":
                count = db.cursor.execute("SELECT COUNT(*) FROM services WHERE barcode LIKE ?", (f"{SEED_TAG}-%",)).fetchone()[0]
            elif table == "parts":
                count = db.cursor.execute("SELECT COUNT(*) FROM parts WHERE code LIKE ?", (f"{SEED_TAG}-%",)).fetchone()[0]
            elif table == "devices":
                count = db.cursor.execute("SELECT COUNT(*) FROM devices WHERE tracking_no LIKE ?", (f"{SEED_TAG}-%",)).fetchone()[0]
            elif table == "partner_shipments":
                count = db.cursor.execute("SELECT COUNT(*) FROM partner_shipments WHERE shipment_no LIKE ?", (f"{SEED_TAG}-%",)).fetchone()[0]
            else:
                count = db.cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            summary[table] = count
        except Exception:
            summary[table] = "ERR"
    return summary


def main():
    db = Database("ayecpro.db")
    ensure_partner_tables(db)
    db.create_payment_debt_links_table()
    cleanup(db)
    personnel = seed_personnel(db)
    customers = seed_customers(db)
    seed_services_and_parts(db)
    seed_finance_assets(db, customers)
    seed_projects(db, customers)
    seed_customer_flow(db, customers, personnel)
    seed_misc(db, customers)
    write_partner_docs(db)
    db.recalculate_all_customer_balances()
    for name, count in summarize(db).items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
