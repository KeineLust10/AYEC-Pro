async (page) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: "artifacts/customer_360_reference.png", fullPage: true });
  return await page.evaluate(() => ({
    title: document.title,
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    documentHeight: document.documentElement.scrollHeight,
    mainBounds: (() => {
      const main = document.querySelector("main");
      const bounds = main.getBoundingClientRect();
      return { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height };
    })(),
    heading: document.querySelector("main h1")?.textContent?.trim() || "",
  }));
}
