#!/usr/bin/env python3
from __future__ import annotations

import unittest
from unittest.mock import patch

from datbotty_gate_v2 import GateReject
import datbotty_merge


class MergeV2Tests(unittest.TestCase):
    def test_candidate_commit_must_be_provider_verified(self):
        with patch.object(
            datbotty_merge,
            "gh",
            return_value={
                "commit": {
                    "verification": {
                        "verified": False,
                        "reason": "unsigned",
                    }
                }
            },
        ):
            with self.assertRaisesRegex(GateReject, "provider-verified"):
                datbotty_merge.assert_verified_candidate_commit("1" * 40)

    def test_exact_merge_parentage_required(self):
        base = "1" * 40
        candidate = "2" * 40
        merge = "3" * 40
        with patch.object(
            datbotty_merge,
            "gh",
            return_value={
                "parents": [{"sha": base}, {"sha": candidate}],
            },
        ):
            datbotty_merge.assert_exact_merge_parentage(
                merge,
                base_sha=base,
                candidate_sha=candidate,
            )
        with patch.object(
            datbotty_merge,
            "gh",
            return_value={"parents": [{"sha": base}]},
        ):
            with self.assertRaisesRegex(GateReject, "parentage"):
                datbotty_merge.assert_exact_merge_parentage(
                    merge,
                    base_sha=base,
                    candidate_sha=candidate,
                )

    def test_merge_ready_rejects_status_not_emitted_by_current_actions_run(self):
        run_url = "https://github.com/CrashyCrash/offbeat-website/actions/runs/1"
        base = "1" * 40
        candidate = "2" * 40
        pr = {
            "state": "open",
            "draft": False,
            "user": {"login": "DatBotty-v4"},
            "head": {
                "sha": candidate,
                "ref": "datbotty/rescue/test",
                "repo": {"full_name": datbotty_merge.REPO},
            },
            "base": {
                "sha": base,
                "ref": "main",
                "repo": {"full_name": datbotty_merge.REPO},
            },
            "mergeable": True,
            "mergeable_state": "clean",
        }
        detail = {
            "authority": {
                "allowed_actor": "DatBotty-v4",
                "branch_prefix": "datbotty/rescue/",
            },
            "provenance": {
                "candidate_sha": candidate,
                "base_sha": base,
            },
        }
        statuses = [
            {
                "context": "DatBotty Deterministic Gate",
                "state": "success",
                "creator": {"login": "github-actions[bot]"},
                "target_url": run_url,
            },
            {
                "context": "DatBotty T1 Review",
                "state": "success",
                "creator": {"login": "DatBotty-v4"},
                "target_url": run_url,
            },
        ]
        with self.assertRaisesRegex(GateReject, "untrusted required gate"):
            datbotty_merge.assert_merge_ready(
                pr,
                base,
                statuses,
                [],
                [],
                {"nodes": [], "pageInfo": {"hasNextPage": False}},
                run_url,
                detail,
            )

    def test_merge_ready_rejects_unresolved_review_thread(self):
        run_url = "https://github.com/CrashyCrash/offbeat-website/actions/runs/1"
        base = "1" * 40
        candidate = "2" * 40
        pr = {
            "state": "open",
            "draft": False,
            "user": {"login": "DatBotty-v4"},
            "head": {
                "sha": candidate,
                "ref": "datbotty/rescue/test",
                "repo": {"full_name": datbotty_merge.REPO},
            },
            "base": {
                "sha": base,
                "ref": "main",
                "repo": {"full_name": datbotty_merge.REPO},
            },
            "mergeable": True,
            "mergeable_state": "clean",
        }
        detail = {
            "authority": {
                "allowed_actor": "DatBotty-v4",
                "branch_prefix": "datbotty/rescue/",
            },
            "provenance": {
                "candidate_sha": candidate,
                "base_sha": base,
            },
        }
        statuses = [
            {
                "context": context,
                "state": "success",
                "creator": {"login": "github-actions[bot]"},
                "target_url": run_url,
            }
            for context in sorted(datbotty_merge.CONTEXTS)
        ]
        with patch.object(
            datbotty_merge,
            "assert_verified_candidate_commit",
            return_value=None,
        ):
            with self.assertRaisesRegex(GateReject, "review threads"):
                datbotty_merge.assert_merge_ready(
                    pr,
                    base,
                    statuses,
                    [],
                    [],
                    {
                        "nodes": [{"isResolved": False}],
                        "pageInfo": {"hasNextPage": False},
                    },
                    run_url,
                    detail,
                )


    def test_transient_readiness_errors_are_narrowly_scoped(self):
        self.assertEqual(
            datbotty_merge.TRANSIENT_READINESS_ERRORS,
            {
                "unresolved status",
                "unresolved check",
                "provider merge policy is not clean",
            },
        )
        self.assertNotIn("stale provider base", datbotty_merge.TRANSIENT_READINESS_ERRORS)
        self.assertNotIn(
            "unresolved review rejection",
            datbotty_merge.TRANSIENT_READINESS_ERRORS,
        )
        self.assertNotIn(
            "missing, failed or untrusted required gate: DatBotty T1 Review",
            datbotty_merge.TRANSIENT_READINESS_ERRORS,
        )



if __name__ == "__main__":
    unittest.main()
