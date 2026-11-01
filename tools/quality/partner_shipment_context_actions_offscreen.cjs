const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputPath = path.resolve("output/playwright/partner-shipment-context-actions-headless.png");
const cdpPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 18994);
const profile = path.join(path.dirname(outputPath), `partner-shipment-context-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  const exceptions = [];
  try {
    let target;
    for (let i = 0; i < 100; i += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${cdpPort}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(150);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No hidden browser target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let id = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
      if (!message.id) return;
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let i = 0; i < 100; i += 1) {
      ready = await evaluate("document.readyState==='complete'&&typeof navigate==='function'&&typeof window.ayecOpenPartnerShipmentDialog==='function'&&typeof window.ayecOpenPartnerFinanceDialog==='function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Partner workspace scripts were not ready.");
    await delay(400);

    const audit = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      const partner={id:961,name:'Fixture Partner',type:'Servis',service_type:'Teknik',city:'Balikesir',commission_rate:0};
      const shipment={id:961,partner_id:961,customer_name:'Fixture Customer',product_name:'Fixture Device',serial_no:'SN-961',sent_at:'2026-10-18',status:'Gonderildi',outbound_tracking_no:'TRK-961'};
      const secondShipment={id:963,partner_id:961,customer_name:'Second Fixture Customer',product_name:'Second Fixture Device',serial_no:'SN-963',sent_at:'2026-10-19',status:'Gonderildi',outbound_tracking_no:'TRK-963'};
      const documents=[{id:962,title:'Shipment invoice',category:'Fatura',shipment_id:961,added_at:'2026-10-18',available:false}];
      const finance={currency:'TRY',precision:2,summary:{total_cost:1250,total_paid:200,balance:1050,customer_total:1600},entries:[{entry_date:'2026-10-17',entry_type:'PAYMENT',description:'Previous payment',payment_method:'EFT',invoice_no:'INV-1',invoice_date:'2026-10-01',display_amount:200}],reconciliation:[{shipment_id:961,product_name:'Fixture Device',cost:1250,paid:200,remaining:1050,invoice_no:'INV-1'}],shipments:[{id:961,label:'#961 | Fixture Device | SN-961 | 2026-10-18'}]};
      const calls=[];
      apiFetch=async(path,options={})=>{calls.push({path,method:options.method||'GET'});if(path.startsWith('/api/desktop/partners/workspace'))return{partners:[partner],selected_partner:partner,shipments:[shipment,secondShipment],timeline:[],trends:[]};if(path.startsWith('/api/desktop/partners/documents?'))return{documents};if(path==='/api/desktop/documents/center')return{rows:[{key:'partner:961:962',source:'Partner',title:'Shipment invoice',category:'Fatura',shipment:'961',available:false,date:'2026-10-18'}]};if(path.startsWith('/api/desktop/partners/finance'))return finance;throw Error('Unexpected API '+path)};
      navigate('partners');
      await new Promise(resolve=>setTimeout(resolve,100));
      document.querySelector('[data-partner-workspace-tab="documents"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const documentsTab={row:!!document.querySelector('[data-partner-workspace-document="962"]'),text:document.querySelector('#partnerWorkspaceDocuments')?.textContent||'',request:calls.find(item=>item.path.includes('/partners/documents?'))?.path||''};
      document.querySelector('[data-partner-workspace-tab="active"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,80));
      document.querySelector('[data-partner-workspace-tab="finance"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const financeTab={summary:document.querySelector('#partnerFinanceSummary')?.textContent||'',entry:!!document.querySelector('#partnerFinanceEntries tbody tr'),shipment:!!document.querySelector('#partnerFinanceReconciliation tbody tr'),request:calls.find(item=>item.path.includes('/partners/finance'))?.path||''};
      document.querySelector('[data-partner-workspace-tab="active"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,80));
      const row=document.querySelector('[data-partner-shipment="961"]');
      if(!row)throw Error('Fixture shipment row was not rendered.');
      const secondRow=document.querySelector('[data-partner-shipment="963"]');
      if(!secondRow)throw Error('Second fixture shipment row was not rendered.');
      secondRow.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      document.querySelector('[data-partner-shipment-action="edit"]')?.click();
      for(let i=0;i<80&&(document.querySelector('#dialogTitle')?.textContent!=="Partner Gonderi Kaydi Duzenle"||document.querySelector('#dialogForm input[name="customer_name"]')?.value!=="Second Fixture Customer");i++)await new Promise(resolve=>setTimeout(resolve,10));
      const secondRowEdit={title:document.querySelector('#dialogTitle')?.textContent||'',customer:document.querySelector('#dialogForm input[name="customer_name"]')?.value||'',product:document.querySelector('#dialogForm input[name="product_name"]')?.value||'',serial:document.querySelector('#dialogForm input[name="serial_no"]')?.value||''};
      document.querySelector('#dialogClose')?.click();
      await new Promise(resolve=>setTimeout(resolve,50));
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      const exportOriginal={create:URL.createObjectURL,revoke:URL.revokeObjectURL,click:HTMLAnchorElement.prototype.click};
      let exportTextPromise=Promise.resolve("");const exportDownloads=[];
      try{
        URL.createObjectURL=blob=>{exportTextPromise=blob.text();return "blob:partner-export-audit"};
        URL.revokeObjectURL=()=>{};
        HTMLAnchorElement.prototype.click=function(){exportDownloads.push({name:this.download,href:this.href})};
        document.querySelector('[data-partner-shipment-action="export"]')?.click();
        await new Promise(resolve=>setTimeout(resolve,20));
        const exportText=await exportTextPromise;
        var exportResult={filename:exportDownloads[0]?.name||"",text:exportText};
      }finally{URL.createObjectURL=exportOriginal.create;URL.revokeObjectURL=exportOriginal.revoke;HTMLAnchorElement.prototype.click=exportOriginal.click}
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      const menuActions=[...document.querySelectorAll('[data-partner-shipment-action]')].map(item=>item.dataset.partnerShipmentAction);
      const partnerMenu=document.querySelector("#contextMenu");
      const menuKeyboard={first:document.activeElement?.dataset.partnerShipmentAction||""};
      const sendMenuKey=key=>partnerMenu.dispatchEvent(new KeyboardEvent("keydown",{key,bubbles:true,cancelable:true}));
      sendMenuKey("ArrowDown");menuKeyboard.down=document.activeElement?.dataset.partnerShipmentAction||"";
      sendMenuKey("ArrowUp");menuKeyboard.up=document.activeElement?.dataset.partnerShipmentAction||"";
      sendMenuKey("End");menuKeyboard.end=document.activeElement?.dataset.partnerShipmentAction||"";
      sendMenuKey("Home");menuKeyboard.home=document.activeElement?.dataset.partnerShipmentAction||"";
      sendMenuKey("Escape");menuKeyboard.escapeCloses=!partnerMenu.classList.contains("open");
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      document.querySelector('[data-partner-shipment-action="edit"]')?.click();
      for(let i=0;i<80&&document.querySelector('#dialogTitle')?.textContent!=="Partner Gonderi Kaydi Duzenle";i++)await new Promise(resolve=>setTimeout(resolve,10));
      const editResult={title:document.querySelector('#dialogTitle')?.textContent||'',customer:document.querySelector('#dialogForm input[name="customer_name"]')?.value||'',product:document.querySelector('#dialogForm input[name="product_name"]')?.value||'',serial:document.querySelector('#dialogForm input[name="serial_no"]')?.value||''};
      document.querySelector('#dialogClose')?.click();
      await new Promise(resolve=>setTimeout(resolve,50));
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      document.querySelector('[data-partner-shipment-action="documents"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const documentCenterResult={title:document.querySelector('#dialogTitle')?.textContent||'',row:!!document.querySelector('[data-document-key="partner:961:962"]'),text:document.querySelector('#externalDocumentsHost')?.textContent||'',request:calls.find(item=>item.path==='/api/desktop/documents/center')?.path||''};
      document.querySelector('#dialogClose')?.click();
      await new Promise(resolve=>setTimeout(resolve,50));
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      document.querySelector('[data-partner-shipment-action="shipment-documents"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const documentsResult={title:document.querySelector('#dialogTitle')?.textContent||'',partner:document.querySelector('.partner-web-documents p')?.textContent||'',row:!!document.querySelector('[data-partner-document-id="962"]'),request:calls.find(item=>item.path.includes('/partners/documents?')&&item.path.includes('shipment_id='))?.path||''};
      document.querySelector('#dialogClose')?.click();
      await new Promise(resolve=>setTimeout(resolve,50));
      row.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:420,clientY:280}));
      document.querySelector('[data-partner-shipment-action="finance"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,120));
      const financeResult={title:document.querySelector('#dialogTitle')?.textContent||'',partner:document.querySelector('.partner-web-finance h3')?.textContent||'',entry:!!document.querySelector('#partnerFinanceEntries tbody tr'),shipment:!!document.querySelector('#partnerFinanceReconciliation tbody tr'),shipmentOption:!!document.querySelector('#dialogForm select[name="shipment_id"] option[value="961"]'),request:calls.find(item=>item.path.includes('/partners/finance'))?.path||''};
      return{menuActions:menuActions,menuKeyboard:menuKeyboard,secondRowEdit:secondRowEdit,edit:editResult,export:exportResult,documentCenter:documentCenterResult,documentsTab,documents:documentsResult,financeTab,finance:financeResult,calls:calls};
    })()`);
    if (JSON.stringify(audit.menuActions) !== JSON.stringify(["edit", "shipment-documents", "documents", "finance", "export"]) || audit.menuKeyboard.first !== "edit" || audit.menuKeyboard.down !== "shipment-documents" || audit.menuKeyboard.up !== "edit" || audit.menuKeyboard.end !== "export" || audit.menuKeyboard.home !== "edit" || !audit.menuKeyboard.escapeCloses || audit.secondRowEdit.title !== "Partner Gonderi Kaydi Duzenle" || audit.secondRowEdit.customer !== "Second Fixture Customer" || audit.secondRowEdit.product !== "Second Fixture Device" || audit.secondRowEdit.serial !== "SN-963" || audit.edit.title !== "Partner Gonderi Kaydi Duzenle" || audit.edit.customer !== "Fixture Customer" || audit.edit.product !== "Fixture Device" || audit.edit.serial !== "SN-961" || audit.export.filename !== "partner_sevkleri.csv" || !audit.export.text.includes("Fixture Customer") || !audit.export.text.includes("Fixture Device") || !audit.export.text.includes("SN-961") || !audit.export.text.includes("TRK-961") || audit.documentCenter.title !== "Belge Merkezi" || !audit.documentCenter.row || !audit.documentCenter.text.includes("Shipment invoice") || audit.documentCenter.request !== "/api/desktop/documents/center" || !audit.documentsTab.row || !audit.documentsTab.text.includes("Shipment invoice") || audit.documentsTab.request !== "/api/desktop/partners/documents?partner_id=961" || !audit.financeTab.summary.includes("1.250,00") || !audit.financeTab.entry || !audit.financeTab.shipment || audit.financeTab.request !== "/api/desktop/partners/finance?partner_id=961" || audit.documents.title !== "Partner Belgeleri" || !audit.documents.partner.includes("Fixture Partner") || !audit.documents.row || audit.documents.request !== "/api/desktop/partners/documents?partner_id=961&shipment_id=961" || audit.finance.title !== "Partner Finans Hareketleri" || audit.finance.partner !== "Fixture Partner" || !audit.finance.entry || !audit.finance.shipment || !audit.finance.shipmentOption || audit.finance.request !== "/api/desktop/partners/finance?partner_id=961" || exceptions.length) {
      throw new Error(`Partner shipment context actions failed: ${JSON.stringify({ audit, exceptions })}`);
    }
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
    process.stdout.write(`${JSON.stringify({ audit, exceptions, screenshot: outputPath, headless: true })}\n`);
  } finally {
    try { socket?.close(); } catch (_) {}
    try {
      spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" });
      const safeProfile = profile.replace(/'/g, "''");
      const cleanup = `$roots=Get-CimInstance Win32_Process -Filter "Name = 'msedge.exe'" | Where-Object { $_.CommandLine -like '*${safeProfile}*' -and $_.CommandLine -match '--remote-debugging-port=${cdpPort}' -and $_.CommandLine -notmatch '--type=' }; foreach ($root in $roots) { taskkill.exe /PID $root.ProcessId /T /F | Out-Null }`;
      spawnSync("powershell.exe", ["-NoProfile", "-Command", cleanup], { stdio: "ignore" });
    } catch (_) { browser.kill(); }
  }
}

run().catch(error => { process.stderr.write(`${String(error.stack || error)}\n`); process.exitCode = 1; });
