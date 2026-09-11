#!/usr/bin/env python3
"""Fail-closed deterministic and T1 gates for DatBotty candidate PRs.

The workflow checks out this script from the protected PR base SHA, then reads
the candidate by its literal event SHA.  Candidate-controlled workflow/script
changes therefore cannot weaken the gate being evaluated.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse


PROVENANCE_RE = re.compile(r"<!-- datbotty-provenance\s*\n(.*?)\n-->", re.DOTALL)
REQUIRED_FIELDS = {
    "schema_version",
    "candidate_id",
    "candidate_sha",
    "candidate_ref",
    "base_sha",
    "execution_flow_run_id",
    "package_id",
    "target_files",
    "deterministic_checks",
}
PROFILE_FILES = {
    "canary-sitemap-lastmod": ["sitemap.xml"],
    "bootstrap-robots-cleanup": ["robots.txt"],
}


class GateReject(RuntimeError):
    pass


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise GateReject(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def parse_provenance(body: str) -> dict:
    match = PROVENANCE_RE.search(body or "")
    if not match:
        raise GateReject("missing datbotty provenance block")
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise GateReject(f"invalid datbotty provenance JSON: {exc}") from exc
    if not isinstance(value, dict) or set(value) != REQUIRED_FIELDS:
        raise GateReject("provenance fields are missing or ambiguous")
    if value["schema_version"] != 1:
        raise GateReject("unsupported provenance schema")
    if not isinstance(value["target_files"], list) or not all(isinstance(item, str) for item in value["target_files"]):
        raise GateReject("invalid provenance target_files")
    if not isinstance(value["deterministic_checks"], dict) or not value["deterministic_checks"]:
        raise GateReject("missing deterministic-check provenance")
    if not all(value["deterministic_checks"].values()):
        raise GateReject("execution deterministic checks did not all pass")
    return value


def check_robots(repo: Path, head: str) -> str:
    text = git(repo, "show", f"{head}:robots.txt")
    if "<!--" in text or "-->" in text or "~~" in text:
        raise GateReject("robots.txt contains non-robots markup")
    directives = []
    pattern = re.compile(r"^(user-agent|allow|disallow|sitemap):\s*(.*)$", re.IGNORECASE)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise GateReject(f"invalid robots directive: {line!r}")
        directives.append((match.group(1).lower(), match.group(2).strip()))
    expected = [
        ("user-agent", "*"),
        ("disallow", ""),
        ("sitemap", "https://offbeatinc.com/sitemap.xml"),
    ]
    if directives != expected:
        raise GateReject("robots.txt is not the approved minimal crawler policy")
    return "robots policy is exact"


def sitemap_entries(xml_text: str) -> list[tuple[str, str]]:
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.fromstring(xml_text)
    if root.tag != f"{{{namespace}}}urlset":
        raise GateReject(f"unexpected sitemap root {root.tag!r}")
    return [
        (
            item.findtext(f"{{{namespace}}}loc") or "",
            item.findtext(f"{{{namespace}}}lastmod") or "",
        )
        for item in root.findall(f"{{{namespace}}}url")
    ]


def check_sitemap(repo: Path, head: str, parent: str) -> str:
    before = sitemap_entries(git(repo, "show", f"{parent}:sitemap.xml"))
    after = sitemap_entries(git(repo, "show", f"{head}:sitemap.xml"))
    if len(before) != len(after) or [loc for loc, _ in before] != [loc for loc, _ in after]:
        raise GateReject("sitemap URL count or ordering changed")
    changed = 0
    for (loc, old_date), (_, new_date) in zip(before, after):
        path = urlparse(loc).path.lstrip("/")
        expected = git(repo, "log", "-1", "--format=%ad", "--date=short", parent, "--", path)
        if not path or not expected or new_date != expected:
            raise GateReject(f"sitemap lastmod mismatch for {path!r}")
        changed += old_date != new_date
    if not changed:
        raise GateReject("sitemap candidate has no history-grounded changes")
    return f"sitemap URLs/order/history dates verified ({len(after)} URLs)"


def validate(repo: Path, event: dict, head: str) -> str:
    pr = event.get("pull_request") or {}
    provenance = parse_provenance(pr.get("body") or "")
    if pr.get("user", {}).get("login") != "DatBotty-v4":
        raise GateReject("PR author is not the dedicated publisher identity")
    if pr.get("head", {}).get("sha") != head or provenance["candidate_sha"] != head:
        raise GateReject("PR head and candidate SHA are not identical")
    candidate_id = provenance["candidate_id"]
    if not isinstance(candidate_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,80}", candidate_id):
        raise GateReject("invalid candidate ID")
    if pr.get("head", {}).get("ref") != f"datbotty/{candidate_id}":
        raise GateReject("candidate branch does not match provenance")
    if provenance["candidate_ref"] != f"refs/datbotty/candidates/{candidate_id}":
        raise GateReject("candidate ref does not match provenance")
    if provenance["package_id"] not in PROFILE_FILES:
        raise GateReject("package has no approved verification profile")
    if sorted(provenance["target_files"]) != PROFILE_FILES[provenance["package_id"]]:
        raise GateReject("provenance target files do not match package profile")
    if not isinstance(provenance["execution_flow_run_id"], str) or not re.fullmatch(r"[0-9a-f-]{36}", provenance["execution_flow_run_id"]):
        raise GateReject("missing or invalid execution-flow provenance")

    parent = git(repo, "rev-parse", f"{head}^")
    if provenance["base_sha"] != parent or pr.get("base", {}).get("sha") != parent:
        raise GateReject("candidate parent, provenance base, and PR base are not identical")
    changed = sorted(filter(None, git(repo, "diff", "--name-only", f"{parent}..{head}").splitlines()))
    if changed != PROFILE_FILES[provenance["package_id"]]:
        raise GateReject(f"changed paths {changed!r} are not the exact profile authorization")
    if provenance["package_id"] == "bootstrap-robots-cleanup":
        return check_robots(repo, head)
    return check_sitemap(repo, head, parent)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--mode", choices=("deterministic", "t1"), required=True)
    args = parser.parse_args()
    try:
        repo = Path(args.repo).resolve()
        event = json.loads(Path(args.event).read_text(encoding="utf-8"))
        git(repo, "cat-file", "-e", f"{args.head}^{{commit}}")
        detail = validate(repo, event, args.head)
    except (GateReject, OSError, json.JSONDecodeError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"{args.mode.upper()} REJECT: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()} ACCEPT: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
