async (page) => {
  await page.addStyleTag({ content: 'body,button,input,select,textarea { font-family: "Segoe UI", Arial, sans-serif !important; }' });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({ path: "artifacts/license_requests_reference.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "artifacts/license_requests_reference_mobile.png", fullPage: true });
  const encoding = await page.evaluate(() => document.characterSet);
  if (encoding.toUpperCase() !== "UTF-8") throw new Error(`Unexpected document encoding: ${encoding}`);
  return { encoding, title: await page.title() };
}
