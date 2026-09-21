#!/usr/bin/env python3
"""Provider-side merger for candidates that passed protected Gate v2."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from datbotty_gate_v2 import (
    GateReject,
    parse_provenance,
    validate_candidate,
    verify_t1,
)

REPO = "CrashyCrash/offbeat-website"
CONTEXTS = {"DatBotty Deterministic Gate", "DatBotty T1 Review"}
SELF_MERGE_CHECK = "Policy-gated low-risk merge"
TRANSIENT_READINESS_ERRORS = {
    "unresolved status",
    "unresolved check",
    "provider merge policy is not clean",
}


def gh(*args: str, body: dict | None = None) -> object:
    command = ["gh", *args]
    if body is not None:
        command += ["--input", "-"]
    result = subprocess.run(
        command,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout)


def is_current_merge_check(check: dict, run_url: str) -> bool:
    return (
        check.get("name") == SELF_MERGE_CHECK
        and check.get("status") == "in_progress"
        and check.get("details_url", "").startswith(run_url + "/job/")
    )


def is_current_merge_policy_state(
    pr: dict,
    checks: list,
    run_url: str,
) -> bool:
    return (
        pr.get("mergeable") is True
        and (
            pr.get("mergeable_state") == "clean"
            or (
                pr.get("mergeable_state") == "unstable"
                and any(is_current_merge_check(check, run_url) for check in checks)
            )
        )
    )


def assert_verified_candidate_commit(sha: str) -> None:
    commit = gh("api", f"repos/{REPO}/commits/{sha}")
    verification = (commit.get("commit") or {}).get("verification") or {}
    if verification.get("verified") is not True:
        raise GateReject(
            "candidate commit is not provider-verified: "
            + str(verification.get("reason") or "unknown")
        )


def assert_merge_ready(
    pr: dict,
    main: str,
    statuses: list,
    checks: list,
    reviews: list,
    threads: dict,
    run_url: str,
    detail: dict,
) -> None:
    authority = detail["authority"]
    provenance = detail["provenance"]
    if (
        pr.get("state") != "open"
        or pr.get("draft") is not False
        or pr.get("user", {}).get("login") != authority["allowed_actor"]
    ):
        raise GateReject("PR is not an eligible Gate-v2 publisher PR")
    if (
        pr.get("head", {}).get("repo", {}).get("full_name") != REPO
        or pr.get("base", {}).get("repo", {}).get("full_name") != REPO
    ):
        raise GateReject("repository mismatch")
    if not str(pr.get("head", {}).get("ref") or "").startswith(
        authority["branch_prefix"]
    ):
        raise GateReject("provider branch is outside standing authority")
    if provenance["candidate_sha"] != pr["head"]["sha"]:
        raise GateReject("candidate provenance/head mismatch")
    if (
        provenance["base_sha"] != main
        or pr["base"]["sha"] != main
        or pr["base"]["ref"] != "main"
    ):
        raise GateReject("stale provider base")

    latest = {}
    for status in statuses:
        latest.setdefault(status["context"], status)
    for name in CONTEXTS:
        status = latest.get(name, {})
        if (
            status.get("state") != "success"
            or status.get("creator", {}).get("login") != "github-actions[bot]"
            or status.get("target_url") != run_url
        ):
            raise GateReject("missing, failed or untrusted required gate: " + name)
    if any(
        status.get("state") in ("failure", "error", "pending")
        for status in latest.values()
    ):
        raise GateReject("unresolved status")

    external_checks = [
        check for check in checks if not is_current_merge_check(check, run_url)
    ]
    if any(
        check.get("status") != "completed"
        or check.get("conclusion") not in ("success", "neutral", "skipped")
        for check in external_checks
    ):
        raise GateReject("unresolved check")

    latest_review = {}
    for review in reviews:
        if review.get("state") != "COMMENTED":
            latest_review[review["user"]["login"]] = review["state"]
    if any(
        state in ("CHANGES_REQUESTED", "PENDING")
        for state in latest_review.values()
    ):
        raise GateReject("unresolved review rejection")

    if (
        threads.get("pageInfo", {}).get("hasNextPage") is not False
        or any(
            thread.get("isResolved") is not True
            for thread in threads.get("nodes", [])
        )
    ):
        raise GateReject("unresolved or incomplete review threads")

    if not is_current_merge_policy_state(pr, checks, run_url):
        raise GateReject("provider merge policy is not clean")

    assert_verified_candidate_commit(pr["head"]["sha"])


def assert_pages_source(pages: dict) -> None:
    if (
        pages.get("build_type") != "legacy"
        or pages.get("source") != {"branch": "main", "path": "/"}
        or pages.get("cname") != "offbeatinc.com"
    ):
        raise GateReject("unexpected Offbeat Pages publishing source")


def request_pages_build(merge_sha: str) -> dict:
    if gh("api", f"repos/{REPO}/git/ref/heads/main")["object"]["sha"] != merge_sha:
        raise GateReject("main moved before Pages build request")
    result = gh("api", "--method", "POST", f"repos/{REPO}/pages/builds")
    if result.get("status") not in ("queued", "building", "built"):
        raise GateReject("Pages build request was not accepted")
    return result


def assert_exact_merge_parentage(
    merge_sha: str,
    *,
    base_sha: str,
    candidate_sha: str,
) -> None:
    commit = gh("api", f"repos/{REPO}/commits/{merge_sha}")
    parents = [parent.get("sha") for parent in commit.get("parents", [])]
    if parents != [base_sha, candidate_sha]:
        raise GateReject(
            "merge parentage mismatch: " + json.dumps(parents, sort_keys=True)
        )


def main() -> None:
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    number = event["pull_request"]["number"]
    pr = gh("api", f"repos/{REPO}/pulls/{number}")
    sha = pr["head"]["sha"]
    if sha != event["pull_request"]["head"]["sha"]:
        raise GateReject("PR changed after review")

    detail = validate_candidate(Path.cwd(), {"pull_request": pr}, sha)
    verify_t1(detail)

    query = (
        'query($number:Int!){repository(owner:"CrashyCrash",name:"offbeat-website")'
        "{pullRequest(number:$number){reviewThreads(first:100)"
        "{nodes{isResolved} pageInfo{hasNextPage}}}}}"
    )
    run_url = f'https://github.com/{REPO}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'

    # GitHub can briefly expose a just-completed sibling check as unresolved
    # when the dependent merge job starts. Retry only those transient provider
    # index states; every authority, provenance, stale-base, review, or gate
    # rejection remains immediately terminal.
    for readiness_attempt in range(6):
        pr = gh("api", f"repos/{REPO}/pulls/{number}")
        if sha != pr["head"]["sha"] or sha != event["pull_request"]["head"]["sha"]:
            raise GateReject("PR changed after review")
        statuses = gh("api", f"repos/{REPO}/commits/{sha}/statuses?per_page=100")
        checks = gh("api", f"repos/{REPO}/commits/{sha}/check-runs?per_page=100")
        reviews = gh("api", f"repos/{REPO}/pulls/{number}/reviews?per_page=100")
        if len(statuses) >= 100 or checks["total_count"] >= 100 or len(reviews) >= 100:
            raise GateReject("incomplete provider evidence pagination")
        threads = gh(
            "api",
            "graphql",
            "-f",
            "query=" + query,
            "-F",
            "number=" + str(number),
        )["data"]["repository"]["pullRequest"]["reviewThreads"]
        base = gh("api", f"repos/{REPO}/git/ref/heads/main")["object"]["sha"]
        try:
            assert_merge_ready(
                pr,
                base,
                statuses,
                checks["check_runs"],
                reviews,
                threads,
                run_url,
                detail,
            )
            break
        except GateReject as exc:
            if (
                str(exc) not in TRANSIENT_READINESS_ERRORS
                or readiness_attempt == 5
            ):
                raise
            time.sleep(2)
    assert_pages_source(gh("api", f"repos/{REPO}/pages"))

    result = gh(
        "api",
        "--method",
        "PUT",
        f"repos/{REPO}/pulls/{number}/merge",
        body={
            "sha": sha,
            "merge_method": "merge",
            "commit_title": (
                f"Merge governed DatBotty Gate-v2 candidate {sha[:12]} (#{number})"
            ),
        },
    )
    if result.get("merged") is not True:
        raise GateReject("provider refused merge")
    merge_sha = result["sha"]
    assert_exact_merge_parentage(
        merge_sha,
        base_sha=base,
        candidate_sha=sha,
    )

    print(
        json.dumps(
            {
                "candidate_sha": sha,
                "base_sha": base,
                "merge_sha": merge_sha,
                "pr": number,
                "result_tree": detail["result_tree"],
                "effects": detail["computed_effects"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    print(
        json.dumps(
            {
                "merge_sha": merge_sha,
                "pages_build_request": request_pages_build(merge_sha),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
