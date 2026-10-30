# Offbeat relaunch — verification record

Date: 2026-10-25 (environment date) · Branch: `arena/187378fe-offbeat-website`
Platform: Arena Agent Mode · Model: not disclosed

## What was checked, and how

| Check | Command | Result |
| --- | --- | --- |
| Site integrity (links, alt text, duplicate ids, shared shell, JSON-LD, local assets) | `python3 tools/check_site.py` | 115 pages, **0 problems** |
| Structural / editorial rules inherited from the previous round | `python3 tests/check_site_structure.py` | **115/115 pages pass** (was 112/115 before this branch; 108/115 before that) |
| GA4 loader unit smoke tests | `node tests/ga4-loader.test.js` | **PASS 17, FAIL 0** |
| Rendered layout at three widths (1440 / 768 / 390) | headless Chromium sweep over all 115 pages × 3 viewports (**345 renders**) | **0 horizontal overflow**, **0 broken images**, **0 JS errors**, 4,675 unique local link targets all resolving |
| Search dialog | headless interaction test, typing `flx4` | opens, returns 8 ranked results, links resolve |
| Library filter | headless interaction test | keyword filter (`turntable` → 5 results in 2 groups) and chip filter (`software` → 20 results) both correct |
| Mobile navigation | headless interaction test at 390px | drawer opens, `aria-expanded` toggles, closes on selection |
| Consent UI | headless test on mobile | compact bar (113px tall), deny → "Analytics off." pill, **0 requests to google-analytics/googletagmanager before consent** |
| Image weight | `assets/img/editorial/` | 9 photos, 1.4 MB total, progressive JPEG, all sized with intrinsic width/height |

Screenshots in this folder were captured from the branch at 1440px and 390px,
full page, with the consent prompt dismissed so it does not cover content.
`before-*.jpg` are captures of the same pages before this branch.

## Known limits of this verification

- **Chromium could not reach `upload.wikimedia.org`** in this sandbox. The three
  product-specific photos (DDJ-FLX4 hero, DDJ-400 photo, controller comparison
  hero) could not be fetched or rendered here, so their visual appearance is
  unverified. They now carry an `onerror` fallback to an editorial photo plus a
  caption that says so, which was exercised by the blocked request.
- No physical device testing. Mobile behaviour was verified at a 390×844
  viewport in headless Chromium, not on iOS Safari or Android Chrome.
- Prices were not re-checked against live carts; they remain dated October 2026
  retailer-search figures, as stated on the pages themselves.
- Analytics/consent presentation was changed (copy length and a privacy link).
  The loader's logic is untouched and its unit tests pass, but this still
  deserves owner review before production deploy, as it touches privacy copy.
