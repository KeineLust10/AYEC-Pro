from src.utils.status_utils import normalize_device_status


def test_test_ediliyor_maps_to_test_column():
    assert normalize_device_status("Test Ediliyor") == "Test S\u00fcrecinde"


def test_seeded_active_statuses_map_to_kanban_columns():
    expected = {
        "Beklemede": "Bekliyor",
        "Islemde": "Tamirde",
        "Test Ediliyor": "Test S\u00fcrecinde",
    }

    assert {
        status: normalize_device_status(status)
        for status in expected
    } == expected
