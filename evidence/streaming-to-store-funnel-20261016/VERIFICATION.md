# VERIFICATION — streaming → DJ Music Stores funnel (PR #884)

**Scope (2 files, 1 insertion each; house pattern only, no CSS/JS/claims/rights):**
- `how-to-dj-with-spotify.html` → "Related DJ guides and next steps" gains first item `DJ Music Stores` → `dj-music-stores.html`.
- `dj-software-apple-music.html` → same.

**Base:** `main @ 0cff98db136e54ada4caf70e7fbf1d004c4d073a`. **Branch:** `value/streaming-to-store-funnel-20261016 @ 0948b30fea32208bb1b67b8376153d68e22cb099`.

**Verified 2026-10-16 (run 3).**

## Why (the finding)
- The two "streaming is not a library replacement" guides both tell a paid-event buyer to build an **owned/performance-safe library**, yet link **nowhere** to where that music comes from:
  - `how-to-dj-with-spotify.html`: *"rebuild important crates with owned downloads, record pools, promos"*; *"Buy or source performance-safe versions of the tracks you will actually play."*
  - `dj-software-apple-music.html`: *"does not remove the need for a properly owned or licensed music library."*
- Their "Related DJ guides and next steps" lists had 5 items each, **0 music-source pages**.
- The store cluster (`dj-music-stores.html` hub + `beatport-vs-traxsource.html` + `soundcloud-vs-bandcamp.html`) was otherwise **reachable only from the site index** — full 112-page in-degree sweep (`.overnight/sweep2_indegree.py`): `dj-music-stores.html` in-degree **1**, the two comparisons in-degree **2**.
- This **resolves** the deferred "third orphan" (FV-0014 run 2, `0cff98d`) with a correction: it is the **buyer-direction dead end** (the promising/pointing side omits the link), not a mere context cross-link.

## Render (Playwright/Chromium, local HTTP, base @ 8011 vs branch @ 8012, 2026-10-16)
- `how-to-dj-with-spotify.html` + `dj-software-apple-music.html`, **desktop 1360×900 + mobile 390×844**:
  - base: HTTP **200**, `a[href=dj-music-stores.html]` **absent**; branch: HTTP **200**, link **present + `is_visible()` true**.
  - **0 console errors, 0 page errors** on all 8 page-loads (base + branch × 2 pages × 2 viewports).
  - Click-through (branch, desktop): `how-to-dj-with-spotify.html` → click `DJ Music Stores` → final URL `…/dj-music-stores.html`, 200.
  - Cluster reachability (branch): `dj-music-stores.html` 200, `beatport-vs-traxsource.html` 200, `soundcloud-vs-bandcamp.html` 200.
- Verdict: **PASS.**

## Lint (html-validate 9.0.0, `.htmlvalidate` default rules; base vs branch, both files)
- Both files: **4 pre-existing `wcag/h63` `<th> scope` problems on each side** — sorted problem sets **byte-identical** → **delta zero.** No new validity problems introduced.

## Merge-tree (3-way `git merge-tree --write-tree`, 2026-10-16)
- **CLEAN** vs #766 (value/disclosure-20261001), #775, #783, #879, #880, #881, #883 (value PRs).
- Conflicts vs #778 / #779 / #780 / #781 / #782 / #785 occur **only in files this PR does not touch** (`best-dj-controllers-2026.html`, `all-dj-guides.html`, `best-dj-laptop-2026.html`, `dj-gear-hub.html`, `index.html`, `beginner-dj-hub.html`) and are **reproduced identically** by merging plain `main` → those heads (pre-existing stale-base conflicts).
- **Only same-file collision: #876** (`tdq/value-draft-auto-…`), a **heading-only churn** auto-draft on `dj-software-apple-music.html` (renames one H2 "what actually matters" → "Match … to your setup"). Collision is a **minified single-line** artifact (both edits on the same physical `<li>`-adjacent line); the content is different (this PR adds a nav `<li>`, #876 renames an `<h2>`), and they **co-exist** — if #876 lands first, re-add the one `<li>` mechanically.

## Non-duplication + guardrail
- Checked **all 47 open PRs** (changed-files + diff): none links the two streaming pages to the store cluster.
- **Retired/slop guardrail:** none of `dj-music-stores.html` / `beatport-vs-traxsource.html` / `soundcloud-vs-bandcamp.html` is in the retired/slop set (FV-0005 / `catalogs/PAGES.md`).
- **Era copies** (2026-08-01 backup; 2026-07-31 quarantine archive): **0 store links** from either streaming page (never implemented).

## Diff
`2 files changed, 2 insertions(+), 2 deletions(-)` (each: one `<li>` added to the existing related-list). `git diff --check` clean.
