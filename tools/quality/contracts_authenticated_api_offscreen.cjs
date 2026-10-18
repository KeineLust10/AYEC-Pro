const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9257);
const baseUrl = process.env.AYEC_AUDIT_URL;
const cookie = process.env.AYEC_CONTRACT_SESSION_COOKIE;
const contractId = Number(process.env.AYEC_CONTRACT_ID);
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `contract-auth-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !cookie || !contractId) throw new Error("Authenticated contract audit configuration is missing.");
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
    await send("Network.enable");
    await send("Network.setCookie", { name: "ayec_session", value: cookie, url: baseUrl });
    await send("Page.navigate", { url: baseUrl });
    for (let i = 0; i < 120; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof apiFetch === 'function' && typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id)")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      document.body.dataset.page = "contracts";
      page = "contracts";
      const contractsShell = document.createElement("div");
      contractsShell.innerHTML = renderContractsReference();
      await loadGenericModule(genericModules.contracts);
      const contractMetrics = [...contractsShell.querySelectorAll(".contracts-reference-metrics .metric strong")].map(node=>node.textContent.trim());
      const slaResponseMetric = contractMetrics[3] || "";
      if (slaResponseMetric !== "-") throw new Error("Unmeasured SLA response metric changed: " + JSON.stringify(contractMetrics));
      db.settings.doubleClick = true;
      const host = document.createElement("div");
      host.innerHTML = '<table class="contracts-reference-table"><tbody><tr data-contract-id="${contractId}"><td>Authenticated contract</td></tr></tbody></table>';
      document.body.append(host);
      host.querySelector("tr").dispatchEvent(new MouseEvent("dblclick", {bubbles:true,cancelable:true}));
      for (let i=0;i<40&&!document.querySelector(".contract-detail-modal");i++) await new Promise(resolve=>setTimeout(resolve,100));
      const opened = document.querySelector(".contract-detail-modal")?.textContent || "";
      if (!opened.includes("Maintenance Plan")) throw new Error("Authenticated contract detail did not load from tenant API: " + opened);
      const dataBase64 = btoa("%PDF-1.4 authenticated tenant upload");
      const created = await apiFetch("/api/desktop/contracts/${contractId}/attachments", {method:"POST",body:JSON.stringify({filename:"browser-contract.pdf",data_base64:dataBase64})});
      const attachmentId = created.id;
      const detail = await apiFetch("/api/desktop/contracts/${contractId}/attachments");
      if (!detail.attachments.some(item=>item.id===attachmentId&&item.filename==="browser-contract.pdf")) throw new Error("Uploaded file is missing from the authenticated tenant detail response.");
      await apiFetch("/api/desktop/contracts/attachments/delete",{method:"POST",body:JSON.stringify({attachment_id:attachmentId})});
      const afterDelete = await apiFetch("/api/desktop/contracts/${contractId}/attachments");
      return {role:currentAuthUser.role,isControlAdmin:currentAuthUser.is_control_admin===true,opened:opened.includes("Maintenance Plan"),uploaded:detail.attachments.some(item=>item.id===attachmentId),attachmentId,deleted:afterDelete.attachments.every(item=>item.id!==attachmentId),slaResponseMetric};
    })()`);
    if (result.role !== "Admin" || result.isControlAdmin || !result.opened || !result.uploaded || !result.attachmentId || !result.deleted || result.slaResponseMetric !== "-" || exceptions.length) throw new Error(JSON.stringify({result,exceptions}));
    const shot = await send("Page.captureScreenshot", {format:"png",captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir,"contracts-authenticated-api-headless.png"),Buffer.from(shot.data,"base64"));
    console.log(JSON.stringify({result,exceptions:exceptions.length,headless:true}));
  } finally {
    if (socket) socket.close();
    browser.kill();
    try { fs.rmSync(profile,{recursive:true,force:true}); } catch (_) {}
  }
}
run().catch(error => { console.error(error.stack || error); process.exitCode = 1; });
