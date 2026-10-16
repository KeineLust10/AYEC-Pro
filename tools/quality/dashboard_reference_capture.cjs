async (page) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: "artifacts/admin_dashboard_reference.png", fullPage: true });
  return await page.evaluate(() => ({ title: document.title, width: document.documentElement.scrollWidth, height: document.documentElement.scrollHeight }));
}
