const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `company-location-headless-profile-${process.pid}`);

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const targets = await response.json();
      const origin = new URL(baseUrl).origin;
      const page = targets.find(target => target.type === "page" && target.url?.startsWith(origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose the local AYEC page.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
    "--window-size=1280,900", baseUrl
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  const exceptions = [];
  try {
    const target = await waitForTarget();
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
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 30000);
      pending.set(id, {
        resolve(value) { clearTimeout(timer); resolve(value); },
        reject(error) { clearTimeout(timer); reject(error); }
      });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.result?.description || "No details."}`);
      return result.result.value;
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof desktopSettings !== 'undefined' && typeof desktopWrite === 'function' && typeof currentAuthUser !== 'undefined'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Company settings UI did not initialize.");

    const initial = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page = "settings";
      settingsSection = "company";
      currentAuthUser = { username: "map-audit-user", role: "Admin" };
      desktopSettings = { company_name: "Map Audit", company_address: "Old Address", map_default_lat: "38.222222", map_default_lng: "29.888888", installation_lat: "40.104412", installation_lng: "27.656398", installation_address: "Old Address", "map_default_lat_user_map-audit-user": "39.333333", "map_default_lng_user_map-audit-user": "28.777777" };
      window.__companyLocationWrites = [];
      apiFetch = async (url, options = {}) => {
        if (url.includes("product_bank_mappings") || url.includes("bank_accounts")) return { rows: [] };
        if (url === "/api/desktop/field-service/reverse-geocode") return { display_name: "New Test Address", city: "Test City", district: "Test District", neighborhood: "Test Quarter", street: "New Test Street", zip_code: "12345" };
        throw new Error("Unexpected company-location request: " + url + " " + options.method);
      };
      desktopWrite = async (table, payload) => { window.__companyLocationWrites.push({ table, ...payload }); desktopSettings[payload.key] = payload.value; return { ok: true }; };
      render();
      const host = document.querySelector(".settings-content");
      const frame = host?.querySelector("[data-company-location-map]");
      if (!frame) throw new Error("Company location map frame missing.");
      window.__companyLocationTestFrame = frame;
      const addFrameListener = frame.addEventListener.bind(frame);
      frame.addEventListener = (type, listener, options) => {
        if (type !== "load") return addFrameListener(type, listener, options);
        window.__companyFrameLoadRegistrations = (window.__companyFrameLoadRegistrations || 0) + 1;
        return addFrameListener(type, function(event) {
          window.__companyFrameLoadEvents = (window.__companyFrameLoadEvents || 0) + 1;
          const mapWindow = frame.contentWindow;
          window.__companyFramePathAtLoad = mapWindow?.location?.pathname || "";
          if (frame.src.includes("/field-vector-map-dist/") && mapWindow) {
            window.__companyTestInitInstalled = true;
            mapWindow.initAyecTomTomMap = (provider, latitude, longitude) => {
              window.__mapInit = { provider, latitude, longitude };
              mapWindow.ayecTomTomMap = {
                onClick(callback) { mapWindow.__locationCallback = callback; },
                select(latitudeValue, longitudeValue) { mapWindow.__selectedPoint = [latitudeValue, longitudeValue]; },
                refresh() {}
              };
              mapWindow.dispatchEvent(new mapWindow.Event("ayec-map-ready"));
              return true;
            };
          }
          return listener.call(this, event);
        }, options);
      };
      return { page, settingsSection, title: host.querySelector("#companyLocation h3")?.textContent || "", latitude: host.querySelector('[data-setting-key="map_default_lat"]')?.value || "", longitude: host.querySelector('[data-setting-key="map_default_lng"]')?.value || "", saveVisible: Boolean(host.querySelector("[data-company-map-save]")), mapInitiallyHidden: frame.hidden };
    })()`);
    if (!initial.saveVisible || !initial.mapInitiallyHidden || initial.latitude !== "40.104412" || initial.longitude !== "27.656398") throw new Error(`Company location panel did not render from the installation or user defaults: ${JSON.stringify(initial)}`);

    const opened = await evaluate(`(() => { document.querySelector("[data-company-map-pick]").click(); const frame=document.querySelector("[data-company-location-map]"); return {sameFrame:frame===window.__companyLocationTestFrame,src:frame?.src,hidden:frame?.hidden,classes:frame?.parentElement?.className}; })()`);
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (await evaluate("typeof document.querySelector('[data-company-location-map]')?.contentWindow?.__locationCallback === 'function'")) break;
      await delay(50);
    }
    const callbackReady = await evaluate("typeof document.querySelector('[data-company-location-map]')?.contentWindow?.__locationCallback === 'function'");
    if (!callbackReady) throw new Error(`Map callback registration failed: ${JSON.stringify({ opened, state: await evaluate("({sameFrame:document.querySelector('[data-company-location-map]')===window.__companyLocationTestFrame, init:window.__mapInit, testInitInstalled:window.__companyTestInitInstalled, loadRegistrations:window.__companyFrameLoadRegistrations, loadEvents:window.__companyFrameLoadEvents, pathAtLoad:window.__companyFramePathAtLoad, status:document.querySelector('[data-company-map-status]')?.textContent, src:document.querySelector('[data-company-location-map]')?.src, framePath:document.querySelector('[data-company-location-map]')?.contentWindow?.location?.pathname, frameReady:document.querySelector('[data-company-location-map]')?.contentDocument?.readyState})") })}`);
    const selected = await evaluate(`(async () => {
      const frame = document.querySelector("[data-company-location-map]");
      if (typeof frame.contentWindow.__locationCallback !== "function") throw new Error("Interactive map callback was not registered: " + JSON.stringify({ src: frame.src, ready: frame.contentDocument?.readyState, init: typeof frame.contentWindow.initAyecTomTomMap, map: typeof frame.contentWindow.ayecTomTomMap, status: document.querySelector("[data-company-map-status]")?.textContent, started: frame.dataset.started, mapInit: window.__mapInit, mapReady: frame.contentWindow.__mapReady, apiMap: frame.contentWindow.ayecTomTomMap ? Object.keys(frame.contentWindow.ayecTomTomMap) : [] }));
      await frame.contentWindow.__locationCallback(41.123456, 29.654321);
      await new Promise(resolve => setTimeout(resolve, 0));
      const host = document.querySelector(".settings-content");
      return {
        mapVisible: !frame.hidden,
        mapInit: window.__mapInit,
        selectedPoint: frame.contentWindow.__selectedPoint,
        latitude: host.querySelector('[data-setting-key="map_default_lat"]')?.value || "",
        longitude: host.querySelector('[data-setting-key="map_default_lng"]')?.value || "",
        address: host.querySelector("[data-company-location-address]")?.value || "",
        status: host.querySelector("[data-company-map-status]")?.textContent || "",
        writes: window.__companyLocationWrites
      };
    })()`);
    if (!opened?.sameFrame || !selected.mapVisible || selected.mapInit?.provider !== "ayec-server-proxy" || selected.latitude !== "41.123456" || selected.longitude !== "29.654321" || selected.address !== "New Test Address") {
      throw new Error(`Company location selection mismatch: ${JSON.stringify(selected)}`);
    }
    const userAddressWrites = selected.writes.filter(item => item.key.startsWith("map_default_") && item.key.includes("_user_map-audit-user"));
    if (JSON.stringify(userAddressWrites.map(item => item.key)) !== JSON.stringify(["map_default_address_user_map-audit-user", "map_default_city_user_map-audit-user", "map_default_district_user_map-audit-user"])) {
      throw new Error(`Per-user address settings mismatch: ${JSON.stringify(userAddressWrites)}`);
    }

    const saved = await evaluate(`(async () => {
      document.querySelector("[data-company-map-save]").click();
      await new Promise(resolve => setTimeout(resolve, 0));
      const writes = window.__companyLocationWrites;
      return {
        writes,
        installation: [desktopSettings.installation_lat, desktopSettings.installation_lng, desktopSettings.installation_address],
        companyAddress: desktopSettings.company_address,
        userCoordinates: [desktopSettings["map_default_lat_user_map-audit-user"], desktopSettings["map_default_lng_user_map-audit-user"]]
      };
    })()`);
    const savedKeys = saved.writes.map(item => item.key);
    for (const key of ["installation_lat", "installation_lng", "installation_address", "company_address", "map_default_lat_user_map-audit-user", "map_default_lng_user_map-audit-user"]) {
      if (!savedKeys.includes(key)) throw new Error(`Company location save did not write ${key}.`);
    }
    if (saved.installation[0] !== "41.123456" || saved.installation[1] !== "29.654321" || saved.installation[2] !== "New Test Address" || saved.companyAddress !== "New Test Address") {
      throw new Error(`Company location save payload mismatch: ${JSON.stringify(saved)}`);
    }
    await evaluate('document.querySelector("#companyLocation")?.scrollIntoView({block:"start"})');
    await delay(100);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const filename = path.join(outputDir, "company-location-picker-headless.png");
    fs.writeFileSync(filename, Buffer.from(screenshot.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(`${JSON.stringify({ initial, selected, saved: { installation: saved.installation, companyAddress: saved.companyAddress, userCoordinates: saved.userCoordinates, writtenKeys: savedKeys }, browserExceptions: exceptions.length, screenshot: filename })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
