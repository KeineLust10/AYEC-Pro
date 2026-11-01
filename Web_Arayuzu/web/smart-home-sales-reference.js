(function () {
  const localToday = () => {
    if (typeof today === "function") return today();
    const date = new Date();
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  };
  const state = {
    search: "",
    productId: "",
    items: [],
    poolSelection: {},
    form: {
      customer_id: "",
      company_name: "",
      contact_name: "",
      phone: "",
      email: "",
      project_name: "",
      date: localToday(),
      block_count: "1",
      flat_count: "1",
      currency: "",
      template: "bulut_deri",
      notes: "",
    },
  };

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
  const currencyCode = value => ["USD", "EUR", "TRY"].includes(String(value || "").toUpperCase()) ? String(value).toUpperCase() : "TRY";
  const numberValue = value => {
    const parsed = Number(String(value ?? "").trim().replace(",", "."));
    return Number.isFinite(parsed) ? parsed : 0;
  };
  const formatMoney = (value, currency) => new Intl.NumberFormat("tr-TR", {
    style: "currency", currency: currencyCode(currency), minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(Number(value) || 0);
  const productText = product => [product.name, product.code, product.category, product.barcode, product.description].join(" ").toLocaleLowerCase("tr-TR");
  const smartHomeKeywords = /akilli|smart|hub|priz|role|zil|aydinlatma|sarj|klima kontrol|enerji|kilit|wii|wiipro|wiicom|wiicap|wiimmd|termostat|otomasyon|interkom|zigbee|dimmer|gateway|sensor|perde|siren|homepod|echo|aqara/;
  function products() {
    const all = Array.isArray(db.stock) ? db.stock : [];
    const smart = all.filter(product => smartHomeKeywords.test(productText(product)));
    return smart.length ? smart : all;
  }
  function customers() { return Array.isArray(db.customers) ? db.customers : []; }
  function selectedCustomer() { return customers().find(customer => String(customer.id) === String(state.form.customer_id)); }
  function productById(id) { return products().find(product => String(product.id) === String(id)); }
  function productPrice(product) { return Number(product.price ?? product.sell_price ?? product.sell ?? 0) || 0; }
  function productCurrency(product) { return currencyCode(product.currency || "TRY"); }
  function offerNumber() {
    const prefix = String(db.settings?.reference_number_prefix || "REF").trim() || "REF";
    const next = String(db.settings?.reference_number_next || "1").trim();
    return `${prefix}${/^\d+$/.test(next) ? next : "1"}`;
  }
  function offerCurrency() { return currencyCode(state.form.currency || state.items[0]?.currency || "TRY"); }
  function offerTemplateOptions() {
    const options = [
      ["modern", "Modern (Premium)"],
      ["corporate", "Kurumsal (Premium)"],
      ["minimal", "Zebra (Premium)"],
      ["bulut_deri", "AYEC Pro (Yeni Taslak)"],
    ];
    if (String(desktopSettings?.proforma_template_uploaded || "0") === "1") options.push(["custom_template", "Kendi \u015eablonum"]);
    if (String(desktopSettings?.proforma_editor_html || "").trim()) options.push(["editor_template", "D\u00fczenleyici \u015eablonum"]);
    const selected = options.some(([value]) => value === state.form.template) ? state.form.template : "bulut_deri";
    return options.map(([value, label]) => `<option value="${value}" ${value === selected ? "selected" : ""}>${label}</option>`).join("");
  }
  function workflowTabs(active) {
    return `<nav class="sales-workflow-tabs" aria-label="Sat\u0131\u015f ak\u0131\u015flar\u0131"><button type="button" data-sales-workflow="sales" class="${active === "sales" ? "active" : ""}">G\u00fcvenlik Sistemleri</button><button type="button" data-sales-workflow="smart-home" class="${active === "smart-home" ? "active" : ""}">Ak\u0131ll\u0131 Ev</button><button type="button" data-sales-workflow="computer" class="${active === "computer" ? "active" : ""}">Bilgisayar</button></nav>`;
  }
  function productOptions() {
    const query = state.search.trim().toLocaleLowerCase("tr-TR");
    const rows = products().filter(product => !query || productText(product).includes(query));
    const items = rows.map(product => `<option value="${escapeHtml(product.id)}" ${String(product.id) === String(state.productId) ? "selected" : ""}>${escapeHtml(product.name || product.part_name || "")} ${product.code ? `[${escapeHtml(product.code)}]` : ""} - ${escapeHtml(formatMoney(productPrice(product), productCurrency(product)))}</option>`).join("");
    return `<option value="">${rows.length ? "\u00dcr\u00fcn se\u00e7in" : "\u00dcr\u00fcn bulunamad\u0131"}</option>${items}`;
  }
  function poolRows(query = "") {
    const normalized = String(query).trim().toLocaleLowerCase("tr-TR");
    return products().filter(product => !normalized || productText(product).includes(normalized)).map(product => {
      const id = String(product.id);
      const choice = state.poolSelection[id] || {};
      const stock = Number(product.qty ?? product.stock ?? 0) || 0;
      return `<tr data-smart-home-pool-row="${escapeHtml(id)}"><td><input type="checkbox" name="product_id" value="${escapeHtml(id)}" ${choice.selected ? "checked" : ""} aria-label="${escapeHtml(product.name || product.part_name || "")} se\u00e7"></td><td>${escapeHtml(product.code || "-")}</td><td><strong>${escapeHtml(product.name || product.part_name || "")}</strong></td><td>${escapeHtml(product.category || "-")}</td><td>${escapeHtml(stock)}</td><td>${escapeHtml(formatMoney(productPrice(product), productCurrency(product)))}</td><td>${escapeHtml(productCurrency(product))}</td><td><input type="number" min="1" max="9999" step="1" name="pool_qty" value="${escapeHtml(choice.qty || 1)}" aria-label="${escapeHtml(product.name || "")} adet"></td><td><input type="text" inputmode="decimal" name="pool_price" value="${escapeHtml(choice.price ?? productPrice(product).toFixed(2))}" aria-label="${escapeHtml(product.name || "")} birim fiyat"></td></tr>`;
    }).join("");
  }
  function openProductPool() {
    state.poolSelection = {};
    const body = `<section class="smart-home-pool-dialog"><p class="muted">Stoktaki ak\u0131ll\u0131 ev \u00fcr\u00fcnlerini aray\u0131n, se\u00e7in ve adet ile fiyatlar\u0131n\u0131 belirleyin.</p><input class="control" type="search" placeholder="\u00dcr\u00fcn ad\u0131, kod, kategori veya barkod ile ara" data-smart-home-pool-search><div class="smart-home-pool-table-wrap"><table class="smart-home-pool-table"><thead><tr><th></th><th>Kod</th><th>\u00dcr\u00fcn</th><th>Kategori</th><th>Stok</th><th>Fiyat</th><th>PB</th><th>Adet</th><th>Birim Fiyat</th></tr></thead><tbody data-smart-home-pool-rows>${poolRows()}</tbody></table></div><small class="muted">${products().length} \u00fcr\u00fcn</small></section>`;
    openDialog("Ak\u0131ll\u0131 Ev \u00dcr\u00fcn Havuzu", "SALES HUB", body, () => {
      const selected = Object.entries(state.poolSelection).filter(([, choice]) => choice.selected);
      if (!selected.length) throw Error("L\u00fctfen en az bir \u00fcr\u00fcn se\u00e7in.");
      selected.forEach(([id, choice]) => {
        const product = productById(id);
        if (!product) return;
        state.items.push({ id: product.id, name: String(product.name || product.part_name || ""), brand: String(product.brand || ""), code: String(product.code || ""), category: String(product.category || ""), description: String(product.description || product.category || ""), qty: Math.max(1, Math.min(9999, Math.trunc(numberValue(choice.qty) || 1))), unit_price: Math.max(0, numberValue(choice.price)), currency: productCurrency(product) });
      });
      render();
      return true;
    }, "Se\u00e7ili \u00dcr\u00fcnleri Teklife Ekle");
  }
  function selectedRows() {
    if (!state.items.length) return '<tr><td colspan="8" class="smart-home-empty">Hen\u00fcz \u00fcr\u00fcn eklenmedi.</td></tr>';
    return state.items.map((item, index) => `<tr><td><strong>${escapeHtml(item.name)}</strong></td><td>${escapeHtml(item.code || "-")}</td><td>${escapeHtml(item.category || "-")}</td><td>${escapeHtml(item.description || "-")}</td><td><input type="number" min="1" max="9999" step="1" value="${escapeHtml(item.qty)}" aria-label="${escapeHtml(item.name)} adet" data-smart-home-qty="${index}"></td><td><input type="text" inputmode="decimal" value="${escapeHtml(item.unit_price.toFixed(2))}" aria-label="${escapeHtml(item.name)} birim fiyat" data-smart-home-price="${index}"></td><td>${escapeHtml(formatMoney(item.qty * item.unit_price, item.currency))}</td><td><button type="button" class="secondary" data-smart-home-remove="${index}" aria-label="\u00dcr\u00fcn\u00fc kald\u0131r">&times;</button></td></tr>`).join("");
  }
  function missingExchangeRates(currency = offerCurrency()) {
    const targetCurrency = currencyCode(currency);
    const missing = new Set();
    state.items.forEach(item => {
      const sourceCurrency = currencyCode(item.currency);
      if (sourceCurrency === targetCurrency) return;
      [sourceCurrency, targetCurrency].forEach(code => {
        if (code !== "TRY" && !(Number(rateForCode(code)) > 0)) missing.add(code);
      });
    });
    return Array.from(missing);
  }
  function totalsMarkup() {
    const currency = offerCurrency();
    const missingRates = missingExchangeRates(currency);
    if (missingRates.length) return `Kur bekleniyor: ${missingRates.join(", ")}`;
    const total = state.items.reduce((sum, item) => sum + targetPrice(item, currency) * item.qty, 0);
    return formatMoney(total, currency);
  }
  function renderPage() {
    const form = state.form;
    const customerOptions = customers().map(customer => `<option value="${escapeHtml(customer.id)}" ${String(customer.id) === String(form.customer_id) ? "selected" : ""}>${escapeHtml(customer.name || customer.company_name || "M\u00fc\u015fteri")}</option>`).join("");
    const tabMarkup = workflowTabs("smart-home");
    return `${tabMarkup}<section class="smart-home-sales-page"><header class="smart-home-sales-header"><div><h2>Ak\u0131ll\u0131 Ev Proforma</h2><p>M\u00fc\u015fteri ve proje bilgilerini girin, \u00fcr\u00fcnleri ekleyin ve kurumsal PDF proforma olu\u015fturun.</p></div><div class="smart-home-offer-badge"><strong>${escapeHtml(offerNumber())}</strong><span>${escapeHtml(form.date)} \u00b7 ${state.items.length} kalem</span></div></header><div class="smart-home-sales-grid"><section class="card smart-home-project-card"><div class="card-head"><h3>Proje ve M\u00fc\u015fteri Bilgileri</h3><span class="badge">Proje teklifi</span></div><div class="smart-home-form-grid"><label>M\u00fc\u015fteri<select class="control" data-smart-home-field="customer_id"><option value="">M\u00fc\u015fteri se\u00e7in</option>${customerOptions}</select></label><label>Teklif No<input class="control" value="${escapeHtml(offerNumber())}" readonly></label><label>Firma / Kurum<input class="control" data-smart-home-field="company_name" value="${escapeHtml(form.company_name)}"></label><label>Tarih<input class="control" type="date" data-smart-home-field="date" value="${escapeHtml(form.date)}"></label><label>Yetkili Ki\u015fi<input class="control" data-smart-home-field="contact_name" value="${escapeHtml(form.contact_name)}"></label><label>Telefon<input class="control" data-smart-home-field="phone" value="${escapeHtml(form.phone)}"></label><label>E-Posta<input class="control" type="email" data-smart-home-field="email" value="${escapeHtml(form.email)}"></label><label>Proje Ad\u0131<input class="control" data-smart-home-field="project_name" value="${escapeHtml(form.project_name)}" required></label><label>Blok Say\u0131s\u0131<input class="control" type="number" min="1" max="9999" step="1" data-smart-home-field="block_count" value="${escapeHtml(form.block_count)}"></label><label>Daire Say\u0131s\u0131<input class="control" type="number" min="1" max="9999" step="1" data-smart-home-field="flat_count" value="${escapeHtml(form.flat_count)}"></label><label class="smart-home-notes">Proje Notlar\u0131<textarea class="control" rows="3" data-smart-home-field="notes">${escapeHtml(form.notes)}</textarea></label><label>Teklif Para Birimi<select class="control" data-smart-home-field="currency"><option value="TRY" ${offerCurrency()==="TRY"?"selected":""}>TRY - TL</option><option value="USD" ${offerCurrency()==="USD"?"selected":""}>USD - $</option><option value="EUR" ${offerCurrency()==="EUR"?"selected":""}>EUR - \u20ac</option></select></label><label>Proforma \u015eablonu<select class="control" data-smart-home-field="template">${offerTemplateOptions()}</select></label></div></section><div class="smart-home-right-column"><section class="card smart-home-product-card"><div class="card-head"><h3>Ak\u0131ll\u0131 Ev \u00dcr\u00fcn Havuzu</h3><span class="badge">${products().length} \u00fcr\u00fcn</span></div><button type="button" class="primary smart-home-pool-open" data-smart-home-open-pool>Ak\u0131ll\u0131 Ev \u00dcr\u00fcn Havuzunu A\u00e7</button><div class="smart-home-product-controls"><input class="control" type="search" placeholder="\u00dcr\u00fcn, kod veya kategori ara" value="${escapeHtml(state.search)}" data-smart-home-search><select class="control" data-smart-home-product>${productOptions()}</select><label>Adet<input class="control" type="number" min="1" max="9999" step="1" value="1" data-smart-home-add-qty></label><label>Birim Fiyat<input class="control" type="text" inputmode="decimal" value="${escapeHtml(state.productId ? (productPrice(productById(state.productId)) || 0).toFixed(2) : "0.00")}" data-smart-home-add-price></label><button type="button" class="primary" data-smart-home-add>\u00dcr\u00fcn Ekle</button></div><p class="muted">Fiyatlar stok kart\u0131ndaki d\u00f6viz t\u00fcr\u00fcyle korunur. Proforma para birimini ve tasar\u0131m \u015fablonunu se\u00e7in.</p></section><section class="card smart-home-items-card"><div class="card-head"><h3>Teklif Kalemleri</h3><span class="badge">${state.items.length} kalem</span></div><div class="smart-home-table-wrap"><table class="smart-home-items"><thead><tr><th>\u00dcr\u00fcn</th><th>Kod</th><th>Kategori</th><th>A\u00e7\u0131klama</th><th>Adet</th><th>Birim Fiyat</th><th>Toplam</th><th></th></tr></thead><tbody>${selectedRows()}</tbody></table></div><div class="smart-home-total"><span>Toplam</span><strong>${escapeHtml(totalsMarkup())}</strong></div><div class="smart-home-actions"><button type="button" class="secondary" data-smart-home-clear>Listeyi Temizle</button><button type="button" class="primary" data-smart-home-generate>Ak\u0131ll\u0131 Ev Proforma PDF Olu\u015ftur</button></div></section></div></div></section>`;
  }
  function targetPrice(item, currency) {
    const sourceCurrency = currencyCode(item.currency);
    const targetCurrency = currencyCode(currency);
    if (sourceCurrency === targetCurrency) return item.unit_price;
    const sourceRate = sourceCurrency === "TRY" ? 1 : Number(rateForCode(sourceCurrency));
    const targetRate = targetCurrency === "TRY" ? 1 : Number(rateForCode(targetCurrency));
    if (!(sourceRate > 0) || !(targetRate > 0)) return null;
    const amountTry = item.unit_price * sourceRate;
    return targetCurrency === "TRY" ? amountTry : amountTry / targetRate;
  }
  async function generateProforma() {
    if (!state.items.length) throw Error("PDF olu\u015fturmadan \u00f6nce en az bir \u00fcr\u00fcn ekleyin.");
    const company = String(state.form.company_name || "").trim();
    const project = String(state.form.project_name || "").trim();
    if (!company) throw Error("Firma / kurum alan\u0131 bo\u015f b\u0131rak\u0131lamaz.");
    if (!project) throw Error("Proje ad\u0131 bo\u015f b\u0131rak\u0131lamaz.");
    const currency = offerCurrency();
    const missingRates = missingExchangeRates(currency);
    if (missingRates.length) throw Error(`Kur bilgisi eksik: ${missingRates.join(", ")}. Proforma olu\u015fturmak i\u00e7in kuru g\u00fcncelleyin.`);
    const payload = {
      company_name: company,
      customer_name: String(state.form.contact_name || company).trim(),
      customer_company: company,
      project_name: project,
      reference_no: offerNumber(),
      template: state.form.template,
      currency,
      margin_percent: 0,
      vat_percent: ayecNormalizeVatPercent(desktopSettings?.default_vat_percent ?? db.settings?.default_vat_percent),
      items: state.items.map(item => ({ component: item.category || "Akilli Ev", category: item.category || "Akilli Ev", brand: item.brand, product: item.name, qty: item.qty, price: targetPrice(item, currency) })),
    };
    const popup = window.open("about:blank", "_blank");
    let response;
    try {
      response = await fetch("/api/desktop/pc-builder/proforma.pdf", { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin", body: JSON.stringify(payload) });
    } catch (error) {
      popup?.close();
      throw error;
    }
    if (!response.ok) {
      popup?.close();
      let message = "PDF olu\u015fturulamad\u0131.";
      try { message = (await response.json()).error || message; } catch (_) {}
      throw Error(message);
    }
    const fileUrl = URL.createObjectURL(await response.blob());
    if (popup) { popup.location.replace(fileUrl); setTimeout(() => URL.revokeObjectURL(fileUrl), 60000); }
    else { const link = document.createElement("a"); link.href = fileUrl; link.download = `${offerNumber()}-akilli-ev-proforma.pdf`; link.click(); setTimeout(() => URL.revokeObjectURL(fileUrl), 60000); }
    toast("Akilli Ev proforma PDF olusturuldu.", "success");
  }
  function render() { const host = document.querySelector("#content"); if (host) host.innerHTML = renderPage(); }

  window.ayecSmartHomeSalesMode = false;
  window.ayecSalesWorkflowTabs = workflowTabs;
  window.ayecRenderSmartHomeSales = renderPage;

  document.addEventListener("click", event => {
    const tab = event.target.closest("[data-sales-workflow]");
    if (tab) {
      const route = tab.dataset.salesWorkflow;
      window.ayecSmartHomeSalesMode = route === "smart-home";
      if (route === "computer") { navigate("pc-builder"); return; }
      if (page !== "sales") navigate("sales"); else render();
      return;
    }
    if (page !== "sales" || !window.ayecSmartHomeSalesMode) return;
    if (event.target.closest("[data-smart-home-add]")) {
      const product = productById(state.productId);
      if (!product) { toast("L\u00fctfen \u00fcr\u00fcn se\u00e7in.", "warning"); return; }
      const qty = Math.max(1, Math.min(9999, Math.trunc(numberValue(document.querySelector("[data-smart-home-add-qty]")?.value) || 1)));
      const price = Math.max(0, Math.min(999999999, numberValue(document.querySelector("[data-smart-home-add-price]")?.value)));
      state.items.push({ id: product.id, name: String(product.name || product.part_name || ""), brand: String(product.brand || ""), code: String(product.code || ""), category: String(product.category || ""), description: String(product.description || product.category || ""), qty, unit_price: price, currency: productCurrency(product) });
      state.productId = "";
      render();
      return;
    }
    const remove = event.target.closest("[data-smart-home-remove]");
    if (remove) { state.items.splice(Number(remove.dataset.smartHomeRemove), 1); render(); return; }
    if (event.target.closest("[data-smart-home-clear]")) { state.items = []; render(); return; }
    if (event.target.closest("[data-smart-home-generate]")) generateProforma().catch(error => toast(error.message || "PDF olusturulamadi.", "error"));
  });
  document.addEventListener("change", event => {
    if (page !== "sales" || !window.ayecSmartHomeSalesMode) return;
    const field = event.target.dataset.smartHomeField;
    if (field) {
      state.form[field] = event.target.value;
      if (field === "customer_id") {
        const customer = selectedCustomer();
        if (customer) {
          state.form.company_name = customer.company_name || customer.company || customer.name || "";
          state.form.contact_name = customer.contact_person || customer.contact || customer.name || "";
          state.form.phone = customer.phone || customer.phone1 || "";
          state.form.email = customer.email || "";
        }
        render();
      } else if (field === "currency" || field === "template") {
        render();
      }
      return;
    }
    if (event.target.matches("[data-smart-home-product]")) {
      state.productId = event.target.value;
      const product = productById(state.productId);
      const price = document.querySelector("[data-smart-home-add-price]");
      if (price) price.value = productPrice(product).toFixed(2);
      return;
    }
    const quantity = event.target.dataset.smartHomeQty;
    if (quantity !== undefined && state.items[Number(quantity)]) {
      state.items[Number(quantity)].qty = Math.max(1, Math.min(9999, Math.trunc(numberValue(event.target.value) || 1)));
      render();
      return;
    }
    const priceIndex = event.target.dataset.smartHomePrice;
    if (priceIndex !== undefined && state.items[Number(priceIndex)]) {
      state.items[Number(priceIndex)].unit_price = Math.max(0, Math.min(999999999, numberValue(event.target.value)));
      render();
    }
  });
  document.addEventListener("input", event => {
    if (page !== "sales" || !window.ayecSmartHomeSalesMode) return;
    if (event.target.matches("[data-smart-home-pool-search]")) {
      const tbody = document.querySelector("[data-smart-home-pool-rows]");
      if (tbody) tbody.innerHTML = poolRows(event.target.value);
      return;
    }
    const poolRow = event.target.closest("[data-smart-home-pool-row]");
    if (poolRow && event.target.name !== "product_id") {
      const choice = state.poolSelection[poolRow.dataset.smartHomePoolRow] || (state.poolSelection[poolRow.dataset.smartHomePoolRow] = {});
      if (event.target.name === "pool_qty") choice.qty = event.target.value;
      if (event.target.name === "pool_price") choice.price = event.target.value;
    }
    if (event.target.matches("[data-smart-home-search]")) {
      state.search = event.target.value;
      const select = document.querySelector("[data-smart-home-product]");
      if (select) { state.productId = ""; select.innerHTML = productOptions(); }
      return;
    }
    const field = event.target.dataset.smartHomeField;
    if (field) state.form[field] = event.target.value;
  });
  document.addEventListener("change", event => {
    if (page !== "sales" || !window.ayecSmartHomeSalesMode) return;
    if (event.target.matches("[data-smart-home-pool-search]")) {
      const tbody = document.querySelector("[data-smart-home-pool-rows]");
      if (tbody) tbody.innerHTML = poolRows(event.target.value);
      return;
    }
    const poolRow = event.target.closest("[data-smart-home-pool-row]");
    if (poolRow && event.target.name === "product_id") {
      const choice = state.poolSelection[poolRow.dataset.smartHomePoolRow] || (state.poolSelection[poolRow.dataset.smartHomePoolRow] = {});
      choice.selected = event.target.checked;
    }
  });
  document.addEventListener("click", event => {
    if (page === "sales" && window.ayecSmartHomeSalesMode && event.target.closest("[data-smart-home-open-pool]")) openProductPool();
  });
})();
