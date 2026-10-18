const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

const webRoot = path.resolve(__dirname, "../../Web_Arayuzu/web");
const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ttf": "font/ttf",
  ".woff2": "font/woff2",
};

async function run() {
  const server = http.createServer((request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, "http://localhost").pathname);
    const relative = pathname === "/" ? "index.html" : pathname.slice(1);
    const filePath = path.resolve(webRoot, relative);
    if (!filePath.startsWith(webRoot + path.sep)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(filePath, (error, data) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      response.writeHead(200, { "Content-Type": contentTypes[path.extname(filePath)] || "application/octet-stream" });
      response.end(data);
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const pageErrors = [];
  const settingsWrites = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.addInitScript(() => {
    window.__legacyImagePickerRequests = 0;
    const nativeClick = HTMLInputElement.prototype.click;
    HTMLInputElement.prototype.click = function () {
      if (this.matches("[data-proforma-image-file]")) {
        window.__legacyImagePickerRequests += 1;
        return;
      }
      return nativeClick.call(this);
    };
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/desktop/table/settings" && request.method() === "POST") {
      settingsWrites.push(request.postDataJSON());
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true }) });
      return;
    }
    if (url.pathname === "/api/desktop/pc-builder/proforma.pdf") {
      await route.fulfill({ status: 200, contentType: "application/pdf", body: "%PDF-1.4\\n% audit fixture\\n" });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });

  try {
    await page.goto(`http://127.0.0.1:${server.address().port}/`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => typeof settingBody === "function" && typeof desktopSettings === "object");
    const template = String.raw`<p>Legacy offer</p><img src="C:\Legacy\brand-logo.png">`;
    await page.evaluate((markup) => {
      settingsSection = "proforma-template";
      desktopSettings.proforma_editor_html = markup;
      desktopSettings.proforma_use_custom_editor = "1";
      document.querySelector("#content").innerHTML = `<div class="settings-content">${settingBody(desktopSettings)}</div><button type="button" data-action="save-settings">Save settings</button>`;
    }, template);
    const initial = await page.evaluate(() => ({
      count: document.querySelectorAll(".proforma-legacy-image").length,
      placeholder: document.querySelector(".proforma-legacy-image")?.textContent,
      safeMarkup: document.querySelector("#proformaTemplateCanvas")?.innerHTML,
    }));
    if (initial.count !== 1 || !initial.placeholder.includes("brand-logo.png") || initial.safeMarkup.includes("C:")) {
      throw new Error(JSON.stringify(initial));
    }

    const writesBeforeBlockedSave = settingsWrites.length;
    await page.locator('[data-action="save-settings"]').evaluate((button) => button.click());
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("g\u00f6rsellerini kaydetmeden"));
    if (settingsWrites.length !== writesBeforeBlockedSave) throw new Error("Unresolved desktop image sent a settings write.");

    await page.locator(".proforma-legacy-image").evaluate((element) => element.click());
    if (!(await page.evaluate(() => window.__legacyImagePickerRequests))) throw new Error("Missing image placeholder did not open its replacement picker.");
    const png = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC", "base64");
    await page.locator("[data-proforma-image-file]").setInputFiles({ name: "brand-logo.png", mimeType: "image/png", buffer: png });
    await page.waitForFunction(() => !document.querySelector(".proforma-legacy-image") && document.querySelector("#proformaTemplateCanvas img[src^='data:image/jpeg;base64,']"));
    const replaced = await page.evaluate(() => ({
      placeholderCount: document.querySelectorAll(".proforma-legacy-image").length,
      imageCount: document.querySelectorAll("#proformaTemplateCanvas img[src^='data:image/jpeg;base64,']").length,
      source: document.querySelector("#proformaTemplateHtml")?.value,
    }));
    if (replaced.placeholderCount || replaced.imageCount !== 1 || !replaced.source.includes("data:image/jpeg;base64,") || replaced.source.includes("C:")) {
      throw new Error(JSON.stringify(replaced));
    }

    await page.locator('[data-action="save-settings"]').evaluate((button) => button.click());
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("Proforma sablon ayarlari kaydedildi."));
    const savedTemplate = settingsWrites.find((item) => item.key === "proforma_editor_html")?.value || "";
    const activationWrites = settingsWrites.filter((item) => item.key === "proforma_use_custom_editor").map((item) => item.value);
    if (!savedTemplate.includes("data:image/jpeg;base64,") || savedTemplate.includes("brand-logo.png") || activationWrites.join(",") !== "0,1") {
      throw new Error(JSON.stringify({ savedTemplateLength: savedTemplate.length, activationWrites }));
    }
    if (pageErrors.length) throw new Error(JSON.stringify(pageErrors));
    return { initial: initial.count, replaced: replaced.imageCount, blockedWrites: writesBeforeBlockedSave, activationWrites, pageErrors };
  } finally {
    await browser.close();
    await new Promise((resolve) => server.close(resolve));
  }
}

if (require.main === module) run().then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = run;
