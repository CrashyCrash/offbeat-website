/* Offbeat Inc. analytics — Google Analytics 4 (GA4) — consent-gated, single loader.
 *
 * Owner-verified property: G-9MG87ETLPT (property "Offbeat", web stream
 * https://offbeatinc.com). This file is the SINGLE GA4 loader for the public site,
 * loaded once per page via:
 *     <script defer src="assets/offbeat-analytics.js"></script>
 *
 * DESIGN (privacy-bounded; see Privacy Policy §3 and the independent review of #967)
 * -------------------------------------------------------------------------------
 * The strongest, most testable way to stop analytics before consent — and thereby to
 * stop Google's automatic Enhanced Measurement (site-search, outbound clicks,
 * history) from running at all — is to NOT LOAD THE GOOGLE TAG until the visitor
 * affirmatively allows analytics. Basic-consent semantics are enforced by omission:
 *
 *   NO CONSENT / REJECT             ->  no gtag.js is injected, no request to
 *                                       Google, no _ga cookie is created. (Zero.)
 *   CONSENT                         ->  one minimized pageview (path-only URL,
 *                                       NO referrer, a short static title) plus an
 *                                       allowlisted "affiliate_click" event that
 *                                       records only merchant/category.
 *   WITHDRAW                        ->  explicit consent denial, GA cookies
 *                                       expired, then ONE teardown reload so the
 *                                       loaded tag is destroyed and never loads
 *                                       again (see withdraw below).
 *
 * What this file explicitly does AND does NOT do:
 *   - We minimize the one pageview we do send (page_location = origin+path only;
 *     page_referrer omitted; page_title bounded and sanitized).
 *   - We use a CLOSED allowlist for custom events (event names + field names +
 *     allowed enum values). URLs, query strings, free text and unknown values are
 *     dropped by construction — not a denylist of known-PII names.
 *   - We declare Consent Mode v2 EXPLICITLY, in the documented order, whenever the
 *     tag loads (which only happens after consent):
 *         gtag('consent','default', { ad_storage, ad_user_data,
 *             ad_personalization: 'denied', analytics_storage: 'denied' })
 *         -> the real gtag.js loads and processes the queued commands in order
 *         -> gtag('consent','update', { analytics_storage: 'granted',
 *             ad_storage / ad_user_data / ad_personalization: 'denied' })
 *         -> gtag('js') + ONE minimized gtag('config') pageview.
 *     We NEVER grant the advertising consent types, and analytics_storage is
 *     'granted' only in that explicit, consent-driven update — never an
 *     unconditional default.
 *   - We remember the visitor's choice in first-party localStorage and honor it on
 *     every page/reload. Withdrawal issues an explicit consent denial, expires the
 *     first-party GA cookies, and — because a LOADED consent-denied tag can still
 *     emit cookieless pings (documented Google behavior for a loaded tag) — does a
 *     single clean teardown reload so the loaded tag is destroyed and, with the
 *     denial persisted, is never loaded on that or any later page.
 *   - We do NOT and CANNOT disable Google Enhanced Measurement from source. That is
 *     a GA4 property/dashboard setting managed by the owner (Admin -> Data
 *     collection and modification -> Data streams -> G-9MG87ETLPT -> Enhanced
 *     measurement). As of October 2026 the owner has it configured for this static
 *     site as: page-load-based Page views ON; site-search, outbound clicks,
 *     browser-history page changes, scroll, videos, file downloads and forms OFF.
 *     This file works with the setting as configured and never claims to change it.
 *   - We do NOT promise absolute absence of PII. Google collects some standard
 *     (at best pseudonymous — browser/device details, IP handled per Google policy)
 *     telemetry once a visitor has consented, which is exactly why consent gates it.
 *
 * No new Google account, property or credential. No other site. DRAFT change.
 */
(function () {
  'use strict';
  if (typeof window === 'undefined') return;
  if (window.__obConsentLoaderInstalled) return;
  window.__obConsentLoaderInstalled = true;

  var PROPERTY = 'G-9MG87ETLPT';
  var GA_SRC = 'https://www.googletagmanager.com/gtag/js?id=' + PROPERTY;
  var STORE_KEY = 'offbeat.ga-consent.v1';
  var TITLE_MAX = 80;

  /* ---- first-party consent store (localStorage) --------------------------
   * Storing the visitor's OWN consent choice is a first-party, non-tracking
   * persistence mechanism; it is not an analytics cookie and it carries no data
   * about the visitor beyond "granted|denied". */
  var ls = {
    get: function (k) { try { return window.localStorage ? window.localStorage.getItem(k) : null; } catch (e) { return null; } },
    set: function (k, v) { try { if (window.localStorage) window.localStorage.setItem(k, v); } catch (e) { } },
    del: function (k) { try { if (window.localStorage) window.localStorage.removeItem(k); } catch (e) { } }
  };

  // 'unknown' => no choice recorded yet; 'denied'; 'granted'.
  function readConsent() {
    var raw = ls.get(STORE_KEY);
    if (!raw) return 'unknown';
    try { var o = JSON.parse(raw); return (o && o.analytics === 'granted') ? 'granted' : 'denied'; }
    catch (e) { return 'denied'; } // fail closed
  }
  function writeConsent(analysis) {
    ls.set(STORE_KEY, JSON.stringify({ analytics: analysis, v: 1, at: new Date().toISOString() }));
  }
  // Exposed (small, honest) so the UI and independent tests can read current state.
  window.offbeatConsentState = function () { return readConsent(); };

  /* ---- data minimization for the ONE pageview we send when consented ------ */
  var EMAIL_RE = /[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]+/i;
  function safePath() {
    try {
      var l = window.location;
      var origin = l.origin || (l.protocol ? l.protocol + '//' + l.host : '');
      if (!origin) return 'https://offbeatinc.com/';
      return origin + (l.pathname || '/'); // path only — no search, no hash
    } catch (e) { return 'https://offbeatinc.com/'; }
  }
  function safeTitle() {
    var s = String(document.title || '').replace(/\s+/g, ' ').trim().slice(0, TITLE_MAX);
    if (!s) return '';
    if (EMAIL_RE.test(s)) return '';                        // no emails in title
    if (/(\+?1?[\s().-]?[0-9][0-9\s().-]{5,}[0-9])/.test(s)) return ''; // phone-like => drop
    if (/^(https?:)?\/\//.test(s) || /\?[a-z0-9_]+=/i.test(s)) return ''; // URL/query-like => drop
    return s;
  }

  /* ---- CLOSED allowlist for custom events (fail by construction) ---------
   * Only the exact event names below, with only the exact safe field names and
   * only the exact safe enum values, are ever forwarded. Anything else — a raw
   * destination URL, a search term, free text, a nested object, a number — is
   * dropped because it cannot match the closed schema. No arbitrary values. */
  var MERCHANT = { amazon: 1, zzounds: 1, sweetwater: 1, guitarcenter: 1, 'guitar-center': 1,
    pluginboutique: 1, loopmasters: 1, landr: 1, splice: 1, distrokid: 1, serato: 1, cdbaby: 1,
    other: 1 };
  var CATEGORY = { headphones: 1, 'headphone': 1, mixer: 1, controller: 1, monitor: 1, speaker: 1,
    interface: 1, software: 1, plugin: 1, 'sample-pack': 1, sample: 1, course: 1, stand: 1,
    turntable: 1, cartridge: 1, 'usb-drive': 1, cable: 1, accessory: 1, 'gig-bag': 1, other: 1 };
  var EVENTS = { 'affiliate_click': { merchant: MERCHANT, category: CATEGORY } };

  window.offbeatTrack = function (name, params) {
    try {
      if (readConsent() !== 'granted') return;                 // never transmit before consent
      if (!Object.prototype.hasOwnProperty.call(EVENTS, String(name))) return;
      var spec = EVENTS[String(name)];
      if (!spec) return;                                         // allowlist: unknown event dropped
      params = (params && typeof params === 'object') ? params : {};
      var payload = {};
      for (var k in spec) {
        if (!Object.prototype.hasOwnProperty.call(params, k)) continue;
        var v = params[k];
        if (typeof v === 'string' && spec[k][v] === 1) payload[k] = v; // else dropped
      }
      if (typeof window.gtag === 'function') window.gtag('event', String(name), payload);
    } catch (e) { /* never break the page */ }
  };

  /* ---- consent UI (small, accessible, non-blocking, no dark patterns) ------
   * Before a choice: one compact bottom-right card with equal-prominence
   * "Allow analytics" / "Do not allow". After a choice: the control collapses
   * to a compact single-line pill (status + actions) so it never permanently
   * obscures content. The region keeps role="region" + aria-live so state
   * changes are announced; every action is a native, keyboard-focusable
   * <button>; the site stays fully usable with analytics off. */
  var UI = null;
  var UI_IN_BODY = false;
  function el(tag, attrs, text) {
    var n = document.createElement(tag);
    if (attrs) { for (var a in attrs) { if (a.charAt(0) === 'o' && a.charAt(1) === 'n' && typeof attrs[a] === 'function') { n[a] = attrs[a]; } else { n.setAttribute(a, attrs[a]); } } }
    if (text != null) n.textContent = text;
    return n;
  }
  function button(label, action) {
    var b = el('button', { type: 'button', 'class': 'ob-consent-btn' }, label);
    b.addEventListener('click', function () { handle(action); });
    return b;
  }
  function privacyLink() {
    var a = el('a', { 'class': 'ob-consent-link', href: 'privacy.html' }, 'Privacy');
    return a;
  }
  function ensureUI() {
    if (!document.body) return null;
    if (UI && UI_IN_BODY) return UI;
    if (UI && UI.parentNode) { try { UI.parentNode.removeChild(UI); } catch (e) { } }
    UI = el('div', { 'class': 'ob-consent', role: 'region', 'aria-label': 'Offbeat analytics consent', 'aria-live': 'polite' });
    document.body.appendChild(UI);
    UI_IN_BODY = true;
    return UI;
  }

  function dismissUI() {
    if (UI && UI.parentNode) {
      try { UI.parentNode.removeChild(UI); } catch (e) { }
    }
    UI_IN_BODY = false;
  }

  function refresh(consent) {
    // When consent has been decided (granted or denied), dismiss and completely remove UI
    if (consent === 'granted' || consent === 'denied') {
      dismissUI();
      return;
    }

    var box = ensureUI();
    if (!box) return;
    box.setAttribute('class', 'ob-consent');
    var p = el('span', { 'class': 'ob-consent-text' });
    var row = el('div', { 'class': 'ob-consent-actions' });

    if (consent === 'unknown') {
      p.textContent = 'We use privacy-friendly analytics to learn which DJ guides are helpful. No ad tracking.';
      row.appendChild(button('Allow analytics', 'grant'));
      row.appendChild(button('Necessary only', 'deny'));
      row.appendChild(privacyLink());
    } else if (consent === 'reask') {
      p.textContent = 'Change your analytics choice. You can allow analytics or withdraw consent at any time.';
      row.appendChild(button('Allow analytics', 'grant'));
      row.appendChild(button('Necessary only', 'withdraw'));
      row.appendChild(privacyLink());
    }

    var restoreFocus = box.contains && box.contains(document.activeElement);
    while (box.firstChild) box.removeChild(box.firstChild);
    box.appendChild(p); box.appendChild(row);
    if (restoreFocus && row.firstChild) row.firstChild.focus();
  }

  // Allow reopening consent preferences from footer or settings link
  if (typeof document !== 'undefined') {
    document.addEventListener('click', function (e) {
      var trigger = e.target && e.target.closest && e.target.closest('[data-reopen-consent]');
      if (trigger) {
        e.preventDefault();
        handle('reask');
      }
    });
  }

  /* ---- withdrawal: explicit denial + cookie expiry + clean teardown --------
   * A loaded, consent-denied Google tag can still emit cookieless pings
   * (documented behavior for a LOADED tag — that is the "advanced-like" path we
   * must not rely on after a denial). So after the explicit denial and cookie
   * expiry we do ONE teardown reload: the loaded tag is destroyed with the
   * document, and because the denial is persisted in localStorage, the Google
   * tag is never loaded on that page or any later page. Basic-mode zero-egress
   * semantics are thereby enforced by construction, not by hope.
   * (The reload only runs when the REAL tag is active; local test seams stand in
   * for the tag and do not need it.) */
  function denyAndTeardown() {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('consent', 'update', {
          ad_storage: 'denied', ad_user_data: 'denied',
          ad_personalization: 'denied', analytics_storage: 'denied'
        });
      }
    } catch (e) { }
    clearGaCookies();
  }

  function clearGaCookies() {
    var mid = String(PROPERTY).replace(/^G-/, '');
    var domains = ['']; // host-only cookies, including older installations
    var host = window.location.hostname || '';
    var labels = host.split('.');
    // GA's default cookie_domain is auto: production cookies can belong to a
    // parent domain. Expiring a host-only cookie does not remove those cookies.
    for (var i = 0; i < labels.length - 1; i++) {
      domains.push('; domain=' + labels.slice(i).join('.'));
    }
    ['_ga', '_ga_' + mid, '_ga4_' + mid, '_ga_' + PROPERTY, '_ga4_' + PROPERTY].forEach(function (c) {
      domains.forEach(function (domain) {
        try { document.cookie = c + '=; Max-Age=0; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/' + domain; } catch (e) { }
      });
    });
  }

  var teardownPending = false;
  function stopAnalytics() {
    // Disable the property before the consent update: an already loaded tag
    // must not emit a denial/engagement ping during document teardown.
    window['ga-disable-' + PROPERTY] = true;
    denyAndTeardown();
    refresh('denied');
    if (window.__obGtagBooted && !window.__OFFBEAT_ANALYTICS_TEST && !teardownPending) {
      teardownPending = true;
      try { window.location.reload(); } catch (e) { }
    }
  }

  function handle(action) {
    if (action === 'grant') { writeConsent('granted'); applyConsent('granted'); }
    else if (action === 'deny' || action === 'withdraw') { writeConsent('denied'); stopAnalytics(); }
    else if (action === 'reask') { refresh('reask'); } // re-choose without changing the store yet
  }

  // Load + measure ONLY after affirmative consent. Idempotent (one tag, one
  // config). Explicit Consent Mode v2 declarations, in the documented order
  // (defaults first, updated state second, then collection):
  function bootGtag() {
    if (window.__obGtagBooted) return;
    window['ga-disable-' + PROPERTY] = false;
    window.__obGtagBooted = true;
    // 1) Explicit Consent Mode v2 default — all four consent types denied.
    //     Queued via the stub BEFORE the tag loads; the real tag processes it
    //     first (basic-mode order: default, then the updated state).
    window.gtag('consent', 'default', {
      ad_storage: 'denied', ad_user_data: 'denied',
      ad_personalization: 'denied', analytics_storage: 'denied'
    });
    // 2) Load the Google tag (a local test seam may substitute for the fetch;
    //     in production the real gtag.js is injected and sends these queued
    //     consent commands in order).
    var hook = window.__OFFBEAT_ANALYTICS_TEST;
    if (hook && typeof hook.inject === 'function') { hook.inject(); }
    else if (!document.querySelector('script[src*="googletagmanager.com/gtag/js"]')) {
      var host = (window.location && (window.location.hostname || window.location.host)) || '';
      var isPreviewHost = /(github\.io|localhost|127\.0\.0\.1|e2b\.app)/i.test(host);
      if (!isPreviewHost) {
        var s = el('script', null);
        s.async = true; s.src = GA_SRC; s.setAttribute('crossorigin', 'anonymous');
        s.onerror = function () { /* blocked: page still works */ };
        (document.head || document.documentElement).appendChild(s);
      }
    }
    // 3) Explicit update — the visitor affirmed consent, so grant analytics;
    //    the three advertising consent types remain denied.
    window.gtag('consent', 'update', {
      ad_storage: 'denied', ad_user_data: 'denied',
      ad_personalization: 'denied', analytics_storage: 'granted'
    });
    window.gtag('js', new Date());
    // 4) One minimized pageview. No referrer. Bounded static title.
    window.gtag('config', PROPERTY, {
      send_page_view: true,
      page_location: safePath(),
      page_referrer: '',
      page_title: safeTitle()
    });
  }

  function applyConsent(consent) {
    if (consent === 'granted') bootGtag();
    refresh(consent);
  }

  function boot() {
    // Safe no-op gtag so any pre-existing reference is harmless.
    window.dataLayer = window.dataLayer || [];
    if (typeof window.gtag !== 'function') { window.gtag = function () { window.dataLayer.push(arguments); }; }
    if (readConsent() !== 'granted') clearGaCookies();
    applyConsent(readConsent());   // consented -> boot+measure; else -> show choice UI, send nothing
  }

  // Consent choices are shared across tabs. Stop any already loaded tag when
  // another tab withdraws, including after a frozen page is restored.
  function reconcileConsent() {
    var consent = readConsent();
    if (consent !== 'granted') {
      if (window.__obGtagBooted) stopAnalytics();
      else { clearGaCookies(); refresh(consent); }
    }
  }
  if (typeof window.addEventListener === 'function') {
    window.addEventListener('storage', function (e) {
      if (e.key === STORE_KEY || e.key === null) reconcileConsent();
    });
    window.addEventListener('pageshow', reconcileConsent);
  }
  if (typeof document === 'undefined') return;
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();
})();
