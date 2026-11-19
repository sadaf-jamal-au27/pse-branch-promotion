"""The official route matrix, in the client's words."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy.branches import validate_tenant
from policy.official_matrix import ISOLATION_ROUTES, OFFICIAL_ROUTES
from policy.promotion import (
    REASON_PROD,
    REASON_PROD_BLOCK,
    REASON_PUBLISH,
    REASON_SANDBOX,
    REASON_UAT,
    REASON_UAT_BLOCK,
    evaluate,
)


class OfficialMatrixTest(unittest.TestCase):
    def test_every_official_and_isolation_route(self) -> None:
        for case in (*OFFICIAL_ROUTES, *ISOLATION_ROUTES):
            with self.subTest(case=case.case_id, route=f"{case.source} -> {case.target}"):
                decision = evaluate(case.source, case.target, case.tenant)
                self.assertEqual(decision.allowed, case.allowed)
                self.assertEqual(decision.action, case.action)
                self.assertEqual(decision.target_type, case.target_type)
                self.assertEqual(decision.exit_code, 0 if case.allowed else 1)
                self.assertIn(case.reason_contains, decision.reason)

    def test_blocked_routes_never_publish_or_deploy(self) -> None:
        promoted = {"build_and_publish", "deploy_uat", "promote_prod"}
        for case in (*OFFICIAL_ROUTES, *ISOLATION_ROUTES):
            if case.allowed:
                continue
            decision = evaluate(case.source, case.target, case.tenant)
            self.assertNotIn(decision.action, promoted)
            self.assertEqual(decision.exit_code, 1)

    def test_client_sentence_feature_to_main(self) -> None:
        decision = evaluate("feature/payments", "main", "pse")
        self.assertEqual(decision.exit_code, 0)
        self.assertEqual(decision.reason, REASON_PUBLISH)

    def test_client_sentence_feature_to_uat_exits_1(self) -> None:
        decision = evaluate("feature/payments", "pse-uat", "pse")
        self.assertEqual(decision.exit_code, 1)
        self.assertIn(REASON_UAT_BLOCK, decision.reason)

    def test_client_sentence_main_to_uat(self) -> None:
        decision = evaluate("main", "pse-uat", "pse")
        self.assertEqual(decision.exit_code, 0)
        self.assertEqual(decision.reason, REASON_UAT)

    def test_client_sentence_skipping_uat_exits_1(self) -> None:
        for target in ("prod", "pse"):
            decision = evaluate("main", target, "pse")
            self.assertEqual(decision.exit_code, 1, target)
            self.assertIn(REASON_PROD_BLOCK, decision.reason)

    def test_client_sentence_uat_promotes_to_production(self) -> None:
        decision = evaluate("pse-uat", "pse", "pse")
        self.assertEqual(decision.exit_code, 0)
        self.assertEqual(decision.reason, REASON_PROD)

    def test_client_sentence_sandbox(self) -> None:
        decision = evaluate("feature/payments", "pse-dev", "pse")
        self.assertEqual(decision.exit_code, 0)
        self.assertEqual(decision.reason, REASON_SANDBOX)
        self.assertEqual(decision.action, "sandbox")

    def test_any_branch_can_merge_back_to_main(self) -> None:
        for source in ("pse-uat", "pse", "prod", "pse-dev"):
            decision = evaluate(source, "main", "pse")
            self.assertEqual(decision.action, "build_and_publish", source)
            self.assertEqual(decision.exit_code, 0)

    def test_production_cannot_skip_back_into_uat(self) -> None:
        decision = evaluate("pse", "pse-uat", "pse")
        self.assertEqual(decision.exit_code, 1)
        self.assertIn(REASON_UAT_BLOCK, decision.reason)

    def test_ref_prefix_is_normalized(self) -> None:
        decision = evaluate("refs/heads/main", "refs/heads/pse-uat", "pse")
        self.assertEqual(decision.action, "deploy_uat")
        self.assertEqual(decision.source, "main")
        self.assertEqual(decision.target, "pse-uat")

    def test_lookalike_governed_names_are_blocked(self) -> None:
        for target in ("Main", "UAT", "Prod", "PSE", "PSE-UAT"):
            decision = evaluate("feature/payments", target, "pse")
            self.assertEqual(decision.exit_code, 1, target)
            self.assertEqual(decision.target_type, "lookalike")

    def test_empty_route_is_blocked(self) -> None:
        decision = evaluate("", "main", "pse")
        self.assertEqual(decision.exit_code, 1)
        self.assertEqual(decision.action, "reject")

    def test_reserved_tenant_slugs_fail_closed(self) -> None:
        for slug in ("main", "uat", "prod", "pse-uat", "A", "PSE"):
            with self.assertRaises(ValueError):
                validate_tenant(slug)

    def test_cli_exit_codes_match_the_matrix(self) -> None:
        blocked = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy.cli",
                "--tenant",
                "pse",
                "--source",
                "feature/payments",
                "--target",
                "prod",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(blocked.returncode, 1)
        self.assertIn("skipping UAT", blocked.stderr)

        allowed = subprocess.run(
            [
                sys.executable,
                "-m",
                "policy.cli",
                "--tenant",
                "pse",
                "--source",
                "feature/payments",
                "--target",
                "main",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(allowed.returncode, 0)
        self.assertIn("Artifact Registry", allowed.stdout)


if __name__ == "__main__":
    unittest.main()
