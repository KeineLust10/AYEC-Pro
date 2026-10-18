const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 34000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright/web-route-smoke");
const manualContent = require("node:fs").readFileSync(path.resolve(__dirname, "../..", "KULLANIM_KILAVUZU.md"), "utf8");
const customerReferenceFixture = JSON.parse(fs.readFileSync(path.join(__dirname, "fixtures", "customer_management_reference.json"), "utf8"));
const nativeCustomerOrder = [1, 2, 58, 25, 44, 19, 32];
customerReferenceFixture.sort((left, right) => {
  const leftIndex = nativeCustomerOrder.indexOf(Number(left.id));
  const rightIndex = nativeCustomerOrder.indexOf(Number(right.id));
  return (leftIndex < 0 ? nativeCustomerOrder.length + Number(left.id) : leftIndex)
    - (rightIndex < 0 ? nativeCustomerOrder.length + Number(right.id) : rightIndex);
});
const profile = path.join(outputDir, `web-route-smoke-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function waitForTarget() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const page = targets.find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1300,850", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  let activeRoute = "bootstrap";
  const exceptions = [];
  const tileNetworkEvents = [];
  const tileRequestUrls = new Map();
  try {
    const target = await waitForTarget();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let nextId = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push({ route: activeRoute, message: message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text || "Unknown browser exception" });
      if (message.method === "Network.requestWillBeSent" && /tile\.openstreetmap\.org/.test(message.params.request.url)) tileRequestUrls.set(message.params.requestId, { url: message.params.request.url, referer: message.params.request.headers?.Referer || message.params.request.headers?.referer || "" });
      if (message.method === "Network.responseReceived" && tileRequestUrls.has(message.params.requestId)) tileNetworkEvents.push({ ...tileRequestUrls.get(message.params.requestId), status: message.params.response.status });
      if (message.method === "Network.loadingFailed" && tileRequestUrls.has(message.params.requestId)) tileNetworkEvents.push({ ...tileRequestUrls.get(message.params.requestId), error: message.params.errorText, canceled: message.params.canceled, blockedReason: message.params.blockedReason || "", corsErrorStatus: message.params.corsErrorStatus || null });
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
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate(`document.readyState === "complete" && typeof db !== "undefined" && typeof navigate === "function" && typeof ayecSectorMenuModels !== "undefined"`);
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("Web application did not become ready for route rendering.");
    const adminAccess = await evaluate(`(() => {currentAuthUser={id:1,username:"QA Admin",full_name:"QA Admin",role:"Admin",is_admin:true,is_control_admin:true,can_access_control_center:true,permissions:JSON.stringify({mode:"all"})};if(typeof updateCurrentUser==="function")updateCurrentUser(currentAuthUser);if(typeof hideAuth==="function")hideAuth();renderWizard=()=>hideAuth();renderLogin=()=>hideAuth();window.handleUnauthorized=()=>hideAuth();const empty=[];for(const key of ["users","personnel","appointments","customers","vehicles","items","rows","results","data"])Object.defineProperty(empty,key,{value:empty});Object.defineProperty(empty,"ok",{value:true});window.__routeSmokeEmpty=empty;window.__routeSmokeManualContent=${JSON.stringify(manualContent + "\n\n| Column | Value |\n| --- | ---: |\n| Audit table | 42 |")};apiFetch=async url=>String(url).startsWith("/api/desktop/manual/content")?{document:"usage",content:window.__routeSmokeManualContent}:empty;const originalFetch=window.fetch.bind(window);window.fetch=(input,options)=>String(input).includes("/api/desktop/accounting/ledger/page")?Promise.resolve(new Response(JSON.stringify({rows:[],has_more:false}),{status:200,headers:{"Content-Type":"application/json"}})):originalFetch(input,options);return{allowed:canAccessControlCenter(),isControlAdmin:currentAuthUser?.is_control_admin===true,canAccess:currentAuthUser?.can_access_control_center===true,authHidden:document.querySelector("#authRoot")?.hidden===true}})()`);
    const routes = await evaluate(`(() => {const originalSector=currentSector,seen=new Set(),out=[];for(const sector of ["teknik_servis","otomotiv"]){currentSector=sector;renderNav();for(const button of document.querySelectorAll(".sidebar .nav-button[data-page]")){const id=button.dataset.page;if(id&&!seen.has(id)){seen.add(id);out.push({id,sector,desktopPageId:ayecDesktopPageIds[id]??null})}}}if(canAccessControlCenter()&&!seen.has("control-center"))out.push({id:"control-center",sector:"teknik_servis",desktopPageId:null});if(ayecDesktopPageIds.assistant!=null&&!seen.has("assistant"))out.push({id:"assistant",sector:"teknik_servis",desktopPageId:ayecDesktopPageIds.assistant,entryPoint:"header-assistant"});currentSector=originalSector;renderNav();return out})()`);
    if (!Array.isArray(routes) || !routes.length) throw new Error("No mapped leaf page routes were exposed by the sector menus.");
    const desktopRoutes = routes.filter(item => item.id !== "control-center");
    const mappedDesktopPageIds = new Set(desktopRoutes.map(item => item.desktopPageId));
    if (desktopRoutes.length !== 43 || mappedDesktopPageIds.size !== 43 || desktopRoutes.some(item => !Number.isInteger(item.desktopPageId)) || !desktopRoutes.some(item => item.id === "assistant" && item.desktopPageId === 170)) throw new Error(`Desktop page route coverage is incomplete: ${JSON.stringify({ total: desktopRoutes.length, mapped: mappedDesktopPageIds.size, assistant: desktopRoutes.find(item => item.id === "assistant") })}`);
    const results = [];
    let jobReportCurrencyAudit = {};
    const mobileResults = [];
    let dashboardShell = null;
    const originalVisualTheme = await evaluate(`document.documentElement.dataset.theme || ""`);
    await evaluate(`applyTheme("midnight", false)`);
    for (const entry of routes) {
      activeRoute = entry.id;
      if (entry.id === "field-service") {
        await evaluate(`(() => {
          class MockLayer {
            constructor(points, options) { this.points = points || []; this.options = options || {}; this.handlers = {}; }
            addTo(map) { this.map = map; map.layers.push(this); return this; }
            bindPopup() { return this; }
            openPopup() { return this; }
            on(name, handler) { this.handlers[name] = handler; return this; }
            setLatLng(point) { this.points = point; return this; }
            getLatLng() { return { lat: this.points?.[0], lng: this.points?.[1] }; }
            setLatLngs(points) { this.points = points; return this; }
            setStyle(style) { Object.assign(this.options, style); return this; }
            getBounds() { return { points: this.points }; }
          }
          class MockMap {
            constructor(root) { this.root = root; this.layers = []; this.handlers = {}; }
            setView(center, zoom) { this.view = { center, zoom }; return this; }
            on(name, handler) { this.handlers[name] = handler; return this; }
            getContainer() { return this.root; }
            removeLayer(layer) { this.layers = this.layers.filter(item => item !== layer); return this; }
            fitBounds() { return this; }
            flyTo(center, zoom) { this.view = { center, zoom }; return this; }
            invalidateSize() { return this; }
            remove() { this.layers = []; return this; }
            fireClick(lat, lng) { this.handlers.click?.({ latlng: { lat, lng } }); }
          }
          window.__auditFieldMap = null;
          window.L = {
            map(root) { window.__auditFieldMap = new MockMap(root); return window.__auditFieldMap; },
            control: { zoom: () => ({ addTo() { return this; } }) },
            tileLayer: () => new MockLayer(),
            circleMarker: (points, options) => new MockLayer(points, options),
            divIcon: options => options,
            marker: (points, options) => new MockLayer(points, options),
            latLngBounds: points => ({ points }),
            polyline: (points, options) => new MockLayer(points, options)
          };
          return true;
        })()`);
      }
      if (entry.id === "field-service") {
        await evaluate(`(() => {
          const original = apiFetch;
          const rows = [
            {id: 801, customer_name: "Tolga Acar", title: "Klima bakimi", date: "2026-10-18", time: "09:00", status: "Planlandi", phone: "05550000001"},
            {id: 802, customer_name: "Derya Aydin", title: "Kombi arizasi", date: "2026-10-18", time: "10:30", status: "Gorevde", phone: "05550000002"},
            {id: 803, customer_name: "Murat Arslan", title: "Periyodik servis", date: "2026-10-18", time: "11:00", status: "Planlandi", phone: "05550000003"},
            {id: 804, customer_name: "Elif Yilmaz", title: "Sogutma kontrolu", date: "2026-10-18", time: "12:00", status: "Tamamlandi", phone: "05550000004"},
            {id: 805, customer_name: "Can Yilmaz", title: "Cihaz kurulumu", date: "2026-10-18", time: "13:00", status: "Planlandi", phone: "05550000005"},
            {id: 806, customer_name: "Kaan Yilmaz", title: "Bakim ziyareti", date: "2026-10-18", time: "14:00", status: "Bekliyor", phone: "05550000006"},
            {id: 807, customer_name: "Selin Yilmaz", title: "Ariza tespiti", date: "2026-10-18", time: "15:00", status: "Planlandi", phone: "05550000007"},
            {id: 808, customer_name: "Baris Cevik", title: "Acil servis", date: "2026-10-18", time: "16:00", status: "Gorevde", phone: "05550000008"}
          ];
          window.__routeSmokeFieldAppointments = rows;
          apiFetch = async (url, ...args) => String(url).startsWith("/api/desktop/table/appointments")
            ? {table: "appointments", columns: Object.keys(rows[0]), rows, count: rows.length}
            : original(url, ...args);
          return true;
        })()`);
      }
      if (entry.id === "service-list") {
        await evaluate(`(() => {
          window.__routeSmokeOriginalServiceDevices = db.serviceDevices;
          const customers = ["Burak \\u015eahin", "Derya Aydin", "Murat Arslan", "Elif Yilmaz", "Can Yilmaz", "Kaan Yilmaz", "Selin Yilmaz", "Tolga Acar", "Mehmet Kaya", "Zeynep Celik", "Burak Sahin", "Ahmet Yilmaz", "Murat Demir", "Derya Aydin", "Selin Yilmaz"];
          const statuses = ["Teslim Edildi", "Teslim Edildi", "Teslim Edildi", "Teslim Edildi", "Teslim Edildi", "Tamirde", "Teslim Edildi", "Parca Bekliyor", "Teslim Edildi", "Test / Onay", "Teslim Edildi", "Bekliyor", "Kargoya Verildi", "Teslim Edildi", "Teslim Edildi"];
          db.serviceDevices = customers.map((customer_name, index) => {
            const number = 15 - index;
            const suffix = String(number).padStart(4, "0");
            const deviceSuffix = String(number).padStart(2, "0");
            return {id:number,tracking_no:"DEMO-SRV-"+suffix,customer_name,phone:"+90 532 *** ** "+String(number).padStart(2,"0"),device_brand:"AYEC",device_model:"Test Cihaz "+deviceSuffix,serial_no:"AC-994"+deviceSuffix+"-X",entry_date:"2026-09-21",exit_date:index>1?"2026-09-21":"",price:900+number*100,currency:"USD",status:statuses[index],priority:index===7?"Acil":index===5?"D\u00fc\u015f\u00fck":"Normal"};
          });
          return db.serviceDevices.length;
        })()`);
      }
      const result = await evaluate(`(async () => {currentSector=${JSON.stringify(entry.sector)};currentAuthUser=${JSON.stringify(entry.id)}==="control-center"?{id:1,username:"admin",full_name:"Central Admin",role:"Admin",is_admin:true,is_control_admin:true,can_access_control_center:true,permissions:JSON.stringify({mode:"all"})}:{id:1,username:"as",full_name:"Aslan Servis",role:"Admin",is_admin:true,is_control_admin:false,can_access_control_center:false,permissions:JSON.stringify({mode:"all"})};if(typeof updateCurrentUser==="function")updateCurrentUser(currentAuthUser);if(${JSON.stringify(entry.id)}==="job-reports"){window.__routeSmokeApiFetch=apiFetch;const serviceRows=[
{id:15,tracking_no:"DEMO-SRV-0015",customer_name:"Tolga Acar",device_brand:"AYEC",device_model:"Test Cihaz 15",status:"Teslim Edildi",entry_date:"2026-09-21",price:2400,priority:"Normal"},
{id:14,tracking_no:"DEMO-SRV-0014",customer_name:"Derya Aydin",device_brand:"AYEC",device_model:"Test Cihaz 14",status:"Teslime Hazir",entry_date:"2026-09-21",price:2300,priority:"Normal"},
{id:13,tracking_no:"DEMO-SRV-0013",customer_name:"Murat Arslan",device_brand:"AYEC",device_model:"Test Cihaz 13",status:"Test / Onay",entry_date:"2026-09-21",price:2200,priority:"Normal"},
{id:12,tracking_no:"DEMO-SRV-0012",customer_name:"Elif Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 12",status:"Tamirde",entry_date:"2026-09-21",price:2100,priority:"Normal"},
{id:11,tracking_no:"DEMO-SRV-0011",customer_name:"Can Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 11",status:"Bekliyor",entry_date:"2026-09-21",price:2000,priority:"Normal"},
{id:10,tracking_no:"DEMO-SRV-0010",customer_name:"Kaan Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 10",status:"Teslim Edildi",entry_date:"2026-09-21",price:1900,priority:"Normal"},
{id:9,tracking_no:"DEMO-SRV-0009",customer_name:"Selin Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 09",status:"Teslim Edildi",entry_date:"2026-09-21",price:1800,priority:"Normal"},
{id:8,tracking_no:"DEMO-SRV-0008",customer_name:"Baris Cevik",device_brand:"AYEC",device_model:"Test Cihaz 08",status:"Parca Bekliyor",entry_date:"2026-09-21",price:1700,priority:"Acil"},
{id:7,tracking_no:"DEMO-SRV-0007",customer_name:"Mehmet Kaya",device_brand:"AYEC",device_model:"Test Cihaz 07",status:"Teslim Edildi",entry_date:"2026-09-20",price:1600,priority:"Normal"},
{id:6,tracking_no:"DEMO-SRV-0006",customer_name:"Zeynep Celik",device_brand:"AYEC",device_model:"Test Cihaz 06",status:"Test / Onay",entry_date:"2026-09-20",price:1500,priority:"Normal"},
{id:5,tracking_no:"DEMO-SRV-0005",customer_name:"Burak Sahin",device_brand:"AYEC",device_model:"Test Cihaz 05",status:"Tamirde",entry_date:"2026-09-20",price:1400,priority:"Normal"},
{id:4,tracking_no:"DEMO-SRV-0004",customer_name:"Ahmet Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 04",status:"Bekliyor",entry_date:"2026-09-20",price:1300,priority:"Normal"},
{id:3,tracking_no:"DEMO-SRV-0003",customer_name:"Cemre Ekin",device_brand:"AYEC",device_model:"Test Cihaz 03",status:"Teslim Edildi",entry_date:"2026-09-20",price:1200,priority:"Normal"},
{id:2,tracking_no:"DEMO-SRV-0002",customer_name:"Aksoy Medya A.S.",device_brand:"AYEC",device_model:"Test Cihaz 02",status:"Teslim Edildi",entry_date:"2026-09-20",price:1100,priority:"Normal"},
{id:1,tracking_no:"DEMO-SRV-0001",customer_name:"Ahmet Yilmaz",device_brand:"AYEC",device_model:"Test Cihaz 01",status:"Teslim Edildi",entry_date:"2026-09-20",price:1000,priority:"Normal"}];const transactions=[
{id:1,customer_id:1,transaction_type:"DEBIT",amount:1800,currency:"TRY",exchange_rate:1,try_equivalent:1800,description:"Accepted Offer Service",tracking_no:"DEMO-SRV-0001",created_at:"2026-09-21 09:00:00",current_balance:0},
{id:2,customer_id:2,transaction_type:"DEBIT",amount:2009,currency:"TRY",exchange_rate:1,try_equivalent:2009,description:"Thermal pad replacement",tracking_no:"DEMO-SRV-0002",created_at:"2026-09-21 09:00:00",current_balance:0},
{id:3,customer_id:3,transaction_type:"DEBIT",amount:1700,currency:"USD",exchange_rate:1,try_equivalent:1700,description:"AYEC Test Device 08 - SMD repair",tracking_no:"DEMO-SRV-0008",created_at:"2026-09-21 09:00:00",current_balance:1700},
{id:4,customer_id:4,transaction_type:"DEBIT",amount:2207,currency:"TRY",exchange_rate:1,try_equivalent:2207,description:"Industrial UPS battery service",tracking_no:"DEMO-SRV-0003",created_at:"2026-09-21 09:00:00",current_balance:0},
{id:5,customer_id:5,transaction_type:"DEBIT",amount:4583,currency:"TRY",exchange_rate:1,try_equivalent:4583,description:"Power board revision",tracking_no:"DEMO-SRV-0015",created_at:"2026-09-21 09:00:00",current_balance:0},
{id:6,customer_id:6,transaction_type:"DEBIT",amount:2175,currency:"TRY",exchange_rate:1,try_equivalent:2175,description:"Screen repair and diagnostics",tracking_no:"DEMO-SRV-0004",created_at:"2026-09-21 09:00:00",current_balance:2175}];apiFetch=async function(url,...args){const value=String(url);if(value.includes("/api/desktop/table/devices"))return{rows:serviceRows,count:serviceRows.length,columns:Object.keys(serviceRows[0])};if(value.includes("/api/desktop/table/currency_transactions"))return{rows:transactions,count:transactions.length,columns:Object.keys(transactions[0])};return window.__routeSmokeApiFetch(url,...args)}}if(${JSON.stringify(entry.id)}==="services"){window.__routeSmokeOriginalCustomers=db.customers;const serviceRows=[["0015","Burak Sahin","Teslim Edildi",2400,"Normal","2026-09-21"],["0014","Derya Aydin","Teslime Hazir",2300,"Normal","2026-09-21"],["0013","Murat Arslan","Test / Onay",2200,"Normal","2026-09-21"],["0012","Elif Yilmaz","Tamirde",2100,"Normal","2026-09-21"],["0011","Can Yilmaz","Bekliyor",2000,"Normal","2026-09-21"],["0010","Kaan Yilmaz","Teslim Edildi",1900,"Normal","2026-09-21"],["0009","Selin Yilmaz","Teslim Edildi",1800,"Normal","2026-09-21"],["0008","Tolga Acar","Parca Bekliyor",1700,"Acil","2026-09-21"],["0007","Mehmet Kaya","Teslim Edildi",1600,"Normal","2026-09-20"],["0006","Zeynep Celik","Test / Onay",1500,"Normal","2026-09-20"],["0005","Burak Sahin","Tamirde",1400,"Normal","2026-09-20"],["0004","Ahmet Yilmaz","Bekliyor",1300,"Normal","2026-09-20"],["0003","Murat Demir","Teslim Edildi",1200,"Normal","2026-09-20"],["0002","Derya Aydin","Teslim Edildi",1100,"Normal","2026-09-20"],["0001","Selin Yilmaz","Teslim Edildi",1000,"Normal","2026-09-20"]];db.customers=serviceRows.map(([number,name,status,price,urgency,date])=>({id:Number(number),name,phone:"",services:[{no:"DEMO-SRV-"+number,device_brand:"AYEC",device_model:"Test Cihaz "+number.slice(-2),status,entry_date:date,date,price,urgency,priority:urgency,fault_description:""}]}))}renderNav();let button=Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item=>item.dataset.page===${JSON.stringify(entry.id)});let submenu=button?.closest(".submenu");if(submenu&&!submenu.classList.contains("open")){const parent=Array.from(document.querySelectorAll("#nav .nav-parent")).find(item=>item.dataset.parent===submenu.id);parent?.click()}button=Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item=>item.dataset.page===${JSON.stringify(entry.id)});if(${JSON.stringify(entry.id)}==="control-center")navigate("control-center");else if(button)button.click();else if(${JSON.stringify(entry.id)}==="assistant")navigate("assistant");await new Promise(resolve=>setTimeout(resolve,90));const content=document.querySelector("#content"),title=document.querySelector("#pageTitle"),root=document.querySelector(".app-shell");return{route:${JSON.stringify(entry.id)},page:page||"",dataPage:document.body.dataset.page||"",theme:document.documentElement.dataset.theme||"",palette:{bg:getComputedStyle(document.documentElement).getPropertyValue("--bg").trim(),surface:getComputedStyle(document.documentElement).getPropertyValue("--surface").trim()},bodyBackground:getComputedStyle(document.body).backgroundColor,bodyImage:getComputedStyle(document.body).backgroundImage,contentBackground:content?getComputedStyle(content).backgroundColor:"",lightPanels:[...document.querySelectorAll(".app-shell *")].map(node=>{const r=node.getBoundingClientRect(),bg=getComputedStyle(node).backgroundColor;return{tag:node.tagName,id:node.id,className:typeof node.className==="string"?node.className:"",bg,area:Math.round(r.width*r.height),bounds:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}}).filter(item=>item.bg==="rgb(255, 255, 255)"&&item.area>12000).sort((a,b)=>b.area-a.area).slice(0,8),bottomLayers:[[20,780],[650,780],[1280,780],[20,840],[650,840],[1280,840]].map(([x,y])=>({point:[x,y],layers:document.elementsFromPoint(x,y).slice(0,5).map(node=>{const r=node.getBoundingClientRect();return{tag:node.tagName,id:node.id,className:typeof node.className==="string"?node.className:"",bg:getComputedStyle(node).backgroundColor,rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}})})),shortcutColumns:(()=>{const grid=document.querySelector(".dashboard-shortcut-grid");return grid?getComputedStyle(grid).gridTemplateColumns.split(" ").length:0})(),jobActionIcons:document.querySelectorAll(".job-report-actions svg").length,jobHeaderLayout:(()=>{const host=document.querySelector(".job-report-heading .actions"),title=document.querySelector(".job-report-heading>div:first-child"),rect=node=>{const r=node?.getBoundingClientRect();return r?{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}:null},box=rect(host),titleBox=rect(title),contentBox=rect(document.querySelector("#content")),items=[...(host?.children||[])].map(rect).filter(Boolean),rows=[...new Set([...(host?.children||[])].map(node=>getComputedStyle(node).gridRowStart))].length,inside=!!box&&!!contentBox&&items.length===6&&box.right<=contentBox.right+1&&items.every(item=>item.x>=box.x-1&&item.y>=box.y-1&&item.right<=box.right+1&&item.bottom<=box.bottom+1),overlap=items.some((a,index)=>items.slice(index+1).some(b=>a.x<b.right-1&&a.right>b.x+1&&a.y<b.bottom-1&&a.bottom>b.y+1));return{width:box?.width||0,height:box?.height||0,rows,inside,noOverlap:!overlap,titleClear:!!titleBox&&!!box&&titleBox.right<=box.x,items:[...(host?.children||[])].map(node=>({className:node.className,gridColumn:getComputedStyle(node).gridColumnStart,gridRow:getComputedStyle(node).gridRowStart,rect:rect(node)}))}})(),manualLoaded:(document.querySelector("#manualDocument")?.innerText||"").includes("Guncel Kullanici Kilavuzu"),manualHeadingCount:document.querySelectorAll("#manualDocument h1,#manualDocument h2,#manualDocument h3").length,manualTableCount:document.querySelectorAll("#manualDocument table").length,manualTableCells:document.querySelector("#manualDocument table tbody tr")?.innerText||"",manualGeometry:(()=>{const rect=selector=>{const r=document.querySelector(selector)?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{title:rect(".manual-reference-head h2"),tabs:rect(".manual-tabs"),document:rect(".manual-document")}})(),jobSummary:(()=>{const get=id=>document.querySelector(id)?.textContent?.trim()||"";return{total:get("#jobReportTotal"),open:get("#jobReportOpen"),paid:get("#jobReportPaid"),services:get("#jobReportServiceCount")}})(),jobFooter:(()=>{const label=document.querySelector(".job-report-summary article:nth-child(3) small");return label?{text:label.textContent.trim(),color:getComputedStyle(label).color,fontSize:getComputedStyle(label).fontSize,labelRect:(()=>{const r=label.getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}})(),cardRect:(()=>{const r=label.closest("article").getBoundingClientRect();return{x:r.x,y:r.y,width:r.width,height:r.height}})()}:null})(),jobTableTypography:(()=>{const row=document.querySelector(".job-report-table tbody tr");return [...(row?.cells||[])].map(cell=>{const r=cell.getBoundingClientRect(),style=getComputedStyle(cell);return{text:cell.innerText.trim(),font:style.font,fontSize:style.fontSize,width:Math.round(r.width),rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}})})(),jobCustomerWrap:(()=>{const node=document.querySelector(".job-report-table tbody tr:nth-child(2) td:nth-child(2) .job-report-customer");if(!node)return null;const r=node.getBoundingClientRect();return{maxWidth:getComputedStyle(node).maxWidth,height:r.height,text:node.innerText.trim()}})(),title:title?.textContent?.trim()||"",contentChars:(content?.innerText||"").trim().length,contentWidth:content?.getBoundingClientRect().width||0,rootVisible:!!root&&getComputedStyle(root).display!=="none",appShellBounds:(()=>{const r=root?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null})(),authState:(()=>{const n=document.querySelector("#authRoot"),s=n?getComputedStyle(n):null;return{hidden:n?.hidden,htmlLength:n?.innerHTML.length||0,zIndex:s?.zIndex,display:s?.display,visibility:s?.visibility,bodyClass:document.body.className}})()}})()`);
      result.authSuppressed = await evaluate(`(() => {const root=document.querySelector("#authRoot");if(root&&!root.hidden)hideAuth();return !root||root.hidden})()`);
      if (!result.authSuppressed) throw new Error(`Authentication overlay was not suppressed for ${entry.id}.`);
      if (entry.id === "service-list") {
        result.serviceListFixture = await evaluate(`(() => {const tab=document.querySelector('[data-service-tab="all"]'),rows=[...document.querySelectorAll(".service-list-table tbody tr[data-kind=service]")],row=rows[0],status=row?.querySelector(".service-list-status"),box=node=>{const r=node?.getBoundingClientRect();return r?[Math.round(r.width),Math.round(r.height)]:null};return{allCount:tab?.querySelector("b")?.textContent||"",visibleRows:rows.length,customers:rows.slice(0,5).map(row=>row.cells[2]?.querySelector("strong")?.textContent||""),firstStatus:status?.getAttribute("aria-label")||"",firstStatusVisual:status?.textContent||"",statusSize:box(status),phone:row?.cells[2]?.querySelector("small")?.textContent||"",prices:rows.slice(0,5).map(row=>row.cells[6]?.textContent.trim()||""),metrics:[...document.querySelectorAll(".service-list-metric")].slice(0,4).map(item=>item.querySelector("strong")?.textContent.trim()||""),rowSize:box(row),columnWidths:[...row?.cells||[]].map(cell=>Math.round(cell.getBoundingClientRect().width)),columnLefts:[...row?.cells||[]].map(cell=>Math.round(cell.getBoundingClientRect().left)),actionSizes:[...row?.querySelectorAll(".service-list-actions button")||[]].slice(0,3).map(box),tableScrollWidth:document.querySelector(".service-list-table-wrap")?.scrollWidth||0,tableClientWidth:document.querySelector(".service-list-table-wrap")?.clientWidth||0}})()`);
        if (result.serviceListFixture.allCount !== "15" || result.serviceListFixture.visibleRows !== 15 || result.serviceListFixture.customers[0] !== "Burak \u015eahin" || result.serviceListFixture.firstStatus !== "Teslim Edildi" || result.serviceListFixture.firstStatusVisual !== "TESL\u0130M\nED\u0130LD\u0130" || result.serviceListFixture.statusSize?.[1] !== 30 || result.serviceListFixture.phone !== "+90 532 *** ** 15" || result.serviceListFixture.prices[0] !== "2,400.00 $" || JSON.stringify(result.serviceListFixture.metrics) !== JSON.stringify(["1 Cihaz","1 Cihaz","0 Cihaz","1 Paket"]) || result.serviceListFixture.rowSize?.[1] !== 70 || result.serviceListFixture.columnWidths?.some((width,index)=>Math.abs(width-[40,86,97,112,92,92,71,107,71,250][index])>1) || result.serviceListFixture.actionSizes[0]?.[0] !== 21 || result.serviceListFixture.actionSizes[0]?.[1] !== 21 || result.serviceListFixture.tableScrollWidth > result.serviceListFixture.tableClientWidth + 1) throw new Error(`Service-list populated fixture or table geometry diverged from the native table: ${JSON.stringify(result.serviceListFixture)}`);
        result.serviceListTypography = await evaluate(`(() => {const row=document.querySelector(".service-list-table tbody tr"),style=node=>{const value=getComputedStyle(node);return{fontSize:value.fontSize,fontWeight:value.fontWeight,fontFamily:value.fontFamily,whiteSpace:value.whiteSpace}};return{tracking:style(row?.cells[1]?.querySelector(".service-list-ticket")),entryDate:style(row?.cells[4]),price:style(row?.cells[6]?.querySelector(".service-list-price")),status:style(row?.cells[7]?.querySelector(".service-list-status"))}})()`);
        if (result.serviceListTypography.tracking?.fontSize !== "11px" || result.serviceListTypography.tracking?.fontWeight !== "700" || result.serviceListTypography.entryDate?.fontSize !== "11px" || result.serviceListTypography.entryDate?.fontWeight !== "400" || result.serviceListTypography.entryDate?.whiteSpace !== "nowrap" || result.serviceListTypography.price?.fontSize !== "11px" || result.serviceListTypography.price?.fontWeight !== "700" || result.serviceListTypography.status?.fontSize !== "8px" || result.serviceListTypography.status?.fontWeight !== "800") throw new Error(`Service-list typography diverged from the native reference: ${JSON.stringify(result.serviceListTypography)}`);
        result.serviceListUrgency = await evaluate(`(() => {const high=document.querySelector('.service-list-table tbody tr[data-id="DEMO-SRV-0008"] .service-list-priority'),low=document.querySelector('.service-list-table tbody tr[data-id="DEMO-SRV-0010"] .service-list-priority'),normal=document.querySelector('.service-list-table tbody tr[data-id="DEMO-SRV-0014"] .service-list-priority'),style=node=>{if(!node)return null;const value=getComputedStyle(node),rect=node.getBoundingClientRect();return{label:node.textContent.trim(),className:node.className,height:Math.round(rect.height),fontSize:value.fontSize,fontWeight:value.fontWeight,background:value.backgroundColor,color:value.color}};return{high:style(high),low:style(low),normal:style(normal)}})()`);
        if (result.serviceListUrgency.high?.label !== "Acil" || !result.serviceListUrgency.high?.className.includes("priority-high") || result.serviceListUrgency.high?.height !== 18 || result.serviceListUrgency.high?.fontSize !== "8px" || result.serviceListUrgency.high?.fontWeight !== "800" || result.serviceListUrgency.high?.background !== "rgb(113, 63, 18)" || result.serviceListUrgency.high?.color !== "rgb(252, 211, 77)" || result.serviceListUrgency.low?.label !== "D\u00fc\u015f\u00fck" || !result.serviceListUrgency.low?.className.includes("priority-low") || result.serviceListUrgency.low?.height !== 18 || result.serviceListUrgency.low?.fontSize !== "8px" || result.serviceListUrgency.low?.background !== "rgba(0, 0, 0, 0)" || result.serviceListUrgency.low?.color !== "rgb(170, 182, 200)" || result.serviceListUrgency.normal?.className.includes("priority-high") || result.serviceListUrgency.normal?.height !== 18) throw new Error(`Service-list urgency badges diverged from native warning/low/normal treatments: ${JSON.stringify(result.serviceListUrgency)}`);
        result.serviceListTabs = await evaluate(`(() => {const node=document.querySelector(".service-list-tabs"),table=document.querySelector(".service-list-table-wrap");const r=node?.getBoundingClientRect();return{scrollWidth:node?.scrollWidth||0,clientWidth:node?.clientWidth||0,tableScrollWidth:table?.scrollWidth||0,tableClientWidth:table?.clientWidth||0,rect:r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null,tabCount:node?.querySelectorAll(".service-list-tab").length||0}})()`);
        if (!result.serviceListTabs.tabCount || result.serviceListTabs.scrollWidth > result.serviceListTabs.clientWidth + 1 || result.serviceListTabs.tableScrollWidth > result.serviceListTabs.tableClientWidth + 1) throw new Error(`Service-list tabs or table overflow their desktop content row: ${JSON.stringify(result.serviceListTabs)}`);
      }
      if (entry.id === "field-service") {
        result.fieldServiceFixture = await evaluate(`(() => {
          const jobs = document.querySelector("[data-field-panel-mode='jobs']");
          const status = document.querySelector("#fieldMapStatus");
          const search = document.querySelector("#genericSearch");
          jobs?.click();
          const all = {count:document.querySelector("#fieldMapCount")?.textContent||"",rows:document.querySelectorAll(".field-map-job").length};
          status.value = "done";
          status.dispatchEvent(new Event("change",{bubbles:true}));
          const done = {count:document.querySelector("#fieldMapCount")?.textContent||"",rows:document.querySelectorAll(".field-map-job").length};
          status.value = "all";
          status.dispatchEvent(new Event("change",{bubbles:true}));
          search.value = "Acil";
          search.dispatchEvent(new Event("input",{bubbles:true}));
          const searchResult = {count:document.querySelector("#fieldMapCount")?.textContent||"",customer:document.querySelector(".field-map-job b")?.textContent||""};
          search.value = "";
          search.dispatchEvent(new Event("input",{bubbles:true}));
          document.querySelector("[data-field-panel-mode='customer']")?.click();
          return {all,done,searchResult,labels:[...document.querySelectorAll("[data-field-panel-mode]")].map(button=>button.textContent.trim()),defaultPanel:document.querySelector("[data-field-customer-location]")?.hidden===false};
        })()`);
        if (result.fieldServiceFixture.all.count !== "8" || result.fieldServiceFixture.all.rows !== 8 || result.fieldServiceFixture.done.count !== "1" || result.fieldServiceFixture.done.rows !== 1 || result.fieldServiceFixture.searchResult.count !== "1" || result.fieldServiceFixture.searchResult.customer !== "Baris Cevik" || !result.fieldServiceFixture.labels.some(label => label.includes("\u0130\u015f Emirleri")) || !result.fieldServiceFixture.defaultPanel) throw new Error(`Field-service appointment queue, status filter, search, or customer panel failed: ${JSON.stringify(result.fieldServiceFixture)}`);
      }
      result.headerContextAudit = await evaluate(`(()=>({adminHeader:!!document.querySelector("#adminHeaderUser"),productContext:!!document.querySelector("#adminProductContext"),userInitial:document.querySelector("#currentUserInitial")?.textContent||""}))()`);
      const isControlCenterRoute = entry.id === "control-center";
      if (result.headerContextAudit.adminHeader !== isControlCenterRoute || result.headerContextAudit.productContext !== isControlCenterRoute) throw new Error(`Route rendered the wrong tenant or central-admin header context: ${JSON.stringify({ route: entry.id, header: result.headerContextAudit })}`);
      if (entry.id === "pc-builder") {
        result.headerLayout = await evaluate(`(() => {const bounds=selector=>{const rect=document.querySelector(selector)?.getBoundingClientRect();return rect?{x:Math.round(rect.x),width:Math.round(rect.width)}:null},title=document.querySelector(".topbar #pageTitle");return{title:bounds(".topbar>div:first-of-type"),titleOverflow:getComputedStyle(title).textOverflow,search:bounds(".topbar .global-search-wrap")}})()`);
        if (result.headerLayout?.title?.x !== 174 || result.headerLayout?.title?.width !== 116 || result.headerLayout?.titleOverflow !== "ellipsis" || result.headerLayout?.search?.x !== 304 || result.headerLayout?.search?.width !== 150) throw new Error(`Desktop breadcrumb and global search bounds differ from the native header: ${JSON.stringify(result.headerLayout)}`);
      }
      if (entry.id === "dashboard") {
        await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
        await delay(30);
        const shortcutColumnsAt1280 = await evaluate(`document.querySelector(".dashboard-shortcut-grid") ? getComputedStyle(document.querySelector(".dashboard-shortcut-grid")).gridTemplateColumns.split(" ").length : 0`);
        if (shortcutColumnsAt1280 !== 2) throw new Error(`Dashboard shortcuts should follow the native two-column layout at 1280px: ${shortcutColumnsAt1280}`);
        result.shortcutColumnsAt1280 = shortcutColumnsAt1280;
        const shortcutCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        fs.writeFileSync(path.join(outputDir, "dashboard-shortcuts-1280x800.png"), Buffer.from(shortcutCapture.data, "base64"));
        await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
        await delay(30);
      }
      if (entry.id === "services") {
        result.serviceBoardParity = await evaluate(`(() => {
          const lanes=[...document.querySelectorAll(".service-board-lane")].map(lane=>Number(lane.querySelector("header>b")?.textContent||0));
          const summary=[...document.querySelectorAll(".service-board-summary b")].map(node=>node.textContent.trim());
          const readyCard=[...document.querySelectorAll(".service-board-card")].find(card=>card.dataset.id==="DEMO-SRV-0014");
          return{lanes,summary,readyIsActive:!serviceComplete({status:"Teslime Hazir"}),deliveredIsComplete:serviceComplete({status:"Teslim Edildi"}),readyCard:readyCard?{title:readyCard.querySelector("h3")?.textContent||"",description:readyCard.querySelector("p")?.textContent||"",status:readyCard.querySelector(".service-board-status")?.textContent.trim()||"",priority:readyCard.querySelector(".service-board-priority")?.textContent.trim()||"",price:readyCard.querySelector(".service-board-price")?.textContent.trim()||""}:null,priceCardCount:document.querySelectorAll(".service-board-price").length};
        })()`);
        const audit=result.serviceBoardParity;
        if(JSON.stringify(audit?.lanes)!==JSON.stringify([2,2,1,2,1])||audit?.summary?.[0]!=="8"||audit?.summary?.[2]!=="0"||audit?.summary?.[3]!=="14,500.00 \u20ba"||!audit?.readyIsActive||!audit?.deliveredIsComplete||audit?.readyCard?.title!=="AYEC Test Cihaz 14"||audit?.readyCard?.description!=="AYEC Test Cihaz 14"||audit?.readyCard?.status!=="Teslime Hazir"||audit?.readyCard?.priority!=="Normal"||audit?.readyCard?.price!=="2,300.00 \u20ba"||audit?.priceCardCount!==8) throw new Error(`Service board parity fixture diverged from the native active-device board: ${JSON.stringify(audit)}`);
        result.serviceBoardFilterWorkflow = await evaluate(`(() => {const total=document.querySelectorAll(".service-board-card").length,urgent=document.querySelector('[data-service-board-filter="urgent"]');urgent?.click();const urgentCount=document.querySelectorAll(".service-board-card").length,urgentActive=document.querySelector('[data-service-board-filter="urgent"]')?.classList.contains("active")||false;document.querySelector('[data-service-board-filter="all"]')?.click();const allCount=document.querySelectorAll(".service-board-card").length,search=document.querySelector("#serviceBoardSearch");search.value="DEMO-SRV-0014";search.dispatchEvent(new Event("input",{bubbles:true}));const searchCount=document.querySelectorAll(".service-board-card").length,searchValue=document.querySelector("#serviceBoardSearch")?.value||"";const resetSearch=document.querySelector("#serviceBoardSearch");resetSearch.value="";resetSearch.dispatchEvent(new Event("input",{bubbles:true}));return{total,urgentCount,urgentActive,allCount,searchCount,searchValue,restoredCount:document.querySelectorAll(".service-board-card").length}})()`);
        const boardFilter=result.serviceBoardFilterWorkflow;
        if (boardFilter.total !== 8 || !boardFilter.urgentActive || boardFilter.urgentCount >= boardFilter.total || boardFilter.allCount !== 8 || boardFilter.searchCount !== 1 || boardFilter.searchValue !== "DEMO-SRV-0014" || boardFilter.restoredCount !== 8) throw new Error(`Service board urgent filter or search did not preserve its fixture results: ${JSON.stringify(boardFilter)}`);
        result.serviceBoardCardActions = {};
        result.serviceBoardCardActions.technician = await evaluate(`(async () => {const card=[...document.querySelectorAll(".service-board-card")].find(item=>item.dataset.id==="DEMO-SRV-0014"),dialog=document.querySelector("#appDialog");if(!card||!dialog)return{available:false};card.querySelector('[data-action="technician-open"]')?.click();for(let attempt=0;attempt<100&&!dialog.open;attempt++)await new Promise(resolve=>setTimeout(resolve,20));const form=document.querySelector("#dialogForm"),title=document.querySelector("#dialogTitle")?.textContent||"";return{available:true,open:dialog.open,title,hasStatus:Boolean(form?.elements.namedItem("status")),hasFault:Boolean(form?.elements.namedItem("fault_description")),hasLabor:Boolean(form?.elements.namedItem("labor_cost"))}})()`);
        await evaluate(`document.querySelector("#appDialog")?.close("cancel")`);
        await delay(30);
        result.serviceBoardCardActions.detail = await evaluate(`(() => {const card=[...document.querySelectorAll(".service-board-card")].find(item=>item.dataset.id==="DEMO-SRV-0014"),dialog=document.querySelector("#appDialog");if(!card||!dialog)return{available:false};card.querySelector('[data-action="service-detail"]')?.click();return{available:true,open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent||"",hasDetails:Boolean(dialog.querySelector("#servicePrintArea"))}})()`);
        await evaluate(`document.querySelector("#appDialog")?.close("cancel")`);
        const cardActions=result.serviceBoardCardActions;
        if (!cardActions.technician.available || !cardActions.technician.open || !cardActions.technician.title.includes("DEMO-SRV-0014") || cardActions.technician.title.toLowerCase().includes("undefined") || !cardActions.technician.hasStatus || !cardActions.technician.hasFault || !cardActions.technician.hasLabor || !cardActions.detail.available || !cardActions.detail.open || !cardActions.detail.title.includes("DEMO-SRV-0014") || !cardActions.detail.hasDetails) throw new Error(`Service board detail or technician actions did not open their desktop-equivalent forms: ${JSON.stringify(cardActions)}`);
        result.serviceBoardContextWorkflow = await evaluate(`(async () => {const original=db.settings.contextMenu,card=[...document.querySelectorAll(".service-board-card")].find(item=>item.dataset.id==="DEMO-SRV-0014"),dialog=document.querySelector("#appDialog"),menu=document.querySelector("#contextMenu");if(!card||!dialog||!menu)return{available:false};db.settings.contextMenu=true;card.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:200,clientY:200}));const options=[...menu.querySelectorAll("[data-service-context]")].map(button=>button.dataset.serviceContext);menu.querySelector('[data-service-context="technician"]')?.click();for(let attempt=0;attempt<100&&!dialog.open;attempt++)await new Promise(resolve=>setTimeout(resolve,20));const audit={available:true,menuOpen:menu.classList.contains("open"),options,dialogOpen:dialog.open,title:document.querySelector("#dialogTitle")?.textContent||"",hasStatus:Boolean(document.querySelector("#dialogForm")?.elements.namedItem("status")),hasFault:Boolean(document.querySelector("#dialogForm")?.elements.namedItem("fault_description"))};if(dialog.open)dialog.close("cancel");db.settings.contextMenu=original;return audit})()`);
        const boardContext=result.serviceBoardContextWorkflow;
        if (!boardContext.available || boardContext.menuOpen || JSON.stringify(boardContext.options)!==JSON.stringify(["form","technician","print"]) || !boardContext.dialogOpen || !boardContext.title.includes("DEMO-SRV-0014") || !boardContext.hasStatus || !boardContext.hasFault) throw new Error(`Service board context action did not open the expected technician workflow: ${JSON.stringify(boardContext)}`);
        result.serviceBoardContextActions = await evaluate(`(async () => {const originalSetting=db.settings.contextMenu,originalPrint=window.print,dialog=document.querySelector("#appDialog"),menu=document.querySelector("#contextMenu"),findCard=()=>[...document.querySelectorAll(".service-board-card")].find(item=>item.dataset.id==="DEMO-SRV-0014"),openMenu=()=>findCard()?.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:200,clientY:200}));let printCount=0;try{db.settings.contextMenu=true;openMenu();menu.querySelector('[data-service-context="form"]')?.click();for(let attempt=0;attempt<100&&!dialog.open;attempt++)await new Promise(resolve=>setTimeout(resolve,20));const form={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent||"",hasDetails:Boolean(dialog.querySelector("#servicePrintArea"))};if(dialog.open)dialog.close("cancel");await new Promise(resolve=>setTimeout(resolve,30));window.print=()=>{printCount++};openMenu();menu.querySelector('[data-service-context="print"]')?.click();for(let attempt=0;attempt<100&&(!dialog.open||!printCount);attempt++)await new Promise(resolve=>setTimeout(resolve,20));return{form,print:{open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent||"",printCount}}}finally{window.print=originalPrint;if(dialog?.open)dialog.close("cancel");db.settings.contextMenu=originalSetting}})()`);
        const contextActions=result.serviceBoardContextActions;
        if (!contextActions.form.open || !contextActions.form.title.includes("DEMO-SRV-0014") || !contextActions.form.hasDetails || !contextActions.print.open || !contextActions.print.title.includes("DEMO-SRV-0014") || contextActions.print.printCount !== 1) throw new Error(`Service board context form or print action failed: ${JSON.stringify(contextActions)}`);
        result.serviceIntakeValidation = await evaluate(`(() => {
          window.__routeSmokeOriginalServiceApiFetch=apiFetch;
          window.__routeSmokeServiceApiCalls=[];
          apiFetch=async(url,options={})=>{window.__routeSmokeServiceApiCalls.push({url:String(url),method:String(options.method||"GET").toUpperCase()});return{rows:[],count:0,columns:[]}};
          db.customers[0].phone="+90 555 000 0015";db.customers[0].tc_no="10000000015";
          serviceDialog();
          const dialog=document.querySelector("#appDialog"),form=document.querySelector("#dialogForm"),required=[...form.querySelectorAll("[required]")].map(node=>node.name).sort();
          const customer=db.customers[0],picker=form.querySelector(".service-customer-search");picker.value=customer.name;picker.dispatchEvent(new Event("input",{bubbles:true}));
          const registeredCustomerSelection={id:form.elements.namedItem("customerId").value,name:form.elements.namedItem("customer_name").value,phone:form.elements.namedItem("customer_phone_input").value,state:form.querySelector(".service-form-state")?.textContent||""};
          picker.value="";picker.dispatchEvent(new Event("input",{bubbles:true}));
          const newCustomerState=form.querySelector(".service-form-state")?.textContent||"";
          document.querySelector("#dialogSubmit").click();
          const warranty=form.elements.namedItem("warranty_status"),warrantyOptions=[...warranty.options].map(option=>option.textContent.trim());
          const audit={open:dialog.open,title:document.querySelector("#dialogTitle")?.textContent||"",required,registeredCustomerSelection,newCustomerState,warrantyOptions,warrantyRequired:warranty.required,warrantyDefault:warranty.value,apiCalls:window.__routeSmokeServiceApiCalls,invalidCount:[...form.querySelectorAll(":invalid")].length,submitLabel:document.querySelector("#dialogSubmit")?.textContent.trim()||""};
          dialog.close("cancel");apiFetch=window.__routeSmokeOriginalServiceApiFetch;delete window.__routeSmokeOriginalServiceApiFetch;
          return audit;
        })()`);
        if(!result.serviceIntakeValidation.open||!result.serviceIntakeValidation.title.includes("Yeni Servis")||!result.serviceIntakeValidation.required.includes("customer_name")||!result.serviceIntakeValidation.required.includes("fault")||!result.serviceIntakeValidation.required.includes("warranty_status")||JSON.stringify(result.serviceIntakeValidation.warrantyOptions)!==JSON.stringify(["Garantili","Garanti Dışı","Bilinmiyor"])||!result.serviceIntakeValidation.warrantyRequired||result.serviceIntakeValidation.warrantyDefault!=="Garantili"||!result.serviceIntakeValidation.registeredCustomerSelection.id||result.serviceIntakeValidation.registeredCustomerSelection.name!=="Burak Sahin"||result.serviceIntakeValidation.registeredCustomerSelection.phone!=="+90 555 000 0015"||result.serviceIntakeValidation.registeredCustomerSelection.state===result.serviceIntakeValidation.newCustomerState||result.serviceIntakeValidation.apiCalls.some(call=>call.method==="POST")||result.serviceIntakeValidation.invalidCount<1||!result.serviceIntakeValidation.submitLabel.includes("Kaydı Tamamla")) throw new Error(`Service intake customer selection or required-field validation failed: ${JSON.stringify(result.serviceIntakeValidation)}`);
        result.serviceIntakeSaveWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,customers:db.customers.slice(),activities:db.activities};
          const calls=[];
          try {
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);if(call.url.includes("/table/customers")&&call.method==="POST")return{id:9801};if(call.url.includes("/table/devices")&&call.method==="POST")return{id:9802};return{rows:[],count:0,columns:[]}};
            hydrateDesktop=async()=>{const device=calls.find(call=>call.method==="POST"&&call.url.includes("/table/devices"))?.body,owner=db.customers.find(customer=>String(customer.id)==="9801");if(device&&owner)owner.services.push({id:"9802",no:device.tracking_no,device:"Acer Aspire 7",serial:"PARITY-001",date:device.entry_date,status:device.status,note:device.fault_description,inspection_summary:device.inspection_summary,price:device.price,used_parts:[]});return true};toast=()=>{};
            serviceDialog();
            const form=document.querySelector("#dialogForm");
            form.elements.namedItem("customer_name").value="Parity Intake Customer";
            form.elements.namedItem("customer_phone_input").value="+90 555 010 2030";
            form.elements.namedItem("device_type").value="Laptop / Notebook";
            form.elements.namedItem("brand").value="Acer";
            form.elements.namedItem("model").value="Aspire 7";
            form.elements.namedItem("serial").value="PARITY-001";
            form.elements.namedItem("fault").value="Intermittent display failure";
            form.elements.namedItem("repair_details").value="Customer status update";
            form.elements.namedItem("internal_notes").value="Internal diagnostic note";
            form.elements.namedItem("inspection_summary").value="Bench test summary";
            form.elements.namedItem("price").value="1250";
            form.elements.namedItem("open_form").checked=true;
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,120));
            const posts=calls.filter(call=>call.method==="POST");
            const dialog=document.querySelector("#appDialog"),result={title:document.querySelector("#dialogTitle")?.textContent||"",detailOpen:dialog?.open||false,detailTitle:document.querySelector("#dialogTitle")?.textContent||"",detailActions:["servicePrintBtn","serviceTechBtn","serviceCloseBtn"].map(id=>!!document.getElementById(id)),inspectionSummaryVisible:(document.querySelector("#dialogBody")?.innerText||"").includes("Bench test summary"),postCount:posts.length,customer:posts.find(call=>call.url.includes("/table/customers"))?.body||null,device:posts.find(call=>call.url.includes("/table/devices"))?.body||null,readCalls:calls.filter(call=>call.method==="GET").map(call=>call.url)};
            document.querySelector("#serviceCloseBtn")?.click();
            return result;
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const intake=result.serviceIntakeSaveWorkflow;
        if(intake?.postCount!==2||intake?.customer?.name!=="Parity Intake Customer"||intake?.customer?.phone!=="+90 555 010 2030"||intake?.device?.customer_id!==9801||intake?.device?.customer_name!=="Parity Intake Customer"||intake?.device?.customer_phone!=="+90 555 010 2030"||intake?.device?.device_type!=="Laptop / Notebook"||intake?.device?.device_brand!=="Acer"||intake?.device?.device_model!=="Aspire 7"||intake?.device?.serial_no!=="PARITY-001"||!intake?.device?.fault_description.includes("Intermittent display failure")||!intake?.device?.fault_description.includes("[NOT]: Customer status update")||!intake?.device?.fault_description.includes("[TEKN\u0130K]: Internal diagnostic note")||intake?.device?.repair_details!=="Customer status update"||intake?.device?.internal_notes!=="Internal diagnostic note"||intake?.device?.inspection_summary!=="Bench test summary"||intake?.device?.warranty_status!=="Garantili"||intake?.device?.price!==1250||intake?.device?.service_source!=="Web Teknik Servis"||!intake?.detailOpen||!intake?.detailTitle.includes("Servis Formu")||!intake?.inspectionSummaryVisible||intake?.detailActions.some(enabled=>!enabled)) throw new Error(`Service intake save payload or receipt opening failed: ${JSON.stringify(intake)}`);
        result.automotiveServiceExtensionWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,currentSector,customers:db.customers.slice(),activities:db.activities};const calls=[];
          try {
            currentSector="otomotiv";apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);return call.url.includes("/table/devices")?{id:9811}:call.url.includes("/table/customers")?{id:9810}:{rows:[],count:0,columns:[]}};hydrateDesktop=async()=>true;toast=()=>{};
            serviceDialog();const form=document.querySelector("#dialogForm");form.elements.namedItem("customer_name").value="Automotive Extension Customer";form.elements.namedItem("customer_phone_input").value="+90 555 010 2040";form.elements.namedItem("plate").value="QA-EXT-01";form.elements.namedItem("serial").value="ENGINE-001";form.elements.namedItem("vin").value="VIN-QA-01";form.elements.namedItem("brand").value="Toyota";form.elements.namedItem("model").value="Corolla";form.elements.namedItem("odometer").value="58200";form.elements.namedItem("service_type").value="Motor Ar\u0131za";form.elements.namedItem("fault").value="Engine check";form.elements.namedItem("open_form").checked=false;document.querySelector("#dialogSubmit").click();await new Promise(resolve=>setTimeout(resolve,120));return{payload:calls.find(call=>call.method==="POST"&&call.url.includes("/table/devices"))?.body||null,invalid:[...form.querySelectorAll(":invalid")].map(node=>({name:node.name,value:node.value,required:node.required})),calls,button:document.querySelector("#dialogSubmit")?.disabled,sector:currentSector};
          } finally {apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;currentSector=saved.currentSector;db.customers=saved.customers;db.activities=saved.activities;save();const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel")}
        })()`);
        const automotiveExtension=result.automotiveServiceExtensionWorkflow?.payload;
        if(automotiveExtension?.vehicle_plate!=="QA-EXT-01"||automotiveExtension?.serial_no!=="ENGINE-001"||automotiveExtension?.vehicle_vin!=="VIN-QA-01"||automotiveExtension?.vehicle_odometer!==58200||automotiveExtension?.sector_extension?.current_km!=="58200"||automotiveExtension?.sector_extension?.service_type!=="Motor Ar\u0131za") throw new Error(`Automotive service extension was not submitted: ${JSON.stringify(result.automotiveServiceExtensionWorkflow)}`);
        result.serviceInspectionEditWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,customers:db.customers.map(customer=>({...customer,services:[...(customer.services||[])],quotes:[...(customer.quotes||[])]})),activities:db.activities},calls=[];
          try {
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);return{}};
            hydrateDesktop=async()=>true;toast=()=>{};
            const customer=db.customers.find(item=>String(item.id)==="15"),service={id:"9810",no:"DEMO-SRV-EDIT",device_type:"Laptop / Notebook",brand:"Acer",model:"Aspire 7",serial:"EDIT-001",status:"Bekliyor",note:"Display check",repair_details:"Customer update",internal_notes:"Existing notes",inspection_summary:"Initial bench result",price:400,delivery:"2026-10-22",warranty_status:"Garantili"};
            dashboardServiceEditDialog(customer,service);
            const form=document.querySelector("#dialogForm"),warranty=form.elements.namedItem("warranty_status"),warrantyOptions=[...warranty.options].map(option=>option.textContent.trim());
            form.elements.namedItem("inspection_summary").value="Updated inspection summary";warranty.value="Bilinmiyor";
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,100));
            const call=calls.find(item=>item.method==="POST"&&item.url.includes("/table/devices"));
            return{dialogOpen:document.querySelector("#appDialog")?.open||false,inspectionSummary:form.elements.namedItem("inspection_summary").value,warrantyOptions,warrantyRequired:warranty.required,payload:call?.body||null};
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const inspectionEdit=result.serviceInspectionEditWorkflow;
        if(inspectionEdit?.dialogOpen||inspectionEdit?.inspectionSummary!=="Updated inspection summary"||inspectionEdit?.payload?.id!==9810||inspectionEdit?.payload?.inspection_summary!=="Updated inspection summary"||JSON.stringify(inspectionEdit?.warrantyOptions)!==JSON.stringify(["Garantili","Garanti Dışı","Bilinmiyor"])||!inspectionEdit?.warrantyRequired||inspectionEdit?.payload?.warranty_status!=="Bilinmiyor"||inspectionEdit?.payload?.sector_extension?.warranty_status!=="Bilinmiyor") throw new Error(`Service inspection summary edit did not persist its value: ${JSON.stringify(inspectionEdit)}`);
        result.serviceIntakeRegisteredSave = await evaluate(`(async () => {
          const cloneCustomers=()=>db.customers.map(customer=>({...customer,services:[...(customer.services||[])],quotes:[...(customer.quotes||[])]}));
          const saved={apiFetch,hydrateDesktop,toast,customers:cloneCustomers(),activities:db.activities},calls=[];
          try {
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);if(call.url.includes("/table/devices")&&call.method==="POST")return{id:9803};return{rows:[],count:0,columns:[]}};
            hydrateDesktop=async()=>true;toast=()=>{};
            serviceDialog("15");
            const form=document.querySelector("#dialogForm");
            form.elements.namedItem("device_type").value="Laptop / Notebook";
            form.elements.namedItem("brand").value="Dell";
            form.elements.namedItem("model").value="Latitude 5440";
            form.elements.namedItem("serial").value="EXISTING-CUSTOMER-01";
            form.elements.namedItem("fault").value="Battery diagnostics";
            form.elements.namedItem("price").value="650";
            form.elements.namedItem("open_form").checked=false;
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,100));
            const posts=calls.filter(call=>call.method==="POST"),device=posts.find(call=>call.url.includes("/table/devices"))?.body;
            return{dialogOpen:document.querySelector("#appDialog")?.open||false,postCount:posts.length,customerPost:posts.some(call=>call.url.includes("/table/customers")),device,customerPicker:form.elements.namedItem("customerId").value,customerName:form.elements.namedItem("customer_name").value};
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const registeredSave=result.serviceIntakeRegisteredSave;
        if(registeredSave?.dialogOpen||registeredSave?.postCount!==1||registeredSave?.customerPost||registeredSave?.customerPicker!=="15"||registeredSave?.customerName!=="Burak Sahin"||registeredSave?.device?.customer_id!==15||registeredSave?.device?.customer_name!=="Burak Sahin"||registeredSave?.device?.customer_phone!=="+90 555 000 0015"||registeredSave?.device?.device_brand!=="Dell"||registeredSave?.device?.device_model!=="Latitude 5440"||registeredSave?.device?.serial_no!=="EXISTING-CUSTOMER-01"||registeredSave?.device?.fault_description!=="Battery diagnostics"||registeredSave?.device?.price!==650) throw new Error(`Registered-customer service intake did not reuse its customer record: ${JSON.stringify(registeredSave)}`);
        result.serviceIntakeFailureWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,customers:db.customers.slice(),activities:db.activities},calls=[],messages=[];
          try {
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase()};calls.push(call);if(call.url.includes("/table/customers")&&call.method==="POST")throw Error("fixture customer write rejected");return{rows:[],count:0,columns:[]}};
            hydrateDesktop=async()=>{throw Error("Unexpected bootstrap after rejected customer write")};toast=(message,type)=>messages.push({message:String(message),type:String(type||"")});
            serviceDialog();
            const form=document.querySelector("#dialogForm");
            form.elements.namedItem("customer_name").value="Retryable Intake Customer";
            form.elements.namedItem("customer_phone_input").value="+90 555 010 2031";
            form.elements.namedItem("device_type").value="Laptop / Notebook";
            form.elements.namedItem("brand").value="Acer";
            form.elements.namedItem("fault").value="Fixture failure path";
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,120));
            const dialog=document.querySelector("#appDialog"),result={dialogOpen:dialog?.open||false,customerName:form.elements.namedItem("customer_name").value,customerPhone:form.elements.namedItem("customer_phone_input").value,postUrls:calls.filter(call=>call.method==="POST").map(call=>call.url),messages};
            document.querySelector("#dialogCancel")?.click();
            return result;
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const failedIntake=result.serviceIntakeFailureWorkflow;
        if(!failedIntake?.dialogOpen||failedIntake.customerName!=="Retryable Intake Customer"||failedIntake.customerPhone!=="+90 555 010 2031"||failedIntake.postUrls.length!==1||!failedIntake.postUrls[0].includes("/table/customers")||!failedIntake.messages.some(item=>item.type==="error")) throw new Error(`Service intake API failure did not preserve a retryable form: ${JSON.stringify(failedIntake)}`);
        result.automotiveInvoiceReadyWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,currentSector,customers:db.customers.map(customer=>({...customer,services:[...(customer.services||[])],quotes:[...(customer.quotes||[])]})),activities:db.activities},calls=[];
          try {
            currentSector="otomotiv";
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);if(call.url.includes("/table/customers")&&call.method==="POST")return{id:9891};if(call.url.includes("/table/devices")&&call.method==="POST")return{id:9892};return{rows:[],count:0,columns:[]}};
            hydrateDesktop=async()=>true;toast=()=>{};
            serviceDialog();
            const form=document.querySelector("#dialogForm");
            form.elements.namedItem("customer_name").value="Automotive Invoice Fixture";
            form.elements.namedItem("customer_phone_input").value="+90 555 010 2099";
            form.elements.namedItem("plate").value="QA-INV-01";
            form.elements.namedItem("brand").value="Toyota";
            form.elements.namedItem("model").value="Corolla";
            form.elements.namedItem("fault").value="Annual service";
            form.elements.namedItem("invoice_ready").checked=true;
            form.elements.namedItem("open_form").checked=false;
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,100));
            const device=calls.find(call=>call.method==="POST"&&call.url.includes("/table/devices"))?.body;
            return{invoiceCheckbox:!!form.elements.namedItem("invoice_ready"),invoiceChecked:!!form.elements.namedItem("invoice_ready").checked,dialogOpen:document.querySelector("#appDialog")?.open||false,device};
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;currentSector=saved.currentSector;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const invoiceReady=result.automotiveInvoiceReadyWorkflow;
        if(!invoiceReady?.invoiceCheckbox||!invoiceReady.invoiceChecked||invoiceReady.dialogOpen||invoiceReady.device?.vehicle_plate!=="QA-INV-01"||!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(invoiceReady.device?.invoice_ready_at||"")) throw new Error(`Automotive invoice-ready descriptor failed to persist its timestamp: ${JSON.stringify(invoiceReady)}`);
        result.automotiveInvoiceReadyEditWorkflow = await evaluate(`(async () => {
          const saved={apiFetch,hydrateDesktop,toast,currentSector,customers:db.customers.map(customer=>({...customer,services:[...(customer.services||[])],quotes:[...(customer.quotes||[])]})),activities:db.activities},calls=[];
          try {
            currentSector="otomotiv";
            apiFetch=async(url,options={})=>{const call={url:String(url),method:String(options.method||"GET").toUpperCase(),body:options.body?JSON.parse(options.body):null};calls.push(call);return{}};
            hydrateDesktop=async()=>true;toast=()=>{};
            const customer=db.customers.find(item=>String(item.id)==="15"),service={id:"9893",no:"DEMO-AUTO-EDIT",device_type:"Araç",brand:"Toyota",model:"Corolla",serial:"SERIAL-INV-02",plate:"QA-INV-02",status:"Bekliyor",note:"Annual service",inspection_summary:"Inspection notes",sector_extension:{vehicle_plate:"QA-INV-02",vehicle_vin:"VIN-INV-02",current_km:"12000",service_type:"Periyodik Bak\u0131m"},current_km:"12000",service_type:"Periyodik Bak\u0131m",invoice_ready_at:null,price:0};
            dashboardServiceEditDialog(customer,service);
            const form=document.querySelector("#dialogForm"),checkbox=form.elements.namedItem("invoice_ready"),initialChecked=!!checkbox?.checked;
            checkbox.checked=true;form.elements.namedItem("current_km").value="12500";form.elements.namedItem("vehicle_plate").value="QA-INV-03";form.elements.namedItem("vehicle_vin").value="VIN-UPDATED-02";form.elements.namedItem("service_type").value="Motor Ar\u0131za";
            document.querySelector("#dialogSubmit").click();
            await new Promise(resolve=>setTimeout(resolve,100));
            const payload=calls.find(call=>call.method==="POST"&&call.url.includes("/table/devices"))?.body,editDialogOpen=document.querySelector("#appDialog")?.open||false;
            serviceDetailDialog(customer,{id:"9893",no:"DEMO-AUTO-EDIT",device:"Toyota Corolla",serial:payload?.serial_no,plate:payload?.vehicle_plate,sector_extension:payload?.sector_extension});
            const detail={vehicleIdentity:document.querySelector("#servicePrintArea .service-summary div:nth-child(4) strong")?.textContent||"",vin:document.querySelector("[data-service-automotive-vin] strong")?.textContent||"",serviceType:document.querySelector("[data-service-automotive-descriptor] strong")?.textContent||"",odometer:document.querySelector("[data-service-automotive-odometer] strong")?.textContent||""};
            return{checkboxPresent:!!checkbox,initialChecked,editDialogOpen,detailDialogOpen:document.querySelector("#appDialog")?.open||false,payload,detail};
          } finally {
            apiFetch=saved.apiFetch;hydrateDesktop=saved.hydrateDesktop;toast=saved.toast;currentSector=saved.currentSector;db.customers=saved.customers;db.activities=saved.activities;save();
            const dialog=document.querySelector("#appDialog");if(dialog?.open)dialog.close("cancel");
          }
        })()`);
        const invoiceReadyEdit=result.automotiveInvoiceReadyEditWorkflow;
        if(!invoiceReadyEdit?.checkboxPresent||invoiceReadyEdit.initialChecked||invoiceReadyEdit.editDialogOpen||!invoiceReadyEdit.detailDialogOpen||invoiceReadyEdit.payload?.id!==9893||invoiceReadyEdit.payload?.sector_extension?.vehicle_plate!=="QA-INV-03"||invoiceReadyEdit.payload?.vehicle_plate!=="QA-INV-03"||invoiceReadyEdit.payload?.serial_no!=="SERIAL-INV-02"||invoiceReadyEdit.payload?.sector_extension?.current_km!=="12500"||invoiceReadyEdit.payload?.sector_extension?.vehicle_vin!=="VIN-UPDATED-02"||invoiceReadyEdit.payload?.sector_extension?.service_type!=="Motor Ar\u0131za"||invoiceReadyEdit.detail?.vehicleIdentity!=="QA-INV-03"||invoiceReadyEdit.detail?.vin!=="VIN-UPDATED-02"||invoiceReadyEdit.detail?.serviceType!=="Motor Ar\u0131za"||invoiceReadyEdit.detail?.odometer!=="12500"||!/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(invoiceReadyEdit.payload?.invoice_ready_at||"")) throw new Error(`Automotive invoice-ready edit did not persist its timestamp: ${JSON.stringify(invoiceReadyEdit)}`);
      }
      if (entry.id === "service-status") {
        result.statusWallFixture = await evaluate(`(() => {
          const names = ["Burak Sahin", "Derya Aydin", "Murat Arslan", "Elif Yilmaz", "Can Yilmaz", "Kaan Yilmaz", "Selin Yilmaz", "Baris Cevik", "Mehmet Kaya", "Zeynep Celik", "Burak Sahin", "Ahmet Yilmaz", "Cemre Ekin", "Aksoy Medya A.S.", "Ahmet Yilmaz"];
          const statuses = ["Teslim Edildi", "Teslime Hazir", "Test / Onay", "Tamirde", "Bekliyor", "Teslim Edildi", "Teslim Edildi", "Parca Bekliyor", "Teslim Edildi", "Test / Onay", "Tamirde", "Bekliyor", "Teslim Edildi", "Teslim Edildi", "Teslim Edildi"];
          const rows = names.map((customer_name, index) => ({ id: 15 - index, tracking_no: "DEMO-SRV-" + String(15 - index).padStart(4, "0"), customer_name, device_brand: "AYEC", device_model: "Test Cihaz " + String(15 - index).padStart(2, "0"), status: statuses[index], entry_date: "2026-09-21", estimated_date: "-", urgency: "Normal" }));
          ayecStatusRows = rows;
          window.currentGenericData = { rows, count: rows.length };
          ayecStatusRender();
          ayecStatusFlowRender(rows);
          ayecStatusAssistantData = { appointments: [{ date: today(), time: "10:30", customer_name: "Derya Aydin", description: "Laptop teslim kontrolu", status: "Bekliyor" }], parts: [{ name: "Guc adaptoru", stock: 1, min_stock: 2 }], personnel: [{ name: "Burak Sahin", role: "Teknisyen", status: "Sahada" }, { name: "Emre Usta", role: "Teknisyen", status: "Atolyede" }, { name: "Serkan Can", role: "Saha Teknisyeni", status: "Gorevde" }] };
          ayecStatusAssistantRender();
          const metrics = ayecStatusMetrics(rows, {}, "2026-10-18");
          document.querySelector("#statusWallTotal").textContent = metrics.volume + " Cihaz";
          document.querySelector("#statusWallClosed").textContent = metrics.deliveredToday + " Teslim";
          document.querySelector("#statusWallActive").textContent = metrics.activeToday + " Aktif";
          document.querySelector("#statusWallOccupancy").textContent = "-";
          document.querySelector("#statusWallCapacity").textContent = metrics.occupying + " Cihaz / Limit yok";
          document.querySelector("#statusWallCritical").textContent = metrics.critical + " Cihaz Bekliyor";
          document.querySelector("#statusWallParts").textContent = metrics.critical + " Kritik Kayit";
          document.querySelector("#statusWallDuration").textContent = "-";
          document.querySelector("#statusWallDurationCount").textContent = metrics.durationCount + " Kapanan Servis";
          return { rows: rows.length, metrics };
        })()`);
        const statusPopulatedCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
        fs.writeFileSync(path.join(outputDir, "route-captures", "service-status-populated-1300x850.png"), Buffer.from(statusPopulatedCapture.data, "base64"));
        result.statusFilterCounts = await evaluate(`Array.from(document.querySelectorAll("[data-status-filter]"), button => button.textContent.trim())`);
        if (result.statusWallFixture?.rows !== 15 || JSON.stringify(result.statusFilterCounts) !== JSON.stringify(["T\u00fcm\u00fc (15)", "Teslim (7)", "Par\u00e7a Bekleyen (1)", "\u0130\u015flemde (7)"])) throw new Error(`Service-status filter totals are not rendered: ${JSON.stringify({ fixture: result.statusWallFixture, counts: result.statusFilterCounts })}`);
        result.statusAssistantErrorAudit = await evaluate(`(() => {const original=ayecStatusAssistantData;ayecStatusAssistantData={appointments:[],parts:[],personnel:[],errors:{appointments:true,parts:true,personnel:true}};ayecStatusAssistantRender();const audit={appointment:document.querySelector("#statusAssistantAppointment")?.textContent||"",stock:document.querySelector("#statusAssistantStock")?.textContent||"",personnel:document.querySelector("#statusAssistantPersonnel")?.textContent.trim()||""};ayecStatusAssistantData=original;ayecStatusAssistantRender();return audit})()`);
        if (result.statusAssistantErrorAudit.appointment !== "Randevu kay\u0131tlar\u0131 okunamad\u0131." || result.statusAssistantErrorAudit.stock !== "Stok kay\u0131tlar\u0131 okunamad\u0131." || !result.statusAssistantErrorAudit.personnel.includes("Teknisyen kaydi bulunmuyor veya okunamadi.")) throw new Error(`Service-status assistant does not report unavailable data like the desktop: ${JSON.stringify(result.statusAssistantErrorAudit)}`);
        result.statusWallGeometry = await evaluate(`(() => {const rect=selector=>{const r=document.querySelector(selector)?.getBoundingClientRect();return r?{left:Math.round(r.left),right:Math.round(r.right),top:Math.round(r.top),bottom:Math.round(r.bottom),width:Math.round(r.width),height:Math.round(r.height)}:null};return{sidebar:rect("#sidebar"),content:rect("#content"),pageHead:rect(".content > .page-head"),actions:rect(".content > .page-head .actions"),metrics:rect(".status-wall-metrics"),list:rect(".status-wall-list"),layout:rect(".status-wall-layout"),main:rect(".status-wall-main"),flow:rect(".status-wall-flow"),side:rect(".status-wall-side"),assistant:rect(".status-wall-assistant"),assistantAppointment:rect("#statusAssistantAppointment"),assistantStock:rect("#statusAssistantStock"),assistantAppointmentButton:rect(".status-wall-assistant [data-status-appointments]"),assistantStockButton:rect(".status-wall-assistant [data-status-stock]"),technicians:rect(".status-wall-technicians"),technicianButton:rect(".status-wall-technicians > button"),camera:rect(".status-wall-camera"),cameraPreview:rect(".status-wall-camera > div"),marquee:rect(".status-wall-marquee"),gap:Math.round((document.querySelector(".status-wall-side")?.getBoundingClientRect().left||0)-(document.querySelector(".status-wall-main")?.getBoundingClientRect().right||0))}})()`);
        result.statusCameraReachabilityAudit = await evaluate(`(() => {const panel=document.querySelector(".status-wall-side"),preview=document.querySelector(".status-wall-camera>div");if(!panel||!preview)return{available:false};const prior=panel.scrollTop;panel.scrollTop=panel.scrollHeight;const bounds=preview.getBoundingClientRect(),panelBounds=panel.getBoundingClientRect();const audit={available:true,focusable:panel.tabIndex===0,previewHeight:Math.round(bounds.height),clientHeight:panel.clientHeight,scrollHeight:panel.scrollHeight,scrollTop:panel.scrollTop,previewTop:Math.round(bounds.top),previewBottom:Math.round(bounds.bottom),panelTop:Math.round(panelBounds.top),panelBottom:Math.round(panelBounds.bottom),previewReachable:bounds.bottom<=panelBounds.bottom+1,overflow:getComputedStyle(panel).overflowY};panel.scrollTop=prior;return audit})()`);
        if (!result.statusCameraReachabilityAudit.available || !result.statusCameraReachabilityAudit.focusable || result.statusCameraReachabilityAudit.previewHeight !== 112 || result.statusCameraReachabilityAudit.scrollHeight > result.statusCameraReachabilityAudit.clientHeight || !result.statusCameraReachabilityAudit.previewReachable || result.statusCameraReachabilityAudit.overflow !== "auto") throw new Error(`Service-status side panels do not fit in the native viewport: ${JSON.stringify(result.statusCameraReachabilityAudit)}`);
        result.statusTechnicianRowGeometry = await evaluate(`(() => [...document.querySelectorAll(".status-wall-technicians article")].map(row=>{const r=row.getBoundingClientRect(),label=row.querySelector("small")?.getBoundingClientRect();return{top:Math.round(r.top),bottom:Math.round(r.bottom),height:Math.round(r.height),labelTop:Math.round(label?.top||0),labelBottom:Math.round(label?.bottom||0),labelText:row.querySelector("small")?.textContent||"",clientHeight:row.clientHeight,scrollHeight:row.scrollHeight}}))()`);
        result.statusAssistantLayoutAudit = await evaluate(`(() => {const appointment=document.querySelector("#statusAssistantAppointment"),stock=document.querySelector("#statusAssistantStock"),measure=node=>({text:node?.textContent||"",title:node?.title||"",height:Math.round(node?.getBoundingClientRect().height||0),clientHeight:node?.clientHeight||0,scrollHeight:node?.scrollHeight||0});return{appointment:measure(appointment),stock:measure(stock)}})()`);
        if (result.statusAssistantLayoutAudit.appointment.height !== 24 || result.statusAssistantLayoutAudit.stock.height !== 24 || result.statusAssistantLayoutAudit.appointment.text.split("\n").length !== 2 || result.statusAssistantLayoutAudit.stock.text.split("\n").length !== 2 || result.statusAssistantLayoutAudit.appointment.title !== result.statusAssistantLayoutAudit.appointment.text || result.statusAssistantLayoutAudit.stock.title !== result.statusAssistantLayoutAudit.stock.text || result.statusAssistantLayoutAudit.appointment.scrollHeight > result.statusAssistantLayoutAudit.appointment.clientHeight || result.statusAssistantLayoutAudit.stock.scrollHeight > result.statusAssistantLayoutAudit.stock.clientHeight) throw new Error(`Service-status assistant notices do not fit the compact two-line layout: ${JSON.stringify(result.statusAssistantLayoutAudit)}`);
        const geometry = result.statusWallGeometry;
        if (geometry.sidebar?.width !== 260 || geometry.content?.left !== 260 || geometry.layout?.left !== 272 || geometry.layout?.right !== 1288 || geometry.layout?.height !== 499 || geometry.main?.width !== 675 || geometry.main?.bottom !== 809 || geometry.side?.width !== 329 || geometry.side?.left !== 959 || geometry.side?.bottom !== 809 || geometry.assistant?.height !== 160 || geometry.technicians?.height !== 168 || geometry.camera?.height !== 150 || geometry.assistantAppointment?.bottom > geometry.assistant?.bottom || geometry.assistantStock?.bottom > geometry.assistant?.bottom || geometry.assistantAppointmentButton?.bottom > geometry.assistant?.bottom || geometry.assistantStockButton?.bottom > geometry.assistant?.bottom || geometry.cameraPreview?.bottom > geometry.camera?.bottom || geometry.technicianButton?.bottom > geometry.technicians?.bottom || geometry.flow?.bottom > geometry.main?.bottom || geometry.marquee?.top < geometry.layout?.bottom || geometry.gap !== 12 || Math.abs(geometry.actions?.top - 158) > 1 || Math.abs(geometry.actions?.height - 28) > 1 || Math.abs(geometry.metrics?.top - 192) > 1 || Math.abs(geometry.metrics?.height - 106) > 1 || Math.abs(geometry.list?.top - 311) > 1) throw new Error(`Service-status shell geometry differs from the 1300x850 desktop reference: ${JSON.stringify(geometry)}`);
        result.statusPersonnelAudit = await evaluate(`(() => {const card=document.querySelector(".status-wall-technicians"),bounds=card?.getBoundingClientRect(),rows=[...document.querySelectorAll(".status-wall-technicians article")],button=document.querySelector(".status-wall-technicians > button"),inside=node=>{const r=node?.getBoundingClientRect();return!!bounds&&!!r&&r.top>=bounds.top&&r.bottom<=bounds.bottom},noOverlap=rows.every((row,index)=>index===0||row.getBoundingClientRect().top>=rows[index-1].getBoundingClientRect().bottom)&&(!rows.length||button?.getBoundingClientRect().top>=rows[rows.length-1].getBoundingClientRect().bottom);return{count:rows.length,rowsInside:rows.every(inside),buttonInside:inside(button),noOverlap}})()`);
        if (result.statusPersonnelAudit.count !== 3 || !result.statusPersonnelAudit.rowsInside || !result.statusPersonnelAudit.buttonInside || !result.statusPersonnelAudit.noOverlap) throw new Error(`Service-status technician entries or action are clipped or overlap: ${JSON.stringify(result.statusPersonnelAudit)}`);
        result.statusTableAudit = await evaluate(`(() => {const buttons=[...document.querySelectorAll("[data-status-filter]")],parts=buttons.find(button=>button.dataset.statusFilter==="parts"),all=buttons.find(button=>button.dataset.statusFilter==="all");parts?.click();const partsRows=document.querySelectorAll(".status-wall-table tbody tr").length;all?.click();const input=document.querySelector("#genericSearch");input.value="Derya";input.dispatchEvent(new Event("input",{bubbles:true}));const searchRows=document.querySelectorAll(".status-wall-table tbody tr").length;input.value="";input.dispatchEvent(new Event("input",{bubbles:true}));const critical=document.querySelector("[data-status-critical]");critical?.click();const criticalRows=document.querySelectorAll(".status-wall-table tbody tr").length;critical?.click();document.querySelector('[data-status-page="1"]')?.click();const pageLabel=document.querySelector(".status-wall-pager b")?.textContent.trim()||"",secondPageFirst=document.querySelector(".status-wall-table tbody tr td:first-child")?.textContent.trim()||"";document.querySelector('[data-status-page="-1"]')?.click();const wrap=document.querySelector(".status-wall-table-wrap"),bounds=wrap?.getBoundingClientRect(),rows=[...document.querySelectorAll(".status-wall-table tbody tr")],visible=rows.filter(row=>{const r=row.getBoundingClientRect();return bounds&&r.top>=bounds.top-1&&r.bottom<=bounds.bottom+1}).length;return{rows:rows.length,partsRows,searchRows,criticalRows,pageLabel,secondPageFirst,visibleRows:visible,tableWidth:Math.round(document.querySelector(".status-wall-table")?.getBoundingClientRect().width||0),clientWidth:wrap?.clientWidth||0,scrollWidth:wrap?.scrollWidth||0}})()`);
        if (result.statusTableAudit.rows !== 7 || result.statusTableAudit.partsRows !== 1 || result.statusTableAudit.searchRows !== 1 || result.statusTableAudit.criticalRows !== 3 || result.statusTableAudit.pageLabel !== "2 / 3" || !result.statusTableAudit.secondPageFirst.includes("0008") || result.statusTableAudit.visibleRows !== 7 || result.statusTableAudit.scrollWidth > result.statusTableAudit.clientWidth + 1) throw new Error(`Service-status table differs from the desktop's visible density or filter behavior: ${JSON.stringify(result.statusTableAudit)}`);
        result.statusAssistantNavigationAudit = await evaluate(`(() => {const original=navigate,routes=[];try{navigate=route=>routes.push(route);document.querySelector("[data-status-appointments]")?.click();document.querySelector("[data-status-stock]")?.click();return routes}finally{navigate=original}})()`);
        if (JSON.stringify(result.statusAssistantNavigationAudit) !== JSON.stringify(["appointments", "stock"])) throw new Error(`Service-status assistant shortcuts did not reach their desktop destinations: ${JSON.stringify(result.statusAssistantNavigationAudit)}`);
      }
      if (entry.id === "stock") {
        result.stockMovementWorkflow = await evaluate(`(async()=>{
          const originalApi=apiFetch,originalFetch=window.fetch,originalPrint=window.print,originalAnchorClick=HTMLAnchorElement.prototype.click,originalContextSetting=db.settings.contextMenu,calls=[],fetchCalls=[],downloads=[];let printCalls=0;const makeRow=(id,type,description)=>({id,part_name:"History fixture",movement_type:type,amount:id,currency:"USD",unit_cost:12.5,description,created_at:"2026-01-01 12:34:00"}),allRows=Array.from({length:100},(_,index)=>makeRow(101-index,index%2?"Giri\u015f":"\u00c7\u0131k\u0131\u015f","Movement "+(101-index)));
          apiFetch=async path=>{const url=new URL(path,location.origin);if(url.pathname!=="/api/desktop/stock/movements/history")return originalApi(path);const query={page:Number(url.searchParams.get("page")||1),search:url.searchParams.get("search")||"",type:url.searchParams.get("type")||""};calls.push(query);if(query.search&&query.type)return{rows:[makeRow(10,"Giri\u015f","Movement 10")],page:1,pages:1,total:1,date_format:"DD.MM.YYYY"};if(query.search)return{rows:[makeRow(10,"Giri\u015f","Movement 10"),makeRow(100,"Giri\u015f","Movement 100")],page:1,pages:1,total:2,date_format:"DD.MM.YYYY"};if(query.type)return{rows:[makeRow(100,"Giri\u015f","Movement 100")],page:1,pages:1,total:1,date_format:"DD.MM.YYYY"};return{rows:query.page===1?allRows:[makeRow(1,"\u00c7\u0131k\u0131\u015f","Movement 1")],page:query.page,pages:2,total:101,date_format:"DD.MM.YYYY"}};
          db.settings.contextMenu=true;window.fetch=async(url,options={})=>{if(String(url).startsWith("/api/desktop/stock/movements/export/")){fetchCalls.push({url:String(url),credentials:options.credentials||""});return new Response("fixture",{status:200,headers:{"Content-Type":"application/octet-stream"}})}return originalFetch(url,options)};window.print=()=>{printCalls++};HTMLAnchorElement.prototype.click=function(){downloads.push({href:this.href,name:this.download})};
          try{
            navigate("movements");await new Promise(resolve=>setTimeout(resolve,30));
            const search=document.getElementById("movementSearch"),type=document.getElementById("movementType");search.value="";type.value="";type.dispatchEvent(new Event("change",{bubbles:true}));await new Promise(resolve=>setTimeout(resolve,25));
            const initial={rows:document.querySelectorAll('#movementTable tbody tr[data-kind="movement"]').length,columns:document.querySelectorAll("#movementTable thead th").length,pager:document.querySelector("#movementPager")?.textContent.replace(/\s+/g," ").trim()||""};
            document.getElementById("movementNext")?.click();await new Promise(resolve=>setTimeout(resolve,20));const secondPageRows=document.querySelectorAll('#movementTable tbody tr[data-kind="movement"]').length,secondPageLabel=document.querySelector("#movementPager")?.textContent.replace(/\s+/g," ").trim()||"";
            const row=document.querySelector('#movementTable tbody tr[data-kind="movement"]');row?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));const dialog=document.querySelector("#appDialog"),detail={opened:!!dialog?.open,title:document.querySelector("#dialogTitle")?.textContent||"",fieldCount:document.querySelectorAll("#dialogBody .movement-detail-row").length,hasPart:document.querySelector("#dialogBody")?.textContent.includes("History fixture")||false};document.querySelector("#dialogClose")?.click();detail.closed=!!dialog&&!dialog.open;
            document.getElementById("movementPrev")?.click();await new Promise(resolve=>setTimeout(resolve,20));search.value="Movement 10";search.dispatchEvent(new Event("input",{bubbles:true}));await new Promise(resolve=>setTimeout(resolve,260));const searchRows=document.querySelectorAll('#movementTable tbody tr[data-kind="movement"]').length;type.value="Giri\u015f";type.dispatchEvent(new Event("change",{bubbles:true}));await new Promise(resolve=>setTimeout(resolve,20));const filteredRows=document.querySelectorAll('#movementTable tbody tr[data-kind="movement"]').length,queryAudit={search:calls.some(item=>item.search==="Movement 10"&&item.type===""),type:calls.some(item=>item.search==="Movement 10"&&item.type==="Giri\u015f")};
            const contextRow=document.querySelector('#movementTable tbody tr[data-kind="movement"]'),menu=document.getElementById("contextMenu"),openMenu=()=>contextRow?.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:350}));openMenu();const menuItems=[...(menu?.querySelectorAll("[data-stock-movement-context]")||[])].map(button=>button.dataset.stockMovementContext);menu?.querySelector('[data-stock-movement-context="movement-export"]')?.click();await new Promise(resolve=>setTimeout(resolve,25));openMenu();menu?.querySelector('[data-stock-movement-context="movement-pdf"]')?.click();await new Promise(resolve=>setTimeout(resolve,25));openMenu();menu?.querySelector('[data-stock-movement-context="movement-print"]')?.click();openMenu();menu?.querySelector('[data-stock-movement-context="movement-delete"]')?.click();const deleteDialog=document.querySelector("#appDialog"),deleteConfirm={opened:!!deleteDialog?.open,title:document.querySelector("#dialogTitle")?.textContent||"",passwordField:!!document.querySelector('#dialogBody input[type="password"]')};document.querySelector("#dialogClose")?.click();deleteConfirm.closed=!!deleteDialog&&!deleteDialog.open;const exportParams=fetchCalls.map(item=>{const url=new URL(item.url,location.origin);return{path:url.pathname,search:url.searchParams.get("search"),type:url.searchParams.get("type"),credentials:item.credentials}});
            return{initial,secondPageRows,secondPageLabel,detail,searchRows,filteredRows,queryAudit,requestCount:calls.length,menuItems,exportParams,downloads:downloads.map(item=>item.name),printCalls,deleteConfirm};
          }finally{apiFetch=originalApi;window.fetch=originalFetch;window.print=originalPrint;HTMLAnchorElement.prototype.click=originalAnchorClick;db.settings.contextMenu=originalContextSetting;const search=document.getElementById("movementSearch"),type=document.getElementById("movementType");if(search){search.value="";search.dispatchEvent(new Event("input",{bubbles:true}));}if(type){type.value="";type.dispatchEvent(new Event("change",{bubbles:true}));}await new Promise(resolve=>setTimeout(resolve,280));navigate("stock");await new Promise(resolve=>setTimeout(resolve,35));}
        })()`);
        const audit=result.stockMovementWorkflow;
        if (audit.initial.rows !== 100 || audit.initial.columns !== 8 || !audit.initial.pager.includes("1 / 2") || audit.secondPageRows !== 1 || !audit.secondPageLabel.includes("2 / 2") || !audit.detail.opened || audit.detail.title !== "Stok Hareketi Detayi" || audit.detail.fieldCount !== 8 || !audit.detail.hasPart || !audit.detail.closed || audit.searchRows !== 2 || audit.filteredRows !== 1 || !audit.queryAudit.search || !audit.queryAudit.type || JSON.stringify(audit.menuItems) !== JSON.stringify(["movement-export","movement-pdf","movement-print","movement-delete"]) || audit.exportParams.length !== 2 || audit.exportParams.some(item=>item.search!=="Movement 10"||item.type!=="Giri\u015f"||item.credentials!=="same-origin") || !audit.downloads.some(name=>name?.endsWith(".xlsx")) || !audit.downloads.some(name=>name?.endsWith(".pdf")) || audit.printCalls !== 1 || !audit.deleteConfirm.opened || !audit.deleteConfirm.passwordField || !audit.deleteConfirm.closed) throw new Error(`Stock movement history workflow diverged from the desktop page: ${JSON.stringify(audit)}`);
      }
      if (entry.id === "job-reports") {
        result.jobReportDensity = await evaluate(`(() => {const rect=node=>{const r=node?.getBoundingClientRect();return r?{left:Math.round(r.left),right:Math.round(r.right),top:Math.round(r.top),bottom:Math.round(r.bottom),width:Math.round(r.width),height:Math.round(r.height)}:null},filters=rect(document.querySelector(".job-report-filters")),wrapNode=document.querySelector(".job-report-table-wrap"),wrap=rect(wrapNode),rows=[...document.querySelectorAll(".job-report-table tbody tr")].map(node=>{const r=node.getBoundingClientRect();return{top:Math.round(r.top),bottom:Math.round(r.bottom)}});return{filters,wrap,tableWidth:Math.round(document.querySelector(".job-report-table")?.getBoundingClientRect().width||0),columns:[...document.querySelectorAll(".job-report-table thead th")].map(node=>Math.round(node.getBoundingClientRect().width)),wrapClientWidth:wrapNode?.clientWidth||0,wrapScrollWidth:wrapNode?.scrollWidth||0,actionCell:(()=>{const cell=document.querySelector(".job-report-table tbody tr td:last-child"),group=cell?.querySelector(".job-report-actions");return{cell:rect(cell),group:rect(group),buttons:[...(group?.querySelectorAll("button")||[])].map(rect)}})(),totalRows:rows.length,rowHeights:rows.map(row=>row.bottom-row.top),fullyVisibleRows:rows.filter(row=>wrap&&row.top>=wrap.top&&row.bottom<=wrap.bottom+3).length,firstAmount:document.querySelector(".job-report-table tbody tr td[data-label='Tutar']")?.textContent.trim()||"",revenue:document.querySelector("#jobReportRevenue")?.textContent.trim()||"",activeTab:document.querySelector("[data-job-report-tab].active")?.dataset.jobReportTab||"",headers:[...document.querySelectorAll(".job-report-table thead th")].map(node=>node.textContent.trim()),rowLabels:[...document.querySelectorAll(".job-report-table tbody tr:first-child td")].map(node=>node.dataset.label||""),exportHeaders:[...ayecJobReportExportData.headers],headerTextTransform:getComputedStyle(document.querySelector(".job-report-table thead th")).textTransform,dateRangeEnabled:document.querySelector("#jobReportDateEnabled")?.checked===true,countText:document.querySelector("#jobReportCount")?.textContent||"",pageSize:document.querySelector("#jobReportPageSize")?.value||"",pagination:(()=>{const node=document.querySelector(".job-report-pagination");return{labels:[...(node?.querySelectorAll("[data-job-report-page]")||[])].map(button=>button.getAttribute("aria-label")),text:node?.innerText||"",buttons:[...(node?.querySelectorAll("[data-job-report-page]")||[])].map(button=>({width:Math.round(button.getBoundingClientRect().width),height:Math.round(button.getBoundingClientRect().height)})),selectAllText:node?.querySelector("[data-job-report-select-visible]")?.textContent.trim()||""}})(),summary:rect(document.querySelector(".job-report-summary"))}})()`);
        if (result.jobReportDensity.columns.some((width,index)=>Math.abs(width-[122,111,84,110,126,78,68,99,116,82][index])>1)) throw new Error(`Job report columns diverged from Qt fixed/contents sizing: ${JSON.stringify(result.jobReportDensity.columns)}`);
        if (result.jobReportDensity.filters?.height > 40 || result.jobReportDensity.actionCell.buttons.some(button=>button.width!==28||button.height!==26) || result.jobReportDensity.rowHeights.some(height=>Math.abs(height-54)>1) || result.jobReportDensity.headerTextTransform !== "none" || JSON.stringify(result.jobReportDensity.pagination?.labels) !== JSON.stringify(["Önceki sayfa","Sonraki sayfa"]) || result.jobReportDensity.pagination?.buttons.some(button=>button.width !== 32 || button.height !== 30) || result.jobReportDensity.pagination?.selectAllText !== "T\u00fcm\u00fcn\u00fc Se\u00e7" || result.jobReportDensity.countText !== "G\u00f6r\u00fcnt\u00fclenen: 6 / 6 \u0130\u015f Kayd\u0131 \u2022 Sayfa: 1 / 1" || result.jobReportDensity.pageSize !== "15" || result.jobReportDensity.fullyVisibleRows < 4 || result.jobReportDensity.summary?.bottom > 850) throw new Error(`Job report filters or visible rows exceed the desktop layout: ${JSON.stringify(result.jobReportDensity)}`);
        if (result.jobReportDensity.firstAmount !== "1,800.00" || result.jobReportDensity.revenue !== "0.00 \u20ba" || result.jobReportDensity.activeTab !== "jobs" || !result.jobReportDensity.dateRangeEnabled || JSON.stringify(result.jobReportDensity.headers) !== JSON.stringify(["\u0130\u015f No","M\u00fc\u015fteri / Kurum","Teknisyen","A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem","Durum","Tutar","Para Br.","Tarih","Tahsilat","\u0130\u015flemler"]) || JSON.stringify(result.jobReportDensity.exportHeaders) !== JSON.stringify(["\u0130\u015f No","M\u00fc\u015fteri / Kurum","Teknisyen","A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem","Durum","Tutar","Para Br.","Tarih","Tahsilat"]) || JSON.stringify(result.jobReportDensity.rowLabels) !== JSON.stringify(["\u0130\u015f No","M\u00fc\u015fteri / Kurum","Teknisyen","A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem","Durum","Tutar","Para Br.","Tarih","Tahsilat","\u0130\u015flemler"])) throw new Error(`Job report initial tab, date range, or currency formatting diverged from desktop: ${JSON.stringify(result.jobReportDensity)}`);
        result.jobReportToolbarGeometry = await evaluate(`(() => {const rect=node=>{const r=node?.getBoundingClientRect();return r?{left:Math.round(r.left),right:Math.round(r.right),width:Math.round(r.width)}:null},tabs=rect(document.querySelector(".job-report-tabs")),search=rect(document.querySelector(".job-report-search")),button=rect(document.querySelector("[data-job-report-search]"));return{tabs,search,gap:search&&tabs?search.left-tabs.right:null,button}})()`);
        if (!result.jobReportToolbarGeometry.tabs || !result.jobReportToolbarGeometry.search || Math.abs(result.jobReportToolbarGeometry.tabs.width-505) > 2 || Math.abs(result.jobReportToolbarGeometry.search.left-793) > 2 || result.jobReportToolbarGeometry.gap < 0 || result.jobReportToolbarGeometry.gap > 12 || result.jobReportToolbarGeometry.button?.width < 40) throw new Error(`Job report search controls do not align with the desktop toolbar: ${JSON.stringify(result.jobReportToolbarGeometry)}`);
        result.jobReportFilterAudit = await evaluate(`(() => {
          const state={ledger:ayecJobLedgerRows,services:ayecJobServiceRows,rows:ayecJobReportRows,tab:ayecJobReportTab,page:ayecJobReportPage,exportData:ayecJobReportExportData,filters:{}};
          ["genericSearch","jobReportStatus","jobReportStart","jobReportEnd","jobReportCurrency","jobReportTechnician","jobReportCustomer","jobReportAmountEnabled","jobReportAmountMin","jobReportAmountMax"].forEach(id=>{const node=document.getElementById(id);state.filters[id]=node?{value:node.value,checked:node.checked,disabled:node.disabled}:null;});
          ayecJobLedgerRows=[
            {id:"QA-FILTER-1",tracking_no:"QA-FILTER-1",customer_name:"Customer A",technician:"Tech A",status:"A\u00e7\u0131k",entry_date:"2026-09-21",currency:"TRY",debit:100,fault_description:"Camera repair"},
            {id:"QA-FILTER-2",tracking_no:"QA-FILTER-2",customer_name:"Customer B",technician:"Tech B",status:"Tahsil Edildi",entry_date:"2026-09-22",currency:"EUR",debit:200,fault_description:"Laptop repair"},
            {id:"QA-FILTER-3",tracking_no:"QA-FILTER-3",customer_name:"Customer A",technician:"Tech B",status:"A\u00e7\u0131k",entry_date:"2026-09-23",currency:"USD",debit:300,fault_description:"Router replacement"},
            {id:"QA-FILTER-4",tracking_no:"QA-FILTER-4",customer_name:"Customer C",technician:"Tech C",status:"A\u00e7\u0131k",entry_date:"2026-09-24",currency:"TRY",debit:400,fault_description:"Phone repair"}
          ];
          ayecJobServiceRows=[];ayecJobReportTab="jobs";ayecJobReportPage=0;
          const reset=()=>{document.querySelector("#genericSearch").value="";document.querySelector("#jobReportStatus").value="all";document.querySelector("#jobReportStart").value="";document.querySelector("#jobReportEnd").value="";document.querySelector("#jobReportCurrency").value="all";document.querySelector("#jobReportTechnician").value="all";document.querySelector("#jobReportCustomer").value="all";document.querySelector("#jobReportAmountEnabled").checked=false;document.querySelector("#jobReportAmountMin").value="0";document.querySelector("#jobReportAmountMax").value="0";ayecJobReportRender();};
          const ids=()=>[...document.querySelectorAll('.job-report-table tbody tr[data-job-report-kind="job"]')].map(row=>row.dataset.jobReportId).sort();
          const pick=(id,value)=>{const node=document.getElementById(id);node.value=value;node.dispatchEvent(new Event("change",{bubbles:true}));};
          reset();const all=ids();
          pick("jobReportStatus","open");const status=ids();
          reset();pick("jobReportCurrency","EUR");const currency=ids();
          reset();pick("jobReportTechnician","Tech B");const technician=ids();
          reset();pick("jobReportCustomer","Customer A");const customer=ids();
          reset();pick("jobReportAmountEnabled",true);document.querySelector("#jobReportAmountEnabled").checked=true;document.querySelector("#jobReportAmountEnabled").dispatchEvent(new Event("change",{bubbles:true}));document.querySelector("#jobReportAmountMin").value="250";document.querySelector("#jobReportAmountMin").dispatchEvent(new Event("input",{bubbles:true}));document.querySelector("#jobReportAmountMax").value="350";document.querySelector("#jobReportAmountMax").dispatchEvent(new Event("input",{bubbles:true}));const amount=ids();
          reset();document.querySelector("#jobReportStart").value="2026-09-22";document.querySelector("#jobReportStart").dispatchEvent(new Event("input",{bubbles:true}));document.querySelector("#jobReportEnd").value="2026-09-23";document.querySelector("#jobReportEnd").dispatchEvent(new Event("input",{bubbles:true}));const date=ids();
          reset();document.querySelector("#genericSearch").value="router";document.querySelector("#genericSearch").dispatchEvent(new Event("input",{bubbles:true}));ayecJobReportPage=4;const searchButton=document.querySelector("[data-job-report-search]");searchButton?.click();const searchButtonResetsPage=ayecJobReportPage===0;const search=ids();
          const expected={all:["QA-FILTER-1","QA-FILTER-2","QA-FILTER-3","QA-FILTER-4"],status:["QA-FILTER-1","QA-FILTER-3","QA-FILTER-4"],currency:["QA-FILTER-2"],technician:["QA-FILTER-2","QA-FILTER-3"],customer:["QA-FILTER-1","QA-FILTER-3"],amount:["QA-FILTER-3"],date:["QA-FILTER-2","QA-FILTER-3"],search:["QA-FILTER-3"],searchButtonResetsPage:true};
          const actual={all,status,currency,technician,customer,amount,date,search,searchButtonResetsPage};
          ayecJobLedgerRows=state.ledger;ayecJobServiceRows=state.services;ayecJobReportRows=state.rows;ayecJobReportTab=state.tab;ayecJobReportPage=state.page;ayecJobReportExportData=state.exportData;
          for(const [id,value] of Object.entries(state.filters)){const node=document.getElementById(id);if(!node||!value)continue;node.value=value.value;node.checked=value.checked;node.disabled=value.disabled;}
          ayecJobReportRender();
          return{actual,expected,passes:Object.keys(expected).every(key=>JSON.stringify(actual[key])===JSON.stringify(expected[key]))};
        })()`);
        if (!result.jobReportFilterAudit.passes) throw new Error(`Job report filters did not return the expected matching rows: ${JSON.stringify(result.jobReportFilterAudit)}`);
        result.jobReportSelectionAudit = await evaluate(`(() => {const visible=[...document.querySelectorAll(".job-report-table tbody tr[data-job-report-kind]")],button=document.querySelector("[data-job-report-select-visible]"),first=visible[0];button?.click();const selectedAll=ayecJobReportSelected.size;first?.querySelector("td")?.click();const deselectedOne=ayecJobReportSelected.size,ariaDeselected=first?.getAttribute("aria-selected");first?.querySelector("td")?.click();const reselectedOne=ayecJobReportSelected.size,ariaReselected=first?.getAttribute("aria-selected");ayecJobReportSelected.clear();first?.focus();first?.dispatchEvent(new KeyboardEvent("keydown",{key:" ",bubbles:true}));const keyboardSelected=ayecJobReportSelected.size;first?.dispatchEvent(new KeyboardEvent("keydown",{key:" ",bubbles:true}));const keyboardDeselected=ayecJobReportSelected.size;ayecJobReportSelected.clear();ayecJobReportSyncSelection();return{visible:visible.length,selectedAll,deselectedOne,reselectedOne,ariaDeselected,ariaReselected,keyboardSelected,keyboardDeselected,button:button?.textContent.trim()||""}})()`);
        if (result.jobReportSelectionAudit.visible < 1 || result.jobReportSelectionAudit.selectedAll !== result.jobReportSelectionAudit.visible || result.jobReportSelectionAudit.deselectedOne !== result.jobReportSelectionAudit.visible-1 || result.jobReportSelectionAudit.reselectedOne !== result.jobReportSelectionAudit.visible || result.jobReportSelectionAudit.ariaDeselected !== "false" || result.jobReportSelectionAudit.ariaReselected !== "true" || result.jobReportSelectionAudit.keyboardSelected !== 1 || result.jobReportSelectionAudit.keyboardDeselected !== 0 || result.jobReportSelectionAudit.button !== "T\u00fcm\u00fcn\u00fc Se\u00e7") throw new Error(`Job report row selection behavior diverged from desktop: ${JSON.stringify(result.jobReportSelectionAudit)}`);
        result.jobReportRevenueFormatAudit = await evaluate(`(() => { const originalCurrency=desktopSettings.currency, originalDefault=desktopSettings.default_currency, originalPrecision=desktopSettings.currency_precision, originalRates=exchangeRateState; desktopSettings.currency="USD"; desktopSettings.currency_precision="2"; exchangeRateState={...exchangeRateState,USD:{selling:40}}; const amount=ayecJobReportRevenue(1250); desktopSettings.currency=originalCurrency; desktopSettings.default_currency=originalDefault; desktopSettings.currency_precision=originalPrecision; exchangeRateState=originalRates; return amount; })()`);
        if (result.jobReportRevenueFormatAudit !== "31.25 $") throw new Error(`Job report currency conversion diverged from desktop: ${result.jobReportRevenueFormatAudit}`);
        jobReportCurrencyAudit = { rowAmount: result.jobReportDensity.firstAmount, revenue: result.jobReportDensity.revenue, activeTab: result.jobReportDensity.activeTab, dateRangeEnabled: result.jobReportDensity.dateRangeEnabled, usdRevenue: result.jobReportRevenueFormatAudit };
        result.jobReportContextAudit = await evaluate(`(async () => {
          const originalRows=ayecJobServiceRows,originalLedger=ayecJobLedgerRows,originalCustomers=db.customers,originalContext=db.settings.contextMenu,originalDoubleClick=db.settings.doubleClick,originalTab=ayecJobReportTab,originalServiceContext=desktopSettings.rc_job_service;
          const beforePrintRows=[...document.querySelectorAll(".job-report-table tbody tr")],beforePrintHidden=beforePrintRows.map(row=>row.hidden),printButton=beforePrintRows[0]?.querySelector("[data-job-report-print-row]"),originalPrint=window.print;let printCalls=0;window.print=()=>{printCalls++};printButton?.click();const visibleDuringPrint=[...document.querySelectorAll(".job-report-table tbody tr")].filter(row=>!row.hidden).length;window.dispatchEvent(new Event("afterprint"));const restoredAfterPrint=beforePrintRows.every((row,index)=>row.hidden===beforePrintHidden[index]);window.print=originalPrint;const rowPrintAudit={rowCount:beforePrintRows.length,buttonPresent:!!printButton,printCalls,visibleDuringPrint,restoredAfterPrint};
          const reportRow={id:991,tracking_no:"CTX-SRV-991",customer_id:991,customer_name:"Context Customer",status:"Tamirde",entry_date:"2026-09-21",exit_date:"2026-09-22",device_brand:"AYEC",device_model:"Audit",labor_cost:90,report_total:125,technician:"Audit Tech",price:90};
          const service={id:991,no:"CTX-SRV-991",device:"Laptop",device_type:"Laptop",brand:"AYEC",model:"Audit",note:"Context fixture",status:"Tamirde",price:90};
          ayecJobServiceRows=[reportRow];db.customers=[{id:991,name:"Context Customer",phone:"",balances:{},services:[service]}];db.settings.contextMenu=true;db.settings.doubleClick=true;desktopSettings.rc_job_service="1";ayecJobReportTab="service";ayecJobReportRender();
          const row=document.querySelector("tr[data-job-report-kind=service]");if(!row)throw new Error("The service-report fixture row did not render.");const serviceTableAudit={headers:[...document.querySelectorAll(".job-report-table thead th")].map(node=>node.textContent.trim()),rowLabels:[...row.querySelectorAll("td")].map(node=>node.dataset.label||""),exportHeaders:[...ayecJobReportExportData.headers],exportRow:ayecJobReportExportData.rows[0],total:row.querySelector("td[data-label=Toplam]")?.textContent.trim()||""};
          const serviceViewButton=row.querySelector("[data-job-report-view]");serviceViewButton?.click();await new Promise(resolve=>setTimeout(resolve,20));const serviceViewOpens=!!document.querySelector("#appDialog")?.open;if(serviceViewOpens){document.querySelector("#appDialog").close();await new Promise(resolve=>setTimeout(resolve,20))}const openMenu=()=>{row.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:520}));return document.querySelector(".service-list-context-menu")};
          let menu=openMenu(),actions=[...(menu?.querySelectorAll("[data-job-report-context]")||[])].map(button=>button.dataset.jobReportContext);
          const actionResults=[];
          for(const action of ["detail","technician","form"]){menu=openMenu();const button=menu?.querySelector('[data-job-report-context="'+action+'"]');button?.click();await new Promise(resolve=>setTimeout(resolve,20));actionResults.push({action,opened:!!document.querySelector("#appDialog")?.open,title:document.querySelector("#dialogTitle")?.textContent||""});if(document.querySelector("#appDialog")?.open){document.querySelector("#appDialog").close();await new Promise(resolve=>setTimeout(resolve,20))}}
          row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,20));const serviceDoubleClickOpens=!!document.querySelector("#appDialog")?.open;if(serviceDoubleClickOpens){document.querySelector("#appDialog").close();await new Promise(resolve=>setTimeout(resolve,20))}
          ayecJobLedgerRows=[{id:992,tracking_no:"CTX-JOB-992",customer_name:"Context Customer",technician:"Audit Tech",description:"Context fixture",status:"Open",currency:"TRY",debit:90,entry_date:"2026-09-21",transactions:[]}];ayecJobReportTab="jobs";document.querySelector("#genericSearch").value="";document.querySelector("#jobReportStatus").value="all";document.querySelector("#jobReportStart").value="";document.querySelector("#jobReportEnd").value="";document.querySelector("#jobReportDateEnabled").checked=false;document.querySelector("#jobReportAmountEnabled").checked=false;ayecJobReportRender();
          const jobRow=document.querySelector("tr[data-job-report-kind=job]");const jobExportDate=ayecJobReportExportData.rows[0]?.[7]||"";jobRow?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));await new Promise(resolve=>setTimeout(resolve,20));const jobDoubleClickOpens=!!document.querySelector("#appDialog")?.open;if(jobDoubleClickOpens){document.querySelector("#appDialog").close();await new Promise(resolve=>setTimeout(resolve,20))}
          jobRow?.dispatchEvent(new KeyboardEvent("keydown",{key:"ContextMenu",bubbles:true,cancelable:true}));menu=document.querySelector(".service-list-context-menu");const contextKeyOpens=!!menu;menu?.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
          jobRow?.dispatchEvent(new KeyboardEvent("keydown",{key:"F10",shiftKey:true,bubbles:true,cancelable:true}));menu=document.querySelector(".service-list-context-menu");const shiftF10Opens=!!menu;menu?.dispatchEvent(new KeyboardEvent("keydown",{key:"Escape",bubbles:true}));
          jobRow?.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:520}));menu=document.querySelector(".service-list-context-menu");const jobContextActions=[...(menu?.querySelectorAll("[data-job-report-context]")||[])].map(button=>button.dataset.jobReportContext);menu?.querySelector('[data-job-report-context="detail"]')?.click();await new Promise(resolve=>setTimeout(resolve,20));const jobContextDetailOpens=!!document.querySelector("#appDialog")?.open;if(jobContextDetailOpens){document.querySelector("#appDialog").close();await new Promise(resolve=>setTimeout(resolve,20))}
          document.querySelectorAll(".service-list-context-menu").forEach(node=>node.remove());
          ayecJobReportTab="service";ayecJobReportRender();const disabledRow=document.querySelector("tr[data-job-report-kind=service]");db.settings.contextMenu=false;disabledRow?.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:520}));const disabledMenuSuppressed=!document.querySelector(".service-list-context-menu");const serviceSearch=document.querySelector("#genericSearch");serviceSearch.value="21.09.2026";ayecJobReportRender();const serviceDateSearch=!!document.querySelector("tr[data-job-report-kind=service]");serviceSearch.value="125.00";ayecJobReportRender();const serviceAmountSearch=!!document.querySelector("tr[data-job-report-kind=service]");serviceSearch.value="audit tech";ayecJobReportRender();const serviceTechnicianSearch=!!document.querySelector("tr[data-job-report-kind=service]");serviceSearch.value="";ayecJobReportRender();const originalApiFetch=apiFetch,originalGenericData=window.currentGenericData;window.currentGenericData=null;apiFetch=async url=>{const path=String(url);if(path.startsWith("/api/desktop/table/devices?limit=500"))return{rows:[{id:701,tracking_no:"TOTAL-SRV-701",labor_cost:100}],count:1};if(path.startsWith("/api/desktop/table/used_parts?limit=1000"))return{rows:[{tracking_no:"TOTAL-SRV-701",price:12.5,quantity:2},{tracking_no:"TOTAL-SRV-701",price:500,quantity:1,is_deleted:1},{tracking_no:"TOTAL-SRV-701",price:999,quantity:0}],count:3};return{rows:[],count:0}};const loadedServiceRows=await ayecLoadJobServiceRows(),loadedServiceTotal=loadedServiceRows[0]?.report_total;apiFetch=originalApiFetch;window.currentGenericData=originalGenericData;
          ayecJobServiceRows=originalRows;ayecJobLedgerRows=originalLedger;db.customers=originalCustomers;db.settings.contextMenu=originalContext;db.settings.doubleClick=originalDoubleClick;desktopSettings.rc_job_service=originalServiceContext;ayecJobReportTab=originalTab;ayecJobReportRender();
          return{actions,actionResults,rowPrintAudit,serviceTableAudit,jobExportDate,serviceViewOpens,serviceDoubleClickOpens,jobDoubleClickOpens,contextKeyOpens,shiftF10Opens,jobContextActions,jobContextDetailOpens,disabledMenuSuppressed,serviceDateSearch,serviceAmountSearch,serviceTechnicianSearch,loadedServiceTotal};
        })()`);
        if (JSON.stringify(result.jobReportContextAudit.serviceTableAudit.headers) !== JSON.stringify(["Servis No","M\u00fc\u015fteri","Durum","Cihaz / \u0130\u015f","Toplam","Giri\u015f Tarihi","Teslim Tarihi","Teknisyen","\u0130\u015flemler"]) || JSON.stringify(result.jobReportContextAudit.serviceTableAudit.rowLabels) !== JSON.stringify(["Servis No","M\u00fc\u015fteri","Durum","Cihaz / \u0130\u015f","Toplam","Giri\u015f Tarihi","Teslim Tarihi","Teknisyen","\u0130\u015flemler"]) || JSON.stringify(result.jobReportContextAudit.serviceTableAudit.exportHeaders) !== JSON.stringify(["Servis No","M\u00fc\u015fteri","Durum","Cihaz / \u0130\u015f","Toplam","Giri\u015f Tarihi","Teslim Tarihi","Teknisyen"]) || result.jobReportContextAudit.serviceTableAudit.exportRow[4] !== 125 || result.jobReportContextAudit.serviceTableAudit.total !== "125.00" || result.jobReportContextAudit.serviceTableAudit.exportRow[5] !== "21.09.2026" || result.jobReportContextAudit.serviceTableAudit.exportRow[6] !== "22.09.2026" || result.jobReportContextAudit.jobExportDate !== "21.09.2026" || JSON.stringify(result.jobReportContextAudit.actions) !== JSON.stringify(["detail","technician","form"]) || result.jobReportContextAudit.actionResults.some(item => !item.opened) || !result.jobReportContextAudit.rowPrintAudit.buttonPresent || result.jobReportContextAudit.rowPrintAudit.rowCount < 2 || result.jobReportContextAudit.rowPrintAudit.printCalls !== 1 || result.jobReportContextAudit.rowPrintAudit.visibleDuringPrint !== 1 || !result.jobReportContextAudit.rowPrintAudit.restoredAfterPrint || !result.jobReportContextAudit.serviceViewOpens || !result.jobReportContextAudit.serviceDoubleClickOpens || !result.jobReportContextAudit.jobDoubleClickOpens || !result.jobReportContextAudit.contextKeyOpens || !result.jobReportContextAudit.shiftF10Opens || JSON.stringify(result.jobReportContextAudit.jobContextActions) !== JSON.stringify(["detail"]) || !result.jobReportContextAudit.jobContextDetailOpens || !result.jobReportContextAudit.disabledMenuSuppressed || !result.jobReportContextAudit.serviceDateSearch || !result.jobReportContextAudit.serviceAmountSearch || !result.jobReportContextAudit.serviceTechnicianSearch || result.jobReportContextAudit.loadedServiceTotal !== 125) throw new Error(`Job report context, print, or double-click actions diverged from desktop behavior: ${JSON.stringify(result.jobReportContextAudit)}`);
        result.jobReportProfitabilityAudit = await evaluate(`(async () => {
          const originalApiFetch=apiFetch,originalTab=ayecJobReportTab,originalDateEnabled=document.querySelector("#jobReportDateEnabled").checked,originalStart=document.querySelector("#jobReportStart").value,originalEnd=document.querySelector("#jobReportEnd").value,originalPeriod=document.querySelector("#jobReportProfitPeriod").value,calls=[];
          apiFetch=async(url,...args)=>{calls.push(String(url));if(String(url).includes("/api/desktop/job-reports/profitability"))return{period:"FY2026",revenue:1250,expenses:250,net:1000,net_ratio:80,status:"fixture"};return originalApiFetch(url,...args)};
          ayecJobReportTab="profit";document.querySelector("[data-job-report-tab=profit]").click();await new Promise(resolve=>setTimeout(resolve,30));
          const periodValues=[...document.querySelectorAll(".job-report-table tbody tr:first-child td")].map(cell=>cell.textContent.trim()),periodQuery=calls.at(-1)||"";
          document.querySelector("#jobReportDateEnabled").checked=true;document.querySelector("#jobReportStart").value="2026-01-01";document.querySelector("#jobReportEnd").value="2026-03-31";await ayecLoadJobProfitability();const rangeQuery=calls.at(-1)||"";
          const callsBeforeMissingRange=calls.length;document.querySelector("#jobReportStart").value="";await ayecLoadJobProfitability();const missingRangeBlocked=calls.length===callsBeforeMissingRange&&document.querySelector("#jobReportHost").textContent.includes("gerekli");
          apiFetch=originalApiFetch;ayecJobReportTab=originalTab;document.querySelector("#jobReportDateEnabled").checked=originalDateEnabled;document.querySelector("#jobReportStart").value=originalStart;document.querySelector("#jobReportEnd").value=originalEnd;document.querySelector("#jobReportProfitPeriod").value=originalPeriod;
          return{periodValues,periodQuery,rangeQuery,missingRangeBlocked};
        })()`);
        if (result.jobReportProfitabilityAudit.periodValues.join("|") !== "FY2026|1,250.00|250.00|1,000.00|80.0%" || !result.jobReportProfitabilityAudit.periodQuery.includes("period=fiscal") || !result.jobReportProfitabilityAudit.rangeQuery.includes("period=range&start=2026-01-01&end=2026-03-31") || !result.jobReportProfitabilityAudit.missingRangeBlocked) throw new Error(`Job report profitability controls diverged from the selected period: ${JSON.stringify(result.jobReportProfitabilityAudit)}`);
        result.jobReportFiltersAudit = await evaluate(`(() => {
          const originalRows=ayecJobServiceRows,originalTab=ayecJobReportTab,originalPage=ayecJobReportPage,originalDoubleClick=db.settings.doubleClick,ids=["genericSearch","jobReportStatus","jobReportStart","jobReportEnd","jobReportCurrency","jobReportTechnician","jobReportCustomer","jobReportPageSize","jobReportAmountMin","jobReportAmountMax","jobReportAmountEnabled"],saved=Object.fromEntries(ids.map(id=>{const node=document.getElementById(id);return[id,node.type==="checkbox"?node.checked:node.value]}));db.settings.doubleClick=true;
          const rows=Array.from({length:9},(_,index)=>({id:700+index,tracking_no:"FILTER-"+index,customer_name:"Customer "+index,technician_name:index%2===0?"Tech A":"Tech B",status:index<4?"Tamirde":"Teslim Edildi",entry_date:"2026-09-21",currency:index===1?"USD":index===8?"EUR":"TRY",price:50+index*25}));
          ayecJobServiceRows=rows;ayecJobReportTab="service";ayecJobReportPage=0;
          const set=(id,value)=>{const node=document.getElementById(id);if(node.type==="checkbox")node.checked=value;else node.value=value};
          const render=()=>{ayecJobReportPage=0;ayecJobReportRender();return[...document.querySelectorAll(".job-report-table tbody tr")].map(row=>row.dataset.jobReportId)};
          set("genericSearch","");set("jobReportStatus","all");set("jobReportStart","");set("jobReportEnd","");set("jobReportCurrency","all");set("jobReportTechnician","all");set("jobReportCustomer","all");set("jobReportPageSize","7");set("jobReportAmountEnabled",false);set("jobReportAmountMin","0");set("jobReportAmountMax","0");render();
          set("jobReportCurrency","USD");const currency=render();set("jobReportCurrency","all");set("jobReportTechnician","Tech A");const technician=render();set("jobReportTechnician","all");set("jobReportCustomer","Customer 8");const customer=render();set("jobReportCustomer","all");set("jobReportAmountEnabled",true);set("jobReportAmountMin","200");set("jobReportAmountMax","250");const amount=render();set("jobReportAmountEnabled",false);set("jobReportAmountMin","0");set("jobReportAmountMax","0");set("jobReportStatus","open");const status=render();set("jobReportStatus","all");set("genericSearch","FILTER-0");const search=render();
          set("genericSearch","");set("jobReportPageSize","7");const firstPage=render(),firstIndicator=document.querySelector(".job-report-pagination b")?.textContent||"";document.querySelector('[data-job-report-page="1"]')?.click();const secondPage=[...document.querySelectorAll(".job-report-table tbody tr")].map(row=>row.dataset.jobReportId),secondIndicator=document.querySelector(".job-report-pagination b")?.textContent||"";
          ayecJobReportTab="technicians";ayecJobReportRender();const matrixRow=document.querySelector("tr[data-job-report-technician]");matrixRow?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));const matrixDrillDown={technician:matrixRow?.dataset.jobReportTechnician||"",tab:ayecJobReportTab,filter:document.querySelector("#jobReportTechnician")?.value||"",visibleRows:document.querySelectorAll(".job-report-table tbody tr[data-job-report-kind]").length};
          ayecJobServiceRows=originalRows;ayecJobReportTab=originalTab;ayecJobReportPage=originalPage;db.settings.doubleClick=originalDoubleClick;for(const id of ids){const node=document.getElementById(id);if(node.type==="checkbox")node.checked=saved[id];else node.value=saved[id]}ayecJobReportRender();
          return{currency,technician,customer,amount,status,search,firstPage,firstIndicator,secondPage,secondIndicator,matrixDrillDown};
        })()`);
        const filterAudit=result.jobReportFiltersAudit;
        if (JSON.stringify(filterAudit.currency) !== JSON.stringify(["701"]) || filterAudit.technician.length !== 5 || JSON.stringify(filterAudit.customer) !== JSON.stringify(["708"]) || JSON.stringify(filterAudit.amount) !== JSON.stringify(["706","707","708"]) || filterAudit.status.length !== 4 || JSON.stringify(filterAudit.search) !== JSON.stringify(["700"]) || filterAudit.firstPage.length !== 7 || filterAudit.firstIndicator !== "1 / 2" || JSON.stringify(filterAudit.secondPage) !== JSON.stringify(["707","708"]) || filterAudit.secondIndicator !== "2 / 2" || filterAudit.matrixDrillDown.technician !== "Tech A" || filterAudit.matrixDrillDown.tab !== "service" || filterAudit.matrixDrillDown.filter !== "Tech A" || filterAudit.matrixDrillDown.visibleRows !== 5) throw new Error(`Job report filters, paging, or technician drill-down diverged from desktop behavior: ${JSON.stringify(filterAudit)}`);
        result.jobMonthlyReportAudit = await evaluate(`(async () => {
          const originalApiFetch=apiFetch,originalCurrency=desktopSettings.currency,originalDefaultCurrency=desktopSettings.default_currency,originalPrecision=desktopSettings.currency_precision,originalRates=exchangeRateState,calls=[];
          const months=Array.from({length:12},(_,index)=>({month:String(index+1).padStart(2,"0")+".2026",new_services:7,completed_services:4,paid_jobs:2,collection_total:1250}));
          apiFetch=async(url,...args)=>{calls.push(String(url));if(String(url)==="/api/desktop/job-reports/monthly")return{current:months[0],months};return originalApiFetch(url,...args)};
          desktopSettings.currency="USD";desktopSettings.default_currency="USD";desktopSettings.currency_precision="2";exchangeRateState={TRY:{selling:1},USD:{selling:40},EUR:{selling:45}};
          document.querySelector("[data-job-report-monthly]").click();await new Promise(resolve=>setTimeout(resolve,30));
          const dialog=document.querySelector("#appDialog"),cardValues=[...document.querySelectorAll("#dialogBody .job-monthly-report-metrics article strong")].map(node=>node.textContent.trim()),tableRows=[...document.querySelectorAll("#dialogBody .job-monthly-report-table tbody tr")],firstRow=[...(tableRows[0]?.querySelectorAll("td")||[])].map(node=>node.textContent.trim()),result={calls,dialogOpen:!!dialog?.open,dialogTitle:document.querySelector("#dialogTitle")?.textContent||"",cardValues,monthlyRowCount:tableRows.length,firstRow};
          if(dialog?.open)dialog.close();apiFetch=originalApiFetch;desktopSettings.currency=originalCurrency;desktopSettings.default_currency=originalDefaultCurrency;desktopSettings.currency_precision=originalPrecision;exchangeRateState=originalRates;
          return result;
        })()`);
        if (JSON.stringify(result.jobMonthlyReportAudit.calls) !== JSON.stringify(["/api/desktop/job-reports/monthly"]) || !result.jobMonthlyReportAudit.dialogOpen || result.jobMonthlyReportAudit.monthlyRowCount !== 12 || result.jobMonthlyReportAudit.cardValues[3] !== "31.25 $" || result.jobMonthlyReportAudit.firstRow[4] !== "31.25 $") throw new Error(`Monthly job report did not follow desktop currency formatting: ${JSON.stringify(result.jobMonthlyReportAudit)}`);
        result.jobReportInvalidDateAudit = await evaluate(`(() => {
          const originalRows=ayecJobLedgerRows,originalTab=ayecJobReportTab,start=document.querySelector("#jobReportStart"),end=document.querySelector("#jobReportEnd"),oldStart=start.value,oldEnd=end.value,enabled=document.querySelector("#jobReportDateEnabled"),oldEnabled=enabled.checked;
          ayecJobLedgerRows=[{id:901,tracking_no:"DATE-VALID",customer_name:"Valid date",status:"Tamirde",entry_date:"2026-09-15"},{id:902,tracking_no:"DATE-MISSING",customer_name:"Missing date",status:"Tamirde",entry_date:""}];
          ayecJobReportTab="jobs";enabled.checked=true;start.value="2026-09-01";end.value="2026-09-30";ayecJobReportRender();
          const visible=[...document.querySelectorAll(".job-report-table tbody tr")].map(row=>row.textContent);
          ayecJobLedgerRows=originalRows;ayecJobReportTab=originalTab;enabled.checked=oldEnabled;start.value=oldStart;end.value=oldEnd;ayecJobReportRender();
          return {visible,validIncluded:visible.some(row=>row.includes("DATE-VALID")),missingExcluded:!visible.some(row=>row.includes("DATE-MISSING"))};
        })()`);
        if (!result.jobReportInvalidDateAudit.validIncluded || !result.jobReportInvalidDateAudit.missingExcluded || result.jobReportInvalidDateAudit.visible.length !== 1) throw new Error(`Job report date filtering did not match the desktop invalid-date behavior: ${JSON.stringify(result.jobReportInvalidDateAudit)}`);
        const layouts = [];
        for (const width of [1200, 1300, 1597, 1598]) {
          await send("Emulation.setDeviceMetricsOverride", { width, height: 850, deviceScaleFactor: 1, mobile: false });
          await delay(25);
          const layout = await evaluate(`(() => {const host=document.querySelector(".job-report-heading .actions"),title=document.querySelector(".job-report-heading>div:first-child"),content=document.querySelector("#content"),rect=node=>{const r=node?.getBoundingClientRect();return r?{x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height}:null},box=rect(host),titleBox=rect(title),contentBox=rect(content),items=[...(host?.children||[])].map(rect).filter(Boolean),overlap=items.some((a,i)=>items.slice(i+1).some(b=>a.x<b.right-1&&a.right>b.x+1&&a.y<b.bottom-1&&a.bottom>b.y+1));return{width:innerWidth,actionsWidth:box?.width||0,inside:!!box&&!!contentBox&&box.right<=contentBox.right+1&&items.length===6&&items.every(item=>item.x>=box.x-1&&item.y>=box.y-1&&item.right<=box.right+1&&item.bottom<=box.bottom+1),noOverlap:!overlap,titleClear:!!titleBox&&!!box&&titleBox.right<=box.x}})()`);
          layouts.push(layout);
          if (!layout.inside || !layout.noOverlap || !layout.titleClear) throw new Error(`Job report actions do not fit at ${width}px: ${JSON.stringify(layout)}`);
        }
        result.jobHeaderBreakpoints = layouts;
        await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
      }
      if (entry.id === "mobile-guide") {
        result.mobileGuideWorkflow = await evaluate(`(() => {
          const link=document.querySelector(".mobile-guide-link a"),image=document.querySelector(".mobile-guide-qr img"),target=link?new URL(link.href):null,qr=image?new URL(image.src):null,original=location.pathname+location.search+location.hash;
          history.replaceState({},"",target?.href||"/");const requestedPage=requestedInitialPage();history.replaceState({},"",original);
          return {stepCount:document.querySelectorAll(".mobile-guide-step").length,targetPage:target?.searchParams.get("page")||"",requestedPage,qrTarget:qr?.searchParams.get("target")||"",manualLink:link?.href||""};
        })()`);
        const flow = result.mobileGuideWorkflow;
        if (flow.stepCount !== 4 || flow.targetPage !== "stock" || flow.requestedPage !== "stock" || flow.qrTarget !== flow.manualLink) throw new Error(`Mobile guide does not hand off to the stock scanner route: ${JSON.stringify(flow)}`);
        const qrBase64 = execFileSync(process.env.PYTHON || "python", ["-c", "import base64,io,sys,qrcode; image=qrcode.make(sys.argv[1]); output=io.BytesIO(); image.save(output,format='PNG'); print(base64.b64encode(output.getvalue()).decode('ascii'))", flow.manualLink], { encoding: "ascii", windowsHide: true }).trim();
        flow.qrImageAudit = await evaluate(`(async () => {const image=document.querySelector(".mobile-guide-qr img");if(!image)return{loaded:false,width:0};document.querySelector(".mobile-guide-qr-error")?.remove();image.hidden=false;image.src="data:image/png;base64,${qrBase64}";await new Promise(resolve=>{if(image.complete)return resolve();image.onload=resolve;image.onerror=resolve});return{loaded:image.complete&&image.naturalWidth>0,width:image.naturalWidth}})()`);
        if (!flow.qrImageAudit.loaded || flow.qrImageAudit.width < 100) throw new Error(`Mobile guide QR capture fixture failed: ${JSON.stringify(flow.qrImageAudit)}`);
      }
      if (entry.id === "customers") {
        result.customerFixture = await evaluate(`(() => {db.customers=${JSON.stringify(customerReferenceFixture)};page="customers";renderNav();render();const rows=[...document.querySelectorAll(".customer-data-table tbody tr")],metrics=[...document.querySelectorAll(".customer-metrics .metric")],filter=document.querySelector(".customer-filterbar"),rect=node=>{const r=node?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{viewport:innerWidth,filterDisplay:getComputedStyle(filter).display,filterGrid:getComputedStyle(filter).gridTemplateColumns,customerCount:db.customers.length,sidebarCustomerCount:document.querySelector('.nav-button[data-page="customers"] .nav-count-badge')?.textContent||"",visibleRows:rows.length,pageIndicator:document.querySelector("#customerPageIndicator")?.textContent||"",firstCustomer:rows[0]?.querySelector(".customer-id")?.textContent||"",firstNameLayout:(()=>{const row=rows[0],cell=row?.querySelector(".customer-name-cell"),name=row?.querySelector(".customer-name"),strong=name?.querySelector("strong"),text=strong?.querySelector("span"),vip=strong?.querySelector("em"),box=node=>{const r=node?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};return{text:text?.textContent,cell:box(cell),name:box(name),strong:box(strong),textRect:box(text),vip:box(vip),computed:{cell:getComputedStyle(cell).display,nameFlex:getComputedStyle(name).flex,strongDisplay:getComputedStyle(strong).display}}})(),visibleCustomerIds:rows.map(row=>row.querySelector(".customer-id")?.textContent||""),rowActions:rows.slice(0,5).map(row=>({id:row.querySelector(".customer-id")?.textContent||"",actions:[...row.querySelectorAll("[data-action]")].map(button=>button.dataset.action)})),balanceCells:rows.slice(0,2).map(row=>({id:row.querySelector(".customer-id")?.textContent||"",amount:row.querySelector(".customer-balance-primary strong")?.textContent.trim()||"",status:row.querySelector(".customer-balance-primary .balance-tag")?.textContent.trim()||"",secondary:row.querySelector(".customer-balance-secondary")?.textContent.trim()||""})),rowActionFits:(()=>{const actions=rows[0]?.lastElementChild?.querySelector(".customer-row-actions");return !!actions&&actions.scrollWidth<=actions.clientWidth+1})(),whatsAppUrl:(()=>{const original=window.open;let url="";window.open=target=>{url=String(target)};openCustomerWhatsApp(db.customers.find(customer=>String(customer.id)==="1"));window.open=original;return url})(),metricValues:metrics.map(node=>node.querySelector("strong")?.textContent.trim()||""),expectedMetricValues:["\u20ba22,300.00 TRY","\u20ba0.00 TRY","4 Adet Aktif"],metricCaptions:metrics.slice(0,3).map(node=>node.querySelector(".customer-metric-caption")?.textContent.trim()||""),metricSecondary:metrics.slice(0,2).map(node=>node.querySelector(".customer-metric-secondary")?.textContent.trim()||""),headerRect:rect(document.querySelector(".customer-page-head")),headerMinHeight:getComputedStyle(document.querySelector(".customer-page-head")).minHeight,searchRect:rect(document.querySelector("#customerSearch")),typeFilterRect:rect(document.querySelector("#customerTypeFilter")),locationFilterRect:rect(document.querySelector("#customerLocationFilter")),balanceFilterRect:rect(document.querySelector("#customerBalanceFilter")),tableRect:rect(document.querySelector(".customer-card .table-wrap"))}})()`);
        result.customerFixture.rowHeight = await evaluate(`(() => { const row=document.querySelector(".customer-data-table tbody tr"); return row ? Math.round(row.getBoundingClientRect().height) : 0; })()`);
        if (result.customerFixture.rowHeight !== 80) throw new Error(`Customer row height diverged from the native 80px row: ${result.customerFixture.rowHeight}`);
        if (result.customerFixture.customerCount !== 28 || result.customerFixture.sidebarCustomerCount !== "28" || result.customerFixture.firstNameLayout?.cell?.[2] < 180 || result.customerFixture.firstNameLayout?.textRect?.[2] < 50 || result.customerFixture.firstNameLayout?.vip?.[0] < result.customerFixture.firstNameLayout?.textRect?.[0] + result.customerFixture.firstNameLayout?.textRect?.[2] || result.customerFixture.visibleRows !== 10 || result.customerFixture.pageIndicator !== "1 / 3" || result.customerFixture.headerRect?.[0] !== 278 || result.customerFixture.headerRect?.[1] < 72 || result.customerFixture.headerRect?.[1] > 84 || result.customerFixture.headerRect?.[3] !== 112 || result.customerFixture.tableRect?.[1] < 445 || result.customerFixture.tableRect?.[1] > 453 || result.customerFixture.balanceCells?.[0]?.amount !== "₺8,100.00" || result.customerFixture.balanceCells?.[0]?.status !== "Alacak" || result.customerFixture.balanceCells?.[0]?.secondary !== "USD: $235.00" || result.customerFixture.balanceCells?.[1]?.amount !== "₺0.00" || result.customerFixture.balanceCells?.[1]?.secondary) throw new Error(`Customer parity fixture did not match the native first-page layout and balances: ${JSON.stringify(result.customerFixture)}`);
        if (JSON.stringify(result.customerFixture.visibleCustomerIds.slice(0, 7)) !== JSON.stringify(["#001", "#002", "#058", "#025", "#044", "#019", "#032"])) throw new Error(`Customer table order diverged from the desktop reference rows: ${JSON.stringify(result.customerFixture.visibleCustomerIds)}`);
        if (JSON.stringify(result.customerFixture.rowActions.map(row=>[row.id,row.actions])) !== JSON.stringify([["#001",["customer-open-services","customer-whatsapp","customer-actions"]],["#002",["customer-actions"]],["#058",["customer-open-360","customer-actions"]],["#025",["customer-actions"]],["#044",["customer-debt-reminder","customer-actions"]]])) throw new Error(`Customer row actions diverged from the desktop rules: ${JSON.stringify(result.customerFixture.rowActions)}`);
        if (!result.customerFixture.rowActionFits) throw new Error("Customer service/WhatsApp/more controls overflow the action cell.");
        if (result.customerFixture.whatsAppUrl !== "https://wa.me/905550000001") throw new Error(`Customer WhatsApp phone normalization failed: ${result.customerFixture.whatsAppUrl}`);
        result.customerActionWorkflow = await evaluate(`(async()=>{const row=[...document.querySelectorAll(".customer-data-table tbody tr")].find(item=>item.querySelector(".customer-id")?.textContent==="#002");row.querySelector('[data-action="customer-actions"]').click();await new Promise(resolve=>setTimeout(resolve,30));const menuTitle=document.querySelector("#dialogTitle").textContent;const actions=[...document.querySelectorAll("#appDialog .product-picker [data-modal-action]")].map(button=>button.dataset.modalAction);document.querySelector('#appDialog [data-modal-action="service-invoice"]').click();await new Promise(resolve=>setTimeout(resolve,50));const invoiceEmptyState=!!document.querySelector("#appDialog").open&&!!document.querySelector("#dialogBody")?.innerText.trim();document.querySelector("#appDialog").close();row.querySelector('[data-action="customer-actions"]').click();await new Promise(resolve=>setTimeout(resolve,30));document.querySelector('#appDialog [data-modal-action="delete"]').click();const deleteConfirmation=!!document.querySelector("#dialogBody")?.innerText.includes(db.customers.find(customer=>String(customer.id)==="2").name);document.querySelector("#appDialog").close();row.querySelector('[data-action="customer-actions"]').click();await new Promise(resolve=>setTimeout(resolve,30));document.querySelector('#appDialog [data-modal-action="customer-notes"]').click();await new Promise(resolve=>setTimeout(resolve,20));const notesOpened=!!document.querySelector("#customerNoteEditor");document.querySelector("#appDialog").close();return{menuTitle,actions,invoiceEmptyState,deleteConfirmation,notesOpened}})()`);
        if (!result.customerActionWorkflow.menuTitle.endsWith(" \u2014 \u0130\u015flemler") || !result.customerActionWorkflow.actions.includes("customer-notes") || !result.customerActionWorkflow.actions.includes("customer-whatsapp") || !result.customerActionWorkflow.actions.includes("debt-reminder") || !result.customerActionWorkflow.actions.includes("service-invoice") || !result.customerActionWorkflow.actions.includes("delete") || !result.customerActionWorkflow.invoiceEmptyState || !result.customerActionWorkflow.deleteConfirmation || !result.customerActionWorkflow.notesOpened) throw new Error(`Customer action menu workflow is incomplete: ${JSON.stringify(result.customerActionWorkflow)}`);
        if (JSON.stringify(result.customerFixture.metricValues.slice(0, 3)) !== JSON.stringify(result.customerFixture.expectedMetricValues) || JSON.stringify(result.customerFixture.metricCaptions) !== JSON.stringify(["4 Bor\u00e7lu M\u00fc\u015fteri Portf\u00f6y\u00fc","Dengeli \u2022 A\u00e7\u0131k Avans Yok","3 At\u00f6lye Montaj \u2022 1 Testte"]) || JSON.stringify(result.customerFixture.metricSecondary) !== JSON.stringify(["USD: $235.00","USD: $0.00"])) throw new Error(`Customer summary values diverged from the desktop fixture: ${JSON.stringify(result.customerFixture)}`);
        if (result.customerFixture.searchRect?.[0] !== 288 || result.customerFixture.searchRect?.[2] !== 994 || result.customerFixture.searchRect?.[1] >= result.customerFixture.typeFilterRect?.[1] || result.customerFixture.typeFilterRect?.[0] !== 330 || result.customerFixture.locationFilterRect?.[0] !== 550 || result.customerFixture.balanceFilterRect?.[0] !== 815 || result.customerFixture.tableRect?.[0] !== 278 || result.customerFixture.tableRect?.[1] !== 449 || result.customerFixture.tableRect?.[2] !== 1004 || result.customerFixture.tableRect?.[3] !== 310) throw new Error(`Customer filter rows or table viewport diverged from the desktop layout: ${JSON.stringify(result.customerFixture)}`);
        const customerListParity = await evaluate(`(() => {
          const headers = [...document.querySelectorAll(".customer-data-table thead th")].map(node => node.textContent.trim());
          const metricTitles = [...document.querySelectorAll(".customer-metrics .metric .metric-top span:first-child")].map(node => node.textContent.trim());
          const cases = [
            { customer: { type: "Kurumsal", is_active: 1, is_problematic: 0 }, status: customerReferenceStatus({ type: "Kurumsal", is_active: 1, is_problematic: 0 }) },
            { customer: { type: "Kurumsal", contract_type: "VIP", is_active: 1 }, status: customerReferenceStatus({ type: "Kurumsal", contract_type: "VIP", is_active: 1 }) },
            { customer: { type: "Bireysel", is_active: 1, is_problematic: 1 }, status: customerReferenceStatus({ type: "Bireysel", is_active: 1, is_problematic: 1 }) },
            { customer: { type: "Bireysel", is_active: 0 }, status: customerReferenceStatus({ type: "Bireysel", is_active: 0 }) }
          ];
          const serviceCustomer = { services: [
            { status: "Test / Onay" }, { status: "Tamirde" }, { status: "Teslimata Hazir" },
            { status: "Tamamlandi" }, { status: "Bekliyor", is_archived: 1 }
          ], quotes: [] };
          const serviceCounts = customerServiceCounts(serviceCustomer);
          const pendingCustomer = { services: [], quotes: [{ status: "sent" }] };
          return { headers, metricTitles, cases, statusClasses: cases.map(item => customerReferenceStatusClass(item.customer)), serviceCounts, serviceSummary: customerServiceSummary(serviceCustomer, serviceCounts), pendingOfferSummary: customerServiceSummary(pendingCustomer) };
        })()`);
        const expectedStatuses = ["Aktif", "Aktif VIP", "\u0130ncelemede", "Pasif"];
        if (customerListParity.headers.length !== 9 || customerListParity.headers[3] !== "SEGMENT" || customerListParity.headers[5] !== "C\u0130HAZ & SERV\u0130SDURUMU" || customerListParity.headers[7] !== "S\u0130STEMDURUMU") throw new Error(`Customer table headers diverged from the desktop column model: ${JSON.stringify(customerListParity.headers)}`);
        if (customerListParity.metricTitles[1] !== "Cari Avans & \u00d6n \u00d6demeler" || customerListParity.metricTitles[2] !== "At\u00f6lye & Servisteki Cihazlar" || customerListParity.metricTitles[3] !== "Kurumsal VIP Portf\u00f6y Oran\u0131") throw new Error(`Customer summary metrics diverged from the desktop labels: ${JSON.stringify(customerListParity.metricTitles)}`);
        if (customerListParity.cases.some((item, index) => item.status !== expectedStatuses[index]) || JSON.stringify(customerListParity.statusClasses) !== JSON.stringify(["active", "vip", "review", "pasif"])) throw new Error(`Customer status mapping diverged from the desktop rules: ${JSON.stringify(customerListParity)}`);
        if (customerListParity.serviceCounts.open !== 3 || customerListParity.serviceCounts.test !== 1 || customerListParity.serviceCounts.repair !== 1 || customerListParity.serviceCounts.deliveryReady !== 1 || customerListParity.serviceCounts.delivered !== 1 || customerListParity.serviceSummary !== "3 Serviste" || customerListParity.pendingOfferSummary !== "1 Teklif Yan\u0131t\u0131 Bekliyor") throw new Error(`Customer service summary diverged from the desktop rules: ${JSON.stringify(customerListParity)}`);
        result.customerListParity = customerListParity;
      }
      if (entry.id === "pc-builder") {
        const pcBuilderLayout = await evaluate(`(() => {
          const content = document.querySelector("#content"), pageRoot = document.querySelector(".pc-builder-page"), tableView = document.querySelector("[data-pc-table-scroll]"), tableHead = document.querySelector(".pc-component-head"), rows = [...document.querySelectorAll(".pc-component-row")];
          const rect = node => { const value = node?.getBoundingClientRect(); return value ? { left: Math.round(value.left), right: Math.round(value.right), width: Math.round(value.width) } : null; };
          return { contentWidth: content?.clientWidth || 0, contentScrollWidth: content?.scrollWidth || 0, documentWidth: document.documentElement.scrollWidth, contentBounds: rect(content), pageRoot: rect(pageRoot), pageGridTemplateColumns: pageRoot ? getComputedStyle(pageRoot).gridTemplateColumns : "", tableView: rect(tableView), tableViewClientWidth: tableView?.clientWidth || 0, tableViewScrollWidth: tableView?.scrollWidth || 0, tableHead: rect(tableHead), tableHeadClientWidth: tableHead?.clientWidth || 0, tableHeadScrollWidth: tableHead?.scrollWidth || 0, lastRow: rect(rows[rows.length - 1]), addComponent: rect(document.querySelector('[data-pc-action="add-component"]')), columns: tableHead ? getComputedStyle(tableHead).gridTemplateColumns.split(" ").length : 0 };
        })()`);
        if (pcBuilderLayout.columns !== 9 || pcBuilderLayout.documentWidth > 1300 || pcBuilderLayout.tableHeadScrollWidth !== 1172 || pcBuilderLayout.lastRow?.width !== 1172 || pcBuilderLayout.tableViewClientWidth >= pcBuilderLayout.tableViewScrollWidth || pcBuilderLayout.tableViewScrollWidth !== 1172 || !pcBuilderLayout.addComponent) throw new Error(`PC Builder native-width component surface diverged: ${JSON.stringify(pcBuilderLayout)}`);
        result.pcBuilderLayout = pcBuilderLayout;
        const pcBuilderScroll = await evaluate(`(()=>{const view=document.querySelector("[data-pc-table-scroll]"),head=document.querySelector(".pc-component-head"),row=document.querySelector(".pc-component-row"),action=row?.lastElementChild;if(!view||!head||!action)return null;const viewport=view.getBoundingClientRect(),headStart=head.getBoundingClientRect().left,max=Math.max(0,view.scrollWidth-view.clientWidth);view.scrollLeft=max;const actionRect=action.getBoundingClientRect(),result={maxScroll:max,scrollLeft:view.scrollLeft,headerShift:Math.round(headStart-head.getBoundingClientRect().left),lastActionVisible:actionRect.left>=viewport.left-1&&actionRect.right<=viewport.right+1};view.scrollLeft=0;return result})()`);
        if (!pcBuilderScroll || pcBuilderScroll.maxScroll < 1 || pcBuilderScroll.scrollLeft < pcBuilderScroll.maxScroll - 1 || pcBuilderScroll.headerShift < 1 || !pcBuilderScroll.lastActionVisible) throw new Error(`PC Builder hidden columns are not horizontally accessible: ${JSON.stringify(pcBuilderScroll)}`);
        result.pcBuilderScroll = pcBuilderScroll;
        await evaluate(`(()=>{const view=document.querySelector("[data-pc-table-scroll]");window.__pcBuilderAuditScrollY=window.scrollY;view.scrollLeft=0;view.focus({preventScroll:true});return true})()`);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowRight", code: "ArrowRight", windowsVirtualKeyCode: 39 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "ArrowRight", code: "ArrowRight", windowsVirtualKeyCode: 39 });
        result.pcBuilderKeyboardScroll = await evaluate(`(()=>{const view=document.querySelector("[data-pc-table-scroll]"),before=window.__pcBuilderAuditScrollY,style=view?getComputedStyle(view):null,result={tabIndex:view?.tabIndex??-1,role:view?.getAttribute("role")||"",label:view?.getAttribute("aria-label")||"",focused:document.activeElement===view,scrollLeft:view?.scrollLeft||0,focusOutline:style?.outlineStyle||"",focusOutlineWidth:style?.outlineWidth||"",scrollYBefore:before,scrollYAfterFocus:window.scrollY};view?.blur();if(view)view.scrollLeft=0;window.scrollTo(0,before);result.scrollYRestored=window.scrollY===before;delete window.__pcBuilderAuditScrollY;return result})()`);
        if (result.pcBuilderKeyboardScroll.tabIndex !== 0 || result.pcBuilderKeyboardScroll.role !== "region" || result.pcBuilderKeyboardScroll.label !== "Bile\u015fen tablosu" || !result.pcBuilderKeyboardScroll.focused || result.pcBuilderKeyboardScroll.scrollLeft <= 0 || result.pcBuilderKeyboardScroll.focusOutline !== "solid" || result.pcBuilderKeyboardScroll.focusOutlineWidth !== "2px" || !result.pcBuilderKeyboardScroll.scrollYRestored) throw new Error(`PC Builder table is not keyboard-accessible or the audit did not restore page position: ${JSON.stringify(result.pcBuilderKeyboardScroll)}`);
        await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
        await delay(35);
        const pcBuilderWideLayout = await evaluate(`(() => {const content=document.querySelector("#content"),head=document.querySelector(".pc-component-head"),last=[...document.querySelectorAll(".pc-component-row")].at(-1),right=node=>node?Math.round(node.getBoundingClientRect().right):0;return{contentWidth:content?.clientWidth||0,contentScrollWidth:content?.scrollWidth||0,contentRight:right(content),headerRight:right(head),rowRight:right(last),columns:head?getComputedStyle(head).gridTemplateColumns.split(" ").length:0}})()`);
        if (pcBuilderWideLayout.columns !== 9 || pcBuilderWideLayout.contentScrollWidth > pcBuilderWideLayout.contentWidth + 2 || pcBuilderWideLayout.headerRight > pcBuilderWideLayout.contentRight + 2 || pcBuilderWideLayout.rowRight > pcBuilderWideLayout.contentRight + 2) throw new Error(`PC Builder columns overflow at 1440px: ${JSON.stringify(pcBuilderWideLayout)}`);
        result.pcBuilderWideLayout = pcBuilderWideLayout;
        await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
        result.pcBuilderWorkflow = await evaluate(`(async()=>{
          const originalApi=apiFetch,calls=[],parts=[{id:990001,category:"Anakart",name:"QA Motherboard ATX",code:"ASUS QA",price:100,stock:5}],customers=[{id:990001,name:"QA Customer"}];
          try{
            apiFetch=async(path,options={})=>{if(path==="/api/desktop/table/parts?limit=1000")return{rows:parts};if(path==="/api/desktop/table/customers?limit=1000")return{rows:customers};calls.push({path,method:options.method||"GET",body:options.body?JSON.parse(options.body):null});return{}};
            render();await new Promise(resolve=>setTimeout(resolve,80));
            const product=document.querySelector('[data-pc-product]'),customer=document.querySelector("#pcCustomer");
            if(!product||![...product.options].some(option=>option.value==="990001")||!customer||![...customer.options].some(option=>option.value==="990001"))return{fixtureLoaded:false,calls};
            product.value="990001";product.dispatchEvent(new Event("change",{bubbles:true}));customer.value="990001";customer.dispatchEvent(new Event("change",{bubbles:true}));
            document.querySelector('[data-pc-action="save"]')?.click();await new Promise(resolve=>setTimeout(resolve,30));
            document.querySelector('[data-pc-action="stock"]')?.click();await new Promise(resolve=>setTimeout(resolve,80));
            const stockCallCount=calls.filter(call=>call.path==="/api/desktop/pc-builder/deduct-stock").length,quantity=document.querySelector("[data-pc-qty]");if(quantity){quantity.value="6";quantity.dispatchEvent(new Event("input",{bubbles:true}));}
            document.querySelector('[data-pc-action="stock"]')?.click();await new Promise(resolve=>setTimeout(resolve,30));
            if(quantity){quantity.value="1";quantity.dispatchEvent(new Event("input",{bubbles:true}));}
            document.querySelector('[data-pc-action="finance"]')?.click();await new Promise(resolve=>setTimeout(resolve,30));
            const save=calls.find(call=>call.path==="/api/desktop/table/audit_logs"),note=calls.find(call=>call.path==="/api/desktop/table/customer_notes"),stock=calls.find(call=>call.path==="/api/desktop/pc-builder/deduct-stock"),finance=calls.find(call=>call.path==="/api/desktop/table/accounting");
            return{fixtureLoaded:true,saveLogged:save?.body?.table_name==="pc_offers",customerNote:note?.body?.customer_id===990001&&note.body.title.includes("PC Teklif"),savedTotal:note?.body?.content?.includes("144.00")||false,stockItems:stock?.body?.items||[],insufficientStockBlocked:stockCallCount===calls.filter(call=>call.path==="/api/desktop/pc-builder/deduct-stock").length,financeAmount:finance?.body?.amount||0,financeCustomerId:finance?.body?.customer_id||null,requestPaths:calls.map(call=>call.path)};
          }finally{apiFetch=originalApi;document.querySelector('[data-pc-action="clear"]')?.click();render();const restored=await new Promise(resolve=>{let attempts=0;const check=()=>{if(document.querySelectorAll(".pc-component-row").length>=15)return resolve(true);if(++attempts>=100)return resolve(false);setTimeout(check,20)};check()});if(!restored)throw Error("PC Builder route fixture did not restore its baseline rows");}
        })()`);
        if (!result.pcBuilderWorkflow.fixtureLoaded || !result.pcBuilderWorkflow.saveLogged || !result.pcBuilderWorkflow.customerNote || !result.pcBuilderWorkflow.savedTotal || result.pcBuilderWorkflow.stockItems.length !== 1 || String(result.pcBuilderWorkflow.stockItems[0].part_id) !== "990001" || result.pcBuilderWorkflow.stockItems[0].quantity !== 1 || !result.pcBuilderWorkflow.insufficientStockBlocked || result.pcBuilderWorkflow.financeAmount !== 144 || result.pcBuilderWorkflow.financeCustomerId !== 990001) throw new Error(`PC Builder save, stock, pricing, or finance workflow diverged from the desktop contract: ${JSON.stringify(result.pcBuilderWorkflow)}`);
      }
      if (entry.id === "job-reports") {
        result.jobReportCaptureState = await evaluate(`(() => {ayecJobReportTab="jobs";ayecJobReportPage=0;document.querySelectorAll("[data-job-report-tab]").forEach(button=>button.classList.toggle("active",button.dataset.jobReportTab===ayecJobReportTab));const dateEnabled=document.querySelector("#jobReportDateEnabled"),start=document.querySelector("#jobReportStart"),end=document.querySelector("#jobReportEnd");dateEnabled.checked=true;if(!start.value)start.value="2026-09-01";if(!end.value)end.value="2026-09-30";ayecJobReportRender();const first=document.querySelector('.job-report-table tbody tr[data-job-report-kind="job"]'),cell=first?.cells[0],rect=cell?.getBoundingClientRect();return{activeTab:document.querySelector("[data-job-report-tab].active")?.dataset.jobReportTab||"",rowCount:document.querySelectorAll(".job-report-table tbody tr[data-job-report-kind]").length,dateEnabled:dateEnabled.checked,start:start.value,end:end.value,firstJobCell:rect?{x:Math.round(rect.x),y:Math.round(rect.y)}:null,columnWidths:first?[...first.cells].map(node=>Math.round(node.getBoundingClientRect().width)):[]}})()`);
        if (result.jobReportCaptureState.activeTab !== "jobs" || result.jobReportCaptureState.rowCount < 1 || !result.jobReportCaptureState.dateEnabled || !result.jobReportCaptureState.start || !result.jobReportCaptureState.end || result.jobReportCaptureState.firstJobCell?.x !== 284 || result.jobReportCaptureState.firstJobCell?.y !== 496 || JSON.stringify(result.jobReportCaptureState.columnWidths) !== JSON.stringify([122,111,84,110,126,78,68,99,116,82])) throw new Error(`Job report baseline or native table geometry was not restored: ${JSON.stringify(result.jobReportCaptureState)}`);
        result.jobReportViewWorkflow = await evaluate(`(async () => {const button=document.querySelector("[data-job-report-view]"),row=button?.closest("tr[data-job-report-kind]"),key=button?.dataset.jobReportView,expectedTitle=row?.cells[0]?.textContent.trim()||"",data=window.currentGenericData,previousColumns=data?.columns;if(data)data.columns=[...new Set([...(previousColumns||[]),"password","token","secret","photo_url"])];button?.click();const dialog=document.querySelector("#appDialog"),fields=[...document.querySelectorAll("#dialogBody .field input")],labels=[...document.querySelectorAll("#dialogBody .field label")].map(label=>label.textContent.trim()),title=document.querySelector("#dialogTitle")?.textContent.trim()||"",close=document.querySelector("#dialogSubmit"),closeLabel=close?.textContent.trim()||"",audit={rowKey:key,rowVisible:!!row,opened:!!dialog?.open,title,expectedTitle,titleMatches:!!expectedTitle&&title.includes(expectedTitle),fieldCount:fields.length,allFieldsReadOnly:fields.length>0&&fields.every(field=>field.readOnly),sensitiveFieldsHidden:!labels.some(label=>/password|token|secret|photo/i.test(label)),closeLabelMatches:closeLabel==="Kapat"};let submitSeen=false;document.querySelector("#dialogForm")?.addEventListener("submit",()=>{submitSeen=true},{once:true});close?.click();for(let attempt=0;attempt<20&&dialog?.open;attempt+=1)await new Promise(resolve=>setTimeout(resolve,25));audit.closedAfterKapat=!!dialog&&!dialog.open;audit.submitSeen=submitSeen;audit.dialogReturnValue=dialog?.returnValue||"";audit.appScript=document.querySelector('script[src*="app.js"]')?.getAttribute("src")||"";if(data)data.columns=previousColumns;if(dialog?.open)dialog.close("cancel");return audit;})()`);
        if (!result.jobReportViewWorkflow.rowVisible || !result.jobReportViewWorkflow.opened || !result.jobReportViewWorkflow.titleMatches || result.jobReportViewWorkflow.fieldCount < 1 || !result.jobReportViewWorkflow.allFieldsReadOnly || !result.jobReportViewWorkflow.sensitiveFieldsHidden || !result.jobReportViewWorkflow.closeLabelMatches || !result.jobReportViewWorkflow.closedAfterKapat) throw new Error(`Job report detail view did not display safe read-only fields or close through its Kapat action: ${JSON.stringify(result.jobReportViewWorkflow)}`);
        result.jobReportContextWorkflow = await evaluate(`(async () => {const row=document.querySelector('.job-report-table tbody tr[data-job-report-kind="job"]'),tracking=row?.cells[0]?.textContent.trim()||"";row?.dispatchEvent(new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:520}));const menu=document.querySelector('.service-list-context-menu'),detail=menu?.querySelector('[data-job-report-context="detail"]'),menuOpened=!!menu&&menu.getAttribute("role")==="menu",menuItemVisible=!!detail&&detail.getAttribute("role")==="menuitem";detail?.click();const dialog=document.querySelector("#appDialog"),title=document.querySelector("#dialogTitle")?.textContent.trim()||"",eyebrow=document.querySelector("#dialogEyebrow")?.textContent.trim()||"",historyRows=document.querySelectorAll("#dialogBody .field.full tbody tr").length,close=document.querySelector("#dialogSubmit"),closeLabel=close?.textContent.trim()||"";close?.click();for(let attempt=0;attempt<20&&dialog?.open;attempt+=1)await new Promise(resolve=>setTimeout(resolve,25));const closedAfterKapat=!!dialog&&!dialog.open;row?.focus();row?.dispatchEvent(new KeyboardEvent("keydown",{key:"ContextMenu",bubbles:true}));const keyboardMenu=document.querySelector('.service-list-context-menu'),keyboardMenuOpened=!!keyboardMenu&&!!keyboardMenu.querySelector('[data-job-report-context="detail"]');keyboardMenu?.remove();if(dialog?.open)dialog.close("cancel");return{tracking,menuOpened,menuItemVisible,dialogOpened:!!dialog?.returnValue||!!dialog?.open,titleMatches:!!tracking&&title.includes(tracking),eyebrow,historyRows,closeLabelMatches:closeLabel==="Kapat",closedAfterKapat,keyboardMenuOpened}})()`);
        if (!result.jobReportContextWorkflow.menuOpened || !result.jobReportContextWorkflow.menuItemVisible || !result.jobReportContextWorkflow.dialogOpened || !result.jobReportContextWorkflow.titleMatches || result.jobReportContextWorkflow.historyRows < 1 || result.jobReportContextWorkflow.eyebrow.length < 1 || !result.jobReportContextWorkflow.closeLabelMatches || !result.jobReportContextWorkflow.closedAfterKapat || !result.jobReportContextWorkflow.keyboardMenuOpened) throw new Error(`Job report pointer or keyboard context actions did not open and close the transaction detail: ${JSON.stringify(result.jobReportContextWorkflow)}`);
        result.jobReportSelectionWorkflow = await evaluate(`(() => {const rows=[...document.querySelectorAll(".job-report-table tbody tr[data-job-report-kind]")],row=rows[0],selectVisible=document.querySelector("[data-job-report-select-visible]");ayecJobReportSelected.clear();ayecJobReportSyncSelection();row?.cells[0]?.click();const clickSelected=row?.getAttribute("aria-selected")==="true";row?.dispatchEvent(new KeyboardEvent("keydown",{key:" ",bubbles:true}));const spaceDeselected=row?.getAttribute("aria-selected")==="false";row?.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}));const enterSelected=row?.getAttribute("aria-selected")==="true";selectVisible?.click();const selectedRows=rows.filter(item=>item.getAttribute("aria-selected")==="true").length,selectedCount=ayecJobReportSelected.size,selectionText=document.querySelector(".job-report-selection-count")?.textContent.trim()||"";ayecJobReportSelected.clear();ayecJobReportSyncSelection();return{rowCount:rows.length,clickSelected,spaceDeselected,enterSelected,selectedRows,selectedCount,selectionText}})()`);
        if (!result.jobReportSelectionWorkflow.clickSelected || !result.jobReportSelectionWorkflow.spaceDeselected || !result.jobReportSelectionWorkflow.enterSelected || result.jobReportSelectionWorkflow.rowCount < 1 || result.jobReportSelectionWorkflow.selectedRows !== result.jobReportSelectionWorkflow.rowCount || result.jobReportSelectionWorkflow.selectedCount !== result.jobReportSelectionWorkflow.rowCount || !result.jobReportSelectionWorkflow.selectionText.includes(String(result.jobReportSelectionWorkflow.rowCount))) throw new Error(`Job report row selection did not respond to pointer, keyboard, or select-visible actions: ${JSON.stringify(result.jobReportSelectionWorkflow)}`);
        result.jobReportPrintWorkflow = await evaluate(`(() => {const rows=[...document.querySelectorAll(".job-report-table tbody tr")],button=document.querySelector("[data-job-report-print-row]"),toolbar=document.querySelector("[data-job-report-print]"),originalPrint=window.print,initial=rows.map(row=>row.hidden);let printCalls=0,rowDuring=[],toolbarDuring=[];try{window.print=()=>{printCalls+=1};button?.click();const targetIndex=rows.indexOf(button?.closest("tr"));rowDuring=rows.map(row=>row.hidden);window.dispatchEvent(new Event("afterprint"));const restored=JSON.stringify(rows.map(row=>row.hidden))===JSON.stringify(initial);toolbar?.click();toolbarDuring=rows.map(row=>row.hidden);return{rowCount:rows.length,rowPrintCalled:printCalls>=1,targetVisibleDuring:targetIndex>=0&&rowDuring[targetIndex]===false,otherRowsHiddenDuring:rowDuring.filter((value,index)=>index!==targetIndex).every(Boolean),restored,toolbarPrintCalled:printCalls===2,allRowsVisibleDuringToolbar:toolbarDuring.every(value=>!value)}}finally{window.print=originalPrint}})()`);
        if (result.jobReportPrintWorkflow.rowCount < 1 || !result.jobReportPrintWorkflow.rowPrintCalled || !result.jobReportPrintWorkflow.targetVisibleDuring || !result.jobReportPrintWorkflow.otherRowsHiddenDuring || !result.jobReportPrintWorkflow.restored || !result.jobReportPrintWorkflow.toolbarPrintCalled || !result.jobReportPrintWorkflow.allRowsVisibleDuringToolbar) throw new Error(`Job report print actions did not isolate a selected row or preserve the full-table print state: ${JSON.stringify(result.jobReportPrintWorkflow)}`);
      }
      if (entry.id === "job-reports") await evaluate("document.activeElement?.blur?.()");
      if (entry.id === "appointments") {
        result.appointmentMatchedFixture = await evaluate(`(() => {
          window.__routeSmokeAppointmentOriginal = { appointments: db.appointments, personnel: db.personnel, personnelRows: ayecAppointmentPersonnelRows };
          const person = { id: 71, name: "QA Tech", role: "Teknisyen", active: 1 };
          db.appointments = [{ id: 71, customerId: 71, customer: "QA Customer", title: "QA Calendar Slot", description: "QA Calendar Slot", date: today(), time: "14:30", technician: "QA Tech", technician_name: "QA Tech", status: "Planlandi", color: "#2563EB", priority: "Normal" }];
          db.personnel = [person];
          ayecAppointmentPersonnelRows = [person];
          ayecAppointmentPersonnelPromise = null;
          render();
          const visibleAppointments = document.querySelectorAll(".appointment-ref-calendar .appointment-ref-event").length;
          const technicianStatus = document.querySelector(".appointment-ref-tech-status header b")?.textContent.trim() || "";
          return { visibleAppointments, technicianStatus, technicianNames: [...document.querySelectorAll(".appointment-ref-tech-row b")].map(node => node.textContent.trim()) };
        })()`);
        if (result.appointmentMatchedFixture.visibleAppointments !== 1 || result.appointmentMatchedFixture.technicianStatus !== "1/1 Aktif" || result.appointmentMatchedFixture.technicianNames.join(",") !== "QA Tech") throw new Error(`Appointment comparison fixture does not match the native capture data: ${JSON.stringify(result.appointmentMatchedFixture)}`);
        result.appointmentSlotCreateWorkflow = await evaluate(`(() => {const date=today(),slot=[...document.querySelectorAll(".appointment-ref-slot")].find(item=>item.dataset.date===date&&item.dataset.time==="15:00");slot?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));const dialog=document.querySelector("#appDialog"),wasOpen=!!dialog?.open,title=document.querySelector("#dialogTitle")?.textContent.trim()||"",dateValue=document.querySelector('#dialogBody [name="date"]')?.value||"",timeValue=document.querySelector('#dialogBody [name="time"]')?.value||"",workflow=document.querySelector('#dialogBody [name="workflow"]')?.value||"";document.querySelector("#dialogClose")?.click();return{slotFound:!!slot,opened:wasOpen,titleMatches:title.startsWith("Yeni Randevu"),dateMatches:dateValue===date,timeMatches:timeValue==="15:00",defaultWorkflow:workflow,closedWithCloseButton:!!dialog&&!dialog.open}})()`);
        if (!result.appointmentSlotCreateWorkflow.slotFound || !result.appointmentSlotCreateWorkflow.opened || !result.appointmentSlotCreateWorkflow.titleMatches || !result.appointmentSlotCreateWorkflow.dateMatches || !result.appointmentSlotCreateWorkflow.timeMatches || result.appointmentSlotCreateWorkflow.defaultWorkflow !== "service" || !result.appointmentSlotCreateWorkflow.closedWithCloseButton) throw new Error(`Empty calendar slot did not open a correctly prefilled new appointment form: ${JSON.stringify(result.appointmentSlotCreateWorkflow)}`);
        result.appointmentEditWorkflow = await evaluate(`(() => {const card=document.querySelector('.appointment-ref-calendar .appointment-ref-event[data-id="71"]');card?.dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));const dialog=document.querySelector("#appDialog"),wasOpen=!!dialog?.open,title=document.querySelector("#dialogTitle")?.textContent.trim()||"",dateValue=document.querySelector('#dialogBody [name="date"]')?.value||"",timeValue=document.querySelector('#dialogBody [name="time"]')?.value||"";document.querySelector("#dialogClose")?.click();return{cardFound:!!card,opened:wasOpen,titleMatches:title.startsWith("Randevuyu"),dateMatches:dateValue===today(),desktopHourValue:timeValue,closedWithCloseButton:!!dialog&&!dialog.open}})()`);
        if (!result.appointmentEditWorkflow.cardFound || !result.appointmentEditWorkflow.opened || !result.appointmentEditWorkflow.titleMatches || !result.appointmentEditWorkflow.dateMatches || result.appointmentEditWorkflow.desktopHourValue !== "14:00" || !result.appointmentEditWorkflow.closedWithCloseButton) throw new Error(`Double-clicking a calendar appointment did not open its desktop-compatible edit form: ${JSON.stringify(result.appointmentEditWorkflow)}`);
      }
      const routeCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      if (entry.id === "job-reports") await evaluate("apiFetch=window.__routeSmokeApiFetch;delete window.__routeSmokeApiFetch;window.currentGenericData=null");
      if (entry.id === "services") await evaluate("db.customers=window.__routeSmokeOriginalCustomers;delete window.__routeSmokeOriginalCustomers");
      if (entry.id === "service-list") await evaluate("db.serviceDevices=window.__routeSmokeOriginalServiceDevices;delete window.__routeSmokeOriginalServiceDevices");
      const routeScreenshot = path.join(outputDir, "route-captures", `${entry.id}-1300x850.png`);
      fs.mkdirSync(path.dirname(routeScreenshot), { recursive: true });
      fs.writeFileSync(routeScreenshot, Buffer.from(routeCapture.data, "base64"));
      if (entry.id === "job-reports") {
        result.jobReportDescriptionTypography = await evaluate(`(() => {const cell=document.querySelector(".job-report-table tbody tr td:nth-child(4)"),text=cell?.querySelector(".job-report-description")||cell,range=document.createRange();if(text)range.selectNodeContents(text);const r=cell?.getBoundingClientRect(),style=cell?getComputedStyle(cell):null;return{fontSize:style?.fontSize||"",lineHeight:style?.lineHeight||"",textLines:range.getClientRects().length,cellHeight:r?Math.round(r.height):0}})()`);
        if (result.jobReportDescriptionTypography.fontSize !== "10px" || result.jobReportDescriptionTypography.textLines !== 2 || result.jobReportDescriptionTypography.cellHeight !== 54) throw new Error(`Job report description typography diverged from the matched reference row: ${JSON.stringify(result.jobReportDescriptionTypography)}`);
      }
      if (entry.id === "appointments") await evaluate(`(() => {const original=window.__routeSmokeAppointmentOriginal;db.appointments=original.appointments;db.personnel=original.personnel;ayecAppointmentPersonnelRows=original.personnelRows;delete window.__routeSmokeAppointmentOriginal;render()})()`);
      if (entry.id === "field-service") {
        await evaluate(`document.querySelector("[data-field-panel-mode='jobs']")?.click()`);
        const fieldJobsState = await evaluate(`(() => ({count:document.querySelector("#fieldMapCount")?.textContent||"",rows:document.querySelectorAll(".field-map-job").length,visible:document.querySelector("#fieldMapRows")?.hidden===false}))()`);
        if (fieldJobsState.count !== "8" || fieldJobsState.rows !== 8 || !fieldJobsState.visible) throw new Error(`Field-map populated jobs panel was not ready to capture: ${JSON.stringify(fieldJobsState)}`);
        result.fieldServiceJobsCapture = fieldJobsState;
        await evaluate(`document.querySelector("[data-field-panel-mode='customer']")?.click()`);
      }
      if (entry.id === "customers") {
        result.customerTableWorkflow = await evaluate(`(() => {
          const tableRows=()=>[...document.querySelectorAll(".customer-data-table tbody tr")],filteredCount=()=>Number(document.querySelector("#customerFilteredCount")?.textContent||0);
          const initial={page:document.querySelector("#customerPageIndicator")?.textContent||"",count:Number(document.querySelector("#customerCount")?.textContent||0),rows:tableRows().length,filtered:filteredCount()};
          document.querySelector("#customerPageNext")?.click();
          const second={page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount()};
          document.querySelector("#customerPageNext")?.click();
          const third={page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount(),nextDisabled:document.querySelector("#customerPageNext")?.disabled||false};
          const search=document.querySelector("#customerSearch");search.value="Zeynep";search.dispatchEvent(new Event("input",{bubbles:true}));
          const searched={count:Number(document.querySelector("#customerCount")?.textContent||0),rows:tableRows().length,filtered:filteredCount(),name:tableRows()[0]?.textContent||""};
          document.querySelector("#customerSearchClear")?.click();
          const restored={count:Number(document.querySelector("#customerCount")?.textContent||0),page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount()};
          const customerFor=row=>db.customers.find(item=>String(item.id)===String(row.dataset.id));
          const type=document.querySelector("#customerTypeFilter");type.value="vip";type.dispatchEvent(new Event("change",{bubbles:true}));
          const vip={count:Number(document.querySelector("#customerCount")?.textContent||0),rows:tableRows().length,filtered:filteredCount(),allVip:tableRows().every(row=>{const customer=customerFor(row);return String(customer?.contract_type||"").toUpperCase().includes("VIP")||String(customer?.type||"").toLowerCase()==="vip"})};
          type.value="dealer";type.dispatchEvent(new Event("change",{bubbles:true}));
          const dealer={count:Number(document.querySelector("#customerCount")?.textContent||0),rows:tableRows().length,filtered:filteredCount(),allDealers:tableRows().every(row=>String(customerFor(row)?.type||"").toLocaleLowerCase("tr-TR").includes("bayi"))};
          type.value="";type.dispatchEvent(new Event("change",{bubbles:true}));
          const selectAll=document.querySelector("#customerSelectAll");selectAll?.click();
          const selected=document.querySelectorAll(".customer-row-select:checked").length;
          const balanceFilter=document.querySelector("#customerBalanceFilter");balanceFilter.value="debt";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
          const debtRows=tableRows(),debt={count:Number(document.querySelector("#customerCount")?.textContent||0),filtered:filteredCount(),matches:debtRows.length>0&&debtRows.every(row=>Object.values(customerFor(row)?.balances||{}).some(value=>Number(value)<0))};
          balanceFilter.value="credit";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
          const creditRows=tableRows(),credit={count:Number(document.querySelector("#customerCount")?.textContent||0),filtered:filteredCount(),matches:creditRows.length>0&&creditRows.every(row=>Object.values(customerFor(row)?.balances||{}).some(value=>Number(value)>0))};
          balanceFilter.value="zero";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
          const zeroRows=tableRows(),zero={count:Number(document.querySelector("#customerCount")?.textContent||0),filtered:filteredCount(),matches:zeroRows.length>0&&zeroRows.every(row=>Object.values(customerFor(row)?.balances||{}).every(value=>!Number(value)))};
          balanceFilter.value="";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
          const location=document.querySelector("#customerLocationFilter");location.value="Ankara";location.dispatchEvent(new Event("change",{bubbles:true}));
          const locationRows=tableRows(),city={count:Number(document.querySelector("#customerCount")?.textContent||0),filtered:filteredCount(),matches:locationRows.length>0&&locationRows.every(row=>String(customerFor(row)?.city||customerFor(row)?.location||"").toLocaleLowerCase("tr-TR")==="ankara")};
          location.value="";location.dispatchEvent(new Event("change",{bubbles:true}));
          const size=document.querySelector("#customerPageSize");size.value="25";size.dispatchEvent(new Event("change",{bubbles:true}));
          const pageSize25={page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount()};
          size.value="100";size.dispatchEvent(new Event("change",{bubbles:true}));
          const pageSize100={page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount()};
          size.value="10";size.dispatchEvent(new Event("change",{bubbles:true}));
          const pageSize10={page:document.querySelector("#customerPageIndicator")?.textContent||"",rows:tableRows().length,filtered:filteredCount()};
          return{initial,second,third,searched,restored,vip,dealer,selected,debt,credit,zero,city,pageSize25,pageSize100,pageSize10,selectAllChecked:selectAll?.checked||false,checkboxCount:document.querySelectorAll(".customer-row-select").length};
        })()`);
        const flow = result.customerTableWorkflow;
        if (flow.initial.page !== "1 / 3" || flow.initial.count !== 28 || flow.initial.rows !== 10 || flow.initial.filtered !== 10
          || flow.second.page !== "2 / 3" || flow.second.rows !== 10 || flow.second.filtered !== 10
          || flow.third.page !== "3 / 3" || flow.third.rows !== 8 || flow.third.filtered !== 8 || !flow.third.nextDisabled
          || flow.searched.count !== 1 || flow.searched.rows !== 1 || flow.searched.filtered !== 1 || !flow.searched.name.includes("Zeynep")
          || flow.restored.count !== 28 || flow.restored.page !== "1 / 3" || flow.restored.rows !== 10 || flow.restored.filtered !== 10
          || flow.vip.count !== 8 || !flow.vip.allVip || flow.vip.filtered !== flow.vip.rows || flow.dealer.count !== 1 || !flow.dealer.allDealers || flow.dealer.filtered !== 1 || flow.selected !== 10 || !flow.debt.matches || flow.debt.filtered !== flow.debt.count || !flow.credit.matches || flow.credit.filtered !== flow.credit.count || !flow.zero.matches || flow.zero.filtered !== 10 || !flow.city.matches || flow.city.filtered !== flow.city.count
          || flow.pageSize25.page !== "1 / 2" || flow.pageSize25.rows !== 25 || flow.pageSize25.filtered !== 25 || flow.pageSize100.page !== "1 / 1" || flow.pageSize100.rows !== 28 || flow.pageSize100.filtered !== 28 || flow.pageSize10.page !== "1 / 3" || flow.pageSize10.rows !== 10 || flow.pageSize10.filtered !== 10) throw new Error(`Customer search, filters, page controls, or selection diverged: ${JSON.stringify(flow)}`);
      }
      if (entry.id === "manual") {
        result.manualTabWorkflow = await evaluate(`(async () => {
          const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
          const previous = apiFetch;
          const requests = [];
          apiFetch = async (url, ...args) => {
            const address = String(url);
            requests.push(address);
            if (address.includes("document=setup")) return { document: "setup", content: "# Setup Fixture\\n\\nSetup-only marker." };
            return previous(url, ...args);
          };
          const setupTab = document.querySelector('[data-manual-tab="setup"]');
          setupTab?.click();
          for (let attempt = 0; attempt < 80 && !document.querySelector("#manualDocument")?.innerText.includes("Setup-only marker"); attempt += 1) await pause(25);
          const setupLoaded = document.querySelector("#manualDocument")?.innerText.includes("Setup-only marker") === true;
          const setupSelected = setupTab?.getAttribute("aria-selected") === "true";
          const usageTab = document.querySelector('[data-manual-tab="usage"]');
          usageTab?.click();
          for (let attempt = 0; attempt < 80 && !document.querySelector("#manualDocument")?.innerText.includes("Guncel Kullanici Kilavuzu"); attempt += 1) await pause(25);
          const usageRestored = document.querySelector("#manualDocument")?.innerText.includes("Guncel Kullanici Kilavuzu") === true;
          const usageSelected = usageTab?.getAttribute("aria-selected") === "true";
          apiFetch = previous;
          return { setupLoaded, setupSelected, usageRestored, usageSelected, requests };
        })()`);
        if (!result.manualTabWorkflow.setupLoaded || !result.manualTabWorkflow.setupSelected || !result.manualTabWorkflow.usageRestored || !result.manualTabWorkflow.usageSelected || !result.manualTabWorkflow.requests.some(url => url.includes("document=setup")) || !result.manualTabWorkflow.requests.some(url => url.includes("document=usage"))) throw new Error(`Manual guide tabs did not switch documents and restore the usage guide: ${JSON.stringify(result.manualTabWorkflow)}`);
      }
      if (entry.id === "backup") {
        result.backupWorkflow = await evaluate(`(async () => {
          const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
          const previousApiFetch = apiFetch;
          const previousDesktopWrite = desktopWrite;
          const previousFetch = window.fetch;
          const previousCreateObjectURL = URL.createObjectURL;
          const previousRevokeObjectURL = URL.revokeObjectURL;
          const previousAnchorClick = HTMLAnchorElement.prototype.click;
          const previousInputClick = HTMLInputElement.prototype.click;
          const calls = [], fetchCalls = [], downloads = [], objectUrls = [];
          const settingWrites = [];
          const backup = { id: "QA-BACKUP-1", filename: "tenant-backup.db", size_bytes: 256, created_at: "2026-10-18 10:00", product_code: "teknik_servis", sha256: "a".repeat(64), source: "web" };
          let backups = [];
          apiFetch = async (url, options = {}) => {
            const address = String(url), method = String(options.method || "GET").toUpperCase();
            calls.push({ address, method, body: options.body || "" });
            if (address === "/api/desktop/backups" && method === "POST") { backups = [backup]; return { ok: true, product_archive_ok: true }; }
            if (address === "/api/desktop/backups") return { backups };
            if (address === "/api/desktop/backups/google-drive/status") return { connected: false, configured: false, redirect_uri: "https://example.test/callback" };
            return window.__routeSmokeEmpty;
          };
          window.fetch = async (url, options = {}) => {
            const address = String(url);
            const headers = options.headers || {};
            fetchCalls.push({ address, method: options.method || "GET", credentials: options.credentials || "", backupName: headers["X-AYEC-Backup-Name"] || "", fileName: options.body?.name || "", fileType: options.body?.type || "", fileSize: options.body?.size || 0 });
            if (address.endsWith("/api/desktop/backups/QA-BACKUP-1/download")) return new Response(new Uint8Array([83, 81, 76, 105, 116, 101]), { status: 200, headers: { "Content-Type": "application/x-sqlite3" } });
            if (address.endsWith("/api/desktop/backups/import")) {
              if (options.body?.name === "qa-bad.db") return new Response(JSON.stringify({ error: "SQLite integrity check failed" }), { status: 400, headers: { "Content-Type": "application/json" } });
              backups = [backup, { ...backup, id: "QA-IMPORTED-2", filename: "qa-import.db", source: "import" }];
              return new Response(JSON.stringify({ ok: true, backup_id: "QA-IMPORTED-2", filename: "qa-import.db", sha256: "b".repeat(64) }), { status: 200, headers: { "Content-Type": "application/json" } });
            }
            return previousFetch(url, options);
          };
          URL.createObjectURL = blob => { objectUrls.push(blob.size); return "blob:qa-backup"; };
          URL.revokeObjectURL = url => { objectUrls.push(url); };
          HTMLAnchorElement.prototype.click = function () { if (this.download) downloads.push({ href: this.href, filename: this.download }); };
          let filePickerOpened = false;
          HTMLInputElement.prototype.click = function () { if (this.id === "backupRestoreFile") { filePickerOpened = true; return; } return previousInputClick.call(this); };
          try {
            document.querySelector("[data-backup-create]")?.click();
            for (let attempt = 0; attempt < 80 && !document.querySelector("[data-backup-download='QA-BACKUP-1']"); attempt += 1) await pause(25);
            const backupRow = document.querySelector("#tenantBackupRows tbody tr")?.innerText || "";
            document.querySelector("[data-backup-download='QA-BACKUP-1']")?.click();
            for (let attempt = 0; attempt < 80 && !downloads.length; attempt += 1) await pause(25);
            await pause(20);
            const dailyEnabled = document.querySelector('[data-setting-key="backup_daily_enabled"]');
            const dailyTime = document.querySelector('[data-setting-key="backup_daily_time"]');
            const timeDisabledInitially = dailyTime?.disabled === true;
            dailyEnabled.checked = true;
            dailyEnabled.dispatchEvent(new Event("change", { bubbles: true }));
            const timeEnabledAfterToggle = dailyTime?.disabled === false;
            dailyTime.value = "03:45";
            desktopWrite = async (scope, payload) => { settingWrites.push({ scope, ...payload }); return { ok: true }; };
            document.querySelector("[data-backup-save-settings]")?.click();
            for (let attempt = 0; attempt < 80 && document.querySelector("[data-backup-save-settings]")?.disabled; attempt += 1) await pause(25);
            const restoreFile = document.querySelector("#backupRestoreFile");
            document.querySelector("[data-backup-stage]")?.click();
            const importFile = new File([new Uint8Array([83, 81, 76, 105, 116, 101])], "qa-import.db", { type: "application/x-sqlite3" });
            Object.defineProperty(restoreFile, "files", { configurable: true, value: [importFile] });
            restoreFile.dispatchEvent(new Event("change", { bubbles: true }));
            for (let attempt = 0; attempt < 80 && !document.querySelector("#appDialog")?.open; attempt += 1) await pause(25);
            const importDialogTitle = document.querySelector("#dialogTitle")?.textContent || "";
            const importDialogBody = document.querySelector("#dialogBody")?.innerText || "";
            const importDialogId = document.querySelector("#dialogBody input[readonly]")?.value || "";
            const importRequest = fetchCalls.find(call => call.address.endsWith("/api/desktop/backups/import"));
            document.querySelector("#dialogSubmit")?.click();
            await pause(25);
            document.querySelectorAll("#toastRoot .toast.error").forEach(node => node.remove());
            const invalidFile = new File(["invalid"], "qa-bad.db", { type: "application/x-sqlite3" });
            Object.defineProperty(restoreFile, "files", { configurable: true, value: [invalidFile] });
            restoreFile.dispatchEvent(new Event("change", { bubbles: true }));
            for (let attempt = 0; attempt < 80 && !document.querySelector("#toastRoot .toast.error")?.textContent.includes("SQLite integrity check failed"); attempt += 1) await pause(25);
            const invalidImport = {
              errorToast: document.querySelector("#toastRoot .toast.error")?.textContent || "",
              dialogOpen: document.querySelector("#appDialog")?.open === true,
              inputReset: restoreFile?.value === "",
              buttonRestored: document.querySelector("[data-backup-stage]")?.disabled === false,
              request: fetchCalls.slice().reverse().find(call => call.address.endsWith("/api/desktop/backups/import")) || null
            };
            return {
              createCalls: calls.filter(call => call.address === "/api/desktop/backups" && call.method === "POST").length,
              listCalls: calls.filter(call => call.address === "/api/desktop/backups" && call.method === "GET").length,
              backupRow,
              downloadCalls: fetchCalls.filter(call => call.address.endsWith("/api/desktop/backups/QA-BACKUP-1/download") && call.credentials === "same-origin").length,
              downloads,
              objectUrls,
              import: {
                filePickerOpened,
                requestMethod: importRequest?.method || "",
                requestCredentials: importRequest?.credentials || "",
                filenameHeader: importRequest?.backupName || "",
                bodyFilename: importRequest?.fileName || "",
                bodyType: importRequest?.fileType || "",
                bodySize: importRequest?.fileSize || 0,
                dialogTitle: importDialogTitle,
                dialogBody: importDialogBody,
                dialogBackupId: importDialogId,
                dialogClosed: document.querySelector("#appDialog")?.open === false,
                inputReset: restoreFile?.value === "",
                buttonRestored: document.querySelector("[data-backup-stage]")?.disabled === false,
                invalidImport
              },
              schedule: {
                timeDisabledInitially,
                timeEnabledAfterToggle,
                dailyEnabled: settingWrites.find(item => item.key === "backup_daily_enabled")?.value,
                dailyTime: settingWrites.find(item => item.key === "backup_daily_time")?.value,
                timezoneSaved: settingWrites.some(item => item.key === "backup_timezone" && Boolean(item.value)),
                writeCount: settingWrites.length
              }
            };
          } finally {
            apiFetch = previousApiFetch;
            desktopWrite = previousDesktopWrite;
            window.fetch = previousFetch;
            URL.createObjectURL = previousCreateObjectURL;
            URL.revokeObjectURL = previousRevokeObjectURL;
            HTMLAnchorElement.prototype.click = previousAnchorClick;
            HTMLInputElement.prototype.click = previousInputClick;
          }
        })()`);
        if (result.backupWorkflow.createCalls !== 1 || result.backupWorkflow.listCalls < 1 || !result.backupWorkflow.backupRow.includes("tenant-backup.db") || result.backupWorkflow.downloadCalls !== 1 || result.backupWorkflow.downloads[0]?.filename !== "tenant-backup.db" || result.backupWorkflow.downloads[0]?.href !== "blob:qa-backup" || result.backupWorkflow.objectUrls[0] !== 6 || result.backupWorkflow.objectUrls[1] !== "blob:qa-backup" || !result.backupWorkflow.schedule.timeDisabledInitially || !result.backupWorkflow.schedule.timeEnabledAfterToggle || result.backupWorkflow.schedule.dailyEnabled !== "1" || result.backupWorkflow.schedule.dailyTime !== "03:45" || !result.backupWorkflow.schedule.timezoneSaved || !result.backupWorkflow.import.filePickerOpened || result.backupWorkflow.import.requestMethod !== "POST" || result.backupWorkflow.import.requestCredentials !== "same-origin" || result.backupWorkflow.import.filenameHeader !== "qa-import.db" || result.backupWorkflow.import.bodyFilename !== "qa-import.db" || result.backupWorkflow.import.bodyType !== "application/x-sqlite3" || result.backupWorkflow.import.bodySize !== 6 || !result.backupWorkflow.import.dialogTitle.includes("Haz\u0131r") || !result.backupWorkflow.import.dialogBody.includes("qa-import.db") || result.backupWorkflow.import.dialogBackupId !== "QA-IMPORTED-2" || !result.backupWorkflow.import.dialogClosed || !result.backupWorkflow.import.inputReset || !result.backupWorkflow.import.buttonRestored || !result.backupWorkflow.import.invalidImport.errorToast.includes("SQLite integrity check failed") || result.backupWorkflow.import.invalidImport.dialogOpen || !result.backupWorkflow.import.invalidImport.inputReset || !result.backupWorkflow.import.invalidImport.buttonRestored || result.backupWorkflow.import.invalidImport.request?.fileName !== "qa-bad.db") throw new Error(`Tenant backup create/list/download/import/schedule browser flow failed: ${JSON.stringify(result.backupWorkflow)}`);
      }
      results.push({ ...result, desktopPageId: entry.desktopPageId, screenshot: routeScreenshot });
      await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
      await delay(35);
      const mobileResult = await evaluate(`(() => { const root=document.documentElement,body=document.body,content=document.querySelector("#content"),shell=document.querySelector(".app-shell"); const offenders=[...document.querySelectorAll("body *")].map(node=>{const rect=node.getBoundingClientRect();return {tag:node.tagName,id:node.id,className:typeof node.className==="string"?node.className:"",right:Math.round(rect.right),width:Math.round(rect.width)}}).filter(item=>item.width>0&&item.right>innerWidth+2).slice(0,8); return {route:${JSON.stringify(entry.id)},page:page||"",bodyPage:body.dataset.page||"",manualLoaded:(document.querySelector("#manualDocument")?.innerText||"").includes("Guncel Kullanici Kilavuzu"),manualHeadingCount:document.querySelectorAll("#manualDocument h1,#manualDocument h2,#manualDocument h3").length,manualTableCount:document.querySelectorAll("#manualDocument table").length,manualTableCells:document.querySelector("#manualDocument table tbody tr")?.innerText||"",shortcutColumns:(()=>{const grid=document.querySelector(".dashboard-shortcut-grid");return grid?getComputedStyle(grid).gridTemplateColumns.split(" ").length:0})(),title:document.querySelector("#pageTitle")?.textContent?.trim()||"",contentChars:(content?.innerText||"").trim().length,rootVisible:!!shell&&getComputedStyle(shell).display!=="none",viewport:innerWidth,documentWidth:root.scrollWidth,bodyWidth:body.scrollWidth,contentWidth:content?.clientWidth||0,contentScrollWidth:content?.scrollWidth||0,offenders}; })()`);
      mobileResults.push(mobileResult);
      await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
      if (entry.id === "dashboard") {
        await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
        const previousTheme = await evaluate(`document.documentElement.dataset.theme || ""`);
        await evaluate(`applyTheme("midnight", false)`);
        const shellState = await evaluate(`(() => { const header=document.querySelector(".app-shell > .topbar"); const headerStyle=header?getComputedStyle(header):null; const rootStyle=getComputedStyle(document.documentElement); const bodyStyle=getComputedStyle(document.body); return { page: page || "", title: document.querySelector("#pageTitle")?.textContent?.trim() || "", theme: document.documentElement.dataset.theme || "", width: innerWidth, height: innerHeight, paletteBackground: rootStyle.getPropertyValue("--bg").trim(), bodyBackground: bodyStyle.backgroundColor, headerBackground: headerStyle?.backgroundImage || headerStyle?.backgroundColor || "", headerColor: headerStyle?.color || "", openDialogs: Array.from(document.querySelectorAll("dialog[open]"), dialog => ({ id: dialog.id, title: dialog.querySelector("h1,h2,[id=dialogTitle]")?.textContent?.trim() || "" })), authVisible: Boolean(document.querySelector("#authRoot")?.innerHTML.trim()) }; })()`);
    if (shellState.page !== "dashboard" || shellState.width !== 1280 || shellState.height !== 800 || shellState.authVisible) throw new Error(`Dashboard shell capture was not in the matched viewport: ${JSON.stringify(shellState)}`);
        const shellCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
        const shellPath = path.join(outputDir, "web-dashboard-shell-1280x800-headless.png");
        fs.writeFileSync(shellPath, Buffer.from(shellCapture.data, "base64"));
        dashboardShell = { ...shellState, screenshot: shellPath };
        if (previousTheme) await evaluate(`applyTheme(${JSON.stringify(previousTheme)}, false)`);
        await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
      }
      await delay(25);
    }
    if (originalVisualTheme) await evaluate(`applyTheme(${JSON.stringify(originalVisualTheme)}, false)`);
    activeRoute = "assistant-workflow";
    const assistantWorkflow = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      let queryBody = null;
      apiFetch = async (url, options = {}) => {
        if (url === "/api/desktop/assistant/status") return { configured: true, model: "audit-fixture" };
        if (url === "/api/desktop/assistant/query") { queryBody = JSON.parse(options.body || "{}"); return { success: true, answer: "Assistant audit answer" }; }
        return originalApiFetch(url, options);
      };
      try {
        navigate("dashboard");
        await new Promise(resolve => setTimeout(resolve, 30));
        document.querySelector("#assistantHeaderBtn")?.click();
        const panelOpen = document.querySelector("#desktopAssistantPanel")?.hidden === false;
        const pageEntryVisible = Boolean(document.querySelector("[data-assistant-page-open]"));
        document.querySelector("[data-assistant-page-open]")?.click();
        for (let attempt = 0; attempt < 40 && !document.querySelector("#assistantStatus")?.textContent.includes("audit-fixture"); attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
        const faqButton = document.querySelector('[data-assistant-faq="stok"]');
        faqButton?.click();
        const faqAnswer = document.querySelector("#assistantAnswer")?.textContent || "";
        const input = document.querySelector("#assistantQuestion");
        input.value = "Audit free-form question";
        document.querySelector("#assistantQueryForm").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await new Promise(resolve => setTimeout(resolve, 35));
        return { page, bodyPage: document.body.dataset.page, panelOpen, pageEntryVisible, faqAnswer, answer: document.querySelector("#assistantAnswer")?.textContent || "", status: document.querySelector("#assistantStatus")?.textContent || "", queryBody };
      } finally { apiFetch = originalApiFetch; }
    })()`);
    if (!assistantWorkflow.panelOpen || !assistantWorkflow.pageEntryVisible || assistantWorkflow.page !== "assistant" || assistantWorkflow.bodyPage !== "assistant" || !assistantWorkflow.faqAnswer.includes("Stok Ekleme") || !assistantWorkflow.answer.includes("Assistant audit answer") || assistantWorkflow.queryBody?.question !== "Audit free-form question" || !assistantWorkflow.status.includes("audit-fixture")) throw new Error(`AI assistant page workflow did not complete: ${JSON.stringify(assistantWorkflow)}`);
    activeRoute = "support-workflow";
    const supportWorkflow = await evaluate(`(() => {
      navigate("support");
      const contact = document.querySelector('[data-support-panel="contact"]');
      const manualButton = document.querySelector('[data-support-tab="manual"]');
      const contactButton = document.querySelector('[data-support-tab="contact"]');
      const actionCards = [...document.querySelectorAll(".support-action-card")];
      const linkFor = prefix => actionCards.find(item => item.getAttribute("href")?.startsWith(prefix))?.getAttribute("href") || "";
      const contactLinks = { phone: document.querySelector(".support-phone")?.getAttribute("href") || "", whatsapp: linkFor("https://wa.me/"), email: linkFor("mailto:"), anydesk: linkFor("https://anydesk.com"), teamviewer: linkFor("https://www.teamviewer.com"), website: linkFor("https://www.ayecpro.com") };
      const initialContactVisible = Boolean(contact && !contact.hidden);
      manualButton?.click();
      const manual = document.querySelector('[data-support-panel="manual"]');
      const manualText = manual?.innerText || "";
      const manualState = { visible: Boolean(manual && !manual.hidden), headings: manual?.querySelectorAll("h1,h2,h3").length || 0, hasJarvisGuide: manualText.includes("JARVIS NEURAL CORE"), hasTroubleshooting: manualText.includes("6.4.") };
      contactButton?.click();
      return { page, bodyPage: document.body.dataset.page, tabCount: document.querySelectorAll("[data-support-tab]").length, initialContactVisible, contactVisibleAfterReturn: Boolean(contact && !contact.hidden), manualState, contactLinks };
    })()`);
    if (supportWorkflow.page !== "support" || supportWorkflow.bodyPage !== "support" || supportWorkflow.tabCount !== 2 || !supportWorkflow.initialContactVisible || !supportWorkflow.contactVisibleAfterReturn || !supportWorkflow.manualState?.visible || supportWorkflow.manualState.headings < 5 || !supportWorkflow.manualState.hasJarvisGuide || !supportWorkflow.manualState.hasTroubleshooting || Object.values(supportWorkflow.contactLinks || {}).some(value => !value)) throw new Error(`Support page desktop parity workflow did not complete: ${JSON.stringify(supportWorkflow)}`);
    activeRoute = "automotive-stock-workflow";
    const automotiveStockWorkflow = await evaluate(`(async () => {
      currentSector = "otomotiv";
      desktopInternalSettings.feature_usage_guides_active = "1";
      db.stock = [{ id: 7001, code: "OEM-7001", barcode: "8607001", name: "Audit Brake Pad", brand: "Audit", category: "Mekanik", oem_code: "OEM-7001", equivalent_code: "ALT-7001", compatible_models: "Model A", shelf_number: "A-01", qty: 2, buy: 100, sell: 150, currency: "TRY", min: 5 }];
      navigate("automotive-stock");
      await new Promise(resolve => setTimeout(resolve, 80));
      let row = document.querySelector("#stockTable tr[data-id='7001']");
      const encodedDescription = "Brake pad description\\n[OTO_SUPPLIER] Audit Supply\\n[OTO_VEHICLE_BRAND] Ford\\n[OTO_VEHICLE_MODEL] Courier\\n[OTO_POSITION] On Sol";
      const productMarkup = productForm({ name: "Audit Brake Pad", description: encodedDescription, oem_code: "OEM-7001", equivalent_code: "ALT-7001", compatible_models: "Courier 2024", shelf_number: "A-01" });
      const productFormProbe = document.createElement("form");
      productFormProbe.innerHTML = productMarkup;
      const metadataFormParity = productFormProbe.querySelector('[name="description"]')?.value === "Brake pad description" && productFormProbe.querySelector('[name="supplier"]')?.value === "Audit Supply" && productFormProbe.querySelector('[name="vehicle_brand"]')?.value === "Ford" && productFormProbe.querySelector('[name="vehicle_model"]')?.value === "Courier" && productFormProbe.querySelector('[name="position"]')?.value === "On Sol";
      let savedProductPayload = null;
      const productFormData = new FormData(productFormProbe);
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint !== "/api/desktop/stock/save") throw new Error("Unexpected automotive stock endpoint: " + endpoint);
        savedProductPayload = JSON.parse(options.body || "{}");
        return { part: { id: 7002, name: savedProductPayload.name, code: savedProductPayload.code, description: savedProductPayload.description, stock: savedProductPayload.stock, min_stock: savedProductPayload.min_stock, price: savedProductPayload.price, purchase_price: savedProductPayload.purchase_price } };
      };
      productFormData.set("name", "Audit Brake Pad");
      productFormData.set("code", "OEM-7002");
      productFormData.set("qty", "2");
      productFormData.set("min", "5");
      productFormData.set("buy", "100");
      productFormData.set("sell", "150");
      const savedProduct = await saveProduct(productFormData, null);
      const productTableRow = document.querySelector("#stockTable tr[data-id='7002']");
      const metadataSaveParity = savedProduct && savedProductPayload?.description === encodedDescription && db.stock.find(item => String(item.id) === "7002")?.supplier === "Audit Supply" && productTableRow?.textContent.includes("Ford") && productTableRow?.textContent.includes("On Sol");
      row = document.querySelector("#stockTable tr[data-id='7001']");
      const stockSearch = document.querySelector("#stockSearch");
      const metadataSearchResults = [];
      for (const query of ["Audit Supply", "Courier", "On Sol"]) {
        stockSearch.value = query;
        stockSearch.dispatchEvent(new Event("input", { bubbles: true }));
        metadataSearchResults.push([...document.querySelectorAll("#stockTable tr[data-kind='stock']")].map(item => item.dataset.id));
      }
      const metadataSearchParity = metadataSearchResults.every(ids => ids.length === 1 && ids[0] === "7002");
      stockSearch.value = "";
      stockSearch.dispatchEvent(new Event("input", { bubbles: true }));
      row = document.querySelector("#stockTable tr[data-id='7001']");
      const priceButton = row?.querySelector("[data-automotive-price-toggle]");
      const expectedPrice = priceButton?.dataset.purchasePrice || "";
      const maskedInitially = priceButton?.textContent === "***";
      priceButton?.click();
      const individualReveal = priceButton?.textContent === expectedPrice;
      priceButton?.click();
      const individuallyMasked = priceButton?.textContent === "***";
      const bulkButton = document.querySelector("[data-automotive-price-all]");
      bulkButton?.click();
      const bulkReveal = priceButton?.textContent === expectedPrice;
      bulkButton?.click();
      const bulkHide = priceButton?.textContent === "***";
      const guideButton = document.querySelector("[data-automotive-stock-guide]");
      guideButton?.click();
      const guide = document.querySelector(".automotive-stock-guide");
      const guideVisible = Boolean(guide && !guide.hidden && document.querySelector(".stock-category-strip")?.hidden && [...document.querySelectorAll("#content .card")].every(card => card.hidden));
      guideButton?.click();
      const guideRestored = Boolean(guide?.hidden === true && document.querySelector(".stock-category-strip")?.hidden === false);
      desktopInternalSettings.feature_usage_guides_active = "0";
      db.settings.contextMenu = true;
      render();
      const writes = [];
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint === "/api/desktop/stock/adjust") {
          const body = JSON.parse(options.body || "{}");
          writes.push({ endpoint, method: options.method || "GET", body });
          return { movement_id: "audit-movement", delta: body.delta, finance_id: null };
        }
        return window.__routeSmokeEmpty;
      };
      const openMovementDialog = () => {
        const currentRow = document.querySelector("#stockTable tr[data-id='7001']");
        currentRow?.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 100, clientY: 100 }));
        document.querySelector('[data-context-action="movement"]')?.click();
        return document.querySelector("#dialogForm");
      };
      const movementForm = openMovementDialog();
      if (movementForm) {
        movementForm.querySelector('[name="type"]').selectedIndex = 0;
        movementForm.querySelector('[name="qty"]').value = "3";
        movementForm.querySelector('[name="ref"]').value = "PO-42";
        movementForm.requestSubmit();
        await new Promise(resolve => setTimeout(resolve, 80));
      }
      const successfulAdjustment = writes.length === 1 && writes[0].body.id === 7001 && writes[0].body.delta === 3 && writes[0].body.reference === "PO-42" && Number(db.stock.find(item => item.id === 7001)?.qty) === 5;
      const insufficientStockForm = openMovementDialog();
      if (insufficientStockForm) {
        insufficientStockForm.querySelector('[name="type"]').selectedIndex = 1;
        insufficientStockForm.querySelector('[name="qty"]').value = "6";
        insufficientStockForm.querySelector('[name="ref"]').value = "OVERDRAW";
        insufficientStockForm.requestSubmit();
        await new Promise(resolve => setTimeout(resolve, 60));
      }
      const overdrawRejected = writes.length === 1 && document.querySelector("#appDialog")?.open === true;
      document.querySelector("#appDialog")?.close("cancel");
      return { page: page || "", rowVisible: Boolean(row), metadataFormParity, metadataSaveParity, metadataSearchParity, metadataSearchResults, savedDescription: savedProductPayload?.description || "", productTableRow: productTableRow?.textContent || "", priceInitiallyMasked: maskedInitially, individualReveal, individuallyMasked, bulkReveal, bulkHide, guideVisible, guideRestored, guideHiddenByFeatureFlag: !document.querySelector("[data-automotive-stock-guide]"), successfulAdjustment, overdrawRejected, writes, exceptions: window.__routeSmokeExceptions || [] };
    })()`);
    if (automotiveStockWorkflow.page !== "automotive-stock" || !automotiveStockWorkflow.rowVisible || !automotiveStockWorkflow.metadataFormParity || !automotiveStockWorkflow.metadataSaveParity || !automotiveStockWorkflow.metadataSearchParity || !automotiveStockWorkflow.priceInitiallyMasked || !automotiveStockWorkflow.individualReveal || !automotiveStockWorkflow.individuallyMasked || !automotiveStockWorkflow.bulkReveal || !automotiveStockWorkflow.bulkHide || !automotiveStockWorkflow.guideVisible || !automotiveStockWorkflow.guideRestored || !automotiveStockWorkflow.guideHiddenByFeatureFlag || !automotiveStockWorkflow.successfulAdjustment || !automotiveStockWorkflow.overdrawRejected || exceptions.length) throw new Error(`Automotive stock guide, metadata, or purchase-price controls failed: ${JSON.stringify({ automotiveStockWorkflow, exceptions })}`);
    activeRoute = "vehicle-maintenance-workflow";
    const vehicleMaintenanceWorkflow = await evaluate(`(async () => {
      currentSector = "otomotiv";
      const card = { id: 81, customer_name: "Audit Driver", vehicle_plate: "34 QA 081", vehicle_brand: "Audit", vehicle_model: "Roadster", linked_device_tracking_no: "SRV-81", appointment_date: "2026-10-20", appointment_time: "10:30", next_maintenance_date: "2026-11-01" };
      const history = { token: "34-QA-081", plate: card.vehicle_plate, maintenance_rows: [{ maintenance_date: "2026-09-01", next_maintenance_date: "2026-11-01", inspection_date: "2026-12-01", notes: "Audit maintenance", service_tracking_no: "SRV-81" }], service_rows: [{ tracking_no: "SRV-81", entry_date: "2026-09-01", status: "Onarimda", approval_status: "Onaylandi", fault_description: "Audit fault", labor_total: 250 }] };
      apiFetch = async endpoint => {
        if (endpoint.startsWith("/api/desktop/vehicle-maintenance/cards")) return { rows: [card] };
        if (endpoint === "/api/desktop/vehicle-maintenance/detail/81") return { card, items: [{ service_name: "Oil service", next_due_date: "2026-11-01", next_due_odometer: 42000 }] };
        if (endpoint === "/api/desktop/vehicle-maintenance/history/81") return history;
        return window.__routeSmokeEmpty;
      };
      navigate("vehicle-maintenance");
      await new Promise(resolve => setTimeout(resolve, 120));
      const row = document.querySelector('[data-maintenance-row="0"]');
      const selectedSummary = document.querySelector("[data-maintenance-summary]")?.textContent || "";
      const selectedHistory = document.querySelector("[data-maintenance-history]")?.textContent || "";
      const serviceEnabled = document.querySelector("[data-maintenance-open-service]")?.disabled === false;
      document.querySelector('[data-maintenance-history][data-maintenance-history="0"]')?.click();
      await new Promise(resolve => setTimeout(resolve, 60));
      const historyDialog = document.querySelector("#appDialog");
      const shareCode = document.querySelector("#vehicleHistoryShareUri")?.value || "";
      const historyTables = historyDialog?.querySelectorAll(".vehicle-history-title").length || 0;
      const historyDialogText = historyDialog?.innerText || "";
      const historyDialogOpen = Boolean(historyDialog?.open);
      historyDialog?.close("cancel");
      return { page: page || "", rowVisible: Boolean(row), selectedSummary, selectedHistory, serviceEnabled, historyDialogOpen, shareCode, historyTables, historyDialogText };
    })()`);
    if (vehicleMaintenanceWorkflow.page !== "vehicle-maintenance" || !vehicleMaintenanceWorkflow.rowVisible || !vehicleMaintenanceWorkflow.selectedSummary.includes("Audit Driver") || !vehicleMaintenanceWorkflow.selectedSummary.includes("Bakim kalemi: 1") || !vehicleMaintenanceWorkflow.selectedSummary.includes("SRV-81") || !vehicleMaintenanceWorkflow.selectedHistory.includes("Servis gecmisi: 1 kayit") || !vehicleMaintenanceWorkflow.historyDialogText.includes("SRV-81") || !vehicleMaintenanceWorkflow.serviceEnabled || !vehicleMaintenanceWorkflow.historyDialogOpen || vehicleMaintenanceWorkflow.shareCode !== "ayec://vehicle-history/34-QA-081" || vehicleMaintenanceWorkflow.historyTables !== 2 || exceptions.length) throw new Error(`Vehicle-maintenance selection or history workflow failed: ${JSON.stringify({ vehicleMaintenanceWorkflow, exceptions })}`);
    activeRoute = "field-service-route-draft";
    const fieldServiceRouteWorkflow = await evaluate(`(async () => {
      const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
      currentSector = "teknik_servis";
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint === "/api/desktop/field-service/route") {
          window.__fieldRouteRequest = { endpoint, method: options.method, body: JSON.parse(options.body || "{}") };
          return { ok: false, reason: "missing_key" };
        }
        if (endpoint === "/api/desktop/field-service/assign") {
          window.__fieldAssignmentRequest = { endpoint, method: options.method, body: JSON.parse(options.body || "{}") };
          return { ok: true };
        }
        if (endpoint === "/api/desktop/field-service/personnel") return { personnel: [{ id: 781, name: "Audit Technician", job: "Technician", status: "Gorevde", lat: 40.108, lng: 27.662 }], center: { lat: 40.10441, lng: 27.6564 }, can_share_location: false };
        return window.__routeSmokeEmpty;
      };
      window.__auditFieldMap = null;
      navigate("field-service");
      for (let attempt = 0; attempt < 80 && (!document.querySelector("#fieldPersonnelMap") || !window.__auditFieldMap || !document.querySelector(".field-location-tools-toggle") || !document.querySelector("[data-field-customer-location]") || document.querySelectorAll("[data-field-map-action]").length < 6); attempt += 1) await pause(25);
      document.querySelector("[data-field-panel-mode='teams']")?.click();
      const teamsPanel = document.querySelector(".field-personnel-queue")?.hidden === false && document.querySelector("#fieldMapRows")?.hidden === true && document.querySelector(".field-map-search")?.hidden === false;
      document.querySelector("[data-field-panel-mode='jobs']")?.click();
      const jobsPanel = document.querySelector(".field-map-queue > header")?.hidden === false && document.querySelector("#fieldMapRows")?.hidden === false && document.querySelector(".field-map-search")?.hidden === false;
      document.querySelector("[data-field-panel-mode='customer']")?.click();
      const customerPanelModes = { teams: teamsPanel, jobs: jobsPanel, returnedToCustomer: document.querySelector("[data-field-customer-location]")?.hidden === false };
      window.__auditFieldMap?.fireClick(40.105, 27.657);
      const selectedCustomerAddress = document.querySelector("[data-field-customer-address]")?.textContent || "";
      const selectedCustomerPreview = document.querySelector("[data-field-customer-preview]")?.textContent || "";
      Object.defineProperty(navigator, "share", { configurable: true, value: async payload => { window.__fieldSharePayload = payload; } });
      document.querySelector("[data-field-customer-share]")?.click();
      for (let attempt = 0; attempt < 40 && !window.__fieldSharePayload; attempt += 1) await pause(25);
      const sharePayload = window.__fieldSharePayload || null;
      document.querySelector("[data-field-customer-assign]")?.click();
      for (let attempt = 0; attempt < 40 && !document.querySelector("#fieldLocationPersonnel"); attempt += 1) await pause(25);
      const assignmentDialogOpened = Boolean(document.querySelector("#fieldLocationPersonnel"));
      document.querySelector("#dialogSubmit")?.click();
      for (let attempt = 0; attempt < 40 && !window.__fieldAssignmentRequest; attempt += 1) await pause(25);
      const assignmentRequest = window.__fieldAssignmentRequest || null;
      for (let attempt = 0; attempt < 40 && document.querySelector("#appDialog")?.open; attempt += 1) await pause(25);
      document.querySelector('[data-field-map-action="home"]')?.click();
      for (let attempt = 0; attempt < 40 && !(document.querySelector("[data-field-customer-preview]")?.textContent || "").includes("40.104410, 27.656400"); attempt += 1) await pause(25);
      const homePreview = document.querySelector("[data-field-customer-preview]")?.textContent || "";
      const homeAddress = document.querySelector("[data-field-customer-address]")?.textContent || "";
      const homeView = window.__auditFieldMap?.view || null;
      document.querySelector(".field-location-tools-toggle")?.click();
      for (let attempt = 0; attempt < 40 && document.querySelector(".field-location-tools")?.hidden !== false; attempt += 1) await pause(25);
      document.querySelector('[data-field-map-action="draw-route"]')?.click();
      for (let attempt = 0; attempt < 40 && document.querySelector("[data-field-route-finish]")?.hidden !== false; attempt += 1) await pause(25);
      window.__auditFieldMap?.fireClick(40.11, 27.66);
      window.__auditFieldMap?.fireClick(40.12, 27.67);
      const draftLine = window.__auditFieldMap?.layers.find(layer => layer.options?.dashArray === "8 6");
      const draftBeforeFinish = { points: draftLine?.points || [], dashArray: draftLine?.options?.dashArray || "" };
      document.querySelector("[data-field-route-finish]")?.click();
      await pause(40);
      const remainingDraft = window.__auditFieldMap?.layers.find(layer => layer.options?.dashArray === "8 6");
      return {
        page: page || "",
        customerPanel: { visible: document.querySelector("[data-field-customer-location]")?.hidden === false, shareButton: Boolean(document.querySelector("[data-field-customer-share]")), assignButton: Boolean(document.querySelector("[data-field-customer-assign]")), searchHidden: document.querySelector(".field-map-search")?.hidden === true, selectedAddress: selectedCustomerAddress, selectedPreview: selectedCustomerPreview },
        customerPanelModes,
        assignmentWorkflow: { dialogOpened: assignmentDialogOpened, request: assignmentRequest },
        shareWorkflow: { called: Boolean(sharePayload), text: sharePayload?.text || "" },
        homeWorkflow: { preview: homePreview, address: homeAddress, view: homeView },
        mapReady: Boolean(window.__auditFieldMap),
        request: window.__fieldRouteRequest || null,
        draftBeforeFinish,
        draftAfterFailure: { points: remainingDraft?.points || [], dashArray: remainingDraft?.options?.dashArray || "" },
        finishHidden: Boolean(document.querySelector("[data-field-route-finish]")?.hidden),
        shareVisible: document.querySelector("[data-field-route-share]")?.hidden === false,
        footer: document.querySelector(".field-map-canvas>footer span")?.textContent || "",
        toolsToggle: document.querySelector(".field-location-tools-toggle")?.textContent || "",
        toolsHidden: document.querySelector(".field-location-tools")?.hidden ?? null,
        actions: [...document.querySelectorAll("[data-field-map-action]")].map(button => button.dataset.fieldMapAction),
        mapHeader: document.querySelector(".field-map-canvas header")?.innerText || "",
        mapFooter: document.querySelector(".field-map-canvas>footer")?.innerText || ""
      };
    })()`);
    if (fieldServiceRouteWorkflow.page !== "field-service" || !fieldServiceRouteWorkflow.customerPanel.visible || !fieldServiceRouteWorkflow.customerPanel.shareButton || !fieldServiceRouteWorkflow.customerPanel.assignButton || !fieldServiceRouteWorkflow.customerPanel.searchHidden || fieldServiceRouteWorkflow.customerPanel.selectedAddress !== "Secilen Konum" || !fieldServiceRouteWorkflow.customerPanel.selectedPreview.includes("40.105000, 27.657000") || !fieldServiceRouteWorkflow.customerPanel.selectedPreview.includes("https://www.google.com/maps?q=40.105000,27.657000") || !fieldServiceRouteWorkflow.customerPanelModes.teams || !fieldServiceRouteWorkflow.customerPanelModes.jobs || !fieldServiceRouteWorkflow.customerPanelModes.returnedToCustomer || !fieldServiceRouteWorkflow.assignmentWorkflow.dialogOpened || !fieldServiceRouteWorkflow.shareWorkflow.called || !fieldServiceRouteWorkflow.shareWorkflow.text.includes("https://www.google.com/maps?q=40.105000,27.657000") || !fieldServiceRouteWorkflow.homeWorkflow.preview.includes("40.104410, 27.656400") || fieldServiceRouteWorkflow.homeWorkflow.address !== "Haritadan seçilen nokta" || fieldServiceRouteWorkflow.homeWorkflow.view?.center?.[0] !== 40.10441 || fieldServiceRouteWorkflow.homeWorkflow.view?.center?.[1] !== 27.6564 || fieldServiceRouteWorkflow.homeWorkflow.view?.zoom !== 13 || fieldServiceRouteWorkflow.assignmentWorkflow.request?.method !== "POST" || fieldServiceRouteWorkflow.assignmentWorkflow.request?.body?.id !== 781 || fieldServiceRouteWorkflow.assignmentWorkflow.request?.body?.lat !== 40.105 || fieldServiceRouteWorkflow.assignmentWorkflow.request?.body?.lng !== 27.657 || !fieldServiceRouteWorkflow.mapReady || fieldServiceRouteWorkflow.request?.method !== "POST" || fieldServiceRouteWorkflow.request?.body?.points?.length !== 2 || fieldServiceRouteWorkflow.draftBeforeFinish.points.length !== 2 || fieldServiceRouteWorkflow.draftAfterFailure.points.length !== 2 || fieldServiceRouteWorkflow.draftAfterFailure.dashArray !== "8 6" || !fieldServiceRouteWorkflow.finishHidden || !fieldServiceRouteWorkflow.shareVisible || !fieldServiceRouteWorkflow.footer.includes("API anahtar") || exceptions.length) throw new Error(`Field-service route draft was not preserved after missing TomTom credentials: ${JSON.stringify({ fieldServiceRouteWorkflow, exceptions })}`);
    const fieldServiceRouteSuccessWorkflow = await evaluate(`(async () => {
      const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
      const geometry = [[40.11, 27.66], [40.115, 27.665], [40.12, 27.67]];
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint === "/api/desktop/field-service/route") {
          window.__fieldRouteSuccessRequest = { endpoint, method: options.method, body: JSON.parse(options.body || "{}") };
          return { ok: true, geometry, distance_meters: 4200, duration_seconds: 600 };
        }
        return window.__routeSmokeEmpty;
      };
      document.querySelector('[data-field-map-action="draw-route"]')?.click();
      for (let attempt = 0; attempt < 40 && document.querySelector("[data-field-route-finish]")?.hidden !== false; attempt += 1) await pause(25);
      window.__auditFieldMap?.fireClick(40.11, 27.66);
      window.__auditFieldMap?.fireClick(40.12, 27.67);
      document.querySelector("[data-field-route-finish]")?.click();
      await pause(60);
      const routedLine = window.__auditFieldMap?.layers.find(layer => layer.options?.color === "#4edea3" && layer.options?.dashArray === null);
      return {
        request: window.__fieldRouteSuccessRequest || null,
        routeGeometry: routedLine?.points || [],
        routeStyle: routedLine?.options || {},
        finishHidden: Boolean(document.querySelector("[data-field-route-finish]")?.hidden),
        shareVisible: document.querySelector("[data-field-route-share]")?.hidden === false,
        footer: document.querySelector(".field-map-canvas>footer span")?.textContent || ""
      };
    })()`);
    if (fieldServiceRouteSuccessWorkflow.request?.method !== "POST" || fieldServiceRouteSuccessWorkflow.request?.body?.points?.length !== 2 || JSON.stringify(fieldServiceRouteSuccessWorkflow.routeGeometry) !== JSON.stringify([[40.11, 27.66], [40.115, 27.665], [40.12, 27.67]]) || fieldServiceRouteSuccessWorkflow.routeStyle.dashArray !== null || !fieldServiceRouteSuccessWorkflow.finishHidden || !fieldServiceRouteSuccessWorkflow.shareVisible || !fieldServiceRouteSuccessWorkflow.footer.includes("4.2 km") || exceptions.length) throw new Error(`Field-service successful routing workflow failed: ${JSON.stringify({ fieldServiceRouteSuccessWorkflow, exceptions })}`);
    const fieldPersonnelDutyWorkflow = await evaluate(`(async () => {
      const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
      const people = [
        { id: 21, name: "Audit Field One", role: "Saha Personeli", status: "Gorevde", lat: 40.10441, lng: 27.6564 },
        { id: 22, name: "Audit Field Two", role: "Teknisyen", status: "Gorevde", lat: 40.11441, lng: 27.6664 },
        { id: 23, name: "Audit Field Three", role: "Saha Destek", status: "Boshta", lat: null, lng: null }
      ];
      window.__fieldPersonnelCalls = [];
      let failFinish = true;
      apiFetch = async (endpoint, options = {}) => {
        window.__fieldPersonnelCalls.push({ endpoint, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null });
        if (endpoint === "/api/desktop/field-service/personnel") return { personnel: people, center: { lat: 40.10441, lng: 27.6564 }, can_share_location: true };
        if (endpoint === "/api/desktop/field-service/finish") {
          if (failFinish) throw new Error("Permission denied");
          return { ok: true };
        }
        return window.__routeSmokeEmpty;
      };
      window.__auditFieldMap = null;
      navigate("field-service");
      for (let attempt = 0; attempt < 100 && document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']").length !== 3; attempt += 1) await pause(25);
      const initialCount = document.querySelector("#fieldPersonnelCount")?.textContent || "";
      const initialPersonnelMetric = document.querySelector("#fieldMapPersonnel")?.textContent || "";
      const initialGpsNote = document.querySelector("#fieldMapGpsNote")?.textContent || "";
      document.querySelectorAll("#toastRoot .toast.error").forEach(node => node.remove());
      document.querySelector('[data-field-personnel-finish="22"]')?.click();
      for (let attempt = 0; attempt < 40 && !document.querySelector("#appDialog")?.open; attempt += 1) await pause(25);
      const confirmTitle = document.querySelector("#dialogTitle")?.textContent || "";
      const confirmBody = document.querySelector("#dialogBody")?.textContent || "";
      const cancel = document.querySelector("#dialogCancel");
      const cancelLabel = cancel?.textContent || "";
      cancel?.click();
      await pause(30);
      const postsAfterCancel = window.__fieldPersonnelCalls.filter(call => call.endpoint === "/api/desktop/field-service/finish").length;
      document.querySelector('[data-field-personnel-finish="22"]')?.click();
      for (let attempt = 0; attempt < 40 && !document.querySelector("#appDialog")?.open; attempt += 1) await pause(25);
      document.querySelector("#dialogSubmit")?.click();
      for (let attempt = 0; attempt < 80 && window.__fieldPersonnelCalls.filter(call => call.endpoint === "/api/desktop/field-service/finish").length < 1; attempt += 1) await pause(25);
      for (let attempt = 0; attempt < 80 && !document.querySelector("#toastRoot .toast.error")?.textContent.includes("Permission denied"); attempt += 1) await pause(25);
      const dialogOpenAfterFailure = document.querySelector("#appDialog")?.open === true;
      const failureToast = document.querySelector("#toastRoot .toast.error")?.textContent || "";
      document.querySelector("#toastRoot .toast.error")?.remove();
      failFinish = false;
      for (let attempt = 0; attempt < 40 && document.querySelector("#dialogSubmit")?.disabled; attempt += 1) await pause(25);
      document.querySelector("#dialogSubmit")?.click();
      for (let attempt = 0; attempt < 80 && window.__fieldPersonnelCalls.filter(call => call.endpoint === "/api/desktop/field-service/finish").length < 2; attempt += 1) await pause(25);
      await pause(30);
      const updatedCard = [...document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']")].find(card => card.dataset.id === "22");
      return {
        page: page || "",
        peopleRendered: document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']").length,
        initialCount,
        initialPersonnelMetric,
        initialGpsNote,
        confirmTitle,
        confirmBody,
        cancelLabel,
        postsAfterCancel,
        dialogOpenAfterFailure,
        failureToast,
        finishCalls: window.__fieldPersonnelCalls.filter(call => call.endpoint === "/api/desktop/field-service/finish"),
        updatedStatus: updatedCard?.querySelector(".badge")?.textContent || "",
        exceptions: window.__routeSmokeExceptions || []
      };
    })()`);
    if (fieldPersonnelDutyWorkflow.page !== "field-service" || fieldPersonnelDutyWorkflow.peopleRendered !== 3 || fieldPersonnelDutyWorkflow.initialCount !== "3" || fieldPersonnelDutyWorkflow.initialPersonnelMetric !== "3 Personel" || fieldPersonnelDutyWorkflow.initialGpsNote !== "2 GPS kaydi / 3 personel" || !fieldPersonnelDutyWorkflow.confirmTitle.includes("G\u00f6revi Tamamla") || !fieldPersonnelDutyWorkflow.confirmBody.includes("Audit Field Two") || fieldPersonnelDutyWorkflow.cancelLabel !== "Hay\u0131r" || fieldPersonnelDutyWorkflow.postsAfterCancel !== 0 || !fieldPersonnelDutyWorkflow.dialogOpenAfterFailure || !fieldPersonnelDutyWorkflow.failureToast.includes("Permission denied") || fieldPersonnelDutyWorkflow.finishCalls.length !== 2 || fieldPersonnelDutyWorkflow.finishCalls.some(call => call.method !== "POST" || call.body?.id !== 22) || fieldPersonnelDutyWorkflow.updatedStatus !== "Bo\u015fta" || exceptions.length) throw new Error(`Field-service duty confirmation workflow failed: ${JSON.stringify({ fieldPersonnelDutyWorkflow, exceptions })}`);
    const fieldServiceTomTomKeyWorkflow = await evaluate(`(async () => {
      const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
      window.__tomtomKeyCalls = [];
      apiFetch = async (endpoint, options = {}) => {
        window.__tomtomKeyCalls.push({ endpoint, method: options.method || "GET", body: options.body ? JSON.parse(options.body) : null });
        return { status: options.method === "POST" ? "configured" : "missing" };
      };
      const keyAction = document.querySelector('[data-field-map-action="tomtom-key"]');
      keyAction?.click();
      for (let attempt = 0; attempt < 40 && !document.querySelector("#appDialog")?.open; attempt += 1) await pause(25);
      const input = document.querySelector('#dialogForm input[name="api_key"]');
      const secureDialog = Boolean(document.querySelector("#appDialog")?.open && input?.type === "password" && input?.autocomplete === "new-password");
      if (input) input.value = "browser-fixture-key";
      document.querySelector("#dialogForm")?.requestSubmit();
      for (let attempt = 0; attempt < 40 && window.__tomtomKeyCalls.length < 2; attempt += 1) await pause(25);
      await pause(30);
      return {
        adminActionVisible: Boolean(keyAction),
        secureDialog,
        calls: window.__tomtomKeyCalls,
        closedAfterSave: document.querySelector("#appDialog")?.open === false,
        responseContainsSecret: document.body.innerText.includes("browser-fixture-key")
      };
    })()`);
    if (!fieldServiceTomTomKeyWorkflow.adminActionVisible || !fieldServiceTomTomKeyWorkflow.secureDialog || fieldServiceTomTomKeyWorkflow.calls.length !== 2 || fieldServiceTomTomKeyWorkflow.calls[0].endpoint !== "/api/desktop/field-service/tomtom-key" || fieldServiceTomTomKeyWorkflow.calls[0].method !== "GET" || fieldServiceTomTomKeyWorkflow.calls[1].method !== "POST" || fieldServiceTomTomKeyWorkflow.calls[1].body?.api_key !== "browser-fixture-key" || !fieldServiceTomTomKeyWorkflow.closedAfterSave || fieldServiceTomTomKeyWorkflow.responseContainsSecret || exceptions.length) throw new Error(`Field-service TomTom key workflow failed: ${JSON.stringify({ fieldServiceTomTomKeyWorkflow, exceptions })}`);
    const leafletAssetAudit = await evaluate(`(async () => {
      const oldLeaflet=window.L,css=document.createElement("link");css.id="fieldLeafletCss";css.rel="stylesheet";css.href="/vendor/leaflet/leaflet.css?v=1.9.4";document.head.append(css);
      const script=document.createElement("script");script.src="/vendor/leaflet/leaflet.js?v=1.9.4";document.head.append(script);
      const loaded=await new Promise(resolve=>{script.onload=()=>resolve(true);script.onerror=()=>resolve(false)});
      const result={loaded,version:window.L?.version||"",mapAvailable:typeof window.L?.map==="function",cssLoaded:Boolean(css.sheet)};
      window.__realLeafletForAudit=window.L;script.remove();window.L=oldLeaflet;
      return result;
    })()`);
    if (!leafletAssetAudit.loaded || leafletAssetAudit.version !== "1.9.4" || !leafletAssetAudit.mapAvailable || !leafletAssetAudit.cssLoaded || exceptions.length) throw new Error(`Bundled Leaflet assets did not load from the web app: ${JSON.stringify({ leafletAssetAudit, exceptions })}`);
    const fieldMapBrowserAudit = await evaluate(`(async () => {
      const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms)),mockLeaflet=window.L;window.L=window.__realLeafletForAudit;
      const appointments=window.__routeSmokeFieldAppointments||[];apiFetch=async endpoint=>{const path=String(endpoint);if(path==="/api/desktop/field-service/personnel")return{personnel:[{id:301,name:"Audit Field One",job:"Technician",status:"Gorevde",lat:40.108,lng:27.662},{id:302,name:"Audit Field Two",job:"Technician",status:"Mola",lat:40.112,lng:27.671},{id:303,name:"Audit Field No GPS",job:"Technician",status:"Mola",lat:null,lng:null}],center:{lat:40.10441,lng:27.6564},can_share_location:false};if(path.startsWith("/api/desktop/table/appointments"))return{table:"appointments",columns:Object.keys(appointments[0]||{}),rows:appointments,count:appointments.length};return window.__routeSmokeEmpty};
      navigate("dashboard");await pause(40);navigate("field-service");
      for(let attempt=0;attempt<120&&(!document.querySelector("#fieldPersonnelMap.leaflet-container")||document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']").length!==3||document.querySelectorAll("#fieldPersonnelMap .field-personnel-marker").length!==2);attempt++)await pause(50);
      await pause(3500);
      const root=document.querySelector("#fieldPersonnelMap"),homeButton=root?.querySelector(".field-map-home-control"),tiles=[...(root?.querySelectorAll(".leaflet-tile")||[])],bounds=root?.getBoundingClientRect(),tileBounds=tiles[0]?.getBoundingClientRect(),layout=document.querySelector(".field-map-layout"),mapCanvas=document.querySelector(".field-map-canvas"),actionHost=document.querySelector(".field-map-actions"),metricsCard=document.querySelector(".field-map-metrics article"),content=document.querySelector("#content"),loadedTileBounds=tiles.filter(tile=>tile.complete&&tile.naturalWidth>0).map(tile=>tile.getBoundingClientRect());let covered=0,total=0;if(bounds?.width&&bounds?.height){for(let y=bounds.top+10;y<bounds.bottom;y+=20)for(let x=bounds.left+10;x<bounds.right;x+=20){total++;if(loadedTileBounds.some(tile=>x>=tile.left&&x<tile.right&&y>=tile.top&&y<tile.bottom))covered++;}}homeButton?.click();homeButton?.blur();const result={homeButtonPresent:Boolean(homeButton),homeButtonLabel:homeButton?.getAttribute("aria-label")||"",version:window.L?.version||"",mapReady:Boolean(root?.classList.contains("leaflet-container")),topbarHeight:Math.round(document.querySelector(".app-shell>.topbar")?.getBoundingClientRect().height||0),pageActionRects:[...document.querySelectorAll(".page-head>div:last-child button")].map(button=>{const r=button.getBoundingClientRect();return{x:Math.round(r.x),y:Math.round(r.y),right:Math.round(r.right),bottom:Math.round(r.bottom)}}),controls:root?.querySelectorAll(".leaflet-control").length||0,tiles:tiles.length,loadedTiles:tiles.filter(tile=>tile.complete&&tile.naturalWidth>0).length,failedTiles:tiles.filter(tile=>tile.complete&&!tile.naturalWidth).length,tileCoverage:total?covered/total:0,tileBoxes:loadedTileBounds.map(tile=>({x:Math.round(tile.left),y:Math.round(tile.top),width:Math.round(tile.width),height:Math.round(tile.height)})),tileSample:tiles[0]?.src||"",tileStyle:tiles[0]?getComputedStyle(tiles[0]).position:"",tileFilter:tiles[0]?getComputedStyle(tiles[0]).filter:"",darkFilterPresent:Boolean(document.querySelector("#ayecFieldMapDarkFilter")),rootBounds:bounds?{x:bounds.x,y:bounds.y,width:bounds.width,height:bounds.height}:null,tileBounds:tileBounds?{x:tileBounds.x,y:tileBounds.y,width:tileBounds.width,height:tileBounds.height}:null,layoutColumns:layout?getComputedStyle(layout).gridTemplateColumns.split(" ").length:0,mapWidth:mapCanvas?Math.round(mapCanvas.getBoundingClientRect().width):0,mapHeaderHeight:Math.round(mapCanvas?.querySelector("header")?.getBoundingClientRect().height||0),actionScrollWidth:actionHost?.scrollWidth||0,actionClientWidth:actionHost?.clientWidth||0,metricsCardHeight:Math.round(metricsCard?.getBoundingClientRect().height||0),metricLabels:[...document.querySelectorAll(".field-map-metrics small")].map(node=>node.textContent.trim()),metricValues:[...document.querySelectorAll(".field-map-metrics strong")].map(node=>node.textContent.trim()),contentWidth:content?.clientWidth||0,mapHint:document.querySelector(".field-map-canvas header small")?.textContent||"",attribution:root?.querySelector(".leaflet-control-attribution")?.textContent||"",personnelCount:document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']").length,markerCount:root?.querySelectorAll(".field-personnel-marker").length||0};
      window.L=mockLeaflet;return result;
    })()`);
    if (!fieldMapBrowserAudit.mapReady || fieldMapBrowserAudit.version !== "1.9.4" || fieldMapBrowserAudit.controls < 1 || !fieldMapBrowserAudit.darkFilterPresent || !fieldMapBrowserAudit.tileFilter.includes("ayecFieldMapDarkFilter") || !fieldMapBrowserAudit.homeButtonPresent || fieldMapBrowserAudit.homeButtonLabel !== "Haritayi merkeze al" || fieldMapBrowserAudit.personnelCount !== 3 || fieldMapBrowserAudit.markerCount !== 2 || fieldMapBrowserAudit.layoutColumns !== 1 || fieldMapBrowserAudit.mapWidth < fieldMapBrowserAudit.contentWidth * 0.9 || fieldMapBrowserAudit.mapHeaderHeight > 82 || fieldMapBrowserAudit.actionScrollWidth > fieldMapBrowserAudit.actionClientWidth + 1 || fieldMapBrowserAudit.metricsCardHeight > 82 || JSON.stringify(fieldMapBrowserAudit.metricLabels) !== JSON.stringify(["SAHADAK\u0130 EK\u0130PLER","BUG\u00dcNK\u00dc SAHA G\u00d6REVLER\u0130","ORTALAMA VARI\u015e S\u00dcRES\u0130","AC\u0130L SAHA \u00c7A\u011eRISI"]) || JSON.stringify(fieldMapBrowserAudit.metricValues) !== JSON.stringify(["3 Personel","-","-","-"]) || fieldMapBrowserAudit.tileCoverage < 0.98 || fieldMapBrowserAudit.topbarHeight !== 36 || Math.abs(fieldMapBrowserAudit.rootBounds?.y-180) > 1 || fieldMapBrowserAudit.pageActionRects.length !== 3 || !fieldMapBrowserAudit.pageActionRects.every(box=>box.x>=450&&box.right<=800&&box.y>=0&&box.bottom<=36) || exceptions.length) throw new Error(`Live field-map initialization failed with bundled Leaflet: ${JSON.stringify({ fieldMapBrowserAudit, exceptions })}`);
    const fieldMapCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const fieldMapImage = Buffer.from(fieldMapCapture.data, "base64");
    fs.writeFileSync(path.join(outputDir, "field-service-live-map-1300x850.png"), fieldMapImage);
    fs.writeFileSync(path.join(outputDir, "route-captures", "field-service-1300x850.png"), fieldMapImage);
    await evaluate(`document.querySelector("[data-field-panel-mode='jobs']")?.click()`);
    const fieldServiceJobsLiveCapture = await evaluate(`(() => ({count:document.querySelector("#fieldMapCount")?.textContent||"",rows:document.querySelectorAll(".field-map-job").length,visible:document.querySelector("#fieldMapRows")?.hidden===false,personnel:document.querySelectorAll("#fieldPersonnelRows [data-kind='field-personnel']").length,markers:document.querySelectorAll("#fieldPersonnelMap .field-personnel-marker").length}))()`);
    if (fieldServiceJobsLiveCapture.count !== "8" || fieldServiceJobsLiveCapture.rows !== 8 || !fieldServiceJobsLiveCapture.visible || fieldServiceJobsLiveCapture.personnel !== 3 || fieldServiceJobsLiveCapture.markers !== 2 || exceptions.length) throw new Error(`Field-map jobs capture did not preserve its settled personnel map: ${JSON.stringify({ fieldServiceJobsLiveCapture, exceptions })}`);
    const layoutMetrics = await send("Page.getLayoutMetrics");
    const fullPageHeight = Math.min(1800, Math.ceil(layoutMetrics.cssContentSize?.height || 850));
    const fieldJobsCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1300, height: fullPageHeight, scale: 1 } });
    fs.writeFileSync(path.join(outputDir, "route-captures", "field-service-jobs-populated-map-1300x850.png"), Buffer.from(fieldJobsCapture.data, "base64"));
    await evaluate(`document.querySelector("[data-field-panel-mode='customer']")?.click()`);
    await delay(250);
    const output = { viewport: [1300, 850], mobileViewport: [390, 844], adminAccess, routeCount: routes.length, desktopRouteCount: desktopRoutes.length, routes: results, mobileResults, dashboardShell, assistantWorkflow, supportWorkflow, jobReportCurrencyAudit, automotiveStockWorkflow, vehicleMaintenanceWorkflow, fieldServiceRouteWorkflow, fieldServiceRouteSuccessWorkflow, fieldPersonnelDutyWorkflow, fieldServiceTomTomKeyWorkflow, leafletAssetAudit, fieldMapBrowserAudit, fieldServiceJobsLiveCapture, tileNetworkEvents, exceptions };
    const resultPath = path.join(outputDir, "route-smoke-result.json");
    fs.writeFileSync(resultPath, JSON.stringify(output, null, 2), "utf8");
    process.stdout.write(JSON.stringify({ resultPath, routeCount: routes.length, exceptionCount: exceptions.length }) + "\n");
    if (exceptions.length || !dashboardShell || results.some(item => !item.rootVisible || item.page !== item.route || item.dataPage !== item.route || item.contentChars < 1 || (item.route === "dashboard" && item.shortcutColumns !== 3) || (item.route === "job-reports" && (item.jobActionIcons !== 12 || !item.jobHeaderLayout?.inside || !item.jobHeaderLayout?.noOverlap || !item.jobHeaderLayout?.titleClear || item.jobHeaderLayout.rows !== 2 || item.jobHeaderLayout.width < 540 || item.jobSummary.total !== "6" || item.jobSummary.open !== "6" || item.jobSummary.paid !== "0" || item.jobSummary.services !== "15" || item.jobFooter?.color !== "rgb(37, 99, 235)" || item.jobFooter?.fontSize !== "10px" || item.jobCustomerWrap?.maxWidth !== "90px" || item.jobCustomerWrap?.height < 30 || item.jobCustomerWrap?.height > 36)) || (item.route === "manual" && (!item.manualLoaded || item.manualHeadingCount < 1 || item.manualTableCount < 1 || item.manualTableCells !== "Audit table\t42" || item.manualGeometry.tabs?.[0] < 278 || item.manualGeometry.tabs?.[0] > 282 || item.manualGeometry.tabs?.[2] < 995 || item.manualGeometry.tabs?.[2] > 1005 || item.manualGeometry.tabs?.[1] < 138 || item.manualGeometry.tabs?.[1] > 150 || item.manualGeometry.tabs?.[3] < 27 || item.manualGeometry.tabs?.[3] > 31 || item.manualGeometry.document?.[1] < 168 || item.manualGeometry.document?.[1] > 174))) || mobileResults.length !== routes.length || mobileResults.some(item => item.documentWidth > item.viewport + 1 || !item.rootVisible || item.page !== item.route || item.bodyPage !== item.route || item.contentChars < 1 || !item.title || (item.route === "dashboard" && item.shortcutColumns !== 1) || (item.route === "manual" && (!item.manualLoaded || item.manualHeadingCount < 1 || item.manualTableCount < 1 || item.manualTableCells !== "Audit table\t42")))) process.exitCode = 1;
  } finally {
    try { socket?.close(); } catch (_) {}
    if (browser.pid) {
      try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    }
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });




