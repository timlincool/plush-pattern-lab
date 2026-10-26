"""Opt-in Git pre-commit for the complete *staged* index; never overwrite hooks."""

import shlex
import subprocess
import sys
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, capture_output=True
    ).stdout.strip()


def install(root: Path) -> None:
    current = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=root,
        text=True,
        capture_output=True,
    )
    if current.returncode not in {0, 1}:
        raise ValueError(current.stderr)
    if current.returncode == 0:
        raise ValueError("custom core.hooksPath is set; refusing to modify it")
    hook = Path(git(root, "rev-parse", "--git-path", "hooks/pre-commit"))
    if not hook.is_absolute():
        hook = root / hook
    checker = root / "scripts" / "check_quality.py"
    if not checker.is_file():
        raise ValueError("scripts/check_quality.py missing")
    content = f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(checker))} --staged\n"
    if hook.exists() or hook.is_symlink():
        if hook.is_file() and not hook.is_symlink() and hook.read_text() == content:
            hook.chmod(0o755)
            return
        raise ValueError("an existing pre-commit hook must not be overwritten")
    hook.parent.mkdir(parents=True, exist_ok=True)
    with hook.open("x", encoding="utf-8") as stream:
        stream.write(content)
    hook.chmod(0o755)


def main() -> int:
    try:
        install(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Installed opt-in staged-index quality hook.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
