const {spawn,spawnSync}=require("node:child_process");
const fs=require("node:fs");
const path=require("node:path");
const edgePath=process.env.EDGE_EXECUTABLE||"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl=process.env.AYEC_AUDIT_URL||"http://127.0.0.1:8851/";
const outputPath=path.resolve("output/playwright/location-picker-manifest-headless.png");
const cdpPort=Number(process.env.AYEC_AUDIT_CDP_PORT||18991);
const profile=path.join(path.dirname(outputPath),"location-picker-profile-"+process.pid);
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function run(){
 fs.mkdirSync(path.dirname(outputPath),{recursive:true});
 const browser=spawn(edgePath,["--headless=new","--disable-gpu","--no-first-run","--no-default-browser-check","--remote-debugging-port="+cdpPort,"--user-data-dir="+profile,"--window-size=1280,900",baseUrl],{stdio:"ignore",windowsHide:true});
 let socket;
 const exceptions=[];
 try{
  let target;
  for(let i=0;i<100;i++){try{target=(await(await fetch("http://127.0.0.1:"+cdpPort+"/json")).json()).find(x=>x.type==="page")}catch{}if(target?.webSocketDebuggerUrl)break;await delay(150)}
  if(!target?.webSocketDebuggerUrl)throw Error("No hidden browser target.");
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.addEventListener("open",resolve,{once:true});socket.addEventListener("error",reject,{once:true})});
  let id=0;const pending=new Map();
  socket.addEventListener("message",event=>{const m=JSON.parse(event.data);if(m.method==="Runtime.exceptionThrown")exceptions.push(m.params.exceptionDetails?.exception?.description||m.params.exceptionDetails?.text||"Unknown exception");if(!m.id)return;const p=pending.get(m.id);if(!p)return;pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result)});
  const send=(method,params={})=>new Promise((resolve,reject)=>{const i=++id;pending.set(i,{resolve,reject});socket.send(JSON.stringify({id:i,method:method,params:params}))});
  const evaluate=async expression=>{const r=await send("Runtime.evaluate",{expression:expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result?.value};
  await send("Page.enable");await send("Runtime.enable");await send("Emulation.setDeviceMetricsOverride",{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  let ready=false;for(let i=0;i<100;i++){ready=await evaluate("document.readyState==='complete'&&typeof openManifestDialog==='function'");if(ready)break;await delay(200)}
  if(!ready)throw Error("Location picker scripts were not ready.");
  const audit=await evaluate("(async()=>{document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');desktopSettings.installation_lat='40.104412';desktopSettings.installation_lng='27.656398';desktopSettings.installation_address='Fixture Address';currentAuthUser={username:'fixture-user'};apiFetch=async(path)=>path.endsWith('/geocode')?{results:[{lat:'40.2',lon:'27.8',display_name:'Street, District, Province, Turkey'}]}:{display_name:'Fixture Reverse Address'};const writes=[];desktopWrite=async(scope,item)=>{writes.push({scope,key:item.key,value:item.value});return {ok:true}};openManifestDialog({key:'location_picker_dialog'});await new Promise(r=>setTimeout(r,100));const host=document.querySelector('[data-location-picker]'),dialog=document.querySelector('#appDialog'),frame=host?.querySelector('[data-location-map]');const initial={opened:!!dialog?.open,title:document.querySelector('#dialogTitle')?.textContent||'',search:!!host?.querySelector('[data-location-search]'),map:!!frame&&frame.src.includes('field-vector-map-dist'),confirm:document.querySelector('#dialogSubmit')?.textContent||'',size:dialog?.getBoundingClientRect().width||0};const input=host?.querySelector('[data-location-query]');input.value='Fixture';host.querySelector('[data-location-search]').click();await new Promise(r=>setTimeout(r,50));const option=host.querySelector('[data-location-result]');if(option)option.click();await new Promise(r=>setTimeout(r,50));const selected={coordinates:host.querySelector('[data-location-coordinates]')?.textContent||'',status:host.querySelector('[data-location-status]')?.textContent||''};document.querySelector('#dialogSubmit').click();await new Promise(r=>setTimeout(r,100));return{initial:initial,selected:selected,writes:writes,closed:!dialog.open}})()");
  if(!audit.initial.opened||!audit.initial.search||!audit.initial.map||audit.initial.confirm!=="Konumu Onayla"||!audit.selected.coordinates.includes("40.20000")||audit.writes.length!==11||!audit.writes.some(x=>x.key==="map_default_lat"&&x.value==="40.2")||!audit.writes.some(x=>x.key==="map_default_lat_user_fixture-user"&&x.value==="40.2")||!audit.writes.some(x=>x.key==="map_default_city_user_fixture-user"&&x.value==="District")||!audit.writes.some(x=>x.key==="map_default_district_user_fixture-user"&&x.value==="Street")||!audit.closed||exceptions.length)throw Error("Location picker audit failed: "+JSON.stringify({audit:audit,exceptions:exceptions}));
  const shot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});fs.writeFileSync(outputPath,Buffer.from(shot.data,"base64"));
  process.stdout.write(JSON.stringify({audit:audit,exceptions:exceptions,screenshot:outputPath,headless:true})+"\n");
 }finally{try{socket?.close()}catch{}try{spawnSync("taskkill.exe",["/PID",String(browser.pid),"/T","/F"],{stdio:"ignore"});const safeProfile=profile.replace(/'/g,"''");const cleanup="$roots=Get-CimInstance Win32_Process -Filter \"Name = 'msedge.exe'\" | Where-Object { $_.CommandLine -like '*"+safeProfile+"*' -and $_.CommandLine -match '--remote-debugging-port="+cdpPort+"' -and $_.CommandLine -notmatch '--type=' }; foreach ($root in $roots) { taskkill.exe /PID $root.ProcessId /T /F | Out-Null }";spawnSync("powershell.exe",["-NoProfile","-Command",cleanup],{stdio:"ignore"})}catch{browser.kill()}}
}
run().catch(error=>{process.stderr.write(String(error.stack||error)+"\n");process.exitCode=1});
