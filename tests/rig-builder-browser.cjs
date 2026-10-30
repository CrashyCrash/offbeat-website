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
      // Owner workflow: build and review first, then save/share/export.
      // The final actions must remain functional on both desktop and mobile.
      const layoutOrder = await page.evaluate(() => Array.from(
        document.querySelectorAll(".rig-booth-section, .rig-table-section, .rig-finalize-section"),
        node => node.className
      ));
      assert.deepEqual(layoutOrder, [
        "rig-booth-section", "rig-table-section", "rig-finalize-section"
      ], "save/share/export must follow the visual booth and itemized shopping list");
      assert.equal(await page.$('.rig-dash-header [data-action="save-rig"]'), null,
        "saving an unfinished rig must not be the first dashboard action");
      assert.ok(await page.$('.rig-finalize-section [data-action="save-rig"]'),
        "save remains available after the completed rig");
      await page.click('.rig-finalize-section [data-action="open-export-modal"]');
      await page.waitForSelector(".picker-dialog--export");
      await page.click(".picker-close");
      assert.deepEqual(errors, [], "post-build export must not cause browser errors");

      // HD 25 already includes a native 3.5mm plug; do not upsell an adapter.
      const initialAlerts = await page.$eval(".compat-items-grid", el => el.textContent);
      assert.doesNotMatch(initialAlerts, /Headphone Connector Adapter Needed|Headphone Jack Adapter Advisory/);
      assert.match(initialAlerts, /Included Speaker Cable Matches/,
        "DM-40D bundle must supply the compatible analog lead");
      assert.doesNotMatch(initialAlerts, /Audio Cable Needed/,
        "default must not upsell a separate audio cable");
      const includedLabel = await page.$eval(".cable-title", el => el.textContent.trim());
      assert.match(includedLabel, /Speaker Package Includes Audio Cable/);
      // Connection map is live to the selected equipment, not a static
      // decorative cable animation or a claim of physically tested routing.
      const initialRoutes = await page.evaluate(() =>
        Array.from(document.querySelectorAll(".rig-route")).map(node => ({
          key: node.dataset.route, status: node.dataset.status, text: node.textContent
        })));
      assert.equal(initialRoutes.length, 3, "host, room audio and headphone cue must be separate routes");
      assert.equal(initialRoutes.find(r => r.key === "master").status, "included",
        "starter's manufacturer-bundled speaker lead should be shown as included");
      assert.equal(initialRoutes.find(r => r.key === "host").status, "review",
        "mobile host must never appear physically verified");
      assert.match(initialRoutes.find(r => r.key === "host").text, /power are conditional/);
      // Starter assumes a compatible phone already owned, not a forced laptop purchase.
      assert.equal(metrics.spend, "$597", "starter excludes a new laptop and stand");
      assert.match(initialAlerts, /Mobile Host, USB Audio and Power Need Verification/);
      const initialOwned = await page.$eval(".metric-val--owned", el => el.textContent.trim());
      assert.match(initialOwned, /\$0$/, "default ownership deduction must be zero");
      const before = Number(metrics.spend.replace(/[^\d.]/g, ""));
      assert.ok(Number.isFinite(before) && before > 0, "initial spend must be a real amount");
      await page.click('.booth-card--main [data-action="toggle-slot-owned"]');
      const afterText = await page.$eval(".metric-val--spend", (el) => el.textContent.trim());
      const after = Number(afterText.replace(/[^\d.]/g, ""));
      assert.ok(after < before, "marking an owned controller must reduce remaining spend");
      assert.deepEqual(errors, [], "browser errors after owned-toggle");

      // Every preset button must quote the same full total displayed after
      // selecting it, including host laptop, speakers, cables and accessories.
      const expectedPresets = [
        ["bedroom-starter", "$597"],
        ["club-ready", "$3,230"],
        ["mobile-pro", "$3,052"],
        ["traktor-techno", "$1,780"]
      ];
      for (const [id, expectedPrice] of expectedPresets) {
        const badge = await page.$eval('[data-preset-id="' + id + '"] .preset-badge', el => el.textContent.trim());
        assert.equal(badge, "Est. " + expectedPrice + " total", id + " badge");
        await page.click('[data-preset-id="' + id + '"]');
        const actualSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
        assert.equal(actualSpend, expectedPrice, id + " purchase cost must match advertised total");
      }
      // A single JBL PA cabinet is NOT a stereo pair. The buyer must see
      // physical-unit counts at both the visual booth and shopping row.
      await page.click('[data-preset-id="mobile-pro"]');
      assert.equal(await page.$eval('[data-context="audience"]', el => el.getAttribute("aria-pressed")), "true",
        "mobile wedding preset must default to audience mode");
      assert.match(await page.$eval(".compat-items-grid", el => el.textContent),
        /Audience Coverage and Deployment Need Verification/,
        "one PA cabinet must not be misrepresented as venue-ready");
      const singleBooth = await page.$eval(".booth-package-detail", el => el.textContent.trim());
      const singleTable = await page.$eval(".speaker-package-detail", el => el.textContent.trim());
      assert.match(singleBooth, /1 individual PA cabinet; a second cabinet is NOT included/);
      assert.equal(singleTable, singleBooth, "booth and checkout must agree on included cabinets");
      await page.$eval(".speaker-package-detail", el =>
        el.closest("tr").querySelector('[data-action="step-qty"][data-step="1"]').click());
      assert.match(await page.$eval(".speaker-package-detail", el => el.textContent.trim()),
        /2 individual PA cabinets; the price covers 2 separate cabinets/);
      assert.equal(await page.$eval(".metric-val--spend", el => el.textContent.trim()), "$3,601",
        "adding a second cabinet must add exactly one cabinet's cost");
      await page.click('[data-preset-id="mobile-pro"]');
      assert.equal(await page.$eval(".metric-val--spend", el => el.textContent.trim()), "$3,052",
        "clarifying package contents must not silently change the buyer's budget");
      await page.click('[data-preset-id="bedroom-starter"]');
      assert.equal(await page.$eval('[data-context="studio"]', el => el.getAttribute("aria-pressed")), "true");
      const deskSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
      await page.click('[data-action="set-listening-context"][data-context="audience"]');
      const venueAlerts = await page.$eval(".compat-items-grid", el => el.textContent);
      assert.match(venueAlerts, /Nearfield Studio Monitors Are Not Audience PA/);
      assert.match(venueAlerts, /Audience PA System Not Selected/);
      assert.equal(await page.$eval('[data-route="master"]', el => el.dataset.status), "blocked");
      assert.match(await page.$eval(".compat-status-tag", el => el.textContent), /Incompatible Configuration/);
      assert.equal(await page.$eval(".metric-val--spend", el => el.textContent.trim()), deskSpend,
        "context switch must not silently add or change purchases");
      // A desk-to-party switch must offer a usable PA picker directly in the
      // booth, rather than relabeling the monitor and trapping Swap in nearfield.
      assert.ok(await page.$('.booth-card--empty[data-speaker-role="audience_pa"]'),
        "audience booth must show missing PA, not the selected desk monitor");
      assert.equal(await page.$eval(".cable-title", el => el.textContent.trim()),
        "No Audio Cables Selected", "a studio monitor's included cable cannot satisfy missing audience PA");
      await page.click('.booth-card--empty[data-speaker-role="audience_pa"]');
      assert.ok(await page.$('.btn-select-item[data-item-id="jbl-eon-715"]'),
        "direct booth PA picker must offer catalog-confirmed PA");
      assert.equal(await page.$('.btn-select-item[data-item-id="pioneer-dm40d"]'), null,
        "direct booth PA picker must not offer nearfield monitors");
      await page.click('.btn-select-item[data-item-id="jbl-eon-715"]');
      assert.match(await page.$eval(".booth-card .booth-model", el => el.textContent), /EON715/);
      const mixedSpeakerTable = await page.$eval(".rig-spec-table", el => el.textContent);
      assert.match(mixedSpeakerTable, /DM-40D/, "existing studio monitors must remain selected");
      assert.match(mixedSpeakerTable, /EON715/, "PA must be added rather than overwriting monitors");
      assert.notEqual(await page.$eval('[data-route="master"]', el => el.dataset.status), "blocked",
        "room path should no longer be blocked for missing PA after selection");
      await page.click('[data-action="set-listening-context"][data-context="studio"]');
      assert.match(await page.$eval(".booth-card .booth-model", el => el.textContent), /DM-40D/,
        "switching back must select studio monitors without deleting the PA");
      await page.click('[data-preset-id="bedroom-starter"]');
      assert.doesNotMatch(await page.$eval(".compat-items-grid", el => el.textContent),
        /Audience PA System Not Selected/);
      const pairBooth = await page.$eval(".booth-package-detail", el => el.textContent.trim());
      const pairTable = await page.$eval(".speaker-package-detail", el => el.textContent.trim());
      assert.match(pairBooth, /1 stereo pair \(2 physical speakers\)/);
      assert.equal(pairTable, pairBooth);
      await page.$eval(".speaker-package-detail", el =>
        el.closest("tr").querySelector('[data-action="step-qty"][data-step="1"]').click());
      assert.match(await page.$eval(".speaker-package-detail", el => el.textContent.trim()),
        /2 stereo pairs \(4 physical speakers\)/);
      assert.equal(await page.$eval(".metric-val--spend", el => el.textContent.trim()), "$746",
        "adding a second pair must add one pair price, not one speaker price");
      // Role-gated speaker pickers: a studio monitor is never offered as
      // audience PA, and a PA cabinet cannot be injected into a monitor slot.
      await page.click('[data-preset-id="bedroom-starter"]');
      await page.click('.booth-card [data-action="pick"][data-category="speakers"]');
      assert.ok(await page.$('.btn-select-item[data-item-id="pioneer-dm40d"]'),
        "monitor picker must offer actual nearfield monitors");
      assert.equal(await page.$('.btn-select-item[data-item-id="jbl-eon-715"]'), null,
        "monitor picker must exclude crowd PA");
      const initialRoleSpend = await page.$eval(".metric-val--spend", el => el.textContent.trim());
      await page.$eval(".btn-select-item", el => { el.dataset.itemId = "jbl-eon-715"; el.click(); });
      assert.equal(await page.$eval("#rig-modal-container", el => el.hidden), false,
        "forged ineligible monitor selection must be refused");
      await page.click(".picker-close");
      assert.equal(await page.$eval(".metric-val--spend", el => el.textContent.trim()), initialRoleSpend,
        "forged selection must not alter purchases");

      await page.click('[data-action="open-add-slot"]');
      await page.click('[data-action="add-new-slot"][data-speaker-role="audience_pa"]');
      assert.ok(await page.$('.btn-select-item[data-item-id="jbl-eon-715"]'),
        "crowd PA picker must offer catalog-confirmed PA");
      assert.equal(await page.$('.btn-select-item[data-item-id="pioneer-dm40d"]'), null,
        "crowd PA picker must exclude nearfield monitors");
      await page.$eval(".btn-select-item", el => { el.dataset.itemId = "pioneer-dm40d"; el.click(); });
      assert.equal(await page.$eval("#rig-modal-container", el => el.hidden), false,
        "forged ineligible PA selection must be refused");
      await page.$eval(".btn-select-item", el => { el.dataset.itemId = "jbl-eon-715"; });
      await page.click('.btn-select-item[data-item-id="jbl-eon-715"]');
      assert.match(await page.$eval(".rig-spec-table", el => el.textContent), /Crowd-Facing PA/);
      assert.match(await page.$eval(".rig-spec-table", el => el.textContent), /DJ Booth Monitors/);
      await page.click('[data-action="set-listening-context"][data-context="audience"]');
      assert.doesNotMatch(await page.$eval(".compat-items-grid", el => el.textContent),
        /Audience PA System Not Selected/, "real PA plus booth monitors must satisfy the PA selection check");
      assert.match(await page.$eval('[data-route="master"]', el => el.textContent), /EON715/,
        "audience routing must describe the PA, not the first nearfield monitor");
      const sharedRoleUrl = page.url();
      assert.match(sharedRoleUrl, /[?&]rig=/);
      await page.goto(sharedRoleUrl, { waitUntil: "load" });
      await page.waitForSelector(".rig-dashboard-shell");
      assert.match(await page.$eval(".rig-spec-table", el => el.textContent), /Crowd-Facing PA/,
        "speaker roles must survive shared URL reload");
      assert.match(await page.$eval(".rig-spec-table", el => el.textContent), /DJ Booth Monitors/);
      assert.deepEqual(errors, [], "role-gated speaker journeys must not throw");
      assert.deepEqual(errors, [], "speaker package labels must not throw");
      await context.close();
      console.log("PASS: " + width + "px real catalog/render/owned-budget/no-overflow");
    }

    // A cheaper FLX2 with an already-owned compatible phone must not be
    // falsely rejected or force a laptop purchase. Verify real mobile DOM.
    const flx2Mobile = {
      name: "FLX2 mobile starter",
      items: [
        { slotId: "c", category: "controllers", itemId: "pioneer-ddj-flx2", qty: 1, owned: false },
        { slotId: "h", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
        { slotId: "s", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
        { slotId: "m", category: "laptops", itemId: "existing-mobile-device", qty: 1, owned: true }
      ]
    };
    const flx2Query = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(flx2Mobile)), "binary").toString("base64")
    );
    const flx2Visit = await visit(browser, 390, flx2Query);
    const flx2Alerts = await flx2Visit.page.$eval(".compat-items-grid", el => el.textContent);
    assert.equal(flx2Visit.metrics.spend, "$497", "FLX2 mobile route does not force a laptop");
    assert.match(flx2Alerts, /FLX2 Mobile Host, USB Audio and Power Need Verification/);
    assert.match(flx2Alerts, /some Android devices cannot/);
    assert.doesNotMatch(flx2Alerts, /Mobile Host Not Verified for This Controller/);
    await flx2Visit.context.close();

    // Accessories-only shared rigs must never show a green "Preliminary Match".
    const noController = {
      name: "Accessory-only rig",
      items: [
        { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true },
        { slotId: "sp", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
        { slotId: "host", category: "laptops", itemId: "macbook-air-m2", qty: 1, owned: true }
      ]
    };
    const noControllerQuery = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(noController)), "binary").toString("base64")
    );
    const missingController = await visit(browser, 390, noControllerQuery);
    const missingState = await missingController.page.evaluate(() => ({
      tag: document.querySelector(".compat-status-tag")?.textContent || "",
      readiness: Number((document.querySelector(".readiness-num")?.textContent || "").replace("%", "")),
      alerts: document.querySelector(".compat-items-grid")?.textContent || ""
    }));
    assert.match(missingState.tag, /Incompatible Configuration/);
    assert.match(missingState.alerts, /DJ Controller or Mixer Required/);
    assert.ok(missingState.readiness <= 40);
    assert.equal(await missingController.page.$eval('[data-route="master"]', el => el.dataset.status),
      "blocked", "missing controller must stop the visual audio route");
    await missingController.context.close();
    console.log("PASS: accessory-only shared rig visibly blocked as incomplete");

    // A standalone controller alone has no selected listening path.
    const noAudio = {
      name: "No listening device",
      items: [{ slotId: "ctrl", category: "controllers", itemId: "denon-prime-4-plus", qty: 1, owned: false }]
    };
    const noAudioQuery = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(noAudio)), "binary").toString("base64")
    );
    const silentRig = await visit(browser, 390, noAudioQuery);
    const silentState = await silentRig.page.evaluate(() => ({
      tag: document.querySelector(".compat-status-tag")?.textContent || "",
      readiness: Number((document.querySelector(".readiness-num")?.textContent || "").replace("%", "")),
      alerts: document.querySelector(".compat-items-grid")?.textContent || ""
    }));
    assert.match(silentState.tag, /Incompatible Configuration/);
    assert.match(silentState.alerts, /Headphones or Speakers Required/);
    assert.ok(silentState.readiness <= 40);
    await silentRig.context.close();
    console.log("PASS: standalone controller with no listening device is incomplete");

    // A second controller is counted in the budget but cannot silently inherit
    // the first controller's host and cable compatibility verdict.
    const twoControllers = {
      name: "Multi-controller routing needs review",
      items: [
        { slotId: "first", category: "controllers", itemId: "denon-prime-4-plus", qty: 1, owned: true },
        { slotId: "second", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1, owned: false },
        { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
        { slotId: "sp", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
        { slotId: "cable", category: "cables", itemId: "cable-rca-rca", qty: 1, owned: false }
      ]
    };
    const multiQuery = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(twoControllers)), "binary").toString("base64")
    );
    const multi = await visit(browser, 390, multiQuery);
    const multiState = await multi.page.evaluate(() => ({
      tag: document.querySelector(".compat-status-tag")?.textContent || "",
      readiness: Number((document.querySelector(".readiness-num")?.textContent || "").replace("%", "")),
      alerts: document.querySelector(".compat-items-grid")?.textContent || ""
    }));
    assert.match(multiState.tag, /Manual Routing Review Required/);
    assert.match(multiState.alerts, /Multiple controllers Need Manual Verification/);
    assert.ok(multiState.readiness <= 50);
    assert.deepEqual(multi.errors, []);
    // The compare modal must show every controller and actual unowned spend,
    // not just the first controller's unit price or the full owned valuation.
    await multi.page.click('[data-action="open-compare"]');
    await multi.page.waitForSelector("#compare-content-grid");
    const compareText = await multi.page.$eval("#compare-content-grid", el => el.textContent);
    assert.match(compareText, /To buy:\s*\$609/);
    assert.match(compareText, /Full value:\s*\$2,808/);
    assert.match(compareText, /Already owned:\s*\$2,199/);
    assert.match(compareText, /Denon DJ Prime 4\+ \(×1, Owned, \$2,199\)/);
    assert.match(compareText, /Pioneer DJ DDJ-FLX4 \(×1, Buy, \$299\)/);
    await multi.context.close();
    console.log("PASS: multi-controller shared rig warns that additional routing is unverified");

    // A quantity stepper can add a second physical controller within one
    // slot. The compatibility verdict must still require manual routing review.
    const quantityRig = {
      name: "Two controllers in one slot",
      items: [
        { slotId: "ctrl", category: "controllers", itemId: "denon-prime-4-plus", qty: 2, owned: false },
        { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false }
      ]
    };
    const quantityQuery = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(quantityRig)), "binary").toString("base64")
    );
    const quantity = await visit(browser, 390, quantityQuery);
    const quantityState = await quantity.page.evaluate(() => ({
      tag: document.querySelector(".compat-status-tag")?.textContent || "",
      readiness: Number((document.querySelector(".readiness-num")?.textContent || "").replace("%", "")),
      alerts: document.querySelector(".compat-items-grid")?.textContent || ""
    }));
    assert.match(quantityState.tag, /Manual Routing Review Required/);
    assert.match(quantityState.alerts, /Multiple controllers Need Manual Verification/);
    assert.ok(quantityState.readiness <= 50);
    assert.deepEqual(quantity.errors, []);
    await quantity.context.close();
    console.log("PASS: two controllers via one quantity stepper require routing review");

    // Connection auto-fix must add the recommended cable, not silently
    // replace an unrelated owned cable or discard its quantity. A buyer may
    // need both RCA and XLR cabling for different equipment/venues.
    const cableFixRig = {
      name: "Keep owned RCA when adding XLR",
      items: [
        { slotId: "ctrl", category: "controllers", itemId: "denon-prime-go", qty: 1, owned: false },
        { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
        { slotId: "sp", category: "speakers", itemId: "yamaha-hs5", qty: 1, owned: false },
        { slotId: "rca", category: "cables", itemId: "cable-rca-rca", qty: 2, owned: true }
      ]
    };
    const cableFixQuery = "?rig=" + encodeURIComponent(
      Buffer.from(encodeURIComponent(JSON.stringify(cableFixRig)), "binary").toString("base64")
    );
    const cableFix = await visit(browser, 390, cableFixQuery);
    const spendBeforeCable = await cableFix.page.$eval(".metric-val--spend", el =>
      Number(el.textContent.replace(/[^\d.]/g, "")));
    const fixSelector = '[data-action="auto-fix-cable"][data-cable-id="cable-xlr-xlr"]';
    assert.ok(await cableFix.page.$(fixSelector), "XLR suggestion must be available");
    assert.equal(await cableFix.page.$eval('[data-route="master"]', el => el.dataset.status),
      "missing", "unrelated RCA cable must not animate as a valid XLR connection");
    await cableFix.page.click(fixSelector);
    const cableFixResult = await cableFix.page.evaluate(() => ({
      state: JSON.parse(localStorage.getItem("offbeat.rig.active")),
      spend: Number((document.querySelector(".metric-val--spend")?.textContent || "").replace(/[^\d.]/g, "")),
      alerts: document.querySelector(".compat-items-grid")?.textContent || ""
    }));
    const originalCable = cableFixResult.state.items.find(s => s.itemId === "cable-rca-rca");
    const addedCable = cableFixResult.state.items.filter(s => s.itemId === "cable-xlr-xlr");
    assert.ok(originalCable, "auto-fix must preserve existing RCA cable");
    assert.equal(originalCable.qty, 2, "existing cable quantity must survive");
    assert.equal(originalCable.owned, true, "existing cable ownership must survive");
    assert.equal(addedCable.length, 1, "XLR fix must add exactly one cable slot");
    assert.equal(addedCable[0].owned, false, "new cable is not automatically owned");
    assert.equal(cableFixResult.spend, spendBeforeCable + 28, "only new cable price increases spend");
    assert.match(cableFixResult.alerts, /Listed Audio Connection Match/);
    assert.equal(await cableFix.page.$eval('[data-route="master"]', el => el.dataset.status),
      "listed", "adding a matching XLR pair must update the live route map");
    assert.deepEqual(cableFix.errors, [], "no JS errors after cable auto-fix");
    await cableFix.context.close();
    console.log("PASS: connection fix adds XLR without discarding owned RCA cables");

    // Guide-to-planner links must not wipe an existing saved shopping list.
    // Replacing a controller resets only its own purchase/quantity state;
    // accessory links append rather than replacing a different cable.
    const handoff = await visit(browser, 390);
    await handoff.page.evaluate(() => {
      localStorage.setItem("offbeat.rig.active", JSON.stringify({
        name: "Owner's Existing DJ Rig",
        items: [
          { slotId: "ctrl", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 2, owned: true },
          { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true },
          { slotId: "sp", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
          { slotId: "host", category: "laptops", itemId: "macbook-air-m2", qty: 1, owned: true },
          { slotId: "mic", category: "microphones", itemId: "mic-shure-sm58", qty: 1, owned: false },
          { slotId: "rca", category: "cables", itemId: "cable-rca-rca", qty: 1, owned: false }
        ]
      }));
    });
    async function followGuideLink(itemId) {
      await handoff.page.goto(base + "/build-your-dj-setup.html?add=" + encodeURIComponent(itemId), {
        waitUntil: "load", timeout: 20000
      });
      await handoff.page.waitForSelector(".rig-dashboard-shell", { timeout: 15000 });
      return handoff.page.evaluate(() => ({
        state: JSON.parse(localStorage.getItem("offbeat.rig.active")),
        url: location.search,
        spend: document.querySelector(".metric-val--spend")?.textContent.trim()
      }));
    }
    let linked = await followGuideLink("denon-prime-4-plus");
    let slots = linked.state.items;
    assert.equal(linked.state.name, "Owner's Existing DJ Rig", "preserve user-defined rig name");
    assert.equal(slots.length, 6, "controller swap must not discard other equipment");
    assert.deepEqual(
      slots.filter(s => s.category === "controllers").map(s => [s.itemId, s.qty, s.owned]),
      [["denon-prime-4-plus", 1, false]],
      "different controller must not inherit old model's quantity or owned state"
    );
    assert.equal(slots.find(s => s.category === "laptops").owned, true);
    assert.equal(slots.find(s => s.category === "headphones").owned, true);
    assert.ok(slots.some(s => s.itemId === "mic-shure-sm58"));
    assert.ok(slots.some(s => s.itemId === "cable-rca-rca"));
    assert.match(linked.url, /^\?rig=/, "guide import must yield shareable current rig URL");
    assert.ok(Number(linked.spend.replace(/[^\d.]/g, "")) > 2000,
      "spend must reflect new unowned controller, not silently reset to default rig");

    linked = await followGuideLink("cable-xlr-xlr");
    assert.ok(linked.state.items.some(s => s.itemId === "cable-rca-rca"),
      "adding XLR must preserve existing RCA cable");
    assert.ok(linked.state.items.some(s => s.itemId === "cable-xlr-xlr"),
      "new cable must appear in shopping list");
    const accessoryCount = linked.state.items.length;
    linked = await followGuideLink("cable-xlr-xlr");
    assert.equal(linked.state.items.length, accessoryCount,
      "following the same accessory link twice must not duplicate purchases");

    // Following a link for equipment already owned must not mark it unowned.
    await handoff.page.evaluate(() => {
      const state = JSON.parse(localStorage.getItem("offbeat.rig.active"));
      const controller = state.items.find(s => s.category === "controllers");
      controller.owned = true;
      controller.qty = 2;
      localStorage.setItem("offbeat.rig.active", JSON.stringify(state));
    });
    linked = await followGuideLink("denon-prime-4-plus");
    const same = linked.state.items.find(s => s.category === "controllers");
    assert.equal(same.owned, true, "same-product guide link preserves ownership");
    assert.equal(same.qty, 2, "same-product guide link preserves quantity");
    assert.deepEqual(handoff.errors, [], "guide handoffs must not throw browser errors");
    await handoff.context.close();
    console.log("PASS: guide-to-planner preserves rig, ownership, quantities and accessory purchases");

    // A real buyer selecting DDJ-GRV6 with a phone must see the supported
    // two-deck path and its limits, not a false "incompatible" verdict.
    // The same mobile host remains blocked for a controller not qualified here.
    function mobileRigLink(controllerId) {
      const state = { name: "Mobile host check", items: [
        { slotId: "ctrl", category: "controllers", itemId: controllerId, qty: 1, owned: false },
        { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true },
        { slotId: "host", category: "laptops", itemId: "existing-mobile-device", qty: 1, owned: true }
      ] };
      return "?rig=" + encodeURIComponent(Buffer.from(
        encodeURIComponent(JSON.stringify(state)), "binary").toString("base64"));
    }
    for (const width of [1440, 390]) {
      const mobileGRV6 = await visit(browser, width, mobileRigLink("alphatheta-ddj-grv6"));
      const shown = await mobileGRV6.page.evaluate(() => ({
        status: document.querySelector(".compat-status-tag")?.textContent.trim(),
        alerts: document.querySelector(".compat-items-grid")?.textContent || ""
      }));
      assert.match(shown.alerts, /GRV6 Mobile: Two Decks Only/);
      assert.match(shown.alerts, /channels 1 and 2/);
      assert.match(shown.alerts, /USB-C and Power Required/);
      assert.doesNotMatch(shown.alerts, /Mobile Host Not Verified for This Controller/);
      assert.doesNotMatch(shown.status, /Incompatible/);
      assert.deepEqual(mobileGRV6.errors, [], "GRV6 mobile UI must not throw");
      await mobileGRV6.context.close();
    }
    const mobileUnsupported = await visit(browser, 390, mobileRigLink("pioneer-ddj-flx10"));
    const blocked = await mobileUnsupported.page.$eval(".compat-items-grid", el => el.textContent);
    assert.match(blocked, /Mobile Host Not Verified for This Controller/);
    assert.equal(await mobileUnsupported.page.$eval('[data-route="host"]', el => el.dataset.status),
      "blocked", "unsupported phone/controller route must not show animated host compatibility");
    assert.deepEqual(mobileUnsupported.errors, [], "unverified mobile host UI must not throw");
    await mobileUnsupported.context.close();
    console.log("PASS: GRV6 supported two-deck mobile journey; unverified controller blocked");

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
