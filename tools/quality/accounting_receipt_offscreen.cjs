const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9253);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outDir, `accounting-receipt-profile-${process.pid}`);
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
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable"); await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let i = 0; i < 80; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof financeDetailDialog === 'function' && document.querySelector('#appDialog')")) break;
      await delay(200);
    }
    const ready = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      const item={id:73,source:"accounting",receipt_available:true,type_label:"Gider",description:"Fixture receipt",amount_try:73,currency:"TRY"};
      window.__receiptItem=item;
      ayecFinanceLedgerItems=[item]; db.finance=[];
      window.__receiptRequests=[]; window.__receiptClicked=null;
      fetch=async url=>{window.__receiptRequests.push(String(url));return {ok:true,headers:{get:()=>"attachment; filename*=UTF-8''expense-receipt.pdf"},blob:async()=>new Blob(["fixture"])};};
      URL.createObjectURL=()=>"blob:receipt-fixture"; URL.revokeObjectURL=()=>{};
      HTMLAnchorElement.prototype.click=function(){window.__receiptClicked={href:this.href,download:this.download}};
      financeDetailDialog(item);
      const button=document.querySelector('[data-finance-detail-action="receipt"]');
      return {button:!!button,dialogOpen:document.querySelector("#appDialog")?.open===true};
    })()`);
    const detailShot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir,"accounting-receipt-detail-headless.png"),Buffer.from(detailShot.data,"base64"));
    const result = await evaluate(`(async () => {
      const button=document.querySelector('[data-finance-detail-action="receipt"]');
      button?.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,40));
      const result={button:!!button,requested:window.__receiptRequests[0]||"",clicked:window.__receiptClicked,dialogOpen:document.querySelector("#appDialog")?.open===true};
      document.querySelector("#appDialog")?.close();
      financeDetailDialog({...window.__receiptItem,id:74,receipt_available:false});
      result.hiddenWithoutReceipt=!document.querySelector('[data-finance-detail-action="receipt"]');
      return result;
    })()`);
    if (!ready.button || !ready.dialogOpen || !result.button || result.requested !== "/api/desktop/accounting/73/receipt/download" || result.clicked?.href !== "blob:receipt-fixture" || result.clicked?.download !== "expense-receipt.pdf" || !result.dialogOpen || !result.hiddenWithoutReceipt || exceptions.length) throw new Error(JSON.stringify({ready,result,exceptions}));
    const screenshot = await send("Page.captureScreenshot", {format:"png", captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir,"accounting-receipt-download-headless.png"),Buffer.from(screenshot.data,"base64"));
    console.log(JSON.stringify({result,exceptions:exceptions.length,headless:true}));
  } finally {
    if (socket) socket.close();
    browser.kill();
  }
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
