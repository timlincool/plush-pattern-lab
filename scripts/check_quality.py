"""Unified trusted-source quality checks; never import the project runtime."""

from __future__ import annotations

import ast
import graphlib
import subprocess
import sys
from pathlib import Path

from check_quality_limits import check_limits

PACKAGE = "plush_pattern_lab"
SOURCE = Path("src") / PACKAGE


def package_files(root: Path) -> dict[str, Path]:
    directory = root / SOURCE
    if not directory.is_dir() or not (directory / "__init__.py").is_file():
        raise ValueError("missing src/plush_pattern_lab package")
    paths = {}
    for path in sorted(directory.rglob("*.py")):
        parts = path.relative_to(root / "src").with_suffix("").parts
        module = ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
        paths[module] = path
    return paths


def imports(module: str, path: Path) -> set[str]:
    parsed = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    used: set[str] = set()
    package = module if path.name == "__init__.py" else module.rpartition(".")[0]
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            used.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                prefix = ".".join(parts[: len(parts) - node.level + 1])
                base = ".".join(filter(None, (prefix, node.module)))
            else:
                base = node.module or ""
            used.add(base)
            used.update(base + "." + alias.name for alias in node.names)
    return used


def architecture_errors(root: Path) -> list[str]:
    paths = package_files(root)
    graph = {}
    errors = []
    for module, path in paths.items():
        dependencies = imports(module, path)
        graph[module] = {
            name for name in dependencies if name in paths and name != module
        }
        for name in dependencies:
            if name == "scripts" or name.startswith("scripts."):
                errors.append(f"{module}: package must not import scripts CLI")
            if (
                module == PACKAGE
                or module.startswith(PACKAGE + ".patterns")
                or module.startswith(PACKAGE + ".validation")
            ) and (
                name == PACKAGE + ".blender" or name.startswith(PACKAGE + ".blender.")
            ):
                errors.append(f"{module}: pure research code depends on Blender")
    try:
        graphlib.TopologicalSorter(graph).prepare()
    except graphlib.CycleError as exc:
        errors.append("circular package imports: " + " -> ".join(exc.args[1]))
    return errors


def run(root: Path, *args: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", *args], cwd=root, text=True, capture_output=True
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise ValueError(f"Ruff {args[0]} failed ({result.returncode})")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        run(root, "check", ".")
        run(root, "format", "--check", ".")
        run(
            root,
            "check",
            "--isolated",
            "--select",
            "C901,PLR0912,PLR0915",
            "--ignore-noqa",
            "--config",
            "lint.mccabe.max-complexity=10",
            "--config",
            "lint.pylint.max-branches=12",
            "--config",
            "lint.pylint.max-statements=50",
            "src",
            "scripts",
            "tests",
        )
        errors = check_limits(root) + architecture_errors(root)
        if errors:
            raise ValueError("\n".join(errors))
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"QUALITY_GATE_FAIL: {exc}", file=sys.stderr)
        return 1
    print("QUALITY_GATE_PASS: Ruff style, C901<=10, branches<=12, statements<=50,")
    print("  2000 lines and acyclic core imports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
