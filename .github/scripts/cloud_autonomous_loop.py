#!/usr/bin/env python3
"""DatBotty v3 - cloud autonomous loop (single tick).

Runs exactly one bounded, idempotent cycle inside GitHub Actions. This is the
CLOUD surface for PUBLIC, no-secret-exposure work only (today: offbeat-website).
It has NO dependency on the local machine or ~/.hermes. Private/local execution,
scheduling, memory and learning remain Hermes' job (see the v3 Execution
Architecture ADR). GitHub Actions complements Hermes across the public/private
boundary; it does not replace it.

Design notes:
* Refuses to run without --once, so the Actions cron fires it once per tick.
* Standard library only - no pip install step, fewer failure modes.
* Each cycle does real, verifiable work: a free-model canary (Gemini-first per
  model policy), a FULL live offbeat-website audit, consumption of the Notion
  Approved Work Queue, and a bounded control-plane evidence write-back.
* Read-only against the WEBSITE today. Publishing website files activates only
  when the workflow is raised to contents:write under bounded per-task approval
  (Gate A). Writing evidence to the Notion control plane is expected loop
  bookkeeping (Continuous Approved Work Charter) and touches no website files.
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

# Free-model priority (Tammy policy): Google/Gemini free FIRST, then OpenRouter
# free models, then other free providers. Ollama is an absolute last resort and
# is intentionally NOT used in this cloud surface.
GEMINI_MODEL = "gemini-1.5-flash"
OPENROUTER_FREE_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


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


def _try_gemini(key):
    """Google Gemini free tier - preferred provider per model policy."""
    model = os.environ.get("GEMINI_MODEL", GEMINI_MODEL)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + model + ":generateContent?key=" + key
    )
    body = json.dumps(
        {"contents": [{"parts": [{"text": "Reply with the single word: OK"}]}]}
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "datbotty-cloud-loop"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    reply = ""
    try:
        reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        reply = ""
    return {"ok": True, "provider": "gemini", "model": model, "reply": reply[:40]}


def _try_openrouter(key):
    """Try free OpenRouter models in priority order; 429 is soft (rate-limited)."""
    models = []
    preferred = os.environ.get("FREE_MODEL")
    if preferred:
        models.append(preferred)
    for m in OPENROUTER_FREE_MODELS:
        if m not in models:
            models.append(m)
    rate_limited = 0
    last_error = None
    for model in models:
        if not model:
            continue
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
            reply = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            ).strip()
            return {
                "ok": True,
                "provider": "openrouter",
                "model": data.get("model", model),
                "reply": reply[:40],
            }
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:160]
            last_error = {"status": exc.code, "error": detail, "model": model}
            if exc.code == 429:
                rate_limited += 1
            continue
        except Exception as exc:
            last_error = {"error": str(exc)[:160], "model": model}
            continue
    return {
        "ok": False,
        "rate_limited": rate_limited,
        "tried": len([m for m in models if m]),
        "last_error": last_error,
    }


def provider_canary():
    """Confirm a free model is reachable, Gemini-first. Soft on rate limits."""
    gem = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gem:
        try:
            res = _try_gemini(gem)
            log("provider_canary_ok", provider="gemini", model=res.get("model"), reply=res.get("reply"))
            return res
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:160]
            log("provider_canary_gemini_error", status=exc.code, error=detail)
        except Exception as exc:
            log("provider_canary_gemini_error", error=str(exc)[:160])
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        if not gem:
            log("provider_canary_skipped", reason="no GEMINI_API_KEY or OPENROUTER_API_KEY set")
            return {"ok": None, "skipped": True}
        log("provider_canary_failed", reason="gemini error and no OPENROUTER_API_KEY fallback")
        return {"ok": False}
    res = _try_openrouter(key)
    if res.get("ok"):
        log("provider_canary_ok", provider="openrouter", model=res.get("model"), reply=res.get("reply"))
        return res
    if res.get("rate_limited"):
        # Non-fatal: free models are rate-limited upstream, not a real failure.
        log(
            "provider_canary_rate_limited",
            tried=res.get("tried"),
            rate_limited=res.get("rate_limited"),
            note="all free OpenRouter models 429; set GEMINI_API_KEY for higher free quota",
        )
        return {"ok": None, "rate_limited": True, "tried": res.get("tried")}
    log("provider_canary_failed", **(res.get("last_error") or {}))
    return res


def audit_site(max_files=300):
    """Read-only audit of EVERY live offbeat-website HTML page for known gaps."""
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
    missing_ga4 = []
    formatting_bug = []
    checked = 0
    for path in html_files[:max_files]:
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
        checked += 1
        if GA4_ID not in html:
            missing_ga4.append(path)
        if FORMATTING_BUG_MARKER in html:
            formatting_bug.append(path)
    scorecard = {
        "html_files_total": len(html_files),
        "checked": checked,
        "missing_ga4_count": len(missing_ga4),
        "formatting_bug_count": len(formatting_bug),
        "examples_missing_ga4": missing_ga4[:12],
        "examples_formatting_bug": formatting_bug[:12],
        "missing_ga4": missing_ga4,
        "formatting_bug": formatting_bug,
    }
    log(
        "site_audit_scorecard",
        html_files_total=len(html_files),
        checked=checked,
        missing_ga4_count=len(missing_ga4),
        formatting_bug_count=len(formatting_bug),
        examples_missing_ga4=missing_ga4[:12],
        examples_formatting_bug=formatting_bug[:12],
    )
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
    """Read the Notion Approved Work Queue (read-only) and return actionable rows."""
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
                    "id": row.get("id"),
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
            tasks=[{k: v for k, v in t.items() if k != "id"} for t in tasks],
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


def _patch_page(token, page_id, properties):
    body = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages/" + page_id,
        data=body,
        headers=_notion_headers(token),
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def write_evidence(token, tasks, audit):
    """Write this cycle's evidence + Last run to each read_only task row.

    BOUNDED write to the Notion CONTROL PLANE only (allowed by the Charter).
    Touches NO website files - those stay behind Gate A. Fails soft so the
    proven read path never regresses.
    """
    now = datetime.now(timezone.utc)
    a = audit if isinstance(audit, dict) else {}
    base = (
        "Cloud loop " + now.strftime("%Y-%m-%d %H:%M UTC")
        + " | pages " + str(a.get("checked", "?")) + "/" + str(a.get("html_files_total", "?"))
        + " | GA4 missing: " + str(a.get("missing_ga4_count", "?"))
        + " | formatting-bug pages: " + str(a.get("formatting_bug_count", "?"))
    )
    wrote = 0
    errors = []
    for t in tasks:
        if t.get("tier") != "read_only" or not t.get("id"):
            continue
        ttype = t.get("type")
        if ttype == "site_audit":
            ev = base + ". Missing GA4: " + (", ".join(a.get("missing_ga4", [])[:10]) or "none")
        elif ttype == "link_audit":
            ev = base + ". Formatting-bug pages: " + (", ".join(a.get("formatting_bug", [])[:10]) or "none")
        else:
            ev = base
        props = {
            "Result / Evidence": {"rich_text": [{"type": "text", "text": {"content": ev[:1900]}}]},
            "Last run": {"date": {"start": now.isoformat()}},
        }
        try:
            _patch_page(token, t["id"], props)
            wrote += 1
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:160]
            errors.append({"id": t.get("id"), "status": exc.code, "error": detail})
        except Exception as exc:
            errors.append({"id": t.get("id"), "error": str(exc)[:160]})
    if errors:
        log("evidence_write_partial", wrote=wrote, errors=errors[:3],
            hint="if 403, grant the integration edit access on the queue DB")
    else:
        log("evidence_written", wrote=wrote)
    return {"wrote": wrote, "errors": errors}


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
    result = {"provider": None, "audit": None, "queue": None, "evidence": None}
    result["provider"] = provider_canary()
    try:
        result["audit"] = audit_site()
    except Exception as exc:
        log("site_audit_failed", error=str(exc)[:200])
        result["audit"] = {"error": str(exc)[:200]}
    result["queue"] = consume_queue()

    token = os.environ.get("NOTION_TOKEN")
    queue = result["queue"]
    if token and isinstance(queue, dict) and queue.get("ok") and queue.get("tasks"):
        try:
            result["evidence"] = write_evidence(token, queue["tasks"], result["audit"])
        except Exception as exc:
            log("evidence_write_failed", error=str(exc)[:200])

    try:
        with open("loop-scorecard.json", "w", encoding="utf-8") as handle:
            json.dump({"ts": datetime.now(timezone.utc).isoformat(), **result}, handle, indent=2)
    except Exception:
        pass

    log("cycle_end", status="ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
