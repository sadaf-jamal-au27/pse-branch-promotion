"""Identity of a build artifact.

UAT and production receive this same URI. They do not compile a second time.
The registry scheme is simulated so the exercise can run in a personal GitHub
account. The URI shape is what a real Artifact Registry client would publish.
"""

from __future__ import annotations

import hashlib

from policy.branches import validate_tenant


def artifact_uri(tenant: str, git_sha: str) -> str:
    slug = validate_tenant(tenant)
    sha = (git_sha or "").strip()
    if not sha:
        raise ValueError("A git SHA is required to identify the artifact.")
    digest = hashlib.sha256(sha.encode("utf-8")).hexdigest()
    return f"simulated://artifact-registry/tenants/{slug}/app@sha256:{digest}"
