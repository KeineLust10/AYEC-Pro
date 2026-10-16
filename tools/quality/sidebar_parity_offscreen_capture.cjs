const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `sidebar-parity-headless-profile-${process.pid}`);
const auditSector = process.env.AYEC_AUDIT_SECTOR === "otomotiv" ? "otomotiv" : "teknik_servis";

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${debugPort}/json`);
      const targets = await response.json();
      const origin = new URL(baseUrl).origin;
      const page = targets.find(target => target.type === "page" && target.url?.startsWith(origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose a CDP page target.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, "--window-size=1280,650", baseUrl], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await waitForTarget();
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { socket.addEventListener("open", resolve, { once: true }); socket.addEventListener("error", reject, { once: true }); });
    let nextId = 0;
    const pending = new Map();
    const runtimeExceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (!message.id) {
        if (message.method === "Runtime.exceptionThrown") runtimeExceptions.push(message.params.exceptionDetails?.exception?.description || message.params.exceptionDetails?.text || "Unknown browser exception");
        return;
      }
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
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
      return result.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 650, deviceScaleFactor: 1, mobile: false });
    let appReady = false;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && document.querySelector('.app-shell') && document.querySelector('#nav') && String(renderNav).includes('OTOMOTIV MODU')")) { appReady = true; break; }
      await delay(200);
    }
    if (!appReady) throw new Error(`The parity menu runtime did not initialize: ${JSON.stringify(runtimeExceptions)}`);
    const state = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      currentSector = ${JSON.stringify(auditSector)};
      renderNav();
      const shell = document.querySelector(".app-shell");
      shell?.classList.remove("sidebar-collapsed", "sidebar-peek");
      const sidebar = document.querySelector(".sidebar");
      if (sidebar) { sidebar.style.transform = "none"; sidebar.style.width = "320px"; }
      const nav = document.querySelector("#nav");
      nav?.querySelectorAll(".nav-parent.open").forEach(button => button.classList.remove("open"));
      nav?.querySelectorAll(".submenu.open").forEach(submenu => submenu.classList.remove("open"));
      const bounds = element => { const box = element?.getBoundingClientRect(); return box ? { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) } : null; };
      const topText = Array.from(document.querySelectorAll("body *")).filter(element => element.children.length === 0 && element.textContent.trim()).map(element => ({ text: element.textContent.trim().slice(0, 32), rect: bounds(element) })).filter(item => item.rect?.height && item.rect.y < 70 && item.rect.x < 320);
      const navButtons = Array.from(nav?.querySelectorAll(".nav-button") || []);
      const parentButton = nav?.querySelector(".nav-parent");
      const childButton = nav?.querySelector(".submenu .nav-button");
      const brand = sidebar?.querySelector(".brand");
      const sectorBadge = document.querySelector("#sectorBrand");
      const brandStyle = brand ? getComputedStyle(brand) : null;
      const parentSubmenu = parentButton ? document.getElementById(parentButton.dataset.parent) : null;
      return { navItems: navButtons.length, groups: nav?.querySelectorAll(".nav-group-title").length || 0, sidebarWidth: Math.round(sidebar?.getBoundingClientRect().width || 0), shell: bounds(shell), sidebar: bounds(sidebar), brand: bounds(brand), brandStyle: brandStyle ? { height: brandStyle.height, padding: brandStyle.padding, margin: brandStyle.margin, boxSizing: brandStyle.boxSizing } : null, brandMarkStyle: sidebar?.querySelector(".brand-mark") ? { background: getComputedStyle(sidebar.querySelector(".brand-mark")).backgroundColor, borderColor: getComputedStyle(sidebar.querySelector(".brand-mark")).borderColor } : null, sectorBadge: sectorBadge ? { text: sectorBadge.textContent, className: sectorBadge.className, title: sectorBadge.title } : null, runtime: { menuModel: typeof ayecSectorMenu, navSource: String(renderNav).slice(0, 90) }, nav: bounds(nav), navTypography: { parent: parentButton ? { size: getComputedStyle(parentButton).fontSize, height: bounds(parentButton).height, y: bounds(parentButton).y, active: parentButton.classList.contains("active"), background: getComputedStyle(parentButton).backgroundColor, color: getComputedStyle(parentButton).color, parentId: parentButton.dataset.parent, submenuId: parentSubmenu?.id, activeChildren: Array.from(parentSubmenu?.querySelectorAll("[data-page].active") || [], button => button.dataset.page) } : null, child: childButton ? { size: getComputedStyle(childButton).fontSize, height: bounds(childButton).height, y: bounds(childButton).y } : null }, activePages: Array.from(nav?.querySelectorAll("[data-page].active") || [], button => button.dataset.page), topText };
    })()`);
    if (!state.sidebarWidth) throw new Error(`Sidebar is not visible: ${JSON.stringify(state)}`);
    if (!state.navTypography.parent?.active || !state.activePages.includes("dashboard")) throw new Error(`Selected dashboard navigation state is not visible: ${JSON.stringify(state.navTypography)}`);
    const expectedSectorBadge = auditSector === "otomotiv" ? "OTOMOTIV MODU" : "ERP";
    const badgeMatches = state.sectorBadge?.text === expectedSectorBadge && (auditSector !== "otomotiv" || state.sectorBadge.className.includes("automotive-sector"));
    if (!badgeMatches) throw new Error(`Expected the ${expectedSectorBadge} sector badge: ${JSON.stringify({ state, runtimeExceptions })}`);
    if (state.brandMarkStyle?.background !== "rgb(30, 48, 77)" || state.brandMarkStyle?.borderColor !== "rgb(27, 42, 66)") throw new Error(`Unexpected dark-blue brand mark palette: ${JSON.stringify(state.brandMarkStyle)}`);
    await delay(400);
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 400, y: 640 });
    await delay(80);
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: 0, width: 320, height: 650, scale: 1 } });
    const filename = path.join(outputDir, `web-sidebar-${auditSector}-current-headless.png`);
    fs.writeFileSync(filename, Buffer.from(screenshot.data, "base64"));
    const sidebarRouteAudit = await evaluate(`(async () => {
      window.handleUnauthorized = () => {};
      render = () => { document.body.dataset.page = page; };
      const originalSector = currentSector;
      const results = [];
      for (const sector of ["teknik_servis", "otomotiv"]) {
        currentSector = sector;
        renderNav();
        const ids = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]"), button => button.dataset.page);
        for (const id of ids) {
          let button = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item => item.dataset.page === id);
          const submenu = button?.closest(".submenu");
          if (submenu && !submenu.classList.contains("open")) {
            const parent = Array.from(document.querySelectorAll("#nav .nav-parent")).find(item => item.dataset.parent === submenu.id);
            parent?.click();
          }
          button = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item => item.dataset.page === id);
          button?.click();
          await new Promise(resolve => setTimeout(resolve, 5));
          const active = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page].active"), item => item.dataset.page);
          const parentButton = submenu ? Array.from(document.querySelectorAll("#nav .nav-parent")).find(item => item.dataset.parent === submenu.id) : null;
          results.push({ sector, id, page, active: active.includes(id), parentActive: !parentButton || parentButton.classList.contains("active") });
        }
        const mainPageTargets = Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]"), button => button.dataset.mainPage).filter(Boolean);
        for (const id of mainPageTargets) {
          const button = Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]")).find(item => item.dataset.mainPage === id);
          button?.click();
          await new Promise(resolve => setTimeout(resolve, 5));
          const activeParent = Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]")).find(item => item.dataset.mainPage === id);
          results.push({ sector, id, page, active: page === id, parentActive: Boolean(activeParent?.classList.contains("active")) });
        }
      }
      currentSector = originalSector;
      renderNav();
      navigate("dashboard");
      const failures = results.filter(item => item.page !== item.id || !item.active || !item.parentActive);
      return { tested: results.length, failures, duplicates: results.filter((item, index) => results.some((other, otherIndex) => otherIndex !== index && other.sector === item.sector && other.id === item.id)).map(item => ({ sector: item.sector, id: item.id })), sectors: Object.fromEntries(["teknik_servis", "otomotiv"].map(sector => [sector, results.filter(item => item.sector === sector).map(item => item.id)])) };
    })()`);
    if (sidebarRouteAudit.failures.length || sidebarRouteAudit.duplicates.length || runtimeExceptions.length) throw new Error(`Sidebar audit reported route failures, duplicate entries, or browser exceptions: ${JSON.stringify({ sidebarRouteAudit, runtimeExceptions })}`);
    const menuCustomizationAudit = await evaluate(`(() => {
      const oldLabels = desktopInternalSettings.web_menu_labels;
      const oldVisibility = desktopInternalSettings.web_menu_visibility;
      desktopInternalSettings.web_menu_labels = JSON.stringify({ teknik_servis: { dashboard: "Audit Technical" }, otomotiv: { dashboard: "Audit Automotive" } });
      desktopInternalSettings.web_menu_visibility = JSON.stringify({ teknik_servis: { support: false }, otomotiv: { support: false } });
      const results = [];
      for (const [sector, expected] of [["teknik_servis", "Audit Technical"], ["otomotiv", "Audit Automotive"]]) {
        currentSector = sector;
        renderNav();
        const label = document.querySelector('#nav [data-page="dashboard"] .nav-label')?.textContent || "";
        const hiddenSupportVisible = Boolean(document.querySelector('#nav [data-page="support"]'));
        results.push({ sector, label, expected, hiddenSupportVisible });
      }
      if (oldLabels === undefined) delete desktopInternalSettings.web_menu_labels; else desktopInternalSettings.web_menu_labels = oldLabels;
      if (oldVisibility === undefined) delete desktopInternalSettings.web_menu_visibility; else desktopInternalSettings.web_menu_visibility = oldVisibility;
      currentSector = "${auditSector}";
      renderNav();
      return results;
    })()`);
    if (menuCustomizationAudit.some(item => item.label !== item.expected || item.hiddenSupportVisible)) throw new Error(`Sidebar customization parity failed: ${JSON.stringify(menuCustomizationAudit)}`);
    const permissionAudit = await evaluate(`(() => {
      const oldUser = currentAuthUser;
      const results = [];
      const serviceParentVisible = () => Array.from(document.querySelectorAll("#nav .nav-parent")).some(button => document.getElementById(button.dataset.parent)?.querySelector('[data-page="dashboard"]'));
      currentAuthUser = { role: "Technician", permissions: JSON.stringify({ pages: [40, 41, 21] }) };
      currentSector = "teknik_servis";
      renderNav();
      results.push({ sector: currentSector, allowed: ["dashboard", "services", "customers"].map(id => Boolean(document.querySelector('#nav [data-page="' + id + '"]'))), denied: ["service-list", "technician", "support"].map(id => Boolean(document.querySelector('#nav [data-page="' + id + '"]'))), serviceParentVisible: serviceParentVisible() });
      currentAuthUser = { role: "Technician", permissions: JSON.stringify({ pages: [40, 60, 21] }) };
      currentSector = "otomotiv";
      renderNav();
      results.push({ sector: currentSector, allowed: ["dashboard", "automotive-stock", "customers"].map(id => Boolean(document.querySelector('#nav [data-page="' + id + '"]'))), denied: ["service-list", "vehicle-maintenance", "support"].map(id => Boolean(document.querySelector('#nav [data-page="' + id + '"]'))), serviceParentVisible: serviceParentVisible() });
      currentAuthUser = { role: "Technician", permissions: JSON.stringify({ pages: [21] }) };
      currentSector = "teknik_servis";
      renderNav();
      results.push({ sector: currentSector, serviceParentVisible: serviceParentVisible() });
      currentAuthUser = oldUser;
      currentSector = "${auditSector}";
      renderNav();
      return results;
    })()`);
    if (permissionAudit.some(item => item.allowed?.some(allowed => !allowed) || item.denied?.some(denied => denied) || item.serviceParentVisible !== (item.sector !== "teknik_servis" || item.allowed !== undefined))) throw new Error(`Role-based sidebar filtering failed: ${JSON.stringify(permissionAudit)}`);
    if (runtimeExceptions.length) throw new Error(`Sidebar audit reported browser exceptions: ${JSON.stringify(runtimeExceptions)}`);
    process.stdout.write(`${JSON.stringify({ ...state, sidebarRouteAudit, menuCustomizationAudit, permissionAudit, runtimeExceptions, screenshot: filename })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
