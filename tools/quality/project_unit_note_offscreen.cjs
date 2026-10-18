const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || (9300 + process.pid % 500));
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `project-unit-note-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
    "--window-size=1280,900", baseUrl
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const pages = await fetch(`http://127.0.0.1:${debugPort}/json`).then(response => response.json());
        target = pages.find(item => item.type === "page" && item.url.startsWith(baseUrl));
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose the audit page.");
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
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 15000);
      pending.set(id, {
        resolve(value) { clearTimeout(timer); resolve(value); },
        reject(error) { clearTimeout(timer); reject(error); }
      });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
      return response.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    await send("Page.navigate", { url: baseUrl });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof p9EditUnitProductNote === 'function'");
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("Project note editor code did not load.");
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const originalApiFetch = apiFetch;
      const button = document.createElement("button");
      button.className = "p9-note-edit";
      button.dataset.id = "953";
      button.dataset.note = "Original note";
      button.textContent = "Original note";
      document.body.append(button);
      window.__projectNoteRequest = null;
      apiFetch = async (url, options = {}) => { window.__projectNoteRequest = { url, payload: JSON.parse(options.body) }; return { ok: true }; };
      p9EditUnitProductNote(button);
      const dialog = document.querySelector(".p9-unit-note-dialog");
      const textarea = dialog?.querySelector('textarea[name="notes"]');
      const initial = { open: dialog?.open === true, title: dialog?.querySelector("h2")?.textContent, note: textarea?.value };
      textarea.value = "Updated fixture note";
      dialog.querySelector('button[type="submit"]').click();
      await new Promise(resolve => setTimeout(resolve, 0));
      const state = { request: window.__projectNoteRequest, closed: !dialog.isConnected, open: dialog.open, updatedNote: button.dataset.note, buttonText: button.textContent };
      apiFetch = originalApiFetch;
      button.remove();
      return { initial, state };
    })()`);
    const expected = result.state.request?.url === "/api/desktop/table/project_unit_products"
      && result.state.request.payload.id === 953
      && result.state.request.payload.notes === "Updated fixture note"
      && result.state.request.payload._action === "update"
      && result.state.closed && !result.state.open
      && result.state.updatedNote === "Updated fixture note";
    if (!result.initial.open || result.initial.title !== "Teknik Not" || result.initial.note !== "Original note" || !expected || exceptions.length) {
      throw new Error(`Project note editor mismatch: ${JSON.stringify({ result, browserExceptions: exceptions })}`);
    }
    const menuResult = await evaluate(`(()=>{
      const oldLoadPart9Projects=loadPart9Projects;
      const oldApiFetch=apiFetch;
      window.__p9UnitContextWrites=[];
      window.__p9ProductAction=false;
      loadPart9Projects=async()=>{};
      apiFetch=async(url,options={})=>{window.__p9UnitContextWrites.push({url,body:JSON.parse(options.body||"{}")});return{ok:true,rows:[],columns:[]}};
      db.settings.contextMenu=true;
      desktopSettings.rc_projects="1";
      p9ProjectState.projects=[{id:42,name:"Audit Project"}];
      p9ProjectState.selectedId=42;
      p9ProjectState.units=[{id:954,project_id:42,status:"Bekliyor"}];
      document.querySelectorAll("dialog[open]").forEach(dialog=>dialog.close());
      document.querySelector("#toastRoot")?.replaceChildren();
      page="projects";
      document.body.dataset.page="projects";
      document.querySelector("#content").innerHTML='<div class="page-head"><div><h2>Project Detail</h2></div></div><section class="p9-project-screen"><div class="p9-unit-grid"><article class="p9-unit-card" data-p9-unit-card="954"><header><strong>Block A - Unit 101</strong><span>Bekliyor</span></header><small>Floor 1 | Apartment</small><div class="p9-unit-meta"><span>Installed devices</span><b>0</b></div></article></div></section>';
      const card=document.querySelector('[data-p9-unit-card="954"]');
      card.innerHTML+='<button type="button" data-p9-unit-products>Products</button>';
      card.querySelector("[data-p9-unit-products]").addEventListener("click",()=>{window.__p9ProductAction=true});
      const openEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:1270,clientY:890});
      card.dispatchEvent(openEvent);
      const menu=document.querySelector("#contextMenu");
      const box=menu.getBoundingClientRect();
      const initial={opened:menu.classList.contains("open")&&menu.classList.contains("project-unit-context-menu"),defaultPrevented:openEvent.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-p9-unit-context-status]"),node=>node.dataset.p9UnitContextStatus).concat(menu.querySelector("[data-p9-unit-context-products]")?.lastElementChild?.textContent.trim()),checked:menu.querySelector('[data-p9-unit-context-status="Bekliyor"]')?.getAttribute("aria-checked"),bounds:{x:box.x,y:box.y,width:box.width,height:box.height}};
      window.__p9UnitContextRestore={oldLoadPart9Projects,oldApiFetch,card};
      return initial;
    })()`);
    const menuImage = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1280, height: 900, scale: 1 } });
    const menuScreenshot = path.join(outputDir, "project-unit-context-menu-headless.png");
    fs.writeFileSync(menuScreenshot, Buffer.from(menuImage.data, "base64"));
    const menuActions = await evaluate(`(async()=>{
      const menu=document.querySelector("#contextMenu");
      menu.querySelector('[data-p9-unit-context-status="Devam Ediyor"]').click();
      await new Promise(resolve=>setTimeout(resolve,0));
      const status={writes:window.__p9UnitContextWrites.slice(),closed:!menu.classList.contains("open")};
      const card=window.__p9UnitContextRestore.card;
      desktopSettings.rc_projects="1";
      card.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:1270,clientY:890}));
      menu.querySelector("[data-p9-unit-context-products]").click();
      const products={triggered:window.__p9ProductAction,closed:!menu.classList.contains("open")};
      await new Promise(resolve=>setTimeout(resolve,25));
      const dialog=document.querySelector("#appDialog");
      const productsDialogOpen=dialog?.open===true;
      dialog?.close("cancel");
      window.__p9ProductAction=false;
      const unitHeader=card.querySelector("header");
      unitHeader.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,0));
      const singleClick={productsOpened:window.__p9ProductAction,dialogOpen:document.querySelector("#appDialog")?.open===true};
      unitHeader.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,25));
      const doubleClick={productsOpened:window.__p9ProductAction,dialogOpen:document.querySelector("#appDialog")?.open===true,title:document.querySelector("#dialogTitle")?.textContent||""};
      document.querySelector("#appDialog")?.close("cancel");
      desktopSettings.rc_projects="0";
      const disabledEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:300,clientY:300});
      card.dispatchEvent(disabledEvent);
      const gate={prevented:disabledEvent.defaultPrevented,opened:menu.classList.contains("open")};
      const restore=window.__p9UnitContextRestore;
      loadPart9Projects=restore.oldLoadPart9Projects;
      apiFetch=restore.oldApiFetch;
      restore.card.remove();
      delete window.__p9UnitContextRestore;
      delete window.__p9UnitContextWrites;
      delete window.__p9ProductAction;
      return {status,products,productsDialogOpen,singleClick,doubleClick,gate};
    })()`);
    const statusWrite = menuActions.status.writes.find(item => item.url === "/api/desktop/table/project_units");
    const box = menuResult.bounds;
    const menuFits = box.x >= 0 && box.y >= 0 && box.x + box.width <= 1280 && box.y + box.height <= 900;
    if (!menuResult.opened || !menuResult.defaultPrevented || JSON.stringify(menuResult.actions) !== JSON.stringify(["Bekliyor", "Devam Ediyor", "Tamamlandı", "Ürünleri Yönet"]) || menuResult.checked !== "true" || !menuFits || !menuActions.status.closed || statusWrite?.body?.id !== 954 || statusWrite.body.status !== "Devam Ediyor" || statusWrite.body._action !== "update" || !menuActions.products.triggered || !menuActions.products.closed || !menuActions.productsDialogOpen || menuActions.singleClick.productsOpened || menuActions.singleClick.dialogOpen || !menuActions.doubleClick.productsOpened || !menuActions.doubleClick.dialogOpen || !menuActions.doubleClick.title.includes("Kurulu Ürünler") || menuActions.gate.prevented || menuActions.gate.opened || exceptions.length) {
      throw new Error(`Project unit context menu mismatch: ${JSON.stringify({ menuResult, menuActions, browserExceptions: exceptions.length })}`);
    }
    process.stdout.write(JSON.stringify({ ...result, projectUnitContextMenu: menuResult, projectUnitActions: menuActions, menuScreenshot, browserExceptions: exceptions.length, headless: true }) + "\n");
  } finally {
    try { socket?.close(); } catch (_) {}
    try {
      const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
      const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      for (const pid of output.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
    } catch (_) { try { browser.kill(); } catch (_) {} }
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
