const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const writes = [];
  const tenants = [
    { id: "tenant-a", company_name: "ASLAN TIC", active: 1, online: true },
    { id: "tenant-b", company_name: "Babali Servis", active: 1, online: false },
  ];
  await page.route("**/api/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (req.method() !== "GET") writes.push({ path: url.pathname, body: req.postDataJSON() });
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: { name: "AYEC Pro" }, tenants };
    else if (url.pathname === "/api/admin/audit-logs") body = { logs: [{ action: "control_notification_sent", company_name: "ASLAN TIC", target_tenant_id: "tenant-a", created_at: "2026-10-14T10:00:00Z", detail: { title: "Audit-backed announcement" } }] };
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "notifications";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.screenshot({ path: "artifacts/admin_notifications_web_desktop.png", fullPage: true });

    await page.locator('[data-notify-audience="selected"]').evaluate((element) => element.click());
    await page.locator('[data-notify-tenant="tenant-a"]').evaluate((element) => element.click());
    await page.locator('[data-notify-tenant="tenant-b"]').evaluate((element) => element.click());
    await page.evaluate(() => {
      const title = document.querySelector("#notifyTitle");
      const body = document.querySelector("#notifyBody");
      title.value = "Deployment notice";
      body.value = "A planned maintenance window begins at 21:00.";
      title.dispatchEvent(new Event("input", { bubbles: true }));
      body.dispatchEvent(new Event("input", { bubbles: true }));
    });
    await page.locator('[data-notify-type="warning"]').evaluate((element) => element.click());
    await page.locator("#notifyPopup").evaluate((element) => element.click());
    const preview = await page.evaluate(() => ({ title: document.querySelector("#notifyPreviewTitle").textContent, body: document.querySelector("#notifyPreviewBody").textContent, type: document.querySelector(".admin-notify-preview").dataset.previewType, count: document.querySelector("#notifyTitleCount").textContent }));
    if (preview.title !== "Deployment notice" || preview.type !== "warning" || preview.count !== "17/120 Karakter") throw new Error(JSON.stringify(preview));
    if (await page.locator('[data-notify-audience="pilot"]').isEnabled()) throw new Error("Unsupported pilot targeting was enabled.");
    if (await page.locator(".admin-notify-delivery button").isEnabled()) throw new Error("Unsupported scheduling was enabled.");

    await page.locator("#notifyPublish").evaluate((element) => element.click());
    await page.locator("#dialogSubmit").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#notifyStatus")?.textContent.includes("2 firma"));
    const posts = writes.filter((entry) => entry.path === "/api/control/send-notification");
    if (posts.length !== 2 || posts[0].body.target_tenant_id !== "tenant-a" || posts[1].body.target_tenant_id !== "tenant-b" || posts.some((entry) => entry.body.popup !== false || entry.body.message_title !== "Deployment notice")) throw new Error(JSON.stringify(posts));
    if (!await page.locator("#notifyHistoryList").innerText().then((text) => text.includes("Audit-backed announcement"))) throw new Error("History is not bound to the audit API.");

    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.evaluate(() => {
      if (typeof setMobileMenu === "function") setMobileMenu(false);
      document.querySelector("#sidebar")?.classList.remove("open");
      document.querySelector("#mobileOverlay")?.classList.remove("open");
      document.querySelector("#mobileOverlay")?.setAttribute("hidden", "");
      document.body.classList.remove("mobile-menu-open");
      document.querySelectorAll(".toast").forEach((node) => node.remove());
    });
    await page.screenshot({ path: "artifacts/admin_notifications_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-notification-layout")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1 || mobile.columns.split(" ").length !== 1) throw new Error(JSON.stringify(mobile));
    return { preview, posts: posts.length, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
