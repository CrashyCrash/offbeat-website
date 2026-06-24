/* Offbeat Inc. analytics scaffold.
   This keeps affiliate click handlers safe before GA4/Plausible/Cloudflare are connected.
   Add the real measurement script in <head> at launch; this file does not send data by itself. */
window.dataLayer = window.dataLayer || [];
window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
window.offbeatTrack = window.offbeatTrack || function(eventName, params){
  try { if (typeof window.gtag === 'function') window.gtag('event', eventName, params || {}); } catch(e) {}
};
