const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9239);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `customer-context-headless-profile-${process.pid}`);
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
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
    "--window-size=1280,900", baseUrl
  ], { stdio: "ignore", windowsHide: true });
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
      if (await evaluate("document.readyState === 'complete' && typeof renderCustomers === 'function' && typeof showContext === 'function'")) break;
      await delay(200);
    }
    const regular = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page="customers";document.body.dataset.page="customers";currentAuthUser={role:"Admin"};
      db.settings.contextMenu=true;
      db.customers=[{id:501,desktopId:501,name:"Fixture Customer",company:"Fixture Ltd",phone:"5550001234",email:"fixture@example.test",type:"Kurumsal",city:"Istanbul",balances:{TRY:-1250,USD:0,EUR:0},services:[],quotes:[],is_active:true}];
      document.querySelector("#content").innerHTML=renderCustomers();bindPageRows();
      const row=document.querySelector('tr[data-kind="customer"]');
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});
      row.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu");
      return {prevented:event.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-customer-context-action]"),button=>({action:button.dataset.customerContextAction,label:button.textContent.trim()})),separators:menu.querySelectorAll(".customer-context-separator").length,insideViewport:menu.getBoundingClientRect().left>=0&&menu.getBoundingClientRect().right<=innerWidth&&menu.getBoundingClientRect().top>=0&&menu.getBoundingClientRect().bottom<=innerHeight};
    })()`);
    const expected = ["notes", "360", "edit", "service", "invoice", "payment", "whatsapp", "debt-reminder", "excel", "pdf", "print", "delete"];
    if (!regular.open || !regular.prevented || JSON.stringify(regular.actions.map(item => item.action)) !== JSON.stringify(expected) || regular.separators !== 4 || !regular.insideViewport) throw new Error(`Customer context menu mismatch: ${JSON.stringify(regular)}`);
    const regularShot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "customer-context-menu-headless.png"), Buffer.from(regularShot.data, "base64"));
    const selected = await evaluate(`(() => {
      const menu=document.querySelector("#contextMenu");menu.classList.remove("open");
      document.querySelector("#customerTable")?.classList.add("multi-select");
      const row=document.querySelector('tr[data-kind="customer"]');
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});row.dispatchEvent(event);
      return Array.from(document.querySelectorAll("#contextMenu [data-customer-context-action]"),button=>button.dataset.customerContextAction);
    })()`);
    if (!selected.includes("selected-excel")) throw new Error(`Customer multi-select context action missing: ${JSON.stringify(selected)}`);
    const preference = await evaluate(`(() => {
      const menu=document.querySelector("#contextMenu");menu.classList.remove("open");
      db.settings.contextMenu=false;
      const row=document.querySelector('tr[data-kind="customer"]');
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});row.dispatchEvent(event);
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented};
    })()`);
    if (preference.open || preference.prevented) throw new Error(`Customer context-menu preference mismatch: ${JSON.stringify(preference)}`);
    const customerNotesFlow = await evaluate(`(async () => {
      db.settings.contextMenu=true;
      window.__auditCustomerNoteRequests=[];
      window.__auditOriginalApiFetch=apiFetch;
      apiFetch=async(url,options={})=>{
        const payload=options.body?JSON.parse(options.body):null;
        window.__auditCustomerNoteRequests.push({url:String(url),method:options.method||"GET",payload});
        if(String(url).includes("customer_notes")&&options.method!=="POST")return {rows:[{id:801,customer_id:501,type:"Genel Not",title:"Fixture note",content:"Initial note",created_at:"2026-10-15 12:00:00"}]};
        return {rows:[]};
      };
      const row=document.querySelector('tr[data-kind="customer"]');
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450}));
      document.querySelector('#contextMenu [data-customer-context-action="notes"]').click();
      await new Promise(resolve=>setTimeout(resolve,30));
      const dialog=document.querySelector("#appDialog");
      const initial={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,count:document.querySelector("#customerNoteCount")?.textContent,loaded:document.querySelector("#customerNoteTitle")?.value};
      const type=document.querySelector("#customerNoteType"),search=document.querySelector("#customerNoteSearch");
      const initialFilterCount=document.querySelectorAll("#customerNoteList [data-cnote-index]").length;
      document.querySelector('#dialogBody [data-cnote-filter="WhatsApp Mesajı"]').click();
      const categoryCount=document.querySelectorAll("#customerNoteList [data-cnote-index]").length;
      document.querySelector('#dialogBody [data-cnote-filter="Tümü"]').click();
      search.value="not found";search.dispatchEvent(new Event("input",{bubbles:true}));
      const searchCount=document.querySelectorAll("#customerNoteList [data-cnote-index]").length;
      search.value="";search.dispatchEvent(new Event("input",{bubbles:true}));
      document.querySelector("#customerNoteNew").click();
      document.querySelector("#customerNoteTitle").value="Saved fixture note";
      type.value="WhatsApp Mesajı";
      const editor=document.querySelector("#customerNoteEditor"),value=document.querySelector("#customerNoteValue");
      editor.innerHTML="Saved note body";editor.dispatchEvent(new Event("input",{bubbles:true}));
      value.value=editor.innerHTML;
      document.querySelector("#dialogSubmit").click();
      for(let attempt=0;attempt<30&&!window.__auditCustomerNoteRequests.some(request=>request.method==="POST");attempt++)await new Promise(resolve=>setTimeout(resolve,10));
      const saved=window.__auditCustomerNoteRequests.find(request=>request.method==="POST");
      const result={initial,initialFilterCount,categoryCount,searchCount,saved:saved?.payload,updatedCount:document.querySelectorAll("#customerNoteList [data-cnote-index]").length,selectedTitle:document.querySelector("#customerNoteTitle")?.value,dialogOpen:dialog.open};
      apiFetch=window.__auditOriginalApiFetch;delete window.__auditOriginalApiFetch;delete window.__auditCustomerNoteRequests;
      return result;
    })()`);
    await delay(30);
    const notesShot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});
    fs.writeFileSync(path.join(outputDir,"customer-notes-dialog-headless.png"),Buffer.from(notesShot.data,"base64"));
    if (!customerNotesFlow.initial.open || customerNotesFlow.initial.count !== "1 Kay\u0131t Listelendi" || customerNotesFlow.initial.loaded !== "Fixture note" || customerNotesFlow.initialFilterCount !== 1 || customerNotesFlow.categoryCount !== 0 || customerNotesFlow.searchCount !== 0 || customerNotesFlow.saved?.title !== "Saved fixture note" || customerNotesFlow.saved?.content !== "Saved note body" || customerNotesFlow.saved?.customer_id !== 501 || customerNotesFlow.updatedCount !== 1 || customerNotesFlow.selectedTitle !== "Saved fixture note" || !customerNotesFlow.dialogOpen) throw new Error(`Customer notes route mismatch: ${JSON.stringify(customerNotesFlow)}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    console.log(JSON.stringify({ regular, selectedActions: selected, preference, customerNotesFlow, browserExceptions: exceptions.length, headless: true }));
  } finally {
    try { socket?.close(); } catch (_) {}
    try { browser.kill(); } catch (_) {}
  }
}

run().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });
