async (page) => {
  const logs = [
    { id: 9942, created_at: "2026-10-14T08:11:02Z", action: "admin_password_reset", actor_user_id: 7, target_tenant_id: "tenant-aslan", target_user_id: 11, company_name: "ASLAN TIC", detail: { reason: "support_verified" } },
    { id: 9941, created_at: "2026-10-14T08:08:12Z", action: "admin_license_updated", actor_user_id: 7, target_tenant_id: "tenant-babali", target_user_id: null, company_name: "Babali Servis", detail: { plan: "pro" } },
    { id: 9940, created_at: "2026-10-14T08:03:01Z", action: "admin_readonly_query", actor_user_id: 7, target_tenant_id: "tenant-aslan", target_user_id: null, company_name: "ASLAN TIC", detail: { table: "users" } },
  ];
  logs[0].ip_address = "192.168.1.108";
  logs[0].record_hash = "e3b0c44298fc1c149afbf4c8996fb924";
  logs[0].detail = { description: "Temporary password set after support verification.", changes: { "user.password_hash": { before: "old-hash", after: "new-hash" }, "user.must_change_pwd": { before: false, after: true } } };
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/control/overview"
      ? { vendor: { name: "AYEC Pro", server: "lisans.ayecpro.com" }, tenants: [{ company_name: "ASLAN TIC" }, { company_name: "Babali Servis" }, { company_name: "Other tenant" }] }
      : path === "/api/admin/audit-logs" ? { logs } : { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
  await page.evaluate(async () => {
    document.querySelector("#authRoot")?.remove();
    document.body.classList.remove("auth-active");
    document.body.dataset.page = "control-center";
    activeAdminTab = "audit";
    document.querySelector("#content").innerHTML = renderControlCenter();
    await loadControlCenter();
  });
  await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
  const encoding = await page.evaluate(() => document.characterSet);
  if (encoding.toUpperCase() !== "UTF-8") throw new Error(`Unexpected document encoding: ${encoding}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const headerLabels = await page.evaluate(() => {
    document.body.dataset.page = "control-center";
    return { breadcrumb: document.querySelector(".admin-breadcrumb-tab")?.selectedOptions[0]?.textContent || document.querySelector("#breadcrumb").textContent, title: document.querySelector("#pageTitle").textContent };
  });
  const headerLayout = await page.evaluate(() => ({ height: document.querySelector(".topbar").getBoundingClientRect().height, titleDisplay: getComputedStyle(document.querySelector("#pageTitle")).display, shellStatus: getComputedStyle(document.querySelector("#shellStatusBar")).display }));
  await page.screenshot({ path: "artifacts/audit_monitoring_web_desktop.png", fullPage: true });
  await page.locator(".admin-breadcrumb-tab").selectOption("dashboard");
  await page.waitForFunction(() => activeAdminTab === "dashboard");
  await page.locator(".admin-breadcrumb-tab").selectOption("audit");
  await page.waitForFunction(() => activeAdminTab === "audit");
  const diffText = await page.locator("#auditInspector").innerText();

  await page.locator('[data-audit-category="auth"]').evaluate(button => button.click());
  const authRows = await page.locator("[data-audit-select]").count();
  const inspectorHasPassword = await page.locator("#auditInspector").innerText().then(text => text.includes("parola"));
  await page.locator('[data-audit-category="all"]').evaluate(button => button.click());
  await page.evaluate(() => {
    const risk = document.querySelector("#auditRiskFilter");
    risk.value = "critical";
    risk.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const criticalRows = await page.locator("[data-audit-select]").count();
  await page.evaluate(() => {
    const risk = document.querySelector("#auditRiskFilter");
    risk.value = "all";
    risk.dispatchEvent(new Event("change", { bubbles: true }));
    const search = document.querySelector("#auditSearch");
    search.value = "Babali";
    search.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const searchRows = await page.locator("[data-audit-select]").count();
  await page.evaluate(() => {
    const search = document.querySelector("#auditSearch");
    search.value = "";
    search.dispatchEvent(new Event("input", { bubbles: true }));
    const select = document.querySelector("#auditCompanyFilter");
    select.value = "Babali Servis";
    select.dispatchEvent(new Event("change", { bubbles: true }));
  });
  const companyRows = await page.locator("[data-audit-select]").count();
  await page.evaluate(() => {
    const select = document.querySelector("#auditCompanyFilter");
    select.value = "all";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    document.querySelector('[data-audit-select="9940"]').click();
  });
  const detailText = await page.locator("#auditInspector").innerText();
  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-audit-export]").evaluate(button => button.click());
  const download = await downloadPromise;
  const checksumShown = await page.locator("#toastRoot").innerText().then(text => text.includes("SHA-256"));
  const exportMetric = await page.locator(".audit-metric-4 b").innerText();
  await page.locator("[data-audit-integrity]").click();
  const integrityWarningShown = await page.locator("#toastRoot").innerText().then(text => text.includes("Doğrulanabilir hash bağlantısı bulunamadı"));

  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    setMobileMenu(false);
    document.querySelector("#sidebar")?.classList.remove("open");
    document.querySelector("#mobileOverlay")?.classList.remove("open");
    document.querySelector("#mobileOverlay")?.setAttribute("hidden", "");
    document.body.classList.remove("mobile-menu-open");
  });
  await page.waitForTimeout(300);
  await page.evaluate(() => document.querySelectorAll("#toastRoot .toast").forEach(toast => toast.remove()));
  await page.screenshot({ path: "artifacts/audit_monitoring_web_mobile.png", fullPage: true });
  const geometry = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    workspaceColumns: getComputedStyle(document.querySelector(".audit-workspace")).gridTemplateColumns,
    metricsColumns: getComputedStyle(document.querySelector(".audit-metrics")).gridTemplateColumns,
  }));

  if (authRows !== 1 || !inspectorHasPassword || !diffText.includes("old-hash") || !diffText.includes("new-hash") || !diffText.includes("192.168.1.108") || criticalRows !== 1 || searchRows !== 1 || companyRows !== 1 || !detailText.includes("users") || !download.suggestedFilename().endsWith(".csv") || !checksumShown || !integrityWarningShown || exportMetric !== "1 Rapor" || !headerLabels.breadcrumb.includes("Denetim") || headerLayout.height !== 56 || headerLayout.titleDisplay !== "none" || headerLayout.shellStatus !== "none" || geometry.viewport !== geometry.document || geometry.workspaceColumns.trim().split(/\s+/).length !== 1 || geometry.metricsColumns.trim().split(/\s+/).length !== 2) {
    throw new Error(JSON.stringify({ authRows, inspectorHasPassword, diffText, criticalRows, searchRows, companyRows, detailText, filename: download.suggestedFilename(), checksumShown, integrityWarningShown, exportMetric, headerLabels, headerLayout, geometry }));
  }
  if (geometry.document > geometry.viewport + 1 || geometry.workspaceColumns.split(" ").length !== 1) throw new Error(JSON.stringify(geometry));
  return { authRows, criticalRows, searchRows, companyRows, filename: download.suggestedFilename(), checksumShown, integrityWarningShown, exportMetric, headerLayout, mobile: geometry };
}
