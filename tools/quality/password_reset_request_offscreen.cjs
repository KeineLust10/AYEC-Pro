const { spawn, spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const net = require("node:net");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const freePort = () => new Promise((resolve, reject) => {
  const server = net.createServer();
  server.once("error", reject);
  server.listen(0, "127.0.0.1", () => {
    const port = server.address().port;
    server.close(error => error ? reject(error) : resolve(port));
  });
});

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const profile = path.join(outDir, `password-reset-profile-${process.pid}`);
  const port = await freePort();
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge page was created.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map(), exceptions = [];
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
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("typeof renderPasswordResetRequest === 'function' && typeof renderLogin === 'function' && typeof openManifestDialog === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Authentication UI scripts did not become ready.");
    await delay(800);
    const authRoutes = await evaluate(`(async()=>{
      authTenants=[{id:"audit-tenant",company_name:"Audit Company"}];
      registrationEnabled=true;
      openManifestDialog({key:"registration_dialog"});
      await new Promise(resolve=>setTimeout(resolve,30));
      const registrationOpen=Boolean(document.querySelector("#registerForm"));
      openManifestDialog({key:"login_dialog"});
      await new Promise(resolve=>setTimeout(resolve,30));
      return {registrationOpen,loginOpen:Boolean(document.querySelector("#loginForm"))};
    })()`);
    if (!authRoutes.registrationOpen || !authRoutes.loginOpen) throw new Error("Login or registration manifest route failed.");
    const requestForm = await evaluate(`(async()=>{
      openManifestDialog({key:"login_dialog"});
      await new Promise(resolve=>setTimeout(resolve,30));
      const link=document.querySelector("#authPasswordReset");
      if(!link)throw new Error("Login screen does not show the password reset action: "+JSON.stringify({form:Boolean(document.querySelector("#loginForm")),help:Boolean(document.querySelector(".auth-help")),text:document.body.innerText.slice(0,260)}));
      link.click();
      const form=document.querySelector("#passwordResetRequestForm");
      if(!form||!form.elements.identifier)throw new Error("Password reset request form is incomplete.");
      form.elements.identifier.value="audit@example.com";
      window.__resetWrites=[];
      apiFetch=async(url,options={})=>{window.__resetWrites.push({url:String(url),payload:JSON.parse(options.body||"{}")} );return {ok:true}};
      return {linkText:link.textContent,formTitle:document.querySelector(".auth-step-label")?.textContent||""};
    })()`);
    const first = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    fs.writeFileSync(path.join(outDir, "password-reset-request-headless.png"), Buffer.from(first.data, "base64"));
    const request = await evaluate(`(async()=>{
      const form=document.querySelector("#passwordResetRequestForm");
      await form.onsubmit({preventDefault(){}});
      await new Promise(resolve=>setTimeout(resolve,30));
      return {request:window.__resetWrites[0],confirmation:document.querySelector(".auth-alert")?.textContent||""};
    })()`);
    if (request.request?.url !== "/api/auth/request-password-reset" || request.request?.payload?.identifier !== "audit@example.com") throw new Error(`Password reset submission did not send the expected request: ${JSON.stringify(request)}`);
    if (!request.confirmation.includes("s\u0131f\u0131rlama ba\u011flant\u0131s\u0131")) throw new Error("The generic password reset confirmation was not shown.");
    const final = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    fs.writeFileSync(path.join(outDir, "password-reset-result-headless.png"), Buffer.from(final.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${exceptions.join(" | ")}`);
    process.stdout.write(JSON.stringify({ headless: true, authRoutes, link: request.linkText, request: request.request, confirmation: request.confirmation, exceptions, screenshots: ["password-reset-request-headless.png", "password-reset-result-headless.png"] }));
    await send("Browser.close");
    socket.close();
  } finally {
    try { socket?.close(); } catch (_) {}
    if (process.platform === "win32") {
      const safeProfile = profile.replace(/'/g, "''");
      const command = `$profilePath='${safeProfile}'; $roots=Get-CimInstance Win32_Process -Filter "name='msedge.exe'" | Where-Object { $_.CommandLine -like "*$profilePath*" -and $_.CommandLine -like '*--headless=new*' }; foreach($root in $roots){ & taskkill /PID $root.ProcessId /T /F | Out-Null }`;
      spawnSync("powershell.exe", ["-NoProfile", "-Command", command], { stdio: "ignore", windowsHide: true });
      if (browser.pid) spawnSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      await delay(500);
    } else browser.kill();
    const root = path.resolve(outDir), resolvedProfile = path.resolve(profile);
    if (resolvedProfile.startsWith(root + path.sep) && fs.existsSync(resolvedProfile)) {
      try { fs.rmSync(resolvedProfile, { recursive: true, force: true, maxRetries: 8, retryDelay: 200 }); } catch (_) {}
    }
  }
}

run().catch(error => { process.stderr.write(error.stack || String(error)); process.exitCode = 1; });
