const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_QUICK_NOTES_CAPTURE_CDP_PORT || 9341);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `quick-notes-visual-headless-${process.pid}`);

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1280,1120", baseUrl], { stdio: "ignore", windowsHide: true });
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
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
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
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 1120, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof apiFetch === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    const state = await evaluate(`(async()=>{
      document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');
      db.settings.doubleClick=true;db.settings.contextMenu=true;desktopSettings.enable_right_click='1';
      const rows=[
        {id:1,category:'Bilgisayar',title:'Ariza Hizli Secimi',label:'GORUNTU YOK',display_order:0,is_active:1},
        {id:2,category:'Bilgisayar',title:'Islem Detayi',label:'FORMAT ATILDI',display_order:1,is_active:1},
        {id:3,category:'Bilgisayar',title:'Gizli Not',label:'TEST OK',display_order:2,is_active:1},
        {id:4,category:'Bilgisayar',title:'Aksesuar',label:'Guc Adaptoru',display_order:3,is_active:1},
        {id:5,category:'Bilgisayar',title:'Cihaz Testi',label:'LCD Goruntu',display_order:4,is_active:1},
        {id:6,category:'Cep Telefonu',title:'Ariza Hizli Secimi',label:'EKRAN KIRIK',display_order:5,is_active:1},
        {id:7,category:'Cep Telefonu',title:'Islem Detayi',label:'Ekran Degisti',display_order:6,is_active:1},
        {id:8,category:'Cep Telefonu',title:'Gizli Not',label:'TEST OK',display_order:7,is_active:1},
        {id:9,category:'Cep Telefonu',title:'Aksesuar',label:'SIM Kart',display_order:8,is_active:1},
        {id:10,category:'Cep Telefonu',title:'Cihaz Testi',label:'Dokunmatik Ekran',display_order:9,is_active:1},
        {id:11,category:'Guvenlik Sistemleri',title:'Ariza Hizli Secimi',label:'KAMERA GORUNTU VERMiyor',display_order:10,is_active:1}
      ];
      let noteReads=0;window.fetch=async url=>{noteReads++;return new Response(JSON.stringify({ok:true,rows,count:rows.length}),{status:200,headers:{'Content-Type':'application/json'}})};
      openManifestDialog({key:'quick_notes_editor'});await new Promise(resolve=>setTimeout(resolve,300));
      const readsBeforeRefresh=noteReads,refreshButton=document.querySelector('#quickNoteRefresh');refreshButton?.click();await new Promise(resolve=>setTimeout(resolve,120));
      const settingsContent=document.querySelector('.settings-content'),settingsSidebar=document.querySelector('.settings-sidebar'),actions=document.querySelector('.page-head .actions');
      const genericSave=document.querySelector('[data-action="save-settings"]');
      const rect=selector=>{const r=document.querySelector(selector)?.getBoundingClientRect();return r?[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]:null};
      const geometry={content:rect('.settings-content'),cardHead:rect('.settings-content>.quick-notes-card-head'),heading:rect('.quick-notes-title-row h3'),description:rect('.quick-notes-heading-copy>p'),count:rect('#quickNoteCount'),profile:rect('.quick-note-profile-toolbar'),toolbar:rect('.quick-notes-toolbar'),host:rect('#quickNotesHost'),tableWrap:rect('#quickNotesHost .table-wrap'),tableViewport:(()=>{const el=document.querySelector('#quickNotesHost .table-wrap');return el?{clientHeight:el.clientHeight,scrollHeight:el.scrollHeight,overflowY:getComputedStyle(el).overflowY}:null})(),title:rect('#pageTitle'),filter:rect('#quickNoteFilter'),search:rect('#quickNoteSearch'),tags:rect('.quick-note-tags'),table:rect('.quick-notes-table'),tableHead:rect('.quick-notes-table thead'),firstRow:rect('.quick-notes-table tbody tr:first-child'),quickNoteToggle:rect('.quick-note-toggle'),actionButtons:[...document.querySelectorAll('.quick-note-edit,.quick-note-delete')].slice(0,2).map(el=>{const r=el.getBoundingClientRect();return[Math.round(r.width),Math.round(r.height)]}),actionIcons:document.querySelectorAll('#quickNotesHost .quick-note-icon').length,rowCells:[...document.querySelectorAll('.quick-notes-table tbody tr:first-child td')].map(cell=>{const r=cell.getBoundingClientRect();return{box:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],children:[...cell.children].map(child=>{const b=child.getBoundingClientRect(),c=getComputedStyle(child);return{className:child.className,box:[Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)],height:c.height,padding:c.padding}})}}),columns:[...document.querySelectorAll('.quick-notes-table thead th')].map(cell=>Math.round(cell.getBoundingClientRect().width)),refresh:rect('#quickNoteRefresh'),add:rect('#quickNoteAdd')};
      const contentStyle=getComputedStyle(settingsContent),headingStyle=getComputedStyle(document.querySelector('.settings-content>.card-head h3')),descriptionStyle=getComputedStyle(document.querySelector('.settings-content>.card-head p')),firstCellStyle=getComputedStyle(document.querySelector('.quick-notes-table tbody tr:first-child td:first-child'));
      return{geometry,contentStyle:{padding:contentStyle.padding,display:contentStyle.display,boxSizing:contentStyle.boxSizing},headingStyle:{fontSize:headingStyle.fontSize,lineHeight:headingStyle.lineHeight,fontWeight:headingStyle.fontWeight,fontFamily:headingStyle.fontFamily,scrollWidth:document.querySelector('.settings-content>.card-head h3')?.scrollWidth,clientWidth:document.querySelector('.settings-content>.card-head h3')?.clientWidth},descriptionStyle:{fontSize:descriptionStyle.fontSize,lineHeight:descriptionStyle.lineHeight},firstCellStyle:{height:firstCellStyle.height,boxSizing:firstCellStyle.boxSizing,padding:firstCellStyle.padding,border:firstCellStyle.border},host:!!document.querySelector('#quickNotesHost'),rows:document.querySelectorAll('#quickNotesHost .quick-notes-table tbody tr').length,titleText:document.querySelector('#pageTitle')?.textContent||'',heading:document.querySelector('#quickNotesHost')?.innerText.slice(0,100)||'',section:document.body.dataset.settingsSection,sidebarDisplay:settingsSidebar?getComputedStyle(settingsSidebar).display:'missing',contentWidth:Math.round(settingsContent?.getBoundingClientRect().width||0),saveDisplay:genericSave?getComputedStyle(genericSave).display:'missing',refreshButton:!!refreshButton,refreshRead:noteReads>readsBeforeRefresh,actionPosition:actions?getComputedStyle(actions).position:'missing',actionStyle:actions?.getAttribute('style')||'',documentWidth:document.documentElement.scrollWidth};
    })()`);
    if (!state.host || state.rows !== 11 || state.section !== "notes" || state.sidebarDisplay !== "none" || state.saveDisplay !== "none" || !state.refreshButton || !state.refreshRead) throw new Error("Quick notes workspace fixture or layout did not match: " + JSON.stringify(state));
    const near = (actual, expected, tolerance = 1) => Array.isArray(actual) && actual.length === expected.length && actual.every((value, index) => Math.abs(value - expected[index]) <= tolerance);
    const g = state.geometry;
    if (!near(g.content, [272, 124, 992, 968]) || !near(g.heading, [302, 157, 312, 34]) || !near(g.count, [630, 160, 130, 28]) || !near(g.profile, [772, 157, 32, 32]) || !near(g.refresh, [932, 168, 107, 42]) || !near(g.add, [1059, 168, 175, 42]) || !near(g.filter, [364, 273, 310, 40]) || !near(g.search, [719, 273, 179, 40]) || !near(g.tags, [904, 275, 302, 40]) || !near(g.tableWrap, [302, 358, 932, 729]) || !near(g.table, [303, 359, 930, 727]) || !near(g.tableHead, [304, 360, 928, 52]) || !near(g.firstRow, [304, 412, 928, 61]) || !near(g.columns, [72, 305, 218, 80, 130, 120], 2) || !near(g.quickNoteToggle.slice(2), [42, 24]) || JSON.stringify(g.actionButtons)!==JSON.stringify([[30,30],[30,30]]) || g.actionIcons!==22) throw new Error("Quick notes desktop geometry did not match: " + JSON.stringify(g));
    const screenshot = await send("Page.captureScreenshot", { format: "png", fromSurface: true });
    const output = path.join(outputDir, "quick-notes-workspace-headless.png");
    fs.writeFileSync(output, Buffer.from(screenshot.data, "base64"));
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const mobile = await evaluate(`(() => { const content=document.querySelector('.settings-content')?.getBoundingClientRect(),table=document.querySelector('#quickNotesHost .table-wrap')?.getBoundingClientRect();return{viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,content:content?[Math.round(content.x),Math.round(content.y),Math.round(content.width),Math.round(content.height)]:null,table:table?[Math.round(table.x),Math.round(table.y),Math.round(table.width),Math.round(table.height)]:null,refreshVisible:!!document.querySelector('#quickNoteRefresh')&&document.querySelector('#quickNoteRefresh').getBoundingClientRect().width>0,searchVisible:!!document.querySelector('#quickNoteSearch')&&document.querySelector('#quickNoteSearch').getBoundingClientRect().width>0}; })()`);
    if (mobile.viewport !== 390 || mobile.documentWidth > 390 || !mobile.content || mobile.content[0] < 0 || mobile.content[0] + mobile.content[2] > 390 || !mobile.refreshVisible || !mobile.searchVisible) throw new Error("Quick notes mobile layout overflowed or hid controls: " + JSON.stringify(mobile));
    console.log(JSON.stringify({ ...state, mobile, screenshot: output }));
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
