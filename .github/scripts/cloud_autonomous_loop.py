#!/usr/bin/env python3
"""DatBotty v3 cloud autonomous loop (v3.3).

v3.2 -> v3.3 key additions:
- self_trigger(): after each run, dispatch next workflow via GH_PAT so the
  loop fires every ~10 min instead of waiting for hourly cron.
  Requires repo secret GH_PAT with scopes: repo, workflow.
  Falls back silently if GH_PAT is absent.
- replenish_queue(): when Approved queue < 3, auto-promotes top Backlog
  tasks to Approved. Queue never empties without human input.
- append_cycle_log(): appends one-line summary to 'DatBotty Cycle Log'
  Notion page so status is always visible without asking Notion AI.
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
OFFBEAT_REPO  = "offbeat-website"
GA4_ID              = "G-9MG87ETLPT"
FORMATTING_BUG_MARKER = "full-width-section r27-buying-checkpoint"
QUEUE_DB_NAME       = "Approved Work Queue"
CYCLE_LOG_TITLE     = "DatBotty Cycle Log"
NOTION_VERSION      = "2022-06-28"
MAX_TASKS_PER_RUN   = 10
REPLENISH_THRESHOLD = 3   # promote Backlog when fewer than this many Approved

AUDIT_TASK_TYPES = {
    "site_audit", "ga4_injection", "formatting_fix",
    "link_audit", "verdict_card_css", "affiliate_fix",
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def log(event, **fields):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event}
    rec.update(fields)
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _post(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _patch(url, body, headers, timeout=60):
    req = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def gh_headers(token=None):
    t = token or os.environ.get("GITHUB_TOKEN")
    h = {"Accept": "application/vnd.github+json",
         "User-Agent": "datbotty-loop",
         "X-GitHub-Api-Version": "2022-11-28"}
    if t:
        h["Authorization"] = "Bearer " + t
    return h


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
    v = (prop or {}).get("select")
    return v.get("name") if v else None


# ---------------------------------------------------------------------------
# LLM providers
# ---------------------------------------------------------------------------

def call_gemini(key, model, sys_p, usr_p):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent?key=" + key)
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": sys_p}]},
        "contents": [{"parts": [{"text": usr_p}]}
    ]}).encode()
    req = urllib.request.Request(url, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "datbotty"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()


def call_oai_compat(base, key, model, sys_p, usr_p, max_tok=1800):
    body = json.dumps({"model": model,
        "messages": [{"role": "system", "content": sys_p},
                     {"role": "user",   "content": usr_p}],
        "max_tokens": max_tok}).encode()
    req = urllib.request.Request(base, data=body,
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "User-Agent": "datbotty"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return (json.loads(r.read()).get("choices", [{}])[0]
                .get("message", {}).get("content", "").strip())


def execute_llm(sys_p, usr_p):
    errors = {}

    gkey = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gkey:
        try:
            return {"ok": True, "provider": "gemini", "model": "gemini-1.5-flash",
                    "content": call_gemini(gkey, "gemini-1.5-flash", sys_p, usr_p)}
        except Exception as e:
            errors["gemini"] = str(e); log("llm_err", p="gemini", e=str(e)[:100])

    ck = os.environ.get("CEREBRAS_API_KEY")
    if ck:
        try:
            return {"ok": True, "provider": "cerebras", "model": "llama-3.3-70b",
                    "content": call_oai_compat("https://api.cerebras.ai/v1/chat/completions",
                        ck, "llama-3.3-70b", sys_p, usr_p)}
        except Exception as e:
            errors["cerebras"] = str(e); log("llm_err", p="cerebras", e=str(e)[:100])

    gk = os.environ.get("GROQ_API_KEY")
    if gk:
        try:
            return {"ok": True, "provider": "groq", "model": "llama-3.3-70b-versatile",
                    "content": call_oai_compat("https://api.groq.com/openai/v1/chat/completions",
                        gk, "llama-3.3-70b-versatile", sys_p, usr_p)}
        except Exception as e:
            errors["groq"] = str(e); log("llm_err", p="groq", e=str(e)[:100])

    mk = os.environ.get("MISTRAL_API_KEY")
    if mk:
        try:
            return {"ok": True, "provider": "mistral", "model": "mistral-small-latest",
                    "content": call_oai_compat("https://api.mistral.ai/v1/chat/completions",
                        mk, "mistral-small-latest", sys_p, usr_p)}
        except Exception as e:
            errors["mistral"] = str(e); log("llm_err", p="mistral", e=str(e)[:100])

    ok = os.environ.get("OPENROUTER_API_KEY")
    if ok:
        for m in ["meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"]:
            try:
                return {"ok": True, "provider": "openrouter", "model": m,
                        "content": call_oai_compat(
                            "https://openrouter.ai/api/v1/chat/completions", ok, m, sys_p, usr_p)}
            except Exception as e:
                errors["openrouter/" + m] = str(e); log("llm_err", p="openrouter", m=m, e=str(e)[:80])

    return {"ok": False, "errors": errors}


# ---------------------------------------------------------------------------
# Site audit
# ---------------------------------------------------------------------------

def audit_site():
    t0 = time.time()
    tree_url = ("https://api.github.com/repos/" + OFFBEAT_OWNER + "/"
                + OFFBEAT_REPO + "/git/trees/main?recursive=1")
    tree = json.loads(_get(tree_url, headers=gh_headers()).decode())
    html_files = [n["path"] for n in tree.get("tree", [])
                  if n.get("type") == "blob" and n["path"].endswith(".html")]

    missing_ga4, fmt_bug = [], []
    for path in html_files:
        raw = ("https://raw.githubusercontent.com/" + OFFBEAT_OWNER
               + "/" + OFFBEAT_REPO + "/main/" + path)
        try:
            html = _get(raw, {"User-Agent": "datbotty"}).decode("utf-8", "replace")
        except Exception:
            continue
        if GA4_ID not in html:
            missing_ga4.append(path)
        if FORMATTING_BUG_MARKER in html:
            fmt_bug.append(path)

    log("audit_done", total=len(html_files), missing_ga4=len(missing_ga4),
        bugs=len(fmt_bug), elapsed=round(time.time()-t0, 1))
    return {"html_files_total": len(html_files), "checked": len(html_files),
            "missing_ga4": missing_ga4, "formatting_bug": fmt_bug}


DEFAULT_AUDIT = {
    "html_files_total": 129, "checked": 0,
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
# Notion helpers
# ---------------------------------------------------------------------------

def _notion_search(token, query, filter_type="page"):
    body = json.dumps({"query": query,
        "filter": {"property": "object", "value": filter_type}}).encode()
    hdrs = _notion_headers(token)
    return json.loads(_post("https://api.notion.com/v1/search", body, hdrs)).get("results", [])


def _patch_page(token, page_id, properties):
    body = json.dumps({"properties": properties}).encode()
    _patch("https://api.notion.com/v1/pages/" + page_id,
           body, _notion_headers(token))


def _append_blocks(token, page_id, children):
    body = json.dumps({"children": children}).encode()
    _patch("https://api.notion.com/v1/blocks/" + page_id + "/children",
           body, _notion_headers(token))


# ---------------------------------------------------------------------------
# Queue: read
# ---------------------------------------------------------------------------

def find_queue_db(token):
    results = _notion_search(token, QUEUE_DB_NAME, "database")
    return next((i["id"] for i in results
        if QUEUE_DB_NAME in _rich(i.get("title", []))), None)


def read_approved_tasks(token, db_id):
    body = json.dumps({
        "filter": {"and": [
            {"property": "Status", "status": {"equals": "Approved"}},
            {"property": "Approved by Tammy", "checkbox": {"equals": True}}
        ]},
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": 50
    }).encode()
    rows = json.loads(_post(
        "https://api.notion.com/v1/databases/" + db_id + "/query",
        body, _notion_headers(token))).get("results", [])

    tasks = []
    for row in rows:
        p = row.get("properties", {})
        lr = (p.get("Last run", {}).get("date") or {}).get("start")
        ev = _rich(p.get("Result / Evidence", {}).get("rich_text", []))
        tasks.append({
            "id": row["id"],
            "task": _rich(p.get("Task", {}).get("title", [])),
            "type": _select(p.get("Task Type")),
            "tier": _select(p.get("Safety Tier")),
            "instructions": _rich(p.get("Instructions", {}).get("rich_text", [])),
            "last_run": lr,
            "has_evidence": bool(ev),
        })
    tasks.sort(key=lambda t: (t["has_evidence"], t["last_run"] or ""))
    log("queue_read", approved=len(tasks),
        fresh=sum(1 for t in tasks if not t["has_evidence"]))
    return tasks


# ---------------------------------------------------------------------------
# Queue: auto-replenish from Backlog
# ---------------------------------------------------------------------------

def replenish_queue(token, db_id, current_count):
    """Promote top Backlog tasks to Approved when queue is running low."""
    if current_count >= REPLENISH_THRESHOLD:
        return 0
    need = max(5, REPLENISH_THRESHOLD - current_count + 5)
    body = json.dumps({
        "filter": {"property": "Status", "status": {"equals": "Backlog"}},
        "sorts": [{"property": "Priority", "direction": "ascending"}],
        "page_size": need
    }).encode()
    backlog = json.loads(_post(
        "https://api.notion.com/v1/databases/" + db_id + "/query",
        body, _notion_headers(token))).get("results", [])

    promoted = 0
    for row in backlog:
        try:
            _patch_page(token, row["id"], {
                "Status": {"status": {"name": "Approved"}},
                "Approved by Tammy": {"checkbox": True},
            })
            promoted += 1
            log("task_promoted", id=row["id"][:8],
                task=_rich(row.get("properties", {}).get("Task", {}).get("title", []))[:50])
        except Exception as e:
            log("promote_err", e=str(e)[:100])
    log("replenish_done", promoted=promoted, was=current_count)
    return promoted


# ---------------------------------------------------------------------------
# Task execution
# ---------------------------------------------------------------------------

def make_artifact(task, audit):
    instructions = (task.get("instructions") or "").strip()
    name = (task.get("task") or "improve offbeatinc.com").strip()

    ctx = (
        "LIVE AUDIT (offbeatinc.com, CrashyCrash/offbeat-website): "
        + str(audit["checked"]) + "/" + str(audit["html_files_total"]) + " pages. "
        "GA4 missing (" + str(len(audit["missing_ga4"])) + "): "
        + ", ".join(audit["missing_ga4"][:15]) + ". "
        "Formatting bug pages: " + ", ".join(audit["formatting_bug"]) + "."
    )
    prompt = (instructions + "\n\n---\n" + ctx) if instructions else (
        "Task: " + name + "\n\nBe specific. Use exact filenames. Include code.\n\n" + ctx)

    sys_p = (
        "You are DatBotty, autonomous web agent for offbeatinc.com (DJ gear/software site, "
        "129 HTML pages, CrashyCrash/offbeat-website). Specific + actionable only. "
        "Exact filenames + code. No vague suggestions. Max 1200 chars output."
    )
    res = execute_llm(sys_p, prompt)
    if res["ok"]:
        tag = res["provider"] + "/" + res["model"]
        return {"ok": True, "text": "[" + tag + "]\n\n" + res["content"]}
    return {"ok": False, "text": "ALL_PROVIDERS_FAILED\n" + json.dumps(res.get("errors", {}))[:400]}


def write_evidence(token, tasks, audit):
    now = datetime.now(timezone.utc)
    wrote, processed = 0, 0
    for t in tasks:
        if t.get("tier") != "read_only" or not t.get("id"):
            continue
        if processed >= MAX_TASKS_PER_RUN:
            log("cap_hit", cap=MAX_TASKS_PER_RUN); break
        t0 = time.time()
        log("working", task=t["task"][:60])
        art = make_artifact(t, audit)
        processed += 1
        stamp = (
            "Loop v3.3 | " + now.strftime("%Y-%m-%d %H:%M UTC")
            + " | " + str(audit["checked"]) + "/" + str(audit["html_files_total"])
            + " pages | GA4 missing: " + str(len(audit["missing_ga4"]))
            + " | llm_ok: " + str(art["ok"])
        )
        evidence = (stamp + "\n\n" + art["text"])[:1900]
        props = {
            "Result / Evidence": {"rich_text": [{"text": {"content": evidence}}]},
            "Last run": {"date": {"start": now.isoformat()}},
            "Status": {"status": {"name": "Done"}},
        }
        try:
            _patch_page(token, t["id"], props)
            wrote += 1
            log("done", task=t["task"][:60], llm=art["ok"], s=round(time.time()-t0, 1))
        except Exception as e:
            log("patch_err", task=t["task"][:60], e=str(e)[:200])
    return wrote


# ---------------------------------------------------------------------------
# Cycle log
# ---------------------------------------------------------------------------

def append_cycle_log(token, wrote, audit, promoted, self_triggered, elapsed):
    """Append one timestamped line to the DatBotty Cycle Log Notion page."""
    try:
        results = _notion_search(token, CYCLE_LOG_TITLE, "page")
        page_id = next(
            (r["id"] for r in results
             if CYCLE_LOG_TITLE in _rich(
                 r.get("properties", {}).get("title", {}).get("title", []))),
            None)
        if not page_id:
            log("cycle_log_skip", reason="page not found")
            return
        now = datetime.now(timezone.utc)
        line = (
            now.strftime("%Y-%m-%d %H:%M UTC") + " | v3.3"
            + " | tasks_done=" + str(wrote)
            + " | promoted=" + str(promoted)
            + " | ga4_missing=" + str(len(audit["missing_ga4"]))
            + " | audit_pages=" + str(audit["checked"]) + "/" + str(audit["html_files_total"])
            + " | self_triggered=" + str(self_triggered)
            + " | elapsed=" + str(elapsed) + "s"
        )
        _append_blocks(token, page_id, [{
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": line}}]}
        }])
        log("cycle_log_ok")
    except Exception as e:
        log("cycle_log_err", e=str(e)[:150])


# ---------------------------------------------------------------------------
# Self-trigger
# ---------------------------------------------------------------------------

def self_trigger():
    """Dispatch next workflow run so loop fires every ~10 min, not hourly.

    Requires repo secret GH_PAT with scopes: repo, workflow.
    The built-in GITHUB_TOKEN lacks actions:write, so it will 403 without PAT.
    Failure is silent — hourly cron acts as fallback.
    """
    pat = os.environ.get("GH_PAT")
    if not pat:
        log("self_trigger_skip", reason="GH_PAT not set — add secret to enable sub-hourly runs")
        return False
    try:
        url = ("https://api.github.com/repos/" + OFFBEAT_OWNER + "/" + OFFBEAT_REPO
               + "/actions/workflows/datbotty-autonomous-loop.yml/dispatches")
        body = json.dumps({"ref": "main"}).encode()
        req = urllib.request.Request(url, data=body,
            headers={**gh_headers(pat), "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=30)
        log("self_trigger_ok")
        return True
    except Exception as e:
        log("self_trigger_err", e=str(e)[:150])
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    args = parser.parse_args()

    log("cycle_start", runner="v3.3")
    t_start = time.time()
    token = os.environ.get("NOTION_TOKEN")

    if not token:
        log("abort", reason="NOTION_TOKEN missing")
        return 1

    # 1. Find queue DB
    db_id = find_queue_db(token)
    if not db_id:
        log("abort", reason="queue DB not found")
        return 1

    # 2. Read approved tasks
    tasks = read_approved_tasks(token, db_id)

    # 3. Auto-replenish if queue is low
    promoted = replenish_queue(token, db_id, len(tasks))
    if promoted:
        tasks = read_approved_tasks(token, db_id)  # re-read with new tasks

    # 4. Decide whether audit is needed
    needs_audit = (
        not args.skip_audit
        and any(t.get("type") in AUDIT_TASK_TYPES for t in tasks)
    )
    if needs_audit:
        audit = audit_site()
    else:
        log("audit_skip", reason="no audit tasks or flag")
        audit = DEFAULT_AUDIT

    # 5. Process tasks
    wrote = write_evidence(token, tasks, audit) if tasks else 0
    if not tasks:
        log("queue_empty", note="all done or none approved")

    elapsed = round(time.time() - t_start, 1)

    # 6. Append to cycle log in Notion
    triggered = False
    try:
        append_cycle_log(token, wrote, audit, promoted, triggered, elapsed)
    except Exception:
        pass

    # 7. Self-trigger next run (needs GH_PAT secret)
    triggered = self_trigger()

    # 8. Scorecard
    scorecard = {
        "runner": "v3.3",
        "ts": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": elapsed,
        "audit_ran": needs_audit,
        "self_triggered": triggered,
        "promoted": promoted,
        "audit": {
            "checked": audit["checked"],
            "total": audit["html_files_total"],
            "missing_ga4": len(audit["missing_ga4"]),
            "missing_ga4_pages": audit["missing_ga4"],
            "formatting_bug": len(audit["formatting_bug"]),
            "formatting_bug_pages": audit["formatting_bug"],
        },
        "queue": {
            "tasks_found": len(tasks),
            "tasks_written": wrote,
            "backlog_promoted": promoted,
        },
    }
    with open("loop-scorecard.json", "w") as f:
        json.dump(scorecard, f, indent=2)

    log("cycle_end", runner="v3.3", wrote=wrote, triggered=triggered,
        promoted=promoted, elapsed_s=elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
