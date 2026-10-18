async (page) => {
  await page.waitForTimeout(750);
  const screenshotRoot = process.env.AYEC_AUDIT_OUTPUT || process.cwd();
  const writes = [];
  const orders = [
    { id: 101, request_no: "REQ-101", company_name: "ASLAN TIC", requester_name: "Engin Aslan", requester_email: "admin@aslan.example", plan_code: "one_year", plan_label: "1 Yillik", amount_try: 15990, payment_reference: "AYEC-101", payment_note: "Transfer completed", status: "payment_reported", created_at: "2026-10-14 09:42" },
    { id: 102, request_no: "REQ-102", company_name: "Babali Servis", requester_name: "Bora Yilmaz", plan_code: "six_months", plan_label: "6 Aylik", amount_try: 4500, payment_reference: "AYEC-102", status: "payment_pending", created_at: "2026-10-14 09:38" },
  ];
  const licenses = [
    { tenant_id: "tenant-1", company_name: "ASLAN TIC", product_code: "teknik_servis", license_code: "AYEC-TEST-101", license_type: "1 Yillik", license_start: "2026-10-14", license_end: "2027-10-14", status: "Active", license_updated_at: "2026-10-14" },
  ];
  const invites = Array.from({ length: 48 }, (_, offset) => {
    const id = offset + 1;
    return {
      id,
      expires_at: "2028-10-14T00:00:00+00:00",
      max_uses: 1,
      use_count: id <= 12 || id > 46 ? 0 : 1,
      revoked_at: id > 46 ? "2026-10-14T00:00:00+00:00" : null,
    };
  });
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (request.method() !== "GET") writes.push({ path: url.pathname, body: request.postDataJSON() });
    let body = {};
    if (url.pathname === "/api/control/overview") body = { vendor: { name: "AYEC Pro", server: "lisans.ayecpro.com" }, tenants: [] };
    else if (url.pathname === "/api/control/provision-invites") body = { invites };
    else if (url.pathname === "/api/admin/license-orders") body = { orders };
    else if (url.pathname === "/api/admin/licenses") body = { licenses };
    else if (url.pathname === "/api/admin/server-status") body = { cpu_percent: 3, ram_percent: 52, disk_percent: 30 };
    else if (url.pathname === "/api/admin/live-status") body = { companies: [{ id: "tenant-1", company_name: "ASLAN TIC", online: true, active_users: 2 }] };
    else body = { ok: true };
    await route.fulfill({ status: 200, contentType: "application/json; charset=utf-8", body: JSON.stringify(body) });
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(300);

  await page.evaluate(async () => {
    document.querySelector("#authRoot")?.remove();
    document.body.classList.remove("auth-active");
    document.body.dataset.page = "control-center";
    activeAdminTab = "license-requests";
    document.querySelector("#content").innerHTML = renderControlCenter();
    await loadControlCenter();
  });
  await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
  const encoding = await page.evaluate(() => document.characterSet);
  if (encoding.toUpperCase() !== "UTF-8") throw new Error(`Unexpected document encoding: ${encoding}`);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const headerMetrics = await page.evaluate(() => ({ values: [...document.querySelectorAll("#adminSystemMetrics strong")].map(item => item.textContent), notificationDisplay: getComputedStyle(document.querySelector("#notificationBtn")).display }));
  if (headerMetrics.values.join(",") !== "3%,52%,30%" || headerMetrics.notificationDisplay === "none" || !await page.locator("#adminHeaderUser").count()) throw new Error(JSON.stringify({ headerMetrics }));
  await page.screenshot({ path: `${screenshotRoot}/artifacts/license_requests_web_desktop.png`, fullPage: true });
  const licenseMetrics = await page.evaluate(() => [...document.querySelectorAll(".license-metric")].map(card => card.querySelector("b")?.textContent));
  if (licenseMetrics.join(",") !== "48,12,34,2") throw new Error(JSON.stringify({ licenseMetrics }));
  const headerLayout = await page.evaluate(() => {
    document.body.dataset.page = "control-center";
    return { breadcrumb: document.querySelector("#breadcrumb").textContent, breadcrumbDisplay: getComputedStyle(document.querySelector("#breadcrumb")).display, height: document.querySelector(".topbar").getBoundingClientRect().height, titleDisplay: getComputedStyle(document.querySelector("#pageTitle")).display, shellStatus: getComputedStyle(document.querySelector("#shellStatusBar")).display };
  });
  await page.screenshot({ path: `${screenshotRoot}/artifacts/license_requests_web_desktop.png`, fullPage: true });

  const initial = await page.locator("[data-license-request]").count();
  const interaction = await page.evaluate(() => {
    const search = document.querySelector("#licenseOrderSearch");
    search.value = "Babali";
    search.dispatchEvent(new Event("input", { bubbles: true }));
    const filtered = document.querySelectorAll('[data-license-request][hidden]').length;
    search.value = "";
    search.dispatchEvent(new Event("input", { bubbles: true }));
    return filtered;
  });
  const preview = await page.evaluate(() => {
    document.querySelector('[data-license-preview="101"]').click();
    return document.querySelector("#dialogBody").innerText;
  });
  await page.evaluate(() => {
    window.confirm = () => true;
    document.querySelector('[data-license-decision="approve"][data-order-id="101"]').click();
  });
  await page.locator("#dialogSubmit").click();
  await page.waitForTimeout(100);
  const decision = writes.find((entry) => entry.path === "/api/admin/license-orders/101/approve");

  await page.evaluate(async () => {
    activeAdminTab = "license-requests";
    document.querySelector("#content").innerHTML = renderControlCenter();
    await loadControlCenter();
  });
  await page.waitForSelector(".license-request-grid");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => {
    setMobileMenu(false);
    document.querySelector("#sidebar")?.classList.remove("open");
    document.querySelector("#mobileOverlay")?.classList.remove("open");
    document.querySelector("#mobileOverlay")?.setAttribute("hidden", "");
    document.body.classList.remove("mobile-menu-open");
    document.querySelectorAll(".toast").forEach((toast) => toast.remove());
  });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${screenshotRoot}/artifacts/license_requests_web_mobile.png`, fullPage: true });
  const geometry = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
    cardColumns: document.querySelector(".license-request-grid") ? getComputedStyle(document.querySelector(".license-request-grid")).gridTemplateColumns : "missing",
    controlsColumns: document.querySelector(".license-request-actions") ? getComputedStyle(document.querySelector(".license-request-actions")).gridTemplateColumns : "",
  }));

  if (initial !== 2 || interaction !== 1 || !decision || decision.body.plan_code !== "one_year" || decision.body.admin_note !== "") {
    throw new Error(JSON.stringify({ initial, interaction, decision }));
  }
  if (!preview.includes("ASLAN TIC") || !preview.includes("15.990,00")) throw new Error("Request preview did not bind the selected order.");
  if (geometry.document > geometry.viewport + 1 || geometry.cardColumns.split(" ").length !== 1) {
    throw new Error(JSON.stringify(geometry));
  }
  const restoredShell = await page.evaluate(() => {
    navigate("dashboard");
    const metrics = document.querySelector("#adminSystemMetrics");
    return { placeholder: document.querySelector("#globalSearch").placeholder, metricsDisplay: metrics ? getComputedStyle(metrics).display : "none" };
  });
  if (restoredShell.placeholder !== "Sistem genelinde ara (Marka, Seri No, ...)" || restoredShell.metricsDisplay !== "none") throw new Error(JSON.stringify({ restoredShell }));
  if (!headerLayout.breadcrumb.includes("Lisans Talepleri") || headerLayout.breadcrumbDisplay === "none" || headerLayout.height !== 48 || headerLayout.titleDisplay !== "none" || headerLayout.shellStatus !== "none") throw new Error(JSON.stringify(headerLayout));
  return { initial, filtered: interaction, decision: decision.path, headerLayout, mobile: geometry };
}
