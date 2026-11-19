"""Render the thin workflow callers that each tenant repository commits.

The promotion logic stays in the platform repository. A tenant file only
chooses the tenant slug and the branch names that start the workflow.
"""

from __future__ import annotations

from policy.branches import branch_spec

_EVENTS = "[opened, synchronize, reopened, ready_for_review]"


def _header(name: str, event: str, branches: tuple[str, ...] | None) -> str:
    lines = [
        f"name: {name}",
        "",
        "on:",
        f"  {event}:",
    ]
    if event == "pull_request":
        lines.append(f"    types: {_EVENTS}")
    if branches is not None:
        lines.append("    branches:")
        lines.extend(f"      - {branch}" for branch in branches)
    lines.extend(
        [
            "",
            "permissions:",
            "  contents: read",
            "",
            "jobs:",
            f"  {name}:",
            f"    name: {name}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_callers(
    tenant: str,
    platform_repository: str,
    platform_ref: str = "v1",
) -> dict[str, str]:
    """Return workflow file name -> YAML text for one tenant."""

    spec = branch_spec(tenant)
    if platform_repository.count("/") != 1:
        raise ValueError("platform_repository must look like owner/name.")

    specs = {
        "promotion-policy.yml": ("pull_request", None, "promotion-policy"),
        "build-and-publish.yml": ("pull_request", spec.integration, "build-and-publish"),
        "deploy-uat.yml": ("pull_request", spec.uat, "deploy-uat"),
        "promote-prod.yml": ("pull_request", spec.production, "promote-prod"),
        "publish-main.yml": ("push", spec.integration, "publish-main"),
    }
    files: dict[str, str] = {}
    for filename, (event, branches, job) in specs.items():
        workflow_file = "build-and-publish.yml" if filename == "publish-main.yml" else filename
        body = _header(job, event, branches)
        body += (
            f"    uses: {platform_repository}/.github/workflows/{workflow_file}@{platform_ref}\n"
            "    with:\n"
            f"      tenant: {spec.tenant}\n"
            f"      platform_repository: {platform_repository}\n"
            f"      platform_ref: {platform_ref}\n"
        )
        files[filename] = body
    return files
