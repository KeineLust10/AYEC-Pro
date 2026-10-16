const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `einvoice-integration-headless-profile-${process.pid}`);

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const expectedDownload = path.join(outputDir, `proforma_${new Date().toISOString().slice(0,10).replaceAll("-","")}.pdf`);
  if (fs.existsSync(expectedDownload)) fs.unlinkSync(expectedDownload);
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1120,820", baseUrl], { stdio: "ignore", windowsHide: true });
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
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text || "Browser exception");
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
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text || "Evaluation failed");
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: outputDir });
    await send("Emulation.setDeviceMetricsOverride", { width: 1120, height: 820, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && document.querySelector('#appShell')")) break;
      await delay(200);
    }
    await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const shell=document.querySelector("#appShell");shell?.removeAttribute("inert");shell?.removeAttribute("aria-hidden");
      window.__einvoiceRequests=[];
      const nativeFetch=window.fetch.bind(window);
      window.fetch=async(url,options={})=>{
        const path=String(url),method=String(options.method||"GET").toUpperCase();
        if(path.includes("/api/desktop/einvoice/settings")){
          window.__einvoiceRequests.push({method,body:options.body||null});
          const body=method==="GET"?{provider:"custom",environment:"sandbox",api_url:"",api_key_configured:false}:{ok:true,detail:"Sandbox test passed.",settings:{provider:"custom",environment:"sandbox",api_url:"",api_key_configured:false}};
          return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
        }
        if(path.includes("/api/desktop/table/e_invoices")){
          window.__einvoiceRequests.push({method,path,body:options.body||null});
          return new Response(JSON.stringify({id:42}),{status:200,headers:{"Content-Type":"application/json"}});
        }
        if(path.includes("/api/desktop/einvoice/send")){
          window.__einvoiceRequests.push({method,path,body:options.body||null});
          return new Response(JSON.stringify({ok:true,id:42,uuid:"ETTN-AUDIT",status:"TEST_QUEUED",sandbox:true}),{status:200,headers:{"Content-Type":"application/json"}});
        }
        if(path.includes("/api/desktop/einvoice/proforma.pdf")){
          window.__einvoiceRequests.push({method,path,body:options.body||null});
          return new Response(new Uint8Array([37,80,68,70,45,97,117,100,105,116]),{status:200,headers:{"Content-Type":"application/pdf"}});
        }
        return nativeFetch(url,options);
      };
      page="invoices";render();
      return true;
    })()`);
    await evaluate('document.querySelector("[data-invoice-action=integration]")?.click()');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate('document.querySelector("#appDialog")?.open && document.querySelector("#einvoiceProvider")')) break;
      await delay(100);
    }
    const fields = await evaluate(`(() => {
      const dialog=document.querySelector("#appDialog"),box=dialog?.getBoundingClientRect();
      const style=dialog?getComputedStyle(dialog):null,body=document.querySelector("#dialogBody"),form=dialog?.querySelector("form"),formBox=form?.getBoundingClientRect();
      return {open:!!dialog?.open,className:dialog?.className,provider:!!document.querySelector(\"#einvoiceProvider\"),environment:!!document.querySelector(\"#einvoiceEnvironment\"),apiUrl:!!document.querySelector(\"#einvoiceApiUrl\"),apiKeyType:document.querySelector(\"#einvoiceApiKey\")?.type||\"\",testButton:!!document.querySelector(\"#einvoiceTestButton\"),dialogBounds:box?{x:Math.round(box.x),y:Math.round(box.y),width:Math.round(box.width),height:Math.round(box.height)}:null,computed:{height:style?.height,minHeight:style?.minHeight,maxHeight:style?.maxHeight,padding:style?.padding,scrollHeight:dialog?.scrollHeight,bodyHeight:body?.getBoundingClientRect().height,bodyScrollHeight:body?.scrollHeight,formHeight:formBox?.height}};
    })()`);
    if (!fields.open || !fields.provider || !fields.environment || fields.apiKeyType !== "password" || !fields.testButton) throw new Error(`Integration dialog is incomplete: ${JSON.stringify(fields)}`);
    await delay(200);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const imagePath = path.join(outputDir, "einvoice-integration-dialog-headless.png");
    fs.writeFileSync(imagePath, Buffer.from(screenshot.data, "base64"));
    await evaluate('document.querySelector("#einvoiceTestButton")?.click()');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if ((await evaluate('document.querySelector("#einvoiceTestStatus")?.dataset.state')) === "success") break;
      await delay(100);
    }
    const testState = await evaluate(`({status:document.querySelector("#einvoiceTestStatus")?.dataset.state,requests:window.__einvoiceRequests})`);
    if (testState.status !== "success" || testState.requests.filter(item => item.method === "POST").length !== 1) throw new Error(`Sandbox connection action failed: ${JSON.stringify(testState)}`);
    await evaluate('document.querySelector("#einvoiceApiUrl").value="https://sandbox.example.test";document.querySelector("#einvoiceApiKey").value="browser-secret";document.querySelector("#dialogSubmit")?.click()');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate('!document.querySelector("#appDialog")?.open')) break;
      await delay(100);
    }
    const final = await evaluate('({dialogOpen:!!document.querySelector("#appDialog")?.open,requests:window.__einvoiceRequests})');
    const saveRequest = final.requests.find(item => item.method === "POST" && String(item.body||"").includes("browser-secret"));
    if (final.dialogOpen || !saveRequest) throw new Error(`Settings save action failed: ${JSON.stringify(final)}`);
    await evaluate('(()=>{const customer=document.querySelector("#invoiceCustomer"),description=document.querySelector(".invoice-line-description"),quantity=document.querySelector(".invoice-line-qty"),price=document.querySelector(".invoice-line-price");customer.value="Audit Customer";customer.dispatchEvent(new Event("input",{bubbles:true}));description.value="Repair";description.dispatchEvent(new Event("input",{bubbles:true}));quantity.value="2";quantity.dispatchEvent(new Event("input",{bubbles:true}));price.value="100";price.dispatchEvent(new Event("input",{bubbles:true}));document.querySelector("[data-invoice-action=send]")?.click()})()');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate('window.__einvoiceRequests.some(item => item.path === "/api/desktop/einvoice/send")')) break;
      await delay(100);
    }
    const sendState = await evaluate('(()=>{const request=window.__einvoiceRequests.find(item=>item.path==="/api/desktop/einvoice/send");return {request:request||null,draftCount:window.__einvoiceRequests.filter(item=>item.path==="/api/desktop/table/e_invoices").length}})()');
    const sendPayload = sendState.request ? JSON.parse(sendState.request.body) : null;
    if (!sendPayload || sendPayload.receiver_name !== "Audit Customer" || sendPayload.invoice.lines[0]["invoice-line-description"] !== "Repair" || sendState.draftCount !== 1) throw new Error(JSON.stringify(sendState));
    await evaluate('document.querySelector("[data-invoice-action=proforma]")?.click()');
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate('window.__einvoiceRequests.some(item => item.path === "/api/desktop/einvoice/proforma.pdf")')) break;
      await delay(100);
    }
    const proforma = await evaluate('(()=>{const item=window.__einvoiceRequests.find(request=>request.path==="/api/desktop/einvoice/proforma.pdf");return item?JSON.parse(item.body):null})()');
    if (!proforma || proforma.receiver_name !== "Audit Customer" || proforma.invoice.lines[0]["invoice-line-description"] !== "Repair") throw new Error(JSON.stringify(proforma));
    await delay(500);
    await evaluate('document.querySelector("[data-invoice-action=preview]")?.click()');
    const preview = await evaluate('(()=>{const dialog=document.querySelector("#appDialog"),content=dialog?.querySelector(".einvoice-preview-text")?.textContent||"";return {open:!!dialog?.open,content,printButtons:[...document.querySelectorAll("button")].filter(button=>/print/i.test(button.textContent)).length}})()');
    if (!preview.open || !preview.content.includes("Audit Customer") || !preview.content.includes("Repair") || preview.printButtons) throw new Error(`Invoice preview failed: ${JSON.stringify(preview)}`);
    await evaluate('document.querySelector("#dialogSubmit")?.click()');
    const previewClosed = await evaluate('!document.querySelector("#appDialog")?.open');
    if (!previewClosed) throw new Error("Invoice preview did not close after its action.");
    const downloads = fs.readdirSync(outputDir).filter(name => /^proforma_\d{8}\.pdf$/.test(name));
    if (!downloads.length) throw new Error("Proforma download was not created.");
    const result = { ...fields, testStatus: testState.status, sendDrafts: sendState.draftCount, proformaRequests: 1, preview: { open: preview.open, closedAfterAction: previewClosed, hasCustomer: preview.content.includes("Audit Customer"), hasLine: preview.content.includes("Repair") }, downloads, requestMethods: final.requests.map(item => item.method).concat(sendState.request.method), screenshot: imagePath, browserExceptions: exceptions };
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    console.log(JSON.stringify(result, null, 2));
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) { browser.kill(); }
  }
}

run().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });
