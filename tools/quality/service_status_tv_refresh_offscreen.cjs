const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_STATUS_TV_CDP_PORT || 19311);
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-status-tv-audit-"));
const profile = path.join(tempRoot, "profile");
const baseUrl = process.argv[2] || "http://127.0.0.1:8851/";
const sessionCookie = process.env.AYEC_STATUS_TV_SESSION_COOKIE || "";
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page");
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a page target.");
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
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    const fetchTracker = sessionCookie ? "window.__deviceReads=[];const nativeFetch=window.fetch.bind(window);window.fetch=(input,init={})=>{const url=typeof input==='string'?input:input.url;if(url.includes('/api/desktop/table/devices')&&(!init.method||init.method.toUpperCase()==='GET'))window.__deviceReads.push(Date.now());return nativeFetch(input,init)};" : "";
    await send("Page.addScriptToEvaluateOnNewDocument", { source: "window.__auditIntervals=[];const nativeSetInterval=window.setInterval.bind(window);window.setInterval=(callback,delay,...args)=>{window.__auditIntervals.push({callback,delay});return nativeSetInterval(callback,delay,...args)};" + fetchTracker });
    if (sessionCookie) {
      await send("Network.enable");
      const cookie = await send("Network.setCookie", { name: "ayec_session", value: sessionCookie, url: baseUrl, httpOnly: true, sameSite: "Lax" });
      if (!cookie.success) throw new Error("Could not install authenticated test session.");
    }
    await send("Page.navigate", { url: baseUrl + "?display=status-wall" });
    if (sessionCookie) {
      let authenticated = false;
      for (let attempt = 0; attempt < 120; attempt += 1) {
        authenticated = await evaluate("typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id)");
        if (authenticated) break;
        await delay(100);
      }
      if (!authenticated) throw new Error("Authenticated service-status app did not initialize.");
      await evaluate("window.__deviceReads=[];page='service-status';render()");
      let firstRead = false;
      for (let attempt = 0; attempt < 100; attempt += 1) {
        firstRead = await evaluate("document.body.dataset.page==='service-status' && window.__deviceReads.length>=1");
        if (firstRead) break;
        await delay(100);
      }
      if (!firstRead) throw new Error("The authenticated status board did not load tenant service rows: " + JSON.stringify(await evaluate("({page,bodyPage:document.body.dataset.page,meta:genericModules['service-status'],reads:window.__deviceReads,exceptions:window.__lastError||null,host:Boolean(document.querySelector('#genericHost')),content:document.querySelector('#content')?.innerText.slice(0,300)})")));
      let refreshDelayMs = 0;
      for (let attempt = 0; attempt < 150; attempt += 1) {
        refreshDelayMs = await evaluate("(()=>{const reads=window.__deviceReads;for(let i=1;i<reads.length;i++){const gap=reads[i]-reads[i-1];if(gap>=4500&&gap<=8000)return gap}return 0})()");
        if (refreshDelayMs) break;
        await delay(100);
      }
      await delay(200);
      const mutation = await evaluate(`(async()=>{const row=(window.currentGenericData?.rows||[]).find(item=>item.tracking_no==='TV-A-001');if(!row)throw new Error('Tenant service row is missing from the loaded table data.');await apiFetch('/api/desktop/table/devices',{method:'POST',body:JSON.stringify({id:row.id,_action:'update',status:'Teslim Edildi'})});return{baseline:window.__deviceReads.length,changedAt:Date.now()}})()`);
      let updated = false;
      for (let attempt = 0; attempt < 100; attempt += 1) {
        updated = await evaluate(`window.__deviceReads.length>${mutation.baseline}&&Boolean(document.querySelector('.status-wall-table')?.textContent.includes('Teslim Edildi'))`);
        if (updated) break;
        await delay(100);
      }
      const result = await evaluate(`({readCount:window.__deviceReads.length,intervalMs:window.__auditIntervals.find(item=>item.delay===5000&&item.callback.toString().includes('data-generic-refresh'))?.delay||0,refreshDelayMs:${refreshDelayMs},updateRefreshDelayMs:window.__deviceReads.length>${mutation.baseline}?window.__deviceReads[${mutation.baseline}]-${mutation.changedAt}:0,rowVisible:Boolean(document.querySelector('.status-wall-table')?.textContent.includes('TV-A-001')),updatedStatusVisible:Boolean(document.querySelector('.status-wall-table')?.textContent.includes('Teslim Edildi'))})`);
      if (!updated || result.intervalMs !== 5000 || result.refreshDelayMs < 4500 || result.refreshDelayMs > 8000 || result.updateRefreshDelayMs < 0 || result.updateRefreshDelayMs > 8000 || !result.rowVisible || !result.updatedStatusVisible || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
      process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length }) + "\n");
    } else {
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && Boolean(document.querySelector('#authRoot'))");
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("Web app did not finish loading.");
    for (let attempt = 0; attempt < 80; attempt += 1) {
      if (await evaluate("Boolean(document.querySelector('#authRoot')?.innerHTML.trim())")) break;
      await delay(100);
    }
    await evaluate(`(() => {
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      document.querySelector('#appShell')?.removeAttribute('inert');
      document.querySelector('#appShell')?.removeAttribute('aria-hidden');
      currentAuthUser = { id: 1, role: 'Admin', permissions: 'all' };
      page = 'service-status';
      render();
    })()`);
    await delay(150);
    const result = await evaluate(`(() => {
      const refresh = document.querySelector('[data-generic-refresh]');
      let clicks = 0;
      if (!refresh) return { found: false, clicks };
      refresh.addEventListener('click', () => { clicks += 1; });
      const timer = window.__auditIntervals.find(item => item.delay === 5000 && item.callback.toString().includes('data-generic-refresh'));
      if (!timer) return { found: false, clicks };
      document.body.dataset.page = 'dashboard';
      timer.callback();
      const offRouteClicks = clicks;
      document.body.dataset.page = 'service-status';
      timer.callback();
      return { found: true, intervalMs: timer.delay, offRouteClicks, onRouteClicks: clicks };
    })()`);
    if (!result.found || result.intervalMs !== 5000 || result.offRouteClicks !== 0 || result.onRouteClicks !== 1 || exceptions.length) {
      throw new Error(JSON.stringify({ result, exceptions }));
    }
    process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length }) + "\n");
    }
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      try { await new Promise(resolve => { socket.addEventListener("close", resolve, { once: true }); socket.send(JSON.stringify({ id: 999999, method: "Browser.close" })); setTimeout(resolve, 200); }); } catch (_) { socket.close(); }
    }
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true }); } catch (_) { browser.kill(); }
    await delay(200);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
