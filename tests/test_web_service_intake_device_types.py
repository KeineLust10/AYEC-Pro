from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
DESKTOP = ROOT / "src" / "ui" / "dialogs" / "new_service_dialog.py"


def test_web_service_intake_supports_desktop_custom_device_type():
    desktop = DESKTOP.read_text(encoding="utf-8")
    web = (WEB / "automotive-parity.js").read_text(encoding="utf-8")

    assert 'OTHER_DEVICE_TYPE = "Di\\u011fer"' in desktop
    assert "def _on_device_type_changed(self, device_type):" in desktop
    assert 'data-service-other-device hidden' in web
    assert 'otherDeviceInput.required=isOther' in web
    assert 'values.device_type==="Di\\u011fer"?String(values.other_device_type||"").trim()' in web
    assert 'device_brands?limit=500' in web
    assert 'serviceModelOptions' in web
    assert 'row.device_type' in web and 'row.device_model' in web
    assert 'serviceCustomerOptions' in web
    assert 'customerSearchInput.addEventListener("input"' in web
    assert 'history.map(row=>String(row.device_type||"").trim())' in web
    assert 'deviceTypeInput.insertBefore(option,otherTypeOption||null)' in web
    assert '/api/desktop/table/fast_notes?limit=500' in web
    assert 'data-service-fault-note-options' in web
    assert 'fault_description:[...selectedFaultNotes,values.fault]' in web
    assert 'data-service-accessory-options' in web


def test_service_intake_uploads_selected_photos_to_intake_gallery():
    web = (WEB / "automotive-parity.js").read_text(encoding="utf-8")

    assert 'data-service-photo-selected' in web
    assert 'selectedServicePhotos.length>=5' in web
    assert 'reader.readAsDataURL(file)' in web
    assert '"/api/desktop/external-tracking/photos"' in web
    assert 'stage:"Giri\\u015f"' in web


def test_service_intake_migrates_desktop_handover_and_bios_fields():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")

    for field in ("delivery_method", "service_location", "other_info", "bios_password"):
        assert f'name="{field}"' in app
        assert f"{field}:values.{field}" in app or f'"{field}"' in app
    assert '"bios_password", "TEXT"' in backend
