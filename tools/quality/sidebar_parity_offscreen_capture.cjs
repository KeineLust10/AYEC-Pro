const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `sidebar-parity-headless-profile-${process.pid}`);
const auditSector = process.env.AYEC_AUDIT_SECTOR === "otomotiv" ? "otomotiv" : "teknik_servis";
const auditLogin = { identifier: process.env.AYEC_AUDIT_LOGIN_USER || "", password: process.env.AYEC_AUDIT_LOGIN_PASSWORD || "", tenantId: process.env.AYEC_AUDIT_LOGIN_TENANT || "" };
const collapsedVisual = process.env.AYEC_AUDIT_COLLAPSED === "1";
const captureFullShell = process.env.AYEC_AUDIT_FULL_SHELL === "1";
const viewportWidth = Number(process.env.AYEC_AUDIT_WIDTH || 1280);
const viewportHeight = Number(process.env.AYEC_AUDIT_HEIGHT || 650);
const captureTop = Number(process.env.AYEC_AUDIT_TOP || 0);
const captureHeight = Number(process.env.AYEC_AUDIT_CAPTURE_HEIGHT || viewportHeight);
const outputSuffix = process.env.AYEC_AUDIT_OUTPUT_SUFFIX || "";
const unselectedNavigation = process.env.AYEC_AUDIT_UNSELECTED === "1";

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
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-cache", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`, `--window-size=1280,${viewportHeight}`, baseUrl], { stdio: "ignore", windowsHide: true });
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
    await send("Emulation.setDeviceMetricsOverride", { width: viewportWidth, height: viewportHeight, deviceScaleFactor: 1, mobile: false });
    await send("Page.navigate", { url: baseUrl });
    for (let attempt = 0; attempt < 50; attempt += 1) {
      if (await evaluate(`document.readyState === "complete" && location.origin === ${JSON.stringify(new URL(baseUrl).origin)}`)) break;
      await delay(100);
    }
    let loginAudit = null;
    if (auditLogin.identifier) {
      loginAudit = await evaluate(`(async () => { const response = await fetch(${JSON.stringify(new URL("/api/auth/login", baseUrl).toString())}, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ identifier: ${JSON.stringify(auditLogin.identifier)}, password: ${JSON.stringify(auditLogin.password)}, tenant_id: ${JSON.stringify(auditLogin.tenantId)} }) }); const body = await response.json().catch(() => ({})); return { status: response.status, ok: body.ok === true }; })()`);
      if (!loginAudit.ok) throw new Error(`Offscreen audit login failed: ${JSON.stringify(loginAudit)}`);
      await send("Page.reload", { ignoreCache: true });
      await delay(250);
    }
    let appReady = false;
    for (let attempt = 0; attempt < 80; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && document.querySelector('.app-shell') && document.querySelector('#nav') && document.querySelector('#authRoot')?.innerHTML.trim() && typeof renderNav === 'function' && typeof window.ayecOpenGlobalSearch === 'function' && String(renderNav).includes('OTOMOTIV MODU')")) { appReady = true; break; }
      await delay(200);
    }
    if (!appReady) throw new Error(`The parity menu runtime did not initialize: ${JSON.stringify(runtimeExceptions)}`);
    const state = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const originalBadgeData = { devices: db.devices, customers: db.customers, appointments: db.appointments };
      db.devices = Array.from({ length: 8 }, (_, index) => ({ id: index + 1, status: "Bekliyor", is_deleted: 0, is_archived: 0 }));
      db.devices.push({ id: 9, status: "Teslim Edildi", is_deleted: 0, is_archived: 0 }, { id: 10, status: "Bekliyor", is_deleted: 1, is_archived: 0 }, { id: 11, status: "Tamamland\u0131", is_deleted: 0, is_archived: 0 }, { id: 12, status: "Haz\u0131r", is_deleted: 0, is_archived: 0 }, { id: 13, status: "Teslime Hazir", is_deleted: 0, is_archived: 0 });
      db.appointments = [{ date: ayecLocalDateKey(new Date()), status: "Planland\u0131" }, { date: ayecLocalDateKey(new Date()), status: "Tamamland\u0131" }, { date: ayecLocalDateKey(new Date()), status: "\u0130ptal" }];
      db.customers = [{ is_deleted: 0, is_partner: 0, type: "Bireysel" }, { is_deleted: 0, is_partner: 0, type: "Kurumsal" }, { is_deleted: 0, is_partner: 1, type: "Bayi" }];
      currentSector = ${JSON.stringify(auditSector)};
      renderNav();
      const badgeTestCounts = Object.fromEntries(["services", "service-status", "appointments", "customers"].map(id => [id, Array.from(document.querySelectorAll("#nav [data-page]")).find(button => button.dataset.page === id)?.querySelector(".nav-count-badge")?.textContent || ""]));
      db.devices = db.devices.slice(0, 10);
      db.appointments = [];
      db.customers = [];
      renderNav();
      const shell = document.querySelector(".app-shell");
      shell?.classList.remove("sidebar-collapsed", "sidebar-peek");
      if (${collapsedVisual}) shell?.classList.add("sidebar-collapsed");
      const sidebar = document.querySelector(".sidebar");
      if (sidebar) sidebar.style.transform = "none";
      const nav = document.querySelector("#nav");
      nav?.querySelectorAll(".nav-parent.open").forEach(button => button.classList.remove("open"));
      nav?.querySelectorAll(".submenu.open").forEach(submenu => submenu.classList.remove("open"));
      const bounds = element => { const box = element?.getBoundingClientRect(); return box ? { x: Math.round(box.x), y: Math.round(box.y), width: Math.round(box.width), height: Math.round(box.height) } : null; };
      const topText = Array.from(document.querySelectorAll("body *")).filter(element => element.children.length === 0 && element.textContent.trim()).map(element => ({ text: element.textContent.trim().slice(0, 32), rect: bounds(element) })).filter(item => item.rect?.height && item.rect.y < 70 && item.rect.x < (sidebar?.getBoundingClientRect().width || 0));
      const navBadges = Object.fromEntries(["services", "service-status", "appointments", "customers"].map(id => [id, Array.from(nav?.querySelectorAll("[data-page]") || []).find(button => button.dataset.page === id)?.querySelector(".nav-count-badge")?.textContent || ""]));
      const navButtons = Array.from(nav?.querySelectorAll(".nav-button") || []);
      const parentButton = nav?.querySelector(".nav-parent");
      const childButton = nav?.querySelector(".submenu .nav-button");
      const brand = sidebar?.querySelector(".brand");
      const sectorBadge = document.querySelector("#sectorBrand");
      const brandStyle = brand ? getComputedStyle(brand) : null;
      const parentSubmenu = parentButton ? document.getElementById(parentButton.dataset.parent) : null;
      const sidebarStyle = sidebar ? getComputedStyle(sidebar) : null;
      const brandMark = sidebar?.querySelector(".brand-mark");
      const bottom = sidebar?.querySelector(".sidebar-bottom");
      return { badgeTestCounts, navPageIds: Array.from(nav?.querySelectorAll("[data-page]") || [], button => button.dataset.page), navBadges, navItems: navButtons.length, groups: nav?.querySelectorAll(".nav-group-title").length || 0, sidebarWidth: Math.round(sidebar?.getBoundingClientRect().width || 0), sidebarBackground: sidebarStyle?.backgroundImage || null, sidebarBackgroundColor: sidebarStyle?.backgroundColor || null, shell: bounds(shell), sidebar: bounds(sidebar), brand: bounds(brand), brandStyle: brandStyle ? { height: brandStyle.height, padding: brandStyle.padding, margin: brandStyle.margin, boxSizing: brandStyle.boxSizing } : null, brandMark: bounds(brandMark), sidebarBottom: bounds(bottom), sidebarBottomStyle: bottom ? { height: getComputedStyle(bottom).height, paddingTop: getComputedStyle(bottom).paddingTop, paddingBottom: getComputedStyle(bottom).paddingBottom, borderTopWidth: getComputedStyle(bottom).borderTopWidth } : null, footerChildren: Array.from(bottom?.children || [], element => ({ className: element.className, text: element.textContent.trim().slice(0, 48), bounds: bounds(element), parts: Array.from(element.querySelectorAll("*"), child => { const style = getComputedStyle(child); return { className: child.className, text: child.textContent.trim().slice(0, 28), bounds: bounds(child), color: style.color, background: style.backgroundColor, border: style.borderColor, font: style.font, padding: style.padding }; }) })), sidebarBottomDisplay: bottom ? getComputedStyle(bottom).display : null, navDisplay: nav ? getComputedStyle(nav).display : null, brandMarkStyle: brandMark ? { background: getComputedStyle(brandMark).backgroundColor, borderColor: getComputedStyle(brandMark).borderColor } : null, sectorBadge: sectorBadge ? { text: sectorBadge.textContent, className: sectorBadge.className, title: sectorBadge.title } : null, runtime: { menuModel: typeof ayecSectorMenu, navSource: String(renderNav).slice(0, 90) }, nav: bounds(nav), navTypography: { parent: parentButton ? { size: getComputedStyle(parentButton).fontSize, weight: getComputedStyle(parentButton).fontWeight, open: parentButton.classList.contains("open"), height: bounds(parentButton).height, y: bounds(parentButton).y, active: parentButton.classList.contains("active"), background: getComputedStyle(parentButton).backgroundColor, color: getComputedStyle(parentButton).color, parentId: parentButton.dataset.parent, submenuId: parentSubmenu?.id, activeChildren: Array.from(parentSubmenu?.querySelectorAll("[data-page].active") || [], button => button.dataset.page) } : null, child: childButton ? { size: getComputedStyle(childButton).fontSize, height: bounds(childButton).height, y: bounds(childButton).y } : null }, activePages: Array.from(nav?.querySelectorAll("[data-page].active") || [], button => button.dataset.page), topText };
    })()`);
    const headerLayout = await evaluate(`Array.from(document.querySelectorAll(".app-shell > .topbar > *")).map(element => { const box=element.getBoundingClientRect(); const style=getComputedStyle(element); return {tag:element.tagName,id:element.id,className:element.className,x:Math.round(box.x),y:Math.round(box.y),width:Math.round(box.width),display:style.display,visibility:style.visibility,opacity:style.opacity,children:element.classList.contains("top-actions")?Array.from(element.children).map(child=>{const r=child.getBoundingClientRect();const cs=getComputedStyle(child);return{id:child.id,className:child.className,x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),display:cs.display,color:cs.color,visibility:cs.visibility,opacity:cs.opacity};}):undefined}; })`);
    const menuPageIconAudit = await evaluate(`(async () => {
      const originalSector = currentSector;
      const results = {};
      for (const sector of ["teknik_servis", "otomotiv"]) {
        currentSector = sector;
        renderNav();
        const pages = Array.from(document.querySelectorAll("#nav .nav-button[data-page]"));
        const gearParents = [];
        const collectParents = items => items.forEach(item => {
          if (item.children && item.icon === "&#9881;") gearParents.push(item.id);
          collectParents(item.children || []);
        });
        collectParents(ayecSectorMenu(sector).flatMap(group => group.items));
        results[sector] = {
          total: pages.length,
          missingDesktopPageIds: pages.map(button => button.dataset.page).filter(id => !ayecDesktopPageIds[id]),
          missingSvgIcons: pages.filter(button => ayecDesktopPageIds[button.dataset.page] && !button.querySelector(".nav-icon svg")).map(button => button.dataset.page),
          missingGearParentIcons: gearParents.filter(id => { const parent = Array.from(document.querySelectorAll("#nav .nav-parent")).find(button => button.dataset.parent === "nav-" + sector + "-" + id); return !parent?.querySelector(".nav-icon svg"); })
        };
      }
      currentSector = originalSector;
      renderNav();
      return results;
    })()`);
    if (Object.values(menuPageIconAudit).some(item => item.missingSvgIcons.length || item.missingGearParentIcons.length)) throw new Error(`Mapped desktop sidebar pages or menu icons are missing SVG icons: ${JSON.stringify(menuPageIconAudit)}`);
    if (!state.sidebarWidth) throw new Error(`Sidebar is not visible: ${JSON.stringify(state)}`);
    const expectedSidebarWidth = collapsedVisual ? 64 : Math.min(320, Math.max(240, Math.round(viewportWidth * 0.2)));
    if (state.sidebarWidth !== expectedSidebarWidth) throw new Error(`Desktop sidebar width differs from the 20vw desktop rule: ${JSON.stringify({ actual: state.sidebarWidth, expected: expectedSidebarWidth })}`);
    if (collapsedVisual && (state.brand?.height !== 60 || state.brandMark?.width !== 42 || state.brandMark?.height !== 42 || state.sidebarBottomDisplay !== "none" || state.navDisplay !== "none")) throw new Error(`Collapsed sidebar does not match the desktop collapsed header/menu/footer geometry: ${JSON.stringify(state)}`);
    const expectedSidebarBackground = "linear-gradient(rgb(13, 24, 41) 0px, rgb(13, 24, 41) 104px, rgba(0, 0, 0, 0) 104px), linear-gradient(rgb(8, 14, 26) 0%, rgb(8, 14, 26) 28%, rgb(13, 24, 41) 72%, rgb(13, 24, 41) 100%)";
    if (state.sidebarBackground !== expectedSidebarBackground) throw new Error(`Midnight sidebar palette differs from the desktop Koyu Mavi gradient: ${JSON.stringify({ actual: state.sidebarBackground, expected: expectedSidebarBackground })}`);
    if (!state.navTypography.parent?.active || !state.activePages.includes("dashboard")) throw new Error(`Selected dashboard navigation state is not visible: ${JSON.stringify(state.navTypography)}`);
    const expectedSectorBadge = auditSector === "otomotiv" ? "OTOMOTIV MODU" : "ERP";
    const badgeMatches = state.sectorBadge?.text === expectedSectorBadge && (auditSector !== "otomotiv" || state.sectorBadge.className.includes("automotive-sector"));
    if (!collapsedVisual && !badgeMatches) throw new Error(`Expected the ${expectedSectorBadge} sector badge: ${JSON.stringify({ state, runtimeExceptions })}`);
    if (state.brandMarkStyle?.background !== "rgb(30, 48, 77)" || state.brandMarkStyle?.borderColor !== "rgb(27, 42, 66)") throw new Error(`Unexpected dark-blue brand mark palette: ${JSON.stringify(state.brandMarkStyle)}`);
    if (unselectedNavigation) await evaluate(`(() => { page = "__sidebar-capture__"; renderNav(); })()`);
    await delay(400);
    const renderedNavRows = await evaluate(`(() => [...document.querySelectorAll("#nav .nav-button")].map(button => {const r=button.getBoundingClientRect();return{text:button.innerText.trim(),page:button.dataset.page||"",parent:button.dataset.parent||"",className:button.className,fontWeight:getComputedStyle(button).fontWeight,y:Math.round(r.y),height:Math.round(r.height),visible:r.height>0}}).filter(item=>item.visible))()`);
    await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: 400, y: 640 });
    await delay(80);
    const screenshot = await send("Page.captureScreenshot", captureFullShell
      ? { format: "png", captureBeyondViewport: true }
      : { format: "png", captureBeyondViewport: true, clip: { x: 0, y: captureTop, width: state.sidebarWidth, height: captureHeight, scale: 1 } });
    const filename = path.join(outputDir, captureFullShell
      ? `web-shell-${auditSector}-${viewportHeight}${outputSuffix}-headless.png`
      : `web-sidebar-${auditSector}-${collapsedVisual ? "collapsed" : "current"}${outputSuffix}-headless.png`);
    fs.writeFileSync(filename, Buffer.from(screenshot.data, "base64"));
    if (process.env.AYEC_AUDIT_CAPTURE_ONLY === "1") {
      const expectedBadgeCounts = auditSector === "otomotiv" ? { services: "", "service-status": "9", appointments: "1", customers: "2" } : { services: "9", "service-status": "9", appointments: "1", customers: "2" };
      if (JSON.stringify(state.badgeTestCounts) !== JSON.stringify(expectedBadgeCounts)) throw new Error(`Sidebar count badge parity failed: ${JSON.stringify({ counts: state.badgeTestCounts, pages: state.navPageIds })}`);
      if (!collapsedVisual) {
        const pageRows = renderedNavRows.filter(item => item.page);
        const serviceParent = renderedNavRows.find(item => item.parent === (auditSector === "otomotiv" ? "nav-otomotiv-automotive-service-parent" : "nav-teknik_servis-service-parent"));
        if (!pageRows.length || pageRows.some(item => item.height !== 42) || serviceParent?.height !== 38) throw new Error(`Sidebar row geometry differs from desktop: ${JSON.stringify({ pageRows: pageRows.map(item => [item.page, item.height]), serviceParent })}`);
      }
      if (runtimeExceptions.length) throw new Error(`Sidebar capture reported browser exceptions: ${JSON.stringify(runtimeExceptions)}`);
      process.stdout.write(`${JSON.stringify({ ...state, renderedNavRows, runtimeExceptions, screenshot: filename })}\n`);
      return;
    }
    const sidebarRouteAudit = await evaluate(`(async () => {
      window.handleUnauthorized = () => {};
      const originalRender = render;
      render = () => { originalRender(); };
      const originalFetch = window.fetch;
      window.fetch = async (...args) => {
        const requestUrl = new URL(typeof args[0] === "string" ? args[0] : args[0]?.url || "", location.href);
        if (requestUrl.origin === location.origin && requestUrl.pathname.startsWith("/api/")) return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
        return originalFetch(...args);
      };
      const originalHydrate = hydrateDesktop;
      hydrateDesktop = async () => ({});
      await hydrateDesktop(true);
      const originalSector = currentSector;
      const results = [];
      for (const sector of ["teknik_servis", "otomotiv"]) {
        currentSector = sector;
        page = "dashboard";
        renderNav();
        const ids = [...new Set(Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]"), button => button.dataset.page))];
        for (const id of ids) {
          let button = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item => item.dataset.page === id);
          let submenu = button?.closest(".submenu");
          if (submenu && !submenu.classList.contains("open")) {
            const parent = Array.from(document.querySelectorAll("#nav .nav-parent")).find(item => item.dataset.parent === submenu.id);
            parent?.click();
          }
          button = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page]")).find(item => item.dataset.page === id);
          const expectedTitle = (button?.querySelector(".nav-label")?.textContent || button?.children[1]?.textContent || "").trim();
          const settingsSectionBefore = settingsSection;
          button?.click();
          await new Promise(resolve => setTimeout(resolve, 5));
          submenu = button?.closest(".submenu");
          const active = Array.from(document.querySelectorAll(".sidebar .nav-button[data-page].active"), item => item.dataset.page);
          const parentButton = submenu ? Array.from(document.querySelectorAll("#nav .nav-parent")).find(item => item.dataset.parent === submenu.id) : null;
          const contentText = document.querySelector("#content")?.textContent.trim() || "";
          const contentRendered = contentText.length >= 20;
          const title = document.querySelector("#pageTitle")?.textContent.trim() || "";
          const titleMatches = title === expectedTitle || id === "pc-builder" && title === "PC Yap\u0131land\u0131r\u0131c\u0131" || id === "settings" && title === "Firma Ayarlar\u0131";
          results.push({ sector, id, page, active: active.includes(id), parentActive: !parentButton || parentButton.classList.contains("active"), settingsSectionStable: id !== "backup" || settingsSection === settingsSectionBefore, contentRendered, contentLength: contentText.length, titleMatches, expectedTitle, title, contentPreview: contentRendered ? undefined : contentText.slice(0, 100) });
        }
        const mainPageTargets = [...new Set(Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]"), button => button.dataset.mainPage).filter(Boolean))].filter(id => !ids.includes(id));
        for (const id of mainPageTargets) {
          const button = Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]")).find(item => item.dataset.mainPage === id);
          button?.click();
          await new Promise(resolve => setTimeout(resolve, 5));
          const activeParent = Array.from(document.querySelectorAll("#nav .nav-parent[data-main-page]")).find(item => item.dataset.mainPage === id);
          const contentText = document.querySelector("#content")?.textContent.trim() || "";
          results.push({ sector, id, page, active: page === id, parentActive: Boolean(activeParent?.classList.contains("active")), contentRendered: contentText.length >= 20, contentLength: contentText.length, contentPreview: contentText.length >= 20 ? undefined : contentText.slice(0, 100) });
        }
      }
      currentSector = originalSector;
      hydrateDesktop = originalHydrate;
      renderNav();
      render = originalRender;
      navigate("dashboard");
      const failures = results.filter(item => item.page !== item.id || !item.active || !item.parentActive || !item.contentRendered || item.settingsSectionStable === false);
      return { tested: results.length, failures, titleMismatches: results.filter(item => item.expectedTitle && !item.titleMatches).map(({ sector, id, expectedTitle, title }) => ({ sector, id, expectedTitle, title })), duplicates: results.filter((item, index) => results.some((other, otherIndex) => otherIndex !== index && other.sector === item.sector && other.id === item.id)).map(item => ({ sector: item.sector, id: item.id })), sectors: Object.fromEntries(["teknik_servis", "otomotiv"].map(sector => [sector, results.filter(item => item.sector === sector).map(item => item.id)])), auditRendererType: typeof renderAuditReference, auditScriptLoaded: Array.from(document.scripts).some(script => script.src.includes("audit-reference.js")) };
    })()`);
    const appBindings = await evaluate("({ render: typeof render, windowRender: typeof window.render, renderBackupPage: typeof renderBackupPage, genericShell: typeof genericShell, contextAction: typeof contextAction, settingsGroups: typeof settingsGroups })");
    if (sidebarRouteAudit.failures.length || sidebarRouteAudit.duplicates.length || runtimeExceptions.length) throw new Error(`Sidebar audit reported route failures, duplicate entries, or browser exceptions: ${JSON.stringify({ sidebarRouteAudit, appBindings, runtimeExceptions })}`);
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
    const searchRouteAudit = await evaluate(`(() => {
      const originalSector = currentSector;
      const originalLabels = desktopInternalSettings.web_menu_labels;
      const expectedRoutes = { teknik_servis: "service-list", otomotiv: "automotive-stock" };
      const results = [];
      for (const sector of Object.keys(expectedRoutes)) {
        currentSector = sector;
        const route = expectedRoutes[sector];
        const customLabel = "Audit " + route;
        desktopInternalSettings.web_menu_labels = JSON.stringify({ [sector]: { [route]: customLabel } });
        renderNav();
        const button = Array.from(document.querySelectorAll("#nav [data-page]")).find(item => item.dataset.page === route);
        const label = (button?.querySelector(".nav-label")?.textContent || button?.querySelector("span:last-child")?.textContent || button?.textContent || "").trim();
        if (!route || !label) { results.push({ sector, route, label, rendered: false }); continue; }
        window.ayecOpenGlobalSearch();
        const input = document.querySelector("#globalSearch");
        input.value = label;
        input.dispatchEvent(new Event("input", { bubbles: true }));
        const result = Array.from(document.querySelectorAll(".global-search-result")).find(item => item.dataset.searchRoute === route);
        const rendered = result?.querySelector("strong")?.textContent === label;
        const activation = sector === "teknik_servis" ? "keyboard" : "mouse";
        if (activation === "keyboard") {
          input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
          input.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
        } else {
          result?.click();
        }
        const activeRoute = Array.from(document.querySelectorAll("#nav .nav-button.active[data-page]"), item => item.dataset.page).includes(route);
        const contentText = document.querySelector("#content")?.textContent.trim() || "";
        results.push({ sector, route, label, customLabel, activation, rendered: label === customLabel && rendered, navigated: page === route && activeRoute, contentRendered: contentText.length >= 20, closed: !document.querySelector("#globalSearchDialog")?.open, restored: Boolean(document.querySelector(".top-actions > .global-search-wrap")) });
      }
      currentSector = originalSector;
      desktopInternalSettings.web_menu_labels = originalLabels;
      renderNav();
      return results;
    })()`);
    if (searchRouteAudit.some(item => !item.rendered || !item.navigated || !item.contentRendered || !item.closed || !item.restored)) throw new Error(`Global search did not render both sector destinations: ${JSON.stringify(searchRouteAudit)}`);
    await delay(180);
    if (runtimeExceptions.length) throw new Error(`Sidebar audit reported browser exceptions: ${JSON.stringify(runtimeExceptions)}`);
    process.stdout.write(`${JSON.stringify({ ...state, loginAudit, headerLayout, sidebarRouteAudit, menuCustomizationAudit, permissionAudit, menuPageIconAudit, searchRouteAudit, runtimeExceptions, screenshot: filename })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    await delay(300);
    fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
