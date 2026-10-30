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
    context: "studio",
    items: [
      { slotId: "core-ctrl", category: "controllers", itemId: "pioneer-ddj-flx4", qty: 1, owned: false },
      { slotId: "core-hp", category: "headphones", itemId: "sennheiser-hd25", qty: 1, owned: false },
      { slotId: "core-spk", category: "speakers", itemId: "pioneer-dm40d", qty: 1, owned: false },
      { slotId: "core-host", category: "laptops", itemId: "existing-mobile-device", qty: 1, owned: true }
    ]
  };

  // Active slot being edited in modal
  var activeModalSlotId = null;
  var activeModalCategory = null;
  var activeModalSpeakerRole = null;

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

  // A guide ?add= link must apply to an explicitly shared rig before any
  // unrelated localStorage state from this browser.
  function restoreSharedRigParam(value) {
    if (!value || value.length > 8192) return false;
    try { return normalizeRigState(JSON.parse(decodeURIComponent(atob(value)))); }
    catch (e) { console.warn("Invalid rig URL param:", e); return false; }
  }

  function parseUrlOrLocalState() {
    var params = new URLSearchParams(window.location.search);

    // 1. Guide-to-planner deep links must preserve the visitor's current rig.
    // Previously ?add= silently started from the default preset, discarding
    // saved equipment, quantities, and ownership selections.
    var addParam = params.get("add");
    if (addParam) {
      var targetItem = getItem(addParam);
      if (targetItem) {
        if (!restoreSharedRigParam(params.get("rig"))) {
          var savedRig = safeStorageGet("offbeat.rig.active");
          if (savedRig && savedRig.length <= 16384) {
            try { normalizeRigState(JSON.parse(savedRig)); }
            catch (e) { console.warn("Invalid local rig state:", e); }
          }
        }

        // Additional accessories are additive. A guide's cable/USB/mic link
        // must not replace an unrelated accessory already in the shopping list.
        var additive = ["cables", "storage", "microphones", "stands"].indexOf(targetItem.category) !== -1;
        var alreadySelected = currentRig.items.some(function (s) { return s.itemId === targetItem.id; });
        var existingSlot = additive ? null : currentRig.items.find(function (s) {
          return s.category === targetItem.category && (s.category !== "speakers" || speakerRoleForSlot(s) === speakerRoleForItem(targetItem));
        });
        if (alreadySelected) {
          // An Add-to-Rig link is idempotent even when the item lives in a
          // second core slot. Never overwrite another selected/owned device.
        } else if (existingSlot) {
          // A genuinely new core product replaces the primary slot, while
          // accessories remain additive. Replacement resets ownership.
          replaceSlotItem(existingSlot, targetItem.id);
          existingSlot.qty = 1;
        } else {
          currentRig.items.push({
            slotId: "guide-" + targetItem.category + "-" + Date.now(),
            category: targetItem.category,
            itemId: targetItem.id,
            qty: 1,
            owned: false
          });
        }
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
    if (restoreSharedRigParam(params.get("rig"))) return;

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
        qty: item.no_purchase === true ? 1 : (Number.isInteger(slot.qty) && slot.qty >= 1 && slot.qty <= 4 ? slot.qty : 1),
        owned: item.no_purchase === true || slot.owned === true,
        role: item.category === "speakers" ? speakerRoleForItem(item) : undefined
      });
    });
    if (!items.length) return null;
    return {
      name: typeof data.name === "string" ? data.name.slice(0, 80) : "My Custom DJ Rig",
      context: data.context === "audience" ? "audience" : "studio",
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

  // Catalog role evidence, not connector shape, controls speaker selection.
  function speakerRoleForItem(item) {
    if (!item || item.category !== "speakers") return null;
    return item.speaker_role === "audience_pa" || item.speaker_role === "nearfield" ? item.speaker_role : null;
  }
  function speakerRoleForSlot(slot) {
    if (!slot || slot.category !== "speakers") return null;
    return speakerRoleForItem(getSlotItem(slot)) ||
      (slot.role === "audience_pa" || slot.role === "nearfield" ? slot.role :
        (currentRig.context === "audience" ? "audience_pa" : "nearfield"));
  }
  function isSpeakerEligibleForRole(item, role) {
    return Boolean(role && speakerRoleForItem(item) === role);
  }
  function preferredSpeakerSlot() {
    var role = currentRig.context === "audience" ? "audience_pa" : "nearfield";
    return currentRig.items.find(function (slot) {
      return slot.category === "speakers" && speakerRoleForItem(getSlotItem(slot)) === role;
    }) || currentRig.items.find(function (slot) { return slot.category === "speakers"; }) || null;
  }

  // Owning the old product does not mean owning its replacement.
  function replaceSlotItem(slot, itemId) {
    var item = getItem(itemId);
    if (!slot || !item || slot.category !== item.category) return false;
    if (slot.category === "speakers" && !isSpeakerEligibleForRole(item, speakerRoleForSlot(slot))) return false;
    if (slot.itemId !== item.id) slot.owned = false;
    slot.itemId = item.id;
    if (slot.category === "speakers") slot.role = speakerRoleForItem(item);
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
    var nextUpgrade = recommendNextUpgrade(compatibility);

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

  // A speaker package can supply a passive 3.5mm-stereo-to-dual-RCA lead.
  // Verify the two connector types and the explicit manufacturer bundle.
  function includedSpeakerCableMatches(controller, speakers) {
    if (!controller || !speakers || speakers.included_audio_cable_3_5mm_to_rca !== true) return false;
    var outputs = controller.master_outputs || [];
    var inputs = speakers.inputs || [];
    var has = function (ports, connector) {
      return ports.some(function (port) { return port.indexOf(connector) !== -1; });
    };
    return (has(outputs, "3.5mm") && has(inputs, "RCA")) ||
           (has(outputs, "RCA") && has(inputs, "3.5mm"));
  }

  /* ------------------------------------------- Real DJ Compatibility Engine */
  function runDeepCompatibilityChecks() {
    var controllerSlot = currentRig.items.find(function (s) { return s.category === "controllers"; });
    var headphonesSlot = currentRig.items.find(function (s) { return s.category === "headphones"; });
    var speakersSlot = preferredSpeakerSlot();
    var laptopSlot = currentRig.items.find(function (s) { return s.category === "laptops"; });
    var cableSlots = currentRig.items.filter(function (s) { return s.category === "cables"; });
    var microphoneSlots = currentRig.items.filter(function (s) { return s.category === "microphones"; });

    var controller = controllerSlot ? getSlotItem(controllerSlot) : null;
    var headphones = headphonesSlot ? getSlotItem(headphonesSlot) : null;
    var speakers = speakersSlot ? getSlotItem(speakersSlot) : null;
    var laptop = laptopSlot ? getSlotItem(laptopSlot) : null;

    var checks = [];
    var fatalErrors = 0;
    var warnings = 0;
    var requiresManualReview = false;

    // Studio monitors are nearfield listening equipment, not crowd PA.
    // The visitor chooses the listening context; a venue rig cannot receive
    // a green compatibility verdict merely because RCA/XLR plugs fit.
    if (currentRig.context === "audience") {
      var speakerChoices = currentRig.items.filter(function (slot) {
        return slot.category === "speakers";
      }).map(getSlotItem).filter(Boolean);
      var hasAudiencePA = speakerChoices.some(function (item) {
        return item.speaker_role === "audience_pa";
      });
      var hasNearfield = speakerChoices.some(function (item) {
        return item.speaker_role === "nearfield";
      });
      if (hasNearfield) {
        warnings++;
        requiresManualReview = true;
        checks.push({
          type: "warning", statusLevel: "workable",
          title: "Nearfield Studio Monitors Are Not Audience PA",
          desc: "Selected desktop/studio monitors are designed for close listening, not projecting sound to a crowd. Do not use them as the event PA; choose venue-rated powered PA cabinets and verify coverage, placement and levels.",
          fixCableId: null
        });
      }
      if (!hasAudiencePA) {
        fatalErrors++;
        checks.push({
          type: "error", statusLevel: "incompatible",
          title: "Audience PA System Not Selected",
          desc: "This rig is intended for a party or audience, but no catalog-confirmed audience PA is selected. A matching audio connector or nearfield monitor does not establish adequate sound reinforcement. Select an appropriate powered PA system.",
          fixCableId: null
        });
      } else {
        warnings++;
        requiresManualReview = true;
        checks.push({
          type: "warning", statusLevel: "workable",
          title: "Audience Coverage and Deployment Need Verification",
          desc: "A powered PA cabinet is selected, but room size, audience count, speaker quantity, stands, power, cable lengths, bass coverage and safe sound levels have not been verified. One cabinet is not a guaranteed stereo or venue-ready system.",
          fixCableId: null
        });
      }
    }

    // The shopping list supports multiple controllers, speakers and other core
    // devices, but the connection engine evaluates only the first of each.
    // Never mark a multi-device rig green based on a single-device check.
    ["controllers", "speakers", "laptops", "headphones"].forEach(function (category) {
      // Quantity steppers can represent multiple physical devices in ONE slot.
      // Count units, not just distinct slots, or two identical controllers/
      // speaker sets can incorrectly inherit a green single-device verdict.
      var count = currentRig.items.reduce(function (total, slot) {
        return total + (slot.category === category ? slot.qty || 1 : 0);
      }, 0);
      if (count < 2) return;
      requiresManualReview = true;
      warnings++;
      checks.push({
        type: "warning", statusLevel: "workable",
        title: "Multiple " + category + " Need Manual Verification",
        desc: "This rig contains " + count + " " + category + ". The shopping total includes all selected gear, " +
          "but automated connector, host and cue checks cover only the first item in each category. " +
          "Verify every additional device's signal path, software and power requirements before purchasing.",
        fixCableId: null
      });
    });

    // The catalog lists vocal microphones but has no verified microphone-input
    // specifications for controllers or mixers. An XLR master OUTPUT and an
    // XLR speaker cable do not establish a usable microphone INPUT path.
    // Never present a wedding/MC rig as ready on that unsupported inference.
    if (microphoneSlots.length) {
      var microphoneCount = microphoneSlots.reduce(function (count, slot) {
        return count + (slot.qty || 1);
      }, 0);
      requiresManualReview = true;
      warnings++;
      checks.push({
        type: "warning", statusLevel: "workable",
        title: "Microphone Input and Cable Need Verification",
        desc: "This rig includes " + microphoneCount + " vocal microphone(s), but the catalog does not verify " +
          "microphone inputs, mic preamp gain, or required microphone cables for the selected controller/mixer. " +
          "An XLR speaker output or cable does not prove that a microphone can be connected. " +
          "Confirm each mic input, cable, gain and any power requirements before purchasing.",
        fixCableId: null
      });
    }

    // A rig with no controller/decks/mixer is not a playable DJ setup.
    // Accessories alone must never produce a green preliminary match.
    if (!controller) {
      checks.push({
        type: "error", statusLevel: "incompatible",
        title: "DJ Controller or Mixer Required",
        desc: "No DJ controller, decks, or mixer are selected. Add a compatible DJ playback and mixing system before treating this as a complete setup.",
        fixCableId: null
      });
      fatalErrors++;
    }

    // A controller without headphones or speakers has no selected listening
    // path. A high readiness score would encourage an incomplete purchase.
    if (controller && !headphones && !speakers) {
      checks.push({
        type: "error", statusLevel: "incompatible",
        title: "Headphones or Speakers Required",
        desc: "This rig has no selected listening or cue output device. Add DJ headphones or speakers " +
          "before treating it as a playable setup; confirm the controller's audio outputs.",
        fixCableId: null
      });
      fatalErrors++;
    }

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
      if (includedSpeakerCableMatches(controller, speakers)) {
        checks.push({
          type: "success", statusLevel: "verified",
          title: "Included Speaker Cable Matches",
          desc: speakers.model + " includes a 3.5mm stereo-to-dual-RCA cable that matches " +
            controller.model + "'s master output and the speaker input. " +
            "No separate cable purchase is needed for this connection; verify package contents and length.",
          fixCableId: null
        });
        if (selected) {
          checks.push({
            type: "warning", statusLevel: "workable",
            title: "Separate Cable May Be Unnecessary",
            desc: selected.name + " is also selected. The speaker package already includes a matching cable; " +
              "keep the extra only if another connection needs it.",
            fixCableId: null
          });
          warnings++;
        }
      } else if (selected) {
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
      if (laptop.id === "existing-mobile-device" && !controller.standalone) {
        if (controller.id === "pioneer-ddj-flx4") {
          checks.push({
            type: "warning", statusLevel: "workable",
            title: "Mobile Host, USB Audio and Power Need Verification",
            desc: "The $0 host assumes you ALREADY own a compatible iOS/Android phone or tablet. " +
              "Verify current rekordbox mobile support, a suitable USB cable and separate 9V/3A " +
              "power for DDJ-FLX4. USB can route master/headphone audio through the controller; " +
              "Bluetooth control leaves audio on the mobile device. Power is not priced here.",
            fixCableId: null
          });
          warnings++;
        } else if (controller.id === "pioneer-ddj-flx2") {
          // AlphaTheta explicitly supports rekordbox/djay mobile on FLX2.
          // Unlike FLX4, compatible USB-C hosts can bus-power FLX2; some
          // Android devices cannot. Bluetooth MIDI needs separate USB power.
          checks.push({
            type: "warning", statusLevel: "workable",
            title: "FLX2 Mobile Host, USB Audio and Power Need Verification",
            desc: "The $0 host assumes you ALREADY own a compatible phone or tablet. " +
              "DDJ-FLX2 supports rekordbox/djay mobile with the included USB-C cable on supported devices. " +
              "Compatible USB-C devices may supply bus power, but some Android devices cannot; " +
              "the rekordbox built-in-phone-speaker route is iOS-only. Bluetooth MIDI control " +
              "requires separate USB-C power and does not itself route audio through the controller. " +
              "Verify your exact phone, app, USB audio, headphone/master routing and power before purchasing. " +
              "Any external power accessory is not priced here.",
            fixCableId: null
          });
          warnings++;
        } else if (controller.id === "alphatheta-ddj-grv6") {
          // AlphaTheta confirms mobile rekordbox support, but only decks 1
          // and 2 work on iOS/Android. No Bluetooth; USB-C and sufficient
          // power are required. Do not reject a real two-deck mobile route
          // or imply the desktop four-deck workflow transfers to a phone.
          checks.push({
            type: "warning", statusLevel: "workable",
            title: "GRV6 Mobile: Two Decks Only, USB-C and Power Required",
            desc: "DDJ-GRV6 supports rekordbox for iOS/Android, but mobile playback " +
              "is limited to channels 1 and 2, not all four hardware channels. " +
              "The controller has no Bluetooth connection. Confirm a compatible " +
              "phone/tablet, USB-C data/audio routing and adequate power " +
              "(9V/3A adapter or a suitable 5V/1.5A USB host). " +
              "External power accessories are not included in this estimate. " +
              "Use a compatible computer for the full four-deck workflow.",
            fixCableId: null
          });
          warnings++;
        } else {
          checks.push({
            type: "error", statusLevel: "incompatible",
            title: "Mobile Host Not Verified for This Controller",
            desc: "This existing-phone option is qualified only for conditional DDJ-FLX4, DDJ-FLX2, or DDJ-GRV6 routes. " +
              "Choose a compatible computer or verify this controller's mobile software, power and audio path.",
            fixSlotId: laptopSlot ? laptopSlot.slotId : null,
            fixItemId: "macbook-air-m2",
            fixActionText: "Compare with a computer host"
          });
          fatalErrors++;
        }
      } else if (laptop.id === "standalone-usb-only" && !controller.standalone) {
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
      var ctrlMini = ctrlJack.indexOf("3.5mm") !== -1;
      var ctrlQuarter = ctrlJack.indexOf('1/4"') !== -1;
      var hpMini = hpJack.indexOf("3.5mm") !== -1;
      var hpQuarter = hpJack.indexOf('1/4"') !== -1;

      // Most catalog headphones have a native 3.5mm plug AND an included
      // 1/4-inch adapter. Never suggest purchasing an unnecessary extra.
      // The generic adapter catalog entry does not specify connector direction.
      if ((ctrlMini && !ctrlQuarter && hpQuarter && !hpMini) ||
          (ctrlQuarter && !ctrlMini && hpMini && !hpQuarter)) {
        var requiredAdapter = ctrlMini
          ? "1/4-inch female to 3.5mm male"
          : "3.5mm female to 1/4-inch male";
        checks.push({
          type: "warning", statusLevel: "workable",
          title: "Headphone Connector Adapter Needed",
          desc: "The listed headphone plug does not fit the controller cue socket directly. Check for an included " +
            requiredAdapter + " adapter or purchase the correct direction separately.",
          fixCableId: null
        });
        warnings++;
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
    if (requiresManualReview) readiness = Math.min(readiness, 50);

    return {
      readiness: Math.max(readiness, 10),
      checks: checks,
      fatalErrors: fatalErrors,
      warnings: warnings,
      requiresManualReview: requiresManualReview
    };
  }

  /* ------------------------------------------- Smart Upgrade Path Advisor */
  function recommendNextUpgrade(compatibility) {
    // An upsell must never distract from an incomplete or manually unverified
    // rig. Compatibility checks are authoritative for the current selection.
    var verdict = compatibility || runDeepCompatibilityChecks();
    if (verdict.fatalErrors > 0 || verdict.requiresManualReview) return null;

    var controllerSlot = currentRig.items.find(function (s) { return s.category === "controllers"; });
    var headphonesSlot = currentRig.items.find(function (s) { return s.category === "headphones"; });
    var speakersSlot = preferredSpeakerSlot();
    var laptopSlot = currentRig.items.find(function (s) { return s.category === "laptops"; });
    var standSlot = currentRig.items.find(function (s) { return s.category === "stands"; });
    var storageSlot = currentRig.items.find(function (s) { return s.category === "storage"; });

    var controller = controllerSlot ? getSlotItem(controllerSlot) : null;
    var headphones = headphonesSlot ? getSlotItem(headphonesSlot) : null;
    var speakers = speakersSlot ? getSlotItem(speakersSlot) : null;
    if (!controller) return null;

    function offer(itemId, role, description, targetSlotId) {
      var target = getItem(itemId);
      if (!target || currentRig.items.some(function (slot) { return slot.itemId === itemId; })) return null;
      return {
        role: role,
        targetName: target.brand + " " + target.model + " (Est. $" + target.price.toLocaleString("en-US") + ")",
        desc: description,
        targetId: itemId,
        targetSlotId: targetSlotId
      };
    }

    if (headphones && headphones.price < 100 && controller.price >= 299) {
      var headphonesUpgrade = offer("sennheiser-hd25", "Headphones Upgrade",
        "Consider closed-back DJ headphones with replaceable parts and isolation suited to your venue. Check fit and current price before buying.",
        headphonesSlot.slotId);
      if (headphonesUpgrade) return headphonesUpgrade;
    }

    if (controller.channels === 4 && speakers && speakers.price < 200) {
      // Four mixer channels do NOT imply balanced master outputs. In
      // particular, RCA-only controllers must not be upsold an XLR monitor
      // pair on the unsupported claim that their outputs are balanced.
      var outputs = controller.master_outputs || [];
      var balanced = outputs.some(function (output) {
        return /\bXLR\b/i.test(output) ||
          (/\bTRS\b/i.test(output) && /balanced/i.test(output));
      });
      if (balanced) {
        var monitorsUpgrade = offer("yamaha-hs5", "Studio Monitor Upgrade",
          "This controller lists a balanced output. Compare the monitor inputs, required pair quantity, cabling, room size and live prices before upgrading.",
          speakersSlot.slotId);
        if (monitorsUpgrade) return monitorsUpgrade;
      }
    }

    if (!standSlot && laptopSlot && getSlotItem(laptopSlot).id !== "existing-mobile-device" && !controller.standalone) {
      var standUpgrade = offer("laptop-stand-pyle", "Optional Laptop Stand",
        "A laptop stand may improve visibility and desk space. Check your laptop size and booth clearance before purchasing.",
        "core-stand");
      if (standUpgrade) return standUpgrade;
    }

    // USB media is only a relevant optional purchase for a standalone player.
    // Never claim that a laptop-dependent controller can load DJ sets from USB,
    // or that a particular flash drive guarantees zero-lag playback.
    if (controller.standalone && !storageSlot) {
      return offer("usb-sandisk-extreme", "Optional Performance Media",
        "Check your standalone player's supported USB formats, library export requirements and current drive compatibility before purchasing.",
        "core-storage");
    }

    return null;
  }

  /* ----------------------------------------------------- Live route explanation */
  // A planning diagram must reflect the SAME checks as the shopping advisor.
  // Animated paths mean only that catalog-listed connectors/cables appear to
  // match; they never claim the equipment is plugged in or tested.
  function renderSignalPathMap(compatibility) {
    var controllerSlot = findSlot("controllers");
    var speakerSlot = preferredSpeakerSlot();
    var headphoneSlot = findSlot("headphones");
    var hostSlot = findSlot("laptops");
    var controller = controllerSlot && getSlotItem(controllerSlot);
    var speaker = speakerSlot && getSlotItem(speakerSlot);
    var headphone = headphoneSlot && getSlotItem(headphoneSlot);
    var host = hostSlot && getSlotItem(hostSlot);
    var checks = compatibility.checks || [];
    var hasCheck = function (title) {
      return checks.some(function (check) { return check.title === title; });
    };

    var hostStatus = "review", hostDetail = "Choose a controller and playback host.";
    if (!controller) {
      hostStatus = "blocked";
    } else if (controller.standalone) {
      hostStatus = "review";
      hostDetail = "Standalone playback listed. Check media format, firmware and source selection.";
    } else if (!host || hasCheck("Host Computer Required") ||
               hasCheck("Host Computer Required for DJing") ||
               hasCheck("Mobile Host Not Verified for This Controller")) {
      hostStatus = "blocked";
      hostDetail = "No qualified playback host. Resolve the host warning before buying.";
    } else if (host.id === "existing-mobile-device") {
      hostDetail = "Mobile USB/audio and power are conditional; check this exact phone and app.";
    } else {
      hostDetail = "Computer + DJ software + USB. Verify drivers and software unlocks.";
    }

    var masterStatus = "review", masterDetail = "Select a controller and speakers to plan a room output.";
    if (!controller) {
      masterStatus = "blocked";
    } else if (!speaker) {
      masterDetail = "No speaker output selected; headphones-only practice may still work.";
    } else if (hasCheck("Included Speaker Cable Matches")) {
      masterStatus = "included";
      masterDetail = "Matching 3.5 mm / RCA lead listed as included with the speaker package.";
    } else if (hasCheck("Listed Audio Connection Match")) {
      masterStatus = "listed";
      masterDetail = "Selected cable matches listed output/input connectors; verify wiring and levels.";
    } else if (hasCheck("Audio Cable Needed")) {
      masterStatus = "missing";
      masterDetail = "A matching cable is not selected. Use the recommendation below.";
    } else {
      masterDetail = "Connector or cable route needs manual confirmation.";
    }
    if (hasCheck("Audience PA System Not Selected")) {
      masterStatus = "blocked";
      masterDetail = "A studio monitor cable match is not audience PA. Select a venue-rated powered PA system.";
    }
    if (compatibility.requiresManualReview && (masterStatus === "included" || masterStatus === "listed")) {
      masterStatus = "review";
      masterDetail += " Additional devices require independent routing checks.";
    }

    var cueStatus = "review", cueDetail = "Select headphones to plan the cue output.";
    if (!controller) {
      cueStatus = "blocked";
    } else if (headphone) {
      if (hasCheck("Headphone Connector Adapter Needed")) {
        cueStatus = "missing";
        cueDetail = "Check the required adapter direction and whether it is included.";
      } else {
        cueStatus = "listed";
        cueDetail = "Headphone jack is listed; confirm cue routing and the physical plug.";
      }
      if (compatibility.requiresManualReview) {
        cueStatus = "review";
        cueDetail += " Additional devices need separate checks.";
      }
    }

    var routes = [
      { key: "host", label: "Playback source", from: host ? host.model : "No host selected",
        to: controller ? controller.model : "No controller", status: hostStatus, detail: hostDetail },
      { key: "master", label: "Room audio", from: controller ? controller.model : "No controller",
        to: speaker ? speaker.model : "No speakers selected", status: masterStatus, detail: masterDetail },
      { key: "cue", label: "Headphone cue", from: controller ? controller.model : "No controller",
        to: headphone ? headphone.model : "No headphones selected", status: cueStatus, detail: cueDetail }
    ];
    return `<div class="rig-route-map" role="group" aria-label="DJ equipment connection planning">
      <div class="rig-route-map-heading">
        <strong>Connection map</strong>
        <span>Live to your selected rig · planning only</span>
      </div>
      <div class="rig-route-map-grid">${routes.map(function (route) {
        return `<div class="rig-route" data-route="${route.key}" data-status="${route.status}">
          <strong class="rig-route-label">${escapeHtml(route.label)}</strong>
          <div class="rig-route-endpoints"><span>${escapeHtml(route.from)}</span>
            <span class="rig-route-wire" aria-hidden="true"></span>
            <span>${escapeHtml(route.to)}</span></div>
          <p>${escapeHtml(route.detail)}</p>
        </div>`;
      }).join("")}</div>
      <p class="rig-route-disclaimer">Moving signals indicate a catalog-listed or included path, not a tested physical connection. Amber and grey paths need verification. See the compatibility checks below.</p>
    </div>`;
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
              <strong>${escapeHtml(p.name)}</strong> <span class="preset-badge">${escapeHtml(presetPriceBadge(p))}</span>
            </button>`;
          }).join("")}
        </div>

        <!-- Listening context controls: required to distinguish nearfield from crowd PA -->
        <div class="rig-preset-strip" role="group" aria-label="Where will this rig be used?">
          <span class="preset-label">Listening context:</span>
          <button type="button" class="rig-preset-pill" data-action="set-listening-context" data-context="studio" aria-pressed="${currentRig.context !== 'audience'}">Desk / studio practice</button>
          <button type="button" class="rig-preset-pill" data-action="set-listening-context" data-context="audience" aria-pressed="${currentRig.context === 'audience'}">Party / live audience</button>
          <span class="preset-label">Venue mode checks PA suitability; it does not certify coverage.</span>
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
            <span class="metric-sub">${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? "No listed issues found" : stats.compatibility.fatalErrors > 0 ? "❌ Incompatibility detected" : stats.compatibility.requiresManualReview ? "⚠️ Signal routing needs review" : "⚠️ " + stats.compatibility.warnings + " connection advisory"}</span>
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
            ${renderBoothSlot(preferredSpeakerSlot() || { slotId: "core-spk", category: "speakers", itemId: null, role: currentRig.context === "audience" ? "audience_pa" : "nearfield" }, currentRig.context === "audience" ? "Audience PA / Speakers" : "DJ Booth Monitors", "🔊")}
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
          ${renderSignalPathMap(stats.compatibility)}
        </div>
      </section>

      <!-- Compatibility Engine Alerts -->
      <section class="rig-compat-section">
        <div class="compat-box">
          <div class="compat-header">
            <h4>⚡ Hardware &amp; Signal Compatibility Assistant</h4>
            <span class="compat-status-tag ${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? 'tag--ok' : stats.compatibility.fatalErrors > 0 ? 'tag--err' : 'tag--warn'}">
              ${stats.compatibility.fatalErrors === 0 && stats.compatibility.warnings === 0 ? 'Preliminary Match' : stats.compatibility.fatalErrors > 0 ? '❌ Incompatible Configuration' : stats.compatibility.requiresManualReview ? '⚠️ Manual Routing Review Required' : '⚠️ Connection Verification Needed'}
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
              <button type="button" data-action="add-new-slot" data-category="speakers" data-speaker-role="nearfield">🔊 Add DJ Booth Monitors</button>
              <button type="button" data-action="add-new-slot" data-category="speakers" data-speaker-role="audience_pa">📢 Add Crowd-Facing PA</button>
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

  // Speaker listings price a PACKAGE, not necessarily one physical cabinet.
  // The catalog explicitly distinguishes stereo pairs from individual PA boxes.
  // Surface that distinction anywhere a buyer can change quantities or prices.
  function speakerPackageSummary(slot, item) {
    if (!slot || slot.category !== "speakers" || !item) return "";
    var qty = Math.max(1, Number(slot.qty) || 1);
    var label = String(item.box_label || "") + " " + String(item.model || "");
    var units = Number(item.speaker_units);
    if (units === 2 || (units !== 1 && /\bpair\b/i.test(label))) {
      return qty + (qty === 1 ? " stereo pair (2 physical speakers)" :
        " stereo pairs (" + (qty * 2) + " physical speakers)") +
        "; the listed price covers " + (qty === 1 ? "the pair" : "all selected pairs") + ".";
    }
    if (units === 1 || /\bsingle\b/i.test(label)) {
      return qty + (qty === 1 ? " individual PA cabinet" : " individual PA cabinets") +
        (qty === 1 ? "; a second cabinet is NOT included." :
          "; the price covers " + qty + " separate cabinets.");
    }
    return "Package quantity not verified in the catalog; confirm included speaker units before buying.";
  }

  function renderBoothSlot(slot, label, icon, isMain) {
    var item = getSlotItem(slot);
    var isOwned = Boolean(slot.owned) || Boolean(item && item.no_purchase === true);

    if (!item) {
      return `
        <div class="booth-card booth-card--empty ${isMain ? 'booth-card--main' : ''}" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}" data-speaker-role="${slot.category === "speakers" ? speakerRoleForSlot(slot) : ""}">
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
          <button type="button" class="booth-owned-toggle ${isOwned ? 'is-active' : ''}" data-action="toggle-slot-owned" data-slot-id="${slot.slotId}" ${item.no_purchase === true ? 'disabled aria-disabled="true"' : ''} title="Toggle already owned">
            ${isOwned ? '✓ Owned' : '🛒 Need'}
          </button>
        </div>
        <div class="booth-card-body" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}" data-speaker-role="${slot.category === "speakers" ? speakerRoleForSlot(slot) : ""}">
          <div class="booth-thumb-wrap">
            <img src="${item.image}" alt="${escapeHtml(item.brand + ' ' + item.model)}" loading="lazy" class="booth-thumb">
          </div>
          <div class="booth-info">
            <span class="booth-brand">${escapeHtml(item.brand)}</span>
            <strong class="booth-model">${escapeHtml(item.model)}</strong>
            <span class="booth-price ${isOwned ? 'price--owned' : ''}">
              ${isOwned ? '<s>$' + (item.price * (slot.qty || 1)) + '</s> (Owned)' : '$' + (item.price * (slot.qty || 1))}
            </span>
            ${slot.category === "speakers" ? '<span class="booth-package-detail">' +
              escapeHtml(speakerPackageSummary(slot, item)) + '</span>' : ''}
          </div>
        </div>
        <div class="booth-card-footer">
          <button type="button" class="booth-swap-btn" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}" data-speaker-role="${slot.category === "speakers" ? speakerRoleForSlot(slot) : ""}">
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
    var isOwned = Boolean(slot.owned) || Boolean(item && item.no_purchase === true);
    var catMeta = CATALOG.categories.find(function (c) { return c.id === slot.category; });
    var qty = slot.qty || 1;

    if (!item) {
      return `
        <tr class="rig-row rig-row--empty">
          <td><span class="cat-pill">${slot.category === "speakers" ? (speakerRoleForSlot(slot) === "audience_pa" ? "📢 Crowd-Facing PA" : "🔊 DJ Booth Monitors") : ((catMeta ? catMeta.icon : "") + " " + (catMeta ? catMeta.name : slot.category))}</span></td>
          <td colspan="4"><span class="empty-slot-msg">No item selected</span></td>
          <td><button type="button" class="btn btn-sm" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}" data-speaker-role="${slot.category === "speakers" ? speakerRoleForSlot(slot) : ""}">Select Component</button></td>
        </tr>
      `;
    }

    var linePrice = item.price * qty;
    var isPlatformPlaceholder = item.no_purchase === true || item.id === "standalone-usb-only";
    var amazonUrl = "https://www.amazon.com/s?k=" + encodeURIComponent(item.amazon_search || (item.brand + " " + item.model)) + "&tag=offbeatdj-20";
    var sweetwaterUrl = "https://www.sweetwater.com/store/search?s=" + encodeURIComponent(item.brand + " " + item.model);
    var reverbUrl = "https://reverb.com/marketplace?query=" + encodeURIComponent(item.brand + " " + item.model);

    return `
      <tr class="rig-row ${isOwned ? 'rig-row--owned' : ''}">
        <td class="cell-cat">
          <span class="cat-pill">${slot.category === "speakers" ? (speakerRoleForSlot(slot) === "audience_pa" ? "📢 Crowd-Facing PA" : "🔊 DJ Booth Monitors") : ((catMeta ? catMeta.icon : "") + " " + (catMeta ? catMeta.name : slot.category))}</span>
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
              ${slot.category === "speakers" ? '<p class="item-tagline speaker-package-detail">' +
                escapeHtml(speakerPackageSummary(slot, item)) + '</p>' : ''}
              ${item.slug ? `<a href="${item.slug}" class="item-guide-link">Read Offbeat Guide →</a>` : ''}
            </div>
          </div>
        </td>
        <td class="cell-qty">
          <div class="qty-stepper-wrap">
            <button type="button" class="qty-step-btn" data-action="step-qty" data-slot-id="${slot.slotId}" data-step="-1" aria-label="Decrease quantity" ${qty <= 1 || isPlatformPlaceholder ? 'disabled' : ''}>-</button>
            <span class="qty-display">${qty}</span>
            <button type="button" class="qty-step-btn" data-action="step-qty" data-slot-id="${slot.slotId}" data-step="1" aria-label="Increase quantity" ${qty >= 4 || isPlatformPlaceholder ? 'disabled' : ''}>+</button>
          </div>
        </td>
        <td class="cell-status">
          <button type="button" class="status-btn ${isOwned ? 'status-btn--owned' : 'status-btn--needed'}" data-action="toggle-slot-owned" data-slot-id="${slot.slotId}" ${isPlatformPlaceholder ? 'disabled aria-disabled="true"' : ''}>
            ${item.id === "existing-mobile-device" ? "Existing phone/tablet (verify)" : isPlatformPlaceholder ? "No laptop purchase" : (isOwned ? "🟢 I Own This" : "🔵 Need to Buy")}
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
            <button type="button" class="btn-swap-inline" data-action="pick" data-slot-id="${slot.slotId}" data-category="${slot.category}" data-speaker-role="${slot.category === "speakers" ? speakerRoleForSlot(slot) : ""}">Swap</button>
            ${isPlatformPlaceholder ? '<span class="owned-sub">' + (item.id === "existing-mobile-device" ? 'Existing phone/tablet — verify compatibility and power' : 'Setup mode — no hardware purchase') + '</span>' : `
            <a href="${sweetwaterUrl}" target="_blank" rel="nofollow noopener sponsored" class="btn-retail btn-retail--sw" title="Search Sweetwater">Sweetwater ↗</a>
            <a href="${amazonUrl}" target="_blank" rel="nofollow noopener sponsored" class="btn-retail btn-retail--amz" title="Search model on Amazon">Amazon ↗</a>
            <a href="${reverbUrl}" target="_blank" rel="nofollow noopener" class="btn-retail btn-retail--rev" title="Find used offers on Reverb">Reverb ↗</a>
            `}
            <button type="button" class="btn-del-slot" data-action="remove-slot" data-slot-id="${slot.slotId}" title="Remove this component">✕</button>
          </div>
        </td>
      </tr>
    `;
  }

  function getCableSummaryText() {
    var cables = currentRig.items.filter(function (s) { return s.category === "cables"; });
    if (cables.length === 0) {
      var controllerSlot = findSlot("controllers"), speakerSlot = findSlot("speakers");
      if (controllerSlot && speakerSlot &&
          includedSpeakerCableMatches(getSlotItem(controllerSlot), getSlotItem(speakerSlot))) {
        return "Speaker Package Includes Audio Cable";
      }
      return "No Audio Cables Selected";
    }
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
  function openPickerModal(slotId, category, requestedRole) {
    activeModalSlotId = slotId;
    activeModalCategory = category;
    var activeSlot = currentRig.items.find(function (s) { return s.slotId === slotId; });
    activeModalSpeakerRole = category === "speakers" ? (activeSlot ? speakerRoleForSlot(activeSlot) :
      (requestedRole === "nearfield" || requestedRole === "audience_pa" ? requestedRole :
        (currentRig.context === "audience" ? "audience_pa" : "nearfield"))) : null;
    var catMeta = CATALOG.categories.find(function (c) { return c.id === category; });
    var items = CATALOG.items.filter(function (i) {
      return i.category === category && (category !== "speakers" || isSpeakerEligibleForRole(i, activeModalSpeakerRole));
    });
    var currentItemId = activeSlot ? activeSlot.itemId : null;

    var modalHtml = `
      <div class="picker-backdrop" data-action="close-modal">
        <div class="picker-dialog" role="dialog" aria-modal="true" aria-labelledby="picker-modal-title">
          <div class="picker-header">
            <div>
              <span class="picker-eyebrow">${catMeta ? catMeta.icon : ''} Component Selector</span>
              <h3 id="picker-modal-title">Select ${category === "speakers" ? (activeModalSpeakerRole === "audience_pa" ? "Crowd-Facing PA" : "DJ Booth Monitors") : (catMeta ? catMeta.name : "Component")}</h3>
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
    activeModalSpeakerRole = null;
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

  // Price each preset from its actual catalog slots. Static marketing badges
  // previously understated complete shopping totals by hundreds of dollars.
  function presetPriceBadge(preset) {
    return "Est. $" + calculateCustomRigValuation(convertPresetToItems(preset)).toLocaleString("en-US") + " total";
  }

  function convertPresetToItems(preset) {
    var items = [];
    Object.keys(preset.slots).forEach(function (cat) {
      items.push({
        slotId: "p-" + cat,
        category: cat,
        itemId: preset.slots[cat],
        qty: 1,
        owned: preset.slots[cat] === "existing-mobile-device"
      });
    });
    return items;
  }

  function renderCompareGridContent(rigA, rigB) {
    var valA = calculateCustomRigValuation(rigA.items);
    var valB = calculateCustomRigValuation(rigB.items);
    var ownedA = calculateCustomRigValuation(rigA.items.filter(function (s) { return s.owned; }));
    var ownedB = calculateCustomRigValuation(rigB.items.filter(function (s) { return s.owned; }));

    return `
      <div class="compare-rig-card">
        <h4>${escapeHtml(rigA.name)}</h4>
        <div class="compare-price-tag">To buy: $${(valA - ownedA).toLocaleString()}</div>
        <div class="metric-sub">Full value: $${valA.toLocaleString()} · Already owned: $${ownedA.toLocaleString()}</div>
        <div class="compare-specs-table">
          ${CATALOG.categories.map(function (cat) {
            var summary = getCategorySummary(rigA.items, cat.id);
            return `<div class="compare-spec-row">
              <span class="spec-cat-label">${cat.name}:</span>
              <strong>${summary}</strong>
            </div>`;
          }).join("")}
        </div>
      </div>

      <div class="compare-rig-card">
        <h4>${escapeHtml(rigB.name)}</h4>
        <div class="compare-price-tag">To buy: $${(valB - ownedB).toLocaleString()}</div>
        <div class="metric-sub">Full value: $${valB.toLocaleString()} · Already owned: $${ownedB.toLocaleString()}</div>
        <div class="compare-specs-table">
          ${CATALOG.categories.map(function (cat) {
            var summary = getCategorySummary(rigB.items, cat.id);
            return `<div class="compare-spec-row">
              <span class="spec-cat-label">${cat.name}:</span>
              <strong>${summary}</strong>
            </div>`;
          }).join("")}
        </div>
      </div>
    `;
  }

  // Compare every selected device, quantity and ownership flag. Showing only
  // the first device per category and a single-unit price misleads buyers.
  function getCategorySummary(items, category) {
    var selected = items.filter(function (slot) { return slot.category === category; });
    if (!selected.length) return "None";
    return selected.map(function (slot) {
      var item = getItem(slot.itemId);
      if (!item) return "";
      var qty = slot.qty || 1;
      return escapeHtml(item.brand + " " + item.model) +
        " (×" + qty + ", " + (slot.owned ? "Owned" : "Buy") +
        ", $" + (item.price * qty).toLocaleString("en-US") + ")";
    }).filter(Boolean).join("<br>");
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
          var pickedItem = getItem(itemId);
          if (!pickedItem || pickedItem.category !== activeModalCategory ||
              (activeModalCategory === "speakers" && !isSpeakerEligibleForRole(pickedItem, activeModalSpeakerRole))) return;
          var targetSlot = currentRig.items.find(function (s) { return s.slotId === activeModalSlotId; });
          if (targetSlot) {
            if (!replaceSlotItem(targetSlot, itemId)) return;
          } else {
            currentRig.items.push({
              slotId: activeModalSlotId,
              category: activeModalCategory,
              role: activeModalCategory === "speakers" ? activeModalSpeakerRole : undefined,
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
      } else if (action === "set-listening-context") {
        var nextContext = btn.getAttribute("data-context");
        if (nextContext !== "studio" && nextContext !== "audience") return;
        currentRig.context = nextContext;
        saveActiveState();
        renderApp();
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
        if (slotId && category) openPickerModal(slotId, category, btn.getAttribute("data-speaker-role"));
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
        var cableItem = getItem(cableId);
        if (cableItem && cableItem.category === "cables") {
          // The connection suggestion is additive, not a request to replace
          // another cable the visitor may already own or need elsewhere.
          // Preserve every existing cable's quantity and ownership.
          var alreadySelected = currentRig.items.some(function (s) { return s.itemId === cableId; });
          if (!alreadySelected) {
            var newSlotId = "auto-cable-" + Date.now();
            var suffix = 0;
            while (currentRig.items.some(function (s) { return s.slotId === newSlotId; })) {
              newSlotId = "auto-cable-" + Date.now() + "-" + (++suffix);
            }
            currentRig.items.push({
              slotId: newSlotId,
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
          if (fixItem && (fixItem.category !== "speakers" || speakerRoleForItem(fixItem))) {
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
        openPickerModal(newSlotId, addCat, btn.getAttribute("data-speaker-role"));
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
    currentRig.context = preset.context === "audience" ? "audience" : "studio";
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
      "  Listening context: " + (currentRig.context === "audience" ? "party / live audience" : "desk / studio"),
      "=========================================",
      ""
    ];

    currentRig.items.forEach(function (slot) {
      var item = getSlotItem(slot);
      if (item) {
        var qty = slot.qty || 1;
        var statusStr = item.no_purchase === true ? "[EXISTING DEVICE / MODE — VERIFY]" : slot.owned ? "[ALREADY OWNED]" : "[NEED TO BUY]";
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
          name: clean.name, context: clean.context, items: clean.items,
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
      context: currentRig.context,
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
