const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/mobile-guide-offscreen"));
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-mobile-guide-audit-"));
const port = Number(process.env.AYEC_AUDIT_PORT || 19400 + process.pid % 400);
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30700 + process.pid % 500);
const baseUrl = `http://127.0.0.1:${port}/`;
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
const profile = path.join(outputDir, `mobile-guide-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
}

async function waitForPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Hidden Edge page did not become available.");
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "audit-result.json");
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const target = await waitForPage();
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
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
      return response.result?.value;
    };
    await send("Runtime.enable");
    await send("Page.enable");
    await send("Page.navigate", { url: baseUrl });
    await evaluate(`new Promise((resolve,reject)=>{let attempts=0;const timer=setInterval(()=>{if(typeof page!=="undefined"&&typeof render==="function"){clearInterval(timer);resolve(true)}else if(++attempts>100){clearInterval(timer);reject(new Error("AYEC app globals did not load"))}},50)})`);
    const workflow = await evaluate(`(async()=>{
      const original={page,toast,clipboard:Object.getOwnPropertyDescriptor(navigator,"clipboard")};
      const messages=[];let copiedText=null;
      const waitFor=async(selector)=>{for(let i=0;i<80;i++){const node=document.querySelector(selector);if(node)return node;await new Promise(resolve=>setTimeout(resolve,50))}throw new Error("Timed out waiting for "+selector)};
      try{
        page="mobile-guide";render();
        const copyButton=await waitFor("[data-mobile-guide-copy]"),image=await waitFor(".mobile-guide-qr img"),address=document.querySelector(".mobile-guide-link a");
        const expectedAddress=new URL("/?page=stock",location.origin).href;
        Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async text=>{copiedText=text}}});
        toast=(message,type)=>messages.push({message,type});
        copyButton.click();for(let i=0;i<80&&(copiedText===null||messages.length===0);i++)await new Promise(resolve=>setTimeout(resolve,50));
        const result={address:address?.href||null,expectedAddress,copiedText,copySuccess:messages.at(-1)||null};
        image.dispatchEvent(new Event("error"));
        result.qrHidden=image.hidden;result.fallbackVisible=Boolean(document.querySelector(".mobile-guide-qr-error"));result.fallbackText=document.querySelector(".mobile-guide-qr-error")?.textContent||null;
        Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async()=>{throw new Error("clipboard unavailable")}}});
        copyButton.click();for(let i=0;i<80&&messages.length<2;i++)await new Promise(resolve=>setTimeout(resolve,50));
        result.copyFailure=messages.at(-1)||null;return result;
      }finally{page=original.page;toast=original.toast;if(original.clipboard)Object.defineProperty(navigator,"clipboard",original.clipboard);else delete navigator.clipboard;render()}
    })()`);
    const expected = workflow.address === workflow.expectedAddress && workflow.copiedText === workflow.expectedAddress && workflow.copySuccess?.type === "success" && workflow.qrHidden && workflow.fallbackVisible && workflow.copyFailure?.type === "error";
    const result = { ok: Boolean(expected && exceptions.length === 0), workflow, browserExceptions: exceptions };
    fs.writeFileSync(resultPath, JSON.stringify(result, null, 2), "utf8");
    if (!result.ok) process.exitCode = 1;
    process.stdout.write(JSON.stringify({ resultPath, ok: result.ok }) + "\n");
  } catch (error) {
    fs.writeFileSync(resultPath, JSON.stringify({ ok: false, error: String(error.stack || error) }, null, 2), "utf8");
    process.stderr.write(String(error.stack || error) + "\n");
    process.exitCode = 1;
  } finally {
    try { socket?.close(); } catch (_) {}
    await stopProcess(browser);
    await stopProcess(server);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
