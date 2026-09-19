#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from datbotty_gate_v2 import (
    GateReject,
    canonical,
    validate_candidate,
    verify_t1,
)


AUTHORITY = {
    "schema_version": 2,
    "halt": False,
    "allowed_actor": "DatBotty-v4",
    "branch_prefix": "datbotty/rescue/",
    "project_id": "proj-website-main",
    "max_changed_files": 5,
    "max_target_files": 5,
    "max_changed_lines": 1500,
    "allowed_change_status": ["M"],
    "allowed_path_globs": ["*.html", "sitemap.xml", "robots.txt", "assets/*.css"],
    "protected_path_globs": [
        ".datbotty/**",
        ".github/**",
        "AGENTS.md",
        "PROJECT_BOUNDARY.md",
        "CNAME",
    ],
    "allowed_effects": ["content_write"],
    "forbidden_effects": [
        "trust_root_write",
        "workflow_write",
        "active_content_write",
        "credential_access",
        "account_change",
        "payment",
        "outreach",
        "hardware_change",
    ],
    "allowed_risks": ["R0"],
    "required_verification_checks": [
        "contract_scope",
        "scanner_delta",
        "git_diff_check",
        "sealed_candidate",
        "t1_review",
    ],
    "reviewer_model": "qwen3.6:27b",
    "reviewer_model_digest": "a50eda8ed977ab48a12431878896b27ffd5cef552c17af3317d9623b939a7f1e",
    "review_ttl_seconds": 1800,
    "volatile_claim_evidence_required": True,
}


def git(cwd: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return cp.stdout.strip()


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "fixture@datbotty.invalid")
        git(self.root, "config", "user.name", "Fixture")
        (self.root / ".datbotty").mkdir()
        (self.root / ".datbotty" / "authority.yml").write_text(
            json.dumps(AUTHORITY, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (self.root / "index.html").write_text(
            "<html><head><title>Fixture</title></head><body><h1>Fixture</h1></body></html>\n",
            encoding="utf-8",
        )
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "base")
        self.base = git(self.root, "rev-parse", "HEAD")

    def close(self) -> None:
        self.tmp.cleanup()

    def commit_candidate(self, text: str, *, extra: dict[str, str] | None = None) -> str:
        (self.root / "index.html").write_text(text, encoding="utf-8")
        for path, body in (extra or {}).items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "candidate")
        return git(self.root, "rev-parse", "HEAD")

    def provenance(
        self,
        head: str,
        *,
        target_files: list[str] | None = None,
        changed_files: list[str] | None = None,
        declared_effects: list[str] | None = None,
        volatile_evidence: list[dict] | None = None,
    ) -> dict:
        target_files = target_files or ["index.html"]
        changed_files = changed_files or ["index.html"]
        contract = {
            "contract_id": "fixture-contract",
            "work_package_id": "fixture-package",
            "contract_version": "rescue-v1",
            "project_id": "proj-website-main",
            "opportunity_ids": ["1"],
            "opportunity_type": "metadata_repair",
            "task_type": "metadata_repair",
            "objective": "repair bounded metadata debt",
            "allowed_paths": list(target_files),
            "target_files": list(target_files),
            "verification_requirements": [
                "contract_scope",
                "scanner_delta",
                "git_diff_check",
                "sealed_candidate",
                "t1_review",
            ],
            "forbidden_paths": [".git", ".github", ".datbotty"],
            "allowed_actions": ["read", "edit", "run-tests", "inspect-diff"],
            "required_tools": ["git", "python"],
            "model_profile": {
                "provider": "ollama",
                "model": "ollama/qwen3.8:27b",
                "transport": "opencode-run",
                "temperature": 0.1,
                "max_output_tokens": 4096,
            },
            "context_budget": {"tokens": 64000, "seconds": 1200},
            "wall_clock_budget": {"tokens": 1, "seconds": 1200},
            "risk": "R0",
            "retry_classification": "bounded_single_retry",
            "acceptance_criteria": ["real repair"],
            "expected_result": "bounded verified candidate",
            "publication_policy": {
                "policy_name": "rescue-worker-no-publication",
                "requires_review": True,
                "may_publish": False,
                "allowed_targets": ["candidate-outbox"],
            },
            "verification_profile": {
                "commands": ["git diff --check"],
                "required_checks": [
                    "contract_scope",
                    "scanner_delta",
                    "git_diff_check",
                    "sealed_candidate",
                    "t1_review",
                ],
                "timeout_seconds": 300,
                "live_verification_required": False,
            },
            "source_opportunity": {
                "project_id": "proj-website-main",
                "opportunity_id": "1",
                "dedup_key": "fixture",
                "kind": "metadata_repair",
                "summary": "fixture",
                "discovered_at": "2026-09-19T00:00:00Z",
            },
        }
        contract_hash = digest(contract)
        verification = {
            "passed": True,
            "changed_files": list(changed_files),
            "allowed_files": list(target_files),
            "checks": {
                "contract_scope": {"passed": True},
                "scanner_delta": {"passed": True},
                "git_diff_check": {"passed": True},
                "sealed_candidate": {"passed": True},
            },
        }
        return {
            "schema_version": 2,
            "issuer": "datbotty-rescue-v1",
            "attempt_id": "fixture-attempt",
            "contract_sha256": contract_hash,
            "contract": {"contract_hash": contract_hash, "contract": contract},
            "base_sha": self.base,
            "candidate_sha": head,
            "result_tree": git(self.root, "rev-parse", f"{head}^{{tree}}"),
            "patch_sha256": "1" * 64,
            "manifest_sha256": "2" * 64,
            "changed_files": list(changed_files),
            "target_files": list(target_files),
            "declared_effects": declared_effects or ["content_write"],
            "deterministic": {
                "passed": True,
                "verification": verification,
                "verification_sha256": digest(verification),
            },
            "t1_review": {"payload": {}, "signature": ""},
            "volatile_evidence": volatile_evidence or [],
        }

    def event(self, head: str, provenance: dict, *, actor: str = "DatBotty-v4") -> dict:
        body = (
            "DatBotty rescue candidate.\n\n<!-- datbotty-gate-v2\n"
            + json.dumps(provenance, sort_keys=True, separators=(",", ":"))
            + "\n-->"
        )
        return {
            "pull_request": {
                "body": body,
                "user": {"login": actor},
                "head": {"sha": head, "ref": "datbotty/rescue/fixture"},
                "base": {"sha": self.base, "ref": "main"},
            }
        }


class GateV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def valid_candidate(self) -> tuple[str, dict, dict]:
        head = self.fx.commit_candidate(
            "<html><head><title>Fixture</title><meta name=\"description\" "
            "content=\"Useful summary\"></head><body><h1>Fixture</h1></body></html>\n"
        )
        provenance = self.fx.provenance(head)
        event = self.fx.event(head, provenance)
        return head, provenance, event

    def test_valid_bounded_content_candidate_passes(self):
        head, _p, event = self.valid_candidate()
        detail = validate_candidate(self.fx.root, event, head)
        self.assertEqual(detail["computed_effects"], ["content_write"])
        self.assertEqual(detail["changed_files"], ["index.html"])

    def test_trust_root_self_modification_rejected(self):
        head = self.fx.commit_candidate(
            "<html><head><title>Fixture</title></head><body><h1>Changed</h1></body></html>\n",
            extra={".datbotty/authority.yml": json.dumps({**AUTHORITY, "halt": True})},
        )
        p = self.fx.provenance(
            head,
            target_files=["index.html", ".datbotty/authority.yml"],
            changed_files=["index.html", ".datbotty/authority.yml"],
            declared_effects=["content_write", "trust_root_write"],
        )
        with self.assertRaisesRegex(GateReject, "protected/trust-root"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_scope_escape_rejected(self):
        (self.fx.root / "other.html").write_text("<html>old</html>\n", encoding="utf-8")
        git(self.fx.root, "add", "other.html")
        git(self.fx.root, "commit", "-m", "base other")
        self.fx.base = git(self.fx.root, "rev-parse", "HEAD")
        head = self.fx.commit_candidate(
            "<html><head><title>Fixture</title></head><body>changed</body></html>\n",
            extra={"other.html": "<html>escaped</html>\n"},
        )
        p = self.fx.provenance(
            head,
            target_files=["index.html"],
            changed_files=["index.html", "other.html"],
        )
        with self.assertRaisesRegex(GateReject, "exceed TaskContract targets"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_active_content_forbidden_effect_rejected(self):
        head = self.fx.commit_candidate(
            "<html><head><title>Fixture</title></head>"
            "<body><script src=\"https://evil.invalid/x.js\"></script></body></html>\n"
        )
        p = self.fx.provenance(
            head,
            declared_effects=["active_content_write", "content_write"],
        )
        with self.assertRaisesRegex(GateReject, "forbidden effect"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_provenance_sha_mismatch_rejected(self):
        head, p, _event = self.valid_candidate()
        p["candidate_sha"] = "0" * 40
        with self.assertRaisesRegex(GateReject, "candidate/base SHA mismatch"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_missing_deterministic_evidence_rejected(self):
        head, p, _event = self.valid_candidate()
        p["deterministic"]["verification"]["checks"]["scanner_delta"]["passed"] = False
        p["deterministic"]["verification_sha256"] = digest(
            p["deterministic"]["verification"]
        )
        with self.assertRaisesRegex(GateReject, "scanner_delta"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_volatile_claim_requires_bound_https_evidence(self):
        head = self.fx.commit_candidate(
            "<html><head><title>Fixture</title></head>"
            "<body><p>Available now for $199.</p></body></html>\n"
        )
        p = self.fx.provenance(head)
        with self.assertRaisesRegex(GateReject, "volatile claim lacks bound evidence"):
            validate_candidate(self.fx.root, self.fx.event(head, p), head)

    def test_valid_signed_t1_binding_passes_and_tamper_fails(self):
        head, p, event = self.valid_candidate()
        detail = validate_candidate(self.fx.root, event, head)
        now = int(time.time())
        binding = {
            "contract_sha256": p["contract_sha256"],
            "base_commit": p["base_sha"],
            "result_tree": p["result_tree"],
            "patch_sha256": p["patch_sha256"],
            "manifest_sha256": p["manifest_sha256"],
            "changed_files": p["changed_files"],
            "target_files": p["target_files"],
        }
        verdict = {
            "verdict": "ACCEPT",
            "contract_sha256": p["contract_sha256"],
            "base_commit": p["base_sha"],
            "result_tree": p["result_tree"],
            "patch_sha256": p["patch_sha256"],
            "reason": "bounded useful repair",
        }
        payload = {
            "schema_version": 1,
            "reviewer_source_sha256": "3" * 64,
            "issued_at": now,
            "expires_at": now + 1800,
            "model": AUTHORITY["reviewer_model"],
            "model_digest": AUTHORITY["reviewer_model_digest"],
            "binding": binding,
            "verdict": verdict,
        }

        key = self.fx.root / "key.pem"
        pub = self.fx.root / "pub.pem"
        data = self.fx.root / "payload.bin"
        sig = self.fx.root / "sig.bin"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(pub)],
            check=True,
            capture_output=True,
        )
        data.write_bytes(canonical(payload))
        subprocess.run(
            [
                "openssl",
                "pkeyutl",
                "-sign",
                "-inkey",
                str(key),
                "-rawin",
                "-in",
                str(data),
                "-out",
                str(sig),
            ],
            check=True,
            capture_output=True,
        )
        detail["provenance"]["t1_review"] = {
            "payload": payload,
            "signature": base64.b64encode(sig.read_bytes()).decode(),
        }
        verified = verify_t1(detail, public_key=pub, now=now)
        self.assertEqual(verified["verdict"]["verdict"], "ACCEPT")

        detail["provenance"]["t1_review"]["payload"]["binding"]["result_tree"] = "f" * 40
        with self.assertRaisesRegex(GateReject, "binding"):
            verify_t1(detail, public_key=pub, now=now)


if __name__ == "__main__":
    unittest.main()
