from tools.ocr_regression_guard import validate_result


def test_ocr_contract_accepts_expected_metadata_and_rows():
    case = {
        "min_rows": 2,
        "max_rows": 2,
        "metadata": {"invoice_no": "INV-42", "supplier_company": "ACME"},
        "rows": [
            {"code": "CAM-1", "currency": "USD", "stock": 2},
            {"name_contains": "camera", "purchase_price": 25.0},
        ],
        "forbidden_name_contains": ["total", "discount"],
    }
    result = {
        "metadata": {"invoice_no": "INV-42", "supplier_company": "ACME"},
        "rows": [
            {
                "code": "CAM-1",
                "name": "Security Camera",
                "currency": "USD",
                "stock": 2,
                "purchase_price": 25.0,
            },
            {
                "code": "NVR-1",
                "name": "NVR Recorder",
                "currency": "USD",
                "stock": 1,
                "purchase_price": 80.0,
            },
        ],
    }

    assert validate_result(case, result) == []


def test_ocr_contract_rejects_summary_leak_and_missing_row():
    case = {
        "min_rows": 1,
        "rows": [{"code": "EXPECTED"}],
        "forbidden_name_contains": ["grand total"],
    }
    result = {
        "metadata": {},
        "rows": [{"code": "TOTAL", "name": "Grand Total", "stock": 1}],
    }

    failures = validate_result(case, result)

    assert any("expected row was not found" in item for item in failures)
    assert any("forbidden summary row" in item for item in failures)
