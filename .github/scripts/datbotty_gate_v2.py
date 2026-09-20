#!/usr/bin/env python3
"""Effects-based provider trust gate for DatBotty rescue candidates.

The workflow executes this file from the protected PR base SHA. Authority is
also loaded from the protected base tree, never from the candidate.
"""
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


class GateReject(RuntimeError):
    pass


PROVENANCE_RE = re.compile(r"<!-- datbotty-gate-v2\s*\n(.*?)\n-->", re.DOTALL)
PUBLIC_KEY = Path(__file__).with_name("reviewer-public.pem")
AUTHORITY_PATH = ".datbotty/authority.yml"

PROVENANCE_FIELDS = {
    "schema_version",
    "issuer",
    "attempt_id",
    "contract_sha256",
    "contract",
    "base_sha",
    "candidate_sha",
    "result_tree",
    "patch_sha256",
    "manifest_sha256",
    "changed_files",
    "target_files",
    "declared_effects",
    "deterministic",
    "t1_review",
    "volatile_evidence",
}

ACTIVE_CONTENT_RE = re.compile(
    r"""(?ix)
    <\s*(?:script|iframe|object|embed)\b
    |<\s*form\b[^>]*\baction\s*=\s*["']https?://
    |\bon(?:load|error|click|submit|focus|mouseover)\s*=
    |javascript\s*:
    """
)

VOLATILE_RE = re.compile(
    r"""(?ix)
    (?:\$\s?\d+(?:[.,]\d+)?)
    |\b(?:price|pricing|sale|discount|coupon|in[\s-]?stock|out[\s-]?of[\s-]?stock|available\s+now)\b
    |\b\d+(?:[.,]\d+)?\s*(?:usd|dollars?)\b
    |\b(?:per|/)\s*(?:month|mo|year|yr)\b
    """
)


def canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


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


def git(repo: Path, *args: str, check: bool = True) -> str:
    cp = subprocess.run(
        [
            "git",
            "--no-pager",
            "--no-replace-objects",
            "-c",
            f"safe.directory={repo.resolve()}",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.fsmonitor=false",
            *args,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if check and cp.returncode:
        raise GateReject(
            f"git {' '.join(args)} failed: {cp.stderr.strip() or cp.stdout.strip()}"
        )
    return cp.stdout.strip()


def load_authority(repo: Path, base_sha: str) -> dict:
    raw = git(repo, "show", f"{base_sha}:{AUTHORITY_PATH}")
    value = strict_json(raw)
    if not isinstance(value, dict) or value.get("schema_version") != 2:
        raise GateReject("unsupported or malformed protected authority")
    required = {
        "schema_version",
        "halt",
        "allowed_actor",
        "branch_prefix",
        "project_id",
        "max_changed_files",
        "max_target_files",
        "max_changed_lines",
        "allowed_change_status",
        "allowed_path_globs",
        "protected_path_globs",
        "allowed_effects",
        "forbidden_effects",
        "allowed_risks",
        "required_verification_checks",
        "reviewer_model",
        "reviewer_model_digest",
        "reviewer_source_sha256",
        "review_ttl_seconds",
        "volatile_claim_evidence_required",
        "volatile_claims_allowed",
    }
    if set(value) != required:
        raise GateReject("protected authority fields are ambiguous")
    if value["halt"] is not False:
        raise GateReject("DatBotty authority is halted on protected base")
    return value


def parse_provenance(body: str) -> dict:
    matches = PROVENANCE_RE.findall(body or "")
    if len(matches) != 1:
        raise GateReject("missing or ambiguous Gate-v2 provenance block")
    value = strict_json(matches[0])
    if not isinstance(value, dict) or set(value) != PROVENANCE_FIELDS:
        raise GateReject("Gate-v2 provenance fields are missing or ambiguous")
    if value["schema_version"] != 2 or value["issuer"] != "datbotty-rescue-v1":
        raise GateReject("unsupported Gate-v2 provenance schema/issuer")
    return value


def _matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _changed_entries(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    output = git(repo, "diff", "--name-status", "--no-renames", base, head, "--")
    entries = []
    for line in output.splitlines():
        if not line.strip():
            continue
        status, path = line.split("\t", 1)
        entries.append((status, path))
    return entries


def _changed_line_count(repo: Path, base: str, head: str) -> int:
    output = git(repo, "diff", "--numstat", base, head, "--")
    total = 0
    for line in output.splitlines():
        if not line.strip():
            continue
        added, deleted, _path = line.split("\t", 2)
        if added == "-" or deleted == "-":
            raise GateReject("binary candidate changes are not authorized")
        total += int(added) + int(deleted)
    return total


def _added_lines(repo: Path, base: str, head: str, path: str) -> list[str]:
    output = git(repo, "diff", "--unified=0", base, head, "--", path)
    lines = []
    for line in output.splitlines():
        if line.startswith("+++") or not line.startswith("+"):
            continue
        lines.append(line[1:])
    return lines


def classify_effects(
    repo: Path,
    base: str,
    head: str,
    changed_files: list[str],
    authority: dict,
) -> list[str]:
    effects = set()
    for path in changed_files:
        if _matches(path, authority["protected_path_globs"]):
            effects.add("trust_root_write")
        if path.startswith(".github/workflows/"):
            effects.add("workflow_write")
        if not _matches(path, authority["protected_path_globs"]):
            effects.add("content_write")
        for line in _added_lines(repo, base, head, path):
            if ACTIVE_CONTENT_RE.search(line):
                effects.add("active_content_write")
    return sorted(effects)


def _validate_contract(provenance: dict, authority: dict) -> dict:
    sealed = provenance["contract"]
    if not isinstance(sealed, dict) or set(sealed) != {"contract_hash", "contract"}:
        raise GateReject("invalid sealed TaskContract record")
    contract = sealed["contract"]
    if not isinstance(contract, dict):
        raise GateReject("invalid TaskContract payload")
    actual_hash = digest(contract)
    if sealed["contract_hash"] != actual_hash or provenance["contract_sha256"] != actual_hash:
        raise GateReject("TaskContract hash mismatch")
    if contract.get("project_id") != authority["project_id"]:
        raise GateReject("TaskContract project mismatch")
    if contract.get("risk") not in authority["allowed_risks"]:
        raise GateReject("TaskContract risk not authorized")
    targets = contract.get("target_files")
    if not isinstance(targets, list) or not targets or not all(
        isinstance(item, str) and item for item in targets
    ):
        raise GateReject("TaskContract target_files malformed")
    if sorted(targets) != sorted(provenance["target_files"]):
        raise GateReject("provenance target_files do not match TaskContract")
    if len(set(targets)) != len(targets) or len(targets) > authority["max_target_files"]:
        raise GateReject("TaskContract target blast radius exceeds authority")
    publication = contract.get("publication_policy")
    if (
        not isinstance(publication, dict)
        or publication.get("requires_review") is not True
        or publication.get("may_publish") is not False
    ):
        raise GateReject("worker TaskContract publication authority is invalid")
    actions = set(contract.get("allowed_actions") or [])
    if actions.intersection({"push", "pr", "merge", "publish"}):
        raise GateReject("worker TaskContract contains provider mutation authority")
    objective = contract.get("objective")
    if not isinstance(objective, str) or not objective.strip():
        raise GateReject("TaskContract objective missing")
    return contract


def _validate_deterministic(
    provenance: dict,
    changed_files: list[str],
    authority: dict,
) -> dict:
    deterministic = provenance["deterministic"]
    if not isinstance(deterministic, dict) or set(deterministic) != {
        "passed",
        "verification",
        "verification_sha256",
    }:
        raise GateReject("deterministic evidence envelope malformed")
    verification = deterministic["verification"]
    if (
        deterministic["passed"] is not True
        or not isinstance(verification, dict)
        or verification.get("passed") is not True
        or deterministic["verification_sha256"] != digest(verification)
    ):
        raise GateReject("deterministic verification binding failed")
    if sorted(verification.get("changed_files") or []) != sorted(changed_files):
        raise GateReject("deterministic changed-file evidence mismatch")
    checks = verification.get("checks")
    if not isinstance(checks, dict):
        raise GateReject("deterministic checks missing")
    for name in authority["required_verification_checks"]:
        if name == "t1_review":
            continue
        check = checks.get(name)
        if not isinstance(check, dict) or check.get("passed") is not True:
            raise GateReject(f"required deterministic evidence missing: {name}")
    return verification


def _validate_volatile_evidence(
    repo: Path,
    base: str,
    head: str,
    changed_files: list[str],
    provenance: dict,
    authority: dict,
) -> None:
    claims: list[tuple[str, str, str]] = []
    for path in changed_files:
        for line in _added_lines(repo, base, head, path):
            normalized = " ".join(line.split())
            if normalized and VOLATILE_RE.search(normalized):
                claims.append(
                    (
                        path,
                        hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
                        normalized,
                    )
                )

    supplied = provenance["volatile_evidence"]
    if not isinstance(supplied, list):
        raise GateReject("volatile_evidence must be a list")

    sealed = provenance.get("contract") or {}
    contract = sealed.get("contract") if isinstance(sealed, dict) else None
    opportunity_type = (
        str(contract.get("opportunity_type") or "")
        if isinstance(contract, dict)
        else ""
    )

    # Enabling evidence-backed fact correction does not grant ordinary rescue
    # tasks authority to introduce commercial facts.
    if opportunity_type != "fact_correction":
        if claims:
            raise GateReject(
                "volatile commercial claims require evidence-bound fact_correction authority"
            )
        if supplied:
            raise GateReject(
                "volatile evidence supplied by a non-fact-correction candidate"
            )
        return

    if authority["volatile_claims_allowed"] is not True:
        raise GateReject(
            "volatile commercial claims are outside protected fact-correction authority"
        )
    if authority["volatile_claim_evidence_required"] is not True:
        raise GateReject("fact-correction authority requires volatile evidence enforcement")
    if len(changed_files) != 1 or len(provenance["target_files"]) != 1:
        raise GateReject("fact correction must be bound to exactly one target file")
    if changed_files != list(provenance["target_files"]):
        raise GateReject("fact correction target/change binding mismatch")

    verification = provenance["deterministic"]["verification"]
    checks = verification.get("checks") if isinstance(verification, dict) else None
    binding = checks.get("fact_evidence_binding") if isinstance(checks, dict) else None
    if not isinstance(binding, dict) or binding.get("passed") is not True:
        raise GateReject("fact correction lacks passed deterministic evidence binding")

    required_binding = {
        "passed",
        "detail",
        "opportunity_id",
        "path",
        "source_research_dedup_key",
        "source_line_sha256",
        "baseline_line_match_count",
        "existing_claim_fragment",
        "baseline_claim_count",
        "candidate_claim_count",
        "old_claim_reduced",
        "normalized_fact",
        "semantic_anchors",
        "semantic_anchor_present",
        "changed_line_count",
        "bounded_delta",
        "active_added_lines",
        "volatile_added_line_count",
        "fact_evidence",
        "fact_evidence_sha256",
        "volatile_evidence",
    }
    if set(binding) != required_binding:
        raise GateReject("fact correction deterministic evidence fields are ambiguous")
    if (
        binding["path"] != changed_files[0]
        or binding["baseline_line_match_count"] != 1
        or binding["old_claim_reduced"] is not True
        or binding["semantic_anchor_present"] is not True
        or binding["bounded_delta"] is not True
        or binding["active_added_lines"] != []
    ):
        raise GateReject("fact correction source/delta binding failed")

    bundle = binding["fact_evidence"]
    if (
        not isinstance(bundle, dict)
        or set(bundle) != {"schema_version", "evidence"}
        or bundle["schema_version"] != 1
        or not isinstance(bundle["evidence"], list)
        or len(bundle["evidence"]) != 1
    ):
        raise GateReject("fact evidence bundle malformed")
    if digest(bundle) != binding["fact_evidence_sha256"]:
        raise GateReject("fact evidence bundle digest mismatch")
    receipt = bundle["evidence"][0]
    required_receipt = {
        "claim_key",
        "normalized_fact",
        "source_url",
        "source_trust_tier",
        "retrieved_at",
        "content_sha256",
        "supporting_excerpt",
        "ttl_seconds",
        "conflict_state",
    }
    if not isinstance(receipt, dict) or set(receipt) != required_receipt:
        raise GateReject("fact evidence receipt malformed")
    if (
        receipt["claim_key"] != binding["source_research_dedup_key"]
        or receipt["normalized_fact"] != binding["normalized_fact"]
        or receipt["source_trust_tier"] != "first_party"
        or receipt["conflict_state"] != "clear"
    ):
        raise GateReject("fact evidence identity/trust binding failed")

    parsed_url = urlsplit(str(receipt["source_url"]))
    if (
        parsed_url.scheme.lower() != "https"
        or not parsed_url.netloc
        or parsed_url.username
        or parsed_url.password
    ):
        raise GateReject("fact evidence source must be credential-free HTTPS")
    content_hash = str(receipt["content_sha256"])
    if not re.fullmatch(r"[0-9a-f]{64}", content_hash):
        raise GateReject("fact evidence content digest malformed")
    excerpt = str(receipt["supporting_excerpt"] or "").strip()
    if not excerpt:
        raise GateReject("fact evidence supporting excerpt missing")

    ttl = receipt["ttl_seconds"]
    if type(ttl) is not int or ttl < 60 or ttl > 7 * 24 * 3600:
        raise GateReject("fact evidence TTL is outside standing authority")
    try:
        retrieved = datetime.fromisoformat(
            str(receipt["retrieved_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except (TypeError, ValueError) as exc:
        raise GateReject("fact evidence retrieval timestamp invalid") from exc
    now = datetime.now(timezone.utc)
    age = (now - retrieved).total_seconds()
    if age < -300 or age > ttl:
        raise GateReject("fact evidence is future-dated or expired")

    expected_items = binding["volatile_evidence"]
    if not isinstance(expected_items, list) or supplied != expected_items:
        raise GateReject("provider volatile evidence differs from deterministic binding")

    indexed: dict[tuple[str, str], dict] = {}
    for item in supplied:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "claim_sha256",
            "fact_evidence_sha256",
            "evidence",
        }:
            raise GateReject("volatile evidence item malformed")
        if (
            item["path"] != changed_files[0]
            or item["fact_evidence_sha256"] != binding["fact_evidence_sha256"]
            or item["evidence"] != receipt
        ):
            raise GateReject("volatile evidence item is not bound to verified provider receipt")
        key = (str(item["path"]), str(item["claim_sha256"]))
        if key in indexed:
            raise GateReject("duplicate volatile evidence binding")
        indexed[key] = item

    claim_keys = {(path, claim_hash) for path, claim_hash, _claim in claims}
    if set(indexed) != claim_keys:
        missing = sorted(claim_keys.difference(indexed))
        extra = sorted(set(indexed).difference(claim_keys))
        raise GateReject(
            f"volatile evidence/claim set mismatch: missing={missing} extra={extra}"
        )
    if binding["volatile_added_line_count"] != len(claims):
        raise GateReject("volatile added-line count differs from deterministic binding")

def validate_candidate(repo: Path, event: dict, head: str) -> dict:
    pr = event.get("pull_request") or {}
    body = pr.get("body") or ""
    provenance = parse_provenance(body)
    base_sha = str(pr.get("base", {}).get("sha") or "")
    authority = load_authority(repo, base_sha)

    if str(pr.get("user", {}).get("login") or "") != authority["allowed_actor"]:
        raise GateReject("PR actor is outside standing DatBotty authority")
    if str(pr.get("head", {}).get("ref") or "").startswith(authority["branch_prefix"]) is False:
        raise GateReject("PR branch is outside standing DatBotty authority")
    if pr.get("base", {}).get("ref") != "main":
        raise GateReject("DatBotty candidates must target main")
    if head != str(pr.get("head", {}).get("sha") or ""):
        raise GateReject("event candidate SHA mismatch")
    if provenance["candidate_sha"] != head or provenance["base_sha"] != base_sha:
        raise GateReject("provenance candidate/base SHA mismatch")

    parents = git(repo, "rev-list", "--parents", "-n", "1", head).split()
    if len(parents) != 2 or parents[0] != head or parents[1] != base_sha:
        raise GateReject("candidate must be exactly one commit on protected base")
    actual_tree = git(repo, "rev-parse", f"{head}^{{tree}}")
    if provenance["result_tree"] != actual_tree:
        raise GateReject("candidate result tree mismatch")

    entries = _changed_entries(repo, base_sha, head)
    changed_files = [path for _status, path in entries]
    if not changed_files or len(changed_files) > authority["max_changed_files"]:
        raise GateReject("candidate changed-file blast radius is empty or excessive")
    if len(set(changed_files)) != len(changed_files):
        raise GateReject("candidate changed paths are ambiguous")
    if sorted(provenance["changed_files"]) != sorted(changed_files):
        raise GateReject("provenance changed_files mismatch")
    if _changed_line_count(repo, base_sha, head) > authority["max_changed_lines"]:
        raise GateReject("candidate changed-line blast radius exceeds authority")

    allowed_status = set(authority["allowed_change_status"])
    for status, path in entries:
        if status not in allowed_status:
            raise GateReject(f"change status not authorized: {status} {path}")
        if _matches(path, authority["protected_path_globs"]):
            raise GateReject(f"protected/trust-root path modified: {path}")
        if not _matches(path, authority["allowed_path_globs"]):
            raise GateReject(f"path outside standing content authority: {path}")

    contract = _validate_contract(provenance, authority)
    targets = list(contract["target_files"])
    if not set(changed_files).issubset(set(targets)):
        raise GateReject("candidate changed paths exceed TaskContract targets")
    for target in targets:
        if _matches(target, authority["protected_path_globs"]):
            raise GateReject(f"TaskContract targets protected path: {target}")
        if not _matches(target, authority["allowed_path_globs"]):
            raise GateReject(f"TaskContract target outside standing authority: {target}")

    computed_effects = classify_effects(
        repo, base_sha, head, changed_files, authority
    )
    if sorted(provenance["declared_effects"]) != computed_effects:
        raise GateReject("declared effects do not match provider classification")
    forbidden = set(computed_effects).intersection(authority["forbidden_effects"])
    if forbidden:
        raise GateReject(f"forbidden effect(s): {sorted(forbidden)}")
    if not set(computed_effects).issubset(set(authority["allowed_effects"])):
        raise GateReject("candidate effect is outside standing authority")

    verification = _validate_deterministic(
        provenance, changed_files, authority
    )
    _validate_volatile_evidence(
        repo, base_sha, head, changed_files, provenance, authority
    )

    return {
        "authority": authority,
        "provenance": provenance,
        "contract": contract,
        "verification": verification,
        "changed_files": changed_files,
        "computed_effects": computed_effects,
        "base_sha": base_sha,
        "head_sha": head,
        "result_tree": actual_tree,
    }


def verify_t1(
    detail: dict,
    *,
    public_key: Path = PUBLIC_KEY,
    now: int | None = None,
) -> dict:
    authority = detail["authority"]
    provenance = detail["provenance"]
    envelope = provenance["t1_review"]
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        raise GateReject("missing or malformed signed T1 envelope")
    payload = envelope["payload"]
    if not isinstance(payload, dict) or set(payload) != {
        "schema_version",
        "reviewer_source_sha256",
        "issued_at",
        "expires_at",
        "model",
        "model_digest",
        "verification_sha256",
        "binding",
        "verdict",
    }:
        raise GateReject("signed T1 payload fields are ambiguous")
    if payload["schema_version"] != 1:
        raise GateReject("unsupported T1 schema")
    if (
        payload["model"] != authority["reviewer_model"]
        or payload["model_digest"] != authority["reviewer_model_digest"]
    ):
        raise GateReject("T1 model identity mismatch")
    if payload["reviewer_source_sha256"] != authority["reviewer_source_sha256"]:
        raise GateReject("T1 reviewer source digest mismatch")
    if payload["verification_sha256"] != provenance["deterministic"]["verification_sha256"]:
        raise GateReject("T1 deterministic evidence hash mismatch")
    issued = payload["issued_at"]
    expires = payload["expires_at"]
    current = int(time.time()) if now is None else now
    if (
        type(issued) is not int
        or type(expires) is not int
        or expires - issued != authority["review_ttl_seconds"]
        or issued > current + 30
        or current >= expires
    ):
        raise GateReject("T1 validity window invalid or expired")

    binding = payload["binding"]
    expected_binding = {
        "contract_sha256": provenance["contract_sha256"],
        "base_commit": provenance["base_sha"],
        "result_tree": provenance["result_tree"],
        "patch_sha256": provenance["patch_sha256"],
        "manifest_sha256": provenance["manifest_sha256"],
        "changed_files": sorted(provenance["changed_files"]),
        "target_files": sorted(provenance["target_files"]),
    }
    if not isinstance(binding, dict) or {
        **binding,
        "changed_files": sorted(binding.get("changed_files") or []),
        "target_files": sorted(binding.get("target_files") or []),
    } != expected_binding:
        raise GateReject("signed T1 binding does not match exact candidate provenance")

    try:
        signature = base64.b64decode(str(envelope["signature"]), validate=True)
    except Exception as exc:
        raise GateReject("invalid T1 signature encoding") from exc
    with tempfile.TemporaryDirectory(prefix="gate-v2-t1-") as tmp:
        data = Path(tmp) / "payload"
        sig = Path(tmp) / "signature"
        data.write_bytes(canonical(payload))
        sig.write_bytes(signature)
        cp = subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-verify",
                "-pubin",
                "-inkey",
                str(public_key),
                "-rawin",
                "-in",
                str(data),
                "-sigfile",
                str(sig),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    if cp.returncode != 0:
        raise GateReject("untrusted T1 signature")

    verdict = payload["verdict"]
    if not isinstance(verdict, dict) or set(verdict) != {
        "verdict",
        "contract_sha256",
        "base_commit",
        "result_tree",
        "patch_sha256",
        "reason",
    }:
        raise GateReject("T1 verdict fields are ambiguous")
    if verdict["verdict"] != "ACCEPT":
        raise GateReject("T1 semantic reviewer rejected candidate")
    for key, provenance_key in (
        ("contract_sha256", "contract_sha256"),
        ("base_commit", "base_sha"),
        ("result_tree", "result_tree"),
        ("patch_sha256", "patch_sha256"),
    ):
        if verdict[key] != provenance[provenance_key]:
            raise GateReject(f"T1 verdict binding mismatch: {key}")
    if not isinstance(verdict["reason"], str) or not verdict["reason"].strip():
        raise GateReject("T1 verdict reason missing")
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
        detail = validate_candidate(repo, event, args.head)
        if args.mode == "t1":
            verify_t1(detail)
            message = "signed T1 binding verified"
        else:
            message = (
                f"effects={detail['computed_effects']} "
                f"paths={detail['changed_files']}"
            )
    except (
        GateReject,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"{args.mode.upper()} REJECT: {exc}", file=sys.stderr)
        return 1
    print(f"{args.mode.upper()} ACCEPT: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
