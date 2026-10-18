from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"
DESKTOP = ROOT / "src" / "ui" / "dialogs" / "new_service_dialog.py"


def test_web_service_intake_supports_desktop_custom_device_type():
    desktop = DESKTOP.read_text(encoding="utf-8")
    web = (WEB / "automotive-parity.js").read_text(encoding="utf-8")
    technical_plugin = (ROOT / "plugins" / "teknik_servis" / "sector_plugin.py").read_text(encoding="utf-8")
    automotive_plugin = (ROOT / "plugins" / "otomotiv" / "sector_plugin.py").read_text(encoding="utf-8")

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
    assert '"name": "inspection_summary"' in technical_plugin
    assert 'name="inspection_summary"' in web
    assert 'inspection_summary:values.inspection_summary||""' in web
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'name="inspection_summary"' in app
    assert 'inspection_summary:values.inspection_summary||""' in app
    assert 'inspection_summary:values.inspection_summary,' in app
    assert 'name="inspection_summary">${esc(service.inspection_summary||"")}' in app
    assert '"name": "invoice_ready"' in automotive_plugin
    assert 'name="invoice_ready"' in web and 'invoice_ready_at:invoiceReadyAt' in web
    assert 'name="invoice_ready"' in app and 'invoice_ready_at:invoiceReadyAt' in app
    assert 'name="service_type" required' in web and 'service_type:values.service_type||""' in web
    assert 'name="service_type" required' in app and 'service_type:values.service_type||""' in app
    assert 'name="vehicle_vin">' in app and 'serial_no:d.serial||""' in app
    assert 'sector_extension:automotive?{vehicle_plate:d.plate||""' in app
    assert 'name="vehicle_type"' in app and 'name="engine_type"' in app
    assert 'vehicle_year:+d.year||null,vehicle_type:d.vehicle_type||"",engine_type:d.engine_type||"",fuel_type:d.fuel_type||""' in app
    assert 'serial_no:values.serial||""' in web
    assert 'name="vehicle_plate"' in app and 'vehicle_plate:values.vehicle_plate||""' in app
    assert 'name="current_km" type="number"' in app and 'current_km:values.current_km||""' in app
    assert "data-service-automotive-vin" in app and "service.sector_extension?.vehicle_vin" in app
    assert "data-service-automotive-descriptor" in app and "service.sector_extension?.service_type" in app
    assert "data-service-automotive-odometer" in app and "service.sector_extension?.current_km" in app
    assert 'sector_extension:automotive?{vehicle_plate:values.vehicle_plate||""' in app
    assert 'options(automotive?["Yok","Var","Firma Garantisi"]:["Garantili","Garanti D\\u0131\\u015f\\u0131","Bilinmiyor"]' in app
    assert 'name="warranty_status" ${automotive?"":"required"}' in app
    assert 'invoice_ready_at:automotive?(values.invoice_ready?' in app
    assert '[...selectedFaultNotes,values.fault,values.repair_details&&values.repair_details.trim()?' in web
    assert '`[NOT]: ${values.repair_details}`' in web
    assert '`[TEKN\\u0130K]: ${values.internal_notes}`' in web
    assert '["Garantili","Garanti D\\u0131\\u015f\\u0131","Bilinmiyor"]' in web
    assert 'name="warranty_status" ${automotive?"":"required"}' in web
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
    assert '[NOT]: ${values.repair_details}' in app
    assert '[TEKN\\u0130K]: ${values.internal_notes}' in app
    assert '["Garantili","Garanti D\\u0131\\u015f\\u0131","Bilinmiyor"]' in app
    desktop = DESKTOP.read_text(encoding="utf-8")
    assert "full_desc += f\"\\n[NOT]: {data['repair_details']}\"" in desktop
    technical_marker = "[TEKN" + chr(304) + "K]"
    assert 'full_desc += f"\\n' + technical_marker + ": {data['internal_notes']}\"" in desktop
    assert '"bios_password", "TEXT"' in backend

