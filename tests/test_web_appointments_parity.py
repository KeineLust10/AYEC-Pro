from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_appointment_context_menu_keeps_desktop_separator_before_delete():
    montage = (WEB / "appointment-montage.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")
    start = montage.index("showContext = function (event, kind, id)")
    end = montage.index("async function completeAppointmentStatus", start)
    menu = montage[start:end]

    assert "menu.addSeparator()" in desktop[desktop.index("def handle_card_right_click"):desktop.index("# Navigasyon Metodları")]
    assert menu.index('menu.append(statusMenu)') < menu.index('separator.className = "context-menu-separator"')
    assert menu.index('separator.className = "context-menu-separator"') < menu.index('menu.append(deleteButton)')
    assert "statusTrigger.onclick = function (event)" in menu
    assert "event.stopPropagation();" in menu


def test_appointment_double_click_resolves_numeric_database_ids():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "appointment_color_palette_offscreen.cjs").read_text(encoding="utf-8")

    assert app.count('appointmentDialog(db.appointments.find(x=>String(x.id)===String(row.dataset.id)))') == 2
    assert 'appointmentDialog(db.appointments.find(x=>x.id===row.dataset.id))' not in app
    assert 'card.dispatchEvent(new MouseEvent("dblclick"' in audit
    assert 'page="appointments";document.body.dataset.page=page;render()' in audit
    assert 'idType !== "number" || doubleClick.rowIdType !== "string"' in audit


def test_appointment_calendar_matches_desktop_week_grid_and_slot_actions():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    form = (WEB / "appointment-workflow.js").read_text(encoding="utf-8")

    assert 'Array.from({length:7}' in page
    assert 'Array.from({length:11}' in page
    assert 'data-date="\'+apDate(d)+\'" data-time="\'+hour+\'"' in page
    assert 'appointmentDialog(null,{date:slot.dataset.date,time:slot.dataset.time})' in page
    assert 'e.dataTransfer.setData("text/plain",ayecDraggedAppointmentId)' in page
    assert 'slot.dataset.date;item.time=slot.dataset.time' in page
    assert 'await desktopWrite("appointments",{id:+item.id,_action:"update",date:item.date,time:item.time})' in page
    assert "slot && slot.date ? slot.date : today()" in form
    assert "slot && slot.time ? String(slot.time).slice(0, 2) + ':00'" in form
    assert "function renderAppointments()" in page
    assert "ayecAppointmentView===\"day\"?[new Date()]:weekDays" in page


def test_appointment_technician_filter_and_status_use_the_personnel_directory():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")
    assert 'apiFetch("/api/desktop/table/personnel?limit=1000&include_deleted=1")' in page
    assert 'activePersonnel=namedPersonnel.filter(person=>Number(person.active??1)!==0).sort((a,b)=>String(a.name||"").localeCompare(String(b.name||""),"tr-TR"))' in page
    assert 'totalTechnicianCount=namedPersonnel.length' in page
    assert "activeTechnicianCount+'/'+totalTechnicianCount+' Aktif</b>" in page
    assert 'COALESCE(active, 1)=1' in desktop
    assert 'COUNT(*) FROM personnel WHERE TRIM(COALESCE(name, \'\'))<>' in desktop


def test_appointment_kpis_follow_desktop_completion_and_urgency_fields():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")
    assert 'String(a.status||"").toLocaleLowerCase("tr-TR").startsWith("tamam")' in page
    assert '["acil","kritik"].includes(String(a.urgency||a.priority||"").toLocaleLowerCase("tr-TR"))' in page
    assert "casefold().startswith('tamam')" in desktop
    assert "row_data[8] in ('Acil', 'Kritik')" in desktop


def test_appointment_kpi_cards_match_desktop_values_and_surface():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    style = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")
    metric = page[page.index("const metric="):page.index("return '<section class=\"appointment-ref-page\"", page.index("const metric="))]

    assert metric.count("<article>") == 4
    assert "<span>" not in metric
    assert "for title, value, accent in [" in desktop
    assert "background: var(--surface-2);" in style


def test_appointment_selected_view_uses_desktop_accent_state():
    style = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")
    selected = style[style.index('body[data-page="appointments"] .appointment-ref-views button[aria-selected="true"]'):]
    selected = selected[:selected.index("}")]

    assert "view_buttons[1].setChecked(True)" in desktop
    assert "border-color:var(--accent,#2563eb)" in selected
    assert "background:var(--accent,#2563eb)" in selected
    assert "color:var(--selection-text,#f8fafc)" in selected


def test_appointment_today_empty_state_matches_desktop_copy_and_alignment():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    style = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")

    assert "Bug\\u00fcn i\\u00e7in kay\\u0131tl\\u0131<br>randevu bulunamad\\u0131." in page
    assert 'QLabel("Bug\u00fcn i\u00e7in kay\u0131tl\u0131\\nrandevu bulunamad\u0131.")' in desktop
    assert ".appointment-ref-side-list>p:only-child" in style
    assert "text-align:center" in style


def test_appointment_refresh_preserves_plan_item_locations_for_filtering():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    source = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert '(a.plan_items||[]).map(item=>String(item.source_location_id||""))' in page
    assert 'if table == "appointments":' in source
    appointment_route = source[source.index('if table == "appointments":', source.index('if path.startswith("/api/desktop/table/")')):]
    appointment_route = appointment_route[:appointment_route.index('if table == "settings":')]
    assert 'FROM appointment_plan_items WHERE appointment_id IN (' in appointment_route
    assert 'item["plan_items"] = plan_by_appointment.get(int(item.get("id") or 0), [])' in appointment_route


def test_appointment_form_carries_desktop_fields_and_workflow_side_effects():
    form = (WEB / "appointment-workflow.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")

    for field in ("personnel", "device", "notes", "color", "workflow", "offerId"):
        assert 'name="' + field + '"' in form
    assert "personnel_name: values.personnel" in form
    assert "description: description" in form
    assert "color: values.color" in form
    assert "offer_no: quote ? (quote.no || quote.offer_no || '') : ''" in form
    assert "apiFetch('/api/desktop/appointments/bootstrap'" in form
    assert "action: 'prepare', appointment_id: Number(saved.id)" in form
    assert "window.openAppointmentMontagePreparation(Number(saved.id))" in form
    assert "db.personnel=source.personnel||[]" in app
    assert "technician:item.personnel_name||\"\"" in app


def test_appointment_color_palette_matches_desktop_swatch_count_and_size():
    form = (WEB / "appointment-workflow.js").read_text(encoding="utf-8")
    style = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "appointments_page.py").read_text(encoding="utf-8")

    assert 'colors = [tc("accent"), tc("danger"), tc("success"), tc("warning"), tc("accent"), tc("warning")]' in desktop
    assert 'style.getPropertyValue("--warn").trim() || "#f59e0b",\n      style.getPropertyValue("--brand").trim() || "#3b82f6",\n      style.getPropertyValue("--warn").trim() || "#f59e0b"' in form
    assert ".appointment-color-choice{width:36px;height:36px;min-width:36px;min-height:36px" in style
    assert ".appointment-color-palette{display:flex;align-items:center;gap:10px" in style


def test_appointment_hour_and_canceled_edit_follow_desktop_rules():
    form = (WEB / "appointment-workflow.js").read_text(encoding="utf-8")

    assert 'type="time" step="3600"' in form
    assert "String(item.time).slice(0, 2) + ':00'" in form
    assert "selectedStatus === '\\u0130ptal' ? 'Bekliyor' : selectedStatus" in form
    assert "desktopLabels.indexOf(parts[0]) >= 0" in form


def test_appointment_customer_combo_supports_desktop_style_text_search():
    form = (WEB / "appointment-workflow.js").read_text(encoding="utf-8")

    assert 'name="customerSearch" list="appointmentCustomers"' in form
    assert 'name="customerId" hidden' in form
    assert "customerSearch.oninput" in form
    assert "customer.dispatchEvent(new Event('change'" in form


def test_appointment_page_toolbar_refresh_and_calendar_cards_match_desktop():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    style = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'textContent="Randevu Merkezi & Takvim"' in page
    assert 'data-appointment-refresh' in page
    assert 'apiFetch("/api/desktop/table/appointments?limit=1000")' in page
    assert 'appointment-ref-calendar-event' in page
    assert 'grid-template-rows:34px 34px' in style
    assert 'grid-template-columns:minmax(0,1fr) 280px' in style
    assert 'grid-auto-rows:minmax(112px,auto)' in style


def test_appointment_side_panel_exposes_desktop_outcome_and_edit_actions():
    page = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    montage = (WEB / "appointment-montage.js").read_text(encoding="utf-8")

    assert "function apSideEvent(a)" in page
    assert ".map(apSideEvent).join(\"\")" in page
    for action in ("Gidildi", "Gidilmedi", "complete", "cancel", "edit"):
        assert '"' + action + '"' in page
    assert 'window.setAppointmentStatus = setAppointmentStatus' in montage
    assert 'contextAction("appointment",id,action)' in page


def test_appointment_context_status_commits_before_updating_local_state():
    montage = (WEB / "appointment-montage.js").read_text(encoding="utf-8")
    start = montage.index("async function setAppointmentStatus(id, status)")
    end = montage.index("async function deleteAppointment", start)
    update = montage[start:end]

    assert 'await desktopWrite("appointments", { id: +appointment.id, _action: "update", status: status })' in update
    assert update.index("await desktopWrite(") < update.index("appointment.status = status")
    assert "catch (error)" in update and '"error"' in update


def test_appointment_completion_persists_timestamp_and_preserves_installment_payment_reference():
    montage = (WEB / "appointment-montage.js").read_text(encoding="utf-8")

    assert "async function completeAppointmentStatus(id)" in montage
    combined_update = 'status: "Tamamland\\u0131", completed_at: completedAt'
    assert combined_update in montage
    completion = montage[montage.index("async function completeAppointmentStatus(id)"):montage.index("function openAppointmentPayment(id)")]
    assert completion.index("await desktopWrite(") < completion.index('appointment.status = "Tamamland\\u0131"')
    assert "function openAppointmentPayment(id)" in montage
    assert "Montaj tamamland\\u0131 | Teklif: " in montage
    assert "description.value = reference" in montage
    assert 'if (!customer) {\n      toast("\\u00d6deme i\\u00e7in randevuya ba\\u011fl\\u0131 bir m\\u00fc\\u015fteri se\\u00e7ilmelidir.", "warning");\n      return;\n    }' in montage


def test_service_status_print_action_offers_desktop_document_types():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    choices = app[app.index("function ayecStatusPrintChoices"):app.index("const ayecStatusRenderBeforeSmsAction")]

    for kind in ("short", "detailed", "cargo", "label-a", "label-b", "form"):
        assert '"' + kind + '"' in choices
    assert "function ayecStatusPrintPreview(row, kind)" in choices
    assert "window.print()" in choices
    assert "kind === \"short\" ? fields.slice(0, 8)" in choices
    assert "kind === \"cargo\"" in choices and "fields.filter(([label])" in choices
    assert 'openGenericDialog(genericModules["service-status"], row, data.columns)' not in choices

    detail = app[app.index("async function ayecOpenStatusServiceDetail"):app.index('document.addEventListener("click", event => {', app.index("async function ayecOpenStatusServiceDetail"))]
    assert "serviceDetailDialog(customer, service)" in detail
    assert 'apiFetch("/api/desktop/table/used_parts?limit=1000")' in detail
    technician = app[app.index("function technicianDialog(c,s)"):app.index("\n", app.index("function technicianDialog(c,s)"))]
    assert "Number.isInteger(+s.id)?+s.id:" in technician
    assert '"Haz\\u0131r"' in app
