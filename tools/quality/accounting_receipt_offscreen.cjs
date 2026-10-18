const { spawn, execFileSync } = require("node:child_process");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 9253);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-accounting-receipt-edge-"));
const profile = path.join(tempRoot, "profile");
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
      if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
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
      const customer={id:17,name:"QA Customer",phone:"5550000017",balances:{TRY:0,USD:0,EUR:0},services:[{id:220,no:"SRV-TEST-73",device:"Fixture device",status:"Teslim Edildi",repair_details:"Screen replaced\\nPort cleaned",labor_cost:30,cargo_fee:5,used_parts:[{part_name:"LCD Panel",quantity:2,price:10,currency:"TRY"}]}],quotes:[]};
      db.customers=[customer]; db.finance=[];
      const item={id:73,source:"accounting",receipt_available:true,type_label:"Gider",type:"Wrong type fallback",description:"Fixture <receipt> | Ref: SRV-TEST-73",tracking_no:"SRV-TEST-73",customer_id:17,customer_name:"QA <Customer>",customer:"Wrong customer fallback",operator_name:"Fixture Operator",timestamp:"2026-10-17 10:00",date:"2026-10-17",created_at:"Wrong date fallback",amount:999,amount_try:73,currency:"TRY"};
      window.__receiptItem=item;
      ayecFinanceLedgerItems=[item]; db.finance=[];
      window.__receiptRequests=[]; window.__receiptClicked=null;
      window.__copiedTracking="";
      Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async value=>{window.__copiedTracking=String(value)}}});
      fetch=async url=>{window.__receiptRequests.push(String(url));return {ok:true,headers:{get:()=>"attachment; filename*=UTF-8''expense-receipt.pdf"},blob:async()=>new Blob(["fixture"])};};
      URL.createObjectURL=()=>"blob:receipt-fixture"; URL.revokeObjectURL=()=>{};
      HTMLAnchorElement.prototype.click=function(){window.__receiptClicked={href:this.href,download:this.download}};
      financeDetailDialog(item);
      const button=document.querySelector('[data-finance-detail-action="receipt"]');
      const receiptPrintButton=document.querySelector('[data-finance-detail-action="receipt-print"]');
      const customerButton=document.querySelector('[data-finance-detail-action="customer360"]');
      const copyButton=document.querySelector('[data-finance-detail-action="copy-tracking"]');
      const serviceButton=document.querySelector('[data-finance-detail-action="service-form"]');
      const serviceLineRows=[...document.querySelectorAll(".finance-detail-lines tbody tr")].map(row=>row.textContent.trim());
      const detailLogLines=[...document.querySelectorAll(".finance-detail-notes .finance-detail-log p")].map(node=>node.textContent);
      const detailFooter=document.querySelector(".finance-detail-notes footer")?.textContent||"";
      return {button:!!button,receiptPrintButton:!!receiptPrintButton,customerButton:!!customerButton,copyButton:!!copyButton,serviceButton:!!serviceButton,serviceLineRows,detailLogLines,detailFooter,dialogOpen:document.querySelector("#appDialog")?.open===true};
    })()`);
    const detailShot=await send("Page.captureScreenshot",{format:"png",captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir,"accounting-receipt-detail-headless.png"),Buffer.from(detailShot.data,"base64"));
    const result = await evaluate(`(async () => {
      document.querySelector('[data-finance-detail-action="copy-tracking"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,20));
      const copiedTracking=window.__copiedTracking;
      document.querySelector('[data-finance-detail-action="service-form"]')?.click();
      const serviceForm={visible:document.querySelector("#appDialog")?.classList.contains("service-print-dialog")||false,title:document.querySelector("#dialogTitle")?.textContent||""};
      document.querySelector("#appDialog")?.close();
      financeDetailDialog(window.__receiptItem);
      document.querySelector('[data-finance-detail-action="customer360"]')?.click();
      const customer360={visible:document.querySelector("#appDialog")?.classList.contains("c360-dialog")||false,title:document.querySelector("#dialogTitle")?.textContent||""};
      document.querySelector("#appDialog")?.close();
      financeDetailDialog(window.__receiptItem);
      document.querySelector('[data-finance-detail-action="receipt-print"]')?.click();
      await new Promise(resolve=>setTimeout(resolve,25));
      const receiptMarkup=document.querySelector('iframe[aria-hidden="true"]')?.srcdoc||"";
      printFinanceTransactionReceipt({...window.__receiptItem,id:74,currency:"USD",amount:123,amount_try:999});
      await new Promise(resolve=>setTimeout(resolve,25));
      const foreignReceiptMarkup=[...document.querySelectorAll('iframe[aria-hidden="true"]')].at(-1)?.srcdoc||"";
      const printedReceipt={title:receiptMarkup.includes("AYEC Pro - Islem Makbuzu"),record:receiptMarkup.includes("Kayit: 73"),date:receiptMarkup.includes("Tarih: 2026-10-17")&&!receiptMarkup.includes("Wrong date fallback"),type:receiptMarkup.includes("Tur: Gider")&&!receiptMarkup.includes("Wrong type fallback"),customerEscaped:receiptMarkup.includes("QA &lt;Customer&gt;")&&!receiptMarkup.includes("Wrong customer fallback"),amount:receiptMarkup.includes("Tutar: "+money(73,"TRY"))&&!receiptMarkup.includes("Tutar: "+money(999,"TRY")),foreignAmount:foreignReceiptMarkup.includes("Tutar: "+money(123,"USD"))&&!foreignReceiptMarkup.includes("Tutar: "+money(999,"USD")),descriptionEscaped:receiptMarkup.includes("Fixture &lt;receipt&gt;"),plainDesktopRows:receiptMarkup.includes("Kayit: 73<br>Tarih: 2026-10-17")&&!receiptMarkup.includes("<h1>"),nativeTypography:receiptMarkup.includes('@page{size:A4;margin:0}body{font:9pt Inter,"Segoe UI",Arial,sans-serif;margin:4px')};
      const button=document.querySelector('[data-finance-detail-action="receipt"]');
      button?.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,40));
      const result={button:!!button,requested:window.__receiptRequests[0]||"",clicked:window.__receiptClicked,dialogOpen:document.querySelector("#appDialog")?.open===true};
      document.querySelector("#appDialog")?.close();
      financeDetailDialog({...window.__receiptItem,id:74,receipt_available:false});
      result.hiddenWithoutReceipt=!document.querySelector('[data-finance-detail-action="receipt"]');
      const fallbackItem={...window.__receiptItem,id:75,receipt_available:false,tracking_no:"",ref_no:"",customer_id:null,description:"Fixture | Ref: SRV-REF-75"};
      ayecFinanceLedgerItems=[fallbackItem];
      financeDetailDialog(fallbackItem);
      const fallbackCopyButton=document.querySelector('[data-finance-detail-action="copy-tracking"]');
      const noCustomerButton=!document.querySelector('[data-finance-detail-action="customer360"]');
      fallbackCopyButton?.click();
      await new Promise(resolve=>setTimeout(resolve,20));
      result.descriptionTrackingFallback=window.__copiedTracking==="SRV-REF-75";
      result.customerActionHiddenWithoutCustomer=noCustomerButton;
      document.querySelector("#appDialog")?.close();
      const selectedItem={...window.__receiptItem,id:76,receipt_available:false,tracking_no:"",ref_no:"",customer_id:null,description:"Selected service fallback",selected_services:[{name:"Fixture SSD",sku:"SSD-01",quantity:2,unit_price:10,currency:"TRY"}]};
      ayecFinanceLedgerItems=[selectedItem];
      financeDetailDialog(selectedItem);
      result.selectedServiceRows=[...document.querySelectorAll(".finance-detail-lines tbody tr")].map(row=>row.textContent.trim());
      document.querySelector("#appDialog")?.close();
      const relatedItem={...window.__receiptItem,id:77,receipt_available:false,tracking_no:"",ref_no:"REF-RELATED",customer_id:null,description:"Related part (x2) - 123,45",selected_services:[]};
      const currentItem={...window.__receiptItem,id:78,receipt_available:false,tracking_no:"",ref_no:"REF-RELATED",customer_id:null,description:"Current transaction",selected_services:[]};
      ayecFinanceLedgerItems=[relatedItem,currentItem];
      financeDetailDialog(currentItem);
      result.relatedDescriptionRows=[...document.querySelectorAll(".finance-detail-lines tbody tr")].map(row=>row.textContent.trim());
      document.querySelector("#appDialog")?.close();
      result.printedReceipt=printedReceipt;
      result.customer360=customer360;
      result.serviceForm=serviceForm;
      result.copiedTracking=copiedTracking;
      return result;
    })()`);
    const serviceRowsMatch=ready.serviceLineRows.length===5&&ready.serviceLineRows.some(row=>row.includes("Screen replaced"))&&ready.serviceLineRows.some(row=>row.includes("Port cleaned"))&&ready.serviceLineRows.some(row=>row.includes("LCD Panel"))&&ready.serviceLineRows.some(row=>row.includes("Kargo"))&&ready.serviceLineRows.some(row=>row.includes("30"));
    const serviceDescriptionMatch=ready.detailLogLines[0]?.includes("Screen replaced")&&ready.detailLogLines[0]?.includes("Port cleaned")&&ready.detailLogLines[1]?.includes("Fixture <receipt>")&&ready.detailFooter.includes("Fixture Operator")&&ready.detailFooter.includes("2026-10-17 10:00");
    const selectedRowsMatch=result.selectedServiceRows.length===1&&result.selectedServiceRows[0].includes("Fixture SSD")&&result.selectedServiceRows[0].includes("SSD-01")&&result.selectedServiceRows[0].includes("20");
    const relatedRowsMatch=result.relatedDescriptionRows.length===1&&result.relatedDescriptionRows[0].includes("Related part")&&result.relatedDescriptionRows[0].includes("123,45")&&result.relatedDescriptionRows[0].includes("—");
    if (!ready.button || !ready.receiptPrintButton || !ready.customerButton || !ready.copyButton || !ready.serviceButton || !serviceRowsMatch || !serviceDescriptionMatch || !selectedRowsMatch || !relatedRowsMatch || !ready.dialogOpen || result.copiedTracking !== "SRV-TEST-73" || !result.serviceForm.visible || !result.serviceForm.title.includes("SRV-TEST-73") || !result.descriptionTrackingFallback || !result.customerActionHiddenWithoutCustomer || !result.customer360.visible || result.customer360.title !== "QA Customer" || Object.values(result.printedReceipt).some(value=>!value) || !result.button || result.requested !== "/api/desktop/accounting/73/receipt/download" || result.clicked?.href !== "blob:receipt-fixture" || result.clicked?.download !== "expense-receipt.pdf" || !result.dialogOpen || !result.hiddenWithoutReceipt || exceptions.length) throw new Error(JSON.stringify({ready,result,exceptions}));
    const screenshot = await send("Page.captureScreenshot", {format:"png", captureBeyondViewport:true});
    fs.writeFileSync(path.join(outDir,"accounting-receipt-download-headless.png"),Buffer.from(screenshot.data,"base64"));
    console.log(JSON.stringify({result,exceptions:exceptions.length,headless:true}));
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) { browser.kill(); }
    await delay(300);
    if (path.dirname(profile) === tempRoot && path.basename(profile) === "profile" && path.dirname(tempRoot) === path.resolve(os.tmpdir()) && path.basename(tempRoot).startsWith("ayec-accounting-receipt-edge-")) {
      try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (_) {}
    }
  }
}
run().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
