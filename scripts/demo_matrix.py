#!/usr/bin/env python3
"""Print the official matrix by executing the policy. Exit 1 on any mismatch."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy.official_matrix import ISOLATION_ROUTES, OFFICIAL_ROUTES
from policy.promotion import evaluate


def _rows(cases):
    mismatches = 0
    for case in cases:
        decision = evaluate(case.source, case.target, case.tenant)
        ok = (
            decision.allowed is case.allowed
            and decision.action == case.action
            and decision.target_type == case.target_type
            and case.reason_contains in decision.reason
            and decision.exit_code == (0 if case.allowed else 1)
        )
        if not ok:
            mismatches += 1
        status = "ALLOWED" if decision.allowed else "BLOCKED"
        mark = "OK" if ok else "MISMATCH"
        print(
            f"{case.case_id:<6} {mark:<9} {status:<8} "
            f"{case.source} -> {case.target:<12} {decision.action}"
        )
    return mismatches


def main() -> int:
    print("Tenant PSE — official promotion matrix")
    print("-" * 72)
    mismatches = _rows(OFFICIAL_ROUTES)
    print()
    print("Tenant isolation — acme does not inherit PSE branch names")
    print("-" * 72)
    mismatches += _rows(ISOLATION_ROUTES)
    print("-" * 72)
    total = len(OFFICIAL_ROUTES) + len(ISOLATION_ROUTES)
    print(f"{total} routes, {mismatches} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
