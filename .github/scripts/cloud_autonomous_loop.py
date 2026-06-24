#!/usr/bin/env python3
"""DatBotty v3 - cloud autonomous loop (single tick).

Runs exactly one bounded, idempotent cycle inside GitHub Actions. This is the
cloud replacement for the local systemd timer + unattended runner. It has NO
dependency on the local machine or ~/.hermes; all configuration comes from
environment variables (wired to repo Actions secrets in the workflow).

Design notes:
* Mirrors the existing runtime convention: refuses to run without --once, so a
  scheduler (here, the Actions cron) fires it once per tick.
* Standard library only - no pip install step, fewer failure modes.
* Each cycle does real, verifiable, read-only useful work today (a free-model
  canary + a live offbeat-website audit). It never writes a bare heartbeat,
  which the Continuous Approved Work Charter forbids.
* Publish / Notion-queue consumption are the next step and activate only when
  the corresponding secrets are present. Until then those steps cleanly skip.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

OFFBEAT_OWNER = "CrashyCrash"
OFFBEAT_REPO = "offbeat-website"
GA4_ID = "G-9MG87ETLPT"
# Known post-restore formatting bug: this section renders full-width outside the
# content wrap, between the editorial-review card and the footer.
FORMATTING_BUG_MARKER = "full-width-section r27-buying-checkpoint"


def log(event, **fields):
    record = {"ts": datetime.now(timezone.utc).isoformat(), "event": event}
    record.update(fields)
    print(json.dumps(record, ensure_ascii=False), flush=True)


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def gh_headers():
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "datbotty-cloud-loop",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def provider_canary():
    """Confirm a free model is reachable. Skips cleanly if no key is configured."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        log("provider_canary_skipped", reason="OPENROUTER_API_KEY not set")
        return {"ok": None, "skipped": True}
    model = os.environ.get("FREE_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    try:
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": "Reply with the single word: OK"}],
                "max_tokens": 5,
            }
        ).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
                "User-Agent": "datbotty-cloud-loop",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
        reply = (data.get("choices", [{}])[0].get("message", {}).get("content", "") or "").strip()
        log("provider_canary_ok", model=data.get("model", model), reply=reply[:40])
        return {"ok": True, "model": data.get("model", model), "reply": reply}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        log("provider_canary_failed", status=exc.code, error=detail)
        return {"ok": False, "status": exc.code, "error": detail}
    except Exception as exc:
        log("provider_canary_failed", error=str(exc)[:200])
        return {"ok": False, "error": str(exc)[:200]}


def audit_site(sample_limit=40):
    """Read-only audit of the live offbeat-website repo for known gaps."""
    tree_url = (
        "https://api.github.com/repos/"
        + OFFBEAT_OWNER + "/" + OFFBEAT_REPO + "/git/trees/main?recursive=1"
    )
    tree = json.loads(_get(tree_url, headers=gh_headers()).decode())
    html_files = [
        node["path"]
        for node in tree.get("tree", [])
        if node.get("type") == "blob" and node["path"].endswith(".html")
    ]
    sample = html_files[:sample_limit]
    missing_ga4 = []
    formatting_bug = []
    for path in sample:
        raw_url = (
            "https://raw.githubusercontent.com/"
            + OFFBEAT_OWNER + "/" + OFFBEAT_REPO + "/main/" + path
        )
        try:
            html = _get(raw_url, headers={"User-Agent": "datbotty-cloud-loop"}).decode(
                "utf-8", "replace"
            )
        except Exception as exc:
            log("audit_fetch_failed", path=path, error=str(exc)[:120])
            continue
        if GA4_ID not in html:
            missing_ga4.append(path)
        if FORMATTING_BUG_MARKER in html:
            formatting_bug.append(path)
    scorecard = {
        "html_files_total": len(html_files),
        "sampled": len(sample),
        "sample_missing_ga4": len(missing_ga4),
        "sample_formatting_bug": len(formatting_bug),
        "examples_missing_ga4": missing_ga4[:5],
        "examples_formatting_bug": formatting_bug[:5],
    }
    log("site_audit_scorecard", **scorecard)
    return scorecard


def main():
    parser = argparse.ArgumentParser(description="DatBotty v3 cloud autonomous loop (one tick).")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run exactly one cycle. Required (a scheduler fires this per tick).",
    )
    args = parser.parse_args()
    if not args.once:
        print("refusing to run without --once", file=sys.stderr)
        return 2

    log("cycle_start", runner="github-actions-cloud-loop")
    result = {"provider": None, "audit": None}
    result["provider"] = provider_canary()
    try:
        result["audit"] = audit_site()
    except Exception as exc:
        log("site_audit_failed", error=str(exc)[:200])
        result["audit"] = {"error": str(exc)[:200]}

    if not os.environ.get("NOTION_TOKEN"):
        log("queue_consumption_skipped", reason="NOTION_TOKEN not set")

    try:
        with open("loop-scorecard.json", "w", encoding="utf-8") as handle:
            json.dump({"ts": datetime.now(timezone.utc).isoformat(), **result}, handle, indent=2)
    except Exception:
        pass

    log("cycle_end", status="ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
