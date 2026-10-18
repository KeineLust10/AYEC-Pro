const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || (9600 + process.pid % 300));
const profile = path.resolve(`output/playwright/smart-home-sales-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  const browser = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1400,1000", baseUrl], { stdio: "ignore", windowsHide: true });
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
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
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
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text || "Browser evaluation failed");
      return response.result.value;
    };
    await delay(1800);
    const initial = JSON.parse(await evaluate('(db.stock=[{id:"SH-01",name:"Aqara Smart Hub",code:"AQ-01",qty:6,price:125.5,currency:"EUR",category:"Smart Home",brand:"Aqara"},{id:"SH-02",name:"Aqara Smart Plug",code:"AQ-02",qty:8,price:18,currency:"USD",category:"Smart Home",brand:"Aqara"}],db.customers=[{id:71,name:"Audit Customer",company_name:"Audit Ltd",contact_person:"Ada Audit",phone:"555-0100",email:"ada@example.test"}],document.querySelector("#authRoot")?.remove(),document.querySelector("#appShell")?.removeAttribute("inert"),document.body.classList.remove("auth-active"),page="sales",window.ayecSmartHomeSalesMode=false,render(),document.querySelector("[data-sales-workflow=smart-home]").click(),JSON.stringify({tab:document.querySelector("[data-sales-workflow=smart-home]")?.classList.contains("active"),mode:window.ayecSmartHomeSalesMode,form:!!document.querySelector("[data-smart-home-field=project_name]"),product:document.querySelector("[data-smart-home-product]")?.options.length}))'));
    if (!initial.tab || !initial.mode || !initial.form || initial.product !== 3) throw new Error(`Smart Home workflow tab failed: ${JSON.stringify(initial)}`);
    await evaluate('((field,value)=>{const node=document.querySelector(`[data-smart-home-field="${field}"]`);node.value=value;node.dispatchEvent(new Event("input",{bubbles:true}));node.dispatchEvent(new Event("change",{bubbles:true}))})("company_name","Audit Ltd")');
    await evaluate('((field,value)=>{const node=document.querySelector(`[data-smart-home-field="${field}"]`);node.value=value;node.dispatchEvent(new Event("input",{bubbles:true}));node.dispatchEvent(new Event("change",{bubbles:true}))})("project_name","Smart Building")');
    await evaluate('(node=>{node.value="SH-01";node.dispatchEvent(new Event("change",{bubbles:true}))})(document.querySelector("[data-smart-home-product]"))');
    await evaluate('(node=>{node.value="2"})(document.querySelector("[data-smart-home-add-qty]"))');
    await evaluate('(node=>{node.value="150,75"})(document.querySelector("[data-smart-home-add-price]"))');
    await evaluate('document.querySelector("[data-smart-home-add]").click()');
    const row = JSON.parse(await evaluate('JSON.stringify({count:document.querySelectorAll("[data-smart-home-qty]").length,qty:document.querySelector("[data-smart-home-qty]")?.value,price:document.querySelector("[data-smart-home-price]")?.value,total:document.querySelector(".smart-home-total")?.innerText})'));
    if (row.count !== 1 || row.qty !== "2" || row.price !== "150.75" || !row.total.includes("301,50")) throw new Error(`Smart Home offer row mismatch: ${JSON.stringify(row)}`);
    await evaluate('document.querySelector("[data-smart-home-open-pool]").click()');
    await evaluate('(node=>{node.checked=true;node.dispatchEvent(new Event("change",{bubbles:true}))})(document.querySelector("[data-smart-home-pool-row=SH-02] input[name=product_id]"))');
    await evaluate('(node=>{node.value="3";node.dispatchEvent(new Event("input",{bubbles:true}))})(document.querySelector("[data-smart-home-pool-row=SH-02] input[name=pool_qty]"))');
    await evaluate('(node=>{node.value="20,50";node.dispatchEvent(new Event("input",{bubbles:true}))})(document.querySelector("[data-smart-home-pool-row=SH-02] input[name=pool_price]"))');
    await evaluate('document.querySelector("#dialogSubmit").click()');
    await delay(80);
    const pool = JSON.parse(await evaluate('JSON.stringify({open:document.querySelector("#appDialog")?.open,count:document.querySelectorAll("[data-smart-home-qty]").length,qty:document.querySelectorAll("[data-smart-home-qty]")[1]?.value,price:document.querySelectorAll("[data-smart-home-price]")[1]?.value})'));
    if (pool.open || pool.count !== 2 || pool.qty !== "3" || pool.price !== "20.50") throw new Error(`Smart Home product pool failed: ${JSON.stringify(pool)}`);
    await evaluate('window.__smartHomeAudit={};salesManualRates={};exchangeRateState={};window.open=()=>{window.__smartHomeAudit.openCalls=(window.__smartHomeAudit.openCalls||0)+1;return{location:{replace:url=>window.__smartHomeAudit.popup=url},close:()=>{window.__smartHomeAudit.closed=true}}};URL.createObjectURL=()=>"blob:audit-pdf";URL.revokeObjectURL=()=>{};window.fetch=async(url,options)=>{window.__smartHomeAudit.url=url;window.__smartHomeAudit.payload=JSON.parse(options.body);return{ok:true,blob:async()=>new Blob(["pdf"])}};document.querySelector("[data-smart-home-generate]").click()');
    await delay(80);
    const missingRate = JSON.parse(await evaluate('JSON.stringify({opened:window.__smartHomeAudit.openCalls||0,requested:!!window.__smartHomeAudit.url})'));
    if (missingRate.opened || missingRate.requested) throw new Error(`Mixed currency proforma proceeded without exchange rates: ${JSON.stringify(missingRate)}`);
    await evaluate('salesManualRates={EUR:36,USD:33};document.querySelector("[data-smart-home-generate]").click()');
    await delay(100);
    const payload = JSON.parse(await evaluate('JSON.stringify(window.__smartHomeAudit)'));
    const item = payload.payload?.items?.[0];
    if (payload.url !== "/api/desktop/pc-builder/proforma.pdf" || payload.popup !== "blob:audit-pdf" || payload.payload?.template !== "bulut_deri" || payload.payload?.currency !== "EUR" || payload.payload?.project_name !== "Smart Building" || payload.payload?.items?.length !== 2 || item?.qty !== 2 || Math.abs(item.price - 150.75) > 0.001 || payload.payload?.items?.[1]?.qty !== 3 || Math.abs(payload.payload.items[1].price - (20.5 * 33 / 36)) > 0.001) throw new Error(`Smart Home PDF request mismatch: ${JSON.stringify(payload)}`);
    const tabLabel = await evaluate('document.querySelector("[data-sales-workflow=security]")?.textContent');
    if (!tabLabel) throw new Error("Shared Sales workflow tabs were not rendered.");
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await delay(80);
    const mobile = JSON.parse(await evaluate('JSON.stringify({width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,gridColumns:getComputedStyle(document.querySelector(".smart-home-sales-grid")).gridTemplateColumns,controlsColumns:getComputedStyle(document.querySelector(".smart-home-product-controls")).gridTemplateColumns})'));
    if (mobile.scrollWidth > mobile.width + 1 || !mobile.gridColumns || !mobile.controlsColumns) throw new Error(`Smart Home mobile layout overflowed: ${JSON.stringify(mobile)}`);
    await send("Emulation.clearDeviceMetricsOverride");
    const offers = JSON.parse(await evaluate('(async()=>{const rows=[{id:801,offer_no:"OF-801",created_at:"2026-10-01",customer_name:"Pending Customer",company_name:"Pending Ltd",total:100,currency_code:"USD",status:"pending"},{id:802,offer_no:"OF-802",created_at:"2026-10-02",customer_name:"Accepted Customer",company_name:"Accepted Ltd",total:240,currency_code:"EUR",status:"accepted"},{id:803,offer_no:"OF-803",created_at:"2026-10-03",customer_name:"Rejected Customer",company_name:"Rejected Ltd",total:50,currency_code:"TRY",status:"rejected"},{id:804,offer_no:"OF-804",created_at:"2026-10-04",customer_name:"Rejected 4",company_name:"Rejected Ltd",total:51,currency_code:"TRY",status:"rejected"},{id:805,offer_no:"OF-805",created_at:"2026-10-05",customer_name:"Rejected 5",company_name:"Rejected Ltd",total:52,currency_code:"TRY",status:"rejected"},{id:806,offer_no:"OF-806",created_at:"2026-10-06",customer_name:"Rejected 6",company_name:"Rejected Ltd",total:53,currency_code:"TRY",status:"rejected"},{id:807,offer_no:"OF-807",created_at:"2026-10-07",customer_name:"Rejected 7",company_name:"Rejected Ltd",total:54,currency_code:"TRY",status:"rejected"}];db.quotes=rows;apiFetch=async()=>({columns:["id","offer_no","created_at","customer_name","company_name","total","currency_code","status"],rows,count:7});page="offers";render();await new Promise(resolve=>setTimeout(resolve,80));const apply=(selector,value)=>{const node=document.querySelector(selector);node.value=value;node.dispatchEvent(new Event("change",{bubbles:true}))};apply("#offerStatusFilter","accepted");const accepted={visible:[...document.querySelectorAll("#genericHost [data-generic-row]")].filter(row=>!row.hidden).map(row=>row.dataset.genericRow),count:document.querySelector("#genericCount")?.textContent,total:document.querySelector("[data-offer-preview=total]")?.textContent};apply("#offerCurrencyFilter","USD");const none={visible:[...document.querySelectorAll("#genericHost [data-generic-row]")].filter(row=>!row.hidden).length,count:document.querySelector("#genericCount")?.textContent,total:document.querySelector("[data-offer-preview=total]")?.textContent};apply("#offerStatusFilter","pending");const pending={visible:[...document.querySelectorAll("#genericHost [data-generic-row]")].filter(row=>!row.hidden).map(row=>row.dataset.genericRow)};apply("#offerStatusFilter","all");apply("#offerCurrencyFilter","all");const firstPage={visible:[...document.querySelectorAll("#genericHost [data-generic-row]")].filter(row=>!row.hidden).length,label:document.querySelector("#offerReferencePageLabel")?.textContent};[...document.querySelectorAll("[data-offer-page]")].find(button=>button.dataset.offerPage==="1").click();const secondPage={visible:[...document.querySelectorAll("#genericHost [data-generic-row]")].filter(row=>!row.hidden).length,label:document.querySelector("#offerReferencePageLabel")?.textContent};return JSON.stringify({accepted,none,pending,firstPage,secondPage})})()'));
    if (offers.accepted.visible.join(",") !== "1" || !offers.accepted.count.includes("/ 1 Teklif") || !offers.accepted.total.includes("240") || offers.none.visible !== 0 || !offers.none.count.includes("/ 0 Teklif") || offers.none.total !== "-" || offers.pending.visible.join(",") !== "0" || offers.firstPage.visible !== 6 || offers.firstPage.label !== "Sayfa 1 / 2" || offers.secondPage.visible !== 1 || offers.secondPage.label !== "Sayfa 2 / 2") throw new Error(`Offer filters failed: ${JSON.stringify(offers)}`);
    const report = JSON.parse(await evaluate('JSON.stringify(buildOfferReportData([{status:"pending",created_at:"2026-10-10",company_name:"Alpha Ltd",customer_name:"A",created_by:"Staff A",total_try:100},{status:"accepted",created_at:"2026-10-11",company_name:"Alpha Ltd",customer_name:"A",created_by:"Staff B",total_try:200},{status:"rejected",created_at:"2025-10-31",company_name:"Legacy Ltd",customer_name:"Legacy",created_by:"Staff A",total_try:50},{status:"sent",created_at:"2026-10-12",company_name:"Sent Ltd",created_by:"Staff C",total_try:70},{status:"Onayland\\u0131",created_at:"2026-10-13",company_name:"Delta Ltd",created_by:"Staff A",total_try:80},{status:"Reddedildi",created_at:"2026-10-14",company_name:"Epsilon Ltd",created_by:"Staff E",total_try:20}],new Date("2026-10-17T00:00:00Z")))'));
    if (report.total !== 6 || report.pending !== 1 || report.accepted !== 2 || report.rejected !== 2 || report.amount !== 520 || report.months.length !== 1 || report.months[0][0] !== "2026-10" || report.months[0][1].count !== 5 || report.customers[0][0] !== "Alpha Ltd" || report.customers[0][1].count !== 2 || report.staff[0][0] !== "Staff A" || report.staff[0][1].count !== 3) throw new Error(`Offer report aggregation mismatch: ${JSON.stringify(report)}`);
    process.stdout.write(JSON.stringify({ screen: "smart-home", productCount: initial.product - 1, quantity: item.qty, price: item.price, currency: payload.payload.currency, pdfOpened: payload.popup === "blob:audit-pdf", exceptions: 0 }) + "\n");
  } finally {
    if (socket) socket.close();
    if (browser.pid) await new Promise(resolve => { const killer = spawn("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true }); killer.once("exit", resolve); });
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });

