# Image-recovery reconciliation — 2026-10-26

**Documentation-only research branch.** No live-site deployment or image usage rights are authorized by this file.

## Research source and actual recoverability

Temporarily reconnected historical Notion work showed a June-2026 image-research package for 106 Offbeat pages. The old fully embedded CSV and JSON each contain **116 image candidates**, with page target, source URL, attribution, license, suggested placement/crop, duplicate group, priority, and historic quality/rights confidence. The dataset is overwhelmingly editorial Unsplash/Pexels, not authentic exact-model product photography.

A June-21 update *claims* a **213-candidate** expansion (N001–N061, Q001–Q004, E001–E032 and further replacement entries), but the Notion page still embeds the **116-row CSV**. Its gallery explicitly says the latest 213-card HTML existed only in an old sandbox under `/data/image-research-complete/index.html`. Thus **213 is not a recoverable catalog until the actual missing file is located**; do not invent N/Q/E rows or use the prose number as coverage proof.

The 10-item Notion image execution queue had `Ready for Agent` and `Not Run` for every item on 2026-10-26. The approximately 100-image self-host task failed its single-page/single-asset scope gate and remained `Needs review`. This documents a failed historical path from research to production; later independent GitHub adoptions must be evaluated on their actual commits.

## Actual priority: real product images, not more generic cards

Candidate families that require validated source/license/model matching and, often, manufacturer permission:

- AlphaTheta/Pioneer: DDJ-FLX4, DDJ-FLX10, DDJ-FLX2, DDJ-GRV6, DDJ-400, CDJ-3000.
- inMusic: Rane ONE, Denon Prime Go, SC6000, Numark Scratch.
- Official software UI: Serato, Traktor, FL Studio, rekordbox, Ableton/djay where usage rights allow.
- Commons: genuine Technics SL-1200MK2 licensed historical candidate; a CDJ-2000 Commons image must **not** be misrepresented as a CDJ-3000.

Historic manufacturer image lists contain contact/request drafts; none establish granted reproduction rights. URL liveness, local possession, manufacturer host, and photographer attribution alone never establish permission.

Use an explicit `LEAD → URL_CHECKED → BINARY_LOCATED → PIXEL_MODEL_MATCHED → RIGHTS_VERIFIED → VISUAL_FIT_APPROVED → STAGED → DEPLOYED` ledger. Keep documentation and rejected leads in private Forgotten-Value; do not copy private Notion-only records or screenshots into this public site without review.

## Implementation and acceptance

1. On a separate K11 worktree, inspect existing local DatBotty-v3 image package and restored image binaries already indexed in Forgotten-Value. Before deleting old Trash, check preserved screenshot paths under `~/.local/share/Trash/files/offbeat-dj-website/NEW16/` without copying enormous trees.
2. Search backups/archives for the missing 213-row export and original research gallery, verifying row counts and hashes before treating it as a recovered artifact.
3. Select authentic, correctly identified, licensed, appealing images for the highest-traffic buying pages. Prefer a small set of visibly superior exact-model photographs over mass-generated diagrams.
4. Perform attribution and license audit; ensure no image falsely depicts the featured product.
5. Create a normal isolated development PR against the correct cumulative Arena branch, with desktop/mobile before-after images and exact per-asset source/rights trail.
6. Only after independently accepted results consider production cutover. Passing structural tests alone does not imply image quality, factual accuracy, licensing or complete visitor readiness.

**Caution:** The historical research status `ready-to-use` was assigned in June 2026 and is not sufficient 2026-10 release authorization. Preserve the original data and evidence before taking action.
