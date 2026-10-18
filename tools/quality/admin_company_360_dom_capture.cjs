const { chromium } = require("playwright");
const fs = require("node:fs");
const path = require("node:path");

async function capture(baseUrl) {
  const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "artifacts");
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const pageErrors = [];
  const reads = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  const writes = [];
  let resetMailSucceeds = false;
  const tenants = [
    { id: "tenant-a", company_name: "ASLAN TIC", active: 1, muted: 0, sector: "teknik_servis", license_type: "Premium", license_code: "AYEC-TEST-A", contact_name: "Engin Aslan", phone: "555 111 2233", email: "admin@aslan.example", company_address: "Gonen / Balikesir", users: [{ id: 1, username: "engin", full_name: "Engin Aslan", email: "admin@aslan.example", role: "Admin", active: 1 }], backups: [] },
    { id: "tenant-b", company_name: "Babali Servis", active: 0, muted: 0, sector: "otomotiv", license_type: "Lifetime", license_code: "AYEC-TEST-B", contact_name: "Bora Babali", phone: "555 222 3344", email: "bora@example.com", company_address: "Balikesir", users: [{ id: 2, username: "bora", full_name: "Bora Babali", email: "bora@example.com", role: "User", active: 1 }], backups: [] },
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
    else if (url.pathname.startsWith("/api/admin/users/") && url.pathname.endsWith("/reset-password")) body = { ok: true, user_id: Number(url.pathname.split("/")[4]) };
    else if (url.pathname === "/api/admin/users/temporary-password") body = { ok: true, user_id: payload?.user_id, recipient: "bora@example.com", mail_sent: true, expires_at: "2026-10-17T12:30:00" };
    else if (url.pathname.startsWith("/api/admin/companies/") && url.pathname.endsWith("/repair-users")) {
      const tenantId = url.pathname.split("/").at(-2);
      const tenant = tenants.find((item) => item.id === tenantId);
      if (tenant) tenant.users = [{ id: 2, username: "bora", full_name: "Bora Babali", email: "bora@example.com", role: "User", active: 1 }];
      body = { ok: true, tenant_id: tenantId, restored_users: 1, backup_id: 7 };
    }
    else if (url.pathname.startsWith("/api/admin/companies/") && url.pathname.endsWith("/delete")) {
      const tenantId = url.pathname.split("/").at(-2);
      const index = tenants.findIndex((tenant) => tenant.id === tenantId);
      if (index >= 0) tenants.splice(index, 1);
      body = { ok: true, tenant_id: tenantId, archive: "20261017-120000-Babali Servis.db" };
    }
    else if (url.pathname.startsWith("/api/admin/companies/") && payload) {
      const tenant = tenants.find((item) => item.id === url.pathname.split("/").pop());
      if (tenant) Object.assign(tenant, payload, { muted: Number(payload.muted) });
      body = { ok: true, tenant_id: tenant?.id, muted: tenant?.muted };
    }
    else if (url.pathname === "/api/control/password-reset") body = { ok: true, reset_url: "https://example.invalid/reset", mail_sent: resetMailSucceeds, mail_message: resetMailSucceeds ? "sent" : "SMTP unavailable" };
    else body = { ok: true };
    if (url.pathname === "/api/control/tenant" && payload) Object.assign(tenants.find((tenant) => tenant.id === payload.tenant_id), payload);
    if (url.pathname === "/api/admin/companies" || url.pathname.startsWith("/api/admin/customer-360/")) reads.push({ path: url.pathname, muted: url.pathname === "/api/admin/companies" ? tenants.map(tenant => [tenant.id, tenant.muted]) : body.company?.muted });
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  try {
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    await page.evaluate(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.body.dataset.page = "control-center";
      currentAuthUser = { tenant_id: "tenant-a", is_control_admin: true };
      activeAdminTab = "tenants";
      document.querySelector("#content").innerHTML = renderControlCenter();
      await loadControlCenter();
    });
    await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
    if ((await page.evaluate(() => document.characterSet)).toUpperCase() !== "UTF-8") throw new Error("Document encoding is not UTF-8.");
    await page.screenshot({ path: path.join(outputDir, "admin_company_360_web_desktop.png"), fullPage: true });
    const initial = await page.locator("[data-company360-id]").count();
    const ownTenantMuteDisabled = await page.locator("#company360Mute").isDisabled();
    if (!ownTenantMuteDisabled) throw new Error("The control tenant mute action must stay disabled.");
    await page.locator('[data-company-filter="inactive"]').evaluate((element) => element.click());
    const inactiveCount = await page.locator("[data-company360-id]").count();
    await page.locator('[data-company-filter="all"]').evaluate((element) => element.click());
    await page.locator('[data-company360-id="tenant-b"]').evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#company360Detail h1")?.textContent === "Babali Servis");
    const selected = await page.evaluate(() => document.querySelector("#company360Detail h1")?.textContent);
    if (initial !== 2 || inactiveCount !== 1 || selected !== "Babali Servis") throw new Error(JSON.stringify({ initial, inactiveCount, selected, pageErrors, detail: await page.locator("#company360Detail").innerText().catch(() => "missing") }));
    if (await page.locator("#company360AddUser").isDisabled()) throw new Error("The desktop-mapped company navigation action must be enabled.");
    const addUserState = await page.locator("#company360AddUser").evaluate((element) => {
      const shell = document.querySelector("#appShell");
      const wasInert = shell?.hasAttribute("inert");
      const wasHidden = shell?.getAttribute("aria-hidden");
      shell?.removeAttribute("inert");
      shell?.removeAttribute("aria-hidden");
      element.focus();
      element.click();
      const focusedId = document.activeElement?.id || "";
      if (wasInert) shell.setAttribute("inert", "");
      if (wasHidden !== null && wasHidden !== undefined) shell.setAttribute("aria-hidden", wasHidden);
      return { focusedId, search: Boolean(document.querySelector("#company360Search")) };
    });
    if (addUserState.focusedId !== "company360Search" || !addUserState.search || writes.some((entry) => entry.path === "/api/control/user")) throw new Error(JSON.stringify({ addUserState, writes }));
    if (process.env.AYEC_COMPANY_360_NAV_ONLY === "1") return { navigationFocused: addUserState.focusedId === "company360Search", searchVisible: addUserState.search, createRequestSent: writes.some((entry) => entry.path === "/api/control/user"), pageErrors };
    await page.locator('[data-company360-temp-password="2"]').evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Gecici Parola Gonder") throw new Error(JSON.stringify({ message: "Temporary password confirmation did not open.", disabled: await page.locator('[data-company360-temp-password="2"]').isDisabled(), title: await page.locator('[data-company360-temp-password="2"]').getAttribute("title"), dialog: await page.locator("#dialogTitle").textContent() }));
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("e-posta ile gonderildi"));
    const temporaryPassword = writes.find((entry) => entry.path === "/api/admin/users/temporary-password");
    if (!temporaryPassword || temporaryPassword.body.tenant_id !== "tenant-b" || temporaryPassword.body.user_id !== 2) throw new Error(JSON.stringify(temporaryPassword));
    await page.locator('[data-company360-reset-link="2"]').evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Parola Sifirlama Baglantisi Gonder") throw new Error("Reset-link confirmation did not open.");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("SMTP unavailable"));
    if (!(await page.locator("#appDialog").evaluate((dialog) => dialog.open))) throw new Error("Reset-link dialog should remain open after failed delivery.");
    const resetDialogText = await page.locator("#dialogBody").textContent();
    if (resetDialogText.includes("example.invalid/reset")) throw new Error("Bearer reset URL must not be shown in the admin dialog.");
    resetMailSucceeds = true;
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("Sifirlama baglantisi kullaniciya e-posta ile gonderildi"));
    const resetLink = writes.find((entry) => entry.path === "/api/control/password-reset");
    if (!resetLink || resetLink.body.tenant_id !== "tenant-b" || resetLink.body.user_id !== 2) throw new Error(JSON.stringify(resetLink));
    await page.locator('[data-company360-reset-password="2"]').evaluate((element) => element.click());
    if (!(await page.locator("#dialogTitle").textContent()).includes("Ge\u00e7ici Parola Ata")) throw new Error("Manual password reset dialog did not open.");
    await page.locator("#company360NewPassword").fill("short");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("\u015eifre en az 6 karakter"));
    if (writes.some((entry) => entry.path.endsWith("/reset-password"))) throw new Error("A short password must not reach the reset endpoint.");
    await page.locator("#company360NewPassword").fill("SafePass123");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("\u015eifre ba\u015far\u0131yla s\u0131f\u0131rland\u0131"));
    const passwordReset = writes.find((entry) => entry.path === "/api/admin/users/2/reset-password");
    if (!passwordReset || passwordReset.body.tenant_id !== "tenant-b" || passwordReset.body.new_password !== "SafePass123") throw new Error(JSON.stringify(passwordReset));
    await page.locator('[data-company360-id="tenant-a"]').evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#company360Detail h1")?.textContent === "ASLAN TIC");
    await page.locator("#company360Sector select").selectOption("otomotiv");
    const sectorResponse = page.waitForResponse((response) => new URL(response.url()).pathname === "/api/control/tenant");
    await page.locator("#company360Sector").evaluate((form) => form.requestSubmit());
    await sectorResponse;
    const sectorState = await page.evaluate(() => ({ company: document.querySelector("#company360Detail h1")?.textContent || "", value: document.querySelector("#company360Sector select")?.value || "" }));
    if (sectorState.value !== "otomotiv") throw new Error(JSON.stringify({ sectorState, writes }));
    const update = writes.find((entry) => entry.path === "/api/control/tenant");
    if (!update || update.body.tenant_id !== "tenant-a" || update.body.sector !== "otomotiv") throw new Error(JSON.stringify(update));
    await page.locator('[data-company360-id="tenant-b"]').evaluate((element) => element.click());
    await page.waitForFunction(() => document.querySelector("#company360Detail h1")?.textContent === "Babali Servis");
    await page.locator("#company360Mute").evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Firmayi Sustur") throw new Error("Tenant mute confirmation did not open.");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#company360Mute")?.textContent.trim() === "Susturmayi Kaldir", undefined, { timeout: 5000 }).catch(async () => {
      throw new Error(JSON.stringify({ state: await page.evaluate(() => ({ label: document.querySelector("#company360Mute")?.textContent, dialog: document.querySelector("#appDialog")?.open, toast: document.querySelector("#toastRoot")?.textContent })), writes, reads, tenants, pageErrors }));
    });
    const mute = writes.find((entry) => entry.path === "/api/admin/companies/tenant-b" && entry.body.muted === true);
    if (!mute) throw new Error(JSON.stringify(writes));
    const mutedState = await page.evaluate(() => ({ tenant: document.querySelector("#company360Detail h1")?.textContent, detail: document.querySelector(".admin-company-summary p b")?.textContent, list: document.querySelector('[data-company360-id="tenant-b"] b')?.textContent }));
    if (mutedState.tenant !== "Babali Servis" || mutedState.detail !== "ERISIM SUSTURULDU" || mutedState.list !== "SUSTURULDU") throw new Error(JSON.stringify({ mutedState, reads }));
    await page.locator("#company360Mute").evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Firma Erisimini Ac") throw new Error("Tenant unmute confirmation did not open.");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#company360Mute")?.textContent.trim() === "Sustur", undefined, { timeout: 5000 }).catch(async () => {
      throw new Error(JSON.stringify({ state: await page.evaluate(() => ({ label: document.querySelector("#company360Mute")?.textContent, dialog: document.querySelector("#appDialog")?.open, toast: document.querySelector("#toastRoot")?.textContent })), writes, pageErrors }));
    });
    const unmute = writes.find((entry) => entry.path === "/api/admin/companies/tenant-b" && entry.body.muted === false);
    if (!unmute) throw new Error(JSON.stringify(writes));
    tenants.find((tenant) => tenant.id === "tenant-b").users = [];
    await page.locator("#company360Refresh").evaluate((element) => element.click());
    await page.waitForFunction(() => Boolean(document.querySelector("#company360RepairUsers")));
    await page.locator("#company360RepairUsers").evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Kullanici Kaydini Kurtar") throw new Error("Missing-user recovery confirmation did not open.");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("1 kullanici kaydi korunan yedekten kurtarildi"));
    await page.waitForFunction(() => document.querySelector("#company360Detail tbody tr")?.textContent.includes("bora"));
    const repairUsers = writes.find((entry) => entry.path === "/api/admin/companies/tenant-b/repair-users");
    if (!repairUsers || await page.locator("#company360RepairUsers").count()) throw new Error(JSON.stringify(repairUsers));
    await page.locator("#company360Delete").evaluate((element) => element.click());
    if (await page.locator("#dialogTitle").textContent() !== "Firma Silme Onayi") throw new Error("Company archive confirmation did not open.");
    await page.locator("#company360DeleteConfirm").fill("wrong company name");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#toastRoot")?.textContent.includes("Firma adi dogrulanamadi"));
    if (writes.some((entry) => entry.path.endsWith("/delete"))) throw new Error("A mismatched company name must not send the archive request.");
    await page.locator("#company360DeleteConfirm").fill("Babali Servis");
    await page.locator("#dialogForm").evaluate((form) => form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true })));
    await page.waitForFunction(() => document.querySelector("#company360Detail h1")?.textContent === "ASLAN TIC");
    const deleteCompany = writes.find((entry) => entry.path === "/api/admin/companies/tenant-b/delete");
    if (!deleteCompany || !deleteCompany.body || tenants.some((tenant) => tenant.id === "tenant-b")) throw new Error(JSON.stringify({ deleteCompany, tenants }));
    await page.setViewportSize({ width: 390, height: 844 });
    await page.addStyleTag({ content: '#sidebar, #mobileOverlay { display: none !important; }' });
    await page.evaluate(() => document.querySelectorAll(".toast").forEach((toast) => toast.remove()));
    await page.screenshot({ path: path.join(outputDir, "admin_company_360_web_mobile.png"), fullPage: true });
    const mobile = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, columns: getComputedStyle(document.querySelector(".admin-company-360-grid")).gridTemplateColumns }));
    if (mobile.document > mobile.viewport + 1 || mobile.columns.split(" ").length !== 1) throw new Error(JSON.stringify(mobile));
    if (pageErrors.length) throw new Error(JSON.stringify({ pageErrors }));
    return { initial, inactiveCount, selected, temporaryPassword: temporaryPassword.path, resetLink: resetLink.path, passwordReset: passwordReset.path, sectorUpdate: update.path, ownTenantMuteDisabled, mutedState, mute: mute.body.muted, unmute: unmute.body.muted, repairUsers: repairUsers.path, deleteCompany: deleteCompany.path, mobile, pageErrors };
  } finally {
    await browser.close();
  }
}

if (require.main === module) capture(process.argv[2] || "http://127.0.0.1:8794/").then((result) => process.stdout.write(JSON.stringify(result) + "\n")).catch((error) => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
module.exports = capture;
