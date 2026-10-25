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

  // 1. Rig Architect with Multi-Accessory Setup
  await page.goto("http://127.0.0.1:8099/build-your-dj-setup.html?preset=club-ready", { waitUntil: "networkidle0" });
  await page.screenshot({ path: "evidence/round-4-2026-10/my-dj-rig-architect-desktop.jpg", fullPage: false });
  console.log("Captured my-dj-rig-architect-desktop.jpg");

  // 2. Beatmatch Trainer in Guided Mode with Live Actionable Coach Banner
  await page.goto("http://127.0.0.1:8099/beatmatch-trainer.html", { waitUntil: "networkidle0" });
  await page.click("[data-start]");
  await new Promise(r => setTimeout(r, 400));
  await page.screenshot({ path: "evidence/round-4-2026-10/trainer-guided-mode.jpg", fullPage: false });
  console.log("Captured trainer-guided-mode.jpg");

  // 3. Compact Privacy Consent Banner (clear localStorage first)
  await page.evaluate(() => localStorage.removeItem("offbeat.ga-consent.v1"));
  await page.goto("http://127.0.0.1:8099/index.html", { waitUntil: "networkidle0" });
  await page.waitForSelector(".ob-consent", { visible: true });
  await page.screenshot({ path: "evidence/round-4-2026-10/consent-compact-dialog.jpg", fullPage: false });
  console.log("Captured consent-compact-dialog.jpg");

  await browser.close();
  console.log("All updated evidence screenshots captured successfully!");
})();
