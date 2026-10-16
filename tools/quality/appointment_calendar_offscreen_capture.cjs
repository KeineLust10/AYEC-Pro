const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `appointment-calendar-headless-profile-${process.pid}`);
const fixedDate = "2026-10-13T09:00:00+03:00";

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1300,850", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await waitForTarget();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 80; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof db !== 'undefined' && typeof render === 'function' && typeof appointmentDialog === 'function'")) break;
      await delay(200);
    }
    const appointmentStatusCheck = await evaluate(`(async () => {
      const originalAppointments = db.appointments, originalWrite = desktopWrite, writes = [];
      db.appointments = [{ id: 731, status: "Bekliyor" }];
      desktopWrite = async (table, payload) => { writes.push({ table, ...payload }); };
      await setAppointmentStatus(731, "Gidildi");
      const persistedStatus = db.appointments[0].status;
      desktopWrite = async () => { throw new Error("QA write failure"); };
      await setAppointmentStatus(731, "Gidilmedi");
      const failureKeepsStatus = db.appointments[0].status === "Gidildi";
      desktopWrite = originalWrite; db.appointments = originalAppointments; save();
      return { persistedStatus, writeStatus: writes[0]?.status, failureKeepsStatus };
    })()`);
    if (appointmentStatusCheck.persistedStatus !== "Gidildi" || appointmentStatusCheck.writeStatus !== "Gidildi" || !appointmentStatusCheck.failureKeepsStatus) throw new Error(`Appointment status persistence mismatch: ${JSON.stringify(appointmentStatusCheck)}`);
    const maintenancePdfCheck = await evaluate(`(async () => {
      const originalFetch = window.fetch, originalCreate = URL.createObjectURL, originalRevoke = URL.revokeObjectURL, originalClick = HTMLAnchorElement.prototype.click;
      let request = "", downloaded = "";
      try {
        window.fetch = async url => { request = String(url); return { ok: true, blob: async () => new Blob(["%PDF-QA"], { type: "application/pdf" }) }; };
        URL.createObjectURL = () => "blob:maintenance-pdf-qa";
        URL.revokeObjectURL = () => {};
        HTMLAnchorElement.prototype.click = function() { downloaded = this.download; };
        await exportVehicleMaintenancePdf();
      } finally {
        window.fetch = originalFetch; URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke; HTMLAnchorElement.prototype.click = originalClick;
      }
      return { request, downloaded };
    })()`);
    if (!maintenancePdfCheck.request.includes("/api/desktop/vehicle-maintenance/export/pdf?q=") || !/^arac_bakim_.*\.pdf$/.test(maintenancePdfCheck.downloaded)) throw new Error(`Maintenance PDF download mismatch: ${JSON.stringify(maintenancePdfCheck)}`);
    const state = await evaluate(`(() => {
      const NativeDate = Date;
      window.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : ["${fixedDate}"])); } static now() { return new NativeDate("${fixedDate}").valueOf(); } };
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const locationForm = document.createElement("form"); locationForm.innerHTML = customerForm(); document.body.append(locationForm);
      const defaultCity = locationForm.elements.city.value, defaultDistrict = locationForm.elements.district.value, defaultAddress = locationForm.elements.address.value;
      const locationCities = [...locationForm.querySelector("#customerCityOptions").options].map(option => option.value);
      const locationStreets = [...locationForm.querySelector("#customerStreetOptions").options].map(option => option.value);
      const cityInput = locationForm.elements.city;
      cityInput.value = ""; cityInput.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
      const comboPanel = document.querySelector("#customerAddressCombo"), comboOptionCount = comboPanel?.querySelectorAll("[data-customer-address-option]").length || 0;
      const comboUsesCustomPopup = !cityInput.hasAttribute("list") && cityInput.getAttribute("role") === "combobox";
      cityInput.value = "zz"; cityInput.dispatchEvent(new Event("input", { bubbles: true }));
      const comboHidesWhenNoMatch = comboPanel?.hidden === true;
      cityInput.value = ""; cityInput.dispatchEvent(new Event("input", { bubbles: true }));
      const comboRecoversAfterNoMatch = comboPanel?.hidden === false && comboPanel.querySelectorAll("[data-customer-address-option]").length === 4;
      comboPanel?.querySelectorAll("[data-customer-address-option]").length && [...comboPanel.querySelectorAll("[data-customer-address-option]")].find(option => option.textContent === "\u0130stanbul")?.click();
      const comboSelectWorks = cityInput.value === "\u0130stanbul", comboClosesAfterSelection = comboPanel?.hidden === true;
      locationForm.elements.city.value = "Bal\u0131kesir"; locationForm.elements.city.dispatchEvent(new Event("change", { bubbles: true }));
      const balikesirDistricts = [...locationForm.querySelector("#customerDistrictOptions").options].map(option => option.value);
      const balikesirNeighborhoods = [...locationForm.querySelector("#customerNeighborhoodOptions").options].map(option => option.value);
      const districtInput = locationForm.elements.district;
      districtInput.value = ""; districtInput.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
      for (let index = 0; index < 12; index += 1) districtInput.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true }));
      const keyboardHighlightedDistrict = comboPanel?.querySelector('[aria-selected="true"]')?.textContent || "";
      districtInput.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true }));
      const keyboardSelectedDistrict = districtInput.value === "G\u00f6nen" && comboPanel?.hidden === true;
      locationForm.elements.city.value = "Istanbul"; locationForm.elements.city.dispatchEvent(new Event("change", { bubbles: true }));
      const otherCityDistricts = [...locationForm.querySelector("#customerDistrictOptions").options].map(option => option.value);
      const otherCityReset = locationForm.elements.district.value === "Merkez" && otherCityDistricts.includes("Di\u011fer");
      locationForm.elements.city.value = "Bal\u0131kesir"; locationForm.elements.city.dispatchEvent(new Event("change", { bubbles: true }));
      const cityReturn = locationForm.elements.district.value === "G\u00f6nen" && locationForm.querySelector("#customerNeighborhoodOptions").options.length === 23;
      locationForm.elements.district.value = "Edremit"; locationForm.elements.district.dispatchEvent(new Event("change", { bubbles: true }));
      const nonGonenDistrict = locationForm.querySelector("#customerNeighborhoodOptions").options.length === 0 && locationForm.elements.neighborhood.placeholder === "Mahalle giriniz";
      const customerLocationDefaultsCheck = { city: defaultCity, district: defaultDistrict, address: defaultAddress, editKeepsBlank: customerFormLocationDefaults({ city: "", district: "", address: "" }).city === "", cities: locationCities.length, hasDefaultCity: locationCities.includes("\u0130zmir"), districts: balikesirDistricts.length, hasGonen: balikesirDistricts.includes("G\u00f6nen"), neighborhoods: balikesirNeighborhoods.length, hasAkcakoy: balikesirNeighborhoods.includes("Ak\u00e7ak\u00f6y"), streets: locationStreets.length, hasAtaturkStreet: locationStreets.includes("Atat\u00fcrk Caddesi"), otherCityReset, cityReturn, nonGonenDistrict, comboOptionCount, comboUsesCustomPopup, comboHidesWhenNoMatch, comboRecoversAfterNoMatch, comboSelectWorks, comboClosesAfterSelection, keyboardHighlightedDistrict, keyboardSelectedDistrict };
      locationForm.remove();
      openDialog("QA customer type", "CRM", customerForm({}), () => true, "Save");
      const customerFormElement = document.querySelector("#dialogForm"), companyInput = customerFormElement.elements.company_name, taxInput = customerFormElement.elements.tax_number, taxOfficeInput = customerFormElement.elements.tax_office, identityInput = customerFormElement.elements.tc_no;
      const serviceTypeInput = customerFormElement.elements.service_type, serviceTypeOptions = [...document.querySelector("#customerServiceTypeOptions").options].map(option => option.value);
      const individualRadio = customerFormElement.querySelector('input[name="type"][value="Bireysel"]'), corporateRadio = customerFormElement.querySelector('input[name="type"][value="Kurumsal"]');
      companyInput.value = "QA Company"; taxInput.value = "1234567890"; taxOfficeInput.value = "QA Office"; identityInput.value = "12345678901";
      serviceTypeInput.value = "Custom Repair";
      const initiallyIndividual = individualRadio.checked && companyInput.readOnly && taxInput.readOnly && taxOfficeInput.readOnly && !identityInput.readOnly;
      corporateRadio.click();
      const corporateState = !companyInput.readOnly && !taxInput.readOnly && !taxOfficeInput.readOnly && identityInput.readOnly && new FormData(customerFormElement).get("type") === "Kurumsal" && new FormData(customerFormElement).get("company_name") === "QA Company";
      individualRadio.click();
      const restoredIndividual = companyInput.readOnly && taxInput.readOnly && taxOfficeInput.readOnly && !identityInput.readOnly && new FormData(customerFormElement).get("tc_no") === "12345678901";
      document.querySelector("#dialogCancel")?.click();
      const customerTypeCheck = { initiallyIndividual, corporateState, restoredIndividual, serviceTypeOptions, serviceTypeEditable: serviceTypeInput.tagName === "INPUT" && serviceTypeInput.getAttribute("list") === "customerServiceTypeOptions" && new FormData(customerFormElement).get("service_type") === "Custom Repair" };
      const shortcutOriginal = { page, currentSector, navigate, render, serviceDialog, maintenanceDialog, openDialog, customerForm, vehicleShortcut: window.openAutomotiveVehicleShortcut, setTimeout: window.setTimeout };
      const shortcutChecks = { technical: { routes: [], newService: 0, newCustomer: 0, vehicle: 0, maintenance: 0 }, automotive: { routes: [], newService: 0, newCustomer: 0, vehicle: 0, maintenance: 0 } };
      const renderDashboardShortcuts = sector => {
        page = "dashboard"; currentSector = sector; render = shortcutOriginal.render; render();
        if (!document.querySelector("[data-dashboard-shortcut]")) document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
        return [...document.querySelectorAll("[data-dashboard-shortcut]")];
      };
      const dispatchDashboardShortcuts = (sector, output) => {
        const cards = renderDashboardShortcuts(sector);
        output.cardCount = cards.length;
        output.targets = cards.map(card => card.dataset.dashboardShortcut);
        navigate = route => output.routes.push(route); render = () => {};
        serviceDialog = () => { output.newService += 1; };
        maintenanceDialog = () => { output.maintenance += 1; };
        openDialog = () => { output.newCustomer += 1; };
        customerForm = () => "";
        window.openAutomotiveVehicleShortcut = () => { output.vehicle += 1; };
        const deferred = [];
        window.setTimeout = callback => { deferred.push(callback); return deferred.length; };
        cards.forEach(card => card.click());
        deferred.forEach(callback => callback());
      };
      dispatchDashboardShortcuts("teknik_servis", shortcutChecks.technical);
      dispatchDashboardShortcuts("otomotiv", shortcutChecks.automotive);
      page = shortcutOriginal.page; currentSector = shortcutOriginal.currentSector;
      navigate = shortcutOriginal.navigate; render = shortcutOriginal.render; serviceDialog = shortcutOriginal.serviceDialog; maintenanceDialog = shortcutOriginal.maintenanceDialog; openDialog = shortcutOriginal.openDialog; customerForm = shortcutOriginal.customerForm; window.openAutomotiveVehicleShortcut = shortcutOriginal.vehicleShortcut; window.setTimeout = shortcutOriginal.setTimeout;
      if (page === "dashboard" && !document.querySelector("[data-dashboard-shortcut]")) document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      render();
      db.customers = [{ id: 71, name: "QA Customer", balances: { TRY: 0, USD: 0, EUR: 0 } }];
      db.personnel = [{ id: 8, name: "QA Tech" }];
      db.stockLocations = [];
      db.appointments = [{ id: 91, customerId: 71, customer: "QA Customer", title: "QA Calendar Slot", description: "QA Calendar Slot", date: "2026-10-13", time: "14:30", technician: "QA Tech", technician_name: "QA Tech", status: "Planlandi", color: "#2563EB", priority: "Normal" }];
      page = "appointments";
      appointmentWeekOffset = 0;
      ayecAppointmentView = "week";
      ayecAppointmentTechnician = "all";
      ayecAppointmentLocation = "all";
      document.documentElement.style.setProperty("--appointment-layout-offset", "178px");
      const shell = document.querySelector(".app-shell");
      shell.style.cssText += ";display:block;width:1300px;height:850px;min-height:850px;overflow:hidden";
      const sidebar = document.querySelector(".sidebar"); if (sidebar) sidebar.style.display = "none";
      const topbar = document.querySelector(".topbar"); if (topbar) topbar.style.display = "none";
      const main = document.querySelector(".main"); if (main) main.style.cssText += ";width:1300px;height:850px;overflow:hidden";
      const content = document.querySelector(".content"); if (content) content.style.cssText += ";padding:4px;width:1300px;height:850px;overflow:hidden";
      render();
      const slots = document.querySelectorAll(".appointment-ref-slot");
      const headers = Array.from(document.querySelectorAll(".appointment-ref-grid-head>b"), item => item.textContent.trim());
      return { slots: slots.length, headers, events: document.querySelectorAll(".appointment-ref-slot .appointment-ref-event").length, view: ayecAppointmentView, shortcutChecks, customerTypeCheck, customerLocationDefaultsCheck };
    })()`);
    const expectedTargets = ["new-service", "new-customer", "new-service", "services", "technician", "customers", "finance", "stock", "appointments", "offers", "finance", "backup"];
    const expectedRoutes = ["services", "technician", "customers", "finance", "stock", "appointments", "offers", "finance", "backup"];
    if (
      state.slots !== 77 || state.events !== 1 || state.headers.length !== 8 ||
      state.customerLocationDefaultsCheck.city !== "Bal\u0131kesir" || state.customerLocationDefaultsCheck.district !== "G\u00f6nen" || state.customerLocationDefaultsCheck.address !== "" || !state.customerLocationDefaultsCheck.editKeepsBlank ||
      state.customerLocationDefaultsCheck.cities !== 4 || !state.customerLocationDefaultsCheck.hasDefaultCity || state.customerLocationDefaultsCheck.districts !== 20 || !state.customerLocationDefaultsCheck.hasGonen ||
      state.customerLocationDefaultsCheck.neighborhoods !== 23 || !state.customerLocationDefaultsCheck.hasAkcakoy || state.customerLocationDefaultsCheck.streets !== 15 || !state.customerLocationDefaultsCheck.hasAtaturkStreet ||
      state.customerLocationDefaultsCheck.comboOptionCount !== 4 || !state.customerLocationDefaultsCheck.comboUsesCustomPopup || !state.customerLocationDefaultsCheck.comboHidesWhenNoMatch || !state.customerLocationDefaultsCheck.comboRecoversAfterNoMatch || !state.customerLocationDefaultsCheck.comboSelectWorks || !state.customerLocationDefaultsCheck.comboClosesAfterSelection ||
      state.customerLocationDefaultsCheck.keyboardHighlightedDistrict !== "G\u00f6nen" || !state.customerLocationDefaultsCheck.keyboardSelectedDistrict ||
      !state.customerLocationDefaultsCheck.otherCityReset || !state.customerLocationDefaultsCheck.cityReturn || !state.customerLocationDefaultsCheck.nonGonenDistrict ||
      !state.customerTypeCheck.initiallyIndividual || !state.customerTypeCheck.corporateState || !state.customerTypeCheck.restoredIndividual || !state.customerTypeCheck.serviceTypeEditable ||
      JSON.stringify(state.customerTypeCheck.serviceTypeOptions) !== JSON.stringify(["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Sat\u0131\u015f"]) ||
      state.shortcutChecks.technical.cardCount !== 12 || JSON.stringify(state.shortcutChecks.technical.targets) !== JSON.stringify(expectedTargets) ||
      JSON.stringify(state.shortcutChecks.technical.routes) !== JSON.stringify(expectedRoutes) || state.shortcutChecks.technical.newService !== 2 || state.shortcutChecks.technical.newCustomer !== 1 ||
      state.shortcutChecks.automotive.cardCount !== 12 || state.shortcutChecks.automotive.vehicle !== 1 || state.shortcutChecks.automotive.newCustomer !== 1 ||
      state.shortcutChecks.automotive.newService !== 0 || state.shortcutChecks.automotive.maintenance !== 1 ||
      JSON.stringify(state.shortcutChecks.automotive.routes) !== JSON.stringify(["vehicle-maintenance", ...expectedRoutes])
    ) throw new Error(`Unexpected weekly grid or shortcut actions: ${JSON.stringify(state)}`);
    await delay(300);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: 850, scale: 1 } });
    const screenshotPath = path.join(outputDir, "appointments-week-current-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const interaction = await evaluate(`(async () => {
      const empty = document.querySelector('.appointment-ref-slot[data-date="2026-10-14"][data-time="14:00"]');
      empty.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
      const fields = { date: document.querySelector('#dialogBody [name="date"]')?.value, time: document.querySelector('#dialogBody [name="time"]')?.value };
      const customerSearch = document.querySelector('#dialogBody [name="customerSearch"]');
      customerSearch.value = "QA Customer";
      customerSearch.dispatchEvent(new Event("input", { bubbles: true }));
      const customerLookup = { value: customerSearch.value, id: document.querySelector('#dialogBody [name="customerId"]')?.value, options: document.querySelector('#dialogBody #appointmentCustomers')?.options.length };
      document.querySelector("#dialogCancel")?.click();
      let stored = "";
      const transfer = { setData(_type, value) { stored = value; }, getData() { return stored; }, effectAllowed: "" };
      desktopWrite = async (_table, payload) => { window.__appointmentWrite = payload; };
      const card = document.querySelector('.appointment-ref-event');
      const drag = new Event("dragstart", { bubbles: true }); Object.defineProperty(drag, "dataTransfer", { value: transfer }); card.dispatchEvent(drag);
      const target = document.querySelector('.appointment-ref-slot[data-date="2026-10-14"][data-time="11:00"]');
      const drop = new Event("drop", { bubbles: true, cancelable: true }); Object.defineProperty(drop, "dataTransfer", { value: transfer }); target.dispatchEvent(drop);
      await new Promise(resolve => setTimeout(resolve, 80));
      const item = db.appointments.find(row => row.id === 91);
      const refreshButton = document.querySelector("[data-appointment-refresh]");
      let refreshUrl = "";
      apiFetch = async url => { refreshUrl = url; return { rows: [{ id: 92, customer_id: 71, customer_name: "QA Refreshed", date: "2026-10-15", time: "16:00", description: "Refreshed item", personnel_name: "QA Tech", status: "Bekliyor" }] }; };
      refreshButton.click();
      await new Promise(resolve => setTimeout(resolve, 80));
      return { fields, customerLookup, stored, date: item.date, time: item.time, write: window.__appointmentWrite, refreshUrl, refreshed: db.appointments.map(row => ({ id: row.id, customer: row.customer, time: row.time })) };
    })()`);
    if (interaction.fields.date !== "2026-10-14" || interaction.fields.time !== "14:00" || interaction.date !== "2026-10-14" || interaction.time !== "11:00" || interaction.write?.date !== "2026-10-14") throw new Error(`Appointment interaction check failed: ${JSON.stringify(interaction)}`);
    if (interaction.customerLookup.value !== "QA Customer" || interaction.customerLookup.id !== "71" || interaction.customerLookup.options !== 1) throw new Error(`Appointment customer lookup failed: ${JSON.stringify(interaction.customerLookup)}`);
    if (interaction.refreshUrl !== "/api/desktop/table/appointments?limit=1000" || interaction.refreshed[0]?.id !== "92" || interaction.refreshed[0]?.time !== "16:00") throw new Error(`Appointment refresh check failed: ${JSON.stringify(interaction)}`);
    const reminder = await evaluate(`(async () => {
      document.body.insertAdjacentHTML("beforeend", genericShell(genericModules.reminders));
      let createPayload = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/personnel?limit=500") return { rows: [{ id: 8, name: "QA Tech" }] };
        if (url.startsWith("/api/desktop/table/reminders") && options.method === "POST") { createPayload = JSON.parse(options.body); return { id: 501 }; }
        if (url.startsWith("/api/desktop/table/reminders")) return { rows: [] };
        throw new Error("Unexpected reminder request: " + url);
      };
      await loadGenericModule(genericModules.reminders, "");
      const form = document.querySelector("#reminderCreateForm");
      form.elements.title.value = "QA reminder";
      form.elements.personnel.value = "8";
      form.elements.date.value = "2026-10-20";
      form.elements.description.value = "QA assignment";
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await new Promise(resolve => setTimeout(resolve, 120));
      return { createPayload };
    })()`);
    if (reminder.createPayload?.personnel_id !== 8 || reminder.createPayload?.personnel !== "QA Tech" || reminder.createPayload?.date !== "2026-10-20") throw new Error(`Reminder assignment check failed: ${JSON.stringify(reminder)}`);
    const shortcutState = await evaluate(`(() => { db.appointments = [{ id: 601, customer_id: 71, customer_name: "QA Customer", date: "2026-10-13", time: "10:00", description: "QA dashboard appointment", status: "Bekliyor" }]; page = "dashboard"; document.querySelector("#content").innerHTML = renderDashboard(); if(!document.querySelector(".dashboard-shortcut-overlay"))document.querySelector("[data-dashboard-shortcuts-toggle]")?.click(); const overlay=document.querySelector(".dashboard-shortcut-overlay"),grid=document.querySelector(".dashboard-shortcut-grid"),style=getComputedStyle(overlay); return { open: Boolean(overlay), cards: document.querySelectorAll("[data-dashboard-shortcut]").length, icons: document.querySelectorAll("[data-dashboard-shortcut] svg").length, overlayWidth:overlay?.getBoundingClientRect().width, overlayLeft:overlay?.getBoundingClientRect().left, inset:style.inset, position:style.position, gridWidth:grid?.getBoundingClientRect().width, columns:getComputedStyle(grid).gridTemplateColumns, closeVisible:overlay?.querySelector("[data-dashboard-shortcuts-close]")?.getBoundingClientRect().right <= innerWidth }; })()`);
    if (!shortcutState.open || shortcutState.cards !== 12 || shortcutState.icons !== 12) throw new Error(`Dashboard shortcut screen mismatch: ${JSON.stringify(shortcutState)}`);
    await evaluate(`document.querySelectorAll(".toast,.toast-container,.toast-stack").forEach(node => { node.style.display = "none"; })`);
    const shortcutScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: 850, scale: 1 } });
    const shortcutScreenshotPath = path.join(outputDir, "dashboard-shortcuts-headless.png");
    fs.writeFileSync(shortcutScreenshotPath, Buffer.from(shortcutScreenshot.data, "base64"));
    const dashboardAppointment = await evaluate(`(async () => {
      db.appointments = [{ id: 601, customer_id: 71, customer_name: "QA Customer", date: "2026-10-13", time: "10:00", description: "QA dashboard appointment", status: "Bekliyor" }];
      page = "dashboard";
      document.querySelector("#content").innerHTML = renderDashboard();
      const shortcutOverlay = { open: Boolean(document.querySelector(".dashboard-shortcut-overlay")), cards: document.querySelectorAll("[data-dashboard-shortcut]").length };
      document.querySelector("[data-dashboard-shortcuts-close]")?.click();
      await new Promise(resolve => setTimeout(resolve, 40));
      const shortcutOverlayClosed = !document.querySelector(".dashboard-shortcut-overlay");
      document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      const originalNavigate = navigate;
      let shortcutRoute = "";
      navigate = target => { shortcutRoute = target; };
      document.querySelector('[data-dashboard-shortcut="appointments"]')?.click();
      navigate = originalNavigate;
      document.querySelector("#content").innerHTML = renderDashboard();
      const rows = Array.from(document.querySelectorAll("[data-dashboard-appointment-row]"));
      let statusWrite = null;
      apiFetch = async (url, options = {}) => { if (url === "/api/desktop/table/appointments" && options.method === "POST") { statusWrite = JSON.parse(options.body); return { ok: true }; } throw new Error("Unexpected dashboard request: " + url); };
      rows[0]?.querySelector("[data-dashboard-appointment-status]")?.click();
      rows[0]?.querySelector('[data-dashboard-appointment-set][data-status="Tamamland\\u0131"]')?.click();
      await new Promise(resolve => setTimeout(resolve, 100));
      const updatedRow = document.querySelector('[data-dashboard-appointment-row="601"]');
      return { shortcutOverlay, shortcutOverlayClosed, shortcutRoute, count: document.querySelectorAll("[data-dashboard-appointment-row]").length, status: db.appointments[0].status, statusWrite, progress: document.querySelector(".dashboard-today-appointment-progress")?.textContent.trim(), rowRendered: Boolean(updatedRow) };
    })()`);
    if (!dashboardAppointment.shortcutOverlay.open || dashboardAppointment.shortcutOverlay.cards !== 12 || !dashboardAppointment.shortcutOverlayClosed || dashboardAppointment.shortcutRoute !== "appointments" || dashboardAppointment.count !== 1 || dashboardAppointment.status !== "Tamamland\u0131" || dashboardAppointment.statusWrite?.id !== 601 || dashboardAppointment.statusWrite?.status !== "Tamamland\u0131" || !dashboardAppointment.progress?.includes("1/1") || !dashboardAppointment.rowRendered) throw new Error(`Dashboard interaction check failed: ${JSON.stringify(dashboardAppointment)}`);
    const shortcutActions = await evaluate(`(async () => {
      currentSector = "teknik_servis";
      let serviceShortcutCalls = 0;
      const originalServiceDialog = serviceDialog;
      serviceDialog = () => { serviceShortcutCalls += 1; };
      document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      document.querySelector('[data-dashboard-shortcut="new-service"]')?.click();
      serviceDialog = originalServiceDialog;
      currentSector = "otomotiv";
      const originalMaintenanceDialog = maintenanceDialog;
      let maintenanceShortcutCalls = 0;
      maintenanceDialog = () => { maintenanceShortcutCalls += 1; };
      document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      document.querySelector('[data-dashboard-shortcut="new-service"]')?.click();
      await new Promise(resolve => setTimeout(resolve, 130));
      const automotiveServiceShortcut = { page, maintenanceShortcutCalls };
      maintenanceDialog = originalMaintenanceDialog;
      page = "dashboard"; document.querySelector("#content").innerHTML = renderDashboard();
      document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      document.querySelector('[data-dashboard-shortcut="vehicle-record"]')?.click();
      const customerSelect = document.querySelector('#dialogBody select[name="customerId"]');
      const picker = { open: Boolean(customerSelect), options: customerSelect?.options.length };
      if (customerSelect) customerSelect.value = "71";
      document.querySelector("#dialogForm")?.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 140));
      const vehicleFormElement = document.querySelector("#dialogForm");
      const vehicleForm = { plate: Boolean(document.querySelector('#dialogBody input[name="plate"]')), brand: Boolean(document.querySelector('#dialogBody input[name="brand"]')), model: Boolean(document.querySelector('#dialogBody input[name="model"]')) };
      let vehiclePayload = null;
      const originalApiFetch = apiFetch;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/customer_vehicles" && options.method === "POST") { vehiclePayload = JSON.parse(options.body); return { id: 88 }; }
        if (url.startsWith("/api/desktop/table/customer_vehicles")) return { rows: [] };
        return { rows: [] };
      };
      vehicleFormElement.elements.plate.value = "QA123";
      vehicleFormElement.elements.brand.value = "AYEC";
      vehicleFormElement.elements.model.value = "Test";
      vehicleFormElement.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 220));
      apiFetch = originalApiFetch;
      currentSector = "teknik_servis";
      const originalCustomerFetch = apiFetch, originalCustomers = db.customers;
      let customerPayload = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/customers" && options.method === "POST") { customerPayload = JSON.parse(options.body); return { id: 99 }; }
        return { rows: [] };
      };
      db.customers = [...originalCustomers];
      document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
      document.querySelector('[data-dashboard-shortcut="new-customer"]')?.click();
      const customerDialog = Boolean(document.querySelector('#dialogBody .customer-editor'));
      const newCustomerForm = document.querySelector("#dialogForm");
      if (newCustomerForm?.elements.name) newCustomerForm.elements.name.value = "QA Shortcut Customer";
      newCustomerForm?.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 180));
      const customerSaved = customerPayload?.name === "QA Shortcut Customer";
      apiFetch = originalCustomerFetch; db.customers = originalCustomers;
      currentSector = "teknik_servis";
      return { serviceShortcutCalls, automotiveServiceShortcut, picker, vehicleForm, vehiclePayload, customerDialog, customerSaved };
    })()`);
    if (shortcutActions.serviceShortcutCalls !== 1 || shortcutActions.automotiveServiceShortcut?.page !== "vehicle-maintenance" || shortcutActions.automotiveServiceShortcut?.maintenanceShortcutCalls !== 1 || !shortcutActions.picker.open || shortcutActions.picker.options !== 2 || !shortcutActions.vehicleForm.plate || !shortcutActions.vehicleForm.brand || !shortcutActions.vehicleForm.model || shortcutActions.vehiclePayload?.customer_id !== 71 || shortcutActions.vehiclePayload?.plate !== "QA123" || !shortcutActions.customerDialog || !shortcutActions.customerSaved) throw new Error(`Dashboard shortcut action mismatch: ${JSON.stringify(shortcutActions)}`);
    const customDeviceType = await evaluate(`(async () => {
      const originalApiFetch = apiFetch, originalSector = currentSector, originalCustomers = db.customers;
      let devicePayload = null;
      const intakePhotos = [];
      db.customers = [{ id: 71, name: "QA Customer", phone: "5551234567", balances: { TRY: 0, USD: 0, EUR: 0 }, services: [{ device_type: "Laptop / Notebook", brand: "QA Brand", model: "QA Model" }, { device_type: "3D Printer", brand: "Prusa", model: "Prusa Mini" }] }];
      currentSector = "teknik_servis";
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/devices" && options.method === "POST") { devicePayload = JSON.parse(options.body); return { id: 777 }; }
        if (url === "/api/desktop/external-tracking/photos" && options.method === "POST") { intakePhotos.push(JSON.parse(options.body)); return { id: 800 + intakePhotos.length }; }
        if (url === "/api/desktop/bootstrap") return {};
        if (url.startsWith("/api/desktop/table/device_brands")) return { rows: [{ device_type: "Laptop / Notebook", brand: "Catalog Brand", is_active: 1 }] };
        if (url.startsWith("/api/desktop/table/fast_notes")) return { rows: [{ category: "Ar\u0131za H\u0131zl\u0131 Se\u00e7imi", label: "QA Fan Noise", is_active: 1, display_order: 0 }, { category: "Aksesuar", label: "QA Adapter", is_active: 1, display_order: 0 }] };
        return { rows: [] };
      };
      serviceDialog();
      await new Promise(resolve => setTimeout(resolve, 60));
      const form = document.querySelector("#dialogForm"), type = form.elements.device_type;
      const brand = form.elements.brand, model = form.elements.model, modelList = document.querySelector("#serviceModelOptions");
      const initialBrands = [...document.querySelector("#serviceBrandOptions").options].map(option => option.value);
      const historicalTypeOption = [...type.options].some(option => option.value === "3D Printer");
      type.value = "3D Printer"; type.dispatchEvent(new Event("change", { bubbles: true }));
      const historicalTypeBrands = [...document.querySelector("#serviceBrandOptions").options].map(option => option.value);
      brand.value = "Prusa"; brand.dispatchEvent(new Event("change", { bubbles: true }));
      const historicalTypeModels = [...modelList.options].map(option => option.value);
      type.value = "Laptop / Notebook"; type.dispatchEvent(new Event("change", { bubbles: true }));
      brand.value = "QA Brand"; brand.dispatchEvent(new Event("change", { bubbles: true }));
      const catalogModels = [...modelList.options].map(option => option.value);
      const dynamicFault = document.querySelector("[data-service-fault-note-options] button");
      const accessoryInput = [...document.querySelectorAll('[data-service-accessory-options] input[name="accessory_option"]')].find(input => input.value === "QA Adapter");
      dynamicFault?.click(); if (accessoryInput) accessoryInput.click();
      const dynamicNotes = { fault: dynamicFault?.textContent, selected: document.querySelector("[data-service-fault-selected]")?.textContent, accessory: accessoryInput?.checked };
      const field = document.querySelector("[data-service-other-device]"), other = form.elements.other_device_type;
      const initiallyHidden = field.hidden;
      type.value = "Di\u011fer"; type.dispatchEvent(new Event("change", { bubbles: true }));
      const visibleAndRequired = !field.hidden && other.required;
      other.value = "CCTV Camera";
      const transfer = new DataTransfer(), png = new Blob([new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10])], { type: "image/png" });
      for (let index = 0; index < 6; index++) transfer.items.add(new File([png], "intake-" + index + ".png", { type: "image/png", lastModified: index + 1 }));
      form.elements.device_photo.files = transfer.files;
      form.elements.device_photo.dispatchEvent(new Event("change", { bubbles: true }));
      const selectedPhotoCount = document.querySelectorAll("[data-service-photo-selected] .service-photo-selected-item").length;
      const customerSearch = form.querySelector(".service-customer-search");
      customerSearch.value = "QA Customer"; customerSearch.dispatchEvent(new Event("input", { bubbles: true }));
      const customerLookup = { id: form.elements.customerId.value, name: form.elements.customer_name.value, phone: form.elements.customer_phone_input.value };
      form.elements.customer_phone_input.value = "5551234567";
      form.elements.fault.value = "QA service intake";
      form.elements.open_form.checked = false;
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 180));
      document.querySelector("#dialogCancel")?.click(); apiFetch = originalApiFetch; currentSector = originalSector; db.customers = originalCustomers;
      return { initialBrands, historicalTypeOption, historicalTypeBrands, historicalTypeModels, catalogModels, dynamicNotes, modelUsesDatalist: model.getAttribute("list") === "serviceModelOptions", customerLookup, initiallyHidden, visibleAndRequired, selectedPhotoCount, intakePhotos, savedDeviceType: devicePayload?.device_type, savedCustomerId: devicePayload?.customer_id, savedFault: devicePayload?.fault_description, savedAccessories: devicePayload?.accessories };
    })()`);
    if (customDeviceType.customerLookup?.id !== "71" || customDeviceType.customerLookup?.name !== "QA Customer" || customDeviceType.customerLookup?.phone !== "5551234567" || customDeviceType.savedCustomerId !== 71 || customDeviceType.dynamicNotes?.fault !== "QA Fan Noise" || customDeviceType.dynamicNotes?.selected !== "QA Fan Noise" || customDeviceType.dynamicNotes?.accessory !== true || !customDeviceType.initialBrands.includes("QA Brand") || !customDeviceType.initialBrands.includes("Catalog Brand") || !customDeviceType.historicalTypeOption || !customDeviceType.historicalTypeBrands.includes("Prusa") || !customDeviceType.historicalTypeModels.includes("Prusa Mini") || !customDeviceType.catalogModels.includes("QA Model") || !customDeviceType.modelUsesDatalist || !customDeviceType.initiallyHidden || !customDeviceType.visibleAndRequired || customDeviceType.savedDeviceType !== "CCTV Camera" || !customDeviceType.savedFault?.includes("QA Fan Noise") || !customDeviceType.savedFault?.includes("QA service intake") || customDeviceType.savedAccessories !== "QA Adapter" || customDeviceType.selectedPhotoCount !== 5 || customDeviceType.intakePhotos.length !== 5 || customDeviceType.intakePhotos.some(photo => photo.stage !== "Giri\u015f" || !photo.data || !photo.tracking_no)) throw new Error(`Custom device type workflow mismatch: ${JSON.stringify(customDeviceType)}`);
    const maintenanceVehicleLookup = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      const rows = [
        { id: 72, customer_id: 71, plate: "QA123", brand: "AYEC", model: "Test", year: 2024, vehicle_type: "Sedan", engine_type: "ICE", fuel_type: "Benzin", last_known_odometer: 42000, inspection_due_date: "2027-01-01" },
        { id: 73, customer_id: 71, plate: "QA999", brand: "Other", model: "Lookup", year: 2022, vehicle_type: "SUV", engine_type: "EV", fuel_type: "Elektrik", last_known_odometer: 12000 }
      ];
      apiFetch = async url => url.startsWith("/api/desktop/table/customer_vehicles") ? { rows } : { rows: [] };
      await maintenanceDialog({});
      const customer = document.querySelector('#dialogBody [name="customer_id"]');
      customer.value = "71";
      customer.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 80));
      const vehicle = document.querySelector('#dialogBody [name="vehicle_id"]');
      const choices = vehicle?.options.length;
      vehicle.value = "72";
      vehicle.dispatchEvent(new Event("change", { bubbles: true }));
      const selected = { id: vehicle.value, plate: document.querySelector('#dialogBody [name="vehicle_plate"]')?.value, brand: document.querySelector('#dialogBody [name="vehicle_brand"]')?.value, odometer: document.querySelector('#dialogBody [name="odometer"]')?.value };
      const plate = document.querySelector('#dialogBody [name="vehicle_plate"]');
      plate.value = "QA999";
      plate.dispatchEvent(new Event("blur", { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 80));
      const byPlate = { id: vehicle.value, plate: plate.value, brand: document.querySelector('#dialogBody [name="vehicle_brand"]')?.value, customer: customer.value };
      document.querySelector("#dialogCancel")?.click();
      apiFetch = originalApiFetch;
      return { choices, selected, byPlate };
    })()`);
    if (maintenanceVehicleLookup.choices !== 3 || maintenanceVehicleLookup.selected.id !== "72" || maintenanceVehicleLookup.selected.plate !== "QA123" || maintenanceVehicleLookup.selected.brand !== "AYEC" || maintenanceVehicleLookup.selected.odometer !== "42000" || maintenanceVehicleLookup.byPlate.id !== "73" || maintenanceVehicleLookup.byPlate.plate !== "QA999" || maintenanceVehicleLookup.byPlate.brand !== "Other" || maintenanceVehicleLookup.byPlate.customer !== "71") throw new Error(`Maintenance vehicle lookup mismatch: ${JSON.stringify(maintenanceVehicleLookup)}`);
    const maintenanceAddVehicle = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      let savedPayload = null;
      const rows = [{ id: 88, customer_id: 71, plate: "QA888", brand: "AYEC", model: "Added", last_known_odometer: 1234 }];
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/customer_vehicles" && options.method === "POST") { savedPayload = JSON.parse(options.body); return { id: 88 }; }
        if (url.startsWith("/api/desktop/table/customer_vehicles")) return { rows };
        return { rows: [] };
      };
      await maintenanceDialog({ notes: "Preserve this draft", _draftItems: [{ item_type: "oil_change", item_label: "Oil", performed: true, interval_days: 30, interval_km: 5000 }] });
      const customer = document.querySelector('#dialogBody [name="customer_id"]'); customer.value = "71";
      document.querySelector('#dialogBody [data-maintenance-add-vehicle]').click();
      await new Promise(resolve => setTimeout(resolve, 130));
      const vehicleEditorOpen = Boolean(document.querySelector('#dialogBody [name="plate"]'));
      const vehicleForm = document.querySelector("#dialogForm");
      vehicleForm.elements.plate.value = "QA888"; vehicleForm.elements.brand.value = "AYEC"; vehicleForm.elements.model.value = "Added";
      vehicleForm.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 180));
      const returned = {
        notes: document.querySelector('#dialogBody [name="notes"]')?.value,
        vehicleId: document.querySelector('#dialogBody [name="vehicle_id"]')?.value,
        itemCount: document.querySelectorAll('#dialogBody [data-maintenance-item]').length,
        preservedItem: [...document.querySelectorAll('#dialogBody [data-maintenance-item]')].some(item => item.dataset.maintenanceItem === "oil_change" && item.querySelector(".maintenance-performed")?.checked && item.querySelector(".maintenance-km")?.value === "5000")
      };
      document.querySelector("#dialogCancel")?.click(); apiFetch = originalApiFetch;
      return { vehicleEditorOpen, savedPayload, returned };
    })()`);
    if (!maintenanceAddVehicle.vehicleEditorOpen || maintenanceAddVehicle.savedPayload?.customer_id !== 71 || maintenanceAddVehicle.savedPayload?.plate !== "QA888" || maintenanceAddVehicle.returned.notes !== "Preserve this draft" || maintenanceAddVehicle.returned.vehicleId !== "88" || !maintenanceAddVehicle.returned.preservedItem) throw new Error(`Maintenance add-vehicle mismatch: ${JSON.stringify(maintenanceAddVehicle)}`);
    const maintenanceAddCustomer = await evaluate(`(async () => {
      const originalApiFetch = apiFetch, originalCustomers = db.customers;
      let customerPayload = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/customers" && options.method === "POST") { customerPayload = JSON.parse(options.body); return { id: 82 }; }
        return { rows: [] };
      };
      db.customers = [...originalCustomers];
      await maintenanceDialog({ notes: "Keep customer draft" });
      document.querySelector('#dialogBody [data-maintenance-add-customer]').click();
      await new Promise(resolve => setTimeout(resolve, 120));
      const customerForm = document.querySelector("#dialogForm"); customerForm.elements.name.value = "QA Added Customer";
      customerForm.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 180));
      const result = { payloadName: customerPayload?.name, customerId: document.querySelector('#dialogBody [name="customer_id"]')?.value, notes: document.querySelector('#dialogBody [name="notes"]')?.value };
      document.querySelector("#dialogCancel")?.click(); apiFetch = originalApiFetch; db.customers = originalCustomers;
      return result;
    })()`);
    if (maintenanceAddCustomer.payloadName !== "QA Added Customer" || maintenanceAddCustomer.customerId !== "82" || maintenanceAddCustomer.notes !== "Keep customer draft") throw new Error(`Maintenance add-customer mismatch: ${JSON.stringify(maintenanceAddCustomer)}`);
    await evaluate(`(() => { document.querySelector(".dashboard-today-appointments-panel")?.scrollIntoView({ block: "start" }); document.querySelectorAll(".toast,.toast-container,.toast-stack").forEach(node => { node.style.display = "none"; }); })()`);
    const dashboardScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: 850, scale: 1 } });
    const dashboardScreenshotPath = path.join(outputDir, "dashboard-today-appointments-headless.png");
    fs.writeFileSync(dashboardScreenshotPath, Buffer.from(dashboardScreenshot.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${exceptions.join(" | ")}`);
    process.stdout.write(`${JSON.stringify({ ...state, appointmentStatusCheck, maintenancePdfCheck, interaction, reminder, shortcutState, dashboardAppointment, shortcutActions, maintenanceVehicleLookup, customDeviceType, screenshot: screenshotPath, dashboardScreenshot: dashboardScreenshotPath, shortcutsScreenshot: shortcutScreenshotPath, browserExceptions: exceptions.length })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
