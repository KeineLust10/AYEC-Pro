const fs = require("node:fs");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const { pathToFileURL } = require("node:url");

const root = path.resolve(__dirname, "../..");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 41000 + (process.pid % 10000);
const indexPath = path.join(root, "Web_Arayuzu", "web", "index.html");
const profileRoot = path.resolve(root, "output", "playwright");
const profile = path.join(profileRoot, `service-confirmations-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!fs.existsSync(edgePath)) throw new Error("Microsoft Edge was not found.");
  if (!profile.startsWith(profileRoot + path.sep)) throw new Error("The browser profile path is outside the audit directory.");
  fs.mkdirSync(profileRoot, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", pathToFileURL(indexPath).href,
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a CDP page target.");
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
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof db === 'object' && typeof openDialog === 'function' && typeof deleteServiceFromWeb === 'function' && typeof openServicePhotosDialog === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("The web shell and service workflows did not become ready.");
    const result = await evaluate(`(async() => {
      const customer={id:851,name:"Fixture Customer",phone:"5550000000",services:[{id:852,no:"TS-852",device:"Laptop",status:"Bekliyor",note:"Fixture"}]};
      const service=customer.services[0];
      db.customers=[customer];
      window.__confirmationWrites=[];
      window.__photoRows=[{id:853,url:"/fixture-photo.png",photo_label:"Entry"}];
      window.__originalApiFetch=apiFetch;
      window.__originalHydrateDesktop=hydrateDesktop;
      window.__originalRender=render;
      hydrateDesktop=async()=>({});
      render=()=>{};
      apiFetch=async(url,options={})=>{
        const entry={url:String(url),payload:options.body?JSON.parse(options.body):null};
        window.__confirmationWrites.push(entry);
        if(entry.url.includes("external-tracking/photos")&&!entry.payload)return {rows:window.__photoRows};
        if(entry.url.includes("external-tracking/photos")&&entry.payload?._action==="delete"){window.__photoRows=[];return {ok:true};}
        return {ok:true};
      };
      window.__nativeConfirmCount=0;
      window.confirm=()=>{window.__nativeConfirmCount+=1;return true};
      deleteServiceFromWeb(service.no);
      const serviceDeleteDialog={open:document.querySelector("#appDialog")?.open===true,title:document.querySelector("#dialogTitle")?.textContent||"",body:document.querySelector("#dialogBody")?.innerText||"",submit:document.querySelector("#dialogSubmit")?.textContent||"",danger:document.querySelector("#dialogSubmit")?.classList.contains("danger")===true};
      document.querySelector("#dialogCancel")?.click();
      const serviceDeleteCancelled=document.querySelector("#appDialog")?.open!==true&&window.__confirmationWrites.length===0&&customer.services.length===1;
      deleteServiceFromWeb(service.no);
      document.querySelector("#dialogSubmit")?.click();
      for(let i=0;i<30&&document.querySelector("#appDialog")?.open;i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const serviceDeleteConfirmed=window.__confirmationWrites.some(item=>item.url==="/api/desktop/table/devices"&&item.payload?._action==="delete")&&customer.services.length===0;
      customer.services=[service];
      quickCloseServiceFromWeb(service.no);
      const quickCloseDialog={open:document.querySelector("#appDialog")?.open===true,title:document.querySelector("#dialogTitle")?.textContent||"",body:document.querySelector("#dialogBody")?.innerText||""};
      document.querySelector("#dialogCancel")?.click();
      await openServicePhotosDialog(customer,service);
      document.querySelector('[data-service-photo-delete="853"]')?.click();
      const photoDeleteDialog={open:document.querySelector("#appDialog")?.open===true,title:document.querySelector("#dialogTitle")?.textContent||"",cancel:document.querySelector("#dialogCancel")?.textContent||"",danger:document.querySelector("#dialogSubmit")?.classList.contains("danger")===true};
      document.querySelector("#dialogCancel")?.click();
      const photoDeleteCancelled=!window.__confirmationWrites.some(item=>item.url==="/api/desktop/external-tracking/photos"&&item.payload?._action==="delete");
      document.querySelector('[data-service-photo-delete="853"]')?.click();
      document.querySelector("#dialogSubmit")?.click();
      for(let i=0;i<30&&document.querySelector("#appDialog")?.open;i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const photoDeleteConfirmed=window.__confirmationWrites.some(item=>item.url==="/api/desktop/external-tracking/photos"&&item.payload?._action==="delete"&&String(item.payload.id)==="853");
      apiFetch=window.__originalApiFetch;
      hydrateDesktop=window.__originalHydrateDesktop;
      render=window.__originalRender;
      return {serviceDeleteDialog,serviceDeleteCancelled,serviceDeleteConfirmed,photoDeleteDialog,photoDeleteCancelled,photoDeleteConfirmed,quickCloseDialog,nativeConfirmCount:window.__nativeConfirmCount};
    })()`);
    if (!result.serviceDeleteDialog.open || !result.serviceDeleteDialog.danger || !result.serviceDeleteDialog.body.includes("TS-852") || !result.serviceDeleteCancelled || !result.serviceDeleteConfirmed) throw new Error(`Service delete confirmation failed: ${JSON.stringify(result)}`);
    if (!result.photoDeleteDialog.open || !result.photoDeleteDialog.danger || result.photoDeleteDialog.cancel !== "Hay\u0131r" || !result.photoDeleteCancelled || !result.photoDeleteConfirmed) throw new Error(`Photo delete confirmation failed: ${JSON.stringify(result)}`);
    if (!result.quickCloseDialog.open || !result.quickCloseDialog.body.includes("teknisyen panelinde tamamlan") || result.nativeConfirmCount !== 0) throw new Error(`Quick-close confirmation failed: ${JSON.stringify(result)}`);
    if (exceptions.length) throw new Error(`The browser reported exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(`${JSON.stringify({ ...result, exceptions, headless: true })}\n`);
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    if (browser.pid) {
      spawnSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      if (browser.exitCode === null) await Promise.race([new Promise(resolve => browser.once("exit", resolve)), delay(2000)]);
    }
    for (let attempt = 0; attempt < 5 && fs.existsSync(profile); attempt += 1) {
      try { fs.rmSync(profile, { recursive: true, force: true }); }
      catch (error) { if (attempt === 4) throw error; await delay(500); }
    }
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error.message}\n`); process.exitCode = 1; });
