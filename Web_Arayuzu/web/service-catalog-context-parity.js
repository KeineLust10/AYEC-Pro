(function () {
  const baseShowContext = window.showContext;
  const items = [
    ["\u{2795} Yeni Hizmet", "add"],
    ["\u{1f4dd} D\u00fczenle", "edit"],
    ["\u{1f5d1}\ufe0f Sil", "delete"],
    ["\u{1f4e4} Excel Aktar", "excel"],
    ["\u{1f4c4} PDF Olarak Kaydet", "pdf"],
    ["\u{1f5a8}\ufe0f Yazd\u0131r", "print"]
  ];

  async function exportServiceCatalog() {
    try {
      const response = await fetch("/api/desktop/services/export/xlsx", { credentials: "same-origin" });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `Excel export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Hizmet_Listesi.xlsx";
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      window.toast("Hizmet listesi Excel'e aktar\u0131ld\u0131.", "success");
    } catch (error) {
      window.toast(error.message || "Excel export failed.", "error");
    }
  }

  async function exportServiceCatalogPdf() {
    try {
      const response = await fetch("/api/desktop/services/export/pdf", { credentials: "same-origin" });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || `PDF export failed (${response.status})`);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "Hizmet_Listesi.pdf";
      document.body.append(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      window.toast("Hizmet listesi PDF olarak kaydedildi.", "success");
    } catch (error) {
      window.toast(error.message || "PDF export failed.", "error");
    }
  }
  async function deleteServiceDefinition(id) {
    const row = (window.currentGenericData?.rows || []).find(item => String(item.id) === String(id));
    window.openDialog("Hizmeti Sil", "SILME ONAYI", `<p>"${esc(row?.name || "Hizmet")}" kayd\u0131 silinsin mi?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`, async () => {
      try {
        await window.apiFetch("/api/desktop/service-definition/delete", {
          method: "POST",
          body: JSON.stringify({ id: Number(id) })
        });
        window.toast("Kay\u0131t silindi", "warning");
        await window.loadGenericModule(window.currentGenericMeta, document.querySelector("#genericSearch")?.value || "");
      } catch (error) {
        window.toast(error.message || "Hizmet silinemedi.", "error");
        return false;
      }
    }, "Evet, Sil");
    const cancel = document.querySelector("#dialogCancel");
    if (cancel) cancel.textContent = "Hay\u0131r";
    const submit = document.querySelector("#dialogSubmit");
    if (submit) { submit.classList.remove("primary"); submit.classList.add("danger"); }
  }

  function runAction(action, id, row) {
    if (action === "add") return document.querySelector("[data-generic-add]")?.click();
    if (action === "edit") return window.contextAction("generic", id, "generic-edit", row);
    if (action === "delete") {
      const data = window.currentGenericData;
      const service = data && data.rows ? data.rows[Number(id)] : null;
      return service ? deleteServiceDefinition(service.id) : window.toast("Hizmet kayd\u0131 bulunamad\u0131.", "warning");
    }
    if (action === "excel") return exportServiceCatalog();
    if (action === "pdf") return exportServiceCatalogPdf();
    const selector = action === "pdf" ? "[data-labor-pdf]" : "[data-labor-print]";
    return document.querySelector(selector)?.click();
  }

  function showServiceCatalogContext(event, id, row) {
    if (!window.ayecContextMenuEnabled()) return;
    event.preventDefault();
    const menu = document.querySelector("#contextMenu");
    menu.innerHTML = items.map(([label, action], index) =>
      (index === 3 ? '<hr class="service-catalog-context-separator">' : "") +
      `<button type="button" data-service-catalog-context="${action}">${label}</button>`
    ).join("");
    menu.style.left = `${Math.max(8, Math.min(event.clientX, innerWidth - 230))}px`;
    menu.style.top = `${Math.max(8, Math.min(event.clientY, innerHeight - items.length * 38 - 24))}px`;
    menu.classList.add("open");
    menu.querySelectorAll("[data-service-catalog-context]").forEach(button => {
      button.onclick = () => {
        menu.classList.remove("open");
        runAction(button.dataset.serviceCatalogContext, id, row);
      };
    });
  }

  if (typeof baseShowContext === "function") {
    window.showContext = function (event, kind, id) {
      if (kind === "generic" && window.currentGenericMeta?.table === "services") {
        return showServiceCatalogContext(event, id, event.currentTarget);
      }
      return baseShowContext(event, kind, id);
    };
  }

  document.addEventListener("click", event => {
    if (event.target.closest("[data-labor-pdf]") && window.currentGenericMeta?.table === "services") {
      event.preventDefault();
      event.stopImmediatePropagation();
      exportServiceCatalogPdf();
      return;
    }
    if (!event.target.closest("[data-labor-export]") || window.currentGenericMeta?.table !== "services") return;
    event.preventDefault();
    event.stopImmediatePropagation();
    exportServiceCatalog();
  }, true);
})();

(function () {
  const baseGenericShell = window.genericShell;
  const baseLaborTable = window.laborServicesTable;
  const baseBindLaborFilters = window.bindLaborServiceFilters;
  window.laborSelectedIds = window.laborSelectedIds || new Set();
  window.laborMultiSelect = false;

  window.genericShell = function (meta) {
    const html = baseGenericShell(meta);
    if (meta?.table !== "services") return html;
    const menu = '<details class="labor-more-menu"><summary class="secondary" aria-label="\u0110i\u011fer i\u015flemler">\u22ef</summary><div class="labor-more-menu-items" role="menu"><button type="button" role="menuitem" data-service-more="multi">\u00c7oklu Se\u00e7im</button><button type="button" role="menuitem" data-service-more="edit">Se\u00e7ileni D\u00fczenle</button><button type="button" role="menuitem" data-service-more="delete">Se\u00e7ileni Sil</button><hr><button type="button" role="menuitem" data-service-more="smart-import">Ak\u0131ll\u0131 \u0130\u00e7e Aktar</button><button type="button" role="menuitem" data-service-more="excel-import">Excel \u0130\u00e7e Aktar</button></div></details>';
    return html.replace('<button class="primary" data-generic-add>', `${menu}<button class="primary" data-generic-add>`);
  };

  window.laborServicesTable = function (rows, allRows) {
    return baseLaborTable(rows, allRows).replace(/(<tr[^>]*data-generic-row=")(\d+)"/g, (match, prefix, index) => `${prefix}${index}" data-labor-id="${esc(rows[Number(index)]?.id ?? "")}"`);
  };

  window.bindLaborServiceFilters = function () {
    baseBindLaborFilters();
    document.querySelectorAll(".labor-services-table tbody tr[data-labor-id]").forEach(row => {
      const checkbox = row.querySelector('input[type="checkbox"]');
      if (!checkbox) return;
      checkbox.checked = window.laborSelectedIds.has(String(row.dataset.laborId));
      row.classList.toggle("selected", checkbox.checked);
      checkbox.onchange = () => {
        const id = String(row.dataset.laborId);
        if (checkbox.checked) {
          window.laborMultiSelect = true;
          window.laborSelectedIds.add(id);
        } else {
          window.laborSelectedIds.delete(id);
        }
        row.classList.toggle("selected", checkbox.checked);
      };
    });
  };

  const importInput = document.createElement("input");
  importInput.type = "file";
  importInput.hidden = true;
  importInput.id = "serviceCatalogImportFile";
  document.body.append(importInput);

  function importFields() {
    const fields = [
      ["name", "Hizmet Ad\u0131", "name"],
      ["price", "Birim Fiyat", "purchase_price"],
      ["currency", "Para Birimi", "currency"],
      ["description", "A\u00e7\u0131klama", "desc"],
      ["barcode", "Barkod / Kod", "code"],
    ];
    const automotive = typeof currentSector !== "undefined" && currentSector === "otomotiv";
    if (automotive) fields.push(
      ["vehicle_type", "Ara\u00e7 Tipi", "vehicle_type"],
      ["vehicle_brand", "Marka", "vehicle_brand"],
      ["vehicle_model", "Model", "vehicle_model"],
      ["vehicle_year", "Y\u0131l", "vehicle_year"],
      ["vehicle_plate", "Plaka", "vehicle_plate"],
    );
    return fields;
  }

  function normalizeImportHeader(value) {
    return String(value || "").toLocaleLowerCase("tr-TR").normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "").replace(/\u0131/g, "i").replace(/[^a-z0-9]+/g, " ").trim();
  }

  function mapServiceImportRows() {
    const state = window.serviceCatalogImportState;
    if (!state) return;
    const mapping = {};
    document.querySelectorAll("[data-service-import-map]").forEach(select => { mapping[select.dataset.serviceImportMap] = select.value; });
    state.mapping = mapping;
    state.rows = state.sourceRows.map(source => Object.fromEntries(
      importFields().map(([key]) => [key, String(mapping[key] ? source[mapping[key]] ?? "" : "")])
    ));
    renderServiceImportRows();
  }

  function readServiceImportRows() {
    return [...document.querySelectorAll("[data-service-import-row]")].map(row => {
      const result = {};
      row.querySelectorAll("[data-service-import-field]").forEach(input => { result[input.dataset.serviceImportField] = input.value; });
      return result;
    });
  }

  function renderServiceImportRows() {
    const state = window.serviceCatalogImportState;
    const body = document.querySelector("#serviceImportRows");
    if (!state || !body) return;
    body.innerHTML = state.rows.map((row, index) => `<tr data-service-import-row="${index}"><td><input type="checkbox" aria-label="Sat\u0131r\u0131 se\u00e7"></td>${importFields().map(([key]) => `<td><input data-service-import-field="${key}" type="${key === "price" ? "number" : "text"}" ${key === "price" ? 'min="0" step="0.01"' : ""} value="${esc(row[key] || "")}"></td>`).join("")}</tr>`).join("");
  }

  function serviceImportDialog(filename, parsed, smart) {
    const sourceRows = Array.isArray(parsed.raw_rows) && parsed.raw_rows.length ? parsed.raw_rows : (parsed.rows || []);
    const fields = importFields();
    const columns = Array.isArray(parsed.detected_columns) && parsed.detected_columns.length
      ? parsed.detected_columns : [...new Set(sourceRows.flatMap(row => Object.keys(row || {})))];
    const suggestions = parsed.suggested_mapping || {};
    const hints = {
      name: ["hizmet", "servis", "name", "service", "urun", "product", "baslik", "isim", "ad"],
      price: ["price", "purchase price", "fiyat", "ucret", "amount", "tutar"],
      currency: ["currency", "para birimi", "doviz"],
      description: ["description", "desc", "aciklama", "not"],
      barcode: ["code", "barcode", "barkod", "sku", "referans"],
      vehicle_type: ["vehicle type", "arac tipi", "tip"],
      vehicle_brand: ["vehicle brand", "arac marka", "marka", "brand"],
      vehicle_model: ["vehicle model", "arac model", "model"],
      vehicle_year: ["vehicle year", "model yili", "yil", "year"],
      vehicle_plate: ["vehicle plate", "arac plaka", "plaka", "plate"],
    };
    const mapping = {};
    for (const [key, , parserKey] of fields) {
      const suggested = suggestions[parserKey];
      const direct = columns.find(column => normalizeImportHeader(column) === normalizeImportHeader(suggested || ""));
      mapping[key] = direct || columns.find(column => hints[key].some(hint => normalizeImportHeader(column).includes(hint))) || "";
    }
    window.serviceCatalogImportState = { filename, sourceRows, rows: [], columns, mapping, warnings: parsed.warnings || [], engine: parsed.engine || "StockImportParser", smart };
    const warningHtml = window.serviceCatalogImportState.warnings.filter(Boolean).map(item => `<p>${esc(item)}</p>`).join("");
    const mapHtml = fields.map(([key, label]) => `<label class="field"><span>${label}</span><select data-service-import-map="${key}"><option value="">(Yoksay)</option>${columns.map(column => `<option value="${esc(column)}" ${mapping[key] === column ? "selected" : ""}>${esc(column)}</option>`).join("")}</select></label>`).join("");
    const header = fields.map(([, label]) => `<th>${label}</th>`).join("");
    const body = `<section class="service-import-preview"><p class="muted">${esc(filename)} \u00b7 ${esc(window.serviceCatalogImportState.engine)} \u00b7 ${sourceRows.length} kaynak sat\u0131r\u0131</p>${warningHtml ? `<div class="import-warnings">${warningHtml}</div>` : ""}<div class="service-import-mapping">${mapHtml}<button type="button" class="secondary" data-service-import-apply>\u0130\u015faretlemeyi Uygula</button></div><div class="service-import-actions"><button type="button" class="secondary" data-service-import-add>+ Sat\u0131r Ekle</button><button type="button" class="secondary" data-service-import-remove>Se\u00e7ileni Sil</button></div><div class="table-wrap service-import-table"><table><thead><tr><th></th>${header}</tr></thead><tbody id="serviceImportRows"></tbody></table></div></section>`;
    window.openDialog(smart ? "Ak\u0131ll\u0131 Hizmet \u0130\u00e7e Aktar" : "Hizmet Listesi \u0130\u00e7e Aktar", "H\u0130ZMET Y\u00d6NET\u0130M\u0130", body, async () => {
      const rows = readServiceImportRows().filter(row => String(row.name || "").trim());
      if (!rows.length) { window.toast("Kaydedilecek hizmet sat\u0131r\u0131 yok.", "warning"); return false; }
      await window.apiFetch("/api/desktop/service-definition/import", { method: "POST", body: JSON.stringify({ rows, is_automotive: typeof currentSector !== "undefined" && currentSector === "otomotiv" }) });
      window.laborSelectedIds.clear();
      window.laborMultiSelect = false;
      window.toast(`${rows.length} hizmet i\u00e7e aktar\u0131ld\u0131.`, "success");
      await window.loadGenericModule(window.currentGenericMeta, document.querySelector("#genericSearch")?.value || "");
    }, "Hizmetleri Kaydet");
    const importDialog = document.querySelector("#appDialog");
    importDialog.classList.add("service-import-dialog");
    importDialog.addEventListener("close", () => importDialog.classList.remove("service-import-dialog"), { once: true });
    window.serviceCatalogImportState.rows = sourceRows.map(source => Object.fromEntries(
      fields.map(([key]) => [key, String(mapping[key] ? source[mapping[key]] ?? "" : "")])
    ));
    renderServiceImportRows();
  }

  async function chooseServiceImport(mode) {
    importInput.dataset.serviceImportMode = mode;
    importInput.accept = mode === "excel-import" ? ".xlsx,.xls,.csv" : ".xlsx,.xls,.csv,.pdf,.xml,.docx,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp,.ppm";
    importInput.value = "";
    importInput.click();
  }

  importInput.onchange = async event => {
    const file = event.target.files?.[0];
    const mode = importInput.dataset.serviceImportMode;
    if (!file) return;
    try {
      window.toast("Hizmet dosyas\u0131 analiz ediliyor...", "warning");
      const parsed = await window.apiFetch("/api/desktop/smart-import", { method: "POST", body: JSON.stringify({ name: file.name, data: await window.fileBase64(file) }) });
      const sourceRows = Array.isArray(parsed.raw_rows) && parsed.raw_rows.length ? parsed.raw_rows : (parsed.rows || []);
      if (!sourceRows.length && !parsed.text) throw new Error((parsed.warnings || []).join("; ") || "No service rows were found in the file");
      serviceImportDialog(file.name, parsed, mode === "smart-import");
    } catch (error) {
      window.toast(error.message || "Service import failed", "error");
    } finally {
      importInput.value = "";
    }
  };

  document.addEventListener("click", event => {
    if (event.target.closest("[data-service-import-apply]")) return mapServiceImportRows();
    if (event.target.closest("[data-service-import-add]")) {
      const rows = readServiceImportRows();
      rows.push(Object.fromEntries(importFields().map(([key]) => [key, ""])));
      window.serviceCatalogImportState.rows = rows;
      return renderServiceImportRows();
    }
    if (event.target.closest("[data-service-import-remove]")) {
      const selected = [...document.querySelectorAll("[data-service-import-row]")].filter(row => row.querySelector('input[type="checkbox"]')?.checked);
      if (!selected.length) return window.toast("Silmek i\u00e7in en az bir sat\u0131r se\u00e7in.", "warning");
      const indices = new Set(selected.map(row => Number(row.dataset.serviceImportRow)));
      window.serviceCatalogImportState.rows = readServiceImportRows().filter((_, index) => !indices.has(index));
      return renderServiceImportRows();
    }
  });

  document.addEventListener("click", event => {
    const action = event.target.closest("[data-service-more]");
    if (!action || window.currentGenericMeta?.table !== "services") return;
    const menu = action.closest(".labor-more-menu");
    menu.open = false;
    if (action.dataset.serviceMore === "smart-import" || action.dataset.serviceMore === "excel-import") {
      return chooseServiceImport(action.dataset.serviceMore);
    }
    const selected = [...window.laborSelectedIds];
    if (action.dataset.serviceMore === "multi") {
      window.laborMultiSelect = !window.laborMultiSelect;
      window.laborSelectedIds.clear();
      document.querySelectorAll(".labor-services-table tbody input[type=checkbox]").forEach(input => { input.checked = false; input.closest("tr")?.classList.remove("selected"); });
      menu.querySelector('[data-service-more="multi"]').textContent = window.laborMultiSelect ? "\u00c7oklu Se\u00e7im A\u00e7\u0131k" : "\u00c7oklu Se\u00e7im";
      return;
    }
    const data = window.currentGenericData;
    const rows = selected.map(id => (data?.rows || []).find(row => String(row.id) === id)).filter(Boolean);
    if (!rows.length) return window.toast("\u0130\u015flem i\u00e7in en az bir hizmet se\u00e7in.", "warning");
    if (action.dataset.serviceMore === "edit") {
      if (rows.length !== 1) return window.toast("D\u00fczenlemek i\u00e7in tek bir hizmet se\u00e7in.", "warning");
      return window.openGenericDialog(window.currentGenericMeta, rows[0], data.columns);
    }
    const count = rows.length;
    window.openDialog("Se\u00e7ili Hizmetleri Sil", "H\u0130ZMET Y\u00d6NET\u0130M\u0130", `<p>${count} adet hizmet silinsin mi? Bu i\u015flem geri al\u0131namaz.</p>`, async () => {
      let deleted = 0;
      for (const row of rows) {
        await window.apiFetch("/api/desktop/service-definition/delete", { method: "POST", body: JSON.stringify({ id: Number(row.id) }) });
        deleted += 1;
      }
      window.laborSelectedIds.clear();
      window.laborMultiSelect = false;
      window.toast(`${deleted} hizmet silindi.`, "success");
      await window.loadGenericModule(window.currentGenericMeta, document.querySelector("#genericSearch")?.value || "");
    }, "Evet, Sil");
    const cancel = document.querySelector("#dialogCancel");
    if (cancel) cancel.textContent = "Hay\u0131r";
    const submit = document.querySelector("#dialogSubmit");
    if (submit) { submit.classList.remove("primary"); submit.classList.add("danger"); }
  });
})();
