#!/usr/bin/env python3
"""Create or update the three enterprise rulesets on each tenant repository.

Dry-run is the default. Nothing is sent to GitHub unless --apply is present.

Examples:

  python3 scripts/configure_rulesets.py \\
      --repo OWNER/github-abacus-task --tenant pse --caller-style local

  python3 scripts/configure_rulesets.py --inventory tenants.example.csv --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy.inventory import InventoryRow, parse_inventory
from policy.rulesets import desired_rulesets, plan_changes

API_VERSION = "2026-03-10"


def _request(method: str, url: str, token: str, body: dict | None = None) -> object:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("X-GitHub-Api-Version", API_VERSION)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API {exc.code} for {method} {url}\n{detail}") from exc
    return json.loads(raw) if raw else {}


def _list_rulesets(api: str, repository: str, token: str) -> list[dict]:
    page = 1
    found: list[dict] = []
    while True:
        batch = _request(
            "GET",
            f"{api}/repos/{repository}/rulesets?per_page=100&page={page}",
            token,
        )
        if not isinstance(batch, list) or not batch:
            break
        for summary in batch:
            full = _request(
                "GET",
                f"{api}/repos/{repository}/rulesets/{summary['id']}",
                token,
            )
            found.append(full)
        if len(batch) < 100:
            break
        page += 1
    return found


def _apply(api: str, repository: str, token: str, tenant: str, caller_style: str) -> None:
    existing = _list_rulesets(api, repository, token)
    desired = desired_rulesets(tenant, caller_style)
    for item in plan_changes(existing, desired):
        if item.action == "unchanged":
            print(f"unchanged  {repository}  {item.name}")
            continue
        if item.action == "create":
            _request("POST", f"{api}/repos/{repository}/rulesets", token, item.payload)
            print(f"created    {repository}  {item.name}")
            continue
        _request(
            "PUT",
            f"{api}/repos/{repository}/rulesets/{item.ruleset_id}",
            token,
            item.payload,
        )
        print(f"updated    {repository}  {item.name}")


def _dry_run(rows: list[InventoryRow]) -> None:
    print("Dry run. GitHub was not called. Pass --apply with GH_TOKEN to enforce.")
    print("Pass --check with GH_TOKEN to compare these payloads to the live rulesets.")
    for row in rows:
        print()
        print(f"# {row.repository}  tenant={row.tenant}  caller_style={row.caller_style}")
        for payload in desired_rulesets(row.tenant, row.caller_style):
            print(json.dumps(payload, indent=2))


def _check(api: str, token: str, rows: list[InventoryRow]) -> int:
    drift = 0
    for row in rows:
        existing = _list_rulesets(api, row.repository, token)
        desired = desired_rulesets(row.tenant, row.caller_style)
        for item in plan_changes(existing, desired):
            print(f"{item.action:<10} {row.repository}  {item.name}")
            if item.action != "unchanged":
                drift += 1
    return 1 if drift else 0


def _rows_from_args(args: argparse.Namespace) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    if args.inventory:
        rows.extend(parse_inventory(Path(args.inventory).read_text(encoding="utf-8")))
    if args.repo:
        if not args.tenant:
            raise SystemExit("--tenant is required with --repo.")
        rows.append(InventoryRow(args.repo, args.tenant, args.caller_style))
    if not rows:
        raise SystemExit("Provide --repo and --tenant, or --inventory.")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply the three enterprise rulesets.")
    parser.add_argument("--repo", help="owner/name. Repeat by using --inventory for many repos.")
    parser.add_argument("--tenant", help="Tenant slug for --repo.")
    parser.add_argument("--caller-style", choices=("local", "reusable"), default="local")
    parser.add_argument("--inventory", help="CSV file: repository,tenant[,caller_style]")
    parser.add_argument("--apply", action="store_true", help="Create or update rulesets.")
    parser.add_argument("--check", action="store_true", help="Exit 1 when live rulesets differ.")
    parser.add_argument("--api", default="https://api.github.com")
    args = parser.parse_args(argv)

    rows = _rows_from_args(args)
    if not args.apply and not args.check:
        _dry_run(rows)
        return 0

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN is required for --apply and --check.")
    if args.check and not args.apply:
        return _check(args.api, token, rows)
    for row in rows:
        _apply(args.api, row.repository, token, row.tenant, row.caller_style)
    return 0


if __name__ == "__main__":
    sys.exit(main())
