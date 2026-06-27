#!/usr/bin/env python3
"""DatBotty v3 cloud autonomous loop (v3.8 — cycle-log hygiene, no self-trigger storm).

Key design: NOTHING can crash the script silently. Every failure is captured
and written to the DatBotty Cycle Log Notion page so we have visible proof
from inside the actual GitHub Actions run environment.

This is the CLOUD PLAN/AUDIT surface only (see .github/CLOUD_LOOP.md). It writes
plans/audit results to Notion and NEVER commits or publishes site changes — the
local Hermes engine (github.com/CrashyCrash/datbotty-hermes) is the only actor
that edits the site, autonomously on free models within bounded safety rules.

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
- Cerebras: corrected model IDs (gpt-oss-120b is the current production model).
- Gemini: try gemini-2.5-flash first, fall through models on a 429.

v3.7 changes (free-quota efficiency — per Tammy):
- Gemini now lists the full set of CURRENT free-tier models (2.5-flash-lite,
  2.0-flash-lite, 2.0-flash, 2.5-flash, flash-latest, 1.5-flash). Pro models
  are paid-only since Apr 2026 and are deliberately excluded.
- Per-call model rotation (_rotated_models): each LLM call starts on a
  different model so routine work SPREADS across all of a provider's free
  models. Each free Gemini model has its own ~1,000-1,500 RPD bucket, so
  rotating across 6 models gives well over 1,000 Gemini calls/day before any
  single model's daily cap is hit.
- Lightweight canary: the health canary now pings each provider's smallest
  model (canary_model, e.g. gemini-2.5-flash-lite) instead of the powerful
  models, so health checks do not burn the scarce 2.5-flash quota.
- Inter-call pacing (_pace_llm): a minimum spacing between outbound LLM HTTP
  calls within a run, so back-to-back tasks cannot burst past per-minute RPM
  limits. Cross-run pacing still comes from provider + model rotation.

v3.8 changes (cycle-log hygiene + cadence — per Tammy):
- Cycle-log self-trim (trim_cycle_log): each cycle keeps only the most recent
  ~50 loop log lines on the DatBotty Cycle Log page; older loop-written lines
  are deleted while the policy callout/headings are preserved. The page can no
  longer grow without bound (bounded deletes/run so a huge log converges over
  a few cycles).
- No per-cycle heartbeat block: the start-of-cycle environment line is logged
  to stdout only and folded into the single END summary line, so idle cycles
  no longer spam the Cycle Log.
- Self-trigger DISABLED by default: the workflow's schedule cron is the sole
  cadence driver. Chained self-dispatch (which queued a new run every cycle and
  flooded the log + burned quota) is off unless ENABLE_SELF_TRIGGER=1.
- Replenish never auto-approves publish-tier tasks: only read_only /
  bounded_write backlog items are auto-promoted; publish-tier stays in Backlog
  for explicit human approval (the rare high-risk gate).

Flow per cycle:
1. Audit (catches any failure, falls back to baseline).
2. Read queue (catches failures).
3. Auto-replenish from Backlog if low (never publish-tier).
4. Process tasks one-by-one (each isolated in try/except). Canary tasks ping
   all providers; other read_only tasks generate an LLM artifact.
5. Self-trigger is DISABLED by default (cron drives cadence).
6. ALWAYS write ONE final cycle summary line, then trim the Cycle Log tail.
"""
from __future__ import annotations
import argparse
import json
import os
import random
import re
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
CYCLE_LOG_KEEP      = 50
VERSION             = "v3.8"

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
    "llm_attempts": [],
    "llm_successes": [],
    "audit_pages": 0,
    "audit_total": 0,
    "missing_ga4": 0,
    "format_bugs": 0,
    "self_triggered": False,
    "cycle_log_trimmed": 0,
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


def _delete(url, headers, timeout=30):
    req = urllib.request.Request(url, headers=headers, method="DELETE")
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
# LLM providers (v3.7 — multi-model spread, light canary, 429 backoff, pacing)
# ---------------------------------------------------------------------------

PROVIDERS = [
    {
        "name": "gemini",
        "env": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "kind": "gemini",
        "models": ["gemini-2.5-flash-lite", "gemini-2.0-flash-lite",
                   "gemini-2.0-flash", "gemini-2.5-flash",
                   "gemini-flash-latest", "gemini-1.5-flash"],
        "canary_model": "gemini-2.5-flash-lite",
    },
    {
        "name": "groq",
        "env": ["GROQ_API_KEY"],
        "kind": "openai",
        "base": "https://api.groq.com/openai/v1/chat/completions",
        "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile"],
        "canary_model": "llama-3.1-8b-instant",
    },
    {
        "name": "cerebras",
        "env": ["CEREBRAS_API_KEY"],
        "kind": "openai",
        "base": "https://api.cerebras.ai/v1/chat/completions",
        "models": ["llama3.1-8b", "gpt-oss-120b", "llama-3.3-70b",
                   "qwen-3-32b", "llama-4-scout-17b-16e-instruct"],
        "canary_model": "llama3.1-8b",
    },
    {
        "name": "mistral",
        "env": ["MISTRAL_API_KEY"],
        "kind": "openai",
        "base": "https://api.mistral.ai/v1/chat/completions",
        "models": ["open-mistral-7b", "mistral-small-latest"],
        "canary_model": "open-mistral-7b",
    },
    {
        "name": "openrouter",
        "env": ["OPENROUTER_API_KEY"],
        "kind": "openai",
        "base": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["meta-llama/llama-3.1-8b-instruct:free",
                   "meta-llama/llama-3.3-70b-instruct:free"],
        "canary_model": "meta-llama/llama-3.1-8b-instruct:free",
    },
]

_provider_cooldown = set()
_llm_call_count = 0
_MIN_LLM_INTERVAL_S = 1.5
_last_llm_call_ts = 0.0


def _pace_llm():
    global _last_llm_call_ts
    wait = _MIN_LLM_INTERVAL_S - (time.time() - _last_llm_call_ts)
    if wait > 0:
        time.sleep(wait)
    _last_llm_call_ts = time.time()


class _RateLimited(Exception):
    def __init__(self, retry_after=None):
        super().__init__("rate_limited")
        self.retry_after = retry_after


class _ModelNotFound(Exception):
    pass


def _http_json(url, body, headers, timeout=90, max_retries=3):
    _pace_llm()
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
               "HTTP-Referer": "https://offbeatinc.com",
               "X-Title": "DatBotty Offbeat Loop"}
    data = _http_json(base, body, headers)
    return (data.get("choices", [{}])[0]
            .get("message", {}).get("content", "") or "").strip()


def _key_looks_real(key):
    if not key:
        return False
    if "secrets." in key or key.startswith("$"):
        return False
    if len(key) < 10:
        return False
    return True


def _provider_key(p):
    return next((os.environ.get(k) for k in p["env"]
                 if _key_looks_real(os.environ.get(k))), None)


def _rotated_models(p):
    models = p["models"]
    if len(models) <= 1:
        return list(models)
    offset = _llm_call_count % len(models)
    return [models[(offset + i) % len(models)] for i in range(len(models))]


def _try_provider(p, sys_p, usr_p, models=None):
    key = _provider_key(p)
    if not key:
        return {"ok": False, "provider": p["name"], "error": "no valid key"}
    global _llm_call_count
    _llm_call_count += 1
    last_err = "no model succeeded"
    rate_limited = False
    candidates = models if models is not None else _rotated_models(p)
    for model in candidates:
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
    n = len(PROVIDERS)
    offset = int(time.time() // 60) % n
    return [PROVIDERS[(offset + i) % n] for i in range(n)]


def execute_llm(sys_p, usr_p):
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
        light = [p.get("canary_model", p["models"][0])]
        res = _try_provider(p, sys_p, usr_p, models=light)
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
# Notion: cycle log (single summary line per cycle + self-trim)
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


def _notion_list_children(token, page_id):
    """Return all child blocks of a page, oldest first, following pagination."""
    blocks = []
    cursor = None
    for _ in range(60):
        url = "https://api.notion.com/v1/blocks/" + page_id + "/children?page_size=100"
        if cursor:
            url += "&start_cursor=" + cursor
        data = json.loads(_get(url, headers=_notion_headers(token)))
        blocks.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return blocks


_LOG_LINE_RE = re.compile(r"^\s*20\d\d-\d\d-\d\d")


def _is_log_line_block(block):
    """True only for loop-written log paragraphs (start with YYYY-MM-DD). Policy
    callouts, headings, and human notes are NOT matched, so trim never removes
    them."""
    if block.get("type") != "paragraph":
        return False
    txt = _rich(block.get("paragraph", {}).get("rich_text", []))
    return bool(_LOG_LINE_RE.match(txt))


def trim_cycle_log(token, keep=CYCLE_LOG_KEEP, max_deletes=300):
    """Keep the Cycle Log short: delete the OLDEST loop-written log lines,
    preserving the most recent `keep` of them and ALL non-log blocks. Bounded to
    `max_deletes`/run so an already-huge log converges over a few cycles without
    runaway calls or tripping Notion's rate limit."""
    page_id = find_cycle_log_id(token)
    if not page_id:
        return 0
    try:
        blocks = _notion_list_children(token, page_id)
    except Exception as e:
        _state["warnings"].append("trim_list: " + type(e).__name__ + ": " + str(e)[:100])
        return 0
    log_blocks = [b for b in blocks if _is_log_line_block(b)]
    excess = len(log_blocks) - keep
    if excess <= 0:
        return 0
    to_delete = log_blocks[:excess][:max_deletes]
    deleted = 0
    for b in to_delete:
        try:
            _delete("https://api.notion.com/v1/blocks/" + b["id"], _notion_headers(token))
            deleted += 1
            time.sleep(0.34)
        except Exception as e:
            _state["warnings"].append("trim_del: " + type(e).__name__ + ": " + str(e)[:80])
            break
    _state["cycle_log_trimmed"] = deleted
    log("cycle_log_trimmed", deleted=deleted, log_lines=len(log_blocks), kept=keep)
    return deleted


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
                "target": _rich(p.get("Target", {}).get("rich_text", [])),
                "instructions": _rich(p.get("Instructions", {}).get("rich_text", [])),
                "last_run": lr,
                "has_evidence": bool(ev),
            })
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


def is_local_executor_ready(task):
    """Return False for rows that are plans/batches, not one bounded write.

    The local Hermes executor can safely consume rows that name one concrete
    task. Broad plan rows make the queue look non-empty while giving Hermes no
    bounded unit to execute.
    """
    tier = task.get("tier") or ""
    if tier not in {"read_only", "bounded_write", "publish"}:
        return False
    text = " ".join([
        task.get("task") or "",
        task.get("target") or "",
        task.get("instructions") or "",
    ]).lower()
    broad_markers = [
        "~70", "38 slugs", "each page", "every file", "for each page",
        "all hero", "all pages", "one row per page", "approval rows",
        "image execution queue", "missing-page list",
    ]
    return not any(marker in text for marker in broad_markers)


def quarantine_non_executable_approved(token, tasks):
    moved = 0
    now = datetime.now(timezone.utc).isoformat()
    for t in tasks:
        if is_local_executor_ready(t):
            continue
        if t.get("tier") == "read_only":
            continue
        evidence = (
            "Cloud loop " + VERSION + " moved this Approved row to Needs review on "
            + now + " because it is a broad plan/batch, not a single bounded "
            "Hermes execution unit. Decompose into one concrete row per file, "
            "page, or small change before re-approval."
        )
        try:
            _patch("https://api.notion.com/v1/pages/" + t["id"],
                json.dumps({"properties": {
                    "Status": {"status": {"name": "Needs review"}},
                    "Approved by Tammy": {"checkbox": False},
                    "Result / Evidence": {"rich_text": [{"text": {"content": evidence[:1900]}}]},
                    "Last run": {"date": {"start": now}},
                }}).encode(), _notion_headers(token))
            moved += 1
        except Exception as e:
            _state["warnings"].append("quarantine fail: " + str(e)[:80])
    if moved:
        log("non_executable_approved_quarantined", moved=moved)
    return moved


def _requires_human_gate(row):
    p = row.get("properties", {})
    text = " ".join([
        _rich(p.get("Task", {}).get("title", [])),
        _rich(p.get("Instructions", {}).get("rich_text", [])),
        _rich(p.get("Target", {}).get("rich_text", [])),
    ]).lower()
    gated_markers = [
        "image", "hero", "create each", "for each slug", "new page",
        "missing review pages", "merge misplaced", "accessibility",
        "mobile responsiveness", "taste", "brand",
    ]
    return any(marker in text for marker in gated_markers)


def replenish_queue(token, db_id, current_count):
    """Promote Backlog -> Approved when the executable pool is low.

    The user policy reserves human approval for rare genuinely high-risk work,
    not every row whose legacy Safety Tier says publish. Concrete maintenance
    rows may be promoted; broad image/page/taste-sensitive rows stay gated.
    """
    if current_count >= REPLENISH_THRESHOLD:
        return 0
    try:
        body = json.dumps({
            "filter": {"property": "Status", "status": {"equals": "Backlog"}},
            "page_size": 25
        }).encode()
        backlog = json.loads(_post(
            "https://api.notion.com/v1/databases/" + db_id + "/query",
            body, _notion_headers(token))).get("results", [])
        promoted = 0
        for row in backlog:
            if promoted >= 5:
                break
            tier = _select(row.get("properties", {}).get("Safety Tier"))
            if tier == "publish" and _requires_human_gate(row):
                continue
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
# Self-trigger (DISABLED by default in v3.8)
# ---------------------------------------------------------------------------

def self_trigger():
    """Disabled by default in v3.8. The workflow's schedule cron is the sole
    cadence driver. Chained self-dispatch is what queued a fresh run every cycle
    and flooded the Cycle Log + burned free-LLM quota, so we no longer
    re-dispatch automatically. Set ENABLE_SELF_TRIGGER=1 only for a deliberate
    one-off catch-up burst."""
    if os.environ.get("ENABLE_SELF_TRIGGER") != "1":
        log("self_trigger_skipped", reason="cron drives cadence")
        return False
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

    # 1. Environment summary (console only; folded into the single END line so we
    #    NEVER write a bare heartbeat block to the Cycle Log every cycle).
    env_summary = (
        "GH_PAT=" + ("set" if _key_looks_real(os.environ.get("GH_PAT")) else "missing")
        + " GITHUB_TOKEN=" + ("set" if os.environ.get("GITHUB_TOKEN") else "missing")
        + " providers=" + (",".join([p for p in
            ["GEMINI", "GROQ", "CEREBRAS", "MISTRAL", "OPENROUTER"]
            if _key_looks_real(os.environ.get(p + "_API_KEY"))]) or "none"))
    log("env", summary=env_summary)

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
        quarantined = quarantine_non_executable_approved(token, tasks)
        if quarantined:
            tasks = read_approved_tasks(token, db_id)
        executable_count = sum(1 for t in tasks if is_local_executor_ready(t))
        promoted = replenish_queue(token, db_id, executable_count)
        _state["promoted"] = promoted
        if promoted:
            tasks = read_approved_tasks(token, db_id)
        if tasks:
            process_tasks(token, tasks, audit)

    # 5. Self-trigger (disabled by default — cron drives cadence)
    self_trigger()

    elapsed = round(time.time() - t_start, 1)

    # 6. ONE final cycle-summary line (the heartbeat), then trim the tail.
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
        + " | " + env_summary
        + " | s=" + str(elapsed)
    )
    append_to_cycle_log(token, end_line)
    if _state["errors"]:
        append_to_cycle_log(token,
            "  \u2514 errors: " + " || ".join(_state["errors"][:5])[:1500])

    # Cycle-log hygiene: keep only a short rolling tail of loop log lines.
    trim_cycle_log(token)

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
