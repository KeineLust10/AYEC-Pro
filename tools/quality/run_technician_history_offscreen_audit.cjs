const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-technician-history-"));
const port = 18600 + process.pid % 400;
const debugPort = 32000 + process.pid % 20000;
const baseUrl = `http://127.0.0.1:${port}/`;
const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const output = path.join(root, "output", "playwright", "technician-history-offscreen-20261018.json");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
    killer.once("error", resolve);
  });
}

(async () => {
  const server = spawn(process.env.PYTHON || "python", [
    path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port),
    "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants"),
  ], { cwd: root, stdio: "ignore", windowsHide: true });
  let browser;
  let socket;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");

    const profile = path.join(tempRoot, "edge-profile");
    browser = spawn(edge, [
      "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
      `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl,
    ], { stdio: "ignore", windowsHide: true });
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge page target.");

    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
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
    let loaded = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      loaded = await evaluate("document.readyState === 'complete' && typeof bindTechnicianHistory === 'function'");
      if (loaded) break;
      await delay(200);
    }
    if (!loaded) throw new Error("Technician history UI did not load.");

    const historyResult = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      const requests=[];
      window.fetch=async input=>{
        const url=String(input);requests.push(url);
        return new Response(JSON.stringify({events:[
          {created_at:'2026-10-18 12:30:00',entry_type:'Part',message:'Part used: Screen x 2 (125.00 TRY)',user:''},
          {created_at:'2026-10-18 12:00:00',entry_type:'Technician',message:'Diagnosis saved',user:'Tech A'}
        ]}),{status:200,headers:{'Content-Type':'application/json'}});
      };
      await bindTechnicianHistory({no:'TECH-HISTORY-AUDIT'});
      const button=document.querySelector('.technician-history-toggle');
      if(!button)throw new Error('Technician history button was not added.');
      button.click();
      await new Promise(resolve=>setTimeout(resolve,100));
      const panel=document.querySelector('.technician-history-panel');
      return {buttonText:button.textContent,visible:!!panel&&!panel.hidden,containsPart:panel?.textContent.includes('Screen x 2')||false,containsLog:panel?.textContent.includes('Diagnosis saved')||false,requests};
    })()`);
    const reportResult = await evaluate(`(async()=>{
      const requests=[];
      window.fetch=async input=>{
        const url=String(input);requests.push(url);
        const payload=url.includes('/test-catalog')
          ? {tests:[{name:'Dynamic profile check',active:true},{name:'Disabled profile check',active:false}]}
          : {tests:[{name:'Dynamic profile check',result:'Ge\\u00e7ti',note:''}]};
        return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}});
      };
      await openServiceReportDialog({name:'Audit Customer'},{no:'TECH-CATALOG-AUDIT',device:'Test device',used_parts:[],labor_cost:0});
      const checks=[...document.querySelectorAll('[data-report-test]')];
      return {names:checks.map(item=>item.dataset.reportTest),selected:checks[0]?.value||'',requests};
    })()`);
    const panelResult = await evaluate(`(async()=>{
      const requests=[];window.activity=()=>{};window.fetch=async(input,init={})=>{
        const url=String(input);requests.push({url,body:init.body||''});
        let payload={events:[{created_at:'2026-10-18 12:00:00',entry_type:'Technician',message:'Panel history event',user:'Tech A'}]};
        if(url.includes('/test-catalog'))payload={tests:[{name:'Dynamic check',active:true},{name:'Disabled check',active:false}]};
        if(url.includes('/checklist')){const value=JSON.parse(init.body||'{}');payload={ok:true,tracking_no:value.tracking_no,checklist_status:(value.selected_labels||[]).join(',')}}
        return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}});
      };
      const body=document.querySelector('#dialogBody');body.innerHTML='<div class="form-grid"><input name="checklist_status"></div>';
      desktopSettings={technician_station_id:'ST-07',technician_station_esd_status:'Inspection recorded',technician_station_equipment:'Actual microscope'};
      const service={no:'TECH-TABS-AUDIT',checklist_status:'Saved check,Inactive saved',technician:'Tech A'};
      const history=await bindTechnicianHistory(service);await bindTechnicianPanelTabs(service,history);
      const tabs=[...body.querySelectorAll('[data-technician-tab]')].map(item=>item.textContent);
      body.querySelector('[data-technician-tab="tests"]').click();
      const testInputs=[...body.querySelectorAll('[data-technician-test]')],initiallyChecked=testInputs[0]?.checked||false;
      testInputs[0].checked=true;testInputs[0].dispatchEvent(new Event('change',{bubbles:true}));await new Promise(resolve=>setTimeout(resolve,100));
      body.querySelector('[data-technician-tab="history"]').click();
      body.querySelector('.technician-history-toggle').click();await new Promise(resolve=>setTimeout(resolve,100));
      const saved=requests.find(item=>item.url.includes('/api/desktop/technician/checklist'));
      body.dataset.technicianPanelStartedAt=String(Date.now());body.querySelector('[data-technician-station-open]').click();let station=document.querySelector('.technician-station-dialog');await new Promise(resolve=>setTimeout(resolve,1100));
      const stationText=station?.textContent||'',firstStationTimer=station?.querySelector('[data-technician-panel-time]')?.textContent||'';station?.close();await new Promise(resolve=>setTimeout(resolve,1100));body.querySelector('[data-technician-station-open]').click();station=document.querySelector('.technician-station-dialog');const stationTimer=station?.querySelector('[data-technician-panel-time]')?.textContent||'';const stationGridValues=[...(station?.querySelectorAll(".technician-station-grid section strong")||[])].map(node=>({text:node.textContent,rect:(()=>{const r=node.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}})(),scrollWidth:node.scrollWidth,clientWidth:node.clientWidth})),stationBody=station?.querySelector(".dialog-body"),stationBodyScroll={scrollHeight:stationBody?.scrollHeight,clientHeight:stationBody?.clientHeight,scrollWidth:stationBody?.scrollWidth,clientWidth:stationBody?.clientWidth,overflowY:getComputedStyle(stationBody).overflowY};
      const bounds=element=>{const rect=element?.getBoundingClientRect();return rect?{x:rect.x,y:rect.y,width:rect.width,height:rect.height}:null};
      return {tabs,testNames:testInputs.map(item=>item.dataset.technicianTest),initiallyChecked,historyVisible:!body.querySelector('[data-technician-pane="history"]').hidden,historyRendered:body.querySelector('.technician-history-panel')?.textContent.includes('Panel history event')||false,savedBody:saved?.body||'',stationText,firstStationTimer,stationTimer,stationBounds:bounds(station),stationGridValues,stationBodyScroll,stationBodyBounds:bounds(station?.querySelector('.dialog-body')),stationFooterBounds:bounds(station?.querySelector('footer')),stationCloseBounds:bounds(station?.querySelector('.technician-station-close')),stationBackdrop:{background:getComputedStyle(station,'::backdrop').backgroundColor,filter:getComputedStyle(station,'::backdrop').backdropFilter},stationFooterStyle:{minHeight:getComputedStyle(station?.querySelector('footer')).minHeight,padding:getComputedStyle(station?.querySelector('footer')).padding,height:getComputedStyle(station?.querySelector('footer')).height,viewport:innerWidth},stationHeaderStyle:{padding:getComputedStyle(station?.querySelector('header')).padding},stationMedia:{viewport:innerWidth,wide:matchMedia('(min-width:651px)').matches,sheets:[...document.styleSheets].map(sheet=>sheet.href),tailRules:(()=>{const sheet=[...document.styleSheets].find(item=>item.href?.includes('/styles.css'));return sheet?[...sheet.cssRules].slice(-3).map(rule=>rule.cssText):[]})()},parentDialogPreserved:document.querySelector('#appDialog')?.open||false,requests};
    })()`);
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const mobileStationResult = await evaluate(`(()=>{
      const body=document.querySelector('#dialogBody');
      body.querySelector('[data-technician-station-open]').click();
      const dialog=document.querySelector('.technician-station-dialog');
      const rect=dialog.getBoundingClientRect();
      return {open:dialog.open,viewport:innerWidth,width:rect.width,left:rect.left,right:rect.right,documentWidth:document.documentElement.scrollWidth,footerHeight:dialog.querySelector('footer').getBoundingClientRect().height,closeVisible:dialog.querySelector('.technician-station-close').getBoundingClientRect().right<=innerWidth};
    })()`);
    await evaluate("document.querySelector('.technician-station-dialog')?.close()");
    await send("Emulation.clearDeviceMetricsOverride");
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const screenshotPath = path.join(root, "output", "playwright", "technician-history-offscreen-20261018", "station-dialog.png");
    fs.mkdirSync(path.dirname(screenshotPath), { recursive: true });
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    await evaluate("document.querySelector('.technician-station-dialog')?.close()");
    const harnessExceptions = exceptions.filter(item => item.includes("showAuth") && item.includes("initializeAuth"));
    const unexpectedExceptions = exceptions.filter(item => !harnessExceptions.includes(item));
    const passed = historyResult?.visible && historyResult?.containsPart && historyResult?.containsLog
      && historyResult?.requests?.some(url => url.includes("/api/desktop/technician/history?tracking_no=TECH-HISTORY-AUDIT"))
      && reportResult?.names?.length === 1 && reportResult?.names[0] === "Dynamic profile check"
      && reportResult?.selected === "Ge\u00e7ti"
      && reportResult?.requests?.some(url => url.includes("/api/desktop/technician/test-catalog?tracking_no=TECH-CATALOG-AUDIT"))
      && panelResult?.tabs?.length === 3 && panelResult?.testNames?.length === 1
      && panelResult?.initiallyChecked === false && panelResult?.historyVisible && panelResult?.historyRendered
      && JSON.parse(panelResult?.savedBody || "{}").selected_labels?.includes("Inactive saved")
      && panelResult?.requests?.some(item => item.url.includes("/api/desktop/technician/checklist"))
      && mobileStationResult?.open && mobileStationResult?.viewport === 390
      && mobileStationResult?.left >= 0 && mobileStationResult?.right <= 390
      && mobileStationResult?.documentWidth <= 390 && mobileStationResult?.closeVisible
      && panelResult?.stationText?.includes("ST-07") && panelResult?.stationText?.includes("Inspection recorded")
      && panelResult?.stationText?.includes("Actual microscope") && panelResult?.stationTimer >= "00:00:02" && panelResult?.stationBodyScroll?.scrollHeight <= panelResult?.stationBodyScroll?.clientHeight + 1 && panelResult?.stationBodyScroll?.overflowY === "hidden" && panelResult?.stationGridValues?.every(item=>item.rect.height<20 && item.scrollWidth<=item.clientWidth)
      && panelResult?.stationBackdrop?.background === "rgb(2, 6, 23)" && panelResult?.stationBackdrop?.filter === "none"
      && panelResult?.parentDialogPreserved
      && unexpectedExceptions.length === 0;
    const artifact = { passed: !!passed, historyResult, reportResult, panelResult, mobileStationResult, screenshotPath, exceptions, harnessExceptions, unexpectedExceptions, route: baseUrl, browser: "Edge headless" };
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify(artifact, null, 2) + "\n", "utf8");
    if (!passed) throw new Error(`Technician history browser audit failed: ${JSON.stringify(artifact)}`);
    process.stdout.write(JSON.stringify(artifact) + "\n");
  } finally {
    try { socket?.close(); } catch (_) {}
    await stopProcess(browser);
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
