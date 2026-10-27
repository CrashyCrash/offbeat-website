/* =============================================================================
   Offbeat Inc. — My DJ Rig Architect & Gear Planner
   "The PCPartPicker of DJ Equipment" (2026 Relaunch Edition)
   ========================================================================== */

(function () {
  "use strict";

  var CATALOG = null;
  var audioCtx = null;
  var soundEnabled = safeStorageGet("offbeat.rig.sfx") !== "muted";

  // Browsers may deny storage access; the planner must still work in memory.
  function safeStorageGet(key) {
    try { return window.localStorage.getItem(key); } catch (e) { return null; }
  }
  function safeStorageSet(key, value) {
    try { window.localStorage.setItem(key, value); return true; }
    catch (e) { return false; }
  }

  // Active Rig State (Supports modular items, quantities, and owned gear)
  var currentRig = {
    name: "My Custom DJ Rig",
    items: [
      { slotId: "core-ctrl", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1, owned: false },
      { slotId: "core-hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
      { slotId: "core-spk", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
      { slotId: "core-host", category: "laptops", itemId: "macbook-air-m2", qty: 1, owned: true },
      { slotId: "core-stand", category: "stands", itemId: "laptop-stand-pyle", qty: 1, owned: false },
      { slotId: "core-cable", category: "cables", itemId: "cable-rca-rca", qty: 1, owned: false }
    ]
  };

  // Active slot being edited in modal
  var activeModalSlotId = null;
  var activeModalCategory = null;

  // DOM Mount Root
  var builderRoot = document.getElementById("rig-app-root");
  if (!builderRoot) return;

  /* ------------------------------------------------------------- Web Audio Feedback */
  function playClickSfx(type) {
    if (!soundEnabled) return;
    try {
      if (!audioCtx) {
        var AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) audioCtx = new AudioContext();
      }
      if (!audioCtx || audioCtx.state === "suspended") {
        if (audioCtx && audioCtx.resume) audioCtx.resume();
      }
      if (!audioCtx) return;

      var now = audioCtx.currentTime;
      var osc = audioCtx.createOscillator();
      var gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      if (type === "toggle") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(440, now);
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.04);
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.04);
        osc.start(now);
        osc.stop(now + 0.04);
      } else if (type === "select") {
        osc.type = "triangle";
        osc.frequency.setValueAtTime(587.33, now); // D5
        osc.frequency.exponentialRampToValueAtTime(880, now + 0.06); // A5
        gain.gain.setValueAtTime(0.05, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
        osc.start(now);
        osc.stop(now + 0.06);
      } else if (type === "preset") {
        osc.type = "sine";
        osc.frequency.setValueAtTime(261.63, now); // C4
        osc.frequency.exponentialRampToValueAtTime(523.25, now + 0.08); // C5
        gain.gain.setValueAtTime(0.04, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
      }
    } catch (e) {
      // Silent fallback
    }
  }

  /* ----------------------------------------------------------------- Init */
  function init() {
    loadCatalogAndState().then(function () {
      renderApp();
      setupGlobalListeners();
    }).catch(function (err) {
      console.error("Failed to load catalog:", err);
      builderRoot.innerHTML = '<div class="highlight-box"><p>Unable to load gear catalog. Please refresh the page.</p></div>';
    });
  }

  function loadCatalogAndState() {
    return fetch("assets/dj-gear-catalog.json")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        CATALOG = data;
        parseUrlOrLocalState();
      });
  }

  function parseUrlOrLocalState() {
    var params = new URLSearchParams(window.location.search);

    // 1. Deep link to add a specific gear item (e.g. ?add=pioneer-ddj-flx10)
    var addParam = params.get("add");
    if (addParam) {
      var targetItem = getItem(addParam);
      if (targetItem) {
        var existingSlot = currentRig.items.find(function (s) { return s.category === targetItem.category; });
        if (existingSlot) {
          existingSlot.itemId = targetItem.id;
          existingSlot.owned = false;
        } else {
          currentRig.items.push({
            slotId: "extra-" + Date.now(),
            category: targetItem.category,
            itemId: targetItem.id,
            qty: 1,
            owned: false
          });
        }
        currentRig.name = "Custom Setup with " + targetItem.brand + " " + targetItem.model;
        saveActiveState();
        return;
      }
    }

    // 2. Preset query param (e.g. ?preset=club-ready)
    var presetParam = params.get("preset");
    if (presetParam && CATALOG.presets) {
      var pMatch = CATALOG.presets.find(function (p) { return p.id === presetParam; });
      if (pMatch) {
        loadPresetData(pMatch);
        return;
      }
    }

    // 3. Base64 encoded rig state param (e.g. ?rig=...)
    var rigParam = params.get("rig");
    if (rigParam && rigParam.length <= 8192) {
      try {
        if (normalizeRigState(JSON.parse(decodeURIComponent(atob(rigParam))))) return;
      } catch (e) {
        console.warn("Invalid rig URL param:", e);
      }
    }

    // 4. Local state is optional and untrusted, just like shared URLs.
    var local = safeStorageGet("offbeat.rig.active");
    if (local && local.length <= 16384) {
      try { normalizeRigState(JSON.parse(local)); }
      catch (e) { console.warn("Invalid local rig state:", e); }
    }
  }

  // Shared URLs and saved rigs are untrusted. Never render raw slot identifiers.
  function sanitizeRigState(data) {
    if (!data || typeof data !== "object" || Array.isArray(data)) return null;
    var raw;
    if (Array.isArray(data.items)) {
      raw = data.items;
    } else if (data.slots && typeof data.slots === "object" && !Array.isArray(data.slots)) {
      var cats = Object.keys(data.slots);
      if (cats.length > 24) return null;
      raw = cats.map(function (cat) {
        return { slotId: "core-" + cat, category: cat, itemId: data.slots[cat],
          qty: 1, owned: Boolean(data.owned && data.owned[cat]) };
      });
    } else return null;
    if (!raw.length || raw.length > 24) return null;

    var used = Object.create(null), items = [];
    raw.forEach(function (slot, index) {
      if (!slot || typeof slot !== "object" || Array.isArray(slot)) return;
      if (typeof slot.itemId !== "string" || typeof slot.category !== "string") return;
      var item = getItem(slot.itemId);
      if (!item || item.category !== slot.category) return;
      var id = typeof slot.slotId === "string" && /^[A-Za-z0-9_-]{1,64}$/.test(slot.slotId)
        ? slot.slotId : "imported-" + index;
      var suffix = 0;
      while (used[id]) id = "imported-" + index + "-" + (++suffix);
      used[id] = true;
      items.push({
        slotId: id, category: item.category, itemId: item.id,
        qty: Number.isInteger(slot.qty) && slot.qty >= 1 && slot.qty <= 4 ? slot.qty : 1,
        owned: slot.owned === true
      });
    });
    if (!items.length) return null;
    return {
      name: typeof data.name === "string" ? data.name.slice(0, 80) : "My Custom DJ Rig",
      items: items
    };
  }

  function normalizeRigState(data) {
    var clean = sanitizeRigState(data);
    if (!clean) return false;
    currentRig = clean;
    return true;
  }

  function saveActiveState() {
    var serialized = JSON.stringify(currentRig);
    safeStorageSet("offbeat.rig.active", serialized);
    try {
      var encoded = btoa(encodeURIComponent(serialized));
      if (encoded.length > 8192) return;
      window.history.replaceState({ rig: currentRig }, "", window.location.pathname + "?rig=" + encodeURIComponent(encoded));
    } catch (e) {
      console.warn("Could not update rig share URL:", e);
    }
  }

  function getItem(id) {
    if (!CATALOG || !id) return null;
    return CATALOG.items.find(function (item) { return item.id === id; }) || null;
  }

  function getSlotItem(slot) {
    return getItem(slot.itemId);
  }

  // Owning the old product does not mean owning its replacement.
  function replaceSlotItem(slot, itemId) {
    var item = getItem(itemId);
    if (!slot || !item) return false;
    if (slot.itemId !== item.id) slot.owned = false;
    slot.itemId = item.id;
    slot.category = item.category;
    return true;
  }

  /* ----------------------------------------------------------- Calculations */
  function calculateRigStats() {
    var totalValue = 0;
    var ownedValue = 0;
    var purchaseCost = 0;
    var itemCount = 0;
    var ownedCount = 0;

    currentRig.items.forEach(function (slot) {
      var item = getSlotItem(slot);
      if (item) {
        var qty = slot.qty || 1;
        var lineTotal = item.price * qty;
        totalValue += lineTotal;
        itemCount += qty;
        if (slot.owned) {
          ownedValue += lineTotal;
          ownedCount += qty;
        } else {
          purchaseCost += lineTotal;
        }
      }
    });

    var compatibility = runDeepCompatibilityChecks();
    var nextUpgrade = recommendNextUpgrade();

    return {
      totalValue: totalValue,
      ownedValue: ownedValue,
      purchaseCost: purchaseCost,
      itemCount: itemCount,
      ownedCount: ownedCount,
      compatibility: compatibility,
      nextUpgrade: nextUpgrade
    };
  }

  /* ------------------------------------------- Real DJ Compatibility Engine */
  function runDeepCompatibilityChecks() {
    var controllerSlot = currentRig.items.find(function (s) { return s.category === "controllers"; });
    var headphonesSlot = currentRig.items.find(function (s) { return s.category === "headphones"; });
    var speakersSlot = currentRig.items.find(function (s) { return s.category === "speakers"; });
    var laptopSlot = currentRig.items.find(function (s) { return s.category === "laptops"; });
    var cableSlots = currentRig.items.filter(function (s) { return s.category === "cables"; });

    var controller = controllerSlot ? getSlotItem(controllerSlot) : null;
    var headphones = headphonesSlot ? getSlotItem(headphonesSlot) : null;
    var speakers = speakersSlot ? getSlotItem(speakersSlot) : null;
    var laptop = laptopSlot ? getSlotItem(laptopSlot) : null;

    var checks = [];
    var fatalErrors = 0;
    var warnings = 0;

    // 1. Audio Signal Cable Matching (3-Way Verification)
    if (controller && speakers) {
      var ctrlOutputs = controller.master_outputs || [];
      var spkInputs = speakers.inputs || [];

      var hasRCAOut = ctrlOutputs.some(function (o) { return o.indexOf("RCA") !== -1; });
      var hasXLROut = ctrlOutputs.some(function (o) { return o.indexOf("XLR") !== -1; });
      var hasTRSOut = ctrlOutputs.some(function (o) { return o.indexOf("TRS") !== -1 || o.indexOf("1/4\"") !== -1; });

      var hasRCAIn = spkInputs.some(function (i) { return i.indexOf("RCA") !== -1; });
      var hasXLRIn = spkInputs.some(function (i) { return i.indexOf("XLR") !== -1; });
      var hasTRSIn = spkInputs.some(function (i) { return i.indexOf("TRS") !== -1 || i.indexOf("1/4\"") !== -1; });

      // Only suggest cables whose physical endpoints match listed connectors.
      // The catalog does not contain every real-world cable type.
      var options = [];
      if (hasXLROut && hasXLRIn) options.push({ id: "cable-xlr-xlr", name: "Balanced XLR Cable Pair" });
      if (hasRCAOut && hasRCAIn) options.push({ id: "cable-rca-rca", name: "Dual RCA to Dual RCA Cable" });
      if (hasRCAOut && hasTRSIn) options.push({ id: "cable-rca-trs", name: "Dual RCA to Dual 1/4\" TS Cable" });
      var selected = options.find(function (c) {
        return cableSlots.some(function (slot) { return slot.itemId === c.id; });
      });
      if (selected) {
        checks.push({
          type: "success", statusLevel: "workable",
          title: "Listed Audio Connection Match",
          desc: "Listed connectors support " + selected.name + " between " + controller.model +
            " and " + speakers.model + ". Verify wiring, levels, and manufacturer requirements.",
          fixCableId: null
        });
      } else if (options.length) {
        var suggestion = options[0];
        checks.push({
          type: "warning", statusLevel: "workable",
          title: "Audio Cable Needed",
          desc: "The catalog lists " + suggestion.name + " as a possible connection between " +
            controller.model + " and " + speakers.model +
            ". Confirm exact wiring and levels before purchasing.",
          fixCableId: suggestion.id, fixActionText: "Select " + suggestion.name
        });
        warnings++;
      } else {
        var miniOut = ctrlOutputs.some(function (o) { return o.indexOf("3.5mm") !== -1; });
        var miniIn = spkInputs.some(function (i) { return i.indexOf("3.5mm") !== -1; });
        var advice = miniOut && miniIn
          ? "A compatible 3.5mm stereo cable may work, but none is in this planner's catalog."
          : hasTRSOut && hasTRSIn
            ? "A matching TRS cable pair may work, but none is in this planner's catalog."
            : "No suitable cable is listed in this planner's catalog for these connectors.";
        checks.push({
          type: "warning", statusLevel: "workable",
          title: "Connection Requires Separate Verification",
          desc: advice + " Check the manufacturers' output and input specifications before buying.",
          fixCableId: null
        });
        warnings++;
      }
    } else if (controller && !speakers) {
      checks.push({
        type: "info",
        statusLevel: "workable",
        title: "Headphones-Only Practice Rig",
        desc: "You can practice transitions in headphones without speakers. Add studio monitors (like Pioneer DM-40D) when you want to hear room acoustics.",
        fixCableId: null
      });
    }

    // 2. Standalone vs Laptop Host Check
    if (controller && laptop) {
      if (laptop.id === "standalone-usb-only" && !controller.standalone) {
        checks.push({
          type: "error",
          statusLevel: "incompatible",
          title: "Host Computer Required for DJing",
          desc: controller.brand + " " + controller.model + " is a MIDI controller without an internal computer. It cannot play music from USB sticks without a laptop running DJ software.",
          fixActionText: "Switch to MacBook Air Laptop",
          fixSlotId: laptopSlot ? laptopSlot.slotId : null,
          fixItemId: "macbook-air-m2"
        });
        fatalErrors++;
      } else if (controller.standalone) {
        checks.push({
          type: "success",
          statusLevel: "verified",
          title: "Standalone Capability Listed",
          desc: controller.brand + " " + controller.model + " is listed as standalone-capable. Confirm supported media, firmware, and streaming services for your intended use.",
          fixCableId: null
        });
      } else {
        checks.push({
          type: "success",
          statusLevel: "verified",
          title: "Host Driver Compatibility Needs Verification",
          desc: controller.model + " is listed for USB use with " + laptop.model + ". Confirm current OS, DJ software licensing, and manufacturer driver requirements.",
          fixCableId: null
        });
      }
    } else if (controller && !laptop && !controller.standalone) {
      // A laptop-dependent controller without any host cannot play a set.
      // Do not present a green "preliminary match" to someone buying this rig.
      checks.push({
        type: "error",
        statusLevel: "incompatible",
        title: "Host Computer Required",
        desc: controller.brand + " " + controller.model +
          " is not listed as standalone. Add a compatible computer and DJ software " +
          "before treating this as a playable setup; verify current OS and driver support.",
        fixCableId: null
      });
      fatalErrors++;
    }

    // 3. Headphone Cue Jack Check
    if (controller && headphones) {
      var ctrlJack = controller.headphone_jack || "";
      var hpJack = headphones.jack_type || "";
      var hasAdapter = cableSlots.some(function (cs) { return cs.itemId === "adapter-headphone-jack"; });

      if (ctrlJack.indexOf("3.5mm") !== -1 && hpJack.indexOf("1/4\"") !== -1 && !hasAdapter) {
        checks.push({
          type: "info",
          statusLevel: "workable",
          title: "Headphone Jack Adapter Advisory",
          desc: "Your controller uses a 3.5mm mini-jack. Make sure your headphones include a 3.5mm plug or add a gold 3.5mm-to-1/4\" adapter to your checklist.",
          fixCableId: "adapter-headphone-jack",
          fixActionText: "Add 1/4\" to 3.5mm Adapter ($8)"
        });
      }
    }

    // Calculate Dynamic Readiness Score
    var readiness = 100;
    if (!controller) readiness -= 35;
    if (!headphones) readiness -= 25;
    if (!speakers) readiness -= 15;
    if (!laptop && (!controller || !controller.standalone)) readiness -= 15;
    if (fatalErrors > 0) readiness = Math.min(readiness, 40);
    else if (warnings > 0) readiness = Math.max(readiness - warnings * 10, 60);

    return {
      readiness: Math.max(readiness, 10),
      checks: checks,
      fatalErrors: fatalErrors,
      warnings: warnings
    };
  }

  /* ------------------------------------------- Smart Upgrade Path Advisor */
  function recommendNextUpgrade() {
    var controllerSlot = currentRig.items.find(function (s) { return s.category === "controllers"; });
    var headphonesSlot = currentRig.items.find(function (s) { return s.category === "headphones"; });
    var speakersSlot = currentRig.items.find(function (s) { return s.category === "speakers"; });
    var standSlot = currentRig.items.find(function (s) { return s.category === "stands"; });

    var controller = controllerSlot ? getSlotItem(controllerSlot) : null;
    var headphones = headphonesSlot ? getSlotItem(headphonesSlot) : null;
    var speakers = speakersSlot ? getSlotItem(speakersSlot) : null;

    if (headphones && headphones.price < 100 && controller && controller.price >= 299) {
      return {
        role: "Headphones Upgrade",
        targetName: "Sennheiser HD 25 ($149)",
        desc: "Upgrading from entry headphones to industry-standard HD 25s provides maximum club booth acoustic isolation and rotating one-ear monitoring.",
        targetId: "sennheiser-hd25",
        targetSlotId: headphonesSlot.slotId
      };
    }

    if (controller && controller.channels === 4 && speakers && speakers.price < 200) {
      return {
        role: "Studio Monitor Upgrade",
        targetName: "Yamaha HS5 ($398 Pair)",
        desc: "Your 4-channel controller has balanced outputs. Upgrading to bi-amped 5-inch Yamaha monitors delivers transparent frequency response for advanced mixing.",
        targetId: "yamaha-hs5",
        targetSlotId: speakersSlot.slotId
      };
    }

    if (!standSlot && controller && !controller.standalone) {
      return {
        role: "Ergonomic Upgrade",
        targetName: "Pyle Pro Laptop Stand ($29)",
        desc: "Elevating your laptop directly above your controller platters saves table footprint and prevents neck strain during long practice sets.",
        targetId: "laptop-stand-pyle",
        targetSlotId: "core-stand"
      };
    }

    return {
      role: "Club Readiness",
      targetName: "SanDisk Extreme PRO USB 3.2 ($28)",
      desc: "Fast solid-state flash memory ensures instant waveform loading and zero lag when exporting rekordbox playlists to club CDJ-3000s.",
      targetId: "usb-sandisk-extreme",
      targetSlotId: "core-storage"
    };
  }

  /* ---------------------------------------------------------------- Render */
  function renderApp() {
    var stats = calculateRigStats();

    var html = `
      <!-- Builder Top Dashboard -->
      <section class="rig-dashboard-shell">
        <div class="rig-dash-header">
          <div class="rig-title-block">
            <span class="hero-eyebrow">Interactive DJ Rig Architect</span>
            <h2 class="rig-main-title" contenteditable="true" data-rig-name title="Click to rename your setup">${escapeHtml(currentRig.name)}</h2>
            <p class="rig-subtitle">Assemble modular equipment, toggle gear you already own, verify audio signal connections, and generate an itemized shopping list.</p>
          </div>
          <div class="rig-dash-actions">
            <!-- Sound FX Toggle -->
            <button type="button" class="btn-sfx-toggle ${soundEnabled ? 'is-on' : 'is-muted'}" data-action="toggle-sound" title="Toggle audio feedback sounds">
              ${soundEnabled ? '🔊 Audio FX: ON' : '🔇 Audio FX: OFF'}
            </button>

            <!-- Export / Share Actions -->
            <button type="button" class="btn btn-secondary btn-sm" data-action="open-export-modal">📤 Share &amp; Export</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="copy-checklist">📋 Checklist</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="save-rig">💾 Save</button>
            <button type="button" class="btn btn-secondary btn-sm" data-action="open-compare">⚖️ Compare</button>
            <button type="button" class="btn btn-sm" data-action="random-rig">🎲 Preset</button>
          </div>
        </div>

        <!-- Presets Bar -->
        <div class="rig-preset-strip" role="group" aria-label="Preset starting points">
          <span class="preset-label">Quick Start Rigs:</span>
          ${CATALOG.presets.map(function (p) {
            return `<button type="button" class="rig-preset-pill" data-preset-id="${p.id}">
              <strong>${escapeHtml(p.name)}</strong> <span class="preset-badge">${escapeHtml(p.badge)}</span>
            </button>`;
          }).join("")}
        </div>

        <!-- Metric Cards -->
        <div class="rig-metrics-grid">
          <div class="rig-metric-card">
            <span class="metric-label">Total Rig Valuation</span>
            <strong class="metric-val">$${stats.totalValue.toLocaleString()}</strong>
            <span class="metric-sub">${stats.itemCount} items in setup</span>
          </div>
          <div class="rig-metric-card metric-card--owned">
            <span class="metric-label">Gear You Own (Saved)</span>
            <strong class="metric-val metric-val--owned">-$${stats.ownedValue.toLocaleString()}</strong>
            <span class="metric-sub">${stats.ownedCount} owned items deducted</span>
          </div>
          <div class="rig-metric-card metric-card--spend">
            <span class="metric-label">Actual Spend Needed</span>
            <strong class="metric-val metric-val--spend">$${stats.purchaseCost.toLocaleString()}</strong>
            <span class="metric-sub">${stats.itemCount - stats.ownedCount} items to purchase</span>
          </div>
          <div class="rig-metric-card metric-card--readiness">
            <span class="metric-label">Setup Readiness</span>
            <div class="readiness-gauge-wrap">
              <div class="readiness-bar"><div class="readiness-fill" style="width: ${stats.compatibility.readiness}%"></div></div>
              <strong class="readiness-num">${stats.compatibility.readiness}%</strong>
            </div>
            <span class="metric-sub">${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? "No listed issues found" : stats.compatibility.fatalErrors > 0 ? "❌ Incompatibility detected" : "⚠️ " + stats.compatibility.warnings + " cable optimization"}</span>
          </div>
        </div>

        <!-- Upgrade Path Advisory Card -->
        ${stats.nextUpgrade ? `
          <div class="upgrade-advisory-card">
            <div class="upgrade-tag">💡 Smart Upgrade Path Advisor</div>
            <div class="upgrade-body">
              <strong>${escapeHtml(stats.nextUpgrade.role)}: ${escapeHtml(stats.nextUpgrade.targetName)}</strong>
              <p>${escapeHtml(stats.nextUpgrade.desc)}</p>
            </div>
            <button type="button" class="btn btn-secondary btn-sm btn-upgrade-swap" data-action="auto-fix-slot" data-slot-id="${stats.nextUpgrade.targetSlotId}" data-item-id="${stats.nextUpgrade.targetId}">
              Try in this rig →
            </button>
          </div>
        ` : ''}
      </section>

      <!-- Visual DJ Booth Studio Layout -->
      <section class="rig-booth-section">
        <div class="section-head">
          <h3>DJ Studio Booth &amp; Signal Routing</h3>
          <p>Interactive 2D booth layout. Click any piece of gear to swap components, adjust quantities, or toggle owned gear.</p>
        </div>
        <div class="rig-booth-stage">
          <!-- Top Row: Monitors, Host Platform, Stands/Media -->
          <div class="booth-top-row">
            ${renderBoothSlot(findSlot("speakers") || { slotId: "core-spk", category: "speakers", itemId: null }, "Monitors / Speakers", "🔊")}
            ${renderBoothSlot(findSlot("laptops") || { slotId: "core-host", category: "laptops", itemId: null }, "Host Platform / OS", "💻")}
            ${renderBoothSlot(findSlot("stands") || findSlot("storage") || findSlot("microphones") || { slotId: "core-stand", category: "stands", itemId: null }, "Stands, Mics & Media", "🏗️")}
          </div>

          <!-- Signal Cables Hub Indicator -->
          <div class="booth-cables-row">
            <div class="cable-pulse-line cable-pulse--left"></div>
            <div class="cable-node-hub" data-action="pick" data-slot-id="${(findSlot('cables') || {}).slotId || 'core-cable'}" data-category="cables">
              <span class="cable-icon">🔌</span>
              <span class="cable-title">${getCableSummaryText()}</span>
              <span class="cable-change">Change Cables →</span>
            </div>
            <div class="cable-pulse-line cable-pulse--right"></div>
          </div>

          <!-- Bottom Row: Controller & Headphones -->
          <div class="booth-bottom-row">
            ${renderBoothSlot(findSlot("controllers") || { slotId: "core-ctrl", category: "controllers", itemId: null }, "DJ Controller / Decks & Mixer", "🎛️", true)}
            ${renderBoothSlot(findSlot("headphones") || { slotId: "core-hp", category: "headphones", itemId: null }, "DJ Headphones", "🎧")}
          </div>
        </div>
      </section>

      <!-- Compatibility Engine Alerts -->
      <section class="rig-compat-section">
        <div class="compat-box">
          <div class="compat-header">
            <h4>⚡ Hardware &amp; Signal Compatibility Assistant</h4>
            <span class="compat-status-tag ${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? 'tag--ok' : stats.compatibility.fatalErrors > 0 ? 'tag--err' : 'tag--warn'}">
              ${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? 'Preliminary Match' : stats.compatibility.fatalErrors > 0 ? '❌ Incompatible Configuration' : '⚠️ Cable Optimization Needed'}
            </span>
          </div>
          <div class="compat-items-grid">
            ${stats.compatibility.checks.map(function (c) {
              return `<div class="compat-item compat-item--${c.type}">
                <div class="compat-icon">${c.type === 'success' ? '✓' : c.type === 'error' ? '❌' : c.type === 'warning' ? '⚠️' : 'ℹ️'}</div>
                <div class="compat-body">
                  <div class="compat-title-row">
                    <strong>${escapeHtml(c.title)}</strong>
                    <span class="compat-level-badge level--${c.statusLevel}">${c.statusLevel === 'verified' ? 'Listed Match' : c.statusLevel === 'incompatible' ? 'Hardware Block' : 'Workable with Note'}</span>
                  </div>
                  <p>${escapeHtml(c.desc)}</p>
                  ${c.fixCableId ? `<button type="button" class="btn-text-action" data-action="auto-fix-cable" data-cable-id="${c.fixCableId}">${escapeHtml(c.fixActionText || 'Auto-select recommended cable →')}</button>` : ''}
                  ${c.fixSlotId && c.fixItemId ? `<button type="button" class="btn-text-action" data-action="auto-fix-slot" data-slot-id="${c.fixSlotId}" data-item-id="${c.fixItemId}">${escapeHtml(c.fixActionText)}</button>` : ''}
                </div>
              </div>`;
            }).join("")}
          </div>
        </div>
      </section>

      <!-- Itemized PCPartPicker Table -->
      <section class="rig-table-section">
        <div class="section-head-split">
          <div>
            <h3>Component Breakdown &amp; Shopping List</h3>
            <p>Every piece in your setup with dated 2026 price estimates, quantities, and direct retailer links.</p>
          </div>
          <div class="add-slot-dropdown-wrap">
            <button type="button" class="btn btn-secondary btn-sm" data-action="open-add-slot">+ Add Equipment Slot ▾</button>
            <div class="add-slot-menu" id="add-slot-menu" hidden>
              <button type="button" data-action="add-new-slot" data-category="microphones">🎤 Add Vocal / Host Microphone</button>
              <button type="button" data-action="add-new-slot" data-category="stands">🏗️ Add DJ Laptop Stand / Riser</button>
              <button type="button" data-action="add-new-slot" data-category="storage">💾 Add USB Media / Flash Drive</button>
              <button type="button" data-action="add-new-slot" data-category="speakers">🔊 Add Extra Monitor / PA Speaker</button>
              <button type="button" data-action="add-new-slot" data-category="cables">🔌 Add Audio Cable / Adapter</button>
              <button type="button" data-action="add-new-slot" data-category="controllers">🎛️ Add Second Controller / Deck</button>
            </div>
          </div>
        </div>

        <div class="table-wrap">
          <table class="drill-table rig-spec-table">
            <thead>
              <tr>
                <th scope="col">Slot &amp; Role</th>
                <th scope="col">Selected Equipment</th>
                <th scope="col">Qty</th>
                <th scope="col">Ownership</th>
                <th scope="col">Price Est.</th>
                <th scope="col">Retailer Actions</th>
              </tr>
            </thead>
            <tbody>
              ${currentRig.items.map(function (slot) {
                return renderModularTableRow(slot);
              }).join("")}
            </tbody>
            <tfoot>
              <tr class="rig-total-row">
                <td colspan="4"><strong>Total Out-of-Pocket Purchase Spend:</strong></td>
                <td colspan="2"><strong class="spend-total-num">$${stats.purchaseCost.toLocaleString()}</strong></td>
              </tr>
            </tfoot>
          </table>
        </div>

        <!-- Commercial Disclosure Notice -->
        <p class="table-note">
          ${CATALOG.meta.disclosure} <a href="disclosure.html">Read our full affiliate disclosure</a>.
        </p>
      </section>

      <!-- Saved Rigs & Comparison Section -->
      <section class="rig-saved-section" id="saved-rigs-drawer">
        ${renderSavedRigsList()}
      </section>

      <!-- Modal Container (Dynamically populated) -->
      <div id="rig-modal-container" hidden></div>
    `;

    builderRoot.innerHTML = html;
  }

  function findSlot(category) {
    return currentRig.items.find(function (s) { return s.category === category; }) || null;
  }

  function renderBoothSlot(slot, label, icon, isMain) {
    var item = getSlotItem(slot);
    var isOwned = Boolean(slot.owned);

    if (!item) {
      return `
        <div class="booth-card booth-card--empty ${isMain ? 'booth-card--main' : ''}" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}">
          <span class="booth-card-role">${icon} ${escapeHtml(label)}</span>
          <div class="booth-empty-content">
            <span class="booth-plus">+</span>
            <strong>Select ${escapeHtml(label)}</strong>
          </div>
        </div>
      `;
    }

    var qtyStr = slot.qty > 1 ? ` <span class="booth-qty-badge">x${slot.qty}</span>` : '';

    return `
      <div class="booth-card ${isMain ? 'booth-card--main' : ''} ${isOwned ? 'booth-card--owned' : ''}">
        <div class="booth-card-top">
          <span class="booth-card-role">${icon} ${escapeHtml(label)}${qtyStr}</span>
          <button type="button" class="booth-owned-toggle ${isOwned ? 'is-active' : ''}" data-action="toggle-slot-owned" data-slot-id="${slot.slotId}" title="Toggle already owned">
            ${isOwned ? '✓ Owned' : '🛒 Need'}
          </button>
        </div>
        <div class="booth-card-body" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}">
          <div class="booth-thumb-wrap">
            <img src="${item.image}" alt="${escapeHtml(item.brand + ' ' + item.model)}" loading="lazy" class="booth-thumb">
          </div>
          <div class="booth-info">
            <span class="booth-brand">${escapeHtml(item.brand)}</span>
            <strong class="booth-model">${escapeHtml(item.model)}</strong>
            <span class="booth-price ${isOwned ? 'price--owned' : ''}">
              ${isOwned ? '<s>$' + (item.price * (slot.qty || 1)) + '</s> (Owned)' : '$' + (item.price * (slot.qty || 1))}
            </span>
          </div>
        </div>
        <div class="booth-card-footer">
          <button type="button" class="booth-swap-btn" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}">
            Swap Gear →
          </button>
          <button type="button" class="booth-spec-btn" data-action="inspect-item" data-item-id="${item.id}" title="View detailed hardware specs">
            Specs ℹ️
          </button>
        </div>
      </div>
    `;
  }

  function renderModularTableRow(slot) {
    var item = getSlotItem(slot);
    var isOwned = Boolean(slot.owned);
    var catMeta = CATALOG.categories.find(function (c) { return c.id === slot.category; });
    var qty = slot.qty || 1;

    if (!item) {
      return `
        <tr class="rig-row rig-row--empty">
          <td><span class="cat-pill">${catMeta ? catMeta.icon : ''} ${catMeta ? catMeta.name : slot.category}</span></td>
          <td colspan="4"><span class="empty-slot-msg">No item selected</span></td>
          <td><button type="button" class="btn btn-sm" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}">Select Component</button></td>
        </tr>
      `;
    }

    var linePrice = item.price * qty;
    var amazonUrl = "https://www.amazon.com/s?k=" + encodeURIComponent(item.amazon_search || (item.brand + " " + item.model)) + "&tag=offbeatdj-20";
    var sweetwaterUrl = "https://www.sweetwater.com/store/search?s=" + encodeURIComponent(item.brand + " " + item.model);
    var reverbUrl = "https://reverb.com/marketplace?query=" + encodeURIComponent(item.brand + " " + item.model);

    return `
      <tr class="rig-row ${isOwned ? 'rig-row--owned' : ''}">
        <td class="cell-cat">
          <span class="cat-pill">${catMeta ? catMeta.icon : ''} ${catMeta ? catMeta.name : slot.category}</span>
        </td>
        <td class="cell-item">
          <div class="item-summary-box">
            <img src="${item.image}" alt="${escapeHtml(item.model)}" class="table-thumb" loading="lazy">
            <div class="item-summary-copy">
              <div class="item-title-row">
                <strong class="item-full-name">${escapeHtml(item.brand)} ${escapeHtml(item.model)}</strong>
                <button type="button" class="btn-item-info" data-action="inspect-item" data-item-id="${item.id}">Specs</button>
              </div>
              <p class="item-tagline">${escapeHtml(item.tagline || item.ideal_for || '')}</p>
              ${item.slug ? `<a href="${item.slug}" class="item-guide-link">Read Offbeat Guide →</a>` : ''}
            </div>
          </div>
        </td>
        <td class="cell-qty">
          <div class="qty-stepper-wrap">
            <button type="button" class="qty-step-btn" data-action="step-qty" data-slot-id="${slot.slotId}" data-step="-1" aria-label="Decrease quantity" ${qty <= 1 ? 'disabled' : ''}>-</button>
            <span class="qty-display">${qty}</span>
            <button type="button" class="qty-step-btn" data-action="step-qty" data-slot-id="${slot.slotId}" data-step="1" aria-label="Increase quantity" ${qty >= 4 ? 'disabled' : ''}>+</button>
          </div>
        </td>
        <td class="cell-status">
          <button type="button" class="status-btn ${isOwned ? 'status-btn--owned' : 'status-btn--needed'}" data-action="toggle-slot-owned" data-slot-id="${slot.slotId}">
            ${isOwned ? '🟢 I Own This' : '🔵 Need to Buy'}
          </button>
        </td>
        <td class="cell-price">
          <span class="price-figure ${isOwned ? 'price--owned' : ''}">
            ${isOwned ? '<s>$' + linePrice + '</s>' : '$' + linePrice}
          </span>
          ${isOwned ? '<span class="owned-sub">($0 out of pocket)</span>' : (qty > 1 ? '<span class="unit-sub">($' + item.price + ' ea)</span>' : '')}
        </td>
        <td class="cell-actions">
          <div class="retail-btn-stack">
            <button type="button" class="btn-swap-inline" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}">Swap</button>
            <a href="${sweetwaterUrl}" target="_blank" rel="nofollow noopener sponsored" class="btn-retail btn-retail--sw" title="Search Sweetwater">Sweetwater ↗</a>
            <a href="${amazonUrl}" target="_blank" rel="nofollow noopener sponsored" class="btn-retail btn-retail--amz" title="Search model on Amazon">Amazon ↗</a>
            <a href="${reverbUrl}" target="_blank" rel="nofollow noopener" class="btn-retail btn-retail--rev" title="Find used offers on Reverb">Reverb ↗</a>
            <button type="button" class="btn-del-slot" data-action="remove-slot" data-slot-id="${slot.slotId}" title="Remove this component">✕</button>
          </div>
        </td>
      </tr>
    `;
  }

  function getCableSummaryText() {
    var cables = currentRig.items.filter(function (s) { return s.category === "cables"; });
    if (cables.length === 0) return "No Audio Cables Selected";
    return cables.map(function (c) {
      var item = getSlotItem(c);
      return item ? item.model : "Audio Cable";
    }).join(" + ");
  }

  function renderSavedRigsList() {
    var saved = getSavedRigs();
    if (!saved || saved.length === 0) return '';

    return `
      <div class="saved-rigs-card">
        <div class="saved-rigs-head">
          <h4>💾 My Saved Custom Rigs (${saved.length})</h4>
          <button type="button" class="btn btn-secondary btn-sm" data-action="open-compare">⚖️ Compare Builds Side-by-Side</button>
        </div>
        <div class="saved-pills-list">
          ${saved.map(function (r, index) {
            return `
              <div class="saved-rig-pill">
                <button type="button" class="btn-load-rig" data-action="load-saved-rig" data-index="${index}">
                  <strong>${escapeHtml(r.name)}</strong>
                  <span>$${r.totalCost || 0} (${escapeHtml(r.date || 'Saved')})</span>
                </button>
                <button type="button" class="btn-del-rig" data-action="delete-saved-rig" data-index="${index}" title="Delete rig">✕</button>
              </div>
            `;
          }).join("")}
        </div>
      </div>
    `;
  }

  /* ------------------------------------------------------------- Modal */
  function openPickerModal(slotId, category) {
    activeModalSlotId = slotId;
    activeModalCategory = category;
    var catMeta = CATALOG.categories.find(function (c) { return c.id === category; });
    var items = CATALOG.items.filter(function (i) { return i.category === category; });

    var activeSlot = currentRig.items.find(function (s) { return s.slotId === slotId; });
    var currentItemId = activeSlot ? activeSlot.itemId : null;

    var modalHtml = `
      <div class="picker-backdrop" data-action="close-modal">
        <div class="picker-dialog" role="dialog" aria-modal="true" aria-labelledby="picker-modal-title">
          <div class="picker-header">
            <div>
              <span class="picker-eyebrow">${catMeta ? catMeta.icon : ''} Component Selector</span>
              <h3 id="picker-modal-title">Select ${catMeta ? catMeta.name : 'Component'}</h3>
            </div>
            <button type="button" class="picker-close" data-action="close-modal" aria-label="Close dialog">✕</button>
          </div>

          <div class="picker-search-bar">
            <input type="search" placeholder="Filter by brand, model, feature (e.g. FLX4, Prime 4, balanced XLR, Pioneer, Traktor)..." data-modal-search autocomplete="off">
          </div>

          <div class="picker-grid" id="modal-items-grid">
            ${renderModalGridItems(items, currentItemId)}
          </div>
        </div>
      </div>
    `;

    var container = document.getElementById("rig-modal-container");
    container.innerHTML = modalHtml;
    container.hidden = false;
    document.body.classList.add("modal-open");

    var searchInput = container.querySelector("[data-modal-search]");
    if (searchInput) {
      searchInput.focus();
      searchInput.addEventListener("input", function (e) {
        var query = e.target.value.toLowerCase().trim();
        var tokens = query ? query.split(/\s+/) : [];
        var filtered = items.filter(function (i) {
          if (tokens.length === 0) return true;
          var text = (i.brand + " " + i.model + " " + (i.tagline || "") + " " + (i.ideal_for || "") + " " + (i.software_unlocks ? i.software_unlocks.join(" ") : "")).toLowerCase();
          return tokens.every(function (t) { return text.indexOf(t) !== -1; });
        });
        document.getElementById("modal-items-grid").innerHTML = renderModalGridItems(filtered, currentItemId);
      });
    }
  }

  function renderModalGridItems(items, currentItemId) {
    if (items.length === 0) {
      return '<div class="picker-empty"><p>No components match your search filter.</p></div>';
    }

    return items.map(function (item) {
      var isCurrent = currentItemId === item.id;
      return `
        <article class="picker-card ${isCurrent ? 'is-selected' : ''}" data-action="select-item" data-item-id="${item.id}">
          <div class="picker-card-img-wrap">
            <img src="${item.image}" alt="${escapeHtml(item.model)}" class="picker-card-img" loading="lazy">
            <span class="picker-price-badge">$${item.price}</span>
            <span class="picker-provenance-tag">Vector Schematic</span>
          </div>
          <div class="picker-card-body">
            <span class="picker-card-brand">${escapeHtml(item.brand)}</span>
            <h4 class="picker-card-title">${escapeHtml(item.model)}</h4>
            <p class="picker-card-tagline">${escapeHtml(item.tagline || item.ideal_for || '')}</p>
            <div class="picker-specs-list">
              ${item.channels ? `<span>${item.channels} Channels</span>` : ''}
              ${item.master_outputs ? `<span>Outputs: ${item.master_outputs.join(", ")}</span>` : ''}
              ${item.inputs ? `<span>Inputs: ${item.inputs.join(", ")}</span>` : ''}
              ${item.software_unlocks ? `<span>Unlocks: ${item.software_unlocks.join(", ")}</span>` : ''}
            </div>
          </div>
          <div class="picker-card-footer">
            <button type="button" class="btn ${isCurrent ? 'btn-secondary' : ''} btn-sm btn-select-item" data-action="select-item" data-item-id="${item.id}">
              ${isCurrent ? '✓ In Your Rig' : 'Select for Rig'}
            </button>
            <button type="button" class="picker-inspect-btn" data-action="inspect-item" data-item-id="${item.id}">Specs ℹ️</button>
          </div>
        </article>
      `;
    }).join("");
  }

  function openInspectorModal(itemId) {
    var item = getItem(itemId);
    if (!item) return;

    var modalHtml = `
      <div class="picker-backdrop" data-action="close-modal">
        <div class="picker-dialog picker-dialog--inspector" role="dialog" aria-modal="true" aria-labelledby="inspector-title">
          <div class="picker-header">
            <div>
              <span class="picker-eyebrow">${escapeHtml(item.brand)} Detailed Specifications</span>
              <h3 id="inspector-title">${escapeHtml(item.model)}</h3>
            </div>
            <button type="button" class="picker-close" data-action="close-modal" aria-label="Close dialog">✕</button>
          </div>

          <div class="inspector-content">
            <div class="inspector-visual-col">
              <img src="${item.image}" alt="${escapeHtml(item.model)}" class="inspector-hero-img">
              <p class="inspector-provenance-note">${escapeHtml(item.provenance || 'Offbeat Illustrated Spec Guide (2026)')}</p>
            </div>
            <div class="inspector-info-col">
              <div class="inspector-price-row">
                <span class="inspector-price">$${item.price}</span>
                <span class="inspector-price-sub">Est. US Retail (Late 2026)</span>
              </div>
              <p class="inspector-summary">${escapeHtml(item.tagline || '')}</p>
              
              <div class="inspector-specs-table">
                ${item.channels ? `<div class="insp-row"><span>Audio Channels:</span><strong>${item.channels} Decks</strong></div>` : ''}
                ${item.master_outputs ? `<div class="insp-row"><span>Master Outputs:</span><strong>${item.master_outputs.join(", ")}</strong></div>` : ''}
                ${item.inputs ? `<div class="insp-row"><span>Audio Inputs:</span><strong>${item.inputs.join(", ")}</strong></div>` : ''}
                ${item.headphone_jack ? `<div class="insp-row"><span>Headphone Jack:</span><strong>${item.headphone_jack}</strong></div>` : ''}
                ${item.software_unlocks ? `<div class="insp-row"><span>Software Unlocks:</span><strong>${item.software_unlocks.join(", ")}</strong></div>` : ''}
                ${item.driver_mm ? `<div class="insp-row"><span>Driver Size:</span><strong>${item.driver_mm} mm</strong></div>` : ''}
                ${item.impedance_ohm ? `<div class="insp-row"><span>Impedance:</span><strong>${item.impedance_ohm} Ω</strong></div>` : ''}
                ${item.driver_size ? `<div class="insp-row"><span>Woofer / Driver:</span><strong>${item.driver_size}</strong></div>` : ''}
                <div class="insp-row"><span>Ideal For:</span><strong>${escapeHtml(item.ideal_for || 'DJ Practice')}</strong></div>
              </div>

              ${item.slug ? `<div class="inspector-actions"><a href="${item.slug}" class="btn btn-secondary btn-sm" target="_blank">Read Full In-Depth Review ↗</a></div>` : ''}
            </div>
          </div>
        </div>
      </div>
    `;

    var container = document.getElementById("rig-modal-container");
    container.innerHTML = modalHtml;
    container.hidden = false;
    document.body.classList.add("modal-open");
  }

  function openExportModal() {
    var stats = calculateRigStats();
    var shareUrl = window.location.href;

    var redditMarkdown = `**[${currentRig.name}](${shareUrl})**\n\n` +
      `| Category | Equipment | Price |\n` +
      `| :--- | :--- | :--- |\n` +
      currentRig.items.map(function (s) {
        var it = getSlotItem(s);
        if (!it) return "";
        var status = s.owned ? "*(Already Owned)*" : "";
        return `| **${s.category.toUpperCase()}** | ${it.brand} ${it.model} ${status} | $${it.price * (s.qty || 1)} |`;
      }).filter(Boolean).join("\n") +
      `\n\n* **Total Rig Valuation:** $${stats.totalValue.toLocaleString()}\n` +
      `* **Owned Gear Savings:** -$${stats.ownedValue.toLocaleString()}\n` +
      `* **Actual Out-of-Pocket Spend:** **$${stats.purchaseCost.toLocaleString()}**\n\n` +
      `*Generated with [Offbeat DJ Rig Architect](${shareUrl})*`;

    var modalHtml = `
      <div class="picker-backdrop" data-action="close-modal">
        <div class="picker-dialog picker-dialog--export" role="dialog" aria-modal="true" aria-labelledby="export-modal-title">
          <div class="picker-header">
            <div>
              <span class="picker-eyebrow">Export &amp; Share DJ Setup</span>
              <h3 id="export-modal-title">Share Your Custom Build</h3>
            </div>
            <button type="button" class="picker-close" data-action="close-modal" aria-label="Close dialog">✕</button>
          </div>

          <div class="export-modal-tabs">
            <button type="button" class="export-tab is-active" data-export-tab="reddit">Reddit / Discord Markdown</button>
            <button type="button" class="export-tab" data-export-tab="link">Shareable URL Link</button>
            <button type="button" class="export-tab" data-export-tab="image">Download Summary Card</button>
          </div>

          <div class="export-tab-pane is-active" id="pane-reddit">
            <p class="export-help">Copy this formatted markdown table to post on r/DJs, r/Beatmatch, or Discord asking for setup feedback:</p>
            <textarea class="export-textarea" id="reddit-export-box" readonly>${escapeHtml(redditMarkdown)}</textarea>
            <div class="export-pane-footer">
              <button type="button" class="btn btn-secondary btn-sm" data-action="copy-reddit-md">📋 Copy Reddit Markdown</button>
            </div>
          </div>

          <div class="export-tab-pane" id="pane-link" hidden>
            <p class="export-help">Direct link to load your exact equipment and ownership selections:</p>
            <input type="text" class="export-input-url" id="link-export-box" value="${escapeHtml(shareUrl)}" readonly>
            <div class="export-pane-footer">
              <button type="button" class="btn btn-secondary btn-sm" data-action="copy-share-url">🔗 Copy Link to Clipboard</button>
            </div>
          </div>

          <div class="export-tab-pane" id="pane-image" hidden>
            <p class="export-help">Generate a graphic summary card to save or post to Instagram / Discord:</p>
            <div class="canvas-preview-wrap">
              <canvas id="rig-export-canvas" width="800" height="480" class="rig-card-canvas"></canvas>
            </div>
            <div class="export-pane-footer">
              <button type="button" class="btn btn-sm" data-action="download-canvas-image">🖼️ Download Rig Image (.PNG)</button>
            </div>
          </div>
        </div>
      </div>
    `;

    var container = document.getElementById("rig-modal-container");
    container.innerHTML = modalHtml;
    container.hidden = false;
    document.body.classList.add("modal-open");

    var tabs = container.querySelectorAll(".export-tab");
    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        tabs.forEach(function (t) { t.classList.remove("is-active"); });
        tab.classList.add("is-active");
        var target = tab.getAttribute("data-export-tab");
        container.querySelectorAll(".export-tab-pane").forEach(function (p) { p.hidden = true; });
        var targetPane = container.querySelector("#pane-" + target);
        if (targetPane) targetPane.hidden = false;
        if (target === "image") drawRigCanvas();
      });
    });
  }

  function drawRigCanvas() {
    var canvas = document.getElementById("rig-export-canvas");
    if (!canvas) return;
    var ctx = canvas.getContext("2d");
    var stats = calculateRigStats();

    // Background Gradient
    var bgGrad = ctx.createLinearGradient(0, 0, 800, 480);
    bgGrad.addColorStop(0, "#0c0b14");
    bgGrad.addColorStop(0.6, "#141224");
    bgGrad.addColorStop(1, "#07070c");
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, 800, 480);

    // Accent Border
    ctx.strokeStyle = "rgba(139, 92, 246, 0.4)";
    ctx.lineWidth = 4;
    ctx.strokeRect(12, 12, 776, 456);

    // Header Glow
    ctx.fillStyle = "#a78bfa";
    ctx.font = "bold 14px 'Syne', system-ui, sans-serif";
    ctx.fillText("OFFBEAT. MY DJ RIG ARCHITECT (2026)", 36, 50);

    // Title
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 26px 'Syne', system-ui, sans-serif";
    ctx.fillText(currentRig.name, 36, 88);

    // Price Badges
    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 18px system-ui, sans-serif";
    ctx.fillText("Spend: $" + stats.purchaseCost.toLocaleString(), 36, 122);

    ctx.fillStyle = "#94a3b8";
    ctx.font = "14px system-ui, sans-serif";
    ctx.fillText("(Valuation: $" + stats.totalValue.toLocaleString() + " · Saved: -$" + stats.ownedValue.toLocaleString() + ")", 210, 122);

    // Separator line
    ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(36, 142);
    ctx.lineTo(764, 142);
    ctx.stroke();

    // Gear List Grid
    var yPos = 176;
    currentRig.items.forEach(function (slot, idx) {
      var it = getSlotItem(slot);
      if (!it || idx > 5) return;

      var col = idx < 3 ? 36 : 410;
      var rowY = yPos + (idx % 3) * 80;

      // Role tag
      ctx.fillStyle = "#a78bfa";
      ctx.font = "bold 11px system-ui, sans-serif";
      ctx.fillText(slot.category.toUpperCase(), col, rowY);

      // Model name
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 16px system-ui, sans-serif";
      ctx.fillText(it.brand + " " + it.model, col, rowY + 22);

      // Price & status
      ctx.fillStyle = slot.owned ? "#4ade80" : "#cbd5e1";
      ctx.font = "13px system-ui, sans-serif";
      ctx.fillText((slot.owned ? "✓ Owned ($0 out of pocket)" : "$" + (it.price * (slot.qty || 1))), col, rowY + 42);
    });

    // Watermark Footer
    ctx.fillStyle = "#64748b";
    ctx.font = "12px system-ui, sans-serif";
    ctx.fillText("offbeatinc.com/build-your-dj-setup.html", 36, 442);
  }

  function downloadCanvasImage() {
    var canvas = document.getElementById("rig-export-canvas");
    if (!canvas) return;
    var link = document.createElement("a");
    link.download = currentRig.name.toLowerCase().replace(/[^a-z0-9]/g, "-") + "-rig.png";
    link.href = canvas.toDataURL("image/png");
    link.click();
  }

  function closeModal() {
    var container = document.getElementById("rig-modal-container");
    container.hidden = true;
    container.innerHTML = "";
    document.body.classList.remove("modal-open");
    activeModalSlotId = null;
    activeModalCategory = null;
  }

  /* -------------------------------------------------- Compare Modal */
  function openCompareModal() {
    var saved = getSavedRigs();
    var allRigsToCompare = [];

    allRigsToCompare.push({ name: currentRig.name + " (Current)", items: currentRig.items });

    CATALOG.presets.forEach(function (p) {
      allRigsToCompare.push({ name: p.name + " (" + p.badge + ")", items: convertPresetToItems(p) });
    });

    saved.forEach(function (s) {
      allRigsToCompare.push({ name: s.name, items: s.items || [] });
    });

    var rigA = allRigsToCompare[0];
    var rigB = allRigsToCompare[1] || allRigsToCompare[0];

    var modalHtml = `
      <div class="picker-backdrop" data-action="close-modal">
        <div class="picker-dialog picker-dialog--wide" role="dialog" aria-modal="true" aria-labelledby="compare-modal-title">
          <div class="picker-header">
            <div>
              <span class="picker-eyebrow">Gear Comparison Tool</span>
              <h3 id="compare-modal-title">Compare Two DJ Setups Side-by-Side</h3>
            </div>
            <button type="button" class="picker-close" data-action="close-modal" aria-label="Close dialog">✕</button>
          </div>

          <div class="compare-selectors-bar">
            <div class="compare-col-select">
              <label>Build A:</label>
              <select id="compare-select-a" class="compare-dropdown">
                ${allRigsToCompare.map(function (r, i) {
                  return `<option value="${i}" ${i === 0 ? 'selected' : ''}>${escapeHtml(r.name)}</option>`;
                }).join("")}
              </select>
            </div>
            <span class="compare-vs-badge">VS</span>
            <div class="compare-col-select">
              <label>Build B:</label>
              <select id="compare-select-b" class="compare-dropdown">
                ${allRigsToCompare.map(function (r, i) {
                  return `<option value="${i}" ${i === 1 ? 'selected' : ''}>${escapeHtml(r.name)}</option>`;
                }).join("")}
              </select>
            </div>
          </div>

          <div class="compare-grid" id="compare-content-grid">
            ${renderCompareGridContent(rigA, rigB)}
          </div>
        </div>
      </div>
    `;

    var container = document.getElementById("rig-modal-container");
    container.innerHTML = modalHtml;
    container.hidden = false;
    document.body.classList.add("modal-open");

    var selA = container.querySelector("#compare-select-a");
    var selB = container.querySelector("#compare-select-b");
    if (selA && selB) {
      var updateCompare = function () {
        var rA = allRigsToCompare[parseInt(selA.value, 10)];
        var rB = allRigsToCompare[parseInt(selB.value, 10)];
        document.getElementById("compare-content-grid").innerHTML = renderCompareGridContent(rA, rB);
      };
      selA.addEventListener("change", updateCompare);
      selB.addEventListener("change", updateCompare);
    }
  }

  function convertPresetToItems(preset) {
    var items = [];
    Object.keys(preset.slots).forEach(function (cat) {
      items.push({
        slotId: "p-" + cat,
        category: cat,
        itemId: preset.slots[cat],
        qty: 1,
        owned: false
      });
    });
    return items;
  }

  function renderCompareGridContent(rigA, rigB) {
    var valA = calculateCustomRigValuation(rigA.items);
    var valB = calculateCustomRigValuation(rigB.items);

    return `
      <div class="compare-rig-card">
        <h4>${escapeHtml(rigA.name)}</h4>
        <div class="compare-price-tag">$${valA.toLocaleString()}</div>
        <div class="compare-specs-table">
          ${CATALOG.categories.map(function (cat) {
            var item = findItemInItems(rigA.items, cat.id);
            return `<div class="compare-spec-row">
              <span class="spec-cat-label">${cat.name}:</span>
              <strong>${item ? (item.brand + ' ' + item.model + ' ($' + item.price + ')') : 'None'}</strong>
            </div>`;
          }).join("")}
        </div>
      </div>

      <div class="compare-rig-card">
        <h4>${escapeHtml(rigB.name)}</h4>
        <div class="compare-price-tag">$${valB.toLocaleString()}</div>
        <div class="compare-specs-table">
          ${CATALOG.categories.map(function (cat) {
            var item = findItemInItems(rigB.items, cat.id);
            return `<div class="compare-spec-row">
              <span class="spec-cat-label">${cat.name}:</span>
              <strong>${item ? (item.brand + ' ' + item.model + ' ($' + item.price + ')') : 'None'}</strong>
            </div>`;
          }).join("")}
        </div>
      </div>
    `;
  }

  function findItemInItems(items, category) {
    var s = items.find(function (slot) { return slot.category === category; });
    return s ? getItem(s.itemId) : null;
  }

  function calculateCustomRigValuation(items) {
    var total = 0;
    items.forEach(function (s) {
      var it = getItem(s.itemId);
      if (it) total += it.price * (s.qty || 1);
    });
    return total;
  }

  /* ------------------------------------------------------------- Actions */
  function setupGlobalListeners() {
    document.addEventListener("click", function (e) {
      // 1. Modal backdrop close
      if (e.target.classList.contains("picker-backdrop")) {
        closeModal();
        return;
      }

      // 2. Button / Card actions
      var btn = e.target.closest("[data-action]") || e.target.closest(".btn-select-item") || e.target.closest(".picker-close");
      if (!btn) return;

      var action = btn.getAttribute("data-action");

      // Handle item selection from modal (both button click and card click)
      if (action === "select-item" || btn.classList.contains("btn-select-item") || btn.classList.contains("picker-card")) {
        var itemId = btn.getAttribute("data-item-id");
        if (activeModalSlotId && itemId) {
          var targetSlot = currentRig.items.find(function (s) { return s.slotId === activeModalSlotId; });
          if (targetSlot) {
            if (!replaceSlotItem(targetSlot, itemId)) return;
          } else {
            currentRig.items.push({
              slotId: activeModalSlotId,
              category: activeModalCategory,
              itemId: itemId,
              qty: 1,
              owned: false
            });
          }
          playClickSfx("select");
          closeModal();
          saveActiveState();
          renderApp();
        }
        return;
      }

      if (action === "step-qty") {
        var stepSlotId = btn.getAttribute("data-slot-id");
        var stepVal = parseInt(btn.getAttribute("data-step"), 10) || 1;
        var sToStep = currentRig.items.find(function (s) { return s.slotId === stepSlotId; });
        if (sToStep) {
          var newQ = (sToStep.qty || 1) + stepVal;
          if (newQ >= 1 && newQ <= 4) {
            sToStep.qty = newQ;
            playClickSfx("toggle");
            saveActiveState();
            renderApp();
          }
        }
      } else if (action === "toggle-sound") {
        soundEnabled = !soundEnabled;
        safeStorageSet("offbeat.rig.sfx", soundEnabled ? "on" : "muted");
        if (soundEnabled) playClickSfx("toggle");
        renderApp();
      } else if (action === "open-export-modal") {
        openExportModal();
      } else if (action === "copy-reddit-md") {
        var redBox = document.getElementById("reddit-export-box");
        if (redBox) {
          navigator.clipboard.writeText(redBox.value).then(function () {
            alert("✓ Reddit Markdown copied to clipboard!");
          });
        }
      } else if (action === "copy-share-url") {
        var linkBox = document.getElementById("link-export-box");
        if (linkBox) {
          navigator.clipboard.writeText(linkBox.value).then(function () {
            alert("✓ Shareable link copied to clipboard!");
          });
        }
      } else if (action === "download-canvas-image") {
        downloadCanvasImage();
      } else if (action === "pick") {
        var slotId = btn.getAttribute("data-slot-id");
        var category = btn.getAttribute("data-category");
        if (slotId && category) openPickerModal(slotId, category);
      } else if (action === "inspect-item") {
        var inspId = btn.getAttribute("data-item-id");
        if (inspId) openInspectorModal(inspId);
      } else if (action === "close-modal" || btn.classList.contains("picker-close")) {
        closeModal();
      } else if (action === "toggle-slot-owned") {
        var tSlotId = btn.getAttribute("data-slot-id");
        var slotToToggle = currentRig.items.find(function (s) { return s.slotId === tSlotId; });
        if (slotToToggle) {
          slotToToggle.owned = !slotToToggle.owned;
          playClickSfx("toggle");
          saveActiveState();
          renderApp();
        }
      } else if (action === "auto-fix-cable") {
        var cableId = btn.getAttribute("data-cable-id");
        if (cableId) {
          var existingCableSlot = currentRig.items.find(function (s) { return s.category === "cables"; });
          if (existingCableSlot) {
            if (!replaceSlotItem(existingCableSlot, cableId)) return;
          } else {
            currentRig.items.push({
              slotId: "core-cable",
              category: "cables",
              itemId: cableId,
              qty: 1,
              owned: false
            });
          }
          playClickSfx("select");
          saveActiveState();
          renderApp();
        }
      } else if (action === "auto-fix-slot") {
        var fixSlotId = btn.getAttribute("data-slot-id");
        var fixItemId = btn.getAttribute("data-item-id");
        var targetFixSlot = currentRig.items.find(function (s) { return s.slotId === fixSlotId; });
        if (targetFixSlot) {
          if (!replaceSlotItem(targetFixSlot, fixItemId)) return;
        } else {
          var fixItem = getItem(fixItemId);
          if (fixItem) {
            currentRig.items.push({
              slotId: fixSlotId,
              category: fixItem.category,
              itemId: fixItemId,
              qty: 1,
              owned: false
            });
          }
        }
        playClickSfx("select");
        saveActiveState();
        renderApp();
      } else if (action === "remove-slot") {
        var rSlotId = btn.getAttribute("data-slot-id");
        currentRig.items = currentRig.items.filter(function (s) { return s.slotId !== rSlotId; });
        playClickSfx("toggle");
        saveActiveState();
        renderApp();
      } else if (action === "open-add-slot") {
        var menu = document.getElementById("add-slot-menu");
        if (menu) menu.hidden = !menu.hidden;
      } else if (action === "add-new-slot") {
        var addCat = btn.getAttribute("data-category");
        var menuElem = document.getElementById("add-slot-menu");
        if (menuElem) menuElem.hidden = true;
        var newSlotId = "extra-" + addCat + "-" + Date.now();
        openPickerModal(newSlotId, addCat);
      } else if (action === "copy-checklist") {
        copyChecklistToClipboard();
      } else if (action === "save-rig") {
        promptSaveRig();
      } else if (action === "open-compare") {
        openCompareModal();
      } else if (action === "random-rig") {
        loadRandomPreset();
      } else if (action === "load-saved-rig") {
        var idx = parseInt(btn.getAttribute("data-index"), 10);
        loadSavedRig(idx);
      } else if (action === "delete-saved-rig") {
        var delIdx = parseInt(btn.getAttribute("data-index"), 10);
        deleteSavedRig(delIdx);
      }
    });

    // Preset pills click
    document.addEventListener("click", function (e) {
      var presetBtn = e.target.closest("[data-preset-id]");
      if (!presetBtn) return;
      var pId = presetBtn.getAttribute("data-preset-id");
      var preset = CATALOG.presets.find(function (p) { return p.id === pId; });
      if (preset) {
        playClickSfx("preset");
        loadPresetData(preset);
      }
    });

    // Title edit
    document.addEventListener("blur", function (e) {
      if (e.target.matches("[data-rig-name]")) {
        currentRig.name = e.target.textContent.trim() || "My Custom DJ Rig";
        saveActiveState();
      }
    }, true);

    // Escape key closes modal
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeModal();
    });
  }

  function loadPresetData(preset) {
    currentRig.name = preset.name;
    currentRig.items = convertPresetToItems(preset);
    saveActiveState();
    renderApp();
  }

  function loadRandomPreset() {
    if (!CATALOG || !CATALOG.presets) return;
    var randomIdx = Math.floor(Math.random() * CATALOG.presets.length);
    playClickSfx("preset");
    loadPresetData(CATALOG.presets[randomIdx]);
  }

  function copyChecklistToClipboard() {
    var stats = calculateRigStats();
    var lines = [
      "=========================================",
      "  OFFBEAT DJ RIG SHOPPING CHECKLIST",
      "  " + currentRig.name,
      "=========================================",
      ""
    ];

    currentRig.items.forEach(function (slot) {
      var item = getSlotItem(slot);
      if (item) {
        var qty = slot.qty || 1;
        var statusStr = slot.owned ? "[ALREADY OWNED]" : "[NEED TO BUY]";
        lines.push(statusStr + " (" + qty + "x) " + item.brand + " " + item.model + " - $" + (item.price * qty));
      }
    });

    lines.push("");
    lines.push("Total Setup Valuation: $" + stats.totalValue.toLocaleString());
    lines.push("Owned Gear Savings: -$" + stats.ownedValue.toLocaleString());
    lines.push("Total Out-of-Pocket Spend: $" + stats.purchaseCost.toLocaleString());
    lines.push("");
    lines.push("Plan and customize your DJ rig on Offbeat: " + window.location.href);

    var text = lines.join("\n");
    navigator.clipboard.writeText(text).then(function () {
      alert("✓ Shopping checklist copied to clipboard!");
    }).catch(function () {
      prompt("Copy your shopping checklist below:", text);
    });
  }

  function getSavedRigs() {
    try {
      var raw = safeStorageGet("offbeat.rigs.saved");
      if (!raw || raw.length > 100000) return [];
      var saved = JSON.parse(raw);
      if (!Array.isArray(saved)) return [];
      return saved.slice(0, 15).map(function (entry) {
        var clean = sanitizeRigState(entry);
        if (!clean) return null;
        return {
          name: clean.name, items: clean.items,
          totalCost: calculateCustomRigValuation(clean.items.filter(function (slot) { return !slot.owned; })),
          date: typeof entry.date === "string" ? entry.date.slice(0, 32) : "Saved"
        };
      }).filter(Boolean);
    } catch (e) { return []; }
  }

  function promptSaveRig() {
    var name = prompt("Name your setup:", currentRig.name);
    if (!name) return;
    currentRig.name = name.slice(0, 80);

    var stats = calculateRigStats();
    var saved = getSavedRigs();
    saved.unshift({
      name: currentRig.name,
      items: JSON.parse(JSON.stringify(currentRig.items)),
      totalCost: stats.purchaseCost,
      date: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    });

    if (saved.length > 15) saved = saved.slice(0, 15);
    safeStorageSet("offbeat.rigs.saved", JSON.stringify(saved));
    saveActiveState();
    renderApp();
  }

  function loadSavedRig(index) {
    var saved = getSavedRigs();
    if (!saved[index]) return;
    var r = saved[index];
    if (!normalizeRigState(r)) return;
    playClickSfx("preset");
    saveActiveState();
    renderApp();
  }

  function deleteSavedRig(index) {
    var saved = getSavedRigs();
    saved.splice(index, 1);
    safeStorageSet("offbeat.rigs.saved", JSON.stringify(saved));
    renderApp();
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  /* ---------------------------------------------------------------- Start */
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
