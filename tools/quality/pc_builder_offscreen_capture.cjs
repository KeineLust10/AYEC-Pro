const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const port = Number(process.env.AYEC_PC_BUILDER_CDP_PORT || 9346);
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-pc-builder-edge-"));
const profile = path.join(tempRoot, "profile");

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, "--window-size=1300,850", baseUrl], { stdio: "ignore", windowsHide: true });
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
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a PC Builder page.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text || "Runtime exception");
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
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    let ready = false;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof apiFetch === 'function'");
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Web application did not finish loading.");
    await evaluate(`(async () => {
      await new Promise(resolve => setTimeout(resolve, 300));
      for (let attempt = 0; attempt < 80; attempt += 1) {
        if (document.querySelector('#authRoot')?.innerHTML.trim() || setupRequired || currentAuthUser) break;
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      document.querySelector('#appShell')?.removeAttribute('inert');
      document.querySelector('#appShell')?.removeAttribute('aria-hidden');
      db.settings.default_vat_percent = 20;
      db.customers = [{ id: 71, name: 'QA Customer', phone: '5551234567', balances: { TRY: 0, USD: 0, EUR: 0 }, services: [], quotes: [] }, { id: 72, name: 'Beta Customer', phone: '5559876543', balances: { TRY: 0, USD: 0, EUR: 0 }, services: [], quotes: [] }];
      const parts = [
        { id: 501, name: 'Audit B550 Board', category: 'Anakart', brand: 'Audit', description: 'AM4 B550', stock: 4, price: 12000 },
        { id: 502, name: 'Audit Ryzen CPU', category: '\u0130\u015flemci', brand: 'Audit', description: 'AM4 8 core', stock: 3, price: 14000 },
        { id: 503, name: 'Audit DDR5 Memory', category: 'RAM', brand: 'Audit', description: '32 GB', stock: 8, price: 4000 },
        { id: 504, name: 'GSkill Fury DDR5', category: 'RAM', brand: 'G.Skill', description: '32 GB', stock: 2, price: 5000 }
      ];
      window.__pcBuilderWrites = [];
      apiFetch = async (endpoint, options = {}) => {
        if (endpoint.includes('/parts')) return { rows: window.__pcBuilderEmptyCapture ? [] : parts };
        if (endpoint.includes('/customers')) return { rows: db.customers };
        const body = options.body ? JSON.parse(options.body) : {};
        window.__pcBuilderWrites.push({ endpoint, body });
        if (endpoint.includes('/pc-builder/deduct-stock')) {
          const items = body.items.map(item => {
            const part = parts.find(entry => String(entry.id) === String(item.part_id));
            if (part) part.stock = Math.max(0, Number(part.stock) - Number(item.quantity));
            return { part_id: item.part_id, quantity: item.quantity, stock: part?.stock ?? 0 };
          });
          return { ok: true, items };
        }
        return { ok: true, id: window.__pcBuilderWrites.length };
      };
      window.__pcBuilderEmptyCapture = true;
      navigate('pc-builder');
      document.querySelector('#toastRoot')?.replaceChildren();
      return true;
    })()`);
    let state;
    for (let attempt = 0; attempt < 60; attempt += 1) {
      state = await evaluate(`(() => {
        const rect = selector => { const node = document.querySelector(selector); if (!node) return null; const r = node.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; };
        const content = document.querySelector('#content');
        const paint = selector => { const node = document.querySelector(selector); if (!node) return null; const style = getComputedStyle(node); return { background: style.backgroundColor, color: style.color, border: style.borderColor }; };
        const fontSize = selector => { const node = document.querySelector(selector); return node ? getComputedStyle(node).fontSize : null; };
        const pageNode = document.querySelector('.pc-builder-page'); const pageStyle = pageNode ? getComputedStyle(pageNode) : null;
        const summary = document.querySelector('.pc-summary');
        const summaryItems = summary ? [...summary.children].map(node => ({ bounds: rectNode(node), display: getComputedStyle(node).display, text: node.innerText.slice(0, 50), children: [...node.children].map(child => { const style = getComputedStyle(child); return { bounds: rectNode(child), height: style.height, boxSizing: style.boxSizing, lineHeight: style.lineHeight }; }) })) : [];
        function rectNode(node) { const r = node.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }
        const contentBounds = content?.getBoundingClientRect();
        const contentRight = contentBounds ? contentBounds.right : 0;
        const mainChildren = ['.pc-builder-header','.pc-customer-bar','.pc-preset-bar','.pc-component-head','.pc-components','.pc-summary','.pc-actions'].map(selector => document.querySelector(selector)).filter(Boolean);
        const childrenWithinContent = mainChildren.every(node => node.getBoundingClientRect().right <= contentRight + 1);
        const summaryNode = summary?.getBoundingClientRect();
        const summaryFits = Boolean(summaryNode) && summaryItems.every(item => item.bounds[0] >= summaryNode.left && item.bounds[0] + item.bounds[2] <= summaryNode.right + 1 && item.bounds[1] >= summaryNode.top && item.bounds[1] + item.bounds[3] <= summaryNode.bottom + 1 && item.children.every(child => child.bounds[0] >= summaryNode.left && child.bounds[0] + child.bounds[2] <= summaryNode.right + 1 && child.bounds[1] >= summaryNode.top && child.bounds[1] + child.bounds[3] <= summaryNode.bottom + 1));
        return { page: document.body.dataset.page, pageTitle: document.querySelector("#pageTitle")?.textContent || "", theme: document.documentElement.dataset.theme || '', rows: document.querySelectorAll('#pcComponents .pc-component-row').length, customerOptions: document.querySelectorAll('#pcCustomer option').length, customerPlaceholder: document.querySelector('#pcCustomer option[value=""]')?.textContent?.trim() || "", heading: document.querySelector('.pc-builder-header h2')?.textContent || '', titleLayout: (() => { const heading=document.querySelector('.pc-builder-header h2'), icon=heading?.querySelector('.pc-builder-title-icon'), textNode=Array.from(heading?.childNodes || []).find(node=>node.nodeType===Node.TEXT_NODE), range=document.createRange(); if(textNode){range.setStart(textNode,0);range.setEnd(textNode,1)} const rect=node=>{const value=node?.getBoundingClientRect();return value?[Math.round(value.x*100)/100,Math.round(value.y*100)/100,Math.round(value.width*100)/100,Math.round(value.height*100)/100]:null}; return {heading:rect(heading),icon:rect(icon),text:range.getBoundingClientRect().toJSON(),iconFlex:getComputedStyle(icon).flex,iconBasis:getComputedStyle(icon).flexBasis,gap:getComputedStyle(heading).gap}; })(), documentWidth: document.documentElement.scrollWidth, contentWidth: content?.clientWidth || 0, contentScrollWidth: content?.scrollWidth || 0, childrenWithinContent, summaryFits, contentHeight: content?.clientHeight || 0, contentScrollHeight: content?.scrollHeight || 0, pageBounds: rect('.pc-builder-page'), pageStyle: pageStyle ? { width: pageStyle.width, maxWidth: pageStyle.maxWidth, boxSizing: pageStyle.boxSizing, left: pageStyle.left, top: pageStyle.top } : null, content: rect('#content'), workflowTabs: rect('.sales-workflow-tabs'), workflowTabButtons: [...document.querySelectorAll('.sales-workflow-tabs [data-sales-workflow]')].map(node => rectNode(node)), header: rect('.pc-builder-header'), customer: rect('.pc-customer-bar'), presets: rect('.pc-preset-bar'), columnHead: rect('.pc-component-head'), componentHost: rect('.pc-components'), firstRow: rect('.pc-component-row'), lastRow: rect('.pc-component-row:last-child'), summary: rect('.pc-summary'), summaryItems, actions: rect('.pc-actions'), componentHeadColumns: Array.from(document.querySelector('.pc-component-head')?.children || [], node => Math.round(node.getBoundingClientRect().width)), componentRowColumns: Array.from(document.querySelector('.pc-component-row')?.children || [], node => Math.round(node.getBoundingClientRect().width)), componentHeadAlignItems: getComputedStyle(document.querySelector('.pc-component-head')).alignItems, componentHeadAlignments: Array.from(document.querySelector('.pc-component-head').children, node => getComputedStyle(node).textAlign), palette: { header: paint('.pc-builder-header'), input: paint('#pcCustomerSearch'), columnHead: paint('.pc-component-head'), product: paint('.pc-component-row select[data-pc-product]') }, presetButton: { font: fontSize('.pc-preset-bar button'), weight: getComputedStyle(document.querySelector('.pc-preset-bar button')).fontWeight }, presetBarRadius: getComputedStyle(document.querySelector('.pc-preset-bar')).borderRadius, presetLabelFont: fontSize('.pc-preset-bar>span'), actionOrder: [...document.querySelectorAll('.pc-actions [data-pc-action]')].map(button => button.dataset.pcAction), customerBarActionCount: document.querySelectorAll('.pc-customer-bar [data-pc-action]').length, fonts: { title: fontSize('.pc-builder-header h2'), subtitle: fontSize('.pc-builder-header p'), columnHead: fontSize('.pc-component-head'), rowName: fontSize('.pc-component-name'), rowTotal: fontSize('.pc-row-total') }, total: document.querySelector('#pcGrand')?.textContent || '' };
      })()`);
      if (state.rows === 15) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    const desktopGeometry = { customer: [280, 202, 1214, 44], presets: [280, 258, 1214, 44], columnHead: [280, 314, 1219, 32], componentHost: [280, 360, 1219, 892], firstRow: [280, 360, 1219, 52], lastRow: [280, 1200, 1219, 52], summary: [280, 1264, 1214, 168], actions: [280, 1444, 1214, 58] };
    if (state.page !== "pc-builder" || state.pageTitle !== "PC Yap\u0131land\u0131r\u0131c\u0131" || state.rows !== 15 || state.customerOptions !== 3 || state.customerPlaceholder !== "\u2014 M\u00fc\u015fteri Se\u00e7 \u2014" || !state.heading.includes("Bilgisayar Topla") || state.documentWidth !== 1300 || state.contentScrollWidth <= state.contentWidth || !state.summaryFits || JSON.stringify(state.componentHeadColumns) !== JSON.stringify([160,150,135,327,56,110,105,55,28]) || JSON.stringify(state.componentRowColumns) !== JSON.stringify([160,150,135,231,112,148,105,55,28]) || state.componentHeadAlignItems !== "center" || JSON.stringify(state.componentHeadAlignments) !== JSON.stringify(["left","left","left","left","center","right","right","center","center"]) || JSON.stringify(state.header) !== JSON.stringify([260, 104, 1025, 82]) || state.workflowTabs?.[0] !== 260 || state.workflowTabs?.[1] !== 70 || state.workflowTabs?.[3] !== 34 || JSON.stringify(state.workflowTabButtons) !== JSON.stringify([[260,70,178,34],[439,70,139,34],[579,70,139,34]]) || Object.entries(desktopGeometry).some(([key, bounds]) => JSON.stringify(state[key]) !== JSON.stringify(bounds)) || state.summaryItems.length !== 7 || state.palette.header.background !== "rgb(13, 24, 41)" || state.palette.columnHead.background !== "rgb(16, 26, 43)" || state.palette.input.background !== "rgb(8, 14, 26)" || state.palette.header.color !== "rgb(226, 232, 240)" || state.presetButton.font !== "11px" || state.presetButton.weight !== "400" || state.presetBarRadius !== "10px" || state.presetLabelFont !== "12px" || JSON.stringify(state.actionOrder) !== JSON.stringify(["pdf", "customer", "stock", "finance", "save", "clear"]) || state.customerBarActionCount !== 0 || state.fonts.title !== "26.67px" || state.fonts.subtitle !== "13.33px" || state.fonts.columnHead !== "12px" || state.fonts.rowName !== "12px") throw new Error("PC Builder desktop fixture, responsive geometry, Koyu Mavi palette, or typography mismatch: " + JSON.stringify(state));
    const rowTotalColor = await evaluate("getComputedStyle(document.querySelector('.pc-row-total')).color");
    if (rowTotalColor !== "rgb(37, 99, 235)") throw new Error(`PC Builder line total color differs from the desktop accent: ${rowTotalColor}`);
    const removeButton = await evaluate(`(() => { const node=document.querySelector('.pc-remove'); const style=getComputedStyle(node); const rect=node.getBoundingClientRect(); return {width:rect.width,height:rect.height,background:style.backgroundColor,border:style.borderWidth,radius:style.borderRadius,fontSize:style.fontSize}; })()`);
    if (JSON.stringify(removeButton) !== JSON.stringify({width:28,height:28,background:"rgba(0, 0, 0, 0)",border:"0px",radius:"6px",fontSize:"13px"})) throw new Error("PC Builder remove control differs from the native toolbutton: " + JSON.stringify(removeButton));
    const responsiveWidths = [];
    for (const width of [1201, 1280, 1350, 1440, 1597, 1598]) {
      await send("Emulation.setDeviceMetricsOverride", { width, height: 850, deviceScaleFactor: 1, mobile: false });
      await new Promise(resolve => setTimeout(resolve, 100));
      const probe = await evaluate(`(() => {
        const content = document.querySelector('#content');
        const contentBounds = content.getBoundingClientRect();
        const selectors = ['.pc-builder-header','.pc-customer-bar','.pc-preset-bar','.pc-table-scroll','.pc-summary','.pc-actions'];
        const sections = selectors.map(selector => { const node = document.querySelector(selector); const bounds = node.getBoundingClientRect(); return { selector, right: Math.round(bounds.right), bottom: Math.round(bounds.bottom) }; });
        const tableScrollNode = document.querySelector('.pc-table-scroll');
        const tableScroll = { clientWidth: tableScrollNode.clientWidth, scrollWidth: tableScrollNode.scrollWidth };
        const summary = document.querySelector('.pc-summary').getBoundingClientRect();
        const summaryChildren = [...document.querySelector('.pc-summary').children].map(node => { const bounds = node.getBoundingClientRect(); return { right: Math.round(bounds.right), bottom: Math.round(bounds.bottom) }; });
        const offerBadge = document.querySelector('.pc-offer-meta strong').getBoundingClientRect();
        const offerDate = document.querySelector('.pc-offer-meta span').getBoundingClientRect();
        return { width: innerWidth, contentWidth: content.clientWidth, contentScrollWidth: content.scrollWidth, contentRight: Math.round(contentBounds.right), sections, tableScroll, summaryRight: Math.round(summary.right), summaryBottom: Math.round(summary.bottom), summaryChildren, offerBadge: [Math.round(offerBadge.x), Math.round(offerBadge.y), Math.round(offerBadge.width), Math.round(offerBadge.height), Math.round(offerBadge.right)], offerDateRight: Math.round(offerDate.right) };
      })()`);
      const expectsHorizontalScroll = width <= 1350;
      const hasHorizontalScroll = probe.contentScrollWidth > probe.contentWidth;
      const scrollModeMatches = expectsHorizontalScroll ? hasHorizontalScroll : !hasHorizontalScroll;
      const maxReachableRight = probe.contentRight + (hasHorizontalScroll ? probe.contentScrollWidth - probe.contentWidth : 0);
      const sectionsFit = probe.sections.every(section => section.right <= maxReachableRight + 1);
      const tableScrollMatches = expectsHorizontalScroll ? probe.tableScroll.scrollWidth > probe.tableScroll.clientWidth : probe.tableScroll.scrollWidth <= probe.tableScroll.clientWidth;
      const fitsContent = scrollModeMatches && sectionsFit && tableScrollMatches;
      const fitsSummary = probe.summaryChildren.every(child => child.right <= probe.summaryRight + 1 && child.bottom <= probe.summaryBottom + 1);
      const offerMetadataFits = probe.offerBadge[2] === 136 && probe.offerBadge[3] === 32 && probe.offerBadge[4] <= maxReachableRight + 1 && probe.offerDateRight <= maxReachableRight + 1;
      responsiveWidths.push({ width, contentWidth: probe.contentWidth, contentScrollWidth: probe.contentScrollWidth, tableScroll: probe.tableScroll, expectsHorizontalScroll, fitsContent, fitsSummary, offerMetadataFits, offerBadge: probe.offerBadge, offerDateRight: probe.offerDateRight });
      if (!fitsContent || !fitsSummary || !offerMetadataFits) throw new Error(`PC Builder overflows at ${width}px: ${JSON.stringify({ ...responsiveWidths.at(-1), contentRight: probe.contentRight, sections: probe.sections })}`);
    }
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 150));
    const formFactorSelect = await evaluate(`(() => { const element = document.querySelector('#pcComponents .pc-component-row select[data-pc-spec]'); if (!element) return null; const style = getComputedStyle(element); const rect = element.getBoundingClientRect(); return { rect: [Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height)], fontSize: style.fontSize, fontFamily: style.fontFamily, productFontFamily: getComputedStyle(document.querySelector("#pcComponents .pc-component-row select[data-pc-product]")).fontFamily, borderRadius: style.borderRadius, padding: style.padding, backgroundImage: style.backgroundImage, backgroundPosition: style.backgroundPosition, backgroundSize: style.backgroundSize }; })()`);
    if (!formFactorSelect || Math.abs(formFactorSelect.rect[0] - 620) > 1 || formFactorSelect.rect[1] !== 369 || formFactorSelect.rect[2] !== 135 || formFactorSelect.rect[3] !== 34 || formFactorSelect.fontSize !== "12px" || !formFactorSelect.fontFamily.startsWith("\"Segoe UI\"") || !formFactorSelect.productFontFamily.startsWith("\"Segoe UI\"") || formFactorSelect.borderRadius !== "8px" || !formFactorSelect.backgroundImage.includes("linear-gradient") || formFactorSelect.backgroundSize !== "auto") throw new Error("PC Builder form-factor select no longer matches the native control: " + JSON.stringify(formFactorSelect));
    const priceStepper = await evaluate(`(() => { const element = document.querySelector('#pcComponents .pc-component-row .pc-inline-stepper[data-pc-stepper="price"]'); if (!element) return null; const rect = node => { const r = node.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; }; return { rect: rect(element), parts: [...element.children].map(node => ({ rect: rect(node), kind: node.tagName === "BUTTON" ? "button" : node.dataset.pcPrice !== undefined ? "input" : "suffix", borderRadius: getComputedStyle(node).borderRadius, fontSize: getComputedStyle(node).fontSize, height: getComputedStyle(node).height, minHeight: getComputedStyle(node).minHeight })) }; })()`);
    if (!priceStepper || priceStepper.rect[0] !== 1113 || priceStepper.rect[1] !== 368 || priceStepper.rect[2] !== 148 || priceStepper.rect[3] !== 34 || priceStepper.parts.length !== 4 || priceStepper.parts[0].rect[2] !== 24 || priceStepper.parts[0].rect[3] !== 24 || priceStepper.parts[0].borderRadius !== "12px" || priceStepper.parts[1].rect[2] !== 62 || priceStepper.parts[1].rect[3] !== 28 || priceStepper.parts[3].rect[2] !== 24 || priceStepper.parts[3].rect[3] !== 24) throw new Error("PC Builder price stepper no longer matches the native inline control: " + JSON.stringify(priceStepper));
    const compactHeaderSearch = await evaluate(`(() => { const r = document.querySelector('.global-search-wrap').getBoundingClientRect(); return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]; })()`);
    if (JSON.stringify(compactHeaderSearch) !== JSON.stringify([304,15,150,40])) throw new Error("PC Builder header search no longer matches native compact desktop geometry: " + JSON.stringify(compactHeaderSearch));
    const shellRateBeforeCapture = await evaluate(`(() => { const node = document.querySelector("#shellExchangeRate"); const previous = node.textContent; node.textContent = "USD kuru: 44.00 TL"; return previous; })()`);
    const nativeViewportCapture = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false, fromSurface: true });
    fs.writeFileSync(path.join(outputDir, "pc-builder-native-viewport-current-headless.png"), Buffer.from(nativeViewportCapture.data, "base64"));
    await evaluate(`document.querySelector("#shellExchangeRate").textContent = ${JSON.stringify(shellRateBeforeCapture)}`);
    const priceStepperInteraction1300 = await evaluate(`(() => { const row=document.querySelector("#pcComponents .pc-component-row"),input=row?.querySelector('[data-pc-price]'),button=row?.querySelector('[data-pc-step="price"][data-pc-delta="1"]'); if(!input||!button)return null; const bounds=button.getBoundingClientRect(),hit=document.elementFromPoint(bounds.left+bounds.width/2,bounds.top+bounds.height/2),before=input.value; button.click(); const after=input.value; input.value=before; input.dispatchEvent(new Event("change",{bubbles:true})); return {hitTargetMatches:hit===button,before,after,restored:input.value===before,buttonRect:[Math.round(bounds.left),Math.round(bounds.top),Math.round(bounds.width),Math.round(bounds.height)]}; })()`);
    if (!priceStepperInteraction1300?.hitTargetMatches || priceStepperInteraction1300.after === priceStepperInteraction1300.before || !priceStepperInteraction1300.restored) throw new Error("PC Builder aligned price increment is not visible, clickable, or state-restoring at 1300px: " + JSON.stringify(priceStepperInteraction1300));
    await send("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1128, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 250));
    await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 1000, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 120));
    const interpolatedHeaderSearch = await evaluate(`(() => { const r = document.querySelector('.global-search-wrap').getBoundingClientRect(); return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]; })()`);
    if (JSON.stringify(interpolatedHeaderSearch) !== JSON.stringify([373,15,223,40])) throw new Error("PC Builder header search interpolation failed: " + JSON.stringify(interpolatedHeaderSearch));
    await send("Emulation.setDeviceMetricsOverride", { width: 1600, height: 1128, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 120));
    const visualGeometry = await evaluate(`(() => { const get = selector => { const r = document.querySelector(selector)?.getBoundingClientRect(); return r ? [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)] : null; }; const cols = selector => [...(document.querySelector(selector)?.children || [])].map(node => Math.round(node.getBoundingClientRect().width)); const content = document.querySelector('#content'); const contentBounds = content.getBoundingClientRect(); const selectors = ['.pc-builder-header','.pc-customer-bar','.pc-preset-bar','.pc-component-head','.pc-components','.pc-summary','.pc-actions']; const sections = selectors.map(selector => { const r = document.querySelector(selector).getBoundingClientRect(); return { selector, right: Math.round(r.right) }; }); const summary = document.querySelector('.pc-summary').getBoundingClientRect(); const summaryChildren = [...document.querySelector('.pc-summary').children].map(node => { const r = node.getBoundingClientRect(); return { right: Math.round(r.right), bottom: Math.round(r.bottom) }; }); return { viewport: [innerWidth,innerHeight], globalSearch: get('.global-search-wrap'), qtyStepper: { rect: get('.pc-inline-stepper[data-pc-stepper="qty"]'), parts: [...document.querySelector('.pc-inline-stepper[data-pc-stepper="qty"]').children].map(node => getNodeRect(node)) }, content: get('#content'), page: get('.pc-builder-page'), header: get('.pc-builder-header'), titleLayout: (() => { const heading=document.querySelector('.pc-builder-header h2'), icon=heading?.querySelector('.pc-builder-title-icon'), textNode=Array.from(heading?.childNodes || []).find(node=>node.nodeType===Node.TEXT_NODE), range=document.createRange(); if(textNode){range.setStart(textNode,0);range.setEnd(textNode,1)} const rect=node=>{const value=node?.getBoundingClientRect();return value?[Math.round(value.x*100)/100,Math.round(value.y*100)/100,Math.round(value.width*100)/100,Math.round(value.height*100)/100]:null}; return {heading:rect(heading),icon:rect(icon),text:range.getBoundingClientRect().toJSON(),iconFlex:getComputedStyle(icon).flex,iconBasis:getComputedStyle(icon).flexBasis,gap:getComputedStyle(heading).gap}; })(), customer: get('.pc-customer-bar'), presets: get('.pc-preset-bar'), table: get('.pc-table-scroll'), head: get('.pc-component-head'), row: get('.pc-component-row'), summary: get('.pc-summary'), actions: get('.pc-actions'), headColumns: cols('.pc-component-head'), rowColumns: cols('.pc-component-row'), headings: [...(document.querySelector('.pc-component-head')?.children || [])].map(node => getNodeRect(node)), contentScrollWidth: content.scrollWidth, sectionsWithinContent: sections.every(section => section.right <= contentBounds.right + 1), summaryFits: summaryChildren.every(child => child.right <= summary.right + 1 && child.bottom <= summary.bottom + 1) }; function getNodeRect(node) { const r = node.getBoundingClientRect(); return [Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]; } })()`);
    if (visualGeometry.viewport[0] !== 1600 || JSON.stringify(visualGeometry.globalSearch?.filter((_, index) => index !== 1 && index !== 3)) !== JSON.stringify([407,260]) || visualGeometry.contentScrollWidth > visualGeometry.content[2] || !visualGeometry.sectionsWithinContent || !visualGeometry.summaryFits || JSON.stringify(visualGeometry.customer) !== JSON.stringify([340,202,1230,44]) || visualGeometry.row[1] - visualGeometry.head[1] - visualGeometry.head[3] !== 14 || JSON.stringify(visualGeometry.qtyStepper.parts.map(part => part.slice(2))) !== JSON.stringify([[24,24],[62,28],[24,24]]) || JSON.stringify(visualGeometry.headColumns) !== JSON.stringify([160,150,135,343,56,110,105,55,28]) || JSON.stringify(visualGeometry.rowColumns) !== JSON.stringify([160,150,135,247,112,148,105,55,28])) throw new Error("PC Builder wide desktop layout, header search, native row origin, or summary overflowed: " + JSON.stringify(visualGeometry));
    await evaluate("document.querySelector('.pc-offer-meta span').textContent = 'Tarih: 24.10.2026'");
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false, fromSurface: true });
    const screenshotPath = path.join(outputDir, "pc-builder-current-headless.png");
    fs.writeFileSync(screenshotPath, Buffer.from(screenshot.data, "base64"));
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    await new Promise(resolve => setTimeout(resolve, 150));
    await evaluate(`(async () => {
      window.__pcBuilderEmptyCapture = false;
      navigate('pc-builder');
      for (let attempt = 0; attempt < 60; attempt += 1) {
        if (window.__pcBuilderParts?.length === 4 && document.querySelector('#pcComponents [data-pc-product] option[value="501"]')) return true;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      throw new Error('PC Builder stock fixture did not restore after the matched visual capture.');
    })()`);
    const quantityRange = await evaluate(`(() => {
      const input = document.querySelector('#pcComponents .pc-component-row [data-pc-qty]');
      const before = input.value;
      const min = input.min;
      const max = input.max;
      input.value = "0";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      const zero = input.value;
      const zeroUnderflow = input.validity.rangeUnderflow;
      input.value = "120";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      const maxClamped = input.value;
      input.value = before;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      return { min, max, zero, zeroUnderflow, maxClamped, restored: input.value };
    })()`);
    if (quantityRange.min !== "0" || quantityRange.max !== "99" || quantityRange.zero !== "0" || quantityRange.zeroUnderflow || quantityRange.maxClamped !== "99" || quantityRange.restored !== "1") throw new Error("PC Builder quantity range differs from the native quantity stepper: " + JSON.stringify(quantityRange));
    const inlineSteppers = await evaluate(`(() => {
      const row = document.querySelector('#pcComponents .pc-component-row');
      const quantity = row?.querySelector('[data-pc-qty]');
      const price = row?.querySelector('[data-pc-price]');
      quantity.value = '1';
      quantity.dispatchEvent(new Event('change', { bubbles: true }));
      price.value = '100,75';
      price.dispatchEvent(new Event('change', { bubbles: true }));
      row.querySelector('[data-pc-step="qty"][data-pc-delta="1"]').click();
      const incrementedQuantity = quantity.value;
      row.querySelector('[data-pc-step="qty"][data-pc-delta="-1"]').click();
      row.querySelector('[data-pc-step="price"][data-pc-delta="1"]').click();
      const incrementedPrice = price.value;
      row.querySelector('[data-pc-step="price"][data-pc-delta="-1"]').click();
      const decrementedPrice = price.value;
      price.value = '1000000';
      price.dispatchEvent(new Event('change', { bubbles: true }));
      const clampedPrice = price.value;
      price.value = '100.75';
      price.dispatchEvent(new Event('change', { bubbles: true }));
      return { incrementedQuantity, restoredQuantity: quantity.value, incrementedPrice, decrementedPrice, clampedPrice, total: row.querySelector('.pc-row-total')?.textContent, suffix: row.querySelector('.pc-stepper-suffix')?.textContent };
    })()`);
    if (inlineSteppers.incrementedQuantity !== "2" || inlineSteppers.restoredQuantity !== "1" || inlineSteppers.incrementedPrice !== "101.75" || inlineSteppers.decrementedPrice !== "100.75" || inlineSteppers.clampedPrice !== "999999.00" || inlineSteppers.total !== "100.75 \u20ba" || inlineSteppers.suffix !== "\u20ba") throw new Error("PC Builder inline steppers do not match the native quantity and price controls: " + JSON.stringify(inlineSteppers));
    const brandFilter = await evaluate(`(() => {
      const ramRow = [...document.querySelectorAll('#pcComponents .pc-component-row')].find(row => row.querySelector('.pc-component-name')?.textContent === 'RAM (Bellek)');
      const brand = ramRow?.querySelector('[data-pc-brand]');
      const options = [...(brand?.options || [])].map(option => option.textContent);
      const hasKnownBrand = options.includes('Corsair') && options.includes('G.Skill');
      const hasStoredBrandOnly = options.includes('Audit');
      const initialProduct = ramRow?.querySelector('[data-pc-product]');
      if (initialProduct) { initialProduct.value = '503'; initialProduct.dispatchEvent(new Event('change', { bubbles: true })); }
      const availableBeforeFilter = [...(ramRow?.querySelector('[data-pc-product]')?.options || [])].map(option => option.value); const priceBeforeFilter = ramRow?.querySelector('[data-pc-price]')?.value || ''; const stockBeforeFilter = ramRow?.querySelector('.pc-stock')?.textContent || '';
      if (brand) { brand.value = 'G.Skill'; brand.dispatchEvent(new Event('change', { bubbles: true })); }
      let filteredRow = [...document.querySelectorAll('#pcComponents .pc-component-row')].find(row => row.querySelector('.pc-component-name')?.textContent === 'RAM (Bellek)');
      const selectedAfterBrand = filteredRow?.querySelector('[data-pc-product]')?.value || '';
      const priceAfterBrand = filteredRow?.querySelector('[data-pc-price]')?.value || '';
      const stockAfterBrand = filteredRow?.querySelector('.pc-stock')?.textContent || '';
      const matchingProducts = [...(filteredRow?.querySelector('[data-pc-product]')?.options || [])].slice(1).map(option => option.textContent);
      const matchingSelect = filteredRow?.querySelector('[data-pc-product]');
      if (matchingSelect) { matchingSelect.value = '504'; matchingSelect.dispatchEvent(new Event('change', { bubbles: true })); }
      filteredRow = [...document.querySelectorAll('#pcComponents .pc-component-row')].find(row => row.querySelector('.pc-component-name')?.textContent === 'RAM (Bellek)');
      const spec = filteredRow?.querySelector('[data-pc-spec]');
      if (spec) { spec.value = 'DDR4'; spec.dispatchEvent(new Event('change', { bubbles: true })); }
      filteredRow = [...document.querySelectorAll('#pcComponents .pc-component-row')].find(row => row.querySelector('.pc-component-name')?.textContent === 'RAM (Bellek)');
      const selectedAfterSpec = filteredRow?.querySelector('[data-pc-product]')?.value || '';
      const priceAfterSpec = filteredRow?.querySelector('[data-pc-price]')?.value || '';
      return { hasKnownBrand, hasStoredBrandOnly, availableBeforeFilter, priceBeforeFilter, stockBeforeFilter, selectedAfterBrand, priceAfterBrand, stockAfterBrand, matchingProducts, selectedAfterSpec, priceAfterSpec };
    })()`);
    if (!brandFilter.hasKnownBrand || brandFilter.hasStoredBrandOnly || brandFilter.priceBeforeFilter !== '4000.00' || brandFilter.stockBeforeFilter !== '8' || brandFilter.selectedAfterBrand !== '' || brandFilter.priceAfterBrand !== '0.00' || brandFilter.stockAfterBrand !== '\u2014' || brandFilter.matchingProducts.length !== 1 || !brandFilter.matchingProducts[0].includes('GSkill Fury DDR5') || brandFilter.selectedAfterSpec !== '' || brandFilter.priceAfterSpec !== '0.00') throw new Error('PC Builder brand options or brand-name alias filtering differ from the desktop behavior: ' + JSON.stringify(brandFilter));
    const addComponent = await evaluate(`(async () => {
      document.querySelector('[data-pc-action="add-component"]').click();
      const form = document.querySelector('#dialogForm');
      const spec = form?.elements.namedItem('spec');
      const initial = { dialogOpen: document.querySelector('#appDialog')?.open || false, nameField: Boolean(form?.elements.namedItem('name')), categoryField: Boolean(form?.elements.namedItem('category')), specValue: spec?.value || '', hasSpecsListField: Boolean(form?.elements.namedItem('specs')) };
      form.elements.namedItem('name').value = 'Optical Drive';
      form.elements.namedItem('category').value = 'Optical Drive';
      spec.value = 'Connection Type';
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      await new Promise(resolve => setTimeout(resolve, 50));
      const row = document.querySelector('#pcComponents .pc-component-row:last-child');
      return { ...initial, rowCount: document.querySelectorAll('#pcComponents .pc-component-row').length, rowName: row?.querySelector('.pc-component-name')?.textContent || '', specLabel: row?.querySelector('[data-pc-spec]')?.getAttribute('aria-label') || '', specDefault: row?.querySelector('[data-pc-spec] option:nth-child(2)')?.textContent || '', dialogOpenAfterSubmit: document.querySelector('#appDialog')?.open || false };
    })()`);
    if (!addComponent.dialogOpen || !addComponent.nameField || !addComponent.categoryField || addComponent.specValue !== 'Standart' || addComponent.hasSpecsListField || addComponent.rowCount !== 16 || addComponent.rowName !== 'Optical Drive' || addComponent.specLabel !== 'Connection Type' || addComponent.specDefault !== 'Standart' || addComponent.dialogOpenAfterSubmit) throw new Error('PC Builder add-component dialog does not match the desktop contract: ' + JSON.stringify(addComponent));
    const presetCopy = await evaluate(`(() => {
      const notes = {};
      for (const key of ['content', 'workstation', 'home', 'gaming']) {
        document.querySelector('[data-pc-preset="' + key + '"]').click();
        notes[key] = { margin: document.querySelector('#pcMargin')?.value, note: document.querySelector('#pcNote')?.value };
      }
      return notes;
    })()`);
    if (presetCopy.content.margin !== '22' || presetCopy.content.note !== 'Yarat\u0131c\u0131 i\u00e7erik \u00fcretimi & video d\u00fczenleme i\u00e7in optimize edilmi\u015ftir.' || presetCopy.workstation.margin !== '18' || presetCopy.workstation.note !== 'Profesyonel i\u015f istasyonu. ECC RAM & i\u015f y\u00fck\u00fc optimizasyonu.' || presetCopy.home.margin !== '15' || presetCopy.home.note !== 'Ev ve Ofis kullan\u0131m\u0131 i\u00e7in haz\u0131rlanm\u0131\u015ft\u0131r. 1 y\u0131l garanti.' || presetCopy.gaming.margin !== '20' || presetCopy.gaming.note !== 'Gaming konfig\u00fcrasyonu. Y\u00fcksek FPS odakl\u0131 se\u00e7im. 1 y\u0131l garanti.') throw new Error('PC Builder preset values differ from the desktop configuration: ' + JSON.stringify(presetCopy));
    const search = await evaluate(`(() => { const input = document.querySelector('#pcCustomerSearch'); const select = document.querySelector('#pcCustomer'); input.value = 'beta'; input.dispatchEvent(new Event('input', { bubbles: true })); const count = select.options.length; const name = select.options[1]?.textContent; select.value = '72'; select.dispatchEvent(new Event('change', { bubbles: true })); input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); const restoredOptions = select.options.length; const afterClear = select.value; const offerWithCustomer = document.querySelector('.pc-offer-meta strong')?.textContent || ''; select.value = ''; select.dispatchEvent(new Event('change', { bubbles: true })); const offerAfterClear = document.querySelector('.pc-offer-meta strong')?.textContent || ''; select.value = '72'; select.dispatchEvent(new Event('change', { bubbles: true })); document.querySelector('[data-pc-preset="gaming"]').click(); return { filteredOptions: count, filteredName: name, restoredOptions, afterClear, offerWithCustomer, offerAfterClear, afterPreset: document.querySelector('#pcCustomer')?.value, searchAfterPreset: document.querySelector('#pcCustomerSearch')?.value, rowsAfterPreset: document.querySelectorAll('#pcComponents .pc-component-row').length }; })()`);
    if (search.filteredOptions !== 2 || search.filteredName !== 'Beta Customer' || search.restoredOptions !== 3 || search.afterClear !== '72' || !search.offerWithCustomer.includes('Beta Customer') || search.offerAfterClear.includes('Beta Customer') || search.afterPreset !== '72' || search.searchAfterPreset !== '' || search.rowsAfterPreset !== 16) throw new Error('Customer selection/search/preset flow failed: ' + JSON.stringify(search));
    const customer360Registration = await evaluate(`(async () => {
      window.__pcBuilderWrites = [];
      const product = document.querySelector('#pcComponents [data-pc-product]');
      product.value = '501';
      product.dispatchEvent(new Event('change', { bubbles: true }));
      document.querySelector('[data-pc-action="customer"]').click();
      await new Promise(resolve => setTimeout(resolve, 80));
      const result = { writes: window.__pcBuilderWrites, dialogOpen: document.querySelector('#appDialog')?.open || false, customer360Visible: document.querySelector('#appDialog')?.classList.contains('c360-dialog') || false, notesButtonVisible: Boolean(document.querySelector('#c360Notes')) };
      document.querySelector('#appDialog')?.close();
      return result;
    })()`);
    if (customer360Registration.writes.length !== 1 || customer360Registration.writes[0].endpoint !== '/api/desktop/table/customer_notes' || customer360Registration.writes[0].body.note_type !== 'Teklif' || customer360Registration.writes[0].body.customer_id !== 72 || !customer360Registration.writes[0].body.content.includes('\u2022 Anakart: Audit B550 Board  x1  12,000.00\u20ba') || !customer360Registration.writes[0].body.content.includes('Teklif Toplam\u0131: 17,280.00 \u20ba') || !customer360Registration.customer360Visible || !customer360Registration.notesButtonVisible) throw new Error('PC Builder MÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¼ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¸teri 360 action did not save the quote note and open the selected customer: ' + JSON.stringify(customer360Registration));
    const proforma = await evaluate(`(async () => {
      const product = document.querySelector('#pcComponents [data-pc-product]');
      product.value = '501';
      product.dispatchEvent(new Event('change', { bubbles: true }));
      desktopSettings = { ...desktopSettings, proforma_editor_html: '<p>Custom editor fixture</p>', proforma_template_uploaded: '1', proforma_template_filename: 'audit-template.pdf' };
      window.__pcPdfRequest = null;
      window.__pcPdfTarget = null;
      window.open = () => ({ location: { replace: value => { window.__pcPdfTarget = value; } }, close: () => {} });
      URL.createObjectURL = () => 'blob:pc-builder-test';
      URL.revokeObjectURL = () => {};
      window.fetch = async (url, options) => {
        window.__pcPdfRequest = { url, payload: JSON.parse(options.body) };
        return { ok: true, blob: async () => new Blob(['%PDF-test']) };
      };
      document.querySelector('[data-pc-action="pdf"]').click();
      await new Promise(resolve => setTimeout(resolve, 20));
      document.querySelector('#pcPdfCompany').value = 'AYEC QA Company';
      document.querySelector('#pcPdfProject').value = 'PC Builder QA';
      document.querySelector('#pcPdfCurrency').value = 'USD';
      document.querySelector('#pcPdfTemplate').value = 'corporate';
      const editorOptionAvailable = [...document.querySelector('#pcPdfTemplate').options].some(option => option.value === 'editor_template');
      document.querySelector('#dialogForm').requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const corporateRequest = window.__pcPdfRequest;
      const customOptionAvailable = [...document.querySelector('#pcPdfTemplate').options].some(option => option.value === 'custom_template');
      document.querySelector('[data-pc-action="pdf"]').click();
      await new Promise(resolve => setTimeout(resolve, 20));
      document.querySelector('#pcPdfCompany').value = 'AYEC QA Company';
      document.querySelector('#pcPdfProject').value = 'PC Builder QA';
      document.querySelector('#pcPdfTemplate').value = 'editor_template';
      document.querySelector('#dialogForm').requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      const editorRequest = window.__pcPdfRequest;
      document.querySelector('[data-pc-action="pdf"]').click();
      await new Promise(resolve => setTimeout(resolve, 20));
      document.querySelector('#pcPdfCompany').value = 'AYEC QA Company';
      document.querySelector('#pcPdfProject').value = 'PC Builder QA';
      document.querySelector('#pcPdfTemplate').value = 'custom_template';
      document.querySelector('#dialogForm').requestSubmit();
      await new Promise(resolve => setTimeout(resolve, 80));
      return { request: corporateRequest, editorRequest, customRequest: window.__pcPdfRequest, editorOptionAvailable, customOptionAvailable, target: window.__pcPdfTarget, dialogOpen: document.querySelector('#appDialog').open };
    })()`);
    if (!proforma.request || proforma.request.url !== '/api/desktop/pc-builder/proforma.pdf' || proforma.request.payload.company_name !== 'AYEC QA Company' || proforma.request.payload.customer_name !== 'Beta Customer' || proforma.request.payload.project_name !== 'PC Builder QA' || proforma.request.payload.currency !== 'USD' || proforma.request.payload.template !== 'corporate' || proforma.request.payload.items.length !== 1 || proforma.request.payload.items[0].product !== 'Audit B550 Board' || !proforma.editorOptionAvailable || proforma.editorRequest?.payload?.template !== 'editor_template' || !proforma.customOptionAvailable || proforma.customRequest?.payload?.template !== 'custom_template' || proforma.target !== 'blob:pc-builder-test' || proforma.dialogOpen) throw new Error('PC Builder proforma dialog or PDF request failed: ' + JSON.stringify(proforma));
    const templateEditor = await evaluate(`(async () => {
      page = 'settings';
      settingsSection = 'proforma-template';
      desktopSettings = { ...desktopSettings, proforma_local_pdf_path_present: '1', proforma_template_uploaded: '0', proforma_template_filename: '' };
      render();
      const sectionPresent = document.querySelector('#proformaTemplateHtml') && document.querySelector('[data-setting-key="proforma_use_custom_editor"]');
      if (!sectionPresent) return { sectionPresent: false };
      const legacyPdfNoticeShown = Boolean(document.querySelector('.proforma-legacy-pdf-notice'));
      document.querySelector('[data-proforma-starter]').click();
      const editor = document.querySelector('#proformaTemplateHtml');
      const canvas = document.querySelector('#proformaTemplateCanvas');
      const paste = new Event('paste', { bubbles: true, cancelable: true });
      Object.defineProperty(paste, 'clipboardData', { value: { getData: type => type === 'text/html' ? '<p onclick="window.__pasteRan=true">Pasted Safe<script>window.__pasteRan=true</script><img src="https://invalid.test/a.png" onerror="window.__pasteRan=true"></p>' : '' } });
      canvas.dispatchEvent(paste);
      const pasteSanitized = canvas.innerHTML.includes('Pasted Safe') && !canvas.innerHTML.includes('onclick') && !canvas.innerHTML.includes('<script') && !canvas.innerHTML.includes('invalid.test');
      const walker = document.createTreeWalker(canvas, NodeFilter.SHOW_TEXT);
      let textNode = null;
      while (walker.nextNode()) { if (walker.currentNode.textContent.includes('PROFORMA')) { textNode = walker.currentNode; break; } }
      const wordStart = textNode.textContent.indexOf('PROFORMA');
      const selection = window.getSelection();
      const range = document.createRange();
      range.setStart(textNode, wordStart); range.setEnd(textNode, wordStart + 'PROFORMA'.length);
      selection.removeAllRanges(); selection.addRange(range);
      document.querySelector('[data-proforma-format="bold"]').click();
      const italicShortcut = !canvas.dispatchEvent(new KeyboardEvent('keydown', { key: 'i', ctrlKey: true, bubbles: true, cancelable: true }));
      const endRange = document.createRange();
      endRange.selectNodeContents(canvas); endRange.collapse(false);
      selection.removeAllRanges(); selection.addRange(endRange);
      document.querySelector('[data-proforma-token="{{firma_adi}}"]').click();
      const fixtureCanvas = document.createElement('canvas');
      fixtureCanvas.width = 2; fixtureCanvas.height = 2;
      fixtureCanvas.getContext('2d').fillRect(0, 0, 2, 2);
      const imageBlob = await new Promise(resolve => fixtureCanvas.toBlob(resolve, 'image/png'));
      const picker = document.querySelector('[data-proforma-image-file]');
      Object.defineProperty(picker, 'files', { configurable: true, value: [new File([imageBlob], 'qa.png', { type: 'image/png' })] });
      picker.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 100));
      window.__templateWrites = [];
      window.__originalApiFetch = apiFetch;
      apiFetch = async (endpoint, options = {}) => { if (endpoint === "/api/desktop/bootstrap") return { settings: { ...desktopSettings } }; window.__templateWrites.push({ endpoint, body: JSON.parse(options.body || "{}") }); return { ok: true }; };
      document.querySelector('[data-action="save-settings"]').click();
      await new Promise(resolve => setTimeout(resolve, 60));
      const validActivation = document.querySelector('[data-setting-key="proforma_use_custom_editor"]').checked;
      const savedEditorValue = editor.value;
      editor.value = '<p>Unrenderable activation fixture</p>';
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      document.querySelector('[data-setting-key="proforma_use_custom_editor"]').checked = true;
      window.__templateFailureWrites = [];
      window.__savedFetch = window.fetch;
      apiFetch = async (endpoint, options = {}) => { if (endpoint === "/api/desktop/bootstrap") return { settings: { ...desktopSettings } }; window.__templateFailureWrites.push({ endpoint, body: JSON.parse(options.body || "{}") }); return { ok: true }; };
      window.fetch = async () => ({ ok: false, json: async () => ({ error: 'Fixture PDF validation failure' }) });
      document.querySelector('[data-action="save-settings"]').click();
      await new Promise(resolve => setTimeout(resolve, 60));
      const activationRestored = document.querySelector('[data-setting-key="proforma_use_custom_editor"]').checked;
      apiFetch = window.__originalApiFetch;
      window.fetch = window.__savedFetch;
      window.__templateUploadRequest = null;
      window.__savedApiFetch = apiFetch;
      apiFetch = async (endpoint, options) => { window.__templateUploadRequest = { endpoint, body: JSON.parse(options.body) }; return { ok: true, uploaded: true, filename: 'audit-template.pdf', page_count: 1 }; };
      const pdfPicker = document.querySelector('[data-proforma-pdf-file]');
      Object.defineProperty(pdfPicker, 'files', { configurable: true, value: [new File(['%PDF-1.4 audit fixture'], 'audit-template.pdf', { type: 'application/pdf' })] });
      pdfPicker.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 80));
      const customPdfUploaded = desktopSettings.proforma_template_uploaded === '1' && desktopSettings.proforma_template_filename === 'audit-template.pdf';
      const legacyPdfNoticeCleared = !document.querySelector('.proforma-legacy-pdf-notice');
      apiFetch = window.__savedApiFetch;
      window.__savedApiFetch = apiFetch;
      apiFetch = async () => ({ ok: true, uploaded: false, filename: '' });
      document.querySelector('[data-proforma-pdf-remove]')?.click();
      await new Promise(resolve => setTimeout(resolve, 80));
      const legacyPdfNoticeRestored = Boolean(document.querySelector('.proforma-legacy-pdf-notice'));
      apiFetch = window.__savedApiFetch;
      return { sectionPresent: true, enabled: validActivation, activationRestored, restoredEditorHtml: desktopSettings.proforma_editor_html, restoredActivation: desktopSettings.proforma_use_custom_editor, failureWrites: window.__templateFailureWrites, italicShortcut, pasteSanitized, editorValue: savedEditorValue, writes: window.__templateWrites, legacyPdfNoticeShown, customPdfUploaded, legacyPdfNoticeCleared, legacyPdfNoticeRestored, customPdfUploadRequest: window.__templateUploadRequest };
    })()`);
    if (!templateEditor.sectionPresent || !templateEditor.enabled || !templateEditor.activationRestored || !templateEditor.italicShortcut || !templateEditor.pasteSanitized || !templateEditor.legacyPdfNoticeShown || !templateEditor.customPdfUploaded || !templateEditor.legacyPdfNoticeCleared || !templateEditor.legacyPdfNoticeRestored || templateEditor.restoredEditorHtml !== templateEditor.editorValue || String(templateEditor.restoredActivation) !== "1" || JSON.stringify(templateEditor.failureWrites.filter(item => item.body.key === "proforma_use_custom_editor").map(item => item.body.value)) !== JSON.stringify(["0", "0", "1"]) || templateEditor.customPdfUploadRequest?.endpoint !== '/api/desktop/pc-builder/proforma-template' || templateEditor.customPdfUploadRequest?.body?.filename !== 'audit-template.pdf' || templateEditor.failureWrites.length !== 5 || templateEditor.failureWrites.some(item => item.endpoint !== '/api/desktop/table/settings') || !templateEditor.editorValue.includes('<b><i>PROFORMA</i></b>') || !templateEditor.editorValue.includes('data:image/jpeg;base64,') || templateEditor.writes.length !== 3 || templateEditor.writes.some(item => item.endpoint !== '/api/desktop/table/settings') || !templateEditor.writes.some(item => item.body.key === 'proforma_editor_html') || JSON.stringify(templateEditor.writes.filter(item => item.body.key === 'proforma_use_custom_editor').map(item => item.body.value)) !== JSON.stringify(['0', '1'])) throw new Error('Proforma template settings editor did not format/insert, validate, and activate only after PDF success: ' + JSON.stringify(templateEditor));
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const templateMobile = await evaluate(`(() => { const section=document.querySelector('.proforma-custom-pdf'),notice=document.querySelector('.proforma-legacy-pdf-notice'); const rect=node=>{const value=node?.getBoundingClientRect();return value?[Math.round(value.left),Math.round(value.right),Math.round(value.width)]:null}; return {viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,section:rect(section),notice:rect(notice),noticeScrollWidth:notice?.scrollWidth||0,noticeClientWidth:notice?.clientWidth||0}; })()`);
    if (templateMobile.viewport !== 390 || templateMobile.documentWidth > 390 || !templateMobile.notice || templateMobile.notice[0] < templateMobile.section[0] || templateMobile.notice[1] > templateMobile.section[1] + 1 || templateMobile.noticeScrollWidth > templateMobile.noticeClientWidth) throw new Error('Proforma legacy PDF notice does not fit the mobile settings layout: ' + JSON.stringify(templateMobile));
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    await evaluate(`(() => { page = 'pc-builder'; render(); })()`);
    const anonymousSave = await evaluate(`(async () => {
      window.__pcBuilderWrites = [];
      const product = document.querySelector('#pcComponents [data-pc-product]');
      product.value = '501';
      product.dispatchEvent(new Event('change', { bubbles: true }));
      const customer = document.querySelector('#pcCustomer');
      customer.value = '';
      customer.dispatchEvent(new Event('change', { bubbles: true }));
      document.querySelector('[data-pc-action="save"]').click();
      await new Promise(resolve => setTimeout(resolve, 40));
      return window.__pcBuilderWrites;
    })()`);
    if (anonymousSave.length !== 1 || anonymousSave[0].endpoint !== '/api/desktop/table/audit_logs' || anonymousSave[0].body.table_name !== 'pc_offers' || anonymousSave[0].body.action !== 'INSERT' || !anonymousSave[0].body.details.includes('M\u00fc\u015fteri: Belirtilmedi') || !anonymousSave[0].body.details.includes('\u2022 Anakart: Audit B550 Board  \u00d71  12,000.00\u20ba  = 12,000.00\u20ba') || !anonymousSave[0].body.details.includes('Maliyet: 12,000.00 \u20ba  |  K\u00e2r Marj\u0131: 20.0%  |  KDV: %20  |  Toplam: 17,280.00 \u20ba') || !/\nTarih: \d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\n/.test(anonymousSave[0].body.details)) throw new Error('Customer-optional PC offer save did not persist the desktop audit entry: ' + JSON.stringify(anonymousSave));
    const customerSave = await evaluate(`(async () => {
      const waitForWrites = async count => { for (let attempt = 0; attempt < 60; attempt += 1) { if (window.__pcBuilderWrites.length >= count) return true; await new Promise(resolve => setTimeout(resolve, 20)); } return false; };
      const customer = document.querySelector("#pcCustomer");
      const option = [...(customer?.options || [])].find(item => item.value);
      if (!customer || !option) throw new Error("PC Builder customer fixture is unavailable.");
      customer.value = option.value;
      customer.dispatchEvent(new Event("change", { bubbles: true }));
      window.__pcBuilderWrites = [];
      document.querySelectorAll("#toastRoot .toast").forEach(node => node.remove());
      document.querySelector('[data-pc-action="save"]').click();
      await waitForWrites(2);
      const writes = window.__pcBuilderWrites;
      const note = writes.find(item => item.endpoint === "/api/desktop/table/customer_notes");
      const audit = writes.find(item => item.endpoint === "/api/desktop/table/audit_logs");
      const messages = [...document.querySelectorAll("#toastRoot .toast")].map(node => node.textContent || "");
      return { customerId: String(option.value), customerName: option.textContent.trim(), writes, note, audit, messages };
    })()`);
    if (customerSave.writes.length !== 2 || customerSave.writes[0]?.endpoint !== "/api/desktop/table/audit_logs" || customerSave.audit?.body?.table_name !== "pc_offers" || customerSave.audit?.body?.action !== "INSERT" || customerSave.writes[1]?.endpoint !== "/api/desktop/table/customer_notes" || String(customerSave.note?.body?.customer_id) !== customerSave.customerId || customerSave.note?.body?.note_type !== "PC Teklif" || customerSave.note?.body?.type !== "PC Teklif" || !String(customerSave.note?.body?.content || "").includes(`M\u00fc\u015fteri: ${customerSave.customerName}`) || !customerSave.messages.some(message => message.includes("kaydedildi"))) throw new Error("PC Builder customer offer save did not match the desktop audit and customer-note workflow: " + JSON.stringify(customerSave));
    const financeSave = await evaluate(`(async () => {
      const waitForWrites = async count => { for (let attempt = 0; attempt < 60; attempt += 1) { if (window.__pcBuilderWrites.length >= count) return true; await new Promise(resolve => setTimeout(resolve, 20)); } return false; };
      window.__pcBuilderWrites = [];
      document.querySelectorAll("#toastRoot .toast").forEach(node => node.remove());
      document.querySelector('[data-pc-action="finance"]').click();
      await waitForWrites(1);
      const writes = window.__pcBuilderWrites;
      const request = writes[0] || null;
      const messages = [...document.querySelectorAll("#toastRoot .toast")].map(node => node.textContent || "");
      return { writes, request, messages };
    })()`);
    const financeBody = financeSave.request?.body || {};
    if (financeSave.writes.length !== 1 || financeSave.request?.endpoint !== "/api/desktop/table/accounting" || financeBody.type !== "Gelir" || financeBody.category !== "Sat\u0131\u015f" || Number(financeBody.amount) !== 17280 || !String(financeBody.description || "").includes("Bilgisayar Topla / Teklif #REF1") || !String(financeBody.description || "").includes("Anakart") || financeBody.customer_name !== customerSave.customerName || String(financeBody.customer_id) !== customerSave.customerId || financeBody.payment_method !== "Nakit" || financeBody.currency !== "TRY" || !Number.isFinite(Date.parse(financeBody.date)) || !financeSave.messages.some(message => message.includes("Finans kayd\u0131 olu\u015fturuldu"))) throw new Error("PC Builder finance workflow did not create the desktop-equivalent income entry: " + JSON.stringify(financeSave));
    const exceptionsBeforeSaveFailure = exceptions.length;
    const saveFailure = await evaluate(`(async () => {
      window.__pcBuilderOriginalApiFetch = apiFetch;
      document.querySelectorAll('#toastRoot .toast').forEach(node => node.remove());
      apiFetch = async () => { throw new Error('Audit offline'); };
      document.querySelector('[data-pc-action="save"]').click();
      for (let attempt = 0; attempt < 40 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
      const messages = [...document.querySelectorAll('#toastRoot .toast')].map(node => node.textContent || '');
      apiFetch = window.__pcBuilderOriginalApiFetch;
      delete window.__pcBuilderOriginalApiFetch;
      return { messages };
    })()`);
    const saveFailureExceptions = exceptions.length - exceptionsBeforeSaveFailure;
    if (!saveFailure.messages.some(message => message.includes('Teklif kaydedilemedi: Audit offline')) || saveFailure.messages.some(message => message.includes('kaydedildi')) || saveFailureExceptions) throw new Error('PC Builder offer save did not report the API failure cleanly: ' + JSON.stringify({ saveFailure, saveFailureExceptions }));
    const exceptionsBeforeActionFailures = exceptions.length;
    const actionFailures = await evaluate(`(async () => {
      const originalApiFetch = apiFetch;
      const triggerFailure = async (action, message) => {
        document.querySelectorAll('#toastRoot .toast').forEach(node => node.remove());
        apiFetch = async () => { throw new Error('Audit offline'); };
        document.querySelector('[data-pc-action="' + action + '"]').click();
        for (let attempt = 0; attempt < 40 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
        const messages = [...document.querySelectorAll('#toastRoot .toast')].map(node => node.textContent || '');
        apiFetch = originalApiFetch;
        return messages.some(value => value.includes(message + 'Audit offline')) && !messages.some(value => value.includes('olu\u015fturuldu') || value.includes('stoktan d\u00fc\u015f\u00fcld\u00fc') || value.includes('m\u00fc\u015fteri kayd\u0131na eklendi'));
      };
      const customerPicker = document.querySelector('#pcCustomer');
      customerPicker.value = '71';
      customerPicker.dispatchEvent(new Event('change', { bubbles: true }));
      const customer = await triggerFailure('customer', 'M\u00fc\u015fteri kayd\u0131 eklenemedi: ');
      const finance = await triggerFailure('finance', 'Finans kayd\u0131 eklenemedi: ');
      const stock = await triggerFailure('stock', 'Stoktan d\u00fc\u015f\u00fclemedi: ');
      return { customer, finance, stock };
    })()`);
    const actionFailureExceptions = exceptions.length - exceptionsBeforeActionFailures;
    if (!actionFailures.customer || !actionFailures.finance || !actionFailures.stock || actionFailureExceptions) throw new Error('PC Builder customer, finance, or stock action did not report API failures cleanly: ' + JSON.stringify({ actionFailures, actionFailureExceptions }));
    const stockDeduction = await evaluate(`(async () => {
      window.__pcBuilderWrites = [];
      const rowFor = name => [...document.querySelectorAll('#pcComponents .pc-component-row')].find(row => row.querySelector('.pc-component-name')?.textContent === name);
      const choose = (name, partId, quantity = 1) => {
        const row = rowFor(name);
        const product = row?.querySelector('[data-pc-product]');
        if (product) { product.value = String(partId); product.dispatchEvent(new Event('change', { bubbles: true })); }
        const qty = row?.querySelector('[data-pc-qty]');
        if (qty) { qty.value = String(quantity); qty.dispatchEvent(new Event('change', { bubbles: true })); }
      };
      let ram = rowFor('RAM (Bellek)');
      const brand = ram?.querySelector('[data-pc-brand]');
      if (brand) { brand.value = ''; brand.dispatchEvent(new Event('change', { bubbles: true })); }
      ram = rowFor('RAM (Bellek)');
      const spec = ram?.querySelector('[data-pc-spec]');
      if (spec) { spec.value = ''; spec.dispatchEvent(new Event('change', { bubbles: true })); }
      choose('Anakart', 501, 1);
      choose('\u0130\u015flemci (CPU)', 502, 1);
      choose('RAM (Bellek)', 503, 9);
      document.querySelector('[data-pc-action="stock"]').click();
      await new Promise(resolve => setTimeout(resolve, 100));
      const request = window.__pcBuilderWrites.find(item => item.endpoint === '/api/desktop/pc-builder/deduct-stock');
      const messages = [...document.querySelectorAll('#toastRoot .toast')].map(node => node.textContent || '');
      const stockFor = name => rowFor(name)?.querySelector('.pc-stock')?.textContent || '';
      const partStock = id => window.__pcBuilderParts?.find(part => String(part.id) === String(id))?.qty;
      return { request, messages, boardStock: stockFor('Anakart'), cpuStock: stockFor('\u0130\u015flemci (CPU)'), ramStock: stockFor('RAM (Bellek)'), boardPartStock: partStock(501), cpuPartStock: partStock(502), ramPartStock: partStock(503) };
    })()`);
    const deductedIds = (stockDeduction.request?.body?.items || []).map(item => String(item.part_id)).sort();
    if (deductedIds.join(',') !== '501,502' || stockDeduction.request.body.items.some(item => Number(item.quantity) !== 1) || stockDeduction.boardStock !== '3' || stockDeduction.cpuStock !== '2' || stockDeduction.ramStock !== '8' || stockDeduction.boardPartStock !== 3 || stockDeduction.cpuPartStock !== 2 || stockDeduction.ramPartStock !== 8 || !stockDeduction.messages.some(message => message.includes('2 \u00fcr\u00fcn stoktan d\u00fc\u015f\u00fcld\u00fc')) || !stockDeduction.messages.some(message => message.includes('Audit DDR5 Memory'))) throw new Error('PC Builder partial stock deduction or refreshed stock labels failed: ' + JSON.stringify(stockDeduction));
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    const mobile = await evaluate(`(() => { const row = document.querySelector('.pc-component-row'); const content = document.querySelector('#content'); const qtyStepper=row?.querySelector('[data-pc-stepper="qty"]'),qtyInput=qtyStepper?.querySelector('[data-pc-qty]'),qtyBefore=Number(qtyInput?.value||0),qtyPlus=qtyStepper?.querySelector('[data-pc-step="qty"][data-pc-delta="1"]'),plusRect=qtyPlus?.getBoundingClientRect();qtyPlus?.click();const qtyAfter=Number(row?.querySelector('[data-pc-qty]')?.value||0);row?.querySelector('[data-pc-stepper="qty"] [data-pc-step="qty"][data-pc-delta="-1"]')?.click();const qtyRestored=Number(row?.querySelector('[data-pc-qty]')?.value||0); return { viewport: innerWidth, documentWidth: document.documentElement.scrollWidth, contentWidth: content?.clientWidth, pageWidth: Math.round(document.querySelector('.pc-builder-page')?.getBoundingClientRect().width || 0), visibleRows: document.querySelectorAll('#pcComponents .pc-component-row').length, componentWidth: Math.round(document.querySelector('.pc-components')?.getBoundingClientRect().width || 0), rowWidth: Math.round(row?.getBoundingClientRect().width || 0), rowScrollWidth: row?.scrollWidth || 0, rowGrid: getComputedStyle(row).gridTemplateColumns, children: [...row.children].map(node => [node.tagName, node.dataset.pcBrand !== undefined ? 'brand' : node.dataset.pcSpec !== undefined ? 'spec' : node.dataset.pcProduct !== undefined ? 'product' : node.dataset.pcQty !== undefined ? 'qty' : node.dataset.pcPrice !== undefined ? 'price' : node.className, Math.round(node.getBoundingClientRect().width), getComputedStyle(node).display]), actionsWidth: Math.round(document.querySelector('.pc-actions')?.getBoundingClientRect().width || 0), quantityInteraction:{before:qtyBefore,after:qtyAfter,restored:qtyRestored,plusVisible:!!plusRect&&plusRect.left>=0&&plusRect.right<=innerWidth&&plusRect.top>=0&&plusRect.bottom<=innerHeight} }; })()`);
    if (mobile.viewport !== 390 || mobile.documentWidth > 390 || mobile.visibleRows !== 16 || mobile.componentWidth > 390 || mobile.rowScrollWidth > mobile.rowWidth || mobile.actionsWidth > 390 || mobile.quantityInteraction?.after !== mobile.quantityInteraction?.before + 1 || mobile.quantityInteraction?.restored !== mobile.quantityInteraction?.before || !mobile.quantityInteraction?.plusVisible || exceptions.length) throw new Error("PC Builder mobile or runtime check failed: " + JSON.stringify({ mobile, exceptions }));
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    const salesWorkflows = await evaluate(`(async () => {
      const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
      const rect = node => { if (!node) return null; const r = node.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; };
      const read = () => ({ page: document.body.dataset.page, active: document.querySelector('.sales-workflow-tabs .active')?.dataset.salesWorkflow || '', labels: [...document.querySelectorAll('.sales-workflow-tabs [data-sales-workflow]')].map(button => button.textContent.trim()), tabs: rect(document.querySelector('.sales-workflow-tabs')), smartHome: Boolean(document.querySelector('.smart-home-sales-page')) });
      const initial = read();
      document.querySelector('[data-sales-workflow="sales"]')?.click(); await pause(300); const sales = read();
      document.querySelector('[data-sales-workflow="smart-home"]')?.click(); await pause(300); const smartHome = read();
      document.querySelector('[data-sales-workflow="computer"]')?.click(); await pause(300); const computer = read();
      return { initial, sales, smartHome, computer };
    })()`);
    const expectedWorkflowLabels = ["G\u00fcvenlik Sistemleri", "Ak\u0131ll\u0131 Ev", "Bilgisayar"];
    if (JSON.stringify(salesWorkflows.initial.labels) !== JSON.stringify(expectedWorkflowLabels) || [salesWorkflows.initial.tabs,salesWorkflows.sales.tabs,salesWorkflows.smartHome.tabs].some(bounds => bounds?.[0] !== 260 || bounds?.[1] !== 70 || bounds?.[3] !== 34) || salesWorkflows.initial.active !== "computer" || salesWorkflows.sales.page !== "sales" || salesWorkflows.sales.active !== "sales" || salesWorkflows.smartHome.page !== "sales" || salesWorkflows.smartHome.active !== "smart-home" || !salesWorkflows.smartHome.smartHome || salesWorkflows.computer.page !== "pc-builder" || salesWorkflows.computer.active !== "computer" || exceptions.length) throw new Error("Sales Hub tab labels or page navigation diverged from desktop: " + JSON.stringify({ salesWorkflows, exceptions }));
    const pricingCalculation = await evaluate(`(() => {
      const rows = [...document.querySelectorAll("#pcComponents .pc-component-row")];
      rows.forEach((row, index) => {
        const quantity = row.querySelector("[data-pc-qty]");
        const price = row.querySelector("[data-pc-price]");
        if (!quantity || !price) throw new Error("PC Builder pricing fixture controls are missing.");
        quantity.value = index === 0 ? "2" : "0";
        quantity.dispatchEvent(new Event("input", { bubbles: true }));
        price.value = index === 0 ? "100.00" : "0.00";
        price.dispatchEvent(new Event("input", { bubbles: true }));
      });
      const margin = document.querySelector("#pcMargin");
      const vat = document.querySelector("#pcVat");
      if (!margin || !vat) throw new Error("PC Builder margin or VAT control is missing.");
      margin.value = "12.5";
      margin.dispatchEvent(new Event("input", { bubbles: true }));
      vat.value = "18";
      vat.dispatchEvent(new Event("change", { bubbles: true }));
      return {
        cost: document.querySelector("#pcCost")?.textContent.trim() || "",
        profit: document.querySelector("#pcProfit")?.textContent.trim() || "",
        vatAmount: document.querySelector("#pcVatAmount")?.textContent.trim() || "",
        grandTotal: document.querySelector("#pcGrand")?.textContent.trim() || "",
        margin: margin.value,
        vat: vat.value,
      };
    })()`);
    if (pricingCalculation.cost !== "200.00 \u20ba" || pricingCalculation.profit !== "+25.00 \u20ba" || pricingCalculation.vatAmount !== "40.50 \u20ba" || pricingCalculation.grandTotal !== "265.50 \u20ba" || pricingCalculation.margin !== "12.5" || pricingCalculation.vat !== "18") throw new Error("PC Builder margin/VAT total diverges from the desktop calculation: " + JSON.stringify(pricingCalculation));
    process.stdout.write(`${JSON.stringify({ state, responsiveWidths, visualGeometry, formFactorSelect, priceStepper, priceStepperInteraction1300, quantityRange, inlineSteppers, brandFilter, addComponent, presetCopy, search, customer360Registration, proforma, templateEditor, templateMobile, anonymousSave, customerSave, financeSave, saveFailure, actionFailures, stockDeduction, mobile, salesWorkflows, pricingCalculation, exceptions, screenshot: screenshotPath })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
    await new Promise(resolve => setTimeout(resolve, 300));
    if (path.dirname(profile) === tempRoot && path.basename(profile) === "profile" && path.dirname(tempRoot) === path.resolve(os.tmpdir()) && path.basename(tempRoot).startsWith("ayec-pc-builder-edge-")) {
      try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); } catch (_) {}
    }
  }
}

run().catch(error => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
