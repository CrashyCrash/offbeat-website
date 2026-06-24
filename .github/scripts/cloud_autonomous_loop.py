#!/usr/bin/env python3
"""DatBotty v3 - cloud autonomous loop (single tick).

Runs exactly one bounded, idempotent cycle inside GitHub Actions. This is the
CLOUD surface for PUBLIC, no-secret-exposure work only (today: offbeat-website).
It has NO dependency on the local machine or ~/.hermes. Private/local execution,
scheduling, memory and learning remain Hermes' job (see the v3 Execution
Architecture ADR). GitHub Actions does not replace Hermes; it complements it
across the public/private boundary.

Design notes:
* Refuses to run without --once, so a scheduler (the Actions cron) fires it once
  per tick.
* Standard library only - no pip install step, fewer failure modes.
* Each cycle does real, verifiable work: a free-model canary, a live
  offbeat-website audit, and consumption of the Notion Approved Work Queue.
  It never writes a bare heartbeat (forbidden by the Continuous Approved Work
  Charter).
* Read-only today. Publishing activates only when the workflow is raised to
  contents:write under bounded per-task approval (Gate A).
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
# Notion control plane: the consumable work queue (matched by title substring).
QUEUE_DB_NAME = "Approved Work Queue"
NOTION_VERSION = "2022-06-28"


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


def _notion_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "datbotty-cloud-loop",
    }


def _rich(parts):
    return "".join(p.get("plain_text", "") for p in (parts or []))


def _select(prop):
    val = (prop or {}).get("select")
    return val.get("name") if val else None


def consume_queue():
    """Read the Notion Approved Work Queue (read-only).

    Finds the queue database by title, pulls rows where Status=Approved AND
    Approved-by-Tammy is checked, and reports them. The cloud loop only ACTS on
    read_only-tier tasks today; bounded_write/publish tasks are reported as
    pending capability (Gate A) so nothing silently stalls.
    """
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        log("queue_consumption_skipped", reason="NOTION_TOKEN not set")
        return {"skipped": True}
    headers = _notion_headers(token)
    try:
        search_body = json.dumps(
            {"query": QUEUE_DB_NAME, "filter": {"property": "object", "value": "database"}}
        ).encode()
        req = urllib.request.Request(
            "https://api.notion.com/v1/search", data=search_body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            results = json.loads(resp.read().decode()).get("results", [])
        db_id = None
        for item in results:
            title = _rich(item.get("title"))
            if QUEUE_DB_NAME in title:
                db_id = item.get("id")
                break
        if not db_id:
            log("queue_db_not_found", hint="share the queue DB with the integration")
            return {"ok": False, "reason": "queue database not found / not shared"}
        query_body = json.dumps(
            {
                "filter": {
                    "and": [
                        {"property": "Status", "status": {"equals": "Approved"}},
                        {"property": "Approved by Tammy", "checkbox": {"equals": True}},
                    ]
                },
                "page_size": 25,
            }
        ).encode()
        req = urllib.request.Request(
            "https://api.notion.com/v1/databases/" + db_id + "/query",
            data=query_body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            rows = json.loads(resp.read().decode()).get("results", [])
        tasks = []
        for row in rows:
            props = row.get("properties", {})
            tasks.append(
                {
                    "task": _rich((props.get("Task", {}) or {}).get("title")),
                    "type": _select(props.get("Task Type")),
                    "target": _rich((props.get("Target", {}) or {}).get("rich_text")),
                    "tier": _select(props.get("Safety Tier")),
                    "priority": _select(props.get("Priority")),
                    "gate": _select(props.get("Gate")),
                }
            )
        actionable = [t for t in tasks if t.get("tier") == "read_only"]
        log(
            "queue_consumed",
            approved=len(tasks),
            read_only_actionable=len(actionable),
            tasks=tasks,
        )
        return {
            "ok": True,
            "approved": len(tasks),
            "read_only_actionable": len(actionable),
            "tasks": tasks,
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:200]
        log("queue_consumption_failed", status=exc.code, error=detail)
        return {"ok": False, "status": exc.code, "error": detail}
    except Exception as exc:
        log("queue_consumption_failed", error=str(exc)[:200])
        return {"ok": False, "error": str(exc)[:200]}


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
    result = {"provider": None, "audit": None, "queue": None}
    result["provider"] = provider_canary()
    try:
        result["audit"] = audit_site()
    except Exception as exc:
        log("site_audit_failed", error=str(exc)[:200])
        result["audit"] = {"error": str(exc)[:200]}
    result["queue"] = consume_queue()

    try:
        with open("loop-scorecard.json", "w", encoding="utf-8") as handle:
            json.dump({"ts": datetime.now(timezone.utc).isoformat(), **result}, handle, indent=2)
    except Exception:
        pass

    log("cycle_end", status="ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
