# Offbeat DJ Website Agent Instructions

> **Binding product-quality reset — October 24, 2026.** Read [docs/SITE-PRODUCT-QUALITY-RECOVERY-20261024.md](docs/SITE-PRODUCT-QUALITY-RECOVERY-20261024.md) before choosing, implementing, reviewing or accepting website work. The principal deliverable is a demonstrably better **live visitor experience**; draft PRs, flawless image loading, green checks and runtime are intermediate evidence only. First reconcile existing work and assess actual desktop/mobile pages. Do not substitute generic placeholder pictures for appropriate imagery or present editorial instructions as copy. External agents may collaborate through independent scoped branches/PRs. Existing protected release, credentials, rights, and privacy controls remain binding.


This repository's protected `main` is the source for the public Offbeat website. Historical K11 local paths below are not requirements for external or sandboxed agents.

Historical K11 checkout path (validate the machine's actual checkout; external agents should use isolated clones or worktrees):

```text
/home/igpu/Desktop/AI Projects/OffbeatDJ-Website
```

Remote:

```text
https://github.com/CrashyCrash/offbeat-website.git
```

Rules:

- Do not use `/home/igpu/Desktop/AI Projects/DatBotty` as a website repo. That
  path is a `DO_NOT_USE` guard repo.
- Do not use v2 or v3 website folders as current source. They are historical
  archives only.
- Do not recreate nested `offbeat-website` folders or symlinks.
- Do not add autonomous GitHub Actions workflows.
- Do not store secrets in this public repo.
- Work on branches. Direct pushes to `main` require explicit user approval.
- Historical DatBotty v4 recovery notes (not the active product acceptance standard) live in
  `/home/igpu/Desktop/AI Projects/DatBotty-v4`.
