"""Repository-sized, dependency-free checks enforced alongside Ruff in CI.

Only trusted main executes this script; it never imports or executes source files.
"""

from __future__ import annotations

import argparse
from pathlib import Path

MAX_PYTHON_LINES = 2000
SOURCE_DIRS = ("scripts", "tests")


def check_limits(root: Path, max_lines: int = MAX_PYTHON_LINES) -> list[str]:
    """Report all oversized Python files, without importing contributor code."""
    if max_lines < 1:
        raise ValueError("max_lines must be positive")
    violations: list[str] = []
    for folder in SOURCE_DIRS:
        source = root / folder
        if not source.is_dir():
            violations.append(f"missing required source directory: {folder}/")
            continue
        for path in sorted(source.rglob("*.py")):
            relative = path.relative_to(root)
            if path.is_symlink():
                violations.append(f"{relative}: symlinked Python files are prohibited")
                continue
            with path.open("r", encoding="utf-8") as handle:
                line_count = sum(1 for _ in handle)
            if line_count > max_lines:
                violations.append(
                    f"{relative}: {line_count} lines exceeds hard limit {max_lines}; split the module"
                )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = check_limits(args.root.resolve())
    for error in errors:
        print(f"QUALITY_GATE_FAIL: {error}")
    if errors:
        return 1
    print(f"QUALITY_GATE_PASS: Python modules <= {MAX_PYTHON_LINES} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
