// Review-only Chromium acceptance for the Arena rig planner.
// Run against a local static server: RIG_BASE_URL=http://127.0.0.1:8099 node tests/rig-builder-browser.cjs
// Requires puppeteer-core and a locally installed Chrome; never sends site data to third parties.
"use strict";

const assert = require("node:assert/strict");
const puppeteer = require("puppeteer-core");

const base = process.env.RIG_BASE_URL || "http://127.0.0.1:8099";
const chrome = process.env.CHROME_BIN || "/usr/bin/google-chrome";

async function visit(browser, width, suffix = "", denyStorage = false) {
  // Isolate browser storage between independent desktop/mobile journeys.
  const context = await browser.createBrowserContext();
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (err) => errors.push(err.message));
  await page.setViewport({ width, height: 900, isMobile: width < 600, hasTouch: width < 600 });
  if (denyStorage) {
    await page.evaluateOnNewDocument(() => {
      Object.defineProperty(window, "localStorage", {
        configurable: true,
        get() { throw new DOMException("Storage blocked", "SecurityError"); }
      });
    });
  }
  await page.goto(base + "/build-your-dj-setup.html" + suffix, {
    waitUntil: "load", timeout: 20000
  });
  await page.waitForSelector(".rig-dashboard-shell", { timeout: 15000 });
  const metrics = await page.evaluate(() => ({
    spend: document.querySelector(".metric-val--spend")?.textContent.trim() || "",
    overflow: document.documentElement.scrollWidth - innerWidth,
    title: document.title
  }));
  assert.match(metrics.spend, /\$/, "remaining purchase cost must show a dollar amount");
  assert.ok(metrics.overflow <= 1, width + "px viewport overflows by " + metrics.overflow + "px");
  assert.deepEqual(errors, [], "browser JS errors at " + width + "px");
  return { page, context, errors, metrics };
}

(async () => {
  const browser = await puppeteer.launch({
    executablePath: chrome, headless: true,
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
  });
  try {
    for (const width of [1440, 390]) {
      const { page, context, errors, metrics } = await visit(browser, width);
      const before = Number(metrics.spend.replace(/[^\d.]/g, ""));
      assert.ok(Number.isFinite(before) && before > 0, "initial spend must be a real amount");
      await page.click('.booth-card--main [data-action="toggle-slot-owned"]');
      const afterText = await page.$eval(".metric-val--spend", (el) => el.textContent.trim());
      const after = Number(afterText.replace(/[^\d.]/g, ""));
      assert.ok(after < before, "marking an owned controller must reduce remaining spend");
      assert.deepEqual(errors, [], "browser errors after owned-toggle");
      await context.close();
      console.log("PASS: " + width + "px real catalog/render/owned-budget/no-overflow");
    }

    const payload = {
      name: '<img src=x onerror="alert(1)">',
      items: [{ slotId: 'x" onmouseover="alert(1)', category: "controllers",
        itemId: "pioneer-ddj-flx4", qty: 2, owned: false }]
    };
    const query = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(payload)), "binary").toString("base64")
    );
    const hostile = await visit(browser, 390, query);
    const injected = await hostile.page.evaluate(() =>
      Array.from(document.querySelectorAll("*")).some((el) =>
        /alert\(1\)/.test((el.getAttribute("onmouseover") || "") +
          (el.getAttribute("onerror") || "")))
    );
    assert.equal(injected, false, "untrusted shared rig must not create event-handler attributes");
    assert.deepEqual(hostile.errors, [], "hostile shared rig must not throw");
    await hostile.context.close();
    console.log("PASS: malicious shared URL cannot inject event handlers");

    const denied = await visit(browser, 390, "", true);
    assert.deepEqual(denied.errors, [], "storage-denied browser must remain usable");
    await denied.context.close();
    console.log("PASS: storage-disabled mobile browser still initializes");
  } finally {
    await browser.close();
  }
})().catch((err) => { console.error(err); process.exitCode = 1; });
