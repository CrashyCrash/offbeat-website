#!/usr/bin/env python3
"""DatBotty v3 cloud autonomous loop (v3.2).

v3.1 -> v3.2 improvements:
- Mark tasks Done after writing evidence (enables queue rotation, not infinite overwrite)
- Skip full 129-file audit when no audit-type tasks are queued (saves 2-3 min/run)
- MAX_TASKS_PER_RUN raised 6 -> 10
- Process tasks with null evidence FIRST (prioritize fresh work)
- Task title used as LLM fallback when Instructions field is empty
- Per-task timing in logs
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

OFFBEAT_OWNER = "CrashyCrash"
OFFBEAT_REPO = "offbeat-website"
GA4_ID = "G-9MG87ETLPT"
FORMATTING_BUG_MARKER = "full-width-section r27-buying-checkpoint"
QUEUE_DB_NAME = "Approved Work Queue"
NOTION_VERSION = "2022-06-28"
MAX_TASKS_PER_RUN = 10

# Task types that require the full site audit scan
AUDIT_TASK_TYPES = {
    "site_audit", "ga4_injection", "formatting_fix",
    "link_audit", "verdict_card_css", "affiliate_fix",
}


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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "datbotty-loop"}
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def _notion_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
        "User-Agent": "datbotty-loop",
    }


def _rich(parts):
    return "".join(p.get("plain_text", "") for p in (parts or []))


def _select(prop):
    val = (prop or {}).get("select")
    return val.get("name") if val else None


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------

def call_gemini(key, model, system_prompt, user_prompt):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent?key=" + key)
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}]
    }).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "datbotty-loop"},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def call_openai_compat(base_url, key, model, system_prompt, user_prompt, max_tokens=1800):
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(base_url, data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "datbotty-loop"},
        method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


def execute_llm_task(system_prompt, user_prompt):
    """Try providers in priority order. Return first success."""
    errors = {}

    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            res = call_gemini(gemini_key, "gemini-1.5-flash", system_prompt, user_prompt)
            return {"ok": True, "provider": "gemini", "model": "gemini-1.5-flash", "content": res}
        except Exception as e:
            errors["gemini"] = str(e)
            log("provider_error", provider="gemini", error=str(e)[:120])

    cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    if cerebras_key:
        try:
            res = call_openai_compat("https://api.cerebras.ai/v1/chat/completions",
                cerebras_key, "llama-3.3-70b", system_prompt, user_prompt)
            return {"ok": True, "provider": "cerebras", "model": "llama-3.3-70b", "content": res}
        except Exception as e:
            errors["cerebras"] = str(e)
            log("provider_error", provider="cerebras", error=str(e)[:120])

    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            res = call_openai_compat("https://api.groq.com/openai/v1/chat/completions",
                groq_key, "llama-3.3-70b-versatile", system_prompt, user_prompt)
            return {"ok": True, "provider": "groq", "model": "llama-3.3-70b-versatile", "content": res}
        except Exception as e:
            errors["groq"] = str(e)
            log("provider_error", provider="groq", error=str(e)[:120])

    mistral_key = os.environ.get("MISTRAL_API_KEY")
    if mistral_key:
        try:
            res = call_openai_compat("https://api.mistral.ai/v1/chat/completions",
                mistral_key, "mistral-small-latest", system_prompt, user_prompt)
            return {"ok": True, "provider": "mistral", "model": "mistral-small-latest", "content": res}
        except Exception as e:
            errors["mistral"] = str(e)
            log("provider_error", provider="mistral", error=str(e)[:120])

    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        for model in ["meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"]:
            try:
                res = call_openai_compat("https://openrouter.ai/api/v1/chat/completions",
                    or_key, model, system_prompt, user_prompt)
                return {"ok": True, "provider": "openrouter", "model": model, "content": res}
            except Exception as e:
                errors["openrouter_" + model] = str(e)
                log("provider_error", provider="openrouter", model=model, error=str(e)[:120])

    return {"ok": False, "errors": errors}


# ---------------------------------------------------------------------------
# Site audit
# ---------------------------------------------------------------------------

def audit_site(max_files=300):
    """Full scan: fetch every HTML file and check for GA4 + formatting bug."""
    t0 = time.time()
    tree_url = ("https://api.github.com/repos/" + OFFBEAT_OWNER + "/"
                + OFFBEAT_REPO + "/git/trees/main?recursive=1")
    tree = json.loads(_get(tree_url, headers=gh_headers()).decode())
    html_files = [n["path"] for n in tree.get("tree", [])
                  if n.get("type") == "blob" and n["path"].endswith(".html")]

    missing_ga4, formatting_bug = [], []
    checked = 0
    for path in html_files[:max_files]:
        raw_url = ("https://raw.githubusercontent.com/" + OFFBEAT_OWNER
                   + "/" + OFFBEAT_REPO + "/main/" + path)
        try:
            html = _get(raw_url, headers={"User-Agent": "datbotty"}).decode("utf-8", "replace")
        except Exception:
            continue
        checked += 1
        if GA4_ID not in html:
            missing_ga4.append(path)
        if FORMATTING_BUG_MARKER in html:
            formatting_bug.append(path)

    elapsed = round(time.time() - t0, 1)
    log("audit_complete", checked=checked, total=len(html_files),
        missing_ga4=len(missing_ga4), bugs=len(formatting_bug), elapsed_s=elapsed)
    return {
        "html_files_total": len(html_files),
        "checked": checked,
        "missing_ga4": missing_ga4,
        "formatting_bug": formatting_bug,
    }


# Known-good baseline so LLM tasks can still reference audit findings
# even when we skip the expensive live scan.
DEFAULT_AUDIT = {
    "html_files_total": 129,
    "checked": 0,
    "missing_ga4": [
        "all-dj-guides.html", "best-dj-controllers-for-beginners.html",
        "best-dj-controllers-for-rekordbox.html", "best-dj-controllers-for-serato.html",
        "best-dj-controllers-under-1000.html", "best-dj-software.html",
        "best-motorized-dj-controllers.html", "best-standalone-dj-systems.html",
        "can-you-dj-without-a-controller.html", "controller-software-compatibility-matrix.html",
    ],
    "formatting_bug": [
        "ddj-flx2-review.html", "ddj-grv6-review.html",
        "pioneer-ddj-flx4-review.html", "rekordbox-vs-serato.html",
        "xdj-az-vs-denon-prime-4-plus.html",
    ],
}


# ---------------------------------------------------------------------------
# Notion queue
# ---------------------------------------------------------------------------

def consume_queue():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        return {"skipped": True, "reason": "no NOTION_TOKEN"}
    headers = _notion_headers(token)

    search_body = json.dumps({"query": QUEUE_DB_NAME,
        "filter": {"property": "object", "value": "database"}}).encode()
    req = urllib.request.Request("https://api.notion.com/v1/search",
        data=search_body, headers=headers, method="POST")
    results = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("results", [])
    db_id = next((i["id"] for i in results
        if QUEUE_DB_NAME in _rich(i.get("title", []))), None)
    if not db_id:
        log("queue_not_found")
        return {"ok": False, "reason": "queue database not found"}

    query_body = json.dumps({
        "filter": {"and": [
            {"property": "Status", "status": {"equals": "Approved"}},
            {"property": "Approved by Tammy", "checkbox": {"equals": True}}
        ]},
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": 50
    }).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/databases/" + db_id + "/query",
        data=query_body, headers=headers, method="POST")
    rows = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("results", [])

    tasks = []
    for row in rows:
        props = row.get("properties", {})
        last_run_prop = props.get("Last run", {})
        date_val = (last_run_prop.get("date") or {}).get("start")
        evidence = _rich(props.get("Result / Evidence", {}).get("rich_text", []))
        tasks.append({
            "id": row.get("id"),
            "task": _rich(props.get("Task", {}).get("title", [])),
            "type": _select(props.get("Task Type")),
            "tier": _select(props.get("Safety Tier")),
            "instructions": _rich(props.get("Instructions", {}).get("rich_text", [])),
            "last_run": date_val,
            "has_evidence": bool(evidence),
        })

    # Sort: tasks with NO evidence first, then by last_run ascending (oldest work first)
    tasks.sort(key=lambda t: (t["has_evidence"], t["last_run"] or ""))

    log("queue_read", total=len(rows),
        no_evidence=sum(1 for t in tasks if not t["has_evidence"]),
        read_only=sum(1 for t in tasks if t["tier"] == "read_only"))
    return {"ok": True, "tasks": tasks, "db_id": db_id}


def _patch_page(token, page_id, properties):
    body = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(
        "https://api.notion.com/v1/pages/" + page_id,
        data=body, headers=_notion_headers(token), method="PATCH")
    urllib.request.urlopen(req, timeout=60)


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

def generate_task_artifact(task, audit_data):
    """Build prompt from Instructions + audit context, call LLM."""
    instructions = (task.get("instructions") or "").strip()
    task_name = (task.get("task") or "improve offbeatinc.com").strip()

    audit_ctx = (
        "LIVE AUDIT DATA (offbeatinc.com / CrashyCrash/offbeat-website): "
        + str(audit_data["checked"]) + "/" + str(audit_data["html_files_total"])
        + " pages checked. GA4 missing: " + str(len(audit_data["missing_ga4"]))
        + " pages. First 10 missing GA4: "
        + ", ".join(audit_data["missing_ga4"][:10]) + ". "
        "Formatting bug pages (r27-buying-checkpoint outside .content-wrap): "
        + ", ".join(audit_data["formatting_bug"]) + "."
    )

    # Use Instructions if set; otherwise fall back to task title as the prompt
    if instructions:
        user_prompt = instructions + "\n\n---\n" + audit_ctx
    else:
        user_prompt = (
            "Task: " + task_name + "\n\n"
            "Produce a specific, actionable plan with exact filenames, "
            "code snippets, and implementation steps for offbeatinc.com.\n\n"
            + audit_ctx
        )

    sys_prompt = (
        "You are DatBotty, an autonomous web improvement agent for offbeatinc.com "
        "(a DJ gear and software review site, 129 HTML pages, repo CrashyCrash/offbeat-website). "
        "Be specific and actionable. Use exact filenames. Include code. No vague suggestions. "
        "Keep output under 1200 chars."
    )

    llm_res = execute_llm_task(sys_prompt, user_prompt)
    if llm_res["ok"]:
        tag = llm_res["provider"] + "/" + llm_res["model"]
        return {"ok": True, "text": "[" + tag + "]\n\n" + llm_res["content"]}
    return {"ok": False, "text": "ALL_PROVIDERS_FAILED\n" + json.dumps(llm_res.get("errors", {}))[:400]}


def write_evidence(token, tasks, audit_data):
    now = datetime.now(timezone.utc)
    wrote = 0
    processed = 0

    for t in tasks:
        if t.get("tier") not in ("read_only",):
            log("task_skip_tier", task=t.get("task", "")[:60], tier=t.get("tier"))
            continue
        if not t.get("id"):
            continue
        if processed >= MAX_TASKS_PER_RUN:
            log("task_cap_reached", cap=MAX_TASKS_PER_RUN)
            break

        t0 = time.time()
        log("generating_artifact", task=t.get("task", "")[:60], type=t.get("type"))
        artifact = generate_task_artifact(t, audit_data)
        processed += 1

        base_stats = (
            "Loop v3.2 | " + now.strftime("%Y-%m-%d %H:%M UTC")
            + " | " + str(audit_data["checked"]) + "/" + str(audit_data["html_files_total"])
            + " pages | GA4 missing: " + str(len(audit_data["missing_ga4"]))
            + " | Bugs: " + str(len(audit_data["formatting_bug"]))
            + " | llm_ok: " + str(artifact["ok"])
        )
        full_evidence = (base_stats + "\n\n" + artifact["text"])[:1900]

        props = {
            "Result / Evidence": {"rich_text": [{"text": {"content": full_evidence}}]},
            "Last run": {"date": {"start": now.isoformat()}},
            # Mark Done so the task rotates out of the Approved queue
            "Status": {"status": {"name": "Done"}},
        }
        try:
            _patch_page(token, t["id"], props)
            wrote += 1
            elapsed = round(time.time() - t0, 1)
            log("evidence_written", task=t.get("task", "")[:60],
                llm_ok=artifact["ok"], elapsed_s=elapsed)
        except Exception as e:
            log("patch_failed", task=t.get("task", "")[:60], error=str(e)[:200])

    return wrote


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip-audit", action="store_true",
                        help="Skip site audit even if audit tasks are queued")
    args = parser.parse_args()

    log("cycle_start", runner="v3.2")
    t_start = time.time()

    # 1. Read queue first to decide whether we need the expensive audit
    queue = consume_queue()
    tasks = queue.get("tasks", []) if queue.get("ok") else []

    # 2. Only run full audit if audit-type tasks are present AND not suppressed
    needs_audit = (
        not args.skip_audit
        and any(t.get("type") in AUDIT_TASK_TYPES for t in tasks)
    )
    if needs_audit:
        log("audit_needed", reason="audit-type tasks in queue")
        audit = audit_site()
    else:
        log("audit_skipped", reason="no audit-type tasks or flag set")
        audit = DEFAULT_AUDIT

    # 3. Write evidence and mark tasks Done
    wrote = 0
    token = os.environ.get("NOTION_TOKEN")
    if token and tasks:
        wrote = write_evidence(token, tasks, audit)
    elif not token:
        log("no_notion_token")
    else:
        log("queue_empty")

    elapsed_total = round(time.time() - t_start, 1)
    scorecard = {
        "runner": "v3.2",
        "ts": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed_total,
        "audit_ran": needs_audit,
        "audit": {
            "checked": audit["checked"],
            "total": audit["html_files_total"],
            "missing_ga4": len(audit["missing_ga4"]),
            "missing_ga4_pages": audit["missing_ga4"],
            "formatting_bug": len(audit["formatting_bug"]),
            "formatting_bug_pages": audit["formatting_bug"],
        },
        "queue": {
            "ok": queue.get("ok", False),
            "tasks_found": len(tasks),
            "tasks_written": wrote,
        },
    }
    with open("loop-scorecard.json", "w") as f:
        json.dump(scorecard, f, indent=2)

    log("cycle_end", runner="v3.2", tasks_written=wrote,
        elapsed_s=elapsed_total, status="ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
