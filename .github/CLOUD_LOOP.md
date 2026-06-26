# DatBotty v3 — Cloud Autonomous Loop (plan + audit only)

This GitHub Actions loop is the **cloud planning/audit surface** for DatBotty v3.
Under the Hermes-first architecture (see the v3 Execution Architecture ADR), it
runs on Actions — a proven scheduler — so planning/auditing no longer depends on
the local machine. **It does NOT execute or publish website changes.**

It lives in **offbeat-website** because this repo is public (unlimited free
Actions minutes) and is the site being maintained. All tooling is under
`.github/` so it never affects the published site.

## Architecture (Hermes-first)

- **Cloud loop (this):** autonomously improves/extends the Notion plans + Approved
  Work Queue and audits that the local Hermes engine is shipping 24/7. It writes
  only to Notion. It NEVER commits to the site and makes only minimal, paced
  free-LLM calls.
- **Local Hermes** (`github.com/CrashyCrash/datbotty-hermes`, runtime `~/.hermes`):
  the ONLY actor that makes real site changes — it reads the Approved Work Queue,
  edits + commits to this repo on free models, and ships autonomously within
  bounded safety rules. No per-task human approval; the gate is reserved for rare
  high-risk actions only.
- **Prefect / Temporal / LangGraph:** rejected as orchestrators.

## What it is

- **Workflow:** `.github/workflows/datbotty-autonomous-loop.yml`
- **Entrypoint:** `.github/scripts/cloud_autonomous_loop.py` (stdlib only; one cycle
  per tick via `--once`)
- **Schedule:** SLOW cadence (hourly or less). Do NOT self-trigger every few
  seconds — that floods the Cycle Log and wastes runner minutes.

## What each cycle does

1. **Plan/audit:** improve the Notion plans + queue; run the 129-page site audit;
   report gaps (e.g. pages missing GA4, formatting bugs) and whether Hermes has
   shipped recently.
2. **Free-model canary:** lightweight + infrequent, rotating the free Gemini
   models so it never burns strong-model quota.
3. **Cycle-log hygiene:** never write a bare heartbeat every few seconds; collapse
   heartbeat-only cycles into one hourly summary and keep the Cycle Log page short.

## Setup (secrets)

Under **Settings → Secrets and variables → Actions**:

| Name | Type | Purpose |
|------|------|---------|
| `NOTION_TOKEN` | secret | Read the approved-work queue and write plan/audit results |
| `GEMINI_API_KEY` (+ other free providers) | secret | Free-model canary / plan assistance |

`GITHUB_TOKEN` is provided automatically.

## Explicitly NOT this loop's job

- Publishing or committing site changes (that is Hermes).
- Raising workflow permissions to `contents: write` for autonomous site edits.
- Heavy per-cycle LLM usage.
