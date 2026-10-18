const { spawn, execFileSync } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");

const root = path.resolve(__dirname, "../../Web_Arayuzu");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const cdpPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9271);
const httpPort = Number(process.env.AYEC_SEARCH_FIXTURE_PORT || 8871);
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `global-search-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

const html = `<!doctype html><html data-theme="midnight"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/midnight-reference.css"><style>body{margin:0;background:#0a121f;color:#eaf0f8;font:14px "Segoe UI",sans-serif}.top-actions{display:flex;gap:12px;padding:24px}.global-search{display:flex;align-items:center;gap:8px;width:290px;padding:9px 13px;border:1px solid #24364d;border-radius:11px;background:#17243a}.global-search input{width:100%;border:0;outline:0;background:transparent;color:inherit}.global-search-dialog{margin:auto}</style></head><body><header class="top-actions"><label class="global-search"><span aria-hidden="true">&#8981;</span><input id="globalSearch" placeholder="Search"></label><button>Other action</button></header><nav id="nav"><button data-page="project-archive"><span>.</span><span>Project Archive</span></button></nav><script>var page="dashboard";var db={customers:[{name:"Musteri Ornegi",phone:"555",services:[{no:"SRV-2401",serial:"ABC-123",device:"Notebook",note:"Screen repair",status:"Bekliyor"}]}],stock:[{name:"Musteri Parca",quantity:2,sell:5,currency:"TRY"}]};function money(){return "5.00 TL"}function esc(value){return String(value??"")}function toast(message){window.lastToast=message}function navigate(route){window.lastNavigation=route}window.fixtureReady=true;</script><script src="/global-search-reference.js"></script></body></html>`;

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const server = http.createServer((request, response) => {
    if (request.url === "/global-search-reference.js") {
      response.setHeader("content-type", "text/javascript; charset=utf-8");
      response.end(fs.readFileSync(path.join(root, "web/global-search-reference.js")));
    } else if (request.url === "/midnight-reference.css") {
      response.setHeader("content-type", "text/css; charset=utf-8");
      response.end(fs.readFileSync(path.join(root, "web/midnight-reference.css")));
    } else {
      response.setHeader("content-type", "text/html; charset=utf-8");
      response.end(html);
    }
  });
  await new Promise(resolve => server.listen(httpPort, "127.0.0.1", resolve));
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", `http://127.0.0.1:${httpPort}/`], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try { target = (await (await fetch(`http://127.0.0.1:${cdpPort}/json`)).json()).find(item => item.type === "page"); } catch (_) {}
      if (target?.webSocketDebuggerUrl) break;
      await delay(200);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a page target.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let id = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown exception");
      if (!message.id) return;
      const task = pending.get(message.id);
      if (!task) return;
      pending.delete(message.id);
      message.error ? task.reject(new Error(message.error.message)) : task.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => { const requestId = ++id; pending.set(requestId, { resolve, reject }); socket.send(JSON.stringify({ id: requestId, method, params })); });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && window.fixtureReady === true && document.querySelector('#globalSearchDialog')")) break;
      await delay(100);
    }
    await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true,bubbles:true}))");
    await evaluate("document.querySelector('#globalSearchDialog').open");
    const desktop = await evaluate("({open:document.querySelector('#globalSearchDialog').open,focus:document.activeElement.id,inside:!!document.querySelector('#globalSearchDialog .global-search-wrap'),width:Math.round(document.querySelector('#globalSearchDialog').getBoundingClientRect().width),placeholder:document.querySelector('#globalSearch').placeholder})");
    if (!desktop.open || desktop.focus !== "globalSearch" || !desktop.inside || desktop.width > 600 || !desktop.placeholder.toLocaleLowerCase().includes("servis")) throw new Error(`Palette did not open in desktop mode: ${JSON.stringify(desktop)}`);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "global-search-palette-headless.png"), Buffer.from(screenshot.data, "base64"));
    await evaluate("document.querySelector('#globalSearch').value='MUSTER';document.querySelector('#globalSearch').dispatchEvent(new Event('input',{bubbles:true}))");
    const search = await evaluate("({labels:Array.from(document.querySelectorAll('[role=option] strong')).map(node=>node.textContent),expanded:document.querySelector('#globalSearch').getAttribute('aria-expanded'),value:document.querySelector('#globalSearch').value,dbType:typeof window.db,navType:typeof window.navigate,body:document.body.innerText.slice(0,80)})");
    if (!search.labels.some(label => label === "Musteri Ornegi") || !search.labels.some(label => label === "Musteri Parca") || search.expanded !== "true") throw new Error(`Search results were not rendered: ${JSON.stringify({...search,runtimeExceptions:exceptions})}`);
    await evaluate("document.querySelector('#globalSearch').value='555';document.querySelector('#globalSearch').dispatchEvent(new Event('input',{bubbles:true}))");
    const phoneSearch = await evaluate("Array.from(document.querySelectorAll('[role=option] strong')).map(node=>node.textContent)");
    if (phoneSearch.length !== 1 || phoneSearch[0] !== "Musteri Ornegi") throw new Error(`Phone search did not return its customer: ${JSON.stringify(phoneSearch)}`);
    await evaluate("document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))");
    const escaped = await evaluate("({open:document.querySelector('#globalSearchDialog').open,restored:document.querySelector('.top-actions > .global-search-wrap')!==null,placeholder:document.querySelector('#globalSearch').placeholder})");
    if (escaped.open || !escaped.restored || escaped.placeholder !== "Search") throw new Error(`Escape did not close and restore the search field: ${JSON.stringify(escaped)}`);
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',metaKey:true,bubbles:true}))");
    const mobile = await evaluate("({open:document.querySelector('#globalSearchDialog').open,display:getComputedStyle(document.querySelector('#globalSearchDialog .global-search-wrap')).display,width:Math.round(document.querySelector('#globalSearchDialog').getBoundingClientRect().width)})");
    if (!mobile.open || mobile.display === "none" || mobile.width > 390) throw new Error(`Palette failed on mobile viewport: ${JSON.stringify(mobile)}`);
    await evaluate("document.querySelector('#globalSearch').value='ABC-123';document.querySelector('#globalSearch').dispatchEvent(new Event('input',{bubbles:true}))");
    const serviceSearch = await evaluate("({labels:Array.from(document.querySelectorAll('[role=option] strong')).map(node=>node.textContent),subtitles:Array.from(document.querySelectorAll('[role=option] small')).map(node=>node.textContent)})");
    if (!serviceSearch.labels.includes("SRV-2401") || !serviceSearch.subtitles.some(value=>value.includes("Notebook"))) throw new Error(`Service search did not return its device: ${JSON.stringify(serviceSearch)}`);
    await evaluate("document.querySelector('#globalSearchResult0')?.click()");
    const serviceActivated = await evaluate("({route:window.lastNavigation,filter:window.ayecAdvancedServiceFilter,open:document.querySelector('#globalSearchDialog').open})");
    if (serviceActivated.route !== "services" || serviceActivated.filter?.tracking !== "SRV-2401" || serviceActivated.open) throw new Error(`Service search activation failed: ${JSON.stringify(serviceActivated)}`);
    await evaluate("document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',metaKey:true,bubbles:true}))");
    await evaluate("document.querySelector('#globalSearch').value='project archive';document.querySelector('#globalSearch').dispatchEvent(new Event('input',{bubbles:true}))");
    const routeSearch = await evaluate("Array.from(document.querySelectorAll('[role=option] strong')).map(node=>node.textContent)");
    if (!routeSearch.includes("Project Archive")) throw new Error(`The rendered navigation label was not indexed: ${JSON.stringify(routeSearch)}`);
    await evaluate("document.querySelector('#globalSearch').dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowDown',bubbles:true}));document.querySelector('#globalSearch').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))");
    const activated = await evaluate("({route:window.lastNavigation,open:document.querySelector('#globalSearchDialog').open,restored:document.querySelector('.top-actions > .global-search-wrap')!==null})");
    if (activated.route !== "project-archive" || activated.open || !activated.restored || exceptions.length) throw new Error(`Palette activation failed: ${JSON.stringify({ activated, exceptions })}`);
    process.stdout.write(`${JSON.stringify({ desktop, search, phoneSearch, escaped, mobile, serviceSearch, serviceActivated, routeSearch, activated, exceptions, screenshot: path.join(outputDir, "global-search-palette-headless.png") })}\n`);
  } finally {
    try { socket?.close(); } catch (_) {}
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    await delay(300);
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
    await new Promise(resolve => server.close(resolve));
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
