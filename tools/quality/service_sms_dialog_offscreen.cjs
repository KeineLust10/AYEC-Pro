const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_SMS_CDP_PORT || 19317);
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-sms-audit-"));
const baseUrl = process.argv[2];
const sessionCookie = process.env.AYEC_SERVICE_SMS_SESSION_COOKIE || "";
const customerIds = JSON.parse(process.env.AYEC_CUSTOMER_SMS_IDS || "[]").map(String);
const viewportWidth = Number(process.env.AYEC_SMS_VIEWPORT_WIDTH || 1280);
const viewportHeight = Number(process.env.AYEC_SMS_VIEWPORT_HEIGHT || 900);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcessTree(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
    killer.once("error", resolve);
  });
  await delay(400);
}

async function run() {
  if (!baseUrl || !sessionCookie) throw new Error("Authenticated SMS audit URL and session are required.");
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(tempRoot, "profile")}`, "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page");
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
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
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    const measureDialog = async () => {
      const metrics = await evaluate("(()=>{const dialog=document.querySelector('#appDialog'),footer=document.querySelector('#dialogFooter')||document.querySelector('#appDialog .dialog-footer'),d=dialog?.getBoundingClientRect(),f=footer?.getBoundingClientRect();return {viewportWidth:innerWidth,documentWidth:document.documentElement.scrollWidth,dialogLeft:d?.left??null,dialogRight:d?.right??null,footerLeft:f?.left??null,footerRight:f?.right??null}})()");
      if (metrics.documentWidth > metrics.viewportWidth + 1 || metrics.dialogLeft < 0 || metrics.dialogRight > metrics.viewportWidth + 1 || (metrics.footerRight !== null && (metrics.footerLeft < 0 || metrics.footerRight > metrics.viewportWidth + 1))) {
        throw new Error("SMS dialog exceeds the viewport: " + JSON.stringify(metrics));
      }
      return metrics;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: viewportWidth, height: viewportHeight, deviceScaleFactor: 1, mobile: viewportWidth <= 650 });
    const cookie = await send("Network.setCookie", { name: "ayec_session", value: sessionCookie, url: baseUrl, httpOnly: true, sameSite: "Lax" });
    if (!cookie.success) throw new Error("Could not install authenticated SMS test session.");
    await send("Page.navigate", { url: baseUrl });
    let authenticated = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      authenticated = await evaluate("typeof currentAuthUser !== 'undefined' && Boolean(window.ayecApplicationReady && currentAuthUser?.id)");
      if (authenticated) break;
      await delay(100);
    }
    if (!authenticated) throw new Error("Authenticated SMS app did not initialize.");
    await evaluate("(()=>{window.__smsFetchAudit=[];const nativeFetch=window.fetch.bind(window);window.fetch=async(input,init={})=>{const item={url:String(input),method:String(init.method||'GET').toUpperCase(),status:0};window.__smsFetchAudit.push(item);try{const response=await nativeFetch(input,init);item.status=response.status;if(!response.ok)item.errorBody=await response.clone().text();return response}catch(error){item.error=String(error);throw error}}})()");
    await evaluate("page='service-status';render()");
    let smsAction = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      smsAction = await evaluate("Boolean(document.querySelector('#statusWallHost [data-status-sms]'))");
      if (smsAction) break;
      await delay(100);
    }
    if (!smsAction) throw new Error("The authenticated service row did not expose its SMS action.");
    let smsActionClicked = false;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      smsActionClicked = await evaluate("(()=>{const button=document.querySelector('#statusWallHost [data-status-sms]');if(!button)return false;button.click();return true})()");
      if (smsActionClicked) break;
      await delay(50);
    }
    if (!smsActionClicked) throw new Error("The authenticated service SMS action disappeared before it could be clicked.");
    let dialogReady = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      dialogReady = await evaluate("Boolean(document.querySelector('#statusSmsMessage'))");
      if (dialogReady) break;
      await delay(100);
    }
    if (!dialogReady) throw new Error("The SMS compose dialog did not open.");
    const dialogViewport = await measureDialog();
    await evaluate("(()=>{const input=document.querySelector('#statusSmsMessage');input.value='Authenticated browser SMS QA';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#dialogSubmit').click()})()");
    let closed = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      closed = await evaluate("!document.querySelector('#appDialog')?.open");
      if (closed) break;
      await delay(100);
    }
    const result = await evaluate("({page:document.body.dataset.page,customer:window.currentGenericData?.rows?.[0]?.customer_name||'',closed:!document.querySelector('#appDialog')?.open,toast:document.querySelector('.toast')?.textContent||'',requests:window.__smsFetchAudit})");
    if (!closed || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    await evaluate("page='customers';render()");
    let customerRowsReady = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      customerRowsReady = await evaluate(`(${JSON.stringify(customerIds)}).every(id=>Boolean(document.querySelector('.customer-row-select[data-id="'+id+'"]')))`);
      if (customerRowsReady) break;
      await delay(100);
    }
    if (!customerRowsReady) throw new Error("The authenticated customer directory did not load the bulk SMS fixture rows.");
    const selected = await evaluate(`(()=>{const ids=${JSON.stringify(customerIds)};const inputs=ids.map(id=>document.querySelector('.customer-row-select[data-id="'+id+'"]'));if(inputs.some(input=>!input))return 0;for(const input of inputs){input.checked=true;input.dispatchEvent(new Event('change',{bubbles:true}))}const action=document.querySelector('[data-action=customer-sms-selected]');if(!action)return 0;action.click();return inputs.length})()`);
    if (selected !== customerIds.length) throw new Error("The customer bulk SMS action did not select every fixture record.");
    for (let index = 1; index <= 2; index += 1) {
      let customerDialogReady = false;
      for (let attempt = 0; attempt < 100; attempt += 1) {
        customerDialogReady = await evaluate("Boolean(document.querySelector('#appDialog')?.open&&document.querySelector('#customerSmsMessage'))");
        if (customerDialogReady) break;
        await delay(100);
      }
      if (!customerDialogReady) throw new Error(`Bulk SMS compose dialog ${index} did not open: ` + JSON.stringify(await evaluate("({open:document.querySelector('#appDialog')?.open,title:document.querySelector('#dialogTitle')?.textContent,returnValue:document.querySelector('#appDialog')?.returnValue,requests:window.__smsFetchAudit})")));
      await measureDialog();
      const recipientBefore = await evaluate("document.querySelector('#dialogBody .readonly-value')?.textContent||''");
      await evaluate(`(()=>{const input=document.querySelector('#customerSmsMessage');input.value='Bulk browser SMS QA ${index}';input.dispatchEvent(new Event('input',{bubbles:true}));document.querySelector('#dialogSubmit').click()})()`);
      let nextDialogReady = false;
      for (let attempt = 0; attempt < 120; attempt += 1) {
        nextDialogReady = index < 2
          ? await evaluate(`Boolean(document.querySelector('#appDialog')?.open&&document.querySelector('#customerSmsMessage')&&document.querySelector('#dialogBody .readonly-value')?.textContent!==${JSON.stringify(recipientBefore)})`)
          : await evaluate("!document.querySelector('#appDialog')?.open");
        if (nextDialogReady) break;
        await delay(100);
      }
      if (!nextDialogReady) throw new Error(`Bulk SMS compose dialog ${index} did not advance after submission: ` + JSON.stringify(await evaluate("({open:document.querySelector('#appDialog')?.open,recipient:document.querySelector('#dialogBody .readonly-value')?.textContent,toast:document.querySelector('.toast')?.textContent,requests:window.__smsFetchAudit})")));
    }
    const customerSmsPosts = await evaluate("window.__smsFetchAudit.filter(item=>item.url.includes('/api/desktop/customer-sms')&&item.method==='POST'&&item.status===200).length");
    if (customerSmsPosts !== 2 || exceptions.length) throw new Error(JSON.stringify({ customerSmsPosts, exceptions }));
    process.stdout.write(JSON.stringify({ ...result, viewportWidth, dialogViewport, customerSmsPosts, browserExceptions: exceptions.length }) + "\n");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) socket.close();
    await stopProcessTree(browser);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 12, retryDelay: 250 });
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
