const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `appointment-context-headless-profile-${process.pid}`);
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
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1300,850", baseUrl], { stdio: "ignore", windowsHide: true });
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
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof showContext === 'function' && typeof appointmentDialog === 'function' && typeof setAppointmentStatus === 'function'")) break;
      await delay(200);
    }
    const menuAudit = await evaluate(`(() => {
      const original = { appointments: db.appointments, page, write: desktopWrite, render };
      window.__appointmentContextAudit = { original, writes: [] };
      hideAuth();
      currentAuthUser = { username: "QA Admin", role: "Admin", permissions: JSON.stringify({ mode: "all" }) };
      updateCurrentUser(currentAuthUser);
      applicationStarted = true;
      db.settings.contextMenu = true;
      page = "appointments";
      db.appointments = [{ id: 731, customerId: 71, customer: "QA Customer", title: "QA Appointment", description: "QA Appointment", date: "2026-10-16", time: "14:00", status: "Bekliyor", technician: "QA Tech" }];
      desktopWrite = async (table, payload) => { window.__appointmentContextAudit.writes.push({ table, ...payload }); };
      renderNav();
      render();
      const target = document.createElement("button");
      document.body.append(target);
      const openMenu = () => showContext({ preventDefault() {}, clientX: 180, clientY: 160, currentTarget: target }, "appointment", 731);
      openMenu();
      const menu = document.querySelector("#contextMenu");
      const actions = Array.from(menu.querySelectorAll("[data-context-action]"), button => button.dataset.contextAction);
      const separators = menu.querySelectorAll("hr.context-menu-separator").length;
      const plainLabels = Array.from(menu.querySelectorAll(":scope > button"), button => button.textContent.trim());
      const statusTrigger = Array.from(menu.querySelectorAll(":scope > button"), button => button.textContent.includes("Durum Değiştir") ? button : null).find(Boolean);
      statusTrigger?.click();
      const statusLabels = Array.from(menu.querySelectorAll(".appointment-status-submenu button"), button => button.textContent.trim());
      const submenuDisplay = menu.querySelector(".appointment-status-submenu")?.style.display || "";
      const screenshotReady = menu.classList.contains("open") && submenuDisplay === "block" && statusLabels.length === 6;
      return { actions, separators, plainLabels, statusLabels, screenshotReady, menuOpen: menu.classList.contains("open"), submenuDisplay };
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const screenshotPath = path.join(outputDir, "appointment-context-menu-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const interaction = await evaluate(`(async () => {
      const menu = document.querySelector("#contextMenu");
      Array.from(menu.querySelectorAll(":scope > button")).find(button => button.textContent.includes("Durum Değiştir"))?.click();
      Array.from(menu.querySelectorAll('.appointment-status-submenu [data-context-action="appointment-status"]')).find(button => button.textContent.trim() === "Gidildi")?.click();
      await new Promise(resolve => setTimeout(resolve, 0));
      const statusWrite = window.__appointmentContextAudit.writes.find(item => item.status === "Gidildi") || null;
      const persistedStatus = db.appointments[0].status;
      const target = document.querySelector("body > button");
      showContext({ preventDefault() {}, clientX: 180, clientY: 160, currentTarget: target }, "appointment", 731);
      document.querySelector('#contextMenu [data-context-action="edit-appointment"]')?.click();
      const editDialog = Boolean(document.querySelector("#appDialog")?.open) && document.querySelector("#dialogBody [name=notes]")?.value === "QA Appointment";
      document.querySelector("#dialogCancel")?.click();
      document.querySelector("#contextMenu")?.classList.remove("open");
      db.appointments = [{ id: 732, status: "Bekliyor" }];
      const completionSaved = await contextAction("appointment", 732, "complete");
      const completionWrite = window.__appointmentContextAudit.writes.find(item => item.id === 732) || null;
      const completionState = { status: db.appointments[0].status, completedAt: db.appointments[0].completed_at };
      db.appointments = [{ id: 733, status: "Bekliyor" }];
      desktopWrite = async () => { throw new Error("QA write failure"); };
      await contextAction("appointment", 733, "complete");
      const failedWriteKeepsPending = db.appointments[0].status === "Bekliyor" && !db.appointments[0].completed_at;
      target?.remove();
      const original = window.__appointmentContextAudit.original;
      db.appointments = original.appointments; page = original.page; desktopWrite = original.write; render = original.render; render();
      delete window.__appointmentContextAudit;
      return { statusWrite, persistedStatus, editDialog, completionSaved, completionWrite, completionState, failedWriteKeepsPending };
    })()`);
    const expectedActions = ["edit-appointment", "montage-prep", "appointment-status", "appointment-status", "appointment-status", "appointment-status", "appointment-status", "appointment-status", "appointment-delete"];
    const expectedStatuses = ["Bekliyor", "İşlemde", "Tamamlandı", "İptal", "Gidildi", "Gidilmedi"];
    if (JSON.stringify(menuAudit.actions) !== JSON.stringify(expectedActions) || menuAudit.separators !== 1 || JSON.stringify(menuAudit.statusLabels) !== JSON.stringify(expectedStatuses) || !menuAudit.screenshotReady || interaction.persistedStatus !== "Gidildi" || interaction.statusWrite?.table !== "appointments" || !interaction.editDialog || !interaction.completionSaved || interaction.completionWrite?.status !== "Tamamlandı" || !interaction.completionWrite?.completed_at || interaction.completionState.status !== "Tamamlandı" || !interaction.completionState.completedAt || !interaction.failedWriteKeepsPending || exceptions.length) {
      throw new Error(`Appointment context menu parity failed: ${JSON.stringify({ menuAudit, interaction, exceptions })}`);
    }
    process.stdout.write(`${JSON.stringify({ ...menuAudit, ...interaction, exceptions, screenshot: screenshotPath })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
