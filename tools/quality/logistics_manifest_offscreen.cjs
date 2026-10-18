const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_PORT || 18851);
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 19237);
const baseUrl = `http://127.0.0.1:${port}/`;
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-logistics-audit-"));
const profile = path.join(tempRoot, "edge-profile");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const children = [];

async function waitForHttp() {
  for (let i = 0; i < 150; i += 1) {
    try { if ((await fetch(baseUrl)).ok) return; } catch (_) {}
    await delay(200);
  }
  throw new Error("Temporary AYEC web server did not start.");
}

async function waitForPageTarget() {
  for (let i = 0; i < 150; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const target = (await response.json()).find(item => item.type === "page");
      if (target?.webSocketDebuggerUrl) return target;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a page target.");
}

function stopTree(child) {
  if (!child?.pid) return Promise.resolve();
  return new Promise(resolve => {
    const killer = spawn("taskkill", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", () => resolve());
    setTimeout(() => { try { child.kill(); } catch (_) {} resolve(); }, 3000).unref();
  });
}

async function run() {
  const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
  children.push(server);
  await waitForHttp();
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  children.push(browser);
  const target = await waitForPageTarget();
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
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
    if (message.error) entry.reject(new Error(message.error.message));
    else entry.resolve(message.result);
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

  try {
    await send("Runtime.enable");
    for (let i = 0; i < 100; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof navigate === 'function' && typeof genericModules !== 'undefined'")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.querySelector("#appShell")?.removeAttribute("inert");
      document.querySelector("#appShell")?.removeAttribute("aria-hidden");
      window.__logisticsData = Array.from({length: 10}, (_, index) => ({
        id: index + 1, tracking_no: "TRK-" + (index + 1), customer_name: "Demo Customer " + (index + 1),
        product_name: "Device " + (index + 1), service_name: "Service " + (index + 1), date: "2026-10-" + String(index + 1).padStart(2, "0"),
        cargo_firm: "Carrier A", return_cargo_firm: "Carrier B", status: index === 1 ? "Approval Pending" : index === 2 ? "Delivered" : "In Transit", type: "Outbound"
      }));
      apiFetch = async url => url.includes("/api/desktop/table/logistics") ? {rows: window.__logisticsData, columns: Object.keys(window.__logisticsData[0]), count: 10} : {rows: [], columns: [], count: 0};
      window.__manifestPopups = [];
      window.open = () => {
        const popup = {html: "", printCalls: 0, focused: false, document: {
          write(value) { popup.html += value; }, close() {},
        }, focus() { popup.focused = true; }, print() { popup.printCalls += 1; }};
        window.__manifestPopups.push(popup);
        return popup;
      };
      window.__logisticsDownloads = [];
      download = (name, rows) => window.__logisticsDownloads.push({name, rows});
      window.__toastEvents = [];
      toast = (message, type) => window.__toastEvents.push({message, type});
      page = "logistics";
      document.body.dataset.page = "logistics";
      navigate("logistics");
      await new Promise(resolve => setTimeout(resolve, 100));
      document.querySelector('[data-external-view="cargo"]').click();
      await new Promise(resolve => setTimeout(resolve, 40));
      const cargoTabVisible = !document.querySelector("#logisticsCargoPanel").hidden && document.querySelector('[data-external-view="cargo"]').classList.contains("active");
      document.querySelector("[data-logistics-print]").click();
      const bulk = window.__manifestPopups.at(-1);
      const bulkResult = {rows: (bulk.html.match(/<tr>/g) || []).length - 1, mentionsLastRow: bulk.html.includes("TRK-10"), printed: bulk.printCalls === 1 && bulk.focused};
      document.querySelector('[data-logistics-print="4"]').click();
      const single = window.__manifestPopups.at(-1);
      const singleResult = {rows: (single.html.match(/<tr>/g) || []).length - 1, includesTarget: single.html.includes("TRK-4"), excludesOther: !single.html.includes("TRK-3"), printed: single.printCalls === 1};
      const search = document.querySelector("#logisticsSearch");
      search.value = "Service 3";
      search.dispatchEvent(new Event("input", {bubbles: true}));
      const serviceSearchIds = [...document.querySelectorAll("#logisticsTableHost tbody tr")].map(row => Number(row.querySelector("small")?.textContent.replace("#", "")));
      search.value = "";
      search.dispatchEvent(new Event("input", {bubbles: true}));
      const serviceFilter = document.querySelector("#logisticsService");
      serviceFilter.value = "Service 3";
      serviceFilter.dispatchEvent(new Event("change", {bubbles: true}));
      const serviceFilterIds = [...document.querySelectorAll("#logisticsTableHost tbody tr")].map(row => Number(row.querySelector("small")?.textContent.replace("#", "")));
      document.querySelector("[data-logistics-clear]").click();
      const statusFilter = document.querySelector("#logisticsStatus");
      statusFilter.value = "status:Approval Pending";
      statusFilter.dispatchEvent(new Event("change", {bubbles: true}));
      const exactStatusFilterIds = [...document.querySelectorAll("#logisticsTableHost tbody tr")].map(row => Number(row.querySelector("small")?.textContent.replace("#", "")));
      document.querySelector("[data-logistics-clear]").click();
      document.querySelector('[data-logistics-page="1"]').click();
      const secondPage = {ids: [...document.querySelectorAll("#logisticsTableHost tbody tr")].map(row => Number(row.querySelector("small")?.textContent.replace("#", ""))), label: document.querySelector("#logisticsPagination b")?.textContent};
      document.querySelector('[data-logistics-page="-1"]').click();
      search.value = "Customer 2";
      search.dispatchEvent(new Event("input", {bubbles: true}));
      document.querySelector("[data-logistics-export]").click();
      const report = window.__logisticsDownloads[0];
      search.value = "missing record";
      search.dispatchEvent(new Event("input", {bubbles: true}));
      document.querySelector("[data-logistics-export]").click();
      return {cargoTabVisible, bulkResult, singleResult, serviceSearchIds, serviceFilterIds, exactStatusFilterIds, secondPage, reportName: report?.name, reportIds: report?.rows?.map(row => row.id), emptyExportCount: window.__logisticsDownloads.length, emptyWarning: window.__toastEvents.at(-1), exceptionCount: 0};
    })()`);
    if (!result.cargoTabVisible) throw new Error("Cargo tracking view did not become visible.");
    if (result.bulkResult.rows !== 10 || !result.bulkResult.mentionsLastRow || !result.bulkResult.printed) throw new Error(`Filtered bulk manifest mismatch: ${JSON.stringify(result.bulkResult)}`);
    if (result.singleResult.rows !== 1 || !result.singleResult.includesTarget || !result.singleResult.excludesOther || !result.singleResult.printed) throw new Error(`Single-row manifest mismatch: ${JSON.stringify(result.singleResult)}`);
    if (JSON.stringify(result.serviceSearchIds) !== JSON.stringify([3])) throw new Error(`Authorized-service search mismatch: ${JSON.stringify(result.serviceSearchIds)}`);
    if (JSON.stringify(result.serviceFilterIds) !== JSON.stringify([3])) throw new Error(`Authorized-service filter mismatch: ${JSON.stringify(result.serviceFilterIds)}`);
    if (JSON.stringify(result.exactStatusFilterIds) !== JSON.stringify([2])) throw new Error(`Exact status filter mismatch: ${JSON.stringify(result.exactStatusFilterIds)}`);
    if (JSON.stringify(result.secondPage.ids) !== JSON.stringify([9, 10]) || result.secondPage.label !== "2 / 2") throw new Error(`Pagination mismatch: ${JSON.stringify(result.secondPage)}`);
    if (!result.reportName?.endsWith(".csv") || JSON.stringify(result.reportIds) !== JSON.stringify([2])) throw new Error(`Filtered report export mismatch: ${JSON.stringify(result)}`);
    if (result.emptyExportCount !== 1 || result.emptyWarning?.type !== "warning") throw new Error(`Empty report warning mismatch: ${JSON.stringify(result)}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${exceptions.join(" | ")}`);
    process.stdout.write(JSON.stringify({ ...result, exceptionCount: exceptions.length }) + "\n");
  } finally {
    socket.close();
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; }).finally(async () => {
  await Promise.all(children.map(stopTree));
  await delay(500);
  fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
});
