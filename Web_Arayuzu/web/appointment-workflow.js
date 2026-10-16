/* Shared appointment workflow for the web surface. ASCII-only source. */
(function () {
  function quoteFor(id) {
    return (db.quotes || []).find(function (quote) { return String(quote.id) === String(id); });
  }

  function quoteItems(quote) {
    return Array.isArray(quote && quote.items) ? quote.items : [];
  }

  function renderOfferChoices(customerId, selectedId) {
    return (db.quotes || []).filter(function (quote) {
      return !customerId || String(quote.customerId) === String(customerId);
    }).map(function (quote) {
      var selected = String(quote.id) === String(selectedId) ? " selected" : "";
      return '<option value="' + esc(quote.id) + '"' + selected + '>' + esc(quote.no || quote.offer_no || ("#" + quote.id)) + '</option>';
    }).join("");
  }

  function descriptionParts(item) {
    var raw = String(item && item.description || "");
    var parts = raw.split(" - ");
    var desktopLabels = ["Ar\u0131za Ke\u015ffi / Servis Onar\u0131m", "Verilen Teklif / Montaj"];
    if (parts.length >= 3 && desktopLabels.indexOf(parts[0]) >= 0) {
      return { device: parts[1], notes: parts.slice(2).join(" - ") };
    }
    return { device: "", notes: raw };
  }

  function colorChoices(selected) {
    var style = getComputedStyle(document.documentElement);
    var palette = [
      style.getPropertyValue("--brand").trim() || "#3b82f6",
      style.getPropertyValue("--danger").trim() || "#f43f5e",
      style.getPropertyValue("--success").trim() || "#10b981",
      style.getPropertyValue("--warn").trim() || "#f59e0b"
    ];
    if (selected && palette.indexOf(selected) < 0) palette.unshift(selected);
    return palette.map(function (color, index) {
      var active = String(selected || palette[0]).toLowerCase() === color.toLowerCase();
      return '<button type="button" class="appointment-color-choice' + (active ? ' selected' : '') + '" data-appointment-color="' + esc(color) + '" aria-label="Renk etiketi ' + (index + 1) + '" aria-pressed="' + active + '" style="background:' + esc(color) + '"></button>';
    }).join("");
  }

  function drawAppointmentOfferPreview() {
    var workflow = document.querySelector('#dialogBody [name="workflow"]');
    var customer = document.querySelector('#dialogBody [name="customerId"]');
    var offer = document.querySelector('#dialogBody [name="offerId"]');
    var offerField = document.querySelector('#dialogBody .appointment-offer-field');
    var preview = document.querySelector('#appointmentOfferPreview');
    if (!workflow || !customer || !offer || !offerField || !preview) return;
    var isInstallation = workflow.value === 'installation';
    offerField.hidden = !isInstallation;
    offer.required = isInstallation;
    var previous = offer.value;
    offer.innerHTML = '<option value="">\u00d6nce teklif se\u00e7in</option>' + renderOfferChoices(customer.value, previous);
    if (!isInstallation) {
      preview.innerHTML = '<span class="muted">\u0130nceleme / onar\u0131m randevusu i\u00e7in serbest planlama kullan\u0131l\u0131r.</span>';
      return;
    }
    var quote = quoteFor(offer.value);
    var items = quoteItems(quote);
    preview.innerHTML = items.length
      ? '<strong>\u00d6n y\u00fckleme kontrol\u00fc</strong><ul>' + items.slice(0, 8).map(function (item) {
          return '<li>' + esc(item.name || item.description || item.service || 'Kalem') + ' x ' + esc(item.qty || item.quantity || 1) + '</li>';
        }).join('') + '</ul>'
      : '<span class="muted">Bu teklif i\u00e7in aktar\u0131lacak malzeme veya hizmet kalemi yok.</span>';
  }

  appointmentDialog = function (item, slot) {
    var selectedWorkflow = item && (item.appointment_type === 'installation' || item.workflow === 'teklif_montaj') ? 'installation' : 'service';
    var selectedCustomer = item && item.customerId ? item.customerId : '';
    var selectedCustomerRecord = db.customers.find(function (customer) { return String(customer.id) === String(selectedCustomer); });
    var selectedOffer = item && (item.offer_id || item.offerId) ? (item.offer_id || item.offerId) : '';
    var parts = descriptionParts(item);
    var selectedPersonnel = item && (item.personnel_name || item.technician || item.technician_name) || '';
    var selectedColor = item && item.color || getComputedStyle(document.documentElement).getPropertyValue('--brand').trim() || '#3b82f6';
    var selectedStatus = item && item.status || 'Bekliyor';
    var hour = item && item.time ? String(item.time).slice(0, 2) + ':00' : (slot && slot.time ? String(slot.time).slice(0, 2) + ':00' : '09:00');
    openDialog(
      item ? 'Randevuyu D\u00fczenle' : 'Yeni Randevu',
      'PLANLAMA',
      '<div class="form-grid">'
        + '<div class="field full"><label>\u0130\u015flem yolu *</label><select name="workflow"><option value="service"' + (selectedWorkflow === 'service' ? ' selected' : '') + '>Ar\u0131za ke\u015ffi / servis onar\u0131m</option><option value="installation"' + (selectedWorkflow === 'installation' ? ' selected' : '') + '>Verilen teklif / montaj</option></select></div>'
        + '<div class="field full"><label>M\u00fc\u015fteri *</label><input name="customerSearch" list="appointmentCustomers" autocomplete="off" required value="' + esc(selectedCustomerRecord ? selectedCustomerRecord.name : (item && item.customer_name || '')) + '" placeholder="M\u00fc\u015fteri ad\u0131n\u0131 yaz\u0131n"><datalist id="appointmentCustomers">' + db.customers.map(function (customer) { return '<option value="' + esc(customer.name) + '"></option>'; }).join('') + '</datalist><select name="customerId" hidden><option value="">Se\u00e7in</option>' + db.customers.map(function (customer) { return '<option value="' + esc(customer.id) + '"' + (String(selectedCustomer) === String(customer.id) ? ' selected' : '') + '>' + esc(customer.name) + '</option>'; }).join('') + '</select></div>'
        + '<div class="field full"><label>Atanan Personel</label><select name="personnel"><option value="">Se\u00e7ilmedi</option>' + (db.personnel || []).map(function (person) { var name = typeof person === 'string' ? person : person.name; return name ? '<option value="' + esc(name) + '"' + (String(selectedPersonnel) === String(name) ? ' selected' : '') + '>' + esc(name) + '</option>' : ''; }).join('') + '</select></div>'
        + '<div class="field full appointment-offer-field"><label>Verilen teklif *</label><select name="offerId"><option value="">\u00d6nce teklif se\u00e7in</option>' + renderOfferChoices(selectedCustomer, selectedOffer) + '</select></div>'
        + '<div class="field full"><div id="appointmentOfferPreview" class="dialog-placeholder"></div></div>'
        + '<div class="field"><label>Tarih *</label><input name="date" type="date" required value="' + esc(item && item.date ? item.date : (slot && slot.date ? slot.date : today())) + '"></div>'
        + '<div class="field"><label>Saat *</label><input name="time" type="time" step="3600" required value="' + esc(hour) + '"></div>'
        + '<div class="field full"><label>Cihaz Marka / Model</label><input name="device" value="' + esc(parts.device) + '"></div>'
        + '<div class="field full"><label>Renk Etiketi</label><div class="appointment-color-palette" role="group" aria-label="Renk Etiketi">' + colorChoices(selectedColor) + '</div><input type="hidden" name="color" value="' + esc(selectedColor) + '"></div>'
        + '<div class="field full"><label>Notlar</label><textarea name="notes" rows="3" placeholder="Randevu i\u00e7in k\u0131sa not veya \u00f6zel talimat...">' + esc(parts.notes) + '</textarea></div>'
        + '</div>',
      async function (formData) {
        var values = Object.fromEntries(formData);
        var customer = db.customers.find(function (entry) { return String(entry.id) === String(values.customerId); });
        if (!customer) throw Error('M\u00fc\u015fteri se\u00e7in');
        if (values.workflow === 'installation' && !values.offerId) throw Error('Montaj i\u00e7in verilen teklif se\u00e7in');
        var quote = quoteFor(values.offerId);
        var workflowLabel = values.workflow === 'installation' ? 'Verilen Teklif / Montaj' : 'Ar\u0131za Ke\u015ffi / Servis Onar\u0131m';
        var description = workflowLabel + ' - ' + values.device + ' - ' + values.notes;
        var status = selectedStatus === '\u0130ptal' ? 'Bekliyor' : selectedStatus;
        var payload = {
          customer_id: Number.isInteger(+customer.id) ? +customer.id : null,
          customer_name: customer.name,
          customer: customer.name,
          date: values.date,
          time: values.time,
          description: description,
          status: status,
          personnel_name: values.personnel,
          color: values.color,
          workflow: values.workflow === 'installation' ? 'teklif_montaj' : 'kesif_onarim',
          appointment_type: values.workflow,
          offer_id: Number.isInteger(+values.offerId) ? +values.offerId : null,
          offer_no: quote ? (quote.no || quote.offer_no || '') : '',
        };
        if (item && Number.isInteger(+item.id)) {
          payload.id = +item.id;
          payload._action = 'update';
        }
        await apiFetch('/api/desktop/appointments/bootstrap', { method: 'POST', body: '{}' });
        var saved = await apiFetch('/api/desktop/table/appointments', { method: 'POST', body: JSON.stringify(payload) });
        if (values.workflow === 'installation' && saved && saved.id) {
          await apiFetch('/api/desktop/appointments/montage-plan', {
            method: 'POST',
            body: JSON.stringify({ action: 'prepare', appointment_id: Number(saved.id) })
          });
        }
        await hydrateDesktop(true);
        if (values.workflow === 'installation' && saved && saved.id) {
          window.setTimeout(function () {
            if (window.openAppointmentMontagePreparation) window.openAppointmentMontagePreparation(Number(saved.id));
          }, 0);
        }
        toast(values.workflow === 'installation' ? 'Montaj randevusu ve y\u00fckleme kontrol\u00fc planland\u0131' : 'Servis randevusu planland\u0131', 'success');
        return true;
      },
      item ? 'G\u00fcncelle' : 'Randevu Ekle'
    );
    var workflow = document.querySelector('#dialogBody [name="workflow"]');
    var customer = document.querySelector('#dialogBody [name="customerId"]');
    var customerSearch = document.querySelector('#dialogBody [name="customerSearch"]');
    var offer = document.querySelector('#dialogBody [name="offerId"]');
    var color = document.querySelector('#dialogBody [name="color"]');
    if (workflow) workflow.onchange = drawAppointmentOfferPreview;
    if (customerSearch && customer) customerSearch.oninput = function () {
      var match = db.customers.find(function (entry) { return String(entry.name || '').trim().toLocaleLowerCase() === customerSearch.value.trim().toLocaleLowerCase(); });
      customer.value = match ? String(match.id) : '';
      customer.dispatchEvent(new Event('change', { bubbles: true }));
    };
    if (customer) customer.onchange = drawAppointmentOfferPreview;
    if (offer) offer.onchange = drawAppointmentOfferPreview;
    document.querySelectorAll('#dialogBody [data-appointment-color]').forEach(function (button) {
      button.onclick = function () {
        if (color) color.value = button.dataset.appointmentColor;
        document.querySelectorAll('#dialogBody [data-appointment-color]').forEach(function (choice) {
          var active = choice === button;
          choice.classList.toggle('selected', active);
          choice.setAttribute('aria-pressed', String(active));
        });
      };
    });
    drawAppointmentOfferPreview();
  };
}());
