const puppeteer = require("/tmp/browser/node_modules/puppeteer-core");

const pages = [
  "index.html",
  "build-your-dj-setup.html",
  "beatmatch-trainer.html",
  "controller-software-compatibility-matrix.html",
  "dj-skills-learning-path.html",
  "dj-glossary.html",
  "best-dj-controllers-2026.html",
  "best-dj-headphones-2026.html",
  "editorial-standards.html",
  "disclosure.html",
  "contact.html"
];

(async () => {
  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    executablePath: "/tmp/chromium",
    headless: "shell"
  });

  let totalErrors = 0;
  for (const p of pages) {
    const page = await browser.newPage();
    const errors = [];
    page.on("pageerror", e => errors.push(String(e)));

    // Desktop
    await page.setViewport({ width: 1440, height: 900 });
    await page.goto(`http://127.0.0.1:8099/${p}`, { waitUntil: "load", timeout: 10000 });
    const dOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

    // Mobile
    await page.setViewport({ width: 390, height: 844, isMobile: true, hasTouch: true });
    await page.goto(`http://127.0.0.1:8099/${p}`, { waitUntil: "load", timeout: 10000 });
    const mOverflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);

    await page.close();

    console.log(`Audited ${p.padEnd(46)} | D-Overflow: ${dOverflow}px | M-Overflow: ${mOverflow}px | Errors: ${errors.length}`);
    if (dOverflow > 0 || mOverflow > 0 || errors.length > 0) {
      totalErrors++;
    }
  }

  await browser.close();
  if (totalErrors > 0) {
    console.error(`Audit failed with ${totalErrors} problematic pages`);
    process.exit(1);
  }
  console.log("ALL SAMPLED PAGES VERIFIED CLEAN WITH 0 OVERFLOW AND 0 JS ERRORS!");
})();
