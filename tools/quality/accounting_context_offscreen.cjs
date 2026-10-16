const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9255);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `accounting-context-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outDir,{recursive:true});
  const browser=spawn(edgePath,["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check",`--remote-debugging-port=${port}`,`--user-data-dir=${profile}`,"--window-size=1280,900",baseUrl],{stdio:"ignore",windowsHide:true});
  let socket;
  try {
    let target;
    for(let i=0;i<100;i+=1){try{target=(await(await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item=>item.type==="page")}catch(_){}if(target?.webSocketDebuggerUrl)break;await delay(200)}
    if(!target?.webSocketDebuggerUrl)throw new Error("No headless Edge CDP target.");
    socket=new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true})});
    let id=0;const pending=new Map();const exceptions=[];
    socket.addEventListener("message",event=>{const message=JSON.parse(event.data);if(message.method==="Runtime.exceptionThrown")exceptions.push(message.params.exceptionDetails.exception?.description||message.params.exceptionDetails.text);if(!message.id)return;const task=pending.get(message.id);if(!task)return;pending.delete(message.id);message.error?task.reject(new Error(message.error.message)):task.resolve(message.result)});
    const send=(method,params={})=>new Promise((resolve,reject)=>{const requestId=++id;pending.set(requestId,{resolve,reject});socket.send(JSON.stringify({id:requestId,method,params}))});
    const evaluate=async expression=>{const result=await send("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(result.exceptionDetails.text+": "+(result.exceptionDetails.exception?.description||""));return result.result.value};
    await send("Page.enable");await send("Runtime.enable");await send("Emulation.setDeviceMetricsOverride",{width:1280,height:900,deviceScaleFactor:1,mobile:false});
    for(let i=0;i<80;i+=1){if(await evaluate("document.readyState==='complete'&&typeof showContext==='function'&&typeof ayecContextMenuEnabled==='function'"))break;await delay(200)}
    const result=await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();document.body.classList.remove("auth-active");page="accounting";document.body.dataset.page="accounting";db.settings.contextMenu=true;desktopSettings.rc_accounting="1";
      window.__financeContextCalls=[];contextAction=(kind,id,action)=>window.__financeContextCalls.push([kind,id,action]);
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:450,clientY:870});showContext(event,"finance","55");
      const menu=document.querySelector("#contextMenu"),rect=menu.getBoundingClientRect();
      const visible={prevented:event.defaultPrevented,actions:Array.from(menu.querySelectorAll("[data-context-action]"),button=>button.dataset.contextAction),separators:menu.querySelectorAll("hr.context-menu-separator").length,labels:Array.from(menu.querySelectorAll("[data-context-action]"),button=>button.textContent.trim()),bottom:Math.round(rect.bottom),viewport:innerHeight};
      return visible;
    })()`);
    const screenshot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});fs.writeFileSync(path.join(outDir,"accounting-context-menu-headless.png"),Buffer.from(screenshot.data,"base64"));
    const flow=await evaluate(`(() => {
      const actions=["finance-detail","finance-export","finance-pdf","finance-print"];
      for(const action of actions){desktopSettings.rc_accounting="1";showContext(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:450,clientY:400}),"finance","55");document.querySelector('#contextMenu [data-context-action="'+action+'"]').click()}
      desktopSettings.rc_accounting="0";const blocked=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:450,clientY:400});showContext(blocked,"finance","55");
      return {calls:window.__financeContextCalls,disabledOpen:document.querySelector("#contextMenu")?.classList.contains("open")||false,disabledDefaultPrevented:blocked.defaultPrevented};
    })()`);
    const expected=["finance-detail","finance-export","finance-pdf","finance-print"];
    if(!result.prevented||JSON.stringify(result.actions)!==JSON.stringify(expected)||result.separators!==1||result.bottom>result.viewport||JSON.stringify(flow.calls.map(item=>item[2]))!==JSON.stringify(expected)||flow.disabledOpen||flow.disabledDefaultPrevented||exceptions.length)throw new Error(JSON.stringify({result,flow,exceptions}));
    console.log(JSON.stringify({result,flow,browserExceptions:exceptions.length,headless:true}));
  } finally {if(socket)socket.close();browser.kill()}
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1});
