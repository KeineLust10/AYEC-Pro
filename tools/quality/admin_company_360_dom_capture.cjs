const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const writes = [];
  const tenants = [
    { id: "tenant-a", company_name: "ASLAN TIC", active: 1, sector: "teknik_servis", license_type: "Premium", license_code: "AYEC-TEST-A", contact_name: "Engin Aslan", phone: "555 111 2233", email: "admin@aslan.example", company_address: "Gonen / Balikesir", users: [{ id: 1, username: "engin", full_name: "Engin Aslan", email: "admin@aslan.example", role: "Admin", active: 1 }], backups: [] },
    { id: "tenant-b", company_name: "Babali Servis", active: 0, sector: "otomotiv", license_type: "Lifetime", license_code: "AYEC-TEST-B", contact_name: "Bora Babali", phone: "555 222 3344", email: "bora@example.com", company_address: "Balikesir", users: [{ id: 2, username: "bora", full_name: "Bora Babali", email: "bora@example.com", role: "User", active: 1 }], backups: [] },
  ];
  const companyDetail = (tenant) => ({ company: tenant, users: tenant.users, licenses: [{ tenant_id: tenant.id, license_code: tenant.license_code, license_type: tenant.license_type, license_end: "2027-10-14" }], backups: [], error_logs: [], live_status: { online: tenant.active === 1, active_users: tenant.active === 1 ? 1 : 0, last_seen: "" }, summary: { user_count: 1, backup_count: 0, error_count: 0, online: tenant.active === 1 } });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const payload = request.method() !== "GET" ? request.postDataJSON() : null;
    if (payload) writes.push({ path: url.pathname, body: payload });
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants };
    else if (url.pathname === "/api/admin/companies") body = { companies: tenants };
    else if (url.pathname.startsWith("/api/admin/customer-360/")) body = companyDetail(tenants.find((tenant) => tenant.id === url.pathname.split("/").pop()) || tenants[0]);
    else if (url.pathname === "/api/control/password-reset") body = { ok: true, reset_url: "https://example.invalid/reset", mail_sent: false };
    else body = { ok: true };
    if (url.pathname === "/api/control/tenant" && payload) Object.assign(tenants.find((tenant) => tenant.id === payload.tenant_id), payload);
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "tenants";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.screenshot({ path: "artifacts/admin_company_360_web_desktop.png", fullPage: true });
    const initial = await page.locator("[data-company360-id]").count();
    await page.locator('[data-company-filter="inactive"]').evaluate((element) => element.click());
    const inactiveCount = await page.locator("[data-company360-id]").count();
    await page.locator('[data-company-filter="all"]').evaluate((element) => element.click());
    await page.locator('[data-company360-id="tenant-b"]').evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#company360Detail h1")?.textContent === "Babali Servis");
    const selected = await page.evaluate(() => document.querySelector("#company360Detail h1")?.textContent);
    if (initial !== 2 || inactiveCount !== 1 || selected !== "Babali Servis") throw new Error(JSON.stringify({ initial, inactiveCount, selected }));
    await page.locator('[data-company360-id="tenant-a"]').evaluate((element) => element.click());
    await page.locator("#company360Sector select").selectOption("otomotiv");
    await page.locator("#company360Sector").evaluate((form) => form.requestSubmit());
    await page.waitForFunction(() => document.querySelector("#company360Sector select")?.value === "otomotiv");
    const update = writes.find((entry) => entry.path === "/api/control/tenant");
    if (!update || update.body.tenant_id !== "tenant-a" || update.body.sector !== "otomotiv") throw new Error(JSON.stringify(update));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_company_360_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-company-360-grid")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1 || mobile.columns.split(" ").length !== 1) throw new Error(JSON.stringify(mobile));
    return { initial, inactiveCount, selected, sectorUpdate: update.path, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
