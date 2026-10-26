# Visitor discovery candidate

Production baseline: `bad6e15f95041912d4590cbae2301c8ab664ac86` (remote main checked before work).

## Visitor outcome

Previously, All Guides was a complete but long static list, linked only in the footer. Visitors had no query or topic controls. The page devoted its first mobile screen to introductory metadata and a large image.

The candidate exposes All Guides in every primary navigation, promotes it on the homepage and five topic hubs, and makes the existing catalog searchable and filterable. Titles and summaries describe the destination rather than promote unsupported testing claims. Eight understandable topics replace the old General bucket. Real starter routes lead to learning, controller selection, software selection and production. A final setup route connects the compatibility matrix, speaker connections and equipment checklist.

All 113 original indexed destinations remain exactly once: 107 editorial guides/hubs plus six home/about/policy pages. Search covers titles, summaries, topic and filename, not complete article bodies. It supports word order, accents and model punctuation; explicit submission scrolls to results. Search/topic survive sharing, reload and returning from a guide. Unknown topics fall back safely; queries are rendered as text. No dependency, remote search request or second index.

## Independent acceptance

Codex reviewed Qwen's initial batch and corrected a retained blocking hero, mismatched form styling, misleading counts, unsuitable copied SEO descriptions, ambiguous topics, mobile controls and no-JavaScript behavior. Qwen's browser harness was unreliable; its test results were not used as acceptance. Codex stopped that exact producer process and used a separate Playwright harness against separate baseline/candidate servers.

- Desktop 1440px; mobile 390px; narrow 320px layout checks: no horizontal overflow or browser errors on catalog, home, FLX4 review and beginner hub.
- Functional desktop/mobile: model punctuation, multiword order, accents, budget search, combined topic/query, empty/reset/focus, URL restore, guide click/back, keyboard and hostile query handling.
- JavaScript disabled: every original catalog destination remains visible, inactive search controls hidden, starter route follows normally.
- axe-core 4.10.3 WCAG 2 A/AA and 2.1 AA checks: no reported violations on baseline or candidate catalog at desktop/mobile. This is automated evidence, not a comprehensive human accessibility audit.
- Parsed all 115 root pages: no broken local paths, duplicate IDs or missing primary catalog links. Article bodies outside the catalog/home/five hub entry sections are unchanged.
- Screenshots and machine-readable results in `evidence/`; the before and after captures use the same viewport and denied analytics choice.

No merge, deployment, public preview or live improvement is claimed. Arena branches remain untouched. Existing article claims were not fact-checked or rewritten by this discovery change.

## Second preserved milestone: article entry and onward journeys

A normal GET search form now appears on the 114 other root pages, including 404. The catalog uses its own query control, avoiding duplicate search fields. The forms send only `q` to the existing catalog; there is no search backend. Four guides now replace repetitive generic related-link blocks with three specific next actions and explanations: FLX4 review, speaker connection, mixing basics and recording. The FLX4's direct model-comparison links are retained. These changes connect choosing equipment to setup, practice to recording, and recording to sharing.

The expanded review found inherited accessibility failures on these four guides, confirmed against the untouched baseline. Comparison tables are now named keyboard-focusable regions; ten mobile overflow tables were exercised with ArrowRight, each scrolling successfully. The recording guide's sponsored inline link is now underlined. The catalog and all four changed guides report no automated axe violations at 1440/390px after these repairs.

Actual cross-page journey exercised at 1440, 1024, 768, 390 and 320px: enter `record mix` from an article header, open the recording guide from the filtered catalog, then follow the YouTube preparation route. Topic links from each new onward section also reach the matching catalog; no local HTTP failures, page exceptions or horizontal overflow were seen. With JavaScript disabled, a native header submission still reaches all 113 browsable destinations. The expandable starter routes work without JavaScript.

The catalog's mobile search now starts about 421px from the top at 390px width; the initial first card starts about 918px down. Submitting a query scrolls directly to matches. This is an observed local layout, not a live-site performance claim.

### Review limitations and release boundary

GitHub release CI rejected the first milestone with `DETERMINISTIC REJECT: missing or ambiguous Gate-v2 provenance block` ([run 40261517706](https://github.com/CrashyCrash/offbeat-website/actions/runs/40261517706)). This ordinary Codex feature branch has no signed DatBotty release envelope. No authority receipts, approvals, workflow changes or status overrides were manufactured. The PR remains a review candidate, not release-approved. Final-head CI disposition must be read from the PR.

The new search finds existing titles/summaries/topics/filenames, not whole article bodies. Existing commercial and testing claims inside articles remain outside this discovery review; removing a generic next-step block is not a full factual requalification of a product review. Screenshots are local previews. Native screen-reader/human-device acceptance and production deployment remain separate.

### Repeating the browser checks

Serve this worktree with a static server on port 8961. Use an existing Playwright installation; the site itself needs no dependencies. Run `node campaign/checks/catalog-journey.cjs`, `node campaign/checks/article-journeys.cjs`, and `node campaign/checks/layout.cjs`. Optional environment variables: `PLAYWRIGHT_MODULE` (module path), `BROWSER_EXECUTABLE` (existing Chromium executable), `CANDIDATE_URL` (trailing slash), and `EVIDENCE_DIR` (output directory). Results and screenshots default to `campaign/evidence/`. axe reports were produced separately with axe-core 4.10.3 and Playwright injection; no auditing library is shipped to visitors.
