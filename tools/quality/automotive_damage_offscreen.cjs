const { spawn, execFileSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9253);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `automotive-damage-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let i = 0; i < 100; i += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge CDP target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let i = 0; i < 80; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof apiFetch === 'function' && document.querySelector('#appDialog')")) break;
      await delay(200);
    }
    const maintenanceSetupAudit = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active"); currentSector = "otomotiv";
      window.__maintenanceAudit = {original: {apiFetch, hydrateDesktop, loadVehicleMaintenance, offerMaintenanceWhatsApp, toast}, savedPayload: null};
      apiFetch = async (url, options = {}) => {
        if (String(url).includes("customer_vehicles")) return {rows: []};
        if (String(url).includes("vehicle-maintenance/save")) { window.__maintenanceAudit.savedPayload = JSON.parse(options.body); return {id: 123, important_items: []}; }
        if (String(url).includes("vehicle-maintenance/detail/")) return {card: {id:123,customer_id:1,vehicle_plate:"10 AUDIT 01",vehicle_brand:"Ford",vehicle_model:"Focus",odometer:12000,service_date:"2026-01-01",next_maintenance_date:"2026-04-01",inspection_due_date:"2027-10-16",appointment_date:"2026-04-01"},items:[]};
        throw new Error("Unexpected maintenance audit request: " + url);
      };
      hydrateDesktop = async () => {}; loadVehicleMaintenance = async () => {}; offerMaintenanceWhatsApp = () => {}; toast = () => {};
      await maintenanceDialog({});
      const form = document.querySelector("#dialogForm"), customer = form?.querySelector('[name="customer_id"]'), plate = form?.querySelector('[name="vehicle_plate"]');
      if (!form || !customer || !plate) return {opened: false};
      const brand = form.querySelector('[name="vehicle_brand"]');
      brand.value = "Ford"; brand.dispatchEvent(new Event("input", {bubbles: true}));
      const formControls = {brandOptions: document.querySelectorAll("#maintenanceBrandOptions option").length, modelOptions: document.querySelectorAll("#maintenanceModelOptions option").length, yearOptions: form.querySelector('[name="vehicle_year"]').options.length, vehicleTypes: form.querySelector('[name="vehicle_type"]').options.length, engineTypes: form.querySelector('[name="engine_type"]').options.length, fuelTypes: form.querySelector('[name="fuel_type"]').options.length, defaults: [form.querySelector('[name="vehicle_type"]').value, form.querySelector('[name="engine_type"]').value, form.querySelector('[name="fuel_type"]').value]};
      const serviceDate = form.querySelector('[name="service_date"]'), nextDate = form.querySelector('[name="next_maintenance_date"]'), appointmentDate = form.querySelector('[name="appointment_date"]'), inspectionDate = form.querySelector('[name="inspection_due_date"]');
      const mainActionsDisabled=form.querySelector("[data-maintenance-gallery]")?.disabled===true&&form.querySelector("[data-maintenance-history]")?.disabled===true;
      const initialDatesMatch = nextDate.value === maintenanceDateAfter(serviceDate.value, 90) && appointmentDate.value === nextDate.value && inspectionDate.value === maintenanceDateAfter(serviceDate.value, 365);
      serviceDate.value = "2026-01-01"; serviceDate.dispatchEvent(new Event("change", {bubbles: true}));
      const dateSyncMatches = nextDate.value === "2026-04-01" && appointmentDate.value === "2026-04-01";
      if (!Array.from(customer.options).some(option => option.value)) customer.add(new Option("Audit Customer", "1"));
      customer.value = Array.from(customer.options).find(option => option.value)?.value || ""; customer.dispatchEvent(new Event("change", {bubbles: true}));
      plate.value = "10 AUDIT 01";
      form.requestSubmit(); await new Promise(resolve => setTimeout(resolve, 100));
      const emptySelectionBlocked = document.querySelector("#appDialog")?.open === true && window.__maintenanceAudit.savedPayload === null;
      const captureServiceDate=form.querySelector('[name="service_date"]'),captureOdometer=form.querySelector('[name="odometer"]');
      window.__maintenanceAudit.originalOdometer=captureOdometer?.value||"";
      captureServiceDate.value="2026-04-01";captureServiceDate.dispatchEvent(new Event("change",{bubbles:true}));
      captureOdometer.value="100000";captureOdometer.dispatchEvent(new Event("input",{bubbles:true}));
      document.querySelector("[data-maintenance-items-open]")?.click();
      const itemDialog=document.querySelector(".maintenance-items-dialog"),itemRows=itemDialog?.querySelectorAll("[data-maintenance-item]")||[];
      const itemViewport=itemDialog?.querySelector(".maintenance-items"),hasVerticalScroll=itemViewport?.scrollHeight>itemViewport?.clientHeight+1;
      const captureFixtureMatches=captureServiceDate.value==="2026-04-01"&&captureOdometer.value==="100000"&&itemRows[0]?.querySelector(".maintenance-due-date").value==="2026-06-30"&&itemRows[0]?.querySelector(".maintenance-due-km").value==="110000";
      const setup={opened:true,formControls,initialDatesMatch,dateSyncMatches,emptySelectionBlocked,mainActionsDisabled};window.__maintenanceAudit.setup=setup;
      const bounds=itemDialog?.getBoundingClientRect();
      return {...setup,itemCount:itemRows.length,childDialogOpen:itemDialog?.open===true,hasVerticalScroll,captureFixtureMatches,firstRowHeight:itemRows[0]?.getBoundingClientRect().height||0,firstInputHeight:itemRows[0]?.querySelector(".maintenance-days")?.getBoundingClientRect().height||0,viewportHeight:itemViewport?.clientHeight||0,bounds:bounds?[bounds.width,bounds.height]:[],itemTypes:Array.from(itemRows).map(element=>element.dataset.maintenanceItem),headings:Array.from(itemDialog?.querySelectorAll(".maintenance-item-head span")||[]).map(element=>element.textContent)};
    })()`);
    if (!maintenanceSetupAudit.opened || !maintenanceSetupAudit.emptySelectionBlocked || !maintenanceSetupAudit.mainActionsDisabled || !maintenanceSetupAudit.childDialogOpen || maintenanceSetupAudit.itemCount !== 10 || !maintenanceSetupAudit.hasVerticalScroll || !maintenanceSetupAudit.captureFixtureMatches || Math.abs(maintenanceSetupAudit.firstRowHeight-58)>3 || Math.abs(maintenanceSetupAudit.firstInputHeight-56)>1 || maintenanceSetupAudit.bounds.some((value,index)=>Math.abs(value-[1180,760][index])>1) || maintenanceSetupAudit.itemTypes.join("|") !== "oil_change|oil_filter|air_filter|cabin_filter|glass_water|antifreeze|brake_fluid|spark_plugs|timing_belt|timing_chain" || maintenanceSetupAudit.headings.join("|") !== "Kalem|Yap\u0131ld\u0131|Periyot (G\u00fcn)|Periyot (KM)|Sonraki Tarih|Sonraki KM") throw new Error(JSON.stringify({maintenanceSetupAudit,exceptions}));
    const maintenanceScreenshot = await send("Page.captureScreenshot", {format: "png", captureBeyondViewport: true});
    const maintenanceScreenshotPath = path.join(outDir, "vehicle-maintenance-items-dialog-headless.png");
    fs.writeFileSync(maintenanceScreenshotPath, Buffer.from(maintenanceScreenshot.data, "base64"));
    const maintenanceCaptureRestored = await evaluate(`(async()=>{const form=document.querySelector("#dialogForm"),dialog=document.querySelector(".maintenance-items-dialog"),serviceDate=form?.querySelector('[name="service_date"]'),odometer=form?.querySelector('[name="odometer"]');const closed=new Promise(resolve=>dialog?.addEventListener("close",resolve,{once:true}));dialog?.querySelector("[data-maintenance-items-cancel]")?.click();await closed;serviceDate.value="2026-01-01";serviceDate.dispatchEvent(new Event("change",{bubbles:true}));odometer.value=window.__maintenanceAudit.originalOdometer;odometer.dispatchEvent(new Event("input",{bubbles:true}));document.querySelector("[data-maintenance-items-open]")?.click();return dialog?.isConnected===false&&serviceDate.value==="2026-01-01"&&document.querySelector(".maintenance-items-dialog")?.open===true})()`);
    if (!maintenanceCaptureRestored) throw new Error("The matched maintenance screenshot fixture was not restored before workflow checks.");
    const maintenanceSaveAudit = await evaluate(`(async () => {
      const itemDialog=document.querySelector(".maintenance-items-dialog"),itemRows=Array.from(itemDialog?.querySelectorAll("[data-maintenance-item]")||[]);
      const firstDays=itemRows[0]?.querySelector(".maintenance-days"),firstKm=itemRows[0]?.querySelector(".maintenance-km");firstDays.value="120";firstDays.dispatchEvent(new Event("input",{bubbles:true}));firstKm.value="12000";firstKm.dispatchEvent(new Event("input",{bubbles:true}));
      const dueTargetsSynced=itemRows[0]?.querySelector(".maintenance-due-date").value==="2026-05-01"&&Number(itemRows[0]?.querySelector(".maintenance-due-km").value)===Number(window.__maintenanceAudit.originalOdometer||0)+12000;
      itemRows.forEach((element,index)=>{element.querySelector(".maintenance-performed").checked=index===0});
      itemDialog?.querySelector("[data-maintenance-items-save]")?.click(); await new Promise(resolve=>setTimeout(resolve,60));
      const form=document.querySelector("#dialogForm"),itemsInput=form?.querySelector('[name="maintenance_items_json"]'),summary=document.querySelector("[data-maintenance-items-summary]");
      const savedSelection=JSON.parse(itemsInput?.value||"[]");
      document.querySelector("[data-maintenance-items-open]")?.click();
      const reopened=document.querySelector(".maintenance-items-dialog"),first=reopened?.querySelector(".maintenance-performed");if(first)first.checked=false;
      reopened?.querySelector("[data-maintenance-items-cancel]")?.click();
      const cancelPreservedSelection=JSON.parse(itemsInput?.value||"[]").length===1;
      form?.requestSubmit(); await new Promise(resolve=>setTimeout(resolve,120));
      const savedPayload=window.__maintenanceAudit.savedPayload;
      const result = {...window.__maintenanceAudit.setup, itemCount:itemRows.length, dueTargetsSynced, dueDateActual:itemRows[0]?.querySelector(".maintenance-due-date").value||"", dueKmActual:itemRows[0]?.querySelector(".maintenance-due-km").value||"", odometerBaseline:window.__maintenanceAudit.originalOdometer||"", savedSelectionCount:savedSelection.length, summaryShowsOne:summary?.textContent.includes("1 kalem")===true, cancelPreservedSelection, savedItems:savedPayload?.items?.length||0, savedPerformed:savedPayload?.items?.[0]?.performed===true, reminderDate:savedPayload?.reminder_date||"", noticeDate:savedPayload?.inspection_notice_date||"", expectedReminderDate:"2026-03-31", expectedNoticeDate:maintenanceDateAfter(form?.querySelector('[name="inspection_due_date"]')?.value||"",-30), closedAfterSave:document.querySelector("#appDialog")?.open===false};
      await maintenanceDialog({id:123});
      result.savedCardActionsEnabled=document.querySelector('#dialogForm [data-maintenance-gallery]')?.disabled===false&&document.querySelector('#dialogForm [data-maintenance-history]')?.disabled===false;
      const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
      Object.assign(window,window.__maintenanceAudit.original);delete window.__maintenanceAudit;
      return result;
    })()`);
    maintenanceSaveAudit.initialDatesMatch = maintenanceSetupAudit.initialDatesMatch;
    maintenanceSaveAudit.dateSyncMatches = maintenanceSetupAudit.dateSyncMatches;
    maintenanceSaveAudit.emptySelectionBlocked = maintenanceSetupAudit.emptySelectionBlocked;
    const maintenanceControls = maintenanceSetupAudit.formControls;
    if (!maintenanceSaveAudit.initialDatesMatch || !maintenanceSaveAudit.dateSyncMatches || !maintenanceSaveAudit.emptySelectionBlocked || maintenanceControls.brandOptions !== 8 || maintenanceControls.modelOptions !== 5 || maintenanceControls.yearOptions !== 39 || maintenanceControls.vehicleTypes !== 7 || maintenanceControls.engineTypes !== 7 || maintenanceControls.fuelTypes !== 6 || maintenanceControls.defaults.join("|") !== "Binek|Benzinli|Benzin" || !maintenanceSaveAudit.dueTargetsSynced || maintenanceSaveAudit.savedSelectionCount !== 1 || !maintenanceSaveAudit.summaryShowsOne || !maintenanceSaveAudit.cancelPreservedSelection || maintenanceSaveAudit.savedItems !== 1 || !maintenanceSaveAudit.savedPerformed || maintenanceSaveAudit.reminderDate !== maintenanceSaveAudit.expectedReminderDate || maintenanceSaveAudit.noticeDate !== maintenanceSaveAudit.expectedNoticeDate || !maintenanceSaveAudit.closedAfterSave || !maintenanceSaveAudit.savedCardActionsEnabled) throw new Error(JSON.stringify({maintenanceSaveAudit}));
    const opened = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      currentSector = "otomotiv"; navigate("services"); await new Promise(resolve => setTimeout(resolve, 100));
      openManifestDialog({key:"automotive_damage_dialog"}); await new Promise(resolve => setTimeout(resolve, 220));
      const service = document.querySelector("#appDialog");
      const opener = service?.querySelector("[data-automotive-damage-open]");
      if (!service?.open || !opener) return {serviceOpened: service?.open === true, openerPresent: !!opener};
      await new Promise(resolve => setTimeout(resolve, 120));
      const dialog = document.querySelector(".automotive-damage-dialog");
      const bounds = dialog?.getBoundingClientRect();
      const fields = {zones: dialog?.querySelectorAll("[data-damage-status]").length || 0, notes: dialog?.querySelectorAll("[data-damage-note]").length || 0, previews: dialog?.querySelectorAll("[data-damage-preview]").length || 0};
      const title = dialog?.querySelector("h2")?.textContent || "";
      const status = dialog?.querySelector('[data-damage-status][data-side="On"]');
      const note = dialog?.querySelector('[data-damage-note][data-side="On"]');
      status.value = "Cizik"; status.dispatchEvent(new Event("change", {bubbles: true}));
      note.value = "Fixture scratch"; note.dispatchEvent(new Event("input", {bubbles: true}));
      const preview = dialog?.querySelector('[data-damage-preview][data-side="On"]');
      const livePreview = {text: preview?.textContent || "", status: preview?.dataset.status || "", noteMarked: preview?.classList.contains("has-note") === true};
      return {serviceOpened: true, openerPresent: true, title, fields, bounds: bounds ? [bounds.width, bounds.height] : [], livePreview};
    })()`);
    if (!opened.serviceOpened || !opened.openerPresent || opened.title !== "Hasar Tespit Formu" || opened.fields.zones !== 16 || opened.fields.notes !== 16 || opened.fields.previews !== 16 || opened.bounds.some((value,index) => Math.abs(value-[1040,760][index]) > 1) || !opened.livePreview.text.includes("Cizik") || opened.livePreview.status !== "Cizik" || !opened.livePreview.noteMarked || exceptions.length) throw new Error(JSON.stringify({opened, exceptions}));
    const screenshot = await send("Page.captureScreenshot", {format: "png", captureBeyondViewport: true});
    const screenshotPath = path.join(outDir, "automotive-damage-dialog-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const interaction = await evaluate(`(async () => {
      const service = document.querySelector("#appDialog"), opener = service?.querySelector("[data-automotive-damage-open]");
      const dialog = document.querySelector(".automotive-damage-dialog");
      dialog.querySelector("[data-damage-save]")?.click(); await new Promise(resolve => setTimeout(resolve, 60));
      const saved = {closed: !document.querySelector(".automotive-damage-dialog"), parentOpen: service.open, label: opener.textContent};
      opener.click(); await new Promise(resolve => setTimeout(resolve, 40));
      const reopened = document.querySelector(".automotive-damage-dialog");
      const retained = reopened?.querySelector('[data-damage-status][data-side="On"]')?.value === "Cizik";
      reopened?.querySelector('[data-damage-status][data-side="On"]')?.dispatchEvent(new Event("change", {bubbles: true}));
      const other = reopened?.querySelector('[data-damage-status][data-side="On"]:not([value="Cizik"])');
      if (other) { other.value = "Gocuk"; other.dispatchEvent(new Event("change", {bubbles: true})); }
      reopened?.querySelector("[data-damage-cancel]")?.click(); await new Promise(resolve => setTimeout(resolve, 50));
      service?.close("cancel"); await new Promise(resolve => setTimeout(resolve, 60)); currentSector = "otomotiv";
      openManifestDialog({key:"automotive_checklist_dialog"}); await new Promise(resolve => setTimeout(resolve, 220));
      const checklist = document.querySelector(".automotive-checklist-dialog"), checklistBounds = checklist?.getBoundingClientRect();
      const checklistStatus = checklist?.querySelector("[data-checklist-status]"), checklistNote = checklist?.querySelector("[data-checklist-note]");
      if (checklistStatus) { checklistStatus.value = "Degismeli"; checklistStatus.dispatchEvent(new Event("change", {bubbles: true})); }
      if (checklistNote) { checklistNote.value = "Fixture inspection"; checklistNote.dispatchEvent(new Event("input", {bubbles: true})); }
      const checklistResult = {open: checklist?.open === true, title: checklist?.querySelector("h2")?.textContent || "", statusCount: checklist?.querySelectorAll("[data-checklist-status]").length || 0, noteCount: checklist?.querySelectorAll("[data-checklist-note]").length || 0, intro: !!checklist?.querySelector(".automotive-checklist-intro"), bounds: checklistBounds ? [checklistBounds.width, checklistBounds.height] : [], firstStatus: checklistStatus?.value || ""};
      return {saved, retained, cancelKeptLabel: opener.textContent === saved.label, checklistResult};
    })()`);
    const checklistScreenshot = await send("Page.captureScreenshot", {format: "png", captureBeyondViewport: true});
    const checklistScreenshotPath = path.join(outDir, "automotive-checklist-dialog-headless.png");
    fs.writeFileSync(checklistScreenshotPath, Buffer.from(checklistScreenshot.data, "base64"));
    const checklistInteraction = await evaluate(`(async () => {
      const service = document.querySelector("#appDialog"), opener = service?.querySelector("[data-automotive-checklist-open]");
      const dialog = document.querySelector(".automotive-checklist-dialog");
      const expected = dialog?.querySelector("[data-checklist-status]")?.value;
      dialog?.querySelector("[data-checklist-save]")?.click(); await new Promise(resolve => setTimeout(resolve, 50));
      const savedLabel = opener?.textContent || "";
      opener?.click(); await new Promise(resolve => setTimeout(resolve, 40));
      const reopened = document.querySelector(".automotive-checklist-dialog");
      const retained = reopened?.querySelector("[data-checklist-status]")?.value === expected;
      reopened?.querySelector("[data-checklist-cancel]")?.click(); await new Promise(resolve => setTimeout(resolve, 50));
      return {closed: !document.querySelector(".automotive-checklist-dialog"), parentOpen: service?.open === true, savedLabel, retained, cancelKeptLabel: opener?.textContent === savedLabel};
    })()`);
    const result = {...opened, ...interaction, maintenanceSaveAudit, maintenanceSetupAudit, checklistInteraction};
    if (!result.saved.closed || !result.saved.parentOpen || !result.saved.label.includes("(1)") || !result.retained || !result.cancelKeptLabel || !result.checklistResult.open || result.checklistResult.title !== "Otomotiv Kontrol Formu" || result.checklistResult.statusCount < 1 || result.checklistResult.noteCount !== result.checklistResult.statusCount || !result.checklistResult.intro || result.checklistResult.bounds.some((value,index) => Math.abs(value-[1120,760][index]) > 1) || result.checklistResult.firstStatus !== "Degismeli" || !result.checklistInteraction.closed || !result.checklistInteraction.parentOpen || !result.checklistInteraction.savedLabel.includes("Kontrol Formu (") || !result.checklistInteraction.retained || !result.checklistInteraction.cancelKeptLabel || exceptions.length) throw new Error(JSON.stringify({result, exceptions}));
    process.stdout.write(`${JSON.stringify({result, exceptions, screenshots: [screenshotPath, checklistScreenshotPath, maintenanceScreenshotPath], headless: true})}\n`);
  } finally {
    try { socket?.close(); } catch (_) {}
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    await delay(300);
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
