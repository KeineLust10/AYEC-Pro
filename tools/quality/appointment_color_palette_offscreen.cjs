const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_APPOINTMENT_COLOR_CDP_PORT || 9243);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const viewportWidth = Number(process.env.AYEC_APPOINTMENT_WIDTH || 1280);
const profile = path.join(outputDir, `appointment-colors-headless-profile-${process.pid}`);

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edge, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--window-size=${viewportWidth},900`, baseUrl,
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
    await send("Emulation.setDeviceMetricsOverride", { width: viewportWidth, height: 900, deviceScaleFactor: 1, mobile: false });
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
      const bounds=document.querySelector('#appDialog').getBoundingClientRect(),before={count:buttons.length,sizes:buttons.map(button=>({width:button.getBoundingClientRect().width,height:button.getBoundingClientRect().height})),colors:buttons.map(button=>button.dataset.appointmentColor),selected:buttons.filter(button=>button.classList.contains('selected')).length,offerHidden:document.querySelector('.appointment-offer-field').hidden,layout:{viewport:innerWidth,dialogWidth:Math.round(bounds.width),dialogLeft:Math.round(bounds.left),dialogRight:Math.round(bounds.right),documentWidth:document.documentElement.scrollWidth}};
      buttons[1].click();
      return {before,selectedColor:document.querySelector('#dialogBody [name="color"]').value,selectedAfter:palette.querySelectorAll('.appointment-color-choice.selected').length,selectedIndex:buttons.findIndex(button=>button.classList.contains('selected')),dialogOpen:document.querySelector('#appDialog').open};
    })()`);
    const colors = state.before.colors;
    const expectedPattern = colors.length === 6 && colors[0] === colors[4] && colors[3] === colors[5];
    if (!state.dialogOpen || state.before.count !== 6 || state.before.sizes.some(size => size.width !== 36 || size.height !== 36) || !expectedPattern || state.before.selected !== 1 || !state.before.offerHidden || state.selectedAfter !== 1 || state.selectedIndex !== 1) throw new Error("Appointment color palette mismatch: " + JSON.stringify(state));
    if (viewportWidth <= 600 && (state.before.layout.dialogLeft < 0 || state.before.layout.dialogRight > viewportWidth || state.before.layout.documentWidth > viewportWidth)) throw new Error("Mobile appointment dialog exceeds viewport: " + JSON.stringify(state.before.layout));
    if (exceptions.length) throw new Error("Browser exceptions: " + JSON.stringify(exceptions));
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "appointment-color-palette-headless.png"), Buffer.from(screenshot.data, "base64"));
    const doubleClick = await evaluate(`(()=>{document.querySelector("#appDialog")?.close("cancel");const date=apDate(new Date());db.appointments=[{id:93,customerId:71,customer_name:"QA Customer",customer:"QA Customer",title:"QA Service",date,time:"14:00",status:"Bekliyor",description:"QA Service"}];page="appointments";document.body.dataset.page=page;render();const card=document.querySelector('.appointment-ref-side-event[data-id="93"]');if(!card)throw new Error("Appointment side card did not render.");card.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));return {dialogOpen:document.querySelector("#appDialog").open,title:document.querySelector("#dialogTitle").textContent,customer:document.querySelector('#dialogBody [name="customerSearch"]').value,idType:typeof db.appointments[0].id,rowIdType:typeof card.dataset.id}})()`);
    if (!doubleClick.dialogOpen || doubleClick.title !== "Randevuyu Düzenle" || doubleClick.customer !== "QA Customer" || doubleClick.idType !== "number" || doubleClick.rowIdType !== "string") throw new Error("Appointment numeric-ID double-click mismatch: " + JSON.stringify(doubleClick));
    const workflow = await evaluate(`(async()=>{
      document.querySelector("#appDialog")?.close("cancel");
      db.customers=[{id:71,name:"QA Customer"},{id:72,name:"Other Customer"}];
      db.personnel=[{id:9,name:"QA Tech"}];
      db.quotes=[{id:88,customerId:71,no:"QA-88",items:[{name:"QA Cable",qty:2,price:25}],total:50},{id:99,customerId:72,no:"OTHER-99",items:[{name:"Other item",qty:1,price:5}],total:5}];
      const originalApiFetch=apiFetch,calls=[];let preparationId=null;
      window.openAppointmentMontagePreparation=id=>{preparationId=id};
      apiFetch=async(path,options={})=>{
        const payload=options.body?JSON.parse(options.body):null;calls.push({path,method:options.method||"GET",payload});
        if(path==="/api/desktop/table/appointments")return{id:901};
        if(path==="/api/desktop/bootstrap")return{customers:[{id:71,name:"QA Customer"}],personnel:[{id:9,name:"QA Tech"}],offers:[{id:88,customerId:71,no:"QA-88",items:[{name:"QA Cable",qty:2,price:25}],total:50}],appointments:[{id:901,customer_id:71,customer_name:"QA Customer",description:"Verilen Teklif / Montaj - Notebook - Replace fan",workflow:"teklif_montaj",status:"Bekliyor"}]};
        return{ok:true};
      };
      try{
        appointmentDialog(null,{date:"2026-10-16",time:"14:00"});
        const form=document.querySelector("#dialogForm"),customerSearch=form.elements.customerSearch,customerId=form.elements.customerId,workflowSelect=form.elements.workflow,offer=form.elements.offerId;
        customerSearch.value="QA Customer";customerSearch.dispatchEvent(new Event("input",{bubbles:true}));
        workflowSelect.value="installation";workflowSelect.dispatchEvent(new Event("change",{bubbles:true}));
        const offerOptions=[...offer.options].map(option=>option.value);offer.value="88";offer.dispatchEvent(new Event("change",{bubbles:true}));
        form.elements.personnel.value="QA Tech";form.elements.device.value="Notebook";form.elements.notes.value="Replace fan";
        document.querySelectorAll("#dialogBody [data-appointment-color]")[2]?.click();
        const beforeSubmit={customerId:customerId.value,offerVisible:!document.querySelector(".appointment-offer-field").hidden,offerOptions,preview:document.querySelector("#appointmentOfferPreview")?.textContent||"",color:form.elements.color.value};
        form.requestSubmit();
        for(let attempt=0;attempt<100&&!calls.some(call=>call.path==="/api/desktop/appointments/montage-plan");attempt++)await new Promise(resolve=>setTimeout(resolve,20));
        return{beforeSubmit,payload:calls.find(call=>call.path==="/api/desktop/table/appointments")?.payload||null,plan:calls.find(call=>call.path==="/api/desktop/appointments/montage-plan")?.payload||null,bootstrap:calls.some(call=>call.path==="/api/desktop/appointments/bootstrap"),preparationId,dialogClosed:!document.querySelector("#appDialog")?.open,calendarTitle:db.appointments.find(item=>String(item.id)==="901")?.title||""};
      }finally{apiFetch=originalApiFetch}
    })()`);
    if (workflow.beforeSubmit.customerId !== "71" || !workflow.beforeSubmit.offerVisible || !workflow.beforeSubmit.offerOptions.includes("88") || workflow.beforeSubmit.offerOptions.includes("99") || !workflow.beforeSubmit.preview.includes("QA Cable") || !workflow.beforeSubmit.color || workflow.payload?.personnel !== "QA Tech" || workflow.payload?.personnel_name !== "QA Tech" || workflow.payload?.device !== "Notebook" || workflow.payload?.notes !== "Replace fan" || workflow.payload?.type !== "Montaj" || workflow.payload?.workflow !== "teklif_montaj" || workflow.payload?.offer_id !== 88 || workflow.payload?.offer_no !== "QA-88" || workflow.payload?.status !== "Bekliyor" || !workflow.bootstrap || workflow.plan?.action !== "prepare" || workflow.plan?.appointment_id !== 901 || workflow.preparationId !== 901 || !workflow.dialogClosed || workflow.calendarTitle !== "Verilen Teklif / Montaj") throw new Error("Appointment installation workflow mismatch: " + JSON.stringify(workflow));
    console.log(JSON.stringify({ ...state, doubleClick, workflow, browserExceptions: exceptions.length, screenshot: "appointment-color-palette-headless.png" }));
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
