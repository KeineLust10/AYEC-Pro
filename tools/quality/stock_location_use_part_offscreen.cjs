const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_STOCK_USE_PART_CDP_PORT || 9245);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `stock-use-part-headless-profile-${process.pid}`);

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edge, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl,
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/json`);
        target = (await response.json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
        if (target) break;
      } catch (_) {}
      await new Promise(resolve => setTimeout(resolve, 200));
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
      const call = pending.get(message.id);
      if (!call) return;
      pending.delete(message.id);
      if (message.error) call.reject(new Error(message.error.message));
      else call.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      if (result.result?.subtype === "error") throw new Error(result.result.description);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof stockLocationUsePartDialog === 'function' && typeof hydrateDesktop === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    const state = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      const requests=[],source={customers:[{id:71,name:'Linked Customer',services:[{no:'SRV-CUSTOMER',device:'Laptop',status:'Bekliyor'}]}],devices:[
        {id:1,tracking_no:'SRV-LINKED',customer_id:71,customer_name:'Linked Customer',device_brand:'Brand',device_model:'Model',status:'Repair',is_archived:0,is_deleted:0},
        {id:2,tracking_no:'SRV-UNLINKED',customer_id:null,customer_name:'',device_brand:'',device_model:'Loose Device',status:'Waiting',is_archived:0,is_deleted:0},
        {id:3,tracking_no:'SRV-ARCHIVED',customer_id:71,customer_name:'Linked Customer',device_model:'Archived',status:'Archived',is_archived:1,is_deleted:0},
        {id:4,tracking_no:'SRV-DELETED',customer_id:71,customer_name:'Linked Customer',device_model:'Deleted',status:'Deleted',is_archived:0,is_deleted:1}],stock:[{id:13,name:'QA Part',unit:'Adet',stock:5}],stock_locations:[{id:8,name:'QA Warehouse',location_type:'warehouse'}],stock_location_balances:[{part_id:13,location_id:8,product_name:'QA Part',quantity:5,reserved_quantity:1,unit:'Adet'}],stock_transfer_history:[],stock_counts:[],stock_kits:[],movements:[],finance:[],personnel:[],appointments:[],offers:[],exchange_rates:{},settings:{},internal_settings:{}};
      window.fetch=async(url,options={})=>{requests.push({url:String(url),method:options.method||'GET',body:options.body||null});const payload=String(url)==='/api/desktop/bootstrap'?source:{ok:true,rows:[],count:0};return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}})};
      await hydrateDesktop(true);
      const mapped={devices:db.serviceDevices.map(item=>({no:item.no,customerName:item.customerName,device:item.device,status:item.status}))};
      stockLocationUsePartDialog({id:'13',name:'QA Part'},'8');
      const dialog=document.querySelector('#appDialog'),selector=dialog.querySelector('[name="tracking_no"]'),quantity=dialog.querySelector('[name="quantity"]');
      const initial={dialogOpen:dialog.open,options:[...selector.options].map(option=>({value:option.value,text:option.textContent})),unitStep:quantity.step,unitMin:quantity.min,unitMax:quantity.max,available:dialog.querySelector('input[disabled][value="4"]')!==null};
      selector.value='SRV-UNLINKED';quantity.value='2';dialog.querySelector('[name="note"]').value='Installed from stock';dialog.querySelector('#dialogSubmit').click();await new Promise(resolve=>setTimeout(resolve,180));
      const write=requests.map(item=>item.body?JSON.parse(item.body):null).find(body=>body?.action==='use-part');
      db.stockLocationBalances[0].unit='Kg';stockLocationUsePartDialog({id:'13',name:'QA Part'},'8');
      const fraction=dialog.querySelector('[name="quantity"]'),fractional={step:fraction.step,min:fraction.min,max:fraction.max};
      return {mapped,initial,write,fractional,requestCount:requests.length};
    })()`);
    const values = state.initial.options.map(option => option.value);
    if (state.mapped.devices.length !== 2 || !values.includes("SRV-UNLINKED") || values.includes("SRV-ARCHIVED") || values.includes("SRV-DELETED") || state.initial.unitStep !== "1" || state.initial.unitMin !== "1" || state.initial.unitMax !== "4" || !state.initial.available) throw new Error("Use-part device list or integer quantity mismatch: " + JSON.stringify(state));
    if (state.write?.action !== "use-part" || state.write.tracking_no !== "SRV-UNLINKED" || state.write.quantity !== 2 || state.write.note !== "Installed from stock") throw new Error("Use-part write mismatch: " + JSON.stringify(state.write));
    if (state.fractional.step !== "0.001" || state.fractional.min !== "0.001" || state.fractional.max !== "4") throw new Error("Fractional quantity mismatch: " + JSON.stringify(state.fractional));
    if (exceptions.length) throw new Error("Browser exceptions: " + JSON.stringify(exceptions));
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "stock-location-use-part-headless.png"), Buffer.from(screenshot.data, "base64"));
    console.log(JSON.stringify({ ...state, browserExceptions: exceptions.length, screenshot: "stock-location-use-part-headless.png" }));
    await send("Browser.close");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) socket.close();
    browser.kill();
  }
}

run().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
