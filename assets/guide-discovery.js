/* Offbeat Inc. — Guide discovery for all-dj-guides.html
 *
 * Dependency-free catalog search and topic filtering.
 * - Word-based matching: all query words must appear, in any order.
 * - Case- and diacritic-insensitive ("Rekordbox" == "rekordbox",
 *   "Café" style accents ignored).
 * - Model-number tolerant: "flx4" matches "FLX-4" (punctuation such as
 *   dashes, dots, and spaces is ignored during comparison).
 * - Topic chips filter the guide sections; result count is announced to
 *   screen readers via aria-live; an empty state offers practical
 *   suggestions and a reset.
 * - Search and topic are read from and written to the URL (?q=...&topic=...)
 *   so results can be shared and restored after visiting a guide.
 * - No JavaScript: every guide stays visible as a normal link.
 *
 * Defensive: if any expected element is missing this file does nothing.
 */
(function () {
  "use strict";

  if (typeof window === "undefined" || typeof document === "undefined") return;

  var toolbar = document.getElementById("catalog");
  var queryInput = document.getElementById("guide-query");
  if (!toolbar || !queryInput) return;

  var form = toolbar.querySelector("form");
  var chips = Array.prototype.slice.call(toolbar.querySelectorAll(".chip[data-topic]"));
  var topicSelect = document.getElementById("guide-topic");
  var countEl = toolbar.querySelector(".discovery-count");
  var emptyEl = toolbar.querySelector(".discovery-empty");
  var emptyMsg = emptyEl ? emptyEl.querySelector("[data-empty-message]") : null;
  var resetButtons = Array.prototype.slice.call(toolbar.querySelectorAll("[data-action='reset-all']"));

  var TOPICS = ["all", "start", "controllers", "software", "gear", "skills", "producer", "music", "site"];

  /* ---------- helpers ---------- */

  function normalize(str) {
    var s = String(str).toLowerCase();
    if (typeof s.normalize === "function") {
      s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // strip diacritics
    }
    return s.replace(/\s+/g, " ").trim();
  }

  function buildHaystack(raw) {
    var norm = normalize(raw);
    return {
      norm: norm,
      model: norm.replace(/[^a-z0-9]/g, "") // "flx-4" -> "flx4"
    };
  }

  function matchesQuery(query, guide) {
    var tokens = normalize(query).split(" ").filter(function (t) { return t.length > 0; });
    if (tokens.length === 0) return true;
    var hay = guide.text;
    for (var i = 0; i < tokens.length; i++) {
      var t = normalize(tokens[i]);
      if (t.length === 0) continue;
      var tModel = t.replace(/[^a-z0-9]/g, "");
      if (hay.norm.indexOf(t) !== -1) continue;
      if (tModel.length > 0 && hay.model.indexOf(tModel) !== -1) continue;
      return false;
    }
    return true;
  }

  /* ---------- catalog model ---------- */

  var sections = [];
  var allGuides = [];

  Array.prototype.forEach.call(document.querySelectorAll(".guide-section"), function (sec) {
    var topic = sec.getAttribute("data-topic") || "general";
    var label = sec.getAttribute("data-topic-label") || "";
    var section = { el: sec, topic: topic, label: label, guides: [] };

    Array.prototype.forEach.call(sec.querySelectorAll("a.card"), function (card) {
      var parts = [label, topic];
      var h3 = card.querySelector("h3");
      var p = card.querySelector("p");
      if (h3) parts.push(h3.textContent);
      if (p) parts.push(p.textContent);
      var href = card.getAttribute("href") || "";
      if (href) parts.push(href.replace(/\.html$/i, ""));

      var guide = {
        el: card,
        text: buildHaystack(parts.join("  |  ")),
        section: section
      };
      card.__guide = guide;
      section.guides.push(guide);
      allGuides.push(guide);
    });

    sections.push(section);
  });

  var TOTAL = allGuides.length;
  if (TOTAL === 0) return;

  /* ---------- state ---------- */

  var state = { q: "", topic: "all" };

  function topicLabel(topic) {
    for (var i = 0; i < sections.length; i++) {
      if (sections[i].topic === topic) return sections[i].label || topic;
    }
    return topic;
  }

  function readFromUrl() {
    var q = "";
    var topic = "all";
    try {
      var params = new URLSearchParams(window.location.search);
      q = (params.get("q") || "").trim().slice(0, 120);
      var t = (params.get("topic") || "").trim().toLowerCase();
      if (TOPICS.indexOf(t) !== -1) topic = t;
    } catch (err) { /* URL APIs unavailable: keep defaults */ }
    return { q: q, topic: topic };
  }

  function writeToUrl() {
    try {
      var url = new URL(window.location.href);
      url.searchParams.delete("q");
      url.searchParams.delete("topic");
      if (state.q) url.searchParams.set("q", state.q);
      if (state.topic !== "all") url.searchParams.set("topic", state.topic);
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    } catch (err) { /* file:// or old browser: state still works in memory */ }
  }

  /* ---------- rendering ---------- */

  function apply() {
    var q = normalize(state.q);
    toolbar.classList.toggle("has-query", !!q || state.topic !== "all");
    var visibleTotal = 0;

    sections.forEach(function (section) {
      var secVisible = 0;
      section.guides.forEach(function (guide) {
        var show = (state.topic === "all" || section.topic === state.topic) &&
                   matchesQuery(q, guide);
        guide.el.hidden = !show;
        if (show) secVisible++;
      });
      section.el.hidden = secVisible === 0;
      visibleTotal += secVisible;
    });

    if (topicSelect) topicSelect.value = state.topic;
    chips.forEach(function (chip) {
      chip.setAttribute("aria-pressed", String(chip.getAttribute("data-topic") === state.topic));
    });

    if (countEl) {
      countEl.textContent = (state.topic === "all" && !q)
        ? TOTAL + " pages in the catalog"
        : "Showing " + visibleTotal + " of " + TOTAL + " pages";
    }

    if (emptyMsg) {
      var parts = [];
      if (q) parts.push("“" + state.q + "”");
      if (state.topic !== "all") parts.push("the " + topicLabel(state.topic) + " topic");
      emptyMsg.textContent = parts.length
        ? "No guides match " + parts.join(" in ") + "."
        : "The catalog looks empty. If JavaScript is on, reset the filters below.";
    }
    if (emptyEl) emptyEl.hidden = visibleTotal > 0;

    writeToUrl();
  }

  /* ---------- events ---------- */

  var timer = null;
  function schedule() {
    if (typeof clearTimeout === "function") {
      clearTimeout(timer);
      timer = setTimeout(apply, 250);
    }
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault(); // live filtering instead of a page reload
      if (timer) { clearTimeout(timer); }
      state.q = queryInput.value.trim().slice(0, 120);
      apply();
      var firstResult = sections.find(function (section) { return !section.el.hidden; });
      if (firstResult) firstResult.el.scrollIntoView({ block: "start" });
    });
  }

  queryInput.addEventListener("input", function () {
    state.q = queryInput.value.trim().slice(0, 120);
    schedule();
  });

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      state.topic = chip.getAttribute("data-topic") || "all";
      apply();
    });
  });

  function resetAll() {
    state.q = "";
    state.topic = "all";
    queryInput.value = "";
    apply();
    if (typeof queryInput.focus === "function") queryInput.focus();
  }
  resetButtons.forEach(function (btn) {
    btn.addEventListener("click", resetAll);
  });

  if (topicSelect) topicSelect.addEventListener("change", function () {
    state.topic = topicSelect.value;
    apply();
  });
  window.addEventListener("pageshow", function () {
    var current = readFromUrl();
    state.q = current.q; state.topic = current.topic;
    queryInput.value = state.q; apply();
  });
  window.addEventListener("popstate", function () {
    var current = readFromUrl();
    state.q = current.q; state.topic = current.topic;
    queryInput.value = state.q; apply();
  });
  /* ---------- init from URL ---------- */

  var initial = readFromUrl();
  state.q = initial.q;
  state.topic = initial.topic;
  queryInput.value = state.q;
  apply();
  toolbar.querySelectorAll("[data-enhanced]").forEach(function (el) { el.hidden = false; });
})();
