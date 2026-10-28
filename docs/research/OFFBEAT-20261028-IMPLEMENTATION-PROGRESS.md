# October 28 implementation progress — image and standalone research acted upon

The external Battle Mode/GLM research in [this draft docs PR #1045](https://github.com/CrashyCrash/offbeat-website/pull/1045) has produced two substantive **nonproduction** deliveries, rather than remaining only reports:

- **[Codex standalone buying guide PR #13](https://github.com/Crashicorn/offbeat-website/pull/13)**, DRAFT, exact head `0b730a1c278258953152e23e0cc8d0c847bc93b9`. Four scoped hardware guides + real-Chromium test and evidence; recovered the interrupted Qwen SC6000 partial diff. [Manufacturer/acceptance notes](https://github.com/CrashyCrash/offbeat-website/issues/1041). Source of truth still requires **one correction**: current [AlphaTheta XDJ-AZ product page](https://alphatheta.com/en/product/all-in-one-dj-system/xdj-az/black/) now expressly confirms Spotify StreamingDirectPlay with Spotify Premium on current firmware; do not overstate unresolved compatibility based on old v1.30 PDF.
- **[Arena photography PR #14](https://github.com/Crashicorn/offbeat-website/pull/14)**, OPEN, exact head `5c502b6ae8b0d1029490b3e609a1551f9420fe4d`. Three locally optimized/credited Pexels editorial photos from verified leads, accurate article hero placements, before/after mobile/desktop browser screenshots and hero mapping fixes. [Photo acquisition issue #1042](https://github.com/CrashyCrash/offbeat-website/issues/1042) still tracks exact-model photography and press-rights gaps; editorial scenes are not manufacturer product photos.

Both PRs target [the cumulative development PR #10](https://github.com/Crashicorn/offbeat-website/pull/10) at `f580788`. Neither is merged/deployed.

**Integration risk:** [Software advisor PR #12](https://github.com/Crashicorn/offbeat-website/pull/12) head `5ec3095` changes `dj-software-hub.html` in the same hero markup that photography PR #14 updates. **They are individually clean against #10, but a combined composition has not been tested.** Preserve both the real Pexels hero and the interactive software advisor; test merged behavior/asset loading before accepting a release. [Detailed durable progress and merge-recovery plan](https://github.com/CrashyCrash/Forgotten-Value/blob/main/projects/offbeat-website/evidence/OFFBEAT-2026-10-28-PR13-PR14-DELIVERY-AND-INTEGRATION.md).

Agent-reported on-K11/Arena Chromium tests are backed by committed source/evidence, but **no GitHub Actions workflow run or commit status was found** for the exact #13/#14 heads at review. No claim of independent CI acceptance.

**Owner decision left open:** visual/editorial approval, release-candidate reconciliation of #11–#14 and protected deployment. Do not merge automatically, alter production, or claim the entire website is now complete.
