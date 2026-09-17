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
      return '<option value="' + esc(quote.id) + '"' + selected + '>' + esc(quote.no || ("#" + quote.id)) + '</option>';
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

  appointmentDialog = function (item) {
    var selectedWorkflow = item && item.appointment_type === 'installation' ? 'installation' : 'service';
    var selectedCustomer = item && item.customerId ? item.customerId : '';
    var selectedOffer = item && (item.offer_id || item.offerId) ? (item.offer_id || item.offerId) : '';
    var title = item && item.title ? item.title : '';
    openDialog(
      item ? 'Randevuyu D\u00fczenle' : 'Yeni Randevu',
      'PLANLAMA',
      '<div class="form-grid">'
        + '<div class="field full"><label>\u0130\u015flem yolu *</label><select name="workflow"><option value="service"' + (selectedWorkflow === 'service' ? ' selected' : '') + '>Ar\u0131za ke\u015ffi / servis onar\u0131m</option><option value="installation"' + (selectedWorkflow === 'installation' ? ' selected' : '') + '>Verilen teklif / montaj</option></select></div>'
        + '<div class="field full"><label>M\u00fc\u015fteri *</label><select name="customerId" required><option value="">Se\u00e7in</option>' + db.customers.map(function (customer) { return '<option value="' + esc(customer.id) + '"' + (String(selectedCustomer) === String(customer.id) ? ' selected' : '') + '>' + esc(customer.name) + '</option>'; }).join('') + '</select></div>'
        + '<div class="field full appointment-offer-field"><label>Verilen teklif *</label><select name="offerId"><option value="">\u00d6nce teklif se\u00e7in</option>' + renderOfferChoices(selectedCustomer, selectedOffer) + '</select></div>'
        + '<div class="field full"><div id="appointmentOfferPreview" class="dialog-placeholder"></div></div>'
        + '<div class="field"><label>Tarih *</label><input name="date" type="date" required value="' + esc(item && item.date ? item.date : today()) + '"></div>'
        + '<div class="field"><label>Saat *</label><input name="time" type="time" required value="' + esc(item && item.time ? item.time : '09:00') + '"></div>'
        + '<div class="field full"><label>Konu *</label><input name="title" required value="' + esc(title) + '"></div>'
        + '<div class="field"><label>Durum</label><select name="status">' + ['Planlan\u0131', 'Onayland\u0131', 'Tamamland\u0131', '\u0130ptal'].map(function (status) { return '<option' + ((item && item.status === status) ? ' selected' : '') + '>' + status + '</option>'; }).join('') + '</select></div>'
        + '</div>',
      async function (formData) {
        var values = Object.fromEntries(formData);
        var customer = db.customers.find(function (entry) { return String(entry.id) === String(values.customerId); });
        if (!customer) throw Error('M\u00fc\u015fteri se\u00e7in');
        if (values.workflow === 'installation' && !values.offerId) throw Error('Montaj i\u00e7in verilen teklif se\u00e7in');
        var quote = quoteFor(values.offerId);
        var description = values.title + (quote ? ' | ' + (quote.no || ('#' + quote.id)) : '');
        var payload = {
          customer_id: Number.isInteger(+customer.id) ? +customer.id : null,
          customer_name: customer.name,
          customer: customer.name,
          date: values.date,
          time: values.time,
          description: description,
          status: values.status,
          source_type: 'web',
          appointment_type: values.workflow,
          offer_id: Number.isInteger(+values.offerId) ? +values.offerId : null,
        };
        if (item && Number.isInteger(+item.id)) {
          payload.id = +item.id;
          payload._action = 'update';
        }
        await apiFetch('/api/desktop/table/appointments', { method: 'POST', body: JSON.stringify(payload) });
        await hydrateDesktop(true);
        toast(values.workflow === 'installation' ? 'Montaj randevusu ve y\u00fckleme kontrol\u00fc planland\u0131' : 'Servis randevusu planland\u0131', 'success');
        return true;
      },
      item ? 'G\u00fcncelle' : 'Randevu Ekle'
    );
    var workflow = document.querySelector('#dialogBody [name="workflow"]');
    var customer = document.querySelector('#dialogBody [name="customerId"]');
    var offer = document.querySelector('#dialogBody [name="offerId"]');
    if (workflow) workflow.onchange = drawAppointmentOfferPreview;
    if (customer) customer.onchange = drawAppointmentOfferPreview;
    if (offer) offer.onchange = drawAppointmentOfferPreview;
    drawAppointmentOfferPreview();
  };
}());
