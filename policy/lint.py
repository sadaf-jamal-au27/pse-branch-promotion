"""Simulated lint for the pilot service.

The step compiles every Python file and rejects debugger breakpoints. A real
tenant swaps this command for ruff, eslint, or Maven inside the platform
workflow. The route decision does not live here, so a lint change cannot open
a promotion path.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def lint_tree(path: Path) -> list[str]:
    problems: list[str] = []
    if not path.exists():
        return [f"Missing source path: {path}"]

    files = sorted(item for item in path.rglob("*.py") if item.is_file())
    if not files:
        return [f"No Python files under {path}"]

    for file in files:
        text = file.read_text(encoding="utf-8")
        if "breakpoint(" in text or "pdb.set_trace" in text:
            problems.append(f"{file}: debugger statement is not allowed")
        try:
            compile(text, str(file), "exec")
        except SyntaxError as exc:
            problems.append(f"{file}:{exc.lineno}: {exc.msg}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint and compile a Python tree.")
    parser.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    problems = lint_tree(Path(args.path))
    if problems:
        print("LINT FAILED", file=sys.stderr)
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1
    print(f"LINT PASSED  {args.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
