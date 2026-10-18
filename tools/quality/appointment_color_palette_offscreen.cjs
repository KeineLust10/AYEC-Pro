const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_APPOINTMENT_COLOR_CDP_PORT || 9243);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `appointment-colors-headless-profile-${process.pid}`);

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
      ready = await evaluate("document.readyState === 'complete' && typeof appointmentDialog === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    const state = await evaluate(`(()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      db.customers=[{id:71,name:'QA Customer'}];db.personnel=[{name:'QA Tech'}];db.quotes=[];
      appointmentDialog(null,{date:'2026-10-16',time:'14:00'});
      const palette=document.querySelector('.appointment-color-palette'),buttons=[...palette.querySelectorAll('.appointment-color-choice')];
      const before={count:buttons.length,sizes:buttons.map(button=>({width:button.getBoundingClientRect().width,height:button.getBoundingClientRect().height})),colors:buttons.map(button=>button.dataset.appointmentColor),selected:buttons.filter(button=>button.classList.contains('selected')).length,offerHidden:document.querySelector('.appointment-offer-field').hidden};
      buttons[1].click();
      return {before,selectedColor:document.querySelector('#dialogBody [name="color"]').value,selectedAfter:palette.querySelectorAll('.appointment-color-choice.selected').length,selectedIndex:buttons.findIndex(button=>button.classList.contains('selected')),dialogOpen:document.querySelector('#appDialog').open};
    })()`);
    const colors = state.before.colors;
    const expectedPattern = colors.length === 6 && colors[0] === colors[4] && colors[3] === colors[5];
    if (!state.dialogOpen || state.before.count !== 6 || state.before.sizes.some(size => size.width !== 36 || size.height !== 36) || !expectedPattern || state.before.selected !== 1 || !state.before.offerHidden || state.selectedAfter !== 1 || state.selectedIndex !== 1) throw new Error("Appointment color palette mismatch: " + JSON.stringify(state));
    if (exceptions.length) throw new Error("Browser exceptions: " + JSON.stringify(exceptions));
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "appointment-color-palette-headless.png"), Buffer.from(screenshot.data, "base64"));
    const doubleClick = await evaluate(`(()=>{document.querySelector("#appDialog")?.close("cancel");const date=apDate(new Date());db.appointments=[{id:93,customerId:71,customer_name:"QA Customer",customer:"QA Customer",title:"QA Service",date,time:"14:00",status:"Bekliyor",description:"QA Service"}];page="appointments";document.body.dataset.page=page;render();const card=document.querySelector('.appointment-ref-side-event[data-id="93"]');if(!card)throw new Error("Appointment side card did not render.");card.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));return {dialogOpen:document.querySelector("#appDialog").open,title:document.querySelector("#dialogTitle").textContent,customer:document.querySelector('#dialogBody [name="customerSearch"]').value,idType:typeof db.appointments[0].id,rowIdType:typeof card.dataset.id}})()`);
    if (!doubleClick.dialogOpen || doubleClick.title !== "Randevuyu Düzenle" || doubleClick.customer !== "QA Customer" || doubleClick.idType !== "number" || doubleClick.rowIdType !== "string") throw new Error("Appointment numeric-ID double-click mismatch: " + JSON.stringify(doubleClick));
    console.log(JSON.stringify({ ...state, doubleClick, browserExceptions: exceptions.length, screenshot: "appointment-color-palette-headless.png" }));
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
