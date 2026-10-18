const { spawn, spawnSync } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9251);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(os.tmpdir(), `contracts-dblclick-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let i = 0; i < 100; i += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless Edge CDP target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const msg = JSON.parse(event.data);
      if (msg.method === "Runtime.exceptionThrown") exceptions.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
      if (!msg.id) return;
      const task = pending.get(msg.id);
      if (!task) return;
      pending.delete(msg.id);
      msg.error ? task.reject(new Error(msg.error.message)) : task.resolve(msg.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let i = 0; i < 80; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof apiFetch === 'function' && document.querySelector('#appDialog')")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      document.body.dataset.page = "contracts"; db.settings.doubleClick = false;
      let calls = [];
      apiFetch = async (url, options = {}) => { calls.push({url, options}); return options.method === "POST" ? {id: 15} : { contract: { id: 44, title: "Fixture contract", customer_name: "Fixture customer", contract_type: "Servis", description: "Details" }, attachments: [{id: 14, filename: "service.pdf", created_at: "2026-10-16", available: true}] }; };
      const host = document.createElement("div"); host.innerHTML = '<table class="contracts-reference-table"><tbody><tr data-contract-id="44"><td>Fixture</td><td><button type="button">Action</button></td></tr></tbody></table>';
      document.body.append(host); const row = host.querySelector("tr");
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 20));
      const disabled = { calls: calls.length, opened: document.querySelector("#appDialog")?.open === true };
      db.settings.doubleClick = true;
      row.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 80));
      const attachmentOption=document.querySelector('[data-contract-attachment-select="14"]');
      attachmentOption?.click();
      const preview = document.querySelector("[data-contract-attachment-open]");
      const previewOpenings=[];
      preview?.addEventListener("click",event=>{event.preventDefault();previewOpenings.push({href:preview.getAttribute("href"),target:preview.getAttribute("target")})});
      attachmentOption?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      const enabled = { calls: calls.length, opened: document.querySelector("#appDialog")?.open === true, title: document.querySelector("#dialogTitle")?.textContent || "", content: document.querySelector("#dialogBody")?.textContent || "", previewHref: preview?.getAttribute("href") || "", previewTarget: preview?.getAttribute("target") || "", selectedId: attachmentOption?.getAttribute("aria-pressed") === "true" ? attachmentOption.dataset.contractAttachmentSelect : "", doubleClickPreview: previewOpenings[0] || null };
      const detailRect = document.querySelector("#appDialog")?.getBoundingClientRect();
      enabled.dialogSize = detailRect ? [detailRect.width, detailRect.height] : [];
      document.querySelector("#appDialog")?.close();
      host.querySelector("button").dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true })); await new Promise(resolve => setTimeout(resolve, 20));
      const buttonTargetIgnored = calls.length === 1;
      const file = new File(["fixture"], "signed-agreement.pdf", {type: "application/pdf"});
      const fileInput = document.querySelector("#contractAttachmentInput");
      Object.defineProperty(fileInput, "files", {configurable: true, value: [file]});
      fileInput.dispatchEvent(new Event("change", {bubbles: true})); await new Promise(resolve => setTimeout(resolve, 100));
      const upload = calls.find(call => call.url === "/api/desktop/contracts/44/attachments" && call.options.method === "POST");
      const uploadPayload = upload ? JSON.parse(upload.options.body) : null;
      document.querySelector('[data-contract-attachment-select="14"]')?.click();
      const remove = document.querySelector('[data-contract-attachment-delete="14"]');
      remove.click();
      const confirmation = document.querySelector("#dialogTitle")?.textContent || "";
      document.querySelector("#dialogSubmit")?.click(); await new Promise(resolve => setTimeout(resolve, 120));
      const deletion = calls.find(call => call.url === "/api/desktop/contracts/attachments/delete");
      return { disabled, enabled, buttonTargetIgnored, upload: uploadPayload, confirmation, deletion: deletion ? JSON.parse(deletion.options.body) : null, refreshed: document.querySelector("#appDialog")?.open === true };
    })()`);
    result.layout = await evaluate("(()=>Object.fromEntries(['#appDialog','#dialogForm','#dialogForm>header','#dialogBody','#dialogFooter','.contract-detail-modal','.contract-detail-info','.contract-detail-files','.contract-detail-files>header','.contract-attachment-list','.contract-detail-actions','[data-contract-attachment-upload]','.contract-detail-files>small'].map(s=>{const e=document.querySelector(s),r=e?.getBoundingClientRect(),c=e&&getComputedStyle(e);return[s,r?{x:r.x,y:r.y,width:r.width,height:r.height,bottom:r.bottom,display:c.display,flexBasis:c.flexBasis}:null]})))()");
    if (result.disabled.calls !== 0 || result.disabled.opened || result.enabled.calls !== 1 || !result.enabled.opened || !(result.enabled.title.startsWith("S") && result.enabled.title.endsWith(" & Ekleri")) || !result.enabled.content.includes("Fixture contract") || !result.enabled.previewHref.endsWith("/14/preview") || result.enabled.previewTarget !== "_blank" || result.enabled.selectedId !== "14" || !result.enabled.doubleClickPreview?.href.endsWith("/14/preview") || result.enabled.doubleClickPreview.target !== "_blank" || result.enabled.dialogSize.some((value,index)=>Math.abs(value-[650,738][index])>1) || !result.buttonTargetIgnored || result.upload?.filename !== "signed-agreement.pdf" || !result.upload.data_base64 || !result.confirmation.includes("Eki Sil") || result.deletion?.attachment_id !== 14 || !result.refreshed || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    await evaluate("document.activeElement?.blur()");
    const clip = await evaluate("(()=>{const r=document.querySelector('#appDialog').getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height,scale:1}})()");
    const shot = await send("Page.captureScreenshot", { format: "png", clip, captureBeyondViewport: true });
    fs.writeFileSync(path.join(outDir, "contracts-double-click-detail-headless.png"), Buffer.from(shot.data, "base64"));
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 812, deviceScaleFactor: 1, mobile: false });
    result.mobileDialogSize = await evaluate("(()=>{const r=document.querySelector('#appDialog').getBoundingClientRect();return [r.width,r.height]})()");
    if (result.mobileDialogSize.some((value,index)=>Math.abs(value-[358,738][index])>1)) throw new Error(JSON.stringify({ mobileDialogSize: result.mobileDialogSize }));
    console.log(JSON.stringify({ result, exceptions: exceptions.length, headless: true }));
  } finally {
    if (socket) socket.close();
    if (browser.pid) spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    try { fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 }); } catch (error) { if (error.code !== "EPERM") throw error; }
  }
}
run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });

