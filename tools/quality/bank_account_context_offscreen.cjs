const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9240);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `bank-context-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function findPage() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const page = (await response.json()).find(target => target.type === "page");
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  const exceptions = [];
  let socket;
  let nextId = 0;
  const pending = new Map();
  try {
    const target = await findPage();
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
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 10000);
      pending.set(id, { resolve(value) { clearTimeout(timer); resolve(value); }, reject(error) { clearTimeout(timer); reject(error); } });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };

    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && typeof ayecBankShell === 'function' && typeof showContext === 'function'")) break;
      await delay(200);
    }
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page="banks";document.body.dataset.page="banks";currentAuthUser={role:"Admin"};
      ayecBankSelected=null;ayecBankSelectedIds=new Set();
      db.finance=[];db.settings.contextMenu=true;
      const fixture=[
        {id:701,bank_name:"Fixture Bank A",account_type:"Bank",account_holder:"Fixture A",iban:"TR000001",currency:"TRY",current_balance:2500,is_active:1},
        {id:702,bank_name:"Fixture Bank B",account_type:"Bank",account_holder:"Fixture B",iban:"TR000002",currency:"TRY",current_balance:1500,is_active:1}
      ];
      document.querySelector("#content").innerHTML=ayecBankShell();
      ayecBankRenderData(fixture);
      const first=document.querySelector('[data-bank-card="701"]');
      first.dispatchEvent(new MouseEvent("click",{bubbles:true}));
      const second=document.querySelector('[data-bank-card="702"]');
      second.dispatchEvent(new MouseEvent("click",{bubbles:true,ctrlKey:true}));
      const selection=Array.from(ayecBankSelectedIds).sort();
      const event=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:1240,clientY:870});
      second.dispatchEvent(event);
      const menu=document.querySelector("#contextMenu");
      const regular={prevented:event.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-context-action]"),button=>({action:button.dataset.contextAction,label:button.textContent.trim(),disabled:button.disabled})),separators:menu.querySelectorAll(".context-menu-separator").length,insideViewport:menu.getBoundingClientRect().left>=0&&menu.getBoundingClientRect().right<=innerWidth&&menu.getBoundingClientRect().top>=0&&menu.getBoundingClientRect().bottom<=innerHeight,selected:Array.from(ayecBankSelectedIds).sort()};
      desktopSettings.rc_bank="0";
      const disabledPreferenceEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});
      second.dispatchEvent(disabledPreferenceEvent);
      const preference={prevented:disabledPreferenceEvent.defaultPrevented,open:menu.classList.contains("open"),enabledForBanks:ayecContextMenuEnabled("banks"),enabledForLoans:ayecContextMenuEnabled("loans")};
      desktopSettings.rc_bank="1";
      menu.classList.remove("open");currentAuthUser={role:"Technician"};
      const roleEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:600,clientY:450});
      second.dispatchEvent(roleEvent);
      const restricted=Array.from(menu.querySelectorAll("[data-context-action]"),button=>({action:button.dataset.contextAction,disabled:button.disabled}));
      currentAuthUser={role:"Admin"};
      const bankApiCalls=[];
      apiFetch=async url=>{bankApiCalls.push(url);return {rows:[fixture[0]],columns:["id","bank_name","account_holder","iban","account_type","currency","current_balance"]};};
      document.querySelector('[data-bank-card="701"]').dispatchEvent(new MouseEvent("dblclick",{bubbles:true,cancelable:true}));
      await new Promise(resolve=>setTimeout(resolve,80));
      const doubleClick={isAdmin:userAdminRole(currentAuthUser?.role),calls:bankApiCalls,opened:document.querySelector("#appDialog")?.open===true,bankName:document.querySelector('#dialogBody input[name="bank_name"]')?.value||""};
      page="loans";document.body.dataset.page="loans";desktopSettings.rc_bank="0";
      const loanNode=document.createElement("div");loanNode.dataset.loanContextRow="88";document.body.appendChild(loanNode);
      const loanDisabledEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:400});loanNode.dispatchEvent(loanDisabledEvent);
      const loanDisabled={prevented:loanDisabledEvent.defaultPrevented,open:menu.classList.contains("open")};
      desktopSettings.rc_bank="1";
      const loanEnabledEvent=new MouseEvent("contextmenu",{bubbles:true,cancelable:true,clientX:500,clientY:400});loanNode.dispatchEvent(loanEnabledEvent);
      const loanEnabled={prevented:loanEnabledEvent.defaultPrevented,open:menu.classList.contains("open"),actions:Array.from(menu.querySelectorAll("[data-loan-context-action]"),button=>button.dataset.loanContextAction)};
      return {selection,regular,preference,restricted,doubleClick,loanDisabled,loanEnabled};
    })()`);
    const expected = ["bank-detail", "bank-edit", "bank-transfer", "bank-toggle", "bank-delete", "bank-bulk-toggle", "bank-bulk-delete"];
    if (JSON.stringify(result.selection) !== JSON.stringify(["701", "702"]) || !result.regular.open || !result.regular.prevented || JSON.stringify(result.regular.actions.map(item => item.action)) !== JSON.stringify(expected) || result.regular.separators !== 1 || !result.regular.insideViewport || JSON.stringify(result.regular.selected) !== JSON.stringify(["701", "702"])) throw new Error(`Bank context menu mismatch: ${JSON.stringify(result)}`);
    if (result.preference.prevented || result.preference.open || result.preference.enabledForBanks || result.preference.enabledForLoans) throw new Error(`Bank context preference mismatch: ${JSON.stringify(result.preference)}`);
    const shot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "bank-account-double-click-edit-headless.png"), Buffer.from(shot.data, "base64"));
    const disabled = result.restricted.filter(item => item.action !== "bank-detail").every(item => item.disabled);
    if (!disabled || result.restricted.find(item => item.action === "bank-detail")?.disabled || exceptions.length) throw new Error(`Bank context authorization mismatch: ${JSON.stringify({ result, exceptions })}`);
    if (result.doubleClick.calls.length !== 1 || result.doubleClick.bankName !== "Fixture Bank A" || !result.doubleClick.opened) throw new Error(`Bank account double-click edit mismatch: ${JSON.stringify(result.doubleClick)}`);
    if (result.loanDisabled.prevented || result.loanDisabled.open || !result.loanEnabled.prevented || !result.loanEnabled.open || JSON.stringify(result.loanEnabled.actions) !== JSON.stringify(["edit", "bulk", "details", "add-installment", "cancel", "delete"])) throw new Error(`Loan context preference/action mismatch: ${JSON.stringify({ disabled: result.loanDisabled, enabled: result.loanEnabled })}`);
    const menuRect = await evaluate(`(() => {
      document.querySelectorAll("#contextMenu, #loanContextMenu").forEach(menu => menu.classList.remove("open"));
      document.querySelector("#appDialog")?.close();
      currentAuthUser = { role: "Admin" };
      desktopSettings.rc_bank = "1";
      const card = document.querySelector('[data-bank-card="702"]');
      card.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 1240, clientY: 870 }));
      const menu = document.querySelector("#contextMenu");
      const rect = menu.getBoundingClientRect();
      const style = getComputedStyle(menu);
      return { x: rect.x + scrollX, y: rect.y + scrollY, width: rect.width, height: rect.height, open: menu.classList.contains("open"), display: style.display, opacity: style.opacity, background: style.backgroundColor };
    })()`);
    if (!menuRect.open || menuRect.display === "none" || Number(menuRect.opacity) === 0) throw new Error(`Bank menu screenshot is not visible: ${JSON.stringify(menuRect)}`);
    await delay(120);
    const menuShot = await send("Page.captureScreenshot", { format: "png", clip: { x: menuRect.x, y: menuRect.y, width: menuRect.width, height: menuRect.height, scale: 1 }, captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "bank-account-context-menu-current-matched-headless.png"), Buffer.from(menuShot.data, "base64"));
    console.log(JSON.stringify({ ...result, browserExceptions: exceptions.length, headless: true }));
  } finally {
    try { socket?.close(); } catch (_) {}
    try { browser.kill(); } catch (_) {}
  }
}

run().catch(error => { console.error(error.stack || String(error)); process.exitCode = 1; });



