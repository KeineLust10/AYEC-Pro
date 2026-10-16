const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 9233);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `loaner-context-headless-profile-${process.pid}`);
function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

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
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,900", baseUrl], { stdio: "ignore", windowsHide: true });
  const exceptions = [];
  let socket;
  try {
    const target = await waitForTarget();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let nextId = 0;
    const pending = new Map();
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId; pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(`${result.exceptionDetails.text}: ${result.exceptionDetails.exception?.description || "No exception description."}`);
      return result.result.value;
    };
    await send("Page.enable"); await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 60; attempt += 1) { if (await evaluate("document.readyState === 'complete' && typeof db !== 'undefined' && typeof ayecLoanerView !== 'undefined'")) break; await delay(200); }
    await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove(); document.body.classList.remove("auth-active");
      document.body.dataset.page = "loaners"; page = "loaners"; db.settings.contextMenu = true;
      ayecLoanerView = "depot";
      ayecLoanerDevices = [{ id: 71, status: "Depoda", device_type: "Dizüstü Bilgisayar", brand_model: "Fixture Laptop", serial_mac: "FIX-SN-71", shelf_no: "A-12", daily_penalty_fee: 50, notes: "Fixture notes" }, { id: 72, status: "Zimmette", device_type: "Dizüstü Bilgisayar", brand_model: "Assigned Laptop", serial_mac: "FIX-SN-72" }];
      ayecLoanerHistory = [{ id: 91, device_id: 71, status: "Aktif", date_returned: null }, { id: 92, device_id: 72, status: "Returned", date_returned: "2026-10-01" }];
      document.querySelector("#content").innerHTML = '<section class="card" style="margin:40px;padding:24px"><h1>Loaner menu audit</h1><button type="button" data-generic-add>New Loan</button><table><tbody><tr data-loaner-row="71" data-loaner-kind="depot"><td>Fixture Laptop</td><td></td><td></td><td></td><td></td><td></td><td></td><td><button type="button">Edit</button></td></tr><tr data-loaner-row="72" data-loaner-kind="depot"><td>Assigned laptop</td><td></td><td></td><td></td><td></td><td></td><td></td><td><button type="button">Edit</button></td></tr><tr data-loaner-row="91" data-loaner-kind="transaction"><td>Active loan</td></tr><tr data-loaner-row="92" data-loaner-kind="transaction"><td>Returned loan</td></tr></tbody></table></section>';
    })()`);
    const openMenu = async (kind, id, file) => {
      await evaluate(`(() => { ayecLoanerView = "${kind === "depot" ? "depot" : "active"}"; const row = document.querySelector('[data-loaner-kind="${kind}"][data-loaner-row="${id}"]'); row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 })); })()`);
      const result = await evaluate(`(() => { const menu = document.querySelector("#contextMenu"); return { actions: Array.from(menu.querySelectorAll("[data-loaner-context]"), item => item.dataset.loanerContext), labels: Array.from(menu.querySelectorAll("button"), item => item.innerText.trim()), separators: menu.querySelectorAll("hr.context-menu-separator").length, width: Math.round(menu.getBoundingClientRect().width), height: Math.round(menu.getBoundingClientRect().height) }; })()`);
      const expected = kind === "depot" ? ["add", "refresh", "assign", "edit", "delete-device"] : ["refresh", "return"];
      if (JSON.stringify(result.actions) !== JSON.stringify(expected)) throw new Error(`Unexpected ${kind} actions: ${JSON.stringify(result)}`);
      if (result.separators !== 1) throw new Error(`Expected one separator for ${kind}: ${JSON.stringify(result)}`);
      const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
      fs.writeFileSync(path.join(outputDir, file), Buffer.from(screenshot.data, "base64"));
      await evaluate('document.querySelector("#contextMenu").classList.remove("open")');
      return result;
    };
    const pageSettingDisabled = await evaluate(`(() => {
      desktopSettings.rc_loaner = "0";
      const row = document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]');
      const event = new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 });
      row.dispatchEvent(event);
      const result = { prevented: event.defaultPrevented, open: document.querySelector("#contextMenu").classList.contains("open") };
      desktopSettings.rc_loaner = "1";
      return result;
    })()`);
    if (pageSettingDisabled.prevented || pageSettingDisabled.open) throw new Error(`Loaner page setting did not suppress its context menu: ${JSON.stringify(pageSettingDisabled)}`);
    const touchMenu = await evaluate(`(async () => {
      const row = document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]');
      const menu = document.querySelector("#contextMenu");
      row.dispatchEvent(new PointerEvent("pointerdown", { pointerType: "touch", pointerId: 1, bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      await new Promise(resolve => setTimeout(resolve, 600));
      const opened = { open: menu.classList.contains("open"), id: menu.dataset.loanerId, actions: Array.from(menu.querySelectorAll("[data-loaner-context]"), item => item.dataset.loanerContext) };
      menu.classList.remove("open");
      row.dispatchEvent(new PointerEvent("pointerdown", { pointerType: "touch", pointerId: 2, bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      document.dispatchEvent(new PointerEvent("pointermove", { pointerType: "touch", pointerId: 2, bubbles: true, cancelable: true, clientX: 310, clientY: 220 }));
      await new Promise(resolve => setTimeout(resolve, 600));
      return { opened, movementCanceled: !menu.classList.contains("open") };
    })()`);
    if (!touchMenu.opened.open || touchMenu.opened.id !== "71" || JSON.stringify(touchMenu.opened.actions) !== JSON.stringify(["add", "refresh", "assign", "edit", "delete-device"]) || !touchMenu.movementCanceled) throw new Error(`Loaner touch context menu mismatch: ${JSON.stringify(touchMenu)}`);
    const keyboardMenu = await evaluate(`(() => {
      desktopSettings.rc_loaner = "1";
      const row = document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]');
      row.focus();
      const event = new KeyboardEvent("keydown", { key: "F10", shiftKey: true, bubbles: true, cancelable: true });
      row.dispatchEvent(event);
      const menu = document.querySelector("#contextMenu");
      const result = { prevented: event.defaultPrevented, open: menu.classList.contains("open"), id: menu.dataset.loanerId, actions: Array.from(menu.querySelectorAll("[data-loaner-context]"), item => item.dataset.loanerContext) };
      menu.classList.remove("open");
      return result;
    })()`);
    if (!keyboardMenu.prevented || !keyboardMenu.open || keyboardMenu.id !== "71" || JSON.stringify(keyboardMenu.actions) !== JSON.stringify(["add", "refresh", "assign", "edit", "delete-device"])) throw new Error(`Keyboard context menu mismatch: ${JSON.stringify(keyboardMenu)}`);
    const depot = await openMenu("depot", 71, "loaner-depot-context-headless.png");
    const active = await openMenu("transaction", 91, "loaner-active-context-headless.png");
    const stateMenus = await evaluate(`(() => {
      const menu = document.querySelector("#contextMenu");
      const openFor = (kind, id, view) => {
        ayecLoanerView = view;
        const row = document.querySelector('[data-loaner-kind="' + kind + '"][data-loaner-row="' + id + '"]');
        row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
        return { actions: Array.from(menu.querySelectorAll("[data-loaner-context]"), item => item.dataset.loanerContext), separators: menu.querySelectorAll("hr.context-menu-separator").length };
      };
      return { assigned: openFor("depot", 72, "depot"), returned: openFor("transaction", 92, "active") };
    })()`);
    if (JSON.stringify(stateMenus.assigned.actions) !== JSON.stringify(["add", "refresh", "edit", "delete-device"]) || stateMenus.assigned.separators !== 1 || JSON.stringify(stateMenus.returned.actions) !== JSON.stringify(["refresh"]) || stateMenus.returned.separators !== 0) throw new Error(`Loaner state menu mismatch: ${JSON.stringify(stateMenus)}`);
    await evaluate('document.querySelector("#contextMenu").classList.remove("open")');
    const doubleClick = await evaluate(`(() => {
      const actualDialog = ayecLoanerDeviceDialog;
      ayecLoanerDeviceDialog = row => { window.__loanerDoubleClickId = row.id; };
      const row = document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]');
      row.cells[0].dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
      const openedId = window.__loanerDoubleClickId;
      row.cells[7].querySelector("button").dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
      const afterActionCell = window.__loanerDoubleClickId;
      ayecLoanerDeviceDialog = actualDialog;
      return { openedId, afterActionCell };
    })()`);
    if (doubleClick.openedId !== 71 || doubleClick.afterActionCell !== 71) throw new Error(`Loaner inventory double-click did not match desktop behavior: ${JSON.stringify(doubleClick)}`);
    const returnDialog = await evaluate(`(async () => {
      apiFetch = async (url, options = {}) => { window.__loanerReturnRequest = { url, payload: JSON.parse(options.body) }; return { ok: true }; };
      loadGenericModule = async () => ({});
      document.querySelector('[data-loaner-kind="transaction"][data-loaner-row="91"]').dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      document.querySelector('#contextMenu [data-loaner-context="return"]').click();
      const form = document.querySelector("#dialogForm");
      const controls = Array.from(form.querySelectorAll("[name]"), control => ({ name: control.name, type: control.type, label: control.closest(".field")?.querySelector("label")?.textContent.trim() }));
      return { title: document.querySelector("#dialogTitle").textContent, controls, open: document.querySelector("#appDialog").open };
    })()`);
    if (returnDialog.title !== "Cihaz\u0131 \u0130ade Al" || returnDialog.controls.map(control => control.name).join(",") !== "condition_in,penalty_applied" || !returnDialog.open) throw new Error(`Loan return dialog did not render the expected fields: ${JSON.stringify(returnDialog)}`);
    const returnScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "loaner-return-dialog-headless.png"), Buffer.from(returnScreenshot.data, "base64"));
    const returnSubmit = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm");
      form.elements.namedItem("condition_in").value = "Screen clean";
      form.elements.namedItem("penalty_applied").value = "25";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      return { open: document.querySelector("#appDialog").open, request: window.__loanerReturnRequest };
    })()`);
    if (returnSubmit.open || returnSubmit.request?.url !== "/api/desktop/loaners/return" || returnSubmit.request.payload.transaction_id !== 91 || returnSubmit.request.payload.condition_in !== "Screen clean" || returnSubmit.request.payload.penalty_applied !== "25") throw new Error(`Loan return dialog did not submit the expected values: ${JSON.stringify(returnSubmit)}`);
    const selector = await evaluate(`(async () => {
      apiFetch = async (url, options = {}) => {
        if (url.includes("loaner_devices?limit=1000")) return { rows: [{ id: 71, status: "Depoda", brand_model: "Fixture Laptop", serial_mac: "FIX-SN-71" }, { id: 72, status: "Depoda", brand_model: "Assigned Laptop", serial_mac: "FIX-SN-72" }] };
        if (url.includes("loaner_transactions?limit=1000")) return { rows: [{ id: 92, device_id: 72, status: "Aktif" }] };
        if (options.method === "POST") { window.__loanerDeviceRequest = { url, payload: JSON.parse(options.body) }; return { ok: true }; }
        return { ok: true };
      };
      loadGenericModule = async () => ({});
      document.querySelector("[data-generic-add]").click();
      await new Promise(resolve => setTimeout(resolve, 20));
      const select = document.querySelector('#dialogBody [name="device_id"]');
      return { title: document.querySelector("#dialogTitle").textContent, submit: document.querySelector("#dialogSubmit").textContent, options: Array.from(select.options, option => ({ value: option.value, text: option.textContent })) };
    })()`);
    if (selector.title !== "Yeni Emanet Ver" || selector.options.length !== 1 || selector.options[0].value !== "71") throw new Error(`New loan selector did not filter unavailable devices: ${JSON.stringify(selector)}`);
    const selectorScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "loaner-new-assignment-device-picker-headless.png"), Buffer.from(selectorScreenshot.data, "base64"));
    const nextForm = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm"); form.requestSubmit(); await new Promise(resolve => setTimeout(resolve, 30));
      const title = document.querySelector("#dialogTitle").textContent; const controls = Array.from(document.querySelectorAll("#dialogBody [name]"), input => input.name);
      document.querySelector("#dialogCancel").click(); return { title, controls };
    })()`);
    if (nextForm.title !== "M\u00fc\u015fteriye Tesis Et (Zimmetle)" || !nextForm.controls.includes("customer_name")) throw new Error(`New loan selector did not open assignment details: ${JSON.stringify(nextForm)}`);
    const deviceForm = await evaluate(`(() => {
      document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]').dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      document.querySelector('#contextMenu [data-loaner-context="add"]').click();
      const form = document.querySelector("#dialogForm"), type = form.elements.namedItem("device_type");
      return { title: document.querySelector("#dialogTitle").textContent, submit: document.querySelector("#dialogSubmit").textContent, controls: Array.from(form.querySelectorAll("[name]"), control => ({ name: control.name, required: control.required, value: control.value })), types: Array.from(type.options, option => option.textContent), nativeRequired: !form.checkValidity() };
    })()`);
    if (deviceForm.title !== "Yeni \u0130kame Cihaz Ekle" || !deviceForm.nativeRequired || deviceForm.controls.map(control => control.name).join(",") !== "device_type,brand_model,serial_mac,shelf_no,daily_penalty_fee,notes" || deviceForm.controls.find(control => control.name === "daily_penalty_fee").value !== "50.0") throw new Error(`Device creation dialog does not match desktop: ${JSON.stringify(deviceForm)}`);
    const deviceScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "loaner-device-create-dialog-headless.png"), Buffer.from(deviceScreenshot.data, "base64"));
    const deviceWrite = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm"); form.elements.namedItem("brand_model").value = "Created Fixture"; form.elements.namedItem("serial_mac").value = "CREATED-SN"; form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100)); return { open: document.querySelector("#appDialog").open, request: window.__loanerDeviceRequest };
    })()`);
    if (deviceWrite.open || deviceWrite.request?.url !== "/api/desktop/table/loaner_devices" || deviceWrite.request.payload.brand_model !== "Created Fixture" || deviceWrite.request.payload.daily_penalty_fee !== 50) throw new Error(`Device creation did not submit expected values: ${JSON.stringify(deviceWrite)}`);
    const deviceEdit = await evaluate(`(() => {
      document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]').dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      document.querySelector('#contextMenu [data-loaner-context="edit"]').click();
      const form = document.querySelector("#dialogForm");
      const type = form.elements.namedItem("device_type");
      return { title: document.querySelector("#dialogTitle").textContent, submit: document.querySelector("#dialogSubmit").textContent, values: Object.fromEntries(Array.from(form.querySelectorAll("[name]"), control => [control.name, control.value])), selectedType: type.value };
    })()`);
    if (deviceEdit.title !== "Emanet Cihaz\u0131 D\u00fczenle" || deviceEdit.values.brand_model !== "Fixture Laptop" || deviceEdit.values.serial_mac !== "FIX-SN-71" || deviceEdit.values.notes !== "Fixture notes" || deviceEdit.selectedType !== "Diz\u00fcst\u00fc Bilgisayar") throw new Error(`Device edit dialog did not retain stored fields: ${JSON.stringify(deviceEdit)}`);
    const deviceEditScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "loaner-device-edit-dialog-headless.png"), Buffer.from(deviceEditScreenshot.data, "base64"));
    const deviceEditSubmit = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm"); form.elements.namedItem("brand_model").value = "Edited Fixture"; form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100)); return { open: document.querySelector("#appDialog").open, request: window.__loanerDeviceRequest };
    })()`);
    if (deviceEditSubmit.open || deviceEditSubmit.request?.payload.id !== 71 || deviceEditSubmit.request.payload._action !== "update" || deviceEditSubmit.request.payload.brand_model !== "Edited Fixture") throw new Error(`Device edit did not submit expected values: ${JSON.stringify(deviceEditSubmit)}`);
    const assignmentForm = await evaluate(`(() => {
      apiFetch = async (url, options) => { window.__loanerAssignRequest = { url, payload: JSON.parse(options.body) }; return { ok: true }; };
      loadGenericModule = async () => ({});
      const row = document.querySelector('[data-loaner-kind="depot"][data-loaner-row="71"]');
      row.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 280, clientY: 220 }));
      document.querySelector('#contextMenu [data-loaner-context="assign"]').click();
      const form = document.querySelector("#dialogForm");
      const controls = Array.from(form.querySelectorAll("[name]"), control => ({ name: control.name, type: control.type, required: control.required, label: control.closest(".field")?.querySelector("label")?.textContent.trim() }));
      return { title: document.querySelector("#dialogTitle").textContent, submit: document.querySelector("#dialogSubmit").textContent, controls, nativeRequired: !form.checkValidity() };
    })()`);
    const assignmentScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    fs.writeFileSync(path.join(outputDir, "loaner-assignment-dialog-headless.png"), Buffer.from(assignmentScreenshot.data, "base64"));
    const assignmentSubmit = await evaluate(`(async () => {
      const form = document.querySelector("#dialogForm");
      form.elements.namedItem("customer_name").value = "Fixture Customer";
      form.elements.namedItem("customer_phone").value = "5550102";
      form.elements.namedItem("tracking_no").value = "SRV-71";
      form.elements.namedItem("condition_out").value = "Screen intact";
      form.requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 100));
      return { open: document.querySelector("#appDialog").open, request: window.__loanerAssignRequest };
    })()`);
    if (!assignmentForm.nativeRequired || assignmentSubmit.open || assignmentSubmit.request?.url !== "/api/desktop/loaners/assign") throw new Error(`Assignment form did not validate or submit: ${JSON.stringify({ assignmentForm, assignmentSubmit })}`);
    if (assignmentForm.controls.map(control => control.name).join(",") !== "customer_name,customer_phone,tracking_no,condition_out,expected_return") throw new Error(`Unexpected assignment fields: ${JSON.stringify(assignmentForm.controls)}`);
    if (assignmentSubmit.request.payload.device_id !== 71 || assignmentSubmit.request.payload.customer_name !== "Fixture Customer" || assignmentSubmit.request.payload.expected_return.length !== 16) throw new Error(`Unexpected assignment payload: ${JSON.stringify(assignmentSubmit.request)}`);
    if (exceptions.length) throw new Error(`Browser exceptions: ${exceptions.join(" | ")}`);
    process.stdout.write(JSON.stringify({ depot, active, stateMenus, pageSettingDisabled, touchMenu, keyboardMenu, returnDialog, returnSubmit, selector, nextForm, deviceForm, deviceWrite, deviceEdit, deviceEditSubmit, assignmentForm, assignmentSubmit, exceptions: exceptions.length, headless: true }, null, 2) + "\n");
  } finally {
    try { socket?.close(); } catch (_) {}
    const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      let processIds = [];
      try {
        const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
        processIds = output.trim().split(/\s+/).filter(value => /^\d+$/.test(value));
      } catch (_) {}
      if (!processIds.length) break;
      for (const pid of processIds) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
      await delay(300);
    }
    try { browser.kill(); } catch (_) {}
    await delay(300);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
