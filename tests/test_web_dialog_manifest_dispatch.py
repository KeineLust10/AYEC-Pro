import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quick_note_manifest_entry_opens_the_working_notes_manager():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(dialog)")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'quick_notes_editor:()=>{settingsSection="notes";navigate("settings")}' in dispatch
    assert 'if(direct[key])return direct[key]()' in dispatch
    assert 'if(settingsSection==="notes")return' in app
    assert 'if($("#quickNotesHost")){loadQuickNotes();$("#quickNoteRefresh").onclick=loadQuickNotes;$("#quickNoteAdd").onclick=()=>quickNoteDialog();$("#quickNoteApplyProfile").onclick=()=>applyQuickNoteProfile($("#quickNoteProfile").value)}' in app
    assert 'await desktopWrite("fast_notes",payload)' in app


def test_settings_section_dataset_stays_current_for_quick_notes_layout():
    settings_theme = (ROOT / "Web_Arayuzu" / "web" / "settings-theme-reference.js").read_text(encoding="utf-8")
    desktop_parity = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")
    render_start = settings_theme.index("render = function () {")
    render_end = settings_theme.index("const host = document.querySelector(\".settings-content\")", render_start)
    render_hook = settings_theme[render_start:render_end]
    assert 'document.body.dataset.settingsSection = settingsSection;' in render_hook
    assert 'document.body.removeAttribute("data-settings-section")' in render_hook
    assert 'body[data-page="settings"][data-settings-section="notes"] .settings-layout' in desktop_parity
    assert 'body[data-page="settings"][data-settings-section="notes"] button[data-action="save-settings"]' in desktop_parity
from pathlib import Path


def test_kb_article_manifest_entry_opens_the_desktop_article_form_and_saves():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openKnowledgeArticleDialog()")
    end = app.index("function openManifestDialog(", start)
    editor = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'name="title" required' in editor
    assert 'name="tags"' in editor
    assert 'name="content" rows="9" required' in editor
    assert 'apiFetch("/api/desktop/table/kb_articles"' in editor
    assert 'if(!article.title)throw Error' in editor
    assert 'if(!article.content)throw Error' in editor
    assert 'add_kb_article_dialog:()=>openKnowledgeArticleDialog()' in dispatch


def test_service_definition_manifest_entry_uses_desktop_fields_and_write_shape():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openServiceDefinitionDialog()")
    end = app.index("function openManifestDialog(", start)
    editor = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    for field in ("name", "barcode", "description", "service_category", "duration_minutes", "vat_rate", "price_try", "price_usd", "price_eur", "is_active"):
        assert f'name="{field}"' in editor
    assert 'apiFetch("/api/desktop/table/services"' in editor
    assert 'add_service_definition_dialog:()=>openServiceDefinitionDialog()' in dispatch
    assert 'currency="USD";price=priceUsd' in editor
    assert 'currency="EUR";price=priceEur' in editor
    assert 'trim().toUpperCase()' in editor


def test_project_unit_sale_manifest_entry_opens_the_project_sale_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'project_unit_sale_dialog:()=>openProjectUnitSaleManifestDialog()' in dispatch
    helper_start = app.index("function openProjectUnitSaleManifestDialog()")
    helper = app[helper_start:]
    assert 'async function p9OpenProjectUnitSale(unitId)' in app
    assert 'p9ProjectState.units' in helper
    assert 'p9OpenProjectUnitSale(unitId)' in helper
    assert 'data-p9-unit-sale="${esc(unit.id)}"' in app


def test_bank_detail_manifest_entry_uses_the_existing_bank_account_history_dialog():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openBankManifestDetail()")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'apiFetch("/api/desktop/table/bank_accounts?limit=500")' in helper
    assert 'ayecOpenBankAccountDetail(accounts[0])' in helper
    assert 'bank_detail_dialog:()=>openBankManifestDetail()' in dispatch
    assert 'function ayecOpenBankAccountDetail(account)' in app


def test_customer_history_manifest_entry_uses_customer_selector_and_360_history():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'customer_history_dialog:()=>customerSelect(customer360,' in dispatch
    assert 'function customer360(c)' in app
    assert 'const services=c.services||[]' in app
    assert 'const cari=finance.length?' in app


def test_vehicle_maintenance_manifest_entry_opens_the_existing_maintenance_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'vehicle_maintenance_dialog:()=>maintenanceDialog()' in dispatch
    assert 'async function maintenanceDialog(sourceRow={})' in app
    assert 'apiFetch("/api/desktop/vehicle-maintenance/save"' in app


def test_service_invoice_manifest_entry_selects_customer_and_opens_invoice_editor():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'service_invoice_dialog:()=>customerSelect(customer=>serviceInvoiceDialog(customer),' in dispatch
    assert 'async function serviceInvoiceDialog(customer)' in app
    assert 'apiFetch(`/api/desktop/service-invoices/${encodeURIComponent(customer.id)}`)' in app
    assert 'data-invoice-transaction' in app


def test_auth_manifest_entries_open_the_existing_login_and_registration_flows():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'login_dialog:()=>renderLogin()' in dispatch
    assert 'registration_dialog:()=>registrationEnabled?renderRegistration():renderLicenseActivation()' in dispatch



def test_bulk_stock_dialog_dispatch_uses_the_existing_sales_selection_workflow():
    root = Path(__file__).resolve().parents[1]
    app = (root / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    extension = (root / "Web_Arayuzu" / "web" / "bulk-sales-selection.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'bulk_stock_select_dialog:()=>{navigate("sales");setTimeout(()=>document.querySelector("[data-sales-bulk-select]")?.click(),120)}' in dispatch
    assert 'async function openBulkSalesSelection()' in extension
    assert 'data-bulk-mode="part"' in extension and 'data-bulk-mode="service"' in extension
    assert 'data-bulk-system' in extension and 'bulkSalesStatus' in extension and 'bulkSalesSort' in extension
    assert 'data-bulk-select-check' in extension and 'data-bulk-select-qty' in extension
    assert 'salesCart.push({productId:item.id,qty:quantity})' in extension
    assert 'salesCart.push({type:"service",serviceId:item.id' in extension


def test_bulk_payment_manifest_entry_opens_loan_installment_payment_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openBulkLoanPaymentWorkflow()")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'bulk_payment_dialog:()=>openBulkLoanPaymentWorkflow()' in dispatch
    assert '/api/desktop/table/loan_installments?limit=1000' in helper
    assert '/api/desktop/loan-installments/${encodeURIComponent(item.id)}/status' in helper
    assert 'data-loan-installment-check' in helper
    assert r'\u0054\u00fcm\u00fcn\u00fc Se\u00e7' in helper
    assert r'\u0054\u00fcm\u00fcn\u00fc \u00d6de' in helper
    assert 'openLoanEarlyClosureDialog(loan,unpaid,payRows)' in helper
    assert 'status:"Erken Kapat\u0131ld\u0131"' in helper
    assert 'id="loanEarlyPenalty" name="penalty_rate" type="number" min="0" max="5"' in helper
    assert 'loanEarlySummary' in helper and 'loanEarlyComparison' in helper


def test_dialog_manifest_generator_matches_runtime_source_and_served_paths():
    root = Path(__file__).resolve().parents[1]
    extractor = (root / "Web_Arayuzu" / "tools" / "extract_dialog_manifest.py").read_text(encoding="utf-8")
    server = (root / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert 'DIALOG_DIR = ROOT.parent / "src" / "ui" / "dialogs"' in extractor
    assert 'OUT_JSON = ROOT / "web" / "dialogs.generated.json"' in extractor
    assert 'DIALOGS_MANIFEST = WEB_ROOT / "dialogs.generated.json"' in server
    manifest_path = root / "Web_Arayuzu" / "web" / "dialogs.generated.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["summary"]["dialog_count"] >= 100
    assert len(manifest["dialogs"]) == manifest["summary"]["dialog_count"]


def test_customer_notes_manifest_entry_uses_the_existing_customer_notes_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'customer_notes_dialog:()=>customerSelect(openCustomerNotes,' in dispatch
    assert 'apiFetch("/api/desktop/table/customer_notes?limit=1000")' in app
    assert 'desktopWrite("customer_notes"' in app


def test_personnel_transaction_manifest_entry_opens_the_salary_and_bonus_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openPersonnelTransactionDialog()")
    end = app.index("function openBulkLoanPaymentWorkflow()", start)
    helper = app[start:end]
    dispatch_start = app.index("function openManifestDialog(")
    dispatch_end = app.index("function customerSelect(", dispatch_start)
    dispatch = app[dispatch_start:dispatch_end]
    assert 'transaction_dialog:()=>openPersonnelTransactionDialog()' in dispatch
    assert '/api/desktop/table/personnel?limit=1000' in helper
    assert 'name="transaction_type"' in helper and 'name="amount"' in helper
    assert 'category:"Gider"' in helper and 'type:"Maaş/Prim"' in helper


def test_sms_settings_manifest_entry_routes_to_the_existing_twilio_settings():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'sms_settings_dialog:()=>{settingsSection="sms-settings";navigate("settings")}' in dispatch
    for key in ("twilio_account_sid", "twilio_auth_token", "twilio_from_number"):
        assert f'exactSettingsField(["{key}"' in app
    assert 'data-twilio-sms-test' in app


def test_customer_select_manifest_entry_uses_searchable_picker_and_customer_details():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'customer_select_dialog:()=>customerSelect(customer360,' in dispatch
    assert 'customerPickerRows()' in app
    assert 'id="customerPickerSearch"' in app
    assert 'data-customer-picker-history' in app


def test_photo_gallery_manifest_dispatch_uses_the_photo_api_and_controls():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function renderTrackingPhotoGallery(")
    end = app.index("function openManifestDialog(", start)
    gallery = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert "photo_gallery_dialog:()=>photoGalleryDialog()" in dispatch
    assert "/api/desktop/external-tracking/photos?${query}" in gallery
    assert '_action:"delete"' in gallery
    assert "devicePhotoFiles" in gallery
    assert "data-device-photo-prev" in gallery and "data-device-photo-next" in gallery
    assert r'stage:stage||"\u0130\u015flem"' in gallery
    assert "function photoGalleryDialog()" in gallery


def test_vehicle_history_qr_manifest_entry_selects_a_maintenance_card():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function vehicleHistoryQrDialog(")
    end = app.index("function openManifestDialog(", start)
    picker = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'vehicle_history_qr_dialog:()=>vehicleHistoryQrDialog()' in dispatch
    assert 'apiFetch("/api/desktop/vehicle-maintenance/cards?q=")' in picker
    assert 'name="card_id"' in picker
    assert 'maintenanceHistoryDialog(row)' in picker
    assert 'history-qr/' in app


def test_device_history_manifest_entry_filters_prior_serial_records():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openDeviceHistoryDialog(")
    end = app.index("function openManifestDialog(", start)
    workflow = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'device_history_dialog:()=>openDeviceHistoryDialog()' in dispatch
    assert 'db.serviceDevices||[]' in workflow
    assert 'item.serial_no||""' in workflow
    assert 'String(item.tracking_no||"")!==current' in workflow
    for column in ("Takip No", "Tarih", r"M\u00fc\u015fteri", r"Ar\u0131za", "Durum"):
        assert f"<th>{column}</th>" in workflow
    assert '#27ae60' in workflow and '#c0392b' in workflow and '#e67e22' in workflow


def test_customer_import_manifest_entry_previews_and_persists_mapped_fields():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("const customerImportFields=")
    end = app.index("function openDeviceHistoryDialog(", start)
    workflow = app[start:end]
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    assert 'customer_import_dialog:()=>openCustomerImportDialog()' in dispatch
    assert 'id="customerImportOpen"' in app
    assert '/api/desktop/customers/import/preview' in workflow
    assert '/api/desktop/table/customers' in workflow
    for field in ("name", "phone", "email", "company_name", "address", "tax_no", "city", "type", "notes"):
        assert f'"{field}"' in workflow
    assert 'await hydrateDesktop(true)' in workflow
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert 'path == "/api/desktop/customers/import/preview"' in backend
    assert 'CUSTOMER_IMPORT_LIMIT = 12 * 1024 * 1024' in backend


def test_global_search_manifest_entry_opens_the_existing_search_palette():
    root = Path(__file__).resolve().parents[1]
    app = (root / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    search = (root / "Web_Arayuzu" / "web" / "global-search-reference.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert "global_search_dialog:()=>window.ayecOpenGlobalSearch?.()" in dispatch
    assert "window.ayecOpenGlobalSearch=openPalette" in search
    assert "palette.showModal()" in search


def test_vehicle_maintenance_items_manifest_entry_opens_editable_card_items():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openVehicleMaintenanceItemsManifestDialog()")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    item_start = app.index("function openMaintenanceItemsDialog(")
    item_end = app.index("async function maintenanceDialog(", item_start)
    item_dialog = app[item_start:item_end]
    assert "$$('[data-maintenance-item]',dialog).forEach" in item_dialog
    assert "$$('[data-maintenance-item]',dialog).filter" in item_dialog
    assert 'apiFetch("/api/desktop/vehicle-maintenance/cards?q=")' in helper
    assert 'void maintenanceDialog(row).then(()=>setTimeout' in helper
    assert "$$('[data-maintenance-item]',dialog).filter" in item_dialog
    assert "vehicle_maintenance_items_dialog:()=>openVehicleMaintenanceItemsManifestDialog()" in dispatch


def test_automotive_damage_and_checklist_manifest_entries_open_the_intake_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openAutomotiveIntakeSubdialog(kind)")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'if(currentSector!=="otomotiv")' in helper
    assert "serviceDialog()" in helper
    assert '[data-automotive-damage-open]' in helper
    assert '[data-automotive-checklist-open]' in helper
    assert 'automotive_damage_dialog:()=>openAutomotiveIntakeSubdialog("damage")' in dispatch
    assert 'automotive_checklist_dialog:()=>openAutomotiveIntakeSubdialog("checklist")' in dispatch


def test_customer_location_manifest_entry_opens_the_existing_location_editor():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openCustomerLocationManifestDialog()")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert "customerSelect(customer=>" in helper
    assert "customerForm(customer)" in helper
    assert "saveCustomer(form,customer)" in helper
    assert '[data-customer-map-toggle]' in helper
    assert "customer_location_dialog:()=>openCustomerLocationManifestDialog()" in dispatch

def test_location_picker_manifest_entry_opens_the_location_map_dialog():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openLocationPickerManifestDialog()")
    helper = app[start:]
    assert "location_picker_dialog:()=>openLocationPickerManifestDialog()" in app
    assert "field-service/geocode" in helper
    assert "field-service/reverse-geocode" in helper
    assert "map_default_lat" in helper and "installation_lng" in helper
    assert "data-location-search" in helper and "data-location-share" in helper
    assert "setTimeout(()=>void search(),600)" in helper
    assert 'dialog.querySelector("#dialogCancel").textContent="Iptal"' in helper
    assert '"map_default_lat_user_"+username' in helper
    assert '"map_default_city_user_"+username' in helper
    assert '"map_default_district_user_"+username' in helper


def test_partner_finance_manifest_dispatches_to_the_live_partner_finance_workflow():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    app = (root / "app.js").read_text(encoding="utf-8")
    partners = (root / "partners-reference.js").read_text(encoding="utf-8")
    assert "partner_finance_dialog:()=>window.ayecOpenPartnerFinanceDialog?.()" in app
    assert "window.ayecOpenPartnerFinanceDialog = async function (partnerId)" in partners
    assert "await loadPartnerWorkspace(partnerId || selectedPartnerId)" in partners
    assert "return openPartnerFinanceDialog()" in partners


def test_partner_shipment_manifest_dispatches_to_the_live_shipment_workflow():
    root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    app = (root / "app.js").read_text(encoding="utf-8")
    partners = (root / "partners-reference.js").read_text(encoding="utf-8")
    assert "partner_shipment_dialog:()=>window.ayecOpenPartnerShipmentDialog?.()" in app
    assert "window.ayecOpenPartnerShipmentDialog = async function (partnerId)" in partners
    assert "await loadPartnerWorkspace(partnerId || selectedPartnerId)" in partners
    assert "return openShipmentDialog()" in partners


def test_project_transaction_manifest_dispatch_opens_income_or_expense_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openProjectTransactionManifestDialog()")
    helper = app[start:]
    assert "project_transaction_dialog:()=>openProjectTransactionManifestDialog()" in app
    assert 'navigate("projects")' in helper
    assert "p9ProjectState.loaded" in helper and "p9CurrentProject()" in helper
    assert 'data-project-transaction-type="Gelir"' in helper
    assert 'data-project-transaction-type="Gider"' in helper
    assert "openProjectTransactionDialog(project,type)" in helper


def test_project_unit_sale_manifest_dispatches_to_sale_ready_units():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openProjectUnitSaleManifestDialog()")
    helper = app[start:]
    assert "project_unit_sale_dialog:()=>openProjectUnitSaleManifestDialog()" in app
    assert "p9ProjectState.loaded" in helper and "p9CurrentProject()" in helper
    assert "p9ProjectState.units" in helper and '"satildi","sold"' in helper
    assert "p9OpenProjectUnitSale(unitId)" in helper


def test_license_request_manifest_entry_opens_the_central_license_workflow():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'license_lock_screen:()=>{settingsSection="license";navigate("settings")}' in app


def test_brand_edit_manifest_entry_opens_the_existing_brand_editor():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openBrandEditManifestDialog()")
    end = app.index("function customerSelect(", start)
    workflow = app[start:end]
    assert 'brand_edit_dialog:()=>openBrandEditManifestDialog()' in workflow
    assert 'navigate("brands")' in workflow
    assert 'document.querySelector("[data-generic-add]")?.click()' in workflow
    assert 'brands:{group:"Ticari",title:"Cihaz Bilgisi & Markalar",table:"device_brands"' in app


def test_customer_vehicle_manifest_entry_opens_the_existing_vehicle_editor():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    automotive = (ROOT / "Web_Arayuzu" / "web" / "automotive-parity.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    assert "customer_vehicle_dialog:()=>window.openAutomotiveVehicleShortcut?.()" in dispatch
    assert "window.openAutomotiveVehicleShortcut=function()" in automotive
    assert "/api/desktop/table/customer_vehicles" in automotive
    for field in ("plate", "brand", "model", "year", "vehicle_type", "engine_type", "fuel_type", "last_known_odometer", "notes"):
        assert f"name=\"{field}\"" in automotive


def test_offer_acceptance_manifest_entry_uses_the_transactional_workflow():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    assert "offer_acceptance_dialog:()=>openOfferAcceptanceManifestDialog()" in dispatch
    assert "function openOfferAcceptanceDialog(offer)" in app
    assert 'apiFetch("/api/desktop/offers/"+Number(offer.id)+"/accept"' in app
    assert "c360-accept-offer" in app and "offerAcceptanceRemaining" in app
    assert r"Teklifi Kabul Et ve Hesaba \u0130\u015fle" in app


def test_processed_offers_expose_the_revision_reversal_workflow():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert "function openOfferRevisionDialog(offer)" in app
    assert '"/api/desktop/offers/"+Number(offer.id)+"/reverse"' in app
    assert 'button.dataset.offerReverse=String(offer.id)' in app
    assert "!offerIsProcessed(offer)" in app
    assert 'maxlength="4000" required' in app


def test_legacy_license_keygen_opens_central_license_management():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert "license_keygen_dialog:()=>openLicenseKeygenManifestDialog()" in app
    assert r'function openLicenseKeygenManifestDialog(){openDialog("HWID Lisans Anahtar\u0131","MERKEZ\u0130 L\u0130SANS AKI\u015eI"' in app
    assert r"Web s\u00fcr\u00fcm\u00fc ba\u011f\u0131ms\u0131z HWID anahtar\u0131 olu\u015fturmaz." in app
    assert 'settingsSection="license";navigate("settings");return true' in app


def test_bank_card_manifest_entry_uses_account_scoped_editor_and_actions():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    start = app.index("async function ayecFetchAllDesktopTableRows(")
    end = app.index("const ayecRenderBeforeBankReference=render;", start)
    workflow = app[start:end]
    assert "bank_detail_dialog_components:()=>openBankCardManifestDialog()" in dispatch
    assert 'ayecFetchAllDesktopTableRows("bank_cards")' in workflow
    assert 'apiFetch("/api/desktop/table/bank_cards",{method:"POST"' in workflow
    for field in ("card_name", "card_last4", "card_limit", "current_debt", "due_day", "statement_day", "is_active"):
        assert f'name="{field}"' in workflow
    assert 'data-bank-card-edit' in workflow and 'data-bank-card-delete' in workflow
    assert 'Number(card.bank_account_id)===Number(account.id)' in workflow


def test_scheduled_alert_manifest_and_bank_detail_use_edit_workflow():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    start = app.index("function openScheduledAlertDialog(")
    end = app.index("const ayecRenderBeforeBankReference=render;", start)
    workflow = app[start:end]
    assert "alert_edit_dialog:()=>openScheduledAlertManifestDialog()" in dispatch
    assert 'apiFetch("/api/desktop/table/scheduled_alerts?limit=500")' in workflow
    assert 'apiFetch("/api/desktop/table/scheduled_alerts",{method:"POST"' in workflow
    assert 'trigger_time:triggerTime,is_enabled:form.has("is_enabled")?1:0' in workflow
    assert 'Yakla\\u015fan Otomatik \\u00d6demeler ve Bildirimler' in workflow
    assert 'data-alert-edit' in workflow and 'returnToAccount' in workflow


def test_loan_detail_manifest_entry_renders_overview_plan_and_attachment_tabs():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openLoanDetailManifestDialog()"):app.index("function openManifestDialog(")]
    assert "loan_detail_dialog:()=>openLoanDetailManifestDialog()" in dispatch
    assert 'apiFetch("/api/desktop/table/loans?limit=1000")' in workflow
    assert 'apiFetch("/api/desktop/table/loan_installments?limit=1000")' in workflow
    assert 'apiFetch("/api/desktop/loans/"+encodeURIComponent(loan.id)+"/attachments")' in workflow
    for tab in ("overview", "plan", "docs"):
        assert f'data-loan-detail-tab="{tab}"' in workflow
    assert "data-loan-detail-content" in workflow
    assert "Kredi Detaylar\\u0131" in workflow


def test_advanced_loan_wizard_manifest_entry_preserves_full_creation_flow():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openAdvancedLoanWizardManifestDialog()"):app.index("function openManifestDialog(")]
    assert "loan_wizard_advanced:()=>openAdvancedLoanWizardManifestDialog()" in dispatch
    assert 'apiFetch("/api/desktop/banks/catalog")' in workflow
    assert 'apiFetch("/api/desktop/loans/create"' in workflow
    for field in ("bank_index", "loan_type", "loan_title", "principal", "interest_rate", "interest_period", "term_months", "start_date", "kkdf_rate", "bsmv_rate", "notes"):
        assert f'name="{field}"' in workflow or f'form.get("{field}")' in workflow
    assert "data-loan-file" in workflow and "data-loan-file-remove" in workflow
    assert "data-loan-file" in workflow and "data-loan-file-remove" in workflow and "loan-document-preview" in workflow
    assert 'zone.ondrop=event=>' in workflow and 'URL.createObjectURL(file)' in workflow
    assert 'preview_url,...file' in workflow and 'currency=String(data.currency||"TRY")' in workflow
    assert 'PDF veya G\\u00f6rsel s\\u00fcr\\u00fckle b\\u0131rak' in workflow
    assert "data-loan-wizard-back" in workflow
    assert "interestTotal" in workflow and "taxTotal" in workflow
    assert "loan_wizard_dialog:()=>openAdvancedLoanWizardManifestDialog()" in dispatch


def test_early_closure_manifest_entry_routes_to_loan_selection_and_calculator():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    payment = app[app.index("function openLoanInstallmentsDialog("):app.index("function openLoanDetailManifestDialog(")]
    assert "early_closure_dialog:()=>openBulkLoanPaymentWorkflow()" in dispatch
    assert "function openLoanEarlyClosureDialog(loan,unpaid,payRows)" in app
    assert "openLoanEarlyClosureDialog(loan,unpaid,payRows)" in payment
    assert "Erken Kapat" in payment


def test_einvoice_integration_manifest_entry_opens_existing_settings_dialog():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("async function openInvoiceIntegrationDialog()"):app.index("function openManifestDialog(")]
    assert "einvoice_integration_dialog:()=>openInvoiceIntegrationDialog()" in dispatch
    assert 'apiFetch("/api/desktop/einvoice/settings")' in workflow
    assert 'id="einvoiceTestButton"' in workflow
    assert 'name="api_key" type="password"' in workflow


def test_personnel_edit_manifest_entry_routes_to_existing_employee_editor():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    personnel = app[app.index("let ayecPersonnelSelectedId"):]
    assert 'personnel_edit_dialog:()=>navigate("personnel")' in dispatch
    assert 'data-personnel-edit' in personnel


def test_vehicle_maintenance_photo_gallery_manifest_entry_selects_a_tenant_card():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openVehicleMaintenancePhotoGalleryManifestDialog()"):app.index("async function maintenancePhotoGallery(row)")]
    assert "vehicle_maintenance_photo_gallery_dialog:()=>openVehicleMaintenancePhotoGalleryManifestDialog()" in dispatch
    assert 'apiFetch("/api/desktop/vehicle-maintenance/cards?q=")' in workflow
    assert "maintenancePhotoGallery(rows[0])" in workflow


def test_fiscal_rollover_manifest_entry_uses_protected_accounting_controls():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("async function ayecOpenFiscalControls()"):app.index("async function ayecOpenFiscalArchivePicker()")]
    assert "fiscal_rollover_wizard:()=>ayecOpenFiscalControls()" in dispatch
    assert 'apiFetch("/api/desktop/fiscal/rollover-plan")' in workflow
    assert '"#ayecFiscalRollover").disabled=!plan?.can_execute' in workflow
    assert '"#ayecFiscalRollover").onclick=()=>ayecOpenFiscalRollover(plan)' in workflow


def test_device_selection_manifest_opens_searchable_tenant_service_picker():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openDeviceSelectionManifestDialog()"):app.index("function openManifestDialog(")]
    assert "device_selection_dialog:()=>openDeviceSelectionManifestDialog()" in dispatch
    assert "devicePickerSearch" in workflow
    assert "TAKIP NO" in workflow and "GIRIS TARIHI" in workflow
    assert "technicianDialog(customer,service)" in workflow
    assert "service.status" in workflow


def test_technician_dialog_exposes_desktop_wizard_service_fields():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dialog = app[app.index("const deviceTitle=service.device||"):app.index("const collect=$(\"#collectPayment\")")]
    assert 'openDialog(`${service.no} \\xb7 ${deviceTitle}`' in dialog
    assert 'service.device_type,service.device_brand||service.brand,service.device_model||service.model' in dialog
    assert 'name="fault_description"' in dialog
    assert 'name="accessories"' in dialog
    assert 'name="checklist_status"' in dialog
    assert "fault_description:values.fault_description" in dialog
    assert "accessories:values.accessories" in dialog
    assert "checklist_status:values.checklist_status" in dialog
    assert 'id="manualUsedPartAdd"' in app
    assert "payload.manual_used_parts=lines.filter(line=>line.manual).map" in app
    assert "window.ayecUsedPartsDrafts.delete(serviceKey)" in app
    assert "async function bindTechnicianPanelTabs(service,historyUi)" in app
    assert "button.dataset.technicianTab=key" in app
    assert 'apiFetch("/api/desktop/technician/checklist"' in app


def test_unified_documents_dialog_opens_searchable_document_center():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    dialog = app[app.index("async function openUnifiedDocumentsCenterDialog()"):app.index("function openManifestDialog(")]
    assert "unified_documents_center_dialog:()=>openUnifiedDocumentsCenterDialog()" in dispatch
    assert 'apiFetch("/api/desktop/documents/center")' in dialog
    assert "documentsCenterSearch" in dialog and "documentsCenterSource" in dialog
    assert 'window.open(row.url,"_blank","noopener")' in dialog
    assert "row.available" in dialog


def test_partner_documents_dialog_supports_tenant_upload_open_and_delete():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    dialog = app[app.index("async function openPartnerDocumentsDialog()"):app.index("function openManifestDialog(")]
    assert "partner_documents_dialog:()=>openPartnerDocumentsDialog()" in dispatch
    assert 'apiFetch("/api/desktop/partners/documents",{method:"POST"' in dialog
    assert "data_base64:encoded" in dialog and "shipment_id:Number(shipmentId)||null" in dialog
    assert 'action:"delete",partner_id:Number(partnerId),id:Number(selected)' in dialog
    assert 'window.open(row.url,"_blank","noopener")' in dialog


def test_advanced_filter_dialog_applies_service_search_criteria():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    dialog = app[app.index("function openAdvancedServiceFilterDialog()"):app.index("async function openPartnerDocumentsDialog()")]
    services = app[app.index("function renderServiceOperationsBoard()"):app.index("renderServices=function(){return renderServiceOperationsBoard()};")]
    assert "advanced_filter:()=>openAdvancedServiceFilterDialog()" in dispatch
    assert 'data-action="advanced-service-filter"' in services
    assert "name=\"customer\"" in dialog and "name=\"tracking\"" in dialog
    assert "name=\"serial\"" in dialog and "name=\"date_start\"" in dialog
    assert "window.ayecAdvancedServiceFilter=values" in dialog
    assert 'dialog.style.width="min(440px, calc(100vw - 28px))"' in dialog
    assert "includes(item.customer,criteria.customer)" in services
    assert "criteria.date_start" in services and "criteria.date_end" in services


def test_partner_profile_dialog_saves_all_desktop_profile_fields():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    dialog = app[app.index("async function openPartnerProfileDialog()"):app.index("function openManifestDialog(")]
    assert "partner_profile_dialog:()=>openPartnerProfileDialog()" in dispatch
    assert 'apiFetch("/api/desktop/partners/profile"' in dialog
    for field in ("name", "phone", "email", "type", "city", "service_type", "commission_rate", "contract_type", "sla_level"):
        assert field in dialog
    assert "id:Number(selected)||null" in dialog


def test_sale_payment_dialog_is_wired_to_sales_checkout_payment_step():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openSalePaymentManifestDialog("):app.index("runSales=async function(mode){", app.index("function openSalePaymentManifestDialog("))]
    assert 'sale_payment_dialog:()=>salesCart.length?runSales("payment")' in dispatch
    assert "salePaymentAmount" in workflow and "salePaymentMethod" in workflow
    assert "salePaymentRemaining" in workflow and "payment_note" in workflow
    checkout = app[app.index("runSales=async function(mode){", app.index("function openSalePaymentManifestDialog(")):app.index("quoteDialog=function(){", app.index("function openSalePaymentManifestDialog("))]
    assert "paymentData=await openSalePaymentManifestDialog" in checkout
    assert "payment_amount:paymentData.payment_amount" in checkout


def test_service_print_options_manifest_maps_browser_print_settings():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openServicePrintOptionsManifestDialog()"):app.index("function openManifestDialog(")]
    assert "service_print_options_dialog:()=>openServicePrintOptionsManifestDialog()" in dispatch
    assert all(field in workflow for field in ("servicePrintProfile", "servicePrintPaper", "servicePrintOrientation", "servicePrintWidth", "servicePrintHeight"))
    assert "window.print()" in workflow and "i\\u015fletim sistemi yaz\\u0131c\\u0131s\\u0131 se\\u00e7imi kullan\\u0131lamaz" in workflow


def test_project_transaction_detail_manifest_opens_selected_read_only_record():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function openProjectTransactionDetailManifestDialog()"):app.index("function openProjectTransactionDetailDialog(")]
    assert "transaction_detail_dialog:()=>openProjectTransactionDetailManifestDialog()" in dispatch
    assert "p9ProjectState.transactions" in workflow
    assert "data-project-transaction-detail" in workflow
    assert "openProjectTransactionDetailDialog(transaction)" in workflow


def test_whatsapp_template_manager_manifest_opens_existing_template_crud():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(")]
    workflow = app[app.index("function renderPart9SmsTemplates()"):app.index("function loadPart9SmsTemplateRows(")]
    assert 'template_manager:()=>{settingsSection="sms-templates";navigate("settings")}' in dispatch
    assert "whatsapp_templates" in app
    assert "data-p9-template-edit" in workflow and "data-p9-template-delete" in workflow
    assert "p9SmsTemplateDialog" in app and "/api/desktop/table/whatsapp_templates" in app



def test_report_dialog_selects_a_service_and_opens_the_printable_report():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openServiceReportPicker()")
    end = app.index("function openManifestDialog(", start)
    helper = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert "db.customers.flatMap" in helper
    assert 'id="serviceReportSearch"' in helper
    assert "openServiceReportDialog(selected.customer,selected.service)" in helper
    assert "report_dialog:()=>openServiceReportPicker()" in dispatch
    assert 'id="servicePrintBtn"' in app
    assert 'id="serviceTechBtn"' in app


def test_service_report_migrates_hardware_checks_signature_and_delivery_actions():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openServiceReportDialog(")
    end = app.index("function openServiceReportPicker(", start)
    report = app[start:end]
    assert '/api/desktop/technician/test-catalog?tracking_no=' in report
    assert 'catalog.tests.filter(item=>item.active!==false&&item.active!==0)' in report
    assert '/api/desktop/technician/tests?tracking_no=' in report
    assert 'method:"POST"' in report and '/api/desktop/technician/tests' in report
    assert 'id="serviceReportSignature"' in report
    assert 'id="serviceReportClearSignature"' in report
    assert 'id="serviceReportDeliverButton"' in report
    assert 'collect_payment:deliver' in report
    assert '/api/desktop/service-tracking/qr?tracking_no=' in report
    styles = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")
    assert "service-report-pane[hidden]{display:block!important}" in styles


def test_image_crop_dialog_supports_browser_file_crop_and_result_event():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openImageCropManifestDialog()")
    end = app.index("function openManifestDialog(", start)
    crop = app[start:end]
    dispatch = app[end:app.index("function customerSelect(", end)]
    assert 'accept="image/*"' in crop
    assert 'imageCropCanvas' in crop and 'event.shiftKey' in crop
    assert 'ayec-image-cropped' in crop and 'dataUrl' in crop
    assert 'image_crop_dialog:()=>openImageCropManifestDialog()' in dispatch


def test_label_editor_manifest_uses_filtered_tenant_catalog_and_edit_routes():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openLabelEditorManifestDialog()")
    end = app.index("function openImageCropManifestDialog(", start)
    editor = app[start:end]
    dispatch = app[app.index("function openManifestDialog("):app.index("function customerSelect(", app.index("function openManifestDialog("))]
    assert 'apiFetch("/api/desktop/labels")' in editor
    assert 'id="labelEditorSearch"' in editor and 'id="labelEditorCategory"' in editor
    assert 'method:"POST"' in editor and 'action:"reset"' in editor
    assert '<button type="button" class="secondary mini" data-label-save>' in editor
    assert 'label_editor_dialog:()=>openLabelEditorManifestDialog()' in dispatch


def test_bulk_password_manifest_opens_the_existing_admin_workflow():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    reference = (ROOT / "Web_Arayuzu" / "web" / "user-management-reference.js").read_text(encoding="utf-8")
    assert 'bulk_password_dialog:async()=>{settingsSection="users";navigate("settings");await loadSettingsUsers();window.ayecBulkPasswordsDialog?.()}' in dispatch
    assert 'apiFetch("/api/desktop/users/bulk-passwords"' in reference
    assert 'data-bulk-password-confirm' in reference
    assert 'eligible=ayecSettingsUsers.filter' in reference


def test_app_lock_manifest_uses_the_authenticated_web_lock_dialog():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openAppLockDialog()")
    end = app.index("const startApplicationWithoutAppLock", start)
    helper = app[start:end]
    dispatch_start = app.index("function openManifestDialog(")
    dispatch_end = app.index("function customerSelect(", dispatch_start)
    assert 'name="password" type="password"' in helper
    assert '/api/desktop/security-settings/verify-app-lock' in helper
    assert 'app_lock_dialog:()=>openAppLockDialog()' in app[dispatch_start:dispatch_end]
    assert 'const unlocked=await openAppLockDialog()' in app[end:]


def test_sector_customer_manifest_dialog_uses_the_existing_profile_form():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openManifestDialog(")
    end = app.index("function customerSelect(", start)
    dispatch = app[start:end]
    assert 'automotive_customer_dialog:()=>openSectorCustomerManifestDialog("otomotiv")' in dispatch
    assert 'technical_service_customer_dialog:()=>openSectorCustomerManifestDialog("teknik_servis")' in dispatch
    assert 'function openSectorCustomerManifestDialog(sector)' in app
    assert 'function customerSectorFields(c={})' in app
    assert '${customerSectorFields(c)}' in app
    assert 'sector_extension:Object.fromEntries((currentSector==="otomotiv"?' in app
    assert 'technician_login_dialog:()=>openTechnicianLoginManifestDialog()' in dispatch
    assert 'modern_manual_product_dialog:()=>openTechnicianLoginManifestDialog(true)' in dispatch
    assert 'critical_alert_dialog:()=>openCriticalAlertManifestDialog()' in dispatch
    assert 'user_switch_dialog:()=>openUserSwitchManifestDialog()' in dispatch
    assert 'setTimeout(()=>$("#logoutBtn")?.click(),80)' in app
    assert 'function openCriticalAlertManifestDialog()' in app
    assert 'body.querySelector(".used-parts-editor")' in app
    assert 'function openTechnicianLoginManifestDialog(showManualProduct=false)' in app
    assert 'String(x.id)===String(no)' in app

