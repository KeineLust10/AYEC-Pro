async (page) => {
  const logs = [
    { id: 701, created_at: "2026-10-14T08:11:02Z", action: "admin_password_reset", actor_user_id: 7, company_name: "ASLAN TIC", status: "Completed" },
    { id: 700, created_at: "2026-10-14T08:08:12Z", action: "admin_license_updated", actor_user_id: 8, company_name: "Babali Servis", status: "Pending" },
  ];
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body = path === "/api/control/overview"
      ? { vendor: { name: "AYEC Pro", server: "lisans.ayecpro.com" }, tenants: [{ id: "tenant-a", company_name: "ASLAN TIC", active: 1, backups: [{}], users: [{ active: 1 }] }, { id: "tenant-b", company_name: "Babali Servis", active: 1, users: [{ active: 1 }] }, { id: "tenant-c", company_name: "Other tenant", active: 0 }] }
      : path === "/api/admin/live-status"
        ? { companies: [{ id: "tenant-a", company_name: "ASLAN TIC", online: true, active_users: 2 }, { id: "tenant-b", company_name: "Babali Servis", online: true, active_users: 1 }, { id: "tenant-c", company_name: "Other tenant", online: false, active_users: 0 }] }
        : path === "/api/admin/server-status"
          ? { cpu_percent: 3, ram_percent: 52, disk_percent: 30 }
          : path === "/api/admin/dashboard"
        ? { online_users: 23, logins_today: 41, disk_usage: "2.4 TB / 8 TB", backup_coverage: 1, pending_commands: 0, expiring_licenses: 2 }
        : path === "/api/admin/audit-logs" ? { logs } : { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(150);
  await page.evaluate(async () => {
    document.querySelector("#authRoot")?.remove();
    document.body.classList.remove("auth-active");
    activeAdminTab = "dashboard";
    page = "control-center";
    render();
    await loadControlCenter();
  });
  await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
  const encoding = await page.evaluate(() => document.characterSet);
  if (encoding.toUpperCase() !== "UTF-8") throw new Error(`Unexpected document encoding: ${encoding}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const headers = await page.locator(".control-audit-table thead th").allTextContents();
  const rows = await page.locator(".control-audit-table tbody tr").count();
  const metrics = await page.locator(".control-kpi").count();
  const backupDetail = await page.locator(".control-kpi-grid.control-kpi-secondary .control-kpi:nth-child(3)").innerText();
  const operatorHidden = await page.locator("#controlOperator").evaluate(element => element.hidden);
  const breadcrumb = await page.locator("#breadcrumb").innerText();
  await page.evaluate(() => { document.body.dataset.page = "control-center"; });
  const topbarGeometry = await page.evaluate(() => ({height: document.querySelector(".topbar").getBoundingClientRect().height, titleDisplay: getComputedStyle(document.querySelector("#pageTitle")).display}));
  const systemMetrics = await page.locator("#adminSystemMetrics > span").count();
  const systemMetricValues = await page.locator("#adminSystemMetrics strong").allTextContents();
  const healthRows = await page.locator(".control-health-row").count();
  const onlineRows = await page.locator(".control-health-row b.on").count();
  const offlineRows = await page.locator(".control-health-row b.off").count();
  const quickActions = await page.locator(".control-quick-actions button").count();
  const unavailableActions = await page.locator(".control-quick-actions button:disabled").count();
  await page.screenshot({ path: "artifacts/admin_dashboard_web_desktop.png", fullPage: true });
  const samplesBeforeRefresh = await page.evaluate(() => adminDashboardSamples.length);
  await page.locator("[data-control-dashboard-refresh]").evaluate(button => button.click());
  await page.waitForFunction(count => adminDashboardSamples.length > count, samplesBeforeRefresh);
  const performanceSampleCount = await page.evaluate(() => adminDashboardSamples.length);
  const performancePath = await page.locator(".control-performance-line").getAttribute("d");
  const performanceAverage = await page.locator(".control-performance-average").innerText();
  await page.evaluate(() => {
    const search = document.querySelector("#controlAuditSearch");
    search.value = "Babali";
    search.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const filteredRows = await page.locator(".control-audit-table tbody tr:not([hidden])").count();
  const filteredCount = await page.locator("#controlAuditCount").innerText();
  await page.evaluate(() => {
    const search = document.querySelector("#controlAuditSearch");
    search.value = "";
    search.dispatchEvent(new Event("input", { bubbles: true }));
  });
  const downloadPromise = page.waitForEvent("download");
  await page.locator("[data-control-export]").evaluate(button => button.click());
  const download = await downloadPromise;
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    setMobileMenu(false);
    document.querySelector(".sidebar")?.classList.remove("open");
    const sidebar = document.querySelector(".sidebar");
    if (sidebar) sidebar.style.visibility = "hidden";
    document.querySelector("#mobileOverlay")?.classList.remove("open");
    document.querySelector("#mobileOverlay")?.setAttribute("hidden", "");
    document.body.classList.remove("mobile-menu-open");
  });
  await page.evaluate(() => document.querySelectorAll("#toastRoot .toast").forEach(toast => toast.remove()));
  await page.screenshot({ path: "artifacts/admin_dashboard_web_mobile.png", fullPage: true });
  const geometry = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, document: document.documentElement.scrollWidth, table: document.querySelector(".control-audit-table-wrap").scrollWidth, tableClient: document.querySelector(".control-audit-table-wrap").clientWidth }));
  await page.locator('[data-control-action="backup-restore"]').click();
  const backupShortcut = await page.evaluate(() => activeAdminTab);
  if (systemMetrics !== 3 || systemMetricValues.join(",") !== "3%,52%,30%" || healthRows !== 3 || onlineRows !== 2 || offlineRows !== 1 || quickActions !== 4 || unavailableActions !== 0 || backupShortcut !== "backup-restore") throw new Error(JSON.stringify({ systemMetrics, systemMetricValues, healthRows, onlineRows, offlineRows, quickActions, unavailableActions, backupShortcut }));
  if (headers.length !== 5 || rows !== 2 || metrics !== 9 || performanceSampleCount < 2 || !backupDetail.includes("%33") || backupDetail.includes("%100") || !operatorHidden || !performancePath || !performanceAverage.includes("ms") || filteredRows !== 1 || !filteredCount.includes("1") || !breadcrumb.includes("Yönetim Konsolu") || topbarGeometry.height !== 56 || topbarGeometry.titleDisplay !== "none" || !download.suggestedFilename().endsWith(".csv")) throw new Error(JSON.stringify({ headers, rows, metrics, performanceSampleCount, backupDetail, operatorHidden, performancePath, performanceAverage, filteredRows, filteredCount, breadcrumb, topbarGeometry, filename: download.suggestedFilename() }));
  if (geometry.document > geometry.viewport + 1 || geometry.table <= geometry.tableClient) throw new Error(JSON.stringify(geometry));
  return { headers, rows, metrics, performanceSampleCount, performancePath, filteredRows, systemMetrics, systemMetricValues, healthRows, onlineRows, offlineRows, quickActions, unavailableActions, backupShortcut, breadcrumb, topbarGeometry, filename: download.suggestedFilename(), encoding, mobile: geometry };
}
