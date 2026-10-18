const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_ROLE_CDP_PORT || 19313);
const baseUrl = process.argv[2];
const login = { identifier: process.env.AYEC_ROLE_LOGIN_USER || "", password: process.env.AYEC_ROLE_LOGIN_PASSWORD || "", tenantId: process.env.AYEC_ROLE_LOGIN_TENANT || "" };
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-role-audit-"));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !login.identifier || !login.password || !login.tenantId) throw new Error("Authenticated audit URL and login are required.");
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(tempRoot, "profile")}`, baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose the audit page.");
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
    let initialized = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      initialized = await evaluate("document.readyState === 'complete' && typeof initializeAuth === 'function' && Boolean(document.querySelector('#authRoot')?.innerHTML.trim())");
      if (initialized) break;
      await delay(100);
    }
    if (!initialized) throw new Error("Web app did not initialize.");
    const loginResult = await evaluate(`(async()=>{const response=await fetch(${JSON.stringify(new URL("/api/auth/login", baseUrl).toString())},{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({identifier:${JSON.stringify(login.identifier)},password:${JSON.stringify(login.password)},tenant_id:${JSON.stringify(login.tenantId)}})});const body=await response.json().catch(()=>({}));return{status:response.status,ok:body.ok===true,userId:body.user?.id,role:body.user?.role}})()`);
    if (!loginResult.ok) throw new Error("Authenticated role-audit login failed: " + JSON.stringify(loginResult));
    const authStatus = await evaluate(`(async()=>{const response=await fetch(${JSON.stringify(new URL("/api/auth/status", baseUrl).toString())});const status=await response.json();if(!status.authenticated||!status.user)return{authenticated:false};updateCurrentUser(status.user);hideAuth();await startApplication();return{authenticated:true,userId:status.user.id,role:status.user.role,permissions:status.user.permissions,isControlAdmin:status.user.is_control_admin}})()`);
    if (!authStatus.authenticated) throw new Error("Authenticated API status did not recognize the browser session.");
    let appReady = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      appReady = await evaluate("Boolean(currentAuthUser?.id && document.querySelector('#appShell') && !document.body.classList.contains('auth-active'))");
      if (appReady) break;
      await delay(100);
    }
    if (!appReady) throw new Error("Signed-in user did not reach the application shell.");
    const result = await evaluate(`(() => {
      const permissionData = typeof currentAuthUser.permissions === 'string' ? JSON.parse(currentAuthUser.permissions || '{}') : (currentAuthUser.permissions || {});
      const signedIn = { id: currentAuthUser.id, role: currentAuthUser.role, pages: permissionData.pages || [] };
      const inspect = (sector, allowed, denied) => {
        currentSector = sector;
        renderNav();
        return { sector, allowed: allowed.map(id => Boolean(document.querySelector('#nav [data-page="'+id+'"]'))), denied: denied.map(id => Boolean(document.querySelector('#nav [data-page="'+id+'"]'))) };
      };
      const technical = inspect('teknik_servis', ['dashboard','services','customers'], ['service-list','technician','support']);
      const automotive = inspect('otomotiv', ['dashboard','services','customers'], ['service-list','automotive-stock','vehicle-maintenance','support']);
      return { loginResult: ${JSON.stringify(loginResult)}, authStatus: ${JSON.stringify(authStatus)}, signedIn, technical, automotive, shellRole: document.querySelector('#currentUserRole')?.textContent || '' };
    })()`);
    if (!result.signedIn.id || !/Teknisyen|Technician/i.test(result.signedIn.role) || !result.signedIn.pages.includes(40) || result.technical.allowed.some(value => !value) || result.technical.denied.some(Boolean) || result.automotive.allowed[0] !== true || result.automotive.allowed[1] !== false || result.automotive.allowed[2] !== true || result.automotive.denied.some(Boolean) || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length }) + "\n");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      try { await new Promise(resolve => { socket.addEventListener("close", resolve, { once: true }); socket.send(JSON.stringify({ id: 999999, method: "Browser.close" })); setTimeout(resolve, 200); }); } catch (_) { socket.close(); }
    }
    browser.kill();
    await delay(200);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
