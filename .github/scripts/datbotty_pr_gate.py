#!/usr/bin/env python3
"""Fail-closed deterministic and T1 gates for DatBotty candidate PRs.

The workflow checks out this script from the protected PR base SHA, then reads
the candidate by its literal event SHA.  Candidate-controlled workflow/script
changes therefore cannot weaken the gate being evaluated.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
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
    "accessibility-about-skip-link": ["about.html"],
    "accessibility-reduced-motion": ["assets/style.css"],
}
PACKAGE_PURPOSE = {
    "canary-sitemap-lastmod": "Correct sitemap lastmod dates using existing page Git history only.",
    "bootstrap-robots-cleanup": "Remove invalid markup; retain the minimal public crawler policy.",
    "accessibility-about-skip-link": "Add the existing site skip-link pattern to About so keyboard users can bypass navigation.",
    "accessibility-reduced-motion": "Respect reduced-motion preferences by disabling smooth scrolling only for users requesting reduced motion.",
}
SKIP_LINK = '<a class="skip-link" href="#main-content">Skip to content</a>'
MOTION_RULE = '@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }'
T1_RE = re.compile(r"<!-- datbotty-t1\s*\n(.*?)\n-->", re.DOTALL)
PUBLIC_KEY = Path(__file__).with_name("reviewer-public.pem")
REVIEW_MODEL_DIGEST = "a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e"
REVIEW_TTL_SECONDS = 1800


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def strict_json(raw: str) -> object:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise GateReject("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


class GateReject(RuntimeError):
    pass


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "--no-pager", "--no-replace-objects", "-c", "safe.directory=" + str(repo.resolve()), "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", *args], cwd=repo, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise GateReject(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def parse_provenance(body: str) -> dict:
    matches = PROVENANCE_RE.findall(body or "")
    if len(matches) != 1:
        raise GateReject("missing datbotty provenance block")
    try:
        value = strict_json(matches[0])
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
    if not all(v is True for v in value["deterministic_checks"].values()):
        raise GateReject("execution deterministic checks did not all pass")
    return value


def check_accessibility(package: str, before: str, after: str) -> str:
    if package == "accessibility-about-skip-link":
        if SKIP_LINK in before or before.count('<body>') != 1 or before.count('id="main-content"') != 1:
            raise GateReject("skip link not eligible or target ambiguous")
        if after.strip() != before.replace('<body>', '<body>' + SKIP_LINK).strip():
            raise GateReject("only the existing site skip-link insertion is authorized")
    elif package == "accessibility-reduced-motion":
        if "prefers-reduced-motion" in before or "scroll-behavior: smooth" not in before:
            raise GateReject("reduced motion repair not eligible")
        if not after.startswith(before.rstrip()):
            raise GateReject("existing stylesheet changed")
        addition = after[len(before.rstrip()):]
        if re.sub(r"\s+", "", addition) != re.sub(r"\s+", "", MOTION_RULE):
            raise GateReject("only the bounded reduced-motion override is authorized")
    else:
        raise GateReject("unknown accessibility package")
    return "bounded accessibility repair verified"


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
    if not re.fullmatch(r"[0-9a-f]{40}", head) or pr.get("base", {}).get("ref") != "main":
        raise GateReject("invalid SHA or base branch")
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
    if git(repo, "rev-list", "--parents", "-n", "1", head).split() != [head, parent]:
        raise GateReject("candidate must have exactly one parent")
    if provenance["base_sha"] != parent or pr.get("base", {}).get("sha") != parent:
        raise GateReject("candidate parent, provenance base, and PR base are not identical")
    changed = sorted(filter(None, git(repo, "diff", "--name-only", f"{parent}..{head}").splitlines()))
    if changed != PROFILE_FILES[provenance["package_id"]]:
        raise GateReject(f"changed paths {changed!r} are not the exact profile authorization")
    git(repo, "diff", "--no-ext-diff", "--no-textconv", "--check", parent, head)
    for path in changed:
        if not git(repo, "ls-tree", head, "--", path).startswith("100644 blob "):
            raise GateReject("candidate must contain regular non-executable files")
    if provenance["package_id"] == "bootstrap-robots-cleanup":
        return check_robots(repo, head)
    if provenance["package_id"].startswith("accessibility-"):
        path = changed[0]
        return check_accessibility(provenance["package_id"], git(repo, "show", f"{parent}:{path}"), git(repo, "show", f"{head}:{path}"))
    return check_sitemap(repo, head, parent)


def review_packet(repo: Path, provenance: dict, detail: str) -> dict:
    head, base = provenance["candidate_sha"], provenance["base_sha"]
    diff = git(repo, "diff", "--no-color", "--no-ext-diff", "--no-textconv", "--diff-algorithm=myers", "--src-prefix=a/", "--dst-prefix=b/", "--unified=3", base, head, "--")
    if not diff or len(diff.encode()) > 100_000:
        raise GateReject("empty or oversized review diff")
    packet = {"repository": "CrashyCrash/offbeat-website", "provenance": provenance,
              "package_purpose": PACKAGE_PURPOSE[provenance["package_id"]], "risk_class": "low",
              "deterministic_result": {"verdict": "PASS", "detail": detail}, "diff": diff}
    # A diff alone can omit semantic dependencies (e.g. the target anchor and
    # existing skip-link CSS). Bind exact candidate blobs, never executor prose.
    paths = list(PROFILE_FILES[provenance["package_id"]])
    if provenance["package_id"] == "accessibility-about-skip-link":
        paths.append("assets/style.css")
    packet["candidate_files"] = {path: git(repo, "show", f"{head}:{path}") for path in paths}
    if len(canonical(packet)) > 100_000:
        raise GateReject("oversized semantic review context")
    return packet


def reviewer_source_digest() -> str:
    folder = Path(__file__).resolve().parent
    return hashlib.sha256((folder / "datbotty_pr_gate.py").read_bytes() + (folder / "t1_reviewer.py").read_bytes()).hexdigest()


def parse_verdict(raw: str, packet: dict) -> dict:
    verdict = strict_json(raw)
    fields = {"verdict", "candidate_sha", "base_sha", "context_sha256", "reason"}
    if not isinstance(verdict, dict) or set(verdict) != fields:
        raise GateReject("malformed semantic verdict")
    p = packet["provenance"]
    if (verdict["candidate_sha"] != p["candidate_sha"] or verdict["base_sha"] != p["base_sha"]
            or verdict["context_sha256"] != digest(packet)):
        raise GateReject("semantic verdict binding mismatch")
    if verdict["verdict"] not in ("ACCEPT", "REJECT") or not isinstance(verdict["reason"], str) or not 1 <= len(verdict["reason"].strip()) <= 2000:
        raise GateReject("ambiguous semantic verdict")
    return verdict


def verify_t1(repo: Path, body: str, packet: dict, public_key: Path | None = None) -> dict:
    matches = T1_RE.findall(body or "")
    if len(matches) != 1:
        raise GateReject("missing or ambiguous T1 envelope")
    envelope = strict_json(matches[0])
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        raise GateReject("invalid T1 envelope")
    payload = envelope["payload"]
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "reviewer_source_sha256", "model", "model_digest", "issued_at", "expires_at", "verdict"}:
        raise GateReject("invalid signed T1 payload")
    if payload["schema_version"] != 1 or payload["reviewer_source_sha256"] != reviewer_source_digest() or payload["model"] != "qwen3.6:27b":
        raise GateReject("T1 reviewer source/model mismatch")
    if payload["model_digest"] != REVIEW_MODEL_DIGEST:
        raise GateReject("missing T1 model digest")
    issued, expires = payload["issued_at"], payload["expires_at"]
    now = time.time()
    if (type(issued) is not int or type(expires) is not int
            or expires - issued != REVIEW_TTL_SECONDS
            or issued > now + 30 or now >= expires):
        raise GateReject("expired, future or invalid T1 validity window")
    key = public_key or PUBLIC_KEY
    with tempfile.TemporaryDirectory(prefix="datbotty-t1-verify-") as tmp:
        data, sig = Path(tmp) / "data", Path(tmp) / "sig"
        data.write_bytes(canonical(payload))
        sig.write_bytes(base64.b64decode(envelope["signature"], validate=True))
        result = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key), "-rawin", "-in", str(data), "-sigfile", str(sig)], capture_output=True, timeout=10)
        if result.returncode:
            raise GateReject("untrusted T1 signature")
    verdict = parse_verdict(json.dumps(payload["verdict"]), packet)
    if verdict["verdict"] != "ACCEPT":
        raise GateReject("T1 REJECT: " + verdict["reason"])
    return payload


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
        if args.mode == "t1":
            provenance = parse_provenance(event["pull_request"]["body"])
            payload = verify_t1(repo, event["pull_request"]["body"], review_packet(repo, provenance, detail))
            detail = payload["verdict"]["reason"]
    except (GateReject, OSError, json.JSONDecodeError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print(f"{args.mode.upper()} REJECT: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()} ACCEPT: {detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
