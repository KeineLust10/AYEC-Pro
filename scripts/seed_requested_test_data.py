"""Seed linked desktop test data without removing real application records."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import Database
from src.utils.path_helper import PathHelper


SEED_TAG = "AYEC-TEST-FULL"
RATES = {"TRY": 1.0, "USD": 45.50, "EUR": 52.00}
STOCK_PER_ITEM = 30


def now_text(offset_days: int = 0) -> str:
    value = datetime.now() + timedelta(days=offset_days)
    return value.strftime("%Y-%m-%d %H:%M:%S")


def date_text(offset_days: int = 0) -> str:
    value = datetime.now() + timedelta(days=offset_days)
    return value.strftime("%Y-%m-%d")


def quote(identifier: str) -> str:
    if not identifier or not identifier.replace("_", "").isalnum():
        raise ValueError(f"Unsafe identifier: {identifier!r}")
    return f'"{identifier}"'


class RequestedTestDataSeeder:
    def __init__(self, db_name: str = "ayecpro.db") -> None:
        random.seed(20260726)
        self.db = Database(db_name=db_name)
        self.conn = self.db.conn
        self.cur = self.db.cursor
        self._columns: dict[str, set[str]] = {}
        self.counts: dict[str, int] = {}

    def table_exists(self, table: str) -> bool:
        row = self.cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None

    def columns(self, table: str) -> set[str]:
        if table not in self._columns:
            self._columns[table] = {
                str(row[1])
                for row in self.cur.execute(
                    f"PRAGMA table_info({quote(table)})"
                ).fetchall()
            }
        return self._columns[table]

    def insert(self, table: str, values: dict) -> int:
        available = self.columns(table)
        payload = {
            key: value for key, value in values.items() if key in available
        }
        if not payload:
            raise RuntimeError(f"No compatible columns found for {table}")
        names = ", ".join(quote(name) for name in payload)
        marks = ", ".join("?" for _ in payload)
        self.cur.execute(
            f"INSERT INTO {quote(table)} ({names}) VALUES ({marks})",
            tuple(payload.values()),
        )
        self.counts[table] = self.counts.get(table, 0) + 1
        return int(self.cur.lastrowid)

    def backup(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"before_{SEED_TAG.lower()}_{stamp}.db"
        path = self.db.backup_database(name)
        if not path:
            raise RuntimeError("Database backup could not be created")
        return str(path)

    def cleanup(self) -> None:
        self.conn.execute("PRAGMA foreign_keys=OFF")

        offer_ids = [
            int(row[0])
            for row in self.cur.execute(
                "SELECT id FROM offers WHERE offer_no LIKE ?",
                (f"{SEED_TAG}%",),
            ).fetchall()
        ]
        for offer_id in offer_ids:
            self.cur.execute(
                "DELETE FROM offer_items WHERE offer_id=?",
                (offer_id,),
            )
        self.cur.execute(
            "DELETE FROM offers WHERE offer_no LIKE ?",
            (f"{SEED_TAG}%",),
        )

        transaction_ids = [
            int(row[0])
            for row in self.cur.execute(
                """
                SELECT id
                FROM currency_transactions
                WHERE tracking_no LIKE ? OR description LIKE ?
                """,
                (f"{SEED_TAG}%", f"%{SEED_TAG}%"),
            ).fetchall()
        ]
        if transaction_ids and self.table_exists("payment_debt_links"):
            marks = ", ".join("?" for _ in transaction_ids)
            self.cur.execute(
                "DELETE FROM payment_debt_links "
                f"WHERE payment_txn_id IN ({marks}) "
                f"OR debt_txn_id IN ({marks})",
                tuple(transaction_ids + transaction_ids),
            )
        self.cur.execute(
            """
            DELETE FROM currency_transactions
            WHERE tracking_no LIKE ? OR description LIKE ?
            """,
            (f"{SEED_TAG}%", f"%{SEED_TAG}%"),
        )
        self.cur.execute(
            """
            DELETE FROM accounting
            WHERE ref_no LIKE ? OR tracking_no LIKE ? OR description LIKE ?
            """,
            (f"{SEED_TAG}%", f"{SEED_TAG}%", f"%{SEED_TAG}%"),
        )

        tracking_numbers = [
            str(row[0])
            for row in self.cur.execute(
                "SELECT tracking_no FROM devices WHERE tracking_no LIKE ?",
                (f"{SEED_TAG}%",),
            ).fetchall()
        ]
        for tracking_no in tracking_numbers:
            self.cur.execute(
                "DELETE FROM used_parts WHERE tracking_no=?",
                (tracking_no,),
            )
            self.cur.execute(
                "DELETE FROM device_tests WHERE tracking_no=?",
                (tracking_no,),
            )
        self.cur.execute(
            "DELETE FROM devices WHERE tracking_no LIKE ?",
            (f"{SEED_TAG}%",),
        )

        self.cur.execute(
            "DELETE FROM appointments WHERE description LIKE ?",
            (f"%{SEED_TAG}%",),
        )
        self.cur.execute(
            "DELETE FROM stock_movements WHERE description LIKE ?",
            (f"%{SEED_TAG}%",),
        )
        self.cur.execute(
            "DELETE FROM parts WHERE code LIKE ? OR description LIKE ?",
            (f"{SEED_TAG}%", f"%{SEED_TAG}%"),
        )
        self.cur.execute(
            "DELETE FROM personnel WHERE username LIKE ?",
            (f"{SEED_TAG.lower()}%",),
        )

        customer_ids = [
            int(row[0])
            for row in self.cur.execute(
                "SELECT id FROM customers WHERE email LIKE ?",
                (f"%{SEED_TAG.lower()}%",),
            ).fetchall()
        ]
        if customer_ids:
            marks = ", ".join("?" for _ in customer_ids)
            if self.table_exists("customer_currency_balances"):
                self.cur.execute(
                    f"DELETE FROM customer_currency_balances "
                    f"WHERE customer_id IN ({marks})",
                    tuple(customer_ids),
                )
            self.cur.execute(
                f"DELETE FROM customers WHERE id IN ({marks})",
                tuple(customer_ids),
            )

        self.cur.execute(
            "DELETE FROM exchange_rates WHERE source=?",
            (SEED_TAG,),
        )
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.counts.clear()

    def seed_rates(self) -> None:
        effective = date_text()
        for currency in ("USD", "EUR"):
            rate = RATES[currency]
            self.insert(
                "exchange_rates",
                {
                    "currency": currency,
                    "buying_rate": round(rate * 0.995, 4),
                    "selling_rate": rate,
                    "effective_date": effective,
                    "source": SEED_TAG,
                    "created_at": now_text(),
                },
            )
        self.conn.commit()

    def seed_customers(self) -> list[dict]:
        first_names = (
            "Ahmet",
            "Ay\u015fe",
            "Mehmet",
            "Zeynep",
            "Burak",
            "Elif",
            "Can",
            "Derya",
            "Murat",
            "Selin",
            "Kemal",
            "Esra",
            "Okan",
            "G\u00f6k\u00e7e",
            "Umut",
            "Buse",
            "Tolga",
            "\u0130rem",
            "Kaan",
            "Deniz",
        )
        last_names = (
            "Y\u0131lmaz",
            "Demir",
            "Kaya",
            "\u00c7elik",
            "\u015eahin",
            "\u00d6zt\u00fcrk",
            "Ayd\u0131n",
            "Arslan",
            "Do\u011fan",
            "K\u0131l\u0131\u00e7",
            "Ko\u00e7",
            "Bulut",
            "Polat",
            "Aksoy",
            "Turan",
            "G\u00fcne\u015f",
            "Kurt",
            "Yavuz",
            "\u00d6zkan",
            "Aslan",
        )
        rows = []
        for index in range(1, 201):
            first = first_names[(index - 1) % len(first_names)]
            last = last_names[((index - 1) // len(first_names)) % len(last_names)]
            name = f"Test M\u00fc\u015fterisi {index:03d} - {first} {last}"
            company = index % 5 == 0
            customer_id = self.insert(
                "customers",
                {
                    "name": name,
                    "phone": f"05{index % 50 + 30:02d}{index:07d}",
                    "phone2": f"0266{7000000 + index:07d}",
                    "email": (
                        f"musteri{index:03d}.{SEED_TAG.lower()}@example.com"
                    ),
                    "type": "Kurumsal" if company else "Bireysel",
                    "company_name": (
                        f"{first} {last} Test Teknoloji Ltd."
                        if company
                        else ""
                    ),
                    "tax_no": f"900{index:07d}" if company else "",
                    "tc_no": f"100{index:08d}"[:11],
                    "tax_office": "Balikesir",
                    "address": (
                        f"Test Mahallesi {index}. Sokak No:{index}, Balikesir"
                    ),
                    "city": "Balikesir",
                    "district": "Karesi" if index % 2 else "Altieylul",
                    "notes": (
                        f"{SEED_TAG} kapsamli masaustu test musterisi"
                    ),
                    "term_days": 30,
                    "limit_amount": 50000 + index * 250,
                    "sms_enabled": 1,
                    "is_problematic": 1 if index % 40 == 0 else 0,
                    "service_type": (
                        "Otomotiv" if index % 3 == 0 else "Teknik Servis"
                    ),
                    "created_at": now_text(-(index % 90)),
                    "updated_at": now_text(),
                    "is_deleted": 0,
                },
            )
            rows.append(
                {
                    "id": customer_id,
                    "name": name,
                    "phone": f"05{index % 50 + 30:02d}{index:07d}",
                }
            )
        self.conn.commit()
        return rows

    def seed_personnel(self) -> list[dict]:
        definitions = (
            ("Mert Usta", "Servis Ustasi", "Servis"),
            ("Seda Kalayci", "Musteri Temsilcisi", "Operasyon"),
            ("Ali Can", "Saha Teknisyeni", "Saha"),
            ("Ece Oner", "Muhasebe", "Finans"),
            ("Tuna Er", "Depo Sorumlusu", "Stok"),
        )
        rows = []
        for index, (name, role, department) in enumerate(definitions, 1):
            personnel_id = self.insert(
                "personnel",
                {
                    "name": name,
                    "username": f"{SEED_TAG.lower()}_personel_{index:02d}",
                    "password": "test1234",
                    "role": role,
                    "phone": f"0555000{index:04d}",
                    "salary": 35000 + index * 2500,
                    "commission": 2 + index,
                    "created_at": now_text(-30),
                    "email": (
                        f"personel{index:02d}.{SEED_TAG.lower()}@example.com"
                    ),
                    "active": 1,
                    "tc_no": f"200000000{index:02d}",
                    "department": department,
                    "status": "Aktif",
                    "last_seen": now_text(),
                    "is_deleted": 0,
                },
            )
            rows.append({"id": personnel_id, "name": name})
        self.conn.commit()
        return rows

    @staticmethod
    def product_definitions() -> list[dict]:
        rows = []
        pc_products = (
            "Intel Core i5 Islemci",
            "Intel Core i7 Islemci",
            "AMD Ryzen 5 Islemci",
            "AMD Ryzen 7 Islemci",
            "B760 Anakart",
            "AM5 Anakart",
            "16GB DDR4 RAM",
            "32GB DDR5 RAM",
            "500GB NVMe SSD",
            "1TB NVMe SSD",
            "2TB SATA SSD",
            "4TB HDD",
            "RTX 4060 Ekran Karti",
            "RX 7600 Ekran Karti",
            "650W PSU",
            "750W PSU",
            "ATX Kasa",
            "240mm Sivi Sogutma",
            "27 Inc Monitor",
            "Mekanik Klavye",
        )
        for index, name in enumerate(pc_products, 1):
            rows.append(
                {
                    "family": "PC",
                    "index": index,
                    "name": name,
                    "category": "Bilgisayar Bile\u015fenleri",
                    "currency": "USD",
                    "purchase": round(18 + index * 3.75, 2),
                    "sale": round(28 + index * 5.25, 2),
                    "brand": ("Asus", "MSI", "Kingston", "Intel")[index % 4],
                }
            )

        security_types = (
            "Bullet IP Kamera",
            "Dome IP Kamera",
            "Turret IP Kamera",
            "PTZ Kamera",
            "Termal Kamera",
            "NVR Kayit Cihazi",
            "DVR Kayit Cihazi",
            "PoE Switch",
            "Kamera Montaj Ayagi",
            "Junction Box",
            "Alarm Paneli",
            "PIR Sensor",
            "Duman Dedektoru",
            "Manyetik Kontak",
            "Siren",
            "Video Interkom",
            "Kart Okuyucu",
            "Network Kablo",
            "Guvenlik Diski",
            "Kamera Adaptoru",
        )
        counter = 0
        for type_index, product_type in enumerate(security_types, 1):
            for variant in range(1, 6):
                counter += 1
                rows.append(
                    {
                        "family": "CCTV",
                        "index": counter,
                        "name": f"{product_type} V{variant:02d}",
                        "category": "G\u00fcvenlik Sistemleri",
                        "currency": "USD",
                        "purchase": round(12 + type_index * 4.2 + variant, 2),
                        "sale": round(22 + type_index * 6.8 + variant * 1.5, 2),
                        "brand": (
                            "Hikvision",
                            "Dahua",
                            "HiLook",
                            "Uniview",
                            "TP-Link",
                        )[variant - 1],
                    }
                )

        smart_types = (
            "Akilli Role",
            "Akilli Anahtar",
            "Akilli Priz",
            "Akilli Termostat",
            "Kapi Sensoru",
            "Hareket Sensoru",
            "Su Baskini Sensoru",
            "Akilli Perde Motoru",
            "Merkezi Kontrol Unitesi",
            "Akilli Kapi Kilidi",
        )
        counter = 0
        for type_index, product_type in enumerate(smart_types, 1):
            for variant in range(1, 6):
                counter += 1
                rows.append(
                    {
                        "family": "SMART",
                        "index": counter,
                        "name": f"{product_type} V{variant:02d}",
                        "category": "Ak\u0131ll\u0131 Ev Sistemleri",
                        "currency": "EUR",
                        "purchase": round(8 + type_index * 3.4 + variant, 2),
                        "sale": round(15 + type_index * 5.1 + variant * 1.4, 2),
                        "brand": (
                            "WiiHOM",
                            "Shelly",
                            "Sonoff",
                            "Tuya",
                            "Aqara",
                        )[variant - 1],
                    }
                )
        return rows

    def seed_parts(self) -> list[dict]:
        rows = []
        for definition in self.product_definitions():
            code_prefix = {
                "PC": "PC",
                "CCTV": "GS",
                "SMART": "AE",
            }[definition["family"]]
            code = f"{code_prefix}-{definition['index']:03d}"
            part_id = self.insert(
                "parts",
                {
                    "name": definition["name"],
                    "part_name": definition["name"],
                    "brand": definition["brand"],
                    "stock": STOCK_PER_ITEM,
                    "price": definition["sale"],
                    "purchase_price": definition["purchase"],
                    "currency": definition["currency"],
                    "code": code,
                    "barcode": (
                        f"86926{len(rows) + 1:08d}"
                    ),
                    "category": definition["category"],
                    "min_stock": 5,
                    "description": (
                        f"{SEED_TAG} {definition['family']} test urunu"
                    ),
                    "shelf_number": (
                        f"{definition['family']}-"
                        f"R{definition['index'] % 10 + 1}"
                    ),
                    "created_at": now_text(),
                    "updated_at": now_text(),
                    "is_deleted": 0,
                },
            )
            self.insert(
                "stock_movements",
                {
                    "part_id": part_id,
                    "movement_type": "Giri\u015f",
                    "amount": STOCK_PER_ITEM,
                    "new_stock": STOCK_PER_ITEM,
                    "description": (
                        f"{SEED_TAG} ilk stok girisi: {definition['name']}"
                    ),
                    "created_at": now_text(),
                    "is_deleted": 0,
                },
            )
            row = dict(definition)
            row["id"] = part_id
            row["code"] = code
            rows.append(row)
        self.conn.commit()
        return rows

    def seed_stock_finance(self, parts: list[dict]) -> None:
        for part in parts:
            native_total = round(
                part["purchase"] * STOCK_PER_ITEM,
                2,
            )
            rate = RATES[part["currency"]]
            self.db.add_transaction(
                t_type="Gider",
                category="Stok Alimi",
                amount=round(native_total * rate, 2),
                description=(
                    f"{SEED_TAG} stok alimi | {part['name']} | "
                    f"{STOCK_PER_ITEM} adet"
                ),
                payment_method="Banka",
                tracking_no=f"{SEED_TAG}-STOCK-{part['id']}",
                ref_no=f"{SEED_TAG}-STK-{part['id']}",
                selected_services=[
                    {
                        "kind": "stock_purchase",
                        "name": part["name"],
                        "quantity": STOCK_PER_ITEM,
                        "unit_price": part["purchase"],
                        "currency": part["currency"],
                        "line_total": native_total,
                    }
                ],
                currency=part["currency"],
                original_amount=native_total,
                exchange_rate=rate,
            )

    def seed_devices(
        self,
        customers: list[dict],
        personnel: list[dict],
        parts: list[dict],
    ) -> list[dict]:
        pc_parts = [part for part in parts if part["family"] == "PC"]
        security_parts = [
            part for part in parts if part["family"] == "CCTV"
        ]
        smart_parts = [part for part in parts if part["family"] == "SMART"]
        definitions = (
            (
                "Laptop",
                "Dell",
                "Latitude 5420",
                pc_parts,
                "Cihaz acilmiyor ve guc almiyor",
            ),
            (
                "Masaustu PC",
                "Asus",
                "ProArt Workstation",
                pc_parts,
                "Goruntu gelmiyor ve sistem yavas",
            ),
            (
                "Kamera Sistemi",
                "Hikvision",
                "NVR-16",
                security_parts,
                "Kayit goruntuleri kesiliyor",
            ),
            (
                "Alarm Sistemi",
                "Dahua",
                "ARC-500",
                security_parts,
                "Sensorler duzensiz calisiyor",
            ),
            (
                "Akilli Ev Merkezi",
                "WiiHOM",
                "Hub Pro",
                smart_parts,
                "Otomasyon senaryolari calismiyor",
            ),
        )
        rows = []
        for index in range(1, 21):
            definition = definitions[(index - 1) % len(definitions)]
            customer = customers[index - 1]
            device_type, brand, model, pool, fault = definition
            tracking_no = f"{SEED_TAG}-SRV-{index:04d}"
            selected_parts = random.sample(pool, 3)
            labor_try = 1200 + index * 350
            parts_try = sum(
                part["sale"] * RATES[part["currency"]]
                for part in selected_parts
            )
            total_try = round(labor_try + parts_try, 2)
            device_id = self.insert(
                "devices",
                {
                    "tracking_no": tracking_no,
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "customer_contact": customer["phone"],
                    "device_type": device_type,
                    "device_brand": brand,
                    "device_model": model,
                    "serial_no": f"TEST-SN-{index:06d}",
                    "fault_category": "Donanim",
                    "urgency": "Normal" if index < 5 else "Acil",
                    "priority": "Normal" if index < 5 else "Yuksek",
                    "status": (
                        "Beklemede"
                        if index % 5 == 1
                        else "Islemde"
                        if index % 5 in (2, 3)
                        else "Test Ediliyor"
                        if index <= 15
                        else "Teslim Edildi"
                    ),
                    "entry_date": date_text(-index),
                    "estimated_date": date_text(index + 2),
                    "price": total_try,
                    "labor_cost": labor_try,
                    "cost_price": round(
                        sum(
                            part["purchase"] * RATES[part["currency"]]
                            for part in selected_parts
                        ),
                        2,
                    ),
                    "fault_description": fault,
                    "repair_details": (
                        "Ariza tespiti yapildi; parca degisimi ve test suruyor."
                    ),
                    "technician": personnel[(index - 1) % len(personnel)][
                        "name"
                    ],
                    "approval_status": "Onaylandi",
                    "payment_status": "Bekliyor",
                    "internal_notes": (
                        f"{SEED_TAG} serviste bulunan test cihazi"
                    ),
                    "accessories": "Adaptor, kablo",
                    "created_at": now_text(-index),
                    "updated_at": now_text(),
                    "delivered_at": (
                        now_text(-index + 2) if index > 15 else None
                    ),
                    "is_archived": 1 if index > 15 else 0,
                    "is_deleted": 0,
                },
            )
            for part in selected_parts:
                if not self.db.use_part(
                    part["id"],
                    quantity=1,
                    tracking_no=tracking_no,
                    commit=False,
                ):
                    raise RuntimeError(
                        f"Part could not be used: {part['code']}"
                    )
            self.conn.commit()
            for test_name, result in (
                ("Guc Testi", "Gecti"),
                ("Goruntu Testi", "Bekliyor"),
                ("Stres Testi", "Bekliyor"),
            ):
                self.insert(
                    "device_tests",
                    {
                        "tracking_no": tracking_no,
                        "test_name": test_name,
                        "result": result,
                        "note": f"{SEED_TAG} servis test kaydi",
                        "technician": personnel[
                            (index - 1) % len(personnel)
                        ]["name"],
                        "test_date": date_text(),
                    },
                )

            service_lines = [
                {
                    "type": "service",
                    "service": f"{device_type} servis isciligi",
                    "description": fault,
                    "qty": 1,
                    "price": labor_try,
                }
            ]
            for part in selected_parts:
                service_lines.append(
                    {
                        "type": "part",
                        "item_id": part["id"],
                        "service": part["name"],
                        "description": f"Ref: {tracking_no}",
                        "qty": 1,
                        "price": round(
                            part["sale"] * RATES[part["currency"]],
                            2,
                        ),
                    }
                )
            description = (
                f"{SEED_TAG} servis kaydi | {tracking_no}\n"
                + "\n".join(
                    f"{line_index}. {line['service']}"
                    for line_index, line in enumerate(service_lines, 1)
                )
            )
            if not self.db.add_currency_transaction(
                customer_id=customer["id"],
                amount=total_try,
                currency="TRY",
                transaction_type="DEBIT",
                exchange_rate=1,
                description=description,
                tracking_no=tracking_no,
            ):
                raise RuntimeError("Service debt could not be created")
            self.db.add_transaction(
                t_type="Gelir",
                category="Servis",
                amount=total_try,
                description=description,
                customer_name=customer["name"],
                customer_id=customer["id"],
                payment_method="Cari Hesap",
                tracking_no=tracking_no,
                ref_no=tracking_no,
                selected_services=service_lines,
                currency="TRY",
                original_amount=total_try,
            )
            payment = round(total_try * 0.50, 2) if index % 2 == 0 else 0
            if payment:
                payment_ref = f"{tracking_no}-PAY"
                self.db.add_currency_transaction(
                    customer_id=customer["id"],
                    amount=payment,
                    currency="TRY",
                    transaction_type="CREDIT",
                    exchange_rate=1,
                    description=(
                        f"{SEED_TAG} kismi servis tahsilati | {tracking_no}"
                    ),
                    tracking_no=payment_ref,
                )
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Tahsilat",
                    amount=payment,
                    description=(
                        f"{SEED_TAG} kismi servis tahsilati | {tracking_no}"
                    ),
                    customer_name=customer["name"],
                    customer_id=customer["id"],
                    payment_method="Nakit",
                    tracking_no=payment_ref,
                    ref_no=payment_ref,
                    currency="TRY",
                    original_amount=payment,
                )
            rows.append(
                {
                    "id": device_id,
                    "tracking_no": tracking_no,
                    "customer": customer,
                    "total_try": total_try,
                }
            )
        self.conn.commit()
        return rows

    def seed_customer_accounts(self, customers: list[dict]) -> None:
        for index, customer in enumerate(customers[5:45], 1):
            currency = ("TRY", "USD", "EUR")[index % 3]
            amount = (
                2500 + index * 175
                if currency == "TRY"
                else 100 + index * 7
            )
            rate = RATES[currency]
            tracking_no = f"{SEED_TAG}-CARI-{index:04d}"
            self.db.add_currency_transaction(
                customer_id=customer["id"],
                amount=amount,
                currency=currency,
                transaction_type="DEBIT",
                exchange_rate=rate,
                description=(
                    f"{SEED_TAG} test musteri borcu | {tracking_no}"
                ),
                tracking_no=tracking_no,
            )
            if index % 2 == 0:
                payment = round(amount * 0.40, 2)
                self.db.add_currency_transaction(
                    customer_id=customer["id"],
                    amount=payment,
                    currency=currency,
                    transaction_type="CREDIT",
                    exchange_rate=rate,
                    description=(
                        f"{SEED_TAG} test cari tahsilati | {tracking_no}"
                    ),
                    tracking_no=f"{tracking_no}-PAY",
                )
                self.db.add_transaction(
                    t_type="Gelir",
                    category="Tahsilat",
                    amount=round(payment * rate, 2),
                    description=(
                        f"{SEED_TAG} test cari tahsilati | {tracking_no}"
                    ),
                    customer_name=customer["name"],
                    customer_id=customer["id"],
                    payment_method="Banka",
                    tracking_no=f"{tracking_no}-PAY",
                    ref_no=f"{tracking_no}-PAY",
                    currency=currency,
                    original_amount=payment,
                    exchange_rate=rate,
                )

    def seed_appointments(
        self,
        customers: list[dict],
        personnel: list[dict],
    ) -> None:
        for day_offset in range(30):
            for slot, time_value in enumerate(("10:00", "15:30"), 1):
                index = day_offset * 2 + slot
                customer = customers[60 + index]
                person = personnel[(index - 1) % len(personnel)]
                self.insert(
                    "appointments",
                    {
                        "customer_name": customer["name"],
                        "customer": customer["name"],
                        "customer_id": customer["id"],
                        "phone": customer["phone"],
                        "date": date_text(day_offset),
                        "time": time_value,
                        "description": (
                            f"{SEED_TAG} aylik test randevusu "
                            f"{day_offset + 1:02d}-{slot}"
                        ),
                        "status": (
                            "Bugun" if day_offset == 0 else "Planlandi"
                        ),
                        "created_at": now_text(),
                        "personnel": person["name"],
                        "personnel_name": person["name"],
                        "personnel_id": person["id"],
                        "device": (
                            "Kamera Sistemi" if slot == 1 else "Bilgisayar"
                        ),
                        "brand": "Test",
                        "model": f"Model-{index:03d}",
                        "urgency": "Normal",
                        "type": "Servis Randevusu",
                        "notes": "Bir aylik test takvimi kaydi.",
                        "is_auto_created": 0,
                    },
                )
        self.conn.commit()

    def seed_offers(
        self,
        customers: list[dict],
        parts: list[dict],
    ) -> None:
        for index in range(1, 26):
            customer = customers[index - 1]
            selected = random.sample(parts, 3)
            items = []
            for part in selected:
                native_price = float(part["sale"])
                try_price = round(
                    native_price * RATES[part["currency"]],
                    2,
                )
                items.append(
                    {
                        "item_id": part["id"],
                        "type": "part",
                        "service": part["name"],
                        "description": (
                            f"{part['brand']} | {part['category']}"
                        ),
                        "brand": part["brand"],
                        "qty": 1 + index % 3,
                        "price": try_price,
                    }
                )
            subtotal = round(
                sum(item["qty"] * item["price"] for item in items),
                2,
            )
            vat_rate = 20.0
            vat_amount = round(subtotal * vat_rate / 100.0, 2)
            total = round(subtotal + vat_amount, 2)
            offer_no = f"{SEED_TAG}-TEK-{index:04d}"
            self.db.save_offer_record(
                {
                    "offer_no": offer_no,
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "company_name": "AYEC Pro Test Firmasi",
                    "contact_name": customer["name"],
                    "project_name": f"Test Teklifi {index:02d}",
                    "template_type": "modern",
                    "currency_code": "TRY",
                    "currency_symbol": "\u20ba",
                    "exchange_rate": 1,
                    "totals": {
                        "subtotal": subtotal,
                        "discount": 0,
                        "vat_rate": vat_rate,
                        "vat_amount": vat_amount,
                        "total": total,
                    },
                    "totals_try": {
                        "subtotal": subtotal,
                        "discount": 0,
                        "vat_rate": vat_rate,
                        "vat_amount": vat_amount,
                        "total": total,
                    },
                    "status": "created",
                    "source": "test_seed",
                    "pdf_path": "",
                    "items": items,
                }
            )
            self.counts["offers"] = self.counts.get("offers", 0) + 1
            self.counts["offer_items"] = (
                self.counts.get("offer_items", 0) + len(items)
            )

    def verify(self) -> dict:
        category_counts = {}
        for category, count in self.cur.execute(
            """
            SELECT category, COUNT(*)
            FROM parts
            WHERE description LIKE ?
            GROUP BY category
            ORDER BY category
            """,
            (f"%{SEED_TAG}%",),
        ).fetchall():
            category_counts[str(category)] = int(count)

        result = {
            "database": PathHelper.get_db_path(),
            "tag": SEED_TAG,
            "customers": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM customers WHERE email LIKE ?",
                    (f"%{SEED_TAG.lower()}%",),
                ).fetchone()[0]
            ),
            "personnel": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM personnel WHERE username LIKE ?",
                    (f"{SEED_TAG.lower()}%",),
                ).fetchone()[0]
            ),
            "parts": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM parts WHERE description LIKE ?",
                    (f"%{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "part_categories": category_counts,
            "appointments": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM appointments WHERE description LIKE ?",
                    (f"%{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "active_devices": int(
                self.cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM devices
                    WHERE tracking_no LIKE ?
                      AND COALESCE(is_archived, 0)=0
                      AND COALESCE(is_deleted, 0)=0
                    """,
                    (f"{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "devices": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM devices WHERE tracking_no LIKE ?",
                    (f"{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "used_parts": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM used_parts WHERE tracking_no LIKE ?",
                    (f"{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "offers": int(
                self.cur.execute(
                    "SELECT COUNT(*) FROM offers WHERE offer_no LIKE ?",
                    (f"{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "offer_items": int(
                self.cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM offer_items
                    WHERE offer_id IN (
                        SELECT id FROM offers WHERE offer_no LIKE ?
                    )
                    """,
                    (f"{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "finance_rows": int(
                self.cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM accounting
                    WHERE ref_no LIKE ? OR description LIKE ?
                    """,
                    (f"{SEED_TAG}%", f"%{SEED_TAG}%"),
                ).fetchone()[0]
            ),
            "customer_account_rows": int(
                self.cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM currency_transactions
                    WHERE tracking_no LIKE ? OR description LIKE ?
                    """,
                    (f"{SEED_TAG}%", f"%{SEED_TAG}%"),
                ).fetchone()[0]
            ),
            "stock_min": int(
                self.cur.execute(
                    "SELECT MIN(stock) FROM parts WHERE description LIKE ?",
                    (f"%{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "stock_max": int(
                self.cur.execute(
                    "SELECT MAX(stock) FROM parts WHERE description LIKE ?",
                    (f"%{SEED_TAG}%",),
                ).fetchone()[0]
            ),
            "integrity_check": str(
                self.cur.execute("PRAGMA integrity_check").fetchone()[0]
            ),
        }
        expected = {
            "customers": 200,
            "personnel": 5,
            "parts": 170,
            "appointments": 60,
            "devices": 20,
            "active_devices": 15,
            "used_parts": 60,
            "offers": 25,
            "offer_items": 75,
        }
        for key, expected_value in expected.items():
            if result[key] != expected_value:
                raise RuntimeError(
                    f"Verification failed for {key}: "
                    f"{result[key]} != {expected_value}"
                )
        if sorted(category_counts.values()) != [20, 50, 100]:
            raise RuntimeError(
                f"Unexpected part category counts: {category_counts}"
            )
        if result["integrity_check"] != "ok":
            raise RuntimeError(
                f"Database integrity check failed: "
                f"{result['integrity_check']}"
            )
        return result

    def run(self) -> tuple[str, dict]:
        backup_path = self.backup()
        self.cleanup()
        self.seed_rates()
        customers = self.seed_customers()
        personnel = self.seed_personnel()
        parts = self.seed_parts()
        self.seed_stock_finance(parts)
        self.seed_devices(customers, personnel, parts)
        self.seed_customer_accounts(customers)
        self.seed_appointments(customers, personnel)
        self.seed_offers(customers, parts)
        self.conn.commit()
        return backup_path, self.verify()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="ayecpro.db")
    args = parser.parse_args()
    seeder = RequestedTestDataSeeder(args.db)
    backup_path, result = seeder.run()
    result["backup"] = backup_path
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
