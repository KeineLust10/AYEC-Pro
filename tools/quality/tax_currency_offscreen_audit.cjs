const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_TAX_AUDIT_CDP_PORT || 9237);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `tax-currency-headless-profile-${process.pid}`);

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edge, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl
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
    const browserExceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") browserExceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
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
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof apiFetch === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    const result = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      settingsSection='tax-currency';page='settings';document.body.dataset.page='settings';
      const requests=[];
      window.fetch=async(url,options={})=>{requests.push({url:String(url),method:options.method||'GET',body:options.body||null});const payload=String(url).includes('/manual')?{ok:true,saved:{USD:45.5,EUR:49.25,GBP:58.75},rates:{USD:{selling:45.5,source:'MANUAL'},EUR:{selling:49.25,source:'MANUAL'},GBP:{selling:58.75,source:'MANUAL'}}}:{ok:true,percent:8.5,rates:{}};return new Response(JSON.stringify(payload),{status:200,headers:{'Content-Type':'application/json'}})};
      window.__taxAuditRequests=requests;
      render();
      const initial={heading:document.querySelector('#content h3')?.textContent,currencies:[...document.querySelectorAll('[data-tax-rate]')].map(input=>input.dataset.taxRate),actions:[...document.querySelectorAll('[data-tax-currency-action]')].map(button=>button.dataset.taxCurrencyAction),globalSaveButtons:document.querySelectorAll('[data-action="save-settings"]').length,misplacedSyncPanel:document.body.innerText.includes('Otomatik Kur E\\u015fitleme')};
      document.querySelector('#taxVatPercent').value='8.5';document.querySelector('[data-tax-currency-action="save-vat"]').click();
      await new Promise(resolve=>setTimeout(resolve,50));
      for(const [currency,value] of Object.entries({USD:'45.5',EUR:'49.25',GBP:'58.75'})){const input=document.querySelector('[data-tax-rate="'+currency+'"]');if(input)input.value=value}
      document.querySelector('[data-tax-currency-action="save-rates"]').click();
      await new Promise(resolve=>setTimeout(resolve,50));
      return {initial,requests,vatValue:desktopSettings.vat_default_rate,visible:document.querySelector('#content')?.innerText.includes('GBP')};
    })()`);
    if (!result || result.initial.currencies.join(",") !== "USD,EUR,GBP") throw new Error(`Currency controls mismatch: ${JSON.stringify(result?.initial)}`);
    if (!result.initial.actions.includes("save-vat") || !result.initial.actions.includes("save-rates") || !result.initial.actions.includes("fetch-rates")) throw new Error(`Settings action controls missing: ${JSON.stringify(result.initial.actions)}`);
    if (result.initial.globalSaveButtons !== 0 || result.initial.misplacedSyncPanel) throw new Error(`Desktop settings controls are misplaced: ${JSON.stringify(result.initial)}`);
    const vat = result.requests.find(request => request.url === "/api/desktop/tax-currency/vat");
    const rates = result.requests.find(request => request.url === "/api/desktop/exchange-rates/manual");
    if (!vat || JSON.parse(vat.body).percent !== "8.5") throw new Error(`VAT save request mismatch: ${JSON.stringify(vat)}`);
    const payload = rates && JSON.parse(rates.body).rates;
    if (!payload || payload.USD !== "45.5" || payload.EUR !== "49.25" || payload.GBP !== "58.75") throw new Error(`Manual rate request mismatch: ${JSON.stringify(rates)}`);
    if (browserExceptions.length) throw new Error("Browser exceptions: " + JSON.stringify(browserExceptions));
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "tax-currency-settings-headless.png"), Buffer.from(screenshot.data, "base64"));
    const bankSettings = await evaluate(`(async()=>{settingsSection='bank-settings';page='settings';render();const inputs=[...document.querySelectorAll('.settings-content .exact-setting')],keys=inputs.map(input=>input.dataset.settingKey),currencyOptions=[...document.querySelector('[data-setting-key="bank_default_currency"]')?.options||[]].map(option=>option.value),values={bank_default_name:'Audit Bank',bank_default_iban:'TR000000000000000000000000',bank_default_currency:'USD',bank_fx_update_minutes:'30',bank_auto_fx:'0',bank_sync_finance:'0',bank_warn_negative:'0'};for(const [key,value] of Object.entries(values)){const input=document.querySelector('[data-setting-key="'+key+'"]');if(input){if(input.type==='checkbox')input.checked=value==='1';else input.value=value}}document.querySelector('[data-setting-key="bank_auto_fx"]').click();values.bank_auto_fx=document.querySelector('[data-setting-key="bank_auto_fx"]').checked?'1':'0';await new Promise(resolve=>setTimeout(resolve,150));const writes=window.__taxAuditRequests.filter(request=>request.url==='/api/desktop/table/settings').map(request=>JSON.parse(request.body));return {keys,currencyOptions,writeKeys:writes.map(write=>write.key),writes,values}})()`);
    const requiredBankKeys = ["bank_default_name", "bank_default_iban", "bank_default_currency", "bank_fx_update_minutes", "bank_auto_fx", "bank_sync_finance", "bank_warn_negative"];
    if (requiredBankKeys.some(key => !bankSettings.keys.includes(key)) || bankSettings.currencyOptions.join(",") !== "TRY,USD,EUR") throw new Error("Bank settings fields or currency options mismatch: " + JSON.stringify(bankSettings));
    if (requiredBankKeys.some(key => !bankSettings.writes.some(write => write.key === key && String(write.value) === bankSettings.values[key]))) throw new Error("Bank settings auto-save omitted or changed values: " + JSON.stringify(bankSettings.writes));
    const bankScreenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "bank-settings-headless.png"), Buffer.from(bankScreenshot.data, "base64"));
    const companySettings = await evaluate(`(async()=>{settingsSection='company';page='settings';render();document.querySelector('[data-company-open-editor]')?.click();const dialog=document.querySelector('#appDialog');dialog.querySelector('[data-company-editor-tab="system"]')?.click();const control=dialog.querySelector('[name="currency_precision"]'),state={section:settingsSection,editorOpen:dialog.open,tab:dialog.querySelector('[data-company-editor-tab="system"]')?.getAttribute('aria-selected'),hasControl:!!control};if(!control)return state;state.tag=control.tagName;state.options=[...control.options].map(option=>option.value);control.value='3';dialog.querySelector('#dialogSubmit')?.click();await new Promise(resolve=>setTimeout(resolve,250));state.writes=window.__taxAuditRequests.filter(request=>request.url==='/api/desktop/table/settings').map(request=>JSON.parse(request.body)).filter(write=>write.key==='currency_precision');return state})()`);
    if (!companySettings.editorOpen || companySettings.tab !== "true" || !companySettings.hasControl || companySettings.tag !== "SELECT" || companySettings.options.join(",") !== "0,1,2,3" || !companySettings.writes.some(write => write.value === "3")) throw new Error("Company currency precision control mismatch: " + JSON.stringify(companySettings));
    const companyScreenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "company-currency-settings-headless.png"), Buffer.from(companyScreenshot.data, "base64"));
    console.log(JSON.stringify({ heading: result.initial.heading, currencies: result.initial.currencies, actions: result.initial.actions, vatRequest: vat, rateRequest: rates, browserExceptions: browserExceptions.length, taxScreenshot: "tax-currency-settings-headless.png", bankSettings, bankScreenshot: "bank-settings-headless.png", companySettings, companyScreenshot: "company-currency-settings-headless.png" }));
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
