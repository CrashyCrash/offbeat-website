# FV-0015 / PR #889 — hero-meta contrast (WCAG AA) verification

Base: `main@0cff98db136e54ada4caf70e7fbf1d004c4d073a` (protected signed release #871)
Branch: `value/muted2-contrast-20261016` @ `744f1b1` (1-line CSS change)
Date: 2026-10-16 · Tool: Playwright + Chromium 1440×900 / 390×844 via local `http.server`

## Measured contrast (live `getComputedStyle`, resolved background chain)

| Page (base = main) | `.hero-meta` (13.6px) | Result base |
|---|---|---|
| best-dj-turntables-2026.html | fg `rgb(100,116,139)` on `rgb(5,5,8)` | **4.28:1 FAIL** |
| best-dj-controllers-2026.html | same | **4.28:1 FAIL** |
| index.html | same | **4.28:1 FAIL** |

Full audit element sets (3 pages, base → branch): 3 FAIL → **0 FAIL**
(`contrast-main-0cff98d.json`, `contrast-pr889.json`).

Branch re-measurement: `.hero-meta` fg `rgb(122,140,171)` (= `#7a8cab`) → **5.98:1 PASS** on all three pages.

## Token math (WCAG 1.4.3, all surfaces)

| fg / surface | ratio |
|---|---|
| old `#64748b` / footer `#08080d` | 3.9–4.2:1 FAIL |
| old `#64748b` / hero gradient (measured) | 4.28:1 FAIL |
| old `#64748b` / `--surface-2 #1a1a24` | 3.63:1 FAIL |
| new `#7a8cab` / footer `#08080d` | 5.9:1 PASS |
| new `#7a8cab` / hero gradient (measured) | **5.98:1 PASS** |
| new `#7a8cab` / `--surface-2` / `--surface` | 5.07 / 5.5:1 PASS |

## Scope of the token

`--muted-2` is defined once (`assets/style.css:15`). Four textual rules reference it; three of those
(`.hero-figure figcaption` line 49, `.spec-label/.stat-label` line 93, `.footer-col h4` line 139) are
overridden by later rules to `--muted`/`#a78bfa` — browser-verified to render passing colors.
**The only rule rendered with the old value is `.hero-meta, .ofb-meta` (line 50) — present on all 112 pages.**

## Pixel evidence (screenshots)

- `hero-base-main-0cff98d.png` — hero contains `#64748b` text pixels (20 sampled), no `#7a8cab` pixels (1)
- `hero-branch-pr889.png`  — hero contains `#7a8cab` text pixels (19 sampled), no `#64748b` pixels (0)
- mobile variants included (390×844 layout intact, meta line wraps cleanly)

## Other checks

- 0 page errors, 0 responses ≥400 (base and branch, 2 pages)
- 8 edge pages (index, 404, about, music-production, best-studio-monitors, dj-music-stores, best-online-dj-courses, beginner-dj-hub) render the new token
- html-validate (turntables + music-production): identical output base/branch → zero delta (1 pre-existing house-pattern warning)
- `git diff --stat`: 1 CSS file, +1/−1; `git diff --check` clean; 0 HTML changes
- Duplication: none of the 31 open PRs touches `assets/style.css` or `--muted-2` (checked 2026-10-16 via `gh pr ... files`)

DRAFT only. Not merged, not deployed.
