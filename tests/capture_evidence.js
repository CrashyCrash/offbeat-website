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

  // 1. Rig Architect Dashboard with Upgrade Advisor & Booth
  await page.goto("http://127.0.0.1:8099/build-your-dj-setup.html?preset=club-ready", { waitUntil: "networkidle0" });
  await page.screenshot({ path: "evidence/round-4-2026-10/my-dj-rig-architect-desktop.jpg", fullPage: false });
  console.log("Captured my-dj-rig-architect-desktop.jpg");

  // 2. Hardware Spec Inspector Modal
  await page.click(".booth-card--main .booth-spec-btn");
  await page.waitForSelector(".picker-dialog--inspector", { visible: true });
  await page.screenshot({ path: "evidence/round-4-2026-10/rig-architect-inspector.jpg", fullPage: false });
  console.log("Captured rig-architect-inspector.jpg");
  await page.click(".picker-close");
  await new Promise(r => setTimeout(r, 200));

  // 3. Side-by-Side Compare Modal
  await page.click('[data-action="open-compare"]');
  await page.waitForSelector("#compare-modal-title", { visible: true });
  await page.screenshot({ path: "evidence/round-4-2026-10/rig-architect-compare.jpg", fullPage: false });
  console.log("Captured rig-architect-compare.jpg");

  await browser.close();
  console.log("All screenshots captured successfully!");
})();
