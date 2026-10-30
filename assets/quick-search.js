/* =============================================================================
   Offbeat Inc. — Sitewide Spotlight Search (Cmd + K / Quick Search)
   Instant navigation across all 118 guides, 29 hardware models & interactive tools
   ========================================================================== */

(function () {
  "use strict";

  var searchIndex = null;
  var selectedIndex = -1;
  var activeCategoryFilter = "all";
  var currentFilteredResults = [];

  function initQuickSearch() {
    injectSearchModalHtml();
    setupKeyListeners();
  }

  function getBasePath() {
    var path = window.location.pathname;
    var idx = path.lastIndexOf("/");
    return idx >= 0 ? path.substring(0, idx + 1) : "./";
  }

  function loadSearchIndex() {
    if (searchIndex) return Promise.resolve(searchIndex);
    return fetch("assets/search-index.json")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        searchIndex = data;
        return searchIndex;
      })
      .catch(function (err) {
        console.warn("Could not load search index:", err);
        return [];
      });
  }

  function injectSearchModalHtml() {
    if (document.getElementById("quick-search-backdrop")) return;

    var backdrop = document.createElement("div");
    backdrop.id = "quick-search-backdrop";
    backdrop.className = "quick-search-backdrop";
    backdrop.hidden = true;
    backdrop.innerHTML = `
      <div class="quick-search-dialog" role="dialog" aria-modal="true" aria-label="Quick Search">
        <div class="qs-input-row">
          <span class="qs-search-icon">🔍</span>
          <input type="search" id="quick-search-input" class="qs-input" placeholder="Search guides, DJ gear, software, tools, or Camelot keys..." autocomplete="off" spellcheck="false">
          <button type="button" id="qs-close-btn" class="qs-kbd-hint" aria-label="Close search">Close ×</button>
        </div>
        <div class="qs-filter-pills" id="qs-filter-bar">
          <button type="button" class="qs-pill is-active" data-qs-filter="all" aria-pressed="true">All</button>
          <button type="button" class="qs-pill" data-qs-filter="controllers" aria-pressed="false">Controllers</button>
          <button type="button" class="qs-pill" data-qs-filter="gear" aria-pressed="false">Gear</button>
          <button type="button" class="qs-pill" data-qs-filter="software" aria-pressed="false">Software</button>
          <button type="button" class="qs-pill" data-qs-filter="tools" aria-pressed="false">Tools</button>
          <button type="button" class="qs-pill" data-qs-filter="guides" aria-pressed="false">Guides &amp; skills</button>
        </div>
        <div class="qs-results-container" id="qs-results-list" role="listbox">
          <div class="qs-placeholder-state">
            <p>Type to search 118+ guides, 29 hardware models, and interactive tools.</p>
            <div class="qs-quick-links">
              <span>Popular shortcuts:</span>
              <a href="build-your-dj-setup.html" class="qs-quick-chip">🎛️ My DJ Rig Architect</a>
              <a href="beatmatch-trainer.html" class="qs-quick-chip">🎧 Beatmatch Trainer</a>
              <a href="dj-skills-learning-path.html" class="qs-quick-chip">🎡 Harmonic Wheel</a>
              <a href="pioneer-ddj-flx4-review.html" class="qs-quick-chip">DDJ-FLX4 Review</a>
              <a href="distrokid-vs-tunecore.html" class="qs-quick-chip">DistroKid vs TuneCore</a>
            </div>
          </div>
        </div>
        <div class="qs-footer">
          <span><kbd>↑</kbd> <kbd>↓</kbd> to navigate</span>
          <span><kbd>↵</kbd> to select</span>
          <span><kbd>esc</kbd> to dismiss</span>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    var input = document.getElementById("quick-search-input");
    input.addEventListener("input", function () {
      renderResults(input.value.trim(), activeCategoryFilter);
    });

    backdrop.addEventListener("click", function (e) {
      if (e.target === backdrop) closeQuickSearch();
    });
    document.getElementById("qs-close-btn").addEventListener("click", closeQuickSearch);

    var filterBar = document.getElementById("qs-filter-bar");
    filterBar.addEventListener("click", function (e) {
      var pill = e.target.closest("[data-qs-filter]");
      if (!pill) return;
      filterBar.querySelectorAll(".qs-pill").forEach(function (p) {
        var active = p === pill;
        p.classList.toggle("is-active", active);
        p.setAttribute("aria-pressed", active ? "true" : "false");
      });
      activeCategoryFilter = pill.getAttribute("data-qs-filter");
      renderResults(input.value.trim(), activeCategoryFilter);
    });
  }

  function openQuickSearch() {
    var backdrop = document.getElementById("quick-search-backdrop");
    if (!backdrop) return;
    loadSearchIndex().then(function () {
      backdrop.hidden = false;
      activeCategoryFilter = "all";
      backdrop.querySelectorAll(".qs-pill").forEach(function (p) {
        var active = p.getAttribute("data-qs-filter") === "all";
        p.classList.toggle("is-active", active);
        p.setAttribute("aria-pressed", active ? "true" : "false");
      });
      document.body.classList.add("modal-open");
      var input = document.getElementById("quick-search-input");
      if (input) {
        input.value = "";
        input.focus();
        renderResults("", "all");
      }
    });
  }

  function closeQuickSearch() {
    var backdrop = document.getElementById("quick-search-backdrop");
    if (!backdrop) return;
    backdrop.hidden = true;
    document.body.classList.remove("modal-open");
    selectedIndex = -1;
  }

  function renderResults(query, categoryFilter) {
    var resultsList = document.getElementById("qs-results-list");
    if (!resultsList || !searchIndex) return;

    if (!query && categoryFilter === "all") {
      resultsList.innerHTML = `
        <div class="qs-placeholder-state">
          <p>Type to search 118+ guides, 29 hardware models, and interactive tools.</p>
          <div class="qs-quick-links">
            <span>Popular shortcuts:</span>
            <a href="build-your-dj-setup.html" class="qs-quick-chip">🎛️ My DJ Rig Architect</a>
            <a href="beatmatch-trainer.html" class="qs-quick-chip">🎧 Beatmatch Trainer</a>
            <a href="dj-skills-learning-path.html" class="qs-quick-chip">🎡 Harmonic Wheel</a>
            <a href="pioneer-ddj-flx4-review.html" class="qs-quick-chip">DDJ-FLX4 Review</a>
            <a href="distrokid-vs-tunecore.html" class="qs-quick-chip">DistroKid vs TuneCore</a>
          </div>
        </div>
      `;
      currentFilteredResults = [];
      selectedIndex = -1;
      return;
    }

    var tokens = query ? query.toLowerCase().split(/\s+/) : [];

    var filtered = searchIndex.filter(function (item) {
      // The index groups are tools/controllers/gear/guides/software.
      // Display categories (e.g. "Controllers", "Headphones") are not filters.
      if (categoryFilter !== "all" && item.g !== categoryFilter) {
        return false;
      }
      if (tokens.length === 0) return true;
      var text = (item.title + " " + item.desc + " " + item.category + " " + (item.k || "")).toLowerCase();
      return tokens.every(function (t) { return text.indexOf(t) !== -1; });
    });

    currentFilteredResults = filtered.slice(0, 12);
    selectedIndex = currentFilteredResults.length > 0 ? 0 : -1;

    if (currentFilteredResults.length === 0) {
      resultsList.innerHTML = `
        <div class="qs-empty-state">
          <p>No results found for "<strong>${escapeHtml(query)}</strong>"</p>
          <span>Try searching for controllers (FLX4, FLX10), headphones (HD 25), software (rekordbox, Serato), or tools.</span>
        </div>
      `;
      return;
    }

    resultsList.innerHTML = currentFilteredResults.map(function (item, idx) {
      var isSelected = idx === selectedIndex;
      var catClass = "qs-badge--" + item.category.toLowerCase().replace(/[^a-z0-9]/g, "-");
      return `
        <a href="${item.url}" class="qs-result-item ${isSelected ? 'is-selected' : ''}" data-qs-idx="${idx}" role="option" aria-selected="${isSelected}">
          <div class="qs-item-head">
            <span class="qs-item-title">${escapeHtml(item.title)}</span>
            <span class="qs-cat-badge ${catClass}">${escapeHtml(item.category)}</span>
          </div>
          ${item.desc ? `<p class="qs-item-desc">${escapeHtml(item.desc)}</p>` : ''}
        </a>
      `;
    }).join("");
  }

  function updateSelectionVisual() {
    var items = document.querySelectorAll(".qs-result-item");
    items.forEach(function (el, idx) {
      if (idx === selectedIndex) {
        el.classList.add("is-selected");
        el.setAttribute("aria-selected", "true");
        el.scrollIntoView({ block: "nearest" });
      } else {
        el.classList.remove("is-selected");
        el.setAttribute("aria-selected", "false");
      }
    });
  }

  function setupKeyListeners() {
    document.addEventListener("keydown", function (e) {
      // Cmd + K or Ctrl + K
      if ((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        var backdrop = document.getElementById("quick-search-backdrop");
        if (backdrop && !backdrop.hidden) {
          closeQuickSearch();
        } else {
          openQuickSearch();
        }
        return;
      }

      // / key when not focused in input
      if (e.key === "/" && !e.target.matches("input, textarea, select, [contenteditable]")) {
        e.preventDefault();
        openQuickSearch();
        return;
      }

      var backdrop = document.getElementById("quick-search-backdrop");
      if (!backdrop || backdrop.hidden) return;

      if (e.key === "Escape") {
        e.preventDefault();
        closeQuickSearch();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        if (currentFilteredResults.length > 0) {
          selectedIndex = (selectedIndex + 1) % currentFilteredResults.length;
          updateSelectionVisual();
        }
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (currentFilteredResults.length > 0) {
          selectedIndex = (selectedIndex - 1 + currentFilteredResults.length) % currentFilteredResults.length;
          updateSelectionVisual();
        }
      } else if (e.key === "Enter") {
        // Native Enter activation must win on filter pills, Close and links.
        // Only Enter in the query input should follow the highlighted result.
        // Previously the document listener hijacked Enter on Close/filters
        // and unexpectedly navigated away from the visitor's current page.
        if (e.target !== document.getElementById("quick-search-input")) return;
        if (selectedIndex >= 0 && currentFilteredResults[selectedIndex]) {
          e.preventDefault();
          window.location.href = currentFilteredResults[selectedIndex].url;
        }
      }
    });

    document.addEventListener("click", function (e) {
      var trigger = e.target.closest("[data-action='open-quick-search']") ||
                    e.target.closest(".nav-search-btn") ||
                    e.target.closest("[data-search-open]") ||
                    e.target.closest(".nav-search");
      if (trigger) {
        e.preventDefault();
        openQuickSearch();
      }
    });
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initQuickSearch);
  } else {
    initQuickSearch();
  }
})();
