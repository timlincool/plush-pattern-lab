"""Unified trusted-source quality checks; never import the project runtime."""

from __future__ import annotations

import argparse
import ast
import graphlib
import subprocess
import sys
import tempfile
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


def check(root: Path) -> None:
    """Validate the complete trusted source tree, not just changed files."""
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
    print("QUALITY_GATE_PASS: Ruff style, C901<=10, branches<=12, statements<=50,")
    print("  2000 lines and acyclic core imports")


def export_index(root: Path, destination: Path) -> None:
    """Write Git's indexed blobs as-is; no smudge filter or working-tree fallback."""
    listed = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=root, check=True, capture_output=True
    ).stdout
    for record in filter(None, listed.split(b"\0")):
        metadata, encoded = record.split(b"\t", 1)
        mode, sha, stage = metadata.decode("ascii").split()
        if mode not in {"100644", "100755"} or stage != "0":
            raise ValueError("staged index contains symlink, submodule or conflict")
        name = encoded.decode("utf-8")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("staged path escapes repository")
        blob = subprocess.run(
            ["git", "cat-file", "blob", sha],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(blob)


def check_staged(root: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="plush-quality-index-") as name:
        staged = Path(name)
        export_index(root, staged)
        quality = staged / "scripts" / "check_quality.py"
        if not quality.is_file():
            raise ValueError("quality checker is missing from staged index")
        process = subprocess.run(
            [sys.executable, str(quality), "--root", str(staged)],
            cwd=staged,
            capture_output=True,
            text=True,
        )
        print(process.stdout, end="")
        if process.stderr:
            print(process.stderr, end="", file=sys.stderr)
        if process.returncode:
            raise ValueError("staged index quality gate failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        if args.staged:
            check_staged(root)
        else:
            check(root)
    except (
        OSError,
        ValueError,
        SyntaxError,
        UnicodeError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"QUALITY_GATE_FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
