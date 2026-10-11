(function () {
  let licenseCountdownTimer = null;
  const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#64748B", "#14B8A6", "#0EA5E9"];
  const textColors = ["#0F172A", "#1E293B", "#334155", "#475569", "#E2E8F0", "#F1F5F9", "#F8FAFC", "#FFFFFF", "#FACC15"];
  const read = (key, fallback) => String(desktopSettings[key] ?? fallback);
  const choice = (key, value) => `<label class="theme-choice-card"><input type="radio" name="${key}" value="${value}" ${read(key, "") === value ? "checked" : ""}><span><strong>${value}</strong></span></label>`;
  const swatches = (key, palette) => palette.map(color => `<button type="button" class="theme-swatch" data-theme-color="${key}" data-color="${color}" style="--swatch:${color}" aria-label="${color}"></button>`).join("");

  function themeContent() {
    const theme = read("color_theme_full", "Forest");
    const appearance = read("appearance_mode", "modern");
    const scale = Math.max(80, Math.min(140, Number(read("interface_scale_percent", "90")) || 90));
    const labelMode = read("side_menu_label_mode", "labels");
    const navMode = read("nav_mode", "sol_menu");
    return `<h3 class="theme-reference-title">Temalar &amp; Yaz\u0131 Tipi</h3>
      <div class="theme-reference-grid">
        <section class="theme-reference-card theme-choice-panel"><label for="themeReferenceSelect">Uygulama Temas\u0131:</label><select id="themeReferenceSelect" class="control" data-theme-setting="color_theme_full"><option ${theme === "AYEC" ? "selected" : ""}>AYEC</option><option ${theme === "Koyu Mavi" ? "selected" : ""}>Koyu Mavi</option><option ${theme === "Forest" ? "selected" : ""}>Forest</option></select></section>
        <section class="theme-reference-card theme-appearance-panel"><strong>Program\u0131n g\xf6rsel yo\u011funlu\u011funu se\xe7in. Klasik g\xf6r\xfcn\xfcm daha d\xfcz, az efektli ve h\u0131zl\u0131 \xe7al\u0131\u015fmaya odakl\u0131d\u0131r.</strong><div class="theme-choice-grid">${["modern", "classic"].map(value => `<label class="theme-mode-card"><input type="radio" name="appearance_mode" value="${value}" ${appearance === value ? "checked" : ""}><span><b>${value === "modern" ? "Modern" : "Klasik"}</b><small>${value === "modern" ? "Mevcut g\xf6rsel zengin aray\xfcz, g\xf6lge ve geni\u015f bo\u015fluklar." : "Daha sade, kompakt ve d\xfc\u015f\xfck efektli aray\xfcz."}</small></span></label>`).join("")}</div></section>
        <section class="theme-reference-card theme-scale-panel"><h4>Yaz\u0131 ve \u0130kon Boyutu</h4><p>Program genelindeki yaz\u0131lar\u0131 ve ikonlar\u0131 kademeli olarak b\xfcy\xfct\xfcn veya k\xfc\xe7\xfclt\xfcn.</p><div class="theme-scale-row"><span>A</span><input id="themeScale" type="range" min="80" max="140" step="10" value="${scale}" aria-label="Aray\xfcz yaz\u0131 ve ikon boyutu"><b>A</b><output id="themeScaleValue">%${scale}</output></div></section>
        <section class="theme-reference-card theme-menu-panel"><h4>Sol Men\xfc G\xf6r\xfcn\xfcm\xfc</h4><p>Men\xfcde yaln\u0131zca simgeleri veya simge ile men\xfc ad\u0131n\u0131 birlikte g\xf6sterin.</p><div class="theme-menu-options"><label><input type="radio" name="side_menu_label_mode" value="icons" ${labelMode === "icons" ? "checked" : ""}> Sadece \u0130konlar</label><label><input type="radio" name="side_menu_label_mode" value="labels" ${labelMode === "labels" ? "checked" : ""}> \u0130kon + Men\xfc Ad\u0131</label></div></section>
        <section class="theme-reference-card theme-color-panel"><h4>Tema Renkleri (Vurgu + Metin)</h4><p>Bi\xe7im boyas\u0131 alanlar\u0131: 1) Tema vurgu rengi, 2) Genel yaz\u0131 rengi. Tema de\u011fi\u015fti\u011finde t\xfcm formlar ve tablolar bu renklere g\xf6re g\xfcncellenir.</p><div class="theme-color-row"><strong>1) Tema vurgu rengi (butonlar/se\xe7imler)</strong><div>${swatches("custom_accent_color", colors)}<button type="button" class="secondary" data-theme-picker="custom_accent_color">Vurgu rengi se\xe7</button><button type="button" class="theme-reset" data-theme-reset="custom_accent_color">Varsay\u0131lana d\xf6n</button><input type="color" data-theme-color-input="custom_accent_color" hidden></div></div><div class="theme-color-row"><strong>2) Yaz\u0131 rengi (metinler/ba\u015fl\u0131klar)</strong><div>${swatches("custom_text_color", textColors)}<button type="button" class="secondary" data-theme-picker="custom_text_color">Metin rengi se\xe7</button><button type="button" class="theme-reset" data-theme-reset="custom_text_color">Varsay\u0131lana d\xf6n</button><input type="color" data-theme-color-input="custom_text_color" hidden></div></div></section>
        <section class="theme-reference-card theme-nav-panel"><h4>Navigasyon D\xfczeni</h4><p>Uygulaman\u0131n navigasyon d\xfczenini se\xe7in.</p><div class="theme-nav-options">${[["sol_menu", "Sol Men\xfc"], ["ust_bar", "\xdcst Bar"], ["her_ikisi", "Her \u0130kisi"]].map(([value, title]) => `<label><input type="radio" name="nav_mode" value="${value}" ${navMode === value ? "checked" : ""}>${title}</label>`).join("")}</div></section>
      </div>`;
  }

  async function saveSetting(key, value) {
    desktopSettings[key] = value;
    await desktopWrite("settings", { key, value });
  }

  function bindThemeControls(host) {
    host.querySelectorAll("[data-theme-setting]").forEach(control => control.addEventListener("change", async () => {
      await saveSetting(control.dataset.themeSetting, control.value);
      if (control.dataset.themeSetting === "color_theme_full") {
        const webTheme = control.value === "Forest" ? "forest" : control.value === "Koyu Mavi" ? "midnight" : "light";
        applyTheme(webTheme);
      }
    }));
    host.querySelectorAll('input[name="appearance_mode"],input[name="side_menu_label_mode"],input[name="nav_mode"]').forEach(control => control.addEventListener("change", async () => {
      if (!control.checked) return;
      await saveSetting(control.name, control.value);
      if (control.name === "side_menu_label_mode") document.querySelector(".app-shell")?.classList.toggle("sidebar-collapsed", control.value === "icons");
    }));
    const scale = host.querySelector("#themeScale");
    scale?.addEventListener("input", () => { host.querySelector("#themeScaleValue").textContent = `%${scale.value}`; });
    scale?.addEventListener("change", async () => { await saveSetting("interface_scale_percent", scale.value); document.documentElement.style.fontSize = `${scale.value}%`; });
    host.querySelectorAll("[data-theme-color]").forEach(button => button.addEventListener("click", async () => applyColor(button.dataset.themeColor, button.dataset.color)));
    host.querySelectorAll("[data-theme-picker]").forEach(button => button.addEventListener("click", () => host.querySelector(`[data-theme-color-input="${button.dataset.themePicker}"]`).click()));
    host.querySelectorAll("[data-theme-color-input]").forEach(input => input.addEventListener("change", () => applyColor(input.dataset.themeColorInput, input.value)));
    host.querySelectorAll("[data-theme-reset]").forEach(button => button.addEventListener("click", () => applyColor(button.dataset.themeReset, "")));
  }

  async function applyColor(key, value) {
    await saveSetting(key, value);
    const cssKey = key === "custom_accent_color" ? "--ayec-electric" : "--ayec-slate-ink";
    document.documentElement.style.setProperty(cssKey, value || (key === "custom_accent_color" ? "#10B981" : "#E2E8F0"));
  }

  const modules = [
    ["operations", "Servis &amp; Operasyon Y\u00f6netimi", "&#128295;"],
    ["finance", "Finans &amp; Banka Y\u00f6netimi", "&#128176;"],
    ["stock", "Stok &amp; Depo Takibi", "&#128230;"],
    ["projects", "Proje / \u0130\u015f Takibi", "&#127959;"],
    ["crm", "M\u00fc\u015fteri \u0130li\u015fkileri (CRM)", "&#129309;"],
    ["personnel", "Personel &amp; Bordro", "&#128101;"],
    ["asistan", "Sesli Asistan &amp; K\u0131sayollar", "&#129302;"],
  ];
  const features = [
    ["wizard_upload", "Sihirbazda dosya y\u00fckleme", "&#128206;"],
    ["iban_verify", "Otomatik IBAN do\u011frulama", "&#9989;"],
    ["voice_alerts", "Sesli uyar\u0131lar", "&#128266;"],
    ["scheduled_alerts", "Zaman ayarl\u0131 duyurular", "&#128467;"],
    ["usage_guides", "Kullan\u0131m k\u0131lavuzu sekmeleri", "&#128218;"],
  ];

  function identityContent() {
    const sector = String(desktopInternalSettings.current_sector || "teknik_servis");
    const profiles = String(desktopInternalSettings.device_business_profiles || "bilgisayar").split(",");
    const activeModules = sector === "otomotiv" ? ["operations", "crm", "stock", "finance", "personnel", "asistan"] : ["operations", "finance", "stock", "projects", "crm", "personnel", "asistan"];
    const profileOptions = [["bilgisayar", "Bilgisayar"], ["cep_telefonu", "Cep Telefonu"], ["akilli_ev", "Ak\u0131ll\u0131 Ev"]];
    const settingInput = (scope, key, checked) => `<input class="switch exact-setting" type="checkbox" data-setting-scope="${scope}" data-setting-key="${key}" ${checked ? "checked" : ""}>`;
    const optionCards = (items, prefix) => items.map(([key, label, icon]) => `<label class="identity-option-card"><span>${icon} ${label}</span>${settingInput("internal_settings", `${prefix}_${key}_active`, (desktopInternalSettings[`${prefix}_${key}_active`] ?? (prefix === "module" ? (activeModules.includes(key) ? "1" : "0") : "1")) === "1")}</label>`).join("");
    return `<div class="identity-reference">
      <header class="identity-reference-head"><span aria-hidden="true">&#9881;</span><div><h2>Sistem Kimli\u011fi &amp; Mod\u00fcler Yap\u0131</h2><p>Uygulama sekt\u00f6r\u00fcn\u00fc, mod\u00fcl eri\u015fimini ve i\u015flev bayraklar\u0131n\u0131 y\u00f6netin.</p></div><strong class="identity-edition">ENTERPRISE PRO</strong><strong class="identity-db-status">Veritaban\u0131: Ba\u011fl\u0131</strong><button type="button" class="secondary" data-identity-refresh>&#8635; Yenile</button></header>
      <div class="identity-reference-grid"><div class="identity-reference-main">
      <fieldset class="identity-reference-section"><legend>1. Sekt\u00f6rel Kimlik (Master Switch)</legend><div class="identity-sector-body"><label for="identitySector">Ana \u00e7al\u0131\u015fma modu:</label><select id="identitySector" class="control exact-setting" data-setting-scope="internal_settings" data-setting-key="current_sector" ${currentAuthUser?.is_admin ? "" : "disabled"}><option value="teknik_servis" ${sector === "teknik_servis" ? "selected" : ""}>TS Teknik Servis Modu</option><option value="otomotiv" ${sector === "otomotiv" ? "selected" : ""}>OT Otomotiv Servis Modu</option></select><p class="identity-warning">&#9888; Dikkat: Sekt\u00f6r de\u011fi\u015fikli\u011fi men\u00fc yap\u0131s\u0131n\u0131 ve etiketleri yeniden d\u00fczenler.</p><label>Cihaz katalog i\u015f kollar\u0131:</label><input type="hidden" class="exact-setting" data-setting-scope="internal_settings" data-setting-key="device_business_profiles" value="${profiles.join(",")}"><div class="identity-profile-options">${profileOptions.map(([key, label]) => `<label class="identity-profile"><input type="checkbox" data-device-profile="${key}" ${profiles.includes(key) ? "checked" : ""}> ${label}</label>`).join("")}</div><small>Se\u00e7ilen kataloglar Yeni Servis Kayd\u0131 ve Yeni Cihaz Ekle alanlar\u0131n\u0131 filtreler.</small></div></fieldset>
      <fieldset class="identity-reference-section"><legend>2. Mod\u00fcl Paketleri (Toggle Switch)</legend><div class="identity-option-grid">${optionCards(modules, "module")}</div></fieldset>
      <fieldset class="identity-reference-section"><legend>3. \u00d6zellik Bazl\u0131 Kontroller</legend><div class="identity-option-grid identity-feature-grid">${optionCards(features, "feature")}</div></fieldset></div><div class="identity-reference-aside">
      <fieldset class="identity-reference-section identity-system-section"><legend><span>4. Sistem ve Veritaban\u0131 Bilgileri</span><span class="identity-status-pill" data-identity-status>Ba\u011flant\u0131 denetleniyor</span></legend><div class="identity-system-info"><div class="identity-database-path"><label for="identityDatabasePath">&#128193; Veritaban\u0131 yolu: <span>SQLite v3</span></label><div><input id="identityDatabasePath" data-identity-database readonly value="Y\u00fckleniyor..." aria-label="Veritaban\u0131 yolu"><button type="button" class="secondary" data-identity-copy title="Veritaban\u0131 yolunu kopyala">Kopyala</button></div></div><div class="identity-metrics"><article><span>Dosya Boyutu</span><b data-identity-size>-</b></article><article><span>Toplam \u00dcr\u00fcn</span><b data-identity-products>-</b></article><article><span>Stok Hareketi</span><b data-identity-movements>-</b></article></div><div class="identity-system-row"><span>&#128176; Stok muhasebe kay\u0131tlar\u0131</span><b data-identity-accounting>-</b></div><div class="identity-system-row"><span>&#9881; Y\u00fckleme modu</span><b data-identity-mode>Development (Geli\u015ftirme Modu)</b></div></div><div class="identity-system-actions"><button type="button" class="secondary" data-identity-copy>&#128203; Veritaban\u0131 Yolunu Kopyala</button><button type="button" class="secondary" data-identity-open>&#128193; Veritaban\u0131 Klas\u00f6r\u00fcn\u00fc A\u00e7</button></div></fieldset>
      <fieldset class="identity-reference-section"><legend><span>5. Ba\u015flang\u0131\u00e7 ve K\u0131sayol Ayarlar\u0131</span><span>Windows OS</span></legend><div class="identity-startup-row"><label><span>Windows ba\u015flang\u0131c\u0131nda otomatik \u00e7al\u0131\u015ft\u0131r<small>Sistem a\u00e7\u0131l\u0131\u015f\u0131nda arka planda haz\u0131r bekler</small></span><input type="checkbox" class="switch" data-identity-startup></label></div><div class="identity-shortcut-actions"><button type="button" class="secondary" data-identity-shortcut="desktop">&#128187; Masa\u00fcst\u00fc k\u0131sayolu olu\u015ftur</button><button type="button" class="secondary" data-identity-shortcut="start-menu">&#128187; Ba\u015flang\u0131\u00e7 men\u00fcs\u00fc k\u0131sayolu olu\u015ftur</button></div></fieldset></div></div>
    </div>`;
  }

  function companyContent() {
    const company = settingsDefinitions.company;
    const numbering = settingsDefinitions.numbering;
    const location = settingsDefinitions.location;
    const bank = settingsDefinitions["bank-settings"];
    const field = (definition, keys) => definition.fields
      .filter(item => keys.includes(item[0]))
      .map(item => exactSettingsField(item, "settings"))
      .join("");
    const sections = [
      ["companyIdentity", "Firma Bilgileri & Kimlik", company, ["company_name", "site_title", "company_email", "company_phone", "company_gsm", "company_fax", "company_website", "company_address", "social_facebook", "social_instagram", "social_youtube"]],
      ["companyVisual", "Logo & G\u00f6rsel", company, ["logo_path", "background_image"]],
      ["companyLocation", "Konum & GPS Harita", location, location.fields.map(item => item[0])],
      ["companyNumbers", "\u0130\u015f / Servis Saya\u00e7lar\u0131", numbering, numbering.fields.map(item => item[0])],
      ["companyBank", "Stok - Banka E\u015fle\u015ftirme", bank, bank.fields.map(item => item[0])],
    ];
    const name = String(desktopSettings.company_name || desktopSettings.company || "AYEC Pro");
    return `<div class="company-reference">
      <div class="company-reference-workspace">
        <section class="company-reference-section company-reference-identity" id="companyIdentity">
          <header class="company-reference-summary"><div><h2>Firma Bilgileri &amp; Resmi Kimlik Y\u00f6netimi <span>Firma Profili</span><span class="verified">Kay\u0131tl\u0131 &amp; Do\u011frulanm\u0131\u015f</span></h2><p>${esc(name)} \u00b7 ${esc(desktopSettings.company_tax_office || "Vergi Dairesi ekleyin")} \u00b7 ${esc(desktopSettings.company_tax_number || "Vergi No ekleyin")} \u00b7 ${esc(desktopSettings.company_phone || "Telefon ekleyin")}</p><div class="company-reference-tags"><span>\u2713 \u0130leti\u015fim Bilgileri</span><span>\u2713 Sosyal Medya</span><span>\u2713 Fatura &amp; S\u00f6zle\u015fme Metinleri</span><span>\u2713 Kargo &amp; Yaz\u0131c\u0131 Ayarlar\u0131</span></div></div><button class="primary" type="button" data-company-open-editor>Firma Bilgilerini D\u00fczenle</button></header>
          <div class="company-reference-visual-heading"><strong>LOGO &amp; G\u00d6RSEL VARLIKLAR</strong><small>Evrak antetlerinde, faturalarda ve masa\u00fcst\u00fcnde yer alan grafik materyaller</small><span>PNG, SVG, ICO Destekli</span></div>
          ${companyVisualPanel(field(company, ["background_image"]))}
        </section>
        <div class="company-reference-panels">${sections.slice(2).map(([id, title, definition, keys]) => `<section class="company-reference-section" id="${id}">${id === "companyNumbers" ? `<header class="company-number-header"><div><span class="company-reference-dot"></span><h3>${title}</h3><small>${definition.description || definition.title}</small></div><div class="company-number-actions"><button type="button" data-company-number-copy>KOPYALA</button><button type="button" data-company-number-csv>CSV \u00c7IKTI</button><button type="button" data-company-number-excel>EXCEL \u00c7IKTI</button><button type="button" data-company-number-print>YAZDIR</button></div></header>${companyNumbersPanel(definition)}` : `<header><span class="company-reference-dot"></span><h3>${title}</h3><small>${definition.description || definition.title}</small></header>${id === "companyBank" ? companyBankPanel() : id === "companyLocation" ? companyLocationPanel(field(definition, keys)) : `<div class="company-reference-fields">${field(definition, keys)}</div>`}`}</section>`).join("")}</div>
      </div>
    </div>`;
  }

  function companyLocationPanel(fields) {
    const lat = esc(desktopSettings.map_default_lat || "40.1044116");
    const lng = esc(desktopSettings.map_default_lng || "27.6563981");
    return `<div class="company-reference-location"><div class="company-reference-fields">${fields}<button type="button" class="secondary" data-company-map-pick>Haritadan Konum Se\u00e7</button><button type="button" class="primary" data-company-map-save>Konumu Kaydet</button></div><div class="company-reference-map" role="img" aria-label="Harita koordinat \u00f6nizlemesi"><span class="company-reference-map-status">GPS Kalibre Edildi</span><div class="company-reference-map-marker"><i></i><b data-company-coordinates>${lat}, ${lng}</b></div><small>OpenStreetMap Dark Tiles</small></div></div>`;
  }

  function companyNumbersPanel(definition) {
    const groups = [
      ["\u0130\u015f Numaras\u0131", "#JOB", "job_number_prefix", "job_number_next"],
      ["Servis Numaras\u0131", "#SRV", "service_number_prefix", "service_number_next"],
      ["Proje Numaras\u0131", "#PRJ", "project_number_prefix", "project_number_next"],
      ["Referans No", "#REF", "reference_number_prefix", "reference_number_next"],
      ["\u00d6deme No", "#PAY", "payment_number_prefix", "payment_number_next"],
    ];
    const fields = new Map(definition.fields.map(item => [item[0], item]));
    const input = (key, label) => {
      const item = fields.get(key);
      const value = esc(desktopSettings[key] ?? item?.[3] ?? "");
      const type = item?.[2] === "number" ? "number" : "text";
      return `<label class="company-number-field"><span>${label}</span><input class="exact-setting" data-setting-key="${key}" data-setting-scope="settings" type="${type}" value="${value}"></label>`;
    };
    return `<div class="company-number-grid">${groups.map(([title, code, prefix, next]) => `<article class="company-number-card"><header><strong>${title}</strong><span>${code}</span></header>${input(prefix, "\u00d6n Ek")}${input(next, "Sonraki")}</article>`).join("")}</div>`;
  }

  function companyVisualPanel(backgroundField) {
    const logoPath = String(desktopSettings.logo_path || "");
    const logoName = esc(logoPath.split(/[\\/]/).pop() || "Logo y\u00fcklenmedi");
    const stampPath = esc(desktopSettings.company_stamp_path || "G\u00f6rsel y\u00fcklenmedi");
    const logoPreview = logoPath ? `<img src="/api/desktop/company-logo?v=${Date.now()}" alt="Firma logosu">` : `<span class="company-reference-logo-empty">AYEC PRO</span>`;
    return `<div class="company-reference-visuals">
      <article class="company-reference-visual-card"><div class="company-reference-visual-preview">${logoPreview}</div><div class="company-reference-visual-copy"><strong>Birincil Firma Logosu</strong><small>${logoName}</small><span>PNG, JPG, WEBP \u00b7 En fazla 5 MB</span></div><div class="company-reference-visual-actions"><button type="button" class="secondary" data-company-logo-upload>De\u011fi\u015ftir</button><button type="button" class="ghost" data-company-logo-remove ${logoPath ? "" : "disabled"}>Kald\u0131r</button></div><input type="file" accept="image/png,image/jpeg,image/webp" data-company-logo-file hidden></article>
      <article class="company-reference-visual-card"><div class="company-reference-visual-preview">PDF</div><div class="company-reference-visual-copy"><strong>Fatura Antet / Ka\u015fe G\u00f6rseli</strong><small>${stampPath}</small><span>Kurumsal PDF ve fatura g\u00f6rseli</span></div><div class="company-reference-visual-actions"><label class="secondary" for="companyStampPath">G\u00f6rsel Yolu</label></div><div class="company-reference-wallpaper-setting"><input id="companyStampPath" class="setting exact-setting" data-setting-key="company_stamp_path" data-setting-scope="settings" value="${stampPath === "G\u00f6rsel y\u00fcklenmedi" ? "" : stampPath}" placeholder="G\u00f6rsel dosyas\u0131 yolu"></div></article>
      <article class="company-reference-visual-card company-reference-wallpaper"><div class="company-reference-wallpaper-preview">\u2302</div><div class="company-reference-visual-copy"><strong>Masa\u00fcst\u00fc Duvar Ka\u011f\u0131d\u0131</strong><small>${esc(desktopSettings.background_image || "Varsay\u0131lan (Dark Slate)")}</small><span>G\u00f6rsel yolu masa\u00fcst\u00fc uygulamas\u0131nda kullan\u0131l\u0131r.</span></div><div class="company-reference-visual-actions"><button type="button" class="secondary" data-company-wallpaper-clear>S\u0131f\u0131rla</button></div><div class="company-reference-wallpaper-setting">${backgroundField}</div></article>
    </div>`;
  }

  function companyBankPanel() {
    return `<div class="company-bank-toolbar"><input type="search" data-company-bank-search placeholder="\u00dcr\u00fcn, hizmet veya men\u00fc ara"><button type="button" class="secondary" data-company-bank-refresh>Yenile</button><button type="button" class="primary" data-company-bank-save>\u25a3 E\u015fle\u015ftirmeleri Kaydet</button></div><div class="company-bank-table-wrap"><table class="company-bank-table"><thead><tr><th>Men\u00fc / Mod\u00fcl Ad\u0131</th><th>Varsay\u0131lan Banka Hesab\u0131</th><th>KDV (%)</th><th>Gelir / Gider Kategorisi</th><th>Durum</th></tr></thead><tbody data-company-bank-rows><tr><td colspan="5">Banka e\u015fle\u015ftirmeleri y\u00fckleniyor...</td></tr></tbody></table></div>`;
  }

  async function loadCompanyBankMappings(host) {
    const body = host.querySelector("[data-company-bank-rows]");
    if (!body) return;
    try {
      const [mappingData, accountData, partData, serviceData] = await Promise.all([
        apiFetch("/api/desktop/table/product_bank_mappings?limit=1000"),
        apiFetch("/api/desktop/table/bank_accounts?limit=500"),
        apiFetch("/api/desktop/table/parts?limit=500"),
        apiFetch("/api/desktop/table/service_definitions?limit=500"),
      ]);
      const mappings = mappingData.rows || [];
      const mappingByKey = new Map(mappings.map(row => [`${row.item_type}:${row.item_id}`, row]));
      const accounts = (accountData.rows || []).filter(row => Number(row.is_active ?? 1) === 1);
      const entries = [
        ["product_stock", 0, "Stok Y\u00f6netimi", "Sat\u0131\u015f"],
        ["product_mobile", 0, "Mobil Stok", "Sat\u0131\u015f"],
        ["service_definitions", 0, "Hizmet Tan\u0131mlar\u0131", "Hizmet"],
        ["product_loaner", 0, "Emanet (Konsinye) Cihazlar", "Sat\u0131\u015f"],
        ...(partData.rows || []).map(row => ["product", Number(row.id), row.name || row.product_name || "", row.category || "Sat\u0131\u015f"]),
        ...(serviceData.rows || []).map(row => ["service", Number(row.id), row.name || row.service_name || "", "Hizmet"]),
      ].filter(row => row[1] === 0 || Number.isFinite(row[1]));
      const categories = [["Sat\u0131\u015f", "Sat\u0131\u015f"], ["Hizmet", "Hizmet"], ["Tahsilat", "Tahsilat"], ["Kira", "Kira"], ["Di\u011fer", "Di\u011fer"]];
      const accountLabel = account => {
        const name = [account.bank_name, account.account_holder || account.account_name].filter(Boolean).join(" - ") || "Banka Hesab\u0131";
        const number = account.account_number || account.account_no;
        return `${name}${number ? ` (${number})` : ""}`;
      };
      body.innerHTML = entries.map(([type, id, name, category]) => {
        const current = mappingByKey.get(`${type}:${id}`) || {};
        const accountOptions = [`<option value="">Atanmam\u0131\u015f</option>`, ...accounts.map(account => `<option value="${Number(account.id)}" ${String(account.id) === String(current.bank_account_id ?? "") ? "selected" : ""}>${esc(accountLabel(account))}</option>`)].join("");
        const categoryOptions = categories.map(([value, label]) => `<option value="${value}" ${(current.default_category || category) === value ? "selected" : ""}>${label}</option>`).join("");
        return `<tr data-company-bank-row data-item-type="${esc(type)}" data-item-id="${Number(id)}" data-mapping-id="${Number(current.id || 0)}"><td>${esc(name)}</td><td><select data-bank-account>${accountOptions}</select></td><td><input type="number" min="0" max="100" step="0.5" value="${Number(current.default_kdv_rate ?? 20)}" data-bank-vat></td><td><select data-bank-category>${categoryOptions}</select></td><td><span class="company-bank-status">${Number(current.bank_account_id || 0) ? "Aktif" : "Atanmam\u0131\u015f"}</span></td></tr>`;
      }).join("");
      host._companyBankAccounts = accounts;
      host.querySelector("[data-company-bank-search]").oninput = event => {
        const query = event.currentTarget.value.trim().toLocaleLowerCase("tr-TR");
        body.querySelectorAll("tr[data-company-bank-row]").forEach(row => { row.hidden = !row.cells[0].textContent.toLocaleLowerCase("tr-TR").includes(query); });
      };
    } catch (error) {
      body.innerHTML = `<tr><td colspan="5">${esc(error.message || "Banka e\u015fle\u015ftirmeleri y\u00fcklenemedi")}</td></tr>`;
    }
  }

  async function saveCompanyBankMappings(host) {
    const rows = [...host.querySelectorAll("[data-company-bank-row]")];
    try {
      for (const row of rows) {
        const mappingId = Number(row.dataset.mappingId || 0);
        const bankId = row.querySelector("[data-bank-account]").value;
        if (!bankId) {
          if (mappingId) await apiFetch("/api/desktop/table/product_bank_mappings", { method: "POST", body: JSON.stringify({ id: mappingId, _action: "delete" }) });
          continue;
        }
        const payload = {
          item_type: row.dataset.itemType,
          item_id: Number(row.dataset.itemId),
          bank_account_id: Number(bankId),
          default_kdv_rate: Number(row.querySelector("[data-bank-vat]").value || 20),
          default_category: row.querySelector("[data-bank-category]").value,
        };
        if (mappingId) { payload.id = mappingId; payload._action = "update"; }
        const saved = await apiFetch("/api/desktop/table/product_bank_mappings", { method: "POST", body: JSON.stringify(payload) });
        if (saved.id) row.dataset.mappingId = String(saved.id);
      }
      toast("E\u015fle\u015ftirmeler kaydedildi", "success");
      await loadCompanyBankMappings(host);
    } catch (error) { toast(error.message || "E\u015fle\u015ftirmeler kaydedilemedi", "error"); }
  }

  function bindCompanyControls(host) {
    const numberRows = () => [...host.querySelectorAll(".company-number-card")].map(card => [card.querySelector("header strong").textContent, ...[...card.querySelectorAll("input")].map(input => input.value)]);
    host.querySelector("[data-company-number-copy]")?.addEventListener("click", async () => {
      try { await navigator.clipboard.writeText(numberRows().map(row => row.join("\t")).join("\n")); toast("Numara ayarlar\u0131 panoya kopyaland\u0131", "success"); }
      catch (error) { toast(error.message || "Panoya kopyalanamad\u0131", "error"); }
    });
    const exportNumbers = (separator, filename, mime) => {
      const csv = numberRows().map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(separator)).join("\r\n");
      const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: mime }));
      const link = document.createElement("a"); link.href = url; link.download = filename; link.click(); URL.revokeObjectURL(url);
    };
    host.querySelector("[data-company-number-csv]")?.addEventListener("click", () => exportNumbers(",", "firma-numaralari.csv", "text/csv;charset=utf-8"));
    host.querySelector("[data-company-number-excel]")?.addEventListener("click", () => exportNumbers(";", "firma-numaralari.xls", "application/vnd.ms-excel;charset=utf-8"));
    host.querySelector("[data-company-number-print]")?.addEventListener("click", () => window.print());
    host.querySelectorAll("[data-company-jump]").forEach(button => button.addEventListener("click", () => {
      const target = host.querySelector(`#${CSS.escape(button.dataset.companyJump)}`);
      target?.scrollIntoView({ behavior: "smooth", block: "start" });
    }));
    loadCompanyBankMappings(host);
    const logoFile = host.querySelector("[data-company-logo-file]");
    host.querySelector("[data-company-logo-upload]")?.addEventListener("click", event => {
      event.stopPropagation();
      logoFile?.click();
    });
    logoFile?.addEventListener("change", async () => {
      const file = logoFile.files?.[0];
      if (!file) return;
      try {
        if (file.size > 5 * 1024 * 1024) throw new Error("Logo en fazla 5 MB olabilir");
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
        const result = await apiFetch("/api/desktop/company-logo", { method: "POST", body: JSON.stringify({ data: btoa(binary) }) });
        desktopSettings.logo_path = result.path;
        render();
        toast("Firma logosu g\u00fcncellendi", "success");
      } catch (error) { toast(error.message || "Logo y\u00fcklenemedi", "error"); }
    });
    host.querySelector("[data-company-logo-remove]")?.addEventListener("click", async event => {
      event.stopPropagation();
      try {
        await apiFetch("/api/desktop/company-logo", { method: "POST", body: JSON.stringify({ remove: true }) });
        desktopSettings.logo_path = "";
        render();
        toast("Firma logosu kald\u0131r\u0131ld\u0131", "success");
      } catch (error) { toast(error.message || "Logo kald\u0131r\u0131lamad\u0131", "error"); }
    });
    host.querySelector("[data-company-wallpaper-clear]")?.addEventListener("click", event => {
      event.stopPropagation();
      const input = host.querySelector('[data-setting-key="background_image"]');
      if (input) input.value = "";
    });
    const coordinateLabel = host.querySelector("[data-company-coordinates]");
    const updateCoordinates = () => {
      if (!coordinateLabel) return;
      const latitude = host.querySelector('[data-setting-key="map_default_lat"]')?.value || "";
      const longitude = host.querySelector('[data-setting-key="map_default_lng"]')?.value || "";
      coordinateLabel.textContent = `${latitude}, ${longitude}`;
    };
    host.querySelectorAll('[data-setting-key="map_default_lat"],[data-setting-key="map_default_lng"]').forEach(input => input.addEventListener("input", updateCoordinates));
    host.querySelector("[data-company-map-save]")?.addEventListener("click", async event => {
      event.stopPropagation();
      const fields = [...host.querySelectorAll('[data-setting-key="map_default_lat"],[data-setting-key="map_default_lng"]')];
      for (const input of fields) await desktopWrite("settings", { key: input.dataset.settingKey, value: input.value });
      toast("Konum ayarlar\u0131 kaydedildi", "success");
    });
    host.querySelector("[data-company-map-pick]")?.addEventListener("click", event => {
      event.stopPropagation();
      if (!navigator.geolocation) {
        toast("Bu taray\u0131c\u0131 konum servisini desteklemiyor", "error");
        return;
      }
      navigator.geolocation.getCurrentPosition(position => {
        const latitude = host.querySelector('[data-setting-key="map_default_lat"]');
        const longitude = host.querySelector('[data-setting-key="map_default_lng"]');
        if (latitude) latitude.value = position.coords.latitude.toFixed(6);
        if (longitude) longitude.value = position.coords.longitude.toFixed(6);
        updateCoordinates();
        toast("Cihaz konumu al\u0131nd\u0131; kaydetmek i\u00e7in Konumu Kaydet\u2019e bas\u0131n", "success");
      }, error => toast(error.message || "Cihaz konumu al\u0131namad\u0131", "error"), { enableHighAccuracy: true, timeout: 10000 });
    });
    host.querySelector("[data-company-bank-refresh]")?.addEventListener("click", () => loadCompanyBankMappings(host));
    host.querySelector("[data-company-bank-save]")?.addEventListener("click", () => saveCompanyBankMappings(host));
    host.querySelector("[data-company-open-editor]")?.addEventListener("click", event => {
      event.stopPropagation();
      const definitions = new Map(settingsDefinitions.company.fields.map(item => [item[0], item]));
      const tabs = [
        { id: "general", label: "Genel & \u0130leti\u015fim", title: "TEMEL FIRMA BILGILERI & SOSYAL MEDYA", keys: ["company_name", "company_email", "social_facebook", "social_instagram", "social_youtube", "company_website", "company_gsm", "company_fax", "site_title", "company_phone", "cargo_company", "cargo_deal_no"] },
        { id: "system", label: "Sistem, Tema & Para Birimi", title: "SISTEM, TEMA VE PARA BIRIMI", keys: ["stock_prefix", "currency_precision", "online_payment_active", "marquee_text"] },
        { id: "document", label: "Yaz\u0131c\u0131 & Belge D\u00fczeni", title: "YAZICI VE BELGE DUZENI", keys: ["document_printer", "receipt_printer", "label_printer", "document_page_size", "document_orientation", "label_size"] },
        { id: "legal", label: "Adres, Vergi & Sozle\u015fmeler", title: "ADRES, VERGI VE SOZLESMELER", keys: ["company_address", "authorized_person", "tax_office", "tax_number", "service_contract", "offer_contract"] }
      ];
      const extra = {
        document_printer: ["Belge Yaz\u0131c\u0131s\u0131", "text", ""], receipt_printer: ["Fi\u015f Yaz\u0131c\u0131s\u0131", "text", ""],
        label_printer: ["Barkod / Etiket Yaz\u0131c\u0131s\u0131", "text", ""], document_page_size: ["Belge Sayfa Boyutu", "select", "A4"],
        document_orientation: ["Belge Y\u00f6n\u00fc", "select", "portrait"], label_size: ["Etiket Boyutu (mm, GxY)", "text", "70x45"],
        authorized_person: ["Yetkili Ki\u015fi", "text", ""], tax_office: ["Vergi Dairesi", "text", ""],
        tax_number: ["Vergi Numaras\u0131", "text", ""]
      };
      const fieldHtml = key => {
        const item = definitions.get(key);
        const [name, label, type, fallback] = item || [key, ...(extra[key] || [key, "text", ""])];
        const displayLabels = { company_name: "Firma Ad\u0131n\u0131z", company_email: "Firma E-posta Adresiniz", social_facebook: "Facebook Adresiniz", social_instagram: "Instagram Adresiniz", social_youtube: "Youtube Adresiniz", company_website: "Web Site Adresiniz", company_gsm: "Firma GSM Numaran\u0131z", company_fax: "Firma Fax", site_title: "Web Site Title", company_phone: "Firma Sabit Telefonunuz" };
        const shownLabel = displayLabels[name] || label;
        const value = desktopSettings[name] ?? fallback ?? "";
        if (type === "checkbox") return `<label class="field company-editor-check"><span>${shownLabel}</span><input type="hidden" name="${name}" value="0"><input type="checkbox" name="${name}" value="1" ${settingBool(value) ? "checked" : ""}></label>`;
        if (name === "cargo_company") {
          const options = ["Yurti\u00e7i Kargo", "Aras Kargo", "MNG Kargo", "S\u00fcrat Kargo", "PTT Kargo"];
          if (value && !options.includes(value)) options.unshift(String(value));
          return `<label class="field"><span>${shownLabel}</span><select name="${name}">${options.map(option => `<option value="${esc(option)}" ${value === option ? "selected" : ""}>${esc(option)}</option>`).join("")}</select></label>`;
        }
        if (type === "select") {
          const options = name === "document_page_size" ? ["A4", "A3", "A5"] : ["portrait", "landscape"];
          return `<label class="field"><span>${shownLabel}</span><select name="${name}">${options.map(option => `<option value="${option}" ${value === option ? "selected" : ""}>${option}</option>`).join("")}</select></label>`;
        }
        const control = type === "textarea" ? `<textarea name="${name}" rows="${name.includes("contract") ? 3 : 2}">${esc(value)}</textarea>` : `<input name="${name}" type="${type}" value="${esc(value)}">`;
        return `<label class="field ${type === "textarea" ? "full" : ""}"><span>${shownLabel}</span>${control}</label>`;
      };
      const body = `<div class="company-settings-editor"><nav class="company-editor-tabs" role="tablist">${tabs.map((tab, index) => `<button type="button" role="tab" aria-selected="${index === 0}" data-company-editor-tab="${tab.id}" class="${index === 0 ? "active" : ""}">${tab.label}</button>`).join("")}</nav>${tabs.map((tab, index) => `<section class="company-editor-panel" role="tabpanel" data-company-editor-panel="${tab.id}" ${index ? "hidden" : ""}><header><strong>${tab.title}</strong>${index === 0 ? "<span>G\u00f6r\u00fcnt\u00fclenen Ekran: IMAGE_9</span>" : ""}</header><div class="form-grid">${tab.keys.map(fieldHtml).join("")}</div></section>`).join("")}</div>`;
      openDialog("Firma Ayarlar\u0131n\u0131 Gir", "SISTEM PARAMETRELER\u0130", body, async values => {
        for (const [key, value] of values.entries()) {
          await desktopWrite("settings", { key, value });
          desktopSettings[key] = value;
        }
        render();
        toast("Firma bilgileri kaydedildi", "success");
      }, "G\u00dcNCELLE");
      const dialog = document.getElementById("appDialog");
      dialog.querySelectorAll("[data-company-editor-tab]").forEach(button => button.addEventListener("click", () => {
        const selected = button.dataset.companyEditorTab;
        dialog.querySelectorAll("[data-company-editor-tab]").forEach(tab => {
          const active = tab === button;
          tab.classList.toggle("active", active);
          tab.setAttribute("aria-selected", String(active));
        });
        dialog.querySelectorAll("[data-company-editor-panel]").forEach(panel => { panel.hidden = panel.dataset.companyEditorPanel !== selected; });
      }));
    });
  }

  function securityContent() {
    const questions = ["\u0130lk evcil hayvan\u0131n\u0131z\u0131n ad\u0131 nedir", "\u0130lkokul \u00f6\u011fretmeninizin ad\u0131 nedir", "Do\u011fdu\u011funuz \u015fehir neresi", "Annenizin k\u0131zl\u0131k soyad\u0131 nedir", "En sevdi\u011finiz yemek nedir"];
    return `<div class="security-reference">
      <header class="security-reference-head"><span aria-hidden="true">&#128272;</span><div><h2>G\u00fcvenlik ve Eri\u015fim Kontrol\u00fc</h2><p>Uygulaman\u0131z\u0131n ve kritik b\u00f6l\u00fcmlerin eri\u015fim g\u00fcvenli\u011fini buradan y\u00f6netebilirsiniz.</p></div></header>
      <section class="security-control-card"><div class="security-control-head"><div><h3>Uygulama Giri\u015f G\u00fcvenli\u011fi</h3><p>Program a\u00e7\u0131l\u0131\u015f\u0131nda \u015fifre sorulsun.</p></div><input type="checkbox" class="switch" data-security-toggle="app_lock_active"></div><label class="security-password"><span>Giri\u015f \u015eifresi:</span><input type="password" autocomplete="new-password" data-security-password="app_password" placeholder="Yeni \u015fifre belirle..."></label><small data-security-configured="app_password"></small></section>
      <section class="security-control-card"><div class="security-control-head"><div><h3>Teknisyen Paneli Korumas\u0131</h3><p>Teknisyen paneline giri\u015fte \u00f6zel \u015fifre istensin.</p></div><input type="checkbox" class="switch" data-security-toggle="tech_lock_active"></div><label class="security-password"><span>Giri\u015f \u015eifresi:</span><input type="password" autocomplete="new-password" data-security-password="tech_password" placeholder="Yeni \u015fifre belirle..."></label><small data-security-configured="tech_password"></small></section>
      <section class="security-control-card"><div class="security-control-head"><div><h3>Otomatik Giri\u015f</h3><p>Program a\u00e7\u0131l\u0131\u015f\u0131nda kullan\u0131c\u0131 ad\u0131 ve \u015fifre sormadan otomatik giri\u015f yap.</p></div><input type="checkbox" class="switch" data-security-toggle="auto_login"></div></section>
      <section class="security-control-card"><div class="security-control-head"><div><h3>&#128273; Y\u00f6netici \u015eifresi ve Kurtarma</h3><p>Kritik i\u015flemler ve \u015fifre s\u0131f\u0131rlama i\u00e7in.</p></div></div><label class="security-password"><span>Y\u00f6netici \u015eifresi:</span><input type="password" autocomplete="new-password" data-security-password="admin_password" placeholder="Yeni admin \u015fifresi belirle..."></label><hr><strong>&#10067; \u015eifre Kurtarma (Gizli Soru)</strong><small>\u015eifrenizi unutursan\u0131z bu soruya verece\u011finiz yan\u0131tla s\u0131f\u0131rlayabilirsiniz.</small><select class="control" data-security-question><option value="custom">\u00d6zel Soru Belirle...</option>${questions.map(question => `<option value="${question}">${question}</option>`).join("")}</select><input class="control" data-security-custom-question placeholder="Kendi gizli sorunuzu yaz\u0131n..." hidden><input class="control" type="password" autocomplete="new-password" data-security-answer placeholder="Yan\u0131t\u0131n\u0131z..."></section>
    </div>`;
  }

  async function bindSecurityControls(host) {
    const question = host.querySelector("[data-security-question]");
    const custom = host.querySelector("[data-security-custom-question]");
    question.addEventListener("change", () => { custom.hidden = question.value !== "custom"; });
    try {
      const state = await apiFetch("/api/desktop/security-settings");
      if (!host.isConnected) return;
      host.querySelectorAll("[data-security-toggle]").forEach(control => { control.checked = Boolean(state[control.dataset.securityToggle]); });
      host.querySelectorAll("[data-security-configured]").forEach(label => { label.textContent = state[label.dataset.securityConfigured] ? "A password is configured. Leave blank to keep it." : "No password configured."; });
      if (state.security_question) {
        const option = [...question.options].find(item => item.value === state.security_question);
        if (option) question.value = state.security_question;
        else { question.value = "custom"; custom.value = state.security_question; custom.hidden = false; }
      }
    } catch (error) { if (host.isConnected) toast("Security settings could not be loaded", "error"); }
  }

  async function saveSecurityControls(host) {
    const questionSelect = host.querySelector("[data-security-question]");
    const question = questionSelect.value === "custom" ? host.querySelector("[data-security-custom-question]").value : questionSelect.value;
    const payload = { security_question: question, security_answer: host.querySelector("[data-security-answer]").value };
    host.querySelectorAll("[data-security-toggle]").forEach(control => { payload[control.dataset.securityToggle] = control.checked; });
    host.querySelectorAll("[data-security-password]").forEach(control => { payload[control.dataset.securityPassword] = control.value; });
    try {
      await apiFetch("/api/desktop/security-settings", { method: "POST", body: JSON.stringify(payload) });
      host.querySelectorAll("[data-security-password], [data-security-answer]").forEach(control => { control.value = ""; });
      toast("Security settings saved", "success");
      await bindSecurityControls(host);
    } catch (error) { toast(error.message || "Security settings could not be saved", "error"); }
  }

  function licenseContent() {
    return `<div class="license-reference">
      <header class="license-reference-head"><h2>&#128274; Lisans Y\u00f6netimi &amp; G\u00fcvenlik Matrisi</h2><div class="license-reference-actions"><button type="button" class="secondary" data-license-action="billing">Mali Belgelerim</button><button type="button" class="secondary" data-license-action="transfer">Lisans Transferi</button><button type="button" class="secondary" data-license-action="extend">S\u00fcreyi Uzat</button></div><p>Saha terminal donan\u0131m\u0131, HWID, model abonelikleri ve banka mutabakat merkezi</p></header>
      <section class="license-status-card"><strong data-license-status>Durum: Y\u00fckleniyor...</strong><div data-license-details></div><div data-license-countdown hidden></div></section>
      <section class="license-hwid-card"><strong data-license-hwid>Cihaz Kimli\u011fi (HWID): Y\u00fckleniyor...</strong><button class="secondary" type="button" data-license-copy>Kopyala</button></section>
      <section class="license-key-card"><h3>Yeni Lisans Anahtar\u0131 Ekle</h3><input type="password" autocomplete="off" data-license-key placeholder="Lisans anahtar\u0131n\u0131z\u0131 buraya yap\u0131\u015ft\u0131r\u0131n..."><button type="button" class="primary" data-license-activate>&#9989; Lisans\u0131 Etkinle\u015ftir</button></section>
      <section class="license-plan-section"><h3>Lisans Paketleri</h3><div class="license-plan-grid" data-license-plans></div></section>
      <section class="license-payment-grid"><article class="license-payment-card"><h3>Resmi \u015eirket Banka Bilgileri</h3><div data-license-bank>Odeme bilgileri aliniyor...</div></article><article class="license-payment-card"><h3>Dekont Y\u00fckleme ve Onay</h3><p>Odemeyi tamamladiktan sonra dekont dosyanizi yukleyin. PDF, JPG veya PNG kabul edilir.</p><button class="secondary license-deposit-button" type="button">Dekont Sec ve Yukle</button></article></section>
      <section class="license-order-panel" data-license-order hidden></section>
      <button type="button" class="primary license-request-button" data-license-request>&#128228; Lisans Talep Et</button>
    </div>`;
  }

  async function bindLicenseControls(host) {
    if (licenseCountdownTimer) clearInterval(licenseCountdownTimer);
    try {
      const license = await apiFetch("/api/license/status");
      if (!host.isConnected) return;
      const access = license.access || {};
      const key = String(desktopSettings.license_key || "");
      const expiry = String(desktopSettings.license_expires || access.license_end || "");
      const active = Boolean(key || access.allowed);
      host.querySelector("[data-license-status]").textContent = `Durum: ${active ? "Aktif \u2714" : "Aktif De\u011fil \u2718"}`;
      const details = [
        `Lisans T\u00fcr\u00fc: ${desktopSettings.license_type || access.license_type || "Deneme S\u00fcr\u00fcm\u00fc"}`,
        `Ba\u015flang\u0131\u00e7: ${desktopSettings.license_started || "-"}`,
        `Biti\u015f: ${expiry || "S\u00fcresiz"}`,
        `Lisans Kodu: ${desktopSettings.license_code || access.license_code || "-"}`,
        `Sunucu G\u00fcncellemesi: ${desktopSettings.license_updated_at || "-"}`,
      ];
      host.querySelector("[data-license-details]").innerHTML = details.map(item => `<div>${esc(item)}</div>`).join("");
      const hwid = typeof licenseClientHardwareId === "function" ? licenseClientHardwareId() : "";
      const hwidLabel = host.querySelector("[data-license-hwid]");
      hwidLabel.textContent = `Cihaz Kimli\u011fi (HWID): ${hwid ? `${hwid.slice(0, 16)}...` : "-"}`;
      hwidLabel.dataset.hwid = hwid;
      const countdown = host.querySelector("[data-license-countdown]");
      const updateCountdown = () => {
        if (!expiry) { countdown.hidden = !active; countdown.textContent = active ? "\u23f3 Kalan S\u00fcre: S\u00fcresiz" : ""; return; }
        const parsed = new Date(expiry.length === 10 ? `${expiry}T23:59:59` : expiry.replace(" ", "T"));
        const seconds = Math.max(0, Math.floor((parsed.getTime() - Date.now()) / 1000));
        countdown.hidden = !active;
        countdown.textContent = `\u23f3 Kalan S\u00fcre: ${Math.floor(seconds / 86400)} g\u00fcn ${Math.floor(seconds % 86400 / 3600)} saat ${Math.floor(seconds % 3600 / 60)} dk`;
      };
      updateCountdown();
      licenseCountdownTimer = setInterval(updateCountdown, 1000);
      const bank = license.payment || {};
      host.querySelector("[data-license-bank]").innerHTML = `<strong>${esc(bank.bank_name || "")}</strong><br>${esc(bank.account_holder || "")}<br>IBAN: ${esc(bank.iban || "")}`;
      const plans = license.plans || [];
      const accents = ["#10B981", "#06B6D4", "#EF4444", "#F59E0B", "#8B5CF6"];
      host.querySelector("[data-license-plans]").innerHTML = plans.map((plan, index) => `<article class="license-plan-card" style="--license-plan-accent:${accents[index % accents.length]}"><strong>${esc(index === 0 ? "BASLANGIC" : index === 2 ? "EN COK TERCIH" : index === plans.length - 1 ? "VIP DESTEK" : "AVANTAJLI")}</strong><h4>${esc(plan.label)}</h4><b>${Number(plan.amount_try || 0).toLocaleString("tr-TR")} TRY</b><small>${Number(plan.duration_months || 0)} ay lisans s\u00fcresi</small><button class="secondary" type="button" data-license-plan="${esc(plan.code)}">Paketi Se\u00e7</button></article>`).join("");
      host.dataset.hardwareId = hwid;
      host.dataset.productCode = String(license.tenant?.product_code || currentSector || "teknik_servis");
      host.querySelectorAll("[data-license-plan]").forEach(button => button.addEventListener("click", () => createLicenseOrder(host, button.dataset.licensePlan)));
    } catch (error) {
      if (host.isConnected) toast("License information could not be loaded", "error");
    }
  }

  async function createLicenseOrder(host, planCode) {
    try {
      const result = await apiFetch("/api/license/orders", { method: "POST", body: JSON.stringify({ plan_code: planCode, hardware_id: host.dataset.hardwareId, product_code: host.dataset.productCode }) });
      const order = result.order || {};
      const panel = host.querySelector("[data-license-order]");
      panel.hidden = false;
      panel.innerHTML = `<strong>${esc(order.plan_label || "Lisans talebi")}</strong><p>${Number(order.amount_try || 0).toLocaleString("tr-TR")} TRY</p><p>Odeme referansi: <b>${esc(order.payment_reference || "-")}</b></p><button type="button" class="primary" data-license-payment-reported>Odemeyi Yaptim</button>`;
      panel.querySelector("[data-license-payment-reported]").addEventListener("click", async () => {
        await apiFetch(`/api/license/orders/${Number(order.id)}/payment-reported`, { method: "POST", body: JSON.stringify({ payment_note: "Payment reported in AYEC Pro web settings" }) });
        panel.innerHTML = "Odeme bildiriminiz alindi. Yonetici onayindan sonra lisansiniz guncellenecektir.";
      });
      panel.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (error) { toast(error.message || "License request could not be created", "error"); }
  }

  function bindIdentityControls(host) {
    const profileField = host.querySelector('[data-setting-key="device_business_profiles"]');
    host.querySelectorAll("[data-device-profile]").forEach(control => control.addEventListener("change", () => {
      const selected = [...host.querySelectorAll("[data-device-profile]:checked")].map(item => item.dataset.deviceProfile);
      profileField.value = (selected.length ? selected : ["bilgisayar"]).join(",");
      desktopInternalSettings.device_business_profiles = profileField.value;
    }));
    host.querySelectorAll(".exact-setting[data-setting-key]").forEach(field => {
      const syncValue = () => {
        desktopInternalSettings[field.dataset.settingKey] = field.type === "checkbox"
          ? (field.checked ? "1" : "0")
          : field.value;
      };
      field.addEventListener("click", syncValue);
      field.addEventListener("change", syncValue);
    });
    const pathField = host.querySelector("[data-identity-database]");
    const canUseLocalShell = currentAuthUser?.is_admin
      && ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    const copyPath = async () => {
      const path = pathField?.dataset.path || "";
      if (!path) return;
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(path);
        else {
          pathField.focus();
          pathField.select();
          if (!document.execCommand("copy")) throw new Error("Clipboard access is unavailable");
        }
        toast("Database path copied", "success");
      } catch (error) { toast(error.message || "Could not copy the database path", "error"); }
    };
    host.querySelectorAll("[data-identity-copy]").forEach(button => button.addEventListener("click", copyPath));
    const runSystemAction = async (action, body = {}) => apiFetch("/api/desktop/system-actions", {
      method: "POST",
      body: JSON.stringify({ action, ...body }),
    });
    host.querySelector("[data-identity-open]")?.addEventListener("click", async () => {
      try {
        await runSystemAction("open-database-folder");
        toast("Database folder opened", "success");
      } catch (error) { toast(error.message || "Could not open the database folder", "error"); }
    });
    host.querySelectorAll("[data-identity-shortcut]").forEach(button => button.addEventListener("click", async () => {
      const action = button.dataset.identityShortcut === "desktop" ? "desktop-shortcut" : "start-menu-shortcut";
      try {
        await runSystemAction(action);
        toast("Shortcut created", "success");
      } catch (error) { toast(error.message || "Could not create the shortcut", "error"); }
    }));
    const startup = host.querySelector("[data-identity-startup]");
    startup.addEventListener("change", async event => {
      const control = event.currentTarget;
      const requested = control.checked;
      try {
        await runSystemAction("startup", { enabled: requested });
        toast("Startup setting updated", "success");
      } catch (error) {
        control.checked = !requested;
        toast(error.message || "Could not update the startup setting", "error");
      }
    });
    const refreshSystemInfo = async () => {
      const refresh = host.querySelector("[data-identity-refresh]");
      if (refresh) refresh.disabled = true;
      try {
        const data = await apiFetch("/api/desktop/system-info");
        if (!host.isConnected) return;
        const path = String(data.database || "");
        pathField.value = path || "-";
        pathField.dataset.path = path;
        host.querySelector("[data-identity-status]").textContent = data.exists ? "\u2713 Durum: Mevcut" : "\u2715 Durum: Bulunamad\u0131";
        host.querySelector("[data-identity-size]").textContent = Number(data.size_mb || 0).toFixed(2) + " MB";
        host.querySelector("[data-identity-products]").textContent = Number(data.counts?.parts || 0) + " Adet";
        host.querySelector("[data-identity-movements]").textContent = Number(data.counts?.stock_movements || 0) + " Kay\u0131t";
        host.querySelector("[data-identity-accounting]").textContent = String(Number(data.counts?.accounting_stock || 0));
        const shellAvailable = canUseLocalShell && Boolean(data.shell_actions_available);
        startup.checked = Boolean(data.startup_enabled);
        startup.disabled = !shellAvailable;
        host.querySelector("[data-identity-open]").disabled = !shellAvailable;
        host.querySelectorAll("[data-identity-shortcut]").forEach(button => { button.disabled = !shellAvailable; });
        const shellMessage = shellAvailable ? "" : "Windows system actions are available in the local desktop app only";
        [startup, host.querySelector("[data-identity-open]"), ...host.querySelectorAll("[data-identity-shortcut]")].forEach(control => {
          if (shellMessage) control.title = shellMessage;
        });
      } catch (error) {
        if (host.isConnected) host.querySelector("[data-identity-status]").textContent = "\u26A0 Durum: Bilgi al\u0131namad\u0131";
      } finally {
        if (refresh) refresh.disabled = false;
      }
    };
    host.querySelector("[data-identity-refresh]")?.addEventListener("click", refreshSystemInfo);
    refreshSystemInfo();
  }
  const priorRender = render;
  render = function () {
    priorRender();
    if (page !== "settings" || !["company", "theme", "identity", "security", "license"].includes(settingsSection)) {
      if (licenseCountdownTimer) { clearInterval(licenseCountdownTimer); licenseCountdownTimer = null; }
      return;
    }
    const host = document.querySelector(".settings-content");
    if (!host) return;
    document.body.dataset.settingsSection = settingsSection;
    if (settingsSection === "company") {
      host.innerHTML = companyContent();
      bindCompanyControls(host);
    } else if (settingsSection === "theme") {
      host.innerHTML = themeContent();
      bindThemeControls(host);
    } else if (settingsSection === "identity") {
      host.innerHTML = identityContent();
      bindIdentityControls(host);
    } else if (settingsSection === "security") {
      host.innerHTML = securityContent();
      bindSecurityControls(host);
    } else {
      host.innerHTML = licenseContent();
      bindLicenseControls(host);
      host.querySelector("[data-license-copy]").addEventListener("click", async () => {
        const value = host.querySelector("[data-license-hwid]").dataset.hwid || "";
        if (!value) return toast("Device ID is unavailable", "error");
        await navigator.clipboard.writeText(value);
        toast("Device ID copied", "success");
      });
      host.querySelector("[data-license-activate]").addEventListener("click", async () => {
        const input = host.querySelector("[data-license-key]");
        const value = input.value.trim();
        if (!value) return toast("Enter a license key", "warning");
        try {
          await apiFetch("/api/desktop/table/settings", { method: "POST", body: JSON.stringify({ key: "license_key", value }) });
          desktopSettings.license_key = value;
          input.value = "";
          host.querySelector("[data-license-status]").textContent = "Durum: Aktif \u2714";
          toast("License activated", "success");
        } catch (error) { toast(error.message || "License activation failed", "error"); }
      });
      host.querySelector("[data-license-request]").addEventListener("click", () => host.querySelector("[data-license-plans]").scrollIntoView({ behavior: "smooth" }));
      host.querySelectorAll("[data-license-action]").forEach(button => button.addEventListener("click", () => {
        const target = button.dataset.licenseAction === "billing" ? "[data-license-bank]" : button.dataset.licenseAction === "transfer" ? "[data-license-hwid]" : "[data-license-plans]";
        host.querySelector(target).scrollIntoView({ behavior: "smooth", block: "center" });
      }));
    }
    const saveButton = document.querySelector('[data-action="save-settings"]');
    const pageActions = document.querySelector(".page-head .actions");
    if (pageActions) {
      if (settingsSection === "license") pageActions.style.setProperty("display", "none", "important");
      else pageActions.style.removeProperty("display");
    }
    if (saveButton) {
      saveButton.textContent = settingsSection === "theme" ? "T\xfcm de\u011fi\u015fiklikleri uygula" : settingsSection === "identity" ? "De\u011fi\u015fiklikleri Uygula ve Kaydet" : "AYARLARI KAYDET";
      saveButton.style.display = settingsSection === "license" ? "none" : "";
      saveButton.hidden = settingsSection === "license";
    }
  };
  document.addEventListener("click", async event => {
    if (page !== "settings" || settingsSection !== "identity" || !event.target.closest('[data-action="save-settings"]')) return;
    const host = document.querySelector(".identity-reference");
    if (!host) return;
    const sectorField = host.querySelector('[data-setting-key="current_sector"]');
    const sector = sectorField && !sectorField.disabled ? sectorField.value : "";
    const values = [...host.querySelectorAll(".exact-setting[data-setting-key]")].filter(field => !field.disabled && field.dataset.settingKey !== "current_sector").map(field => ({
      scope: field.dataset.settingScope || "internal_settings",
      key: field.dataset.settingKey,
      value: field.type === "checkbox" ? (field.checked ? "1" : "0") : field.value,
    }));
    try {
      if (sector && sector !== currentSector && !confirm("\u00c7al\u0131\u015fma alan\u0131 se\u00e7ilen sekt\u00f6re ge\u00e7irilsin mi?")) return;
      await Promise.all(values.map(item => apiFetch(`/api/desktop/table/${item.scope}`, {
        method: "POST",
        body: JSON.stringify({ key: item.key, value: item.value }),
      })));
      values.forEach(item => { desktopInternalSettings[item.key] = item.value; });
      if (sector && sector !== currentSector) {
        const result = await apiFetch("/api/company/sector", { method: "POST", body: JSON.stringify({ sector }) });
        currentSector = result.sector;
        desktopInternalSettings.current_sector = result.sector;
        renderNav();
      }
      toast("\u2705 De\u011fi\u015fiklikler kaydedildi", "success");
    } catch (error) {
      toast(error.message || "Settings could not be saved", "error");
    }
  }, true);
  document.addEventListener("click", event => {
    if (page !== "settings" || settingsSection !== "security" || !event.target.closest('[data-action="save-settings"]')) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const host = document.querySelector("#settingsBody");
    if (host) saveSecurityControls(host);
  }, true);
})();
