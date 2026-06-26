/* Offbeat Inc. analytics.
   Loads GA4 (G-9MG87ETLPT) and keeps affiliate click handlers safe.
   Guarded so pages that already inline the gtag snippet do not double-load/double-count. */
(function () {
  var GA4_ID = 'G-9MG87ETLPT';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };

  // Only inject the GA4 loader if no gtag.js script is already present on the page.
  if (!document.querySelector('script[src*="googletagmanager.com/gtag/js"]')) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
    document.head.appendChild(s);
    window.gtag('js', new Date());
    window.gtag('config', GA4_ID);
  }

  window.offbeatTrack = window.offbeatTrack || function (eventName, params) {
    try { if (typeof window.gtag === 'function') window.gtag('event', eventName, params || {}); } catch (e) {}
  };
})();
