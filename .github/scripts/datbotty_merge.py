#!/usr/bin/env python3
"""Small policy-gated merger, executed only by trusted pull_request_target code."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

if __package__:
    from .datbotty_pr_gate import GateReject, PROFILE_FILES, parse_provenance, review_packet, validate, verify_t1
else:
    from datbotty_pr_gate import GateReject, PROFILE_FILES, parse_provenance, review_packet, validate, verify_t1

REPO = "CrashyCrash/offbeat-website"
CONTEXTS = {"DatBotty Deterministic Gate", "DatBotty T1 Review"}


def gh(*args: str, body: dict | None = None) -> object:
    command = ["gh", *args]
    if body is not None:
        command += ["--input", "-"]
    result = subprocess.run(command, input=json.dumps(body) if body is not None else None,
                            capture_output=True, text=True, timeout=30, check=True)
    return json.loads(result.stdout)


def assert_merge_ready(pr: dict, main: str, statuses: list, checks: list,
                       reviews: list, threads: dict, run_url: str) -> None:
    p = parse_provenance(pr.get("body", ""))
    if pr.get("state") != "open" or pr.get("draft") is not False or pr.get("user", {}).get("login") != "DatBotty-v4":
        raise GateReject("PR is not an eligible publisher PR")
    if pr.get("head", {}).get("repo", {}).get("full_name") != REPO or pr.get("base", {}).get("repo", {}).get("full_name") != REPO:
        raise GateReject("repository mismatch")
    if p["package_id"] not in PROFILE_FILES or p["candidate_sha"] != pr["head"]["sha"]:
        raise GateReject("risk class or candidate mismatch")
    if p["base_sha"] != main or pr["base"]["sha"] != main or pr["base"]["ref"] != "main":
        raise GateReject("stale base")
    # The two required statuses must be emitted by this trusted workflow run,
    # not a similarly named old check or a publisher-written status.
    latest = {}
    for status in statuses:
        latest.setdefault(status["context"], status)
    for name in CONTEXTS:
        status = latest.get(name, {})
        if (status.get("state") != "success" or status.get("creator", {}).get("login") != "github-actions[bot]"
                or status.get("target_url") != run_url):
            raise GateReject("missing, failed or untrusted required gate: " + name)
    if any(s.get("state") in ("failure", "error", "pending") for s in latest.values()):
        raise GateReject("unresolved status")
    if any(c.get("status") != "completed" or c.get("conclusion") not in ("success", "neutral", "skipped") for c in checks):
        raise GateReject("unresolved check")
    latest_review = {}
    for review in reviews:
        if review.get("state") != "COMMENTED":
            latest_review[review["user"]["login"]] = review["state"]
    if any(state in ("CHANGES_REQUESTED", "PENDING") for state in latest_review.values()):
        raise GateReject("unresolved review rejection")
    if threads.get("pageInfo", {}).get("hasNextPage") is not False or any(t.get("isResolved") is not True for t in threads.get("nodes", [])):
        raise GateReject("unresolved or incomplete review threads")
    if pr.get("mergeable") is not True or pr.get("mergeable_state") != "clean":
        raise GateReject("provider merge policy is not clean")


def main() -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    number = event["pull_request"]["number"]
    pr = gh("api", f"repos/{REPO}/pulls/{number}")
    sha = pr["head"]["sha"]
    if sha != event["pull_request"]["head"]["sha"]:
        raise GateReject("PR changed after review")
    detail = validate(Path.cwd(), {"pull_request": pr}, sha)
    verify_t1(Path.cwd(), pr["body"], review_packet(Path.cwd(), parse_provenance(pr["body"]), detail))
    statuses = gh("api", f"repos/{REPO}/commits/{sha}/statuses?per_page=100")
    checks = gh("api", f"repos/{REPO}/commits/{sha}/check-runs?per_page=100")
    reviews = gh("api", f"repos/{REPO}/pulls/{number}/reviews?per_page=100")
    if len(statuses) >= 100 or checks["total_count"] >= 100 or len(reviews) >= 100:
        raise GateReject("incomplete provider evidence pagination")
    query = 'query($number:Int!){repository(owner:"CrashyCrash",name:"offbeat-website"){pullRequest(number:$number){reviewThreads(first:100){nodes{isResolved} pageInfo{hasNextPage}}}}}'
    threads = gh("api", "graphql", "-f", "query=" + query, "-F", "number=" + str(number))["data"]["repository"]["pullRequest"]["reviewThreads"]
    base = gh("api", f"repos/{REPO}/git/ref/heads/main")["object"]["sha"]
    run_url = f'https://github.com/{REPO}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
    assert_merge_ready(pr, base, statuses, checks["check_runs"], reviews, threads, run_url)
    result = gh("api", "--method", "PUT", f"repos/{REPO}/pulls/{number}/merge",
                body={"sha": sha, "merge_method": "merge", "commit_title": f"Merge governed DatBotty candidate {sha[:12]} (#{number})"})
    if result.get("merged") is not True:
        raise GateReject("provider refused merge")
    print(json.dumps({"candidate_sha": sha, "base_sha": base, "merge_sha": result["sha"], "pr": number}, sort_keys=True))


if __name__ == "__main__":
    main()
