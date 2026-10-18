# -*- coding: utf-8 -*-
"""Capture the actual desktop shell and routed sales page without networking."""

import os
import argparse
import socket
import sys
from datetime import datetime
from unittest.mock import patch

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['AYEC_VISUAL_ACCEPTANCE'] = '1'

from tools.quality.desktop_visual_acceptance import ROOT, seed_visual_fixture
from PyQt6.QtCore import QDate, QEvent, QPoint, QSettings, QTemporaryDir, QTime, QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap, QShowEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QLayout, QPushButton, QWidget
from src.database import Database
from src.ui.main_window import MainWindow
from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page
from src.ui.pages.sales_hub_page import SalesHubPage
from src.utils.theme_manager import ThemeManager


class ReferenceCaptureWindow(MainWindow):
    def start_initial_tasks(self):
        pass

    def schedule_ui_task(self, priority, callback, label=None):
        pass

    def configure_auto_web_sync(self, enabled):
        pass


def seed_brands_reference(db):
    cursor = db.cursor
    reference_rows = [
        ("Ak\u0131ll\u0131 Ayd\u0131nlatma", "Tapo", 1),
        ("Ak\u0131ll\u0131 Ev Merkezi", "Aqara", 1),
        ("Ak\u0131ll\u0131 Ev Merkezi", "Google", 1),
        ("Ak\u0131ll\u0131 Saat", "Apple", 1),
        ("Ak\u0131ll\u0131 Saat", "Samsung", 1),
        ("Cep Telefonu", "Apple iPhone", 1),
        ("Cep Telefonu", "Xiaomi", 1),
        ("Laptop / Diz\u00fcst\u00fc", "ASUS", 1),
        ("Laptop / Diz\u00fcst\u00fc", "Dell", 1),
        ("All In One PC", "Lenovo", 1),
    ]
    existing = [tuple(row) for row in cursor.execute(
        "SELECT device_type, brand, is_active FROM device_brands ORDER BY id"
    ).fetchall()]
    reference_keys = {(row[0], row[1]) for row in reference_rows}
    remainder = [row for row in existing if (row[0], row[1]) not in reference_keys]
    brand_rows = list(reference_rows)
    used_keys = {(row[0], row[1]) for row in brand_rows}
    group_names = {row[0] for row in brand_rows}
    for row in remainder:
        if row[0] not in group_names and len(group_names) < 18:
            brand_rows.append(row)
            used_keys.add((row[0], row[1]))
            group_names.add(row[0])
    reference_fillers = [
        ("Ak\u0131ll\u0131 Kamera", "Google Nest", 1),
        ("Ak\u0131ll\u0131 Priz", "TP-Link", 1),
        ("Robot S\u00fcp\u00fcrge", "Roborock", 1),
        ("Termostat", "Google Nest", 1),
        ("Masa\u00fcst\u00fc PC", "Lenovo", 1),
        ("All In One", "HP", 1),
        ("Mini PC", "Intel NUC", 1),
        ("IoT Cihazlari", "Sonoff", 1),
    ]
    for row in reference_fillers:
        if len(group_names) >= 18:
            break
        if row[0] not in group_names:
            brand_rows.append(row)
            used_keys.add((row[0], row[1]))
            group_names.add(row[0])
    for row in remainder:
        if len(brand_rows) >= 48:
            break
        if (row[0], row[1]) not in used_keys:
            brand_rows.append(row)
            used_keys.add((row[0], row[1]))
    cursor.execute("DELETE FROM device_brands")
    cursor.executemany(
        "INSERT INTO device_brands (device_type, brand, is_active) VALUES (?, ?, ?)",
        brand_rows,
    )
    counts = (
        ("Ak\u0131ll\u0131 Ayd\u0131nlatma", "Tapo", 28),
        ("Ak\u0131ll\u0131 Ev Merkezi", "Aqara", 14),
        ("Ak\u0131ll\u0131 Ev Merkezi", "Google", 52),
        ("Ak\u0131ll\u0131 Saat", "Apple", 114),
        ("Ak\u0131ll\u0131 Saat", "Samsung", 87),
        ("Cep Telefonu", "Apple iPhone", 342),
        ("Cep Telefonu", "Xiaomi", 198),
        ("Laptop / Diz\u00fcst\u00fc", "ASUS", 176),
        ("Laptop / Diz\u00fcst\u00fc", "Dell", 92),
        ("All In One PC", "Lenovo", 43),
    )
    cursor.execute("DELETE FROM devices")
    service_rows = []
    sequence = 1
    for device_type, brand, count in counts:
        for _index in range(count):
            service_rows.append((
                "REF-BRAND-{:04d}".format(sequence), "Reference Fixture", brand,
                device_type, "Teslim Edildi", "2026-10-01", 0,
            ))
            sequence += 1
    cursor.executemany(
        "INSERT INTO devices (tracking_no, customer_name, device_brand, device_type, status, entry_date, price) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        service_rows,
    )
    db.conn.commit()


def seed_product_groups_reference(db):
    groups = (
        ('Laptop', 14), ('Elektronik Cihaz', 8), ('Cep Telefonu', 12),
        ('Bilgisayar', 9), ('All In One', 5), ('Ak\u0131ll\u0131 Saat', 7),
        ('Ak\u0131ll\u0131 Priz', 4), ('Ak\u0131ll\u0131 Kamera', 6),
        ('Ak\u0131ll\u0131 Ev Merkezi', 3), ('Ak\u0131ll\u0131 Ayd\u0131nlatma', 5),
        ('Ekran', 2), ('Yaz\u0131c\u0131', 2), ('A\u011f Cihaz\u0131', 2),
        ('Sunucu', 2), ('G\u00fc\u00e7 Kayna\u011f\u0131', 2), ('Oyun Konsolu', 2),
        ('Televizyon', 2), ('Di\u011fer', 2),
    )
    examples = (
        ('Asus', 'Lenovo', 'Dell'), ('Sony', 'Philips', 'Samsung'),
        ('Apple', 'Samsung', 'Xiaomi'), ('HP', 'Dell', 'Toplama'),
        ('iMac', 'Lenovo', 'HP'), ('Apple Watch', 'Garmin', 'Huawei'),
        ('Tuya', 'Sonoff', 'TP-Link'), ('Dahua', 'Hikvision', 'Ezviz'),
        ('Aqara', 'Fibaro', 'Tuya'), ('Philips Hue', 'Yeelight', 'IKEA'),
    )
    shared_brands = ['Reference Brand {:02d}'.format(index) for index in range(1, 30)]
    cursor = db.cursor
    cursor.execute('DELETE FROM product_groups')
    cursor.execute('DELETE FROM device_brands')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    old = '2026-08-01 12:00:00'
    cursor.executemany(
        'INSERT INTO product_groups (name, is_active, created_at, updated_at) VALUES (?, 1, ?, ?)',
        [(name, now if index < 2 else old, now) for index, (name, _) in enumerate(groups)],
    )
    brand_rows = []
    filler_index = 0
    for group_index, (group_name, brand_count) in enumerate(groups):
        selected = list(examples[group_index]) if group_index < len(examples) else []
        while len(selected) < brand_count:
            selected.append(shared_brands[filler_index % len(shared_brands)])
            filler_index += 1
        brand_rows.extend((group_name, brand, 1) for brand in selected[:brand_count])
    cursor.executemany(
        'INSERT INTO device_brands (device_type, brand, is_active) VALUES (?, ?, ?)',
        brand_rows,
    )
    cursor.execute("UPDATE devices SET device_type='Laptop & PC', status='Teslim Edildi'")
    existing = cursor.execute('SELECT COUNT(*) FROM devices').fetchone()[0]
    extra_rows = []
    for index in range(max(0, 1480 - existing)):
        device_type = 'Laptop & PC' if index < max(0, 622 - existing) else groups[index % len(groups)][0]
        status = 'Tamirde' if index < max(0, 94 - min(existing, 94)) else 'Teslim Edildi'
        extra_rows.append((
            'REF-PG-{:04d}'.format(index + 1), 'Reference Fixture', 'AYEC',
            'Service Device {:04d}'.format(index + 1), status,
            '2026-10-01', 0, 'Normal', device_type,
        ))
    if extra_rows:
        cursor.executemany(
            'INSERT INTO devices (tracking_no, customer_name, device_brand, device_model, status, entry_date, price, priority, device_type) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            extra_rows,
        )
    cursor.execute("UPDATE devices SET status='Tamirde' WHERE id IN (SELECT id FROM devices ORDER BY id LIMIT 94)")
    db.conn.commit()


def seed_check_notes_reference(db):
    cursor = db.cursor
    cursor.execute('DELETE FROM checks_notes')
    rows = [
        ('\u00c7ek', 'Giri\u015f (Al\u0131nan)', 'PF-0001', 71050.0, '2026-10-21', 'Ahmet Y\u0131lmaz (Y\u0131lmaz Ticaret)', 'AYEC Demo Firma', 'Garanti BBVA', 'Kad\u0131k\u00f6y R\u0131ht\u0131m \u015eubesi (102)', '102', 'CK-8849201', 'Reference check', 'Portf\u00f6yde', ''),
        ('Senet', 'Giri\u015f (Al\u0131nan)', 'PF-0002', 41650.0, '2026-11-05', 'Ay\u015fe Demir', '\u015eah\u0131s Senedi (Kefilli)', '\u0130\u015f Bankas\u0131', '\u00dc' 'mraniye \u00c7ar\u015f\u0131 (412)', '412', 'SNT-2026-09', 'Reference note', 'Portf\u00f6yde', ''),
        ('\u00c7ek', 'Giri\u015f (Al\u0131nan)', 'PF-0003', 156800.0, '2026-11-20', 'Mehmet Kaya Lojistik A.\u015e.', 'M\u00fc\u015fteri \u00c7eki', 'Akbank T.A.\u015e.', 'Be\u015fikta\u015f', '778', 'CK-9912048', 'Bank clearance', 'Ciro Edildi', ''),
        ('Senet', 'Giri\u015f (Al\u0131nan)', 'PF-0004', 30380.0, '2026-12-05', 'Zeynep \u00c7elik', 'AYEC Demo Firma Portf\u00f6y', 'Yap\u0131 Kredi', 'Mecidiyek\u00f6y (778)', '778', 'SNT-2026-14', 'Reference note', 'Portf\u00f6yde', ''),
    ]
    monthly = (500.0, 500.0, 550.0, 520.0, 600.0)
    for index, amount_usd in enumerate(monthly, 1):
        record_type = '\u00c7ek' if index in (1, 3, 4) else 'Senet'
        day = 8 + index * 3
        rows.append((record_type, 'Giri\u015f (Al\u0131nan)', 'PF-{:04d}'.format(index + 4), amount_usd * 49,
                     '2026-10-{:02d}'.format(day), 'Reference Customer {:02d}'.format(index), 'AYEC Pro',
                     'Garanti BBVA', 'Kadikoy', '102', 'CK-REF-{:04d}'.format(index), 'Reference portfolio', 'Portf\u00f6yde', ''))
    for index in range(5):
        record_type = '\u00c7ek'
        due = '2026-11-{:02d}'.format(10 + index * 4)
        rows.append((record_type, 'Giri\u015f (Al\u0131nan)', 'PF-{:04d}'.format(index + 10), 2773.4 * 49,
                     due, 'Reference Customer {:02d}'.format(index + 6), 'AYEC Pro', 'Akbank', 'Besiktas',
                     '778', 'CK-REF-{:04d}'.format(index + 6), 'Reference portfolio', 'Portf\u00f6yde', ''))
    for index in range(4):
        rows.append(('\u00c7ek', 'Giri\u015f (Al\u0131nan)', 'PF-{:04d}'.format(index + 15), 2400.0 * 49,
                     '2026-12-{:02d}'.format(3 + index * 5), 'Reference Customer {:02d}'.format(index + 11), 'AYEC Pro',
                     'Akbank', 'Besiktas', '778', 'CK-REF-{:04d}'.format(index + 11), 'Bank clearance', 'Ciro Edildi', ''))
    for index in range(5):
        rows.append(('\u00c7ek', '\u00c7\u0131k\u0131\u015f (Verilen)', 'PF-OWN-{:02d}'.format(index + 1), 1798.6 * 49,
                     '2026-11-{:02d}'.format(12 + index * 3), 'AYEC Pro', 'Reference Payee {:02d}'.format(index + 1),
                     'Yapi Kredi', 'Mecidiyekoy', '778', 'OWN-REF-{:04d}'.format(index + 1), 'Own portfolio check', 'Portf\u00f6yde', ''))
    cursor.executemany(
        'INSERT INTO checks_notes (type, direction, portfolio_no, amount, due_date, issuer, recipient, bank_name, branch_name, account_no, check_no, description, status, image_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows,
    )
    db.conn.commit()
    db.set_setting('default_currency', 'USD')
    cursor.execute("UPDATE exchange_rates SET buying_rate=49.0, selling_rate=49.0 WHERE currency='USD'")
    cursor.execute("UPDATE exchange_rates SET buying_rate=53.4210, selling_rate=53.4210 WHERE currency='EUR'")
    db.conn.commit()


def seed_labor_services_reference(db):
    db.cursor.execute("UPDATE exchange_rates SET buying_rate=?, selling_rate=? WHERE currency=?", (32.42, 32.42, "USD"))
    rows = [
        ("Termal Macun & Fan Temizli\u011fi", "Masa\u00fcst\u00fc ve Laptop cihazlar i\u00e7in so\u011futucu blok, fan ve Arctic MX-4 macun yenileme", "Periyodik Bak\u0131m", 45, 650, "#SRV-101", 1),
        ("Anakart BGA Reballing / GPU \u00c7ip Onar\u0131m\u0131", "Lazerli BGA istasyonunda lehim yenileme ve mikroskop alt\u0131nda faz hatlar\u0131 testi", "Donan\u0131m & Lehim", 180, 2450, "#SRV-204", 1),
        ("Format, Orijinal Lisans & Driver Optimizasyonu", "Windows 11 Pro kurulumu, t\u00fcm \u00fcretici s\u00fcr\u00fcc\u00fcleri ve temel ofis bile\u015fenleri testi", "Yaz\u0131l\u0131m & Kurulum", 60, 500, "#SRV-308", 1),
        ("Laptop IPS / OLED Ekran De\u011fi\u015fim \u0130\u015f\u00e7ili\u011fi", "Panel hari\u00e7 saf i\u015f\u00e7ilik, \u00e7er\u00e7eve yap\u0131\u015ft\u0131r\u0131c\u0131 bantlar\u0131n tazelenmesi ve piksel kontrol\u00fc", "Donan\u0131m & Lehim", 40, 450, "#SRV-112", 1),
        ("Yerinde A\u011f, Router & IP Kamera Montaj Ke\u015ffi", "M\u00fc\u015fteri adresinde saatlik saha m\u00fchendislik ve yap\u0131sal kablolama analizleri", "Saha & Montaj", 120, 1200, "#SRV-502", 1),
        ("Ultrasonik Banyo ile S\u0131v\u0131 Temas\u0131 Oksit Giderme", "\u00d6zel kimyasal sol\u00fcsyonunda 40kHz titre\u015fimli devre kart\u0131 y\u0131kama ve f\u0131r\u0131nlama", "Donan\u0131m & Lehim", 90, 950, "#SRV-119", 0),
    ]
    db.get_services_list()
    db.cursor.execute("DELETE FROM services")
    categories = (["Donan\u0131m & Lehim"] * 11 + ["Yaz\u0131l\u0131m & Kurulum"] * 8 + ["Periyodik Bak\u0131m"] * 5 + ["Saha & Montaj"] * 4)
    for index in range(6, 34):
        category = categories[index - 6]
        rows.append((f"Teknik Servis Iscilik Kalemi {index + 1}", "Standart servis iscilik tanimi", category, 30 + (index % 7) * 15, 350 + index * 25 + (117 if index == 33 else 0), f"#SRV-{600 + index}", 0 if index == 31 else 1))
    for name, description, category, duration, price, code, active in rows:
        db.add_service(name, price, description, code, "TRY", price_try=price, is_active=active)
        db.cursor.execute(
            "UPDATE services SET service_category=?, duration_minutes=?, vat_rate=20 WHERE barcode=?",
            (category, duration, code),
        )
    db.conn.commit()
    usd_values = {"#SRV-101": 20.00, "#SRV-204": 75.00, "#SRV-308": 15.50, "#SRV-112": 14.00, "#SRV-502": 37.00, "#SRV-119": 29.50}
    for barcode, usd_price in usd_values.items():
        db.cursor.execute("UPDATE services SET price_usd=? WHERE barcode=?", (usd_price, barcode))
    db.conn.commit()


def seed_report_templates_reference(db):
    """Seed the temporary screenshot database with the visible Part 7 rows."""
    rows = [
        (1, "Teknik Servis::Bilgisayar::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "G\u00d6R\u00dcNT\u00dc YOK (Ekrana sinyal gelmiyor, fanlar d\u00f6n\u00fcyor)", 1, 1, "Giri\u015f Kayd\u0131 & Fi\u015f", "F1"),
        (9, "Teknik Servis::Bilgisayar::\u0130\u015flem Detay\u0131", "FORMAT ATILDI / YAZILIM YEN\u0130LEND\u0130 (Sistem g\u00fcncellendi, s\u00fcr\u00fcc\u00fcler kuruldu)", 1, 2, "Teknisyen \u00c7\u00f6z\u00fcm\u00fc", "F2"),
        (14, "Teknik Servis::Bilgisayar::Gizli Not", "TEST OK (STRES TEST\u0130 GE\u00c7T\u0130) (AIDA64 30dk stabil)", 1, 3, "Sadece \u0130\u00e7 Servis", ""),
        (18, "Teknik Servis::Bilgisayar::Aksesuar", "Orijinal G\u00fc\u00e7 Adapt\u00f6r\u00fc & G\u00fc\u00e7 Kablosu", 1, 4, "Kabul Tutana\u011f\u0131", "F4"),
        (24, "Teknik Servis::Bilgisayar::Cihaz Testi", "LCD Panel Renk & \u00d6l\u00fc Piksel Kontrol\u00fc", 1, 5, "\u00c7\u0131k\u0131\u015f Kalite Formu", "F5"),
        (36, "Teknik Servis::Cep Telefonu::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "\u00d6N CAM \u00c7ATLAK / EKRAN KIRIK", 1, 6, "Kabul Formu", "F5"),
        (44, "Teknik Servis::Cep Telefonu::\u0130\u015flem Detay\u0131", "OR\u0130J\u0130NAL EKRAN & DOKUNMAT\u0130K DE\u011e\u0130\u015e\u0130M\u0130 YAPILDI", 1, 7, "Fatura & Rapor", ""),
        (49, "Teknik Servis::Cep Telefonu::Gizli Not", "TEST OK (STRES TEST\u0130 GE\u00c7T\u0130)", 1, 8, "Sadece \u0130\u00e7 Servis", ""),
        (53, "Teknik Servis::Cep Telefonu::Aksesuar", "SIM KART VE HAFIZA KARTI", 1, 9, "G\u00fcvenlik / \u0130ade", "F7"),
        (59, "Teknik Servis::Cep Telefonu::Cihaz Testi", "Dokunmatik Ekran ve Sens\u00f6r Kontrol\u00fc", 1, 10, "\u00c7\u0131k\u015f Kalite Formu", "F8"),
        (75, "Teknik Servis::G\u00fcvenlik Sistemleri::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "KAMERA G\u00d6R\u00dcNT\u00dc VERM\u0130YOR", 1, 11, "Giri\u015f Kayd\u0131 & Fi\u015f", "F9"),
    ]
    category_specs = (
        ("Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", 25, "Giri\u015f Kayd\u0131 & Fi\u015f", ("G\u00d6R\u00dcNT\u00dc YOK", "A\u00c7ILMIYOR", "\u015eARJ ALMIYOR", "KAMERA G\u00d6R\u00dcNT\u00dc VERM\u0130YOR")),
        ("\u0130\u015flem Detay\u0131", 32, "Teknisyen \u00c7\u00f6z\u00fcm\u00fc", ("FORMAT ATILDI / YAZILIM YEN\u0130LEND\u0130", "OR\u0130J\u0130NAL PAR\u00c7A TAKILDI", "BA\u011eLANTI NOKTASI ONARILDI")),
        ("Cihaz Testi", 14, "\u00c7\u0131k\u0131\u015f Kalite Formu", ("LCD PANEL RENK KONTROL\u00dc", "DOKUNMAT\u0130K EKRAN TEST\u0130", "P\u0130L SA\u011eLIK TEST\u0130")),
        ("Aksesuar", 13, "Kabul Tutana\u011f\u0131", ("G\u00dc\u00c7 ADAPT\u00d6R\u00dc VE KABLO", "SIM KART VE HAFIZA KARTI", "OR\u0130J\u0130NAL KUTU")),
        ("Gizli Not", 8, "Sadece \u0130\u00e7 Servis", ("TEST OK (STRES TEST\u0130 GE\u00c7T\u0130)", "M\u00dc\u015eTER\u0130YE B\u0130LG\u0130 VER\u0130LD\u0130")),
    )
    scopes = ("Bilgisayar", "Cep Telefonu", "Tablet", "G\u00fcvenlik Sistemleri", "Ak\u0131ll\u0131 Ev")
    next_id = 100
    next_order = len(rows) + 1
    for category_name, count, usage_area, labels in category_specs:
        for index in range(count):
            scope = scopes[index % len(scopes)]
            label = labels[index % len(labels)]
            shortcut = "F{}".format((index % 9) + 1) if index % 3 else ""
            rows.append((
                next_id,
                "Teknik Servis::{}::{}".format(scope, category_name),
                label,
                1,
                next_order,
                usage_area,
                shortcut,
            ))
            next_id += 1
            next_order += 1
    db.cursor.execute("DELETE FROM fast_notes")
    db.cursor.executemany(
        "INSERT INTO fast_notes "
        "(id,category,label,is_active,display_order,display_category,title) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    db.conn.commit()


def seed_quick_notes_reference(db):
    """Seed the screenshot database with the visible quick-note rows."""
    rows = [
        (1, "Teknik Servis::Bilgisayar::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "G\u00d6R\u00dcNT\u00dc YOK", 1, 0, "Bilgisayar", "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi"),
        (9, "Teknik Servis::Bilgisayar::\u0130\u015flem Detay\u0131", "FORMAT ATILDI", 1, 0, "Bilgisayar", "\u0130\u015flem Detay\u0131"),
        (14, "Teknik Servis::Bilgisayar::Gizli Not", "TEST OK", 1, 0, "Bilgisayar", "Gizli Not"),
        (18, "Teknik Servis::Bilgisayar::Aksesuar", "G\u00fc\u00e7 Adapt\u00f6r\u00fc", 1, 0, "Bilgisayar", "Aksesuar"),
        (24, "Teknik Servis::Bilgisayar::Cihaz Testi", "LCD G\u00f6r\u00fcnt\u00fc", 1, 0, "Bilgisayar", "Cihaz Testi"),
        (36, "Teknik Servis::Cep Telefonu::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "EKRAN KIRIK", 1, 0, "Cep Telefonu", "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi"),
        (44, "Teknik Servis::Cep Telefonu::\u0130\u015flem Detay\u0131", "Ekran De\u011fi\u015fti", 1, 0, "Cep Telefonu", "\u0130\u015flem Detay\u0131"),
        (49, "Teknik Servis::Cep Telefonu::Gizli Not", "TEST OK", 1, 0, "Cep Telefonu", "Gizli Not"),
        (53, "Teknik Servis::Cep Telefonu::Aksesuar", "SIM Kart", 1, 0, "Cep Telefonu", "Aksesuar"),
        (59, "Teknik Servis::Cep Telefonu::Cihaz Testi", "Dokunmatik Ekran", 1, 0, "Cep Telefonu", "Cihaz Testi"),
        (75, "Teknik Servis::G\u00fcvenlik Sistemleri::Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", "KAMERA G\u00d6R\u00dcNT\u00dc VERM\u0130YOR", 1, 0, "G\u00fcvenlik Sistemleri", "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi"),
    ]
    db.cursor.execute("DELETE FROM fast_notes")
    db.cursor.executemany(
        "INSERT INTO fast_notes "
        "(id,category,label,is_active,display_order,display_category,title) "
        "VALUES (?,?,?,?,?,?,?)",
        rows,
    )
    db.conn.commit()


def seed_credit_reference(db):
    db.cursor.execute("DELETE FROM loan_installments")
    db.cursor.execute("DELETE FROM loans")
    loan_id = db.add_loan(
        bank_name="Garanti BBVA (Garanti Bankas\u0131)", principal=89760,
        interest_rate=24, months=36, start_date="2026-11-01",
        total_payment=126720, description="\u015eirket Ara\u00e7 & Donan\u0131m Finansman\u0131",
    )
    if not loan_id:
        raise AssertionError("The credit reference record could not be created")
    paid_dates = ("2026-11-28", "2026-12-30", "2027-01-29", "2027-02-28")
    db.cursor.executemany(
        "INSERT INTO loan_installments "
        "(loan_id,installment_no,due_date,total_amount,principal_part,interest_part,status,paid_date) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            (loan_id, number, f"{2026 + (number + 10) // 12:04d}-{(number + 10) % 12 + 1:02d}-01",
             3520.0, 3520.0, 0.0, "\u00d6dendi" if number <= 4 else "Bekliyor",
             paid_dates[number - 1] if number <= 4 else None)
            for number in range(1, 37)
        ],
    )
    db.conn.commit()


def seed_service_list_reference(db):
    rows = (
        (15, "Burak \u015eahin", "+90 532 *** ** 15", "AYECTest Cihaz 15", "AC-99415-X", "Teslim Edildi", "-", "2026-09-21", 2400, "Normal", ""),
        (14, "Derya Ayd\u0131n", "+90 544 *** ** 14", "AYECTest Cihaz 14", "AC-99414-B", "Teslim Edildi", "-", "2026-09-21", 2300, "Normal", ""),
        (13, "Murat Arslan", "+90 533 *** ** 13", "AYECTest Cihaz 13", "AC-99413-K", "Teslim Edildi", "2026-09-21", "2026-09-21", 2200, "Normal", ""),
        (12, "Elif Y\u0131lmaz", "+90 555 *** ** 12", "AYECTest Cihaz 12", "AC-99412-M", "Teslim Edildi", "2026-09-21", "2026-09-21", 2100, "Normal", ""),
        (11, "Can Y\u0131lmaz", "+90 531 *** ** 11", "AYECTest Cihaz 11", "AC-99411-L", "Teslim Edildi", "2026-09-21", "2026-09-21", 2000, "Normal", ""),
        (10, "Kaan Y\u0131lmaz", "+90 536 *** ** 10", "AYECTest Cihaz 10", "AC-99410-Q", "Teslim Edildi", "-", "2026-09-21", 1900, "Normal", ""),
        (9, "Selin Y\u0131lmaz", "+90 535 *** ** 09", "AYECTest Cihaz 09", "AC-99409-R", "Teslim Edildi", "2026-09-21", "2026-09-21", 1800, "Normal", ""),
        (8, "Tolga Acar", "+90 538 *** ** 08", "AYECTest Cihaz 08", "AC-99408-T", "Test S\u00fcrecinde", "S\u00fcre\u00e7te", "2026-09-21", 1700, "Y\u00fcksek", ""),
        (7, "Emre Kaya", "+90 532 *** ** 07", "iPhone 14 Pro Max", "IP-88412-TR", "Par\u00e7a Bekliyor", "-", "2026-09-20", 3850, "Normal", ""),
        (6, "Gizem Demir", "+90 542 *** ** 06", "MacBook Pro 16 M2", "MB-44109-AP", "Onar\u0131mda", "\u0130\u015flemde", "2026-09-20", 4500, "Acil (VIP)", ""),
        (5, "Serkan Y\u0131ld\u0131z", "+90 537 *** ** 05", "Samsung Galaxy S23 Ultra", "SM-99052-KR", "Kargoda", "Kargoda", "2026-09-19", 1650, "Normal", "Kargo"),
        (4, "Okan \u00c7elik", "+90 530 *** ** 04", "Dell XPS 15 9520", "DL-77204-US", "Teslim Edildi", "2026-09-20", "2026-09-18", 1450, "Normal", ""),
        (3, "Ay\u015fe Ko\u00e7", "+90 533 *** ** 03", "iPad Pro 12.9 M1", "IP-55301-EU", "Onayland\u0131", "Onayland\u0131", "2026-09-17", 1100, "Normal", ""),
        (2, "Ahmet Y\u00fccel", "+90 541 *** ** 02", "Sony PlayStation 5", "PS-33201-JP", "Teslim Edildi", "2026-09-18", "2026-09-16", 950, "Normal", ""),
        (1, "Kemal Aksoy", "+90 535 *** ** 01", "Lenovo ThinkPad X1", "LN-11904-DE", "Teslim Edildi", "2026-09-17", "2026-09-15", 1250, "Normal", ""),
    )
    for number, name, phone, model, serial, status, exit_date, entry_date, price, urgency, delivery_type in rows:
        db.cursor.execute(
            "UPDATE devices SET customer_name=?, customer_contact=?, device_brand=?, "
            "device_model=?, serial_no=?, status=?, exit_date=?, entry_date=?, price=?, "
            "urgency=?, delivery_type=? WHERE tracking_no=?",
            (name, phone, model, "", serial, status, exit_date, entry_date, price,
             urgency, delivery_type, f"DEMO-SRV-{number:04d}"),
        )
    db.conn.commit()
    db.set_setting("currency", "USD")
    db.set_setting("service_revenue_target", "30000")


def seed_service_status_assistant_reference(db):
    cursor = db.cursor
    fixtures = {
        "appointments": [{
            "customer_name": "Derya Aydin",
            "phone": "5551234567",
            "date": QDate.currentDate().toString("yyyy-MM-dd"),
            "time": "10:30",
            "description": "Laptop teslim kontrolu",
            "status": "Bekliyor",
            "created_at": "2026-10-18 09:00:00",
        }],
        "parts": [{"name": "Guc adaptoru", "stock": 1, "min_stock": 2, "is_deleted": 0}],
        "personnel": [
            {"name": "Burak Sahin", "role": "Teknisyen", "status": "Sahada", "is_active": 1, "active": 1, "is_deleted": 0},
            {"name": "Emre Usta", "role": "Teknisyen", "status": "Atolyede", "is_active": 1, "active": 1, "is_deleted": 0},
            {"name": "Serkan Can", "role": "Saha Teknisyeni", "status": "Gorevde", "is_active": 1, "active": 1, "is_deleted": 0},
        ],
    }
    for table, rows in fixtures.items():
        columns = {row[1] for row in cursor.execute('PRAGMA table_info("{}")'.format(table)).fetchall()}
        cursor.execute('DELETE FROM "{}"'.format(table))
        for record in rows:
            selected = [(name, value) for name, value in record.items() if name in columns]
            names = ", ".join('"{}"'.format(name) for name, _value in selected)
            placeholders = ", ".join("?" for _name, _value in selected)
            cursor.execute(
                'INSERT INTO "{}" ({}) VALUES ({})'.format(table, names, placeholders),
                [value for _name, value in selected],
            )
    db.conn.commit()


def seed_customer_management_reference(db):
    db.conn.commit()
    db.conn.execute("PRAGMA foreign_keys=OFF")
    customer_ids = db.cursor.execute(
        "SELECT id FROM customers ORDER BY id"
    ).fetchall()
    child_tables = []
    for table_row in db.cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall():
        table_name = str(table_row[0])
        columns = {
            column[1]
            for column in db.cursor.execute(
                'PRAGMA table_info("{}")'.format(table_name.replace('"', '""'))
            ).fetchall()
        }
        if "customer_id" in columns:
            child_tables.append(table_name)

    def swap_customer_ids(left, right, temporary):
        for table_name in child_tables:
            table_sql = '"{}"'.format(table_name.replace('"', '""'))
            db.cursor.execute(
                "UPDATE {} SET customer_id=? WHERE customer_id=?".format(table_sql),
                (temporary, left),
            )
            db.cursor.execute(
                "UPDATE {} SET customer_id=? WHERE customer_id=?".format(table_sql),
                (left, right),
            )
            db.cursor.execute(
                "UPDATE {} SET customer_id=? WHERE customer_id=?".format(table_sql),
                (right, temporary),
            )
        db.cursor.execute("UPDATE customers SET id=? WHERE id=?", (temporary, left))
        db.cursor.execute("UPDATE customers SET id=? WHERE id=?", (left, right))
        db.cursor.execute("UPDATE customers SET id=? WHERE id=?", (right, temporary))

    existing_ids = {int(row[0]) for row in customer_ids}
    if {3, 25}.issubset(existing_ids):
        swap_customer_ids(3, 25, 90003)
    if {4, 19}.issubset(existing_ids):
        swap_customer_ids(4, 19, 90004)
    if {5, 15}.issubset(existing_ids):
        swap_customer_ids(5, 15, 90005)
    db.conn.commit()
    db.conn.execute("PRAGMA foreign_keys=ON")
    updates = (
        ("Ahmet Y\u0131lmaz", "0555 000 0001", "demo1@example.test", "Bireysel", "", "Kad\u0131k\u00f6y", "\u0130stanbul", "VIP", 1),
        ("Ay\u015fe Demir", "0555 000 0002", "demo2@example.test", "Bireysel", "", "\u00c7ankaya", "Ankara", "", 2),
        ("Bar\u0131\u015f \u00c7evik", "0555 000 0025", "demo25@example.test", "Bireysel", "", "Ata\u015fehir", "\u0130stanbul", "", 25),
        ("Berk Eren", "0555 000 0019", "demo19@example.test", "Bireysel", "", "Sar\u0131yer", "\u0130stanbul", "", 19),
        ("Burak \u015eahin", "0555 000 0015", "demo15@example.test", "Bireysel", "", "Kad\u0131k\u00f6y", "\u0130stanbul", "", 15),
        ("Zeynep Acar", "0555 000 0006", "zeynep@example.test", "Bireysel", "", "\u0130zmir", "\u0130zmir", "", 6),
    )
    db.cursor.executemany(
        "UPDATE customers SET name=?, phone=?, email=?, type=?, company_name=?, district=?, city=?, contract_type=? WHERE id=?",
        updates,
    )
    reference_customers = (
        (32, "Ceyda Kaya Teknoloji", "0555 000 00 32", "info@kayatech.test", "Kurumsal Bayi", "Ceyda Kaya Teknoloji", "Alt\u0131eyl\u00fcl", "Bal\u0131kesir", "", 0),
        (44, "Mert \u00d6zt\u00fcrk", "0555 000 00 44", "mert@ozturk.test", "Bireysel", "", "\u00c7ankaya", "Ankara", "", 1),
        (58, "TeknoEv Otomasyon A.\u015e.", "0232 400 00 12", "info@teknoev.com", "Kurumsal", "TeknoEv Otomasyon A.\u015e.", "Konak", "\u0130zmir", "VIP", 0),
    )
    db.cursor.executemany(
        "INSERT OR IGNORE INTO customers (id, name, phone, email, type, company_name, district, city, contract_type, is_problematic) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        reference_customers,
    )
    db.cursor.execute(
        "UPDATE customers SET type='Bireysel' WHERE COALESCE(is_partner, 0)=0"
    )
    db.cursor.execute(
        "UPDATE customers SET type='Kurumsal' WHERE id IN (3, 6, 7, 8, 9, 10)"
    )
    db.cursor.execute("UPDATE customers SET type='Kurumsal Bayi' WHERE id=32")
    db.cursor.execute("UPDATE customers SET type='Bireysel' WHERE id=44")
    db.cursor.execute("UPDATE customers SET type='Kurumsal' WHERE id=58")
    db.cursor.execute(
        "UPDATE customers SET contract_type='VIP' WHERE id IN (1, 11, 12, 13, 14, 16, 17, 58)"
    )
    db.cursor.execute("UPDATE customers SET is_problematic=1 WHERE id=44")
    db.cursor.execute("DELETE FROM customer_currency_balances")
    db.cursor.executemany(
        "INSERT INTO customer_currency_balances (customer_id, currency, balance, last_updated) VALUES (?, ?, ?, ?)",
        [
            (1, "TRY", 8100.0, "2026-10-05"),
            (20, "TRY", 0.001, "2026-10-05"),
            (21, "TRY", 0.001, "2026-10-05"),
            (58, "TRY", 14200.0, "2026-10-05"),
            (1, "USD", 235.0, "2026-10-05"),
            (44, "TRY", -1450.0, "2026-10-05"),
        ],
    )
    db.cursor.execute("DELETE FROM devices")
    db.cursor.executemany(
        "INSERT INTO devices (tracking_no, customer_name, device_brand, device_model, status, entry_date, customer_id, device_type) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            ("CRM-OPEN-0001-T", "Ahmet Y\u0131lmaz", "Apple", "MacBook Pro", "Testte", "2026-10-01", 1, "Laptop"),
            ("CRM-OPEN-0001-R", "Ahmet Y\u0131lmaz", "Apple", "MacBook Pro", "Tamirde", "2026-10-01", 1, "Laptop"),
            ("CRM-HISTORY-0002-1", "Ay\u015fe Demir", "Lenovo", "ThinkPad E14", "Teslim Edildi", "2026-09-20", 2, "Laptop"),
            ("CRM-HISTORY-0002-2", "Ay\u015fe Demir", "Lenovo", "ThinkPad E14", "Teslim Edildi", "2026-09-21", 2, "Laptop"),
            ("CRM-HISTORY-0002-3", "Ay\u015fe Demir", "Lenovo", "ThinkPad E14", "Teslim Edildi", "2026-09-22", 2, "Laptop"),
            ("CRM-HISTORY-0015", "Burak \u015eahin", "Apple", "MacBook Pro", "Teslim Edildi - Atolye Montaj", "2026-10-02", 15, "Laptop"),
            ("CRM-HISTORY-0007", "Demo Musteri 06", "Samsung", "Galaxy A55", "Teslim Edildi - Atolye Montaj", "2026-10-03", 7, "Telefon"),
            ("CRM-DONE-MONTAGE", "Reference Customer", "Dell", "Latitude 5540", "Teslim Edildi - Atolye Montaj", "2026-10-04", 8, "Laptop"),
            ("CRM-OPEN-0058-1", "TeknoEv Otomasyon A.\u015e.", "Bosch", "Smart Hub", "Yillik Bakimda", "2026-10-05", 58, "Akilli Ev"),
            ("CRM-OPEN-0058-2", "TeknoEv Otomasyon A.\u015e.", "Bosch", "Smart Hub", "Yillik Bakimda", "2026-10-05", 58, "Akilli Ev"),
            ("CRM-READY-0032", "Ceyda Kaya Teknoloji", "Hikvision", "NVR System", "Teslimata Haz\u0131r", "2026-10-06", 32, "G\u00fcvenlik Sistemi"),
        ],
    )
    db.create_offer_tables()
    db.cursor.execute("DELETE FROM offers WHERE customer_id=44 AND offer_no='CRM-REF-044'")
    db.cursor.execute(
        "INSERT INTO offers (offer_no, customer_id, customer_name, status) VALUES (?, ?, ?, ?)",
        ("CRM-REF-044", 44, "Mert \u00d6zt\u00fcrk", "sent"),
    )
    db.conn.commit()


def seed_invoice_reference(page):
    customer_id = -999
    customer_name = "Hilton Bosphorus Otel & Kongre Hizmetleri"
    page.customers_data[customer_id] = {
        "name": customer_name,
        "tax": "1234567890",
        "addr": "Harbiye Mah. Asker Oca\u011f\u0131 Cad. No:1, 34367 \u015ei\u015fli / \u0130stanbul - T\u00dcRK\u0130YE",
    }
    customer_index = page.cmb_customer.findData(customer_id)
    if customer_index < 0:
        page.cmb_customer.addItem(customer_name, customer_id)
        customer_index = page.cmb_customer.findData(customer_id)
    page.cmb_customer.setCurrentIndex(customer_index)
    page.tax_office.setText("Beyo\u011flu Vergi Dairesi")
    page.invoice_date.setDate(QDate(2026, 10, 1))
    page.invoice_time.setTime(QTime(20, 47))
    page.currency_select.setCurrentIndex(page.currency_select.findData("USD"))
    page.exchange_rate.setText("49.0013")
    page.inp_delivery_reference.setText("IRS20260000009841")
    page.invoice_notes.setPlainText(
        "\u0130\u015fbu fatura bedeli 14 g\u00fcn i\u00e7erisinde Garanti BBVA Ticari hesab\u0131m\u0131za "
        "yat\u0131r\u0131lmal\u0131d\u0131r. Mal teslimi eksiksiz yap\u0131lm\u0131\u015ft\u0131r."
    )
    page.inp_order_reference.setText("PO-2026-HLT-992")
    page.due_date.setDate(QDate(2026, 10, 15))

    bank_label = "Garanti BBVA Ticari USD (TR44 0006 2000 ...)"
    bank_index = page.cmb_bank.findText(bank_label)
    if bank_index < 0:
        page.cmb_bank.addItem(bank_label, -999)
        bank_index = page.cmb_bank.findText(bank_label)
    page.cmb_bank.setCurrentIndex(bank_index)
    page.chk_auto_reconcile.setChecked(True)

    if page.items_table.rowCount() < 2:
        page.btn_add_item.click()
    rows = (
        {1: "Ak\u0131ll\u0131 Ev Otomasyon Kontrol Paneli Kurulumu\nSN: AYEC-8932-TR  |  \u0130\u015f\u00e7ilik & Konfig\u00fcrasyon Dahil", 2: "AYEC-SM-104",
         3: "1", 4: "Adet", 5: "1850.00", 6: "5.0", 7: "20"},
        {1: "4K IP G\u00fcvenlik Kameras\u0131 Bak\u0131m ve Network\nGTIP: 8525.80.19  |  Saha M\u00fchendislik Hizmeti", 2: "SRV-NET-09",
         3: "2", 4: "Hizmet", 5: "300.00", 6: "0.0", 7: "20"},
    )
    for row, values in enumerate(rows):
        for column, value in values.items():
            page.items_table.item(row, column).setText(value)
    page.calculate_totals()


def run(*, page_id=150, width=1600, height=1280, sample_reference=False, dialog=None, settings_index=14, settings_tab=1, theme_name='Koyu Mavi'):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    from src.utils.reference_typography import apply_reference_font
    apply_reference_font(app)
    directory = QTemporaryDir()
    db = Database(directory.filePath('shell.db'))
    seed_visual_fixture(db, currency_rates=True)
    if page_id == 61:
        db.update_personnel_location_schema()
        db.seed_demo_personnel_locations()
    if page_id == 21:
        seed_customer_management_reference(db)
        db.set_setting('company_name', 'Aslan Computer')
        # Keep the asynchronous customer worker on this seeded connection.
        db._db_name = ':memory:'
    if page_id == 42:
        seed_service_list_reference(db)
    if page_id == 147:
        seed_report_templates_reference(db)
        db.set_setting('company_name', 'ASLAN COMPUTER')
    if page_id == 140:
        seed_labor_services_reference(db)
    if page_id == 145:
        seed_brands_reference(db)
        db.set_setting('company_name', 'Aslan Computer')
        db.set_setting('site_title', 'Merkez \u015eube')
    if page_id == 146:
        seed_product_groups_reference(db)
    if page_id == 106:
        seed_check_notes_reference(db)
    if page_id == 130 and settings_index == 14:
        seed_quick_notes_reference(db)
    if page_id == 130 and settings_index == 16:
        from src.utils.secure_setting_store import SecureSettingStore
        SecureSettingStore.set(db, 'telegram_bot_token', '123456789:REFERENCE')
        db.set_setting('telegram_chat_ids', '["893412781", "561298834"]')
    if page_id == 105:
        seed_credit_reference(db)
    theme_name = ThemeManager.normalize_theme_name(theme_name)
    db.set_setting('color_theme_full', theme_name)
    db.set_setting('nav_mode', 'sol_menu')
    db.set_setting('desktop_auto_web_sync', '0')
    db.set_internal_setting('current_sector', 'teknik_servis')
    if page_id == 43 and sample_reference:
        seed_service_status_assistant_reference(db)
    settings = QSettings(directory.filePath('draft.ini'), QSettings.Format.IniFormat)
    original_sector_check = SalesHubPage._is_automotive
    SalesHubPage._is_automotive = lambda self: False if page_id == 300 else True
    initializer = NewTransactionV2Page.__init__

    def isolated_initializer(page, database, main_window=None, **kwargs):
        initializer(page, database, main_window, draft_settings=settings)
        page._restore_draft = lambda: None
        page.update_exchange_rates = lambda: page.on_currency_changed(page.cmb_currency.currentText())

    transaction_initializer = NewTransactionV2Page.__init__

    def capture_initializer(page, database, main_window=None, **kwargs):
        transaction_initializer(page, database, main_window, **kwargs)
        page._restore_draft = lambda: None
        page.update_exchange_rates = lambda: page.on_currency_changed(page.cmb_currency.currentText())

    window = None
    reference_dialog = None
    try:
        with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network disabled')):
            if page_id == 21 and os.environ.get('AYEC_CAPTURE_CUSTOMER_STATE') == '1':
                from src.ui.pages.customers_page import CustomersPage
                on_customer_data_loaded = CustomersPage.on_data_loaded

                def capture_customer_data_loaded(self, customers, total):
                    self._reference_raw_customer_rows = [dict(row) for row in list(customers or [])]
                    return on_customer_data_loaded(self, customers, total)

                CustomersPage.on_data_loaded = capture_customer_data_loaded
            window = ReferenceCaptureWindow(db, {'username': 'fixture', 'name': 'Aslan', 'role': 'Admin'})
            with patch.object(NewTransactionV2Page, '__init__', capture_initializer):
                window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                window.apply_nav_mode()
                if page_id == 130:
                    window.app_header.btn_shortcuts.show()
                    window.app_header.btn_interface_edit.show()
                else:
                    window.app_header.btn_shortcuts.hide()
                    window.app_header.btn_interface_edit.hide()
                window._is_page_allowed_for_active_sector = lambda index: True
                if page_id == 60:
                    window._active_sector_id = lambda: 'otomotiv'
                routed_page = window.get_page(page_id)
                if routed_page is not None:
                    window._switch_content_with_fade(routed_page)
                window.on_menu_click(page_id)
                routed_page = window.pages.get(page_id)
                if routed_page is None:
                    raise AssertionError('The actual page route did not load')
                if page_id == 66:
                    routed_page.tabs.setCurrentIndex(0)
                if page_id == 130:
                    settings_row = routed_page.sidebar.items_map.index(settings_index)
                    routed_page.sidebar.list_widget.setCurrentRow(settings_row)
                    if settings_index == 6:
                        settings_widget = routed_page.content_area.currentWidget()
                        settings_widget.tabs.setCurrentIndex(settings_tab)
                    elif settings_index == 21:
                        settings_widget = routed_page.content_area.currentWidget()
                        settings_widget.tabs.setCurrentIndex(settings_tab)
                if page_id == 105:
                    routed_page.tabs.setCurrentIndex(settings_tab)
                    if settings_tab == 1:
                        routed_page.loans_tab.load_loans()
                        first_loan = routed_page.loans_tab.tree.topLevelItem(0)
                        if first_loan is not None:
                            first_loan.setExpanded(True)
                if page_id == 146:
                    db.cursor.execute("DELETE FROM product_groups WHERE name='Laptop & PC'")
                    db.conn.commit()
                    routed_page.load_data()
                if page_id == 145:
                    seed_brands_reference(db)
                    routed_page.load_data()
                if page_id == 106:
                    original_check_loader = db.get_checks_notes
                    db.get_checks_notes = lambda status_filter=None: sorted(
                        original_check_loader(status_filter=status_filter), key=lambda row: row['id']
                    )
                    routed_page.load_data()
                if page_id == 30:
                    if sample_reference:
                        db.cursor.execute("DELETE FROM appointments")
                        db.cursor.execute(
                            "INSERT INTO appointments (customer_name, phone, date, time, description, status, personnel_name, type, urgency, color, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            ("QA Customer", "5551234567", "2026-10-13", "14:30", "QA Calendar Slot", "Planlandi", "QA Tech", "Saha Servis", "Normal", "#2563EB", "2026-10-13 09:00:00"),
                        )
                    else:
                        db.cursor.execute("UPDATE appointments SET date = date(date, '+7 days')")
                    db.conn.commit()
                    routed_page.refresh_calendar()
                    if os.environ.get('AYEC_CAPTURE_APPOINTMENT_GEOMETRY') == '1':
                        def widget_rect(widget):
                            point = widget.mapToGlobal(QPoint(0, 0))
                            origin = window.mapToGlobal(QPoint(0, 0))
                            rect = widget.rect()
                            return (point.x() - origin.x(), point.y() - origin.y(), rect.width(), rect.height())
                        print('APPOINTMENT_PRE_SHOW_GEOMETRY', {
                            'window': widget_rect(window),
                            'header': widget_rect(window.app_header),
                            'sidebar': widget_rect(window.app_sidebar),
                            'top_nav': widget_rect(window.app_top_nav),
                            'page': widget_rect(routed_page),
                            'page_toolbar': widget_rect(routed_page.layout().itemAt(0).widget()),
                            'calendar': widget_rect(routed_page.table),
                            'side_panel': widget_rect(routed_page.side_panel),
                        })
                if page_id == 147 and routed_page.table.rowCount():
                    routed_page._usage_metrics = {
                        "date": datetime.now().date().isoformat(),
                        "count": 48,
                        "average_seconds": 1.2,
                    }
                    routed_page._refresh_usage_stats()
                    routed_page.table.selectRow(0)
                    routed_page.set_preview_context(
                        customer="Burak Y\u0131lmaz", device="ASUS ROG Strix G15",
                        serial="SRV-2026-89410", accessory="Orijinal G\u00fc\u00e7 Adapt\u00f6r\u00fc & G\u00fc\u00e7 Kablosu",
                        date="01.10.2026",
                    )
                if page_id == 150 and sample_reference:
                    page = routed_page
                    transaction = page.sales_page
                    transaction._deferred_load_customers = lambda: None
                    transaction._deferred_load_services = lambda: None
                    transaction._deferred_load_exchange_rates = lambda: None
                    transaction._restore_draft = lambda: None
                    transaction.load_services = lambda: None
                if page_id == 101 and sample_reference:
                    examples = (
                        ("D\u00fckkan Kiras\u0131", "Eren Depo & Ana At\u00f6lye Merkez Binas\u0131", 45000, "red", "FTR-9081"),
                        ("Yedek Par\u00e7a", "\u00d6zlem Yedek Par\u00e7a \u0130thalat Ltd.", 45000, "red", "IRS-883120"),
                        ("Servis Tahsilat\u0131", "Aksoy Medya A.\u015e. (Toplu Bak\u0131m)", 84000, "green", "SRV-2026-904"),
                        ("Elektrik", "EnerjiSa Sanayi Tarifesi", 18000, "red", "FAT-449102"),
                        ("Saha Yak\u0131t", "Selim \u00c7elik Saha Operasyonu", 9240, "red", "FIS-9812"),
                        ("Personel", "Eyl\u00fcl Ay\u0131 Saha Prim Da\u011f\u0131t\u0131m\u0131", 8730, "red", "PRM-09"),
                    )
                    date = QDate.currentDate().toString("yyyy-MM-dd")
                    routed_page._rows = [
                        {
                            "date": date, "category": category, "description": description,
                            "amount_try": amount, "color_code": color,
                            "type_label": "Gider" if color == "red" else "Gelir",
                            "ref_no": reference,
                            "payment_method": "Banka" if color == "red" else "Sanal POS",
                        }
                        for category, description, amount, color, reference in examples
                    ]
                    for key, amount in (
                        ("gross_revenue", 439307.53), ("expenses", 118650),
                        ("pocket_net", 320657.53), ("pending", 34800),
                    ):
                        routed_page.metric_values[key].setText(routed_page._currency(amount))
                    routed_page.expense_ratio.setValue(27)
                    routed_page._apply_filters()
                ThemeManager.refresh_widget_tree(window)
                if page_id == 42:
                    window.setMinimumSize(0, 0)
                window.resize(width, height)
                if page_id == 150:
                    header_layout = window.app_header.layout()
                    header_widgets = (
                        window.app_header.lbl_logo,
                        window.app_header.lbl_brand_pro,
                        window.app_header.brand_separator,
                        window.app_header.lbl_app_name,
                        window.app_header.btn_back,
                        window.app_header.breadcrumb_separator,
                        window.app_header.breadcrumb,
                        window.app_header.btn_settings,
                        window.app_header.btn_shortcuts,
                        window.app_header.btn_interface_edit,
                        window.app_header.btn_update,
                        window.app_header.notification_bell,
                        window.app_header.breadcrumb.assistant_btn,
                        window.app_header.btn_web_sync,
                        window.app_header.btn_theme_toggle,
                        window.app_header.cmb_theme,
                        window.app_header.btn_minimize,
                        window.app_header.btn_maximize,
                        window.app_header.btn_close,
                    )
                    while header_layout.count():
                        item = header_layout.takeAt(0)
                        widget = item.widget()
                        if widget is not None:
                            widget.setParent(None)
                    window.app_sidebar.setFixedWidth(300)
                    window.app_header.setFixedHeight(54)
                    window.resize(width, height)
                    window.app_sidebar.side_menu.set_pinned(True, persist=False, animate=False)
                    window.app_sidebar.side_menu.logout_btn.hide()
                    window.app_top_nav.hide()
                    window.app_sidebar.side_menu.footer_mode.hide()
                    window.app_sidebar.side_menu.version_label.hide()
                    window.app_sidebar.side_menu.branding_title.setText('Aslan Computer')
                    window.app_sidebar.side_menu.branding_subtitle.setText('v2.0.4 Premium ERP')
                    window.app_sidebar.side_menu.branding_logo.setFixedSize(52, 52)
                    window.app_sidebar.side_menu.branding_logo.setPixmap(
                        window.app_header.lbl_logo.pixmap()
                    )
                    window.app_sidebar.side_menu.brand_card.setStyleSheet(
                        'QFrame#SideMenuBrandCard { background: #0f1629; border: 1px solid #1e2d4d; border-radius: 16px; }'
                    )
                    window.app_sidebar.side_menu.header.setFixedHeight(126)
                    window.app_sidebar.side_menu.brand_card.setFixedHeight(80)
                    window.app_sidebar.side_menu.branding_logo.setFixedSize(52, 52)
                    window.app_sidebar.side_menu.branding_logo.setPixmap(
                        window.app_header.lbl_logo.pixmap()
                    )
                    window.app_header.layout().setContentsMargins(12, 0, 10, 0)
                    window.app_header.layout().setSpacing(4)
                    window.app_header.lbl_logo.setFixedSize(32, 32)
                    window.app_header.layout().addWidget(window.app_header.lbl_logo)
                    window.app_header.layout().addWidget(window.app_header.lbl_app_name)
                    window.app_header.layout().addWidget(window.app_header.lbl_brand_pro)
                    window.app_header.layout().addWidget(window.app_header.brand_separator)
                    window.app_header.layout().addWidget(window.app_header.btn_back)
                    window.app_header.layout().addWidget(window.app_header.breadcrumb_separator)
                    window.app_header.layout().addWidget(window.app_header.breadcrumb)
                    window.app_header.breadcrumb.layout.removeWidget(
                        window.app_header.breadcrumb.assistant_btn
                    )
                    window.app_header.breadcrumb.layout.removeWidget(
                        window.app_header.breadcrumb.mute_btn
                    )
                    window.app_header.breadcrumb.layout.removeWidget(
                        window.app_header.breadcrumb.user_lbl
                    )
                    window.app_header.breadcrumb.assistant_btn.setParent(window.app_header)
                    window.app_header.breadcrumb.mute_btn.setParent(window.app_header)
                    window.app_header.breadcrumb.user_lbl.setParent(window.app_header)
                    window.app_header.layout().addStretch(1)
                    window.app_header.layout().addWidget(window.app_header.breadcrumb.assistant_btn)
                    depot_chip = QWidget(window.app_header)
                    depot_chip.setObjectName('ReferenceDepotChip')
                    depot_chip.setFixedSize(92, 30)
                    depot_chip.setStyleSheet(
                        'QWidget#ReferenceDepotChip { background: #202b40; '
                        'border-radius: 6px; }'
                    )
                    depot_chip_layout = QHBoxLayout(depot_chip)
                    depot_chip_layout.setContentsMargins(8, 0, 8, 0)
                    depot_chip_layout.addWidget(QLabel('Eren Depo', depot_chip))
                    window.app_header.layout().addWidget(depot_chip)
                    window.app_header.layout().addWidget(window.app_header.notification_bell)
                    window.app_header.layout().addWidget(window.app_header.btn_shortcuts)
                    window.app_header.layout().addWidget(window.app_header.btn_web_sync)
                    window.app_header.layout().addWidget(window.app_header.breadcrumb.user_lbl)
                    window.app_header.layout().addWidget(window.app_header.btn_settings)
                    window.app_header.layout().addWidget(window.app_header.btn_theme_toggle)
                    window.app_header.layout().addWidget(window.app_header.cmb_theme)
                    for control in (
                        window.app_header.btn_minimize,
                        window.app_header.btn_maximize,
                        window.app_header.btn_close,
                    ):
                        window.app_header.layout().addWidget(control)
                    window.app_header.lbl_brand_pro.show()
                    window.app_header.brand_separator.show()
                    window.app_header.breadcrumb_separator.show()
                    window.app_header.breadcrumb.setMinimumWidth(0)
                    window.app_header.breadcrumb.setMaximumWidth(16777215)
                    window.app_header.lbl_app_name.setText('AYEC')
                    window.app_header.lbl_app_name.show()
                    window.app_header.btn_back.show()
                    window.app_header.btn_back.setEnabled(True)
                    window.app_header.breadcrumb.assistant_btn.setFixedWidth(126)
                    window.app_header.breadcrumb.assistant_btn.setText('CORE')
                    window.app_header.breadcrumb.assistant_btn.show()
                    window.app_header.breadcrumb.mute_btn.hide()
                    window.app_header.breadcrumb.user_lbl.setText('Eren Aslan')
                    window.app_header.breadcrumb.user_lbl.show()
                    window.app_header.breadcrumb.update_path([
                        ('Teklif & Satis Yonetimi', 150),
                        ('Teklif & Satis Olustur', 150),
                    ])
                    window.app_header.breadcrumb.setMinimumWidth(0)
                    window.app_header.breadcrumb.setMaximumWidth(16777215)
                    window.app_header.btn_web_sync.setFixedSize(34, 38)
                    window.app_header.btn_web_sync.show()
                    window.app_header.btn_settings.setFixedSize(28, 28)
                    window.app_header.btn_settings.show()
                    window.app_header.btn_shortcuts.setFixedSize(28, 28)
                    window.app_header.btn_shortcuts.setText('\u2637')
                    window.app_header.btn_shortcuts.show()
                    window.app_header.notification_bell.setFixedSize(28, 28)
                    window.app_header.layout().addWidget(window.app_header.notification_bell)
                    window.app_header.btn_update.hide()
                    window.app_header.btn_interface_edit.hide()
                    window.app_header.btn_theme_toggle.setFixedSize(28, 28)
                    window.app_header.cmb_theme.setMinimumWidth(112)
                    window.app_header.cmb_theme.setMaximumWidth(112)
                    window.app_header.cmb_theme.setFixedHeight(38)
                    window.app_header.cmb_theme.show()
                    for control in (
                        window.app_header.btn_minimize,
                        window.app_header.btn_maximize,
                        window.app_header.btn_close,
                    ):
                        control.setFixedSize(12, 12)
                        control.show()
                    for action in window.app_sidebar.side_menu.findChildren(QPushButton):
                        if action.text().strip() == 'Teklif Oluştur':
                            action.setFixedWidth(260)
                    window.app_sidebar.side_menu.on_page_changed_internal(150)
                    for group in window.app_sidebar.side_menu.accordion_groups:
                        if group._title_lbl.text() == 'Teklif Yönetimi':
                            group._active_stays_expanded = True
                            group.is_expanded = True
                            group.sub_container.setMaximumHeight(16777215)
                            group.sub_container.show()
                            group.arrow_label.setText('v')
                window.show()
                QTest.qWait(750 if page_id == 130 else 300)
                app.processEvents()
                if page_id == 130 and settings_index == 20:
                    routed_page.change_page(settings_index)
                    app.processEvents()
                if page_id in (42, 130):
                    window.layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
                    window.centralWidget().layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
                    window.shell_layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
                    window.setMinimumSize(0, 0)
                    window.setMaximumSize(width, height)
                    window.resize(width, height)
                    app.processEvents()
                if sample_reference and page_id == 115:
                    seed_invoice_reference(routed_page)
                if sample_reference and page_id == 150:
                    transaction = routed_page.sales_page
                    transaction._catalog_category = 'all'
                    transaction._catalog_query = ''
                    transaction._catalog_stock_only = False
                    transaction._part_matches_domain = lambda _info, _domain: True
                    transaction.catalog_search.blockSignals(True)
                    transaction.catalog_search.clear()
                    transaction.catalog_search.blockSignals(False)
                    transaction.update_exchange_rates = lambda: transaction.on_currency_changed(
                        transaction.cmb_currency.currentText()
                    )
                    db.cursor.execute(
                        'UPDATE exchange_rates SET buying_rate=?, selling_rate=? '
                        'WHERE currency=?', (49.0184, 49.0184, 'USD'),
                    )
                    db.cursor.execute(
                        'UPDATE exchange_rates SET buying_rate=?, selling_rate=? '
                        'WHERE currency=?', (53.4210, 53.4210, 'EUR'),
                    )
                    db.cursor.execute(
                        'UPDATE customers SET name=?, company_name=?, phone=?, '
                        'tax_number=?, tax_office=?, limit_amount=? WHERE id=( '
                        'SELECT id FROM customers ORDER BY id LIMIT 1)',
                        ('Aslan Holding A.\u015e.', 'Aslan Holding A.\u015e.',
                         '+90 532 555 12 34', '1234567890', 'Kad\u0131k\u00f6y', 15000),
                    )
                    db.conn.commit()
                    from src.utils.exchange_rate_manager import ExchangeRateManager
                    ExchangeRateManager._rates_cache.pop('USD', None)
                    ExchangeRateManager._rates_cache.pop('EUR', None)
                    transaction.load_customers()
                    customer_index = transaction.cmb_customer.findText('Aslan Holding A.\u015e.')
                    if customer_index < 0:
                        raise AssertionError('The sample customer was not loaded')
                    transaction.cmb_customer.setCurrentIndex(customer_index)
                    transaction._refresh_customer_preview()
                    sample_customer_index = transaction.cmb_customer.findText('Aslan Holding A.\u015e.')
                    transaction.cmb_customer.setCurrentIndex(sample_customer_index)
                    transaction._select_reference_currency('TRY')
                    transaction._select_reference_currency('USD')
                    transaction.date_edit.setDate(QDate(2026, 10, 1))
                    transaction.current_exchange_rate = 49.0184
                    for index in range(transaction.cmb_currency.count()):
                        if transaction._parse_currency_code(transaction.cmb_currency.itemText(index)) == 'USD':
                            transaction.cmb_currency.setCurrentIndex(index)
                            break
                    transaction.load_services = lambda: None
                    names = (
                        ('DH-IPC-HFW2431S', 'Dahua 4MP Full-Color Gece G\u00f6r\u00fc\u015fl\u00fc IP Dome Kamera', 24, 45, 'Raf: B-12 | PoE Destekli | Ak\u0131ll\u0131 Analiz'),
                        ('NVR-4108HS-4KS2', 'Dahua 8 Kanal 4K Ultra HD H.265+ NVR Kay\u0131t Cihaz\u0131', 9, 92, 'Raf: A-04 | 1 SATA Portu | 10TB Destek'),
                        ('ST4000VX016', 'Seagate SkyHawk 4TB 256MB 5400RPM 7/24 G\u00fcvenlik Diski', 38, 118, 'Raf: D-08 | 3 Y\u0131l Distrib\u00fct\u00f6r Garantili'),
                        ('SW-POE-8G2S', 'Hikvision 8 Port Gigabit PoE+ 2 SFP Uplink Switch', 15, 68, 'Raf: C-02 | 120W G\u00fc\u00e7 B\u00fct\u00e7esi | 250m Mod'),
                        ('SRV-MONTAJ-01', 'G\u00fcvenlik Kameras\u0131 Montaj\u0131 & U\u00e7 Ba\u011flant\u0131 Hizmeti', 0, 25, 'Saha \u0130\u015f\u00e7ili\u011fi | Kamera Ba\u015f\u0131na \u0130\u015f\u00e7ilik Bedeli'),
                        ('CAT6-UTP-305M', 'Nexans Cat6 23AWG %100 Bak\u0131r UTP A\u011f Kablosu (305m)', 11, 125, 'Raf: K-01 | LSZH D\u0131\u015f K\u0131l\u0131f | Yang\u0131na Dayan\u0131kl\u0131'),
                    )
                    rate = transaction.current_exchange_rate
                    transaction._all_parts_catalog = [
                        {
                            'id': index + 1, 'code': code, 'name': name,
                            'type': 'part', 'stock': stock, 'price': dollars * rate,
                            'original_price': dollars, 'currency': 'USD',
                            'category': 'Guvenlik Sistemleri', 'description': description,
                        }
                        for index, (code, name, stock, dollars, description) in enumerate(names)
                    ]
                    transaction.cmb_customer.currentTextChanged.disconnect(
                        transaction._refresh_customer_preview
                    )
                    transaction.cmb_currency.currentTextChanged.disconnect(
                        transaction._handle_currency_change
                    )
                    transaction.catalog_search.textChanged.disconnect(
                        transaction._on_catalog_search_changed
                    )
                    transaction.cmb_product_domain.currentIndexChanged.disconnect(
                        transaction._on_product_domain_changed
                    )
                    transaction.catalog_tabs.currentChanged.disconnect(
                        transaction._set_catalog_mode
                    )
                    transaction._refresh_catalog_cards(transaction._all_parts_catalog)
                    transaction.cmb_product_domain.setCurrentIndex(0)
                    transaction.catalog_search.setText('')
                    transaction.catalog_search.blockSignals(False)
                    transaction.cmb_product_domain.setCurrentIndex(0)
                    transaction.catalog_tabs.setCurrentIndex(0)
                    transaction.catalog_tabs.hide()
                    transaction.cart_items = [
                        {
                            'id': f'reference-{index}', 'item_id': index + 1,
                            'type': 'part', 'service': name, 'description': code,
                            'price': dollars * rate, 'qty': count,
                            'date': '2026-10-01',
                        }
                        for index, (code, name, _stock, dollars, _description), count in zip(
                            range(4), (names[0], names[1], names[2], names[4]), (4, 1, 1, 4)
                        )
                    ]
                    transaction.refresh_cart_ui()
                    transaction.update_totals()
                    transaction._apply_discount_percent(5)
                    transaction._refresh_customer_preview = lambda: None
                    transaction.customer_title.setText('Aslan Holding A.\u015e.')
                    transaction.customer_title.show()
                    customer_preview_lines = (
                        'Yetkili: Mehmet Aslan',
                        'Cari bakiye (USD): 0.00 $',
                        'Tel: +90 532 555 12 34',
                        'Kredi Limiti: $15,000',
                    )
                    transaction.customer_preview.setText(
                        ' | '.join(customer_preview_lines)
                        if transaction.height() < 980
                        else '\n'.join(customer_preview_lines)
                    )
                    transaction.customer_preview.show()
                    transaction.customer_avatar.setText('A')
                    avatar_size = 40 if transaction.height() < 980 else 58
                    transaction.customer_avatar.setFixedSize(avatar_size, avatar_size)
                    transaction.reference_cart_rate.setText('1 USD = 49.0184 \u20ba')
                    transaction.lbl_subtotal.setStyleSheet(
                        'QLabel#TransactionCartSubtotal { color: #94a3b8; font-size: 12px; }'
                    )
                    transaction.lbl_subtotal.setText(
                        'Ara Toplam (4 Kalem):  $ 490.00  (24,019.02 TRY)'
                    )
                    transaction.findChild(QFrame, 'TransactionGrandTotal').setFixedHeight(
                        54 if transaction.height() < 980 else 86
                    )
                    transaction.reference_cart_rate.setStyleSheet(
                        'QLabel#TransactionCartExchangeRate { color: #94a3b8; font-size: 10px; }'
                    )
                    transaction.btn_offer.setFixedHeight(
                        34 if transaction.height() < 980 else 50
                    )
                    transaction.lbl_total.primary_token = 'finance_primary'
                    transaction.lbl_total.setText('558.60 $\n27,381.68 ₺')
                    page.tabs.setTabBarAutoHide(True)
                    page.tabs.tabBar().hide()
                    if hasattr(window, 'assistant_fab'):
                        window.assistant_fab.hide()
                    card_count = transaction.catalog_cards_layout.count()
                    if card_count != 6:
                        raise AssertionError(f'Reference catalog card count was {card_count}, expected 6')
                    if transaction.catalog_cards_scroll.isHidden():
                        raise AssertionError('Reference catalog grid is hidden')
                QTest.qWait(8000 if page_id == 61 else 300)
                if page_id in {101, 105, 106, 115}:
                    window.app_header.raise_()
                    app.processEvents()
                if window.content_area.currentWidget() is not routed_page:
                    raise AssertionError('The original navigation did not select the page route')
                output = ROOT / 'artifacts' / 'desktop_shell_reference' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                output.mkdir(parents=True, exist_ok=False)
                if dialog in {'new_customer', 'customer_notes', 'customer_360', 'new_service', 'transaction_details', 'payment_collection', 'technician_panel', 'technician_station', 'bulk_stock_select'}:
                    required_page = 150 if dialog == 'bulk_stock_select' else 21 if dialog in {'new_customer', 'customer_notes', 'customer_360', 'payment_collection'} else 42 if dialog in {'new_service', 'technician_panel', 'technician_station'} else 101
                    if page_id != required_page:
                        raise ValueError('The requested dialog capture uses page {}'.format(required_page))
                    if dialog == 'bulk_stock_select':
                        from src.ui.dialogs.bulk_stock_select_dialog import BulkStockSelectDialog
                        parts_data = {}
                        sample_rows = (
                            (1, 287.0, 'AES-104-CTRL', 51),
                            (2, 324.0, 'AES-105-RLY', 52),
                            (3, 361.0, 'AES-108-RAD', 53),
                            (4, 398.0, 'AES-112-DOR', 54),
                            (5, 435.0, 'AES-115-WTR', 55),
                            (6, 472.0, 'AES-120-GAS', 54),
                        )
                        for index, price, code, stock in sample_rows:
                            name = 'Ak\u0131ll\u0131 Ev Sistemleri \u00dcr\u00fcn {:02d}'.format(index)
                            parts_data[name] = {
                                'id': 'reference-smart-home-{:02d}'.format(index),
                                'name': name,
                                'category': 'Ak\u0131ll\u0131 Ev Sistemleri',
                                'stock': stock,
                                'price': price,
                                'original_price': price,
                                'currency': 'TRY',
                                'code': code,
                                'barcode': '8690123847{:02d}'.format(index),
                            }
                        for category, total, prefix, price_start in (
                            ('Ak\u0131ll\u0131 Ev Sistemleri', 40, 'AES-REF', 600),
                            ('Bilgisayar Bile\u015fenleri', 48, 'PC-REF', 1200),
                            ('G\u00fcvenlik Sistemleri', 36, 'SEC-REF', 2200),
                        ):
                            first_index = 7 if prefix == 'AES-REF' else 1
                            for index in range(first_index, total + 1):
                                name = '{} Reference {:02d}'.format(prefix, index)
                                price = float(price_start + index)
                                parts_data[name] = {
                                    'id': '{}-{:03d}'.format(prefix, index),
                                    'name': name,
                                    'category': category,
                                    'stock': 10 + index,
                                    'price': price,
                                    'original_price': price,
                                    'currency': 'TRY',
                                    'code': '{}-{:03d}'.format(prefix, index),
                                    'barcode': '8690999{:05d}'.format(index),
                                }
                        reference_dialog = BulkStockSelectDialog(
                            routed_page, db,
                            getattr(routed_page, 'services_data', {}),
                            parts_data,
                        )
                        reference_dialog._refresh_system_styles()
                        reference_dialog._filter_rows()
                        visible_index = 0
                        for row_index in range(reference_dialog.tree.topLevelItemCount()):
                            row = reference_dialog.tree.topLevelItem(row_index)
                            if not row.isHidden() and visible_index < 3:
                                reference_dialog._set_row_selected(row, True)
                                visible_index += 1
                        previous_block = reference_dialog.select_visible.blockSignals(True)
                        reference_dialog.select_visible.setCheckState(Qt.CheckState.Unchecked)
                        reference_dialog.select_visible.blockSignals(previous_block)
                        dialog_width, dialog_height = 864, 840
                        dialog_x, dialog_y = (width - dialog_width) // 2, 202
                    elif dialog == 'technician_panel':
                        from src.ui.dialogs.technician_panel import TechnicalServiceTechnicianPanel
                        reference_dialog = TechnicalServiceTechnicianPanel(db, 'DEMO-SRV-0008')
                        dialog_width, dialog_height = 1280, 837
                        dialog_x, dialog_y = 0, max(0, (height - dialog_height) // 2)
                    elif dialog == 'technician_station':
                        from src.ui.dialogs.technician_panel import TechnicalServiceTechnicianPanel
                        from src.ui.widgets.modern_dialog import ModernDialog
                        panel = TechnicalServiceTechnicianPanel(db, 'DEMO-SRV-0008')
                        reference_dialog = ModernDialog('Istasyon Bilgileri', panel, width=700, height=210)
                        reference_dialog.content_layout.addWidget(panel.station_bar)
                        panel.station_bar.show()
                        reference_dialog.add_button('Kapat', 'secondary', reference_dialog.accept)
                        dialog_width, dialog_height = 700, 210
                        dialog_x, dialog_y = (width - dialog_width) // 2, (height - dialog_height) // 2
                    elif dialog == 'transaction_details':
                        from src.ui.pages.accounting_dialogs.transaction_details_dialog import TransactionDetailsDialog
                        reference_dialog = TransactionDetailsDialog(db, {
                            'id': 44, 'date': '2026-09-28', 'timestamp': '28.09.2026 14:32:19',
                            'type_label': 'Tahsilat', 'status_label': 'Tamamlandı', 'source': 'currency',
                            'currency': 'EUR', 'amount': 7375.00, 'amount_try': 411016.12,
                            'rate': 55.7310, 'customer_id': 1, 'customer_name': 'Gökhan Polat',
                            'description': 'Ref: OFFER-6-20260928232749 | Cari borç kapatma tahsilatı | '
                            'Borç Kaydı: Ref: TEKLIF-0006 | Accepted offer | '
                            'Banka Havale/EFT ile hesaba aktarıldı.',
                            'tracking_no': 'OFFER-6-20260928232749', 'ref_no': 'OFFER-6-20260928232749',
                            'service_work_lines': [
                                'Saha keşif ve kablolama kontrolü tamamlandı',
                                'Modül firmware v4.8 sürümüne güncellendi ve test edildi',
                                'Kullanıcı erişim yetkileri teslim edildi',
                            ],
                            'selected_services': [
                                {'name': 'Teklif Ürünü: Akıllı Kontrol Ünitesi', 'sku': 'IOT-MOD-2026', 'quantity': 2, 'unit_price': 1250.00, 'total': 2500.00},
                                {'name': 'Akıllı Ev Sistemleri Ürün Paketi 05', 'sku': 'SMART-HM-05', 'quantity': 3, 'unit_price': 1400.00, 'total': 4200.00},
                                {'name': 'Yerinde Kurulum, Test ve Yazılım Güncelleme İşçiliği', 'sku': 'SERVIS-LBR-01', 'quantity': 1, 'unit_price': 675.00, 'total': 675.00},
                            ],
                        }, routed_page)
                        dialog_width, dialog_height, dialog_x, dialog_y = 1440, 1040, (width - 1440) // 2, 120
                    elif dialog == 'payment_collection':
                        from src.ui.dialogs.payment_dialog import ModernPaymentDialog
                        db.set_setting('currency', 'EUR')
                        db.conn.execute("DELETE FROM payment_debt_links")
                        db.conn.execute("DELETE FROM currency_transactions WHERE customer_id=1")
                        db.conn.execute("DELETE FROM customer_currency_balances WHERE customer_id=1")
                        db.conn.execute(
                            "INSERT INTO customer_currency_balances (customer_id,currency,balance,last_updated) "
                            "VALUES (1,'USD',0,'2026-10-01'),(1,'EUR',46,'2026-10-01'),(1,'TRY',0,'2026-10-01')"
                        )
                        db.conn.execute(
                            "UPDATE exchange_rates SET buying_rate=49.0184,selling_rate=49.0184 "
                            "WHERE currency='USD'"
                        )
                        db.conn.execute(
                            "UPDATE exchange_rates SET buying_rate=55.42,selling_rate=55.42 "
                            "WHERE currency='EUR'"
                        )
                        db.conn.executemany(
                            "INSERT INTO currency_transactions "
                            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
                            "description,tracking_no,created_at,current_balance) "
                            "VALUES (1,'DEBIT',?, 'EUR',55.42,?,?,?,?,-?)",
                            [
                                (30, 1662.6, 'Servis Iscilik & Panel Onarimi\nDahua Guvenlik Kamerasi Montaji',
                                 'DEMO-SRV-0001', '2026-09-21 10:00:00', 30),
                                (16, 886.72, '12V 2A Guvenlik Adaptoru\nYedek Parca Satisi (Depo)',
                                 'STK-0922', '2026-09-27 10:00:00', 16),
                            ],
                        )
                        db.conn.commit()
                        reference_dialog = ModernPaymentDialog(
                            routed_page,
                            db,
                            {'id': 1, 'name': 'Burak \u015eahin', 'phone': '05550000015'},
                        )
                        dialog_width, dialog_height = 960, 900
                        dialog_x, dialog_y = (width - dialog_width) // 2, 124
                    elif dialog == 'new_customer':
                        from src.ui.dialogs.technical_service_customer_dialog import TechnicalServiceCustomerDialog
                        reference_dialog = TechnicalServiceCustomerDialog(
                            db, routed_page,
                            sector_manager=getattr(window, 'sector_manager', None),
                        )
                        dialog_width, dialog_height, dialog_x, dialog_y = 864, 820, (width - 864) // 2, 144
                    elif dialog == 'customer_notes':
                        from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
                        notes = [
                            ('Genel Not', 'IP Adres', 'Sunucu ve yerel a\u011f eri\u015fimi i\u00e7in belirlenen konfig\u00fcrasyon:<br>- Statik IP: 192.168.1.105<br>- Alt A\u011f Maskesi: 255.255.255.0<br>- A\u011f Ge\u00e7idi: 192.168.1.1<br>- Firewall 8080 ve 443 portlar\u0131 d\u0131\u015f eri\u015fime g\u00fcvenli IP listesiyle a\u00e7\u0131lm\u0131\u015ft\u0131r.', '2026-09-29 16:52:29'),
                            ('Telefon G\u00f6r\u00fc\u015fmesi', 'Telefon G\u00f6r\u00fc\u015fmesi', 'Cihaz teslimi ve kurulum randevusu teyit edildi. \u00c7ar\u015famba sabah\u0131 haz\u0131r olacak.', '2026-09-28 14:10:05'),
                            ('WhatsApp', 'Teklif \u0130letildi', 'Y\u0131ll\u0131k bak\u0131m ve lisanslama teklif PDF dosyas\u0131 WhatsApp i\u015fletme hatt\u0131ndan payla\u015f\u0131ld\u0131.', '2026-09-25 11:30:18'),
                        ]
                        db.conn.executemany(
                            'INSERT INTO customer_notes (customer_id, type, title, content, created_at) VALUES (?, ?, ?, ?, ?)',
                            [(1, note_type, title, content, created_at) for note_type, title, content, created_at in notes],
                        )
                        db.conn.commit()
                        reference_dialog = CustomerNotesDialog(db, 1, 'Ahmet Y\u0131lmaz', routed_page)
                        dialog_width, dialog_height, dialog_x, dialog_y = 864, 840, (width - 864) // 2, 23
                    elif dialog == 'customer_360':
                        from src.ui.dialogs.customer_360_dialog import Customer360Dialog
                        db.set_setting('currency', 'USD')
                        db.conn.execute("DELETE FROM currency_transactions WHERE customer_id=1")
                        db.conn.execute("DELETE FROM exchange_rates WHERE currency='USD'")
                        db.conn.execute(
                            "INSERT INTO exchange_rates (currency, buying_rate, selling_rate, effective_date, source, created_at) VALUES ('USD', 34.2, 34.2, DATE('now'), 'Figma reference', DATETIME('now'))"
                        )
                        db.conn.execute(
                            "UPDATE customer_currency_balances SET balance=0 WHERE customer_id=1 AND currency='TRY'"
                        )
                        db.conn.execute(
                            "INSERT OR REPLACE INTO customer_currency_balances (customer_id, currency, balance, last_updated) VALUES (1, 'USD', -165, '2026-09-27')"
                        )
                        db.conn.execute(
                            "INSERT INTO devices (tracking_no, customer_name, device_brand, device_model, status, entry_date, customer_id, device_type) VALUES ('DEMO-SRV-0001', 'Ahmet Y\u0131lmaz', 'Akilli Ev Sistemleri', 'Urun 01', 'Teslim Edildi', '2026-09-27', 1, 'Akilli Ev')"
                        )
                        db.conn.executemany(
                            "INSERT INTO currency_transactions (customer_id, transaction_type, amount, currency, exchange_rate, try_equivalent, description, tracking_no, created_at, current_balance) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            [
                                ('DEBIT', 7, 'USD', 34.2, 239.4, 'Akilli Ev Sistemleri Urun 02', 'DEMO-SRV-0001', '2026-09-27 16:00:00', 165),
                                ('CREDIT', 900, 'TRY', 1, 900, 'Cari borc kapatma tahsilati', 'DEMO-SRV-0001', '2026-09-27 14:00:00', 165),
                                ('DEBIT', 6, 'USD', 34.2, 205.2, 'Akilli Ev Sistemleri Urun 01', 'DEMO-SRV-0001', '2026-09-27 12:00:00', 165),
                                ('CREDIT', 900, 'TRY', 1, 900, 'Cari borc kapatma tahsilati', 'DEMO-SRV-0001', '2026-09-27 10:00:00', 165),
                                ('DEBIT', 7, 'USD', 34.2, 239.4, 'Akilli Ev Sistemleri Urun 02', 'DEMO-SRV-0001', '2026-09-27 08:00:00', 165),
                                ('DEBIT', 17, 'USD', 34.2, 581.4, 'Akilli Ev Sistemleri Urun 01', 'DEMO-SRV-0001', '2026-09-21 08:00:00', 165),
                            ],
                        )
                        db.conn.commit()
                        reference_dialog = Customer360Dialog(
                            db, 1, 'Ahmet Y\u0131lmaz', routed_page,
                            sector_manager=getattr(window, 'sector_manager', None),
                        )
                        dialog_width, dialog_height, dialog_x, dialog_y = 1220, 920, (width - 1220) // 2, 143
                    else:
                        from src.ui.dialogs.technical_service_new_service_dialog import TechnicalServiceNewServiceDialog
                        db.set_setting('currency', 'TRY')
                        reference_dialog = TechnicalServiceNewServiceDialog(
                            db, routed_page,
                            sector_manager=getattr(window, 'sector_manager', None),
                        )
                        dialog_width = min(1440, max(760, width - 32))
                        dialog_height = min(1184, max(600, height - 48))
                        dialog_x, dialog_y = (width - dialog_width) // 2, (height - dialog_height) // 2
                    reference_dialog.show()
                    reference_dialog.raise_()
                    # The offscreen Qt platform advertises an 800px screen even
                    # when the reference viewport is 1280px wide. Keep capture
                    # geometry representative of the desktop reference.
                    reference_dialog.setMaximumSize(max(1200, dialog_width), max(1000, dialog_height))
                    reference_dialog.resize(dialog_width, dialog_height)
                    QTest.qWait(1500)
                    reference_dialog.update()
                    reference_dialog.repaint()
                    app.processEvents()
                    path = output / '{}_dialog.png'.format(dialog)
                    canvas = QPixmap(width, height)
                    canvas.fill(QColor('#020617'))
                    painter = QPainter(canvas)
                    painter.fillRect(0, 0, width, height, QColor(2, 6, 23, 150))
                    screen = reference_dialog.screen() or app.primaryScreen()
                    dialog_image = screen.grabWindow(int(reference_dialog.winId()))
                    if dialog_image.isNull():
                        raise AssertionError('The dialog screenshot could not be captured')
                    painter.drawPixmap(dialog_x, dialog_y, dialog_image)
                    painter.end()
                    if not canvas.save(str(path)):
                        raise AssertionError('The dialog screenshot could not be saved')
                    return path
                theme_slug = theme_name.lower().replace(' ', '_')
                path = output / f'{theme_slug}_route_{page_id}_{window.width()}x{window.height()}.png'
                if page_id == 30 and os.environ.get('AYEC_CAPTURE_GEOMETRY'):
                    import json
                    header = window.app_header
                    controls = []
                    for child in header.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                        text_method = getattr(child, 'text', None)
                        controls.append({
                            'class': child.metaObject().className(),
                            'name': child.objectName(),
                            'text': text_method() if callable(text_method) else '',
                            'geometry': [child.x(), child.y(), child.width(), child.height()],
                            'visible': child.isVisible(),
                        })
                    visible_controls = []
                    for child in header.findChildren(QWidget):
                        if not child.isVisible():
                            continue
                        text_method = getattr(child, 'text', None)
                        origin = child.mapTo(header, QPoint(0, 0))
                        visible_controls.append({
                            'class': child.metaObject().className(),
                            'name': child.objectName(),
                            'text': text_method() if callable(text_method) else '',
                            'tooltip': child.toolTip(),
                            'geometry': [origin.x(), origin.y(), child.width(), child.height()],
                        })
                    print('ROUTE30_HEADER', json.dumps({
                        'geometry': [header.x(), header.y(), header.width(), header.height()],
                        'controls': controls,
                        'visible_controls': visible_controls,
                    }, ensure_ascii=True))
                    side_menu = window.app_sidebar.side_menu
                    footer = side_menu.footer
                    footer_children = []
                    for child in footer.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                        origin = child.mapTo(window, QPoint(0, 0))
                        footer_children.append({
                            'class': child.metaObject().className(),
                            'name': child.objectName(),
                            'text': getattr(child, 'text', lambda: '')(),
                            'geometry': [origin.x(), origin.y(), child.width(), child.height()],
                            'visible': child.isVisible(),
                        })
                    footer_origin = footer.mapTo(window, QPoint(0, 0))
                    logout_origin = side_menu.logout_btn.mapTo(window, QPoint(0, 0))
                    header_origin = side_menu.header.mapTo(window, QPoint(0, 0))
                    brand_origin = side_menu.brand_card.mapTo(window, QPoint(0, 0))
                    logo_origin = side_menu.branding_logo.mapTo(window, QPoint(0, 0))
                    sector_origin = side_menu.branding_sector_badge.mapTo(window, QPoint(0, 0))
                    pin_origin = side_menu.pin_button.mapTo(window, QPoint(0, 0))
                    def app_widget_rect(widget):
                        origin = widget.mapTo(window, QPoint(0, 0))
                        return [origin.x(), origin.y(), widget.width(), widget.height()]
                    appointment_layout = routed_page.layout()
                    page_items = []
                    for index in range(appointment_layout.count()):
                        item = appointment_layout.itemAt(index)
                        widget = item.widget()
                        if widget is not None:
                            page_items.append({
                                'class': widget.metaObject().className(),
                                'name': widget.objectName(),
                                'geometry': app_widget_rect(widget),
                            })
                        else:
                            rect = item.geometry()
                            page_origin = routed_page.mapTo(window, QPoint(0, 0))
                            page_items.append({
                                'class': 'layout',
                                'name': '',
                                'geometry': [page_origin.x() + rect.x(), page_origin.y() + rect.y(), rect.width(), rect.height()],
                            })
                    appointment_toolbar = appointment_layout.itemAt(0).widget()
                    appointment_kpis = []
                    for value in routed_page.appointment_kpi_values:
                        card = value.parentWidget()
                        appointment_kpis.append(app_widget_rect(card))
                    appointment_side_children = []
                    for child in routed_page.side_panel.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                        appointment_side_children.append({
                            'class': child.metaObject().className(),
                            'name': child.objectName(),
                            'text': getattr(child, 'text', lambda: '')(),
                            'geometry': app_widget_rect(child),
                            'visible': child.isVisible(),
                        })
                    appointment_technician_children = []
                    technician_frame = routed_page.side_panel.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)[-1]
                    for child in technician_frame.findChildren(QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly):
                        appointment_technician_children.append({
                            'class': child.metaObject().className(),
                            'name': child.objectName(),
                            'text': getattr(child, 'text', lambda: '')(),
                            'geometry': app_widget_rect(child),
                            'visible': child.isVisible(),
                        })
                    appointment_toolbar_widgets = []
                    for child in appointment_toolbar.findChildren(QWidget):
                        if child.isVisible():
                            appointment_toolbar_widgets.append({
                                'class': child.metaObject().className(),
                                'text': getattr(child, 'text', lambda: '')(),
                                'geometry': app_widget_rect(child),
                                'font_size': child.font().pointSizeF(),
                                'style': child.styleSheet(),
                            })
                    appointment_calendar_geometry = {
                        'table': app_widget_rect(routed_page.table),
                        'viewport': app_widget_rect(routed_page.table.viewport()),
                        'horizontal_header': app_widget_rect(routed_page.table.horizontalHeader()),
                        'vertical_header': app_widget_rect(routed_page.table.verticalHeader()),
                        'column_widths': [routed_page.table.columnWidth(index) for index in range(routed_page.table.columnCount())],
                        'column_positions': [routed_page.table.horizontalHeader().sectionViewportPosition(index) for index in range(routed_page.table.columnCount())],
                        'row_heights': [routed_page.table.rowHeight(index) for index in range(routed_page.table.rowCount())],
                        'row_positions': [routed_page.table.verticalHeader().sectionViewportPosition(index) for index in range(routed_page.table.rowCount())],
                    }
                    print('ROUTE30_SIDEBAR_FOOTER', json.dumps({
                        'sidebar': [window.app_sidebar.x(), window.app_sidebar.y(), window.app_sidebar.width(), window.app_sidebar.height()],
                        'side_menu': [side_menu.x(), side_menu.y(), side_menu.width(), side_menu.height()],
                        'header': [header_origin.x(), header_origin.y(), side_menu.header.width(), side_menu.header.height()],
                        'brand': [brand_origin.x(), brand_origin.y(), side_menu.brand_card.width(), side_menu.brand_card.height()],
                        'logo': [logo_origin.x(), logo_origin.y(), side_menu.branding_logo.width(), side_menu.branding_logo.height()],
                        'sector_badge': [sector_origin.x(), sector_origin.y(), side_menu.branding_sector_badge.width(), side_menu.branding_sector_badge.height()],
                        'pin': [pin_origin.x(), pin_origin.y(), side_menu.pin_button.width(), side_menu.pin_button.height()],
                        'footer': [footer_origin.x(), footer_origin.y(), footer.width(), footer.height()],
                        'logout': [logout_origin.x(), logout_origin.y(), side_menu.logout_btn.width(), side_menu.logout_btn.height()],
                        'children': footer_children,
                        'appointment_page': app_widget_rect(routed_page),
                        'appointment_items': page_items,
                        'appointment_kpis': appointment_kpis,
                        'appointment_side_children': appointment_side_children,
                        'appointment_technician_children': appointment_technician_children,
                        'appointment_toolbar': app_widget_rect(appointment_toolbar),
                        'appointment_toolbar_widgets': appointment_toolbar_widgets,
                        'appointment_calendar': app_widget_rect(routed_page.table),
                        'appointment_calendar_geometry': appointment_calendar_geometry,
                        'appointment_side_panel': app_widget_rect(routed_page.side_panel),
                    }, ensure_ascii=True))
                if page_id == 42 and os.environ.get('AYEC_CAPTURE_GEOMETRY'):
                    table = routed_page.table
                    print('ROUTE42_GEOMETRY', window.width(), table.width(),
                          table.viewport().width(),
                          [table.columnWidth(index) for index in range(table.columnCount())],
                          table.horizontalScrollBar().maximum())
                    print('ROUTE42_SIZE_HINTS', window.minimumWidth(),
                          window.minimumSizeHint().width(), routed_page.minimumWidth(),
                          routed_page.minimumSizeHint().width(),
                          table.minimumWidth(), table.minimumSizeHint().width(),
                          routed_page.sizePolicy().horizontalPolicy().name)
                    print('ROUTE42_LAYOUT_WIDTHS', window.sizeHint().width(),
                          window.centralWidget().width(), window.app_sidebar.width(),
                          window.right_container.width(), window.app_header.minimumSizeHint().width(),
                          window.right_container.minimumWidth(),
                          window.right_container.minimumSizeHint().width(),
                          window.right_container.layout().sizeConstraint().name,
                          [button.width() for button in routed_page.reference_quick_actions])
                    print('ROUTE42_WINDOW_STATE', window.isMaximized(), window.isFullScreen(),
                          window.maximumWidth(), window.maximumSize().width(),
                          window.screen().geometry().width())
                    print('ROUTE42_LAYOUT_CONSTRAINTS',
                          window.layout().sizeConstraint().name,
                          window.centralWidget().layout().sizeConstraint().name,
                          window.shell_layout.sizeConstraint().name)
                if page_id == 147 and os.environ.get('AYEC_CAPTURE_GEOMETRY'):
                    print('ROUTE147_FILTER_WIDTHS', window.width(),
                          routed_page.search.width(), routed_page.device_filter.width(),
                          routed_page.status_filter.width(), routed_page.status_filter.minimumWidth(),
                          routed_page.status_filter.maximumWidth(), routed_page.refresh_button.width())
                if page_id == 21:
                    from src.ui.pages._cpp_worker import CustomerWorker

                    captured_rows = {}
                    sample_worker = CustomerWorker(db, 100, 0, '', None)
                    sample_worker.data_loaded.connect(
                        lambda rows, total: captured_rows.update(rows=rows, total=total)
                    )
                    sample_worker.run()
                    rows_by_id = {int(row['id']): row for row in captured_rows.get('rows', [])}
                    reference_order = (1, 2, 58, 25, 44, 19, 32)
                    if 44 in rows_by_id and int(rows_by_id[44].get('pending_offer_count', 0) or 0) != 1:
                        raise AssertionError('Customer reference fixture is missing Mert\'s pending offer.')
                    if all(customer_id in rows_by_id for customer_id in reference_order):
                        reference_rows = []
                        for customer_id in reference_order:
                            row_data = dict(rows_by_id[customer_id])
                            if customer_id == 44:
                                row_data['overdue_days'] = 12
                            reference_rows.append(row_data)
                        routed_page.on_data_loaded(
                            reference_rows,
                            captured_rows.get('total', 28),
                        )
                        target_positions = {
                            customer_id: position
                            for position, customer_id in enumerate(reference_order)
                        }
                        for row_index in range(routed_page.table.rowCount()):
                            customer_item = routed_page.table.item(row_index, 1)
                            customer_data = customer_item.data(Qt.ItemDataRole.UserRole)
                            name_item = routed_page.table.item(row_index, 2)
                            if customer_data and name_item is not None:
                                name_item.setData(
                                    Qt.ItemDataRole.UserRole + 1,
                                    target_positions.get(int(customer_data['id']), row_index),
                                )
                        routed_page.table.setSortingEnabled(True)
                        routed_page.table.sortItems(2, Qt.SortOrder.AscendingOrder)
                        routed_page.table.setSortingEnabled(False)
                        if os.environ.get('AYEC_CAPTURE_CUSTOMER_HOVER') == '1' and routed_page.table.rowCount():
                            hover_row = int(os.environ.get('AYEC_CAPTURE_CUSTOMER_HOVER_ROW', '0'))
                            if hover_row < 0 or hover_row >= routed_page.table.rowCount():
                                raise AssertionError('Requested customer hover row is outside the rendered table.')
                            hover_item = routed_page.table.item(hover_row, 2)
                            hover_point = routed_page.table.visualItemRect(hover_item).center()
                            QTest.mouseMove(routed_page.table.viewport(), QPoint(hover_point.x(), hover_point.y()))
                            routed_page._on_table_cell_entered(hover_row, 2)
                            app.processEvents()
                if page_id == 130 and settings_index == 14 and os.environ.get('AYEC_CAPTURE_QUICK_NOTES_EXPANDED') == '1':
                    window.app_sidebar.side_menu.set_collapsed(False, animate=False)
                    app.processEvents()
                if page_id == 300 and os.environ.get('AYEC_CAPTURE_PC_BUILDER_GEOMETRY') == '1':
                    import json
                    pc_builder_tabs = getattr(routed_page, 'tabs', None)
                    if pc_builder_tabs is not None:
                        pc_builder_tabs.setCurrentIndex(2)
                        if hasattr(routed_page, '_ensure_tab_loaded'):
                            routed_page._ensure_tab_loaded(2)
                        app.processEvents()
                    def pc_builder_rect(widget):
                        if widget is None:
                            return None
                        point = widget.mapTo(window, QPoint(0, 0))
                        return [point.x(), point.y(), widget.width(), widget.height()]
                    def pc_builder_font(widget):
                        font = widget.font()
                        return {'family': font.family(), 'point_size': font.pointSizeF(), 'pixel_size': font.pixelSize()}
                    pc_builder_page = getattr(routed_page, 'pc_builder_page', None) or routed_page
                    pc_builder_rows = pc_builder_page.findChildren(QWidget, 'ComponentRow')
                    pc_builder_summary = pc_builder_page.findChild(QWidget, 'SummaryPanel')
                    pc_builder_summary_items = []
                    if pc_builder_summary and pc_builder_summary.layout():
                        for index in range(pc_builder_summary.layout().count()):
                            item = pc_builder_summary.layout().itemAt(index)
                            widget = item.widget()
                            if widget is None:
                                continue
                            row, column, row_span, column_span = pc_builder_summary.layout().getItemPosition(index)
                            item_data = {'row': row, 'column': column, 'row_span': row_span, 'column_span': column_span, 'rect': pc_builder_rect(widget)}
                            if hasattr(widget, 'text'):
                                item_data['text'] = str(widget.text())[:40]
                            pc_builder_summary_items.append(item_data)
                    pc_builder_title = next((item for item in pc_builder_page.findChildren(QLabel) if item.text().endswith('Bilgisayar Topla')), None)
                    print('PC_BUILDER_GEOMETRY', json.dumps({
                        'window': [window.width(), window.height()],
                        'route_type': type(routed_page).__name__,
                        'tab_index': pc_builder_tabs.currentIndex() if pc_builder_tabs is not None else None,
                        'tab_count': pc_builder_tabs.count() if pc_builder_tabs is not None else None,
                        'page': pc_builder_rect(pc_builder_page),
                        'header': pc_builder_rect(pc_builder_page.findChild(QWidget, 'PCHeader')),
                        'customer': pc_builder_rect(pc_builder_page.findChild(QWidget, 'CustSearch')),
                        'preset': pc_builder_rect(pc_builder_page.findChild(QWidget, 'PresetBar')),
                        'column_header': pc_builder_rect(pc_builder_page.findChild(QWidget, 'ColHeader')),
                        'first_row': pc_builder_rect(pc_builder_rows[0]) if pc_builder_rows else None,
                        'last_row': pc_builder_rect(pc_builder_rows[-1]) if pc_builder_rows else None,
                        'summary': pc_builder_rect(pc_builder_page.findChild(QWidget, 'SummaryPanel')),
                        'summary_items': pc_builder_summary_items,
                        'actions': pc_builder_rect(pc_builder_page.findChild(QWidget, 'ActionBar')),
                        'title_font': pc_builder_font(pc_builder_title) if pc_builder_title else None,
                    }, ensure_ascii=True))
                if not window.grab().save(str(path)):
                    raise AssertionError('Native shell screenshot could not be saved')
                if page_id == 21 and os.environ.get('AYEC_CAPTURE_CUSTOMER_STATE') == '1':
                    import json
                    customer_table = getattr(routed_page, 'table', None)
                    rows = []
                    if customer_table is not None:
                        for row in range(customer_table.rowCount()):
                            id_item = customer_table.item(row, 1)
                            name_item = customer_table.item(row, 2)
                            id_cell = customer_table.cellWidget(row, 1)
                            name_cell = customer_table.cellWidget(row, 2)
                            customer_data = id_item.data(Qt.ItemDataRole.UserRole) if id_item else None
                            name_labels = name_cell.findChildren(QLabel) if name_cell else []
                            rows.append({
                                'id': id_cell.findChild(QLabel).text() if id_cell and id_cell.findChild(QLabel) else str(customer_data.get('id', '')) if customer_data else '',
                                'name': next((label.text() for label in name_labels if len(label.text()) > 3), name_item.data(Qt.ItemDataRole.UserRole + 1) if name_item else ''),
                                'type': customer_data.get('type', '') if customer_data else '',
                                'is_partner': customer_data.get('is_partner', 0) if customer_data else 0,
                            })
                    state_path = output / 'customer_table_state.json'
                    state = {
                        'routed_db_is_capture_db': getattr(routed_page, 'db', None) is db,
                        'routed_db_name': getattr(getattr(routed_page, 'db', None), '_db_name', ''),
                        'worker_filter_type': getattr(getattr(routed_page, 'worker', None), 'filter_type', None),
                        'worker_search_query': getattr(getattr(routed_page, 'worker', None), 'search_query', None),
                        'worker_limit': getattr(getattr(routed_page, 'worker', None), 'limit', None),
                        'worker_offset': getattr(getattr(routed_page, 'worker', None), 'offset', None),
                        'total_count': getattr(routed_page, 'total_count', None),
                        'limit': getattr(routed_page, 'limit', None),
                        'current_page': getattr(routed_page, 'current_page', None),
                        'filter_type': getattr(routed_page, 'current_filter_type', None),
                        'rows': rows,
                        'raw_rows': getattr(routed_page, '_reference_raw_customer_rows', []),
                        'query_preview': [dict(row) for row in db.conn.execute(
                            "SELECT id, name, type, is_partner FROM customers WHERE COALESCE(is_deleted, 0)=0 AND COALESCE(is_partner, 0)=0 ORDER BY name LIMIT 10"
                        ).fetchall()],
                    }
                    state_path.write_text(json.dumps(state, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
                if page_id == 130 and settings_index == 14 and os.environ.get('AYEC_CAPTURE_QUICK_NOTES_GEOMETRY') == '1':
                    import json
                    def quick_notes_rect(widget):
                        point = widget.mapTo(window, QPoint(0, 0))
                        return [point.x(), point.y(), widget.width(), widget.height()]
                    quick_notes_widget = routed_page.content_area.currentWidget()
                    print('QUICK_NOTES_GEOMETRY', json.dumps({
                        'window': [window.width(), window.height()],
                        'settings_page': quick_notes_rect(routed_page),
                        'content_area': quick_notes_rect(routed_page.content_area),
                        'widget': quick_notes_rect(quick_notes_widget),
                        'title': next((quick_notes_rect(item) for item in quick_notes_widget.findChildren(QLabel) if item.text().startswith('H\u0131zl\u0131 Notlar')), None),
                        'filter': quick_notes_rect(quick_notes_widget.filter_frame),
                        'table': quick_notes_rect(quick_notes_widget.table),
                        'refresh': quick_notes_rect(quick_notes_widget.btn_refresh),
                        'add': quick_notes_rect(quick_notes_widget.btn_add),
                        'description': next((quick_notes_rect(item) for item in quick_notes_widget.findChildren(QLabel) if item.text().startswith('Teknisyen paneli')), None),
                        'count': quick_notes_rect(quick_notes_widget.lbl_count),
                        'filter_combo': quick_notes_rect(quick_notes_widget.combo_filter),
                        'search_input': quick_notes_rect(quick_notes_widget.inp_search),
                        'quick_tags': [quick_notes_rect(item) for item in quick_notes_widget.quick_tag_buttons],
                    }, ensure_ascii=True))
                if page_id == 21 and os.environ.get('AYEC_VERIFY_CUSTOMER_HEADER_RESTORE') == '1':
                    window.on_menu_click(40)
                    app.processEvents()
                    if getattr(window.app_header, '_customer_reference_mode', False):
                        raise AssertionError('Customer reference header remained active after navigation.')
                    if not window.app_header.isVisible():
                        raise AssertionError('Shared application header did not restore after navigation.')
                return path
    finally:
        SalesHubPage._is_automotive = original_sector_check
        if reference_dialog is not None:
            reference_dialog.close()
            reference_dialog.deleteLater()
        if window is not None:
            window.close()
            window.deleteLater()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--page', type=int, default=150)
    parser.add_argument('--width', type=int, default=1600)
    parser.add_argument('--height', type=int, default=1280)
    parser.add_argument('--theme', choices=tuple(ThemeManager.THEME_FILES), default='Koyu Mavi')
    parser.add_argument('--sample-reference', action='store_true')
    parser.add_argument('--dialog', choices=('new_customer', 'customer_notes', 'customer_360', 'new_service', 'transaction_details', 'payment_collection', 'technician_panel', 'technician_station', 'bulk_stock_select'))
    parser.add_argument('--settings-index', type=int, default=14)
    parser.add_argument('--settings-tab', type=int, default=1)
    options = parser.parse_args()
    run(
        page_id=options.page, width=options.width, height=options.height,
        theme_name=options.theme,
        sample_reference=options.sample_reference, dialog=options.dialog,
        settings_index=options.settings_index, settings_tab=options.settings_tab,
    )
