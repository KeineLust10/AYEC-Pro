const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const requestedPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 0);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `customer-vehicle-manifest-profile-${process.pid}`);
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
      ready = await evaluate("document.readyState === 'complete' && typeof db === 'object' && typeof openManifestDialog === 'function' && typeof window.openAutomotiveVehicleShortcut === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("The app and vehicle editor scripts did not become ready.");
    const stockAdjustment = await evaluate(`(() => {
      window.__adjustOriginalApi=apiFetch;window.__adjustOriginalStock=db.stock;window.__adjustOriginalMovements=db.movements;
      window.__stockAdjustWrites=[];
      apiFetch=async(url,options={})=>{window.__stockAdjustWrites.push({url:String(url),payload:options.body?JSON.parse(options.body):null});return {movement_id:992,delta:-2,finance_id:null}};
      db.stock=[{id:991,name:"Audit Adjust Part",qty:5,min:1,buy:4,currency:"TRY"}];
      movementDialog(db.stock[0]);
      const form=document.querySelector("#dialogForm");
      if(!form?.querySelector('[name="type"]')||!form.querySelector('[name="qty"]')||!form.querySelector('[name="ref"]'))throw new Error("Stock movement dialog is missing the integer adjustment controls.");
      form.querySelector('[name="type"]').value="Çıkış";form.querySelector('[name="qty"]').value="2";form.querySelector('[name="ref"]').value="Audit adjustment";
      return {title:document.querySelector("#dialogTitle")?.textContent||"",fields:3};
    })()`);
    const stockAdjustmentShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const stockAdjustmentPath = path.join(outDir, "stock-adjustment-dialog-headless.png");
    fs.writeFileSync(stockAdjustmentPath, Buffer.from(stockAdjustmentShot.data, "base64"));
    const stockAdjustmentResult = await evaluate(`(async()=>{document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,180));const result={writes:window.__stockAdjustWrites,qty:db.stock[0]?.qty,closed:!document.querySelector("#appDialog")?.open};apiFetch=window.__adjustOriginalApi;db.stock=window.__adjustOriginalStock;db.movements=window.__adjustOriginalMovements;return result})()`);
    if(!stockAdjustmentResult.closed||stockAdjustmentResult.qty!==3||stockAdjustmentResult.writes.length!==1||stockAdjustmentResult.writes[0].url!=="/api/desktop/stock/adjust"||stockAdjustmentResult.writes[0].payload.id!==991||stockAdjustmentResult.writes[0].payload.delta!==-2)throw new Error(`Stock adjustment did not persist the expected delta: ${JSON.stringify(stockAdjustmentResult)}`);
    const quickClose = await evaluate(`(() => {
      window.__quickCloseOriginalApi=apiFetch;
      apiFetch=async url=>String(url).includes("security-settings")?{tech_lock_active:false}:{};
      currentSector="teknik_servis";
      db.customers=[{id:721,name:"Audit Quick Close Customer",phone:"5550000000",services:[{id:722,no:"TS-QC-722",device:"Laptop",status:"Bekliyor",note:""}]}];
      quickCloseServiceFromWeb("TS-QC-722");
      const body=document.querySelector("#dialogBody")?.innerText||"";
      if(!body.includes("TS-QC-722")||!body.includes("teknisyen panelinde tamamlan"))throw new Error("Quick-close confirmation did not preserve the desktop warning.");
      return {title:document.querySelector("#dialogTitle")?.textContent||"",button:document.querySelector("#dialogSubmit")?.textContent||""};
    })()`);
    const quickCloseShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const quickClosePath = path.join(outDir, "service-quick-close-confirmation-headless.png");
    fs.writeFileSync(quickClosePath, Buffer.from(quickCloseShot.data, "base64"));
    const quickCloseOpened = await evaluate(`(async()=>{document.querySelector("#dialogSubmit").click();await new Promise(resolve=>setTimeout(resolve,300));const form=document.querySelector("#dialogForm");const result={title:document.querySelector("#dialogTitle")?.textContent||"",open:document.querySelector("#appDialog")?.open,hasStatus:!!form?.querySelector('[name="status"]'),hasPayment:!!document.querySelector("#dialogBody")?.innerText.includes("Tahsilat Tutarı")};document.querySelector("#dialogCancel")?.click();apiFetch=window.__quickCloseOriginalApi;return result})()`);
    if(!quickCloseOpened.open||!quickCloseOpened.hasStatus||!quickCloseOpened.hasPayment)throw new Error(`Quick-close did not open the technician payment workflow: ${JSON.stringify(quickCloseOpened)}`);
    const serviceDelete = await evaluate(`(() => {
      window.__auditOriginalApi=apiFetch;window.__auditOriginalHydrate=hydrateDesktop;
      window.__serviceDeleteWrites=[];
      apiFetch=async(url,options={})=>{window.__serviceDeleteWrites.push({url:String(url),payload:options.body?JSON.parse(options.body):null});return {ok:true}};
      hydrateDesktop=async()=>({});
      currentSector="teknik_servis";
      db.customers=[{id:715,name:"Audit Delete Customer",phone:"5550000000",services:[{id:716,no:"TS-DEL-716",device:"Laptop",status:"Bekliyor",note:""}]}];
      deleteServiceFromWeb("TS-DEL-716");
      const body=document.querySelector("#dialogBody")?.innerText||"";
      if(!body.includes("TS-DEL-716")||!body.includes("geri al\u0131namaz"))throw new Error("Service delete confirmation did not explain the delete.");
      return {title:document.querySelector("#dialogTitle")?.textContent||"",button:document.querySelector("#dialogSubmit")?.textContent||""};
    })()`);
    const serviceDeleteShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const serviceDeletePath = path.join(outDir, "service-delete-confirmation-headless.png");
    fs.writeFileSync(serviceDeletePath, Buffer.from(serviceDeleteShot.data, "base64"));
    const serviceDeleteResult = await evaluate(`(async()=>{document.querySelector("#dialogSubmit").click();await new Promise(resolve=>setTimeout(resolve,150));const result={closed:!document.querySelector("#appDialog")?.open,writes:window.__serviceDeleteWrites};apiFetch=window.__auditOriginalApi;hydrateDesktop=window.__auditOriginalHydrate;return result})()`);
    if(!serviceDeleteResult.closed||serviceDeleteResult.writes.length!==1||serviceDeleteResult.writes[0].url!=="/api/desktop/table/devices"||serviceDeleteResult.writes[0].payload.id!==716||serviceDeleteResult.writes[0].payload._action!=="delete")throw new Error(`Service delete did not send the expected soft-delete request: ${JSON.stringify(serviceDeleteResult)}`);
    const stockDelete = await evaluate(`(() => {
      window.__auditOriginalStock = db.stock;
      const product={id:990,name:"Audit Protected Stock",qty:3,min:1};
      db.stock=[product];
      deleteProduct(product);
      const input=document.querySelector('#dialogBody input[name="password"]');
      if(!input||input.type!=="password"||!input.required) throw new Error("Stock deletion is missing password verification.");
      return {title:document.querySelector("#dialogTitle")?.textContent||"",label:document.querySelector("#dialogBody label")?.textContent||"",button:document.querySelector("#dialogSubmit")?.textContent||""};
    })()`);
    const stockDeleteShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const stockDeletePath = path.join(outDir, "stock-delete-security-headless.png");
    fs.writeFileSync(stockDeletePath, Buffer.from(stockDeleteShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); db.stock=window.__auditOriginalStock; return true; })()`);
    const userSwitch = await evaluate(`(() => {
      openManifestDialog({key:"user_switch_dialog"});
      const body=document.querySelector("#dialogBody"),submit=document.querySelector("#dialogSubmit");
      if(!body?.innerText.includes("Devam etmek istiyor musunuz?")||!submit) throw new Error("User switch confirmation was not rendered.");
      const logout=document.querySelector("#logoutBtn");window.__userSwitchLogout=false;logout.onclick=()=>{window.__userSwitchLogout=true};
      return {title:document.querySelector("#dialogTitle")?.textContent||"",cancel:document.querySelector("#dialogCancel")?.textContent||"",confirm:submit.textContent};
    })()`);
    const userSwitchShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const userSwitchPath = path.join(outDir, "user-switch-manifest-headless.png");
    fs.writeFileSync(userSwitchPath, Buffer.from(userSwitchShot.data, "base64"));
    await evaluate(`(async()=>{document.querySelector("#dialogSubmit").click();await new Promise(resolve=>setTimeout(resolve,150));if(!window.__userSwitchLogout)throw new Error("User switch did not enter the existing logout flow.");return true})()`);
    const customerNotesDelete = await evaluate(`(async()=>{
      document.querySelector("#authRoot")?.remove();document.body.classList.remove("auth-active");
      window.__noteRows=[{id:601,customer_id:712,type:"Genel Not",title:"Audit note",content:"Delete audit note",created_at:"2026-01-01T00:00:00"}];
      window.__noteWrites=[];
      apiFetch=async(url,options={})=>{
        if(!options.method)return {rows:window.__noteRows};
        const payload=options.body?JSON.parse(options.body):null;
        window.__noteWrites.push({url:String(url),payload});
        if(payload?._action==="delete")window.__noteRows=window.__noteRows.filter(note=>String(note.id)!==String(payload.id));
        return {ok:true};
      };
      const customer={id:712,name:"Audit Notes Customer",note_history:[]};
      openCustomerNotes(customer);
      await new Promise(resolve=>setTimeout(resolve,80));
      const deleteButton=document.querySelector("#customerNoteDelete");
      if(!deleteButton||!document.querySelector("[data-cnote-index]"))throw new Error("Customer note editor or saved note did not render.");
      deleteButton.click();
      await new Promise(resolve=>setTimeout(resolve,120));
      if(!document.querySelector("#dialogTitle")?.textContent.includes("Notunu Sil"))throw new Error("Customer note deletion confirmation did not render.");
      return {title:document.querySelector("#dialogTitle")?.textContent||"",button:document.querySelector("#dialogSubmit")?.textContent||""};
    })()`);
    const customerNotesDeleteShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const customerNotesDeletePath = path.join(outDir,"customer-notes-delete-headless.png");
    fs.writeFileSync(customerNotesDeletePath,Buffer.from(customerNotesDeleteShot.data,"base64"));
    const customerNotesDeleted = await evaluate(`(async()=>{
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve=>setTimeout(resolve,220));
      return {writes:window.__noteWrites,remaining:window.__noteRows.length,dialogTitle:document.querySelector("#dialogTitle")?.textContent||""};
    })()`);
    if(customerNotesDelete.button!=="Notu Sil"||customerNotesDeleted.writes.length!==1||customerNotesDeleted.writes[0].url!=="/api/desktop/table/customer_notes"||customerNotesDeleted.writes[0].payload._action!=="delete"||customerNotesDeleted.remaining!==0||customerNotesDeleted.dialogTitle!=="M\u00fc\u015fteri Notlar\u0131"||exceptions.length)throw new Error(JSON.stringify({customerNotesDelete,customerNotesDeleted,exceptions}));
    const criticalAlert = await evaluate(`(() => {
      window.__auditOriginalStock = db.stock;
      db.stock = [{id:991,name:"Audit Critical Part",qty:0,min:2}];
      openManifestDialog({key:"critical_alert_dialog"});
      const body=document.querySelector("#dialogBody");
      if(!body?.innerText.includes("Audit Critical Part")||!body.innerText.includes("Kritik seviye: 2")) throw new Error("Critical alert did not render low-stock details.");
      return {title:document.querySelector("#dialogTitle")?.textContent||"",card:body.querySelectorAll(".critical-alert-card").length,closeHidden:document.querySelector("#dialogCancel")?.hidden===true};
    })()`);
    const criticalAlertShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const criticalAlertPath = path.join(outDir, "critical-alert-manifest-headless.png");
    fs.writeFileSync(criticalAlertPath, Buffer.from(criticalAlertShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogSubmit")?.click(); db.stock=window.__auditOriginalStock; return true; })()`);
    const technicianLogin = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      currentSector = "teknik_servis";
      db.customers = [{id:713,name:"Audit Technician Customer",phone:"5550000000",services:[{id:714,no:"TS-AUDIT-714",device:"Laptop",status:"Bekliyor",note:""}]}];
      apiFetch = async url => String(url).includes("security-settings") ? {tech_lock_active:false} : {};
      openManifestDialog({key:"technician_login_dialog"});
      const form=document.querySelector("#dialogForm");
      const input=form?.querySelector('[name="tracking_no"]');
      if(!form||!input) throw new Error("Technician tracking picker was not opened.");
      input.value="714";
      return {picker:true,heading:document.querySelector("#dialogTitle")?.textContent||""};
    })()`);
    const technicianLoginShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const technicianLoginPath = path.join(outDir, "technician-login-manifest-headless.png");
    fs.writeFileSync(technicianLoginPath, Buffer.from(technicianLoginShot.data, "base64"));
    const technicianOpened = await evaluate(`(async()=>{document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,350));const form=document.querySelector("#dialogForm");return {title:document.querySelector("#dialogTitle")?.textContent||"",open:document.querySelector("#appDialog")?.open,hasStatus:!!form?.querySelector('[name="status"]'),hasNote:!!form?.querySelector("textarea"),body:document.querySelector("#dialogBody")?.innerText||""}})()`);
    if(!technicianOpened.hasStatus||!technicianOpened.hasNote) throw new Error(`Technician detail form did not open: ${JSON.stringify(technicianOpened)}`);
    const technicianFormShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const technicianFormPath = path.join(outDir, "technician-login-service-form-headless.png");
    fs.writeFileSync(technicianFormPath, Buffer.from(technicianFormShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); openManifestDialog({key:"modern_manual_product_dialog"}); const input=document.querySelector('#dialogBody input[name="tracking_no"]'); if(!input) throw new Error("Manual product service picker was not opened."); input.value="714"; return true; })()`);
    const manualProduct = await evaluate(`(async()=>{document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,450));const details=document.querySelector("#dialogBody .used-part-manual");const name=document.querySelector("#manualUsedPartName"),price=document.querySelector("#manualUsedPartPrice");return {title:document.querySelector("#dialogTitle")?.textContent||"",open:document.querySelector("#appDialog")?.open,details:!!details,detailsOpen:!!details?.open,name:!!name,price:!!price,body:document.querySelector("#dialogBody")?.innerText||""}})()`);
    if(!manualProduct.open||!manualProduct.detailsOpen||!manualProduct.name||!manualProduct.price) throw new Error(`Manual product editor did not open: ${JSON.stringify(manualProduct)}`);
    const manualProductShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const manualProductPath = path.join(outDir, "manual-product-service-flow-headless.png");
    fs.writeFileSync(manualProductPath, Buffer.from(manualProductShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); return true; })()`);
    const customerProfile = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      currentSector = "otomotiv";
      openManifestDialog({key:"automotive_customer_dialog"});
      const automotiveForm = document.querySelector("#dialogForm");
      const automotiveFields = ["vehicle_plate","vehicle_vin","vehicle_brand","vehicle_model","vehicle_year","vehicle_engine"];
      if (!automotiveForm || automotiveFields.some(name => !automotiveForm.querySelector('[name="'+name+'"]'))) throw new Error("Automotive customer profile is missing a desktop field.");
      return {automotive:true,fields:automotiveFields.length};
    })()`);
    const customerProfileShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const customerProfilePath = path.join(outDir, "automotive-customer-profile-headless.png");
    fs.writeFileSync(customerProfilePath, Buffer.from(customerProfileShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); currentSector="teknik_servis"; openManifestDialog({key:"technical_service_customer_dialog"}); const form=document.querySelector("#dialogForm"); const fields=["device_type","device_brand","device_model"]; if(!form||fields.some(name=>!form.querySelector('[name="'+name+'"]'))) throw new Error("Technical service customer profile is missing a desktop field."); return true; })()`);
    const technicalCustomerShot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:false});
    const technicalCustomerPath = path.join(outDir, "technical-customer-profile-headless.png");
    fs.writeFileSync(technicalCustomerPath, Buffer.from(technicalCustomerShot.data, "base64"));
    await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); return true; })()`);
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      currentSector = "otomotiv";
      db.customers = [{id:712,name:"Audit Customer",phone:"5550000000",services:[]}];
      const writes = [];
      window.__customerVehicleWrites = writes;
      apiFetch = async (url, options = {}) => {
        writes.push({url:String(url), payload:options.body ? JSON.parse(options.body) : null});
        return {id:881};
      };
      customer360 = () => {};
      openManifestDialog({key:"customer_vehicle_dialog"});
      await new Promise(resolve => setTimeout(resolve, 50));
      const picker = document.querySelector("#dialogForm");
      const customer = picker?.querySelector('[name="customerId"]');
      if (!picker || !customer) throw new Error("Customer picker was not opened.");
      customer.value = "712";
      picker.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 120));
      const form = document.querySelector("#dialogForm");
      const fields = ["plate","brand","model","year","vehicle_type","engine_type","fuel_type","last_known_odometer","notes"];
      if (!form || fields.some(name => !form.querySelector('[name="'+name+'"]'))) throw new Error("Vehicle editor is missing a desktop field.");
      const values = {plate:"10 AUDIT 01",brand:"Ford",model:"Focus",year:"2022",vehicle_type:"Binek",engine_type:"Benzinli",fuel_type:"Benzin",last_known_odometer:"12345",notes:"manifest audit"};
      for (const [name,value] of Object.entries(values)) { const input=form.querySelector('[name="'+name+'"]'); input.value=value; input.dispatchEvent(new Event("input",{bubbles:true})); }
      return {pickerOpened:true,editorOpened:true,fields:fields.length};
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const screenshotPath = path.join(outDir, "customer-vehicle-manifest-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const saved = await evaluate(`(async () => { document.querySelector("#dialogForm").requestSubmit(); await new Promise(resolve => setTimeout(resolve, 120)); return {dialogClosed:!document.querySelector("#appDialog")?.open,writes:window.__customerVehicleWrites}; })()`);
    const write = saved.writes[0];
    if (!customerProfile.automotive || customerProfile.fields !== 6 || !result.pickerOpened || !result.editorOpened || result.fields !== 9 || saved.writes.length !== 1 || !write.url.includes("/api/desktop/table/customer_vehicles") || write.payload.customer_id !== 712 || write.payload.plate !== "10 AUDIT 01" || write.payload.engine_type !== "Benzinli" || write.payload.notes !== "manifest audit" || !saved.dialogClosed || exceptions.length) throw new Error(JSON.stringify({ result, saved, exceptions }));
    process.stdout.write(`${JSON.stringify({ ...result, ...saved, stockAdjustment, stockAdjustmentResult, stockAdjustmentPath, quickClose, quickCloseOpened, quickClosePath, serviceDelete, serviceDeletePath, stockDelete, stockDeletePath, userSwitch, userSwitchPath, customerNotesDelete, customerNotesDeleted, customerNotesDeletePath, criticalAlert, criticalAlertPath, technicianLogin, technicianLoginPath, technicianFormPath, manualProductPath, customerProfile, customerProfilePath, technicalCustomerPath, exceptions, headless: true, screenshot: screenshotPath })}\n`);
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
