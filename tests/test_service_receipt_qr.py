import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pypdf import PdfReader

from src.ui.pages._dashboard_func_mixin import DashboardFuncMixin
from src.utils._pdf_service_mixin import PDFServiceMixin
from src.utils.pdf_manager import PDFManagerQt


class _SettingsDb:
    def get_setting(self, key, default=""):
        values = {
            "company_name": "AYEC Pro Test",
            "company_phone": "5550000000",
            "company_address": "Test Address",
            "service_terms": "Test service terms.",
        }
        return values.get(key, default)


def test_service_qr_drawing_contains_tracking_payload():
    drawing = PDFServiceMixin._service_qr_drawing("SRV-1001")

    assert drawing.contents
    assert drawing.contents[0].value.startswith("https://ayecpro.com/servis/takip/")
    assert "." in drawing.contents[0].value.rsplit("/", 1)[-1]


def test_detailed_service_receipt_with_qr_is_created():
    temp_root = Path.cwd() / ".tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir:
        manager = PDFManagerQt(_SettingsDb())
        manager._get_save_path = lambda: temp_dir
        manager._open_file = lambda _path: None
        device = {
            "tracking_no": "SRV-1001",
            "customer_name": "Test Customer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "SERIAL-1",
            "reported_fault": "Screen issue",
            "repair_notes": "Repair completed",
            "status": "Ready",
            "delivery_type": "Pickup",
        }

        success, output_path = manager.create_service_receipt(
            device,
            [{"part_name": "Test Part", "quantity": 1, "price": 50}],
            100,
        )

        assert success is True
        assert Path(output_path).exists()
        assert len(PdfReader(output_path).pages) == 1


def test_dashboard_label_b_uses_pdf_generator():
    class _Db:
        def get_device_by_tracking_no(self, tracking_no):
            return {"tracking_no": tracking_no}

    class _Page:
        db = _Db()

        def __init__(self):
            self.messages = []

        def notify(self, message, level):
            self.messages.append((message, level))

        def _get_service_print_options(self, profile, title):
            return SimpleNamespace(
                direct_print=False,
                printer_name="",
                label_width_mm=70.0,
                label_height_mm=45.0,
            )

        def _complete_service_print(self, path, options, success_message):
            self.notify(f"{success_message}: {path}", "success")

    page = _Page()
    with patch("src.utils.pdf_manager.PDFManagerQt") as manager_class:
        manager_class.return_value.create_device_label_b.return_value = (
            True,
            "label.pdf",
        )
        DashboardFuncMixin._print_service_label_b(page, "SRV-1001")

    manager_class.return_value.create_device_label_b.assert_called_once_with(
        {"tracking_no": "SRV-1001"},
        width_mm=70.0,
        height_mm=45.0,
    )
    assert page.messages == [
        ("Cihaz etiketi B olu\u015fturuldu: label.pdf", "success")
    ]


def test_service_print_templates_have_expected_page_sizes():
    temp_root = Path.cwd() / ".tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir:
        manager = PDFManagerQt(_SettingsDb())
        manager._get_save_path = lambda: temp_dir
        manager._open_file = lambda _path: None
        device = {
            "tracking_no": "SRV-2002",
            "customer_name": "Test Customer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "SERIAL-2",
            "reported_fault": "Power issue",
            "status": "Waiting",
        }
        outputs = [
            manager.create_short_service_receipt(device, [], 0)[1],
            manager.create_detailed_service_receipt(device, [], 0)[1],
            manager.create_cargo_receipt(device, [], 0)[1],
            manager.create_device_label(device)[1],
            manager.create_device_label_b(device)[1],
            manager.create_service_receipt(device, [], 0)[1],
        ]

        page_sizes = []
        for output in outputs:
            path = Path(output)
            assert path.exists()
            reader = PdfReader(path)
            assert len(reader.pages) == 1
            box = reader.pages[0].mediabox
            page_sizes.append((round(float(box.width)), round(float(box.height))))

        assert len(set(page_sizes)) == 5
        assert page_sizes[1] == page_sizes[5]


def test_detailed_service_receipt_supports_a3_a4_a5_and_delivery_fields():
    temp_root = Path.cwd() / ".tmp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temp_dir:
        manager = PDFManagerQt(_SettingsDb())
        manager._get_save_path = lambda: temp_dir
        manager._open_file = lambda _path: None
        device = {
            "tracking_no": "SRV-3003",
            "customer_name": "Owner Company",
            "customer_contact": "5551002000",
            "delivered_by_name": "Delivery Person",
            "delivered_by_phone": "5553004000",
            "device_brand": "Brand",
            "device_model": "Model",
            "serial_no": "SERIAL-3",
            "reported_fault": "Power issue",
        }

        outputs = {}
        for page_size in ("A3", "A4", "A5"):
            page_device = dict(device)
            page_device["tracking_no"] = f"SRV-{page_size}"
            success, output = manager.create_detailed_service_receipt(
                page_device,
                [],
                0,
                page_size=page_size,
                orientation="portrait",
            )
            assert success is True
            outputs[page_size] = PdfReader(output)

        assert all(len(reader.pages) == 1 for reader in outputs.values())

        sizes = {
            key: (
                round(float(reader.pages[0].mediabox.width)),
                round(float(reader.pages[0].mediabox.height)),
            )
            for key, reader in outputs.items()
        }
        assert sizes["A3"] != sizes["A4"] != sizes["A5"]
        text = outputs["A4"].pages[0].extract_text()
        normalized_text = " ".join(text.split())
        assert "CIHAZ SAHIBI" in normalized_text
        assert "TESLIM EDEN" in normalized_text
        assert "Delivery Person" in text
        assert "5553004000" in text


def test_detailed_service_receipt_does_not_copy_owner_into_delivery_fields():
    manager = PDFManagerQt(_SettingsDb())
    context = manager._service_print_context(
        {
            "tracking_no": "SRV-4004",
            "customer_name": "Owner Company",
            "customer_contact": "5551002000",
        },
        [],
        0,
    )

    assert context["delivered_by"] == "-"
    assert context["delivered_phone"] == "-"


def test_dashboard_invoice_action_opens_customer_invoice_dialog():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute(
        """
        CREATE TABLE devices (
            tracking_no TEXT,
            customer_id INTEGER,
            is_deleted INTEGER DEFAULT 0
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO devices (tracking_no, customer_id)
        VALUES ('SRV-1001', 42)
        """
    )

    class _Db:
        pass

    db = _Db()
    db.cursor = cursor

    class _Page:
        def __init__(self):
            self.db = db
            self.refresh_count = 0
            self.messages = []

        def refresh_data(self):
            self.refresh_count += 1

        def notify(self, message, level):
            self.messages.append((message, level))

    page = _Page()
    try:
        with patch(
            "src.ui.dialogs.service_invoice_dialog.ServiceInvoiceDialog"
        ) as dialog_class:
            DashboardFuncMixin._open_context_menu_action_deferred(
                page,
                "invoice",
                "SRV-1001",
            )

        dialog_class.assert_called_once_with(db, 42, page)
        dialog_class.return_value.exec.assert_called_once_with()
        assert page.refresh_count == 1
        assert page.messages == []
    finally:
        connection.close()
