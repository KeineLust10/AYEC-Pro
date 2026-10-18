const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 34000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-check-note-audit-"));

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const origin = new URL(baseUrl).origin;
      const page = targets.find(target => target.type === "page" && target.url?.startsWith(origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
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
      if (!message.id) {
        if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown browser exception");
        return;
      }
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
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && document.querySelector('#appDialog') && performance.getEntriesByType('resource').some(item => item.name.includes('check-notes-parity.js'))");
      if (ready) break;
      await delay(100);
    }
    if (!ready) {
      const diagnostics = await evaluate("({ state: document.readyState, showContext: typeof showContext === 'function' ? String(showContext).slice(0, 180) : typeof showContext, resources: performance.getEntriesByType('resource').map(item => item.name).filter(name => name.includes('check-notes-parity')), exceptions: document.querySelector('#appDialog') ? 'dialog-ready' : 'dialog-missing' })");
      throw new Error(`The check-note context menu did not initialize: ${JSON.stringify(diagnostics)}`);
    }
    const routeState = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page = "checks";
      document.body.dataset.page = "checks";
      const markup = genericShell(genericModules.checks);
      document.querySelector("#content").innerHTML = markup;
      apiFetch = async () => ({ rows: [{ id: 502, type: "\u00c7ek", direction: "Giri\u015f (Al\u0131nan)", issuer: "Route Issuer", bank_name: "Route Bank", check_no: "ROUTE-502", amount: 850, due_date: "2026-11-03", status: "Portf\u00f6yde" }], columns: ["id", "type", "direction", "issuer", "bank_name", "check_no", "amount", "due_date", "status"] });
      await loadGenericModule(genericModules.checks, "");
      document.querySelector("#checkStatusFilter").value = "Tahsil Edildi";
      document.querySelector("#checkBankFilter").value = "Route Bank";
      document.querySelector("#checkDateStart").value = "2026-10-10";
      document.querySelector("#checkDateEnd").value = "2026-11-10";
      window.checksReferenceTab = "checks";
      window.checksReferencePage = 2;
      document.querySelector("[data-check-clear]").click();
      await new Promise(resolve => setTimeout(resolve, 20));
      const first = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
      const nextYear = new Date(new Date().getFullYear() + 1, new Date().getMonth(), 1);
      const dateValue = value => String(value.getFullYear()) + "-" + String(value.getMonth() + 1).padStart(2, "0") + "-" + String(value.getDate()).padStart(2, "0");
      return { hasLoaderHost: !!document.querySelector("#genericHost"), hasStatusFilter: !!document.querySelector("#checkStatusFilter"), rowCount: document.querySelectorAll("#genericHost tbody tr").length, rowCode: document.querySelector("#genericHost tbody tr")?.textContent.includes("ROUTE-502"), clearedToDesktopDefaults: document.querySelector("#checkStatusFilter").value === "" && document.querySelector("#checkBankFilter").value === "" && document.querySelector("#checkDateStart").value === dateValue(first) && document.querySelector("#checkDateEnd").value === dateValue(nextYear) && window.checksReferenceTab === "all" && window.checksReferencePage === 0 };
    })()`);
    if (!routeState.hasLoaderHost || !routeState.hasStatusFilter || routeState.rowCount !== 1 || !routeState.rowCode || !routeState.clearedToDesktopDefaults) throw new Error(`Check-note page route did not render its loaded row: ${JSON.stringify(routeState)}`);
    const routeScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "check-note-workspace-headless.png"), Buffer.from(routeScreenshot.data, "base64"));
    const result = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page = "checks";
      db.settings.contextMenu = true;
      desktopSettings.rc_bank = "0";
      const record = { id: 501, type: "Check", direction: "Giri\\u015f (Al\\u0131nan)", issuer: "Audit Issuer", recipient: "Audit Recipient", bank_name: "Audit Bank", branch_name: "Main", check_no: "AUDIT-501", amount: 1200, due_date: "2026-11-02", status: "Portf\\u00f6yde" };
      window.currentGenericData = { rows: [record] };
      if (!document.querySelector("#genericHost")) { const host = document.createElement("div"); host.id = "genericHost"; document.body.append(host); }
      document.querySelector("#genericHost").innerHTML = '<table><tbody><tr data-id="501" data-check-status="Portf\\u00f6yde"></tr></tbody></table>';
      const requests = [];
      window.__checkContextAuditRequests = requests;
      apiFetch = async (url, options = {}) => { requests.push({ url, options }); return {}; };
      loadGenericModule = async () => {};
      const event = { clientX: 300, clientY: 240, prevented: false, preventDefault() { this.prevented = true; } };
      showContext(event, "check-note", "501");
      const menu = document.querySelector("#contextMenu");
      const initialActions = Array.from(menu.querySelectorAll("[data-check-context-action]"), button => button.dataset.checkContextAction);
      const detailAction = menu.querySelector('[data-check-context-action="detail"]');
      const statusToggle = menu.querySelector("[data-check-status-toggle]");
      const contextOpened = menu.classList.contains("open") && event.prevented;
      detailAction.click();
      const detailTitle = document.querySelector("#dialogTitle").textContent;
      document.querySelector("#appDialog").close("cancel");
      showContext({ ...event, prevented: false }, "check-note", "501");
      const secondMenu = document.querySelector("#contextMenu");
      const submenuToggle = secondMenu.querySelector("[data-check-status-toggle]");
      submenuToggle.click();
      const submenu = secondMenu.querySelector(".check-note-context-submenu-panel");
      const submenuOpen = !submenu.hidden && submenuToggle.getAttribute("aria-expanded") === "true";
      window.__checkContextState = { contextOpened, initialActions, detailTitle, submenuOpen };
      return window.__checkContextState;
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const statusResult = await evaluate(`(async () => {
      const menu = document.querySelector("#contextMenu");
      menu.querySelector('[data-check-context-action="Tahsil Edildi"]').click();
      await new Promise(resolve => setTimeout(resolve, 50));
      const requests = window.__checkContextAuditRequests;
      return { statusActionClosed: !menu.classList.contains("open"), requests: requests.map(request => ({ url: request.url, method: request.options.method || "GET", body: request.options.body ? JSON.parse(request.options.body) : null })) };
    })()`);
    Object.assign(result, statusResult);
    const requiredStatuses = ["Tahsil Edildi", "Ciro Edildi", "Ödendi", "Karşılıksız", "İade"];
    const actions = result.initialActions;
    const statusWrite = result.requests.find(request => request.url === "/api/desktop/checks/501/status");
    if (!result.contextOpened || !actions.includes("detail") || requiredStatuses.some(status => !actions.includes(status)) || actions.includes("Portföyde") || !result.detailTitle.includes("Çek / Senet") || !result.submenuOpen || !result.statusActionClosed || statusWrite?.method !== "POST" || statusWrite.body?.status !== "Tahsil Edildi" || exceptions.length) {
      throw new Error(`Check-note context audit failed: ${JSON.stringify({ ...result, screenshotData: undefined, exceptions })}`);
    }
    const imagePath = path.join(outputDir, "check-note-status-context-menu-headless.png");
    fs.writeFileSync(imagePath, Buffer.from(screenshot.data, "base64"));
    process.stdout.write(`${JSON.stringify({ routeState, ...result, screenshotData: undefined, imagePath, browserExceptions: exceptions.length })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    if (path.dirname(profile) === os.tmpdir() && path.basename(profile).startsWith("ayec-check-note-audit-")) {
      try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
    }
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
