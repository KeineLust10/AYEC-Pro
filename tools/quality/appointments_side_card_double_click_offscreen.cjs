const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9252);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `appointment-side-double-click-${process.pid}`);
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
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable"); await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let i = 0; i < 80; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof appointmentDialog === 'function' && document.querySelector('#appDialog')")) break;
      await delay(200);
    }
    const result = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      document.body.dataset.page = "appointments";
      db.customers = [{id: 17, name: "Fixture Customer"}];
      db.appointments = [{id: 82, customerId: "17", customer: "Fixture Customer", date: "2026-10-16", time: "10:00", title: "Fixture appointment", status: "Bekliyor"}];
      const card = document.createElement("article"); card.className = "appointment-ref-event appointment-ref-side-event"; card.dataset.kind = "appointment"; card.dataset.id = "82";
      card.innerHTML = '<strong>Fixture appointment</strong><button type="button" data-appointment-outcome="edit" data-id="82">Detail</button>'; document.body.append(card);
      card.querySelector("button").dispatchEvent(new MouseEvent("dblclick", {bubbles:true, cancelable:true}));
      const buttonIgnored = !document.querySelector("#appDialog")?.open;
      card.querySelector("strong").dispatchEvent(new MouseEvent("dblclick", {bubbles:true, cancelable:true}));
      const dialog = document.querySelector("#appDialog");
      return {buttonIgnored, opened: dialog?.open === true, title: document.querySelector("#dialogTitle")?.textContent || "", customer: document.querySelector('#dialogBody input[name="customerSearch"]')?.value || "", date: document.querySelector('#dialogBody input[name="date"]')?.value || ""};
    })()`);
    if (!result.buttonIgnored || !result.opened || !result.title.startsWith("Randevuyu ") || !result.title.endsWith("enle") || result.customer !== "Fixture Customer" || result.date !== "2026-10-16" || exceptions.length) throw new Error(JSON.stringify({result, exceptions}));
    const screenshot = await send("Page.captureScreenshot", {format:"png", captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir, "appointments-side-card-double-click-headless.png"), Buffer.from(screenshot.data, "base64"));
    console.log(JSON.stringify({result, exceptions: exceptions.length, headless: true}));
  } finally {
    if (socket) socket.close();
    browser.kill();
  }
}
run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });




