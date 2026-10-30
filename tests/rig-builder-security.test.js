// Run: node --test tests/rig-builder-security.test.js
// No browser, network, or third-party dependencies required.
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../assets/rig-builder.js"), "utf8");
const hook = "  /* ---------------------------------------------------------------- Start */";
assert.equal(source.split(hook).length, 2, "test hook must match one startup point");

function harness(storageDisabled) {
  const memory = Object.create(null);
  const localStorage = {
    getItem(key) {
      if (storageDisabled) throw new Error("Storage disabled");
      return memory[key] ?? null;
    },
    setItem(key, value) {
      if (storageDisabled) throw new Error("Storage disabled");
      memory[key] = value;
    }
  };
  let lastUrl = null;
  const window = {
    localStorage,
    location: { pathname: "/build-your-dj-setup.html", search: "" },
    history: { replaceState(_state, _title, url) { lastUrl = url; } }
  };
  const document = {
    getElementById() { return {}; },
    readyState: "loading",
    addEventListener() {}
  };
  const injected = source.replace(hook, `  window.__testRig = {
    setCatalog: function (x) { CATALOG = x; },
    sanitizeRigState: sanitizeRigState,
    normalizeRigState: normalizeRigState,
    parseUrlOrLocalState: parseUrlOrLocalState,
    saveActiveState: saveActiveState,
    getRig: function () { return currentRig; },
    getSavedRigs: getSavedRigs,
    renderSavedRigsList: renderSavedRigsList,
    replaceSlotItem: replaceSlotItem,
    runDeepCompatibilityChecks: runDeepCompatibilityChecks,
    calculateRigStats: calculateRigStats,
    presetPriceBadge: presetPriceBadge,
    recommendNextUpgrade: recommendNextUpgrade,
    renderModularTableRow: renderModularTableRow,
    renderCompareGridContent: renderCompareGridContent,
    loadPresetData: loadPresetData
  };
` + hook);
  vm.runInNewContext(injected, { window, document, URLSearchParams, console, atob, btoa });
  window.__testRig.setCatalog({
    items: [
      { id: "pioneer-ddj-flx4", category: "controllers", price: 299 },
      { id: "sennheiser-hd25", category: "headphones", price: 149 }
    ],
    categories: [],
    presets: []
  });
  return { api: window.__testRig, memory, window, lastUrl: () => lastUrl };
}

function slot(id = "core-ctrl") {
  return { slotId: id, category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1, owned: false };
}

test("hostile shared identifiers cannot become HTML attributes", () => {
  const { api } = harness(false);
  const rig = api.sanitizeRigState({
    name: "<img src=x onerror=alert(1)>",
    items: [{ ...slot('x" onmouseover="alert(1)'), qty: 999999, owned: "true" }]
  });
  assert.equal(rig.items[0].slotId, "imported-0");
  assert.equal(rig.items[0].qty, 1);
  assert.equal(rig.items[0].owned, false);
  assert.equal(rig.name, "<img src=x onerror=alert(1)>");
});

test("unknown catalog items, category mismatches and oversized payloads fail closed", () => {
  const { api } = harness(false);
  assert.equal(api.sanitizeRigState({ items: [{ ...slot(), itemId: "not-in-catalog" }] }), null);
  assert.equal(api.sanitizeRigState({ items: [{ ...slot(), category: "headphones" }] }), null);
  assert.equal(api.sanitizeRigState({ items: Array.from({ length: 25 }, () => slot()) }), null);
  assert.equal(api.sanitizeRigState({ items: [] }), null);
});

test("duplicate IDs are unique and legacy preset links still work", () => {
  const { api } = harness(false);
  const rig = api.sanitizeRigState({ items: [
    slot("a"), slot("a"), slot("imported-2-1"), slot("imported-2-1")
  ] });
  assert.equal(new Set(rig.items.map(x => x.slotId)).size, 4);
  const legacy = api.sanitizeRigState({ slots: { controllers: "pioneer-ddj-flx4" } });
  assert.equal(legacy.items[0].itemId, "pioneer-ddj-flx4");
});

test("malicious URL is sanitized before entering the active rig", () => {
  const { api, window } = harness(false);
  const payload = { name: "Shared", items: [slot('x" onfocus="alert(1)')] };
  window.location.search = "?rig=" + encodeURIComponent(btoa(encodeURIComponent(JSON.stringify(payload))));
  api.parseUrlOrLocalState();
  assert.equal(api.getRig().items[0].slotId, "imported-0");
});

test("saved rigs ignore forged totals, exclude owned gear and escape hostile dates", () => {
  const { api, memory } = harness(false);
  memory["offbeat.rigs.saved"] = JSON.stringify([{
    name: "Saved", items: [{ ...slot(), qty: 2 }, { slotId: "owned-hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true }],
    totalCost: '<img src=x onerror=alert(1)>',
    date: '<img src=x onerror=alert(1)>'
  }]);
  assert.equal(api.getSavedRigs()[0].totalCost, 598);
  const markup = api.renderSavedRigsList();
  assert.match(markup, /&lt;img/);
  assert.match(markup, /\$598/);
  assert.doesNotMatch(markup, /\(<img/);
});

test("blocked browser storage does not prevent in-memory editing or share URL", () => {
  const { api, lastUrl } = harness(true);
  assert.doesNotThrow(() => api.saveActiveState());
  assert.match(lastUrl(), /\?rig=/);
  assert.deepEqual(Array.from(api.getSavedRigs()), []);
});

test("share links encode base64 plus and restore correctly without local storage", () => {
  const { api, memory, window, lastUrl } = harness(false);
  const name = "m~?wKQPW[GTy"; // Produces a '+' in base64(JSON-as-URI-component).
  assert.equal(api.normalizeRigState({ name, items: [slot()] }), true);
  api.saveActiveState();
  const url = lastUrl();
  assert.match(url, /%2B/, "literal plus must be percent-encoded in query strings");
  memory["offbeat.rig.active"] = ""; // Prove the shared URL works on a new device.
  window.location.search = new URL(url, "https://offbeatinc.com").search;
  assert.equal(api.normalizeRigState({ name: "Other", items: [slot()] }), true);
  api.parseUrlOrLocalState();
  assert.equal(api.getRig().name, name);
});

test("guide add of an existing secondary controller preserves the whole shared rig", () => {
  const { api, memory, window, lastUrl } = harness(false);
  api.setCatalog({ items: [
    { id: "pioneer-ddj-flx4", category: "controllers", price: 299 },
    { id: "denon-prime-4-plus", category: "controllers", price: 2199 },
    { id: "sennheiser-hd25", category: "headphones", price: 149 }
  ], categories: [], presets: [] });
  const shared = { name: "Two-controller comparison", items: [
    { slotId: "first", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1, owned: true },
    { slotId: "second", category: "controllers", itemId: "denon-prime-4-plus", qty: 2, owned: false },
    { slotId: "headphones", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true }
  ] };
  memory["offbeat.rig.active"] = JSON.stringify({ items: [slot()] });
  const encoded = btoa(encodeURIComponent(JSON.stringify(shared)));
  window.location.search = "?add=denon-prime-4-plus&rig=" + encodeURIComponent(encoded);
  api.parseUrlOrLocalState();
  const actual = api.getRig();
  assert.equal(actual.name, shared.name);
  assert.equal(actual.items.length, 3, "repeated add must not duplicate or replace a core device");
  assert.deepEqual(Array.from(actual.items, s => [s.slotId, s.itemId, s.qty, s.owned]),
    shared.items.map(s => [s.slotId, s.itemId, s.qty, s.owned]));
  assert.match(lastUrl(), /\?rig=/, "the unchanged rig remains shareable");
});

test("replacing an owned product resets the new purchase to not-owned", () => {
  const { api } = harness(false);
  const old = api.getRig().items[0];
  old.owned = true;
  assert.equal(api.replaceSlotItem(old, "sennheiser-hd25"), true);
  assert.equal(old.itemId, "sennheiser-hd25");
  assert.equal(old.category, "headphones");
  assert.equal(old.owned, false);
  assert.equal(api.replaceSlotItem(old, "not-in-catalog"), false);
  assert.equal(old.itemId, "sennheiser-hd25");
  assert.ok(api.calculateRigStats().purchaseCost >= 149);
});

test("RCA cable is not declared compatible with 3.5mm-only master output", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "flx2", category: "controllers", model: "DDJ-FLX2", price: 200,
      master_outputs: ["3.5mm Aux (Unbalanced)"] },
    { id: "dm40", category: "speakers", model: "DM-40D", price: 180,
      inputs: ["RCA (Unbalanced)", "3.5mm Stereo Mini"] },
    { id: "cable-rca-rca", category: "cables", price: 12 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "c", category: "controllers", itemId: "flx2", qty: 1 },
    { slotId: "s", category: "speakers", itemId: "dm40", qty: 1 },
    { slotId: "x", category: "cables", itemId: "cable-rca-rca", qty: 1 }
  ] }), true);
  const connection = api.runDeepCompatibilityChecks().checks[0];
  assert.equal(connection.type, "warning");
  assert.equal(connection.fixCableId, null);
  assert.match(connection.desc, /3.5mm stereo cable/);
});

test("matching XLR output and input select XLR cable, never RCA fallback", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "flx10", category: "controllers", model: "DDJ-FLX10", price: 1600,
      master_outputs: ["XLR (Balanced)", "RCA (Unbalanced)"] },
    { id: "hs5", category: "speakers", model: "HS5", price: 400,
      inputs: ["XLR3-31 (Balanced)"] },
    { id: "cable-xlr-xlr", category: "cables", price: 28 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "c", category: "controllers", itemId: "flx10", qty: 1 },
    { slotId: "s", category: "speakers", itemId: "hs5", qty: 1 }
  ] }), true);
  assert.equal(api.runDeepCompatibilityChecks().checks[0].fixCableId, "cable-xlr-xlr");
});


test("a laptop-dependent controller with no computer is not declared playable", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "usb-only", category: "controllers", brand: "Example", model: "USB Controller",
      price: 250, standalone: false },
    { id: "standalone", category: "controllers", brand: "Example", model: "Standalone Deck",
      price: 900, standalone: true },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "usb-only", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 }
  ] }), true);
  const needsHost = api.runDeepCompatibilityChecks();
  assert.equal(needsHost.fatalErrors, 1);
  assert.ok(needsHost.readiness <= 40);
  assert.ok(needsHost.checks.some(check => check.type === "error" && /Host Computer Required/.test(check.title)));

  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "standalone", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 }
  ] }), true);
  const standalone = api.runDeepCompatibilityChecks();
  assert.equal(standalone.fatalErrors, 0);
});


test("accessory-only rigs cannot claim a playable preliminary match", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "headphones", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "speakers", category: "speakers", price: 199, inputs: ["RCA"] },
    { id: "laptop", category: "laptops", price: 999 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "hp", category: "headphones", itemId: "headphones", qty: 1 },
    { slotId: "spk", category: "speakers", itemId: "speakers", qty: 1 },
    { slotId: "host", category: "laptops", itemId: "laptop", qty: 1 }
  ] }), true);
  const result = api.runDeepCompatibilityChecks();
  assert.equal(result.fatalErrors, 1);
  assert.ok(result.readiness <= 40);
  assert.ok(result.checks.some(check => check.type === "error" && /Controller or Mixer Required/.test(check.title)));
});

test("included headphone plugs and adapters do not trigger unnecessary purchases", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "flx4", category: "controllers", price: 299, model: "FLX4",
      standalone: false, headphone_jack: '3.5mm (1/8")' },
    { id: "hd25", category: "headphones", price: 149,
      jack_type: '3.5mm with screw-on 1/4" adapter included' },
    { id: "host", category: "laptops", price: 999 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "flx4", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hd25", qty: 1 },
    { slotId: "host", category: "laptops", itemId: "host", qty: 1 }
  ] }), true);
  assert.ok(!api.runDeepCompatibilityChecks().checks.some(c => /Headphone.*Adapter/.test(c.title)));
});

test("a genuine headphone plug mismatch warns without an unverified auto-add", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "mini-controller", category: "controllers", price: 299,
      standalone: true, headphone_jack: "3.5mm" },
    { id: "quarter-only", category: "headphones", price: 149,
      jack_type: '1/4" plug only' }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "mini-controller", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "quarter-only", qty: 1 }
  ] }), true);
  const result = api.runDeepCompatibilityChecks();
  const advisory = result.checks.find(c => /Headphone Connector Adapter Needed/.test(c.title));
  assert.equal(advisory.type, "warning");
  assert.equal(advisory.fixCableId, null);
  assert.match(advisory.desc, /1\/4-inch female to 3.5mm male/);
});

test("additional controllers cannot inherit a green single-controller compatibility verdict", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "standalone", category: "controllers", brand: "Example", model: "Standalone Deck",
      price: 900, standalone: true, master_outputs: ["RCA (Unbalanced)"] },
    { id: "usb-only", category: "controllers", brand: "Example", model: "Laptop Controller",
      price: 250, standalone: false, master_outputs: ["RCA (Unbalanced)"] },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "sp", category: "speakers", price: 180, inputs: ["RCA (Unbalanced)"] },
    { id: "cable-rca-rca", category: "cables", price: 12 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "primary", category: "controllers", itemId: "standalone", qty: 1 },
    { slotId: "second", category: "controllers", itemId: "usb-only", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 },
    { slotId: "sp", category: "speakers", itemId: "sp", qty: 1 },
    { slotId: "cable", category: "cables", itemId: "cable-rca-rca", qty: 1 }
  ] }), true);
  const verdict = api.runDeepCompatibilityChecks();
  assert.equal(verdict.requiresManualReview, true);
  assert.ok(verdict.readiness <= 50);
  assert.ok(verdict.checks.some(c => /Multiple controllers Need Manual Verification/.test(c.title)));
  assert.equal(api.calculateRigStats().totalValue, 1491,
    "all controllers must remain in the purchase valuation");
});

test("quantity steppers count physical core devices, not only slots", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "deck", category: "controllers", model: "Standalone Deck", price: 900, standalone: true },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "cable", category: "cables", price: 12 }
  ], categories: [], presets: [] });
  const rig = [
    { slotId: "deck", category: "controllers", itemId: "deck", qty: 2, owned: false },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1, owned: false },
    { slotId: "cable", category: "cables", itemId: "cable", qty: 4, owned: false }
  ];
  assert.equal(api.normalizeRigState({ items: rig }), true);
  const doubledController = api.runDeepCompatibilityChecks();
  assert.equal(doubledController.requiresManualReview, true);
  assert.ok(doubledController.readiness <= 50);
  assert.ok(doubledController.checks.some(c => /Multiple controllers Need Manual Verification/.test(c.title)));
  assert.equal(api.calculateRigStats().totalValue, 1997,
    "the budget must include two actual controllers and four accessory cables");

  rig[0].qty = 1;
  rig[1].qty = 2;
  assert.equal(api.normalizeRigState({ items: rig }), true);
  const doubledHeadphones = api.runDeepCompatibilityChecks();
  assert.equal(doubledHeadphones.requiresManualReview, true);
  assert.ok(doubledHeadphones.checks.some(c => /Multiple headphones Need Manual Verification/.test(c.title)));

  rig[1].qty = 1;
  assert.equal(api.normalizeRigState({ items: rig }), true);
  const accessoriesOnly = api.runDeepCompatibilityChecks();
  assert.equal(accessoriesOnly.requiresManualReview, false,
    "four accessory cables alone must not trigger multi-core routing warnings");
});

test("a single controller is not penalized for multiple accessory cables", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "deck", category: "controllers", model: "Standalone Deck", price: 900, standalone: true },
    { id: "cable1", category: "cables", price: 12 },
    { id: "cable2", category: "cables", price: 15 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "deck", qty: 1 },
    { slotId: "c1", category: "cables", itemId: "cable1", qty: 1 },
    { slotId: "c2", category: "cables", itemId: "cable2", qty: 1 }
  ] }), true);
  const verdict = api.runDeepCompatibilityChecks();
  assert.equal(verdict.requiresManualReview, false);
  assert.ok(!verdict.checks.some(c => /Multiple .* Need Manual Verification/.test(c.title)));
});

test("additional speakers require manual review even when the first speaker matches", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "deck", category: "controllers", model: "Standalone Deck", price: 900, standalone: true,
      master_outputs: ["RCA (Unbalanced)"] },
    { id: "rca", category: "speakers", model: "RCA Monitor", price: 180, inputs: ["RCA (Unbalanced)"] },
    { id: "xlr", category: "speakers", model: "XLR PA", price: 500, inputs: ["XLR (Balanced)"] },
    { id: "cable-rca-rca", category: "cables", price: 12 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "deck", qty: 1 },
    { slotId: "sp1", category: "speakers", itemId: "rca", qty: 1 },
    { slotId: "sp2", category: "speakers", itemId: "xlr", qty: 1 },
    { slotId: "cable", category: "cables", itemId: "cable-rca-rca", qty: 1 }
  ] }), true);
  const verdict = api.runDeepCompatibilityChecks();
  assert.equal(verdict.requiresManualReview, true);
  assert.ok(verdict.readiness <= 50);
  assert.ok(verdict.checks.some(c => /Multiple speakers Need Manual Verification/.test(c.title)));
});

test("a controller without headphones or speakers is not declared ready", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "standalone", category: "controllers", brand: "Example", model: "Standalone Deck",
      price: 900, standalone: true },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "standalone", qty: 1 }
  ] }), true);
  const incomplete = api.runDeepCompatibilityChecks();
  assert.ok(incomplete.fatalErrors > 0);
  assert.ok(incomplete.readiness <= 40);
  assert.ok(incomplete.checks.some(c => /Headphones or Speakers Required/.test(c.title)));
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "standalone", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 }
  ] }), true);
  const listening = api.runDeepCompatibilityChecks();
  assert.equal(listening.fatalErrors, 0, "headphones-only practice remains supported");
});

test("starter explicitly assumes an existing phone, not a $999 laptop", () => {
  const { api } = harness(false);
  const host = api.getRig().items.find(s => s.category === "laptops");
  assert.equal(host.itemId, "existing-mobile-device");
  assert.equal(host.owned, true);
  assert.ok(!api.getRig().items.some(s => s.category === "stands"));
});

test("FLX4 and FLX2 mobile routes are conditional; unsupported controllers fail closed", () => {
  const { api } = harness(false);
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  api.setCatalog(catalog);
  const items = [
    { slotId: "c", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1 },
    { slotId: "h", category: "headphones", itemId: "sennheiser-hd25", qty: 1 },
    { slotId: "s", category: "speakers", itemId: "pioneer-dm40d", qty: 1 },
    { slotId: "m", category: "laptops", itemId: "existing-mobile-device", qty: 4, owned: false }
  ];
  assert.equal(api.normalizeRigState({ items }), true);
  assert.equal(api.getRig().items[3].owned, true, "a zero-cost placeholder cannot be sold as a phone");
  assert.equal(api.getRig().items[3].qty, 1, "shared links cannot add four free existing devices");
  const mobile = api.runDeepCompatibilityChecks();
  assert.equal(mobile.fatalErrors, 0);
  assert.ok(mobile.warnings > 0, "software, power and audio must be verified");
  assert.ok(mobile.checks.some(c => /Mobile Host, USB Audio and Power/.test(c.title) && /9V\/3A/.test(c.desc)));
  assert.equal(api.calculateRigStats().purchaseCost, 597);
  assert.equal(api.recommendNextUpgrade(), null, "do not upsell a laptop stand to phone users");

  // Manufacturer explicitly lists FLX2 USB-C mobile support, unlike FLX10.
  // Its conditional phone route is $100 cheaper and must not be rejected.
  items[0].itemId = "pioneer-ddj-flx2";
  assert.equal(api.normalizeRigState({ items }), true);
  const flx2 = api.runDeepCompatibilityChecks();
  assert.equal(flx2.fatalErrors, 0);
  assert.ok(flx2.warnings > 0);
  assert.ok(flx2.checks.some(c => /FLX2 Mobile Host, USB Audio and Power/.test(c.title) &&
    /some Android devices cannot/.test(c.desc) && /Bluetooth MIDI/.test(c.desc)));
  assert.equal(api.calculateRigStats().purchaseCost, 497);
  assert.equal(api.recommendNextUpgrade(), null, "FLX2 mobile users need no laptop stand");

  items[0].itemId = "pioneer-ddj-flx10";
  assert.equal(api.normalizeRigState({ items }), true);
  const other = api.runDeepCompatibilityChecks();
  assert.ok(other.fatalErrors > 0 && other.readiness <= 40);
  assert.ok(other.checks.some(c => /Mobile Host Not Verified/.test(c.title)));
});

test("all four preset badges equal full current catalog totals", () => {
  const { api } = harness(false);
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  api.setCatalog(catalog);
  const expected = {
    "bedroom-starter": 597,
    "club-ready": 3230,
    "mobile-pro": 3052,
    "traktor-techno": 1780
  };
  assert.equal(catalog.presets.length, Object.keys(expected).length);
  for (const preset of catalog.presets) {
    const badge = "Est. $" + expected[preset.id].toLocaleString("en-US") + " total";
    assert.equal(api.presetPriceBadge(preset), badge, preset.id + " computed badge");
    assert.equal(preset.badge, badge, preset.id + " catalog badge");
  }
});


test("RCA-only four-channel controllers never receive a fabricated balanced-monitor upsell", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "rca-four", category: "controllers", brand: "Example", model: "RCA Four",
      price: 600, channels: 4, standalone: false, master_outputs: ["RCA (Unbalanced)"] },
    { id: "xlr-four", category: "controllers", brand: "Example", model: "XLR Four",
      price: 900, channels: 4, standalone: false, master_outputs: ["XLR (Balanced)"] },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "speakers", category: "speakers", price: 150, inputs: ["RCA (Unbalanced)"] },
    { id: "host", category: "laptops", price: 999 },
    { id: "laptop-stand-pyle", category: "stands", brand: "Pyle", model: "Laptop Stand", price: 29 },
    { id: "yamaha-hs5", category: "speakers", brand: "Yamaha", model: "HS5 Pair", price: 398 }
  ], categories: [], presets: [] });
  const items = [
    { slotId: "ctrl", category: "controllers", itemId: "rca-four", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 },
    { slotId: "sp", category: "speakers", itemId: "speakers", qty: 1 },
    { slotId: "host", category: "laptops", itemId: "host", qty: 1 },
    { slotId: "stand", category: "stands", itemId: "laptop-stand-pyle", qty: 1 }
  ];
  assert.equal(api.normalizeRigState({ items }), true);
  assert.equal(api.recommendNextUpgrade(), null, "RCA-only four-channel deck must not suggest balanced monitors");
  items[0].itemId = "xlr-four";
  assert.equal(api.normalizeRigState({ items }), true);
  const upgrade = api.recommendNextUpgrade();
  assert.equal(upgrade.targetId, "yamaha-hs5");
  assert.match(upgrade.desc, /required pair quantity, cabling/);
});

test("optional USB-media upsell requires a standalone player and absent storage", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "usb-controller", category: "controllers", brand: "Example", model: "Laptop Controller",
      price: 299, standalone: false },
    { id: "standalone", category: "controllers", brand: "Example", model: "Standalone",
      price: 999, standalone: true },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "host", category: "laptops", price: 999 },
    { id: "stand", category: "stands", price: 29 },
    { id: "usb-sandisk-extreme", category: "storage", brand: "SanDisk", model: "Extreme", price: 28 }
  ], categories: [], presets: [] });
  const items = [
    { slotId: "ctrl", category: "controllers", itemId: "usb-controller", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 },
    { slotId: "host", category: "laptops", itemId: "host", qty: 1 },
    { slotId: "stand", category: "stands", itemId: "stand", qty: 1 }
  ];
  assert.equal(api.normalizeRigState({ items }), true);
  assert.equal(api.recommendNextUpgrade(), null, "computer-dependent deck cannot load a DJ set from USB");
  items[0].itemId = "standalone";
  assert.equal(api.normalizeRigState({ items }), true);
  const upgrade = api.recommendNextUpgrade();
  assert.equal(upgrade.targetId, "usb-sandisk-extreme");
  assert.doesNotMatch(upgrade.desc, /zero lag|guarantee/i);
  items.push({ slotId: "media", category: "storage", itemId: "usb-sandisk-extreme", qty: 1 });
  assert.equal(api.normalizeRigState({ items }), true);
  assert.equal(api.recommendNextUpgrade(), null, "existing storage must not be upsold again");
});

test("incomplete or multi-device rigs do not show optional shopping upsells", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "usb-controller", category: "controllers", brand: "Example", model: "USB",
      price: 299, standalone: false },
    { id: "standalone", category: "controllers", brand: "Example", model: "Standalone",
      price: 999, standalone: true },
    { id: "hp", category: "headphones", price: 149, jack_type: "3.5mm" },
    { id: "usb-sandisk-extreme", category: "storage", brand: "SanDisk", model: "Extreme", price: 28 }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "usb-controller", qty: 1 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 }
  ] }), true);
  assert.equal(api.recommendNextUpgrade(), null, "missing host is more important than optional gear");
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "standalone", qty: 2 },
    { slotId: "hp", category: "headphones", itemId: "hp", qty: 1 }
  ] }), true);
  assert.equal(api.recommendNextUpgrade(), null, "multi-controller routing must be reviewed before upselling");
});

test("mobile wedding preset requires independent microphone input and cable review", () => {
  const { api } = harness(false);
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  api.setCatalog(catalog);
  const preset = catalog.presets.find(p => p.id === "mobile-pro");
  assert.ok(preset, "mobile wedding preset must exist");
  const items = Object.entries(preset.slots).map(([category, itemId], i) => ({
    slotId: "preset-" + i, category, itemId, qty: 1, owned: false
  }));
  assert.equal(api.normalizeRigState({ items }), true);
  const withMic = api.runDeepCompatibilityChecks();
  assert.equal(withMic.requiresManualReview, true);
  assert.ok(withMic.readiness <= 50);
  assert.ok(withMic.checks.some(c => c.title === "Microphone Input and Cable Need Verification" &&
    /XLR speaker output or cable does not prove/.test(c.desc)));
  assert.equal(api.recommendNextUpgrade(withMic), null,
    "optional upsells must not supersede an unverified microphone signal path");
  assert.equal(api.normalizeRigState({ items: items.filter(s => s.category !== "microphones") }), true);
  const withoutMic = api.runDeepCompatibilityChecks();
  assert.equal(withoutMic.requiresManualReview, false);
  assert.ok(!withoutMic.checks.some(c => /Microphone Input/.test(c.title)));
});

test("zero-cost standalone mode is not sold as an unrelated USB drive", () => {
  const { api } = harness(false);
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  api.setCatalog(catalog);
  const standalone = { slotId: "host", category: "laptops",
    itemId: "standalone-usb-only", qty: 1, owned: false };
  const row = api.renderModularTableRow(standalone);
  assert.match(row, /No laptop purchase/);
  assert.match(row, /Setup mode — no hardware purchase/);
  assert.doesNotMatch(row, /amazon\.com|sweetwater\.com|reverb\.com/);
  const realItem = api.renderModularTableRow({
    slotId: "ctrl", category: "controllers", itemId: "denon-prime-4-plus",
    qty: 1, owned: false
  });
  assert.match(realItem, /amazon\.com/);
  assert.match(realItem, /sweetwater\.com/);
});

test("KRK Classic 5 catalog entry never blends ROKIT G4 connectors or DSP", () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  const classic = catalog.items.find(item => item.id === "krk-rokit-5-g4");
  assert.ok(classic, "preserve legacy item ID for existing shared rigs");
  assert.equal(classic.model, "Classic 5 (Pair)");
  assert.match(classic.driver_size, /glass-aramid/i);
  assert.match(classic.sound_modes, /analog/i);
  assert.doesNotMatch(classic.sound_modes, /DSP/i);
  assert.deepEqual(classic.inputs, [
    "XLR (Balanced)", '1/4" TRS (Balanced)', "RCA (Unbalanced)"
  ]);
  assert.match(classic.spec_source, /^https:\/\/www\.krkmusic\.com\/products\/classic-5-/);
  assert.match(classic.amazon_search, /Classic 5/);
  assert.doesNotMatch(classic.model, /ROKIT|G4/i);
});

test("guide add preserves explicit shared rig over unrelated local state", () => {
  const { api, memory, window } = harness(false);
  const shared = { name: "Shared buyer build", items: [{ ...slot(), qty: 2, owned: true }] };
  memory["offbeat.rig.active"] = JSON.stringify({
    name: "Unrelated saved build", items: [{ ...slot(), qty: 1, owned: false }]
  });
  window.location.search = "?rig=" +
    encodeURIComponent(btoa(encodeURIComponent(JSON.stringify(shared)))) +
    "&add=sennheiser-hd25";
  api.parseUrlOrLocalState();
  const rig = api.getRig();
  assert.equal(rig.name, "Shared buyer build");
  assert.equal(rig.items.length, 2);
  assert.equal(rig.items[0].qty, 2);
  assert.equal(rig.items[0].owned, true);
  assert.equal(rig.items[1].itemId, "sennheiser-hd25");
  assert.equal(rig.items[1].owned, false);
});

test("corrupt shared rig falls back to valid saved rig during guide add", () => {
  const { api, memory, window } = harness(false);
  memory["offbeat.rig.active"] = JSON.stringify({
    name: "Saved fallback", items: [{ ...slot(), owned: true }]
  });
  window.location.search = "?rig=not-base64!&add=sennheiser-hd25";
  api.parseUrlOrLocalState();
  assert.equal(api.getRig().name, "Saved fallback");
  assert.equal(api.getRig().items.length, 2);
  assert.equal(api.getRig().items[0].owned, true);
});

test("adding an already-selected shared item does not reset owned quantity", () => {
  const { api, memory, window } = harness(false);
  const shared = { name: "Owned controller", items: [{ ...slot(), qty: 3, owned: true }] };
  memory["offbeat.rig.active"] = JSON.stringify({ name: "Other", items: [slot()] });
  window.location.search = "?rig=" +
    encodeURIComponent(btoa(encodeURIComponent(JSON.stringify(shared)))) +
    "&add=pioneer-ddj-flx4";
  api.parseUrlOrLocalState();
  assert.equal(api.getRig().name, "Owned controller");
  assert.equal(api.getRig().items.length, 1);
  assert.equal(api.getRig().items[0].qty, 3);
  assert.equal(api.getRig().items[0].owned, true);
});

test("rig comparison shows every controller, quantities, ownership and real spend", () => {
  const { api } = harness(false);
  api.setCatalog({
    items: [
      { id: "a", category: "controllers", brand: "Alpha", model: "Controller", price: 299 },
      { id: "b", category: "controllers", brand: "Denon", model: "Prime 4+", price: 2199 },
      { id: "hp", category: "headphones", brand: "Sennheiser", model: "HD 25", price: 149 }
    ],
    categories: [
      { id: "controllers", name: "Controllers" },
      { id: "headphones", name: "Headphones" }
    ],
    presets: []
  });
  const markup = api.renderCompareGridContent({
    name: "Owned <Rig>",
    items: [
      { slotId: "first", category: "controllers", itemId: "a", qty: 2, owned: true },
      { slotId: "second", category: "controllers", itemId: "b", qty: 1, owned: false },
      { slotId: "hp", category: "headphones", itemId: "hp", qty: 1, owned: false }
    ]
  }, {
    name: "New",
    items: [{ slotId: "first", category: "controllers", itemId: "b", qty: 1, owned: false }]
  });
  assert.match(markup, /To buy: \$2,348/);
  assert.match(markup, /Full value: \$2,946 · Already owned: \$598/);
  assert.match(markup, /Alpha Controller \(×2, Owned, \$598\)/);
  assert.match(markup, /Denon Prime 4\+ \(×1, Buy, \$2,199\)/);
  assert.match(markup, /Sennheiser HD 25 \(×1, Buy, \$149\)/);
  assert.match(markup, /To buy: \$2,199/);
  assert.match(markup, /Owned &lt;Rig&gt;/);
  assert.doesNotMatch(markup, /Owned <Rig>/);
});

test("manufacturer-supplied DM-40D lead connects FLX2 and FLX4 without another purchase", () => {
  const { api } = harness(false);
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  api.setCatalog(catalog);
  const dm = catalog.items.find(item => item.id === "pioneer-dm40d");
  assert.equal(dm.included_audio_cable_3_5mm_to_rca, true);
  const starter = catalog.presets.find(p => p.id === "bedroom-starter");
  assert.equal(starter.slots.cables, undefined, "starter must not bill a redundant RCA lead");
  for (const controllerId of ["pioneer-ddj-flx4", "pioneer-ddj-flx2"]) {
    const items = [
      { slotId: "controller", category: "controllers", itemId: controllerId, qty: 1, owned: false },
      { slotId: "speaker", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
      { slotId: "headphones", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
      { slotId: "host", category: "laptops", itemId: "macbook-air-m2", qty: 1, owned: false }
    ];
    assert.equal(api.normalizeRigState({ name: "Included cable", items }), true);
    const checks = api.runDeepCompatibilityChecks().checks;
    assert.ok(checks.some(c => c.title === "Included Speaker Cable Matches" && c.type === "success"),
      controllerId + " must recognize the supplied cable");
    assert.ok(!checks.some(c => c.title === "Audio Cable Needed"),
      controllerId + " must not upsell a cable already included");
  }
  const withExtra = [
    { slotId: "controller", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1 },
    { slotId: "speaker", category: "speakers", itemId: "pioneer-dm40d", qty: 1 },
    { slotId: "extra-cable", category: "cables", itemId: "cable-rca-rca", qty: 1 }
  ];
  assert.equal(api.normalizeRigState({ name: "Extra cable", items: withExtra }), true);
  const extraChecks = api.runDeepCompatibilityChecks().checks;
  assert.ok(extraChecks.some(c => c.title === "Separate Cable May Be Unnecessary" && c.type === "warning"),
    "existing optional cable must remain in the rig but be flagged");
  assert.equal(api.getRig().items.length, 3, "do not delete user-selected equipment");
});

// Real catalog and executed compatibility verdict: the GRV6 mobile path is
// valid but limited to two decks, while unrelated controllers stay blocked.
test("vendor-qualified GRV6 mobile routing and PRIME 4+ booth sockets", () => {
  const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, "../assets/dj-gear-catalog.json"), "utf8"));
  const prime = catalog.items.find(item => item.id === "denon-prime-4-plus");
  assert.deepEqual(prime.master_outputs, [
    "XLR (Balanced)", "RCA (Unbalanced)", "Booth XLR (Balanced)", "Zone XLR (Balanced)"
  ]);
  assert.equal(prime.spec_source, "https://www.denondj.com/prime-4-plus");
  const grv = catalog.items.find(item => item.id === "alphatheta-ddj-grv6");
  assert.ok(grv.spec_source.includes("pioneerdj.com") && grv.spec_source.includes("ddj-grv6"));

  const { api } = harness(false);
  api.setCatalog(catalog);
  const rig = { name: "GRV6 phone route", items: [
    { slotId: "ctrl", category: "controllers", itemId: "alphatheta-ddj-grv6", qty: 1, owned: false },
    { slotId: "hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: true },
    { slotId: "host", category: "laptops", itemId: "existing-mobile-device", qty: 1, owned: true }
  ] };
  assert.equal(api.normalizeRigState(rig), true);
  const result = api.runDeepCompatibilityChecks();
  assert.equal(result.fatalErrors, 0, "official GRV6 mobile route must not be falsely blocked");
  const mobile = result.checks.find(check => /GRV6 Mobile/.test(check.title));
  assert.ok(mobile, "limited mobile route must remain visible");
  assert.equal(mobile.type, "warning");
  assert.match(mobile.desc, /channels 1 and 2/);
  assert.match(mobile.desc, /no Bluetooth/);
  assert.ok(mobile.desc.includes("9V/3A"));
  assert.ok(result.warnings > 0, "mobile mode must not be labelled fully verified");

  rig.items[0].itemId = "pioneer-ddj-flx10";
  assert.equal(api.normalizeRigState(rig), true);
  const unsupported = api.runDeepCompatibilityChecks();
  assert.ok(unsupported.fatalErrors > 0, "unverified controller mobile route remains fail-closed");
  assert.ok(unsupported.checks.some(check => check.title === "Mobile Host Not Verified for This Controller"));
});

test("audience use rejects nearfield monitors even when XLR connectors and cable match", () => {
  const { api } = harness(false);
  api.setCatalog({ items: [
    { id: "ctrl", category: "controllers", brand: "Example", model: "Deck", price: 900,
      standalone: true, master_outputs: ["XLR (Balanced)"] },
    { id: "near", category: "speakers", model: "Studio Monitor", price: 250,
      speaker_role: "nearfield", inputs: ["XLR (Balanced)"] },
    { id: "pa", category: "speakers", model: "Powered PA", price: 550,
      speaker_role: "audience_pa", inputs: ["XLR (Balanced)"] },
    { id: "xlr", category: "cables", model: "XLR Pair", price: 30 }
  ], categories: [], presets: [] });
  const controller = { slotId: "ctrl", category: "controllers", itemId: "ctrl", qty: 1 };
  const speaker = { slotId: "spk", category: "speakers", itemId: "near", qty: 1 };
  const cable = { slotId: "cable", category: "cables", itemId: "xlr", qty: 1 };
  assert.equal(api.normalizeRigState({ context: "audience", items: [controller, speaker, cable] }), true);
  const bad = api.runDeepCompatibilityChecks();
  assert.equal(bad.fatalErrors, 1);
  assert.ok(bad.readiness <= 40);
  assert.ok(bad.checks.some(c => c.title === "Nearfield Studio Monitors Are Not Audience PA"));
  assert.ok(bad.checks.some(c => c.title === "Audience PA System Not Selected"));

  assert.equal(api.normalizeRigState({ context: "audience", items: [
    controller, { ...speaker, itemId: "pa" }, cable
  ] }), true);
  const pa = api.runDeepCompatibilityChecks();
  assert.equal(pa.fatalErrors, 0);
  assert.equal(pa.requiresManualReview, true, "listed PA is not a venue coverage certificate");
  assert.ok(pa.readiness <= 50);
  assert.ok(pa.checks.some(c => c.title === "Audience Coverage and Deployment Need Verification"));

  assert.equal(api.normalizeRigState({ context: "studio", items: [controller, speaker, cable] }), true);
  const studio = api.runDeepCompatibilityChecks();
  assert.equal(studio.fatalErrors, 0);
  assert.ok(!studio.checks.some(c => c.title === "Audience PA System Not Selected"));
});

test("audience context is validated, shareable and preserved in saved rig sanitization", () => {
  const { api, window, memory, lastUrl } = harness(false);
  const selected = { name: "Venue", context: "audience", items: [slot()] };
  assert.equal(api.normalizeRigState(selected), true);
  api.saveActiveState();
  assert.match(lastUrl(), /\?rig=/);
  memory["offbeat.rig.active"] = "";
  window.location.search = new URL(lastUrl(), "https://offbeatinc.com").search;
  assert.equal(api.normalizeRigState({ name: "Desk", items: [slot()] }), true);
  api.parseUrlOrLocalState();
  assert.equal(api.getRig().context, "audience");
  assert.equal(api.sanitizeRigState({ context: "<script>", items: [slot()] }).context, "studio");
  assert.equal(api.sanitizeRigState({ items: [slot()] }).context, "studio");
});

test("mobile preset chooses audience mode; switching presets resets context", () => {
  const { api } = harness(false);
  const mobile = { name: "Mobile", context: "audience", slots: { controllers: "pioneer-ddj-flx4" } };
  const bedroom = { name: "Bedroom", context: "studio", slots: { controllers: "pioneer-ddj-flx4" } };
  api.loadPresetData(mobile);
  assert.equal(api.getRig().context, "audience");
  api.loadPresetData(bedroom);
  assert.equal(api.getRig().context, "studio");
});
