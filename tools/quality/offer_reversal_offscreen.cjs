const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const freePort = () => new Promise((resolve, reject) => {
  const server = net.createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => {
    const port = server.address().port;
    server.close(error => error ? reject(error) : resolve(port));
  });
});

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const profile = path.join(outDir, `offer-reversal-profile-${process.pid}`);
  const port = await freePort();
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge page was created.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map(), exceptions = [];
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
      const timer = setTimeout(() => { pending.delete(requestId); reject(new Error(`CDP command timed out: ${method}`)); }, 30000);
      pending.set(requestId, { resolve(value) { clearTimeout(timer); resolve(value); }, reject(error) { clearTimeout(timer); reject(error); } });
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
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate('typeof loadGenericModule === "function" && typeof genericTable === "function" && typeof openOfferRevisionDialog === "function"');
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Offer revision UI scripts did not become ready.");
    await delay(500);
    const licenseRoute = await evaluate(`(async()=>{
      const originalNavigate=navigate,originalSection=settingsSection,originalOpenDialog=openDialog;let destination="",opened=null;
      navigate=route=>{destination=route};
      openDialog=(title,eyebrow,body,onSubmit,submitLabel)=>{opened={title,eyebrow,body,submitLabel,onSubmit}};
      openManifestDialog({key:"license_keygen_dialog"});
      const submitted=await opened?.onSubmit?.({});
      const result={destination,section:settingsSection,dialog:opened&&{title:opened.title,eyebrow:opened.eyebrow,body:opened.body,submitLabel:opened.submitLabel},submitted};
      navigate=originalNavigate;settingsSection=originalSection;openDialog=originalOpenDialog;
      return result;
    })()`);
    if (licenseRoute.destination !== "settings" || licenseRoute.section !== "license" || licenseRoute.submitted !== true || licenseRoute.dialog?.title !== "HWID Lisans Anahtar\u0131" || licenseRoute.dialog?.submitLabel !== "Merkezi Lisans Ayarlar\u0131n\u0131 A\u00e7" || !licenseRoute.dialog?.body.includes("Web s\u00fcr\u00fcm\u00fc ba\u011f\u0131ms\u0131z HWID anahtar\u0131 olu\u015fturmaz.")) throw new Error(`Legacy license dialog did not explain the central license path: ${JSON.stringify(licenseRoute)}`);
    const licenseDialog = await evaluate(`(()=>{
      openManifestDialog({key:"license_keygen_dialog"});
      return {open:document.querySelector("#appDialog")?.open===true,title:document.querySelector("#dialogTitle")?.textContent||"",body:document.querySelector("#dialogBody")?.innerText||"",action:document.querySelector("#dialogSubmit")?.textContent||""};
    })()`);
    if (!licenseDialog.open || licenseDialog.title !== "HWID Lisans Anahtar\u0131" || !licenseDialog.body.includes("Web s\u00fcr\u00fcm\u00fc ba\u011f\u0131ms\u0131z HWID anahtar\u0131 olu\u015fturmaz.") || licenseDialog.action !== "Merkezi Lisans Ayarlar\u0131n\u0131 A\u00e7") throw new Error(`Legacy license explanation dialog did not render: ${JSON.stringify(licenseDialog)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const opened = await evaluate(`(async()=>{
      const offer={id:81,offer_no:"OFF-REV-81",status:"processed",total:2400,currency_code:"TRY",customer_id:7,customer_name:"Audit Customer"};
      const columns=["offer_no","created_at","customer_name","company_name","total","created_by","status","pdf_path"];
      const host=document.createElement("div");host.id="offerReversalAuditHost";document.body.append(host);
      host.innerHTML=genericTable({table:"offers"},{columns,rows:[offer]});
      bindOfferRevisionActions([offer]);
      const button=host.querySelector("[data-offer-reverse]");
      const actionVisible=Boolean(button);
      button?.click();
      const dialog={title:document.querySelector("#dialogTitle")?.textContent||"",body:document.querySelector("#dialogBody")?.innerText||"",required:Boolean(document.querySelector("#offerRevisionReason")?.required)};
      return {actionVisible,dialog};
    })()`);
    if (!opened.actionVisible || !opened.dialog.title.includes("Revize") || !opened.dialog.required) throw new Error(`Offer revision dialog did not open correctly: ${JSON.stringify(opened)}`);
    const first = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    fs.writeFileSync(path.join(outDir, "offer-reversal-dialog-headless.png"), Buffer.from(first.data, "base64"));
    const submitted = await evaluate(`(async()=>{
      window.__offerReversalWrites=[];
      apiFetch=async(url,options={})=>{window.__offerReversalWrites.push({url:String(url),payload:JSON.parse(options.body||"{}")});return {offer_id:81,reversal_tracking_no:"SRV-REV-81"}};
      hydrateDesktop=async()=>{};render=()=>{};
      const field=document.querySelector("#offerRevisionReason");field.value="Customer changed product quantity";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve=>setTimeout(resolve,80));
      const write=window.__offerReversalWrites[0];
      const closed=!document.querySelector("#appDialog").open;
      return {write,closed,toast:document.querySelector(".toast")?.innerText||""};
    })()`);
    if (submitted.write?.url !== "/api/desktop/offers/81/reverse" || submitted.write?.payload?.reason !== "Customer changed product quantity" || !submitted.closed) throw new Error(`Offer reversal submission mismatch: ${JSON.stringify(submitted)}`);
    const resultShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    fs.writeFileSync(path.join(outDir, "offer-reversal-result-headless.png"), Buffer.from(resultShot.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(JSON.stringify({ licenseRoute, licenseDialog, actionVisible: opened.actionVisible, dialog: opened.dialog, submission: submitted, exceptions, screenshots: ["offer-reversal-dialog-headless.png", "offer-reversal-result-headless.png"] }) + "\n");
  } finally {
    try { await send("Browser.close"); } catch (_) {}
    try { socket?.close(); } catch (_) {}
    try { spawnSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) { browser.kill(); }
    await delay(300);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
