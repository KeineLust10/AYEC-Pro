const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_QUICK_NOTES_AUDIT_CDP_PORT || 9241);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `customer-import-headless-profile-${process.pid}`);
async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edge, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl,
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/json`);
        target = (await response.json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
        if (target) break;
      } catch (_) {}
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a page target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
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
      const call = pending.get(message.id);
      if (!call) return;
      pending.delete(message.id);
      if (message.error) call.reject(new Error(message.error.message));
      else call.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      if (result.result?.subtype === "error") throw new Error(result.result.description);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof apiFetch === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    const preview = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      const writes=[];window.__customerImportWrites=writes;
      window.fetch=async(url,options={})=>{const path=String(url),method=options.method||'GET';let payload={};if(options.body){payload=JSON.parse(options.body);if(path.includes('/api/desktop/table/customers'))writes.push(payload)}const data=path.includes('/api/desktop/customers/import/preview')?{rows:[{name:'Import Buyer',phone:'5553000',email:'import@example.test',company_name:'Import Lab',address:'North Road',tax_no:'TX-99',city:'Ankara',type:'Kurumsal',notes:'fixture'}],count:1,header_row:2}:path.includes('/api/desktop/table/customers')?{id:222}:{ok:true};return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}})};
      hydrateDesktop=async()=>({});openCustomerImportDialog();const picker=document.querySelector('#appDialog'),pickerReady=picker.open&&!!picker.querySelector('#customerImportFile');picker.close('cancel');
      customerImportPreviewDialog({rows:[{name:'Import Buyer',phone:'5553000',email:'import@example.test',company_name:'Import Lab',address:'North Road',tax_no:'TX-99',city:'Ankara',type:'Kurumsal',notes:'fixture'}],count:1,header_row:2},'customers.csv');
      const dialog=document.querySelector('#appDialog'),inputs=[...dialog.querySelectorAll('[data-customer-import-field]')];dialog.querySelector('[data-customer-import-field="name"]').value='Edited Import Buyer';
      return {pickerReady,previewOpen:dialog.open,title:document.querySelector('#dialogTitle').textContent,fieldCount:inputs.length,headerRow:dialog.innerText.includes('Baslik satiri: 2'),inputValues:inputs.map(input=>input.value)};
    })()`);
    if (!preview.pickerReady || !preview.previewOpen || preview.fieldCount !== 9 || !preview.headerRow) throw new Error("Customer import preview did not open correctly: " + JSON.stringify(preview));
    const capture = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "customer-import-offscreen-headless.png"), Buffer.from(capture.data, "base64"));
    const save = await evaluate(`(async()=>{document.querySelector('#dialogSubmit').click();await new Promise(resolve=>setTimeout(resolve,250));const dialog=document.querySelector('#appDialog');return {closed:!dialog.open,writes:window.__customerImportWrites}})()`);
    if (!save.closed || save.writes.length !== 1 || save.writes[0].name !== "Edited Import Buyer" || save.writes[0].company_name !== "Import Lab" || save.writes[0].type !== "Kurumsal") throw new Error("Customer import save did not persist the edited row: " + JSON.stringify(save));
    if (exceptions.length) throw new Error("Browser exceptions: " + JSON.stringify(exceptions));
    console.log(JSON.stringify({ preview, save, browserExceptions: exceptions.length, screenshot: "customer-import-offscreen-headless.png" }));
    await send("Browser.close");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) socket.close();
    browser.kill();
  }
}

run().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
