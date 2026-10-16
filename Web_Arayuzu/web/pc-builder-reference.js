(function () {
  const pcDefaults = [
    ["Anakart", "Anakart", "Form Fakt\u00f6r", ["ATX", "mATX", "ITX", "E-ATX"]],
    ["\u0130\u015flemci (CPU)", "\u0130\u015flemci", "Soket", ["LGA1700", "LGA1200", "AM5", "AM4", "TR4"]],
    ["RAM (Bellek)", "RAM", "Tip", ["DDR5", "DDR4", "DDR3", "ECC DDR4"]],
    ["SSD / M.2", "SSD", "Aray\u00fcz", ["NVMe M.2", "SATA SSD", "M.2 SATA"]],
    ["HDD", "HDD", "RPM", ["7200 RPM", "5400 RPM", "10000 RPM"]],
    ["Ekran Kart\u0131 (GPU)", "Ekran Kart\u0131", "Ba\u011flant\u0131", ["PCIe 4.0 x16", "PCIe 3.0 x16"]],
    ["\u0130\u015flemci So\u011futucu", "CPU So\u011futucu", "Tip", ["Hava", "S\u0131v\u0131 (AIO)", "Custom Loop"]],
    ["G\u00fc\u00e7 Kayna\u011f\u0131 (PSU)", "G\u00fc\u00e7 Kayna\u011f\u0131", "Sertifika", ["80+ Gold", "80+ Platinum", "80+ Bronze", "80+ Titanium"]],
    ["Kasa", "Kasa", "Form Fakt\u00f6r", ["Mid Tower", "Full Tower", "Mini ITX", "Slim ATX"]],
    ["Monit\u00f6r", "Monit\u00f6r", "Panel", ["IPS", "VA", "TN", "OLED", "Mini-LED"]],
    ["Klavye", "Klavye", "Tip", ["Mekanik", "Membran", "Hybrid"]],
    ["Mouse", "Mouse", "DPI", ["Standart", "Gaming", "Ergonomik"]],
    ["\u0130\u015fletim Sistemi", "Yaz\u0131l\u0131m", "S\u00fcr\u00fcm", ["Windows 11 Pro", "Windows 11 Home", "Windows 10 Pro"]],
    ["Thermal Pasta", "Aksesuar", "Tip", ["Standart", "Premium", "Liquid Metal"]],
    ["Kablo Y\u00f6netimi", "Aksesuar", "Tip", ["Standart", "Mod\u00fcler PSU"]]
  ];
  const pcPresets = {
    home: [15, "Ev ve Ofis kullan\u0131m\u0131 i\u00e7in haz\u0131rlanm\u0131\u015ft\u0131r. 1 y\u0131l garanti."],
    gaming: [20, "Gaming konfig\u00fcrasyonu. Y\u00fcksek FPS odakl\u0131 se\u00e7im. 1 y\u0131l garanti."],
    content: [22, "Yarat\u0131c\u0131 i\u00e7erik \u00fcretimi ve video d\u00fczenleme i\u00e7in optimize edilmi\u015ftir."],
    workstation: [18, "Profesyonel i\u015f istasyonu. ECC RAM ve i\u015f y\u00fck\u00fc optimizasyonu."]
  };
  let pcRows = [];
  let pcParts = [];
  let pcCustomers = [];
  let pcOfferNo = "";
  let pcCustomerId = "";
  let pcMargin = 20;
  let pcVat = 20;
  let pcNote = "";
  let pcInitialized = false;

  const pcText = (value) => String(value ?? "");
  const pcEscape = (value) => esc(pcText(value));
  const pcMoney = (value) => money(Number(value) || 0, "TRY");
  const pcNumber = (value) => Number.isFinite(Number(value)) ? Number(value) : 0;
  const pcSettings = () => desktopSettings || {};
  function pcNewOfferNo() {
    const settings = pcSettings();
    const prefix = String(settings.reference_number_prefix || "REF").trim() || "REF";
    const raw = String(settings.reference_number_next || "1").trim();
    return `${prefix}${/^\d+$/.test(raw) ? raw : "1"}`;
  }
  function pcNewRow(name, category, specLabel, specs) {
    return { key: uid("pc"), name, category, specLabel, specs, brand: "", spec: "", partId: "", qty: 1, price: 0, stock: null };
  }
  function pcTotals() {
    const cost = pcRows.reduce((sum, row) => sum + (Number(row.qty) || 0) * (Number(row.price) || 0), 0);
    const profit = cost * pcMargin / 100;
    const vatBase = cost + profit;
    const vatAmount = vatBase * pcVat / 100;
    return { cost, profit, vatAmount, grand: vatBase + vatAmount };
  }
  function pcRowsMarkup() {
    return pcRows.map((row) => {
      const categoryParts = pcParts.filter((part) => String(part.category || "").trim().toLowerCase() === row.category.toLowerCase());
      const brands = [...new Set(categoryParts.map((part) => String(part.brand || "").trim()).filter(Boolean))].sort();
      const spec = row.spec.toLowerCase();
      const brand = row.brand.toLowerCase();
      const filtered = categoryParts.filter((part) => {
        const haystack = `${part.name || ""} ${part.code || ""} ${part.description || ""} ${part.brand || ""}`.toLowerCase();
        return (!brand || haystack.includes(brand)) && (!spec || String(part.name || "").toLowerCase().includes(spec));
      });
      const options = filtered.map((part) => `<option value="${pcEscape(part.id)}" ${String(part.id) === String(row.partId) ? "selected" : ""}>${pcEscape(part.name || part.part_name)} [${Number(part.qty ?? part.stock) || 0} adet]</option>`).join("");
      const stock = row.stock == null ? "\u2014" : String(row.stock);
      const stockClass = Number(row.stock) > 3 ? "good" : Number(row.stock) > 0 ? "warn" : "bad";
      return `<div class="pc-component-row" data-pc-row="${pcEscape(row.key)}"><strong class="pc-component-name">${pcEscape(row.name)}</strong><select data-pc-brand aria-label="${pcEscape(row.name)} marka"><option value="">T\u00fcm Markalar</option>${brands.map((item) => `<option ${item.toLowerCase() === brand ? "selected" : ""}>${pcEscape(item)}</option>`).join("")}</select><select data-pc-spec aria-label="${pcEscape(row.specLabel)}"><option value="">\u2014 ${pcEscape(row.specLabel)} \u2014</option>${row.specs.map((item) => `<option ${item.toLowerCase() === spec ? "selected" : ""}>${pcEscape(item)}</option>`).join("")}</select><select data-pc-product aria-label="${pcEscape(row.name)} \u00fcr\u00fcn"><option value="">${filtered.length ? `\u2014 \u00dcr\u00fcn Se\u00e7 (${filtered.length} \u00fcr\u00fcn) \u2014` : "\u2014 Stokta yok \u2014"}</option>${options}</select><input data-pc-qty type="number" min="1" step="1" value="${pcEscape(row.qty)}" aria-label="Adet"><input data-pc-price type="number" min="0" step="0.01" value="${pcEscape(row.price)}" aria-label="Birim fiyat"><strong class="pc-row-total">${pcMoney((Number(row.qty) || 0) * (Number(row.price) || 0))}</strong><span class="pc-stock ${stockClass}">${pcEscape(stock)}</span><button type="button" class="icon-btn pc-remove" data-pc-remove aria-label="Bile\u015feni kald\u0131r">&times;</button></div>`;
    }).join("");
  }
  function pcRender() {
    const totals = pcTotals();
    const customerOptions = pcCustomers.map((customer) => `<option value="${pcEscape(customer.id)}" ${String(customer.id) === String(pcCustomerId) ? "selected" : ""}>${pcEscape(customer.name)}</option>`).join("");
    const vatOptions = [...new Set([0, 1, 8, 18, 20, pcVat])].sort((a, b) => a - b);
    $("#content").innerHTML = `<section class="pc-builder-page"><header class="pc-builder-header"><div><h2>\u25a3 Bilgisayar Topla</h2><p>Bile\u015fen se\u00e7 \u00b7 Fiyatland\u0131r \u00b7 Teklif olu\u015ftur \u00b7 Sat\u0131\u015fa d\u00f6n\u00fc\u015ft\u00fcr</p></div><div class="pc-offer-meta"><strong>Teklif No: ${pcEscape(pcOfferNo)}</strong><span>Tarih: ${new Date().toLocaleDateString("tr-TR")}</span></div></header><div class="pc-customer-bar"><label>M\u00fc\u015fteri se\u00e7in<select id="pcCustomer"><option value="">M\u00fc\u015fteri se\u00e7ilmedi</option>${customerOptions}</select></label><button type="button" class="secondary" data-pc-action="customer">M\u00fc\u015fteri 360</button></div><div class="pc-preset-bar"><span>H\u0131zl\u0131 \u015eablon:</span><button type="button" data-pc-preset="home">\u2302 Ev & Ofis</button><button type="button" data-pc-preset="gaming">Gaming</button><button type="button" data-pc-preset="content">\u25c8 \u0130\u00e7erik \u00dcretici</button><button type="button" data-pc-preset="workstation">\u25a3 \u0130\u015f \u0130stasyonu</button><button type="button" data-pc-preset="clear">Temizle</button><button type="button" class="success" data-pc-action="add-component">+ Bile\u015fen Ekle</button></div><div class="pc-component-head"><span>Bile\u015fen</span><span>Marka</span><span>\u00d6zellik</span><span>\u00dcr\u00fcn (Stoktan)</span><span>Adet</span><span>Birim Fiyat</span><span>Toplam</span><span>Stok</span><span></span></div><div class="pc-components" id="pcComponents">${pcRowsMarkup()}</div><section class="pc-summary"><div><span>Maliyet Toplam\u0131</span><strong id="pcCost">${pcMoney(totals.cost)}</strong></div><label>KDV<select id="pcVat">${vatOptions.map((value) => `<option value="${value}" ${value === pcVat ? "selected" : ""}>${value ? `KDV %${value}` : "KDV Yok"}</option>`).join("")}</select></label><div><span>KDV Tutar\u0131</span><strong id="pcVatAmount">${pcMoney(totals.vatAmount)}</strong></div><label>K\u00e2r Marj\u0131<input id="pcMargin" type="number" min="0" max="500" step="0.1" value="${pcEscape(pcMargin)}">%</label><div><span>K\u00e2r</span><strong class="pc-profit" id="pcProfit">+${pcMoney(totals.profit)}</strong></div><div class="pc-grand"><span>Genel Toplam</span><strong id="pcGrand">${pcMoney(totals.grand)}</strong></div><label class="pc-note">Teklif Notu<textarea id="pcNote" placeholder="M\u00fc\u015fteriye iletilecek notlar, garanti \u015fartlar\u0131, kurulum \u00fccreti vb.">${pcEscape(pcNote)}</textarea></label></section><div class="pc-actions"><button type="button" data-pc-action="pdf">\u25a7 PDF Teklif</button><button type="button" data-pc-action="customer-note">\u263a M\u00fc\u015fteri 360 Kayd\u0131</button><button type="button" data-pc-action="stock">\u25a3 Stok D\u00fc\u015f\u00fcr</button><button type="button" data-pc-action="finance">\u20ba Finans Kayd\u0131</button><button type="button" data-pc-action="save">Sipari\u015f Kaydet</button><button type="button" class="danger" data-pc-action="clear">Temizle</button></div></section>`;
  }
  function pcRefreshTotals() {
    const totals = pcTotals();
    const cost = $("#pcCost"); if (!cost) return;
    cost.textContent = pcMoney(totals.cost);
    $("#pcProfit").textContent = `+${pcMoney(totals.profit)}`;
    $("#pcVatAmount").textContent = pcMoney(totals.vatAmount);
    $("#pcGrand").textContent = pcMoney(totals.grand);
    pcRows.forEach((row) => { const node = document.querySelector(`[data-pc-row="${CSS.escape(row.key)}"] .pc-row-total`); if (node) node.textContent = pcMoney((Number(row.qty) || 0) * (Number(row.price) || 0)); });
  }
  function pcSelectedCustomer() { return pcCustomers.find((item) => String(item.id) === String(pcCustomerId || $("#pcCustomer")?.value || "")); }
  function pcFilledRows() { return pcRows.filter((row) => row.partId && Number(row.qty) > 0).map((row) => { const part = pcParts.find((item) => String(item.id) === String(row.partId)); return { component: row.name, category: row.category, product: part?.name || part?.part_name || "", part_id: row.partId, stock: Number(row.stock) || 0, qty: Number(row.qty) || 0, unit_price: Number(row.price) || 0, total: (Number(row.qty) || 0) * (Number(row.price) || 0) }; }); }
  function pcRequireRows() { const rows = pcFilledRows(); if (!rows.length) { toast("L\u00fctfen en az bir bile\u015fen se\u00e7in.", "error"); return null; } return rows; }
  function pcClear() { pcRows = pcDefaults.map((item) => pcNewRow(...item)); pcOfferNo = pcNewOfferNo(); pcCustomerId = ""; pcMargin = 20; pcNote = ""; pcRender(); }
  function pcApplyPreset(key) { if (key === "clear") return pcClear(); const preset = pcPresets[key]; if (!preset) return; pcMargin = preset[0]; pcNote = preset[1]; pcRender(); }
  async function pcSaveNote(type) {
    const rows = pcRequireRows(); if (!rows) return;
    const customer = pcSelectedCustomer(); if (!customer) { toast("Kay\u0131t i\u00e7in \u00f6nce m\u00fc\u015fteri se\u00e7in.", "error"); return; }
    const totals = pcTotals();
    const lines = rows.map((row) => `${row.component}: ${row.product} x${row.qty} ${pcMoney(row.unit_price)} = ${pcMoney(row.total)}`).join("\n");
    const content = `[PC Teklif Kayd\u0131] No: ${pcOfferNo}\nM\u00fc\u015fteri: ${customer.name}\n\nBile\u015fenler:\n${lines}\n\nMaliyet: ${pcMoney(totals.cost)} | K\u00e2r Marj\u0131: ${pcMargin}% | KDV: %${pcVat} | Toplam: ${pcMoney(totals.grand)}\nNot: ${pcNote}`;
    await apiFetch("/api/desktop/table/customer_notes", { method: "POST", body: JSON.stringify({ customer_id: Number(customer.id) || customer.id, note_type: type, type, title: `PC Teklif #${pcOfferNo}`, content, created_at: new Date().toISOString() }) });
    toast(`Teklif #${pcOfferNo} m\u00fc\u015fteri kayd\u0131na eklendi.`, "success");
  }
  async function pcDeductStock() {
    const rows = pcRequireRows(); if (!rows) return;
    const insufficient = rows.filter((row) => row.qty > row.stock);
    if (insufficient.length) { toast(`Yetersiz stok: ${insufficient.map((row) => row.product).join(", ")}`, "error"); return; }
    await apiFetch("/api/desktop/pc-builder/deduct-stock", { method: "POST", body: JSON.stringify({ reference: pcOfferNo, items: rows.map((row) => ({ part_id: row.part_id, quantity: row.qty })) }) });
    toast(`${rows.length} \u00fcr\u00fcn stoktan d\u00fc\u015f\u00fcld\u00fc.`, "success");
    await pcLoad();
  }
  async function pcAddFinance() {
    const rows = pcRequireRows(); if (!rows) return;
    const customer = pcSelectedCustomer(); const totals = pcTotals();
    await apiFetch("/api/desktop/table/accounting", { method: "POST", body: JSON.stringify({ type: "Gelir", category: "Sat\u0131\u015f", amount: totals.grand, description: `Bilgisayar Topla / Teklif #${pcOfferNo}`, customer_name: customer?.name || "", customer_id: customer ? Number(customer.id) || customer.id : null, payment_method: "Nakit", currency: "TRY", date: new Date().toISOString() }) });
    toast(`Finans kayd\u0131 olu\u015fturuldu: ${pcMoney(totals.grand)}`, "success");
  }
  function pcPrint() {
    if (!pcRequireRows()) return;
    const totals = pcTotals(); const rows = pcFilledRows(); const customer = pcSelectedCustomer();
    const printWindow = window.open("", "_blank", "width=900,height=700");
    if (!printWindow) { toast("Yazd\u0131rma penceresi taray\u0131c\u0131 taraf\u0131ndan engellendi.", "error"); return; }
    printWindow.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>PC Teklif ${pcEscape(pcOfferNo)}</title><style>body{font:14px Arial,sans-serif;margin:36px;color:#172033}h1{margin:0 0 5px}small{color:#667085}table{width:100%;border-collapse:collapse;margin:24px 0}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left}td:last-child,th:last-child{text-align:right}.sum{margin-left:auto;width:300px}.sum div{display:flex;justify-content:space-between;padding:5px}.total{font-size:20px;font-weight:bold;border-top:2px solid #333;margin-top:8px;padding-top:12px}pre{white-space:pre-wrap}</style></head><body><h1>Bilgisayar Teklif Formu</h1><small>${pcEscape(pcOfferNo)} · ${new Date().toLocaleDateString("tr-TR")} · ${pcEscape(customer?.name || "M\u00fc\u015fteri belirtilmedi")}</small><table><thead><tr><th>Bile\u015fen</th><th>\u00dcr\u00fcn</th><th>Adet</th><th>Birim Fiyat</th><th>Toplam</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${pcEscape(row.component)}</td><td>${pcEscape(row.product)}</td><td>${row.qty}</td><td>${pcMoney(row.unit_price)}</td><td>${pcMoney(row.total)}</td></tr>`).join("")}</tbody></table><div class="sum"><div><span>Maliyet</span><b>${pcMoney(totals.cost)}</b></div><div><span>K\u00e2r (${pcMargin}%)</span><b>${pcMoney(totals.profit)}</b></div><div><span>KDV (%${pcVat})</span><b>${pcMoney(totals.vatAmount)}</b></div><div class="total"><span>Genel Toplam</span><b>${pcMoney(totals.grand)}</b></div></div><h3>Teklif Notu</h3><pre>${pcEscape(pcNote)}</pre><script>window.onload=()=>window.print()<\/script></body></html>`);
    printWindow.document.close();
  }
  async function pcLoad() {
    try {
      if (!pcInitialized) {
        pcMargin = 20;
        pcVat = Math.max(0, Math.min(100, Number(desktopSettings?.default_vat_percent ?? 20) || 0));
        pcInitialized = true;
      }
      const [parts, customers] = await Promise.all([apiFetch("/api/desktop/table/parts?limit=1000"), apiFetch("/api/desktop/table/customers?limit=1000")]);
      pcParts = (parts.rows || []).map((part) => ({ ...part, qty: Number(part.stock) || 0 }));
      pcCustomers = customers.rows || db.customers || [];
      window.__pcBuilderParts = pcParts;
      pcRender();
    } catch (error) {
      const componentHost = $("#pcComponents") || $(".pc-builder-page") || $("#content");
      if (componentHost) componentHost.innerHTML = `<div class="empty-state"><strong>Stok verisi y\u00fcklenemedi</strong><span>${pcEscape(error.message)}</span></div>`;
    }
  }
  const pcBaseRender = render;
  render = function () {
    if (page !== "pc-builder") return pcBaseRender();
    document.body.dataset.page = page;
    $("#content").innerHTML = "<section class=\"pc-builder-page\"><div class=\"pc-loading\">Bile\u015fen ve m\u00fc\u015fteri verileri y\u00fckleniyor\u2026</div></section>";
    if (!pcOfferNo) { pcOfferNo = pcNewOfferNo(); pcRows = pcDefaults.map((item) => pcNewRow(...item)); }
    pcLoad();
  };
  document.addEventListener("click", async (event) => {
    const preset = event.target.closest("[data-pc-preset]");
    if (preset) { pcApplyPreset(preset.dataset.pcPreset); return; }
    const remove = event.target.closest("[data-pc-remove]");
    if (remove) { pcRows = pcRows.filter((row) => row.key !== remove.closest("[data-pc-row]").dataset.pcRow); pcRender(); return; }
    const action = event.target.closest("[data-pc-action]")?.dataset.pcAction;
    if (!action) return;
    try {
      if (action === "clear") pcClear();
      if (action === "add-component") openDialog("Bile\u015fen Ekle", "PC YAPILANDIRICI", `<div class="form-grid"><div class="field"><label>Bile\u015fen ad\u0131</label><input name="name" required></div><div class="field"><label>Stok kategorisi</label><input name="category" required></div><div class="field full"><label>\u00d6zellik se\u00e7enekleri (virg\u00fcl ile ay\u0131r\u0131n)</label><input name="specs" placeholder="ATX, mATX, ITX"></div></div>`, (form) => { const name = String(form.get("name") || "").trim(); const category = String(form.get("category") || "").trim(); if (!name || !category) throw Error("Bile\u015fen ad\u0131 ve stok kategorisi zorunludur."); pcRows.push(pcNewRow(name, category, "\u00d6zellik", String(form.get("specs") || "").split(",").map((item) => item.trim()).filter(Boolean))); pcRender(); return true; }, "Bile\u015fen Ekle");
      if (action === "pdf") pcPrint();
      if (action === "customer") { const customer = pcSelectedCustomer(); if (customer) customer360(db.customers.find((item) => String(item.id) === String(customer.id)) || customer); else toast("M\u00fc\u015fteri se\u00e7in.", "warning"); }
      if (action === "customer-note") await pcSaveNote("PC Teklif");
      if (action === "save") await pcSaveNote("Teklif");
      if (action === "stock") await pcDeductStock();
      if (action === "finance") await pcAddFinance();
    } catch (error) { toast(error.message, "error"); }
  });
  document.addEventListener("change", (event) => {
    if (page !== "pc-builder") return;
    if (event.target.id === "pcCustomer") { pcCustomerId = event.target.value; return; }
    const rowElement = event.target.closest("[data-pc-row]");
    if (rowElement) {
      const row = pcRows.find((item) => item.key === rowElement.dataset.pcRow); if (!row) return;
      if (event.target.matches("[data-pc-brand]")) row.brand = event.target.value;
      if (event.target.matches("[data-pc-spec]")) row.spec = event.target.value;
      if (event.target.matches("[data-pc-product]")) { row.partId = event.target.value; const part = pcParts.find((item) => String(item.id) === String(row.partId)); row.price = Number(part?.price) || 0; row.stock = part ? Number(part.qty) || 0 : null; }
      if (event.target.matches("[data-pc-qty]")) row.qty = Math.max(1, Number(event.target.value) || 1);
      if (event.target.matches("[data-pc-price]")) row.price = Math.max(0, Number(event.target.value) || 0);
      if (event.target.matches("[data-pc-brand], [data-pc-spec]")) pcRender(); else pcRefreshTotals();
    }
    if (event.target.id === "pcVat") { pcVat = Number(event.target.value) || 0; pcRefreshTotals(); }
  });
  document.addEventListener("input", (event) => {
    if (page !== "pc-builder") return;
    const rowElement = event.target.closest("[data-pc-row]");
    const row = rowElement && pcRows.find((item) => item.key === rowElement.dataset.pcRow);
    if (row && event.target.matches("[data-pc-qty]")) { row.qty = Math.max(1, Number(event.target.value) || 1); pcRefreshTotals(); }
    if (row && event.target.matches("[data-pc-price]")) { row.price = Math.max(0, Number(event.target.value) || 0); pcRefreshTotals(); }
    if (event.target.id === "pcMargin") { pcMargin = Math.min(500, Math.max(0, Number(event.target.value) || 0)); pcRefreshTotals(); }
    if (event.target.id === "pcNote") pcNote = event.target.value;
  });
})();
