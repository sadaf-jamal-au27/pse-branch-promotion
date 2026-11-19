"""GitHub ruleset payloads for the three governed branch classes.

Three rulesets per repository, sixteen repositories, is the 48-screen manual
task this module replaces. Sandbox branches are absent on purpose: the client
matrix leaves them ungated.

``caller_style`` selects the status-check name GitHub will actually report:

- ``local``: this pilot repository. The workflow runs as a normal job, so the
  check name is the job name (``promotion-policy``).
- ``reusable``: a tenant repository calls the platform workflow. GitHub reports
  ``<caller job> / <called job>``. Both ids are the same word, so the check is
  ``promotion-policy / promotion-policy``. Confirm it on the first pilot PR
  before enforcement is set to active.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from policy.branches import branch_spec

RULESET_NAMES = {
    "integration": "enterprise-integration-main",
    "uat": "enterprise-uat-gate",
    "production": "enterprise-production-gate",
}

# Assumption, easy to change in one place: production needs two approvals.
REVIEW_COUNTS = {
    "integration": 1,
    "uat": 1,
    "production": 2,
}

JOBS = {
    "integration": ("promotion-policy", "build-and-publish"),
    "uat": ("promotion-policy", "deploy-uat"),
    "production": ("promotion-policy", "promote-prod"),
}

_SERVER_FIELDS = {
    "id",
    "node_id",
    "source",
    "source_type",
    "created_at",
    "updated_at",
    "current_user_can_bypass",
    "_links",
    "links",
}


def status_check_context(job: str, caller_style: str) -> str:
    if caller_style == "local":
        return job
    if caller_style == "reusable":
        return f"{job} / {job}"
    raise ValueError("caller_style must be 'local' or 'reusable'.")


def _pull_request_rule(review_count: int, last_push_approval: bool) -> dict:
    return {
        "type": "pull_request",
        "parameters": {
            "required_approving_review_count": review_count,
            "dismiss_stale_reviews_on_push": True,
            "require_code_owner_review": False,
            "require_last_push_approval": last_push_approval,
            "required_review_thread_resolution": True,
            "allowed_merge_methods": ["squash", "merge"],
        },
    }


def _status_rule(contexts: list[str], integration_id: int | None) -> dict:
    checks = []
    for context in contexts:
        check = {"context": context}
        if integration_id is not None:
            check["integration_id"] = integration_id
        checks.append(check)
    return {
        "type": "required_status_checks",
        "parameters": {
            "do_not_enforce_on_create": True,
            "strict_required_status_checks_policy": True,
            "required_status_checks": checks,
        },
    }


def build_ruleset(
    *,
    name: str,
    branches: tuple[str, ...],
    checks: list[str],
    review_count: int,
    last_push_approval: bool,
    integration_id: int | None,
) -> dict:
    return {
        "name": name,
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": {
            "ref_name": {
                "include": [f"refs/heads/{branch}" for branch in branches],
                "exclude": [],
            }
        },
        "rules": [
            _pull_request_rule(review_count, last_push_approval),
            _status_rule(checks, integration_id),
            {"type": "deletion"},
            {"type": "non_fast_forward"},
        ],
    }


def desired_rulesets(
    tenant: str,
    caller_style: str = "local",
    integration_id: int | None = None,
) -> list[dict]:
    spec = branch_spec(tenant)
    gates = {
        "integration": spec.integration,
        "uat": spec.uat,
        "production": spec.production,
    }
    payloads = []
    for gate, branches in gates.items():
        checks = [status_check_context(job, caller_style) for job in JOBS[gate]]
        payloads.append(
            build_ruleset(
                name=RULESET_NAMES[gate],
                branches=branches,
                checks=checks,
                review_count=REVIEW_COUNTS[gate],
                last_push_approval=(gate == "production"),
                integration_id=integration_id,
            )
        )
    return payloads


def canonical(payload: dict) -> str:
    cleaned = {key: value for key, value in payload.items() if key not in _SERVER_FIELDS}
    return json.dumps(cleaned, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class PlanItem:
    action: str
    name: str
    ruleset_id: int | None
    payload: dict


def plan_changes(existing: list[dict], desired: list[dict]) -> list[PlanItem]:
    """Compare live rulesets to the generated ones.

    Rulesets this module does not own are left in place. The script does not
    delete them.
    """

    by_name = {item.get("name"): item for item in existing}
    plan: list[PlanItem] = []
    for want in desired:
        have = by_name.get(want["name"])
        if have is None:
            plan.append(PlanItem("create", want["name"], None, want))
            continue
        ruleset_id = have.get("id")
        if canonical(have) == canonical(want):
            plan.append(PlanItem("unchanged", want["name"], ruleset_id, want))
        else:
            plan.append(PlanItem("update", want["name"], ruleset_id, want))
    return plan
