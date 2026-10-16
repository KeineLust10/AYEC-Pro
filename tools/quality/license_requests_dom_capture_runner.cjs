const fs = require("node:fs");
const { chromium } = require("playwright");

async function run(baseUrl) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    const source = fs.readFileSync("tools/quality/license_requests_dom_capture.cjs", "utf8");
    const capture = Function(`return (${source});`)();
    return await capture(page);
  } finally {
    await browser.close();
  }
}

if (require.main === module) run(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = run;
