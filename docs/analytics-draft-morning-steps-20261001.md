# GA4 draft — morning approval steps
1. OWNER confirms in the GA4 admin console that property G-9MG87ETLPT belongs to their account and records the confirmation (ownership is currently UNPROVEN).
2. Enable: set OFFBEAT_GA4_CONFIGURED = true in assets/offbeat-analytics.js.
3. Mark the draft PR ready and merge it.
4. Deploy via the site's normal deploy path.
5. Verify 3 sample pages (about, amuse-vs-distrokid, index): exactly ONE load of https://www.googletagmanager.com/gtag/js?id=G-9MG87ETLPT, exactly one gtag('config') call, no double-init, no console errors.
