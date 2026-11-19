"""Parse the tenant inventory the ruleset script applies."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryRow:
    repository: str
    tenant: str
    caller_style: str


def parse_inventory(text: str) -> list[InventoryRow]:
    rows: list[InventoryRow] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("repository,"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) not in (2, 3):
            raise ValueError(f"Line {line_number}: expected repository,tenant[,caller_style].")
        repository, tenant = parts[0], parts[1]
        caller_style = parts[2] if len(parts) == 3 and parts[2] else "reusable"
        if repository.count("/") != 1:
            raise ValueError(f"Line {line_number}: repository must look like owner/name.")
        if caller_style not in {"local", "reusable"}:
            raise ValueError(f"Line {line_number}: caller_style must be local or reusable.")
        rows.append(InventoryRow(repository, tenant, caller_style))
    return rows
