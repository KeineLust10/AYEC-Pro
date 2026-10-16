const { chromium } = require("playwright");
const { pathToFileURL } = require("node:url");

async function capture(referencePath, outputPath) {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  try {
    await page.goto(pathToFileURL(referencePath).href, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1800);
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif; }' });
    await page.evaluate(() => document.fonts.ready);
    const pageInfo = await page.evaluate(() => ({
      charset: document.characterSet,
      title: document.title,
      heading: document.querySelector("main h1")?.textContent?.trim() || document.querySelector("main h2")?.textContent?.trim() || "",
      mainWidth: document.querySelector("main")?.getBoundingClientRect().width || 0,
      mainHeight: document.querySelector("main")?.getBoundingClientRect().height || 0,
    }));
    if (pageInfo.charset.toUpperCase() !== "UTF-8") throw new Error(`Unexpected document encoding: ${pageInfo.charset}`);
    const main = page.locator("main");
    if (await main.count()) await main.screenshot({ path: outputPath });
    else await page.screenshot({ path: outputPath, fullPage: true });
    return pageInfo;
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2], process.argv[3]).then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
