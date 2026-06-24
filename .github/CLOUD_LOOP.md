# DatBotty v3 - Cloud Autonomous Loop

This is the **cloud replacement** for DatBotty v3's local systemd timer. It runs
on GitHub Actions - a proven scheduler - so the loop no longer depends on the
local machine, `~/.hermes`, or anyone running `systemctl`.

It lives in **offbeat-website** (not the private DatBotty-v3 repo) because this
repo is public (unlimited free Actions minutes) and is the site the loop
maintains, so it can later publish fixes to itself using the built-in token.
All tooling is under `.github/` so it never affects the published site.

## What it is

- **Workflow:** `.github/workflows/datbotty-autonomous-loop.yml` (add via the
  GitHub UI - see below)
- **Entrypoint:** `.github/scripts/cloud_autonomous_loop.py` (standard library
  only; runs one cycle per tick via `--once`, mirroring the existing convention)
- **Schedule:** hourly plus manual run

## Why this instead of local systemd

- The local `datbotty.timer` was never installed, and the unattended runner
  refuses to run without `--once` - so nothing was firing it.
- Actions is a managed cron with logs, retries, and artifacts built in. No
  custom supervisor scripts, no local box that has to stay awake.
- Every run is observable in the **Actions** tab and uploads a
  `loop-scorecard.json` artifact.

## What each cycle does today (zero setup required)

The loop never writes a bare heartbeat. With no secrets configured it still does
real, read-only useful work:

1. **Free-model canary** - skipped until `OPENROUTER_API_KEY` is set.
2. **Live site audit** - scans this repo for the two known post-restore gaps and
   reports counts + examples:
   - pages missing GA4 `G-9MG87ETLPT`
   - pages still carrying the `full-width-section r27-buying-checkpoint`
     formatting bug

## Add the workflow file (one time)

GitHub blocks automated pushes of workflow files without special scope, so add
it by hand: in the GitHub UI, **Add file -> Create new file**, name it
`.github/workflows/datbotty-autonomous-loop.yml`, paste the YAML provided in
chat, and commit to `main`.

## One-time setup to unlock more

Under **Settings -> Secrets and variables -> Actions**:

| Name | Type | Purpose |
|------|------|---------|
| `OPENROUTER_API_KEY` | secret | Enables the free-model canary (and later model-driven work) |
| `FREE_MODEL` | variable | Optional override of the free model id |
| `NOTION_TOKEN` | secret | Enables reading the approved-work queue and writing run results |

`GITHUB_TOKEN` is provided automatically; no action needed.

## Roadmap (next steps, in order)

1. **Queue consumption** - with `NOTION_TOKEN`, pull the next approved task from
   the Notion work queue each cycle instead of only auditing.
2. **Publishing** - raise the workflow `permissions:` from `contents: read` to
   `contents: write`, then apply approved fixes to this repo and record a
   Published Value row, with rollback.
3. **Throughput** - batch multiple approved tasks per cycle toward the Gate B
   target once the publish path is proven safe.
