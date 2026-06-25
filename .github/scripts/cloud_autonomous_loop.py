#!/usr/bin/env python3
"""DatBotty v3 - cloud autonomous loop (v3).

Executes a bounded, idempotent cycle. 
1. Audits live site for known gaps (GA4, formatting bugs).
2. Reads the Notion Approved Work Queue.
3. Evaluates all free model routes (Gemini, Groq, Cerebras, Mistral, OpenRouter).
4. Routes actionable tasks to healthy models to generate concrete, actionable fixes.
5. Writes the generated artifacts back to Notion.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
import random

OFFBEAT_OWNER = "CrashyCrash"
OFFBEAT_REPO = "offbeat-website"
GA4_ID = "G-9MG87ETLPT"
FORMATTING_BUG_MARKER = "full-width-section r27-buying-checkpoint"
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
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "datbotty-cloud-loop"}
    if token: headers["Authorization"] = "Bearer " + token
    return headers

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

def call_openai_compat(url, key, model, system_prompt, user_prompt, max_tokens=1500):
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
        "User-Agent": "datbotty-cloud-loop"
    }, method="POST")
    
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

def call_gemini(key, model, system_prompt, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}]
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "datbotty-cloud-loop"
    }, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

def execute_llm_task(system_prompt, user_prompt):
    """Fallback router trying all free models."""
    errors = {}
    
    # 1. Gemini
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if gemini_key:
        try:
            res = call_gemini(gemini_key, "gemini-1.5-flash", system_prompt, user_prompt)
            return {"ok": True, "provider": "gemini", "model": "gemini-1.5-flash", "content": res}
        except Exception as e:
            errors["gemini"] = str(e)

    # 2. Cerebras
    cerebras_key = os.environ.get("CEREBRAS_API_KEY")
    if cerebras_key:
        try:
            res = call_openai_compat("https://api.cerebras.ai/v1/chat/completions", cerebras_key, "llama-3.3-70b", system_prompt, user_prompt)
            return {"ok": True, "provider": "cerebras", "model": "llama-3.3-70b", "content": res}
        except Exception as e:
            errors["cerebras"] = str(e)
            
    # 3. Groq
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            res = call_openai_compat("https://api.groq.com/openai/v1/chat/completions", groq_key, "llama-3.3-70b-versatile", system_prompt, user_prompt)
            return {"ok": True, "provider": "groq", "model": "llama-3.3-70b-versatile", "content": res}
        except Exception as e:
            errors["groq"] = str(e)
            
    # 4. Mistral
    mistral_key = os.environ.get("MISTRAL_API_KEY")
    if mistral_key:
        try:
            res = call_openai_compat("https://api.mistral.ai/v1/chat/completions", mistral_key, "mistral-small-latest", system_prompt, user_prompt)
            return {"ok": True, "provider": "mistral", "model": "mistral-small-latest", "content": res}
        except Exception as e:
            errors["mistral"] = str(e)
            
    # 5. OpenRouter
    or_key = os.environ.get("OPENROUTER_API_KEY")
    if or_key:
        for model in ["meta-llama/llama-3.3-70b-instruct:free", "google/gemini-2.0-flash-exp:free"]:
            try:
                res = call_openai_compat("https://openrouter.ai/api/v1/chat/completions", or_key, model, system_prompt, user_prompt)
                return {"ok": True, "provider": "openrouter", "model": model, "content": res}
            except Exception as e:
                errors[f"openrouter_{model}"] = str(e)
                
    return {"ok": False, "errors": errors}

def audit_site(max_files=300):
    tree_url = f"https://api.github.com/repos/{OFFBEAT_OWNER}/{OFFBEAT_REPO}/git/trees/main?recursive=1"
    tree = json.loads(_get(tree_url, headers=gh_headers()).decode())
    html_files = [n["path"] for n in tree.get("tree", []) if n.get("type") == "blob" and n["path"].endswith(".html")]
    
    missing_ga4, formatting_bug = [], []
    checked = 0
    for path in html_files[:max_files]:
        raw_url = f"https://raw.githubusercontent.com/{OFFBEAT_OWNER}/{OFFBEAT_REPO}/main/{path}"
        try:
            html = _get(raw_url, headers={"User-Agent": "datbotty"}).decode("utf-8", "replace")
        except Exception:
            continue
        checked += 1
        if GA4_ID not in html: missing_ga4.append(path)
        if FORMATTING_BUG_MARKER in html: formatting_bug.append(path)
        
    return {
        "html_files_total": len(html_files),
        "checked": checked,
        "missing_ga4": missing_ga4,
        "formatting_bug": formatting_bug
    }

def consume_queue():
    token = os.environ.get("NOTION_TOKEN")
    if not token: return {"skipped": True}
    headers = _notion_headers(token)
    
    search_body = json.dumps({"query": QUEUE_DB_NAME, "filter": {"property": "object", "value": "database"}}).encode()
    req = urllib.request.Request("https://api.notion.com/v1/search", data=search_body, headers=headers, method="POST")
    results = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("results", [])
    db_id = next((i["id"] for i in results if QUEUE_DB_NAME in _rich(i.get("title"))), None)
    if not db_id: return {"ok": False, "reason": "queue database not found"}
    
    query_body = json.dumps({
        "filter": {"and": [
            {"property": "Status", "status": {"equals": "Approved"}},
            {"property": "Approved by Tammy", "checkbox": {"equals": True}}
        ]},
        "page_size": 25
    }).encode()
    req = urllib.request.Request(f"https://api.notion.com/v1/databases/{db_id}/query", data=query_body, headers=headers, method="POST")
    rows = json.loads(urllib.request.urlopen(req, timeout=60).read().decode()).get("results", [])
    
    tasks = []
    for row in rows:
        props = row.get("properties", {})
        tasks.append({
            "id": row.get("id"),
            "task": _rich(props.get("Task", {}).get("title")),
            "type": _select(props.get("Task Type")),
            "tier": _select(props.get("Safety Tier"))
        })
    return {"ok": True, "tasks": tasks}

def _patch_page(token, page_id, properties):
    body = json.dumps({"properties": properties}).encode()
    req = urllib.request.Request(f"https://api.notion.com/v1/pages/{page_id}", data=body, headers=_notion_headers(token), method="PATCH")
    urllib.request.urlopen(req, timeout=60)

def generate_task_artifact(task, audit_data):
    if task.get("type") == "site_audit" and audit_data["missing_ga4"]:
        target_file = random.choice(audit_data["missing_ga4"])
        sys_prompt = "You are a web developer. Provide exact, actionable instructions to inject a GA4 tag into an HTML file."
        user_prompt = f"The file '{target_file}' is missing the GA4 tag {GA4_ID}. Write the exact `<script>` tag required, and explicitly state that it must be placed immediately after the `<head>` tag. Return ONLY the markdown codeblock with the snippet and a 1-sentence placement instruction."
        
        llm_res = execute_llm_task(sys_prompt, user_prompt)
        if llm_res["ok"]: return f"✅ Model Artifact ({llm_res['provider']} {llm_res['model']}) for {target_file}:\n\n{llm_res['content']}"
            
    elif task.get("type") == "link_audit" and audit_data["formatting_bug"]:
        target_file = random.choice(audit_data["formatting_bug"])
        sys_prompt = "You are a web developer. Fix HTML layout bugs."
        user_prompt = f"The file '{target_file}' has a formatting bug because `{FORMATTING_BUG_MARKER}` is placed outside the main content wrapper. Write a 2-sentence instruction on how to correctly nest this div inside `<main class='content-wrap'>`. No fluff."
        
        llm_res = execute_llm_task(sys_prompt, user_prompt)
        if llm_res["ok"]: return f"✅ Model Artifact ({llm_res['provider']} {llm_res['model']}) for {target_file}:\n\n{llm_res['content']}"
            
    llm_res = execute_llm_task("You are an autonomous agent.", "Acknowledge operational readiness in exactly 5 words.")
    if llm_res["ok"]: return f"🤖 System Canary ({llm_res['provider']} {llm_res['model']}): {llm_res['content']}"
        
    return f"❌ All providers failed. Errors: {llm_res.get('errors')}"

def write_evidence(token, tasks, audit_data):
    now = datetime.now(timezone.utc)
    wrote = 0
    for t in tasks:
        if t.get("tier") != "read_only" or not t.get("id"): continue
        
        artifact = generate_task_artifact(t, audit_data)
        base_stats = f"Cloud loop | {audit_data['checked']}/{audit_data['html_files_total']} pages | GA4 missing: {len(audit_data['missing_ga4'])} | Bugs: {len(audit_data['formatting_bug'])}"
        full_evidence = f"{base_stats}\n\n{artifact}"
        
        props = {
            "Result / Evidence": {"rich_text": [{"text": {"content": full_evidence[:1900]}}]},
            "Last run": {"date": {"start": now.isoformat()}}
        }
        try:
            _patch_page(token, t["id"], props)
            wrote += 1
        except Exception as e:
            log("evidence_patch_failed", error=str(e))
    return wrote

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    
    log("cycle_start", runner="v3-multi-model")
    audit = audit_site()
    queue = consume_queue()
    
    token = os.environ.get("NOTION_TOKEN")
    if token and queue.get("ok"):
        write_evidence(token, queue["tasks"], audit)
        
    log("cycle_end", status="ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())