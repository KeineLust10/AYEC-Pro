const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9231);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `dashboard-service-context-headless-profile-${process.pid}`);

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const targets = await response.json();
      const origin = new URL(baseUrl).origin;
      const page = targets.find(target => target.type === "page" && target.url?.startsWith(origin));
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
  try {
    const target = await waitForTarget();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
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
    const send = (method, params = {}, timeoutMs = 60000) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => {
        pending.delete(id);
        reject(new Error(`CDP command timed out: ${method}`));
      }, timeoutMs);
      pending.set(id, {
        resolve(value) { clearTimeout(timer); resolve(value); },
        reject(error) { clearTimeout(timer); reject(error); }
      });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };

    const screenshotFailures = [];
    const screenshotFallbacks = [];
    let screenshotsCaptured = 0;
    let componentScreenshotsCaptured = 0;
    let screenshotsAttempted = 0;
    async function capture(filename, setup) {
      screenshotsAttempted += 1;
      await evaluate(setup);
      await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
      await delay(50);
      const viewport = await evaluate("({ width: innerWidth, height: innerHeight })");
      try {
        const result = await send("Page.captureScreenshot", {
          format: "png",
          fromSurface: true,
          optimizeForSpeed: true,
          clip: { x: 0, y: 0, width: viewport.width, height: viewport.height, scale: 1 }
        }, 24000);
        fs.writeFileSync(path.join(outputDir, filename), Buffer.from(result.data, "base64"));
        screenshotsCaptured += 1;
      } catch (error) {
        try {
          const clip = await evaluate(`(() => {
            const candidates = Array.from(document.querySelectorAll("#contextMenu.open, .context-menu.open, .kb-context-menu, .service-list-context-menu, .service-list-context-submenu-panel, #appDialog[open], #appDialog.open, dialog[open], [role=dialog], #importPreview, [data-status-marquee]"));
            const element = candidates.find(node => {
              const rect = node.getBoundingClientRect();
              const style = getComputedStyle(node);
              return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden" && (node.id !== "importPreview" || node.childElementCount > 0);
            });
            if (!element) return null;
            const rect = element.getBoundingClientRect();
            const left = Math.max(0, Math.floor(rect.left - 16));
            const top = Math.max(0, Math.floor(rect.top - 16));
            return { x: left, y: top, width: Math.min(innerWidth - left, Math.max(1, Math.ceil(rect.width + 32))), height: Math.min(innerHeight - top, Math.max(1, Math.ceil(rect.height + 32))), scale: 1 };
          })()`);
          if (!clip) throw new Error("No visible menu or dialog to crop.");
          const result = await send("Page.captureScreenshot", {
            format: "png", fromSurface: true, optimizeForSpeed: true, clip
          }, 24000);
          const componentFilename = filename.replace(/\.png$/i, "-component.png");
          fs.writeFileSync(path.join(outputDir, componentFilename), Buffer.from(result.data, "base64"));
          componentScreenshotsCaptured += 1;
          screenshotFallbacks.push({ filename, componentFilename, error: error.message });
        } catch (fallbackError) {
          screenshotFailures.push({ filename, error: error.message, fallbackError: fallbackError.message });
        }
      }
    }

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof db !== 'undefined' && typeof navigate === 'function' && typeof render === 'function' && typeof renderDashboard === 'function'")) break;
      await delay(200);
    }
    const dashboardShortcutCards = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();document.body.classList.remove("auth-active");page="dashboard";document.body.dataset.page="dashboard";currentSector="teknik_servis";
      window.__dashboardShortcutRoutes=[];window.__dashboardShortcutNavigateOriginal=navigate;navigate=target=>window.__dashboardShortcutRoutes.push(target);render();
      window.__dashboardShortcutCards=[...document.querySelectorAll("[data-dashboard-shortcut]")].map(card=>({target:card.dataset.dashboardShortcut,title:card.querySelector("strong")?.textContent||""}));
      const grid=document.querySelector(".dashboard-shortcut-grid"),overlay=document.querySelector(".dashboard-shortcut-overlay"),gridStyle=getComputedStyle(grid),rect=grid.getBoundingClientRect(),overlayRect=overlay.getBoundingClientRect();
      return {cards:window.__dashboardShortcutCards,gridColumns:gridStyle.gridTemplateColumns.trim().split(" ").filter(Boolean).length,gridTemplateColumns:gridStyle.gridTemplateColumns,gridWidth:Math.round(rect.width),overlayWidth:Math.round(overlayRect.width),overlayX:Math.round(overlayRect.x),overlayHeight:Math.round(overlayRect.height),overlayBackground:getComputedStyle(overlay).backgroundColor,cardBackground:getComputedStyle(document.querySelector(".dashboard-shortcut-card")).backgroundColor};
    })()`);
    if(dashboardShortcutCards.cards.length!==12||dashboardShortcutCards.gridColumns!==2||dashboardShortcutCards.overlayBackground!=="rgb(8, 14, 26)"||dashboardShortcutCards.cardBackground!=="rgb(13, 24, 41)")throw new Error(`Dashboard shortcut layout or palette mismatch: ${JSON.stringify(dashboardShortcutCards)}`);
    const dashboardUnlinkedDeviceParity = await evaluate(`(() => {
      const previousCustomers=db.customers,previousDevices=db.serviceDevices;
      db.customers=[{id:71,name:"Linked Customer",phone:"5550000001",balances:{TRY:-12},services:[{id:70,no:"SRV-LINKED",device:"Laptop",status:"Tamirde"}]}];
      db.serviceDevices=[
        {id:70,no:"SRV-LINKED",tracking_no:"SRV-LINKED",customer_id:71,customer_name:"Linked Customer",device_brand:"Brand",device_model:"Laptop",status:"Tamirde"},
        {id:71,no:"SRV-UNLINKED",tracking_no:"SRV-UNLINKED",customer_id:null,customer_name:"Walk-in",device_type:"Phone",device_model:"Model X",fault_description:"Screen issue",status:"Bekliyor"}
      ];
      const rows=dashboardServices(),[customer,service]=findService("SRV-UNLINKED");
      serviceDetailDialog(customer,service);
      const result={rowCount:rows.length,unlinked:rows.find(row=>row.no==="SRV-UNLINKED"),detailOpen:document.querySelector("#appDialog")?.open||false,detailText:document.querySelector("#dialogBody")?.textContent||""};
      db.customers=previousCustomers;db.serviceDevices=previousDevices;
      return result;
    })()`);
    if(dashboardUnlinkedDeviceParity.rowCount!==2||dashboardUnlinkedDeviceParity.unlinked?.customer!=="Walk-in"||dashboardUnlinkedDeviceParity.unlinked?.note!=="Screen issue"||!dashboardUnlinkedDeviceParity.detailOpen||!dashboardUnlinkedDeviceParity.detailText.includes("Walk-in")||!dashboardUnlinkedDeviceParity.detailText.includes("Screen issue"))throw new Error(`Dashboard unlinked device parity mismatch: ${JSON.stringify(dashboardUnlinkedDeviceParity)}`);
    await capture("dashboard-unlinked-device-detail-headless.png", "true");
    await evaluate('document.querySelector("#appDialog")?.close()');
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 1024, deviceScaleFactor: 1, mobile: false });
    await capture("dashboard-shortcuts-initial-headless.png", "true");
    await evaluate('(()=>{const style=document.createElement("style");style.id="dashboardShortcutIsolationAudit";style.textContent="#appShell{display:block!important;min-height:0!important;height:auto!important;padding:0!important}#appShell>.topbar,#sidebar,#shellStatusBar{display:none!important}.main{display:block!important;min-height:0!important;overflow:visible!important}#content{padding:0!important;min-height:0!important;overflow:visible!important}.dashboard-shortcut-overlay{inset:0!important;right:0!important;width:100vw!important;max-width:100vw!important;padding:24px 28px 28px!important;border-radius:16px!important}body{overflow:hidden!important}";document.head.appendChild(style)})()');
    const isolatedShortcutColumns = await evaluate('getComputedStyle(document.querySelector(".dashboard-shortcut-grid")).gridTemplateColumns.trim().split(" ").filter(Boolean).length');
    if(isolatedShortcutColumns!==3)throw new Error("Isolated dashboard shortcut columns mismatch: "+isolatedShortcutColumns);
    await capture("dashboard-shortcuts-isolated-headless.png", "true");
    await evaluate('document.querySelector("#dashboardShortcutIsolationAudit")?.remove()');
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    const dashboardShortcutFlow = await evaluate(`(async () => {
      const cards=window.__dashboardShortcutCards;
      const results=[];
      for(const card of cards){
        if(!document.querySelector(".dashboard-shortcut-overlay"))document.querySelector("[data-dashboard-shortcuts-toggle]")?.click();
        const button=[...document.querySelectorAll("[data-dashboard-shortcut]")].find(item=>item.dataset.dashboardShortcut===card.target&&(item.querySelector("strong")?.textContent||"")===card.title);
        if(!button)throw new Error("Dashboard shortcut disappeared: "+card.title);
        button.click();await new Promise(resolve=>setTimeout(resolve,20));
        const dialog=document.querySelector("#appDialog"),dialogOpen=Boolean(dialog?.open),dialogTitle=document.querySelector("#dialogTitle")?.textContent||"";
        if(dialogOpen)document.querySelector("#dialogCancel")?.click();
        results.push({target:card.target,title:card.title,dialogOpen,dialogTitle,overlayClosed:!document.querySelector(".dashboard-shortcut-overlay")});
      }
      navigate=window.__dashboardShortcutNavigateOriginal;delete window.__dashboardShortcutNavigateOriginal;delete window.__dashboardShortcutCards;
      return {cards,results,routes:window.__dashboardShortcutRoutes};
    })()`);
    if(dashboardShortcutFlow.cards.length!==12||dashboardShortcutFlow.results.some(item=>!item.overlayClosed)||dashboardShortcutFlow.results.filter(item=>item.target==="new-service").some(item=>!item.dialogOpen)||dashboardShortcutFlow.results.find(item=>item.target==="new-customer")?.dialogOpen!==true||JSON.stringify(dashboardShortcutFlow.routes)!==JSON.stringify(["services","technician","customers","finance","stock","appointments","offers","finance","backup"]))throw new Error(`Dashboard shortcut flow mismatch: ${JSON.stringify(dashboardShortcutFlow)}`);
    await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "dashboard";
      page = "dashboard";
      db.settings.contextMenu = true;
      currentAuthUser = { role: "Admin" };
      const service = { id: 77, no: "SRV-77", device: "Laptop", device_type: "Laptop", status: "Bekliyor", note: "Fixture", customerId: 501, customer_name: "Fixture", customer_contact: "5550001234" };
      db.customers = [{ id: 501, name: "Fixture Customer", phone: "5550001234", services: [service] }];
      const host = document.querySelector("#content");
      if (host) host.innerHTML = '<section class="card" style="margin:40px;padding:24px"><h1>Dashboard context menu audit</h1><p>Offscreen fixture for desktop menu parity.</p></section>';
      showContext({ preventDefault() {}, clientX: 280, clientY: 220, currentTarget: document.querySelector("#content") }, "service", "SRV-77");
    })()`);
    const root = await evaluate(`(() => {
      const menu = document.querySelector(".service-list-context-menu");
      if (!menu) throw new Error("Dashboard service context menu was not rendered.");
      const actions = Array.from(menu.querySelectorAll("[data-service-context]"), item => item.dataset.serviceContext);
      const texts = Array.from(menu.querySelectorAll("button"), item => item.innerText.trim());
      return { actions, texts, width: Math.round(menu.getBoundingClientRect().width), height: Math.round(menu.getBoundingClientRect().height) };
    })()`);
    const expected = ["technician", "form", "edit", "close", "customer", "customer-info", "sms", "whatsapp", "payment", "photos", "print-detailed", "invoice", "delete"];
    if (JSON.stringify(root.actions) !== JSON.stringify(expected)) throw new Error(`Unexpected dashboard menu actions: ${JSON.stringify(root.actions)}`);
    const appLockPrompt = await evaluate(`(async()=>{
      const original={applicationStarted,currentAuthUser,apiFetch,hydrateDesktop,loadParityState,renderNav,navigate,requestedInitialPage,render,checkScheduledAlerts,renderLogin};
      const harness={original,requests:[],pending:null};window.__appLockHarness=harness;
      applicationStarted=false;apiFetch=async(url,options={})=>{if(url==="/api/desktop/security-settings")return {app_lock_active:true,app_password_configured:true};if(url==="/api/desktop/security-settings/verify-app-lock"){harness.requests.push({url,method:options.method,payload:JSON.parse(options.body)});return {ok:true,required:true};}if(url==="/api/auth/logout"){harness.requests.push({url,method:options.method});return {ok:true};}throw new Error("Unexpected app-lock audit request: "+url)};
      hydrateDesktop=async()=>({settings:{},internal_settings:{}});loadParityState=async()=>{};renderNav=()=>{};navigate=()=>{};requestedInitialPage=()=>"dashboard";render=()=>{};checkScheduledAlerts=()=>{};renderLogin=()=>{};
      harness.pending=startApplication();await new Promise(resolve=>setTimeout(resolve,0));
      const dialog=document.querySelector("#appDialog");return {open:Boolean(dialog?.open),title:document.querySelector("#dialogTitle")?.textContent,inputType:document.querySelector('#dialogBody input[name="password"]')?.type,cancelLabel:document.querySelector("#dialogCancel")?.textContent};
    })()`);
    if(!appLockPrompt.open||!String(appLockPrompt.title).includes("Kilitli")||appLockPrompt.inputType!=="password")throw new Error(`Application lock prompt mismatch: ${JSON.stringify(appLockPrompt)}`);
    await capture("application-lock-prompt-current-headless.png", "true");
    const appLockFlow = await evaluate(`(async()=>{
      const harness=window.__appLockHarness,input=document.querySelector('#dialogBody input[name="password"]');input.value="fixture-app-password";document.querySelector("#dialogForm").requestSubmit();await harness.pending;
      const accepted={request:harness.requests.find(item=>item.url==="/api/desktop/security-settings/verify-app-lock"),started:applicationStarted,dialogClosed:!document.querySelector("#appDialog")?.open};
      applicationStarted=false;const cancelPending=startApplication();await new Promise(resolve=>setTimeout(resolve,0));document.querySelector("#dialogCancel").click();await cancelPending;
      const cancelled={logout:harness.requests.some(item=>item.url==="/api/auth/logout"),started:applicationStarted};
      applicationStarted=harness.original.applicationStarted;currentAuthUser=harness.original.currentAuthUser;apiFetch=harness.original.apiFetch;hydrateDesktop=harness.original.hydrateDesktop;loadParityState=harness.original.loadParityState;renderNav=harness.original.renderNav;navigate=harness.original.navigate;requestedInitialPage=harness.original.requestedInitialPage;render=harness.original.render;checkScheduledAlerts=harness.original.checkScheduledAlerts;renderLogin=harness.original.renderLogin;delete window.__appLockHarness;
      return {accepted,cancelled};
    })()`);
    if(appLockFlow.accepted.request?.payload?.password!=="fixture-app-password"||appLockFlow.accepted.request?.method!=="POST"||!appLockFlow.accepted.started||!appLockFlow.accepted.dialogClosed||!appLockFlow.cancelled.logout||appLockFlow.cancelled.started)throw new Error(`Application lock flow mismatch: ${JSON.stringify(appLockFlow)}`);
    const technicianLockPrompt = await evaluate(`(async()=>{
      const customer=db.customers[0],service=customer?.services?.[0];
      window.__technicianLockHarness={originalApiFetch:apiFetch,requests:[],pending:null};const harness=window.__technicianLockHarness;
      apiFetch=async(url,options={})=>{if(url==="/api/desktop/security-settings")return {tech_lock_active:true,tech_password_configured:true};if(url==="/api/desktop/security-settings/verify-tech-lock"){harness.requests.push({url,method:options.method,payload:JSON.parse(options.body)});return {ok:true,required:true};}throw new Error("Unexpected technician-lock audit request: "+url)};
      harness.pending=technicianDialog(customer,service);await new Promise(resolve=>setTimeout(resolve,0));
      const dialog=document.querySelector("#appDialog");return {open:Boolean(dialog?.open),title:document.querySelector("#dialogTitle")?.textContent,inputType:document.querySelector('#dialogBody input[name="password"]')?.type,cancelLabel:document.querySelector("#dialogCancel")?.textContent};
    })()`);
    if(!technicianLockPrompt.open||!String(technicianLockPrompt.title).includes("Teknisyen Paneli Kilitli")||technicianLockPrompt.inputType!=="password")throw new Error(`Technician lock prompt mismatch: ${JSON.stringify(technicianLockPrompt)}`);
    await capture("technician-lock-prompt-current-headless.png", "true");
    const technicianLockFlow = await evaluate(`(async()=>{
      const harness=window.__technicianLockHarness,input=document.querySelector('#dialogBody input[name="password"]');input.value="fixture-tech-password";document.querySelector("#dialogForm").requestSubmit();await harness.pending;
      const accepted={request:harness.requests[0],technicianDialogOpen:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent};document.querySelector("#dialogCancel")?.click();
      const beforeCancelRequests=harness.requests.length,cancelPending=technicianDialog(db.customers[0],db.customers[0].services[0]);await new Promise(resolve=>setTimeout(resolve,0));document.querySelector("#dialogCancel").click();await cancelPending;
      const cancelled={noVerification:harness.requests.length===beforeCancelRequests,dialogClosed:!document.querySelector("#appDialog")?.open};apiFetch=harness.originalApiFetch;delete window.__technicianLockHarness;
      return {accepted,cancelled};
    })()`);
    if(technicianLockFlow.accepted.request?.url!=="/api/desktop/security-settings/verify-tech-lock"||technicianLockFlow.accepted.request?.method!=="POST"||technicianLockFlow.accepted.request?.payload?.password!=="fixture-tech-password"||!technicianLockFlow.accepted.technicianDialogOpen||!String(technicianLockFlow.accepted.title).includes("SRV-77")||!technicianLockFlow.cancelled.noVerification||!technicianLockFlow.cancelled.dialogClosed)throw new Error(`Technician lock flow mismatch: ${JSON.stringify(technicianLockFlow)}`);
    const technicianPaymentBankFlow = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      const originalHydrateDesktop = hydrateDesktop;
      const requests = [];
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/security-settings") return { tech_lock_active: false };
        if (url === "/api/desktop/table/bank_accounts?limit=500") return { rows: [{ id: 61, bank_name: "Fixture Bank", is_active: 1, is_deleted: 0 }] };
        if (url === "/api/desktop/technician/update") { requests.push(JSON.parse(options.body)); return { finance_id: 81 }; }
        return { rows: [] };
      };
      hydrateDesktop = async () => {};
      const customer = db.customers[0], service = customer.services[0];
      await technicianDialog(customer, service);
      const bank = document.querySelector('#dialogBody select[name="bank_account_id"]');
      const method = document.querySelector('#dialogBody select[name="payment_method"]');
      const collect = document.querySelector('#dialogBody input[name="collect_payment"]');
      const payment = document.querySelector('#dialogBody input[name="payment_amount"]');
      const result = { banks: Array.from(bank.options, option => ({ value: option.value, label: option.textContent })), methods: Array.from(method.options, option => option.textContent) };
      bank.value = "61"; method.value = "Havale/EFT"; collect.checked = true; collect.dispatchEvent(new Event("change", { bubbles: true })); payment.value = "42.5";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 30));
      result.request = requests[0]; result.closed = !document.querySelector("#appDialog")?.open;
      apiFetch = originalApiFetch; hydrateDesktop = originalHydrateDesktop;
      return result;
    })()`);
    if (!technicianPaymentBankFlow.banks.some(option => option.value === "61" && option.label === "Fixture Bank") || !technicianPaymentBankFlow.methods.includes("Havale/EFT") || technicianPaymentBankFlow.request?.bank_account_id !== 61 || technicianPaymentBankFlow.request?.payment_method !== "Havale/EFT" || technicianPaymentBankFlow.request?.payment_amount !== 42.5 || !technicianPaymentBankFlow.closed) throw new Error(`Technician bank collection flow mismatch: ${JSON.stringify(technicianPaymentBankFlow)}`);
    if (process.env.AYEC_TECHNICIAN_BANK_AUDIT_ONLY === "1") {
      console.log(JSON.stringify({ technicianPaymentBankFlow, browserExceptions: exceptions.length, headless: true }));
      return;
    }
    const roles = await evaluate(`(() => {
      const out = {};
      for (const role of ["Admin", "Teknisyen", "Muhasebe", "Personel"]) {
        document.querySelector(".service-list-context-menu")?.remove();
        document.querySelectorAll(".service-list-context-submenu-panel").forEach(node=>node.remove());
        currentAuthUser = { role };
        showContext({ preventDefault(){}, clientX:280, clientY:220, currentTarget:document.querySelector("#content") }, "service", "SRV-77");
        out[role] = Array.from(document.querySelectorAll(".service-list-context-menu:not(.service-list-context-submenu-panel) [data-service-context]"), item=>item.dataset.serviceContext);
      }
      document.querySelector(".service-list-context-menu")?.remove();
      document.querySelectorAll(".service-list-context-submenu-panel").forEach(node=>node.remove());
      currentAuthUser = { role: "Admin" };
      return out;
    })()`);
    if (roles.Teknisyen.includes("close") !== true || roles.Teknisyen.includes("delete") || roles.Muhasebe.includes("sms") !== true || roles.Muhasebe.includes("edit") || roles.Personel.includes("delete") || roles.Personel.includes("sms")) {
      throw new Error(`Unexpected context-menu role matrix: ${JSON.stringify(roles)}`);
    }
    await evaluate(`showContext({preventDefault(){},clientX:280,clientY:220,currentTarget:document.querySelector("#content")},"service","SRV-77")`);
    await capture("dashboard-service-context-current-headless.png", "true");
    const fieldMenu = await evaluate(`(() => {
      const event = { preventDefault(){ this.prevented = true; }, clientX: 1279, clientY: 899, currentTarget: document.querySelector("#content") };
      showContext(event, "field-personnel", "missing-fixture-person");
      const menu = document.querySelector("#contextMenu");
      const rect = menu.getBoundingClientRect();
      return { open: menu.classList.contains("open"), prevented: event.prevented, text: menu.textContent.trim(), action: menu.querySelector("[data-context-action]")?.dataset.contextAction, rect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom } };
    })()`);
    if (!fieldMenu.open || !fieldMenu.prevented || fieldMenu.action !== "field-personnel-finish" || !fieldMenu.text.includes("G\u00f6revi Tamamla / Bo\u015fa \u00c7\u0131kar")) throw new Error(`Field personnel menu mismatch: ${JSON.stringify(fieldMenu)}`);
    if (fieldMenu.rect.left < 0 || fieldMenu.rect.top < 0 || fieldMenu.rect.right > 1280 || fieldMenu.rect.bottom > 900) throw new Error(`Field personnel menu exceeded viewport bounds: ${JSON.stringify(fieldMenu.rect)}`);
    await capture("field-personnel-context-menu-current-headless.png", "true");
    await evaluate(`document.querySelector("#contextMenu [data-context-action=field-personnel-finish]")?.click()`);
    const fieldMenuDismissed = await evaluate(`!document.querySelector("#contextMenu").classList.contains("open")`);
    if (!fieldMenuDismissed) throw new Error("Field personnel context action did not dismiss its menu.");
    const stockMenu = await evaluate(`(() => {
      page = "stock";
      document.body.dataset.page = "stock";
      db.stock = [{ id: 88, name: "Context Fixture", code: "CF-88", qty: 4, currency: "TRY" }];
      const event = { preventDefault(){ this.prevented = true; }, clientX: 220, clientY: 220, currentTarget: document.querySelector("#content") };
      showContext(event, "stock", "88");
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.prevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), separators: menu.querySelectorAll(".context-menu-separator").length };
    })()`);
    const expectedStockActions = ["movement", "edit-product", "stock-photo", "stock-pdf", "stock-print", "stock-excel", "delete-product"];
    if (!stockMenu.open || !stockMenu.prevented || JSON.stringify(stockMenu.actions) !== JSON.stringify(expectedStockActions) || stockMenu.separators !== 2) throw new Error(`Stock context menu mismatch: ${JSON.stringify(stockMenu)}`);
    await capture("stock-context-menu-current-headless.png", "true");
    const stockDeleteDialog = await evaluate(`(() => {
      document.querySelector('#contextMenu [data-context-action="delete-product"]')?.click();
      return { open: !!document.querySelector("#appDialog")?.open, title: document.querySelector("#dialogTitle")?.textContent, inputType: document.querySelector("#stockDeletePassword")?.type };
    })()`);
    if (!stockDeleteDialog.open || stockDeleteDialog.title !== "Stok Silme Onay\u0131" || stockDeleteDialog.inputType !== "password") throw new Error(`Stock delete confirmation mismatch: ${JSON.stringify(stockDeleteDialog)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const stockDeleteCancelled = await evaluate('!document.querySelector("#appDialog")?.open');
    if (!stockDeleteCancelled) throw new Error("Stock delete confirmation did not cancel cleanly.");
    const bankMenu = await evaluate(`(() => {
      page = "banks";
      document.body.dataset.page = "banks";
      currentAuthUser = { role: "Admin" };
      ayecBankAccounts = [{ id: 11, bank_name: "Fixture Bank", current_balance: 2500, currency: "TRY", is_active: 1 }];
      ayecBankRenderData = rows => { ayecBankAccounts = rows || []; };
      const event = { preventDefault(){ this.prevented = true; }, clientX: 240, clientY: 260, currentTarget: document.querySelector("#content") };
      showContext(event, "bank-account", "11");
      const menu = document.querySelector("#contextMenu");
      const manager = { open: menu.classList.contains("open"), prevented: event.prevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), button => button.dataset.contextAction), disabled: Array.from(menu.querySelectorAll("[data-context-action]"), button => button.disabled), separators: menu.querySelectorAll(".context-menu-separator").length };
      menu.classList.remove("open");
      currentAuthUser = { role: "Teknisyen" };
      showContext(event, "bank-account", "11");
      const staffMenu = document.querySelector("#contextMenu");
      return { manager, staffDisabled: Array.from(staffMenu.querySelectorAll("[data-context-action]"), button => button.disabled) };
    })()`);
    const expectedBankActions = ["bank-detail", "bank-edit", "bank-transfer", "bank-toggle", "bank-delete", "bank-bulk-toggle", "bank-bulk-delete"];
    if (!bankMenu.manager.open || !bankMenu.manager.prevented || JSON.stringify(bankMenu.manager.actions) !== JSON.stringify(expectedBankActions) || bankMenu.manager.disabled.some(Boolean) || bankMenu.manager.separators !== 1 || JSON.stringify(bankMenu.staffDisabled) !== JSON.stringify([false, true, true, true, true, true, true])) throw new Error(`Bank account menu mismatch: ${JSON.stringify(bankMenu)}`);
    await capture("bank-account-context-menu-current-headless.png", "true");
    const installmentMenu = await evaluate(`(async () => {
      page = "loans";
      window.__loanAuditFetch = window.fetch;
      window.fetch = async (url, init = {}) => {
        const value = String(url);
        if (value.includes("table/loans")) return new Response(JSON.stringify({ rows: [{ id: 21, bank_name: "Fixture Bank", loan_type: "Business", amount: 10000, status: "Aktif", interest_rate: 5 }], columns: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
        if (value.includes("table/loan_installments")) return new Response(JSON.stringify({ rows: [{ id: 31, loan_id: 21, installment_no: 1, total_amount: 1000, status: "Bekliyor", due_date: "2026-11-01" }, { id: 32, loan_id: 21, installment_no: 2, total_amount: 1000, status: "\\u00d6dendi", due_date: "2026-12-01", paid_date: "2026-11-01" }], columns: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
        return window.__loanAuditFetch(url, init);
      };
      document.body.dataset.page = "loans";
      render();
      await new Promise(resolve => setTimeout(resolve, 300));
      const host = document.querySelector("#content");
      const menu = document.querySelector("#contextMenu");
      const loanTarget = host.querySelector("[data-loan-context-row]");
      const loanEvent = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 240 });
      loanTarget.dispatchEvent(loanEvent);
      const loan = { prevented: loanEvent.defaultPrevented, type: menu.dataset.loanContextType, id: menu.dataset.loanContextId, actions: Array.from(menu.querySelectorAll("[data-loan-context-action]"), item => item.dataset.loanContextAction), separators: menu.querySelectorAll("hr").length, text: menu.innerText.trim() };
      const openFor = id => {
        menu.innerHTML = "";
        const target = host.querySelector('[data-installment-row="' + id + '"]');
        const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 240 });
        target.dispatchEvent(event);
        return { prevented: event.defaultPrevented, type: menu.dataset.loanContextType, id: menu.dataset.loanContextId, actions: Array.from(menu.querySelectorAll("[data-loan-context-action]"), item => item.dataset.loanContextAction), text: menu.innerText.trim() };
      };
      const result = { loan, unpaid: openFor(31), paid: openFor(32), rows: host.querySelectorAll("[data-installment-row]").length };
      return result;
    })()`);
    const expectedLoanActions = ["edit", "bulk", "details", "add-installment", "cancel", "delete"];
    if (installmentMenu.rows !== 2 || !installmentMenu.loan.prevented || installmentMenu.loan.type !== "loan" || installmentMenu.loan.id !== "21" || JSON.stringify(installmentMenu.loan.actions) !== JSON.stringify(expectedLoanActions) || installmentMenu.loan.separators !== 1 || !installmentMenu.unpaid.prevented || installmentMenu.unpaid.type !== "installment" || installmentMenu.unpaid.id !== "31" || JSON.stringify(installmentMenu.unpaid.actions) !== JSON.stringify(["pay", "details"]) || !installmentMenu.unpaid.text.includes("Taksiti \u00d6dendi Olarak \u0130\u015faretle") || installmentMenu.paid.type !== "installment" || installmentMenu.paid.id !== "32" || JSON.stringify(installmentMenu.paid.actions) !== JSON.stringify(["unpay", "details"]) || !installmentMenu.paid.text.includes("\u00d6deme Durumunu Geri Al")) throw new Error(`Loan context menu mismatch: ${JSON.stringify(installmentMenu)}`);
    await evaluate(`(() => {const target=document.querySelector("[data-loan-context-row]");target.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:280,clientY:240}));})()`);
    await capture("loan-contract-context-menu-current-headless.png", "true");
    await evaluate(`(() => {const target=document.querySelector('[data-installment-row="31"]');target.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:280,clientY:240}));})()`);
    await capture("loan-installment-context-menu-current-headless.png", "true");
    await evaluate(`document.querySelector('#contextMenu [data-loan-context-action="pay"]')?.click()`);
    const loanConfirmation = await evaluate(`({ open: document.querySelector("#appDialog")?.open || false, title: document.querySelector("#dialogTitle")?.textContent || "" })`);
    if (!loanConfirmation.open || loanConfirmation.title !== "Taksiti \u00d6dendi Olarak \u0130\u015faretle") throw new Error(`Loan payment confirmation mismatch: ${JSON.stringify(loanConfirmation)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const loanConfirmationCancelled = await evaluate('document.querySelector("#appDialog")?.open === false');
    if (!loanConfirmationCancelled) throw new Error("Loan payment confirmation did not cancel cleanly.");
    await evaluate('document.querySelector("#contextMenu")?.classList.remove("open");window.fetch=window.__loanAuditFetch||window.fetch;currentAuthUser={role:"Admin"};page="dashboard";document.body.dataset.page="dashboard"');
    const externalMenu = await evaluate(`(async () => {
      window.__externalAuditFetch = window.fetch;
      window.fetch = async (url, init = {}) => {
        if (String(url).includes("table/external_warranty_tracking")) return new Response(JSON.stringify({ rows: [{ id: 41, internal_tracking_no: "EXT-41", external_service_name: "Fixture Service", external_service_no: "FS-41", customer_name: "Fixture Customer", product_name: "Laptop", sent_date: "2026-10-01", status: "Kargoya Verildi", warranty: "Garanti", amount: 500 }], columns: [] }), { status: 200, headers: { "Content-Type": "application/json" } });
        return window.__externalAuditFetch(url, init);
      };
      page = "logistics";
      document.body.dataset.page = "logistics";
      document.querySelector("#content").innerHTML = genericShell({ table: "logistics", title: "Logistics", description: "Offscreen fixture" });
      document.querySelector("[data-external-refresh]")?.click();
      await new Promise(resolve => setTimeout(resolve, 300));
      const row = document.querySelector('[data-external-row="41"]');
      if (!row) throw new Error("External tracking fixture row did not render.");
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 300, clientY: 260 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, id: menu.dataset.targetId, actions: Array.from(menu.querySelectorAll("[data-external-context]"), item => item.dataset.externalContext), text: menu.innerText.trim() };
    })()`);
    const expectedExternalActions = ["edit", "delete", "gallery", "export"];
    if (!externalMenu.open || !externalMenu.prevented || externalMenu.id !== "41" || JSON.stringify(externalMenu.actions) !== JSON.stringify(expectedExternalActions) || !externalMenu.text.includes("Foto\u011Fraf Galerisi")) throw new Error(`External tracking menu mismatch: ${JSON.stringify(externalMenu)}`);
    await capture("external-tracking-context-menu-current-headless.png", "true");
    await evaluate('document.querySelector("#contextMenu [data-external-context=delete]")?.click()');
    const externalDeleteDialog = await evaluate(`({ open: document.querySelector("#appDialog")?.open || false, title: document.querySelector("#dialogTitle")?.textContent || "", cancel: document.querySelector("#dialogCancel")?.textContent || "" })`);
    if (!externalDeleteDialog.open || externalDeleteDialog.title !== "Harici Takip Kayd\u0131n\u0131 Sil" || externalDeleteDialog.cancel !== "Hay\u0131r") throw new Error(`External tracking delete dialog mismatch: ${JSON.stringify(externalDeleteDialog)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const externalDeleteCancelled = await evaluate('document.querySelector("#appDialog")?.open === false');
    if (!externalDeleteCancelled) throw new Error("External tracking delete confirmation did not cancel cleanly.");
    await evaluate('document.querySelector("#contextMenu")?.classList.remove("open");window.fetch=window.__externalAuditFetch||window.fetch;page="dashboard";document.body.dataset.page="dashboard"');
    const stockLocationMenu = await evaluate(`(() => {
      page = "stock-locations";
      document.body.dataset.page = "stock-locations";
      window.__stockLocationAuditState = { stock: db.stock, stockLocations: db.stockLocations, stockLocationBalances: db.stockLocationBalances, stockTransferHistory: db.stockTransferHistory, customers: db.customers };
      db.stock = [{ id: 88, name: "Fixture SSD", code: "SSD-88", unit: "Adet", quantity: 5, currency: "TRY" }];
      db.stockLocations = [{ id: 6, name: "Fixture Warehouse", location_type: "warehouse", quantity: 5 }];
      db.stockLocationBalances = [{ part_id: 88, location_id: 6, location_name: "Fixture Warehouse", location_type: "warehouse", product_name: "Fixture SSD", product_code: "SSD-88", barcode: "BAR-88", unit: "Adet", quantity: 5, reserved_quantity: 1, min_quantity: 1 }];
      db.stockTransferHistory = [];
      db.customers = [...(db.customers || []), { id: 987654, name: "Fixture Customer", services: [{ no: "SRV-501", status: "Tamirde", device: "Laptop" }] }];
      document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-kind="stock-location" data-id="88" data-location-id="6"><td>Fixture SSD</td></tr></tbody></table></section>';
      const row = document.querySelector('tr[data-kind="stock-location"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 250, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), text: menu.innerText.trim() };
    })()`);
    const expectedStockLocationActions = ["location-edit", "location-use", "location-transfer"];
    if (!stockLocationMenu.open || !stockLocationMenu.prevented || JSON.stringify(stockLocationMenu.actions) !== JSON.stringify(expectedStockLocationActions)) throw new Error(`Stock location menu mismatch: ${JSON.stringify(stockLocationMenu)}`);
    await capture("stock-location-context-menu-current-headless.png", "true");
    await evaluate('document.querySelector("#contextMenu [data-context-action=location-use]")?.click()');
    const stockLocationUse = await evaluate(`({ open: document.querySelector("#appDialog")?.open || false, fields: Array.from(document.querySelectorAll("#dialogBody [name]"), field => field.name) })`);
    if (!stockLocationUse.open || !stockLocationUse.fields.includes("tracking_no")) throw new Error(`Stock location use dialog mismatch: ${JSON.stringify(stockLocationUse)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const stockLocationUseCancelled = await evaluate('document.querySelector("#appDialog")?.open === false');
    if (!stockLocationUseCancelled) throw new Error("Stock location use dialog did not cancel cleanly.");
    await evaluate('Object.assign(db,window.__stockLocationAuditState);delete window.__stockLocationAuditState;page="dashboard";document.body.dataset.page="dashboard"');
    const vehicleMaintenanceMenu = await evaluate(`(() => {
      page = "vehicle-maintenance";
      document.body.dataset.page = "vehicle-maintenance";
      vehicleMaintenanceRows = [{ id: 61, customer_name: "Fixture Customer", vehicle_plate: "34TEST61", model: "Fixture Vehicle" }];
      document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-kind="vehicle-maintenance" data-id="61"><td>Fixture Vehicle</td></tr></tbody></table></section>';
      const row = document.querySelector('tr[data-kind="vehicle-maintenance"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), separators: menu.querySelectorAll("hr.context-menu-separator").length, text: menu.innerText.trim() };
    })()`);
    const expectedMaintenanceActions = ["maintenance-open", "maintenance-photos", "maintenance-history", "maintenance-excel", "maintenance-pdf", "maintenance-print"];
    if (!vehicleMaintenanceMenu.open || !vehicleMaintenanceMenu.prevented || JSON.stringify(vehicleMaintenanceMenu.actions) !== JSON.stringify(expectedMaintenanceActions) || vehicleMaintenanceMenu.separators !== 1) throw new Error(`Vehicle maintenance context menu mismatch: ${JSON.stringify(vehicleMaintenanceMenu)}`);
    await capture("vehicle-maintenance-context-menu-current-headless.png", "true");
    const maintenancePrint = await evaluate(`(() => {let calls=0;const original=window.print;window.print=()=>{calls++};document.querySelector('#contextMenu [data-context-action="maintenance-print"]')?.click();window.print=original;return {calls,closed:!document.querySelector("#contextMenu").classList.contains("open")};})()`);
    if (maintenancePrint.calls !== 1 || !maintenancePrint.closed) throw new Error(`Vehicle maintenance print action mismatch: ${JSON.stringify(maintenancePrint)}`);
    const maintenanceContextDispatch = await evaluate(`(() => {
      const names = ["maintenanceDialog", "maintenancePhotoGallery", "maintenanceHistoryDialog", "exportVehicleMaintenanceExcel", "exportVehicleMaintenancePdf", "print"];
      const originals = Object.fromEntries(names.map(name => [name, window[name]]));
      const calls = [];
      try {
        for (const name of names) window[name] = (...args) => calls.push({ name, recordId: args[0]?.id ?? null });
        const row = document.querySelector('tr[data-kind="vehicle-maintenance"]');
        for (const action of ["maintenance-open", "maintenance-photos", "maintenance-history", "maintenance-excel", "maintenance-pdf", "maintenance-print"]) {
          row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 }));
          document.querySelector('#contextMenu [data-context-action="' + action + '"]')?.click();
        }
        return { calls, menuClosed: !document.querySelector("#contextMenu").classList.contains("open") };
      } finally {
        for (const name of names) window[name] = originals[name];
      }
    })()`);
    const expectedMaintenanceDispatch = ["maintenanceDialog", "maintenancePhotoGallery", "maintenanceHistoryDialog", "exportVehicleMaintenanceExcel", "exportVehicleMaintenancePdf", "print"];
    if (!maintenanceContextDispatch.menuClosed || JSON.stringify(maintenanceContextDispatch.calls.map(call => call.name)) !== JSON.stringify(expectedMaintenanceDispatch) || maintenanceContextDispatch.calls.slice(0, 3).some(call => call.recordId !== 61)) throw new Error(`Vehicle maintenance context dispatch mismatch: ${JSON.stringify(maintenanceContextDispatch)}`);
    const maintenanceWhatsAppPhoneWarning = await evaluate(`(() => {
      offerMaintenanceWhatsApp({ customer_name: "Fixture Customer", customer_phone: "no digits", vehicle_plate: "34 TEST 61", important_items: ["Oil"] }, {});
      return { open: document.querySelector("#appDialog")?.open || false, warning: Array.from(document.querySelectorAll(".toast"), item => item.textContent).join(" ") };
    })()`);
    if (maintenanceWhatsAppPhoneWarning.open || !maintenanceWhatsAppPhoneWarning.warning.includes("WhatsApp")) throw new Error(`Vehicle maintenance phone warning mismatch: ${JSON.stringify(maintenanceWhatsAppPhoneWarning)}`);
    await capture("vehicle-maintenance-whatsapp-phone-warning-current-headless.png", "true");
    await evaluate('document.querySelectorAll(".toast").forEach(node => node.remove())');
    const maintenanceWhatsAppPrompt = await evaluate(`(() => {
      window.__maintenanceWhatsAppUrl = "";
      window.open = url => { window.__maintenanceWhatsAppUrl = url; return null; };
      offerMaintenanceWhatsApp({ customer_name: "Fixture Customer", customer_phone: "05550000061", vehicle_plate: "34 TEST 61", important_items: ["Oil", "Filter", "Belt", "Brakes", "Battery", "Tires"] }, { appointment_date: "2026-11-01", appointment_time: "14:30" });
      return { open: document.querySelector("#appDialog")?.open || false, title: document.querySelector("#dialogTitle")?.textContent || "", body: document.querySelector("#dialogBody")?.textContent || "", cancel: document.querySelector("#dialogCancel")?.textContent || "", submit: document.querySelector("#dialogSubmit")?.textContent || "" };
    })()`);
    if (!maintenanceWhatsAppPrompt.open || !maintenanceWhatsAppPrompt.title.startsWith("Randevu Mesaj") || !maintenanceWhatsAppPrompt.body.includes("WhatsApp randevu mesaj") || !maintenanceWhatsAppPrompt.cancel || !maintenanceWhatsAppPrompt.submit.startsWith("WhatsApp'")) throw new Error(`Vehicle maintenance WhatsApp prompt mismatch: ${JSON.stringify(maintenanceWhatsAppPrompt)}`);
    await capture("vehicle-maintenance-whatsapp-confirm-current-headless.png", "true");
    const maintenanceWhatsAppCancelled = await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); return { closed: document.querySelector("#appDialog")?.open === false, url: window.__maintenanceWhatsAppUrl }; })()`);
    if (!maintenanceWhatsAppCancelled.closed || maintenanceWhatsAppCancelled.url) throw new Error(`Vehicle maintenance WhatsApp cancel mismatch: ${JSON.stringify(maintenanceWhatsAppCancelled)}`);
    await evaluate(`offerMaintenanceWhatsApp({ customer_name: "Fixture Customer", customer_phone: "05550000061", vehicle_plate: "34 TEST 61", important_items: ["Oil", "Filter", "Belt", "Brakes", "Battery", "Tires"] }, { appointment_date: "2026-11-01", appointment_time: "14:30" })`);
    const maintenanceWhatsAppAccepted = await evaluate(`(async () => { document.querySelector("#dialogSubmit")?.click(); await new Promise(resolve => setTimeout(resolve, 50)); const url = window.__maintenanceWhatsAppUrl; const message = new URL(url).searchParams.get("text") || ""; return { closed: document.querySelector("#appDialog")?.open === false, phone: new URL(url).pathname.split("/").pop(), message }; })()`);
    if (!maintenanceWhatsAppAccepted.closed || maintenanceWhatsAppAccepted.phone !== "905550000061" || !maintenanceWhatsAppAccepted.message.includes("01.11.2026 14:30") || !maintenanceWhatsAppAccepted.message.includes("ve 1 kalem daha")) throw new Error(`Vehicle maintenance WhatsApp accept mismatch: ${JSON.stringify(maintenanceWhatsAppAccepted)}`);
    await capture("vehicle-maintenance-whatsapp-message-result-current-headless.png", "true");
    const financeMenu = await evaluate(`(() => {
      page = "finance";
      document.body.dataset.page = "finance";
      ayecFinanceLedgerItems = [{ web_key: "FIN-FIXTURE-1", id: 601, type: "income", amount: 500, description: "Fixture transaction", date: "2026-10-15" }];
      document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-kind="finance" data-id="FIN-FIXTURE-1"><td>Fixture transaction</td></tr></tbody></table></section>';
      const row = document.querySelector('tr[data-kind="finance"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), separators: menu.querySelectorAll("hr.context-menu-separator").length };
    })()`);
    const expectedFinanceActions = ["finance-detail", "finance-export", "finance-pdf", "finance-print"];
    if (!financeMenu.open || !financeMenu.prevented || JSON.stringify(financeMenu.actions) !== JSON.stringify(expectedFinanceActions) || financeMenu.separators !== 1) throw new Error(`Finance context menu mismatch: ${JSON.stringify(financeMenu)}`);
    await capture("finance-context-menu-current-headless.png", "true");
    const financePrint = await evaluate(`(() => {let calls=0;const original=window.print;window.print=()=>{calls++};document.querySelector('#contextMenu [data-context-action="finance-print"]')?.click();window.print=original;return {calls,closed:!document.querySelector("#contextMenu").classList.contains("open")};})()`);
    if (financePrint.calls !== 1 || !financePrint.closed) throw new Error(`Finance print action mismatch: ${JSON.stringify(financePrint)}`);
    const dateGroupMenu = await evaluate(`(() => {
      const date = "2026-10-15";
      ayecExpandedLedgerDates.delete(date);
      const row = document.createElement("tr");
      row.dataset.kind = "finance-date-group"; row.dataset.date = date; row.dataset.id = date;
      row.innerHTML = '<td><button type="button">Fixture date</button></td>';
      document.querySelector("#content").replaceChildren(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      const label = menu.innerText.trim();
      const originalRender = render;
      render = () => {};
      menu.querySelector("button")?.click();
      render = originalRender;
      return { prevented: event.defaultPrevented, label, expanded: ayecExpandedLedgerDates.has(date) };
    })()`);
    if (!dateGroupMenu.prevented || dateGroupMenu.label !== "G\u00fcn\u00fc A\u00e7" || !dateGroupMenu.expanded) throw new Error(`Finance date-group menu mismatch: ${JSON.stringify(dateGroupMenu)}`);
    const announcementMenu = await evaluate(`(() => {
      page = "announcements";
      document.body.dataset.page = "announcements";
      window.__announcementAuditRows = ayecAnnouncementRows;
      ayecAnnouncementRows = [{ id: 71, title: "Fixture announcement", priority: "Normal", content: "Offscreen menu audit", author: "Admin" }];
      document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-kind="announcement" data-id="71"><td>Fixture announcement</td></tr></tbody></table></section>';
      const row = document.querySelector('tr[data-kind="announcement"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), text: menu.innerText.trim() };
    })()`);
    if (!announcementMenu.open || !announcementMenu.prevented || JSON.stringify(announcementMenu.actions) !== JSON.stringify(["announcement-edit", "announcement-delete"])) throw new Error(`Announcement context menu mismatch: ${JSON.stringify(announcementMenu)}`);
    await capture("announcement-context-menu-current-headless.png", "true");
    await evaluate('document.querySelector("#contextMenu [data-context-action=announcement-delete]")?.click()');
    const announcementDeleteDialog = await evaluate(`({ open: document.querySelector("#appDialog")?.open || false, title: document.querySelector("#dialogTitle")?.textContent || "" })`);
    if (!announcementDeleteDialog.open || announcementDeleteDialog.title !== "Duyuruyu Sil") throw new Error(`Announcement delete confirmation mismatch: ${JSON.stringify(announcementDeleteDialog)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const announcementDeleteCancelled = await evaluate('document.querySelector("#appDialog")?.open === false');
    if (!announcementDeleteCancelled) throw new Error("Announcement delete dialog did not cancel cleanly.");
    await evaluate('document.querySelector("#contextMenu")?.classList.remove("open");ayecAnnouncementRows=window.__announcementAuditRows;delete window.__announcementAuditRows;page="dashboard";document.body.dataset.page="dashboard"');
    const checkMenu = await evaluate(`(() => {
      page = "check-notes";
      document.body.dataset.page = "check-notes";
      document.querySelector("#content").innerHTML = '<section class="card"><div id="genericHost"><table><tbody><tr data-kind="check-note" data-id="81" data-check-status="Portf\u00f6yde"><td>Fixture check note</td></tr></tbody></table></div></section>';
      const row = document.querySelector('#genericHost tbody tr[data-id="81"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-check-context-action]"), item => item.dataset.checkContextAction), statusToggle: menu.querySelector("[data-check-status-toggle]")?.textContent.trim() || "", currentStatusIncluded: Array.from(menu.querySelectorAll("[data-check-context-action]"), item => item.dataset.checkContextAction).includes("Portf\u00f6yde") };
    })()`);
    const expectedCheckActions = ["detail", "Tahsil Edildi", "Ciro Edildi", "\u00d6dendi", "Kar\u015f\u0131l\u0131ks\u0131z", "\u0130ade"];
    if (!checkMenu.open || !checkMenu.prevented || JSON.stringify(checkMenu.actions) !== JSON.stringify(expectedCheckActions) || checkMenu.currentStatusIncluded || !checkMenu.statusToggle.startsWith("Durum De\u011fi\u015ftir")) throw new Error("Check note context menu mismatch: " + JSON.stringify(checkMenu));
    await capture("check-note-context-menu-current-headless.png", "true");
    const checkSubmenu = await evaluate(`(() => {
      const toggle = document.querySelector("#contextMenu [data-check-status-toggle]");
      toggle.click();
      const panel = document.querySelector("#contextMenu .check-note-context-submenu-panel");
      return { visible: !panel.hidden, expanded: toggle.getAttribute("aria-expanded"), statuses: Array.from(panel.querySelectorAll("[data-check-context-action]"), item => item.dataset.checkContextAction) };
    })()`);
    if (!checkSubmenu.visible || checkSubmenu.expanded !== "true" || JSON.stringify(checkSubmenu.statuses) !== JSON.stringify(expectedCheckActions.slice(1))) throw new Error(`Check note status submenu mismatch: ${JSON.stringify(checkSubmenu)}`);
    await capture("check-note-status-submenu-current-headless.png", "true");
    const managedUserMenu = await evaluate(`(() => {
      page = "settings";
      settingsSection = "users";
      document.body.dataset.page = "settings";
      document.body.dataset.settingsSection = "users";
      window.__managedUserAuditRows = ayecSettingsUsers;
      ayecSettingsUsers = [{ id: 72, username: "fixture.staff", full_name: "Fixture Staff", role: "Personel", is_active: 1 }];
      document.querySelector("#content").innerHTML = '<section class="card"><table><tbody><tr data-kind="settings-user" data-id="72"><td>Fixture Staff</td></tr></tbody></table></section>';
      const row = document.querySelector('tr[data-kind="settings-user"]');
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, actions: Array.from(menu.querySelectorAll("[data-context-action]"), item => item.dataset.contextAction), text: menu.innerText.trim() };
    })()`);
    if (!managedUserMenu.open || !managedUserMenu.prevented || JSON.stringify(managedUserMenu.actions) !== JSON.stringify(["managed-user-edit", "managed-user-delete"])) throw new Error(`Managed user context menu mismatch: ${JSON.stringify(managedUserMenu)}`);
    await capture("managed-user-context-menu-current-headless.png", "true");
    await evaluate('document.querySelector("#contextMenu [data-context-action=managed-user-delete]")?.click()');
    const managedUserDeleteDialog = await evaluate(`({ open: document.querySelector("#appDialog")?.open || false, title: document.querySelector("#dialogTitle")?.textContent || "", cancel: document.querySelector("#dialogCancel")?.textContent || "" })`);
    if (!managedUserDeleteDialog.open || managedUserDeleteDialog.title !== "Kullan\u0131c\u0131y\u0131 Sil" || managedUserDeleteDialog.cancel !== "Hay\u0131r") throw new Error(`Managed user delete confirmation mismatch: ${JSON.stringify(managedUserDeleteDialog)}`);
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const managedUserDeleteCancelled = await evaluate('document.querySelector("#appDialog")?.open === false');
    if (!managedUserDeleteCancelled) throw new Error("Managed user delete confirmation did not cancel cleanly.");
    await evaluate('document.querySelector("#contextMenu")?.classList.remove("open");ayecSettingsUsers=window.__managedUserAuditRows;delete window.__managedUserAuditRows;page="dashboard";document.body.dataset.page="dashboard"');
    const personnelMenu = await evaluate(`(async () => {
      page = "personnel";
      document.body.dataset.page = "personnel";
      db.settings.contextMenu = true;
      document.querySelector("#content").innerHTML=genericShell(genericModules.personnel);
      window.__personnelOriginalApiFetch=apiFetch;
      window.__personnelAuditWrites=[];
      apiFetch=async(url,options={})=>{
        if(options.body)window.__personnelAuditWrites.push({url,payload:JSON.parse(options.body)});
        return {rows:[{id:81,name:"Fixture Person",role:"Technician",department:"Service",salary:100,commission:5,active:1}],count:1,columns:["name","role"]};
      };
      await loadGenericModule(genericModules.personnel);
      const row=document.querySelector('#personnelRows [data-personnel-id="81"]');
      if(!row)throw new Error("Personnel fixture did not render.");
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:300,clientY:240});
      row.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-personnel-context]"),item=>item.dataset.personnelContext),separators:menu.querySelectorAll("hr.context-menu-separator").length,writes:window.__personnelAuditWrites.length};
    })()`);
    if (!personnelMenu.open || !personnelMenu.prevented || JSON.stringify(personnelMenu.actions) !== JSON.stringify(["edit","remove"]) || personnelMenu.separators !== 1 || personnelMenu.writes !== 0) throw new Error(`Personnel context menu mismatch: ${JSON.stringify(personnelMenu)}`);
    await capture("personnel-context-menu-current-headless.png", "true");
    const personnelEditDialog = await evaluate(`(() => {
      document.querySelector('#contextMenu [data-personnel-context="edit"]')?.click();
      const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm");
      const result={open:dialog.open,name:form?.querySelector('[name="name"]')?.value,menuClosed:!document.querySelector("#contextMenu").classList.contains("open")};
      document.querySelector("#dialogCancel")?.click();
      return {...result,cancelled:!dialog.open};
    })()`);
    if (!personnelEditDialog.open || personnelEditDialog.name !== "Fixture Person" || !personnelEditDialog.menuClosed || !personnelEditDialog.cancelled) throw new Error(`Personnel context edit mismatch: ${JSON.stringify(personnelEditDialog)}`);
    await capture("personnel-context-edit-current-headless.png", "true");
    const personnelDeleteDialog = await evaluate(`(() => {
      const row=document.querySelector('#personnelRows [data-personnel-id="81"]');
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:300,clientY:240}));
      document.querySelector('#contextMenu [data-personnel-context="remove"]')?.click();
      const dialog=document.querySelector("#appDialog"),password=document.querySelector('#dialogBody input[name="admin_password"]');
      const result={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,passwordRequired:password?.required===true,passwordType:password?.type};
      document.querySelector("#dialogCancel")?.click();
      return {...result,cancelled:!dialog.open,writes:window.__personnelAuditWrites.length};
    })()`);
    if (!personnelDeleteDialog.open || personnelDeleteDialog.title !== "Onay" || !personnelDeleteDialog.passwordRequired || personnelDeleteDialog.passwordType !== "password" || !personnelDeleteDialog.cancelled || personnelDeleteDialog.writes !== 0) throw new Error(`Personnel delete confirmation mismatch: ${JSON.stringify(personnelDeleteDialog)}`);
    await capture("personnel-delete-password-confirmation-current-headless.png", "true");
    await evaluate(`(() => {apiFetch=window.__personnelOriginalApiFetch||apiFetch;delete window.__personnelOriginalApiFetch;page="dashboard";document.body.dataset.page="dashboard"})()`);
    const projectTransactionDialogOpen = await evaluate(`(async () => {
      window.__projectTransactionAudit = { requests: [] };
      window.__projectTransactionOriginalApiFetch = apiFetch;
      apiFetch = async (url, options = {}) => {
        window.__projectTransactionAudit.requests.push({ url, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null });
        if (url.startsWith("/api/desktop/table/bank_accounts")) return { rows: [{ id: 61, bank_name: "Fixture Bank", account_holder: "Project Account", account_number: "987654", is_active: 1, is_deleted: 0 }] };
        return { ok: true, id: 501 };
      };
      await openProjectTransactionDialog({ id: 91, name: "Fixture Project", currency: "TRY" }, "Gider");
      const form = document.querySelector("#dialogForm");
      return { open: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, categoryCount: form.querySelectorAll('[name="category"] option').length, bankChoice: form.querySelector('[name="bank_account_id"] option[value="61"]')?.textContent, date: form.querySelector('[name="date"]').value, fields: ["category", "amount", "bank_account_id", "date", "description"].every(name => form.querySelector('[name="' + name + '"]')) };
    })()`);
    if (!projectTransactionDialogOpen.open || projectTransactionDialogOpen.title !== "Gider Ekle" || projectTransactionDialogOpen.categoryCount !== 6 || !projectTransactionDialogOpen.bankChoice || !projectTransactionDialogOpen.date || !projectTransactionDialogOpen.fields) throw new Error(`Project transaction dialog mismatch: ${JSON.stringify(projectTransactionDialogOpen)}`);
    await capture("project-transaction-dialog-current-headless.png", "true");
    const projectTransactionFlow = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm");
      form.querySelector('[name="category"]').value = "Malzeme";
      form.querySelector('[name="amount"]').value = "275.50";
      form.querySelector('[name="bank_account_id"]').value = "61";
      form.querySelector('[name="description"]').value = "Fixture materials";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 50));
      const result = { requests: window.__projectTransactionAudit.requests, closed: !document.querySelector("#appDialog").open };
      apiFetch = window.__projectTransactionOriginalApiFetch;
      delete window.__projectTransactionOriginalApiFetch;
      delete window.__projectTransactionAudit;
      return result;
    })()`);
    const projectTransactionPost = projectTransactionFlow.requests.find(item => item.url === "/api/desktop/projects/transactions");
    if (!projectTransactionPost || projectTransactionPost.method !== "POST" || projectTransactionPost.body.project_id !== 91 || projectTransactionPost.body.type !== "Gider" || projectTransactionPost.body.amount !== 275.5 || projectTransactionPost.body.bank_account_id !== "61" || projectTransactionPost.body.category !== "Malzeme" || !projectTransactionFlow.closed) throw new Error(`Project transaction save flow mismatch: ${JSON.stringify(projectTransactionFlow)}`);    const projectFinanceDynamicFilters = await evaluate(`(() => {
      const state = { ...p9ProjectState };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", budget: 1000 }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.transactions = [
        { id: 601, project_id: 91, type: "Gider", amount: 100, category: "Fixture Category", payment_method: "Fixture Wire", status: "Bekliyor" },
        { id: 602, project_id: 91, type: "Gelir", amount: 300, category: "Fixture Income", payment_method: "Fixture Cash", status: "\u00d6dendi" }
      ];
      p9ProjectState.units = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "finance";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      const host = document.createElement("div");
      host.innerHTML = renderPart9Projects();
      const result = { categories: Array.from(host.querySelectorAll("#p9FinanceCategory option"), option => option.textContent), channels: Array.from(host.querySelectorAll("#p9FinanceChannel option"), option => option.textContent) };
      Object.assign(p9ProjectState, state);
      return result;
    })()`);
    if (!projectFinanceDynamicFilters.categories.includes("Fixture Category") || !projectFinanceDynamicFilters.categories.includes("Fixture Income") || !projectFinanceDynamicFilters.channels.includes("Fixture Wire") || !projectFinanceDynamicFilters.channels.includes("Fixture Cash")) throw new Error(`Project finance dynamic filters mismatch: ${JSON.stringify(projectFinanceDynamicFilters)}`);    const projectFinancePendingSegment = await evaluate(`(() => {
      const state = { ...p9ProjectState };
      const view = { ...p9FinanceView };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", budget: 1000 }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.transactions = [
        { id: 601, project_id: 91, type: "Gider", amount: 100, category: "Fixture Category", payment_method: "Fixture Wire", status: "Bekliyor" },
        { id: 602, project_id: 91, type: "Gelir", amount: 300, category: "Fixture Income", payment_method: "Fixture Cash", status: "\u00d6dendi" }
      ];
      p9ProjectState.units = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "finance";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      Object.assign(p9FinanceView, { query: "", type: "all", category: "all", channel: "all", status: "all", date: "all", segment: "pending" });
      const host = document.createElement("div");
      host.innerHTML = renderPart9Projects();
      const result = { rows: Array.from(host.querySelectorAll("[data-p9-finance-transaction]"), row => row.dataset.p9FinanceTransaction), pendingTab: host.querySelector('[data-p9-finance-category="pending"]')?.innerText };
      Object.assign(p9ProjectState, state);
      Object.assign(p9FinanceView, view);
      return result;
    })()`);
    if (JSON.stringify(projectFinancePendingSegment.rows) !== JSON.stringify(["601"]) || !projectFinancePendingSegment.pendingTab?.includes("1")) throw new Error(`Project finance pending segment mismatch: ${JSON.stringify(projectFinancePendingSegment)}`);    const projectSubcontractorPaymentOpen = await evaluate(`(async () => {
      window.__projectPaymentAudit = { requests: [], previousState: { ...p9ProjectState }, previousFetch: apiFetch };
      apiFetch = async (url, options = {}) => {
        window.__projectPaymentAudit.requests.push({ url, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null });
        if (url.startsWith("/api/desktop/table/bank_accounts")) return { rows: [] };
        return { ok: true, rows: [] };
      };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY", budget: 1000 }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.transactions = [];
      p9ProjectState.team = [{ id: 44, project_id: 91, name: "Fixture Contractor", job_type: "Electrical", total_contract_amount: 1000 }];
      p9ProjectState.units = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "team";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-team-pay="44"]').click();
      await new Promise(resolve => setTimeout(resolve, 30));
      const category = document.querySelector('#dialogForm [name="category"]');
      const result = { button: Boolean(document.querySelector('[data-p9-team-pay="44"]')), dialogOpen: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, category: category?.value, categoryDisabled: category?.disabled, description: document.querySelector('#dialogForm [name="description"]')?.value };
      return result;
    })()`);
    if (!projectSubcontractorPaymentOpen.button || !projectSubcontractorPaymentOpen.dialogOpen || projectSubcontractorPaymentOpen.title !== "Gider Ekle" || projectSubcontractorPaymentOpen.category !== "Ta\u015feron \u00d6demesi" || !projectSubcontractorPaymentOpen.categoryDisabled || !projectSubcontractorPaymentOpen.description.includes("Fixture Contractor")) throw new Error(`Subcontractor payment dialog mismatch: ${JSON.stringify(projectSubcontractorPaymentOpen)}`);
    await capture("project-subcontractor-payment-dialog-current-headless.png", "true");
    const projectSubcontractorPaymentSave = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm");
      form.querySelector('[name="amount"]').value = "125.50";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100));
      const request = window.__projectPaymentAudit.requests.find(item => item.url === "/api/desktop/projects/transactions");
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__projectPaymentAudit.previousFetch;
      Object.assign(p9ProjectState, window.__projectPaymentAudit.previousState);
      delete window.__projectPaymentAudit;
      return { request, closed };
    })()`);
    if (!projectSubcontractorPaymentSave.request || projectSubcontractorPaymentSave.request.body.ref_table !== "subcontractors" || projectSubcontractorPaymentSave.request.body.ref_id !== 44 || projectSubcontractorPaymentSave.request.body.category !== "Ta\u015feron \u00d6demesi" || projectSubcontractorPaymentSave.request.body.amount !== 125.5 || !projectSubcontractorPaymentSave.closed) throw new Error(`Subcontractor payment save mismatch: ${JSON.stringify(projectSubcontractorPaymentSave)}`);
    const projectTransactionDetail = await evaluate(`(() => {
      window.__projectTransactionDetailPrevious = p9ProjectState.transactions;
      p9ProjectState.transactions = [{ id: 502, type: "Gider", amount: 275.5, date: "2026-10-15", category: "Malzeme", description: "Fixture materials", status: "\u00d6dendi", tracking_no: "TX-502", ref_table: "projects", ref_id: 91 }];
      document.querySelector("#content").innerHTML = '<table><tbody><tr data-p9-finance-transaction="502"><td>Fixture transaction</td></tr></tbody></table>';
      document.querySelector('[data-p9-finance-transaction="502"]').dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
      const body = document.querySelector("#dialogBody").innerText;
      return { open: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, body, submit: document.querySelector("#dialogSubmit")?.textContent, hasAmount: body.includes("276"), hasCategory: body.includes("Malzeme"), hasDescription: body.includes("Fixture materials"), hasStatus: body.includes("\u00d6dendi"), hasTracking: body.includes("TX-502") };
    })()`);
    if (!projectTransactionDetail.open || projectTransactionDetail.title !== "\u0130\u015flem Detay\u0131" || !projectTransactionDetail.hasAmount || !projectTransactionDetail.hasCategory || !projectTransactionDetail.hasDescription || !projectTransactionDetail.hasStatus || !projectTransactionDetail.hasTracking || projectTransactionDetail.submit !== "Kapat") throw new Error(`Project transaction details mismatch: ${JSON.stringify(projectTransactionDetail)}`);
    await capture("project-transaction-detail-current-headless.png", "true");
    projectTransactionDetail.cancelled = await evaluate(`(() => { document.querySelector("#dialogCancel")?.click(); p9ProjectState.transactions = window.__projectTransactionDetailPrevious; delete window.__projectTransactionDetailPrevious; return !document.querySelector("#appDialog").open; })()`);
    if (!projectTransactionDetail.cancelled) throw new Error(`Project transaction detail cancel mismatch: ${JSON.stringify(projectTransactionDetail)}`);
        const projectCreationOpen = await evaluate(`(() => {
      window.__projectCreationAudit = { previousState: { ...p9ProjectState }, previousApiFetch: apiFetch, requests: [] };
      apiFetch = async (url, options = {}) => {
        window.__projectCreationAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null });
        if (url.startsWith("/api/desktop/table/customers")) return { rows: [{ id: 77, name: "Fixture Customer" }] };
        if (url.startsWith("/api/desktop/table/projects")) return { rows: [{ id: 92, name: "Fixture Web Project", status: "Devam Ediyor", currency: "USD" }] };
        return { ok: true, rows: [] };
      };
      p9ProjectState.projects = [];
      p9ProjectState.selectedId = "";
      p9ProjectState.units = [];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "finance";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector("[data-p9-add-project]").click();
      return true;
    })()`);
    await new Promise(resolve => setTimeout(resolve, 30));
    const projectCreationDialog = await evaluate(`(() => ({ open: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, customer: document.querySelector('#dialogForm [name="customer_id"] option[value="77"]')?.textContent, currency: document.querySelector('#dialogForm [name="currency"]').value, start: document.querySelector('#dialogForm [name="start_date"]').value, end: document.querySelector('#dialogForm [name="end_date"]').value, rateHidden: document.querySelector("#p9ProjectExchangeRateField").hidden, rateDisplay: getComputedStyle(document.querySelector("#p9ProjectExchangeRateField")).display }))()`);
    if (!projectCreationDialog.open || projectCreationDialog.title !== "Yeni Proje Olu\u015ftur" || projectCreationDialog.customer !== "Fixture Customer" || projectCreationDialog.currency !== "TRY" || !projectCreationDialog.start || !projectCreationDialog.end || !projectCreationDialog.rateHidden || projectCreationDialog.rateDisplay !== "none") throw new Error(`Project creation form mismatch: ${JSON.stringify(projectCreationDialog)}`);
    await capture("project-creation-dialog-current-headless.png", "true");
    const projectCreationSave = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm");
      form.querySelector('[name="name"]').value = "Fixture Web Project";
      form.querySelector('[name="customer_id"]').value = "77";
      const transfer = new DataTransfer();
      transfer.items.add(new File([new Uint8Array([37, 80, 68, 70, 45, 102, 105, 120, 116, 117, 114, 101])], "fixture-contract.pdf", { type: "application/pdf" }));
      form.querySelector('[name="contract_file"]').files = transfer.files;
      form.querySelector('[name="currency"]').value = "USD";
      form.querySelector('[name="currency"]').dispatchEvent(new Event("change", { bubbles: true }));
      const rateDisplayAfterCurrency = getComputedStyle(document.querySelector("#p9ProjectExchangeRateField")).display;
      form.querySelector('[name="exchange_rate"]').value = "31.25";
      form.querySelector('[name="budget"]').value = "1200";
      form.querySelector('[name="cost"]').value = "500";
      form.querySelector('[name="payment_method"]').value = "Pe\u015fin";
      form.querySelector('[name="description"]').value = "Fixture project description";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 400));
      const request = window.__projectCreationAudit.requests.find(item => item.url === "/api/desktop/projects/create");
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__projectCreationAudit.previousApiFetch;
      Object.assign(p9ProjectState, window.__projectCreationAudit.previousState);
      delete window.__projectCreationAudit;
      return { request, closed, rateDisplayAfterCurrency };
    })()`);
    const projectCreateBody = projectCreationSave.request?.body;
    if (!projectCreateBody || projectCreateBody.name !== "Fixture Web Project" || projectCreateBody.customer_id !== "77" || projectCreateBody.currency !== "USD" || projectCreateBody.exchange_rate !== 31.25 || projectCreateBody.budget !== 1200 || projectCreateBody.cost !== 500 || projectCreateBody.payment_method !== "Pe\u015fin" || projectCreateBody.contract_pdf?.filename !== "fixture-contract.pdf" || projectCreateBody.contract_pdf?.data_base64 !== "JVBERi1maXh0dXJl" || !projectCreationSave.closed || projectCreationSave.rateDisplayAfterCurrency === "none") throw new Error(`Project creation save mismatch: ${JSON.stringify(projectCreationSave)}`);
    const stockDeleteConfirmFlow = await evaluate(`(async () => {
      window.__stockDeleteConfirmAudit = { previousDb: structuredClone(db), previousStorage: localStorage.getItem(DB_KEY), previousFetch: apiFetch, previousRender: render, requests: [] };
      db = { stock: [{ id: 45, name: "Fixture Stock", qty: 4, currency: "TRY" }], movements: [], finance: [], activities: [] };
      localStorage.setItem(DB_KEY, JSON.stringify(db));
      apiFetch = async (url, options = {}) => { window.__stockDeleteConfirmAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { movement_id: 77, stock: 4, finance_id: 88, refund: 500, currency: "TRY" }; };
      render = () => {};
      const product = db.stock[0];
      deleteProduct(product);
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__stockDeleteConfirmAudit.requests.length === 0 && db.stock.length === 1;
      deleteProduct(product);
      document.querySelector("#stockDeletePassword").value = "fixture-password";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__stockDeleteConfirmAudit.requests[0];
      const sideEffects = { stockRemoved: db.stock.length === 0, movement: db.movements[0]?.id === "77", finance: db.finance[0]?.id === "88" };
      const closed = !document.querySelector("#appDialog").open;
      db = window.__stockDeleteConfirmAudit.previousDb;
      if (window.__stockDeleteConfirmAudit.previousStorage === null) localStorage.removeItem(DB_KEY); else localStorage.setItem(DB_KEY, window.__stockDeleteConfirmAudit.previousStorage);
      apiFetch = window.__stockDeleteConfirmAudit.previousFetch;
      render = window.__stockDeleteConfirmAudit.previousRender;
      delete window.__stockDeleteConfirmAudit;
      return { opened, cancelled, request, sideEffects, closed };
    })()`);
    if (stockDeleteConfirmFlow.opened.title !== "Stok Kart\u0131n\u0131 Sil" || !stockDeleteConfirmFlow.opened.body.includes("Fixture Stock") || !stockDeleteConfirmFlow.opened.danger || !stockDeleteConfirmFlow.cancelled || stockDeleteConfirmFlow.request?.url !== "/api/desktop/stock/delete" || stockDeleteConfirmFlow.request?.body.id !== 45 || !stockDeleteConfirmFlow.sideEffects.stockRemoved || !stockDeleteConfirmFlow.sideEffects.movement || !stockDeleteConfirmFlow.sideEffects.finance || !stockDeleteConfirmFlow.closed) throw new Error(`Stock delete confirm dialog mismatch: ${JSON.stringify(stockDeleteConfirmFlow)}`);
    await capture("stock-delete-confirmation-current-headless.png", "true");
    const bankDeleteConfirmFlow = await evaluate(`(async () => {
      window.__bankDeleteConfirmAudit = { previousFetch: apiFetch, previousLoad: ayecLoadBankReference, previousAccounts: ayecBankAccounts, previousSelected: Array.from(ayecBankSelectedIds), previousUser: currentAuthUser, requests: [] };
      apiFetch = async (url, options = {}) => { window.__bankDeleteConfirmAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true }; };
      ayecLoadBankReference = async () => {};
      ayecBankAccounts = [{ id: 71, bank_name: "Fixture Bank" }, { id: 72, bank_name: "Fixture Bank Two" }];
      ayecBankSelectedIds = new Set(["71", "72"]);
      currentAuthUser = { role: "Admin" };
      ayecBankCardContextAction("71", "bank-bulk-delete");
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__bankDeleteConfirmAudit.requests.length === 0;
      ayecBankCardContextAction("71", "bank-bulk-delete");
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const requests = window.__bankDeleteConfirmAudit.requests;
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__bankDeleteConfirmAudit.previousFetch;
      ayecLoadBankReference = window.__bankDeleteConfirmAudit.previousLoad;
      ayecBankAccounts = window.__bankDeleteConfirmAudit.previousAccounts;
      ayecBankSelectedIds = new Set(window.__bankDeleteConfirmAudit.previousSelected);
      currentAuthUser = window.__bankDeleteConfirmAudit.previousUser;
      delete window.__bankDeleteConfirmAudit;
      return { opened, cancelled, requests, closed };
    })()`);
    if (bankDeleteConfirmFlow.opened.title !== "Banka Hesaplar\u0131n\u0131 Sil" || !bankDeleteConfirmFlow.opened.body.includes("2 hesab") || !bankDeleteConfirmFlow.opened.danger || !bankDeleteConfirmFlow.cancelled || bankDeleteConfirmFlow.requests.length !== 2 || bankDeleteConfirmFlow.requests.some(request => request.url !== "/api/desktop/table/bank_accounts" || request.body._action !== "delete") || !bankDeleteConfirmFlow.closed) throw new Error(`Bank account deletion confirmation mismatch: ${JSON.stringify(bankDeleteConfirmFlow)}`);
    await capture("bank-account-delete-confirmation-current-headless.png", "true");
    const subcontractorRemoveFlow = await evaluate(`(async () => {
      window.__subcontractorRemoveAudit = { previousState: { ...p9ProjectState }, previousFetch: apiFetch, previousLoad: loadPart9Projects, requests: [] };
      apiFetch = async (url, options = {}) => { window.__subcontractorRemoveAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      loadPart9Projects = async () => {};
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY" }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [{ id: 44, project_id: 91, name: "Fixture Contractor", job_type: "Electrician", total_contract_amount: 1000 }];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "team";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-team-delete="44"]').click();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__subcontractorRemoveAudit.requests.length === 0;
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-team-delete="44"]').click();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__subcontractorRemoveAudit.requests[0];
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__subcontractorRemoveAudit.previousFetch;
      loadPart9Projects = window.__subcontractorRemoveAudit.previousLoad;
      Object.assign(p9ProjectState, window.__subcontractorRemoveAudit.previousState);
      delete window.__subcontractorRemoveAudit;
      return { opened, cancelled, request, closed };
    })()`);
    if (subcontractorRemoveFlow.opened.title !== "Ekip \u00dcyesini Projeden Kald\u0131r" || !subcontractorRemoveFlow.opened.body.includes("Fixture Contractor") || !subcontractorRemoveFlow.opened.danger || !subcontractorRemoveFlow.cancelled || subcontractorRemoveFlow.request?.url !== "/api/desktop/table/subcontractors" || subcontractorRemoveFlow.request?.body.id !== 44 || subcontractorRemoveFlow.request?.body._action !== "delete" || !subcontractorRemoveFlow.closed) throw new Error(`Subcontractor removal confirmation mismatch: ${JSON.stringify(subcontractorRemoveFlow)}`);
    await capture("project-subcontractor-delete-confirmation-current-headless.png", "true");
    const projectBulkUnitsOpen = await evaluate(`(() => {
      window.__projectBulkUnitsAudit = { previousState: { ...p9ProjectState }, previousApiFetch: apiFetch, requests: [] };
      apiFetch = async (url, options = {}) => { window.__projectBulkUnitsAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY" }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "units";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-add-unit="bulk"]').click();
      const form = document.querySelector("#dialogForm");
      const open = { dialog: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, blockCount: form.querySelector('[name="block_count"]').value, unitCount: form.querySelector('[name="unit_count"]').value, preview: document.querySelector("#p9UnitPreview").textContent };
      form.querySelector('[name="block_count"]').value = "2";
      form.querySelector('[name="unit_count"]').value = "3";
      form.querySelector('[name="naming"]').value = "custom";
      form.querySelector('[name="naming"]').dispatchEvent(new Event("change", { bubbles: true }));
      form.querySelector('[name="custom_names"]').value = "North, South";
      form.querySelector('[name="custom_names"]').dispatchEvent(new Event("input", { bubbles: true }));
      const customVisible = !document.querySelector("#p9CustomBlockNamesField").hidden;
      const customPreview = document.querySelector("#p9UnitPreview").textContent;
      return { open, customVisible, customPreview };
    })()`);
    if (!projectBulkUnitsOpen.open.dialog || projectBulkUnitsOpen.open.title !== "Blok ve Daire Olu\u015ftur" || projectBulkUnitsOpen.open.blockCount !== "1" || projectBulkUnitsOpen.open.unitCount !== "5" || !projectBulkUnitsOpen.open.preview.includes("Toplam 5 daire") || !projectBulkUnitsOpen.customVisible || !projectBulkUnitsOpen.customPreview.includes("North: 3 daire, South: 3 daire") || !projectBulkUnitsOpen.customPreview.includes("Toplam 6 daire")) throw new Error(`Project bulk-unit dialog mismatch: ${JSON.stringify(projectBulkUnitsOpen)}`);
    await capture("project-bulk-unit-dialog-current-headless.png", "true");
    const projectBulkUnitsSave = await evaluate(`(async () => {
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 120));
      const request = window.__projectBulkUnitsAudit.requests.find(item => item.url === "/api/desktop/projects/units/bulk-create");
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__projectBulkUnitsAudit.previousApiFetch;
      Object.assign(p9ProjectState, window.__projectBulkUnitsAudit.previousState);
      delete window.__projectBulkUnitsAudit;
      return { request, closed };
    })()`);
    if (projectBulkUnitsSave.request?.body.project_id !== 91 || projectBulkUnitsSave.request?.body.block_count !== 2 || projectBulkUnitsSave.request?.body.unit_count !== 3 || projectBulkUnitsSave.request?.body.naming !== "custom" || projectBulkUnitsSave.request?.body.custom_names !== "North, South" || !projectBulkUnitsSave.closed) throw new Error(`Project bulk-unit save mismatch: ${JSON.stringify(projectBulkUnitsSave)}`);
    const projectSingleUnitSave = await evaluate(`(async () => {
      window.__projectSingleUnitAudit = { previousState: { ...p9ProjectState }, previousApiFetch: apiFetch, requests: [] };
      apiFetch = async (url, options = {}) => { window.__projectSingleUnitAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY" }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "units";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-add-unit="single"]').click();
      const form = document.querySelector("#dialogForm");
      const title = document.querySelector("#dialogTitle").textContent;
      form.querySelector('[name="unit_no"]').value = "B-7";
      form.querySelector('[name="block_name"]').value = "B Blok";
      form.querySelector('[name="floor_no"]').value = "2";
      form.querySelector('[name="unit_kind"]').value = "Oda";
      form.querySelector('[name="status"]').value = "Devam Ediyor";
      form.querySelector('[name="area"]').value = "45.5";
      form.querySelector('[name="unit_price"]').value = "90000";
      form.querySelector('[name="description"]').value = "Fixture single unit";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 120));
      const request = window.__projectSingleUnitAudit.requests.find(item => item.url === "/api/desktop/table/project_units");
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__projectSingleUnitAudit.previousApiFetch;
      Object.assign(p9ProjectState, window.__projectSingleUnitAudit.previousState);
      delete window.__projectSingleUnitAudit;
      return { title, request, closed };
    })()`);
    if (projectSingleUnitSave.title !== "Tekil Daire / Oda Ekle" || projectSingleUnitSave.request?.body.project_id !== 91 || projectSingleUnitSave.request?.body.unit_no !== "B-7" || projectSingleUnitSave.request?.body.block_name !== "B Blok" || projectSingleUnitSave.request?.body.unit_kind !== "Oda" || projectSingleUnitSave.request?.body.area !== 45.5 || projectSingleUnitSave.request?.body.unit_price !== 90000 || !projectSingleUnitSave.closed) throw new Error(`Project single-unit save mismatch: ${JSON.stringify(projectSingleUnitSave)}`);
    await capture("project-single-unit-dialog-current-headless.png", "true");
    const genericDeleteFlow = await evaluate(`(async () => {
      window.__genericDeleteAudit = { previousFetch: apiFetch, previousLoad: loadGenericModule, requests: [] };
      apiFetch = async (url, options = {}) => { window.__genericDeleteAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      loadGenericModule = async () => {};
      const meta = { title: "H\u0131zl\u0131 Not", table: "fast_notes" };
      const row = { id: 53, name: "Fixture note" };
      deleteGenericRow(meta, row);
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = !document.querySelector("#appDialog").open && window.__genericDeleteAudit.requests.length === 0;
      deleteGenericRow(meta, row);
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100));
      const request = window.__genericDeleteAudit.requests[0];
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__genericDeleteAudit.previousFetch;
      loadGenericModule = window.__genericDeleteAudit.previousLoad;
      delete window.__genericDeleteAudit;
      return { opened, cancelled, request, closed };
    })()`);
    if (genericDeleteFlow.opened.title !== "Kayd\u0131 Sil" || !genericDeleteFlow.opened.body.includes("Fixture note") || !genericDeleteFlow.opened.danger || !genericDeleteFlow.cancelled || genericDeleteFlow.request?.url !== "/api/desktop/table/fast_notes" || genericDeleteFlow.request?.body.id !== 53 || genericDeleteFlow.request?.body._action !== "delete" || !genericDeleteFlow.closed) throw new Error(`Generic delete dialog mismatch: ${JSON.stringify(genericDeleteFlow)}`);
    await capture("generic-delete-confirmation-current-headless.png", "true");
    const bulkServicePriceFlow = await evaluate(`(async () => {
      window.__bulkServicePriceAudit = { previousFetch: apiFetch, previousLoad: loadGenericModule, previousData: window.currentGenericData, requests: [] };
      apiFetch = async (url, options = {}) => { window.__bulkServicePriceAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      loadGenericModule = async () => {};
      window.currentGenericData = { rows: [{ id: 11, price_try: 100 }, { id: 12, price_try: 50 }] };
      openBulkServicePriceDialog({ title: "Hizmet", table: "services" });
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, value: document.querySelector('#dialogForm [name="percent"]').value };
      document.querySelector('#dialogForm [name="percent"]').value = "12.5";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 130));
      const requests = window.__bulkServicePriceAudit.requests;
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__bulkServicePriceAudit.previousFetch;
      loadGenericModule = window.__bulkServicePriceAudit.previousLoad;
      window.currentGenericData = window.__bulkServicePriceAudit.previousData;
      delete window.__bulkServicePriceAudit;
      return { opened, requests, closed };
    })()`);
    if (bulkServicePriceFlow.opened.title !== "Toplu Fiyat G\u00fcncelle" || bulkServicePriceFlow.opened.value !== "0" || bulkServicePriceFlow.requests.length !== 2 || bulkServicePriceFlow.requests[0].body.price_try !== 112.5 || bulkServicePriceFlow.requests[1].body.price_try !== 56.25 || !bulkServicePriceFlow.closed) throw new Error(`Bulk service price dialog mismatch: ${JSON.stringify(bulkServicePriceFlow)}`);
    await capture("bulk-service-price-dialog-current-headless.png", "true");
    const clearImportPreviewFlow = await evaluate(`(async () => {
      const previousRows = window.importRows;
      const previousDraw = drawImportPreview;
      drawImportPreview = () => {};
      window.importRows = [{ name: "Fixture one" }, { name: "Fixture two" }];
      openClearImportPreviewDialog();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText };
      document.querySelector("#dialogCancel").click();
      const cancelled = !document.querySelector("#appDialog").open && window.importRows.length === 2;
      openClearImportPreviewDialog();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 40));
      const cleared = window.importRows.length === 0;
      const closed = !document.querySelector("#appDialog").open;
      window.importRows = previousRows;
      drawImportPreview = previousDraw;
      return { opened, cancelled, cleared, closed };
    })()`);
    if (clearImportPreviewFlow.opened.title !== "\u0130\u00e7e Aktarma Listesini Temizle" || !clearImportPreviewFlow.opened.body.includes("t\u00fcm sat\u0131rlar") || !clearImportPreviewFlow.cancelled || !clearImportPreviewFlow.cleared || !clearImportPreviewFlow.closed) throw new Error(`Import preview clear dialog mismatch: ${JSON.stringify(clearImportPreviewFlow)}`);
    await capture("import-preview-clear-confirmation-current-headless.png", "true");
    const companyLogoRemovalFlow = await evaluate(`(async () => {
      window.__companyLogoAudit = { previousFetch: apiFetch, previousRender: render, previousRefresh: refreshCompanyLogo, previousLogo: desktopSettings.logo_path, requests: [] };
      apiFetch = async (url, options = {}) => { window.__companyLogoAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true }; };
      render = () => {};
      refreshCompanyLogo = () => {};
      desktopSettings.logo_path = "fixture-logo.png";
      const trigger = document.createElement("button");
      trigger.type = "button";
      trigger.dataset.action = "remove-company-logo";
      document.body.append(trigger);
      trigger.click();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__companyLogoAudit.requests.length === 0 && desktopSettings.logo_path === "fixture-logo.png";
      trigger.click();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__companyLogoAudit.requests[0];
      const removed = desktopSettings.logo_path === "";
      const closed = !document.querySelector("#appDialog").open;
      trigger.remove();
      apiFetch = window.__companyLogoAudit.previousFetch;
      render = window.__companyLogoAudit.previousRender;
      refreshCompanyLogo = window.__companyLogoAudit.previousRefresh;
      desktopSettings.logo_path = window.__companyLogoAudit.previousLogo;
      delete window.__companyLogoAudit;
      return { opened, cancelled, request, removed, closed };
    })()`);
    if (companyLogoRemovalFlow.opened.title !== "Logoyu Kald\u0131r" || !companyLogoRemovalFlow.opened.body.includes("Firma logosu") || !companyLogoRemovalFlow.opened.danger || !companyLogoRemovalFlow.cancelled || companyLogoRemovalFlow.request?.url !== "/api/desktop/company-logo" || companyLogoRemovalFlow.request?.body.remove !== true || !companyLogoRemovalFlow.removed || !companyLogoRemovalFlow.closed) throw new Error(`Company logo removal dialog mismatch: ${JSON.stringify(companyLogoRemovalFlow)}`);
    await capture("company-logo-removal-confirmation-current-headless.png", "true");
    const sectorSwitchFlow = await evaluate(`(async () => {
      window.__sectorSwitchAudit = { previousFetch: apiFetch, previousHydrate: hydrateDesktop, previousRenderNav: renderNav, previousNavigate: navigate, previousUser: currentAuthUser, previousSector: currentSector, previousSettingSector: desktopInternalSettings.current_sector, requests: [] };
      apiFetch = async (url, options = {}) => { window.__sectorSwitchAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { sector: "otomotiv" }; };
      hydrateDesktop = async () => {};
      renderNav = () => {};
      navigate = () => {};
      currentAuthUser = { is_admin: true };
      currentSector = "teknik_servis";
      desktopInternalSettings.current_sector = "teknik_servis";
      let select = document.querySelector("#companySectorSelect");
      const created = !select;
      if (created) { select = document.createElement("select"); select.id = "companySectorSelect"; document.body.append(select); }
      if (!select.querySelector('option[value="otomotiv"]')) select.insertAdjacentHTML("beforeend", '<option value="otomotiv">Otomotiv Servis</option>');
      select.value = "otomotiv";
      saveCompanySector();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__sectorSwitchAudit.requests.length === 0 && currentSector === "teknik_servis";
      saveCompanySector();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__sectorSwitchAudit.requests[0];
      const saved = currentSector === "otomotiv";
      const closed = !document.querySelector("#appDialog").open;
      if (created) select.remove();
      apiFetch = window.__sectorSwitchAudit.previousFetch;
      hydrateDesktop = window.__sectorSwitchAudit.previousHydrate;
      renderNav = window.__sectorSwitchAudit.previousRenderNav;
      navigate = window.__sectorSwitchAudit.previousNavigate;
      currentAuthUser = window.__sectorSwitchAudit.previousUser;
      currentSector = window.__sectorSwitchAudit.previousSector;
      desktopInternalSettings.current_sector = window.__sectorSwitchAudit.previousSettingSector;
      delete window.__sectorSwitchAudit;
      return { opened, cancelled, request, saved, closed };
    })()`);
    if (sectorSwitchFlow.opened.title !== "Sekt\u00f6r\u00fc Uygula" || !sectorSwitchFlow.opened.body.includes("Otomotiv Servis") || !sectorSwitchFlow.cancelled || sectorSwitchFlow.request?.url !== "/api/company/sector" || sectorSwitchFlow.request?.body.sector !== "otomotiv" || !sectorSwitchFlow.saved || !sectorSwitchFlow.closed) throw new Error(`Sector switch dialog mismatch: ${JSON.stringify(sectorSwitchFlow)}`);
    await capture("sector-switch-confirmation-current-headless.png", "true");
    const identitySectorSaveFlow = await evaluate(`(async () => {
      window.__identitySectorSaveAudit = { previousFetch: apiFetch, previousRenderNav: renderNav, previousPage: page, previousSection: settingsSection, previousSector: currentSector, previousCurrentSetting: desktopInternalSettings.current_sector, previousValue: desktopInternalSettings.web_identity_fixture, requests: [] };
      apiFetch = async (url, options = {}) => { window.__identitySectorSaveAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return url === "/api/company/sector" ? { sector: "otomotiv" } : { ok: true }; };
      renderNav = () => {};
      page = "settings";
      settingsSection = "identity";
      currentSector = "teknik_servis";
      desktopInternalSettings.current_sector = "teknik_servis";
      const content = document.querySelector("#content");
      content.innerHTML = '<section class="identity-reference"><input class="exact-setting" data-setting-key="web_identity_fixture" data-setting-scope="internal_settings" value="fixture-value"><select data-setting-key="current_sector"><option value="teknik_servis">Technical</option><option value="otomotiv" selected>Automotive</option></select><button type="button" data-action="save-settings">Save</button></section>';
      const trigger = content.querySelector('[data-action="save-settings"]');
      trigger.click();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__identitySectorSaveAudit.requests.length === 0 && currentSector === "teknik_servis";
      trigger.click();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const requests = window.__identitySectorSaveAudit.requests;
      const saved = currentSector === "otomotiv" && desktopInternalSettings.web_identity_fixture === "fixture-value";
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__identitySectorSaveAudit.previousFetch;
      renderNav = window.__identitySectorSaveAudit.previousRenderNav;
      page = window.__identitySectorSaveAudit.previousPage;
      settingsSection = window.__identitySectorSaveAudit.previousSection;
      currentSector = window.__identitySectorSaveAudit.previousSector;
      desktopInternalSettings.current_sector = window.__identitySectorSaveAudit.previousCurrentSetting;
      if (window.__identitySectorSaveAudit.previousValue === undefined) delete desktopInternalSettings.web_identity_fixture; else desktopInternalSettings.web_identity_fixture = window.__identitySectorSaveAudit.previousValue;
      delete window.__identitySectorSaveAudit;
      return { opened, cancelled, requests, saved, closed };
    })()`);
    if (identitySectorSaveFlow.opened.title !== "Sekt\u00f6r De\u011fi\u015fikli\u011fini Uygula" || !identitySectorSaveFlow.opened.body.includes("se\u00e7ilen sekt\u00f6re") || !identitySectorSaveFlow.cancelled || identitySectorSaveFlow.requests.length !== 2 || identitySectorSaveFlow.requests[0].body.key !== "web_identity_fixture" || identitySectorSaveFlow.requests[1].url !== "/api/company/sector" || !identitySectorSaveFlow.saved || !identitySectorSaveFlow.closed) throw new Error(`Identity sector save mismatch: ${JSON.stringify(identitySectorSaveFlow)}`);
    await capture("identity-settings-sector-confirmation-current-headless.png", "true");
    const resetDemoFlow = await evaluate(`(async () => {
      window.__resetDemoAudit = { previousDb: structuredClone(db), previousRender: render, previousStorage: localStorage.getItem(DB_KEY), renderCount: 0 };
      db = { customers: [{ id: "fixture" }], stock: [], settings: {} };
      render = () => { window.__resetDemoAudit.renderCount += 1; };
      handleAction("reset-demo");
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = db.customers.length === 1;
      handleAction("reset-demo");
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 40));
      const saved = db.customers.length === (seed.customers || []).length;
      const closed = !document.querySelector("#appDialog").open;
      const result = { opened, cancelled, saved, closed, renderCount: window.__resetDemoAudit.renderCount };
      db = window.__resetDemoAudit.previousDb;
      render = window.__resetDemoAudit.previousRender;
      if (window.__resetDemoAudit.previousStorage === null) localStorage.removeItem(DB_KEY);
      else localStorage.setItem(DB_KEY, window.__resetDemoAudit.previousStorage);
      delete window.__resetDemoAudit;
      return result;
    })()`);
    if (resetDemoFlow.opened.title !== "\u00d6rnek Verileri S\u0131f\u0131rla" || !resetDemoFlow.opened.danger || !resetDemoFlow.cancelled || !resetDemoFlow.saved || !resetDemoFlow.closed || resetDemoFlow.renderCount !== 1) throw new Error(`Reset demo dialog mismatch: ${JSON.stringify(resetDemoFlow)}`);
    await capture("reset-demo-confirmation-current-headless.png", "true");
    const menuResetFlow = await evaluate(`(async () => {
      window.__menuResetAudit = { previousFetch: apiFetch, previousRenderNav: renderNav, previousNavigate: navigate, previousLabels: desktopInternalSettings.web_menu_labels, previousVisibility: desktopInternalSettings.web_menu_visibility, previousLabelStorage: localStorage.getItem("ayec_menu_labels"), previousVisibilityStorage: localStorage.getItem("ayec_menu_visibility"), requests: [] };
      apiFetch = async (url, options = {}) => { window.__menuResetAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true }; };
      renderNav = () => {};
      navigate = () => {};
      interfaceEditorDialog();
      const firstInput = document.querySelector('#dialogBody input[name^="menu_"]');
      firstInput.value = "Fixture unsaved label";
      const resetButton = () => Array.from(document.querySelectorAll("#dialogFooter button")).find(button => button.textContent.includes("Varsay"));
      resetButton().click();
      const opened = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const restoredValue = document.querySelector('#dialogBody input[name^="menu_"]')?.value;
      const cancelled = window.__menuResetAudit.requests.length === 0;
      resetButton().click();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const resetRequests = window.__menuResetAudit.requests;
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__menuResetAudit.previousFetch;
      renderNav = window.__menuResetAudit.previousRenderNav;
      navigate = window.__menuResetAudit.previousNavigate;
      desktopInternalSettings.web_menu_labels = window.__menuResetAudit.previousLabels;
      desktopInternalSettings.web_menu_visibility = window.__menuResetAudit.previousVisibility;
      for (const [key, value] of [["ayec_menu_labels", window.__menuResetAudit.previousLabelStorage], ["ayec_menu_visibility", window.__menuResetAudit.previousVisibilityStorage]]) { if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value); }
      delete window.__menuResetAudit;
      return { opened, restoredValue, cancelled, resetRequests, closed };
    })()`);
    if (menuResetFlow.opened.title !== "Men\u00fcleri Varsay\u0131lana D\u00f6nd\u00fcr" || !menuResetFlow.opened.danger || menuResetFlow.restoredValue !== "Fixture unsaved label" || !menuResetFlow.cancelled || menuResetFlow.resetRequests.length !== 2 || !menuResetFlow.closed) throw new Error(`Menu reset confirmation mismatch: ${JSON.stringify(menuResetFlow)}`);
    await capture("menu-reset-confirmation-current-headless.png", "true");
    const wipeAllConfirmationFlow = await evaluate(`(async () => {
      window.__wipeAllConfirmAudit = { previousDb: structuredClone(db), previousStorage: localStorage.getItem(DB_KEY), previousFetch: apiFetch, previousHydrate: hydrateDesktop, previousNavigate: navigate, requests: [] };
      db = { customers: [{ id: "wipe-fixture" }], stock: [], movements: [], finance: [], appointments: [], quotes: [], activities: [] };
      localStorage.setItem(DB_KEY, JSON.stringify(db));
      apiFetch = async (url, options = {}) => { window.__wipeAllConfirmAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { deleted_rows: 3, backup: "fixture-backup.db" }; };
      hydrateDesktop = async () => {};
      navigate = () => {};
      const fillAndSubmitFirstStep = async () => {
        openWipeAllDialog();
        const firstTitle = document.querySelector("#dialogTitle").textContent;
        const first = document.querySelector("#dialogForm");
        const passwordType = first.querySelector('[name="password"]').type;
        first.querySelector('[name="password"]').value = "fixture-admin-password";
        first.querySelector('[name="phrase"]').value = "TUM VERILERI SIL";
        first.requestSubmit();
        await new Promise(resolve => setTimeout(resolve, 30));
        return { title: firstTitle, passwordType };
      };
      const firstOpen = await fillAndSubmitFirstStep();
      const secondOpen = { title: document.querySelector("#dialogTitle").textContent, body: document.querySelector("#dialogBody").innerText, danger: document.querySelector("#dialogSubmit").classList.contains("danger") };
      document.querySelector("#dialogCancel").click();
      const cancelled = window.__wipeAllConfirmAudit.requests.length === 0 && db.customers.length === 1;
      await fillAndSubmitFirstStep();
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__wipeAllConfirmAudit.requests[0];
      const wiped = db.customers.length === 0 && db.stock.length === 0;
      const closed = !document.querySelector("#appDialog").open;
      db = window.__wipeAllConfirmAudit.previousDb;
      if (window.__wipeAllConfirmAudit.previousStorage === null) localStorage.removeItem(DB_KEY); else localStorage.setItem(DB_KEY, window.__wipeAllConfirmAudit.previousStorage);
      apiFetch = window.__wipeAllConfirmAudit.previousFetch;
      hydrateDesktop = window.__wipeAllConfirmAudit.previousHydrate;
      navigate = window.__wipeAllConfirmAudit.previousNavigate;
      delete window.__wipeAllConfirmAudit;
      return { firstOpen, secondOpen, cancelled, request, wiped, closed };
    })()`);
    if (wipeAllConfirmationFlow.firstOpen.title !== "Operasyonel Verileri S\u0131f\u0131rla" || wipeAllConfirmationFlow.firstOpen.passwordType !== "password" || wipeAllConfirmationFlow.secondOpen.title !== "Son Onay: Operasyonel Verileri Sil" || !wipeAllConfirmationFlow.secondOpen.danger || !wipeAllConfirmationFlow.cancelled || wipeAllConfirmationFlow.request?.url !== "/api/admin/wipe-user-data" || wipeAllConfirmationFlow.request?.body.password !== "fixture-admin-password" || wipeAllConfirmationFlow.request?.body.phrase !== "TUM VERILERI SIL" || !wipeAllConfirmationFlow.wiped || !wipeAllConfirmationFlow.closed) throw new Error(`Wipe All confirmation flow mismatch: ${JSON.stringify(wipeAllConfirmationFlow)}`);
    await capture("wipe-all-final-confirmation-current-headless.png", "true");
    const projectLifecycleOpen = await evaluate(`(() => {
      window.__projectLifecycleAudit = { previousState: { ...p9ProjectState }, previousApiFetch: apiFetch, requests: [] };
      apiFetch = async (url, options = {}) => { window.__projectLifecycleAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Lifecycle Project", currency: "TRY", status: "Devam Ediyor", is_archived: 0 }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "finance";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector('[data-p9-project-action="complete"]').click();
      const completeTitle = document.querySelector("#dialogTitle").textContent;
      document.querySelector("#dialogCancel").click();
      document.querySelector('[data-p9-project-action="delete"]').click();
      const deleteTitle = document.querySelector("#dialogTitle").textContent;
      const deleteDanger = document.querySelector("#dialogSubmit").classList.contains("danger");
      document.querySelector("#dialogCancel").click();
      document.querySelector('[data-p9-project-action="archive"]').click();
      return { completeTitle, deleteTitle, deleteDanger, archiveTitle: document.querySelector("#dialogTitle").textContent, requestsBeforeConfirm: window.__projectLifecycleAudit.requests.length, archiveOpen: document.querySelector("#appDialog").open };
    })()`);
    if (projectLifecycleOpen.completeTitle !== "Projeyi Tamamla" || projectLifecycleOpen.deleteTitle !== "Projeyi Sil" || !projectLifecycleOpen.deleteDanger || projectLifecycleOpen.archiveTitle !== "Projeyi Ar\u015fivle" || projectLifecycleOpen.requestsBeforeConfirm !== 0 || !projectLifecycleOpen.archiveOpen) throw new Error(`Project lifecycle confirmation mismatch: ${JSON.stringify(projectLifecycleOpen)}`);
    await capture("project-lifecycle-confirmation-current-headless.png", "true");
    const projectLifecycleSave = await evaluate(`(async () => {
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const request = window.__projectLifecycleAudit.requests.find(item => item.url === "/api/desktop/projects/lifecycle");
      const closed = !document.querySelector("#appDialog").open;
      apiFetch = window.__projectLifecycleAudit.previousApiFetch;
      Object.assign(p9ProjectState, window.__projectLifecycleAudit.previousState);
      delete window.__projectLifecycleAudit;
      return { request, closed };
    })()`);
    if (projectLifecycleSave.request?.body.project_id !== 91 || projectLifecycleSave.request?.body.action !== "archive" || !projectLifecycleSave.closed) throw new Error(`Project lifecycle save mismatch: ${JSON.stringify(projectLifecycleSave)}`);const projectUnitExportOpen = await evaluate(`(() => {
      window.__projectUnitExportAudit = { previousState: { ...p9ProjectState }, previousFetch: window.fetch, previousAnchorClick: HTMLAnchorElement.prototype.click, previousCreateUrl: URL.createObjectURL, previousRevokeUrl: URL.revokeObjectURL, urls: [], download: "" };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY" }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [{ id: 951, project_id: 91, unit_no: "A-1", block_name: "A Block", status: "Bekliyor" }];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "units";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      window.fetch = async url => { window.__projectUnitExportAudit.urls.push(String(url)); return { ok: true, blob: async () => new Blob(["fixture"]) }; };
      URL.createObjectURL = () => "blob:project-unit-export";
      URL.revokeObjectURL = () => {};
      HTMLAnchorElement.prototype.click = function() { window.__projectUnitExportAudit.download = this.download; };
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector("[data-p9-units-export]").click();
      const select = document.querySelector('#dialogForm [name="format"]');
      return { open: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, formats: Array.from(select.options, option => option.value), defaultFormat: select.value, urls: window.__projectUnitExportAudit.urls };
    })()`);
    if (!projectUnitExportOpen.open || projectUnitExportOpen.title !== "Excel Raporu Kaydet" || JSON.stringify(projectUnitExportOpen.formats) !== JSON.stringify(["xlsx", "csv"]) || projectUnitExportOpen.defaultFormat !== "xlsx" || projectUnitExportOpen.urls.length) throw new Error(`Project unit export dialog mismatch: ${JSON.stringify(projectUnitExportOpen)}`);
    await capture("project-unit-export-format-current-headless.png", "true");
    const projectUnitExportDownload = await evaluate(`(async () => {
      document.querySelector('#dialogForm [name="format"]').value = "csv";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 60));
      const result = { urls: window.__projectUnitExportAudit.urls, download: window.__projectUnitExportAudit.download, closed: !document.querySelector("#appDialog").open };
      window.fetch = window.__projectUnitExportAudit.previousFetch;
      HTMLAnchorElement.prototype.click = window.__projectUnitExportAudit.previousAnchorClick;
      URL.createObjectURL = window.__projectUnitExportAudit.previousCreateUrl;
      URL.revokeObjectURL = window.__projectUnitExportAudit.previousRevokeUrl;
      Object.assign(p9ProjectState, window.__projectUnitExportAudit.previousState);
      delete window.__projectUnitExportAudit;
      return result;
    })()`);
    if (projectUnitExportDownload.urls.length !== 1 || !projectUnitExportDownload.urls[0].endsWith("/api/desktop/projects/91/units/export.csv") || !projectUnitExportDownload.download.endsWith(".csv") || !projectUnitExportDownload.closed) throw new Error(`Project unit export download mismatch: ${JSON.stringify(projectUnitExportDownload)}`);const projectBulkStatusOpen = await evaluate(`(() => {
      window.__projectBulkStatusAudit = { previousState: { ...p9ProjectState }, previousFetch: apiFetch, requests: [] };
      apiFetch = async (url, options = {}) => { window.__projectBulkStatusAudit.requests.push({ url, body: options.body ? JSON.parse(options.body) : null }); return { ok: true, rows: [] }; };
      p9ProjectState.projects = [{ id: 91, name: "Fixture Project", currency: "TRY" }];
      p9ProjectState.selectedId = 91;
      p9ProjectState.units = [{ id: 951, project_id: 91, block_name: "A Blok", unit_no: "A-1", status: "Bekliyor" }, { id: 952, project_id: 91, block_name: "A Blok", unit_no: "A-2", status: "Devam Ediyor" }, { id: 953, project_id: 91, parent_unit_id: 951, block_name: "A Blok", unit_no: "A-1-1", status: "Bekliyor" }];
      p9ProjectState.transactions = [];
      p9ProjectState.team = [];
      p9ProjectState.unitProducts = [];
      p9ProjectState.tab = "units";
      p9ProjectState.loaded = true;
      p9ProjectState.loading = false;
      p9ProjectState.error = "";
      document.querySelector("#content").innerHTML = renderPart9Projects();
      document.querySelector("[data-p9-units-bulk]").click();
      const select = document.querySelector('#dialogForm [name="status"]');
      return { open: document.querySelector("#appDialog").open, title: document.querySelector("#dialogTitle").textContent, statuses: Array.from(select.options, option => option.value), defaultStatus: select.value, requests: window.__projectBulkStatusAudit.requests.length };
    })()`);
    if (!projectBulkStatusOpen.open || projectBulkStatusOpen.title !== "Toplu Durum G\u00fcncelle" || JSON.stringify(projectBulkStatusOpen.statuses) !== JSON.stringify(["Bekliyor", "Devam Ediyor", "Tamamland\u0131"]) || projectBulkStatusOpen.defaultStatus !== "Bekliyor" || projectBulkStatusOpen.requests !== 0) throw new Error(`Project bulk status dialog mismatch: ${JSON.stringify(projectBulkStatusOpen)}`);
    await capture("project-bulk-status-dialog-current-headless.png", "true");
    const projectBulkStatusSave = await evaluate(`(async () => {
      document.querySelector("#dialogCancel").click();
      const cancelled = !document.querySelector("#appDialog").open && window.__projectBulkStatusAudit.requests.length === 0;
      document.querySelector("[data-p9-units-bulk]").click();
      document.querySelector('#dialogForm [name="status"]').value = "Tamamland\u0131";
      document.querySelector("#dialogForm").requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100));
      const updates = window.__projectBulkStatusAudit.requests.filter(item => item.url === "/api/desktop/table/project_units" && item.body?._action === "update");
      apiFetch = window.__projectBulkStatusAudit.previousFetch;
      Object.assign(p9ProjectState, window.__projectBulkStatusAudit.previousState);
      delete window.__projectBulkStatusAudit;
      return { cancelled, updates, dialogClosed: !document.querySelector("#appDialog").open };
    })()`);
    if (!projectBulkStatusSave.cancelled || !projectBulkStatusSave.dialogClosed || JSON.stringify(projectBulkStatusSave.updates.map(item => item.body.id).sort()) !== JSON.stringify([951, 952]) || projectBulkStatusSave.updates.some(item => item.body.status !== "Tamamland\u0131")) throw new Error(`Project bulk status save mismatch: ${JSON.stringify(projectBulkStatusSave)}`);const projectUnitMenu = await evaluate(`(() => {
      page = "project-detail";
      document.body.dataset.page = "project-detail";
      window.__projectUnitAuditUnits = p9ProjectState.units;
      p9ProjectState.units = [...p9ProjectState.units, { id: 951, project_id: 91, unit_no: "A-951", block_name: "A", status: "Bekliyor", room_count: 2 }];
      document.querySelector("#content").innerHTML = '<section class="card"><article class="p9-unit-card" data-p9-unit-card="951"><button data-p9-unit-products="951">Products</button></article></section>';
      const card = document.querySelector('[data-p9-unit-card="951"]');
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 270, clientY: 240 });
      card.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return { open: menu.classList.contains("open"), prevented: event.defaultPrevented, statuses: Array.from(menu.querySelectorAll("[data-p9-unit-context-status]"), item => ({status:item.dataset.p9UnitContextStatus,checked:item.getAttribute("aria-checked")})), products: Boolean(menu.querySelector('[data-p9-unit-context-products="951"]')), separators: menu.querySelectorAll("hr.context-menu-separator").length };
    })()`);
    if (!projectUnitMenu.open || !projectUnitMenu.prevented || JSON.stringify(projectUnitMenu.statuses) !== JSON.stringify([{status:"Bekliyor",checked:"true"},{status:"Devam Ediyor",checked:"false"},{status:"Tamamland\u0131",checked:"false"}]) || !projectUnitMenu.products || projectUnitMenu.separators !== 1) throw new Error(`Project unit context menu mismatch: ${JSON.stringify(projectUnitMenu)}`);
    await capture("project-unit-context-menu-current-headless.png", "true");
    const projectUnitStatus = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      const originalLoad = loadPart9Projects;
      window.__projectUnitAuditRequest = null;
      let loads = 0;
      apiFetch = async (url, options = {}) => { window.__projectUnitAuditRequest = {url, payload: JSON.parse(options.body)}; return {ok:true}; };
      loadPart9Projects = async () => { loads++; };
      document.querySelector('#contextMenu [data-p9-unit-context-status="Devam Ediyor"]')?.click();
      await new Promise(resolve => setTimeout(resolve, 30));
      apiFetch = originalApiFetch;
      loadPart9Projects = originalLoad;
      const result = {request:window.__projectUnitAuditRequest,loads,closed:!document.querySelector("#contextMenu").classList.contains("open")};
      p9ProjectState.units = window.__projectUnitAuditUnits;
      delete window.__projectUnitAuditUnits;
      return result;
    })()`);
    if (projectUnitStatus.request?.url !== "/api/desktop/table/project_units" || projectUnitStatus.request.payload.id !== 951 || projectUnitStatus.request.payload.status !== "Devam Ediyor" || projectUnitStatus.request.payload._action !== "update" || projectUnitStatus.loads !== 1 || !projectUnitStatus.closed) throw new Error(`Project unit status action mismatch: ${JSON.stringify(projectUnitStatus)}`);
    const projectNoteDoubleClick = await evaluate(`(async () => {
      page = "projects";
      document.body.dataset.page = "projects";
      db.settings.doubleClick = true;
      const body=document.querySelector("#dialogBody"),previousBody=body.innerHTML,originalApiFetch=apiFetch;
      body.innerHTML='<div class="p9-unit-products"><table><tbody><tr><td>Part</td><td>CODE</td><td>1</td><td><button type="button" class="p9-note-edit" data-id="953" data-note="Original note">Original note</button></td><td>Active</td></tr></tbody></table></div>';
      window.__projectNoteRequest=null;
      apiFetch=async(url,options={})=>{window.__projectNoteRequest={url,payload:JSON.parse(options.body)};return {ok:true};};
      const cell=body.querySelector("td:nth-child(4)");
      cell.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const dialog=document.querySelector(".p9-unit-note-dialog"),textarea=dialog?.querySelector("textarea[name=notes]");
      const opened={open:dialog?.open===true,note:textarea?.value,title:dialog?.querySelector("h2")?.textContent};
      if(!opened.open)throw new Error("Project unit technical note editor did not open.");
      textarea.value="Updated fixture note";
      dialog.querySelector('button[type="submit"]').click();
      await new Promise(resolve=>setTimeout(resolve,0));
      apiFetch=originalApiFetch;
      const result={...opened,request:window.__projectNoteRequest,closed:!dialog.isConnected,dialogOpen:dialog.open,updatedNote:body.querySelector(".p9-note-edit")?.dataset.note};
      body.innerHTML=previousBody;
      return result;
    })()`);
    if (!projectNoteDoubleClick.open || projectNoteDoubleClick.note !== "Original note" || projectNoteDoubleClick.title !== "Teknik Not" || projectNoteDoubleClick.request?.url !== "/api/desktop/table/project_unit_products" || projectNoteDoubleClick.request.payload.id !== 953 || projectNoteDoubleClick.request.payload.notes !== "Updated fixture note" || projectNoteDoubleClick.request.payload._action !== "update" || !projectNoteDoubleClick.closed || projectNoteDoubleClick.dialogOpen || projectNoteDoubleClick.updatedNote !== "Updated fixture note") throw new Error(`Project unit note double-click mismatch: ${JSON.stringify(projectNoteDoubleClick)}`);
    await capture("project-unit-note-double-click-edit-current-headless.png", "true");
    const serviceCatalogMenu = await evaluate(`(() => {
      page = "services";
      document.body.dataset.page = "services";
      db.settings.contextMenu = true;
      window.currentGenericMeta = {table:"services"};
      window.currentGenericData = {rows:[{id:952,name:"Fixture Service"}],columns:[]};
      document.querySelector("#contextMenu").classList.remove("open");
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:300,clientY:250});
      showContext(event,"generic",0);
      const menu = document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-service-catalog-context]"),item=>item.dataset.serviceCatalogContext),separators:menu.querySelectorAll("hr.service-catalog-context-separator").length};
    })()`);
    if (!serviceCatalogMenu.open || !serviceCatalogMenu.prevented || JSON.stringify(serviceCatalogMenu.actions) !== JSON.stringify(["add","edit","delete","excel","pdf","print"]) || serviceCatalogMenu.separators !== 1) throw new Error(`Service catalog context menu mismatch: ${JSON.stringify(serviceCatalogMenu)}`);
    await capture("service-catalog-context-menu-current-headless.png", "true");
    const serviceBulkMenu = await evaluate(`(async () => {
      page="services";
      document.querySelector("#contextMenu").classList.remove("open");
      const meta={table:"services",title:"Hizmet ve Ucret Yonetimi",description:"",group:"HIZMETLER"};
      document.querySelector("#content").innerHTML=genericShell(meta);
      const originalApiFetch=apiFetch;
      apiFetch=async()=>({rows:[{id:952,name:"First Service",price_try:120,is_active:1},{id:954,name:"Second Service",price_try:240,is_active:1}],columns:["id","name","price_try","is_active"],count:2});
      await loadGenericModule(meta,"");
      apiFetch=originalApiFetch;
      const menu=document.querySelector(".labor-more-menu"),labels=[...menu.querySelectorAll("[data-service-more]")].map(button=>button.textContent.trim());
      menu.querySelector("summary").click();
      const checkboxes=[...document.querySelectorAll(".labor-services-table tbody input[type=checkbox]")];
      checkboxes[0].click();
      const selectedFirst=window.laborSelectedIds.has("952")&&window.laborMultiSelect;
      menu.querySelector('[data-service-more="edit"]').click();
      const edit={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent};
      document.querySelector("#dialogCancel")?.click();
      checkboxes[1].click();
      menu.querySelector("summary").click();
      menu.querySelector('[data-service-more="delete"]').click();
      const deletion={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent,selectedCount:(document.querySelector("#dialogBody")?.textContent.match(/2 adet hizmet/)||[]).length};
      document.querySelector("#dialogCancel")?.click();
      document.querySelectorAll(".context-menu,.service-list-context-menu").forEach(item=>{item.classList.remove("open");item.style.display="none";});
      menu.querySelector("summary").click();
      return {labels,selectedFirst,selected:[...window.laborSelectedIds],edit,deletion};
    })()`);
    await capture("service-catalog-more-menu-current-headless.png", "true");
    const serviceImportFlow = await evaluate(`(async () => {
      const menu=document.querySelector(".labor-more-menu"),input=document.querySelector("#serviceCatalogImportFile"),originalClick=input.click;
      input.click=()=>{};
      menu.open=true;
      menu.querySelector('[data-service-more="smart-import"]').click();
      const smartMode={mode:input.dataset.serviceImportMode,accept:input.accept};
      window.__serviceImportOriginalApiFetch=apiFetch;
      apiFetch=async()=>({raw_rows:[{name:"Imported Service",purchase_price:"45",currency:"TRY",desc:"Preview row",code:"SV-77"}],detected_columns:["name","purchase_price","currency","desc","code"],suggested_mapping:{name:"name",purchase_price:"purchase_price",currency:"currency",desc:"desc",code:"code"},warnings:[],engine:"fixture parser"});
      Object.defineProperty(input,"files",{configurable:true,value:[new File(["fixture"],"service.csv",{type:"text/csv"})]});
      await input.onchange({target:input});
      const preview={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent,rows:document.querySelectorAll("#serviceImportRows tr").length,mappedName:document.querySelector('[data-service-import-row] [data-service-import-field="name"]')?.value,mappedPrice:document.querySelector('[data-service-import-row] [data-service-import-field="price"]')?.value};
      return {smartMode,preview};
    })()`);
    await capture("service-catalog-import-preview-current-headless.png", "true");
    const serviceImportEdits = await evaluate(`(() => {
      const menu=document.querySelector(".labor-more-menu"),input=document.querySelector("#serviceCatalogImportFile");
      document.querySelector("[data-service-import-add]").click();
      const rowCountAfterAdd=document.querySelectorAll("#serviceImportRows tr").length;
      document.querySelector('#serviceImportRows tr:last-child input[type="checkbox"]').click();
      document.querySelector("[data-service-import-remove]").click();
      const rowCountAfterRemove=document.querySelectorAll("#serviceImportRows tr").length;
      document.querySelector("#dialogCancel").click();
      apiFetch=window.__serviceImportOriginalApiFetch;
      delete window.__serviceImportOriginalApiFetch;
      menu.open=true;
      menu.querySelector('[data-service-more="excel-import"]').click();
      const excelMode={mode:input.dataset.serviceImportMode,accept:input.accept};
      return {rowCountAfterAdd,rowCountAfterRemove,excelMode,dialogClosed:!document.querySelector("#appDialog")?.open};
    })()`);
    const serviceImportSaved = await evaluate(`(async () => {
      const menu=document.querySelector(".labor-more-menu"),input=document.querySelector("#serviceCatalogImportFile");
      menu.open=true;
      menu.querySelector('[data-service-more="smart-import"]').click();
      apiFetch=async(url,options={})=>String(url).includes("smart-import")?{raw_rows:[{name:"Confirmed Service",purchase_price:"72",currency:"TRY",desc:"Committed fixture",code:"SV-88"}],detected_columns:["name","purchase_price","currency","desc","code"],suggested_mapping:{name:"name",purchase_price:"purchase_price",currency:"currency",desc:"desc",code:"code"},warnings:[],engine:"fixture parser"}:{rows:[],count:0,columns:[]};
      Object.defineProperty(input,"files",{configurable:true,value:[new File(["fixture"],"service.csv",{type:"text/csv"})]});
      await input.onchange({target:input});
      let request=null;
      apiFetch=async(url,options={})=>{if(String(url).includes("service-definition/import"))request={url,method:options.method,payload:JSON.parse(options.body)};return {rows:[],count:0,columns:[]};};
      document.querySelector("#dialogSubmit").click();
      await new Promise(resolve=>setTimeout(resolve,100));
      return {request,dialogClosed:!document.querySelector("#appDialog")?.open};
    })()`);
    await capture("service-catalog-import-confirmed-current-headless.png", "true");
    if(JSON.stringify(serviceBulkMenu.labels)!==JSON.stringify(["\u00c7oklu Se\u00e7im","Se\u00e7ileni D\u00fczenle","Se\u00e7ileni Sil","Ak\u0131ll\u0131 \u0130\u00e7e Aktar","Excel \u0130\u00e7e Aktar"])||!serviceBulkMenu.selectedFirst||serviceBulkMenu.selected.length!==2||!serviceBulkMenu.edit.open||!String(serviceBulkMenu.edit.title).includes("D\u00fczenle")||!serviceBulkMenu.deletion.open||serviceBulkMenu.deletion.selectedCount!==1)throw new Error(`Service catalog bulk menu mismatch: ${JSON.stringify(serviceBulkMenu)}`);
    if(serviceImportFlow.smartMode.mode!=="smart-import"||!serviceImportFlow.smartMode.accept.includes(".pdf")||!serviceImportFlow.preview.open||serviceImportFlow.preview.rows!==1||serviceImportFlow.preview.mappedName!=="Imported Service"||serviceImportFlow.preview.mappedPrice!=="45"||serviceImportEdits.rowCountAfterAdd!==2||serviceImportEdits.rowCountAfterRemove!==1||serviceImportEdits.excelMode.mode!=="excel-import"||!serviceImportEdits.excelMode.accept.includes(".xlsx")||!serviceImportEdits.dialogClosed||serviceImportSaved.request?.url!=="/api/desktop/service-definition/import"||serviceImportSaved.request.method!=="POST"||serviceImportSaved.request.payload.rows?.[0]?.name!=="Confirmed Service"||serviceImportSaved.request.payload.rows?.[0]?.price!=="72"||!serviceImportSaved.dialogClosed)throw new Error(`Service import flow mismatch: ${JSON.stringify({serviceImportFlow,serviceImportEdits,serviceImportSaved})}`);
    const knowledgeMenu = await evaluate(`(async () => {
      page = "knowledge";
      document.body.dataset.page = "knowledge";
      const meta = {table:"kb_articles",label:"Knowledge Base"};
      document.querySelector("#content").innerHTML = genericShell(meta);
      const originalApiFetch = apiFetch;
      apiFetch = async () => ({rows:[{id:953,title:"Fixture Article",tags:"audit",content:"Fixture article content"}],count:1,columns:[]});
      await loadGenericModule(meta, "");
      apiFetch = originalApiFetch;
      const article = document.querySelector("[data-kb-article=\\"953\\"]");
      if (!article) throw new Error("Knowledge base article fixture did not render.");
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:320,clientY:260});
      article.dispatchEvent(event);
      const menu = document.querySelector(".kb-context-menu");
      return {open:Boolean(menu),prevented:event.defaultPrevented,actions:menu?Array.from(menu.querySelectorAll("button"),button=>button.hasAttribute("data-kb-menu-delete")?"delete":button.hasAttribute("data-kb-menu-copy")?"copy":"unknown"):[],selected:document.querySelector("[data-kb-article].active")?.dataset.kbArticle};
    })()`);
    if (!knowledgeMenu.open || !knowledgeMenu.prevented || JSON.stringify(knowledgeMenu.actions) !== JSON.stringify(["delete","copy"]) || knowledgeMenu.selected !== "953") throw new Error(`Knowledge base context menu mismatch: ${JSON.stringify(knowledgeMenu)}`);
    await capture("knowledge-base-context-menu-current-headless.png", "true");
    const knowledgeDeleteCancelled = await evaluate(`(() => {
      document.querySelector(".kb-context-menu [data-kb-menu-delete]")?.click();
      const dialog = document.querySelector("#appDialog");
      const opened = dialog?.open === true;
      const title = document.querySelector("#dialogTitle")?.textContent || "";
      document.querySelector("#dialogCancel")?.click();
      return {open:opened,title,cancelled:dialog?.open===false,menuClosed:!document.querySelector(".kb-context-menu")};
    })()`);
    if (!knowledgeDeleteCancelled.open || !knowledgeDeleteCancelled.cancelled || !knowledgeDeleteCancelled.menuClosed) throw new Error(`Knowledge base delete confirmation mismatch: ${JSON.stringify(knowledgeDeleteCancelled)}`);
    const loanerInventoryMenu = await evaluate(`(() => {
      page = "loaners";
      document.body.dataset.page = "loaners";
      db.settings.contextMenu = true;
      ayecLoanerView = "active";
      ayecLoanerDevices = [{id:954,status:"Depoda",brand_model:"Fixture Device"}];
      ayecLoanerHistory = [{id:955,device_id:954,date_returned:null}];
      document.querySelector("#content").innerHTML = '<section class="card"><div data-loaner-row="954" data-loaner-kind="depot"></div><div data-loaner-row="955" data-loaner-kind="transaction"></div></section>';
      const inventoryEvent = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:300,clientY:260});
      document.querySelector('[data-loaner-kind="depot"]').dispatchEvent(inventoryEvent);
      const menu = document.querySelector("#contextMenu");
      const inventory = {open:menu.classList.contains("open"),prevented:inventoryEvent.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-loaner-context]"),item=>item.dataset.loanerContext),separators:menu.querySelectorAll("hr.context-menu-separator").length};
      return inventory;
    })()`);
    const expectedLoanerInventory = ["add","refresh","assign","edit","delete-device"];
    if (!loanerInventoryMenu.open || !loanerInventoryMenu.prevented || JSON.stringify(loanerInventoryMenu.actions) !== JSON.stringify(expectedLoanerInventory) || loanerInventoryMenu.separators !== 1) throw new Error(`Loaner inventory context menu mismatch: ${JSON.stringify(loanerInventoryMenu)}`);
    await capture("loaner-inventory-context-menu-current-headless.png", "true");
    const loanerActiveMenu = await evaluate(`(() => {
      const menu = document.querySelector("#contextMenu");
      menu.classList.remove("open");
      const activeEvent = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:300,clientY:260});
      document.querySelector('[data-loaner-kind="transaction"]').dispatchEvent(activeEvent);
      return {open:menu.classList.contains("open"),prevented:activeEvent.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-loaner-context]"),item=>item.dataset.loanerContext),separators:menu.querySelectorAll("hr.context-menu-separator").length};
    })()`);
    if (!loanerActiveMenu.open || !loanerActiveMenu.prevented || JSON.stringify(loanerActiveMenu.actions) !== JSON.stringify(["refresh","return"]) || loanerActiveMenu.separators !== 1) throw new Error(`Loaner active context menu mismatch: ${JSON.stringify(loanerActiveMenu)}`);
    await capture("loaner-active-context-menu-current-headless.png", "true");
    const reportTemplateContext = await evaluate(`(async()=>{
      window.__reportTemplateOriginalPage=page;window.__reportTemplateOriginalApiFetch=apiFetch;
      db.settings.contextMenu=true;page="report-templates";document.body.dataset.page=page;
      apiFetch=async()=>({rows:[{id:994,category:"General",label:"Fixture report template",is_active:1,display_order:0}],count:1,columns:[]});
      render();await new Promise(resolve=>setTimeout(resolve,80));
      const row=document.querySelector('[data-template-row="994"]'),rowRect=row?.getBoundingClientRect();document.querySelector("#toastRoot")?.replaceChildren();
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:(rowRect?.left||340)+40,clientY:(rowRect?.top||270)+20});row?.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu"),rect=menu.getBoundingClientRect();return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,visible:getComputedStyle(menu).display!=="none"&&rect.width>0&&rect.height>0,computedDisplay:getComputedStyle(menu).display,style:menu.getAttribute("style"),hidden:menu.hidden,className:menu.className,rect:{left:rect.left,top:rect.top,width:rect.width,height:rect.height},selected:document.querySelector("[data-template-row].selected")?.dataset.templateRow,actions:Array.from(menu.querySelectorAll("[data-template-context]"),item=>item.dataset.templateContext)};
    })()`);
    await capture("report-template-context-menu-current-headless.png", "true");
    const reportTemplateActions = await evaluate(`(()=>{
      const menu=document.querySelector("#contextMenu");
      menu.querySelector('[data-template-context="edit"]')?.click();
      const edit={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent};document.querySelector("#dialogCancel")?.click();
      const row=document.querySelector('[data-template-row="994"]');const deleteEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:340,clientY:270});row?.dispatchEvent(deleteEvent);menu.querySelector('[data-template-context="delete"]')?.click();
      const deletion={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent};document.querySelector("#dialogCancel")?.click();
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const doubleClick={open:document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent};document.querySelector("#dialogCancel")?.click();
      const keyboardEvent=new KeyboardEvent("keydown",{key:"ContextMenu",bubbles:true,cancelable:true});row.dispatchEvent(keyboardEvent);
      const keyboardContext={prevented:keyboardEvent.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-template-context]"),item=>item.dataset.templateContext)};menu.classList.remove("open");
      apiFetch=window.__reportTemplateOriginalApiFetch;page=window.__reportTemplateOriginalPage;document.body.dataset.page=page;delete window.__reportTemplateOriginalApiFetch;delete window.__reportTemplateOriginalPage;
      return {edit,deletion,doubleClick,keyboardContext,deleteCancelled:!document.querySelector("#appDialog")?.open};
    })()`);
    if(!reportTemplateContext.open||!reportTemplateContext.prevented||!reportTemplateContext.visible||reportTemplateContext.selected!=="994"||JSON.stringify(reportTemplateContext.actions)!==JSON.stringify(["edit","delete"])||!reportTemplateActions.edit.open||!String(reportTemplateActions.edit.title).includes("D\u00fczenle")||!reportTemplateActions.deletion.open||!String(reportTemplateActions.deletion.title).includes("Sil")||!reportTemplateActions.doubleClick.open||!String(reportTemplateActions.doubleClick.title).includes("D\u00fczenle")||!reportTemplateActions.keyboardContext.prevented||!reportTemplateActions.keyboardContext.open||JSON.stringify(reportTemplateActions.keyboardContext.actions)!==JSON.stringify(["edit","delete"])||!reportTemplateActions.deleteCancelled)throw new Error(`Report-template context menu mismatch: ${JSON.stringify({reportTemplateContext,reportTemplateActions})}`);
    const quickNoteMenu = await evaluate(`(() => {
      db.settings.contextMenu = true;
      const note = {id:956,title:"Fixture Note",content:"Audit note"};
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:1279,clientY:899});
      showQuickNoteContext(event,note);
      const menu = document.querySelector("#contextMenu");
      const rect=menu.getBoundingClientRect();
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-quick-note-action]"),item=>item.dataset.quickNoteAction),rect:{left:rect.left,top:rect.top,right:rect.right,bottom:rect.bottom}};
    })()`);
    if (!quickNoteMenu.open || !quickNoteMenu.prevented || JSON.stringify(quickNoteMenu.actions) !== JSON.stringify(["edit","delete"])) throw new Error(`Quick note context menu mismatch: ${JSON.stringify(quickNoteMenu)}`);
    if (quickNoteMenu.rect.left < 0 || quickNoteMenu.rect.top < 0 || quickNoteMenu.rect.right > 1280 || quickNoteMenu.rect.bottom > 900) throw new Error(`Quick note menu exceeded viewport bounds: ${JSON.stringify(quickNoteMenu.rect)}`);
    await capture("quick-note-context-menu-current-headless.png", "true");
    const quickNoteDeleteCancelled = await evaluate(`(() => {
      document.querySelector('#contextMenu [data-quick-note-action="delete"]')?.click();
      const dialog = document.querySelector("#appDialog");
      const opened = dialog?.open === true;
      const title = document.querySelector("#dialogTitle")?.textContent || "";
      document.querySelector("#dialogCancel")?.click();
      return {opened,title,cancelled:dialog?.open===false,menuClosed:!document.querySelector("#contextMenu").classList.contains("open")};
    })()`);
    if (!quickNoteDeleteCancelled.opened || quickNoteDeleteCancelled.title !== "Notu Sil" || !quickNoteDeleteCancelled.cancelled || !quickNoteDeleteCancelled.menuClosed) throw new Error(`Quick note delete cancellation mismatch: ${JSON.stringify(quickNoteDeleteCancelled)}`);
    const quickNoteDoubleClick = await evaluate(`(async () => {
      page = "settings";
      document.body.dataset.page = "settings";
      db.settings.doubleClick = true;
      document.querySelector("#content").innerHTML='<span id="quickNoteCount"></span><select id="quickNoteFilter"></select><input id="quickNoteSearch"><div id="quickNotesHost"></div>';
      const originalApiFetch=apiFetch;
      apiFetch=async()=>({rows:[{id:968,title:"Fixture Double Click Note",label:"Fixture note body",category:"Repair",display_category:"Computer",display_order:3,is_active:1}]});
      await loadQuickNotes();
      const row=document.querySelector('tr[data-kind="quick-note"][data-id="968"]');
      if(!row)throw new Error("Quick note fixture did not render.");
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm");
      const dialogRect=dialog.getBoundingClientRect(),field= form?.querySelector('.quick-note-editor-fields>.field'),fieldLabel=field?.querySelector(':scope > label'),fieldInput=field?.querySelector('input');
      const result={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,editorHeading:form?.querySelector(".quick-note-editor h3")?.textContent,editorDescription:form?.querySelector(".quick-note-editor p")?.textContent,dialogClass:dialog.classList.contains("quick-note-editor-dialog"),dialogSize:{width:dialogRect.width,height:dialogRect.height},firstFieldAligned:Boolean(fieldLabel&&fieldInput&&fieldLabel.getBoundingClientRect().right<fieldInput.getBoundingClientRect().left&&Math.abs(fieldLabel.getBoundingClientRect().top+fieldLabel.getBoundingClientRect().height/2-fieldInput.getBoundingClientRect().top-fieldInput.getBoundingClientRect().height/2)<2),cancelLabel:document.querySelector("#dialogCancel")?.textContent,submitLabel:document.querySelector("#dialogSubmit")?.textContent,noteTitle:form?.querySelector('[name="title"]')?.value,titlePlaceholder:form?.querySelector('[name="title"]')?.placeholder,label:form?.querySelector('[name="label"]')?.value,labelType:form?.querySelector('[name="label"]')?.tagName,isActiveType:form?.querySelector('[name="is_active"]')?.type,isActiveChecked:form?.querySelector('[name="is_active"]')?.checked,category:form?.querySelector('[name="category"]')?.value,categoryOptions:Array.from(form?.querySelectorAll('#quickNoteCategories option')||[],option=>option.value)};
      apiFetch=originalApiFetch;
      return result;
    })()`);
    if (!quickNoteDoubleClick.open || quickNoteDoubleClick.title !== "H\u0131zl\u0131 Not Detay\u0131" || quickNoteDoubleClick.editorHeading !== "H\u0131zl\u0131 Not\u0131 D\u00fczenle / Ekle" || quickNoteDoubleClick.editorDescription !== "Servis ak\u0131\u015f\u0131ndaki kategori, ba\u015fl\u0131k ve not i\u00e7eri\u011fini d\u00fczenleyin." || !quickNoteDoubleClick.dialogClass || quickNoteDoubleClick.dialogSize.width !== 680 || quickNoteDoubleClick.dialogSize.height !== 760 || !quickNoteDoubleClick.firstFieldAligned || quickNoteDoubleClick.cancelLabel !== "\u0130ptal" || quickNoteDoubleClick.submitLabel !== "Kaydet" || quickNoteDoubleClick.noteTitle !== "Fixture Double Click Note" || quickNoteDoubleClick.titlePlaceholder !== "\u015eablon ba\u015fl\u0131\u011f\u0131..." || quickNoteDoubleClick.label !== "Fixture note body" || quickNoteDoubleClick.labelType !== "INPUT" || quickNoteDoubleClick.isActiveType !== "checkbox" || !quickNoteDoubleClick.isActiveChecked || quickNoteDoubleClick.category !== "Repair" || JSON.stringify(quickNoteDoubleClick.categoryOptions) !== JSON.stringify(["Ar\u0131za Notu","\u0130\u015flem Detay\u0131","Gizli Not"])) throw new Error(`Quick note double-click edit mismatch: ${JSON.stringify(quickNoteDoubleClick)}`);
    await capture("quick-note-double-click-edit-current-headless.png", "true");
    const quickNoteInactiveSave = await evaluate(`(async () => {
      const originalWrite=desktopWrite,writes=[];
      desktopWrite=async(table,payload)=>writes.push({table,payload});
      document.querySelector('#dialogForm [name="category"]').value="";
      document.querySelector('#dialogForm [name="title"]').value="";
      document.querySelector('#dialogForm [name="label"]').value="";
      document.querySelector('#dialogForm [name="display_order"]').value="-2";
      document.querySelector('#dialogForm [name="is_active"]').checked=false;
      document.querySelector("#dialogSubmit")?.click();
      for(let attempt=0;attempt<20&&document.querySelector("#appDialog")?.open;attempt++)await new Promise(resolve=>setTimeout(resolve,10));
      desktopWrite=originalWrite;
      return {closed:document.querySelector("#appDialog")?.open===false,write:writes[0]||null};
    })()`);
    if (!quickNoteInactiveSave.closed || quickNoteInactiveSave.write?.table !== "fast_notes" || quickNoteInactiveSave.write?.payload?.is_active !== 0 || quickNoteInactiveSave.write?.payload?.category !== "" || quickNoteInactiveSave.write?.payload?.title !== "" || quickNoteInactiveSave.write?.payload?.label !== "" || quickNoteInactiveSave.write?.payload?.display_order !== -2) throw new Error(`Quick note desktop-permitted values save mismatch: ${JSON.stringify(quickNoteInactiveSave)}`);
    const salesCartMenu = await evaluate(`(() => {
      page = "sales";
      document.body.dataset.page = "sales";
      db.settings.contextMenu = true;
      salesCart = [{id:"audit-line",type:"service",serviceId:88,name:"Fixture Service",qty:1,unitPriceTry:100,price:100,description:""}];
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:340,clientY:280});
      showContext(event,"sales-cart","0");
      const menu = document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-context-action]"),item=>item.dataset.contextAction),separators:menu.querySelectorAll("hr.context-menu-separator").length};
    })()`);
    const expectedSalesCartActions = ["sales-cart-quantity","sales-cart-price","sales-cart-description","sales-cart-copy","sales-cart-remove"];
    if (!salesCartMenu.open || !salesCartMenu.prevented || JSON.stringify(salesCartMenu.actions) !== JSON.stringify(expectedSalesCartActions) || salesCartMenu.separators !== 2) throw new Error(`Sales cart context menu mismatch: ${JSON.stringify(salesCartMenu)}`);
    await capture("sales-cart-context-menu-current-headless.png", "true");
    const salesCartContextActions = await evaluate(`(async () => {
      const runDialog=async(action,field,value)=>{
        showContext(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:340,clientY:280}),"sales-cart","0");
        document.querySelector('#contextMenu [data-context-action="'+action+'"]').click();
        const form=document.querySelector("#dialogForm"),input=form?.querySelector('[name="'+field+'"]');
        if(!input)throw new Error("Sales cart dialog field missing: "+field);
        input.value=value;
        await new Promise((resolve,reject)=>{form.addEventListener("submit",event=>{event.preventDefault();Promise.resolve(form.onsubmit(event)).then(resolve,reject)},{once:true});form.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));});
      };
      await runDialog("sales-cart-quantity","quantity","3");
      await runDialog("sales-cart-price","unit_price","125");
      const longDescription="Audit description ".repeat(40);
      await runDialog("sales-cart-description","description",longDescription);
      showContext(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:340,clientY:280}),"sales-cart","0");
      document.querySelector('#contextMenu [data-context-action="sales-cart-copy"]').click();
      const copied=salesCart.length===2&&salesCart[1].qty===3&&salesCart[1].unitPriceTry===125&&salesCart[1].description===longDescription;
      showContext(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:340,clientY:280}),"sales-cart","0");
      document.querySelector('#contextMenu [data-context-action="sales-cart-remove"]').click();
      return {quantity:salesCart[0]?.qty,price:salesCart[0]?.unitPriceTry,descriptionLength:salesCart[0]?.description?.length,copied,remaining:salesCart.length,dialogClosed:!document.querySelector("#appDialog")?.open};
    })()`);
    if(salesCartContextActions.quantity!==3||salesCartContextActions.price!==125||salesCartContextActions.descriptionLength!=="Audit description ".repeat(40).length||!salesCartContextActions.copied||salesCartContextActions.remaining!==1||!salesCartContextActions.dialogClosed)throw new Error(`Sales cart context actions mismatch: ${JSON.stringify(salesCartContextActions)}`);
    const appointmentMenu = await evaluate(`(() => {
      page = "appointments";
      document.body.dataset.page = "appointments";
      db.settings.contextMenu = true;
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:320,clientY:260});
      showContext(event,"appointment",957);
      const menu = document.querySelector("#contextMenu");
      const topLevel = Array.from(menu.children).filter(item=>item.matches("button"));
      const statusTrigger = Array.from(topLevel).find(item=>item.getAttribute("aria-haspopup")==="menu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:topLevel.map(item=>item.dataset.contextAction||"status-trigger"),separators:menu.querySelectorAll(":scope > hr.context-menu-separator").length,statusExpanded:statusTrigger?.getAttribute("aria-expanded"),statuses:Array.from(menu.querySelectorAll(".appointment-status-submenu [data-context-action]"),item=>item.textContent.trim())};
    })()`);
    if (!appointmentMenu.open || !appointmentMenu.prevented || JSON.stringify(appointmentMenu.actions) !== JSON.stringify(["edit-appointment","montage-prep","status-trigger","appointment-delete"]) || appointmentMenu.separators !== 1 || appointmentMenu.statusExpanded !== "false" || JSON.stringify(appointmentMenu.statuses) !== JSON.stringify(["Bekliyor","İşlemde","Tamamlandı","İptal","Gidildi","Gidilmedi"])) throw new Error(`Appointment context menu mismatch: ${JSON.stringify(appointmentMenu)}`);
    await capture("appointment-context-menu-current-headless.png", "true");
    const appointmentStatusSubmenu = await evaluate(`(() => {const menu=document.querySelector("#contextMenu");menu.querySelector('[aria-haspopup="menu"]')?.click();menu.classList.add("open");return {open:menu.classList.contains("open"),expanded:menu.querySelector('[aria-haspopup="menu"]')?.getAttribute("aria-expanded"),display:menu.querySelector(".appointment-status-submenu")?.style.display};})()`);
    if (!appointmentStatusSubmenu.open || appointmentStatusSubmenu.expanded !== "true" || appointmentStatusSubmenu.display !== "block") throw new Error(`Appointment status submenu mismatch: ${JSON.stringify(appointmentStatusSubmenu)}`);
    await capture("appointment-status-submenu-current-headless.png", "true");
    const appointmentDoubleClick = await evaluate(`(() => {
      page = "appointments";
      document.body.dataset.page = "appointments";
      db.settings.doubleClick = true;
      window.__appointmentDoubleClickPrevious={appointments:db.appointments,customers:db.customers};
      const fixtureDate=today();
      db.customers=[{id:"9720",name:"Fixture Appointment Customer"}];
      db.appointments=[{id:"9721",customerId:"9720",customer:"Fixture Appointment Customer",title:"Fixture Appointment",date:fixtureDate,time:"10:15",status:"Planlandı",technician:"Fixture Tech"}];
      render();
      const row=document.querySelector('[data-kind="appointment"][data-id="9721"]');
      if(!row)throw new Error("Appointment fixture did not render in the calendar.");
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm");
      const timeInput=form?.querySelector('[name="time"]');
      const result={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,customer:form?.querySelector('[name="customerId"]')?.value,time:timeInput?.value,storedTime:db.appointments.find(item=>item.id==="9721")?.time,appointmentId:db.appointments.find(item=>item.id==="9721")?.id};
      return result;
    })()`);
    if (!appointmentDoubleClick.open || appointmentDoubleClick.title !== "Randevuyu D\u00fczenle" || appointmentDoubleClick.customer !== "9720" || appointmentDoubleClick.time !== "10:00" || appointmentDoubleClick.appointmentId !== "9721") throw new Error(`Appointment double-click edit mismatch: ${JSON.stringify(appointmentDoubleClick)}`);
    await capture("appointment-double-click-edit-current-headless.png", "true");
    await evaluate(`(() => {const previous=window.__appointmentDoubleClickPrevious;document.querySelector("#dialogCancel")?.click();db.appointments=previous.appointments;db.customers=previous.customers;render();delete window.__appointmentDoubleClickPrevious;})()`);
    const appointmentEmptySlotDoubleClick = await evaluate(`(() => {
      page = "appointments";
      document.body.dataset.page = "appointments";
      db.settings.doubleClick = true;
      const previousAppointments=db.appointments,previousCustomers=db.customers;
      window.__appointmentEmptySlotDoubleClickPrevious={appointments:previousAppointments,customers:previousCustomers};
      db.customers=[{id:"9720",name:"Fixture Appointment Customer"}];
      db.appointments=[{id:"9721",customerId:"9720",customer:"Fixture Appointment Customer",title:"Fixture Appointment",date:today(),time:"10:15",status:"Planland\u0131",technician:"Fixture Tech"}];
      render();
      const slot=Array.from(document.querySelectorAll(".appointment-ref-slot")).find(item=>!item.querySelector('[data-kind="appointment"]'));
      if(!slot)throw new Error("Empty appointment calendar slot missing.");
      const expectedDate=slot.dataset.date,expectedTime=String(slot.dataset.time||"").slice(0,2)+":00";
      slot.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm");
      const result={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,date:form?.querySelector('[name="date"]')?.value,time:form?.querySelector('[name="time"]')?.value,expectedDate,expectedTime};
      return result;
    })()`);
    if (!appointmentEmptySlotDoubleClick.open || appointmentEmptySlotDoubleClick.title !== "Yeni Randevu" || appointmentEmptySlotDoubleClick.date !== appointmentEmptySlotDoubleClick.expectedDate || appointmentEmptySlotDoubleClick.time !== appointmentEmptySlotDoubleClick.expectedTime) throw new Error(`Appointment empty-slot double-click mismatch: ${JSON.stringify(appointmentEmptySlotDoubleClick)}`);
    await capture("appointment-empty-slot-double-click-current-headless.png", "true");
    await evaluate(`(() => {const previous=window.__appointmentEmptySlotDoubleClickPrevious;document.querySelector("#dialogCancel")?.click();if(previous){db.appointments=previous.appointments;db.customers=previous.customers;render();delete window.__appointmentEmptySlotDoubleClickPrevious;}})()`);
    const jobReportMenus = await evaluate(`(() => {
      page = "job-reports";
      document.body.dataset.page = "job-reports";
      db.settings.contextMenu = true;
      document.querySelectorAll(".service-list-context-menu").forEach(menu=>menu.remove());
      document.querySelector("#content").innerHTML = '<table><tbody><tr data-job-report-kind="job" data-job-report-id="958"><td>JOB-958</td></tr><tr data-job-report-kind="service" data-job-report-id="959"><td>SRV-959</td></tr></tbody></table>';
      const jobEvent = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:310,clientY:270});
      document.querySelector('[data-job-report-kind="job"]').dispatchEvent(jobEvent);
      const jobMenu = document.querySelector(".service-list-context-menu");
      const job = {open:Boolean(jobMenu),prevented:jobEvent.defaultPrevented,actions:jobMenu?Array.from(jobMenu.querySelectorAll("[data-job-report-context]"),item=>item.dataset.jobReportContext):[]};
      jobMenu?.remove();
      const serviceEvent = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:310,clientY:270});
      document.querySelector('[data-job-report-kind="service"]').dispatchEvent(serviceEvent);
      const serviceMenu = document.querySelector(".service-list-context-menu");
      const service = {open:Boolean(serviceMenu),prevented:serviceEvent.defaultPrevented,actions:serviceMenu?Array.from(serviceMenu.querySelectorAll("[data-job-report-context]"),item=>item.dataset.jobReportContext):[]};
      return {job,service};
    })()`);
    if (!jobReportMenus.job.open || !jobReportMenus.job.prevented || JSON.stringify(jobReportMenus.job.actions) !== JSON.stringify(["detail"])) throw new Error(`Job report context menu mismatch: ${JSON.stringify(jobReportMenus.job)}`);
    await capture("job-report-context-menu-current-headless.png", "true");
    if (!jobReportMenus.service.open || !jobReportMenus.service.prevented || JSON.stringify(jobReportMenus.service.actions) !== JSON.stringify(["detail","technician","form"])) throw new Error(`Service report context menu mismatch: ${JSON.stringify(jobReportMenus.service)}`);
    await capture("service-report-context-menu-current-headless.png", "true");
    const serviceListContextMenu = await evaluate(`(() => {
      page = "service-list";
      document.body.dataset.page = "service-list";
      currentAuthUser = {role:"Admin"};
      db.settings.contextMenu = true;
      document.querySelectorAll(".service-list-context-menu").forEach(menu=>menu.remove());
      document.querySelector("#content").innerHTML = '<section class="card"><table class="service-list-table"><tbody><tr data-kind="service" data-id="SRV-77"><td>SRV-77</td></tr></tbody></table></section>';
      const row = document.querySelector(".service-list-table tr[data-kind=service]");
      bindInteractiveRow(row);
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:300,clientY:240});
      row.dispatchEvent(event);
      const menu = document.querySelector(".service-list-context-menu:not(.service-list-context-submenu-panel)");
      return {open:Boolean(menu),prevented:event.defaultPrevented,actions:menu?Array.from(menu.querySelectorAll("[data-service-context]"),item=>item.dataset.serviceContext):[],triggers:menu?Array.from(menu.querySelectorAll("[data-service-submenu-trigger]"),item=>item.dataset.serviceSubmenuTrigger):[],separators:menu?.querySelectorAll("hr").length||0};
    })()`);
    const expectedServiceListActions = ["technician","form","edit","close","customer","customer-info","sms","whatsapp","payment","photos","print-detailed","invoice","delete"];
    if (!serviceListContextMenu.open || !serviceListContextMenu.prevented || JSON.stringify(serviceListContextMenu.actions) !== JSON.stringify(expectedServiceListActions) || JSON.stringify(serviceListContextMenu.triggers) !== JSON.stringify(["status","print"]) || serviceListContextMenu.separators !== 4) throw new Error(`Service list context menu mismatch: ${JSON.stringify(serviceListContextMenu)}`);
    await capture("service-list-context-menu-current-headless.png", "true");
    const serviceListStatusSubmenu = await evaluate(`(() => {const menu=document.querySelector(".service-list-context-menu:not(.service-list-context-submenu-panel)");menu.querySelector('[data-service-submenu-trigger="status"]')?.click();const panel=Array.from(document.querySelectorAll(".service-list-context-submenu-panel")).find(node=>!node.hidden&&node.querySelector("[data-status]"));return {expanded:menu.querySelector('[data-service-submenu-trigger="status"]')?.getAttribute("aria-expanded"),statuses:panel?Array.from(panel.querySelectorAll("[data-status]"),item=>item.dataset.status):[]};})()`);
    if (serviceListStatusSubmenu.expanded !== "true" || JSON.stringify(serviceListStatusSubmenu.statuses) !== JSON.stringify(["Bekliyor","Tamirde","Parça Bekliyor","Test Sürecinde","Hazır","Teslim Edildi","İptal"])) throw new Error(`Service list status submenu mismatch: ${JSON.stringify(serviceListStatusSubmenu)}`);
    await capture("service-list-status-submenu-current-headless.png", "true");
    const serviceListRowActionParity = await evaluate(`(() => {
      window.__serviceListRowActionPrevious = { page, dataPage: document.body.dataset.page, customers: db.customers };
      db.customers = [{ id: 9700, name: "Fixture Customer", services: [{ id: "SRV-ROW-ACTIONS", entry_date: today(), amount: 125, status: "Tamirde", urgency: "Normal", model: "Fixture Device" }] }];
      page = "service-list";
      render();
      const wrap = document.querySelector(".service-list-table-wrap");
      const table = document.querySelector(".service-list-table");
      const row = table?.querySelector('tr[data-kind="service"]');
      const actionCell = row?.lastElementChild;
      const buttons = Array.from(actionCell?.querySelectorAll("button") || []);
      const beforeScroll = { tableWidth: Math.round(table?.getBoundingClientRect().width || 0), actionWidth: Math.round(actionCell?.getBoundingClientRect().width || 0), clientWidth: wrap?.clientWidth || 0, scrollWidth: wrap?.scrollWidth || 0, buttonCount: buttons.length };
      if (wrap) wrap.scrollLeft = wrap.scrollWidth;
      const wrapRect = wrap?.getBoundingClientRect();
      const lastButtonRect = buttons.at(-1)?.getBoundingClientRect();
      return { ...beforeScroll, maxScrollLeft: wrap ? wrap.scrollWidth - wrap.clientWidth : 0, lastActionVisible: Boolean(wrapRect && lastButtonRect && lastButtonRect.width > 0 && lastButtonRect.right <= wrapRect.right + 1) };
    })()`);
    if (serviceListRowActionParity.buttonCount !== 8 || serviceListRowActionParity.tableWidth < 1066 || serviceListRowActionParity.actionWidth < 224 || serviceListRowActionParity.maxScrollLeft < 1 || !serviceListRowActionParity.lastActionVisible) throw new Error(`Service list row action layout mismatch: ${JSON.stringify(serviceListRowActionParity)}`);
    await evaluate(`(() => {const previous=window.__serviceListRowActionPrevious;db.customers=previous.customers;page=previous.page;document.body.dataset.page=previous.dataPage;render();delete window.__serviceListRowActionPrevious;})()`);
    const stockHistoryMenu = await evaluate(`(() => {
      page = "movements";
      document.body.dataset.page = "movements";
      db.settings.contextMenu = true;
      db.movements = [{id:960,description:"Fixture Stock Movement"}];
      document.querySelector("#content").innerHTML = '<section class="card"><table id="movementTable"><tbody><tr data-kind="movement" data-id="960"><td>Fixture movement</td></tr></tbody></table></section>';
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:315,clientY:275});
      document.querySelector('#movementTable tr[data-id="960"]').dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-stock-movement-context]"),item=>item.dataset.stockMovementContext),separators:menu.querySelectorAll("hr.context-menu-separator").length};
    })()`);
    if (!stockHistoryMenu.open || !stockHistoryMenu.prevented || JSON.stringify(stockHistoryMenu.actions) !== JSON.stringify(["movement-export","movement-pdf","movement-print","movement-delete"]) || stockHistoryMenu.separators !== 1) throw new Error(`Stock history context menu mismatch: ${JSON.stringify(stockHistoryMenu)}`);
    await capture("stock-history-context-menu-current-headless.png", "true");
    const stockHistoryExportActions = await evaluate(`(async () => {
      const originalFetch = window.fetch, originalCreate = URL.createObjectURL, originalRevoke = URL.revokeObjectURL, originalClick = HTMLAnchorElement.prototype.click, originalPrint = window.print;
      const requests = [], downloads = [], prints = [];
      window.fetch = async url => { requests.push(String(url)); return { ok:true, blob:async () => new Blob(["fixture"]) }; };
      URL.createObjectURL = () => "blob:stock-audit";
      URL.revokeObjectURL = () => {};
      HTMLAnchorElement.prototype.click = function () { downloads.push({ href:this.href, name:this.download }); };
      window.print = () => prints.push(true);
      const openMenu = () => document.querySelector('#movementTable tr[data-id="960"]').dispatchEvent(new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:315,clientY:275}));
      const clickAction = action => document.querySelector('#contextMenu [data-stock-movement-context="' + action + '"]')?.click();
      try {
        openMenu(); clickAction("movement-pdf");
        await new Promise(resolve => setTimeout(resolve, 0));
        const pdf = { request:requests[0] || "", download:downloads[0]?.name || "" };
        openMenu(); clickAction("movement-export");
        await new Promise(resolve => setTimeout(resolve, 0));
        const excel = { request:requests[1] || "", download:downloads[1]?.name || "" };
        openMenu(); clickAction("movement-print");
        return { pdf, excel, printCount:prints.length };
      } finally {
        window.fetch = originalFetch; URL.createObjectURL = originalCreate; URL.revokeObjectURL = originalRevoke; HTMLAnchorElement.prototype.click = originalClick; window.print = originalPrint;
      }
    })()`);
    if (!stockHistoryExportActions.pdf.request.includes("/api/desktop/stock/movements/export/pdf") || !stockHistoryExportActions.pdf.download.endsWith(".pdf") || !stockHistoryExportActions.excel.request.includes("/api/desktop/stock/movements/export/xlsx") || !stockHistoryExportActions.excel.download.endsWith(".xlsx") || stockHistoryExportActions.printCount !== 1) throw new Error(`Stock history export action mismatch: ${JSON.stringify(stockHistoryExportActions)}`);
    const stockHistoryDeleteCancelled = await evaluate(`(() => {
      document.querySelector('#contextMenu [data-stock-movement-context="movement-delete"]')?.click();
      const dialog=document.querySelector("#appDialog"),opened=dialog?.open===true,title=document.querySelector("#dialogTitle")?.textContent||"",password=document.querySelector('#dialogBody input[type="password"]');
      document.querySelector("#dialogCancel")?.click();
      return {opened,title,passwordRequired:Boolean(password?.required),cancelled:dialog?.open===false};
    })()`);
    if (!stockHistoryDeleteCancelled.opened || !stockHistoryDeleteCancelled.passwordRequired || !stockHistoryDeleteCancelled.cancelled) throw new Error(`Stock history delete confirmation mismatch: ${JSON.stringify(stockHistoryDeleteCancelled)}`);
    const voiceShortcutMenu = await evaluate(`(() => {
      page = "settings";
      document.body.dataset.page = "settings";
      settingsSection = "voice-shortcuts";
      db.settings.contextMenu = true;
      desktopSettings.voice_assistant_shortcuts = JSON.stringify([{id:"voice-audit",name:"audit_shortcut",phrases:["audit trigger"],action_type:"Sayfa",action:"dashboard",is_active:true}]);
      document.querySelector("#content").innerHTML = renderVoiceShortcuts();
      const row = document.querySelector('tr[data-kind="voice-shortcut"]');
      if (!row) throw new Error("Voice shortcut fixture did not render.");
      bindVoiceShortcuts();
      const event = new MouseEvent("contextmenu", {bubbles:true,cancelable:true,clientX:305,clientY:255});
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-context-action]"),item=>item.dataset.contextAction),separators:menu.querySelectorAll("hr.context-menu-separator").length};
    })()`);
    if (!voiceShortcutMenu.open || !voiceShortcutMenu.prevented || JSON.stringify(voiceShortcutMenu.actions) !== JSON.stringify(["voice-shortcut-edit","voice-shortcut-delete","voice-shortcut-add"]) || voiceShortcutMenu.separators !== 1) throw new Error(`Voice shortcut context menu mismatch: ${JSON.stringify(voiceShortcutMenu)}`);
    await capture("voice-shortcut-context-menu-current-headless.png", "true");
    const voiceShortcutEditCancelled = await evaluate(`(() => {
      document.querySelector('#contextMenu [data-context-action="voice-shortcut-edit"]')?.click();
      const dialog=document.querySelector("#appDialog"),opened=dialog?.open===true,form=Boolean(document.querySelector("#dialogBody .voice-shortcut-form")),title=document.querySelector("#dialogTitle")?.textContent||"";
      document.querySelector("#dialogCancel")?.click();
      return {opened,form,title,cancelled:dialog?.open===false,menuClosed:!document.querySelector("#contextMenu").classList.contains("open")};
    })()`);
    if (!voiceShortcutEditCancelled.opened || !voiceShortcutEditCancelled.form || !voiceShortcutEditCancelled.cancelled || !voiceShortcutEditCancelled.menuClosed) throw new Error(`Voice shortcut edit dialog mismatch: ${JSON.stringify(voiceShortcutEditCancelled)}`);
    await capture("voice-shortcut-edit-dialog-current-headless.png", "true");
    const voiceShortcutDoubleClick = await evaluate(`(() => {
      db.settings.doubleClick = true;
      const row=document.querySelector('tr[data-kind="voice-shortcut"][data-id="voice-audit"]');
      if(!row)throw new Error("Voice shortcut row missing for double-click.");
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm");
      const result={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,name:form?.querySelector('[name="name"]')?.value,phrases:form?.querySelector('[name="phrases"]')?.value,type:form?.querySelector('[name="action_type"]')?.value};
      document.querySelector("#dialogCancel")?.click();
      return result;
    })()`);
    if (!voiceShortcutDoubleClick.open || voiceShortcutDoubleClick.title !== "Kestirme D\u00fczenle" || voiceShortcutDoubleClick.name !== "audit_shortcut" || voiceShortcutDoubleClick.phrases !== "audit trigger" || voiceShortcutDoubleClick.type !== "Sayfa") throw new Error(`Voice shortcut double-click edit mismatch: ${JSON.stringify(voiceShortcutDoubleClick)}`);
    await capture("voice-shortcut-double-click-edit-current-headless.png", "true");
    const voiceShortcutDelete = await evaluate(`(async () => {
      const originalApiFetch=apiFetch;
      window.__voiceShortcutAuditRequest=null;
      apiFetch=async(url,options={})=>{window.__voiceShortcutAuditRequest={url,payload:JSON.parse(options.body)};return {ok:true};};
      const row=document.querySelector('tr[data-kind="voice-shortcut"]');
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:305,clientY:255}));
      document.querySelector('#contextMenu [data-context-action="voice-shortcut-delete"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,30));
      apiFetch=originalApiFetch;
      const request=window.__voiceShortcutAuditRequest,stored=JSON.parse(request?.payload?.value||"{}");
      return {url:request?.url,key:request?.payload?.key,deleted:!Object.prototype.hasOwnProperty.call(stored,"audit_shortcut"),menuClosed:!document.querySelector("#contextMenu").classList.contains("open")};
    })()`);
    if (voiceShortcutDelete.url !== "/api/desktop/table/settings" || voiceShortcutDelete.key !== "voice_assistant_shortcuts" || !voiceShortcutDelete.deleted || !voiceShortcutDelete.menuClosed) throw new Error(`Voice shortcut delete action mismatch: ${JSON.stringify(voiceShortcutDelete)}`);
    await capture("voice-shortcut-delete-result-current-headless.png", "true");
    const voiceShortcutCreate = await evaluate(`(async () => {
      const originalApiFetch=apiFetch;
      window.__voiceShortcutCreateRequest=null;
      apiFetch=async(url,options={})=>{window.__voiceShortcutCreateRequest={url,payload:JSON.parse(options.body)};return {ok:true};};
      ayecVoiceShortcutDialog();
      const form=document.querySelector("#dialogForm");
      form.querySelector('[name="name"]').value="audit_new";
      form.querySelector('[name="phrases"]').value="one, two; three";
      const type=form.querySelector('[name="action_type"]');type.value="Fonksiyon";type.dispatchEvent(new Event("change",{bubbles:true}));
      form.querySelector('[name="action"]').value="stock_comparison";
      const dialogOpened=document.querySelector("#appDialog").open;
      await new Promise((resolve,reject)=>{form.addEventListener("submit",event=>{event.preventDefault();Promise.resolve(form.onsubmit(event)).then(resolve,reject)},{once:true});form.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));});
      apiFetch=originalApiFetch;
      const request=window.__voiceShortcutCreateRequest,configuration=JSON.parse(request?.payload?.value||"{}");
      return {dialogOpened,url:request?.url,key:request?.payload?.key,shortcut:configuration.audit_new||null,dialogClosed:!document.querySelector("#appDialog").open};
    })()`);
    if (!voiceShortcutCreate.dialogOpened || voiceShortcutCreate.url !== "/api/desktop/table/settings" || voiceShortcutCreate.key !== "voice_assistant_shortcuts" || JSON.stringify(voiceShortcutCreate.shortcut?.triggers) !== JSON.stringify(["one","two","three"]) || JSON.stringify(voiceShortcutCreate.shortcut?.action) !== JSON.stringify({type:"builtin",name:"stock_comparison"}) || !voiceShortcutCreate.dialogClosed) throw new Error(`Voice shortcut create workflow mismatch: ${JSON.stringify(voiceShortcutCreate)}`);
    await capture("voice-shortcut-create-result-current-headless.png", "true");
    const partnerShipmentMenu = await evaluate(`(async () => {
      page = "partners";
      document.body.dataset.page = "partners";
      const originalApiFetch=apiFetch;
      apiFetch=async()=>({partners:[{id:1,name:"Fixture Partner",service_type:"Technical"}],selected_partner:{id:1,name:"Fixture Partner",service_type:"Technical"},shipments:[{id:961,serial_no:"P-961",customer_name:"Fixture Customer",product_name:"Fixture Product",status:"Sent"}],timeline:[],trends:[]});
      render();
      await new Promise(resolve=>setTimeout(resolve,30));
      const row=document.querySelector('[data-partner-shipment="961"]');
      if(!row)throw new Error("Partner shipment fixture did not render.");
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:320,clientY:260});
      row.dispatchEvent(event);
      apiFetch=originalApiFetch;
      const menu=document.querySelector("#contextMenu");
      return {open:menu.classList.contains("open"),prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-partner-shipment-action]"),item=>item.dataset.partnerShipmentAction),separators:menu.querySelectorAll("hr.context-menu-separator").length};
    })()`);
    if (!partnerShipmentMenu.open || !partnerShipmentMenu.prevented || JSON.stringify(partnerShipmentMenu.actions) !== JSON.stringify(["edit","shipment-documents","documents","finance","export"]) || partnerShipmentMenu.separators !== 1) throw new Error(`Partner shipment context menu mismatch: ${JSON.stringify(partnerShipmentMenu)}`);
    await capture("partner-shipment-context-menu-current-headless.png", "true");
    const partnerShipmentForm = await evaluate(`(async () => {
      db.settings.currency="USD";
      const originalApiFetch=apiFetch,photoRequests=[];
      window.__partnerPhotoOriginalApiFetch=originalApiFetch;
      apiFetch=async url=>{photoRequests.push(url);return {rows:[]}};
      document.querySelector("#partnerShipmentAdd")?.click();
      const form=document.querySelector("#dialogForm");
      const documentsButton=Boolean(document.querySelector("#partnerShipmentDocumentsButton"));
      const photoButton=document.querySelector("#partnerShipmentPhotoButton");
      photoButton?.click();
      await new Promise(resolve=>setTimeout(resolve,40));
      return {open:document.querySelector("#appDialog")?.open===true,contractReadOnly:form?.querySelector('[name="contract_type"]')?.readOnly===true,slaReadOnly:form?.querySelector('[name="sla_level"]')?.readOnly===true,currencyField:Boolean(form?.querySelector('[name="currency"]')),partnerCostCurrency:form?.querySelector('input[name="partner_cost"]')?.closest(".field")?.textContent||"",partnerCostSuffix:form?.querySelector('input[name="partner_cost"]')?.parentElement?.querySelector("span")?.textContent||"",quoteCurrency:form?.querySelector('input[name="quote_amount"]')?.closest(".field")?.textContent||"",documentsButton,photoButton:Boolean(photoButton),galleryOpen:document.querySelector(".partner-photo-dialog")?.open===true,photoListRequest:photoRequests[0]||""};
    })()`);
    if (!partnerShipmentForm.open || !partnerShipmentForm.contractReadOnly || !partnerShipmentForm.slaReadOnly || partnerShipmentForm.currencyField || partnerShipmentForm.partnerCostSuffix !== "$" || !partnerShipmentForm.quoteCurrency.includes("$") || !partnerShipmentForm.documentsButton || !partnerShipmentForm.photoButton || !partnerShipmentForm.galleryOpen || !partnerShipmentForm.photoListRequest.startsWith("/api/desktop/partners/shipment-photos?")) throw new Error(`Partner shipment form parity mismatch: ${JSON.stringify(partnerShipmentForm)}`);
    await capture("partner-shipment-form-currency-headless.png", "true");
    await evaluate(`(() => { document.querySelector(".partner-photo-dialog")?.close(); document.querySelector("#appDialog")?.close(); if(window.__partnerPhotoOriginalApiFetch)apiFetch=window.__partnerPhotoOriginalApiFetch; })()`);
    const contractDoubleClick = await evaluate(`(async () => {
      page = "contracts";
      document.body.dataset.page = "contracts";
      db.settings.doubleClick = true;
      const originalApiFetch=apiFetch;
      apiFetch=async(path)=>({contract:{id:971,title:"Fixture Contract",customer_name:"Fixture Customer",contract_type:"Maintenance",description:"Fixture"},attachments:[]});
      const host=document.querySelector("#content");
      host.innerHTML='<table class="contracts-reference-table"><tbody><tr data-contract-id="971"><td>Fixture Contract</td></tr></tbody></table>';
      const row=host.querySelector('[data-contract-id="971"]');
      row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,30));
      apiFetch=originalApiFetch;
      const dialog=document.querySelector("#appDialog");
      return {open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent,contractId:document.querySelector(".contract-detail-modal")?.dataset.contractId,detail:document.querySelector(".contract-detail-info strong")?.textContent};
    })()`);
    if (!contractDoubleClick.open || contractDoubleClick.contractId !== "971" || !contractDoubleClick.title?.includes("S\u00f6zle\u015fme Detaylar\u0131") || contractDoubleClick.detail !== "Fixture Contract") throw new Error(`Contract double-click detail mismatch: ${JSON.stringify(contractDoubleClick)}`);
    await capture("contract-double-click-detail-current-headless.png", "true");
    await evaluate('document.querySelector("#dialogCancel")?.click()');
    const statusAssistantParity = await evaluate(`(async () => {
      page = "service-status";
      document.body.dataset.page = "service-status";
      db.settings.doubleClick = true;
      desktopSettings.marquee_text = "Fixture ticker";
      const originalApiFetch=apiFetch,originalNavigate=navigate;
      const date=today();
      window.__statusAssistantNavigation=[];
      navigate=route=>window.__statusAssistantNavigation.push(route);
      apiFetch=async(url)=>{
        if(url.includes("/appointments?"))return {rows:[{id:801,date,time:"09:30",customer_name:"Fixture Customer",description:"Fixture appointment",status:"Bekliyor"},{id:802,date,time:"08:00",customer_name:"Completed Customer",status:"Tamamlandi"}],count:2};
        if(url.includes("/parts?"))return {rows:[{id:803,name:"Critical Part",stock:1,min_stock:3},{id:804,name:"Healthy Part",stock:8,min_stock:2}],count:2};
        if(url.includes("/personnel?"))return {rows:[{id:805,name:"Fixture Technician",role:"Teknisyen",status:"Musait",is_active:1},{id:806,name:"Inactive Technician",role:"Teknisyen",is_active:0}],count:2};
        if(url.includes("/devices?"))return {rows:Array.from({length:15},(_,index)=>({id:900+index,tracking_no:"DEMO-SRV-"+String(15-index).padStart(4,"0"),customer_name:"Fixture Customer "+(index+1),device_brand:"AYEC",device_model:"Test Device "+(index+1),serial_no:"SER-"+(index+1),status:index===0?"Teslim Edildi":index===1?"Parca Bekliyor":"Bekliyor",entry_date:date,urgency:index===1?"Kritik":"Normal"})),count:15,columns:["tracking_no","customer_name","device_model","status","entry_date"]};
        return {rows:[],count:0,columns:[]};
      };
      render();
      await loadGenericModule(genericModules["service-status"]);
      const appointmentText=document.querySelector("#statusAssistantAppointment")?.textContent||"";
      const stockText=document.querySelector("#statusAssistantStock")?.textContent||"";
      const personnelText=document.querySelector("#statusAssistantPersonnel")?.textContent||"";
      const personnelCount=document.querySelector("#statusAssistantPersonnelCount")?.textContent||"";
      const markupPresent=Boolean(document.querySelector(".status-wall-assistant")&&document.querySelector(".status-wall-technicians")&&document.querySelector(".status-wall-camera"));
      document.querySelector("[data-status-appointments]")?.click();
      document.querySelector("[data-status-stock]")?.click();
      document.querySelector("[data-status-personnel]")?.click();
      const result={markupPresent,appointmentText,stockText,personnelText,personnelCount,navigation:window.__statusAssistantNavigation,deviceRows:document.querySelectorAll("#statusWallHost tbody tr").length,deviceTotal:document.querySelector("#statusWallTotal")?.textContent};
      apiFetch=originalApiFetch;navigate=originalNavigate;
      return result;
    })()`);
    if (!statusAssistantParity.markupPresent || !statusAssistantParity.appointmentText.includes("1 bekleyen randevu") || !statusAssistantParity.appointmentText.includes("Fixture Customer") || !statusAssistantParity.stockText.includes("1 urun") || !statusAssistantParity.stockText.includes("Critical Part") || !statusAssistantParity.personnelText.includes("Fixture Technician") || statusAssistantParity.personnelText.includes("Inactive Technician") || statusAssistantParity.personnelCount !== "1 Aktif" || JSON.stringify(statusAssistantParity.navigation) !== JSON.stringify(["appointments","stock","personnel"]) || statusAssistantParity.deviceRows !== 9 || statusAssistantParity.deviceTotal !== "15 Cihaz") throw new Error(`Status assistant parity mismatch: ${JSON.stringify(statusAssistantParity)}`);
    await send("Emulation.setDeviceMetricsOverride", {width:1280,height:800,deviceScaleFactor:1,mobile:false});
    await evaluate(`(() => { document.querySelector("#contextMenu")?.classList.remove("open"); document.querySelectorAll(".service-list-context-menu,.service-list-context-submenu-panel,.toast").forEach(node=>node.remove()); ayecStatusRender(); })()`);
    await capture("service-status-assistant-desktop-parity-current-headless.png", "true");
    await send("Emulation.setDeviceMetricsOverride", {width:1280,height:900,deviceScaleFactor:1,mobile:false});
    const marqueeOpen = await evaluate(`(() => {
      page = "service-status";
      document.body.dataset.page = "service-status";
      window.__marqueePreviousDoubleClick = db.settings.doubleClick;
      db.settings.doubleClick = false;
      desktopSettings.marquee_text = "Fixture ticker";
      document.querySelector("#content").innerHTML='<div data-status-marquee><div class="status-wall-marquee-track"><span>Fixture ticker</span><span>Fixture ticker</span></div></div>';
      window.__marqueeOriginalApiFetch=apiFetch;
      window.__marqueeSettingsRequest=null;
      apiFetch=async(url,options={})=>{window.__marqueeSettingsRequest={url,payload:JSON.parse(options.body)};return {ok:true};};
      const marquee=document.querySelector("[data-status-marquee]");
      marquee.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const form=document.querySelector("#dialogForm");
      if(!form)throw new Error("Status marquee editor did not open.");
      const input=form.querySelector('[name="marquee_text"]');
      return {initial:input?.value||""};
    })()`);
    if (marqueeOpen.initial !== "Fixture ticker") throw new Error(`Status marquee editor initial value mismatch: ${JSON.stringify(marqueeOpen)}`);
    await capture("service-status-marquee-editor-current-headless.png", "true");
    const marqueeEdit = await evaluate(`(async () => {
      const form=document.querySelector("#dialogForm"),input=form?.querySelector('[name="marquee_text"]');
      if(!form||!input)throw new Error("Status marquee editor controls disappeared.");
      const dialog=document.querySelector("#appDialog");let closedEvent=false;dialog.addEventListener("close",()=>{closedEvent=true},{once:true});
      input.value="Fixture updated ticker";
      document.querySelector("#dialogSubmit").click();
      for(let attempt=0;attempt<20&&document.querySelector("#appDialog").open;attempt++)await new Promise(resolve=>setTimeout(resolve,10));
      apiFetch=window.__marqueeOriginalApiFetch;
      db.settings.doubleClick=window.__marqueePreviousDoubleClick;
      return {request:window.__marqueeSettingsRequest,dialogClosed:!dialog.open,closedEvent,returnValue:dialog.returnValue,submitDisabled:document.querySelector("#dialogSubmit").disabled,submitLabel:document.querySelector("#dialogSubmit").textContent,savedValue:desktopSettings.marquee_text};
    })()`);
    marqueeEdit.initial = marqueeOpen.initial;
    if (marqueeEdit.initial !== "Fixture ticker" || marqueeEdit.request?.url !== "/api/desktop/table/settings" || marqueeEdit.request?.payload?.key !== "marquee_text" || marqueeEdit.request?.payload?.value !== "Fixture updated ticker" || !marqueeEdit.dialogClosed || marqueeEdit.savedValue !== "Fixture updated ticker") throw new Error(`Status marquee edit mismatch: ${JSON.stringify(marqueeEdit)}`);
    await capture("service-status-marquee-edit-current-headless.png", "true");
    await evaluate(`(() => {page="dashboard";document.body.dataset.page="dashboard";db.settings.contextMenu=true;currentAuthUser={role:"Admin"};const service={id:77,no:"SRV-77",device:"Laptop",device_type:"Laptop",status:"Bekliyor",note:"Fixture",customerId:501,customer_name:"Fixture",customer_contact:"5550001234"};db.customers=[{id:501,name:"Fixture Customer",phone:"5550001234",services:[service]}];document.querySelector("#content").innerHTML='<section class="card">Dashboard context menu audit</section>';document.querySelectorAll(".service-list-context-menu").forEach(menu=>menu.remove());document.querySelectorAll(".service-list-context-submenu-panel").forEach(menu=>menu.remove());showContext({preventDefault(){},clientX:280,clientY:220,currentTarget:document.querySelector("#content")},"service","SRV-77")})()`);
    const status = await evaluate(`(() => { const trigger=document.querySelector('[data-service-submenu-trigger="status"]'); if(!trigger)throw new Error("Status submenu trigger missing."); trigger.dispatchEvent(new PointerEvent("pointerenter",{bubbles:false})); const panel=Array.from(document.querySelectorAll(".service-list-context-submenu-panel")).find(node=>!node.hidden&&node.querySelector("[data-status]")); return panel?Array.from(panel.querySelectorAll("[data-status]"),item=>item.dataset.status):[]; })()`);
    if (status.length !== 7) throw new Error(`Expected 7 status options; got ${status.length}.`);
    await capture("dashboard-service-status-submenu-current-headless.png", "true");
    await evaluate(`document.querySelector(".service-list-context-menu")?.remove();document.querySelectorAll(".service-list-context-submenu-panel").forEach(node=>node.remove());showContext({preventDefault(){},clientX:280,clientY:220,currentTarget:document.querySelector("#content")},"service","SRV-77")`);
    const print = await evaluate(`(() => { const trigger=document.querySelector('[data-service-submenu-trigger="print"]'); if(!trigger)throw new Error("Print submenu trigger missing."); trigger.dispatchEvent(new PointerEvent("pointerenter",{bubbles:false})); const panel=Array.from(document.querySelectorAll(".service-list-context-submenu-panel")).find(node=>!node.hidden&&node.querySelector("[data-service-print-choice]")); return panel?Array.from(panel.querySelectorAll("[data-service-print-choice]"),item=>item.dataset.servicePrintChoice):[]; })()`);
    if (JSON.stringify(print) !== JSON.stringify(["short", "detailed", "cargo", "label-a", "label-b", "form"])) throw new Error(`Unexpected print choices: ${JSON.stringify(print)}`);
    await capture("dashboard-service-print-submenu-current-headless.png", "true");
    const interaction = await evaluate(`(async() => {
      window.__auditFetches=[];
      const originalApiFetch=apiFetch;
      apiFetch=async(url,init={})=>{window.__auditFetches.push({url:String(url),method:init.method||"GET",body:init.body||""});return {ok:true};};
      document.querySelector('.service-list-context-menu [data-service-submenu-trigger="status"]')?.click();
      document.querySelector('.service-list-context-submenu-panel [data-status="Hazır"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const write=window.__auditFetches[0]||null;
      document.querySelector(".service-list-context-menu")?.remove();
      showContext({preventDefault(){},clientX:280,clientY:220,currentTarget:document.querySelector("#content")},"service","SRV-77");
      const deleteButton=document.querySelector('.service-list-context-menu [data-service-context="delete"]');
      const eventTrace=[];
      const deleteMenu=deleteButton?.closest(".service-list-context-menu");
      deleteButton?.addEventListener("click",()=>eventTrace.push("button-click"));
      deleteMenu?.addEventListener("click",event=>eventTrace.push("menu-click:"+(event.target.dataset.serviceContext||"child")));
      const menuHandler=String(deleteMenu?.onclick||"").slice(0,120);
      const menuActions=Array.from(document.querySelectorAll(".service-list-context-menu:not(.service-list-context-submenu-panel) [data-service-context]"),item=>item.dataset.serviceContext);
      deleteButton?.click();
      await new Promise(resolve=>setTimeout(resolve,30));
      const confirmOpen=document.querySelector("#appDialog")?.open||false;
      document.querySelector("#dialogCancel")?.click();
      document.querySelector(".service-list-context-menu")?.remove();
      showContext({preventDefault(){},clientX:280,clientY:220,currentTarget:document.querySelector("#content")},"service","SRV-77");
      window.__auditOpens=[];
      const originalOpen=window.open;
      window.open=(...args)=>{window.__auditOpens.push(args);return null};
      document.querySelector('.service-list-context-menu [data-service-context="whatsapp"]')?.click();
      const whatsapp=window.__auditOpens[0]||null;
      window.open=originalOpen;
      apiFetch=originalApiFetch;
      return {write:write?{url:write.url,method:write.method,payload:JSON.parse(write.body)}:null,menuActions,deleteButtonPresent:Boolean(deleteButton),eventTrace,menuHandler,deleteConfirmationOpened:confirmOpen,deleteDialogTitle:document.querySelector("#dialogTitle")?.textContent,deleteCancelled:(document.querySelector("#appDialog")?.open===false),whatsapp:whatsapp?{url:whatsapp[0],target:whatsapp[1],features:whatsapp[2]}:null,fetchCount:window.__auditFetches.length,statusTriggerFound:Boolean(document.querySelector('.service-list-context-menu [data-service-submenu-trigger="status"]')),statusPanelCount:document.querySelectorAll(".service-list-context-submenu-panel").length,statusPanelHidden:document.querySelector('.service-list-context-submenu-panel[role="menu"]')?.hidden};
    })()`);
    if (interaction.write?.url !== "/api/desktop/table/devices" || interaction.write?.method !== "POST" || interaction.write?.payload?.id !== 77 || interaction.write?.payload?.status !== "Hazır" || interaction.write?.payload?._action !== "update" || !interaction.deleteConfirmationOpened || !interaction.deleteCancelled || !interaction.whatsapp?.url?.startsWith("https://wa.me/905550001234?") || interaction.whatsapp?.features !== "noopener" || interaction.fetchCount !== 1) {
      throw new Error(`Dashboard context actions did not match their expected dispatch: ${JSON.stringify({ interaction, exceptions })}`);
    }
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    const stockImportParity = await evaluate(`(async () => {
      page = "import";
      document.body.dataset.page = "import";
      const originalApiFetch = apiFetch;
      apiFetch = async (url) => {
        if (url === "/api/desktop/smart-import") return {
          engine: "Fixture StockImportParser",
          rows: [{ code: "IMP-001", name: "Fixture Camera", category: "Security", qty: 4, min: 1, buy: 10, sell: 20, currency: "USD", barcode: "869000000001" }],
          suggested_mapping: { "Item Code": "code", "Product Name": "name" },
          warnings: ["Fixture review warning"]
        };
        throw new Error("Unexpected import audit request: " + url);
      };
      navigate("import");
      await handleImport(new File(["fixture"], "fixture.csv", { type: "text/csv" }));
      const preview = document.querySelector("#importPreview");
      const result = {
        laneCount: document.querySelectorAll(".import-lane").length,
        rows: window.importRows?.length || 0,
        name: window.importRows?.[0]?.name,
        code: window.importRows?.[0]?.code,
        quantity: window.importRows?.[0]?.qty,
        engine: window.importMeta?.engine,
        warning: (window.importMeta?.warnings || []).join(" "),
        mapping: preview?.textContent.includes("Item Code") && preview?.textContent.includes("Product Name"),
        commitAction: Boolean(preview?.querySelector('[data-action="commit-import"]')),
        addRowAction: Boolean(document.querySelector('[data-action="add-import-row"]'))
      };
      document.querySelectorAll(".toast").forEach(node => node.remove());
      apiFetch = originalApiFetch;
      return result;
    })()`);
    if (stockImportParity.laneCount !== 3 || stockImportParity.rows !== 1 || stockImportParity.name !== "Fixture Camera" || stockImportParity.code !== "IMP-001" || stockImportParity.quantity !== 4 || stockImportParity.engine !== "Fixture StockImportParser" || !stockImportParity.warning.includes("Fixture review warning") || !stockImportParity.mapping || !stockImportParity.commitAction || !stockImportParity.addRowAction) throw new Error(`Stock import parity mismatch: ${JSON.stringify(stockImportParity)}`);
    await capture("stock-smart-import-preview-current-headless.png", "true");
    const automotiveChecklistParity = await evaluate(`(async () => {
      window.__automotiveOriginalApiFetch=apiFetch;window.__automotiveOriginalHydrate=hydrateDesktop;window.__automotiveOriginalSector=currentSector;
      currentSector="otomotiv";
      window.__automotiveDamagePayload=null;
      apiFetch=async(url,options={})=>{
        if(url.includes("/automotive_service_forms?"))return {rows:[{id:707,device_id:707,tracking_no:"AUTO-DAMAGE-707",vehicle_plate:"34 TEST 07",damage_marks_json:JSON.stringify({items:[{side:"On",zone:"Kaput",status:"Cizik",note:"Existing scratch"}],general_note:"Existing note"}),checklist_json:JSON.stringify({brakes:true,road_test:false,steering:false})}],count:1};
        if(url.includes("/vehicle-maintenance/cards?"))return {rows:[{id:707,vehicle_plate:"34 TEST 07"}],count:1};
        if(url==="/api/desktop/vehicle-maintenance/history/707")return {token:"AUTO-HISTORY-707",plate:"34 TEST 07",maintenance_rows:[],service_rows:[{tracking_no:"AUTO-DAMAGE-707",status:"Bekliyor",customer_name:"Fixture Auto Customer"}]};
        if(url==="/api/desktop/technician/update"){window.__automotiveDamagePayload=JSON.parse(options.body);return {ok:true};}
        return {rows:[],count:0};
      };
      hydrateDesktop=async()=>({});
      await technicianDialog({id:707,name:"Fixture Auto Customer",phone:"5550000707"},{id:707,no:"AUTO-DAMAGE-707",device:"Ford Courier",status:"Bekliyor",vehicle_plate:"34 TEST 07",serial:"VIN-707",priority:"Normal"});
      const openButton=document.querySelector("[data-technician-damage-open]"),checklistButton=document.querySelector("[data-technician-checklist-open]"),historyButton=document.querySelector("[data-technician-vehicle-history]");
      if(!openButton||!checklistButton||!historyButton)throw new Error("Automotive technician checklist, history, or damage action missing.");
      historyButton.click();
      await new Promise(resolve=>setTimeout(resolve,20));
      const historyHost=document.querySelector("#technicianVehicleHistory"),historyHeading=historyHost?.querySelector("h3")?.textContent||"",historyRow=historyHost?.textContent.includes("AUTO-DAMAGE-707")||false,historyQr=historyHost?.querySelector("img")?.getAttribute("src")||"";
      historyButton.click();
      const initialButton=checklistButton.textContent;
      checklistButton.click();
      const dialog=document.querySelector(".automotive-checklist-dialog");
      const status=(section,label)=>Array.from(dialog?.querySelectorAll("[data-checklist-status]")||[]).find(item=>item.dataset.section===section&&item.dataset.label===label)?.value||"";
      const result={initialButton,sections:dialog?.querySelectorAll(".automotive-checklist-section").length||0,rowCount:dialog?.querySelectorAll("[data-checklist-status]").length||0,legacyBrake:status("bakim_oncesi","Fren Balatalari"),legacyRoadTest:status("bakim_sonrasi","Yol Testi"),legacySteering:status("teknisyen_ek_kontrolleri","Direksiyon ve Suspansiyon"),historyHeading,historyRow,historyQr};
      return result;
    })()`);
    if (automotiveChecklistParity.initialButton !== "Kontrol Formu (3)" || automotiveChecklistParity.sections !== 4 || automotiveChecklistParity.rowCount !== 19 || automotiveChecklistParity.legacyBrake !== "Tamam" || automotiveChecklistParity.legacyRoadTest !== "Incelenmeli" || automotiveChecklistParity.legacySteering !== "Incelenmeli" || !automotiveChecklistParity.historyHeading.includes("QR") || !automotiveChecklistParity.historyRow || !automotiveChecklistParity.historyQr.includes("history-qr/707")) throw new Error(`Automotive technician checklist/history initialization mismatch: ${JSON.stringify(automotiveChecklistParity)}`);
    await capture("automotive-technician-checklist-editor-current-headless.png", "true");
    const automotiveChecklistSave = await evaluate(`(() => {
      const dialog=document.querySelector(".automotive-checklist-dialog");
      const status=dialog.querySelector('[data-checklist-status][data-section="servis_kabul"][data-label="Ruhsat Teslimi"]');
      status.value="Degismeli";status.dispatchEvent(new Event("change",{bubbles:true}));
      const note=dialog.querySelector('[data-checklist-note][data-section="servis_kabul"][data-label="Ruhsat Teslimi"]');note.value="Fixture technician check";
      dialog.querySelector("[data-checklist-save]").click();
      const checklistButtonLabel=document.querySelector("[data-technician-checklist-open]")?.textContent||"";
      const damageButton=document.querySelector("[data-technician-damage-open]");damageButton.click();
      const damage=document.querySelector(".automotive-damage-dialog");
      return {checklistButtonLabel,initialStatus:damage?.querySelector('[data-damage-status][data-side="On"][data-zone="Kaput"]')?.value||"",initialNote:damage?.querySelector('[data-damage-note][data-side="On"][data-zone="Kaput"]')?.value||"",initialGeneral:damage?.querySelector("[data-damage-general]")?.value||"",damageButtonText:damageButton.textContent};
    })()`);
    if (automotiveChecklistSave.checklistButtonLabel !== "Kontrol Formu (19)" || automotiveChecklistSave.initialStatus !== "Cizik" || automotiveChecklistSave.initialNote !== "Existing scratch" || automotiveChecklistSave.initialGeneral !== "Existing note" || automotiveChecklistSave.damageButtonText !== "Hasar Tespiti (1)") throw new Error(`Automotive technician checklist save mismatch: ${JSON.stringify(automotiveChecklistSave)}`);
    const automotiveDamageParity=automotiveChecklistSave;
    await capture("automotive-damage-editor-current-headless.png", "true");
    const automotiveDamageSave = await evaluate(`(async () => {
      const dialog=document.querySelector(".automotive-damage-dialog"),damage=dialog.querySelector('[data-damage-status][data-side="On"][data-zone="Kaput"]');
      damage.value="Gocuk";damage.dispatchEvent(new Event("change",{bubbles:true}));
      dialog.querySelector('[data-damage-note][data-side="On"][data-zone="Kaput"]').value="Fixture updated mark";
      dialog.querySelector('[data-damage-note][data-side="On"][data-zone="Kaput"]').dispatchEvent(new Event("input",{bubbles:true}));
      dialog.querySelector("[data-damage-general]").value="Fixture updated note";
      dialog.querySelector("[data-damage-save]").click();
      const previewStatus=document.querySelector('[data-damage-preview][data-side="On"][data-zone="Kaput"]')?.dataset.status||"";
      const buttonLabel=document.querySelector("[data-technician-damage-open]")?.textContent||"";
      document.querySelector("#dialogSubmit")?.click();
      for(let attempt=0;attempt<20&&!window.__automotiveDamagePayload;attempt++)await new Promise(resolve=>setTimeout(resolve,10));
      for(let attempt=0;attempt<40&&document.querySelector("#appDialog")?.open;attempt++)await new Promise(resolve=>setTimeout(resolve,10));
      const saved=window.__automotiveDamagePayload?.automotive_form?.damage_marks;
      const savedChecklist=window.__automotiveDamagePayload?.automotive_form?.checklist;
      apiFetch=window.__automotiveOriginalApiFetch;hydrateDesktop=window.__automotiveOriginalHydrate;currentSector=window.__automotiveOriginalSector;
      return {previewStatus,buttonLabel,saved,savedChecklist,dialogClosed:!document.querySelector("#appDialog")?.open};
    })()`);
    const automotiveDamageItem=automotiveDamageSave.saved?.items?.[0];
    const checklistRuhsat=automotiveDamageSave.savedChecklist?.find(item=>item.label==="Ruhsat Teslimi"),checklistBrakes=automotiveDamageSave.savedChecklist?.find(item=>item.label==="Fren Balatalari"),checklistRoad=automotiveDamageSave.savedChecklist?.find(item=>item.label==="Yol Testi"),checklistSteering=automotiveDamageSave.savedChecklist?.find(item=>item.label==="Direksiyon ve Suspansiyon");
    if (automotiveDamageSave.previewStatus !== "Gocuk" || automotiveDamageSave.buttonLabel !== "Hasar Tespiti (1)" || automotiveDamageItem?.status !== "Gocuk" || automotiveDamageItem?.note !== "Fixture updated mark" || automotiveDamageSave.saved?.general_note !== "Fixture updated note" || automotiveDamageSave.savedChecklist?.length !== 19 || checklistRuhsat?.status !== "Degismeli" || checklistRuhsat?.note !== "Fixture technician check" || checklistBrakes?.status !== "Tamam" || checklistRoad?.status !== "Incelenmeli" || checklistSteering?.status !== "Incelenmeli" || !automotiveDamageSave.dialogClosed) throw new Error(`Automotive technician form save mismatch: ${JSON.stringify(automotiveDamageSave)}`);
    const automotiveDamageCreate = await evaluate(`(() => {
      const originalSector=currentSector;currentSector="otomotiv";
      serviceDialog("501");
      const button=document.querySelector("[data-automotive-damage-open]");
      const checklistButton=document.querySelector("[data-automotive-checklist-open]");
      if(!button||!checklistButton)throw new Error("Automotive intake checklist or damage action is missing.");
      checklistButton.click();
      const checklistDialog=document.querySelector(".automotive-checklist-dialog");
      const checklistSections=checklistDialog?.querySelectorAll(".automotive-checklist-section").length||0;
      const checklistRows=checklistDialog?.querySelectorAll("[data-checklist-status]").length||0;
      const checklistStatus=checklistDialog?.querySelector('[data-checklist-status][data-section="servis_kabul"][data-label="Ruhsat Teslimi"]');
      if(checklistStatus){checklistStatus.value="Degismeli";checklistStatus.dispatchEvent(new Event("change",{bubbles:true}));}
      const checklistNote=checklistDialog?.querySelector('[data-checklist-note][data-section="servis_kabul"][data-label="Ruhsat Teslimi"]');
      if(checklistNote)checklistNote.value="Fixture intake check";
      return {originalSector,checklistSections,checklistRows,hasChecklistNote:Boolean(checklistNote)};
    })()`);
    if (automotiveDamageCreate.checklistSections !== 3 || automotiveDamageCreate.checklistRows !== 18 || !automotiveDamageCreate.hasChecklistNote) throw new Error(`Automotive intake checklist initialization mismatch: ${JSON.stringify(automotiveDamageCreate)}`);
    await capture("automotive-checklist-editor-current-headless.png", "true");
    const automotiveChecklistCreate = await evaluate(`(() => {
      const checklistDialog=document.querySelector(".automotive-checklist-dialog");
      checklistDialog?.querySelector("[data-checklist-save]")?.click();
      const checklistLabel=document.querySelector("[data-automotive-checklist-open]")?.textContent||"";
      const button=document.querySelector("[data-automotive-damage-open]");
      button.click();
      const dialog=document.querySelector(".automotive-damage-dialog");
      const zoneCount=dialog?.querySelectorAll("[data-damage-status]").length||0;
      const hasGeneralNote=Boolean(dialog?.querySelector("[data-damage-general]"));
      const status=dialog?.querySelector('[data-damage-status][data-side="Arka"][data-zone="Bagaj"]');
      if(status){status.value="Boya Hasari";status.dispatchEvent(new Event("change",{bubbles:true}));}
      dialog?.querySelector('[data-damage-note][data-side="Arka"][data-zone="Bagaj"]')?.setAttribute("value","Intake fixture mark");
      dialog?.querySelector("[data-damage-general]")?.replaceChildren(document.createTextNode("Intake fixture note"));
      dialog?.querySelector("[data-damage-save]")?.click();
      const label=button.textContent;
      document.querySelector("#dialogCancel")?.click();
      currentSector=window.__automotiveOriginalSector;
      return {zoneCount,hasGeneralNote,label,checklistLabel,parentOpen:document.querySelector("#appDialog")?.open||false};
    })()`);
    if (automotiveChecklistCreate.zoneCount !== 16 || !automotiveChecklistCreate.hasGeneralNote || automotiveChecklistCreate.label !== "Hasar Tespiti (1)" || automotiveChecklistCreate.checklistLabel !== "Kontrol Formu (18)" || automotiveChecklistCreate.parentOpen) throw new Error(`Automotive intake editor flow mismatch: ${JSON.stringify(automotiveChecklistCreate)}`);
    const customerPickerParity = await evaluate(`(async () => {
      db.customers=[{id:"picker-audit-1",name:"Picker Audit Customer",phone:"5551002000",email:"audit@example.test",type:"Bireysel",balances:{TRY:125,USD:0,EUR:0}}];
      db.settings.contextMenu=true;
      window.ayecContextMenuEnabled=()=>true;
      window.__pickerAuditPicked="";
      customerSelect(customer=>window.__pickerAuditPicked=customer.id,"Picker Audit");
      const search=document.querySelector("#customerPickerSearch");
      search.value="audit@example.test";
      search.dispatchEvent(new Event("input",{bubbles:true}));
      const rows=[...document.querySelectorAll("#customerPickerRows tr")];
      if(rows.length!==1)throw new Error("Customer picker search mismatch: "+rows.length);
      rows[0].dispatchEvent(new MouseEvent("click",{bubbles:true}));
      rows[0].dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:90,clientY:100}));
      const menu=[...document.querySelectorAll("#contextMenu button")].map(button=>button.textContent.trim());
      if(menu.length!==3||!menu[0].includes("Bu M\\u00fc\\u015fteriyi Se\\u00e7")||!menu[1].includes("\\u0130\\u015flem Ge\\u00e7mi\\u015fi")||!menu[2].includes("M\\u00fc\\u015fteri Kayd\\u0131n\\u0131 Sil"))throw new Error("Customer picker context menu mismatch: "+JSON.stringify(menu));
      return {searchRows:rows.length,menu};
    })()`);
    await capture("customer-picker-context-menu-current-headless.png", "true");
    const customerPickerSelected = await evaluate(`(async () => {
      document.querySelector('#contextMenu [data-customer-picker-action="select"]').click();
      await new Promise(resolve=>setTimeout(resolve,100));
      return {picked:window.__pickerAuditPicked,dialogOpen:document.querySelector("#appDialog")?.open||false};
    })()`);
    if (customerPickerParity.searchRows !== 1 || customerPickerSelected.picked !== "picker-audit-1" || customerPickerSelected.dialogOpen) throw new Error(`Customer picker selection mismatch: ${JSON.stringify({customerPickerParity,customerPickerSelected})}`);
    const customerProfileParity = await evaluate(`(async () => {
      const original={apiFetch,customers:[...db.customers],activities:[...db.activities],storage:localStorage.getItem(DB_KEY)};
      const requests=[];apiFetch=async(url,options={})=>{requests.push({url,payload:JSON.parse(options.body)});return {id:812}};
      const markup=customerForm({});
      const host=document.createElement("div");host.innerHTML=markup;
      const names=[...host.querySelectorAll("[name]")].map(field=>field.name);
      const savedSector=currentSector;currentSector="otomotiv";const automotiveNames=[...new DOMParser().parseFromString(customerForm({}),"text/html").querySelectorAll("[name]")].map(field=>field.name);currentSector=savedSector;
      const sms=host.querySelector('[name="sms_enabled"]');
      const problematic=host.querySelector('[name="is_problematic"]');
      const form=document.createElement("form");form.append(host);
      const value=(name,text)=>{const field=form.querySelector('[name="'+name+'"]');if(field)field.value=text};
      value("name","Parity Customer");value("phone","+90 555 100 2000");value("device_type","Laptop");value("device_brand","Fixture Device");value("device_model","Model D");value("company_name","Parity Ltd");value("phone2","5552003000");value("email","parity@example.test");value("tax_number","1234567890");value("tax_office","Istanbul");value("term_days","30");value("limit_amount","2500");value("commission_rate","7.5");value("service_type","Genel");value("city","Istanbul");value("district","Kadikoy");value("neighborhood","Moda");value("zip_code","34710");value("street","Test Street");value("address","Test Address");value("notes","Test note");value("TRY","100");value("USD","2");value("EUR","3");sms.checked=false;problematic.checked=true;
      const saved=await saveCustomer(new FormData(form));
      const payload=requests[0]?.payload;
      let phoneError="";try{value("phone","555");await saveCustomer(new FormData(form))}catch(error){phoneError=error.message}
      db.customers=original.customers;db.activities=original.activities;apiFetch=original.apiFetch;if(original.storage===null)localStorage.removeItem(DB_KEY);else localStorage.setItem(DB_KEY,original.storage);
      return {names,automotiveNames,smsDefault:sms.defaultChecked,smsChecked:sms.checked,problematicChecked:problematic.checked,saved,requestCount:requests.length,payload,phoneError};
    })()`);
    if (!customerProfileParity.names.includes("tax_number") || !customerProfileParity.names.includes("device_type") || !customerProfileParity.automotiveNames.includes("vehicle_plate") || !customerProfileParity.automotiveNames.includes("vehicle_vin") || !customerProfileParity.names.includes("sms_enabled") || !customerProfileParity.names.includes("is_problematic") || customerProfileParity.smsDefault !== true || customerProfileParity.requestCount !== 1 || !customerProfileParity.saved || customerProfileParity.payload.company_name !== "Parity Ltd" || customerProfileParity.payload.tax_id !== "1234567890" || customerProfileParity.payload.sms_enabled !== 0 || customerProfileParity.payload.is_problematic !== 1 || customerProfileParity.payload.balances.TRY !== 100 || customerProfileParity.payload.sector_extension.device_type !== "Laptop" || !customerProfileParity.phoneError) throw new Error(`Customer profile parity mismatch: ${JSON.stringify(customerProfileParity)}`);
    const customerLocationParity = await evaluate(`(async () => {
      const originalApiFetch=apiFetch,form=document.createElement("form"),requests=[];
      form.id="dialogForm";form.innerHTML='<input name="street" value="10 Test Street"><input name="neighborhood" value="Moda"><input name="district" value="Kadikoy"><input name="city" value="Istanbul"><input name="zip_code" value="34710"><textarea name="address"></textarea><input name="latitude" type="hidden"><input name="longitude" type="hidden"><button type="button" data-customer-location-search>Search</button><button type="button" data-customer-geolocate>Locate</button><p data-customer-location-status></p><div data-customer-location-results></div>';
      document.body.append(form);
      apiFetch=async(url,options={})=>{requests.push({url,payload:JSON.parse(options.body)});if(url.endsWith("reverse-geocode"))return {display_name:"10 Test Street, Istanbul",city:"Istanbul",district:"Kadikoy",neighborhood:"Moda",street:"Test Street 10",zip_code:"34710"};return {results:[{display_name:"10 Test Street, Istanbul",lat:40.987654,lon:29.123456}]}};
      form.querySelector("[data-customer-location-search]").click();await new Promise(resolve=>setTimeout(resolve,0));
      const resultCount=form.querySelectorAll("[data-customer-location-index]").length;
      form.querySelector("[data-customer-location-index]")?.click();
      const selected={latitude:form.elements.latitude.value,longitude:form.elements.longitude.value,address:form.elements.address.value};
      const geoDescriptor=Object.getOwnPropertyDescriptor(navigator,"geolocation");Object.defineProperty(navigator,"geolocation",{configurable:true,value:{getCurrentPosition(success){success({coords:{latitude:40.100001,longitude:27.600002}})}}});
      form.querySelector("[data-customer-geolocate]").click();await new Promise(resolve=>setTimeout(resolve,0));
      const result={resultCount,request:requests[0],selected,geolocation:{latitude:form.elements.latitude.value,longitude:form.elements.longitude.value,status:form.querySelector("[data-customer-location-status]").textContent,city:form.elements.city.value},reverseRequests:requests.filter(item=>item.url.endsWith("reverse-geocode")).length};
      if(geoDescriptor)Object.defineProperty(navigator,"geolocation",geoDescriptor);else delete navigator.geolocation;
      form.remove();apiFetch=originalApiFetch;
      return result;
    })()`);
    if (customerLocationParity.resultCount !== 1 || customerLocationParity.request.url !== "/api/desktop/field-service/geocode" || customerLocationParity.selected.latitude !== "40.987654" || customerLocationParity.selected.longitude !== "29.123456" || customerLocationParity.selected.address !== "10 Test Street, Istanbul" || customerLocationParity.geolocation.latitude !== "40.100001" || customerLocationParity.geolocation.longitude !== "27.600002" || customerLocationParity.geolocation.city !== "Istanbul" || customerLocationParity.reverseRequests !== 2) throw new Error(`Customer location flow mismatch: ${JSON.stringify(customerLocationParity)}`);
    const customerMapPicker = await evaluate(`(async () => {
      const fixture=document.createElement("form");fixture.id="dialogForm";fixture.style.cssText="position:fixed;inset:20px auto auto 20px;width:760px;height:640px;z-index:99999;background:#fff;overflow:auto";fixture.innerHTML=customerForm({});document.body.append(fixture);
      fixture.querySelector("[data-customer-map-toggle]").click();
      const frame=fixture.querySelector("[data-customer-location-map]");
      for(let attempt=0;attempt<100;attempt+=1){if(frame.contentWindow?.location?.pathname==="/field-vector-map-dist/index.html"&&typeof frame.contentWindow?.initAyecTomTomMap==="function")break;await new Promise(resolve=>setTimeout(resolve,50))}
      const result={visible:!fixture.querySelector("[data-customer-map-wrap]").hidden,src:new URL(frame.src).pathname,initAvailable:typeof frame.contentWindow?.initAyecTomTomMap==="function",clickBridgeAvailable:typeof frame.contentWindow?.ayecTomTomMap?.onClick==="function"};
      fixture.remove();return result;
    })()`);
    if (!customerMapPicker.visible || customerMapPicker.src !== "/field-vector-map-dist/index.html" || !customerMapPicker.initAvailable || !customerMapPicker.clickBridgeAvailable) throw new Error(`Customer map picker mismatch: ${JSON.stringify(customerMapPicker)}`);
    process.stdout.write(JSON.stringify({ customerMapPicker, customerLocationParity, customerProfileParity, root, appLockPrompt, appLockFlow, technicianLockPrompt, technicianLockFlow, status, print, roles, interaction, fieldMenu: { ...fieldMenu, dismissed: fieldMenuDismissed }, stockMenu: { ...stockMenu, deleteDialog: stockDeleteDialog, deleteCancelled: stockDeleteCancelled }, bankMenu, installmentMenu, loanConfirmation: { ...loanConfirmation, cancelled: loanConfirmationCancelled }, externalMenu, externalDelete: { ...externalDeleteDialog, cancelled: externalDeleteCancelled }, stockLocationMenu, stockLocationUse: { ...stockLocationUse, cancelled: stockLocationUseCancelled }, vehicleMaintenanceMenu, maintenancePrint, maintenanceWhatsAppPhoneWarning, maintenanceWhatsAppPrompt, maintenanceWhatsAppCancelled, maintenanceWhatsAppAccepted, financeMenu, financePrint, dateGroupMenu, announcementMenu, announcementDelete: { ...announcementDeleteDialog, cancelled: announcementDeleteCancelled }, checkMenu, checkSubmenu, managedUserMenu, managedUserDelete: { ...managedUserDeleteDialog, cancelled: managedUserDeleteCancelled }, personnelMenu, personnelEditDialog, personnelDeleteDialog, projectTransactionDialogOpen, projectTransactionFlow, projectFinanceDynamicFilters, projectFinancePendingSegment, projectSubcontractorPaymentOpen, projectSubcontractorPaymentSave, projectTransactionDetail, projectCreationDialog, projectCreationSave, projectLifecycleOpen, projectLifecycleSave, projectUnitExportOpen, projectUnitExportDownload, projectBulkStatusOpen, projectBulkStatusSave, projectUnitMenu, projectUnitStatus, projectNoteDoubleClick, serviceCatalogMenu, serviceBulkMenu, serviceImportFlow, serviceImportEdits, serviceImportSaved, knowledgeMenu, knowledgeDeleteCancelled, loanerInventoryMenu, loanerActiveMenu, reportTemplateContext, reportTemplateActions, quickNoteMenu, quickNoteDeleteCancelled, quickNoteDoubleClick, salesCartMenu, salesCartContextActions, appointmentMenu, appointmentDoubleClick, appointmentEmptySlotDoubleClick, jobReportMenus, serviceListContextMenu, serviceListStatusSubmenu, stockHistoryMenu, stockHistoryExportActions, stockHistoryDeleteCancelled, voiceShortcutMenu, voiceShortcutEditCancelled, voiceShortcutDoubleClick, voiceShortcutDelete, voiceShortcutCreate, partnerShipmentMenu, contractDoubleClick, statusAssistantParity, marqueeEdit, stockImportParity, automotiveChecklistParity, automotiveChecklistSave, automotiveDamageParity, automotiveDamageSave, automotiveDamageCreate, automotiveChecklistCreate, customerPickerParity, customerPickerSelected, dashboardShortcutFlow, browserExceptions: exceptions.length, screenshotsCaptured, screenshotsAttempted, componentScreenshotsCaptured, screenshotFallbacks, screenshotFailures, serviceListRowActionParity }) + "\n");
  } finally {
    try { await send("Browser.close"); } catch (_) {}
    try { socket?.close(); } catch (_) {}
    try {
      const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
      const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      for (const pid of output.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
    } catch (_) {
      try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) { browser.kill(); }
    }
    await delay(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });


