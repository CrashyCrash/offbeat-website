# Offbeat public-site product-quality recovery — 2026-10-24

**Status:** owner-approved direction and agent acceptance criteria. **This document does not grant any new GitHub bypass, merge, deployment, credential, media-rights, privacy, or financial authority.** Follow the active protected repository policies. The live website and its readers, not agent activity, determine success.

## Purpose and diagnosis

Offbeat was primarily a practical proving ground for DatBotty/TaskDatty to deliver useful improvements without routine owner involvement. After months, the live site still contains conspicuous product-quality defects despite numerous agents, drafts, checks, and successful protected releases. This is a **program-level delivery failure**, not merely a few missing edits.

Verified 2026-10-24 examples:
- `disclosure.html`: duplicated consecutive generic hero/illustration; PR #937 repaired image loading without removing duplicate/redundant visuals.
- `privacy.html`: reader-facing text leaks excessive analytics implementation detail, including the GA4 measurement ID; keep accurate required disclosures, but do not publish unnecessary configuration instructions.
- `assets/offbeat-analytics.js`: initial consent prompt is unnecessarily long relative to the choice.
- `about.html`: editorial process instructions ("When a guide uses hands-on testing...") are presented to visitors rather than describing demonstrated practices.
- `best-dj-controllers-2026.html`: comparison table repeatedly says "Verify current price" instead of providing useful, properly sourced price information or clearly qualified price ranges/dates.
- No favicon on current `main`, although already prepared sitewide drafts #769 and #891 exist.
- Several image fixes use `assets/img/page-visuals/*.png` **generic illustration cards** as a substitute for broken/wrong-product photographs. Loading correctly is not equivalent to relevance. `data-original-src` alone does not cause a browser to display an image.
- Existing open branches contain substantial useful, duplicated, obsolete, superseded, and blocked work; do not start another candidate until reviewing likely competing PRs.

Dated snapshot (2026-10-24): 53 open issues, 61 open PRs, ~116 HTML files and 112 generic page-visual PNGs. Counts are evidence of backlog, **not outcome metrics**; refresh before relying on them.

**Why this happened:** optimization for PR/CI/reviewer success rather than page usability; technical regression checks without an acceptable product baseline; many narrow, competing, stale drafts; laborious cross-page HTML edits; and a legitimate but too-narrow unattended release lane, which excludes many sitewide, asset, executable, and legal/policy improvements. No self-granted relaxation of that lane.

## Binding definition of product completion

A defect is complete only when:
1. The exact observed **live URL and visitor task** are recorded with before-state evidence (screenshot or reproducible browser observation as appropriate).
2. The change improves the **whole rendered page/journey**, not only source syntax, asset availability, or a narrow diff; inspect desktop and mobile.
3. Relevant product images depict the correct equipment/category and have legitimate source rights, truthful alt text and credit. A generic fallback cannot count as a successful product-photo adoption. Remove duplicated or gratuitous figures; a policy page often needs no hero at all.
4. Price/model/license/specification claims are current, primary-source-grounded, with geography/currency/as-of date and no invented firsthand testing. If reliable current price cannot be sourced, use an explicitly qualified range or restructure the comparison rather than filling most of a price column with "Verify current price."
5. Published copy is visitor language: no internal agent instructions, future editorial promises presented as evidence, empty/generated filler, unsupported guarantees, contradictory statements, redundant process text, or implementation trivia.
6. Consent controls remain privacy-respecting, accessible and compact, with accurate policy text; do not remove material disclosures to shorten copy. Changes to privacy/legal/analytics behavior require their **own authorized stronger review**.
7. Navigation, keyboard/touch behavior, key links, layout, and relevant commercial actions work. Zero console errors/404s/HTML-validation regression is necessary where applicable, **not sufficient**.
8. The release has independent **semantic and visual** acceptance on the exact final head; GitHub protected merge, Pages deployment and *fresh public-page readback* are independently confirmed. For images also verify the rendered pixels/source, not merely HTTP 200.
9. The discovered defect is closed or dispositioned only after live verification; draft PRs, green checks and documents are tracked separately from realized visitor improvement.

## Immediate two-track execution

**Track A — short, outcome-first website rescue (parallel to TaskDatty):**
- First inventory representative live pages and visitor journeys using Playwright/browser screenshots: homepage, navigation, buying comparisons, guides, About, Privacy, Disclosure, Contact, desktop and mobile. Expand into a complete URL census as value justifies. Classify issues by visitor harm and obviousness, not number of source changes.
- Consolidate the **highest-impact existing work first**, especially favicon #891 (superseding #769), verified/rights-appropriate visual candidates, user-visible contradictions, duplicated figures, and unfinished buyer comparisons. A merged placeholder fallback is **not** equivalent to a finished image solution.
- Produce a **small number of coherent batches** (sitewide visual/brand consistency; buyer trust and pricing; short consent and intelligible trust/legal pages with separate approvals), rather than dozens of unrelated cosmetic edits. Fix shared causes, not one symptom/page at a time.
- Each candidate carries: visitor problem, before screenshots/URLs, target after-state, exact source and media provenance, affected pages, tradeoffs, independent review, mobile/desktop after screenshots, release eligibility, and proof of deployed effect.
- Where legal/privacy/scripts/assets/multi-page structural changes are outside current unattended release policy, prepare an accurate independent-reviewed candidate and identify the *specific* legitimate authorized release path. Never use owner credentials in untrusted external agents or bypass protections.

**Track B — sustained autonomy accountability:** TaskDatty remains responsible for independently discovering, prioritizing, implementing, safely releasing within delegated scope, verifying public benefit, and continuing unattended. Its infrastructure work is justified only by a measured impediment to Track A outcomes. A separate external rescue is not proof that TaskDatty can do this itself.

## External-agent collaboration contract

This repository is public. Independent advanced agents may inspect current source and `https://offbeatinc.com`, cross-check official vendor evidence, design a correction, run Playwright and create **separate nonoverlapping branches/PRs** with GitHub least privilege (read-only first; repository-scoped PR write only if necessary). Do not grant access to private TaskDatty/Forgotten-Value repos, production credentials, or protected release identity to achieve a website result. Do not request agent-created workflow automation or self-approval.

Use 2–3 complementary perspectives at first: (1) adversarial visitor/visual and content audit, (2) implementation of already evidenced high-value fixes, (3) independent product/rights/factual review. They must not all rewrite the same pages. Share findings by issue/PR links and evidence, not chat transcripts. Always reconcile against live main and existing open PRs; stop producing duplicate plans/PRs.

## Scoring and prioritization

Prefer the task with the largest **verified reduction in visitor harm or confusion per elapsed day and owner minute**. Prioritize wrong-product heroes, misleading purchase advice, broken journeys, accessibility/mobile faults, consumer trust and obvious production polish over tags, metadata, rote single-sentence edits and new architecture. Avoid any reward based solely on PR count, model-hours, CI passes, or documents.

**Stop drift immediately** when work becomes another automation platform, redundant audit report, stale-branch rebase marathon, unnecessary full-site rewrite, or screenshot collection without direct correction/delivery. Complete a visible result or state the concrete release blocker and move to another authorized high-impact objective.
