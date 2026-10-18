const fs = require("node:fs");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const { pathToFileURL } = require("node:url");

const root = path.resolve(__dirname, "../..");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = 42000 + (process.pid % 10000);
const indexPath = path.join(root, "Web_Arayuzu", "web", "index.html");
const profileRoot = path.resolve(root, "output", "playwright");
const profile = path.join(profileRoot, `customer-location-geocode-profile-${process.pid}`);
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
      ready = await evaluate("document.readyState === 'complete' && typeof db === 'object' && typeof openDialog === 'function' && typeof customerForm === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("The customer form and web shell did not become ready.");
    const result = await evaluate(`(async() => {
      window.__geocodeCalls=[];
      window.__geocodeMode="empty";
      window.__originalGeocodeApi=apiFetch;
      apiFetch=async(url,options={})=>{
        window.__geocodeCalls.push({url:String(url),payload:options.body?JSON.parse(options.body):null});
        if(String(url)==="/api/desktop/field-service/geocode"){
          if(window.__geocodeMode==="empty")return {results:[]};
          if(window.__geocodeMode==="failure")throw Error("Provider unavailable");
          return {results:[{display_name:"Test Street, Gonen, Balikesir",lat:39.6401,lon:27.6402}]};
        }
        if(String(url)==="/api/desktop/field-service/reverse-geocode")return {city:"Balikesir",district:"Gonen",street:"Test Street",display_name:"Test Street, Gonen, Balikesir"};
        return {ok:true};
      };
      openDialog("Customer Location","CRM",customerForm({name:"Fixture Customer",city:"Balikesir",district:"Gonen",street:"Test Street"}),()=>true,"Close");
      const form=document.querySelector("#dialogForm");
      const search=form.querySelector("[data-customer-location-search]");
      form.elements.city.value="";
      form.elements.district.value="";
      form.elements.street.value="";
      search.click();
      const blankStatus=form.querySelector("[data-customer-location-status]")?.textContent||"";
      form.elements.city.value="Balikesir";
      form.elements.district.value="Gonen";
      form.elements.street.value="Test Street";
      search.click();
      for(let i=0;i<30&&!(form.querySelector("[data-customer-location-status]")?.textContent||"").includes("konumu bulunamad\u0131");i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const emptyState={status:form.querySelector("[data-customer-location-status]")?.textContent||"",searchEnabled:!search.disabled,results:form.querySelectorAll("[data-customer-location-index]").length};
      window.__geocodeMode="failure";
      search.click();
      for(let i=0;i<30&&!(form.querySelector("[data-customer-location-status]")?.textContent||"").includes("Provider unavailable");i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const failureState={status:form.querySelector("[data-customer-location-status]")?.textContent||"",searchEnabled:!search.disabled};
      window.__geocodeMode="success";
      search.click();
      for(let i=0;i<30&&!form.querySelector("[data-customer-location-index]");i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const queryState={calls:window.__geocodeCalls,results:[...form.querySelectorAll("[data-customer-location-index]")].map(button=>button.textContent),status:form.querySelector("[data-customer-location-status]")?.textContent||""};
      form.querySelector("[data-customer-location-index]")?.click();
      for(let i=0;i<30&&!String(form.querySelector("[data-customer-location-status]")?.textContent||"").includes("Konumdan adres");i+=1)await new Promise(resolve=>setTimeout(resolve,20));
      const selected={latitude:form.elements.latitude.value,longitude:form.elements.longitude.value,city:form.elements.city.value,district:form.elements.district.value,street:form.elements.street.value,address:form.elements.address.value,status:form.querySelector("[data-customer-location-status]")?.textContent||""};
      apiFetch=window.__originalGeocodeApi;
      document.querySelector("#dialogCancel")?.click();
      return {blankStatus,emptyState,failureState,queryState,selected};
    })()`);
    const call = result.queryState.calls[0];
    const reverseCall = result.queryState.calls.find(item => item.url === "/api/desktop/field-service/reverse-geocode");
    if (!result.blankStatus.includes("\u00d6nce adres") || !result.emptyState.status.includes("konumu bulunamadı") || !result.emptyState.searchEnabled || result.emptyState.results !== 0 || !result.failureState.status.includes("Provider unavailable") || !result.failureState.searchEnabled || call?.url !== "/api/desktop/field-service/geocode" || call.payload?.query !== "Test Street, Gonen, Balikesir" || result.queryState.results[0] !== "Test Street, Gonen, Balikesir" || reverseCall?.url !== "/api/desktop/field-service/reverse-geocode" || reverseCall.payload?.lat !== 39.6401 || reverseCall.payload?.lon !== 27.6402 || result.queryState.calls.length !== 4 || result.selected.latitude !== "39.6401" || result.selected.longitude !== "27.6402" || result.selected.city !== "Balikesir" || result.selected.district !== "Gonen" || result.selected.street !== "Test Street" || result.selected.address !== "Test Street, Gonen, Balikesir" || result.selected.status !== "Konumdan adres bilgileri dolduruldu." || exceptions.length) {
      throw new Error(`Customer geocoding selection failed: ${JSON.stringify({ ...result, exceptions })}`);
    }
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
