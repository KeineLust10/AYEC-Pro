const { chromium } = require("playwright");

async function capture(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const statements = [];
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: {}, tenants: [] };
    else if (url.pathname === "/api/admin/companies") body = { companies: [{ id: "tenant-a", company_name: "ASLAN TIC" }] };
    else if (url.pathname === "/api/admin/companies/tenant-a/query" && route.request().method() === "POST") {
      const request = route.request().postDataJSON();
      statements.push(request.sql);
      body = { ok: true, columns: ["id", "username", "role"], rows: [[101, "operator", "admin"], [102, "service", "technician"]], truncated: false };
    }
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      activeAdminTab = "database-query";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.locator("#adminQueryRun").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#adminQueryResultCount")?.textContent.includes("2 sat"));
    const result = await page.evaluate(() => ({
      heading: document.querySelector(".admin-query-hero h2")?.textContent,
      columns: [...document.querySelectorAll("#adminQueryHead th")].map((item) => item.textContent),
      rows: document.querySelectorAll("#adminQueryRows tr").length,
      status: document.querySelector("#adminQueryStatus")?.textContent,
    }));
    if (result.rows !== 2 || result.columns.length !== 3 || !statements[0]?.startsWith("SELECT")) throw new Error(JSON.stringify({ result, statements }));
    await page.locator("#adminQueryExplain").evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#adminQueryStatus")?.textContent.startsWith("Tamamland"));
    if (!statements[1]?.startsWith("EXPLAIN QUERY PLAN SELECT")) throw new Error(JSON.stringify(statements));
    await page.screenshot({ path: "artifacts/admin_sql_diagnostic_web_desktop.png", fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: "#sidebar, #mobileOverlay { display: none !important; }" });
    await page.screenshot({ path: "artifacts/admin_sql_diagnostic_web_mobile.png", fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth }));
    if (mobile.document > mobile.viewport + 1) throw new Error(JSON.stringify(mobile));
    return { ...result, statements: statements.length, mobile };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
