const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const logs = [
    { id: 81, level: "ERROR", tenant_id: "tenant-a", version: "2.0.1", os_info: "Windows 11", error_message: "sqlite3.OperationalError: database is locked", stack_trace: "File main.py, line 318\n  raise OperationalError()", created_at: "2026-10-14 08:05:12" },
    { id: 82, level: "WARNING", resolved: true, tenant_id: "tenant-b", version: "2.0.0", os_info: "Windows 10", error_message: "WhatsAppApiTimeout", stack_trace: "", created_at: "2026-10-14 07:58:39" },
  ];
  let reads = 0;
  await page.addInitScript(() => {
    window.__telemetryCopied = "";
    Object.defineProperty(navigator, "clipboard", { configurable: true, value: { writeText: async (text) => { window.__telemetryCopied = text; } } });
  });
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants: [{ id: "tenant-a", company_name: "ASLAN TIC", active: 1 }, { id: "tenant-b", company_name: "Babali Servis", active: 1 }] };
    else if (url.pathname === "/api/control/telemetry/errors") { reads++; body = { ok: true, logs, stability_percent: 98.5, handled_count: 14 }; }
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "telemetry";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.waitForFunction(() => document.querySelectorAll("[data-telemetry-row]").length === 2);
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_error_telemetry_web_desktop.png", fullPage: true });
    const summary = await page.evaluate(() => ({ total: document.querySelector("#adminTelemetryTotal").textContent, stack: document.querySelector("#adminTelemetryStackCount").textContent, tenants: document.querySelector("#adminTelemetryTenantCount").textContent }));
    await page.locator('[data-telemetry-filter="warning"]').evaluate((element) => element.click());
    const stackRows = await page.locator("[data-telemetry-row]").count();
    if (stackRows !== 1 || summary.total !== "0" || summary.stack !== "1" || summary.tenants !== "14") throw new Error(JSON.stringify({ summary, stackRows }));
    await page.locator('[data-telemetry-filter="all"]').evaluate((element) => element.click());
    await page.locator("#adminTelemetryCompany").selectOption("tenant-b");
    const companyRows = await page.locator("[data-telemetry-row]").count();
    await page.locator("#adminTelemetryCompany").selectOption("");
    await page.evaluate(() => { const input = document.querySelector("#adminTelemetrySearch"); input.value = "OperationalError"; input.dispatchEvent(new Event("input", { bubbles: true })); });
    const searchRows = await page.locator("[data-telemetry-row]").count();
    await page.evaluate(() => { const input = document.querySelector("#adminTelemetrySearch"); input.value = ""; input.dispatchEvent(new Event("input", { bubbles: true })); });
    if (companyRows !== 1 || searchRows !== 1) throw new Error(JSON.stringify({ companyRows, searchRows }));
    await page.locator('[data-view-trace="82"]').evaluate((element) => element.click());
    const selected = await page.evaluate(() => document.querySelector(".admin-error-detail h3")?.textContent);
    if (selected !== "WhatsAppApiTimeout" || await page.locator("#adminTelemetryDetail button:disabled").count() !== 2) throw new Error(JSON.stringify({ selected }));
    await page.locator('[data-view-trace="81"]').evaluate((element) => element.click());
    await page.locator("#adminTelemetryCopy").evaluate((element) => element.click());
    const copied = await page.evaluate(() => window.__telemetryCopied);
    if (!copied.includes("OperationalError") || !copied.includes("line 318")) throw new Error("Copy action did not use the selected stack trace.");
    const downloadEvent = page.waitForEvent("download");
    await page.locator("#adminTelemetryExport").evaluate((element) => element.click());
    const download = await downloadEvent;
    if (download.suggestedFilename() !== "admin-telemetry.csv") throw new Error(download.suggestedFilename());
    await page.locator("#adminTelemetryPause").evaluate((element) => element.click());
    if (await page.locator("#adminTelemetryPause").innerText() !== "Canl\u0131 Ak\u0131\u015f\u0131 S\xfcrd\xfcr") throw new Error("Polling pause control did not switch state.");
    const beforeRefresh = reads;
    await page.locator("#adminTelemetryRefresh").evaluate((element) => element.click());
    await page.waitForTimeout(100);
    if (reads <= beforeRefresh) throw new Error("Refresh did not call the telemetry API.");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_error_telemetry_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-error-metrics")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1) throw new Error(JSON.stringify(mobile));
    return { summary, stackRows, companyRows, searchRows, selected, csv: download.suggestedFilename(), reads, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
