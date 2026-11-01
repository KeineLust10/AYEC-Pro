const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const requestedPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 0);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `bank-card-manifest-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const freePort = () => new Promise((resolve, reject) => {
  const server = net.createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => { const address = server.address(); server.close(error => error ? reject(error) : resolve(address.port)); });
});

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const port = requestedPort || await freePort();
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1320,900", baseUrl], { stdio: "ignore", windowsHide: true });
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
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => { const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (result.exceptionDetails) throw new Error(result.exceptionDetails.text); return result.result.value; };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1320, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 80; attempt += 1) { ready = await evaluate("document.readyState === 'complete' && typeof db === 'object' && typeof openManifestDialog === 'function' && Boolean(document.querySelector('#authRoot')?.innerHTML)"); if (ready) break; await delay(200); }
    if (!ready) throw new Error("The web app did not become ready.");
    const opened = await evaluate(`(async()=>{
      document.querySelector("#authRoot")?.remove();document.body.classList.remove("auth-active");currentAuthUser={role:"admin"};
      const account={id:91,bank_name:"Audit Bank",account_holder:"Audit User",currency:"TRY",is_active:1};
      const card={id:42,bank_account_id:91,card_name:"Business Card",card_last4:"4321",card_limit:10000,current_debt:750,due_day:15,statement_day:1,is_active:1};
      const alert={id:7,alert_type:"loan_reminder",trigger_time:"11:00",is_enabled:1};
      const loan={id:5,bank_account_id:91,amount:10000,total_payment:12000,interest_rate:12,term_months:12,status:"Aktif",start_date:"2026-01-01"};
      const installments=[{loan_id:5,installment_no:1,due_date:"2026-02-01",total_amount:6000,status:"Ödendi"},{loan_id:5,installment_no:2,due_date:"2026-03-01",total_amount:6000,status:"Bekliyor"}];
      const transactions=[{id:301,bank_account_id:91,date:"2026-10-01",created_at:"2026-10-01 10:30:00",type:"Gider",category:"Kira",description:"Office rent",amount:500,payment_method:"Havale"},{id:302,related_account_id:91,date:"2026-10-02",created_at:"2026-10-02 12:00:00",type:"Gelir",category:"Hizmet",description:"Service payment",amount:1500,payment_method:"EFT",customer_name:"Audit Customer"}];
      const requests=[];window.__bankCardAudit={requests};
      apiFetch=async(url,options={})=>{const payload=options.body?JSON.parse(options.body):null;requests.push({url:String(url),method:options.method||"GET",payload});if(String(url).includes("bank_accounts"))return{rows:[account],columns:["id","bank_name","account_holder","account_number","currency","current_balance","is_active"]};if(String(url).includes("bank_cards")&&options.method)return{ok:true};if(String(url).includes("bank_cards"))return{rows:[card]};if(String(url).includes("scheduled_alerts"))return{rows:[alert]};if(String(url).includes("loan_installments"))return{rows:installments};if(String(url).includes("loans"))return{rows:[loan]};if(String(url).includes("accounting")){const offset=Number(new URL(String(url),"http://audit.local").searchParams.get("offset")||0);return{rows:transactions.slice(offset,offset+1),count:transactions.length}}return{rows:[]}};
      db.finance=[];openManifestDialog({key:"bank_detail_dialog_components"});await new Promise(resolve=>setTimeout(resolve,60));
      const form=document.querySelector("#dialogForm"),fields=form?[...form.querySelectorAll("input")].map(item=>item.name):[];
      if(!form||!fields.includes("card_name")||!fields.includes("card_last4")||!fields.includes("card_limit")||!fields.includes("current_debt")||!fields.includes("due_day")||!fields.includes("statement_day")||!fields.includes("is_active"))throw new Error("Credit card editor fields are incomplete.");
      form.querySelector('[name="card_name"]').value="Audit Card";form.querySelector('[name="card_last4"]').value="1234";form.querySelector('[name="card_limit"]').value="12000";form.querySelector('[name="current_debt"]').value="900";form.querySelector('[name="due_day"]').value="16";form.querySelector('[name="statement_day"]').value="2";
      const editorShot=await new Promise(resolve=>setTimeout(resolve,40));return{fields,opened:true};
    })()`);
    await delay(250);
    const editorShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const editorPath = path.join(outDir, "bank-card-editor-manifest-headless.png");
    fs.writeFileSync(editorPath, Buffer.from(editorShot.data, "base64"));
    const saved = await evaluate(`(async()=>{document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,240));return{audit:window.__bankCardAudit,detailOpened:document.querySelector("#appDialog")?.open&&document.querySelector("#dialogTitle")?.textContent==="Banka Hesab\u0131 Detaylar\u0131"}})()`);
    const request = saved.audit.requests.find(item => item.method === "POST");
    if (!opened.opened || !request || request.url !== "/api/desktop/table/bank_cards" || request.payload.bank_account_id !== 91 || request.payload.card_name !== "Audit Card" || request.payload.card_last4 !== "1234" || request.payload.card_limit !== 12000 || request.payload.current_debt !== 900 || request.payload.due_day !== 16 || request.payload.statement_day !== 2 || request.payload.is_active !== 1 || !saved.detailOpened) throw new Error(JSON.stringify({ opened, saved, exceptions }));
    const sectorEditorKeyboard = await evaluate(`(async()=>{const originalSector=currentSector,state={};document.querySelector("#appDialog")?.close();try{currentSector="teknik_servis";interfaceEditorDialog();await new Promise(resolve=>setTimeout(resolve,80));const dialog=document.querySelector("#appDialog"),tabs=[...dialog.querySelectorAll("[data-editor-sector]")],panels=[...dialog.querySelectorAll("[data-editor-panel]")];state.count=tabs.length;state.open=dialog.open;state.initialRoving=tabs.filter(tab=>tab.tabIndex===0).length===1&&tabs[0]?.tabIndex===0;state.ariaLinks=tabs.every(tab=>tab.getAttribute("role")==="tab"&&dialog.querySelector("#"+tab.getAttribute("aria-controls"))?.getAttribute("aria-labelledby")===tab.id);tabs[0].parentElement.style.display="grid";tabs[0]?.focus();const key=(tab,value)=>tab.dispatchEvent(new KeyboardEvent("keydown",{key:value,bubbles:true,cancelable:true}));key(tabs[0],"ArrowLeft");state.leftWraps=document.activeElement===tabs[1]&&tabs[1]?.getAttribute("aria-selected")==="true"&&panels[1]?.classList.contains("mobile-active");key(tabs[1],"ArrowRight");state.rightWraps=document.activeElement===tabs[0]&&tabs[0]?.getAttribute("aria-selected")==="true";key(tabs[0],"End");state.endSelectsSecond=document.activeElement===tabs[1];key(tabs[1],"Home");state.homeSelectsFirst=document.activeElement===tabs[0];state.finalRoving=tabs.filter(tab=>tab.tabIndex===0).length===1&&tabs[0]?.tabIndex===0;return state}finally{document.querySelector("#appDialog")?.close();currentSector=originalSector}})()`);
    if (sectorEditorKeyboard.count !== 2 || !sectorEditorKeyboard.open || !sectorEditorKeyboard.initialRoving || !sectorEditorKeyboard.ariaLinks || !sectorEditorKeyboard.leftWraps || !sectorEditorKeyboard.rightWraps || !sectorEditorKeyboard.endSelectsSecond || !sectorEditorKeyboard.homeSelectsFirst || !sectorEditorKeyboard.finalRoving) throw new Error("Sector editor tab keyboard mismatch: " + JSON.stringify(sectorEditorKeyboard));
    const detail = await evaluate(`(async()=>{await ayecOpenBankAccountDetail(${JSON.stringify({id:91,bank_name:"Audit Bank",account_holder:"Audit User",currency:"TRY",is_active:1})});await new Promise(resolve=>setTimeout(resolve,180));const tabs=[...document.querySelectorAll("[data-bank-tab]")].map(item=>item.textContent);const general=document.querySelector('[data-bank-panel="general"]')?.textContent||"",header=document.querySelector(".bank-account-title-card")?.textContent||"";document.querySelector('[data-bank-tab="loans"]').click();const loan=document.querySelector('[data-bank-panel="loans"]')?.textContent||"";const loanRows=document.querySelectorAll('[data-bank-panel="loans"] tbody tr').length;document.querySelector('[data-bank-tab="analytics"]').click();const analytics=document.querySelector('[data-bank-panel="analytics"]')?.textContent||"";document.querySelector('[data-bank-tab="transactions"]').click();const initialRows=document.querySelectorAll('[data-bank-tx-rows] tr').length;document.querySelector('[data-bank-tx-search]').value="rent";document.querySelector('[data-bank-tx-search]').dispatchEvent(new Event("input",{bubbles:true}));const filteredRows=document.querySelectorAll('[data-bank-tx-rows] tr').length;const filterText=document.querySelector('[data-bank-tx-rows]')?.textContent||"";document.querySelector('[data-bank-tx-reset]').click();document.querySelector('[data-bank-tx-rows] tr[data-bank-tx-id]').dispatchEvent(new MouseEvent("dblclick",{bubbles:true}));const transactionDetailTitle=document.querySelector("#dialogTitle")?.textContent||"";document.querySelector("#dialogClose").click();await new Promise(resolve=>setTimeout(resolve,260));const transactionDetailRestored=document.querySelector("#dialogTitle")?.textContent==="Banka Hesab\u0131 Detaylar\u0131";document.querySelector('[data-bank-tab="extra"]').click();const transactionPages=window.__bankCardAudit.requests.filter(item=>item.url.includes("accounting")).length;return{tabs,general,header,loan,loanRows,analytics,initialRows,filteredRows,filterText,transactionDetailTitle,transactionDetailRestored,transactionPages,editAccount:!!document.querySelector('[data-bank-account-edit]'),rows:document.querySelectorAll(".bank-card-detail tbody tr").length,add:!!document.querySelector("[data-bank-card-add]"),edit:!!document.querySelector('[data-bank-card-edit="42"]'),delete:!!document.querySelector('[data-bank-card-delete="42"]'),alerts:document.querySelectorAll(".bank-alert-detail tbody tr").length,alertEdit:!!document.querySelector('[data-alert-edit="0"]')}})()`);
    const bankTabKeyboard = await evaluate(`(()=>{const tabs=[...document.querySelectorAll("[data-bank-tab]")],state={count:tabs.length,initialRoving:tabs.filter(tab=>tab.tabIndex===0).length===1};const key=(tab,value)=>tab.dispatchEvent(new KeyboardEvent("keydown",{key:value,bubbles:true,cancelable:true}));const select=name=>tabs.find(tab=>tab.dataset.bankTab===name);select("general")?.click();state.generalRoving=select("general")?.tabIndex===0&&document.querySelector('[data-bank-panel="general"]')?.getAttribute("aria-labelledby")==="bank-detail-tab-general";select("extra")?.focus();key(select("extra"),"ArrowRight");state.rightWrapsToGeneral=document.activeElement===select("general");key(select("general"),"ArrowLeft");state.leftWrapsToExtra=document.activeElement===select("extra");key(select("extra"),"Home");state.homeSelectsGeneral=document.activeElement===select("general");key(select("general"),"End");state.endSelectsExtra=document.activeElement===select("extra");state.finalRoving=tabs.filter(tab=>tab.tabIndex===0).length===1&&select("extra")?.tabIndex===0;return state})()`);
    if (bankTabKeyboard.count !== 5 || !bankTabKeyboard.initialRoving || !bankTabKeyboard.generalRoving || !bankTabKeyboard.rightWrapsToGeneral || !bankTabKeyboard.leftWrapsToExtra || !bankTabKeyboard.homeSelectsGeneral || !bankTabKeyboard.endSelectsExtra || !bankTabKeyboard.finalRoving) throw new Error("Bank account tab keyboard mismatch: " + JSON.stringify(bankTabKeyboard));
    const detailPath = path.join(outDir, "bank-card-account-detail-headless.png");
    const detailPaths = [];
    for (const tab of ["general", "loans", "transactions", "analytics", "extra"]) {
      await evaluate(`document.querySelector('[data-bank-tab="${tab}"]').click()`);
      await delay(100);
      const detailsShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      const screenshotPath = path.join(outDir, `bank-account-${tab}-headless.png`);
      fs.writeFileSync(screenshotPath, Buffer.from(detailsShot.data, "base64"));
      detailPaths.push(screenshotPath);
      if (tab === "extra") fs.copyFileSync(screenshotPath, detailPath);
    }
    if (detail.rows !== 1 || !detail.add || !detail.edit || !detail.delete || !detail.editAccount || !detail.header.includes("Audit Bank") || !detail.header.includes("Audit User") || !detail.header.includes("Aktif") || detail.alerts !== 1 || !detail.alertEdit || detail.tabs.length !== 5 || !detail.general.includes("Hesap Türü") || !detail.general.includes("Kredi") || !detail.loan.includes("Kredi Özeti") || detail.loanRows !== 2 || !detail.analytics.includes("Toplam Giriş") || detail.initialRows !== 2 || detail.filteredRows !== 1 || !detail.filterText.includes("Office rent") || detail.transactionDetailTitle !== "\u0130\u015flem Detay\u0131" || !detail.transactionDetailRestored || detail.transactionPages !== 6 || exceptions.length) throw new Error(JSON.stringify({ opened, saved, detail, bankTabKeyboard, exceptions }));
    const alertEdited = await evaluate(`(async()=>{document.querySelector('[data-alert-edit="0"]').click();await new Promise(resolve=>setTimeout(resolve,140));const form=document.querySelector("#dialogForm"),label=form?.querySelector('[name="trigger_time"]'),check=form?.querySelector('[name="is_enabled"]');const loaded={time:label?.value,active:check?.checked};label.value="11:30";check.checked=false;document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,240));const request=window.__bankCardAudit.requests.filter(item=>item.method==="POST").find(item=>item.url.includes("scheduled_alerts"));return{loaded,payload:request?.payload,detailRestored:document.querySelector("#dialogTitle")?.textContent==="Banka Hesab\u0131 Detaylar\u0131"}})()`);
    const edited = await evaluate(`(async()=>{document.querySelector('[data-bank-tab="extra"]').click();document.querySelector('[data-bank-card-edit="42"]').click();await new Promise(resolve=>setTimeout(resolve,140));const form=document.querySelector("#dialogForm"),loaded={name:form?.querySelector('[name="card_name"]')?.value,last4:form?.querySelector('[name="card_last4"]')?.value,limit:form?.querySelector('[name="card_limit"]')?.value,debt:form?.querySelector('[name="current_debt"]')?.value};document.querySelector("#dialogCancel").click();await new Promise(resolve=>setTimeout(resolve,160));return{loaded,detailRestored:document.querySelector("#dialogTitle")?.textContent==="Banka Hesab\u0131 Detaylar\u0131"}})()`);
    const deleted = await evaluate(`(async()=>{document.querySelector('[data-bank-tab="extra"]').click();document.querySelector('[data-bank-card-delete="42"]').click();await new Promise(resolve=>setTimeout(resolve,60));const confirmation=document.querySelector("#dialogBody")?.textContent||"";document.querySelector("#dialogForm").requestSubmit();await new Promise(resolve=>setTimeout(resolve,240));const posts=window.__bankCardAudit.requests.filter(item=>item.method==="POST");return{confirmation,deletePayload:posts[posts.length-1]?.payload,detailRestored:document.querySelector("#dialogTitle")?.textContent==="Banka Hesab\u0131 Detaylar\u0131"}})()`);
    const accountEdited = await evaluate(`(async()=>{document.querySelector('[data-bank-account-edit]').click();await new Promise(resolve=>setTimeout(resolve,100));const form=document.querySelector("#dialogForm");const result={title:document.querySelector("#dialogTitle")?.textContent,name:form?.querySelector('[name="bank_name"]')?.value,fields:[...form.querySelectorAll("input")].map(input=>input.name)};document.querySelector("#dialogCancel").click();return result})()`);
    if (alertEdited.loaded.time !== "11:00" || !alertEdited.loaded.active || alertEdited.payload?.id !== 7 || alertEdited.payload?.trigger_time !== "11:30" || alertEdited.payload?.is_enabled !== 0 || !alertEdited.detailRestored || edited.loaded.name !== "Business Card" || edited.loaded.last4 !== "4321" || edited.loaded.limit !== "10000" || edited.loaded.debt !== "750" || !edited.detailRestored || !deleted.confirmation.includes("silinsin mi") || deleted.deletePayload?._action !== "delete" || deleted.deletePayload?.id !== 42 || !deleted.detailRestored || !accountEdited.fields.includes("bank_name") || accountEdited.name !== "Audit Bank" || exceptions.length) throw new Error(JSON.stringify({ opened, saved, detail, alertEdited, edited, deleted, accountEdited, exceptions }));
    process.stdout.write(`${JSON.stringify({ opened, saved: { detailOpened: saved.detailOpened, request: request.payload }, detail, bankTabKeyboard, sectorEditorKeyboard, alertEdited, edited, deleted, accountEdited, exceptions, headless: true, screenshots: [editorPath, ...detailPaths, detailPath] })}\n`);
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
