(function () {
  "use strict";

  let partnerRows = [];
  let shipmentRows = [];
  let partnerTimelineRows = [];
  let partnerTrendRows = [];
  let selectedPartnerId = null;
  let selectedTab = "active";
  let partnerQuery = "";
  let serviceFilter = "";
  let commissionFilter = "all";

  function partnerLocalDateInputValue(date = new Date()) { return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, "0"), String(date.getDate()).padStart(2, "0")].join("-"); }

  const completedStatuses = new Set([
    "geri geldi",
    "musteriye teslim edildi",
    "tamamlandi",
    "teslim edildi",
  ]);

  function isCompletedPartnerShipment(row) {
    const status = String(row.status || "").trim().toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll("\u0131", "i");
    return completedStatuses.has(status);
  }

  function filteredPartners() {
    const query = partnerQuery.trim().toLocaleLowerCase("tr-TR");
    return partnerRows.filter((partner) => {
      const searchable = [partner.name, partner.city, partner.phone, partner.email, partner.service_type]
        .map((value) => String(value || "").toLocaleLowerCase("tr-TR"))
        .join(" ");
      const serviceMatches = !serviceFilter || String(partner.service_type || "") === serviceFilter;
      const commission = Number(partner.commission_rate || 0) > 0;
      const commissionMatches = commissionFilter === "all"
        || (commissionFilter === "commissioned" && commission)
        || (commissionFilter === "no-commission" && !commission);
      return searchable.includes(query) && serviceMatches && commissionMatches;
    });
  }

  function partnerListMarkup() {
    const partners = filteredPartners();
    return partners.length ? partners.map((partner) => {
      const selected = String(partner.id) === String(selectedPartnerId);
      const name = String(partner.name || "Partner");
      const initials = name.split(/\s+/).slice(0, 2).map((part) => part[0] || "").join("").toLocaleUpperCase("tr-TR") || "PT";
      return `<button type="button" class="partner-web-list-row${selected ? " selected" : ""}" data-partner-id="${esc(partner.id)}">
        <span class="partner-web-avatar">${esc(initials)}</span><span><strong>${esc(name)}</strong><small>${esc(partner.service_type || "Genel")} · ${esc(partner.city || "\u015eehir yok")}</small></span>
      </button>`;
    }).join("") : '<p class="partner-web-empty">Partner bulunamad\u0131.</p>';
  }

  function shipmentTableMarkup(rows) {
    if (!rows.length) return '<p class="partner-web-empty">Bu g\u00f6r\u00fcn\u00fcmde sevkiyat kayd\u0131 yok.</p>';
    return `<div class="table-wrap"><table class="partner-web-table"><thead><tr><th>Emanet No</th><th>M\u00fc\u015fteri</th><th>\u00dcr\u00fcn</th><th>Tarih</th><th>Durum</th><th>Kargo / Servis No</th></tr></thead><tbody>${rows.map((row) => {
      const cargo = [row.outbound_tracking_no, row.return_tracking_no, row.external_ref_no].filter(Boolean).join(" / ");
      return `<tr data-partner-shipment="${esc(row.id)}" tabindex="0" title="D\u00fczenlemek i\u00e7in \u00e7ift t\u0131klay\u0131n"><td>${esc(row.serial_no || row.external_ref_no || "-")}</td><td>${esc(row.customer_name || "-")}</td><td>${esc(row.product_name || "-")}</td><td>${esc(String(row.sent_at || row.created_at || "").slice(0, 10) || "-")}</td><td>${esc(row.status || "-")}</td><td>${esc(cargo || "-")}</td></tr>`;
    }).join("")}</tbody></table></div>`;
  }

  function shipmentFormMarkup(row = {}, partner) {
    const today = partnerLocalDateInputValue();
    const currencyCode = String(db.settings.currency || "TRY").toUpperCase();
    const currencySymbol = currencyCode === "USD" ? "$" : currencyCode === "EUR" ? "\u20ac" : "\u20ba";
    const text = (name, label, fallback = "", readOnly = false) => `<div class="field"><label>${label}</label><input name="${name}" ${name === "customer_name" || name === "product_name" ? "required" : ""} ${readOnly ? "readonly" : ""} value="${esc(row[name] ?? fallback)}"></div>`;
    const amount = (name, label) => `<div class="field"><label>${label}</label><span class="partner-shipment-amount"><input name="${name}" type="number" min="0" max="10000000" step="0.01" value="${esc(row[name] ?? 0)}"><span aria-hidden="true">${currencySymbol}</span></span></div>`;
    const area = (name, label, fallback = "") => `<div class="field full"><label>${label}</label><textarea name="${name}" rows="2">${esc(row[name] ?? fallback)}</textarea></div>`;
    return `<div class="partner-web-form"><div class="field full"><label>Calisma Ortagi</label><input value="${esc(partner.name || "")}" readonly></div>
      ${text("customer_name", "Musteri *")} ${text("product_name", "Urun *")} ${text("serial_no", "Seri No")}
      ${area("issue_summary", "Ariza / Konu")} ${area("shipment_reason", "Gonderim Nedeni")}
      ${text("external_ref_no", "Partner Ref / Servis No")} ${text("status", "Durum", "Hazirlaniyor")}
      ${text("outbound_tracking_no", "Gidis Kargo")} ${text("return_tracking_no", "Donus Kargo")}
      ${amount("partner_cost", "Partner Maliyeti")} ${amount("customer_price", "Musteriye Yansitilan")}
      ${text("quote_status", "Teklif Durumu", "Beklemede")} ${amount("quote_amount", "Teklif Tutari")}
      ${text("approval_status", "Onay Durumu", "Onay Bekliyor")}
      <div class="field"><label>Gonderim Tarihi</label><input name="sent_at" type="date" value="${esc(row.sent_at || today)}"></div>
      ${text("contract_type", "Sozlesme", partner.contract_type || "Standart Anlasma", true)} ${text("sla_level", "SLA", partner.sla_level || "24 Saat Donus", true)}
      ${area("accessories", "Aksesuarlar / Paket")} ${text("cost_responsibility", "Maliyet Sorumlulugu", "Partner")}
      ${text("return_qc", "Donus Kalite Kontrol", "Beklemede")} ${text("cosmetic_status", "Kozmetik Durum", "Kontrol Edilmedi")}
      ${text("missing_parts", "Eksik Parca", "Yok")}
      <div class="field"><label>Donus Tarihi</label><input name="returned_at" type="date" value="${esc(row.returned_at || today)}"></div>
      ${area("notes", "Notlar")}</div>`;
  }

  function openShipmentDialog(row = {}) {
    const partner = partnerRows.find((item) => String(item.id) === String(selectedPartnerId));
    if (!partner) return toast("Once bir partner secin.", "warning");
    const editing = Boolean(row.id);
    openDialog(editing ? "Partner Gonderi Kaydi Duzenle" : "Partner Gonderi Kaydi", "PARTNER SEVKIYATI", shipmentFormMarkup(row, partner), async (form) => {
      const payload = Object.fromEntries(form.entries());
      payload.partner_id = partner.id;
      if (editing) payload.id = row.id;
      ["partner_cost", "customer_price", "quote_amount"].forEach((key) => { payload[key] = Number(payload[key] || 0); });
      const result = await apiFetch("/api/desktop/partners/shipments", { method: "POST", body: JSON.stringify(payload) });
      await loadPartnerWorkspace(partner.id);
      toast(editing ? "Partner gonderi kaydi guncellendi." : "Partner gonderi kaydi kaydedildi.");
      return result.ok;
    }, editing ? "Guncelle" : "Kaydet ve Kapat");
    const footer = document.querySelector("#dialogFooter");
    const documentsButton = document.createElement("button");
    documentsButton.type = "button";
    documentsButton.className = "secondary";
    documentsButton.id = "partnerShipmentDocumentsButton";
    documentsButton.textContent = "Belgeler";
    documentsButton.onclick = () => openPartnerDocuments(row).catch(error => toast(error.message || "Belgeler yuklenemedi.", "error"));
    footer?.insertBefore(documentsButton, document.querySelector("#dialogCancel"));
    const photoButton = document.createElement("button");
    photoButton.type = "button";
    photoButton.className = "secondary";
    photoButton.id = "partnerShipmentPhotoButton";
    photoButton.textContent = "Foto\u011fraf Galerisi";
    photoButton.onclick = () => openPartnerShipmentPhotoGallery(partner, row, document.querySelector("#dialogForm"));
    footer?.insertBefore(photoButton, document.querySelector("#dialogCancel"));
  }

  window.ayecOpenPartnerShipmentDialog = async function (partnerId) {
    if (page !== "partners") navigate("partners");
    await loadPartnerWorkspace(partnerId || selectedPartnerId);
    return openShipmentDialog();
  };

  async function openPartnerShipmentPhotoGallery(partner, row, form) {
    const identity = {
      partner_id: partner.id,
      shipment_id: row.id || "",
      serial_no: form?.elements.serial_no?.value || row.serial_no || "",
      product_name: form?.elements.product_name?.value || row.product_name || "",
    };
    const query = new URLSearchParams(identity).toString();
    const dialog = document.createElement("dialog");
    dialog.className = "partner-photo-dialog";
    dialog.innerHTML = `<header><div><h2>Foto\u011fraf Galerisi</h2><p>Cihaz Foto\u011fraflar\u0131 (#${esc(identity.serial_no || identity.product_name || "shipment")})</p></div><button type="button" class="secondary" data-partner-photo-add>Foto\u011fraf Ekle</button><input type="file" accept="image/jpeg,image/png,image/bmp" multiple hidden></header><div class="partner-photo-stage"><img alt="Partner g\u00f6nderi foto\u011fraf\u0131" hidden><p data-partner-photo-empty>Bu kay\u0131t i\u00e7in foto\u011fraf bulunamad\u0131.</p></div><footer><button type="button" class="secondary" data-partner-photo-prev>Onceki</button><span data-partner-photo-counter>0 / 0</span><button type="button" class="secondary" data-partner-photo-next>Sonraki</button><button type="button" class="primary" data-partner-photo-close>Kaydet ve Kapat</button></footer>`;
    document.body.append(dialog);
    dialog.addEventListener("close", () => dialog.remove(), { once: true });
    dialog.showModal();
    const image = dialog.querySelector("img");
    const emptyState = dialog.querySelector("[data-partner-photo-empty]");
    const counter = dialog.querySelector("[data-partner-photo-counter]");
    let photos = [];
    let index = 0;
    const draw = () => {
      const photo = photos[index];
      if (photo?.available) {
        image.src = `/api/desktop/partners/shipment-photo/${photo.id}?${query}`;
        image.hidden = false;
        emptyState.hidden = true;
        counter.textContent = `${index + 1} / ${photos.length}`;
      } else {
        image.removeAttribute("src");
        image.hidden = true;
        emptyState.hidden = false;
        counter.textContent = `0 / ${photos.length}`;
      }
    };
    const load = async () => {
      const data = await apiFetch(`/api/desktop/partners/shipment-photos?${query}`);
      photos = Array.isArray(data.rows) ? data.rows : [];
      index = Math.min(index, Math.max(photos.length - 1, 0));
      draw();
    };
    dialog.querySelector("[data-partner-photo-add]").onclick = () => dialog.querySelector('input[type="file"]').click();
    dialog.querySelector('input[type="file"]').onchange = async event => {
      for (const file of Array.from(event.target.files || [])) {
        if (file.size > 8 * 1024 * 1024) { toast("Foto\u011fraf boyutu 8 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.", "error"); continue; }
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
        try {
          await apiFetch("/api/desktop/partners/shipment-photos", { method: "POST", body: JSON.stringify({ ...identity, data: btoa(binary), label: file.name }) });
          photos.push({ id: "pending", available: false });
        } catch (error) { toast(error.message || "Foto\u011fraf eklenemedi.", "error"); }
      }
      event.target.value = "";
      index = Math.max(photos.length - 1, 0);
      try { await load(); } catch (error) { toast(error.message || "Foto\u011fraflar y\u00fcklenemedi.", "error"); }
    };
    dialog.querySelector("[data-partner-photo-prev]").onclick = () => { if (photos.length) { index = (index - 1 + photos.length) % photos.length; draw(); } };
    dialog.querySelector("[data-partner-photo-next]").onclick = () => { if (photos.length) { index = (index + 1) % photos.length; draw(); } };
    dialog.querySelector("[data-partner-photo-close]").onclick = () => dialog.close();
    try { await load(); } catch (error) { toast(error.message || "Foto\u011fraflar y\u00fcklenemedi.", "error"); }
  }

  async function openPartnerDocuments(shipment = null) {
    const partner = partnerRows.find((item) => String(item.id) === String(selectedPartnerId));
    if (!partner) return toast("Once bir partner secin.", "warning");
    const shipmentId = shipment?.id || "";
    let documents = [];
    let selectedId = null;
    const query = new URLSearchParams({ partner_id: partner.id });
    if (shipmentId) query.set("shipment_id", shipmentId);
    const load = async () => {
      const result = await apiFetch(`/api/desktop/partners/documents?${query}`);
      documents = Array.isArray(result.documents) ? result.documents : [];
      if (!documents.some((item) => String(item.id) === String(selectedId))) selectedId = null;
      draw();
    };
    const draw = () => {
      const host = document.querySelector("#partnerDocumentHost");
      if (!host) return;
      host.innerHTML = documents.length
        ? `<div class="table-wrap"><table class="partner-web-document-table"><thead><tr><th>Baslik</th><th>Kategori</th><th>Eklenme</th><th>Durum</th><th></th></tr></thead><tbody>${documents.map((item) => `<tr data-partner-document-id="${esc(item.id)}" class="${String(item.id) === String(selectedId) ? "selected" : ""}"><td>${esc(item.title)}</td><td>${esc(item.category || "-")}</td><td>${esc(item.added_at || "-")}</td><td>${item.available ? "Web erisimi var" : "Yerel dosya erisimi yok"}</td><td><button type="button" class="secondary" data-partner-document-delete="${esc(item.id)}">Sil</button></td></tr>`).join("")}</tbody></table></div>`
        : '<p class="partner-web-empty">Bu sevkiyat icin belge bulunamadi.</p>';
    };
    const body = `<section class="partner-web-documents"><p>${shipmentId ? "Sevkiyata ait belgeleri yonetin." : "Partner belgelerini yonetin."} ${esc(partner.name || "")}</p><input id="partnerDocumentFile" type="file" hidden><button type="button" class="secondary" id="partnerDocumentUpload">Belge Ekle</button><div id="partnerDocumentHost" aria-live="polite"><p class="partner-web-empty">Yukleniyor...</p></div></section>`;
    openDialog("Partner Belgeleri", "DOSYALAR / BELGELER", body, async () => {
      const selected = documents.find((item) => String(item.id) === String(selectedId));
      if (!selected) { toast("Acma icin bir belge secin.", "warning"); return false; }
      if (!selected.available || !selected.url) { toast("Bu dosyanin web erisimi yok.", "warning"); return false; }
      const anchor = document.createElement("a");
      anchor.href = selected.url;
      anchor.download = selected.title || "partner-document";
      anchor.rel = "noopener";
      anchor.click();
      return false;
    }, "Ac");
    const host = document.querySelector("#partnerDocumentHost");
    if (host) host.onclick = async (event) => {
      const remove = event.target.closest("[data-partner-document-delete]");
      if (remove) {
        const documentId = remove.dataset.partnerDocumentDelete;
        try {
          await apiFetch("/api/desktop/partners/documents", { method: "POST", body: JSON.stringify({ action: "delete", partner_id: partner.id, id: documentId }) });
          toast("Belge kaydi silindi.");
          await load();
        } catch (error) { toast(error.message || "Belge silinemedi.", "error"); }
        return;
      }
      const row = event.target.closest("[data-partner-document-id]");
      if (row) { selectedId = row.dataset.partnerDocumentId; draw(); }
    };
    const fileInput = document.querySelector("#partnerDocumentFile");
    const uploadButton = document.querySelector("#partnerDocumentUpload");
    if (uploadButton && fileInput) uploadButton.onclick = () => fileInput.click();
    if (fileInput) fileInput.onchange = async () => {
      const file = fileInput.files?.[0];
      fileInput.value = "";
      if (!file) return;
      if (file.size <= 0 || file.size > 25 * 1024 * 1024) return toast("Dosya bos veya 25 MB sinirini asiyor.", "error");
      try {
        const encoded = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onerror = () => reject(new Error("Dosya okunamadi."));
          reader.onload = () => resolve(String(reader.result || "").split(",")[1] || "");
          reader.readAsDataURL(file);
        });
        await apiFetch("/api/desktop/partners/documents", { method: "POST", body: JSON.stringify({ action: "upload", partner_id: partner.id, shipment_id: shipmentId || null, filename: file.name, data_base64: encoded }) });
        toast("Belge eklendi.");
        await load();
      } catch (error) { toast(error.message || "Belge eklenemedi.", "error"); }
    };
    await load();
  }

  function partnerFinanceMoney(value, data) {
    const code = data.currency || "TRY";
    const precision = Math.min(3, Math.max(0, Number(data.precision ?? 2)));
    const symbol = code === "USD" ? "$" : code === "EUR" ? "\u20ac" : "\u20ba";
    return `${new Intl.NumberFormat("tr-TR", { minimumFractionDigits: precision, maximumFractionDigits: precision }).format(Number(value) || 0)} ${symbol}`;
  }

  function drawPartnerFinanceContent(data) {
    const summary = document.querySelector("#partnerFinanceSummary");
    const entries = document.querySelector("#partnerFinanceEntries");
    const reconciliation = document.querySelector("#partnerFinanceReconciliation");
    if (summary) {
      const values = data.summary || {};
      summary.innerHTML = `<div class="partner-web-finance-stats"><article><small>Toplam Partner Borcu</small><strong>${partnerFinanceMoney(values.total_cost, data)}</strong></article><article><small>Yapilan Odeme</small><strong>${partnerFinanceMoney(values.total_paid, data)}</strong></article><article><small>Kalan Borc</small><strong>${partnerFinanceMoney(values.balance, data)}</strong></article></div><p class="partner-web-finance-note">Musteriye yansitilan toplam: ${partnerFinanceMoney(values.customer_total, data)} | Kalan partner borcu: ${partnerFinanceMoney(values.balance, data)}</p>`;
    }
    if (entries) {
      const rows = data.entries || [];
      entries.innerHTML = `<div class="table-wrap"><table class="partner-web-table"><thead><tr><th>Tarih</th><th>Tip</th><th>Aciklama</th><th>Yontem</th><th>Fatura No</th><th>Fatura Tarihi</th><th>Tutar</th></tr></thead><tbody>${rows.length ? rows.map((item) => `<tr><td>${esc(item.entry_date || "-")}</td><td>${esc(item.entry_type || "-")}</td><td>${esc(item.description || "-")}</td><td>${esc(item.payment_method || "-")}</td><td>${esc(item.invoice_no || "-")}</td><td>${esc(item.invoice_date || "-")}</td><td>${esc(partnerFinanceMoney(item.display_amount, data))}</td></tr>`).join("") : '<tr><td colspan="7" class="partner-web-empty">Finans hareketi bulunamadi.</td></tr>'}</tbody></table></div>`;
    }
    if (reconciliation) {
      const rows = data.reconciliation || [];
      reconciliation.innerHTML = `<div class="table-wrap"><table class="partner-web-table"><thead><tr><th>Sevk</th><th>Urun</th><th>Partner Maliyeti</th><th>Eslesen Odeme</th><th>Kalan</th><th>Son Fatura</th></tr></thead><tbody>${rows.length ? rows.map((item) => `<tr><td>#${esc(item.shipment_id)}</td><td>${esc(item.product_name || "-")}</td><td>${esc(partnerFinanceMoney(item.cost, data))}</td><td>${esc(partnerFinanceMoney(item.paid, data))}</td><td>${esc(partnerFinanceMoney(item.remaining, data))}</td><td>${esc(item.invoice_no || "-")}</td></tr>`).join("") : '<tr><td colspan="6" class="partner-web-empty">Sevkiyat eslestirmesi bulunamadi.</td></tr>'}</tbody></table></div>`;
    }
  }

  async function openPartnerFinanceDialog() {
    const partner = partnerRows.find((item) => String(item.id) === String(selectedPartnerId));
    if (!partner) return toast("Once bir partner secin.", "warning");
    const data = await apiFetch(`/api/desktop/partners/finance?partner_id=${encodeURIComponent(partner.id)}`);
    const today = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    const body = `<section class="partner-web-finance"><h3>${esc(partner.name || "Partner")}</h3><p id="partnerFinanceSummary"></p><h4>Finans Hareketleri</h4><div id="partnerFinanceEntries"></div><h4>Sevkiyat Mutabakati</h4><div id="partnerFinanceReconciliation"></div><div class="partner-web-finance-form"><div class="field"><label>Odeme Tarihi</label><input type="date" name="entry_date" value="${today}"></div><div class="field"><label>Odeme Tutari</label><input type="number" name="amount" min="0.01" max="10000000" step="0.01" value="0"></div><div class="field"><label>Yontem</label><input name="payment_method" value="Havale / EFT"></div><div class="field"><label>Aciklama</label><input name="description" placeholder="Partner odeme aciklamasi"></div><div class="field"><label>Fatura No</label><input name="invoice_no" placeholder="Partner fatura no"></div><div class="field"><label>Fatura Tarihi</label><input type="date" name="invoice_date" value="${today}"></div><div class="field full"><label>Sevk Eslestirme</label><select name="shipment_id"><option value="">Genel Partner Odemesi</option>${(data.shipments || []).map((item) => `<option value="${esc(item.id)}">${esc(item.label)}</option>`).join("")}</select></div><div class="field full"><button type="button" class="primary" id="partnerFinanceSave">Partner Odemesi Kaydet</button></div></div></section>`;
    openDialog("Partner Finans Hareketleri", "PARTNER FINANS", body, async () => true, "Kapat");
    drawPartnerFinanceContent(data);
    const save = document.querySelector("#partnerFinanceSave");
    if (!save) return;
    save.onclick = async () => {
      const form = document.querySelector("#dialogForm");
      const values = Object.fromEntries(new FormData(form).entries());
      values.amount = Number(values.amount || 0);
      if (!(values.amount > 0)) return toast("Gecerli bir odeme tutari girin.", "error");
      values.partner_id = partner.id;
      values.shipment_id = values.shipment_id || null;
      save.disabled = true;
      try {
        await apiFetch("/api/desktop/partners/finance", { method: "POST", body: JSON.stringify(values) });
        toast("Partner odemesi kaydedildi.");
        const updated = await apiFetch(`/api/desktop/partners/finance?partner_id=${encodeURIComponent(partner.id)}`);
        drawPartnerFinanceContent(updated);
        form.elements.amount.value = "0";
        form.elements.description.value = "";
        form.elements.invoice_no.value = "";
      } catch (error) { toast(error.message || "Partner odemesi kaydedilemedi.", "error"); }
      finally { save.disabled = false; }
    };
  }

  window.ayecOpenPartnerFinanceDialog = async function (partnerId) {
    if (page !== "partners") navigate("partners");
    await loadPartnerWorkspace(partnerId || selectedPartnerId);
    return openPartnerFinanceDialog();
  };

  function showPartnerShipmentMenu(event, row) {
    if (typeof ayecContextMenuEnabled === "function" && !ayecContextMenuEnabled("partners")) return;
    const menu = document.querySelector("#contextMenu");
    if (!menu) return;
    event.preventDefault();
    event.stopPropagation();
    menu.dataset.partnerShipmentId = String(row.id);
    menu.dataset.partnerMenu = "1";
    const items = [["Ac / Duzenle", "edit"], ["Belgeler", "shipment-documents"], ["Belge Merkezi", "documents"], ["Partner Finans", "finance"], ["", "separator"], ["Excel Disa Aktar", "export"]];
    menu.innerHTML = items.map(([label, action]) => action === "separator"
      ? '<hr class="context-menu-separator">'
      : `<button type="button" role="menuitem" data-partner-shipment-action="${action}">${label}</button>`).join("");
    menu.style.left = `${Math.max(8, Math.min(event.clientX, innerWidth - 220))}px`;
    menu.style.top = `${Math.max(8, Math.min(event.clientY, innerHeight - items.length * 28 - 12))}px`;
    menu.classList.add("open");
  }

  function exportPartnerShipments() {
    const rows = shipmentRows.map((row) => ({
      "Emanet No": row.serial_no || row.external_ref_no || "",
      "Musteri": row.customer_name || "", "Urun": row.product_name || "",
      "Tarih": row.sent_at || row.created_at || "", "Durum": row.status || "",
      "Gidis": row.outbound_tracking_no || "", "Donus": row.return_tracking_no || "",
      "Servis No": row.external_ref_no || "",
    }));
    download("partner_sevkleri.csv", csv(rows));
  }

  function partnerAnalyticsTable(kind) {
    if (kind === "timeline") {
      const body = partnerTimelineRows.length ? partnerTimelineRows.map((row) => `<tr><td>${esc(row.event_date || "-")}</td><td>${esc(row.event_type || "-")}</td><td>${esc(row.detail || "-")}</td><td>${esc(row.shipment_id || "-")}</td></tr>`).join("") : '<tr><td colspan="4" class="partner-web-empty">Zaman cizelgesi kaydi bulunamadi.</td></tr>';
      return `<div class="table-wrap"><table class="partner-web-table"><thead><tr><th>Tarih</th><th>Tip</th><th>Detay</th><th>Sevk</th></tr></thead><tbody>${body}</tbody></table></div>`;
    }
    const body = partnerTrendRows.length ? partnerTrendRows.map((row) => `<tr><td>${esc(row.period || "-")}</td><td>${esc(row.shipment_count || 0)}</td><td>${esc(row.completed_count || 0)}</td><td>${esc(row.partner_cost || 0)}</td><td>${esc(row.customer_price || 0)}</td><td>${esc(row.quote_amount || 0)}</td></tr>`).join("") : '<tr><td colspan="6" class="partner-web-empty">Trend kaydi bulunamadi.</td></tr>';
    return `<div class="table-wrap"><table class="partner-web-table"><thead><tr><th>Donem</th><th>Sevk</th><th>Tamamlanan</th><th>Partner Maliyeti</th><th>Musteriye Yansiyan</th><th>Teklif</th></tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function cleanPartnerNoteHtml(source) {
    const parsed = new DOMParser().parseFromString(String(source || ""), "text/html");
    const allowed = new Set(["P", "DIV", "BR", "B", "STRONG", "I", "EM", "U", "UL", "OL", "LI", "PRE", "CODE", "BLOCKQUOTE", "A", "SPAN", "IMG"]);
    const discard = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "SVG", "MATH", "VIDEO", "AUDIO"]);
    const clean = (root) => Array.from(root.childNodes).forEach((node) => {
      if (node.nodeType !== Node.ELEMENT_NODE) return;
      if (!allowed.has(node.tagName)) {
        if (discard.has(node.tagName)) node.remove();
        else { clean(node); node.replaceWith(...Array.from(node.childNodes)); }
        return;
      }
      if (node.tagName === "IMG") {
        const source = String(node.getAttribute("src") || "");
        const alt = String(node.getAttribute("alt") || "").slice(0, 240);
        if (source.length > 15_000_000 || !/^data:image\/(png|jpeg|gif|webp);base64,[a-z0-9+/=]+$/i.test(source)) { node.remove(); return; }
        Array.from(node.attributes).forEach((attribute) => node.removeAttribute(attribute.name));
        node.setAttribute("src", source);
        if (alt) node.setAttribute("alt", alt);
        return;
      }
      const href = node.tagName === "A" ? node.getAttribute("href") : null;
      Array.from(node.attributes).forEach((attribute) => node.removeAttribute(attribute.name));
      if (href && /^(https?:|mailto:)/i.test(href.trim())) { node.setAttribute("href", href.trim()); node.setAttribute("rel", "noopener noreferrer"); }
      clean(node);
    });
    clean(parsed.body);
    return parsed.body.innerHTML;
  }

  async function openPartnerNotesDialog() {
    const partner = partnerRows.find((item) => String(item.id) === String(selectedPartnerId));
    if (!partner) return toast("Once bir partner secin.", "warning");
    const typeValues = ["Genel Not", "WhatsApp Mesaj\u0131", "SMS", "Telefon G\u00f6r\u00fc\u015fmesi", "E-Posta"];
    const types = typeValues;
    let notes = [];
    let selectedId = null;
    let filter = "Tumu";
    const body = `<section class="partner-web-notes"><header class="partner-web-note-head"><strong>${esc(partner.name || "Partner")}</strong><small>ID: #C-${String(partner.id).padStart(4, "0")}</small><span>Musteri etkilesim gecmisi ve dahili partner notlari</span></header><div class="partner-web-note-filter"><div>${[["Tumu", "Tumu"], ["Genel Not", "Genel Not"], ["WhatsApp", "WhatsApp Mesaj\u0131"], ["SMS", "SMS"], ["Telefon", "Telefon G\u00f6r\u00fc\u015fmesi"], ["E-Posta", "E-Posta"], ["Teklif", "PC Teklif"]].map(([label, value]) => `<button type="button" class="secondary" data-partner-note-filter="${esc(value)}">${esc(label)}</button>`).join("")}</div><input class="control" id="partnerNoteSearch" type="search" placeholder="Notlarda ara..." aria-label="Notlarda ara"></div><div class="partner-web-notes-split"><aside class="partner-web-note-history"><header><strong>Kayit Gecmisi</strong><small id="partnerNoteCount">0 Kayit Listelendi</small></header><div id="partnerNoteList"></div></aside><section class="partner-web-note-editor"><label class="field"><span>Not Basligi *</span><input class="control" id="partnerNoteTitle" placeholder="Not basligi"></label><div class="partner-web-note-toolbar">${[["B", "bold", "Bold"], ["I", "italic", "Italik"], ["U", "underline", "Alti cizili"], ["\u2022", "insertUnorderedList", "Madde isaretli liste"], ["&lt;/&gt;", "formatBlock", "Kod"], ["\u25a3", "date", "Tarih ekle"]].map(([label, action, title]) => `<button type="button" class="secondary" data-partner-note-format="${action}" title="${title}">${label}</button>`).join("")}<span id="partnerNoteCharacters">0 karakter</span></div><div id="partnerNoteEditor" class="partner-web-note-content" contenteditable="true" role="textbox" aria-label="Not metni" data-placeholder="Not metnini buraya yaziniz..."></div><div class="partner-web-note-meta"><small id="partnerNoteDate">Yeni not - tarih kayitta otomatik olusturulacak</small><small>UTF-8 Destekli</small></div><div class="partner-web-note-actions"><label>Kategori:<select class="control" id="partnerNoteType">${types.map((type, index) => `<option value="${typeValues[index]}">${type}</option>`).join("")}</select></label><div><button type="button" class="secondary" id="partnerNoteNew">+ Yeni Not</button><button type="button" class="secondary" id="partnerNoteDelete">Sil</button><button type="button" class="primary" id="partnerNoteSave">Kaydet / Guncelle</button></div></div><div class="partner-web-note-confirm" id="partnerNoteConfirm" hidden><span>Bu notu silmek istiyor musunuz?</span><button type="button" class="secondary" id="partnerNoteDeleteCancel">Iptal</button><button type="button" class="danger" id="partnerNoteDeleteConfirm">Sil</button></div></section></div></section>`;
    openDialog("Partner Notlari", "PARTNER NOTLARI", body, async () => true, "Kapat");
    const editor = document.querySelector("#partnerNoteEditor");
    const titleInput = document.querySelector("#partnerNoteTitle");
    const typeInput = document.querySelector("#partnerNoteType");
    const list = document.querySelector("#partnerNoteList");
    const load = async (preferredId = selectedId) => {
      const result = await apiFetch(`/api/desktop/partners/notes?partner_id=${encodeURIComponent(partner.id)}`);
      notes = Array.isArray(result.notes) ? result.notes : [];
      drawList();
      const preferred = notes.find((item) => String(item.id) === String(preferredId)) || (!preferredId ? notes[0] : null);
      if (preferred) selectNote(preferred);
      else if (selectedId && !notes.some((item) => String(item.id) === String(selectedId))) newNote();
    };
    const drawList = () => {
      const query = String(document.querySelector("#partnerNoteSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
      const visible = notes.filter((note) => {
        const matchesType = filter === "Tumu" || (filter === "PC Teklif" ? ["PC Teklif", "Teklif"].includes(note.note_type) : note.note_type === filter);
        const haystack = `${note.title || ""} ${note.note_type || ""} ${note.content || ""}`.replace(/<[^>]*>/g, " ").toLocaleLowerCase("tr-TR");
        return matchesType && (!query || haystack.includes(query));
      });
      const totalButton = document.querySelector('[data-partner-note-filter="Tumu"]');
      if (totalButton) totalButton.textContent = `Tumu ${notes.length}`;
      const count = document.querySelector("#partnerNoteCount");
      if (count) count.textContent = `${visible.length} Kayit Listelendi`;
      if (list) list.innerHTML = visible.length ? visible.map((note) => {
        const plain = new DOMParser().parseFromString(cleanPartnerNoteHtml(note.content), "text/html").body.textContent || "";
        return `<button type="button" class="partner-web-note-card ${String(note.id) === String(selectedId) ? "selected" : ""}" data-partner-note-id="${esc(note.id)}"><strong>${esc(note.title || note.created_at || "Not")}</strong><span>${esc(plain.replace(/\s+/g, " ").slice(0, 78))}</span><small>${esc(note.note_type || "Genel Not")} · ${esc(note.created_at || "")}</small></button>`;
      }).join("") : '<p class="partner-web-empty">Bu partnere ait not yok. Yeni Not ile baslayin.</p>';
    };
    const updateCount = () => { const count = document.querySelector("#partnerNoteCharacters"); if (count && editor) count.textContent = `${editor.innerText.length} karakter`; };
    const selectNote = (note) => {
      selectedId = note.id;
      titleInput.value = note.title || note.created_at || "";
      typeInput.value = typeValues.includes(note.note_type) ? note.note_type : "Genel Not";
      editor.innerHTML = cleanPartnerNoteHtml(note.content);
      document.querySelector("#partnerNoteDate").textContent = `Kayit tarihi: ${note.created_at || "-"}`;
      document.querySelector("#partnerNoteConfirm").hidden = true;
      updateCount();
      drawList();
    };
    const newNote = () => {
      selectedId = null;
      titleInput.value = "";
      typeInput.value = "Genel Not";
      editor.replaceChildren();
      document.querySelector("#partnerNoteDate").textContent = "Yeni not - tarih kayitta otomatik olusturulacak";
      document.querySelector("#partnerNoteConfirm").hidden = true;
      updateCount();
      drawList();
      titleInput.focus();
    };
    list.onclick = (event) => {
      const card = event.target.closest("[data-partner-note-id]");
      const note = notes.find((item) => String(item.id) === card?.dataset.partnerNoteId);
      if (note) selectNote(note);
    };
    document.querySelector("#partnerNoteSearch").oninput = drawList;
    document.querySelectorAll("[data-partner-note-filter]").forEach((button) => { button.onclick = () => { filter = button.dataset.partnerNoteFilter; document.querySelectorAll("[data-partner-note-filter]").forEach((item) => item.classList.toggle("primary", item === button)); drawList(); }; });
    document.querySelectorAll("[data-partner-note-format]").forEach((button) => { button.onclick = () => {
      const action = button.dataset.partnerNoteFormat;
      if (action === "date") document.execCommand("insertText", false, new Date().toISOString().slice(0, 10));
      else if (action === "formatBlock") document.execCommand("formatBlock", false, "pre");
      else document.execCommand(action, false);
      editor.focus(); updateCount();
    }; });
    editor.oninput = updateCount;
    document.querySelector("#partnerNoteNew").onclick = newNote;
    document.querySelector("#partnerNoteSave").onclick = async () => {
      const content = cleanPartnerNoteHtml(editor.innerHTML);
      if (!editor.innerText.trim()) return toast("Not icerigi bos birakilamaz.", "error");
      const button = document.querySelector("#partnerNoteSave");
      button.disabled = true;
      try {
        const result = await apiFetch("/api/desktop/partners/notes", { method: "POST", body: JSON.stringify({ action: "save", partner_id: partner.id, id: selectedId, title: titleInput.value, note_type: typeInput.value, content }) });
        selectedId = result.id;
        toast("Partner notu kaydedildi.");
        await load(selectedId);
      } catch (error) { toast(error.message || "Partner notu kaydedilemedi.", "error"); }
      finally { button.disabled = false; }
    };
    document.querySelector("#partnerNoteDelete").onclick = () => {
      if (!selectedId) return toast("Silmek icin kayitli bir not secin.", "warning");
      document.querySelector("#partnerNoteConfirm").hidden = false;
    };
    document.querySelector("#partnerNoteDeleteCancel").onclick = () => { document.querySelector("#partnerNoteConfirm").hidden = true; };
    document.querySelector("#partnerNoteDeleteConfirm").onclick = async () => {
      try {
        await apiFetch("/api/desktop/partners/notes", { method: "POST", body: JSON.stringify({ action: "delete", partner_id: partner.id, note_id: selectedId }) });
        toast("Partner notu silindi.");
        selectedId = null;
        await load(null);
      } catch (error) { toast(error.message || "Partner notu silinemedi.", "error"); }
    };
    try { await load(null); } catch (error) { toast(error.message || "Partner notlari yuklenemedi.", "error"); }
  }

  function openPartnerProfileDialog(partner = null) {
    const typeOptions = ["Kurumsal", "Bayi", "Tedarikci"];
    const serviceOptions = ["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Satis"];
    const contractOptions = ["Standart Anlasma", "Premium SLA", "Parca Tedarik", "Kurumsal Servis"];
    const slaOptions = ["24 Saat Donus", "Ayni Gun", "48 Saat", "Haftalik Batch"];
    const select = (name, label, values, current) => `<div class="field"><label>${label}</label><select class="control" name="${name}">${values.map((value) => `<option value="${value}" ${current === value ? "selected" : ""}>${value}</option>`).join("")}</select></div>`;
    const body = `<section class="partner-web-profile"><div class="form-grid">${select("type", "Ortak Tipi", typeOptions, partner?.type || "Bayi")}<div class="field"><label>Ortak Adi *</label><input class="control" name="name" required value="${esc(partner?.name || "")}" placeholder="Ortak adi / Unvan"></div><div class="field"><label>Telefon</label><input class="control" name="phone" type="tel" value="${esc(partner?.phone || "")}" placeholder="05xx ..."></div><div class="field"><label>E-Posta</label><input class="control" name="email" type="email" value="${esc(partner?.email || "")}" placeholder="email@example.com"></div><div class="field"><label>Hizmet Turu</label><input class="control" name="service_type" list="partnerServiceOptions" value="${esc(partner?.service_type || "Genel")}"><datalist id="partnerServiceOptions">${serviceOptions.map((value) => `<option value="${value}"></option>`).join("")}</datalist></div><div class="field"><label>Komisyon Orani (%)</label><input class="control" name="commission_rate" type="number" min="0" max="100" step="0.01" value="${Number(partner?.commission_rate || 0)}"></div><div class="field"><label>Sehir</label><input class="control" name="city" value="${esc(partner?.city || "")}" placeholder="Sehir"></div>${select("contract_type", "Sozlesme", contractOptions, partner?.contract_type || "Standart Anlasma")}${select("sla_level", "SLA", slaOptions, partner?.sla_level || "24 Saat Donus")}</div></section>`;
    openDialog(partner ? "Calisma Ortagi Duzenle" : "Yeni Calisma Ortagi", "PARTNER PROFILI", body, async (formData) => {
      const payload = Object.fromEntries(formData.entries());
      payload.commission_rate = Number(payload.commission_rate || 0);
      if (partner) payload.id = partner.id;
      const result = await apiFetch("/api/desktop/partners/profile", { method: "POST", body: JSON.stringify(payload) });
      await loadPartnerWorkspace(result.id);
      toast("Calisma ortagi kaydedildi.");
    }, "Kaydet");
  }

  function partnerScorecard(partner, shipments, activeCount) {
    const sla = Number(String(partner.sla_level || "24").match(/\d+/)?.[0] || 24);
    const serials = [];
    const turnaround = [];
    let onTime = 0;
    let completed = 0;
    let issues = 0;
    for (const row of shipments) {
      const serial = String(row.serial_no || "").trim();
      if (serial) serials.push(serial);
      const missing = String(row.missing_parts || "").trim().toLocaleLowerCase("tr-TR");
      const qc = String(row.return_qc || "").trim().toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
      if (missing && !["yok", "-"].includes(missing)) issues++;
      if (qc && !["gecti", "basarili", "tamam"].includes(qc)) issues++;
      if (row.sent_at && row.returned_at) {
        const sent = Date.parse(`${row.sent_at}T00:00:00Z`);
        const returned = Date.parse(`${row.returned_at}T00:00:00Z`);
        if (Number.isFinite(sent) && Number.isFinite(returned)) {
          const hours = Math.max((returned - sent) / 3600000, 0);
          turnaround.push(hours);
          completed++;
          if (hours <= sla) onTime++;
        }
      }
    }
    const counts = new Map();
    serials.forEach((serial) => counts.set(serial, (counts.get(serial) || 0) + 1));
    const repeats = [...counts.values()].filter((count) => count > 1).length;
    const average = turnaround.length ? Math.round((turnaround.reduce((sum, value) => sum + value, 0) / turnaround.length) * 10) / 10 : 0;
    const onTimeRate = completed ? Math.round((onTime / completed) * 1000) / 10 : 0;
    const comeback = serials.length ? Math.round((repeats / serials.length) * 1000) / 10 : 0;
    return `Donus: ${average}s | SLA: %${onTimeRate} | Tekrar: ${repeats} | Geri: %${comeback} | Kalite: ${issues} | Aktif: ${activeCount}`;
  }

  function showPartnerMoreMenu() {
    const host = document.querySelector("#partnerMoreMenu");
    if (!host) return;
    host.hidden = !host.hidden;
    if (host.hidden) return;
    const close = (event) => {
      if (!host.contains(event.target) && event.target.id !== "partnerMore") {
        host.hidden = true;
        document.removeEventListener("pointerdown", close, true);
      }
    };
    document.addEventListener("pointerdown", close, true);
  }

  function renderPartnerWorkspace() {
    const selected = partnerRows.find((partner) => String(partner.id) === String(selectedPartnerId));
    const active = shipmentRows.filter((row) => !isCompletedPartnerShipment(row));
    const history = shipmentRows.filter(isCompletedPartnerShipment);
    const services = [...new Set(partnerRows.map((partner) => String(partner.service_type || "").trim()).filter(Boolean))].sort();
    const tabs = [{ id: "active", label: "Aktif G\u00f6nderiler" }, { id: "history", label: "Ge\u00e7mi\u015f" }, { id: "notes", label: "Notlar" }, { id: "finance", label: "Finans" }, { id: "documents", label: "Belgeler" }, { id: "timeline", label: "Zaman Cizelgesi" }, { id: "trends", label: "Trendler" }];
    const selectedRows = selectedTab === "history" ? history : active;
    const selectedContent = selectedTab === "timeline" ? partnerAnalyticsTable("timeline") : selectedTab === "trends" ? partnerAnalyticsTable("trends") : selectedTab === "notes" ? '<section class="partner-web-tab-action"><p>Secili partnerin hizli notlari ve etkilesim gecmisi.</p><button type="button" class="primary" id="partnerNotesOpen">Partner Notlarini Ac</button></section>' : selectedTab === "finance" ? '<section class="partner-web-tab-action"><p>Komisyon, tahsilat ve partner bazli finans hareketleri.</p><button type="button" class="primary" id="partnerFinanceOpen">Tahsilat / Finans Islemi</button></section>' : selectedTab === "documents" ? '<section class="partner-web-tab-action"><p>Secili partnerin sozlesme, teklif, fatura ve sevk belgeleri.</p><button type="button" class="primary" id="partnerDocumentsOpen">Belgeleri Ac</button></section>' : shipmentTableMarkup(selectedRows);
    const stats = selected ? `<div class="partner-web-stats"><article><strong>${shipmentRows.length}</strong><small>Toplam Gonderi</small></article><article><strong>${active.length}</strong><small>Surecte</small></article><article><strong>${history.length}</strong><small>Tamamlanan</small></article><article><strong>${esc(String(shipmentRows[0]?.sent_at || shipmentRows[0]?.created_at || "-").slice(0, 10))}</strong><small>Son Gonderim</small></article></div>` : "";
    const scorecard = selected ? partnerScorecard(selected, shipmentRows, active.length) : "";
    const heading = pageHead("\u00c7al\u0131\u015fma Ortaklar\u0131", "Partner kartlar\u0131n\u0131, g\u00f6nderileri ve d\u00f6n\u00fc\u015f s\u00fcrecini izleyin.", '<button type="button" class="primary" id="partnerAdd">+ Yeni Ortak</button>');
    return `${heading}<section class="partner-web-layout"><aside class="card partner-web-sidebar"><div class="partner-web-filters"><input class="control" id="partnerWorkspaceSearch" type="search" value="${esc(partnerQuery)}" placeholder="Ortak ara: ad, \u015fehir, telefon, hizmet..." aria-label="Ortak ara"><select class="control" id="partnerWorkspaceService"><option value="">Hizmet</option>${services.map((service) => `<option value="${esc(service)}" ${service === serviceFilter ? "selected" : ""}>${esc(service)}</option>`).join("")}</select><select class="control" id="partnerWorkspaceCommission"><option value="all" ${commissionFilter === "all" ? "selected" : ""}>T\u00fcm partnerler</option><option value="commissioned" ${commissionFilter === "commissioned" ? "selected" : ""}>Komisyonlu</option><option value="no-commission" ${commissionFilter === "no-commission" ? "selected" : ""}>Komisyonsuz</option></select></div><div class="partner-web-list" id="partnerWorkspaceList">${partnerListMarkup()}</div><small class="partner-web-count">Toplam partner: ${filteredPartners().length}</small></aside><section class="partner-web-main">${selected ? `<header class="card partner-web-hero"><div class="partner-web-hero-copy"><h2>${esc([...(selected.name || "").split(/\s+/).filter(Boolean).slice(0,2).map((part) => part[0]?.toUpperCase() || "")].join("") || "PT")}  ${esc(selected.name || "Partner")}</h2><p>${esc([selected.type || "Partner", selected.service_type || "Genel", selected.city, Number(selected.commission_rate || 0) ? `Komisyon %${Number(selected.commission_rate).toFixed(2)}` : ""].filter(Boolean).join(" | "))}</p><p class="partner-web-scorecard">${esc(scorecard)}</p></div><div class="partner-web-hero-actions"><button type="button" class="primary" id="partnerShipmentAdd">+ Gonderi Kaydi</button><button type="button" class="primary" id="partnerHeroDocuments">Belgeler</button><button type="button" class="primary" id="partnerHeroDocumentCenter">Belge Merkezi</button><button type="button" class="primary" id="partnerProfileEdit">Ortak Bilgilerini Duzenle</button><button type="button" class="primary" id="partnerMore">Daha Fazla</button><div class="partner-web-more-menu" id="partnerMoreMenu" hidden><button type="button" data-partner-more="360">Ortak 360</button><button type="button" data-partner-more="profile">Hizmet &amp; Komisyon</button><button type="button" data-partner-more="notes">Notlar</button><button type="button" data-partner-more="service">Yeni Servis Kaydi</button><button type="button" data-partner-more="finance">Odeme / Tahsilat</button><button type="button" data-partner-more="whatsapp">WhatsApp Mesaj</button></div></div>${stats}</header><section class="card partner-web-shipments"><h3 class="partner-web-shipments-title">Gonderilen Urunler</h3><p class="partner-web-shipments-subtitle">Secili partnerin acik, servis ve gecmis kayitlari.</p><nav class="partner-web-tabs" aria-label="Partner sevkiyatlar\u0131">${tabs.map((tab) => `<button type="button" data-partner-workspace-tab="${tab.id}" class="${selectedTab === tab.id ? "active" : ""}">${tab.label}</button>`).join("")}</nav><div id="partnerWorkspaceShipments">${selectedContent}</div></section>` : '<section class="card partner-web-empty-state"><h2>Partner se\u00e7in</h2><p>Soldaki listeden bir \u00e7al\u0131\u015fma orta\u011f\u0131 se\u00e7erek sevk ve takip ekran\u0131n\u0131 a\u00e7\u0131n.</p></section>'}</section></section>`;
  }

  async function loadPartnerWorkspace(partnerId) {
    const query = partnerId ? `?partner_id=${encodeURIComponent(partnerId)}` : "";
    const data = await apiFetch(`/api/desktop/partners/workspace${query}`);
    partnerRows = Array.isArray(data.partners) ? data.partners : [];
    partnerTimelineRows = Array.isArray(data.timeline) ? data.timeline : [];
    partnerTrendRows = Array.isArray(data.trends) ? data.trends : [];
    if (data.selected_partner) selectedPartnerId = data.selected_partner.id;
    else if (!partnerRows.some((partner) => String(partner.id) === String(selectedPartnerId))) selectedPartnerId = partnerRows[0]?.id ?? null;
    shipmentRows = data.selected_partner ? (data.shipments || []) : [];
    if (!data.selected_partner && selectedPartnerId) return loadPartnerWorkspace(selectedPartnerId);
    renderPartnerWorkspacePage();
  }

  function renderPartnerWorkspacePage() {
    const content = document.querySelector("#content");
    if (!content || page !== "partners") return;
    document.body.dataset.page = page;
    content.innerHTML = renderPartnerWorkspace();
    bindPage();
    const search = document.querySelector("#partnerWorkspaceSearch");
    const service = document.querySelector("#partnerWorkspaceService");
    const commission = document.querySelector("#partnerWorkspaceCommission");
    document.querySelector("#partnerAdd")?.addEventListener("click", () => openPartnerProfileDialog());
    if (search) search.oninput = () => { partnerQuery = search.value; document.querySelector("#partnerWorkspaceList").innerHTML = partnerListMarkup(); document.querySelector(".partner-web-count").textContent = `Toplam partner: ${filteredPartners().length}`; bindPartnerRows(); };
    if (service) service.onchange = () => { serviceFilter = service.value; renderPartnerWorkspacePage(); };
    if (commission) commission.onchange = () => { commissionFilter = commission.value; renderPartnerWorkspacePage(); };
    document.querySelectorAll("[data-partner-workspace-tab]").forEach((button) => {
      button.onclick = () => { selectedTab = button.dataset.partnerWorkspaceTab; renderPartnerWorkspacePage(); };
    });
    const add = document.querySelector("#partnerShipmentAdd");
    if (add) add.onclick = () => openShipmentDialog();
    const selectedPartner = partnerRows.find((item) => String(item.id) === String(selectedPartnerId));
    document.querySelector("#partnerProfileEdit")?.addEventListener("click", () => openPartnerProfileDialog(selectedPartner));
    document.querySelector("#partnerHeroDocuments")?.addEventListener("click", () => openPartnerDocuments().catch((error) => toast(error.message, "error")));
    document.querySelector("#partnerHeroDocumentCenter")?.addEventListener("click", () => {
      if (typeof window.openDesktopDocumentsCenter === "function") window.openDesktopDocumentsCenter().catch((error) => toast(error.message, "error"));
      else toast("Belge merkezi yuklenemedi.", "error");
    });
    document.querySelector("#partnerMore")?.addEventListener("click", showPartnerMoreMenu);
    document.querySelector("#partnerMoreMenu")?.addEventListener("click", (event) => {
      const action = event.target.closest("[data-partner-more]")?.dataset.partnerMore;
      if (!action) return;
      document.querySelector("#partnerMoreMenu").hidden = true;
      if (action === "360" && typeof window.customer360 === "function") window.customer360(selectedPartner);
      else if (action === "profile") openPartnerProfileDialog(selectedPartner);
      else if (action === "notes") openPartnerNotesDialog().catch((error) => toast(error.message, "error"));
      else if (action === "service" && typeof window.serviceDialog === "function") window.serviceDialog(selectedPartner.id);
      else if (action === "finance") openPartnerFinanceDialog().catch((error) => toast(error.message, "error"));
      else if (action === "whatsapp") {
        const phone = String(selectedPartner.phone || "").replace(/\D/g, "");
        if (phone) window.open(`https://wa.me/${phone}`, "_blank", "noopener,noreferrer");
        else toast("Partner telefon numarasi bulunamadi.", "warning");
      }
    });
    document.querySelector("#partnerNotesOpen")?.addEventListener("click", () => openPartnerNotesDialog().catch((error) => toast(error.message, "error")));
    document.querySelector("#partnerFinanceOpen")?.addEventListener("click", () => openPartnerFinanceDialog().catch((error) => toast(error.message, "error")));
    document.querySelector("#partnerDocumentsOpen")?.addEventListener("click", () => openPartnerDocuments().catch((error) => toast(error.message, "error")));
    document.querySelectorAll("[data-partner-shipment]").forEach((row) => {
      const shipment = shipmentRows.find((item) => String(item.id) === row.dataset.partnerShipment) || {};
      const edit = () => openShipmentDialog(shipment);
      row.ondblclick = edit;
      row.onkeydown = (event) => { if (event.key === "Enter") edit(); };
      row.oncontextmenu = (event) => showPartnerShipmentMenu(event, shipment);
    });
    bindPartnerRows();
  }

  document.addEventListener("click", (event) => {
    const menu = document.querySelector("#contextMenu");
    if (!menu?.dataset.partnerMenu) return;
    const action = event.target.closest("[data-partner-shipment-action]");
    if (!action) { menu.classList.remove("open"); delete menu.dataset.partnerMenu; return; }
    event.preventDefault();
    menu.classList.remove("open");
    delete menu.dataset.partnerMenu;
    const selected = shipmentRows.find((row) => String(row.id) === menu.dataset.partnerShipmentId);
    if (action.dataset.partnerShipmentAction === "edit" && selected) openShipmentDialog(selected);
    if (action.dataset.partnerShipmentAction === "shipment-documents" && selected) openPartnerDocuments(selected).catch((error) => toast(error.message || "Belgeler yuklenemedi.", "error"));
    if (action.dataset.partnerShipmentAction === "documents") {
      if (typeof window.openDesktopDocumentsCenter === "function") window.openDesktopDocumentsCenter().catch((error) => toast(error.message || "Belge merkezi yuklenemedi.", "error"));
      else toast("Belge merkezi yuklenemedi.", "error");
    }
    if (action.dataset.partnerShipmentAction === "finance") openPartnerFinanceDialog().catch((error) => toast(error.message || "Partner finans yuklenemedi.", "error"));
    if (action.dataset.partnerShipmentAction === "export") exportPartnerShipments();
  });

  function bindPartnerRows() {
    document.querySelectorAll("[data-partner-id]").forEach((button) => {
      button.onclick = () => {
        selectedPartnerId = button.dataset.partnerId;
        selectedTab = "active";
        loadPartnerWorkspace(selectedPartnerId).catch((error) => toast(error.message, "error"));
      };
    });
  }

  const renderBeforePartnerWorkspace = render;
  render = function () {
    if (page !== "partners") return renderBeforePartnerWorkspace();
    renderPartnerWorkspacePage();
    loadPartnerWorkspace(selectedPartnerId).catch((error) => {
      const content = document.querySelector("#content");
      if (content) content.innerHTML = empty("Partnerler y\u00fcklenemedi", esc(error.message || "Veri okunamad\u0131."));
    });
  };
})();
