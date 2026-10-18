const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_AUDIT_CDP_PORT || 36000 + (process.pid % 9000));
const url = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8865/";
const output = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(output, `service-invoice-profile-${process.pid}`);
const width = Number(process.env.AYEC_AUDIT_WIDTH || 1180);
const height = Number(process.env.AYEC_AUDIT_HEIGHT || 820);
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

async function targetPage() {
  for (let i = 0; i < 100; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/json`);
      const targets = await response.json();
      const page = targets.find(item => item.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await wait(200);
  }
  throw new Error("Headless Edge did not expose a page target.");
}

async function run() {
  fs.mkdirSync(output, { recursive: true });
  const browser = spawn(edge, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, `--window-size=${width},${height}`, url], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await targetPage();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message)); else request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: false });
    for (let i = 0; i < 100; i += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof serviceInvoiceDialog === 'function' && typeof customerActions === 'function'")) break;
      await wait(150);
    }
    const result = await evaluate(`(async () => {
      const originalApiFetch = apiFetch, originalFetch = window.fetch, originalClick = HTMLAnchorElement.prototype.click;
      window.__serviceInvoiceOriginals = { originalApiFetch, originalFetch, originalClick };
      const customer = { id: 901, name: "QA Service Customer", balances: { TRY: -80 }, services: [] };
      db.customers = [customer];
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint.endsWith("/pdf")) return { ok: true, blob: async () => new Blob(["pdf"], { type: "application/pdf" }) };
        if (options.method === "POST") return { marked: 2 };
        return { customer_id: 901, customer_name: customer.name, currency: "TRY", currency_rate: 1, customer_balance: -80, transactions: [
          { id: 71, source: "accounting", date: "2026-10-10", description: "TRY service", category: "Sat\\u0131\\u015f", amount: 100, currency: "TRY" },
          { id: 72, source: "currency", date: "2026-10-10", description: "USD service", category: "Sat\\u0131\\u015f", amount: 2, currency: "USD", try_equivalent: 80 }
        ] };
      };
      let downloaded = "";
      window.fetch = async () => new Response(new Blob(["pdf"], { type: "application/pdf" }), { status: 200 });
      URL.createObjectURL = () => "blob:service-invoice-qa"; URL.revokeObjectURL = () => {};
      HTMLAnchorElement.prototype.click = function() { downloaded = this.download; window.__serviceInvoiceDownloaded = downloaded; };
      hideAuth();
      applyTheme("midnight");
      customerActions(901);
      const opener = document.createElement("button"); opener.dataset.action = "customer-actions"; opener.dataset.id = "901"; document.body.append(opener); opener.click();
      await new Promise(resolve => setTimeout(resolve, 80));
      const invoiceAction = document.querySelector('[data-modal-action="service-invoice"]');
      if (!invoiceAction) throw new Error("Service invoice action was not added to the customer action menu.");
      invoiceAction.click(); await new Promise(resolve => setTimeout(resolve, 80));
      const invoiceModal = document.querySelector("#appDialog");
      const rows = [...invoiceModal.querySelectorAll("[data-invoice-transaction]")];
      if (rows.length !== 2) throw new Error("Expected 2 transaction rows, found " + rows.length + ".");
      const initialSelection = { selected: rows.filter(input => input.checked).length, total: document.querySelector("#serviceInvoiceTotal")?.textContent || "" };
      const balanceText = document.querySelector(".service-invoice-balance")?.textContent || "";
      const geometry = document.querySelector("#dialogForm")?.getBoundingClientRect();
      const dialog = document.querySelector("#appDialog")?.getBoundingClientRect();
      const rect = selector => { const value = document.querySelector(selector)?.getBoundingClientRect(); return value ? [Math.round(value.x), Math.round(value.y), Math.round(value.width), Math.round(value.height)] : null; };
      const elementGeometry = { formHeader: rect("#dialogForm>header"), body: rect("#dialogBody"), footer: rect("#dialogFooter"), titlebar: rect(".service-invoice-titlebar"), header: rect(".service-invoice-web>header"), headerTitle: rect(".service-invoice-web>header>strong"), balance: rect(".service-invoice-balance"), controls: rect(".service-invoice-header-controls"), activeCurrency: rect(".service-invoice-header-controls>span"), template: rect("#serviceInvoiceTemplate"), table: rect(".service-invoice-table"), title: rect(".service-invoice-title"), columns: rect(".service-invoice-columns"), group: rect(".service-invoice-group"), row: rect(".service-invoice-row"), note: rect(".service-invoice-web>footer>span"), total: rect(".service-invoice-web>footer>div"), totalLabel: rect(".service-invoice-web>footer>div>b"), totalValue: rect("#serviceInvoiceTotal"), cancel: rect("#dialogCancel"), submit: rect("#dialogSubmit") };
      const titlebar=document.querySelector(".service-invoice-titlebar"),close=titlebar?.querySelector("button");
      const noteStyle=getComputedStyle(document.querySelector(".service-invoice-web>footer>span"));
      const footerNoteStyle={fontSize:noteStyle.fontSize,fontStyle:noteStyle.fontStyle,fontWeight:noteStyle.fontWeight,color:noteStyle.color};
      const oddRowStyle=getComputedStyle(document.querySelector(".service-invoice-row:nth-of-type(odd)"));
      const oddRowColors={background:oddRowStyle.backgroundColor,color:oddRowStyle.color};
      const submitStyle=getComputedStyle(document.querySelector("#dialogSubmit"));
      const disabledSubmitStyle={backgroundImage:submitStyle.backgroundImage,borderColor:submitStyle.borderColor,color:submitStyle.color};
      const headerTitleStyle=getComputedStyle(document.querySelector(".service-invoice-web>header>strong"));
      const balanceStyle=getComputedStyle(document.querySelector(".service-invoice-balance"));
      const headerTypography={title:headerTitleStyle.fontSize,balance:balanceStyle.fontSize};
      const footerStyles=[".service-invoice-web>footer>span",".service-invoice-web>footer>div>b","#serviceInvoiceTotal","#dialogCancel","#dialogSubmit"].map(selector=>{const style=getComputedStyle(document.querySelector(selector));return{fontSize:style.fontSize,fontWeight:style.fontWeight,fontStyle:style.fontStyle,color:style.color,lineHeight:style.lineHeight}});
      return { initialSelection, balanceText, headerTypography, footerStyles, submitDisabled:document.querySelector("#dialogSubmit")?.disabled||false, disabledSubmitStyle, footerNoteStyle, oddRowColors, titlebarTitleColor:titlebar?getComputedStyle(titlebar).color:"", titlebarCloseColor:close?getComputedStyle(close).color:"", modalWidth: geometry?.width, modalHeight: geometry?.height, dialogBounds: dialog ? { x: dialog.x, y: dialog.y, width: dialog.width, height: dialog.height } : null, elementGeometry, exceptions: [] };
    })()`);
    if (result.initialSelection.selected !== 0 || result.initialSelection.total !== "0.00 \u20ba" || !result.balanceText.includes("-80.00 \u20ba") || !result.submitDisabled || !result.disabledSubmitStyle.backgroundImage.includes("linear-gradient")) throw new Error(`Service invoice initial state mismatch: ${JSON.stringify(result)}`);
    if (JSON.stringify(result.elementGeometry.balance) !== JSON.stringify([232, 72, 352, 35])) throw new Error(`Service invoice balance geometry mismatch: ${JSON.stringify(result.elementGeometry.balance)}`);
    if (JSON.stringify(result.elementGeometry.headerTitle) !== JSON.stringify([11, 77, 209, 27])) throw new Error(`Service invoice heading alignment mismatch: ${JSON.stringify(result.elementGeometry.headerTitle)}`);
    if (JSON.stringify(result.elementGeometry.template) !== JSON.stringify([1044, 75, 120, 28])) throw new Error(`Service invoice template selector geometry mismatch: ${JSON.stringify(result.elementGeometry.template)}`);
    if (JSON.stringify(result.elementGeometry.total) !== JSON.stringify([801, 644, 363, 107])) throw new Error(`Service invoice total panel geometry mismatch: ${JSON.stringify(result.elementGeometry.total)}`);
    if (JSON.stringify(result.elementGeometry.totalLabel) !== JSON.stringify([826, 669, 154, 57]) || JSON.stringify(result.elementGeometry.totalValue) !== JSON.stringify([986, 669, 153, 57])) throw new Error(`Service invoice summary label/value geometry mismatch: ${JSON.stringify({ label: result.elementGeometry.totalLabel, value: result.elementGeometry.totalValue })}`);
    if (JSON.stringify(result.headerTypography) !== JSON.stringify({ title: "18.67px", balance: "14.67px" })) throw new Error(`Service invoice header typography mismatch: ${JSON.stringify(result.headerTypography)}`);
    if (result.titlebarTitleColor !== "rgb(226, 232, 240)" || result.titlebarCloseColor !== "rgb(152, 168, 186)") throw new Error(`Service invoice titlebar contrast mismatch: ${JSON.stringify({ title: result.titlebarTitleColor, close: result.titlebarCloseColor })}`);
    if (JSON.stringify(result.footerNoteStyle) !== JSON.stringify({ fontSize: "12px", fontStyle: "italic", fontWeight: "400", color: "rgb(148, 163, 184)" })) throw new Error(`Service invoice footer note style mismatch: ${JSON.stringify(result.footerNoteStyle)}`);
    const expectedFooterStyles = [{ fontSize: "12px", fontWeight: "400", fontStyle: "italic" }, { fontSize: "14px", fontWeight: "700", fontStyle: "normal" }, { fontSize: "18px", fontWeight: "700", fontStyle: "normal" }, { fontSize: "12px", fontWeight: "700", fontStyle: "normal" }, { fontSize: "12px", fontWeight: "400", fontStyle: "normal" }];
    if (JSON.stringify(result.footerStyles.map(({ fontSize, fontWeight, fontStyle }) => ({ fontSize, fontWeight, fontStyle }))) !== JSON.stringify(expectedFooterStyles)) throw new Error(`Service invoice footer typography mismatch: ${JSON.stringify(result.footerStyles)}`);
    if (JSON.stringify(result.oddRowColors) !== JSON.stringify({ background: "rgb(247, 247, 247)", color: "rgb(23, 32, 51)" })) throw new Error(`Service invoice odd-row contrast mismatch: ${JSON.stringify(result.oddRowColors)}`);
    const bounds = result.dialogBounds;
    const baselineScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: bounds ? { ...bounds, scale: 1 } : undefined });
    fs.writeFileSync(path.join(output, "service-invoice-dialog-unselected-headless.png"), Buffer.from(baselineScreenshot.data, "base64"));
    const selection = await evaluate(`(async () => { const rows=[...document.querySelectorAll("[data-invoice-transaction]")],group=document.querySelector('[data-invoice-group="0"]'); group.click(); const selected={groupChecked:rows.every(input=>input.checked),submitEnabled:!document.querySelector("#dialogSubmit")?.disabled,total:document.querySelector("#serviceInvoiceTotal")?.textContent||""}; group.click(); const cleared={groupUnchecked:rows.every(input=>!input.checked),submitDisabled:document.querySelector("#dialogSubmit")?.disabled,total:document.querySelector("#serviceInvoiceTotal")?.textContent||""}; group.click(); return {...selected,cleared}; })()`);
    if (!selection.groupChecked || !selection.submitEnabled || selection.total !== "180.00 \u20ba" || !selection.cleared.groupUnchecked || !selection.cleared.submitDisabled || selection.cleared.total !== "0.00 \u20ba") throw new Error(`Service invoice selection state mismatch: ${JSON.stringify(selection)}`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: bounds ? { ...bounds, scale: 1 } : undefined });
    const screenshotPath = path.join(output, "service-invoice-dialog-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    const workflow = await evaluate(`(async () => { document.querySelector("#dialogForm")?.requestSubmit(); await new Promise(resolve => setTimeout(resolve, 120)); const confirmation = document.querySelector("#dialogTitle")?.textContent || ""; const pdfDownload = window.__serviceInvoiceDownloaded || ""; document.querySelector("#appDialog")?.close("cancel"); const original = window.__serviceInvoiceOriginals; apiFetch = original.originalApiFetch; window.fetch = original.originalFetch; HTMLAnchorElement.prototype.click = original.originalClick; return { confirmation, pdfDownload }; })()`);
    if (!workflow.confirmation.includes("PDF") || workflow.pdfDownload !== "service-invoice-901.pdf") throw new Error(`Service invoice PDF workflow mismatch: ${JSON.stringify(workflow)}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${exceptions.join(" | ")}`);
    process.stdout.write(`${JSON.stringify({ ...result, ...selection, ...workflow, screenshot: screenshotPath, baselineScreenshot: path.join(output, "service-invoice-dialog-unselected-headless.png"), browserExceptions: exceptions.length })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
