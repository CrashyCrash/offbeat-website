const puppeteer = require("/tmp/browser/node_modules/puppeteer-core");

(async () => {
  const browser = await puppeteer.launch({
    executablePath: "/tmp/chromium",
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
  });

  const page = await browser.newPage();
  await page.setCacheEnabled(false);
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });

  // 1. Rig Architect in Photo Mode
  await page.goto("http://127.0.0.1:8099/build-your-dj-setup.html?preset=club-ready", { waitUntil: "networkidle0" });
  await page.click('[data-action="set-viewmode"][data-mode="photos"]');
  await new Promise(r => setTimeout(r, 200));
  await page.screenshot({ path: "evidence/round-4-2026-10/rig-architect-photo-mode.jpg", fullPage: false });
  console.log("Captured rig-architect-photo-mode.jpg");

  // 2. Export Modal with Reddit Markdown and Canvas Card
  await page.click('[data-action="open-export-modal"]');
  await page.waitForSelector(".picker-dialog--export", { visible: true });
  await page.screenshot({ path: "evidence/round-4-2026-10/rig-export-dialog.jpg", fullPage: false });
  console.log("Captured rig-export-dialog.jpg");
  await page.click(".picker-close");
  await new Promise(r => setTimeout(r, 200));

  // 3. Sitewide Spotlight Search (Cmd + K)
  await page.click(".nav-search");
  await page.waitForSelector("#quick-search-backdrop", { visible: true });
  await page.screenshot({ path: "evidence/round-4-2026-10/spotlight-search-modal.jpg", fullPage: false });
  console.log("Captured spotlight-search-modal.jpg");

  await browser.close();
  console.log("Captured all new evidence screenshots successfully!");
})();
