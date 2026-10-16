const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const writes = [];
  const tenants = [
    { id: "tenant-a", company_name: "ASLAN TIC", active: 1, sector: "teknik_servis", license_type: "Premium", commands: [{ command_type: "deploy_update", status: "completed", created_at: "2026-10-14T10:00:00Z" }] },
    { id: "tenant-b", company_name: "Babali Servis", active: 1, sector: "otomotiv", license_type: "Lifetime", commands: [{ command_type: "deploy_update", status: "pending", created_at: "2026-10-14T10:05:00Z" }] },
  ];
  const updates = [{ version: "v2.0.1-rc3", target_scope: "Pilot", file_path: "https://updates.example/package.zip", notes: "Security and stability fixes", created_at: "2026-10-14T09:00:00Z" }];
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const body = request.method() === "POST" ? request.postDataJSON() : null;
    if (body) writes.push({ path: url.pathname, body });
    let response = {};
    if (url.pathname === "/api/control/overview") response = { vendor: {}, tenants };
    else if (url.pathname === "/api/control/staged-update" && request.method() === "GET") response = { updates };
    else if (url.pathname === "/api/control/staged-update" && request.method() === "POST") { updates.unshift({ ...body, created_at: "2026-10-14T10:10:00Z" }); response = { ok: true }; }
    else if (url.pathname === "/api/admin/updates/deploy") response = { ok: true, targets: body.targets };
    else response = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(response) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "staged-update";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
  await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_ota_web_desktop.png", fullPage: true });
    if (await page.locator("#otaTestButton").isEnabled()) throw new Error("Unsupported test-send action was enabled.");
    await page.locator("#otaStageNew").evaluate((element) => element.click());
    await page.locator('#dialogBody [name="version"]').fill("v2.0.2");
    await page.locator('#dialogBody [name="file_path"]').fill("https://updates.example/v2.0.2.zip");
    await page.locator('#dialogBody [name="notes"]').fill("Reliability update");
    await page.locator("#dialogSubmit").evaluate((element) => element.click());
    await page.waitForFunction(() => Array.from(document.querySelectorAll("#otaVersion option")).some(option => option.value === "v2.0.2"));
    await page.locator("#otaChannel").selectOption("stable");
    await page.locator("#otaSelectAll").evaluate((element) => element.click());
    await page.evaluate(() => {
      const notes = document.querySelector("#otaChangelog");
      notes.value = "Verified update notes";
      notes.dispatchEvent(new Event("input", { bubbles: true }));
      notes.dispatchEvent(new Event("change", { bubbles: true }));
    });
    await page.locator("#otaDeployButton").evaluate((element) => element.click());
    await page.locator("#dialogSubmit").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#otaVersion")?.value === "v2.0.2");
    const staged = writes.find((entry) => entry.path === "/api/control/staged-update");
    const deployed = writes.find((entry) => entry.path === "/api/admin/updates/deploy");
    if (!staged || staged.body.version !== "v2.0.2" || !deployed || deployed.body.version !== "v2.0.2" || deployed.body.channel !== "stable" || deployed.body.targets.length !== 2 || deployed.body.changelog !== "Verified update notes") throw new Error(JSON.stringify({ staged, deployed }));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: "artifacts/admin_ota_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-ota-grid")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1 || mobile.columns.split(" ").length !== 1) throw new Error(JSON.stringify(mobile));
    return { staged: staged.path, deployed: deployed.path, targetCount: deployed.body.targets.length, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
