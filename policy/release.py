"""Run one promotion stage, or refuse it.

``publish`` compiles nothing by itself. The build workflow lints and compiles
before it calls this stage. ``uat`` and ``prod`` only record the digest that
``publish`` already created.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from policy.artifacts import artifact_uri
from policy.promotion import REASON_PUBLISH, RouteDecision, evaluate

_EXPECTED_ACTION = {
    "publish": "build_and_publish",
    "uat": "deploy_uat",
    "prod": "promote_prod",
}

_COMPILATION = {
    "publish": "performed-before-publish",
    "uat": "not-performed",
    "prod": "not-performed",
}


class ReleaseRejected(Exception):
    def __init__(self, decision: RouteDecision) -> None:
        super().__init__(decision.reason)
        self.decision = decision


def publish_main(tenant: str, sha: str) -> dict:
    """Publish the commit that is already on main.

    A pull request into main proves the candidate. After GitHub merges it, the
    merge commit has its own SHA. UAT deploys that SHA, so this is the digest
    the rest of the ladder promotes.
    """

    cleaned = (sha or "").strip()
    uri = artifact_uri(tenant, cleaned)
    return {
        "stage": "publish",
        "tenant": tenant,
        "source": "main",
        "target": "main",
        "sha": cleaned,
        "uri": uri,
        "compilation": "performed-before-publish",
        "immutable": True,
        "action": "build_and_publish",
        "reason": REASON_PUBLISH,
    }


def execute(
    stage: str,
    source: str,
    target: str,
    tenant: str,
    sha: str,
) -> dict:
    if stage not in _EXPECTED_ACTION:
        raise ValueError(f"Unknown stage '{stage}'.")

    decision = evaluate(source, target, tenant)
    if decision.action != _EXPECTED_ACTION[stage]:
        raise ReleaseRejected(decision)

    uri = artifact_uri(tenant, sha)
    return {
        "stage": stage,
        "tenant": decision.tenant,
        "source": decision.source,
        "target": decision.target,
        "sha": sha.strip(),
        "uri": uri,
        "compilation": _COMPILATION[stage],
        "immutable": True,
        "action": decision.action,
        "reason": decision.reason,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish or promote one immutable artifact.")
    parser.add_argument("--stage", required=True, choices=[*sorted(_EXPECTED_ACTION), "publish-main"])
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--source")
    parser.add_argument("--target")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--output", help="Write the manifest JSON to this path.")
    args = parser.parse_args(argv)

    try:
        if args.stage == "publish-main":
            manifest = publish_main(args.tenant, args.sha)
        else:
            if not args.source or not args.target:
                print(
                    "BLOCKED  invalid release  exit 1\nSource and target branches are required.",
                    file=sys.stderr,
                )
                return 1
            manifest = execute(args.stage, args.source, args.target, args.tenant, args.sha)
    except ReleaseRejected as rejected:
        print(rejected.decision.format(), file=sys.stderr)
        return rejected.decision.exit_code
    except ValueError as exc:
        print(f"BLOCKED  invalid release  exit 1\n{exc}", file=sys.stderr)
        return 1

    text = json.dumps(manifest, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
