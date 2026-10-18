const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || (9600 + process.pid % 300));
const output = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright/sales-bulk-f2-headless.png");
const composerOutput = path.resolve("output/playwright/sales-detailed-line-composer-headless.png");
const profile = path.resolve(`output/playwright/sales-bulk-f2-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  const browser = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose the project page.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") {
        exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown browser exception");
      }
      if (!message.id || !pending.has(message.id)) return;
      const entry = pending.get(message.id);
      pending.delete(message.id);
      message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    await send("Runtime.enable");
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text || "Browser evaluation failed");
      return response.result.value;
    };
    await delay(1800);
    await evaluate('apiFetch=async path=>path.includes("/services")?{rows:[{id:9,name:"Audit Service",price:125,code:"SVC-09"}]}:{rows:[]}');
    const catalog = JSON.parse(await evaluate('(db.stock=[{id:"AUDIT-1",name:"Audit kamera kit",code:"A1",qty:2,sell:10,currency:"TRY",category:"Audit"},{id:"AUDIT-0",name:"Out of stock",code:"A0",qty:0,sell:11,currency:"TRY",category:"Audit"}],page="sales",render(),JSON.stringify({outOfStockVisible:document.querySelector("#salesProducts")?.innerText.includes("Out of stock"),outOfStockDisabled:document.querySelector("[data-id=\\"AUDIT-0\\"]")?.disabled,filterPressed:document.querySelector("[data-sales-filter]")?.getAttribute("aria-pressed")}))'));
    if (!catalog.outOfStockVisible || !catalog.outOfStockDisabled || catalog.filterPressed !== "false") throw new Error(`Default catalog filter mismatch: ${JSON.stringify(catalog)}`);
    const transactionDate = await evaluate('(input=>{input.value="2026-11-03";input.dispatchEvent(new Event("change",{bubbles:true}));return salesDraft.date})(document.querySelector("#salesDate"))');
    if (transactionDate !== "2026-11-03") throw new Error(`Sales transaction date was not retained: ${transactionDate}`);
    await evaluate('document.querySelector("[data-sales-filter]").click()');
    const filtered = JSON.parse(await evaluate('JSON.stringify({outOfStockVisible:document.querySelector("#salesProducts")?.innerText.includes("Out of stock"),filterPressed:document.querySelector("[data-sales-filter]")?.getAttribute("aria-pressed")})'));
    if (filtered.outOfStockVisible || filtered.filterPressed !== "true") throw new Error(`Stock-only filter mismatch: ${JSON.stringify(filtered)}`);
    const toolbar = JSON.parse(await evaluate('JSON.stringify({page:document.body.dataset.page,button:!!document.querySelector("[data-sales-bulk-select]"),shortcuts:[...document.querySelectorAll(".sales-actions kbd")].map(item=>item.textContent)})'));
    if (toolbar.page !== "sales" || !toolbar.button || !["F5", "F8", "F10", "F12"].every(key => toolbar.shortcuts.includes(key))) throw new Error(`Sales toolbar check failed: ${JSON.stringify(toolbar)}`);
    await evaluate('document.body.dispatchEvent(new KeyboardEvent("keydown",{key:"F2",bubbles:true,cancelable:true}))');
    await delay(500);
    const initial = JSON.parse(await evaluate('JSON.stringify({open:document.querySelector("#appDialog")?.open,title:document.querySelector("#appDialog")?.innerText.includes("Toplu"),modes:[...document.querySelectorAll("[data-bulk-mode]")].map(button=>button.dataset.bulkMode)})'));
    if (!initial.open || !initial.title || initial.modes.join(",") !== "part,service") throw new Error(`F2 did not open the bulk selector: ${JSON.stringify(initial)}`);
    await evaluate('document.querySelector("[data-bulk-mode=service]").click()');
    const service = JSON.parse(await evaluate('JSON.stringify({mode:document.querySelector("[data-bulk-mode].active")?.dataset.bulkMode,row:document.querySelector("#bulkSalesRows")?.innerText.includes("Audit Service")})'));
    if (service.mode !== "service" || !service.row) throw new Error(`Service mode check failed: ${JSON.stringify(service)}`);
    const shortcuts = JSON.parse(await evaluate('(window.__shortcutCalls=[],handleAction=action=>window.__shortcutCalls.push(action),["F5","F8","F10","F12"].forEach(key=>document.body.dispatchEvent(new KeyboardEvent("keydown",{key,bubbles:true,cancelable:true}))),JSON.stringify(window.__shortcutCalls))'));
    if (shortcuts.join(",") !== "create-proforma,save-service,create-proforma,pay-save") throw new Error(`Sales shortcut dispatch failed: ${JSON.stringify(shortcuts)}`);
    await evaluate('document.querySelector("#appDialog").close()');
    await evaluate('document.querySelector("[data-sales-line-toggle]").click()');
    await delay(150);
    await evaluate('(el=>{el.value="AUDIT-1";el.dispatchEvent(new Event("change",{bubbles:true}))})(document.querySelector("#salesLineProduct"))');
    await evaluate('(controls=>{controls[0].value="2";controls[1].value="7.25";controls[2].value="Camera install note";controls.forEach(el=>el.dispatchEvent(new Event("input",{bubbles:true}))) })(["#salesLineQty","#salesLinePrice","#salesLineDescription"].map(selector=>document.querySelector(selector)))');
    const stockTotal = await evaluate('document.querySelector("#salesLineTotal")?.textContent');
    if (!stockTotal) throw new Error("Detailed stock composer did not calculate its line total.");
    await evaluate('document.querySelector("[data-sales-line-add]").click()');
    const stockLine = JSON.parse(await evaluate('JSON.stringify((()=>{const line=salesCart.find(item=>String(item.productId)==="AUDIT-1");return{qty:line?.qty,price:line?.unitPriceTry,description:line?.description}})())'));
    if (stockLine.qty !== 2 || stockLine.price !== 7.25 || stockLine.description !== "Camera install note") throw new Error(`Detailed stock line mismatch: ${JSON.stringify(stockLine)}`);
    await evaluate('(el=>{el.value="service";el.dispatchEvent(new Event("change",{bubbles:true}))})(document.querySelector("#salesLineType"))');
    await delay(150);
    await evaluate('(el=>{el.value="Audit Service";el.dispatchEvent(new Event("input",{bubbles:true}))})(document.querySelector("#salesLineService"))');
    await evaluate('(controls=>{controls[0].value="3";controls[1].value="125";controls[2].value="Service note";controls.forEach(el=>el.dispatchEvent(new Event("input",{bubbles:true}))) })(["#salesLineQty","#salesLinePrice","#salesLineDescription"].map(selector=>document.querySelector(selector)))');
    await evaluate('document.querySelector("[data-sales-line-add]").click()');
    const serviceLine = JSON.parse(await evaluate('JSON.stringify((()=>{const line=salesCart.find(item=>item.type==="service");return{qty:line?.qty,price:line?.unitPriceTry,serviceId:line?.serviceId,name:line?.name,description:line?.description}})())'));
    if (serviceLine.qty !== 3 || serviceLine.price !== 125 || serviceLine.serviceId !== 9 || serviceLine.name !== "Audit Service" || serviceLine.description !== "Service note") throw new Error(`Detailed service line mismatch: ${JSON.stringify(serviceLine)}`);
    const cartContext = await evaluate(`(async()=>{
      db.settings.contextMenu=true;salesCurrency="TRY";
      const openAction=(itemType,action)=>{const index=salesCart.findIndex(item=>item.type===itemType||itemType==="part"&&item.type!=="service");const row=document.querySelector('[data-kind="sales-cart"][data-id="'+index+'"]');if(!row)throw Error('Cart row missing: '+itemType);row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:120,clientY:120}));const button=document.querySelector('#contextMenu [data-context-action="'+action+'"]');if(!button)throw Error('Context action missing: '+action);button.click();return index};
      const closeWithValue=async(selector,value)=>{await new Promise(resolve=>setTimeout(resolve,60));const input=document.querySelector(selector);if(!input)throw Error('Dialog input missing: '+selector);input.value=value;document.querySelector('#dialogSubmit').click();await new Promise(resolve=>setTimeout(resolve,100));};
      let serviceIndex=openAction('service','sales-cart-quantity');const quantityInput=document.querySelector('#dialogBody input[name="quantity"]');const serviceQuantityMode={type:quantityInput?.type,inputMode:quantityInput?.inputMode};await closeWithValue('#dialogBody input[name="quantity"]','1,5');
      openAction('service','sales-cart-price');await closeWithValue('#dialogBody input[name="unit_price"]','150,75');
      openAction('service','sales-cart-description');await closeWithValue('#dialogBody textarea[name="description"]','Edited service note');
      openAction('service','sales-cart-copy');const copiedCount=salesCart.filter(item=>item.type==='service').length;const duplicateIndex=salesCart.findLastIndex(item=>item.type==='service');const duplicateRow=document.querySelector('[data-kind="sales-cart"][data-id="'+duplicateIndex+'"]');duplicateRow.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:120,clientY:120}));document.querySelector('#contextMenu [data-context-action="sales-cart-remove"]').click();
      const partIndex=openAction('part','sales-cart-quantity'),partInput=document.querySelector('#dialogBody input[name="quantity"]'),partRange={min:partInput?.min,max:partInput?.max,step:partInput?.step};await closeWithValue('#dialogBody input[name="quantity"]','5');const editedPartQuantity=salesCart[partIndex].qty;salesCart[partIndex].qty=2;render();
      const serviceLine=salesCart.find(item=>item.type==='service');return{serviceQuantityMode,serviceQuantity:serviceLine?.qty,servicePrice:serviceLine?.unitPriceTry,servicePriceMirror:serviceLine?.priceTry,serviceDescription:serviceLine?.description,copiedCount,serviceCountAfterRemove:salesCart.filter(item=>item.type==='service').length,editedPartQuantity,partRange};
    })()`);
    if(cartContext.serviceQuantityMode.type!=="text"||cartContext.serviceQuantityMode.inputMode!=="decimal"||cartContext.serviceQuantity!==1.5||cartContext.servicePrice!==150.75||cartContext.servicePriceMirror!==150.75||cartContext.serviceDescription!=="Edited service note"||cartContext.copiedCount!==2||cartContext.serviceCountAfterRemove!==1||cartContext.editedPartQuantity!==5||cartContext.partRange.max!=="999999999"||cartContext.partRange.step!=="1")throw new Error(`Cart context parity mismatch: ${JSON.stringify(cartContext)}`);
    await evaluate('(async()=>{window.__dateAudit={};db.customers=[{id:501,desktopId:501,name:"Date Audit Customer",company:"Date Audit Customer",quotes:[]}];salesCustomer=501;salesCurrency="TRY";salesCart=[{type:"service",serviceId:9,name:"Audit Service",priceTry:150.75,unitPriceTry:150.75,qty:1.5,description:"Audit"}];apiFetch=async(path,options)=>{window.__dateAudit.calls=(window.__dateAudit.calls||[]).concat(path);if(path.includes("/sales/commit")){window.__dateAudit.payload=JSON.parse(options.body);return{offer_id:51,offer_no:"AUDIT-DATE-51",transaction_date:window.__dateAudit.transaction_date,currency:"TRY",currency_symbol:"\\u20ba",exchange_rate:1,subtotal:226.125,discount:0,discount_percent:0,discount_try:0,vat_amount:0,total:226.125,subtotal_try:226.125,vat_amount_try:0,total_try:226.125}};return{}};hydrateDesktop=async()=>{};render=()=>{};toast=message=>{window.__dateAudit.toast=message};openProformaDocument=()=>{};await runSales("proforma")})()');
    const commitDate = JSON.parse(await evaluate('JSON.stringify(window.__dateAudit)'));
    if (commitDate.payload?.transaction_date !== "2026-11-03" || commitDate.payload?.lines?.[0]?.qty !== 1.5 || commitDate.payload?.lines?.[0]?.unit_price !== 150.75) throw new Error(`Selected transaction date or fractional service values were not sent to the commit API: ${JSON.stringify(commitDate)}`);
    await evaluate('document.querySelectorAll(".auth-root,.auth-shell").forEach(node=>node.remove());document.body.classList.remove("auth-active")');
    const composerShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(composerOutput, Buffer.from(composerShot.data, "base64"));
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(output, Buffer.from(screenshot.data, "base64"));
    if (exceptions.length) throw new Error(`Sales workflow browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(`${JSON.stringify({ result: "PASS", exceptions, catalog, filtered, transactionDate, commitDate: commitDate.payload?.transaction_date, committedServiceLine: commitDate.payload?.lines?.[0], toolbar, initial, service, shortcuts, stockLine, serviceLine, cartContext, composerScreenshot: composerOutput, screenshot: output })}\n`);
  } finally {
    try { socket?.close(); } catch (_) {}
    if (browser.pid) spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });





