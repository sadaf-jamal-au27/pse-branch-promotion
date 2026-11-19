"""Command line entry for the required status check."""

from __future__ import annotations

import argparse
import sys

from policy.promotion import evaluate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Exit 0 when the pull request route is on the official matrix, else exit 1."
    )
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    args = parser.parse_args(argv)

    try:
        decision = evaluate(args.source, args.target, args.tenant)
    except ValueError as exc:
        print(f"BLOCKED  invalid tenant  exit 1\n{exc}", file=sys.stderr)
        return 1

    stream = sys.stdout if decision.allowed else sys.stderr
    print(decision.format(), file=stream)
    return decision.exit_code


if __name__ == "__main__":
    sys.exit(main())
