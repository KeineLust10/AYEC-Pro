const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `service-print-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const qrPython = [
  "import base64",
  "from reportlab.graphics import renderSVG",
  "from reportlab.graphics.barcode.qr import QrCodeWidget",
  "from reportlab.graphics.shapes import Drawing",
  "from urllib.parse import quote",
  "from Web_Arayuzu.Main import SERVICE_TRACKING_URL, service_tracking_token",
  "target = f'{SERVICE_TRACKING_URL}/{quote(service_tracking_token(\"SRV-QA-204\"), safe=\".\")}'",
  "qr = QrCodeWidget(target)",
  "x1, y1, x2, y2 = qr.getBounds()",
  "side = 96",
  "scale = min(side / max(x2-x1, 1), side / max(y2-y1, 1))",
  "drawing = Drawing(side, side, transform=[scale, 0, 0, scale, -x1*scale, -y1*scale])",
  "drawing.add(qr)",
  "print(base64.b64encode(renderSVG.drawToString(drawing).encode()).decode())"
].join("\n");
const qrDataUrl = `data:image/svg+xml;base64,${execFileSync("python", ["-c", qrPython], {encoding:"utf8"}).trim()}`;

async function findPage() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const page = (await response.json()).find(item => item.type === "page" && item.url?.startsWith(new URL(baseUrl).origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await findPage();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
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
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof renderServiceListReference === 'function' && typeof openServiceBulkPrint === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("The service-list print module did not load.");
    const result = await evaluate(`(async()=>{
      const NativeDate = Date;
      window.Date = class extends NativeDate { constructor(...args) { super(...(args.length ? args : ["2026-10-17T22:55:00"])); } static now() { return new NativeDate("2026-10-17T22:55:00").valueOf(); } };
      hideAuth();
      currentAuthUser={username:"QA Admin",role:"Admin",permissions:JSON.stringify({mode:"all"})};
      updateCurrentUser(currentAuthUser);
      applicationStarted=true;
      db.settings={...db.settings,company_name:"QA SERVICE CENTER",company_address:"Workshop Road 10",company_phone:"5551234567",company_email:"qa@example.test",company_website:"https://example.test",service_terms:"Retain the signed service receipt for warranty claims.",print_document_page_size:"A5",print_document_orientation:"landscape"};
      db.customers=[{id:41,name:"Aylin Example",company:"Example Ltd",phone:"5551002000",phone2:"5551002001",address:"Customer Avenue 5",email:"customer@example.test",services:[{id:93,no:"SRV-QA-204",customer_id:41,customer_name:"Aylin Example",customer_contact:"5551002000",customer_address:"Customer Avenue 5",device:"Laptop Model Z",brand:"Acme",model:"Z",device_type:"Laptop",serial:"SN-204",serial_no:"SN-204",entry_date:"2026-10-16",estimated_date:"2026-10-20",status:"Tamirde",delivery_method:"Elden",reported_fault:"Screen flickers",fault_description:"Screen flickers",repair_notes:"Replaced display cable",repair_details:"Replaced display cable",technician:"QA Tech",created_by:"QA Reception",delivered_by_name:"QA Handover",delivered_by_phone:"5553004000",labor_cost:25,used_parts:[{part_name:"Display cable",quantity:2,line_total:50},{part_name:"Connector",quantity:1,unit_price:50}],amount:125,currency:"TRY",payment_status:"Beklemede"}]}];
      ayecServiceListState.date="all";
      page="service-list";
      render();
      const rowButton=document.querySelector('[data-service-command="row-print"]');
      if(!rowButton)throw new Error("The service row print action is missing.");
      rowButton.click();
      const detailed=document.querySelector('[data-print-choice="detailed"]');
      if(!detailed)throw new Error("The detailed receipt choice is missing.");
      detailed.click();
      const dialog=document.querySelector("#appDialog");
      const slip=dialog?.querySelector(".service-bulk-slip");
      if(!dialog?.open||!slip)throw new Error("The detailed service receipt did not open.");
      const text=slip.innerText;
      const qr=slip.querySelector(".service-receipt-qr img");
      const checks={
        selected_record: text.includes("SRV-QA-204"),
        company_contact: text.includes("QA SERVICE CENTER")&&text.includes("Workshop Road 10")&&text.includes("qa@example.test"),
        customer_contact: text.includes("5551002000")&&!text.includes("Customer Avenue 5"),
        service_detail: text.includes("Acme Z")&&text.includes("Screen flickers")&&text.includes("Replaced display cable")&&text.includes("QA Handover"),
        parts_and_labor: text.includes("Display cable")&&text.includes("Connector")&&text.includes("SERVIS ISCILIK"),
        total: slip.querySelector(".service-receipt-total")?.innerText.includes("125"),
        terms_and_signatures: text.includes("Retain the signed service receipt")&&text.includes("TESLIM EDEN IMZASI")&&text.includes("SERVIS YETKILISI"),
        tracking_qr_binding: qr?.getAttribute("src").includes("/api/desktop/service-tracking/qr?tracking_no=SRV-QA-204"),
        print_page_settings: dialog.querySelector("style")?.textContent.includes("210mm 148mm")
      };
      const qrSource=qr?.getAttribute("src");
      qr.src=${JSON.stringify(qrDataUrl)};
      await new Promise(resolve=>{if(qr.complete)return resolve();qr.onload=resolve;qr.onerror=resolve;setTimeout(resolve,500)});
      checks.tracking_qr_rendered=qr.naturalWidth>0&&qr.naturalHeight>0;
      return {checks,text,qrSource};
    })()`);
    if (Object.values(result.checks).some(value => !value) || exceptions.length) throw new Error(`Service receipt mismatch: ${JSON.stringify({ result, exceptions })}`);
    await delay(200);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const screenshotPath = path.join(outputDir, "service-detailed-receipt-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const printFit = await evaluate(`(()=>{const dialog=document.querySelector("#appDialog");if(typeof dialog?.__fitServiceReceiptToPage!=="function"||typeof dialog?.__prepareServiceReceiptPrint!=="function")throw new Error("Print preparation handlers are missing.");dialog.__fitServiceReceiptToPage();const fit=Array.from(dialog.querySelectorAll(".service-bulk-slip"),slip=>Number(slip.style.zoom));dialog.__prepareServiceReceiptPrint();return fit})()`);
    await send("Emulation.setEmulatedMedia", { media: "print" });
    const printMetrics = await evaluate(`(()=>{const root=document.querySelector("#serviceReceiptPrintRoot"),slip=root?.querySelector(".service-bulk-slip"),style=node=>node?{display:getComputedStyle(node).display,background:getComputedStyle(node).backgroundColor,backgroundImage:getComputedStyle(node).backgroundImage,rect:(()=>{const r=node.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}})()}:null;const info=slip?.querySelector(".service-receipt-info");const cells=[...(info?.querySelectorAll("dt,dd")||[])].map(node=>{const r=node.getBoundingClientRect();return{tag:node.tagName,text:node.textContent.trim(),rect:{x:r.x,y:r.y,width:r.width,height:r.height}}});return{html:style(document.documentElement),body:style(document.body),appShell:style(document.querySelector("#appShell")),dialog:style(document.querySelector("#appDialog")),printRoot:style(root),slip:style(slip),receiptInfo:{grid:getComputedStyle(info).gridTemplateColumns,cells}}})()`);
    const printedPdf = await send("Page.printToPDF", { printBackground: true, preferCSSPageSize: true, displayHeaderFooter: false });
    const pdfPath = path.join(outputDir, "service-detailed-receipt-web.pdf");
    fs.writeFileSync(pdfPath, Buffer.from(printedPdf.data, "base64"));
    execFileSync("python", [path.join(__dirname, "service_receipt_desktop_reference.py")], {stdio:"ignore"});
    const desktopPdfPath = path.join(outputDir, "service-detailed-receipt-desktop.pdf");
    const compareCode = `import json,pypdfium2 as p,numpy as np; docs=[p.PdfDocument(${JSON.stringify(desktopPdfPath)}),p.PdfDocument(${JSON.stringify(pdfPath)})]; pages=[len(d) for d in docs]; sizes=[list(d[0].get_size()) for d in docs]; corners=[[list(d[0].render(scale=1).to_pil().convert("RGB").getpixel(pt)) for pt in [(0,0),(d[0].render(scale=1).to_pil().width-1,0),(0,d[0].render(scale=1).to_pil().height-1),(d[0].render(scale=1).to_pil().width-1,d[0].render(scale=1).to_pil().height-1)]] for d in docs]; images=[np.asarray(d[0].render(scale=1.5).to_pil().convert("RGB"),dtype=np.int16) for d in docs]; diff=np.abs(images[0]-images[1]); visual={"render_size":list(images[0].shape[:2]),"mae":round(float(diff.mean()),3),"exact_pixel_percent":round(float((diff.max(axis=2)==0).mean()*100),2),"p95_delta":int(np.percentile(diff,95))}; print(json.dumps({"pages":pages,"sizes":sizes,"corners":corners,"visual":visual}))`;
    const pdfComparison = JSON.parse(execFileSync("python", ["-c", compareCode], {encoding:"utf8"}).trim());
    const pdfPages = pdfComparison.pages[1];
    const samePageSize = pdfComparison.sizes[0].every((value,index)=>Math.abs(value-pdfComparison.sizes[1][index])<0.5);
    const whiteCorners = pdfComparison.corners.every(page=>page.every(pixel=>pixel.every(channel=>channel===255)));
    if (pdfPages !== 1 || pdfComparison.pages[0] !== 1 || !samePageSize || !whiteCorners || pdfComparison.visual.mae >= 13.1) throw new Error(`Detailed receipt PDF comparison failed: ${JSON.stringify(pdfComparison)}`);
    await evaluate(`document.querySelector("#appDialog")?.__cleanupServiceReceiptPrint(document.querySelector("#serviceReceiptPrintRoot"))`);
    const printDialogRestored = await evaluate(`(()=>{const dialog=document.querySelector("#appDialog");window.print=()=>{};document.querySelector("#serviceBulkPrintAction")?.click();const restored=dialog?.open&&!document.querySelector("#serviceReceiptPrintRoot");if(dialog?.open)dialog.close();return restored})()`);
    if (!printDialogRestored) throw new Error("The detailed receipt dialog did not return after printing.");
    process.stdout.write(`${JSON.stringify({ ...result, printFit, printMetrics, pdfPages, pdfComparison, exceptions, screenshot: screenshotPath, pdf: pdfPath })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    await delay(300);
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
