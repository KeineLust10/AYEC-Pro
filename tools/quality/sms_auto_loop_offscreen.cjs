const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 30000 + (process.pid % 10000));
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `sms-loop-headless-profile-${process.pid}`);
const loopKeys = ["repaired", "approval", "parts", "testing", "done"];

function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function waitForTarget() {
  const endpoint = `http://127.0.0.1:${debugPort}/json`;
  for (let attempt = 0; attempt < 100; attempt += 1) {
    try {
      const response = await fetch(endpoint);
      const targets = await response.json();
      const origin = new URL(baseUrl).origin;
      const page = targets.find(target => target.type === "page" && target.url?.startsWith(origin));
      if (page?.webSocketDebuggerUrl) return page;
    } catch (_) {}
    await delay(200);
  }
  throw new Error("Headless Edge did not expose the local AYEC page.");
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
    "--window-size=1280,900", baseUrl
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
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message)); else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 30000);
      pending.set(id, {
        resolve(value) { clearTimeout(timer); resolve(value); },
        reject(error) { clearTimeout(timer); reject(error); }
      });
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
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof render === 'function' && typeof renderPart9SmsProvider === 'function' && typeof desktopSettings !== 'undefined' && typeof desktopWrite === 'function'");
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("SMS settings UI did not initialize.");

    const initial = await evaluate(`(() => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      page = "settings";
      settingsSection = "sms-settings";
      currentAuthUser = { role: "Admin" };
      const keys = ["repaired", "approval", "parts", "testing", "done"];
      desktopSettings = { sms_username: "fixture-user", sms_password: "", sms_title: "AYEC", sms_active: "1" };
      keys.forEach((key, index) => {
        desktopSettings["loop_" + key] = ["3", "1", "2", "1", "0"][index];
        desktopSettings["loop_active_" + key] = "1";
        desktopSettings["loop_template_" + key] = "Template " + (index + 1);
      });
      window.__smsLoopWrites = [];
      apiFetch = async url => {
        if (url.startsWith("/api/desktop/table/whatsapp_templates")) return { rows: keys.map((_key, index) => ({ name: "Template " + (index + 1) })) };
        throw new Error("Unexpected SMS settings request: " + url);
      };
      desktopWrite = async (table, payload) => { window.__smsLoopWrites.push({ table, ...payload }); desktopSettings[payload.key] = payload.value; return { ok: true }; };
      render();
      return { page, settingsSection, title: document.querySelector(".p9-sms-provider-title h3")?.textContent || "", cards: document.querySelectorAll(".p9-sms-loop").length };
    })()`);
    await delay(100);
    const result = await evaluate(`(async () => {
      const root = document.querySelector(".p9-sms-provider");
      const cards = [...root.querySelectorAll(".p9-sms-loop")];
      const keys = ["repaired", "approval", "parts", "testing", "done"];
      const cardState = cards.map((card, index) => ({
        key: keys[index],
        label: card.querySelector("header strong")?.textContent.trim() || "",
        active: Boolean(card.querySelector('[data-setting-key="loop_active_' + keys[index] + '"]')?.checked),
        interval: card.querySelector('[data-setting-key="loop_' + keys[index] + '"]')?.value || "",
        template: card.querySelector('[data-setting-key="loop_template_' + keys[index] + '"]')?.value || "",
        options: card.querySelectorAll('[data-setting-key="loop_template_' + keys[index] + '"] option').length
      }));
      const repaired = cards[0];
      repaired.querySelector('[data-setting-key="loop_repaired"]').value = "5";
      repaired.querySelector('[data-setting-key="loop_active_repaired"]').checked = false;
      repaired.querySelector('[data-setting-key="loop_template_repaired"]').value = "Template 4";
      repaired.querySelector("[data-p9-sms-quick-save]").click();
      await new Promise(resolve => setTimeout(resolve, 0));
      const writes = window.__smsLoopWrites;
      const saved = {
        interval: desktopSettings.loop_repaired,
        active: desktopSettings.loop_active_repaired,
        template: desktopSettings.loop_template_repaired
      };
      render();
      const reloaded = {
        interval: document.querySelector('[data-setting-key="loop_repaired"]')?.value || "",
        active: Boolean(document.querySelector('[data-setting-key="loop_active_repaired"]')?.checked),
        template: document.querySelector('[data-setting-key="loop_template_repaired"]')?.value || ""
      };
      return { cardState, writes, saved, reloaded, screenshotReady: Boolean(document.querySelector(".p9-sms-provider")) };
    })()`);
    if (initial.cards !== 5 || result.cardState.length !== 5 || result.cardState.some(item => !item.active || !item.interval || !item.template || item.options < 2)) {
      throw new Error(`SMS loop cards or template options mismatch: ${JSON.stringify({ initial, result })}`);
    }
    const expectedWrites = ["loop_active_repaired", "loop_repaired", "loop_template_repaired"];
    if (JSON.stringify(result.writes.map(item => item.key)) !== JSON.stringify(expectedWrites) || result.saved.interval !== "5" || result.saved.active !== "0" || result.saved.template !== "Template 4" || result.reloaded.interval !== "5" || result.reloaded.active || result.reloaded.template !== "Template 4") {
      throw new Error(`SMS loop save/reload mismatch: ${JSON.stringify(result)}`);
    }
    const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    const filename = path.join(outputDir, "sms-auto-loops-headless.png");
    fs.writeFileSync(filename, Buffer.from(screenshot.data, "base64"));
    if (exceptions.length) throw new Error(`Browser exceptions: ${JSON.stringify(exceptions)}`);
    process.stdout.write(`${JSON.stringify({ initial, ...result, browserExceptions: exceptions.length, screenshot: filename })}\n`);
  } finally {
    if (socket) socket.close();
    try { execFileSync("taskkill", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
