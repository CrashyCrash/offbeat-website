/* Offbeat Inc. analytics scaffold.
   This keeps affiliate click handlers safe before GA4/Plausible/Cloudflare are connected.
   Add the real measurement script in <head> at launch; this file does not send data by itself. */
const OFFBEAT_GA4_CONFIGURED = false; // DRAFT: owner must confirm ownership of GA4 property before enabling.
const OFFBEAT_GA4_PROPERTY = "G-9MG87ETLPT";

window.dataLayer = window.dataLayer || [];
window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
window.offbeatTrack = window.offbeatTrack || function(eventName, params){
  try { if (typeof window.gtag === 'function') window.gtag('event', eventName, params || {}); } catch(e) {}
};

/* Central GA4 loader (DRAFT, disabled by default).
   When OFFBEAT_GA4_CONFIGURED is false this block does nothing and the file sends no data
   (behavior identical to the previous no-op scaffold).
   When true, it inserts a single gtag.js loader (only if one is not already on the document),
   reuses the dataLayer/gtag stub, and calls gtag('js')/gtag('config') exactly once. */
(function(){
  'use strict';
  function boot(){
    if (OFFBEAT_GA4_CONFIGURED !== true) return;
    if (window.__offbeatGA4Booted) return; // guard against double-init on repeat calls
    if (typeof document === 'undefined' || !document.head) return;
    var existing = document.querySelector('script[src*="googletagmanager.com/gtag/js"]');
    if (!existing) {
      var s = document.createElement('script');
      s.async = true;
      s.src = 'https://www.googletagmanager.com/gtag/js?id=' + OFFBEAT_GA4_PROPERTY;
      s.setAttribute('data-offbeat-ga4', 'central');
      document.head.appendChild(s);
    }
    if (typeof window.gtag !== 'function') {
      window.dataLayer = window.dataLayer || [];
      window.gtag = function(){ window.dataLayer.push(arguments); };
    }
    window.__offbeatGA4Booted = true;
    window.gtag('js', new Date());
    window.gtag('config', OFFBEAT_GA4_PROPERTY);
  }
  try {
    if (typeof document !== 'undefined' && document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
      boot();
    }
  } catch(e) {}
})();
