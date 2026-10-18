const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || (9400 + process.pid % 400));
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `project-unit-sale-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page" && item.url.startsWith(baseUrl)); } catch (_) {}
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
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      message.error ? entry.reject(new Error(message.error.message)) : entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 800, height: 836, deviceScaleFactor: 1, mobile: false });
    await send("Page.navigate", { url: baseUrl });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof p9OpenProjectUnitSale === 'function' && document.querySelector('#appDialog')");
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("Project unit sale code did not load.");
    const openState = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      p9ProjectState.projects=[{id:42,name:'Fixture Project',currency:'TRY'}];
      p9ProjectState.selectedId=42;
      p9ProjectState.units=[{id:954,project_id:42,block_name:'A',unit_no:'A-12',status:'Satilik',price:200000}];
      p9ProjectState.loaded=true;p9ProjectState.loading=false;
      window.__saleRequests=[];window.__salePrints=0;
      const originalApiFetch=apiFetch,originalLoad=loadPart9Projects,originalPrint=window.print;
      apiFetch=async(url,options={})=>{const request={url,payload:options.body?JSON.parse(options.body):null};window.__saleRequests.push(request);if(url==='/api/desktop/table/personnel?limit=1000')return{rows:[{name:'Fixture Rep'}]};if(url==='/api/desktop/projects/unit-sales')return{ok:true,sale_id:1};return{rows:[]}};
      loadPart9Projects=async()=>{p9ProjectState.loaded=true;p9ProjectState.units[0].status='Satildi';p9ProjectState.units[0].price=200000};
      window.print=()=>{window.__salePrints+=1};
      const button=document.createElement('button');button.dataset.p9UnitSale='954';document.body.append(button);button.click();
      await new Promise(resolve=>setTimeout(resolve,80));
      const dialog=document.querySelector('#appDialog');
      window.__saleAudit={originalApiFetch,originalLoad,originalPrint,button};
      const rect=dialog.getBoundingClientRect(),style=getComputedStyle(dialog);
      return{open:dialog.open,title:document.querySelector('#dialogTitle').textContent,fields:Array.from(dialog.querySelectorAll('#dialogBody input[name],#dialogBody textarea[name],#dialogBody select[name]'),node=>node.name),tabs:Array.from(dialog.querySelectorAll('[data-p9-sale-tab]'),node=>node.dataset.p9SaleTab),footer:Array.from(dialog.querySelectorAll('#dialogFooter [data-p9-sale-submit]'),node=>node.dataset.p9SaleSubmit),layout:{width:Math.round(rect.width),height:Math.round(rect.height),cssHeight:style.height,viewport:[innerWidth,innerHeight],classes:dialog.className}}
    })()`);
    const expectedFields = ["buyer_name", "buyer_tc", "buyer_phone", "buyer_email", "buyer_address", "list_price", "sale_price", "down_payment_rate", "down_payment_amount", "remaining_balance", "delivery_date", "sales_rep", "notes", "sale_action"];
    if (!openState?.open || openState.tabs.join(",") !== "info,plan,docs,map" || expectedFields.some(field => !openState.fields.includes(field)) || openState.footer.join(",") !== "print,proforma" || openState.layout.width !== 720) throw new Error(`Project unit sale form mismatch: ${JSON.stringify(openState)}`);
    const box = await evaluate("(()=>{const r=document.querySelector('#appDialog').getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}})()");
    const image = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: {...box, scale: 1} });
    const screenshotPath = path.join(outputDir, "project-unit-sale-web-reference.png");
    fs.writeFileSync(screenshotPath, Buffer.from(image.data, "base64"));
    const discardState = await evaluate(`(async()=>{
      const dialog=document.querySelector('#appDialog'),form=document.querySelector('#dialogForm');
      form.elements.buyer_name.value='Discard fixture';form.elements.buyer_name.dispatchEvent(new Event('input',{bubbles:true}));
      document.querySelector('#dialogCancel').click();
      await new Promise(resolve=>setTimeout(resolve,0));
      const warning=document.querySelector('.p9-sale-discard-dialog');
      const prompted=warning?.open===true&&dialog.open;
      warning.querySelector('[data-p9-sale-keep]').click();
      const kept=dialog.open&&!warning.open;
      document.querySelector('#dialogCancel').click();warning.querySelector('[data-p9-sale-discard]').click();
      const discarded=!dialog.open;
      window.__saleAudit.button.click();await new Promise(resolve=>setTimeout(resolve,80));
      return{prompted,kept,discarded,reopened:dialog.open}
    })()`);
    const interactions = await evaluate(`(async()=>{
      const dialog=document.querySelector('#appDialog'),form=document.querySelector('#dialogForm');
      const input=(name,value)=>{const control=form.elements[name];control.value=value;control.dispatchEvent(new Event('input',{bubbles:true}));control.dispatchEvent(new Event('change',{bubbles:true}))};
      input('buyer_name','Fixture Buyer');input('buyer_tc','10000000146');input('buyer_phone','5551234567');input('buyer_email','buyer@example.test');input('buyer_address','Example Street 1');input('list_price','220000');input('sale_price','200000');input('down_payment_rate','10');input('delivery_date',new Date(Date.now()+30*86400000-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16));
      const totals={down:form.elements.down_payment_amount.value,remaining:form.elements.remaining_balance.value};
      dialog.querySelector('[data-p9-sale-tab="plan"]').click();dialog.querySelector('[data-p9-sale-plan-add]').click();dialog.querySelector('[data-p9-sale-plan-add]').click();
      const firstPlan=dialog.querySelector('[data-p9-sale-plan] tr');firstPlan.click();dialog.querySelector('[data-p9-sale-plan-remove]').click();
      const plan=dialog.querySelector('[data-p9-sale-plan] tr');plan.querySelector('[name="plan_amount"]').value='180000';plan.querySelector('[name="plan_status"]').value='Bekliyor';
      dialog.querySelector('[data-p9-sale-tab="docs"]').click();
      const fileInput=dialog.querySelector('[data-p9-sale-doc-input]'),agreement=new File(['fixture'],'agreement.pdf',{type:'application/pdf'}),removeFile=new File(['fixture'],'remove-me.txt',{type:'text/plain'});
      Object.defineProperty(fileInput,'files',{configurable:true,value:[agreement,removeFile]});fileInput.dispatchEvent(new Event('change',{bubbles:true}));
      dialog.querySelector('[data-p9-sale-docs] [data-document-name="remove-me.txt"]').click();dialog.querySelector('[data-p9-sale-doc-remove]').click();
      dialog.querySelector('[data-p9-sale-tab="map"]').click();dialog.querySelector('[data-p9-sale-map-query]').value='Istanbul';dialog.querySelector('[data-p9-sale-map-search]').click();
      const map={visible:!dialog.querySelector('[data-p9-sale-map]').hidden,external:!dialog.querySelector('[data-p9-sale-map-open]').hidden};
      dialog.querySelector('[data-p9-sale-submit="print"]').click();
      await new Promise(resolve=>setTimeout(resolve,350));
      return{totals,map,planRows:dialog.querySelectorAll('[data-p9-sale-plan] tr').length,documents:Array.from(dialog.querySelectorAll('[data-p9-sale-docs] li'),item=>item.dataset.documentName),closed:!dialog.open,requests:window.__saleRequests.filter(item=>item.url==='/api/desktop/projects/unit-sales'),printCalls:window.__salePrints,restored:!!window.__saleAudit}
    })()`);
    const request = interactions.requests[0]?.payload;
    if (!discardState.prompted || !discardState.kept || !discardState.discarded || !discardState.reopened || !interactions.closed || interactions.planRows !== 1 || interactions.documents.join(",") !== "agreement.pdf" || !request || request.buyer_tc !== "10000000146" || request.documents?.[0] !== "agreement.pdf" || request.payment_plan?.[0]?.amount !== 180000 || interactions.totals.down !== "20000.00" || interactions.totals.remaining !== "180000.00" || !interactions.map.visible || !interactions.map.external || interactions.printCalls !== 1) throw new Error(`Project unit sale interaction mismatch: ${JSON.stringify({discardState,interactions})}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(`${JSON.stringify({ openState, discardState, interactions, screenshot: screenshotPath, exceptions })}\n`);
    await evaluate("window.__saleAudit.originalApiFetch && (apiFetch=window.__saleAudit.originalApiFetch,loadPart9Projects=window.__saleAudit.originalLoad,window.print=window.__saleAudit.originalPrint,window.__saleAudit.button.remove())");
  } finally {
    try { socket?.close(); } catch (_) {}
    browser.kill();
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
