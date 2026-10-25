/* Offbeat Inc. — small progressive enhancements.
 * No tracking, no third-party requests. Everything degrades gracefully without JS.
 * 1. Mobile navigation drawer
 * 2. Current-section highlighting in the header
 * 3. Instant client-side search over a local JSON index (loaded on demand)
 */
(function () {
  "use strict";

  var navLinks = document.querySelector(".nav-links");
  var toggle = document.querySelector(".nav-toggle");

  /* ---------- 1. Mobile navigation ---------- */
  if (toggle && navLinks) {
    toggle.addEventListener("click", function () {
      var open = navLinks.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    navLinks.addEventListener("click", function (event) {
      if (event.target.closest("a") && navLinks.classList.contains("is-open")) {
        navLinks.classList.remove("is-open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ---------- 2. Current section highlight ---------- */
  (function highlightCurrent() {
    if (!navLinks) return;
    var here = location.pathname.split("/").pop() || "index.html";
    var groups = {
      "beginner-dj-hub.html": ["start", "beginner", "how-to-start", "learn-djing", "first", "setup"],
      "dj-controllers-hub.html": ["controller", "ddj", "flx", "xdj", "inpulse", "rane", "mixtrack"],
      "dj-software-hub.html": ["software", "serato", "rekordbox", "traktor", "djay", "virtual-dj", "daw", "ableton", "fl-studio", "logic"],
      "dj-gear-hub.html": ["gear", "headphone", "mixer", "turntable", "cdj", "laptop", "cartridge", "usb", "monitor", "speaker", "stand", "equipment", "budget"],
      "dj-skills-performance-hub.html": ["skill", "mix", "beatmatch", "gig", "wedding", "record", "promote", "festival"]
    };
    Object.keys(groups).forEach(function (target) {
      var link = navLinks.querySelector('a[href="' + target + '"]');
      if (!link) return;
      if (groups[target].some(function (key) { return here.indexOf(key) !== -1; })) {
        link.classList.add("is-current");
      }
    });
    var direct = navLinks.querySelector('a[href="' + here + '"]');
    if (direct) direct.classList.add("is-current");
  })();

  /* ---------- 3. Glossary filter (dj-glossary.html) ---------- */
  (function glossary() {
    var input = document.querySelector("[data-glossary-input]");
    var terms = document.querySelectorAll(".glossary-term");
    var letterChips = document.querySelectorAll(".glossary-chip[data-letter]");
    var catChips = document.querySelectorAll(".glossary-cat-chip");
    var empty = document.querySelector("[data-glossary-empty]");
    var count = document.querySelector("[data-glossary-count]");
    var randomBtn = document.querySelector("[data-glossary-random]");
    if (!input || !terms.length) return;
    var letter = "all";
    var category = "all";

    function apply() {
      var query = input.value.toLowerCase().trim();
      var shown = 0;
      terms.forEach(function (term) {
        var text = term.getAttribute("data-terms") || term.textContent.toLowerCase();
        var initial = (term.getAttribute("data-letter") || "").toLowerCase();
        var cat = (term.getAttribute("data-cat") || "").toLowerCase();
        var letterOk = letter === "all" || initial === letter;
        var catOk = category === "all" || cat === category;
        var matchOk = !query || text.indexOf(query) !== -1;
        var visible = letterOk && catOk && matchOk;
        term.hidden = !visible;
        if (visible) shown++;
      });
      if (empty) empty.hidden = shown !== 0;
      if (count) count.textContent = shown + (shown === 1 ? " term" : " terms");
    }

    input.addEventListener("input", apply);

    letterChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        letter = chip.getAttribute("data-letter");
        letterChips.forEach(function (other) {
          var on = other === chip;
          other.classList.toggle("is-active", on);
          other.setAttribute("aria-pressed", on ? "true" : "false");
        });
        apply();
      });
    });

    catChips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        category = chip.getAttribute("data-cat");
        catChips.forEach(function (other) {
          var on = other === chip;
          other.classList.toggle("is-active", on);
          other.setAttribute("aria-pressed", on ? "true" : "false");
        });
        apply();
      });
    });

    if (randomBtn) {
      randomBtn.addEventListener("click", function () {
        letter = "all";
        category = "all";
        input.value = "";
        letterChips.forEach(function (c) { c.classList.toggle("is-active", c.getAttribute("data-letter") === "all"); });
        catChips.forEach(function (c) { c.classList.toggle("is-active", c.getAttribute("data-cat") === "all"); });
        apply();
        var randIndex = Math.floor(Math.random() * terms.length);
        var chosen = terms[randIndex];
        if (chosen) {
          chosen.scrollIntoView({ behavior: "smooth", block: "center" });
          chosen.classList.add("is-highlighted");
          window.setTimeout(function () { chosen.classList.remove("is-highlighted"); }, 2000);
        }
      });
    }

    apply();
  })();

  /* ---------- 3b. Library filter (all-dj-guides.html) ---------- */
  (function library() {
    var input = document.querySelector("[data-library-input]");
    var chips = document.querySelectorAll(".chip-filter");
    var items = document.querySelectorAll(".library-item");
    var groups = document.querySelectorAll(".library-group");
    var empty = document.querySelector("[data-library-empty]");
    if (!input || !items.length) return;
    var group = "all";

    function apply() {
      var terms = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      var shown = 0;
      items.forEach(function (item) {
        var text = item.getAttribute("data-terms") || "";
        var inGroup = group === "all" || item.getAttribute("data-group") === group;
        var matches = terms.every(function (t) { return text.indexOf(t) !== -1; });
        var visible = inGroup && matches;
        item.hidden = !visible;
        if (visible) shown++;
      });
      groups.forEach(function (section) {
        var has = section.querySelector(".library-item:not([hidden])");
        section.hidden = !has;
      });
      if (empty) empty.hidden = shown !== 0;
    }

    input.addEventListener("input", apply);
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        group = chip.getAttribute("data-filter");
        chips.forEach(function (other) {
          var on = other === chip;
          other.classList.toggle("is-active", on);
          other.setAttribute("aria-pressed", on ? "true" : "false");
        });
        apply();
      });
    });
    apply();
  })();


  /* ---------- 5. Long-guide navigation ----------
   * Three pieces that make a 10-minute guide navigable:
   *   a. section ids + hover permalinks on every heading
   *   b. a collapsible "In this guide" card (all widths) and, on wide screens,
   *      a sticky rail that follows the reader down the page
   *   c. numbered badges on "Step N" sections and a reading-progress bar
   */
  (function guideNavigation() {
    var main = document.querySelector("main");
    if (!main) return;
    var wrap = main.querySelector(".content-wrap") || main.querySelector(".page-content");
    if (!wrap) return;

    var headings = [].slice.call(wrap.querySelectorAll("h2")).filter(function (h) {
      return h.textContent.trim().length > 3 && !h.closest("details");
    });
    if (headings.length < 4) return;

    var slug = function (text) {
      return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48);
    };
    var shortLabel = function (text) {
      return text.replace(/\s*\([^)]*\)\s*$/, "").replace(/\s+[—–]\s+.*$/, "").trim();
    };

    /* Labels are captured before badges and permalinks touch the headings */
    var entries = headings.map(function (heading) {
      return { el: heading, label: shortLabel(heading.textContent.replace(/\s+/g, " ").trim()) };
    });

    headings.forEach(function (heading, i) {
      if (!heading.id) heading.id = "section-" + (i + 1) + "-" + slug(heading.textContent);
      heading.classList.add("anchored");
      var link = document.createElement("a");
      link.className = "heading-anchor";
      link.href = "#" + heading.id;
      link.setAttribute("aria-label", "Link to “" + entries[i].label + "”");
      link.innerHTML = "#";
      heading.appendChild(link);
    });

    /* Numbered badges for step-by-step sections */
    Array.prototype.forEach.call(wrap.querySelectorAll(".article-section, .format-section, .ofb-section, section"), function (section) {
      var h2 = section.querySelector("h2");
      if (!h2) return;
      var match = h2.textContent.match(/^Step\s+(\d+)\s*[:.—-]\s*/i);
      if (!match) return;
      section.classList.add("is-step");
      var badge = document.createElement("span");
      badge.className = "step-num";
      badge.setAttribute("aria-hidden", "true");
      badge.textContent = match[1];
      var text = h2.textContent.replace(match[0], "");
      h2.textContent = "";
      h2.appendChild(badge);
      h2.appendChild(document.createTextNode(text));
    });

    /* a. Collapsible contents card */
    var items = entries.slice(0, 16).map(function (entry) {
      return '<li><a href="#' + entry.el.id + '">' + entry.label + "</a></li>";
    }).join("");

    var toc = document.createElement("nav");
    toc.className = "toc";
    toc.setAttribute("aria-label", "On this page");
    toc.innerHTML =
      '<details><summary>In this guide <span class="toc-count">' + headings.length +
      " sections</span></summary><ol class=\"toc-list\">" + items + "</ol></details>";

    var anchor = wrap.querySelector(".article-section") || wrap.firstElementChild;
    if (anchor) anchor.parentNode.insertBefore(toc, anchor.nextSibling);
    else wrap.appendChild(toc);

    /* b. Sticky rail for wide screens */
    var rail = document.createElement("aside");
    rail.className = "guide-rail";
    rail.setAttribute("aria-label", "Guide contents");
    rail.innerHTML =
      '<div class="rail-inner">' +
      '<p class="rail-label">On this page</p>' +
      '<ol class="rail-list">' +
      entries.slice(0, 18).map(function (entry) {
        return '<li><a href="#' + entry.el.id + '">' + entry.label + "</a></li>";
      }).join("") +
      "</ol>" +
      '<a class="rail-top" href="#top">Back to top <span aria-hidden="true">↑</span></a>' +
      "</div>";
    wrap.insertBefore(rail, wrap.firstElementChild);
    wrap.classList.add("has-rail");

    var links = [].slice.call(rail.querySelectorAll(".rail-list a"));
    var byId = {};
    links.forEach(function (link) { byId[link.getAttribute("href").slice(1)] = link; });
    var current = null;

    function setActive(id) {
      if (current === id) return;
      current = id;
      links.forEach(function (link) { link.classList.toggle("is-active", link === byId[id]); });
    }

    if ("IntersectionObserver" in window) {
      var seen = {};
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) { seen[entry.target.id] = entry.isIntersecting; });
        var visible = headings.filter(function (h) { return seen[h.id]; });
        if (visible.length) setActive(visible[0].id);
      }, { rootMargin: "-15% 0px -70% 0px", threshold: 0 });
      headings.forEach(function (h) { observer.observe(h); });
    }

    /* c. Reading progress */
    var bar = document.createElement("div");
    bar.className = "read-progress";
    bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);
    var ticking = false;
    function update() {
      var height = document.documentElement.scrollHeight - window.innerHeight;
      var ratio = height > 0 ? Math.min(1, Math.max(0, window.scrollY / height)) : 0;
      bar.style.transform = "scaleX(" + ratio + ")";
      ticking = false;
    }
    window.addEventListener("scroll", function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    update();
  })();

  /* ---------- 6. Search ---------- */
  var overlay = document.getElementById("site-search");
  var openers = document.querySelectorAll("[data-search-open]");
  if (!overlay || !openers.length) return;

  var input = overlay.querySelector("[data-search-input]");
  var results = overlay.querySelector("[data-search-results]");
  var status = overlay.querySelector("[data-search-status]");
  var index = null;
  var loading = false;
  var active = -1;

  function openSearch() {
    overlay.hidden = false;
    document.documentElement.style.overflow = "hidden";
    loadIndex();
    window.setTimeout(function () { input.focus(); }, 30);
  }
  function closeSearch() {
    overlay.hidden = true;
    document.documentElement.style.overflow = "";
    active = -1;
    groupFilter = "all";
    if (groupHost) {
      [].forEach.call(groupHost.querySelectorAll(".search-chip"), function (c) {
        c.classList.toggle("is-active", c.getAttribute("data-group") === "all");
      });
    }
  }

  function loadIndex() {
    if (index || loading) return;
    loading = true;
    fetch("assets/search-index.json")
      .then(function (r) { return r.json(); })
      .then(function (data) { index = data; buildGroups(); render(input.value); })
      .catch(function () {
        if (status) status.textContent = "Search index unavailable — browse All DJ Guides instead.";
      });
  }

  var groupHost = overlay.querySelector("[data-search-groups]");

  function buildGroups() {
    if (!groupHost || !index) return;
    var order = [];
    var seen = {};
    index.forEach(function (item) {
      if (!seen[item.g]) { seen[item.g] = item.c; order.push(item.g); }
    });
    var html = '<button type="button" class="search-chip is-active" data-group="all">All</button>';
    order.forEach(function (id) {
      html += '<button type="button" class="search-chip" data-group="' + id + '">' +
        seen[id].replace(/ &amp; /g, " & ") + "</button>";
    });
    groupHost.innerHTML = html;
    groupHost.addEventListener("click", function (event) {
      var chip = event.target.closest("[data-group]");
      if (!chip) return;
      groupFilter = chip.getAttribute("data-group");
      [].forEach.call(groupHost.querySelectorAll(".search-chip"), function (c) {
        c.classList.toggle("is-active", c === chip);
      });
      render(input.value);
    });
  }

  function score(item, terms) {
    var hay = (item.t + " " + item.d + " " + item.k).toLowerCase();
    var total = 0;
    for (var i = 0; i < terms.length; i++) {
      var pos = hay.indexOf(terms[i]);
      if (pos === -1) return 0;
      total += pos === 0 ? 6 : 3;
      if (item.t.toLowerCase().indexOf(terms[i]) !== -1) total += 8;
    }
    return total;
  }

  var groupFilter = "all";

  function render(query) {
    if (!index) return;
    var terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    active = -1;
    var list = terms.length
      ? index
          .map(function (item) { return { item: item, s: score(item, terms) }; })
          .filter(function (r) { return r.s > 0; })
          .sort(function (a, b) { return b.s - a.s; })
          .slice(0, 12)
          .map(function (r) { return r.item; })
      : index.filter(function (item) { return item.f; }).slice(0, 8);
    if (groupFilter !== "all") {
      list = list.filter(function (item) { return item.g === groupFilter; });
    }

    if (status) {
      status.textContent = terms.length || groupFilter !== "all"
        ? (list.length ? list.length + (list.length === 1 ? " result" : " results") : "No guides matched that search")
        : "Popular guides";
    }
    results.innerHTML = list.map(function (item) {
      return '<li><a href="' + item.u + '"><span class="search-cat">' + item.c +
        '</span><strong>' + item.t + '</strong><span class="search-desc">' +
        item.d + '</span></a></li>';
    }).join("");
  }

  function move(delta) {
    var links = results.querySelectorAll("a");
    if (!links.length) return;
    active = (active + delta + links.length) % links.length;
    links[active].focus();
  }

  openers.forEach(function (button) {
    button.addEventListener("click", function (event) {
      event.preventDefault();
      openSearch();
    });
  });

  overlay.addEventListener("click", function (event) {
    if (event.target === overlay || event.target.hasAttribute("data-search-close")) closeSearch();
  });

  input.addEventListener("input", function () { render(input.value); });
  input.addEventListener("keydown", function (event) {
    if (event.key === "ArrowDown") { event.preventDefault(); move(1); }
    if (event.key === "ArrowUp") { event.preventDefault(); move(-1); }
    if (event.key === "Enter") {
      var first = results.querySelector("a");
      if (first) window.location.href = first.getAttribute("href");
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && !overlay.hidden) closeSearch();
    if ((event.key === "/" || (event.key === "k" && (event.metaKey || event.ctrlKey))) &&
        overlay.hidden && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)) {
      event.preventDefault();
      openSearch();
    }
  });
})();

/* ---------- 7. Table affordance: show a scroll hint on wide tables (mobile) ---------- */
(function tableHints() {
  document.querySelectorAll(".table-wrap, .comparison-table-wrap, .comparison-table-wrapper, .table-wrapper").forEach(function (wrap) {
    var table = wrap.querySelector("table");
    if (!table) return;
    function check() {
      var scrollable = wrap.scrollWidth > wrap.clientWidth + 4;
      wrap.classList.toggle("is-scrollable", scrollable);
      wrap.setAttribute("data-scrollable", scrollable ? "true" : "false");
    }
    check();
    window.addEventListener("resize", check, { passive: true });
  });
})();
