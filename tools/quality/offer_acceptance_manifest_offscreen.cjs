const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const requestedPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 0);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `offer-acceptance-manifest-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const freePort = () => new Promise((resolve, reject) => {
  const server = net.createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => {
    const address = server.address();
    server.close(error => error ? reject(error) : resolve(address.port));
  });
});

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const port = requestedPort || await freePort();
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge CDP page was created.");
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
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof db === 'object' && typeof openManifestDialog === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("The web app did not become ready.");
    const opened = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const offer={id:801,offer_no:"PRF-AUDIT-1",total:500,currency_code:"TRY",status:"Teklif"};
      db.customers=[{id:712,name:"Audit Customer",company_name:"Audit Company",balances:{TRY:0,USD:0,EUR:0},quotes:[offer],services:[]}];
      const requests=[];
      window.__offerAcceptanceAudit={requests,hydrated:false};
      apiFetch=async(url,options={})=>{requests.push({url:String(url),payload:options.body?JSON.parse(options.body):null});return{offer_id:801,payment:125.5,remaining:374.5,currency:"TRY"}};
      hydrateDesktop=async()=>{window.__offerAcceptanceAudit.hydrated=true;return{}};
      customer360(db.customers[0]);
      const customerActionVisible=!!document.querySelector(".c360-accept-offer:not(:disabled)");
      document.querySelector("#appDialog")?.close("cancel");
      openManifestDialog({key:"offer_acceptance_dialog"});
      const picker=document.querySelector("#dialogForm"),customer=picker?.querySelector('tr[data-kind="customer-picker"][data-id="712"]');
      if(!picker||!customer)throw new Error("Customer selection was not opened.");
      customer.click();picker.requestSubmit();
      await new Promise(resolve=>setTimeout(resolve,140));
      const form=document.querySelector("#dialogForm"),amount=form?.querySelector('[name="payment_amount"]'),method=form?.querySelector('[name="payment_method"]');
      if(!form||!amount||!method)throw new Error("Offer acceptance form was not opened.");
      const fields=[...form.querySelectorAll("input,select")].map(item=>item.name||item.id);
      amount.value="125.50";amount.dispatchEvent(new Event("input",{bubbles:true}));
      const remaining=document.querySelector("#offerAcceptanceRemaining")?.textContent||"";
      const paymentMethod=method.value;
      return {customerActionVisible,pickerOpened:true,formOpened:true,fields,remaining,paymentMethod};
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const screenshotPath = path.join(outDir, "offer-acceptance-manifest-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const saved = await evaluate(`(async () => { document.querySelector("#dialogForm").requestSubmit(); await new Promise(resolve => setTimeout(resolve,120)); return {closed:!document.querySelector("#appDialog")?.open,audit:window.__offerAcceptanceAudit}; })()`);
    const request = saved.audit.requests[0];
    if (!opened.customerActionVisible || !opened.pickerOpened || !opened.formOpened || !opened.fields.includes("payment_amount") || !opened.fields.includes("payment_method") || opened.paymentMethod !== "Nakit" || saved.audit.requests.length !== 1 || request.url !== "/api/desktop/offers/801/accept" || request.payload.payment_amount !== 125.5 || request.payload.payment_method !== "Nakit" || !saved.audit.hydrated || !saved.closed || exceptions.length) throw new Error(JSON.stringify({ opened, saved, exceptions }));
    process.stdout.write(`${JSON.stringify({ ...opened, ...saved, exceptions, headless: true, screenshot: screenshotPath })}\n`);
  } finally {
    try { socket?.close(); } catch (_) {}
    if (process.platform === "win32") {
      const safeProfile = profile.replace(/'/g, "''");
      const command = `$profilePath='${safeProfile}'; $roots=Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like "*$profilePath*" -and $_.CommandLine -like '*--headless=new*' }; foreach($root in $roots){ & taskkill /PID $root.ProcessId /T /F | Out-Null }`;
      spawnSync("powershell.exe", ["-NoProfile", "-Command", command], { stdio: "ignore" });
      if (browser.pid) spawnSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" });
      await delay(500);
    } else browser.kill();
    const root = path.resolve(outDir);
    const resolvedProfile = path.resolve(profile);
    if (resolvedProfile.startsWith(root + path.sep) && fs.existsSync(resolvedProfile)) fs.rmSync(resolvedProfile, { recursive: true, force: true });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
