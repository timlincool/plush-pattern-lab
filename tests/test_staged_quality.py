"""Staged-index and local-hook negative controls in isolated synthetic git clones."""

import shutil
import subprocess
import sys
from pathlib import Path

from install_quality_hook import install

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    return subprocess.run(
        ["git", *args], cwd=root, check=True, text=True, capture_output=True
    )


def fixture(tmp_path):
    git(tmp_path, "init", "--quiet")
    git(tmp_path, "config", "user.name", "Synthetic Test")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    for name in (
        "pyproject.toml",
        "ruff.toml",
        "scripts/check_quality.py",
        "scripts/check_quality_limits.py",
        "src/plush_pattern_lab/__init__.py",
    ):
        dest = tmp_path / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / name, dest)
    (tmp_path / "tests").mkdir()
    git(tmp_path, "add", ".")
    return tmp_path


def quality(root):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_quality.py"),
            "--root",
            str(root),
            "--staged",
        ],
        cwd=root,
        text=True,
        capture_output=True,
    )


def test_staged_invalid_ignores_unstaged_repair(tmp_path):
    root = fixture(tmp_path)
    source = root / "scripts/example.py"
    source.write_text("print(undefined_value)\n")
    git(root, "add", ".")
    source.write_text('print("corrected only in working tree")\n')
    result = quality(root)
    assert result.returncode != 0
    assert "F821" in result.stdout


def test_staged_valid_ignores_unstaged_damage(tmp_path):
    root = fixture(tmp_path)
    source = root / "scripts/example.py"
    source.write_text('print("safe")\n')
    git(root, "add", ".")
    source.write_text("print(undefined_value)\n")
    result = quality(root)
    assert result.returncode == 0, result.stdout + result.stderr


def test_noqa_cannot_skip_complexity_limit(tmp_path):
    root = fixture(tmp_path)
    source = root / "scripts/example.py"
    code = "def bad(x):  # noqa: C901, PLR0912\n" + "".join(
        f"    if x == {i}:\n        x += 1\n" for i in range(14)
    )
    source.write_text(code)
    git(root, "add", ".")
    result = quality(root)
    assert result.returncode != 0
    assert "C901" in result.stdout


def test_git_symlink_refused(tmp_path):
    root = fixture(tmp_path)
    source = root / "scripts/example.py"
    source.write_text('print("safe")\n')
    symlink = root / "scripts/link.py"
    symlink.symlink_to("example.py")
    git(root, "add", ".")
    result = quality(root)
    assert result.returncode != 0
    assert "symlink" in result.stderr


def test_hook_install_idempotent_and_preserves_existing(tmp_path):
    root = fixture(tmp_path)
    install(root)
    install(root)
    hook = root / ".git/hooks/pre-commit"
    assert hook.is_file()
    assert "--staged" in hook.read_text()
    hook.write_text("custom hook\n")
    try:
        install(root)
    except ValueError as exc:
        assert "not be overwritten" in str(exc)
    else:
        raise AssertionError("existing hook overwritten")
