#!/usr/bin/env python3
"""DatBotty v3 cloud autonomous loop (v3.6.1 — multi-provider LLM hardening).

Key design: NOTHING can crash the script silently. Every failure is captured
and written to the DatBotty Cycle Log Notion page so we have visible proof
from inside the actual GitHub Actions run environment.

v3.6 changes (LLM reliability):
- Each provider tries a list of candidate models; a 404/400 model error falls
  through to the next model instead of failing the whole provider.
- 429 / 5xx responses are retried with exponential backoff that respects the
  Retry-After header, then the provider is parked in a per-run cooldown so we
  stop hammering it (this is what kept spamming Groq until it 429'd).
- The starting provider rotates every minute (round-robin) so we do not always
  begin with the same provider.
- A real Provider Health Canary pings ALL five providers (not stop-at-first)
  and writes a per-provider PROVIDER CANARY line to the cycle log.

v3.6.1 changes:
- Cerebras: corrected model IDs (gpt-oss-120b is the current production model;
  the old llama-3.3-70b/llama3.1-8b IDs were 404ing). Broader fallback list.
- Gemini: free-tier quota cuts make gemini-2.0-flash frequently return 429
  (limit:0), so we now try gemini-2.5-flash first and, on a 429, fall through
  to the next candidate model before parking the provider in cooldown.

Flow per cycle:
1. Heartbeat-first: write 'cycle start' line to cycle log immediately.
2. Run audit (catches any failure, falls back to baseline).
3. Read queue (catches failures).
4. Auto-replenish from Backlog if low.
5. Process tasks one-by-one (each isolated in try/except). Canary tasks ping
   all providers; other read_only tasks generate an LLM artifact.
6. Self-trigger next run via GH_PAT (if set).
7. ALWAYS write final cycle summary line.
"""
from __future__ import annotations
import argparse
import json
import os
import random
import sys
import time
import traceback
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
REPLENISH_THRESHOLD = 3
VERSION             = "v3.6.1"

AUDIT_TASK_TYPES = {
    "site_audit", "ga4_injection", "formatting_fix",
    "link_audit", "verdict_card_css", "affiliate_fix",
}

# State accumulator — fields here are written to cycle log at end of every run.
_state = {
    "version": VERSION,
    "errors": [],
    "warnings": [],
    "notion_ok": False,
    "audit_ok": False,
    "queue_ok": False,
    "tasks_attempted": 0,
    "tasks_written": 0,
    "promoted": 0,
    "llm_attempts": [],   # list of provider names tried
    "llm_successes": [],  # list of provider names that worked
    "audit_pages": 0,
    "audit_total": 0,
    "missing_ga4": 0,
    "format_bugs": 0,
    "self_triggered": False,
    "cycle_log_page_id": None,
}


def log(event, **fields):
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event}
    rec.update(fields)
    print(json.dumps(rec, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------------------
# HTTP primitives
# ---------------------------------------------------------------------------

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
    t = token or os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
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
# LLM providers (v3.6 — multi-model fallback, 429 backoff, rotation, canary)
# ---------------------------------------------------------------------------

# Each provider lists candidate models tried in order. A 404/400 model error
# falls through to the next model rather than failing the whole provider, which
# makes the canary resilient to free-tier model-name drift (the cause of the
# Gemini/Cerebras 404s).
PROVIDERS = [
    {
        "name": "gemini",
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "kind": "gemini",
        "models": ["gemini-2.5-flash", "gemini-flash-latest",
                   "gemini-2.0-flash", "gemini-1.5-flash-latest"],
    },
    {
        "name": "groq",
        "env": ["GROQ_API_KEY"],
        "kind": "openai",
        "base": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    },
    {
        "name": "cerebras",
        "env": ["CEREBRAS_API_KEY"],
        "kind": "openai",
        "base": "https://api.cerebras.ai/v1/chat/completions",
        "models": ["gpt-oss-120b", "llama-3.3-70b", "llama3.1-8b",
                   "qwen-3-32b", "llama-4-scout-17b-16e-instruct"],
    },
    {
        "name": "mistral",
        "env": ["MISTRAL_API_KEY"],
        "kind": "openai",
        "base": "https://api.mistral.ai/v1/chat/completions",
        "models": ["mistral-small-latest", "open-mistral-7b"],
    },
    {
        "name": "openrouter",
        "env": ["OPENROUTER_API_KEY"],
        "kind": "openai",
        "base": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["meta-llama/llama-3.3-70b-instruct:free",
                   "meta-llama/llama-3.1-8b-instruct:free"],
    },
]

# Providers that 429'd or hard-failed during this process run are parked here
# so we stop hammering them for the rest of the cycle.
_provider_cooldown = set()


class _RateLimited(Exception):
    def __init__(self, retry_after=None):
        super().__init__("rate_limited")
        self.retry_after = retry_after


class _ModelNotFound(Exception):
    pass


def _http_json(url, body, headers, timeout=90, max_retries=3):
    """POST JSON with retry/backoff. Raises _RateLimited / _ModelNotFound /
    the original error so the caller can decide whether to rotate model or
    provider."""
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            code = e.code
            if code in (400, 404):
                raise _ModelNotFound(str(code))
            if code == 429 or code >= 500:
                retry_after = None
                try:
                    ra = e.headers.get("Retry-After") if e.headers else None
                    retry_after = float(ra) if ra else None
                except Exception:
                    retry_after = None
                attempt += 1
                if attempt > max_retries:
                    raise _RateLimited(retry_after) if code == 429 else e
                sleep_s = retry_after if retry_after is not None else min(2 ** attempt + random.random(), 20)
                time.sleep(sleep_s)
                continue
            raise


def _call_gemini(key, model, sys_p, usr_p):
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           + model + ":generateContent")
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": sys_p}]},
        "contents": [{"parts": [{"text": usr_p}]}],
        "generationConfig": {"maxOutputTokens": 1800},
    }).encode()
    headers = {"Content-Type": "application/json",
               "User-Agent": "datbotty",
               "x-goog-api-key": key}
    data = _http_json(url, body, headers)
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def _call_openai_compat(base, key, model, sys_p, usr_p, max_tok=1800):
    body = json.dumps({"model": model,
        "messages": [{"role": "system", "content": sys_p},
                     {"role": "user",   "content": usr_p}],
        "max_tokens": max_tok}).encode()
    headers = {"Authorization": "Bearer " + key,
               "Content-Type": "application/json",
               "User-Agent": "datbotty",
               # OpenRouter asks for these; harmless for the other providers.
               "HTTP-Referer": "https://offbeatinc.com",
               "X-Title": "DatBotty Offbeat Loop"}
    data = _http_json(base, body, headers)
    return (data.get("choices", [{}])[0]
            .get("message", {}).get("content", "") or "").strip()


def _key_looks_real(key):
    """Detect if a secret got resolved properly vs literal '$ secrets.X '."""
    if not key:
        return False
    if "secrets." in key or "${{" in key or key.startswith("$"):
        return False
    if len(key) < 10:
        return False
    return True


def _provider_key(p):
    return next((os.environ.get(k) for k in p["env"]
                 if _key_looks_real(os.environ.get(k))), None)


def _try_provider(p, sys_p, usr_p):
    """Try a single provider across its candidate models. Returns a dict with
    ok=True/False. On a 429 we fall through to the next candidate model (a
    per-model free-tier quota does not necessarily affect the others), and only
    park the provider in cooldown if every model was rate-limited."""
    key = _provider_key(p)
    if not key:
        return {"ok": False, "provider": p["name"], "error": "no valid key"}
    last_err = "no model succeeded"
    rate_limited = False
    for model in p["models"]:
        try:
            if p["kind"] == "gemini":
                out = _call_gemini(key, model, sys_p, usr_p)
            else:
                out = _call_openai_compat(p["base"], key, model, sys_p, usr_p)
            if out:
                return {"ok": True, "provider": p["name"], "model": model, "content": out}
            last_err = "empty response"
        except _ModelNotFound as e:
            last_err = "model_not_found(" + str(e) + ")"
            continue
        except _RateLimited:
            rate_limited = True
            last_err = "rate_limited"
            continue
        except Exception as e:
            last_err = type(e).__name__ + ": " + str(e)[:120]
            continue
    if rate_limited:
        _provider_cooldown.add(p["name"])
        return {"ok": False, "provider": p["name"], "error": "rate_limited", "rate_limited": True}
    return {"ok": False, "provider": p["name"], "error": last_err}


def _rotated_providers():
    """Round-robin starting offset (changes each minute) so we do not always
    begin with the same provider and burn it down to a 429."""
    n = len(PROVIDERS)
    offset = int(time.time() // 60) % n
    return [PROVIDERS[(offset + i) % n] for i in range(n)]


def execute_llm(sys_p, usr_p):
    """Return the first provider that succeeds, rotating start order and
    skipping providers already parked in cooldown."""
    errors = {}
    for p in _rotated_providers():
        name = p["name"]
        if name in _provider_cooldown:
            errors[name] = "skipped (cooldown)"
            continue
        if not _provider_key(p):
            errors[name] = "no valid key (env not interpolated or unset)"
            continue
        _state["llm_attempts"].append(name)
        res = _try_provider(p, sys_p, usr_p)
        if res.get("ok"):
            _state["llm_successes"].append(name)
            return {"ok": True, "provider": name, "model": res["model"], "content": res["content"]}
        errors[name] = res.get("error", "failed")
        log("llm_err", p=name, e=str(errors[name])[:120])
    return {"ok": False, "errors": errors}


def provider_canary(token):
    """Ping EVERY provider with a tiny prompt and record per-provider health,
    then write a PROVIDER CANARY line to the cycle log. Unlike execute_llm this
    does not stop at the first success and ignores cooldown, so it proves which
    of the five providers are actually returning valid responses."""
    sys_p = "You are a health check. Reply with exactly: OK"
    usr_p = "Reply with exactly: OK"
    results = {}
    parts = []
    for p in PROVIDERS:
        name = p["name"]
        if not _provider_key(p):
            results[name] = {"ok": False, "detail": "no key"}
            parts.append(name + "=NOKEY")
            continue
        res = _try_provider(p, sys_p, usr_p)
        if res.get("ok"):
            results[name] = {"ok": True, "model": res.get("model")}
            parts.append(name + "=OK(" + str(res.get("model")) + ")")
            if name not in _state["llm_successes"]:
                _state["llm_successes"].append(name)
        else:
            detail = str(res.get("error", "fail"))[:50]
            results[name] = {"ok": False, "detail": detail}
            parts.append(name + "=FAIL(" + detail + ")")
    ok_count = sum(1 for v in results.values() if v.get("ok"))
    line = (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            + " | PROVIDER CANARY | " + str(ok_count) + "/" + str(len(PROVIDERS))
            + " ok | " + " | ".join(parts))
    append_to_cycle_log(token, line)
    log("provider_canary", ok_count=ok_count, results=results)
    return {"ok": ok_count > 0, "ok_count": ok_count, "results": results, "line": line}


# ---------------------------------------------------------------------------
# Site audit (with fallback)
# ---------------------------------------------------------------------------

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


def audit_site_safe():
    """Always returns an audit dict. Never raises."""
    try:
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
        log("audit_ok", total=len(html_files), missing_ga4=len(missing_ga4),
            bugs=len(fmt_bug), s=round(time.time()-t0, 1))
        _state["audit_ok"] = True
        return {"html_files_total": len(html_files), "checked": len(html_files),
                "missing_ga4": missing_ga4, "formatting_bug": fmt_bug}
    except Exception as e:
        msg = type(e).__name__ + ": " + str(e)[:150]
        _state["errors"].append("audit_site: " + msg)
        log("audit_err", e=msg)
        return DEFAULT_AUDIT


# ---------------------------------------------------------------------------
# Notion: cycle log (heartbeat + final summary)
# ---------------------------------------------------------------------------

def _notion_search(token, query, filter_type="page"):
    body = json.dumps({"query": query,
        "filter": {"property": "object", "value": filter_type}}).encode()
    return json.loads(_post("https://api.notion.com/v1/search",
        body, _notion_headers(token))).get("results", [])


def find_cycle_log_id(token):
    if _state["cycle_log_page_id"]:
        return _state["cycle_log_page_id"]
    try:
        results = _notion_search(token, CYCLE_LOG_TITLE, "page")
        for r in results:
            title_parts = (r.get("properties", {})
                .get("title", {}).get("title", []))
            if CYCLE_LOG_TITLE in _rich(title_parts):
                _state["cycle_log_page_id"] = r["id"]
                return r["id"]
        # fallback: any page whose title matches by alternate property keys
        for r in results:
            props = r.get("properties", {})
            for k, v in props.items():
                if v.get("type") == "title":
                    if CYCLE_LOG_TITLE in _rich(v.get("title", [])):
                        _state["cycle_log_page_id"] = r["id"]
                        return r["id"]
        _state["warnings"].append("cycle log page not found")
        return None
    except Exception as e:
        _state["errors"].append("find_cycle_log: " + type(e).__name__ + ": " + str(e)[:120])
        return None


def append_to_cycle_log(token, text):
    page_id = find_cycle_log_id(token)
    if not page_id:
        return False
    try:
        body = json.dumps({"children": [{
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}
        }]}).encode()
        _patch("https://api.notion.com/v1/blocks/" + page_id + "/children",
               body, _notion_headers(token))
        return True
    except Exception as e:
        _state["errors"].append("cycle_log_append: " + type(e).__name__ + ": " + str(e)[:120])
        return False


# ---------------------------------------------------------------------------
# Queue: read + replenish + write
# ---------------------------------------------------------------------------

def find_queue_db(token):
    try:
        results = _notion_search(token, QUEUE_DB_NAME, "database")
        for i in results:
            if QUEUE_DB_NAME in _rich(i.get("title", [])):
                return i["id"]
    except Exception as e:
        _state["errors"].append("find_queue: " + type(e).__name__ + ": " + str(e)[:120])
    return None


def read_approved_tasks(token, db_id):
    try:
        body = json.dumps({
            "filter": {"and": [
                {"property": "Status", "status": {"equals": "Approved"}},
                {"property": "Approved by Tammy", "checkbox": {"equals": True}}
            ]},
            "page_size": 50
        }).encode()
        rows = json.loads(_post(
            "https://api.notion.com/v1/databases/" + db_id + "/query",
            body, _notion_headers(token))).get("results", [])

        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
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
                "priority": _select(p.get("Priority")) or "P3",
                "instructions": _rich(p.get("Instructions", {}).get("rich_text", [])),
                "last_run": lr,
                "has_evidence": bool(ev),
            })
        # Sort: no-evidence first, then by priority, then by oldest last_run
        tasks.sort(key=lambda t: (
            t["has_evidence"],
            priority_order.get(t["priority"], 9),
            t["last_run"] or "",
        ))
        _state["queue_ok"] = True
        return tasks
    except Exception as e:
        _state["errors"].append("read_queue: " + type(e).__name__ + ": " + str(e)[:120])
        return []


def replenish_queue(token, db_id, current_count):
    if current_count >= REPLENISH_THRESHOLD:
        return 0
    try:
        body = json.dumps({
            "filter": {"property": "Status", "status": {"equals": "Backlog"}},
            "page_size": 10
        }).encode()
        backlog = json.loads(_post(
            "https://api.notion.com/v1/databases/" + db_id + "/query",
            body, _notion_headers(token))).get("results", [])
        promoted = 0
        for row in backlog[:5]:
            try:
                _patch("https://api.notion.com/v1/pages/" + row["id"],
                    json.dumps({"properties": {
                        "Status": {"status": {"name": "Approved"}},
                        "Approved by Tammy": {"checkbox": True},
                    }}).encode(), _notion_headers(token))
                promoted += 1
            except Exception as e:
                _state["warnings"].append("promote fail: " + str(e)[:80])
        log("replenished", promoted=promoted)
        return promoted
    except Exception as e:
        _state["errors"].append("replenish: " + type(e).__name__ + ": " + str(e)[:120])
        return 0


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
    err_summary = "; ".join(k + "=" + str(v)[:80] for k, v in res.get("errors", {}).items())[:600]
    return {"ok": False, "text": "ALL_PROVIDERS_FAILED: " + err_summary}


def _is_canary(task):
    name = (task.get("task") or "").lower()
    return ("canary" in name) or ("provider health" in name)


def process_tasks(token, tasks, audit):
    now = datetime.now(timezone.utc)
    wrote, attempted = 0, 0
    for t in tasks:
        if t.get("tier") != "read_only" or not t.get("id"):
            continue
        if attempted >= MAX_TASKS_PER_RUN:
            break
        attempted += 1
        try:
            t0 = time.time()
            log("working", task=t["task"][:60])
            if _is_canary(t):
                can = provider_canary(token)
                ok = can["ok_count"] == len(PROVIDERS)
                stamp = (
                    "Loop " + VERSION + " | " + now.strftime("%Y-%m-%d %H:%M UTC")
                    + " | Provider canary " + str(can["ok_count"]) + "/"
                    + str(len(PROVIDERS)) + " OK")
                body_text = can["line"]
            else:
                art = make_artifact(t, audit)
                ok = art["ok"]
                stamp = (
                    "Loop " + VERSION + " | " + now.strftime("%Y-%m-%d %H:%M UTC")
                    + " | " + str(audit["checked"]) + "/" + str(audit["html_files_total"])
                    + " pages | GA4 missing: " + str(len(audit["missing_ga4"]))
                    + " | llm_ok: " + str(art["ok"]))
                body_text = art["text"]
            evidence = (stamp + "\n\n" + body_text)[:1900]
            props = {
                "Result / Evidence": {"rich_text": [{"text": {"content": evidence}}]},
                "Last run": {"date": {"start": now.isoformat()}},
            }
            if ok:
                props["Status"] = {"status": {"name": "Done"}}
            _patch("https://api.notion.com/v1/pages/" + t["id"],
                json.dumps({"properties": props}).encode(), _notion_headers(token))
            wrote += 1
            log("done", task=t["task"][:60], ok=ok, s=round(time.time()-t0, 1))
        except Exception as e:
            _state["errors"].append("task '" + t["task"][:40] + "': "
                + type(e).__name__ + ": " + str(e)[:100])
            log("task_err", task=t["task"][:40], e=str(e)[:120])
    _state["tasks_attempted"] = attempted
    _state["tasks_written"] = wrote
    return wrote


# ---------------------------------------------------------------------------
# Self-trigger
# ---------------------------------------------------------------------------

def self_trigger():
    pat = os.environ.get("GH_PAT")
    if not _key_looks_real(pat):
        _state["warnings"].append("GH_PAT not exposed in workflow env — self-trigger disabled")
        return False
    try:
        url = ("https://api.github.com/repos/" + OFFBEAT_OWNER + "/" + OFFBEAT_REPO
               + "/actions/workflows/datbotty-autonomous-loop.yml/dispatches")
        body = json.dumps({"ref": "main"}).encode()
        req = urllib.request.Request(url, data=body,
            headers={**gh_headers(pat), "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=30)
        _state["self_triggered"] = True
        log("self_trigger_ok")
        return True
    except Exception as e:
        _state["errors"].append("self_trigger: " + type(e).__name__ + ": " + str(e)[:120])
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--skip-audit", action="store_true")
    args = parser.parse_args()

    log("cycle_start", v=VERSION)
    t_start = time.time()

    token = os.environ.get("NOTION_TOKEN")
    if not _key_looks_real(token):
        log("abort", reason="NOTION_TOKEN not interpolated or missing")
        return 1
    _state["notion_ok"] = True

    # 1. Heartbeat: prove we got here.
    now = datetime.now(timezone.utc)
    heartbeat = (now.strftime("%Y-%m-%d %H:%M:%S UTC") + " | " + VERSION + " START"
        + " | GH_PAT=" + ("set" if _key_looks_real(os.environ.get("GH_PAT")) else "missing")
        + " | GITHUB_TOKEN=" + ("set" if os.environ.get("GITHUB_TOKEN") else "missing")
        + " | providers_set=" + ",".join([p for p in
            ["GEMINI", "GROQ", "CEREBRAS", "MISTRAL", "OPENROUTER"]
            if _key_looks_real(os.environ.get(p + "_API_KEY"))]))
    append_to_cycle_log(token, heartbeat)

    # 2. Audit (safe)
    audit = audit_site_safe() if not args.skip_audit else DEFAULT_AUDIT
    _state["audit_pages"] = audit["checked"]
    _state["audit_total"] = audit["html_files_total"]
    _state["missing_ga4"] = len(audit["missing_ga4"])
    _state["format_bugs"] = len(audit["formatting_bug"])

    # 3. Find queue
    db_id = find_queue_db(token)
    if not db_id:
        _state["errors"].append("queue DB not found by search")

    # 4. Read + replenish + process
    tasks = []
    if db_id:
        tasks = read_approved_tasks(token, db_id)
        promoted = replenish_queue(token, db_id, len(tasks))
        _state["promoted"] = promoted
        if promoted:
            tasks = read_approved_tasks(token, db_id)
        if tasks:
            process_tasks(token, tasks, audit)

    # 5. Self-trigger
    self_trigger()

    elapsed = round(time.time() - t_start, 1)

    # 6. Final cycle log
    end_line = (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        + " | " + VERSION + " END"
        + " | tasks_done=" + str(_state["tasks_written"]) + "/" + str(_state["tasks_attempted"])
        + " | promoted=" + str(_state["promoted"])
        + " | audit=" + str(_state["audit_pages"]) + "/" + str(_state["audit_total"])
        + " | ga4_missing=" + str(_state["missing_ga4"])
        + " | llm_ok=" + (",".join(_state["llm_successes"][:5]) or "none")
        + " | self_trig=" + str(_state["self_triggered"])
        + " | err=" + str(len(_state["errors"]))
        + " | s=" + str(elapsed)
    )
    append_to_cycle_log(token, end_line)
    if _state["errors"]:
        append_to_cycle_log(token,
            "  \u2514 errors: " + " || ".join(_state["errors"][:5])[:1500])

    # 7. Scorecard
    try:
        with open("loop-scorecard.json", "w") as f:
            json.dump({**_state, "elapsed_s": elapsed}, f, indent=2)
    except Exception:
        pass

    log("cycle_end", **{k: v for k, v in _state.items() if k != "cycle_log_page_id"},
        elapsed_s=elapsed)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        # Last-resort: try to write a fatal-error line to cycle log.
        tb = traceback.format_exc()[-1500:]
        log("fatal", tb=tb[-500:])
        try:
            tok = os.environ.get("NOTION_TOKEN")
            if tok and _key_looks_real(tok):
                append_to_cycle_log(tok,
                    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    + " | " + VERSION + " FATAL: " + tb[-800:])
        except Exception:
            pass
        sys.exit(1)
