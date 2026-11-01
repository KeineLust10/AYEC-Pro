const { spawn } = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");

const root = path.resolve(__dirname, "../..");
const webRoot = path.join(root, "Web_Arayuzu");
const output = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/customer-density-audit"));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-customer-density-"));
const edge = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      server.close(error => error ? reject(error) : resolve(port));
    });
  });
}

function stop(child) {
  if (!child?.pid) return Promise.resolve();
  return new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
    killer.once("error", resolve);
  });
}

async function run() {
  fs.mkdirSync(output, { recursive: true });
  const appPort = await freePort();
  const debugPort = await freePort();
  const baseUrl = `http://127.0.0.1:${appPort}/`;
  const backend = spawn(process.env.PYTHON || "python", [path.join(webRoot, "Main.py"), "--host", "127.0.0.1", "--port", String(appPort), "--db", path.join(temp, "admin.db"), "--tenant-dir", path.join(temp, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
  let browser;
  let socket;
  let profile = path.join(temp, "edge-profile");
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    browser = spawn(edge, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1440,1000", baseUrl], { stdio: "ignore", windowsHide: true });
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("No headless page target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const item = pending.get(message.id);
      if (!item) return;
      pending.delete(message.id);
      message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      pending.set(requestId, { resolve, reject });
      socket.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    let readyPage = false;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      readyPage = await evaluate("document.readyState === 'complete' && typeof render === 'function'");
      if (readyPage) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!readyPage) throw new Error("Web app did not finish loading.");
    const result = await evaluate(`(()=>{
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      const balances=[{TRY:-100,USD:100},{TRY:-50},{USD:100},{TRY:0},{TRY:-5},{TRY:0},{TRY:80},{TRY:-20}];
      db.customers=Array.from({length:8},(_,i)=>({id:i+1,name:'Density '+(i+1),type:'Bireysel',city:i===0?' Istanbul ':'Istanbul',phone:'555000'+i,email:'density'+i+'@example.test',balances:balances[i]}));
      exchangeRateState={TRY:{selling:1},USD:{selling:2},EUR:{selling:4}};
      desktopSettings.currency='TRY';
      db.devices=[];
      document.body.dataset.customerDensity='';
      page='customers';
      render();
      const button=document.querySelector('#customerDensityToggle');
      const table=document.querySelector('#customerTable .customer-data-table');
      const firstRow=()=>document.querySelector('#customerTable .customer-data-table tbody tr')?.getBoundingClientRect().height||0;
      const dense={button:!!button,pressed:button?.getAttribute('aria-pressed'),className:table?.className,height:firstRow(),mobileOverflow:document.documentElement.scrollWidth>innerWidth};
      if(!button||!table||!dense.height)throw new Error('Customer density control or table did not render.');
      button.click();
      const comfortable={pressed:button.getAttribute('aria-pressed'),className:table.className,height:firstRow(),label:button.getAttribute('aria-label')};
      if(!table.classList.contains('comfortable')||comfortable.height<=dense.height)throw new Error('Comfortable density did not increase row height.');
      render();
      const afterRender={pressed:document.querySelector('#customerDensityToggle')?.getAttribute('aria-pressed'),className:document.querySelector('#customerTable .customer-data-table')?.className};
      if(!afterRender.className?.includes('comfortable'))throw new Error('Density choice was lost after render.');
      const setBalance=value=>{const select=document.querySelector('#customerBalanceFilter');select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}));return Number(document.querySelector('#customerCount')?.textContent||0)};
      const balanceFilters={nonzero:setBalance('nonzero'),debt:setBalance('debt'),credit:setBalance('credit'),zero:setBalance('zero')};
      if(JSON.stringify(balanceFilters)!==JSON.stringify({nonzero:6,debt:4,credit:3,zero:2}))throw new Error('Customer balance filters do not include the desktop receivable alias: '+JSON.stringify(balanceFilters));
      const allBalances=document.querySelector('#customerBalanceFilter');allBalances.value='';allBalances.dispatchEvent(new Event('change',{bubbles:true}));
      const locationSelect=document.querySelector('#customerLocationFilter');locationSelect.value='Istanbul';locationSelect.dispatchEvent(new Event('change',{bubbles:true}));
      const locationCount=Number(document.querySelector('#customerCount')?.textContent||0);
      if(locationCount!==8)throw new Error('Customer city filtering did not normalize surrounding whitespace: '+locationCount);
      const sizeSelect=document.querySelector('#customerPageSize'),testPageSize=document.createElement('option');testPageSize.value='5';testPageSize.textContent='5';sizeSelect.append(testPageSize);sizeSelect.value='5';sizeSelect.dispatchEvent(new Event('change',{bubbles:true}));
      const pageOneIds=[...document.querySelectorAll('.customer-row-select')].map(input=>input.dataset.id);
      const headerSelect=document.querySelector('#customerSelectAll');headerSelect.checked=true;headerSelect.dispatchEvent(new Event('change',{bubbles:true}));
      const firstPageSelection=[...window.ayecSelectedCustomerIds].sort();
      if(pageOneIds.length!==5||JSON.stringify(firstPageSelection)!==JSON.stringify([...pageOneIds].sort()))throw new Error('Select-all did not stay within the visible customer page.');
      document.querySelector('#customerPageNext').click();
      const pageTwoIds=[...document.querySelectorAll('.customer-row-select')].map(input=>input.dataset.id);
      const pageTwoAfterNavigation={ids:[...window.ayecSelectedCustomerIds].sort(),checked:document.querySelector('#customerSelectAll').checked,indeterminate:document.querySelector('#customerSelectAll').indeterminate,checkedRows:[...document.querySelectorAll('.customer-row-select:checked')].length};
      if(pageTwoAfterNavigation.ids.length||pageTwoAfterNavigation.checked||pageTwoAfterNavigation.indeterminate||pageTwoAfterNavigation.checkedRows)throw new Error('Customer selection was not cleared after the desktop-style page reload.');
      document.querySelector('#customerSelectAll').checked=true;document.querySelector('#customerSelectAll').dispatchEvent(new Event('change',{bubbles:true}));
      const pageTwoSelection=[...window.ayecSelectedCustomerIds].sort();
      document.querySelector('#customerPagePrev').click();
      const afterPageReturn={ids:[...window.ayecSelectedCustomerIds].sort(),checkedRows:[...document.querySelectorAll('.customer-row-select:checked')].length,visibleIds:[...document.querySelectorAll('.customer-row-select')].map(input=>input.dataset.id)};
      if(JSON.stringify(pageTwoSelection)!==JSON.stringify([...pageTwoIds].sort())||afterPageReturn.ids.length||afterPageReturn.checkedRows||JSON.stringify(afterPageReturn.visibleIds)!==JSON.stringify([...pageOneIds]))throw new Error('Customer bulk selection did not reset with the desktop page reload.');
      const multiButton=document.querySelector('#customerMultiSelect');multiButton.click();
      document.querySelector('tr[data-kind="customer"][data-id="1"]').click();
      const firstRowSelection={pressed:multiButton.getAttribute('aria-pressed'),rowSelected:document.querySelector('tr[data-id="1"]')?.classList.contains('selected'),checkboxChecked:document.querySelector('tr[data-id="1"] .customer-row-select')?.checked,rowIds:[...window.ayecCustomerRowSelection].sort(),bulkIds:[...window.ayecSelectedCustomerIds].sort()};
      document.querySelector('tr[data-kind="customer"][data-id="2"]').click();
      document.querySelector('tr[data-kind="customer"][data-id="1"]').click();
      const rowToggleSelection={rowIds:[...window.ayecCustomerRowSelection].sort(),secondRowSelected:document.querySelector('tr[data-id="2"]')?.classList.contains('selected'),secondRowChecked:document.querySelector('tr[data-id="2"] .customer-row-select')?.checked,bulkIds:[...window.ayecSelectedCustomerIds].sort()};
      multiButton.click();
      document.querySelector('tr[data-kind="customer"][data-id="3"]').click();
      const disabledModeSelection={pressed:multiButton.getAttribute('aria-pressed'),modeClass:document.querySelector('#customerTable')?.classList.contains('multi-select'),rowIds:[...window.ayecCustomerRowSelection].sort(),row3Selected:document.querySelector('tr[data-id="3"]')?.classList.contains('selected'),bulkIds:[...window.ayecSelectedCustomerIds].sort()};
      if(firstRowSelection.pressed!=='true'||!firstRowSelection.rowSelected||firstRowSelection.checkboxChecked||JSON.stringify(firstRowSelection.rowIds)!==JSON.stringify(['1'])||firstRowSelection.bulkIds.length!==0||JSON.stringify(rowToggleSelection.rowIds)!==JSON.stringify(['2'])||!rowToggleSelection.secondRowSelected||rowToggleSelection.secondRowChecked||rowToggleSelection.bulkIds.length!==0||disabledModeSelection.pressed!=='false'||disabledModeSelection.modeClass||JSON.stringify(disabledModeSelection.rowIds)!==JSON.stringify(['3'])||!disabledModeSelection.row3Selected||disabledModeSelection.bulkIds.length!==0)throw new Error('Customer row-selection mode and bulk checkboxes are not independent.');
      return {dense,comfortable,afterRender,balanceFilters,locationCount,pageSelection:{pageOneIds,pageTwoIds,firstPageSelection,pageTwoAfterNavigation,pageTwoSelection,afterPageReturn},multiSelect:{firstRowSelection,rowToggleSelection,disabledModeSelection}};
    })()`);
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const mobile = await evaluate(`(()=>{const b=document.querySelector('#customerDensityToggle');const t=document.querySelector('#customerTable .customer-data-table');return {viewport:innerWidth,document:document.documentElement.scrollWidth,buttonVisible:!!b&&b.getBoundingClientRect().width>0,tableClass:t?.className,actionsColumns:getComputedStyle(document.querySelector('.customer-quick-actions')).gridTemplateColumns}})()`);
    if (mobile.document > mobile.viewport || !mobile.buttonVisible) throw new Error("Customer toolbar overflows or density toggle is hidden at mobile width.");
    if (exceptions.length) throw new Error("Browser exceptions: " + exceptions.join(" | "));
    fs.writeFileSync(path.join(output, "customer-density-audit.json"), JSON.stringify({ ok: true, result, mobile, exceptions }, null, 2), "utf8");
  } catch (error) {
    fs.writeFileSync(path.join(output, "customer-density-audit.json"), JSON.stringify({ ok: false, error: String(error.stack || error) }, null, 2), "utf8");
    process.exitCode = 1;
  } finally {
    socket?.close();
    await stop(browser);
    await stop(backend);
    if (path.resolve(temp).startsWith(path.resolve(os.tmpdir()) + path.sep)) fs.rmSync(temp, { recursive: true, force: true });
  }
}

run().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
