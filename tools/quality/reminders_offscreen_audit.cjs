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
        writes: [], originalApiFetch: originalApiFetch
      };
      apiFetch = async (url, options = {}) => {
        const text = String(url);
        if (text.includes("/table/personnel")) return { rows: [{ id: 8, name: "QA Tech" }], count: 1 };
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
      const layout = { pageHead: rect("#content .page-head"), subtitle: rect("#content .page-head p"), card: rect("#content .reminders-reference"), tabs: rect("#content .reminder-tabs"), actions: rect("#content .reminder-list-actions"), table: rect("#content .reminder-table") };
      const personnelOptions = Array.from(document.querySelectorAll('#reminderCreateForm [name="personnel"] option'), option => option.textContent.trim());
      const legacyCells = Array.from(document.querySelectorAll('[data-reminder-id="910"] td'), cell => cell.textContent.trim());
      window.__reminderAudit.records.length = 0;
      await loadGenericModule(genericModules.reminders, "");
      const form = document.querySelector("#reminderCreateForm");
      form.elements.title.value = "QA Reminder";
      form.elements.personnel.value = "8";
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
      return { layout, listLayout, personnelOptions, legacyCells, createWrite, createdRowVisible: Boolean(createdRow), activeTab, deleteEnabledWithoutSelection, emptySelectionNotice, deleteEnabled };
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const screenshotPath = path.join(outputDir, "reminders-list-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
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
    if (!result.personnelOptions.includes("QA Tech") || JSON.stringify(result.legacyCells) !== JSON.stringify(expectedLegacyCells) || result.createWrite?.personnel_id !== 8 || result.createWrite?.personnel !== "QA Tech" || !result.createdRowVisible || result.activeTab !== "true" || !result.deleteEnabledWithoutSelection || !result.emptySelectionNotice || !result.deleteEnabled || !result.confirmDialog || result.deleteWrite?.id !== 911 || result.deleteWrite?._action !== "delete" || !result.deletedRowMissing || exceptions.length) {
      throw new Error(`Reminder workflow mismatch: ${JSON.stringify({ result, exceptions })}`);
    }
    process.stdout.write(`${JSON.stringify({ ...result, exceptions, screenshot: screenshotPath })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
