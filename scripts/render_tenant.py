#!/usr/bin/env python3
"""Write the four caller workflows for one tenant repository."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from policy.render import render_callers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render tenant caller workflows.")
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--platform-repository", required=True)
    parser.add_argument("--platform-ref", default="v1")
    parser.add_argument("--output", required=True, help="Directory that receives .github/workflows.")
    args = parser.parse_args(argv)

    destination = Path(args.output) / ".github" / "workflows"
    destination.mkdir(parents=True, exist_ok=True)
    files = render_callers(args.tenant, args.platform_repository, args.platform_ref)
    for name, text in files.items():
        (destination / name).write_text(text, encoding="utf-8")
        print(destination / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
