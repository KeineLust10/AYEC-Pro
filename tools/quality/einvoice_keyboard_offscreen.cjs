const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9261);
const baseUrl = process.env.AYEC_AUDIT_URL;
const cookie = process.env.AYEC_EINVOICE_SESSION_COOKIE;
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `einvoice-keyboard-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !cookie) throw new Error("Authenticated e-invoice audit configuration is missing.");
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
    await send("Network.enable");
    await send("Network.setCookie", { name: "ayec_session", value: cookie, url: baseUrl });
    await send("Page.navigate", { url: baseUrl });
    for (let i = 0; i < 120; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof bindInvoiceComposer === 'function' && typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id)")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      page = "invoices";
      document.querySelector("#content").innerHTML = renderInvoiceComposer();
      bindInvoiceComposer();
      const lines = () => document.querySelectorAll("#invoiceLinesBody [data-invoice-line]").length;
      const initialRows = lines();
      window.dispatchEvent(new KeyboardEvent("keydown", {key:"F2",bubbles:true,cancelable:true}));
      const afterF2 = lines();
      window.dispatchEvent(new KeyboardEvent("keydown", {key:"F4",bubbles:true,cancelable:true}));
      const f4FocusedCustomer = document.activeElement?.id === "invoiceCustomer";
      document.querySelector("#invoiceCustomer").value = "Keyboard Fixture Customer";
      document.querySelector(".invoice-line-description").value = "Keyboard Fixture Service";
      const calls = [];
      window.apiFetch = async (url, options={}) => {calls.push({url,options}); return url === "/api/desktop/einvoice/send" ? {id:77,sandbox:true,uuid:"fixture-uuid",status:"TEST_QUEUED"} : {id:77};};
      window.dispatchEvent(new KeyboardEvent("keydown", {key:"F12",bubbles:true,cancelable:true}));
      for (let i=0;i<40&&!calls.some(call=>call.url==="/api/desktop/einvoice/send");i++) await new Promise(resolve=>setTimeout(resolve,100));
      return {role:currentAuthUser.role,initialRows,afterF2,f4FocusedCustomer,sendCalls:calls.filter(call=>call.url==="/api/desktop/einvoice/send").length,sendPayload:JSON.parse(calls.find(call=>call.url==="/api/desktop/einvoice/send")?.options.body||"{}").receiver_name||""};
    })()`);
    if (result.role !== "Admin" || result.afterF2 !== result.initialRows + 1 || !result.f4FocusedCustomer || result.sendCalls !== 1 || result.sendPayload !== "Keyboard Fixture Customer" || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outDir, "einvoice-keyboard-headless.png"), Buffer.from(shot.data, "base64"));
    console.log(JSON.stringify({ result, exceptions: exceptions.length, headless: true }));
  } finally {
    if (socket) socket.close();
    browser.kill();
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}
run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
