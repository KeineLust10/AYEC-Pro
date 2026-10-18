const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9237);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `external-tracking-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function waitForTarget() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
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
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1268, height: 1220, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof db !== 'undefined' && typeof loadGenericModule === 'function'")) break;
      await delay(200);
    }
    const pageResult = await evaluate(`(async () => {
      for (let attempt = 0; attempt < 50 && !document.querySelector("#authRoot .auth-shell"); attempt += 1) await new Promise(resolve => setTimeout(resolve, 100));
      await new Promise(resolve => setTimeout(resolve, 100));
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.querySelector("#appShell")?.removeAttribute("inert");
      document.querySelector("#appShell")?.removeAttribute("aria-hidden");
      window.__originalExternalApiFetch = apiFetch;
      apiFetch = async url => {
        if (url.includes("external_warranty_tracking")) return { rows: [
          { id: 93, internal_tracking_no: "GAR-2026-058", customer_name: "Demo Musteri 13", product_name: "Demo Cihaz 13", external_service_name: "Yetkili Servis TR", external_service_no: "450000013", sent_date: "2026-09-14", status: "Onay Bekliyor", warranty_coverage: "-", repair_cost: null },
          { id: 94, internal_tracking_no: "GAR-2026-059", customer_name: "Demo Musteri 12", product_name: "Demo Cihaz 12", external_service_name: "Yetkili Servis TR", external_service_no: "450000012", sent_date: "2026-09-13", status: "Dis Serviste", outbound_cargo_no: "Yurti\u00e7i", warranty_coverage: "-", repair_cost: null },
          { id: 95, internal_tracking_no: "GAR-2026-060", customer_name: "Demo Musteri 11", product_name: "Demo Cihaz 11", external_service_name: "Yetkili Servis TR", external_service_no: "450000011", sent_date: "2026-09-12", status: "Musteriye Hazir", warranty_coverage: "-", repair_cost: null },
          { id: 96, internal_tracking_no: "GAR-2026-061", customer_name: "Demo Musteri 10", product_name: "Demo Cihaz 10", external_service_name: "Yetkili Servis TR", external_service_no: "450000010", sent_date: "2026-09-11", status: "Teslim Alindi", warranty_coverage: "-", repair_cost: null },
          ...Array.from({ length: 4 }, (_, index) => ({ id: 97 + index, internal_tracking_no: "GAR-2026-" + (62 + index), status: "Onay Bekliyor" })),
          ...Array.from({ length: 4 }, (_, index) => ({ id: 101 + index, internal_tracking_no: "GAR-2026-" + (66 + index), status: "Kargoya Verildi" })),
          ...Array.from({ length: 6 }, (_, index) => ({ id: 105 + index, internal_tracking_no: "GAR-2026-" + (70 + index), status: "Geri Geldi" }))
        ], columns: ["id", "internal_tracking_no", "customer_name", "product_name", "external_service_name", "external_service_no", "sent_date", "status", "notes", "outbound_cargo_no", "inbound_cargo_no", "warranty_coverage", "repair_cost"] };
        return { rows: [], columns: [], count: 0 };
      };
      window.__externalTrackingFixtureFetch = apiFetch;
      page = "logistics";
      document.body.dataset.page = "logistics";
      db.settings.doubleClick = true;
      db.settings.contextMenu = false;
      navigate("logistics");
      await new Promise(resolve => setTimeout(resolve, 80));
      const row = document.querySelector('[data-external-row="93"]');
      if (!row) throw new Error("External tracking fixture row did not render.");
      const bounds = selector => { const node=document.querySelector(selector),rect=node?.getBoundingClientRect();return rect?{x:Math.round(rect.x),y:Math.round(rect.y),width:Math.round(rect.width),height:Math.round(rect.height)}:null; };
      const rowActions=Array.from(row.querySelectorAll("[data-external-edit], [data-external-delete]"),node=>{const rect=node.getBoundingClientRect();return {action:node.hasAttribute("data-external-edit")?"edit":"delete",width:Math.round(rect.width),height:Math.round(rect.height)}});
      const pendingMetricLabel=document.querySelector("#externalTrackingPending")?.parentElement?.querySelector("footer")?.textContent.trim();
      return { rowActions, pendingMetricLabel, rowCount: document.querySelectorAll('[data-external-row]').length, columns: Array.from(document.querySelectorAll("#externalTrackingHost thead th"), node => node.innerText.replace(/\s+/g, " ").trim()), actions: Array.from(document.querySelectorAll(".external-tracking-command-row"), row => Array.from(row.querySelectorAll("button"), button => Array.from(button.attributes).find(attribute => attribute.name.startsWith("data-external-"))?.name)), monthControl: { tag: document.querySelector("#externalTrackingMonth")?.tagName, first: document.querySelector("#externalTrackingMonth option")?.textContent, second: document.querySelector("#externalTrackingMonth option:nth-child(2)")?.value, options: document.querySelectorAll("#externalTrackingMonth option").length }, summary: { total: document.querySelector("#externalTrackingTotal")?.textContent, active: document.querySelector("#externalTrackingActive")?.textContent, pending: document.querySelector("#externalTrackingPending")?.textContent, received: document.querySelector("#externalTrackingReceived")?.textContent }, statusBadges: Array.from(document.querySelectorAll("[data-external-row] .badge"), node => ({ label: node.textContent.trim(), tone: Array.from(node.classList).find(name => ["info", "warn", "danger", "success", "neutral"].includes(name)) || "", background: getComputedStyle(node).backgroundColor, color: getComputedStyle(node).color })), geometry: { tabs: bounds(".external-tracking-tabs"), header: bounds("#externalTrackingPanel .page-head"), metrics: bounds(".external-tracking-metrics"), filters: bounds(".external-tracking-filters"), table: bounds(".external-tracking-table"), firstRow: bounds("[data-external-row]") } };
    })()`);
    if (pageResult.rowCount !== 4) throw new Error(`External tracking page fixture mismatch: ${JSON.stringify(pageResult)}`);
    if (JSON.stringify(pageResult.rowActions) !== JSON.stringify([{ action: "edit", width: 74, height: 30 }, { action: "delete", width: 36, height: 30 }])) throw new Error(`External tracking row action geometry mismatch: ${JSON.stringify(pageResult.rowActions)}`);
    if (!String(pageResult.pendingMetricLabel).startsWith("Fiyat / Onay")) throw new Error(`External tracking pending metric label mismatch: ${pageResult.pendingMetricLabel}`);
    const expectedBadges = [["info", "rgb(16, 26, 43)", "rgb(37, 99, 235)"], ["danger", "rgb(127, 29, 29)", "rgb(192, 132, 252)"], ["success", "rgb(7, 48, 52)", "rgb(78, 222, 163)"], ["success", "rgb(7, 48, 52)", "rgb(78, 222, 163)"]];
    const actualBadges = pageResult.statusBadges.map(badge => [badge.tone, badge.background, badge.color]);
    if (JSON.stringify(actualBadges) !== JSON.stringify(expectedBadges)) throw new Error(`External tracking status palette mismatch: ${JSON.stringify(pageResult.statusBadges)}`);
    if (pageResult.summary.total !== "18" || pageResult.summary.active !== "5" || pageResult.summary.pending !== "5" || pageResult.summary.received !== "8") throw new Error(`External tracking summary mismatch: ${JSON.stringify(pageResult.summary)}`);
    if (JSON.stringify(pageResult.columns.slice(5).map(value => value.replace(/\n/g, " "))) !== JSON.stringify(["GARANT\u0130 KAPSAMI", "MAL\u0130YET / TUTAR", "DURUM", "\u0130\u015ELEMLER"]) || pageResult.monthControl.tag !== "SELECT" || pageResult.monthControl.first !== "T\u00FCm Aylar" || pageResult.monthControl.options !== 2) throw new Error(`External tracking table control parity mismatch: ${JSON.stringify({ columns: pageResult.columns, monthControl: pageResult.monthControl })}`);
    if (JSON.stringify(pageResult.actions) !== JSON.stringify([["data-external-cargo-sync", "data-external-manifest", "data-external-export"], ["data-external-add", "data-external-import", "data-external-documents", "data-external-multiselect"]]) || pageResult.monthControl.second !== "2026-09") throw new Error(`External tracking action layout mismatch: ${JSON.stringify({ actions: pageResult.actions, monthControl: pageResult.monthControl })}`);
    const manifestFlow = await evaluate(`(async () => {
      window.__manifestPrintCalls = 0;
      window.print = () => { window.__manifestPrintCalls += 1; };
      document.querySelector("[data-external-manifest]").click();
      const dialog = document.querySelector("#appDialog");
      const bulkRows = Array.from(document.querySelectorAll("#dialogBody .external-cargo-manifest tbody tr"), row => row.innerText.replace(/\\s+/g, " ").trim());
      document.querySelector("#dialogSubmit").click();
      const bulkPrinted = window.__manifestPrintCalls === 1;
      dialog.close("audit");
      document.querySelector('[data-external-row="94"]').click();
      document.querySelector("[data-external-manifest]").click();
      const selectedRows = Array.from(document.querySelectorAll("#dialogBody .external-cargo-manifest tbody tr"), row => row.innerText.replace(/\\s+/g, " ").trim());
      document.querySelector("#dialogSubmit").click();
      const selectedPrinted = window.__manifestPrintCalls === 2;
      dialog.close("audit");
      return {bulkCount: bulkRows.length, containsLast: bulkRows.some(row => row.includes("GAR-2026-75")), bulkPrinted, selectedCount: selectedRows.length, selectedRow: selectedRows[0] || "", excludesOther: !selectedRows.some(row => row.includes("GAR-2026-058")), selectedPrinted};
    })()`);
    if (manifestFlow.bulkCount !== 18 || !manifestFlow.containsLast || !manifestFlow.bulkPrinted || manifestFlow.selectedCount !== 1 || !manifestFlow.selectedRow.includes("GAR-2026-059") || !manifestFlow.excludesOther || !manifestFlow.selectedPrinted) throw new Error(`External cargo manifest workflow mismatch: ${JSON.stringify(manifestFlow)}`);
    const panelScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "external-tracking-panel-current-headless.png"), Buffer.from(panelScreenshot.data, "base64"));
    await evaluate(`(() => { const style=document.createElement("style");style.textContent="#appShell{display:block!important;min-height:0!important;height:auto!important;padding:0!important}#appShell>.topbar,#sidebar,#shellStatusBar{display:none!important}.main{display:block!important;min-height:0!important;overflow:visible!important}#content{padding:0!important;min-height:0!important;overflow:visible!important}.external-tracking-tabs{display:none!important}body{overflow:hidden!important}";document.head.appendChild(style); })()`);
    const isolatedGeometry = await evaluate(`(() => { const selectors=["#externalTrackingPanel .page-head",".external-tracking-metrics",".external-tracking-filters","#externalTrackingSearch","#externalTrackingStatus","#externalTrackingService","#externalTrackingMonth","[data-external-refresh]",".external-tracking-table","[data-external-row]","#externalTrackingPagination","#externalTrackingPagination>div button:first-child","#externalTrackingPagination>div b","#externalTrackingPagination>div button:last-child"];const geometry=Object.fromEntries(selectors.map(selector=>{const rect=document.querySelector(selector)?.getBoundingClientRect();return [selector,rect?{x:Math.round(rect.x),y:Math.round(rect.y),width:Math.round(rect.width),height:Math.round(rect.height)}:null]}));const backgrounds=Object.fromEntries(["html","body","#appShell",".app-shell",".main","#content","#externalTrackingPanel"].map(selector=>{const node=document.querySelector(selector);const style=node&&getComputedStyle(node);return [selector,style?{color:style.backgroundColor,image:style.backgroundImage}:null]}));return {geometry,backgrounds}; })()`);
    const pagerPrevious = isolatedGeometry.geometry["#externalTrackingPagination>div button:first-child"];
    const pagerNext = isolatedGeometry.geometry["#externalTrackingPagination>div button:last-child"];
    if (JSON.stringify(pagerPrevious) !== JSON.stringify({ x: 1108, y: 880, width: 34, height: 28 }) || JSON.stringify(pagerNext) !== JSON.stringify({ x: 1218, y: 880, width: 34, height: 28 })) throw new Error(`External tracking pager geometry differs from the Qt reference: ${JSON.stringify({ pagerPrevious, pagerNext })}`);
    const filterGeometry = Object.fromEntries(["#externalTrackingSearch", "#externalTrackingStatus", "#externalTrackingService", "#externalTrackingMonth", "[data-external-refresh]"].map(selector => [selector, isolatedGeometry.geometry[selector]]));
    const expectedFilterGeometry = { "#externalTrackingSearch": { x: 29, y: 288, width: 518, height: 38 }, "#externalTrackingStatus": { x: 555, y: 283, width: 208, height: 48 }, "#externalTrackingService": { x: 771, y: 283, width: 208, height: 48 }, "#externalTrackingMonth": { x: 987, y: 283, width: 208, height: 48 }, "[data-external-refresh]": { x: 1203, y: 289, width: 36, height: 36 } };
    if (JSON.stringify(filterGeometry) !== JSON.stringify(expectedFilterGeometry)) throw new Error(`External tracking filter geometry differs from the Qt reference: ${JSON.stringify(filterGeometry)}`);
    const isolatedScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "external-tracking-panel-isolated-headless.png"), Buffer.from(isolatedScreenshot.data, "base64"));
    await evaluate(`(() => { const tabs=document.querySelector(".external-tracking-tabs");if(tabs)tabs.style.display="none"; })()`);
    const noTabsScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "external-tracking-panel-no-web-tabs-headless.png"), Buffer.from(noTabsScreenshot.data, "base64"));
    await evaluate(`(() => { const tabs=document.querySelector(".external-tracking-tabs");if(tabs)tabs.style.display=""; })()`);
    const contextMenuFlow = await evaluate(`(async () => {
      let row=document.querySelector('[data-external-row="93"]');const menu=document.querySelector("#contextMenu");
      db.settings.contextMenu=true;row.dispatchEvent(new PointerEvent("pointerdown",{pointerType:"touch",pointerId:1,bubbles:true,cancelable:true,clientX:420,clientY:570}));await new Promise(resolve=>setTimeout(resolve,600));const touchMenu={open:menu.classList.contains("open"),targetId:menu.dataset.targetId,actions:Array.from(menu.querySelectorAll("[data-external-context]"),item=>item.dataset.externalContext)};menu.classList.remove("open","external-tracking-context");
      row=document.querySelector('[data-external-row="93"]');row.dispatchEvent(new PointerEvent("pointerdown",{pointerType:"touch",pointerId:2,bubbles:true,cancelable:true,clientX:420,clientY:570}));document.dispatchEvent(new PointerEvent("pointermove",{pointerType:"touch",pointerId:2,bubbles:true,cancelable:true,clientX:450,clientY:570}));await new Promise(resolve=>setTimeout(resolve,600));const touchMoveCanceled=!menu.classList.contains("open");
      row=document.querySelector('[data-external-row="93"]');
      db.settings.contextMenu=true;row.focus();const keyEvent=new KeyboardEvent("keydown",{key:"F10",shiftKey:true,bubbles:true,cancelable:true});row.dispatchEvent(keyEvent);const keyboardMenu={prevented:keyEvent.defaultPrevented,open:menu.classList.contains("open"),focusedAction:document.activeElement?.dataset.externalContext||""};menu.classList.remove("open","external-tracking-context");
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:420,clientY:570}));
      const labels=[...menu.querySelectorAll('[data-external-context]')].map(item=>item.textContent.trim());
      menu.querySelector('[data-external-context="edit"]').click();
      const editTitle=document.querySelector("#dialogTitle")?.textContent;document.querySelector("#dialogCancel")?.click();
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:420,clientY:570}));
      menu.querySelector('[data-external-context="delete"]').click();await new Promise(resolve=>setTimeout(resolve,0));
      const deleteTitle=document.querySelector("#dialogTitle")?.textContent;document.querySelector("#dialogCancel")?.click();
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:420,clientY:570}));
      menu.querySelector('[data-external-context="gallery"]').click();
      const galleryTitle=document.querySelector("#dialogTitle")?.textContent;document.querySelector("#dialogCancel")?.click();
      const originalFetch=window.fetch;let exportUrl="";
      window.fetch=async url=>{exportUrl=String(url);return {ok:true,blob:async()=>new Blob(["fixture"])};};
      row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:420,clientY:570}));
      menu.querySelector('[data-external-context="export"]').click();await new Promise(resolve=>setTimeout(resolve,0));
      window.fetch=originalFetch;db.settings.contextMenu=false;
      const disabledEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:420,clientY:570});row.dispatchEvent(disabledEvent);
      return {touchMenu,touchMoveCanceled,keyboardMenu,labels,editTitle,deleteTitle,galleryTitle,exportUrl,disabledDefaultPrevented:disabledEvent.defaultPrevented};
    })()`);
    if (!contextMenuFlow.touchMenu.open || contextMenuFlow.touchMenu.targetId !== "93" || JSON.stringify(contextMenuFlow.touchMenu.actions) !== JSON.stringify(["edit", "delete", "gallery", "export"]) || !contextMenuFlow.touchMoveCanceled || !contextMenuFlow.keyboardMenu.prevented || !contextMenuFlow.keyboardMenu.open || contextMenuFlow.keyboardMenu.focusedAction !== "edit" || JSON.stringify(contextMenuFlow.labels) !== JSON.stringify(["D\u00fczenle", "Sil", "Foto\u011fraf Galerisi", "Secilileri Excel D\u0131şa Aktar"]) || !String(contextMenuFlow.editTitle).includes("D\u00fczenle") || !String(contextMenuFlow.deleteTitle).includes("Sil") || contextMenuFlow.galleryTitle !== "Foto\u011fraf Galerisi" || !contextMenuFlow.exportUrl.includes("/api/desktop/external-tracking/export?ids=93") || contextMenuFlow.disabledDefaultPrevented) throw new Error(`External tracking context menu mismatch: ${JSON.stringify(contextMenuFlow)}`);
    const photoGalleryFlow = await evaluate(`(async () => {
      const photo = {id: 501, tracking_no: "GAR-2026-058", photo_label: "fixture.png", url: "/fixture.png", available: true};
      let deleted = false;
      let uploadRequest = null;
      let deleteRequest = null;
      apiFetch = async (url, options = {}) => {
        if (String(url).startsWith("/api/desktop/external-tracking/photos")) {
          if (options.method === "POST") {
            const payload = JSON.parse(options.body || "{}");
            if (payload._action === "delete") { deleteRequest = payload; deleted = true; return {ok: true}; }
            uploadRequest = {tracking_no: payload.tracking_no, label: payload.label, stage: payload.stage || "", dataLength: String(payload.data || "").length};
            return {ok: true};
          }
          return {rows: deleted ? [] : [photo]};
        }
        return {rows: [], columns: []};
      };
      const row = document.querySelector('[data-external-row="93"]');
      db.settings.contextMenu = true;
      row.dispatchEvent(new MouseEvent("contextmenu", {bubbles: true, cancelable: true, clientX: 420, clientY: 570}));
      document.querySelector('#contextMenu [data-external-context="gallery"]').click();
      await new Promise(resolve => setTimeout(resolve, 20));
      const loadedPhoto = document.querySelector('#dialogBody [data-external-photo-list] img');
      const input = document.querySelector('#dialogBody [data-external-photo-input]');
      Object.defineProperty(input, "files", {configurable: true, value: [new File(["photo-data"], "fixture.png", {type: "image/png"})]});
      await input.onchange();
      const uploadedPhoto = Boolean(document.querySelector('#dialogBody [data-external-photo-list] img'));
      document.querySelector('#dialogBody [data-external-photo-delete="501"]').click();
      await new Promise(resolve => setTimeout(resolve, 20));
      const deletedPhoto = !document.querySelector('#dialogBody [data-external-photo-list] img');
      return {title: document.querySelector("#dialogTitle")?.textContent, loadedPhoto: loadedPhoto?.getAttribute("src"), uploadedPhoto, uploadRequest, deletedPhoto, deleteRequest};
    })()`);
    if (photoGalleryFlow.title !== "Foto\u011fraf Galerisi" || photoGalleryFlow.loadedPhoto !== "/fixture.png" || !photoGalleryFlow.uploadedPhoto || photoGalleryFlow.uploadRequest?.tracking_no !== "GAR-2026-058" || photoGalleryFlow.uploadRequest?.label !== "fixture.png" || photoGalleryFlow.uploadRequest?.dataLength < 8 || !photoGalleryFlow.deletedPhoto || Number(photoGalleryFlow.deleteRequest?.id) !== 501) throw new Error(`External tracking photo gallery mismatch: ${JSON.stringify(photoGalleryFlow)}`);
    const importFlow = await evaluate(`(async () => {
      let request = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/external-tracking/import") { request = {url, payload: JSON.parse(options.body || "{}")}; return {success: 1, failures: 0}; }
        return window.__externalTrackingFixtureFetch(url);
      };
      const input = document.querySelector("[data-external-import-file]");
      const file = new File(["internal_tracking_no,customer_name\\nNEW-1,Fixture"], "fixture.csv", {type: "text/csv"});
      Object.defineProperty(input, "files", {configurable: true, value: [file]});
      input.onchange();
      await new Promise(resolve => setTimeout(resolve, 120));
      return {url: request?.url, filename: request?.payload?.filename, dataLength: String(request?.payload?.data || "").length, rowCount: document.querySelectorAll("[data-external-row]").length, toast: document.querySelector("#toast")?.textContent || ""};
    })()`);
    if (importFlow.url !== "/api/desktop/external-tracking/import" || importFlow.filename !== "fixture.csv" || importFlow.dataLength < 20 || importFlow.rowCount !== 4) throw new Error(`External tracking CSV import mismatch: ${JSON.stringify(importFlow)}`);
    const saveFlow = await evaluate(`(async () => {
      const writes = [];
      window.__externalTrackingWrites = writes;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/table/external_warranty_tracking" && options.method === "POST") { const payload = JSON.parse(options.body || "{}"); writes.push(payload); return {ok: true}; }
        if (String(url).startsWith("/api/desktop/external-tracking/photos")) return {rows: []};
        return window.__externalTrackingFixtureFetch(url);
      };
      document.querySelector("[data-external-add]").click();
      const createForm = document.querySelector("#dialogForm");
      createForm.elements.internal_tracking_no.value = "GAR-NEW-001";
      createForm.elements.customer_name.value = "Fixture Customer";
      createForm.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 40));
      const createRequest = writes[0] || null;
      document.querySelector('[data-external-row="93"] [data-external-edit]').click();
      const editForm = document.querySelector("#dialogForm");
      editForm.elements.status.value = "Geri Geldi";
      editForm.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 60));
      return {createRequest, updateRequest: writes[1] || null, closed: !document.querySelector("#appDialog")?.open, count: writes.length};
    })()`);
    if (saveFlow.count !== 2 || saveFlow.createRequest?.internal_tracking_no !== "GAR-NEW-001" || saveFlow.createRequest?.customer_name !== "Fixture Customer" || saveFlow.createRequest?.id || saveFlow.updateRequest?.id !== 93 || saveFlow.updateRequest?._action !== "update" || saveFlow.updateRequest?.status !== "Geri Geldi" || !saveFlow.closed) throw new Error(`External tracking create/update mismatch: ${JSON.stringify(saveFlow)}`);
    const filterFlow = await evaluate(`(() => {
      const month=document.querySelector("#externalTrackingMonth");
      month.value="2026-09";month.dispatchEvent(new Event("change",{bubbles:true}));
      const monthCount=document.querySelectorAll("[data-external-row]").length;
      const search=document.querySelector("#externalTrackingSearch");
      search.value="no matching record";search.dispatchEvent(new Event("input",{bubbles:true}));
      const emptyCount=document.querySelectorAll("[data-external-row]").length;
      search.value="";search.dispatchEvent(new Event("input",{bubbles:true}));month.value="";month.dispatchEvent(new Event("change",{bubbles:true}));
      return {monthCount,emptyCount,reset:search.value===""&&month.value==="",restoredCount:document.querySelectorAll("[data-external-row]").length};
    })()`);
    if (filterFlow.monthCount !== 4 || filterFlow.emptyCount !== 0 || !filterFlow.reset || filterFlow.restoredCount !== 4) throw new Error(`External tracking filter controls mismatch: ${JSON.stringify(filterFlow)}`);
    const enabledResult = await evaluate(`(() => {
      const row = document.querySelector('[data-external-row="93"]');
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
      const dialog = document.querySelector("#appDialog");
      return { opened: Boolean(dialog?.open), title: document.querySelector("#dialogTitle")?.textContent, trackingNo: document.querySelector('#dialogBody [name="internal_tracking_no"]')?.value };
    })()`);
    if (!enabledResult.opened || enabledResult.trackingNo !== "GAR-2026-058") throw new Error(`External tracking double-click did not open edit: ${JSON.stringify(enabledResult)}`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const disabledResult = await evaluate(`(() => {
      db.settings.doubleClick = false;
      document.querySelector("#appDialog")?.close("cancel");
      const row = document.querySelector('[data-external-row="93"]');
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
      const opened = Boolean(document.querySelector("#appDialog")?.open);
      return { opened };
    })()`);
    if (disabledResult.opened) throw new Error(`External tracking double-click preference was ignored: ${JSON.stringify(disabledResult)}`);
    const deleteFlow = await evaluate(`(async () => {
      const writes = window.__externalTrackingWrites;
      const row = document.querySelector('[data-external-row="93"]');
      row.querySelector("[data-external-delete]").click();
      document.querySelector("#dialogCancel").click();
      const cancelPreserved = writes.length === 2;
      row.querySelector("[data-external-delete]").click();
      document.querySelector("#dialogSubmit").click();
      await new Promise(resolve => setTimeout(resolve, 50));
      return {cancelPreserved, request: writes.at(-1), count: writes.length, dialogOpen: Boolean(document.querySelector("#appDialog")?.open)};
    })()`);
    if (!deleteFlow.cancelPreserved || deleteFlow.count !== 3 || deleteFlow.request?.id !== 93 || deleteFlow.request?._action !== "delete" || deleteFlow.dialogOpen) throw new Error(`External tracking confirmed delete mismatch: ${JSON.stringify(deleteFlow)}`);
    await evaluate(`(() => { apiFetch = window.__originalExternalApiFetch; delete window.__originalExternalApiFetch; })()`);
    fs.writeFileSync(path.join(outputDir, "external-tracking-edit-dialog-headless.png"), Buffer.from(screenshot.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    console.log(JSON.stringify({ pageResult, manifestFlow, isolatedGeometry, contextMenuFlow, photoGalleryFlow, importFlow, saveFlow, filterFlow, enabledResult, disabledResult, deleteFlow, browserExceptions: exceptions.length, headless: true }));
  } finally {
    if (socket) socket.close();
    if (browser.pid) await new Promise(resolve => {
      const killer = spawn("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      killer.once("exit", resolve);
      killer.once("error", resolve);
    });
  }
}

run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
