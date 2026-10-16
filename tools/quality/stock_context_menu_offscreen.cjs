const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9241);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `stock-context-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function findPage() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const page = (await response.json()).find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  const exceptions = [];
  let socket;
  let nextId = 0;
  const pending = new Map();
  try {
    const target = await findPage();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 10000);
      pending.set(id, { resolve(value) { clearTimeout(timer); resolve(value); }, reject(error) { clearTimeout(timer); reject(error); } });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof renderStock === 'function' && typeof showContext === 'function'")) break;
      await delay(200);
    }
    const result = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page="stock";document.body.dataset.page="stock";currentAuthUser={role:"Admin"};
      db.settings.contextMenu=true;
      db.stock=[{id:901,code:"STK-AUDIT",name:"Fixture Product",description:"Context menu fixture",category:"General",qty:12,min:2,unit:"Adet",buy:10,sell:15,currency:"TRY",shelf:"A-01"}];
      document.querySelector("#content").innerHTML=renderStock();bindPageRows();
      const row=document.querySelector('tr[data-kind="stock"]');
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:1260,clientY:890});
      row.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu");
      const rect=menu.getBoundingClientRect();
      const regular={prevented:event.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-context-action]"),button=>({action:button.dataset.contextAction,label:button.textContent.trim()})),separators:menu.querySelectorAll(".context-menu-separator").length,rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},style:{background:getComputedStyle(menu).backgroundColor,color:getComputedStyle(menu).color,font:getComputedStyle(menu.querySelector("button")).font},insideViewport:rect.left>=0&&rect.right<=innerWidth&&rect.top>=0&&rect.bottom<=innerHeight};
      return regular;
    })()`);
    const expected = ["movement", "edit-product", "stock-photo", "stock-pdf", "stock-print", "stock-excel", "delete-product"];
    if (!result.open || !result.prevented || JSON.stringify(result.actions.map(item => item.action)) !== JSON.stringify(expected) || result.separators !== 2 || !result.insideViewport) throw new Error(`Stock context menu mismatch: ${JSON.stringify(result)}`);
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "stock-context-menu-headless.png"), Buffer.from(shot.data, "base64"));
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: result.rect.x + 60, y: result.rect.y + 11, buttons: 0 });
    const hoverBackground = await evaluate('getComputedStyle(document.querySelector("#contextMenu button")).backgroundColor');
    if (hoverBackground !== "rgb(30, 64, 175)") throw new Error(`Stock context hover color mismatch: ${hoverBackground}`);
    const outcome = await evaluate(`(async () => {
      const row=document.querySelector('tr[data-kind="stock"]'),menu=document.querySelector("#contextMenu");
      menu.querySelector('[data-context-action="delete-product"]').click();
      const dialog={open:document.querySelector("#appDialog").open,title:document.querySelector("#dialogTitle")?.textContent,hasPassword:document.querySelector('#dialogBody input[type="password"]')!==null,hasConfirm:document.querySelector("#dialogSubmit")?.textContent};
      document.querySelector("#dialogCancel")?.click();
      const dismissed=!document.querySelector("#appDialog").open;
      db.settings.contextMenu=false;
      const disabledMenuEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});row.dispatchEvent(disabledMenuEvent);
      db.settings.doubleClick=true;
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true}));
      const doubleClick={open:document.querySelector("#appDialog").open,title:document.querySelector("#dialogTitle")?.textContent,productName:document.querySelector('#dialogBody input[name="name"]')?.value};
      document.querySelector("#dialogCancel")?.click();
      db.settings.doubleClick=false;
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true}));
      const originalFetch=window.fetch,originalPrint=window.print,originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL,originalAnchorClick=HTMLAnchorElement.prototype.click;
      let printCalls=0,downloadName="";
      window.fetch=async url=>{window.__stockPdfRequest=String(url);return new Response("%PDF-stock-audit",{status:200,headers:{"Content-Type":"application/pdf"}})};
      URL.createObjectURL=()=>"blob:stock-audit";URL.revokeObjectURL=()=>{};
      HTMLAnchorElement.prototype.click=function(){downloadName=this.download};
      window.print=()=>{printCalls++};
      contextAction("stock","901","stock-pdf");
      await new Promise(resolve=>setTimeout(resolve,40));
      const pdf={request:window.__stockPdfRequest,download:downloadName,printCalls};
      contextAction("stock","901","stock-print");
      const print={calls:printCalls};
      window.fetch=originalFetch;window.print=originalPrint;URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;HTMLAnchorElement.prototype.click=originalAnchorClick;
      return {dialog,dismissed,disabled:{open:menu.classList.contains("open"),prevented:disabledMenuEvent.defaultPrevented},doubleClick,doubleClickDisabled:document.querySelector("#appDialog").open,pdf,print};
    })()`);
    if (!outcome.dialog.open || !outcome.dialog.hasPassword || !outcome.dismissed || outcome.disabled.open || outcome.disabled.prevented || !outcome.doubleClick.open || outcome.doubleClick.title !== "\u00dcr\u00fcn\u00fc D\u00fczenle" || outcome.doubleClick.productName !== "Fixture Product" || outcome.doubleClickDisabled || outcome.pdf.request !== "/api/desktop/stock/export/pdf" || !/^stok_listesi_.*\.pdf$/.test(outcome.pdf.download) || outcome.pdf.printCalls !== 0 || outcome.print.calls !== 1 || exceptions.length) throw new Error(`Stock context action mismatch: ${JSON.stringify({ result, outcome, exceptions })}`);
    const movementMenu = await evaluate(`(() => {
      page="movements";document.body.dataset.page="movements";db.settings.contextMenu=true;desktopSettings.rc_stock="1";
      document.querySelector("#content").innerHTML='<div id="movementTable"><table><tbody><tr data-kind="movement" data-id="9901"><td>9901</td><td>Fixture Product</td><td>Giri\u015f</td></tr></tbody></table></div>';
      const row=document.querySelector('#movementTable tr[data-kind="movement"]'),event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:400});row.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu");
      return {prevented:event.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-stock-movement-context]"),button=>button.dataset.stockMovementContext),separators:menu.querySelectorAll(".context-menu-separator").length};
    })()`);
    if (!movementMenu.open || !movementMenu.prevented || JSON.stringify(movementMenu.actions) !== JSON.stringify(["movement-export","movement-pdf","movement-print","movement-delete"]) || movementMenu.separators !== 1) throw new Error(`Stock movement context menu mismatch: ${JSON.stringify(movementMenu)}`);
    const movementShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "stock-movement-context-menu-headless.png"), Buffer.from(movementShot.data, "base64"));
    const movementActions = await evaluate(`(async () => {
      const originalFetch=window.fetch,originalPrint=window.print,originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL,originalAnchorClick=HTMLAnchorElement.prototype.click;
      let printCalls=0,downloadName="";
      window.fetch=async url=>{window.__movementPdfRequest=String(url);return new Response("%PDF-movement-audit",{status:200,headers:{"Content-Type":"application/pdf"}})};
      URL.createObjectURL=()=>"blob:movement-audit";URL.revokeObjectURL=()=>{};HTMLAnchorElement.prototype.click=function(){downloadName=this.download};window.print=()=>{printCalls++};
      document.querySelector('#contextMenu [data-stock-movement-context="movement-pdf"]').click();
      await new Promise(resolve=>setTimeout(resolve,40));
      const pdf={request:window.__movementPdfRequest,download:downloadName,printCalls};
      contextAction("movement","9901","movement-print");
      const print={calls:printCalls};
      window.fetch=originalFetch;window.print=originalPrint;URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;HTMLAnchorElement.prototype.click=originalAnchorClick;
      return {pdf,print};
    })()`);
    if (movementActions.pdf.request !== "/api/desktop/stock/movements/export/pdf?page=1&search=&type=" || !/^stok_hareketleri_.*\.pdf$/.test(movementActions.pdf.download) || movementActions.pdf.printCalls !== 0 || movementActions.print.calls !== 1 || exceptions.length) throw new Error(`Stock movement context action mismatch: ${JSON.stringify({ movementMenu, movementActions, exceptions })}`);
    const financeMenu = await evaluate(`(() => {
      page="finance";document.body.dataset.page="finance";db.settings.contextMenu=true;desktopSettings.rc_accounting="1";
      showContext({preventDefault(){},clientX:520,clientY:420,currentTarget:document.querySelector("#content")},"finance","finance-audit-row");
      const menu=document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-context-action]"),button=>button.dataset.contextAction)};
    })()`);
    if (!financeMenu.open || JSON.stringify(financeMenu.actions) !== JSON.stringify(["finance-detail","finance-export","finance-pdf","finance-print"])) throw new Error(`Finance context menu mismatch: ${JSON.stringify(financeMenu)}`);
    const financeShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "finance-context-menu-headless.png"), Buffer.from(financeShot.data, "base64"));
    const financeActions = await evaluate(`(async () => {
      const originalFetch=window.fetch,originalPrint=window.print,originalCreate=URL.createObjectURL,originalRevoke=URL.revokeObjectURL,originalAnchorClick=HTMLAnchorElement.prototype.click;
      let requestUrl="",requestBody=null,printCalls=0,downloadName="";
      window.fetch=async(url,options={})=>{requestUrl=String(url);requestBody=JSON.parse(options.body);return new Response("%PDF-finance-audit",{status:200,headers:{"Content-Type":"application/pdf"}})};
      URL.createObjectURL=()=>"blob:finance-audit";URL.revokeObjectURL=()=>{};HTMLAnchorElement.prototype.click=function(){downloadName=this.download};window.print=()=>{printCalls++};
      document.querySelector('#contextMenu [data-context-action="finance-pdf"]').click();
      await new Promise(resolve=>setTimeout(resolve,40));
      const pdf={requestUrl,requestBody,download:downloadName,printCalls};
      contextAction("finance","finance-audit-row","finance-print");
      const print={calls:printCalls};
      window.fetch=originalFetch;window.print=originalPrint;URL.createObjectURL=originalCreate;URL.revokeObjectURL=originalRevoke;HTMLAnchorElement.prototype.click=originalAnchorClick;
      return {pdf,print};
    })()`);
    if (financeActions.pdf.requestUrl !== "/api/desktop/accounting/ledger/export/pdf" || !/^cari-hareketler-.*\.pdf$/.test(financeActions.pdf.download) || financeActions.pdf.printCalls !== 0 || financeActions.print.calls !== 1 || exceptions.length) throw new Error(`Finance context action mismatch: ${JSON.stringify({ financeMenu, financeActions, exceptions })}`);
    console.log(JSON.stringify({ regular: result, ...outcome, movementMenu, movementActions, financeMenu, financeActions, browserExceptions: exceptions.length, headless: true }));
  } finally {
    try { socket?.close(); } catch (_) {}
    try { browser.kill(); } catch (_) {}
  }
}

run().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });
