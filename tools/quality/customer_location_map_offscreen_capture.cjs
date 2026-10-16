const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_MAP_AUDIT_URL;
const cookies = JSON.parse(process.env.AYEC_MAP_AUDIT_COOKIES || "[]");
const outputPath = path.resolve(process.env.AYEC_MAP_AUDIT_SCREENSHOT || "output/playwright/customer-location-map-authenticated.png");
const debugPort = Number(process.env.AYEC_MAP_AUDIT_CDP_PORT || (9400 + process.pid % 500));
const profile = path.join(path.dirname(outputPath), `customer-location-map-profile-${process.pid}`);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function run() {
  if (!baseUrl || !cookies.length) throw new Error("Authenticated map audit requires a URL and session cookies.");
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--no-first-run", "--no-default-browser-check", "--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  const exceptions = [];
  try {
    let target;
    for (let i = 0; i < 100; i += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
        target = (await response.json()).find(item => item.type === "page");
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await wait(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless browser target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.result?.description || "No details."}`);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (const cookie of cookies) await send("Network.setCookie", { ...cookie, url: baseUrl });
    await send("Page.navigate", { url: baseUrl });
    let ready = false;
    for (let i = 0; i < 160; i += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof customerForm === 'function' && typeof openCustomerLocationMap === 'function'");
      if (ready) break;
      await wait(250);
    }
    if (!ready) throw new Error("Authenticated customer editor scripts did not load.");
    const fixture = await evaluate(`(() => {
      const form=document.createElement("form");form.id="dialogForm";form.style.cssText="position:fixed;inset:12px auto auto 12px;width:760px;height:650px;z-index:99999;background:#fff;overflow:auto;padding:12px";
      form.innerHTML='<input name="latitude" type="hidden" value="40.1044116"><input name="longitude" type="hidden" value="27.6563981"><button type="button" data-customer-geolocate>Locate</button><p data-customer-location-status></p><div class="customer-location-map" data-customer-map-wrap><iframe title="Customer map" data-customer-location-map></iframe><button type="button" data-customer-map-apply>Apply</button></div>';
      document.body.append(form);openCustomerLocationMap(form);return true;
    })()`);
    if (!fixture) throw new Error("Could not create map fixture.");
    let map = null;
    for (let i = 0; i < 180; i += 1) {
      map = await evaluate(`(() => {const frame=document.querySelector('#dialogForm [data-customer-location-map]'),doc=frame?.contentDocument;return {loaded:typeof frame?.contentWindow?.initAyecTomTomMap==='function',ready:frame?.contentWindow?.document.querySelector('#map-status')?.textContent||'',canvas:!!doc?.querySelector('#map canvas'),registered:document.querySelector('#dialogForm [data-customer-location-status]')?.textContent||''}})()`);
      if (map.ready.includes("hazir") || map.ready.includes("ready")) break;
      if (map.ready.includes("yuklenemedi") || map.ready.includes("unavailable")) break;
      await wait(250);
    }
    if (!map.loaded) throw new Error(`Map iframe did not load its SDK: ${JSON.stringify(map)}`);
    const rect = await evaluate(`(() => {const r=document.querySelector('#dialogForm iframe').getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()`);
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: rect.x + rect.width * 0.72, y: rect.y + rect.height * 0.52 });
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: rect.x + rect.width * 0.72, y: rect.y + rect.height * 0.52, button: "left", clickCount: 1 });
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: rect.x + rect.width * 0.72, y: rect.y + rect.height * 0.52, button: "left", clickCount: 1 });
    await wait(900);
    const selected = await evaluate(`(() => ({latitude:document.querySelector('#dialogForm [name="latitude"]').value,longitude:document.querySelector('#dialogForm [name="longitude"]').value,status:document.querySelector('#dialogForm [data-customer-location-status]').textContent,mapStatus:document.querySelector('#dialogForm iframe').contentDocument.querySelector('#map-status').textContent}))()`);
    const geolocationDenied = await evaluate(`(async () => {
      Object.defineProperty(navigator,"geolocation",{configurable:true,value:{getCurrentPosition(_success,failure){failure({message:"Permission denied"})}}});
      document.querySelector('#dialogForm [data-customer-geolocate]').click();
      await new Promise(resolve=>setTimeout(resolve,0));
      return {status:document.querySelector('#dialogForm [data-customer-location-status]').textContent,latitude:document.querySelector('#dialogForm [name="latitude"]').value,longitude:document.querySelector('#dialogForm [name="longitude"]').value};
    })()`);
    const reverseGeocodeError = await evaluate(`(async () => {
      const form=document.createElement("form");
      form.innerHTML="<input name=latitude value=40.1><input name=longitude value=27.6><input name=street value=Fixture-Street><textarea name=address>Fixture-Address</textarea><p data-customer-location-status></p>";
      document.body.append(form);
      const originalApiFetch=apiFetch;
      apiFetch=async()=>{throw new Error("Fixture reverse geocode unavailable")};
      const result=await reverseCustomerAddress(form,"40.1","27.6");
      apiFetch=originalApiFetch;
      const evidence={result,status:form.querySelector("[data-customer-location-status]").textContent,street:form.elements.street.value,address:form.elements.address.value};
      form.remove();
      return evidence;
    })()`);
    const addressSearchErrors = await evaluate(`(async () => {
      const form=document.createElement("form");form.id="dialogForm";
      form.innerHTML="<input name=street value=Fixture-Street><input name=neighborhood><input name=district><input name=city><input name=zip_code><button type=button data-customer-location-search>Search</button><p data-customer-location-status></p><div data-customer-location-results></div>";
      document.body.append(form);
      const search=form.querySelector("[data-customer-location-search]"),status=form.querySelector("[data-customer-location-status]"),originalApiFetch=apiFetch;
      apiFetch=async()=>({results:[]});search.click();await new Promise(resolve=>setTimeout(resolve,0));
      const noResults={status:status.textContent,enabled:!search.disabled};
      apiFetch=async()=>{throw new Error("Fixture address search unavailable")};search.click();await new Promise(resolve=>setTimeout(resolve,0));
      const requestError={status:status.textContent,enabled:!search.disabled};
      apiFetch=originalApiFetch;form.remove();return {noResults,requestError};
    })()`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(outputPath, Buffer.from(screenshot.data, "base64"));
    const changed = Math.abs(Number(selected.latitude) - 40.1044116) > 0.00005 || Math.abs(Number(selected.longitude) - 27.6563981) > 0.00005;
    process.stdout.write(JSON.stringify({ map, selected, changed, geolocationDenied, reverseGeocodeError, addressSearchErrors, browserExceptions: exceptions.length, screenshot: outputPath }) + "\n");
    if (!changed || !selected.status.includes("Haritadan")) throw new Error(`Map click did not update the selected customer coordinates: ${JSON.stringify({map,selected})}`);
    if (geolocationDenied.status !== "Permission denied" || geolocationDenied.latitude !== selected.latitude || geolocationDenied.longitude !== selected.longitude) throw new Error(`Geolocation denial was not handled cleanly: ${JSON.stringify(geolocationDenied)}`);
    if (reverseGeocodeError.result !== false || !reverseGeocodeError.status.includes("adres bilgileri getirilemedi") || reverseGeocodeError.street !== "Fixture-Street" || reverseGeocodeError.address !== "Fixture-Address") throw new Error(`Reverse geocoding error changed saved address data: ${JSON.stringify(reverseGeocodeError)}`);
    if (!addressSearchErrors.noResults.status.includes("Adres konumu bulunamadı") || !addressSearchErrors.noResults.enabled || addressSearchErrors.requestError.status !== "Fixture address search unavailable" || !addressSearchErrors.requestError.enabled) throw new Error(`Customer address search error state mismatch: ${JSON.stringify(addressSearchErrors)}`);
  } finally {
    try { await socket?.send(JSON.stringify({ id: 99999, method: "Browser.close" })); } catch (_) {}
    try { socket?.close(); } catch (_) {}
    try {
      const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
      const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      for (const pid of output.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
    } catch (_) { try { browser.kill(); } catch (_) {} }
  }
}
run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
