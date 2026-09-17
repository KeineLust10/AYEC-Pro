import json
import sqlite3

from pypdf import PdfReader

from src.utils.offer_pdf_data import load_offer_pdf_data
from src.utils.pdf_manager import PDFManagerQt


class OfferDb:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE offers (
                id INTEGER PRIMARY KEY,
                offer_no TEXT,
                customer_name TEXT,
                company_name TEXT,
                contact_name TEXT,
                project_name TEXT,
                template_type TEXT,
                currency_code TEXT,
                currency_symbol TEXT,
                subtotal REAL,
                discount REAL,
                vat_rate REAL,
                vat_amount REAL,
                total REAL,
                payload_json TEXT
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE offer_items (
                id INTEGER PRIMARY KEY,
                offer_id INTEGER,
                service TEXT,
                description TEXT,
                brand TEXT,
                qty REAL,
                unit_price REAL,
                payload_json TEXT
            )
            """
        )

    def get_setting(self, _key, default=""):
        return default


def test_synced_web_offer_can_be_rebuilt_from_database_rows():
    db = OfferDb()
    db.cursor.execute(
        """
        INSERT INTO offers (
            id, offer_no, customer_name, company_name, contact_name,
            project_name, template_type, currency_code, currency_symbol,
            subtotal, discount, vat_rate, vat_amount, total, payload_json
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "PRF-2026-0001",
            "Engin Mamu",
            "Ayec",
            "Engin Mamu",
            "M2 SSD",
            "modern",
            "TRY",
            "",
            9600.0,
            0.0,
            0.20,
            1920.0,
            11520.0,
            json.dumps({"source": "web"}),
        ),
    )
    db.cursor.execute(
        """
        INSERT INTO offer_items (
            id, offer_id, service, description, brand, qty, unit_price, payload_json
        ) VALUES (1, 1, ?, ?, ?, 1, 9600, ?)
        """,
        ("M2 SSD 1 TB", "M2 SSD 1 TB", "Kingston", json.dumps({"code": "SSD-1"})),
    )
    db.conn.commit()

    data = load_offer_pdf_data(db, 1)

    assert data["offer"]["offer_no"] == "PRF-2026-0001"
    assert data["items"][0]["service"] == "M2 SSD 1 TB"
    assert data["items"][0]["price"] == 9600.0
    assert data["totals"] == (9600.0, 0.0, 0.20, 1920.0, 11520.0)
    assert data["currency_symbol"] == "\u20ba"


def test_import_source_marker_is_not_used_as_offer_description():
    db = OfferDb()
    db.cursor.execute(
        """
        INSERT INTO offers (
            id, offer_no, customer_name, company_name, contact_name,
            project_name, template_type, currency_code, currency_symbol,
            subtotal, discount, vat_rate, vat_amount, total, payload_json
        ) VALUES (1, 'PRF-CLEAN-1', 'Customer', 'AYEC Pro', 'Customer',
                  '', 'modern', 'USD', '$', 35, 0, 0, 0, 35, '{}')
        """
    )
    db.cursor.execute(
        """
        INSERT INTO offer_items (
            id, offer_id, service, description, brand, qty, unit_price,
            payload_json
        ) VALUES (1, 1, 'IP Camera', 'Web akilli ice aktarma',
                  'Dahua', 1, 35, '{}')
        """
    )
    db.conn.commit()

    data = load_offer_pdf_data(db, 1)

    assert data["items"][0]["description"] == "Dahua"


def test_synced_web_offer_data_generates_a_real_pdf(tmp_path):
    db = OfferDb()
    db.cursor.execute(
        """
        INSERT INTO offers (
            id, offer_no, customer_name, company_name, contact_name,
            project_name, template_type, currency_code, currency_symbol,
            subtotal, discount, vat_rate, vat_amount, total, payload_json
        ) VALUES (1, 'PRF-WEB-2', 'Test Customer', 'AYEC Pro',
                  'Test Customer', 'Security Project', 'modern', 'USD', '$',
                  100, 0, 0.20, 20, 120, '{}')
        """
    )
    db.cursor.execute(
        """
        INSERT INTO offer_items (
            id, offer_id, service, description, brand, qty, unit_price, payload_json
        ) VALUES (1, 1, 'Camera', 'Security camera', 'AYEC', 2, 50, '{}')
        """
    )
    db.conn.commit()
    data = load_offer_pdf_data(db, 1)
    target = tmp_path / "synced-offer.pdf"
    manager = PDFManagerQt(db)
    manager._open_file = lambda _filename: None

    success, result = manager.create_proforma(
        template_type="modern",
        cart_items=data["items"],
        totals=data["totals"],
        company_name="AYEC Pro",
        customer_name="Test Customer",
        project_name="Security Project",
        contact_name="Test Customer",
        reference_no="PRF-WEB-2",
        save_path=str(target),
        currency=data["currency_symbol"],
    )

    assert success is True, result
    assert target.read_bytes().startswith(b"%PDF-")


def test_service_offer_restores_full_maintenance_list():
    db = OfferDb()
    db.cursor.executescript(
        """
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY,
            tracking_no TEXT,
            repair_details TEXT,
            fault_description TEXT,
            vehicle_maintenance_card_id INTEGER
        );
        CREATE TABLE vehicle_maintenance_cards (
            id INTEGER PRIMARY KEY,
            linked_device_tracking_no TEXT
        );
        CREATE TABLE vehicle_maintenance_items (
            id INTEGER PRIMARY KEY,
            card_id INTEGER,
            item_label TEXT,
            performed INTEGER
        );
        INSERT INTO offers (
            id, offer_no, customer_name, company_name, contact_name,
            project_name, template_type, currency_code, currency_symbol,
            subtotal, discount, vat_rate, vat_amount, total, payload_json
        ) VALUES (
            1, 'REF1', 'Hasan', 'AYEC Pro', 'Hasan', 'SRV1', 'modern',
            'TRY', '', 2500, 0, 0.18, 450, 2950, '{}'
        );
        INSERT INTO offer_items (
            id, offer_id, service, description, brand, qty, unit_price, payload_json
        ) VALUES (
            1, 1, 'Servis Iscilik - Ford Courier',
            'Bakim kalemleri: Yag Degisimi, Yag Filtresi ve 3 kalem daha',
            '', 1, 2500, '{}'
        );
        INSERT INTO devices VALUES (
            1, 'SRV1', '',
            'Bakim kalemleri: Yag Degisimi, Yag Filtresi ve 3 kalem daha', 10
        );
        INSERT INTO vehicle_maintenance_cards VALUES (10, 'SRV1');
        INSERT INTO vehicle_maintenance_items VALUES (1, 10, 'Yag Degisimi', 1);
        INSERT INTO vehicle_maintenance_items VALUES (2, 10, 'Yag Filtresi', 1);
        INSERT INTO vehicle_maintenance_items VALUES (3, 10, 'Hava Filtresi', 1);
        INSERT INTO vehicle_maintenance_items VALUES (4, 10, 'Polen Filtresi', 1);
        INSERT INTO vehicle_maintenance_items VALUES (5, 10, 'Antifriz', 1);
        """
    )
    db.conn.commit()

    data = load_offer_pdf_data(db, 1)
    description = data["items"][0]["description"]

    assert description.splitlines() == [
        "1. Yag Degisimi",
        "2. Yag Filtresi",
        "3. Hava Filtresi",
        "4. Polen Filtresi",
        "5. Antifriz",
    ]
    assert "kalem daha" not in description


def test_technical_service_offer_uses_device_work_lines_without_automotive_data():
    db = OfferDb()
    db.cursor.executescript(
        """
        CREATE TABLE devices (
            id INTEGER PRIMARY KEY,
            tracking_no TEXT,
            repair_details TEXT,
            fault_description TEXT
        );
        INSERT INTO offers (
            id, offer_no, customer_name, company_name, contact_name,
            project_name, template_type, currency_code, currency_symbol,
            subtotal, discount, vat_rate, vat_amount, total, payload_json
        ) VALUES (
            1, 'TECH-1', 'Test Customer', 'AYEC Pro', 'Test Customer',
            'TRK-TECH-1', 'modern', 'TRY', '', 1000, 0, 0.20, 200, 1200, '{}'
        );
        INSERT INTO offer_items (
            id, offer_id, service, description, brand, qty, unit_price, payload_json
        ) VALUES (
            1, 1, 'Servis Iscilik - Notebook', 'Genel servis islemi',
            '', 1, 1000, '{}'
        );
        INSERT INTO devices VALUES (
            1, 'TRK-TECH-1', 'Fan temizligi\nTermal macun yenileme', 'Asiri isinma'
        );
        """
    )
    db.conn.commit()

    data = load_offer_pdf_data(db, 1)

    assert data["items"][0]["description"].splitlines() == [
        "1. Fan temizligi",
        "2. Termal macun yenileme",
    ]


def test_all_offer_templates_use_saved_date_currency_and_professional_sections(tmp_path):
    db = OfferDb()
    manager = PDFManagerQt(db)
    manager._open_file = lambda _filename: None
    items = [
        {
            "service": "IP Kamera",
            "description": "Dis ortam guvenlik kamerasi",
            "brand": "AYEC",
            "model": "CAM-8",
            "code": "SEC-001",
            "qty": 2,
            "price": 5750.5,
        }
    ]

    for template in ("modern", "corporate", "minimal", "bulut_deri"):
        target = tmp_path / f"{template}.pdf"
        success, result = manager.create_proforma(
            template_type=template,
            cart_items=items,
            totals=(11501.0, 0.0, 0.0, 0.0, 11501.0),
            company_name="Bulut Teknoloji",
            customer_name="Ahmet Yilmaz",
            customer_company="ABC Guvenlik",
            project_name="Kamera Kurulumu",
            contact_name="Ahmet Yilmaz",
            reference_no="PRF-2026-0042",
            offer_date="2026-07-08T10:38:44",
            currency="\u20ba",
            currency_code="TRY",
            save_path=str(target),
        )

        assert success is True, result
        text = "\n".join(page.extract_text() or "" for page in PdfReader(target).pages)
        assert "08.07.2026" in text
        assert "23.07.2026" in text
        assert "ABC Guvenlik" in text
        assert "Ahmet Yilmaz" in text
        assert "Hesaplanan KDV(%0.00)" in text
        assert "11.501,00 \u20ba" in text
        assert "T\u00fcrk Liras\u0131 (TRY)" in text
        assert "Amerikan Dolar\u0131" not in text
        assert "MODERN" not in text
        assert "KURUMSAL" not in text
        assert "ZEBRA" not in text
