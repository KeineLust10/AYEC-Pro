const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9242);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `brand-export-headless-profile-${process.pid}`);
const pageKind = process.env.AYEC_AUDIT_PAGE === "product-groups" ? "product-groups" : "brands";
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function findPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const target = (await response.json()).find(item => item.type === "page");
      if (target?.webSocketDebuggerUrl) return target;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1440,1000", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  const pending = new Map();
  const exceptions = [];
  let nextId = 0;
  try {
    const target = await findPage();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
      if (!message.id) return;
      const item = pending.get(message.id);
      if (!item) return;
      pending.delete(message.id);
      if (message.error) item.reject(new Error(message.error.message));
      else item.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof genericShell === 'function' && typeof render === 'function'")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const groupPage = "__PAGE_KIND__" === "product-groups";
      page = groupPage ? "product-groups" : "brands";
      document.body.dataset.page = page;
      window.currentGenericMeta = genericModules.brands;
      if (groupPage) {
        window.apiFetch = async () => ({rows:[], count:0, columns:[]});
        render();
      } else {
        document.querySelector("#content").innerHTML = genericShell(genericModules.brands);
      }
      const requests = [];
      let prints = 0;
      window.fetch = async url => {
        requests.push(String(url));
        return {ok:true,blob:async()=>new Blob(["export"]),json:async()=>({})};
      };
      URL.createObjectURL = () => "blob:test";
      URL.revokeObjectURL = () => {};
      HTMLAnchorElement.prototype.click = function () { this.dataset.downloaded = this.download; };
      window.print = () => { prints += 1; };
      document.querySelector(groupPage ? "#groupPdf" : '[data-brand-export="pdf"]').click();
      await new Promise(resolve => setTimeout(resolve, 50));
      document.querySelector(groupPage ? "#groupExport" : '[data-brand-export="excel"]').click();
      await new Promise(resolve => setTimeout(resolve, 50));
      document.querySelector(groupPage ? "#groupPrint" : '[data-brand-export="print"]').click();
      return {requests, prints, page:document.body.dataset.page, pdfVisible:!!document.querySelector(groupPage ? "#groupPdf" : '[data-brand-export="pdf"]')};
    })()`.replace("__PAGE_KIND__", pageKind));
    const image = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const routePrefix = pageKind === "product-groups" ? "/product-groups/export/" : "/device-brands/export/";
    const screenshotPath = `${pageKind}-export-headless.png`;
    fs.writeFileSync(path.join(outputDir, screenshotPath), Buffer.from(image.data, "base64"));
    if (result.requests.length !== 2 || !result.requests[0].includes(`${routePrefix}pdf`) || !result.requests[1].includes(`${routePrefix}xlsx`) || result.prints !== 1 || exceptions.length) {
      throw new Error(JSON.stringify({ result, exceptions }));
    }
    process.stdout.write(JSON.stringify({ ...result, browserExceptions:exceptions.length, headless:true, screenshot:`output/playwright/${screenshotPath}` }) + "\n");
  } finally {
    if (socket) socket.close();
    browser.kill();
    await delay(300);
    try {
      const { execFileSync } = require("node:child_process");
      const pids = execFileSync("powershell", ["-NoProfile", "-Command", `$p=Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*brand-export-headless-profile-${process.pid}*' }; $p.ProcessId`], { encoding:"utf8" });
      for (const pid of pids.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) { try { process.kill(Number(pid)); } catch (_) {} }
    } catch (_) {}
    await delay(300);
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
