const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9251);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `contracts-dblclick-profile-${process.pid}`);
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
      const msg = JSON.parse(event.data);
      if (msg.method === "Runtime.exceptionThrown") exceptions.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
      if (!msg.id) return;
      const task = pending.get(msg.id);
      if (!task) return;
      pending.delete(msg.id);
      msg.error ? task.reject(new Error(msg.error.message)) : task.resolve(msg.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
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
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      document.body.dataset.page = "contracts"; db.settings.doubleClick = false;
      let calls = [];
      apiFetch = async url => { calls.push(url); return { contract: { id: 44, title: "Fixture contract", customer_name: "Fixture customer", contract_type: "Servis", description: "Details" }, attachments: [] }; };
      const host = document.createElement("div"); host.innerHTML = '<table class="contracts-reference-table"><tbody><tr data-contract-id="44"><td>Fixture</td><td><button type="button">Action</button></td></tr></tbody></table>';
      document.body.append(host); const row = host.querySelector("tr");
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 20));
      const disabled = { calls: calls.length, opened: document.querySelector("#appDialog")?.open === true };
      db.settings.doubleClick = true;
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 80));
      const enabled = { calls: calls.length, opened: document.querySelector("#appDialog")?.open === true, title: document.querySelector("#dialogTitle")?.textContent || "", content: document.querySelector("#dialogBody")?.textContent || "" };
      document.querySelector("#appDialog")?.close();
      host.querySelector("button").dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 20));
      return { disabled, enabled, buttonTargetIgnored: calls.length === 1 };
    })()`);
    if (result.disabled.calls !== 0 || result.disabled.opened || result.enabled.calls !== 1 || !result.enabled.opened || !(result.enabled.title.startsWith("S") && result.enabled.title.endsWith(" & Ekleri")) || !result.enabled.content.includes("Fixture contract") || !result.buttonTargetIgnored || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outDir, "contracts-double-click-detail-headless.png"), Buffer.from(shot.data, "base64"));
    console.log(JSON.stringify({ result, exceptions: exceptions.length, headless: true }));
  } finally {
    if (socket) socket.close();
    browser.kill();
  }
}
run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });

