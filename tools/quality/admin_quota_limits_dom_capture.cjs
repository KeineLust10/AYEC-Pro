const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.addInitScript(() => {
    window.__quotaDownload = null;
    window.__quotaScrollTarget = null;
    HTMLAnchorElement.prototype.click = function () { if (this.download) window.__quotaDownload = { name: this.download, href: this.href }; };
    HTMLElement.prototype.scrollIntoView = function () { window.__quotaScrollTarget = this.id; };
  });
  const usage = [
    { tenant_id: "tenant-a", company_name: "ASLAN TIC", db_size_mb: 12.5, users_count: 4, users_limit: 10, devices_count: 8, devices_limit: 100, services_count: 125, services_limit: 1000 },
    { tenant_id: "tenant-b", company_name: "Babali Servis", db_size_mb: 2.1, users_count: 2, users_limit: 10, devices_count: 3, devices_limit: 100, services_count: 45, services_limit: 1000 },
  ];
  let reads = 0;
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants: [] };
    else if (url.pathname === "/api/admin/licenses/usage") { reads++; body = { usages: usage }; }
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "quota-limits";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.waitForFunction(() => document.querySelectorAll("[data-quota-row]").length === 2);
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_quota_limits_web_desktop.png", fullPage: true });
    const summary = await page.evaluate(() => ({ tenants: document.querySelector("#quotaCount")?.textContent, users: document.querySelectorAll("[data-quota-row]")[0]?.children[2]?.querySelector("b")?.textContent }));
    const upgradeState = await page.evaluate(() => ({ message: document.querySelector(".admin-quota-upgrade header p")?.textContent, prices: document.querySelectorAll(".admin-quota-upgrade-options strong").length, disabledOptions: [...document.querySelectorAll(".admin-quota-upgrade-options input")].filter((input) => input.disabled).length, button: document.querySelector(".admin-quota-upgrade footer button")?.textContent }));
    if (!upgradeState.message.includes("merkezi katalog") || upgradeState.prices !== 0 || upgradeState.disabledOptions !== 3 || upgradeState.button !== "Desteklenmiyor") throw new Error(JSON.stringify(upgradeState));
    await page.evaluate(() => { const input = document.querySelector("#quotaSearch"); input.value = "Babali"; input.dispatchEvent(new Event("input", { bubbles: true })); });
    const filteredState = await page.evaluate(() => ({ value: document.querySelector("#quotaSearch").value, count: document.querySelector("#quotaCount").textContent, rows: [...document.querySelectorAll("[data-quota-row]")].map((row) => ({ company: row.dataset.company, hidden: row.hidden })) }));
    const filtered = filteredState.rows.filter((row) => !row.hidden).length;
    await page.evaluate(() => { const input = document.querySelector("#quotaSearch"); input.value = ""; input.dispatchEvent(new Event("input", { bubbles: true })); });
    if (filtered !== 1 || summary.tenants !== "2 / 2 tenant" || summary.users !== "4 / 10 Koltuk") throw new Error(JSON.stringify({ summary, filteredState, filtered }));
    await page.locator('[data-quota-upgrade="tenant-b"]').evaluate((element) => element.click());
    const selectedFromRow = await page.evaluate(() => ({ tenant: document.querySelector("#quotaUpgradeTenant").value, focused: document.activeElement?.id, tag: document.activeElement?.tagName }));
    if (selectedFromRow.tenant !== "tenant-b") throw new Error(JSON.stringify(selectedFromRow));
    const headerReadsBefore = reads;
    await page.evaluate(() => { const select = document.querySelector("#quotaUpgradeTenant"); window.__quotaSelectNode = select; window.__quotaSelectChanges = []; select.addEventListener("change", () => window.__quotaSelectChanges.push(select.value)); });
    await page.locator("#quotaPlan").evaluate((element) => element.click());
    const headerAction = await page.evaluate(() => ({ target: window.__quotaScrollTarget, tenant: document.querySelector("#quotaUpgradeTenant").value, sameElement: window.__quotaSelectNode === document.querySelector("#quotaUpgradeTenant"), changes: window.__quotaSelectChanges }));
    headerAction.reads = reads - headerReadsBefore;
    if (headerAction.target !== "quotaUpgradeTenant" || headerAction.tenant !== "tenant-b" || headerAction.sameElement !== false || headerAction.reads < 1) throw new Error(JSON.stringify(headerAction));
    if (await page.locator(".admin-quota-table-card button:disabled").count() !== 2) throw new Error("Unsupported quota mutation action must remain unavailable.");
    await page.locator("#quotaCsv").evaluate((element) => element.click());
    const download = await page.evaluate(() => window.__quotaDownload);
    if (download?.name !== "admin-tenant-quotas.csv" || !download.href.startsWith("blob:")) throw new Error(JSON.stringify(download));
    const before = reads;
    await page.locator("#quotaRefresh").evaluate((element) => element.click());
    await page.waitForTimeout(100);
    if (reads <= before) throw new Error("Refresh did not call the quota usage API.");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: "#sidebar, #mobileOverlay { display: none !important; }" });
    await page.screenshot({ path: "artifacts/admin_quota_limits_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-quota-metrics")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1) throw new Error(JSON.stringify(mobile));
    if (pageErrors.length) throw new Error(JSON.stringify(pageErrors));
    return { summary, upgradeState, filtered, selectedFromRow, headerAction, csv: download.name, reads, mobile, pageErrors };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
