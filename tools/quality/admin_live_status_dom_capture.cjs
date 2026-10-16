const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const companies = [
    { id: "tenant-a", company_name: "ASLAN TIC", online: true, active_users: 2, last_seen: "" },
    { id: "tenant-b", company_name: "Babali Servis", online: false, active_users: 0, last_seen: "" },
  ];
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const body = url.pathname === "/api/control/overview" ? { vendor: {}, tenants: companies } : url.pathname === "/api/admin/live-status" ? { companies } : url.pathname === "/api/admin/audit-logs" ? { logs: [{ company_name: "ASLAN TIC", action: "session_seen", created_at: "2026-10-14T10:00:00Z" }] } : { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "live-status";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.screenshot({ path: "artifacts/admin_live_status_web_desktop.png", fullPage: true });
    const initial = await page.locator("[data-live-company]").count();
    await page.locator('[data-live-filter="online"]').evaluate((element) => element.click());
    const onlineCount = await page.locator("[data-live-company]:not([hidden])").count();
    await page.locator('[data-live-filter="all"]').evaluate((element) => element.click());
    await page.evaluate(() => {
      const search = document.querySelector("#adminLiveSearch");
      search.value = "tenant-b";
      search.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const searchCount = await page.locator("[data-live-company]:not([hidden])").count();
    if (initial !== 2 || onlineCount !== 1 || searchCount !== 1) throw new Error(JSON.stringify({ initial, onlineCount, searchCount }));
    if (await page.locator(".admin-live-company button:disabled").count() < 3) throw new Error("Unsupported remote actions must stay disabled.");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.screenshot({ path: "artifacts/admin_live_status_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-live-companies")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1 || mobile.columns.split(" ").length !== 1) throw new Error(JSON.stringify(mobile));
    return { initial, onlineCount, searchCount, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
