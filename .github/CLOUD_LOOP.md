# DatBotty v3 Cloud Loop - Disabled Historical Record

The old DatBotty v3 cloud planning/audit loop is disabled and must not be used
for DatBotty v4 recovery.

The former scheduled workflow was moved out of `.github/workflows/` to:

```text
.github/disabled-workflows/datbotty-v3-autonomous-loop.yml.disabled
```

The former Python entrypoint was moved out of `.github/scripts/` to:

```text
.github/disabled-workflows/cloud_autonomous_loop.py.disabled
```

Why:

- It belongs to the v3 Hermes/Notion architecture.
- It references old Notion/provider-secret plumbing.
- It can create project drift and confusion for v4 agents.
- v4 recovery requires deterministic local evidence, explicit approval gates,
  and no scheduled autonomous GitHub Actions control plane.
