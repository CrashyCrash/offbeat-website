# Visitor-Journey Packet — Verification (2026-10-17)

Independent, non-production verification of the integrated draft tree. No merge, no deploy.

## Scope and lineage

| | |
|---|---|
| Base | `main` @ `a16b7105ed91afe8874751e9782f7831165a720f` (current main at build) |
| Packet head | `b1e58856b51affc382ea25d50e0f0ac0db8fd1fb` |
| Branch | `value/visitor-journey-packet-20261017` |
| Tree delta | 111 files (235 insertions / 193 deletions); **`sitemap.xml` untouched** |

Source PRs integrated (merge order = list order; each merge's parent² is the exact source head):

| # | Exact source head | Visitor benefit |
|---|---|---|
| #775 | `2c9492f08ab0b3e4a49b45a38445575368cbffa8` | 4 pages: dead hero image refs repointed to local PNGs |
| #783 | `ae0ba91b647458b2e728b8478cc165dc0b1f3c6c` | contact/disclosure: dead Unsplash hero refs → local illustrations |
| #883 | `c87ac0d7ceda050509ccddf24aa9c8e129261271` | 2 hub cards connecting otherwise orphaned buyer pages |
| #888 | `88810a13aad878c8af1723e01af04863bcd084c5` | 9 pages: false third-party illustration credits → "Illustration by Offbeat Inc." |
| #890 | `50ae6ef269b853e2af6bd61c3dd7f8d630799a59` | 105 pages: page-specific `og:image`/`twitter:image` from existing local assets |
| #901 | `e759b033376ea5935062d9919c5daf55a11d3237` | 2 index-only DJ decision guides exposed in the hubs |
| #902 | `caa102dd02afa5403eaab1d8f17603e486f92222` | 19 generic "Open guide." labels in `all-dj-guides.html` → reader-facing descriptions |

Not included (deliberate): #891 (favicon) and #893 (org schema) base on an older main and conflict against `a16b7105` — wave 2; #892 (ratings) conflicts with #890 on 2 review pages — wave 2.

## 1. Composability with owner-pending #886 (planner draft)

- `git merge-tree --write-tree` matrix: packet head × #886 head (`048665e7`) — and each of the 7 source heads × #886 — **all CLEAN, zero conflicts**.
- Only shared file between the packet and #886: `dj-gear-hub.html` (#890 adds a head meta line; #886 adds a body card — disjoint regions, merge-clean both proven by matrix).
- `sitemap.xml` is untouched by this packet, so the owner may merge #886 before/after/independently of this packet.

## 2. Full-site asset audit (115 pages served locally)

- **393 local/own-domain refs (`<img src>`, `<link href>`, `<script src>`, `og:image`) → all 200. Zero local 4xx.**
- External third-party refs (gtag, vendor CDNs) are UA-sensitive from this host: non-browser clients get 403/404, browser UAs get 200 (verified per-class). These pre-exist on `a16b7105` (same URLs, same pages) and are not introduced by this packet. The browser pass (§3) is the authoritative request record.

## 3. Browser render pass (Playwright/Chromium — authoritative)

Desktop 1360×900 + mobile 390×844, 11 pages × 2 viewports, real browser UA:

| Check | Result |
|---|---|
| Page errors / request-failed events | **0 / 0** on all 22 passes |
| Hero images (`naturalWidth`) on the 6 broken-media pages | **1200×560 loaded** on all six |
| #888 caption "Illustration by Offbeat Inc." | present on both spot-checked pages (`best-dj-controllers-under-200`, `best-turntable-cartridges`) |
| #883/#901 hub cards | both present in served bytes (base has neither); `best-online-dj-courses` card visible on desktop+mobile; `music-production-tools` card bbox verified visible |
| #890 `og:image` | all 11 sampled pages point to `…/assets/img/page-visuals/<page>.png` (existing local assets) |
| #902 reader-facing descriptions | sampled labels rendered in browser |

## 4. Broken-media before/after (the core fix, proven)

Same 6 pages, base `a16b7105` (port 8442) vs packet `b1e58856` (port 8441):

| Page | Source PR | Base hero status | Packet hero status |
|---|---|---|---|
| serato-dj-lite-vs-pro.html | #775 | 404 | **200** |
| soundcloud-vs-bandcamp.html | #775 | 404 | **200** |
| distrokid-vs-tunecore.html | #775 | 404 | **200** |
| numark-mixtrack-pro-fx-vs-ddj-200.html | #775 | 404 | **200** |
| contact.html | #783 | 404 (Unsplash) | **200** |
| disclosure.html | #783 | 404 (Unsplash) | **200** |

## 5. Content-level checks (diff-verified)

- **#902:** `all-dj-guides.html` file-level count of `<p>Open guide.</p>`: **85 → 66** (exactly 19 replaced with reader-facing next-step descriptions) — matches the source PR's claim.
- **#888:** the 9 affected pages each gain `Illustration by Offbeat Inc.` attribution on the hero figure (diff-verified); the previously false "Photo by … on Pexels" third-party credits on Offbeat's own illustrations are removed.
- **#883:** exact one-card insertions verified in `music-production.html` and `dj-skills-performance-hub.html`.

## 6. `html-validate` delta (default ruleset, all 111 changed files)

- Base: **279 issues — Packet: 279 issues — delta zero.** All are the pre-existing house `void-style` pattern (meta self-close); the only differences are line/column shifts from added meta lines. **No new rule class introduced.**

## 7. Status

**DRAFT — not merged, not deployed.** Owner review/merge is the only completion path. Composable with #886 in either order. Screenshots: `shots/` (11 pages × desktop/mobile).
