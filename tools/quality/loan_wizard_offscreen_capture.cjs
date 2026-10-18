const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_LOAN_AUDIT_URL || "http://127.0.0.1:8853/";
const outputPath = path.resolve(process.env.AYEC_LOAN_AUDIT_SCREENSHOT || "output/playwright/loan-wizard-documents-current-headless.png");
const debugPort = Number(process.env.AYEC_LOAN_AUDIT_CDP_PORT || (9300 + process.pid % 500));
const profile = path.join(path.dirname(outputPath), `loan-wizard-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1360,900", "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  const pending = new Map();
  let nextId = 0;
  const exceptions = [];
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
        target = (await response.json()).find(item => item.type === "page");
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless browser target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.result?.description || "No details."}`);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1360, height: 900, deviceScaleFactor: 1, mobile: false });
    await send("Page.navigate", { url: baseUrl });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof openAdvancedLoanWizardManifestDialog === 'function'");
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("The loan wizard runtime did not initialize.");
    const prepared = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      apiFetch = async path => path === "/api/desktop/banks/catalog" ? { banks: [{ name: "QA Bank", shortName: "QA" }], document_upload_enabled: true, currency: "EUR" } : {};
      openAdvancedLoanWizardManifestDialog();
      for (let attempt = 0; attempt < 60; attempt += 1) {
        if (document.querySelector("#dialogForm") && document.querySelector("#dialogSubmit")) break;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      return Boolean(document.querySelector('#dialogForm [name="loan_title"]'));
    })()`);
    if (!prepared) throw new Error("The initial loan form did not open.");
    const captureStep = async name => {
      const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: true });
      const target = name === "documents" ? outputPath : path.join(path.dirname(outputPath), `loan-wizard-${name}-matched-headless.png`);
      fs.writeFileSync(target, Buffer.from(screenshot.data, "base64"));
      return target;
    };
    const stepScreenshots = { general: await captureStep("general") };
    const stepGeometry = {};
    stepGeometry.general = await evaluate(`(() => {const box=selector=>{const e=document.querySelector(selector),r=e?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{heading:box(".loan-wizard-general .loan-wizard-step-heading"),bank:box('#dialogForm [name="bank_index"]'),loanType:box('#dialogForm [name="loan_type"]'),title:box('#dialogForm [name="loan_title"]'),eft:box(".loan-wizard-general .field:nth-child(4) input"),swift:box(".loan-wizard-general .field:nth-child(5) input")}})()`);
    await evaluate(`(async () => { document.querySelector('#dialogForm [name="loan_title"]').value = "QA Loan"; document.querySelector("#dialogSubmit").click(); await new Promise(resolve => setTimeout(resolve, 250)); return true; })()`);
    stepScreenshots.finance = await captureStep("finance");
    stepGeometry.finance = await evaluate(`(() => {const box=selector=>{const e=document.querySelector(selector),r=e?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{principal:box('#dialogForm [name="principal"]'),interest:box('#dialogForm [name="interest_rate"]'),months:box('#dialogForm [name="term_months"]'),date:box('#dialogForm [name="start_date"]'),kkdf:box('#dialogForm [name="kkdf_rate"]'),bsmv:box('#dialogForm [name="bsmv_rate"]'),preview:box(".loan-wizard-preview")}})()`);
    const financeDefaults = await evaluate(`(() => {const field=document.querySelector('#dialogForm [name="start_date"]'),now=new Date(),day=now.getDate(),next=new Date(now);next.setDate(1);next.setMonth(next.getMonth()+1);next.setDate(Math.min(day,new Date(next.getFullYear(),next.getMonth()+1,0).getDate()));const pad=value=>String(value).padStart(2,"0");return{date:field?.value||"",label:field?.closest(".field")?.querySelector("label")?.textContent.trim()||"",expected:[next.getFullYear(),pad(next.getMonth()+1),pad(next.getDate())].join("-")}})()`);
    if (financeDefaults.date !== financeDefaults.expected || !financeDefaults.label.includes("\u0130lk \u00d6deme Tarihi")) throw new Error(`Native first-payment defaults did not match: ${JSON.stringify(financeDefaults)}`);
    await evaluate(`(async () => { document.querySelector("#dialogSubmit").click(); await new Promise(resolve => setTimeout(resolve, 250)); return true; })()`);
    stepScreenshots.documents = await captureStep("documents");
    const workflow = await evaluate(`(() => {
      const dialog=document.querySelector("#appDialog"),rect=dialog?.getBoundingClientRect();
      const box=selector=>{const element=document.querySelector(selector),r=element?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};
      return {open:Boolean(dialog?.open),classes:dialog?.className||"",bounds:rect?[Math.round(rect.x),Math.round(rect.y),Math.round(rect.width),Math.round(rect.height)]:null,step:"",heading:document.querySelector(".loan-wizard-document-heading h2")?.textContent||"",bodyText:document.querySelector("#dialogBody")?.innerText.slice(0,100)||"",content:box(".loan-wizard-documents"),contract:box(".loan-document-zones .loan-document-zone:first-child"),paymentPlan:box(".loan-document-zones .loan-document-zone:nth-child(2)"),notes:box(".loan-document-zones .field"),notesLabel:box(".loan-document-zones .field>label"),notesInput:box(".loan-document-zones .field>textarea"),fileList:box(".loan-document-list"),back:box("#dialogCancel"),next:box("#dialogSubmit"),footer:box("#dialogFooter"),exceptionCount:0};
    })()`);
    if (workflow.error) throw new Error(JSON.stringify(workflow));
    const near=(actual,expected,tolerance=2)=>Array.isArray(actual)&&actual.length===expected.length&&actual.every((value,index)=>Math.abs(value-expected[index])<=tolerance);
    const general=stepGeometry.general,finance=stepGeometry.finance;
    const relative=(box)=>box?.map((value,index)=>value-(index===0?workflow.bounds[0]:index===1?workflow.bounds[1]:0));
    if(!near(relative(general.bank),[234,213,1040,40],3)||!near(relative(general.loanType),[234,268,1040,40],3)||!near(relative(general.title),[234,323,1040,40],3)||!near(relative(general.eft),[234,378,1040,40],3)||!near(relative(general.swift),[234,433,1040,40],3)) throw new Error(`General step geometry did not match: ${JSON.stringify(general)}`);
    if(!near(relative(finance.principal),[264,252,392,63],3)||!near(relative(finance.interest),[264,330,177,60],3)||!near(relative(finance.months),[264,405,392,63],3)||!near(relative(finance.date),[264,483,392,40],3)||!near(relative(finance.kkdf),[264,538,392,63],3)||!near(relative(finance.bsmv),[264,616,392,63],3)||!near(relative(finance.preview),[686,102,588,606],3)) throw new Error(`Finance step geometry did not match: ${JSON.stringify(finance)}`);
    if (!workflow.open || !workflow.classes.includes("loan-wizard-dialog") || !workflow.heading.includes("Evrak Y\u00fckleme") || workflow.bounds?.[2] !== 1320 || workflow.bounds?.[3] !== 820 || workflow.back?.[2] !== 120 || workflow.next?.[2] !== 140 || workflow.notesInput?.[0] - workflow.bounds?.[0] !== 43 || workflow.notesInput?.[1] - workflow.bounds?.[1] !== 636 || workflow.notesInput?.[2] !== 607 || workflow.notesInput?.[3] !== 72) throw new Error(`The document step or desktop geometry did not match: ${JSON.stringify(workflow)}`);
    await evaluate(`(async () => { document.querySelector("#dialogSubmit").click(); await new Promise(resolve => setTimeout(resolve, 250)); return true; })()`);
    stepScreenshots.summary = await captureStep("summary");
    stepGeometry.summary = await evaluate(`(() => {const box=selector=>{const e=document.querySelector(selector),r=e?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{heading:box(".loan-wizard-summary .loan-wizard-step-heading"),bankCard:box(".loan-wizard-summary article:nth-of-type(1)"),financeCard:box(".loan-wizard-summary article:nth-of-type(2)"),extrasCard:box(".loan-wizard-summary article:nth-of-type(3)"),table:box(".loan-installment-table"),rowCount:document.querySelectorAll(".loan-installment-table tbody tr").length,columnCount:document.querySelectorAll(".loan-installment-table thead th").length}})()`);
    const summary=stepGeometry.summary;
    if(!near(relative(summary.bankCard),[32,126,621,175],4)||!near(relative(summary.financeCard),[663,126,621,175],4)||!near(relative(summary.extrasCard),[32,311,1252,115],4)||!near(relative(summary.table),[32,508,1252,220],4)||summary.rowCount!==36||summary.columnCount!==5) throw new Error(`Summary step geometry or installment table did not match: ${JSON.stringify(summary)}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(JSON.stringify({ ...workflow, financeDefaults, stepGeometry, browserExceptions: exceptions.length, screenshots: stepScreenshots }) + "\n");
  } finally {
    try { socket?.send(JSON.stringify({ id: 99999, method: "Browser.close" })); } catch (_) {}
    try { socket?.close(); } catch (_) {}
    if (browser.exitCode === null) browser.kill();
  }
}

run().catch(error => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
