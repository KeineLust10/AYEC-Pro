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
  const pcCommonBrands = {
    "Anakart": ["ASUS", "MSI", "Gigabyte", "ASRock", "Biostar"],
    "\u0130\u015flemci": ["Intel", "AMD"],
    "RAM": ["Corsair", "Kingston", "G.Skill", "Samsung", "Crucial", "HyperX", "TeamGroup"],
    "SSD": ["Samsung", "WD", "Seagate", "Crucial", "Kingston", "Sabrent", "Corsair", "ADATA"],
    "HDD": ["Seagate", "WD", "Toshiba", "HGST"],
    "Ekran Kart\u0131": ["ASUS", "MSI", "Gigabyte", "Zotac", "Sapphire", "PowerColor", "EVGA", "PNY"],
    "CPU So\u011futucu": ["Noctua", "be quiet!", "Corsair", "Cooler Master", "DeepCool", "Arctic", "Thermalright"],
    "G\u00fc\u00e7 Kayna\u011f\u0131": ["Corsair", "Seasonic", "be quiet!", "EVGA", "Cooler Master", "Thermaltake", "FSP"],
    "Kasa": ["Fractal Design", "Phanteks", "NZXT", "Corsair", "Lian Li", "Cooler Master", "be quiet!"],
    "Monit\u00f6r": ["LG", "Samsung", "ASUS", "BenQ", "AOC", "Dell", "ViewSonic"],
    "Klavye": ["Logitech", "Corsair", "Razer", "HyperX", "SteelSeries", "Ducky"],
    "Mouse": ["Logitech", "Razer", "Corsair", "SteelSeries", "Zowie"],
    "Yaz\u0131l\u0131m": ["Microsoft", "OEM"],
    "Aksesuar": ["Noctua", "Thermal Grizzly", "Arctic", "Di\u011fer"]
  };
  function pcNormalizeBrand(value) {
    return String(value || "").toLocaleLowerCase("tr-TR").replace(/[\u0131\u0130]/g, "i").replace(/\u011f/g, "g").replace(/\u015f/g, "s").replace(/\u00fc/g, "u").replace(/\u00f6/g, "o").replace(/\u00e7/g, "c").replace(/[!.]/g, " ").replace(/[^a-z0-9]+/g, " ").trim().replace(/\s+/g, " ");
  }
  function pcBrandMatches(brand, text) {
    const normalized = pcNormalizeBrand(brand);
    const name = pcNormalizeBrand(text);
    if (!normalized || name.includes(normalized)) return true;
    const aliases = { "g skill": ["gskill"], "be quiet": ["bequiet"], "cooler master": ["coolermaster"], "fractal design": ["fractal"], "thermal grizzly": ["grizzly"], "teamgroup": ["team group"] };
    return (aliases[normalized] || []).some((alias) => name.includes(alias) || name.replace(/ /g, "").includes(alias));
  }
  function pcBrandOptions(parts, category) {
    const common = pcCommonBrands[category] || [];
    const brands = new Set(common);
    const special = new Set(["Fractal Design", "Cooler Master", "Thermal Grizzly", "be quiet!"]);
    for (const part of parts) {
      const name = String(part.name || part.part_name || "").trim();
      for (const brand of common) if (pcBrandMatches(brand, name)) brands.add(brand);
      const words = name.split(/\s+/).filter(Boolean);
      for (const candidate of [words.slice(0, 2).join(" "), words[0] || ""]) {
        if (candidate && candidate.length > 1 && !/^\d+$/.test(candidate) && ((candidate.toUpperCase() === candidate && candidate.length <= 8) || special.has(candidate))) brands.add(candidate);
      }
    }
    return [...brands].sort((a, b) => pcNormalizeBrand(a).localeCompare(pcNormalizeBrand(b)));
  }
  function pcSelectedPartMatches(row) {
    const part = pcParts.find((item) => String(item.id) === String(row.partId));
    if (!part) return false;
    const name = String(part.name || part.part_name || "");
    const haystack = `${name} ${part.code || ""} ${part.description || ""}`;
    return (!row.brand || pcBrandMatches(row.brand, haystack)) && (!row.spec || name.toLowerCase().includes(row.spec.toLowerCase()));
  }
  const pcPresets = {
    home: [15, "Ev ve Ofis kullan\u0131m\u0131 i\u00e7in haz\u0131rlanm\u0131\u015ft\u0131r. 1 y\u0131l garanti."],
    gaming: [20, "Gaming konfig\u00fcrasyonu. Y\u00fcksek FPS odakl\u0131 se\u00e7im. 1 y\u0131l garanti."],
    content: [22, "Yarat\u0131c\u0131 i\u00e7erik \u00fcretimi \u0026 video d\u00fczenleme i\u00e7in optimize edilmi\u015ftir."],
    workstation: [18, "Profesyonel i\u015f istasyonu. ECC RAM \u0026 i\u015f y\u00fck\u00fc optimizasyonu."]
  };
  let pcRows = [];
  let pcParts = [];
  let pcCustomers = [];
  let pcOfferNo = "";
  let pcCustomerId = "";
  let pcCustomerSearch = "";
  let pcMargin = 20;
  let pcVat = 20;
  let pcNote = "";
  let pcInitialized = false;

  const pcText = (value) => String(value ?? "");
  const pcEscape = (value) => esc(pcText(value));
  const pcNativeNumber = (value) => (Number(value) || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const pcMoney = (value) => `${pcNativeNumber(value)} \u20ba`;
  const pcNativeDateTime = (value) => {
    const date = value instanceof Date ? value : new Date(value);
    return `${String(date.getDate()).padStart(2, "0")}.${String(date.getMonth() + 1).padStart(2, "0")}.${date.getFullYear()} ${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
  };
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
      const brands = pcBrandOptions(categoryParts, row.category);
      const spec = row.spec.toLowerCase();
      const brand = row.brand;
      const filtered = categoryParts.filter((part) => {
        const haystack = `${part.name || part.part_name || ""} ${part.code || ""} ${part.description || ""}`;
        return (!brand || pcBrandMatches(brand, haystack)) && (!spec || String(part.name || part.part_name || "").toLowerCase().includes(spec));
      });
      const options = filtered.map((part) => `<option value="${pcEscape(part.id)}" ${String(part.id) === String(row.partId) ? "selected" : ""}>${pcEscape(part.name || part.part_name)} [${Number(part.qty ?? part.stock) || 0} adet]</option>`).join("");
      const stock = row.stock == null ? "\u2014" : String(row.stock);
      const stockClass = Number(row.stock) > 3 ? "good" : Number(row.stock) > 0 ? "warn" : "bad";
      return `<div class="pc-component-row" data-pc-row="${pcEscape(row.key)}"><strong class="pc-component-name">${pcEscape(row.name)}</strong><select data-pc-brand aria-label="${pcEscape(row.name)} marka"><option value="">T\u00fcm Markalar</option>${brands.map((item) => `<option ${item.toLowerCase() === brand ? "selected" : ""}>${pcEscape(item)}</option>`).join("")}</select><select data-pc-spec aria-label="${pcEscape(row.specLabel)}"><option value="">\u2014 ${pcEscape(row.specLabel)} \u2014</option>${row.specs.map((item) => `<option ${item.toLowerCase() === spec ? "selected" : ""}>${pcEscape(item)}</option>`).join("")}</select><select data-pc-product aria-label="${pcEscape(row.name)} \u00fcr\u00fcn"><option value="">${filtered.length ? `\u2014 \u00dcr\u00fcn Se\u00e7 (${filtered.length} \u00fcr\u00fcn) \u2014` : "\u2014 Stokta yok \u2014"}</option>${options}</select><div class="pc-inline-stepper" data-pc-stepper="qty"><button type="button" data-pc-step="qty" data-pc-delta="-1" aria-label="Adedi azalt">-</button><input data-pc-qty type="number" min="0" max="99" step="1" value="${pcEscape(row.qty)}" aria-label="Adet"><button type="button" data-pc-step="qty" data-pc-delta="1" aria-label="Adedi artir">+</button></div><div class="pc-inline-stepper pc-price-stepper" data-pc-stepper="price"><button type="button" data-pc-step="price" data-pc-delta="-1" aria-label="Fiyati azalt">-</button><input data-pc-price type="text" inputmode="decimal" maxlength="9" value="${pcEscape((Number(row.price) || 0).toFixed(2))}" aria-label="Birim fiyat"><span class="pc-stepper-suffix">\u20ba</span><button type="button" data-pc-step="price" data-pc-delta="1" aria-label="Fiyati artir">+</button></div><strong class="pc-row-total">${pcMoney((Number(row.qty) || 0) * (Number(row.price) || 0))}</strong><span class="pc-stock ${stockClass}">${pcEscape(stock)}</span><button type="button" class="icon-btn pc-remove" data-pc-remove aria-label="Bile\u015feni kald\u0131r">&#x2715;</button></div>`;
    }).join("");
  }
  function pcRefreshOfferCustomer() {
    const customer = pcCustomers.find((item) => String(item.id) === String(pcCustomerId));
    const label = document.querySelector(".pc-offer-meta strong");
    if (label) label.textContent = `Teklif No: ${pcOfferNo}${customer ? `  |  M\u00fc\u015fteri: ${customer.name || ""}` : ""}`;
  }
  function pcRender() {
    const totals = pcTotals();
    const customerQuery = pcCustomerSearch.trim().toLocaleLowerCase("tr-TR");
    const visibleCustomers = pcCustomers.filter((customer) => !customerQuery || String(customer.name || "").toLocaleLowerCase("tr-TR").includes(customerQuery));
    const customerOptions = visibleCustomers.map((customer) => `<option value="${pcEscape(customer.id)}" ${String(customer.id) === String(pcCustomerId) ? "selected" : ""}>${pcEscape(customer.name)}</option>`).join("");
    const selectedCustomer = pcCustomers.find((customer) => String(customer.id) === String(pcCustomerId));
    const offerLabel = `Teklif No: ${pcOfferNo}${selectedCustomer ? `  |  M\u00fc\u015fteri: ${selectedCustomer.name || ""}` : ""}`;
    const vatOptions = [...new Set([0, 1, 8, 18, 20, pcVat])].sort((a, b) => a - b);
    const workflowTabs = window.ayecSalesWorkflowTabs ? window.ayecSalesWorkflowTabs("computer") : "";
    $("#content").innerHTML = `${workflowTabs}<section class="pc-builder-page"><header class="pc-builder-header"><div><h2><span class="pc-builder-title-icon" aria-hidden="true"><svg viewBox="0 0 28 28" width="28" height="28" focusable="false"><rect x="2" y="2" width="24" height="16" rx="2" fill="#2563eb"/><rect x="4" y="4" width="20" height="12" rx="1" fill="#7dd3fc"/><path d="M11 18v3H8v2h12v-2h-3v-3" fill="#94a3b8"/></svg></span>Bilgisayar Topla</h2><p>Bile\u015fen se\u00e7 \u00b7 Fiyatland\u0131r \u00b7 Teklif olu\u015ftur \u00b7 Sat\u0131\u015fa d\u00f6n\u00fc\u015ft\u00fcr</p></div><div class="pc-offer-meta"><strong>${pcEscape(offerLabel)}</strong><span>Tarih: ${new Date().toLocaleDateString("tr-TR")}</span></div></header><div class="pc-customer-bar"><span class="pc-customer-icon" aria-hidden="true">\ud83d\udc64</span><input id="pcCustomerSearch" type="search" value="${pcEscape(pcCustomerSearch)}" aria-label="M\u00fc\u015fteri ara" placeholder="M\u00fc\u015fteri ara veya se\u00e7..."><select id="pcCustomer" aria-label="M\u00fc\u015fteri se\u00e7in"><option value="">M\u00fc\u015fteri se\u00e7ilmedi</option>${customerOptions}</select></div><div class="pc-preset-bar"><span>H\u0131zl\u0131 \u015eablon:</span><button type="button" data-pc-preset="home">\ud83c\udfe0 Ev & Ofis</button><button type="button" data-pc-preset="gaming">\ud83c\udfae Gaming</button><button type="button" data-pc-preset="content">\ud83c\udfa8 \u0130\u00e7erik \u00dcretici</button><button type="button" data-pc-preset="workstation">\ud83d\udda5 \u0130\u015f \u0130stasyonu</button><button type="button" data-pc-preset="clear">\ud83e\uddf9 Temizle</button><button type="button" class="success" data-pc-action="add-component">+ Bile\u015fen Ekle</button></div><div class="pc-table-scroll" data-pc-table-scroll tabindex="0" role="region" aria-label="Bile\u015fen tablosu"><div class="pc-component-head"><span>Bile\u015fen</span><span>Marka</span><span>\u00d6zellik</span><span>\u00dcr\u00fcn (Stoktan)</span><span>Adet</span><span>Birim Fiyat</span><span>Toplam</span><span>Stok</span><span></span></div><div class="pc-components" id="pcComponents">${pcRowsMarkup()}</div></div><section class="pc-summary"><div><span>Maliyet Toplam\u0131:</span><strong id="pcCost">${pcMoney(totals.cost)}</strong></div><label class="pc-vat"><span>KDV:</span><select id="pcVat">${vatOptions.map((value) => `<option value="${value}" ${value === pcVat ? "selected" : ""}>${value ? `KDV %${value}` : "KDV Yok"}</option>`).join("")}</select></label><div><span>KDV Tutar\u0131:</span><strong id="pcVatAmount">${pcMoney(totals.vatAmount)}</strong></div><label class="pc-margin"><span>K\u00e2r Marj\u0131:</span><input id="pcMargin" type="number" min="0" max="500" step="0.1" value="${pcEscape(pcMargin)}"><span class="pc-margin-suffix">%</span></label><div><span>K\u00e2r:</span><strong class="pc-profit" id="pcProfit">+${pcMoney(totals.profit)}</strong></div><div class="pc-grand"><span>Genel Toplam:</span><strong id="pcGrand">${pcMoney(totals.grand)}</strong></div><label class="pc-note"><span>Teklif Notu:</span><textarea id="pcNote" placeholder="M\u00fc\u015fteriye iletilecek notlar, garanti \u015fartlar\u0131, kurulum \u00fccreti vb.">${pcEscape(pcNote)}</textarea></label></section><div class="pc-actions"><button type="button" data-pc-action="pdf">\u25a7 PDF Teklif</button><button type="button" data-pc-action="customer">M\u00fc\u015fteri 360</button><button type="button" data-pc-action="stock">\u25a3 Stok D\u00fc\u015f\u00fcr</button><button type="button" data-pc-action="finance">\u20ba Finans Kayd\u0131</button><button type="button" data-pc-action="save">Sipari\u015f Kaydet</button><button type="button" class="danger" data-pc-action="clear">Temizle</button></div></section>`;
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
  function pcFilledRows() { return pcRows.filter((row) => row.partId && Number(row.qty) > 0).map((row) => { const part = pcParts.find((item) => String(item.id) === String(row.partId)); return { component: row.name, category: row.category, brand: part?.brand || row.brand || "", product: part?.name || part?.part_name || "", part_id: row.partId, stock: Number(row.stock) || 0, qty: Number(row.qty) || 0, unit_price: Number(row.price) || 0, total: (Number(row.qty) || 0) * (Number(row.price) || 0) }; }); }
  function pcRequireRows() { const rows = pcFilledRows(); if (!rows.length) { toast("L\u00fctfen en az bir bile\u015fen se\u00e7in.", "error"); return null; } return rows; }
  function pcSetQuantity(row, input) { const qty = Math.min(99, Math.max(0, Math.trunc(Number(input.value) || 0))); row.qty = qty; if (input.value !== String(qty)) input.value = String(qty); }
  function pcSetPrice(row, input) { const parsed = Number(String(input.value || "").replace(",", ".")); const price = Math.min(999999, Math.max(0, Math.round((Number.isFinite(parsed) ? parsed : 0) * 100) / 100)); row.price = price; input.value = price.toFixed(2); }
  function pcClear() { pcRows = pcDefaults.map((item) => pcNewRow(...item)); pcOfferNo = pcNewOfferNo(); pcCustomerId = ""; pcCustomerSearch = ""; pcMargin = 20; pcNote = ""; pcRender(); }
  function pcApplyPreset(key) { if (key === "clear") return pcClear(); const preset = pcPresets[key]; if (!preset) return; pcMargin = preset[0]; pcNote = preset[1]; pcRender(); }
  async function pcSaveNote(type) {
    const rows = pcRequireRows(); if (!rows) return;
    const customer = pcSelectedCustomer(); if (!customer) { toast("Kay\u0131t i\u00e7in \u00f6nce m\u00fc\u015fteri se\u00e7in.", "error"); return; }
    const totals = pcTotals();
    const lines = rows.map((row) => `\u2022 ${row.component}: ${row.product}  x${row.qty}  ${pcNativeNumber(row.unit_price)}\u20ba`).join("\n");
    const content = `[Bilgisayar Teklifi #${pcOfferNo}]\n${lines}\nTeklif Toplam\u0131: ${pcNativeNumber(totals.grand)} \u20ba\n${pcNote}`;
    try {
      await apiFetch("/api/desktop/table/customer_notes", { method: "POST", body: JSON.stringify({ customer_id: Number(customer.id) || customer.id, note_type: type, type, title: `PC Teklif #${pcOfferNo}`, content, created_at: new Date().toISOString() }) });
    } catch (error) {
      toast(`M\u00fc\u015fteri kayd\u0131 eklenemedi: ${error?.message || error}`, "error");
      return;
    }
    toast(`Teklif #${pcOfferNo} m\u00fc\u015fteri kayd\u0131na eklendi.`, "success");
    return customer;
  }
  async function pcSaveOffer() {
    const rows = pcRequireRows(); if (!rows) return;
    try {
      const customer = pcSelectedCustomer(); const totals = pcTotals();
      const lines = rows.map((row) => `  \u2022 ${row.component}: ${row.product}  \u00d7${row.qty}  ${pcNativeNumber(row.unit_price)}\u20ba  = ${pcNativeNumber(row.total)}\u20ba`).join("\n");
      const content = `[PC Teklif Kayd\u0131] No: ${pcOfferNo}\nTarih: ${pcNativeDateTime(new Date())}\nM\u00fc\u015fteri: ${customer?.name || "Belirtilmedi"}\n\nBile\u015fenler:\n${lines}\n\nMaliyet: ${pcNativeNumber(totals.cost)} \u20ba  |  K\u00e2r Marj\u0131: ${pcMargin.toFixed(1)}%  |  KDV: %${pcVat}  |  Toplam: ${pcNativeNumber(totals.grand)} \u20ba\nNot: ${pcNote}`;
      await apiFetch("/api/desktop/table/audit_logs", { method: "POST", body: JSON.stringify({ user_id: "sistem", table_name: "pc_offers", action: "INSERT", details: content.slice(0, 500) }) });
      if (customer) {
        await apiFetch("/api/desktop/table/customer_notes", { method: "POST", body: JSON.stringify({ customer_id: Number(customer.id) || customer.id, note_type: "PC Teklif", type: "PC Teklif", title: `PC Teklif #${pcOfferNo}`, content, created_at: new Date().toISOString() }) });
      }
      toast(`Teklif #${pcOfferNo} kaydedildi.`, "success");
    } catch (error) {
      toast(`Teklif kaydedilemedi: ${error?.message || error}`, "error");
    }
  }
  async function pcDeductStock() {
    const rows = pcRequireRows(); if (!rows) return;
    const grouped = new Map();
    for (const row of rows) {
      const key = String(row.part_id);
      const group = grouped.get(key) || { part_id: row.part_id, quantity: 0, stock: Number(row.stock) || 0, product: row.product, rowCount: 0 };
      group.quantity += row.qty;
      group.stock = Math.min(group.stock, Number(row.stock) || 0);
      group.rowCount += 1;
      grouped.set(key, group);
    }
    const groups = [...grouped.values()];
    const insufficient = groups.filter((group) => group.quantity > group.stock);
    const available = groups.filter((group) => group.quantity <= group.stock);
    if (!available.length) {
      for (const group of insufficient) toast(`${group.product}: Yetersiz stok (${group.stock} var, ${group.quantity} gerekli)`, "error");
      return;
    }
    try {
      await apiFetch("/api/desktop/pc-builder/deduct-stock", { method: "POST", body: JSON.stringify({ reference: pcOfferNo, items: available.map((group) => ({ part_id: group.part_id, quantity: group.quantity })) }) });
    } catch (error) {
      toast(`Stoktan d\u00fc\u015f\u00fclemedi: ${error?.message || error}`, "error");
      return;
    }
    const successCount = available.reduce((sum, group) => sum + group.rowCount, 0);
    if (successCount) toast(`${successCount} \u00fcr\u00fcn stoktan d\u00fc\u015f\u00fcld\u00fc.`, "success");
    for (const group of insufficient) toast(`${group.product}: Yetersiz stok (${group.stock} var, ${group.quantity} gerekli)`, "error");
    await pcLoad();
  }
  async function pcAddFinance() {
    const rows = pcRequireRows(); if (!rows) return;
    const customer = pcSelectedCustomer(); const totals = pcTotals();
    const componentSummary = rows.slice(0, 3).map((row) => row.component).join(", ");
    const description = `Bilgisayar Topla / Teklif #${pcOfferNo} \u2014 ${componentSummary}${rows.length > 3 ? "..." : ""}`;
    try {
      await apiFetch("/api/desktop/table/accounting", { method: "POST", body: JSON.stringify({ type: "Gelir", category: "Sat\u0131\u015f", amount: totals.grand, description, customer_name: customer?.name || "", customer_id: customer ? Number(customer.id) || customer.id : null, payment_method: "Nakit", currency: "TRY", date: new Date().toISOString() }) });
    } catch (error) {
      toast(`Finans kayd\u0131 eklenemedi: ${error?.message || error}`, "error");
      return;
    }
    toast(`Finans kayd\u0131 olu\u015fturuldu: ${pcMoney(totals.grand)}`, "success");
  }
  function pcOpenProformaDialog() {
    const rows = pcRequireRows(); if (!rows) return;
    const customer = pcSelectedCustomer(); const totals = pcTotals();
    const company = String(desktopSettings?.company_name || "").trim();
    const templateOptions = [
      '<option value="modern">Modern (Premium)</option>',
      '<option value="corporate">Kurumsal (Premium)</option>',
      '<option value="minimal">Zebra (Premium)</option>',
      '<option value="bulut_deri">AYEC Pro (Yeni Taslak)</option>'
    ];
    if (String(pcSettings().proforma_editor_html || "").trim()) templateOptions.push('<option value="editor_template">Edit\u00f6r \u015eablonum</option>');
    if (String(pcSettings().proforma_template_uploaded || "0") === "1") templateOptions.push('<option value="custom_template">Ozel PDF Sablonum</option>');
    const body = `<div class="form-grid"><div class="field"><label for="pcPdfCompany">Firma</label><input id="pcPdfCompany" name="company_name" value="${pcEscape(company)}" required></div><div class="field"><label for="pcPdfCustomer">Yetkili</label><input id="pcPdfCustomer" name="customer_name" value="${pcEscape(customer?.name || "Perakende M\u00fc\u015fteri")}" required></div><div class="field"><label for="pcPdfProject">Proje Ad\u0131</label><input id="pcPdfProject" name="project_name" value="${pcEscape(`Bilgisayar Toplama ${pcOfferNo}`)}" required></div><div class="field"><label for="pcPdfCurrency">Teklif Para Birimi</label><select id="pcPdfCurrency" name="currency"><option value="TRY">T\u00fcrk Liras\u0131 (\u20ba)</option><option value="USD">Amerikan Dolar\u0131 ($)</option><option value="EUR">Euro (\u20ac)</option></select></div><div class="field full"><label for="pcPdfTemplate">Tasar\u0131m \u015eablonu</label><select id="pcPdfTemplate" name="template">${templateOptions.join("")}</select></div><div class="field full"><p class="muted">${rows.length} bile\u015fen \u00b7 Maliyet ${pcMoney(totals.cost)} \u00b7 KDV %${pcVat} \u00b7 Genel Toplam ${pcMoney(totals.grand)}</p></div></div>`;
    openDialog("Proforma PDF Olu\u015ftur", "PC YAPILANDIRICI", body, async (form) => {
      const popup = window.open("about:blank", "_blank");
      const payload = {
        company_name: String(form.get("company_name") || "").trim(),
        customer_name: String(form.get("customer_name") || "").trim(),
        project_name: String(form.get("project_name") || "").trim(),
        customer_company: customer?.company_name || "",
        reference_no: pcOfferNo,
        currency: String(form.get("currency") || "TRY"),
        template: String(form.get("template") || "modern"),
        margin_percent: pcMargin,
        vat_percent: pcVat,
        items: rows.map((row) => ({ component: row.component, category: row.category, brand: row.brand, product: row.product, qty: row.qty, price: row.unit_price }))
      };
      let response;
      try { response = await fetch("/api/desktop/pc-builder/proforma.pdf", { method: "POST", headers: { "Content-Type": "application/json" }, credentials: "same-origin", body: JSON.stringify(payload) }); }
      catch (error) { popup?.close(); throw error; }
      if (!response.ok) {
        popup?.close();
        let message = "PDF olu\u015fturulamad\u0131.";
        try { message = (await response.json()).error || message; } catch (_) {}
        throw Error(message);
      }
      const fileUrl = URL.createObjectURL(await response.blob());
      if (popup) { popup.location.replace(fileUrl); setTimeout(() => URL.revokeObjectURL(fileUrl), 60000); }
      else { const link = document.createElement("a"); link.href = fileUrl; link.download = `${pcOfferNo}-proforma.pdf`; link.click(); setTimeout(() => URL.revokeObjectURL(fileUrl), 60000); }
      toast("Proforma PDF olu\u015fturuldu.", "success");
      return true;
    }, "PDF Olu\u015ftur");
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
      for (const row of pcRows) {
        const selected = pcParts.find((part) => String(part.id) === String(row.partId));
        if (selected) { row.stock = Number(selected.qty) || 0; row.price = Number(selected.price) || 0; }
      }
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
    const step = event.target.closest("[data-pc-step]");
    if (step) {
      const rowElement = step.closest("[data-pc-row]");
      const row = pcRows.find((item) => item.key === rowElement?.dataset.pcRow);
      const kind = step.dataset.pcStep;
      const input = rowElement?.querySelector(kind === "qty" ? "[data-pc-qty]" : "[data-pc-price]");
      if (!row || !input) return;
      input.value = String((Number(input.value) || 0) + Number(step.dataset.pcDelta || 0));
      if (kind === "qty") pcSetQuantity(row, input); else pcSetPrice(row, input);
      pcRefreshTotals();
      return;
    }
    const remove = event.target.closest("[data-pc-remove]");
    if (remove) { pcRows = pcRows.filter((row) => row.key !== remove.closest("[data-pc-row]").dataset.pcRow); pcRender(); return; }
    const action = event.target.closest("[data-pc-action]")?.dataset.pcAction;
    if (!action) return;
    try {
      if (action === "clear") pcClear();
      if (action === "add-component") openDialog("Bile\u015fen Ekle", "PC YAPILANDIRICI", `<div class="form-grid"><div class="field"><label>Bile\u015fen ad\u0131</label><input name="name" required></div><div class="field"><label>Stok kategorisi</label><input name="category" required></div><div class="field full"><label>\u00d6zellik etiketi</label><input name="spec" value="Standart" placeholder="Tip, Ba\u011flant\u0131, H\u0131z"></div></div>`, (form) => { const name = String(form.get("name") || "").trim(); const category = String(form.get("category") || "").trim(); const spec = String(form.get("spec") || "").trim() || "Tip"; if (!name || !category) throw Error("Bile\u015fen ad\u0131 ve stok kategorisi zorunludur."); pcRows.push(pcNewRow(name, category, spec, ["Standart"])); pcRender(); return true; }, "Bile\u015fen Ekle");
      if (action === "pdf") pcOpenProformaDialog();
      if (action === "customer") { const customer = await pcSaveNote("Teklif"); if (customer) customer360(db.customers.find((item) => String(item.id) === String(customer.id)) || customer); }
      if (action === "save") await pcSaveOffer();
      if (action === "stock") await pcDeductStock();
      if (action === "finance") await pcAddFinance();
    } catch (error) { toast(error.message, "error"); }
  });
  document.addEventListener("change", (event) => {
    if (page !== "pc-builder") return;
    if (event.target.id === "pcCustomer") { pcCustomerId = event.target.value; pcRefreshOfferCustomer(); return; }
    const rowElement = event.target.closest("[data-pc-row]");
    if (rowElement) {
      const row = pcRows.find((item) => item.key === rowElement.dataset.pcRow); if (!row) return;
      const filtersChanged = event.target.matches("[data-pc-brand], [data-pc-spec]");
      if (event.target.matches("[data-pc-brand]")) row.brand = event.target.value;
      if (event.target.matches("[data-pc-spec]")) row.spec = event.target.value;
      if (event.target.matches("[data-pc-product]")) {
        row.partId = event.target.value;
        const part = pcParts.find((item) => String(item.id) === String(row.partId));
        row.price = Number(part?.price) || 0;
        row.stock = part ? Number(part.qty) || 0 : null;
        const priceInput = rowElement.querySelector("[data-pc-price]");
        if (priceInput) priceInput.value = row.price.toFixed(2);
        const stockLabel = rowElement.querySelector(".pc-stock");
        if (stockLabel) {
          stockLabel.textContent = row.stock == null ? "\u2014" : String(row.stock);
          stockLabel.classList.toggle("good", Number(row.stock) > 3);
          stockLabel.classList.toggle("warn", Number(row.stock) > 0 && Number(row.stock) <= 3);
          stockLabel.classList.toggle("bad", row.stock == null || Number(row.stock) <= 0);
        }
      }
      if (event.target.matches("[data-pc-qty]")) pcSetQuantity(row, event.target);
      if (event.target.matches("[data-pc-price]")) pcSetPrice(row, event.target);
      if (filtersChanged) { if (!pcSelectedPartMatches(row)) { row.partId = ""; row.price = 0; row.stock = null; } pcRender(); } else pcRefreshTotals();
    }
    if (event.target.id === "pcVat") { pcVat = Number(event.target.value) || 0; pcRefreshTotals(); }
  });
  document.addEventListener("input", (event) => {
    if (page !== "pc-builder") return;
    if (event.target.id === "pcCustomerSearch") {
      pcCustomerSearch = event.target.value;
      const query = pcCustomerSearch.trim().toLocaleLowerCase("tr-TR");
      const customers = pcCustomers.filter((customer) => !query || String(customer.name || "").toLocaleLowerCase("tr-TR").includes(query));
      const select = $("#pcCustomer");
      const selectedId = select?.value || pcCustomerId;
      pcCustomerId = selectedId && customers.some((customer) => String(customer.id) === String(selectedId)) ? selectedId : "";
      if (select) {
        select.innerHTML = `<option value="">M\u00fc\u015fteri se\u00e7ilmedi</option>${customers.map((customer) => `<option value="${pcEscape(customer.id)}">${pcEscape(customer.name)}</option>`).join("")}`;
        select.value = pcCustomerId;
      }
      pcRefreshOfferCustomer();
      return;
    }
    const rowElement = event.target.closest("[data-pc-row]");
    const row = rowElement && pcRows.find((item) => item.key === rowElement.dataset.pcRow);
    if (row && event.target.matches("[data-pc-qty]")) { pcSetQuantity(row, event.target); pcRefreshTotals(); }
    if (row && event.target.matches("[data-pc-price]")) { row.price = Math.max(0, Number(event.target.value) || 0); pcRefreshTotals(); }
    if (event.target.id === "pcMargin") { pcMargin = Math.min(500, Math.max(0, Number(event.target.value) || 0)); pcRefreshTotals(); }
    if (event.target.id === "pcNote") pcNote = event.target.value;
  });
})();
