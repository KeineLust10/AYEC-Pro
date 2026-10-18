const fs = require("node:fs");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");
const { pathToFileURL } = require("node:url");

const root = path.resolve(__dirname, "../..");
const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = 34000 + (process.pid % 10000);
const indexPath = path.join(root, "Web_Arayuzu", "web", "index.html");
const profile = path.join(root, "output", "playwright", `header-quick-action-profile-${process.pid}`);
const profileRoot = path.resolve(root, "output", "playwright");

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

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
  if (!fs.existsSync(edgePath)) throw new Error(`Microsoft Edge was not found at ${edgePath}`);
  if (!profile.startsWith(profileRoot + path.sep)) throw new Error("The browser profile path is outside the audit directory.");
  fs.mkdirSync(profileRoot, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new",
    "--disable-gpu",
    "--disable-cache",
    "--no-first-run",
    "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`,
    `--user-data-dir=${profile}`,
    "--window-size=1500,900",
    pathToFileURL(indexPath).href,
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    const target = await waitForTarget();
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
      if (message.method === "Runtime.exceptionThrown") {
        const details = message.params.exceptionDetails;
        const frame = details.stackTrace?.callFrames?.[0];
        exceptions.push({
          description: details.exception?.description || details.text,
          source: frame ? `${frame.url}:${frame.lineNumber + 1}` : "unknown",
        });
      }
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
      if (response.result?.subtype === "error") throw new Error(response.result.description);
      return response.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 900, deviceScaleFactor: 1, mobile: false });
    for (let attempt = 0; attempt < 80; attempt += 1) {
      if (await evaluate("document.readyState === 'complete' && document.querySelector('.topbar') && [...document.styleSheets].some(sheet => sheet.href && sheet.href.includes('desktop-parity.css'))")) break;
      await delay(100);
    }
    const shell = await evaluate(`(() => {
      document.documentElement.dataset.theme = "midnight";
      const pageHandlerAvailable = typeof handleAction === "function";
      return {
        globalQuickAddCount: document.querySelectorAll('.topbar [data-action="quick-add"]').length,
        dashboardPageHandlerAvailable: pageHandlerAvailable,
        desktopBackControl: Boolean(document.querySelector('#headerBackBtn')),
        desktopThemeControl: Boolean(document.querySelector('#headerThemePicker')),
        topbarHeight: document.querySelector('.topbar').getBoundingClientRect().height,
        shortcutsDisplay: getComputedStyle(document.querySelector('#headerShortcutsBtn')).display
      };
    })()`);
    if (shell.globalQuickAddCount !== 0 || !shell.dashboardPageHandlerAvailable || !shell.desktopBackControl || !shell.desktopThemeControl || shell.topbarHeight !== 70 || shell.shortcutsDisplay !== "flex") {
      throw new Error(`The web shell differs from the desktop header contract: ${JSON.stringify(shell)}`);
    }
    await evaluate("navigate('dashboard')");
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("document.body.dataset.page === 'dashboard' && document.querySelector('.dashboard-shortcut-overlay')")) break;
      await delay(50);
    }
    const shortcutsInitial = await evaluate("document.body.dataset.page === 'dashboard' && Boolean(document.querySelector('.dashboard-shortcut-overlay'))");
    await evaluate("document.querySelector('#headerShortcutsBtn').click()");
    const shortcutsClosed = await evaluate("document.body.dataset.page === 'dashboard' && !document.querySelector('.dashboard-shortcut-overlay')");
    await evaluate("document.querySelector('#headerShortcutsBtn').click()");
    const shortcutsReopened = await evaluate("document.body.dataset.page === 'dashboard' && Boolean(document.querySelector('.dashboard-shortcut-overlay'))");
    await send("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
    const shortcutsCompactHidden = await evaluate("getComputedStyle(document.querySelector('#headerShortcutsBtn')).display === 'none'");
    const topbarGeometry = await evaluate(`(() => Array.from(document.querySelectorAll('.app-shell>.topbar>*')).map(node => { const r=node.getBoundingClientRect(),s=getComputedStyle(node); return {id:node.id||'',className:typeof node.className==='string'?node.className:'',text:node.textContent.trim(),x:Math.round(r.x),width:Math.round(r.width),height:Math.round(r.height),display:s.display,children:node.classList.contains('top-actions')?Array.from(node.children).map(child=>{const b=child.getBoundingClientRect(),cs=getComputedStyle(child);return{id:child.id||'',className:typeof child.className==='string'?child.className:'',x:Math.round(b.x),width:Math.round(b.width),height:Math.round(b.height),display:cs.display};}):undefined}; }))()`);
    await evaluate("document.querySelector('#headerShortcutsBtn').click()");
    await evaluate("document.documentElement.dataset.theme = 'midnight'");
    await delay(50);
    const headerScreenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    const headerScreenshotPath = path.join(root, "output", "playwright", "web-shell-header-geometry-offscreen.png");
    fs.writeFileSync(headerScreenshotPath, Buffer.from(headerScreenshot.data, "base64"));
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 1, mobile: false });
    const mobileHeader = await evaluate(`(() => ({brandHidden: ['.header-app-logo','.header-brand-pro','.header-brand-separator','.header-app-name','.header-back'].every(selector=>{const element=document.querySelector(selector);return !element||getComputedStyle(element).display==='none'}), menuVisible:getComputedStyle(document.querySelector('#menuToggle')).display!=='none', topbarWidth:document.querySelector('.topbar').getBoundingClientRect().width, topbarScrollWidth:document.querySelector('.topbar').scrollWidth, viewportWidth:innerWidth}))()`);
    const mobileHeaderMatches = mobileHeader.brandHidden && mobileHeader.menuVisible && mobileHeader.topbarScrollWidth <= mobileHeader.viewportWidth;
    await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 900, deviceScaleFactor: 1, mobile: false });
    const logoBox = topbarGeometry.find(item => item.className === "header-app-logo");
    const backBox = topbarGeometry.find(item => item.id === "headerBackBtn");
    const brandIndex = topbarGeometry.findIndex(item => item.className === "header-brand-pro");
    const appName = topbarGeometry.find(item => item.className === "header-app-name");
    const navigationBox = topbarGeometry.find(item => item.className === "" && item.display === "flex");
    const actionBoxes = topbarGeometry.find(item => item.className === "top-actions")?.children || [];
    const syncBox = actionBoxes.find(item => item.id === "syncNowBtn");
    const settingsBox = actionBoxes.find(item => item.id === "headerSettingsBtn");
    const interfaceBox = actionBoxes.find(item => item.id === "interfaceEditBtn");
    const notificationBox = actionBoxes.find(item => item.id === "notificationBtn");
    const headerGeometryMatches = logoBox?.x === 92 && logoBox?.width === 10 && logoBox?.height === 20 && backBox?.x === 8 && backBox?.width === 80 && backBox?.height === 32 && (brandIndex < 0 || topbarGeometry[brandIndex]?.display === "none") && appName?.text === "AYEC Pro" && appName.x === 106 && appName.width === 64 && appName.height === 69 && appName.display === "flex" && navigationBox?.x === 174 && syncBox?.width === 26 && syncBox?.height === 26 && settingsBox?.width === 26 && settingsBox?.height === 26 && interfaceBox?.height === 26 && notificationBox?.width === 26 && notificationBox?.height === 26;
    if (!headerGeometryMatches) throw new Error(`The desktop brand/back header geometry differs: ${JSON.stringify(topbarGeometry)}`);
    await send("Emulation.setDeviceMetricsOverride", { width: 1500, height: 900, deviceScaleFactor: 1, mobile: false });
    if (!shortcutsInitial || !shortcutsClosed || !shortcutsReopened || !shortcutsCompactHidden) {
      throw new Error(`The desktop header shortcut toggle failed: ${JSON.stringify({ shortcutsInitial, shortcutsClosed, shortcutsReopened, shortcutsCompactHidden })}`);
    }
    await evaluate(`(() => {
      window.__assistantSpeechCalls = [];
      window.SpeechSynthesisUtterance = function (text) { this.text = text; this.lang = ""; };
      Object.defineProperty(window, "speechSynthesis", { configurable: true, value: { speak: utterance => window.__assistantSpeechCalls.push({ text: utterance.text, lang: utterance.lang }) } });
      window.__assistantLocalSpeechCalls = [];
      window.__assistantAudioPlays = [];
      window.URL.createObjectURL = () => "blob:assistant-fixture";
      window.URL.revokeObjectURL = () => {};
      window.Audio = function (url) { this.url = url; this.addEventListener = () => {}; this.play = async () => window.__assistantAudioPlays.push(url); };
      window.__voiceMicState = { requests: 0, tracksStopped: 0, contextClosed: false, constraints: [] };
      window.__browserNotifications = [];
      function FixtureNotification(title, options) { window.__browserNotifications.push({ title, options }); }
      FixtureNotification.permission = "granted";
      Object.defineProperty(window, "Notification", { configurable: true, value: FixtureNotification });
      Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: { getUserMedia: async constraints => {
        window.__voiceMicState.requests += 1;
        window.__voiceMicState.constraints.push(constraints);
        return { getTracks: () => [{ stop: () => { window.__voiceMicState.tracksStopped += 1; } }] };
      }, enumerateDevices: async () => [{ kind: "audioinput", deviceId: "browser-mic-1", label: "Fixture microphone" }] } });
      window.AudioContext = function () {
        this.state = "running";
        this.createAnalyser = () => ({ fftSize: 0, connect: () => {}, getFloatTimeDomainData: samples => samples.fill(0.05) });
        this.createMediaStreamSource = () => ({ connect: () => {} });
        this.close = async () => { this.state = "closed"; window.__voiceMicState.contextClosed = true; };
      };
      const nativeFetch = window.fetch.bind(window);
      window.fetch = async (url, options = {}) => {
        if (url === "/api/desktop/assistant/speech") {
          window.__assistantLocalSpeechCalls.push({ url, method: options.method, payload: JSON.parse(options.body || "{}") });
          return { ok: true, blob: async () => new Blob(["fixture wav"], { type: "audio/wav" }) };
        }
        return nativeFetch(url, options);
      };
      window.__assistantApiCalls = [];
      window.__scheduledAlertWrites = [];
      window.__headerSettingsWrites = [];
      window.apiFetch = async (url, options = {}) => {
        const payload = JSON.parse(options.body || "{}");
        if (url === "/api/desktop/assistant/query") window.__assistantApiCalls.push({ url, method: options.method, payload });
        if (url === "/api/desktop/table/scheduled_alerts") window.__scheduledAlertWrites.push({ url, method: options.method, payload });
        if (url === "/api/desktop/table/settings") window.__headerSettingsWrites.push({ url, method: options.method, payload });
        if (url === "/api/desktop/assistant/query" && payload.question === "error query") return { success: false, error: "Assistant service unavailable." };
        return { success: true, answer: "Fixture AI response", rows: [] };
      };
      if (typeof db !== "undefined") db.settings.asistan_voice_enabled = "1";
      return true;
    })()`);
    const headerThemeFlow = await evaluate(`(async () => {
      const picker = document.querySelector('#headerThemePicker');
      picker.value = 'forest';
      picker.dispatchEvent(new Event('change', { bubbles: true }));
      const changed = { theme: document.documentElement.dataset.theme, picker: picker.value, saved: db.settings.theme };
      picker.value = 'midnight';
      picker.dispatchEvent(new Event('change', { bubbles: true }));
      await new Promise(resolve => setTimeout(resolve, 0));
      return { changed, restored: document.documentElement.dataset.theme, writes: window.__headerSettingsWrites };
    })()`);
    if (headerThemeFlow.changed.theme !== "forest" || headerThemeFlow.changed.picker !== "forest" || headerThemeFlow.changed.saved !== "forest" || headerThemeFlow.restored !== "midnight" || headerThemeFlow.writes.length !== 2 || headerThemeFlow.writes.some(write => write.method !== "POST" || write.payload.key !== "web_theme") || headerThemeFlow.writes[0].payload.value !== "forest" || headerThemeFlow.writes[1].payload.value !== "midnight") {
      throw new Error(`The header theme control did not apply and persist its selection: ${JSON.stringify(headerThemeFlow)}`);
    }
    await evaluate("document.querySelector('#assistantHeaderBtn').click()");
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("document.querySelector('#desktopAssistantPanel:not([hidden]) .desktop-assistant-messages .desktop-assistant-message')")) break;
      await delay(50);
    }
    const panelOpen = await evaluate(`(() => ({
      visible: Boolean(document.querySelector('#desktopAssistantPanel:not([hidden])')),
      heading: document.querySelector('#desktopAssistantPanel .desktop-assistant-head strong')?.textContent,
      assistantButtonExpanded: document.querySelector('#assistantHeaderBtn')?.getAttribute('aria-expanded'),
      assistantButtonLabel: document.querySelector('#assistantHeaderBtn')?.textContent.trim(),
      bounds: (() => { const rect = document.querySelector('#desktopAssistantPanel').getBoundingClientRect(); return [Math.round(rect.x), Math.round(rect.y), Math.round(rect.width), Math.round(rect.height)]; })()
    }))()`);
    if (!panelOpen.visible || panelOpen.heading !== "AYEC Pro" || panelOpen.assistantButtonExpanded !== "true" || panelOpen.assistantButtonLabel !== String.fromCodePoint(0x1f916) || panelOpen.bounds[2] !== 450 || panelOpen.bounds[3] !== 700) {
      throw new Error(`The assistant panel did not open from the desktop header control: ${JSON.stringify(panelOpen)}`);
    }
    const dragged = await evaluate(`(() => {
      const header = document.querySelector('#desktopAssistantPanel .desktop-assistant-head');
      const rect = header.getBoundingClientRect();
      const startX = rect.left + 30;
      const startY = rect.top + 30;
      header.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, pointerId: 7, button: 0, clientX: startX, clientY: startY }));
      document.dispatchEvent(new PointerEvent('pointermove', { bubbles: true, pointerId: 7, clientX: startX - 120, clientY: startY - 40 }));
      document.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 7, clientX: startX - 120, clientY: startY - 40 }));
      const panelRect = document.querySelector('#desktopAssistantPanel').getBoundingClientRect();
      return [Math.round(panelRect.x), Math.round(panelRect.y)];
    })()`);
    if (JSON.stringify(dragged) !== JSON.stringify([panelOpen.bounds[0] - 120, panelOpen.bounds[1] - 40])) {
      throw new Error(`The assistant panel did not follow the desktop drag interaction: ${JSON.stringify({ panelOpen, dragged })}`);
    }
    await evaluate(`(() => {
      const input = document.querySelector('#desktopAssistantInput');
      input.value = 'finans ozeti';
      document.querySelector('.desktop-assistant-compose').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("document.body.dataset.page === 'finance' && document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message').length >= 3")) break;
      await delay(50);
    }
    const action = await evaluate(`(() => ({
      route: document.body.dataset.page,
      reply: [...document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message.is-assistant')].map(node => node.textContent).at(-1),
      panelVisible: !document.querySelector('#desktopAssistantPanel').hidden
    }))()`);
    if (action.route !== "finance" || action.reply !== "Finansal \u00f6zeti a\u00e7\u0131yorum." || !action.panelVisible || exceptions.length) {
      throw new Error(`The assistant financial-summary action failed: ${JSON.stringify({ action, exceptions })}`);
    }
    const spoken = await evaluate("({ local: window.__assistantLocalSpeechCalls, fallback: window.__assistantSpeechCalls, plays: window.__assistantAudioPlays })");
    if (spoken.local.length !== 1 || spoken.local[0].url !== "/api/desktop/assistant/speech" || spoken.local[0].payload.text !== action.reply || spoken.fallback.length !== 0 || spoken.plays.length !== 1) {
      throw new Error(`The assistant local voice reply did not match the desktop setting: ${JSON.stringify(spoken)}`);
    }
    await evaluate(`(() => {
      if (typeof db !== "undefined") db.settings.asistan_voice_enabled = "0";
      const input = document.querySelector('#desktopAssistantInput');
      input.value = 'merhaba';
      document.querySelector('.desktop-assistant-compose').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message').length >= 5")) break;
      await delay(50);
    }
    const apiQuery = await evaluate(`(() => ({
      reply: [...document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message.is-assistant')].map(node => node.textContent).at(-1),
      speechCallCount: window.__assistantSpeechCalls.length,
      localSpeechCallCount: window.__assistantLocalSpeechCalls.length,
      audioPlayCount: window.__assistantAudioPlays.length,
      calls: window.__assistantApiCalls
    }))()`);
    if (apiQuery.reply !== "Fixture AI response" || apiQuery.speechCallCount !== 0 || apiQuery.localSpeechCallCount !== 1 || apiQuery.audioPlayCount !== 1 || apiQuery.calls.length !== 1 || apiQuery.calls[0].url !== "/api/desktop/assistant/query" || apiQuery.calls[0].method !== "POST" || apiQuery.calls[0].payload.question !== "merhaba") {
      throw new Error(`The assistant API or voice-off setting failed: ${JSON.stringify(apiQuery)}`);
    }
    await evaluate(`(() => {
      const input = document.querySelector('#desktopAssistantInput');
      input.value = 'error query';
      document.querySelector('.desktop-assistant-compose').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message').length >= 7")) break;
      await delay(50);
    }
    const apiFailure = await evaluate(`(() => ({
      reply: [...document.querySelectorAll('#desktopAssistantPanel .desktop-assistant-message.is-assistant')].map(node => node.textContent).at(-1),
      speechCallCount: window.__assistantSpeechCalls.length,
      queryCount: window.__assistantApiCalls.length
    }))()`);
    if (apiFailure.reply !== "Hata: Assistant service unavailable." || apiFailure.speechCallCount !== 0 || apiFailure.queryCount !== 2) {
      throw new Error(`The assistant API error state failed: ${JSON.stringify(apiFailure)}`);
    }
    await evaluate(`scheduledAlerts = [
      { id: 1, alert_type: 'loan_reminder', trigger_time: '11:00', is_enabled: 1 },
      { id: 2, alert_type: 'check_reminder', trigger_time: '11:30', is_enabled: 1 },
      { id: 3, alert_type: 'stock_critical', trigger_time: '15:00', is_enabled: 1 },
      { id: 4, alert_type: 'service_delivery', trigger_time: '17:30', is_enabled: 0 }
    ]; true`);
    await evaluate("settingsSection = 'voice-settings'; navigate('settings')");
    const scheduledAlertParity = await evaluate(`(() => {
      const serviceRow = [...document.querySelectorAll('.voice-reminder-row')].find(row => row.querySelector('[data-voice-alert="service_delivery"]'));
      return {
        count: document.querySelectorAll('.voice-reminder-row').length,
        serviceTime: serviceRow?.querySelector('.voice-reminder-time')?.value,
        serviceEnabled: serviceRow?.querySelector('[data-voice-alert]')?.checked
      };
    })()`);
    if (scheduledAlertParity.count !== 4 || scheduledAlertParity.serviceTime !== "17:30" || scheduledAlertParity.serviceEnabled !== false) {
      throw new Error(`The desktop scheduled-alert settings did not render accurately: ${JSON.stringify(scheduledAlertParity)}`);
    }
    await evaluate(`(() => {
      const serviceRow = [...document.querySelectorAll('.voice-reminder-row')].find(row => row.querySelector('[data-voice-alert="service_delivery"]'));
      const time = serviceRow.querySelector('[data-voice-alert-time]');
      const toggle = serviceRow.querySelector('[data-voice-alert]');
      time.value = '17:45';
      time.dispatchEvent(new Event('change', { bubbles: true }));
      toggle.checked = true;
      toggle.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("window.__scheduledAlertWrites.length >= 2 && !document.querySelector('[data-voice-alert-time=service_delivery]')?.disabled && !document.querySelector('[data-voice-alert=service_delivery]')?.disabled")) break;
      await delay(50);
    }
    const scheduledAlertEdit = await evaluate("({ alert: scheduledAlerts.find(item => item.alert_type === 'service_delivery'), writes: window.__scheduledAlertWrites })");
    if (scheduledAlertEdit.alert.trigger_time !== "17:45" || Number(scheduledAlertEdit.alert.is_enabled) !== 1 || scheduledAlertEdit.writes.length !== 2 || scheduledAlertEdit.writes[0].payload.trigger_time !== "17:45" || scheduledAlertEdit.writes[1].payload.is_enabled !== 1) {
      throw new Error(`The scheduled alert time/toggle edits did not persist: ${JSON.stringify(scheduledAlertEdit)}`);
    }
    await evaluate("document.querySelector('[data-voice-speech-preview]')?.click()");
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("window.__assistantAudioPlays.length >= 2")) break;
      await delay(50);
    }
    const voicePreview = await evaluate(`(() => ({
      present: Boolean(document.querySelector('[data-voice-speech-preview]')),
      calls: window.__assistantLocalSpeechCalls,
      playCount: window.__assistantAudioPlays.length,
      enabled: !document.querySelector('[data-voice-speech-preview]')?.disabled,
      page: document.body.dataset.page,
      settingsSection,
      title: document.querySelector('#pageTitle')?.textContent
    }))()`);
    if (!voicePreview.present || voicePreview.calls.length !== 2 || voicePreview.calls[1].payload.text !== "AYEC ses testi, Efendim,." || voicePreview.playCount !== 2 || !voicePreview.enabled) {
      throw new Error(`The voice settings local EMA preview failed: ${JSON.stringify(voicePreview)}`);
    }
    await evaluate("document.querySelector('[data-voice-reminder-settings]')?.click()");
    const reminderSettings = await evaluate("({ section: settingsSection, visible: Boolean(document.querySelector('.voice-shortcuts-page')) })");
    if (reminderSettings.section !== "voice-shortcuts" || !reminderSettings.visible) {
      throw new Error(`The voice reminder scenario shortcut did not open its web editor: ${JSON.stringify(reminderSettings)}`);
    }
    await evaluate("settingsSection = 'voice-settings'; navigate('settings')");
    await evaluate("document.querySelector('[data-voice-microphone-test]')?.click()");
    for (let attempt = 0; attempt < 45; attempt += 1) {
      if (await evaluate("!document.querySelector('[data-voice-microphone-test]')?.disabled")) break;
      await delay(50);
    }
    const microphoneTest = await evaluate(`(() => ({
      present: Boolean(document.querySelector('[data-voice-microphone-test]')),
      enabled: !document.querySelector('[data-voice-microphone-test]')?.disabled,
      state: window.__voiceMicState,
      options: document.querySelectorAll('#voiceBrowserInputDevice option').length
    }))()`);
    if (!microphoneTest.present || !microphoneTest.enabled || microphoneTest.state.requests !== 1 || microphoneTest.state.tracksStopped !== 1 || !microphoneTest.state.contextClosed || microphoneTest.options !== 2) {
      throw new Error(`The voice settings microphone test failed or left capture active: ${JSON.stringify(microphoneTest)}`);
    }
    await evaluate(`(() => {
      const select = document.querySelector('#voiceBrowserInputDevice');
      select.value = 'browser-mic-1';
      select.dispatchEvent(new Event('change', { bubbles: true }));
      document.querySelector('[data-voice-microphone-test]').click();
      return true;
    })()`);
    for (let attempt = 0; attempt < 45; attempt += 1) {
      if (await evaluate("window.__voiceMicState.requests >= 2 && !document.querySelector('[data-voice-microphone-test]')?.disabled")) break;
      await delay(50);
    }
    const selectedMicrophoneTest = await evaluate("({ state: window.__voiceMicState, savedDevice: localStorage.getItem('ayec.web.voice.input-device') })");
    if (selectedMicrophoneTest.state.requests !== 2 || selectedMicrophoneTest.state.tracksStopped !== 2 || !selectedMicrophoneTest.state.contextClosed || JSON.stringify(selectedMicrophoneTest.state.constraints[1]) !== JSON.stringify({ audio: { deviceId: { exact: 'browser-mic-1' } } }) || selectedMicrophoneTest.savedDevice !== 'browser-mic-1') {
      throw new Error(`The selected browser microphone was not used and cleaned up: ${JSON.stringify(selectedMicrophoneTest)}`);
    }
    await evaluate(`(() => {
      desktopSettings.quiet_hours_start = '19:00';
      desktopSettings.quiet_hours_end = '08:30';
      desktopInternalSettings.feature_scheduled_alerts_active = '1';
      desktopInternalSettings.feature_voice_alerts_active = '1';
      window.__scheduledAlertWrites.length = 0;
      scheduledAlerts = [{ id: 8, alert_type: 'stock_critical', trigger_time: '20:15', is_enabled: 1, is_critical: 0 }];
      window.__scheduledAlertBase = { toastCount: notifications.length, speechCount: window.__assistantLocalSpeechCalls.length, audioCount: window.__assistantAudioPlays.length, notificationCount: window.__browserNotifications.length };
      checkScheduledAlerts(new Date(2026, 0, 1, 20, 15));
      window.__scheduledQuietResult = { toastCount: notifications.length, speechCount: window.__assistantLocalSpeechCalls.length, audioCount: window.__assistantAudioPlays.length, notificationCount: window.__browserNotifications.length };
      scheduledAlerts = [{ id: 9, alert_type: 'loan_reminder', trigger_time: '11:00', is_enabled: 1, is_critical: 0 }];
      checkScheduledAlerts(new Date(2026, 0, 1, 11, 0));
      const savedTrigger = scheduledAlerts[0].last_triggered;
      scheduledAlerts = [{ id: 9, alert_type: 'loan_reminder', trigger_time: '11:00', is_enabled: 1, is_critical: 0, last_triggered: savedTrigger }];
      checkScheduledAlerts(new Date(2026, 0, 1, 11, 0));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("window.__assistantLocalSpeechCalls.length >= 3 && window.__assistantAudioPlays.length >= 3")) break;
      await delay(50);
    }
    const scheduledAlertQuietAndActive = await evaluate(`({
      base: window.__scheduledAlertBase,
      quiet: window.__scheduledQuietResult,
      afterActive: { speechCount: window.__assistantLocalSpeechCalls.length, audioCount: window.__assistantAudioPlays.length, notificationCount: window.__browserNotifications.length, writes: window.__scheduledAlertWrites }
    })`);
    if (scheduledAlertQuietAndActive.quiet.toastCount !== scheduledAlertQuietAndActive.base.toastCount + 1 || scheduledAlertQuietAndActive.quiet.speechCount !== scheduledAlertQuietAndActive.base.speechCount || scheduledAlertQuietAndActive.quiet.audioCount !== scheduledAlertQuietAndActive.base.audioCount || scheduledAlertQuietAndActive.quiet.notificationCount !== scheduledAlertQuietAndActive.base.notificationCount || scheduledAlertQuietAndActive.afterActive.speechCount !== scheduledAlertQuietAndActive.base.speechCount + 1 || scheduledAlertQuietAndActive.afterActive.audioCount !== scheduledAlertQuietAndActive.base.audioCount + 1 || scheduledAlertQuietAndActive.afterActive.notificationCount !== scheduledAlertQuietAndActive.base.notificationCount + 1 || scheduledAlertQuietAndActive.afterActive.writes.length !== 2 || scheduledAlertQuietAndActive.afterActive.writes[1].payload.last_triggered !== "2026-01-01T11:00:00") {
      throw new Error(`The quiet-hour or active voice-alert behavior diverged: ${JSON.stringify(scheduledAlertQuietAndActive)}`);
    }
    await evaluate(`(() => {
      scheduledAlerts = [{ id: 10, alert_type: 'service_delivery', trigger_time: '20:16', is_enabled: 1, is_critical: 1 }];
      checkScheduledAlerts(new Date(2026, 0, 1, 20, 16));
      return true;
    })()`);
    for (let attempt = 0; attempt < 40; attempt += 1) {
      if (await evaluate("window.__assistantLocalSpeechCalls.length >= 4 && window.__assistantAudioPlays.length >= 4")) break;
      await delay(50);
    }
    const criticalAlert = await evaluate("({ speechCount: window.__assistantLocalSpeechCalls.length, audioCount: window.__assistantAudioPlays.length, notificationCount: window.__browserNotifications.length })");
    if (criticalAlert.speechCount !== 4 || criticalAlert.audioCount !== 4 || criticalAlert.notificationCount !== scheduledAlertQuietAndActive.afterActive.notificationCount + 1) {
      throw new Error(`The critical alert did not bypass quiet hours: ${JSON.stringify(criticalAlert)}`);
    }
    await evaluate(`(() => {
      desktopInternalSettings.feature_voice_alerts_active = '0';
      scheduledAlerts = [{ id: 11, alert_type: 'check_reminder', trigger_time: '11:01', is_enabled: 1, is_critical: 0 }];
      window.__voiceDisabledToastBase = notifications.length;
      checkScheduledAlerts(new Date(2026, 0, 1, 11, 1));
      window.__voiceDisabledToastCount = notifications.length;
      desktopInternalSettings.feature_scheduled_alerts_active = '0';
      scheduledAlerts = [{ id: 12, alert_type: 'check_reminder', trigger_time: '11:02', is_enabled: 1, is_critical: 0 }];
      checkScheduledAlerts(new Date(2026, 0, 1, 11, 2));
      return true;
    })()`);
    const scheduledFeatureGates = await evaluate("({ speechCount: window.__assistantLocalSpeechCalls.length, audioCount: window.__assistantAudioPlays.length, notificationCount: window.__browserNotifications.length, writeCount: window.__scheduledAlertWrites.length, voiceDisabledToastDelta: window.__voiceDisabledToastCount - window.__voiceDisabledToastBase, allDisabledToastDelta: notifications.length - window.__voiceDisabledToastCount })");
    if (scheduledFeatureGates.speechCount !== 4 || scheduledFeatureGates.audioCount !== 4 || scheduledFeatureGates.notificationCount !== criticalAlert.notificationCount || scheduledFeatureGates.writeCount !== 4 || scheduledFeatureGates.voiceDisabledToastDelta !== 1 || scheduledFeatureGates.allDisabledToastDelta !== 0) {
      throw new Error(`The scheduled-alert feature gates failed: ${JSON.stringify(scheduledFeatureGates)}`);
    }
    await evaluate("document.querySelector('#desktopAssistantInput').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))");
    const closed = await evaluate("document.querySelector('#desktopAssistantPanel').hidden && document.querySelector('#assistantHeaderBtn').getAttribute('aria-expanded') === 'false'");
    if (!closed) throw new Error("Escape did not close the assistant panel.");
    await delay(100);
    if (exceptions.length) throw new Error(`The browser reported exceptions: ${JSON.stringify(exceptions)}`);
    if (!mobileHeaderMatches) throw new Error(`The compact header overflowed or retained desktop branding: ${JSON.stringify(mobileHeader)}`);
    const result = { shell, shortcutsInitial, shortcutsClosed, shortcutsReopened, shortcutsCompactHidden, topbarGeometry, headerGeometryMatches, headerThemeFlow, mobileHeader, headerScreenshotPath, panelOpen, dragged, action, spoken, apiQuery, apiFailure, closed, exceptions, headless: true };
    result.reportPath = path.join(root, "output", "playwright", "desktop-header-visual-audit-result-20261018.json");
    fs.writeFileSync(result.reportPath, JSON.stringify(result, null, 2) + "\n", "utf8");
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } finally {
    if (socket && socket.readyState === WebSocket.OPEN) socket.close();
    if (browser.pid) {
      spawnSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      if (browser.exitCode === null) {
        await Promise.race([
          new Promise(resolve => browser.once("exit", resolve)),
          delay(2000),
        ]);
      }
    }
    for (let attempt = 0; attempt < 5 && fs.existsSync(profile); attempt += 1) {
      try {
        fs.rmSync(profile, { recursive: true, force: true });
      } catch (error) {
        if (attempt === 4) throw error;
        await delay(500);
      }
    }
  }
}

run().catch(error => {
  process.stderr.write(`${error.stack || error.message}\n`);
  process.exitCode = 1;
});
