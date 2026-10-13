# Workflows

No autonomous DatBotty v2/v3 workflows are active here.

Do not add scheduled autonomous workflows during DatBotty v4 recovery. v4 work
must be driven by the evidence-and-approval loop in
`/home/igpu/Desktop/AI Projects/DatBotty-v4`.

GitHub-managed entries such as Pages deployment, Dependabot, or Copilot may
appear in `gh workflow list`; those are not repo-authored workflow files. The
rule here is that `.github/workflows/` must not contain DatBotty autonomous loop
YAML during recovery.

## Proposed TDQ read-only draft checks (2026-10-12)

Offbeat draft PR #806 proposes a GitHub-hosted `pull_request` workflow
`tdq-draft-triage.yml` for **draft** `tdq/proof-auto-*` source candidates.
Unlike the historical DatBotty autonomous loop, it creates no tasks, starts
no model worker, never mutates a PR, never merges, and never deploys.
It checks the single changed HTML source path, preserves executable/affiliate
link surfaces, and flags newly added facts/prices for **independent** review.
It runs on a trusted base checkout with a read-only token and never executes
candidate branch code. Source checks are NOT semantic approval.

This workflow is **not active** merely because it appears in this draft
branch. It must be separately reviewed and merged into the default branch.
Existing earlier drafts will not be retroactively checked without a new
eligible event. See private TaskDatty #65 for a source-outcome/status readout
and TaskDatty PR #68 for proposed K11 progress samples and faster cadence.
