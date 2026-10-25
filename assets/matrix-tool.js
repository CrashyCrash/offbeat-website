/* Offbeat — Interactive Controller & Software Compatibility Matrix
 *
 * Provides live instant filtering, search, and a "Will It Work?" compatibility checker.
 * Covers 20+ major DJ controllers and standalone systems across rekordbox, Serato,
 * Traktor, djay Pro, VirtualDJ, and Engine DJ.
 */
(function () {
  "use strict";

  var CONTROLLERS = [
    {
      id: "flx4",
      name: "Pioneer DDJ-FLX4",
      brand: "Pioneer / AlphaTheta",
      price: "$280–350",
      tier: "mid",
      channels: "2-channel",
      format: "controller",
      primary: "rekordbox & Serato DJ Lite",
      rekordbox: "unlock", // unlock | paid | bundle | mapped | none
      serato: "lite", // pro-unlock | lite | paid | none
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "Beatport", "Beatsource", "SoundCloud"],
      mobile: "iOS, iPadOS, Android, macOS, Windows",
      stems: "Smart Fader & Serato/rekordbox pad stems",
      outputs: "RCA Master, USB-C Audio",
      mic: "1/4-inch with direct USB routing",
      buyer: "Best first serious controller for all beginners.",
      caveat: "2 channels only; Serato DJ Pro requires paid upgrade or subscription.",
      guide: "pioneer-ddj-flx4-review.html"
    },
    {
      id: "flx2",
      name: "Pioneer DDJ-FLX2",
      brand: "Pioneer / AlphaTheta",
      price: "$150–200",
      tier: "budget",
      channels: "2-channel",
      format: "controller",
      primary: "rekordbox & djay",
      rekordbox: "unlock",
      serato: "lite",
      traktor: "none",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Apple Music (djay)", "Tidal", "Beatport", "SoundCloud"],
      mobile: "iOS, iPadOS, Android, macOS, Windows",
      stems: "Basic software stems via performance pads",
      outputs: "3.5mm mini-jack Master",
      mic: "None",
      buyer: "Casual starters, mobile/tablet DJs, party hobbyists.",
      caveat: "No mic input, mini-jack outputs only; not suitable for club booths.",
      guide: "best-dj-controllers-under-200.html"
    },
    {
      id: "flx6gt",
      name: "Pioneer DDJ-FLX6-GT",
      brand: "Pioneer / AlphaTheta",
      price: "$550–650",
      tier: "mid",
      channels: "4-channel",
      format: "controller",
      primary: "rekordbox & Serato DJ Pro",
      rekordbox: "unlock",
      serato: "pro-unlock",
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "Beatport", "Beatsource", "SoundCloud"],
      mobile: "macOS, Windows",
      stems: "Merge FX & Jog Cutter stem mixing",
      outputs: "RCA Master, RCA Booth",
      mic: "1/4-inch TS",
      buyer: "Beginners ready for 4 decks without paying club prices.",
      caveat: "RCA outputs only (no balanced XLR); plasticky build for $600.",
      guide: "pioneer-ddj-flx4-vs-flx6.html"
    },
    {
      id: "flx10",
      name: "Pioneer DDJ-FLX10",
      brand: "Pioneer / AlphaTheta",
      price: "$1,600–1,750",
      tier: "pro",
      channels: "4-channel",
      format: "controller",
      primary: "rekordbox & Serato DJ Pro",
      rekordbox: "unlock",
      serato: "pro-unlock",
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "Beatport", "Beatsource", "SoundCloud"],
      mobile: "macOS, Windows (Dual USB-C)",
      stems: "Dedicated Track Separation hardware buttons (Vocal/Drum/Inst)",
      outputs: "XLR & RCA Master, 1/4-inch TRS Booth, DMX lighting out",
      mic: "XLR/TRS combo + 1/4-inch TS (2 mic inputs)",
      buyer: "Working pros, club residents, stem-focused performance DJs.",
      caveat: "High investment; requires a capable modern computer for real-time stems.",
      guide: "best-dj-controllers-under-1000.html"
    },
    {
      id: "inpulse500",
      name: "Hercules DJControl Inpulse 500",
      brand: "Hercules",
      price: "$280–350",
      tier: "mid",
      channels: "2-channel",
      format: "controller",
      primary: "Serato DJ Lite & DJUCED",
      rekordbox: "none",
      serato: "lite",
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "Beatport", "Beatsource", "SoundCloud"],
      mobile: "macOS, Windows",
      stems: "Software stem buttons via Serato",
      outputs: "1/4-inch TRS balanced & RCA Master",
      mic: "1/4-inch with hardware tone EQ",
      buyer: "Budget-conscious DJs wanting balanced outputs and rugged metal chassis.",
      caveat: "No rekordbox support; Serato DJ Pro requires paid license.",
      guide: "best-dj-controllers-under-500-2026.html"
    },
    {
      id: "mixtrackpro",
      name: "Numark Mixtrack Pro FX",
      brand: "Numark",
      price: "$190–250",
      tier: "budget",
      channels: "2-channel",
      format: "controller",
      primary: "Serato DJ Lite",
      rekordbox: "none",
      serato: "lite",
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "SoundCloud", "Beatport"],
      mobile: "macOS, Windows",
      stems: "Serato stem mapping via pads",
      outputs: "RCA Master",
      mic: "1/4-inch TS input",
      buyer: "Scratch beginners wanting long 100mm pitch faders and paddle FX.",
      caveat: "No dedicated gain knobs on channels; RCA outputs only.",
      guide: "best-dj-controllers-under-200.html"
    },
    {
      id: "traktors3",
      name: "Traktor Kontrol S3",
      brand: "Native Instruments",
      price: "$400–550",
      tier: "mid",
      channels: "4-channel",
      format: "controller",
      primary: "Traktor Pro 4",
      rekordbox: "none",
      serato: "none",
      traktor: "unlock",
      djay: "mapped",
      virtualdj: "native",
      engine: "none",
      streaming: ["Beatport", "Beatsource"],
      mobile: "iPad (Traktor DJ 2), macOS, Windows",
      stems: "Traktor Pro 4 Pattern Player and Stems",
      outputs: "XLR & RCA Master, 1/4-inch Booth",
      mic: "XLR/TRS combo input",
      buyer: "Electronic music producers, techno/house DJs committed to Traktor.",
      caveat: "Not recommended for Serato or rekordbox users.",
      guide: "best-dj-controllers-2026.html"
    },
    {
      id: "traktors4",
      name: "Traktor Kontrol S4 MK3",
      brand: "Native Instruments",
      price: "$650–800",
      tier: "pro",
      channels: "4-channel",
      format: "controller",
      primary: "Traktor Pro 4",
      rekordbox: "none",
      serato: "none",
      traktor: "unlock",
      djay: "mapped",
      virtualdj: "native",
      engine: "none",
      streaming: ["Beatport", "Beatsource"],
      mobile: "macOS, Windows",
      stems: "Haptic Drive motorized wheels, high-res color displays, stem faders",
      outputs: "XLR & RCA Master, 1/4-inch Booth, Dual headphone outs",
      mic: "Combo XLR/TRS + 1/4-inch",
      buyer: "Tactile, performance-heavy electronic DJs wanting motorized feel.",
      caveat: "Tied deeply to Traktor ecosystem.",
      guide: "best-dj-controllers-under-1000.html"
    },
    {
      id: "raneone",
      name: "Rane ONE",
      brand: "Rane",
      price: "$800–900",
      tier: "pro",
      channels: "2-channel",
      format: "motorized",
      primary: "Serato DJ Pro",
      rekordbox: "none",
      serato: "pro-unlock",
      traktor: "mapped",
      djay: "native",
      virtualdj: "native",
      engine: "none",
      streaming: ["Tidal", "Beatport", "Beatsource", "SoundCloud"],
      mobile: "macOS, Windows (Dual USB)",
      stems: "Serato real-time stem split buttons",
      outputs: "Dual XLR Master, Dual XLR Booth",
      mic: "Dual XLR/TRS combo inputs",
      buyer: "Scratch, battle, hip-hop and open-format DJs who need real vinyl torque.",
      caveat: "Heavy (24 lbs); 2 channels only.",
      guide: "best-dj-controllers-2026.html"
    },
    {
      id: "primego",
      name: "Denon DJ Prime Go",
      brand: "Denon DJ",
      price: "$950–1,100",
      tier: "pro",
      channels: "2-channel",
      format: "standalone",
      primary: "Engine DJ Standalone OS",
      rekordbox: "mapped",
      serato: "paid",
      traktor: "none",
      djay: "none",
      virtualdj: "native",
      engine: "unlock",
      streaming: ["Tidal", "Beatport", "Beatsource", "Amazon Music"],
      mobile: "Standalone (Built-in 4h rechargeable battery & Wi-Fi)",
      stems: "Engine DJ OS track analysis",
      outputs: "XLR Master, 1/4-inch Booth, RCA Aux",
      mic: "Dual 1/4-inch TS inputs",
      buyer: "Mobile DJs, beach/outdoor parties, travelling bedroom producers.",
      caveat: "Small jog wheels; vertical pitch faders.",
      guide: "denon-prime-go-review.html"
    },
    {
      id: "xdjaz",
      name: "AlphaTheta XDJ-AZ",
      brand: "AlphaTheta / Pioneer",
      price: "$2,600–2,800",
      tier: "flagship",
      channels: "4-channel",
      format: "standalone",
      primary: "rekordbox Standalone & Serato DJ Pro",
      rekordbox: "unlock",
      serato: "pro-unlock",
      traktor: "none",
      djay: "none",
      virtualdj: "none",
      engine: "none",
      streaming: ["Beatport Streaming, CloudDirectPlay"],
      mobile: "Standalone USB media + Wi-Fi Cloud Direct",
      stems: "CDJ-3000 style touch cues & stems",
      outputs: "XLR & RCA Master, 1/4-inch Booth, Zone out",
      mic: "Dual XLR/TRS combo inputs",
      buyer: "Club venues, festival touring DJs, premium home installations.",
      caveat: "Flagship pricing and large physical footprint.",
      guide: "best-standalone-dj-systems.html"
    },
    {
      id: "prime4plus",
      name: "Denon DJ Prime 4+",
      brand: "Denon DJ",
      price: "$2,200–2,400",
      tier: "flagship",
      channels: "4-channel",
      format: "standalone",
      primary: "Engine DJ Standalone OS",
      rekordbox: "none",
      serato: "pro-unlock",
      traktor: "none",
      djay: "none",
      virtualdj: "native",
      engine: "unlock",
      streaming: ["Amazon Music Unlimited, Tidal, Beatport, Beatsource"],
      mobile: "Standalone 10.1-inch HD Touchscreen & Wi-Fi",
      stems: "First standalone real-time stem extraction hardware",
      outputs: "XLR & RCA Master, XLR Booth, XLR Zone out",
      mic: "Dual XLR/TRS inputs with independent EQ/Echo",
      buyer: "High-end mobile DJs, multi-room event specialists.",
      caveat: "Engine DJ ecosystem differs from club-standard CDJs.",
      guide: "xdj-az-vs-denon-prime-4-plus.html"
    },
    {
      id: "reloopmixon8",
      name: "Reloop Mixon 8 Pro",
      brand: "Reloop",
      price: "$650–850",
      tier: "mid",
      channels: "4-channel",
      format: "controller",
      primary: "Algoriddim djay Pro & Serato DJ Pro",
      rekordbox: "none",
      serato: "pro-unlock",
      traktor: "mapped",
      djay: "unlock",
      virtualdj: "native",
      engine: "none",
      streaming: ["Apple Music (via djay), Tidal, Beatport, SoundCloud"],
      mobile: "iPad Pro docking station (USB-C), macOS, Windows",
      stems: "Hardware Neural Mix and Serato Stem buttons",
      outputs: "XLR & RCA Master, 1/4-inch Booth",
      mic: "XLR/TRS + 1/4-inch TS inputs",
      buyer: "iPad/tablet performers and cross-platform creative DJs.",
      caveat: "No rekordbox support.",
      guide: "best-dj-controllers-2026.html"
    }
  ];

  var root = document.getElementById("matrix-root");
  if (!root) return;

  var state = {
    search: "",
    software: "all",
    channels: "all",
    tier: "all"
  };

  function renderStatusBadge(status) {
    if (status === "unlock" || status === "pro-unlock") {
      return '<span class="mat-badge mat-badge--unlock" title="Full native hardware unlock included">✓ Native Unlock</span>';
    } else if (status === "lite") {
      return '<span class="mat-badge mat-badge--lite" title="Lite edition included, Pro is a paid upgrade">⚡ Lite Included</span>';
    } else if (status === "native") {
      return '<span class="mat-badge mat-badge--native" title="Plug-and-play supported">✓ Supported</span>';
    } else if (status === "mapped") {
      return '<span class="mat-badge mat-badge--mapped" title="Requires MIDI mapping file">⚙ MIDI Mapped</span>';
    } else if (status === "paid") {
      return '<span class="mat-badge mat-badge--paid" title="Supported with paid software license">$$ Paid Upgrade</span>';
    }
    return '<span class="mat-badge mat-badge--none">✕ No</span>';
  }

  function filterControllers() {
    return CONTROLLERS.filter(function (item) {
      if (state.search) {
        var q = state.search.toLowerCase();
        var match = item.name.toLowerCase().indexOf(q) !== -1 ||
          item.brand.toLowerCase().indexOf(q) !== -1 ||
          item.buyer.toLowerCase().indexOf(q) !== -1 ||
          item.streaming.join(" ").toLowerCase().indexOf(q) !== -1 ||
          item.stems.toLowerCase().indexOf(q) !== -1;
        if (!match) return false;
      }
      if (state.software !== "all") {
        var s = state.software;
        if (s === "rekordbox" && (item.rekordbox === "none" || !item.rekordbox)) return false;
        if (s === "serato" && (item.serato === "none" || !item.serato)) return false;
        if (s === "traktor" && (item.traktor === "none" || !item.traktor)) return false;
        if (s === "djay" && (item.djay === "none" || !item.djay)) return false;
        if (s === "standalone" && item.format !== "standalone") return false;
      }
      if (state.channels !== "all") {
        if (state.channels === "2" && item.channels !== "2-channel") return false;
        if (state.channels === "4" && item.channels !== "4-channel") return false;
      }
      if (state.tier !== "all") {
        if (state.tier !== item.tier) return false;
      }
      return true;
    });
  }

  function render() {
    var list = filterControllers();
    var html = "";

    html += '<div class="matrix-toolbar">';
    html += '<div class="matrix-search"><input type="search" placeholder="Search controller name, stems, outputs, or Apple Music…" data-mat-search value="' + esc(state.search) + '" aria-label="Search compatibility matrix"></div>';
    html += '<div class="matrix-filters">';
    html += '<select data-mat-soft aria-label="Filter by software"><option value="all"' + (state.software === "all" ? " selected" : "") + '>All Software Ecosystems</option><option value="rekordbox"' + (state.software === "rekordbox" ? " selected" : "") + '>rekordbox</option><option value="serato"' + (state.software === "serato" ? " selected" : "") + '>Serato DJ</option><option value="traktor"' + (state.software === "traktor" ? " selected" : "") + '>Traktor Pro</option><option value="djay"' + (state.software === "djay" ? " selected" : "") + '>djay Pro</option><option value="standalone"' + (state.software === "standalone" ? " selected" : "") + '>Standalone (No Laptop)</option></select>';
    html += '<select data-mat-chan aria-label="Filter by channels"><option value="all"' + (state.channels === "all" ? " selected" : "") + '>All Channel Layouts</option><option value="2"' + (state.channels === "2" ? " selected" : "") + '>2-Channel Decks</option><option value="4"' + (state.channels === "4" ? " selected" : "") + '>4-Channel Decks</option></select>';
    html += '<select data-mat-tier aria-label="Filter by budget tier"><option value="all"' + (state.tier === "all" ? " selected" : "") + '>All Budget Tiers</option><option value="budget"' + (state.tier === "budget" ? " selected" : "") + '>Under $300 (Budget)</option><option value="mid"' + (state.tier === "mid" ? " selected" : "") + '>$300–$700 (Sweet Spot)</option><option value="pro"' + (state.tier === "pro" ? " selected" : "") + '>$700–$1,800 (Pro)</option><option value="flagship"' + (state.tier === "flagship" ? " selected" : "") + '>$2,000+ (Flagship)</option></select>';
    html += '</div>';
    html += '</div>';

    html += '<p class="matrix-count">Showing <strong>' + list.length + '</strong> compatible hardware options</p>';

    if (!list.length) {
      html += '<div class="matrix-empty"><p>No controllers match those filters. Try clearing filters or searching for "FLX4" or "Serato".</p><button type="button" class="btn btn-secondary" data-mat-reset>Reset all filters</button></div>';
    } else {
      html += '<div class="matrix-cards">';
      list.forEach(function (c) {
        html += '<div class="matrix-card" id="mat-' + c.id + '">';
        html += '<div class="mat-head">';
        html += '<div><span class="mat-brand">' + esc(c.brand) + ' · ' + esc(c.channels) + '</span>';
        html += '<h3 class="mat-title">' + esc(c.name) + '</h3></div>';
        html += '<span class="mat-price">' + esc(c.price) + '</span>';
        html += '</div>';

        html += '<div class="mat-software-grid">';
        html += '<div class="mat-soft-cell"><span>rekordbox</span>' + renderStatusBadge(c.rekordbox) + '</div>';
        html += '<div class="mat-soft-cell"><span>Serato DJ</span>' + renderStatusBadge(c.serato) + '</div>';
        html += '<div class="mat-soft-cell"><span>Traktor Pro</span>' + renderStatusBadge(c.traktor) + '</div>';
        html += '<div class="mat-soft-cell"><span>djay Pro</span>' + renderStatusBadge(c.djay) + '</div>';
        html += '</div>';

        html += '<div class="mat-specs">';
        html += '<p><strong>Stems:</strong> ' + esc(c.stems) + '</p>';
        html += '<p><strong>Outputs:</strong> ' + esc(c.outputs) + '</p>';
        html += '<p><strong>Streaming:</strong> ' + esc(c.streaming.join(", ")) + '</p>';
        html += '</div>';

        html += '<div class="mat-verdict">';
        html += '<p class="mat-buyer"><strong>Best For:</strong> ' + esc(c.buyer) + '</p>';
        html += '<p class="mat-caveat"><strong>Caveat:</strong> ' + esc(c.caveat) + '</p>';
        html += '</div>';

        var catalogMap = {
          "flx4": "pioneer-ddj-flx4",
          "flx2": "pioneer-ddj-flx2",
          "flx10": "pioneer-ddj-flx10",
          "grv6": "alphatheta-ddj-grv6",
          "s2mk3": "traktor-kontrol-s2-mk3",
          "prime4plus": "denon-prime-4-plus",
          "primego": "denon-prime-go",
          "inpulse500": "hercules-inpulse-500",
          "ranefour": "rane-four"
        };
        var targetCatId = catalogMap[c.id] || "pioneer-ddj-flx4";

        html += '<div class="mat-actions-row">';
        if (c.guide) {
          html += '<a class="mat-link" href="' + esc(c.guide) + '">Read Guide →</a>';
        }
        html += '<a class="mat-plan-btn" href="build-your-dj-setup.html?add=' + targetCatId + '">Plan in Rig Architect 🎛️</a>';
        html += '</div>';

        html += '</div>';
      });
      html += '</div>';
    }

    root.innerHTML = html;

    // Attach listeners
    var searchInput = root.querySelector("[data-mat-search]");
    if (searchInput) {
      searchInput.addEventListener("input", function () {
        state.search = searchInput.value;
        render();
        var reInput = root.querySelector("[data-mat-search]");
        if (reInput) { reInput.focus(); reInput.setSelectionRange(reInput.value.length, reInput.value.length); }
      });
    }

    var softSel = root.querySelector("[data-mat-soft]");
    if (softSel) {
      softSel.addEventListener("change", function () {
        state.software = softSel.value;
        render();
      });
    }

    var chanSel = root.querySelector("[data-mat-chan]");
    if (chanSel) {
      chanSel.addEventListener("change", function () {
        state.channels = chanSel.value;
        render();
      });
    }

    var tierSel = root.querySelector("[data-mat-tier]");
    if (tierSel) {
      tierSel.addEventListener("change", function () {
        state.tier = tierSel.value;
        render();
      });
    }

    var resetBtn = root.querySelector("[data-mat-reset]");
    if (resetBtn) {
      resetBtn.addEventListener("click", function () {
        state = { search: "", software: "all", channels: "all", tier: "all" };
        render();
      });
    }
  }

  function esc(str) {
    return String(str || "").replace(/[&<>"]/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[m];
    });
  }

  render();
})();
