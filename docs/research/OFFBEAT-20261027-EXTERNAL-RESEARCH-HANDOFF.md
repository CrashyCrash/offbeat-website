# Offbeat external research — actionable handoff (2026-10-27)

## Purpose

The owner commissioned five independent Battle Mode research prompts (two outputs each) and a separate GLM image lead report. Consolidated full-source audit, verified URLs, important contradictions and model-identification traps are in **[Forgotten-Value's reconciled research record](https://github.com/CrashyCrash/Forgotten-Value/blob/main/projects/offbeat-website/evidence/external-research-20261027/RECONCILED-FINDINGS.md)**.

The research did **not** modify any Offbeat HTML or authorize republishing manufacturers' images. It must not be characterized as implementing, fixing, deploying or independently accepting the development pages.

## Three focused engineering queues

1. **[#1042 — Authentic photographs + manufacturer press rights](https://github.com/CrashyCrash/offbeat-website/issues/1042).** Human-review-ready Commons source leads: exact [Allen & Heath Xone:96](https://commons.wikimedia.org/wiki/File:Allen_%26_Heath_Xone_96.jpg) (Vittjas Tief, CC BY-SA 4.0); true [Pioneer DDJ-RX with rekordbox](https://commons.wikimedia.org/wiki/File:Pioneer_DDJ-RX_DJ-Controller_(front)_with_computer_running_mixing_software_Rekordbox.jpg) (Jonn Leffmann, CC BY 3.0); [Le Badaboum nightclub booth](https://commons.wikimedia.org/wiki/File:Le_Badaboum_Paris_DJ_booth.jpg) (CC0); [Bob Beaman older-CDJ club booth](https://commons.wikimedia.org/wiki/File:DJ_booth_with_DJ-Mixer,_two_turntables_and_two_CDJ-players_in_former_Bob_Beaman_nightclub_in_Munich.jpg) (CC BY 2.0). Verify full file pages, exact alt text, credits and intended context before import. Do not use Club Booth as model-specific PRIME 4+, or ambiguous Commons KRK photo as exact G4. Official [inMusic press contact](https://www.inmusicbrands.com/press/) is `inmusic@jessuppr.com`; contact, **not permission**.
2. **[#1043 — Live-site buying correctness](https://github.com/CrashyCrash/offbeat-website/issues/1043).** External audit observed live FLX4/FLX6 ports and buying-link mismatches, unsupported jog-adjustment claims, Lite Stems upsell, ATH-M50x measurement confusion, and conflicting software pricing. Independent primary-source checks: [FLX4 official mic input](https://www.pioneerdj.com/en/product/dj-controllers/ddj-flx4/), [FLX6-GT actual input inventory](https://www.pioneerdj.com/en/news/2022/ddj-flx6-gt-4-channel-dj-controller-for-multiple-dj-applications/), [Serato DJ Lite Stems](https://support.serato.com/hc/en-us/articles/5852995594511-Stems-with-Serato-DJ-Lite), and [ATH-M50x 99 dB/mW sensitivity](https://www.audio-technica.com.hk/index.php?lang=eng&op=productdetails&pid=927). Reproduce exact current page/link before fixing. **Public offbeatinc.com is not the cumulative Arena development preview**; check prior PR ancestry and avoid duplicating implemented changes.
3. **[#1044 — Affiliate second-retailer and image-rights route](https://github.com/CrashyCrash/offbeat-website/issues/1044).** [zZounds official program](https://www.zzounds.com/info/aff) and [FAQ](https://www.zzounds.com/aff--faq) offer default 6% referral/45-day cookie; **owner enrollment unknown**. Current Amazon catalog API is [Creators API](https://affiliate-program.amazon.com/creatorsapi/docs/) and [PA-API 5 is deprecated](https://affiliate-program.amazon.com/creatorsapi/docs/en-us/paapiv5-deprecation). No owner-private affiliate credentials, account approvals, product feed grants or permission to use specific merchant photos were supplied. The reports' blank source citations / prior-version assumptions do not create rights.

## External agent report quality — do not silently promote guesses

| Source files | Use | Failures |
|---|---|---|
| `1A` / `1B` | Manufacturer permission leads | Search quotas stopped investigations early; general corporate terms do not prove a blanket prohibition on every media/affiliate use |
| `2A` / `2B` | Model-specific Commons candidates | Xone:96 corroborated; `2A` speculates KRK G4 identity and some complete Commons file URLs are missing |
| `3A` / `3B` | Generic editorial hero leads | `3A` delivers **no working original/download URLs** in its candidate descriptions; `3B` did not inspect all photos or their image dimensions |
| `4A` / `4B` | Affiliate/retailer opportunities | `4A` references obsolete PA-API 5 for new work; `4B` has numerous **blank citation destinations**, so confirm official programs individually |
| `5A` / `5B` | Live buying-path errors | `5A` used actual page routes; `5B` used only short search excerpts and couldn't click any links; its inferred missing pages/phantom products are NOT proven |
| GLM `OFFBEAT-PRODUCT-IMAGE-LEADS.md` | Commons editorial image discovery + publisher contacts | Model/generation false-identity traps are valuable; "no open-license priority-model image exists anywhere" goes beyond finite searches; no blanket media approval |

## Required acceptance before using anything

- Every exact-product image requires verified photographer/source, full-resolution rights evidence, exact **model and generation**, proper caption, modification/share-alike treatment, and a useful placement on the actual reviewed source branch. Generic licensed club photos are editorial context **only**.
- Every buyer-defect fix needs a reproducible wrong claim or actual wrong retailer destination and its manufacturer reference. No mass-copy rewrite, fake testing or superficial badges.
- Every affiliate link requires authenticated owner enrollment/approval, exact product destination, clear disclosure and compliance with its current retailer agreement. No invented programs or prices.
- No automatic merges to production, no new TaskDatty/Arena controllers. Existing [PR #10](https://github.com/Crashicorn/offbeat-website/pull/10), [PR #11](https://github.com/Crashicorn/offbeat-website/pull/11), [PR #12](https://github.com/Crashicorn/offbeat-website/pull/12) remain separately reviewable; PR #12 has moved since original recovery so verify current SHA at execution time.

**This is a documentation-only review PR.** The interrupted OpenCode task is intentionally deferred until the owner finishes triaging the external research.
