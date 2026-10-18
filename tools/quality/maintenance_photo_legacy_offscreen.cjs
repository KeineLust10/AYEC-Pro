const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9266);
const baseUrl = process.env.AYEC_AUDIT_URL;
const cookie = process.env.AYEC_MAINTENANCE_SESSION_COOKIE;
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `maintenance-photo-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !cookie) throw new Error("Authenticated maintenance-photo audit configuration is missing.");
  fs.mkdirSync(outDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let i=0;i<100;i+=1) { try { target=(await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item=>item.type==="page"); } catch (_) {} if(target?.webSocketDebuggerUrl)break; await delay(200); }
    if(!target?.webSocketDebuggerUrl)throw new Error("No headless Edge CDP target.");
    socket=new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true});});
    let id=0;const pending=new Map(),exceptions=[];
    socket.addEventListener("message",event=>{const msg=JSON.parse(event.data);if(msg.method==="Runtime.exceptionThrown")exceptions.push(msg.params.exceptionDetails.exception?.description||msg.params.exceptionDetails.text);if(!msg.id)return;const task=pending.get(msg.id);if(!task)return;pending.delete(msg.id);msg.error?task.reject(new Error(msg.error.message)):task.resolve(msg.result);});
    const send=(method,params={})=>new Promise((resolve,reject)=>{const requestId=++id;pending.set(requestId,{resolve,reject});socket.send(JSON.stringify({id:requestId,method,params}));});
    const evaluate=async expression=>{const result=await send("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});if(result.exceptionDetails)throw new Error(result.exceptionDetails.text);return result.result.value;};
    await send("Page.enable");await send("Runtime.enable");await send("Network.enable");
    await send("Network.setCookie",{name:"ayec_session",value:cookie,url:baseUrl});await send("Page.navigate",{url:baseUrl});
    let ready=false;for(let i=0;i<120;i+=1){ready=await evaluate("document.readyState==='complete'&&typeof maintenancePhotoGallery==='function'&&Boolean(currentAuthUser?.id)");if(ready)break;await delay(200);}if(!ready)throw new Error("Maintenance photo page did not initialize: "+JSON.stringify(await evaluate("({state:document.readyState,photoGallery:typeof maintenancePhotoGallery,auth:currentAuthUser||null,scripts:[...document.scripts].map(script=>({src:script.src,loaded:script.readyState||null}))})")));
    const result=await evaluate(`(async()=>{page="vehicle-maintenance";document.body.dataset.page="vehicle-maintenance";await maintenancePhotoGallery({id:9,vehicle_plate:"ABC-123"});for(let i=0;i<80&&!document.querySelector(".maintenance-photo-preview img");i++)await new Promise(resolve=>setTimeout(resolve,100));const image=document.querySelector(".maintenance-photo-preview img");if(image)try{await image.decode()}catch(_){}return{role:currentAuthUser.role,dialogOpen:document.querySelector("#appDialog")?.open===true,source:image?.getAttribute("src")||"",loaded:Boolean(image?.complete&&image.naturalWidth===1),counter:document.querySelector("[data-photo-counter]")?.textContent||""}})()`);
    if(result.role!=="Admin"||!result.dialogOpen||!result.source.includes("/api/desktop/vehicle-maintenance/photo/")||!result.loaded||result.counter!=="1 / 1"||exceptions.length)throw new Error(JSON.stringify({result,exceptions}));
    const shot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});fs.writeFileSync(path.join(outDir,"maintenance-photo-legacy-headless.png"),Buffer.from(shot.data,"base64"));
    console.log(JSON.stringify({result,exceptions:exceptions.length,headless:true}));
  } finally {if(socket)socket.close();browser.kill();try{fs.rmSync(profile,{recursive:true,force:true});}catch(_){} }
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
