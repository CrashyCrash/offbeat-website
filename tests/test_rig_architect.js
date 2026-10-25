const puppeteer = require("/tmp/browser/node_modules/puppeteer-core");

(async () => {
  const browser = await puppeteer.launch({
    args: ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    executablePath: "/tmp/chromium",
    headless: "shell"
  });

  const page = await browser.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", msg => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.setViewport({ width: 1440, height: 900 });
  await page.goto("http://127.0.0.1:8099/build-your-dj-setup.html", { waitUntil: "load" });

  // Wait for catalog load and app render
  await page.waitForSelector(".rig-dashboard-shell", { timeout: 5000 });
  console.log("✓ Dashboard mounted successfully");

  // Check initial calculations
  const initialSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
  console.log("Initial Needed Spend:", initialSpend);

  // Test 1: Load Preset "The Club-Ready Rig"
  await page.click('[data-preset-id="club-ready"]');
  await new Promise(r => setTimeout(r, 200));
  const clubModel = await page.$eval(".booth-card--main .booth-model", el => el.textContent.trim());
  console.log("Preset loaded controller:", clubModel);
  if (clubModel !== "DDJ-FLX10") throw new Error("Expected DDJ-FLX10 for club preset, got " + clubModel);

  // Test 2: Modal Component Swapper
  await page.click('.booth-card--main [data-action="pick"]');
  await page.waitForSelector(".picker-backdrop", { timeout: 3000 });
  console.log("✓ Component selector modal opened");

  // Search in modal
  await page.type("[data-modal-search]", "Denon Prime 4");
  await new Promise(r => setTimeout(r, 200));
  const filteredCount = await page.$$eval(".picker-card", cards => cards.length);
  console.log("Modal filtered items count for Denon Prime 4:", filteredCount);
  if (filteredCount !== 1) throw new Error("Expected 1 result for Denon Prime 4 search");

  // Select Denon Prime 4+
  await page.evaluate(() => {
    const btn = document.querySelector("#modal-items-grid .btn-select-item");
    if (btn) btn.click();
    else console.error("Could not find button inside #modal-items-grid");
  });
  await new Promise(r => setTimeout(r, 300));

  const newModel = await page.$eval(".booth-card--main .booth-model", el => el.textContent.trim());
  console.log("Updated controller in rig:", newModel);
  if (newModel !== "Prime 4+") throw new Error("Expected Prime 4+ selected");

  // Test 3: Toggle "Already Own"
  const preToggleSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
  await page.click('.booth-card--main [data-action="toggle-slot-owned"]');
  await new Promise(r => setTimeout(r, 200));
  const postToggleSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
  console.log("Spend before owned toggle:", preToggleSpend, "-> after owned toggle:", postToggleSpend);

  // Test 4: Quantity adjustment using + stepper
  const preQtySpend = await page.$eval(".spend-total-num", el => el.textContent.trim());
  await page.click('[data-action="step-qty"][data-step="1"]');
  await new Promise(r => setTimeout(r, 200));
  const newQty = await page.$eval(".qty-display", el => el.textContent.trim());
  console.log("Adjusted quantity via stepper to:", newQty);
  if (newQty !== "2") throw new Error("Expected quantity to be 2, got: " + newQty);

  // Test 5: Open Compare Builds Modal
  await page.click('[data-action="open-compare"]');
  await page.waitForSelector("#compare-modal-title", { timeout: 3000 });
  console.log("✓ Compare setups modal opened");
  await page.click('.picker-close');
  await new Promise(r => setTimeout(r, 200));

  // Test 6: Deep link test (?add=pioneer-ddj-flx10)
  await page.goto("http://127.0.0.1:8099/build-your-dj-setup.html?add=pioneer-ddj-flx10", { waitUntil: "load" });
  await page.waitForSelector(".booth-card--main", { timeout: 5000 });
  const deepLinkedModel = await page.$eval(".booth-card--main .booth-model", el => el.textContent.trim());
  console.log("Deep-linked controller:", deepLinkedModel);
  if (deepLinkedModel !== "DDJ-FLX10") throw new Error("Expected deep-linked DDJ-FLX10");

  // Test 7: Hardware Spec Inspector Modal
  await page.click('.booth-card--main .booth-spec-btn');
  await page.waitForSelector('.picker-dialog--inspector', { visible: true });
  const inspectorTitle = await page.$eval('#inspector-title', el => el.textContent.trim());
  console.log('✓ Inspector modal opened for:', inspectorTitle);
  if (inspectorTitle !== "DDJ-FLX10") throw new Error("Expected inspector for DDJ-FLX10, got: " + inspectorTitle);
  await page.click('.picker-close');
  await new Promise(r => setTimeout(r, 200));

  // Test 8: Upgrade Path Advisory & Compatibility Badges
  const upgradeText = await page.$eval('.upgrade-body strong', el => el.textContent.trim());
  console.log('✓ Upgrade advisory active:', upgradeText);
  if (!upgradeText) throw new Error("Expected upgrade advisory text");

  const compatBadges = await page.$$('.compat-level-badge');
  console.log('✓ Compatibility level badges rendered:', compatBadges.length);
  if (compatBadges.length === 0) throw new Error("Expected compatibility level badges");

  // Test 9: Dedicated Multi-Accessory Coexistence Test
  // Add a Shure SM58 mic without replacing the laptop stand
  await page.click('[data-action="open-add-slot"]');
  await page.waitForSelector('[data-action="add-new-slot"][data-category="microphones"]');
  await page.click('[data-action="add-new-slot"][data-category="microphones"]');
  await page.waitForSelector('.picker-card');
  await page.click('.picker-card'); // Click to select Shure SM58
  await new Promise(r => setTimeout(r, 200));

  const hasStand = await page.$eval('.rig-spec-table', el => el.textContent.includes('Pyle Pro'));
  const hasMic = await page.$eval('.rig-spec-table', el => el.textContent.includes('SM58'));
  console.log('✓ Multi-accessory coexistence (Stand + Mic both present):', hasStand && hasMic);
  if (!hasStand || !hasMic) throw new Error("Expected both Stand and Microphone to coexist in rig!");

  // Test 10: Sound SFX Toggle
  await page.click('[data-action="toggle-sound"]');
  const sfxText = await page.$eval('[data-action="toggle-sound"]', el => el.textContent.trim());
  console.log('✓ Sound FX toggle state:', sfxText);

  // Test 11: Share & Export Modal with Reddit Markdown and Canvas
  await page.click('[data-action="open-export-modal"]');
  await page.waitForSelector('.picker-dialog--export', { visible: true });
  const redditMd = await page.$eval('#reddit-export-box', el => el.value);
  console.log('✓ Export modal opened, Reddit markdown length:', redditMd.length);
  if (!redditMd || redditMd.length < 50) throw new Error("Expected generated Reddit markdown");
  await page.click('.picker-close');
  await new Promise(r => setTimeout(r, 200));

  console.log("JS Console Errors:", errors);
  if (errors.length > 0) throw new Error("Found JS errors: " + JSON.stringify(errors));

  await browser.close();
  console.log("ALL RIG BUILDER TESTS (INCLUDING MULTI-ACCESSORY COEXISTENCE & EXPORT) PASSED WITH 0 ERRORS!");
})();
