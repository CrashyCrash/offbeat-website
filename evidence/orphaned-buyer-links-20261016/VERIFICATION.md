# Verification — orphaned buyer-page links (draft branch, 2026-10-16)

Isolated draft work of an autonomous Forgotten-Value run (run 2). Base: protected `main` @ `0cff98db136e54ada4caf70e7fbf1d004c4d073a`. **Nothing here is merged or deployed.**

## Claim under test

Two live product-discovery pages were reachable **only from the site index** (`all-dj-guides.html`) — a one-way dead end at the buyer/learner decision point, the same class of gap as the turntables → cartridges finding (DRAFT PR #881):

1. `music-production-tools.html` ("Production tools for DJ/producers" — the cluster's orchestration / what-to-buy-when guide) had **zero inbound links** from its own cluster: `music-production.html`, `best-daw-for-music-production.html`, `best-music-production-plugins.html`, `best-music-production-software-2026.html`, `best-dj-sample-packs-2026.html`, `midi-controllers-for-music-production.html` (measured: 0 refs each on `0cff98d`; `music-production.html`'s own "Producer crossover" grid listed the other 6 cluster pages but not the tools page).
2. `best-online-dj-courses.html` ("Best Online DJ Courses 2026" — Udemy vs Skillshare vs free YouTube, the site's only structured-learning purchase page) had **zero inbound links** from any learner/skills page: `how-to-start-djing.html`, `learn-djing.html`, `how-to-mix-music-beginners.html`, `how-to-get-dj-gigs.html`, `how-to-become-a-dj.html`, `dj-skills-performance-hub.html` (measured: 0 refs each on `0cff98d`).

**Change (2 files, 1 insertion each, site's own house pattern `ofb-grid`/`ofb-card`, no CSS, no new product/price claims, no rights additions):**

- `music-production.html` — adds the missing "Music Production Tools" card to the existing 6-card "Producer crossover" grid (→ 7; card copy mirrors the tools page's own H1/H2/FAQ wording).
- `dj-skills-performance-hub.html` — adds a "Best Online DJ Courses" card (kicker "Guided learning") to the existing "What this hub fixes" grid (→ 7; copy mirrors the courses page's own H1/H2 wording).

## Browser verification (Playwright/Chromium, local HTTP servers, 2026-10-16)

- Desktop 1360×900 and mobile 390×844; base vs branch on both changed pages.
- **Base:** `music-production.html` grid = 6 cards, tools card **absent**; `dj-skills-performance-hub.html` grid = 6 cards, courses card **absent**; 0 responses ≥400; 0 console/page errors.
- **Branch:** both pages 7 cards; new card present and **visible** in all 4 viewport/page combos (element `is_visible()` true; bounding boxes recorded); **0 responses ≥400; 0 console/page errors**.
- All 4 target URLs (both changed pages + both targets) return **HTTP 200** on the branch server.

## Static verification

- `git diff --stat` = 2 files, 2 insertions(+), 1 deletion(-) (the 1 deletion is the single reflowed grid line in `music-production.html`; content is an insertion only).
- `git diff --check` clean.
- `html-validate` 9.0.0 on both files, base vs branch: **3 problems on each side** (pre-existing house-pattern `wcag/h63` class already tracked by the queue; rule-count diff empty) → **delta zero**.
- Mergeability (3-way `git merge-tree` vs open PR heads, 2026-10-16): **CLEAN** vs #766, #770, #775, #783, #879, #880, #881. #778/#779/#780/#781 show content conflicts **only in files this PR does not touch** (`best-dj-controllers-2026.html`; `all-dj-guides.html`, `best-dj-laptop-2026.html`, `dj-gear-hub.html`, `index.html`) — reproduced identically by merging plain `main` into each head **without** this PR, i.e. pre-existing stale-base conflicts of those PRs.
- Duplication check: all 46 open PRs checked. #766 fixes disclosure on `contact.html`/`music-production-tools.html`; #770 adds `datePublished`/JSON-LD to several files; #772/#768 are disclosure/contact edits; #781 (stack) rewords `how-to-start-djing.html` and adds a "Learning Path" card at the **head** of the skills-hub grid plus new page `dj-skills-learning-path.html` (that page carries a courses link) — none of these add the two links implemented here.
- Historical copies (read-only): era copies `~/Desktop/Restored/offbeat-dj-website/{6-13-2026,NEW16}/public-page(s)` and the 2026-07-31 quarantine archive show **0 refs** from `music-production.html` → `music-production-tools.html` and from `dj-skills-performance-hub.html` → `best-online-dj-courses.html` → the gap never shipped; it is not an owner-retired link.
- Guardrail check: neither target page is in the retired/slop set (FV-0005 / `catalogs/PAGES.md`); `music-production-tools.html` is the legitimate target of the merge-ready non-draft PR #766.

## Card screenshots (branch)

| Card | Desktop 1360×900 | Mobile 390×844 |
|---|---|---|
| Music Production Tools (`music-production.html`) | `shots/music-production___branch-desktop_1360px_card.png` | `shots/music-production___branch-mobile_390px_card.png` |
| Best Online DJ Courses (`dj-skills-performance-hub.html`) | `shots/dj-skills-performance-hub___branch-desktop_1360px_card.png` | `shots/dj-skills-performance-hub___branch-mobile_390px_card.png` |

Full-page desktop + mobile screenshots for all four combos were generated and inspected during verification (kept out of the diff for size).
