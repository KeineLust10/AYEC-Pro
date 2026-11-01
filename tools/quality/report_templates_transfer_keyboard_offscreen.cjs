const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/report-templates-transfer-keyboard"));
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-report-templates-keyboard-"));
const port = Number(process.env.AYEC_AUDIT_PORT || 19200 + process.pid % 400);
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30200 + process.pid % 500);
const baseUrl = `http://127.0.0.1:${port}/`;
const sector = process.env.AYEC_AUDIT_SECTOR === "otomotiv" ? "otomotiv" : "teknik_servis";
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
const profile = path.join(outputDir, `report-templates-keyboard-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
}

async function waitForPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Hidden Edge page did not become available.");
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "audit-result.json");
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const target = await waitForPage();
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
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
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
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
      return response.result?.value;
    };
    await send("Runtime.enable");
    await send("Page.enable");
    await send("Page.navigate", { url: baseUrl });
    await evaluate(`new Promise((resolve,reject)=>{let attempts=0;const timer=setInterval(()=>{if(typeof page!=="undefined"&&typeof render==="function"&&typeof db!=="undefined"){clearInterval(timer);resolve(true)}else if(++attempts>100){clearInterval(timer);reject(new Error("AYEC app globals did not load"))}},50)})`);
    const workflow = await evaluate(`(async()=>{
      const original={page,currentSector,apiFetch,rows:db.fast_notes,contextMenu:db.settings.contextMenu,createObjectURL:URL.createObjectURL,anchorClick:HTMLAnchorElement.prototype.click,inputClick:HTMLInputElement.prototype.click,clipboard:Object.getOwnPropertyDescriptor(navigator,"clipboard")};
      const fixture=[{id:99301,category:"Device QA",label:"Keyboard template",content:"Check device" ,is_active:1,display_order:1}];
      const writes=[],copyUsageWrites=[];let downloadedBlob=null,downloadInfo=null,pickerOpened=false,nextId=99302,clipboardText=null;
      const waitFor=async(selector)=>{for(let i=0;i<80;i++){const node=document.querySelector(selector);if(node)return node;await new Promise(resolve=>setTimeout(resolve,50))}throw new Error("Timed out waiting for "+selector)};
      try{
        db.fast_notes=fixture;
        db.settings.contextMenu=true;
        Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{clipboardText=text}}});
        apiFetch=async(url,options={})=>{if(String(url)==="/api/desktop/report-template-usage"){copyUsageWrites.push(JSON.parse(options.body));return{date:"2026-10-25",count:1,average_seconds:1}}if(!String(url).startsWith("/api/desktop/table/fast_notes"))return{rows:[]};if(options.method==="POST"){const values=JSON.parse(options.body);writes.push(values);if(values._action==="delete"){for(let i=fixture.length-1;i>=0;i--)if(String(fixture[i].id)===String(values.id))fixture.splice(i,1)}else if(values._action==="update"){const index=fixture.findIndex(row=>String(row.id)===String(values.id));if(index>=0)fixture[index]={...fixture[index],...values}}else fixture.push({...values,id:nextId++});return{}}return{rows:fixture}};
        currentSector="${sector}";page="report-templates";render();
        const trigger=await waitFor("#templateImport");
        await waitFor("[data-template-row]");
        const copyButton=await waitFor("#templateCopy");copyButton.click();
        for(let i=0;i<80&&copyUsageWrites.length===0;i++)await new Promise(resolve=>setTimeout(resolve,50));
        const copiedTemplate=clipboardText;
        trigger.click();
        const menu=document.querySelector("#contextMenu");
        const items=[...menu.querySelectorAll("[data-template-transfer]")];
        const result={opened:menu.classList.contains("open"),expanded:trigger.getAttribute("aria-expanded"),initialFocus:document.activeElement?.dataset?.templateTransfer||null,items:items.map(item=>item.dataset.templateTransfer),copiedTemplate,copyUsagePayload:copyUsageWrites[0]||null};
        const key=(value)=>document.activeElement.dispatchEvent(new KeyboardEvent("keydown",{key:value,bubbles:true,cancelable:true}));
        key("ArrowDown");result.afterArrowDown=document.activeElement?.dataset?.templateTransfer||null;
        key("End");result.afterEnd=document.activeElement?.dataset?.templateTransfer||null;
        key("Home");result.afterHome=document.activeElement?.dataset?.templateTransfer||null;
        key("ArrowUp");result.afterArrowUp=document.activeElement?.dataset?.templateTransfer||null;
        key("Escape");result.closed=!menu.classList.contains("open");result.collapsed=trigger.getAttribute("aria-expanded");result.focusReturned=document.activeElement===trigger;
        URL.createObjectURL=blob=>{downloadedBlob=blob;return"blob:report-template-audit"};
        HTMLAnchorElement.prototype.click=function(){downloadInfo={filename:this.download,href:this.href}};
        trigger.click();menu.querySelector('[data-template-transfer="export"]').click();
        result.exportFilename=downloadInfo?.filename||null;result.exportContainsFixture=Boolean(downloadedBlob&&(await downloadedBlob.text()).includes("Keyboard template"));
        const originalRow=document.querySelector('[data-template-row="99301"]');originalRow.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
        await waitFor("#dialogSubmit");document.querySelector('textarea[name="label"]').value="Edited template";document.querySelector("#dialogSubmit").click();
        for(let i=0;i<80&&!writes.some(value=>value._action==="update");i++)await new Promise(resolve=>setTimeout(resolve,50));
        for(let i=0;i<80&&!([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Edited template")));i++)await new Promise(resolve=>setTimeout(resolve,50));
        result.editPayload=writes.find(value=>value._action==="update")||null;result.editedRowVisible=Boolean([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Edited template")));
        const editedRow=document.querySelector('[data-template-row="99301"]');editedRow.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,button:2}));
        const deleteAction=await waitFor('[data-template-context="delete"]');deleteAction.click();await waitFor("#dialogCancel");document.querySelector("#dialogCancel").click();
        result.deleteCancelPreserved=Boolean(document.querySelector('[data-template-row="99301"]'));result.noDeleteWriteOnCancel=!writes.some(value=>value._action==="delete");
        document.querySelector('[data-template-row="99301"]').dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,button:2}));
        const confirmedDeleteAction=await waitFor('[data-template-context="delete"]');confirmedDeleteAction.click();await waitFor("#dialogSubmit");document.querySelector("#dialogSubmit").click();
        for(let i=0;i<80&&!writes.some(value=>value._action==="delete");i++)await new Promise(resolve=>setTimeout(resolve,50));
        for(let i=0;i<80&&document.querySelector('[data-template-row="99301"]');i++)await new Promise(resolve=>setTimeout(resolve,50));
        result.deletePayload=writes.find(value=>value._action==="delete")||null;result.deletedRowAbsent=!document.querySelector('[data-template-row="99301"]');
        document.getElementById("templateAdd").click();await waitFor("#dialogSubmit");
        document.querySelector('input[name="category"]').value="Checklist QA";document.querySelector('textarea[name="label"]').value="Created template";document.querySelector('input[name="display_order"]').value="3";document.querySelector("#dialogSubmit").click();
        for(let i=0;i<80&&!writes.some(value=>value.label==="Created template");i++)await new Promise(resolve=>setTimeout(resolve,50));
        for(let i=0;i<80&&!([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Created template")));i++)await new Promise(resolve=>setTimeout(resolve,50));
        result.createPayload=writes.find(value=>value.label==="Created template")||null;result.createdRowVisible=Boolean([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Created template")));
        HTMLInputElement.prototype.click=function(){if(this.id==="templateCsv"){pickerOpened=true;return}return original.inputClick.call(this)};
        trigger.click();menu.querySelector('[data-template-transfer="import"]').click();
        const input=document.getElementById("templateCsv"),file=new File(["category,label,is_active,display_order\\r\\nImport QA,Imported template,1,2"],"report-templates.csv",{type:"text/csv"});
        Object.defineProperty(input,"files",{configurable:true,value:[file]});input.dispatchEvent(new Event("change",{bubbles:true}));
        for(let i=0;i<80&&writes.length===0;i++)await new Promise(resolve=>setTimeout(resolve,50));
        for(let i=0;i<80&&!([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Imported template")));i++)await new Promise(resolve=>setTimeout(resolve,50));
        result.importPickerOpened=pickerOpened;result.importPayload=writes.find(value=>value.label==="Imported template")||null;result.importedRowVisible=Boolean([...document.querySelectorAll("[data-template-row]")].some(row=>row.textContent.includes("Imported template")));
        const category=await waitFor('[data-template-category="Import QA"]');category.click();result.categoryFilterRows=document.querySelectorAll("[data-template-row]").length;result.categoryFilterLabel=document.querySelector("[data-template-row]")?.textContent||"";
        const search=document.getElementById("templateSearch");search.value="no matching template";search.dispatchEvent(new Event("input",{bubbles:true}));result.searchNoMatches=document.querySelectorAll("[data-template-row]").length===0;
        document.getElementById("templateClear").click();result.clearRestoresRows=document.querySelectorAll("[data-template-row]").length===2;result.clearRestoresSearch=search.value==="";
        document.getElementById("templateManage").click();const manageTitle=await waitFor("#dialogTitle"),manageDialog=document.getElementById("appDialog");result.manageDialogOpen=Boolean(manageDialog.open&&manageTitle.textContent.length>0);result.manageCounts=[...document.querySelectorAll("#dialogBody .field strong")].map(item=>item.textContent.trim());document.getElementById("dialogClose").click();result.manageDialogClosed=!manageDialog.open;
        return result;
      }finally{URL.createObjectURL=original.createObjectURL;HTMLAnchorElement.prototype.click=original.anchorClick;HTMLInputElement.prototype.click=original.inputClick;if(original.clipboard)Object.defineProperty(navigator,"clipboard",original.clipboard);else delete navigator.clipboard;page=original.page;currentSector=original.currentSector;apiFetch=original.apiFetch;db.fast_notes=original.rows;db.settings.contextMenu=original.contextMenu;render()}
    })()`);
    const expected = workflow.opened && workflow.expanded === "true" && workflow.initialFocus === "import" && workflow.items.join(",") === "import,export" && workflow.afterArrowDown === "export" && workflow.afterEnd === "export" && workflow.afterHome === "import" && workflow.afterArrowUp === "export" && workflow.closed && workflow.collapsed === "false" && workflow.focusReturned && workflow.copiedTemplate === "Keyboard template" && workflow.copyUsagePayload && workflow.exportFilename === "rapor-cumle-kaliplari.csv" && workflow.exportContainsFixture && workflow.editPayload?._action === "update" && workflow.editPayload?.label === "Edited template" && workflow.editedRowVisible && workflow.deleteCancelPreserved && workflow.noDeleteWriteOnCancel && workflow.deletePayload?._action === "delete" && workflow.deletedRowAbsent && workflow.createPayload?.label === "Created template" && workflow.createPayload?.category === "Checklist QA" && workflow.createdRowVisible && workflow.importPickerOpened && workflow.importPayload?.label === "Imported template" && workflow.importPayload?.category === "Import QA" && workflow.importedRowVisible && workflow.categoryFilterRows === 1 && workflow.categoryFilterLabel.includes("Imported template") && workflow.searchNoMatches && workflow.clearRestoresRows && workflow.clearRestoresSearch && workflow.manageDialogOpen && workflow.manageCounts.join(",") === "2,2" && workflow.manageDialogClosed;
    const result = { ok: Boolean(expected && exceptions.length === 0), workflow, browserExceptions: exceptions };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2), "utf8");
    if (!result.ok) process.exitCode = 1;
    process.stdout.write(JSON.stringify({ resultPath, ok: result.ok }) + "\n");
  } catch (error) {
    fs.writeFileSync(resultPath, JSON.stringify({ ok: false, error: String(error.stack || error) }, null, 2), "utf8");
    process.stderr.write(String(error.stack || error) + "\n");
    process.exitCode = 1;
  } finally {
    try { socket?.close(); } catch (_) {}
    await stopProcess(browser);
    await stopProcess(server);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
