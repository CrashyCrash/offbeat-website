# Offbeat Arena development — 2026-10-27 owner review and exact preview

**Source under review:** [Crashicorn/offbeat-website PR #10](https://github.com/Crashicorn/offbeat-website/pull/10), branch `arena/849667ed-offbeat-website`, commit `21bb497833f4309facda1e968ecc4d4e14a79657`. This is a cumulative *fork development* candidate stacked on PR #9 and earlier Arena work. It **is not deployed on `CrashyCrash/offbeat-website` or offbeatinc.com**. Never assume fork GitHub Pages publishes that same SHA without checking its actual deployed source.

## Owner: how to see the actual new website

Open `/home/igpu/Desktop/AI-Projects/fv-campaign-20261026/OPEN-MY-PROJECTS.html` on K11. The October 27 corrected version puts site links at top; if the local checkout is stale, run `git pull --ff-only` in that checkout.

**Simplest one-command local preview:**

```bash
cd /home/igpu/Desktop/AI-Projects/fv-campaign-20261026
git pull --ff-only
bash tools/open-offbeat-pr10-preview.sh
```

The helper checks that GitHub's actual PR #10 HEAD matches the exact reviewed SHA, adds a separate read-only-intent worktree without changing original repo branches, starts a loopback-only static server, and opens Rig Studio. On the K11 (only after the script succeeds):

- [Rig Studio](http://127.0.0.1:8878/build-your-dj-setup.html)
- [New speaker connection planner](http://127.0.0.1:8878/best-dj-monitor-speakers.html)
- [Beginner controller choice](http://127.0.0.1:8878/best-dj-controllers-for-beginners.html)
- [Headphone guide](http://127.0.0.1:8878/best-dj-headphones-2026.html)

The server is nonproduction, local to K11, and should not be mistaken for a public Pages deployment. If the helper cannot verify HEAD or a port is occupied, it stops instead of silently displaying unrelated bytes.

Independent QA: [Forgotten-Value campaign review](https://github.com/CrashyCrash/Forgotten-Value/blob/campaign/overnight-20261026/projects/offbeat-website/evidence/offbeat-pr10-acceptance-20261027/VERDICT.md) and [test ledger](https://github.com/CrashyCrash/Forgotten-Value/blob/campaign/overnight-20261026/projects/offbeat-website/evidence/offbeat-pr10-acceptance-20261027/TESTS.md). Its author-suite count is **7/8**, not 8/8. The failing `tests/test_buying_journeys.js:163` expects a second DM-40D pair to cost +$149 while the implementation adds a $12 additional cable (+$161). The test expectation needs to be reconciled with physical signal topology. The independent Chromium review is useful evidence; the owner has not visually approved this cumulative site for publication.

## Integration conditions

1. **Clarify signal distribution for 2 × DM-40D pairs or any multi-pair configuration.** Two pairs may need extra outputs, splitting or an active distribution stage, not just an extra cable. Determine the actual controller's output count/routing and how a second stereo signal reaches both pairs; do not bill or draw unprovided hardware as connected. Differentiate "extra cable physically attached" from "plausible connection path." The model should say unavailable/needs distribution when appropriate, with truthful cost or allowance; add actual browser tests.
2. Reconcile the stale author test and verify all appropriate suites on the exact integration SHA, including proper assets and browser interactions.
3. Independently review the actual Rig Studio, speaker planner, software matrix and guide UI at desktop/mobile sizes with the owner's MacBook/real browser if useful. Re-check model identity, prices, rights/attribution and product specifications before publication.
4. **Do not bulk merge stacked Arena branches into production** until their ancestry, existing protected offbeatinc.com behavior, missing images, editorial claims, analytics/consent and external links have undergone selective regression review. No production release authorized by this document.
5. Favor visitor-visible buying reliability and authentic model-matched photographs, not another TaskDatty architecture project or test-count-driven editorial polish.

## Separate overnight records

The broader Oct 26–27 local-Qwen run produced a playable music audition and a nonproduction AfterLotto candidate review, but the owner found **most navigation links broken in the dashboard-linked :8002 older preview**. The user has asked to correct those other project records and then **focus this conversation exclusively on Offbeat**. Avoid importing an AfterLotto acceptance claim into Offbeat release gates or starting unrelated campaigns.
