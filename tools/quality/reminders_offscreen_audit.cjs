const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `reminders-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function findPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const page = (await response.json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,850", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await findPage();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
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
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 850, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof loadGenericModule === 'function' && typeof render === 'function'")) break;
      await delay(200);
    }
    const created = await evaluate(`(async () => {
      hideAuth();
      currentAuthUser = { username: "QA Admin", role: "Admin", permissions: JSON.stringify({ mode: "all" }) };
      updateCurrentUser(currentAuthUser);
      applicationStarted = true;
      page = "reminders";
      const originalApiFetch = apiFetch;
      window.__reminderAudit = {
        records: [{ id: 910, tracking_no: "LEGACY-1", message: "Legacy reminder title", due_date: "2026-10-21", is_read: 1, created_at: "2026-10-15 09:00:00", title: null, personnel: null, date: null, description: null, status: null }],
        writes: [], requests: [], originalApiFetch: originalApiFetch
      };
      apiFetch = async (url, options = {}) => {
        const text = String(url);
        window.__reminderAudit.requests.push(text);
        if (text.includes("/table/personnel")) return { rows: [{ id: 8, name: "QA Tech" }, { id: 9, name: "Archived QA Tech", is_deleted: 1 }], count: 2 };
        if (text.includes("/table/reminders") && !options.method) return { rows: window.__reminderAudit.records.slice(), count: window.__reminderAudit.records.length };
        if (text.includes("/table/reminders") && options.method === "POST") {
          const body = JSON.parse(options.body || "{}");
          window.__reminderAudit.writes.push(body);
          if (body._action === "delete") {
            const index = window.__reminderAudit.records.findIndex(row => String(row.id) === String(body.id));
            if (index >= 0) window.__reminderAudit.records.splice(index, 1);
            return { ok: true };
          }
          const created = { id: 911, ...body, created_at: "2026-10-16 10:00:00" };
          window.__reminderAudit.records.push(created);
          return created;
        }
        return originalApiFetch(text, options);
      };
      renderNav();
      render();
      await new Promise(resolve => setTimeout(resolve, 50));
      const rect = selector => { const node = document.querySelector(selector); if (!node) return null; const box = node.getBoundingClientRect(); return { x: box.x, y: box.y, width: box.width, height: box.height }; };
      const layout = { pageHead: rect("#content .page-head"), subtitle: rect("#content .page-head p"), card: rect("#content .reminders-reference"), tabs: rect("#content .reminder-tabs"), actions: rect("#content .reminder-list-actions"), host: rect("#reminderListHost"), wrap: rect("#reminderListHost .table-wrap"), table: rect("#content .reminder-table") };
      const personnelOptions = Array.from(document.querySelectorAll('#reminderCreateForm [name="personnel"] option'), option => option.textContent.trim());
      const legacyCells = Array.from(document.querySelectorAll('[data-reminder-id="910"] td'), cell => cell.textContent.trim());
      await loadGenericModule(genericModules.reminders, "");
      const form = document.querySelector("#reminderCreateForm");
      form.elements.title.value = "QA Reminder";
      form.elements.personnel.value = "9";
      form.elements.date.value = "2026-10-20";
      form.elements.description.value = "QA reminder details";
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await new Promise(resolve => setTimeout(resolve, 80));
      const createWrite = window.__reminderAudit.writes.find(body => body.title === "QA Reminder") || null;
      const createdRow = document.querySelector('[data-reminder-id="911"]');
      const activeTab = document.querySelector('[data-reminder-tab="list"]')?.getAttribute("aria-selected");
      const listLayout = {
        tabs: rect(".reminder-tabs"),
        actions: rect(".reminder-list-actions"),
        host: rect("#reminderListHost"),
        wrap: rect("#reminderListHost .table-wrap"),
        table: rect(".reminder-table"),
        headerHeight: document.querySelector(".reminder-table thead tr")?.getBoundingClientRect().height || 0,
        rowHeight: createdRow?.getBoundingClientRect().height || 0,
        columnWidths: Array.from(document.querySelectorAll(".reminder-table thead th"), node => Math.round(node.getBoundingClientRect().width)),
        deleteColor: getComputedStyle(document.querySelector("[data-reminder-delete]")).backgroundColor
      };
      const deleteButton = document.querySelector("[data-reminder-delete]");
      const deleteEnabledWithoutSelection = Boolean(deleteButton && !deleteButton.disabled);
      deleteButton?.click();
      const emptySelectionNotice = document.querySelector("#toastRoot")?.textContent.includes("Lütfen silinecek bir satır seçin") || false;
      const deleteEnabled = Boolean(deleteButton && !deleteButton.disabled);
      document.querySelector("#toastRoot")?.replaceChildren();
      const keyboardNavigation = (() => {
        createdRow?.focus();
        const rowIds = Array.from(createdRow?.closest("tbody")?.querySelectorAll("[data-reminder-id]") || [], row => row.dataset.reminderId);
        let observed = null;
        document.addEventListener("keydown", event => { if (event.key === "ArrowUp" || event.key === "ArrowDown") observed = { key: event.key, prevented: event.defaultPrevented }; }, { once: true });
        const upEvent = new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true, cancelable: true });
        createdRow?.dispatchEvent(upEvent);
        const upRow = document.activeElement;
        const up = { id: upRow?.dataset.reminderId || "", selected: upRow?.getAttribute("aria-selected") === "true" };
        const downEvent = new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true });
        upRow?.dispatchEvent(downEvent);
        const downRow = document.activeElement;
        const down = { id: downRow?.dataset.reminderId || "", selected: downRow?.getAttribute("aria-selected") === "true" };
        const archivedCell = document.querySelector('[data-reminder-id="911"]')?.children[2];
        const archivedStyle = archivedCell ? getComputedStyle(archivedCell) : null;
        const archivedAssignment = { rowHeight: document.querySelector('[data-reminder-id="911"]')?.getBoundingClientRect().height || 0, title: archivedCell?.title || "", whiteSpace: archivedStyle?.whiteSpace || "", textOverflow: archivedStyle?.textOverflow || "" };
        downRow?.classList.remove("selected");
        downRow?.setAttribute("aria-selected", "false");
        downRow?.blur();
        window.__reminderAudit.records = [{ id: 911, title: "QA Reminder", personnel: "QA Tech", date: "2026-10-20", description: "QA reminder details", status: "Aktif", is_read: 0 }];
        return { up, down, rowIds, eventPrevented: upEvent.defaultPrevented, observed, archivedAssignment };
      })();
      await loadGenericModule(genericModules.reminders, "");
      return { layout, listLayout, personnelOptions, legacyCells, createWrite, requests: window.__reminderAudit.requests.slice(), createdRowVisible: Boolean(document.querySelector('[data-reminder-id="911"]')), activeTab, deleteEnabledWithoutSelection, emptySelectionNotice, deleteEnabled, keyboardNavigation };
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const screenshotPath = path.join(outputDir, "reminders-list-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    await send("Emulation.setDeviceMetricsOverride", { width: 960, height: 760, deviceScaleFactor: 1, mobile: false });
    await evaluate(`(()=>{for(const selector of [".sidebar",".topbar","#shellStatusBar"])document.querySelector(selector)?.setAttribute("style","display:none!important");document.querySelector(".app-shell")?.setAttribute("style","display:block!important;min-height:0!important");document.querySelector(".main")?.setAttribute("style","margin:0!important;padding:0!important;min-height:0!important;width:100%!important");document.querySelector("#content")?.setAttribute("style","margin:0!important;padding:16px!important;width:100%!important;max-width:none!important;min-height:0!important");document.body.style.minWidth="0";document.body.style.overflow="hidden"})()`);
    await evaluate(`document.querySelector(".reminders-reference")?.style.setProperty("min-height", "668px", "important")`);
    await delay(100);
    await evaluate(`document.querySelector('[data-reminder-tab="add"]')?.click()`);
    await new Promise(resolve => setTimeout(resolve, 30));
    await evaluate(`(()=>{const form=document.querySelector("#reminderCreateForm");form?.reset();if(form?.elements.date){const now=new Date();form.elements.date.value=[now.getFullYear(),String(now.getMonth()+1).padStart(2,"0"),String(now.getDate()).padStart(2,"0")].join("-")}})()`);
    const addMetrics = await evaluate(`(()=>{const rect=selector=>{const node=document.querySelector(selector);if(!node)return null;const box=node.getBoundingClientRect();return{x:box.x,y:box.y,width:box.width,height:box.height}};return{heading:rect(".reminders-page-head h2"),tabs:rect(".reminder-tabs"),form:rect("#reminderCreateForm"),fieldset:rect("#reminderCreateForm fieldset"),title:rect('#reminderCreateForm [name="title"]'),personnel:rect('#reminderCreateForm [name="personnel"]'),date:rect('#reminderCreateForm [name="date"]'),description:rect('#reminderCreateForm [name="description"]'),submit:rect('#reminderCreateForm [type="submit"]')}})()`);
    const near = (actual, expected, tolerance = 1) => Math.abs(actual - expected) <= tolerance;
    if (!near(addMetrics.tabs.x, 16) || !near(addMetrics.tabs.y, 62) || !near(addMetrics.tabs.width, 928) || !near(addMetrics.tabs.height, 44)
      || !near(addMetrics.fieldset.x, 33) || !near(addMetrics.fieldset.y, 138) || !near(addMetrics.fieldset.width, 894) || !near(addMetrics.fieldset.height, 396)
      || !near(addMetrics.title.x, 52) || !near(addMetrics.title.y, 220) || !near(addMetrics.title.width, 525, 2)
      || !near(addMetrics.description.x, 52) || !near(addMetrics.description.y, 324) || !near(addMetrics.description.width, 856) || !near(addMetrics.description.height, 191)
      || !near(addMetrics.submit.x, 707) || !near(addMetrics.submit.y, 553) || !near(addMetrics.submit.width, 220) || !near(addMetrics.submit.height, 48)) {
      throw new Error("Reminder add-form geometry diverged from the desktop capture: " + JSON.stringify(addMetrics));
    }
    const addScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 960, height: 760, scale: 1 } });
    fs.writeFileSync(path.join(outputDir, "reminders-add-isolated-headless.png"), Buffer.from(addScreenshot.data, "base64"));
    await evaluate(`document.querySelector('[data-reminder-tab="list"]')?.click()`);
    await new Promise(resolve => setTimeout(resolve, 30));
    const isolatedMetrics = await evaluate(`(()=>{const rect=selector=>{const node=document.querySelector(selector);if(!node)return null;const box=node.getBoundingClientRect();return{x:box.x,y:box.y,width:box.width,height:box.height}};const bg=selector=>{const node=document.querySelector(selector);return node?getComputedStyle(node).backgroundColor:null};return{heading:rect(".reminders-page-head h2"),headingStyle:(()=>{const node=document.querySelector(".reminders-page-head h2");const style=getComputedStyle(node);return{fontFamily:style.fontFamily,fontSize:style.fontSize,fontWeight:style.fontWeight}})(),tabs:rect(".reminder-tabs"),actions:rect(".reminder-list-actions"),wrap:rect("#reminderListHost .table-wrap"),table:rect(".reminder-table"),row:rect(".reminder-table tbody tr"),archivedAssignment:(()=>{const row=document.querySelector('[data-reminder-id="911"]'),cell=row?.children[2],style=cell?getComputedStyle(cell):null;return{rowHeight:row?.getBoundingClientRect().height||0,title:cell?.title||"",whiteSpace:style?.whiteSpace||"",overflow:style?.overflow||"",textOverflow:style?.textOverflow||""}})(),deleteButton:(()=>{const node=document.querySelector("[data-reminder-delete]");if(!node)return null;const style=getComputedStyle(node);return{className:node.className,focused:document.activeElement===node,borderColor:style.borderColor,outline:style.outline,boxShadow:style.boxShadow}})(),backgrounds:{body:bg("body"),content:bg("#content"),pageHead:bg(".reminders-page-head"),card:bg(".reminders-reference"),tableHead:bg(".reminder-table th"),tableCell:bg(".reminder-table td")}}})()`);
    await evaluate("document.activeElement?.blur()");
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 950, y: 750 });
    const isolatedScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 960, height: 760, scale: 1 } });
    fs.writeFileSync(path.join(outputDir, "reminders-list-isolated-headless.png"), Buffer.from(isolatedScreenshot.data, "base64"));
    const deleted = await evaluate(`(async () => {
      document.querySelector('[data-reminder-id="911"]')?.click();
      document.querySelector("[data-reminder-delete]")?.click();
      const confirmDialog = Boolean(document.querySelector("#appDialog")?.open)
        && document.querySelector("#dialogTitle")?.textContent.includes("Hatırlatıcıyı Sil")
        && document.querySelector("#dialogCancel")?.textContent === "Hayır";
      document.querySelector("#dialogSubmit")?.click();
      await new Promise(resolve => setTimeout(resolve, 100));
      const deleteWrite = window.__reminderAudit.writes.find(body => body._action === "delete") || null;
      const deletedRowMissing = !document.querySelector('[data-reminder-id="911"]');
      apiFetch = window.__reminderAudit.originalApiFetch;
      delete window.__reminderAudit;
      return { confirmDialog, deleteWrite, deletedRowMissing };
    })()`);
    const result = { ...created, ...deleted, screenshot: screenshotPath };
    const expectedLegacyCells = ["910", "Legacy reminder title", "Genel (Herkes)", "2026-10-21", "Legacy reminder title", "Okundu"];
    if (!result.personnelOptions.includes("QA Tech") || !result.personnelOptions.includes("Archived QA Tech") || !result.requests.some(url => url.includes("/table/personnel?limit=500&include_deleted=1")) || JSON.stringify(result.legacyCells) !== JSON.stringify(expectedLegacyCells) || result.createWrite?.personnel_id !== 9 || result.createWrite?.personnel !== "Archived QA Tech" || !result.createdRowVisible || result.keyboardNavigation.up.id !== "910" || !result.keyboardNavigation.up.selected || result.keyboardNavigation.down.id !== "911" || !result.keyboardNavigation.down.selected || result.activeTab !== "true" || !result.deleteEnabledWithoutSelection || !result.emptySelectionNotice || !result.deleteEnabled || !result.confirmDialog || Math.abs(result.keyboardNavigation.archivedAssignment.rowHeight - 30) > 1 || result.keyboardNavigation.archivedAssignment.title !== "Archived QA Tech" || result.keyboardNavigation.archivedAssignment.whiteSpace !== "nowrap" || result.keyboardNavigation.archivedAssignment.textOverflow !== "ellipsis" || result.deleteWrite?.id !== 911 || result.deleteWrite?._action !== "delete" || !result.deletedRowMissing || exceptions.length) {
      throw new Error(`Reminder workflow mismatch: ${JSON.stringify({ result, exceptions })}`);
    }
    process.stdout.write(`${JSON.stringify({ ...result, addMetrics, isolatedMetrics, exceptions, screenshot: screenshotPath })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
