from src.ui.pages._stock_import import StockImportMixin


def test_customer_export_with_english_headers_is_rejected_from_stock_import():
    parse_result = {
        "source_path": "export.xlsx",
        "detected_columns": ["Customer Name", "Phone", "Email"],
        "raw_rows": [
            {"Customer Name": "Casey QA", "Phone": "555-0100", "Email": "qa@example.test"}
        ],
    }

    assert StockImportMixin._looks_like_customer_export(parse_result) is True


def test_stock_export_with_english_headers_is_not_misidentified():
    parse_result = {
        "source_path": "inventory.xlsx",
        "detected_columns": [
            "SKU",
            "Product Name",
            "Stock Quantity",
            "Purchase Price",
            "Sale Price",
            "Barcode",
            "Category",
        ],
        "raw_rows": [],
    }

    assert StockImportMixin._looks_like_customer_export(parse_result) is False


def test_customer_export_with_turkish_headers_is_rejected_from_stock_import():
    parse_result = {
        "source_path": "export.xlsx",
        "detected_columns": ["M\u00fc\u015fteri Ad\u0131", "Telefon", "E-posta"],
        "raw_rows": [
            {"M\u00fc\u015fteri Ad\u0131": "Ay\u015fe QA", "Telefon": "555-0100", "E-posta": "qa@example.test"}
        ],
    }

    assert StockImportMixin._looks_like_customer_export(parse_result) is True
