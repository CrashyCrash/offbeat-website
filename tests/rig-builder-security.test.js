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
    calculateRigStats: calculateRigStats
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
      price: 900, standalone: true }
  ], categories: [], presets: [] });
  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "usb-only", qty: 1 }
  ] }), true);
  const needsHost = api.runDeepCompatibilityChecks();
  assert.equal(needsHost.fatalErrors, 1);
  assert.ok(needsHost.readiness <= 40);
  assert.ok(needsHost.checks.some(check => check.type === "error" && /Host Computer Required/.test(check.title)));

  assert.equal(api.normalizeRigState({ items: [
    { slotId: "ctrl", category: "controllers", itemId: "standalone", qty: 1 }
  ] }), true);
  const standalone = api.runDeepCompatibilityChecks();
  assert.equal(standalone.fatalErrors, 0);
});
