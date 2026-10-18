const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9254);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `job-service-context-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let i=0;i<100;i+=1) {
      try { target=(await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item=>item.type==="page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge CDP target.");
    socket=new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true})});
    let id=0;const pending=new Map();const exceptions=[];
    socket.addEventListener("message",event=>{const message=JSON.parse(event.data);if(message.method==="Runtime.exceptionThrown")exceptions.push(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text);if(!message.id)return;const task=pending.get(message.id);if(!task)return;pending.delete(message.id);message.error?task.reject(new Error(message.error.message)):task.resolve(message.result)});
    const send=(method,params={})=>new Promise((resolve,reject)=>{const requestId=++id;pending.set(requestId,{resolve,reject});socket.send(JSON.stringify({id:requestId,method,params}))});
    const evaluate=async expression=>{const result=await send("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(result.exceptionDetails.text+": "+(result.exceptionDetails.exception?.description||""));return result.result.value};
    await send("Page.enable");await send("Runtime.enable");await send("Emulation.setDeviceMetricsOverride",{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    for(let i=0;i<80;i+=1){if(await evaluate("document.readyState==='complete'&&typeof ayecJobReportRender==='function'&&typeof ayecContextMenuEnabled==='function'"))break;await delay(200)}
    const setup=await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();document.body.classList.remove("auth-active");page="job-reports";document.body.dataset.page="job-reports";const reportRoot=document.createElement("main");reportRoot.innerHTML=genericShell({table:"devices"});document.body.append(reportRoot);db.settings.contextMenu=true;desktopSettings.rc_job_service="1";
      document.querySelector("#jobReportStart").value="2026-06-01";document.querySelector("#jobReportEnd").value="2026-06-30";
      window.__jobMenuCalls=[];window.__jobMenuDetail=(...args)=>window.__jobMenuCalls.push(["detail",args.length]);window.__jobMenuTechnician=(...args)=>window.__jobMenuCalls.push(["technician",args.length]);window.__jobMenuForm=(...args)=>window.__jobMenuCalls.push(["form",args.length]);window.__jobMenuTracking=(...args)=>window.__jobMenuCalls.push(["job-detail",args.length]);
      serviceDetailDialog=window.__jobMenuDetail;technicianDialog=window.__jobMenuTechnician;dashboardServiceEditDialog=window.__jobMenuForm;ayecJobTrackingDetail=window.__jobMenuTracking;findService=()=>[{},{}];
      ayecJobServiceRows=[{id:61,tracking_no:"SRV-61",customer_name:"Fixture",status:"Bekliyor"}];ayecJobLedgerRows=[{id:91,tracking_no:"JOB-91",customer_name:"Fixture",debit:10}];
      const summary=ayecJobSummary([{tracking_no:"PAID-1",transaction_type:"DEBIT",amount:100},{tracking_no:"PAID-1",transaction_type:"CREDIT",amount:100,try_equivalent:100},{tracking_no:"OPEN-1",transaction_type:"DEBIT",amount:80},{tracking_no:"OPEN-1",transaction_type:"CREDIT",amount:30,try_equivalent:20},{tracking_no:"OPEN-2",transaction_type:"DEBIT",amount:10},{tracking_no:"",transaction_type:"CREDIT",amount:9,try_equivalent:9}],[{},{},{}]);
      const service=document.createElement("tr");service.dataset.jobReportKind="service";service.dataset.jobReportId="61";service.innerHTML="<td>SRV-61</td>";document.body.append(service);
      const job=document.createElement("tr");job.dataset.jobReportKind="job";job.dataset.jobReportId="91";job.innerHTML="<td>JOB-91</td>";document.body.append(job);
      return {serviceConnected:service.isConnected,jobConnected:job.isConnected,summary};
    })()`);
    const profitability=await evaluate(`(async()=>{
      apiFetch=async url=>{window.__jobProfitUrl=url;if(url.includes("/monthly")){const months=Array.from({length:12},(_,index)=>({month:String(index+1).padStart(2,"0")+".2026",new_services:index===0?3:0,completed_services:index===0?2:0,paid_jobs:index===0?1:0,collection_total:index===0?125:0}));return {current:months[0],months};}return {period:"2026-06-01 - 2026-06-30",revenue:150,expenses:30,net:120,net_ratio:80,status:"Fixture ledger summary"};};
      ayecJobReportTab="profit";ayecJobReportRender();await new Promise(resolve=>setTimeout(resolve,0));
      const range={url:window.__jobProfitUrl,cells:Array.from(document.querySelectorAll("#jobReportHost tbody td"),cell=>cell.textContent),controlsVisible:!document.querySelector("#jobReportProfitControls").hidden,dateEnabled:document.querySelector("#jobReportDateEnabled").checked};
      document.querySelector("#jobReportDateEnabled").checked=false;document.querySelector("#jobReportDateEnabled").dispatchEvent(new Event("change",{bubbles:true}));
      const period=document.querySelector("#jobReportProfitPeriod");period.value="year";period.dispatchEvent(new Event("change",{bubbles:true}));await new Promise(resolve=>setTimeout(resolve,0));
      const periodMode={url:window.__jobProfitUrl,disabled:period.disabled,dateInputsDisabled:document.querySelector("#jobReportStart").disabled};
      document.querySelector("[data-job-report-monthly]").click();await new Promise(resolve=>setTimeout(resolve,0));
      const dialog=document.querySelector("#appDialog"),monthly={url:window.__jobProfitUrl,open:dialog.open,width:Math.round(dialog.getBoundingClientRect().width),height:Math.round(dialog.getBoundingClientRect().height),rows:document.querySelectorAll(".job-monthly-report-table tbody tr").length,metrics:Array.from(document.querySelectorAll(".job-monthly-report-metrics strong"),node=>node.textContent),cancelHidden:document.querySelector("#dialogCancel").hidden};
      ayecJobReportTab="jobs";ayecJobReportRender();return {range,periodMode,monthly};
    })()`);
    const monthlyShot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});fs.writeFileSync(path.join(outDir,"job-monthly-report-headless.png"),Buffer.from(monthlyShot.data,"base64"));
    await evaluate("document.querySelector('#dialogSubmit').click()");
    const serviceMenu=await evaluate(`(() => {const row=document.querySelector('tr[data-job-report-kind="service"]');const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:300});row.dispatchEvent(event);const menu=document.querySelector(".service-list-context-menu");return {prevented:event.defaultPrevented,actions:Array.from(menu?.querySelectorAll("[data-job-report-context]")||[],button=>button.dataset.jobReportContext),labels:Array.from(menu?.querySelectorAll("[data-job-report-context]")||[],button=>button.textContent.trim()),open:!!menu};})()`);
    const screenshot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});fs.writeFileSync(path.join(outDir,"job-service-context-menu-headless.png"),Buffer.from(screenshot.data,"base64"));
    const result=await evaluate(`(async()=>{
      const invoke=async(action)=>{const button=document.querySelector('.service-list-context-menu [data-job-report-context="'+action+'"]');button?.click();await new Promise(resolve=>setTimeout(resolve,0));};
      await invoke("detail");document.querySelector("tr[data-job-report-kind=service]").dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:300}));await invoke("technician");document.querySelector("tr[data-job-report-kind=service]").dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:300}));await invoke("form");
      document.querySelector("tr[data-job-report-kind=job]").dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:300}));await invoke("detail");
      const calls=window.__jobMenuCalls.slice();document.querySelector(".service-list-context-menu")?.remove();desktopSettings.rc_job_service="0";const disabledEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:300});document.querySelector("tr[data-job-report-kind=service]").dispatchEvent(disabledEvent);
      const disabledClosed=!document.querySelector(".service-list-context-menu");
      return {calls,disabledClosed,disabledDefaultPrevented:disabledEvent.defaultPrevented};
    })()`);
    const expected=["detail","technician","form","job-detail"];
    if(!setup.serviceConnected||!setup.jobConnected||JSON.stringify(setup.summary)!==JSON.stringify({totalJobs:3,openJobs:2,paidJobs:1,totalServices:3,totalRevenue:129})||!profitability.range.url.includes("period=range")||profitability.range.cells[0]!=="2026-06-01 - 2026-06-30"||profitability.range.cells[3]!=="120.00"||!profitability.range.controlsVisible||!profitability.range.dateEnabled||!profitability.periodMode.url.includes("period=year")||profitability.periodMode.disabled||!profitability.periodMode.dateInputsDisabled||!profitability.monthly.url.endsWith("/api/desktop/job-reports/monthly")||!profitability.monthly.open||profitability.monthly.width!==600||profitability.monthly.height!==400||profitability.monthly.rows!==12||JSON.stringify(profitability.monthly.metrics)!==JSON.stringify(["3","2","1","\u20ba125,00"])||!profitability.monthly.cancelHidden||!serviceMenu.open||!serviceMenu.prevented||JSON.stringify(serviceMenu.actions)!==JSON.stringify(["detail","technician","form"])||JSON.stringify(result.calls.map(item=>item[0]))!==JSON.stringify(expected)||!result.disabledClosed||result.disabledDefaultPrevented||exceptions.length)throw new Error(JSON.stringify({setup,profitability,serviceMenu,result,exceptions}));
    console.log(JSON.stringify({setup,profitability,serviceMenu,result,browserExceptions:exceptions.length,headless:true}));
  } finally {if(socket)socket.close();browser.kill()}
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1});



