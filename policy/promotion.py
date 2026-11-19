"""Decide whether a pull request follows the official promotion matrix.

GitHub rulesets can bind rules to a target branch. They cannot express which
source branch is allowed to merge into that target. This module is that
decision. Callers exit with ``decision.exit_code`` so a blocked route is a
failed status check.
"""

from __future__ import annotations

from dataclasses import dataclass

from policy.branches import branch_spec, normalize_branch

REASON_PUBLISH = (
    "Code is reviewed, linted, compiled, and published to Artifact Registry."
)
REASON_UAT = "Deploys validated build artifacts to UAT for end-to-end testing."
REASON_UAT_BLOCK = (
    "Rejects direct feature branches. Changes must merge into main first."
)
REASON_PROD = (
    "Promotes thoroughly tested UAT bundles into live Production runtime."
)
REASON_PROD_BLOCK = (
    "Blocks direct feature PRs and blocks skipping UAT (main -> prod)."
)
REASON_SANDBOX = (
    "Free experimentation in non-governed branches without promotion gates."
)
REASON_LOOKALIKE = (
    "Blocked because the target branch matches a governed branch except for case. "
    "Governed names must be exact."
)
REASON_MISSING = "Source and target branches are required."


@dataclass(frozen=True)
class RouteDecision:
    allowed: bool
    exit_code: int
    target_type: str
    action: str
    reason: str
    source: str
    target: str
    tenant: str

    def format(self) -> str:
        status = "ALLOWED" if self.allowed else "BLOCKED"
        return (
            f"{status}  {self.source or '(empty)'} -> {self.target or '(empty)'}  "
            f"{self.target_type}  {self.action}  exit {self.exit_code}\n"
            f"{self.reason}"
        )


def _lookalike(branch: str, governed: frozenset[str]) -> bool:
    exact = {name.casefold(): name for name in governed}
    canonical = exact.get(branch.casefold())
    return canonical is not None and branch != canonical


def evaluate(source: str | None, target: str | None, tenant: str) -> RouteDecision:
    """Return the official decision for one pull request route.

    ``tenant`` is the repository's tenant, not a guess from the branch name.
    In the ``acme`` repository the branch ``pse`` is sandbox. In the ``pse``
    repository the branch ``pse`` is production.
    """

    spec = branch_spec(tenant)
    head = normalize_branch(source)
    base = normalize_branch(target)
    common = {
        "source": head,
        "target": base,
        "tenant": spec.tenant,
    }

    if not head or not base:
        return RouteDecision(
            allowed=False,
            exit_code=1,
            target_type="invalid",
            action="reject",
            reason=REASON_MISSING,
            **common,
        )

    if _lookalike(base, spec.governed):
        return RouteDecision(
            allowed=False,
            exit_code=1,
            target_type="lookalike",
            action="reject",
            reason=f"{REASON_LOOKALIKE} Route {head} -> {base}.",
            **common,
        )

    if base in spec.integration:
        return RouteDecision(
            allowed=True,
            exit_code=0,
            target_type="integration",
            action="build_and_publish",
            reason=REASON_PUBLISH,
            **common,
        )

    if base in spec.uat:
        if head == "main":
            return RouteDecision(
                allowed=True,
                exit_code=0,
                target_type="uat",
                action="deploy_uat",
                reason=REASON_UAT,
                **common,
            )
        return RouteDecision(
            allowed=False,
            exit_code=1,
            target_type="uat",
            action="reject",
            reason=f"{REASON_UAT_BLOCK} Route {head} -> {base}.",
            **common,
        )

    if base in spec.production:
        if head in spec.uat:
            return RouteDecision(
                allowed=True,
                exit_code=0,
                target_type="production",
                action="promote_prod",
                reason=REASON_PROD,
                **common,
            )
        return RouteDecision(
            allowed=False,
            exit_code=1,
            target_type="production",
            action="reject",
            reason=f"{REASON_PROD_BLOCK} Route {head} -> {base}.",
            **common,
        )

    return RouteDecision(
        allowed=True,
        exit_code=0,
        target_type="sandbox",
        action="sandbox",
        reason=REASON_SANDBOX,
        **common,
    )
