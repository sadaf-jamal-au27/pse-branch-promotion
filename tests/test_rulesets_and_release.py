"""Rulesets, artifact identity, lint, and workflow triggers stay in one contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy.artifacts import artifact_uri
from policy.branches import branch_spec
from policy.inventory import parse_inventory
from policy.lint import lint_tree
from policy.release import ReleaseRejected, execute, publish_main
from policy.render import render_callers
from policy.rulesets import (
    JOBS,
    desired_rulesets,
    plan_changes,
    status_check_context,
)


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def _checks(payload: dict) -> list[str]:
    for rule in payload["rules"]:
        if rule["type"] == "required_status_checks":
            return [item["context"] for item in rule["parameters"]["required_status_checks"]]
    raise AssertionError("status checks missing")


class RulesetContractTest(unittest.TestCase):
    def test_three_rulesets_and_no_sandbox_branch(self) -> None:
        payloads = desired_rulesets("pse", "local")
        self.assertEqual(len(payloads), 3)
        names = [item["name"] for item in payloads]
        self.assertEqual(
            names,
            [
                "enterprise-integration-main",
                "enterprise-uat-gate",
                "enterprise-production-gate",
            ],
        )
        encoded = json.dumps(payloads)
        self.assertNotIn("pse-dev", encoded)
        self.assertNotIn("refs/heads/*", encoded)
        self.assertNotIn("policy-tests", encoded)

    def test_branch_includes_follow_the_tenant_spec(self) -> None:
        spec = branch_spec("pse")
        by_name = {item["name"]: item for item in desired_rulesets("pse")}
        self.assertEqual(
            by_name["enterprise-integration-main"]["conditions"]["ref_name"]["include"],
            ["refs/heads/main"],
        )
        self.assertEqual(
            by_name["enterprise-uat-gate"]["conditions"]["ref_name"]["include"],
            [f"refs/heads/{branch}" for branch in spec.uat],
        )
        self.assertEqual(
            by_name["enterprise-production-gate"]["conditions"]["ref_name"]["include"],
            [f"refs/heads/{branch}" for branch in spec.production],
        )

    def test_reviews_checks_and_no_bypass(self) -> None:
        by_name = {item["name"]: item for item in desired_rulesets("pse", "local")}
        expectations = {
            "enterprise-integration-main": (1, False, "integration"),
            "enterprise-uat-gate": (1, False, "uat"),
            "enterprise-production-gate": (2, True, "production"),
        }
        for name, (reviews, last_push, gate) in expectations.items():
            payload = by_name[name]
            self.assertEqual(payload["bypass_actors"], [])
            self.assertEqual(payload["enforcement"], "active")
            rule_types = [rule["type"] for rule in payload["rules"]]
            self.assertEqual(
                rule_types,
                ["pull_request", "required_status_checks", "deletion", "non_fast_forward"],
            )
            pull = payload["rules"][0]["parameters"]
            self.assertEqual(pull["required_approving_review_count"], reviews)
            self.assertEqual(pull["require_last_push_approval"], last_push)
            self.assertEqual(
                _checks(payload),
                [status_check_context(job, "local") for job in JOBS[gate]],
            )
            status = payload["rules"][1]["parameters"]
            self.assertTrue(status["strict_required_status_checks_policy"])

    def test_reusable_callers_use_the_prefixed_check_name(self) -> None:
        payloads = desired_rulesets("acme", "reusable")
        uat = next(item for item in payloads if item["name"] == "enterprise-uat-gate")
        self.assertEqual(
            _checks(uat),
            [
                "promotion-policy / promotion-policy",
                "deploy-uat / deploy-uat",
            ],
        )
        self.assertIn("refs/heads/acme-uat", json.dumps(uat))
        self.assertNotIn("pse-uat", json.dumps(payloads))

    def test_plan_is_idempotent_and_detects_drift(self) -> None:
        desired = desired_rulesets("pse")
        created = plan_changes([], desired)
        self.assertEqual([item.action for item in created], ["create", "create", "create"])

        existing = []
        for index, payload in enumerate(desired, start=1):
            current = json.loads(json.dumps(payload))
            current["id"] = index
            current["source"] = "Repository"
            existing.append(current)
        same = plan_changes(existing, desired)
        self.assertTrue(all(item.action == "unchanged" for item in same))

        drifted = json.loads(json.dumps(existing))
        drifted[2]["rules"][0]["parameters"]["required_approving_review_count"] = 1
        plan = plan_changes(drifted, desired)
        self.assertEqual([item.action for item in plan], ["unchanged", "unchanged", "update"])
        self.assertEqual(plan[2].ruleset_id, 3)

    def test_inventory_and_dry_run(self) -> None:
        rows = parse_inventory((ROOT / "tenants.example.csv").read_text(encoding="utf-8"))
        self.assertEqual([(row.tenant, row.caller_style) for row in rows], [("pse", "local"), ("acme", "reusable")])
        with self.assertRaises(ValueError):
            parse_inventory("not-a-repo,pse\n")

        completed = subprocess.run(
            [
                sys.executable,
                "scripts/configure_rulesets.py",
                "--repo",
                "OWNER/github-abacus-task",
                "--tenant",
                "pse",
                "--caller-style",
                "local",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Dry run", completed.stdout)
        self.assertIn("enterprise-production-gate", completed.stdout)
        self.assertNotIn("created", completed.stdout)


class ReleaseAndLintTest(unittest.TestCase):
    def test_the_same_digest_is_promoted_without_recompile(self) -> None:
        sha = "0123456789abcdef"
        published = execute("publish", "feature/payments", "main", "pse", sha)
        deployed = execute("uat", "main", "pse-uat", "pse", sha)
        promoted = execute("prod", "pse-uat", "prod", "pse", sha)
        self.assertEqual(published["uri"], artifact_uri("pse", sha))
        self.assertEqual(published["uri"], deployed["uri"])
        self.assertEqual(deployed["uri"], promoted["uri"])
        self.assertEqual(deployed["compilation"], "not-performed")
        self.assertEqual(promoted["compilation"], "not-performed")
        self.assertEqual(publish_main("pse", sha)["uri"], published["uri"])
        self.assertTrue(published["immutable"])

    def test_a_blocked_route_cannot_publish_or_promote(self) -> None:
        with self.assertRaises(ReleaseRejected):
            execute("uat", "feature/payments", "pse-uat", "pse", "abc")
        with self.assertRaises(ReleaseRejected):
            execute("prod", "main", "prod", "pse", "abc")
        with self.assertRaises(ReleaseRejected):
            execute("publish", "feature/payments", "pse-dev", "pse", "abc")

    def test_lint_passes_the_pilot_and_rejects_bad_files(self) -> None:
        self.assertEqual(lint_tree(ROOT / "src"), [])
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            broken = directory / "broken.py"
            broken.write_text("def broken(:\n    pass\n", encoding="utf-8")
            self.assertTrue(lint_tree(directory))
            broken.write_text("def fine():\n    breakpoint()\n", encoding="utf-8")
            problems = lint_tree(directory)
            self.assertTrue(any("debugger" in problem for problem in problems))


class WorkflowContractTest(unittest.TestCase):
    def test_pilot_workflows_trigger_the_governed_branches(self) -> None:
        spec = branch_spec("pse")
        policy = _workflow("promotion-policy.yml")
        self.assertNotIn("\n    branches:\n", policy)
        build = _workflow("build-and-publish.yml")
        self.assertIn("      - main\n", build)
        self.assertIn("policy.lint", build)
        self.assertIn("--stage publish", build)
        self.assertIn("publish-main:", build)
        self.assertIn("--stage publish-main", build)
        self.assertIn("github.event_name == 'push'", build)
        deploy = _workflow("deploy-uat.yml")
        promote = _workflow("promote-prod.yml")
        for branch in spec.uat:
            self.assertIn(f"      - {branch}\n", deploy)
        for branch in spec.production:
            self.assertIn(f"      - {branch}\n", promote)
        for text in (deploy, promote):
            self.assertNotIn("policy.lint", text)
        self.assertIn("--stage uat", deploy)
        self.assertIn("--stage prod", promote)

    def test_rendered_callers_match_the_ruleset_branches(self) -> None:
        spec = branch_spec("pse")
        files = render_callers("pse", "acme/platform-workflows", "v1")
        self.assertNotIn("branches:", files["promotion-policy.yml"])
        for branch in spec.uat:
            self.assertIn(f"      - {branch}\n", files["deploy-uat.yml"])
        for branch in spec.production:
            self.assertIn(f"      - {branch}\n", files["promote-prod.yml"])
        self.assertIn(
            "uses: acme/platform-workflows/.github/workflows/deploy-uat.yml@v1\n",
            files["deploy-uat.yml"],
        )
        self.assertIn("tenant: pse\n", files["promote-prod.yml"])

        rules = {item["name"]: item for item in desired_rulesets("pse", "reusable")}
        self.assertEqual(
            rules["enterprise-uat-gate"]["conditions"]["ref_name"]["include"],
            [f"refs/heads/{branch}" for branch in spec.uat],
        )


if __name__ == "__main__":
    unittest.main()
