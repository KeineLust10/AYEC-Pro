const { spawn, spawnSync } = require("node:child_process");
const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 31000 + (process.pid % 20000);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = require("node:path").resolve("output/playwright");
const profile = require("node:path").join(outputDir, `service-list-date-profile-${process.pid}`);
async function run() {
  require("node:fs").mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); if (target) break; } catch (_) {}
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless page target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0; const pending = new Map(), exceptions = [];
    socket.addEventListener("message", event => { const message = JSON.parse(event.data); if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text); if (!message.id) return; const item = pending.get(message.id); if (!item) return; pending.delete(message.id); message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result); });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => { const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text); return result.result?.value; };
    await send("Page.enable"); await send("Runtime.enable");
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) { ready = await evaluate("document.readyState === 'complete' && typeof render === 'function'"); if (ready) break; await new Promise(resolve => setTimeout(resolve, 200)); }
    if (!ready) throw new Error("Web app did not finish loading.");
    const result = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      const now=new Date(),date=value=>{const d=new Date(value);return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
      const today=date(now),prior=new Date(now),recent=new Date(now);prior.setDate(prior.getDate()-1);recent.setDate(recent.getDate()-10);
      const statusClassifications={ready:ayecStatusKind({status:'Teslime Hazir'}),delivered:ayecStatusKind({status:'Teslim Edildi'}),legacyCompleted:ayecStatusKind({status:'Tamamlandi'}),readyAlias:ayecStatusKind({status:'Hazir'}),canceled:ayecStatusKind({status:'\u0130ptal'}),repairing:ayecStatusKind({status:'Tamirde'}),parts:ayecStatusKind({status:'Par\u00e7a Bekliyor'})};
      if(JSON.stringify(statusClassifications)!==JSON.stringify({ready:'open',delivered:'done',legacyCompleted:'open',readyAlias:'open',canceled:'open',repairing:'open',parts:'parts'}))throw new Error('Service-status classification differs from desktop filters: '+JSON.stringify(statusClassifications));
      const metricRows=[{entry_date:today,delivered_at:today,status:'Teslim Edildi'},{entry_date:today,status:'Tamirde'},{entry_date:date(prior),status:'Teslime Hazir'},{entry_date:today,status:'Par\u00e7a Bekliyor',urgency:'ACIL'},{entry_date:today,status:'\u0130ptal',urgency:'ACIL'},{entry_date:today,status:'Bekliyor',is_deleted:1},{entry_date:today,status:'Bekliyor',is_archived:1},{entry_date:date(recent),delivered_at:today,status:'Teslim Edildi'}];
      const metricResult=ayecStatusMetrics(metricRows,{workshop_capacity:'2'},today);
      const metricExpected={volume:5,deliveredToday:2,activeToday:2,occupying:3,critical:1,parts:1,durationCount:2,averageDuration:5,capacity:2,total:6};
      if(JSON.stringify(metricResult)!==JSON.stringify(metricExpected))throw new Error('Service-status metrics differ from desktop calculations: '+JSON.stringify(metricResult));
      const initialDateFilter=ayecServiceListState.date;
      const recentRows=Array.from({length:15},(_,index)=>({tracking_no:index?'SRV-RECENT-'+index:'SRV-RECENT',customer_name:'Recent Entry',device_brand:'Fixture',device_model:'Recent'+index,entry_date:date(recent),status:index===3?'Kargoya Verildi':index===4?'Tamirde':'Bekliyor',delivery_type:index===4?'D\u0131\u015f Servis':'',service_source:index===2?'Kargo transferi':'',is_invoiced:index===1?1:0,invoice_no:index===0?'INV-DESYNC':'',price:15}));
      db.customers=[];db.serviceDevices=[
        {tracking_no:'SRV-OLD-APPT',customer_name:'Old Appointment',device_brand:'Fixture',device_model:'Old',entry_date:'2020-01-01',appointment_date:today,status:'Bekliyor',price:10},
        ...recentRows,
        {tracking_no:'SRV-TODAY',customer_name:'Today Entry',device_brand:'Fixture',device_model:'Today',phone:'needlephone',serial_no:'needleserial',entry_date:today+' 09:00',appointment_date:date(prior),status:'NeedleStatus',price:20}
      ];
      page='service-list';render();
      const originalSector=currentSector,originalOpenDialog=window.openDialog;let capturedStatusDialog;
      window.openDialog=(...args)=>{capturedStatusDialog=args};
      currentSector='otomotiv';openServiceStatusDialog({}, {no:'AUTO-STATUS',id:1,status:'Tamirde'});
      const statusOptions=document.createElement('select');statusOptions.innerHTML=capturedStatusDialog?.[2]||'';
      const automotiveStatuses=[...statusOptions.options].map(option=>option.textContent);
      if(!automotiveStatuses.includes('Serviste')||automotiveStatuses.includes('Tamirde'))throw new Error('Automotive status dialog options do not match desktop.');
      const originalApiFetch=window.apiFetch,automotiveService={no:'AUTO-STATUS',id:91,status:'Tamirde'};let statusRequest;
      openServiceStatusDialog({},automotiveService);
      window.apiFetch=async(path,options)=>{statusRequest={path,body:JSON.parse(options.body)}};
      await capturedStatusDialog[3]({get:()=> 'Serviste'});
      if(automotiveService.status!=='Serviste'||statusRequest?.path!=='/api/desktop/table/devices'||statusRequest.body.status!=='Serviste'||statusRequest.body.id!==91)throw new Error('Automotive status update did not submit the selected value.');
      window.apiFetch=originalApiFetch;
      currentSector='teknik';openServiceStatusDialog({}, {no:'TECH-STATUS',id:2,status:'Tamirde'});
      statusOptions.innerHTML=capturedStatusDialog?.[2]||'';
      const technicalStatuses=[...statusOptions.options].map(option=>option.textContent);
      if(!technicalStatuses.includes('Tamirde')||technicalStatuses.includes('Serviste'))throw new Error('Technical status dialog options do not match desktop.');
      currentSector='otomotiv';render();
      const automotiveFilter=document.querySelector('#serviceListStatus option[value="repair"]')?.textContent;
      currentSector='teknik';render();
      const technicalFilter=document.querySelector('#serviceListStatus option[value="repair"]')?.textContent;
      if(automotiveFilter!=='Serviste'||technicalFilter!=='Tamirde')throw new Error('Service status filter labels do not match sector.');
      currentSector=originalSector;window.openDialog=originalOpenDialog;render();
      const serviceRows=[...document.querySelectorAll('.service-list-table tbody tr[data-kind=service]')];
      serviceRows[1]?.dispatchEvent(new MouseEvent('click',{bubbles:true}));
      const clickedRowSelection={currentId:ayecServiceListState.currentId,rowId:serviceRows[1]?.dataset.id,current:serviceRows[1]?.classList.contains('is-current'),checkboxSelection:serviceRows[1]?.classList.contains('is-selected'),background:getComputedStyle(serviceRows[1].cells[0]).backgroundColor};
      const rowContextEvent=new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:500,clientY:300});
      serviceRows[0]?.dispatchEvent(rowContextEvent);
      const contextRoot=document.querySelector('.service-list-context-menu:not(.service-list-context-submenu-panel)');
      const mouseContext={prevented:rowContextEvent.defaultPrevented,currentId:ayecServiceListState.currentId,rowCurrent:serviceRows[0]?.classList.contains('is-current'),firstAction:contextRoot?.querySelector('[data-service-context]')?.dataset.serviceContext,hasPrintMenu:!!contextRoot?.querySelector('[data-service-submenu-trigger=print]')};
      document.querySelectorAll('.service-list-context-menu').forEach(menu=>menu.remove());
      const keyboardRow=document.querySelector('.service-list-table tbody tr[data-kind=service]');
      const keyboardControl=keyboardRow?.querySelector('button[data-action=service-detail]');
      const keyboardRowTabIndex=keyboardControl?.tabIndex;
      keyboardControl?.focus();
      const keyboardEvent=new KeyboardEvent('keydown',{key:'F10',shiftKey:true,bubbles:true,cancelable:true});
      keyboardControl?.dispatchEvent(keyboardEvent);
      const keyboardContext={tabIndex:keyboardRowTabIndex,prevented:keyboardEvent.defaultPrevented,opened:!!document.querySelector('.service-list-context-menu'),focused:!!document.activeElement?.matches('.service-list-context-menu button[role=menuitem]')};
      const initialCount=document.querySelectorAll('.service-list-table tbody tr[data-kind=service]').length;
      const pageSize=document.querySelector('#serviceListPageSize'),defaultPageSize=ayecServiceListState.pageSize,pageSizeOptions=[...pageSize.options].map(option=>Number(option.value));
      pageSize.value='8';pageSize.dispatchEvent(new Event('change',{bubbles:true}));
      const pageEight=document.querySelectorAll('.service-list-table tbody tr[data-kind=service]').length;
      document.querySelector('#serviceListPageSize').value='100';document.querySelector('#serviceListPageSize').dispatchEvent(new Event('change',{bubbles:true}));
      const pageHundred=document.querySelectorAll('.service-list-table tbody tr[data-kind=service]').length;
      document.querySelector('[data-service-tab="cargo"]')?.click();
      const cargoRows=[...document.querySelectorAll('.service-list-table tbody tr[data-kind=service]')].map(row=>row.dataset.id);
      document.querySelector('[data-service-tab="invoiced"]')?.click();
      const invoicedRows=[...document.querySelectorAll('.service-list-table tbody tr[data-kind=service]')].map(row=>row.dataset.id);
      document.querySelector('[data-service-tab="uninvoiced"]')?.click();
      const uninvoicedCount=document.querySelectorAll('.service-list-table tbody tr[data-kind=service]').length;
      document.querySelector('[data-service-tab="today"]')?.click();
      const todayRows=[...document.querySelectorAll('.service-list-table tbody tr[data-kind=service]')].map(row=>row.dataset.id);
      const applySearch=value=>{const input=document.querySelector('#serviceListSearch');input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));return [...document.querySelectorAll('.service-list-table tbody tr[data-kind=service]')].map(row=>row.dataset.id)};
      const excludedSearches={phone:applySearch('needlephone'),serial:applySearch('needleserial'),status:applySearch('NeedleStatus')};
      const trackingSearch=applySearch('SRV-TODAY'),deviceSearch=applySearch('Today');
      const originalBulkPrint=window.openServiceBulkPrint,detailedPrintCalls=[];
      window.openServiceBulkPrint=records=>detailedPrintCalls.push(...records);
      document.querySelector('.service-list-table tbody tr[data-id="SRV-TODAY"]')?.click();
      document.querySelector('[data-service-command="print"]')?.click();
      window.openServiceBulkPrint=originalBulkPrint;
      const directDetailedPrint={currentId:ayecServiceListState.currentId,count:detailedPrintCalls.length,tracking:detailedPrintCalls[0]?.service?.tracking_no||detailedPrintCalls[0]?.service?.no};
      ayecServiceListState.currentId=null;document.querySelector('[data-service-command="print"]')?.click();
      directDetailedPrint.noSelectionWarning=document.querySelector('#toastRoot .toast.warning div')?.textContent||"";
      Object.assign(ayecServiceListState,{tab:'all',query:'',status:'all',date:'all',priority:'all',page:1});render();
      const originalFetch=window.fetch,originalDownload=window.download,exportRequests=[],csvDownloads=[];
      window.fetch=async(url,options)=>{exportRequests.push({url,body:JSON.parse(options.body),headers:options.headers});return {ok:true,blob:async()=>new Blob(['fixture'])}};
      window.download=(name,text,type)=>csvDownloads.push({name,text,type});
      const submitExport=async format=>{openServiceListExportDialog();const select=document.querySelector('#serviceListExportFormat');select.value=format;document.querySelector('#dialogForm').dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,30));};
      ayecServiceListState.selected=new Set(['SRV-OLD-APPT','SRV-RECENT-1']);
      document.querySelector('[data-service-command="bulk-toggle"]')?.click();
      document.querySelector('[data-service-command="bulk-export"]')?.click();
      const selectedExportTitle=document.querySelector('#dialogTitle')?.textContent;
      const selectedFormat=document.querySelector('#serviceListExportFormat');if(selectedFormat)selectedFormat.value='csv';
      document.querySelector('#dialogForm')?.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,30));
      const selectedCsv={name:csvDownloads[0]?.name,rowCount:(csvDownloads[0]?.text.split(String.fromCharCode(10)).length||0)-1};
      ayecServiceListState.selected.clear();
      await submitExport('xlsx');await submitExport('pdf');await submitExport('csv');
      window.fetch=originalFetch;window.download=originalDownload;
      const serviceExport={selectedExportTitle,selectedCsv,requestCount:exportRequests.length,paths:exportRequests.map(item=>item.url),first:exportRequests[0]?.body.records[0],recordCount:exportRequests[0]?.body.records.length,csvName:csvDownloads[1]?.name,csvHeader:csvDownloads[1]?.text.split(String.fromCharCode(10))[0].replace(String.fromCharCode(65279),"")};
      return {defaultDate:initialDateFilter,defaultPageSize,pageSizeOptions,clickedRowSelection,mouseContext,keyboardContext,initialCount,pageEight,pageHundred,cargoRows,invoicedRows,uninvoicedCount,todayRows,todayDate:today,excludedSearches,trackingSearch,deviceSearch,directDetailedPrint,serviceExport};
    })()`);
    if (result.defaultDate !== "last_30" || result.clickedRowSelection.currentId !== result.clickedRowSelection.rowId || !result.clickedRowSelection.current || result.clickedRowSelection.checkboxSelection || result.clickedRowSelection.background !== "rgb(30, 48, 77)" || !result.mouseContext.prevented || result.mouseContext.firstAction !== "technician" || !result.mouseContext.hasPrintMenu || !result.mouseContext.rowCurrent || result.mouseContext.currentId !== "SRV-RECENT" || result.keyboardContext.tabIndex !== 0 || !result.keyboardContext.prevented || !result.keyboardContext.opened || !result.keyboardContext.focused || result.defaultPageSize !== 15 || JSON.stringify(result.pageSizeOptions) !== JSON.stringify([8, 15, 25, 50, 100]) || result.initialCount !== 15 || result.pageEight !== 8 || result.pageHundred !== 16 || JSON.stringify(result.cargoRows) !== JSON.stringify(["SRV-RECENT-2", "SRV-RECENT-3"]) || JSON.stringify(result.invoicedRows) !== JSON.stringify(["SRV-RECENT-1"]) || result.uninvoicedCount !== 15 || JSON.stringify(result.todayRows) !== JSON.stringify(["SRV-TODAY"]) || Object.values(result.excludedSearches).some(rows => rows.length !== 0) || JSON.stringify(result.trackingSearch) !== JSON.stringify(["SRV-TODAY"]) || JSON.stringify(result.deviceSearch) !== JSON.stringify(["SRV-TODAY"]) || result.directDetailedPrint.currentId !== "SRV-TODAY" || result.directDetailedPrint.count !== 1 || result.directDetailedPrint.tracking !== "SRV-TODAY" || !result.directDetailedPrint.noSelectionWarning.includes("fi\u015fini yazd\u0131rmak") || result.serviceExport.selectedExportTitle !== "Se\u00e7ili Servis Kay\u0131tlar\u0131n\u0131 D\u0131\u015fa Aktar" || result.serviceExport.selectedCsv.rowCount !== 2 || result.serviceExport.requestCount !== 2 || JSON.stringify(result.serviceExport.paths) !== JSON.stringify(["/api/desktop/service-list/export/xlsx", "/api/desktop/service-list/export/pdf"]) || result.serviceExport.recordCount !== 17 || result.serviceExport.first.tracking_no !== "SRV-OLD-APPT" || result.serviceExport.csvName !== "servis_listesi_" + new Date().toISOString().slice(0, 10).replaceAll("-", "") + ".csv" || !result.serviceExport.csvHeader.startsWith("Takip No;M\u00fc\u015fteri;\u015eirket;Cihaz T\u00fcr\u00fc;Marka;Model;Giri\u015f Tarihi;\u00c7\u0131k\u0131\u015f Tarihi") || exceptions.length) throw new Error("Service-list parity failed: " + JSON.stringify({ result, exceptions }));
    const shot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    require("node:fs").writeFileSync(require("node:path").join(outputDir, "service-list-today-filter-headless.png"), Buffer.from(shot.data, "base64"));
    const statusMetricsUi = await evaluate(`(async()=>{
      const day=(offset)=>{const date=new Date();date.setDate(date.getDate()+offset);return [date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('-')};
      const rows=[{id:1,entry_date:day(0),delivered_at:day(0),status:'Teslim Edildi'},{id:2,entry_date:day(0),status:'Tamirde'},{id:3,entry_date:day(-1),status:'Teslime Hazir'},{id:4,entry_date:day(0),status:'Par\u00e7a Bekliyor',urgency:'ACIL'},{id:5,entry_date:day(0),status:'\u0130ptal',urgency:'ACIL'},{id:6,entry_date:day(0),status:'Bekliyor',is_deleted:1},{id:7,entry_date:day(0),status:'Bekliyor',is_archived:1},{id:8,entry_date:day(-10),delivered_at:day(0),status:'Teslim Edildi'}];
      const originalApiFetch=apiFetch,originalSettings=desktopSettings,originalDevices=db.devices,originalPage=page;
      apiFetch=async url=>String(url).includes('/api/desktop/table/devices')?{rows,count:rows.length,columns:[]}:({rows:[],count:0,columns:[]});
      desktopSettings={...desktopSettings,workshop_capacity:'2'};db.devices=rows;page='service-status';render();await loadGenericModule(genericModules['service-status']);
      const values={volume:$('#statusWallTotal')?.textContent,deliveredToday:$('#statusWallClosed')?.textContent,activeToday:$('#statusWallActive')?.textContent,occupancy:$('#statusWallOccupancy')?.textContent,capacity:$('#statusWallCapacity')?.textContent,critical:$('#statusWallCritical')?.textContent,criticalDetail:$('#statusWallParts')?.textContent,duration:$('#statusWallDuration')?.textContent,durationCount:$('#statusWallDurationCount')?.textContent,flowNote:$('#statusWallFlowNote')?.textContent,flowChart:Boolean($('#statusWallFlowChart svg')),flowBars:$('#statusWallFlowChart rect')?.length||0};
      apiFetch=originalApiFetch;desktopSettings=originalSettings;db.devices=originalDevices;page=originalPage;return values;
    })()`);
    const expectedStatusMetricsUi={volume:"5 Cihaz",deliveredToday:"2 Teslim",activeToday:"2 Aktif",occupancy:"%150",capacity:"3 / 2.0 Cihaz",critical:"1 Cihaz Bekliyor",criticalDetail:"1 Kritik Kayıt",duration:"5.0 Gün",durationCount:"2 Kapanan Servis",flowNote:"Saat bilgili kabul kayd\u0131 yok | 4 kay\u0131tta saat yok",flowChart:true,flowBars:0};
    if(JSON.stringify(statusMetricsUi)!==JSON.stringify(expectedStatusMetricsUi))throw new Error("Service-status metric UI differs from desktop calculations: "+JSON.stringify(statusMetricsUi));
    await send("Emulation.setDeviceMetricsOverride", { width: 1362, height: 1119, deviceScaleFactor: 1, mobile: false });
    const statusPageGeometry=await evaluate(`(async()=>{
      document.querySelector("#contextMenu")?.remove();document.querySelectorAll(".service-list-context-menu,.service-list-context-submenu-panel,.toast").forEach(node=>node.remove());document.querySelector("#toastRoot")?.replaceChildren();
      const today=new Date(),todayKey=[today.getFullYear(),String(today.getMonth()+1).padStart(2,'0'),String(today.getDate()).padStart(2,'0')].join('-');
      const statuses=['Teslim Edildi','Teslime Hazir','Test / Onay','Tamirde','Bekliyor','Teslim Edildi','Teslim Edildi','Teslim Edildi','Teslim Edildi','Teslim Edildi','Teslim Edildi','Par\u00e7a Bekliyor','Tamirde','Bekliyor','Tamirde'];
      const names=['Burak Sahin','Derya Aydin','Murat Arslan','Elif Yilmaz','Can Yilmaz','Kaan Yilmaz','Selin Yilmaz'];
      const rows=statuses.map((status,index)=>({id:1500-index,tracking_no:'DEMO-SRV-'+String(15-index).padStart(4,'0'),customer_name:names[index%names.length],device_brand:'AYEC Test',device_model:'Cihaz '+(15-index),serial_no:'SER-'+(15-index),status,entry_date:'2026-09-21',delivered_at:'',exit_date:'',urgency:'NORMAL',is_deleted:0,is_archived:0}));
      rows[11].urgency='PARCA';
      const old={apiFetch,desktopSettings,desktopPersonnel,devices:db.devices,page};
      apiFetch=async url=>String(url).includes('/api/desktop/table/devices')?{rows,count:rows.length,columns:[]}:(String(url).includes('/appointments?')?{rows:[],count:0}:String(url).includes('/parts?')?{rows:[],count:0}:String(url).includes('/personnel?')?{rows:[{id:1,name:'Burak Sahin',role:'Stajyer Teknisyen',status:'Durum bildirilmemis',is_active:1},{id:2,name:'Eren Uysal',role:'Saha Muhendisi',status:'Durum bildirilmemis',is_active:1},{id:3,name:'Selim Celik',role:'Kidemli Teknisyen',status:'Durum bildirilmemis',is_active:1}],count:3}:{rows:[],count:0,columns:[]});
      desktopSettings={...desktopSettings,workshop_capacity:''};desktopPersonnel=[{id:1,name:'Burak Sahin',role:'Stajyer Teknisyen',status:''},{id:2,name:'Eren Uysal',role:'Saha Muhendisi',status:''},{id:3,name:'Selim Celik',role:'Kidemli Teknisyen',status:''}];db.devices=rows;page='service-status';render();await loadGenericModule(genericModules['service-status']);
      const rect=selector=>{const e=document.querySelector(selector),r=e?.getBoundingClientRect();return r?{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)}:null};
      return{layoutDisplay:getComputedStyle(document.querySelector('.status-wall-layout')).display,layoutColumns:getComputedStyle(document.querySelector('.status-wall-layout')).gridTemplateColumns,mainDisplay:getComputedStyle(document.querySelector('.status-wall-main')).display,content:rect('#content'),header:rect('#content .page-head'),metrics:rect('.status-wall-metrics'),layout:rect('.status-wall-layout'),list:rect('.status-wall-list'),side:rect('.status-wall-side'),flow:rect('.status-wall-flow'),flowNote:$('#statusWallFlowNote')?.textContent,statusRows:document.querySelectorAll('#statusWallHost tbody tr').length,metricValues:['#statusWallTotal','#statusWallClosed','#statusWallActive','#statusWallOccupancy','#statusWallCapacity','#statusWallCritical','#statusWallParts','#statusWallDuration','#statusWallDurationCount'].map(selector=>document.querySelector(selector)?.textContent)};
    })()`);
    if(statusPageGeometry.statusRows!==7||JSON.stringify(statusPageGeometry.metricValues)!==JSON.stringify(['0 Cihaz','0 Teslim','0 Aktif','-','8 Cihaz / Limit yok','1 Cihaz Bekliyor','1 Kritik Kayıt','-','0 Kapanan Servis']))throw new Error('Service-status reference fixture mismatch: '+JSON.stringify(statusPageGeometry));
    const statusShot=await send("Page.captureScreenshot",{format:"png",fromSurface:true});
    require("node:fs").writeFileSync(require("node:path").join(outputDir,"service-status-native-paired-web-source.png"),Buffer.from(statusShot.data,"base64"));
    process.stdout.write(JSON.stringify({ ...result, statusMetricsUi, statusPageGeometry, browserExceptions: exceptions.length, screenshot: "service-list-today-filter-headless.png", statusScreenshot:"service-status-native-paired-web-source.png" }) + "\n");
    await send("Browser.close");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) socket.close();
    if (process.platform === "win32" && browser.pid) spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    else browser.kill();
    try { require("node:fs").rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}
run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });





