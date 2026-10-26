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
