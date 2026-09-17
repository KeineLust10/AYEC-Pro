# -*- coding: utf-8 -*-
"""Populate AYEC Pro desktop database with broad demo/test data.

The script writes to the same AppData SQLite database used by the desktop app.
Rows created here are tagged with SEED_TAG so the script can be rerun safely
without touching real user records.
"""

from __future__ import annotations

import json
import random
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import Database
from src.utils.path_helper import PathHelper


SEED_TAG = "AYEC-DEMO-20260708"
random.seed(20260708)


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def day(offset: int = 0) -> str:
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def quote(identifier: str) -> str:
    if not identifier or not identifier.replace("_", "").isalnum():
        raise ValueError(f"Unsafe identifier: {identifier!r}")
    return f'"{identifier}"'


class Seeder:
    def __init__(self) -> None:
        self.db = Database()
        self.cur = self.db.cursor
        self.conn = self.db.conn
        self.columns_cache: dict[str, set[str]] = {}
        self.counts: dict[str, int] = {}

    def table_exists(self, table: str) -> bool:
        self.cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return self.cur.fetchone() is not None

    def columns(self, table: str) -> set[str]:
        if table not in self.columns_cache:
            if not self.table_exists(table):
                self.columns_cache[table] = set()
            else:
                self.cur.execute(f"PRAGMA table_info({quote(table)})")
                self.columns_cache[table] = {row[1] for row in self.cur.fetchall()}
        return self.columns_cache[table]

    def insert(self, table: str, data: dict) -> int | None:
        cols = self.columns(table)
        payload = {key: value for key, value in data.items() if key in cols}
        if not payload:
            return None
        names = ", ".join(quote(key) for key in payload)
        marks = ", ".join("?" for _ in payload)
        self.cur.execute(
            f"INSERT INTO {quote(table)} ({names}) VALUES ({marks})",
            tuple(payload.values()),
        )
        self.counts[table] = self.counts.get(table, 0) + 1
        return int(self.cur.lastrowid)

    def delete_like(self, table: str, column: str) -> None:
        if self.table_exists(table) and column in self.columns(table):
            self.cur.execute(
                f"DELETE FROM {quote(table)} WHERE {quote(column)} LIKE ?",
                (f"%{SEED_TAG}%",),
            )

    def cleanup(self) -> None:
        self.cur.execute("PRAGMA foreign_keys=OFF")
        tracking_prefix = f"{SEED_TAG}%"
        code_prefix = f"{SEED_TAG}%"
        ref_prefix = f"{SEED_TAG}%"

        if self.table_exists("projects") and "ref_no" in self.columns("projects"):
            self.cur.execute("SELECT id FROM projects WHERE ref_no LIKE ?", (ref_prefix,))
            project_ids = [row[0] for row in self.cur.fetchall()]
            for pid in project_ids:
                for table in (
                    "project_unit_products",
                    "project_unit_sales",
                    "project_transactions",
                    "subcontractors",
                    "project_units",
                ):
                    if self.table_exists(table) and "project_id" in self.columns(table):
                        self.cur.execute(
                            f"DELETE FROM {quote(table)} WHERE project_id=?",
                            (pid,),
                        )
            self.cur.execute("DELETE FROM projects WHERE ref_no LIKE ?", (ref_prefix,))

        if self.table_exists("devices") and "tracking_no" in self.columns("devices"):
            self.cur.execute(
                "SELECT tracking_no, id FROM devices WHERE tracking_no LIKE ?",
                (tracking_prefix,),
            )
            device_rows = self.cur.fetchall()
            tracking_numbers = [row[0] for row in device_rows]
            device_ids = [row[1] for row in device_rows]
            for tno in tracking_numbers:
                for table in ("used_parts", "device_tests", "service_logs", "currency_transactions"):
                    if self.table_exists(table) and "tracking_no" in self.columns(table):
                        self.cur.execute(
                            f"DELETE FROM {quote(table)} WHERE tracking_no=?",
                            (tno,),
                        )
            for did in device_ids:
                for table in (
                    "automotive_quote_items",
                    "automotive_quote_forms",
                    "automotive_delivery_forms",
                    "automotive_parts_requests",
                    "automotive_checkup_forms",
                ):
                    if self.table_exists(table) and "device_id" in self.columns(table):
                        self.cur.execute(
                            f"DELETE FROM {quote(table)} WHERE device_id=?",
                            (did,),
                        )
            self.cur.execute("DELETE FROM devices WHERE tracking_no LIKE ?", (tracking_prefix,))

        for table, column in (
            ("parts", "code"),
            ("stock_movements", "description"),
            ("customers", "email"),
            ("personnel", "username"),
            ("appointments", "description"),
            ("reminders", "message"),
            ("accounting", "ref_no"),
            ("bank_accounts", "account_number"),
            ("bank_cards", "card_name"),
            ("loans", "loan_title"),
            ("checks_notes", "portfolio_no"),
            ("contracts", "description"),
            ("tickets", "subject"),
            ("kb_articles", "title"),
            ("announcements", "title"),
            ("notifications", "content"),
            ("assistant_notifications", "message"),
            ("services", "name"),
            ("service_definitions", "service_name"),
            ("customer_services", "notes"),
            ("customer_notes", "content"),
            ("loaner_devices", "serial_mac"),
            ("loaner_transactions", "tracking_no"),
            ("logistics", "tracking_no"),
            ("e_invoices", "uuid"),
            ("external_warranty_tracking", "internal_tracking_no"),
            ("customer_vehicles", "qr_token"),
            ("vehicle_maintenance_cards", "qr_token"),
            ("audit_logs", "details"),
            ("sms_log", "message"),
            ("product_bank_mappings", "default_category"),
        ):
            self.delete_like(table, column)

        self.conn.commit()
        self.cur.execute("PRAGMA foreign_keys=ON")
        self.counts.clear()

    def backup(self) -> Path | None:
        db_path = Path(PathHelper.get_db_path())
        if not db_path.exists():
            return None
        backup_dir = ROOT / "backups" / "seed_backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"ayecpro_before_seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(db_path, target)
        return target

    def seed_customers(self) -> list[dict]:
        first = [
            "Ahmet", "Ayşe", "Mehmet", "Zeynep", "Burak", "Elif", "Can", "Derya",
            "Murat", "Selin", "Kemal", "Esra", "Okan", "Gökçe", "Umut", "Buse",
            "Tolga", "İrem", "Kaan", "Deniz",
        ]
        last = [
            "Yılmaz", "Demir", "Kaya", "Çelik", "Şahin", "Öztürk", "Aydın", "Arslan",
            "Doğan", "Kılıç", "Koç", "Bulut", "Polat", "Aksoy", "Turan", "Güneş",
            "Kurt", "Yavuz", "Özkan", "Aslan",
        ]
        customers = []
        for idx in range(1, 21):
            name = f"{first[idx - 1]} {last[idx - 1]}"
            is_company = idx % 4 == 0
            cid = self.insert(
                "customers",
                {
                    "name": name,
                    "phone": f"05{idx:02d} {300 + idx:03d} {10 + idx:02d} {20 + idx:02d}",
                    "phone2": f"0216 555 {idx:04d}",
                    "email": f"musteri{idx:02d}.{SEED_TAG.lower()}@example.com",
                    "type": "Kurumsal" if is_company else "Bireysel",
                    "company_name": f"{name.split()[0]} Teknoloji Ltd. Şti." if is_company else "",
                    "tax_no": f"900000{idx:04d}" if is_company else "",
                    "tc_no": f"100000000{idx:02d}",
                    "tax_office": "Kadıköy",
                    "address": f"Test Mahallesi {idx}. Sokak No:{idx}, İstanbul",
                    "city": "İstanbul",
                    "district": "Kadıköy" if idx % 2 else "Ümraniye",
                    "neighborhood": "Test Mahallesi",
                    "street": f"{idx}. Sokak",
                    "zip_code": f"34{idx:03d}",
                    "notes": f"{SEED_TAG} detaylı masaüstü test müşterisi",
                    "term_days": 30,
                    "limit_amount": 25000 + idx * 1500,
                    "sms_enabled": 1,
                    "is_problematic": 1 if idx in (7, 14) else 0,
                    "service_type": "Teknik Servis" if idx % 3 else "Otomotiv",
                    "commission_rate": 2.5 if idx % 5 == 0 else 0,
                    "is_partner": 1 if idx in (4, 8, 12) else 0,
                    "contract_type": "SLA" if idx in (4, 8, 12) else "Standart",
                    "sla_level": "Gold" if idx in (4, 8, 12) else "Bronze",
                    "created_at": day(-idx),
                    "is_deleted": 0,
                },
            )
            customers.append({"id": cid, "name": name, "phone": f"05{idx:02d}300{idx:04d}"})
        return customers

    def seed_personnel(self) -> list[dict]:
        people = [
            ("Mert Usta", "Teknik Servis Ustası", "Servis"),
            ("Seda Kalaycı", "Müşteri Temsilcisi", "Operasyon"),
            ("Ali Can", "Saha Teknisyeni", "Saha"),
            ("Ece Öner", "Muhasebe", "Finans"),
            ("Tuna Er", "Depo Sorumlusu", "Stok"),
            ("Naz Ak", "Proje Yöneticisi", "Proje"),
            ("Ömer Işık", "Otomotiv Teknisyeni", "Otomotiv"),
            ("Cemre Su", "Satış Temsilcisi", "Satış"),
            ("Barış Topal", "Güvenlik Sistemleri Uzmanı", "CCTV"),
            ("İlker Şen", "PC Toplama Uzmanı", "PC"),
            ("Pelin Ada", "Lojistik", "Kargo"),
            ("Duru Kaya", "Yönetici", "Yönetim"),
        ]
        rows = []
        for idx, (name, role, dept) in enumerate(people, start=1):
            pid = self.insert(
                "personnel",
                {
                    "name": name,
                    "username": f"demo_personel_{idx:02d}_{SEED_TAG}",
                    "password": "demo123",
                    "role": role,
                    "phone": f"05{50 + idx} 444 {idx:04d}",
                    "salary": 28000 + idx * 1750,
                    "commission": 3 + idx % 6,
                    "created_at": day(-30 + idx),
                    "email": f"personel{idx:02d}.{SEED_TAG.lower()}@example.com",
                    "active": 1,
                    "tc_no": f"200000000{idx:02d}",
                    "department": dept,
                    "telegram_id": f"demo_tg_{idx:02d}",
                    "lat": 40.98 + idx / 1000,
                    "lng": 29.02 + idx / 1000,
                    "status": "Aktif",
                    "last_seen": now(),
                },
            )
            rows.append({"id": pid, "name": name, "role": role})
        return rows

    def seed_parts(self) -> tuple[list[dict], list[dict]]:
        security_names = [
            "2MP Bullet Kamera", "4MP Dome Kamera", "8MP Varifocal Kamera", "PTZ Speed Dome",
            "Termal Kamera", "IP Kayıt Cihazı 4 Kanal", "NVR 8 Kanal", "NVR 16 Kanal",
            "DVR 8 Kanal", "PoE Switch 8 Port", "PoE Switch 16 Port", "Cat6 Kablo 305m",
            "CCTV 2+1 Kablo 100m", "BNC Konnektör", "RJ45 Konnektör", "12V Adaptör",
            "UPS 1kVA", "WD Purple 2TB", "Seagate Skyhawk 4TB", "Rack Kabin 9U",
            "Manyetik Kontak", "PIR Sensör", "Duman Dedektörü", "Yangın Butonu",
            "Siren Flaşör", "Alarm Paneli", "Keypad", "RFID Kart Okuyucu",
            "Parmak İzi Okuyucu", "Kapı Kilidi", "Exit Butonu", "Video İnterkom",
            "Monitör İç Ünite", "Zil Paneli", "Fiber Medya Converter", "Patch Panel",
            "Kamera Montaj Ayağı", "Junction Box", "HDMI KVM Extender", "Network Test Cihazı",
            "Kablo Kanalı", "Sigorta Kutusu", "Akü 12V 7Ah", "Akü 12V 18Ah",
            "Solar Kamera Paneli", "Wi-Fi Kamera", "Akıllı Kapı Zili", "Hareket Projektörü",
            "Güvenlik Etiketi", "Kamera Lens Temizleme Seti",
        ]
        pc_names = [
            "Intel i5 İşlemci", "Intel i7 İşlemci", "AMD Ryzen 5", "AMD Ryzen 7",
            "B660 Anakart", "B760 Anakart", "AM5 Anakart", "8GB DDR4 RAM",
            "16GB DDR4 RAM", "32GB DDR5 RAM", "500GB NVMe SSD", "1TB NVMe SSD",
            "2TB SATA SSD", "1TB HDD", "4TB HDD", "RTX 4060 Ekran Kartı",
            "RTX 4070 Ekran Kartı", "RX 7600 Ekran Kartı", "650W PSU", "750W PSU",
            "850W PSU", "ATX Kasa", "Mesh Kasa", "Sıvı Soğutma 240mm",
            "Tower CPU Soğutucu", "Termal Macun", "Wi-Fi PCIe Kart", "Bluetooth Adaptör",
            "USB-C Hub", "M.2 Heatsink", "SATA Kablo", "DisplayPort Kablo",
            "HDMI Kablo", "27 inç Monitör", "Mekanik Klavye", "Oyuncu Mouse",
            "Webcam 1080p", "Hoparlör Seti", "Kulaklık", "Laptop Adaptörü",
            "Laptop Batarya", "Laptop Ekran 15.6", "Klavye TR Q", "Touchpad Modülü",
            "Fan Modülü", "Menteşe Takımı", "CMOS Pil", "Kasa Fanı 120mm",
            "ARGB Kontrolcü", "Windows Lisans Kartı",
        ]

        def add_part(name: str, idx: int, family: str) -> dict:
            code = f"{SEED_TAG}-{family}-{idx:03d}"
            price = 350 + idx * (45 if family == "CCTV" else 65)
            pid = self.insert(
                "parts",
                {
                    "name": name,
                    "part_name": name,
                    "brand": random.choice(["Hikvision", "Dahua", "TP-Link", "Asus", "MSI", "Kingston", "WD"]),
                    "stock": 100,
                    "price": float(price),
                    "purchase_price": float(price * 0.68),
                    "currency": "TRY",
                    "code": code,
                    "barcode": f"869{idx:09d}",
                    "category": "Kamera Güvenlik Sistemleri" if family == "CCTV" else "PC Parçaları",
                    "min_stock": 10,
                    "description": f"{SEED_TAG} {family} stok test ürünü",
                    "shelf_number": f"{family}-R{(idx % 10) + 1}",
                    "oem_code": f"OEM-{family}-{idx:03d}",
                    "equivalent_code": f"EQ-{idx:03d}",
                    "compatible_models": "Genel uyumlu test stoğu",
                    "created_at": now(),
                    "is_deleted": 0,
                },
            )
            self.insert(
                "stock_movements",
                {
                    "part_id": pid,
                    "movement_type": "Giriş",
                    "type": "Giriş",
                    "amount": 100,
                    "new_stock": 100,
                    "current_stock": 100,
                    "description": f"{SEED_TAG} ilk test stok girişi",
                    "created_at": now(),
                    "date": day(0),
                    "is_deleted": 0,
                },
            )
            return {"id": pid, "name": name, "code": code, "price": price}

        security = [add_part(name, idx, "CCTV") for idx, name in enumerate(security_names, start=1)]
        pc = [add_part(name, idx, "PC") for idx, name in enumerate(pc_names, start=1)]
        return security, pc

    def add_used_parts(self, tracking_no: str, parts: list[dict], count: int = 3) -> float:
        total = 0.0
        selected = random.sample(parts, k=min(count, len(parts)))
        for part in selected:
            qty = random.choice([1, 1, 2])
            line_total = part["price"] * qty
            total += line_total
            self.insert(
                "used_parts",
                {
                    "tracking_no": tracking_no,
                    "part_id": part["id"],
                    "part_name": part["name"],
                    "price": line_total,
                    "quantity": qty,
                    "purchase_price_snapshot": round(line_total * 0.68, 2),
                    "currency": "TRY",
                    "created_at": now(),
                    "is_deleted": 0,
                },
            )
            self.cur.execute("UPDATE parts SET stock=MAX(COALESCE(stock,0)-?, 0) WHERE id=?", (qty, part["id"]))
            self.insert(
                "stock_movements",
                {
                    "part_id": part["id"],
                    "movement_type": "Çıkış",
                    "type": "Çıkış",
                    "amount": -qty,
                    "description": f"{SEED_TAG} servis parça kullanımı {tracking_no}",
                    "created_at": now(),
                    "date": day(0),
                    "is_deleted": 0,
                },
            )
        return total

    def seed_devices(self, customers: list[dict], personnel: list[dict], security_parts: list[dict], pc_parts: list[dict]) -> list[dict]:
        active_devices = []
        models = [
            ("Laptop", "Dell", "Latitude 5420", pc_parts),
            ("Masaüstü PC", "Asus", "ProArt Workstation", pc_parts),
            ("Kamera Sistemi", "Hikvision", "DS-7608NI-K2", security_parts),
            ("Güvenlik Alarmı", "Paradox", "SP6000", security_parts),
            ("Telefon", "Samsung", "Galaxy S23", pc_parts),
        ]
        faults = [
            "Açılmıyor ve güç almıyor",
            "Görüntü gelmiyor, detaylı test gerekiyor",
            "Ağ bağlantısı kopuyor",
            "Disk arızası ve veri aktarımı gerekli",
            "Kamera kayıt sistemi periyodik bakım",
        ]
        statuses = ["Beklemede", "İşlemde", "Parça Bekliyor", "Test Ediliyor"]
        for idx in range(1, 21):
            customer = customers[(idx - 1) % len(customers)]
            dtype, brand, model, part_pool = models[(idx - 1) % len(models)]
            tracking_no = f"{SEED_TAG}-SRV-{idx:04d}"
            part_total = self.add_used_parts(tracking_no, part_pool, count=3)
            labor = 650 + idx * 75
            total = part_total + labor
            did = self.insert(
                "devices",
                {
                    "tracking_no": tracking_no,
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "customer_contact": customer["phone"],
                    "device_type": dtype,
                    "device_brand": brand,
                    "device_model": model,
                    "serial_no": f"SN-DEMO-{idx:05d}",
                    "fault_category": "Donanım",
                    "urgency": "Acil" if idx % 6 == 0 else "Normal",
                    "priority": "Yüksek" if idx % 6 == 0 else "Normal",
                    "status": statuses[idx % len(statuses)],
                    "entry_date": day(-idx),
                    "estimated_date": day(2 + idx % 5),
                    "price": total,
                    "labor_cost": labor,
                    "cost_price": part_total * 0.68,
                    "fault_description": faults[idx % len(faults)],
                    "repair_details": "Parça değişimi yapıldı, test süreci devam ediyor.",
                    "technician": personnel[idx % len(personnel)]["name"],
                    "approval_status": "Onaylandı" if idx % 3 else "Beklemede",
                    "payment_status": "Bekliyor",
                    "internal_notes": f"{SEED_TAG} serviste bulunan test cihazı; parça kullanılmıştır.",
                    "accessories": "Adaptör, kablo, taşıma çantası",
                    "created_at": now(),
                    "updated_at": now(),
                    "is_archived": 0,
                    "is_deleted": 0,
                },
            )
            for test_name in ("Güç Testi", "Görüntü Testi", "Stres Testi"):
                self.insert(
                    "device_tests",
                    {
                        "tracking_no": tracking_no,
                        "test_name": test_name,
                        "result": "Geçti" if test_name != "Stres Testi" or idx % 4 else "Tekrar Test",
                        "note": f"{SEED_TAG} otomatik test kaydı",
                        "technician": personnel[idx % len(personnel)]["name"],
                        "created_at": now(),
                    },
                )
            active_devices.append({"id": did, "tracking_no": tracking_no, "customer": customer, "total": total})

        for idx in range(1, 51):
            customer = customers[idx % len(customers)]
            dtype, brand, model, part_pool = models[idx % len(models)]
            tracking_no = f"{SEED_TAG}-ARSIV-{idx:04d}"
            part_total = self.add_used_parts(tracking_no, part_pool, count=1)
            self.insert(
                "devices",
                {
                    "tracking_no": tracking_no,
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "customer_contact": customer["phone"],
                    "device_type": dtype,
                    "device_brand": brand,
                    "device_model": model,
                    "serial_no": f"SN-ARCH-{idx:05d}",
                    "fault_category": "Bakım",
                    "urgency": "Normal",
                    "status": "Teslim Edildi",
                    "entry_date": day(-90 - idx),
                    "exit_date": day(-60 - idx),
                    "delivered_at": day(-60 - idx),
                    "price": part_total + 500,
                    "labor_cost": 500,
                    "fault_description": "Arşiv test kaydı",
                    "repair_details": "Bakım tamamlandı ve teslim edildi.",
                    "technician": personnel[idx % len(personnel)]["name"],
                    "approval_status": "Onaylandı",
                    "payment_status": "Ödendi",
                    "internal_notes": f"{SEED_TAG} arşiv ekranı test kaydı.",
                    "created_at": day(-90 - idx),
                    "updated_at": day(-60 - idx),
                    "is_archived": 1,
                    "is_deleted": 0,
                },
            )
        return active_devices

    def seed_appointments(self, customers: list[dict], personnel: list[dict]) -> None:
        for offset in range(0, 14):
            for slot, tm in enumerate(("10:00", "15:30"), start=1):
                customer = customers[(offset * 2 + slot) % len(customers)]
                person = personnel[(offset + slot) % len(personnel)]
                self.insert(
                    "appointments",
                    {
                        "customer_name": customer["name"],
                        "customer": customer["name"],
                        "customer_id": customer["id"],
                        "phone": customer["phone"],
                        "date": day(offset),
                        "time": tm,
                        "description": f"{SEED_TAG} günlük detaylı test randevusu {offset + 1}-{slot}",
                        "status": "Planlandı" if offset > 0 else "Bugün",
                        "created_at": now(),
                        "personnel": person["name"],
                        "personnel_name": person["name"],
                        "personnel_id": person["id"],
                        "device": "Kamera sistemi" if slot == 1 else "PC bakım",
                        "brand": "Demo",
                        "model": "Test",
                        "urgency": "Normal",
                        "type": "Servis Randevusu",
                        "notes": "Her güne iki ayrı test randevusu.",
                        "is_auto_created": 0,
                    },
                )

    def seed_finance(self, customers: list[dict], devices: list[dict]) -> list[int]:
        bank_ids = []
        for idx, bank in enumerate(("Ziraat", "Garanti BBVA", "Akbank", "İş Bankası"), start=1):
            bid = self.insert(
                "bank_accounts",
                {
                    "bank_name": bank,
                    "account_holder": "AYEC Pro Demo",
                    "account_name": f"{bank} Demo Hesabı",
                    "account_no": f"{SEED_TAG}-BA-{idx:03d}",
                    "account_number": f"{SEED_TAG}-BA-{idx:03d}",
                    "branch": "Kadıköy",
                    "branch_code": f"{100 + idx}",
                    "iban": f"TR{idx:02d}000000000000000000{idx:04d}",
                    "currency": "TRY",
                    "is_active": 1,
                    "created_at": now(),
                    "current_balance": 150000 + idx * 50000,
                    "is_deleted": 0,
                },
            )
            bank_ids.append(bid)

        for idx in range(1, 61):
            customer = customers[idx % len(customers)]
            is_income = idx % 3 != 0
            amount = 750 + idx * 185
            self.insert(
                "accounting",
                {
                    "type": "Gelir" if is_income else "Gider",
                    "category": random.choice(["Servis", "Parça Satışı", "Proje", "Personel", "Kira", "Kargo"]),
                    "amount": amount,
                    "try_equivalent": amount,
                    "currency": "TRY",
                    "exchange_rate": 1,
                    "original_amount": amount,
                    "description": f"{SEED_TAG} finansal test hareketi #{idx}",
                    "date": day(-idx % 30),
                    "created_at": now(),
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "is_invoiced": 1 if idx % 4 == 0 else 0,
                    "payment_method": random.choice(["Nakit", "Banka", "Kredi Kartı"]),
                    "bank_account_id": bank_ids[idx % len(bank_ids)],
                    "tracking_no": devices[idx % len(devices)]["tracking_no"],
                    "ref_no": f"{SEED_TAG}-ACC-{idx:04d}",
                    "is_deleted": 0,
                },
            )

        for idx, bid in enumerate(bank_ids[:3], start=1):
            card_id = self.insert(
                "bank_cards",
                {
                    "bank_account_id": bid,
                    "card_name": f"{SEED_TAG} Demo Kart {idx}",
                    "card_last4": f"{3300 + idx}",
                    "card_limit": 75000 + idx * 25000,
                    "current_debt": 12000 + idx * 3000,
                    "due_day": 20 + idx,
                    "statement_day": 10 + idx,
                    "is_active": 1,
                    "created_at": now(),
                },
            )
            _ = card_id

        for idx in range(1, 4):
            amount = 120000 + idx * 60000
            loan_id = self.insert(
                "loans",
                {
                    "bank_account_id": bank_ids[idx % len(bank_ids)],
                    "bank_name": ["Ziraat", "Akbank", "İş Bankası"][idx - 1],
                    "amount": amount,
                    "interest_rate": 3.25 + idx / 10,
                    "term_months": 12,
                    "start_date": day(-idx * 20),
                    "total_payment": amount * 1.35,
                    "description": f"{SEED_TAG} demo kredi kaydı",
                    "status": "Aktif",
                    "created_at": now(),
                    "loan_type": "Taksitli",
                    "loan_title": f"{SEED_TAG} Demo İşletme Kredisi {idx}",
                    "kkdf_rate": 15,
                    "bsmv_rate": 15,
                    "is_deleted": 0,
                },
            )
            for inst in range(1, 7):
                total = round((amount * 1.35) / 12, 2)
                self.insert(
                    "loan_installments",
                    {
                        "loan_id": loan_id,
                        "installment_no": inst,
                        "due_date": day(inst * 30 - idx * 2),
                        "total_amount": total,
                        "principal_part": round(total * 0.78, 2),
                        "interest_part": round(total * 0.14, 2),
                        "kkdf_amount": round(total * 0.04, 2),
                        "bsmv_amount": round(total * 0.04, 2),
                        "status": "Bekliyor" if inst > 1 else "Ödendi",
                        "paid_date": day(-1) if inst == 1 else None,
                        "created_at": now(),
                        "is_deleted": 0,
                    },
                )

        for idx in range(1, 13):
            self.insert(
                "checks_notes",
                {
                    "type": "Çek" if idx % 2 else "Senet",
                    "direction": "Giriş" if idx % 3 else "Çıkış",
                    "portfolio_no": f"{SEED_TAG}-PORT-{idx:04d}",
                    "amount": 10000 + idx * 2750,
                    "due_date": day(5 + idx * 3),
                    "issuer": customers[idx % len(customers)]["name"],
                    "recipient": "AYEC Pro Demo",
                    "bank_name": random.choice(["Ziraat", "Garanti", "Akbank"]),
                    "branch_name": "Kadıköy",
                    "account_no": f"CHK-{idx:05d}",
                    "check_no": f"CN-{idx:05d}",
                    "description": f"{SEED_TAG} çek/senet test kaydı",
                    "status": random.choice(["Portföyde", "Tahsil Edildi", "Ciro Edildi"]),
                    "created_at": now(),
                },
            )
        return bank_ids

    def seed_projects(self, customers: list[dict], personnel: list[dict], parts: list[dict], bank_ids: list[int]) -> None:
        project_specs = [
            ("Akıllı Villa Otomasyon Projesi", "Devam Ediyor", 850000),
            ("Site Kamera Güvenlik Yenileme", "Planlandı", 620000),
            ("Kurumsal PC Laboratuvar Kurulumu", "Devam Ediyor", 430000),
            ("Otomotiv Servis Atölye Altyapısı", "Tamamlandı", 510000),
            ("Perakende Mağaza Alarm ve Network", "Devam Ediyor", 375000),
        ]
        for pidx, (name, status, budget) in enumerate(project_specs, start=1):
            customer = customers[(pidx * 3) % len(customers)]
            project_id = self.insert(
                "projects",
                {
                    "name": name,
                    "start_date": day(-30 + pidx),
                    "end_date": day(60 + pidx * 10),
                    "budget": budget,
                    "cost": budget * 0.62,
                    "payment_method": "Banka",
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "status": status,
                    "description": f"{SEED_TAG} proje modülü detaylı test kaydı",
                    "ref_no": f"{SEED_TAG}-PRJ-{pidx:03d}",
                    "currency": "TRY",
                    "exchange_rate": 1,
                    "created_at": now(),
                    "is_archived": 1 if status == "Tamamlandı" else 0,
                },
            )
            for sidx, job in enumerate(("Elektrik", "Kablo Kanalları", "Montaj", "Yazılım Konfigürasyon"), start=1):
                self.insert(
                    "subcontractors",
                    {
                        "project_id": project_id,
                        "name": f"{job} Taşeron Demo {pidx}-{sidx}",
                        "job_type": job,
                        "total_contract_amount": 35000 + sidx * 12500,
                        "contact_info": f"05{sidx}5 777 {pidx}{sidx:03d}",
                        "created_at": now(),
                    },
                )
            unit_ids = []
            for uidx in range(1, 11):
                unit_id = self.insert(
                    "project_units",
                    {
                        "project_id": project_id,
                        "block_name": f"Blok {chr(64 + ((uidx - 1) % 3) + 1)}",
                        "floor_no": str((uidx - 1) // 3 + 1),
                        "unit_no": f"{100 + uidx}",
                        "status": random.choice(["Satılık", "Rezerve", "Satıldı", "Teslim Edildi", "Devam Ediyor"]),
                        "price": 75000 + uidx * 12500,
                        "unit_type": "Daire/Oda",
                        "area": 85 + uidx * 3,
                        "unit_price": 1100 + uidx * 20,
                        "total_price": 75000 + uidx * 12500,
                        "customer_id": customers[(uidx + pidx) % len(customers)]["id"] if uidx % 3 == 0 else None,
                        "description": f"{SEED_TAG} proje ünitesi test kaydı",
                        "unit_kind": "Daire",
                        "created_at": now(),
                    },
                )
                unit_ids.append(unit_id)
                for ridx, room in enumerate(("Salon", "Mutfak", "Oda"), start=1):
                    room_id = self.insert(
                        "project_units",
                        {
                            "project_id": project_id,
                            "block_name": f"Blok {chr(64 + ((uidx - 1) % 3) + 1)}",
                            "floor_no": str((uidx - 1) // 3 + 1),
                            "unit_no": f"{100 + uidx}-{room}",
                            "status": "Devam Ediyor",
                            "unit_type": room,
                            "area": 20 + ridx * 5,
                            "parent_unit_id": unit_id,
                            "unit_kind": "Oda",
                            "description": f"{SEED_TAG} oda bazlı kurulum hedefi",
                            "created_at": now(),
                        },
                    )
                    for part in random.sample(parts, k=2):
                        self.insert(
                            "project_unit_products",
                            {
                                "unit_id": room_id,
                                "project_id": project_id,
                                "part_id": part["id"],
                                "part_name": part["name"],
                                "part_code": part["code"],
                                "quantity": random.choice([1, 2, 3]),
                                "notes": f"{SEED_TAG} proje oda kurulum ürünü",
                                "added_at": now(),
                            },
                        )
            for tidx in range(1, 9):
                is_income = tidx % 3 == 0
                self.insert(
                    "project_transactions",
                    {
                        "project_id": project_id,
                        "type": "Gelir" if is_income else "Gider",
                        "category": "Daire Satışı" if is_income else random.choice(["Malzeme", "İşçilik", "Taşeron Ödemesi"]),
                        "amount": 15000 + tidx * 8500,
                        "payment_method": random.choice(["Nakit", "Banka", "Çek"]),
                        "date": day(-tidx),
                        "description": f"{SEED_TAG} proje finans hareketi",
                        "status": "Ödendi" if tidx % 2 else "Ödenmedi",
                        "paid_date": day(-tidx + 1) if tidx % 2 else None,
                        "ref_table": "project_units",
                        "ref_id": unit_ids[tidx % len(unit_ids)],
                        "created_at": now(),
                        "original_amount": 15000 + tidx * 8500,
                        "original_currency": "TRY",
                        "exchange_rate": 1,
                    },
                )
            for sale_idx, unit_id in enumerate(unit_ids[:3], start=1):
                buyer = customers[(sale_idx + pidx) % len(customers)]
                price = 90000 + sale_idx * 30000
                self.insert(
                    "project_unit_sales",
                    {
                        "project_id": project_id,
                        "unit_id": unit_id,
                        "buyer_name": buyer["name"],
                        "buyer_phone": buyer["phone"],
                        "buyer_email": f"buyer{sale_idx}.{SEED_TAG.lower()}@example.com",
                        "buyer_address": "Demo proje satış adresi",
                        "delivery_date": day(30 + sale_idx),
                        "sales_rep": personnel[sale_idx % len(personnel)]["name"],
                        "notes": f"{SEED_TAG} proje satış test kaydı",
                        "list_price": price * 1.08,
                        "sale_price": price,
                        "down_payment_rate": 25,
                        "down_payment_amount": price * 0.25,
                        "remaining_balance": price * 0.75,
                        "payment_plan": "3 taksit demo plan",
                        "documents": "Kimlik, sözleşme, teslim formu",
                        "created_at": now(),
                    },
                )
            _ = bank_ids

    def seed_other_menus(self, customers: list[dict], personnel: list[dict], devices: list[dict], parts: list[dict], bank_ids: list[int]) -> None:
        for idx in range(1, 16):
            self.insert("reminders", {
                "tracking_no": devices[idx % len(devices)]["tracking_no"],
                "title": f"Demo Hatırlatma {idx}",
                "message": f"{SEED_TAG} takip ve uyarı test hatırlatması",
                "due_date": day(idx),
                "date": day(idx),
                "personnel": personnel[idx % len(personnel)]["name"],
                "description": "Menü test verisi",
                "status": "Bekliyor",
                "is_read": 0,
                "created_at": now(),
            })
        for idx in range(1, 9):
            customer = customers[idx % len(customers)]
            self.insert("contracts", {
                "customer_id": customer["id"],
                "title": f"Demo Bakım Sözleşmesi {idx}",
                "start_date": day(-idx * 5),
                "end_date": day(365 - idx),
                "contract_type": "Periyodik Bakım",
                "price": 18000 + idx * 2500,
                "status": "Aktif",
                "description": f"{SEED_TAG} sözleşme modülü test kaydı",
                "created_at": now(),
            })
        for idx in range(1, 13):
            self.insert("tickets", {
                "subject": f"{SEED_TAG} Destek Talebi {idx}",
                "customer_name": customers[idx % len(customers)]["name"],
                "priority": random.choice(["Düşük", "Orta", "Yüksek"]),
                "status": random.choice(["Açık", "İşlemde", "Kapalı"]),
                "description": "Destek menüsü test açıklaması",
                "created_at": now(),
                "updated_at": now(),
            })
        for idx in range(1, 9):
            self.insert("kb_articles", {
                "title": f"{SEED_TAG} Bilgi Bankası Makalesi {idx}",
                "category": random.choice(["Servis", "Stok", "Finans", "Proje"]),
                "content": "Detaylı test için demo bilgi bankası içeriği.",
                "created_at": now(),
            })
        for idx in range(1, 6):
            self.insert("announcements", {
                "title": f"{SEED_TAG} Duyuru {idx}",
                "content": "Masaüstü test verisi duyuru içeriği.",
                "created_at": now(),
            })
        for idx in range(1, 13):
            self.insert("notifications", {
                "category": random.choice(["stock", "device", "payment", "general"]),
                "title": f"Demo Bildirim {idx}",
                "content": f"{SEED_TAG} bildirim merkezi test kaydı",
                "link_id": str(idx),
                "status": "unread" if idx % 3 else "read",
                "priority": "high" if idx % 4 == 0 else "normal",
                "created_at": now(),
            })
            self.insert("assistant_notifications", {
                "message": f"{SEED_TAG} asistan kritik/test bildirimi {idx}",
                "type": random.choice(["stock", "finance", "appointment"]),
                "is_critical": 1 if idx % 5 == 0 else 0,
                "status": "unread",
                "created_at": now(),
            })
        for idx in range(1, 16):
            self.insert("services", {
                "name": f"{SEED_TAG} Servis Hizmeti {idx}",
                "category": random.choice(["Teknik Servis", "Otomotiv", "Güvenlik", "PC"]),
                "price": 500 + idx * 150,
                "description": "Hizmet listesi test verisi",
                "is_active": 1,
                "created_at": now(),
            })
            self.insert("service_definitions", {
                "service_name": f"{SEED_TAG} Tanımlı Hizmet {idx}",
                "name": f"{SEED_TAG} Tanımlı Hizmet {idx}",
                "category": random.choice(["Bakım", "Kurulum", "Onarım"]),
                "price": 400 + idx * 120,
                "duration": 45 + idx * 5,
                "description": "Servis tanımları test verisi",
                "is_active": 1,
                "created_at": now(),
            })
        for idx, customer in enumerate(customers, start=1):
            self.insert("customer_services", {
                "customer_id": customer["id"],
                "name": f"Demo periyodik bakım {idx}",
                "qty": 1,
                "unit_price": 1250 + idx * 50,
                "total": 1250 + idx * 50,
                "notes": f"{SEED_TAG} müşteri hizmet geçmişi",
                "date": day(-idx),
            })
            for nidx in range(2):
                self.insert("customer_notes", {
                    "customer_id": customer["id"],
                    "note_type": "Servis Notu" if nidx == 0 else "Finans Notu",
                    "content": f"{SEED_TAG} müşteri 360 notu {idx}-{nidx + 1}",
                    "created_at": now(),
                })
        for idx in range(1, 9):
            loaner_id = self.insert("loaner_devices", {
                "device_type": random.choice(["Telefon", "Laptop", "Tablet"]),
                "brand_model": f"Demo Emanet Cihaz {idx}",
                "serial_mac": f"{SEED_TAG}-LOANER-{idx:04d}",
                "status": "Müşteride" if idx <= 5 else "Depoda",
                "daily_penalty_fee": 100,
                "shelf_no": f"E-{idx}",
                "notes": "Emanet cihaz test kaydı",
                "created_at": now(),
            })
            if idx <= 5:
                customer = customers[idx % len(customers)]
                self.insert("loaner_transactions", {
                    "device_id": loaner_id,
                    "customer_name": customer["name"],
                    "customer_phone": customer["phone"],
                    "tracking_no": f"{SEED_TAG}-LOANER-TRX-{idx:04d}",
                    "condition_out": "Sağlam teslim edildi",
                    "condition_in": "",
                    "date_given": day(-idx),
                    "expected_return": day(7 + idx),
                    "status": "Aktif",
                    "created_at": now(),
                })
        for idx in range(1, 11):
            self.insert("logistics", {
                "tracking_no": f"{SEED_TAG}-KARGO-{idx:04d}",
                "customer_name": customers[idx % len(customers)]["name"],
                "cargo_firm": random.choice(["Yurtiçi", "MNG", "Aras"]),
                "cargo_company": random.choice(["Yurtiçi", "MNG", "Aras"]),
                "cargo_no": f"KRG{idx:06d}",
                "type": "Giden" if idx % 2 else "Gelen",
                "direction": "Giden" if idx % 2 else "Gelen",
                "status": random.choice(["Hazırlanıyor", "Yolda", "Teslim Edildi"]),
                "date": day(-idx),
                "description": "Lojistik test kaydı",
                "created_at": now(),
            })
        for idx in range(1, 13):
            customer = customers[idx % len(customers)]
            self.insert("e_invoices", {
                "uuid": f"{SEED_TAG}-EINV-{idx:04d}",
                "invoice_type": "E-Arşiv",
                "receiver_name": customer["name"],
                "receiver_vkn": f"90000{idx:05d}",
                "amount": 1500 + idx * 450,
                "status": random.choice(["Taslak", "Gönderildi", "Onaylandı"]),
                "json_data": json.dumps({"seed": SEED_TAG, "line": idx}, ensure_ascii=False),
                "created_at": now(),
                "updated_at": now(),
            })
        for idx in range(1, 9):
            device = devices[idx % len(devices)]
            self.insert("external_warranty_tracking", {
                "internal_tracking_no": f"{SEED_TAG}-EXT-{idx:04d}",
                "customer_name": device["customer"]["name"],
                "product_name": "Garantiye gönderilen demo ürün",
                "external_service_name": random.choice(["Distribütör A", "Yetkili Servis B"]),
                "external_service_no": f"EXTSRV{idx:05d}",
                "sent_date": day(-idx),
                "outbound_cargo_no": f"OUT{idx:05d}",
                "inbound_cargo_no": f"IN{idx:05d}" if idx % 2 else "",
                "status": random.choice(["Gönderildi", "İncelemede", "Tamamlandı"]),
                "notes": "Dış servis takip test kaydı",
                "created_at": now(),
            })
        for idx, part in enumerate(parts[:12], start=1):
            self.insert("product_bank_mappings", {
                "item_type": "part",
                "item_id": part["id"],
                "bank_account_id": bank_ids[idx % len(bank_ids)],
                "default_kdv_rate": 20,
                "default_category": f"{SEED_TAG} ürün-banka eşlemesi",
                "created_at": now(),
                "updated_at": now(),
            })
        for idx in range(1, 8):
            self.insert("audit_logs", {
                "user_id": 1,
                "table_name": "seed_demo",
                "user": "demo_admin",
                "action": "seed",
                "details": f"{SEED_TAG} denetim logu test kaydı {idx}",
                "created_at": now(),
            })
            self.insert("sms_log", {
                "phone": customers[idx % len(customers)]["phone"],
                "message": f"{SEED_TAG} SMS log test mesajı",
                "status": "sent",
                "sent_at": now(),
                "created_at": now(),
            })

    def seed_automotive(self, customers: list[dict], devices: list[dict], parts: list[dict]) -> None:
        brands = [("Toyota", "Corolla"), ("Ford", "Focus"), ("Renault", "Megane"), ("Fiat", "Egea")]
        for idx in range(1, 9):
            customer = customers[idx % len(customers)]
            brand, model = brands[idx % len(brands)]
            plate = f"34 DEM {idx:02d}"
            vehicle_id = self.insert("customer_vehicles", {
                "customer_id": customer["id"],
                "plate": plate,
                "brand": brand,
                "model": model,
                "year": str(2018 + idx % 6),
                "vehicle_type": "Binek",
                "engine_type": "1.6",
                "fuel_type": "Benzin",
                "inspection_due_date": day(180 + idx),
                "inspection_notice_date": day(150 + idx),
                "qr_token": f"{SEED_TAG}-VEH-{idx:04d}",
                "last_known_odometer": 45000 + idx * 6500,
                "notes": "Otomotiv müşteri aracı test kaydı",
                "is_active": 1,
                "created_at": now(),
                "updated_at": now(),
            })
            card_id = self.insert("vehicle_maintenance_cards", {
                "vehicle_id": vehicle_id,
                "customer_id": customer["id"],
                "customer_name": customer["name"],
                "customer_phone": customer["phone"],
                "vehicle_plate": plate,
                "vehicle_brand": brand,
                "vehicle_model": model,
                "vehicle_year": str(2018 + idx % 6),
                "vehicle_type": "Binek",
                "engine_type": "1.6",
                "fuel_type": "Benzin",
                "inspection_due_date": day(180 + idx),
                "inspection_notice_date": day(150 + idx),
                "qr_token": f"{SEED_TAG}-CARD-{idx:04d}",
                "odometer": 45000 + idx * 6500,
                "service_date": day(-idx),
                "next_maintenance_date": day(90 + idx),
                "appointment_date": day(30 + idx),
                "appointment_time": "09:30",
                "notes": f"{SEED_TAG} otomotiv bakım kartı",
                "reminder_date": day(80 + idx),
                "created_by": "demo_admin",
                "created_at": now(),
                "updated_at": now(),
            })
            for item in ("Yağ değişimi", "Filtre kontrol", "Fren balata", "Antifriz", "Cam suyu"):
                self.insert("vehicle_maintenance_items", {
                    "card_id": card_id,
                    "item_type": "Bakım",
                    "item_label": item,
                    "performed": 1,
                    "interval_days": 180,
                    "interval_km": 10000,
                    "next_due_date": day(180 + idx),
                    "next_due_odometer": 55000 + idx * 6500,
                    "notes": f"{SEED_TAG} bakım kalemi",
                })
            device = devices[idx % len(devices)]
            quote_id = self.insert("automotive_quote_forms", {
                "device_id": device["id"],
                "tracking_no": device["tracking_no"],
                "customer_id": customer["id"],
                "vehicle_id": vehicle_id,
                "vehicle_plate": plate,
                "quote_no": f"{SEED_TAG}-OTO-TEK-{idx:04d}",
                "approval_status": "Onaylandı",
                "approval_note": "Demo onay",
                "discount_amount": 250,
                "subtotal": 5000 + idx * 300,
                "total_amount": 4750 + idx * 300,
                "created_at": now(),
                "updated_at": now(),
            })
            for part in random.sample(parts, k=2):
                self.insert("automotive_quote_items", {
                    "quote_form_id": quote_id,
                    "item_type": "Parça",
                    "item_name": part["name"],
                    "qty": 1,
                    "unit_price": part["price"],
                    "approved": 1,
                    "source_status": "Stoktan",
                    "note": f"{SEED_TAG} otomotiv teklif kalemi",
                })
            req_id = self.insert("automotive_parts_requests", {
                "device_id": device["id"],
                "tracking_no": device["tracking_no"],
                "customer_id": customer["id"],
                "vehicle_id": vehicle_id,
                "vehicle_plate": plate,
                "supplier_name": "Demo Tedarikçi",
                "status": "Talep Edildi",
                "expected_date": day(7 + idx),
                "request_note": f"{SEED_TAG} otomotiv parça talebi",
                "created_at": now(),
                "updated_at": now(),
            })
            for part in random.sample(parts, k=2):
                self.insert("automotive_parts_request_items", {
                    "request_id": req_id,
                    "part_name": part["name"],
                    "qty": 1,
                    "oem_no": f"OEM-{idx}-{part['id']}",
                    "unit_cost": part["price"] * 0.7,
                    "note": "Demo talep kalemi",
                })

    def run(self) -> tuple[Path | None, dict[str, int]]:
        backup_path = self.backup()
        self.cleanup()
        customers = self.seed_customers()
        personnel = self.seed_personnel()
        security_parts, pc_parts = self.seed_parts()
        all_parts = security_parts + pc_parts
        devices = self.seed_devices(customers, personnel, security_parts, pc_parts)
        self.seed_appointments(customers, personnel)
        bank_ids = self.seed_finance(customers, devices)
        self.seed_projects(customers, personnel, all_parts, bank_ids)
        self.seed_other_menus(customers, personnel, devices, all_parts, bank_ids)
        self.seed_automotive(customers, devices, all_parts)
        self.cur.execute(
            "UPDATE parts SET stock=100 WHERE code LIKE ?",
            (f"{SEED_TAG}%",),
        )
        self.conn.commit()
        return backup_path, dict(sorted(self.counts.items()))


def main() -> int:
    seeder = Seeder()
    backup_path, counts = seeder.run()
    print("Comprehensive desktop test data seeded.")
    print(f"Database: {PathHelper.get_db_path()}")
    if backup_path:
        print(f"Backup: {backup_path}")
    print(json.dumps(counts, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
