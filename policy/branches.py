"""Governed branch names for one tenant repository.

The client's matrix names two UAT branches and two production branches:

- UAT: ``uat`` and ``<tenant>-uat``
- Production: ``prod`` and ``<tenant>``
- Integration: ``main``

Every other branch is sandbox, for example ``<tenant>-dev``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TENANT = re.compile(r"[a-z][a-z0-9-]{0,30}")
_RESERVED = frozenset({"main", "uat", "prod"})


def validate_tenant(tenant: str) -> str:
    """Return the tenant slug or raise ValueError.

    A bad slug must fail closed. ``main``, ``uat``, and ``prod`` are branch
    names, so they cannot also be a tenant id. A slug ending in ``-uat`` would
    make ``<tenant>-uat`` ambiguous.
    """

    if not isinstance(tenant, str) or not _TENANT.fullmatch(tenant):
        raise ValueError(
            "Tenant slug must be 2-31 characters, lowercase, and start with a letter."
        )
    if len(tenant) < 2 or tenant.endswith("-") or "--" in tenant:
        raise ValueError(
            "Tenant slug must be 2-31 characters and must not start or end with a hyphen."
        )
    if tenant in _RESERVED or tenant.endswith("-uat"):
        raise ValueError(
            f"Tenant slug '{tenant}' collides with a governed branch name."
        )
    return tenant


@dataclass(frozen=True)
class BranchSpec:
    tenant: str
    integration: tuple[str, ...]
    uat: tuple[str, ...]
    production: tuple[str, ...]

    @property
    def governed(self) -> frozenset[str]:
        return frozenset((*self.integration, *self.uat, *self.production))


def branch_spec(tenant: str) -> BranchSpec:
    slug = validate_tenant(tenant)
    return BranchSpec(
        tenant=slug,
        integration=("main",),
        uat=("uat", f"{slug}-uat"),
        production=("prod", slug),
    )


def normalize_branch(name: str | None) -> str:
    """Strip the Git ref prefix GitHub sometimes includes."""

    if name is None:
        return ""
    value = str(name).strip()
    for prefix in ("refs/heads/", "refs/tags/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value
