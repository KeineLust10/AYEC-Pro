const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 36000 + (process.pid % 10000);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve("output/playwright");
const profile = path.join(outputDir, `loaner-context-probe-${process.pid}`);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/json`);
        target = (await response.json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await wait(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose the app page.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const commandId = ++id;
      pending.set(commandId, { resolve, reject });
      socket.send(JSON.stringify({ id: commandId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof renderNav === 'function'")) break;
      await wait(200);
    }
    const results = [];
    for (const kind of ["depot", "transaction"]) {
      const state = await evaluate(`(() => {
        document.querySelector("#authRoot")?.remove();
        document.body.classList.remove("auth-active");
        page = "loaners"; document.body.dataset.page = "loaners";
        db.settings.contextMenu = true; ayecLoanerView = "active";
        ayecLoanerDevices = [{ id: 954, status: "Depoda", brand_model: "Fixture Device" }];
        ayecLoanerHistory = [{ id: 955, device_id: 954, date_returned: null }];
        document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-loaner-row="954" data-loaner-kind="depot"><td>Fixture inventory device</td></tr><tr data-loaner-row="955" data-loaner-kind="transaction"><td>Fixture active loan</td></tr></tbody></table></section>';
        const menu = document.querySelector("#contextMenu"); menu.classList.remove("open");
        const row = document.querySelector('[data-loaner-kind="${kind}"]');
        const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 360, clientY: 260 });
        row.dispatchEvent(event);
        const rect = menu.getBoundingClientRect(), style = getComputedStyle(menu);
        return { kind: "${kind}", prevented: event.defaultPrevented, open: menu.classList.contains("open"), display: style.display, visibility: style.visibility, zIndex: style.zIndex, rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }, text: menu.innerText, actions: Array.from(menu.querySelectorAll("[data-loaner-context]"), button => button.dataset.loanerContext) };
      })()`);
      if (!state.prevented || !state.open || state.display === "none" || state.visibility === "hidden" || state.rect.width <= 0 || state.rect.height <= 0 || state.actions.length === 0) throw new Error(`Loaner ${kind} menu did not render visibly: ${JSON.stringify(state)}`);
      await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
      await new Promise(resolve => setTimeout(resolve, 50));
      const afterEmulation = await evaluate(`(() => { const menu = document.querySelector("#contextMenu"), style = getComputedStyle(menu), rect = menu.getBoundingClientRect(); return { display: style.display, visibility: style.visibility, open: menu.classList.contains("open"), rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height } }; })()`);
      if (!afterEmulation.open || afterEmulation.display === "none" || afterEmulation.visibility === "hidden" || afterEmulation.rect.width <= 0 || afterEmulation.rect.height <= 0) throw new Error(`Loaner ${kind} menu became invisible after media emulation: ${JSON.stringify(afterEmulation)}`);
      const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true, optimizeForSpeed: true, clip: { x: 0, y: 0, width: 1280, height: 900, scale: 1 } });
      const filename = `loaner-${kind}-context-menu-visual-probe.png`;
      fs.writeFileSync(path.join(outputDir, filename), Buffer.from(screenshot.data, "base64"));
      results.push({ ...state, afterEmulation, screenshot: path.join(outputDir, filename) });
    }
    process.stdout.write(JSON.stringify({ results }) + "\n");
  } finally {
    try { await socket?.send(JSON.stringify({ id: 99999, method: "Browser.close" })); } catch (_) {}
    try { socket?.close(); } catch (_) {}
    try {
      const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
      const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      for (const pid of output.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
    } catch (_) {
      try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) { browser.kill(); }
    }
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
