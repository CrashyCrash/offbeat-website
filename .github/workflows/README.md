# Workflows

No autonomous DatBotty v2/v3 workflows are active here.

Do not restart the old scheduled DatBotty v2/v3/v4 engineering loops;
their worker/reviewer provenance is incompatible with current TaskDatty.

**Narrow owner-authorized exception (October 13, 2026):** the GitHub-hosted
`tdq-signed-local-release.yml` is a SCHEDULED VERIFIER/RELEASE GATE, not an
autonomous engineering worker or a replacement orchestrator. It processes only
an existing K11-issued single-page draft already independently reviewed by
the isolated local reviewer OS account with a verifiable Ed25519 signature.
GitHub independently rechecks the exact current head/base, restricted HTML
content, signed review, active native branch policy enforced on a **non-bypass
GitHub Actions merge identity**, and actual Pages
publishing source before any native merge. It never invents or implements
tasks, does not execute candidate code, and never bypasses legacy protection.
The old DatBotty statuses remain required until independently proven TDQ
contexts support an explicitly authorized ruleset migration. The existing
owner's emergency GitHub bypass permission is preserved: it is not a license
for the autonomous Actions bot to bypass the ruleset, which must report
`current_user_can_bypass=never`. Do not require GitHub Actions to access the
administration-only list of all owner recovery actors. Multi-page,
functionality, product claims, credentials, WordPress and unverified content
are not authorized for unattended release.

Any signed-review expiry, missing key, publisher failure or mismatch blocks
publication; green syntax tests or source integrity alone never approve copy.

GitHub-managed entries such as Pages deployment, Dependabot, or Copilot may
appear in `gh workflow list`; those are not repo-authored workflow files. The
rule here is that `.github/workflows/` must not contain DatBotty autonomous loop
YAML during recovery.

## TDQ read-only draft checks (activated in source, 2026-10-12)

Offbeat PR #806 merged a GitHub-hosted `pull_request` workflow
`tdq-draft-triage.yml` for **draft** `tdq/proof-auto-*` source candidates.
Unlike the historical DatBotty autonomous loop, it creates no tasks, starts
no model worker, never mutates a PR, never merges, and never deploys.
It checks the single changed HTML source path, preserves executable/affiliate
link surfaces, and flags newly added facts/prices for **independent** review.
It runs on a trusted base checkout with a read-only token and never executes
candidate branch code. Source checks are NOT semantic approval.

The workflow is now present on `main` with read-only permissions, so
qualifying same-repository future `tdq/proof-auto-*` draft PR events can
trigger independent static triage. Existing earlier drafts are NOT
retroactively checked until an eligible new event. A successful tdq run
has NOT yet been observed, and this checker never grants semantic approval. See private TaskDatty #65 for a source-outcome/status readout
and TaskDatty PR #68 for proposed K11 progress samples and faster cadence.
