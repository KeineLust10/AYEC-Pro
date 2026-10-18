const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-security-confirm-"));
const port = 18800 + (process.pid % 900);
const cdpPort = 19600 + (process.pid % 900);
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = `http://127.0.0.1:${port}/`;
const profile = path.join(tempRoot, "edge-profile");
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });

async function stopProcess(process) {
  if (!process?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(process.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
}

async function run() {
  let browser;
  let socket;
  const exceptions = [];
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
    let target;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${cdpPort}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(150);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No hidden browser target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
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
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let scriptsReady = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      scriptsReady = await evaluate("document.readyState==='complete'&&typeof openManifestDialog==='function'&&typeof render==='function'");
      if (scriptsReady) break;
      await delay(200);
    }
    if (!scriptsReady) throw new Error("Web scripts were not ready.");
    const audit = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      window.currentAuthUser={id:1,username:'fixture-admin',role:'Admin',is_admin:true};
      window.auditCalls=[];
      window.auditSecurityState={app_lock_active:false,tech_lock_active:false,auto_login:false,app_password_configured:false,tech_password_configured:false,security_question:''};
      apiFetch=async(path,options={})=>{
        const body=options.body?JSON.parse(options.body):{};
        auditCalls.push({path,method:options.method||'GET',body});
        if(path==='/api/desktop/security-settings'&&(!options.method||options.method==='GET'))return {...auditSecurityState};
        if(path==='/api/desktop/security-settings/verify-action'){
          if(body.password!=='fixture-password')throw Error('The password is incorrect.');
          return {ok:true};
        }
        if(path==='/api/desktop/security-settings'&&options.method==='POST'){
          if(Boolean(body.auto_login)!==Boolean(auditSecurityState.auto_login)&&body.current_password!=='fixture-password')throw Error('Current password is required.');
          auditSecurityState={...auditSecurityState,...body};
          return {ok:true};
        }
        throw Error('Unexpected API '+path);
      };
      openManifestDialog({key:'security_confirm_dialog',title:'Action confirmation'});
      await new Promise(resolve=>setTimeout(resolve,80));
      const prompt=document.querySelector('#dialogBody input[name="password"]');
      if(!document.querySelector('#appDialog').open||!prompt)throw Error('Security confirmation dialog did not open.');
      prompt.value='wrong';
      document.querySelector('#dialogSubmit').click();
      await new Promise(resolve=>setTimeout(resolve,100));
      if(!document.querySelector('#appDialog').open||auditCalls.filter(call=>call.path.includes('verify-action')).length!==1)throw Error('Wrong password did not keep the confirmation open.');
      document.querySelector('#dialogBody input[name="password"]').value='fixture-password';
      document.querySelector('#dialogSubmit').click();
      await new Promise(resolve=>setTimeout(resolve,160));
      if(document.querySelector('#appDialog').open)throw Error('Valid password did not close the confirmation.');
      settingsSection='security';navigate('settings');
      await new Promise(resolve=>setTimeout(resolve,160));
      const toggle=document.querySelector('[data-security-toggle="auto_login"]');
      if(!toggle)throw Error('Automatic login control was not rendered.');
      toggle.checked=true;
      document.querySelector('[data-action="save-settings"]').click();
      await new Promise(resolve=>setTimeout(resolve,80));
      const settingsPrompt=document.querySelector('#dialogBody input[name="password"]');
      if(!document.querySelector('#appDialog').open||!settingsPrompt)throw Error('Automatic login change did not request current password.');
      settingsPrompt.value='fixture-password';
      document.querySelector('#dialogSubmit').click();
      await new Promise(resolve=>setTimeout(resolve,180));
      const saveCall=auditCalls.find(call=>call.path==='/api/desktop/security-settings'&&call.method==='POST'&&call.body.auto_login===true);
      if(!saveCall||saveCall.body.current_password!=='fixture-password'||auditSecurityState.auto_login!==true)throw Error('Automatic login was not saved with current-password verification.');
      return {directPrompt:true,wrongPasswordKeptOpen:true,validPasswordAccepted:true,automaticLoginReauth:true,passwordSentWithAtomicSave:true,apiCalls:auditCalls.map(call=>({path:call.path,method:call.method}))};
    })()`);
    if (!audit?.directPrompt || !audit?.wrongPasswordKeptOpen || !audit?.validPasswordAccepted || !audit?.automaticLoginReauth || !audit?.passwordSentWithAtomicSave || exceptions.length) throw new Error("Security confirmation browser audit failed: " + JSON.stringify({ audit, exceptions }));
    process.stdout.write(JSON.stringify({ audit, headless: true }) + "\n");
  } finally {
    try { socket?.close(); } catch (_) {}
    await stopProcess(browser);
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });


