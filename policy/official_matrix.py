"""Concrete routes that the client table requires.

The engine is tested against this list. The sentences in ``reason_contains``
are the client's own action descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedRoute:
    case_id: str
    source: str
    target: str
    tenant: str
    allowed: bool
    action: str
    target_type: str
    reason_contains: str


# One row for each cell of the official matrix, including both branch names
# the client wrote as "uat / <pse>-uat" and "prod / <pse>".
OFFICIAL_ROUTES: tuple[ExpectedRoute, ...] = (
    ExpectedRoute(
        "TC-01",
        "feature/payments",
        "main",
        "pse",
        True,
        "build_and_publish",
        "integration",
        "published to Artifact Registry",
    ),
    ExpectedRoute(
        "TC-02",
        "hotfix/tax-round",
        "main",
        "pse",
        True,
        "build_and_publish",
        "integration",
        "published to Artifact Registry",
    ),
    ExpectedRoute(
        "TC-03",
        "main",
        "uat",
        "pse",
        True,
        "deploy_uat",
        "uat",
        "UAT for end-to-end testing",
    ),
    ExpectedRoute(
        "TC-04",
        "main",
        "pse-uat",
        "pse",
        True,
        "deploy_uat",
        "uat",
        "UAT for end-to-end testing",
    ),
    ExpectedRoute(
        "TC-05",
        "feature/payments",
        "uat",
        "pse",
        False,
        "reject",
        "uat",
        "must merge into main first",
    ),
    ExpectedRoute(
        "TC-06",
        "feature/payments",
        "pse-uat",
        "pse",
        False,
        "reject",
        "uat",
        "must merge into main first",
    ),
    ExpectedRoute(
        "TC-07",
        "pse-dev",
        "pse-uat",
        "pse",
        False,
        "reject",
        "uat",
        "must merge into main first",
    ),
    ExpectedRoute(
        "TC-08",
        "uat",
        "prod",
        "pse",
        True,
        "promote_prod",
        "production",
        "live Production runtime",
    ),
    ExpectedRoute(
        "TC-09",
        "pse-uat",
        "pse",
        "pse",
        True,
        "promote_prod",
        "production",
        "live Production runtime",
    ),
    ExpectedRoute(
        "TC-10",
        "uat",
        "pse",
        "pse",
        True,
        "promote_prod",
        "production",
        "live Production runtime",
    ),
    ExpectedRoute(
        "TC-11",
        "pse-uat",
        "prod",
        "pse",
        True,
        "promote_prod",
        "production",
        "live Production runtime",
    ),
    ExpectedRoute(
        "TC-12",
        "main",
        "prod",
        "pse",
        False,
        "reject",
        "production",
        "skipping UAT",
    ),
    ExpectedRoute(
        "TC-13",
        "main",
        "pse",
        "pse",
        False,
        "reject",
        "production",
        "skipping UAT",
    ),
    ExpectedRoute(
        "TC-14",
        "feature/payments",
        "prod",
        "pse",
        False,
        "reject",
        "production",
        "skipping UAT",
    ),
    ExpectedRoute(
        "TC-15",
        "feature/payments",
        "pse",
        "pse",
        False,
        "reject",
        "production",
        "skipping UAT",
    ),
    ExpectedRoute(
        "TC-16",
        "feature/payments",
        "pse-dev",
        "pse",
        True,
        "sandbox",
        "sandbox",
        "without promotion gates",
    ),
    ExpectedRoute(
        "TC-17",
        "feature/payments",
        "experiment",
        "pse",
        True,
        "sandbox",
        "sandbox",
        "without promotion gates",
    ),
)


# Proves the tenant argument is the repository identity. ``pse`` inside the
# acme repository is not production.
ISOLATION_ROUTES: tuple[ExpectedRoute, ...] = (
    ExpectedRoute(
        "TC-18",
        "feature/payments",
        "pse",
        "acme",
        True,
        "sandbox",
        "sandbox",
        "without promotion gates",
    ),
    ExpectedRoute(
        "TC-19",
        "acme-uat",
        "acme",
        "acme",
        True,
        "promote_prod",
        "production",
        "live Production runtime",
    ),
    ExpectedRoute(
        "TC-20",
        "feature/payments",
        "acme",
        "acme",
        False,
        "reject",
        "production",
        "skipping UAT",
    ),
    ExpectedRoute(
        "TC-21",
        "main",
        "acme-uat",
        "acme",
        True,
        "deploy_uat",
        "uat",
        "UAT for end-to-end testing",
    ),
)
