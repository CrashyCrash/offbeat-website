# Offbeat DJ Website Boundary

**Status:** current public website checkout.

This repository is the clean canonical checkout for the current Offbeat DJ site.
It was cloned on 2026-07-31 from:

```text
https://github.com/CrashyCrash/offbeat-website.git
```

The previous local path
`/home/igpu/Desktop/AI Projects/DatBotty` was polluted with legacy automation
folders, an untracked `.env`, and a self-referential `offbeat-website` symlink.
That old root was moved to:

```text
/home/igpu/Desktop/AI Projects/_archive-2026-07-31/DatBotty-polluted-offbeat-website-root
```

Do not use the archived root, v2 folders, or v3 normalized-page folders for
current website development unless the user explicitly asks for forensic
comparison.

Boundary check:

```bash
git rev-parse --show-toplevel
git remote -v
git status -sb
find . -maxdepth 2 -name offbeat-website -print
```

Expected:

- Top level is `/home/igpu/Desktop/AI Projects/OffbeatDJ-Website`.
- Remote is `CrashyCrash/offbeat-website`.
- Working tree is clean before a task starts.
- The `find` command prints nothing.
