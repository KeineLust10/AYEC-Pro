const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  let statusReads = 0;
  await page.addInitScript(() => {
    window.__serverClipboard = "";
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (value) => { window.__serverClipboard = value; } } });
  });
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants: [] };
    else if (url.pathname === "/api/admin/server-status") { statusReads++; body = { version: "2.0.4", db_path: "C:/ayec/data/tenant_registry.db", cpu_percent: 32, ram_percent: 57, disk_percent: 41, disk_usage: "%41", tenant_count: 12, server_time: "2026-10-14T08:15:00+00:00" }; }
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "server-settings";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.waitForFunction(() => document.querySelectorAll(".admin-server-metric").length === 5);
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_server_settings_web_desktop.png", fullPage: true });
    const metrics = await page.evaluate(() => [...document.querySelectorAll(".admin-server-metric header b")].map(item => item.textContent));
    if (metrics.join(",") !== "32%,57%,41%,Veri yok,Veri yok" || await page.locator(".admin-server-maintenance button:not(:disabled)").count() !== 0) throw new Error(JSON.stringify({ metrics }));
    if (await page.locator(".admin-server-topology .admin-server-unavailable").count() !== 1) throw new Error("Unavailable replication data was not represented.");
    await page.locator("#serverCopyStatus").evaluate((element) => element.click());
    const copied = await page.evaluate(() => window.__serverClipboard);
    if (!copied.includes("tenant_count") || !copied.includes("12")) throw new Error("Copy status did not include server metrics.");
    const before = statusReads;
    await page.locator("#serverConnectionTest").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#serverConnectionTest")?.textContent === "API Erisimi Basarili");
    if (statusReads <= before) throw new Error("Connection check did not call server status API.");
    await page.locator("#serverStatusRefresh").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelectorAll(".admin-server-metric").length === 5 && document.querySelector("#serverStatusRefresh"));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: "#sidebar, #mobileOverlay { display: none !important; }" });
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_server_settings_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, metrics: getComputedStyle(document.querySelector(".admin-server-metrics")).gridTemplateColumns, layout: getComputedStyle(document.querySelector(".admin-server-layout")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1) throw new Error(JSON.stringify(mobile));
    return { metrics, copied: copied.length, statusReads, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
