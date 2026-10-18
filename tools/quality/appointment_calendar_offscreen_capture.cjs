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
    const state = await evaluate(`(async () => {
      const NativeDate = Date;
      window.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : ["${fixedDate}"])); } static now() { return new NativeDate("${fixedDate}").valueOf(); } };
      const authRoot = document.querySelector("#authRoot");
      if (authRoot) { authRoot.hidden = true; authRoot.replaceChildren(); }
      window.showAuth = () => {};
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
      db.personnel = [{ id: 8, name: "QA Tech", role: "Teknisyen", active: 1 }];
      db.stockLocations = [];
      db.appointments = [{ id: 91, customerId: 71, customer: "QA Customer", title: "QA Calendar Slot", description: "QA Calendar Slot", date: "2026-10-13", time: "14:30", technician: "QA Tech", technician_name: "QA Tech", status: "Planlandi", color: "#2563EB", priority: "Normal" }];
      navigate("appointments");
      ayecAppointmentPersonnelRows = null;
      ayecAppointmentPersonnelPromise = null;
      const originalPersonnelApiFetch = apiFetch;
      window.__appointmentOriginalPersonnelApiFetch = originalPersonnelApiFetch;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/personnel?limit=1000&include_deleted=1") return { rows: [
          { id: 8, name: "QA Tech", role: "Teknisyen", active: 1 },
          { id: 12, name: "No Appointment Tech", role: "Muhasebe", active: 1 },
          { id: 13, name: "Inactive QA", role: "Teknisyen", active: 0 },
          { id: 14, name: "Archived QA", role: "Teknisyen", active: 0, is_deleted: 1 }
        ] };
        return originalPersonnelApiFetch(url, options);
      };
      appointmentWeekOffset = 0;
      ayecAppointmentView = "week";
      ayecAppointmentTechnician = "all";
      ayecAppointmentLocation = "all";
      const shell = document.querySelector(".app-shell"), sidebar = document.querySelector(".sidebar"), topbar = document.querySelector(".topbar"), main = document.querySelector(".main"), content = document.querySelector(".content");
      window.__appointmentShellStyles = { root: document.documentElement.style.cssText, shell: shell?.style.cssText, sidebar: sidebar?.style.cssText, topbar: topbar?.style.cssText, main: main?.style.cssText, content: content?.style.cssText };
      document.documentElement.style.setProperty("--appointment-layout-offset", "178px");
      shell.style.cssText += ";display:block;width:1300px;height:850px;min-height:850px;overflow:hidden";
      if (sidebar) sidebar.style.display = "none";
      if (topbar) topbar.style.display = "none";
      if (main) main.style.cssText += ";width:1300px;height:850px;overflow:hidden";
      if (content) content.style.cssText += ";padding:4px;width:1300px;height:850px;overflow:hidden";
      render();
      await new Promise(resolve => setTimeout(resolve, 80));
      const canceledStatuses = [String.fromCharCode(304) + "ptal", "Iptal", "Tamamland" + String.fromCharCode(305), "Cancelled"];
      const plannedStatusCheck = { pendingVisible: !apAppointmentClosed("Bekliyor"), closedHidden: canceledStatuses.every(apAppointmentClosed) };
      appointmentDialog(db.appointments[0]);
      const editTimeMatchesDesktop = document.querySelector('#dialogBody [name="time"]')?.value === "14:00";
      document.querySelector("#dialogCancel")?.click();
      const slots = document.querySelectorAll(".appointment-ref-slot");
      const headers = Array.from(document.querySelectorAll(".appointment-ref-grid-head>b"), item => item.textContent.trim());
      const technicianOptions = Array.from(document.querySelectorAll("#appointmentTechnician option"), item => item.textContent.trim());
      const technicianStatus = document.querySelector(".appointment-ref-layout aside section:nth-child(2) header b")?.textContent.trim();
      const technicianRows = Array.from(document.querySelectorAll(".appointment-ref-tech-row"), item => item.querySelector("b")?.textContent.trim());
      const previousAppointments = db.appointments;
      db.appointments = [
        { id: 91, customerId: 71, customer: "QA Customer", title: "Planned", date: "2026-10-13", time: "14:00", technician: "QA Tech", status: "Planlandi", urgency: "Kritik" },
        { id: 92, customerId: 71, customer: "QA Customer", title: "Delivered", date: "2026-10-14", time: "14:00", technician: "QA Tech", status: "Teslim Edildi", urgency: "Normal" },
        { id: 93, customerId: 71, customer: "QA Customer", title: "Completed", date: "2026-10-15", time: "14:00", technician: "QA Tech", status: "Tamamlandi", urgency: "Normal" }
      ];
      render();
      const appointmentMetrics = Array.from(document.querySelectorAll(".appointment-ref-metrics article"), item => item.querySelector("b")?.textContent.trim());
      db.appointments = previousAppointments;
      render();
      return { slots: slots.length, headers, events: document.querySelectorAll(".appointment-ref-slot .appointment-ref-event").length, view: ayecAppointmentView, technicianOptions, technicianStatus, technicianRows, appointmentMetrics, editTimeMatchesDesktop, plannedStatusCheck, shortcutChecks, customerTypeCheck, customerLocationDefaultsCheck };
    })()`);
    const expectedTargets = ["new-service", "new-customer", "new-service", "services", "technician", "customers", "finance", "stock", "appointments", "offers", "finance", "backup"];
    const expectedRoutes = ["services", "technician", "customers", "finance", "stock", "appointments", "offers", "finance", "backup"];
    if (
      state.slots !== 77 || state.events !== 1 || state.headers.length !== 8 || !state.editTimeMatchesDesktop || !state.plannedStatusCheck.pendingVisible || !state.plannedStatusCheck.closedHidden || JSON.stringify(state.technicianOptions) !== JSON.stringify(["T\u00fcm Teknisyenler (2)", "No Appointment Tech", "QA Tech"]) || state.technicianStatus !== "2/4 Aktif" || JSON.stringify(state.technicianRows) !== JSON.stringify(["No Appointment Tech", "QA Tech"]) || JSON.stringify(state.appointmentMetrics) !== JSON.stringify(["1 Randevu", "1 G\u00f6revli", "%33", "1 Servis"]) ||
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
    await evaluate(`(() => { document.querySelectorAll(".toast").forEach(node=>node.remove());window.__appointmentVisualFixture={appointments:db.appointments,personnel:db.personnel,personnelRows:ayecAppointmentPersonnelRows};db.appointments=[];const people=Array.from({length:6},(_,index)=>({id:index+1,name:"QA Tech "+String(index+1).padStart(2,"0"),role:"Teknisyen",active:1}));db.personnel=people;ayecAppointmentPersonnelRows=people;ayecAppointmentPersonnelPromise=null;render();return true;})()`);
    await delay(250);
    await evaluate(`(() => { const s=window.__appointmentShellStyles||{};document.documentElement.style.cssText=s.root||"";const restore=(selector,value)=>{const node=document.querySelector(selector);if(node&&value!==undefined)node.style.cssText=value;};restore(".app-shell",s.shell);restore(".sidebar",s.sidebar);restore(".topbar",s.topbar);restore(".main",s.main);restore(".content",s.content);render();return true;})()`);
    if (process.env.AYEC_CALENDAR_MATCHED_VIEWPORT === "1") {
      const width = Number(process.env.AYEC_VIEWPORT_WIDTH || 1280);
      const height = Number(process.env.AYEC_VIEWPORT_HEIGHT || 1024);
      const contentWidth = Number(process.env.AYEC_CALENDAR_CONTENT_WIDTH || width);
      await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
      await evaluate(`(() => {
        const width=${width},height=${height},contentWidth=${contentWidth};
        const s=window.__appointmentShellStyles||{};
        document.documentElement.style.cssText=s.root||"";
        const restore=(selector,value)=>{const node=document.querySelector(selector);if(node&&value!==undefined)node.style.cssText=value;};
        restore(".app-shell",s.shell);restore(".sidebar",s.sidebar);restore(".topbar",s.topbar);restore(".main",s.main);restore(".content",s.content);
        const shell=document.querySelector(".app-shell"),sidebar=document.querySelector(".sidebar"),topbar=document.querySelector(".topbar"),statusBar=document.querySelector("#shellStatusBar");
        if(shell)shell.style.cssText+=";display:block;width:"+width+"px;height:"+height+"px;min-height:"+height+"px;overflow:hidden";
        if(sidebar)sidebar.style.display="none";if(topbar)topbar.style.display="none";if(statusBar)statusBar.style.display="none";
        const main=document.querySelector(".main"),content=document.querySelector(".content");
        if(main)main.style.cssText+=";width:"+contentWidth+"px;height:"+height+"px;overflow:hidden";
        if(content)content.style.cssText+=";padding:0;width:"+contentWidth+"px;height:"+height+"px;overflow:hidden";
        ayecAppointmentView="week";appointmentWeekOffset=0;render();return true;
      })()`);
      await delay(300);
      const geometry = await evaluate(`(() => {const selectors=[".appointment-ref-page",".appointment-ref-toolbar",".appointment-ref-nav-row",".appointment-ref-title",".appointment-ref-views",".appointment-ref-filter-row",".appointment-ref-metrics",".appointment-ref-layout",".appointment-ref-calendar",".appointment-ref-legend"];return Object.fromEntries(selectors.map(selector=>{const node=document.querySelector(selector),r=node?.getBoundingClientRect();return[selector,r?{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}:null]}))})()`);
      const headerDateCheck = await evaluate(`(() => {const headers=[...document.querySelectorAll(".appointment-ref-grid-head>b:not(:first-child)")];return{count:headers.length,allHaveWeekday:headers.every(node=>node.querySelector("span")?.textContent.trim()),allHaveDate:headers.every(node=>/^\\d{2}\\.\\d{2}\\.\\d{4}$/.test(node.querySelector("small")?.textContent.trim()||"")),firstWeekday:headers[0]?.querySelector("span")?.textContent.trim(),firstDate:headers[0]?.querySelector("small")?.textContent.trim()}})()`); if(headerDateCheck.count!==7||!headerDateCheck.allHaveWeekday||!headerDateCheck.allHaveDate||headerDateCheck.firstDate!=="12.10.2026") throw new Error(`Calendar header date layout mismatch: ${JSON.stringify(headerDateCheck)}`);
      const toolbarDateCheck = await evaluate(`(() => {const title=document.querySelector(".appointment-ref-title>b"),period=document.querySelector(".appointment-ref-title small"),week=document.querySelector(".appointment-ref-grid-head>b:not(:first-child) span");return{page:document.body.dataset.page,period:period?.textContent.trim(),titleFont:title?getComputedStyle(title).fontSize:"",periodFont:period?getComputedStyle(period).fontSize:"",weekdayFont:week?getComputedStyle(week).fontSize:""}})()`);
      if(toolbarDateCheck.period!=="12.10.2026 - 18.10.2026") throw new Error(`Calendar toolbar date format mismatch: ${JSON.stringify(toolbarDateCheck)}`);
      const matched = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: contentWidth, height, scale: 1 } });
      const matchedPath = path.join(outputDir, `appointments-week-matched-${contentWidth}x${height}.png`);
      fs.writeFileSync(matchedPath, Buffer.from(matched.data, "base64"));
      if (exceptions.length) throw new Error(`Calendar capture raised browser exceptions: ${JSON.stringify(exceptions)}`);
      process.stdout.write(`${JSON.stringify({ matchedViewport: [width, height], geometry, headerDateCheck, toolbarDateCheck, appointmentChecks: { editTimeMatchesDesktop: state.editTimeMatchesDesktop, plannedStatusCheck: state.plannedStatusCheck }, screenshot: matchedPath, browserExceptions: exceptions })}\n`);
      return;
    }
    await delay(250);
    const fullShellGeometry = await evaluate(`(() => {const rect=selector=>{const node=document.querySelector(selector);if(!node)return null;const r=node.getBoundingClientRect();return{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),display:getComputedStyle(node).display,background:getComputedStyle(node).backgroundColor,color:getComputedStyle(node).color,borderColor:getComputedStyle(node).borderColor};};return{viewport:[innerWidth,innerHeight],document:[document.documentElement.clientWidth,document.documentElement.clientHeight,document.documentElement.scrollWidth,document.documentElement.scrollHeight],shell:rect(".app-shell"),sidebar:rect(".sidebar"),brand:rect(".sidebar .brand"),brandMark:rect(".sidebar .brand-mark"),brandSector:rect("#sectorBrand"),sidebarPin:rect("#sidebarPin"),sidebarFooter:{panel:rect(".sidebar-bottom"),license:rect(".sidebar-license"),user:rect(".sidebar-bottom .user"),profile:rect("#profileBtn"),logout:rect("#logoutBtn")},topbar:rect(".topbar"),main:rect(".main"),content:rect(".content"),contentMetrics:(()=>{const node=document.querySelector(".content");const s=getComputedStyle(node);return{overflowX:s.overflowX,overflowY:s.overflowY,clientWidth:node.clientWidth,offsetWidth:node.offsetWidth,clientHeight:node.clientHeight,scrollHeight:node.scrollHeight}})(),mainMetrics:(()=>{const node=document.querySelector(".main");const s=getComputedStyle(node);return{overflowX:s.overflowX,overflowY:s.overflowY,clientWidth:node.clientWidth,offsetWidth:node.offsetWidth,clientHeight:node.clientHeight,scrollHeight:node.scrollHeight}})(),headerControls:{back:rect("#headerBackBtn"),logo:rect(".header-app-logo"),brand:rect(".header-app-name"),page:rect("#pageTitle"),search:rect(".global-search-wrap"),assistant:rect("#assistantHeaderBtn"),sync:rect("#syncNowBtn"),management:rect("#managementCenterBtn"),interfaceEdit:rect("#interfaceEditBtn"),notifications:rect("#notificationBtn"),settings:rect("#headerSettingsBtn"),theme:rect("#headerThemePicker"),profile:rect("#headerProfileActions"),quickAdd:rect('[data-action="quick-add"]'),topActions:rect(".top-actions"),topActionsChildren:[...document.querySelectorAll(".top-actions>*")].map(node=>{const r=node.getBoundingClientRect();return{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),id:node.id||"",className:String(node.className)}})},pageHead:rect(".page-head"),appointmentPage:rect(".appointment-ref-page"),toolbar:rect(".appointment-ref-toolbar"),toolbarStructure:{navRow:rect(".appointment-ref-nav-row"),period:rect(".appointment-ref-period"),title:rect(".appointment-ref-title"),titleText:rect(".appointment-ref-title b"),dateText:rect(".appointment-ref-title small"),views:rect(".appointment-ref-views"),filter:rect(".appointment-ref-filter-row"),periodButtons:[...document.querySelectorAll(".appointment-ref-period button")].map(node=>{const r=node.getBoundingClientRect();return[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}),viewButtons:[...document.querySelectorAll(".appointment-ref-views button")].map(node=>{const r=node.getBoundingClientRect();return[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}),filterLabels:[...document.querySelectorAll(".appointment-ref-filter-label")].map(node=>{const r=node.getBoundingClientRect();return[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}),filterSelects:[rect("#appointmentTechnician"),rect("#appointmentLocation")],actions:[rect('[data-action="add-appointment"]'),rect("[data-appointment-planned]"),rect("[data-appointment-refresh]")]},toolbarItems:[...document.querySelectorAll(".appointment-ref-toolbar button,.appointment-ref-toolbar label,.appointment-ref-toolbar select,.appointment-ref-toolbar strong")].map(node=>{const r=node.getBoundingClientRect();return{tag:node.tagName,className:String(node.className),id:node.id,text:(node.innerText||node.textContent||"").trim().replace(/\s+/g," ").slice(0,40),rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],style:{background:getComputedStyle(node).backgroundColor,color:getComputedStyle(node).color,border:getComputedStyle(node).borderColor,fontSize:getComputedStyle(node).fontSize,fontWeight:getComputedStyle(node).fontWeight,disabled:node.disabled}}}),metrics:rect(".appointment-ref-metrics"),layout:rect(".appointment-ref-layout"),calendar:rect(".appointment-ref-calendar"),calendarMetrics:(()=>{const node=document.querySelector(".appointment-ref-calendar");return{clientWidth:node.clientWidth,offsetWidth:node.offsetWidth,scrollWidth:node.scrollWidth,clientHeight:node.clientHeight,offsetHeight:node.offsetHeight,scrollHeight:node.scrollHeight}})(),calendarHeaderCells:[...document.querySelectorAll(".appointment-ref-grid-head>b")].map(node=>{const r=node.getBoundingClientRect();return[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}),calendarHourFirst:rect(".appointment-ref-hour"),calendarSlotFirst:rect(".appointment-ref-slot"),sidePanel:rect(".appointment-ref-layout>aside"),asideCards:[rect(".appointment-ref-layout>aside>.card:first-child"),rect(".appointment-ref-layout>aside>.card:last-child")],asideFirstHeader:rect(".appointment-ref-layout>aside>.card:first-child>header"),asideFirstTitle:rect(".appointment-ref-layout>aside>.card:first-child h2"),asideFirstCount:rect(".appointment-ref-layout>aside>.card:first-child header>b"),asideFirstList:rect(".appointment-ref-side-list"),asideSecondHeader:rect(".appointment-ref-layout>aside>.card:last-child>header"),asideSecondTitle:rect(".appointment-ref-layout>aside>.card:last-child h2"),asideSecondCount:rect(".appointment-ref-layout>aside>.card:last-child header>b"),asideTechnicianFrame:rect(".appointment-ref-tech-status"),asideTechnicianRows:[...document.querySelectorAll(".appointment-ref-tech-status .appointment-ref-tech-row")].map(node=>{const r=node.getBoundingClientRect();return[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}),asideTechnicianAction:rect(".appointment-ref-tech-status>button"),greenNodes:[...document.querySelectorAll("*")].filter(node=>{const style=getComputedStyle(node);return style.backgroundColor==="rgb(52, 211, 153)"||style.color==="rgb(52, 211, 153)"}).map(node=>{const r=node.getBoundingClientRect();return{tag:node.tagName,className:String(node.className),text:(node.innerText||"").trim().replace(/\s+/g," ").slice(0,30),background:getComputedStyle(node).backgroundColor,color:getComputedStyle(node).color,rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}}).filter(row=>row.rect[2]&&row.rect[3])};})()`);
    fullShellGeometry.calendarPaint = await evaluate(`(() => {const style=selector=>getComputedStyle(document.querySelector(selector));const calendar=style(".appointment-ref-calendar"),header=style(".appointment-ref-grid-head>b"),hour=style(".appointment-ref-hour"),slot=style(".appointment-ref-slot");return{theme:document.documentElement.dataset.theme,background:calendar.backgroundColor,header:header.backgroundColor,hourBackground:hour.backgroundColor,hourFont:hour.fontFamily,slot:slot.backgroundColor,gridLine:slot.borderBottomColor};})()`);
    if (fullShellGeometry.calendarPaint.background !== "rgb(13, 24, 41)" || fullShellGeometry.calendarPaint.header !== "rgb(13, 24, 41)" || fullShellGeometry.calendarPaint.slot !== "rgb(13, 24, 41)" || fullShellGeometry.calendarPaint.gridLine !== "rgb(27, 42, 66)" || !fullShellGeometry.calendarPaint.hourFont.includes("Segoe UI")) throw new Error(`Desktop calendar palette mismatch: ${JSON.stringify(fullShellGeometry.calendarPaint)}`);
    const fullShellRendered = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: 850, scale: 1 } });
    const fullShellScreenshotPath = path.join(outputDir, "appointments-full-shell-current-headless.png");
    fs.writeFileSync(fullShellScreenshotPath, Buffer.from(fullShellRendered.data, "base64"));
    const footerBoxes = fullShellGeometry.sidebarFooter;
    for (const [name, box, expected] of [
      ["panel", footerBoxes.panel, [0, 710, 260, 124]],
      ["license", footerBoxes.license, [12, 721, 236, 53]],
      ["logout", footerBoxes.logout, [12, 780, 236, 44]],
    ]) {
      const actual = box && [box.x, box.y, box.width, box.height];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Desktop sidebar footer geometry mismatch for ${name}: ${JSON.stringify({ actual, expected })}`);
    }
    for (const [name, box, expected] of [
      ["brand", fullShellGeometry.brand, [15, 85, 230, 100]],
      ["brandMark", fullShellGeometry.brandMark, [24, 113, 44, 44]],
      ["brandSector", fullShellGeometry.brandSector, [170, 126, 34, 18]],
      ["sidebarPin", fullShellGeometry.sidebarPin, [212, 94, 24, 24]],
    ]) {
      const actual = box && [box.x, box.y, box.width, box.height];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Desktop sidebar brand geometry mismatch for ${name}: ${JSON.stringify({ actual, expected })}`);
    }
    for (const [name, box, expected] of [
      ["content", fullShellGeometry.content, [260, 70, 1040, 764]],
      ["appointmentPage", fullShellGeometry.appointmentPage, [260, 70, 1040, 764]],
      ["appointmentToolbar", fullShellGeometry.toolbar, [264, 70, 1032, 91]],
      ["appointmentMetrics", fullShellGeometry.metrics, [264, 167, 1032, 57]],
      ["appointmentLayout", fullShellGeometry.layout, [264, 230, 1032, 596]],
      ["appointmentCalendar", fullShellGeometry.calendar, [264, 230, 740, 596]],
      ["appointmentSidePanel", fullShellGeometry.sidePanel, [1016, 230, 280, 596]],
      ["appointmentEventCard", fullShellGeometry.asideCards[0], [1016, 230, 280, 369]],
      ["appointmentEventScrollArea", fullShellGeometry.asideFirstList, [1031, 275, 250, 323]],
      ["appointmentTechnicianStatus", fullShellGeometry.asideTechnicianFrame, [1031, 608, 250, 203]],
      ["appointmentEventCount", fullShellGeometry.asideFirstCount, [1202, 245, 79, 20]],
      ["appointmentEventTitle", fullShellGeometry.asideFirstTitle, [1031, 245, 145, 20]],
      ["appointmentTechnicianAction", fullShellGeometry.asideTechnicianAction, [1042, 768, 228, 33]],
    ]) {
      const actual = box && [box.x, box.y, box.width, box.height];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Desktop appointments geometry mismatch for ${name}: ${JSON.stringify({ actual, expected })}`);
    }
    if (JSON.stringify(fullShellGeometry.asideTechnicianRows) !== JSON.stringify([[1042, 639, 228, 37], [1042, 682, 228, 37], [1042, 725, 228, 37]])) throw new Error(`Desktop technician row geometry mismatch: ${JSON.stringify(fullShellGeometry.asideTechnicianRows)}`);
    const expectedCalendarHeaders = [[265, 231, 80, 55], [345, 231, 93, 55], [438, 231, 93, 55], [531, 231, 93, 55], [624, 231, 93, 55], [717, 231, 92, 55], [809, 231, 92, 55], [901, 231, 92, 55]];
    if (JSON.stringify(fullShellGeometry.calendarHeaderCells) !== JSON.stringify(expectedCalendarHeaders)) throw new Error(`Desktop calendar header geometry mismatch: ${JSON.stringify(fullShellGeometry.calendarHeaderCells)}`);
    const toolbarStructure = fullShellGeometry.toolbarStructure;
    for (const [name, box, expected] of [
      ["toolbarNavRow", toolbarStructure.navRow, [273, 75, 1014, 36]],
      ["toolbarPeriod", toolbarStructure.period, [273, 77, 155, 32]],
      ["toolbarTitle", toolbarStructure.title, [438, 75, 212, 36]],
      ["toolbarTitleText", toolbarStructure.titleText, [438, 75, 186, 20]],
      ["toolbarDateText", toolbarStructure.dateText, [438, 97, 212, 14]],
      ["toolbarViews", toolbarStructure.views, [660, 77, 285, 32]],
      ["toolbarFilter", toolbarStructure.filter, [273, 115, 1014, 41]],
      ["toolbarTechnicianSelect", toolbarStructure.filterSelects[0], [356, 120, 150, 31]],
      ["toolbarLocationSelect", toolbarStructure.filterSelects[1], [584, 120, 147, 31]],
    ]) {
      const actual = box && [box.x, box.y, box.width, box.height];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Desktop appointments toolbar geometry mismatch for ${name}: ${JSON.stringify({ actual, expected })}`);
    }
    if (JSON.stringify(toolbarStructure.periodButtons) !== JSON.stringify([[273, 77, 32, 32], [315, 77, 71, 32], [396, 77, 32, 32]])) throw new Error(`Desktop appointments navigation button mismatch: ${JSON.stringify(toolbarStructure.periodButtons)}`);
    if (JSON.stringify(toolbarStructure.viewButtons) !== JSON.stringify([[660, 77, 66, 32], [730, 77, 71, 32], [805, 77, 51, 32], [860, 77, 85, 32]])) throw new Error(`Desktop appointments view buttons mismatch: ${JSON.stringify(toolbarStructure.viewButtons)}`);
    if (JSON.stringify(toolbarStructure.filterLabels) !== JSON.stringify([[282, 127, 68, 17], [512, 127, 66, 17]])) throw new Error(`Desktop appointments filter labels mismatch: ${JSON.stringify(toolbarStructure.filterLabels)}`);
    if (JSON.stringify(toolbarStructure.actions.map(box => box && [box.x, box.y, box.width, box.height])) !== JSON.stringify([[737, 119, 150, 32], [893, 119, 150, 32], [1166, 119, 112, 33]])) throw new Error(`Desktop appointments filter actions mismatch: ${JSON.stringify(toolbarStructure.actions)}`);
    for (const [name, box, expected] of [
      ["calendarHourFirst", fullShellGeometry.calendarHourFirst, [265, 286, 80, 112]],
      ["calendarSlotFirst", fullShellGeometry.calendarSlotFirst, [345, 286, 93, 112]],
    ]) {
      const actual = box && [box.x, box.y, box.width, box.height];
      if (JSON.stringify(actual) !== JSON.stringify(expected)) throw new Error(`Desktop calendar cell geometry mismatch for ${name}: ${JSON.stringify({ actual, expected })}`);
    }
    if (fullShellGeometry.calendarMetrics.clientWidth !== 728 || fullShellGeometry.calendarMetrics.offsetWidth !== 740 || fullShellGeometry.calendarMetrics.scrollWidth !== 728 || fullShellGeometry.calendarMetrics.scrollHeight !== 1287) throw new Error(`Desktop calendar viewport mismatch: ${JSON.stringify(fullShellGeometry.calendarMetrics)}`);
    if (fullShellGeometry.mainMetrics.scrollHeight !== 764 || fullShellGeometry.mainMetrics.clientWidth !== 1040) throw new Error(`Desktop main viewport has unexpected overflow: ${JSON.stringify(fullShellGeometry.mainMetrics)}`);
    const headerControls = fullShellGeometry.headerControls;
    const exactHeaderBoxes = [[headerControls.back, 8, 19, 80, 32], [headerControls.logo, 92, 30, 10, 10], [headerControls.brand, 106, 25, 64, 19], [headerControls.page, 174, 27, 73, 16], [headerControls.search, 304, 15, 150, 40], [headerControls.assistant, 1254, 19, 32, 32]];
    for (const [box, x, y, width, height] of exactHeaderBoxes) {
      if (!box || box.x !== x || box.y !== y || box.width !== width || box.height !== height) throw new Error(`Desktop header geometry mismatch: ${JSON.stringify({ box, expected: [x, y, width, height] })}`);
    }
    const topActionChildren = fullShellGeometry.headerControls.topActionsChildren;
    const visibleTopActions = topActionChildren.filter(box => box.width > 0 && box.height > 0).sort((left, right) => left.x - right.x);
    if (!headerControls.profile || !headerControls.sync || !headerControls.notifications || !headerControls.settings || !headerControls.theme || !headerControls.quickAdd || visibleTopActions.some((box, index) => index && visibleTopActions[index - 1].x + visibleTopActions[index - 1].width > box.x)) throw new Error(`Desktop header controls overlap or are missing: ${JSON.stringify({ visibleTopActions })}`);
    const topbarDetails = await evaluate(`(() => [...document.querySelector(".topbar")?.children||[]].map(node=>{const r=node.getBoundingClientRect(),s=getComputedStyle(node),children=[...node.children].map(child=>{const box=child.getBoundingClientRect(),style=getComputedStyle(child);return{id:child.id,className:String(child.className),text:(child.innerText||"").trim().replace(/\\s+/g," ").slice(0,48),rect:[Math.round(box.x),Math.round(box.y),Math.round(box.width),Math.round(box.height)],display:style.display,flex:style.flex}});return{tag:node.tagName,id:node.id,className:String(node.className),text:(node.innerText||"").trim().replace(/\\s+/g," ").slice(0,90),rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],background:s.backgroundColor,color:s.color,children}}))()`);
    const headerBackCheck = await evaluate(`(() => {const target=page,button=document.querySelector("#headerBackBtn"),wasEnabled=!!button&&!button.disabled;button?.click();const previous=page;navigate(target);return{wasEnabled,previous,restored:page===target,enabledAgain:!!button&&!button.disabled};})()`);
    if (!headerBackCheck.wasEnabled || !headerBackCheck.previous || !headerBackCheck.restored || !headerBackCheck.enabledAgain) throw new Error(`Desktop-style back navigation mismatch: ${JSON.stringify(headerBackCheck)}`);
    const navigationScrollReset = await evaluate(`(() => {const main=document.querySelector(".main");main.scrollTop=160;navigate("appointments");return main.scrollTop;})()`);
    if (navigationScrollReset !== 0) throw new Error(`Main viewport did not reset after navigation: ${navigationScrollReset}`);
    await evaluate(`(() => { const s=window.__appointmentShellStyles||{},restore=(selector,value)=>{const node=document.querySelector(selector);if(node&&value!==undefined)node.style.cssText=value;};document.documentElement.style.cssText=s.root||"";document.documentElement.style.setProperty("--appointment-layout-offset","178px");restore(".app-shell",s.shell);const shell=document.querySelector(".app-shell"),sidebar=document.querySelector(".sidebar"),topbar=document.querySelector(".topbar"),statusBar=document.querySelector("#shellStatusBar");if(shell)shell.style.cssText+=";display:block;width:1300px;height:850px;min-height:850px;overflow:hidden";if(sidebar)sidebar.style.display="none";if(topbar)topbar.style.display="none";if(statusBar)statusBar.style.display="none";const main=document.querySelector(".main"),content=document.querySelector(".content");if(main)main.style.cssText+=";width:1300px;height:850px;overflow:hidden";if(content)content.style.cssText+=";padding:0;width:1300px;height:850px;overflow:hidden";render();return true;})()`);
    await delay(80);
    await delay(300);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: 850, scale: 1 } });
    const screenshotPath = path.join(outputDir, "appointments-week-current-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    await evaluate(`(() => {db.appointments=window.__appointmentVisualFixture.appointments;db.personnel=window.__appointmentVisualFixture.personnel;ayecAppointmentPersonnelRows=window.__appointmentVisualFixture.personnelRows;apiFetch=window.__appointmentOriginalPersonnelApiFetch;render();return true;})()`);
    await delay(120);
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
      apiFetch = async url => { refreshUrl = url; return { rows: [{ id: 92, customer_id: 71, customer_name: "QA Refreshed", date: "2026-10-15", time: "16:00", description: "Refreshed item", personnel_name: "QA Tech", status: "Bekliyor", plan_items: [{ source_location_id: 7 }] }] }; };
      refreshButton.click();
      await new Promise(resolve => setTimeout(resolve, 80));
      return { fields, customerLookup, stored, date: item.date, time: item.time, write: window.__appointmentWrite, refreshUrl, refreshed: db.appointments.map(row => ({ id: row.id, customer: row.customer, time: row.time, planItemCount: row.plan_items?.length || 0 })) };
    })()`);
    if (interaction.fields.date !== "2026-10-14" || interaction.fields.time !== "14:00" || interaction.date !== "2026-10-14" || interaction.time !== "11:00" || interaction.write?.date !== "2026-10-14") throw new Error(`Appointment interaction check failed: ${JSON.stringify(interaction)}`);
    if (interaction.customerLookup.value !== "QA Customer" || interaction.customerLookup.id !== "71" || interaction.customerLookup.options !== 1) throw new Error(`Appointment customer lookup failed: ${JSON.stringify(interaction.customerLookup)}`);
    if (interaction.refreshUrl !== "/api/desktop/table/appointments?limit=1000" || interaction.refreshed[0]?.id !== "92" || interaction.refreshed[0]?.time !== "16:00" || interaction.refreshed[0]?.planItemCount !== 1) throw new Error(`Appointment refresh check failed: ${JSON.stringify(interaction)}`);
    const reminder = await evaluate(`(async () => {
      document.body.insertAdjacentHTML("beforeend", genericShell(genericModules.reminders));
      let createPayload = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/personnel?limit=500&include_deleted=1") return { rows: [{ id: 8, name: "QA Tech" }] };
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
      const preservedItems = JSON.parse(document.querySelector('#dialogBody [name="maintenance_items_json"]')?.value || "[]");
      const returned = {
        notes: document.querySelector('#dialogBody [name="notes"]')?.value,
        vehicleId: document.querySelector('#dialogBody [name="vehicle_id"]')?.value,
        itemCount: preservedItems.length,
        preservedItem: preservedItems.some(item => item.item_type === "oil_change" && item.performed === true && Number(item.interval_km) === 5000)
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
    process.stdout.write(`${JSON.stringify({ ...state, appointmentStatusCheck, maintenancePdfCheck, interaction, reminder, shortcutState, dashboardAppointment, shortcutActions, maintenanceVehicleLookup, customDeviceType, screenshot: screenshotPath, fullShellScreenshot: fullShellScreenshotPath, fullShellGeometry, topbarDetails, headerBackCheck, navigationScrollReset, dashboardScreenshot: dashboardScreenshotPath, shortcutsScreenshot: shortcutScreenshotPath, browserExceptions: exceptions.length })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
