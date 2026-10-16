const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  await page.addInitScript(() => {
    window.__backupDownload = null;
    HTMLAnchorElement.prototype.click = function () { if (this.download) window.__backupDownload = { name: this.download, href: this.href }; };
  });
  const backups = {
    "tenant-a": [
      { index: -1, filename: "tenant-a.db (current)", size_bytes: 12400000, modified: "2026-10-14 08:05", source: "server", kind: "current" },
      { index: 11, backup_id: 11, filename: "tenant-a-nightly.db", size_bytes: 8000000, modified: "2026-10-13 02:00", source: "desktop", kind: "support", product_code: "AYEC_PRO", hardware_id: "HW-A", sha256: "a".repeat(64) },
      { index: 0, filename: "tenant-a-legacy.db", size_bytes: 6000000, modified: "2026-09-20 01:00", source: "server", kind: "legacy" },
    ],
    "tenant-b": [{ index: 21, backup_id: 21, filename: "tenant-b-weekly.db", size_bytes: 5000000, modified: "2026-10-12 02:00", source: "desktop", kind: "support", product_code: "AYEC_PRO", hardware_id: "HW-B", sha256: "b".repeat(64) }],
  };
  const calls = [];
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants: [{ id: "tenant-a", company_name: "ASLAN TIC", active: 1 }, { id: "tenant-b", company_name: "Babali Servis", active: 1 }] };
    else if (url.pathname.startsWith("/api/admin/backups/") && url.pathname.includes("/download/")) { calls.push({ method: "GET", url: url.pathname + url.search }); await route.fulfill({ status: 200, contentType: "application/vnd.sqlite3", body: "mock-db" }); return; }
    else if (url.pathname.startsWith("/api/admin/backups/") && url.pathname.endsWith("/restore")) { calls.push({ method: "POST", url: url.pathname, body: route.request().postDataJSON() }); body = { ok: true, command_id: 501 }; }
    else if (url.pathname.startsWith("/api/admin/backups/")) body = { backups: backups[decodeURIComponent(url.pathname.split("/").at(-1))] || [] };
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "backup-restore";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.waitForFunction(() => document.querySelectorAll("[data-backup-row]").length === 3);
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_backup_restore_web_desktop.png", fullPage: true });
    const summary = await page.evaluate(() => ({ tenant: document.querySelector("#backupTenantSelect")?.value, rows: document.querySelectorAll("[data-backup-row]").length, bytes: document.querySelectorAll(".admin-backup-metrics article")[2]?.querySelector("strong")?.textContent }));
    await page.evaluate(() => { const input = document.querySelector("#backupSearch"); input.value = "nightly"; input.dispatchEvent(new Event("input", { bubbles: true })); });
    const filtered = await page.locator("[data-backup-row]").evaluateAll((rows) => rows.filter((row) => !row.hidden).length);
    await page.evaluate(() => { const input = document.querySelector("#backupSearch"); input.value = ""; input.dispatchEvent(new Event("input", { bubbles: true })); });
    await page.locator('[data-backup-download="1"]').evaluate((element) => element.click());
    await page.waitForFunction(() => window.__backupDownload !== null);
    const download = await page.evaluate(() => window.__backupDownload);
    if (summary.rows !== 3 || filtered !== 1 || download?.name !== "tenant-a-nightly.db" || !calls.some((call) => call.url.includes("backup_id=11"))) throw new Error(JSON.stringify({ summary, filtered, download, calls }));
    const confirm = page.locator("#backupRestoreConfirm");
    await confirm.evaluate((element) => { element.checked = true; element.dispatchEvent(new Event("change", { bubbles: true })); });
    await page.locator('[data-backup-select="1"]').evaluate((element) => element.click());
    if (await page.locator("#backupRestoreQueue").isDisabled()) throw new Error("Restore confirmation should enable only after a backup is selected.");
    await page.locator("#backupRestoreQueue").evaluate((element) => element.click());
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#appDialog")?.open === false);
    const restore = calls.find((call) => call.method === "POST");
    if (!restore || restore.body.backup_id !== 11 || restore.body.backup_index !== 11) throw new Error(JSON.stringify({ restore, calls }));
    await page.locator("#backupTenantSelect").selectOption("tenant-b");
    await page.waitForFunction(() => document.querySelectorAll("[data-backup-row]").length === 1);
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: "#sidebar, #mobileOverlay { display: none !important; }" });
    await page.screenshot({ path: "artifacts/admin_backup_restore_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-backup-metrics")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1) throw new Error(JSON.stringify(mobile));
    return { summary, filtered, download: download.name, restore: restore.body, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
